#!/bin/sh
# One headless OpenCode session in the isolated pilot setup (E9 lane Q).
#
# Usage:  sh launch.sh <model> <prompt-file> <workspace> <out-dir> [--agent NAME]
#   <model>        the model sub-setup: qwen | deepseek, or a full provider/model id
#   <prompt-file>  the prompt, read from the file (never interpolated into a shell string)
#   <workspace>    the directory the session runs in
#   <out-dir>      created; receives trace.json (the --format json event stream),
#                  stderr.txt, rc.txt (the exit status), session.json (the harness's own
#                  record of the session, its messages and its parts, from the session
#                  store) and pointer.json (the session-pointer plugin's file, when present)
#   --agent NAME   run under a configured agent instead of the default
#
# Environment: OPENROUTER_API_KEY must be set; it is passed through and never written down.
# OPENCODE_DISABLE_EXTERNAL_SKILLS=1 is set so the run's catalog holds only the skills this
# setup installed (E9-4: a clean catalog for the trace check); measured: without it the
# binary also scans ~/.claude/skills and ~/.agents/skills in the real home.
#
# Side effects: writes only under <out-dir>, the isolated setup, and ${TMPDIR}/recheck-v2/.
# A run that exceeds the timeout (default 900s, RECHECK_OPENCODE_TIMEOUT) is killed and
# rc.txt records 124.
set -eu

SETUP="${RECHECK_OPENCODE_SETUP:-$HOME/.local/share/skills-v2-pilot/opencode}"
TIMEOUT="${RECHECK_OPENCODE_TIMEOUT:-900}"

[ $# -ge 4 ] || { sed -n '2,22p' "$0"; exit 2; }
MODEL_ARG="$1"; PROMPT_FILE="$2"; WORKSPACE="$3"; OUT_DIR="$4"; shift 4
AGENT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --agent) AGENT="$2"; shift 2 ;;
    *) echo "launch.sh: unknown argument $1" >&2; exit 2 ;;
  esac
done

case "$MODEL_ARG" in
  qwen) MODEL="openrouter/qwen/qwen3.8-flash" ;;
  deepseek) MODEL="openrouter/deepseek/deepseek-v4.1-flash" ;;
  */*) MODEL="$MODEL_ARG" ;;
  *) echo "launch.sh: unknown model $MODEL_ARG (qwen | deepseek | provider/model)" >&2; exit 2 ;;
esac

[ -f "$PROMPT_FILE" ] || { echo "launch.sh: no prompt file at $PROMPT_FILE" >&2; exit 3; }
[ -d "$WORKSPACE" ] || { echo "launch.sh: no workspace at $WORKSPACE" >&2; exit 3; }
OC="$SETUP/npm/node_modules/.bin/opencode"
[ -x "$OC" ] || { echo "launch.sh: no opencode binary at $OC (run install.sh)" >&2; exit 3; }
[ -n "${OPENROUTER_API_KEY:-}" ] || { echo "launch.sh: OPENROUTER_API_KEY is not set" >&2; exit 3; }

mkdir -p "$OUT_DIR"
OUT_DIR=$(cd "$OUT_DIR" && pwd)
PROMPT_FILE=$(cd "$(dirname "$PROMPT_FILE")" && pwd)/$(basename "$PROMPT_FILE")
WORKSPACE=$(cd "$WORKSPACE" && pwd)

export XDG_CONFIG_HOME="$SETUP/xdg-config"
export XDG_DATA_HOME="$SETUP/xdg-data"
export XDG_CACHE_HOME="$SETUP/xdg-cache"
export XDG_STATE_HOME="$SETUP/xdg-state"
export OPENCODE_DISABLE_EXTERNAL_SKILLS=1

set +e
(
  cd "$WORKSPACE"
  if [ -n "$AGENT" ]; then
    "$OC" run --model "$MODEL" --agent "$AGENT" --format json "$(cat "$PROMPT_FILE")" \
      < /dev/null > "$OUT_DIR/trace.json" 2> "$OUT_DIR/stderr.txt"
  else
    "$OC" run --model "$MODEL" --format json "$(cat "$PROMPT_FILE")" \
      < /dev/null > "$OUT_DIR/trace.json" 2> "$OUT_DIR/stderr.txt"
  fi
  echo $? > "$OUT_DIR/rc.txt"
) &
CHILD=$!
WAITED=0
while [ ! -f "$OUT_DIR/rc.txt" ]; do
  sleep 2
  WAITED=$((WAITED + 2))
  if [ "$WAITED" -ge "$TIMEOUT" ]; then
    kill -9 "$CHILD" 2>/dev/null || true
    pkill -9 -f "$OC run --model $MODEL" 2>/dev/null || true
    echo 124 > "$OUT_DIR/rc.txt"
    break
  fi
done
wait "$CHILD" 2>/dev/null || true
set -e

RC=$(cat "$OUT_DIR/rc.txt")

# The harness's own record of the session, read out of the session store.
SESSION_ID=$(sed -n 's/.*"sessionID":"\([^"]*\)".*/\1/p' "$OUT_DIR/trace.json" 2>/dev/null | head -1 || true)
HELPERS=$(cd "$SETUP" 2>/dev/null && pwd)
ADAPTER_DIR=$(cd "$(dirname "$0")/../../skills/recheck-v2/adapters/opencode" && pwd)
if [ -n "$SESSION_ID" ]; then
  /usr/bin/python3 "$ADAPTER_DIR/turns.py" --session "$SESSION_ID" --setup "$SETUP" --raw \
    > "$OUT_DIR/session.json" 2> "$OUT_DIR/session.stderr" || true
fi
POINTER_DIR="${TMPDIR:-/tmp}/recheck-v2/opencode"
if [ -d "$POINTER_DIR" ]; then
  # the newest pointer file, if the plugin wrote one for this run
  NEWEST=$(ls -t "$POINTER_DIR"/*.json 2>/dev/null | head -1 || true)
  [ -n "$NEWEST" ] && cp "$NEWEST" "$OUT_DIR/pointer.json" || true
fi

echo "model=$MODEL agent=${AGENT:-<default>} exit=$RC session=${SESSION_ID:-<none>} out=$OUT_DIR"
exit "$RC"
