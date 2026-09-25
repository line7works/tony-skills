"""`render-visual` and `record-publish` (ruling E14-6, brief 3.6, required test 6).

The visual lands beside the doc as `<slug>-architecture.html`, nothing else is written, it holds
no script and no external resource, and its text carries every component and every door of the
doc. `record-publish` writes the `Artifact:` line once, accepts the same URL again, refuses a
different one with the bytes as found, and leaves the line untouched when the answer says
`publish: false` or the publish returned no URL, the output saying which.
"""
import os
import re
import unittest

import archlib
import testlib
from test_arch_record import LIVING, LIVING_REL, rerun_answer

D = archlib.D
URL = "https://example.invalid/artifact/turnstile"


class _Visual(unittest.TestCase):

    FILES = None

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-visual-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(self.staging)
        self.ws = archlib.repo_workspace(self.tmp, files=self.FILES)

    def written(self, answer=None, run_id="run-0001", name="run", **extra):
        run = archlib.ArchRun(self.tmp, self.ws, self.staging, name=name, run_id=run_id, **extra)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = run.record(answer or archlib.clean_answer(run_id=run_id))
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = run.write()
        self.assertEqual(code, 0, out + err)
        return run, doc["doc"]


class RenderVisual(_Visual):

    def test_beside_the_doc_and_nothing_else(self):
        run, path = self.written()
        before = archlib.listing(self.ws)
        code, doc, out, err = run.render()
        self.assertEqual(code, 0, out + err)
        html = os.path.join(os.path.dirname(path), "turnstile-architecture.html")
        self.assertEqual(doc["visual"], html)
        after = archlib.listing(self.ws)
        added = sorted(set(after) - set(before))
        self.assertEqual([rel for rel, _ in added], [os.path.relpath(html, self.ws)])
        text = testlib.read_text(html)
        for needle in ("turnstile.py", "reset()", "language %s Python 3.9" % D, "storage %s none in v0" % D,
                       "Sam Bench", "count turns", "the fixture calls turnstile.py"):
            self.assertIn(needle, text.replace("&#x27;", "'").replace("&amp;", "&"), needle)
        lowered = text.lower()
        for banned in ("<script", "<link", "<iframe", "<img", "src=", "href=", "@import", "url("):
            self.assertNotIn(banned, lowered)
        self.assertTrue(lowered.startswith("<title>"), text[:40])
        receipt = testlib.load_json(os.path.join(run.run_dir, "receipt.json"))
        self.assertEqual(receipt["writes"][-1]["path"], html)
        self.assertEqual(receipt["writes"][-1]["sha256_after"], archlib.sha(html))

    def test_markup_in_the_doc_is_escaped(self):
        a = archlib.clean_answer()
        a["components"][0]["name"] = "<b>turnstile.py</b>"
        run, path = self.written(a)
        code, doc, out, err = run.render()
        self.assertEqual(code, 0, out + err)
        text = testlib.read_text(doc["visual"])
        self.assertNotIn("<b>", text)
        self.assertIn("&lt;b&gt;turnstile.py&lt;/b&gt;", text)

    def test_render_before_write_is_usage(self):
        run = archlib.ArchRun(self.tmp, self.ws, self.staging)
        run.to_harvest()
        run.record(archlib.clean_answer())
        self.assertEqual(run.render()[0], 2)


class RecordPublish(_Visual):

    def test_written_once_then_the_same_url_accepted(self):
        run, path = self.written()
        run.render()
        code, doc, out, err = run.publish(URL)
        self.assertEqual(code, 0, out + err)
        self.assertEqual((doc["outcome"], doc["artifact_url"]), ("published", URL))
        lines = testlib.read_text(path).split("\n")
        self.assertEqual(lines[4], "Artifact: %s" % URL)
        self.assertEqual(sum(1 for l in lines if l.startswith("Artifact:")), 1)
        before = archlib.sha(path)
        code, doc, out, err = run.publish(URL)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(doc["outcome"], "published")
        self.assertEqual(archlib.sha(path), before, "the same URL again changes nothing")

    def test_a_different_url_is_refused_with_the_bytes_as_found(self):
        run, path = self.written()
        run.render()
        run.publish(URL)
        before = archlib.sha(path)
        code, doc, out, err = run.publish("https://example.invalid/artifact/second")
        self.assertEqual(code, 5, out + err)
        self.assertEqual(doc["refusals"][0]["rule"], "artifact-url-changed")
        self.assertEqual(archlib.sha(path), before)

    def test_publish_false_leaves_the_line_untouched(self):
        run, path = self.written(archlib.clean_answer(publish=False))
        run.render()
        before = archlib.sha(path)
        code, doc, out, err = run.publish()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(doc["outcome"], "skipped")
        self.assertIn("publish: false", doc["reason"])
        self.assertEqual(archlib.sha(path), before)
        code, doc, out, err = run.report()
        result = testlib.load_json(os.path.join(run.run_dir, "result.json"))
        self.assertEqual(result["station_result"]["publish_outcome"], "skipped")
        self.assertFalse(result["station_result"]["published"])

    def test_no_url_returned_leaves_the_line_untouched(self):
        run, path = self.written()
        run.render()
        before = archlib.sha(path)
        code, doc, out, err = run.publish()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(doc["outcome"], "rendered-not-published")
        self.assertIn("rendered and not published", doc["reason"])
        self.assertEqual(archlib.sha(path), before)

    def test_publish_before_render_is_usage(self):
        run, path = self.written()
        self.assertEqual(run.publish(URL)[0], 2)


class SameUrlAcrossRuns(_Visual):

    FILES = {LIVING_REL: LIVING.replace("Blind review: declined 2026-09-21\n",
                                        "Blind review: declined 2026-09-21\nArtifact: %s\n" % URL)}

    def test_a_rerun_republishes_to_the_recorded_url(self):
        run, path = self.written(rerun_answer(publish_url=URL))
        run.render()
        code, doc, out, err = run.publish(URL)
        self.assertEqual((code, doc["outcome"]), (0, "published"), out + err)
        self.assertEqual(len(re.findall(r"(?m)^Artifact: ", testlib.read_text(path))), 1)

    def test_a_rerun_answer_without_the_recorded_url_is_refused(self):
        run = archlib.ArchRun(self.tmp, self.ws, self.staging)
        run.to_harvest()
        code, doc, out, err = run.record(rerun_answer())
        self.assertEqual(code, 5, out + err)
        self.assertIn("republish-url", [r["rule"] for r in doc["refusals"]])


if __name__ == "__main__":
    unittest.main()
