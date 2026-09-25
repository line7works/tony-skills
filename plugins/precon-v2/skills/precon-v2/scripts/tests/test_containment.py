"""Every path precon-v2 opens or writes resolves where it belongs (precon-v2-contract.md sections 7
and 9; the outside reviewer's P-1 and P-2, rulings R1 and R2 of round 5).

R1: the cold-read doc's own path is resolved immediately before it is read, not only its folder at
`request`: a cold-read file that is a symlink leaving the scope doc's home is refused (exit 5,
`outside-home`), and nothing of it reaches the run directory, a preview, or the workspace. The same
for a reader's sidecar that resolves outside the run directory.

R2: every run artifact (`preview/`, `exit-test/` and its index, the receipt, and the rest) is
resolved and checked to lie inside the run directory before it is written, under report-only and
otherwise: a symlinked artifact folder, or one symlinked artifact among several, is refused (exit 5,
`outside-run`) before the first artifact is written, and the workspace and staging home are
unchanged, so report-only's "nothing was written outside the run directory" holds.
"""
import json
import os
import unittest

import preconlib
import testlib

COLD_REL = "docs/reviews/2026-09-20-precon-cold-read-turnstile.md"
SENTINEL = "EXTERNAL SENTINEL: never a project document.\n"


class _Base(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("contain-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.fx = preconlib.Fixture(self.tmp)
        self.doc = preconlib.ensure_scope_doc(self.fx)
        self.outside = os.path.join(self.tmp, "outside-every-root")
        os.makedirs(self.outside)

    def harvested(self, report_only=False):
        run = self.fx.new_run(report_only=report_only)
        run.select()
        code, doc, err = run.harvest()
        self.assertEqual(code, 0, err)
        return run

    def request(self, run, row="claude-session"):
        code, out, err = run.phase("request", "--row", row, "--session-model", "synthetic-model")
        return code, (json.loads(out) if out.strip() else None), err

    def sidecar(self, run, call_id, run_dir=None, raw="Exact reader raw text\n"):
        path = os.path.join(run_dir or run.run_dir, "readers", call_id, "sidecar.json")
        testlib.write_json(path, {"call_id": call_id, "run_id": run.run_id, "row": "claude-session", "status": "ok",
                                  "effective_model": "synthetic-model", "reason": None, "raw_text": raw})
        return path

    def digests(self):
        return (testlib.tree_digest(self.fx.ws), testlib.tree_digest(self.fx.staging))

    def refused(self, result, rule):
        code, doc, err = result
        self.assertEqual(code, 5, "%s %s" % (json.dumps(doc, ensure_ascii=False), err))
        self.assertIn(rule, [r["rule"] for r in doc["refusals"]], json.dumps(doc, ensure_ascii=False))
        self.assertFalse(doc["ok"])

    def sentinel_nowhere(self, run):
        for root in (run.run_dir, self.fx.ws, self.fx.staging):
            for base, dirs, files in os.walk(root):
                for name in files:
                    path = os.path.join(base, name)
                    if os.path.islink(path):
                        continue
                    with open(path, "rb") as fh:
                        self.assertNotIn(SENTINEL.strip().encode("utf-8"), fh.read(), path)


class ColdReadFileLeavingItsHome(_Base):
    """R1, the reviewer's `edge_probes.py` shape: the cold-read doc's folder is inside the workspace, the
    file itself a symlink to a file outside every root."""

    def plant(self):
        """The cold-read doc's path becomes a symlink to a file outside every root."""
        external = os.path.join(self.outside, "outside-all-roots.txt")
        if not os.path.isfile(external):
            testlib.write_text(external, SENTINEL)
        cold = os.path.join(self.fx.ws, COLD_REL)
        if os.path.lexists(cold):
            os.remove(cold)
        if not os.path.isdir(os.path.dirname(cold)):
            os.makedirs(os.path.dirname(cold))
        os.symlink(external, cold)

    def unplant(self):
        cold = os.path.join(self.fx.ws, COLD_REL)
        if os.path.lexists(cold):
            os.remove(cold)

    def through_request(self, report_only):
        run = self.harvested(report_only=report_only)
        code, doc, err = self.request(run)
        self.assertEqual(code, 0, err)
        self.sidecar(run, doc["requests"][0]["call_id"])
        return run

    def test_record_answer_refuses_and_nothing_is_copied(self):
        for report_only in (True, False):
            self.plant()
            run = self.through_request(report_only)
            before = self.digests()
            result = run.record(preconlib.answer(run, exit_test={"rows": ["claude-session"]}))
            self.refused(result, "outside-home")
            self.assertFalse(os.path.exists(run.run_file("answer.json")))
            self.assertFalse(os.path.exists(run.run_file("preview")))
            self.assertEqual(self.digests(), before)
            self.sentinel_nowhere(run)

    def test_a_symlink_planted_after_record_answer_is_refused_at_write(self):
        for report_only in (True, False):
            self.unplant()
            run = self.through_request(report_only)
            code, doc, err = run.record(preconlib.answer(run, exit_test={"rows": ["claude-session"]}))
            self.assertEqual(code, 0, json.dumps(doc))
            self.plant()
            before = self.digests()
            self.refused(run.write(), "outside-home")
            self.assertEqual(self.digests(), before)
            self.assertFalse(os.path.exists(run.run_file("receipt.json")))
            self.assertFalse(os.path.exists(run.run_file("preview")))
            self.sentinel_nowhere(run)

    def test_a_cold_read_file_inside_its_home_still_continues(self):
        """The control: an ordinary cold-read doc of the same name gains the new section."""
        cold = os.path.join(self.fx.ws, COLD_REL)
        testlib.write_text(cold, "# Precon cold read: turnstile (2026-09-19)\n")
        run = self.through_request(False)
        code, doc, err = run.record(preconlib.answer(run, exit_test={"rows": ["claude-session"]}))
        self.assertEqual(code, 0, json.dumps(doc))
        self.assertEqual(run.write()[0], 0)
        text = preconlib.read(cold)
        self.assertTrue(text.startswith("# Precon cold read: turnstile (2026-09-19)\n"))
        self.assertIn("Exact reader raw text\n", text)


class SidecarLeavingTheRun(_Base):
    """R1's neighbour: readers' sidecar for a call is read only from inside the run directory."""

    def test_a_symlinked_call_folder_is_refused(self):
        run = self.harvested()
        code, doc, err = self.request(run)
        self.assertEqual(code, 0, err)
        call_id = doc["requests"][0]["call_id"]
        elsewhere = os.path.join(self.outside, "elsewhere-run")
        self.sidecar(run, call_id, run_dir=elsewhere, raw=SENTINEL)
        os.makedirs(os.path.join(run.run_dir, "readers"))
        os.symlink(os.path.join(elsewhere, "readers", call_id), os.path.join(run.run_dir, "readers", call_id))
        before = self.digests()
        code, out, err = run.record(preconlib.answer(run, exit_test={"rows": ["claude-session"]}))
        self.assertEqual(code, 5, "%s %s" % (json.dumps(out), err))
        self.assertTrue(any("outside the run directory" in r["message"] for r in out["refusals"]), json.dumps(out))
        self.assertEqual(self.digests(), before)
        self.sentinel_nowhere(run)


class ArtifactFolderLeavingTheRun(_Base):
    """R2, the reviewer's `report_only_escape.py` shapes, and one symlinked artifact among several."""

    def link_into_workspace(self, run, role):
        target = os.path.join(self.fx.ws, "escaped-" + role)
        os.makedirs(target)
        os.symlink(target, os.path.join(run.run_dir, role), target_is_directory=True)
        return target

    def test_a_symlinked_preview_folder_is_refused_under_report_only(self):
        run = self.harvested(report_only=True)
        target = self.link_into_workspace(run, "preview")
        code, doc, err = run.record(preconlib.answer(run, lines=[preconlib.owner_line("A new output format",
                                                                                     "json please")]))
        self.assertEqual(code, 0, json.dumps(doc))
        before = self.digests()
        self.refused(run.write(), "outside-run")
        self.assertEqual(self.digests(), before)
        self.assertEqual(os.listdir(target), [])
        self.assertFalse(os.path.exists(run.run_file("receipt.json")))

    def test_a_symlinked_exit_test_folder_is_refused(self):
        for report_only in (True, False):
            run = self.harvested(report_only=report_only)
            target = self.link_into_workspace(run, "exit-test")
            before = self.digests()
            self.refused(self.request(run), "outside-run")
            self.assertEqual(self.digests(), before)
            self.assertEqual(os.listdir(target), [])
            os.remove(os.path.join(run.run_dir, "exit-test"))
            os.rmdir(target)

    def test_a_symlinked_readers_folder_is_refused_at_request(self):
        run = self.harvested()
        target = self.link_into_workspace(run, "readers")
        before = self.digests()
        self.refused(self.request(run), "outside-run")
        self.assertEqual(self.digests(), before)
        self.assertFalse(os.path.exists(run.run_file(os.path.join("exit-test", "requests.json"))))
        self.assertEqual(os.listdir(target), [])

    def test_every_preview_is_checked_before_the_first_is_written(self):
        """The second preview's file is a symlink leaving the run: the first preview is not written."""
        run = self.harvested(report_only=True)
        code, doc, err = self.request(run)
        self.assertEqual(code, 0, err)
        self.sidecar(run, doc["requests"][0]["call_id"])
        code, doc, err = run.record(preconlib.answer(run, exit_test={"rows": ["claude-session"]}))
        self.assertEqual(code, 0, json.dumps(doc))
        os.makedirs(run.run_file("preview"))
        escaped = os.path.join(self.fx.ws, "escaped-second-preview.md")
        os.symlink(escaped, run.run_file(os.path.join("preview", "2-" + os.path.basename(COLD_REL))))
        before = self.digests()
        self.refused(run.write(), "outside-run")
        self.assertEqual(self.digests(), before)
        self.assertEqual(os.listdir(run.run_file("preview")), ["2-" + os.path.basename(COLD_REL)])
        self.assertFalse(os.path.lexists(escaped))

    def test_every_request_is_checked_before_the_first_is_written(self):
        run = self.fx.new_run(owner_word={"rows": ["gpt-astra"], "words": "and gpt-astra"})
        run.select()
        self.assertEqual(run.harvest()[0], 0)
        os.makedirs(run.run_file("exit-test"))
        escaped = os.path.join(self.fx.ws, "escaped-request.json")
        os.symlink(escaped, run.run_file(os.path.join("exit-test", "%s-gpt-astra.json" % run.run_id)))
        before = self.digests()
        code, out, err = run.phase("request", "--row", "claude-session", "--row", "gpt-astra",
                                   "--session-model", "synthetic-model")
        self.refused((code, json.loads(out) if out.strip() else None, err), "outside-run")
        self.assertEqual(self.digests(), before)
        self.assertEqual(os.listdir(run.run_file("exit-test")), ["%s-gpt-astra.json" % run.run_id])

    def test_a_symlinked_receipt_is_refused_before_any_document_is_written(self):
        run = self.harvested()
        code, doc, err = run.record(preconlib.answer(run, lines=[preconlib.owner_line("A new output format",
                                                                                     "json please")]))
        self.assertEqual(code, 0, json.dumps(doc))
        os.symlink(os.path.join(self.fx.ws, "escaped-receipt.json"), run.run_file("receipt.json"))
        before = self.digests()
        self.refused(run.write(), "outside-run")
        self.assertEqual(self.digests(), before)

    def test_the_ordinary_report_only_run_is_unchanged(self):
        """The control: report-only through every phase writes run artifacts only."""
        before = self.digests()
        run = self.harvested(report_only=True)
        code, doc, err = run.record(preconlib.answer(run, lines=[preconlib.owner_line("A new output format",
                                                                                     "json please")]))
        self.assertEqual(code, 0, json.dumps(doc))
        code, doc, err = run.write()
        self.assertEqual(code, 0, err)
        self.assertTrue(doc["planned"][0]["preview"].startswith(run.run_dir + os.sep))
        code, result, err = run.report()
        self.assertEqual(code, 10, err)
        self.assertTrue(result["wrote_nothing"])
        self.assertEqual(self.digests(), before)


if __name__ == "__main__":
    unittest.main()
