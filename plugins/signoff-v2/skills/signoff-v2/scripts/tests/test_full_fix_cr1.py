"""E13 full-review fix round, control-room item CR-1: signoff-v2 is manual-only on Claude Code.

Contract section 11 asks for the manual-only sidecar where the skill must not auto-trigger. Codex
reads `agents/openai.yaml` (`allow_implicit_invocation: false`); Claude Code reads the SKILL.md
frontmatter and not that sidecar, so the frontmatter carries `disable-model-invocation: true`.
"""
import os
import unittest

import testlib


def frontmatter(path):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert text.startswith("---\n"), "SKILL.md opens with a frontmatter block"
    block = text[4:text.index("\n---\n", 4)]
    out = {}
    for line in block.split("\n"):
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


class ManualOnlyOnClaudeCode(unittest.TestCase):
    def test_the_frontmatter_disables_model_invocation(self):
        fields = frontmatter(os.path.join(testlib.SKILL, "SKILL.md"))
        self.assertEqual(fields.get("disable-model-invocation"), "true", fields)

    def test_the_codex_sidecar_still_says_the_same(self):
        with open(os.path.join(testlib.SKILL, "agents", "openai.yaml")) as handle:
            self.assertIn("allow_implicit_invocation: false", handle.read())


if __name__ == "__main__":
    unittest.main()
