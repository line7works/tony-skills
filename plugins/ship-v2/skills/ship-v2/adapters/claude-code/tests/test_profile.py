"""This harness's profile, read against the core (E15 slice 2, ship-v2).

The twelve sections of the E9 seam, in order, each answered; the core named as built; the sidecar section true to
the core's own SKILL.md and Codex sidecar (owner pick P5: no manual-only control on ship-v2); and the one seam v1
held in a harness tool, the Stop-hook check (ruling E15-12), named in section 7 with its helper: on Claude Code a
reading of this session's own transcript, on Codex `Hook: NOT armed`, labelled honestly.
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
        self.assertNotIn("disable-model-invocation: true", skill)
        self.assertNotIn("allow_implicit_invocation: false", sidecar)
        section = text().split("## 9. ")[1].split("## 10. ")[0]
        self.assertIn("P5", section)
        self.assertTrue(section.startswith("Sidecars and invocation restrictions\n\nNone"))

    def test_the_core_is_built(self):
        self.assertNotIn("not built yet", text())
        self.assertNotIn("phase-not-built", text())

    def test_the_stop_hook_seam_is_named(self):
        section = text().split("## 7. ")[1].split("## 8. ")[0]
        self.assertIn("E15-12", section)
        self.assertIn("hook.py", section)
        if os.path.basename(testlib.ADAPTER) == "claude-code":
            self.assertIn("transcript", section)
            self.assertIn("helper-derived", section)
        else:
            self.assertIn("Hook: NOT armed", section)


if __name__ == "__main__":
    unittest.main()
