"""E13 full-review fix round, Astra's F6 (MAJOR): the Codex signoff adapter carries no reviewer
transport of its own.

Her `probe_adapters.py` put a local executable in front of `codex` that only captured its
arguments and exited 66; the real helper invoked `codex exec -s danger-full-access -c
approval_policy=never ...` and reported `transport-failed`, `_sources.launch: one codex exec`. The
contract's sections 3 and 10 and the repository invariant say a reviewer is summoned through
`readers` and a core's helper never launches a harness. The adapter now prepares the readers
request and consumes its sidecar; without a qualified readers route for this harness it stops
`lane-unavailable` and names the missing capability. Nothing here launches Codex or a model.
"""

import json
import os
import shutil
import stat
import tempfile
import unittest

import testlib
from test_reviewer import fake_run

HELPER = "reviewer.py"


def capturing_codex(parent):
    """Astra's stand-in: records every argument it is given and exits 66."""
    folder = os.path.join(parent, "capture-bin")
    os.makedirs(folder)
    log = os.path.join(parent, "codex-argv.log")
    script = os.path.join(folder, "codex")
    with open(script, "w") as handle:
        handle.write("#!/bin/sh\nprintf '%%s\\n' \"$*\" >> '%s'\n"
                     "[ \"$1\" = \"--version\" ] && echo 'codex-cli 0.155.1' && exit 0\nexit 66\n"
                     % log)
    os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR)
    return folder, log


class NoPrivateTransport(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="f6-")
        self.run_dir = fake_run(self.work)
        self.bin, self.log = capturing_codex(self.work)
        self.env = {"PATH": self.bin + os.pathsep + "/usr/bin:/bin", "CODEX_SANDBOX": "seatbelt",
                    "CODEX_HOME": self.work}

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def launched(self):
        if not os.path.isfile(self.log):
            return []
        with open(self.log) as handle:
            return [line for line in handle.read().split("\n")
                    if line.strip() and not line.startswith("--version")]

    def test_the_request_mode_launches_nothing_and_stops_lane_unavailable(self):
        code, out, err = testlib.run(HELPER, ["--run-dir", self.run_dir, "--workspace", self.work],
                                     env=self.env)
        self.assertEqual(self.launched(), [], "the helper launched codex: %s" % self.launched())
        self.assertEqual(code, 3, "%s %s" % (out, err))
        doc = json.loads(out)
        self.assertEqual(doc["status"], "lane-unavailable")
        self.assertIn("readers", doc["missing_capability"])
        self.assertEqual(doc["requests"], [])
        self.assertFalse(os.path.isdir(os.path.join(self.run_dir, "readers", "calls")),
                         "nothing is written for a call that cannot be made")

    def test_the_helper_carries_no_launch_path(self):
        with open(os.path.join(testlib.ADAPTER, HELPER)) as handle:
            source = handle.read()
        for word in ("subprocess", "danger-full-access", "approval_policy", "codex exec -"):
            self.assertNotIn(word, source, "reviewer.py still carries %r" % word)

    def test_the_sidecar_of_a_readers_call_is_consumed(self):
        sidecar = os.path.join(self.work, "sidecar.json")
        raw = os.path.join(self.work, "raw.md")
        with open(raw, "w") as handle:
            handle.write("the reviewer's report\n")
        with open(sidecar, "w") as handle:
            json.dump({"status": "ok", "raw_file": raw, "effective_model": "claude-opus-5-5",
                       "transport": "claude-subagent", "call_id": "c-1"}, handle)
        doc = testlib.run_json(HELPER, ["--sidecar", sidecar, "--run-dir", self.run_dir],
                               env=self.env)
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["answer_identity"], {"session_id": "claude-subagent:c-1",
                                                  "model": "claude-opus-5-5"})
        self.assertEqual(self.launched(), [])

    def test_a_lane_unavailable_sidecar_is_mapped_not_retried(self):
        sidecar = os.path.join(self.work, "sidecar.json")
        with open(sidecar, "w") as handle:
            json.dump({"status": "lane-unavailable", "reason": "no route"}, handle)
        doc = testlib.run_json(HELPER, ["--sidecar", sidecar, "--run-dir", self.run_dir],
                               env=self.env)
        self.assertEqual(doc["status"], "lane-unavailable")
        self.assertIsNone(doc["answer_identity"])


if __name__ == "__main__":
    unittest.main()
