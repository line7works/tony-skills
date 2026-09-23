#!/bin/sh
# The negative installation tests of this core on Codex (E13 slice 3, 3.3).
# Adapted from plugins/recheck-v2/setups/codex/negative-tests.sh and prepare-negative.py; the
# cases live in ../negative-cases.py, shared with the Claude Code setup. Byte-identical in
# build-v2 and signoff-v2.
#
# Usage: negative-tests.sh <fresh output directory> [--live]
# The free half always runs (codex plugin marketplace add / plugin add and the cache, no
# session); --live adds the catalog sessions. Every case gets its own throwaway CODEX_HOME under
# the output directory and no credential; the live ~/.codex is never touched.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
[ $# -ge 1 ] || { echo "usage: negative-tests.sh <fresh output directory> [--live]" >&2; exit 2; }
command -v codex >/dev/null 2>&1 || { echo "negative-tests.sh: codex is not on PATH" >&2; exit 3; }
export PYTHONDONTWRITEBYTECODE=1
OUT="$1"; shift
exec python3 "$SCRIPT_DIR/../negative-cases.py" --harness codex --out "$OUT" "$@"
