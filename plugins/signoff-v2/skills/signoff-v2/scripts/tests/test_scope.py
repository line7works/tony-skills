"""The section 8 source set, computed by script from git.

Three lists plus the base: committed since the slice's base (`git diff --name-only base..HEAD`),
changed in the working tree against HEAD (staged or not), untracked and not ignored. A set that
cannot be computed — no git, no such ref — is a stop with a reason, never a guess.
`docs/records/` is excluded from all three (CR-3), exactly as `recheck_core/identity.py` excludes
it, because the component's log describes the source and is never part of it.

The seeded cases are the measurements: S1-02 plants an untracked defect file, S1-03 plants a
committed file the working-tree diff hides, S1-04 plants an ignored twin beside the untracked
file, and S3-04 commits the build doc itself into the set.
"""
import os
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()
from signoff_core import identity  # noqa: E402

GIT_ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
               GIT_AUTHOR_NAME="Case Author", GIT_AUTHOR_EMAIL="case@example.invalid",
               GIT_COMMITTER_NAME="Case Author", GIT_COMMITTER_EMAIL="case@example.invalid",
               GIT_AUTHOR_DATE="2026-09-19T09:00:00-07:00",
               GIT_COMMITTER_DATE="2026-09-19T09:00:00-07:00")


def git(cwd, *args):
    proc = subprocess.run(["git"] + list(args), cwd=cwd, env=GIT_ENV,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("git %s: %s" % (args[0], proc.stderr.decode("utf-8", "replace")))
    return proc.stdout.decode("utf-8")


def write(root, rel, text):
    full = os.path.join(root, rel)
    folder = os.path.dirname(full)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text)
    return full


class TheThreeListsAndTheBase(unittest.TestCase):
    """A hand-built workspace, so each list can be planted on its own."""

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-scope-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.ws = os.path.join(self.dir, "workspace")
        os.makedirs(self.ws)
        git(self.ws, "init", "-q", "-b", "main")
        write(self.ws, ".gitignore", "build/\n*.pyc\n")
        write(self.ws, "src/kept.py", "KEPT = 1\n")
        git(self.ws, "add", "-A")
        git(self.ws, "commit", "-q", "-m", "base")
        git(self.ws, "tag", "base")

    def set_of(self, base="base"):
        return identity.source_set(self.ws, base)

    def test_a_clean_tree_at_the_base_has_three_empty_lists(self):
        got = self.set_of()
        self.assertEqual(got["base_ref"], "base")
        self.assertEqual(got["committed"], [])
        self.assertEqual(got["changed"], [])
        self.assertEqual(got["untracked"], [])
        self.assertEqual(len(got["base_commit"]), 40)

    def test_a_committed_file_is_in_the_committed_list_only(self):
        write(self.ws, "src/added.py", "ADDED = 1\n")
        git(self.ws, "add", "-A")
        git(self.ws, "commit", "-q", "-m", "work")
        got = self.set_of()
        self.assertEqual(got["committed"], ["src/added.py"])
        self.assertEqual(got["changed"], [])
        self.assertEqual(got["untracked"], [])

    def test_a_working_tree_edit_is_in_the_changed_list_staged_or_not(self):
        write(self.ws, "src/kept.py", "KEPT = 2\n")
        self.assertEqual(self.set_of()["changed"], ["src/kept.py"])
        git(self.ws, "add", "src/kept.py")
        self.assertEqual(self.set_of()["changed"], ["src/kept.py"])

    def test_an_untracked_file_is_in_the_untracked_list(self):
        write(self.ws, "src/loose.py", "LOOSE = 1\n")
        got = self.set_of()
        self.assertEqual(got["untracked"], ["src/loose.py"])
        self.assertEqual(got["committed"], [])
        self.assertEqual(got["changed"], [])

    def test_an_ignored_file_is_in_no_list(self):
        write(self.ws, "build/cache.py", "CACHED = 1\n")
        write(self.ws, "src/loose.py", "LOOSE = 1\n")
        got = self.set_of()
        self.assertEqual(got["untracked"], ["src/loose.py"])
        self.assertNotIn("build/cache.py", got["committed"] + got["changed"] + got["untracked"])

    def test_docs_records_is_excluded_from_every_list(self):
        """CR-3: the component's log describes the source and is never part of it."""
        write(self.ws, "docs/records/docs__plans__x.events.jsonl", '{"seq":0}\n')
        got = self.set_of()
        self.assertEqual(got["untracked"], [])
        git(self.ws, "add", "-f", "docs/records")
        git(self.ws, "commit", "-q", "-m", "log")
        got = self.set_of()
        self.assertEqual(got["committed"], [])
        self.assertEqual(got["excluded"], ["docs/records/"])

    def test_an_unresolvable_base_is_a_stop_with_a_reason(self):
        with self.assertRaises(identity.ScopeUnavailable) as caught:
            self.set_of(base="no-such-ref")
        self.assertEqual(caught.exception.reason_code, "base_unresolvable")
        self.assertIn("no-such-ref", str(caught.exception))

    def test_a_directory_that_is_not_a_git_work_tree_is_a_stop(self):
        plain = os.path.join(self.dir, "plain")
        os.makedirs(plain)
        with self.assertRaises(identity.ScopeUnavailable) as caught:
            identity.source_set(plain, "base")
        self.assertEqual(caught.exception.reason_code, "not_a_git_work_tree")

    def test_a_subdirectory_of_a_work_tree_is_a_stop(self):
        with self.assertRaises(identity.ScopeUnavailable) as caught:
            identity.source_set(os.path.join(self.ws, "src"), "base")
        self.assertEqual(caught.exception.reason_code, "not_a_git_work_tree")


