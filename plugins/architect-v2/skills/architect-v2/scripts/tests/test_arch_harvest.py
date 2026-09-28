"""The input gate and `harvest` (lane contract section 10, brief 3.3, required test 3).

No scope doc: the docless path (harvest continues, the answer must carry the gate's question and
its reason). One scope doc: taken, its ledger emitted with ids. Two: `several`, the run stops
`selection-several` with both listed, never picked. An existing architecture doc: harvested with
its run count and its next run number. Every case writes nothing outside the run directory.
"""
import os
import unittest

import archlib
import testlib


class _Harvest(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-harvest-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(self.staging)


class OneScopeDoc(_Harvest):

    def test_the_ledger_is_emitted_with_ids(self):
        ws = archlib.repo_workspace(self.tmp)
        before = archlib.listing(ws)
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(doc["next"], "record-answer")
        self.assertFalse(doc["docless"])
        self.assertEqual(doc["slug"], "turnstile")
        self.assertEqual(doc["scope_doc"], os.path.join(ws, archlib.SCOPE_REL))
        i = archlib.ids()
        by_id = {row["id"]: row for row in doc["ledger"]}
        self.assertEqual(by_id[i["decided"]]["tag"], "decided")
        self.assertEqual(by_id[i["parked"]]["tag"], "parked")
        self.assertEqual(doc["target"], os.path.join(ws, "docs", "architecture", "%s-turnstile.md" % archlib.TODAY))
        self.assertIsNone(doc["living_doc"])
        harvest = testlib.load_json(os.path.join(run.run_dir, "harvest.json"))
        self.assertEqual([(r["id"], r["tag"], r["text"]) for r in harvest["ledger"]],
                         [(r["id"], r["tag"], r["text"]) for r in doc["ledger"]])
        self.assertEqual(archlib.listing(ws), before)

    def test_a_staged_scope_doc_targets_the_staging_home(self):
        ws = archlib.repo_workspace(self.tmp)
        os.remove(os.path.join(ws, archlib.SCOPE_REL))
        testlib.write_text(os.path.join(self.staging, "turnstile-scope.md"), archlib.SCOPE)
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(doc["target"], os.path.join(self.staging, "turnstile-architecture.md"))

    def test_the_architecture_hunt_must_name_the_scope_docs_slug(self):
        ws = archlib.repo_workspace(self.tmp)
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        code, doc, out, err = run.to_harvest(slug="other")
        self.assertEqual(code, 2, out + err)
        self.assertIn("turnstile", err)
        self.assertFalse(os.path.exists(os.path.join(run.run_dir, "harvest.json")))

    def test_harvest_before_select_is_usage(self):
        ws = archlib.repo_workspace(self.tmp)
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        self.assertEqual(run.check_input()[0], 0)
        code, doc, out, err = run.harvest()
        self.assertEqual(code, 2, out + err)


class NoScopeDoc(_Harvest):

    def test_the_docless_path(self):
        ws = testlib.git_workspace(self.tmp, "ws")
        before = archlib.listing(ws)
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        self.assertEqual(run.check_input()[0], 0)
        code, doc, out, err = run.select("scope")
        self.assertEqual((code, doc["outcome"]), (0, "none"))
        code, doc, out, err = run.select("architecture", "bench-counter")
        self.assertEqual(code, 0, err)
        code, doc, out, err = run.harvest()
        self.assertEqual(code, 0, out + err)
        self.assertTrue(doc["docless"])
        self.assertIsNone(doc["scope_doc"])
        self.assertEqual(doc["ledger"], [])
        self.assertEqual(doc["slug"], "bench-counter")
        self.assertIn("docless", doc["reason"])
        self.assertEqual(archlib.listing(ws), before)

    def test_docless_without_a_slug_is_usage(self):
        ws = testlib.git_workspace(self.tmp, "ws")
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        run.check_input()
        run.select("scope")
        run.select("architecture")
        code, doc, out, err = run.harvest()
        self.assertEqual(code, 2, out + err)


class TwoScopeDocs(_Harvest):

    def test_several_is_listed_never_picked(self):
        ws = archlib.repo_workspace(self.tmp, files={"docs/scope/2026-09-21-turnstile-two.md": archlib.SCOPE})
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        run.check_input()
        code, doc, out, err = run.select("scope")
        self.assertEqual(doc["outcome"], "several")
        run.select("architecture", "turnstile")
        code, doc, out, err = run.harvest()
        self.assertEqual(code, 10, out + err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "selection-several"))
        result = testlib.load_json(os.path.join(run.run_dir, "result.json"))
        self.assertEqual(result["stop_tag"], "selection-several")
        self.assertEqual(sorted(c["path"] for c in result["selection"]["scope"]["candidates"]),
                         sorted([os.path.join(ws, archlib.SCOPE_REL),
                                 os.path.join(ws, "docs/scope/2026-09-21-turnstile-two.md")]))
        self.assertIsNone(result["station_result"]["scope_doc"])
        self.assertFalse(os.path.exists(os.path.join(run.run_dir, "harvest.json")))
        code, doc, out, err = run.record(archlib.clean_answer())
        self.assertEqual(code, 2, "a stopped run takes no answer")

    def test_the_owner_pick_arrives_as_the_input_path(self):
        ws = archlib.repo_workspace(self.tmp, files={"docs/scope/2026-09-21-turnstile-two.md": archlib.SCOPE})
        run = archlib.ArchRun(self.tmp, ws, self.staging,
                              station={"scope_doc": os.path.join(ws, archlib.SCOPE_REL)})
        run.check_input()
        run.select("scope")
        run.select("architecture", "turnstile")
        code, doc, out, err = run.harvest()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(doc["scope_doc"], os.path.join(ws, archlib.SCOPE_REL))

    def test_an_input_path_outside_both_homes_is_usage(self):
        ws = archlib.repo_workspace(self.tmp)
        elsewhere = os.path.join(self.tmp, "elsewhere-scope.md")
        testlib.write_text(elsewhere, archlib.SCOPE)
        run = archlib.ArchRun(self.tmp, ws, self.staging, station={"scope_doc": elsewhere})
        run.check_input()
        run.select("architecture", "elsewhere")
        code, doc, out, err = run.harvest()
        self.assertEqual(code, 2, out + err)


