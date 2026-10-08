"""This harness's profile, read against the core (vertical-v2, E15 slice 1).

The twelve sections of the E9 seam, in order and each answered; the station's own values the profile
states (the local row and profile on this harness, the floor, the owner's words, the contract) are the
ones the core's code and schemas carry.
"""
import json
import os
import re
import unittest

import testlib

PROFILE = os.path.join(testlib.ADAPTER, "profile.md")
SECTIONS = ("Identity", "Model and floor", "Run id and directory", "The user channel", "`session_wrote_fix`",
            "Run date", "The verifier capability", "Delivery", "Sidecars and invocation restrictions",
            "Negative tests", "Installed-package verification", "Capability labels")
HARNESS = os.path.basename(testlib.ADAPTER)


def text(path=PROFILE):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TheProfile(unittest.TestCase):

    def test_twelve_sections_in_order_each_answered(self):
        found = re.findall(r"^## (\d+)\. (.+)$", text(), flags=re.M)
        self.assertEqual([int(n) for n, _ in found], list(range(1, 13)))
        self.assertEqual(tuple(title for _, title in found), SECTIONS)
        for body in re.split(r"^## \d+\. .+$", text(), flags=re.M)[1:]:
            self.assertTrue(body.strip())

    def test_the_stated_values_are_the_cores(self):
        body = text()
        schema = json.load(open(testlib.SCHEMA, encoding="utf-8"))
        station = schema["properties"]["station"]["properties"]
        for field in ("session_model", "date", "owner_words"):
            self.assertIn(field, station)
        self.assertIn("`floor: opus`", body)
        self.assertIn("`station.owner_words`", body)
        local = "`claude-session`" if HARNESS == "claude-code" else "`claude-opus-cli`"
        self.assertIn(local, body)
        if HARNESS == "codex":
            self.assertIn("runs no check", body)
        contract = os.path.join(testlib.SKILL_ROOT, "references", "vertical-contract.md")
        self.assertTrue(os.path.isfile(contract))

    def test_no_manual_only_control(self):
        skill = text(os.path.join(testlib.SKILL_ROOT, "SKILL.md"))
        sidecar = text(os.path.join(testlib.SKILL_ROOT, "agents", "openai.yaml"))
        self.assertNotIn("disable-model-invocation", skill)
        self.assertNotIn("allow_implicit_invocation", sidecar)
        self.assertIn("None (owner pick P5)", text())


if __name__ == "__main__":
    unittest.main()
