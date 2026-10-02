"""The station trace (ruling E15-7): `back_core/trace.py`, `references/trace.schema.json` and
`scripts/validate-trace.py`, shared by the three back cores (`references/back-files.txt`).

A trace line names a station visit or a reader summons with the identity the station's own CLI
returned, the route that resolved it (3a or 3b), the run directory the visit used and its terminal
status; a `refused` line names a station refused before the visit. The refusal rule: a v1 name, a name
without `-v2` where a v2 station is expected, a root under a v1 plugin folder (the checkout shape
`plugins/<v1>/` or the installed shape `<v1>/<version>/`), or an interface version the caller does
not know. The module writes and reads the file; it never launches anything.
"""
import json
import os
import subprocess
import sys
import unittest

import testlib

testlib.add_scripts_to_path()

from back_core import trace  # noqa: E402
from station_core import validate  # noqa: E402

V1 = ("pre" + "con", "archi" + "tect", "blue" + "print", "in" + "spect", "bu" + "ild", "sign" + "off",
      "re" + "check", "verti" + "cal", "hand" + "off", "sh" + "ip")
SCHEMA = os.path.join(testlib.REF, "trace.schema.json")
VALIDATOR = "validate-trace.py"
HAS_JSONSCHEMA = not validate.jsonschema_unavailable("TRACE_TEST")


def identity(name="build-v2", root="/tmp/plugins/build-v2", version="0.1.0", interface=1):
    return {"name": name, "version": version, "root": root, "interface_version": interface,
            "commit": None, "content_sha256": None}


class TheV1Names(unittest.TestCase):

    def test_the_ten_v1_names_are_assembled_at_run_time(self):
        self.assertEqual(sorted(trace.v1_names()), sorted(V1))


class TheRefusalRule(unittest.TestCase):

    def rules(self, expected, ident, known=(1,)):
        return sorted(r["rule"] for r in trace.refusals(expected, ident, known))

    def test_a_v2_sibling_in_the_checkout_and_the_installed_shape_passes(self):
        self.assertEqual(self.rules("build-v2", identity()), [])
        self.assertEqual(self.rules("build-v2", identity(root="/h/config/plugins/cache/m/build-v2/0.1.0")), [])
        self.assertEqual(self.rules("readers", identity("readers", "/tmp/plugins/readers", "1.0.1")), [])

    def test_a_v1_name_is_refused(self):
        for name in V1:
            got = self.rules(name + "-v2", identity(name, "/tmp/plugins/%s-v2" % name))
            self.assertIn("v1-name", got, name)

    def test_a_name_without_v2_where_a_v2_station_is_expected(self):
        got = self.rules("signoff-v2", identity("signoff-old", "/tmp/plugins/signoff-v2"))
        self.assertIn("v1-name", got)
        self.assertIn("name-mismatch", got)

    def test_another_v2_name_is_a_mismatch(self):
        self.assertEqual(self.rules("build-v2", identity("signoff-v2", "/tmp/plugins/signoff-v2")), ["name-mismatch"])

    def test_a_root_under_each_v1_plugin_folder_is_refused(self):
        for name in V1:
            for root in ("/repo/plugins/%s" % name, "/repo/plugins/%s/skills" % name,
                         "/h/config/plugins/cache/m/%s/1.0.0" % name, "/h/codex/plugins/cache/m/%s/0.3.10" % name):
                self.assertIn("v1-root", self.rules("build-v2", identity(root=root)), root)

    def test_a_v1_word_elsewhere_in_a_path_is_not_a_v1_root(self):
        self.assertEqual(self.rules("build-v2", identity(root="/home/someone/build/plugins/build-v2")), [])
        self.assertEqual(self.rules("build-v2", identity(root="/srv/ship/cache/m/build-v2/0.1.0")), [])

    def test_an_unknown_interface_version_is_refused(self):
        self.assertEqual(self.rules("build-v2", identity(interface=2)), ["unknown-interface"])
        self.assertEqual(self.rules("build-v2", identity(interface=None)), ["unknown-interface"])
        self.assertEqual(self.rules("build-v2", identity(interface=2), known=(1, 2)), [])

    def test_a_missing_identity_is_refused(self):
        self.assertEqual(self.rules("build-v2", None), ["no-identity"])