class AnExistingArchitectureDoc(_Harvest):

    DOC = ("# Turnstile %(D)s architecture (2026-09-21)\n\n"
           "Scope doc: docs/scope/2026-09-20-turnstile.md\n"
           "Blind review: declined 2026-09-21\n"
           "Artifact: https://example.invalid/artifact/turnstile\n\n"
           "## Walkthrough target\n"
           "Who: Sam Bench  %(M)s  When: 2026-10-01  %(M)s  Must be able to: count turns\n\n"
           "## v0 drawing\nComponents: turnstile.py (serves: count turns)\nData flow: the fixture calls it\n"
           "Diagram: fixture -> turnstile.py\n\n"
           "## Poured concrete (one-way doors)\n- language %(D)s Python 3.9 %(D)s every bench script imports it\n\n"
           "## Deferred\n- a web dashboard %(D)s door stays open because the module has no I/O\n\n"
           "## Run log\n"
           "### Run 1 %(D)s 2026-09-21 %(D)s trigger: first run\n"
           "Exit ramp: system\nStep 3.1 (walkthrough target): Sam Bench\nStep 3.2 (candidates): module; service\n"
           "Step 3.3 (one-way doors): language\nRulings: declined\nChanged this run: first run\n\n"
           "### Run 2 %(D)s 2026-09-22 %(D)s trigger: idea blossomed\n"
           "Exit ramp: system\nStep 3.1 (walkthrough target): Sam Bench\nStep 3.2 (candidates): module; service\n"
           "Step 3.3 (one-way doors): language\nRulings: declined\nChanged this run: reset added\n") % {"D": archlib.D, "M": archlib.M}

    def test_harvested_with_its_run_count(self):
        ws = archlib.repo_workspace(self.tmp, files={"docs/architecture/2026-09-21-turnstile.md": self.DOC})
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 0, out + err)
        living = doc["living_doc"]
        self.assertEqual(living["path"], os.path.join(ws, "docs/architecture/2026-09-21-turnstile.md"))
        self.assertEqual(living["runs"], [1, 2])
        self.assertEqual(living["next_run"], 3)
        self.assertEqual(living["artifact_url"], "https://example.invalid/artifact/turnstile")
        self.assertEqual(doc["target"], living["path"])
        harvest = testlib.load_json(os.path.join(run.run_dir, "harvest.json"))
        self.assertEqual(harvest["living_doc"]["sha256"], archlib.sha(living["path"]))

    def test_a_living_doc_off_its_form_stops_the_run(self):
        broken = self.DOC.replace("## Deferred\n", "## Deferred things\n")
        ws = archlib.repo_workspace(self.tmp, files={"docs/architecture/2026-09-21-turnstile.md": broken})
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "living-doc-malformed")

    def test_a_free_line_under_poured_or_deferred_stops_the_run_naming_it(self):
        """CA1-11: a line the owner typed under Poured concrete or Deferred that is not a list line
        can be neither carried nor struck, so the run stops at harvest naming it, before any ask."""
        cases = (("## Deferred\n", "## Deferred\nthe owner's note on the dashboard\n"),
                 ("## Poured concrete (one-way doors)\n", "## Poured concrete (one-way doors)\n### a heading he added\n"))
        for index, (old, new) in enumerate(cases):
            ws = archlib.repo_workspace(self.tmp, files={"docs/architecture/2026-09-21-turnstile.md":
                                                        self.DOC.replace(old, new)}, name="ws-%d" % index)
            run = archlib.ArchRun(self.tmp, ws, self.staging, name="run-%d" % index)
            code, doc, out, err = run.to_harvest()
            self.assertEqual(code, 10, out + err)
            self.assertEqual(doc["stop_tag"], "living-doc-malformed")
            self.assertIn(new.split("\n")[1], doc["reason"])
            self.assertFalse(os.path.exists(os.path.join(run.run_dir, "harvest.json")))

    def test_a_hand_added_header_line_stops_the_run_naming_it(self):
        """The same dead end in the head: the header lines are this run's (Scope doc or Docless,
        Blind review, Artifact), so a line the owner added there could never be carried."""
        ws = archlib.repo_workspace(self.tmp, files={"docs/architecture/2026-09-21-turnstile.md": self.DOC.replace(
            "Blind review: declined 2026-09-21\n", "Blind review: declined 2026-09-21\nOwner: Sam Bench\n")},
            name="ws-head")
        run = archlib.ArchRun(self.tmp, ws, self.staging, name="run-head")
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "living-doc-malformed")
        self.assertIn("Owner: Sam Bench", doc["reason"])

    def test_a_line_holding_another_line_boundary_stops_the_run_naming_it(self):
        """Slice 3b R5 (CA7-3): every answer string refuses the line boundaries, so an item holding one other than LF
        could be neither carried nor struck: the run stops at harvest naming the line by its number and the
        character by its code point (never printed raw), nothing written, the doc left as found."""
        cases = (("- a\u2028- b", "U+2028"), ("- a web dashboard\x85later", "U+0085"), ("- a\vb", "U+000B"),
                 ("- a\x0cb", "U+000C"), ("- a\x1cb", "U+001C"), ("- a\u2029b", "U+2029"))
        for index, (item, point) in enumerate(cases):
            text = self.DOC.replace("## Deferred\n", "## Deferred\n%s\n" % item)
            number = text.split("\n").index(item) + 1
            ws = archlib.repo_workspace(self.tmp, files={"docs/architecture/2026-09-21-turnstile.md": text},
                                        name="ws-b%d" % index)
            before = archlib.listing(ws)
            run = archlib.ArchRun(self.tmp, ws, self.staging, name="run-b%d" % index)
            code, doc, out, err = run.to_harvest()
            self.assertEqual(code, 10, (point, out + err))
            self.assertEqual(doc["stop_tag"], "living-doc-malformed")
            self.assertIn("line %d: " % number, doc["reason"])
            self.assertIn(point, doc["reason"])
            self.assertIn("so no answer can carry or strike it", doc["reason"])
            self.assertIn("then start a new run", doc["reason"])
            self.assertFalse(any(ch in doc["reason"] for ch in item[2:] if not ch.isprintable()), point)
            self.assertFalse(os.path.exists(os.path.join(run.run_dir, "harvest.json")))
            self.assertEqual(archlib.listing(ws), before)

    def test_a_crlf_doc_keeps_its_one_cr_finding(self):
        """CR and LF are no other boundary: a CRLF doc still stops on its one CR finding, as before R5."""
        ws = archlib.repo_workspace(self.tmp, files={"docs/architecture/2026-09-21-turnstile.md":
                                                    self.DOC.replace("\n", "\r\n")}, name="ws-crlf")
        run = archlib.ArchRun(self.tmp, ws, self.staging, name="run-crlf")
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "living-doc-malformed")
        self.assertIn("the doc has CR line endings; this core continues LF documents only", doc["reason"])
        self.assertNotIn("line boundary other than LF", doc["reason"])

    def test_two_living_docs_are_several(self):
        ws = archlib.repo_workspace(self.tmp, files={"docs/architecture/2026-09-21-turnstile.md": self.DOC,
                                                    "docs/architecture/2026-09-22-turnstile.md": self.DOC})
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "selection-several")


