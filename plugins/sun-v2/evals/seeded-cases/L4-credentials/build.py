#!/usr/bin/env python3
"""Generator for the L4-credentials family of the E16 seeded cases (the lane contract's section 12; slice 1).

Standard library only, Python 3.9. `CASES.md` says what each case holds. `CASES` holds the fixture each case is
built from, what is planted in it and the steps `../observe.py` drives; it states no outcome.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_lib"))

import caselib  # noqa: E402

FAMILY = "L4-credentials"
CASES = {
    "L4-01-clean": {"fixture": "credentials", "drive": [{"do": "look"}, {"do": "go"}, {"do": "status"}]},
    "L4-02-a-fake-fails-echoing-it": {"fixture": "credentials", "drive": [{"do": "look"}, {"do": "go"}, {"do": "status"}],
                                       "plants": [{"plant": "fake-plan", "tool": "fakegit", "entry": {"command": "cas", "do": "echo", "value": "<canary>", "exit": 9}}]},
    "L4-03-a-fake-writes-it-to-its-own-log": {"fixture": "credentials", "drive": [{"do": "look"}, {"do": "go"}],
                                               "plants": [{"plant": "fake-plan", "tool": "fakehost", "entry": {"command": "create", "do": "log", "value": "<canary>"}}]},
    "L4-04-a-kill-mid-call": {"fixture": "credentials", "drive": [{"do": "look"}, {"do": "go", "kill_mid_child": "fakedump"}, {"do": "resume"}]},
    "L4-05-a-missing-tool": {"fixture": "credentials", "plants": [{"plant": "missing-tool"}], "drive": [{"do": "look"}]},
    "L4-06-an-expired-token": {"fixture": "credentials", "drive": [{"do": "look"}, {"do": "go"}],
                                "plants": [{"plant": "fake-plan", "tool": "fakehost", "entry": {"command": "create", "do": "fail", "exit": 7, "stdout": {"kind": "auth"}}}]},
    "L4-07-an-empty-env-pull": {"fixture": "credentials", "drive": [{"do": "look"}, {"do": "go"}],
                                 "plants": [{"plant": "fake-plan", "tool": "fakehost", "entry": {"command": "write", "do": "empty"}}]},
    "L4-08-a-half-env-pull": {"fixture": "credentials", "drive": [{"do": "look"}, {"do": "go"}],
                               "plants": [{"plant": "fake-plan", "tool": "fakehost", "entry": {"command": "write", "do": "half"}}]},
    "L4-09-a-malformed-answer": {"fixture": "credentials", "drive": [{"do": "look"}, {"do": "go"}],
                                  "plants": [{"plant": "fake-plan", "tool": "fakehost", "entry": {"command": "issue", "text": "{\"token\": "}}]},
    "L4-10-a-linked-output-path": {"fixture": "credentials", "drive": [{"do": "look"}, {"do": "link-at-the-env-files-place"}, {"do": "go"}]},
    "L4-11-a-debug-variable-in-the-session": {"fixture": "credentials", "plants": [{"plant": "debug-variable"}], "drive": [{"do": "look"}, {"do": "go"}]},
}

if __name__ == "__main__":
    sys.exit(caselib.make_family(FAMILY, CASES))
