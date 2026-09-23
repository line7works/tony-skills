#!/usr/bin/env python3
"""The Codex invocation facts for a build-v2 run (E13 slice 3).

Prints one JSON document with three objects: `invocation` (exactly the keys
`references/input.schema.json` closes under `invocation`: `harness`, `caller`, `mode`; copy it
whole, type none of it), `answer_fields` (`session_id`, the recorded answer's session id: the
executor's own thread) and `measurement` (what was measured and where; copied nowhere).

Exit 0 success, 2 usage, 3 a harness record or the `codex` binary is missing, 1 anything else.
Python 3.9, standard library only.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

EPILOG = """\
invocation.harness is "codex-cli". invocation.caller is "user" and invocation.mode "direct" on a
direct request; --caller NAME (the calling station, from its payload) makes them NAME and
"station": instruction-bound, because who asked is not a harness fact.

answer_fields.session_id is the executor's own thread: the rollout named by CODEX_THREAD_ID under
the sessions root of the home this helper is installed in (E9-40), never under CODEX_HOME (E9-36),
unwritable by this process (E9-37) unless the sealed bench's wall witness holds (SB-8); its
session_meta.id must equal the thread id. A helper outside an install exits 3 unless
BUILD_V2_ADAPTER_TEST=1 and BUILD_V2_ADAPTER_RECORD name a fixture record.

Exit 0 success, 2 usage, 3 a harness record or the codex binary is missing, 1 anything else.

Example:
  invocation.py --workspace /Users/x/Developer/widget

Side effects: none except the E9-37 check, which opens the rollout for append and closes it
without writing. No network, no model call.
"""


def main():
    p = _common.parser("invocation.py", "The invocation facts build-v2 needs on Codex.", EPILOG)
    p.add_argument("--workspace", default=None,
                   help="the workspace the rollout's session_meta.cwd must name (default: none)")
    p.add_argument("--caller", default=None,
                   help="the calling station's name, from its payload (default: a direct request)")
    args = p.parse_args()
    if args.caller is not None and (not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", args.caller)
                                    or args.caller == "user"):
        raise _common.Usage("--caller names a calling station (one token, not 'user')")
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
    model, extra = _common.model_facts(context, records)
    caller = args.caller or "user"
    return {
        "invocation": {"harness": _common.HARNESS, "caller": caller,
                       "mode": "station" if args.caller else "direct"},
        "answer_fields": {"session_id": thread},
        "measurement": {
            "harness_version": version,
            "harness_version_in_record": meta.get("cli_version"),
            "entry": _common.entry_kind(_common.installed_home()),
            "sandbox": _common.sandbox_of(context, wall_note),
            "interaction_mode": mode,
            "session_id": thread,
            "rollout": str(path),
            "model_id": model["id"],
            "provider_route": meta.get("model_provider"),
            "effort": extra.get("effort"),
            "workspace_binding": binding,
            "_sources": {
                "schema": "invocation carries exactly the keys references/input.schema.json "
                          "allows; the executor copies it whole and types none of it",
                "caller_and_mode": ("--caller %s (instruction-bound)" % caller) if args.caller
                                   else "no --caller: a direct request (instruction-bound)",
                "harness_version": "codex --version, beside session_meta.cli_version",
                "session": discovery,
                "interaction_mode": mode_source,
                "model_id": "turn_context.model",
            },
        },
    }


if __name__ == "__main__":
    sys.exit(_common.run("invocation.py", main))
