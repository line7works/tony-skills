#!/bin/sh
# Installed-package verification for the OpenCode pilot setup (E9 section 9.2, amendment A7b,
# ruling E9-16; guide "Distribution and versioning": verify the installed package, not the repo).
#
# Usage:  sh verify-install.sh [--setup DIR] [--skill NAME]
#   --setup DIR   the isolated pilot setup (default ~/.local/share/skills-v2-pilot/opencode)
#   --skill NAME  the installed skill folder to check (default recheck-v2)
#
# Prints one JSON object on stdout and nothing else; diagnostics go to stderr.
# Exit 0 when every check passed, 4 when any failed, 2 on a usage slip, 3 when the installed
# folder or the canonical folder is missing. Side effects: none (it writes only a temporary
# file under ${TMPDIR}).
#
# Checks:
#   installed_path      where the harness actually loads the skill from (opencode debug skill)
#   diff_empty          diff -r installed vs canonical, excluding __pycache__
#   frontmatter         name, description and metadata.version of the installed SKILL.md equal
#                       the canonical ones
#   links_contained     every relative link AND every backticked relative path in the
#                       installed SKILL.md, adapters/README.md, references/*.md and each
#                       adapters/*/profile.md resolves inside the installed skill root after
#                       every symlink; a reference reached through a symlink, and any symlink
#                       anywhere in the installed tree, is a finding (identical bytes behind a
#                       symlink pass `diff -r`)
#   identity            skill-identity from the installed copy; content_sha256 is compared
#                       with the canonical checkout's, version and commit are recorded only
#                       (E9-16: they come from the packaging, not the content)
#   is_copy_not_symlink the installed folder and its SKILL.md are real files (guide: an update
#                       must not turn a copied install back into a symlink)
set -eu

SETUP="${HOME}/.local/share/skills-v2-pilot/opencode"
SKILL="recheck-v2"
while [ $# -gt 0 ]; do
  case "$1" in
    --setup) SETUP="$2"; shift 2 ;;
    --skill) SKILL="$2"; shift 2 ;;
    -h|--help) sed -n '2,27p' "$0"; exit 0 ;;
    *) echo "verify-install.sh: unknown argument $1" >&2; exit 2 ;;
  esac
done

