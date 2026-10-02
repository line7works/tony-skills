"""E14 slice 3c, item 3.1 (contract A3): the Codex reviewer's roster lookup through readers.

Request mode no longer refuses unconditionally. It finds the readers component beside this
plugin (route 3a in a checkout, route 3b in an installed cache; a test hook under
SIGNOFF_V2_ADAPTER_TEST=1 names a fixture root), runs readers' own `suggest` step at the
Opus-class floor for the roster rows a Codex session can dispatch, writes the readers request for
the row it names where readers' SKILL.md says a caller writes one (`<request run_dir>/<call
id>.json`), prints it and exits 0. `lane-unavailable` (exit 3, the capability named) is reported
only when no row is eligible at the floor or readers is not there; a refusal from `suggest`
itself is carried with readers' own status and reason (exit 3). Nothing is launched: `codex` and
`claude` stand-ins on PATH record every argument and are never called, and no reader is
dispatched.

Every run uses the real `readers.py` (copied from the checkout into a fixture root beside a
fixture roster) with READERS_CHECKOUT pointing at a directory that does not exist, so readers'
last-pick memory reports `unavailable` and nothing is written outside the temporary tree.
"""

import json
import os
import shutil
import stat
import tempfile
import unittest

import testlib
from test_reviewer import fake_run

HELPER = "reviewer.py"
PLUGINS = os.path.dirname(os.path.dirname(os.path.dirname(testlib.SKILL_ROOT)))
READERS_PLUGIN = os.path.join(PLUGINS, "readers")
READERS_PY = os.path.join(READERS_PLUGIN, "skills", "readers", "assets", "readers.py")
ROOT_VAR = testlib.PREFIX + "_READERS_ROOT"
RUN_ID = "signoff-f-20260923-ab12"


def fixture_readers(parent, roster_name, version="1.0.1"):
    """A readers component with the real runner and a fixture roster: `<parent>/<version>`."""
    root = os.path.join(parent, version)
    assets = os.path.join(root, "skills", "readers", "assets")
    os.makedirs(assets)
    os.makedirs(os.path.join(root, ".claude-plugin"))
    with open(os.path.join(root, ".claude-plugin", "plugin.json"), "w") as handle:
        json.dump({"name": "readers", "version": version}, handle)
    shutil.copy(READERS_PY, os.path.join(assets, "readers.py"))
    shutil.copy(os.path.join(testlib.FIXTURES, roster_name), os.path.join(assets, "roster.json"))
    return root


def capturing(parent, names=("codex", "claude")):
    """Stand-ins that record every argument they are given and exit 66."""
    folder = os.path.join(parent, "capture-bin")
    os.makedirs(folder)
    log = os.path.join(parent, "launch-argv.log")
    for name in names:
        script = os.path.join(folder, name)
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\nprintf '%s %%s\\n' \"$*\" >> '%s'\nexit 66\n" % (name, log))
        os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR)
    return folder, log


