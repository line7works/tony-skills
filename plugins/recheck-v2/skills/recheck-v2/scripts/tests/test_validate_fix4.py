"""recheck_core.validate after Astra's review, fix agent 3: the semantic checks E8-A19 and E8-A31 (V3), E8-A21
(V8), E8-A24 (V7, V14), E8-A25 (V17), E8-A26 and E8-A40 (V13), E8-A33 (V18), and E8-A44 (V12). Expectations are
the amendment block of docs/plans/2026-09-13-recheck-v2-e8-core.md section 12 and pilot-contract.md sections 8,
9, and 11; the run directories are built here from the example documents, never from the answer key."""
import copy
import json
import os
import shutil
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import checkpoint as cpmod, ledger, receipt as rcmod, validate  # noqa: E402

DOC = "docs/plans/2026-09-18-widget-export.md"
SHA_EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def example(name):
    return testlib.load_json(os.path.join(testlib.EX, name))


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def touch(path, text=""):
    write_text(path, text)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = validate.load_schemas()

    def setUp(self):
        self.dir = testlib.make_scratch("e8-fix4-validate-")

    def tearDown(self):
        testlib.rmtree(self.dir)

    def run_checks(self, doc, **kw):
        return validate.run_semantic(doc, schemas=self.schemas, **kw)

    def findings(self, doc, check_id, **kw):
        return [f for f in self.run_checks(doc, **kw)["semantic"] if f["id"] == check_id]

    def paths(self, doc, check_id, **kw):
        return [f["path"] for f in self.findings(doc, check_id, **kw)]

    def messages(self, doc, check_id, **kw):
        return " | ".join(f["message"] for f in self.findings(doc, check_id, **kw))

    def skips(self, doc, **kw):
        return {s["id"]: s["reason"] for s in self.run_checks(doc, **kw)["skipped"]}

    def relocated(self, name, run_dir, create=True):
        """The example result with its run directory moved to run_dir; every listed run artifact created."""
        doc = example(name)
        old = doc["run"]["run_dir"]
        doc["run"]["run_dir"] = run_dir

        def move(value):
            return run_dir + value[len(old):] if isinstance(value, str) and value.startswith(old) else value
        for w in doc["records_written"]:
            w["path"] = move(w["path"])
            if create and w["kind"] == "run_artifact":
                touch(w["path"], w["path"])
        if "receipt_path" in doc:
            doc["receipt_path"] = move(doc["receipt_path"])
        ver = doc["run"].get("verifier") or {}
        if ver.get("raw_path"):
            ver["raw_path"] = move(ver["raw_path"])
        for c in ver.get("calls") or []:
            if c.get("raw_path"):
                c["raw_path"] = move(c["raw_path"])
        for it in doc.get("items") or []:
            for e in it["verification"]["evidence"]:
                if e.get("artifact_path"):
                    e["artifact_path"] = move(e["artifact_path"])
        return doc


class V3Containment(Base):
    """E8-A19: with the workspace, a project-record path must resolve inside the workspace's real path."""

    def test_symlinked_record_outside_the_workspace(self):
        ws = os.path.join(self.dir, "ws")
        outside = os.path.join(self.dir, "outside", "plan.md")
        touch(outside, "# elsewhere\n")
        doc = example("result-completed.json")
        block = next(i for i, w in enumerate(doc["records_written"]) if w["kind"] == "punch_list_block")
        os.makedirs(os.path.join(ws, "docs", "plans"))
        os.symlink(outside, os.path.join(ws, DOC))
        touch(os.path.join(ws, "docs", "reviews", "2026-09-19-signoff-widget-export-a.md"), "# verdict\n")
        found = [f for f in self.findings(doc, "V3", workspace=ws) if f["path"] == "/records_written/%d/path" % block]
        self.assertEqual(len(found), 1, self.messages(doc, "V3", workspace=ws))
        self.assertIn("resolves outside the workspace", found[0]["message"])
        # the same path as a regular file inside the workspace: no containment finding
        os.remove(os.path.join(ws, DOC))
        touch(os.path.join(ws, DOC), "# plan\n")
        self.assertEqual([f for f in self.findings(doc, "V3", workspace=ws) if "outside" in f["message"]], [])
        # a symlink that stays inside the workspace is contained
        os.remove(os.path.join(ws, DOC))
        touch(os.path.join(ws, "docs", "plans", "real.md"), "# plan\n")
        os.symlink(os.path.join(ws, "docs", "plans", "real.md"), os.path.join(ws, DOC))
        self.assertEqual([f for f in self.findings(doc, "V3", workspace=ws) if "/records_written/%d/path" % block in f["path"]], [])

    def test_workspace_itself_through_a_symlink(self):
        """The workspace path may be a symlink: containment compares real paths on both sides."""
        real = os.path.join(self.dir, "real-ws")
        link = os.path.join(self.dir, "ws-link")
        touch(os.path.join(real, DOC), "# plan\n")
        touch(os.path.join(real, "docs", "reviews", "2026-09-19-signoff-widget-export-a.md"), "# verdict\n")
        os.symlink(real, link)
        doc = example("result-completed.json")
        self.assertEqual([f for f in self.findings(doc, "V3", workspace=link) if "outside" in f["message"] or "does not exist" in f["message"]], [])


