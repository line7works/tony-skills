#!/bin/sh
# Verify this core's installed package in its isolated Claude Code setup (E13 slice 3, 3.3).
# Adapted from plugins/recheck-v2/setups/claude-code/verify-install.sh; the checks live in
# ../verify-package.py, shared with the Codex setup. Byte-identical in build-v2 and signoff-v2.
#
# Usage: verify-install.sh --home DIR   (or <CORE>_CLAUDE_HOME=DIR)
# Prints one JSON object; exit 0 no finding, 4 a finding, 2 usage.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
CORE=$(basename -- "$PLUGIN_ROOT")
VAR=$(printf '%s' "$CORE" | tr 'a-z-' 'A-Z_')_CLAUDE_HOME
SETUP_HOME=$(eval "printf '%s' \"\${$VAR:-}\"")
if [ "${1:-}" = "--home" ]; then SETUP_HOME="${2:-}"; shift 2 || true; fi
[ $# -eq 0 ] || { echo "verify-install.sh: unknown argument: $1" >&2; exit 2; }
[ -n "$SETUP_HOME" ] && [ -d "$SETUP_HOME" ] || { echo "verify-install.sh: name the installed home: --home DIR or $VAR" >&2; exit 2; }
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$SCRIPT_DIR/../verify-package.py" --cache "$SETUP_HOME/config/plugins/cache" --market "$CORE-setup"
