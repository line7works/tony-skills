"""`write` (brief 3.5, CR-10, CR-13, required test 5), through the real CLI.

A new doc is byte-identical to what the template renderers produce from the same values and
passes `templates.check`; a re-run appends `### Run N+1`, N the highest, strikes superseded lines
and deletes none; the header lines keep their order and either-or forms; every write is in the
receipt with its hashes; a document changed on disk after the harvest stops the run with the
bytes as found; report-only writes nothing outside the run directory.
"""
import os
import unittest

import archlib
import testlib
from test_arch_record import LIVING, LIVING_REL, rerun_answer

testlib.add_scripts_to_path()

from station_core import runlog, templates  # noqa: E402

D = archlib.D
M = archlib.M


class _Write(unittest.TestCase):

    FILES = None
    EXTRA = {}

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-write-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(self.staging)
        self.ws = archlib.repo_workspace(self.tmp, files=self.FILES)
        self.run = archlib.ArchRun(self.tmp, self.ws, self.staging, **self.EXTRA)
        code, doc, out, err = self.run.to_harvest()
        self.assertEqual(code, 0, out + err)
        self.i = archlib.ids()


class ANewDoc(_Write):

    def test_byte_identical_to_the_renderers_and_on_its_form(self):
        a = archlib.clean_answer()
        self.assertEqual(self.run.record(a)[0], 0)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        path = os.path.join(self.ws, "docs", "architecture", "%s-turnstile.md" % archlib.TODAY)
        self.assertEqual(doc["doc"], path)
        self.assertEqual(doc["run"], 1)
        text = testlib.read_text(path)
        passed = "%s (%s)" % (self.i["decided"], self.i["decided_text"])
        block = templates.render_run_block(
            1, archlib.TODAY, "first run",
            "system %s the interview continued; the owner said yes, a system" % D,
            "Sam Bench, 2026-10-01: count turns; reset the count",
            "module (platform:library); service (platform:server, storage:database); chosen: module; "
            "rejected: service %s the bench imports a module" % D,
            "language, storage and platform settled for the full vision",
            "none yet; passed forward untouched: %s" % passed,
            "first run")
        expected = templates.render_architecture_doc(
            "Turnstile", archlib.TODAY, "none yet", "Sam Bench", "2026-10-01", "count turns; reset the count",
            "turnstile.py (serves: count turns); reset() (serves: reset the count)",
            "the fixture calls turnstile.py; reset() zeroes the count",
            "fixture -> turnstile.py -> count",
            ["language %s Python 3.9 %s every bench script imports it" % (D, D),
             "storage %s none in v0 %s nothing is remembered" % (D, D)],
            ["a web dashboard %s door stays open because the module has no I/O" % D],
            [block], scope_doc=archlib.SCOPE_REL)
        self.assertEqual(text, expected)
        self.assertEqual(templates.check("architecture-doc", text), [])
        header = text.split("\n")[2:4]
        self.assertEqual(header, ["Scope doc: %s" % archlib.SCOPE_REL, "Blind review: none yet"])
        self.assertNotIn("Artifact:", text)

    def test_the_receipt(self):
        self.run.record(archlib.clean_answer())
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        receipt = testlib.load_json(os.path.join(self.run.run_dir, "receipt.json"))
        writes = [w for w in receipt["writes"] if w["kind"] == "document"]
        self.assertEqual(len(writes), 1)
        for w in receipt["writes"]:
            if w["kind"] == "run_artifact":
                self.assertTrue(w["path"].startswith(self.run.run_dir + os.sep), w)
        self.assertEqual(writes[0]["path"], doc["doc"])
        self.assertEqual(writes[0]["kind"], "document")
        self.assertIsNone(writes[0]["sha256_before"])
        self.assertEqual(writes[0]["sha256_after"], archlib.sha(doc["doc"]))

    def test_write_before_an_answer_is_usage(self):
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 2, out + err)

    def test_the_needs_check_lines_land_in_deferred(self):
        a = archlib.clean_answer(lines=[{"text": "whether the encoder reports half turns", "tag": "open",
                                         "trace": {"kind": "assumed", "ref": "outside the property line"}}])
        self.assertEqual(self.run.record(a)[0], 0, a)
        code, doc, out, err = self.run.write()
        text = testlib.read_text(doc["doc"])
        self.assertIn("- NEEDS CHECK: whether the encoder reports half turns\n", text)


