#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""handoff.py: the phase driver of handoff-v2, the end-of-slice photograph (E15 slice 1, hand-back 2).

    uv run handoff.py check-input <input.json>
    uv run handoff.py select --run-dir D [--doc PATH | --name NAME]
    uv run handoff.py photograph --run-dir D [--suite-record FILE] [--records-root DIR]
    uv run handoff.py gate --run-dir D --questions FILE
    uv run handoff.py record-answer --run-dir D --answer FILE
    uv run handoff.py write --run-dir D [--records-root DIR]
    uv run handoff.py report --run-dir D --bottom-line TEXT [--skill-note TEXT]
    uv run handoff.py identity <workspace>
    uv run handoff.py skill-identity

`back_core/backdriver.py` runs this phase table over the station_core driver's seams;
`references/back-loop.md` is the discipline the three back cores share and
`references/handoff-contract.md` is this core's own: what each phase reads, writes and prints, its exits and its
stops. No phase runs a test suite, invokes a station, writes a trace or runs a git command that changes a branch, an
index or a worktree.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from back_core import backdriver  # noqa: E402
from handoff_core import answer, gate, photograph, report, select, write  # noqa: E402

STATION = "handoff-v2"


def _phases():
    return [
        {"name": "select", "help": "find the build doc (the repo's tiers), read it by the line rules, its identity",
         "arguments": [{"flags": ["--doc"], "metavar": "PATH", "default": None,
                        "help": "the build doc the invocation names, or the plan established in this session"},
                       {"flags": ["--name"], "metavar": "NAME", "default": None,
                        "help": "the feature the invocation names, matched by file name, then by an Intent: line"}],
         "handler": select.handler},
        {"name": "photograph", "help": "every card and the open set, the branch and the tree, read now",
         "arguments": [{"flags": ["--suite-record"], "metavar": "FILE", "default": None,
                        "help": "the last-recorded suite state (a build-v2 result.json), read with its provenance"}],
         "handler": photograph.handler},
        {"name": "gate", "help": "the questions of the session and of the record",
         "arguments": [{"flags": ["--questions"], "metavar": "FILE", "required": True,
                        "help": "the session's questions (references/answer.schema.json, kind questions)"}],
         "handler": gate.handler},
        {"name": "record-answer", "help": "the owner's answers held to the record; any unanswered: gate-open",
         "arguments": [{"flags": ["--answer"], "metavar": "FILE", "required": True,
                        "help": "the recorded answers (references/answer.schema.json, kind answers)"}],
         "handler": answer.handler},
        {"name": "write", "help": "the next move, the grants through the records, one block at the tail of ## Handoffs",
         "arguments": [], "handler": write.handler},
        {"name": "report", "help": "the result and the HANDOFF: block",
         "arguments": [{"flags": ["--bottom-line"], "metavar": "TEXT", "default": None,
                        "help": "two or three sentences on one line: what was captured and what to type (required)"},
                       {"flags": ["--skill-note"], "metavar": "TEXT", "default": None,
                        "help": "only when a rule was worked around, reinterpreted or excepted"}],
         "handler": report.handler},
    ]


if __name__ == "__main__":
    sys.exit(backdriver.main(STATION, _phases()))
