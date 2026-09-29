"""blueprint-v2's `report` (lane L, brief 3.7 and required test 8).

`result.json` validates against the result schema and the semantic checks (through the shared
`validate-result.py`); `station_result` holds the doc, the slice count, and the open questions and
assumptions the script counted; the `BLUEPRINT:` read-back is rendered from the result and its
counts equal the doc's. Every stop leaves a result that validates too.
"""
import os
import re
import unittest

import bplib
import testlib


class _Report(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("bp-report-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def completed(self, files, answer, **kw):
        ws = testlib.git_workspace(self.tmp, "ws", files)
        run = bplib.Run(self.tmp, ws, **kw)
        run.to_harvest()
        self.assertEqual(run.record(answer)[0], 0)
        self.assertEqual(run.write()[0], 0)
        code, out, err = run.report()
        self.assertEqual(code, 10, err)
        return run, out

    def validates(self, run):
        path = os.path.join(run.run_dir, "result.json")
        code, out, err = testlib.run_script("validate-result.py", [path], cwd=run.cwd)
        self.assertEqual(code, 0, out + err)
        return testlib.load_json(path)


class Completed(_Report):

    def test_the_result_validates_and_the_readback_counts_equal_the_doc(self):
        run, out = self.completed(bplib.base_files(), bplib.clean_answer())
        result = self.validates(run)
        self.assertEqual(out, result)
        self.assertEqual((result["status"], result["stop_tag"], result["wrote_nothing"]), ("completed", None, False))
        sr = result["station_result"]
        doc = bplib.read(sr["doc"])
        slices = re.findall(r"^## Slice (\S+) %s (.+)$" % bplib.D, doc, re.M)
        self.assertEqual(sr["slices"], len(slices))
        self.assertEqual((sr["open_questions"], sr["assumptions"]), (1, 1))
        block = sr["readback"]
        lines = block.split("\n")
        self.assertEqual(lines[0], "BLUEPRINT: turnstile")
        self.assertEqual(lines[1], "Doc: %s  %s  Slices: %d  %s  Open questions: 1  %s  Assumptions: 1"
                         % (os.path.relpath(sr["doc"], run.ws), bplib.M, len(slices), bplib.M, bplib.M))
        for name, short in slices:
            self.assertIn("Slice %s %s %s" % (name, bplib.D, short), lines)
        self.assertIn("Open: how often the counter resets", lines)
        self.assertIn("Assumed: the bench script prints the count itself", lines)
        self.assertEqual(lines[-1], "Next: build-v2 slice A when ready.")
        kinds = dict((w["path"], w["kind"]) for w in result["writes"])
        self.assertEqual(kinds[sr["doc"]], "document")
        self.assertEqual(kinds[os.path.join(run.run_dir, "result.json")], "run_artifact")

    def test_an_extended_doc_counts_every_slice_it_holds(self):
        run, out = self.completed(bplib.base_files(build=bplib.BUILD_FILLED), bplib.extension_answer())
        sr = self.validates(run)["station_result"]
        self.assertEqual((sr["doc_action"], sr["slices"], sr["slice_names"], sr["new_slices"]),
                         ("extended", 2, ["A", "B"], ["B"]))
        self.assertIn("Next: build-v2 slice B when ready.", sr["readback"])

    def test_report_only_says_it_wrote_nothing(self):
        run, out = self.completed(bplib.base_files(), bplib.clean_answer(), report_only=True)
        result = self.validates(run)
        self.assertEqual((result["report_only"], result["wrote_nothing"]), (True, True))
        self.assertIn("report-only", result["station_result"]["readback"])

    def test_a_collapsed_gate_is_recorded_with_its_words(self):
        answer = bplib.clean_answer()
        answer["collapsed_gate"] = {"words": "blueprint it and build slice A"}
        run, out = self.completed(bplib.base_files(), answer)
        sr = self.validates(run)["station_result"]
        self.assertEqual(sr["collapsed_gate"], "blueprint it and build slice A")
        self.assertIn("Gate collapsed by the owner's words: blueprint it and build slice A", sr["readback"])

    def test_report_again_answers_the_recorded_result(self):
        run, out = self.completed(bplib.base_files(), bplib.clean_answer())
        again = run.report()
        self.assertEqual((again[0], again[1]), (10, out))


class Stopped(_Report):

    def test_every_stop_leaves_a_valid_result(self):
        answer = bplib.clean_answer()
        answer["ceremony"] = {"needs_build_doc": False, "why": "a one-line change"}
        answer["slices"] = []
        ws = testlib.git_workspace(self.tmp, "ws", bplib.base_files())
        run = bplib.Run(self.tmp, ws)
        run.to_harvest()
        run.record(answer)
        code, out, err = run.write()
        self.assertEqual(code, 10)
        result = self.validates(run)
        self.assertEqual(result["stop_tag"], "no-build-doc")
        self.assertIn("No build doc", result["station_result"]["readback"])
        code, again, err = run.report()
        self.assertEqual((code, again), (10, result))

    def test_report_before_write_is_usage(self):
        ws = testlib.git_workspace(self.tmp, "ws", bplib.base_files())
        run = bplib.Run(self.tmp, ws)
        run.to_harvest()
        self.assertEqual(run.report()[0], 2)


if __name__ == "__main__":
    unittest.main()
