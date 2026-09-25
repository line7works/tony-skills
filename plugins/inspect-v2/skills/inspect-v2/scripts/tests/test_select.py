"""Selection (lane contract section 4, required test 3), through the real CLI.

The build hunt's three tiers (the two-source narrowing, `docs/plans/*-<name>.md` then the flat
`docs/<name>-build-plan.md`, then the phase or slice fallback), each tier deciding when it holds a
candidate; the scope hunt by glob over every home (`docs/scope/*.md`, `docs/*-scope.md`, the
staging home's `*-scope.md`), `several` listed, never picked; and `choose`, the core's own command
that records the executor's Intent match or the owner's pick, only among the listed candidates.
"""
import json
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


class TheStationFields(_Select):

    def test_a_blank_station_field_is_refused_at_check_input(self):
        # CI1-14: a whitespace-only model, displayed model or session model is a blank field
        for key in ("model", "displayed_model", "session_model"):
            with self.subTest(key=key):
                ws = ilib.workspace(self.tmp, name="ws-" + key)
                run = ilib.Runner(self.tmp, ws, run_dir=os.path.join(self.tmp, "run-" + key))
                code, doc, out, err = run.check(ilib.make_input(ws, run.run_dir, **{key: "   "}))
                self.assertEqual(code, 4, out + err)
                self.assertIn(key, json.dumps(doc["errors"]))
                self.assertFalse(os.path.exists(run.run_dir))


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


class Named(_Select):
    """R6 (CI1-10): v1's "the invocation names a build doc". `named --path P` takes one existing `.md`
    inside the workspace (by its real path, never through a link out) as the build hunt's `one`, home
    `named`; a doc outside every build home adds its own directory's `scope/*.md` and `*-scope.md` to
    this run's scope hunt (v1 Step 1)."""

    DOC = "notes/turnstile/plan.md"

    def named(self, run, path):
        return run.phase("named", "--path", path)

    def test_a_doc_outside_every_home_is_taken_as_one_named(self):
        run = self.runner({self.DOC: ilib.BUILD_DOC, "notes/turnstile/scope/2026-09-20-turnstile.md": ilib.SCOPE_DOC},
                          build=None)
        code, doc, out, err = self.named(run, os.path.join(run.ws, self.DOC))
        self.assertEqual(code, 0, out + err)
        sel = run.artifact("selection-build.json")
        self.assertEqual((sel["outcome"], [c["home"] for c in sel["candidates"]]), ("one", ["named"]))
        self.assertEqual(os.path.relpath(sel["candidates"][0]["path"], run.ws), self.DOC)
        scope = self.select(run, "scope")
        self.assertEqual((scope["outcome"], self.rel(run, scope)), ("one", ["notes/turnstile/scope/2026-09-20-turnstile.md"]))
        self.assertIn("named-dir-scope", [r["home"] for r in scope["searched"]])
        code, doc, out, err = run.phase("harvest")
        self.assertEqual(code, 0, out + err)
        harvest = run.artifact("harvest.json")
        self.assertEqual((harvest["build_doc"]["rel"], harvest["build_doc"]["how"]), (self.DOC, "named"))
        self.assertFalse(harvest["no_record"])

    def test_a_flat_scope_doc_beside_the_named_doc(self):
        run = self.runner({self.DOC: ilib.BUILD_DOC, "notes/turnstile/turnstile-scope.md": ilib.SCOPE_DOC}, build=None)
        self.assertEqual(self.named(run, self.DOC)[0], 0, "a workspace-relative path is taken too")
        scope = self.select(run, "scope")
        self.assertEqual(self.rel(run, scope), ["notes/turnstile/turnstile-scope.md"])

    def test_a_doc_inside_a_home_adds_no_scope_home(self):
        run = self.runner({})
        self.assertEqual(self.named(run, os.path.join(run.ws, ilib.BUILD_REL))[0], 0)
        scope = self.select(run, "scope")
        self.assertEqual(sorted(r["home"] for r in scope["searched"]), ["repo-flat", "repo-scope", "staging"])

    def test_what_is_refused(self):
        outside = os.path.join(self.tmp, "elsewhere-plan.md")
        testlib.write_text(outside, ilib.BUILD_DOC)
        run = self.runner({"notes/plan.txt": "not markdown\n", "notes/folder.md/x": "a folder named .md\n"})
        os.symlink(outside, os.path.join(run.ws, "notes", "linked-plan.md"))
        for path in (outside, os.path.join(run.ws, "notes", "linked-plan.md"), os.path.join(run.ws, "notes", "plan.txt"),
                     os.path.join(run.ws, "notes", "missing.md"), os.path.join(run.ws, "notes", "folder.md"),
                     "../elsewhere-plan.md"):
            with self.subTest(path=path):
                code, doc, out, err = self.named(run, path)
                self.assertEqual(code, 2, out + err)
                self.assertNotIn("invalid choice", err, "refused by the command, not by the parser")
                self.assertFalse(os.path.exists(os.path.join(run.run_dir, "selection-build.json")))

    def test_named_after_harvest_is_usage(self):
        run = self.runner({})
        self.select(run, "build", "turnstile")
        self.select(run, "scope")
        self.assertEqual(run.phase("harvest")[0], 0)
        code, doc, out, err = self.named(run, ilib.BUILD_REL)
        self.assertEqual(code, 2, out + err)
        self.assertIn("harvested", err)


if __name__ == "__main__":
    unittest.main()
