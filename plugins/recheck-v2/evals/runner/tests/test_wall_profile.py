"""The wall: the profile writer, the loopback proxy, and what a plain child can reach (A5).

No model anywhere, and no harness. Every enforcement test runs a PLAIN child under
`/usr/bin/sandbox-exec` — `cat`, `python3`, a shell redirection, `cp`, `git -C`, a grandchild
through `sh -c` — and asserts what the kernel did, not what the profile says.

The name is `test_wall_profile.py` rather than `test_wall.py`: `test_wall.py` is the ANSWER
KEY's wall (the key directories at mode 000), and the two must not be confused.
"""
import argparse
import glob
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from testlib import RunnerCase, cli, parse_stdout, runner

SANDBOX_EXEC = "/usr/bin/sandbox-exec"
WRITER_PATH = os.path.join(runner.PLUGIN_DIR, "setups", "_wall",
                           "write-sandbox-profile.py")


def _load_writer():
    spec = importlib.util.spec_from_file_location("write_sandbox_profile", WRITER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


writer = _load_writer()


def sandbox(profile, argv, cwd="/", env=None):
    """One plain child under the profile. stdout is a PIPE, which the wall does not police.

    `cwd` defaults to `/` on purpose: the suite's own working directory is inside the
    checkout, which every profile refuses, and an unreadable cwd breaks Python's path-based
    imports before the test's own code runs (`_path_importer_cache` raises PermissionError on
    the `''` entry of `sys.path`). A real launch names its workspace, which is always a root
    the profile allows.
    """
    return subprocess.run([SANDBOX_EXEC, "-f", profile] + list(argv),
                          capture_output=True, text=True, cwd=cwd,
                          env=env or {"PATH": "/usr/bin:/bin", "HOME": os.path.expanduser("~")})


def refused(completed):
    """A refusal reads the same from every tool: a non-zero status and EPERM."""
    return completed.returncode != 0 and (
        "Operation not permitted" in (completed.stderr or "")
        or "not permitted" in (completed.stdout or ""))


# --------------------------------------------------------------------------- the writer alone


class ProfileShapeTest(unittest.TestCase):
    def build(self, **spec):
        spec.setdefault("label", "a test")
        return writer.build(spec)

    def test_a_path_is_emitted_in_both_its_given_and_its_resolved_form(self):
        """`/tmp` is `/private/tmp` and `/var` is `/private/var` on this Mac."""
        text, summary = self.build(read_roots=["/tmp"])
        self.assertIn('(subpath "/tmp")', text)
        self.assertIn('(subpath "/private/tmp")', text)
        self.assertEqual([r["path"] for r in summary["read_roots"]],
                         ["/tmp", "/private/tmp"])

    def test_quotes_and_backslashes_are_escaped(self):
        text, _summary = self.build(read_roots=['/tmp/a"b\\c'])
        self.assertIn('\\"', text)
        self.assertIn("\\\\", text)
        # and the emitted text still parses as one rule per line
        self.assertTrue(all(line.count("(") == line.count(")")
                            for line in text.splitlines() if line.startswith("(")))

    def test_every_ancestor_of_every_allowed_root_keeps_read_metadata(self):
        _text, summary = self.build(write_roots=["/tmp/a/b/c"])
        for ancestor in ("/", "/private", "/private/tmp", "/private/tmp/a", "/private/tmp/a/b"):
            self.assertIn(ancestor, summary["metadata_ancestors"], ancestor)

    def test_a_refused_root_under_an_allowed_root_is_denied_AFTER_the_allows(self):
        text, summary = self.build(read_roots=["/tmp/tree"],
                                   refused_roots=["/tmp/tree/secret"])
        self.assertIn("/private/tmp/tree/secret", summary["refused_after_the_allows"])
        self.assertLess(text.index('(subpath "/private/tmp/tree")'),
                        text.index('(subpath "/private/tmp/tree/secret")'),
                        "the re-denial must come after the allow, or the allow wins")

    def test_a_refused_root_that_CONTAINS_an_allowed_root_is_denied_BEFORE_the_allows(self):
        """The case the homes make real: `<pilot>/claude-code` is refused and
        `<pilot>/claude-code/absent` is this condition's own home."""
        text, summary = self.build(read_roots=["/tmp/home/absent"],
                                   refused_roots=["/tmp/home"])
        self.assertIn("/private/tmp/home", summary["refused_before_the_allows"])
        self.assertLess(text.index('(subpath "/private/tmp/home")'),
                        text.index('(subpath "/private/tmp/home/absent")'))

    def test_the_final_text_refuses_every_refused_root(self):
        _text, summary = self.build(read_roots=["/tmp/tree", "/tmp/home/absent"],
                                    write_roots=["/tmp/tree/own"],
                                    refused_roots=["/tmp/home", "/tmp/other", "/tmp/tree/key"])
        self.assertEqual(summary["checked"][:5], "every")

    def test_a_spec_that_names_one_path_as_both_allowed_and_refused_is_refused(self):
        with self.assertRaises(writer.SpecError) as caught:
            self.build(read_roots=["/tmp/same"], refused_roots=["/tmp/same"])
        self.assertIn("both", str(caught.exception))

    def test_evaluate_is_last_match_wins(self):
        built = writer.build_rules({"read_roots": ["/tmp/tree"],
                                    "refused_roots": ["/tmp/tree/secret"]})
        self.assertEqual(writer.evaluate(built["rules"], "/private/tmp/tree/a",
                                         "file-read-data"), "allow")
        self.assertEqual(writer.evaluate(built["rules"], "/private/tmp/tree/secret/a",
                                         "file-read-data"), "deny")

    def test_the_wildcard_operation_covers_the_modes_a_narrow_list_would_miss(self):
        built = writer.build_rules({"write_roots": ["/tmp/tree"]})
        self.assertEqual(writer.evaluate(built["rules"], "/private/tmp/elsewhere",
                                         "file-write-mode"), "deny")
        self.assertEqual(writer.evaluate(built["rules"], "/private/tmp/elsewhere",
                                         "file-write-times"), "deny")

    def test_the_writer_prints_a_summary_and_writes_the_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = os.path.join(tmp, "spec.json")
            out = os.path.join(tmp, "launch.sb")
            runner.write_json(spec, {"read_roots": ["/usr/share"], "proxy_port": 1234})
            step = subprocess.run(["/usr/bin/python3", WRITER_PATH, "--spec", spec,
                                   "--out", out], capture_output=True, text=True)
            self.assertEqual(step.returncode, 0, step.stderr)
            self.assertTrue(os.path.isfile(out))
            summary = json.loads(step.stdout)
            self.assertEqual(summary["proxy_port"], 1234)
            self.assertIn('(allow network-outbound (remote ip "localhost:1234"))',
                          runner.read_text(out))

    def test_a_spec_that_cannot_keep_its_promises_exits_two_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = os.path.join(tmp, "spec.json")
            out = os.path.join(tmp, "launch.sb")
            runner.write_json(spec, {"read_roots": ["/tmp/x"], "refused_roots": ["/tmp/x"]})
            step = subprocess.run(["/usr/bin/python3", WRITER_PATH, "--spec", spec,
                                   "--out", out], capture_output=True, text=True)
            self.assertEqual(step.returncode, 2, step.stdout)
            self.assertFalse(os.path.exists(out))


# --------------------------------------------------------------- what a plain child can reach


@unittest.skipUnless(os.path.isfile(SANDBOX_EXEC), "this machine has no sandbox-exec")
class WallEnforcementTest(unittest.TestCase):
    """The tree of A5: an own trial tree, another trial tree, two homes, a stage, a fake
    `trials/` and `records/`. Every forbidden read and write is refused by the KERNEL."""

    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="wall-", dir="/private/tmp")
        cls.mine = os.path.join(cls.root, "tmp", "own-tree")
        cls.theirs = os.path.join(cls.root, "tmp", "other-tree")
        cls.home = os.path.join(cls.root, "homes", "available")
        cls.other_home = os.path.join(cls.root, "homes", "absent")
        cls.stage = os.path.join(cls.root, "stage")
        cls.trials = os.path.join(cls.root, "trials")
        cls.records = os.path.join(cls.root, "records")
        cls.record = os.path.join(cls.trials, "own-record")
        for path in (cls.mine, cls.theirs, cls.home, cls.other_home, cls.trials,
                     cls.records, cls.record):
            os.makedirs(path)
        # the staged skill, as the launch reads it
        cls.skill_files = []
        for leaf in ("references", "scripts", "adapters", "schemas"):
            directory = os.path.join(cls.stage, "plugins", "recheck-v2", "skills",
                                     "recheck-v2", leaf)
            os.makedirs(directory)
            path = os.path.join(directory, "a-%s-file" % leaf)
            runner.write_text(path, "the staged skill's %s\n" % leaf)
            cls.skill_files.append(path)
        for path, text in ((os.path.join(cls.theirs, "result.json"), "another trial's result"),
                           (os.path.join(cls.other_home, "install.json"), "the other home"),
                           (os.path.join(cls.trials, "sentinel.txt"), "a sibling trial"),
                           (os.path.join(cls.records, "grade.json"), "a grading record"),
                           (os.path.join(cls.home, "state.json"), "this home's own state"),
                           (os.path.join(cls.mine, "input.json"), "this trial's own input")):
            runner.write_text(path, text)
        # a symlink INSIDE the own tree that points outside it
        cls.escape = os.path.join(cls.mine, "escape-link")
        os.symlink(os.path.join(cls.theirs, "result.json"), cls.escape)
        cls.profile = os.path.join(cls.root, "launch.sb")
        spec = {
            "label": "the A5 test tree",
            "read_roots": [cls.stage, "/usr", "/bin", "/System", "/Library",
                           os.path.join(os.path.expanduser("~"), ".gitconfig")],
            "write_roots": [cls.mine, cls.home, cls.record],
            "refused_roots": [cls.theirs, cls.other_home, cls.trials, cls.records,
                              os.path.join(cls.root, "homes")],
            "proxy_port": None,
        }
        text, cls.summary = writer.build(spec)
        runner.write_text(cls.profile, text)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    # ---- the reads that must work
    def test_every_file_of_the_staged_skill_is_readable(self):
        for path in self.skill_files:
            got = sandbox(self.profile, ["/bin/cat", path])
            self.assertEqual(got.returncode, 0, "%s: %s" % (path, got.stderr))
            self.assertIn("staged skill", got.stdout)

    def test_the_trials_own_tree_is_readable_and_writable(self):
        got = sandbox(self.profile, ["/bin/cat", os.path.join(self.mine, "input.json")])
        self.assertEqual(got.returncode, 0, got.stderr)
        target = os.path.join(self.mine, "written-by-the-child.txt")
        got = sandbox(self.profile, ["/bin/sh", "-c", "echo written > %s" % target])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(runner.read_text(target), "written\n")

    def test_this_conditions_own_home_is_readable(self):
        got = sandbox(self.profile, ["/bin/cat", os.path.join(self.home, "state.json")])
        self.assertEqual(got.returncode, 0, got.stderr)

    def test_the_tools_a_trial_runs_still_run(self):
        for argv in (["/usr/bin/git", "--version"],
                     ["/usr/bin/python3", "-c", "print('python3 ran')"]):
            got = sandbox(self.profile, argv)
            self.assertEqual(got.returncode, 0, "%s: %s" % (argv, got.stderr))
        uv = runner.which("uv")
        if uv:
            got = sandbox(self.profile, [uv, "--version"])
            self.assertEqual(got.returncode, 0, got.stderr)

    def test_git_C_works_inside_the_trials_own_tree(self):
        repo = os.path.join(self.mine, "repo")
        os.makedirs(repo, exist_ok=True)
        got = sandbox(self.profile, ["/bin/sh", "-c",
                                     "/usr/bin/git init -q %s && /usr/bin/git -C %s status "
                                     "--porcelain && echo GIT-OK" % (repo, repo)])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertIn("GIT-OK", got.stdout)

    # ---- the reads that must be refused
    def test_another_trials_tree_is_refused_to_cat_and_to_python(self):
        target = os.path.join(self.theirs, "result.json")
        self.assertTrue(refused(sandbox(self.profile, ["/bin/cat", target])))
        got = sandbox(self.profile, ["/usr/bin/python3", "-c",
                                     "import sys;open(sys.argv[1]).read()", target])
        self.assertTrue(refused(got), got.stderr)
        self.assertIn("PermissionError", got.stderr)

    def test_the_other_conditions_home_is_refused(self):
        self.assertTrue(refused(sandbox(
            self.profile, ["/bin/cat", os.path.join(self.other_home, "install.json")])))

    def test_the_sibling_trials_and_the_grading_records_are_refused(self):
        for target in (os.path.join(self.trials, "sentinel.txt"),
                       os.path.join(self.records, "grade.json")):
            self.assertTrue(refused(sandbox(self.profile, ["/bin/cat", target])), target)

    def test_a_grandchild_through_sh_c_is_refused_the_same_way(self):
        got = sandbox(self.profile, ["/bin/sh", "-c",
                                     "/bin/sh -c '/bin/cat %s'"
                                     % os.path.join(self.theirs, "result.json")])
        self.assertNotEqual(got.returncode, 0)
        self.assertIn("Operation not permitted", got.stderr)

    def test_a_symlink_inside_the_own_tree_that_points_outside_it_is_refused(self):
        """The link is reachable; what it POINTS AT is not. The kernel checks the resolved
        path, so a link is not a way through the wall."""
        self.assertTrue(os.path.islink(self.escape))
        self.assertTrue(refused(sandbox(self.profile, ["/bin/cat", self.escape])))

    def test_a_hard_path_through_tmp_and_private_tmp_is_refused_alike(self):
        """`/tmp` is a symlink to `/private/tmp`; both spellings of the same forbidden file
        are refused, because the deny names both forms."""
        target = os.path.join(self.theirs, "result.json")
        through_tmp = target.replace("/private/tmp/", "/tmp/", 1)
        self.assertTrue(refused(sandbox(self.profile, ["/bin/cat", target])))
        self.assertTrue(refused(sandbox(self.profile, ["/bin/cat", through_tmp])))

    # ---- the writes that must be refused
    def test_a_shell_redirection_outside_the_write_roots_is_refused(self):
        target = os.path.join(self.theirs, "planted.txt")
        got = sandbox(self.profile, ["/bin/sh", "-c", "echo planted > %s" % target])
        self.assertNotEqual(got.returncode, 0)
        self.assertFalse(os.path.exists(target))

    def test_cp_out_of_the_own_tree_is_refused(self):
        source = os.path.join(self.mine, "input.json")
        target = os.path.join(self.other_home, "copied.json")
        got = sandbox(self.profile, ["/bin/cp", source, target])
        self.assertNotEqual(got.returncode, 0)
        self.assertFalse(os.path.exists(target))

    def test_a_write_into_the_records_root_is_refused(self):
        target = os.path.join(self.records, "planted.json")
        got = sandbox(self.profile, ["/usr/bin/python3", "-c",
                                     "import sys;open(sys.argv[1],'w').write('x')", target])
        self.assertNotEqual(got.returncode, 0)
        self.assertIn("PermissionError", got.stderr)
        self.assertFalse(os.path.exists(target))

    def test_chmod_outside_the_write_roots_is_refused(self):
        """`file-write*`, not a narrow list: a mode change is a write."""
        target = os.path.join(self.theirs, "result.json")
        before = stat.S_IMODE(os.stat(target).st_mode)
        got = sandbox(self.profile, ["/bin/chmod", "700", target])
        self.assertNotEqual(got.returncode, 0)
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), before)


