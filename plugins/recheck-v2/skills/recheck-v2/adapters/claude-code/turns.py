#!/usr/bin/env python3
"""The Claude Code user channel: the session's turn list, and the turn holding
the user's words.

Prints one JSON document on stdout and nothing else; diagnostics go to stderr.
Exit 0 success, 2 usage, 3 a harness record this helper needs is missing, 1
anything else. Python 3.9, standard library only. It reads the session's own
transcript, writes nothing, launches nothing, and never composes a turn
reference the harness did not record.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

EPILOG = """\
turn_ref shape: claude-code:session <sessionId>:msg <uuid>

Roles (E9 lane contract section 6): a `user` record whose message.content is a
string or text blocks is the user's turn; a `user` record carrying tool results
is not a turn and stays out of the map; an `isSidechain` record is a subagent's
and stays out of the map; every other `assistant` record is `assistant`. A
station reference passed with --station-ref is mapped `station`; those values
come from the calling station's payload, never from the executor.

Discovery, in order: --transcript, --session-id, the harness's own
CLAUDE_CODE_SESSION_ID in the tool shell's environment, a hook payload keyed by
CLAUDE_PID, then the newest transcript under the config directory whose records
name --workspace as their cwd (ambiguous with two sessions in one directory:
the `note` field says how many matched).

Example:
  turns.py --find "waive the comma one, ship it"

Side effects: none. Nothing is written, no network, no model call. The user's
text is never printed: --find answers with turn references and timestamps only.
"""


def build_parser():
    parser = argparse.ArgumentParser(
        prog="turns.py",
        description="The session's turn attribution map for recheck-v2 on Claude Code.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--find",
        metavar="WORDS",
        default=None,
        help="report the user turns whose text contains WORDS verbatim (default: none)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="accepted for compatibility; stdout is always JSON (default: on)",
    )
    parser.add_argument(
        "--transcript", default=None, help="an explicit transcript path (default: discovered)"
    )
    parser.add_argument(
        "--session-id", default=None, help="an explicit session id (default: discovered)"
    )
    parser.add_argument(
        "--config-dir",
        default=None,
        help="the Claude Code config directory (default: $CLAUDE_CONFIG_DIR, else ~/.claude)",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="the workspace, for the last discovery candidate (default: none)",
    )
    parser.add_argument(
        "--station-ref",
        action="append",
        default=[],
        metavar="REF",
        help="a turn reference the calling station produced; repeatable (default: none)",
    )
    return parser


def main(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    cfg = _common.config_dir(args.config_dir)
    path, session_id, discovery, note = _common.find_transcript(
        explicit=args.transcript,
        session_id=args.session_id,
        cfg=cfg,
        workspace=args.workspace,
    )
    session = _common.read_session(path, session_id, args.station_ref)

    document = {
        "harness": _common.HARNESS,
        "config_dir": cfg,
        "session_id": session_id,
        "transcript": path,
        "discovery": discovery,
        "note": note,
        "turn_ref_shape": "claude-code:session <sessionId>:msg <uuid>",
        "counts": session["counts"],
        "turn_attribution": session["attribution"],
    }
    if args.find is not None:
        found = []
        for ref, timestamp, text in session["users"]:
            if args.find in text:
                found.append({"turn_ref": ref, "timestamp": timestamp})
        document["find"] = args.find
        document["found"] = found
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=False) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except _common.HelperError as error:
        sys.stderr.write("turns.py: %s\n" % error)
        sys.exit(error.code)
    except KeyboardInterrupt:
        sys.stderr.write("turns.py: interrupted\n")
        sys.exit(1)
    except Exception as error:  # noqa: BLE001 - a helper never prints a traceback in place of JSON
        sys.stderr.write("turns.py: %s: %s\n" % (type(error).__name__, error))
        sys.exit(1)
