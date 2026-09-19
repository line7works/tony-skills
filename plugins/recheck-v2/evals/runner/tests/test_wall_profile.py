"""The wall: the profile writer, the loopback proxy, and what a plain child can reach (A5).

No model anywhere, and no harness. Every enforcement test runs a PLAIN child under
`/usr/bin/sandbox-exec` — `cat`, `python3`, a shell redirection, `cp`, `git -C`, a grandchild
through `sh -c` — and asserts what the kernel did, not what the profile says.

The name is `test_wall_profile.py` rather than `test_wall.py`: `test_wall.py` is the ANSWER
KEY's wall (the key directories at mode 000), and the two must not be confused.
"""
import importlib.util
import json
import os
import shutil
import socket
import stat
import subprocess
import tempfile
import threading
import unittest

from testlib import RunnerCase, runner

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
