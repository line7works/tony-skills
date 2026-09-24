#!/bin/sh
# The negative installation tests of this core on Claude Code (E13 slice 3, 3.3).
# Adapted from plugins/recheck-v2/setups/claude-code/negative-tests.sh; the cases live in
# ../negative-cases.py, shared with the Codex setup. Byte-identical in build-v2 and signoff-v2.
#
# Usage: negative-tests.sh <fresh output directory> [--live]
# The free half always runs (install commands and the cache, no session); --live adds the
# catalog sessions. Every case gets its own throwaway CLAUDE_CONFIG_DIR under the output
# directory; the live ~/.claude is never touched. One JSON line per case on stdout.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
[ $# -ge 1 ] || { echo "usage: negative-tests.sh <fresh output directory> [--live]" >&2; exit 2; }
command -v claude >/dev/null 2>&1 || { echo "negative-tests.sh: claude is not on PATH" >&2; exit 3; }
export PYTHONDONTWRITEBYTECODE=1
OUT="$1"; shift
exec python3 "$SCRIPT_DIR/../negative-cases.py" --harness claude-code --out "$OUT" "$@"