class V3Inventory(Base):
    """E8-A31: with the run directory supplied, every regular file under it appears in the write list exactly
    once, and every listed run artifact exists."""

    def test_every_file_once(self):
        run_dir = os.path.join(self.dir, "run")
        doc = self.relocated("result-completed.json", run_dir)
        self.assertEqual(self.paths(doc, "V3", run_dir=run_dir), [], self.messages(doc, "V3", run_dir=run_dir))
        # a file present but unlisted (a redirected output no evidence entry named)
        touch(os.path.join(run_dir, "verifier", "extra-command.log"), "x\n")
        found = self.findings(doc, "V3", run_dir=run_dir)
        self.assertEqual(len(found), 1, found)
        self.assertIn("verifier/extra-command.log", found[0]["message"]); self.assertIn("not in the write list", found[0]["message"])
        # nested under a subdirectory too
        touch(os.path.join(run_dir, "verifier", "nested", "deep.log"), "x\n")
        self.assertEqual(len(self.findings(doc, "V3", run_dir=run_dir)), 2)

    def test_listed_twice_and_listed_but_missing(self):
        run_dir = os.path.join(self.dir, "run")
        doc = self.relocated("result-completed.json", run_dir)
        dup = copy.deepcopy(doc)
        dup["records_written"].insert(5, dict(dup["records_written"][4]))
        found = self.findings(dup, "V3", run_dir=run_dir)
        self.assertEqual([f["path"] for f in found], ["/records_written/5"], found)
        self.assertIn("listed twice", found[0]["message"])
        missing = copy.deepcopy(doc)
        os.remove(missing["records_written"][5]["path"])
        found = self.findings(missing, "V3", run_dir=run_dir)
        self.assertEqual([f["path"] for f in found], ["/records_written/5/path"], found)
        self.assertIn("does not exist under run_dir", found[0]["message"])

    def test_inventory_needs_the_supplied_run_dir_and_a_write_list(self):
        run_dir = os.path.join(self.dir, "run")
        doc = self.relocated("result-completed.json", run_dir)
        touch(os.path.join(run_dir, "verifier", "extra-command.log"), "x\n")
        self.assertEqual(self.paths(doc, "V3"), [], "without --run-dir the inventory does not run (the result's own run_dir only locates artifacts)")
        # a refused resume's envelope lists nothing (E8-A42) beside its untouched run directory: no inventory finding
        envelope = {"protocol_version": 1, "run": example("result-completed-blocked.json")["run"], "status": "stopped",
                    "stop_reason": "resume refused at section 11 step 1: checkpoint.json does not exist", "records_written": []}
        envelope["run"]["run_dir"] = run_dir
        self.assertEqual(validate.validate_result(envelope, self.schemas), [])
        self.assertEqual(self.paths(envelope, "V3", run_dir=run_dir), [])


