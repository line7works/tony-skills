"""The window rule (the E15 lane contract A28 (1); contract section 3.5, THE WINDOW RULE).

ship-v2 records what the workspace holds when each station visit opens (build-v2, signoff-v2 and recheck-v2 alike)
and, at each visit's close and at every step between visits (a lap, a fix, a pause's answer, the report), holds
everything that moved since the last pin, net of the station's own listed writes and ship-v2's own sanctioned writes:
the build doc moved otherwise is stop 2, a path outside the slice's footprint is stop 4, and a path inside it that
nothing names is refused (exit 5, nothing written). One rule, coded once (`ship_core/window.py`).

Slice 2 re-check 1's R1S2-2 (its `g7_signoff_window.py` shapes: an edit outside the footprint while the signoff-v2
visit is open, and one between build-v2's result and that visit), check 1's C2-1 shapes (`a2_repin`, `a2b_during`),
every window with an outside path, a doc move and an unnamed inside path, and each station's own listed writes and
ship-v2's own `Status:` write passing (R1S2-4: a grant during an open recheck-v2 visit after the station wrote the doc).
The slice's footprint is `src/turnstile.py`, `tests/`; `README.md` and slice B's `src/spinner.py` lie outside it.
"""
import os
import unittest

import cr25lib
import slib
import testlib

OUTSIDE = (("README.md", "# Turnstile\n\nEdited outside the footprint.\n"),
           ("src/spinner.py", "def twice(count):\n    return count * 2\n"))
INSIDE = ("tests/test_extra.py", "def test_extra():\n    assert True\n")


def outside(ws):
    for rel, text in OUTSIDE:
        testlib.write_text(os.path.join(ws, rel), text)


def inside(ws):
    testlib.write_text(os.path.join(ws, INSIDE[0]), INSIDE[1])


def doc_edit(ws):
    """A hand edit of the build doc: a readable line changed, no station's write."""
    path = os.path.join(ws, slib.DOC)
    text = testlib.read_text(path)
    testlib.write_text(path, text.replace("- the bench clock is monotonic", "- the bench clock is monotonic, checked", 1))


