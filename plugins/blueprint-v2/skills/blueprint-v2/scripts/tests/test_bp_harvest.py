"""blueprint-v2's `harvest` (lane L, brief 3.3 and required test 4).

The scope doc's ledger with its ids; the architecture doc's poured-concrete and deferred lines;
an existing build doc's `Status:` lines, `Plan: inspected` lines and five ledger sections captured
byte for byte; the run date; the stops (`selection-several`, `ledger-refused`) and the usage slips
(a hunt not run, a build hunt with no name, the wrong phase).
"""
import os
import unittest

import bplib
import testlib

testlib.add_scripts_to_path()

from station_core import ledger  # noqa: E402


class _Harvest(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("bp-harvest-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def run_for(self, files, **kw):
        ws = testlib.git_workspace(self.tmp, "ws", files)
        run = bplib.Run(self.tmp, ws, **kw)
        run.check_input()
        return run


class TheLedger(_Harvest):

    def test_every_ledger_line_with_its_id_tag_and_text(self):
        run = self.run_for(bplib.base_files())
        run.select_all()
        code, out, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertEqual(out["next"], "record-answer")
        expected = [(row["id"], row["tag"], row["text"]) for row in ledger.read(bplib.SCOPE)]
        got = [(row["id"], row["tag"], row["text"]) for row in out["scope"]["ledger"]]
        self.assertEqual(got, expected)
        saved = testlib.load_json(os.path.join(run.run_dir, "harvest.json"))
        self.assertEqual([r["id"] for r in saved["scope"]["ledger"]], [r[0] for r in expected])
        self.assertEqual(saved["scope"]["path"], os.path.join(run.ws, bplib.SCOPE_PATH))
        self.assertRegex(saved["run_date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(saved["target"], os.path.join(run.ws, "docs", "plans",
                                                       "%s-turnstile.md" % saved["run_date"]))
        self.assertIsNone(saved["build"])

    def test_no_scope_doc_is_an_empty_ledger_not_a_stop(self):
        run = self.run_for(bplib.base_files(scope=False))
        run.select_all()
        code, out, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertIsNone(out["scope"])

    def test_an_untaggable_line_stops_ledger_refused_quoting_it(self):
        bad = bplib.SCOPE.replace("- One module, no package %s assumed (small and reversible)" % bplib.D,
                                  "- One module, no package")
        run = self.run_for(dict(bplib.base_files(), **{bplib.SCOPE_PATH: bad}))
        run.select_all()
        code, out, err = run.harvest()
        self.assertEqual(code, 10, err)
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "ledger-refused"))
        self.assertIn("- One module, no package", out["reason"])
        self.assertTrue(os.path.isfile(os.path.join(run.run_dir, "result.json")))


class TheArchitectureDoc(_Harvest):

    def test_poured_concrete_and_deferred_lines_with_ids(self):
        run = self.run_for(bplib.base_files(arch=True))
        run.select_all()
        code, out, err = run.harvest()
        self.assertEqual(code, 0, err)
        arch = out["architecture"]
        self.assertEqual(arch["path"], os.path.join(run.ws, bplib.ARCH_PATH))
        self.assertEqual([p["text"] for p in arch["poured"]],
                         ["language %s Python 3.9 %s every caller imports it" % (bplib.D, bplib.D)])
        self.assertEqual([p["text"] for p in arch["struck"]],
                         ["~~storage %s a file %s superseded~~" % (bplib.D, bplib.D)])
        self.assertEqual([p["text"] for p in arch["deferred"]], ["a web view %s the module has no I/O" % bplib.D])
        self.assertTrue(all(p["id"].startswith("arch-") for p in arch["poured"]))
        self.assertTrue(all(p["id"].startswith("defer-") for p in arch["deferred"]))


