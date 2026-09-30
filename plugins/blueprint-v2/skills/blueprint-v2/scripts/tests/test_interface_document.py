"""The interface document against the code (E14 slice 3c, item 3.2; a port of build-v2's test).

`references/blueprint-v2-contract.md` states this core's CLI in its section "19. Interface", in four tables read
BY THEIR HEADINGS (`### Commands`, `### Result statuses`, `### Invocation fields`,
`### Run-directory artifacts`), each row split on `|` with the backticks stripped. The test fails
when the document and the code disagree on:

- the commands and each one's arguments: against the subcommands of the driver's parser
  (`station_core.driver.build_parser` with `blueprint.py`'s hunts and own commands) and against the
  dispatch table the driver builds (the shared commands, the four lane phases of `HANDLERS`, and
  the own commands of `COMMANDS`); an argument is written `<name>` (positional), `--flag M`
  (required), `[--flag M]` (optional), `[--flag M ...]` (repeatable), `{a,b}` for a closed choice;
- each command's exit codes: every code named must be in `station_core/exits.py`'s `ALL`, the
  union over the commands must be exactly `ALL`, and each command's codes must be exactly the
  codes its handler's code can return, read from the source: 1 and 2 for every command (the
  dispatcher's catch-alls: a defect, and argparse's usage slip, which is PROVED for each command by
  a real one); 0 where the reachable code emits a document with no code or with `exits.SUCCESS`;
  3 where it reaches `require_jsonschema`'s exit or raises `ComponentUnavailable`; 4, 5 and 10
  where it names `exits.VALIDATION`, `exits.REFUSED` or `exits.TERMINAL` (or passes 4, 5, 10 to
  an `emit`), 10 also where it raises the driver's `Terminal`. "Reachable" is the handler, the
  decorators on it, and every function of this core's own modules (`station_core/`,
  `blueprint_core/`, `blueprint.py`) it calls, followed transitively; a method call on an object is
  followed to every method of that name the core defines, except the standard containers' and
  strings' own method names. A decorator's `except X:` clause counts only when some function the
  handler's own body reaches (its decorators set aside) raises `X`, or a class of this core derived
  from it; a clause naming no exception class of this core (a bare `except`, a standard exception)
  counts as written (C3C1-2). `station-loop.md` section 2's exit table must name exactly `ALL`;
- the result statuses: the document's rows against `references/result.schema.json`'s `status`
  enum and against the status values the code passes to its result builder (``_finish``),
  returns from no function, or names as a `status=` keyword; a `stopped` run is a stop, every
  other a completion (`station-loop.md` section 5);
- the input's `invocation` fields: against `references/input.schema.json` (names, required, and
  every enum value named in the row);
- the run-directory artifacts: against every name this core's code joins onto the run directory
  (`os.path.join(run_dir, ...)`, and the core's own helpers whose name parameter reaches such a
  join), as a literal, a `%`-formatted literal (`*` for the slot) or a module constant; the first
  path segment, with `/` for a folder (a name with no extension, or one joined with more parts).
  A literal that a `*` name of the same list matches is that name's.

`BLUEPRINT_V2_INTERFACE_DOC` points the test at another copy of the document; the mutation proof (a copy with
one row changed) uses it. Standard library only; nothing is written in the checkout.
"""
import argparse
import ast
import fnmatch
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import testlib

CONTRACT = "blueprint-v2-contract.md"
SCRIPT = "blueprint"
CORE_PKG = "blueprint_core"
DOC_ENV = "BLUEPRINT_V2_INTERFACE_DOC"
# the result builder(s) and the position of their status argument; the functions whose returned
# tuples start with a status
FINISHERS = {"_finish": 2}
RETURNERS = ()

DOC = os.environ.get(DOC_ENV) or os.path.join(testlib.REF, CONTRACT)
SECTION = "## 19. Interface"

testlib.add_scripts_to_path()
sys.dont_write_bytecode = True
script = importlib.import_module(SCRIPT)  # noqa: E402
from station_core import driver, exits  # noqa: E402

