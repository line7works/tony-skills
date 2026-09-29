"""`harvest` and `packet` (lane contract section 4, required test 4), through the real CLI.

harvest: the code book resolved as a v2 sibling by route 3a (this checkout) and 3b (an installed-
shape copy); the records component confirmed at interface version 2, and exit 3 with one line on
stderr and nothing on stdout when it is missing, speaks another version, or the test hook makes
the real failure happen; the gate's stops (no build doc, several unresolved, an unreadable doc, no
code book). packet: one fresh directory per lens holding exactly `build-doc.md`, `scope-doc.md` (or
`no-record.md`) and `code-book.md`, each line-numbered `N: `.
"""
import os
import re
import shutil
import unittest

import ilib
import testlib

RECORDS = testlib.records_root()
NEEDS_CHECKOUT = testlib.checkout_sibling("blueprint-v2") is None or RECORDS is None or \
    testlib.checkout_sibling("readers") is None
SKIP = "the installed shape: no blueprint-v2, records or readers beside this core"


@unittest.skipIf(NEEDS_CHECKOUT, SKIP)
class _Run(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("harvest-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def run_for(self, **kw):
        ws = ilib.workspace(self.tmp, **{k: v for k, v in kw.items() if k in ("build", "scope", "extra")})
        run = ilib.Runner(self.tmp, ws, driver=kw.get("driver"), env=kw.get("env"))
        return run


class TheReadersRosterRoutes(_Run):
    """A7 section 5 (R5): `packet` and `request` find readers' roster through the shared resolver
    (`station_core/readers_roster.py`); the argument route, 3a, 3b and the missing case exit as before,
    and nothing found (or an unreadable roster) is this core's exit 3, one line naming every place looked."""

    def packet(self, *args, **kw):
        run = self.run_for(**kw)
        self.assertEqual(run.upto("harvest")[0], 0)
        return run, run.phase("packet", *args)

    def test_the_argument_route(self):
        run, (code, doc, out, err) = self.packet("--readers-root", testlib.checkout_sibling("readers"))
        self.assertEqual(code, 0, out + err)
        self.assertEqual(run.artifact("packet.json")["readers"]["route"], "argument")

    def test_an_unusable_argument_is_passed_over_for_route_3a(self):
        bogus = os.path.join(self.tmp, "not-readers")
        os.makedirs(bogus)
        run, (code, doc, out, err) = self.packet("--readers-root", bogus)
        self.assertEqual(code, 0, out + err)
        found = run.artifact("packet.json")["readers"]
        self.assertEqual(found["route"], "3a")
        self.assertIn("%s (no plugin.json)" % bogus, found["looked"])

    def test_route_3a_in_this_checkout(self):
        run, (code, doc, out, err) = self.packet()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(run.artifact("packet.json")["readers"]["route"], "3a")

    def test_route_3b_in_the_installed_shape(self):
        run, (code, doc, out, err) = self.packet(driver=ilib.installed_shape(self.tmp))
        self.assertEqual(code, 0, out + err)
        found = run.artifact("packet.json")["readers"]
        self.assertEqual(found["route"], "3b")
        self.assertIn(os.path.join("cache", "local", "readers"), os.path.normpath(found["root"]))

    def test_no_readers_is_exit_3_naming_every_place_looked(self):
        run, (code, doc, out, err) = self.packet(driver=ilib.installed_shape(self.tmp, with_readers=False))
        self.assertEqual((code, out), (3, ""), err)
        self.assertTrue(err.startswith("missing dependency: readers component (looked in: "), err)
        self.assertIn("%s (no such directory)" % os.path.join(os.pardir, os.pardir, "readers"), err)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertFalse(os.path.exists(os.path.join(run.run_dir, "packet.json")))

    def test_an_unreadable_roster_is_exit_3(self):
        driver = ilib.installed_shape(self.tmp)
        base = os.path.join(self.tmp, "cache", "local", "readers")
        (version,) = os.listdir(base)
        testlib.write_text(os.path.join(base, version, "skills", "readers", "assets", "roster.json"), "{not json\n")
        run, (code, doc, out, err) = self.packet(driver=driver)
        self.assertEqual((code, out), (3, ""), err)
        self.assertIn("has no readable roster", err)


class Harvest(_Run):

    def test_the_code_book_by_route_3a_and_the_records_confirmed(self):
        run = self.run_for()
        code, doc, out, err = run.upto("harvest")
        self.assertEqual(code, 0, out + err)
        harvest = run.artifact("harvest.json")
        self.assertEqual(harvest["code_book"]["route"], "3a")
        self.assertTrue(harvest["code_book"]["path"].endswith(
            os.path.join("blueprint-v2", "skills", "blueprint-v2", "SKILL.md")))
        self.assertEqual(harvest["records"]["interface_version"], 2)
        self.assertEqual(harvest["build_doc"]["rel"], ilib.BUILD_REL)
        self.assertEqual(harvest["scope_doc"]["rel"], ilib.SCOPE_REL)
        self.assertFalse(harvest["no_record"])
        self.assertEqual([s["name"] for s in harvest["slices"]], ["A"])
        self.assertEqual(harvest["records"]["head"], "0" * 64)
        self.assertEqual(doc["next"], "packet")

    def test_the_code_book_by_route_3b_in_the_installed_shape(self):
        driver = ilib.installed_shape(self.tmp)
        run = self.run_for(driver=driver)
        code, doc, out, err = run.upto("harvest")
        self.assertEqual(code, 0, out + err)
        harvest = run.artifact("harvest.json")
        self.assertEqual(harvest["code_book"]["route"], "3b")
        self.assertIn(os.path.join("cache", "local", "blueprint-v2"), harvest["code_book"]["path"])

    def test_no_code_book_is_a_stop(self):
        driver = ilib.installed_shape(self.tmp, with_code_book=False)
        run = self.run_for(driver=driver)
        code, doc, out, err = run.upto("harvest")
        self.assertEqual(code, 10, out + err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "code-book-missing"))
        self.assertIn("blueprint-v2", doc["reason"])

    def test_no_records_component_is_exit_3(self):
        driver = ilib.installed_shape(self.tmp, with_records=False)
        run = self.run_for(driver=driver)
        code, doc, out, err = run.upto("harvest")
        self.assertEqual((code, out), (3, ""), err)
        self.assertTrue(err.startswith("missing dependency: records component"), err)
        self.assertEqual(len(err.strip().splitlines()), 1)

    def test_the_test_hook_makes_the_real_failure_happen(self):
        run = self.run_for(env={"INSPECT_V2_TEST_NO_RECORDS": "1"})
        code, doc, out, err = run.upto("harvest")
        self.assertEqual((code, out), (3, ""), err)
        self.assertIn("INSPECT_V2_TEST_NO_RECORDS=1", err)

    def test_the_hook_is_ignored_outside_test_mode(self):
        run = self.run_for(env={"INSPECT_V2_TEST": "0", "INSPECT_V2_TEST_NO_RECORDS": "1"})
        code, doc, out, err = run.upto("harvest")
        self.assertEqual(code, 0, out + err)

    def test_a_component_at_another_interface_version_is_exit_3(self):
        fake = os.path.join(self.tmp, "records-v1")
        shutil.copytree(RECORDS, fake, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "fixtures"))
        script = os.path.join(fake, "scripts", "records.py")
        text = testlib.read_text(script)
        changed = re.sub(r"\nINTERFACE_VERSION = \d+\n", "\nINTERFACE_VERSION = 1\n", text, count=1)
        self.assertNotEqual(changed, text)
        testlib.write_text(script, changed)
        run = self.run_for()
        run.upto("select-scope")
        code, doc, out, err = run.phase("harvest", "--records-root", fake)
        self.assertEqual((code, out), (3, ""), err)
        self.assertIn("speaks interface version 1, not 2", err)

    def test_no_build_doc_is_selection_none(self):
        run = self.run_for(build=None)
        code, doc, out, err = run.upto("harvest")
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "selection-none")
        self.assertTrue(os.path.isfile(os.path.join(run.run_dir, "result.json")))

    def test_several_build_docs_stop_listed_and_a_choice_continues(self):
        run = self.run_for(extra={"docs/plans/2026-09-23-turnstile.md": ilib.BUILD_DOC})
        code, doc, out, err = run.upto("harvest")
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "selection-several")
        self.assertIn("2026-09-23-turnstile.md", doc["reason"])
        other = ilib.Runner(self.tmp, run.ws, run_dir=os.path.join(self.tmp, "run2"))
        other.upto("select-scope", doc=ilib.make_input(run.ws, other.run_dir, run_id="run-0002"))
        code, doc, out, err = other.phase("choose", "--hunt", "build", "--path",
                                          os.path.join(run.ws, ilib.BUILD_REL), "--by", "owner",
                                          "--words", "the 22nd")
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = other.phase("harvest")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(other.artifact("harvest.json")["build_doc"]["rel"], ilib.BUILD_REL)

    def test_several_scope_docs_unresolved_stop(self):
        run = self.run_for(extra={"docs/turnstile-scope.md": ilib.SCOPE_DOC})
        code, doc, out, err = run.upto("harvest")
        self.assertEqual((code, doc["stop_tag"]), (10, "selection-several"), out + err)

    def test_harvest_needs_both_hunts(self):
        run = self.run_for()
        run.upto("select-build")
        code, doc, out, err = run.phase("harvest")
        self.assertEqual(code, 2, out + err)
        self.assertIn("select --hunt scope", err)

    def test_no_scope_doc_is_the_no_record_rule(self):
        run = self.run_for(scope=None)
        code, doc, out, err = run.upto("harvest")
        self.assertEqual(code, 0, out + err)
        harvest = run.artifact("harvest.json")
        self.assertTrue(harvest["no_record"])
        self.assertIsNone(harvest["scope_doc"])

    def test_an_untaggable_scope_line_is_quoted_and_the_plan_still_inspected(self):
        scope = ilib.SCOPE_DOC.replace("- One module, no package", "- One module with no tag at all\n- One module, no package")
        run = self.run_for(scope=scope)
        code, doc, out, err = run.upto("harvest")
        self.assertEqual(code, 0, out + err)
        ledger = run.artifact("harvest.json")["ledger"]
        self.assertEqual(ledger["lines"], [])
        self.assertEqual([r["raw"] for r in ledger["refused"]], ["- One module with no tag at all"])

    def test_construction_already_started_is_noted(self):
        run = self.run_for(build=ilib.BUILD_DOC.replace("Status: not started", "Status: built"))
        code, doc, out, err = run.upto("harvest")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(run.artifact("harvest.json")["construction_started"], ["A"])


