#!/usr/bin/env python3
"""The Claude Code verifier capability: the readers request, and the sidecar
readers hands back.

Two modes, one JSON document on stdout in each:

*Request* (`--brief`): the readers request block of `references/verifier.md`
section 6 for row `claude-session`, profile `repo-with-tools`, with
`session_model` filled from the harness's own record of the running session and
`authorized` omitted (a Claude row needs none). This helper launches nothing:
the executor hands the block to `/readers`, which runs the fresh subagent.

*Record* (`--sidecar`): the readers sidecar mapped onto the `record-call` flags
of `verifier.md` section 5, as `{"status", "raw", "model", "kind", "injected",
"refused", "note"}`. It never retries: the core decides (contract section 7).

Diagnostics go to stderr. Exit 0 success, 2 usage, 3 a harness record this
helper needs is missing, 1 anything else. Python 3.9, standard library only.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

ROW = "claude-session"
PROFILE = "repo-with-tools"
PROTOCOL_VERSION = 1

# readers contract, "The Claude lane": the channels the harness adds on the Agent
# route for `repo-with-tools`, measured 2026-09-07 and 2026-09-08 by readers.
AGENT_ROUTE_CHANNELS = [
    "the workspace's instruction files (AGENTS.md, CLAUDE.md) and what they import",
    "the user's global instruction file ~/.claude/CLAUDE.md and its imports",
    "the repo's auto-memory index",
    "the harness's git-status block (branch, recent commit subjects, the git user handle)",
    "the userEmail line",
    "the harness's tool rosters (MCP server instructions, agent types, skills)",
]

# verifier.md section 4. `oversize` has no equivalent and is reported as
# `invalid-request` with the estimate and the limit in the note.
KNOWN_STATUSES = {
    "ok",
    "empty",
    "incomplete",
    "transport-failed",
    "timed-out",
    "capture-failed",
    "cancelled",
    "unknown-model",
    "floor-refused",
    "profile-unsupported",
    "version-mismatch",
    "lane-unavailable",
    "invalid-request",
    "unauthorized",
}
# readers' own vocabulary carries one status E8-27 does not: `oversize`, which
# verifier.md section 6 maps onto `invalid-request` with the estimate and the
# limit in the note.
READERS_ONLY_STATUSES = {"oversize"}

EPILOG = """\
Request mode (default) needs --brief, --workspace, --scratch, --raw, and one of
--call-id or --run-id; the run id is the call id without its -verify suffix
when only --call-id is given. The block's `row` is claude-session and its
`profile` is repo-with-tools, both fixed by the E9 profile; `model`, `effort`,
`output_budget`, and `isolation` are never written (isolation: worktree is not
requested, the scenario runs in the real checkout).

Record mode (--sidecar FILE) maps readers' sidecar onto the record-call flags.
`ok` only when the raw file exists and is non-empty; `oversize` becomes
`invalid-request` with the estimate and the limit in the note.

Test hook: with RECHECK_ADAPTER_TEST=1 and RECHECK_ADAPTER_CANNED=<dir>, record
mode reads <dir>/sidecar.json instead of --sidecar. RECHECK_ADAPTER_CANNED set
without RECHECK_ADAPTER_TEST=1 refuses with reason `canned response outside
test` and reads nothing.

Examples:
  verifier.py --brief /tmp/recheck-v2/<run>/checklist.md \\
      --workspace /Users/x/Developer/widget \\
      --scratch /tmp/recheck-v2/<run>/verifier \\
      --raw /tmp/recheck-v2/<run>/verifier/raw.md --call-id <run>-verify
  verifier.py --sidecar /tmp/readers/<run>/<call>/sidecar.json

