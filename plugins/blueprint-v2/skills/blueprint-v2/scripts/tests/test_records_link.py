"""The records resolver and the confirm step (required test 8).

Route 3a (the checkout's sibling `records` folder) and route 3b (the installed shape, rebuilt in a
temporary cache), each confirmed through `component-identity` at interface version 2; exit 3 with
one plain line on stderr and nothing on stdout when the component is missing and when it speaks
another interface version, through the phase driver's own error mapping. Only inspect-v2 calls
these helpers at run time (ruling E14-9); the frame tests them in every core because the code is
shared. The station name is a parameter: the events a core writes carry its own name.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import records_client as rcl, records_link  # noqa: E402

RECORDS = testlib.records_root()

PROBE = """
import json, sys
sys.path.insert(0, sys.argv[1])
from station_core import records_link
try:
    client = records_link.open_client(sys.argv[2])
except records_link.ComponentUnavailable as refusal:
    print(json.dumps({"refused": str(refusal)}))
else:
    print(json.dumps({"root": client.root, "interface_version": client.interface_version}))
"""

# A phase driver whose `harvest` opens the component: the driver's own error mapping is measured.
DRIVER_PROBE = """
import sys
sys.path.insert(0, sys.argv[1])
from station_core import driver, records_link

def harvest(ctx, args):
    records_link.open_client(ctx.station, records_root=args.records_root)
    return driver.emit(ctx.envelope(ok=True))

sys.exit(driver.main(sys.argv[2], {}, {"harvest": harvest}, sys.argv[3:]))
"""


def fake_component(parent, interface_version):
    """A real copy of the component with its one INTERFACE_VERSION assignment rewritten."""
    root = os.path.join(parent, "records-v%d" % interface_version)
    shutil.copytree(RECORDS, root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
    script = os.path.join(root, "scripts", "records.py")
    text = testlib.read_text(script)
    changed = re.sub(r"\nINTERFACE_VERSION = \d+\n", "\nINTERFACE_VERSION = %d\n" % interface_version,
                     text, count=1)
    assert changed != text, "the component's INTERFACE_VERSION assignment moved"
    testlib.write_text(script, changed)
    return root


@unittest.skipIf(RECORDS is None, "no records component beside this core (the installed shape): "
                                  "routes 3a and 3b are measured in the checkout only")
class _Scratch(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("records-link-")
        self.addCleanup(testlib.rmtree, self.tmp)


class Route3a(_Scratch):

    def test_the_sibling_folder_is_found_and_confirmed(self):
        env = dict(os.environ)
        env.pop("RECORDS_ROOT", None)
        client = records_link.open_client(testlib.CORE, environ=env)
        self.assertEqual(os.path.realpath(client.root), os.path.realpath(RECORDS))
        self.assertEqual(client.interface_version, 2)

    def test_the_station_name_is_the_callers(self):
        actor = records_link.actor(testlib.CORE, "run-1", "claude-code")
        self.assertEqual(actor, {"station": testlib.CORE, "run_id": "run-1", "harness": "claude-code"})
        with self.assertRaises(ValueError):
            records_link.actor("", "run-1", "claude-code")

    def test_the_copys_own_station_constant_is_never_read(self):
        self.assertEqual(rcl.STATION, "recheck-v2")
        for base, dirs, files in os.walk(testlib.SCRIPTS):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests")]
            for name in files:
                if name.endswith(".py") and name != "records_client.py":
                    text = testlib.read_text(os.path.join(base, name))
                    self.assertNotIn("rcl.STATION", text, name)
                    self.assertNotIn("records_client.STATION", text, name)


class Route3b(_Scratch):

    def setUp(self):
        _Scratch.setUp(self)
        self.market = os.path.join(self.tmp, "cache", "one-market")
        installed = os.path.join(self.market, testlib.CORE, "0.1.0")
        shutil.copytree(testlib.PLUGIN, installed,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "evals", "setups"))
        self.scripts = os.path.join(installed, "skills", testlib.CORE, "scripts")
        version = testlib.load_json(os.path.join(RECORDS, ".claude-plugin", "plugin.json"))["version"]
        self.component = os.path.join(self.market, "records", version)
        shutil.copytree(RECORDS, self.component,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))

    def probe(self):
        env = testlib.base_env()
        proc = subprocess.run([sys.executable, "-c", PROBE, self.scripts, testlib.CORE], cwd=self.tmp,
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return json.loads(proc.stdout.decode())

    def test_the_installed_copy_picks_route_3b_and_confirms_it(self):
        got = self.probe()
        self.assertEqual(os.path.realpath(got.get("root", "")), os.path.realpath(self.component), got)
        self.assertEqual(got["interface_version"], 2)

    def test_with_the_component_gone_the_refusal_names_route_3b(self):
        shutil.rmtree(os.path.join(self.market, "records"))
        refusal = self.probe().get("refused", "")
        self.assertTrue(refusal.startswith("missing dependency: records component (looked in: "), refusal)
        self.assertIn("(no such directory)", refusal)


class ExitThree(_Scratch):

    def driver(self, args, env=None):
        proc = subprocess.run([sys.executable, "-c", DRIVER_PROBE, testlib.SCRIPTS, testlib.CORE] + args,
                              cwd=self.tmp, env=env or testlib.base_env(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.returncode, proc.stdout.decode(), proc.stderr.decode()

    def assertExitThree(self, code, out, err, needle):
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertEqual(len(err.strip().split("\n")), 1, err)
        self.assertIn(needle, err)

    def test_a_missing_component(self):
        env = testlib.base_env({testlib.PREFIX + "_TEST": "1", testlib.PREFIX + "_TEST_NO_RECORDS": "1"})
        code, out, err = self.driver(["harvest", "--run-dir", self.tmp], env=env)
        self.assertExitThree(code, out, err, "missing dependency: records component")

    def test_another_interface_version(self):
        root = fake_component(self.tmp, 1)
        code, out, err = self.driver(["harvest", "--run-dir", self.tmp, "--records-root", root])
        self.assertExitThree(code, out, err, "speaks interface version 1, not 2")

    def test_the_hook_is_ignored_without_the_test_flag(self):
        env = testlib.base_env({testlib.PREFIX + "_TEST_NO_RECORDS": "1"})
        code, out, err = self.driver(["harvest", "--run-dir", self.tmp], env=env)
        self.assertEqual(code, 0, err)


if __name__ == "__main__":
    unittest.main()
