"""recheck_core.ledger: Appendix A parsing, the open filter, the home, cards, and renderers
byte-compatible with the E7 library's writers (E8-28). Every expectation cites a CASES.md fact
or a contract section."""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import canon, ledger, records_view  # noqa: E402

DOC = "docs/plans/2026-09-18-widget-export.md"


def case(lane, prefix):
    for cid, cdir in testlib.lane_cases(lane):
        if cid.startswith(prefix):
            return cdir
    raise AssertionError(prefix)


def parsed_doc(cdir, rel=DOC):
    return ledger.parse_document(testlib.read_text(os.path.join(cdir, "workspace", rel)), rel)


def sha(text):
    return canon.sha256_hex(text.encode("utf-8"))


class Parsing(unittest.TestCase):
    def test_w2_01_records_and_states(self):
        """W CASES.md, W2-01: E1, E2, E4 findings; a 2026-09-20 recheck line for E2; RO-E2 directly after it;
        a 2026-09-21 block with RL-E1, RL-E2. After the landed steps E1 and E2 read fixed and E4 stays open."""
        p = parsed_doc(case("W-recording", "W2-01"))
        kinds = [(r["kind"], r["line"]) for r in p["records"]]
        self.assertEqual(kinds, [("finding", 9), ("finding", 14), ("finding", 32), ("recheck", 14), ("reopening", 14), ("recheck", 9), ("recheck", 14)])
        self.assertEqual([(b["date"], b["kind"], b["slices"]) for b in p["blocks"]], [("2026-09-19", "review", ["A"]), ("2026-09-20", "recheck", ["A"]), ("2026-09-21", "recheck", ["A"])])
        states = {(e["line"]): e["state"] for e in ledger.open_set(p)["entries"]}
        self.assertEqual(states, {9: "fixed", 14: "fixed", 32: "open"})
        self.assertEqual([s["card"] for s in p["slices"]], ["rejected"])

    def test_w2_03_two_slice_heading(self):
        """W CASES.md, W2-03: the block heading `### 2026-09-21 — recheck: Slice A, Slice B` (E8-19)."""
        p = parsed_doc(case("W-recording", "W2-03"))
        self.assertEqual(p["blocks"][-1]["slices"], ["A", "B"])
        self.assertEqual(ledger.render_heading("2026-09-21", ["B", "A"]), "### 2026-09-21 — recheck: Slice A, Slice B")

    def test_w3_01_legacy_shapes(self):
        """W CASES.md, W3-01: line 1 carries the legacy tag (csv) glued to the location (the location is
        src/widget/export.py:9, E8-22); line 2 has four fields and no claim; line 4 is a legacy waiver
        without quoted words; the Notes bullets outside the ledger home are not records."""
        p = parsed_doc(case("W-recording", "W3-01"))
        recs = p["records"]
        self.assertEqual([r["kind"] for r in recs], ["finding", "finding", "finding", "waiver"])
        self.assertEqual((recs[0]["file"], recs[0]["line"], recs[0]["tag"]), ("src/widget/export.py", 9, "csv"))
        self.assertIsNone(recs[1]["claim"]); self.assertEqual(recs[1]["line"], 14)
        self.assertIsNone(recs[3]["words"]); self.assertEqual(recs[3]["date"], "2026-09-20")
        entries = ledger.open_set(p)["entries"]
        self.assertEqual([(e["line"], e["state"]) for e in entries], [(9, "open"), (14, "open"), (32, "waived")])
        self.assertEqual(ledger.open_set(p)["ambiguities"], [])

    def test_w3_02_ambiguities(self):
        """W CASES.md, W3-02a: six fields (a claim containing the separator); W3-02b: two fields; W3-02c: two
        identical findings in one block; W3-02d: a waiver line without its date. Each is missing input
        (Appendix A, ambiguous legacy records)."""
        for prefix, needle in (("W3-02a", "matches no Appendix A shape"), ("W3-02b", "matches no Appendix A shape"),
                               ("W3-02c", "same location and claim in one block"), ("W3-02d", "without its date")):
            amb = ledger.open_set(parsed_doc(case("W-recording", prefix)))["ambiguities"]
            self.assertTrue(amb, prefix)
            self.assertIn(needle, amb[0]["reason"], prefix)

    def test_w3_03_fence_and_undated_heading(self):
        """W CASES.md, W3-03: the fenced example and the bullets under `### Fixer notes` are not records; the
        only record is E1 (ruling E7-16, E8-20)."""
        p = parsed_doc(case("W-recording", "W3-03"))
        self.assertEqual([(r["kind"], r["line"]) for r in p["records"]], [("finding", 9)])
        self.assertEqual(len(p["blocks"]), 1)
        self.assertEqual(ledger.open_set(p)["ambiguities"], [])

    def test_s1_claimless(self):
        """S1 CASES.md: S1-02's claim-less entry sits at a location two entries share (ambiguous); S1-03's sits
        at a location a single entry holds (matched on location alone); S1-01's two entries differ in claim."""
        amb = ledger.open_set(parsed_doc(case("S1-colocated", "S1-02")))["ambiguities"]
        self.assertEqual(len(amb), 1); self.assertIn("claim-less finding at a location several entries share", amb[0]["reason"])
        o = ledger.open_set(parsed_doc(case("S1-colocated", "S1-03")))
        self.assertEqual(o["ambiguities"], []); self.assertEqual(len(o["entries"]), 1); self.assertIsNone(o["entries"][0]["claim"])
        self.assertEqual(records_view.match_entries(o["entries"], "src/widget/export.py", 11, "anything"), o["entries"])
        o1 = ledger.open_set(parsed_doc(case("S1-colocated", "S1-01")))
        self.assertEqual(len(o1["entries"]), 2); self.assertEqual(o1["ambiguities"], [])
        self.assertEqual(len(records_view.match_entries(o1["entries"], "src/widget/export.py", 11, "a missing title exports as the string None")), 1)

    def test_s2_05_legacy_waiver_closes(self):
        """S2 CASES.md, S2-05: the legacy waiver line (no quoted words) is later in the file than the BLOCKER
        finding it names; file order decides (Appendix A open filter): the BLOCKER is waived, the MAJOR open."""
        o = ledger.open_set(parsed_doc(case("S2-waivers-reopening", "S2-05")))
        self.assertEqual({e["line"]: e["state"] for e in o["entries"]}, {9: "waived", 17: "open"})

    def test_i1_03_three_fields(self):
        """IA CASES.md, I1-03: the sole ledger line has three fields; ruling E7-13: it matches no shape."""
        amb = ledger.open_set(parsed_doc(case("IA-input-authorization", "I1-03")))["ambiguities"]
        self.assertEqual(len(amb), 1); self.assertIn("field count 3", amb[0]["reason"])

    def test_recheck_line_no_claim(self):
        rec = ledger._block_record(["BLOCKER", "src/x.py:1", "()", "fixed", "how"], 1, "", {"kind": "recheck", "line_no": 1, "date": "2026-09-20", "slices": ["A"], "text": ""})
        self.assertEqual(rec["kind"], "recheck"); self.assertIsNone(rec["claim"])
        rec = ledger._block_record(["MAJOR", "src/x.py:1", "broke: a claim — a scenario"], 1, "", {"kind": "recheck", "line_no": 1, "date": "2026-09-20", "slices": ["A"], "text": ""})
        self.assertEqual((rec["kind"], rec["claim"], rec["scenario"]), ("defect", "a claim", "a scenario"))


