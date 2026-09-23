"""The interface document against the code (E13 slice 3, lane contract section 11, last bullet).

`references/signoff-contract.md` closes `scripts/signoff.py`'s CLI; its section "14. Interface"
states the interface in four tables. This test reads each table BY ITS HEADING (`### Commands`,
`### Result statuses`, `### Invocation fields`, `### Run-directory artifacts`), splits each row on
`|` and strips the backticks, and fails when the document and the code disagree on:

- the list of CLI commands and each one's arguments: against `signoff.build_parser()`'s
  subcommands, their handlers and their required arguments;
- each command's exit codes: every code named must be one of `signoff_core/constants.py`'s
  `EXIT_*`, the union must be exactly that set, every command lists 1 and 2 and 2 is PROVED for
  each by a real usage slip; a command whose handler (read with `inspect.getsource`) opens the
  records client, loads a schema, or ends a run through `finish`/`raise_terminal` (which load the
  result schema) must list 3; one whose handler emits `EXIT_VALIDATION` or ends a run through
  `finish`/`raise_terminal` (which emit it for a result that fails validation) must list 4 and no
  other may; one whose handler can end the run (`finish`, `raise_terminal`, `require_references`)
  must list 10 and no other may;
- the result statuses: the document's rows against `references/result.schema.json`'s `status`
  enum and against every status the code passes to `finish`, `raise_terminal`, `Terminal`,
  `Stop` and `_refusal_stop`, or maps a component exit to (read with regular expressions over
  `signoff.py` and `signoff_core/`), and the terminal column against `result.TERMINAL`;
- the input's `invocation` fields: against `references/input.schema.json` (names and required);
- the run-directory artifacts: against the names the code joins onto the run directory
  (`os.path.join(run_dir, "…")`, `os.path.join(run.run_dir, "…")`, `run.scratch("…")`, and the
  receipt's `.log` sibling).

`SIGNOFF_V2_INTERFACE_DOC` points the test at another copy of the document (the mutation proof
uses it). Standard library only; nothing is written.
"""

import glob
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
SKILL = os.path.dirname(SCRIPTS)
REFS = os.path.join(SKILL, "references")
DOC = os.environ.get("SIGNOFF_V2_INTERFACE_DOC") or os.path.join(REFS, "signoff-contract.md")
SECTION = "## 14. Interface"

sys.dont_write_bytecode = True
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
import signoff  # noqa: E402
from signoff_core import constants, result as resultmod  # noqa: E402

EXITS = {getattr(constants, n) for n in dir(constants) if n.startswith("EXIT_")}
COMMON = ("help", "records_root", "plugin_root", "skill_root")


def section(text, heading):
    start = text.find(heading + "\n")
    if start < 0:
        raise AssertionError("the interface document has no %r section" % heading)
    body = text[start + len(heading):]
    end = re.search(r"^## ", body, re.M)
    return body[:end.start()] if end else body


def table(text, heading):
    start = re.search(r"^### %s\s*$" % re.escape(heading), text, re.M)
    if not start:
        raise AssertionError("no table heading ### %s" % heading)
    rows = []
    for line in text[start.end():].splitlines():
        if line.startswith("### "):
            break
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip().replace("`", "") for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    if len(rows) < 2:
        raise AssertionError("the table under ### %s has no rows" % heading)
    return rows[1:]


def codes(cell):
    return {int(part) for part in re.findall(r"\d+", cell)}


def code_statuses():
    found = set()
    patterns = (r'(?:Terminal|Stop|_refusal_stop)\(\s*"([a-z_]+)"',
                r'finish\(run, resolved, "([a-z_]+)"',
                r'raise_terminal\(run, resolved, args, "([a-z_]+)"',
                r'^\s*status = "([a-z_]+)" if ',
                r'^\s*status = "[a-z_]+" if [^\n]* else "([a-z_]+)"\s*$')
    paths = [os.path.join(SCRIPTS, "signoff.py")] + glob.glob(os.path.join(SCRIPTS, "signoff_core",
                                                                          "*.py"))
    for path in paths:
        with open(path) as handle:
            source = handle.read()
        for pattern in patterns:
            found |= set(re.findall(pattern, source, re.M))
        mapping = re.search(r"def _status_for\(.*?\n(?:[ \t].*\n)+", source)
        if mapping:
            found |= set(re.findall(r'\d+: "([a-z_]+)"', mapping.group(0)))
            found |= set(re.findall(r'\.get\(exit_code, "([a-z_]+)"\)', mapping.group(0)))
    return found


