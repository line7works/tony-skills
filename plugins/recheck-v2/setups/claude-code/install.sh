#!/bin/sh
# Install the recheck-v2 pilot into an isolated Claude Code setup (E9 lane C).
#
# Creates ~/.local/share/skills-v2-pilot/claude-code/ and nothing else outside
# it: no write under ~/.claude, no write in this repository. Re-runnable.
#
# Usage: install.sh [--pilot-home DIR]
# Prints one JSON object on stdout; every command's own output goes to stderr.
# Exit 0 success, 2 usage, 3 the claude binary is missing, 1 anything else.
#
# Measured facts this script records for RESULTS.md land in
# <pilot home>/install.json.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
REPO_ROOT=$(CDPATH= cd -- "$PLUGIN_ROOT/../.." && pwd -P)
PILOT_HOME="${SKILLS_V2_PILOT_HOME:-$HOME/.local/share/skills-v2-pilot/claude-code}"

while [ $# -gt 0 ]; do
  case "$1" in
    --pilot-home) PILOT_HOME="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "install.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

command -v claude >/dev/null 2>&1 || { echo "install.sh: claude is not on PATH" >&2; exit 3; }

CONFIG_DIR="$PILOT_HOME/config"
MARKET="$PILOT_HOME/marketplace"
export CLAUDE_CONFIG_DIR="$CONFIG_DIR"
mkdir -p "$CONFIG_DIR" "$MARKET/.claude-plugin"

CLAUDE_VERSION=$(claude --version 2>/dev/null | awk '{print $1}')

# The pilot marketplace, for the two shared probes only. They are deliberately
# absent from the repo's marketplace ("Neither fixture is listed in the
# marketplace and neither leaves the isolated setups",
# setups/_fixtures/README.md), `claude plugin install` offers no
# install-by-path, and a marketplace entry's source must resolve inside the
# marketplace root (measured 2026-09-14: an absolute path and a `..` path are
# both rejected as "source: Invalid input"), so this marketplace holds symlinks
# to the worktree's fixture folders. recheck-v2 and readers come from the
# repo's own marketplace, as the lane contract says.
ln -sfn "$PLUGIN_ROOT/setups/_fixtures/delivery-probe" "$MARKET/delivery-probe"
ln -sfn "$PLUGIN_ROOT/setups/_fixtures/manual-only-probe" "$MARKET/manual-only-probe"
cat > "$MARKET/.claude-plugin/marketplace.json" <<JSON
{
  "name": "skills-v2-pilot",
  "owner": { "name": "Tony Coon" },
  "description": "Isolated pilot marketplace for the recheck-v2 E9 lane C setup: the two shared probes, symlinked from the lane worktree.",
  "plugins": [
    { "name": "delivery-probe", "source": "./delivery-probe" },
    { "name": "manual-only-probe", "source": "./manual-only-probe" }
  ]
}
JSON

run() { echo "\$ $*" >&2; "$@" >&2 2>&1 || echo "  (exit $?)" >&2; }

run claude plugin marketplace add "$REPO_ROOT"
run claude plugin marketplace update tony-skills
run claude plugin marketplace add "$MARKET"

# Neither `install` on an already-installed plugin nor `update` refreshes a
# cache copy whose version did not change (measured 2026-09-14: a new file in
# the source folder did not reach the cache through either), and
# verify-install.sh diffs the cache against the canonical folder, so the install
# is always an uninstall followed by an install.
for plugin in recheck-v2@tony-skills readers@tony-skills \
              delivery-probe@skills-v2-pilot manual-only-probe@skills-v2-pilot; do
  claude plugin uninstall "$plugin" >/dev/null 2>&1 || true
done
RECHECK_RESULT=$(claude plugin install recheck-v2@tony-skills --json -y 2>&1 | head -1 || true)
READERS_RESULT=$(claude plugin install readers@tony-skills --json -y 2>&1 | head -1 || true)
DELIVERY_RESULT=$(claude plugin install delivery-probe@skills-v2-pilot --json -y 2>&1 | head -1 || true)
MANUAL_RESULT=$(claude plugin install manual-only-probe@skills-v2-pilot --json -y 2>&1 | head -1 || true)
echo "recheck-v2@tony-skills: $RECHECK_RESULT" >&2
echo "readers@tony-skills: $READERS_RESULT" >&2
echo "delivery-probe@skills-v2-pilot: $DELIVERY_RESULT" >&2
echo "manual-only-probe@skills-v2-pilot: $MANUAL_RESULT" >&2

