"""Every seeded case of this core's three families, driven through `observe.py`.

**What this suite may assert, and what it may not.** The expected outcome of each case lives in
an answer key outside this repository that no one here has seen (lane contract pick P4). So this
suite asserts only what the CONTRACT guarantees for EVERY run, whatever the case holds:

- a terminal status exists, and it is one of the two neutral words;
- the source set has three lists and a base;
- the result validates against its schema and the semantic checks;
- the report-only case wrote nothing;
- a refused answer is neither acted on nor repaired;
- nothing is raised at a location outside the source set;
- no run of this station ever clears a finding.

The outcome assertions — which finding is raised, which verdict is recorded, which path is in
the packet — are the control room's, graded against the key. If a test here ever starts saying
what a case "should" produce, it has crossed that line and must come out.
"""
import json
import os
import subprocess
import unittest

import testlib

NEUTRAL = ("completion", "stop")
CLEAR_KINDS = ("disposition", "waived", "reopened")


def observe_all(out_dir):
    proc = subprocess.run(
        [testlib.GEN_PYTHON, testlib.OBSERVE, "--all", "--out", out_dir,
         "--records-root", testlib.RECORDS_ROOT],
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


class EveryCaseRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("signoff-seeded-")
        cls.out = os.path.join(cls.dir, "observed")
        code, out, err = observe_all(cls.out)
        cls.summary = json.loads(out) if out.strip() else {"cases": [], "failed": -1}
        cls.code, cls.err = code, err
        cls.observed = {}
        for row in cls.summary.get("cases", []):
            if row.get("observed"):
                cls.observed[row["case"]] = testlib.load_json(row["observed"])

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def test_observe_drove_every_case_of_every_family(self):
        self.assertEqual(self.code, 0, self.err)
        self.assertEqual(self.summary["failed"], 0, json.dumps(self.summary))
        self.assertEqual(sorted(self.observed), sorted(testlib.all_case_ids()))
        self.assertEqual(len(self.observed), 13)

    def test_every_case_reached_a_terminal_status(self):
        for case_id, observed in sorted(self.observed.items()):
            self.assertIn(observed.get("terminal_status"), NEUTRAL, case_id)

    def test_every_case_that_computed_a_scope_has_three_lists_and_a_base(self):
        for case_id, observed in sorted(self.observed.items()):
            if "base_ref" not in observed:
                continue
            self.assertEqual(observed["base_ref"], "base", case_id)
            for key in ("source_set_committed", "source_set_changed", "source_set_untracked"):
                self.assertIsInstance(observed.get(key), list, "%s: %s" % (case_id, key))
            every = (observed["source_set_committed"] + observed["source_set_changed"]
                     + observed["source_set_untracked"])
            self.assertTrue(every, "%s: the set is empty, which no case of these families is"
                            % case_id)
            self.assertEqual([p for p in every if p.startswith("docs/records/")], [], case_id)

    def test_nothing_is_raised_at_a_location_outside_the_source_set(self):
        """Section 10's rule, over every case at once: a location outside the set is a note."""
        for case_id, observed in sorted(self.observed.items()):
            if "base_ref" not in observed:
                continue
            in_set = set(observed["source_set_committed"] + observed["source_set_changed"]
                         + observed["source_set_untracked"])
            for location in observed.get("raised_locations", []):
                self.assertIn(location.rsplit(":", 1)[0], in_set,
                              "%s raised %s, which is outside its source set" % (case_id, location))

    def test_every_packet_file_list_is_the_whole_source_set(self):
        for case_id, observed in sorted(self.observed.items()):
            if "base_ref" not in observed or "_packet_files" not in observed:
                continue
            in_set = sorted(set(observed["source_set_committed"] + observed["source_set_changed"]
                                + observed["source_set_untracked"]))
            self.assertEqual(observed["_packet_files"], in_set,
                             "%s: the packet's file list is not the source set" % case_id)

    def test_a_refused_answer_is_neither_acted_on_nor_repaired(self):
        for case_id, observed in sorted(self.observed.items()):
            if not observed.get("answer_refused"):
                continue
            self.assertFalse(observed.get("verdict_recorded"), case_id)
            self.assertEqual(observed.get("raised_locations"), [], case_id)
            self.assertTrue(observed.get("writes_none"), case_id)
            self.assertIn(observed.get("refusal_reason"),
                          ("independence", "answer_invalid", "packet_incomplete"), case_id)

    def test_a_run_that_recorded_no_verdict_moved_no_card_and_wrote_nothing(self):
        for case_id, observed in sorted(self.observed.items()):
            if observed.get("verdict_recorded"):
                continue
            self.assertTrue(observed.get("writes_none"),
                            "%s recorded no verdict and still wrote" % case_id)
            self.assertEqual(observed.get("card_after"), "built",
                             "%s recorded no verdict and moved its card" % case_id)

    def test_every_raised_finding_carries_a_severity_and_an_evidence_kind(self):
        for case_id, observed in sorted(self.observed.items()):
            for location in observed.get("raised_locations", []):
                self.assertIn(observed["raised_severities"].get(location),
                              ("BLOCKER", "MAJOR", "MINOR"), "%s %s" % (case_id, location))
                self.assertIn(observed["raised_evidence_kinds"].get(location),
                              ("executed", "read", "reasoned"), "%s %s" % (case_id, location))

    def test_a_completed_run_with_no_findings_lists_the_checks_it_executed(self):
        for case_id, observed in sorted(self.observed.items()):
            if observed.get("terminal_status") != "completion":
                continue
            if observed.get("raised_locations"):
                continue
            self.assertTrue(observed.get("clean_review_checks_listed"),
                            "%s completed clean without listing a check" % case_id)
            self.assertTrue(observed.get("check_output_contains"), case_id)

    def test_no_observed_file_states_an_expected_outcome(self):
        """The guard on this whole arrangement: nothing here says what a case should produce."""
        for case_id, observed in sorted(self.observed.items()):
            text = json.dumps(observed)
            for word in ('"expected"', '"should"', '"pass"', '"fail"', '"either"', '"any_of"'):
                self.assertNotIn(word, text, "%s: %s" % (case_id, word))


class TheResultsValidate(unittest.TestCase):
    """Every case's result validates against the schema and the semantic checks, through the
    real validator, not through an in-process shortcut."""

    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("signoff-seeded-validate-")

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def test_every_case_result_passes_validate_result(self):
        for case_id in testlib.all_case_ids():
            with self.subTest(case=case_id):
                case_dir, result, supplied = self.run_case(case_id)
                code, out, err = testlib.run_script(
                    "validate-result.py", [result, "--input", supplied], cwd=self.dir)
                self.assertEqual(code, 0, "%s: %s%s" % (case_id, out, err))

    def run_case(self, case_id):
        family = testlib.family_of(case_id)
        case_dir = testlib.build_case(family, case_id, os.path.join(self.dir, case_id, family))
        seeded = testlib.load_json(os.path.join(case_dir, "input.json"))
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "seeded-case",
                              "run_id": "validate-%s" % case_id, "run_dir": seeded["run_dir"],
                              "run_date": "2026-09-21", "harness": None,
                              "sessions": seeded["sessions"]},
               "workspace": seeded["workspace"],
               "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                          "base": seeded["base"]},
               "report_only": bool(seeded.get("report_only")),
               "review": {"depth": "LEAN", "route": "recorded-answer"}}
        supplied = testlib.write_json(os.path.join(case_dir, "signoff-input.json"), doc)
        env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}
        run_dir = seeded["run_dir"]
        for args in (["check-input", supplied], ["scope", "--run-dir", run_dir],
                     ["request", "--run-dir", run_dir],
                     ["record-answer", "--run-dir", run_dir, "--answer",
                      os.path.join(case_dir, "answer.json")],
                     ["record", "--run-dir", run_dir]):
            code, body, err = testlib.signoff(args, env=env)
            if code != 0:
                break
        result = os.path.join(run_dir, "result.json")
        self.assertTrue(os.path.isfile(result), "%s wrote no result" % case_id)
        return case_dir, result, os.path.join(run_dir, "input.json")


