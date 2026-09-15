#!/bin/sh
# The negative installation tests of E9 section 9.2 / amendment A7b, each in a
# throwaway copy of the isolated pilot setup.
#
# Usage: negative-tests.sh [--pilot-home DIR] [--out DIR] [--live]
#
# Prints one JSON line per test on stdout: {"test", "what", "observed",
# "harness_message", ...}. `observed` is one of enforced / prevented activation
# / ignored / crashed / loaded, from the harness's own output. Diagnostics go to
# stderr. Exit 0 when every test ran (a finding is data, not an error), 2 usage,
# 3 claude is missing, 1 anything else.
#
# Each case builds its own throwaway setup under <out>: a mutated copy of the
# plugin, its own marketplace, and its own CLAUDE_CONFIG_DIR, so the real pilot
# setup is never touched. The free half (the harness's validate and install
# verdicts, the core's own stop, the copy-versus-symlink diff) always runs;
# --live adds the headless sessions that read the catalog the harness actually
# built, because `claude plugin validate` reports a manifest's shape and not
# what a session loaded. Every row keeps the child's exit status beside the
# harness's own message, and an output directory that already holds a run is
# refused rather than wiped (E9-34).
#
# The --live sessions, four in all: two catalog sessions (the six loadable
# cases, then the two broken ones), one missing-resource session that installs
# the mutated plugin and asks a session what it sees, and one explicit-route
# session that types the broken-delimiter skill's own slash command. The last
# two are there because a catalog listing answers only half the question: the
# broken-delimiter skill is absent from `skills` and present in
# `slash_commands`, so automatic listing and explicit invocation are two
# measurements, not one (Astra's finding 8).

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
PILOT_HOME="${SKILLS_V2_PILOT_HOME:-$HOME/.local/share/skills-v2-pilot/claude-code}"
OUT="${TMPDIR:-/tmp}/recheck-v2-negative"
LIVE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --pilot-home) PILOT_HOME="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --live) LIVE=1; shift ;;
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "negative-tests.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

