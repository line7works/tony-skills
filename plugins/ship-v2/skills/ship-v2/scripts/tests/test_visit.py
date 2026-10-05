"""CR-21, the trace is the record of every visit (rulings E15-6 and E15-7; contract section 3.4).

`visit` resolves the station the records way (route 3a, then 3b) by allowlist identity, reads its `skill-identity`
through the station's own CLI BEFORE the visit, checks it is the expected v2 sibling (its name, its plugin version,
its resolved root, a known interface version), writes the trace line, and only then hands the executor the visit. A
v1 name, a root under a v1 plugin folder, a link, or an unknown interface version is refused before the visit, and
the refusal is a trace line (`station-refused`). `visit --result` reads the station's own result file from the
visit's run directory, validates it against that station's result schema, refuses a v1 result file (exit 5, nothing
written), and records the terminal status on the trace. The planted v1 roots are tripwires: a manifest that is a
named pipe (an open blocks, and the timeout fails the test) and a script that leaves a marker when run.
"""
import json
import os
import subprocess
import sys
import unittest

import slib
import testlib

testlib.add_scripts_to_path()
from back_core import trace as tracemod  # noqa: E402

V1_BUILD = tracemod.v1_names()[4]           # the v1 build station's name, assembled, never typed


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheVisitIsTraced(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-visit-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)

    def begin(self, tree):
        drive, run_dir = slib.start(self, tree, self.tmp, self.ws)
        slib.through_hook(self, drive, self.tmp, run_dir)
        return drive, run_dir

    def test_the_identity_is_read_and_traced_before_the_executor_gets_the_visit(self):
        tree = slib.Tree(self.tmp)
        drive, run_dir = self.begin(tree)
        code, out, err = drive(["visit", "--run-dir", run_dir, "--station", "build-v2"])
        self.assertEqual(code, 0, (out, err))
        lines = slib.trace(run_dir)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual((line["kind"], line["caller"], line["expected"], line["route"], line["status"]),
                         ("visit", "ship-v2", "build-v2", "3a", "visiting"))
        self.assertEqual(line["identity"]["name"], "build-v2")
        self.assertEqual(line["identity"]["root"], os.path.realpath(os.path.join(tree.root, "build-v2")))
        self.assertEqual(line["identity"]["interface_version"], 1)
        self.assertEqual(line["run_dir"], out["visit_run_dir"])
        self.assertTrue(out["skill_md"].endswith(os.path.join("build-v2", "skills", "build-v2", "SKILL.md")))
        self.assertEqual(out["next"], "visit --result")
        self.assertIn("/build-v2 A", out["summon"])
        self.assertFalse(os.path.exists(out["visit_run_dir"]), "the station's own check-input creates its run")

    def test_the_result_is_validated_and_its_status_traced(self):
        tree = slib.Tree(self.tmp)
        drive, run_dir = self.begin(tree)
        code, out, err = slib.visit(self, drive, run_dir, "build-v2", "completed", self.ws)
        self.assertEqual(code, 0, (out, err))
        lines = slib.trace(run_dir)
        self.assertEqual([(l["kind"], l["status"]) for l in lines], [("visit", "visiting"), ("visit", "completed")])
        self.assertEqual(lines[0]["identity"], lines[1]["identity"])
        self.assertEqual(lines[0]["run_dir"], lines[1]["run_dir"])
        self.assertEqual(out["next"], "visit --station signoff-v2")
        self.assertEqual(slib.validate_trace(run_dir)[0], 0)

    def test_the_stations_are_visited_in_their_order(self):
        tree = slib.Tree(self.tmp)
        drive, run_dir = self.begin(tree)
        for name in ("signoff-v2", "recheck-v2", V1_BUILD, "precon-v2"):
            code, out, err = drive(["visit", "--run-dir", run_dir, "--station", name])
            self.assertEqual(code, 2, (name, out, err))
        self.assertEqual(slib.trace(run_dir), [])

    def refused(self, tree, drive, run_dir, rule):
        code, out, err = drive(["visit", "--run-dir", run_dir, "--station", "build-v2"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "report")
        lines = slib.trace(run_dir)
        self.assertEqual([l["kind"] for l in lines], ["refused"])
        self.assertIn(rule, lines[0]["refusal"]["rules"])
        self.assertEqual(slib.validate_trace(run_dir)[0], 0)
        code, out, err = drive(["visit", "--run-dir", run_dir, "--station", "build-v2"])
        self.assertEqual(code, 2, "a refused station ends the run: no visit follows")
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual(code, 10, (out, err))
        self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "station-refused"))
        return lines[0]

    def test_a_link_to_a_v1_folder_is_refused_before_anything_of_it_is_opened_or_run(self):
        tree = slib.Tree(self.tmp, stations=("signoff-v2", "recheck-v2"))
        v1 = slib.plant_v1(tree.root, V1_BUILD, "build-v2")
        os.symlink(v1, os.path.join(tree.root, "build-v2"))
        drive, run_dir = self.begin(tree)
        try:
            line = self.refused(tree, drive, run_dir, "v1-root")
        except subprocess.TimeoutExpired:
            self.fail("the resolver opened the planted manifest (a named pipe blocked)")
        self.assertIsNone(line["identity"])
        self.assertFalse(slib.ran(v1, "build-v2"), "the planted station's script ran")

    def test_a_folder_whose_manifest_names_a_v1_station_is_refused_without_running_it(self):
        tree = slib.Tree(self.tmp, stations=("signoff-v2", "recheck-v2"))
        root = slib.standin(tree.root, "build-v2", manifest_name=V1_BUILD, marker="V1_RAN")
        drive, run_dir = self.begin(tree)
        line = self.refused(tree, drive, run_dir, "v1-name")
        self.assertFalse(os.path.exists(os.path.join(root, "V1_RAN")), "the station's CLI ran")

    def test_a_station_reporting_a_v1_name_is_refused(self):
        tree = slib.Tree(self.tmp, stations=("signoff-v2", "recheck-v2"))
        slib.standin(tree.root, "build-v2", identity_name=V1_BUILD)
        drive, run_dir = self.begin(tree)
        line = self.refused(tree, drive, run_dir, "v1-name")
        self.assertEqual(line["identity"]["name"], V1_BUILD)

    def test_an_unknown_interface_version_is_refused(self):
        tree = slib.Tree(self.tmp, stations=("signoff-v2", "recheck-v2"))
        slib.standin(tree.root, "build-v2", interface=None)
        drive, run_dir = self.begin(tree)
        line = self.refused(tree, drive, run_dir, "unknown-interface")
        self.assertIsNone(line["identity"]["interface_version"])

    def test_an_installed_v1_version_folder_is_refused(self):
        """The installed shape (route 3b): `<cache>/build-v2/<version>` that is a link into a v1 version folder."""
        cache = os.path.join(self.tmp, "cache", "market")
        os.makedirs(cache)
        tree = slib.Tree(self.tmp, stations=("signoff-v2", "recheck-v2"))
        # the installed shape: <cache>/ship-v2/<version>/ and <cache>/build-v2/<version>/
        version = testlib.load_json(os.path.join(tree.ship, ".claude-plugin", "plugin.json"))["version"]
        installed = os.path.join(cache, "ship-v2", version)
        os.makedirs(os.path.dirname(installed))
        os.rename(tree.ship, installed)
        v1 = slib.plant_v1(os.path.join(cache, V1_BUILD), "0.1.1", "build-v2")
        os.makedirs(os.path.join(cache, "build-v2"))
        os.symlink(v1, os.path.join(cache, "build-v2", "0.1.1"))
        tree.ship = installed
        tree.script = os.path.join(installed, "skills", "ship-v2", "scripts", "ship.py")
        drive, run_dir = self.begin(tree)
        self.refused(tree, drive, run_dir, "v1-root")
        self.assertFalse(slib.ran(v1, "build-v2"))

    def test_the_real_stations_identities(self):
        """Measured on this checkout's real stations (route 3a): build-v2 and signoff-v2 report a known interface
        version; recheck-v2's `skill-identity` reports none (and, run isolated by an interpreter without jsonschema in
        its own site-packages, exits 3 and reports nothing), so under CR-21's rule ship refuses it before any visit
        (the report's frozen-folder request: recheck-v2 is frozen, E15-2)."""
        probe = ("import json, sys\nsys.path.insert(0, sys.argv[1])\nsys.dont_write_bytecode = True\n"
                 "from ship_core import stations\nout = {}\nfor name in ('build-v2', 'signoff-v2', 'recheck-v2'):\n"
                 "    found = stations.resolve(name)\n    ident = stations.identify(name, found)\n"
                 "    out[name] = [(ident or {}).get('interface_version'), sorted(r['rule'] for r in stations.refusals(name, ident))]\n"
                 "print(json.dumps(out))\n")
        proc = subprocess.run([sys.executable, "-c", probe, testlib.SCRIPTS], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=testlib.base_env(), timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = json.loads(proc.stdout.decode())
        self.assertEqual(out["build-v2"], [1, []])
        self.assertEqual(out["signoff-v2"], [1, []])
        self.assertEqual(out["recheck-v2"][0], None)
        self.assertIn(out["recheck-v2"][1], (["unknown-interface"], ["no-identity"]))


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheResultIsTheStationsOwn(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-result-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        self.tree = slib.Tree(self.tmp)
        self.drive, self.run_dir = slib.start(self, self.tree, self.tmp, self.ws)
        slib.through_hook(self, self.drive, self.tmp, self.run_dir)
        code, self.visit, err = self.drive(["visit", "--run-dir", self.run_dir, "--station", "build-v2"])
        self.assertEqual(code, 0, (self.visit, err))

    def refused(self, doc):
        path = slib.put_result(self.visit, doc) if doc is not None else None
        before = (slib.trace(self.run_dir), slib.snapshot(self.ws),
                  testlib.load_json(os.path.join(self.run_dir, "checkpoint.json")))
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        after = (slib.trace(self.run_dir), slib.snapshot(self.ws),
                 testlib.load_json(os.path.join(self.run_dir, "checkpoint.json")))
        self.assertEqual(code, 5, (out, err))
        self.assertEqual(before, after, "a refused result writes nothing")
        return out

    def test_a_v1_result_file_is_refused(self):
        """What a v1 station leaves: its own report block as text, no v2 result document."""
        self.refused({"status": "COMPLETE", "station": V1_BUILD, "report": "BUILD: A"})

    def test_a_result_naming_a_v1_station_is_refused(self):
        doc = slib.station_result("build-v2", "completed", self.visit, self.ws)
        doc["plugin_version"] = "1.4.0"
        out = self.refused(doc)
        self.assertIn("version", out["reason"])

    def test_a_result_of_another_run_is_refused(self):
        doc = slib.station_result("build-v2", "completed", self.visit, self.ws)
        doc["run_id"] = "another-run"
        self.refused(doc)

    def test_a_result_for_another_slice_is_refused(self):
        doc = slib.station_result("build-v2", "completed", self.visit, self.ws, slice_name="B")
        self.refused(doc)

    def test_a_result_that_is_a_link_is_refused(self):
        real = os.path.join(self.tmp, "elsewhere.json")
        testlib.write_json(real, slib.station_result("build-v2", "completed", self.visit, self.ws))
        os.makedirs(self.visit["visit_run_dir"])
        os.symlink(real, os.path.join(self.visit["visit_run_dir"], "result.json"))
        self.refused(None)

    def test_a_station_swapped_during_the_visit_is_refused_and_traced(self):
        slib.put_result(self.visit, slib.station_result("build-v2", "completed", self.visit, self.ws))
        testlib.rmtree(os.path.join(self.tree.root, "build-v2"))
        slib.standin(self.tree.root, "build-v2", identity_name=V1_BUILD)
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "report")
        self.assertEqual([l["kind"] for l in slib.trace(self.run_dir)], ["visit", "refused"])

    def test_no_result_yet_is_a_usage_slip(self):
        code, out, err = self.drive(["visit", "--run-dir", self.run_dir, "--result"])
        self.assertEqual(code, 2, (out, err))


if __name__ == "__main__":
    unittest.main()
