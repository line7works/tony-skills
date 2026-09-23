"""E13 slice 1, brief 3.1: reaching the records component.

The resolver snippet is copied from the component's `references/interface.md` unchanged (a drift
test proves it), the pick is confirmed with `component-identity`, and every command the pilot
uses is one function that binds caller values as argv items and never as shell text. A missing
component, or one speaking another interface version, is the pilot's exit 3 shape: one line on
stderr, nothing on stdout.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

import testlib

testlib.add_scripts_to_path()
from recheck_core import records_client as rc  # noqa: E402

RECORDS = os.path.join(testlib.PLUGIN, os.pardir, "records")
INTERFACE = os.path.normpath(os.path.join(RECORDS, "references", "interface.md"))


def stub_component(root, version, body=None, manifest_version="9.9.9"):
    """A fake component root: plugin.json plus a scripts/records.py that prints what it is told."""
    os.makedirs(os.path.join(root, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(root, ".claude-plugin"), exist_ok=True)
    with open(os.path.join(root, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "records", "version": manifest_version}, fh)
    if body is None:
        body = ('import json, sys\n'
                'sys.stdout.write(json.dumps({"ok": True, "interface_version": %s,\n'
                '    "component_version": "9.9.9", "name": "records"}) + "\\n")\n' % version)
    with open(os.path.join(root, "scripts", "records.py"), "w", encoding="utf-8") as fh:
        fh.write(body)
    return root


class Snippet(unittest.TestCase):
    """The copied resolver is the interface's, byte for byte."""

    def test_interface_snippet_is_copied_unchanged(self):
        with open(INTERFACE, "r", encoding="utf-8") as fh:
            text = fh.read()
        marker = "<!-- resolver: python -->"
        self.assertIn(marker, text)
        block = text.split(marker, 1)[1].split("```python", 1)[1].split("\n```", 1)[0]
        want = rc.snippet_region(block)
        with open(rc.__file__.replace(".pyc", ".py"), "r", encoding="utf-8") as fh:
            mine = fh.read()
        self.assertIn(rc.SNIPPET_BEGIN, mine)
        got = mine.split(rc.SNIPPET_BEGIN, 1)[1].split(rc.SNIPPET_END, 1)[0]
        self.assertEqual(want.strip("\n"), got.strip("\n"))


class Resolution(unittest.TestCase):
    def setUp(self):
        self.dir = testlib.make_scratch("e13-records-client-")
        self.addCleanup(testlib.rmtree, self.dir)

    def test_argument_then_environment_then_beside(self):
        a = stub_component(os.path.join(self.dir, "a"), 1)
        b = stub_component(os.path.join(self.dir, "b"), 1)
        self.assertEqual(rc.records_root(a, None, {}), a)
        self.assertEqual(rc.records_root(None, None, {"RECORDS_ROOT": b}), b)
        station = os.path.join(self.dir, "plugins", "recheck-v2")
        os.makedirs(station)
        stub_component(os.path.join(self.dir, "plugins", "records"), 1)
        got = rc.records_root(None, station, {})
        self.assertTrue(os.path.isfile(os.path.join(got, "scripts", "records.py")))

    def test_installed_shape_picks_the_highest_dotted_version(self):
        station = os.path.join(self.dir, "cache", "mkt", "recheck-v2", "0.2.0")
        os.makedirs(station)
        base = os.path.join(self.dir, "cache", "mkt", "records")
        for name in ("0.9.0", "0.10.0", "01.0"):
            stub_component(os.path.join(base, name), 1, manifest_version=name)
        got = rc.records_root(None, station, {})
        self.assertEqual(os.path.basename(os.path.normpath(got)), "0.10.0")

    def test_nothing_found_names_every_candidate(self):
        station = os.path.join(self.dir, "lonely")
        os.makedirs(station)
        with self.assertRaises(LookupError) as caught:
            rc.records_root(None, station, {})
        message = str(caught.exception)
        self.assertTrue(message.startswith("missing dependency: records component (looked in: "))
        self.assertIn("no such directory", message)

    def test_confirm_refuses_another_interface_version(self):
        """F10 (E13 amendment A7): the pilot speaks records interface version 2, so a component
        at version 1 is refused and the refusal says so."""
        one = stub_component(os.path.join(self.dir, "one"), 1)
        with self.assertRaises(LookupError) as caught:
            rc.confirm_interface(one, list(rc.KNOWN_INTERFACE_VERSIONS), python=testlib.GEN_PYTHON)
        self.assertIn("speaks interface version 1, not 2", str(caught.exception))

    def test_confirm_refuses_a_component_that_reports_nothing(self):
        mute = stub_component(os.path.join(self.dir, "mute"), 1, body="import sys\nsys.exit(1)\n")
        with self.assertRaises(LookupError) as caught:
            rc.confirm_interface(mute, [1], python=testlib.GEN_PYTHON)
        self.assertIn("did not report an interface version", str(caught.exception))

    def test_open_client_confirms_the_real_component(self):
        client = rc.open_client(records_root=os.path.normpath(RECORDS))
        self.assertEqual(client.interface_version, 2)  # F10, E13 amendment A7