# --------------------------------------------------------------------------- the proxy (A2)


class WallProxyTest(unittest.TestCase):
    """Loopback only, so this runs the same offline. An echo listener stands in for the
    'allowed host' and is allowlisted in the TEST spec only."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="wall-proxy-", dir="/private/tmp")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(4)
        self.echo_port = self.listener.getsockname()[1]
        self.addCleanup(self.listener.close)
        threading.Thread(target=self._serve, daemon=True).start()
        self.log = os.path.join(self.root, "proxy.jsonl")
        self.proxy = runner.wall_proxy.WallProxy(["127.0.0.1:%d" % self.echo_port], self.log)
        self.proxy.start()
        self.addCleanup(self.proxy.stop)

    def _serve(self):
        while True:
            try:
                client, _ = self.listener.accept()
            except OSError:
                return
            try:
                client.sendall(b"ECHO-LISTENER\n")
            finally:
                client.close()

    def connect(self, target):
        client = socket.create_connection(("127.0.0.1", self.proxy.port), timeout=10)
        client.sendall(("CONNECT %s HTTP/1.1\r\nHost: %s\r\n\r\n"
                        % (target, target)).encode("ascii"))
        head = client.recv(200)
        return client, head.decode("latin-1")

    def log_rows(self):
        return [json.loads(line) for line in runner.read_text(self.log, "").splitlines()
                if line.strip()]

    def test_an_allowed_host_gets_connect_200_and_the_bytes_flow(self):
        client, head = self.connect("127.0.0.1:%d" % self.echo_port)
        self.addCleanup(client.close)
        self.assertIn("200 Connection established", head)
        self.assertIn(b"ECHO-LISTENER", client.recv(100))

    def test_a_host_that_is_not_on_the_allowlist_gets_403_and_a_log_line(self):
        client, head = self.connect("api.example.invalid:443")
        client.close()
        self.assertIn("403 Forbidden", head)
        rows = [r for r in self.log_rows() if r.get("host") == "api.example.invalid"]
        self.assertEqual(len(rows), 1, self.log_rows())
        self.assertEqual(rows[0]["outcome"], "refused")
        self.assertEqual(rows[0]["bytes_to_host"], 0)

    def test_a_plain_http_request_is_refused(self):
        client = socket.create_connection(("127.0.0.1", self.proxy.port), timeout=10)
        self.addCleanup(client.close)
        client.sendall(b"GET http://example.invalid/ HTTP/1.1\r\nHost: example.invalid\r\n\r\n")
        self.assertIn("403 Forbidden", client.recv(200).decode("latin-1"))

    def test_the_log_carries_no_header_and_no_body(self):
        client, _head = self.connect("127.0.0.1:%d" % self.echo_port)
        client.sendall(b"a-secret-request-body")
        client.close()
        blob = runner.read_text(self.log, "")
        self.assertNotIn("a-secret-request-body", blob)
        self.assertNotIn("Host:", blob)

    @unittest.skipUnless(os.path.isfile(SANDBOX_EXEC), "this machine has no sandbox-exec")
    def test_a_walled_child_reaches_an_allowed_host_only_through_the_proxy(self):
        """The whole of A2, with a plain child and no network beyond loopback.

        The "allowed host" is this test's own echo listener, allowlisted as
        `127.0.0.1:<port>` in the TEST spec only. Nothing here leaves the machine, so it runs
        the same offline.
        """
        profile = os.path.join(self.root, "net.sb")
        text, _summary = writer.build({"label": "network", "proxy_port": self.proxy.port,
                                       "read_roots": ["/usr", "/bin", "/System", "/Library"]})
        runner.write_text(profile, text)
        speak = (
            "import socket,sys\n"
            "s=socket.create_connection(('127.0.0.1',int(sys.argv[1])),timeout=10)\n"
            "s.sendall(('CONNECT %s HTTP/1.1\\r\\nHost: %s\\r\\n\\r\\n'"
            "%(sys.argv[2],sys.argv[2])).encode())\n"
            "sys.stdout.write(s.recv(200).decode('latin-1'))\n")
        # 1. an allowed host, through the proxy: CONNECT 200
        got = sandbox(profile, ["/usr/bin/python3", "-c", speak, str(self.proxy.port),
                                "127.0.0.1:%d" % self.echo_port])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertIn("200 Connection established", got.stdout)
        # 2. a refused host, through the same proxy: 403, and a log line naming it
        got = sandbox(profile, ["/usr/bin/python3", "-c", speak, str(self.proxy.port),
                                "walled.example.invalid:443"])
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertIn("403 Forbidden", got.stdout)
        rows = [r for r in self.log_rows() if r.get("host") == "walled.example.invalid"]
        self.assertEqual(len(rows), 1, self.log_rows())
        self.assertEqual(rows[0]["outcome"], "refused")
        # 3. the same allowed host DIRECTLY, with no proxy: the profile refuses the connection
        direct = ("import socket,sys\n"
                  "socket.create_connection(('127.0.0.1',int(sys.argv[1])),timeout=5)\n")
        got = sandbox(profile, ["/usr/bin/python3", "-c", direct, str(self.echo_port)])
        self.assertNotEqual(got.returncode, 0)
        self.assertIn("PermissionError", got.stderr)


# ------------------------------------------------------------------ the wall in the runner


class WallInTheRunnerTest(RunnerCase):
    """`wall_spec`, `Setup.walled` and the two A4 refusals, with no launch."""

    def setup_object(self):
        campaign = runner.Campaign(self.campaign)
        return campaign, runner.ClaudeCodeSetup(campaign, stage=self.stage)

    def staged_launcher(self, setup):
        """The stage of a test campaign holds empty setup directories; the wall's own code
        asks the setup which executable a launch selects, so the file has to be there."""
        path = os.path.join(setup.setup_dir, "launch.sh")
        if not os.path.isfile(path):
            runner.write_text(path, "#!/bin/sh\nexit 0\n")
        return path

    def test_the_spec_names_this_conditions_home_and_refuses_the_others(self):
        campaign, setup = self.setup_object()
        out_dir = os.path.join(campaign.trials, "a-trial", "harness")
        spec = runner.wall_spec(campaign, setup, "available", out_dir,
                                workspace=os.path.join(self.scratch, "ws"),
                                scratch=os.path.join(self.scratch, "tree", "scratch"))
        allowed = [r["path"] for r in spec["read_roots"] + spec["write_roots"]]
        refused_paths = [r["path"] for r in spec["refused_roots"]]
        self.assertIn(os.path.realpath(setup.home("available")),
                      [os.path.realpath(p) for p in allowed])
        for other in ("absent", "routing"):
            self.assertIn(os.path.realpath(setup.home(other)), refused_paths, other)
        self.assertIn(os.path.realpath(campaign.trials), refused_paths)
        self.assertIn(os.path.realpath(campaign.tmp), refused_paths)
        self.assertIn(os.path.realpath(runner.REPO_ROOT), refused_paths)

    def test_the_spec_the_runner_builds_produces_a_profile_that_keeps_its_promises(self):
        campaign, setup = self.setup_object()
        out_dir = os.path.join(campaign.trials, "a-trial", "harness")
        runner.ensure_dir(setup.home("available"))
        spec = runner.wall_spec(campaign, setup, "available", out_dir,
                                workspace=os.path.join(self.scratch, "ws"),
                                scratch=os.path.join(self.scratch, "tree", "scratch"),
                                proxy_port=9999)
        text, summary = writer.build(spec)
        self.assertIn("(deny file-write*)", text)
        self.assertIn('(allow network-outbound (remote ip "localhost:9999"))', text)
        self.assertGreater(len(summary["refused_roots"]), 5)

    def test_a_fake_launcher_bypasses_the_wall_and_says_so(self):
        campaign, setup = self.setup_object()
        out_dir = os.path.join(self.scratch, "harness")
        with setup.walled("available", out_dir,
                          launcher=self.fake_launcher("claude-code")) as wall:
            self.assertEqual(wall.record, {"sealed": False, "why": "fake launcher"})
            self.assertEqual(wall.prefix(["sh", "x"]), ["sh", "x"])
            self.assertEqual(wall.env, {})

    def test_a_synthetic_campaign_bypasses_the_wall_and_says_so(self):
        campaign, setup = self.setup_object()
        out_dir = os.path.join(self.scratch, "harness-2")
        self.staged_launcher(setup)
        with setup.walled("available", out_dir, launcher=setup.script("launch.sh")) as wall:
            self.assertFalse(wall.record["sealed"])
            self.assertIn("synthetic", wall.record["why"])

    def test_a_trial_record_carries_the_wall_block(self):
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertIn("wall", command)
        self.assertFalse(command["wall"]["sealed"])
        self.assertTrue(command["wall"]["why"])


class WallProxyThroughputTest(unittest.TestCase):
    """Send-back 4: back-pressure must never look like a closed connection.

    The first relay set both sockets non-blocking and called `sendall` on them. When the far
    side's buffer filled, `sendall` raised `BlockingIOError` (EAGAIN), the handler read that as
    a close, and the proxy tore a live session down mid-stream: two walled comparison trials
    ran three minutes and ended `API Error: Connection dropped (ECONNRESET)` with
    `bytes_to_host` at 131404 (proof root `wall-proof-20260919T162738Z`).

    Loopback only and no model. The "allowed host" is this test's own listener, allowlisted as
    `127.0.0.1:<port>` in the TEST spec only.
    """

    # One megabyte of incompressible bytes, repeated. 50 MiB each way is enough to fill every
    # buffer in the path several times over; the old relay died at about one megabyte.
    BLOCK = os.urandom(1 << 20)
    COPIES = 50
    TOTAL = (1 << 20) * 50

    @classmethod
    def expected_digest(cls):
        h = hashlib.sha256()
        for _ in range(cls.COPIES):
            h.update(cls.BLOCK)
        return h.hexdigest()

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="wall-relay-", dir="/private/tmp")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(4)
        self.far_port = self.listener.getsockname()[1]
        self.addCleanup(self.listener.close)
        self.far = {}
        self.log = os.path.join(self.root, "proxy.jsonl")
        self.proxy = runner.wall_proxy.WallProxy(["127.0.0.1:%d" % self.far_port], self.log)
        self.proxy.start()
        self.addCleanup(self.proxy.stop)

    def serve(self, target):
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        return thread

    def connect(self):
        target = "127.0.0.1:%d" % self.far_port
        client = socket.create_connection(("127.0.0.1", self.proxy.port), timeout=30)
        client.sendall(("CONNECT %s HTTP/1.1\r\nHost: %s\r\n\r\n"
                        % (target, target)).encode("ascii"))
        head = client.recv(200).decode("latin-1")
        self.assertIn("200 Connection established", head)
        client.settimeout(180)
        return client

    def read_exactly(self, sock, total, chunk=4096, sleep_every=0, sleep_for=0.0):
        """Read `total` bytes, slowly on purpose, hashing as it goes."""
        digest, seen, reads = hashlib.sha256(), 0, 0
        while seen < total:
            blob = sock.recv(chunk)
            if not blob:
                break
            digest.update(blob)
            seen += len(blob)
            reads += 1
            if sleep_every and reads % sleep_every == 0:
                time.sleep(sleep_for)
        return digest.hexdigest(), seen

    def log_rows(self):
        return [json.loads(line) for line in runner.read_text(self.log, "").splitlines()
                if line.strip()]

    def test_fifty_megabytes_each_way_past_a_slow_reader_arrive_byte_for_byte(self):
        want = self.expected_digest()

        def far_side():
            conn, _ = self.listener.accept()
            conn.settimeout(180)
            try:
                self.far["up_sha"], self.far["up_bytes"] = self.read_exactly(
                    conn, self.TOTAL, chunk=4096, sleep_every=32, sleep_for=0.001)
                for _ in range(self.COPIES):
                    conn.sendall(self.BLOCK)
                conn.shutdown(socket.SHUT_WR)
            except OSError as exc:
                self.far["error"] = str(exc)
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

        thread = self.serve(far_side)
        client = self.connect()

        def push():
            try:
                for _ in range(self.COPIES):
                    client.sendall(self.BLOCK)
            except OSError as exc:
                self.far["push_error"] = str(exc)

        pusher = threading.Thread(target=push)
        pusher.start()
        down_sha, down_bytes = self.read_exactly(client, self.TOTAL, chunk=4096,
                                                 sleep_every=64, sleep_for=0.0005)
        pusher.join(timeout=180)
        thread.join(timeout=30)

        self.assertIsNone(self.far.get("error"), self.far)
        self.assertIsNone(self.far.get("push_error"), self.far)
        self.assertEqual(self.far.get("up_bytes"), self.TOTAL, "the upload was cut short")
        self.assertEqual(self.far.get("up_sha"), want, "the upload arrived corrupted")
        self.assertEqual(down_bytes, self.TOTAL, "the download was cut short")
        self.assertEqual(down_sha, want, "the download arrived corrupted")

        # and the proxy's own log agrees, and says the relay ended cleanly
        client.close()
        for _ in range(100):
            rows = [r for r in self.log_rows() if r.get("outcome") == "allowed"]
            if rows:
                break
            time.sleep(0.05)
        self.assertEqual(len(rows), 1, self.log_rows())
        self.assertEqual(rows[0]["bytes_to_host"], self.TOTAL)
        self.assertEqual(rows[0]["bytes_to_client"], self.TOTAL)
        self.assertTrue(rows[0]["clean"], rows[0])

    def test_a_stream_held_idle_mid_way_resumes_rather_than_dropping(self):
        """A model that pauses between tokens is not a model that hung up."""
        payload = self.BLOCK[:1 << 18]

        def far_side():
            conn, _ = self.listener.accept()
            conn.settimeout(60)
            try:
                first, _n = self.read_exactly(conn, len(payload))
                conn.sendall(payload)
                time.sleep(3)                       # the pause
                conn.sendall(payload)
                second, _n = self.read_exactly(conn, len(payload))
                self.far["halves"] = (first, second)
                conn.shutdown(socket.SHUT_WR)
            except OSError as exc:
                self.far["error"] = str(exc)

        thread = self.serve(far_side)
        client = self.connect()
        want = hashlib.sha256(payload).hexdigest()
        client.sendall(payload)
        first, first_bytes = self.read_exactly(client, len(payload))
        time.sleep(3)                               # idle in the other direction too
        client.sendall(payload)
        second, second_bytes = self.read_exactly(client, len(payload))
        thread.join(timeout=30)
        self.assertIsNone(self.far.get("error"), self.far)
        self.assertEqual((first_bytes, second_bytes), (len(payload), len(payload)))
        self.assertEqual([first, second], [want, want])
        self.assertEqual(list(self.far.get("halves")), [want, want])

    def test_a_half_close_keeps_the_other_direction_open(self):
        """The client says it is done sending; everything the far side still owes arrives."""
        up = self.BLOCK[:1 << 16]
        down = self.BLOCK[:1 << 20]

        def far_side():
            conn, _ = self.listener.accept()
            conn.settimeout(60)
            try:
                seen = b""
                while len(seen) < len(up):
                    blob = conn.recv(4096)
                    if not blob:
                        break
                    seen += blob
                # the half-close must arrive as a plain EOF, not as an error
                self.far["eof_after_up"] = conn.recv(4096) == b""
                self.far["up"] = hashlib.sha256(seen).hexdigest()
                conn.sendall(down)
                conn.shutdown(socket.SHUT_WR)
                conn.close()
            except OSError as exc:
                self.far["error"] = str(exc)

        thread = self.serve(far_side)
        client = self.connect()
        client.sendall(up)
        client.shutdown(socket.SHUT_WR)
        got, got_bytes = self.read_exactly(client, len(down))
        thread.join(timeout=30)
        self.assertIsNone(self.far.get("error"), self.far)
        self.assertTrue(self.far.get("eof_after_up"), self.far)
        self.assertEqual(self.far.get("up"), hashlib.sha256(up).hexdigest())
        self.assertEqual(got_bytes, len(down), "the far side's reply was cut short")
        self.assertEqual(got, hashlib.sha256(down).hexdigest())

    def test_the_headers_are_read_unbuffered_so_nothing_is_swallowed(self):
        """A client that sends its first payload bytes in the SAME packet as the CONNECT
        headers must not lose them to a read-ahead buffer."""
        self.assertEqual(runner.wall_proxy._Handler.rbufsize, 0)
        payload = b"the-first-bytes-after-the-headers"

        def far_side():
            conn, _ = self.listener.accept()
            conn.settimeout(30)
            try:
                self.far["first"] = conn.recv(len(payload))
                conn.close()
            except OSError as exc:
                self.far["error"] = str(exc)

        thread = self.serve(far_side)
        target = "127.0.0.1:%d" % self.far_port
        client = socket.create_connection(("127.0.0.1", self.proxy.port), timeout=30)
        self.addCleanup(client.close)
        client.sendall(("CONNECT %s HTTP/1.1\r\nHost: %s\r\n\r\n"
                        % (target, target)).encode("ascii") + payload)
        client.settimeout(30)
        self.assertIn("200 Connection established", client.recv(200).decode("latin-1"))
        thread.join(timeout=30)
        self.assertEqual(self.far.get("first"), payload, self.far)


@unittest.skipUnless(os.path.isfile(SANDBOX_EXEC), "this machine has no sandbox-exec")
class GitConfigReadsTest(RunnerCase):
    """Send-back 4 item 3: git's two global config locations are declared reads, identically
    for both setups and therefore for both conditions.

    Measured 2026-09-19 on this Mac: with `~/.config` refused, `git status` prints
    `warning: unable to access '~/.config/git/ignore': Operation not permitted` and continues;
    `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null` does NOT silence it, because the
    `core.excludesFile` default is applied independently of any config file; allowing the
    directory does silence it.
    """

    def test_both_setups_declare_the_same_two_git_paths_with_a_reason(self):
        campaign = runner.Campaign(self.campaign)
        for cls, name in ((runner.ClaudeCodeSetup, "claude-code"),
                          (runner.CodexSetup, "codex")):
            needs = runner.wall_needs(cls(campaign, stage=self.stage, name=name))
            paths = {e["path"]: e for e in needs["read"]}
            for wanted in ("~/.gitconfig", "~/.config/git"):
                self.assertIn(wanted, paths, name)
                self.assertTrue(paths[wanted].get("optional"), (name, wanted))
                self.assertGreater(len(paths[wanted]["why"]), 60, (name, wanted))

    def test_the_declared_paths_reach_the_profile_and_silence_the_warning(self):
        """A real `git status` under a real profile built from the real needs file."""
        campaign = runner.Campaign(self.campaign)
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        runner.ensure_dir(setup.home("available"))
        work = os.path.join(self.scratch, "gitwork")
        repo = os.path.join(work, "repo")
        runner.ensure_dir(repo)
        runner.run_cmd(["/usr/bin/git", "init", "-q", repo], env=runner.tool_env(),
                       label="init")
        runner.write_text(os.path.join(repo, "a.txt"), "x\n")
        spec = runner.wall_spec(campaign, setup, "available",
                                os.path.join(campaign.trials, "t", "harness"),
                                workspace=repo, run_dir=os.path.join(work, "run"),
                                scratch=os.path.join(work, "scratch"),
                                roots=[work])
        declared = [os.path.realpath(os.path.expanduser("~/.config/git"))]
        self.assertTrue([r for r in spec["read_roots"]
                         if os.path.realpath(r["path"]) in declared],
                        "~/.config/git is not in the profile's read roots")
        profile = os.path.join(self.scratch, "git.sb")
        text, _summary = writer.build(spec)
        runner.write_text(profile, text)
        got = sandbox(profile, ["/usr/bin/git", "-C", repo, "status", "--porcelain"],
                      cwd=repo)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertNotIn("Operation not permitted", got.stderr)
        self.assertNotIn("unable to access", got.stderr)
        self.assertIn("a.txt", got.stdout)


@unittest.skipUnless(os.path.isfile(SANDBOX_EXEC), "this machine has no sandbox-exec")
class NamedCwdTest(unittest.TestCase):
    """Send-back 1, fault 1: a walled child never inherits the operator's cwd.

    The control room ran the runner from a scratch under `/private/tmp`, which every profile
    refuses, so every shell in `launch.sh` printed `getcwd: cannot access parent directories:
    Operation not permitted` before a model was called. This proves both halves: inheriting a
    refused cwd breaks the child, and the named cwd fixes it.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="wall-cwd-", dir="/private/tmp")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.refused = os.path.join(self.root, "where-the-operator-stood")
        self.allowed = os.path.join(self.root, "the-launchs-own-workspace")
        os.makedirs(self.refused)
        os.makedirs(self.allowed)
        self.profile = os.path.join(self.root, "launch.sb")
        text, _summary = writer.build({
            "label": "the named cwd",
            "read_roots": ["/usr", "/bin", "/System", "/Library"],
            "write_roots": [self.allowed],
            "refused_roots": [self.refused],
        })
        runner.write_text(self.profile, text)

    def test_a_child_that_INHERITS_a_refused_cwd_cannot_even_getcwd(self):
        """The fault, reproduced: this is what the first live proof did."""
        got = sandbox(self.profile, ["/bin/sh", "-c", "pwd"], cwd=self.refused)
        self.assertIn("getcwd", (got.stderr or "") + (got.stdout or ""))
        got = sandbox(self.profile, ["/usr/bin/python3", "-c", "import os;print(os.getcwd())"],
                      cwd=self.refused)
        self.assertNotEqual(got.returncode, 0)
        self.assertIn("PermissionError", got.stderr)

    def test_a_child_given_the_NAMED_cwd_resolves_it(self):
        got = sandbox(self.profile, ["/bin/sh", "-c", "pwd"], cwd=self.allowed)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(got.stdout.strip(), os.path.realpath(self.allowed))
        self.assertNotIn("getcwd", got.stderr or "")
        got = sandbox(self.profile, ["/usr/bin/python3", "-c", "import os;print(os.getcwd())"],
                      cwd=self.allowed)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(got.stdout.strip(), os.path.realpath(self.allowed))

    def test_a_grandchild_of_the_named_cwd_resolves_it_too(self):
        """`launch.sh` runs a python post-step through a shell; the cwd has to survive both."""
        got = sandbox(self.profile,
                      ["/bin/sh", "-c",
                       "/bin/sh -c '/usr/bin/python3 -c \"import os;print(os.getcwd())\"'"],
                      cwd=self.allowed)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(got.stdout.strip(), os.path.realpath(self.allowed))


