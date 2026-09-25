"""The lane's own observer, `evals/seeded-cases/lane_observe.py` (reading CR-7, required test 9).

Every family of this core is built for real (its own `build.py`), and `observe_lane` is handed a
`lane` step naming the neutral facts precon-v2 can produce; each name is filled from a drive of
the REAL CLI on that case (`_via` says `cli`), a name it has no fact for stays unfilled, and the
case's workspace and staging home are left as found. Then `observe.py --all` runs as the control
room runs it and no case of this core carries `_lane_pending` or `_errors`.
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

import testlib

SEEDED = os.path.join(testlib.PLUGIN, "evals", "seeded-cases")
LANE = os.path.join(SEEDED, "lane_observe.py")
GEN = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
FAMILIES = ("P1-ledger-traceability", "P2-one-living-doc", "P3-the-exit-test")


def lane_module():
    spec = importlib.util.spec_from_file_location("lane_observe_under_test", LANE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(family, out):
    proc = subprocess.run([GEN, os.path.join(SEEDED, family, "build.py"), "--out", out, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
    assert proc.returncode == 0, proc.stderr.decode()
    return [(row["case"], row["path"]) for row in json.loads(proc.stdout.decode())["cases"]]


class _Lane(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("lane-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.module = lane_module()

    def observe(self, case_dir, step):
        neutral = testlib.load_json(os.path.join(case_dir, "input.json"))
        facts = {"_errors": [], "_phases": []}
        via = {}
        scratch = os.path.join(self.tmp, "scratch-%d" % len(os.listdir(self.tmp)))
        os.makedirs(scratch)
        before = (testlib.tree_digest(neutral["workspace"]), testlib.tree_digest(neutral["staging"]))
        self.module.observe_lane(step, case_dir, neutral, facts, via, scratch)
        self.assertEqual((testlib.tree_digest(neutral["workspace"]), testlib.tree_digest(neutral["staging"])),
                         before, "the lane observer writes nothing where the case's documents live")
        self.assertEqual(facts["_errors"], [])
        for name in step["pending"]:
            if name in facts:
                self.assertEqual(via.get(name), "cli", name)
        return facts


class P2(_Lane):

    def test_the_selection_facts_from_the_real_cli(self):
        seen = {}
        for case, case_dir in build("P2-one-living-doc", os.path.join(self.tmp, "cases")):
            facts = self.observe(case_dir, {"kind": "lane", "hunt": "scope", "name": "turnstile",
                                            "pending": ["selection_outcome", "selection_candidates"]})
            seen[case] = (facts["selection_outcome"], facts["selection_candidates"])
        self.assertEqual(seen["P2-03-two-homes"][0], "several")
        self.assertEqual(seen["P2-03-two-homes"][1], ["staging/turnstile-scope.md",
                                                      "workspace/docs/scope/2026-09-20-turnstile.md"])
        self.assertEqual(seen["P2-01-clean"], ("none", []))


class P1(_Lane):

    def test_the_ledger_and_answer_facts_from_the_real_cli(self):
        step = {"kind": "lane", "scope_doc": "workspace/docs/scope/2026-09-20-turnstile.md",
                "pending": ["ledger_refused", "ledger_tags", "ledger_refused_lines", "answer_refused",
                            "answer_written", "refusal_reason"]}
        seen = {}
        for case, case_dir in build("P1-ledger-traceability", os.path.join(self.tmp, "cases")):
            seen[case] = self.observe(case_dir, dict(step))
        self.assertIs(seen["P1-04-untaggable-ledger-line"]["ledger_refused"], True)
        self.assertEqual(seen["P1-04-untaggable-ledger-line"]["ledger_refused_lines"], [7])
        self.assertIs(seen["P1-01-clean"]["ledger_refused"], False)
        self.assertEqual(seen["P1-01-clean"]["ledger_tags"]["parked"], 2)
        for case in ("P1-01-clean", "P1-02-no-source", "P1-03-parked-quietly-resolved"):
            self.assertIn("answer_refused", seen[case])
            self.assertIn("answer_written", seen[case])
            self.assertEqual(seen[case]["answer_written"], not seen[case]["answer_refused"])

    def test_a_name_it_has_no_fact_for_stays_unfilled(self):
        case, case_dir = build("P1-ledger-traceability", os.path.join(self.tmp, "cases"))[0]
        facts = self.observe(case_dir, {"kind": "lane", "pending": ["visual_rendered", "ledger_refused"],
                                        "scope_doc": "workspace/docs/scope/2026-09-20-turnstile.md"})
        self.assertNotIn("visual_rendered", facts)
        self.assertIn("ledger_refused", facts)


class P3(_Lane):

    def test_the_request_facts_from_the_real_cli(self):
        seen = {}
        for case, case_dir in build("P3-the-exit-test", os.path.join(self.tmp, "cases")):
            drive = testlib.load_json(os.path.join(case_dir, "drive.json"))
            request = [s for s in drive["steps"] if s["kind"] == "request"][0]
            seen[case] = self.observe(case_dir, {"kind": "lane", "rows": request["rows"],
                                                 "documents": request["documents"], "pending": [
                "authorized_rows", "request_documents", "request_profiles", "refusal_reason"]})
        self.assertEqual(seen["P3-01-clean"]["authorized_rows"], ["gpt-astra"])
        self.assertEqual(seen["P3-01-clean"]["request_profiles"], ["starved"])
        self.assertEqual(seen["P3-01-clean"]["request_documents"], ["2026-09-20-turnstile.md"])
        self.assertEqual(seen["P3-03-claude-row-named"]["authorized_rows"], [])
        self.assertEqual(seen["P3-02-outside-no-word"]["authorized_rows"], [])
        self.assertIn("gpt-astra", seen["P3-02-outside-no-word"]["refusal_reason"])


@unittest.skipIf(testlib.checkout_sibling("readers") is None,
                 "no readers component beside this core (the installed shape): observe.py reads its roster")
class TheObserver(unittest.TestCase):

    def test_no_case_of_this_core_left_pending_or_in_error(self):
        tmp = testlib.make_scratch("observe-lane-")
        self.addCleanup(testlib.rmtree, tmp)
        proc = subprocess.run([sys.executable, os.path.join(SEEDED, "observe.py"), "--all", "--out", tmp],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stdout.decode()[-2000:] + proc.stderr.decode()[-2000:])
        rows = json.loads(proc.stdout.decode())["cases"]
        self.assertEqual(sorted(set(r["case"][:2] for r in rows)), ["P1", "P2", "P3"])
        for row in rows:
            observed = testlib.load_json(row["observed"])
            self.assertNotIn("_lane_pending", observed, row["case"])
            self.assertNotIn("_errors", observed, row["case"])


if __name__ == "__main__":
    unittest.main()
