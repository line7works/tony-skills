#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""vertical.py: the phase driver of vertical-v2, the whole-build review (E15 slice 1).

    uv run vertical.py check-input <input.json>
    uv run vertical.py gate --run-dir D [--doc PATH | --name NAME] [--records-root DIR]
    uv run vertical.py ask --run-dir D [--readers-root DIR]
    uv run vertical.py ask --run-dir D --local-suggest FILE --outside-suggest FILE [--readers-root DIR]
    uv run vertical.py ask --run-dir D --answer FILE
    uv run vertical.py scope --run-dir D
    uv run vertical.py request --run-dir D [--readers-root DIR]
    uv run vertical.py request --run-dir D --resend LENS --status STATUS [--readers-root DIR]
    uv run vertical.py record-local --run-dir D --answer FILE
    uv run vertical.py request --run-dir D --outside [--row ROW ...] [--readers-root DIR]
    uv run vertical.py record-outside --run-dir D --answer FILE
    uv run vertical.py verdict --run-dir D [--records-root DIR]
    uv run vertical.py report --run-dir D [--bottom-line TEXT] [--skill-note TEXT]
    uv run vertical.py identity <workspace>
    uv run vertical.py skill-identity

`back_core/backdriver.py` runs this phase table over the station_core driver's seams;
`references/back-loop.md` is the discipline the three back cores share and
`references/vertical-contract.md` is this core's own: what each phase reads, writes and prints, its
exits and its stops.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from back_core import backdriver  # noqa: E402
from vertical_core import ask, gate, record, request, scope, verdict  # noqa: E402

STATION = "vertical-v2"
READERS_ROOT = {"flags": ["--readers-root"], "metavar": "DIR", "default": None,
                "help": "readers' root (default: route 3a beside this core, then 3b, the installed shape)"}
ANSWER = {"flags": ["--answer"], "metavar": "FILE", "required": True, "help": "the executor's recorded answer"}


def _phases():
    return [
        {"name": "gate", "help": "the doc, every card and Status: line, the preconditions, the base and the boundary",
         "arguments": [{"flags": ["--doc"], "metavar": "PATH", "default": None,
                        "help": "the build doc the invocation names, or the plan established in this session"},
                       {"flags": ["--name"], "metavar": "NAME", "default": None,
                        "help": "the feature the hunt matches by file name"}],
         "handler": gate.handler},
        {"name": "ask", "help": "the two suggests in v1's order, the ask rendered, the owner's answer recorded",
         "arguments": [READERS_ROOT,
                       {"flags": ["--local-suggest"], "metavar": "FILE", "default": None,
                        "help": "readers' suggest output for the local row (run first, with the floor)"},
                       {"flags": ["--outside-suggest"], "metavar": "FILE", "default": None,
                        "help": "readers' suggest output for the outside rows"},
                       {"flags": ["--answer"], "metavar": "FILE", "default": None,
                        "help": "the owner's answer to the ask (references/answer.schema.json, kind ask)"}],
         "handler": ask.handler},
        {"name": "scope", "help": "the cold packets cut from the reviewed commit, their file and withheld lists", "arguments": [],
         "handler": scope.handler},
        {"name": "request", "help": "one readers request per local lens; --outside after record-local only",
         "arguments": [READERS_ROOT,
                       {"flags": ["--outside"], "action": "store_true",
                        "help": "the outside rows the owner's answer named (after record-local only)"},
                       {"flags": ["--row"], "action": "append", "default": None, "metavar": "ROW",
                        "help": "with --outside: only this named row (repeatable)"},
                       {"flags": ["--resend"], "metavar": "LENS", "default": None,
                        "help": "re-send one local lens once, as a fresh call id"},
                       {"flags": ["--status"], "metavar": "STATUS", "default": None,
                        "help": "with --resend: the READERS status the first call came back with"}],
         "handler": request.handler},
        {"name": "record-local", "help": "the local fleet's merged and verified answer", "arguments": [ANSWER],
         "handler": record.record_local},
        {"name": "record-outside", "help": "the outside fleet's verified answer", "arguments": [ANSWER],
         "handler": record.record_outside},
        {"name": "verdict", "help": "dedupe, Refuted: N, the ledger comparison, the one write", "arguments": [],
         "handler": verdict.handler},
        {"name": "report", "help": "the result and the VERTICAL: block",
         "arguments": [{"flags": ["--bottom-line"], "metavar": "TEXT", "default": None,
                        "help": "two or three sentences: the build's state and what to do next (required)"},
                       {"flags": ["--skill-note"], "metavar": "TEXT", "default": None,
                        "help": "only when a rule was worked around, reinterpreted or excepted"}],
         "handler": verdict.report_handler},
    ]


if __name__ == "__main__":
    sys.exit(backdriver.main(STATION, _phases()))
