#!/bin/sh
# One headless Claude Code session of the pilot setup (E9 lane C).
#
# Usage: launch.sh <prompt-file> <workspace> <out-dir> [--plugin NAME]...
#                  [--plugin-dir DIR]... [--bypass] [--model M] [--effort E]
#
# --plugin NAME loads that plugin from the pilot's own install cache;
# --plugin-dir DIR loads an installed copy anywhere (the negative tests' own
# throwaway installs). Giving either one replaces the default pair
# (recheck-v2 readers).
#
# --model M and --effort E go straight onto the claude argv (ruling E10-62:
# Tony pinned this setup to Opus 5 at effort medium, `claude --model opus
# --effort medium`). `claude --help` on 2.1.272 prints "--effort <level> ...
# (low, medium, high, xhigh, max)". Neither is defaulted here: omitting one
# leaves the harness on whatever the machine's sign-in chooses, which is what
# E9 measured. What this script was TOLD is recorded in launch.json as
# configured_model and configured_effort, apart from the `model` key, which is
# and stays the session's own init event (E10-50, E10-62 item 4).
#
# Copies to <out-dir>: trace.jsonl (the stream-json trace), transcript.jsonl
# (the harness's own record of the session), result.txt (the final text),
# launch.json (the command line, the session id, the catalog, the cost, and the
# claude process's own exit status).
# Prints one JSON object on stdout; the harness's own output goes to the files.
# Exit 0 the session ended with a usable result, 2 usage (an unknown argument,
# a missing prompt or workspace, or an output directory that already holds a
# launch: a record is never overwritten), 3 claude or the installed plugin is
# missing, 1 the claude process failed or the session produced no result and no
# session id (the records written so far are kept and named).
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
PLUGIN_DIRS=""
WRITABLE_DIRS=""   # E11-26: extra roots the runner names for THIS trial
DENY_DIRS=""       # E11-45 S1: roots this launch may never write, denied by permission
MODEL=""          # E10-62: the plan's pinned model, or empty for the sign-in's own
EFFORT=""         # E10-62: the plan's pinned effort, or empty for the harness's own

[ $# -ge 3 ] || { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
PROMPT_FILE="$1"; WORKSPACE="$2"; OUT_DIR="$3"; shift 3
while [ $# -gt 0 ]; do
  case "$1" in
    --plugin) PLUGINS="$PLUGINS $2"; shift 2 ;;
    --plugin-dir)
      [ -d "$2" ] || { echo "launch.sh: no plugin directory: $2" >&2; exit 3; }
      PLUGIN_DIRS="$PLUGIN_DIRS $2"; shift 2 ;;
    --bypass) BYPASS=1; shift ;;
    --model)
      [ $# -ge 2 ] || { echo "launch.sh: --model takes a value" >&2; exit 2; }
      MODEL="$2"; shift 2 ;;
    --effort)
      [ $# -ge 2 ] || { echo "launch.sh: --effort takes a value" >&2; exit 2; }
      EFFORT="$2"; shift 2 ;;
    --writable)
      # E11-26: a root the runner named for THIS trial (its own run leaf's directory). The
      # run directory is a sibling of the workspace and is not under ${TMPDIR}/runs since the
      # per-trial scratch of E11-7 item 2, so it is named rather than assumed.
      [ $# -ge 2 ] || { echo "launch.sh: --writable takes a value" >&2; exit 2; }
      [ -d "$2" ] || { echo "launch.sh: no writable directory: $2" >&2; exit 3; }
      WRITABLE_DIRS="$WRITABLE_DIRS $2"; shift 2 ;;
    --deny)
      # E11-45 S1: a root this launch must not write. It becomes a path-scoped
      # `permissions.deny` entry for Write and Edit, so the refusal comes from the
      # harness rather than from the mandate's prose. The directory need not exist yet.
      [ $# -ge 2 ] || { echo "launch.sh: --deny takes a value" >&2; exit 2; }
      DENY_DIRS="$DENY_DIRS $2"; shift 2 ;;
    *) echo "launch.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$PLUGINS" ] || [ -n "$PLUGIN_DIRS" ] || PLUGINS="recheck-v2 readers"

command -v claude >/dev/null 2>&1 || { echo "launch.sh: claude is not on PATH" >&2; exit 3; }
[ -f "$PROMPT_FILE" ] || { echo "launch.sh: no prompt file: $PROMPT_FILE" >&2; exit 2; }
[ -d "$WORKSPACE" ] || { echo "launch.sh: no workspace: $WORKSPACE" >&2; exit 2; }
# A reused output directory is refused rather than overwritten (E9-34): the
# records of a live session are the evidence.
for kept in trace.jsonl launch.json transcript.jsonl result.txt; do
  [ -e "$OUT_DIR/$kept" ] && {
    echo "launch.sh: $OUT_DIR already holds $kept; name a fresh output directory" >&2
    exit 2
  }
done
mkdir -p "$OUT_DIR"
OUT_DIR=$(CDPATH= cd -- "$OUT_DIR" && pwd -P)
WORKSPACE=$(CDPATH= cd -- "$WORKSPACE" && pwd -P)
# The session starts in the workspace, so a relative prompt path is resolved
# here, before the cd: read from there it would be empty, and the harness would
# be handed no prompt at all (measured 2026-09-14, exit 1 "Input must be
# provided either through stdin or as a prompt argument when using --print").
PROMPT_FILE=$(CDPATH= cd -- "$(dirname -- "$PROMPT_FILE")" && pwd -P)/$(basename -- "$PROMPT_FILE")
[ -s "$PROMPT_FILE" ] || { echo "launch.sh: the prompt file is empty: $PROMPT_FILE" >&2; exit 2; }

