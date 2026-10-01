#!/bin/sh
# One headless Claude Code session of this core's setup (E13 slice 3, brief 3.3).
#
# Adapted from plugins/recheck-v2/setups/claude-code/launch.sh. Byte-identical in the six v2 cores
# that carry it (the four front cores, build-v2 and signoff-v2; E14 punch list), held equal by the
# front cores' test_shared_equal.py and by build-v2's and signoff-v2's test_setup_guard.py, which
# compare their copy with precon-v2's. The home guard below (E14 slice 3c): the out-dir and the
# installed home may not be or sit under ~/.claude, ~/.codex or ~/.local/share/skills-v2-*, as
# given or resolved, and neither may TMPDIR, TEMP or TMP (exit 2, nothing created). The core is
# this script's own plugin folder.
#
# Usage: launch.sh <prompt-file> <workspace> <out-dir>
# The session runs with CLAUDE_CONFIG_DIR=<home>/config, the ISOLATED config directory install.sh
# built (<CORE>_CLAUDE_HOME, e.g. BUILD_V2_CLAUDE_HOME), where the core is installed and enabled.
# This is the one difference from the pilot's launcher, which ran against the machine's own
# config directory with --plugin-dir because the isolated one has no sign-in (the pilot's
# RESULTS, "Sign-in"): E13 slice 3 may not touch the live ~/.claude, so a session that finds no
# sign-in here is recorded as not measured with the harness's own message, never retried there.
# --strict-mcp-config drops every MCP server; WebFetch and WebSearch are removed.
#
# Copies to <out-dir>: trace.jsonl (stream-json), transcript.jsonl (the session's own record, from
# the isolated config's projects/ folder), result.txt, command.txt and launch.json (session id,
# the init event's catalog, cost, exit). Exit 0 a usable result, 2 usage or a spent out-dir,
# 3 claude or the home missing, 1 the session failed or produced no result.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
CORE=$(basename -- "$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)")
VAR=$(printf '%s' "$CORE" | tr 'a-z-' 'A-Z_')_CLAUDE_HOME
SETUP_HOME=$(eval "printf '%s' \"\${$VAR:-}\"")
[ $# -eq 3 ] || { echo "usage: launch.sh <prompt-file> <workspace> <out-dir>" >&2; exit 2; }
PROMPT_FILE="$1"; WORKSPACE="$2"; OUT_DIR="$3"
command -v claude >/dev/null 2>&1 || { echo "launch.sh: claude is not on PATH" >&2; exit 3; }
[ -s "$PROMPT_FILE" ] || { echo "launch.sh: no prompt file (or it is empty): $PROMPT_FILE" >&2; exit 2; }
[ -d "$WORKSPACE" ] || { echo "launch.sh: no workspace: $WORKSPACE" >&2; exit 2; }
# The home guard, before anything is created (E14 slice 3c fix 3-2): the installers' GUARD, byte for byte.
for checked in "$OUT_DIR" "$SETUP_HOME"; do
  env -u TMPDIR -u TEMP -u TMP python3 - "$checked" "$HOME" "launch.sh" "${TMPDIR-}" "${TEMP-}" "${TMP-}" <<'GUARD' >/dev/null || exit 2
import os, sys
target, home, name = sys.argv[1:4]


def refuse(why):
    sys.stderr.write("%s: %s; nothing created\n" % (name, why))
    sys.exit(2)


def forms(path):
    return (os.path.abspath(path), os.path.realpath(path))


def rest(path, base):
    """The part of `path` below `base` ("" when they are the same), or None; compared casefolded."""
    p, b = path.casefold(), base.casefold().rstrip(os.sep)
    return "" if p == b else (p[len(b) + 1:] if p.startswith(b + os.sep) else None)


if not os.path.isabs(home):
    refuse("HOME is not an absolute path")
share = os.path.join(home, ".local", "share")
homes = (os.path.join(home, ".claude"), os.path.join(home, ".codex"),
         os.path.join(share, "skills-v2-pilot"), os.path.join(share, "skills-v2-locked"))
temps = [value for value in sys.argv[4:7] if value] or ["/tmp"]
for given in [target] + temps:
    for path in forms(given):
        for forbidden in homes:
            if any(rest(path, base) is not None for base in forms(forbidden)):
                refuse("%s is under %s, which no setup may touch" % (given, forbidden))
        for base in forms(share):
            below = rest(path, base)
            if below and below.split(os.sep)[0].startswith("skills-v2-"):
                refuse("%s is under %s, which no setup may touch"
                       % (given, os.path.join(share, below.split(os.sep)[0])))
print(os.path.realpath(target))
GUARD
done
[ -n "$SETUP_HOME" ] && [ -d "$SETUP_HOME/config" ] || { echo "launch.sh: $VAR must name the installed home" >&2; exit 3; }
for kept in trace.jsonl launch.json transcript.jsonl result.txt; do
  [ -e "$OUT_DIR/$kept" ] && { echo "launch.sh: $OUT_DIR already holds $kept; name a fresh output directory" >&2; exit 2; }
done
mkdir -p "$OUT_DIR"
OUT_DIR=$(CDPATH= cd -- "$OUT_DIR" && pwd -P)
WORKSPACE=$(CDPATH= cd -- "$WORKSPACE" && pwd -P)
PROMPT_FILE=$(CDPATH= cd -- "$(dirname -- "$PROMPT_FILE")" && pwd -P)/$(basename -- "$PROMPT_FILE")
CONFIG_DIR="$SETUP_HOME/config"
set -- claude --strict-mcp-config --disallowed-tools WebFetch WebSearch \
  --permission-mode acceptEdits --output-format stream-json --verbose --print
printf 'CLAUDE_CONFIG_DIR=%s %s\n' "$CONFIG_DIR" "$*" > "$OUT_DIR/command.txt"
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
STATUS=0
( cd "$WORKSPACE" && CLAUDE_CONFIG_DIR="$CONFIG_DIR" "$@" "$(cat "$PROMPT_FILE")" \
    < /dev/null > "$OUT_DIR/trace.jsonl" 2> "$OUT_DIR/trace.err" ) || STATUS=$?
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
python3 - "$OUT_DIR" "$WORKSPACE" "$PROMPT_FILE" "$START" "$END" "$CONFIG_DIR" "$STATUS" <<'PY'
import glob, json, os, re, shutil, sys
out_dir, workspace, prompt, start, end, config_dir, status = sys.argv[1:8]
init, result = {}, {}
for line in open(os.path.join(out_dir, "trace.jsonl"), encoding="utf-8"):
    try:
        record = json.loads(line)
    except ValueError:
        continue
    if record.get("type") == "system" and record.get("subtype") == "init":
        init = record
    if record.get("type") == "result":
        result = record
session = result.get("session_id") or init.get("session_id")
transcript = None
if session:
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(workspace))
    for candidate in [os.path.join(config_dir, "projects", slug, session + ".jsonl")] + glob.glob(
            os.path.join(config_dir, "projects", "*", session + ".jsonl")):
        if os.path.isfile(candidate):
            transcript = candidate
            break
