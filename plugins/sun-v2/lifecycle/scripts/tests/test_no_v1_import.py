"""No implicit import of v1 (the contract's E16-16; section 12's family T1).

Reads every text file of this plugin and fails on a path under the v1 plugin's folder, on a v1 skill's
folder, on a climb out of this plugin to one, on any deference that makes another skill's file the law
where this one is silent, and on any subprocess argument that names a v1 skill. The `-v2` names are
fine in every form. The needles are assembled at run time, so this file does not trip its own scan;
`V1_IMPORT_ROOT` points the scan at another copy of the plugin (the planted-reference proof uses it).
"""
import os
import re
import shutil
import tempfile
import unittest

import harness

PLUGIN_V1 = "s" + "un"
SKILLS_V1 = ("sun" + "rise", "sun" + "set")
FOLDER_NEEDLES = ["plugins/%s/" % PLUGIN_V1, "plugins/%s\"" % PLUGIN_V1, "plugins/%s'" % PLUGIN_V1]
SKILL_NEEDLES = ["skills/%s/" % name for name in SKILLS_V1]
_ALT = "|".join(SKILLS_V1)
DEFERENCE = re.compile(r"is\s+the\s+law\s+(?:of\s+[^.]*?\s+)?(?:wherever|where)\s+this\s+(?:file|skill)\s+is\s+silent", re.IGNORECASE)
ARGV = re.compile(r"""(?:subprocess\.\w+|Popen|check_output|os\.exec\w*|run)\s*\(\s*\[[^\]]*?["'](?:/|claude\s+/|\$)(%s)["']""" % _ALT)
_ARGS = r"""(?:[^()]|\([^()]*\))*?"""
CLIMB = re.compile(r"""join\(%s["']\.\.["']%s["'](%s)["']""" % (_ARGS, _ARGS, PLUGIN_V1 + "|" + _ALT))
DOLLAR = re.compile(r"\$(%s)(?![\w-])" % _ALT)
TEXT = (".md", ".py", ".json", ".txt", ".sh", ".yaml", ".yml", ".jsonl", "")


def root():
    return os.environ.get("V1_IMPORT_ROOT") or harness.PLUGIN


def files(base):
    for folder, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            if os.path.splitext(name)[1] in TEXT:
                yield os.path.join(folder, name)


def findings(base):
    out = []
    for path in files(base):
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        rel = os.path.relpath(path, base)
        for needle in FOLDER_NEEDLES:
            if needle in text:
                out.append("%s names the v1 plugin folder" % rel)
        for needle in SKILL_NEEDLES:
            if needle in text:
                out.append("%s names a v1 skill folder" % rel)
        for match in CLIMB.finditer(text):
            out.append("%s climbs out to the v1 folder %r" % (rel, match.group(1)))
        for match in DOLLAR.finditer(text):
            out.append("%s names the v1 skill %r as a skill mention" % (rel, match.group(1)))
        if DEFERENCE.search(text):
            out.append("%s defers to another file as law where it is silent" % rel)
        for match in ARGV.finditer(text):
            out.append("%s launches the v1 skill %r" % (rel, match.group(1)))
    return out


PLANTS = {
    "a v1 path": ("lifecycle/scripts/sun_core/facts.py", ["\nV1 = \"plugins/", PLUGIN_V1, "/assets/rise.wav\"\n"]),
    "a v1 skill folder": ("skills/sunrise-v2/SKILL.md", ["\nRead skills/", SKILLS_V1[0], "/SKILL.md for the forms.\n"]),
    "a deference": ("skills/sunset-v2/SKILL.md", ["\nThe v1 skill's text is the ", "law where this skill is silent.\n"]),
    "a subprocess that names a v1 skill": ("lifecycle/scripts/sun.py", ["\nimport subprocess\nsubprocess.run([\"claude\", \"/", SKILLS_V1[1], "\"])\n"]),
    "a skill mention": ("lifecycle/skills.json", ["\n$", SKILLS_V1[0], "\n"]),
}


class NoV1Import(unittest.TestCase):
    def test_no_v1_import(self):
        self.assertEqual(findings(root()), [])

    def test_the_scan_reads_the_whole_plugin(self):
        seen = set(os.path.relpath(p, root()).split(os.sep)[0] for p in files(root()))
        self.assertTrue({"lifecycle", "skills", ".claude-plugin"} <= seen, seen)

    def test_no_v1_import_fails_on_a_scratch_copy_with_a_planted_v1_reference(self):
        for label, (rel, parts) in PLANTS.items():
            tmp = tempfile.mkdtemp(prefix="sunv2-t1-")
            try:
                copy = os.path.join(tmp, "sun-v2")
                shutil.copytree(harness.PLUGIN, copy, ignore=shutil.ignore_patterns("__pycache__"))
                self.assertEqual(findings(copy), [], "the copy is not clean before the plant")
                with open(os.path.join(copy, rel), "a", encoding="utf-8") as fh:
                    fh.write("".join(parts))
                found = findings(copy)
                self.assertTrue(found, "the scan passed a copy with %s planted" % label)
                self.assertTrue(all(f.startswith(rel) for f in found), found)
            finally:
                shutil.rmtree(tmp, True)


if __name__ == "__main__":
    unittest.main()