class CodexLauncherToleratesTheWallsOwnFilesTest(unittest.TestCase):
    """The regression the wall introduced, and the fix, with a STUB `codex` and no model.

    `walled` writes `launch.sb`, `launch-wall.json` and `proxy.jsonl` into `<record>/harness/`
    BEFORE the launcher runs. `setups/codex/launch.sh` refused any out-dir that merely existed,
    so every walled Codex trial would have exited before reaching the model. The refusal now
    names the session records a SPENT directory holds, the way claude-code's does.
    """

    LAUNCHER = os.path.join(runner.PLUGIN_DIR, "setups", "codex", "launch.sh")

    def run_launcher(self, out_dir):
        root = tempfile.mkdtemp(prefix="codex-launch-", dir="/private/tmp")
        self.addCleanup(shutil.rmtree, root, True)
        binaries = os.path.join(root, "bin")
        os.makedirs(binaries)
        stub = os.path.join(binaries, "codex")
        runner.write_text(stub, "#!/bin/sh\nexit 0\n")
        os.chmod(stub, 0o755)
        workspace = os.path.join(root, "ws")
        os.makedirs(workspace)
        prompt = os.path.join(root, "prompt.txt")
        runner.write_text(prompt, "a prompt this test wrote\n")
        home = os.path.join(root, "codex-home")
        os.makedirs(os.path.join(home, "child"))
        return subprocess.run(
            ["sh", self.LAUNCHER, prompt, workspace, out_dir],
            capture_output=True, text=True,
            env={"PATH": binaries + ":/usr/bin:/bin", "HOME": root,
                 "RECHECK_CODEX_HOME": home})

    def test_an_out_dir_holding_only_the_walls_own_files_is_accepted(self):
        root = tempfile.mkdtemp(prefix="codex-out-", dir="/private/tmp")
        self.addCleanup(shutil.rmtree, root, True)
        out_dir = os.path.join(root, "harness")
        os.makedirs(out_dir)
        for name in ("launch.sb", "launch-wall.json", "proxy.jsonl"):
            runner.write_text(os.path.join(out_dir, name), "written by the wall\n")
        got = self.run_launcher(out_dir)
        self.assertNotIn("refusing to overwrite", got.stderr)
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "launch.json")), got.stderr)
        # and the wall's own files are still there afterwards
        for name in ("launch.sb", "launch-wall.json", "proxy.jsonl"):
            self.assertTrue(os.path.isfile(os.path.join(out_dir, name)), name)

    def test_an_out_dir_holding_a_session_record_is_still_refused(self):
        root = tempfile.mkdtemp(prefix="codex-out-", dir="/private/tmp")
        self.addCleanup(shutil.rmtree, root, True)
        out_dir = os.path.join(root, "harness")
        os.makedirs(out_dir)
        runner.write_text(os.path.join(out_dir, "events.jsonl"), "a live session's record\n")
        got = self.run_launcher(out_dir)
        self.assertNotEqual(got.returncode, 0)
        self.assertIn("refusing to overwrite a live session", got.stderr)
        self.assertIn("events.jsonl", got.stderr)

    def test_the_launcher_runs_codex_with_the_walls_sandbox_flags_and_no_network_setting(self):
        root = tempfile.mkdtemp(prefix="codex-out-", dir="/private/tmp")
        self.addCleanup(shutil.rmtree, root, True)
        out_dir = os.path.join(root, "harness")
        self.run_launcher(out_dir)
        command = runner.read_json(os.path.join(out_dir, "command.json"))
        self.assertIn("--sandbox", command)
        self.assertEqual(command[command.index("--sandbox") + 1], "danger-full-access")
        self.assertIn("approval_policy=never", command)
        self.assertNotIn("sandbox_workspace_write.network_access=true", command)