class RenderAndApply(unittest.TestCase):
    """The core's bytes equal the seeded W2 plans' hashes (W CASES.md, run directory facts)."""

    def head_doc(self, cdir):
        return testlib.git(os.path.join(cdir, "workspace"), "show", "HEAD:" + DOC)

    def test_w2_01_chain(self):
        cdir = case("W-recording", "W2-01")
        plan = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))["plan"]
        cp = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
        inp = testlib.load_json(os.path.join(cdir, "input.json"))
        head = self.head_doc(cdir)
        self.assertEqual(sha(head), plan[0]["before_sha256"])
        g = inp["authorization"]["reopen"][0]
        c1 = ledger.append_at_home(head, ledger.render_reopen(g["date"], g["item"]["location"]["file"], g["item"]["location"]["line"], g["item"]["claim"], g["quoted_words"]), DOC)
        self.assertEqual(sha(c1), plan[0]["after_sha256"], "RO-E2 directly after the ledger home's last line")
        lines = []
        for it, st in zip(cp["scope"]["checklist"], cp["items"]):
            res = st["result"]
            lines.append(ledger.render_recheck_line(it["severity"], it["location"]["file"], it["location"]["line"], it["claim"], "fixed", ledger.render_how(res["verification"])))
        c2 = ledger.append_at_home(c1, ledger.render_block("2026-09-21", ["A"], lines), DOC)
        self.assertEqual(sha(c2), plan[1]["after_sha256"], "one blank line, the heading, the lines")
        self.assertEqual(c2, testlib.read_text(os.path.join(cdir, "workspace", DOC)), "the doc on disk is HEAD plus the two landed steps")
        w = inp["authorization"]["waivers"][0]
        c3 = ledger.append_at_home(c2, ledger.render_waiver(w["date"], w["severity"], w["item"]["location"]["file"], w["item"]["location"]["line"], w["item"]["claim"], w["quoted_words"]), DOC)
        self.assertEqual(sha(c3), plan[2]["after_sha256"], "WV-E4")
        c4 = ledger.set_status_text(c3, "A", "signed off")
        self.assertEqual(sha(c4), plan[3]["after_sha256"], "the status step replaces the text after Status: only")
        self.assertEqual(c4.count("\n"), c3.count("\n"))

    def test_w2_03_and_w2_05(self):
        cdir = case("W-recording", "W2-03")
        plan = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))["plan"]
        cp = testlib.load_json(os.path.join(cdir, "run", "checkpoint.json"))
        lines = [ledger.render_recheck_line(it["severity"], it["location"]["file"], it["location"]["line"], it["claim"], "fixed", ledger.render_how(st["result"]["verification"]))
                 for it, st in zip(cp["scope"]["checklist"], cp["items"])]
        c1 = ledger.append_at_home(self.head_doc(cdir), ledger.render_block("2026-09-21", ["A", "B"], lines), DOC)
        self.assertEqual(sha(c1), plan[0]["after_sha256"])
        self.assertEqual(sha(ledger.set_status_text(c1, "A", "signed off")), plan[1]["after_sha256"])
        self.assertEqual(sha(ledger.set_status_text(ledger.set_status_text(c1, "A", "signed off"), "B", "signed off")), plan[2]["after_sha256"])
        cdir = case("W-recording", "W2-05")
        plan = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))["plan"]
        inp = testlib.load_json(os.path.join(cdir, "input.json"))
        w = inp["authorization"]["waivers"][0]
        on_disk = testlib.read_text(os.path.join(cdir, "workspace", DOC))
        self.assertEqual(sha(on_disk), plan[0]["after_sha256"], "step 1 landed")
        c2 = ledger.append_at_home(on_disk, ledger.render_waiver(w["date"], w["severity"], w["item"]["location"]["file"], w["item"]["location"]["line"], w["item"]["claim"], w["quoted_words"]), DOC)
        self.assertEqual(sha(c2), plan[1]["after_sha256"], "WV-E1 regenerated from the grant")

    def test_apply_step_matches_renderers(self):
        cdir = case("W-recording", "W2-05")
        plan = testlib.load_json(os.path.join(cdir, "run", "receipt.json"))["plan"]
        inp = testlib.load_json(os.path.join(cdir, "input.json"))
        w = inp["authorization"]["waivers"][0]
        on_disk = testlib.read_text(os.path.join(cdir, "workspace", DOC))
        step = {"kind": "waived_line", "target": DOC, "content": ledger.render_waiver(w["date"], w["severity"], "src/widget/export.py", 9, w["item"]["claim"], w["quoted_words"])}
        self.assertEqual(sha(ledger.apply_step(on_disk, step)), plan[1]["after_sha256"])
        self.assertEqual(sha(ledger.apply_step(ledger.apply_step(on_disk, step), {"kind": "status_line", "slice": "A", "value": "signed off"})), plan[2]["after_sha256"])

    def test_quoted_words_and_single_line(self):
        """Appendix A: an inner double quote is written as a single quote; no separator or line break in a field."""
        line = ledger.render_waiver("2026-09-20", "MINOR", "a.py", 1, "claim", 'say "hi"')
        self.assertIn("· \"say 'hi'\"\n", line)
        self.assertEqual(ledger.ledger_words('say "hi"'), "say 'hi'", "the marker form equals the ledger line's words (E8-A16)")
        self.assertEqual(ledger.render_how({"method": "static", "static_reason": "non_executable_artifact", "evidence": [{"kind": "read", "detail": "line 1\nline 2 · x"}]}),
                         "static (non_executable_artifact) line 1 line 2 - x")
        self.assertEqual(ledger.render_how({"method": "executed", "evidence": [{"kind": "command", "detail": "executed already"}]}), "executed already")
        self.assertEqual(ledger.render_recheck_line("BLOCKER", "a.py", 1, None, "fixed", "how"), "- BLOCKER · a.py:1 · () · fixed · how")

    def test_home_created_when_absent(self):
        """Appendix A: the `## Punch list` section is created when no block exists yet (F1-06's verdict doc)."""
        cdir = case("F1-fixed-defect", "F1-06")
        rel = "docs/reviews/2026-09-19-signoff-widget-export-a.md"
        text = testlib.read_text(os.path.join(cdir, "workspace", rel))
        p = ledger.parse_document(text, rel)
        self.assertEqual(p["blocks"], [], "`## Findings` is not a block heading")
        self.assertEqual(ledger.ledger_home(p)[2], True)
        out = ledger.append_at_home(text, ledger.render_block("2026-09-20", ["A"], ["- x"]), rel)
        self.assertTrue(out.endswith("\n\n## Punch list\n\n### 2026-09-20 — recheck: Slice A\n- x\n"), repr(out[-80:]))
        self.assertEqual(ledger.verdict_doc_glob(os.path.join(cdir, "workspace"), DOC, "A"), [rel])
        many = case("F1-fixed-defect", "F1-07")
        self.assertEqual(len(ledger.verdict_doc_glob(os.path.join(many, "workspace"), DOC, "A")), 2, "F1-07: two matches")

    def test_home_is_the_place_whose_tail_comes_last(self):
        """Appendix A as amended (E8-A13, under E8-1's file order): records in two places; the home is the place
        whose tail comes last in the file, whatever the dates, so an appended record is the last record in file
        order. Here the later-dated block sits under `## Notes` before `## Punch list`: the home is the Punch list."""
        text = "# T\n\n## Slice A — x\nStatus: rejected\n\n## Notes\n\n### 2026-09-19 — review: Slice A\n- MAJOR · a.py:1 · c · s · Slice A\n\n## Punch list\n\n### 2026-09-18 — review: Slice A\n- MINOR · a.py:2 · d · s · Slice A\n"
        p = ledger.parse_document(text, DOC)
        start, end, create = ledger.ledger_home(p)
        self.assertFalse(create); self.assertEqual(p["lines"][start], "## Punch list")
        out = ledger.append_at_home(text, "- WAIVED (per user) · 2026-09-20 · MAJOR · a.py:1 · c · \"w\"\n", DOC)
        self.assertTrue(out.endswith("- MINOR · a.py:2 · d · s · Slice A\n- WAIVED (per user) · 2026-09-20 · MAJOR · a.py:1 · c · \"w\"\n"), repr(out[-120:]))
        o = ledger.open_set(ledger.parse_document(out, DOC))
        self.assertEqual({e["line"]: e["state"] for e in o["entries"]}, {1: "waived", 2: "open"}, "the appended line is never dead")
        # the reverse layout: the Punch list first, a Notes section with a block after it; the home is Notes
        text2 = "# T\n\n## Slice A — x\nStatus: rejected\n\n## Punch list\n\n### 2026-09-19 — review: Slice A\n- MAJOR · a.py:1 · c · s · Slice A\n\n## Notes\n\n### 2026-09-18 — recheck: Slice A\n- MINOR · a.py:2 · (d) · fixed · how\n"
        p2 = ledger.parse_document(text2, DOC)
        start, end, create = ledger.ledger_home(p2)
        self.assertEqual(p2["lines"][start], "## Notes")
        # a standalone waiver line in a later section is a record too and moves the home there
        text3 = "# T\n\n## Punch list\n\n### 2026-09-19 — review: Slice A\n- MAJOR · a.py:1 · c · s · Slice A\n\n## Later\n\n- WAIVED (per user) · 2026-09-20 · MAJOR · a.py:1 · c · \"w\"\n"
        p3 = ledger.parse_document(text3, DOC)
        self.assertEqual(p3["lines"][ledger.ledger_home(p3)[0]], "## Later")


