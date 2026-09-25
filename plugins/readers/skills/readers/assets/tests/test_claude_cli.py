"""The Claude CLI lane (row `claude-opus-cli`, transport `claude-cli`; E14, A12).

Every test drives the runner through its shell entry (`assets/readers`) as a child process, from a
temporary directory, with a synthetic `PATH`. No test launches the real `claude`: the dispatch tests
read the canned fixtures under `fixtures/canned/claude-*` (only under `READERS_TEST=1`), and the
command-line tests put a stand-in `claude` first on `PATH` that records its argv, its stdin, its
environment keys and its working directory, then prints a result document. The last-pick memory is
pointed at an empty temporary checkout, so nothing is remembered anywhere.

Run: `cd assets && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests`.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.dirname(HERE)
sys.path.insert(0, ASSETS)
import readers  # noqa: E402  (the module, for compose() and the fixed lists only; never dispatched here)

ENTRY = os.path.join(ASSETS, "readers")
CANNED = os.path.join(ASSETS, "fixtures", "canned")
ROW = "claude-opus-cli"
BASE_COMMIT = "8d258fc"
ROSTER_REL = "plugins/readers/skills/readers/assets/roster.json"

# The stand-in `claude`: a /bin/sh front that records the environment it was given before any
# interpreter can add to it (the system python3 shim adds keys of its own), then the recorder.
STUB_SH = """#!/bin/sh
here="$(cd "$(dirname "$0")" && pwd -P)"
/usr/bin/env > "$here/last-env.txt"
exec %s "$here/stub.py" "$@"
"""
STUB = r'''import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
calls = os.path.join(here, "calls")
os.makedirs(calls, exist_ok=True)
n = len(os.listdir(calls))
stdin = sys.stdin.read()
with open(os.path.join(here, "last-env.txt")) as f:
    env_keys = sorted(line.split("=", 1)[0] for line in f.read().splitlines() if "=" in line)
with open(os.path.join(calls, "%d.json" % n), "w") as f:
    json.dump({"argv": sys.argv[1:], "stdin": stdin, "env_keys": env_keys,
               "cwd": os.getcwd(), "cwd_entries": sorted(os.listdir(os.getcwd()))}, f)
with open(os.path.join(here, "mode.json")) as f:
    mode = json.load(f)
sys.stdout.write(mode["stdout"])
sys.stderr.write(mode.get("stderr", ""))
sys.exit(mode.get("exit", 0))
'''


def ok_document():
    with open(os.path.join(CANNED, "claude-ok", "stdout.json")) as f:
        return json.load(f)


class _Lane(unittest.TestCase):

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="readers-claude-cli-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.stub_dir = os.path.join(self.tmp, "stub-bin")
        self.py_dir = os.path.join(self.tmp, "py-bin")
        os.makedirs(self.stub_dir)
        os.makedirs(self.py_dir)
        # the shell entry execs `python3` from PATH: the interpreter running this suite
        os.symlink(sys.executable, os.path.join(self.py_dir, "python3"))
        with open(os.path.join(self.stub_dir, "stub.py"), "w") as f:
            f.write(STUB)
        with open(os.path.join(self.stub_dir, "claude"), "w") as f:
            f.write(STUB_SH % sys.executable)
        os.chmod(os.path.join(self.stub_dir, "claude"), 0o755)
        self.stub_mode(stdout=json.dumps(ok_document()))
        self.ws = os.path.join(self.tmp, "workspace")
        os.makedirs(self.ws)
        self.doc = os.path.join(self.tmp, "doc.md")
        with open(self.doc, "w") as f:
            f.write("# A document\n\nOne line to read.\n")
        with open(os.path.join(self.ws, "notes.md"), "w") as f:
            f.write("workspace file\n")
        self.runs = os.path.join(self.tmp, "runs")
        self.n = 0

    def stub_mode(self, stdout, stderr="", exit=0):
        with open(os.path.join(self.stub_dir, "mode.json"), "w") as f:
            json.dump({"stdout": stdout, "stderr": stderr, "exit": exit}, f)

    def path(self, with_claude=True):
        dirs = ([self.stub_dir] if with_claude else []) + [self.py_dir, "/usr/bin", "/bin"]
        return os.pathsep.join(dirs)

    def env(self, with_claude=True, **extra):
        env = {"PATH": self.path(with_claude), "HOME": self.tmp, "TMPDIR": self.tmp,
               "READERS_CHECKOUT": os.path.join(self.tmp, "no-checkout"),
               "READERS_RUN_ROOT": self.runs, "PYTHONDONTWRITEBYTECODE": "1",
               "LANG": "C.UTF-8", "A_PARENT_SECRET": "must-not-reach-the-child"}
        env.update(extra)
        return env

    def request(self, **fields):
        self.n += 1
        req = {"protocol_version": 1, "run_id": "run-cli", "call_id": "call-%d" % self.n,
               "row": ROW, "mandate": "Read the document and report.", "profile": "starved",
               "documents": [self.doc]}
        req.update(fields)
        path = os.path.join(self.tmp, "request-%d.json" % self.n)
        with open(path, "w") as f:
            json.dump(req, f)
        return path, req

    def entry(self, args, env):
        proc = subprocess.run(["/bin/sh", ENTRY] + args, env=env, cwd=self.tmp,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")

    def dispatch(self, req_path, env):
        code, out, err = self.entry([req_path], env)
        try:
            return code, json.loads(out)
        except ValueError:
            self.fail("the runner printed no JSON: %r %r" % (out, err))

    def calls(self):
        d = os.path.join(self.stub_dir, "calls")
        if not os.path.isdir(d):
            return []
        out = []
        for name in sorted(os.listdir(d), key=lambda n: int(n.split(".")[0])):
            with open(os.path.join(d, name)) as f:
                out.append(json.load(f))
        return out

    def call_dir(self, req):
        return os.path.join(self.runs, req["run_id"], req["call_id"])


class CannedFixtures(_Lane):
    """Dispatch on each canned fixture and the status each maps to."""

    def canned(self, name, **fields):
        path, req = self.request(**fields)
        code, res = self.dispatch(path, self.env(READERS_TEST="1",
                                                 READERS_CANNED_CLAUDE=os.path.join(CANNED, name)))
        self.assertEqual(self.calls(), [], "a canned dispatch launches no child")
        return code, res, req

    def test_ok(self):
        code, res, req = self.canned("claude-ok")
        self.assertEqual((code, res["status"]), (0, "ok"), res)
        self.assertEqual(res["raw_text"], ok_document()["result"])
        with open(res["raw_file"], encoding="utf-8") as f:
            self.assertEqual(f.read(), ok_document()["result"])
        self.assertEqual(res["transport"], "claude-cli")
        self.assertEqual(res["kind"], "portable")
        self.assertEqual(res["effective_model"], "opus")
        self.assertIsNone(res["effective_effort"])
        self.assertTrue(res["canned"].startswith("READERS_CANNED_CLAUDE="))
        roster_row = {r["id"]: r for r in readers.load_roster()["rows"]}[ROW]
        self.assertEqual(res["parity"], roster_row["parity"]["starved"])
        self.assertEqual(res["isolation"], roster_row["isolation"]["starved"])
        diag = res["diagnostics"]
        for name in ("command.txt", "stdout.json", "stderr.txt"):
            self.assertTrue(os.path.isfile(os.path.join(diag, name)), name)
        self.assertTrue(os.path.isfile(os.path.join(self.call_dir(req), "dispatch.log")))

    def test_empty(self):
        code, res, _ = self.canned("claude-empty")
        self.assertEqual((code, res["status"]), (1, "empty"), res)
        self.assertEqual(res["raw_text"], "")
        self.assertIsNone(res["raw_file"])

    def test_error(self):
        code, res, _ = self.canned("claude-error")
        self.assertEqual((code, res["status"]), (1, "transport-failed"), res)
        self.assertIn("CANNED-ERROR", res["reason"])
        self.assertEqual(res["exit_code"], 1)

    def test_incomplete(self):
        code, res, _ = self.canned("claude-incomplete")
        self.assertEqual((code, res["status"]), (1, "incomplete"), res)
        self.assertEqual(res["raw_text"], "")
        self.assertIsNone(res["raw_file"])
        with open(os.path.join(res["diagnostics"], "partial.md"), encoding="utf-8") as f:
            self.assertIn("CANNED-PARTIAL", f.read())
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(res["diagnostics"]), "raw.md")))


class TheHookOutsideTest(_Lane):

    def test_hook_without_readers_test_is_refused_with_nothing_sent(self):
        path, req = self.request()
        code, res = self.dispatch(path, self.env(READERS_CANNED_CLAUDE=os.path.join(CANNED, "claude-ok")))
        self.assertEqual((code, res["status"]), (1, "transport-failed"), res)
        self.assertIn("canned response outside test", res["reason"])
        self.assertEqual(self.calls(), [], "nothing is sent")
        cd = self.call_dir(req)
        self.assertFalse(os.path.exists(os.path.join(cd, "dispatch.log")))
        self.assertFalse(os.path.exists(os.path.join(cd, "diagnostics")))
        self.assertTrue(os.path.isfile(os.path.join(cd, "sidecar.json")))


class TheCommandLine(_Lane):
    """The argv built for each profile, the stdin prompt, the environment keys, the working directory."""

    FIXED = ["-p", "--model", "opus", "--output-format", "json", "--no-session-persistence",
             "--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands"]

    def launch(self, **fields):
        path, req = self.request(**fields)
        code, res = self.dispatch(path, self.env())
        self.assertEqual((code, res["status"]), (0, "ok"), res)
        calls = self.calls()
        self.assertEqual(len(calls), 1)
        roster = {r["id"]: r for r in readers.load_roster()["rows"]}
        loaded = dict(req)
        self.assertEqual(calls[0]["stdin"], readers.compose(loaded, roster[ROW]),
                         "the composed prompt, on stdin, byte for byte")
        # PWD, SHLVL and _ are set by the stub's own /bin/sh front; __CF_USER_TEXT_ENCODING by macOS
        self.assertTrue(set(calls[0]["env_keys"]) <= set(readers.CHILD_ENV_KEYS) | {"PWD", "SHLVL", "_", "__CF_USER_TEXT_ENCODING"},
                        calls[0]["env_keys"])
        self.assertNotIn("A_PARENT_SECRET", calls[0]["env_keys"])
        self.assertNotIn("READERS_RUN_ROOT", calls[0]["env_keys"])
        with open(os.path.join(res["diagnostics"], "command.txt")) as f:
            self.assertEqual(json.loads(f.read()), ["claude"] + calls[0]["argv"])
        return calls[0], res, req

    def test_starved(self):
        call, res, req = self.launch(profile="starved")
        self.assertEqual(call["argv"], self.FIXED + ["--tools", "", "--disallowedTools", "WebFetch,WebSearch"])
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.join(self.call_dir(req), "work"))
        self.assertEqual(call["cwd_entries"], [])
        self.assertTrue(res["parity"].startswith("tools: none"))

    def test_packet_only(self):
        call, res, req = self.launch(profile="packet-only")
        self.assertEqual(call["argv"], self.FIXED + ["--tools", "", "--disallowedTools", "WebFetch,WebSearch"])
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.join(self.call_dir(req), "packet"))
        self.assertEqual(call["cwd_entries"], ["doc.md"])
        self.assertTrue(res["parity"].startswith("tools: none"))

    def test_repo(self):
        call, res, req = self.launch(profile="repo", workspace=self.ws)
        self.assertEqual(call["argv"], self.FIXED + ["--tools", "Read,Glob,Grep", "--add-dir", self.ws,
                                                     "--disallowedTools", "WebFetch,WebSearch"])
        self.assertEqual(os.path.realpath(call["cwd"]), self.ws)
        self.assertEqual(res["workdir"], self.ws)

    def test_effort_only_when_the_request_carries_one(self):
        call, res, _ = self.launch(profile="starved", effort="high")
        self.assertEqual(call["argv"], self.FIXED + ["--effort", "high", "--tools", "",
                                                     "--disallowedTools", "WebFetch,WebSearch"])
        self.assertEqual(res["effective_effort"], "high")

    def test_repo_with_tools_is_not_offered(self):
        path, _ = self.request(profile="repo-with-tools", workspace=self.ws)
        code, res = self.dispatch(path, self.env())
        self.assertEqual(res["status"], "profile-unsupported", res)
        self.assertEqual(self.calls(), [])

    def test_an_effort_the_row_does_not_list(self):
        path, _ = self.request(effort="max")
        code, res = self.dispatch(path, self.env())
        self.assertEqual(res["status"], "invalid-request", res)
        self.assertEqual(self.calls(), [])


class TheGuards(_Lane):
    """The result document's guards, from a stand-in child (no canned hook)."""

    def status_for(self, stdout, stderr="", exit=0):
        self.stub_mode(stdout=stdout, stderr=stderr, exit=exit)
        path, _ = self.request()
        code, res = self.dispatch(path, self.env())
        return res

    def test_nonzero_exit_keeps_the_cli_message(self):
        res = self.status_for("", stderr="Error: synthetic startup failure", exit=2)
        self.assertEqual(res["status"], "transport-failed")
        self.assertIn("synthetic startup failure", res["reason"])
        self.assertEqual(res["exit_code"], 2)

    def test_unparseable_stdout(self):
        res = self.status_for("not json at all")
        self.assertEqual(res["status"], "transport-failed")

    def test_is_error_under_exit_zero(self):
        doc = ok_document()
        doc.update(is_error=True, result="synthetic error text")
        res = self.status_for(json.dumps(doc))
        self.assertEqual(res["status"], "transport-failed")
        self.assertIn("synthetic error text", res["reason"])

    def test_missing_result(self):
        doc = ok_document()
        del doc["result"]
        res = self.status_for(json.dumps(doc))
        self.assertEqual(res["status"], "transport-failed")

    def test_turn_cap_is_incomplete(self):
        doc = ok_document()
        doc.update(subtype="error_max_turns", num_turns=1, result="cut short")
        res = self.status_for(json.dumps(doc))
        self.assertEqual(res["status"], "incomplete")
        with open(os.path.join(res["diagnostics"], "partial.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "cut short")

    def test_whitespace_result_is_empty(self):
        doc = ok_document()
        doc.update(result=" \n\t")
        res = self.status_for(json.dumps(doc))
        self.assertEqual(res["status"], "empty")


class ClaudeAbsent(_Lane):

    def test_lane_unavailable_before_any_dispatch_line(self):
        self.assertIsNone(shutil.which("claude", path=self.path(with_claude=False)),
                          "the synthetic PATH must not hold a claude binary")
        path, req = self.request()
        code, res = self.dispatch(path, self.env(with_claude=False))
        self.assertEqual((code, res["status"]), (1, "lane-unavailable"), res)
        self.assertIn("claude CLI not on PATH", res["reason"])
        self.assertFalse(os.path.exists(os.path.join(self.call_dir(req), "dispatch.log")))
        code, out, _ = self.entry(["validate", path], self.env(with_claude=False))
        self.assertEqual((code, out.strip()), (1, "lane-unavailable"))


class ValidateAndSuggestUnderTheFloor(_Lane):

    def test_validate_passes_the_row_under_floor_opus(self):
        path, _ = self.request(floor="opus")
        code, out, err = self.entry(["validate", path], self.env())
        self.assertEqual((code, out.strip()), (0, "valid"), err)
        self.assertEqual(self.calls(), [], "validate dispatches nothing")
        self.assertFalse(os.path.exists(self.runs), "validate writes nothing")

    def test_a_typed_model_under_the_floor_is_unknown_model(self):
        path, _ = self.request(floor="opus", model="sonnet")
        code, out, _ = self.entry(["validate", path], self.env())
        self.assertEqual((code, out.strip()), (1, "unknown-model"))

    def test_the_row_needs_no_word(self):
        path, _ = self.request(authorized=False)
        code, out, _ = self.entry(["validate", path], self.env())
        self.assertEqual((code, out.strip()), (0, "valid"))

    def test_suggest_under_floor_opus(self):
        code, out, err = self.entry(["suggest", ROW, "--run", "run-suggest", "--floor", "opus"], self.env())
        self.assertEqual(code, 0, out + err)
        body = json.loads(out)
        (row,) = body["suggestions"]
        self.assertEqual(row["row"], ROW)
        self.assertEqual(row["model"], "opus")
        self.assertEqual(row["source"], "roster default")
        self.assertEqual(row["eligibility"], "eligible")
        self.assertIs(row["outside"], False)
        self.assertIs(row["needs_word"], False)
        self.assertIs(row["available"], True)


class TheRoster(unittest.TestCase):

    def test_the_new_row(self):
        rows = {r["id"]: r for r in readers.load_roster()["rows"]}
        row = rows[ROW]
        expected = {"provider": "anthropic", "transport": "claude-cli", "kind": "portable",
                    "model": "opus", "effort_encoding": "flag", "effort_default": "",
                    "efforts": ["low", "medium", "high"], "context_window": "unknown",
                    "max_output": "unknown", "limits_source": "harness", "timeout_s": 1800,
                    "credential_env": "", "eligibility": "eligible",
                    "supported_profiles": ["starved", "packet-only", "repo"],
                    "available": True, "guide": "", "verified_at": "2026-09-24"}
        for key, value in expected.items():
            self.assertEqual(row[key], value, key)
        self.assertEqual(sorted(row["parity"]), sorted(row["supported_profiles"]))
        self.assertEqual(sorted(row["isolation"]), sorted(row["supported_profiles"]))
        self.assertEqual(set(row), set(rows["claude-opus"]), "the same fields as the Claude rows")

    def test_every_existing_row_is_unchanged(self):
        git = shutil.which("git")
        top = None
        if git:
            proc = subprocess.run([git, "-C", ASSETS, "rev-parse", "--show-toplevel"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            top = proc.stdout.decode().strip() if proc.returncode == 0 else None
        if not top:
            self.skipTest("no git checkout around the assets (the installed shape): the base roster "
                          "cannot be read")
        proc = subprocess.run([git, "-C", top, "show", "%s:%s" % (BASE_COMMIT, ROSTER_REL)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            self.skipTest("commit %s is not in this checkout: %s" % (BASE_COMMIT, proc.stderr.decode()))
        base = json.loads(proc.stdout.decode("utf-8"))
        now = readers.load_roster()
        self.assertEqual({k: v for k, v in now.items() if k != "rows"},
                         {k: v for k, v in base.items() if k != "rows"})
        self.assertEqual(now["rows"][:len(base["rows"])], base["rows"])
        self.assertEqual([r["id"] for r in now["rows"][len(base["rows"]):]], [ROW])


if __name__ == "__main__":
    unittest.main()
