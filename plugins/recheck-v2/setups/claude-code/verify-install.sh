#!/bin/sh
# Installed-package verification for the Claude Code pilot setup (E9 section
# 9.2, amendment A7b, ruling E9-16).
#
# Usage: verify-install.sh [--pilot-home DIR] [--installed DIR]
# Prints one JSON object on stdout; diagnostics go to stderr.
# Exit 0 every check passed, 4 a check failed, 2 usage, 3 the installed plugin
# or the claude binary is missing, 1 anything else. Writes nothing.
#
# Checks: the installed folder diffs clean against the canonical one
# (__pycache__ excluded); the installed SKILL.md frontmatter name, description
# and metadata.version equal the canonical; every relative path the installed
# SKILL.md, adapters/README.md and references/*.md link resolves inside the
# installed plugin root; the installed copy's `recheck.py skill-identity`
# content_sha256 equals the canonical checkout's (E9-16: version and commit are
# recorded, never compared, because a cache copy is outside git).

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
PILOT_HOME="${SKILLS_V2_PILOT_HOME:-$HOME/.local/share/skills-v2-pilot/claude-code}"
INSTALLED=""

while [ $# -gt 0 ]; do
  case "$1" in
    --pilot-home) PILOT_HOME="$2"; shift 2 ;;
    --installed) INSTALLED="$2"; shift 2 ;;
    -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "verify-install.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

CONFIG_DIR="$PILOT_HOME/config"
if [ -z "$INSTALLED" ]; then
  INSTALLED=$(find "$CONFIG_DIR/plugins/cache" -maxdepth 3 -mindepth 3 -type d \
    -path '*/recheck-v2/*' 2>/dev/null | sort | tail -1)
fi
[ -n "$INSTALLED" ] && [ -d "$INSTALLED" ] || {
  echo "verify-install.sh: no installed recheck-v2 under $CONFIG_DIR/plugins/cache" >&2
  exit 3
}
command -v uv >/dev/null 2>&1 || { echo "verify-install.sh: uv is not on PATH" >&2; exit 3; }

CANON_ID=$(uv run "$PLUGIN_ROOT/skills/recheck-v2/scripts/recheck.py" skill-identity 2>/dev/null)
INST_ID=$(uv run "$INSTALLED/skills/recheck-v2/scripts/recheck.py" skill-identity 2>/dev/null)
DIFF=$(diff -r -x __pycache__ "$PLUGIN_ROOT" "$INSTALLED" 2>&1 || true)

python3 - "$PLUGIN_ROOT" "$INSTALLED" "$CANON_ID" "$INST_ID" "$DIFF" <<'PY'
import glob
import json
import os
import re
import sys

canonical, installed, canon_id, inst_id, diff_text = sys.argv[1:6]
findings = []

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


def frontmatter(path):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    if end < 0:
        return None
    block = text[4:end + 1]
    fields = {}
    key = None
    for line in block.splitlines():
        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:", line):
            key, _, rest = line.partition(":")
            fields[key] = rest.strip()
        elif key and line.startswith("  ") and ":" in line:
            sub, _, rest = line.strip().partition(":")
            fields["%s.%s" % (key, sub)] = rest.strip()
        elif key and line.strip():
            fields[key] = (fields.get(key, "") + " " + line.strip()).strip()
    return fields


canon_fm = frontmatter(os.path.join(canonical, "skills", "recheck-v2", "SKILL.md"))
inst_fm = frontmatter(os.path.join(installed, "skills", "recheck-v2", "SKILL.md"))
frontmatter_check = {}
if not canon_fm or not inst_fm:
    findings.append("a SKILL.md frontmatter block could not be parsed")
else:
    for field in ("name", "description", "metadata.version"):
        same = canon_fm.get(field) == inst_fm.get(field) and inst_fm.get(field) not in (None, "")
        frontmatter_check[field] = {
            "installed": inst_fm.get(field) if field != "description" else
            (inst_fm.get(field) or "")[:60] + "…",
            "equals_canonical": same,
        }
        if not same:
            findings.append("installed frontmatter field %s differs or is missing" % field)

# "Every relative path the installed SKILL.md, adapters/README.md and
# references/*.md LINK resolves inside the installed plugin root" (section 9.2):
# the markdown links are the links. Backticked file names in prose are artifact
# names and repo-relative paths, not links; they are listed for the record and
# gate nothing.
LINK = re.compile(r"\]\(([^)\s]+)\)")
TICK = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|json|py))`")
skill_root = os.path.join(installed, "skills", "recheck-v2")
targets = [
    os.path.join(skill_root, "SKILL.md"),
    os.path.join(skill_root, "adapters", "README.md"),
]
targets.extend(sorted(glob.glob(os.path.join(skill_root, "references", "*.md"))))
root_real = os.path.realpath(installed)
checked = 0
outside = []
missing = []
unresolved_prose = []


def contained(resolved):
    return resolved == root_real or resolved.startswith(root_real + os.sep)


for path in targets:
    if not os.path.isfile(path):
        findings.append("expected file missing from the installed copy: %s" % path)
        continue
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    label = os.path.relpath(path, installed)
    for candidate in sorted(set(LINK.findall(text))):
        if candidate.startswith(("http://", "https://", "#", "/", "$")) or "${" in candidate:
            continue
        resolved = os.path.realpath(os.path.join(os.path.dirname(path), candidate))
        checked += 1
        if not contained(resolved):
            outside.append("%s -> %s" % (label, candidate))
        elif not os.path.exists(resolved):
            missing.append("%s -> %s" % (label, candidate))
    for candidate in sorted(set(TICK.findall(text)) - set(LINK.findall(text))):
        if candidate.startswith(("http://", "https://", "#", "/", "$")) or "${" in candidate:
            continue
        resolved = os.path.realpath(os.path.join(os.path.dirname(path), candidate))
        if not contained(resolved) or not os.path.exists(resolved):
            unresolved_prose.append("%s -> %s" % (label, candidate))
if outside:
    findings.append("linked paths resolving outside the plugin root: %s" % ", ".join(outside))
if missing:
    findings.append("linked paths that do not exist: %s" % ", ".join(missing))

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
    "frontmatter": frontmatter_check,
    "links_checked": checked,
    "links_outside_root": outside,
    "links_missing": missing,
    "backticked_paths_not_resolving_in_root": unresolved_prose,
    "skill_identity": {
        "canonical": canon_identity,
        "installed": inst_identity,
        "content_sha256_equal": identity_match,
        "note": "E9-16: version and commit are recorded, never compared; a cache copy is "
                "outside git and reads commit unversioned",
    },
    "is_symlink": os.path.islink(installed)
    or os.path.islink(os.path.join(installed, "skills", "recheck-v2", "SKILL.md")),
    "findings": findings,
}
sys.stdout.write(json.dumps(document, indent=2) + "\n")
sys.exit(0 if document["ok"] else 4)
PY
