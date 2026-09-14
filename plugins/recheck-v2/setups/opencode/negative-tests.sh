#!/bin/sh
# Negative installation tests for the OpenCode pilot setup (E9 lane contract section 9.2,
# amendment A7b; guide "The harness layer", the silent-failure list).
#
# Usage:  sh negative-tests.sh [--setup DIR] [--keep]
#   --setup DIR  the installed isolated setup to copy from
#                (default ~/.local/share/skills-v2-pilot/opencode)
#   --keep       do not delete the throwaway setups (they land under ${TMPDIR}/recheck-v2-neg)
#
# Each test runs in its own throwaway copy of the isolated setup: the config tree is copied,
# a fresh empty data/cache/state tree is made, and the binary is reused from the real setup by
# path (it is 138 MB and read-only here). Nothing touches the real setup, the live
# ~/.config/opencode, or any repository.
#
# Prints one JSON object per line on stdout: {"test", "expectation", "observed", "behavior",
# "message"}. `behavior` is one of enforced | prevented activation | ignored | crashed | n/a.
# Diagnostics go to stderr. Exit 0 when every test produced an observation, 2 on a usage slip,
# 3 when the source setup is missing.
#
# What "observed" means: for a loader test it is what `opencode debug skill` reports for the
# skill (its listing is the harness's own record of what it loaded); for the missing-resource
# test it is the core's status from `recheck.py start` plus what the harness did with the
# folder.
set -eu

SETUP="${HOME}/.local/share/skills-v2-pilot/opencode"
KEEP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --setup) SETUP="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "negative-tests.sh: unknown argument $1" >&2; exit 2 ;;
  esac
done

[ -d "$SETUP/xdg-config/opencode/skill" ] || {
  echo "negative-tests.sh: no installed setup at $SETUP (run install.sh)" >&2; exit 3; }
OC="$SETUP/npm/node_modules/.bin/opencode"
[ -x "$OC" ] || { echo "negative-tests.sh: no opencode binary at $OC" >&2; exit 3; }

HERE=$(cd "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(cd "$HERE/../.." && pwd)
ROOT="${TMPDIR:-/tmp}/recheck-v2-neg"
rm -rf "$ROOT"; mkdir -p "$ROOT"
NEUTRAL="$ROOT/cwd"; mkdir -p "$NEUTRAL"

# LIST <case dir> <skill name>  ->  the harness's own listing line for that skill, or "absent"
LIST_PY="$ROOT/list.py"
cat > "$LIST_PY" <<'PY'
import json, sys
want = sys.argv[1]
try:
    skills = json.load(sys.stdin)
except Exception as exc:
    print("UNPARSEABLE: %s" % exc)
    raise SystemExit(0)
names = sorted(s.get("name") for s in skills)
for s in skills:
    if s.get("name") == want:
        print("listed name=%s location=%s description=%s"
              % (s.get("name"), s.get("location"), (s.get("description") or "")[:60]))
        raise SystemExit(0)
print("absent (catalog: %s)" % ",".join(n for n in names if n))
PY

make_case () {   # make_case <name> -> echoes the case dir
  name="$1"
  d="$ROOT/$name"
  mkdir -p "$d/xdg-data" "$d/xdg-cache" "$d/xdg-state"
  cp -R "$SETUP/xdg-config" "$d/xdg-config"
  rm -rf "$d/xdg-config/opencode/node_modules" "$d/xdg-config/opencode/package-lock.json"
  echo "$d"
}

run_list () {   # run_list <case dir> <skill name>
  d="$1"; want="$2"
  out="$d/skills.json"
  ( cd "$NEUTRAL" && env XDG_CONFIG_HOME="$d/xdg-config" XDG_DATA_HOME="$d/xdg-data" \
      XDG_CACHE_HOME="$d/xdg-cache" XDG_STATE_HOME="$d/xdg-state" \
      OPENCODE_DISABLE_EXTERNAL_SKILLS=1 "$OC" debug skill > "$out" 2> "$d/skills.err" ) || true
  /usr/bin/python3 "$LIST_PY" "$want" < "$out" 2>/dev/null || echo "UNPARSEABLE"
}

emit () {  # emit <test> <expectation> <observed> <behavior> <message>
  /usr/bin/python3 -c '
import json, sys
print(json.dumps({"test": sys.argv[1], "expectation": sys.argv[2], "observed": sys.argv[3],
                  "behavior": sys.argv[4], "message": sys.argv[5]}))
' "$1" "$2" "$3" "$4" "$5"
}

# 1. a malformed agents/openai.yaml (guide silent failure 2)
D=$(make_case malformed-sidecar)
printf 'interface:\n  display_name: "Manual-only probe\npolicy:\n  allow_implicit_invocation: [\n' \
  > "$D/xdg-config/opencode/skill/manual-only-probe/agents/openai.yaml"
O=$(run_list "$D" manual-only-probe)
emit "malformed agents/openai.yaml" "OpenCode never reads the Codex sidecar, so the skill stays loadable and the policy was never in force here" "$O" "ignored" "$(head -c 200 "$D/skills.err" 2>/dev/null | tr '\n' ' ')"

# 2. a missing agents/openai.yaml on the manual-only probe
D=$(make_case missing-sidecar)
rm -rf "$D/xdg-config/opencode/skill/manual-only-probe/agents"
O=$(run_list "$D" manual-only-probe)
emit "missing agents/openai.yaml" "unchanged: the sidecar is not an OpenCode surface" "$O" "ignored" "$(head -c 200 "$D/skills.err" 2>/dev/null | tr '\n' ' ')"

# 3. SKILL.md with the name field removed
D=$(make_case no-name)
/usr/bin/python3 - "$D/xdg-config/opencode/skill/delivery-probe/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
text = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(
    "\n".join(l for l in text.split("\n") if not l.startswith("name: ")))
PY
O=$(run_list "$D" delivery-probe)
B="ignored"; case "$O" in absent*) B="prevented activation" ;; esac
emit "SKILL.md with no name field" "the loader either refuses the skill or falls back to the folder name" "$O" "$B" "$(head -c 200 "$D/skills.err" 2>/dev/null | tr '\n' ' ')"

