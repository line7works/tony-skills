#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""inspect_v2.py: the phase driver of inspect-v2, the plan check (E14 slice 2, lane I).

    uv run inspect_v2.py check-input <input.json>
    uv run inspect_v2.py select --run-dir D --hunt build [--name NAME]
    uv run inspect_v2.py select --run-dir D --hunt scope
    uv run inspect_v2.py choose --run-dir D --hunt build|scope --path P --by intent|owner [--words TEXT]
    uv run inspect_v2.py harvest --run-dir D [--records-root DIR]
    uv run inspect_v2.py packet --run-dir D [--readers-root DIR]
    uv run inspect_v2.py request --run-dir D [--suggest FILE] [--readers-root DIR]
    uv run inspect_v2.py record-answer --run-dir D --answer FILE
    uv run inspect_v2.py write --run-dir D [--records-root DIR]
    uv run inspect_v2.py report --run-dir D
    uv run inspect_v2.py identity <workspace>
    uv run inspect_v2.py skill-identity

The shared phase driver is `station_core/driver.py`; `references/station-loop.md` is the contract
every front core shares and `references/inspect-v2-contract.md` is this core's own: what each phase
and command reads, writes and prints, its exits and its stops. This file holds what is inspect-v2's:
its name, its hunt table, its phases (`inspect_core/`) and its own commands.

The hunt tables are the v1 inspect station's own (its Step 1). `build`: `docs/plans/*-<topic>.md`,
then the older flat `docs/<feature>-build-plan.md`, then any phase or slice doc under `docs/`
or `plan/`, in that order (the two-source narrowing, then the fallback). `scope`: by glob,
never by a guessed slug, over every `docs/scope/*.md`, every older flat `docs/*-scope.md` and
every staging `*-scope.md`, one tier; matching by `Intent:` line is the executor's, recorded with
`choose`.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from station_core import driver  # noqa: E402
from inspect_core import answering, gate, packet, reporting, request, writing  # noqa: E402

STATION = "inspect-v2"

HUNTS = {
    "build": [
        {"home": "repo-plans", "root": "workspace", "globs": ["docs/plans/*-{name}.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-build-plan.md"], "tier": 2},
        {"home": "phase-or-slice", "root": "workspace", "globs": ["docs/*phase*.md", "docs/*slice*.md", "plan/*.md"], "tier": 3},
    ],
    "scope": [
        {"home": "repo-scope", "root": "workspace", "globs": ["docs/scope/*.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/*-scope.md"], "tier": 1},
        {"home": "staging", "root": "staging", "globs": ["*-scope.md"], "tier": 1},
    ],
}

HANDLERS = {"harvest": gate.harvest, "record-answer": answering.handler, "write": writing.handler,
            "report": reporting.handler}

READERS_ROOT = {"flags": ["--readers-root"], "metavar": "DIR", "default": None,
                "help": "readers' root (default: route 3a beside this core, then 3b, the installed shape)"}
RUN_DIR = {"flags": ["--run-dir"], "metavar": "D", "required": True, "help": "the run directory"}

COMMANDS = [
    {"name": "choose", "help": "record the executor's Intent match or the owner's pick among a hunt's several",
     "arguments": [RUN_DIR,
                   {"flags": ["--hunt"], "required": True, "choices": ["build", "scope"], "help": "the hunt"},
                   {"flags": ["--path"], "required": True, "metavar": "P", "help": "one listed candidate"},
                   {"flags": ["--by"], "required": True, "choices": ["intent", "owner"],
                    "help": "intent: the executor matched the Intent line; owner: the owner picked"},
                   {"flags": ["--words"], "default": None, "metavar": "TEXT",
                    "help": "the owner's words, verbatim (required with --by owner)"}],
     "handler": gate.choose},
    {"name": "packet", "help": "one fresh numbered directory per lens: build doc, record, code book",
     "arguments": [RUN_DIR, READERS_ROOT], "handler": packet.handler},
    {"name": "request", "help": "one readers request per lens, the mandates verbatim (exit 5: packet refused)",
     "arguments": [RUN_DIR, READERS_ROOT,
                   {"flags": ["--suggest"], "metavar": "FILE", "default": None,
                    "help": "this run's `readers suggest` output (required when the ask displayed a model)"}],
     "handler": request.handler},
]


if __name__ == "__main__":
    sys.exit(driver.main(STATION, HUNTS, HANDLERS, commands=COMMANDS))
