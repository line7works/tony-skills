"""The interface document against the code (E13 slice 3, lane contract section 11, last bullet).

`references/build-contract.md` closes `scripts/build.py`'s CLI; its section "19. Interface" states
the interface in four tables. This test reads each table BY ITS HEADING (`### Commands`,
`### Result statuses`, `### Invocation fields`, `### Run-directory artifacts`), splits each row
on `|` and strips the backticks, and fails when the document and the code disagree on:

- the list of CLI commands and each one's arguments: against the subcommands and the required
  arguments of `build.build_parser()`, and against the `COMMANDS` dispatch table;
- each command's exit codes: every code named must be in `build_core/exits.py`'s `ALL`, the union
  over the commands must be exactly `ALL`, every command must list 1 and 2 (the dispatcher's
  catch-alls) and 2 is PROVED for each by a real usage slip; the commands in `build.NEEDS_RECORDS`
  must list 3; the commands whose handler emits `exits.VALIDATION` must list 4 and no other may;
  and section 16's exit table must name exactly `ALL`;
- the result statuses: the document's rows against `references/result.schema.json`'s `status`
  enum and against `build_core/result.py`'s `COMPLETION_STATUSES` and `STOP_STATUSES`, the
  terminal status column included;
- the input's `invocation` fields: against `references/input.schema.json` (names, and required);
- the run-directory artifacts: against the names the code writes under the run directory,
  read from `scripts/build.py` (`artifact("…")`, `write_artifact("…")`) and
  `build_core/statefile.py` (`os.path.join(run_dir, "…")`).

`BUILD_V2_INTERFACE_DOC` points the test at another copy of the document; the mutation proof
(a copy with one row changed) uses it. Standard library only; nothing is written.
"""

import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
SKILL = os.path.dirname(SCRIPTS)
REFS = os.path.join(SKILL, "references")
DOC = os.environ.get("BUILD_V2_INTERFACE_DOC") or os.path.join(REFS, "build-contract.md")
SECTION = "## 19. Interface"

sys.dont_write_bytecode = True
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
import build  # noqa: E402
from build_core import exits, result as resultmod  # noqa: E402


def section(text, heading):
    start = text.find(heading + "\n")
    if start < 0:
        raise AssertionError("the interface document has no %r section" % heading)
    body = text[start + len(heading):]
    end = re.search(r"^## ", body, re.M)
    return body[:end.start()] if end else body


def table(text, heading):
    """The rows of the first Markdown table under `### heading`, as lists of cells."""
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


class Interface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DOC, "r", encoding="utf-8") as handle:
            cls.full = handle.read()
        cls.text = section(cls.full, SECTION)
        cls.parser = build.build_parser()
        subs = [a for a in cls.parser._actions if a.__class__.__name__ == "_SubParsersAction"]
        cls.subparsers = subs[0].choices

    def commands(self):
        return {row[0]: row for row in table(self.text, "Commands")}

    def test_the_command_list(self):
        documented = set(self.commands())
        self.assertEqual(documented, set(self.subparsers), "document vs build_parser()")
        self.assertEqual(documented, set(build.COMMANDS), "document vs COMMANDS")

    def test_each_commands_arguments(self):
        for name, row in self.commands().items():
            parts = []
            for action in self.subparsers[name]._actions:
                if action.dest in ("help", "skill_root", "records_root"):
                    continue
                if not action.option_strings:
                    parts.append("<%s>" % (action.metavar or action.dest))
                elif action.required:
                    parts.append("%s %s" % (action.option_strings[0], action.metavar))
            self.assertEqual(row[1], " ".join(parts) or "none", name)

    def test_the_exit_codes(self):
        rows = self.commands()
        union = set()
        for name, row in rows.items():
            listed = codes(row[2])
            union |= listed
            self.assertTrue(listed <= set(exits.ALL), "%s names a code the CLI lacks" % name)
            self.assertTrue({1, 2} <= listed, "%s must list the catch-alls 1 and 2" % name)
            if name in build.NEEDS_RECORDS:
                self.assertIn(3, listed, "%s reaches the records component" % name)
            emits_validation = "exits.VALIDATION" in inspect.getsource(build.COMMANDS[name])
            self.assertEqual(4 in listed, emits_validation, "%s and exit 4" % name)
        self.assertEqual(union, set(exits.ALL), "the union of the per-command codes")
        exit_table = section(self.full, "## 16. Exit codes")
        self.assertEqual({int(c) for c in re.findall(r"^\| exit (\d+) \|", exit_table, re.M)},
                         set(exits.ALL), "section 16's exit table")

    def test_a_usage_slip_is_exit_2_for_every_command(self):
        work = tempfile.mkdtemp(prefix="iface-")
        try:
            missing = os.path.join(work, "absent")
            for name in self.commands():
                if name == "skill-identity":
                    argv = [name, "--no-such-option"]
                elif name in ("check-input",):
                    argv = [name, os.path.join(missing, "input.json")]
                elif name == "identity":
                    argv = [name]
                elif name == "record-answer":
                    argv = [name, "--run-dir", missing, "--answer", os.path.join(work, "a.json")]
                else:
                    argv = [name, "--run-dir", missing]
                proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "build.py")] + argv,
                                      cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
                self.assertEqual(proc.returncode, 2, "%s: %s" % (name, proc.stderr.decode()[-300:]))
        finally:
            import shutil
            shutil.rmtree(work, ignore_errors=True)

    def test_the_result_statuses(self):
        rows = table(self.text, "Result statuses")
        documented = {row[0]: row[1] for row in rows}
        with open(os.path.join(REFS, "result.schema.json")) as handle:
            schema = json.load(handle)
        self.assertEqual(set(documented), set(schema["properties"]["status"]["enum"]),
                         "document vs result.schema.json")
        code = set(resultmod.COMPLETION_STATUSES) | set(resultmod.STOP_STATUSES)
        self.assertEqual(set(documented), code, "document vs build_core/result.py")
        for status, kind in documented.items():
            self.assertEqual(kind, "stop" if status in resultmod.STOP_STATUSES else "completion",
                             status)
            self.assertIn(kind, schema["properties"]["terminal_status"]["enum"])

    def test_the_invocation_fields(self):
        rows = table(self.text, "Invocation fields")
        with open(os.path.join(REFS, "input.schema.json")) as handle:
            block = json.load(handle)["properties"]["invocation"]
        self.assertEqual({row[0] for row in rows}, set(block["properties"]))
        for row in rows:
            self.assertEqual(row[1] == "yes", row[0] in block["required"], row[0])
            enum = block["properties"][row[0]].get("enum")
            for value in enum or []:
                self.assertIn(value, row[2], "%s: %s" % (row[0], value))

    def test_the_run_directory_artifacts(self):
        rows = table(self.text, "Run-directory artifacts")
        with open(os.path.join(SCRIPTS, "build.py")) as handle:
            source = handle.read()
        with open(os.path.join(SCRIPTS, "build_core", "statefile.py")) as handle:
            statefile = handle.read()
        written = set(re.findall(r'(?:write_)?artifact\("([^"]+)"', source))
        written |= set(re.findall(r'os\.path\.join\(run_dir, "([^"]+)"\)', statefile))
        self.assertTrue(written, "the code-side reading found nothing")
        self.assertEqual({row[0] for row in rows}, written)


if __name__ == "__main__":
    unittest.main()
