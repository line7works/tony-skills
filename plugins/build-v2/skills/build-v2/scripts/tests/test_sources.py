"""The source set: three lists plus the base, computed from git and never guessed.

Lane contract section 8. What this suite holds: each list holds what git says it holds; an
ignored file is in none of them; `docs/records/` is in none of them (CR-3); a workspace with no
git and a base ref that does not resolve are each a STOP with a reason rather than an empty set;
and the prefix this core excludes is the prefix the records component publishes, so the identity
the component computes and the set this core reports describe the same tree.
"""
import json
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from build_core import sources  # noqa: E402


class TheThreeLists(unittest.TestCase):

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-sources-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.ws = testlib.make_workspace(self.scratch)

    def test_a_clean_tree_at_the_base_has_an_empty_set(self):
        source = sources.source_set(self.ws, "base")
        self.assertEqual(source["committed"], [])
        self.assertEqual(source["changed"], [])
        self.assertEqual(source["untracked"], [])
        self.assertEqual(source["base"], "base")
        self.assertEqual(len(source["base_commit"]), 40)

    def test_a_committed_change_is_in_committed_only(self):
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 1\n")
        testlib.commit_work(self.ws)
        source = sources.source_set(self.ws, "base")
        self.assertEqual(source["committed"], ["src/widget.py"])
        self.assertEqual(source["changed"], [])
        self.assertEqual(source["untracked"], [])

    def test_a_working_tree_change_is_in_changed_only(self):
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 2\n")
        source = sources.source_set(self.ws, "base")
        self.assertEqual(source["committed"], [])
        self.assertEqual(source["changed"], ["src/widget.py"])

    def test_a_staged_change_is_in_changed_too(self):
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 3\n")
        testlib.git(self.ws, ["add", "src/widget.py"])
        source = sources.source_set(self.ws, "base")
        self.assertEqual(source["changed"], ["src/widget.py"])

    def test_an_untracked_file_is_in_untracked_only(self):
        testlib.write_text(os.path.join(self.ws, "src", "extra.py"), "X = 1\n")
        source = sources.source_set(self.ws, "base")
        self.assertEqual(source["untracked"], ["src/extra.py"])
        self.assertEqual(source["changed"], [])

    def test_an_ignored_file_is_in_no_list(self):
        testlib.write_text(os.path.join(self.ws, "build", "out.txt"), "generated\n")
        testlib.write_text(os.path.join(self.ws, "src", "widget.pyc"), "bytes\n")
        source = sources.source_set(self.ws, "base")
        self.assertEqual(source["untracked"], [])
        self.assertEqual(sources.all_paths(source), [])

    def test_the_records_log_is_in_no_list(self):
        """CR-3: `docs/records/` is the component's own history, never source this build touched."""
        testlib.write_text(os.path.join(self.ws, "docs", "records", "a.events.jsonl"), '{"v":1}\n')
        source = sources.source_set(self.ws, "base")
        self.assertEqual(source["untracked"], [])
        testlib.commit_work(self.ws)
        source = sources.source_set(self.ws, "base")
        self.assertEqual(source["committed"], [])
        self.assertEqual(source["excluded"], ["docs/records/"])

    def test_all_three_at_once(self):
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 1\n")
        testlib.commit_work(self.ws)
        testlib.write_text(os.path.join(self.ws, "src", "other.py"), "VALUE = 2\n")
        testlib.write_text(os.path.join(self.ws, "src", "extra.py"), "X = 1\n")
        source = sources.source_set(self.ws, "base")
        self.assertEqual(source["committed"], ["src/widget.py"])
        self.assertEqual(source["changed"], ["src/other.py"])
        self.assertEqual(source["untracked"], ["src/extra.py"])
        self.assertEqual(sources.all_paths(source),
                         ["src/extra.py", "src/other.py", "src/widget.py"])
        self.assertEqual(sources.lists_holding(source, "src/other.py"), ["changed"])


