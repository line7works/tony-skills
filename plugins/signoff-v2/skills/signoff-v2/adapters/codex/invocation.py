#!/usr/bin/env python3
"""The Codex invocation facts for a signoff-v2 run (E13 slice 3).

Prints one JSON document: `invocation` (exactly the keys `references/input.schema.json` closes
under `invocation`; copy it whole, type none of it) and `measurement` (copied nowhere).

Exit 0 success, 2 usage, 3 a harness record or the `codex` binary is missing, 1 anything else.
Python 3.9, standard library only.
"""

import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

EPILOG = """\
mode comes from session_meta.originator (E9-33/E9-36): codex_exec is headless, codex_cli_rs
interactive (unmeasured), anything else exit 3. A caller route (--caller NAME --run-id ID
--run-dir DIR, all three together) keeps the caller's ids and is always headless.

run_id: signoff-<target token, lowercase>-<YYYYMMDD>-<4 hex from os.urandom>, single use.
run_dir: ${TMPDIR:-/tmp}/signoff-v2/<run_id>, outside every workspace; named, never created.

sessions.reviewing is this session's own thread: the rollout named by CODEX_THREAD_ID under the
sessions root of the home this helper is installed in (E9-40), refused under CODEX_HOME (E9-36)
and when writable without the wall witness (E9-37, SB-8); its session_meta.id is the value.
sessions.building is null unless --building-session ID (instruction-bound) or --build-result
PATH (the build run's own answer.session_id) names it.

model.id is turn_context.model. floor_class and floor_met follow the pilot's E9-3 Codex map,
PROVISIONAL: gpt-6-astra and gpt-5.6-sol are opus (met); every other id is unknown, floor_met
null. The v1 floor is Opus-class.

A helper outside an install exits 3 unless SIGNOFF_V2_ADAPTER_TEST=1 and
SIGNOFF_V2_ADAPTER_RECORD name a fixture record.

Exit 0 success, 2 usage, 3 a harness record or the codex binary is missing, 1 anything else.

Example:
  invocation.py --workspace /Users/x/Developer/widget --target-token F

Side effects: none except the E9-37 check, which opens the rollout for append and closes it
without writing. No network, no model call.
"""


def slug(text):
    cleaned = re.sub(r"[^a-z0-9]+", "-", (text or "run").lower()).strip("-")
    return cleaned or "run"


def building_from_result(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            result = json.load(handle)
    except (OSError, ValueError) as exc:
        raise _common.Missing("the build result %s cannot be read: %s" % (path, exc))
    session = ((result or {}).get("answer") or {}).get("session_id")
    if not isinstance(session, str) or not session:
        raise _common.Missing("the build result %s records no answer.session_id" % path)
    return session


def main():
    p = _common.parser("invocation.py", "The invocation facts signoff-v2 needs on Codex.", EPILOG)
    p.add_argument("--workspace", default=None,
                   help="the workspace the rollout's session_meta.cwd must name (default: none)")
    p.add_argument("--target-token", default="run", help="the slice the run id carries")
    p.add_argument("--run-date", default=None, help="YYYY-MM-DD (default: today, local)")
    p.add_argument("--caller", default=None, help="the calling station (default: direct)")
    p.add_argument("--run-id", default=None, help="the caller's run id (default: minted)")
    p.add_argument("--run-dir", default=None, help="the caller's run directory (default: minted)")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--building-session", default=None, help="the building session (caller's)")
    group.add_argument("--build-result", default=None, help="the build run's result.json")
    args = p.parse_args()
    ids = [args.caller, args.run_id, args.run_dir]
    if any(ids) and not all(ids):
        raise _common.Usage("--caller, --run-id and --run-dir are passed together or not at all")
    if args.run_id is not None and not re.match(r"^[A-Za-z0-9._-]+$", args.run_id):
        raise _common.Usage("--run-id must be one path segment")
    if args.run_dir is not None and not os.path.isabs(args.run_dir):
        raise _common.Usage("--run-dir must be absolute")
    if args.run_date:
        try:
            datetime.datetime.strptime(args.run_date, "%Y-%m-%d")
        except ValueError:
            raise _common.Usage("--run-date must be a calendar YYYY-MM-DD")
        run_date, date_source = args.run_date, "--run-date"
    else:
        run_date, date_source = datetime.date.today().isoformat(), "the machine's local date"

    version = _common.codex_version()
    path, wall_note, discovery = _common.locate(args.workspace)
    records = _common.read_records(path)
    meta, context = _common.facts(records)
    thread = meta.get("id")
    expected = os.environ.get("CODEX_THREAD_ID")
    if not thread or (expected and _common.installed_home() is not None and thread != expected):
        raise _common.Missing("the rollout's session_meta.id %r is not CODEX_THREAD_ID %r"
                              % (thread, expected))
    binding = _common.check_workspace(meta, args.workspace)
    mode, mode_source = _common.interaction_mode(meta)
    if args.caller:
        mode, mode_source = "headless", "%s; a caller route is always headless" % mode_source
    model, extra = _common.model_facts(context, records)

    if args.caller:
        run_id, run_dir, ids_source = args.run_id, args.run_dir, "the caller's, unchanged"
    else:
        run_id = "signoff-%s-%s-%s" % (slug(args.target_token), run_date.replace("-", ""),
                                       os.urandom(2).hex())
        run_dir = os.path.join(os.environ.get("TMPDIR") or "/tmp", "signoff-v2", run_id)
        ids_source = "minted by this helper"
    if args.workspace:
        ws, rd = os.path.realpath(args.workspace), os.path.realpath(run_dir)
        if rd == ws or rd.startswith(ws + os.sep):
            raise _common.Usage("the run directory %s is inside the workspace" % run_dir)
    if args.build_result:
        building = building_from_result(args.build_result)
        building_source = "answer.session_id of the build result %s" % args.build_result
    elif args.building_session:
        building, building_source = args.building_session, "--building-session (instruction-bound)"
    else:
        building, building_source = None, "unknown: no --building-session and no --build-result"
    return {
        "invocation": {
            "mode": mode, "caller": args.caller or "direct", "run_id": run_id,
            "run_dir": run_dir, "run_date": run_date, "harness": _common.HARNESS,
            "sessions": {"building": building, "reviewing": thread},
            "model": model,
        },
        "measurement": {
            "harness_version": version,
            "harness_version_in_record": meta.get("cli_version"),
            "entry": _common.entry_kind(_common.installed_home()),
            "sandbox": _common.sandbox_of(context, wall_note),
            "rollout": str(path),
            "provider_route": meta.get("model_provider"),
            "effort": extra.get("effort"),
            "context_tokens": extra.get("context_tokens"),
            "workspace_binding": binding,
            "_sources": {
                "schema": "invocation carries exactly the keys references/input.schema.json "
                          "allows; the executor copies it whole and types none of it",
                "mode": mode_source, "ids": ids_source, "run_date": date_source,
                "sessions.reviewing": "session_meta.id of %s (%s)" % (path, discovery),
                "sessions.building": building_source,
                "model": "turn_context.model; the pilot's E9-3 Codex map, provisional",
            },
        },
    }


if __name__ == "__main__":
    sys.exit(_common.run("invocation.py", main))
