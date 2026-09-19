"""The core's half of E11 round 2 (E11-45): S3's derived stop reason, S2's service observation.

Every test here fails against the batch-A commit `c285358` and passes after batch B. Standard
library plus jsonschema, Python 3.9, run from anywhere.
"""
import json
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()
import recheck  # noqa: E402  (imported for its side effect of a loadable CLI)
from recheck_core import verifier  # noqa: E402


class S3DerivedReason(unittest.TestCase):
    """S3: the stop reason comes from what the run observed, not from the word the model typed.

    The E10 campaign's F5 lane is the record: a session whose own report showed the outbound
    operation declined typed `missing_evidence`, and the core wrote that down. One test per row
    of the package's table, then the two end-to-end rules — the typed reason is retained, and an
    outcome the run cannot decide stays unresolved rather than falling back to a default.
    """

    RUN = "/tmp/does-not-need-to-exist"

    def derive(self, **item):
        item.setdefault("method", "executed")
        item.setdefault("evidence", [])
        return verifier.derive_reason(item, self.RUN, call_status=item.pop("call_status", "ok"))

    # --- the table, one test per row ---------------------------------------------------

    def test_a_declined_operation_is_verification_blocked(self):
        got = self.derive(evidence=[{"kind": "command",
                                     "detail": "curl http://service.internal/health -> "
                                               "operation not permitted"}])
        self.assertEqual(got["reason"], "verification_blocked")
        self.assertIn("declined", got["observed"])

    def test_an_unreachable_service_is_verification_blocked(self):
        got = self.derive(evidence=[{"kind": "command",
                                     "detail": "curl: (6) Could not resolve host: "
                                               "service.internal"}])
        self.assertEqual(got["reason"], "verification_blocked")
        self.assertIn("unreachable", got["observed"])

    def test_a_command_that_showed_the_defect_is_reproduces(self):
        got = self.derive(evidence=[{"kind": "command",
                                     "detail": "ran the scenario; the CSV cell is unquoted"}])
        self.assertEqual(got["reason"], "reproduces")

    def test_a_command_that_showed_a_narrower_case_is_missed_case(self):
        got = self.derive(missed_case="a title holding a double quote",
                          evidence=[{"kind": "command",
                                     "detail": "ran the scenario; commas quote, quotes do not"}])
        self.assertEqual(got["reason"], "missed_case")

    def test_an_absent_required_input_is_missing_evidence(self):
        got = self.derive(method="static", static_reason="non_executable_artifact",
                          missing="the fixture carries no such file or directory to read",
                          evidence=[{"kind": "read", "detail": "looked for the artifact"}])
        self.assertEqual(got["reason"], "missing_evidence")

    def test_a_call_that_did_not_complete_is_verification_blocked(self):
        got = self.derive(call_status="timed-out",
                          evidence=[{"kind": "command", "detail": "ran the scenario"}])
        self.assertEqual(got["reason"], "verification_blocked")
        self.assertIn("timed-out", got["how"])

    def test_an_unrecognised_outcome_stays_unresolved(self):
        got = self.derive(method="static", static_reason="mutates_real_state",
                          evidence=[{"kind": "read", "detail": "read the source"}])
        self.assertIsNone(got["reason"])
        self.assertEqual(got["observed"], verifier.UNRESOLVED)

    def test_a_negated_refusal_is_not_a_refusal(self):
        """The same trap `declared_block` closes: "no permission denied" is not a refusal."""
        got = self.derive(evidence=[{"kind": "command",
                                     "detail": "ran the scenario; no permission denied, the "
                                               "cell is unquoted"}])
        self.assertEqual(got["reason"], "reproduces")

    def test_the_derivation_never_reads_the_reason_the_model_typed(self):
        """Two calls differing only in the typed reason derive the same thing."""
        evidence = [{"kind": "command", "detail": "ran the scenario; the cell is unquoted"}]
        a = self.derive(reason="missing_evidence", evidence=list(evidence))
        b = self.derive(reason="reproduces", evidence=list(evidence))
        self.assertEqual(a, b)


