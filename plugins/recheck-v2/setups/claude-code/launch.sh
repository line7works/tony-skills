#!/bin/sh
# One headless Claude Code session of the pilot setup (E9 lane C).
#
# Usage: launch.sh <prompt-file> <workspace> <out-dir> [--plugin NAME]... [--bypass]
#
# Copies to <out-dir>: trace.jsonl (the stream-json trace), transcript.jsonl
# (the harness's own record of the session), result.txt (the final text),
# launch.json (the command line, the session id, the catalog, the cost).
# Prints one JSON object on stdout; the harness's own output goes to the files.
# Exit 0 the session ended, 2 usage, 3 claude or the installed plugin is
# missing, 1 anything else.
#
# Sign-in: the isolated CLAUDE_CONFIG_DIR does NOT keep the machine's sign-in
# (measured 2026-09-14: `claude -p 'say ok'` there answers "Not logged in ·
# Please run /login", cost 0), so a live session runs against the machine's own
# config directory and loads the pilot from the isolated install cache with
# --plugin-dir, as E9 section 6 rules for that case. --setting-sources local
# drops the machine's user settings, which is where installed plugins are
# enabled, so the catalog is the built-in skills plus the plugins named here and
# no v1 station; --strict-mcp-config drops every MCP server. Both are recorded
# in launch.json from the session's own init event.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PILOT_HOME="${SKILLS_V2_PILOT_HOME:-$HOME/.local/share/skills-v2-pilot/claude-code}"
CONFIG_DIR="$PILOT_HOME/config"
CACHE="$CONFIG_DIR/plugins/cache"
BYPASS=0
PLUGINS=""

[ $# -ge 3 ] || { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
PROMPT_FILE="$1"; WORKSPACE="$2"; OUT_DIR="$3"; shift 3
while [ $# -gt 0 ]; do
  case "$1" in
    --plugin) PLUGINS="$PLUGINS $2"; shift 2 ;;
    --bypass) BYPASS=1; shift ;;
    *) echo "launch.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$PLUGINS" ] || PLUGINS="recheck-v2 readers"

command -v claude >/dev/null 2>&1 || { echo "launch.sh: claude is not on PATH" >&2; exit 3; }
[ -f "$PROMPT_FILE" ] || { echo "launch.sh: no prompt file: $PROMPT_FILE" >&2; exit 2; }
[ -d "$WORKSPACE" ] || { echo "launch.sh: no workspace: $WORKSPACE" >&2; exit 2; }
mkdir -p "$OUT_DIR"
OUT_DIR=$(CDPATH= cd -- "$OUT_DIR" && pwd -P)
WORKSPACE=$(CDPATH= cd -- "$WORKSPACE" && pwd -P)

set -- claude
for name in $PLUGINS; do
  dir=$(find "$CACHE" -maxdepth 3 -mindepth 3 -type d -path "*/$name/*" 2>/dev/null | sort | tail -1)
  [ -n "$dir" ] || { echo "launch.sh: $name is not installed under $CACHE" >&2; exit 3; }
  set -- "$@" --plugin-dir "$dir"
done

RUN_ROOT="${TMPDIR:-/tmp}/recheck-v2"
mkdir -p "$RUN_ROOT"
set -- "$@" --setting-sources local --strict-mcp-config \
  --settings "$PILOT_HOME/launch-settings.json" \
  --disallowed-tools WebFetch WebSearch \
  --add-dir "$RUN_ROOT" \
  --permission-prompts none \
  --output-format stream-json --verbose --print
if [ "$BYPASS" -eq 1 ]; then
  SANDBOX="bypass"
  set -- "$@" --dangerously-skip-permissions
else
  SANDBOX="acceptEdits"
  set -- "$@" --permission-mode acceptEdits
fi

printf '%s\n' "$*" > "$OUT_DIR/command.txt"
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cd "$WORKSPACE"
RECHECK_HARNESS_SANDBOX="$SANDBOX" READERS_CHECKOUT="$PILOT_HOME/readers-checkout" "$@" "$(cat "$PROMPT_FILE")" \
  < /dev/null > "$OUT_DIR/trace.jsonl" 2> "$OUT_DIR/trace.err" || true
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

python3 - "$OUT_DIR" "$WORKSPACE" "$PROMPT_FILE" "$SANDBOX" "$START" "$END" "$CONFIG_DIR" <<'PY'
import glob
import json
import os
import shutil
import sys

out_dir, workspace, prompt_file, sandbox, start, end, config_dir = sys.argv[1:8]
trace = os.path.join(out_dir, "trace.jsonl")
init = {}
result = {}
with open(trace, "r", encoding="utf-8") as handle:
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
            result = record

session_id = result.get("session_id") or init.get("session_id")
transcript = None
if session_id:
    # The live session writes its transcript under the machine's own config
    # directory, not the isolated one, because the isolated one has no sign-in.
    for root in (os.path.expanduser("~/.claude"), config_dir):
        hits = glob.glob(os.path.join(root, "projects", "*", "%s.jsonl" % session_id))
        if hits:
            transcript = hits[0]
            break
if transcript:
    shutil.copyfile(transcript, os.path.join(out_dir, "transcript.jsonl"))
with open(os.path.join(out_dir, "result.txt"), "w", encoding="utf-8") as handle:
    handle.write((result.get("result") or "") + "\n")

document = {
    "session_id": session_id,
    "workspace": workspace,
    "prompt_file": os.path.abspath(prompt_file),
    "sandbox": sandbox,
    "started_at": start,
    "ended_at": end,
    "model": init.get("model"),
    "permission_mode": init.get("permissionMode"),
    "plugins": init.get("plugins"),
    "skills": init.get("skills"),
    "slash_commands": init.get("slash_commands"),
    "mcp_servers": init.get("mcp_servers"),
    "tools": init.get("tools"),
    "is_error": result.get("is_error"),
    "num_turns": result.get("num_turns"),
    "total_cost_usd": result.get("total_cost_usd"),
    "permission_denials": result.get("permission_denials"),
    "trace": trace,
    "transcript": os.path.join(out_dir, "transcript.jsonl") if transcript else None,
    "transcript_source": transcript,
}
with open(os.path.join(out_dir, "launch.json"), "w", encoding="utf-8") as handle:
    json.dump(document, handle, indent=2)
    handle.write("\n")
sys.stdout.write(json.dumps(document, indent=2) + "\n")
PY
