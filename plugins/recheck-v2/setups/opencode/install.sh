#!/bin/sh
# recheck-v2 pilot setup, lane Q: OpenCode with its OpenRouter provider (E9 ruling D3a).
#
# Creates the isolated pilot home under ~/.local/share/skills-v2-pilot/opencode/ and installs
# the pinned opencode binary, the isolated XDG config and data homes, the two model
# sub-setups, the recheck-verifier agent, the session-pointer plugin, the recheck-v2 skill
# folder, and the two shared probes. Touches nothing under ~/.config/opencode,
# ~/.local/share/opencode, ~/.claude, or any repository.
#
# Usage:  sh install.sh [--setup DIR] [--model MODEL]
#   --setup DIR   the isolated pilot home (default ~/.local/share/skills-v2-pilot/opencode)
#   --model M     the default model written into opencode.json
#                 (default openrouter/qwen/qwen3.8-flash)
#
# Requires OPENROUTER_API_KEY in the environment. The key is never written to disk, never
# copied into the config, and never printed: install.sh only checks that it is set.
#
# Side effects: creates <setup>/{npm,xdg-config,xdg-data,xdg-cache,xdg-state}; runs
# `npm install --prefix <setup>/npm opencode-ai@<pinned>`; writes
# <setup>/xdg-config/opencode/{opencode.json,plugin/session-pointer.js} and the skill folders
# under <setup>/xdg-config/opencode/skill/. Rerunning replaces those files and leaves the
# session store (<setup>/xdg-data/opencode/opencode.db) alone.
set -eu

OPENCODE_VERSION="1.18.31"   # pinned 2026-09-14 from `npm view opencode-ai version`
SETUP="${HOME}/.local/share/skills-v2-pilot/opencode"
MODEL="openrouter/qwen/qwen3.8-flash"

while [ $# -gt 0 ]; do
  case "$1" in
    --setup) SETUP="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "install.sh: unknown argument $1" >&2; exit 2 ;;
  esac
done

HERE=$(cd "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(cd "$HERE/../.." && pwd)     # plugins/recheck-v2
SKILL_SRC="$PLUGIN_ROOT/skills/recheck-v2"
FIXTURES="$PLUGIN_ROOT/setups/_fixtures"

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "install.sh: OPENROUTER_API_KEY is not set in the environment" >&2
  exit 3
fi
echo "credential: OPENROUTER_API_KEY set"

mkdir -p "$SETUP/npm" "$SETUP/xdg-config/opencode" "$SETUP/xdg-data" "$SETUP/xdg-cache" "$SETUP/xdg-state"

echo "installing opencode-ai@$OPENCODE_VERSION into $SETUP/npm"
npm install --prefix "$SETUP/npm" "opencode-ai@$OPENCODE_VERSION" >/dev/null
OC="$SETUP/npm/node_modules/.bin/opencode"
[ -x "$OC" ] || { echo "install.sh: opencode binary missing at $OC" >&2; exit 3; }

# The config: the two model sub-setups, the verifier agent, the default model, and the
# external-directory allow rule for the run root.
#
# Measured on 1.18.31: the default rule is `external_directory * ask`, and in a headless
# `opencode run` an "ask" is auto-rejected ("The user rejected permission to use this specific
# tool call"), so a write to the run directory the contract puts OUTSIDE the workspace fails.
# The run root is ${TMPDIR:-/tmp}/recheck-v2 (contract section 2 and the adapter profile
# section 3); install.sh writes the machine's concrete TMPDIR into the rule and keeps a
# /tmp/recheck-v2 rule for a shell without TMPDIR. Rules are evaluated last-match-wins, so
# the broad "ask" comes first.
RUNROOT="${TMPDIR:-/tmp}"
RUNROOT="${RUNROOT%/}/recheck-v2"
sed -e "s|__MODEL__|$MODEL|g" -e "s|__RUNROOT__|$RUNROOT|g" \
  "$HERE/assets/opencode.json" > "$SETUP/xdg-config/opencode/opencode.json"
echo "run root allowed: $RUNROOT"

# The session pointer plugin (the user channel; see adapters/opencode/profile.md section 4).
mkdir -p "$SETUP/xdg-config/opencode/plugin"
cp "$HERE/assets/session-pointer.js" "$SETUP/xdg-config/opencode/plugin/session-pointer.js"

# The skill folder and the two shared probes, on the surface this setup ships:
# <isolated XDG_CONFIG_HOME>/opencode/skill/<name>/ (measured in RESULTS.md).
SKILLDIR="$SETUP/xdg-config/opencode/skill"
mkdir -p "$SKILLDIR"
for name in recheck-v2 delivery-probe manual-only-probe; do
  rm -rf "$SKILLDIR/$name"
done
cp -R "$SKILL_SRC" "$SKILLDIR/recheck-v2"
cp -R "$FIXTURES/delivery-probe/skills/delivery-probe" "$SKILLDIR/delivery-probe"
cp -R "$FIXTURES/manual-only-probe/skills/manual-only-probe" "$SKILLDIR/manual-only-probe"
find "$SKILLDIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

XDG_CONFIG_HOME="$SETUP/xdg-config" XDG_DATA_HOME="$SETUP/xdg-data" \
XDG_CACHE_HOME="$SETUP/xdg-cache" XDG_STATE_HOME="$SETUP/xdg-state" \
OPENCODE_DISABLE_EXTERNAL_SKILLS=1 \
  "$OC" --version

echo "setup:   $SETUP"
echo "binary:  $OC"
echo "model:   $MODEL"
echo "skills:  $(ls "$SKILLDIR" | tr '\n' ' ')"
echo "install.sh: done"