class ClaimNormalization(unittest.TestCase):
    """E8-A28: outer parentheses are not part of the claim in any shape the reader accepts (review finding,
    recheck line, waiver, reopening) nor in the join key, so a review claim written `(text)` matches its
    recheck, waiver, and reopening lines."""
    HEAD = "# T\n\n## Slice A — x\nStatus: rejected\n\n## Punch list\n\n### 2026-09-19 — review: Slice A\n- BLOCKER · a.py:1 · (the claim) · a scenario · Slice A\n"

    def entries(self, text):
        o = ledger.open_set(ledger.parse_document(text, DOC))
        self.assertEqual(o["ambiguities"], [])
        return o["entries"]

    def test_parenthesized_review_claim(self):
        entries = self.entries(self.HEAD)
        self.assertEqual([(e["claim"], e["state"]) for e in entries], [("the claim", "open")])
        self.assertEqual(ledger.render_recheck_line("BLOCKER", "a.py", 1, entries[0]["claim"], "fixed", "how"),
                         "- BLOCKER · a.py:1 · (the claim) · fixed · how", "the rendered recheck line wraps the claim once")
        # (a) a prior recheck line marking it fixed: the open set has one entry, state fixed
        fixed = self.HEAD + "\n### 2026-09-20 — recheck: Slice A\n- BLOCKER · a.py:1 · (the claim) · fixed · executed x\n"
        self.assertEqual([(e["claim"], e["state"]) for e in self.entries(fixed)], [("the claim", "fixed")])
        # (b) a waiver line for it, the claim bare: waived
        waived = self.HEAD + "- WAIVED (per user) · 2026-09-20 · BLOCKER · a.py:1 · the claim · \"w\"\n"
        self.assertEqual([(e["claim"], e["state"]) for e in self.entries(waived)], [("the claim", "waived")])
        # (c) a reopening line after the fix: open again
        reopened = fixed + "- REOPENED (per user) · 2026-09-21 · a.py:1 · the claim · \"r\"\n"
        self.assertEqual([(e["claim"], e["state"]) for e in self.entries(reopened)], [("the claim", "open")])
        # the grant lines written with parentheses match the same entry (one normalization for every shape)
        waived2 = self.HEAD + "- WAIVED (per user) · 2026-09-20 · BLOCKER · a.py:1 · (the claim) · \"w\"\n"
        self.assertEqual([e["state"] for e in self.entries(waived2)], ["waived"])
        reopened2 = fixed + "- REOPENED (per user) · 2026-09-21 · a.py:1 · (the claim) · \"r\"\n"
        self.assertEqual([e["state"] for e in self.entries(reopened2)], ["open"])

    def test_join_key_strips_the_reference(self):
        """Named-item matching normalizes the reference's claim the same way. E13 slice 1: the join
        moved to `records_view.match_entries`, which runs over the component's entries; the rule it
        applies is unchanged, and the entries here are the same shape."""
        entries = self.entries(self.HEAD)
        self.assertEqual(len(records_view.match_entries(entries, "a.py", 1, "(the claim)")), 1)
        self.assertEqual(len(records_view.match_entries(entries, "a.py", 1, "the claim")), 1)
        self.assertEqual(records_view.match_entries(entries, "a.py", 1, "another claim"), [])
        self.assertEqual(ledger.strip_parens("(x)"), "x")
        self.assertEqual(ledger.strip_parens("()"), None)
        self.assertEqual(ledger.strip_parens("x"), "x")


