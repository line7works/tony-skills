#!/bin/sh
# Installed-package verification for the Claude Code pilot setup (E9 section
# 9.2, amendment A7b, ruling E9-16).
#
# Usage: verify-install.sh [--pilot-home DIR] [--installed DIR]
# Prints one JSON object on stdout; diagnostics go to stderr.
# Exit 0 every check passed, 4 a check failed, 2 usage, 3 the installed plugin,
# the claude binary or uv is missing, 1 anything else. Writes nothing inside the
# installed copy or the repository (a scratch directory under $TMPDIR holds the
# child commands' stderr and is removed).
#
# Checks: the installed folder diffs clean against the canonical one
# (__pycache__ excluded); the installed SKILL.md frontmatter name, description
# (parsed as YAML and compared whole, folded scalars included) and
# metadata.version equal the canonical; every runtime reference the installed
# SKILL.md, adapters/README.md, references/*.md and the adapter profiles name —
# Markdown links AND backticked paths — resolves inside the installed plugin
# root, exists, and is a real file; no surface inside the installed root is a
# symlink (lstat, every entry, the root included: a package that must be a copy
# is a copy); the installed copy's `recheck.py skill-identity` content_sha256
# equals the canonical checkout's (E9-16: version and commit are recorded, never
# compared, because a cache copy is outside git).

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
PILOT_HOME="${SKILLS_V2_PILOT_HOME:-$HOME/.local/share/skills-v2-pilot/claude-code}"
INSTALLED=""

while [ $# -gt 0 ]; do
  case "$1" in
    --pilot-home) PILOT_HOME="$2"; shift 2 ;;
    --installed) INSTALLED="$2"; shift 2 ;;
    -h|--help) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "verify-install.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

CONFIG_DIR="$PILOT_HOME/config"
if [ -z "$INSTALLED" ]; then
  INSTALLED=$(find "$CONFIG_DIR/plugins/cache" -maxdepth 3 -mindepth 3 \
    -path '*/recheck-v2/*' 2>/dev/null | sort | tail -1)