CODE_NAMES = {"SUCCESS": exits.SUCCESS, "GENERAL": exits.GENERAL, "USAGE": exits.USAGE,
              "MISSING_DEPENDENCY": exits.MISSING_DEPENDENCY, "VALIDATION": exits.VALIDATION,
              "REFUSED": exits.REFUSED, "TERMINAL": exits.TERMINAL}
CONTAINER_METHODS = {"get", "update", "append", "extend", "write", "read", "items", "keys", "values", "pop",
                     "setdefault", "format", "join", "split", "strip", "replace", "startswith", "endswith",
                     "close", "add", "copy", "sort", "encode", "decode", "lower", "upper", "index", "count",
                     "insert", "remove", "seek", "flush", "readlines", "splitlines", "rstrip", "lstrip",
                     "group", "match", "search", "hexdigest", "digest", "casefold"}


# ---- the document ------------------------------------------------------------------------------

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


def codes_of(cell):
    return {int(part) for part in re.findall(r"\d+", cell)}


# ---- the code: the parser and the dispatch table ------------------------------------------------

def parser_commands():
    parser = driver.build_parser(script.STATION, script.HUNTS, script.COMMANDS)
    subs = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    return subs[0].choices


def dispatch():
    """{command: handler} as `driver.main` builds it."""
    table_ = {"check-input": driver.command_check_input, "select": driver.command_select,
              "identity": driver.command_identity, "skill-identity": driver.command_skill_identity}
    for phase in driver.LANE_PHASES:
        table_[phase] = script.HANDLERS.get(phase) or driver.not_built(phase)
    for own in script.COMMANDS:
        table_[own["name"]] = own["handler"]
    return table_


def arguments(subparser):
    parts = []
    for action in subparser._actions:
        if action.dest in ("help", "skill_root", "records_root"):
            continue
        shown = action.metavar or ("{%s}" % ",".join(action.choices) if action.choices else None)
        if not action.option_strings:
            parts.append("<%s>" % (shown or action.dest))
            continue
        flag = action.option_strings[0]
        takes = action.nargs != 0
        text = "%s %s" % (flag, shown or action.dest.upper()) if takes else flag
        if isinstance(action, argparse._AppendAction):
            text += " ..."
        parts.append(text if action.required else "[%s]" % text)
    return " ".join(parts) or "none"


# ---- the code: its modules read as syntax -------------------------------------------------------

