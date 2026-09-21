"""E13 slice 1, send-back 1: the semantic validator reads the records through the component.

Three things are proved here.

1. **V17** is no longer "every ledger line the run wrote parses back under Appendix A". It is now
   "the run's events, rendered by `records.py render --run-id`, are exactly the lines the document
   holds at the places the receipt names". A document line altered after the write fails it, and a
   log event this run wrote with no matching line fails it.
2. **V6** reproduces the card mapping over the open set the component derives, not over a
   re-parse of the document's records. Beside it, the NARROW agreement test question 7 of the
   builder's report described: over every movable card value and every open-set shape the mapping
   distinguishes, the core's `card_after` equals the component's `card_derived`; for a card the
   skill may not move, the difference is by design and is pinned here.
3. **The record grammar that remains in `ledger.py` is a DETECTOR ONLY.** The component's reader is
   deliberately tolerant where the core's is strict (amendment A3: a grant line counts with or
   without its leading `- ` bullet, and the core's strict reader still requires it). A document
   that makes the two disagree therefore decides the question: the run must follow the component.
   This test fails the moment the detector is used to decide state.
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import ledger, validate  # noqa: E402
from recheck_core import records_client as rc  # noqa: E402

RECORDS = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir, "records"))
DOC = "docs/plans/2026-09-18-widget-export.md"
LOG = "docs/records/docs__plans__2026-09-18-widget-export.events.jsonl"


class CompletedRun(unittest.TestCase):
    """A real F1-01 run, driven to `completed`, as the subject of the V17 and V6 checks."""

    LANE = "F1-fixed-defect"
    CASE = "F1-01-fixed-clean"

    def setUp(self):
        self.dir = testlib.make_scratch("e13-validator-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case(self.LANE, self.CASE, self.dir)
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")
        self.input = testlib.prepare_input(self.case)
        self.client = rc.open_client(records_root=RECORDS)
        self.drive()

    def drive(self):
        code, doc, err = testlib.recheck(["start", self.input], cwd=self.dir)
        self.assertEqual(code, 0, err)
        items = [{"index": i, "location": "%s:%s" % (it["location"]["file"], it["location"]["line"]),
                  "disposition": "fixed", "method": "executed"} for i, it in enumerate(doc["checklist"])]
        testlib.write_report(self.run_dir, testlib.canned_report(items))
        code, _, err = testlib.recheck(["record-call", "--run-dir", self.run_dir, "--call-id", doc["call_id"],
                                        "--status", "ok", "--raw", os.path.join(self.run_dir, "verifier", "raw.md"),
                                        "--kind", "subagent", "--model", "claude-fable-5-1"], cwd=self.dir)
        self.assertEqual(code, 0, err)
        for i in range(len(items)):
            code, _, err = testlib.recheck(["adjudicate", "--run-dir", self.run_dir, "--item", str(i),
                                            "--action", "confirmed"], cwd=self.dir)
            self.assertEqual(code, 0, err)
        code, doc, err = testlib.recheck(["record", "--run-dir", self.run_dir], cwd=self.dir)
        self.assertEqual(code, 10, err)
        self.result = testlib.load_json(os.path.join(self.run_dir, "result.json"))
        self.assertEqual(self.result["status"], "completed")

    def semantic(self, check_id=None):
        """Run the validator the way `validate-result.py` does; return its findings."""
        schemas = validate.load_schemas()
        out = validate.run_semantic(self.result, input_doc=testlib.load_json(os.path.join(self.run_dir, "input.json")),
                                    run_dir=self.run_dir, workspace=self.workspace, schemas=schemas,
                                    records=self.client)
        if check_id is None:
            return out
        return [f for f in out["semantic"] if f["id"] == check_id]

    def doc_path(self):
        return os.path.join(self.workspace, DOC)

    def rewrite_doc(self, change):
        with open(self.doc_path(), "r", encoding="utf-8") as fh:
            text = fh.read()
        new = change(text)
        self.assertNotEqual(new, text, "the test's own edit changed nothing")
        with open(self.doc_path(), "w", encoding="utf-8") as fh:
            fh.write(new)


class V17RendersToTheDocument(CompletedRun):
    def test_a_clean_run_passes(self):
        out = self.semantic()
        self.assertEqual([f for f in out["semantic"] if f["id"] in ("V6", "V17")], [])
        self.assertEqual([s for s in out["skipped"] if s["id"] in ("V6", "V17")], [])

    def test_a_document_line_altered_after_the_write_fails(self):
        self.rewrite_doc(lambda t: t.replace("· fixed · executed ran the scenario command",
                                             "· fixed · executed something else entirely"))
        findings = self.semantic("V17")
        self.assertTrue(findings, "an altered line must fail V17")
        self.assertTrue(any("no longer" in f["message"] or "does not hold" in f["message"] for f in findings),
                        findings)

    def test_a_log_event_with_no_matching_line_fails(self):
        """An extra event this run wrote, appended after the document steps: the run's events no
        longer render to the lines the document holds."""
        run_id = testlib.load_json(os.path.join(self.run_dir, "receipt.json"))["run_id"]
        state = self.client.state(self.workspace, DOC)
        identity = self.client.identity(self.workspace)["identity"]
        extra = {"v": 1, "kind": "defect_raised", "at": "2026-09-20T10:00:00Z", "ledger_doc": DOC,
                 "actor": {"station": "recheck-v2", "run_id": run_id, "harness": "test-harness"},
                 "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
                 "slice": "A", "severity": "MAJOR",
                 "location": {"raw": "src/widget/export.py:44", "file": "src/widget/export.py", "line": 44,
                              "line_end": None, "tag": None, "more": [], "resolved": True},
                 "claim": "an event with no line in the document", "scenario": "run it once",
                 "raised_by": None, "caused_by": None}
        self.client.append(self.workspace, DOC, [extra], state["head"], self.dir)
        findings = self.semantic("V17")
        self.assertTrue(findings, "an event with no line must fail V17")

    def test_v17_reads_the_records_through_the_component(self):
        """The check must not be satisfiable by the document alone: with the log gone it cannot run."""
        os.remove(os.path.join(self.workspace, LOG))
        findings = self.semantic("V17")
        self.assertTrue(findings, "V17 must fail when the run's events are not in the log")


class V6FromDerivedState(CompletedRun):
    def test_the_mapping_comes_from_the_component(self):
        cards = self.result["cards"]
        self.assertEqual([c["slice"] for c in cards], ["A"])
        self.assertEqual(cards[0]["after"], "signed off")
        self.assertEqual(self.semantic("V6"), [])
        state = self.client.state(self.workspace, DOC)
        self.assertEqual(state["slices"][0]["card_derived"], "signed off")
        self.assertEqual(state["slices"][0]["card_observed"], "signed off")

    def test_a_card_the_open_set_does_not_support_fails(self):
        self.result["cards"][0]["after"] = "rejected"
        findings = self.semantic("V6")
        self.assertTrue(findings, "a card the open set does not support must fail V6")

    def test_v6_does_not_re_parse_the_document_for_the_open_set(self):
        """The record lines are removed from the document and the log is left alone: the mapping
        still reproduces, because it is the component's open set and not the document's."""
        self.rewrite_doc(lambda t: "\n".join(l for l in t.split("\n") if not l.startswith("- ")))
        self.assertEqual(self.semantic("V6"), [],
                         "V6 reproduced a different mapping once the document's lines were gone")


class CardMappingAgreement(unittest.TestCase):
    """Report question 7, answered narrowly: where the core's mapping and the component's agree,
    and the one place they are designed to differ."""

    MOVABLE = ("not started", "rejected", "signed off with conditions", "signed off")
    # every open-set shape the mapping distinguishes, with the value it maps to
    SHAPES = (((), "signed off"),
              (("MINOR",), "signed off"),
              (("MAJOR",), "signed off with conditions"),
              (("MAJOR", "MINOR"), "signed off with conditions"),
              (("BLOCKER",), "rejected"),
              (("BLOCKER", "MAJOR"), "rejected"),
              (("BLOCKER", "MAJOR", "MINOR"), "rejected"))

    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("e13-card-agreement-")
        cls.client = rc.open_client(records_root=RECORDS)

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def build(self, name, severities, card):
        """A workspace whose slice A holds one open finding per severity and a `Status:` of `card`."""
        lib = testlib.fixturelib()

        def builder(fx):
            fx.skeleton()
            doc = fx.build_doc("widget-export", "2026-09-18", "Widget export",
                               [{"name": "A", "title": "CSV export", "status": card}])
            fx.commit("scaffold", lib.GIT_BASE_DATE)
            findings = []
            for i, severity in enumerate(severities):
                findings.append({"severity": severity, "file": "src/widget/export.py", "line": 10 + i,
                                 "claim": "claim %d" % i, "scenario": "run it and read line %d" % (10 + i)})
            if findings:
                fx.review_block(doc, "2026-09-19", "A", findings)
            fx.commit("the review", fx.next_when())
            fx.manifest()

        case = lib.build_case(self.dir, name, "agreement", [], builder)
        return os.path.join(self.dir, name, "workspace")

    def derived(self, workspace):
        state = self.client.state(workspace, DOC)
        rows = [row for row in state["slices"] if row["name"] == "A"]
        return (rows[0]["card_derived"], rows[0]["card_observed"]) if rows else (None, None)

    def test_the_two_agree_on_every_movable_card_and_every_shape(self):
        checked = 0
        for card in self.MOVABLE:
            for severities, expected in self.SHAPES:
                name = "m-%s-%s" % (card.replace(" ", "_"), "-".join(severities) or "none")
                workspace = self.build(name, severities, card)
                self.client.import_legacy(workspace, DOC)
                derived, observed = self.derived(workspace)
                self.assertEqual(observed, card, name)
                open_entries = [{"severity": s} for s in severities]
                mapped = ledger.card_after(card, open_entries)
                self.assertEqual(mapped, expected, "%s: the core's own mapping moved" % name)
                self.assertEqual(derived, mapped,
                                 "%s: card_derived %r, card_after %r" % (name, derived, mapped))
                checked += 1
        self.assertEqual(checked, len(self.MOVABLE) * len(self.SHAPES))

    def test_built_keeps_built_on_both_sides(self):
        for severities, _ in self.SHAPES:
            name = "b-%s" % ("-".join(severities) or "none")
            workspace = self.build(name, severities, "built")
            self.client.import_legacy(workspace, DOC)
            derived, observed = self.derived(workspace)
            self.assertEqual(observed, "built", name)
            self.assertEqual(derived, "built", name)
            self.assertEqual(ledger.card_after("built", [{"severity": s} for s in severities]), "built", name)

    def test_the_designed_difference_on_a_card_the_skill_may_not_move(self):
        """A `Status:` text that is not one of the six card values reads `none`. The core's mapping
        leaves a non-movable card alone; the component's `card_derived` computes the mapping anyway.
        That difference is why `card_after` stays the core's decision (ruling E13-1)."""
        workspace = self.build("none-card", ("BLOCKER",), "in progress")
        self.client.import_legacy(workspace, DOC)
        derived, observed = self.derived(workspace)
        self.assertEqual(observed, "none", "a Status: text outside the six values reads none")
        self.assertEqual(derived, "rejected", "the component computes the mapping anyway")
        self.assertEqual(ledger.card_after("none", [{"severity": "BLOCKER"}]), "none",
                         "the core leaves a card it may not move alone")
        self.assertNotEqual(derived, ledger.card_after("none", [{"severity": "BLOCKER"}]),
                            "this is the one designed difference; if it closes, card_after can go")


