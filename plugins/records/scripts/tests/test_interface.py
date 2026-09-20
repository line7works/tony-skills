"""The A7a interface tests, and the coverage rule that holds `interface.md` to the code.

Contract section 13, slice 3: "Every command from another working directory, with an invalid
argument (exit 2), with a missing input file, and without `jsonschema` (exit 3). ...
`interface.md` names every command, field, and exit code the code has, checked by a test that
reads both. The frozen-pilot check of E12-2."

The coverage rule, in both directions:

- FORWARD, per command and strict: every field path a real run of that command returns is named
  in `interface.md`, in that command's own table or in one of the two inherited tables
  ("Every response", "Every command that walks a log").
- REVERSE: every field a command's OWN table names is returned by some run of that command, and
  every field an inherited table names is returned by some run of one of the commands that table
  covers. A command's own table can therefore carry no ghost, and an inherited field does not
  have to be provoked on all six commands to be documented once.

A table row may name `X.*`, which says "this node's keys are data, or it is described somewhere
else" (an event line, a map keyed by event kind). The walk stops there, so the document decides
where description stops rather than the walk.

`interface_cases.py` builds every response once for the whole module; it drives the real CLI, so
nothing here is hand-written.
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

import testlib
import interface_cases

testlib.add_scripts_to_path()

import records  # noqa: E402

INTERFACE = os.path.join(testlib.REFERENCES, "interface.md")
COMMON_HEADING = "Every response"
WALK_HEADING = "Every command that walks a log"
LOCK_HEADING = "Every command that takes the lock"
WALKS_A_LOG = ("verify", "events", "append", "state", "render", "import-legacy")
TAKES_THE_LOCK = ("append", "import-legacy")
GROUPS = ((COMMON_HEADING, tuple(sorted(("verify", "events", "identity", "append",
                                         "component-identity", "state", "render",
                                         "import-legacy", "mirrors", "survey")))),
          (WALK_HEADING, WALKS_A_LOG),
          (LOCK_HEADING, TAKES_THE_LOCK))
EXIT_CODES = ("0", "1", "2", "3", "4", "5", "6", "7")
FIXTURE_DOC = interface_cases.FIXTURE_DOC

_STATE = {}


def setUpModule():
    _STATE["scratch"] = testlib.make_scratch("records-interface-")
    _STATE["cases"] = interface_cases.every_case(_STATE["scratch"])
    with open(INTERFACE, encoding="utf-8") as fh:
        _STATE["text"] = fh.read()


def tearDownModule():
    testlib.rmtree(_STATE.get("scratch") or "")


def document_text():
    return _STATE["text"]


def cases():
    return _STATE["cases"]


# ---- reading interface.md ----------------------------------------------------------------------

def sections(text):
    """{heading title: its lines} for every `##` and `###` heading, in file order."""
    out = {}
    title = None
    for line in text.split("\n"):
        heading = re.match(r"^#{2,3} (.+?)\s*$", line)
        if heading:
            title = heading.group(1).strip().strip("`")
            out.setdefault(title, [])
            continue
        if title is not None:
            out[title].append(line)
    return out


def field_rows(lines):
    """Every field path named in a table whose first column header is `Field`."""
    out = []
    inside = False
    for line in lines:
        if re.match(r"^\|\s*Field\s*\|", line):
            inside = True
            continue
        if not inside:
            continue
        if not line.startswith("|"):
            inside = False
            continue
        if re.match(r"^\|\s*-+", line):
            continue
        cell = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if cell:
            out.append(cell.group(1))
    return out


def documented():
    """(own fields per command, everything documented per command, the inherited groups)."""
    parsed = sections(document_text())
    groups = [(heading, commands, field_rows(parsed.get(heading, [])))
              for heading, commands in GROUPS]
    own = dict((command, field_rows(parsed.get(command, []))) for command in records.COMMANDS)
    full = {}
    for command, fields in own.items():
        every = set(fields)
        for _, commands, rows in groups:
            if command in commands:
                every |= set(rows)
        full[command] = every
    return own, full, groups


def observed():
    """{command: the field paths its real runs returned}, with the document's stops honoured."""
    _, full, _ = documented()
    out = {}
    for case in cases():
        if case["body"] is None:
            continue
        stops = set(f for f in full.get(case["command"], ()) if f.endswith(".*"))
        out.setdefault(case["command"], set()).update(
            interface_cases.field_paths(case["body"], stops))
    return out