class ASetThatCannotBeComputedIsAStop(unittest.TestCase):

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-sources-stop-")
        self.addCleanup(testlib.rmtree, self.scratch)

    def test_a_directory_that_is_not_a_git_work_tree(self):
        plain = os.path.join(self.scratch, "plain")
        os.makedirs(plain)
        with self.assertRaises(sources.GitError) as caught:
            sources.source_set(plain, "base")
        self.assertIn("not inside a git work tree", str(caught.exception))
        self.assertIn("cannot be computed", str(caught.exception))

    def test_a_base_ref_that_does_not_resolve(self):
        ws = testlib.make_workspace(self.scratch)
        with self.assertRaises(sources.GitError) as caught:
            sources.source_set(ws, "no-such-tag")
        self.assertIn("does not resolve", str(caught.exception))
        self.assertIn("cannot be computed", str(caught.exception))

    def test_a_subdirectory_of_a_work_tree_is_not_its_root(self):
        ws = testlib.make_workspace(self.scratch)
        with self.assertRaises(sources.GitError) as caught:
            sources.source_set(os.path.join(ws, "src"), "base")
        self.assertIn("root", str(caught.exception))


class TheCliReportsTheStops(unittest.TestCase):
    """The stop reaches the result as a `stop`, with a tag and a reason."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-sources-cli-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.ws = testlib.make_workspace(self.scratch)
        self.run_dir = os.path.join(self.scratch, "run")

    def _to_preflight(self, **extra):
        path = os.path.join(self.scratch, "input.json")
        testlib.write_json(path, testlib.make_input(self.run_dir, self.ws, **extra))
        self.assertEqual(testlib.run_build(["check-input", path])[0], 0)
        self.assertEqual(testlib.run_build(["contract", "--run-dir", self.run_dir])[0], 0)
        return testlib.run_build(["preflight", "--run-dir", self.run_dir])

    def test_a_base_that_does_not_resolve_stops_the_run(self):
        code, out, err = self._to_preflight(base="no-such-tag")
        self.assertEqual(code, 10, err)
        document = json.loads(out)
        self.assertEqual(document["status"], "stopped")
        self.assertEqual(document["terminal_status"], "stop")
        result = testlib.load_json(os.path.join(self.run_dir, "result.json"))
        self.assertEqual(result["stop_tag"], "no_base")
        self.assertIn("does not resolve", result["stop_reason"])
        self.assertIsNone(result.get("source_set"))

    def test_the_set_reaches_the_result(self):
        testlib.write_text(os.path.join(self.ws, "src", "widget.py"), "def spin():\n    return 1\n")
        testlib.commit_work(self.ws)
        testlib.write_text(os.path.join(self.ws, "src", "extra.py"), "X = 1\n")
        code, out, err = self._to_preflight()
        self.assertEqual(code, 0, err)
        document = json.loads(out)
        self.assertEqual(document["source_set"]["committed"], ["src/widget.py"])
        self.assertEqual(document["source_set"]["untracked"], ["src/extra.py"])


class TheExclusionAgreesWithTheComponent(unittest.TestCase):
    """The prefix this core excludes is the prefix the component publishes under `excluded`."""

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-exclusion-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.ws = testlib.make_workspace(self.scratch)

    def test_the_lists_are_the_same(self):
        code, out, err = testlib.run_build(["identity", self.ws])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["excluded"], list(sources.EXCLUDED_PREFIXES))

    def test_a_log_write_does_not_make_the_workspace_dirty(self):
        """The component excludes the same prefix, so the identity a card event carries is the
        identity of the source, not of the log this run just wrote."""
        before = json.loads(testlib.run_build(["identity", self.ws])[1])["identity"]
        testlib.write_text(os.path.join(self.ws, "docs", "records", "x.events.jsonl"), '{"v":1}\n')
        after = json.loads(testlib.run_build(["identity", self.ws])[1])["identity"]
        self.assertEqual(before, after)
        self.assertFalse(after["dirty"])


if __name__ == "__main__":
    unittest.main()
