"""E18 slice D: version bumps so an update delivers the round (the E18 plan, slice D).

Every plugin whose files slices A to C changed carries its patch version raised by one: signoff-v2, ship-v2,
vertical-v2 and handoff-v2 from 0.1.0 to 0.1.1; architect-v2, blueprint-v2, inspect-v2 and precon-v2 from 0.1.1 to
0.1.2. Each one's manifest carries the new version, its README states it wherever it states the current one, its
station's `skill-identity` reports it as `version` and `plugin_version`, and every result example that carries a
`plugin_version` carries it. In the installed shape a sibling plugin is not beside this one; its rows are reported
as SKIPPED with that reason, never as passed.

E18 fix round 1, slice C, raises signoff-v2 and ship-v2 again, from 0.1.1 to 0.1.2, so an update delivers that
round's fixes; the other six keep the versions slice D gave them. E18 fix round 2, slice C, raises the same two
from 0.1.2 to 0.1.3 for that round's fixes; the other six are unchanged.
"""
import glob
import json
import os
import re
import subprocess
import sys
import unittest

import testlib

NEW = {
    "signoff-v2": "0.1.3",
    "ship-v2": "0.1.3",
    "vertical-v2": "0.1.1",
    "handoff-v2": "0.1.1",
    "architect-v2": "0.1.2",
    "blueprint-v2": "0.1.2",
    "inspect-v2": "0.1.2",
    "precon-v2": "0.1.2",
}
OLD = {name: "0.1.0" if new == "0.1.1" else "0.1.1" for name, new in NEW.items()}
DRIVER = {
    "signoff-v2": "signoff.py",
    "ship-v2": "ship.py",
    "vertical-v2": "vertical.py",
    "handoff-v2": "handoff.py",
    "architect-v2": "architect.py",
    "blueprint-v2": "blueprint.py",
    "inspect-v2": "inspect_v2.py",
    "precon-v2": "precon.py",
}
# A README states the plugin's current version as "Version X", "plugin version X", "version X" or "the plugin, at X".
STATED = re.compile(r"(?:\b[Vv]ersion|the plugin, at) (\d+\.\d+\.\d+)")


def plugin_root(name):
    return testlib.PLUGIN if name == testlib.CORE else os.path.join(testlib.PLUGINS, name)


class TheVersions(unittest.TestCase):

    def root(self, name):
        root = plugin_root(name)
        if not os.path.isfile(os.path.join(root, ".claude-plugin", "plugin.json")):
            self.skipTest("the installed shape: %s is not beside this plugin" % name)
        return root

    def each(self, check):
        for name in sorted(NEW):
            with self.subTest(plugin=name):
                check(name, self.root(name))

    def test_each_manifest_carries_the_new_version(self):
        def check(name, root):
            manifest = testlib.load_json(os.path.join(root, ".claude-plugin", "plugin.json"))
            self.assertEqual((manifest["name"], manifest["version"]), (name, NEW[name]))
        self.each(check)

    def test_each_readme_states_the_new_version_wherever_it_states_one(self):
        def check(name, root):
            path = os.path.join(root, "README.md")
            if not os.path.isfile(path):
                self.skipTest("the installed shape: %s carries no README.md" % name)
            stated = STATED.findall(testlib.read_text(path))
            self.assertTrue(stated, "%s's README states no version" % name)
            self.assertEqual(set(stated), {NEW[name]}, stated)
            self.assertNotIn(OLD[name], stated)
        self.each(check)

    def test_each_station_s_skill_identity_reports_the_new_version(self):
        def check(name, root):
            driver = os.path.join(root, "skills", name, "scripts", DRIVER[name])
            proc = subprocess.run([sys.executable, driver, "skill-identity"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, cwd=testlib.scratch_base(), env=testlib.base_env())
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            doc = json.loads(proc.stdout.decode())
            self.assertEqual((doc["name"], doc["version"], doc["plugin_version"]), (name, NEW[name], NEW[name]), doc)
        self.each(check)

    def test_each_result_example_carries_the_new_plugin_version(self):
        def check(name, root):
            examples = os.path.join(root, "skills", name, "references", "examples")
            seen = 0
            for path in sorted(glob.glob(os.path.join(examples, "**", "*.json"), recursive=True)):
                doc = testlib.load_json(path)
                if isinstance(doc, dict) and "plugin_version" in doc:
                    seen += 1
                    self.assertEqual(doc["plugin_version"], NEW[name], path)
            self.assertGreater(seen, 0, "%s has no example carrying a plugin_version" % name)
        self.each(check)


if __name__ == "__main__":
    unittest.main()