# ---- the coverage rule --------------------------------------------------------------------------

class InterfaceMdNamesWhatTheCodeReturns(unittest.TestCase):
    def test_every_field_a_command_returns_is_documented(self):
        own, full, _ = documented()
        missing = {}
        for command, paths in sorted(observed().items()):
            gap = sorted(p for p in paths if p not in full[command])
            if gap:
                missing[command] = gap
        self.assertEqual(missing, {},
                         "references/interface.md does not name these response fields")

    def test_every_field_a_commands_own_table_names_is_returned(self):
        own, _, _ = documented()
        seen = observed()
        ghosts = {}
        for command, fields in sorted(own.items()):
            gap = sorted(f for f in fields if f not in seen.get(command, ()))
            if gap:
                ghosts[command] = gap
        self.assertEqual(ghosts, {},
                         "references/interface.md names fields no run of that command returns")

    def test_every_inherited_field_is_returned_by_a_command_it_covers(self):
        _, _, groups = documented()
        seen = observed()
        ghosts = {}
        for heading, commands, rows in groups:
            covered = set()
            for command in commands:
                covered |= seen.get(command, set())
            gap = sorted(f for f in rows if f not in covered)
            if gap:
                ghosts[heading] = gap
        self.assertEqual(ghosts, {},
                         "an inherited table names a field none of its commands returns")

    def test_each_command_has_its_own_section_and_a_field_table(self):
        own, _, _ = documented()
        for command in sorted(records.COMMANDS):
            self.assertTrue(own[command], "interface.md has no field table for %s" % command)

    def test_the_three_inherited_tables_are_there(self):
        _, _, groups = documented()
        rows = dict((heading, fields) for heading, _, fields in groups)
        self.assertEqual(sorted(rows[COMMON_HEADING]),
                         ["component_version", "interface_version", "ok"])
        self.assertIn("error", rows[WALK_HEADING])
        self.assertIn("reason", rows[WALK_HEADING])
        self.assertIn("lock", rows[LOCK_HEADING])
        self.assertIn("holder_alive", rows[LOCK_HEADING])


class InterfaceMdNamesEveryCommandAndArgument(unittest.TestCase):
    def test_every_command_is_named(self):
        text = document_text()
        for command in sorted(records.COMMANDS):
            self.assertIn("### `%s`" % command, text, command)

    def test_the_document_names_no_command_the_cli_does_not_have(self):
        headings = set(re.findall(r"^### `([a-z-]+)`", document_text(), re.M))
        self.assertEqual(sorted(headings - set(records.COMMANDS)), [])

    def test_every_argument_of_every_command_is_named_in_its_section(self):
        parsed = sections(document_text())
        subparsers = [a for a in records.build_parser()._actions
                      if isinstance(a, argparse._SubParsersAction)]
        self.assertEqual(len(subparsers), 1)
        for command, parser in sorted(subparsers[0].choices.items()):
            body = "\n".join(parsed[command]) + "\n".join(parsed["Arguments every command takes"])
            for action in parser._actions:
                for option in action.option_strings:
                    if option == "--help":
                        continue
                    self.assertIn(option, body, "%s: %s is not named in its section" % (command, option))

    def test_every_top_level_argument_is_named(self):
        text = document_text()
        for action in records.build_parser()._actions:
            for option in action.option_strings:
                self.assertIn(option, text, option)

    def test_the_test_only_flag_is_marked_as_one_and_is_not_the_stations_argument(self):
        text = document_text()
        self.assertIn("`--component-root DIR` | TEST ONLY", text)
        self.assertIn("`--records-root`", text, "12.1's station-side argument is documented")
        self.assertNotIn("--records-root DIR`", text.replace("`--records-root`", ""),
                         "records.py must not appear to take 12.1's argument")


