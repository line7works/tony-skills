"""This core's seeded cases build and observe (E14 slice 1, 3.7).

What the suite holds is only what every case guarantees, never an outcome (the outcomes are in an
answer key no builder reads): every family builds every case it lists, twice to the same tree
hash; `observe.py` runs every case with no step error, emits `writes_none`, and lists the lane's
pending facts for every `lane` step; no shipped case file names an expected value.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest

import testlib

SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
OBSERVE = os.path.join(SEEDED, "observe.py")
GEN = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable


def families():
    return sorted(n for n in os.listdir(SEEDED) if n[:1].isupper() and os.path.isdir(os.path.join(SEEDED, n)))


class TheFamilies(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("seeded-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def build(self, family, out):
        proc = subprocess.run([GEN, os.path.join(SEEDED, family, "build.py"), "--out", out, "--json"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return dict((row["case"], row["tree_sha256"]) for row in json.loads(proc.stdout.decode())["cases"])

    def test_every_family_builds_deterministically_with_a_clean_case(self):
        names = families()
        self.assertTrue(names)
        for family in names:
            one = self.build(family, os.path.join(self.tmp, "a", family))
            two = self.build(family, os.path.join(self.tmp, "b", family))
            self.assertEqual(one, two, family)
            self.assertGreaterEqual(len(one), 3, family)
            self.assertTrue(any(case.endswith("-01-clean") for case in one), family)
            with open(os.path.join(SEEDED, family, "CASES.md"), encoding="utf-8") as fh:
                text = fh.read()
            for case in one:
                self.assertIn("## %s" % case, text)

    def test_no_case_file_states_an_outcome(self):
        for family in families():
            for base, dirs, files in os.walk(os.path.join(SEEDED, family)):
                for name in files:
                    with open(os.path.join(base, name), encoding="utf-8") as fh:
                        text = fh.read()
                    for word in ('"assert"', "expected_", "Pass:", "must be refused", "should pass"):
                        self.assertNotIn(word, text, os.path.join(base, name))


@unittest.skipIf(testlib.checkout_sibling("readers") is None,
                 "no readers component beside this core (the installed shape): observe.py reads its roster")
class TheObserver(unittest.TestCase):

    def test_every_case_observes_with_no_step_error(self):
        tmp = testlib.make_scratch("observe-")
        self.addCleanup(testlib.rmtree, tmp)
        proc = subprocess.run([sys.executable, OBSERVE, "--all", "--out", tmp], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stdout.decode()[-2000:] + proc.stderr.decode()[-2000:])
        rows = json.loads(proc.stdout.decode())["cases"]
        self.assertTrue(rows)
        for row in rows:
            observed = testlib.load_json(row["observed"])
            self.assertNotIn("_errors", observed, row["case"])
            self.assertIn("writes_none", observed, row["case"])
            drive = testlib.load_json(os.path.join(os.path.dirname(row["observed"]), "drive.json"))
            for step in drive["steps"]:
                if step["kind"] != "lane":
                    continue
                for name in step.get("pending", []):
                    self.assertTrue(name in observed or name in observed.get("_lane_pending", []),
                                    "%s: the lane fact %s is neither observed nor pending" % (row["case"], name))


@unittest.skipIf(testlib.checkout_sibling("readers") is None,
                 "no readers component beside this core (the installed shape): observe.py reads its roster")
class TheLaneHook(unittest.TestCase):
    """The `lane_observe.py` seam (CS-1, CS-2), driven in-process on a scratch copy of the plugin with a
    planted observer and a planted `lane` step: an observer works on its own dict; only the names its step
    lists that the frame did not observe are merged; every other name it fills is recorded under `_errors`
    and never merged; `SystemExit` lands in `_errors`; its own `_errors` and `_phases` are appended."""

    def hook(self, body):
        tmp = testlib.make_scratch("lanehook-")
        self.addCleanup(testlib.rmtree, tmp)
        plugin = os.path.join(tmp, os.path.basename(testlib.PLUGIN))
        shutil.copytree(testlib.PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        seeded = os.path.join(plugin, "evals", "seeded-cases")
        testlib.write_text(os.path.join(seeded, "lane_observe.py"), body)
        spec = importlib.util.spec_from_file_location("observe_under_test", os.path.join(seeded, "observe.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, tmp

    def run_hook(self, body, facts):
        module, tmp = self.hook(body)
        step = {"kind": "lane", "pending": ["listed_fact", "other_listed"]}
        module.lane_observe(step, tmp, {"workspace": tmp, "staging": tmp}, facts, {}, tmp)
        return facts

    def test_only_listed_unobserved_names_merge(self):
        facts = self.run_hook("def observe_lane(step, case_dir, neutral, facts, via, scratch):\n"
                              "    facts['listed_fact'] = 'lane'\n"
                              "    facts['selection_outcome'] = 'planted'\n"
                              "    facts['unlisted_fact'] = 1\n"
                              "    facts['_phases'].append('lane:planted')\n",
                              {"_phases": [], "_errors": [], "selection_outcome": "one"})
        self.assertEqual(facts["listed_fact"], "lane")
        self.assertEqual(facts["selection_outcome"], "one")
        self.assertNotIn("unlisted_fact", facts)
        self.assertEqual(facts["_phases"], ["lane:planted"])
        self.assertEqual(sorted(e["error"].split("'")[1] for e in facts["_errors"]), ["selection_outcome", "unlisted_fact"])
        self.assertNotIn("other_listed", facts, "a listed name the observer did not fill stays unfilled (pending)")

    def test_a_system_exit_and_a_removed_errors_key_land_in_errors(self):
        facts = self.run_hook("def observe_lane(step, case_dir, neutral, facts, via, scratch):\n"
                              "    facts['listed_fact'] = 'lane'\n"
                              "    facts.pop('_errors')\n"
                              "    raise SystemExit(3)\n", {"_phases": [], "_errors": []})
        self.assertEqual(facts["listed_fact"], "lane")
        self.assertEqual(len(facts["_errors"]), 1)
        self.assertIn("SystemExit", facts["_errors"][0]["error"])

if __name__ == "__main__":
    unittest.main()
