#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""ship.py: the phase driver of ship-v2 (the E15 back frame's skeleton; slice 1, hand-back 1).

    uv run ship.py check-input <input.json>
    uv run ship.py <phase> --run-dir D
    uv run ship.py identity <workspace>
    uv run ship.py skill-identity

The phase table is the E15 lane contract's section 10, in its order. The back frame fixes the command
lines; every phase answers `phase-not-built` (exit 10, nothing read or written) until slice 2 builds
ship-v2. `back_core/backdriver.py` runs the table over the station_core driver's seams;
`references/back-loop.md` is the discipline the three back cores share.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from back_core import backdriver  # noqa: E402

STATION = "ship-v2"

PHASES = [
    {"name": "select", "help": "find the build doc (the narrowed hunt)", "arguments": [], "handler": None},
    {"name": "hook", "help": "record the adapter's armed-or-not reading", "arguments": [], "handler": None},
    {"name": "visit", "help": "resolve, identify and trace one station visit", "arguments": [], "handler": None},
    {"name": "fix", "help": "record the executor's fixes against the named findings", "arguments": [],
     "handler": None},
    {"name": "lap", "help": "the lap counter", "arguments": [], "handler": None},
    {"name": "pause", "help": "a station's question passed through; a waiver or reopen recorded", "arguments": [],
     "handler": None},
    {"name": "report", "help": "the result and the SHIP: block from the trace", "arguments": [], "handler": None},
]

if __name__ == "__main__":
    sys.exit(backdriver.main(STATION, PHASES))
