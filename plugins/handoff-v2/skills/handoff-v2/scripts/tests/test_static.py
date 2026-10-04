"""Static guarantees over this core's own files (A2 Q2, CR-16, E15-4).

1. No handoff-v2 script runs a git command that changes a branch, an index or a worktree: every git argv in the
   core's files is a read-only subcommand (the checkpoint commit is the executor's named step, outside the script).
2. handoff invokes no station and writes no trace: no core module imports the trace module or writes
   `trace.jsonl`, and the only subprocesses are git and the records component's CLI (a run proves the second half,
   `test_report_only.py`).
3. Every subprocess argv is a list; no shell text.
"""
import os
import re
import unittest

import testlib

CORE_FILES = [os.path.join(testlib.SCRIPTS, "handoff.py")] + [
    os.path.join(testlib.SCRIPTS, "handoff_core", n) for n in sorted(os.listdir(os.path.join(testlib.SCRIPTS, "handoff_core")))
    if n.endswith(".py")] + [
    os.path.join(testlib.SKILL, "adapters", h, n) for h in ("claude-code", "codex")
    for n in sorted(os.listdir(os.path.join(testlib.SKILL, "adapters", h))) if n.endswith(".py") and n != "_common.py"]
READ_ONLY = ("rev-parse", "symbolic-ref", "rev-list", "status", "show", "cat-file", "log", "ls-files", "diff",
             "merge-base")
CHANGING = ("add", "commit", "checkout", "switch", "reset", "merge", "rebase", "stash", "push", "pull", "fetch",
            "worktree", "branch", "tag", "restore", "rm", "mv", "cherry-pick", "revert", "update-ref", "update-index",
            "gc", "clean", "apply", "am", "config", "init", "clone", "notes", "replace")
GIT_CALL = re.compile(r"""\[\s*["']git["']\s*,(?P<rest>[^\]]*)\]""")
RUN_CALL = re.compile(r"""\b(?:gitio\.)?(?:run|text|_git)\(\s*(?:ws|workspace|self\.ws|root|path|\w+)\s*,\s*\[\s*["'](?P<sub>[a-z-]+)["']""")


def text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class NoChangingGit(unittest.TestCase):

    def test_the_core_files_are_found(self):
        names = [os.path.basename(p) for p in CORE_FILES]
        for name in ("handoff.py", "gitio.py", "write.py"):
            self.assertIn(name, names)

    def test_every_git_subcommand_is_read_only(self):
        found = []
        for path in CORE_FILES:
            body = text(path)
            for match in RUN_CALL.finditer(body):
                if match.group("sub") not in READ_ONLY:
                    found.append((os.path.basename(path), match.group("sub")))
            for match in GIT_CALL.finditer(body):
                words = re.findall(r"""["']([a-z-]+)["']""", match.group("rest"))
                for word in words:
                    if word in CHANGING:
                        found.append((os.path.basename(path), word))
        self.assertEqual(found, [])

    def test_no_shell_text(self):
        for path in CORE_FILES:
            body = text(path)
            self.assertNotIn("shell=True", body, path)
            self.assertNotIn("os.system(", body, path)
            self.assertNotIn("os.popen(", body, path)

    def test_the_plant_is_seen(self):
        body = 'gitio.run(ws, ["commit", "-m", "x"])\nsubprocess.run(["git", "-C", ws, "add", "-A"])\n'
        hits = [m.group("sub") for m in RUN_CALL.finditer(body)]
        hits += [w for m in GIT_CALL.finditer(body) for w in re.findall(r"""["']([a-z-]+)["']""", m.group("rest"))
                 if w in CHANGING]
        self.assertEqual(sorted(hits), ["add", "commit"])


class NoTraceNoStation(unittest.TestCase):

    def test_no_core_module_touches_the_trace(self):
        for path in CORE_FILES:
            body = text(path)
            self.assertNotIn("back_core import trace", body, path)
            self.assertNotIn("import trace", body, path)
            self.assertNotIn("trace.jsonl", body, path)

    def test_the_only_subprocesses_are_git_and_the_records_cli(self):
        allowed = ("gitio.py",)
        for path in CORE_FILES:
            body = text(path)
            if re.search(r"^\s*(?:import subprocess|from subprocess import)", body, flags=re.M):
                self.assertIn(os.path.basename(path), allowed, path)


if __name__ == "__main__":
    unittest.main()
