#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""ship.py: the phase driver of ship-v2, the coordinator of one slice's loop (E15 slice 2).

    uv run ship.py check-input <input.json>
    uv run ship.py select --run-dir D [--doc PATH | --name NAME] [--slice NAME]
    uv run ship.py hook --run-dir D --reading FILE
    uv run ship.py visit --run-dir D --station NAME
    uv run ship.py visit --run-dir D --result
    uv run ship.py fix --run-dir D --fixes FILE
    uv run ship.py lap --run-dir D
    uv run ship.py pause --run-dir D --question FILE
    uv run ship.py pause --run-dir D --answer FILE
    uv run ship.py report --run-dir D --bottom-line TEXT [--skill-note TEXT]
    uv run ship.py identity <workspace>
    uv run ship.py skill-identity

The phase table is the E15 lane contract's section 10, in its order. `back_core/backdriver.py` runs it over the
station_core driver's seams; `references/back-loop.md` is the discipline the three back cores share and
`references/ship-contract.md` is this core's own: what each phase reads, writes and prints, its stages, its exits and
its stops. No phase runs a station's phases (the one station command it runs is `skill-identity`), answers the
owner's question, or runs a git command that changes a branch, an index or a worktree; nothing is pushed, merged or
opened.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from back_core import backdriver  # noqa: E402
from ship_core import fix, hook, lap, pause, report, select, visit  # noqa: E402

STATION = "ship-v2"


def _phases():
    return [
        {"name": "select", "help": "find the build doc (the narrowed hunt), read it twice, the slice and its footprint",
         "arguments": [{"flags": ["--doc"], "metavar": "PATH", "default": None,
                        "help": "the build doc the invocation names, or the plan established in this session"},
                       {"flags": ["--name"], "metavar": "NAME", "default": None,
                        "help": "the feature the invocation names, matched by the repo's file-name tiers"},
                       {"flags": ["--slice"], "metavar": "NAME", "default": None,
                        "help": "the slice the owner named when the input named none"}],
         "handler": select.handler},
        {"name": "hook", "help": "record the adapter's armed-or-not reading of the Stop hook",
         "arguments": [{"flags": ["--reading"], "metavar": "FILE", "required": True,
                        "help": "the adapter's hook.py output (references/answer.schema.json, kind hook)"}],
         "handler": hook.handler},
        {"name": "visit", "help": "open a station visit (identity read and traced first), or read its own result",
         "arguments": [{"flags": ["--station"], "metavar": "NAME", "default": None,
                        "help": "the next station in the loop's order: build-v2, signoff-v2 or recheck-v2"},
                       {"flags": ["--result"], "action": "store_true", "default": False,
                        "help": "read the visited station's result.json from the visit's run directory"}],
         "handler": visit.handler},
        {"name": "fix", "help": "record the lap's fixes against the named findings, held to the slice's footprint",
         "arguments": [{"flags": ["--fixes"], "metavar": "FILE", "required": True,
                        "help": "the fixes (references/answer.schema.json, kind fixes)"}],
         "handler": fix.handler},
        {"name": "lap", "help": "the lap counter: open the extra lap; a lap beyond the allowed count is refused",
         "arguments": [], "handler": lap.handler},
        {"name": "pause", "help": "a question to the owner passed through, or his answer recorded (a waiver, a reopening)",
         "arguments": [{"flags": ["--question"], "metavar": "FILE", "default": None,
                        "help": "the question (references/answer.schema.json, kind question)"},
                       {"flags": ["--answer"], "metavar": "FILE", "default": None,
                        "help": "the owner's answer (references/answer.schema.json, kind answer)"}],
         "handler": pause.handler},
        {"name": "report", "help": "the result and the SHIP: block",
         "arguments": [{"flags": ["--bottom-line"], "metavar": "TEXT", "default": None,
                        "help": "two or three sentences on one line: what shipped, its state, what to do next"},
                       {"flags": ["--skill-note"], "metavar": "TEXT", "default": None,
                        "help": "only when a rule was worked around, reinterpreted or excepted"}],
         "handler": report.handler},
    ]


if __name__ == "__main__":
    sys.exit(backdriver.main(STATION, _phases()))
