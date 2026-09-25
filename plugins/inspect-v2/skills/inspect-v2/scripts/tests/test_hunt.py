"""The hunt (E14-10, required test 5): one function, one result shape, three outcomes.

Zero, one and two candidates in each home; the `searched` list names every home looked in, the
ones not given included; tiers decide in order; the helper never expands `~` and never guesses a
home the table does not name.
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import hunt  # noqa: E402

HOMES = [
    {"home": "repo-scope", "root": "workspace", "globs": ["docs/scope/*-{name}.md"], "tier": 1},
    {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-scope.md"], "tier": 1},
    {"home": "staging", "root": "staging", "globs": ["{name}-scope.md"], "tier": 1},
]


class _Homes(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("hunt-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = os.path.join(self.tmp, "ws")
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(os.path.join(self.ws, "docs", "scope"))
        os.makedirs(self.staging)

    def touch(self, *parts):
        path = os.path.join(*parts)
        testlib.write_text(path, "# a doc\n")
        return path

    def run_hunt(self, homes=HOMES, name="widget", staging=True):
        return hunt.hunt(homes, {"workspace": self.ws, "staging": self.staging if staging else None},
                         name=name)


class TheShape(_Homes):

    def test_the_keys_and_the_searched_list(self):
        result = self.run_hunt()
        self.assertEqual(sorted(result), ["candidates", "outcome", "searched"])
        self.assertEqual([row["home"] for row in result["searched"]],
                         ["repo-scope", "repo-flat", "staging"])
        for row in result["searched"]:
            self.assertEqual(sorted(row), ["found", "given", "globs", "home", "root", "tier"])
            self.assertTrue(row["given"])


class EachHomeZeroOneTwo(_Homes):

    def test_zero_everywhere_is_none(self):
        result = self.run_hunt()
        self.assertEqual((result["outcome"], result["candidates"]), ("none", []))

    def test_one_in_the_repo_scope_home(self):
        path = self.touch(self.ws, "docs", "scope", "2026-09-20-widget.md")
        result = self.run_hunt()
        self.assertEqual(result["outcome"], "one")
        self.assertEqual([c["path"] for c in result["candidates"]], [path])
        self.assertEqual(result["candidates"][0]["home"], "repo-scope")

    def test_two_in_the_repo_scope_home(self):
        self.touch(self.ws, "docs", "scope", "2026-09-20-widget.md")
        self.touch(self.ws, "docs", "scope", "2026-09-22-widget.md")
        result = self.run_hunt()
        self.assertEqual(result["outcome"], "several")
        self.assertEqual(len(result["candidates"]), 2)

    def test_one_in_the_flat_home(self):
        path = self.touch(self.ws, "docs", "widget-scope.md")
        result = self.run_hunt()
        self.assertEqual((result["outcome"], [c["path"] for c in result["candidates"]]),
                         ("one", [path]))

    def test_two_across_the_flat_home(self):
        # one flat name can hold only one file; a second tier-1 home supplies the second
        self.touch(self.ws, "docs", "widget-scope.md")
        self.touch(self.staging, "widget-scope.md")
        result = self.run_hunt()
        self.assertEqual(result["outcome"], "several")
        self.assertEqual(sorted(c["home"] for c in result["candidates"]), ["repo-flat", "staging"])

    def test_one_in_the_staging_home(self):
        path = self.touch(self.staging, "widget-scope.md")
        result = self.run_hunt()
        self.assertEqual((result["outcome"], [c["path"] for c in result["candidates"]]),
                         ("one", [path]))

    def test_two_in_the_staging_home_without_a_name(self):
        self.touch(self.staging, "widget-scope.md")
        self.touch(self.staging, "gadget-scope.md")
        result = self.run_hunt(name=None)
        self.assertEqual(result["outcome"], "several")
        self.assertEqual(len(result["candidates"]), 2)

    def test_a_home_not_given_is_named_and_skipped(self):
        self.touch(self.staging, "widget-scope.md")
        result = self.run_hunt(staging=False)
        self.assertEqual(result["outcome"], "none")
        staging = [row for row in result["searched"] if row["home"] == "staging"][0]
        self.assertFalse(staging["given"])
        self.assertEqual(staging["found"], [])


class Tiers(_Homes):

    TIERED = [
        {"home": "plans", "root": "workspace", "globs": ["docs/plans/*-{name}.md"], "tier": 1},
        {"home": "flat", "root": "workspace", "globs": ["docs/{name}-build-plan.md"], "tier": 2},
    ]

    def test_the_first_tier_with_a_candidate_decides(self):
        new = self.touch(self.ws, "docs", "plans", "2026-09-20-widget.md")
        self.touch(self.ws, "docs", "widget-build-plan.md")
        result = self.run_hunt(homes=self.TIERED)
        self.assertEqual((result["outcome"], [c["path"] for c in result["candidates"]]),
                         ("one", [new]))
        flat = [row for row in result["searched"] if row["home"] == "flat"][0]
        self.assertEqual(len(flat["found"]), 1, "every home is searched and reported")

    def test_a_later_tier_decides_when_the_first_is_empty(self):
        old = self.touch(self.ws, "docs", "widget-build-plan.md")
        result = self.run_hunt(homes=self.TIERED)
        self.assertEqual((result["outcome"], [c["path"] for c in result["candidates"]]),
                         ("one", [old]))


class Refusals(_Homes):

    def test_a_name_that_is_not_one_segment_is_refused(self):
        for bad in ("../x", "a/b", "*", "a b", "", "Widget", "~x"):
            with self.assertRaises(hunt.HuntRefused, msg=bad):
                self.run_hunt(name=bad)

    def test_a_home_root_with_a_tilde_is_refused(self):
        with self.assertRaises(hunt.HuntRefused):
            hunt.hunt(HOMES, {"workspace": "~/somewhere", "staging": None}, name="widget")

    def test_a_relative_home_root_is_refused(self):
        with self.assertRaises(hunt.HuntRefused):
            hunt.hunt(HOMES, {"workspace": "relative/ws", "staging": None}, name="widget")

    def test_a_glob_that_leaves_its_home_is_refused(self):
        homes = [{"home": "x", "root": "workspace", "globs": ["../*.md"], "tier": 1}]
        with self.assertRaises(hunt.HuntRefused):
            hunt.hunt(homes, {"workspace": self.ws}, name=None)

    def test_a_root_the_table_names_but_the_caller_does_not_is_not_given(self):
        homes = [{"home": "x", "root": "elsewhere", "globs": ["*.md"], "tier": 1}]
        result = hunt.hunt(homes, {"workspace": self.ws}, name=None)
        self.assertFalse(result["searched"][0]["given"])


if __name__ == "__main__":
    unittest.main()
