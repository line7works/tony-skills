"""A readers root is used only by allowlist identity (the E15 lane contract A5 (1); B5, C1A3-2; rulings
E15-6 and E15-7).

The root must be the expected readers plugin: the checkout sibling `plugins/readers` beside this core (route
3a) or an installed `readers/<version>` folder of the plugin cache (route 3b), each a real directory (never
a link) under its exact name, compared with the candidate by the disk's own identity (device and inode).
Every file vertical-v2 then opens or runs from it (the manifest, the roster, `readers.py`) must resolve by
its real path inside that root, compared the same way. Anything else is refused BEFORE any of the root's
files is opened or run, and the refusal is a trace line; the name-based v1 screen stays as a second line
behind it. The planted v1 roots here are tripwires: their manifest and roster are named pipes (an open would
block, and the test's timeout would fail it) and their `readers.py` writes a marker when run.
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


REAL_READERS = """import sys
if sys.argv[1:] == ["--version"]:
    print("1")
"""


def plant_readers(root, version="1.0.1"):
    """A readers-shaped plugin at `root`: a manifest naming readers, a roster, and a readers.py that prints
    its protocol version and writes nothing."""
    testlib.write_json(os.path.join(root, ".claude-plugin", "plugin.json"), {"name": "readers", "version": version})
    testlib.write_json(os.path.join(root, "skills", "readers", "assets", "roster.json"), {"rows": []})
    testlib.write_text(os.path.join(root, "skills", "readers", "assets", "readers.py"), REAL_READERS)
    return root


def plant_tripwire_at(root):
    """The tripwire's shape at any folder (named pipes for the manifest and the roster, a marker-writing
    readers.py)."""
    os.makedirs(os.path.join(root, ".claude-plugin"))
    os.makedirs(os.path.join(root, "skills", "readers", "assets"))
    os.mkfifo(os.path.join(root, ".claude-plugin", "plugin.json"))
    os.mkfifo(os.path.join(root, "skills", "readers", "assets", "roster.json"))
    testlib.write_text(os.path.join(root, "skills", "readers", "assets", "readers.py"), TRIPWIRE)
    return root


def case_insensitive(folder):
    """True when `folder`'s disk folds letter case (the attack the case-variant tests drive needs it)."""
    probe = os.path.join(folder, "CaseProbe")
    os.makedirs(probe)
    try:
        return os.path.isdir(os.path.join(folder, "caseprobe"))
    finally:
        os.rmdir(probe)