class V8Receipt(Base):
    """E8-A21: the receipt proves the state (entries in order, intent before done, one done per step, observed
    equals the planned after-hash) and, with the workspace, every fully-done target rests at its final hash."""

    def plan(self):
        content = "\n### 2026-09-24 — recheck: Slice A\n- MAJOR · src/export.ts:142 · (x) · fixed · executed\n"
        after1 = rcmod.sha(content)
        return [{"step": 1, "kind": "punch_list_block", "target": DOC, "before_sha256": SHA_EMPTY, "after_sha256": after1, "content": content,
                 "heading": "### 2026-09-24 — recheck: Slice A"},
                {"step": 2, "kind": "status_line", "target": DOC, "before_sha256": after1, "after_sha256": rcmod.sha(content + "Status: signed off\n"), "value": "signed off"}]

    def make(self, entries, phase="recording"):
        """A real receipt chain in a fresh run directory (Receipt.new then one write per entry)."""
        run_dir = os.path.join(self.dir, "run-%d" % len(os.listdir(self.dir)))
        os.makedirs(run_dir)
        plan = self.plan()
        rc = rcmod.Receipt.new(run_dir, "recheck-a-20260924-5f5f", plan, self.schemas)
        for step, kind, observed in entries:
            rc.entry(step, kind, observed)
        if phase != "recording":
            rc.doc["phase"] = phase
            rc.save()
        return run_dir, plan

    def result(self, plan, landed, status="recording_failed", stop_reason=None):
        doc = example("result-recording-failed.json")
        doc["records_written"] = [w for w in doc["records_written"] if w["kind"] == "run_artifact"]
        tail = doc["records_written"].pop()
        for s in plan[:landed]:
            doc["records_written"].append({"kind": s["kind"], "path": s["target"], "appended": s["kind"] != "status_line",
                                           "sha256_before": s["before_sha256"], "sha256_after": s["after_sha256"]})
        doc["records_written"].append(tail)
        doc["status"] = status
        if status == "completed":
            doc.update({"result": "all_clear", "cards": [{"slice": "A", "before": "rejected", "after": "signed off"}], "boundary_violations": [],
                        "rejected_grants": [], "still_open": []})
            doc["source_identity"]["after_run"] = doc["source_identity"]["at_transaction"]
            doc.pop("stop_reason", None)
        if stop_reason:
            doc["stop_reason"] = stop_reason
        return doc

    def test_a_sound_receipt_is_clean(self):
        plan = self.plan()
        run_dir, _ = self.make([(1, "intent", None), (1, "done", plan[0]["after_sha256"]), (2, "intent", None)])
        doc = self.result(plan, 1)
        self.assertEqual(self.paths(doc, "V8", run_dir=run_dir), [], self.messages(doc, "V8", run_dir=run_dir))

    def test_plan_without_entries_is_accepted(self):
        """A containment failure at plan time (E8-A19) leaves a receipt with the plan and no entry."""
        plan = self.plan()
        run_dir, _ = self.make([])
        doc = self.result(plan, 0, stop_reason="step 1 target %s resolves outside the workspace; no write" % DOC)
        self.assertEqual(self.paths(doc, "V8", run_dir=run_dir), [], self.messages(doc, "V8", run_dir=run_dir))

    def test_entry_rules(self):
        plan = self.plan()
        cases = [
            ("precedes the step's intent", [(1, "done", plan[0]["after_sha256"])]),
            ("repeats the step's done entry", [(1, "intent", None), (1, "done", plan[0]["after_sha256"]), (1, "done", plan[0]["after_sha256"])]),
            ("out of sequence", [(2, "intent", None), (1, "intent", None)]),
            ("observed", [(1, "intent", None), (1, "done", "f" * 64)]),
            ("names no plan step", [(3, "intent", None)]),
        ]
        for needle, entries in cases:
            run_dir, _ = self.make(entries)
            doc = self.result(plan, 0)
            found = [f for f in self.findings(doc, "V8", run_dir=run_dir) if "E8-A21" in f["message"]]
            self.assertEqual(len(found), 1, (needle, self.messages(doc, "V8", run_dir=run_dir)))
            self.assertIn(needle, found[0]["message"], needle)
            self.assertIn("entry", found[0]["message"], "the finding names the entry")

    def test_resting_hash_with_the_workspace(self):
        plan = self.plan()
        run_dir, _ = self.make([(1, "intent", None), (1, "done", plan[0]["after_sha256"]), (2, "intent", None), (2, "done", plan[1]["after_sha256"])], phase="committed")
        ws = os.path.join(self.dir, "ws")
        write_text(os.path.join(ws, DOC), plan[0]["content"] + "Status: signed off\n")
        doc = self.result(plan, 2, status="completed")
        self.assertEqual(self.paths(doc, "V8", run_dir=run_dir, workspace=ws), [], self.messages(doc, "V8", run_dir=run_dir, workspace=ws))
        write_text(os.path.join(ws, DOC), plan[0]["content"] + "Status: signed off\nedited outside\n")
        found = self.findings(doc, "V8", run_dir=run_dir, workspace=ws)
        self.assertEqual(len(found), 1, found)
        self.assertIn(DOC, found[0]["message"]); self.assertIn("rests at", found[0]["message"])
        self.assertEqual(self.paths(doc, "V8", run_dir=run_dir), [], "without the workspace the resting check does not run")
        # a recording_failed result that reports the outside edit is exempt for the target it names
        reported = self.result(plan, 2, stop_reason="step 2 (status_line, %s) landed but the target now rests at abcdef012345, not the step's after hash %s (an outside edit after the step; needs the user's word)" % (DOC, plan[1]["after_sha256"][:12]))
        self.assertEqual(self.paths(reported, "V8", run_dir=run_dir, workspace=ws), [], self.messages(reported, "V8", run_dir=run_dir, workspace=ws))
        other = self.result(plan, 2, stop_reason="step 2 (status_line, docs/other.md) landed but the target now rests at abcdef012345, not the step's after hash 000 (an outside edit after the step; needs the user's word)")
        self.assertEqual(len(self.findings(other, "V8", run_dir=run_dir, workspace=ws)), 1, "the exemption covers only the named target")