class S3DerivedReasonEndToEnd(unittest.TestCase):
    """S3 through a real run: what the record carries after `adjudicate --action confirmed`."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("e11-r2-s3")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def drive(self, lane, case_id):
        case_dir = testlib.build_case(lane, case_id,
                                      os.path.join(self.scratch, case_id + "-fixture"))
        path = testlib.prepare_input(case_dir)
        started = self.step(["start", path])
        return os.path.join(case_dir, "run"), started

    def step(self, args):
        code, document, err = testlib.recheck(args, cwd=self.scratch)
        self.assertIn(code, (0, 10), "%s: %s" % (args[0], err[-900:]))
        return document

    @staticmethod
    def where(item):
        location = item["location"]
        return "%s:%s" % (location["file"], location["line"])

    def record(self, run_dir, call_id, text, name):
        path = testlib.write_report(run_dir, text, name)
        return self.step(["record-call", "--run-dir", run_dir, "--call-id", call_id,
                          "--status", "ok", "--raw", path, "--model", "test-verifier",
                          "--kind", "canned"])

    def confirmed_item(self, report):
        run_dir, started = self.drive("F5-blocked-execution", "F5-01-outbound-required")
        items = started["checklist"]
        self.record(run_dir, started["call_id"], report(self.where(items[0])), "supplied.md")
        self.step(["adjudicate", "--run-dir", run_dir, "--item", "0", "--action", "confirmed"])
        done = self.step(["record", "--run-dir", run_dir])
        return run_dir, done, testlib.load_json(done["result"])["items"][0]

    def test_the_models_stated_reason_is_retained_and_the_derived_one_recorded(self):
        """The F5 shape: the report's own evidence shows the call declined, it types
        `missing_evidence`, and the recorded reason is the derived `verification_blocked`."""
        def report(where):
            return testlib.canned_report([
                {"index": 0, "location": where, "disposition": "not_fixed",
                 "reason": "missing_evidence", "method": "executed",
                 "missing": "no service observation was obtained",
                 "evidence": [{"kind": "command", "artifact": None,
                               "detail": "POST /v1/emit -> operation not permitted by the "
                                         "sandbox"}]}])
        run_dir, done, item = self.confirmed_item(report)
        self.assertEqual(item["reason"], "verification_blocked")
        adjudication = item["adjudication"]
        self.assertEqual(adjudication["reason_as_stated"], "missing_evidence")
        self.assertEqual(adjudication["reason_derived"]["reason"], "verification_blocked")
        self.assertIn("operation not permitted", adjudication["reason_derived"]["how"])
        # the derived reason moved the evidence field with it, and nothing contradicts it
        self.assertTrue(item["verification"]["blocked"])
        self.assertIsNone(item["verification"].get("missing"))
        code, out, _err = testlib.run_script(
            "validate-result.py",
            [done["result"], "--input", os.path.join(run_dir, "input.json"),
             "--run-dir", run_dir], cwd=self.scratch)
        self.assertEqual(code, 0, out[-600:])

    def test_an_unresolved_outcome_keeps_the_stated_reason(self):
        """Nothing the run retained decides it: the typed reason stands, marked unresolved."""
        def report(where):
            return testlib.canned_report([
                {"index": 0, "location": where, "disposition": "not_fixed",
                 "reason": "missing_evidence", "method": "static",
                 "static_reason": "non_executable_artifact",
                 "missing": "the run holds no comparison baseline",
                 "evidence": [{"kind": "read", "artifact": None,
                               "detail": "read the handler source"}]}])
        _run_dir, _done, item = self.confirmed_item(report)
        self.assertEqual(item["reason"], "missing_evidence")
        adjudication = item["adjudication"]
        self.assertEqual(adjudication["reason_as_stated"], "missing_evidence")
        self.assertIsNone(adjudication["reason_derived"]["reason"])
        self.assertEqual(adjudication["reason_derived"]["observed"], verifier.UNRESOLVED)

    def test_both_schemas_carry_the_derived_reason(self):
        with open(os.path.join(testlib.REF, "result.schema.json"), encoding="utf-8") as fh:
            result = json.load(fh)
        with open(os.path.join(testlib.REF, "checkpoint.schema.json"), encoding="utf-8") as fh:
            checkpoint = json.load(fh)
        adjudication = result["$defs"]["adjudication"]
        self.assertIn("reason_as_stated", adjudication["properties"])
        self.assertIn("reason_derived", adjudication["properties"])
        self.assertEqual(checkpoint["$defs"]["adjudication"], adjudication)
        guard = [row for row in adjudication["allOf"]
                 if row.get("if", {}).get("required") == ["reason_as_stated"]]
        self.assertEqual(len(guard), 1)
        self.assertEqual(guard[0]["then"]["required"], ["reason_derived"])


if __name__ == "__main__":
    unittest.main()


class S2ServiceObservation(unittest.TestCase):
    """S2: `fixed` is refused on an item that requires a service observation and carries none.

    The E10 campaign's F5 lane again: the fix can only be proved by observing the named
    service, the sandbox declines the call, and a static read cleared the item anyway. The
    requirement is declared on the input and bound onto the checklist item, so the rule is a
    contract field and not a check keyed to a fixture id.
    """

    SERVICE = "https://sync.widget.example.invalid/v1/rows"

    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("e11-r2-s2")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def step(self, args):
        code, document, err = testlib.recheck(args, cwd=self.scratch)
        self.assertIn(code, (0, 10), "%s: %s" % (args[0], err[-900:]))
        return document

    def drive(self):
        case_dir = testlib.build_case("F5-blocked-execution", "F5-01-outbound-required",
                                      os.path.join(self.scratch, "s2-%d" % self.counter()))
        path = testlib.prepare_input(case_dir)
        started = self.step(["start", path])
        return case_dir, os.path.join(case_dir, "run"), started

    _n = [0]

    @classmethod
    def counter(cls):
        cls._n[0] += 1
        return cls._n[0]

    @staticmethod
    def where(item):
        location = item["location"]
        return "%s:%s" % (location["file"], location["line"])

    def cleared(self, evidence, method="static", static_reason="non_executable_artifact",
                artifact_text=None):
        """A run whose verifier reports `fixed` for item 0 with the given evidence."""
        case_dir, run_dir, started = self.drive()
        if artifact_text is not None:
            scratch = os.path.join(run_dir, "verifier")
            os.makedirs(scratch, exist_ok=True)
            with open(os.path.join(scratch, "observation.txt"), "w", encoding="utf-8") as fh:
                fh.write(artifact_text)
        row = {"index": 0, "location": self.where(started["checklist"][0]),
               "disposition": "fixed", "method": method, "evidence": evidence}
        if method == "static":
            row["static_reason"] = static_reason
        text = testlib.canned_report([row])
        path = testlib.write_report(run_dir, text, "supplied.md")
        self.step(["record-call", "--run-dir", run_dir, "--call-id", started["call_id"],
                   "--status", "ok", "--raw", path, "--model", "test-verifier",
                   "--kind", "canned"])
        self.step(["adjudicate", "--run-dir", run_dir, "--item", "0", "--action", "confirmed"])
        done = self.step(["record", "--run-dir", run_dir])
        result = testlib.load_json(done["result"])
        return case_dir, run_dir, done, result["items"][0]

    def test_a_fixed_without_the_observation_is_refused(self):
        _case, _run, _done, item = self.cleared(
            [{"kind": "read", "artifact": None,
              "detail": "read src/widget/sync.py; the double count is gone"}])
        self.assertEqual(item["disposition"], "not_fixed")
        self.assertEqual(item["reason"], "missing_evidence")
        refusal = item["adjudication"]["service_observation_refused"]
        self.assertEqual(refusal["service"], self.SERVICE)
        self.assertEqual(refusal["verifier_said"], "fixed")

    def test_a_static_read_is_not_a_service_observation(self):
        """Even a static read that NAMES the service does not clear the item."""
        _case, _run, _done, item = self.cleared(
            [{"kind": "read", "artifact": None,
              "detail": "read the client code that posts to %s" % self.SERVICE}])
        self.assertEqual(item["disposition"], "not_fixed")
        self.assertIn("service_observation_refused", item["adjudication"])

    def test_a_fixed_with_a_bound_observation_is_accepted(self):
        _case, _run, done, item = self.cleared(
            [{"kind": "command", "artifact": "observation.txt",
              "detail": "GET %s/count before and after the push" % self.SERVICE}],
            method="executed",
            artifact_text="GET %s/count -> 3\nafter the push -> 6\n" % self.SERVICE)
        self.assertEqual(item["disposition"], "fixed")
        self.assertNotIn("service_observation_refused", item["adjudication"])

    def test_the_refusal_retains_the_rejected_claim(self):
        _case, _run, _done, item = self.cleared(
            [{"kind": "read", "artifact": None, "detail": "read the source only"}])
        adjudication = item["adjudication"]
        self.assertEqual(adjudication["verifier_said"], "fixed")
        self.assertEqual(adjudication["driver_action"], "downgraded")
        self.assertIn("static", adjudication["service_observation_refused"]["why"])
        self.assertEqual(adjudication["service_observation_refused"]["method"], "static")

    def test_the_requirement_comes_from_the_item_not_the_case_id(self):
        """An item with no declaration is cleared by exactly the same static report."""
        case_dir = testlib.build_case("F1-fixed-defect", "F1-01-fixed-clean",
                                      os.path.join(self.scratch, "s2-control"))
        path = testlib.prepare_input(case_dir)
        run_dir = os.path.join(case_dir, "run")
        started = self.step(["start", path])
        text = testlib.canned_report([
            {"index": 0, "location": self.where(started["checklist"][0]),
             "disposition": "fixed", "method": "static",
             "static_reason": "non_executable_artifact",
             "evidence": [{"kind": "read", "artifact": None,
                           "detail": "read the source only"}]}])
        raw = testlib.write_report(run_dir, text, "supplied.md")
        self.step(["record-call", "--run-dir", run_dir, "--call-id", started["call_id"],
                   "--status", "ok", "--raw", raw, "--model", "test-verifier", "--kind",
                   "canned"])
        self.step(["adjudicate", "--run-dir", run_dir, "--item", "0", "--action", "confirmed"])
        done = self.step(["record", "--run-dir", run_dir])
        item = testlib.load_json(done["result"])["items"][0]
        self.assertEqual(item["disposition"], "fixed")
        self.assertNotIn("service_observation_refused", item["adjudication"])

    def test_the_validator_rejects_a_fixed_without_the_bound_observation(self):
        """A record the core would not write: a `fixed` whose observation retained nothing.

        Built from the accepted run by dropping the retained output, so the record stays
        schema-valid and only the S2 rule can reject it.
        """
        _case, run_dir, done, item = self.cleared(
            [{"kind": "command", "artifact": "observation.txt",
              "detail": "GET %s/count before and after the push" % self.SERVICE}],
            method="executed",
            artifact_text="GET %s/count -> 3\nafter the push -> 6\n" % self.SERVICE)
        self.assertEqual(item["disposition"], "fixed")
        result = testlib.load_json(done["result"])
        for entry in result["items"][0]["verification"]["evidence"]:
            entry.pop("artifact_path", None)
        path = os.path.join(self.scratch, "forged-result.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(result, fh)
        code, out, _err = testlib.run_script(
            "validate-result.py",
            [path, "--input", os.path.join(run_dir, "input.json")], cwd=self.scratch)
        document = json.loads(out)
        self.assertEqual(document["schema"], [], document["schema"])
        v11 = [f for f in document["semantic"] if f["id"] == "V11"]
        self.assertTrue(v11, document["semantic"])
        self.assertIn("requires an observation", v11[0]["message"])
        self.assertNotEqual(code, 0)

    def test_the_validator_says_so_when_it_has_no_input_to_check_against(self):
        """Without the input the rule cannot be checked; V11 reports skipped, never passes."""
        _case, _run, done, _item = self.cleared(
            [{"kind": "read", "artifact": None, "detail": "read the source only"}])
        code, out, _err = testlib.run_script("validate-result.py", [done["result"]],
                                             cwd=self.scratch)
        document = json.loads(out)
        skipped = [row for row in document["skipped"] if row["id"] == "V11"]
        self.assertTrue(skipped, document["skipped"])
        self.assertIn("service-observation", skipped[0]["reason"])
