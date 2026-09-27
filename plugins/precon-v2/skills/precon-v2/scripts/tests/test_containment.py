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

    def test_through_request_the_planted_link_is_refused(self):
        """CP5-1 (R4 of 3b): `request` resolves the cold-read file itself, not only its folder, before any
        request is built: exit 5 `outside-home`, no `exit-test/`, so no reader is summoned for a run that
        `record-answer` would refuse."""
        for report_only in (True, False):
            self.plant()
            run = self.harvested(report_only=report_only)
            before = self.digests()
            self.refused(self.request(run), "outside-home")
            self.assertFalse(os.path.lexists(run.run_file("exit-test")))
            self.assertFalse(os.path.lexists(run.run_file("readers")))
            self.assertEqual(self.digests(), before)
            self.sentinel_nowhere(run)

    def test_record_answer_refuses_and_nothing_is_copied(self):
        """The link planted after `request` (a race): `record-answer` refuses as it plans."""
        for report_only in (True, False):
            self.unplant()
            run = self.through_request(report_only)
            self.plant()
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


class ColdReadCandidateSwapped(_Base):
    """CP5-2 (R5 of 3b): a cold-read candidate swapped for a link leaving every root between `select --hunt
    cold-read` and `harvest`: exit 5 `outside-home`, "nothing was written", and the run holds no
    `harvest-scope-doc.md` (the scope doc's copy is written only once every cold-read candidate is read)."""

    def test_the_swap_leaves_no_harvest_copy(self):
        cold = os.path.join(self.fx.ws, COLD_REL)
        testlib.write_text(cold, "# Precon cold read: turnstile (2026-09-19)\n")
        run = self.fx.new_run()
        run.select()
        run.select(hunt="cold-read")
        external = os.path.join(self.outside, "outside-cold-read.md")
        testlib.write_text(external, SENTINEL)
        os.remove(cold)
        os.symlink(external, cold)
        before = (self.digests(), sorted(os.listdir(run.run_dir)))
        code, out, err = run.phase("harvest")
        self.refused((code, json.loads(out) if out.strip() else None, err), "outside-home")
        self.assertFalse(os.path.lexists(run.run_file("harvest-scope-doc.md")))
        self.assertFalse(os.path.lexists(run.run_file("harvest.json")))
        self.assertEqual((self.digests(), sorted(os.listdir(run.run_dir))), before)
        self.assertEqual(testlib.load_json(run.run_file("checkpoint.json"))["phase"], "selected")
        self.sentinel_nowhere(run)

    def test_the_unswapped_candidate_is_harvested_with_the_copy(self):
        cold = os.path.join(self.fx.ws, COLD_REL)
        testlib.write_text(cold, "# Precon cold read: turnstile (2026-09-19)\n")
        run = self.fx.new_run()
        run.select()
        run.select(hunt="cold-read")
        code, doc, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertEqual(preconlib.read(run.run_file("harvest-scope-doc.md")), preconlib.read(self.doc))


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