class AMalformedArchitectureDoc(_Harvest):
    """R4 (CL1-3): a poured-concrete or deferred section the reader cannot read whole is refused at
    harvest (`ledger-refused`, the lines quoted), never dropped."""

    POURED = "## Poured concrete (one-way doors)"
    ITEM = "- language %s Python 3.9 %s every caller imports it" % (bplib.D, bplib.D)
    DEFER = "- a web view %s the module has no I/O" % bplib.D

    def harvest_arch(self, arch):
        run = self.run_for(dict(bplib.base_files(), **{bplib.ARCH_PATH: arch}))
        run.select_all()
        return run, run.harvest()

    def test_each_malformed_shape_stops_ledger_refused_quoting_it(self):
        A = bplib.ARCH
        shapes = [
            ("re-cased poured heading", A.replace(self.POURED, "## poured concrete (one-way doors)"),
             "## poured concrete (one-way doors)"),
            ("poured heading without its suffix", A.replace(self.POURED, "## Poured concrete"), "## Poured concrete"),
            ("indented poured item", A.replace(self.ITEM, "  " + self.ITEM), "  " + self.ITEM),
            ("star poured item", A.replace(self.ITEM, "*" + self.ITEM[1:]), "*" + self.ITEM[1:]),
            ("blank poured item", A.replace(self.ITEM + "\n", self.ITEM + "\n- \n"), "'- '"),
            ("a poured line with no dash", A.replace(self.ITEM, self.ITEM[2:]), self.ITEM[2:]),
            ("re-cased deferred heading", A.replace("## Deferred", "## deferred"), "## deferred"),
            ("indented deferred item", A.replace(self.DEFER, "  " + self.DEFER), "  " + self.DEFER),
        ]
        for label, arch, quoted in shapes:
            self.tmp_reset()
            run, (code, out, err) = self.harvest_arch(arch)
            self.assertEqual(code, 10, (label, out, err))
            self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "ledger-refused"), label)
            self.assertIn(quoted, out["reason"], label)
            self.assertIn(bplib.ARCH_PATH, out["reason"], label)
            self.assertFalse(os.path.exists(os.path.join(run.run_dir, "harvest.json")), label)

    def test_a_subheading_inside_the_poured_section_passes_and_its_items_are_read(self):
        arch = bplib.ARCH.replace(self.POURED + "\n", self.POURED + "\n### the language\n")
        run, (code, out, err) = self.harvest_arch(arch)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual([p["text"] for p in out["architecture"]["poured"]], [self.ITEM[2:]])

    def test_the_well_formed_doc_is_read_with_nothing_refused(self):
        run, (code, out, err) = self.harvest_arch(bplib.ARCH)
        self.assertEqual(code, 0, (out, err))
        self.assertNotIn("refused", out["architecture"])

    def test_an_unrelated_section_is_passed_over_whatever_its_words(self):
        # round 3, R5 (CL2-3): the two sections are known by their exact heading text, never by a word
        for heading in ("## Why we deferred the cache", "## Notes", "## Poured concrete notes",
                        "## Deferred decisions, a history"):
            self.tmp_reset()
            arch = bplib.ARCH.replace("## Run log\n", "%s\n- a line of prose about it\n\n## Run log\n" % heading)
            run, (code, out, err) = self.harvest_arch(arch)
            self.assertEqual(code, 0, (heading, out, err))
            self.assertEqual([p["text"] for p in out["architecture"]["poured"]], [self.ITEM[2:]], heading)
            self.assertEqual([p["text"] for p in out["architecture"]["deferred"]], [self.DEFER[2:]], heading)

    def test_a_missing_section_quotes_the_near_miss_heading(self):
        self.tmp_reset()
        run, (code, out, err) = self.harvest_arch(bplib.ARCH.replace("## Deferred\n", "## deferred\n"))
        self.assertEqual((code, out["stop_tag"]), (10, "ledger-refused"), out)
        self.assertIn("'## deferred'", out["reason"])
        self.assertIn("missing the section '## Deferred'", out["reason"])

    def tmp_reset(self):
        testlib.rmtree(self.tmp)
        os.makedirs(self.tmp)


class TheExistingBuildDoc(_Harvest):

    def test_protected_lines_are_captured_byte_for_byte(self):
        run = self.run_for(bplib.base_files(build=bplib.BUILD_FILLED))
        run.select_all()
        code, out, err = run.harvest()
        self.assertEqual(code, 0, err)
        build = out["build"]
        self.assertEqual(build["path"], os.path.join(run.ws, bplib.BUILD_PATH))
        self.assertEqual(build["sha256"], testlib.sha256_file(build["path"]))
        self.assertEqual([(s["name"], s["short"], s["status_line"]) for s in build["slices"]],
                         [("A", "Count turns", "Status: in progress")])
        self.assertEqual(build["stamps"],
                         ["Plan: inspected 2026-09-23 by gpt-6-astra %s 0 BLOCKER %s 1 MAJOR %s 0 MINOR"
                          % (bplib.M, bplib.M, bplib.M)])
        tail = bplib.BUILD_FILLED[bplib.BUILD_FILLED.index("## Build assumptions"):]
        self.assertEqual("".join(build["ledger_lines"]), tail)
        self.assertEqual(build["form_findings"], [])
        saved = testlib.load_json(os.path.join(run.run_dir, "harvest.json"))
        self.assertEqual(saved["target"], build["path"])

    def test_crlf_lines_keep_their_endings(self):
        crlf = bplib.BUILD_FILLED.replace("\n", "\r\n")
        run = self.run_for({"README.md": "x\n"})
        testlib.write_text(os.path.join(run.ws, bplib.BUILD_PATH), crlf, newline="")
        run.select_all()
        code, out, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertEqual("".join(out["build"]["ledger_lines"]), crlf[crlf.index("## Build assumptions"):])