class TheAllowlist(unittest.TestCase):
    """A5 (1): the root by allowlist identity, every file it opens or runs inside it; driven in a child
    process (`resolve`, which also runs readers.py --version) so a blocked open fails by timeout."""

    PROBE = """import json, os, sys
sys.path.insert(0, sys.argv[1])
sys.dont_write_bytecode = True
from vertical_core import common, readers_link
common.plugin_root = lambda: sys.argv[2]
try:
    found, roster, ident, refusals = readers_link.resolve(None, sys.argv[3] or None)
    print(json.dumps({"refused": False, "route": found["route"], "root": ident["root"],
                      "interface_version": ident["interface_version"], "refusals": refusals}))
except readers_link.RootRefused as exc:
    print(json.dumps({"refused": True, "route": exc.route, "rule": exc.rule, "under": exc.under}))
"""

    def setUp(self):
        self.tmp = os.path.realpath(testlib.make_scratch("vallow-"))
        self.addCleanup(testlib.rmtree, self.tmp)
        self.core = os.path.join(self.tmp, "plugins", "vertical-v2")
        os.makedirs(self.core)
        self.v1 = plant_tripwire(self.tmp)

    def probe(self, plugin_root=None, argument=""):
        os.makedirs(plugin_root or self.core, exist_ok=True)
        try:
            proc = subprocess.run([sys.executable, "-c", self.PROBE, testlib.SCRIPTS, plugin_root or self.core,
                                   argument], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT,
                                  env=testlib.base_env({"PYTHONDONTWRITEBYTECODE": "1"}))
        except subprocess.TimeoutExpired:
            self.fail("a file of a refused root was opened (a named pipe blocked)")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertFalse(marker(self.v1), "the v1 folder's readers.py ran")
        return json.loads(proc.stdout.decode())

    def assert_refused(self, out, route, rule="v1-root"):
        self.assertEqual((out["refused"], out["route"], out["rule"]), (True, route, rule), out)

    def test_a_different_letter_case_of_a_v1_folder_as_the_explicit_root(self):
        if not case_insensitive(self.tmp):
            self.skipTest("this disk keeps letter case apart, so the case variant is another folder")
        plant_readers(os.path.join(self.tmp, "plugins", "readers"))
        self.assert_refused(self.probe(argument=os.path.join(self.tmp, "plugins", V1.upper())), "argument")

    def test_route_3a_a_sibling_linked_to_a_different_letter_case_of_a_v1_folder(self):
        os.symlink(os.path.join(self.tmp, "plugins", V1.upper()), os.path.join(self.tmp, "plugins", "readers"))
        self.assert_refused(self.probe(), "3a")

    def test_route_3b_a_version_linked_to_a_different_letter_case_of_a_v1_folder(self):
        cache = os.path.join(self.tmp, "cache", "market")
        plant_tripwire_at(os.path.join(cache, V1, "1.0.0"))
        os.makedirs(os.path.join(cache, "readers"))
        os.symlink(os.path.join(cache, V1.upper(), "1.0.0"), os.path.join(cache, "readers", "1.0.1"))
        out = self.probe(plugin_root=os.path.join(cache, "vertical-v2", "0.1.0"))
        self.assertFalse(marker(os.path.join(cache, V1, "1.0.0")))
        self.assert_refused(out, "3b")

    def test_a_readers_py_linked_into_a_v1_folder(self):
        real = plant_readers(os.path.join(self.tmp, "plugins", "readers"))
        script = os.path.join(real, "skills", "readers", "assets", "readers.py")
        os.remove(script)
        os.symlink(os.path.join(self.v1, "skills", "readers", "assets", "readers.py"), script)
        self.assert_refused(self.probe(), "3a")

    def test_a_roster_linked_into_a_v1_folder(self):
        real = plant_readers(os.path.join(self.tmp, "plugins", "readers"))
        roster = os.path.join(real, "skills", "readers", "assets", "roster.json")
        os.remove(roster)
        os.symlink(os.path.join(self.v1, "skills", "readers", "assets", "roster.json"), roster)
        self.assert_refused(self.probe(), "3a")

    def test_a_manifest_linked_into_a_v1_folder(self):
        real = plant_readers(os.path.join(self.tmp, "plugins", "readers"))
        manifest = os.path.join(real, ".claude-plugin", "plugin.json")
        os.remove(manifest)
        os.symlink(os.path.join(self.v1, ".claude-plugin", "plugin.json"), manifest)
        self.assert_refused(self.probe(), "3a")

    def test_a_root_nested_inside_an_installed_v1_version_folder(self):
        plant_readers(os.path.join(self.tmp, "plugins", "readers"))
        nested = plant_tripwire_at(os.path.join(self.tmp, "cache", "market", V1, "1.0.0", "vendor", "readers"))
        out = self.probe(argument=nested)
        self.assertFalse(marker(nested))
        self.assert_refused(out, "argument")

    def test_a_readers_copy_that_is_not_the_expected_plugin_is_refused(self):
        plant_readers(os.path.join(self.tmp, "plugins", "readers"))
        elsewhere = plant_readers(os.path.join(self.tmp, "elsewhere", "readers"))
        self.assert_refused(self.probe(argument=elsewhere), "argument", rule="no-identity")

    def test_a_link_to_the_real_readers_is_accepted_by_identity(self):
        real = plant_readers(os.path.join(self.tmp, "plugins", "readers"))
        link = os.path.join(self.tmp, "elsewhere", "readers")
        os.makedirs(os.path.dirname(link))
        os.symlink(real, link)
        out = self.probe(argument=link)
        self.assertEqual((out["refused"], out["route"], out["root"], out["refusals"]), (False, "argument", real, []))

    def test_the_real_readers_by_its_normal_path_is_accepted(self):
        real = plant_readers(os.path.join(self.tmp, "plugins", "readers"))
        for argument, route in (("", "3a"), (real, "argument")):
            out = self.probe(argument=argument)
            self.assertEqual((out["refused"], out["route"], out["root"], out["interface_version"]),
                             (False, route, real, 1), argument)

    def test_the_installed_readers_is_accepted_and_a_stray_entry_beside_it_is_never_opened(self):
        cache = os.path.join(self.tmp, "cache", "market")
        real = plant_readers(os.path.join(cache, "readers", "1.0.1"))
        plant_tripwire_at(os.path.join(cache, "readers", "notes"))
        out = self.probe(plugin_root=os.path.join(cache, "vertical-v2", "0.1.0"))
        self.assertFalse(marker(os.path.join(cache, "readers", "notes")))
        self.assertEqual((out["refused"], out["route"], out["root"]), (False, "3b", real))


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


    def test_request_with_a_different_letter_case_of_a_v1_folder_never_opens_or_runs_it(self):
        if not case_insensitive(os.path.realpath(self.tmp)):
            self.skipTest("this disk keeps letter case apart, so the case variant is another folder")
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        v1 = plant_tripwire(self.tmp)
        variant = os.path.join(self.tmp, "plugins", V1.upper())
        code, out, err = self.run_with_timeout(run_dir, ["request", "--run-dir", run_dir, "--readers-root", variant])
        self.assert_refused(run_dir, code, out, v1)

    def test_ask_with_a_different_letter_case_of_a_v1_folder_never_opens_it(self):
        if not case_insensitive(os.path.realpath(self.tmp)):
            self.skipTest("this disk keeps letter case apart, so the case variant is another folder")
        ws, info = vlib.make_repo(self.tmp, records=True)
        drive, run_dir = vlib.start(self.tmp, ws)
        self.assertEqual(drive(["gate", "--run-dir", run_dir])[0], 0)
        run_id = vlib.load(run_dir, "input.json")["run_id"]
        local = vlib.write(self.tmp, "sl.json", vlib.suggest_doc(run_id, run_dir, ["claude-session"], floor="opus"))
        outside = vlib.write(self.tmp, "so.json", vlib.suggest_doc(run_id, run_dir, vlib.OUTSIDE_ROWS))
        v1 = plant_tripwire(self.tmp)
        variant = os.path.join(self.tmp, "plugins", V1.upper())
        code, out, err = self.run_with_timeout(run_dir, ["ask", "--run-dir", run_dir, "--local-suggest", local,
                                                         "--outside-suggest", outside, "--readers-root", variant])
        self.assert_refused(run_dir, code, out, v1)


if __name__ == "__main__":
    unittest.main()
