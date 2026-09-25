"""The phase driver of this core (required test 12), through the real CLI.

`--help` without jsonschema; `identity` and `skill-identity` at `interface_version` 1;
`check-input` on the valid and invalid examples (their absolute paths pointed at temporary
directories); `select` on a fixture for every hunt the core's table names; the four phases a lane
fills stop as `phase-not-built`; `validate-examples.py` green; `validate-result.py` both ways.
Every run is made from a working directory outside the worktree.
"""
import fnmatch
import glob
import importlib.util
import re
import json
import os
import subprocess
import sys
import unittest

import testlib

EXAMPLE_PATHS = {"/tmp/widget-workspace": "ws", "/tmp/widget-staging": "staging",
                 "/tmp/station-runs/run-0001": "run"}


def station_module():
    spec = importlib.util.spec_from_file_location("station_driver_under_test", testlib.DRIVER)
    module = importlib.util.module_from_spec(spec)
    testlib.add_scripts_to_path()
    spec.loader.exec_module(module)
    return module


class _Cli(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("driver-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.cwd = os.path.join(self.tmp, "elsewhere")
        os.makedirs(self.cwd)
        self.ws = testlib.git_workspace(self.tmp, "ws")
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(self.staging)
        self.run_dir = os.path.join(self.tmp, "run")

    def cli(self, args, env=None):
        return testlib.run_driver(args, cwd=self.cwd, env=env)

    def json_out(self, out):
        doc = json.loads(out)
        self.assertEqual(doc["interface_version"], 1)
        return doc

    def localize(self, doc):
        text = json.dumps(doc)
        for example, name in EXAMPLE_PATHS.items():
            text = text.replace(example, os.path.join(self.tmp, name))
        return json.loads(text)

    def checked(self, **extra):
        path = os.path.join(self.tmp, "input.json")
        testlib.write_json(path, testlib.make_input(self.ws, self.run_dir, staging=self.staging, **extra))
        code, out, err = self.cli(["check-input", path])
        self.assertEqual(code, 0, out + err)
        return self.json_out(out)


class Help(_Cli):

    def test_help_without_jsonschema(self):
        stub = testlib.stub_without_jsonschema(self.tmp)
        env = testlib.base_env({"PYTHONPATH": stub})
        code, out, err = self.cli(["--help"], env=env)
        self.assertEqual(code, 0, err)
        for word in ("check-input", "select", "harvest", "record-answer", "write", "report",
                     "identity", "skill-identity", "Exit", "Side effects"):
            self.assertIn(word, out)

    def test_check_input_without_jsonschema_is_exit_3(self):
        stub = testlib.stub_without_jsonschema(self.tmp)
        path = os.path.join(self.tmp, "input.json")
        testlib.write_json(path, testlib.make_input(self.ws, self.run_dir))
        code, out, err = self.cli(["check-input", path], env=testlib.base_env({"PYTHONPATH": stub}))
        self.assertEqual((code, out), (3, ""))
        self.assertEqual(err.strip(), testlib.MISSING_DEPENDENCY)
        self.assertFalse(os.path.exists(self.run_dir))

    def test_the_jsonschema_hook(self):
        path = os.path.join(self.tmp, "input.json")
        testlib.write_json(path, testlib.make_input(self.ws, self.run_dir))
        env = testlib.base_env({testlib.PREFIX + "_TEST": "1", testlib.PREFIX + "_TEST_NO_JSONSCHEMA": "1"})
        code, out, err = self.cli(["check-input", path], env=env)
        self.assertEqual((code, out), (3, ""))

    def test_no_command_is_usage(self):
        code, out, err = self.cli([])
        self.assertEqual(code, 2)


class Identity(_Cli):

    def test_identity(self):
        code, out, err = self.cli(["identity", self.ws])
        self.assertEqual(code, 0, err)
        doc = self.json_out(out)
        self.assertEqual(doc["kind"], "git")
        self.assertEqual(len(doc["head"]), 40)
        plain = os.path.join(self.tmp, "plain")
        os.makedirs(plain)
        doc = self.json_out(self.cli(["identity", plain])[1])
        self.assertEqual((doc["kind"], doc["head"]), ("directory", None))
        self.assertEqual(self.cli(["identity", os.path.join(self.tmp, "missing")])[0], 2)

    def test_skill_identity(self):
        code, out, err = self.cli(["skill-identity"])
        self.assertEqual(code, 0, err)
        doc = self.json_out(out)
        self.assertEqual(doc["name"], testlib.CORE)
        self.assertEqual(doc["version"], testlib.load_json(
            os.path.join(testlib.PLUGIN, ".claude-plugin", "plugin.json"))["version"])
        self.assertEqual(len(doc["content_sha256"]), 64)


class CheckInput(_Cli):

    def test_every_valid_example(self):
        for path in sorted(glob.glob(os.path.join(testlib.EX, "input", "valid", "*.json"))):
            testlib.rmtree(os.path.join(self.tmp, "run"))
            doc = self.localize(testlib.load_json(path))
            target = os.path.join(self.tmp, "input.json")
            testlib.write_json(target, doc)
            code, out, err = self.cli(["check-input", target])
            self.assertEqual(code, 0, "%s: %s%s" % (os.path.basename(path), out, err))
            self.assertEqual(self.json_out(out)["next"], "select")

    def test_every_invalid_example(self):
        for path in sorted(glob.glob(os.path.join(testlib.EX, "input", "invalid", "*.json"))):
            doc = self.localize(testlib.load_json(path))
            target = os.path.join(self.tmp, "input.json")
            testlib.write_json(target, doc)
            code, out, err = self.cli(["check-input", target])
            self.assertEqual(code, 4, "%s: %s%s" % (os.path.basename(path), out, err))
            self.assertFalse(os.path.exists(os.path.join(self.tmp, "run")), path)

    def test_the_path_rules(self):
        inside = os.path.join(self.ws, "run")
        for doc in (testlib.make_input(self.ws, inside),
                    testlib.make_input(self.ws, os.path.join(self.staging, "run"), staging=self.staging),
                    testlib.make_input(os.path.join(self.tmp, "missing"), self.run_dir)):
            path = os.path.join(self.tmp, "input.json")
            testlib.write_json(path, doc)
            code, out, err = self.cli(["check-input", path])
            self.assertEqual(code, 4, out + err)

    def test_a_blank_or_invisible_owner_word_is_refused(self):
        """Inspect's round 2 checker (CS-3): whitespace or invisibles only never authorize a row."""
        for words in ("   ", u"\u200b", u"\ufeff \u3164", "\t\n"):
            path = os.path.join(self.tmp, "input.json")
            testlib.write_json(path, testlib.make_input(self.ws, self.run_dir, staging=self.staging,
                                                        owner_word={"rows": ["gpt-astra"], "words": words}))
            code, out, err = self.cli(["check-input", path])
            self.assertEqual(code, 4, (repr(words), out, err))
            self.assertIn("/owner_word/words", out)
            self.assertFalse(os.path.exists(self.run_dir), "nothing created")

    def test_a_run_directory_already_used(self):
        self.checked()
        path = os.path.join(self.tmp, "input.json")
        code, out, err = self.cli(["check-input", path])
        self.assertEqual(code, 2, out + err)

    def test_a_file_that_is_not_there_or_not_json(self):
        self.assertEqual(self.cli(["check-input", os.path.join(self.tmp, "none.json")])[0], 2)
        bad = os.path.join(self.tmp, "bad.json")
        testlib.write_text(bad, "not json")
        self.assertEqual(self.cli(["check-input", bad])[0], 2)


class Select(_Cli):

    def test_every_hunt_on_an_empty_and_a_one_candidate_fixture(self):
        hunts = station_module().HUNTS
        self.assertTrue(hunts)
        for name, homes in sorted(hunts.items()):
            testlib.rmtree(self.run_dir)
            self.checked()
            code, out, err = self.cli(["select", "--run-dir", self.run_dir, "--hunt", name,
                                       "--name", "widget"])
            self.assertEqual(code, 0, err)
            doc = self.json_out(out)
            self.assertEqual(doc["outcome"], "none", name)
            self.assertEqual(len(doc["searched"]), len(homes))
            first = sorted(homes, key=lambda h: h["tier"])[0]
            root = {"workspace": self.ws, "staging": self.staging}[first["root"]]
            pattern = first["globs"][0].replace("{name}", "widget")
            rel = re.sub(r"\[0-9\]", "0", pattern).replace("*", "2026-09-20")
            self.assertTrue(fnmatch.fnmatchcase(rel, pattern), (name, pattern, rel))
            testlib.write_text(os.path.join(root, rel), "# a doc\n")
            code, out, err = self.cli(["select", "--run-dir", self.run_dir, "--hunt", name,
                                       "--name", "widget"])
            doc = self.json_out(out)
            self.assertEqual((code, doc["outcome"]), (0, "one"), (name, doc))
            self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "selection-%s.json" % name)))
            os.remove(os.path.join(root, rel))

    def test_an_unknown_hunt_and_a_bad_name(self):
        self.checked()
        self.assertEqual(self.cli(["select", "--run-dir", self.run_dir, "--hunt", "nope"])[0], 2)
        hunt = sorted(station_module().HUNTS)[0]
        self.assertEqual(self.cli(["select", "--run-dir", self.run_dir, "--hunt", hunt,
                                   "--name", "../x"])[0], 2)

    def test_select_before_check_input(self):
        os.makedirs(self.run_dir)
        self.assertEqual(self.cli(["select", "--run-dir", self.run_dir])[0], 2)