class ADocumentChangedAfterHarvest(_Write):

    FILES = {LIVING_REL: LIVING}

    def test_the_bytes_are_left_as_found(self):
        self.assertEqual(self.run.record(rerun_answer())[0], 0)
        path = os.path.join(self.ws, LIVING_REL)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\nan edit by hand\n")
        before = archlib.sha(path)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "document-changed")
        self.assertEqual(archlib.sha(path), before)
        receipt = os.path.join(self.run.run_dir, "receipt.json")
        writes = testlib.load_json(receipt)["writes"] if os.path.exists(receipt) else []
        self.assertEqual([w for w in writes if w["kind"] == "document"], [])


class AReRun(_Write):

    FILES = {LIVING_REL: LIVING}

    def test_run_n_plus_one_with_strikes_and_no_deletion(self):
        self.assertEqual(self.run.record(rerun_answer())[0], 0)
        path = os.path.join(self.ws, LIVING_REL)
        before = testlib.read_text(path)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        self.assertEqual((doc["doc"], doc["run"]), (path, 2))
        after = testlib.read_text(path)
        self.assertEqual(runlog.runs(after)[-1][0], 2)
        self.assertEqual(runlog.losses(before, after), [])
        self.assertIn("- ~~storage %s none in v0 %s nothing is remembered~~\n" % (D, D), after)
        self.assertIn("- storage %s a JSON file %s the count survives a restart\n" % (D, D), after)
        after_lines = after.split("\n")
        for line in before.split("\n"):
            if not line.strip() or line.startswith(("Blind review:", "Scope doc:", "Artifact:")):
                continue
            self.assertTrue(line in after_lines or runlog.strike(line) in after_lines, line)
        self.assertIn("### Run 1 %s 2026-09-21 %s trigger: first run\n" % (D, D), after)
        self.assertIn("### Run 2 %s %s %s trigger: idea blossomed\n" % (D, archlib.TODAY, D), after)
        self.assertEqual(templates.check("architecture-doc", after), [])
        lines = after.split("\n")
        self.assertEqual(lines[2], "Scope doc: %s" % archlib.SCOPE_REL)
        self.assertEqual(lines[3], "Blind review: none yet")
        receipt = testlib.load_json(os.path.join(self.run.run_dir, "receipt.json"))
        docs = [w for w in receipt["writes"] if w["kind"] == "document"]
        self.assertEqual(docs[0]["sha256_before"], archlib.sha_text(before))
        self.assertEqual(docs[0]["sha256_after"], archlib.sha(path))

    def test_a_changed_walkthrough_strikes_the_old_line(self):
        a = rerun_answer()
        a["walkthrough"]["must"] = ["count turns", "reset the count", "read the count aloud"]
        a["components"].append({"name": "speak()", "serves": "read the count aloud"})
        self.assertEqual(self.run.record(a)[0], 0)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        after = testlib.read_text(doc["doc"])
        self.assertIn("~~Who: Sam Bench  %s  When: 2026-10-01  %s  Must be able to: count turns; reset the count~~\n"
                      % (M, M), after)
        self.assertIn("Who: Sam Bench  %s  When: 2026-10-01  %s  Must be able to: count turns; reset the count; "
                      "read the count aloud\n" % (M, M), after)
        self.assertIn("~~Components: turnstile.py (serves: count turns); reset() (serves: reset the count)~~\n", after)
        self.assertEqual(templates.check("architecture-doc", after), [])

    def test_the_recorded_artifact_line_is_kept(self):
        living = LIVING.replace("Blind review: declined 2026-09-21\n",
                                "Blind review: declined 2026-09-21\nArtifact: https://example.invalid/artifact/turnstile\n")
        path = os.path.join(self.ws, LIVING_REL)
        testlib.write_text(path, living)
        run = archlib.ArchRun(self.tmp, self.ws, self.staging, name="run-b", run_id="run-0002")
        self.assertEqual(run.to_harvest()[0], 0)
        a = rerun_answer(run_id="run-0002", publish_url="https://example.invalid/artifact/turnstile")
        self.assertEqual(run.record(a)[0], 0)
        code, doc, out, err = run.write()
        self.assertEqual(code, 0, out + err)
        lines = testlib.read_text(path).split("\n")
        self.assertEqual(lines[2:5], ["Scope doc: %s" % archlib.SCOPE_REL, "Blind review: none yet",
                                      "Artifact: https://example.invalid/artifact/turnstile"])


