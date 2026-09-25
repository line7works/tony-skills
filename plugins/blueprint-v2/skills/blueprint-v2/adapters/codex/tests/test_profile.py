"""This harness's profile (lane L, reading CR-14): the E9 seam's twelve sections, in order, each
answered; no section left for a lane to fill; the station's own claims held to the code.

Standard library only; reads files, writes nothing.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTER = os.path.dirname(HERE)
SKILL = os.path.dirname(os.path.dirname(ADAPTER))
PROFILE = os.path.join(ADAPTER, "profile.md")
SECTIONS = ["Identity", "Model and floor", "Run id and directory", "The user channel", "`session_wrote_fix`",
            "Run date", "The verifier capability", "Delivery", "Sidecars and invocation restrictions",
            "Negative tests", "Installed-package verification", "Capability labels"]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TheProfile(unittest.TestCase):

    def setUp(self):
        self.text = read(PROFILE)

    def section(self, number):
        start = self.text.index("\n## %d. " % number)
        stop = self.text.find("\n## ", start + 1)
        return self.text[start:stop if stop > 0 else len(self.text)]

    def test_the_twelve_sections_in_order_each_answered(self):
        found = re.findall(r"^## (\d+)\. (.+)$", self.text, re.M)
        self.assertEqual([int(n) for n, _ in found], list(range(1, 13)))
        self.assertEqual([t for _, t in found], SECTIONS)
        for number in range(1, 13):
            body = self.section(number).split("\n", 2)[-1].strip()
            self.assertTrue(body, number)
        self.assertNotIn("lane L fills", self.text)
        self.assertNotIn("fills this", self.text)

    def test_the_run_date_claim_is_the_cores(self):
        self.assertIn("harvest.json", self.section(6))
        phases = read(os.path.join(SKILL, "scripts", "blueprint_core", "phases.py"))
        self.assertIn('"run_date": run_date', phases)
        self.assertIn("datetime.date.today()", phases)

    def test_no_reader_is_summoned_and_the_contract_says_so(self):
        self.assertIn("summons none", self.section(7))
        contract = read(os.path.join(SKILL, "references", "blueprint-v2-contract.md"))
        self.assertIn("## 14. Readers\n\nNone.", contract)
        scripts = os.path.join(SKILL, "scripts", "blueprint_core")
        for name in os.listdir(scripts):
            if name.endswith(".py"):
                self.assertNotIn("readers_request", read(os.path.join(scripts, name)), name)

    def test_the_owners_words_the_station_records_exist_in_the_code(self):
        user = self.section(4)
        self.assertIn("choose --words", user)
        self.assertIn("collapsed_gate.words", user)
        driver = read(os.path.join(SKILL, "scripts", "blueprint.py"))
        self.assertIn('"--words"', driver)
        schema = read(os.path.join(SKILL, "references", "answer.schema.json"))
        self.assertIn('"collapsed_gate"', schema)


if __name__ == "__main__":
    unittest.main()
