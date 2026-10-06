#!/usr/bin/env python3
"""The Stop-hook check on Claude Code for a ship-v2 run (v1's step 0; ruling E15-12; the profile's section 7).

The documented summon is `/goal /ship-v2 <slice> [doc]`; a skill cannot arm the Stop hook. This helper reads the
session's own transcript (found exactly as `invocation.py` finds it: the harness's CLAUDE_CODE_SESSION_ID, bound to
this session's records, ruling E9-28) and prints one reading, the core's `references/answer.schema.json` kind
`hook`, which `ship.py hook --reading FILE` takes whole.

WHICH RECORDS COUNT (slice 2 check 1's C2-2, with the control room's send-back 1). Only the harness's own records of
this session (its `sessionId`), never a sidechain, never a record carrying a `message` (a user record, a tool result,
an assistant record or a typed prompt never counts, whatever text it holds). Two shapes are accepted:

1. THE GOAL COMMAND PAIR (the shape the control room measured on a live, `/goal`-armed Claude Code session; that
   version writes no record carrying the old phrase). Two `system` records of subtype `local_command`, in order:
   (a) the command, its `content` opening `<command-name>/goal</command-name>`, its goal text in `<command-args>`;
   (b) its output, with a `commandRun` field, its `content` opening `<local-command-stdout>Goal set: ` and then the
   same goal text. `armed` when the LAST (a) for `/goal` in the session is followed by its (b), and that goal text
   opens with `/ship-v2` and names this run's slice (`--slice`) as its next word. A later `/goal` command replaces the
   goal, whatever it sets; (b) with no (a) before it, or (a) with no (b), sets none.
2. THE CONFIRMATION PHRASE (older harness versions, the fixture's shape): a `system` record whose own `content` opens
   with the Stop hook's confirmation (the module constant `CONFIRMATION`, compared without regard to case), after the
   last prompt the owner typed in this session that invokes `/ship-v2` (a user record whose content is his text, never
   a tool result), when that prompt is a `/goal` one, and with no `/goal` command record (a) after it.

`armed` true with the record or records as `evidence`; `armed` false otherwise, `evidence` null, `how` saying what was
missing. A reading of harness records by their type, subtype, place and content, labelled `helper-derived`, never a
fact the harness enforces. The run proceeds identically armed or not, and the SHIP: block says which.

Exit 0 success, 2 usage, 3 a harness record or the `claude` binary is missing, 1 anything else. stdout carries one
JSON document; diagnostics go to stderr. Python 3.9, standard library only. Side effects: none.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

CONFIRMATION = "stop hook is now active"
SHIP = re.compile(r"(?<![\w/-])/ship-v2(?![\w-])")
GOAL = re.compile(r"(?<![\w/-])/goal(?![\w-])")
COMMAND = "<command-name>/goal</command-name>"
ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
SET = "<local-command-stdout>Goal set: "
EPILOG = """\
Reads this session's transcript for the harness's own records that this run's goal is set: the last /goal command
record and its "Goal set" output naming /ship-v2 and --slice, or, on older versions, the Stop hook's confirmation
record after this run's typed /goal prompt; prints the reading (kind hook) for `ship.py hook --reading FILE`.
--transcript and --session-id are the fixture interface and work only under SHIP_V2_ADAPTER_TEST=1.

Exit 0 success, 2 usage, 3 a harness record or the claude binary is missing, 1 anything else.

Example:
  hook.py --workspace /tmp/widget-workspace > hook.json

Side effects: none. Nothing is written, no network, no model call.
"""


def typed_text(record):
    """The text the owner typed, when `record` is a prompt he typed (a user record whose content is his text, with
    no tool result in it); None otherwise."""
    message = record.get("message")
    if record.get("type") != "user" or not isinstance(message, dict) or message.get("role") != "user":
        return None
    if record.get("isMeta") or record.get("isSidechain"):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list) or not content:
        return None
    texts = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "text" or not isinstance(block.get("text"), str):
            return None
        texts.append(block["text"])
    return "\n".join(texts)


def _own_system(record):
    return record.get("type") == "system" and "message" not in record and not record.get("isSidechain")


def goal_command(record):
    """The goal text of shape (a), a `/goal` command record, or None."""
    content = record.get("content")
    if not _own_system(record) or record.get("subtype") != "local_command" or not isinstance(content, str):
        return None
    if not content.lstrip().startswith(COMMAND):
        return None
    found = ARGS.search(content)
    return found.group(1).strip() if found else ""


def goal_set(record):
    """The goal text of shape (b), the `/goal` command's `Goal set:` output record, or None."""
    content = record.get("content")
    if not _own_system(record) or record.get("subtype") != "local_command" or "commandRun" not in record \
            or not isinstance(content, str):
        return None
    text = content.lstrip()
    if not text.startswith(SET):
        return None
    text = text[len(SET):]
    end = text.find("</local-command-stdout>")
    return (text[:end] if end >= 0 else text).strip()


