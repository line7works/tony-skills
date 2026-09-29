"""`sibling.py` (required test 9): a v2 sibling's root through route 3a and route 3b; a v1 name
and a v1 folder refused.

inspect-v2's code book is `blueprint-v2`'s installed `SKILL.md`, resolved this way (ruling
E14-7). The fixtures are synthetic plugin folders built in a temporary directory: a checkout
layout (`plugins/<core>` beside `plugins/blueprint-v2`) and an installed cache layout
(`<cache>/<market>/<core>/<version>` beside `<cache>/<market>/blueprint-v2/<version>`).
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import sibling  # noqa: E402


def plugin(root, name, version, skill=True):
    testlib.write_json(os.path.join(root, ".claude-plugin", "plugin.json"),
                       {"name": name, "version": version})
    if skill:
        testlib.write_text(os.path.join(root, "skills", name, "SKILL.md"),
                           "---\nname: %s\ndescription: x\n---\n\n# %s\n" % (name, name))
    return root


class _Layouts(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("sibling-")
        self.addCleanup(testlib.rmtree, self.tmp)


class Route3a(_Layouts):

    def test_the_checkout_sibling(self):
        plugins = os.path.join(self.tmp, "plugins")
        me = plugin(os.path.join(plugins, "inspect-v2"), "inspect-v2", "0.1.0")
        other = plugin(os.path.join(plugins, "blueprint-v2"), "blueprint-v2", "0.1.0")
        found = sibling.resolve("blueprint-v2", me)
        self.assertEqual(os.path.realpath(found["root"]), os.path.realpath(other))
        self.assertEqual(found["route"], "3a")
        self.assertEqual(os.path.realpath(sibling.skill_file(found["root"], "blueprint-v2")),
                         os.path.realpath(os.path.join(other, "skills", "blueprint-v2", "SKILL.md")))


class Route3b(_Layouts):

    def test_the_installed_shape_picks_the_highest_version(self):
        market = os.path.join(self.tmp, "cache", "market")
        me = plugin(os.path.join(market, "inspect-v2", "0.1.0"), "inspect-v2", "0.1.0")
        plugin(os.path.join(market, "blueprint-v2", "0.1.0"), "blueprint-v2", "0.1.0")
        high = plugin(os.path.join(market, "blueprint-v2", "0.10.0"), "blueprint-v2", "0.10.0")
        plugin(os.path.join(market, "blueprint-v2", "0.2.0"), "blueprint-v2", "0.2.0")
        found = sibling.resolve("blueprint-v2", me)
        self.assertEqual(os.path.realpath(found["root"]), os.path.realpath(high))
        self.assertEqual(found["route"], "3b")

    def test_a_folder_whose_manifest_differs_is_rejected(self):
        market = os.path.join(self.tmp, "cache", "market")
        me = plugin(os.path.join(market, "inspect-v2", "0.1.0"), "inspect-v2", "0.1.0")
        plugin(os.path.join(market, "blueprint-v2", "0.2.0"), "blueprint-v2", "0.3.0")
        with self.assertRaises(LookupError) as ctx:
            sibling.resolve("blueprint-v2", me)
        self.assertIn("name differs from version", str(ctx.exception))

    def test_nothing_found_names_every_place_looked(self):
        me = plugin(os.path.join(self.tmp, "lonely", "inspect-v2"), "inspect-v2", "0.1.0")
        with self.assertRaises(LookupError) as ctx:
            sibling.resolve("blueprint-v2", me)
        message = str(ctx.exception)
        self.assertTrue(message.startswith("missing sibling: blueprint-v2 (looked in: "), message)


class V1Refused(_Layouts):

    def test_a_v1_name_is_refused_before_any_lookup(self):
        me = plugin(os.path.join(self.tmp, "plugins", "inspect-v2"), "inspect-v2", "0.1.0")
        plugin(os.path.join(self.tmp, "plugins", "blueprint"), "blueprint", "1.0.0")
        for name in ("blueprint", "signoff", "precon", "blueprint-v1", "../blueprint", "Blueprint-v2", ""):
            with self.assertRaises(sibling.SiblingRefused, msg=name):
                sibling.resolve(name, me)

    def test_an_explicit_folder_holding_a_v1_plugin_is_refused(self):
        me = plugin(os.path.join(self.tmp, "plugins", "inspect-v2"), "inspect-v2", "0.1.0")
        v1 = plugin(os.path.join(self.tmp, "plugins", "blueprint"), "blueprint", "1.0.0")
        with self.assertRaises(sibling.SiblingRefused):
            sibling.resolve("blueprint-v2", me, argument=v1)

    def test_a_3a_folder_holding_a_v1_manifest_is_not_taken(self):
        plugins = os.path.join(self.tmp, "plugins")
        me = plugin(os.path.join(plugins, "inspect-v2"), "inspect-v2", "0.1.0")
        plugin(os.path.join(plugins, "blueprint-v2"), "blueprint", "1.0.0")
        with self.assertRaises(LookupError):
            sibling.resolve("blueprint-v2", me)

    def test_an_explicit_v2_folder_is_taken(self):
        me = plugin(os.path.join(self.tmp, "a", "inspect-v2"), "inspect-v2", "0.1.0")
        other = plugin(os.path.join(self.tmp, "b", "blueprint-v2"), "blueprint-v2", "0.1.0")
        found = sibling.resolve("blueprint-v2", me, argument=other)
        self.assertEqual((os.path.realpath(found["root"]), found["route"]), (os.path.realpath(other), "argument"))


if __name__ == "__main__":
    unittest.main()