PLANT = {"outside": outside, "inside": inside, "doc": doc_edit}
STOP = {"outside": ("outside-footprint", 4), "doc": ("spec-change", 2)}


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheWindowRule(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-window-rule-")
        self.addCleanup(testlib.rmtree, self.tmp)

    # ---- the run, step by step -----------------------------------------------------------------------------------

    def run_(self, name, majors=1):
        return cr25lib.Run(self, self.tmp, name, majors=majors)

    def build(self, run, during=None, after=None):
        def writes(visit):
            if during is not None:
                during(visit)
            cr25lib.card(run.tmp, run.ws, "build-v2", "not started", "built", "build-run")
        return run.visit("build-v2", "completed", before_result=writes, after_result=after)

    def signoff(self, run, during=None, after=None, which="findings"):
        def writes(visit):
            if during is not None:
                during(visit)
            if which == "findings":
                for index in range(run.majors):
                    run.findings.append(slib.raise_finding(
                        run.tmp, run.ws, location=slib.MAJOR_AT if index == 0 else cr25lib.SECOND_AT, card=None,
                        claim="the counter skips turn %d" % index))
                cr25lib.card(run.tmp, run.ws, "signoff-v2", "built", "signed off with conditions", "signoff-run")
            else:
                cr25lib.card(run.tmp, run.ws, "signoff-v2", "built", "signed off", "signoff-run")
        return run.visit("signoff-v2", which, before_result=writes, after_result=after)

    def fix(self, run, lap=1, paths=("src/turnstile.py",)):
        testlib.write_text(os.path.join(run.ws, "src", "turnstile.py"), "def spin(count):\n    return count + %d\n"
                           % (lap + 5))
        return run.drive(["fix", "--run-dir", run.run_dir, "--fixes", slib.fixes_file(
            run.tmp, run.run_dir, lap, [{"finding": run.findings[0], "paths": list(paths), "summary": "lap %d" % lap}],
            name="fixes-%d-%d.json" % (lap, len(os.listdir(run.tmp))))])

    def recheck(self, run, which="all_clear", during=None, after=None):
        def writes(visit):
            if during is not None:
                during(visit)
            if which == "all_clear":
                cr25lib.recheck(run.tmp, run.ws, run.findings[0], True, "signed off with conditions", "signed off",
                                "recheck-%d" % len(os.listdir(run.tmp)))
            else:
                cr25lib.recheck(run.tmp, run.ws, run.findings[0], False, "signed off with conditions",
                                "signed off with conditions", "recheck-%d" % len(os.listdir(run.tmp)))
        return run.visit("recheck-v2", which, before_result=writes, after_result=after)

    def to_fixing(self, run):
        code, out, err = self.build(run)
        self.assertEqual((code, out["next"]), (0, "visit --station signoff-v2"), (out, err))
        code, out, err = self.signoff(run)
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))

    def to_fixed(self, run):
        self.to_fixing(run)
        code, out, err = self.fix(run)
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))

    def to_lap_needed(self, run):
        self.to_fixed(run)
        code, out, err = self.recheck(run, "not_clear")
        self.assertEqual((code, out["next"]), (0, "lap"), (out, err))

    # ---- the verdicts ----------------------------------------------------------------------------------------------

    def stopped(self, run, res, kind):
        code, out, err = res
        tag, condition = STOP[kind]
        self.assertEqual((code, out.get("next"), out.get("stop_tag")), (0, "report", tag), (out, err))
        code, out, err = slib.report(run.drive, run.run_dir)
        self.assertEqual((code, out["status"], out["stop_tag"]), (10, "stopped", tag), (out, err))
        self.assertTrue(out["station_result"]["result_line"].startswith("STOPPED (condition %d: " % condition), out)
        self.assertEqual(slib.validate_trace(run.run_dir)[0], 0)
        return out

    def refused(self, run, res):
        code, out, err = res
        self.assertEqual(code, 5, (out, err))
        self.assertIn(INSIDE[0], out["reason"])
        return out

    def closing(self, run):
        return [(l["expected"], l["status"]) for l in slib.trace(run.run_dir) if l["kind"] == "visit"
                and l["status"] != "visiting"]

    # ---- R1S2-2: re-check 1's g7_signoff_window.py shapes ---------------------------------------------------------

    def test_g7_an_edit_outside_the_footprint_while_the_signoff_visit_is_open_is_stop_4(self):
        run = self.run_("g7-during")
        self.build(run)
        res = self.signoff(run, during=lambda visit: outside(run.ws))
        out = self.stopped(run, res, "outside")
        self.assertIn("README.md", out["reason"])
        self.assertIn("src/spinner.py", out["reason"])
        self.assertNotIn("ALL CLEAR", out["station_result"]["result_line"])
        self.assertEqual(self.closing(run), [("build-v2", "completed"), ("signoff-v2", "completed")],
                         "the station's own result closes its visit; no fix and no recheck follow")

    def test_g7_an_edit_between_build_v2s_result_and_the_signoff_visit_is_stop_4(self):
        run = self.run_("g7-between")
        self.build(run)
        testlib.write_text(os.path.join(run.ws, "README.md"), OUTSIDE[0][1])
        res = run.drive(["visit", "--run-dir", run.run_dir, "--station", "signoff-v2"])
        out = self.stopped(run, res, "outside")
        self.assertIn("README.md", out["reason"])
        self.assertEqual(self.closing(run), [("build-v2", "completed")], "no signoff-v2 visit opened")

    # ---- check 1's C2-1 shapes (held since fix round 1) -----------------------------------------------------------

    def test_a2_repin_edits_after_recheck_not_clear_and_before_lap_are_stop_4(self):
        run = self.run_("a2")
        self.to_lap_needed(run)
        outside(run.ws)
        self.stopped(run, run.lap(), "outside")

    def test_a2b_an_edit_outside_while_the_recheck_visit_is_open_is_stop_4(self):
        run = self.run_("a2b")
        self.to_fixed(run)
        self.stopped(run, self.recheck(run, during=lambda visit: outside(run.ws)), "outside")

    # ---- the build-v2 visit ----------------------------------------------------------------------------------------

    def test_build_visit_outside(self):
        run = self.run_("bo")
        self.stopped(run, self.build(run, during=lambda visit: outside(run.ws)), "outside")

    def test_build_visit_doc_moved_after_its_own_write(self):
        run = self.run_("bd")
        self.stopped(run, self.build(run, after=lambda visit: doc_edit(run.ws)), "doc")

    def test_build_visit_an_inside_path_its_result_does_not_list(self):
        run = self.run_("bi")
        self.refused(run, self.build(run, after=lambda visit: inside(run.ws)))

    def test_build_visit_the_builds_own_work_and_ledger_lines_pass(self):
        """build-v2's own listed writes: its source set names the build's paths inside the footprint, and its
        sanctioned ledger document carries the executor's ledger lines and the station's `Status:` line."""
        run = self.run_("bok")

        def work(visit):
            inside(run.ws)
            testlib.write_text(os.path.join(run.ws, "src", "turnstile.py"), "def spin(count):\n    return count + 9\n")
            doc_edit(run.ws)
        code, out, err = self.build(run, during=work)
        self.assertEqual((code, out["next"]), (0, "visit --station signoff-v2"), (out, err))

    # ---- between build-v2's result and the signoff-v2 visit -------------------------------------------------------

    def between_build_and_signoff(self, kind):
        run = self.run_("bs-" + kind)
        self.build(run)
        PLANT[kind](run.ws)
        return run, run.drive(["visit", "--run-dir", run.run_dir, "--station", "signoff-v2"])

    def test_between_build_and_signoff_outside(self):
        self.stopped(*self.between_build_and_signoff("outside"), kind="outside")

    def test_between_build_and_signoff_doc(self):
        self.stopped(*self.between_build_and_signoff("doc"), kind="doc")

    def test_between_build_and_signoff_inside(self):
        self.refused(*self.between_build_and_signoff("inside"))

    # ---- the signoff-v2 visit --------------------------------------------------------------------------------------

    def test_signoff_visit_doc_moved_after_its_own_write(self):
        run = self.run_("sd")
        self.build(run)
        self.stopped(run, self.signoff(run, after=lambda visit: doc_edit(run.ws)), "doc")

    def test_signoff_visit_an_inside_path(self):
        run = self.run_("si")
        self.build(run)
        self.refused(run, self.signoff(run, during=lambda visit: inside(run.ws)))

    def test_signoff_visit_a_hand_edit_before_its_own_write_is_stop_2(self):
        """The station's receipt chains from the doc it read; the doc at the visit's opening was another: an edit
        before the station's own write never becomes its baseline."""
        run = self.run_("shand")
        self.build(run)
        code, visit, err = run.drive(["visit", "--run-dir", run.run_dir, "--station", "signoff-v2"])
        self.assertEqual(code, 0, (visit, err))
        doc_edit(run.ws)
        before = slib.sha(os.path.join(run.ws, slib.DOC))
        run.findings.append(slib.raise_finding(run.tmp, run.ws, card=None))
        cr25lib.card(run.tmp, run.ws, "signoff-v2", "built", "signed off with conditions", "signoff-run")
        slib.put_result(visit, slib.station_result("signoff-v2", "findings", visit, run.ws,
                                                   doc_move=(before, slib.sha(os.path.join(run.ws, slib.DOC)))))
        self.stopped(run, run.drive(["visit", "--run-dir", run.run_dir, "--result"]), "doc")

    def test_signoff_visit_a_doc_write_its_result_does_not_list_is_stop_2(self):
        run = self.run_("snolist")
        self.build(run)

        def writes(visit):
            run.findings.append(slib.raise_finding(run.tmp, run.ws, card=None))
            cr25lib.card(run.tmp, run.ws, "signoff-v2", "built", "signed off with conditions", "signoff-run")
        self.stopped(run, slib.visit(self, run.drive, run.run_dir, "signoff-v2", "findings", run.ws,
                                     before_result=writes, evidence=False), "doc")

    def test_signoff_visit_its_own_writes_pass_the_verdict_doc_included(self):
        """signoff-v2's own listed writes: its punch-list block and card in the doc and its verdict doc under
        `docs/reviews/`, each by the hashes its receipt gives; the verdict doc edited after it is stop 4."""
        for edited in (False, True):
            run = self.run_("sv-%s" % edited)
            self.build(run)
            code, visit, err = run.drive(["visit", "--run-dir", run.run_dir, "--station", "signoff-v2"])
            self.assertEqual(code, 0, (visit, err))
            doc = os.path.join(run.ws, slib.DOC)
            verdict_rel = "docs/reviews/2026-10-05-signoff-turnstile-a.md"
            verdict = os.path.join(run.ws, verdict_rel)
            before = slib.sha(doc)
            run.findings.append(slib.raise_finding(run.tmp, run.ws, card=None))
            text = testlib.read_text(doc)
            testlib.write_text(doc, text + "\n" + "\n".join(slib.review_block(date="2026-10-05")[1:]) + "\n")
            middle = slib.sha(doc)
            cr25lib.card(run.tmp, run.ws, "signoff-v2", "built", "signed off with conditions", "signoff-run")
            testlib.write_text(verdict, "# Verdict\n\nsigned off with conditions\n")
            result = slib.station_result("signoff-v2", "findings", visit, run.ws)
            receipt = os.path.join(visit["visit_run_dir"], "receipt.json")
            testlib.write_json(receipt, {"receipt_version": 1, "steps": [
                {"kind": "block", "target": slib.DOC, "before_sha256": before, "after_sha256": middle, "state": "done"},
                {"kind": "verdict_doc", "target": verdict_rel, "before_sha256": None,
                 "after_sha256": slib.sha(verdict), "state": "done"},
                {"kind": "card", "target": slib.DOC, "before_sha256": middle, "after_sha256": slib.sha(doc),
                 "state": "done"}]})
            result["receipt"] = receipt
            result["records_written"] = [r for r in result["records_written"] if r["kind"] == "run_artifact"] + [
                {"kind": "build_doc", "path": doc}, {"kind": "verdict_doc", "path": verdict},
                {"kind": "card", "path": doc}]
            slib.put_result(visit, result)
            if edited:
                testlib.write_text(verdict, "# Verdict\n\nsigned off, said a hand\n")
            res = run.drive(["visit", "--run-dir", run.run_dir, "--result"])
            if edited:
                self.stopped(run, res, "outside")
            else:
                self.assertEqual((res[0], res[1]["next"]), (0, "fix"), res)

    # ---- between the signoff-v2 result and `fix` -------------------------------------------------------------------

    def at_fix(self, kind):
        run = self.run_("sf-" + kind)
        self.to_fixing(run)
        PLANT[kind](run.ws)
        return run, self.fix(run)

    def test_at_fix_outside(self):
        self.stopped(*self.at_fix("outside"), kind="outside")

    def test_at_fix_doc(self):
        self.stopped(*self.at_fix("doc"), kind="doc")

    def test_at_fix_inside(self):
        self.refused(*self.at_fix("inside"))

    # ---- between `fix` and the recheck-v2 visit --------------------------------------------------------------------

    def at_recheck_opening(self, kind):
        run = self.run_("fr-" + kind)
        self.to_fixed(run)
        PLANT[kind](run.ws)
        return run, run.drive(["visit", "--run-dir", run.run_dir, "--station", "recheck-v2"])

    def test_at_recheck_opening_outside(self):
        self.stopped(*self.at_recheck_opening("outside"), kind="outside")

    def test_at_recheck_opening_doc(self):
        self.stopped(*self.at_recheck_opening("doc"), kind="doc")

    def test_at_recheck_opening_inside(self):
        self.refused(*self.at_recheck_opening("inside"))

    # ---- the recheck-v2 visit --------------------------------------------------------------------------------------

    def test_recheck_visit_doc_moved_after_its_own_write(self):
        run = self.run_("rd")
        self.to_fixed(run)
        self.stopped(run, self.recheck(run, after=lambda visit: doc_edit(run.ws)), "doc")

    def test_recheck_visit_an_inside_path(self):
        run = self.run_("ri")
        self.to_fixed(run)
        self.refused(run, self.recheck(run, during=lambda visit: inside(run.ws)))

    # ---- between the recheck-v2 result and `lap`, and the lap's `fix` ---------------------------------------------

    def test_at_lap_doc(self):
        run = self.run_("ld")
        self.to_lap_needed(run)
        doc_edit(run.ws)
        self.stopped(run, run.lap(), "doc")

    def test_at_lap_an_inside_path_is_the_next_fixs_to_name(self):
        run = self.run_("li")
        self.to_lap_needed(run)
        inside(run.ws)
        code, out, err = run.lap()
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        self.refused(run, self.fix(run, lap=2))
        code, out, err = self.fix(run, lap=2, paths=("src/turnstile.py", INSIDE[0]))
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))

    # ---- a pause's answer outside an open visit --------------------------------------------------------------------

    def answered(self, run, kind, stage="built"):
        if stage == "built":
            self.build(run)
        else:
            self.to_fixing(run)
        code, asked, err = run.drive(["pause", "--run-dir", run.run_dir, "--question", slib.question_file(
            run.tmp, run.run_dir, "Which mode should the counter use?", station="signoff-v2")])
        self.assertEqual(code, 0, (asked, err))
        PLANT[kind](run.ws)
        return run.drive(["pause", "--run-dir", run.run_dir, "--answer", slib.answer_file(
            run.tmp, run.run_dir, asked["pause"], "the plain mode")])

    def test_at_a_pause_answer_outside(self):
        run = self.run_("po")
        self.stopped(run, self.answered(run, "outside"), "outside")

    def test_at_a_pause_answer_doc(self):
        run = self.run_("pd")
        self.stopped(run, self.answered(run, "doc"), "doc")

    def test_at_a_pause_answer_inside_is_refused_and_the_run_waits(self):
        run = self.run_("pi")
        self.refused(run, self.answered(run, "inside"))
        self.assertEqual(testlib.load_json(os.path.join(run.run_dir, "checkpoint.json"))["phase"], "paused")

    def test_at_a_pause_answer_while_the_lap_is_fixing_an_inside_path_waits_for_fix(self):
        run = self.run_("pf")
        code, out, err = self.answered(run, "inside", stage="fixing")
        self.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        self.refused(run, self.fix(run))

    # ---- the report --------------------------------------------------------------------------------------------------

    def at_report(self, kind):
        run = self.run_("rp-" + kind, majors=0)
        self.build(run)
        code, out, err = self.signoff(run, which="clean")
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        PLANT[kind](run.ws)
        return run, slib.report(run.drive, run.run_dir)

    def test_at_report_outside(self):
        run, (code, out, err) = self.at_report("outside")
        self.assertEqual((code, out["status"], out["stop_tag"]), (10, "stopped", "outside-footprint"), (out, err))
        self.assertTrue(out["station_result"]["result_line"].startswith("STOPPED (condition 4: "))

    def test_at_report_doc(self):
        run, (code, out, err) = self.at_report("doc")
        self.assertEqual((code, out["status"], out["stop_tag"]), (10, "stopped", "spec-change"), (out, err))

    def test_at_report_inside(self):
        run, res = self.at_report("inside")
        self.refused(run, res)

    # ---- ship-v2's own sanctioned writes ---------------------------------------------------------------------------

    def test_r1s2_4_a_grant_during_an_open_recheck_visit_after_the_station_wrote_the_doc(self):
        """Re-check 1's g4 V3: recheck-v2 writes its block into the doc, the owner's waiver lands while its visit is
        open (the card and the line move), then `visit --result`: ship-v2's own write is never a fix's move."""
        run = self.run_("v3", majors=2)
        self.to_fixing(run)
        code, out, err = self.fix(run)
        self.assertEqual(code, 0, (out, err))
        code, visit, err = run.drive(["visit", "--run-dir", run.run_dir, "--station", "recheck-v2"])
        self.assertEqual(code, 0, (visit, err))
        doc = os.path.join(run.ws, slib.DOC)
        before = slib.sha(doc)
        cr25lib.recheck(run.tmp, run.ws, run.findings[0], True, "signed off with conditions",
                        "signed off with conditions", "recheck-v3")
        testlib.write_text(doc, testlib.read_text(doc) + "\n### 2026-10-05 recheck: Slice A\n")
        station_row = {"kind": "punch_list_block", "path": slib.DOC, "appended": True, "sha256_before": before,
                       "sha256_after": slib.sha(doc)}
        run.grant("waive", run.findings[1], "Waive the second, a bench quirk")
        self.assertNotEqual(slib.sha(doc), station_row["sha256_after"], "ship-v2 moved the line")
        slib.put_result(visit, slib.station_result("recheck-v2", "all_clear", visit, run.ws, writes=[station_row]))
        code, out, err = run.drive(["visit", "--run-dir", run.run_dir, "--result"])
        self.assertEqual((code, out.get("stop_tag"), out["next"]), (0, None, "report"), (out, err))

    def test_a_grant_while_fixing_then_the_fix(self):
        """The owner waives the lap's one MAJOR at `fixing`: ship-v2 moves the card and its `Status:` line, and the
        lap's `fix` that follows is not stop 2 for the doc ship-v2 itself moved."""
        run = self.run_("gf")
        self.to_fixing(run)
        before = slib.sha(os.path.join(run.ws, slib.DOC))
        out = run.grant("waive", run.findings[0], "Waive it, a bench quirk")
        self.assertNotEqual(slib.sha(os.path.join(run.ws, slib.DOC)), before, "ship-v2 moved the line")
        code, out, err = run.drive(["fix", "--run-dir", run.run_dir, "--fixes", slib.fixes_file(
            run.tmp, run.run_dir, 1, [], name="fixes-none.json")])
        self.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))

    def test_a_grant_during_the_open_signoff_visit_after_the_station_wrote(self):
        run = self.run_("gs", majors=1)
        self.build(run)
        code, visit, err = run.drive(["visit", "--run-dir", run.run_dir, "--station", "signoff-v2"])
        self.assertEqual(code, 0, (visit, err))
        before = slib.sha(os.path.join(run.ws, slib.DOC))
        run.findings.append(slib.raise_finding(run.tmp, run.ws, card=None))
        cr25lib.card(run.tmp, run.ws, "signoff-v2", "built", "signed off with conditions", "signoff-run")
        after = slib.sha(os.path.join(run.ws, slib.DOC))
        slib.put_result(visit, slib.station_result("signoff-v2", "findings", visit, run.ws, doc_move=(before, after)))
        run.grant("waive", run.findings[0], "Waive it while the review closes")
        self.assertNotEqual(slib.sha(os.path.join(run.ws, slib.DOC)), after, "ship-v2 moved the line")
        code, out, err = run.drive(["visit", "--run-dir", run.run_dir, "--result"])
        self.assertEqual(code, 0, (out, err))
        self.assertNotIn("stop_tag", out, out)


if __name__ == "__main__":
    unittest.main()
