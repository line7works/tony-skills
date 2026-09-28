"""E13 full-review fix round, Astra's F6 (MAJOR): the Codex signoff adapter carries no reviewer
transport of its own.

Her `probe_adapters.py` put a local executable in front of `codex` that only captured its
arguments and exited 66; the real helper invoked `codex exec -s danger-full-access -c
approval_policy=never ...` and reported `transport-failed`, `_sources.launch: one codex exec`. The
contract's sections 3 and 10 and the repository invariant say a reviewer is summoned through
`readers` and a core's helper never launches a harness. The adapter prepares the readers request
and consumes its sidecar; since E14 A3 it looks the row up through readers' own `suggest` step
(the one child process it starts, readers' runner, which dispatches nothing) and writes the
request for the executor to hand to readers. Nothing here launches Codex, Claude or a model.
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
    """Astra's stand-in, and one for `claude` beside it: each records every argument and exits 66."""
    folder = os.path.join(parent, "capture-bin")
    os.makedirs(folder)
    log = os.path.join(parent, "codex-argv.log")
    for name in ("codex", "claude"):
        script = os.path.join(folder, name)
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\nprintf '%%s\\n' \"$*\" >> '%s'\n"
                         "[ \"$1\" = \"--version\" ] && echo '%s 0.155.1' && exit 0\nexit 66\n"
                         % (log, name))
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

    def test_the_request_mode_launches_nothing_and_writes_only_the_readers_request(self):
        code, out, err = testlib.run(HELPER, ["--run-dir", self.run_dir, "--workspace", self.work],
                                     env=self.env)
        self.assertEqual(self.launched(), [], "the helper launched a harness: %s" % self.launched())
        self.assertEqual(code, 0, "%s %s" % (out, err))
        doc = json.loads(out)
        self.assertEqual(doc["status"], "ready")
        calls = os.path.join(self.run_dir, "readers", "calls")
        self.assertEqual(sorted(os.listdir(calls)),
                         sorted(["snapshot", os.path.basename(doc["request_files"][0])]),
                         "the request file and readers' own snapshot, nothing else")

    def test_the_helper_carries_no_launch_path(self):
        with open(os.path.join(testlib.ADAPTER, HELPER)) as handle:
            source = handle.read()
        for word in ("danger-full-access", "approval_policy", "codex exec", "claude -p",
                     "os.system", "Popen"):
            self.assertNotIn(word, source, "reviewer.py still carries %r" % word)
        self.assertEqual(source.count("subprocess.run("), 1,
                         "one child process: readers' own suggest step")
        self.assertIn('"suggest"', source)

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
