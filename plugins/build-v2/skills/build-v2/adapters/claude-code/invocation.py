#!/usr/bin/env python3
"""The Claude Code invocation facts for a build-v2 run (E13 slice 3).

Prints one JSON document with three objects:

- `invocation`: exactly the three keys `references/input.schema.json` closes under
  `invocation` (`harness`, `caller`, `mode`). Copy it whole into the input; type none of it.
- `answer_fields`: `session_id`, the value the recorded answer's `session_id` carries
  (`references/answer.schema.json`). Copy it into the answer at step 5; never type one.
- `measurement`: what was measured and where it came from. Copied nowhere: the schema closes
  `invocation` with `additionalProperties: false`, so a measurement key there is refused.

Exit 0 success, 2 usage, 3 a harness record or the `claude` binary this helper needs is missing,
1 anything else. stdout carries one JSON document and nothing else; diagnostics go to stderr.
Python 3.9, standard library only.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

EPILOG = """\
invocation.harness is "claude-code". invocation.caller is "user" and invocation.mode "direct"
on a direct request; --caller NAME (the calling station, from its payload) makes them NAME and
"station". Those two are the profile's instruction-bound fields: who asked is not a harness fact.

answer_fields.session_id is the session's own id, read through the harness's
CLAUDE_CODE_SESSION_ID and bound to this session's transcript (ruling E9-28): the file is named
for it, every turn record carries it, and with --workspace a record names that workspace as its
cwd. --transcript and --session-id are the fixture interface and work only under
BUILD_V2_ADAPTER_TEST=1.

Exit 0 success, 2 usage, 3 a harness record or the claude binary is missing, 1 anything else.

Example:
  invocation.py --workspace /Users/x/Developer/widget

Side effects: none. Nothing is written, no network, no model call.
"""


def build_parser():
    parser = _common.JsonParser(prog="invocation.py", epilog=EPILOG,
                                description="The invocation facts build-v2 needs on Claude Code.",
                                formatter_class=__import__("argparse").RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", default=None,
                        help="the workspace the session's record must name as a cwd (default: none)")
    parser.add_argument("--caller", default=None,
                        help="the calling station's name, from its payload (default: none, a "
                             "direct request)")
    parser.add_argument("--config-dir", default=None,
                        help="the Claude Code config directory (default: $CLAUDE_CONFIG_DIR, "
                             "else ~/.claude)")
    parser.add_argument("--transcript", default=None,
                        help="fixture interface, test mode only: an explicit transcript path")
    parser.add_argument("--session-id", default=None,
                        help="fixture interface, test mode only: an explicit session id")
    return parser


def main():
    args = build_parser().parse_args()
    if args.caller is not None and (not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", args.caller)
                                    or args.caller == "user"):
        raise _common.HelperError("--caller names a calling station (one token, not 'user')", 2)
    version = _common.claude_version()
    cfg = _common.config_dir(args.config_dir)
    path, session_id, discovery, binding = _common.find_transcript(
        explicit=args.transcript, session_id=args.session_id, cfg=cfg, workspace=args.workspace)
    session = _common.read_session(path)
    sandbox, sandbox_source = _common.sandbox_mode(session)
    mode, mode_source = _common.mode_hint(session)
    caller = args.caller or "user"
    return {
        "invocation": {
            "harness": _common.HARNESS,
            "caller": caller,
            "mode": "station" if args.caller else "direct",
            "session_id": session_id,
        },
        "answer_fields": {"session_id": session_id},
        "measurement": {
            "harness_version": version,
            "entry": _common.entry_kind(__file__, cfg),
            "sandbox": sandbox,
            "interaction_mode": mode,
            "session_id": session_id,
            "transcript": path,
            "model_id": session["models"][-1] if session["models"] else None,
            "model_ids_seen": sorted(set(session["models"])),
            "effort": session["efforts"][-1] if session["efforts"] else None,
            "provider_route": _common.provider_route(),
            "workspace_binding": binding,
            "_sources": {
                "schema": "invocation carries exactly the keys references/input.schema.json "
                          "allows; the executor copies it whole and types none of it",
                "harness": "this adapter's own harness name",
                "caller_and_mode": ("--caller %s (instruction-bound: the calling station's "
                                    "payload)" % caller) if args.caller else
                                   "no --caller: a direct request (instruction-bound)",
                "harness_version": "claude --version",
                "harness_version_records_in_transcript": sorted(set(session["versions"])),
                "session": discovery,
                "sandbox": sandbox_source or "no record reachable",
                "interaction_mode": mode_source,
                "model_id": "the last non-sidechain, non-synthetic assistant record's "
                            "message.model in %s" % path,
                "synthetic_records_skipped": session["synthetic_records"],
            },
        },
    }


if __name__ == "__main__":
    sys.exit(_common.run("invocation.py", main))