class SignoffNeverClearsAFinding(unittest.TestCase):
    """The standing rule of this station, over every case that wrote a log at all."""

    def test_no_log_any_case_wrote_holds_a_clearing_event(self):
        base = testlib.make_scratch("signoff-seeded-clears-")
        self.addCleanup(testlib.rmtree, base)
        for case_id in testlib.all_case_ids():
            family = testlib.family_of(case_id)
            case_dir = testlib.build_case(family, case_id, os.path.join(base, case_id, family))
            seeded = testlib.load_json(os.path.join(case_dir, "input.json"))
            doc = {"protocol_version": 1,
                   "invocation": {"mode": "headless", "caller": "seeded-case",
                                  "run_id": "clears-%s" % case_id, "run_dir": seeded["run_dir"],
                                  "run_date": "2026-09-21", "harness": None,
                                  "sessions": seeded["sessions"]},
                   "workspace": seeded["workspace"],
                   "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                              "base": seeded["base"]},
                   "report_only": bool(seeded.get("report_only")),
                   "review": {"depth": "LEAN", "route": "recorded-answer"}}
            supplied = testlib.write_json(os.path.join(case_dir, "in.json"), doc)
            env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}
            run_dir = seeded["run_dir"]
            for args in (["check-input", supplied], ["scope", "--run-dir", run_dir],
                         ["request", "--run-dir", run_dir],
                         ["record-answer", "--run-dir", run_dir, "--answer",
                          os.path.join(case_dir, "answer.json")],
                         ["record", "--run-dir", run_dir]):
                code, body, err = testlib.signoff(args, env=env)
                if code != 0:
                    break
            records = os.path.join(seeded["workspace"], "docs", "records")
            if not os.path.isdir(records):
                continue
            for name in os.listdir(records):
                if not name.endswith(".jsonl"):
                    continue
                for line in testlib.read_text(os.path.join(records, name)).split("\n"):
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    self.assertNotIn(event["kind"], CLEAR_KINDS,
                                     "%s: signoff wrote a %s" % (case_id, event["kind"]))


if __name__ == "__main__":
    unittest.main()
