"""signoff-v2 on Codex, E17 fix round 1 slice B: each lens's reviewer gets its own mandate.

The same cases as the Claude Code module. The core's `request` writes `readers/mandate-<lens>.md`
per lens and a map from each lens to its mandate in `request.json` (empty for LIGHT). Request
mode binds each `--lens` request's `mandate` to that lens's own file and drops the map from every
request; refuses a `--lens` the map does not hold, writing nothing; reads `--lens <lens>-r<N>`
(N of 2 or more) as Step 3's one re-send of `<lens>`; binds the single request of a call with no
`--lens` to `readers/mandate.md`; and on a `request.json` written before this change (no map)
behaves exactly as before. The mandate check accepts `readers/mandate.md` or one of this run's own
lens mandates, and nothing else.

Every run uses the real `readers.py` beside a fixture roster (the readers route module's
fixture), and nothing is launched.
"""

import json
import os
import shutil
import tempfile
import unittest

import testlib
from test_a3_readers_route import ROOT_VAR, capturing, fixture_readers

HELPER = "reviewer.py"
RUN_ID = "signoff-f-20260923-ab12"
FIVE = ["spec", "correctness", "seams", "security", "tests"]


def fake_run(parent, lenses=None):
    """A run directory with the core's request; `lenses` None writes no map (an older run)."""
    run_dir = os.path.join(parent, RUN_ID)
    readers = os.path.join(run_dir, "readers")
    os.makedirs(os.path.join(run_dir, "packet"))
    os.makedirs(readers)
    with open(os.path.join(readers, "mandate.md"), "w") as handle:
        handle.write("# Reviewer mandate\n")
    request = {"protocol_version": 1, "run_id": RUN_ID, "call_id": RUN_ID + "-review",
               "run_dir": os.path.join(readers, "calls"), "row": "claude-session",
               "profile": "repo-with-tools", "workspace": parent, "documents": [],
               "mandate": os.path.join(readers, "mandate.md"), "floor": "opus",
               "session_model": "gpt-6-astra"}
    if lenses is not None:
        request["lens_mandates"] = {}
        for lens in lenses:
            path = os.path.join(readers, "mandate-%s.md" % lens)
            with open(path, "w") as handle:
                handle.write("# Reviewer mandate, lens %s\n" % lens)
            request["lens_mandates"][lens] = path
    with open(os.path.join(run_dir, "request.json"), "w") as handle:
        json.dump(request, handle)
    return run_dir