class V7V14Grants(Base):
    """E8-A24: the validator recomputes each grant's channel verdict with the core's own rule; the result's
    rejected_grants is never the proof."""

    TURN = "codex:thread 01a0a1b2:turn 9"

    def s2_01_shape(self):
        """The S2-01 shape on the examples: the open MAJOR waived by the input's forwarded waiver, all_clear,
        the card signed off, the waiver line written."""
        result = example("result-completed.json")
        inp = example("input-caller.json")
        item = result["items"][1]
        mark = {"date": "2026-09-20", "quoted_words": "waive the undefined-title one, ship it", "turn_ref": self.TURN}
        item["waived"] = mark
        result.update({"result": "all_clear", "still_open": []})
        result["cards"][0].update({"after": "signed off", "reason": "BLOCKER cleared; the MAJOR waived per user"})
        inp["authorization"]["waivers"][0].update({"item": {"location": dict(item["location"]), "claim": item["claim"]}, "turn_ref": self.TURN,
                                                   "quoted_words": mark["quoted_words"], "date": mark["date"], "severity": "MAJOR"})
        self.assertEqual(validate.validate_result(result, self.schemas), [])
        self.assertEqual(validate.validate_input(inp, self.schemas), [])
        return result, inp

    def test_attribution_decides(self):
        result, inp = self.s2_01_shape()
        self.assertEqual(self.paths(result, "V7", input_doc=inp), []); self.assertEqual(self.paths(result, "V14", input_doc=inp), [])
        user = copy.deepcopy(inp); user["invocation"]["turn_attribution"] = {self.TURN: "user"}
        self.assertEqual(self.paths(result, "V7", input_doc=user), []); self.assertEqual(self.paths(result, "V14", input_doc=user), [])
        assistant = copy.deepcopy(inp); assistant["invocation"]["turn_attribution"] = {self.TURN: "assistant"}
        v7 = self.findings(result, "V7", input_doc=assistant)
        self.assertTrue(any(f["path"] == "/items/1/waived" and "channel rule rejects" in f["message"] and "authorization.waivers[0]" in f["message"] for f in v7), v7)
        self.assertTrue(any(f["path"] == "/records_written" and "1 waived_line writes for 0 accepted waivers" in f["message"] for f in v7), v7)
        v14 = self.findings(result, "V14", input_doc=assistant)
        self.assertEqual([f["path"] for f in v14], ["/authorization/waivers/0"], v14)
        self.assertIn("does not list it under authorization.waivers[0]", v14[0]["message"])
        # the result listing the grant does not rescue the marker or the line: the rejection must have written nothing
        listed = copy.deepcopy(result)
        listed["rejected_grants"] = ["authorization.waivers[0]: src/export.ts:142 · turn_ref %r maps to assistant (the adapter's turn_attribution); not a grant; not written" % self.TURN]
        self.assertEqual(self.paths(listed, "V14", input_doc=assistant), [])
        self.assertTrue(any("channel rule rejects" in f["message"] for f in self.findings(listed, "V7", input_doc=assistant)))

    def test_route_rules_and_other_reasons(self):
        result, inp = self.s2_01_shape()
        # the station route needs forwarded_by (E7-13)
        bare = copy.deepcopy(inp); bare["authorization"]["waivers"][0].pop("forwarded_by")
        self.assertTrue(any("forwarded_by" in f["message"] for f in self.findings(result, "V7", input_doc=bare)))
        self.assertEqual(self.paths(result, "V14", input_doc=bare), ["/authorization/waivers/0"])
        # a grant the rule accepts, listed as rejected for no other reason: the result's own list is not the proof
        wrongly = copy.deepcopy(result)
        wrongly["rejected_grants"] = ["authorization.waivers[0]: src/export.ts:142 · turn_ref maps to assistant; not written"]
        v14 = self.findings(wrongly, "V14", input_doc=inp)
        self.assertEqual([f["path"] for f in v14], ["/authorization/waivers/0"], v14)
        self.assertIn("for no other reason", v14[0]["message"])
        # listed for another reason (it matched no entry): V14 accepts the entry, and V7 then holds the marker and the line to it
        other = copy.deepcopy(result)
        other["rejected_grants"] = ["authorization.waivers[0]: src/export.ts:142 · names no entry in the record (x); nothing to waive; not written"]
        self.assertEqual(self.paths(other, "V14", input_doc=inp), [])
        self.assertTrue(any(f["path"] == "/items/1/waived" for f in self.findings(other, "V7", input_doc=inp)))

    def test_extra_continuation(self):
        result, inp = self.s2_01_shape()
        turn = "codex:thread 01a0a1b2:turn 12"
        inp["authorization"]["extra_continuation"] = {"by": "user", "channel": "user-turn", "turn_ref": turn, "quoted_words": "one more round", "date": "2026-09-20", "forwarded_by": "ship-v2"}
        self.assertEqual(self.paths(result, "V14", input_doc=inp), [])
        # E9-1: a supplied map is the session's turn list, so the waiver's own turn is listed as the user's
        inp["invocation"]["turn_attribution"] = {turn: "station", self.TURN: "user"}
        v14 = self.findings(result, "V14", input_doc=inp)
        self.assertEqual([f["path"] for f in v14], ["/authorization/extra_continuation"], v14)
        listed = copy.deepcopy(result)
        listed["rejected_grants"] = ["authorization.extra_continuation: None:None · turn_ref maps to station; not a grant"]
        self.assertEqual(self.paths(listed, "V14", input_doc=inp), [])
        used = copy.deepcopy(result)
        used["rejected_grants"] = ["authorization.extra_continuation: None:None · already used for continuation 1"]
        inp["invocation"].pop("turn_attribution")
        self.assertEqual(self.paths(used, "V14", input_doc=inp), [], "a used continuation grant is listed for another reason (E8-A23)")


