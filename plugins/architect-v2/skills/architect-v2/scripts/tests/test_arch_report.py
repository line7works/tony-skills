"""`report` (brief 3.8, CR-13, required test 8), through the real CLI.

The result validates against the result schema and the semantic checks (the shared validator,
run as a script); every write of the run is in `writes` with its hashes, which match the bytes on
disk; `station_result` names the doc, the run number, the visual, the publish, the candidates and
the pick, and the rulings count; the chat block is rendered from the result. A scope-doc run whose
review offer has no outcome stops `review-pending`.
"""
import os
import unittest

import archlib
import testlib

URL = "https://example.invalid/artifact/turnstile"


class Report(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-report-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp)
        self.run = archlib.ArchRun(self.tmp, self.ws)
        code, doc, out, err = self.run.to_harvest()
        self.assertEqual(code, 0, out + err)

    def finish(self, answer):
        for code, doc, out, err in self.run.full(answer, url=URL)[:-1]:
            self.assertEqual(code, 0, out + err)
        return self.run.report()

    def validated(self):
        path = os.path.join(self.run.run_dir, "result.json")
        code, out, err = testlib.run_script("validate-result.py", [path], cwd=self.run.cwd)
        self.assertEqual(code, 0, out + err)
        return testlib.load_json(path)

    def test_a_declined_review_completes(self):
        code, doc, out, err = self.finish(archlib.clean_answer(review={"outcome": "declined", "date": archlib.TODAY}))
        self.assertEqual(code, 10, out + err)
        result = self.validated()
        self.assertEqual((result["status"], result["stop_tag"]), ("completed", None))
        sr = result["station_result"]
        doc_path = os.path.join(self.ws, "docs", "architecture", "%s-turnstile.md" % archlib.TODAY)
        html = os.path.join(self.ws, "docs", "architecture", "turnstile-architecture.html")
        self.assertEqual(sr["doc_path"], doc_path)
        self.assertEqual(sr["run_number"], 1)
        self.assertEqual(sr["visual_path"], html)
        self.assertTrue(sr["published"])
        self.assertEqual(sr["artifact_url"], URL)
        self.assertEqual(sr["publish_outcome"], "published")
        self.assertEqual(sr["candidates"], ["module", "service"])
        self.assertEqual(sr["pick"], "module")
        self.assertEqual(sr["rulings_count"], 0)
        self.assertEqual(sr["review"], "declined")
        self.assertEqual(sr["passed_forward"], [archlib.ids()["decided"]])
        on_disk = {}
        for w in result["writes"]:
            if w["kind"] == "document":
                on_disk[w["path"]] = w["sha256_after"]
        self.assertEqual(on_disk[doc_path], archlib.sha(doc_path))
        self.assertEqual(on_disk[html], archlib.sha(html))
        self.assertFalse(result["wrote_nothing"])
        self.assertIn("scope", result["selection"])
        self.assertIn("architecture", result["selection"])
        chat = doc["chat"]
        self.assertTrue(chat.startswith("ARCHITECT: Turnstile\n"), chat)
        self.assertIn("Doc: %s\n" % doc_path, chat)
        self.assertIn("Artifact: %s\n" % URL, chat)
        self.assertIn("Run: 1\n", chat)
        self.assertIn("Review: declined\n", chat)
        self.assertIn("components in v0 2", chat)
        self.assertIn("poured-concrete decisions 2", chat)
        self.assertIn("deferred items 1", chat)
        text = testlib.read_text(doc_path)
        self.assertIn("Blind review: declined %s\n" % archlib.TODAY, text)

    def test_a_pending_review_stops(self):
        code, doc, out, err = self.finish(archlib.clean_answer())
        self.assertEqual(code, 10, out + err)
        result = self.validated()
        self.assertEqual((result["status"], result["stop_tag"]), ("stopped", "review-pending"))
        self.assertIn("none yet", result["reason"])

    def test_a_failed_review_completes_and_says_so(self):
        code, doc, out, err = self.finish(archlib.clean_answer(
            review={"outcome": "failed", "date": archlib.TODAY, "reason": "transport-failed: the lane timed out"}))
        self.assertEqual(code, 10, out + err)
        result = self.validated()
        self.assertEqual(result["status"], "completed")
        self.assertIn("Review: failed %s transport-failed: the lane timed out" % archlib.D, doc["chat"])

    def test_a_done_review_names_each_failed_lane(self):
        """R6 (CA1-7): a lane that did not return is named beside the done review, in v1's words."""
        for step in (self.run.record(archlib.clean_answer()), self.run.write(), self.run.render(),
                     self.run.publish(URL), self.run.request("gpt-astra", "gemini")):
            self.assertEqual(step[0], 0, step[2] + step[3])
        take = os.path.join(self.tmp, "take.md")
        testlib.write_text(take, "a module, no server\n")
        code, doc, out, err = self.run.save_take("gpt-astra", take)
        self.assertEqual(code, 0, out + err)
        rel = os.path.relpath(doc["path"], self.ws)
        a = archlib.clean_answer(review={"outcome": "done", "spine": "a module, no server",
                                         "failed_lanes": [{"row": "gemini", "reason": "transport-failed: timed out"}]})
        for step in (self.run.record(a), self.run.write(), self.run.render(), self.run.publish(URL)):
            self.assertEqual(step[0], 0, step[2] + step[3])
        code, doc, out, err = self.run.report()
        self.assertEqual(code, 10, out + err)
        self.assertIn("Review: done at %s, with gemini failed %s transport-failed: timed out\n" % (rel, archlib.D),
                      doc["chat"])
        result = self.validated()
        self.assertEqual(result["station_result"]["review_failed_lanes"],
                         [{"row": "gemini", "reason": "transport-failed: timed out"}])

    def test_failed_lanes_rows_are_checked(self):
        """CA2-5: each failed lane is a row a request of this run built, with no saved take, once."""
        for step in (self.run.record(archlib.clean_answer()), self.run.write(), self.run.render(),
                     self.run.publish(URL), self.run.request("gpt-astra", "gemini")):
            self.assertEqual(step[0], 0, step[2] + step[3])
        take = os.path.join(self.tmp, "take.md")
        testlib.write_text(take, "a module, no server\n")
        self.assertEqual(self.run.save_take("gpt-astra", take)[0], 0)
        for lanes in ([{"row": "gpt-astra", "reason": "timed out"}],
                      [{"row": "qwen", "reason": "timed out"}],
                      [{"row": "nobody", "reason": "timed out"}],
                      [{"row": "gemini", "reason": "timed out"}, {"row": "gemini", "reason": "timed out again"}]):
            a = archlib.clean_answer(review={"outcome": "done", "spine": "a module", "failed_lanes": lanes})
            before = archlib.listing(self.run.run_dir)
            code, doc, out, err = self.run.record(a)
            self.assertEqual(code, 5, (lanes, out + err))
            self.assertIn("review-fields", [r["rule"] for r in doc["refusals"]], lanes)
            self.assertEqual(archlib.listing(self.run.run_dir), before)
        a = archlib.clean_answer(review={"outcome": "done", "spine": "a module",
                                         "failed_lanes": [{"row": "gemini", "reason": "timed out"}]})
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 0, out + err)

    def test_failed_lanes_on_a_review_that_is_not_done_is_refused(self):
        a = archlib.clean_answer(review={"outcome": "declined", "date": archlib.TODAY,
                                         "failed_lanes": [{"row": "gemini", "reason": "timed out"}]})
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)
        self.assertIn("review-fields", [r["rule"] for r in doc["refusals"]])

    def test_report_twice_prints_the_same_result(self):
        self.finish(archlib.clean_answer(review={"outcome": "declined", "date": archlib.TODAY}))
        first = testlib.read_text(os.path.join(self.run.run_dir, "result.json"))
        code, doc, out, err = self.run.report()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(testlib.read_text(os.path.join(self.run.run_dir, "result.json")), first)

    def test_report_before_write_is_usage(self):
        self.run.record(archlib.clean_answer())
        self.assertEqual(self.run.report()[0], 2)

    def test_a_harvest_stop_reports_its_result(self):
        tmp = testlib.make_scratch("arch-report-")
        self.addCleanup(testlib.rmtree, tmp)
        ws = archlib.repo_workspace(tmp, files={"docs/scope/2026-09-21-turnstile-two.md": archlib.SCOPE})
        run = archlib.ArchRun(tmp, ws)
        self.assertEqual(run.to_harvest()[0], 10)
        code, doc, out, err = run.report()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "selection-several")
        path = os.path.join(run.run_dir, "result.json")
        code, out, err = testlib.run_script("validate-result.py", [path], cwd=run.cwd)
        self.assertEqual(code, 0, out + err)


if __name__ == "__main__":
    unittest.main()
