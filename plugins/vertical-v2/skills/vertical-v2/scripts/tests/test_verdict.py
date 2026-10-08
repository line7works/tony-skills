"""vertical-v2's verdict and report (contract sections 3.8 and 3.9; readings CR-7 and CR-8).

The verified findings (CONFIRMED and PLAUSIBLE) are deduped on file:line and claim, the refuted ones
counted as `Refuted: N`, the severity mapping names the verdict, the repeats and misses are read against
the ledger through the records component, and the one write is the verdict doc
`docs/reviews/<date>-vertical-<feature>.md`, v1's three sections, rendered by `forms.py`; a rerun appends
a dated block to the same file, never a second file, never an edit of an earlier block. The archive copies
are removed after the verdict. A report-only run writes nothing. `report` ends the run with the
`VERTICAL:` block.
"""
import json
import os
import types
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()

from vertical_core import forms, report  # noqa: E402

DOC_NAME = "2026-10-01-vertical-turnstile.md"
OUT_A = "run-0001-gpt-astra"


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the verdict runs after the fleets (records, readers' roster, jsonschema)")
class _Verdict(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vverdict-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def verdict(self, drive, run_dir):
        code, out, err = drive(["verdict", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        return out

    def doc(self, ws):
        return testlib.read_text(os.path.join(ws, "docs", "reviews", DOC_NAME))


class TheWrite(_Verdict):

    def test_a_local_only_review_writes_one_doc_with_v1s_three_sections(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        before = testlib.tree_digest(ws)
        out = self.verdict(drive, run_dir)
        self.assertEqual(vlib.verdict_docs(ws), [DOC_NAME])
        parsed = forms.parse_doc(self.doc(ws))
        block = parsed["blocks"][0]
        self.assertEqual((block["verdict"], block["refuted"], block["findings"]), ("SIGNED OFF", 0, []))
        self.assertTrue(any(line.startswith("Base: %s" % info["base"]) for line in block["method"]), block["method"])
        self.assertIn(forms.BANNER, self.doc(ws))
        self.assertEqual(len(block["appendix"]), 3)
        os.remove(os.path.join(ws, "docs", "reviews", DOC_NAME))
        self.assertEqual(testlib.tree_digest(ws), before, "the verdict doc is the one write")

    def test_the_copies_are_removed_after_the_verdict(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=("gpt-astra", "deepseek"))
        self.verdict(drive, run_dir)
        seen = 0
        for folder in ("packets", "summons"):
            for name in os.listdir(os.path.join(run_dir, folder)):
                seen += 1
                for part in ("workspace", "documents"):
                    self.assertFalse(os.path.exists(os.path.join(run_dir, folder, name, part)), (folder, name, part))
                self.assertTrue(os.path.isfile(os.path.join(run_dir, folder, name, "mandate.md")), (folder, name))
        self.assertGreaterEqual(seen, 6)

    def test_a_rerun_appends_a_dated_block_to_the_same_file(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        self.verdict(drive, run_dir)
        first = self.doc(ws)
        testlib.git(ws, ["add", "-A"])
        testlib.git(ws, ["commit", "-q", "-m", "file the verdict"])
        drive2, run_dir2 = vlib.start(self.tmp, ws, run="run-2")
        code, out, err = vlib.through_ask(drive2, self.tmp, run_dir2, rows=())
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(drive2(["scope", "--run-dir", run_dir2])[0], 0)
        self.assertEqual(drive2(["request", "--run-dir", run_dir2])[0], 0)
        vlib.file_local_sidecars(run_dir2)
        self.assertEqual(vlib.record_local(drive2, self.tmp, run_dir2, name="local-2.json")[0], 0)
        self.verdict(drive2, run_dir2)
        second = self.doc(ws)
        self.assertEqual(vlib.verdict_docs(ws), [DOC_NAME])
        self.assertTrue(second.startswith(first))
        self.assertEqual(len(forms.parse_doc(second)["blocks"]), 2)

    def test_two_verdict_docs_for_one_build_stop_the_write(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        for name in ("2026-09-01-vertical-turnstile.md", "2026-09-02-vertical-turnstile.md"):
            testlib.write_text(os.path.join(ws, "docs", "reviews", name), "# Vertical review\n")
        code, out, err = drive(["verdict", "--run-dir", run_dir])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "verdict-doc-ambiguous")

    def test_a_report_only_run_writes_nothing(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=(), report_only=True)
        before = testlib.tree_digest(ws)
        out = self.verdict(drive, run_dir)
        self.assertEqual(testlib.tree_digest(ws), before)
        self.assertEqual(vlib.verdict_docs(ws), [])
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Clean; nothing to fix."])
        self.assertEqual(code, 10, (out, err))
        self.assertTrue(out["wrote_nothing"])
        self.assertEqual(out["writes"][-1]["kind"], "run_artifact")


class TheMerge(_Verdict):

    def test_refuted_findings_are_counted_and_kept_out_of_the_verdict(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, outside_findings=[
            vlib.finding("src/turnstile.py:4", severity="BLOCKER", found_by=[OUT_A], claim="reset loses the count"),
            vlib.finding("src/ghost.py:9", stamp="REFUTED", found_by=[OUT_A], claim="a ghost import",
                         refuted_because="no such file in the reviewed copy")])
        self.verdict(drive, run_dir)
        block = forms.parse_doc(self.doc(ws))["blocks"][0]
        self.assertEqual(block["verdict"], "REJECTED")
        self.assertEqual(block["refuted"], 1)
        self.assertEqual([f["location"] for f in block["findings"]], ["src/turnstile.py:4"])

    def test_one_finding_from_two_reviewers_is_listed_once_with_both(self):
        local_id = "run-0001-local-correctness"
        drive, run_dir, ws, info = vlib.through_outside(
            self.tmp, local_findings=[vlib.finding("src/turnstile.py:4", found_by=[local_id], claim="reset loses the count")],
            outside_findings=[vlib.finding("src/turnstile.py:4", found_by=[OUT_A], claim="reset loses the count")])
        self.verdict(drive, run_dir)
        block = forms.parse_doc(self.doc(ws))["blocks"][0]
        self.assertEqual(len(block["findings"]), 1)
        self.assertEqual(sorted(block["findings"][0]["reviewers"]), ["gpt-astra", "local:correctness"])
        self.assertEqual(block["verdict"], "SIGNED OFF WITH CONDITIONS")

    def test_repeats_and_misses_are_read_against_the_ledger(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=("gpt-astra",), outside_findings=[
            vlib.finding("src/turnstile.py:2", severity="MINOR", found_by=[OUT_A], claim="the counter skips a turn")])
        self.verdict(drive, run_dir)
        block = forms.parse_doc(self.doc(ws))["blocks"][0]
        self.assertEqual(len(block["repeats"]), 1)
        self.assertIn("fixed", block["repeats"][0])
        again = os.path.join(self.tmp, "again")
        os.makedirs(again)
        drive, run_dir, ws2, info = vlib.through_outside(again, rows=("gpt-astra",))
        self.verdict(drive, run_dir)
        block = forms.parse_doc(testlib.read_text(os.path.join(ws2, "docs", "reviews", DOC_NAME)))["blocks"][0]
        self.assertEqual(len(block["misses"]), 1)
        self.assertIn("src/turnstile.py:2", block["misses"][0])

    def test_the_method_line_names_the_outside_reviewer_and_the_dropped_one(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, statuses={"deepseek": "transport-failed"})
        self.verdict(drive, run_dir)
        method = forms.parse_doc(self.doc(ws))["blocks"][0]["method"]
        self.assertTrue(any(l.startswith("Outside: gpt-astra") and "parity:" in l and "isolation:" in l for l in method), method)
        self.assertTrue(any(l.startswith("Dropped: deepseek") and "transport-failed" in l for l in method), method)
        self.assertTrue(any(l.startswith("Local: ") for l in method), method)


class TheFixRoundOne(_Verdict):
    """C1A-1 (survivors continue), C1A-2 (a derived card that differs is named in the Method line), C1A-3
    (the withheld sentence) and C1A-6 (a staged name read back to its path) at the verdict."""

    def report(self, drive, run_dir):
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Signed off; nothing to fix."])
        self.assertEqual(code, 10, (out, err))
        return forms.parse_vertical(testlib.read_text(os.path.join(run_dir, "chat.md")))

    def test_the_only_named_row_dropped_reaches_a_verdict_and_is_named(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra",), dropped=("gpt-astra",))
        self.assertEqual(drive(["request", "--run-dir", run_dir, "--outside"])[0], 0)
        self.verdict(drive, run_dir)
        method = forms.parse_doc(self.doc(ws))["blocks"][0]["method"]
        dropped = [l for l in method if l.startswith("Dropped: ")]
        self.assertEqual(len(dropped), 1, method)
        self.assertIn("gpt-astra", dropped[0])
        self.assertIn("dropped at suggest", dropped[0])
        self.assertIn("unavailable", dropped[0])
        fields = self.report(drive, run_dir)
        self.assertEqual(fields["reviewers"], [])
        self.assertEqual([d["row"] for d in fields["dropped"]], ["gpt-astra"])
        self.assertIn("dropped at suggest", fields["dropped"][0]["why"])

    def test_a_dropped_row_beside_a_live_one_is_named_and_the_live_one_reviews(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=("gpt-astra", "gemini"), dropped=("gpt-astra",))
        self.verdict(drive, run_dir)
        method = forms.parse_doc(self.doc(ws))["blocks"][0]["method"]
        self.assertTrue(any(l.startswith("Outside: gemini") for l in method), method)
        self.assertTrue(any(l.startswith("Dropped: gpt-astra") and "dropped at suggest" in l for l in method), method)
        self.assertFalse(any(l == "Dropped: none" for l in method), method)
        fields = self.report(drive, run_dir)
        self.assertEqual(fields["reviewers"], ["gemini"])
        self.assertEqual([d["row"] for d in fields["dropped"]], ["gpt-astra"])

    def test_a_derived_card_that_differs_is_named_in_the_method_line_with_both_cards(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=(), repo={"doc_text": vlib.open_major_doc()})
        self.verdict(drive, run_dir)
        method = forms.parse_doc(self.doc(ws))["blocks"][0]["method"]
        cards = [l for l in method if l.startswith("Card: ")]
        self.assertEqual(len(cards), 1, method)
        self.assertIn("slice A", cards[0])
        self.assertIn("signed off with conditions", cards[0])
        self.assertIn("'signed off'", cards[0])

    def test_no_card_line_when_every_derived_card_agrees(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        self.verdict(drive, run_dir)
        method = forms.parse_doc(self.doc(ws))["blocks"][0]["method"]
        self.assertFalse(any(l.startswith("Card: ") for l in method), method)
        withheld = [l for l in method if l.startswith("Withheld from every packet")][0]
        self.assertIn("build assumptions, deviations, discovered", withheld)

    def test_a_finding_at_either_colliding_staged_name_reads_back_to_its_own_path(self):
        files = {"docs/a__b.md": "COLLIDE-ONE\n", "docs/a/b.md": "COLLIDE-TWO\n"}
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("deepseek",), repo={"extra_build_files": files})
        self.assertEqual(drive(["request", "--run-dir", run_dir, "--outside"])[0], 0)
        vlib.file_outside_sidecars(run_dir)
        packet = [p for p in vlib.load(run_dir, "scope.json")["packets"] if p["name"] == "outside-deepseek"][0]
        staged = dict((e.get("source"), os.path.basename(e["path"])) for e in testlib.load_json(packet["files"])["files"]
                      if e.get("source") in files)
        call = "run-0001-deepseek"
        answer = vlib.write(self.tmp, "outside-answer.json", vlib.outside_answer(run_dir, findings=[
            vlib.finding("%s:1" % staged["docs/a__b.md"], found_by=[call], claim="the first note is wrong"),
            vlib.finding("%s:1" % staged["docs/a/b.md"], found_by=[call], claim="the second note is wrong")]))
        code, out, err = drive(["record-outside", "--run-dir", run_dir, "--answer", answer])
        self.assertEqual(code, 0, (out, err))
        recorded = dict((f["claim"], f["location"]) for f in vlib.load(run_dir, "outside.json")["findings"])
        self.assertEqual(recorded, {"the first note is wrong": "docs/a__b.md:1", "the second note is wrong": "docs/a/b.md:1"})


class ThePhases(_Verdict):

    def test_the_verdict_waits_for_the_named_outside_fleet(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra",))
        code, out, err = drive(["verdict", "--run-dir", run_dir])
        self.assertEqual(code, 2, (out, err))
        self.assertIn("request --outside", err)

    def test_report_ends_the_run_with_the_vertical_block(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=("gpt-astra",))
        self.verdict(drive, run_dir)
        code, out, err = drive(["report", "--run-dir", run_dir, "--bottom-line", "Signed off; nothing to fix."])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("completed", None))
        chat = testlib.read_text(os.path.join(run_dir, "chat.md"))
        fields = forms.parse_vertical(chat)
        self.assertEqual(fields["verdict"], "SIGNED OFF")
        self.assertEqual(fields["reviewers"], ["gpt-astra"])
        self.assertEqual(fields["verdict_doc"], "docs/reviews/%s" % DOC_NAME)
        code, rout, rerr = testlib.run_script("validate-result.py", [os.path.join(run_dir, "result.json")])
        self.assertEqual(code, 0, rout + rerr)
        trace_check = testlib.run_script("validate-trace.py", [os.path.join(run_dir, "trace.jsonl")])
        self.assertEqual(trace_check[0], 0, trace_check[1] + trace_check[2])

    def test_report_needs_the_bottom_line(self):
        drive, run_dir, ws, info = vlib.through_outside(self.tmp, rows=())
        self.verdict(drive, run_dir)
        code, out, err = drive(["report", "--run-dir", run_dir])
        self.assertEqual(code, 2, (out, err))


class TheReceiptAtTheVerdict(_Verdict):
    """C1A3-5: `verdict` holds the run to the local receipt the way `request --outside` does, and refuses
    (exit 5, nothing written) when it fails: on a local-only run and after the outside fleet."""

    def local_with_a_finding(self, rows):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp, rows=rows)
        vlib.file_local_sidecars(run_dir)
        ids = vlib.local_ids(run_dir)
        code, out, err = vlib.record_local(drive, self.tmp, run_dir,
                                           findings=[vlib.finding("src/turnstile.py:2", found_by=[ids[0]])])
        self.assertEqual(code, 0, (out, err))
        return drive, run_dir, ws

    def drop_the_finding(self, run_dir):
        local = vlib.load(run_dir, "local.json")
        self.assertEqual(len(local["findings"]), 1)
        local["findings"] = []
        testlib.write_json(os.path.join(run_dir, "local.json"), local)

    def assert_refused(self, drive, run_dir, ws):
        code, out, err = drive(["verdict", "--run-dir", run_dir])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("record-local", out["reason"])
        self.assertEqual(vlib.verdict_docs(ws), [])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "verdict.json")))

    def test_a_local_record_edited_on_a_local_only_run(self):
        drive, run_dir, ws = self.local_with_a_finding(rows=())
        self.drop_the_finding(run_dir)
        self.assert_refused(drive, run_dir, ws)

    def test_a_local_record_edited_after_the_outside_fleet(self):
        drive, run_dir, ws = self.local_with_a_finding(rows=("gpt-astra",))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 0, (out, err))
        vlib.file_outside_sidecars(run_dir)
        answer = vlib.write(self.tmp, "outside-answer.json", vlib.outside_answer(run_dir))
        code, out, err = drive(["record-outside", "--run-dir", run_dir, "--answer", answer])
        self.assertEqual(code, 0, (out, err))
        self.drop_the_finding(run_dir)
        self.assert_refused(drive, run_dir, ws)

    def test_the_intact_record_reaches_the_verdict(self):
        drive, run_dir, ws = self.local_with_a_finding(rows=())
        out = self.verdict(drive, run_dir)
        self.assertEqual(out["findings"], 1)


class TheCopiesOnAStop(_Verdict):
    """C1A3-6: a run that stops after `scope` removes every packet's workspace and documents, the previews
    and the summons copies alike, when it stops (`report.finish`); the mandates and the two lists stay."""

    def assert_no_copies(self, run_dir, folders):
        seen = 0
        for folder in folders:
            for name in os.listdir(os.path.join(run_dir, folder)):
                seen += 1
                for part in ("workspace", "documents"):
                    self.assertFalse(os.path.exists(os.path.join(run_dir, folder, name, part)), (folder, name, part))
                for kept in ("mandate.md", "files.json", "withheld.json"):
                    self.assertTrue(os.path.isfile(os.path.join(run_dir, folder, name, kept)), (folder, name, kept))
        self.assertGreater(seen, 0)

    def test_a_floor_refused_stop_at_record_local(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        vlib.file_local_sidecars(run_dir, status="floor-refused")
        code, out, err = vlib.record_local(drive, self.tmp, run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "floor-refused"), (out, err))
        self.assert_no_copies(run_dir, ("packets", "summons"))

    def test_a_station_refused_stop_at_request(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        elsewhere = os.path.join(self.tmp, "elsewhere-readers")
        os.makedirs(elsewhere)
        code, out, err = drive(["request", "--run-dir", run_dir, "--readers-root", elsewhere])
        self.assertEqual((code, out["stop_tag"]), (10, "station-refused"), (out, err))
        self.assert_no_copies(run_dir, ("packets",))


def plant_outside(root):
    """A folder outside the run directory holding what a followed link would delete; returns its listing."""
    for part in ("workspace", "documents"):
        testlib.write_text(os.path.join(root, part, "precious.txt"), "keep me\n")
        testlib.write_text(os.path.join(root, "inner", part, "precious.txt"), "keep me\n")
    return files_under(root)


def files_under(root):
    out = []
    for base, dirs, files in os.walk(root):
        out += [os.path.relpath(os.path.join(base, name), root) for name in files]
    return sorted(out)


def plant_packet(run_dir, folder, name):
    for part in ("workspace", "documents"):
        testlib.write_text(os.path.join(run_dir, folder, name, part, "copy.txt"), "a copy\n")
    testlib.write_text(os.path.join(run_dir, folder, name, "mandate.md"), "the mandate\n")


class TheRemovalNeverFollowsALink(unittest.TestCase):
    """C1A4-3: removing the previews and the summons copies never follows a link. A link planted at
    `summons/<name>`, `packets/<name>`, `<folder>/<name>/workspace` or at `summons` or `packets` itself is
    removed as a link, never its target, and nothing outside the run directory is deleted; the real copies
    beside it are removed and the mandates stay."""

    def setUp(self):
        self.tmp = os.path.realpath(testlib.make_scratch("vlinks-"))
        self.addCleanup(testlib.rmtree, self.tmp)
        self.run_dir = os.path.join(self.tmp, "run")
        for folder in ("packets", "summons"):
            plant_packet(self.run_dir, folder, "local-spec" if folder == "packets" else "run-0001-spec")
        self.outside = os.path.join(self.tmp, "OUTSIDE")
        self.before = plant_outside(self.outside)

    def drop(self):
        report.drop_copies(types.SimpleNamespace(run_dir=self.run_dir))
        self.assertEqual(files_under(self.outside), self.before)
        for folder, name in (("packets", "local-spec"), ("summons", "run-0001-spec")):
            if os.path.isdir(os.path.join(self.run_dir, folder)) and not os.path.islink(os.path.join(self.run_dir, folder)):
                for part in ("workspace", "documents"):
                    self.assertFalse(os.path.lexists(os.path.join(self.run_dir, folder, name, part)), (folder, part))
                self.assertTrue(os.path.isfile(os.path.join(self.run_dir, folder, name, "mandate.md")))

    def test_a_link_at_a_summons_entry(self):
        link = os.path.join(self.run_dir, "summons", "evil")
        os.symlink(self.outside, link)
        self.drop()
        self.assertFalse(os.path.lexists(link))

    def test_a_link_at_a_packets_entry(self):
        link = os.path.join(self.run_dir, "packets", "evil")
        os.symlink(self.outside, link)
        self.drop()
        self.assertFalse(os.path.lexists(link))

    def test_a_link_at_a_copys_workspace(self):
        link = os.path.join(self.run_dir, "packets", "evil", "workspace")
        os.makedirs(os.path.dirname(link))
        os.symlink(os.path.join(self.outside, "workspace"), link)
        self.drop()
        self.assertFalse(os.path.lexists(link))

    def test_the_summons_folder_itself_a_link(self):
        testlib.rmtree(os.path.join(self.run_dir, "summons"))
        os.symlink(self.outside, os.path.join(self.run_dir, "summons"))
        self.drop()
        self.assertFalse(os.path.lexists(os.path.join(self.run_dir, "summons")))

    def test_the_packets_folder_itself_a_link(self):
        testlib.rmtree(os.path.join(self.run_dir, "packets"))
        os.symlink(os.path.join(self.outside, "inner"), os.path.join(self.run_dir, "packets"))
        self.drop()
        self.assertFalse(os.path.lexists(os.path.join(self.run_dir, "packets")))


class TheRemovalOnAStopThroughTheCli(_Verdict):
    """C1A4-3 through the real CLI, check 4's probe: links planted after `scope`, then a `station-refused` stop
    at `request`; the outside folders survive."""

    def test_links_in_summons_and_packets_are_never_followed_on_a_stop(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        outside = os.path.join(self.tmp, "OUTSIDE")
        before = plant_outside(outside)
        os.makedirs(os.path.join(run_dir, "summons"), exist_ok=True)
        os.symlink(outside, os.path.join(run_dir, "summons", "evil"))
        os.symlink(outside, os.path.join(run_dir, "packets", "evil"))
        elsewhere = os.path.join(self.tmp, "elsewhere-readers")
        os.makedirs(elsewhere)
        code, out, err = drive(["request", "--run-dir", run_dir, "--readers-root", elsewhere])
        self.assertEqual((code, out["stop_tag"]), (10, "station-refused"), (out, err))
        self.assertEqual(files_under(outside), before)


if __name__ == "__main__":
    unittest.main()
