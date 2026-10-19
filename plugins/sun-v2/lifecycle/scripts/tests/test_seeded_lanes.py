"""E16 slice 5, the join's part J2: the seeded families that need the lanes (the contract's section 12), on the three joined
lanes over the fakes: L0 (the verified baseline), L2 (never clobber), L3 (adoption), L5 (git), L7 (restore) and L8 (no clock).

Each family builds, its ids are the ones its `CASES.md` names, at least three with one clean, and neither `CASES.md` nor the
cases of `build.py` states an outcome. `observe.py --all` drives every case of every family to an ending: each look, go,
resume and status it drives ends with an ending the tool printed, or killed where the case kills it, or not driven where an
earlier look of the case gave no manifest to go on. This module grades nothing: the expected outcomes are in a key outside
this repository, and the control room grades. The five families of slice 1 build and observe as before
(`test_seeded_cases`).
"""
import base64
import json
import os
import sys

import harness
import scan
import test_seeded_cases as slice1

sys.path.insert(0, os.path.join(slice1.SEEDED, "_lib"))
import caselib  # noqa: E402

FAMILIES = ("L0-the-verified-baseline", "L2-never-clobber", "L3-adoption", "L5-git", "L7-restore", "L8-no-clock")
DRIVEN = ("look", "go", "resume", "status")


