"""This harness's profile, read against the core (E15 slice 1, hand-back 2: handoff-v2 built).

The twelve sections of the E9 seam, in order, every section answered; the sidecar section true to the core's
own SKILL.md and Codex sidecar (owner pick P5: the manual-only controls on handoff-v2 only); and the memory
pointer seam (A2 Q3, ruling E15-12) named in the section that carries it: on Claude Code the adapter's own step,
`pointer.py`, under a memory folder it is given; on Codex no memory pointer, the block being the pointer.
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

    def test_the_core_is_built(self):
        self.assertNotIn("not built yet", text())
        self.assertNotIn("phase-not-built", text())

    def test_the_memory_pointer_seam_is_named(self):
        section = text().split("## 7. ")[1].split("## 8. ")[0]
        self.assertIn("E15-12", section)
        if os.path.basename(testlib.ADAPTER) == "claude-code":
            self.assertIn("pointer.py", section)
            self.assertIn("--memory-dir", section)
        else:
            self.assertIn("no memory pointer", section)
            self.assertNotIn("`pointer.py`", text())


if __name__ == "__main__":
    unittest.main()
