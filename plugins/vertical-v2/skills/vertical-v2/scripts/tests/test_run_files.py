"""vertical-v2's own reads of its run files (the E15 lane contract A12; C1A7-2; contract section 3, "The run
directory").

Every run file vertical-v2 reads or opens itself (`ask.json`, `gate.json` and every other artifact through
`common.read`, the readers sidecars and captures, `local.json` and `local-receipt.json`, `outside.json`,
`trace.jsonl`) is refused, before anything opens the path, when it is a link or anything that is not a
regular file (a named pipe, a socket, a folder), or when it resolves outside the run directory: a named
problem and the run's existing refusal for a damaged run directory (exit 1 where an artifact the phase needs
cannot be read; exit 5 where the local review's record is held to its receipt), never a hang. Each run below
is guarded by a timeout, so a hang fails the test instead of stopping the suite. The frame's own reads of
`checkpoint.json` and `input.json` are frozen and not tested here (the E15 punch list).
"""
import os
import shutil
import subprocess
import sys
import unittest

import testlib
import vlib

TIMEOUT = 60


def run_timed(args, cwd):
    """This core's CLI under a timeout: (exit code, stdout, stderr), or (None, ..., "hung") on a timeout."""
    cmd = [sys.executable, testlib.DRIVER] + [str(a) for a in args]
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=vlib.env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, "", "hung: the phase did not end within %d s" % TIMEOUT
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def plant_pipe(path):
    os.remove(path)
    os.mkfifo(path)


def plant_link(tmp, path):
    """The file moved outside the run directory and a link left in its place (its content unchanged)."""
    outside = os.path.join(tmp, "moved-" + os.path.basename(path))
    shutil.move(path, outside)
    os.symlink(outside, path)


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheRunFiles(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vrunfiles-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def through_ask(self, tmp=None):
        tmp = tmp or self.tmp
        ws, info = vlib.make_repo(tmp, records=True)
        drive, run_dir = vlib.start(tmp, ws)
        code, out, err = vlib.through_ask(drive, tmp, run_dir)
        self.assertEqual(code, 0, (out, err))
        return run_dir

    def assert_refused(self, result, code, name, words):
        got, out, err = result
        self.assertIsNotNone(got, err)
        self.assertEqual(got, code, (out, err))
        text = err if code == 1 else out
        self.assertIn(name, text)
        self.assertIn(words, text)

    def test_a_named_pipe_at_ask_json_refuses_scope_never_a_hang(self):
        run_dir = self.through_ask()
        plant_pipe(os.path.join(run_dir, "ask.json"))
        self.assert_refused(run_timed(["scope", "--run-dir", run_dir], self.tmp), 1, "ask.json", "not a regular file")
        self.assertFalse(os.path.exists(os.path.join(run_dir, "scope.json")))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")))

    def test_a_named_pipe_at_gate_json_refuses_scope_never_a_hang(self):
        run_dir = self.through_ask()
        plant_pipe(os.path.join(run_dir, "gate.json"))
        self.assert_refused(run_timed(["scope", "--run-dir", run_dir], self.tmp), 1, "gate.json", "not a regular file")
        self.assertFalse(os.path.exists(os.path.join(run_dir, "scope.json")))

    def test_a_link_at_ask_json_or_gate_json_refuses_scope(self):
        for name in ("ask.json", "gate.json"):
            with self.subTest(artifact=name):
                tmp = testlib.make_scratch("vrunfiles-link-")
                self.addCleanup(testlib.rmtree, tmp)
                run_dir = self.through_ask(tmp)
                plant_link(tmp, os.path.join(run_dir, name))
                self.assert_refused(run_timed(["scope", "--run-dir", run_dir], tmp), 1, name, "is a link")
                self.assertFalse(os.path.exists(os.path.join(run_dir, "scope.json")))

    def test_a_named_pipe_at_requests_local_json_refuses_record_local(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir)
        answer = vlib.write(self.tmp, "local-answer.json", vlib.local_answer(run_dir))
        plant_pipe(os.path.join(run_dir, "requests-local.json"))
        self.assert_refused(run_timed(["record-local", "--run-dir", run_dir, "--answer", answer], self.tmp), 1,
                            "requests-local.json", "not a regular file")
        self.assertFalse(os.path.exists(os.path.join(run_dir, "local.json")))

    def test_a_named_pipe_or_a_link_at_a_sidecar_refuses_record_local(self):
        for plant in ("pipe", "link"):
            with self.subTest(plant=plant):
                tmp = testlib.make_scratch("vrunfiles-side-")
                self.addCleanup(testlib.rmtree, tmp)
                drive, run_dir, ws, info = vlib.through_local_requests(tmp)
                vlib.file_local_sidecars(run_dir)
                answer = vlib.write(tmp, "local-answer.json", vlib.local_answer(run_dir))
                call_id = vlib.local_ids(run_dir)[0]
                side = os.path.join(run_dir, "readers", call_id, "sidecar.json")
                plant_pipe(side) if plant == "pipe" else plant_link(tmp, side)
                self.assert_refused(run_timed(["record-local", "--run-dir", run_dir, "--answer", answer], tmp), 5,
                                    "sidecar", "is a link" if plant == "link" else "not a regular file")
                self.assertFalse(os.path.exists(os.path.join(run_dir, "local.json")))

    def test_a_named_pipe_at_the_trace_refuses_record_local_never_a_hang(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir)
        answer = vlib.write(self.tmp, "local-answer.json", vlib.local_answer(run_dir))
        trace = os.path.join(run_dir, "trace.jsonl")
        if os.path.lexists(trace):
            os.remove(trace)
        os.mkfifo(trace)
        self.assert_refused(run_timed(["record-local", "--run-dir", run_dir, "--answer", answer], self.tmp), 1,
                            "trace.jsonl", "not a regular file")
        self.assertFalse(os.path.exists(os.path.join(run_dir, "local.json")))

    def test_a_link_at_the_receipt_or_a_named_pipe_at_local_json_refuses_the_verdict(self):
        for name, plant, words in (("local-receipt.json", "link", "is a link"),
                                   ("local.json", "pipe", "not a regular file")):
            with self.subTest(artifact=name):
                tmp = testlib.make_scratch("vrunfiles-rec-")
                self.addCleanup(testlib.rmtree, tmp)
                drive, run_dir, ws, info = vlib.through_record_local(tmp, rows=())
                path = os.path.join(run_dir, name)
                plant_pipe(path) if plant == "pipe" else plant_link(tmp, path)
                self.assert_refused(run_timed(["verdict", "--run-dir", run_dir], tmp), 5, name, words)
                self.assertEqual(vlib.verdict_docs(ws), [])

    def test_a_named_pipe_at_outside_json_refuses_the_verdict_never_read_as_absent(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp)
        plant_pipe(os.path.join(run_dir, "outside.json"))
        self.assert_refused(run_timed(["verdict", "--run-dir", run_dir], self.tmp), 1, "outside.json",
                            "not a regular file")
        self.assertEqual(vlib.verdict_docs(ws), [])


if __name__ == "__main__":
    unittest.main()