class NotBuilt(_Cli):
    """The placeholder stop of a phase the lane has not built, keyed to what the driver declares built
    (`HANDLERS`): a built phase never answers `phase-not-built`, and on a run that has only been
    checked it is usage (exit 2, `select` first) or a refusal, never a write: the run directory, the
    workspace and the staging home are digested before and after (CS-3)."""

    def test_the_lane_phases_not_in_handlers_stop_as_phase_not_built(self):
        built = set(getattr(station_module(), "HANDLERS", {}) or {})
        self.checked()
        before = (testlib.tree_digest(self.run_dir), testlib.tree_digest(self.ws), testlib.tree_digest(self.staging))
        answer = os.path.join(self.tmp, "answer.json")
        testlib.write_json(answer, {"questions": [], "lines": []})
        for args in (["harvest"], ["record-answer", "--answer", answer], ["write"], ["report"]):
            code, out, err = self.cli(args + ["--run-dir", self.run_dir])
            if args[0] in built:
                self.assertNotIn("phase-not-built", out, args)
                self.assertIn(code, (2, 4, 5, 10), (args, out, err))
                if code == 10:
                    doc = self.json_out(out)
                    self.assertEqual(doc["status"], "stopped", args)
                    self.assertNotEqual(doc.get("stop_tag"), "phase-not-built", args)
                continue
            self.assertEqual(code, 10, args)
            doc = self.json_out(out)
            self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "phase-not-built"), args)
            self.assertIn(args[0], doc["reason"])
        after = (testlib.tree_digest(self.run_dir), testlib.tree_digest(self.ws), testlib.tree_digest(self.staging))
        self.assertEqual(after, before, "nothing written: the run directory, the workspace and the staging home unchanged")

    def test_the_placeholder_itself(self):
        """`driver.not_built(phase)` in-process: the document shape every core's unbuilt phase answers with."""
        testlib.add_scripts_to_path()
        from station_core import driver as drivermod
        captured = {}

        class Ctx(object):
            station = testlib.CORE

            def envelope(self, **fields):
                fields.update({"interface_version": 1, "station": self.station})
                return fields

        class Args(object):
            run_dir = "/tmp/never-opened"

        real_emit = drivermod.emit
        drivermod.emit = lambda document, code=0: captured.update(document=document, code=code) or code
        try:
            code = drivermod.not_built("write")(Ctx(), Args())
        finally:
            drivermod.emit = real_emit
        self.assertEqual(code, 10)
        doc = captured["document"]
        self.assertEqual((doc["status"], doc["stop_tag"], doc["next"]), ("stopped", "phase-not-built", "done"))
        self.assertIn("`write`", doc["reason"])
        self.assertIn(testlib.CORE, doc["reason"])


