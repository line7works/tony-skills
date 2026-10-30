"""tools/guide-findings.py against a throwaway home folder: one GUIDE text is one finding.

Every test points the tool at a temporary HOME, so the owner's real files are never read.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

TOOL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "guide-findings.py"))

LOG_HEAD = "# Guide findings\n\n## Inbox\n\n"
LOG_LINE = '- 2026-10-20 · E15 · claude-code · held · "the log note" · run 12\n'
GUIDE_A = '- 2026-10-21 · thread-a · loop · "GUIDE: adds E16 the first note"\n'
GUIDE_B = '- 2026-10-22 · thread-b · loop · "GUIDE: contradicts E17 the second note"\n'
MALFORMED = '- not a dated line · "GUIDE: held E18 broken"\n'


class GuideFindingsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = self._tmp.name
        self.dev = os.path.join(self.home, "Developer")
        self.write("tony-skills/docs/guide-findings.md", LOG_HEAD + LOG_LINE)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, text):
        path = os.path.join(self.dev, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def run_tool(self, *args):
        env = dict(os.environ, HOME=self.home)
        return subprocess.run([sys.executable, TOOL, *args], env=env, capture_output=True, text=True)

    def findings(self):
        proc = self.run_tool("--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_same_line_in_two_checkouts_counts_once(self):
        self.write("tony-skills/docs/feedback.md", GUIDE_A)
        self.write("tony-skills-e18/docs/feedback.md", GUIDE_A)
        fb = [x for x in self.findings() if x["origin"] == "fb"]
        self.assertEqual(len(fb), 1)
        self.assertTrue(fb[0]["source"].endswith(os.path.join("docs", "feedback.md") + ":1"))
        report = self.run_tool().stdout
        self.assertIn("| 0 | 1 | 1 | 0 | 2 |", report)
        self.assertEqual(report.count("the first note"), 1)
        check = self.run_tool("--check")
        self.assertEqual(check.returncode, 0)
        self.assertIn("2 findings parsed, 0 malformed", check.stderr)

    def test_two_different_lines_count_twice(self):
        self.write("tony-skills/docs/feedback.md", GUIDE_A + GUIDE_B)
        self.write("other/docs/feedback.md", GUIDE_B.replace("second", "third"))
        fb = [x for x in self.findings() if x["origin"] == "fb"]
        self.assertEqual(sorted(x["note"] for x in fb), [
            "adds E16 the first note",
            "contradicts E17 the second note",
            "contradicts E17 the third note",
        ])

    def test_log_finding_still_counts(self):
        self.write("tony-skills-e18/docs/feedback.md", GUIDE_A)
        found = self.findings()
        log = [x for x in found if x["origin"] == "log"]
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["note"], "the log note")
        self.assertEqual(len(found), 2)

    def test_malformed_line_repeated_is_reported_once(self):
        self.write("tony-skills/docs/feedback.md", MALFORMED)
        self.write("tony-skills-e18/docs/feedback.md", MALFORMED)
        check = self.run_tool("--check")
        self.assertEqual(check.returncode, 1)
        self.assertEqual(check.stderr.count("MALFORMED:"), 1)
        self.assertIn("1 findings parsed, 1 malformed", check.stderr)


if __name__ == "__main__":
    unittest.main()