class SeededLanes(harness.Case):
    def test_J2_S12_every_family_has_three_cases_or_more_one_clean_and_files_that_state_no_outcome(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                code, out, err = slice1.run(os.path.join(family, "build.py"), "--list")
                self.assertEqual(code, 0, err)
                ids = out.split()
                self.assertGreaterEqual(len(ids), 3, family)
                self.assertEqual(len([i for i in ids if i.endswith("-01-clean")]), 1, family)
                text = open(os.path.join(slice1.SEEDED, family, "CASES.md")).read()
                self.assertEqual(slice1.re.findall(r"^## (\S+-\d\d-\S+)$", text, slice1.re.M), ids,
                                 "%s: CASES.md and build.py name different cases" % family)
                self.assertIsNone(slice1.OUTCOME_WORDS.search(text), "%s: CASES.md states an outcome" % family)
                source = open(os.path.join(slice1.SEEDED, family, "build.py")).read()
                self.assertIsNone(slice1.OUTCOME_WORDS.search(source.split("CASES = ")[1]), "%s: build.py states an outcome" % family)

    def test_J2_S12_observe_drives_every_case_of_every_family_to_an_ending(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                out = os.path.join(self.tmp, family)
                code, _o, err = slice1.run(os.path.join(family, "build.py"), "--out", out)
                self.assertEqual(code, 0, err)
                code, text, err = slice1.run("observe.py", "--out", out, "--all")
                self.assertEqual(code, 0, err)
                observed = json.loads(text)["observed"]
                code, listed, err = slice1.run(os.path.join(family, "build.py"), "--list")
                self.assertEqual(sorted(o["case"] for o in observed), sorted(listed.split()))
                for case in observed:
                    driven = [s for s in case["steps"] if s["do"] in DRIVEN]
                    self.assertTrue(driven, case["case"])
                    for step in driven:
                        self.assertTrue(step.get("ending") or step.get("killed") or step.get("not_driven"),
                                        "%s: a %s with no ending: %s" % (case["case"], step["do"], step))
                    self.assertIn("named", case, case["case"])


class Disclosure(harness.Case):
    """The join's J2c, D8 (the reviewer's BLOCKER; the owner's design step, "Reuse the tool's own scanner"): no held or
    protected value is copied into an observation, and every observation passes the SEC-11 scanner (`tests/scan.py`) fed
    every secret and held value of the case's machine before anything is printed; a hit stops it, naming the case and the
    value's name, and prints nothing of the value."""

    def observed(self, out, case):
        code, text, err = slice1.run("observe.py", "--out", out, "--case", case)
        return code, text, err

    def probe(self, rel):
        """Her plant: a joined case with no step, the database password's base64 form written into `rel` of its home."""
        out = os.path.join(self.tmp, "probe")
        case = "probe"
        m = caselib.machine(out, case)
        facts = {"case": case, "family": "probe"}
        caselib.joined(m, facts)
        facts["rows_root"] = m.rows_root
        encoded = base64.b64encode(facts["password"].encode()).decode()
        before = open(m.path(rel)).read() if os.path.exists(m.path(rel)) else ""
        m.put(rel, before + encoded + "\n")
        with open(os.path.join(out, case, "case.json"), "w") as fh:
            json.dump({"case": case, "family": "probe", "fixture": "joined", "drive": [], "facts": facts}, fh)
        return out, case, facts["password"], encoded

    def test_J2c_D8_SEC1_SEC11_L3_01_clean_holds_neither_the_held_database_identity_nor_a_table_name(self):
        out = os.path.join(self.tmp, "L3-adoption")
        code, _o, err = slice1.run(os.path.join("L3-adoption", "build.py"), "--out", out)
        self.assertEqual(code, 0, err)
        code, text, err = self.observed(out, "L3-01-clean")
        self.assertEqual(code, 0, err)
        seen = json.loads(text)["observed"][0]
        with open(os.path.join(out, "L3-01-clean", "home", ".fakes", "pg", "state.json")) as fh:
            pg = json.load(fh)
        # her first two lines, each now false: the held identity in no form anywhere, and no table name in the database's facts
        self.assertFalse([form for form in scan.needles(pg["identity"]) if form in text], "the held database identity is in the observation")
        self.assertFalse([name for name in pg["tables"] if name in json.dumps(seen["providers"]["database"])],
                         "a held table name is in the observation")

    def test_J2c_D8_SEC11_her_encoded_password_in_a_file_of_the_home_reaches_no_observation(self):
        out, case, password, encoded = self.probe("notes.txt")
        code, text, err = self.observed(out, case)
        self.assertEqual(code, 0, err)
        # her third and fourth lines, each now false: the encoded password does not reach the observation, unreported
        self.assertFalse([form for form in scan.needles(password) if form in text + err], "the password reaches the observation")
        self.assertNotIn("secret_values_met_and_replaced", text)

    def test_J2c_D8_SEC11_a_planted_hit_stops_the_observation_naming_the_case_and_the_value_and_printing_none_of_it(self):
        out, case, password, encoded = self.probe("shortcuts.txt")     # a layer file whose text the observation names
        code, text, err = self.observed(out, case)
        self.assertEqual(code, 3, err)
        self.assertEqual(text, "")
        self.assertIn("case probe", err)
        self.assertIn("the database password", err)
        self.assertFalse([form for form in scan.needles(password) if form in err], "the stop prints the value")


class Schedules(harness.Case):
    """The join's J2c, J2-2 (the reviewer's MAJOR): L7's clean case seeds the schedule layers (a launch agent, a crontab
    line, a routine, as the set lane's fixture does) and its observation names their state, bytes and calls after the
    sunrise, after the sunset and after the restore. It grades nothing."""

    def test_J2c_J2_2_L7_clean_seeds_the_schedule_layers_and_names_them_after_each_run(self):
        out = os.path.join(self.tmp, "L7-restore")
        code, _o, err = slice1.run(os.path.join("L7-restore", "build.py"), "--out", out)
        self.assertEqual(code, 0, err)
        code, text, err = slice1.run("observe.py", "--out", out, "--case", "L7-01-clean")
        self.assertEqual(code, 0, err)
        seen = json.loads(text)["observed"][0]
        snapshots = dict((s["label"], s) for s in seen["steps"] if s["do"] == "snapshot")
        self.assertEqual(sorted(snapshots), ["after the sunrise", "after the sunset"])
        seeded = snapshots["after the sunrise"]["named"]["schedules"]
        self.assertEqual((seeded["launch agent files"], len(seeded["loaded labels"]), seeded["crontab lines"], len(seeded["routines"])),
                         (2, 2, 2, 2), seeded)
        for named in (snapshots["after the sunset"]["named"], seen["named"]):
            self.assertEqual(sorted(named["schedules"]), sorted(seeded))
            self.assertIn("calls", named["schedules"])


if __name__ == "__main__":
    import unittest
    unittest.main()