class OwnCommands(_Cli):
    """The seam of station-loop.md 3.8: a core's own commands through `main(..., commands=)`."""

    def own_driver(self, commands_source):
        path = os.path.join(self.tmp, "own.py")
        testlib.write_text(path, "\n".join([
            "import os, sys",
            "sys.dont_write_bytecode = True",
            "sys.path.insert(0, %r)" % testlib.SCRIPTS,
            "from station_core import driver",
            "def show(ctx, args):",
            "    return driver.emit(ctx.envelope(ok=True, shown=args.thing, run_dir=args.run_dir))",
            "COMMANDS = %s" % commands_source,
            "sys.exit(driver.main('%s', {'scope': [{'home': 'repo-scope', 'root': 'workspace',"
            " 'globs': ['docs/scope/*-{name}.md'], 'tier': 1}]}, {}, commands=COMMANDS))" % testlib.CORE,
        ]))
        return path

    def run_own(self, path, args):
        env = testlib.base_env()
        proc = subprocess.run([sys.executable, path] + args + ["--skill-root", testlib.SKILL],
                              cwd=self.cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.returncode, proc.stdout.decode(), proc.stderr.decode()

    def test_an_own_command_is_listed_and_dispatched(self):
        path = self.own_driver("[{'name': 'show-thing', 'help': 'show the thing',"
                               " 'arguments': [{'flags': ['--run-dir'], 'metavar': 'D', 'required': True},"
                               " {'flags': ['--thing'], 'default': 'x'}], 'handler': show}]")
        code, out, err = self.run_own(path, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("Commands of this core", out)
        self.assertIn("show-thing", out)
        code, out, err = self.run_own(path, ["show-thing", "--run-dir", self.run_dir, "--thing", "y"])
        self.assertEqual(code, 0, err)
        doc = self.json_out(out)
        self.assertEqual((doc["ok"], doc["shown"], doc["run_dir"]), (True, "y", self.run_dir))
        code, out, err = self.run_own(path, ["show-thing"])
        self.assertEqual(code, 2, "a missing required argument is usage")

    def test_a_shared_name_or_a_missing_field_is_a_defect_of_the_script(self):
        for source in ("[{'name': 'select', 'help': 'h', 'arguments': [], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'metavar': 'X'}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--skill-root']}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['thing']}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [], 'handler': 'show'}]",
                       "[{'name': '', 'help': 'h', 'arguments': [], 'handler': show}]",
                       "[{'name': 'two words', 'help': 'h', 'arguments': [], 'handler': show}]",
                       "[{'name': 'Thing', 'help': 'h', 'arguments': [], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': None, 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--command']}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['-c'], 'dest': 'skill_root'}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--a']}, {'flags': ['--a']}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--a'], 'colour': 'red'}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': 5}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--a'], 'action': 'store_true', 'metavar': 'X'}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--a'], 'dest': 5}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--a'], 'action': 'store_const'}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--a'], 'action': 'append_const'}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--a'], 'help': 5}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': ['--a'], 'action': 'help', 'metavar': 'X'}], 'handler': show}]",
                       "[{'name': 'thing', 'help': 'h', 'arguments': [{'flags': [['--x']]}], 'handler': show}]"):
            path = self.own_driver(source)
            code, out, err = self.run_own(path, ["--help"])
            self.assertNotEqual(code, 0, source)
            self.assertIn("ValueError", err, source)

    def test_no_own_commands_lists_none(self):
        path = self.own_driver("[]")
        code, out, err = self.run_own(path, ["--help"])
        self.assertEqual(code, 0, err)
        self.assertIn("Commands of this core", out)
        self.assertIn("  (none)", out)
        self.assertIn("own commands    the lane contract's", out)

    def test_a_bad_handlers_table_is_a_defect(self):
        for handlers, word in (("{'harvst': lambda ctx, args: 0}", "harvst"),
                               ("{'harvest': 'phase_harvest'}", "not callable"),
                               ("['harvest']", "mapping")):
            path = os.path.join(self.tmp, "bad.py")
            testlib.write_text(path, "\n".join([
                "import os, sys",
                "sys.dont_write_bytecode = True",
                "sys.path.insert(0, %r)" % testlib.SCRIPTS,
                "from station_core import driver",
                "sys.exit(driver.main(%r, {}, %s))" % (testlib.CORE, handlers)]))
            code, out, err = self.run_own(path, ["--help"])
            self.assertNotEqual(code, 0, handlers)
            self.assertIn(word, err, handlers)


class Validators(_Cli):

    def test_validate_examples_is_green(self):
        code, out, err = testlib.run_script("validate-examples.py", [], cwd=self.cwd)
        self.assertEqual(code, 0, out + err)
        self.assertTrue(json.loads(out)["ok"])

    def test_validate_result_both_ways(self):
        for path in sorted(glob.glob(os.path.join(testlib.EX, "result", "valid", "*.json"))):
            code, out, err = testlib.run_script("validate-result.py", [path], cwd=self.cwd)
            self.assertEqual(code, 0, "%s: %s%s" % (path, out, err))
        for path in sorted(glob.glob(os.path.join(testlib.EX, "result", "invalid", "*.json"))):
            code, out, err = testlib.run_script("validate-result.py", [path], cwd=self.cwd)
            self.assertEqual(code, 4, "%s: %s%s" % (path, out, err))


if __name__ == "__main__":
    unittest.main()