class Interface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DOC, "r", encoding="utf-8") as handle:
            cls.full = handle.read()
        cls.text = section(cls.full, SECTION)
        parser = signoff.build_parser()
        subs = [a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction"]
        cls.subparsers = subs[0].choices

    def commands(self):
        return {row[0]: row for row in table(self.text, "Commands")}

    def handler_source(self, name):
        return inspect.getsource(self.subparsers[name].get_default("handler"))

    def test_the_command_list(self):
        self.assertEqual(set(self.commands()), set(self.subparsers))

    def test_each_commands_arguments(self):
        for name, row in self.commands().items():
            parts = []
            for action in self.subparsers[name]._actions:
                if action.dest in COMMON:
                    continue
                if not action.option_strings:
                    parts.append("<%s>" % (action.metavar or action.dest))
                elif action.required:
                    parts.append("%s %s" % (action.option_strings[0], action.metavar))
            self.assertEqual(row[1], " ".join(parts) or "none", name)

    def test_the_exit_codes(self):
        union = set()
        for name, row in self.commands().items():
            listed = codes(row[2])
            union |= listed
            source = self.handler_source(name)
            ends = any(word in source for word in ("finish(", "raise_terminal("))
            self.assertTrue(listed <= EXITS, name)
            self.assertTrue({1, 2} <= listed, name)
            if "open_records(" in source or "load_schema(" in source or ends:
                self.assertIn(3, listed, "%s can meet a missing dependency" % name)
            self.assertEqual(4 in listed, "EXIT_VALIDATION" in source or ends, "%s and 4" % name)
            terminal = ends or "require_references(" in source
            self.assertEqual(10 in listed, terminal, "%s and 10" % name)
        self.assertEqual(union, EXITS)

    def test_a_usage_slip_is_exit_2_for_every_command(self):
        work = tempfile.mkdtemp(prefix="iface-")
        try:
            missing = os.path.join(work, "absent")
            for name in self.commands():
                if name == "skill-identity":
                    argv = [name, "--no-such-option"]
                elif name == "check-input":
                    argv = [name, os.path.join(missing, "input.json")]
                elif name == "identity":
                    argv = [name]
                elif name == "record-answer":
                    argv = [name, "--run-dir", missing, "--answer", os.path.join(work, "a.json")]
                else:
                    argv = [name, "--run-dir", missing]
                proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "signoff.py")] + argv,
                                      cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
                self.assertEqual(proc.returncode, 2, "%s: %s" % (name, proc.stderr.decode()[-300:]))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_the_result_statuses(self):
        documented = {row[0]: row[1] for row in table(self.text, "Result statuses")}
        with open(os.path.join(REFS, "result.schema.json")) as handle:
            schema = json.load(handle)
        self.assertEqual(set(documented), set(schema["properties"]["status"]["enum"]))
        self.assertEqual(set(documented), code_statuses(), "document vs the code's statuses")
        for status, kind in documented.items():
            self.assertEqual(kind, resultmod.TERMINAL.get(status, "stop"), status)

    def test_the_invocation_fields(self):
        rows = table(self.text, "Invocation fields")
        with open(os.path.join(REFS, "input.schema.json")) as handle:
            block = json.load(handle)["properties"]["invocation"]
        self.assertEqual({row[0] for row in rows}, set(block["properties"]))
        for row in rows:
            self.assertEqual(row[1] == "yes", row[0] in block["required"], row[0])
            for value in block["properties"][row[0]].get("enum") or []:
                self.assertIn(value, row[2], row[0])

    def test_the_run_directory_artifacts(self):
        documented = {row[0] for row in table(self.text, "Run-directory artifacts")}
        written = set()
        for path in [os.path.join(SCRIPTS, "signoff.py")] + glob.glob(
                os.path.join(SCRIPTS, "signoff_core", "*.py")):
            with open(path) as handle:
                source = handle.read()
            written |= set(re.findall(r'os\.path\.join\((?:self\.|run\.)?run_dir, "([^"]+)"\)',
                                      source))
            written |= {name + "/" for name in re.findall(r'run\.scratch\("([^"]+)"\)', source)}
            written |= {name + ".log" for name in
                        re.findall(r'(\w+)\.path\[:-len\("\.json"\)\] \+ "\.log"', source)}
        self.assertTrue(written)
        self.assertEqual(documented, written)


if __name__ == "__main__":
    unittest.main()
