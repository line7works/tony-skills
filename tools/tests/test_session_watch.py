"""tools/session-watch/ livewatch.py and toolwatch.py against a synthetic transcript and a throwaway repo.

Offline: every test builds its own temporary repo folder and .jsonl, so no real transcript is read.
"""
import io
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


def load_livewatch():
    sys.path.insert(0, os.path.dirname(LIVE))
    try:
        import livewatch
    finally:
        sys.path.pop(0)
    return livewatch


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

    def labeler(self, **kw):
        return load_livewatch().Labeler(self.repo, **kw)

    def test_livewatch_masks_path_without_extension_and_dot_claude(self):
        lab = self.labeler()
        self.assertEqual(lab.label("Read", {"file_path": f"/tmp/{SECRET}/README"}), "outside repo: file")
        self.assertEqual(lab.label("Edit", {"file_path": os.path.join(self.repo, ".claude", "x.json")}),
                         "outside repo: .json file")
        self.assertEqual(lab.label("Write", {"file_path": os.path.join(self.repo, "a", "b.txt")}), "a/b.txt")
        self.assertEqual(lab.label("Bash", {"command": f"bash {SECRET}.sh"}), "(no repo script)  []")

    def test_toolsearch_and_skill_print_no_text(self):
        lab = self.labeler()
        self.assertEqual(lab.label("ToolSearch", {"query": f"select:{SECRET},Other"}), "select 2 tools")
        self.assertEqual(lab.label("ToolSearch", {"query": f"find {SECRET} tools"}), "keyword search")
        self.assertEqual(lab.label("Skill", {"skill": "sweep"}), "skill")
        self.assertEqual(lab.label("Skill", {"skill": SECRET + " notes"}), "skill")
        shown = self.labeler(show_skills=True)
        self.assertEqual(shown.label("Skill", {"skill": "sun:sunrise"}), "sun:sunrise")
        self.assertEqual(shown.label("Skill", {"skill": f"{SECRET} with spaces"}), "skill")

    def test_dotfile_outside_repo_has_no_extension(self):
        lab = self.labeler()
        self.assertEqual(lab.label("Read", {"file_path": f"/tmp/x/.{SECRET}"}), "outside repo: file")
        self.assertEqual(lab.label("Read", {"file_path": "/tmp/x/.env"}), "outside repo: file")
        self.assertEqual(lab.label("Read", {"file_path": None}), "outside repo: file")
        self.assertEqual(lab.label("Write", {}), "outside repo: file")

    def test_quoted_and_heredoc_flags_do_not_print(self):
        lab = self.labeler()
        out = lab.label("Bash", {"command": f"echo '--{SECRET}' \"--{SECRET}2\" --real <<EOF\n--{SECRET}3\nEOF"})
        self.assertNotIn(SECRET, out)
        self.assertIn("--real", out)
        self.assertNotIn(SECRET, lab.label("Bash", {"command": f"git log -- --{SECRET}"}))
        self.assertEqual(lab.label("Bash", {"command": f"echo 'unclosed --{SECRET}"}), "(no repo script)  []")
        self.assertNotIn("--Bad", lab.label("Bash", {"command": "x --Bad --caf\u00e9"}))

    def test_flags_capped_at_ten(self):
        out = self.labeler().label("Bash", {"command": "x " + " ".join(f"--f{i}" for i in range(15))})
        self.assertEqual(out.count("--"), 10, out)

    def test_paths_escaping_the_repo_are_masked(self):
        lab = self.labeler()
        outside_dir = os.path.join(os.path.dirname(self.repo), SECRET)
        os.makedirs(outside_dir)
        os.symlink(outside_dir, os.path.join(self.repo, "link"))
        self.assertEqual(lab.label("Read", {"file_path": os.path.join(self.repo, "..", SECRET, "a.txt")}),
                         "outside repo: .txt file")
        self.assertEqual(lab.label("Read", {"file_path": os.path.join(self.repo, "link", "b.md")}),
                         "outside repo: .md file")
        self.assertEqual(lab.label("Write", {"file_path": os.path.join(self.repo, ".claude", "settings.json")}),
                         "outside repo: .json file")
        self.assertEqual(lab.label("Read", {"file_path": "../" + SECRET + "/c.py"}), "outside repo: .py file")

    def test_split_record_while_following_is_processed_once(self):
        lw = load_livewatch()
        path = os.path.join(os.path.dirname(self.jsonl), "growing.jsonl")
        call = json.dumps(rec("assistant", 1, [{"type": "tool_use", "id": "a", "name": "Read",
                                                "input": {"file_path": "/tmp/q.md"}}]))
        result = json.dumps(rec("user", 2, [{"type": "tool_result", "tool_use_id": "a", "content": "xy"}])) + "\n"
        with open(path, "w") as w:
            w.write(call + "\n" + result[:20])
        steps = []

        class Done(Exception):
            pass

        def fake_sleep(_):
            steps.append(1)
            if len(steps) == 1:
                with open(path, "a") as w:
                    w.write(result[20:])
            elif len(steps) > 3:
                raise Done

        buf = io.StringIO()
        with open(path) as f, self.assertRaises(Done):
            lw.watch(f, lw.Labeler(self.repo), out=buf, follow=True, sleep=fake_sleep)
        lines = buf.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("#1 Read outside repo: .md file :: 1.0s, 2 chars", lines[0])

    def test_partial_last_line_with_once(self):
        with open(self.jsonl, "a") as f:
            f.write('{"type": "user", "timest')
        self.assertEqual(len(self.live_lines()), 4)

    def test_malformed_records_do_not_crash(self):
        bad = [
            {"type": "assistant", "timestamp": 12345, "message": {"content": []}},
            {"type": "user", "timestamp": "not a time", "message": {"content": "x"}},
            {"type": "user", "timestamp": "2026-01-01T00:00:07", "message": {"content": 5}},
            {"type": "assistant", "timestamp": "2026-01-01T00:00:08Z", "message": "str",},
            {"type": "assistant", "timestamp": "2026-01-01T00:00:09Z",
             "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": 3}},
                                     {"type": "tool_use", "id": "r", "name": "Read", "input": {"file_path": None}},
                                     {"type": "tool_use", "id": "r", "name": "Read", "input": {"file_path": None}},
                                     {"type": "text", "text": 7}],
                         "usage": {"input_tokens": "lots"}}},
            {"type": "user", "timestamp": "2026-01-01T00:00:10Z",
             "message": {"content": [{"type": "tool_result", "tool_use_id": "r", "content": 9}]}},
        ]
        with open(self.jsonl, "a") as f:
            for r in bad:
                f.write(json.dumps(r) + "\n")
        lines = self.live_lines()
        self.assertIn("#3 Read outside repo: file", lines[-1])
        out = self.run_py(TOOL)
        self.assertRegex(out, r"Read\s+calls\s+2\s+")
        self.assertIn("'input_tokens': 31", out)
        self.assertEqual(self.run_py(TOOL, "--since", "2026-01-01T00:00:04").count("USER"), 0)

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