class EveryLaunchKindsTmpdirIsInsideAWriteRootTest(RunnerCase):
    """Send-back 1, fault 2: the audit, as a test.

    Every walled launch kind's TMPDIR, its `${TMPDIR}/runs` (which
    `setups/claude-code/launch.sh` creates on every launch), its run directory and its
    adapters' run root must each sit inside a write root of its own profile, and its named
    cwd inside a read root. The native check died in under a second because one kind's TMPDIR
    was the campaign's shared `tmp/`, which is a REFUSED root.

    The kinds are built here the way each call site builds them, from the runner's own
    helpers, so a call site that stops using `trial_scratch` or `probe_scratch` fails here.
    """

    def campaign_and_setup(self, name="claude-code"):
        campaign = runner.Campaign(self.campaign)
        cls = {"claude-code": runner.ClaudeCodeSetup, "codex": runner.CodexSetup,
               "opencode": runner.OpenCodeSetup}[name]
        setup = cls(campaign, stage=self.stage, name=name)
        runner.ensure_dir(setup.home("available"))
        return campaign, setup

    def kinds(self, campaign, setup):
        """`(name, workspace, run_dir, scratch, roots, out_dir)` per launch kind."""
        rows = []

        def trial_shaped(name, tid, kind_attempt=0):
            tree = campaign.opaque_tree(tid, kind_attempt)
            case = os.path.join(tree, "fixture", "abc123def456")
            workspace = os.path.join(case, "workspace")
            run_dir = os.path.join(case, "run")
            scratch = runner.trial_scratch(campaign, tid, kind_attempt)
            return (name, workspace, run_dir, scratch,
                    runner.named_writable_roots(run_dir),
                    os.path.join(campaign.trials, tid, "harness"))

        # 1. comparison, and 2. its rerun (the same path, another attempt)
        rows.append(trial_shaped("comparison", "claude-code-F1-01-fixed-clean-available-r1"))
        rows.append(trial_shaped("rerun", "claude-code-F1-01-fixed-clean-available-r1", 1))
        # 3. routing: the workspace is the opaque tree's own, not a fixture leaf
        tid = "routing-claude-code-T-01-slash-v2-slice-r1"
        tree = campaign.opaque_tree(tid, 0)
        rows.append(("routing", os.path.join(tree, "workspace"),
                     os.path.join(tree, "run"), runner.trial_scratch(campaign, tid, 0),
                     runner.named_writable_roots(os.path.join(tree, "run")),
                     os.path.join(campaign.trials, tid, "harness")))
        # 4. and 5. both continuation halves
        rows.append(trial_shaped("continuation-first", "cont-claude-code-F3-02-handoff-r1"))
        rows.append(trial_shaped("continuation-second", "cont-claude-code-F3-02-handoff-r1"))
        # 6. the compaction resume
        rows.append(trial_shaped("compaction-resume", "cont-claude-code-F3-02-compaction-r1"))
        # 7. the consumer: its workspace is inside the pair directory of its own tree
        tid = "consumer-claude-code-from-codex-r1"
        tree = campaign.opaque_tree(tid, 0)
        pair = os.path.join(tree, "pair")
        rows.append(("consumer", os.path.join(pair, "workspace"),
                     os.path.join(pair, "run"), runner.trial_scratch(campaign, tid, 0),
                     runner.named_writable_roots(os.path.join(pair, "run")),
                     os.path.join(campaign.trials, tid, "harness")))
        # 8. probe-env
        base = runner.probe_dir(campaign, setup.name, "available")
        rows.append(("probe-env", os.path.join(campaign.root, "probes", "workspace"),
                     os.path.join(campaign.root, "probes", "workspace"),
                     runner.probe_scratch(base), [],
                     os.path.join(base, "20260919T000000Z")))
        # 9. the write-fence proof's live mode
        base = os.path.join(campaign.tmp, "write-fence", setup.name)
        rows.append(("write-fence", os.path.join(base, "workspace"),
                     os.path.join(base, "run"), runner.probe_scratch(base),
                     runner.named_writable_roots(os.path.join(base, "run")),
                     os.path.join(campaign.trials, "fence-%s-x" % setup.name, "harness")))
        # 10. the native read-boundary probe
        base = os.path.join(campaign.tmp, "native-read-boundary", setup.name)
        rows.append(("native-read-boundary", os.path.join(base, "workspace"),
                     os.path.join(base, "run"), runner.probe_scratch(base),
                     runner.named_writable_roots(os.path.join(base, "run")),
                     os.path.join(campaign.records("native-read-boundary"), setup.name,
                                  "harness-20260919T000000Z")))
        return rows

    def inside(self, rows, path):
        """Is `path` inside one of these roots, in EITHER spelling?

        The writer emits every root in its given AND its resolved form, because `/var` is
        `/private/var` and `/tmp` is `/private/tmp` on this Mac. The relocated test pilot root
        lives under `/var/folders/...`, so a comparison on one spelling alone reports a root
        that is in the profile as missing from it.
        """
        hits = []
        for row in rows:
            for root in (row["path"], os.path.realpath(row["path"])):
                for candidate in (os.path.abspath(path), os.path.realpath(path)):
                    if runner.path_contains(root, candidate):
                        hits.append(row["path"])
                        break
                else:
                    continue
                break
        return hits

    def test_every_launch_kind(self):
        for name in ("claude-code", "codex", "opencode"):
            campaign, setup = self.campaign_and_setup(name)
            for kind, workspace, run_dir, scratch, roots, out_dir in self.kinds(campaign,
                                                                                setup):
                spec = runner.wall_spec(campaign, setup, "available", out_dir,
                                        workspace=workspace, run_dir=run_dir,
                                        scratch=scratch, roots=roots, proxy_port=1)
                writes = spec["write_roots"]
                reads = spec["read_roots"] + writes
                label = "%s / %s" % (name, kind)
                # TMPDIR itself
                self.assertTrue(self.inside(writes, scratch),
                                "%s: TMPDIR %s is in no write root" % (label, scratch))
                # `${TMPDIR}/runs`, which setups/claude-code/launch.sh makes on every launch
                self.assertTrue(self.inside(writes, os.path.join(scratch, "runs")),
                                "%s: ${TMPDIR}/runs is in no write root" % label)
                # the run directory
                self.assertTrue(self.inside(writes, run_dir),
                                "%s: the run directory is in no write root" % label)
                # the adapters' run root, `<opaque tree>/runs`
                tree = os.path.dirname(os.path.realpath(scratch))
                self.assertTrue(self.inside(writes, os.path.join(tree, "runs")),
                                "%s: the adapters' run root is in no write root" % label)
                # the named cwd, readable
                self.assertTrue(self.inside(reads, spec["cwd"]),
                                "%s: the named cwd %s is in no read root"
                                % (label, spec["cwd"]))
                self.assertEqual(spec["cwd"], os.path.realpath(workspace))
                # send-back 5: the offline uv cache, on every kind of every setup.
                uv = spec["uv"]
                self.assertEqual(uv["UV_OFFLINE"], "1", label)
                self.assertEqual(os.path.realpath(uv["UV_CACHE_DIR"]),
                                 os.path.realpath(setup.uv_cache("available")), label)
                self.assertTrue(self.inside(writes, uv["UV_CACHE_DIR"]),
                                "%s: UV_CACHE_DIR is in no write root" % label)
                self.assertTrue(runner.path_contains(setup.home("available"),
                                                     uv["UV_CACHE_DIR"]),
                                "%s: UV_CACHE_DIR is outside this condition's home" % label)
                # the two names ride with the WALL, not with launch_env: they exist because
                # the wall closes the network, and an unwalled launch has no warmed cache.
                self.assertNotIn("UV_CACHE_DIR", setup.launch_env("available"), label)
                self.assertNotIn("UV_OFFLINE", setup.launch_env("available"), label)
                self.assertEqual(setup.uv_env("available"), uv, label)
                # send-back 2: Claude Code's own scratch pointer, on every claude-code kind
                # and on no other harness's.
                pointers = spec["harness_tmpdirs"]
                if name == "claude-code":
                    self.assertEqual(sorted(pointers), ["CLAUDE_CODE_TMPDIR"], label)
                    cc_tmp = pointers["CLAUDE_CODE_TMPDIR"]
                    self.assertEqual(os.path.realpath(cc_tmp),
                                     os.path.realpath(os.path.join(scratch, "cc-tmp")), label)
                    self.assertTrue(os.path.isdir(cc_tmp),
                                    "%s: CLAUDE_CODE_TMPDIR was not created before the launch"
                                    % label)
                    self.assertTrue(self.inside(writes, cc_tmp),
                                    "%s: CLAUDE_CODE_TMPDIR is in no write root" % label)
                    self.assertFalse(
                        runner.path_contains("/private/tmp", os.path.realpath(cc_tmp))
                        and not self.inside(writes, cc_tmp),
                        "%s: CLAUDE_CODE_TMPDIR is under the shared /tmp" % label)
                else:
                    self.assertEqual(pointers, {}, label)
                # and Codex's own two, which its launcher always adds
                if name == "codex":
                    child = os.path.join(setup.home("available"), "child")
                    self.assertTrue(self.inside(writes, child),
                                    "%s: $CODEX_HOME/child is in no write root" % label)
                    self.assertTrue(self.inside(writes, os.path.join(child, "uv-cache")),
                                    "%s: the uv cache is in no write root" % label)

    def test_the_campaigns_shared_tmp_is_never_a_launchs_TMPDIR(self):
        """The fault itself: `<campaign>/tmp` is a REFUSED root, so a launch handed it as
        TMPDIR cannot make `${TMPDIR}/runs`."""
        campaign, setup = self.campaign_and_setup()
        for _kind, workspace, run_dir, scratch, roots, out_dir in self.kinds(campaign, setup):
            self.assertNotEqual(os.path.realpath(scratch), os.path.realpath(campaign.tmp))
        spec = runner.wall_spec(campaign, setup, "available",
                                os.path.join(campaign.trials, "t", "harness"),
                                workspace=os.path.join(self.scratch, "ws"),
                                scratch=os.path.join(self.scratch, "tree", "scratch"))
        self.assertIn(os.path.realpath(campaign.tmp),
                      [r["path"] for r in spec["refused_roots"]])