def names_run(goal_text, slice_name):
    words = goal_text.split()
    return bool(slice_name) and len(words) >= 2 and words[0] == "/ship-v2" and words[1] == slice_name


def is_confirmation(record):
    """The harness's own Stop-hook confirmation record (module docstring, WHICH RECORD COUNTS)."""
    if record.get("type") != "system" or "message" in record or record.get("isSidechain"):
        return False
    content = record.get("content")
    return isinstance(content, str) and content.strip().lower().startswith(CONFIRMATION)


def main():
    parser = _common.JsonParser(prog="hook.py", epilog=EPILOG,
                                description="The Stop-hook reading ship-v2 records on Claude Code.",
                                formatter_class=__import__("argparse").RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", default=None, help="the workspace the session's record must name as a cwd")
    parser.add_argument("--config-dir", default=None, help="the Claude Code config directory (default: "
                                                           "$CLAUDE_CONFIG_DIR, else ~/.claude)")
    parser.add_argument("--transcript", default=None, help="fixture interface, test mode only")
    parser.add_argument("--session-id", default=None, help="fixture interface, test mode only")
    parser.add_argument("--slice", default=None, help="this run's slice: the goal must name it (`/ship-v2 <slice>`)")
    args = parser.parse_args()
    cfg = _common.config_dir(args.config_dir)
    path, session_id, discovery, binding = _common.find_transcript(
        explicit=args.transcript, session_id=args.session_id, cfg=cfg, workspace=args.workspace)
    prompt = None           # (line, is a /goal prompt) of the last typed prompt that invokes ship-v2
    seen = None             # (line, type) of the last confirmation after that prompt (shape 2)
    command = None          # (line, goal text) of the last /goal command record (shape 1 (a))
    goal = None             # (line of (a), line of (b), goal text): its output followed it (shape 1)
    with open(path, "r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or record.get("sessionId") != session_id:
                continue
            text = typed_text(record)
            if text is not None and SHIP.search(text):
                prompt = (number, GOAL.search(text) is not None)
                seen = None
                continue
            asked = goal_command(record)
            if asked is not None:
                command, goal, seen = (number, asked), None, None
                continue
            output = goal_set(record)
            if output is not None:
                if command is not None and goal is None and output == command[1]:
                    goal = (command[0], number, output)
                continue
            if prompt is not None and prompt[1] and is_confirmation(record):
                seen = (number, record.get("type"))
    if goal is not None and names_run(goal[2], args.slice):
        return {"answer_version": 1, "kind": "hook", "harness": _common.HARNESS, "armed": True,
                "how": "the harness's own records set this run's goal: the last /goal command (line %d) and its "
                       "\"Goal set\" output (line %d) name /ship-v2 and slice %s in this session's transcript (%s)"
                       % (goal[0], goal[1], args.slice, discovery),
                "evidence": "%s lines %d and %d (a system local_command record pair)" % (path, goal[0], goal[1])}
    if seen is not None:
        return {"answer_version": 1, "kind": "hook", "harness": _common.HARNESS, "armed": True,
                "how": "the harness's own Stop-hook confirmation record follows this run's /goal prompt (line %d) in "
                       "this session's transcript (%s)" % (prompt[0], discovery),
                "evidence": "%s line %d (a %s record)" % (path, seen[0], seen[1])}
    if command is not None:
        why = ("the last /goal command (line %d) %s" % (command[0], "has no \"Goal set\" output after it"
                                                         if goal is None else
                                                         "sets a goal that does not name /ship-v2 %s"
                                                         % (args.slice or "<slice>: pass --slice")))
    elif prompt is None:
        why = "no prompt typed in this session invokes /ship-v2 and no /goal command record is in it"
    elif not prompt[1]:
        why = "this run's prompt (line %d) carries no /goal" % prompt[0]
    else:
        why = ("no system record after this run's /goal prompt (line %d) carries the Stop hook's confirmation"
               % prompt[0])
    return {"answer_version": 1, "kind": "hook", "harness": _common.HARNESS, "armed": False,
            "how": "no record of this session's transcript shows the harness's Stop-hook confirmation for this "
                   "run: %s (%s; %s)" % (why, discovery, path), "evidence": None}


if __name__ == "__main__":
    sys.exit(_common.run("hook.py", main))
