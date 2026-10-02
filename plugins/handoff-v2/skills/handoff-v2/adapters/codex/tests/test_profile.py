"""This harness's profile, read against the core (E15 slice 1, the back frame's skeleton).

The twelve sections of the E9 seam, in order; every section answered for what the back frame fixes,
the core named as not built yet, and the sidecar section true to the core's own SKILL.md and Codex
sidecar (owner pick P5: the manual-only controls on handoff-v2 only).
"""
import os
import re
import unittest

import testlib

PROFILE = os.path.join(testlib.ADAPTER, "profile.md")
SECTIONS = ("Identity", "Model and floor", "Run id and directory", "The user channel", "`session_wrote_fix`",
            "Run date", "The verifier capability", "Delivery", "Sidecars and invocation restrictions",
            "Negative tests", "Installed-package verification", "Capability labels")


def text(path=PROFILE):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TheProfile(unittest.TestCase):

    def test_twelve_sections_in_order(self):
        found = re.findall(r"^## (\d+)\. (.+)$", text(), flags=re.M)
        self.assertEqual([int(n) for n, _ in found], list(range(1, 13)))
        self.assertEqual(tuple(title for _, title in found), SECTIONS)

    def test_every_section_is_answered(self):
        bodies = re.split(r"^## \d+\. .+$", text(), flags=re.M)[1:]
        self.assertEqual(len(bodies), 12)
        for title, body in zip(SECTIONS, bodies):
            self.assertTrue(body.strip(), title)

    def test_the_sidecar_section_matches_the_cores_controls(self):
        skill = text(os.path.join(testlib.SKILL_ROOT, "SKILL.md"))
        sidecar = text(os.path.join(testlib.SKILL_ROOT, "agents", "openai.yaml"))
        manual = testlib.CORE == "handoff-v2"
        self.assertEqual("disable-model-invocation: true" in skill, manual)
        self.assertEqual("allow_implicit_invocation: false" in sidecar, manual)
        section = text().split("## 9. ")[1].split("## 10. ")[0]
        self.assertEqual("P5" in section, True)
        self.assertEqual(section.startswith("Sidecars and invocation restrictions\n\nNone"), not manual)

    def test_the_core_is_named_as_not_built(self):
        self.assertIn("not built yet", text())
        self.assertIn("phase-not-built", text())


if __name__ == "__main__":
    unittest.main()
