"""The transcript lookup behind the sealed bench's wall (send-back 5, blocker 2).

Live proof 5 (root `wall-proof-20260919T171050Z`): `invocation.py` exited 3 with
`CLAUDE_CODE_SESSION_ID is <id> but no transcript named <id>.jsonl exists under
~/.claude/projects`, and the with-skill trial stopped on it. The profile allows a session only
its OWN slug folder under `~/.claude/projects`; LISTING the parent is refused, `glob` swallows
that refusal and returns nothing, and the helper read the refusal as absence.

A directory at mode 0o111 is the faithful stand-in: traversable, not listable — which is
exactly what the wall leaves, since the profile allows `file-read-metadata` on the ancestors of
an allowed root and denies `file-read-data` (the listing) on the parent.

No model and no harness anywhere.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

import testlib

sys.path.insert(0, testlib.ADAPTER)
import _common  # noqa: E402

# the id the fixture transcript's own records carry; every route here is keyed on it
SESSION = "4cd53208-8cb8-4de2-bb71-be7594182bb1"
OTHER = "99999999-0000-0000-0000-000000000000"
LAUNCH_SH = os.path.join(testlib.PLUGIN_ROOT, "setups", "claude-code", "launch.sh")


class SlugRuleTest(unittest.TestCase):
    """One rule, in two places, tested against each other."""

    def test_the_adapter_and_the_launcher_spell_the_slug_the_same_way(self):
        with open(LAUNCH_SH, encoding="utf-8") as handle:
            text = handle.read()
        # the launcher's own line, read out of the file rather than restated here
        self.assertIn('slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(workspace))', text)
        launcher = lambda path: re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(path))
        for sample in ("/tmp", "/private/tmp/a.b/c-d", os.path.expanduser("~"),
                       "/private/tmp/claude-501/-Users-x/y/scratchpad"):
            self.assertEqual(_common.project_slug(sample), launcher(sample), sample)

    def test_the_slug_is_taken_from_the_RESOLVED_path(self):
        self.assertEqual(_common.project_slug("/tmp"), _common.project_slug("/private/tmp"))


class WalledLookupTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="recheck-adapter-wall-")
        self.addCleanup(self._open_up)
        self.addCleanup(shutil.rmtree, self.home, True)
        self.projects = os.path.join(self.home, "projects")
        self.workspace = os.path.join(self.home, "workspace")
        os.makedirs(self.workspace)
        self.slug_dir = os.path.join(self.projects, _common.project_slug(self.workspace))
        os.makedirs(self.slug_dir)
        self.copy = os.path.join(self.slug_dir, "%s.jsonl" % SESSION)
        # the shipped fixture, with every record's `cwd` rewritten to THIS test's workspace so
        # the E9-28 workspace binding holds; nothing else about it is touched
        self._retarget(testlib.TRANSCRIPT, self.copy, self.workspace)
        # a sibling the session may not list, holding another session's record
        self.sibling = os.path.join(self.projects, "-tmp-someone-elses-repo")
        os.makedirs(self.sibling)
        self._retarget(testlib.TRANSCRIPT,
                       os.path.join(self.sibling, "%s.jsonl" % OTHER), self.workspace)

    @staticmethod
    def _retarget(source, target, workspace):
        real = os.path.realpath(workspace)
        with open(source, encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        for row in rows:
            if "cwd" in row:
                row["cwd"] = real
        with open(target, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    def _open_up(self):
        for path in (getattr(self, "projects", None),):
            if path and os.path.isdir(path):
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass

    def close_the_listing(self):
        """Traversable, not listable: what the wall leaves."""
        os.chmod(self.projects, 0o111)

    def env(self, **extra):
        base = {"CLAUDE_CONFIG_DIR": self.home, "TMPDIR": self.home}
        base.update(extra)
        return base

    def test_the_named_slug_folder_is_found_when_the_parent_cannot_be_listed(self):
        self.close_the_listing()
        with self.assertRaises(OSError):
            os.listdir(self.projects)          # the test's own premise, asserted
        document = testlib.run_json(
            "turns.py", ["--workspace", self.workspace],
            cwd=self.workspace, env=self.env(CLAUDE_CODE_SESSION_ID=SESSION))
        self.assertEqual(document["transcript"], self.copy)
        self.assertIn("named slug folder", document["discovery"])

    def test_the_same_lookup_works_when_the_parent_IS_listable(self):
        document = testlib.run_json(
            "turns.py", ["--workspace", self.workspace],
            cwd=self.workspace, env=self.env(CLAUDE_CODE_SESSION_ID=SESSION))
        self.assertEqual(document["transcript"], self.copy)

    def test_the_workspace_argument_is_tried_when_the_cwd_is_elsewhere(self):
        """The harness can change directory, so the session's cwd and the workspace are not
        always the same path. Both are tried; neither is guessed."""
        self.close_the_listing()
        elsewhere = os.path.join(self.home, "somewhere-else")
        os.makedirs(elsewhere)
        document = testlib.run_json(
            "turns.py", ["--workspace", self.workspace],
            cwd=elsewhere, env=self.env(CLAUDE_CODE_SESSION_ID=SESSION))
        self.assertEqual(document["transcript"], self.copy)

    def test_a_refused_directory_is_RECORDED_not_read_as_absence(self):
        os.unlink(self.copy)
        self.close_the_listing()
        code, out, err = testlib.run(
            "turns.py", ["--workspace", self.workspace],
            cwd=self.workspace, env=self.env(CLAUDE_CODE_SESSION_ID=SESSION))
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("Directories that refused to be read", err)
        self.assertIn("PermissionError", err)
        self.assertIn(self.projects, err)
        self.assertIn("Named folders tried", err)

    def test_a_genuinely_absent_transcript_still_says_so_with_nothing_refused(self):
        os.unlink(self.copy)
        code, _out, err = testlib.run(
            "turns.py", ["--workspace", self.workspace],
            cwd=self.workspace, env=self.env(CLAUDE_CODE_SESSION_ID=SESSION))
        self.assertEqual(code, 3)
        self.assertIn("nothing was refused", err)

    def test_the_wall_does_not_open_a_route_to_another_sessions_record(self):
        """E9-28 is untouched: every route is keyed on the harness's own session id."""
        self.close_the_listing()
        code, _out, err = testlib.run(
            "turns.py", ["--workspace", self.workspace], cwd=self.workspace,
            env=self.env(CLAUDE_CODE_SESSION_ID=OTHER))
        self.assertEqual(code, 3)
        self.assertNotIn(self.sibling, _out_or(err))

    def test_the_verifier_reads_the_session_model_through_the_same_route(self):
        self.close_the_listing()
        brief = os.path.join(self.workspace, "checklist.md")
        with open(brief, "w", encoding="utf-8") as handle:
            handle.write("a brief this test wrote\n")
        code, out, err = testlib.run(
            "verifier.py", ["--brief", brief, "--workspace", self.workspace,
                            "--scratch", os.path.join(self.home, "scratch"),
                            "--raw", os.path.join(self.home, "scratch", "raw.md")],
            cwd=self.workspace,
            env=self.env(CLAUDE_CODE_SESSION_ID=SESSION,
                         RECHECK_ADAPTER_CANNED=None))
        # whatever the verifier then does, it must not have failed FOR THE TRANSCRIPT
        self.assertNotIn("no transcript named", out + err)


def _out_or(text):
    return text or ""


if __name__ == "__main__":
    unittest.main()