if transcript:
    shutil.copyfile(transcript, os.path.join(out_dir, "transcript.jsonl"))
with open(os.path.join(out_dir, "result.txt"), "w", encoding="utf-8") as handle:
    handle.write((result.get("result") or "") + "\n")
problems = []
if int(status):
    problems.append("the claude process exited %s" % status)
if not session:
    problems.append("the session produced no session id")
if not result or result.get("is_error"):
    problems.append("the session produced no usable result: %r" % (result.get("result"),))
doc = {"ok": not problems, "problems": problems, "claude_exit": int(status), "session_id": session,
       "config_dir": config_dir, "workspace": workspace, "prompt_file": prompt,
       "started_at": start, "ended_at": end, "model": init.get("model"),
       "permission_mode": init.get("permissionMode"), "skills": init.get("skills"),
       "slash_commands": init.get("slash_commands"), "plugins": init.get("plugins"),
       "mcp_servers": init.get("mcp_servers"), "is_error": result.get("is_error"),
       "result": result.get("result"), "total_cost_usd": result.get("total_cost_usd"),
       "permission_denials": result.get("permission_denials"),
       "transcript": os.path.join(out_dir, "transcript.jsonl") if transcript else None}
with open(os.path.join(out_dir, "launch.json"), "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
print(json.dumps(doc, indent=2))
sys.exit(1 if problems else 0)
PY