class ALedgerTheReaderRefuses(_Harvest):

    def test_ledger_refused(self):
        bad = archlib.SCOPE.replace("- One module, no package", "One module, no package")
        ws = archlib.repo_workspace(self.tmp, files={archlib.SCOPE_REL: bad})
        run = archlib.ArchRun(self.tmp, ws, self.staging)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "ledger-refused")
        self.assertIn("One module", doc["reason"])


class ADocThatIsNotUtf8(_Harvest):
    """Slice 3b round 2 R2 (CA3B-2): a scope doc or a living doc holding a byte that is not UTF-8 stops the run
    with its tag (`ledger-refused` for the scope doc, `living-doc-malformed` for the living doc), the sentence
    naming the doc and the error; never a traceback, and nothing is written outside the run directory."""

    def latin(self, ws, rel, old, new):
        path = os.path.join(ws, rel)
        with open(path, "rb") as fh:
            data = fh.read()
        self.assertIn(old, data)
        with open(path, "wb") as fh:
            fh.write(data.replace(old, new, 1))
        return path

    def stopped(self, run, ws, tag, path):
        before = archlib.listing(ws)
        code, doc, out, err = run.to_harvest(**self.to_harvest)
        self.assertEqual(code, 10, out + err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(doc["stop_tag"], tag)
        self.assertIn("%s is not UTF-8 (" % path, doc["reason"])
        self.assertIn("the doc is left as found: save it as UTF-8, then start a new run", doc["reason"])
        self.assertEqual(archlib.listing(ws), before)
        self.assertFalse(os.path.exists(os.path.join(run.run_dir, "harvest.json")))
        self.assertFalse(os.path.exists(os.path.join(run.run_dir, "harvested-doc.md")))

    to_harvest = {}

    def test_a_scope_doc_that_is_not_utf8_is_ledger_refused(self):
        ws = archlib.repo_workspace(self.tmp)
        path = self.latin(ws, archlib.SCOPE_REL, b"bench rig", b"bench r\xefg")
        self.stopped(archlib.ArchRun(self.tmp, ws, self.staging), ws, "ledger-refused", path)

    def test_a_living_doc_that_is_not_utf8_is_living_doc_malformed(self):
        from test_arch_record import LIVING, LIVING_REL
        ws = archlib.repo_workspace(self.tmp, files={LIVING_REL: LIVING})
        path = self.latin(ws, LIVING_REL, b"a web dashboard", b"a web dashb\xf6ard")
        self.stopped(archlib.ArchRun(self.tmp, ws, self.staging), ws, "living-doc-malformed", path)

    def test_a_docless_runs_living_doc_that_is_not_utf8_is_living_doc_malformed(self):
        """No scope doc read, so the doc that is not UTF-8 is the living doc, and its tag says so."""
        from test_arch_record import LIVING
        rel = "docs/architecture/2026-09-21-bench-counter.md"
        ws = testlib.git_workspace(self.tmp, "plain", {"README.md": "# A project\n", rel: LIVING})
        path = self.latin(ws, rel, b"a web dashboard", b"a web dashb\xf6ard")
        self.to_harvest = {"slug": "bench-counter", "scope": True}
        self.stopped(archlib.ArchRun(self.tmp, ws, self.staging), ws, "living-doc-malformed", path)


if __name__ == "__main__":
    unittest.main()
