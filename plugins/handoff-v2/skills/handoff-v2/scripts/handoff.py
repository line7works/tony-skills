#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""handoff.py: the phase driver of handoff-v2 (the E15 back frame's skeleton; slice 1, hand-back 1).

    uv run handoff.py check-input <input.json>
    uv run handoff.py <phase> --run-dir D
    uv run handoff.py identity <workspace>
    uv run handoff.py skill-identity

The phase table is the E15 lane contract's section 9, in its order. The back frame fixes the command
lines; every phase answers `phase-not-built` (exit 10, nothing read or written) until the hand-back
that builds handoff-v2 fills it. `back_core/backdriver.py` runs the table over the station_core
driver's seams; `references/back-loop.md` is the discipline the three back cores share.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from back_core import backdriver  # noqa: E402

STATION = "handoff-v2"

PHASES = [
    {"name": "select", "help": "find the build doc (the doc hunt)", "arguments": [], "handler": None},
    {"name": "photograph", "help": "every card and the open set, the branch and the tree, read now", "arguments": [],
     "handler": None},
    {"name": "gate", "help": "the questions of the session and of the record", "arguments": [], "handler": None},
    {"name": "record-answer", "help": "record the owner's answers to the question gate", "arguments": [],
     "handler": None},
    {"name": "write", "help": "one block at the tail of ## Handoffs, the next move", "arguments": [], "handler": None},
    {"name": "report", "help": "the result and the HANDOFF: block", "arguments": [], "handler": None},
]

if __name__ == "__main__":
    sys.exit(backdriver.main(STATION, PHASES))
