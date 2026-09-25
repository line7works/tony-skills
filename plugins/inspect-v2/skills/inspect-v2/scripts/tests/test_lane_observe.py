"""The lane facts of families I1 to I4 (required test 9; brief CR-7).

`evals/seeded-cases/lane_observe.py` fills every name each `lane` step lists under `pending`, from
a real drive of this core (the CLI, or the library `request` calls, named in `_via`), never from
what the case expects: `observe.py` run on every case of this core's families leaves no
`_lane_pending` and no `_errors`, and every lane fact carries its `_via`. Facts only: this test
asserts no outcome of any case (the outcomes are in an answer key no builder reads).
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
OBSERVE = os.path.join(SEEDED, "observe.py")
FAMILIES = ("I1-primary-evidence", "I2-the-no-record-rule", "I3-records-and-the-stamp", "I4-no-v1-import")
I3 = os.path.join(SEEDED, "I3-records-and-the-stamp")


@unittest.skipIf(testlib.checkout_sibling("readers") is None or testlib.records_root() is None or
                 testlib.checkout_sibling("blueprint-v2") is None,
                 "the installed shape: the lane drive needs records, readers and blueprint-v2 beside this core")
class TheLaneFacts(unittest.TestCase):

    def test_every_pending_name_is_filled_by_a_real_drive(self):
        self.assertTrue(os.path.isfile(os.path.join(SEEDED, "lane_observe.py")))
        tmp = testlib.make_scratch("lane-observe-")
        self.addCleanup(testlib.rmtree, tmp)
        proc = subprocess.run([sys.executable, OBSERVE, "--all", "--out", tmp], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stdout.decode()[-3000:] + proc.stderr.decode()[-3000:])
        rows = json.loads(proc.stdout.decode())["cases"]
        seen = set()
        for row in rows:
            observed = testlib.load_json(row["observed"])
            self.assertNotIn("_errors", observed, row["case"])
            if observed["_family"] not in FAMILIES:
                continue
            seen.add(observed["_family"])
            self.assertNotIn("_lane_pending", observed, row["case"])
            drive = testlib.load_json(os.path.join(os.path.dirname(row["observed"]), "drive.json"))
            for step in drive["steps"]:
                if step["kind"] != "lane":
                    continue
                for name in step.get("pending", []):
                    self.assertIn(name, observed, (row["case"], name))
                    self.assertIn(name, observed["_via"], (row["case"], name))
                    self.assertTrue(observed["_via"][name].startswith(("cli", "library")), observed["_via"][name])
                    # CI1-12: `_via` names the phases the drive reached, and none it never ran
                    ran = [p["phase"] for p in observed["_phases"] if p.get("phase")]
                    how = observed["_via"][name]
                    named = how.split("cli: ", 1)[1].split(" (", 1)[0] if how.startswith("cli: ") else \
                        how.split(" after ", 1)[1].split(" through", 1)[0]
                    named = [p.strip() for p in named.split(",")]
                    windows = [ran[i:i + len(named)] for i in range(len(ran) - len(named) + 1)]
                    self.assertIn(named, windows, (row["case"], name, how, ran))
                    # round 3, R5: a fact that rests on the owner word the translation supplied (I3's
                    # outside row, no word in the neutral input) names that word as a translation choice
                    if observed["_family"] == "I3-records-and-the-stamp":
                        self.assertIn("translation choice: the owner word", how, (row["case"], name))
                        self.assertIn("send it to gpt-astra", how, (row["case"], name))
                    else:
                        self.assertNotIn("owner word", how, (row["case"], name))
        self.assertEqual(seen, set(FAMILIES) - {"I4-no-v1-import"} | ({"I4-no-v1-import"} & seen))


@unittest.skipIf(testlib.checkout_sibling("readers") is None or testlib.records_root() is None or
                 testlib.checkout_sibling("blueprint-v2") is None,
                 "the installed shape: the lane drive needs records, readers and blueprint-v2 beside this core")
class ThePlantedAdjudications(unittest.TestCase):
    """Round 5, the control room's ruling on question 1: a seeded replay's translation copies a planted
    `seeded_adjudications` list into the executor's `adjudications` as given (`reason` renamed `why`), a
    renaming of the fixture, never an invented judgment; a case whose planted answer holds none still
    stops at `record-answer` (exit 5, missing-adjudication) with its names pending. The stop is driven on
    a synthetic copy of I3-01-clean with the list taken out, built under a temporary directory."""

    def setUp(self):
        self.tmp = testlib.make_scratch("planted-adj-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def built(self):
        proc = subprocess.run([sys.executable, os.path.join(I3, "build.py"), "--out", self.tmp, "--case", "I3-01-clean"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        case_dir = os.path.join(self.tmp, "I3-01-clean")
        neutral = testlib.load_json(os.path.join(case_dir, "input.json"))
        step = [s for s in testlib.load_json(os.path.join(case_dir, "drive.json"))["steps"] if s["kind"] == "lane"][0]
        return case_dir, neutral, step

    def observe(self, case_dir, neutral, step):
        import importlib.util
        spec = importlib.util.spec_from_file_location("lane_observe_under_test", os.path.join(SEEDED, "lane_observe.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        facts, via = {"_phases": [], "_errors": []}, {}
        scratch = os.path.join(self.tmp, "scratch")
        os.makedirs(scratch)
        module.observe_lane(step, case_dir, neutral, facts, via, scratch)
        return module, facts, via

    def test_the_translation_copies_the_planted_list_as_given(self):
        case_dir, neutral, step = self.built()
        module, facts, via = self.observe(case_dir, neutral, step)
        self.assertEqual(facts["_errors"], [])
        self.assertEqual([(p["phase"], p["exit"]) for p in facts["_phases"]][-3:],
                         [("record-answer", 0), ("write", 0), ("report", 10)])
        for name in step["pending"]:
            self.assertIn(name, facts)
            self.assertIn("translation choice", via[name])
        reader = testlib.load_json(os.path.join(case_dir, neutral["answer"]))
        doc = module.translate(reader, {"calls": [{"call_id": "run-gpt-astra", "lens": "paper", "row": "gpt-astra"}]},
                               "s")
        self.assertEqual(doc["adjudications"], [{"finding": a["finding"], "decision": a["decision"], "why": a["reason"]}
                                                for a in reader["seeded_adjudications"]])
        self.assertNotIn("seeded_adjudications", doc["results"][0])

    def test_a_planted_answer_with_no_list_still_stops_at_record_answer(self):
        case_dir, neutral, step = self.built()
        path = os.path.join(case_dir, neutral["answer"])
        reader = testlib.load_json(path)
        del reader["seeded_adjudications"]
        testlib.write_json(path, reader)
        module, facts, via = self.observe(case_dir, neutral, step)
        self.assertEqual(facts["_errors"], [])
        self.assertEqual([(p["phase"], p["exit"]) for p in facts["_phases"]][-1], ("record-answer", 5))
        self.assertEqual([n for n in step["pending"] if n in facts], [])
        self.assertNotIn("adjudications", module.translate(reader, None, "s"))


if __name__ == "__main__":
    unittest.main()
