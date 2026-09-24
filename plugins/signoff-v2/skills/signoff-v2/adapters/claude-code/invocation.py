#!/usr/bin/env python3
"""The Claude Code invocation facts for a signoff-v2 run (E13 slice 3).

Prints one JSON document with two objects. `invocation` holds exactly the keys
`references/input.schema.json` closes under `invocation` (mode, caller, run_id, run_dir,
run_date, harness, sessions, model): copy it whole into the input and type none of it.
`measurement` says what was measured and where; it is copied nowhere, and a key of it placed
under `invocation` makes the input invalid (`additionalProperties: false`).

Exit 0 success, 2 usage, 3 a harness record or the `claude` binary is missing (a selected build
result that records no `invocation.session_id` among them), 1 anything else.
Python 3.9, standard library only.
"""

import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

FLOOR = "opus"     # v1 signoff Step 0: reviewers run at Opus-class or better (pick P5)
EPILOG = """\
mode is a harness fact (ruling E9-33): CLAUDE_CODE_SESSION_ATTENDED, else CLAUDE_CODE_ENTRYPOINT,
cross-checked against the transcript's own entrypoint record; a disagreement or no record is
exit 3. A caller route (--caller NAME --run-id ID --run-dir DIR, all three together) keeps the
caller's ids and is always headless.

run_id: signoff-<target token, lowercase>-<YYYYMMDD>-<4 hex from os.urandom>, single use.
run_dir: ${TMPDIR:-/tmp}/signoff-v2/<run_id>, outside every workspace; named, never created.
run_date: --run-date YYYY-MM-DD, else the machine's local calendar date.

sessions.reviewing is this session's own id: CLAUDE_CODE_SESSION_ID, bound to the transcript
(ruling E9-28). sessions.building comes only from the selected build run's own record:
--build-result PATH (that run's result.json, in its own run directory) with --workspace,
--build-doc and --slice, which it must match; its recorded invocation.session_id (the harness session the
build adapter read) is read, never the typed answer.session_id. A selected result that records no
invocation.session_id is exit 3 and no invocation is printed (Astra's N1). With no --build-result
the building session is null and measurement.building_provenance says "unavailable". There is no
flag that types a building session (Astra's F4). Equal to reviewing is the core's independence
refusal.

model.id is the last non-sidechain, non-synthetic assistant record's message.model. floor_class
and floor_met follow ruling E9-3's map against the v1 floor, Opus-class: claude-opus-*,
claude-fable-*, claude-mythos-* are opus (met); claude-sonnet-* sonnet and claude-haiku-* haiku
(not met); anything else, or no model record, is unknown with floor_met null.

--transcript and --session-id are the fixture interface and work only under
SIGNOFF_V2_ADAPTER_TEST=1.

Exit 0 success, 2 usage, 3 a harness record or the claude binary is missing (a selected build
result that records no invocation.session_id among them), 1 anything else.

Example:
  invocation.py --workspace /Users/x/Developer/widget --target-token F

Side effects: none. Nothing is written (the run directory is named, never created: `signoff.py
check-input` creates it), no network, no model call.
"""


def slug(text):
    cleaned = re.sub(r"[^a-z0-9]+", "-", (text or "run").lower()).strip("-")
    return cleaned or "run"