fi
[ -n "$INSTALLED" ] && [ -e "$INSTALLED" ] || {
  echo "verify-install.sh: no installed recheck-v2 under $CONFIG_DIR/plugins/cache" >&2
  exit 3
}
command -v uv >/dev/null 2>&1 || { echo "verify-install.sh: uv is not on PATH" >&2; exit 3; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/recheck-verify-install.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM

# Every child's status is kept and its diagnostics reach stderr: an offline or
# broken dependency must never look like a passing component check.
CANON_STATUS=0
CANON_ID=$(uv run "$PLUGIN_ROOT/skills/recheck-v2/scripts/recheck.py" skill-identity \
  2>"$WORK/canonical-identity.err") || CANON_STATUS=$?
if [ "$CANON_STATUS" -ne 0 ]; then
  echo "verify-install.sh: the canonical skill-identity command exited $CANON_STATUS:" >&2
  cat "$WORK/canonical-identity.err" >&2
fi
INST_STATUS=0
INST_ID=$(uv run "$INSTALLED/skills/recheck-v2/scripts/recheck.py" skill-identity \
  2>"$WORK/installed-identity.err") || INST_STATUS=$?
if [ "$INST_STATUS" -ne 0 ]; then
  echo "verify-install.sh: the installed skill-identity command exited $INST_STATUS:" >&2
  cat "$WORK/installed-identity.err" >&2
fi
DIFF_STATUS=0
DIFF=$(diff -r -x __pycache__ "$PLUGIN_ROOT" "$INSTALLED" 2>"$WORK/diff.err") || DIFF_STATUS=$?
if [ -s "$WORK/diff.err" ]; then
  echo "verify-install.sh: diff wrote to stderr:" >&2
  cat "$WORK/diff.err" >&2
fi

uv run --with pyyaml python - "$PLUGIN_ROOT" "$INSTALLED" "$CANON_ID" "$INST_ID" "$DIFF" \
  "$CANON_STATUS" "$INST_STATUS" "$DIFF_STATUS" "$(cat "$WORK/diff.err")" <<'PY'
import glob
import json
import os
import re
import sys

import yaml

(canonical, installed, canon_id, inst_id, diff_text,
 canon_status, inst_status, diff_status, diff_err) = sys.argv[1:10]
findings = []

if canon_status != "0":
    findings.append(
        "the canonical skill-identity command exited %s (its diagnostics are on stderr)"
        % canon_status
    )
if inst_status != "0":
    findings.append(
        "the installed skill-identity command exited %s (its diagnostics are on stderr)"
        % inst_status
    )
if diff_err.strip():
    findings.append("diff reported an error on stderr: %s" % diff_err.strip().splitlines()[0])

try:
    canon_identity = json.loads(canon_id)
except ValueError:
    canon_identity = None
    findings.append("the canonical checkout's skill-identity did not print JSON")
try:
    inst_identity = json.loads(inst_id)
except ValueError:
    inst_identity = None
    findings.append("the installed copy's skill-identity did not print JSON")

diff_lines = [line for line in diff_text.splitlines() if line.strip()]
if diff_lines:
    findings.append("diff -r is not empty: %d lines, first: %s" % (len(diff_lines), diff_lines[0]))

# ---------------------------------------------------------------- frontmatter
def frontmatter(path):
    """The block between the --- delimiters, parsed as YAML.

    A hand-rolled `key: value` split reads an indented colon inside a folded
    description as a nested key and can call two different descriptions equal
    (Astra's finding 11), so the real parser runs and the description is
    compared whole.
    """
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    if not text.startswith("---\n"):
        return None, "no opening frontmatter delimiter"
    end = text.find("\n---\n", 3)
    if end < 0:
        return None, "no closing frontmatter delimiter"
    block = text[4:end + 1]
    try:
        parsed = yaml.safe_load(block)
    except yaml.YAMLError as error:
        return None, "the frontmatter is not valid YAML: %s" % error
    if not isinstance(parsed, dict):
        return None, "the frontmatter is not a mapping"
    return parsed, None


def field(document, name):
    if name == "metadata.version":
        return (document.get("metadata") or {}).get("version")
    return document.get(name)


skill_root = os.path.join(installed, "skills", "recheck-v2")
canon_fm, canon_why = frontmatter(os.path.join(canonical, "skills", "recheck-v2", "SKILL.md"))
inst_fm, inst_why = frontmatter(os.path.join(skill_root, "SKILL.md"))
frontmatter_check = {}
if canon_fm is None or inst_fm is None:
    findings.append(
        "a SKILL.md frontmatter block could not be parsed (canonical: %s; installed: %s)"
        % (canon_why or "ok", inst_why or "ok")
    )
else:
    for name in ("name", "description", "metadata.version"):
        mine, theirs = field(inst_fm, name), field(canon_fm, name)
        same = mine == theirs and mine not in (None, "")
        frontmatter_check[name] = {
            "installed": mine if name != "description" else (mine or "")[:60] + "…",
            "installed_length": len(mine) if isinstance(mine, str) else None,
            "canonical_length": len(theirs) if isinstance(theirs, str) else None,
            "equals_canonical": same,
        }
        if not same:
            findings.append("installed frontmatter field %s differs or is missing" % name)

# ------------------------------------------------------- symlinks and copies
root_real = os.path.realpath(installed)
symlinks = []
if os.path.islink(installed):
    symlinks.append("the installed plugin root itself -> %s" % os.readlink(installed))
for base, directories, files in os.walk(installed, followlinks=False):
    for name in list(directories) + files:
        path = os.path.join(base, name)
        if os.path.islink(path):
            target = os.readlink(path)
            resolved = os.path.realpath(path)
            symlinks.append(
                "%s -> %s%s"
                % (
                    os.path.relpath(path, installed),
                    target,
                    "" if resolved.startswith(root_real + os.sep) else " (outside the root)",
                )
            )
if symlinks:
    findings.append(
        "the installed package must be a copy, and these surfaces are links: %s"
        % "; ".join(symlinks)
    )

# ------------------------------------------------------------- references
# Every runtime reference the installed documents name, whether it is written
# as a Markdown link or as a backticked path (the adapter index uses backticked
# paths, which the link-only check of the first pass never looked at).
LINK = re.compile(r"\]\(([^)\s]+)\)")
TICK = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|json|py|sh|yaml|yml|toml))`")
SKILL_DIRECTORIES = ("references", "adapters", "scripts", "assets", "evals", "hooks", "skills")

targets = [
    os.path.join(skill_root, "SKILL.md"),
    os.path.join(skill_root, "adapters", "README.md"),
]
targets.extend(sorted(glob.glob(os.path.join(skill_root, "references", "*.md"))))
targets.extend(sorted(glob.glob(os.path.join(skill_root, "adapters", "*", "profile.md"))))

checked = 0
outside = []
missing = []
linked = []
named_but_absent = []
artifact_names = []


def contained(path):
    return path == root_real or path.startswith(root_real + os.sep)


def skippable(candidate):
    return candidate.startswith(("http://", "https://", "#", "/", "$")) or "${" in candidate


def bases_for(document_dir):
    """A prose path is written from the document or from the skill root.

    `references/pilot-contract.md` names `scripts/validate-result.py`, which is
    the skill root's, and `adapters/README.md` names `claude-code/profile.md`,
    which is its own directory's: both bases are tried before a reference is
    called absent.
    """
    return [document_dir, skill_root]


def inspect(label, document_dir, candidate, required):
    """One reference: contained, existing, and not a link anywhere below root."""
    global checked
    found_base = None
    for base in bases_for(document_dir):
        if os.path.lexists(os.path.join(base, candidate)):
            found_base = base
            break
    if found_base is None:
        first = candidate.split("/")[0]
        if required or first in SKILL_DIRECTORIES:
            checked += 1
            resolved = os.path.realpath(os.path.join(document_dir, candidate))
            if not contained(resolved):
                outside.append("%s -> %s" % (label, candidate))
            else:
                missing.append("%s -> %s" % (label, candidate))
        else:
            named_but_absent.append("%s -> %s" % (label, candidate))
        return
    checked += 1
    resolved = os.path.realpath(os.path.join(found_base, candidate))
    if not contained(resolved):
        outside.append("%s -> %s" % (label, candidate))
        return
    # lstat every component inside the root: a link anywhere on the path means
    # the reference leaves the installed copy even when its realpath is inside.
    walked = found_base
    for part in os.path.normpath(candidate).split(os.sep):
        walked = os.path.join(walked, part)
        if os.path.islink(walked):
            linked.append("%s -> %s (%s is a link)" % (label, candidate, walked))
            return


for path in targets:
    if not os.path.isfile(path):
        findings.append("expected file missing from the installed copy: %s" % path)
        continue
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    label = os.path.relpath(path, installed)
    document_dir = os.path.dirname(path)
    links = set(LINK.findall(text))
    for candidate in sorted(links):
        if skippable(candidate):
            continue
        inspect(label, document_dir, candidate.split("#")[0], required=True)
    for candidate in sorted(set(TICK.findall(text)) - links):
        if skippable(candidate):
            continue
        first = candidate.split("/")[0]
        resolves = any(
            os.path.lexists(os.path.join(base, candidate)) for base in bases_for(document_dir)
        )
        if not resolves and (
            "/" not in candidate or first in ("docs", "run_dir", "verifier", "evals")
        ):
            # `chat.md`, `result.json`, `run_dir/checkpoint.json`,
            # `docs/plans/...`: artifact names and workspace paths in prose, not
            # paths into the installed package.
            artifact_names.append("%s -> %s" % (label, candidate))
            continue
        inspect(label, document_dir, candidate, required=False)

if outside:
    findings.append("references resolving outside the plugin root: %s" % ", ".join(outside))
if missing:
    findings.append("references that do not exist in the installed copy: %s" % ", ".join(missing))
if linked:
    findings.append("references reached through a symlink: %s" % ", ".join(linked))

identity_match = bool(
    canon_identity and inst_identity
    and canon_identity.get("content_sha256") == inst_identity.get("content_sha256")
)
if not identity_match:
    findings.append("skill-identity content_sha256 differs between installed and canonical")

document = {
    "ok": not findings,
    "canonical": canonical,
    "installed": installed,
    "diff_lines": len(diff_lines),
    "diff_exit": int(diff_status),
    "frontmatter": frontmatter_check,
    "frontmatter_parser": "yaml.safe_load (pyyaml %s)" % yaml.__version__,
    "references_checked": checked,
    "references_outside_root": outside,
    "references_missing": missing,
    "references_through_a_symlink": linked,
    "named_but_absent_from_this_package": named_but_absent,
    "artifact_names_not_references": artifact_names,
    "symlinks_in_the_installed_package": symlinks,
    "skill_identity": {
        "canonical": canon_identity,
        "installed": inst_identity,
        "canonical_command_exit": int(canon_status),
        "installed_command_exit": int(inst_status),
        "content_sha256_equal": identity_match,
        "note": "E9-16: version and commit are recorded, never compared; a cache copy is "
                "outside git and reads commit unversioned",
    },
    "is_symlink": os.path.islink(installed)
    or os.path.islink(os.path.join(skill_root, "SKILL.md")),
    "findings": findings,
}
sys.stdout.write(json.dumps(document, indent=2) + "\n")
sys.exit(0 if document["ok"] else 4)
PY