class ClaudeCodeTmpdirTest(RunnerCase):
    """Send-back 2: `/tmp/claude-<uid>` is shared by every Claude session on this Mac, so it
    can never be a root of one trial's profile; `CLAUDE_CODE_TMPDIR` moves that scratch inside
    the trial's own TMPDIR."""

    def the_setups(self):
        campaign = runner.Campaign(self.campaign)
        return campaign, {
            "claude-code": runner.ClaudeCodeSetup(campaign, stage=self.stage),
            "codex": runner.CodexSetup(campaign, stage=self.stage),
            "opencode": runner.OpenCodeSetup(campaign, stage=self.stage, name="opencode"),
        }

    def test_the_name_is_declared_and_carries_its_reason(self):
        self.assertIn("CLAUDE_CODE_TMPDIR", runner.DECLARED_ENV)
        self.assertIn("shared", runner.DECLARED_ENV["CLAUDE_CODE_TMPDIR"])
        # it IS a banned shape, which is exactly why it has to be declared
        self.assertTrue(runner.BANNED_ENV_RE.match("CLAUDE_CODE_TMPDIR"))
        # and `run_cmd` therefore lets it through rather than refusing the child
        built = runner.Campaign(self.campaign).env(
            extra={"CLAUDE_CODE_TMPDIR": "/x"}, require_binaries=False)
        self.assertEqual([n for n in runner.banned_names(built)
                          if n not in runner.DECLARED_ENV], [])

    def test_only_claude_code_gets_it_and_it_is_created(self):
        campaign, setups = self.the_setups()
        tmpdir = os.path.join(self.scratch, "a-launchs-own-tmpdir")
        runner.ensure_dir(tmpdir)
        self.assertEqual(setups["codex"].scratch_env(tmpdir), {})
        self.assertEqual(setups["opencode"].scratch_env(tmpdir), {})
        got = setups["claude-code"].scratch_env(tmpdir)
        self.assertEqual(sorted(got), ["CLAUDE_CODE_TMPDIR"])
        self.assertEqual(got["CLAUDE_CODE_TMPDIR"], os.path.join(tmpdir, "cc-tmp"))
        self.assertTrue(os.path.isdir(got["CLAUDE_CODE_TMPDIR"]))
        # never the shared folder the live proof died on
        self.assertNotEqual(os.path.realpath(got["CLAUDE_CODE_TMPDIR"]),
                            os.path.realpath("/tmp/claude-%d" % os.getuid()))

    def test_a_real_claude_code_launch_carries_it_and_the_record_says_so(self):
        """Through the fake launcher, which records the names its environment held."""
        tid, got = self.run_trial()
        self.assertEqual(got.returncode, 0, got.stderr)
        names = runner.read_json(os.path.join(self.campaign, "trials", tid, "harness",
                                              "env-names.json"))["names"]
        self.assertIn("CLAUDE_CODE_TMPDIR", names)
        command = runner.read_json(os.path.join(self.campaign, "trials", tid, "command.json"))
        self.assertIn("CLAUDE_CODE_TMPDIR", command["allowlisted_env_names"])
        self.assertIn("CLAUDE_CODE_TMPDIR", command["launcher_env_names"])
        # and it points inside this trial's own scratch, which the runner made before the
        # launch. (The record cannot be searched for the literal `/tmp/claude-<uid>`: this
        # suite's own scratch root legitimately contains that string.)
        scratch = runner.trial_scratch(runner.Campaign(self.campaign), tid, 0)
        self.assertTrue(os.path.isdir(os.path.join(scratch, "cc-tmp")))
        self.assertTrue(runner.path_contains(command["opaque_tree"],
                                             os.path.join(scratch, "cc-tmp")))


