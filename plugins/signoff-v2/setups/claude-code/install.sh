#!/bin/sh
# Install this core into an isolated Claude Code setup (E13 slice 3, brief 3.3).
#
# Adapted from plugins/recheck-v2/setups/claude-code/install.sh (E9 lane C). Byte-identical in
# build-v2 and signoff-v2: the core is this script's own plugin folder, never configured.
#
# Usage: install.sh --home DIR      (or <CORE>_CLAUDE_HOME=DIR install.sh, e.g. BUILD_V2_CLAUDE_HOME)
#
# The home is REQUIRED and has no default, so two setups never share one by accident, and it may
# never be the live ~/.claude or the pilot's ~/.local/share/skills-v2-pilot. Inside it: config/
# (CLAUDE_CONFIG_DIR) and marketplace/, this setup's own marketplace, whose entries are symlinks
# to the worktree's plugin folders: the core, records, and for signoff-v2 readers (the repo's
# marketplace.json is the control room's and does not list the v2 cores). Every plugin is
# uninstalled, its cache folder cleared, and installed again, so the cache is this checkout.
# Writes <home>/install.json and prints it. Exit 0 every command succeeded, 2 usage, 3 claude is
# missing, 1 a marketplace or install command failed or reported an outcome other than ok (the
# record still lands, with ok false and the failing commands named). No sign-in is read or copied:
# Claude Code keeps its sign-in in the macOS Keychain and an isolated config dir has none.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
PLUGINS_DIR=$(CDPATH= cd -- "$PLUGIN_ROOT/.." && pwd -P)
REPO_ROOT=$(CDPATH= cd -- "$PLUGINS_DIR/.." && pwd -P)
CORE=$(basename -- "$PLUGIN_ROOT")
VAR=$(printf '%s' "$CORE" | tr 'a-z-' 'A-Z_')_CLAUDE_HOME
SETUP_HOME=$(eval "printf '%s' \"\${$VAR:-}\"")
export PYTHONDONTWRITEBYTECODE=1

while [ $# -gt 0 ]; do
  case "$1" in
    --home) [ $# -ge 2 ] || { echo "install.sh: --home takes a directory" >&2; exit 2; }
            SETUP_HOME="$2"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "install.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$SETUP_HOME" ] || { echo "install.sh: name the isolated home: --home DIR or $VAR" >&2; exit 2; }