class TheSeededCasesAreTheMeasurement(unittest.TestCase):
    """Each planted condition of family S1, read back through the same function."""

    @classmethod
    def setUpClass(cls):
        cls.dir = testlib.make_scratch("signoff-scope-cases-")
        cls.cases = {}
        for case_id in testlib.case_ids("S1-review-scope") + ["S3-04-builder-claims-in-ledger"]:
            family = testlib.family_of(case_id)
            cls.cases[case_id] = testlib.build_case(family, case_id, os.path.join(cls.dir, family))

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.dir)

    def set_of(self, case_id):
        case = self.cases[case_id]
        return identity.source_set(os.path.join(case, "workspace"), "base")

    def test_s1_01_clean_holds_the_two_committed_paths(self):
        got = self.set_of("S1-01-clean")
        self.assertEqual(got["committed"], ["src/signpost/pad.py", "src/signpost/render.py"])
        self.assertEqual(got["changed"], [])
        self.assertEqual(got["untracked"], [])

    def test_s1_02_untracked_defect_is_in_the_untracked_list(self):
        got = self.set_of("S1-02-untracked-defect")
        self.assertEqual(got["untracked"], ["src/signpost/pad.py"])
        self.assertEqual(got["committed"], ["src/signpost/render.py"])

    def test_s1_03_committed_hidden_is_reachable_only_against_the_base(self):
        got = self.set_of("S1-03-committed-hidden")
        self.assertIn("src/signpost/pad.py", got["committed"])
        self.assertEqual(got["changed"], [])
        self.assertEqual(got["untracked"], [])

    def test_s1_04_keeps_the_untracked_file_and_drops_the_ignored_twin(self):
        got = self.set_of("S1-04-ignored-excluded")
        every = got["committed"] + got["changed"] + got["untracked"]
        self.assertIn("src/signpost/pad.py", every)
        self.assertNotIn("build/cache.py", every)

    def test_s3_04_carries_the_build_doc_in_the_committed_list(self):
        got = self.set_of("S3-04-builder-claims-in-ledger")
        self.assertIn("docs/plans/2026-09-18-signpost-rows.md", got["committed"])


if __name__ == "__main__":
    unittest.main()