# The allow list the executor needs, so no prompt blocks a headless run, and the
# web tools denied at the harness so the mandate's "no web tool" is enforced and
# not only instructed. Merged into the isolated settings.json (the plugin
# commands own the rest of that file) and written standalone for launch.sh,
# which passes it with --settings because the live sign-in is not reachable from
# the isolated config directory (RESULTS.md, "Sign-in").
LAUNCH_SETTINGS="$PILOT_HOME/launch-settings.json"
cat > "$LAUNCH_SETTINGS" <<'JSON'
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": [
      "Bash",
      "Read",
      "Write",
      "Glob",
      "Grep",
      "Skill",
      "Agent",
      "Task",
      "TodoWrite"
    ],
    "deny": [
      "WebFetch",
      "WebSearch"
    ]
  },
  "includeCoAuthoredBy": false
}
JSON

python3 - "$CONFIG_DIR/settings.json" "$LAUNCH_SETTINGS" <<'PY'
import json, sys

target, source = sys.argv[1], sys.argv[2]
try:
    with open(target, "r", encoding="utf-8") as handle:
        current = json.load(handle)
except (OSError, ValueError):
    current = {}
with open(source, "r", encoding="utf-8") as handle:
    add = json.load(handle)
current["permissions"] = add["permissions"]
with open(target, "w", encoding="utf-8") as handle:
    json.dump(current, handle, indent=2)
    handle.write("\n")
PY

# readers keeps its last-pick memory in a checkout it resolves from
# $READERS_CHECKOUT (default ~/Developer/tony-skills). The pilot points it at
# its own isolated copy of that one file, so a readers call in this setup never
# writes into a repository. Nothing else of readers lives here.
mkdir -p "$PILOT_HOME/readers-checkout/plugins/readers"
[ -f "$PILOT_HOME/readers-checkout/plugins/readers/last-picks.json" ] || \
  printf '{"protocol_version": 1, "picks": {}}\n' \
    > "$PILOT_HOME/readers-checkout/plugins/readers/last-picks.json"

INSTALLED=$(find "$CONFIG_DIR/plugins/cache" -maxdepth 3 -mindepth 3 -type d 2>/dev/null | sort | tr '\n' ' ')

python3 - "$PILOT_HOME" "$CLAUDE_VERSION" "$REPO_ROOT" "$PLUGIN_ROOT" "$INSTALLED" \
  "$RECHECK_RESULT" "$READERS_RESULT" "$DELIVERY_RESULT" "$MANUAL_RESULT" <<'PY'
import json, os, subprocess, sys

(pilot, version, repo, plugin_root, installed,
 recheck, readers, delivery, manual) = sys.argv[1:10]
document = {
    "pilot_home": pilot,
    "config_dir": os.path.join(pilot, "config"),
    "claude_version": version,
    "repo_root": repo,
    "plugin_root": plugin_root,
    "commit": subprocess.check_output(
        ["git", "-C", repo, "rev-parse", "HEAD"]).decode().strip(),
    "branch": subprocess.check_output(
        ["git", "-C", repo, "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip(),
    "installed_plugin_dirs": installed.split(),
    "install_results": {
        "recheck-v2@tony-skills": recheck,
        "readers@tony-skills": readers,
        "delivery-probe@skills-v2-pilot": delivery,
        "manual-only-probe@skills-v2-pilot": manual,
    },
    "launch_settings": os.path.join(pilot, "launch-settings.json"),
}
with open(os.path.join(pilot, "install.json"), "w", encoding="utf-8") as handle:
    json.dump(document, handle, indent=2)
    handle.write("\n")
sys.stdout.write(json.dumps(document, indent=2) + "\n")
PY