class V17DefectSlice(Base):
    """E8-A25: the written defect line's slice (the fourth field under a multi-slice heading, the heading's
    slice otherwise) equals charged_to_slice."""

    def build(self, slices, charged):
        ws, run_dir = os.path.join(self.dir, "ws"), os.path.join(self.dir, "run")
        os.makedirs(run_dir)
        result = example("result-completed.json")
        items = result["items"]
        lines = [ledger.render_recheck_line(it["severity"], it["location"]["file"], it["location"]["line"], it["claim"], "fixed" if it["disposition"] == "fixed" else "not fixed", "executed it")
                 for it in items]
        defect = {"severity": "MAJOR", "severity_basis": "default table", "location": {"file": "src/export.ts", "line": 150},
                  "claim": "quoted commas now double their quotes", "failure_scenario": "export a title with a comma",
                  "source": "fix_introduced", "charged_to_slice": charged}
        lines.append(ledger.render_defect_line("MAJOR", "src/export.ts", 150, defect["claim"], defect["failure_scenario"],
                                               ledger.defect_slice_field(slices, "B" if len(slices) > 1 else slices[0])))
        text = "# plan\n\n## Slice A — export\nStatus: rejected\n\n## Slice B — validation\nStatus: rejected\n\n## Punch list\n\n### 2026-09-19 — review: Slice A\n"
        text += "- BLOCKER · src/export.ts:142 · %s · %s · A\n- MAJOR · src/export.ts:142 · %s · %s · A\n" % (items[0]["claim"], items[0]["failure_scenario"], items[1]["claim"], items[1]["failure_scenario"])
        text += ledger.render_block("2026-09-20", slices, lines)
        write_text(os.path.join(ws, DOC), text)
        result["new_defects"] = [defect]
        result["still_open"].append("MAJOR · src/export.ts:150 · broke: %s" % defect["claim"])
        result["records_written"] = [w for w in result["records_written"] if w["kind"] in ("run_artifact", "punch_list_block")]
        return result, ws, run_dir

    def test_multi_slice_heading(self):
        result, ws, run_dir = self.build(["A", "B"], "B")
        self.assertEqual(self.paths(result, "V17", run_dir=run_dir, workspace=ws), [], self.messages(result, "V17", run_dir=run_dir, workspace=ws))
        result["new_defects"][0]["charged_to_slice"] = "A"
        found = self.findings(result, "V17", run_dir=run_dir, workspace=ws)
        self.assertEqual([f["path"] for f in found], ["/new_defects/0/charged_to_slice"], found)
        self.assertIn("charges 'B'", found[0]["message"])

    def test_single_slice_heading(self):
        result, ws, run_dir = self.build(["A"], "A")
        self.assertEqual(self.paths(result, "V17", run_dir=run_dir, workspace=ws), [], self.messages(result, "V17", run_dir=run_dir, workspace=ws))
        result["new_defects"][0]["charged_to_slice"] = "B"
        self.assertEqual(self.paths(result, "V17", run_dir=run_dir, workspace=ws), ["/new_defects/0/charged_to_slice"])


class V13RetainedReports(Base):
    """E8-A26, E8-A40: every complete call record (complete and ok alike) must have its report at raw_path,
    hashing to raw_sha256, with a parseable tail; the legacy skip applies only without raw_sha256."""

    def setUp(self):
        Base.setUp(self)
        self.run_dir = os.path.join(self.dir, "run")
        self.result = self.relocated("result-completed.json", self.run_dir)
        self.cp = example("checkpoint-partial.json")
        self.cp["run_id"] = self.result["run"]["run_id"]
        self.raw = os.path.join(self.run_dir, "verifier", "raw.md")
        self.report = testlib.canned_report([
            {"index": 0, "location": "src/export.ts:142", "disposition": "fixed", "location_after_fix": "src/export.ts:151"},
            {"index": 1, "location": "src/export.ts:142", "disposition": "not_fixed", "reason": "missed_case", "missed_case": "an absent title key"}])

    def call(self, status="complete", sha=True, items=(0, 1)):
        c = {"call_id": self.result["run"]["run_id"] + "-verify", "status": status, "items": list(items), "raw_path": self.raw}
        if sha:
            from recheck_core import canon
            c["raw_sha256"] = canon.sha256_file(self.raw) if os.path.isfile(self.raw) else "0" * 64
        self.cp["verifier_calls"] = [c]
        write_json(os.path.join(self.run_dir, "checkpoint.json"), self.cp)

    def test_missing_file_hash_mismatch_and_missing_tail_are_findings(self):
        os.remove(self.raw)
        self.call()
        found = self.findings(self.result, "V13", run_dir=self.run_dir)
        self.assertTrue(any("does not exist" in f["message"] and f["path"] == "/run/verifier/calls/0/raw_path" for f in found), found)
        self.assertNotIn("V13", self.skips(self.result, run_dir=self.run_dir))
        write_text(self.raw, self.report)
        self.call()
        write_text(self.raw, self.report + "\nedited after the record\n")
        found = self.findings(self.result, "V13", run_dir=self.run_dir)
        self.assertTrue(any("does not hash" in f["message"] for f in found), found)
        write_text(self.raw, "prose only, no block\n")
        self.call()
        found = self.findings(self.result, "V13", run_dir=self.run_dir)
        self.assertTrue(any("no usable tail" in f["message"] for f in found), found)
        self.assertNotIn("V13", self.skips(self.result, run_dir=self.run_dir), "a missing tail is a finding, never a skip, when raw_sha256 is recorded")

    def test_matching_tail_is_clean_under_both_spellings(self):
        write_text(self.raw, self.report)
        for status in ("complete", "ok"):
            self.call(status)
            self.assertEqual(self.paths(self.result, "V13", run_dir=self.run_dir), [], (status, self.messages(self.result, "V13", run_dir=self.run_dir)))
        wrong = copy.deepcopy(self.result)
        wrong["items"][1]["adjudication"]["verifier_said"] = "fixed"
        wrong["items"][1]["adjudication"]["driver_action"] = "downgraded"
        self.assertEqual(self.paths(wrong, "V13", run_dir=self.run_dir), ["/items/1/adjudication/verifier_said"])
        self.call("transport-failed")
        found = self.findings(self.result, "V13", run_dir=self.run_dir)
        self.assertTrue(all("no retained report's tail covers" in f["message"] for f in found) and found, "a failed call proves nothing")

    def test_legacy_skip_only_without_raw_sha256(self):
        write_text(self.raw, "prose only, no block\n")
        self.call(sha=False)
        self.assertEqual(self.paths(self.result, "V13", run_dir=self.run_dir), [])
        self.assertEqual(self.skips(self.result, run_dir=self.run_dir).get("V13"), validate.NO_TAIL_SKIP)


