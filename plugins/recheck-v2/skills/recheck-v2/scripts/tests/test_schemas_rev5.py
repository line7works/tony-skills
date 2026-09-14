"""Schema accept/reject cases for every revision-5 change (E8 lane contract section 4).

Expectations come from the lane contract rulings named on each test and pilot contract
sections 2, 8, 13, and 14; no answer key is read.
"""
import copy
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import validate  # noqa: E402

SHA0 = "0" * 64
HARNESS = {"name": "claude-code", "version": "2.1.268", "entry": "plugin", "sandbox": "default"}
MODEL = {"id": "claude-fable-5-1", "floor_class": "opus", "floor_met": True}


class InputSchemaRevision5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = validate.load_schemas()
        cls.direct = testlib.load_json(testlib.EX + "/input-direct.json")
        cls.caller = testlib.load_json(testlib.EX + "/input-caller.json")

    def errors(self, doc):
        return validate.validate_input(doc, self.schemas)

    def mutated(self, base, fn):
        d = copy.deepcopy(base)
        fn(d)
        return d

    def test_examples_validate(self):
        self.assertEqual(self.errors(self.direct), [])
        self.assertEqual(self.errors(self.caller), [])

    # E8-18: harness is an object {name, version, entry, sandbox}, optional as a whole
    def test_harness_object_accepted_and_string_rejected(self):
        self.assertEqual(self.errors(self.mutated(self.direct, lambda d: d["invocation"].__setitem__("harness", dict(HARNESS)))), [])
        errs = self.errors(self.mutated(self.direct, lambda d: d["invocation"].__setitem__("harness", "claude-code 2.1.268")))
        self.assertTrue(errs and errs[0]["path"] == "/invocation/harness", errs)

    def test_harness_requires_every_field_and_no_extra(self):
        for field in ("name", "version", "entry", "sandbox"):
            errs = self.errors(self.mutated(self.direct, lambda d, f=field: d["invocation"]["harness"].pop(f)))
            self.assertTrue(errs, "harness without %s accepted" % field)
            errs = self.errors(self.mutated(self.direct, lambda d, f=field: d["invocation"]["harness"].__setitem__(f, "")))
            self.assertTrue(errs, "harness with empty %s accepted" % field)
        self.assertTrue(self.errors(self.mutated(self.direct, lambda d: d["invocation"]["harness"].__setitem__("os", "darwin"))))

    def test_harness_and_model_optional(self):
        d = self.mutated(self.direct, lambda d: (d["invocation"].pop("harness"), d["invocation"].pop("model")))
        self.assertEqual(self.errors(d), [], "a fixture input omits both (E8-18)")

    # E8-18: model is an object; id, floor_class, floor_met required; floor_met boolean or null
    def test_model_floor_met_values(self):
        for value in (True, False, None):
            d = self.mutated(self.direct, lambda d, v=value: d["invocation"]["model"].__setitem__("floor_met", v))
            self.assertEqual(self.errors(d), [], "floor_met %r rejected" % (value,))
        for bad in ("yes", 1, "null"):
            d = self.mutated(self.direct, lambda d, v=bad: d["invocation"]["model"].__setitem__("floor_met", v))
            self.assertTrue(self.errors(d), "floor_met %r accepted" % (bad,))

    def test_model_without_floor_met_rejected(self):
        errs = self.errors(self.mutated(self.direct, lambda d: d["invocation"]["model"].pop("floor_met")))
        self.assertTrue(errs and "floor_met" in errs[0]["message"], errs)

    def test_model_string_rejected(self):
        self.assertTrue(self.errors(self.mutated(self.direct, lambda d: d["invocation"].__setitem__("model", "claude-fable-5-1"))))

    def test_model_optional_fields_and_settings(self):
        full = dict(MODEL, effort="low", provider_route="anthropic", context_tokens=200000,
                    settings={"temperature": 0, "thinking": True, "tool_schema": "2026-06"})
        self.assertEqual(self.errors(self.mutated(self.direct, lambda d: d["invocation"].__setitem__("model", full))), [])
        self.assertTrue(self.errors(self.mutated(self.direct, lambda d: d["invocation"]["model"].__setitem__("context_tokens", "200k"))))
        self.assertTrue(self.errors(self.mutated(self.direct, lambda d: d["invocation"]["model"].__setitem__("settings", {"tools": {"web": False}}))))
        self.assertTrue(self.errors(self.mutated(self.direct, lambda d: d["invocation"]["model"].__setitem__("temperature", 0))), "unknown model key accepted")

    # E8-13: session_wrote_fix boolean, default false
    def test_session_wrote_fix(self):
        self.assertEqual(self.schemas.docs["input"]["properties"]["invocation"]["properties"]["session_wrote_fix"]["default"], False)
        self.assertEqual(self.errors(self.mutated(self.direct, lambda d: d["invocation"].__setitem__("session_wrote_fix", True))), [])
        self.assertTrue(self.errors(self.mutated(self.direct, lambda d: d["invocation"].__setitem__("session_wrote_fix", "no"))))

    # E8-25: run_date YYYY-MM-DD
    def test_run_date(self):
        self.assertEqual(self.errors(self.mutated(self.direct, lambda d: d["invocation"].__setitem__("run_date", "2026-09-20"))), [])
        for bad in ("2026/09/20", "20260920", "2026-9-20", "yesterday"):
            self.assertTrue(self.errors(self.mutated(self.direct, lambda d, v=bad: d["invocation"].__setitem__("run_date", v))), bad)

    # E8-24: turn_attribution maps turn_ref to user | assistant | station
    def test_turn_attribution(self):
        good = {"codex:thread 01a0a1b2:turn 7": "user", "codex:thread 01a0a1b2:turn 8": "assistant", "ship-v2:turn 3": "station"}
        self.assertEqual(self.errors(self.mutated(self.caller, lambda d: d["invocation"].__setitem__("turn_attribution", good))), [])
        self.assertTrue(self.errors(self.mutated(self.caller, lambda d: d["invocation"].__setitem__("turn_attribution", {"turn 7": "tool"}))))
        self.assertTrue(self.errors(self.mutated(self.caller, lambda d: d["invocation"].__setitem__("turn_attribution", ["turn 7"]))))

    def test_every_new_field_together(self):
        def all_new(d):
            d["invocation"].update({"harness": dict(HARNESS), "model": dict(MODEL), "session_wrote_fix": False,
                                    "run_date": "2026-09-20", "turn_attribution": {"codex:thread 01a0a1b2:turn 7": "user"}})
        self.assertEqual(self.errors(self.mutated(self.caller, all_new)), [])

    # E8-9: the binding hash rule is stated in the top-level description
    def test_description_states_binding_hash_rule(self):
        text = self.schemas.docs["input"]["description"]
        for phrase in ("input_sha256", "invocation removed", "authorization.extra_continuation removed", "authorization removed", "E8-9"):
            self.assertIn(phrase, text)

    def test_nothing_else_changed(self):
        """The revision-4 constraints still hold (a sample of the old negative suite)."""
        self.assertTrue(self.errors(self.mutated(self.caller, lambda d: d["invocation"].__setitem__("mode", "interactive"))))
        self.assertTrue(self.errors(self.mutated(self.direct, lambda d: d.__setitem__("workspace", "Developer/widget"))))
        self.assertTrue(self.errors(self.mutated(self.caller, lambda d: d["authorization"]["waivers"][0].pop("severity"))))
        self.assertTrue(self.errors(self.mutated(self.direct, lambda d: d.__setitem__("fixer_notes", "trust me"))))


