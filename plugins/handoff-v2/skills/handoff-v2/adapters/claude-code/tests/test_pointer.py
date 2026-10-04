"""The Claude Code adapter's own step (A2 Q3, ruling E15-12): the memory pointer. `pointer.py` writes v1's
auto-memory pointer, one file per feature (`handoff-<feature>.md`, overwritten each run) and its index line in
`MEMORY.md` (added or replaced, never a second), from the text the core's `write` left in the run directory, and
only under the memory folder it is GIVEN: there is no default, it never reads HOME, and a run whose pointer is not
the adapter's (a Codex run, a report-only run) is refused with nothing written. It leaves a receipt with every
write's hash before and after in the run directory.
"""
import hashlib
import json
import os
import shutil
import tempfile
import unittest

import testlib

HELPER = "pointer.py"
DOC = "docs/plans/2026-09-20-turnstile.md"


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def pointer_doc(for_adapter=True, date="2026-10-04", kickoff="/ship-v2 B %s" % DOC):
    text = ("---\nname: handoff-turnstile\ndescription: the build loop's kickoff pointer for %s\ntype: project\n---\n\n"
            "Build doc: %s\nHandoff block: %s\nKickoff: %s\n" % (DOC, DOC, date, kickoff))
    return {"pointer_version": 1, "run_id": "run", "harness": "claude-code" if for_adapter else "codex-cli",
            "feature": "turnstile", "file_name": "handoff-turnstile.md", "doc": DOC, "block_date": date,
            "kickoff": kickoff, "text": text, "for_adapter": for_adapter,
            "index_line": "- [Build loop kickoff: turnstile](handoff-turnstile.md): the kickoff line for %s, from the "
                          "%s handoff block" % (DOC, date),
            "note": None if for_adapter else "Codex: no memory pointer is written; the block in the build doc is "
                                             "the pointer (E15-12)"}


class ThePointer(unittest.TestCase):

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="pointer-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run_dir = os.path.join(self.tmp, "run")
        self.memory = os.path.join(self.tmp, "memory")
        self.home = os.path.join(self.tmp, "home")
        for folder in (self.run_dir, self.memory, self.home):
            os.makedirs(folder)
        with open(os.path.join(self.memory, "MEMORY.md"), "w", encoding="utf-8") as fh:
            fh.write("# Memory Index\n- [Other](other.md): another note\n")

    def put(self, doc):
        with open(os.path.join(self.run_dir, "pointer.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    def call(self, args):
        return testlib.run(HELPER, args, env={"HOME": self.home})

    def test_no_memory_folder_given_is_a_usage_stop_and_nothing_is_created(self):
        self.put(pointer_doc())
        code, out, err = self.call(["--run-dir", self.run_dir])
        self.assertEqual(code, 2, (out, err))
        self.assertEqual(os.listdir(self.home), [])
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "pointer-receipt.json")))

    def test_a_memory_folder_that_is_not_there_is_refused(self):
        self.put(pointer_doc())
        code, out, err = self.call(["--run-dir", self.run_dir, "--memory-dir", os.path.join(self.tmp, "nowhere")])
        self.assertEqual(code, 2, (out, err))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "nowhere")))

    def test_the_pointer_and_its_index_line_land_under_the_given_folder_only(self):
        self.put(pointer_doc())
        before = sha(os.path.join(self.memory, "MEMORY.md"))
        code, out, err = self.call(["--run-dir", self.run_dir, "--memory-dir", self.memory])
        self.assertEqual(code, 0, (out, err))
        with open(os.path.join(self.memory, "handoff-turnstile.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), pointer_doc()["text"])
        with open(os.path.join(self.memory, "MEMORY.md"), encoding="utf-8") as fh:
            index = fh.read()
        self.assertEqual(index.count("(handoff-turnstile.md)"), 1)
        self.assertIn("- [Other](other.md): another note\n", index)
        self.assertEqual(os.listdir(self.home), [])
        receipt = json.loads(out)
        self.assertEqual(receipt, testlib_load(os.path.join(self.run_dir, "pointer-receipt.json")))
        rows = dict((os.path.basename(w["path"]), w) for w in receipt["writes"])
        self.assertEqual(rows["MEMORY.md"]["sha256_before"], before)
        self.assertIsNone(rows["handoff-turnstile.md"]["sha256_before"])
        self.assertEqual(rows["handoff-turnstile.md"]["sha256_after"], sha(os.path.join(self.memory, "handoff-turnstile.md")))

    def test_a_second_run_supersedes_never_seconds(self):
        self.put(pointer_doc(date="2026-10-01", kickoff="/ship-v2 A %s" % DOC))
        self.assertEqual(self.call(["--run-dir", self.run_dir, "--memory-dir", self.memory])[0], 0)
        self.put(pointer_doc())
        code, out, err = self.call(["--run-dir", self.run_dir, "--memory-dir", self.memory])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(sorted(os.listdir(self.memory)), ["MEMORY.md", "handoff-turnstile.md"])
        with open(os.path.join(self.memory, "MEMORY.md"), encoding="utf-8") as fh:
            index = fh.read()
        self.assertEqual(index.count("(handoff-turnstile.md)"), 1)
        self.assertIn("2026-10-04", index)
        self.assertNotIn("2026-10-01", index)

    def test_a_pointer_that_is_not_the_adapters_is_refused_and_nothing_is_written(self):
        self.put(pointer_doc(for_adapter=False))
        before = sorted(os.listdir(self.memory))
        code, out, err = self.call(["--run-dir", self.run_dir, "--memory-dir", self.memory])
        self.assertEqual(code, 5, (out, err))
        self.assertEqual(sorted(os.listdir(self.memory)), before)

    def test_a_link_at_the_pointer_path_is_refused(self):
        self.put(pointer_doc())
        os.symlink(os.path.join(self.tmp, "elsewhere.md"), os.path.join(self.memory, "handoff-turnstile.md"))
        code, out, err = self.call(["--run-dir", self.run_dir, "--memory-dir", self.memory])
        self.assertEqual(code, 5, (out, err))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "elsewhere.md")))

    def test_the_helper_never_reads_home(self):
        with open(os.path.join(testlib.ADAPTER, HELPER), encoding="utf-8") as fh:
            body = fh.read()
        self.assertNotIn("HOME", body)
        self.assertNotIn("expanduser", body)
        self.assertNotIn("~", body)


def testlib_load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    unittest.main()
