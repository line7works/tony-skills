"""The setup scripts, exercised with a stand-in `opencode` that calls no model.

Astra finding 14: `launch.sh` watched for the appearance of `rc.txt` rather than its own
child, so a reused output directory disabled the timeout entirely (a three-second child under
`RECHECK_OPENCODE_TIMEOUT=1` returned exit 0 after 3.28 s), and its `pkill -f` pattern could
reach another launch. These tests hold the rewrite to: a used output directory is refused; the
timeout fires on this launch's own child; and a process whose command line matches the old
`pkill` pattern survives.

Ruling E9-38 adds two more: the launcher requires the setup's own auth store rather than the
`OPENROUTER_API_KEY` variable, and it removes that variable from the harness process's
environment, so no tool shell the session opens can carry the provider key and an executor's
own `env` probe cannot print it into the harness's records.

Ruling E9-41 adds two more: the timeout loop collects a child's own exit status before it
marks a timeout (a child that ran 0.2 s under a one-second limit was recorded as 124), and the
secret scanner exempts only the CONFIGURED setup's own auth store by resolved path, so a
capture that merely carries the name `opencode/auth.json` is scanned like any other file.

`sh -n` over every setup script is the hermetic syntax gate of E9 section 9.1.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testlib  # noqa: E402

SETUPS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(testlib.ADAPTER)))), "setups", "opencode")
SCRIPTS = ("install.sh", "launch.sh", "verify-install.sh", "negative-tests.sh",
           "scan-secrets.sh")
MODEL = "openrouter/qwen/qwen3.8-flash"


class Syntax(unittest.TestCase):
    def test_every_setup_script_parses(self):
        for name in SCRIPTS:
            path = os.path.join(SETUPS, name)
            self.assertTrue(os.path.isfile(path), path)
            proc = subprocess.Popen(["sh", "-n", path], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            _out, err = proc.communicate()
            self.assertEqual(proc.returncode, 0,
                             "%s: %s" % (name, err.decode("utf-8", "replace")))


class Launch(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.setup = testlib.make_setup(self.root, testlib.load_record(), binary=True)
        self.binary = os.path.join(self.setup, "npm", "node_modules", ".bin", "opencode")
        self.workspace = os.path.join(self.root, "ws")
        os.makedirs(self.workspace)
        self.prompt = os.path.join(self.root, "prompt.txt")
        with open(self.prompt, "w", encoding="utf-8") as handle:
            handle.write("say something\n")
        # ruling E9-38: the launcher's precondition is the setup's own auth store
        self.auth = os.path.join(self.setup, "xdg-data", "opencode", "auth.json")
        if not os.path.isdir(os.path.dirname(self.auth)):
            os.makedirs(os.path.dirname(self.auth))
        with open(self.auth, "w", encoding="utf-8") as handle:
            json.dump({"openrouter": {"type": "api", "key": "not-a-real-key-this-is-a-test"}},
                      handle)
        os.chmod(self.auth, 0o600)
        self.decoys = []

    def tearDown(self):
        for proc in self.decoys:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:       # noqa: BLE001 - cleanup only
                pass
        testlib.cleanup(self.root)

    def launch(self, out_dir, env=None, timeout="900"):
        environment = dict(os.environ)
        environment.update({
            "RECHECK_OPENCODE_SETUP": self.setup,
            "RECHECK_OPENCODE_TIMEOUT": timeout,
            "OPENROUTER_API_KEY": "not-a-real-key-this-is-a-test",
            "TMPDIR": os.path.join(self.root, "tmp"),
        })
        if not os.path.isdir(environment["TMPDIR"]):
            os.makedirs(environment["TMPDIR"])
        if env:
            environment.update(env)
        proc = subprocess.Popen(
            ["sh", os.path.join(SETUPS, "launch.sh"), "qwen", self.prompt,
             self.workspace, out_dir],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
        out, err = proc.communicate()
        return (proc.returncode, out.decode("utf-8", "replace"),
                err.decode("utf-8", "replace"))

    def test_a_used_output_directory_is_refused(self):
        out_dir = os.path.join(self.root, "out")
        os.makedirs(out_dir)
        with open(os.path.join(out_dir, "rc.txt"), "w", encoding="utf-8") as handle:
            handle.write("0\n")
        code, out, err = self.launch(out_dir)
        self.assertEqual(code, 2)
        self.assertIn("spent output directory", err)
        self.assertEqual(out, "")

    def test_a_missing_binary_is_exit_three(self):
        os.remove(self.binary)
        code, _out, err = self.launch(os.path.join(self.root, "out2"))
        self.assertEqual(code, 3)
        self.assertIn("no opencode binary", err)

    def test_a_clean_launch_records_its_own_child_and_its_exit(self):
        out_dir = os.path.join(self.root, "out3")
        trace = os.path.join(self.root, "canned-trace.json")
        with open(trace, "w", encoding="utf-8") as handle:
            handle.write('{"type":"step_start","sessionID":"ses_x"}\n')
        code, out, err = self.launch(
            out_dir, env={"RECHECK_STANDIN_TRACE": trace, "RECHECK_STANDIN_RC": "0"})
        self.assertEqual(code, 0, err)
        with open(os.path.join(out_dir, "rc.txt"), encoding="utf-8") as handle:
            self.assertEqual(handle.read().strip(), "0")
        with open(os.path.join(out_dir, "child.pid"), encoding="utf-8") as handle:
            self.assertTrue(handle.read().strip().isdigit())
        self.assertIn("pid=", out)

    def test_the_timeout_fires_on_this_launchs_own_child(self):
        out_dir = os.path.join(self.root, "out4")
        started = time.time()
        code, _out, err = self.launch(
            out_dir, env={"RECHECK_STANDIN_SLEEP": "30"}, timeout="1")
        elapsed = time.time() - started
        self.assertEqual(code, 124, err)
        with open(os.path.join(out_dir, "rc.txt"), encoding="utf-8") as handle:
            self.assertEqual(handle.read().strip(), "124")
        self.assertLess(elapsed, 20, "the timeout did not fire promptly")

    def test_the_launcher_refuses_when_the_auth_store_is_absent(self):
        """Ruling E9-38: the auth store is the precondition, not the variable."""
        os.remove(self.auth)
        code, out, err = self.launch(os.path.join(self.root, "out-noauth"))
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("no auth store at", err)
        self.assertIn("install.sh", err)

    def test_the_child_does_not_inherit_the_provider_key(self):
        """Ruling E9-38: set in the parent, absent from the harness process's environment."""
        out_dir = os.path.join(self.root, "out-env")
        names = os.path.join(self.root, "child-env-names.txt")
        trace = os.path.join(self.root, "env-trace.json")
        with open(trace, "w", encoding="utf-8") as handle:
            handle.write('{"type":"step_start","sessionID":"ses_x"}\n')
        code, _out, err = self.launch(
            out_dir,
            env={"RECHECK_STANDIN_ENV": names, "RECHECK_STANDIN_TRACE": trace,
                 "OPENROUTER_API_KEY": "sk-or-v1-" + "0" * 64})
        self.assertEqual(code, 0, err)
        with open(names, encoding="utf-8") as handle:
            child = [line.strip() for line in handle if line.strip()]
        self.assertIn("XDG_DATA_HOME", child, "the child's environment was not captured")
        self.assertNotIn("OPENROUTER_API_KEY", child,
                         "the harness process inherited the provider key")
        # and the launcher's own scan of its captures found nothing
        with open(os.path.join(out_dir, "secret-scan.json"), encoding="utf-8") as handle:
            self.assertTrue(json.load(handle)["ok"])

    def test_a_child_that_finishes_inside_the_limit_keeps_its_own_exit_status(self):
        """Ruling E9-41: a completed child is collected before any timeout verdict."""
        out_dir = os.path.join(self.root, "out-fast")
        trace = os.path.join(self.root, "fast-trace.json")
        with open(trace, "w", encoding="utf-8") as handle:
            handle.write('{"type":"step_start","sessionID":"ses_fast"}\n')
        started = time.time()
        code, out, err = self.launch(
            out_dir,
            env={"RECHECK_STANDIN_SLEEP": "0.2", "RECHECK_STANDIN_TRACE": trace,
                 "RECHECK_STANDIN_RC": "0"},
            timeout="1")
        elapsed = time.time() - started
        self.assertEqual(code, 0, err)
        with open(os.path.join(out_dir, "rc.txt"), encoding="utf-8") as handle:
            self.assertEqual(handle.read().strip(), "0",
                             "a child that finished in 0.2 s was recorded as a timeout")
        self.assertIn("exit=0", out)
        self.assertLess(elapsed, 20)

    def test_the_scanner_catches_a_capture_that_is_merely_named_like_an_auth_store(self):
        """Ruling E9-41: only the configured setup's own store is exempt, by resolved path.

        The planted value is SYNTHETIC: a key-shaped string of repeating hex, never a real
        credential, and the assertions below prove the scanner never prints it.
        """
        planted_dir = os.path.join(self.root, "capture", "opencode")
        os.makedirs(planted_dir)
        synthetic = "sk-or-v1-" + ("ab12cd34" * 8)
        with open(os.path.join(planted_dir, "auth.json"), "w", encoding="utf-8") as handle:
            json.dump({"openrouter": {"type": "api", "key": synthetic}}, handle)
        report = os.path.join(self.root, "scan.json")
        with open(report, "w", encoding="utf-8") as sink:
            proc = subprocess.Popen(
                ["sh", os.path.join(SETUPS, "scan-secrets.sh"), "--quiet",
                 "--setup", self.setup, os.path.join(self.root, "capture")],
                stdout=sink, stderr=subprocess.PIPE)
            _out, err = proc.communicate()
        self.assertEqual(proc.returncode, 5,
                         "a capture named opencode/auth.json was treated as the setup's store")
        with open(report, encoding="utf-8") as handle:
            body = handle.read()
        document = json.loads(body)
        self.assertFalse(document["ok"])
        self.assertTrue(document["hits"])
        planted = os.path.realpath(os.path.join(planted_dir, "auth.json"))
        self.assertNotIn(planted, document["auth_stores_skipped"],
                         "the planted capture was treated as an exempt auth store")
        # the configured setup's own store is the only thing the scan may skip
        self.assertEqual(document["auth_stores_skipped"], [os.path.realpath(self.auth)])
        for hit in document["hits"]:
            self.assertTrue(hit["file"].endswith(os.path.join("capture", "opencode", "auth.json")))
            self.assertEqual(hit["length"], 73)
        self.assertNotIn(synthetic, body, "the scanner printed the value")
        self.assertNotIn(synthetic, err.decode("utf-8", "replace"))

    def test_the_scanner_still_exempts_the_configured_setups_own_store(self):
        """The auth store install.sh writes is the one file skipped (ruling E9-38)."""
        report = os.path.join(self.root, "setup-scan.json")
        with open(report, "w", encoding="utf-8") as sink:
            proc = subprocess.Popen(
                ["sh", os.path.join(SETUPS, "scan-secrets.sh"), "--quiet",
                 "--setup", self.setup],
                stdout=sink, stderr=subprocess.DEVNULL)
            proc.communicate()
        self.assertEqual(proc.returncode, 0)
        with open(report, encoding="utf-8") as handle:
            document = json.load(handle)
        self.assertEqual(document["auth_stores_skipped"], [os.path.realpath(self.auth)])

    def test_the_timeout_leaves_another_matching_launch_alone(self):
        """The old `pkill -9 -f "<binary> run --model <model>"` could reach any launch."""
        decoy = subprocess.Popen(
            [self.binary, "run", "--model", MODEL, "--format", "json", "a decoy prompt"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=dict(os.environ, RECHECK_STANDIN_SLEEP="30"),
            preexec_fn=os.setsid)
        self.decoys.append(decoy)
        time.sleep(0.5)
        self.assertIsNone(decoy.poll(), "the decoy did not start")
        out_dir = os.path.join(self.root, "out5")
        code, _out, err = self.launch(
            out_dir, env={"RECHECK_STANDIN_SLEEP": "30"}, timeout="1")
        self.assertEqual(code, 124, err)
        time.sleep(0.5)
        self.assertIsNone(decoy.poll(),
                          "the timeout killed a process outside this launch's group")
        os.killpg(os.getpgid(decoy.pid), signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