class Source(object):
    """This core's own modules, parsed: functions, class methods, import aliases and constants."""

    def __init__(self):
        self.mods = {}
        for pkg in ("station_core", CORE_PKG):
            folder = os.path.join(testlib.SCRIPTS, pkg)
            for name in sorted(os.listdir(folder)):
                if name.endswith(".py"):
                    key = pkg if name == "__init__.py" else "%s.%s" % (pkg, name[:-3])
                    self.mods[key] = (pkg, self._parse(os.path.join(folder, name)))
        self.mods[SCRIPT] = ("", self._parse(os.path.join(testlib.SCRIPTS, SCRIPT + ".py")))
        self.funcs, self.methods, self.classes = {}, {}, {}
        self.aliases, self.symbols, self.consts = {}, {}, {}
        for key, (pkg, tree) in self.mods.items():
            aliases, symbols, consts = {}, {}, {}
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    self.funcs[(key, node.name)] = node
                elif isinstance(node, ast.ClassDef):
                    methods = {}
                    for sub in node.body:
                        if isinstance(sub, ast.FunctionDef):
                            methods[sub.name] = sub
                            self.methods.setdefault(sub.name, []).append((key, sub))
                    self.classes[(key, node.name)] = methods
                elif (isinstance(node, ast.Assign) and len(node.targets) == 1
                      and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Constant)
                      and isinstance(node.value.value, str)):
                    consts[node.targets[0].id] = node.value.value
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    base = ((pkg + "." + node.module) if node.module else pkg) if node.level == 1 \
                        else (node.module or "")
                    for alias in node.names:
                        if "%s.%s" % (base, alias.name) in self.mods:
                            aliases[alias.asname or alias.name] = "%s.%s" % (base, alias.name)
                        elif base in self.mods:
                            symbols[alias.asname or alias.name] = (base, alias.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.mods:
                            aliases[alias.asname or alias.name] = alias.name
            self.aliases[key], self.symbols[key], self.consts[key] = aliases, symbols, consts

    @staticmethod
    def _parse(path):
        with open(path, "r", encoding="utf-8") as handle:
            return ast.parse(handle.read(), path)

    def resolve(self, mod, func):
        """The functions of this core a call's callee can be: [(module, node)]."""
        if isinstance(func, ast.Name):
            if (mod, func.id) in self.funcs:
                return [(mod, self.funcs[(mod, func.id)])]
            if func.id in self.symbols[mod]:
                target = self.symbols[mod][func.id]
                return [(target[0], self.funcs[target])] if target in self.funcs else []
            return []
        if not isinstance(func, ast.Attribute):
            return []
        value = func.value
        if isinstance(value, ast.Name) and value.id in self.aliases[mod]:
            target = (self.aliases[mod][value.id], func.attr)
            return [(target[0], self.funcs[target])] if target in self.funcs else []
        if isinstance(value, ast.Name) and (mod, value.id) in self.classes:
            method = self.classes[(mod, value.id)].get(func.attr)
            return [(mod, method)] if method else []
        if func.attr in CONTAINER_METHODS:
            return []
        return list(self.methods.get(func.attr, []))

    def reach(self, mod, node, decorators=True):
        """[(module, function, taken as a decorator)] reachable from `node`; with `decorators` False
        the decorators are set aside, so the reach is the body's own."""
        seen, stack, out = set(), [(mod, node, False)], []
        while stack:
            where, fn, as_decorator = stack.pop()
            if id(fn) in seen:
                continue
            seen.add(id(fn))
            out.append((where, fn, as_decorator))
            if decorators:
                for deco in fn.decorator_list:
                    stack.extend((m, f, True) for m, f in
                                 self.resolve(where, deco.func if isinstance(deco, ast.Call) else deco))
            for stmt in fn.body:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Call):
                        stack.extend((m, f, False) for m, f in self.resolve(where, sub.func))
        return out

    def exception_classes(self):
        """{class name: the names of its bases} for every class this core defines."""
        classes = {}
        for key, (pkg, tree) in self.mods.items():
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    classes[node.name] = [_last_name(base) for base in node.bases]
        return classes

    def handler_node(self, handler):
        handler = getattr(handler, "__wrapped__", handler)
        if handler.__qualname__.startswith("not_built."):
            return "station_core.driver", self.funcs[("station_core.driver", "not_built")]
        return handler.__module__, self.funcs[(handler.__module__, handler.__name__)]


def _callee(call):
    func = call.func
    return func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)


def _last_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def raised_classes(source, reached):
    """The exception classes of this core the functions `reached` raise, with every class of this core
    each one derives from (an `except` of a base catches it)."""
    classes = source.exception_classes()
    raised = set()
    for mod, fn, _ in reached:
        for stmt in fn.body:
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Raise) and sub.exc is not None:
                    name = _last_name(sub.exc.func if isinstance(sub.exc, ast.Call) else sub.exc)
                    if name in classes:
                        raised.add(name)
    pending = list(raised)
    while pending:
        for base in classes.get(pending.pop(), []):
            if base in classes and base not in raised:
                raised.add(base)
                pending.append(base)
    return raised


def unraised_clauses(source, fn, raised):
    """The nodes of `fn`'s `except X:` clauses whose X names only classes of this core that nothing the
    handler's body reaches raises: a code there is one the command cannot return (C3C1-2)."""
    classes = source.exception_classes()
    dead = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            kinds = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
            names = [_last_name(kind) for kind in kinds]
            if all(name in classes for name in names) and not any(name in raised for name in names):
                dead.update(id(sub) for sub in ast.walk(node))
    return dead


