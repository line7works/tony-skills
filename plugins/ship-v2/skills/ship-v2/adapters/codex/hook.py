#!/usr/bin/env python3
"""The Stop-hook check on Codex for a ship-v2 run: a named capability with a stated result (ruling E15-12).

Codex has no Stop hook and no `/goal` confirmation this core can read, so the reading is always `Hook: NOT armed`,
labelled honestly: the core's `references/answer.schema.json` kind `hook`, `armed` false, `evidence` null, and `how`
saying why. `ship.py hook --reading FILE` takes it whole; the run proceeds identically.

Exit 0 success, 2 usage, 1 anything else. stdout carries one JSON document. Python 3.9, standard library only.
Side effects: none.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _common  # noqa: E402

EPILOG = """\
Prints the Stop-hook reading (kind hook) for `ship.py hook --reading FILE`: on Codex, always NOT armed.

Exit 0 success, 2 usage, 1 anything else.

Example:
  hook.py > hook.json

Side effects: none. Nothing is read or written, no network, no model call.
"""


def main():
    _common.parser("hook.py", "The Stop-hook reading ship-v2 records on Codex.", EPILOG).parse_args()
    return {"answer_version": 1, "kind": "hook", "harness": _common.HARNESS, "armed": False,
            "how": "Hook: NOT armed. Codex has no Stop hook and no goal confirmation this adapter can read, so the run "
                   "is unwrapped and the SHIP: block says so (ruling E15-12)",
            "evidence": None}


if __name__ == "__main__":
    sys.exit(_common.run("hook.py", main))