class _Run(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("trace-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.run_dir = os.path.join(self.tmp, "run")
        os.makedirs(self.run_dir)

    def summons(self, **over):
        fields = dict(kind="summons", caller="vertical-v2", expected="readers",
                      identity=identity("readers", "/tmp/plugins/readers", "1.0.1"), route="3a",
                      run_dir=os.path.join(self.run_dir, "readers"), status="ok", call_id="r1-local-spec",
                      row="claude-session", at="2026-10-01T12:00:00Z")
        fields.update(over)
        return trace.line(**fields)


class TheLineShapes(_Run):

    def test_a_summons_a_visit_and_a_refused_line_are_well_formed(self):
        lines = [self.summons(),
                 trace.line(kind="visit", caller="ship-v2", expected="build-v2", identity=identity(), route="3b",
                            run_dir="/tmp/runs/build-1", status="completed", at="2026-10-01T12:00:00Z"),
                 trace.line(kind="refused", caller="ship-v2", expected="build-v2",
                            identity=identity("build", "/repo/plugins/build"), route="3a", run_dir="/tmp/runs/build-2",
                            refusal={"rules": ["v1-name", "v1-root"], "reason": "a v1 station"},
                            at="2026-10-01T12:00:00Z")]
        for one in lines:
            self.assertEqual(trace.check_line(one), [], one)

    def test_each_kind_forbids_the_others_fields(self):
        bad = self.summons()
        bad["refusal"] = {"rules": ["v1-name"], "reason": "x"}
        self.assertTrue(trace.check_line(bad))
        bad = self.summons()
        del bad["call_id"]
        self.assertTrue(trace.check_line(bad))
        visit = trace.line(kind="visit", caller="ship-v2", expected="build-v2", identity=identity(), route="3a",
                           run_dir="/tmp/r", status="completed", at="2026-10-01T12:00:00Z")
        visit["row"] = "claude-session"
        self.assertTrue(trace.check_line(visit))

    def test_a_refused_line_needs_its_rules(self):
        refused = trace.line(kind="refused", caller="ship-v2", expected="build-v2", identity=None, route=None,
                             run_dir="/tmp/r", refusal={"rules": [], "reason": "x"}, at="2026-10-01T12:00:00Z")
        self.assertTrue(trace.check_line(refused))

    def test_an_unknown_key_kind_or_route_is_refused(self):
        for key, value in (("extra", 1), ("kind", "call"), ("route", "3c"), ("trace_version", 2)):
            bad = self.summons()
            bad[key] = value
            self.assertTrue(trace.check_line(bad), key)


@unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema is not importable here: the schema checks run under uv run")
class TheSchema(_Run):

    def schema(self):
        with open(SCHEMA, encoding="utf-8") as fh:
            return json.load(fh)

    def test_good_lines_validate_and_bad_lines_do_not(self):
        good = dict(self.summons(), seq=0)
        self.assertEqual(validate.errors_for(good, self.schema()), [])
        for key, value in (("extra", 1), ("kind", "call"), ("seq", -1), ("status", "")):
            bad = dict(good)
            bad[key] = value
            self.assertTrue(validate.errors_for(bad, self.schema()), key)
        bad = dict(good)
        bad["identity"] = dict(good["identity"], plugin="x")
        self.assertTrue(validate.errors_for(bad, self.schema()), "the identity is closed")

    def test_the_schema_is_closed_at_every_level(self):
        def walk(node, where):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(node.get("additionalProperties"), False, where)
                for key, value in node.items():
                    walk(value, where + "/" + str(key))
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, "%s/%d" % (where, index))
        walk(self.schema(), "")


@unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema is not importable here: appends are schema-checked under uv run")
class TheFile(_Run):

    def test_append_numbers_the_lines_and_read_gives_them_back(self):
        trace.append(self.run_dir, self.summons(), testlib.SKILL)
        trace.append(self.run_dir, self.summons(call_id="r1-local-seams"), testlib.SKILL)
        lines = trace.read(self.run_dir)
        self.assertEqual([l["seq"] for l in lines], [0, 1])
        self.assertEqual([l["call_id"] for l in lines], ["r1-local-spec", "r1-local-seams"])

    def test_append_refuses_a_bad_line_and_writes_nothing(self):
        bad = self.summons()
        bad["extra"] = 1
        with self.assertRaises(trace.TraceError):
            trace.append(self.run_dir, bad, testlib.SKILL)
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, trace.FILE)))

    def test_read_refuses_a_broken_sequence(self):
        trace.append(self.run_dir, self.summons(), testlib.SKILL)
        path = os.path.join(self.run_dir, trace.FILE)
        with open(path, encoding="utf-8") as fh:
            one = json.loads(fh.readline())
        one["seq"] = 5
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(one) + "\n")
        with self.assertRaises(trace.TraceError):
            trace.read(self.run_dir)

    def test_an_absent_file_reads_as_no_lines(self):
        self.assertEqual(trace.read(self.run_dir), [])

    def test_the_validator_passes_a_good_file_and_fails_a_bad_one(self):
        trace.append(self.run_dir, self.summons(), testlib.SKILL)
        path = os.path.join(self.run_dir, trace.FILE)
        code, out, err = testlib.run_script(VALIDATOR, [path])
        self.assertEqual(code, 0, out + err)
        self.assertTrue(json.loads(out)["ok"])
        with open(path, "a", encoding="utf-8") as fh:
            fh.write('{"trace_version": 1, "seq": 1, "kind": "summons"}\n')
        code, out, err = testlib.run_script(VALIDATOR, [path])
        self.assertEqual(code, 4, out + err)
        report = json.loads(out)
        self.assertFalse(report["ok"])
        self.assertEqual(set(f["line"] for f in report["findings"]), {2})

    def test_the_validator_names_a_v1_identity_in_a_visit(self):
        line = trace.line(kind="visit", caller="ship-v2", expected="build-v2", identity=identity("build", "/repo/plugins/build"),
                          route="3a", run_dir="/tmp/r", status="completed", at="2026-10-01T12:00:00Z")
        path = os.path.join(self.tmp, "t.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(line, seq=0)) + "\n")
        code, out, err = testlib.run_script(VALIDATOR, [path])
        self.assertEqual(code, 4, out + err)
        self.assertIn("v1-name", out)


class TheValidatorInterface(unittest.TestCase):

    def test_help_and_usage_work_without_jsonschema(self):
        code, out, err = testlib.run_script(VALIDATOR, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("exit", out.lower())
        code, out, err = testlib.run_script(VALIDATOR, ["/no/such/trace.jsonl"])
        self.assertEqual(code, 2, out + err)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
