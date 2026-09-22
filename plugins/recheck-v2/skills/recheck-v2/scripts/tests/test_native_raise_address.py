"""E13 CR-F3: recheck starts on a finding a station raised NATIVELY.

After amendment A4 a signoff station raises findings as native `finding_raised` events and places
the component's rendered review block (`### <date> — review: Slice X`) in the build doc. The
pilot's view used to address every native event as "no document line, no heading", so a
`{build_doc, slice}` start built `scope.checklist[i].record.heading` as '' and refused its own
checkpoint (missing_input, `/scope/checklist/i/record/heading '' should be non-empty`).

The address of a native raise (`finding_raised`, `defect_raised`) is now where the component's
rendering of that event sits in the document: `records.py render --run-id <the event's run>`
gives the exact line and the heading its block carries; the document's own record at that line
gives the line number and the heading it actually sits under. A raise whose line the document
does not carry (the station's append landed, its document write did not) keeps the heading the
component's render carries and no line.

Nothing here changes what recheck decides (ruling E13-1): the same findings are open, the same
checklist is selected, the same card moves.

Every event is appended and rendered through the real records CLI; the document is edited only
the way a station would edit it (the rendered block appended at the tail).
"""
import json
import os
import subprocess
import unittest

import testlib

DOC = "docs/plans/2026-09-18-widget-export.md"
RECORDS = os.path.normpath(os.path.join(testlib.PLUGIN, os.pardir, "records"))
RECORDS_CLI = os.path.join(RECORDS, "scripts", "records.py")
NATIVE_RUN = "signoff-cr-f3-native-1"
NATIVE_CLAIM = "the header line is written twice"
NATIVE_HEADING = "### 2026-09-21 — review: Slice A"
BASIS = "default table: a real defect with a concrete failure path, contained and fixable in place"