class ReadersRoute(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="a3-route-")
        self.run_dir = fake_run(self.work)
        self.calls = os.path.join(self.run_dir, "readers", "calls")
        self.bin, self.log = capturing(self.work)
        self.env = {"PATH": self.bin + os.pathsep + "/usr/bin:/bin",
                    "READERS_CHECKOUT": os.path.join(self.work, "no-checkout")}

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def launched(self):
        if not os.path.isfile(self.log):
            return []
        with open(self.log) as handle:
            return [line for line in handle.read().split("\n") if line.strip()]

    def call(self, roster=None, extra=(), root=None, adapter=None):
        env = dict(self.env)
        if roster:
            env[ROOT_VAR] = fixture_readers(os.path.join(self.work, "readers-fixture"), roster)
        elif root:
            env[ROOT_VAR] = root
        return testlib.run(HELPER, ["--run-dir", self.run_dir, "--workspace", self.work]
                           + list(extra), env=env, adapter=adapter)

    def written(self):
        if not os.path.isdir(self.calls):
            return []
        return sorted(name for name in os.listdir(self.calls) if name.endswith(".json"))

    def test_an_eligible_portable_row_is_requested_and_exit_0(self):
        code, out, err = self.call("roster-portable-opus.json")
        self.assertEqual(code, 0, "%s %s" % (out, err))
        doc = json.loads(out)
        self.assertEqual(doc["status"], "ready")
        self.assertEqual(doc["row"], "claude-opus-cli")
        self.assertEqual(len(doc["requests"]), 1)
        block = doc["requests"][0]
        self.assertEqual((block["row"], block["floor"], block["protocol_version"]),
                         ("claude-opus-cli", "opus", 1))
        self.assertEqual(block["profile"], "repo", "the row offers repo, not repo-with-tools")
        self.assertEqual(block["run_id"], RUN_ID)
        self.assertEqual(block["call_id"], RUN_ID + "-review")
        self.assertEqual(os.path.realpath(block["run_dir"]), os.path.realpath(self.calls))
        for never in ("model", "effort", "output_budget", "isolation", "session_model",
                      "authorized"):
            self.assertNotIn(never, block)
        path = os.path.join(self.calls, RUN_ID + "-review.json")
        self.assertEqual([os.path.realpath(p) for p in doc["request_files"]],
                         [os.path.realpath(path)])
        with open(path) as handle:
            self.assertEqual(json.load(handle), block, "the file is the block printed")
        self.assertEqual(doc["suggest"]["eligibility"], "eligible")
        self.assertTrue(os.path.isfile(os.path.join(self.calls, "snapshot", "roster.json")),
                        "readers' suggest froze the run beside the request")
        self.assertEqual(doc["dispatch"][0]["argv"][1:], [path])
        self.assertIsNone(doc["answer_identity"])
        self.assertEqual(self.launched(), [], "nothing is launched: %s" % self.launched())

    def test_one_request_per_lens(self):
        code, out, err = self.call("roster-portable-opus.json",
                                   extra=["--lens", "spec", "--lens", "correctness"])
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual([b["call_id"] for b in doc["requests"]],
                         [RUN_ID + "-review-spec", RUN_ID + "-review-correctness"])
        self.assertEqual(self.written(), [RUN_ID + "-review-correctness.json",
                                          RUN_ID + "-review-spec.json"])

    def test_no_eligible_row_at_the_floor_is_lane_unavailable(self):
        code, out, err = self.call("roster-no-portable-opus.json")
        self.assertEqual(code, 3, "%s %s" % (out, err))
        doc = json.loads(out)
        self.assertEqual(doc["status"], "lane-unavailable")
        self.assertIn("floor", doc["missing_capability"])
        self.assertIn("portable", doc["missing_capability"])
        self.assertEqual(doc["requests"], [])
        self.assertEqual(self.written(), [], "no request is written for a call that cannot be made")
        self.assertEqual(self.launched(), [])

    def test_a_refusal_from_suggest_is_carried_with_readers_own_status(self):
        os.makedirs(os.path.join(self.run_dir, "readers"), exist_ok=True)
        with open(self.calls, "w") as handle:
            handle.write("a file where readers' run directory should be\n")
        code, out, err = self.call("roster-portable-opus.json")
        self.assertEqual(code, 3, "%s %s" % (out, err))
        doc = json.loads(out)
        self.assertEqual(doc["status"], "invalid-request")
        self.assertIn("run dir unusable", doc["reason"])
        self.assertEqual(doc["requests"], [])
        self.assertEqual(self.launched(), [])

    def test_readers_not_found_is_lane_unavailable_naming_it(self):
        home, adapter = testlib.installed_copy(self.work)
        absent = os.path.join(self.work, "absent-readers")
        code, out, err = self.call(root=absent, adapter=adapter)
        self.assertEqual(code, 3, "%s %s" % (out, err))
        doc = json.loads(out)
        self.assertEqual(doc["status"], "lane-unavailable")
        self.assertIn("readers component", doc["missing_capability"])
        self.assertIn(absent, doc["missing_capability"], "every place looked is named")
        self.assertEqual(self.written(), [])

    def test_the_installed_shape_finds_readers_by_route_3b(self):
        home, adapter = testlib.installed_copy(self.work)
        market = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(adapter))))))
        fixture_readers(os.path.join(market, "readers"), "roster-portable-opus.json", "1.0.1")
        env = dict(self.env)
        env[testlib.TEST_FLAG] = None
        code, out, err = testlib.run(HELPER, ["--run-dir", self.run_dir], env=env, adapter=adapter)
        self.assertEqual(code, 0, "%s %s" % (out, err))
        doc = json.loads(out)
        self.assertEqual(doc["row"], "claude-opus-cli")
        self.assertEqual(doc["_sources"]["readers_route"], "3b")

    def test_the_test_hook_is_ignored_outside_test_mode(self):
        root = fixture_readers(os.path.join(self.work, "hooked"), "roster-no-portable-opus.json")
        home, adapter = testlib.installed_copy(self.work)
        env = dict(self.env)
        env.update({ROOT_VAR: root, testlib.TEST_FLAG: None})
        code, out, err = testlib.run(HELPER, ["--run-dir", self.run_dir], env=env, adapter=adapter)
        self.assertEqual(code, 3, "%s %s" % (out, err))
        doc = json.loads(out)
        self.assertEqual(doc["status"], "lane-unavailable")
        self.assertIn("readers component", doc["missing_capability"],
                      "the hook's roster was not read: no readers beside the installed copy")

    def test_the_row_it_names_meets_the_cores_floor_by_its_roster_model(self):
        # E14 punch list, item 4(a): the reader reports the row's roster `model` (`opus` for claude-opus-cli) as
        # its effective model, which the sidecar map hands the core; the core's floor classes it opus
        code, out, err = self.call("roster-portable-opus.json")
        self.assertEqual(code, 0, "%s %s" % (out, err))
        doc = json.loads(out)
        with open(os.path.join(self.calls, "snapshot", "roster.json")) as handle:
            rows = json.load(handle)["rows"]
        model = [r["model"] for r in rows if r["id"] == doc["row"]][0]
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "signoff_floor_for_adapter", os.path.join(testlib.SKILL_ROOT, "scripts", "signoff_core", "floor.py"))
        floor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(floor)
        self.assertEqual((model, floor.class_of(model)), ("opus", ("opus", True)))


if __name__ == "__main__":
    unittest.main()
