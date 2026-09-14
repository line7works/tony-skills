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

Roles (E9 lane contract section 6, ruling E9-22): a `user` record whose
message.content is a string or text blocks is the user's turn; a `user` record
carrying tool results is not a turn and stays out of the map; a `user` record
carrying any of the keys isMeta, turnCompanion, sourceToolUseID or
toolUseResult is one the harness wrote itself and stays out of the map,
whatever the key's value is ({}, false and null are marks too); an isSidechain
record is a subagent's and stays out of the map; every other `assistant` record
is `assistant`. A station reference passed with --station-ref is mapped
`station`; those values come from the calling station's payload, never from the
executor.

Discovery (ruling E9-28), one route: the harness's own CLAUDE_CODE_SESSION_ID
in the tool shell's environment, resolved to <config>/projects/*/<id>.jsonl and
bound to this session (every turn record's sessionId, and a record whose cwd is
--workspace). Unset, ambiguous or mismatched: exit 3 naming it. There is no
fallback to the newest transcript, to another workspace's record, or to a hook
payload. --transcript and --session-id are the fixture interface and are
accepted only under RECHECK_ADAPTER_TEST=1 (default: off; a usage error at run
time). A session record with no user or assistant turns is unusable and is
reported as exit 3, never as an empty map (ruling E9-29).

Example:
  turns.py --workspace /Users/x/Developer/widget --find "waive the comma one, ship it"

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
        "--transcript",
        default=None,
        help="fixture interface, RECHECK_ADAPTER_TEST=1 only: an explicit transcript path "
        "(default: the session's own record through CLAUDE_CODE_SESSION_ID)",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="fixture interface, RECHECK_ADAPTER_TEST=1 only: an explicit session id "
        "(default: the harness's CLAUDE_CODE_SESSION_ID)",
    )
    parser.add_argument(
        "--config-dir",
        default=None,
        help="the Claude Code config directory (default: $CLAUDE_CONFIG_DIR, else ~/.claude)",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="the workspace the session's record must name as a cwd, ruling E9-28's binding "
        "(default: none, and the binding is reported as not run)",
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
    if not session["counts"]["user_turns"] and not session["counts"]["assistant_turns"]:
        # Ruling E9-29: an empty map is a supplied turn list that rejects every
        # reference, so the adapter never prints one in place of a failure.
        raise _common.HelperError(
            "unusable session record: no user or assistant turns in %s" % path, 3
        )

    document = {
        "harness": _common.HARNESS,
        "config_dir": cfg,
        "session_id": session_id,
        "transcript": path,
        "discovery": discovery,
        "workspace_binding": note,
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
