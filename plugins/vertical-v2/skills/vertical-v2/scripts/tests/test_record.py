"""vertical-v2's record-local and record-outside (contract sections 3.5 and 3.7; readings CR-5, CR-7
and CR-9).

Each call's status, model, profile, parity and isolation are read from readers' own sidecar, never
typed. A local lens that did not come back `ok` leaves the local review incomplete (a stop), once its
one re-send is spent or its refusal is deterministic; a floor refusal stops the run. The executor
verifies every finding against the source and stamps it; the script refuses (exit 5) a CONFIRMED or
PLAUSIBLE finding whose file:line does not exist in the reviewed copy, a refutation with no reason, a
re-grade with no reason, a finding credited to a call that is not this phase's or did not come back ok,
and a lens with no finding that does not say what it tried. Every summons is a trace line.
"""
import json
import os
import unittest

import testlib
import vlib


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "recording runs after the requests (records, readers' roster, jsonschema)")
class _Record(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vrec-")
        self.addCleanup(testlib.rmtree, self.tmp)


class RecordLocal(_Record):

    def test_a_clean_local_review_with_what_each_lens_tried_is_recorded(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir)
        code, out, err = vlib.record_local(drive, self.tmp, run_dir)
        self.assertEqual(code, 0, (out, err))
        local = vlib.load(run_dir, "local.json")
        self.assertEqual([c["status"] for c in local["calls"]], ["ok", "ok", "ok"])
        self.assertEqual(out["next"], "request --outside")
        lines = [json.loads(l) for l in open(os.path.join(run_dir, "trace.jsonl"))]
        self.assertEqual([(l["kind"], l["status"], l["expected"]) for l in lines], [("summons", "ok", "readers")] * 3)
        self.assertEqual(sorted(l["call_id"] for l in lines), sorted(vlib.local_ids(run_dir)))

    def test_a_missing_sidecar_is_refused(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        code, out, err = vlib.record_local(drive, self.tmp, run_dir)
        self.assertEqual(code, 5, (out, err))
        self.assertIn("sidecar", out["reason"])

    def test_a_confirmed_finding_at_a_location_that_does_not_exist_is_refused(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir)
        ids = vlib.local_ids(run_dir)
        for location in ("src/nowhere.py:3", "src/turnstile.py:400"):
            code, out, err = vlib.record_local(drive, self.tmp, run_dir,
                                               findings=[vlib.finding(location, found_by=[ids[0]])])
            self.assertEqual(code, 5, (location, out, err))
            self.assertIn(location, out["reason"])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "local.json")))

    def test_a_refutation_with_no_reason_and_a_regrade_with_no_reason_are_refused(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir)
        ids = vlib.local_ids(run_dir)
        code, out, err = vlib.record_local(drive, self.tmp, run_dir, findings=[
            vlib.finding("src/nowhere.py:3", stamp="REFUTED", found_by=[ids[0]])])
        self.assertEqual(code, 5, (out, err))
        code, out, err = vlib.record_local(drive, self.tmp, run_dir, findings=[
            vlib.finding("src/turnstile.py:2", found_by=[ids[0]], reported_severity="BLOCKER")])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("re-grade", out["reason"])
        code, out, err = vlib.record_local(drive, self.tmp, run_dir, findings=[
            vlib.finding("src/turnstile.py:2", found_by=[ids[0]], reported_severity="BLOCKER",
                         regrade_reason="no data-loss path"),
            vlib.finding("src/nowhere.py:3", stamp="REFUTED", found_by=[ids[1]], refuted_because="no such file")])
        self.assertEqual(code, 0, (out, err))

    def test_a_lens_with_no_finding_and_nothing_tried_is_refused(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir)
        code, out, err = vlib.record_local(drive, self.tmp, run_dir, tried=[])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("tried", out["reason"])

    def test_a_finding_credited_to_a_call_of_another_phase_is_refused(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir)
        code, out, err = vlib.record_local(drive, self.tmp, run_dir, findings=[
            vlib.finding("src/turnstile.py:2", found_by=["run-0001-gpt-astra"])])
        self.assertEqual(code, 5, (out, err))

    def test_a_lens_that_failed_after_its_resend_stops_the_run_incomplete(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir)
        seams = [c for c in vlib.load(run_dir, "requests-local.json")["calls"] if c["lens"] == "seams"][0]
        vlib.sidecar(run_dir, seams["call_id"], seams["row"], status="transport-failed", reason="the tool failed")
        code, out, err = vlib.record_local(drive, self.tmp, run_dir)
        self.assertEqual(code, 5, (out, err))
        self.assertIn("--resend", out["reason"])
        self.assertEqual(drive(["request", "--run-dir", run_dir, "--resend", "seams", "--status", "transport-failed"])[0], 0)
        vlib.sidecar(run_dir, seams["call_id"] + "-2", seams["row"], status="empty", reason="no content")
        code, out, err = vlib.record_local(drive, self.tmp, run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "local-incomplete")
        lines = [json.loads(l) for l in open(os.path.join(run_dir, "trace.jsonl"))]
        self.assertEqual(len(lines), 4)
        self.assertEqual(vlib.outside_files(run_dir), [])

    def test_a_floor_refusal_stops_the_run(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir)
        spec = [c for c in vlib.load(run_dir, "requests-local.json")["calls"] if c["lens"] == "spec"][0]
        vlib.sidecar(run_dir, spec["call_id"], spec["row"], status="floor-refused", reason="session model below the floor")
        code, out, err = vlib.record_local(drive, self.tmp, run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "floor-refused")