class Packet(_Run):

    def lens_dirs(self, run):
        return run.artifact("packet.json")["dirs"]

    def test_three_lenses_three_files_each_numbered(self):
        run = self.run_for()
        code, doc, out, err = run.upto("packet")
        self.assertEqual(code, 0, out + err)
        dirs = self.lens_dirs(run)
        self.assertEqual([d["lens"] for d in dirs], ["traceability", "code-book", "repo-reality"])
        book = testlib.read_text(run.artifact("harvest.json")["code_book"]["path"])
        for entry in dirs:
            self.assertTrue(entry["dir"].startswith(run.run_dir + os.sep))
            self.assertEqual(sorted(os.listdir(entry["dir"])), ["build-doc.md", "code-book.md", "scope-doc.md"])
            self.assertEqual(entry["files"], ["build-doc.md", "code-book.md", "scope-doc.md"])
            self.assertEqual(testlib.read_text(os.path.join(entry["dir"], "build-doc.md")), ilib.numbered(ilib.BUILD_DOC))
            self.assertEqual(testlib.read_text(os.path.join(entry["dir"], "scope-doc.md")), ilib.numbered(ilib.SCOPE_DOC))
            self.assertEqual(testlib.read_text(os.path.join(entry["dir"], "code-book.md")), ilib.numbered(book))
        self.assertEqual(len(set(d["dir"] for d in dirs)), 3, "one fresh directory per lens")
        self.assertEqual(doc["dirs"], [{"lens": d["lens"], "dir": d["dir"], "files": d["files"]} for d in dirs])

    def test_no_scope_doc_gives_no_record_md(self):
        run = self.run_for(scope=None)
        code, doc, out, err = run.upto("packet")
        self.assertEqual(code, 0, out + err)
        for entry in self.lens_dirs(run):
            self.assertEqual(sorted(os.listdir(entry["dir"])), ["build-doc.md", "code-book.md", "no-record.md"])
            self.assertEqual(testlib.read_text(os.path.join(entry["dir"], "no-record.md")),
                             "1: NO RECORD \u2014 no scope doc exists for this feature.\n")

    def test_an_outside_row_has_the_paper_lens_and_repo_reality(self):
        run = self.run_for()
        doc = ilib.make_input(run.ws, run.run_dir, row="gpt-astra")
        code, out_doc, out, err = run.upto("packet", doc=doc)
        self.assertEqual(code, 0, out + err)
        self.assertEqual([d["lens"] for d in self.lens_dirs(run)], ["paper", "repo-reality"])

    def test_no_row_in_the_input_is_usage(self):
        run = self.run_for()
        code, doc, out, err = run.upto("packet", doc=ilib.make_input(run.ws, run.run_dir, row=None))
        self.assertEqual(code, 2, out + err)
        self.assertIn("station.row", err)

    def test_a_second_packet_is_refused(self):
        run = self.run_for()
        run.upto("request")
        code, doc, out, err = run.phase("packet")
        self.assertEqual(code, 2, out + err)

    def test_a_crlf_doc_numbers_its_lines_as_an_editor_does(self):
        run = self.run_for(build=ilib.BUILD_DOC.replace("\n", "\r\n"))
        code, doc, out, err = run.upto("packet")
        self.assertEqual(code, 0, out + err)
        text = testlib.read_text(os.path.join(self.lens_dirs(run)[0]["dir"], "build-doc.md"))
        self.assertEqual(len(text.splitlines()), len(ilib.BUILD_DOC.splitlines()))


if __name__ == "__main__":
    unittest.main()
