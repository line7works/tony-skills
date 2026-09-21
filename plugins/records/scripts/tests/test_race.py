"""Two processes racing on one log: one wins, one gets exit 7, the log verifies (section 10)."""
import json
import os
import subprocess
import tempfile
import unittest

import testlib

testlib.add_scripts_to_path()
from records_core import identity as identity_mod  # noqa: E402

DOC = testlib.DOC


class Race(unittest.TestCase):
    def setUp(self):
        self.scratch = testlib.make_scratch("records-race-")
        self.batches = os.path.join(self.scratch, "batches")
        os.makedirs(self.batches)
        self.workspace = testlib.make_workspace(self.scratch)
        self.identity = identity_mod.source_identity(self.workspace)
        path = testlib.events_file(self.batches, [testlib.opened(self.identity)], "open.json")
        code, doc, err = testlib.run_json(["append", "--workspace", self.workspace, "--doc", DOC,
                                           "--events", path, "--expect-head", testlib.ZERO])
        self.assertEqual(code, 0, (doc, err))
        self.head = doc["head"]

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def launch(self, name, line):
        event = testlib.raised(identity=self.identity, claim="raised by %s" % name,
                               loc=testlib.location("src/widget.py:%d" % line, "src/widget.py", line))
        path = testlib.events_file(self.batches, [event], "%s.json" % name)
        cmd = [testlib.FLOOR_PYTHON, testlib.CLI, "append", "--workspace", self.workspace,
               "--doc", DOC, "--events", path, "--expect-head", self.head]
        return subprocess.Popen(cmd, cwd=tempfile.gettempdir(), env=testlib.env_for_child(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_one_wins_one_conflicts_and_the_log_verifies(self):
        first = self.launch("first", 91)
        second = self.launch("second", 92)
        results = []
        for proc in (first, second):
            out, err = proc.communicate()
            results.append((proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")))
        codes = sorted(code for code, _, _ in results)
        self.assertEqual(codes, [0, 7], "one wins, one conflicts: %r" % (results,))

        loser = [r for r in results if r[0] == 7][0]
        document = json.loads(loser[1])
        self.assertEqual(document["error"], "conflict")
        self.assertTrue("lock" in document["reason"] or "head" in document["reason"],
                        "the loser is stopped by the lock or by the head: %s" % document["reason"])

        code, doc, err = testlib.run_json(["verify", "--workspace", self.workspace, "--doc", DOC])
        self.assertEqual(code, 0, err)
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["events"], 2, "exactly one of the two racing events landed")

    def test_the_lock_is_not_left_behind(self):
        for proc in (self.launch("a", 93), self.launch("b", 94)):
            proc.communicate()
        from records_core import events as events_mod
        self.assertFalse(os.path.isfile(events_mod.lock_path(testlib.log_file(self.workspace))))


if __name__ == "__main__":
    unittest.main()