HERE=$(cd "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(cd "$HERE/../.." && pwd)
CANON="$PLUGIN_ROOT/skills/$SKILL"
INSTALLED="$SETUP/xdg-config/opencode/skill/$SKILL"

[ -d "$CANON" ] || { echo "verify-install.sh: no canonical skill at $CANON" >&2; exit 3; }
[ -d "$INSTALLED" ] || { echo "verify-install.sh: no installed skill at $INSTALLED (run install.sh)" >&2; exit 3; }

export XDG_CONFIG_HOME="$SETUP/xdg-config"
export XDG_DATA_HOME="$SETUP/xdg-data"
export XDG_CACHE_HOME="$SETUP/xdg-cache"
export XDG_STATE_HOME="$SETUP/xdg-state"
export OPENCODE_DISABLE_EXTERNAL_SKILLS=1
OC="$SETUP/npm/node_modules/.bin/opencode"

cat > "${TMPDIR:-/tmp}/recheck-v2-loaded-$$.py" <<'PY'
import json, sys
want = sys.argv[1]
try:
    skills = json.load(sys.stdin)
except Exception:
    print("")
    raise SystemExit(0)
for skill in skills:
    if skill.get("name") == want:
        print(skill.get("location") or "")
        raise SystemExit(0)
print("")
PY
# Measured on 1.18.31: `opencode debug skill` cuts its stdout at 65,536 bytes when stdout is
# a pipe and writes all of it to a file, so the listing is captured by redirection, never
# through a pipe (finding Q-F2 in RESULTS.md).
SKILLS_JSON="${TMPDIR:-/tmp}/recheck-v2-skills-$$.json"
( cd "$SETUP" && "$OC" debug skill 2>/dev/null > "$SKILLS_JSON" ) || true
LOADED=$(/usr/bin/python3 "${TMPDIR:-/tmp}/recheck-v2-loaded-$$.py" "$SKILL" < "$SKILLS_JSON" || echo "")
rm -f "${TMPDIR:-/tmp}/recheck-v2-loaded-$$.py" "$SKILLS_JSON"

DIFF=$(diff -r -x '__pycache__' "$CANON" "$INSTALLED" 2>&1 || true)

CANON_ID=$(cd "$PLUGIN_ROOT" && uv run "$CANON/scripts/recheck.py" skill-identity 2>/dev/null || echo '{}')
INST_ID=$(uv run "$INSTALLED/scripts/recheck.py" skill-identity 2>/dev/null || echo '{}')

/usr/bin/python3 - "$CANON" "$INSTALLED" "$LOADED" "$DIFF" "$CANON_ID" "$INST_ID" <<'PY'
import json, os, re, sys

canon, installed, loaded, diff_text, canon_id, inst_id = sys.argv[1:7]
findings = []


def frontmatter(path):
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---\n"):
        return None
    block = text.split("\n---\n", 1)[0][4:]
    out = {}
    key = None
    for line in block.split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and not line.startswith(" "):
            key = m.group(1)
            out[key] = m.group(2).strip()
        elif key and line.startswith("  "):
            m2 = re.match(r"^\s+([A-Za-z_][\w-]*):\s*(.*)$", line)
            if m2:
                out["%s.%s" % (key, m2.group(1))] = m2.group(2).strip()
            else:
                out[key] = (out.get(key, "") + " " + line.strip()).strip()
    return out


cf = frontmatter(os.path.join(canon, "SKILL.md")) or {}
inf = frontmatter(os.path.join(installed, "SKILL.md")) or {}
fm_fields = {}
for field in ("name", "description", "metadata.version"):
    fm_fields[field] = {"canonical": cf.get(field), "installed": inf.get(field),
                        "equal": cf.get(field) == inf.get(field) and cf.get(field) is not None}
    if not fm_fields[field]["equal"]:
        findings.append("frontmatter field %s differs or is missing" % field)

link = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# Astra finding 10: SKILL.md and the adapter index name their references in backticks, not in
# Markdown links, so a link-only check verified none of the paths that actually matter. A
# backticked token is a candidate reference when it is a plain relative path; it is resolved
# against the file's own directory first, then against the installed root (SKILL.md spells
# them from the skill root, adapters/README.md from its own directory).
code_path = re.compile(r"`([^`\s]+)`")
plain_path = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
outside = []
unresolved = []
symlinked = []
checked = 0
paths_checked = 0
targets = [os.path.join(installed, "SKILL.md"),
           os.path.join(installed, "adapters", "README.md")]
refs = os.path.join(installed, "references")
if os.path.isdir(refs):
    targets += [os.path.join(refs, n) for n in sorted(os.listdir(refs)) if n.endswith(".md")]
adapters = os.path.join(installed, "adapters")
if os.path.isdir(adapters):
    for name in sorted(os.listdir(adapters)):
        profile = os.path.join(adapters, name, "profile.md")
        if os.path.isfile(profile):
            targets.append(profile)
root = os.path.realpath(installed)


def contained(resolved):
    return resolved == root or resolved.startswith(root + os.sep)


def any_link(path):
    """True when `path`, or any component of it below the installed root, is a symlink."""
    path = os.path.abspath(path)
    while True:
        if os.path.islink(path):
            return True
        parent = os.path.dirname(path)
        if parent == path or os.path.realpath(parent) == root or len(parent) <= len(installed):
            return False
        path = parent


for path in targets:
    if not os.path.isfile(path):
        outside.append("%s: missing" % os.path.relpath(path, installed))
        continue
    text = open(path, encoding="utf-8").read()
    here = os.path.dirname(path)
    for href in link.findall(text):
        href = href.split("#", 1)[0].strip()
        if not href or "://" in href or href.startswith("mailto:"):
            continue
        checked += 1
        candidate = os.path.join(here, href)
        resolved = os.path.realpath(candidate)
        if not contained(resolved):
            outside.append("%s -> %s (link, resolves to %s)"
                           % (os.path.relpath(path, installed), href, resolved))
        elif not os.path.exists(resolved):
            outside.append("%s -> %s (link, does not exist)"
                           % (os.path.relpath(path, installed), href))
        elif any_link(candidate):
            symlinked.append("%s -> %s (link target is reached through a symlink)"
                             % (os.path.relpath(path, installed), href))
    for token in code_path.findall(text):
        token = token.split("#", 1)[0]
        if (not plain_path.match(token) or "://" in token
                or not re.search(r"\.(md|py|json|sh|js|yaml|yml|toml)$", token)):
            continue
        candidates = [os.path.join(here, token), os.path.join(installed, token)]
        found = None
        for candidate in candidates:
            if os.path.lexists(candidate):
                found = candidate
                break
        if found is None:
            # a run artifact or an example path, not a reference into the package
            unresolved.append("%s: `%s`" % (os.path.relpath(path, installed), token))
            continue
        paths_checked += 1
        resolved = os.path.realpath(found)
        if not contained(resolved):
            outside.append("%s -> `%s` (backticked path, resolves to %s)"
                           % (os.path.relpath(path, installed), token, resolved))
        elif any_link(found):
            symlinked.append("%s -> `%s` (backticked path is reached through a symlink)"
                             % (os.path.relpath(path, installed), token))
if outside:
    findings.append("references that do not resolve inside the installed root: %s" % outside)
if symlinked:
    findings.append("references reached through a symlink: %s" % symlinked)

# Astra finding 10 again: identical bytes behind a symlink pass `diff -r`, so the whole
# installed tree is swept for symlinks rather than only the folder and its SKILL.md.
tree_symlinks = []
for base, dirs, names in os.walk(installed):
    for name in list(dirs) + names:
        candidate = os.path.join(base, name)
        if os.path.islink(candidate):
            tree_symlinks.append(os.path.relpath(candidate, installed))
if tree_symlinks:
    findings.append("symlinks inside the installed package: %s" % sorted(tree_symlinks))


def load(text):
    try:
        return json.loads(text)
    except Exception:
        return {}


cid, iid = load(canon_id), load(inst_id)
same_content = bool(cid.get("content_sha256")) and cid.get("content_sha256") == iid.get("content_sha256")
if not same_content:
    findings.append("content_sha256 differs: canonical %s, installed %s"
                    % (cid.get("content_sha256"), iid.get("content_sha256")))

is_copy = not os.path.islink(installed) and not os.path.islink(os.path.join(installed, "SKILL.md"))
if not is_copy:
    findings.append("the installed skill folder or its SKILL.md is a symlink, not a copy")

diff_empty = diff_text.strip() == ""
if not diff_empty:
    findings.append("diff -r against the canonical folder is not empty")

if not loaded:
    findings.append("the harness does not list the skill (opencode debug skill)")
elif os.path.realpath(os.path.dirname(loaded)) != root:
    findings.append("the harness loads the skill from %s, not from %s" % (loaded, installed))

print(json.dumps({
    "ok": not findings,
    "installed_path": installed,
    "loaded_from": loaded or None,
    "diff_empty": diff_empty,
    "diff": diff_text.strip().split("\n") if diff_text.strip() else [],
    "frontmatter": fm_fields,
    "links_checked": checked,
    "backticked_paths_checked": paths_checked,
    "backticked_tokens_not_package_paths": sorted(unresolved),
    "links_outside_root": outside,
    "references_through_symlinks": symlinked,
    "symlinks_in_package": sorted(tree_symlinks),
    "identity": {"canonical": cid, "installed": iid,
                 "content_sha256_equal": same_content,
                 "note": "E9-16: version and commit come from the packaging and are recorded, never compared"},
    "is_copy_not_symlink": is_copy,
    "findings": findings,
}, indent=2, sort_keys=True))
sys.exit(0 if not findings else 4)
PY