class RecordOutside(_Record):

    def outside(self, rows=("gpt-astra", "deepseek"), findings=(), statuses=None):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=rows)
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 0, (out, err))
        vlib.file_outside_sidecars(run_dir, statuses=statuses)
        answer = vlib.write(self.tmp, "outside-answer.json", vlib.outside_answer(run_dir, findings=findings))
        return drive, run_dir, drive(["record-outside", "--run-dir", run_dir, "--answer", answer])

    def test_authorized_lands_on_exactly_the_named_outside_rows(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra", "deepseek"))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 0, (out, err))
        built = [testlib.load_json(c["request_file"]) for c in vlib.load(run_dir, "requests-outside.json")["calls"]]
        self.assertEqual(sorted(r["row"] for r in built), ["deepseek", "gpt-astra"])
        self.assertTrue(all(r.get("authorized") is True for r in built))
        by_row = dict((r["row"], r) for r in built)
        self.assertEqual(by_row["gpt-astra"]["profile"], "repo")
        self.assertEqual(by_row["gpt-astra"]["workspace"], os.path.join(run_dir, "summons", "run-0001-gpt-astra", "workspace"))
        self.assertEqual(by_row["deepseek"]["profile"], "packet-only")
        self.assertEqual(by_row["deepseek"]["output_budget"], 32768)
        self.assertTrue(by_row["deepseek"]["documents"])
        for path in os.listdir(os.path.join(run_dir, "requests")):
            req = testlib.load_json(os.path.join(run_dir, "requests", path))
            if req["row"].startswith("claude"):
                self.assertNotIn("authorized", req)

    def test_a_row_the_answer_did_not_name_is_refused(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra",))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside", "--row", "gemini"])
        self.assertEqual(code, 5, (out, err))
        self.assertEqual(vlib.outside_files(run_dir), [])

    def test_a_claude_row_the_answer_named_is_refused(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("claude-opus",))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("Claude row", out["reason"])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-outside.json")))

    def test_a_verified_outside_finding_is_recorded_with_its_stamp(self):
        drive, run_dir, (code, out, err) = self.outside(findings=[
            vlib.finding("src/turnstile.py:4", found_by=["run-0001-gpt-astra"], claim="reset returns zero")])
        self.assertEqual(code, 0, (out, err))
        outside = vlib.load(run_dir, "outside.json")
        self.assertEqual([f["stamp"] for f in outside["findings"]], ["CONFIRMED"])
        self.assertEqual(out["next"], "verdict")

    def test_a_hallucinated_location_stamped_confirmed_is_refused(self):
        drive, run_dir, (code, out, err) = self.outside(findings=[
            vlib.finding("src/ghost.py:12", found_by=["run-0001-gpt-astra"])])
        self.assertEqual(code, 5, (out, err))

    def test_a_packet_only_citation_maps_back_to_its_path(self):
        drive, run_dir, (code, out, err) = self.outside(findings=[
            vlib.finding("src__spinner.py:4", found_by=["run-0001-deepseek"], claim="twice is untested")])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(vlib.load(run_dir, "outside.json")["findings"][0]["location"], "src/spinner.py:4")

    def test_a_dropped_reviewer_is_recorded_and_its_findings_never_count(self):
        drive, run_dir, (code, out, err) = self.outside(statuses={"deepseek": "transport-failed"}, findings=[
            vlib.finding("src/turnstile.py:4", found_by=["run-0001-deepseek"])])
        self.assertEqual(code, 5, (out, err))
        answer = vlib.write(self.tmp, "outside-answer-2.json", vlib.outside_answer(run_dir))
        code, out, err = drive(["record-outside", "--run-dir", run_dir, "--answer", answer])
        self.assertEqual(code, 0, (out, err))
        calls = dict((c["row"], c) for c in vlib.load(run_dir, "outside.json")["calls"])
        self.assertEqual((calls["deepseek"]["status"], calls["deepseek"]["reason"]), ("transport-failed", "the tool timed out"))


if __name__ == "__main__":
    unittest.main()