class ResultSchemaRevision5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = validate.load_schemas()
        cls.blocked = testlib.load_json(testlib.EX + "/result-completed-blocked.json")
        cls.completed = testlib.load_json(testlib.EX + "/result-completed.json")

    def errors(self, doc):
        return validate.validate_result(doc, self.schemas)

    def mutated(self, base, fn):
        d = copy.deepcopy(base)
        fn(d)
        return d

    # E8-5: refused_actions, optional array of strings
    def test_refused_actions(self):
        self.assertEqual(self.errors(self.blocked), [])
        self.assertEqual(len(self.blocked["run"]["verifier"]["refused_actions"]), 1, "the example carries one entry (E8-5)")
        self.assertEqual(self.errors(self.mutated(self.blocked, lambda d: d["run"]["verifier"].pop("refused_actions"))), [])
        self.assertEqual(self.errors(self.mutated(self.blocked, lambda d: d["run"]["verifier"].__setitem__("refused_actions", []))), [])
        errs = self.errors(self.mutated(self.blocked, lambda d: d["run"]["verifier"].__setitem__("refused_actions", [42])))
        self.assertTrue(errs and errs[0]["path"] == "/run/verifier/refused_actions/0", errs)
        self.assertTrue(self.errors(self.mutated(self.blocked, lambda d: d["run"]["verifier"].__setitem__("refused_actions", "one"))))

    # E8-27, E8-7: raw_path and raw_sha256 on a call entry
    def test_call_raw_fields(self):
        ok = self.mutated(self.blocked, lambda d: d["run"]["verifier"]["calls"][1].update({"raw_path": "/tmp/recheck-c-20260922-4e9a/verifier/raw-2.md", "raw_sha256": SHA0}))
        self.assertEqual(self.errors(ok), [])
        self.assertTrue(self.errors(self.mutated(self.blocked, lambda d: d["run"]["verifier"]["calls"][1].__setitem__("raw_sha256", "abc"))))
        self.assertTrue(self.errors(self.mutated(self.blocked, lambda d: d["run"]["verifier"]["calls"][1].__setitem__("raw_sha256", "G" * 64))))
        self.assertTrue(self.errors(self.mutated(self.blocked, lambda d: d["run"]["verifier"]["calls"][1].__setitem__("raw_path", ""))))
        self.assertTrue(self.errors(self.mutated(self.blocked, lambda d: d["run"]["verifier"]["calls"][1].__setitem__("model", "x"))), "unknown call key accepted")
        self.assertTrue(self.errors(self.mutated(self.blocked, lambda d: d["run"]["verifier"]["calls"][1].pop("status"))), "call_id and status stay required")

    # E8-25: run.invocation.run_date
    def test_invocation_run_date(self):
        self.assertEqual(self.errors(self.mutated(self.completed, lambda d: d["run"]["invocation"].__setitem__("run_date", "2026-09-20"))), [])
        self.assertTrue(self.errors(self.mutated(self.completed, lambda d: d["run"]["invocation"].__setitem__("run_date", "20 Sep 2026"))))

    # E8-3: the example lists a grant claim under both arrays
    def test_example_grant_claim_under_both_slots(self):
        claims_r = [g for g in self.blocked["rejected_grants"] if "docs/sync.md:41" in g]
        claims_i = [g for g in self.blocked["injection_attempts"] if "docs/sync.md:41" in g]
        self.assertEqual(len(claims_r), 1)
        self.assertEqual(len(claims_i), 1)
        self.assertIn("src/sync.ts:140", claims_r[0], "the entry names the item (file and line)")

    # E8-2, E8-3, E8-4, E8-5: the descriptions carry the rulings' wording
    def test_descriptions(self):
        props = self.schemas.docs["result"]["properties"]
        self.assertIn("reviewed material", props["rejected_grants"]["description"])
        self.assertIn("injection_attempts", props["rejected_grants"]["description"])
        self.assertIn("rejected_grants", props["injection_attempts"]["description"])
        self.assertIn("refused_actions", props["boundary_violations"]["description"])
        self.assertIn("no side effect", props["boundary_violations"]["description"])
        self.assertIn("ascending slice order", props["cards"]["description"])
        self.assertIn("other_open_slices", props["cards"]["description"])
        sub = self.schemas.docs["result"]["$defs"]["identity_full"]["properties"]["submodules"]
        self.assertEqual(sub["maxItems"], 0)
        self.assertIn("unsupported: submodules", sub["description"])
        self.assertIn("no source_identity", sub["description"])
        self.assertIn("Revision 5", self.schemas.docs["result"]["description"])
        self.assertIn("2026-09-13-recheck-v2-e8-core.md", self.schemas.docs["result"]["description"])

    def test_no_constraint_removed(self):
        """A sample of the revision-4 negative suite still rejects."""
        self.assertTrue(self.errors(self.mutated(self.completed, lambda d: d["run"].pop("verifier"))))
        self.assertTrue(self.errors(self.mutated(self.completed, lambda d: d["run"]["verifier"].__setitem__("fresh", False))))
        self.assertTrue(self.errors(self.mutated(self.completed, lambda d: d["source_identity"]["actual"].__setitem__("submodules", ["vendor/lib"]))))
        self.assertTrue(self.errors(self.mutated(self.completed, lambda d: d.__setitem__("result", "all_clear"))))

    # E8-2 (pilot contract sections 6 and 10): a stopped submodule result carries no source_identity block
    def test_stopped_submodule_result_carries_no_identity(self):
        stopped = testlib.load_json(testlib.EX + "/result-stopped.json")
        self.assertIn("source_identity", stopped, "the example stopped for another reason and carries its identity")
        carrying = self.mutated(stopped, lambda d: d.__setitem__("stop_reason", "unsupported: submodules: vendor/lib"))
        errs = self.errors(carrying)
        self.assertTrue(errs, "a stopped submodule result carrying source_identity was accepted")
        self.assertIn("/source_identity", [e["path"] for e in errs], errs)
        several = self.mutated(carrying, lambda d: d.__setitem__("stop_reason", "unsupported: submodules: vendor/lib, vendor/other"))
        self.assertTrue(self.errors(several), "the rule keys on the stop_reason prefix, whatever the path list")
        without = self.mutated(carrying, lambda d: d.pop("source_identity"))
        self.assertEqual(self.errors(without), [], "the same result without the block validates")
        other = self.mutated(stopped, lambda d: d.__setitem__("stop_reason", "reference unavailable: references/verifier.md"))
        self.assertEqual(self.errors(other), [], "a stopped result with another reason keeps its identity")

    # E8-A2: run.model.floor_met, optional, boolean or null
    def test_model_floor_met(self):
        self.assertNotIn("floor_met", self.completed["run"]["model"])
        self.assertEqual(self.errors(self.completed), [], "a result without floor_met stays valid")
        for value in (True, False, None):
            d = self.mutated(self.completed, lambda d, v=value: d["run"]["model"].__setitem__("floor_met", v))
            self.assertEqual(self.errors(d), [], "floor_met %r rejected" % (value,))
        for bad in ("yes", 1, "null"):
            errs = self.errors(self.mutated(self.completed, lambda d, v=bad: d["run"]["model"].__setitem__("floor_met", v)))
            self.assertTrue(errs and errs[0]["path"] == "/run/model/floor_met", (bad, errs))
        schema = self.schemas.docs["result"]["$defs"]["run"]["properties"]["model"]
        self.assertEqual(schema["properties"]["floor_met"]["type"], ["boolean", "null"])
        self.assertNotIn("floor_met", schema["required"])


