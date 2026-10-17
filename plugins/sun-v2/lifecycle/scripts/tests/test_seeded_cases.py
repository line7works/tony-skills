"""The seeded cases build and can be observed (the contract's section 12; the brief's section 8).

Five families over the frame's fake rows: L1, L4, L6, L9 and T1. Each has at least three cases, one of
them clean. This test builds every family, checks the ids against `CASES.md`, and drives the clean case
of each through the observer, where it asserts that the work was done, by name. It grades no planted
case: the expected outcomes are in a key outside this repository, and the control room grades.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import unittest

import harness

SEEDED = os.path.join(harness.PLUGIN, "evals", "seeded-cases")
FAMILIES = ("L1-the-gate", "L4-credentials", "L6-resume", "L9-the-preview-binds", "T1-no-v1-import")
OUTCOME_WORDS = re.compile(r"\b(expected|must|should|is refused|is stopped|ends refused|ends stopped|correct|wrong)\b", re.IGNORECASE)


def run(script, *argv):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([sys.executable, "-W", "ignore", os.path.join(SEEDED, script)] + list(argv), env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, cwd=os.path.dirname(harness.PLUGIN))
    return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class SeededCases(harness.Case):
    def test_every_family_has_three_cases_or_more_one_clean_and_a_cases_file_that_states_no_outcome(self):
        for family in FAMILIES:
            code, out, err = run(os.path.join(family, "build.py"), "--list")
            self.assertEqual(code, 0, err)
            ids = out.split()
            self.assertGreaterEqual(len(ids), 3, family)
            self.assertEqual(len([i for i in ids if i.endswith("-01-clean")]), 1, family)
            text = open(os.path.join(SEEDED, family, "CASES.md")).read()
            self.assertEqual(re.findall(r"^## (\S+-\d\d-\S+)$", text, re.M), ids, "%s: CASES.md and build.py name different cases" % family)
            self.assertIsNone(OUTCOME_WORDS.search(text), "%s: CASES.md states an outcome" % family)
            source = open(os.path.join(SEEDED, family, "build.py")).read()
            self.assertIsNone(OUTCOME_WORDS.search(source.split("CASES = ")[1]), "%s: build.py states an outcome" % family)

    def observed(self, family, case):
        out = os.path.join(self.tmp, family)
        code, _o, err = run(os.path.join(family, "build.py"), "--out", out)
        self.assertEqual(code, 0, err)
        code, text, err = run("observe.py", "--out", out, "--case", case)
        self.assertEqual(code, 0, err)
        return json.loads(text)["observed"][0]

    def test_the_clean_case_of_each_family_shows_the_work_done_by_name(self):
        gate = self.observed("L1-the-gate", "L1-01-clean")
        self.assertEqual([(s["ending"], s["manifest_written"], s["cue_calls"]) for s in gate["steps"]], [("preview", True, ["sunrise"])])
        resume = self.observed("L6-resume", "L6-01-clean")
        self.assertEqual([s["ending"] for s in resume["steps"]], ["preview", "complete"])
        self.assertEqual(resume["files"]["dev/demo/README.md"]["sha256"], sha("# demo\n"))
        self.assertEqual(resume["files"]["shortcuts.txt"]["sha256"], sha("alias other\nalias demo\n"))
        self.assertEqual(resume["files"]["dev/demo/scope.md"]["sha256"], sha("scope\n"))
        self.assertNotIn("dev/demo-scope.md", resume["files"])
        self.assertEqual(resume["fakes"]["fakehost"]["things"], {"demo": {"kind": "repo", "state": "paused"}})
        self.assertEqual(resume["fakes"]["fakegit"]["refs"], {"main": "c1"})
        self.assertEqual(resume["fakes"]["fakehost"]["changing_calls"], ["create", "set"])
        self.assertEqual(resume["journal"][0], "open - -")
        self.assertEqual(resume["journal"][-1], "run-end - complete")
        self.assertEqual(len([line for line in resume["journal"] if line.startswith("completion ")]), 6)
        binds = self.observed("L9-the-preview-binds", "L9-01-clean")
        self.assertEqual(sorted(set(line.split()[1] for line in binds["journal"] if line.split()[1] != "-")), ["B1", "C1", "G1", "H1", "K1", "K2", "M1", "S1"])
        creds = self.observed("L4-credentials", "L4-01-clean")
        self.assertEqual(creds["scan_findings"], [])
        self.assertGreaterEqual(creds["values_scanned_for"], 7)
        for name in ("demo.pulled.env", "demo-dump.txt"):
            self.assertEqual(creds["secret_files"][name], {"present": True, "mode": "0o600", "holds_its_canary": True})
        self.assertEqual(creds["fakes"]["fakedump"]["changing_calls"], ["dump"])
        scan = self.observed("T1-no-v1-import", "T1-01-clean")
        self.assertEqual(scan["steps"], [{"do": "v1scan", "v1_findings_present": False, "v1_finding_count": 0}])

    def test_the_builder_refuses_an_out_folder_under_a_harness_home(self):
        code, out, err = run(os.path.join("L1-the-gate", "build.py"), "--out", os.path.join(os.path.expanduser("~"), ".claude", "nowhere-sunv2-test"))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
