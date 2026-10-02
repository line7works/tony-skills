"""A v1 readers root is refused before any of its files is opened or run (B5; rulings E15-6 and E15-7).

Every candidate readers root, the explicit one and both discovery routes (3a beside the core, 3b the
installed shape), is resolved to its real path first; one under a v1 plugin folder, a symbolic link's
target included, is refused BEFORE its manifest, its roster or any executable of it is opened, and the
refusal is a trace line. The planted root here is a tripwire: its manifest and roster are named pipes (an
open would block, and the test's timeout would fail it) and its `readers.py` writes a marker when run.
"""
import json
import os
import subprocess
import sys
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from back_core import trace  # noqa: E402

V1 = trace.v1_names()[-1]
TIMEOUT = 120
TRIPWIRE = """import os, sys
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "V1_EXECUTED"), "w") as fh:
    fh.write("ran")
print("1")
"""


def plant_tripwire(parent):
    """A readers-shaped folder under `<parent>/plugins/<a v1 name>/`: named pipes for its manifest and
    roster, and a `readers.py` that leaves a marker. Returns the folder."""
    root = os.path.join(parent, "plugins", V1)
    os.makedirs(os.path.join(root, ".claude-plugin"))
    os.makedirs(os.path.join(root, "skills", "readers", "assets"))
    os.mkfifo(os.path.join(root, ".claude-plugin", "plugin.json"))
    os.mkfifo(os.path.join(root, "skills", "readers", "assets", "roster.json"))
    testlib.write_text(os.path.join(root, "skills", "readers", "assets", "readers.py"), TRIPWIRE)
    return root


def marker(root):
    return os.path.exists(os.path.join(root, "skills", "readers", "assets", "V1_EXECUTED"))


class TheDiscoveryRoutes(unittest.TestCase):
    """The preflight on each route, driven in a child process so a blocked open fails by timeout."""

    PROBE = """import json, os, sys
sys.path.insert(0, sys.argv[1])
sys.dont_write_bytecode = True
from vertical_core import common, readers_link
common.plugin_root = lambda: sys.argv[2]
try:
    readers_link.find(sys.argv[3] or None)
    print(json.dumps({"refused": False}))
except readers_link.RootRefused as exc:
    print(json.dumps({"refused": True, "route": exc.route, "real": exc.real, "under": exc.under}))
"""

    def setUp(self):
        self.tmp = os.path.realpath(testlib.make_scratch("vroot-"))
        self.addCleanup(testlib.rmtree, self.tmp)
        self.v1 = plant_tripwire(self.tmp)

    def probe(self, plugin_root, argument=""):
        os.makedirs(plugin_root, exist_ok=True)
        try:
            proc = subprocess.run([sys.executable, "-c", self.PROBE, testlib.SCRIPTS, plugin_root, argument],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT,
                                  env=testlib.base_env({"PYTHONDONTWRITEBYTECODE": "1"}))
        except subprocess.TimeoutExpired:
            self.fail("the resolver opened the v1 root's manifest or roster (a named pipe blocked)")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertFalse(marker(self.v1), "the v1 root's readers.py ran")
        return json.loads(proc.stdout.decode())

    def test_an_explicit_root_under_a_v1_folder(self):
        out = self.probe(os.path.join(self.tmp, "plugins", "vertical-v2"), self.v1)
        self.assertEqual((out["refused"], out["route"], out["under"]), (True, "argument", V1))

    def test_an_explicit_root_that_is_a_link_into_a_v1_folder(self):
        link = os.path.join(self.tmp, "elsewhere", "readers")
        os.makedirs(os.path.dirname(link))
        os.symlink(self.v1, link)
        out = self.probe(os.path.join(self.tmp, "plugins", "vertical-v2"), link)
        self.assertEqual((out["refused"], out["route"], out["real"]), (True, "argument", self.v1))

    def test_route_3a_a_checkout_sibling_linked_into_a_v1_folder(self):
        os.symlink(self.v1, os.path.join(self.tmp, "plugins", "readers"))
        out = self.probe(os.path.join(self.tmp, "plugins", "vertical-v2"))
        self.assertEqual((out["refused"], out["route"], out["real"]), (True, "3a", self.v1))

    def test_route_3b_an_installed_version_linked_into_a_v1_folder(self):
        cache = os.path.join(self.tmp, "cache", "market")
        os.makedirs(os.path.join(cache, "readers"))
        os.symlink(self.v1, os.path.join(cache, "readers", "1.0.1"))
        out = self.probe(os.path.join(cache, "vertical-v2", "0.1.0"))
        self.assertEqual((out["refused"], out["route"], out["real"]), (True, "3b", self.v1))


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the CLI probes run the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheCliRefusal(unittest.TestCase):
    """Through the real driver: the run stops `station-refused` with one `refused` trace line, and the
    tripwire's marker never appears."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vrootcli-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def run_with_timeout(self, run_dir, args):
        env = vlib.env()
        try:
            proc = subprocess.run([sys.executable, testlib.DRIVER] + args, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, cwd=self.tmp, env=env, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            self.fail("the driver opened the v1 root's manifest or roster (a named pipe blocked)")
        return proc.returncode, json.loads(proc.stdout.decode() or "null"), proc.stderr.decode()

    def assert_refused(self, run_dir, code, out, v1):
        self.assertEqual(code, 10, out)
        self.assertEqual(out["stop_tag"], "station-refused")
        lines = [json.loads(l) for l in testlib.read_text(os.path.join(run_dir, "trace.jsonl")).splitlines()]
        self.assertEqual([l["kind"] for l in lines], ["refused"])
        self.assertEqual(lines[0]["refusal"]["rules"], ["v1-root"])
        self.assertEqual(lines[0]["expected"], "readers")
        self.assertFalse(marker(v1))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-local.json")))

    def test_request_with_a_v1_root_never_opens_or_runs_it(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        v1 = plant_tripwire(self.tmp)
        code, out, err = self.run_with_timeout(run_dir, ["request", "--run-dir", run_dir, "--readers-root", v1])
        self.assert_refused(run_dir, code, out, v1)

    def test_ask_with_a_v1_root_never_opens_it(self):
        ws, info = vlib.make_repo(self.tmp, records=True)
        drive, run_dir = vlib.start(self.tmp, ws)
        self.assertEqual(drive(["gate", "--run-dir", run_dir])[0], 0)
        run_id = vlib.load(run_dir, "input.json")["run_id"]
        local = vlib.write(self.tmp, "sl.json", vlib.suggest_doc(run_id, run_dir, ["claude-session"], floor="opus"))
        outside = vlib.write(self.tmp, "so.json", vlib.suggest_doc(run_id, run_dir, vlib.OUTSIDE_ROWS))
        v1 = plant_tripwire(self.tmp)
        code, out, err = self.run_with_timeout(run_dir, ["ask", "--run-dir", run_dir, "--local-suggest", local,
                                                         "--outside-suggest", outside, "--readers-root", v1])
        self.assert_refused(run_dir, code, out, v1)


if __name__ == "__main__":
    unittest.main()