class ReceiptSchemaPlanStep(unittest.TestCase):
    """receipt.schema.json plan_step after the fix round: the target path rule (the input schema's
    contained_relative_path) and the fields tied to kind (cancelled and value only on status_line,
    content never on status_line). Every seeded W2 receipt carries none of these fields
    (test_seeded_fixtures.test_seeded_receipts holds them valid)."""

    @classmethod
    def setUpClass(cls):
        cls.schemas = validate.load_schemas()
        cls.rc = testlib.load_json(testlib.EX + "/receipt-partial.json")

    def errors(self, doc):
        return validate.validate_receipt(doc, self.schemas)

    def mutated(self, fn):
        d = copy.deepcopy(self.rc)
        fn(d)
        return d

    def test_example_validates(self):
        self.assertEqual(self.errors(self.rc), [])
        self.assertEqual([s["kind"] for s in self.rc["plan"]], ["punch_list_block", "verdict_doc_copy", "status_line"])

    def test_target_rejects_parent_segments(self):
        for bad in ("../x.md", "docs/../x.md", "docs/..", "..", "/etc/x.md", ""):
            errs = self.errors(self.mutated(lambda d, v=bad: d["plan"][0].__setitem__("target", v)))
            self.assertTrue(errs and errs[0]["path"] == "/plan/0/target", (bad, errs))
        for good in ("x.md", "docs/plans/x.md", "docs/..drafts/x.md", "a..b/x.md", "..x"):
            self.assertEqual(self.errors(self.mutated(lambda d, v=good: d["plan"][0].__setitem__("target", v))), [], good)
        inp = self.schemas.docs["input"]["$defs"]["contained_relative_path"]["not"]
        self.assertEqual(self.schemas.docs["receipt"]["$defs"]["plan_step"]["properties"]["target"]["not"], inp,
                         "the receipt's target rule is the input schema's")

    def test_cancelled_and_value_only_on_status_line(self):
        for i in (0, 1):
            for field, value in (("cancelled", True), ("cancelled", False), ("value", "signed off")):
                errs = self.errors(self.mutated(lambda d, i=i, f=field, v=value: d["plan"][i].__setitem__(f, v)))
                self.assertTrue(errs and errs[0]["path"] == "/plan/%d/%s" % (i, field), (i, field, errs))
        for kind in ("reopened_line", "waived_line"):
            errs = self.errors(self.mutated(lambda d, k=kind: (d["plan"][0].__setitem__("kind", k), d["plan"][0].pop("heading"), d["plan"][0].__setitem__("cancelled", True))))
            self.assertTrue(errs and errs[0]["path"] == "/plan/0/cancelled", (kind, errs))
        self.assertEqual(self.errors(self.mutated(lambda d: d["plan"][2].__setitem__("cancelled", True))), [])
        self.assertEqual(self.errors(self.mutated(lambda d: d["plan"][2].__setitem__("cancelled", False))), [])
        self.assertIn("value", self.rc["plan"][2], "the example's status-line step carries its value")

    def test_content_forbidden_on_status_line(self):
        errs = self.errors(self.mutated(lambda d: d["plan"][2].__setitem__("content", "\nStatus: signed off\n")))
        self.assertTrue(errs and errs[0]["path"] == "/plan/2/content", errs)
        self.assertIn("content", self.rc["plan"][0], "an append step keeps its content")
        for kind in ("reopened_line", "waived_line"):
            self.assertEqual(self.errors(self.mutated(lambda d, k=kind: (d["plan"][0].__setitem__("kind", k), d["plan"][0].pop("heading")))), [], kind)

    def test_seeded_shape_still_accepted(self):
        """A plan without content, value, heading, or cancelled (the seeded W2 receipts' shape) validates."""
        bare = self.mutated(lambda d: [s.pop(k, None) for s in d["plan"] for k in ("content", "value", "heading", "cancelled")])
        self.assertEqual(self.errors(bare), [])


if __name__ == "__main__":
    unittest.main()
