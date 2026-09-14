#!/usr/bin/env python3
"""The Claude Code invocation facts for a recheck-v2 run.

Prints the `invocation` values the executor copies into the input document:
run id and directory, the harness object, the model object with `floor_met`,
the run date, `session_wrote_fix`, and the turn attribution map. Every value is
read from a harness record, a command, or an explicit flag; none is composed.

Prints one JSON document on stdout and nothing else; diagnostics go to stderr.
Exit 0 success, 2 usage, 3 a harness record or binary this helper needs is
missing, 1 anything else. Python 3.9, standard library only.
"""

import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

EPILOG = """\
run_id: recheck-<target token, lowercase>-<YYYYMMDD>-<4 hex from os.urandom>,
single use. run_dir: ${TMPDIR:-/tmp}/recheck-v2/<run_id>, outside every
workspace. On a caller route pass --caller NAME --run-id ID --run-dir DIR
together and the caller's ids are kept unchanged.

model.id is the last non-sidechain assistant record's message.model in the
session's own transcript (the harness wrote it). floor_class and floor_met
follow ruling E9-3: claude-opus-*, claude-fable-*, claude-mythos- * are class
opus; claude-sonnet-* sonnet; claude-haiku-* haiku; anything else is unknown
with floor_met null.

session_wrote_fix is the executor's honest answer (ruling E9-14): this helper
never guesses it and defaults it to false. mode_hint is a fact, not a pick: a
headless `claude -p` session's tool shell carries
CLAUDE_CODE_SESSION_ATTENDED=0, an interactive one carries 1. The executor
types `invocation.mode` from it, so a headless run never asks a question into a
channel nobody reads (contract section 2).

Example:
  invocation.py --workspace /Users/x/Developer/widget --target-token A \\
      --run-date 2026-09-20

Side effects: none. Nothing is written (the run directory is named, never
created: `recheck.py start` creates it), no network, no model call.
"""

TOKEN_RE = re.compile(r"[^a-z0-9]+")


def slug(text):
    cleaned = TOKEN_RE.sub("-", (text or "run").lower()).strip("-")
    return cleaned or "run"


def mint_run_id(token, run_date):
    stamp = run_date.replace("-", "")
    return "recheck-%s-%s-%s" % (slug(token), stamp, os.urandom(2).hex())


def build_parser():
    parser = argparse.ArgumentParser(
        prog="invocation.py",
        description="The invocation facts recheck-v2 needs on Claude Code.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--workspace", default=None, help="the absolute repo root under test (default: none)"
    )
    parser.add_argument(
        "--target-token",
        default="run",
        help="the slice or target the run id carries (default: run)",
    )
    parser.add_argument(
        "--session-wrote-fix",
        action="store_true",
        help="the driving session authored a fix under review (default: false)",
    )
    parser.add_argument(
        "--run-date",
        default=None,
        metavar="YYYY-MM-DD",
        help="the run date (default: the machine's local calendar date)",
    )
    parser.add_argument("--caller", default=None, help="the calling station's name (default: none)")
    parser.add_argument("--run-id", default=None, help="the caller's run id (default: minted)")
    parser.add_argument(
        "--run-dir", default=None, help="the caller's run directory (default: minted)"
    )
    parser.add_argument(
        "--model-floor",
        default="opus",
        help="policy.model_floor the floor is asserted against (default: opus)",
    )
    parser.add_argument("--transcript", default=None, help="an explicit transcript path")
    parser.add_argument("--session-id", default=None, help="an explicit session id")
    parser.add_argument(
        "--config-dir",
        default=None,
        help="the Claude Code config directory (default: $CLAUDE_CONFIG_DIR, else ~/.claude)",
    )
    parser.add_argument(
        "--station-ref",
        action="append",
        default=[],
        metavar="REF",
        help="a turn reference the calling station produced; repeatable",
    )
    return parser


def main(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    caller_ids = [args.caller, args.run_id, args.run_dir]
    if any(caller_ids) and not all(caller_ids):
        sys.stderr.write(
            "invocation.py: --caller, --run-id and --run-dir are passed together or not at all\n"
        )
        return 2

    if args.run_date:
        try:
            datetime.datetime.strptime(args.run_date, "%Y-%m-%d")
        except ValueError:
            sys.stderr.write("invocation.py: --run-date is YYYY-MM-DD, got %r\n" % args.run_date)
            return 2
        run_date = args.run_date
        date_source = "--run-date"
    else:
        run_date = datetime.date.today().isoformat()
        date_source = "the machine's local calendar date"

    version = _common.claude_version()
    cfg = _common.config_dir(args.config_dir)
    path, session_id, discovery, note = _common.find_transcript(
        explicit=args.transcript,
        session_id=args.session_id,
        cfg=cfg,
        workspace=args.workspace,
    )
    session = _common.read_session(path, session_id, args.station_ref)

    models = session["models"]
    model_id = models[-1] if models else None
    distinct = sorted(set(models))
    floor_class, floor_met = _common.floor_for(model_id, args.model_floor)
    sandbox, sandbox_source = _common.sandbox_mode()
    entry = _common.entry_kind(__file__, cfg)

    settings = {"entrypoint": os.environ.get("CLAUDE_CODE_ENTRYPOINT") or "unknown"}
    effort = session["efforts"][-1] if session["efforts"] else None
    if effort:
        settings["effort_record"] = effort
    env_effort = os.environ.get("CLAUDE_EFFORT")
    if env_effort:
        settings["effort_env"] = env_effort
    settings["permission_mode"] = sandbox

    model = {
        "id": model_id or "unknown",
        "floor_class": floor_class,
        "floor_met": floor_met,
        "provider_route": _common.provider_route(),
        "settings": settings,
    }
    if effort or env_effort:
        model["effort"] = effort or env_effort

    if args.caller:
        run_id = args.run_id
        run_dir = args.run_dir
        ids_source = "the caller's, unchanged"
    else:
        run_id = mint_run_id(args.target_token, run_date)
        tmp = os.environ.get("TMPDIR") or "/tmp"
        run_dir = os.path.join(tmp, "recheck-v2", run_id)
        ids_source = "minted by this helper"

    mode, mode_source = _common.mode_hint()
    document = {
        "run_id": run_id,
        "run_dir": run_dir,
        "harness": {
            "name": _common.HARNESS,
            "version": version,
            "entry": entry,
            "sandbox": sandbox,
        },
        "model": model,
        "run_date": run_date,
        "mode_hint": mode,
        "session_wrote_fix": bool(args.session_wrote_fix),
        "turn_attribution": session["attribution"],
        "_sources": {
            "ids": ids_source,
            "version": "claude --version",
            "entry": "the helper's own path under %s" % cfg,
            "sandbox": sandbox_source or "no record reachable",
            "model_id": "the last non-sidechain assistant record's message.model in %s" % path,
            "model_ids_seen": distinct,
            "run_date": date_source,
            "mode_hint": mode_source,
            "session_wrote_fix": "the executor's flag (ruling E9-14); never guessed",
            "turn_attribution": discovery,
            "turn_attribution_note": note,
            "counts": session["counts"],
        },
    }
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=False) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except _common.HelperError as error:
        sys.stderr.write("invocation.py: %s\n" % error)
        sys.exit(error.code)
    except KeyboardInterrupt:
        sys.stderr.write("invocation.py: interrupted\n")
        sys.exit(1)
    except Exception as error:  # noqa: BLE001
        sys.stderr.write("invocation.py: %s: %s\n" % (type(error).__name__, error))
        sys.exit(1)