def reachable_codes(source, handler):
    """The exit codes the handler's reachable code can return (the rules of the docstring)."""
    found = {exits.GENERAL, exits.USAGE}
    start = source.handler_node(handler)
    raised = raised_classes(source, source.reach(*start, decorators=False))
    for mod, fn, as_decorator in source.reach(*start):
        dead = unraised_clauses(source, fn, raised) if as_decorator else set()
        for stmt in fn.body:
            for sub in ast.walk(stmt):
                if id(sub) in dead:
                    continue
                if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "exits" \
                        and sub.attr in CODE_NAMES:
                    found.add(CODE_NAMES[sub.attr])
                if isinstance(sub, ast.Call):
                    name = _callee(sub)
                    if name == "emit" and len(sub.args) == 1 and not sub.keywords:
                        found.add(exits.SUCCESS)
                    if name == "emit" and len(sub.args) == 2 and isinstance(sub.args[1], ast.Constant) \
                            and sub.args[1].value in exits.ALL:
                        found.add(sub.args[1].value)
                    if name == "Terminal":
                        found.add(exits.TERMINAL)
                    if name == "exit" and sub.args and isinstance(sub.args[0], ast.Constant) \
                            and sub.args[0].value == exits.MISSING_DEPENDENCY:
                        found.add(exits.MISSING_DEPENDENCY)
                if isinstance(sub, ast.Raise) and isinstance(sub.exc, ast.Call) \
                        and _callee(sub.exc) == "ComponentUnavailable":
                    found.add(exits.MISSING_DEPENDENCY)
    return found


def coded_statuses(source):
    found = set()
    for mod, (pkg, tree) in source.mods.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _callee(node)
                if name in FINISHERS and len(node.args) > FINISHERS[name]:
                    arg = node.args[FINISHERS[name]]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        found.add(arg.value)
                for keyword in node.keywords:
                    if keyword.arg == "status" and isinstance(keyword.value, ast.Constant) \
                            and isinstance(keyword.value.value, str):
                        found.add(keyword.value.value)
            if isinstance(node, ast.FunctionDef) and node.name in RETURNERS:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Tuple) and sub.value.elts \
                            and isinstance(sub.value.elts[0], ast.Constant):
                        found.add(sub.value.elts[0].value)
    return found


def _text(node):
    return ast.unparse(node) if hasattr(ast, "unparse") else ast.dump(node)


RUN_DIR_TEXTS = ("run_dir", "run.run_dir", "run_dir or ''")


def _is_join(call):
    return _text(call.func) == "os.path.join" and len(call.args) >= 2 and _text(call.args[0]) in RUN_DIR_TEXTS


def _param_position(fn, node):
    params = [a.arg for a in fn.args.args]
    if isinstance(node, ast.Name) and node.id in params:
        return params.index(node.id)
    if isinstance(node, ast.Starred) and isinstance(node.value, ast.Name) and fn.args.vararg \
            and node.value.id == fn.args.vararg.arg:
        return "*"
    return None


def path_helpers(source):
    """{(module, function): position of its name parameter, or '*' for `*parts`}: the functions
    whose name parameter reaches a join onto the run directory, directly or through another."""
    helpers = {}
    changed = True
    while changed:
        changed = False
        for key, fn in source.funcs.items():
            if key in helpers:
                continue
            for sub in ast.walk(fn):
                if not isinstance(sub, ast.Call):
                    continue
                position = None
                if _is_join(sub):
                    position = _param_position(fn, sub.args[1])
                else:
                    for mod, target in source.resolve(key[0], sub.func):
                        at = helpers.get((mod, target.name))
                        at = 1 if at == "*" else at
                        if at is not None and len(sub.args) > at:
                            position = _param_position(fn, sub.args[at])
                if position is not None:
                    helpers[key] = position
                    changed = True
                    break
    return helpers


