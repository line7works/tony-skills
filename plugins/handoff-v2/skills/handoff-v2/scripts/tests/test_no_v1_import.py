"""No implicit import of a v1 station (rulings E14-7 and E15-6; the E15 back frame's copy).

Reads this core's `SKILL.md`, `references/`, `adapters/` and `scripts/` and fails on any
reference to a v1 plugin folder, on any deference that makes another file the law where this
file is silent, and on any subprocess argv that names a v1 skill.

This is the E14 test (precon-v2's copy) with its needle list widened by ruling E15-6 to the three
back-half v1 names beside the seven E14 names: the v1 vertical, handoff and ship folders. It is a
back-frame file, identical in vertical-v2, handoff-v2 and ship-v2 (`references/back-files.txt`), not a
copy of the E14 file, because its needle list differs from the front cores'.

E14-7's needle list is a floor; the control room widened it (the slice 1 checker's C1-10) to the
installed shape a core actually runs in: a v1 skill folder `skills/<v1>/` (the cache layout of an
installed plugin), a quoted `"<v1>"` path segment beside a quoted `".."` in a `join` (a climb out
of the core to a v1 folder), and a Codex `$<v1>` skill mention in an argv or a shell string. The
`-v2` names are fine in every form.

The needles are assembled at run time so this file does not trip its own scan; `V1_IMPORT_ROOT`
points the scan at another copy of the skill (the planted-reference proof uses it).
"""
import os
import re
import unittest

import testlib

V1 = ("pre" + "con", "archi" + "tect", "blue" + "print", "in" + "spect", "bu" + "ild",
      "sign" + "off", "re" + "check", "verti" + "cal", "hand" + "off", "sh" + "ip")
FOLDER_NEEDLES = ["plugins/%s/" % name for name in V1]
DEFERENCE = re.compile(r"is\s+the\s+law\s+(?:of\s+[^.]*?\s+)?(?:wherever|where)\s+this\s+file\s+is\s+silent",
                       re.IGNORECASE)
# A subprocess argv naming a v1 skill: a list literal holding a quoted "/<v1>" slash command or a
# bare v1 skill name next to an argv-building call.
ARGV = re.compile(r"""(?:subprocess\.\w+|Popen|check_output|os\.exec\w*|run)\s*\(\s*\[[^\]]*?["'](?:/|claude\s+/)?(%s)["']"""
                  % "|".join(V1))
SKILL_NEEDLES = ["skills/%s/" % name for name in V1]
_ALT = "|".join(V1)
# a quoted v1 segment and a quoted ".." inside one join(...) call, in either order; the call's
# arguments may hold one level of parentheses (`join(os.path.dirname(__file__), "..", ...)`)
_ARGS = r"""(?:[^()]|\([^()]*\))*?"""
CLIMB = re.compile(r"""join\(%s(?:["']\.\.["']%s["'](%s)["']|["'](%s)["']%s["']\.\.["'])"""
                   % (_ARGS, _ARGS, _ALT, _ALT, _ARGS))
# a Codex skill mention: `$<v1>` not followed by a name character or a hyphen (`$<v1>-v2` is fine)
DOLLAR = re.compile(r"\$(%s)(?![\w-])" % _ALT)
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
        for needle in SKILL_NEEDLES:
            if needle in text:
                out.append("%s names the v1 skill folder %s" % (rel, needle))
        for match in CLIMB.finditer(text):
            out.append("%s climbs to the v1 folder %r" % (rel, match.group(1) or match.group(2)))
        for match in DOLLAR.finditer(text):
            out.append("%s names the v1 skill %r as $%s" % (rel, match.group(1), match.group(1)))
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
    # E15-6: the three back-half names are needles too
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

    # C1-10 (the E14 slice 1 checker): the installed shape a core actually runs in
    def test_a_v1_skill_folder_in_the_installed_shape(self):
        found = self.plant("references/x.md", "Read ~/.claude/plugins/cache/m/x/1.0.0/skills/%s/SKILL.md\n" % V1[2])
        self.assertTrue(found and "v1 skill folder" in found[0], found)

    def test_a_quoted_v1_segment_beside_a_climb_in_a_join(self):
        found = self.plant("scripts/x.py", "import os\nroot = os.path.join(here, \"..\", \"..\", \"%s\")\n" % V1[2])
        self.assertTrue(found and "climbs to the v1 folder" in found[0], found)
        found = self.plant("scripts/z.py", "import os\nroot = os.path.join(os.path.dirname(__file__), '..', '%s')\n" % V1[0])
        self.assertTrue(found and "climbs to the v1 folder" in found[0], found)
        found = self.plant("scripts/y.py", "import os\nroot = os.path.join(\"%s\", '..', 'SKILL.md')\n" % V1[3])
        self.assertTrue(found and "climbs to the v1 folder" in found[0], found)

    def test_a_codex_dollar_skill_in_an_argv(self):
        found = self.plant("scripts/x.py", "import subprocess\nsubprocess.run([\"codex\", \"exec\", \"$%s\"])\n" % V1[2])
        self.assertTrue(found and "names the v1 skill" in found[0], found)
        found = self.plant("adapters/x.sh", "codex exec '$%s run the slice'\n" % V1[4])
        self.assertTrue(found and "names the v1 skill" in found[0], found)

    def test_the_v2_forms_of_the_new_needles_are_fine(self):
        self.assertEqual(self.plant("references/x.md",
                                    "skills/%s-v2/SKILL.md and $%s-v2 and $%s_dir\n" % (V1[2], V1[2], V1[4])), [])
        self.assertEqual(self.plant("scripts/x.py",
                                    "import os\nos.path.join(root, \"..\", \"%s-v2\")\n" % V1[2]), [])

    def test_each_back_half_v1_folder_is_found(self):
        for name in ("verti" + "cal", "hand" + "off", "sh" + "ip"):
            found = self.plant("references/x.md", "Read the/other/tree/plugins/%s/SKILL.md\n" % name)
            self.assertTrue(any("v1 folder plugins/%s/" % name in f for f in found), (name, found))
            found = self.plant("scripts/x.py", "import subprocess\nsubprocess.run([\"codex\", \"exec\", \"$%s\"])\n" % name)
            self.assertTrue(any("names the v1 skill %r" % name in f for f in found), (name, found))
            found = self.plant("references/y.md", "Read ~/.claude/plugins/cache/m/x/1.0.0/skills/%s/SKILL.md\n" % name)
            self.assertTrue(any("v1 skill folder skills/%s/" % name in f for f in found), (name, found))

    def test_the_v2_forms_of_the_back_half_names_are_fine(self):
        for name in ("verti" + "cal", "hand" + "off", "sh" + "ip"):
            self.assertEqual(self.plant("references/x.md", "plugins/%s-v2/ and skills/%s-v2/ and $%s-v2\n"
                                        % (name, name, name)), [], name)

    def test_a_v2_name_is_fine(self):
        self.assertEqual(self.plant("references/x.md", "plugins/%s-v2/ is a sibling\n" % V1[2]), [])


if __name__ == "__main__":
    unittest.main()
