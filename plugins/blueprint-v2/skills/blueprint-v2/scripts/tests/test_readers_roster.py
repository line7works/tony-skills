"""`readers_roster.py` (slice 3a's design, section 5): readers' roster found one way for every core.

An explicit folder is taken only when its manifest names `readers` and the roster file is there;
route 3a is the checkout sibling; route 3b the installed shape, the highest canonical version whose
folder name equals its manifest's version and that holds the roster. Nothing found raises
`RosterMissing` (a `LookupError`) naming every place looked. The fixtures are synthetic plugin
folders in a temporary directory: a checkout layout (`plugins/<core>` beside `plugins/readers`) and
an installed cache layout (`<cache>/<market>/<core>/<version>` beside
`<cache>/<market>/readers/<version>`).
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import readers_roster, sibling  # noqa: E402

ROSTER = os.path.join("skills", "readers", "assets", "roster.json")


def plugin(root, name, version, roster=True, rows=("claude-opus",)):
    testlib.write_json(os.path.join(root, ".claude-plugin", "plugin.json"), {"name": name, "version": version})
    if roster:
        testlib.write_json(os.path.join(root, ROSTER), {"rows": [{"id": row, "provider": "anthropic"} for row in rows]})
    return root


class _Layouts(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("roster-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def checkout(self):
        plugins = os.path.join(self.tmp, "plugins")
        return plugin(os.path.join(plugins, "precon-v2"), "precon-v2", "0.1.0", roster=False), plugins

    def installed(self):
        market = os.path.join(self.tmp, "cache", "market")
        return plugin(os.path.join(market, "precon-v2", "0.1.0"), "precon-v2", "0.1.0", roster=False), market


class TheArgument(_Layouts):

    def test_a_folder_naming_readers_with_its_roster_is_taken(self):
        me, _ = self.checkout()
        folder = plugin(os.path.join(self.tmp, "elsewhere", "readers"), "readers", "0.3.0", rows=("gpt",))
        found = readers_roster.find(me, folder)
        self.assertEqual((found["route"], found["root"]), ("argument", folder))
        self.assertEqual(found["roster"], os.path.join(folder, ROSTER))
        found, roster = readers_roster.load(me, folder)
        self.assertEqual(roster["rows"][0]["id"], "gpt")

    def test_a_folder_without_a_readers_manifest_or_without_its_roster_is_passed_over(self):
        me, plugins = self.checkout()
        plugin(os.path.join(plugins, "readers"), "readers", "0.1.0")
        for folder, why in ((plugin(os.path.join(self.tmp, "a"), "records", "0.1.0"), "its manifest names 'records'"),
                            (plugin(os.path.join(self.tmp, "b"), "readers", "0.1.0", roster=False), "no roster"),
                            (os.path.join(self.tmp, "c"), "no such directory")):
            found = readers_roster.find(me, folder)
            self.assertEqual(found["route"], "3a", folder)
            self.assertIn("%s (%s)" % (folder, why), found["looked"])


class Route3a(_Layouts):

    def test_the_checkout_sibling(self):
        me, plugins = self.checkout()
        plugin(os.path.join(plugins, "readers"), "readers", "0.1.0")
        found = readers_roster.find(me)
        self.assertEqual(found["route"], "3a")
        self.assertEqual(os.path.realpath(found["roster"]), os.path.realpath(os.path.join(plugins, "readers", ROSTER)))

    def test_a_checkout_sibling_without_its_roster_is_not_taken(self):
        me, plugins = self.checkout()
        plugin(os.path.join(plugins, "readers"), "readers", "0.1.0", roster=False)
        with self.assertRaises(readers_roster.RosterMissing) as caught:
            readers_roster.find(me)
        self.assertIn("(no roster)", str(caught.exception))


class Route3b(_Layouts):

    def test_the_highest_canonical_version_that_holds_the_roster(self):
        me, market = self.installed()
        base = os.path.join(market, "readers")
        plugin(os.path.join(base, "0.1.0"), "readers", "0.1.0")
        plugin(os.path.join(base, "0.2.0"), "readers", "0.2.0", rows=("second",))
        plugin(os.path.join(base, "0.9.0"), "readers", "0.3.0")            # folder name is not its version
        plugin(os.path.join(base, "01.2"), "readers", "01.2")               # not canonical digits
        plugin(os.path.join(base, "0.4.0"), "readers", "0.4.0", roster=False)
        plugin(os.path.join(base, "0.5.0"), "records", "0.5.0")             # another plugin
        os.makedirs(os.path.join(base, "0.6.0"))                            # no manifest
        found, roster = readers_roster.load(me)
        self.assertEqual((found["route"], os.path.basename(found["root"])), ("3b", "0.2.0"))
        self.assertEqual(roster["rows"][0]["id"], "second")
        looked = " ".join(found["looked"])
        for part in ("0.9.0 (name differs from version 0.3.0)", "01.2 (version not dotted integers)",
                     "0.4.0 (no roster)", "0.5.0 (its manifest names 'records')", "0.6.0 (no plugin.json)"):
            self.assertIn(part, looked)

    def test_nothing_found_names_every_place_looked(self):
        me, market = self.installed()
        argument = os.path.join(self.tmp, "nowhere")
        with self.assertRaises(LookupError) as caught:
            readers_roster.find(me, argument)
        self.assertIsInstance(caught.exception, readers_roster.RosterMissing)
        message = str(caught.exception)
        self.assertTrue(message.startswith("missing dependency: readers component (looked in: "), message)
        for place in (argument, os.path.join(me, os.pardir, "readers"),
                      os.path.join(me, os.pardir, os.pardir, "readers") + " (no such directory)"):
            self.assertIn(place, message)

    def test_an_unreadable_roster_is_missing(self):
        me, plugins = self.checkout()
        root = plugin(os.path.join(plugins, "readers"), "readers", "0.1.0")
        testlib.write_text(os.path.join(root, ROSTER), "{not json")
        with self.assertRaises(readers_roster.RosterMissing) as caught:
            readers_roster.load(me)
        self.assertIn("no readable roster", str(caught.exception))
        testlib.write_text(os.path.join(root, ROSTER), "[1, 2]")
        with self.assertRaises(readers_roster.RosterMissing):
            readers_roster.load(me)


class SiblingHelpers(unittest.TestCase):

    def test_manifest_and_version_key_are_public_and_the_old_names_kept(self):
        self.assertIs(sibling._manifest, sibling.manifest)
        self.assertIs(sibling._version_key, sibling.version_key)
        self.assertEqual(sibling.version_key("0.1.10"), (0, 1, 10))
        for name in ("01.2", "1.x", "1..2", "", "1.02"):
            self.assertIsNone(sibling.version_key(name), name)


if __name__ == "__main__":
    unittest.main()
