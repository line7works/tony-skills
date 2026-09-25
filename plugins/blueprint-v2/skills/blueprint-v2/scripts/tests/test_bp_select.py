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

    def test_an_undated_doc_named_by_the_topic_is_one(self):
        for hunt, rel in (("build", "docs/plans/turnstile.md"), ("scope", "docs/scope/turnstile.md"),
                          ("architecture", "docs/architecture/turnstile.md")):
            run = self.run_with({"README.md": "x\n", rel: "# a\n"})
            code, out, err = run.select(hunt, "turnstile")
            self.assertEqual((out["outcome"], [os.path.relpath(c["path"], run.ws) for c in out["candidates"]]),
                             ("one", [rel]), hunt)

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


if __name__ == "__main__":
    unittest.main()