class Base(unittest.TestCase):
    LANE = "F1-fixed-defect"
    CASE = "F1-01-fixed-clean"

    def setUp(self):
        self.dir = testlib.make_scratch("e13-cr-f3-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case(self.LANE, self.CASE, os.path.join(self.dir, "cases"))
        self.workspace = os.path.join(self.case, "workspace")
        testlib.prepare_input(self.case)

    # ---- the records component, run directly --------------------------------------------------

    def records(self, *args):
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run([testlib.GEN_PYTHON, RECORDS_CLI] + list(args), cwd=self.dir, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace")
        body = json.loads(out) if out.strip() else None
        self.assertEqual(proc.returncode, 0, "%s: %s %s" % (args[0], out, proc.stderr.decode("utf-8", "replace")))
        return body

    def raise_native(self):
        """A signoff station's native raise: level the log, append one `finding_raised` through the
        real CLI, and return the component's rendering of that run."""
        self.records("import-legacy", "--workspace", self.workspace, "--doc", DOC)
        head = self.records("state", "--workspace", self.workspace, "--doc", DOC)["head"]
        identity = self.records("identity", "--workspace", self.workspace)["identity"]
        event = {"v": 1, "kind": "finding_raised", "at": "2026-09-21T10:00:00Z", "ledger_doc": DOC,
                 "actor": {"station": "signoff-v2", "run_id": NATIVE_RUN, "harness": "claude-code"},
                 "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
                 "slice": "A", "severity": "MAJOR",
                 "location": {"raw": "src/widget/export.py:31", "file": "src/widget/export.py", "line": 31,
                              "line_end": None, "tag": None, "more": [], "resolved": True},
                 "claim": NATIVE_CLAIM,
                 "scenario": "run the exporter twice and read the file; two header lines",
                 "raised_by": "independent reviewer"}
        path = os.path.join(self.dir, "native-events.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([event], fh)
        self.records("append", "--workspace", self.workspace, "--doc", DOC, "--events", path, "--expect-head", head)
        return self.records("render", "--workspace", self.workspace, "--doc", DOC, "--run-id", NATIVE_RUN)

    def place(self, text):
        """The station's document write: the rendered block appended at the ledger home's tail."""
        with open(os.path.join(self.workspace, DOC), "a", encoding="utf-8") as fh:
            fh.write(text)

    def doc_lines(self):
        return testlib.read_text(os.path.join(self.workspace, DOC)).split("\n")

    # ---- the pilot --------------------------------------------------------------------------

    def start(self, input_path=None):
        return testlib.recheck(["start", input_path or os.path.join(self.case, "input.json")], cwd=self.dir)

    def checkpoint(self, run_dir=None):
        return testlib.load_json(os.path.join(run_dir or os.path.join(self.case, "run"), "checkpoint.json"))

    def ledger_entries(self):
        code, doc, err = testlib.recheck(["ledger", os.path.join(self.workspace, DOC), "--workspace", self.workspace],
                                         cwd=self.dir)
        self.assertEqual(code, 0, err)
        return doc["entries"]

    def item(self, checklist, claim):
        found = [it for it in checklist if it["claim"] == claim]
        self.assertEqual(len(found), 1, checklist)
        return found[0]


class NativeFindingPlaced(Base):
    """(a) the rendered review block sits in the document."""

    def test_start_proceeds_to_verify_with_the_documents_heading_and_line(self):
        rendered = self.raise_native()
        self.assertEqual(len(rendered["review_lines"]), 1)
        self.place(rendered["review"])
        lines = self.doc_lines()
        line_no = lines.index(rendered["review_lines"][0]) + 1
        self.assertEqual(lines[line_no - 2], NATIVE_HEADING, "the station placed the block under its heading")

        code, doc, err = self.start()
        self.assertEqual(code, 0, "%s\n%s" % (err, doc))
        self.assertEqual(doc["next"], "verify", doc)
        checklist = self.checkpoint()["scope"]["checklist"]
        native = self.item(checklist, NATIVE_CLAIM)
        self.assertEqual(native["record"], {"document": DOC, "heading": NATIVE_HEADING, "date": "2026-09-21"})
        # the decision is unchanged: the legacy BLOCKER and the native MAJOR are both open for A, in file order
        self.assertEqual([it["claim"] for it in checklist],
                         ["CSV export writes a title containing a comma without quoting", NATIVE_CLAIM])

        entry = [e for e in self.ledger_entries() if e["claim"] == NATIVE_CLAIM][0]
        self.assertEqual(entry["heading"], NATIVE_HEADING)
        self.assertEqual(entry["last_record_line"], line_no, "the line the rendered finding sits on")

    def test_the_documents_heading_wins_over_the_rendered_one(self):
        """The block was placed by hand under a heading of the document's own dating: the address is
        where the line SITS, so the heading is the document's."""
        rendered = self.raise_native()
        by_hand = "\n### 2026-09-22 — review: Slice A\n" + rendered["review_lines"][0] + "\n"
        self.place(by_hand)
        line_no = self.doc_lines().index(rendered["review_lines"][0]) + 1
        code, doc, err = self.start()
        self.assertEqual(code, 0, "%s\n%s" % (err, doc))
        native = self.item(self.checkpoint()["scope"]["checklist"], NATIVE_CLAIM)
        self.assertEqual(native["record"], {"document": DOC, "heading": "### 2026-09-22 — review: Slice A",
                                            "date": "2026-09-22"})
        entry = [e for e in self.ledger_entries() if e["claim"] == NATIVE_CLAIM][0]
        self.assertEqual(entry["last_record_line"], line_no)


class OneRenderPerRun(Base):
    """The view reaches the component through `records_client` only, and renders each run once per
    view build however many raises the run holds."""

    def test_two_raises_of_one_run_cost_one_render_and_address_apart(self):
        rendered = self.raise_native()
        head = self.records("state", "--workspace", self.workspace, "--doc", DOC)["head"]
        identity = self.records("identity", "--workspace", self.workspace)["identity"]
        second = {"v": 1, "kind": "finding_raised", "at": "2026-09-21T10:00:02Z", "ledger_doc": DOC,
                  "actor": {"station": "signoff-v2", "run_id": NATIVE_RUN, "harness": "claude-code"},
                  "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
                  "slice": "A", "severity": "MINOR",
                  "location": {"raw": "src/widget/export.py:40", "file": "src/widget/export.py", "line": 40,
                               "line_end": None, "tag": None, "more": [], "resolved": True},
                  "claim": "the footer is missing", "scenario": "read the file; no footer line",
                  "raised_by": "independent reviewer"}
        path = os.path.join(self.dir, "native-events-2.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([second], fh)
        self.records("append", "--workspace", self.workspace, "--doc", DOC, "--events", path, "--expect-head", head)
        rendered = self.records("render", "--workspace", self.workspace, "--doc", DOC, "--run-id", NATIVE_RUN)
        self.assertEqual(len(rendered["review_lines"]), 2)
        self.place(rendered["review"])
        lines = self.doc_lines()

        testlib.add_scripts_to_path()
        from recheck_core import records_view  # noqa: E402
        client = testlib.records_client()
        calls = []
        real = client.render

        def counted(workspace, doc, run_id):
            calls.append(run_id)
            return real(workspace, doc, run_id)

        client.render = counted
        view = records_view.read(client, self.workspace, DOC)
        self.assertEqual(calls, [NATIVE_RUN], "one render per run per view build")
        got = dict((e["claim"], (e["origin"]["line_no"], e["heading"])) for e in view.entries)
        self.assertEqual(got[NATIVE_CLAIM], (lines.index(rendered["review_lines"][0]) + 1, NATIVE_HEADING))
        self.assertEqual(got["the footer is missing"], (lines.index(rendered["review_lines"][1]) + 1, NATIVE_HEADING))


class MultiSliceRun(Base):
    """One native run raising on two slices renders one review block per slice (records A4); each
    raise is addressed under its own slice's block, whatever order the run raised them in."""
    CASE = "F1-09-two-slices"

    def raise_two(self):
        self.records("import-legacy", "--workspace", self.workspace, "--doc", DOC)
        head = self.records("state", "--workspace", self.workspace, "--doc", DOC)["head"]
        identity = self.records("identity", "--workspace", self.workspace)["identity"]
        events = []
        for i, (name, line, claim) in enumerate((("B", 50, "slice B raised first"), ("A", 31, NATIVE_CLAIM))):
            events.append({"v": 1, "kind": "finding_raised", "at": "2026-09-21T10:00:0%dZ" % i, "ledger_doc": DOC,
                           "actor": {"station": "signoff-v2", "run_id": NATIVE_RUN, "harness": "claude-code"},
                           "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
                           "slice": name, "severity": "MAJOR",
                           "location": {"raw": "src/widget/export.py:%d" % line, "file": "src/widget/export.py",
                                        "line": line, "line_end": None, "tag": None, "more": [], "resolved": True},
                           "claim": claim, "scenario": "run the exporter and read the file",
                           "raised_by": "independent reviewer"})
        path = os.path.join(self.dir, "native-two-slices.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(events, fh)
        self.records("append", "--workspace", self.workspace, "--doc", DOC, "--events", path, "--expect-head", head)
        return self.records("render", "--workspace", self.workspace, "--doc", DOC, "--run-id", NATIVE_RUN)

    def test_each_raise_sits_under_its_own_slices_block(self):
        rendered = self.raise_two()
        self.assertEqual(rendered["review_slices"], ["A", "B"])
        self.place(rendered["review"])
        lines = self.doc_lines()
        by_claim = dict((e["claim"], e) for e in self.ledger_entries())
        a, b = by_claim[NATIVE_CLAIM], by_claim["slice B raised first"]
        self.assertEqual((a["heading"], a["slice"]), (NATIVE_HEADING, "A"))
        self.assertEqual((b["heading"], b["slice"]), ("### 2026-09-21 — review: Slice B", "B"))
        self.assertEqual(lines[a["last_record_line"] - 1].split(" · ")[2], "(%s)" % NATIVE_CLAIM)
        self.assertEqual(lines[b["last_record_line"] - 1].split(" · ")[2], "(slice B raised first)")
        self.assertLess(a["last_record_line"], b["last_record_line"])


class NativeFindingNotPlaced(Base):
    """(b) the station's append landed and its document write did not.

    What the pilot does, pinned: the finding is in the log, so it is open and on the checklist
    (the log decides, ruling E13-1 and CR-1). Its address is the heading the component's render
    carries and no line. No existing rule stops on a raise whose line the document lacks: the
    checkpoint validates, `start` proceeds to `verify`, and a full run records and completes. The
    recheck block the run places is the component's rendering of the run's own events and does
    not depend on where the raise sits, so the run's document write lands as it always does.
    """

    def test_start_proceeds_with_the_rendered_heading_and_no_line(self):
        rendered = self.raise_native()
        self.assertNotIn(rendered["review_lines"][0], self.doc_lines())
        code, doc, err = self.start()
        self.assertEqual(code, 0, "%s\n%s" % (err, doc))
        self.assertEqual(doc["next"], "verify", doc)
        native = self.item(self.checkpoint()["scope"]["checklist"], NATIVE_CLAIM)
        self.assertEqual(native["record"], {"document": DOC, "heading": NATIVE_HEADING, "date": "2026-09-21"})
        entry = [e for e in self.ledger_entries() if e["claim"] == NATIVE_CLAIM][0]
        self.assertEqual(entry["heading"], NATIVE_HEADING)
        self.assertIsNone(entry["last_record_line"], "the document carries no line for it")

    def test_a_full_run_records_and_completes(self):
        self.raise_native()
        code, started, err = self.start()
        self.assertEqual(code, 0, err)
        run_dir = os.path.join(self.case, "run")
        items = []
        for i, item in enumerate(started["checklist"]):
            items.append({"index": i, "disposition": "fixed", "method": "executed",
                          "location": "%s:%s" % (item["location"]["file"], item["location"]["line"])})
        testlib.write_report(run_dir, testlib.canned_report(items))
        code, _, err = testlib.recheck(["record-call", "--run-dir", run_dir, "--call-id", started["call_id"],
                                        "--status", "ok", "--raw", os.path.join(run_dir, "verifier", "raw.md"),
                                        "--kind", "subagent", "--model", "claude-fable-5-1"], cwd=self.dir)
        self.assertEqual(code, 0, err)
        for i in range(len(items)):
            code, _, err = testlib.recheck(["adjudicate", "--run-dir", run_dir, "--item", str(i),
                                            "--action", "confirmed"], cwd=self.dir)
            self.assertEqual(code, 0, err)
        code, result, err = testlib.recheck(["record", "--run-dir", run_dir], cwd=self.dir)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "completed", result)
        text = testlib.read_text(os.path.join(self.workspace, DOC))
        self.assertIn("- MAJOR · src/widget/export.py:31 · (%s) · fixed · executed" % NATIVE_CLAIM, text)
        self.assertNotIn(NATIVE_HEADING, text, "the run never writes the station's missing review block")


class NativeDefect(Base):
    """(c) a native `defect_raised`: the pilot's own fix-introduced defect from an earlier run.

    Run 1 (F1-02) clears the BLOCKER and raises a MAJOR defect, which the pilot places as a defect
    line under its own recheck heading. Run 2 starts on that defect. Its address is the defect
    line and the recheck heading it sits under, as it was when the pilot read the Markdown itself.
    """
    CASE = "F1-02-regression"
    RUN1_HEADING = "### 2026-09-20 — recheck: Slice A"
    DEFECT = ("- MAJOR · src/widget/export.py:20 · broke: a zero quantity exports as an empty cell — run "
              "PYTHONPATH=src python3 -m widget.export Bolt 0; the data line reads Bolt, with an empty qty cell")

    def run_one(self):
        run_dir = os.path.join(self.case, "run")
        code, started, err = self.start()
        self.assertEqual(code, 0, err)
        report = testlib.canned_report(
            [{"index": 0, "location": "src/widget/export.py:17", "disposition": "fixed",
              "location_after_fix": "src/widget/export.py:20"}],
            new_defects=[{"caused_by_index": 0, "location": "src/widget/export.py:20",
                          "claim": "a zero quantity exports as an empty cell",
                          "failure_scenario": "run PYTHONPATH=src python3 -m widget.export Bolt 0; the data line reads Bolt, with an empty qty cell",
                          "evidence": [{"kind": "command", "detail": "printed Bolt,", "artifact": None}]}])
        testlib.write_report(run_dir, report)
        steps = [["record-call", "--run-dir", run_dir, "--call-id", started["call_id"], "--status", "ok",
                  "--raw", os.path.join(run_dir, "verifier", "raw.md"), "--kind", "subagent", "--model", "claude-fable-5-1"],
                 ["adjudicate", "--run-dir", run_dir, "--item", "0", "--action", "confirmed"],
                 ["new-defect", "--run-dir", run_dir, "--index", "0", "--severity", "MAJOR", "--severity-basis", BASIS]]
        for args in steps:
            code, _, err = testlib.recheck(args, cwd=self.dir)
            self.assertEqual(code, 0, "%s\n%s" % (args, err))
        code, result, err = testlib.recheck(["record", "--run-dir", run_dir], cwd=self.dir)
        self.assertEqual(code, 10, err)
        self.assertEqual(result["status"], "completed", result)

    def test_run_two_starts_on_the_defect_at_its_line_and_heading(self):
        self.run_one()
        lines = self.doc_lines()
        self.assertIn(self.DEFECT, lines)
        line_no = lines.index(self.DEFECT) + 1
        self.assertIn(self.RUN1_HEADING, lines)

        run_dir = os.path.join(self.case, "run-2")
        os.makedirs(run_dir)

        def second(doc):
            doc["invocation"]["run_id"] = doc["invocation"]["run_id"] + "-2"
            doc["invocation"]["run_dir"] = run_dir

        path = testlib.prepare_input(self.case, run_date="2026-09-21", mutate=second,
                                     path=os.path.join(self.case, "input-2.json"))
        code, doc, err = self.start(path)
        self.assertEqual(code, 0, "%s\n%s" % (err, doc))
        self.assertEqual(doc["next"], "verify", doc)
        checklist = self.checkpoint(run_dir)["scope"]["checklist"]
        self.assertEqual(len(checklist), 1, checklist)
        self.assertEqual(checklist[0]["claim"], "a zero quantity exports as an empty cell")
        self.assertEqual(checklist[0]["record"], {"document": DOC, "heading": self.RUN1_HEADING, "date": "2026-09-20"})
        entry = [e for e in self.ledger_entries() if e["claim"] == "a zero quantity exports as an empty cell"][0]
        self.assertEqual(entry["heading"], self.RUN1_HEADING)
        self.assertEqual(entry["last_record_line"], line_no)


if __name__ == "__main__":
    unittest.main()