class DefectSlice(unittest.TestCase):
    """E8-A25: a fix-introduced defect line names its slice in a fourth field only under a heading naming more
    than one slice; the reader takes that field as the charge; the single-slice line keeps three fields."""
    MULTI = {"kind": "recheck", "line_no": 1, "date": "2026-09-20", "slices": ["A", "B"], "text": ""}
    SINGLE = {"kind": "recheck", "line_no": 1, "date": "2026-09-20", "slices": ["A"], "text": ""}

    def test_render(self):
        base = ledger.render_defect_line("MAJOR", "a.py", 2, "c", "s")
        self.assertEqual(base, "- MAJOR · a.py:2 · broke: c — s", "a single-slice block's bytes are unchanged")
        self.assertIsNone(ledger.defect_slice_field(["A"], "A"))
        self.assertEqual(ledger.defect_slice_field(["A", "B"], "B"), "B")
        self.assertEqual(ledger.render_defect_line("MAJOR", "a.py", 2, "c", "s", ledger.defect_slice_field(["A"], "A")), base)
        self.assertEqual(ledger.render_defect_line("MAJOR", "a.py", 2, "c", "s", ledger.defect_slice_field(["A", "B"], "B")), base + " · B")
        self.assertEqual(ledger.render_defect_line("MAJOR", "a.py", 2, "c", "s", ledger.defect_slice_field(["A", "none"], "none")), base + " · punch list")

    def test_reader(self):
        rec = ledger._block_record(["MAJOR", "a.py:2", "broke: c — s", "B"], 1, "", self.MULTI)
        self.assertEqual((rec["kind"], rec["claim"], rec["slice"]), ("defect", "c", "B"))
        self.assertEqual(ledger.entry_slice(rec), "B")
        rec = ledger._block_record(["MAJOR", "a.py:2", "broke: c — s", "Slice B"], 1, "", self.MULTI)
        self.assertEqual((rec["kind"], rec["slice"]), ("defect", "B"))
        rec = ledger._block_record(["MAJOR", "a.py:2", "broke: c — s"], 1, "", self.MULTI)
        self.assertEqual(rec["kind"], "ambiguous")
        self.assertEqual(rec["reason"], "fix-introduced defect line under a multi-slice heading lacks its slice field")
        rec = ledger._block_record(["MAJOR", "a.py:2", "broke: c — s", "A"], 1, "", self.SINGLE)
        self.assertEqual(rec["kind"], "ambiguous")
        self.assertIn("field count 4 matches no Appendix A shape", rec["reason"])
        rec = ledger._block_record(["MAJOR", "a.py:2", "broke: c — s"], 1, "", self.SINGLE)
        self.assertEqual((rec["kind"], rec["slice"]), ("defect", None))
        self.assertEqual(ledger.entry_slice(rec), "A")

    def test_document_round_trip(self):
        head = "# T\n\n## Slice A — x\nStatus: rejected\n\n## Slice B — y\nStatus: rejected\n\n## Punch list\n\n### 2026-09-20 — recheck: Slice A, Slice B\n"
        text = head + ledger.render_defect_line("MAJOR", "b.py", 3, "c", "s", ledger.defect_slice_field(["A", "B"], "B")) + "\n"
        p = ledger.parse_document(text, DOC)
        o = ledger.open_set(p)
        self.assertEqual(o["ambiguities"], [])
        self.assertEqual([(e["line"], e["slice"], e["state"]) for e in o["entries"]], [(3, "B", "open")])
        # the cards are computed from that charge: B holds the open MAJOR, A holds nothing
        self.assertEqual(ledger.card_after("rejected", [e for e in o["entries"] if e["slice"] == "B" and e["state"] == "open"]), "signed off with conditions")
        self.assertEqual(ledger.card_after("rejected", [e for e in o["entries"] if e["slice"] == "A" and e["state"] == "open"]), "signed off")
        # the same line without its field under the same heading is missing input
        o = ledger.open_set(ledger.parse_document(head + ledger.render_defect_line("MAJOR", "b.py", 3, "c", "s") + "\n", DOC))
        self.assertEqual(len(o["ambiguities"]), 1)
        self.assertEqual(o["ambiguities"][0]["reason"], "fix-introduced defect line under a multi-slice heading lacks its slice field")
        # under a single-slice heading a fourth field is ambiguous too
        single = head.replace("Slice A, Slice B", "Slice A") + ledger.render_defect_line("MAJOR", "b.py", 3, "c", "s", "A") + "\n"
        o = ledger.open_set(ledger.parse_document(single, DOC))
        self.assertEqual(len(o["ambiguities"]), 1)
        self.assertIn("field count 4", o["ambiguities"][0]["reason"])