command -v claude >/dev/null 2>&1 || { echo "install.sh: claude is not on PATH" >&2; exit 3; }
mkdir -p "$SETUP_HOME"
SETUP_HOME=$(CDPATH= cd -- "$SETUP_HOME" && pwd -P)
for forbidden in "$HOME/.claude" "$HOME/.local/share/skills-v2-pilot" "$HOME/.local/share/skills-v2-locked"; do
  case "$SETUP_HOME/" in "$forbidden"/*) echo "install.sh: $SETUP_HOME is under $forbidden, which no setup may touch" >&2; exit 2 ;; esac
done

case "$CORE" in
  signoff-v2) PLUGINS="$CORE records readers" ;;
  *) PLUGINS="$CORE records" ;;
esac
CONFIG_DIR="$SETUP_HOME/config"
MARKET="$SETUP_HOME/marketplace"
MARKET_NAME="$CORE-setup"
export CLAUDE_CONFIG_DIR="$CONFIG_DIR"
mkdir -p "$CONFIG_DIR" "$MARKET/.claude-plugin"

# A marketplace entry's source must resolve inside the marketplace root (the pilot measured an
# absolute path and a `..` path both rejected), so the entries are symlinks to the worktree.
ENTRIES=""
for plugin in $PLUGINS; do
  ln -sfn "$PLUGINS_DIR/$plugin" "$MARKET/$plugin"
  ENTRIES="$ENTRIES{ \"name\": \"$plugin\", \"source\": \"./$plugin\" },"
done
cat > "$MARKET/.claude-plugin/marketplace.json" <<JSON
{
  "name": "$MARKET_NAME",
  "owner": { "name": "skills v2 setup" },
  "description": "Isolated marketplace of the $CORE Claude Code setup: symlinks to the worktree's plugin folders.",
  "plugins": [ ${ENTRIES%,} ]
}
JSON

WORK=$(mktemp -d "${TMPDIR:-/tmp}/$CORE-install.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM
: > "$WORK/failures"
: > "$WORK/results"
CLAUDE_VERSION=$(claude --version 2>/dev/null | awk '{print $1}')

status=0
claude plugin marketplace add "$MARKET" >"$WORK/m.out" 2>&1 || status=$?
if [ "$status" -ne 0 ]; then
  # A rerun finds the marketplace already added; an update is then the same step.
  ustatus=0
  claude plugin marketplace update "$MARKET_NAME" >>"$WORK/m.out" 2>&1 || ustatus=$?
  [ "$ustatus" -eq 0 ] || echo "marketplace add/update $MARKET_NAME: exit $status/$ustatus" >> "$WORK/failures"
fi
cat "$WORK/m.out" >&2

for plugin in $PLUGINS; do
  claude plugin uninstall "$plugin@$MARKET_NAME" >/dev/null 2>&1 || true
  # `uninstall` leaves the cache folder on disk (the pilot's E10-24), so it is cleared here.
  find "$CONFIG_DIR/plugins/cache/$MARKET_NAME" -mindepth 1 -maxdepth 1 -type d -name "$plugin" -print0 2>/dev/null \
    | xargs -0 python3 -c 'import shutil,sys; [shutil.rmtree(p) for p in sys.argv[1:]]' || true
done
for plugin in $PLUGINS; do
  spec="$plugin@$MARKET_NAME"
  st=0
  claude plugin install "$spec" --json -y > "$WORK/out" 2>&1 || st=$?
  line=$(head -1 "$WORK/out")
  echo "$spec: exit $st: $line" >&2
  if [ "$st" -ne 0 ]; then
    echo "install $spec: exit $st" >> "$WORK/failures"
  elif ! printf '%s' "$line" | grep -q '"outcome":"ok"'; then
    echo "install $spec: outcome is not ok" >> "$WORK/failures"
  fi
  printf '%s\t%s\t%s\n' "$spec" "$st" "$line" >> "$WORK/results"
done

python3 - "$SETUP_HOME" "$CORE" "$CLAUDE_VERSION" "$REPO_ROOT" "$MARKET_NAME" "$WORK/results" "$WORK/failures" <<'PY'
import json, os, subprocess, sys
home, core, version, repo, market, results, failures = sys.argv[1:8]
rows = []
for line in open(results, encoding="utf-8").read().splitlines():
    spec, status, first = (line.split("\t") + ["", ""])[:3]
    rows.append({"plugin": spec, "exit": int(status), "first_line": first})
failed = [l for l in open(failures, encoding="utf-8").read().splitlines() if l.strip()]
cache = os.path.join(home, "config", "plugins", "cache", market)
installed = sorted(os.path.join(cache, p, v) for p in (os.listdir(cache) if os.path.isdir(cache) else [])
                   for v in os.listdir(os.path.join(cache, p)))
def git(*args):
    proc = subprocess.run(["git", "-C", repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stdout.decode().strip() or None
doc = {"core": core, "harness": "claude-code", "setup_home": home,
       "config_dir": os.path.join(home, "config"), "marketplace": market,
       "claude_version": version, "repo_root": repo, "commit": git("rev-parse", "HEAD"),
       "installs": rows, "installed_plugin_dirs": installed, "ok": not failed,
       "failed_commands": failed}
with open(os.path.join(home, "install.json"), "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
print(json.dumps(doc, indent=2))
if failed:
    sys.stderr.write("install.sh: the setup is not installed: %s\n" % "; ".join(failed))
    sys.exit(1)
PY
