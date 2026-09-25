"""Selection (lane contract section 4, required test 3), through the real CLI.

The build hunt's three tiers (the two-source narrowing, `docs/plans/*-<name>.md` then the flat
`docs/<name>-build-plan.md`, then the phase or slice fallback), each tier deciding when it holds a
candidate; the scope hunt by glob over every home (`docs/scope/*.md`, `docs/*-scope.md`, the
staging home's `*-scope.md`), `several` listed, never picked; and `choose`, the core's own command
that records the executor's Intent match or the owner's pick, only among the listed candidates.
"""
import os
import unittest

import ilib
import testlib


class _Select(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("select-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(self.staging)

    def runner(self, files, build=ilib.BUILD_DOC, scope=None):
        ws = ilib.workspace(self.tmp, build=build, scope=scope, extra=files)
        run = ilib.Runner(self.tmp, ws)
        code, doc, out, err = run.check(ilib.make_input(ws, run.run_dir, staging=self.staging))
        self.assertEqual(code, 0, out + err)
        return run

    def select(self, run, hunt, name=None):
        args = ["--hunt", hunt] + (["--name", name] if name else [])
        code, doc, out, err = run.phase("select", *args)
        self.assertEqual(code, 0, out + err)
        return doc

    def rel(self, run, doc):
        return sorted(os.path.relpath(c["path"], run.ws) for c in doc["candidates"])


class TheBuildHunt(_Select):

    def test_tier_one_beats_the_flat_name_and_the_fallback(self):
        run = self.runner({"docs/turnstile-build-plan.md": "# flat\n", "docs/phase-1.md": "# p\n"})
        doc = self.select(run, "build", "turnstile")
        self.assertEqual((doc["outcome"], self.rel(run, doc)), ("one", [ilib.BUILD_REL]))

    def test_the_flat_name_when_no_plans_doc(self):
        run = self.runner({"docs/turnstile-build-plan.md": "# flat\n", "docs/phase-1.md": "# p\n"}, build=None)
        doc = self.select(run, "build", "turnstile")
        self.assertEqual((doc["outcome"], self.rel(run, doc)), ("one", ["docs/turnstile-build-plan.md"]))

    def test_the_fallback_lists_several_and_picks_none(self):
        run = self.runner({"docs/phase-1.md": "# p\n", "plan/slices.md": "# s\n"}, build=None)
        doc = self.select(run, "build", "turnstile")
        self.assertEqual(doc["outcome"], "several")
        self.assertEqual(self.rel(run, doc), ["docs/phase-1.md", "plan/slices.md"])

    def test_two_plans_for_one_name_are_several(self):
        run = self.runner({"docs/plans/2026-09-23-turnstile.md": ilib.BUILD_DOC})
        doc = self.select(run, "build", "turnstile")
        self.assertEqual(doc["outcome"], "several")
        self.assertEqual(len(doc["candidates"]), 2)

    def test_none_when_no_doc_is_written(self):
        run = self.runner({}, build=None)
        doc = self.select(run, "build", "turnstile")
        self.assertEqual((doc["outcome"], doc["candidates"]), ("none", []))
        self.assertEqual([row["home"] for row in doc["searched"]], ["repo-plans", "repo-flat", "phase-or-slice"])


class TheScopeHunt(_Select):

    def test_every_home_is_searched_and_several_are_listed(self):
        testlib.write_text(os.path.join(self.staging, "turnstile-scope.md"), ilib.SCOPE_DOC)
        run = self.runner({ilib.SCOPE_REL: ilib.SCOPE_DOC, "docs/turnstile-scope.md": ilib.SCOPE_DOC})
        doc = self.select(run, "scope")
        self.assertEqual(doc["outcome"], "several")
        self.assertEqual(len(doc["candidates"]), 3)
        self.assertEqual(sorted(r["home"] for r in doc["searched"]), ["repo-flat", "repo-scope", "staging"])
        self.assertTrue(all(r["given"] for r in doc["searched"]))

    def test_the_scope_hunt_never_guesses_a_slug(self):
        run = self.runner({"docs/scope/2026-09-20-other-name.md": ilib.SCOPE_DOC})
        doc = self.select(run, "scope")
        self.assertEqual(self.rel(run, doc), ["docs/scope/2026-09-20-other-name.md"])

    def test_no_scope_doc_is_none(self):
        run = self.runner({})
        doc = self.select(run, "scope")
        self.assertEqual(doc["outcome"], "none")


class Choose(_Select):

    def test_choose_takes_only_a_listed_candidate(self):
        run = self.runner({ilib.SCOPE_REL: ilib.SCOPE_DOC, "docs/turnstile-scope.md": ilib.SCOPE_DOC})
        self.select(run, "scope")
        outside = os.path.join(run.ws, "README.md")
        code, doc, out, err = run.phase("choose", "--hunt", "scope", "--path", outside, "--by", "intent")
        self.assertEqual(code, 2, out + err)
        target = os.path.join(run.ws, ilib.SCOPE_REL)
        code, doc, out, err = run.phase("choose", "--hunt", "scope", "--path", target, "--by", "intent")
        self.assertEqual(code, 0, out + err)
        self.assertEqual((doc["chosen"], doc["by"]), (target, "intent"))
        self.assertEqual(run.artifact("checkpoint.json")["choices"]["scope"]["path"], target)

    def test_choose_on_a_hunt_that_was_not_several(self):
        run = self.runner({ilib.SCOPE_REL: ilib.SCOPE_DOC})
        self.select(run, "scope")
        target = os.path.join(run.ws, ilib.SCOPE_REL)
        code, doc, out, err = run.phase("choose", "--hunt", "scope", "--path", target, "--by", "intent")
        self.assertEqual(code, 2, out + err)

    def test_the_owner_pick_carries_his_words(self):
        run = self.runner({"docs/plans/2026-09-23-turnstile.md": ilib.BUILD_DOC})
        self.select(run, "build", "turnstile")
        target = os.path.join(run.ws, ilib.BUILD_REL)
        code, doc, out, err = run.phase("choose", "--hunt", "build", "--path", target, "--by", "owner")
        self.assertEqual(code, 2, "an owner pick without his words is usage: " + out + err)
        code, doc, out, err = run.phase("choose", "--hunt", "build", "--path", target, "--by", "owner",
                                        "--words", "take the 22nd one")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(doc["words"], "take the 22nd one")

    def test_an_intent_match_is_not_the_build_hunts(self):
        run = self.runner({"docs/plans/2026-09-23-turnstile.md": ilib.BUILD_DOC})
        self.select(run, "build", "turnstile")
        target = os.path.join(run.ws, ilib.BUILD_REL)
        code, doc, out, err = run.phase("choose", "--hunt", "build", "--path", target, "--by", "intent")
        self.assertEqual(code, 0, "an Intent match settles a build doc tie too (v1 Step 1): " + out + err)


if __name__ == "__main__":
    unittest.main()
