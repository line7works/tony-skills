"""signoff-v2 on Claude Code, E17 fix round 1 slice B: each lens's reviewer gets its own mandate.

The core's `request` writes `readers/mandate-<lens>.md` per lens and a map from each lens to its
mandate in `request.json` (empty for LIGHT). Request mode binds each `--lens` block's `mandate` to
that lens's own file and drops the map from every block; refuses a `--lens` the map does not
hold; reads `--lens <lens>-r<N>` (N of 2 or more) as Step 3's one re-send of `<lens>`; binds the
single block of a call with no `--lens` to `readers/mandate.md`; and on a `request.json` written
before this change (no map) behaves exactly as before.
"""

import json
import os
import shutil
import tempfile
import unittest

import testlib

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
    with open(os.path.join(run_dir, "packet", "material.md"), "w") as handle:
        handle.write("material\n")
    request = {"protocol_version": 1, "run_id": RUN_ID, "call_id": RUN_ID + "-review",
               "run_dir": os.path.join(readers, "calls"), "row": "claude-session",
               "profile": "repo-with-tools", "workspace": "/tmp/widget-workspace",
               "documents": [os.path.join(run_dir, "packet", "material.md")],
               "mandate": os.path.join(readers, "mandate.md"), "floor": "opus",
               "session_model": "claude-opus-5"}
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
        self.work = tempfile.mkdtemp(prefix="reviewer-e17-")

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def lens_args(self, *lenses):
        out = []
        for lens in lenses:
            out += ["--lens", lens]
        return out

    def call(self, run_dir, *lenses):
        return testlib.run(HELPER, testlib.fixture_args() + ["--run-dir", run_dir]
                           + self.lens_args(*lenses))

    def test_five_lenses_give_five_blocks_each_bound_to_its_own_mandate(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir, *FIVE)
        self.assertEqual(code, 0, err)
        requests = json.loads(out)["requests"]
        self.assertEqual([r["call_id"] for r in requests],
                         ["%s-review-%s" % (RUN_ID, lens) for lens in FIVE])
        for lens, block in zip(FIVE, requests):
            self.assertEqual(block["mandate"],
                             os.path.join(run_dir, "readers", "mandate-%s.md" % lens))
            self.assertNotIn("lens_mandates", block)
        self.assertEqual(len({block["mandate"] for block in requests}), 5)

    def test_a_lens_the_map_does_not_hold_is_refused(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir, "spec", "accessibility")
        self.assertEqual(code, 2, err)
        self.assertIn("accessibility", json.loads(out)["error"])
        self.assertNotIn("requests", json.loads(out))

    def test_any_lens_on_a_light_runs_empty_map_is_refused(self):
        run_dir = fake_run(self.work, [])
        for lens in ("spec", "correctness", "review"):
            code, out, err = self.call(run_dir, lens)
            self.assertEqual(code, 2, (lens, err))

    def test_a_re_send_binds_the_lens_own_mandate_under_a_fresh_call_id(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir, "spec-r2")
        self.assertEqual(code, 0, err)
        block = json.loads(out)["requests"][0]
        self.assertEqual(block["call_id"], RUN_ID + "-review-spec-r2")
        self.assertEqual(block["mandate"], os.path.join(run_dir, "readers", "mandate-spec.md"))
        self.assertEqual(block["raw_path"], os.path.join(run_dir, "readers", "calls",
                                                         RUN_ID + "-review-spec-r2", "raw.md"))
        self.assertNotIn("lens_mandates", block)

    def test_r1_is_not_a_re_send(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir, "spec-r1")
        self.assertEqual(code, 2, err)

    def test_no_lens_binds_the_shared_mandate(self):
        run_dir = fake_run(self.work, FIVE)
        code, out, err = self.call(run_dir)
        self.assertEqual(code, 0, err)
        requests = json.loads(out)["requests"]
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["call_id"], RUN_ID + "-review")
        self.assertEqual(requests[0]["mandate"], os.path.join(run_dir, "readers", "mandate.md"))
        self.assertNotIn("lens_mandates", requests[0])

    def test_a_light_run_with_no_lens_binds_the_shared_mandate(self):
        run_dir = fake_run(self.work, [])
        code, out, err = self.call(run_dir)
        self.assertEqual(code, 0, err)
        block = json.loads(out)["requests"][0]
        self.assertEqual(block["mandate"], os.path.join(run_dir, "readers", "mandate.md"))
        self.assertNotIn("lens_mandates", block)

    def test_a_lens_mandate_outside_the_run_is_refused(self):
        run_dir = fake_run(self.work, FIVE)
        path = os.path.join(run_dir, "request.json")
        with open(path) as handle:
            request = json.load(handle)
        request["lens_mandates"]["spec"] = "/tmp/outside-brief.md"
        with open(path, "w") as handle:
            json.dump(request, handle)
        code, out, err = self.call(run_dir, "spec")
        self.assertEqual(code, 2, err)

    def test_a_request_with_no_map_behaves_as_before(self):
        run_dir = fake_run(self.work, None)
        code, out, err = self.call(run_dir, "spec", "correctness", "anything-at-all")
        self.assertEqual(code, 0, err)
        requests = json.loads(out)["requests"]
        self.assertEqual([r["call_id"] for r in requests],
                         ["%s-review-%s" % (RUN_ID, lens)
                          for lens in ("spec", "correctness", "anything-at-all")])
        for block in requests:
            self.assertEqual(block["mandate"], os.path.join(run_dir, "readers", "mandate.md"))
            self.assertNotIn("lens_mandates", block)
        code, out, err = self.call(run_dir)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["requests"][0]["call_id"], RUN_ID + "-review")


if __name__ == "__main__":
    unittest.main()
