"""blueprint-v2's hunts (lane L, brief 3.3 and required test 3; carried item C1-7).

`scope` holds both of its homes in ONE tier, so a `docs/scope/` doc and a flat `docs/*-scope.md`
doc are `several`, both listed, none picked; `architecture` and `build` keep the newer home ahead
of the older flat name. Each hunt is driven with zero, one and two candidates through the real
CLI. `choose` records the owner's pick among a `several` outcome, and only there.
"""
import os
import unittest

import bplib
import testlib
from test_hunt import SKIP_SENSITIVE, case_folded


class _Select(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("bp-select-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def run_with(self, files):
        ws = testlib.git_workspace(self.tmp, "ws-%d" % len(os.listdir(self.tmp)), files)
        run = bplib.Run(self.tmp, ws, name="run-%d" % len(os.listdir(self.tmp)))
        run.check_input()
        return run


class C17(_Select):

    def test_a_scope_folder_doc_and_a_flat_doc_are_several_both_listed(self):
        run = self.run_with({"README.md": "x\n", bplib.SCOPE_PATH: bplib.SCOPE,
                             "docs/turnstile-scope.md": bplib.SCOPE})
        code, out, err = run.select("scope")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["outcome"], "several")
        self.assertEqual(sorted(os.path.relpath(c["path"], run.ws) for c in out["candidates"]),
                         ["docs/scope/2026-09-20-turnstile.md", "docs/turnstile-scope.md"])
        self.assertEqual(set(c["tier"] for c in out["candidates"]), {1})

    def test_the_same_with_the_feature_name(self):
        run = self.run_with({"README.md": "x\n", bplib.SCOPE_PATH: bplib.SCOPE,
                             "docs/turnstile-scope.md": bplib.SCOPE})
        code, out, err = run.select("scope", "turnstile")
        self.assertEqual((code, out["outcome"], len(out["candidates"])), (0, "several", 2))

    def test_the_name_narrows_the_folder_home(self):
        run = self.run_with({"README.md": "x\n", bplib.SCOPE_PATH: bplib.SCOPE,
                             "docs/scope/2026-09-21-turnstile-reverse.md": bplib.SCOPE})
        self.assertEqual(run.select("scope")[1]["outcome"], "several")
        code, out, err = run.select("scope", "turnstile")
        self.assertEqual((out["outcome"], [os.path.basename(c["path"]) for c in out["candidates"]]),
                         ("one", ["2026-09-20-turnstile.md"]))


class EveryHunt(_Select):
    """Zero, one and two candidates for each hunt."""

    CASES = {
        "scope": ("turnstile", [bplib.SCOPE_PATH, "docs/turnstile-scope.md"]),
        "architecture": ("turnstile", [bplib.ARCH_PATH, "docs/architecture/2026-09-25-turnstile.md"]),
        "build": ("turnstile", [bplib.BUILD_PATH, "docs/plans/2026-09-25-turnstile.md"]),
    }

    def test_zero_one_two(self):
        for hunt, (name, paths) in sorted(self.CASES.items()):
            for count in (0, 1, 2):
                files = {"README.md": "x\n"}
                for rel in paths[:count]:
                    files[rel] = "# a doc\n"
                run = self.run_with(files)
                code, out, err = run.select(hunt, name)
                self.assertEqual(code, 0, (hunt, count, err))
                self.assertEqual(out["outcome"], ("none", "one", "several")[count], (hunt, count))
                self.assertEqual(len(out["candidates"]), count, (hunt, count))

    def test_the_newer_home_beats_the_flat_name_for_architecture_and_build(self):
        for hunt, flat in (("architecture", "docs/turnstile-architecture.md"),
                           ("build", "docs/turnstile-build-plan.md")):
            newer = self.CASES[hunt][1][0]
            run = self.run_with({"README.md": "x\n", newer: "# a\n", flat: "# b\n"})
            code, out, err = run.select(hunt, "turnstile")
            self.assertEqual((out["outcome"], os.path.relpath(out["candidates"][0]["path"], run.ws)),
                             ("one", newer), hunt)
            run2 = self.run_with({"README.md": "x\n", flat: "# b\n"})
            code, out, err = run2.select(hunt, "turnstile")
            self.assertEqual((out["outcome"], os.path.relpath(out["candidates"][0]["path"], run2.ws)),
                             ("one", flat), hunt)


class DatedNames(_Select):
    """R3 (CL1-2): a dated name matches the feature by its topic, the part after the date, whole; another
    feature whose slug ends in this one's is never taken as this feature's doc."""

    def test_another_features_dated_doc_is_none_for_this_feature(self):
        for hunt, rel in (("build", "docs/plans/2026-09-22-big-turnstile.md"),
                          ("scope", "docs/scope/2026-09-20-reverse-turnstile.md"),
                          ("architecture", "docs/architecture/2026-09-21-big-turnstile.md")):
            run = self.run_with({"README.md": "x\n", rel: "# another feature's doc\n"})
            code, out, err = run.select(hunt, "turnstile")
            self.assertEqual(code, 0, err)
            self.assertEqual((out["outcome"], out["candidates"]), ("none", []), (hunt, rel))

    def test_the_feature_beside_another_is_one(self):
        run = self.run_with({"README.md": "x\n", "docs/plans/2026-09-22-big-turnstile.md": "# a\n",
                             bplib.BUILD_PATH: "# b\n"})
        code, out, err = run.select("build", "turnstile")
        self.assertEqual((out["outcome"], [os.path.relpath(c["path"], run.ws) for c in out["candidates"]]),
                         ("one", [bplib.BUILD_PATH]))

    def test_an_undated_prefix_is_not_a_date(self):
        run = self.run_with({"README.md": "x\n", "docs/plans/v2-turnstile.md": "# a\n"})
        self.assertEqual(run.select("build", "turnstile")[1]["outcome"], "none")

    def test_an_undated_doc_in_the_scope_or_architecture_folder_is_no_home(self):
        # round 3, R6 (CL2-4): those folders' v1 home is the dated name only; an undated `<topic>.md` is none
        # (the build hunt's plans folder takes one since round 5, R2: `UndatedPlans`)
        for hunt, rel in (("scope", "docs/scope/turnstile.md"), ("architecture", "docs/architecture/turnstile.md")):
            for name in ("turnstile", None):
                run = self.run_with({"README.md": "x\n", rel: "# a\n"})
                code, out, err = run.select(hunt, name)
                self.assertEqual(code, 0, err)
                self.assertEqual((out["outcome"], out["candidates"]), ("none", []), (hunt, name))

    def test_the_hunt_table_holds_the_v1_homes_only(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("blueprint_driver_homes", testlib.DRIVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        dated = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-{name}.md"
        self.assertEqual(sorted((hunt, g, home["tier"]) for hunt, homes in module.HUNTS.items()
                                for home in homes for g in home["globs"]),
                         sorted([("architecture", "docs/architecture/" + dated, 1),
                                 ("architecture", "docs/{name}-architecture.md", 2),
                                 ("build", "docs/plans/" + dated, 1), ("build", "docs/plans/{name}.md", 1),
                                 ("build", "docs/{name}-build-plan.md", 2),
                                 ("scope", "docs/scope/" + dated, 1), ("scope", "docs/{name}-scope.md", 1)]))

    def test_with_no_name_every_dated_doc_is_a_candidate(self):
        run = self.run_with({"README.md": "x\n", bplib.SCOPE_PATH: bplib.SCOPE,
                             "docs/scope/2026-09-21-turnstile-reverse.md": bplib.SCOPE})
        code, out, err = run.select("scope")
        self.assertEqual((out["outcome"], len(out["candidates"])), ("several", 2))


class Choose(_Select):

    def several(self):
        run = self.run_with({"README.md": "x\n", bplib.SCOPE_PATH: bplib.SCOPE,
                             "docs/turnstile-scope.md": bplib.SCOPE})
        run.select("scope")
        return run

    def choose(self, run, path, words="take the one under docs/scope", hunt="scope"):
        return run.cli(["choose", "--run-dir", run.run_dir, "--hunt", hunt, "--path", path,
                        "--words", words])

    def test_the_owners_pick_is_recorded_with_his_words(self):
        run = self.several()
        target = os.path.join(run.ws, bplib.SCOPE_PATH)
        code, out, err = self.choose(run, target)
        self.assertEqual(code, 0, err)
        self.assertEqual(out["chosen"]["path"], target)
        saved = testlib.load_json(os.path.join(run.run_dir, "selection-scope.json"))
        self.assertEqual(saved["outcome"], "several")
        self.assertEqual(len(saved["candidates"]), 2)
        self.assertEqual(saved["chosen"], {"path": target, "by": "owner",
                                           "words": "take the one under docs/scope"})

    def test_a_path_that_is_not_a_candidate_is_usage(self):
        run = self.several()
        before = testlib.sha256_file(os.path.join(run.run_dir, "selection-scope.json"))
        code, out, err = self.choose(run, os.path.join(run.ws, "README.md"))
        self.assertEqual(code, 2, err)
        self.assertEqual(before, testlib.sha256_file(os.path.join(run.run_dir, "selection-scope.json")))

    def test_blank_words_are_usage(self):
        run = self.several()
        code, out, err = self.choose(run, os.path.join(run.ws, bplib.SCOPE_PATH), words="  ")
        self.assertEqual(code, 2, err)

    def test_invisible_words_are_usage_and_nothing_written(self):
        # CL4-1: the words test is the frame's own `bare`, so words of an invisible character only are no
        # words (a zero width space, a byte order mark, a left-to-right mark), on a first pick and on a rerun
        for label, words in (("U+200B", "\u200b"), ("BOM", "\ufeff"), ("LRM", "\u200e")):
            run = self.several()
            target = os.path.join(run.ws, bplib.SCOPE_PATH)
            selection = os.path.join(run.run_dir, "selection-scope.json")
            before = testlib.sha256_file(selection)
            code, out, err = self.choose(run, target, words=words)
            self.assertEqual(code, 2, (label, out, err))
            self.assertEqual(before, testlib.sha256_file(selection), label)
            code, out, err = self.choose(run, target)
            self.assertEqual(code, 0, (label, err))
            picked = testlib.sha256_file(selection)
            code, out, err = self.choose(run, target, words=" %s " % words)
            self.assertEqual(code, 2, (label, out, err))
            self.assertEqual(picked, testlib.sha256_file(selection), label)
            self.assertEqual(testlib.load_json(selection)["chosen"]["words"], "take the one under docs/scope")

    def test_only_a_several_outcome_takes_a_choice(self):
        run = self.run_with({"README.md": "x\n", bplib.SCOPE_PATH: bplib.SCOPE})
        run.select("scope")
        code, out, err = self.choose(run, os.path.join(run.ws, bplib.SCOPE_PATH))
        self.assertEqual(code, 2, err)
        code, out, err = self.choose(run, os.path.join(run.ws, bplib.SCOPE_PATH), hunt="build")
        self.assertEqual(code, 2, err)

    def test_choose_after_harvest_is_the_wrong_phase(self):
        run = self.run_with(bplib.base_files())
        run.select_all()
        self.assertEqual(run.harvest()[0], 0)
        code, out, err = self.choose(run, os.path.join(run.ws, bplib.SCOPE_PATH))
        self.assertEqual(code, 2, err)


class ChooseInEitherSpelling(_Select):
    """C3C1-1's class: the hunt lists a literal glob's match as its folder spells it
    (`docs/Turnstile-scope.md`), and the owner's pick is the same file named in the idea's case
    (`docs/turnstile-scope.md`), which `choose` took before the hunt respelled it. The pick is
    accepted and recorded in the disk spelling, as a pick named that way is. Skipped on a
    case-sensitive scratch, by the shared hunt test's probe."""

    def test_a_pick_in_the_ideas_case_is_recorded_in_the_disk_spelling(self):
        if not case_folded(self.tmp):
            self.skipTest(SKIP_SENSITIVE)
        spelled = "docs/Turnstile-scope.md"
        for typed in (spelled, "docs/turnstile-scope.md"):
            with self.subTest(path=typed):
                run = self.run_with({"README.md": "x\n", bplib.SCOPE_PATH: bplib.SCOPE, spelled: bplib.SCOPE})
                code, out, err = run.select("scope")
                self.assertEqual((code, out["outcome"]), (0, "several"), err)
                disk = os.path.join(run.ws, spelled)
                self.assertIn(disk, [c["path"] for c in out["candidates"]])
                code, out, err = run.cli(["choose", "--run-dir", run.run_dir, "--hunt", "scope", "--path",
                                          os.path.join(run.ws, typed), "--words", "the flat one"])
                self.assertEqual(code, 0, err)
                self.assertEqual(out["chosen"]["path"], disk)
                saved = testlib.load_json(os.path.join(run.run_dir, "selection-scope.json"))
                self.assertEqual(saved["chosen"], {"path": disk, "by": "owner", "words": "the flat one"})
                run.select("architecture")
                run.select("build", "turnstile")
                code, out, err = run.harvest()
                self.assertEqual(code, 0, err)
                self.assertEqual(out["scope"]["path"], disk)


class UndatedPlans(_Select):
    """Round 5, R2 (the outside reviewer's L-5): the build hunt's first tier matches both
    `docs/plans/<date>-<topic>.md` and `docs/plans/<topic>.md` (contract section 11: `select` over
    `docs/plans/*.md` by topic, then the flat name); several first-tier matches are listed, never picked;
    the flat `docs/<topic>-build-plan.md` stays second."""

    UNDATED = "docs/plans/turnstile.md"
    FLAT = "docs/turnstile-build-plan.md"

    def found(self, files):
        run = self.run_with(dict({"README.md": "x\n"}, **files))
        code, out, err = run.select("build", "turnstile")
        self.assertEqual(code, 0, err)
        return out["outcome"], sorted((os.path.relpath(c["path"], run.ws), c["tier"]) for c in out["candidates"])

    def test_an_existing_undated_plan_alone_is_one(self):
        self.assertEqual(self.found({self.UNDATED: bplib.BUILD_FILLED}), ("one", [(self.UNDATED, 1)]))

    def test_an_undated_plan_and_its_dated_twin_are_several_both_listed(self):
        self.assertEqual(self.found({self.UNDATED: bplib.BUILD_FILLED, bplib.BUILD_PATH: bplib.BUILD_FILLED}),
                         ("several", [(bplib.BUILD_PATH, 1), (self.UNDATED, 1)]))

    def test_the_flat_build_plan_is_still_second(self):
        self.assertEqual(self.found({self.FLAT: bplib.BUILD_FILLED}), ("one", [(self.FLAT, 2)]))
        self.assertEqual(self.found({self.FLAT: bplib.BUILD_FILLED, self.UNDATED: bplib.BUILD_FILLED}),
                         ("one", [(self.UNDATED, 1)]))

    def test_another_features_undated_plan_is_not_this_one(self):
        # (a re-cased `Turnstile.md` is left out: on a case-insensitive file system it IS `turnstile.md`)
        for rel in ("docs/plans/big-turnstile.md", "docs/plans/turnstile-v2.md", "docs/plans/v2-turnstile.md",
                    "docs/plans/turnstile.md.bak", "docs/plans/sub/turnstile.md"):
            self.assertEqual(self.found({rel: "# a\n"}), ("none", []), rel)

    def test_the_undated_plan_is_extended_where_it_lies_and_never_forked(self):
        ws = testlib.git_workspace(self.tmp, "ws-extend", dict(bplib.base_files(), **{self.UNDATED: bplib.BUILD_FILLED}))
        run = bplib.Run(self.tmp, ws, name="run-extend")
        harvest = run.to_harvest()
        target = os.path.join(ws, self.UNDATED)
        self.assertEqual(harvest["target"], target)
        code, out, err = run.record(bplib.extension_answer())
        self.assertEqual(code, 0, (out, err))
        code, out, err = run.write()
        self.assertEqual((code, out["doc"], out["action"]), (0, target, "extended"), (out, err))
        self.assertEqual(sorted(os.listdir(os.path.join(ws, "docs", "plans"))), ["turnstile.md"])
        self.assertIn("## Slice B", bplib.read(target))

    def test_an_undated_plan_and_its_dated_twin_stop_harvest_unpicked(self):
        ws = testlib.git_workspace(self.tmp, "ws-twin", dict(bplib.base_files(build=bplib.BUILD_FILLED),
                                                             **{self.UNDATED: bplib.BUILD_FILLED}))
        run = bplib.Run(self.tmp, ws, name="run-twin")
        run.check_input()
        run.select_all()
        code, out, err = run.harvest()
        self.assertEqual((code, out["stop_tag"]), (10, "selection-several"), (out, err))
        self.assertIn(self.UNDATED, out["reason"])
        self.assertIn(bplib.BUILD_PATH, out["reason"])


if __name__ == "__main__":
    unittest.main()
