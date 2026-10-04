"""`photograph` (CR-11): every card and the open set from the records component's `state`, the branch, the commits
ahead of the default branch, the tree state and the last-recorded suite state with its provenance, all read by the
script now; never a test run; nothing written outside the run directory.
"""
import json
import os
import unittest

import hlib
import testlib


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class ThePhotograph(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-photo-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def photograph(self, ws, args=(), **station):
        drive, run_dir = hlib.start(self.tmp, ws, **station)
        code, out, err = drive(["select", "--run-dir", run_dir, "--name", hlib.FEATURE])
        self.assertEqual(code, 0, (out, err))
        before = hlib.snapshot(ws)
        code, out, err = drive(["photograph", "--run-dir", run_dir] + list(args))
        self.assertEqual(hlib.snapshot(ws), before)
        return code, out, err, run_dir

    def test_the_cards_and_the_open_set_come_from_the_records(self):
        text = hlib.build_doc(slices=[("A", "the counter", "signed off with conditions", "nothing"),
                                      ("B", "the spinner", "not started", "Slice A")],
                              punch=hlib.review_block())
        ws, _ = hlib.make_repo(self.tmp, text, records=True)
        code, out, err, _ = self.photograph(ws)
        self.assertEqual(code, 0, (out, err))
        cards = dict((c["name"], (c["card"], c["source"])) for c in out["cards"])
        self.assertEqual(cards, {"A": ("signed off with conditions", "records"), "B": ("not started", "records")})
        self.assertEqual([(o["slice"], o["severity"], o["location"]) for o in out["open"]],
                         [("A", "MAJOR", "src/turnstile.py:2")])
        self.assertTrue(out["records"]["exists"])

    def test_without_a_log_the_cards_fall_back_to_the_status_lines_and_say_so(self):
        ws, _ = hlib.make_repo(self.tmp)
        code, out, err, _ = self.photograph(ws)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(set(c["source"] for c in out["cards"]), {"status-line"})
        self.assertFalse(out["records"]["exists"])
        self.assertEqual(out["open"], [])

    def test_the_branch_the_commits_ahead_and_the_tree(self):
        ws, _ = hlib.make_repo(self.tmp, dirt={"notes.txt": "loose work\n"})
        code, out, err, _ = self.photograph(ws)
        self.assertEqual(code, 0, (out, err))
        repo = out["repo"]
        self.assertEqual(repo["branch"], "feat")
        self.assertEqual(repo["ahead"], 1)
        self.assertEqual(repo["base"], "main")
        self.assertEqual(repo["tree"], "dirty")
        self.assertEqual(repo["dirt"], ["notes.txt"])

    def test_no_suite_record_reads_none_recorded(self):
        ws, _ = hlib.make_repo(self.tmp)
        code, out, err, _ = self.photograph(ws)
        self.assertEqual(out["suite"]["state"], "none recorded")

    def test_a_build_v2_result_is_read_with_its_provenance(self):
        ws, _ = hlib.make_repo(self.tmp)
        record = os.path.join(self.tmp, "build-run", "result.json")
        testlib.write_json(record, {"result_version": 1, "run_id": "build-run-7", "slice": "A",
                                    "status": "completed", "build_doc": hlib.DOC,
                                    "checks": [{"name": "unit", "result": "passed"}, {"name": "lint", "result": "failing"},
                                               {"name": "e2e", "result": "not_run"}]})
        code, out, err, _ = self.photograph(ws, ["--suite-record", record])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["suite"]["state"], "1 passed, 1 failing, 1 not run")
        self.assertIn("build-run-7", out["suite"]["provenance"])
        self.assertEqual(out["suite"]["sha256"], hlib.sha(record))

    def test_a_file_that_is_not_a_station_result_is_named_and_not_read_as_a_state(self):
        ws, _ = hlib.make_repo(self.tmp)
        record = os.path.join(self.tmp, "ci.log")
        testlib.write_text(record, "ok\n")
        code, out, err, _ = self.photograph(ws, ["--suite-record", record])
        self.assertEqual(code, 0, (out, err))
        self.assertIn("not read", out["suite"]["state"])

    def test_a_workspace_that_is_not_git_stops(self):
        ws = os.path.join(self.tmp, "plain")
        testlib.write_text(os.path.join(ws, hlib.DOC), hlib.build_doc())
        code, out, err, _ = self.photograph(ws)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "not-git")

    def test_an_earlier_block_edited_since_the_commit_stops(self):
        text = hlib.build_doc(handoffs=hlib.handoff_block("2026-09-25"))
        ws, _ = hlib.make_repo(self.tmp, text)
        edited = text.replace("the bench clock drifts", "the bench clock is fine")
        testlib.write_text(os.path.join(ws, hlib.DOC), edited)
        code, out, err, _ = self.photograph(ws)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "block-edited")

    def test_no_test_command_is_ever_run(self):
        ws, _ = hlib.make_repo(self.tmp, extra_files={"tests/test_marker.py": "open('RAN', 'w').write('x')\n"})
        code, out, err, _ = self.photograph(ws)
        self.assertEqual(code, 0, (out, err))
        self.assertFalse(os.path.exists(os.path.join(ws, "RAN")))


if __name__ == "__main__":
    unittest.main()