class InterfaceMdNamesEveryExitCode(unittest.TestCase):
    def test_every_code_from_zero_to_seven_is_in_the_table(self):
        lines = sections(document_text())["Exit codes"]
        rows = set(re.findall(r"^\| (\d) \|", "\n".join(lines), re.M))
        self.assertEqual(sorted(rows), list(EXIT_CODES))

    def test_every_exit_the_cases_produced_is_documented(self):
        lines = "\n".join(sections(document_text())["Exit codes"])
        for case in cases():
            self.assertIn("| %d |" % case["exit"], lines,
                          "%s exited %d, which the table does not name" % (case["case"], case["exit"]))

    def test_every_error_name_the_cases_produced_is_documented(self):
        text = document_text()
        for case in cases():
            body = case["body"]
            if not body or body.get("ok") is not False:
                continue
            self.assertIn("`%s`" % body["error"], text, case["case"])


# ---- the A7a tests ------------------------------------------------------------------------------

class EveryCommandFromAnotherWorkingDirectory(unittest.TestCase):
    """The guide: "Test helpers from a different working directory." Two directories, one answer."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("records-cwd-")
        cls.workspace = testlib.fixture_workspace(cls.scratch)
        code, body, err = testlib.run_json(
            ["import-legacy", "--workspace", cls.workspace, "--doc", FIXTURE_DOC])
        assert code == 0, err
        cls.run_id = body["run_id"]
        cls.identity = testlib.write_json(
            os.path.join(cls.scratch, "identity.json"),
            testlib.run_json(["identity", "--workspace", cls.workspace])[1]["identity"])

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.scratch)

    def calls(self):
        ws = ["--workspace", self.workspace, "--doc", FIXTURE_DOC]
        return {
            "verify": ["verify"] + ws,
            "events": ["events"] + ws,
            "identity": ["identity", "--workspace", self.workspace],
            "append": ["append"] + ws + ["--events", os.path.join(self.scratch, "none.json"),
                                         "--expect-head", testlib.ZERO],
            "component-identity": ["component-identity"],
            "state": ["state"] + ws + ["--at-source", self.identity],
            "render": ["render"] + ws + ["--run-id", self.run_id],
            "import-legacy": ["import-legacy"] + ws + ["--dry-run"],
            "mirrors": ["mirrors"] + ws,
            "survey": ["survey", "--workspace", self.workspace],
        }

    def test_every_command_answers_the_same_from_two_different_directories(self):
        here = testlib.ROOT
        elsewhere = tempfile.gettempdir()
        for command, argv in sorted(self.calls().items()):
            first = testlib.run_cli(argv, cwd=here)
            second = testlib.run_cli(argv, cwd=elsewhere)
            self.assertEqual(first[0], second[0], command)
            self.assertEqual(first[1], second[1],
                             "%s answers differently depending on the working directory" % command)

    def test_every_read_only_command_succeeds_from_another_directory(self):
        for command, argv in sorted(self.calls().items()):
            if command == "append":
                continue  # its own case is the missing input file below
            code, body, err = testlib.run_json(argv, cwd=tempfile.gettempdir())
            self.assertEqual(code, 0, "%s: %s %s" % (command, body, err))
            self.assertTrue(body["ok"], command)


class EveryCommandWithAnInvalidArgument(unittest.TestCase):
    def test_an_unknown_flag_is_exit_two_and_prints_no_json(self):
        for command in sorted(records.COMMANDS):
            code, out, err = testlib.run_cli([command, "--no-such-flag"])
            self.assertEqual(code, 2, command)
            self.assertEqual(out, "", command)
            self.assertIn("error:", err, command)

    def test_a_missing_required_argument_is_exit_two(self):
        for command in sorted(records.COMMANDS):
            if command == "component-identity":
                continue  # it takes none
            code, out, _ = testlib.run_cli([command])
            self.assertEqual(code, 2, command)
            self.assertEqual(out, "", command)

    def test_a_workspace_that_is_not_there_is_exit_two(self):
        gone = os.path.join(tempfile.gettempdir(), "records-no-such-workspace")
        for command in sorted(records.COMMANDS):
            if command == "component-identity":
                continue
            argv = [command, "--workspace", gone]
            if command not in ("identity", "survey"):
                argv += ["--doc", FIXTURE_DOC]
            if command == "append":
                argv += ["--events", gone, "--expect-head", testlib.ZERO]
            if command == "render":
                argv += ["--run-id", "r"]
            code, out, err = testlib.run_cli(argv)
            self.assertEqual(code, 2, "%s: %s" % (command, err))
            self.assertEqual(out, "", command)


class EveryFileArgumentThatIsNotThere(unittest.TestCase):
    """A missing input file is a usage error, named, with nothing on stdout."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("records-missing-")
        cls.workspace = testlib.fixture_workspace(cls.scratch)
        cls.gone = os.path.join(cls.scratch, "not-a-file.json")

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.scratch)

    def test_each_of_the_three_file_arguments_is_exit_two(self):
        ws = ["--workspace", self.workspace, "--doc", FIXTURE_DOC]
        calls = {
            "--events": ["append"] + ws + ["--events", self.gone, "--expect-head", testlib.ZERO],
            "--at-source": ["state"] + ws + ["--at-source", self.gone],
            "--resolutions": ["import-legacy"] + ws + ["--resolutions", self.gone, "--dry-run"],
        }
        for flag, argv in sorted(calls.items()):
            code, out, err = testlib.run_cli(argv)
            self.assertEqual(code, 2, "%s: %s" % (flag, err))
            self.assertEqual(out, "", flag)
            self.assertIn(flag, err, flag)
            self.assertIn("not a file", err, flag)

    def test_a_file_that_is_not_json_is_also_a_usage_error(self):
        path = os.path.join(self.scratch, "not-json.json")
        testlib.write(path, "{ this is not JSON\n")
        code, out, err = testlib.run_cli(
            ["append", "--workspace", self.workspace, "--doc", FIXTURE_DOC,
             "--events", path, "--expect-head", testlib.ZERO])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("does not read as JSON", err)