class Commands(unittest.TestCase):
    """One function per CLI command the pilot uses, over a real fixture workspace."""

    DOC = "docs/plans/2026-09-18-widget-export.md"

    def setUp(self):
        self.dir = testlib.make_scratch("e13-records-cmds-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case("F1-fixed-defect", "F1-01-fixed-clean", self.dir)
        self.workspace = os.path.join(self.case, "workspace")
        self.doc = self.DOC
        self.client = rc.open_client(records_root=os.path.normpath(RECORDS))

    def one_event(self, finding, identity):
        return {"v": 1, "kind": "disposition", "at": "2026-09-20T09:00:00Z", "ledger_doc": self.doc,
                "actor": {"station": "recheck-v2", "run_id": "probe-run", "harness": "test-harness"},
                "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
                "finding": finding, "disposition": "fixed", "how": "executed ran the scenario command",
                "verified_source": {"known": True, "identity": identity}, "join_basis": None}

    def test_verify_of_a_document_with_no_log_is_clean(self):
        out = self.client.verify(self.workspace, self.doc)
        self.assertFalse(out["exists"])
        self.assertEqual(out["head"], "0" * 64)

    def test_import_then_state_then_append_then_render(self):
        rep = self.client.import_legacy(self.workspace, self.doc)
        self.assertEqual(rep["ambiguous"], 0)
        state = self.client.state(self.workspace, self.doc)
        self.assertEqual(state["counts"]["open"], 1)
        identity = self.client.identity(self.workspace)["identity"]
        event = self.one_event(state["findings"][0]["id"], identity)
        out = self.client.append(self.workspace, self.doc, [event], state["head"], self.dir)
        self.assertEqual(out["appended"][0]["kind"], "disposition")
        rendered = self.client.render(self.workspace, self.doc, "probe-run")
        self.assertIn("### 2026-09-20 — recheck: Slice A", rendered["block"])
        self.assertIn("· fixed ·", rendered["block"])

    def test_a_head_that_moved_is_exit_7(self):
        self.client.import_legacy(self.workspace, self.doc)
        state = self.client.state(self.workspace, self.doc)
        identity = self.client.identity(self.workspace)["identity"]
        event = self.one_event(state["findings"][0]["id"], identity)
        with self.assertRaises(rc.RecordsRefusal) as caught:
            self.client.append(self.workspace, self.doc, [event], "f" * 64, self.dir)
        self.assertEqual(caught.exception.exit_code, 7)
        self.assertEqual(caught.exception.error, "conflict")

    def test_a_clear_against_another_source_is_exit_6(self):
        self.client.import_legacy(self.workspace, self.doc)
        state = self.client.state(self.workspace, self.doc)
        identity = dict(self.client.identity(self.workspace)["identity"])
        identity["commit"] = "0" * 40
        event = self.one_event(state["findings"][0]["id"], identity)
        with self.assertRaises(rc.RecordsRefusal) as caught:
            self.client.append(self.workspace, self.doc, [event], state["head"], self.dir)
        self.assertEqual(caught.exception.exit_code, 6)
        self.assertEqual(caught.exception.error, "stale_source")

    def test_values_are_argv_items_never_shell_text(self):
        """A document name carrying shell metacharacters reaches the component as one argument."""
        sentinel = os.path.join(self.dir, "pwned")
        name = "docs/plans/$(touch %s).md" % sentinel
        out = self.client.verify(self.workspace, name)
        self.assertFalse(os.path.exists(sentinel))
        self.assertEqual(out["spec"]["doc"], name)


class DriverExitThree(unittest.TestCase):
    """3.1: the pilot stops with exit 3 and a plain message when the component is missing."""

    def setUp(self):
        self.dir = testlib.make_scratch("e13-records-exit3-")
        self.addCleanup(testlib.rmtree, self.dir)

    def run_cli(self, *args, **kwargs):
        env = dict(os.environ)
        env.update(kwargs.get("env") or {})
        return testlib.run_script("recheck.py", list(args), cwd=self.dir, env=env)

    def test_help_works_without_the_component(self):
        code, out, err = self.run_cli("--help", env={"RECORDS_ROOT": os.path.join(self.dir, "nowhere"),
                                                     "RECHECK_TEST": "1", "RECHECK_TEST_NO_RECORDS": "1"})
        self.assertEqual(code, 0)
        self.assertIn("recheck.py", out)

    def test_argument_checking_works_without_the_component(self):
        code, out, err = self.run_cli("record", env={"RECHECK_TEST": "1", "RECHECK_TEST_NO_RECORDS": "1"})
        self.assertEqual(code, 2)

    def test_missing_component_is_exit_3_with_nothing_on_stdout(self):
        case = testlib.build_case("F1-fixed-defect", "F1-01-fixed-clean", self.dir)
        testlib.prepare_input(case)
        code, out, err = self.run_cli("start", os.path.join(case, "input.json"),
                                      env={"RECHECK_TEST": "1", "RECHECK_TEST_NO_RECORDS": "1"})
        self.assertEqual(code, 3)
        self.assertEqual(out.strip(), "")
        self.assertIn("missing dependency: records component", err)
        self.assertFalse(os.path.exists(os.path.join(case, "run", "checkpoint.json")))

    def test_another_interface_version_is_exit_3(self):
        """F10 (E13 amendment A7): a component still at records interface version 1 is exit 3."""
        case = testlib.build_case("F1-fixed-defect", "F1-01-fixed-clean", self.dir)
        testlib.prepare_input(case)
        one = stub_component(os.path.join(self.dir, "one"), 1)
        code, out, err = self.run_cli("--records-root", one, "start", os.path.join(case, "input.json"))
        self.assertEqual(code, 3)
        self.assertEqual(out.strip(), "")
        self.assertIn("speaks interface version 1, not 2", err)
        self.assertFalse(os.path.exists(os.path.join(case, "run", "checkpoint.json")))


if __name__ == "__main__":
    unittest.main()