class LensMandates(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="codex-e17-")
        self.bin, self.log = capturing(self.work)
        self.env = {"PATH": self.bin + os.pathsep + "/usr/bin:/bin",
                    "READERS_CHECKOUT": os.path.join(self.work, "no-checkout"),
                    ROOT_VAR: fixture_readers(os.path.join(self.work, "readers-fixture"),
                                              "roster-portable-opus.json")}

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def call(self, run_dir, *lenses):
        args = ["--run-dir", run_dir, "--workspace", self.work]
        for lens in lenses:
            args += ["--lens", lens]
        return testlib.run(HELPER, args, env=self.env)

    def written(self, run_dir):
        calls = os.path.join(run_dir, "readers", "calls")
        if not os.path.isdir(calls):
            return []
        return sorted(name for name in os.listdir(calls) if name.endswith(".json"))

    def launched(self):
        if not os.path.isfile(self.log):
            return []
        with open(self.log) as handle:
            return [line for line in handle.read().split("\n") if line.strip()]

    def test_five_lenses_give_five_requests_each_bound_to_its_own_mandate(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir, *FIVE)
        self.assertEqual(code, 0, "%s %s" % (out, err))
        doc = json.loads(out)
        self.assertEqual([r["call_id"] for r in doc["requests"]],
                         ["%s-review-%s" % (RUN_ID, lens) for lens in FIVE])
        for lens, block, path in zip(FIVE, doc["requests"], doc["request_files"]):
            self.assertEqual(block["mandate"],
                             os.path.join(run_dir, "readers", "mandate-%s.md" % lens))
            self.assertNotIn("lens_mandates", block)
            with open(path) as handle:
                self.assertEqual(json.load(handle), block, "the file is the block printed")
        self.assertEqual(len({block["mandate"] for block in doc["requests"]}), 5)
        self.assertEqual(self.launched(), [])

    def test_a_lens_the_map_does_not_hold_is_refused_and_nothing_is_written(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir, "spec", "accessibility")
        self.assertEqual(code, 2, "%s %s" % (out, err))
        self.assertIn("accessibility", err)
        self.assertEqual(self.written(run_dir), [])

    def test_any_lens_on_a_light_runs_empty_map_is_refused(self):
        run_dir = fake_run(self.work, [])
        for lens in ("spec", "correctness", "review"):
            code, out, err = self.call(run_dir, lens)
            self.assertEqual(code, 2, (lens, out, err))
        self.assertEqual(self.written(run_dir), [])

    def test_a_re_send_binds_the_lens_own_mandate_under_a_fresh_call_id(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir, "spec-r2")
        self.assertEqual(code, 0, "%s %s" % (out, err))
        block = json.loads(out)["requests"][0]
        self.assertEqual(block["call_id"], RUN_ID + "-review-spec-r2")
        self.assertEqual(block["mandate"], os.path.join(run_dir, "readers", "mandate-spec.md"))
        self.assertNotIn("lens_mandates", block)
        self.assertEqual(self.written(run_dir), [RUN_ID + "-review-spec-r2.json"])

    def test_r1_is_not_a_re_send(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir, "spec-r1")
        self.assertEqual(code, 2, "%s %s" % (out, err))

    def test_no_lens_binds_the_shared_mandate(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir)
        self.assertEqual(code, 0, "%s %s" % (out, err))
        requests = json.loads(out)["requests"]
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["call_id"], RUN_ID + "-review")
        self.assertEqual(requests[0]["mandate"], os.path.join(run_dir, "readers", "mandate.md"))
        self.assertNotIn("lens_mandates", requests[0])

    def test_a_light_run_with_no_lens_binds_the_shared_mandate(self):
        run_dir = fake_run(self.work, [])
        code, out, err = self.call(run_dir)
        self.assertEqual(code, 0, "%s %s" % (out, err))
        block = json.loads(out)["requests"][0]
        self.assertEqual(block["mandate"], os.path.join(run_dir, "readers", "mandate.md"))
        self.assertNotIn("lens_mandates", block)

    def test_the_mandate_check_accepts_only_this_runs_own_lens_mandates(self):
        run_dir = fake_run(self.work, FIVE)
        path = os.path.join(run_dir, "request.json")
        with open(path) as handle:
            request = json.load(handle)
        # under the run's readers/ but not the lens's own file: refused
        request["lens_mandates"]["spec"] = os.path.join(run_dir, "readers", "mandate-seams.md")
        with open(path, "w") as handle:
            json.dump(request, handle)
        code, out, err = self.call(run_dir, "spec")
        self.assertEqual(code, 2, "%s %s" % (out, err))
        self.assertIn("mandate", err)
        request["lens_mandates"]["spec"] = "/tmp/outside-brief.md"
        with open(path, "w") as handle:
            json.dump(request, handle)
        code, out, err = self.call(run_dir, "spec")
        self.assertEqual(code, 2, "%s %s" % (out, err))
        self.assertEqual(self.written(run_dir), [])

    def test_a_request_with_no_map_behaves_as_before(self):
        run_dir = fake_run(self.work, None)
        code, out, err = self.call(run_dir, "spec", "correctness", "anything-at-all")
        self.assertEqual(code, 0, "%s %s" % (out, err))
        requests = json.loads(out)["requests"]
        self.assertEqual([r["call_id"] for r in requests],
                         ["%s-review-%s" % (RUN_ID, lens)
                          for lens in ("spec", "correctness", "anything-at-all")])
        for block in requests:
            self.assertEqual(block["mandate"], os.path.join(run_dir, "readers", "mandate.md"))
            self.assertNotIn("lens_mandates", block)


if __name__ == "__main__":
    unittest.main()