class EveryCommandWithoutJsonschema(unittest.TestCase):
    def test_every_command_exits_three_with_one_line_on_stderr(self):
        seen = set()
        for case in cases():
            if not case["case"].startswith("without-jsonschema-"):
                continue
            seen.add(case["command"])
            self.assertEqual(case["exit"], 3, case["case"])
            self.assertIsNone(case["body"], case["case"])
            self.assertEqual(case["stderr"].strip(), testlib.MISSING_DEPENDENCY, case["case"])
        self.assertEqual(sorted(seen), sorted(records.COMMANDS))

    def test_help_still_works_without_it(self):
        scratch = testlib.make_scratch("records-help-")
        try:
            stub = testlib.stub_without_jsonschema(scratch)
            for command in sorted(records.COMMANDS):
                code, out, err = testlib.run_cli([command, "--help"], env={"PYTHONPATH": stub})
                self.assertEqual(code, 0, "%s: %s" % (command, err))
                self.assertIn("side effects:", out, command)
        finally:
            testlib.rmtree(scratch)


class TheHelpExamplesRun(unittest.TestCase):
    """The guide: exercise the documented commands, using the command examples as test input."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = testlib.make_scratch("records-examples-")
        cls.workspace = testlib.fixture_workspace(cls.scratch)
        cls.identity = testlib.write_json(
            os.path.join(cls.scratch, "identity.json"),
            testlib.run_json(["identity", "--workspace", cls.workspace])[1]["identity"])
        cls.batch = testlib.events_file(cls.scratch, [testlib.opened(doc=FIXTURE_DOC)])
        cls.answers = testlib.write_json(os.path.join(cls.scratch, "answers.json"), {
            "answered_by": "the owner", "answered_on": "2026-05-20",
            "answers": [{"line": 1, "raw": "a line no import stopped on", "skip": True,
                         "why": "an answer the question was never asked"}]})

    @classmethod
    def tearDownClass(cls):
        testlib.rmtree(cls.scratch)

    def examples(self):
        code, out, err = testlib.run_cli(["--help"])
        self.assertEqual(code, 0, err)
        found = []
        pending = None
        for line in out.split("\n"):
            text = line.strip()
            if pending is not None:
                pending = pending[:-1].strip() + " " + text
            elif text.startswith("uv run records.py"):
                pending = text
            else:
                continue
            if pending.endswith("\\"):
                continue
            found.append(shlex.split(pending)[3:])
            pending = None
        return found

    def substituted(self, argv):
        out = []
        replace = {"--workspace": self.workspace, "--doc": FIXTURE_DOC,
                   "--events": self.batch, "--at-source": self.identity,
                   "--resolutions": self.answers}
        skip = False
        for index, token in enumerate(argv):
            if skip:
                skip = False
                continue
            out.append(token)
            if token in replace:
                out.append(replace[token])
                skip = True
        return out

    def test_the_epilog_holds_an_example_for_every_command(self):
        named = set(argv[0] for argv in self.examples())
        self.assertEqual(sorted(named), sorted(records.COMMANDS))

    def test_every_example_runs_and_is_never_a_usage_error(self):
        self.assertGreaterEqual(len(self.examples()), len(records.COMMANDS))
        for argv in self.examples():
            ready = self.substituted(argv)
            code, out, err = testlib.run_cli(ready)
            self.assertNotEqual(code, 2, "the example is a usage error: %s (%s)" % (ready, err))
            self.assertNotEqual(code, 3, "the example could not start: %s (%s)" % (ready, err))
            self.assertIn(code, (0, 4, 5, 7), "%s exited %d: %s" % (ready, code, err))
            document = json.loads(out)
            self.assertEqual(document["interface_version"], 1)
            self.assertEqual(document["component_version"], records.component_meta(testlib.ROOT)["version"])


class ThePluginManifest(unittest.TestCase):
    def test_it_names_the_component_and_the_version_the_contract_gives(self):
        with open(os.path.join(testlib.ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
        self.assertEqual(meta["name"], "records")
        self.assertEqual(meta["version"], "0.1.0")
        self.assertTrue(meta["description"])

    def test_every_response_carries_that_version(self):
        for case in cases():
            if case["body"] is None:
                continue
            self.assertEqual(case["body"]["component_version"], "0.1.0", case["case"])
            self.assertEqual(case["body"]["interface_version"], 1, case["case"])

    def test_component_identity_agrees_with_the_manifest(self):
        code, body, err = testlib.run_json(["component-identity"])
        self.assertEqual(code, 0, err)
        self.assertEqual(body["version"], "0.1.0")
        self.assertEqual(body["name"], "records")


class ThePilotIsFrozen(unittest.TestCase):
    """Ruling E12-2: at close, `git diff --stat main -- plugins/recheck-v2` prints nothing."""

    def test_nothing_under_plugins_recheck_v2_has_moved(self):
        repo = testlib.REPO
        # a linked worktree's `.git` is a file, not a directory, so ask git rather than the tree
        inside = subprocess.run(["git", "-C", repo, "rev-parse", "--git-dir"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if inside.returncode != 0:
            self.skipTest("not a git checkout: %s" % repo)
        known = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "--quiet", "main"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if known.returncode != 0:
            self.skipTest("this checkout has no `main` to diff against")
        proc = subprocess.run(["git", "-C", repo, "diff", "--stat", "main", "--",
                               "plugins/recheck-v2"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        self.assertEqual(proc.stdout.decode("utf-8", "replace"), "",
                         "the qualified pilot is not byte-identical to main (ruling E12-2)")

    def test_this_component_writes_nowhere_near_it(self):
        """Nothing shipped here names a path inside the pilot as a write target."""
        offenders = []
        for dirpath, dirnames, filenames in os.walk(os.path.join(testlib.ROOT, "scripts")):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as fh:
                    for number, line in enumerate(fh, 1):
                        if "recheck-v2" in line and re.search(r'\bopen\([^)]*["\']w', line):
                            offenders.append("%s:%d" % (path, number))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