class ASymlinkedDocHome(unittest.TestCase):
    """R2 (CA1-3): every document write checks that the real path of the target's existing parent
    folder lies inside the workspace, the staging home or the run directory. `write` stops
    `write-refused`; `render-visual` and `record-publish` are usage; nothing lands outside, and
    the result lists no write it did not make where it says."""

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-write-link-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp)
        self.outside = os.path.join(self.tmp, "outside")
        os.makedirs(self.outside)
        self.run = archlib.ArchRun(self.tmp, self.ws)

    def test_write_is_refused(self):
        os.symlink(self.outside, os.path.join(self.ws, "docs", "architecture"))
        self.run.to_harvest()
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "write-refused")
        self.assertEqual(os.listdir(self.outside), [])
        self.assertEqual([w for w in doc["writes"] if w["kind"] == "document"], [])

    def test_render_and_publish_are_usage(self):
        self.run.to_harvest()
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        self.assertEqual(self.run.write()[0], 0)
        folder = os.path.join(self.ws, "docs", "architecture")
        moved = os.path.join(self.outside, "architecture")
        os.rename(folder, moved)
        os.symlink(moved, folder)
        before = archlib.listing(self.outside)
        code, doc, out, err = self.run.render()
        self.assertEqual(code, 2, out + err)
        self.assertEqual(archlib.listing(self.outside), before)
        os.remove(folder)
        os.rename(moved, folder)
        self.assertEqual(self.run.render()[0], 0)
        os.rename(folder, moved)
        os.symlink(moved, folder)
        before = archlib.listing(self.outside)
        code, doc, out, err = self.run.publish("https://example.invalid/artifact/turnstile")
        self.assertEqual(code, 2, out + err)
        self.assertEqual(archlib.listing(self.outside), before)

    def test_a_link_into_the_run_directory_is_refused_and_report_holds(self):
        """CA2-3: a workspace folder linked to a folder INSIDE the run directory is held to the
        workspace it lies under by name: `write` stops `write-refused`, never a traceback, and
        `report` prints a result that validates."""
        self.run.to_harvest()
        inner = os.path.join(self.run.run_dir, "inner")
        os.makedirs(inner)
        os.symlink(inner, os.path.join(self.ws, "docs", "architecture"))
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 10, out + err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(doc["stop_tag"], "write-refused")
        self.assertEqual(os.listdir(inner), [])
        code, doc, out, err = self.run.report()
        self.assertEqual(code, 10, out + err)
        path = os.path.join(self.run.run_dir, "result.json")
        code, out, err = testlib.run_script("validate-result.py", [path], cwd=self.run.cwd)
        self.assertEqual(code, 0, out + err)

    def test_a_link_into_the_staging_home_is_refused(self):
        """CA2-3: a workspace folder linked into the staging home would write there under a
        workspace path; it is refused the same way."""
        staging = os.path.join(self.tmp, "staging")
        os.makedirs(os.path.join(staging, "elsewhere"))
        os.symlink(os.path.join(staging, "elsewhere"), os.path.join(self.ws, "docs", "architecture"))
        run = archlib.ArchRun(self.tmp, self.ws, staging, name="run-staged")
        self.assertEqual(run.to_harvest()[0], 0)
        self.assertEqual(run.record(archlib.clean_answer())[0], 0)
        code, doc, out, err = run.write()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "write-refused")
        self.assertEqual(os.listdir(os.path.join(staging, "elsewhere")), [])

    def test_render_into_a_link_into_the_run_directory_is_usage(self):
        self.run.to_harvest()
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        self.assertEqual(self.run.write()[0], 0)
        folder = os.path.join(self.ws, "docs", "architecture")
        moved = os.path.join(self.run.run_dir, "moved")
        os.rename(folder, moved)
        os.symlink(moved, folder)
        before = archlib.listing(moved)
        code, doc, out, err = self.run.render()
        self.assertEqual(code, 2, out + err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(archlib.listing(moved), before)


class ReportOnly(_Write):

    EXTRA = {"report_only": True}

    def test_nothing_written_outside_the_run_directory(self):
        before_ws = archlib.listing(self.ws)
        before_staging = archlib.listing(self.staging)
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        steps = [self.run.write(), self.run.render(), self.run.publish("https://example.invalid/artifact/new")]
        take = os.path.join(self.tmp, "take.md")
        testlib.write_text(take, "a take\n")
        steps.append(self.run.request("gpt-astra", roster=testlib.readers_roster()))
        steps.append(self.run.save_take("gpt-astra", take))
        for code, doc, out, err in steps:
            self.assertEqual(code, 0, out + err)
        self.assertTrue(steps[4][1]["path"].startswith(self.run.run_dir + os.sep), steps[4][1])
        code, doc, out, err = self.run.report()
        self.assertIn(code, (10,), out + err)
        self.assertEqual(archlib.listing(self.ws), before_ws)
        self.assertEqual(archlib.listing(self.staging), before_staging)
        result = testlib.load_json(os.path.join(self.run.run_dir, "result.json"))
        self.assertTrue(result["wrote_nothing"])
        self.assertTrue(result["report_only"])
        for w in result["writes"]:
            self.assertTrue(w["path"].startswith(self.run.run_dir + os.sep), w)
            self.assertEqual(w["kind"], "run_artifact")
        preview = steps[0][1]["doc"]
        self.assertTrue(preview.startswith(self.run.run_dir + os.sep))
        self.assertEqual(templates.check("architecture-doc", testlib.read_text(preview)), [])


class DoclessStagingDoc(unittest.TestCase):

    def test_a_docless_doc_lands_in_staging_with_its_reason(self):
        tmp = testlib.make_scratch("arch-write-")
        self.addCleanup(testlib.rmtree, tmp)
        staging = os.path.join(tmp, "staging")
        os.makedirs(staging)
        ws = testlib.git_workspace(tmp, "ws")
        run = archlib.ArchRun(tmp, ws, staging)
        run.check_input()
        run.select("scope")
        run.select("architecture", "bench-counter")
        self.assertEqual(run.harvest()[0], 0)
        a = archlib.clean_answer(review={"outcome": "not-offered"},
                                 docless={"reason": "an experiment drawn before any precon", "home": "staging"})
        a["questions"] = [{"id": "Q0", "text": "Is there a scope doc somewhere the glob cannot see?", "touches": [],
                           "answer": "none", "about": "scope-doc"}] + [q for q in a["questions"] if q["id"] != "Q2"]
        a["poured_concrete"] = [{"text": "language %s Python 3.9 %s the bench" % (D, D), "tag": "decided",
                                 "trace": {"kind": "question", "ref": "Q3"}}]
        a["deferred"] = []
        code, doc, out, err = run.record(a)
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = run.write()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(doc["doc"], os.path.join(staging, "bench-counter-architecture.md"))
        text = testlib.read_text(doc["doc"])
        self.assertEqual(text.split("\n")[2:4], ["Docless: an experiment drawn before any precon",
                                                "Blind review: none %s docless" % D])
        self.assertIn("Rulings: not offered %s docless" % D, text)
        self.assertEqual(templates.check("architecture-doc", text), [])


class _Refused(object):
    """Slice 3b round 2 R1 and R5 (CA3B-1): a hand-planted node on the way to a write, or a folder where a file
    goes, is exit 1 before the command's first write: stdout empty, no traceback, the sentence naming the node,
    that nothing was written, and the command to run again; every listing unchanged."""

    def refused(self, call, node, command, folder=True, said=None):
        roots = [r for r in (self.run.run_dir, self.ws, self.staging) if r]
        before = [archlib.listing(r) for r in roots]
        phase = testlib.load_json(os.path.join(self.run.run_dir, "checkpoint.json"))["phase"]
        code, doc, out, err = call()
        self.assertEqual(code, 1, out + err)
        self.assertEqual(out, "")
        self.assertNotIn("Traceback", err)
        if said:
            self.assertIn(said % node, err)
        elif folder:
            self.assertIn("unreadable run directory: %s is not a folder this run can write" % node, err)
        else:
            self.assertIn("%s is a folder where this run writes a file" % node, err)
        self.assertIn("nothing was written and the run stays where it was", err)
        self.assertIn("run `%s` again" % command, err)
        self.assertEqual([archlib.listing(r) for r in roots], before)
        self.assertEqual(testlib.load_json(os.path.join(self.run.run_dir, "checkpoint.json"))["phase"], phase)


class ANodeInTheWritesWay(_Refused, _Write):

    def test_a_file_where_the_doc_folder_goes(self):
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        node = os.path.join(self.ws, "docs", "architecture")
        testlib.write_text(node, "not a folder\n")
        self.refused(self.run.write, node, "write")
        os.remove(node)
        self.assertEqual(self.run.write()[0], 0)

    def test_a_folder_where_the_snapshot_goes_before_the_first_write(self):
        """The doc no longer lands before the snapshot's traceback: the write is refused whole."""
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        node = os.path.join(self.run.run_dir, "written-doc.md")
        os.makedirs(node)
        self.refused(self.run.write, node, "write", said="unreadable run directory: %s is not a file (a folder, or a "
                     "symlink that leads to no file, stands where the run directory's written-doc.md")
        os.rmdir(node)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        self.assertTrue(os.path.isfile(node))

    def test_a_dangling_symlink_where_the_snapshot_goes_before_the_first_write(self):
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        node = os.path.join(self.run.run_dir, "written-doc.md")
        os.symlink(os.path.join(self.run.run_dir, "no-such-file"), node)
        self.refused(self.run.write, node, "write", said="unreadable run directory: %s is not a file")
        os.remove(node)
        self.assertEqual(self.run.write()[0], 0)

    @unittest.skipIf(os.geteuid() == 0, "root writes any folder")
    def test_a_run_directory_it_cannot_write(self):
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        os.chmod(self.run.run_dir, 0o555)
        self.addCleanup(os.chmod, self.run.run_dir, 0o755)
        self.refused(self.run.write, self.run.run_dir, "write")
        os.chmod(self.run.run_dir, 0o755)
        self.assertEqual(self.run.write()[0], 0)

    def test_a_folder_where_a_run_file_goes_at_each_command(self):
        """R5: record-answer, write, render-visual, record-publish and report each hold every run-directory file
        they may write (the receipt, the checkpoint, the result, their own) before their first write."""
        answer_json = os.path.join(self.run.run_dir, "answer.json")
        os.makedirs(answer_json)
        self.refused(lambda: self.run.record(archlib.clean_answer()), answer_json, "record-answer", folder=False)
        os.rmdir(answer_json)
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        receipt = os.path.join(self.run.run_dir, "receipt.json")
        with open(receipt, "rb") as fh:
            kept = fh.read()
        os.remove(receipt)
        os.makedirs(receipt)
        self.refused(self.run.write, receipt, "write", folder=False)
        os.rmdir(receipt)
        with open(receipt, "wb") as fh:
            fh.write(kept)
        self.assertEqual(self.run.write()[0], 0)
        html = os.path.join(self.ws, "docs", "architecture", "turnstile-architecture.html")
        os.makedirs(html)
        self.refused(self.run.render, html, "render-visual", folder=False)
        os.rmdir(html)
        self.assertEqual(self.run.render()[0], 0)
        publish = os.path.join(self.run.run_dir, "publish.json")
        os.makedirs(publish)
        self.refused(lambda: self.run.publish("https://example.invalid/artifact/turnstile"), publish,
                     "record-publish", folder=False)
        os.rmdir(publish)
        self.assertEqual(self.run.publish("https://example.invalid/artifact/turnstile")[0], 0)
        result = os.path.join(self.run.run_dir, "result.json")
        os.makedirs(result)
        self.refused(self.run.report, result, "report", folder=False)
        os.rmdir(result)
        self.assertEqual(self.run.report()[0], 10)


class ANodeInThePreviewsWay(_Refused, _Write):

    EXTRA = {"report_only": True}

    def test_a_file_where_the_preview_folder_goes(self):
        self.assertEqual(self.run.record(archlib.clean_answer())[0], 0)
        node = os.path.join(self.run.run_dir, "preview")
        testlib.write_text(node, "not a folder\n")
        self.refused(self.run.write, node, "write")
        os.remove(node)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        self.assertTrue(doc["doc"].startswith(node + os.sep))


class ANodeInTheHarvestsWay(_Refused, unittest.TestCase):
    """R5: harvest holds its run-directory files before its first write (the docless set-aside's included)."""

    def test_a_folder_where_the_receipt_goes(self):
        self.tmp = testlib.make_scratch("arch-write-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.staging = None
        self.ws = archlib.repo_workspace(self.tmp)
        self.run = archlib.ArchRun(self.tmp, self.ws)
        self.assertEqual(self.run.check_input()[0], 0)
        self.assertEqual(self.run.select("scope")[0], 0)
        self.assertEqual(self.run.select("architecture", "turnstile")[0], 0)
        node = os.path.join(self.run.run_dir, "receipt.json")
        os.makedirs(node)
        self.refused(self.run.harvest, node, "harvest", folder=False)
        os.rmdir(node)
        self.assertEqual(self.run.harvest()[0], 0)


if __name__ == "__main__":
    unittest.main()
