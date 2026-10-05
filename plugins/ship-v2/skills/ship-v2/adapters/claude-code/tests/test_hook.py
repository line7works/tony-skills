"""ship-v2 on Claude Code: hook.py, the Stop-hook check (ruling E15-12; the profile's section 7).

v1's step 0: the documented summon is `/goal /ship-v2 <slice> [doc]`, a skill cannot arm the Stop hook, and the
run records whether this session showed the confirmation that the Stop hook is active. `hook.py` reads the
session's own transcript (found the way `invocation.py` finds it, ruling E9-28) and prints one reading, armed or not
armed, with the record it saw: `helper-derived`, a reading of a harness record, never a claim the harness enforces.
The reading is the core's `answer.schema.json` kind `hook`, which `ship.py hook` takes whole.
"""

import json
import os
import shutil
import tempfile
import unittest

import testlib

HELPER = "hook.py"
CONFIRMATION = "Stop hook is now active"


def with_records(extra):
    work = tempfile.mkdtemp(prefix="hook-cc-")
    rows = testlib.records() + list(extra)
    return work, testlib.write_records(work, rows)


def confirmation_record(text=CONFIRMATION):
    return {"type": "system", "sessionId": testlib.SESSION, "content": "%s for the goal: /goal /ship-v2 A" % text,
            "cwd": "/tmp/widget-workspace"}


class TheReading(unittest.TestCase):

    def reading(self, extra):
        work, path = with_records(extra)
        try:
            return testlib.run_json(HELPER, ["--transcript", path, "--session-id", testlib.SESSION])
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_armed_when_the_session_shows_the_confirmation(self):
        out = self.reading([confirmation_record()])
        self.assertEqual((out["kind"], out["harness"], out["armed"]), ("hook", "claude-code", True))
        self.assertIn("line", out["evidence"])

    def test_not_armed_without_it(self):
        out = self.reading([])
        self.assertEqual((out["armed"], out["evidence"]), (False, None))
        self.assertIn("no record", out["how"])

    def test_a_confirmation_from_another_session_does_not_count(self):
        other = dict(confirmation_record(), sessionId="00000000-0000-0000-0000-000000000000")
        out = self.reading([other])
        self.assertFalse(out["armed"])

    def test_the_reading_validates_against_the_core(self):
        out = self.reading([confirmation_record()])
        schema = os.path.join(testlib.SKILL_ROOT, "references", "answer.schema.json")
        self.assertEqual(testlib.validate(out, schema), [])

    def test_help_and_usage(self):
        code, out, err = testlib.run(HELPER, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("Side effects", json.loads(out)["help"])
        code, out, err = testlib.run(HELPER, ["--no-such-flag"])
        self.assertEqual(code, 2)

    def test_the_fixture_flags_are_refused_at_run_time(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args() + ["--session-id", testlib.SESSION],
                                     env={testlib.TEST_FLAG: None})
        self.assertEqual(code, 2, err)


if __name__ == "__main__":
    unittest.main()