class PropertyLineReads(_Base):
    """The outside reviewer's closing look, P-1 (ruling R1 of round 6): the three reads that opened a path
    without the containment check. The terminal replay's `result.json` and every enumerated run artifact
    resolve inside the run directory before either is opened (exit 5, `outside-run`, nothing hashed or
    recorded, the checkpoint not advanced to `done`); the answer `record-answer` reads resolves inside the
    workspace, the staging home or the run directory (exit 5, `outside-home`, `accepted` never true,
    nothing written). The reviewer's probes `terminal-result-outside-read`, `artifact-outside-read` and
    `answer-outside-read`, each with its control."""

    MARK = "OUTSIDE_ROOT_SENTINEL"

    def no_sentinel(self, code, out, err):
        self.assertNotIn(self.MARK, out)
        self.assertNotIn(self.MARK, err)

    def outside_file(self, name, text):
        path = os.path.join(self.outside, name)
        testlib.write_text(path, text)
        return path

    def reported(self, report_only=True):
        run = self.harvested(report_only=report_only)
        code, doc, err = run.record(preconlib.answer(run))
        self.assertEqual(code, 0, json.dumps(doc))
        self.assertEqual(run.write()[0], 0)
        return run

    def phase_of(self, run):
        return testlib.load_json(run.run_file("checkpoint.json"))["phase"]

    def test_terminal_result_outside_read(self):
        """A completed run's `result.json` swapped for a symlink to an outside result: every phase that
        replays it refuses, and the sentinel reason is printed nowhere."""
        for report_only in (True, False):
            run = self.reported(report_only)
            code, result, err = run.report()
            self.assertEqual(code, 10, err)
            data = dict(result, reason=self.MARK)
            external = self.outside_file("outside-result-%s.json" % report_only, json.dumps(data))
            os.remove(run.run_file("result.json"))
            os.symlink(external, run.run_file("result.json"))
            before = self.digests()
            for name in ("report", "write", "harvest", "request"):
                args = ("--row", "claude-session", "--session-model", "synthetic-model") if name == "request" else ()
                code, out, err = run.phase(name, *args)
                self.assertEqual(code, 5, "%s: %s %s" % (name, out, err))
                doc = json.loads(out)
                self.assertEqual([r["rule"] for r in doc["refusals"]], ["outside-run"], out)
                self.no_sentinel(code, out, err)
            code, out, err = run.phase("record-answer", "--answer", run.run_file("checkpoint.json"))
            self.assertEqual(code, 5, out + err)
            self.no_sentinel(code, out, err)
            code, out, err = run.phase("state")  # the board: it never opens the result
            self.no_sentinel(code, out, err)
            self.assertEqual(self.digests(), before)

    def test_checkpoint_outside_read(self):
        """CP6-1 (R6 of 3b): the run's `checkpoint.json` (then its `input.json`) swapped for a link to an outside
        copy whose `run_id` is the sentinel: `state`, `harvest`, `write` and `report` each refuse, exit 5
        `outside-run`, before the file is opened; the sentinel is printed nowhere."""
        for name in ("checkpoint.json", "input.json"):
            run = self.reported(report_only=False)
            data = dict(testlib.load_json(run.run_file(name)), run_id=self.MARK)
            external = self.outside_file("outside-%s" % name, json.dumps(data))
            os.remove(run.run_file(name))
            os.symlink(external, run.run_file(name))
            before = self.digests()
            for command in ("state", "harvest", "write", "report"):
                code, out, err = run.phase(command)
                self.assertEqual(code, 5, "%s %s: %s %s" % (name, command, out, err))
                doc = json.loads(out)
                self.assertEqual([r["rule"] for r in doc["refusals"]], ["outside-run"], out)
                self.no_sentinel(code, out, err)
            self.assertEqual(self.digests(), before)

    def test_terminal_result_inside_the_run_is_replayed(self):
        """The control: the real in-run `result.json` is printed again, exit 10."""
        run = self.reported()
        code, result, err = run.report()
        self.assertEqual(code, 10, err)
        code, again, err = run.report()
        self.assertEqual((code, again), (10, result))

    def test_artifact_outside_read(self):
        """An extra run artifact that is a symlink to an outside file: `report` refuses before the checkpoint
        advances, hashes nothing and records no result; the run is not `done`."""
        for report_only in (True, False):
            run = self.reported(report_only)
            external = self.outside_file("external-sentinel-%s.txt" % report_only, self.MARK + "\n")
            os.symlink(external, run.run_file("extra.txt"))
            nested = run.run_file(os.path.join("preview", "deeper"))
            os.makedirs(nested)
            before = self.digests()
            code, out, err = run.phase("report")
            self.assertEqual(code, 5, out + err)
            doc = json.loads(out)
            self.assertEqual([r["rule"] for r in doc["refusals"]], ["outside-run"], out)
            self.assertNotIn(testlib.sha256_file(external), out)
            self.no_sentinel(code, out, err)
            self.assertFalse(os.path.lexists(run.run_file("result.json")))
            self.assertEqual(self.phase_of(run), "written")
            self.assertEqual(self.digests(), before)
            # a link deeper in the run is refused the same way
            os.remove(run.run_file("extra.txt"))
            os.symlink(external, os.path.join(nested, "extra.txt"))
            code, out, err = run.phase("report")
            self.assertEqual(code, 5, out + err)
            self.assertNotIn(testlib.sha256_file(external), out)
            self.assertEqual(self.phase_of(run), "written")
            # the control: with the link gone the same run reports, exit 10, and is `done`
            os.remove(os.path.join(nested, "extra.txt"))
            code, result, err = run.report()
            self.assertEqual(code, 10, err)
            self.assertEqual(self.phase_of(run), "done")

    def test_an_artifact_linked_inside_the_run_is_hashed(self):
        """The control: a run artifact that is a symlink to another file of the same run is hashed as usual."""
        run = self.reported()
        os.symlink(run.run_file("answer.json"), run.run_file("extra.txt"))
        code, result, err = run.report()
        self.assertEqual(code, 10, err)
        self.assertIn(run.run_file("extra.txt"), [w["path"] for w in result["writes"]])

    def test_answer_outside_read(self):
        """The supplied answer outside the workspace, the staging home and the run directory: exit 5,
        `outside-home`, `accepted` never true, nothing written; directly and through a symlink in a root."""
        run = self.harvested()
        answer = preconlib.answer(run, lines=[preconlib.owner_line("Outside input " + self.MARK, "yes")])
        external = self.outside_file("outside-answer.json", json.dumps(answer))
        before = (self.digests(), sorted(os.listdir(run.run_dir)))
        link = os.path.join(self.fx.ws, "linked-answer.json")
        os.symlink(external, link)
        for supplied in (external, link):
            code, out, err = run.phase("record-answer", "--answer", supplied)
            self.assertEqual(code, 5, out + err)
            doc = json.loads(out)
            self.assertIsNot(doc.get("accepted"), True)
            self.assertFalse(doc["ok"])
            self.assertEqual([r["rule"] for r in doc["refusals"]], ["outside-home"], out)
            self.no_sentinel(code, out, err)
            self.assertFalse(os.path.exists(run.run_file("answer.json")))
            self.assertEqual(self.phase_of(run), "harvested")
        os.remove(link)
        self.assertEqual((self.digests(), sorted(os.listdir(run.run_dir))), before)

    def test_an_answer_named_as_the_run_result_is_refused(self):
        """R7 of 3b (the control room's wording, C5): the answer file is written under `<run>/executor/`; one
        that resolves to the run's own `result.json` (the file `finish` writes and reads) is refused, exit 5
        `outside-home`, `accepted` never true, nothing written; directly and through a link in `executor/`."""
        run = self.harvested()
        result = run.run_file("result.json")
        testlib.write_json(result, preconlib.answer(run))
        link = run.run_file(os.path.join(preconlib.EXECUTOR_DIR, "answer-link.json"))
        os.symlink(result, link)
        before = (self.digests(), sorted(os.listdir(run.run_dir)))
        for supplied in (result, link):
            code, out, err = run.phase("record-answer", "--answer", supplied)
            self.assertEqual(code, 5, out + err)
            doc = json.loads(out)
            self.assertIsNot(doc.get("accepted"), True)
            self.assertEqual([r["rule"] for r in doc["refusals"]], ["outside-home"], out)
            self.assertFalse(os.path.exists(run.run_file("answer.json")))
            self.assertEqual(self.phase_of(run), "harvested")
        self.assertEqual((self.digests(), sorted(os.listdir(run.run_dir))), before)
        # the control: the same answer under `<run>/executor/` is accepted
        os.remove(link)
        os.remove(result)
        code, doc, err = run.record(preconlib.answer(run))
        self.assertEqual(code, 0, json.dumps(doc))

    def test_an_outside_file_that_is_not_json_is_refused_before_it_is_read(self):
        run = self.harvested()
        external = self.outside_file("outside-not-json.txt", "not json " + self.MARK)
        code, out, err = run.phase("record-answer", "--answer", external)
        self.assertEqual(code, 5, out + err)
        self.no_sentinel(code, out, err)

    def test_an_answer_in_each_root_is_accepted(self):
        """The control: an answer in the workspace, the staging home or the run directory is read."""
        for where in ("workspace", "staging", "run"):
            run = self.harvested()
            folder = {"workspace": self.fx.ws, "staging": self.fx.staging, "run": run.run_dir}[where]
            path = os.path.join(folder, "answer-in-%s.json" % run.run_id)
            testlib.write_json(path, preconlib.answer(run))
            code, out, err = run.phase("record-answer", "--answer", path)
            self.assertEqual(code, 0, "%s: %s %s" % (where, out, err))
            self.assertTrue(json.loads(out)["accepted"])
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
