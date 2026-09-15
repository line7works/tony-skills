#!/bin/sh
# One headless OpenCode session in the isolated pilot setup (E9 lane Q).
#
# Usage:  sh launch.sh <model> <prompt-file> <workspace> <out-dir> [--agent NAME]
#   <model>        the model sub-setup: qwen | deepseek, or a full provider/model id
#   <prompt-file>  the prompt, read from the file (never interpolated into a shell string)
#   <out-dir>      created, and it must be unused: a directory that already holds a launch's
#                  rc.txt or trace.json is refused (Astra finding 14 — reusing one disabled the
#                  timeout). It receives trace.json (the --format json event stream),
#                  stderr.txt, child.pid (the opencode process id of THIS launch), rc.txt (the
#                  exit status, written once this launch's own child has ended), session.json
#                  (the harness's own record of the session, its messages and its parts, from
#                  the session store) and pointer.json (this launch's own session-pointer file)
#   <workspace>    the directory the session runs in
#   --agent NAME   run under a configured agent instead of the default
#
# Environment: the provider key is NOT passed to the harness (ruling E9-38). The session reads
# it from the setup's own auth store, <setup>/xdg-data/opencode/auth.json, which install.sh
# wrote at mode 0600; this launcher requires that file and removes OPENROUTER_API_KEY from the
# child's environment, so no tool shell inherits it and an executor's own `env` probe cannot
# print it into the harness's records. After every launch the output directory is scanned for
# credential-shaped values and a hit is exit 5.
# OPENCODE_DISABLE_EXTERNAL_SKILLS=1 is set so the run's catalog holds only the skills this
# setup installed (E9-4: a clean catalog for the trace check); measured: without it the
# binary also scans ~/.claude/skills and ~/.agents/skills in the real home.
#
# The timeout (default 900s, RECHECK_OPENCODE_TIMEOUT) watches THIS launch's own child by its
# process id, not by the appearance of a result file, and kills only that child's process
# group: no `pkill -f` pattern that could reach another launch (Astra finding 14). rc.txt
# records 124 only when the child was still running when the limit was reached; a child that
# finished first keeps its own exit status (ruling E9-41).
#
# Side effects: writes only under <out-dir>, the isolated setup, and ${TMPDIR}/recheck-v2/.
set -eu

SETUP="${RECHECK_OPENCODE_SETUP:-$HOME/.local/share/skills-v2-pilot/opencode}"
TIMEOUT="${RECHECK_OPENCODE_TIMEOUT:-900}"