class V18RefusedResume(Base):
    """E8-A33: a stopped result refused at section 11 step N is held to a checkpoint that fails at N."""

    def envelope(self, step, reason="corrupt"):
        """The shape stopped_envelope_without_run_dir delivers: the run block from the presented input (no verifier
        block, no session), the reason, an empty write list."""
        run = example("result-completed-blocked.json")["run"]
        run.pop("verifier", None); run.pop("session_wrote_fix", None)
        run["run_dir"] = os.path.join(self.dir, "run")
        return {"protocol_version": 1, "run": run, "status": "stopped",
                "stop_reason": "resume refused at section 11 step %d: %s" % (step, reason), "records_written": []}

    def seed(self, run_dir, corrupt=False):
        cp = example("checkpoint-partial.json")
        if corrupt:
            cp["items"][1]["retries"] = 1  # the C4-01 shape: one field edited after signing, the log untouched
        write_json(os.path.join(run_dir, "checkpoint.json"), cp)
        shutil.copy(os.path.join(testlib.EX, "checkpoint-partial.log"), os.path.join(run_dir, "checkpoint.log"))

    def test_c4_01_shape_validates_and_an_intact_checkpoint_is_the_finding(self):
        run_dir = os.path.join(self.dir, "run")
        self.seed(run_dir, corrupt=True)
        env = self.envelope(2, "self digest does not recompute")
        self.assertEqual(validate.validate_result(env, self.schemas), [])
        out = self.run_checks(env, run_dir=run_dir)
        self.assertEqual(out["semantic"], [], out)
        self.seed(run_dir, corrupt=False)
        found = self.findings(env, "V18", run_dir=run_dir)
        self.assertEqual([f["path"] for f in found], ["/stop_reason"], found)
        self.assertIn("the checkpoint verifies", found[0]["message"])

    def test_steps_1_and_3(self):
        run_dir = os.path.join(self.dir, "run")
        os.makedirs(run_dir)
        self.assertEqual(self.paths(self.envelope(1, "checkpoint.json does not exist"), "V18", run_dir=run_dir), [])
        self.seed(run_dir)
        self.assertEqual(self.paths(self.envelope(1), "V18", run_dir=run_dir), ["/stop_reason"])
        self.assertEqual(self.paths(self.envelope(2), "V18", run_dir=run_dir), ["/stop_reason"], "an intact checkpoint refused at step 2")
        other = self.envelope(3, "the checkpoint's run id is not the invocation's")
        other["run"]["run_id"] = "another-run"
        self.assertEqual(self.paths(other, "V18", run_dir=run_dir), [])
        same = self.envelope(3, "the binding hash differs")
        self.assertEqual(self.paths(same, "V18", run_dir=run_dir), ["/stop_reason"], "the run id is the checkpoint's and no input was supplied")
        inp = example("input-direct.json")
        self.assertEqual(self.paths(same, "V18", run_dir=run_dir, input_doc=inp), [], "with the input, the binding hash differs from the checkpoint's input_sha256")

    def test_a_refusal_carries_nothing_graded(self):
        run_dir = os.path.join(self.dir, "run")
        self.seed(run_dir, corrupt=True)
        env = self.envelope(2)
        env["records_written"] = [{"kind": "punch_list_block", "path": DOC, "appended": True}]
        self.assertIn("/records_written/0", self.paths(env, "V18", run_dir=run_dir))

    def seed_signed(self, run_dir, mutate):
        """The example checkpoint with `mutate` applied, re-signed, and its log's last line rewritten to match, so
        that the checkpoint verifies (the precondition is asserted)."""
        cp = example("checkpoint-partial.json")
        mutate(cp)
        cp["integrity"]["self"] = cpmod.self_hash(cp)
        write_json(os.path.join(run_dir, "checkpoint.json"), cp)
        rows = testlib.read_text(os.path.join(testlib.EX, "checkpoint-partial.log")).splitlines()
        rows[-1] = "%d %s" % (cp["integrity"]["seq"], cp["integrity"]["self"])
        write_text(os.path.join(run_dir, "checkpoint.log"), "\n".join(rows) + "\n")
        v = cpmod.read_and_verify(run_dir, self.schemas)
        self.assertTrue(v["ok"], v)
        return cp

    def test_step_1_run_ended(self):
        """E8-A49: `the run ended as <status>: ...; start a new run` (cmd_resume, section 11 step 1, E8-A20) needs the
        checkpoint verified at phase stopped, terminal.resumable false, and terminal.status the named status."""
        run_dir = os.path.join(self.dir, "run")

        def ended(cp):
            cp["phase"] = "stopped"
            cp["terminal"] = {"status": "stale_source", "stop_reason": "HEAD is 1111111, the run started at 7a1b2c3", "resumable": False}
        self.seed_signed(run_dir, ended)
        env = self.envelope(1, "the run ended as stale_source: HEAD is 1111111, the run started at 7a1b2c3; start a new run")
        self.assertEqual(validate.validate_result(env, self.schemas), [])
        self.assertEqual(self.paths(env, "V18", run_dir=run_dir), [], self.messages(env, "V18", run_dir=run_dir))
        # negative control: the same reason beside a checkpoint still verifying
        self.seed_signed(run_dir, lambda cp: cp.__setitem__("phase", "verifying"))
        found = self.findings(env, "V18", run_dir=run_dir)
        self.assertEqual([f["path"] for f in found], ["/stop_reason"], found)
        self.assertIn("phase is verifying", found[0]["message"])
        # a resumable terminal (section 10's bounded recovery) is not an ended run
        self.seed_signed(run_dir, lambda cp: (ended(cp), cp["terminal"].__setitem__("resumable", True)))
        self.assertIn("says resumable", self.messages(env, "V18", run_dir=run_dir))
        # another terminal status than the one named
        self.seed_signed(run_dir, lambda cp: (ended(cp), cp["terminal"].__setitem__("status", "verifier_unavailable")))
        self.assertIn("terminal status is verifier_unavailable", self.messages(env, "V18", run_dir=run_dir))
        # a step 1 refusal with another reason keeps E8-A33: the checkpoint must fail at step 1
        self.seed_signed(run_dir, ended)
        self.assertEqual(self.paths(self.envelope(1, "checkpoint.log does not exist"), "V18", run_dir=run_dir), ["/stop_reason"])

    def test_step_6_reused_grant(self):
        """E8-A49: `extra_continuation: turn_ref '<ref>' already used for continuation <n>` (cmd_resume, E8-A23) needs
        <ref> in the checkpoint's continuation_grants_used; no workspace is needed for this reason."""
        run_dir = os.path.join(self.dir, "run")
        ref = "codex:thread 01a0a1b2:turn 9"
        reason = "continuation limit exceeded: this would be continuation 3 and extra_continuation: turn_ref '%s' already used for continuation 2; state stays on disk" % ref
        self.seed_signed(run_dir, lambda cp: (cp.__setitem__("continuations", 1), cp.__setitem__("continuation_grants_used", [ref])))
        env = self.envelope(6, reason)
        self.assertEqual(validate.validate_result(env, self.schemas), [])
        out = self.run_checks(env, run_dir=run_dir)
        self.assertEqual([f for f in out["semantic"] if f["id"] == "V18"], [], out["semantic"])
        self.assertNotIn("V18", {s["id"] for s in out["skipped"]}, "the reused-grant condition needs no workspace")
        # negative control: the same reason beside a checkpoint whose used list lacks the ref
        self.seed_signed(run_dir, lambda cp: (cp.__setitem__("continuations", 1), cp.__setitem__("continuation_grants_used", ["codex:thread 01a0a1b2:turn 4"])))
        found = self.findings(env, "V18", run_dir=run_dir)
        self.assertEqual([f["path"] for f in found], ["/stop_reason"], found)
        self.assertIn(ref, found[0]["message"])
        self.seed_signed(run_dir, lambda cp: cp.__setitem__("continuations", 1))  # no used list at all
        self.assertEqual(self.paths(env, "V18", run_dir=run_dir), ["/stop_reason"])
        # a step 6 refusal with another reason keeps E8-A33: the identity check, which needs the workspace
        other = self.envelope(6, "continuation limit exceeded: this would be continuation 3 and no extra_continuation grant is presented; state stays on disk")
        self.assertIn("workspace", self.skips(other, run_dir=run_dir).get("V18", ""))


