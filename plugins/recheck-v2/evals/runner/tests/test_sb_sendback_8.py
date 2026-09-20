"""Send-back 8, defect 1: the one credential store a condition reaches through a link.

The measured failure (control room, 2026-09-19, root `wall-proof-codex-20260920T005305Z`):
`trials/codex-F1-01-fixed-clean-absent-r1` ended `launch_failed`, exit 1, `turn.failed` with
`401 Unauthorized: Missing bearer or basic authentication in header`. The Codex install keeps
ONE credential file (`setups/codex/install.sh` lines 47 to 57 and 94 to 108): every derived
home's `auth.json` and `child/auth.json` is a SYMLINK to the base home's store. The base home
IS the `available` condition's home, so for the `absent` condition the link's target sits
under `another condition's home for this setup`, which the profile refuses. Codex found no
credential and fell back to an unauthenticated call.

What these tests pin, with a FAKE two-home layout this file builds under the TEST pilot root
and no machine path anywhere:

1. the spec names the ONE RESOLVED store as a `write_files` LITERAL, not a subpath, and names
   it once however many links point at it;
2. a condition whose store is inside its own home produces NO extra row;
3. a setup that declares no `credential_store` (Claude Code) produces no extra row, so its
   spec is unchanged;
4. through the REAL `setups/_wall/write-sandbox-profile.py` and a REAL `sandbox-exec` child:
   the literal READS and APPENDS (Codex rewrites the store on a token refresh, so read-only
   in one condition and writable in the other would be a with/without difference the
   comparison must not carry), the link in the launch's own home resolves to it, and every
   sibling in that same refused home — the native check's sentinel, `config.toml`, `skills/`,
   `plugins/`, `sessions/` — is still refused by the kernel;
5. the writer's own check still proves the final text refuses every refused root, including a
   refused root that now contains one allowed literal.

No model, no harness, no `codex`, no launch. Nothing here opens `evals/answer-key/`, the
held-out set, or any routing request, and nothing reads a real credential: the store this
test builds holds text this file wrote.
"""
import os
import shutil
import subprocess
import unittest

from testlib import RunnerCase, runner

SANDBOX_EXEC = "/usr/bin/sandbox-exec"
# Not a credential and never one: the bytes this test writes into its own fake store.
FAKE_STORE = '{"fake": "not a credential; written by test_sb_sendback_8.py"}\n'


