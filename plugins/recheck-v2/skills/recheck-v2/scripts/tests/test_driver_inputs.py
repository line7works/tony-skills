"""recheck.py start: the terminal branches before verification, on the IA, I2I4, S34, and VXUM
fixtures. Every expectation is a CASES.md fact plus the contract section named on the test; no
answer key is read. Fixture inputs omit invocation.model and harness (E8-18), so each test
injects them the way the adapter would, unless the branch under test is the floor itself."""
import json
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()

SKILL_ROOT = testlib.SKILL
records_client = testlib.records_client  # E13 slice 1: resolve_scope reads through the component


class Driver(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("e8-slice2-inputs-")

    def tearDown(self):
        testlib.rmtree(self.dir)

    def case(self, lane, cid, **prep):
        cdir = testlib.build_case(lane, cid, os.path.join(self.dir, lane))
        if prep.get("raw"):
            return cdir
        testlib.prepare_input(cdir, **{k: v for k, v in prep.items() if k != "raw"})
        return cdir

    def start(self, cdir, extra=()):
        return testlib.recheck(list(extra) + ["start", os.path.join(cdir, "input.json")], cwd=self.dir)

    def assert_envelope_no_run(self, doc, fields):
        env = doc["document"]
        self.assertEqual(doc["status"], "missing_input")
        self.assertEqual(env["status"], "missing_input")
        self.assertNotIn("run", env, "no run block when the payload fails the schema (section 2)")
        self.assertEqual(env["missing_input"]["fields"], fields)
        self.assertNotIn("question", env["missing_input"])
        self.assertIsNone(doc["result"])

    def assert_envelope_path_rule(self, doc, fields, question, cdir):
        """E8-A6: a schema-valid payload that fails a path rule: the run block from the presented invocation,
        the one question on a direct interactive run only, an empty write list, nothing written."""
        env = doc["document"]
        self.assertEqual(doc["status"], "missing_input")
        self.assertEqual(env["status"], "missing_input")
        self.assertIn("run", env, "the run block comes from the presented invocation (E8-A6)")
        # E8-A30: the run block reports the presented invocation, compared against the input itself
        presented = testlib.load_json(os.path.join(cdir, "input.json"))["invocation"]
        self.assertEqual(env["run"]["invocation"]["mode"], presented["mode"])
        self.assertEqual(env["run"]["invocation"]["caller"], presented["caller"])
        self.assertEqual(env["run"]["run_id"], presented["run_id"])
        self.assertEqual(env["missing_input"]["fields"], fields)
        self.assertEqual(env["records_written"], [])
        if question:
            self.assertTrue(env["missing_input"]["question"]); self.assertEqual(doc["question"], env["missing_input"]["question"])
        else:
            self.assertNotIn("question", env["missing_input"]); self.assertIsNone(doc["question"])
        self.assertIsNone(doc["result"])
        from recheck_core import validate
        self.assertEqual(validate.validate_result(env, validate.load_schemas()), [], "the envelope validates against the result schema")

    def validate(self, cdir, result_path):
        code, out, err = testlib.run_script("validate-result.py", [result_path, "--input", os.path.join(cdir, "input.json"), "--run-dir", os.path.join(cdir, "run")], cwd=self.dir)
        self.assertEqual(code, 0, "%s\n%s" % (err, out))
        got = json.loads(out)
        self.assertEqual(got["skipped"], [], "every check runs: the input names the workspace, the run directory is supplied")
        return got

    # ---- IA: I1 ----

    def test_i1_01_schema_invalid_no_run_block(self):
        """IA CASES.md, I1-01: workspace and target absent; the two required-property errors surface at the root."""
        cdir = self.case("IA-input-authorization", "I1-01-headless-schema-invalid", raw=True)
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        self.assert_envelope_no_run(doc, ["target", "workspace"])  # the validator sorts errors by path then message
        self.assertEqual(os.listdir(os.path.join(cdir, "run")), [], "nothing is written anywhere")

    def test_i1_02_headless_build_doc_missing(self):
        """IA CASES.md, I1-02: the named doc does not exist; headless: the envelope, no question, the run block,
        the write list holds the resolved input and the result (section 2, E8-6)."""
        cdir = self.case("IA-input-authorization", "I1-02-headless-semantic-missing")
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input")
        self.assertIn("run", res)
        self.assertEqual(res["missing_input"]["fields"], ["target.build_doc"])
        self.assertNotIn("question", res["missing_input"])
        self.assertIsNone(doc["question"])
        kinds = [(w["kind"], os.path.basename(w["path"])) for w in res["records_written"]]
        self.assertEqual(kinds, [("run_artifact", "input.json"), ("run_artifact", "result.json"), ("run_artifact", "chat.md")])
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])

    def test_i1_03_interactive_question(self):
        """IA CASES.md, I1-03: the three-field line matches no shape (ruling E7-13); direct interactive: one question."""
        cdir = self.case("IA-input-authorization", "I1-03-interactive-missing")
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input")
        self.assertEqual(res["missing_input"]["fields"], ["target.build_doc"])
        self.assertTrue(res["missing_input"]["question"])
        self.assertEqual(doc["question"], res["missing_input"]["question"])
        self.assertTrue(any("field count 3" in a for a in res["missing_input"]["ambiguity"]))
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])

    def test_i1_06_headless_no_question(self):
        cdir = self.case("IA-input-authorization", "I1-06-headless-scenario-missing")
        code, doc, err = self.start(cdir)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertNotIn("question", res["missing_input"])

    def test_i1_04_station_item_without_record(self):
        """IA CASES.md, I1-04: the oneOf on target matches neither branch; the validator's one error sits at target
        with the `record` message in its context; the envelope names the leaf the items branch reports (E7-7)."""
        cdir = self.case("IA-input-authorization", "I1-04-station-caller-missing", raw=True)
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        # E8-A9: the validator's own path first, then the refined leaf
        self.assert_envelope_no_run(doc, ["target", "target.items[0].record"])

    def test_i1_05_and_07_empty_checklist_open_card(self):
        """IA CASES.md, I1-05 / I1-07: Status rejected and an empty punch list: a record gap (R14); the question
        only on the direct interactive route."""
        cdir = self.case("IA-input-authorization", "I1-05-empty-checklist-open-card")
        code, doc, err = self.start(cdir)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertIn("R14", res["missing_input"]["ambiguity"][0])
        self.assertIn("question", res["missing_input"])
        cdir = self.case("IA-input-authorization", "I1-07-empty-checklist-open-card-headless")
        code, doc, err = self.start(cdir)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertNotIn("question", res["missing_input"])
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])

    # ---- IA: I3, I5 ----

    def test_i3_stale_source(self):
        """IA CASES.md, I3-01 (pin names the base commit), I3-02 (unresolvable pin), I3-03 (dirty true against
        dirty false): stale_source, both identities, matched false, records untouched (R4)."""
        for cid, needle in (("I3-01-pin-old-commit", "expected commit"), ("I3-02-pin-unresolvable", "does not resolve"), ("I3-03-pin-dirty-false", "dirty")):
            cdir = self.case("IA-input-authorization", cid)
            before = testlib.read_text(os.path.join(cdir, "workspace", "docs/plans/2026-09-18-widget-export.md"))
            code, doc, err = self.start(cdir)
            self.assertEqual(code, 10, (cid, err))
            res = testlib.load_json(doc["result"])
            self.assertEqual(res["status"], "stale_source", cid)
            self.assertFalse(res["source_identity"]["matched"]); self.assertIn("expected", res["source_identity"])
            self.assertIn(needle, res["stop_reason"], cid)
            self.assertEqual(testlib.read_text(os.path.join(cdir, "workspace", "docs/plans/2026-09-18-widget-export.md")), before)
            self.assertFalse(os.path.exists(os.path.join(cdir, "run", "checklist.md")), "stops before the brief")
            self.assertTrue(self.validate(cdir, doc["result"])["ok"], cid)

    def test_i5_01_nothing_open(self):
        """IA CASES.md, I5-01: the one entry's latest record reads fixed and the card reads signed off (section 10)."""
        cdir = self.case("IA-input-authorization", "I5-01-empty-checklist-clear-card")
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "nothing_open"); self.assertEqual(res["checklist"]["count"], 0)
        self.assertEqual(res["checklist"]["slice"], "A")
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])

    # ---- IA: A1, A2, A3 ----

    def test_a1_01_forged_channel_fails_schema(self):
        """IA CASES.md, A1-01: channel assistant-turn fails the const; no run block, nothing written."""
        cdir = self.case("IA-input-authorization", "A1-01-forged-direct-schema", raw=True)
        code, doc, err = self.start(cdir)
        self.assert_envelope_no_run(doc, ["authorization.waivers[0].channel"])

    def test_a1_02_turn_attribution_rejects(self):
        """IA CASES.md, A1-02 with its trial map {turn 5: user, turn 6: assistant}: the waiver cites turn 6 and is
        rejected naming the attribution (E8-24); the item stays in scope."""
        cdir = self.case("IA-input-authorization", "A1-02-forged-direct-channel",
                         mutate=lambda d: d["invocation"].__setitem__("turn_attribution", {"turn 5": "user", "turn 6": "assistant"}))
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["next"], "verify")
        self.assertEqual(len(doc["rejected_grants"]), 1); self.assertIn("assistant", doc["rejected_grants"][0])
        self.assertEqual(len(doc["checklist"]), 1)
        cp = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
        self.assertEqual(cp["scope"]["grants"]["waivers"], []); self.assertEqual(len(cp["scope"]["grants"]["rejected"]), 1)
        # without the map the field rules alone apply and the waiver is accepted
        cdir = self.case("IA-input-authorization", "A1-02-forged-direct-channel")
        code, doc, err = self.start(cdir)
        self.assertEqual(doc["rejected_grants"], [])

    def test_e9_1_unmapped_turn_ref_rejected(self):
        """IA CASES.md, A1-02 with a map that lists turn 5 only: the waiver cites turn 6, which the supplied map does
        not carry, so it names no turn of the session and is rejected (ruling E9-1, E9 lane contract section 4); the
        item stays in scope. The same input with no map at all is accepted on the field rules alone (E8-24)."""
        cdir = self.case("IA-input-authorization", "A1-02-forged-direct-channel",
                         mutate=lambda d: d["invocation"].__setitem__("turn_attribution", {"turn 5": "user"}))
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["next"], "verify")
        self.assertEqual(len(doc["rejected_grants"]), 1)
        self.assertIn("not in the adapter's turn_attribution", doc["rejected_grants"][0])
        self.assertIn("E9-1", doc["rejected_grants"][0])
        self.assertEqual(len(doc["checklist"]), 1)
        cp = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
        self.assertEqual(cp["scope"]["grants"]["waivers"], []); self.assertEqual(len(cp["scope"]["grants"]["rejected"]), 1)

    def test_e9_29_empty_supplied_map_rejects(self):
        """IA CASES.md, A1-02 with turn_attribution supplied as an empty map: the map is the session's turn list and lists
        no turn, so the waiver's reference names no turn of the session and is rejected (rulings E9-1 and E9-29); an
        absent map still leaves the field rules alone in force (E8-24)."""
        cdir = self.case("IA-input-authorization", "A1-02-forged-direct-channel",
                         mutate=lambda d: d["invocation"].__setitem__("turn_attribution", {}))
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(doc["rejected_grants"]), 1)
        self.assertIn("no turn of this session", doc["rejected_grants"][0])
        self.assertEqual(len(doc["checklist"]), 1)

    def test_a2_01_station_route(self):
        """IA CASES.md, A2-01: grant 1 lacks forwarded_by (rejected, ruling E7-13); grant 2's turn_ref maps to the
        station (rejected, E8-24); both BLOCKER and MAJOR stay in scope."""
        cdir = self.case("IA-input-authorization", "A2-01-forged-caller",
                         mutate=lambda d: d["invocation"].__setitem__("turn_attribution", {"turn 5": "user", "ship-v2:turn 3": "station"}))
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(doc["rejected_grants"]), 2)
        self.assertTrue(any("forwarded_by" in r for r in doc["rejected_grants"]))
        self.assertTrue(any("station" in r for r in doc["rejected_grants"]))
        self.assertEqual([it["location"]["line"] for it in doc["checklist"]], [10, 16])

    def test_a3_01_conflicting_grants(self):
        """IA CASES.md, A3-01: a waiver and a reopening for the same item on the same date (R28)."""
        cdir = self.case("IA-input-authorization", "A3-01-conflicting-grants",
                         mutate=lambda d: d["invocation"].__setitem__("turn_attribution", {"turn 5": "user", "turn 7": "user"}))
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input")
        self.assertEqual(res["missing_input"]["fields"], ["authorization.waivers[0]", "authorization.reopen[0]"])
        self.assertIn("same date", res["missing_input"]["ambiguity"][0])
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])

    # ---- I2I4 ----

    def test_i2_named_items(self):
        """I2I4 CASES.md, I2-02: the named pair matches nothing; I2-03: it resolves to two entries (missing input)."""
        for cid in ("I2-02-named-item-none", "I2-03-named-item-two"):
            cdir = self.case("I2I4-conflicts-paths", cid)
            code, doc, err = self.start(cdir)
            self.assertEqual(code, 10, (cid, err))
            res = testlib.load_json(doc["result"])
            self.assertEqual(res["status"], "missing_input", cid)
            self.assertEqual(res["missing_input"]["fields"], ["named_items[0]"], cid)
            self.assertIn("question", res["missing_input"])

    def test_i2_04_two_candidates(self):
        """I2I4 CASES.md, I2-04: A and B both rejected with blocks dated 2026-09-19 (section 3: more than one candidate)."""
        cdir = self.case("I2I4-conflicts-paths", "I2-04-multiple-candidate-slices")
        code, doc, err = self.start(cdir)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input")
        self.assertEqual(res["missing_input"]["fields"], ["target.slice"])
        self.assertEqual(res["missing_input"]["question"], "Which slice should this recheck cover, A or B?")
        for cid in ("I2-06-headless-two-candidates", "I2-07-direct-headless-two-candidates"):
            cdir = self.case("I2I4-conflicts-paths", cid)
            code, doc, err = self.start(cdir)
            res = testlib.load_json(doc["result"])
            self.assertEqual(res["status"], "missing_input"); self.assertNotIn("question", res["missing_input"])

    def test_i2_05_single_candidate(self):
        """I2I4 CASES.md, I2-05: A rejected with an open entry, B signed off with no entry: A is selected."""
        cdir = self.case("I2I4-conflicts-paths", "I2-05-single-candidate")
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 0, err)
        self.assertEqual([it["slice"] for it in doc["checklist"]], ["A"])

    def test_i4_schema_and_path_rules(self):
        """I2I4 CASES.md: I4-01 relative workspace, I4-03 a .. segment, I4-06/07 claim with separator or newline,
        I4-08 a station caller in interactive mode (schema): the envelope with no run block, nothing written.
        I4-02, I4-04, I4-10 fail the path rules: the run block from the presented invocation, the question on the
        direct interactive route (I4-02, I4-04) and not on the station route (I4-10), an empty write list, no run
        directory (section 2 as amended, E8-A6)."""
        # E8-A9: a oneOf failure on target lists the validator's own path (target) and the refined leaf
        for cid, fields in (("I4-01-relative-workspace", ["workspace"]), ("I4-03-build-doc-dotdot", ["target", "target.build_doc"]),
                            ("I4-06-claim-with-separator", ["target", "target.items[0].claim"]), ("I4-07-claim-with-newline", ["target", "target.items[0].claim"]),
                            ("I4-08-station-caller-interactive", ["invocation.mode"])):
            cdir = self.case("I2I4-conflicts-paths", cid, raw=True)
            code, doc, err = self.start(cdir)
            self.assertEqual(code, 10, (cid, err))
            self.assert_envelope_no_run(doc, fields)
        for cid, fields, question in (("I4-02-run-dir-inside-workspace", ["invocation.run_dir"], True),
                                      ("I4-04-build-doc-symlink-escape", ["target.build_doc"], True),
                                      ("I4-10-station-run-dir-inside-workspace", ["invocation.run_dir"], False)):
            cdir = self.case("I2I4-conflicts-paths", cid)
            code, doc, err = self.start(cdir)
            self.assertEqual(code, 10, (cid, err))
            self.assert_envelope_path_rule(doc, fields, question, cdir)
            self.assertEqual(doc["document"]["run"]["run_id"], cid + "-run", cid)
            self.assertFalse(os.path.exists(os.path.join(cdir, "workspace", ".recheck-run")), cid)
            self.assertEqual(os.listdir(os.path.join(cdir, "run")), [], "%s: no run directory is created" % cid)
            self.assertEqual(testlib.project_status(os.path.join(cdir, "workspace")), "", cid)

    def test_i4_05_duplicate_items(self):
        """I2I4 CASES.md, I4-05 / I4-09: two byte-identical items; a semantic fault after validation: the run block,
        the run directory, the question on the direct interactive route only (E8-6)."""
        cdir = self.case("I2I4-conflicts-paths", "I4-05-duplicate-items")
        code, doc, err = self.start(cdir)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertIn("run", res)
        self.assertEqual(res["missing_input"]["fields"], ["target.items[1]"]); self.assertIn("question", res["missing_input"])
        cdir = self.case("I2I4-conflicts-paths", "I4-09-station-duplicate-items")
        code, doc, err = self.start(cdir)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertNotIn("question", res["missing_input"])
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])

    def test_explicit_item_slice_without_heading(self):
        """E8-A16: an explicit item whose slice is not `none` and has no `## Slice <name>` heading in its
        record.document is missing input naming target.items[i].slice; no project write."""
        item = {"severity": "BLOCKER", "location": {"file": "src/widget/export.py", "line": 17},
                "claim": "CSV export writes a title containing a comma without quoting",
                "failure_scenario": "run PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3; the data line has three columns instead of two",
                "record": {"document": "docs/plans/2026-09-18-widget-export.md", "heading": "### 2026-09-19 — review: Slice A", "date": "2026-09-19"},
                "slice": "Z"}
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean", mutate=lambda d: d.__setitem__("target", {"items": [dict(item)]}))
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input")
        self.assertEqual(res["missing_input"]["fields"], ["target.items[0].slice"])
        self.assertIn("Z", res["missing_input"]["ambiguity"][0]); self.assertIn("question", res["missing_input"])
        self.assertEqual(sorted(os.listdir(os.path.join(cdir, "run"))), ["chat.md", "input.json", "result.json"])
        self.assertEqual(testlib.project_status(os.path.join(cdir, "workspace")), "", "nothing written to the project")
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])
        # slice none needs no heading; slice A has one: the run proceeds to the brief
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean", mutate=lambda d: d.__setitem__("target", {"items": [dict(item, slice="A")]}))
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 0, err); self.assertEqual(doc["next"], "verify")

    # ---- S34 ----

    def test_s4_stale_and_submodule(self):
        """S34 CASES.md, S4-01, S4-02, S4-03: the pin differs (stale_source, R4); S4-05: the pin matches (the run
        proceeds); S4-04: an initialized submodule: stopped, the path named, no source_identity, no record write (E8-2)."""
        for cid in ("S4-01-staged-change", "S4-02-binary-change", "S4-03-untracked-content-change"):
            cdir = self.case("S34-cards-identity", cid)
            code, doc, err = self.start(cdir)
            res = testlib.load_json(doc["result"])
            self.assertEqual(res["status"], "stale_source", cid); self.assertFalse(res["source_identity"]["matched"])
            self.assertTrue(self.validate(cdir, doc["result"])["ok"], cid)
        cdir = self.case("S34-cards-identity", "S4-05-clean-match")
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 0, err); self.assertEqual(doc["next"], "verify")
        cdir = self.case("S34-cards-identity", "S4-04-submodule")
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "stopped"); self.assertEqual(res["stop_reason"], "unsupported: submodules: theme")
        self.assertNotIn("source_identity", res)
        self.assertEqual(testlib.project_status(os.path.join(cdir, "workspace")), "")
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])

    # ---- VXUM: V1, U1, M1 ----

    def test_v1_floor(self):
        """VXUM CASES.md, V1-01 (a model below opus), V1-02 (a model the profile does not list): verifier_unavailable
        with below_floor / unknown_capability; nothing graded; only input.json and the result written (E8-18)."""
        cdir = self.case("VXUM-verifier-execution", "V1-01-below-floor", model={"id": "claude-haiku-4-5", "floor_class": "below opus", "floor_met": False})
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "verifier_unavailable"); self.assertTrue(res["stop_reason"].startswith("below_floor: claude-haiku-4-5 (below opus)"))
        self.assertEqual(res["run"]["model"]["floor_met"], False)
        self.assertEqual(sorted(os.listdir(os.path.join(cdir, "run"))), ["chat.md", "input.json", "result.json"],
                         "the chat block is written on every terminal status with a run directory, verifier_unavailable included (E8-A14)")
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])
        cdir = self.case("VXUM-verifier-execution", "V1-02-unknown-model", model={"id": "mystery-1", "floor_class": "unknown", "floor_met": None})
        code, doc, err = self.start(cdir)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "verifier_unavailable"); self.assertTrue(res["stop_reason"].startswith("unknown_capability:"))
        self.assertIsNone(res["run"]["model"]["floor_met"])
        cdir = self.case("VXUM-verifier-execution", "V1-02-unknown-model", model=False)
        code, doc, err = self.start(cdir)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "verifier_unavailable"); self.assertIn("invocation.model is absent", res["stop_reason"])
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])

    def test_u1_reused_run_id(self):
        """VXUM CASES.md, U1-01: run/ holds a seeded checkpoint and log; resume false: stopped, nothing written (E8-23)."""
        cdir = self.case("VXUM-verifier-execution", "U1-01-reused-run-id")
        before = sorted(os.listdir(os.path.join(cdir, "run")))
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "stopped"); self.assertIsNone(doc["result"])
        self.assertTrue(doc["document"]["stop_reason"].startswith("reused run id: U1-01-reused-run-id-run"))
        self.assertEqual(sorted(os.listdir(os.path.join(cdir, "run"))), before)

    def test_m1_missing_reference(self):
        """VXUM CASES.md, M1-01: the install copy lacks result.schema.json; M1-02: it lacks input.schema.json. E8-17:
        stopped before any work with the relative path; the envelope unvalidated when the result schema is the one
        missing. The fixture's install/ is the skill root copied with the reference removed."""
        cdir = self.case("VXUM-verifier-execution", "M1-01-missing-reference")
        root = os.path.join(cdir, "install")
        self.assertFalse(os.path.exists(os.path.join(root, "references", "result.schema.json")))
        code, doc, err = self.start(cdir, ["--skill-root", root])
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["status"], "stopped"); self.assertTrue(doc["unvalidated"])
        self.assertTrue(doc["document"]["stop_reason"].startswith("reference unavailable: references/result.schema.json"))
        self.assertEqual(sorted(os.listdir(os.path.join(cdir, "run"))), [], "nothing written")
        cdir = self.case("VXUM-verifier-execution", "M1-02-missing-input-schema")
        root = os.path.join(cdir, "install")
        code, doc, err = self.start(cdir, ["--skill-root", root])
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["document"]["stop_reason"], "reference unavailable: references/input.schema.json")
        self.assertFalse(doc["unvalidated"])
        self.assertEqual(sorted(os.listdir(os.path.join(cdir, "run"))), [])
        # the same refusal from a scratch copy of the real skill root with the contract removed
        copy = os.path.join(self.dir, "skill-root")
        shutil.copytree(SKILL_ROOT, copy, ignore=shutil.ignore_patterns("tests", "__pycache__", "examples"))
        os.remove(os.path.join(copy, "references", "pilot-contract.md"))
        cdir = self.case("VXUM-verifier-execution", "X1-01-runnable-scenario")
        code, doc, err = self.start(cdir, ["--skill-root", copy])
        self.assertEqual(doc["document"]["stop_reason"], "reference unavailable: references/pilot-contract.md")

    def test_unparseable_reference_is_the_stopped_envelope(self):
        """A reference that exists but does not parse stops the run like a missing one: the stopped envelope on
        stdout (exit 10), stop_reason `reference unavailable: references/<name>`, nothing written; unvalidated only
        when the result schema is at fault; never exit 1 or 2 (E8-17, E8-A10). Phase commands too."""
        for name, unvalidated in (("input.schema.json", False), ("result.schema.json", True)):
            copy = os.path.join(self.dir, "root-" + name)
            shutil.copytree(SKILL_ROOT, copy, ignore=shutil.ignore_patterns("tests", "__pycache__", "examples"))
            with open(os.path.join(copy, "references", name), "w", encoding="utf-8") as fh:
                fh.write("{ not json")
            cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
            code, doc, err = self.start(cdir, ["--skill-root", copy])
            self.assertEqual(code, 10, (name, err))
            self.assertEqual(doc["status"], "stopped"); self.assertEqual(doc["unvalidated"], unvalidated, name)
            self.assertTrue(doc["document"]["stop_reason"].startswith("reference unavailable: references/%s" % name), doc["document"]["stop_reason"])
            self.assertEqual(sorted(os.listdir(os.path.join(cdir, "run"))), [], "nothing written")
        # a phase command against a run directory: the same envelope, exit 10, not 2
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 0, err)
        listing = sorted(os.listdir(os.path.join(cdir, "run")))
        copy = os.path.join(self.dir, "root-input.schema.json")
        code, doc, err = testlib.recheck(["--skill-root", copy, "record", "--run-dir", os.path.join(cdir, "run")], cwd=self.dir)
        self.assertEqual(code, 10, err); self.assertEqual(doc["status"], "stopped")
        self.assertEqual(doc["document"]["stop_reason"], "reference unavailable: references/input.schema.json")
        self.assertEqual(sorted(os.listdir(os.path.join(cdir, "run"))), listing, "nothing written")
        # a schema that parses but is not a schema is the same stop
        copy = os.path.join(self.dir, "root-not-a-schema")
        shutil.copytree(SKILL_ROOT, copy, ignore=shutil.ignore_patterns("tests", "__pycache__", "examples"))
        with open(os.path.join(copy, "references", "checkpoint.schema.json"), "w", encoding="utf-8") as fh:
            fh.write('{"type": "nonsense"}')
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        code, doc, err = self.start(cdir, ["--skill-root", copy])
        self.assertEqual(code, 10, err)
        self.assertEqual(doc["document"]["stop_reason"], "reference unavailable: references/checkpoint.schema.json")

    def test_nonexistent_skill_root_is_usage(self):
        """A --skill-root that is not a directory is a usage error (exit 2, the path named), never exit 1."""
        missing = os.path.join(self.dir, "no-such-root")
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        for args in (["--skill-root", missing, "start", os.path.join(cdir, "input.json")], ["--skill-root", missing, "skill-identity"],
                     ["--skill-root", missing, "record", "--run-dir", os.path.join(cdir, "run")]):
            code, out, err = testlib.run_script("recheck.py", args, cwd=self.dir)
            self.assertEqual(code, 2, (args, err)); self.assertEqual(out, ""); self.assertIn(missing, err)
        self.assertEqual(os.listdir(os.path.join(cdir, "run")), [])
        code, out, err = testlib.run_script("validate-result.py", [os.path.join(testlib.EX, "result-nothing-open.json"), "--skill-root", missing], cwd=self.dir)
        self.assertEqual(code, 2, err); self.assertEqual(out, ""); self.assertIn(missing, err)

    def test_review_sheet_verdicts(self):
        """F1 CASES.md, F1-04: the kit sheet (read); F1-05: headings Checklist and Severity only (not the kit sheet)."""
        cdir = self.case("F1-fixed-defect", "F1-04-sheet-bar")
        code, doc, err = self.start(cdir)
        self.assertEqual(doc["review_sheet"], "read"); self.assertEqual(len(doc["severity_bar"]), 3)
        self.assertIn("Review sheet (read only", testlib.read_text(doc["brief"]))
        cdir = self.case("F1-fixed-defect", "F1-05-non-sheet")
        code, doc, err = self.start(cdir)
        self.assertEqual(doc["review_sheet"], "not_kit_sheet"); self.assertEqual(doc["severity_bar"], [])
        self.assertNotIn("Review sheet (read only", testlib.read_text(doc["brief"]))

    def test_brief_carries_no_run_id(self):
        """E8-11: the brief names items by index from 0 and carries no run id or run-dir path other than the scratch."""
        cdir = self.case("F1-fixed-defect", "F1-09-two-slices")
        code, doc, err = self.start(cdir)
        brief = testlib.read_text(doc["brief"])
        self.assertIn("### Item 0", brief)
        self.assertNotIn("F1-09-two-slices-run", brief)
        run_dir = os.path.join(cdir, "run")
        self.assertEqual(brief.count(run_dir), brief.count(os.path.join(run_dir, "verifier")), "the run dir appears only as the scratch prefix")
        self.assertEqual([it["slice"] for it in doc["checklist"]], ["A"], "Slice B's entry stays out of the checklist")

    # ---- the fix round after Astra's review (E8-A19, E8-A29, E8-A32, E8-A35) ----

    ITEM = {"severity": "BLOCKER", "location": {"file": "src/widget/export.py", "line": 17},
            "claim": "CSV export writes a title containing a comma without quoting",
            "failure_scenario": "run PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3; the data line has three columns instead of two",
            "record": {"document": "docs/plans/2026-09-18-widget-export.md", "heading": "### 2026-09-19 — review: Slice A", "date": "2026-09-19"},
            "slice": "A"}

    def test_explicit_item_record_document_symlink_escape(self):
        """E8-A19: an explicit item's record.document whose parent directory is a symlink to a directory outside
        the workspace fails the path rules exactly like build_doc (section 2): invalid input, the run block from
        the presented invocation, no run directory, nothing written."""
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean", raw=True)
        ws = os.path.join(cdir, "workspace")
        outside = os.path.join(self.dir, "outside-docs")
        os.makedirs(outside)
        shutil.copyfile(os.path.join(ws, "docs", "plans", "2026-09-18-widget-export.md"), os.path.join(outside, "2026-09-18-widget-export.md"))
        os.symlink(outside, os.path.join(ws, "docs", "linked"))
        item = dict(self.ITEM, record=dict(self.ITEM["record"], document="docs/linked/2026-09-18-widget-export.md"))
        testlib.prepare_input(cdir, mutate=lambda d: d.__setitem__("target", {"items": [item]}))
        run_dir = os.path.join(cdir, "run")
        before = sorted(os.listdir(run_dir)) if os.path.isdir(run_dir) else None
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        self.assert_envelope_path_rule(doc, ["target.items[0].record.document"], True, cdir)
        self.assertIn("docs/linked/2026-09-18-widget-export.md resolves outside the workspace after symlinks", doc["document"]["missing_input"]["ambiguity"][0])
        self.assertEqual(sorted(os.listdir(run_dir)) if os.path.isdir(run_dir) else None, before, "no run directory is created")
        self.assertTrue(before in (None, []), before)
        from recheck_core import inputs
        self.assertEqual(inputs.path_rules({"workspace": ws, "invocation": {"run_dir": run_dir}, "target": {"items": [dict(item, record={"document": "../x.md"})]}}, lambda p: (True, "")),
                         [("target.items[0].record.document", "record.document must be relative with no .. segment")])
        self.assertEqual(inputs.path_rules({"workspace": ws, "invocation": {"run_dir": run_dir}, "target": {"items": [dict(self.ITEM)]}}, lambda p: (True, "")), [])

    def test_named_entries_resolve_before_nothing_open(self):
        """E8-A29: the S2-03 shape (a cleared entry, a user reopening naming it, target.build_doc without slice)
        resolves to a one-item scope, not nothing_open; named_items naming nothing on a clear doc is missing
        input; nothing named on the clear doc is nothing_open."""
        from recheck_core import inputs
        cdir = self.case("S2-waivers-reopening", "S2-03-reopened", mutate=lambda d: d["target"].pop("slice"))
        doc = testlib.load_json(os.path.join(cdir, "input.json"))
        grants = inputs.collect_grants(doc)
        scope = inputs.resolve_scope(doc, os.path.join(cdir, "workspace"), grants["reopenings"], records_client())
        self.assertEqual(scope["status"], "ok", scope)
        self.assertEqual(len(scope["checklist"]), 1); self.assertEqual(scope["source"], "named_items"); self.assertEqual(scope["slice"], "A")
        code, started, err = self.start(cdir)
        self.assertEqual(code, 0, err); self.assertEqual(started["next"], "verify")
        self.assertEqual([(it["location"]["line"], it["slice"]) for it in started["checklist"]], [(11, "A")])

        def name_nothing(d):
            d["target"].pop("slice")
            d.pop("authorization")
            d["named_items"] = [{"location": {"file": "src/widget/export.py", "line": 99}, "claim": "no such entry"}]
        cdir = self.case("S2-waivers-reopening", "S2-03-reopened", mutate=name_nothing)
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertEqual(res["missing_input"]["fields"], ["named_items[0]"])

        def name_none(d):
            d["target"].pop("slice")
            d.pop("authorization")
            d.pop("named_items")
        cdir = self.case("S2-waivers-reopening", "S2-03-reopened", mutate=name_none)
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err)
        self.assertEqual(testlib.load_json(doc["result"])["status"], "nothing_open")

    def test_empty_failure_scenario_is_missing_input(self):
        """E8-A32: a review finding with five fields and an empty fourth (the failure scenario) is missing input
        naming target.build_doc and the record's line, from resolve_scope and before checklist.md or the
        checkpoint is written; exit 10, status missing_input, the question on the direct interactive route."""
        from recheck_core import inputs
        cdir = self.case("F1-fixed-defect", "F1-01-fixed-clean")
        ws = os.path.join(cdir, "workspace")
        rel = "docs/plans/2026-09-18-widget-export.md"
        path = os.path.join(ws, rel)
        lines = testlib.read_text(path).split("\n")
        idx = next(i for i, l in enumerate(lines) if l.startswith("- BLOCKER · "))
        fields = lines[idx][2:].split(" · ")
        self.assertEqual(len(fields), 5)
        fields[3] = ""
        lines[idx] = "- " + " · ".join(fields)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        doc = testlib.load_json(os.path.join(cdir, "input.json"))
        scope = inputs.resolve_scope(doc, ws, [], records_client())
        self.assertEqual(scope["status"], "missing_input")
        self.assertEqual(scope["fields"], ["target.build_doc"])
        self.assertEqual(scope["ambiguity"], ["the record at %s:%d has no failure scenario; supply or confirm it" % (rel, idx + 1)])
        self.assertEqual(scope["question"], scope["ambiguity"][0])
        code, doc, err = self.start(cdir)
        self.assertEqual(code, 10, err); self.assertEqual(doc["status"], "missing_input")
        res = testlib.load_json(doc["result"])
        self.assertEqual(res["status"], "missing_input"); self.assertEqual(res["missing_input"]["fields"], ["target.build_doc"])
        self.assertEqual(res["missing_input"]["question"], scope["question"])
        self.assertFalse(os.path.exists(os.path.join(cdir, "run", "checklist.md")))
        self.assertEqual(sorted(os.listdir(os.path.join(cdir, "run"))), ["chat.md", "input.json", "result.json"])
        self.assertTrue(self.validate(cdir, doc["result"])["ok"])

    def test_a1_01_schema_rejected_grant_is_listed(self):
        """E8-A35: the A1-01 payload (a waiver with channel assistant-turn on the direct route) fails the schema;
        the envelope names the channel path among the fields and lists the grant under rejected_grants as
        `<JSON path>: <file:line> · <why>`; no run block, no run directory, an empty write list."""
        from recheck_core import inputs, validate
        cdir = self.case("IA-input-authorization", "A1-01-forged-direct-schema", raw=True)
        code, doc, err = self.start(cdir)
        self.assert_envelope_no_run(doc, ["authorization.waivers[0].channel"])
        env = doc["document"]
        self.assertEqual(len(env["rejected_grants"]), 1)
        self.assertTrue(env["rejected_grants"][0].startswith("authorization.waivers[0]: src/widget/export.py:10 · "), env["rejected_grants"][0])
        self.assertIn("user-turn", env["rejected_grants"][0])
        self.assertEqual(env.get("records_written", []), [])
        self.assertEqual(os.listdir(os.path.join(cdir, "run")), [])
        self.assertEqual(validate.validate_result(env, validate.load_schemas()), [], "the envelope validates against the result schema")
        errors = [{"path": "/authorization/reopen/1/turn_ref", "message": "1 is not of type 'string'"},
                  {"path": "/authorization/extra_continuation", "message": "'turn_ref' is a required property"},
                  {"path": "/authorization/waivers/0/channel", "message": "'user-turn' was expected"},
                  {"path": "/authorization/waivers/0/severity", "message": "'HUGE' is not one of ['BLOCKER', 'MAJOR', 'MINOR']"},
                  {"path": "/target", "message": "not a grant path"}]
        payload = {"authorization": {"waivers": [{"item": {"location": {"file": "a.py", "line": 1}, "claim": "c"}}],
                                     "reopen": [{}, {"item": {"claim": "c"}}], "extra_continuation": {"by": "user"}}}
        self.assertEqual(inputs.schema_rejected_grants(errors, payload),
                         ["authorization.reopen[1]: - · 1 is not of type 'string'",
                          "authorization.extra_continuation: - · 'turn_ref' is a required property",
                          "authorization.waivers[0]: a.py:1 · 'user-turn' was expected; 'HUGE' is not one of ['BLOCKER', 'MAJOR', 'MINOR']"])
        self.assertNotIn("rejected_grants", inputs.envelope({}, ["target"], ["x"], schema_errors=[errors[-1]]))


if __name__ == "__main__":
    unittest.main()