class Stops(_Harvest):

    def test_several_scope_docs_stop_selection_several_listing_both(self):
        run = self.run_for(dict(bplib.base_files(), **{"docs/turnstile-scope.md": bplib.SCOPE}))
        run.select_all()
        code, out, err = run.harvest()
        self.assertEqual(code, 10, err)
        self.assertEqual(out["stop_tag"], "selection-several")
        self.assertIn(bplib.SCOPE_PATH, out["reason"])
        self.assertIn("docs/turnstile-scope.md", out["reason"])
        self.assertEqual(testlib.load_json(os.path.join(run.run_dir, "checkpoint.json"))["phase"], "done")

    def test_the_owners_choice_lets_harvest_take_it(self):
        run = self.run_for(dict(bplib.base_files(), **{"docs/turnstile-scope.md": bplib.SCOPE}))
        run.select_all()
        path = os.path.join(run.ws, "docs/turnstile-scope.md")
        code, out, err = run.cli(["choose", "--run-dir", run.run_dir, "--hunt", "scope", "--path", path,
                                  "--words", "the flat one"])
        self.assertEqual(code, 0, err)
        code, out, err = run.harvest()
        self.assertEqual(code, 0, err)
        self.assertEqual(out["scope"]["path"], path)
        self.assertEqual(out["scope"]["chosen_by_owner"], "the flat one")

    def test_a_terminal_run_answers_its_recorded_result(self):
        run = self.run_for(dict(bplib.base_files(), **{"docs/turnstile-scope.md": bplib.SCOPE}))
        run.select_all()
        first = run.harvest()
        again = run.harvest()
        self.assertEqual((again[0], again[1]), (10, first[1]))


class UsageSlips(_Harvest):

    def test_a_hunt_not_run_is_usage(self):
        run = self.run_for(bplib.base_files())
        run.select("scope")
        run.select("build", "turnstile")
        code, out, err = run.harvest()
        self.assertEqual(code, 2)
        self.assertIn("architecture", err)
        self.assertFalse(os.path.exists(os.path.join(run.run_dir, "harvest.json")))

    def test_a_build_hunt_with_no_name_is_usage(self):
        run = self.run_for(bplib.base_files())
        run.select("scope")
        run.select("architecture")
        run.select("build")
        code, out, err = run.harvest()
        self.assertEqual(code, 2)
        self.assertIn("--name", err)

    def test_harvest_before_select_is_usage(self):
        run = self.run_for(bplib.base_files())
        code, out, err = run.harvest()
        self.assertEqual(code, 2)
        self.assertIn("select", err)

    def test_a_selected_doc_that_vanished_or_is_not_utf8_is_usage(self):
        run = self.run_for(bplib.base_files(build=bplib.BUILD_FILLED))
        run.select_all()
        os.remove(os.path.join(run.ws, bplib.SCOPE_PATH))
        code, out, err = run.harvest()
        self.assertEqual(code, 2, err)
        self.assertIn("select --hunt scope", err)
        self.assertFalse(os.path.exists(os.path.join(run.run_dir, "harvest.json")))
        with open(os.path.join(run.ws, bplib.BUILD_PATH), "wb") as fh:
            fh.write(b"# \xff\xfe not text\n")
        run.select("scope")
        code, out, err = run.harvest()
        self.assertEqual(code, 2, err)
        self.assertIn("select --hunt build", err)

    def test_harvest_twice_is_usage(self):
        run = self.run_for(bplib.base_files())
        run.select_all()
        self.assertEqual(run.harvest()[0], 0)
        self.assertEqual(run.harvest()[0], 2)


if __name__ == "__main__":
    unittest.main()
