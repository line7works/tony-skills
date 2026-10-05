"""ship-v2 on Codex: hook.py, the Stop-hook check as a named capability with a stated result (ruling E15-12).

Codex has no Stop hook and no `/goal` confirmation this core can read, so the reading is always `Hook: NOT armed`,
labelled honestly: `armed` false and `how` saying why, never a guess. The reading is the core's
`answer.schema.json` kind `hook`, which `ship.py hook` takes whole.
"""

import json
import os
import unittest

import testlib

HELPER = "hook.py"


class TheReading(unittest.TestCase):

    def test_never_armed_and_says_why(self):
        code, out, err = testlib.run(HELPER, [])
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual((doc["kind"], doc["harness"], doc["armed"], doc["evidence"]),
                         ("hook", "codex-cli", False, None))
        self.assertIn("NOT armed", doc["how"])

    def test_the_reading_validates_against_the_core(self):
        code, out, err = testlib.run(HELPER, [])
        schema = os.path.join(testlib.SKILL_ROOT, "references", "answer.schema.json")
        self.assertEqual(testlib.validate(json.loads(out), schema), [])

    def test_help_and_usage(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        code, out, err = testlib.run(HELPER, ["--no-such-flag"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