[ $# -ge 4 ] || { sed -n '2,29p' "$0"; exit 2; }
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
AUTH="$SETUP/xdg-data/opencode/auth.json"
[ -f "$AUTH" ] || { echo "launch.sh: no auth store at $AUTH (run install.sh once with OPENROUTER_API_KEY set)" >&2; exit 3; }

# A used output directory is refused rather than reused: its rc.txt would make the monitor
# below skip its own loop and the timeout would never fire (Astra finding 14).
for spent in rc.txt trace.json child.pid; do
  if [ -e "$OUT_DIR/$spent" ]; then
    echo "launch.sh: $OUT_DIR is a spent output directory (it holds $spent); give this launch a fresh one" >&2
    exit 2
  fi
done
mkdir -p "$OUT_DIR"
OUT_DIR=$(cd "$OUT_DIR" && pwd)
PROMPT_FILE=$(cd "$(dirname "$PROMPT_FILE")" && pwd)/$(basename "$PROMPT_FILE")
WORKSPACE=$(cd "$WORKSPACE" && pwd)

export XDG_CONFIG_HOME="$SETUP/xdg-config"
export XDG_DATA_HOME="$SETUP/xdg-data"
export XDG_CACHE_HOME="$SETUP/xdg-cache"
export XDG_STATE_HOME="$SETUP/xdg-state"
export OPENCODE_DISABLE_EXTERNAL_SKILLS=1

PROMPT=$(cat "$PROMPT_FILE")

# Job control puts the child in its own process group, so the timeout can terminate exactly
# this launch and nothing else. `exec` makes the child the opencode process itself, so
# $CHILD is both the process id the pointer plugin records and the group to signal.
set +e
set -m
# `env -u OPENROUTER_API_KEY` is the whole point of ruling E9-38: the child, and therefore
# every tool shell it opens, never carries the value.
if [ -n "$AGENT" ]; then
  (
    cd "$WORKSPACE"
    exec env -u OPENROUTER_API_KEY "$OC" run --model "$MODEL" --agent "$AGENT" --format json "$PROMPT" \
      < /dev/null > "$OUT_DIR/trace.json" 2> "$OUT_DIR/stderr.txt"
  ) &
else
  (
    cd "$WORKSPACE"
    exec env -u OPENROUTER_API_KEY "$OC" run --model "$MODEL" --format json "$PROMPT" \
      < /dev/null > "$OUT_DIR/trace.json" 2> "$OUT_DIR/stderr.txt"
  ) &
fi
CHILD=$!
set +m
echo "$CHILD" > "$OUT_DIR/child.pid"

WAITED=0
TIMED_OUT=0
while kill -0 "$CHILD" 2>/dev/null; do
  sleep 1
  WAITED=$((WAITED + 1))
  # Ruling E9-41: a child that finished during that sleep has an exit status of its own, and
  # collecting it comes before any timeout verdict. Without this re-check a child that ran for
  # 0.2 s under a one-second limit was recorded as 124.
  kill -0 "$CHILD" 2>/dev/null || break
  if [ "$WAITED" -ge "$TIMEOUT" ]; then
    # only a child that is still running is terminated, and only its own process group
    kill -TERM -"$CHILD" 2>/dev/null || kill -TERM "$CHILD" 2>/dev/null || true
    sleep 2
    kill -9 -"$CHILD" 2>/dev/null || kill -9 "$CHILD" 2>/dev/null || true
    TIMED_OUT=1
    break
  fi
done
wait "$CHILD"
RC=$?
set -e
[ "$TIMED_OUT" -eq 1 ] && RC=124
echo "$RC" > "$OUT_DIR/rc.txt"

# The harness's own record of the session, read out of the session store. This is a capture of
# a finished session by its id, not a run-time binding, so it goes through turns.py's fixture
# interface (RECHECK_ADAPTER_TEST=1 + --session, ruling E9-32); no helper resolves a session
# this way at run time.
SESSION_ID=$(sed -n 's/.*"sessionID":"\([^"]*\)".*/\1/p' "$OUT_DIR/trace.json" 2>/dev/null | head -1 || true)
ADAPTER_DIR=$(cd "$(dirname "$0")/../../skills/recheck-v2/adapters/opencode" && pwd)
if [ -n "$SESSION_ID" ]; then
  RECHECK_ADAPTER_TEST=1 env -u OPENROUTER_API_KEY /usr/bin/python3 "$ADAPTER_DIR/turns.py" \
    --session "$SESSION_ID" --setup "$SETUP" --raw \
    > "$OUT_DIR/session.json" 2> "$OUT_DIR/session.stderr" || true
fi

# This launch's own pointer file, named by the child's process id (never "the newest one").
POINTER="${TMPDIR:-/tmp}/recheck-v2/opencode/$CHILD.json"
if [ -f "$POINTER" ]; then
  cp "$POINTER" "$OUT_DIR/pointer.json"
else
  echo "launch.sh: no session pointer at $POINTER for this launch" >&2
fi

# Ruling E9-38: every capture this launch wrote is scanned before the launcher reports. A
# credential-shaped value in a trace, a stderr file or a session dump is a failure, and the
# scan prints the shape and the offset, never the value.
SCAN_OUT="$OUT_DIR/secret-scan.json"
if sh "$(dirname "$0")/scan-secrets.sh" --quiet --setup "$SETUP" "$OUT_DIR" > "$SCAN_OUT" 2>/dev/null; then
  SCAN_RC=0
else
  SCAN_RC=$?
fi

echo "model=$MODEL agent=${AGENT:-<default>} exit=$RC pid=$CHILD session=${SESSION_ID:-<none>} out=$OUT_DIR scan=$([ "$SCAN_RC" -eq 0 ] && echo clean || echo HIT)"
if [ "$SCAN_RC" -ne 0 ]; then
  echo "launch.sh: credential-shaped values in this launch's own captures; see $SCAN_OUT" >&2
  exit 5
fi
exit "$RC"