class TheGrammarIsADetectorOnly(unittest.TestCase):
    """The record grammar left in `ledger.py` decides whether to STOP, never what is open.

    Amendment A3: the component reads a `WAIVED (per user)` line with or without its leading `- `
    bullet; the core's strict reader requires the bullet and does not see the line at all (it is
    not a record for it, and not an ambiguity either). So a document carrying a bullet-less waiver
    makes the two readers disagree about one finding, with no ambiguity to stop on, and the run's
    answer says which of them decided.
    """

    def setUp(self):
        self.dir = testlib.make_scratch("e13-detector-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.workspace = self.build()

    def build(self):
        lib = testlib.fixturelib()

        def builder(fx):
            fx.skeleton()
            doc = fx.build_doc("widget-export", "2026-09-18", "Widget export",
                               [{"name": "A", "title": "CSV export", "status": "signed off"}])
            fx.commit("scaffold", lib.GIT_BASE_DATE)
            fx.review_block(doc, "2026-09-19", "A",
                            [{"severity": "BLOCKER", "file": "src/widget/export.py", "line": 11,
                              "claim": "a title with a comma is exported unquoted",
                              "scenario": "export a row whose title holds a comma; one extra column"}])
            # the bullet-less grant line: a record for the component (A3), invisible to the core's
            # strict reader, and not an ambiguity for it either
            fx.raw_ledger_line(doc, 'WAIVED (per user) · 2026-09-20 · BLOCKER · src/widget/export.py:11 · '
                                    'a title with a comma is exported unquoted · "ship it"\n')
            fx.commit("the review and the bullet-less waiver", fx.next_when())
            fx.manifest()

        case = lib.build_case(self.dir, "detector", "detector", [], builder)
        return os.path.join(self.dir, "detector", "workspace")

    def test_the_core_s_strict_reader_sees_the_finding_as_open_and_flags_nothing(self):
        with open(os.path.join(self.workspace, DOC), "r", encoding="utf-8") as fh:
            parsed = ledger.parse_document(fh.read(), DOC)
        opened = ledger.open_set(parsed)
        self.assertEqual(opened["ambiguities"], [], "the detector has nothing to stop on here")
        self.assertEqual([(e["line"], e["state"]) for e in opened["entries"]], [(11, "open")],
                         "the strict reader does not see the bullet-less waiver")

    def test_the_component_sees_it_waived(self):
        client = rc.open_client(records_root=RECORDS)
        client.import_legacy(self.workspace, DOC)
        state = client.state(self.workspace, DOC)
        self.assertEqual([f["status"] for f in state["findings"]], ["waived"])

    def test_the_run_follows_the_component_not_the_detector(self):
        case = os.path.dirname(self.workspace)
        run_dir = os.path.join(case, "run")
        os.makedirs(run_dir, exist_ok=True)
        payload = {"protocol_version": 1, "workspace": self.workspace,
                   "invocation": {"mode": "interactive", "caller": "direct", "resume": False,
                                  "run_id": "detector-run", "run_dir": run_dir,
                                  "run_date": "2026-09-20",
                                  "harness": dict(testlib.HARNESS), "model": dict(testlib.MODEL)},
                   "target": {"build_doc": DOC, "slice": "A"}}
        path = os.path.join(case, "input.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        code, doc, err = testlib.recheck(["start", path], cwd=self.dir)
        self.assertEqual(code, 10, "the detector decided the open set: %s" % json.dumps(doc)[:400])
        self.assertEqual(doc["status"], "nothing_open",
                         "the component says the finding is waived, so nothing is open")


BASIS = "default table: a real defect with a concrete failure path"


class V17DefectsAndMarkers(CompletedRun):
    """E8-A25 and the grant markers, held against the run's own events rather than a re-parse.

    This is where the guarantee `test_validate_fix4.V17DefectSlice` used to hold lives now: that
    class built a document and a result by hand and read the written line back with the core's
    grammar, which is exactly the second reader E13 slice 1 removes. The charge is now the slice
    the `defect_raised` event carries, so the test drives a real run that raises one.
    """

    CASE = "F1-02-regression"

    def drive(self):
        code, doc, err = testlib.recheck(["start", self.input], cwd=self.dir)
        self.assertEqual(code, 0, err)
        items = [{"index": i, "location": "%s:%s" % (it["location"]["file"], it["location"]["line"]),
                  "disposition": "fixed", "method": "executed",
                  "location_after_fix": "src/widget/export.py:20"} for i, it in enumerate(doc["checklist"])]
        defects = [{"caused_by_index": 0, "location": "src/widget/export.py:20",
                    "claim": "a zero quantity exports as an empty cell",
                    "failure_scenario": "run it with Bolt 0; the data line reads Bolt, with an empty qty cell",
                    "evidence": [{"kind": "command", "detail": "printed Bolt,", "artifact": None}]}]
        testlib.write_report(self.run_dir, testlib.canned_report(items, new_defects=defects))
        code, _, err = testlib.recheck(["record-call", "--run-dir", self.run_dir, "--call-id", doc["call_id"],
                                        "--status", "ok", "--raw", os.path.join(self.run_dir, "verifier", "raw.md"),
                                        "--kind", "subagent", "--model", "claude-fable-5-1"], cwd=self.dir)
        self.assertEqual(code, 0, err)
        for i in range(len(items)):
            code, _, err = testlib.recheck(["adjudicate", "--run-dir", self.run_dir, "--item", str(i),
                                            "--action", "confirmed"], cwd=self.dir)
            self.assertEqual(code, 0, err)
        code, _, err = testlib.recheck(["new-defect", "--run-dir", self.run_dir, "--index", "0",
                                        "--severity", "MAJOR", "--severity-basis", BASIS], cwd=self.dir)
        self.assertEqual(code, 0, err)
        code, doc, err = testlib.recheck(["record", "--run-dir", self.run_dir], cwd=self.dir)
        self.assertEqual(code, 10, err)
        self.result = testlib.load_json(os.path.join(self.run_dir, "result.json"))
        self.assertEqual(self.result["status"], "completed")

    def test_the_run_raised_the_defect_and_the_check_passes(self):
        self.assertEqual(len(self.result["new_defects"]), 1)
        self.assertEqual(self.result["new_defects"][0]["charged_to_slice"], "A")
        self.assertEqual(self.semantic("V17"), [])

    def test_a_charge_the_event_does_not_carry_fails(self):
        self.result["new_defects"][0]["charged_to_slice"] = "B"
        findings = self.semantic("V17")
        self.assertEqual([f["path"] for f in findings], ["/new_defects/0/charged_to_slice"], findings)
        self.assertIn("charges 'A'", findings[0]["message"])
        self.assertIn("E8-A25", findings[0]["message"])

    def test_a_defect_no_event_of_this_run_raised_fails(self):
        self.result["new_defects"][0]["claim"] = "a claim no event carries"
        findings = self.semantic("V17")
        self.assertEqual([f["path"] for f in findings], ["/new_defects/0"], findings)


RESTORED_FOR_THE_COPY = ("find_entries", "entry_claim_field")


class TheRestoredHelpersAreNeverOnTheDecisionPath(unittest.TestCase):
    """`ledger.find_entries` and `ledger.entry_claim_field` exist for the component's copy, not for
    this skill's decisions.

    Send-back 1 deleted them once their callers moved to `records_view.match_entries` and
    `records_view.claim_field`. The records component holds a BYTE-FOR-BYTE copy of this whole file
    (`records_core/legacy.py`, ruling E12-2, checked by that component's
    `test_parity.TheCopyIsTheSameReader`), so deleting them broke the copy — the builder's finding
    5. Send-back 2 restored the file to `main`'s bytes, which means the two functions are back in
    the module while the join they used to do stays in `records_view`.

    Two guards keep it that way. The first is a source read: no file of this skill may name either
    helper on `ledger`, or import it by name. The second is dynamic: the decision path is run with
    both booby-trapped, so a call raises rather than quietly working.
    """

    CORE = os.path.join(testlib.SCRIPTS, "recheck_core")

    def source_files(self):
        out = [os.path.join(testlib.SCRIPTS, name) for name in sorted(os.listdir(testlib.SCRIPTS))
               if name.endswith(".py")]
        out += [os.path.join(self.CORE, name) for name in sorted(os.listdir(self.CORE))
                if name.endswith(".py") and name != "ledger.py"]
        return out

    def test_no_shipped_file_calls_either_helper(self):
        offenders = []
        for path in self.source_files():
            with open(path, "r", encoding="utf-8") as fh:
                for number, line in enumerate(fh, 1):
                    code = line.split("#", 1)[0]
                    for name in RESTORED_FOR_THE_COPY:
                        if ("ledger.%s(" % name) in code or ("import %s" % name) in code:
                            offenders.append("%s:%d %s" % (os.path.basename(path), number, line.strip()))
        self.assertEqual(offenders, [],
                         "the join belongs to records_view; these call the copy's helpers instead")

    def test_the_decision_path_runs_with_both_booby_trapped(self):
        """Scope resolution and the waiver join, with the two helpers replaced by traps."""
        from recheck_core import inputs, ledger as ledger_mod, records_view, result as result_mod

        def trap(*args, **kwargs):
            raise AssertionError("a run's decision path called one of the copy's helpers")

        case = testlib.build_case("S2-waivers-reopening", "S2-01-waived-clearance", self.dir)
        workspace = os.path.join(case, "workspace")
        doc = testlib.load_json(testlib.prepare_input(case))
        client = testlib.records_client()
        saved = {name: getattr(ledger_mod, name) for name in RESTORED_FOR_THE_COPY}
        for name in RESTORED_FOR_THE_COPY:
            setattr(ledger_mod, name, trap)
        try:
            grants = inputs.collect_grants(doc)
            scope = inputs.resolve_scope(doc, workspace, grants["reopenings"], client)
            self.assertEqual(scope["status"], "ok", scope)
            self.assertTrue(scope["checklist"], "the checklist is the open set this run decides on")
            view = records_view.read(client, workspace, scope["document"])
            waivers = [g for _, g in grants["waivers"]]
            self.assertTrue(waivers, "the case carries the waiver this joins")
            slices = result_mod.waiver_slices(view.entries, waivers)
            self.assertEqual(slices, {"A"}, slices)
        finally:
            for name, original in saved.items():
                setattr(ledger_mod, name, original)

    def test_the_helpers_are_still_there_for_the_copy(self):
        """A guard on the guard: if they ever go again, the component's copy test breaks, so this
        says out loud why they stay."""
        from recheck_core import ledger as ledger_mod
        for name in RESTORED_FOR_THE_COPY:
            self.assertTrue(callable(getattr(ledger_mod, name, None)),
                            "%s is part of the byte-for-byte region records copies (E12-2)" % name)

    def setUp(self):
        self.dir = testlib.make_scratch("e13-copy-helpers-")
        self.addCleanup(testlib.rmtree, self.dir)


if __name__ == "__main__":
    unittest.main()