def building_from_result(path, workspace, build_doc, slice_name, error, usage):
    """The building session of the SELECTED build run, bound to this review (Astra's F4).

    The build core writes `result.json` into its own run directory; the file is accepted only
    there and only for the workspace, document and slice this review is of. The building session
    is that run's recorded HARNESS identity, `invocation.session_id`: the session the build
    adapter read from the harness's own record and the build core checked the answer against
    (send-back 1). A selected result without it is REFUSED (`error`, exit 3; Astra's N1): a null
    building session would read as a different session and let this one sign off its own build,
    and the executor's typed `answer.session_id` is never read in its place. Returns (session,
    provenance).
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            result = json.load(handle)
    except (OSError, ValueError) as exc:
        raise error("the build result %s cannot be read: %s" % (path, exc))
    if not isinstance(result, dict):
        raise error("the build result %s is not a build-v2 result object" % path)
    problems = []
    run_dir = result.get("run_dir")
    if not isinstance(run_dir, str) or os.path.realpath(run_dir) != os.path.realpath(
            os.path.dirname(os.path.abspath(path))):
        problems.append("it is not in its own run directory (%r)" % (run_dir,))
    if not isinstance(result.get("workspace"), str) or os.path.realpath(
            result["workspace"]) != os.path.realpath(workspace):
        problems.append("it is for the workspace %r, not %r" % (result.get("workspace"), workspace))
    if result.get("build_doc") != build_doc:
        problems.append("it is for the document %r, not %r" % (result.get("build_doc"), build_doc))
    if result.get("slice") != slice_name:
        problems.append("it is for slice %r, not %r" % (result.get("slice"), slice_name))
    if problems:
        raise usage("the build result %s is not the selected build run of this review: %s"
                    % (path, "; ".join(problems)))
    session = (result.get("invocation") or {}).get("session_id")
    run_name = result.get("run_id") or os.path.basename(run_dir)
    if not isinstance(session, str) or not session:
        raise error(
            "unavailable provenance: selected build run %s records no "
            "invocation.session_id; no reviewing invocation was emitted"
            % run_name)
    return session, "build run %s" % run_name


UNAVAILABLE = ("unavailable provenance: no build run was selected (--build-result), so the building "
               "session is not known and is null; it is never asserted from typed text")


def build_parser():
    p = _common.JsonParser(prog="invocation.py", epilog=EPILOG,
                           description="The invocation facts signoff-v2 needs on Claude Code.",
                           formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workspace", default=None,
                   help="the workspace the session's record must name as a cwd (default: none)")
    p.add_argument("--target-token", default="run",
                   help="the slice the run id carries (default: run)")
    p.add_argument("--run-date", default=None, metavar="YYYY-MM-DD",
                   help="the run date (default: the machine's local calendar date)")
    p.add_argument("--caller", default=None, help="the calling station (default: direct)")
    p.add_argument("--run-id", default=None, help="the caller's run id (default: minted)")
    p.add_argument("--run-dir", default=None, help="the caller's run directory (default: minted)")
    p.add_argument("--build-result", default=None,
                   help="the selected build run's own result.json; its recorded "
                        "invocation.session_id is the building session. Needs --workspace, --build-doc and --slice, "
                        "which it must match (default: none, building session unavailable)")
    p.add_argument("--build-doc", default=None,
                   help="the build doc under review, workspace-relative (with --build-result)")
    p.add_argument("--slice", default=None, help="the slice under review (with --build-result)")
    p.add_argument("--config-dir", default=None,
                   help="the Claude Code config directory (default: $CLAUDE_CONFIG_DIR, else "
                        "~/.claude)")
    p.add_argument("--transcript", default=None, help="fixture interface, test mode only")
    p.add_argument("--session-id", default=None, help="fixture interface, test mode only")
    return p


def main():
    args = build_parser().parse_args()
    ids = [args.caller, args.run_id, args.run_dir]
    if any(ids) and not all(ids):
        raise _common.HelperError("--caller, --run-id and --run-dir are passed together or not "
                                  "at all", 2)
    if args.run_id is not None and not re.match(r"^[A-Za-z0-9._-]+$", args.run_id):
        raise _common.HelperError("--run-id must be one path segment", 2)
    if args.run_dir is not None and not os.path.isabs(args.run_dir):
        raise _common.HelperError("--run-dir must be absolute", 2)
    if args.run_date:
        try:
            datetime.datetime.strptime(args.run_date, "%Y-%m-%d")
        except ValueError:
            raise _common.HelperError("--run-date is a calendar YYYY-MM-DD, got %r"
                                      % args.run_date, 2)
        run_date, date_source = args.run_date, "--run-date"
    else:
        run_date, date_source = datetime.date.today().isoformat(), "the machine's local date"

    version = _common.claude_version()
    cfg = _common.config_dir(args.config_dir)
    path, session_id, discovery, binding = _common.find_transcript(
        explicit=args.transcript, session_id=args.session_id, cfg=cfg, workspace=args.workspace)
    session = _common.read_session(path)
    model_id = session["models"][-1] if session["models"] else None
    floor_class, floor_met = _common.floor_for(model_id, FLOOR)

    mode, mode_source = _common.mode_hint(session)
    if args.caller:
        mode, mode_source = "headless", "%s; a caller route is always headless" % mode_source
    if mode not in ("interactive", "headless"):
        raise _common.HelperError("the interaction mode is a harness fact (ruling E9-33) and no "
                                  "record of it is reachable: %s" % mode_source, 3)

    if args.caller:
        run_id, run_dir, ids_source = args.run_id, args.run_dir, "the caller's, unchanged"
    else:
        run_id = "signoff-%s-%s-%s" % (slug(args.target_token), run_date.replace("-", ""),
                                       os.urandom(2).hex())
        run_dir = os.path.join(os.environ.get("TMPDIR") or "/tmp", "signoff-v2", run_id)
        ids_source = "minted by this helper"
    if args.workspace:
        ws = os.path.realpath(args.workspace)
        rd = os.path.realpath(run_dir)
        if rd == ws or rd.startswith(ws + os.sep):
            raise _common.HelperError("the run directory %s is inside the workspace" % run_dir, 2)

    if args.build_result:
        missing = [flag for flag, value in (("--workspace", args.workspace),
                                            ("--build-doc", args.build_doc),
                                            ("--slice", args.slice)) if not value]
        if missing:
            raise _common.HelperError("--build-result is bound to this review's workspace, "
                                      "document and slice: pass %s" % ", ".join(missing), 2)
        building, provenance = building_from_result(
            args.build_result, args.workspace, args.build_doc, args.slice,
            lambda message: _common.HelperError(message, 3),
            lambda message: _common.HelperError(message, 2))
        building_source = ("invocation.session_id recorded by %s (%s): the session its build "
                           "adapter read from the harness record, bound to this workspace, "
                           "document and slice" % (provenance, args.build_result))
    else:
        building, provenance, building_source = None, "unavailable", UNAVAILABLE
    sandbox, sandbox_source = _common.sandbox_mode(session)
    return {
        "invocation": {
            "mode": mode,
            "caller": args.caller or "direct",
            "run_id": run_id,
            "run_dir": run_dir,
            "run_date": run_date,
            "harness": _common.HARNESS,
            "sessions": {"building": building, "reviewing": session_id},
            "model": {"id": model_id or "unknown", "floor_class": floor_class,
                      "floor_met": floor_met},
        },
        "measurement": {
            "harness_version": version,
            "entry": _common.entry_kind(__file__, cfg),
            "sandbox": sandbox,
            "transcript": path,
            "model_ids_seen": sorted(set(session["models"])),
            "effort": session["efforts"][-1] if session["efforts"] else None,
            "provider_route": _common.provider_route(),
            "workspace_binding": binding,
            "building_provenance": provenance,
            "_sources": {
                "schema": "invocation carries exactly the keys references/input.schema.json "
                          "allows; the executor copies it whole and types none of it",
                "mode": mode_source,
                "ids": ids_source,
                "run_date": date_source,
                "sessions.reviewing": "this session's own id from its transcript: %s" % discovery,
                "sessions.building": building_source,
                "model": "the last non-sidechain, non-synthetic assistant record's "
                         "message.model in %s; floor %s (v1 Step 0), map E9-3" % (path, FLOOR),
                "synthetic_records_skipped": session["synthetic_records"],
                "harness_version": "claude --version",
                "sandbox": sandbox_source or "no record reachable",
            },
        },
    }


if __name__ == "__main__":
    sys.exit(_common.run("invocation.py", main))