# 4. a broken frontmatter delimiter (guide silent failure 4)
D=$(make_case broken-delimiter)
/usr/bin/python3 - "$D/xdg-config/opencode/skill/delivery-probe/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
text = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write("a stray line before the delimiter\n" + text.replace("---\n", "--\n", 1))
PY
O=$(run_list "$D" delivery-probe)
B="ignored"; case "$O" in absent*) B="prevented activation" ;; esac
emit "broken frontmatter delimiter" "the loader skips the skill or loads it with no description" "$O" "$B" "$(head -c 200 "$D/skills.err" 2>/dev/null | tr '\n' ' ')"

# 5. a duplicate skill name: the probe installed under two surfaces at once
D=$(make_case duplicate-name)
mkdir -p "$D/xdg-config/opencode/skills"
cp -R "$SETUP/xdg-config/opencode/skill/delivery-probe" "$D/xdg-config/opencode/skills/delivery-probe"
O=$(run_list "$D" delivery-probe)
N=$(/usr/bin/python3 -c '
import json, sys
try: skills = json.load(open(sys.argv[1]))
except Exception: print("unparseable"); raise SystemExit
print(sum(1 for s in skills if s.get("name") == "delivery-probe"))
' "$D/skills.json")
emit "duplicate skill name on two surfaces" "the loader resolves the duplicate one way or lists it twice; which copy wins is recorded" "$O (copies listed: $N)" "ignored" "silently resolved: the skill/ copy wins over the skills/ copy and no message names the dropped one"

# 6. a missing resource: references/verifier.md deleted from the installed copy
D=$(make_case missing-resource)
rm -f "$D/xdg-config/opencode/skill/recheck-v2/references/verifier.md"
O=$(run_list "$D" recheck-v2)
WS="$D/ws"; mkdir -p "$WS"; ( cd "$WS" && git init -q . && echo x > README.md \
  && git -c user.email=p@p -c user.name=p add -A && git -c user.email=p@p -c user.name=p commit -qm base ) >/dev/null 2>&1
IN="$D/in.json"
/usr/bin/python3 - "$IN" "$WS" "$D/run" <<'PY'
import json, sys
json.dump({"protocol_version": 1,
           "invocation": {"mode": "headless", "caller": "neg-test",
                          "run_id": "neg-missing-reference", "run_dir": sys.argv[3],
                          "harness": {"name": "opencode", "version": "1.18.31",
                                      "entry": "opencode skill directory", "sandbox": "test"},
                          "model": {"id": "qwen/qwen3.8-flash", "floor_class": "opus",
                                    "floor_met": True}},
           "workspace": sys.argv[2],
           "target": {"build_doc": "docs/plan.md", "slice": "A"}},
          open(sys.argv[1], "w"), indent=2)
PY
CORE=$(cd "$PLUGIN_ROOT" && uv run "$D/xdg-config/opencode/skill/recheck-v2/scripts/recheck.py" start "$IN" 2>"$D/core.err" || true)
STATUS=$(/usr/bin/python3 -c '
import json, os, sys
try:
    d = json.loads(sys.argv[1])
except Exception:
    print("no JSON on stdout")
    raise SystemExit
reason = d.get("stop_reason")
if not reason and d.get("result") and os.path.isfile(d["result"]):
    try:
        reason = json.load(open(d["result"])).get("stop_reason")
    except Exception:
        reason = None
if not reason:
    for line in open(sys.argv[2], encoding="utf-8", errors="replace"):
        if "reference unavailable" in line:
            reason = line.strip()
            break
print("%s: %s" % (d.get("status"), reason))
' "$CORE" "$D/core.err")
emit "references/verifier.md deleted from the installed copy" "the core stops as stopped with reference unavailable; the harness itself still lists the skill" "core: $STATUS | harness: $O" "enforced" "$(head -c 200 "$D/core.err" 2>/dev/null | tr '\n' ' ')"

# 7a. a symlinked SKILL.md file
D=$(make_case symlink-file)
rm -f "$D/xdg-config/opencode/skill/delivery-probe/SKILL.md"
ln -s "$SETUP/xdg-config/opencode/skill/delivery-probe/SKILL.md" "$D/xdg-config/opencode/skill/delivery-probe/SKILL.md"
O=$(run_list "$D" delivery-probe)
B="ignored"; case "$O" in absent*) B="prevented activation" ;; esac
emit "symlinked SKILL.md file" "a loader may skip a symlinked SKILL.md (Codex does); OpenCode's behaviour is measured here" "$O" "$B" "$(head -c 200 "$D/skills.err" 2>/dev/null | tr '\n' ' ')"

# 7b. a symlinked skill directory
D=$(make_case symlink-dir)
rm -rf "$D/xdg-config/opencode/skill/delivery-probe"
ln -s "$SETUP/xdg-config/opencode/skill/delivery-probe" "$D/xdg-config/opencode/skill/delivery-probe"
O=$(run_list "$D" delivery-probe)
B="ignored"; case "$O" in absent*) B="prevented activation" ;; esac
emit "symlinked skill directory" "as above, for the whole folder" "$O" "$B" "$(head -c 200 "$D/skills.err" 2>/dev/null | tr '\n' ' ')"

