#!/usr/bin/env python3
"""The Stop-hook check on Claude Code for a ship-v2 run (v1's step 0; ruling E15-12; the profile's section 7).

The documented summon is `/goal /ship-v2 <slice> [doc]`; a skill cannot arm the Stop hook. This helper reads the
session's own transcript (found exactly as `invocation.py` finds it: the harness's CLAUDE_CODE_SESSION_ID, bound to
this session's records, ruling E9-28) and prints one reading, the core's `references/answer.schema.json` kind
`hook`, which `ship.py hook --reading FILE` takes whole:

- `armed` true when a record of THIS session (its `sessionId` this session's) holds the confirmation text "Stop hook
  is now active" anywhere in its strings; the last such record is the `evidence` (its line and type);
- `armed` false otherwise, `evidence` null, `how` saying no record showed it.

Label: `helper-derived`, a reading of a harness record by the confirmation's text, never a fact the harness
enforces; the run proceeds identically armed or not, and the SHIP: block says which.

Exit 0 success, 2 usage, 3 a harness record or the `claude` binary is missing, 1 anything else. stdout carries one
JSON document; diagnostics go to stderr. Python 3.9, standard library only. Side effects: none.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

CONFIRMATION = "stop hook is now active"
EPILOG = """\
Reads this session's transcript for the Stop hook's confirmation ("Stop hook is now active"); prints the reading
(kind hook) for `ship.py hook --reading FILE`. --transcript and --session-id are the fixture interface and work
only under SHIP_V2_ADAPTER_TEST=1.

Exit 0 success, 2 usage, 3 a harness record or the claude binary is missing, 1 anything else.

Example:
  hook.py --workspace /tmp/widget-workspace > hook.json

Side effects: none. Nothing is written, no network, no model call.
"""


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            for text in _strings(item):
                yield text
    elif isinstance(value, list):
        for item in value:
            for text in _strings(item):
                yield text


def main():
    parser = _common.JsonParser(prog="hook.py", epilog=EPILOG,
                                description="The Stop-hook reading ship-v2 records on Claude Code.",
                                formatter_class=__import__("argparse").RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", default=None, help="the workspace the session's record must name as a cwd")
    parser.add_argument("--config-dir", default=None, help="the Claude Code config directory (default: "
                                                           "$CLAUDE_CONFIG_DIR, else ~/.claude)")
    parser.add_argument("--transcript", default=None, help="fixture interface, test mode only")
    parser.add_argument("--session-id", default=None, help="fixture interface, test mode only")
    args = parser.parse_args()
    cfg = _common.config_dir(args.config_dir)
    path, session_id, discovery, binding = _common.find_transcript(
        explicit=args.transcript, session_id=args.session_id, cfg=cfg, workspace=args.workspace)
    seen = None
    with open(path, "r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or record.get("sessionId") != session_id:
                continue
            if any(CONFIRMATION in text.lower() for text in _strings(record)):
                seen = (number, record.get("type"))
    if seen is None:
        return {"answer_version": 1, "kind": "hook", "harness": _common.HARNESS, "armed": False,
                "how": "no record of this session's transcript shows the Stop hook's confirmation (%s; %s)"
                       % (discovery, path), "evidence": None}
    return {"answer_version": 1, "kind": "hook", "harness": _common.HARNESS, "armed": True,
            "how": "a record of this session's own transcript shows the Stop hook's confirmation (%s)" % discovery,
            "evidence": "%s line %d (a %s record)" % (path, seen[0], seen[1])}


if __name__ == "__main__":
    sys.exit(_common.run("hook.py", main))
