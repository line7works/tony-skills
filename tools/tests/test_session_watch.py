"""tools/session-watch/ livewatch.py and toolwatch.py against a synthetic transcript and a throwaway repo.

Offline: every test builds its own temporary repo folder and .jsonl, so no real transcript is read.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.join(HERE, "..", "session-watch", "livewatch.py")
TOOL = os.path.join(HERE, "..", "session-watch", "toolwatch.py")
SECRET = "privatename"


def rec(typ, t, content, **extra):
    msg = {"content": content}
    msg.update(extra.pop("message_extra", {}))
    return dict({"type": typ, "timestamp": f"2026-01-01T00:00:{t:02d}Z", "message": msg}, **extra)


class SessionWatchTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = os.path.realpath(self._tmp.name)
        self.repo = os.path.join(root, "repo")
        os.makedirs(os.path.join(self.repo, "scripts"))
        with open(os.path.join(self.repo, "scripts", "build.py"), "w") as f:
            f.write("print('hi')\n")
        outside = os.path.join(root, f"{SECRET}-scratch", "notes.md")
        script = os.path.join(self.repo, "scripts", "build.py")
        records = [
            rec("user", 0, f"please run the build for {SECRET}"),
            rec("assistant", 1, [{"type": "tool_use", "id": "t1", "name": "Bash",
                                  "input": {"command": f"python3 {script} all --to={SECRET}@example.com | grep ok"}}],
                message_extra={"usage": {"input_tokens": 10, "output_tokens": 5}}),
            rec("user", 3, [{"type": "tool_result", "tool_use_id": "t1", "content": "ok built"}]),
            rec("assistant", 4, [{"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": outside}}],
                message_extra={"usage": {"input_tokens": 20, "output_tokens": 7}}),
            rec("user", 5, [{"type": "tool_result", "tool_use_id": "t2", "is_error": True,
                             "content": [{"type": "text", "text": f"no such file {SECRET}"}]}]),
            rec("assistant", 6, [{"type": "text", "text": "Done."}],
                message_extra={"stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 2}}),
        ]
        self.jsonl = os.path.join(root, "session.jsonl")
        with open(self.jsonl, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            f.write("not json\n")

    def tearDown(self):
        self._tmp.cleanup()

    def run_py(self, script, *args, env=None):
        p = subprocess.run([sys.executable, script, self.jsonl, "--repo", self.repo, *args],
                           capture_output=True, text=True, env=dict(os.environ, **(env or {})), timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def live_lines(self, *args, env=None):
        return self.run_py(LIVE, "--once", *args, env=env).splitlines()

    def test_livewatch_lines(self):
        lines = self.live_lines()
        self.assertEqual(len(lines), 4, lines)
        self.assertRegex(lines[0], r"^\s+0s USER prompt \(\d+ chars\)$")
        self.assertIn("#1 Bash scripts/build.py --to [grep] :: 2.0s, 8 chars", lines[1])
        self.assertNotIn("ERROR", lines[1])
        self.assertIn("#2 Read outside repo: .md file :: 1.0s,", lines[2])
        self.assertTrue(lines[2].endswith(" ERROR"), lines[2])
        self.assertRegex(lines[3], r"^\s+6s TURN END \(2 tool calls so far\)$")

    def test_livewatch_never_leaks(self):
        out = "\n".join(self.live_lines())
        for leak in (SECRET, "@", "example.com", self.repo, "t1", "t2", "notes", "ok built", "Done."):
            self.assertNotIn(leak, out)

    def test_livewatch_subcommands_and_skip(self):
        lines = self.live_lines("--subcommands", "all")
        self.assertIn("scripts/build.py all --to", lines[1])
        skipped = self.live_lines(env={"SKIP": "1"})
        self.assertFalse(any("#1 " in x for x in skipped), skipped)
        self.assertTrue(any("#2 Read" in x for x in skipped), skipped)

    def test_livewatch_masks_path_without_extension_and_dot_claude(self):
        sys.path.insert(0, os.path.dirname(LIVE))
        try:
            import livewatch
        finally:
            sys.path.pop(0)
        lab = livewatch.Labeler(self.repo)
        self.assertEqual(lab.label("Read", {"file_path": f"/tmp/{SECRET}/README"}), "outside repo: file")
        self.assertEqual(lab.label("Edit", {"file_path": os.path.join(self.repo, ".claude", "x.json")}),
                         "outside repo: .json file")
        self.assertEqual(lab.label("Write", {"file_path": os.path.join(self.repo, "a", "b.txt")}), "a/b.txt")
        self.assertEqual(lab.label("Bash", {"command": f"bash {SECRET}.sh"}), "(no repo script)  []")

    def test_toolwatch_totals(self):
        out = self.run_py(TOOL)
        self.assertIn("== totals", out)
        self.assertRegex(out, r"Bash\s+calls\s+1\s+errors\s+0\s+result chars\s+8\b")
        self.assertRegex(out, r"Read\s+calls\s+1\s+errors\s+1\s+result chars\s+\d+")
        self.assertRegex(out, r"== repo scripts run via Bash\n\s+1\s+scripts/build.py all\n")
        self.assertIn("ERR Read", out)
        self.assertIn("'input_tokens': 31", out)
        self.assertIn("'output_tokens': 14", out)
        self.assertNotIn("== identical calls repeated", out)


if __name__ == "__main__":
    unittest.main()