def _writer():
    import importlib.util
    path = os.path.join(runner.PLUGIN_DIR, "setups", "_wall", "write-sandbox-profile.py")
    spec = importlib.util.spec_from_file_location("write_sandbox_profile_sb8", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


writer = _writer()


def sandbox(profile, argv, cwd="/"):
    """One plain child under the profile. `/` as the cwd for the reason test_wall_profile
    gives: the suite's own working directory is inside the checkout, which every profile
    refuses."""
    return subprocess.run([SANDBOX_EXEC, "-f", profile] + list(argv),
                          capture_output=True, text=True, cwd=cwd,
                          env={"PATH": "/usr/bin:/bin", "HOME": os.path.expanduser("~")})


def refused(completed):
    return completed.returncode != 0 and (
        "Operation not permitted" in (completed.stderr or "")
        or "not permitted" in (completed.stdout or ""))


def paths(rows):
    return [row["path"] for row in rows]


class TwoHomeLayout(RunnerCase):
    """A fake Codex install under the TEST pilot root: one store, links from the other home."""

    setups = ("codex",)

    def setUp(self):
        super(TwoHomeLayout, self).setUp()
        self.pilot_codex = os.path.join(runner.PILOT_ROOT, "codex")
        self.addCleanup(shutil.rmtree, self.pilot_codex, True)
        shutil.rmtree(self.pilot_codex, ignore_errors=True)
        self.campaign_object = runner.Campaign(self.campaign)
        self.setup = runner.CodexSetup(self.campaign_object, stage=self.stage)
        self.base = self.setup.home("available")
        self.other = self.setup.home("absent")
        # the ONE store, in the base home, exactly where install.sh writes it
        self.store = os.path.join(self.base, "auth.json")
        runner.write_text(self.store, FAKE_STORE)
        os.chmod(self.store, 0o600)
        # what else lives in that home and must STAY refused to the other condition
        self.siblings = []
        for relative, text in (("native-read-boundary-sentinel.txt", "the native check\n"),
                               ("config.toml", "model = \"a-test-model\"\n"),
                               (os.path.join("skills", "recheck-v2", "SKILL.md"), "staged\n"),
                               (os.path.join("plugins", "cache", "a.json"), "{}\n"),
                               (os.path.join("sessions", "2026", "a-rollout.jsonl"), "{}\n")):
            path = os.path.join(self.base, relative)
            runner.write_text(path, text)
            self.siblings.append(path)
        # the other condition's home: the single-store links install.sh makes
        self.links = []
        for relative in ("auth.json", os.path.join("child", "auth.json")):
            link = os.path.join(self.other, relative)
            runner.ensure_dir(os.path.dirname(link))
            os.symlink(self.store, link)
            self.links.append(link)
        runner.write_text(os.path.join(self.other, "config.toml"), "model = \"a-test-model\"\n")
        self.workspace = os.path.join(self.scratch, "tree", "workspace")
        runner.ensure_dir(self.workspace)

    def spec_for(self, condition, setup=None):
        out_dir = os.path.join(self.campaign_object.trials, "a-trial", "harness")
        return runner.wall_spec(self.campaign_object, setup or self.setup, condition, out_dir,
                                workspace=self.workspace,
                                scratch=os.path.join(self.scratch, "tree", "scratch"))


class TheSpecNamesTheOneResolvedStoreTest(TwoHomeLayout):

    def test_the_store_is_named_as_a_literal_write_file(self):
        rows = self.spec_for("absent")["write_files"]
        self.assertEqual(paths(rows), [os.path.realpath(self.store)])

    def test_two_links_to_one_store_produce_one_row(self):
        """`auth.json` and `child/auth.json` both point at it; the file is named ONCE."""
        self.assertEqual(len(self.spec_for("absent")["write_files"]), 1)

    def test_the_row_carries_the_reason_the_setup_declared(self):
        why = self.spec_for("absent")["write_files"][0]["why"]
        self.assertIn("credential", why.lower())
        self.assertIn("send-back 8", why)

    def test_the_store_is_NOT_named_as_a_subpath_root(self):
        """A subpath of the base home would reopen the whole home; a literal opens one file."""
        spec = self.spec_for("absent")
        for row in spec["read_roots"] + spec["write_roots"]:
            self.assertFalse(runner.path_contains(row["path"], self.siblings[0]),
                             "%s reopens %s" % (row["path"], self.siblings[0]))

    def test_the_other_home_is_still_a_refused_root(self):
        refused_paths = paths(self.spec_for("absent")["refused_roots"])
        self.assertIn(os.path.realpath(self.base), refused_paths)

    def test_the_condition_whose_store_is_in_its_OWN_home_gets_no_extra_row(self):
        self.assertEqual(self.spec_for("available")["write_files"], [])

    def test_a_link_that_resolves_inside_no_refused_root_gets_no_row(self):
        """Nothing refuses it, so nothing has to be reopened."""
        outside = os.path.join(self.scratch, "outside-every-refused-root", "auth.json")
        runner.write_text(outside, FAKE_STORE)
        for link in self.links:
            os.unlink(link)
            os.symlink(outside, link)
        self.assertEqual(self.spec_for("absent")["write_files"], [])

    def test_a_plain_file_that_is_not_a_link_gets_no_row(self):
        for link in self.links:
            os.unlink(link)
            runner.write_text(link, FAKE_STORE)
        self.assertEqual(self.spec_for("absent")["write_files"], [])

    def test_a_dangling_link_gets_no_row(self):
        """Fail closed: a link with no file behind it opens nothing."""
        for link in self.links:
            os.unlink(link)
            os.symlink(os.path.join(self.base, "no-such-store.json"), link)
        self.assertEqual(self.spec_for("absent")["write_files"], [])

    def test_claude_codes_spec_is_unchanged(self):
        """Claude Code declares no `credential_store`, so it grows no row."""
        setup = runner.ClaudeCodeSetup(self.campaign_object, stage=self.stage)
        for condition in ("available", "absent"):
            self.assertEqual(self.spec_for(condition, setup=setup)["write_files"], [],
                             condition)

    def test_the_setup_declares_the_two_home_relative_files_with_a_reason(self):
        block = runner.wall_needs(self.setup).get("credential_store")
        self.assertIsInstance(block, dict)
        self.assertEqual(block.get("files"), ["auth.json", "child/auth.json"])
        self.assertTrue(block.get("why"))


@unittest.skipUnless(os.path.isfile(SANDBOX_EXEC), "this machine has no sandbox-exec")
class TheKernelOpensTheLiteralAndNothingElseTest(TwoHomeLayout):
    """The real writer, a real profile, and real `sandbox-exec` children."""

    def setUp(self):
        super(TheKernelOpensTheLiteralAndNothingElseTest, self).setUp()
        self.spec = self.spec_for("absent")
        text, self.summary = writer.build(self.spec)
        self.profile = os.path.join(self.scratch, "launch.sb")
        runner.write_text(self.profile, text)
        self.text = text

    def test_the_literal_reads(self):
        got = sandbox(self.profile, ["/bin/cat", os.path.realpath(self.store)])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertIn("not a credential", got.stdout)

    def test_the_literal_appends(self):
        """Codex rewrites the store on a token refresh, so the file must be WRITABLE."""
        got = sandbox(self.profile, ["/usr/bin/python3", "-c",
                                     "import sys;open(sys.argv[1],'ab').close()",
                                     os.path.realpath(self.store)])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(runner.read_text(self.store), FAKE_STORE)

    def test_the_launchs_OWN_link_resolves_to_it(self):
        """The route Codex actually takes: `<this home>/auth.json` is the link."""
        for link in self.links:
            got = sandbox(self.profile, ["/bin/cat", link])
            self.assertEqual(got.returncode, 0, "%s: %s" % (link, got.stderr))
            self.assertIn("not a credential", got.stdout)

    def test_every_sibling_in_that_same_refused_home_is_still_refused(self):
        for path in self.siblings:
            self.assertTrue(refused(sandbox(self.profile, ["/bin/cat", path])), path)

    def test_the_refused_homes_own_directories_cannot_be_listed(self):
        for relative in ("skills", "plugins", "sessions"):
            got = sandbox(self.profile, ["/bin/ls", os.path.join(self.base, relative)])
            self.assertNotEqual(got.returncode, 0, relative)

    def test_a_write_beside_the_literal_in_the_refused_home_is_refused(self):
        target = os.path.join(self.base, "planted-by-the-test.json")
        got = sandbox(self.profile, ["/bin/sh", "-c", "echo planted > %s" % target])
        self.assertNotEqual(got.returncode, 0)
        self.assertFalse(os.path.exists(target))

    def test_the_literal_is_reopened_AFTER_the_deny_of_the_refused_home(self):
        """Last match wins: the allow has to come after the deny, or the deny wins."""
        self.assertIn(os.path.realpath(self.base), self.summary["refused_before_the_allows"])
        self.assertLess(self.text.index('(subpath "%s")' % os.path.realpath(self.base)),
                        self.text.index('(literal "%s")' % os.path.realpath(self.store)))

    def test_the_final_text_still_refuses_every_refused_root(self):
        """The writer's own evaluation, over the emitted rules, with the literal in place."""
        self.assertEqual(writer.check_profile(writer.build_rules(self.spec)), [])

    def test_this_conditions_own_home_still_works(self):
        got = sandbox(self.profile, ["/bin/cat", os.path.join(self.other, "config.toml")])
        self.assertEqual(got.returncode, 0, got.stderr)


class TheWriterKeepsItsPromisesWithALiteralInsideADeniedRootTest(unittest.TestCase):
    """The writer alone, on a hand-built spec: no runner, no pilot root."""

    def build(self, **spec):
        spec.setdefault("label", "a send-back 8 test")
        return writer.build(spec)

    def test_a_write_file_inside_a_refused_root_moves_that_root_before_the_allows(self):
        text, summary = self.build(write_roots=["/tmp/mine"],
                                   write_files=["/tmp/theirs/auth.json"],
                                   refused_roots=["/tmp/theirs"])
        self.assertIn("/private/tmp/theirs", summary["refused_before_the_allows"])
        self.assertLess(text.index('(subpath "/private/tmp/theirs")'),
                        text.index('(literal "/private/tmp/theirs/auth.json")'))

    def test_the_literal_is_allowed_for_reads_AND_writes(self):
        _text, summary = self.build(write_files=["/tmp/theirs/auth.json"],
                                    refused_roots=["/tmp/theirs"])
        for operation in writer.CHECKED_READ + writer.CHECKED_WRITE:
            self.assertEqual(
                writer.evaluate(writer.build_rules(
                    {"write_files": ["/tmp/theirs/auth.json"],
                     "refused_roots": ["/tmp/theirs"]})["rules"],
                    "/private/tmp/theirs/auth.json", operation),
                "allow", operation)
        self.assertEqual([r["path"] for r in summary["write_files"]],
                         ["/tmp/theirs/auth.json", "/private/tmp/theirs/auth.json"])

    def test_a_sibling_of_the_literal_stays_denied_by_evaluation(self):
        rules = writer.build_rules({"write_files": ["/tmp/theirs/auth.json"],
                                    "refused_roots": ["/tmp/theirs"]})["rules"]
        for operation in writer.CHECKED_READ + writer.CHECKED_WRITE:
            self.assertEqual(writer.evaluate(rules, "/private/tmp/theirs/sentinel.txt",
                                             operation), "deny", operation)

    def test_a_path_named_as_both_a_write_file_and_a_refused_root_is_refused(self):
        with self.assertRaises(writer.SpecError):
            self.build(write_files=["/tmp/same"], refused_roots=["/tmp/same"])

    def test_a_spec_with_no_write_files_emits_no_such_rule(self):
        text, summary = self.build(write_roots=["/tmp/mine"])
        self.assertEqual(summary["write_files"], [])
        self.assertNotIn("write files", text)


if __name__ == "__main__":
    unittest.main()
