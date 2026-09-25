"""No implicit import of a v1 station (ruling E14-7, required tests 11 and I4).

Reads this core's `SKILL.md`, `references/`, `adapters/` and `scripts/` and fails on any
reference to a v1 plugin folder, on any deference that makes another file the law where this
file is silent, and on
any subprocess argv that names a v1 skill. The needles are assembled at run time so this file
does not trip its own scan; `V1_IMPORT_ROOT` points the scan at another copy of the skill (the
planted-reference proof uses it).
"""
import os
import re
import unittest

import testlib

V1 = ("pre" + "con", "archi" + "tect", "blue" + "print", "in" + "spect", "bu" + "ild",
      "sign" + "off", "re" + "check")
FOLDER_NEEDLES = ["plugins/%s/" % name for name in V1]
DEFERENCE = re.compile(r"is\s+the\s+law\s+(?:of\s+[^.]*?\s+)?(?:wherever|where)\s+this\s+file\s+is\s+silent",
                       re.IGNORECASE)
# A subprocess argv naming a v1 skill: a list literal holding a quoted "/<v1>" slash command or a
# bare v1 skill name next to an argv-building call.
ARGV = re.compile(r"""(?:subprocess\.\w+|Popen|check_output|os\.exec\w*|run)\s*\(\s*\[[^\]]*?["'](?:/|claude\s+/)?(%s)["']"""
                  % "|".join(V1))
SCANNED = ("SKILL.md", "references", "adapters", "scripts")
TEXT = (".md", ".py", ".json", ".txt", ".sh", ".yaml", ".yml", ".jsonl")


def root():
    return os.environ.get("V1_IMPORT_ROOT") or testlib.SKILL


def files(base):
    for part in SCANNED:
        path = os.path.join(base, part)
        if os.path.isfile(path):
            yield path
            continue
        for folder, dirs, names in os.walk(path):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(names):
                if name.endswith(TEXT):
                    yield os.path.join(folder, name)


def findings(base):
    out = []
    for path in files(base):
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        rel = os.path.relpath(path, base)
        for needle in FOLDER_NEEDLES:
            if needle in text:
                out.append("%s names the v1 folder %s" % (rel, needle))
        if DEFERENCE.search(text):
            out.append("%s defers to another file as law where it is silent" % rel)
        for match in ARGV.finditer(text):
            out.append("%s launches the v1 skill %r" % (rel, match.group(1)))
    return out


class NoV1Import(unittest.TestCase):

    def test_the_core_names_no_v1_station(self):
        self.assertEqual(findings(root()), [])

    def test_the_scan_covers_the_four_places(self):
        seen = {os.path.relpath(p, root()).split(os.sep)[0] for p in files(root())}
        self.assertEqual(seen, set(SCANNED))


class TheScanCatchesAPlant(unittest.TestCase):
    """The scan itself is proved on planted copies, so a green run is not a blind one."""

    def setUp(self):
        self.tmp = testlib.make_scratch("no-v1-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def plant(self, rel, text):
        base = os.path.join(self.tmp, "skill")
        for part in SCANNED:
            if part.endswith(".md"):
                testlib.write_text(os.path.join(base, part), "# clean\n")
            else:
                os.makedirs(os.path.join(base, part), exist_ok=True)
        testlib.write_text(os.path.join(base, rel), text)
        return findings(base)

    def test_a_v1_folder_in_a_reference(self):
        found = self.plant("references/x.md", "Read the/other/tree/%s SKILL.md\n" % FOLDER_NEEDLES[2])
        self.assertTrue(found and "v1 folder" in found[0], found)

    def test_a_deference(self):
        found = self.plant("SKILL.md", "The other station's SKILL.md is the " + "law wherever this file is silent.\n")
        self.assertTrue(found, found)

    def test_a_subprocess_naming_a_v1_skill(self):
        found = self.plant("scripts/x.py", "import subprocess\nsubprocess.run([\"claude\", \"-p\", \"/%s\"])\n" % V1[2])
        self.assertTrue(found, found)

    def test_a_v2_name_is_fine(self):
        self.assertEqual(self.plant("references/x.md", "plugins/%s-v2/ is a sibling\n" % V1[2]), [])


if __name__ == "__main__":
    unittest.main()
