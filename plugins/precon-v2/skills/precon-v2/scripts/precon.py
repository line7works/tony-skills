#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""precon.py: the phase driver of precon-v2 (E14; the frame of slice 1, the core of lane P).

    uv run precon.py check-input <input.json>
    uv run precon.py select --run-dir D --hunt scope --name IDEA
    uv run precon.py select --run-dir D --hunt cold-read --name IDEA
    uv run precon.py harvest --run-dir D
    uv run precon.py state --run-dir D
    uv run precon.py request --run-dir D --row ROW [--row ROW ...] [--model ROW=ID] [--session-model ID]
    uv run precon.py record-answer --run-dir D --answer FILE
    uv run precon.py write --run-dir D
    uv run precon.py report --run-dir D
    uv run precon.py identity <workspace>
    uv run precon.py skill-identity

The shared phase driver is `station_core/driver.py`; `references/station-loop.md` is the contract
every front core shares, and `references/precon-v2-contract.md` is this station's own: what each
phase and each own command reads, writes and prints, and its exits. This file holds what is
precon-v2's: its name, its hunt table, its phases and its own commands (`precon_core/`).

The hunt table is the v1 precon station's own homes for an existing scope doc under an idea
slug: the repo doc kit's `docs/scope/*-<idea>.md`, the older flat `docs/<idea>-scope.md`, and
the staging home's `<idea>-scope.md`, all one tier, so a doc found in two homes is `several` and
asked, never picked. The `cold-read` hunt finds the cold-read docs of an earlier exit test, where
the dispositions of a later run go.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from station_core import driver  # noqa: E402
from precon_core import phases  # noqa: E402

STATION = "precon-v2"

HUNTS = {
    "scope": [
        {"home": "repo-scope", "root": "workspace", "globs": ["docs/scope/*-{name}.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-scope.md"], "tier": 1},
        {"home": "staging", "root": "staging", "globs": ["{name}-scope.md"], "tier": 1},
    ],
    "cold-read": [
        {"home": "repo-reviews", "root": "workspace", "globs": ["docs/reviews/*-precon-cold-read-{name}.md"],
         "tier": 1},
        {"home": "staging", "root": "staging", "globs": ["precon-cold-reads/{name}-cold-read-*.md"], "tier": 1},
    ],
}

HANDLERS = {"harvest": phases.harvest, "record-answer": phases.record_answer, "write": phases.write,
            "report": phases.report}

RUN_DIR = {"flags": ["--run-dir"], "metavar": "D", "required": True, "help": "the run directory"}
COMMANDS = [
    {"name": "state", "help": "the counted board of the scope doc as it stands (read-only)",
     "arguments": [RUN_DIR], "handler": phases.state},
    {"name": "request", "help": "build the exit test's readers requests, one per named row",
     "arguments": [RUN_DIR,
                   {"flags": ["--row"], "metavar": "ROW", "action": "append", "default": None,
                    "help": "a readers roster row the owner named for the cold read (repeatable)"},
                   {"flags": ["--model"], "metavar": "ROW=ID", "action": "append", "default": None,
                    "help": "a model id the owner typed against that row"},
                   {"flags": ["--session-model"], "metavar": "ID", "default": None,
                    "help": "the model id this session reports for itself (claude-session only)"},
                   {"flags": ["--roster"], "metavar": "FILE", "default": None,
                    "help": "readers' roster.json (default: the readers plugin beside this one)"}],
     "handler": phases.request},
]


if __name__ == "__main__":
    sys.exit(driver.main(STATION, HUNTS, HANDLERS, commands=COMMANDS))