def _segment(source, mod, node):
    """(name, deeper) for a name node: a literal, a %-formatted literal, a constant, or a join."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, False
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant):
        return node.left.value.replace("%s", "*").replace("%d", "*"), False
    if isinstance(node, ast.Name):
        if node.id in source.consts[mod]:
            return source.consts[mod][node.id], False
        if node.id in source.symbols[mod]:
            target = source.symbols[mod][node.id]
            value = source.consts.get(target[0], {}).get(target[1])
            return (value, False) if value else (None, False)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in source.aliases[mod]:
        value = source.consts.get(source.aliases[mod][node.value.id], {}).get(node.attr)
        return (value, False) if value else (None, False)
    if isinstance(node, ast.Call) and _text(node.func) == "os.path.join" and node.args:
        name, _ = _segment(source, mod, node.args[0])
        return name, True
    if isinstance(node, ast.Tuple) and node.elts:
        name, _ = _segment(source, mod, node.elts[0])
        return name, len(node.elts) > 1
    return None, False


def written_names(source):
    helpers = path_helpers(source)
    names = set()
    for mod, (pkg, tree) in source.mods.items():
        loops = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.comprehension)) and isinstance(node.target, ast.Name) \
                    and isinstance(node.iter, (ast.Tuple, ast.List)) \
                    and all(isinstance(e, ast.Constant) for e in node.iter.elts):
                loops.setdefault(node.target.id, []).extend(e.value for e in node.iter.elts)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            found = []
            if _is_join(node):
                found = [(node.args[1], len(node.args) > 2)]
            else:
                for target_mod, target in source.resolve(mod, node.func):
                    at = helpers.get((target_mod, target.name))
                    if at is None:
                        continue
                    if at == "*":
                        found = [(node.args[1], len(node.args) > 2)] if len(node.args) > 1 else []
                    elif len(node.args) > at:
                        found = [(node.args[at], False)]
                    if target.name == "preflight":
                        found = [(arg, False) for arg in node.args[1:]]
                    break
            for arg, deeper in found:
                if isinstance(arg, ast.Name) and arg.id in loops:
                    candidates = [(value, deeper) for value in loops[arg.id]]
                else:
                    name, more = _segment(source, mod, arg)
                    candidates = [(name, deeper or more)] if name else []
                for name, more in candidates:
                    first = name.split("/")[0]
                    if more or "/" in name or "." not in first:
                        first += "/"
                    names.add(first)
    globs = [n for n in names if "*" in n]
    return {n for n in names if n in globs or not any(fnmatch.fnmatchcase(n, g) for g in globs)}


# ---- the tests ---------------------------------------------------------------------------------

class Interface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DOC, "r", encoding="utf-8") as handle:
            cls.full = handle.read()
        cls.text = section(cls.full, SECTION)
        cls.subparsers = parser_commands()
        cls.source = Source()

    def commands(self):
        return {row[0]: row for row in table(self.text, "Commands")}

    def test_the_command_list(self):
        documented = set(self.commands())
        self.assertEqual(documented, set(self.subparsers), "document vs the driver's parser")
        self.assertEqual(documented, set(dispatch()), "document vs the dispatch table")

    def test_each_commands_arguments(self):
        for name, row in self.commands().items():
            self.assertEqual(row[1], arguments(self.subparsers[name]), name)

    def test_the_exit_codes(self):
        handlers = dispatch()
        union = set()
        for name, row in self.commands().items():
            listed = codes_of(row[2])
            union |= listed
            self.assertTrue(listed <= set(exits.ALL), "%s names a code the CLI lacks" % name)
            self.assertEqual(listed, reachable_codes(self.source, handlers[name]),
                             "%s: the document vs the codes its handler's code can return" % name)
        self.assertEqual(union, set(exits.ALL), "the union of the per-command codes")
        loop = section(testlib.read_text(os.path.join(testlib.REF, "station-loop.md")),
                       "## 2. The CLI and the exit codes")
        self.assertEqual({int(c) for c in re.findall(r"^\| (\d+) \|", loop, re.M)}, set(exits.ALL),
                         "station-loop.md section 2's exit table")

    def test_a_usage_slip_is_exit_2_for_every_command(self):
        work = tempfile.mkdtemp(prefix="iface-")
        try:
            for name in self.commands():
                code, out, err = testlib.run_driver([name, "--no-such-option"], cwd=work)
                self.assertEqual(code, exits.USAGE, "%s: %s" % (name, err[-300:]))
                self.assertEqual(out, "", "%s: a usage slip prints nothing on stdout" % name)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_the_result_statuses(self):
        documented = {row[0]: row[1] for row in table(self.text, "Result statuses")}
        schema = testlib.load_json(os.path.join(testlib.REF, "result.schema.json"))
        self.assertEqual(set(documented), set(schema["properties"]["status"]["enum"]),
                         "document vs result.schema.json")
        self.assertEqual(set(documented), coded_statuses(self.source), "document vs the code")
        for status, kind in documented.items():
            self.assertEqual(kind, "stop" if status == "stopped" else "completion", status)

    def test_the_invocation_fields(self):
        rows = table(self.text, "Invocation fields")
        block = testlib.load_json(os.path.join(testlib.REF, "input.schema.json"))["properties"]["invocation"]
        self.assertEqual({row[0] for row in rows}, set(block["properties"]))
        for row in rows:
            self.assertEqual(row[1] == "yes", row[0] in block["required"], row[0])
            for value in block["properties"][row[0]].get("enum") or []:
                self.assertIn(value, row[2], "%s: %s" % (row[0], value))

    def test_the_run_directory_artifacts(self):
        rows = table(self.text, "Run-directory artifacts")
        written = written_names(self.source)
        self.assertTrue(written, "the code-side reading found nothing")
        self.assertEqual({row[0] for row in rows}, written)


class TheMutationProof(unittest.TestCase):
    """A copy of the document with one row changed fails this test (through `BLUEPRINT_V2_INTERFACE_DOC`)."""

    MUTATIONS = (
        ("### Commands", "| `check-input` | `<input.json>` |", "| `check-input` | `<input>` |"),
        ("### Result statuses", "| `stopped` | `stop` |", "| `stopped` | `completion` |"),
        ("### Invocation fields", "| `mode` | yes |", "| `mode` | no |"),
        ("### Run-directory artifacts", "| `input.json` |", "| `inputs.json` |"),
    )

    def test_each_table_catches_a_changed_row(self):
        text = testlib.read_text(DOC)
        work = tempfile.mkdtemp(prefix="iface-mutant-")
        try:
            for heading, old, new in self.MUTATIONS:
                with self.subTest(table=heading):
                    self.assertEqual(text.count(old), 1, "the row to change: %s" % old)
                    mutant = os.path.join(work, "contract.md")
                    testlib.write_text(mutant, text.replace(old, new))
                    proc = subprocess.run(
                        [sys.executable, "-m", "unittest", "test_interface_document.Interface"],
                        cwd=testlib.TESTS, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        env=testlib.base_env({DOC_ENV: mutant}))
                    self.assertNotEqual(proc.returncode, 0, "the mutant passed: %s" % heading)
                    self.assertIn("FAIL", proc.stderr.decode("utf-8", "replace"))
            # the exit codes: one code struck from one command
            row = re.search(r"^\| `select` \| [^|]+ \| ([0-9, ]+) \|$", text, re.M)
            self.assertIsNotNone(row, "the select row")
            mutant = os.path.join(work, "contract.md")
            testlib.write_text(mutant, text.replace(row.group(0), row.group(0).replace(row.group(1),
                                                                                        row.group(1).replace("0, ", "", 1))))
            proc = subprocess.run([sys.executable, "-m", "unittest", "test_interface_document.Interface"],
                                  cwd=testlib.TESTS, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env=testlib.base_env({DOC_ENV: mutant}))
            self.assertNotEqual(proc.returncode, 0, "the exit-code mutant passed")
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
