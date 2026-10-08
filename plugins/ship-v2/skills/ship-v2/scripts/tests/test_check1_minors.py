"""Slice 2 check 1's MINOR findings C2-3 to C2-8, each by the checker's replacement (contract sections 3.4 to 3.8, 4).

C2-3: ignored files are not in the pin, as build-v2's; the contract says so. C2-4: a recheck-v2 result for another
slice, doc or version (its `checklist` and `run.skill`) is refused. C2-5: the `SKILL.md` ship-v2 hands the executor
resolves inside the station root and is a regular file, or the station is refused (a `refused` line). C2-6: a visit
whose station leaves no result, or a refused one, still reaches a terminal status: `report` at `visiting` ends the run
`visit-unfinished`. C2-7: whitespace-only owner words are refused. C2-8: the `invocation.mode` handed over is one the
station's own input schema accepts.
"""
import os
import unittest

import slib
import testlib


def fixed_run(test, tmp, ws, tree):
    drive, run_dir = slib.start(test, tree, tmp, ws)
    slib.through_hook(test, drive, tmp, run_dir)
    code, visit, err = slib.visit(test, drive, run_dir, "build-v2", "completed", ws)
    finding = slib.raise_finding(tmp, ws)
    code, out, err = slib.visit(test, drive, run_dir, "signoff-v2", "findings", ws)
    test.assertEqual((code, out["next"]), (0, "fix"), (out, err))
    testlib.write_text(os.path.join(ws, "src", "turnstile.py"), "def spin(count):\n    return count + 2\n")
    code, out, err = drive(["fix", "--run-dir", run_dir, "--fixes", slib.fixes_file(
        tmp, run_dir, 1, [{"finding": finding, "paths": ["src/turnstile.py"], "summary": "the fix"}])])
    test.assertEqual((code, out["next"]), (0, "visit --station recheck-v2"), (out, err))
    return drive, run_dir, finding


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheMinors(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-minors-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)

    # C2-3
    def test_c2_3_ignored_files_are_not_in_the_pin_and_the_contract_says_so(self):
        with open(os.path.join(testlib.SKILL, "references", "ship-contract.md"), encoding="utf-8") as fh:
            contract = " ".join(fh.read().split()).lower()
        self.assertIn("ignored files are not in the pin, as build-v2's; a fix that writes one is not seen", contract)
        testlib.write_text(os.path.join(self.ws, ".gitignore"), "local.cfg\n")
        slib.commit_all(self.ws, "ignore a local file")
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, drive, self.tmp, run_dir)
        slib.visit(self, drive, run_dir, "build-v2", "completed", self.ws)
        finding = slib.raise_finding(self.tmp, self.ws)
        slib.visit(self, drive, run_dir, "signoff-v2", "findings", self.ws)
        testlib.write_text(os.path.join(self.ws, "local.cfg"), "mode = fast\n")
        testlib.write_text(os.path.join(self.ws, "src", "turnstile.py"), "def spin(count):\n    return count + 2\n")
        code, out, err = drive(["fix", "--run-dir", run_dir, "--fixes", slib.fixes_file(
            self.tmp, run_dir, 1, [{"finding": finding, "paths": ["src/turnstile.py"], "summary": "the fix"}])])
        self.assertEqual((code, out["moved"]), (0, ["src/turnstile.py"]), (out, err))

    # C2-4
    def recheck_result_refused(self, mutate):
        drive, run_dir, finding = fixed_run(self, self.tmp, self.ws, self.tree)
        code, visit, err = drive(["visit", "--run-dir", run_dir, "--station", "recheck-v2"])
        self.assertEqual(code, 0, (visit, err))
        doc = slib.station_result("recheck-v2", "not_clear", visit, self.ws, writes=[])
        mutate(doc)
        slib.put_result(visit, doc)
        before = slib.trace(run_dir)
        code, out, err = drive(["visit", "--run-dir", run_dir, "--result"])
        self.assertEqual(code, 5, (out, err))
        self.assertEqual(before, slib.trace(run_dir))
        return out["reason"]

    def test_c2_4_a_recheck_result_for_another_slice_is_refused(self):
        self.assertIn("slice", self.recheck_result_refused(lambda d: d["checklist"].update(slice="B")))

    def test_c2_4_a_recheck_result_for_another_doc_is_refused(self):
        reason = self.recheck_result_refused(lambda d: d["checklist"].update(build_doc="docs/plans/other.md"))
        self.assertIn("docs/plans/other.md", reason)

    def test_c2_4_a_recheck_result_of_another_version_is_refused(self):
        self.assertIn("9.9.9", self.recheck_result_refused(lambda d: d["run"]["skill"].update(version="9.9.9")))

    def test_c2_4_a_recheck_result_naming_another_station_is_refused(self):
        self.assertIn("names the station", self.recheck_result_refused(
            lambda d: d["run"]["skill"].update(name="recheck")))

    # C2-5
    def test_c2_5_a_skill_md_that_links_into_a_v1_folder_is_refused_before_the_visit(self):
        v1 = os.path.join(self.tmp, "elsewhere", "bu" + "ild", "skills", "bu" + "ild")
        testlib.write_text(os.path.join(v1, "SKILL.md"), "---\nname: v1\n---\n")
        skill_md = os.path.join(self.tree.root, "build-v2", "skills", "build-v2", "SKILL.md")
        os.remove(skill_md)
        os.symlink(os.path.join(v1, "SKILL.md"), skill_md)
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, drive, self.tmp, run_dir)
        code, out, err = drive(["visit", "--run-dir", run_dir, "--station", "build-v2"])
        self.assertEqual((code, out["next"], out.get("stop_tag")), (0, "report", "station-refused"), (out, err))
        self.assertNotIn("skill_md", out)
        lines = slib.trace(run_dir)
        self.assertEqual([l["kind"] for l in lines], ["refused"])
        self.assertIn("SKILL.md", lines[0]["refusal"]["reason"])
        self.assertEqual(slib.validate_trace(run_dir)[0], 0)

    def test_c2_5_a_missing_skill_md_is_refused_too(self):
        os.remove(os.path.join(self.tree.root, "build-v2", "skills", "build-v2", "SKILL.md"))
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, drive, self.tmp, run_dir)
        code, out, err = drive(["visit", "--run-dir", run_dir, "--station", "build-v2"])
        self.assertEqual((code, out.get("stop_tag")), (0, "station-refused"), (out, err))

    # C2-6
    def test_c2_6_a_visit_with_no_result_ends_in_a_terminal_status(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, drive, self.tmp, run_dir)
        code, visit, err = drive(["visit", "--run-dir", run_dir, "--station", "build-v2"])
        self.assertEqual(code, 0, (visit, err))
        code, out, err = drive(["visit", "--run-dir", run_dir, "--result"])
        self.assertEqual(code, 2, (out, err))
        self.assertIn("report", err, "the usage message names the way to end the run")
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "visit-unfinished"))
        self.assertIn("build-v2", out["reason"])
        self.assertIn("no result", out["reason"])
        self.assertEqual([(l["kind"], l["status"]) for l in slib.trace(run_dir)], [("visit", "visiting")])
        self.assertEqual(slib.validate_trace(run_dir)[0], 0)
        self.assertIn("Result: STOPPED (build-v2: visit-unfinished)", out["station_result"]["chat"])

    def test_c2_6_a_refused_result_can_end_the_run_too(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, drive, self.tmp, run_dir)
        code, visit, err = drive(["visit", "--run-dir", run_dir, "--station", "build-v2"])
        slib.put_result(visit, {"status": "COMPLETE", "report": "a text a v1 station leaves"})
        code, out, err = drive(["visit", "--run-dir", run_dir, "--result"])
        self.assertEqual(code, 5, (out, err))
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "visit-unfinished"), (out, err))
        self.assertIn("refused", out["reason"])

    # C2-7
    def test_c2_7_whitespace_only_owner_words_are_refused(self):
        for station in ({"slice": "A", "extra_laps": {"count": 1, "words": "   "}},
                        {"slice": "A", "minor_fixes": {"words": "\t \n"}}):
            run_dir = os.path.join(self.tmp, "blank")
            doc = slib.make_input(self.ws, run_dir, run_id="blank", **station)
            path = os.path.join(self.tmp, "blank-input.json")
            testlib.write_json(path, doc)
            code, out, err = slib.Driver(self.tree, self.tmp)(["check-input", path])
            self.assertEqual(code, 4, (station, out, err))

    # C2-8
    def test_c2_8_the_mode_handed_over_is_one_the_stations_input_schema_takes(self):
        drive, run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, drive, self.tmp, run_dir)
        seen = {}

        def opened(station, which=None):
            code, out, err = drive(["visit", "--run-dir", run_dir, "--station", station])
            self.assertEqual(code, 0, (station, out, err))
            seen[station] = out
            if which is not None:
                slib.put_result(out, slib.station_result(station, which, out, self.ws))
                code, done, err = drive(["visit", "--run-dir", run_dir, "--result"])
                self.assertEqual(code, 0, (station, done, err))
                return done
        opened("build-v2", "completed")
        finding = slib.raise_finding(self.tmp, self.ws)
        opened("signoff-v2", "findings")
        testlib.write_text(os.path.join(self.ws, "src", "turnstile.py"), "def spin(count):\n    return count + 2\n")
        code, out, err = drive(["fix", "--run-dir", run_dir, "--fixes", slib.fixes_file(
            self.tmp, run_dir, 1, [{"finding": finding, "paths": ["src/turnstile.py"], "summary": "the fix"}])])
        self.assertEqual(code, 0, (out, err))
        opened("recheck-v2")
        for station, visit in sorted(seen.items()):
            schema = testlib.load_json(os.path.join(slib.real_station(station), "skills", station, "references",
                                                    "input.schema.json"))
            invocation = schema["properties"]["invocation"]
            self.assertIn(visit["mode"], invocation["properties"]["mode"]["enum"], (station, visit["mode"]))
            self.assertEqual(visit["caller"], "ship-v2")
            self.assertIn("invocation.mode %s" % visit["mode"], visit["how"])
            if station == "recheck-v2":
                self.assertEqual(visit["mode"], invocation["else"]["properties"]["mode"]["const"],
                                 "a caller other than direct takes the mode recheck-v2's schema names")
        self.assertEqual((seen["build-v2"]["mode"], seen["signoff-v2"]["mode"], seen["recheck-v2"]["mode"]),
                         ("station", "headless", "headless"))

if __name__ == "__main__":
    unittest.main()
