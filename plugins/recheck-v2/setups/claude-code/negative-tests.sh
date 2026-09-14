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
# --live adds the two headless sessions that read the catalog the harness
# actually built, because `claude plugin validate` reports a manifest's shape
# and not what a session loaded.

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
rm -rf "$OUT"
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
  CLAUDE_CONFIG_DIR="$root/config" claude plugin marketplace add "$root/marketplace" \
    > "$root/marketplace-add.txt" 2>&1 || true
  CLAUDE_CONFIG_DIR="$root/config" claude plugin validate "$root/marketplace/$name" \
    > "$root/validate.txt" 2>&1 || true
  # the manifest validator says nothing about a SKILL.md, so validate the skill
  # folder as well: that is where the harness reports a broken frontmatter or a
  # component it could not read.
  CLAUDE_CONFIG_DIR="$root/config" claude plugin validate "$root/marketplace/$name/skills" \
    > "$root/validate-skills.txt" 2>&1 || true
  CLAUDE_CONFIG_DIR="$root/config" claude plugin install "$name@neg-$case_id" --json -y \
    > "$root/install.txt" 2>&1 || true
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
             "catalog.txt", "core.txt", "diff.txt"):
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
ROOT="$OUT/missing-resource"
mkdir -p "$ROOT"
cp -R "$PLUGIN_ROOT" "$ROOT/recheck-v2"
rm -f "$ROOT/recheck-v2/skills/recheck-v2/references/verifier.md"
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
uv run "$ROOT/recheck-v2/skills/recheck-v2/scripts/recheck.py" start "$CASE_INPUT" \
  > "$ROOT/core.txt" 2>&1 || true
if grep -q 'reference unavailable' "$ROOT/core.txt"; then OBS="enforced"; else OBS="ignored"; fi
emit missing-resource "references/verifier.md deleted from the installed copy" \
  "$OBS" "$ROOT" \
  "expectation=the core stops as stopped with stop_reason 'reference unavailable: <path>' before any work (contract section 10, check M1)"

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
claude plugin marketplace add "$ROOT/marketplace" > "$ROOT/marketplace-add.txt" 2>&1 || true
claude plugin install delivery-probe@neg-update --json -y > "$ROOT/install.txt" 2>&1 || true
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
  claude plugin install delivery-probe@neg-update --json -y >/dev/null 2>&1 || true
  CACHE2=$(find "$ROOT/config/plugins/cache" -maxdepth 3 -mindepth 3 -type d 2>/dev/null | head -1)
  echo "after the source became a symlink: $CACHE2"
  echo "is symlink: $( [ -L "$CACHE2" ] && echo yes || echo no )"
  echo "SKILL.md is symlink: $( [ -L "$CACHE2/skills/delivery-probe/SKILL.md" ] && echo yes || echo no )"
  diff -r -x __pycache__ "$DELIVERY" "$CACHE2" > /dev/null 2>&1 \
    && echo "diff after reinstall: clean" || echo "diff after reinstall: differs"
} > "$ROOT/diff.txt" 2>&1
unset CLAUDE_CONFIG_DIR
if grep -q "is symlink: yes" "$ROOT/diff.txt"; then OBS="crashed"; else OBS="enforced"; fi
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