@unittest.skipUnless(os.path.isfile(SANDBOX_EXEC), "this machine has no sandbox-exec")
@unittest.skipUnless(runner.which("uv"), "this machine has no uv")
class OfflineUvCacheTest(RunnerCase):
    """Send-back 5, blocker 1: the core runs behind the wall because `install` warmed a cache.

    No network and no model. The fixture script declares an EMPTY dependency set, so warming
    it needs no index: what is tested is the mechanism (a per-home cache, `UV_OFFLINE=1` at
    launch, the wall profile in between), not pypi.
    """

    # Built line by line rather than as one triple-quoted block, so this file's own quoting
    # stays boring.
    TINY = "\n".join([
        "#!/usr/bin/env python3",
        "# /// script",
        '# requires-python = ">=3.9"',
        "# dependencies = []",
        "# ///",
        "import argparse",
        'parser = argparse.ArgumentParser(description="a fixture script this test wrote")',
        "parser.parse_args()",
        'print("the staged core ran")',
        "",
    ])

    def tiny_stage(self, recheck=None):
        """A stage holding PEP 723 scripts, named the way the real ones are."""
        scripts = os.path.join(self.stage, "plugins", "recheck-v2", "skills", "recheck-v2",
                               "scripts")
        runner.ensure_dir(scripts)
        for name, body in (("recheck.py", recheck or self.TINY),
                           ("validate-result.py", self.TINY)):
            path = os.path.join(scripts, name)
            runner.write_text(path, body)
            # the real stage is copied with `copy2`, which keeps the executable bit; uv spawns
            # the script by its shebang, so a 0644 copy fails with `Permission denied`
            os.chmod(path, 0o755)
        return scripts

    def setup_object(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        runner.ensure_dir(setup.home("available"))
        return campaign, setup

    def test_pep723_scripts_finds_the_real_plugins_three_declared_scripts(self):
        """Against the CHECKOUT, so the enumeration is checked against what really ships."""
        rows = runner.pep723_scripts(os.path.dirname(os.path.dirname(runner.PLUGIN_DIR)))
        names = sorted(os.path.basename(r["script"]) for r in rows)
        self.assertEqual(names, ["recheck.py", "validate-examples.py", "validate-result.py"])
        for row in rows:
            self.assertIn('dependencies = ["jsonschema==4.25.1"]', row["declares"])
            self.assertIn('requires-python = ">=3.9"', row["declares"])

    def test_the_cache_is_inside_the_home_and_the_codex_lane_keeps_its_own_path(self):
        campaign = runner.Campaign(self.campaign)
        claude = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        codex = runner.CodexSetup(campaign, stage=self.stage)
        for setup in (claude, codex):
            for condition in ("available", "absent"):
                cache = setup.uv_cache(condition)
                self.assertTrue(runner.path_contains(setup.home(condition), cache),
                                (setup.name, condition))
                self.assertEqual(setup.uv_env(condition)["UV_OFFLINE"], "1")
                self.assertEqual(setup.uv_env(condition)["UV_CACHE_DIR"], cache)
        # E9-25: the Codex lane's cache is the one its own launcher already exports
        self.assertTrue(codex.uv_cache("available").endswith(
            os.path.join("child", "uv-cache")))
        # apparatus, not skill: both conditions get a cache of their own, built the same way
        self.assertNotEqual(claude.uv_cache("available"), claude.uv_cache("absent"))

    def test_warming_then_running_offline_behind_the_wall(self):
        campaign, setup = self.setup_object()
        self.tiny_stage()
        warm = runner.warm_uv_cache(campaign, setup, "available")
        self.assertTrue(warm["ok"], warm)
        self.assertEqual(warm["failed"], [])
        self.assertEqual(sorted(os.path.basename(p) for p in warm["scripts"]),
                         ["recheck.py", "validate-result.py"])
        # both interpreter passes ran, and the record says which
        self.assertEqual(sorted({r["pass"] for r in warm["passes"]}),
                         ["default", "only-system"])
        # the hash listing
        self.assertTrue(warm["listing"]["present"])
        self.assertGreater(warm["listing"]["files"], 0)
        self.assertEqual(len(warm["listing"]["tree_sha256"]), 64)
        self.assertTrue(runner.path_contains(setup.home("available"), warm["cache"]))

        # ...and now offline, behind this home's own profile, in a plain child
        check = runner.uv_offline_check(campaign, setup, "available")
        self.assertTrue(check["ok"], check)
        self.assertEqual(check["exit"], 0)
        self.assertIn("UV_OFFLINE", check["env_names"])
        self.assertIn("UV_CACHE_DIR", check["env_names"])
        self.assertTrue(os.path.isfile(check["profile"]))

    def test_an_unwarmed_cache_fails_the_offline_check_rather_than_passing_quietly(self):
        """The control: the check is not passing because it cannot fail."""
        campaign, setup = self.setup_object()
        self.tiny_stage(recheck=self.TINY.replace(
            "# dependencies = []",
            '# dependencies = ["a-package-this-bench-will-never-have==9.9.9"]'))
        runner.ensure_dir(setup.uv_cache("available"))
        check = runner.uv_offline_check(campaign, setup, "available")
        self.assertFalse(check["ok"], check)
        self.assertNotEqual(check["exit"], 0)

    def test_verify_carries_the_offline_check_and_never_changes_its_own_exit(self):
        campaign, setup = self.setup_object()
        self.tiny_stage()
        runner.ensure_dir(setup.uv_cache("available"))
        step = runner.with_uv_offline_check(campaign, setup, "available",
                                            {"exit": 0, "label": "verify-install.sh"})
        self.assertIn("uv_offline", step)
        self.assertEqual(step["exit"], 0)
        if not step["uv_offline"]["ok"]:
            self.assertIn("missing dependency", step["uv_offline_problem"])


@unittest.skipUnless(os.path.isfile(SANDBOX_EXEC), "this machine has no sandbox-exec")
@unittest.skipUnless(runner.which("uv"), "this machine has no uv")
class VerifyRecordsTheOfflineUvCheckTest(RunnerCase):
    """Send-back 6: a passing check that is not recorded is a failing check that will be
    invisible.

    `with_uv_offline_check` attached `uv_offline` to the verify STEP and `do_verify` built its
    rows from named fields, so on the real root the block ran, wrote its profiles under
    `records/uv-offline-check/`, and appeared in neither verify's stdout nor its record file:
    grep count zero for `uv_offline` in all eight records while the check was passing.

    No model anywhere. The homes here are ones the test builds; `verify-install.sh` is a stub.
    """

    TINY = "\n".join([
        "#!/usr/bin/env python3",
        "# /// script",
        '# requires-python = ">=3.9"',
        "# dependencies = []",
        "# ///",
        "import argparse",
        "argparse.ArgumentParser().parse_args()",
        'print("the staged core ran")',
        "",
    ])

    def stage_the_core(self, stage=None, unobtainable=False):
        """The staged core. `unobtainable=True` gives it a dependency no warm pass can
        resolve, which is the honest stand-in for the live blocker: an EMPTY dependency set
        runs offline from a cold cache, so an empty cache alone proves nothing."""
        scripts = os.path.join(stage or self.stage, "plugins", "recheck-v2", "skills",
                               "recheck-v2", "scripts")
        runner.ensure_dir(scripts)
        path = os.path.join(scripts, "recheck.py")
        body = self.TINY
        if unobtainable:
            body = body.replace(
                "# dependencies = []",
                '# dependencies = ["a-package-this-bench-will-never-have==9.9.9"]')
        runner.write_text(path, body)
        os.chmod(path, 0o755)
        return path

    def canonical_digest(self, campaign):
        """`do_verify` compares the installed digest with the CHECKOUT's own, so the stub has
        to print that one; anything else fails the row for a reason this test is not about."""
        identity = runner.fresh_skill_identity(campaign)
        self.assertTrue(identity["ok"], identity)
        return identity["content_sha256"]

    def stub_launcher(self, setup):
        """`require_wall` asks the setup which executable a launch selects, so the file has to
        be in the stage; it is never run."""
        path = os.path.join(setup.setup_dir, "launch.sh")
        if not os.path.isfile(path):
            runner.ensure_dir(setup.setup_dir)
            runner.write_text(path, "#!/bin/sh\nexit 0\n")
            os.chmod(path, 0o755)
        return path

    def stub_verify_install(self, setup, canonical="a-canonical-digest"):
        """A `verify-install.sh` this test wrote: it prints the shape do_verify reads."""
        runner.ensure_dir(setup.setup_dir)
        path = os.path.join(setup.setup_dir, "verify-install.sh")
        runner.write_text(path, "#!/bin/sh\ncat <<'JSON'\n" + json.dumps(
            {"ok": True, "skill_identity": {"installed": {"content_sha256": canonical}}},
            indent=1) + "\nJSON\n")
        os.chmod(path, 0o755)
        return path

    def seal(self, sealed=True):
        campaign = runner.Campaign(self.campaign)
        document = runner.read_json(campaign.campaign_json)
        document["sealed"] = sealed
        # `require_wall` refuses sealed+synthetic before it reaches anything else, and every
        # test campaign is synthetic by default. The launch gate under test here is the one a
        # REAL sealed campaign meets, so this one stops saying it is synthetic. No launch
        # happens in this class; only the gate is called.
        document["synthetic"] = False
        runner.write_json(campaign.campaign_json, document)
        if os.path.exists(campaign.synthetic_marker):
            os.unlink(campaign.synthetic_marker)
        return campaign

    def setUpHome(self, campaign, warm=True):
        # `do_verify` builds its own setups from `campaign.stage`, so the stub launcher and the
        # staged core go THERE; the object this test keeps is built the same way.
        setup = runner.ClaudeCodeSetup(campaign, stage=campaign.stage)
        runner.ensure_dir(setup.home("available"))
        self.stub_verify_install(setup, canonical=self.canonical_digest(campaign))
        self.stub_launcher(setup)
        self.stage_the_core(campaign.stage, unobtainable=not warm)
        if warm:
            record = runner.warm_uv_cache(campaign, setup, "available")
            self.assertTrue(record["ok"], record)
        else:
            runner.ensure_dir(setup.uv_cache("available"))
        return setup

    def verify_args(self, **extra):
        base = dict(campaign=self.campaign, setup=["claude-code"], home="available")
        base.update(extra)
        return argparse.Namespace(**base)

    def test_the_row_carries_the_whole_block_in_stdout_and_in_the_record(self):
        campaign = self.seal(sealed=False)
        self.setUpHome(campaign)
        document = runner.do_verify(self.verify_args())
        row = document["rows"][0]
        self.assertIn("uv_offline", row)
        self.assertTrue(row["uv_offline_ok"], row["uv_offline"])
        self.assertEqual(row["uv_offline"]["exit"], 0)
        self.assertIn("UV_OFFLINE", row["uv_offline"]["env_names"])
        self.assertTrue(os.path.isfile(row["uv_offline"]["profile"]))
        # ...and the same thing on disk, which is where it was missing
        records = sorted(glob.glob(os.path.join(campaign.root, "records", "verify*.json")))
        self.assertTrue(records)
        blob = runner.read_text(records[-1], "")
        self.assertIn("uv_offline", blob)
        on_disk = runner.read_json(records[-1])["rows"][0]
        self.assertEqual(on_disk["uv_offline_ok"], row["uv_offline_ok"])
        self.assertEqual(on_disk["uv_offline"]["profile"], row["uv_offline"]["profile"])

    def test_an_unsealed_plan_records_it_and_never_gates(self):
        campaign = self.seal(sealed=False)
        self.setUpHome(campaign, warm=False)          # an EMPTY cache
        document = runner.do_verify(self.verify_args())
        self.assertFalse(document["rows"][0]["uv_offline_ok"])
        self.assertTrue(document["uv_offline_failed"])
        self.assertFalse(document["sealed"])
        self.assertNotIn(runner.FAIL_EXIT_KEY, document)
        self.assertIn("never gates", document["uv_offline_gate"])

    def test_a_sealed_plan_with_an_empty_cache_FAILS_verify_on_stdout(self):
        campaign = self.seal()
        self.setUpHome(campaign, warm=False)
        document = runner.do_verify(self.verify_args())
        self.assertTrue(document["sealed"])
        self.assertFalse(document["rows"][0]["uv_offline_ok"])
        self.assertIn(runner.FAIL_EXIT_KEY, document)
        message = document[runner.FAIL_EXIT_KEY]
        self.assertIn("claude-code/available", message)
        self.assertIn("install", message)
        self.assertIn("missing dependency", message)
        # the document is still returned, so `main` prints it on stdout (A7a)
        self.assertTrue(document["rows"])

    def test_a_sealed_plan_with_a_warm_cache_passes(self):
        campaign = self.seal()
        self.setUpHome(campaign, warm=True)
        document = runner.do_verify(self.verify_args())
        self.assertTrue(document["rows"][0]["uv_offline_ok"])
        self.assertEqual(document["uv_offline_failed"], [])
        self.assertNotIn(runner.FAIL_EXIT_KEY, document)

    def test_the_launch_gate_refuses_a_home_with_no_passing_check(self):
        campaign = self.seal()
        setup = self.setUpHome(campaign, warm=False)
        runner.do_verify(self.verify_args())
        with self.assertRaises(runner.Usage) as caught:
            runner.require_wall(campaign, setup, setup.script("launch.sh"), "a trial",
                                condition="available")
        message = str(caught.exception)
        self.assertIn("claude-code/available", message)
        self.assertIn("install", message)
        self.assertIn("--home available", message)

    def test_the_launch_gate_refuses_a_home_no_verify_record_names(self):
        campaign = self.seal()
        setup = self.setUpHome(campaign, warm=True)
        with self.assertRaises(runner.Usage) as caught:
            runner.require_wall(campaign, setup, setup.script("launch.sh"), "a trial",
                                condition="routing")
        self.assertIn("no verify record", str(caught.exception))

    def test_the_launch_gate_lets_a_verified_home_through(self):
        campaign = self.seal()
        setup = self.setUpHome(campaign, warm=True)
        runner.do_verify(self.verify_args())
        record = runner.require_wall(campaign, setup, setup.script("launch.sh"), "a trial",
                                     condition="available")
        self.assertTrue(record["required"])
        self.assertTrue(record["uv_offline"]["ok"])

    def test_an_unsealed_campaign_is_never_gated_by_it(self):
        campaign = self.seal(sealed=False)
        setup = self.setUpHome(campaign, warm=False)
        runner.do_verify(self.verify_args())
        record = runner.require_wall(campaign, setup, setup.script("launch.sh"), "a trial",
                                     condition="available")
        self.assertFalse(record["required"])

    def test_installs_record_file_carries_the_warm_passes_and_the_tree_hash(self):
        """Item 4: confirmed on the RECORD, not only on stdout."""
        campaign = self.seal(sealed=False)
        setup = self.setUpHome(campaign, warm=False)
        warm = runner.warm_uv_cache(campaign, setup, "available")
        path = campaign.reserve_record("install")
        runner.write_json(path, {"campaign": campaign.root,
                                 "installs": [{"setup": setup.name, "condition": "available",
                                               "uv_cache": warm}]})
        on_disk = runner.read_json(path)["installs"][0]["uv_cache"]
        self.assertEqual(sorted({r["pass"] for r in on_disk["passes"]}),
                         ["default", "only-system"])
        self.assertEqual(len(on_disk["listing"]["tree_sha256"]), 64)
        self.assertIn("recheck.py", " ".join(on_disk["scripts"]))
        self.assertTrue(on_disk["dependency_sets"])


class TheAvailableHomeContainsTheOtherTwoTest(RunnerCase):
    """The claude-code `available` home IS `<pilot>/claude-code`, a WRITE root that CONTAINS
    `absent` and `routing`. The profile must re-deny both, for READ and for WRITE, after that
    allow: the last matching rule wins, so the order is the whole proof."""

    def profile_text(self):
        campaign = runner.Campaign(self.campaign)
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        runner.ensure_dir(setup.home("available"))
        tid = "claude-code-F1-01-fixed-clean-available-r1"
        tree = campaign.opaque_tree(tid, 0)
        case = os.path.join(tree, "fixture", "abc123def456")
        spec = runner.wall_spec(
            campaign, setup, "available",
            os.path.join(campaign.trials, tid, "harness"),
            workspace=os.path.join(case, "workspace"),
            run_dir=os.path.join(case, "run"),
            scratch=runner.trial_scratch(campaign, tid, 0),
            roots=[case], proxy_port=1)
        text, _summary = writer.build(spec)
        return setup, text, writer.build_rules(spec)["rules"]

    def test_available_is_the_home_directory_itself(self):
        setup = runner.ClaudeCodeSetup(runner.Campaign(self.campaign), stage=self.stage)
        self.assertEqual(setup.home("available"),
                         os.path.join(runner.PILOT_ROOT, "claude-code"))
        for other in ("absent", "routing"):
            self.assertTrue(runner.path_contains(setup.home("available"),
                                                 setup.home(other)), other)

    def test_the_two_siblings_are_re_denied_after_the_allow_for_both_operations(self):
        setup, text, rules = self.profile_text()
        home = os.path.realpath(setup.home("available"))
        allow_line = [i for i, line in enumerate(text.splitlines())
                      if line.startswith("(allow file-read* file-write*")
                      and '(subpath "%s")' % home in line]
        self.assertEqual(len(allow_line), 1, "the home is allowed exactly once:\n%s" % text)
        for other in ("absent", "routing"):
            path = os.path.realpath(setup.home(other))
            deny_line = [i for i, line in enumerate(text.splitlines())
                         if line.startswith("(deny file-read* file-write*")
                         and '(subpath "%s")' % path in line]
            self.assertEqual(len(deny_line), 1,
                             "%s is re-denied exactly once:\n%s" % (other, text))
            self.assertGreater(deny_line[0], allow_line[0],
                               "%s is denied BEFORE the home is allowed, so the allow wins"
                               % other)
            # and the kernel's own rule, evaluated: deny for read AND for write
            for operation in ("file-read-data", "file-read-metadata", "file-write-data",
                              "file-write-create", "file-write-mode"):
                self.assertEqual(writer.evaluate(rules, path, operation), "deny",
                                 "%s is not denied for %s" % (other, operation))
                self.assertEqual(writer.evaluate(rules, os.path.join(path, "install.json"),
                                                 operation), "deny", other)
            # while the home itself stays readable and writable
            for operation in ("file-read-data", "file-write-data"):
                self.assertEqual(writer.evaluate(rules, os.path.join(home, "config"),
                                                 operation), "allow")


@unittest.skipUnless(os.path.isfile(SANDBOX_EXEC), "this machine has no sandbox-exec")
class WalledReadBoundaryProbeTest(RunnerCase):
    """Send-back 3: on a SEALED plan the read-boundary probe measures the WALL, not the disk.

    The bare child used to run outside every profile, so it read everything a plain process
    can read, failed the preflight of a bench whose sessions are confined, and
    `require_preflight` then refused every trial of a sealed campaign. No model anywhere: the
    probe is a plain `python3 -c`.
    """

    def seal(self):
        campaign = runner.Campaign(self.campaign)
        document = runner.read_json(campaign.campaign_json)
        document["sealed"] = True
        runner.write_json(campaign.campaign_json, document)
        # the other condition's home has to exist, or "could not list it" is not a refusal
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        runner.ensure_dir(setup.home("available"))
        runner.write_text(os.path.join(setup.home("absent"), "install.json"), "{}\n")
        return campaign

    def test_the_walled_child_is_separated_and_the_bare_one_is_not(self):
        campaign = self.seal()
        document = runner.read_boundary_probe(campaign, campaign.plan())
        self.assertTrue(document["walled"])
        row = document["rows"][0]
        self.assertTrue(row["walled"])
        self.assertTrue(row["probe_ran"], row)
        # the wall refused all three
        self.assertFalse(row["read_the_other_trials_sentinel"], row)
        self.assertEqual(row["discovered_other_trial_trees"], [], row)
        self.assertFalse(row["read_the_other_conditions_install"], row)
        self.assertTrue(row["separated"])
        self.assertTrue(document["separated"])
        # and the filesystem underneath still allows every one of them, recorded as a fact
        fact = row["unwalled_filesystem_fact"]
        self.assertTrue(fact["probe_ran"], fact)
        self.assertTrue(fact["read_the_other_trials_sentinel"], fact)
        self.assertFalse(fact["separated"])
        # the profile the child ran behind is retained and hashed
        self.assertTrue(os.path.isfile(row["wall"]["profile"]))
        self.assertEqual(len(row["wall"]["profile_sha256"]), 64)
        self.assertTrue(runner.path_contains(campaign.opaque_tree(
            runner.trial_id("claude-code", "read-boundary-probe-a", "available", 1), 0),
            row["wall"]["cwd"]))
        # and it is NOT under trials/ (A4's reason, kept)
        self.assertFalse(runner.path_contains(campaign.trials, row["wall"]["profile"]))

    def test_a_profile_that_ALLOWS_the_sentinel_fails_the_probe(self):
        """The control: the probe is not passing because the child is broken."""
        campaign = self.seal()
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        mine = runner.trial_id("claude-code", "read-boundary-probe-a", "available", 1)
        theirs = runner.trial_id("claude-code", "read-boundary-probe-b", "available", 1)
        my_scratch = runner.trial_scratch(campaign, mine, 0)
        their_tree = campaign.opaque_tree(theirs, 0)
        runner.ensure_dir(their_tree)
        sentinel = os.path.join(their_tree, "sentinel.txt")
        runner.write_text(sentinel, runner.READ_BOUNDARY_SENTINEL)
        # the same spec, with the other trial's tree deliberately ALLOWED
        wall = runner.read_boundary_wall(campaign, setup, mine, my_scratch)
        spec = runner.read_json(wall["spec_path"])
        spec["read_roots"].append({"path": their_tree, "why": "deliberately reopened"})
        spec["refused_roots"] = [r for r in spec["refused_roots"]
                                 if not runner.path_contains(r["path"], their_tree)]
        leaky = os.path.join(self.scratch, "leaky.sb")
        text, _summary = writer.build(spec)
        runner.write_text(leaky, text)
        probe = runner.run_cmd(
            [SANDBOX_EXEC, "-f", leaky, sys.executable, "-c", runner.READ_BOUNDARY_SOURCE,
             sentinel, setup.home("absent")],
            env=campaign.env(extra=setup.launch_env("available"), scratch=my_scratch,
                             require_binaries=False),
            cwd=wall["cwd"], label="a deliberately leaky profile")
        answer = runner._read_boundary_answer(probe)
        self.assertTrue(answer["probe_ran"], answer)
        self.assertTrue(answer["read_the_other_trials_sentinel"], answer)
        self.assertFalse(runner._read_boundary_separated(answer))

    def test_a_probe_that_could_not_run_is_never_separated(self):
        """A child that answers nothing is not a child that passed."""
        self.assertFalse(runner._read_boundary_separated(
            runner._read_boundary_answer({"stdout": "", "stderr": "boom", "exit": 71})))

    def test_an_UNSEALED_plan_keeps_the_old_reading_and_the_old_refusal(self):
        campaign = runner.Campaign(self.campaign)
        document = runner.read_boundary_probe(campaign, campaign.plan())
        self.assertFalse(document["walled"])
        row = document["rows"][0]
        self.assertFalse(row["walled"])
        self.assertIsNone(row.get("wall"))
        self.assertNotIn("unwalled_filesystem_fact", row)
        # the filesystem lets one plain child read another's sentinel, so it is not separated
        self.assertTrue(row["read_the_other_trials_sentinel"], row)
        self.assertFalse(document["separated"])


class PreflightPrintsItsRecordOnTheFailurePathTest(RunnerCase):
    """Send-back 3: A7a's one-JSON-document-on-stdout rule holds when the preflight REFUSES.

    On the failing live proof the record was 0 bytes and everything measured existed only in
    stderr.
    """

    def test_a_failing_preflight_prints_the_record_and_exits_non_zero(self):
        got = cli(["preflight", "--campaign", self.campaign])
        self.assertNotEqual(got.returncode, 0, got.stdout)
        document = parse_stdout(got)
        self.assertFalse(document["separated"])
        self.assertIn("claude-code", document["not_separated"])
        self.assertTrue(document["rows"][0]["read_the_other_trials_sentinel"])
        self.assertIn("read-boundary preflight failed", got.stderr)
        self.assertIn("read-boundary preflight failed",
                      document[runner.FAIL_EXIT_KEY])
        # and the same document is on disk
        self.assertTrue(os.path.isfile(document["record"]))
        on_disk = runner.read_json(document["record"])
        self.assertEqual(on_disk["separated"], document["separated"])

    def test_a_passing_preflight_still_prints_it_and_exits_zero(self):
        got = cli(["preflight", "--campaign", self.campaign, "--accept-unseparated"])
        self.assertEqual(got.returncode, 0, got.stderr[-600:])
        document = parse_stdout(got)
        self.assertTrue(document["accepted_unseparated"])
        self.assertNotIn(runner.FAIL_EXIT_KEY, document)


class SealedCampaignTest(RunnerCase):
    """A4: a sealed plan gives up `--accept-unseparated` and a recorded ruling, and refuses a
    real launch it cannot wall."""

    preflight_accepted = True

    def seal(self):
        campaign = runner.Campaign(self.campaign)
        document = runner.read_json(campaign.campaign_json)
        document["sealed"] = True
        runner.write_json(campaign.campaign_json, document)
        return campaign

    def test_validate_plan_accepts_sealed_and_refuses_a_non_boolean(self):
        plan = runner.default_plan("x")
        plan["sealed"] = True
        self.assertIs(runner.validate_plan(plan)["sealed"], True)
        plan["sealed"] = "yes"
        with self.assertRaises(runner.Usage) as caught:
            runner.validate_plan(plan)
        self.assertIn("`sealed` must be true or false", str(caught.exception))

    def test_a_sealed_campaign_refuses_an_accepted_unseparated_bench(self):
        campaign = self.seal()
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "a launch")
        self.assertIn("nothing left for an acceptance to cover", str(caught.exception))

    def test_a_sealed_campaign_refuses_a_recorded_ruling(self):
        campaign = self.seal()
        runner.write_json(
            os.path.join(campaign.records("read-boundary"), "preflight-ruled.json"),
            {"separated": False, "accepted_unseparated": False,
             "allow_rules": {"ok": True}, "rows": [],
             "ruling": {"id": "E11-40", "text": "the words", "recorded_at": runner.now_iso(),
                        "overrides": {"per_setup": {"claude-code": {"separated": False}}}}})
        with self.assertRaises(runner.Usage) as caught:
            runner.require_preflight(campaign, "a launch")
        self.assertIn("`sealed: true`", str(caught.exception))

    def test_a_sealed_and_synthetic_campaign_refuses_a_real_launch(self):
        campaign = self.seal()
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        runner.write_text(os.path.join(setup.setup_dir, "launch.sh"), "#!/bin/sh\nexit 0\n")
        with self.assertRaises(runner.Usage) as caught:
            runner.require_wall(campaign, setup, setup.script("launch.sh"), "a trial")
        self.assertIn("cannot both be true", str(caught.exception))

    def test_a_fake_launcher_is_exempt_from_the_sealed_gate(self):
        campaign = self.seal()
        setup = runner.ClaudeCodeSetup(campaign, stage=self.stage)
        record = runner.require_wall(campaign, setup, self.fake_launcher("claude-code"),
                                     "a trial")
        self.assertFalse(record["required"])


if __name__ == "__main__":
    unittest.main()
