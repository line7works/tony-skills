"""Route 3b: this core's records client, installed, finds the one installed component.

E13 slice 3 (brief 3.4, required test 4). The installed shape is rebuilt under a temporary
directory the way `plugins/records/scripts/tests/test_resolution.py` builds its fake cache: a
harness cache `<cache>/<marketplace>/<plugin>/<version>/`, with this core's client module at its
installed path and a copy of the records component at `<cache>/<marketplace>/records/<V>/`. The
copied client, imported from its installed location with no argument and no RECORDS_ROOT, must
pick route 3b's folder and confirm it; with the component gone it must refuse with the
interface's one line naming route 3b's directory. Standard library only; the component's
`component-identity` needs no jsonschema.

`INSTALLED_SHAPE_CLIENT` points the test at another client file (the mutation proof uses it).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
SKILL = os.path.dirname(SCRIPTS)
CORE = os.path.basename(SKILL)
PLUGIN = os.path.dirname(os.path.dirname(SKILL))
RECORDS = os.path.normpath(os.path.join(PLUGIN, os.pardir, "records"))
PACKAGE = {"build-v2": "build_core", "signoff-v2": "signoff_core"}[CORE]
CLIENT = os.environ.get("INSTALLED_SHAPE_CLIENT") or os.path.join(SCRIPTS, PACKAGE,
                                                                   "records_client.py")
PROBE = """
import json, sys
sys.path.insert(0, sys.argv[1])
from %s import records_client as rcl
try:
    client = rcl.open_client()
except rcl.ComponentUnavailable as refusal:
    print(json.dumps({"refused": str(refusal)}))
else:
    print(json.dumps({"root": client.root, "interface_version": client.interface_version}))
""" % PACKAGE


def records_version():
    with open(os.path.join(RECORDS, ".claude-plugin", "plugin.json")) as handle:
        return json.load(handle)["version"]


class InstalledShapeTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="installed-shape-")
        self.market = os.path.join(self.work, "cache", "one-market")
        scripts = os.path.join(self.market, CORE, "0.1.0", "skills", CORE, "scripts")
        os.makedirs(os.path.join(scripts, PACKAGE))
        open(os.path.join(scripts, PACKAGE, "__init__.py"), "w").close()
        shutil.copyfile(CLIENT, os.path.join(scripts, PACKAGE, "records_client.py"))
        self.scripts = scripts
        self.component = os.path.join(self.market, "records", records_version())
        shutil.copytree(RECORDS, self.component,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def probe(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("RECORDS_ROOT", None)
        proc = subprocess.run([sys.executable, "-c", PROBE, self.scripts], cwd=self.work, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return json.loads(proc.stdout.decode())

    def test_the_installed_client_picks_route_3b_and_confirms_it(self):
        got = self.probe()
        self.assertEqual(os.path.realpath(got.get("root", "")), os.path.realpath(self.component),
                         got)
        self.assertEqual(got["interface_version"], 2)

    def test_with_the_component_gone_the_refusal_names_route_3b(self):
        shutil.rmtree(os.path.join(self.market, "records"))
        got = self.probe()
        refusal = got.get("refused", "")
        self.assertTrue(refusal.startswith("missing dependency: records component (looked in: "),
                        got)
        self.assertIn(os.path.join(self.market, CORE, "0.1.0", os.pardir, os.pardir, "records")
                      + " (no such directory)", refusal)


if __name__ == "__main__":
    unittest.main()