class V12MovedBefore(Base):
    """E8-A44: a card may be listed as moved beside a boundary violation only when its status-line step is
    receipted done with a step number below boundary.json's before_step and the reason is the core's."""

    def setUp(self):
        Base.setUp(self)
        self.run_dir = os.path.join(self.dir, "run")
        os.makedirs(self.run_dir)
        block = "\n### 2026-09-21 — recheck: Slice A, Slice B\n- BLOCKER · src/a.py:1 · (x) · fixed · executed\n"
        h1 = rcmod.sha(block); h2 = rcmod.sha(block + "A"); h3 = rcmod.sha(block + "AB")
        self.plan = [{"step": 1, "kind": "punch_list_block", "target": DOC, "before_sha256": SHA_EMPTY, "after_sha256": h1, "content": block, "heading": "### 2026-09-21 — recheck: Slice A, Slice B"},
                     {"step": 2, "kind": "status_line", "target": DOC, "before_sha256": h1, "after_sha256": h2, "value": "signed off"},
                     {"step": 3, "kind": "status_line", "target": DOC, "before_sha256": h2, "after_sha256": h3, "value": "signed off", "cancelled": True}]
        self.entries = [(1, "intent", None), (1, "done", h1), (2, "intent", None), (2, "done", h2), (3, "intent", None)]
        self.result = example("result-completed.json")
        self.result.update({"boundary_violations": ["README.md changed between A's status line and B's"], "result": "not_clear",
                            "cards": [{"slice": "A", "before": "rejected", "after": "signed off", "reason": validate.MOVED_BEFORE_VIOLATION},
                                      {"slice": "B", "before": "rejected", "after": "rejected", "reason": "a boundary violation froze the card"}]})
        self.assertEqual(validate.validate_result(self.result, self.schemas), [])

    def write(self, plan=None, entries=None, before_step=3):
        rc = rcmod.Receipt.new(self.run_dir, self.result["run"]["run_id"], plan or self.plan, self.schemas)
        for step, kind, observed in (entries if entries is not None else self.entries):
            rc.entry(step, kind, observed)
        if before_step is not None:
            rcmod.write_boundary(self.run_dir, self.result["boundary_violations"], before_step)
        elif os.path.exists(rcmod.boundary_path(self.run_dir)):
            os.remove(rcmod.boundary_path(self.run_dir))

    def test_the_w2_03_shape_is_clean(self):
        self.write()
        self.assertEqual(self.paths(self.result, "V12"), [], "result-only part")
        self.assertEqual(self.paths(self.result, "V12", run_dir=self.run_dir), [], self.messages(self.result, "V12", run_dir=self.run_dir))

    def test_any_other_moved_card_is_a_finding(self):
        self.write()
        other = copy.deepcopy(self.result); other["cards"][0]["reason"] = "BLOCKER cleared"
        paths = self.paths(other, "V12")
        self.assertIn("/cards/0", paths)
        self.assertTrue(any(p.startswith("/records_written/") for p in paths), "with no moved-before card the status line has nothing to stand for")
        promoted = copy.deepcopy(self.result); promoted["result"] = "partial"
        self.assertIn("/result", self.paths(promoted, "V12"))
        two = copy.deepcopy(self.result)
        two["records_written"].insert(-1, {"kind": "status_line", "path": DOC, "appended": False})
        self.assertEqual(len([p for p in self.paths(two, "V12") if p.startswith("/records_written/")]), 1, "one status line stands for the moved-before card; the second has no card")

    def test_before_step_and_the_done_entry_decide(self):
        self.write(before_step=2)
        found = self.findings(self.result, "V12", run_dir=self.run_dir)
        self.assertTrue(any(f["path"] == "/cards/0" and "not below" in f["message"] for f in found), found)
        self.write(entries=[(1, "intent", None), (1, "done", self.plan[0]["after_sha256"]), (2, "intent", None), (3, "intent", None)])
        found = self.findings(self.result, "V12", run_dir=self.run_dir)
        self.assertTrue(any(f["path"] == "/cards/0" and "not receipted done" in f["message"] for f in found), found)
        self.write(before_step=None)
        found = self.findings(self.result, "V12", run_dir=self.run_dir)
        self.assertTrue(any(f["path"] == "/cards/0" for f in found), "without boundary.json no card may be listed as moved")
        live = [dict(s) for s in self.plan]; live[2].pop("cancelled")
        self.write(plan=live)
        found = self.findings(self.result, "V12", run_dir=self.run_dir)
        self.assertTrue(any("step 3 is not cancelled" in f["message"] for f in found), found)
        frozen = copy.deepcopy(self.result)
        frozen["cards"][0].update({"after": "rejected", "reason": "frozen"})
        frozen["records_written"] = [w for w in frozen["records_written"] if w["kind"] != "status_line"]
        self.write()
        found = self.findings(frozen, "V12", run_dir=self.run_dir)
        self.assertTrue(any("step 2 is not cancelled" in f["message"] for f in found), "a done status step with no card claiming it must have been cancelled")