Side effects: none. Nothing is written, no network, and this helper makes no
model call of its own: /readers launches the fresh subagent.
"""


def build_parser():
    parser = argparse.ArgumentParser(
        prog="verifier.py",
        description="The readers request for recheck-v2's verifier on Claude Code, and the sidecar map.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--brief", default=None, help="the brief <run_dir>/checklist.md")
    parser.add_argument("--workspace", default=None, help="the absolute repo root under test")
    parser.add_argument("--scratch", default=None, help="<run_dir>/verifier, the only writable place")
    parser.add_argument("--raw", default=None, help="the retained report path for this call")
    parser.add_argument("--call-id", default=None, help="the call id the last command handed out")
    parser.add_argument("--run-id", default=None, help="the run id (default: from --call-id)")
    parser.add_argument(
        "--floor", default="opus", help="policy.model_floor from the input (default: opus)"
    )
    parser.add_argument(
        "--sidecar", default=None, help="record mode: the readers sidecar to map (default: none)"
    )
    parser.add_argument("--transcript", default=None, help="an explicit transcript path")
    parser.add_argument("--session-id", default=None, help="an explicit session id")
    parser.add_argument("--config-dir", default=None, help="the Claude Code config directory")
    return parser


def run_id_from_call(call_id):
    for suffix in ("-verify",):
        index = call_id.rfind(suffix)
        if index > 0:
            return call_id[:index]
    return None


def request_mode(args):
    missing = [
        name
        for name, value in (
            ("--brief", args.brief),
            ("--workspace", args.workspace),
            ("--scratch", args.scratch),
            ("--raw", args.raw),
        )
        if not value
    ]
    if missing:
        sys.stderr.write("verifier.py: request mode needs %s\n" % ", ".join(missing))
        return 2, None
    if not args.call_id and not args.run_id:
        sys.stderr.write("verifier.py: request mode needs --call-id or --run-id\n")
        return 2, None
    run_id = args.run_id or run_id_from_call(args.call_id)
    if not run_id:
        sys.stderr.write(
            "verifier.py: --call-id %r carries no -verify suffix; pass --run-id\n" % args.call_id
        )
        return 2, None
    call_id = args.call_id or ("%s-verify" % run_id)
    brief = os.path.abspath(args.brief)
    if not os.path.isfile(brief):
        raise _common.HelperError("the brief is not a file: %s" % brief, 3)

    cfg = _common.config_dir(args.config_dir)
    path, session_id, discovery, _note = _common.find_transcript(
        explicit=args.transcript, session_id=args.session_id, cfg=cfg, workspace=args.workspace
    )
    session = _common.read_session(path, session_id)
    models = session["models"]
    if not models:
        raise _common.HelperError(
            "no assistant record in %s carries message.model, so session_model cannot be filled"
            % path,
            3,
        )
    session_model = models[-1]

    document = {
        "request": {
            "protocol_version": PROTOCOL_VERSION,
            "run_id": run_id,
            "call_id": call_id,
            "run_dir": os.path.abspath(args.scratch),
            "row": ROW,
            "mandate": brief,
            "workspace": os.path.abspath(args.workspace),
            "profile": PROFILE,
            "raw_path": os.path.abspath(args.raw),
            "floor": args.floor,
            "session_model": session_model,
        },
        "_sources": {
            "session_model": "the last non-sidechain assistant record's message.model in %s"
            % path,
            "session_model_discovery": discovery,
            "authorized": "omitted: row claude-session is an anthropic row and needs no word",
            "row_and_profile": "fixed by the E9 Claude Code profile, not chosen by the executor",
            "never_written": ["model", "effort", "output_budget", "isolation"],
        },
    }
    return 0, document


def map_sidecar(sidecar, raw_override=None):
    status = sidecar.get("status")
    reason = sidecar.get("reason")
    raw = sidecar.get("raw_path") or sidecar.get("raw_file") or raw_override
    note = reason

    if status == "oversize":
        budget = sidecar.get("budget") or {}
        status = "invalid-request"
        note = "oversize: estimate %s, limit %s%s" % (
            budget.get("estimate_tokens"),
            budget.get("limit"),
            (" (%s)" % reason) if reason else "",
        )

    if status == "ok":
        if not raw or not os.path.isfile(raw) or os.path.getsize(raw) == 0:
            status = "capture-failed"
            note = "readers reported ok but the raw file is missing or empty: %s" % raw

    injected = []
    for name in sidecar.get("workdir_instruction_files") or []:
        injected.append("workdir instruction file: %s" % name)
    injected.extend(AGENT_ROUTE_CHANNELS)

    refused = list(sidecar.get("refused_actions") or [])

    return {
        "status": status,
        "raw": raw,
        "model": sidecar.get("effective_model"),
        "kind": sidecar.get("transport"),
        "injected": injected,
        "refused": refused,
        "note": note,
        "_sources": {
            "status": "the sidecar's status (oversize reported as invalid-request, verifier.md section 6)",
            "model": "the sidecar's effective_model",
            "kind": "the sidecar's transport",
            "injected": "the sidecar's workdir_instruction_files plus the channels the readers "
            "contract measures for the claude-session repo-with-tools Agent route",
            "sidecar": sidecar.get("sidecar"),
            "retry": "never here: the core decides (contract section 7)",
        },
    }


def record_mode(args):
    canned = os.environ.get("RECHECK_ADAPTER_CANNED")
    if canned and os.environ.get("RECHECK_ADAPTER_TEST") != "1":
        sys.stderr.write("verifier.py: canned response outside test\n")
        return 1, None
    if canned:
        path = os.path.join(canned, "sidecar.json")
    else:
        path = os.path.abspath(args.sidecar)
    if not os.path.isfile(path):
        raise _common.HelperError("sidecar not found: %s" % path, 3)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            sidecar = json.load(handle)
    except ValueError as exc:
        raise _common.HelperError("sidecar is not JSON (%s): %s" % (exc, path), 1)
    if not isinstance(sidecar, dict):
        raise _common.HelperError("sidecar is not a JSON object: %s" % path, 1)
    status = sidecar.get("status")
    if status not in KNOWN_STATUSES and status not in READERS_ONLY_STATUSES:
        raise _common.HelperError(
            "sidecar status %r is outside the verifier.md section 4 vocabulary" % (status,), 1
        )
    return 0, map_sidecar(sidecar, args.raw)


def main(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    if args.sidecar or os.environ.get("RECHECK_ADAPTER_CANNED"):
        code, document = record_mode(args)
    else:
        code, document = request_mode(args)
    if document is not None:
        sys.stdout.write(json.dumps(document, indent=2, sort_keys=False) + "\n")
    return code


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except _common.HelperError as error:
        sys.stderr.write("verifier.py: %s\n" % error)
        sys.exit(error.code)
    except KeyboardInterrupt:
        sys.stderr.write("verifier.py: interrupted\n")
        sys.exit(1)
    except Exception as error:  # noqa: BLE001
        sys.stderr.write("verifier.py: %s: %s\n" % (type(error).__name__, error))
        sys.exit(1)
