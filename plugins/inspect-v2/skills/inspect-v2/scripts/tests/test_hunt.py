"""The hunt (E14-10, required test 5): one function, one result shape, three outcomes.

Zero, one and two candidates in each home; the `searched` list names every home looked in, the
ones not given included; tiers decide in order; the helper never expands `~` and never guesses a
home the table does not name.

The disk spelling (E14 slice 3c, item 3.3): a candidate a literal glob answers on a
case-insensitive disk is listed as its folder spells it, through the hunt and through each core's
`select`, and where the core has a `choose` command a pick named in that spelling is accepted.
Those tests are skipped on a case-sensitive scratch, by the probe blueprint's harvest test uses;
the rule for several entries or none is proved on a stubbed folder listing, on any disk.
"""
import json
import os
import unittest
from unittest import mock

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


class MetacharacterRoots(unittest.TestCase):
    """A root whose path holds a glob metacharacter (`[`, `*`, `?`) is searched as the literal
    directory it names (the E14 slice 1 checker's C1-3): the root is escaped, the home's own glob
    is not, and a glob still never leaves its root."""

    def setUp(self):
        self.tmp = testlib.make_scratch("hunt-meta-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def roots(self, mark):
        base = os.path.join(self.tmp, "base%s" % mark)
        ws, staging = os.path.join(base, "ws%s" % mark), os.path.join(base, "staging%s" % mark)
        os.makedirs(os.path.join(ws, "docs", "scope"))
        os.makedirs(staging)
        return ws, staging

    def test_one_document_in_each_home_under_each_mark(self):
        for mark in ("[1]", "*", "?"):
            for home, parts in (("repo-scope", ("docs", "scope", "2026-09-20-widget.md")),
                                ("repo-flat", ("docs", "widget-scope.md")),
                                ("staging", ("widget-scope.md",))):
                with self.subTest(mark=mark, home=home):
                    ws, staging = self.roots(mark + home)
                    path = os.path.join(staging if home == "staging" else ws, *parts)
                    testlib.write_text(path, "# a doc\n")
                    result = hunt.hunt(HOMES, {"workspace": ws, "staging": staging}, name="widget")
                    self.assertEqual((result["outcome"], [c["path"] for c in result["candidates"]]),
                                     ("one", [path]))
                    self.assertEqual([c["home"] for c in result["candidates"]], [home])
                    row = [r for r in result["searched"] if r["home"] == home][0]
                    self.assertEqual(row["found"], [path])

    def test_a_sibling_the_unescaped_root_would_match_is_not_searched(self):
        # `ws*` unescaped would also match `wsX`; escaped, only the literal `ws*` is read
        ws, staging = self.roots("*")
        other = os.path.join(os.path.dirname(ws), "wsX")
        testlib.write_text(os.path.join(other, "docs", "widget-scope.md"), "# not this root\n")
        result = hunt.hunt(HOMES, {"workspace": ws, "staging": staging}, name="widget")
        self.assertEqual((result["outcome"], result["candidates"]), ("none", []))


def case_folded(scratch):
    """True when the scratch's file system answers a name in another letter case (the probe
    blueprint's harvest test uses: CaseProbe written, caseprobe looked up)."""
    probe = os.path.join(scratch, "CaseProbe")
    testlib.write_text(probe, "x\n")
    folded = os.path.exists(os.path.join(scratch, "caseprobe"))
    os.remove(probe)
    return folded


SKIP_SENSITIVE = "the test scratch is case-sensitive (probe: CaseProbe written, caseprobe not found)"


class TheDiskSpelling(_Homes):

    def test_a_literal_glob_lists_the_file_as_the_folder_spells_it(self):
        if not case_folded(self.tmp):
            self.skipTest(SKIP_SENSITIVE)
        path = self.touch(self.ws, "docs", "Turnstile-scope.md")
        result = self.run_hunt(name="turnstile")
        self.assertEqual((result["outcome"], [c["path"] for c in result["candidates"]]),
                         ("one", [path]))
        flat = [row for row in result["searched"] if row["home"] == "repo-flat"][0]
        self.assertEqual(flat["found"], [path])

    def spelled(self, listing, name="turnstile-scope.md"):
        folder = os.path.join(self.ws, "docs")
        with mock.patch.object(hunt.os, "listdir", return_value=list(listing)):
            return hunt.disk_spelling(os.path.join(folder, name)), folder

    def test_one_entry_in_another_case_gives_its_spelling(self):
        got, folder = self.spelled(["README.md", "Turnstile-scope.md"])
        self.assertEqual(got, os.path.join(folder, "Turnstile-scope.md"))

    def test_several_entries_or_none_leave_the_path_as_found(self):
        for listing in (["Turnstile-scope.md", "TURNSTILE-scope.md"], ["gadget-scope.md"], []):
            with self.subTest(listing=listing):
                got, folder = self.spelled(listing)
                self.assertEqual(got, os.path.join(folder, "turnstile-scope.md"))

    def test_a_name_listed_as_is_is_kept(self):
        got, folder = self.spelled(["Turnstile-scope.md", "turnstile-scope.md"])
        self.assertEqual(got, os.path.join(folder, "turnstile-scope.md"))

    def test_a_folder_that_cannot_be_listed_leaves_the_path_as_found(self):
        path = os.path.join(self.tmp, "absent", "turnstile-scope.md")
        self.assertEqual(hunt.disk_spelling(path), path)


# Per core: a literal-glob hunt of its own table, the file its folder holds in another letter case,
# and, where the core has a `choose` command, a second candidate in the same tier so the hunt is
# `several` and the owner's pick can be named in the disk spelling.
THROUGH_SELECT = {
    "precon-v2": {"hunt": "scope", "file": "docs/Turnstile-scope.md", "choose": None},
    "architect-v2": {"hunt": "architecture", "file": "docs/Turnstile-architecture.md", "choose": None},
    "blueprint-v2": {"hunt": "scope", "file": "docs/Turnstile-scope.md",
                     "choose": {"second": "docs/scope/2026-09-20-turnstile.md",
                                "argv": ["--words", "the flat one"]}},
    "inspect-v2": {"hunt": "build", "file": "docs/plans/Turnstile.md",
                   "choose": {"second": "docs/plans/2026-09-20-turnstile.md",
                              "argv": ["--by", "owner", "--words", "the undated one"]}},
}


class TheDiskSpellingThroughSelect(unittest.TestCase):
    """The core's own `select` lists the disk spelling in its envelope and in selection-<hunt>.json,
    and its `choose` (blueprint-v2 and inspect-v2 carry one) accepts a pick named that way."""

    def setUp(self):
        self.tmp = testlib.make_scratch("hunt-cli-")
        self.addCleanup(testlib.rmtree, self.tmp)
        if not case_folded(self.tmp):
            self.skipTest(SKIP_SENSITIVE)
        self.case = THROUGH_SELECT[testlib.CORE]
        files = {"README.md": "# A project\n", self.case["file"]: "# Turnstile\n"}
        if self.case["choose"]:
            files[self.case["choose"]["second"]] = "# Turnstile, dated\n"
        self.ws = testlib.git_workspace(self.tmp, files=files)
        self.run_dir = os.path.join(self.tmp, "run")
        doc = os.path.join(self.tmp, "input.json")
        testlib.write_json(doc, testlib.make_input(self.ws, self.run_dir))
        code, out, err = testlib.run_driver(["check-input", doc])
        self.assertEqual(code, 0, (out, err))

    def select(self):
        code, out, err = testlib.run_driver(["select", "--run-dir", self.run_dir, "--hunt",
                                             self.case["hunt"], "--name", "turnstile"])
        self.assertEqual(code, 0, (out, err))
        return json.loads(out)

    def test_the_envelope_and_the_selection_file_carry_the_disk_spelling(self):
        spelled = os.path.join(self.ws, self.case["file"])
        envelope = self.select()
        self.assertIn(spelled, [c["path"] for c in envelope["candidates"]])
        saved = testlib.load_json(os.path.join(self.run_dir, "selection-%s.json" % self.case["hunt"]))
        self.assertIn(spelled, [c["path"] for c in saved["candidates"]])
        lowered = os.path.join(self.ws, self.case["file"].replace("Turnstile", "turnstile"))
        self.assertNotIn(lowered, [c["path"] for c in envelope["candidates"]])

    def test_a_pick_named_in_the_disk_spelling_is_accepted(self):
        if not self.case["choose"]:
            self.skipTest("%s has no `choose` command" % testlib.CORE)
        envelope = self.select()
        self.assertEqual(envelope["outcome"], "several")
        spelled = os.path.join(self.ws, self.case["file"])
        code, out, err = testlib.run_driver(["choose", "--run-dir", self.run_dir, "--hunt", self.case["hunt"],
                                             "--path", spelled] + self.case["choose"]["argv"])
        self.assertEqual(code, 0, (out, err))
        self.assertIn(spelled, out)


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