command -v claude >/dev/null 2>&1 || { echo "negative-tests.sh: claude is not on PATH" >&2; exit 3; }
if [ -e "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ]; then
  echo "negative-tests.sh: $OUT already holds a run; name a fresh --out directory" >&2
  exit 2
fi
mkdir -p "$OUT"

DELIVERY="$PLUGIN_ROOT/setups/_fixtures/delivery-probe"
MANUAL="$PLUGIN_ROOT/setups/_fixtures/manual-only-probe"

# build_case <case> <source plugin> <plugin name>  -> copies the plugin and
# builds a throwaway marketplace and config dir around it; echoes the copy path.
build_case() {
  case_id="$1"; source="$2"; name="$3"
  root="$OUT/$case_id"
  mkdir -p "$root/marketplace/.claude-plugin" "$root/config"
  cp -R "$source" "$root/marketplace/$name"
  # the copied plugin.json still carries the source plugin's name, and the
  # catalog keys a skill by <plugin>:<skill>, so give every copy its own plugin
  # name: otherwise two cases collide in one listing and neither can be read.
  python3 - "$root/marketplace/$name/.claude-plugin/plugin.json" "$name" <<'PYNAME'
import json, sys
path, new = sys.argv[1:3]
with open(path, "r", encoding="utf-8") as handle:
    document = json.load(handle)
document["name"] = new
with open(path, "w", encoding="utf-8") as handle:
    json.dump(document, handle, indent=2)
PYNAME
  cat > "$root/marketplace/.claude-plugin/marketplace.json" <<JSON
{ "name": "neg-$case_id", "owner": { "name": "pilot" },
  "description": "Throwaway marketplace for the E9 lane C negative test $case_id.",
  "plugins": [ { "name": "$name", "source": "./$name" } ] }
JSON
  echo "$root/marketplace/$name"
}

# install_case <case> -> validate + install into the throwaway config dir,
# echoing the harness's own messages on fd 3.
install_case() {
  case_id="$1"; name="$2"
  root="$OUT/$case_id"
  : > "$root/exits.txt"
  keep() {  # keep <label> <file> <command...>: run it, record its exit status
    label="$1"; file="$2"; shift 2
    status=0
    "$@" > "$file" 2>&1 || status=$?
    echo "$label: exit $status" >> "$root/exits.txt"
  }
  keep marketplace-add "$root/marketplace-add.txt" \
    env CLAUDE_CONFIG_DIR="$root/config" claude plugin marketplace add "$root/marketplace"
  keep validate "$root/validate.txt" \
    env CLAUDE_CONFIG_DIR="$root/config" claude plugin validate "$root/marketplace/$name"
  # the manifest validator says nothing about a SKILL.md, so validate the skill
  # folder as well: that is where the harness reports a broken frontmatter or a
  # component it could not read.
  keep validate-skills "$root/validate-skills.txt" \
    env CLAUDE_CONFIG_DIR="$root/config" claude plugin validate "$root/marketplace/$name/skills"
  keep install "$root/install.txt" \
    env CLAUDE_CONFIG_DIR="$root/config" claude plugin install "$name@neg-$case_id" --json -y
}

emit() {
  python3 - "$@" <<'PY'
import json, os, sys
case_id, what, observed, root = sys.argv[1:5]
extra = {}
for pair in sys.argv[5:]:
    key, _, value = pair.partition("=")
    extra[key] = value
messages = {}
for name in ("validate.txt", "validate-skills.txt", "install.txt", "marketplace-add.txt",
             "catalog.txt", "core.txt", "diff.txt", "exits.txt", "live.txt",
             "install-2.txt", "core-source.txt"):
    path = os.path.join(root, name)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read().strip()
        if text:
            messages[name[:-4]] = text[:600]
document = {"test": case_id, "what": what, "observed": observed,
            "harness_message": messages, "setup": root}
document.update(extra)
sys.stdout.write(json.dumps(document) + "\n")
PY
}

verdict() {  # verdict <root>: what the install alone establishes
  if ! grep -q '"outcome":"ok"' "$1/install.txt" 2>/dev/null; then echo crashed; return; fi
  if [ -z "$(find "$1/config/plugins/cache" -name SKILL.md 2>/dev/null | head -1)" ]; then
    echo "prevented activation (the installed copy holds no SKILL.md)"
  else
    echo "installed (the catalog line below says whether the skill loaded)"
  fi
}

# ---------------------------------------------------------------- 1 malformed sidecar
COPY=$(build_case malformed-sidecar "$DELIVERY" probe-malformed-sidecar)
printf ': : broken: [yaml\n  - not: valid\n' > "$COPY/skills/delivery-probe/agents/openai.yaml"
install_case malformed-sidecar probe-malformed-sidecar
emit malformed-sidecar "a malformed agents/openai.yaml beside the skill" \
  "$(verdict "$OUT/malformed-sidecar")" "$OUT/malformed-sidecar" \
  "expectation=Claude reads frontmatter and never the Codex sidecar, so the skill should load unchanged"

# ---------------------------------------------------------------- 2 missing sidecar
COPY=$(build_case missing-sidecar "$MANUAL" probe-missing-sidecar)
rm -f "$COPY/skills/manual-only-probe/agents/openai.yaml"
install_case missing-sidecar probe-missing-sidecar
emit missing-sidecar "the manual-only probe with no agents/openai.yaml" \
  "$(verdict "$OUT/missing-sidecar")" "$OUT/missing-sidecar" \
  "expectation=the restriction rides on disable-model-invocation in the frontmatter, not the sidecar"

# ---------------------------------------------------------------- 3 name removed
COPY=$(build_case no-name "$DELIVERY" probe-no-name)
mv "$COPY/skills/delivery-probe" "$COPY/skills/probe-no-name"
grep -v '^name:' "$COPY/skills/probe-no-name/SKILL.md" > "$COPY/skills/probe-no-name/SKILL.md.new"
mv "$COPY/skills/probe-no-name/SKILL.md.new" "$COPY/skills/probe-no-name/SKILL.md"
install_case no-name probe-no-name
emit no-name "SKILL.md with the name field removed" \
  "$(verdict "$OUT/no-name")" "$OUT/no-name" \
  "expectation=a skill with no name should be refused, not loaded under a guessed name"

# ---------------------------------------------------------------- 4 broken delimiter
COPY=$(build_case broken-delimiter "$DELIVERY" probe-broken-delim)
mv "$COPY/skills/delivery-probe" "$COPY/skills/probe-broken-delim"
python3 - "$COPY/skills/probe-broken-delim/SKILL.md" <<'PY'
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    text = handle.read()
with open(path, "w", encoding="utf-8") as handle:
    handle.write("--\n" + text[4:])
PY
install_case broken-delimiter probe-broken-delim
emit broken-delimiter "SKILL.md whose opening frontmatter delimiter is broken" \
  "$(verdict "$OUT/broken-delimiter")" "$OUT/broken-delimiter" \
  "expectation=the loader should skip the skill rather than read the frontmatter as prose"

# ---------------------------------------------------------------- 5 duplicate skill name
COPY=$(build_case duplicate-a "$DELIVERY" delivery-probe-a)
install_case duplicate-a delivery-probe-a
COPY=$(build_case duplicate-b "$DELIVERY" delivery-probe-b)
install_case duplicate-b delivery-probe-b
emit duplicate-name "the same skill name installed twice, under two plugin names" \
  "$(verdict "$OUT/duplicate-b")" "$OUT/duplicate-b" \
  "expectation=both plugins install; the catalog shows how the harness resolves the collision" \
  "second_setup=$OUT/duplicate-a"

# ---------------------------------------------------------------- 6 missing resource
# Installed through the harness like every other case, not only copied: E9
# section 9.2 asks what the harness does with a package whose runtime reference
# is gone, and a copy on disk answers only the core's half (Astra's finding 8).
ROOT="$OUT/missing-resource"
COPY=$(build_case missing-resource "$PLUGIN_ROOT" probe-missing-resource)
rm -f "$COPY/skills/recheck-v2/references/verifier.md"
install_case missing-resource probe-missing-resource
MISSING_CACHE=$(find "$ROOT/config/plugins/cache" -maxdepth 3 -mindepth 3 -type d 2>/dev/null | head -1)
if [ -n "$MISSING_CACHE" ] && [ -d "$MISSING_CACHE/skills/recheck-v2" ]; then
  CORE_UNDER_TEST="$MISSING_CACHE"
else
  CORE_UNDER_TEST="$COPY"
fi
echo "the core ran from: $CORE_UNDER_TEST" > "$ROOT/core-source.txt"
CASE_INPUT="$ROOT/input.json"
python3 - "$ROOT" "$PLUGIN_ROOT" <<'PY'
import json, os, sys
root, plugin_root = sys.argv[1:3]
payload = {
    "protocol_version": 1,
    "invocation": {
        "mode": "headless", "caller": "direct",
        "run_id": "neg-missing-reference", "run_dir": os.path.join(root, "run"),
        "resume": False,
        "harness": {"name": "claude-code", "version": "0", "entry": "explicit path",
                     "sandbox": "acceptEdits"},
        "model": {"id": "claude-opus-5", "floor_class": "opus", "floor_met": True},
    },
    "workspace": plugin_root,
    "target": {"build_doc": "README.md", "slice": "A"},
}
with open(os.path.join(root, "input.json"), "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
PY
CORE_STATUS=0
uv run "$CORE_UNDER_TEST/skills/recheck-v2/scripts/recheck.py" start "$CASE_INPUT" \
  > "$ROOT/core.txt" 2>&1 || CORE_STATUS=$?
echo "core start: exit $CORE_STATUS" >> "$ROOT/exits.txt"
if ! grep -q '"outcome":"ok"' "$ROOT/install.txt" 2>/dev/null; then
  OBS="crashed (the install of this case did not report outcome ok; see exits.txt)"
elif grep -q 'reference unavailable' "$ROOT/core.txt"; then
  OBS="enforced (by the core; the harness's own half is the live row below)"
else
  OBS="ignored"
fi
emit missing-resource "references/verifier.md deleted from the plugin, installed through the harness" \
  "$OBS" "$ROOT" \
  "expectation=the core stops as stopped with stop_reason 'reference unavailable: <path>' before any work (contract section 10, check M1); the harness itself is measured in the live row" \
  "core_ran_from=$CORE_UNDER_TEST"

# ---------------------------------------------------------------- 7 symlinks
COPY=$(build_case symlink-skill-file "$DELIVERY" probe-symlink-file)
rm -f "$COPY/skills/delivery-probe/SKILL.md"
ln -s "$DELIVERY/skills/delivery-probe/SKILL.md" "$COPY/skills/delivery-probe/SKILL.md"
install_case symlink-skill-file probe-symlink-file
emit symlink-skill-file "a symlinked SKILL.md file inside the plugin" \
  "$(verdict "$OUT/symlink-skill-file")" "$OUT/symlink-skill-file" \
  "expectation=recorded, not assumed: Codex skips a symlinked SKILL.md; Claude's behaviour is this test"

COPY=$(build_case symlink-skill-dir "$DELIVERY" probe-symlink-dir)
rm -rf "$COPY/skills/delivery-probe"
ln -s "$DELIVERY/skills/delivery-probe" "$COPY/skills/delivery-probe"
install_case symlink-skill-dir probe-symlink-dir
emit symlink-skill-dir "a symlinked skill directory inside the plugin" \
  "$(verdict "$OUT/symlink-skill-dir")" "$OUT/symlink-skill-dir" \
  "expectation=install dereferences symlinks that stay inside the marketplace (the harness's own validate warning)"

# ---------------------------------------------------------------- 8 copy to symlink and back
ROOT="$OUT/update-copy-symlink"
mkdir -p "$ROOT/marketplace/.claude-plugin" "$ROOT/config"
cp -R "$DELIVERY" "$ROOT/marketplace/delivery-probe"
cat > "$ROOT/marketplace/.claude-plugin/marketplace.json" <<'JSON'
{ "name": "neg-update", "owner": { "name": "pilot" },
  "description": "Throwaway marketplace for the E9 lane C update test.",
  "plugins": [ { "name": "delivery-probe", "source": "./delivery-probe" } ] }
JSON
export CLAUDE_CONFIG_DIR="$ROOT/config"
: > "$ROOT/exits.txt"
ADD_STATUS=0
claude plugin marketplace add "$ROOT/marketplace" > "$ROOT/marketplace-add.txt" 2>&1 || ADD_STATUS=$?
echo "marketplace-add: exit $ADD_STATUS" >> "$ROOT/exits.txt"
INSTALL1_STATUS=0
claude plugin install delivery-probe@neg-update --json -y > "$ROOT/install.txt" 2>&1 || INSTALL1_STATUS=$?
echo "install-1: exit $INSTALL1_STATUS" >> "$ROOT/exits.txt"
CACHE=$(find "$ROOT/config/plugins/cache" -maxdepth 3 -mindepth 3 -type d 2>/dev/null | head -1)
{
  echo "first install: $CACHE"
  echo "is symlink: $( [ -L "$CACHE" ] && echo yes || echo no )"
  echo "SKILL.md is symlink: $( [ -L "$CACHE/skills/delivery-probe/SKILL.md" ] && echo yes || echo no )"
  diff -r -x __pycache__ "$ROOT/marketplace/delivery-probe" "$CACHE" > /dev/null 2>&1 \
    && echo "diff after install: clean" || echo "diff after install: differs"
  # the source becomes a symlink, then the plugin is reinstalled
  rm -rf "$ROOT/marketplace/delivery-probe"
  ln -s "$DELIVERY" "$ROOT/marketplace/delivery-probe"
  claude plugin uninstall delivery-probe@neg-update >/dev/null 2>&1 || true
  INSTALL2_STATUS=0
  claude plugin install delivery-probe@neg-update --json -y > "$ROOT/install-2.txt" 2>&1 \
    || INSTALL2_STATUS=$?
  echo "install-2: exit $INSTALL2_STATUS" >> "$ROOT/exits.txt"
  CACHE2=$(find "$ROOT/config/plugins/cache" -maxdepth 3 -mindepth 3 -type d 2>/dev/null | head -1)
  echo "after the source became a symlink: $CACHE2"
  echo "is symlink: $( [ -L "$CACHE2" ] && echo yes || echo no )"
  echo "SKILL.md is symlink: $( [ -L "$CACHE2/skills/delivery-probe/SKILL.md" ] && echo yes || echo no )"
  diff -r -x __pycache__ "$DELIVERY" "$CACHE2" > /dev/null 2>&1 \
    && echo "diff after reinstall: clean" || echo "diff after reinstall: differs"
} > "$ROOT/diff.txt" 2>&1
unset CLAUDE_CONFIG_DIR
# `enforced` is reachable only from two successful installs with clean diffs and
# no link in the cache: a failed install with a `differs` diff read `enforced`
# before (Astra's finding 9).
WHY=""
grep -q '"outcome":"ok"' "$ROOT/install.txt" 2>/dev/null || WHY="$WHY the first install did not report outcome ok;"
grep -q '"outcome":"ok"' "$ROOT/install-2.txt" 2>/dev/null || WHY="$WHY the second install did not report outcome ok;"
grep -q "^install-1: exit 0$" "$ROOT/exits.txt" || WHY="$WHY the first install exited non-zero;"
grep -q "^install-2: exit 0$" "$ROOT/exits.txt" || WHY="$WHY the second install exited non-zero;"
grep -q "diff after install: clean" "$ROOT/diff.txt" || WHY="$WHY the first diff is not clean;"
grep -q "diff after reinstall: clean" "$ROOT/diff.txt" || WHY="$WHY the second diff is not clean;"
if grep -q "is symlink: yes" "$ROOT/diff.txt"; then WHY="$WHY the installed copy is a link;"; fi
if [ -n "$WHY" ]; then OBS="crashed (not classifiable as enforced:$WHY)"; else OBS="enforced"; fi
emit update-copy-symlink "an update that changes the source from a copy to a symlink" \
  "$OBS" "$ROOT" \
  "expectation=the installed copy stays a real copy through the change (guide, Distribution and versioning, check 3)"

# ---------------------------------------------------------------- the live catalogs
if [ "$LIVE" -eq 1 ]; then
  RUN_ROOT="${TMPDIR:-/tmp}/recheck-v2"
  mkdir -p "$RUN_ROOT" "$OUT/catalog"
  set -- claude
  for case_id in malformed-sidecar missing-sidecar symlink-skill-file symlink-skill-dir \
                 duplicate-a duplicate-b; do
    dir=$(find "$OUT/$case_id/config/plugins/cache" -maxdepth 3 -mindepth 3 -type d 2>/dev/null | head -1)
    [ -n "$dir" ] && set -- "$@" --plugin-dir "$dir"
  done
  "$@" --setting-sources local --strict-mcp-config --settings "$PILOT_HOME/launch-settings.json" \
    --permission-prompts none --permission-mode acceptEdits \
    --output-format stream-json --verbose --print "ok" \
    < /dev/null > "$OUT/catalog/loaded.jsonl" 2> "$OUT/catalog/loaded.err" || true

  set -- claude
  for case_id in no-name broken-delimiter; do
    dir=$(find "$OUT/$case_id/config/plugins/cache" -maxdepth 3 -mindepth 3 -type d 2>/dev/null | head -1)
    [ -n "$dir" ] && set -- "$@" --plugin-dir "$dir"
  done
  "$@" --setting-sources local --strict-mcp-config --settings "$PILOT_HOME/launch-settings.json" \
    --permission-prompts none --permission-mode acceptEdits \
    --output-format stream-json --verbose --print "ok" \
    < /dev/null > "$OUT/catalog/broken.jsonl" 2> "$OUT/catalog/broken.err" || true

  # ---- the two surfaces a catalog listing cannot answer (Astra's finding 8)
  # (a) the missing-resource package, loaded into a real session: is the plugin
  #     there, is the skill listed, and what does the harness say when the model
  #     goes looking for the reference that is gone?
  MISSING_CACHE=$(find "$OUT/missing-resource/config/plugins/cache" -maxdepth 3 -mindepth 3 \
    -type d 2>/dev/null | head -1)
  if [ -n "$MISSING_CACHE" ]; then
    mkdir -p "$OUT/missing-resource/ws"
    cat > "$OUT/missing-resource/prompt.txt" <<'PROMPT'
Do not invoke any skill and do not run any recheck. Answer in three short lines: (1) the exact skill names your catalog lists, (2) the result of reading the file skills/recheck-v2/references/verifier.md inside the recheck-v2 plugin directory that was loaded for this session, quoting the tool's own message if it fails, (3) whether any other file in that plugin's references directory is readable.
PROMPT
    LIVE_STATUS=0
    sh "$SCRIPT_DIR/launch.sh" "$OUT/missing-resource/prompt.txt" "$OUT/missing-resource/ws" \
      "$OUT/missing-resource/live" --plugin-dir "$MISSING_CACHE" \
      > "$OUT/missing-resource/live.json" 2> "$OUT/missing-resource/live.err" || LIVE_STATUS=$?
    echo "live launch: exit $LIVE_STATUS" >> "$OUT/missing-resource/exits.txt"
    cp "$OUT/missing-resource/live/result.txt" "$OUT/missing-resource/live.txt" 2>/dev/null || true
    python3 - "$OUT/missing-resource" "$MISSING_CACHE" <<'PY'
import json, os, sys
root, cache = sys.argv[1:3]
launch = {}
path = os.path.join(root, "live", "launch.json")
if os.path.isfile(path):
    with open(path, "r", encoding="utf-8") as handle:
        launch = json.load(handle)
answer = ""
result = os.path.join(root, "live", "result.txt")
if os.path.isfile(result):
    with open(result, "r", encoding="utf-8", errors="replace") as handle:
        answer = handle.read().strip()
plugins = [p.get("name") for p in (launch.get("plugins") or [])]
skills = [s for s in (launch.get("skills") or []) if "recheck" in s]
sys.stdout.write(json.dumps({
    "test": "missing-resource-live",
    "what": "the mutated package loaded into a session: what the harness listed and what the "
            "model saw when it looked for the deleted reference",
    "observed": "loaded" if launch.get("skills") else "crashed",
    "plugin_listed": plugins,
    "skill_listed": skills,
    "session_id": launch.get("session_id"),
    "total_cost_usd": launch.get("total_cost_usd"),
    "model_said": answer[:1200],
    "harness_message": {"launch_problems": launch.get("problems")},
    "setup": os.path.join(root, "live"),
}) + "\n")
PY
  fi

  # (b) the broken-delimiter skill's explicit route: it is absent from `skills`
  #     and present in `slash_commands`, so the automatic listing and the
  #     explicit invocation are two different measurements.
  BROKEN_CACHE=$(find "$OUT/broken-delimiter/config/plugins/cache" -maxdepth 3 -mindepth 3 \
    -type d 2>/dev/null | head -1)
  if [ -n "$BROKEN_CACHE" ]; then
    mkdir -p "$OUT/broken-delimiter/ws"
    # Both spellings, because they answer differently: the bare name is an
    # unknown command and the namespaced one the catalog itself lists runs the
    # skill (measured 2026-09-14).
    printf '/probe-broken-delim\n' > "$OUT/broken-delimiter/prompt-bare.txt"
    printf '/probe-broken-delim:probe-broken-delim\n' > "$OUT/broken-delimiter/prompt-namespaced.txt"
    for form in bare namespaced; do
      LIVE_STATUS=0
      sh "$SCRIPT_DIR/launch.sh" "$OUT/broken-delimiter/prompt-$form.txt" \
        "$OUT/broken-delimiter/ws" "$OUT/broken-delimiter/live-$form" \
        --plugin-dir "$BROKEN_CACHE" \
        > "$OUT/broken-delimiter/live-$form.json" 2> "$OUT/broken-delimiter/live-$form.err" \
        || LIVE_STATUS=$?
      echo "live launch ($form): exit $LIVE_STATUS" >> "$OUT/broken-delimiter/exits.txt"
    done
    python3 - "$OUT/broken-delimiter" <<'PY'
import json, os, sys
root = sys.argv[1]


def read(*parts):
    path = os.path.join(root, *parts)
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read().strip()


def launch_of(form):
    text = read("live-%s" % form, "launch.json")
    return json.loads(text) if text else {}


forms = {}
for form in ("bare", "namespaced"):
    launch = launch_of(form)
    answer = read("live-%s" % form, "result.txt")
    forms[form] = {
        "command": read("prompt-%s.txt" % form),
        "session_id": launch.get("session_id"),
        "total_cost_usd": launch.get("total_cost_usd"),
        "num_turns": launch.get("num_turns"),
        "ran": "SENTINEL S01" in answer or "END-OF-PROBE" in answer,
        "answer": answer[:400],
        "stderr": read("live-%s" % form, "trace.err")[:400],
    }
launch = launch_of("namespaced") or launch_of("bare")
skills = [s for s in (launch.get("skills") or []) if "probe-broken-delim" in s]
commands = [c for c in (launch.get("slash_commands") or []) if "probe-broken-delim" in c]
ran = any(form["ran"] for form in forms.values())
sys.stdout.write(json.dumps({
    "test": "broken-delimiter-explicit-route",
    "what": "the broken-delimiter skill invoked explicitly, both spellings, against the same "
            "installed copy whose skill the catalog's `skills` list omits",
    "observed": "ran (the body reached the model through the explicit route)" if ran else
                "did not run (neither spelling produced a skill body)",
    "listed_in_skills": skills,
    "listed_in_slash_commands": commands,
    "forms": forms,
    "harness_message": {"launch_problems": launch.get("problems")},
    "setup": os.path.join(root, "live-namespaced"),
}) + "\n")
PY
  fi

  python3 - "$OUT/catalog" <<'PY'
import json, os, sys
directory = sys.argv[1]
for name in ("loaded", "broken"):
    path = os.path.join(directory, "%s.jsonl" % name)
    init = {}
    cost = None
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if record.get("type") == "system" and record.get("subtype") == "init":
                    init = record
                if record.get("type") == "result":
                    cost = record.get("total_cost_usd")
    stderr_path = os.path.join(directory, "%s.err" % name)
    stderr = ""
    if os.path.isfile(stderr_path):
        with open(stderr_path, "r", encoding="utf-8", errors="replace") as handle:
            stderr = handle.read().strip()[:600]
    listed = init.get("skills") or []
    verdicts = {}
    for case_id, plugin in (
        ("malformed-sidecar", "probe-malformed-sidecar"),
        ("missing-sidecar", "probe-missing-sidecar"),
        ("symlink-skill-file", "probe-symlink-file"),
        ("symlink-skill-dir", "probe-symlink-dir"),
        ("duplicate-name", "delivery-probe-a"),
        ("duplicate-name-b", "delivery-probe-b"),
        ("no-name", "probe-no-name"),
        ("broken-delimiter", "probe-broken-delim"),
    ):
        if not any(p.get("name") == plugin for p in (init.get("plugins") or [])):
            continue
        hit = [entry for entry in listed if entry.startswith(plugin + ":")]
        verdicts[case_id] = ("ignored (loaded as %s)" % hit[0]) if hit else \
            "prevented activation (the plugin loaded, the skill is not in the catalog)"
    sys.stdout.write(json.dumps({
        "test": "catalog-%s" % name,
        "verdicts": verdicts,
        "what": "the catalog a session built with those plugin copies loaded",
        "observed": "loaded" if init.get("skills") else "crashed",
        "plugins": init.get("plugins"),
        "skills": init.get("skills"),
        "slash_commands": [c for c in (init.get("slash_commands") or []) if "probe" in c],
        "stderr": stderr,
        "total_cost_usd": cost,
        "setup": directory,
    }) + "\n")
PY
fi
