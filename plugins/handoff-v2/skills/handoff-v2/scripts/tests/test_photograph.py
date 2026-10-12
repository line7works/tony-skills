"""`photograph` (CR-11): every card and the open set from the records component's `state`, the branch, the commits
ahead of the default branch, the tree state and the last-recorded suite state with its provenance, all read by the
script now; never a test run; nothing written outside the run directory.
"""
import json
import os
import re
import unittest

import hlib
import testlib

testlib.add_scripts_to_path()
from handoff_core import forms  # noqa: E402


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


RESULT = {"result_version": 1, "run_id": "build-run-7", "slice": "A", "status": "completed", "build_doc": hlib.DOC,
          "checks": [{"name": "unit", "result": "passed"}, {"name": "lint", "result": "failing"},
                     {"name": "e2e", "result": "not_run"}]}
INSIDE = "runs/build-run/result.json"            # a record the workspace holds, committed with the build


def rooted(value):
    """The parts of a suite value that start like an absolute or a home-directory path."""
    return [part for part in value.replace(",", " ").replace("(", " ").split() if part.startswith(("/", "~"))]


@unittest.skipUnless(hlib.records_usable(), "needs jsonschema and the records component beside this core")
class TheSuiteRecordsName(unittest.TestCase):
    """The E15 punch list, item 3 (the E15 lane contract A34 (3)): the suite record is named by its path relative to
    the workspace when it lies inside the workspace, and by its file name alone when it does not; no absolute path
    and no home-directory path reaches the `- Suite:` line of the block or the `Suite:` field of the `HANDOFF:`
    report, for a build-v2 result and for any other file alike. The run id, the slice, the time, the counts and the
    file's hash stay; `photograph.json` keeps the record's resolved path in `suite.path`."""

    def setUp(self):
        self.tmp = testlib.make_scratch("handoff-suite-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws, _ = hlib.make_repo(self.tmp, extra_files={INSIDE: json.dumps(RESULT), "notes/suite.txt": "42 passed\n"})
        self.outside = os.path.join(self.tmp, "elsewhere", "build-run", "result.json")
        testlib.write_json(self.outside, RESULT)

    def photographed(self, record, run="run"):
        drive, run_dir = hlib.start(self.tmp, self.ws, run=run, harness="codex-cli")
        code, out, err = drive(["select", "--run-dir", run_dir, "--name", hlib.FEATURE])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["photograph", "--run-dir", run_dir, "--suite-record", record])
        self.assertEqual(code, 0, (out, err))
        return drive, run_dir, out["suite"]

    def assertNamed(self, suite, name, record):
        """The suite names its record `name` and nothing longer; the rest of the provenance stays."""
        self.assertEqual(suite["state"], "1 passed, 1 failing, 1 not run")
        self.assertRegex(suite["provenance"], r"^build-v2 run build-run-7, slice A, result %s, "
                                              r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$" % re.escape(name))
        self.assertEqual(rooted(suite["state"]) + rooted(suite["provenance"]), [])
        self.assertEqual(suite["sha256"], hlib.sha(record))
        self.assertEqual(suite["path"], os.path.realpath(record), "photograph.json keeps the resolved path")

    def test_a_record_outside_the_workspace_is_named_by_its_file_name_alone(self):
        _, run_dir, suite = self.photographed(self.outside)
        self.assertNamed(suite, "result.json", self.outside)
        self.assertEqual(testlib.load_json(os.path.join(run_dir, "photograph.json"))["suite"], suite)

    def test_a_record_inside_the_workspace_is_named_by_its_path_from_the_workspace(self):
        _, _, suite = self.photographed(os.path.join(self.ws, INSIDE))
        self.assertNamed(suite, INSIDE, os.path.join(self.ws, INSIDE))

    def test_a_record_reached_through_a_link_is_named_by_where_it_lies(self):
        into = os.path.join(self.tmp, "a-link-into-the-workspace.json")
        os.symlink(os.path.join(self.ws, INSIDE), into)
        _, _, suite = self.photographed(into, run="run-in")
        self.assertNamed(suite, INSIDE, os.path.join(self.ws, INSIDE))
        out = os.path.join(self.ws, "latest-result.json")
        os.symlink(self.outside, out)
        _, _, suite = self.photographed(out, run="run-out")
        self.assertNamed(suite, "result.json", self.outside)
        folder = os.path.join(self.tmp, "a-link-to-the-workspace")
        os.symlink(self.ws, folder)
        _, _, suite = self.photographed(os.path.join(folder, INSIDE), run="run-folder")
        self.assertNamed(suite, INSIDE, os.path.join(self.ws, INSIDE))

    def test_any_other_file_is_named_the_same_way(self):
        for run, record, name in (("run-a", os.path.join(self.ws, "notes", "suite.txt"), "notes/suite.txt"),
                                  ("run-b", os.path.join(self.tmp, "elsewhere", "ci.log"), "ci.log")):
            testlib.write_text(record, "42 passed\n")
            _, _, suite = self.photographed(record, run=run)
            self.assertEqual(suite["state"], "recorded at %s, not read as a suite state (not a build-v2 result)" % name)
            self.assertRegex(suite["provenance"], r"^%s, \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$" % re.escape(name))
            self.assertEqual(rooted(suite["state"]) + rooted(suite["provenance"]), [])
            self.assertEqual(suite["path"], os.path.realpath(record))

    def test_a_name_that_starts_with_a_tilde_is_written_behind_a_dot(self):
        record = os.path.join(self.tmp, "elsewhere", "~result.json")
        testlib.write_json(record, RESULT)
        _, _, suite = self.photographed(record)
        self.assertNamed(suite, "./~result.json", record)

    def test_a_record_whose_run_id_is_no_build_v2_run_id_is_not_read_as_a_result(self):
        for run, run_id in (("run-a", "/srv/builds/run-7"), ("run-b", "~/builds/run-7"), ("run-c", "two words")):
            record = os.path.join(self.tmp, "elsewhere", run + ".json")
            testlib.write_json(record, dict(RESULT, run_id=run_id))
            _, _, suite = self.photographed(record, run=run)
            self.assertIn("not read as a suite state", suite["state"], run_id)
            self.assertEqual(rooted(suite["state"]) + rooted(suite["provenance"]), [], run_id)
        record = os.path.join(self.tmp, "elsewhere", "slice.json")
        testlib.write_json(record, dict(RESULT, slice="/srv/a"))
        _, _, suite = self.photographed(record, run="run-d")
        self.assertRegex(suite["provenance"], r"^build-v2 run build-run-7, result slice\.json, ")

    def to_the_report(self, record):
        drive, run_dir, _ = self.photographed(record)
        code, out, err = drive(["gate", "--run-dir", run_dir, "--questions", hlib.questions_file(self.tmp, run_dir)])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["record-answer", "--run-dir", run_dir, "--answer", hlib.answers_file(self.tmp, run_dir)])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["write", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Captured."])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["status"], "completed", out)
        block = [line for line in hlib.read_doc(self.ws).split("\n") if line.startswith("- Suite: ")]
        self.assertEqual(len(block), 1)
        chat = out["station_result"]["chat"]
        self.assertEqual(chat, testlib.read_text(os.path.join(run_dir, "chat.md")))
        return block[0][len("- Suite: "):], forms.parse_report(chat)["suite"]

    def assertSuiteValue(self, record, name):
        in_block, in_report = self.to_the_report(record)
        self.assertEqual(in_block, in_report)
        self.assertRegex(in_block, r"^1 passed, 1 failing, 1 not run \u00b7 build-v2 run build-run-7, slice A, "
                                   r"result %s, \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$" % re.escape(name))
        self.assertEqual(rooted(in_block), [])
        self.assertNotIn(self.tmp, hlib.read_doc(self.ws))

    def test_the_block_and_the_report_name_a_record_outside_by_its_file_name(self):
        self.assertSuiteValue(self.outside, "result.json")

    def test_the_block_and_the_report_name_a_record_inside_by_its_path_from_the_workspace(self):
        self.assertSuiteValue(os.path.join(self.ws, INSIDE), INSIDE)

    def test_the_block_and_the_report_for_any_other_file_through_a_link(self):
        link = os.path.join(self.tmp, "a-link.txt")
        os.symlink(os.path.join(self.ws, "notes", "suite.txt"), link)
        in_block, in_report = self.to_the_report(link)
        self.assertEqual(in_block, in_report)
        self.assertRegex(in_block, r"^recorded at notes/suite\.txt, not read as a suite state \(not a build-v2 result\) "
                                   r"\u00b7 notes/suite\.txt, \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(rooted(in_block), [])
        self.assertNotIn(self.tmp, hlib.read_doc(self.ws))


if __name__ == "__main__":
    unittest.main()