class V6MovedBefore(Base):
    """E8-A44 in V6: a card that moved before the violation was found is held to the mapping; a frozen card
    beside a violation is not."""

    def test_moved_before_card_held_to_the_mapping(self):
        ws = os.path.join(self.dir, "ws")
        items = example("result-completed.json")["items"]
        text = "# plan\n\n## Slice A — export\nStatus: signed off with conditions\n\n## Punch list\n\n### 2026-09-19 — review: Slice A\n"
        text += "- BLOCKER · src/export.ts:142 · %s · %s · A\n- MAJOR · src/export.ts:142 · %s · %s · A\n" % (items[0]["claim"], items[0]["failure_scenario"], items[1]["claim"], items[1]["failure_scenario"])
        text += ledger.render_block("2026-09-20", ["A"], [ledger.render_recheck_line("BLOCKER", "src/export.ts", 142, items[0]["claim"], "fixed", "executed"),
                                                          ledger.render_recheck_line("MAJOR", "src/export.ts", 142, items[1]["claim"], "not fixed", "executed")])
        write_text(os.path.join(ws, DOC), text)
        result = example("result-completed.json")
        result["records_written"] = [w for w in result["records_written"] if w["kind"] != "waived_line"]
        self.assertEqual(self.paths(result, "V6", workspace=ws), [], self.messages(result, "V6", workspace=ws))
        result["boundary_violations"] = ["README.md changed"]; result["result"] = "not_clear"
        result["cards"][0]["reason"] = validate.MOVED_BEFORE_VIOLATION
        self.assertEqual(self.paths(result, "V6", workspace=ws), [], "moved by the mapping before the violation was found")
        result["cards"][0]["after"] = "signed off"
        found = self.findings(result, "V6", workspace=ws)
        self.assertTrue(any(f["path"] == "/cards/0/after" and "the mapping over the slice's open set gives" in f["message"] for f in found),
                        "a moved-before card is held to the mapping (%r)" % found)
        result["cards"][0]["reason"] = "other"
        self.assertEqual([f for f in self.findings(result, "V6", workspace=ws) if "the mapping over" in f["message"]], [],
                         "any other moved card beside a violation is V12's finding, not the mapping's")
        self.assertIn("/cards/0", self.paths(result, "V12"))


if __name__ == "__main__":
    unittest.main()