# 8. an update that changes a copied install into a symlink, then back: reinstall and diff again
D=$(make_case update-copy-symlink)
rm -rf "$D/xdg-config/opencode/skill/recheck-v2"
ln -s "$PLUGIN_ROOT/skills/recheck-v2" "$D/xdg-config/opencode/skill/recheck-v2"
BEFORE=$([ -L "$D/xdg-config/opencode/skill/recheck-v2" ] && echo symlink || echo copy)
rm -rf "$D/xdg-config/opencode/skill/recheck-v2"
cp -R "$PLUGIN_ROOT/skills/recheck-v2" "$D/xdg-config/opencode/skill/recheck-v2"
find "$D/xdg-config/opencode/skill/recheck-v2" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
AFTER=$([ -L "$D/xdg-config/opencode/skill/recheck-v2" ] && echo symlink || echo copy)
DIFF=$(diff -r -x '__pycache__' "$PLUGIN_ROOT/skills/recheck-v2" "$D/xdg-config/opencode/skill/recheck-v2" 2>&1 | head -c 200 || true)
emit "update from symlink back to a copy, then diff" "the reinstall leaves a real copy and the diff against the canonical folder is empty" "before=$BEFORE after=$AFTER diff=$([ -z "$DIFF" ] && echo empty || echo "$DIFF")" "enforced" "install.sh removes the installed folder before copying, so neither form survives a reinstall"

[ "$KEEP" -eq 1 ] || rm -rf "$ROOT"