class Cards(unittest.TestCase):
    def test_mapping(self):
        e = lambda sev: {"severity": sev, "state": "open"}  # noqa: E731
        self.assertEqual(ledger.card_after("rejected", [e("BLOCKER"), e("MAJOR")]), "rejected")
        self.assertEqual(ledger.card_after("rejected", [e("MAJOR"), e("MINOR")]), "signed off with conditions")
        self.assertEqual(ledger.card_after("rejected", [e("MINOR")]), "signed off", "MINOR items never move a card")
        self.assertEqual(ledger.card_after("signed off with conditions", []), "signed off")
        self.assertEqual(ledger.card_after("signed off", [e("BLOCKER")]), "rejected", "demoted if it stood higher")
        self.assertEqual(ledger.card_after("built", [e("BLOCKER")]), "built", "a slice at built keeps built")
        # E8-A8: a slice at not started moves by the mapping like any other card
        self.assertEqual(ledger.card_after("not started", [e("MAJOR")]), "signed off with conditions")
        self.assertEqual(ledger.card_after("not started", [e("BLOCKER")]), "rejected")
        self.assertEqual(ledger.card_after("not started", []), "signed off")
        self.assertIn("not started", ledger.MOVABLE_CARDS)
        self.assertEqual(ledger.card_after("none", [e("BLOCKER")]), "none")
        self.assertEqual(ledger.sort_slices(["B", "A", "Beta", "A"]), ["A", "B", "Beta"])

    def test_s3_01_built_card(self):
        """S34 CASES.md, S3-01: the card reads built at HEAD with two open BLOCKERs."""
        p = parsed_doc(case("S34-cards-identity", "S3-01"))
        self.assertEqual(p["slices"][0]["card"], "built")
        o = ledger.open_set(p)
        self.assertEqual(ledger.card_after("built", [x for x in o["entries"] if x["state"] == "open"]), "built")


if __name__ == "__main__":
    unittest.main()
