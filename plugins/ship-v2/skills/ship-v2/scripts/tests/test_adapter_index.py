"""E18 live run, slice A: the adapter index names every helper.

`adapters/README.md` maps each harness to its profile and helpers. Every helper file in each adapter folder (a `.py`
file directly in `adapters/claude-code/` or `adapters/codex/` whose name does not start with an underscore) is named in
the index as `<adapter>/<file>`, so a helper added to a folder cannot go unlisted.
"""
import os
import unittest

import testlib

ADAPTERS = os.path.join(testlib.SKILL, "adapters")
FOLDERS = ("claude-code", "codex")


def index():
    with open(os.path.join(ADAPTERS, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def helpers(folder):
    root = os.path.join(ADAPTERS, folder)
    return sorted(name for name in os.listdir(root)
                  if name.endswith(".py") and not name.startswith("_") and os.path.isfile(os.path.join(root, name)))


class TheAdapterIndex(unittest.TestCase):

    def test_every_helper_is_named_in_the_index(self):
        text = index()
        for folder in FOLDERS:
            found = helpers(folder)
            self.assertTrue(found, folder)
            for name in found:
                with self.subTest(helper="%s/%s" % (folder, name)):
                    self.assertIn("`%s/%s`" % (folder, name), text)


if __name__ == "__main__":
    unittest.main()