set -- claude
for name in $PLUGINS; do
  dir=$(find "$CACHE" -maxdepth 3 -mindepth 3 -type d -path "*/$name/*" 2>/dev/null | sort | tail -1)
  [ -n "$dir" ] || { echo "launch.sh: $name is not installed under $CACHE" >&2; exit 3; }
  set -- "$@" --plugin-dir "$dir"
done
for dir in $PLUGIN_DIRS; do
  set -- "$@" --plugin-dir "$dir"
done

RUN_ROOT="${TMPDIR:-/tmp}/runs"  # E10-22: a neutral name; the E10 prompt names this path
mkdir -p "$RUN_ROOT"
# E10-62: the plan's pinned pair, on the claude argv. Each is added only when
# it was given, so an E9-shaped call runs exactly the command E9 measured.
if [ -n "$MODEL" ]; then set -- "$@" --model "$MODEL"; fi
if [ -n "$EFFORT" ]; then set -- "$@" --effort "$EFFORT"; fi
# E11-45 S1: this launch's own settings - the installed ones plus the path-scoped write
# denials and the outbound-command denials (E11-41 R6: the F5 outbound call is declined by
# permission, not left to a name that happens not to resolve). Written beside the capture so
# the record shows exactly what the fence was.
LAUNCH_SETTINGS="$OUT_DIR/launch-settings.json"
python3 "$(dirname -- "$0")/write-fence.py" \
  "$PILOT_HOME/launch-settings.json" "$LAUNCH_SETTINGS" $DENY_DIRS \
  || { echo "launch.sh: could not write the launch settings" >&2; exit 3; }
set -- "$@" --setting-sources local --strict-mcp-config \
  --settings "$LAUNCH_SETTINGS" \
  --disallowed-tools WebFetch WebSearch \
  --add-dir "$RUN_ROOT" \
  --permission-prompts none \
  --output-format stream-json --verbose --print
for dir in $WRITABLE_DIRS; do
  set -- "$@" --add-dir "$dir"
done
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
CLAUDE_STATUS=0
RECHECK_HARNESS_SANDBOX="$SANDBOX" READERS_CHECKOUT="$PILOT_HOME/readers-checkout" "$@" "$(cat "$PROMPT_FILE")" \
  < /dev/null > "$OUT_DIR/trace.jsonl" 2> "$OUT_DIR/trace.err" || CLAUDE_STATUS=$?
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [ "$CLAUDE_STATUS" -ne 0 ]; then
  echo "launch.sh: claude exited $CLAUDE_STATUS; its stderr:" >&2
  cat "$OUT_DIR/trace.err" >&2
fi

python3 - "$OUT_DIR" "$WORKSPACE" "$PROMPT_FILE" "$SANDBOX" "$START" "$END" "$CONFIG_DIR" \
  "$CLAUDE_STATUS" "$MODEL" "$EFFORT" <<'PY'
import glob
import json
import os
import re
import shutil
import sys

(out_dir, workspace, prompt_file, sandbox, start, end, config_dir,
 claude_status, configured_model, configured_effort) = sys.argv[1:11]
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
# The session's own project folder is named after its cwd, every character that is
# not a letter or a digit replaced by "-". Behind the wall the sibling folders
# under projects/ are unreadable and the directory itself cannot be LISTED, so the
# named path is tried first and the glob is the fallback for an unwalled launch.
slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(workspace))
if session_id:
    # The live session writes its transcript under the machine's own config
    # directory, not the isolated one, because the isolated one has no sign-in.
    for root in (os.path.expanduser("~/.claude"), config_dir):
        named = os.path.join(root, "projects", slug, "%s.jsonl" % session_id)
        if os.path.isfile(named):
            transcript = named
            break
        try:
            hits = glob.glob(os.path.join(root, "projects", "*", "%s.jsonl" % session_id))
        except OSError:
            hits = []
        if hits:
            transcript = hits[0]
            break
if transcript:
    shutil.copyfile(transcript, os.path.join(out_dir, "transcript.jsonl"))
with open(os.path.join(out_dir, "result.txt"), "w", encoding="utf-8") as handle:
    handle.write((result.get("result") or "") + "\n")

problems = []
if int(claude_status) != 0:
    problems.append("the claude process exited %s" % claude_status)
if not session_id:
    problems.append("the session produced no session id")
if not result:
    problems.append("the trace holds no result event")

document = {
    "ok": not problems,
    "problems": problems,
    "claude_exit": int(claude_status),
    "session_id": session_id,
    "workspace": workspace,
    "prompt_file": os.path.abspath(prompt_file),
    "sandbox": sandbox,
    "started_at": start,
    "ended_at": end,
    # The session's own init event. E10-50 and E10-62 item 4: this is an
    # OBSERVATION and stays one; what this script was TOLD is the two keys below.
    "model": init.get("model"),
    "configured_model": configured_model or None,
    "configured_effort": configured_effort or None,
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
    "transcript_slug": slug,
}
with open(os.path.join(out_dir, "launch.json"), "w", encoding="utf-8") as handle:
    json.dump(document, handle, indent=2)
    handle.write("\n")
sys.stdout.write(json.dumps(document, indent=2) + "\n")
if problems:
    # A null session result is not a measurement: it is a failed launch, and a
    # caller that reads only the exit status must see it (Astra's finding 9).
    sys.stderr.write(
        "launch.sh: %s; the records written are under %s\n" % ("; ".join(problems), out_dir)
    )
    sys.exit(1)
PY
