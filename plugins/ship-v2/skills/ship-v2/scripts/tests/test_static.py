"""Static guarantees over this core's own files (CR-24, E15-4; contract section 14), by an AST walk (handoff-v2's
shape, the slice 1b check's C1B1-6).

1. No ship-v2 script starts a process except where it must: every `import` or `from ... import` naming `subprocess`,
   `pty`, `asyncio`, `multiprocessing` or `importlib`, and every `from os import` of `system`, `popen`, `exec*`,
   `spawn*`, `posix_spawn*` or `fork*`, is allowed only in the allowlisted files (`ship_core/gitio.py`, git read only;
   `ship_core/stations.py`, a station's own `skill-identity` and nothing else; `station_core/driver.py`,
   `station_core/records_client.py`, both adapters' `_common.py`); every call of `os.system`, `os.popen`, `os.exec*`,
   `os.spawn*`, `os.posix_spawn*`, `os.fork*` (through any name `os` is bound to, or `getattr` on it),
   `importlib.import_module` or `__import__` fails anywhere (an `__import__` of one literal module name outside that
   list, the frame's `__import__("argparse")`, is not a process start). The walk covers every `.py` file under
   `scripts/` (the copied `station_core`, `back_core` and the second reading's modules included) and both adapters,
   their tests and the vendored reader left out.
2. No ship-v2 script runs a git command that changes a branch, an index or a worktree, and nothing is pushed,
   merged or opened: `gitio.run` refuses any subcommand outside its read-only list at run time, before git starts
   (a changing subcommand planted through a variable is refused), and every literal `["git", ...]` argv in the walked
   files names no changing subcommand.
3. No script launches a harness, a pull-request tool or a station's phase: no literal argv in the walked files starts
   with `claude`, `codex` or `gh` (the adapters' measurement helpers' `--version` probe, a back-frame file, aside),
   and the one station command ship-v2 runs is `skill-identity`.
4. Every subprocess argv is a list; no shell text.
"""
import ast
import os
import re
import unittest

import testlib

testlib.add_scripts_to_path()
from ship_core import gitio  # noqa: E402

FORBIDDEN_MODULES = ("subprocess", "pty", "asyncio", "multiprocessing", "importlib")
OS_STARTS = re.compile(r"^(?:system|popen|exec\w*|spawn\w*|posix_spawn\w*|fork\w*)$")
ALLOWLIST = ("scripts/ship_core/gitio.py", "scripts/ship_core/stations.py", "scripts/station_core/driver.py",
             "scripts/station_core/records_client.py", "adapters/claude-code/_common.py", "adapters/codex/_common.py")
CHANGING = ("add", "commit", "checkout", "switch", "reset", "merge", "rebase", "stash", "push", "pull", "fetch",
            "worktree", "branch", "tag", "restore", "rm", "mv", "cherry-pick", "revert", "update-ref", "update-index",
            "gc", "clean", "apply", "am", "config", "init", "clone", "notes", "replace")
LAUNCHERS = ("claude", "codex", "gh")
# the adapters' measurement helpers (the E9 seam, back-frame files) read the harness binary's own `--version`
VERSION_PROBES = ("adapters/claude-code/_common.py", "adapters/codex/_common.py")


def walked_files():
    """Every `.py` file under `scripts/` and both adapters, their tests and the vendored reader left out."""
    out = []
    for top in ("scripts", os.path.join("adapters", "claude-code"), os.path.join("adapters", "codex")):
        root = os.path.join(testlib.SKILL, top)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in ("tests", "__pycache__", "vendor"))
            for name in sorted(filenames):
                if name.endswith(".py"):
                    path = os.path.join(dirpath, name)
                    out.append((os.path.relpath(path, testlib.SKILL).replace(os.sep, "/"), path))
    return out


def findings(source, rel):
    """Every breach of rules 1, 3, 4 and of rule 2's literal half in one file's source, as (rel, line, words)."""
    tree = ast.parse(source)
    allowed = rel in ALLOWLIST
    os_names = set()
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top == "os":
                    os_names.add(alias.asname or "os")
                if top in FORBIDDEN_MODULES and not allowed:
                    out.append((rel, node.lineno, "import %s" % alias.name))
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if top in FORBIDDEN_MODULES and not allowed:
                out.append((rel, node.lineno, "from %s import" % node.module))
            if top == "os":
                for alias in node.names:
                    if OS_STARTS.match(alias.name) and not allowed:
                        out.append((rel, node.lineno, "from os import %s" % alias.name))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            base, attr = func.value.id, func.attr
            if base in os_names | {"os"} and OS_STARTS.match(attr):
                out.append((rel, node.lineno, "%s.%s()" % (base, attr)))
            if base == "importlib" and attr == "import_module":
                out.append((rel, node.lineno, "importlib.import_module()"))
            if base in ("asyncio",) and attr.startswith("create_subprocess"):
                out.append((rel, node.lineno, "asyncio.%s()" % attr))
        elif isinstance(func, ast.Name) and func.id == "__import__":
            args = node.args
            literal = len(args) == 1 and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str) \
                and not node.keywords
            if not literal or args[0].value.split(".")[0] in FORBIDDEN_MODULES + ("os",):
                out.append((rel, node.lineno, "__import__()"))
        elif isinstance(func, ast.Name) and func.id == "getattr" and len(node.args) >= 2:
            target, name = node.args[0], node.args[1]
            if isinstance(target, ast.Name) and target.id in os_names | {"os"} and \
                    (not isinstance(name, ast.Constant) or OS_STARTS.match(str(name.value))):
                out.append((rel, node.lineno, "getattr(os, ...)"))
        if isinstance(func, ast.Attribute) or isinstance(func, ast.Name):
            for arg in node.args[:1]:
                if isinstance(arg, ast.List) and arg.elts and isinstance(arg.elts[0], ast.Constant):
                    first = arg.elts[0].value
                    words = [e.value for e in arg.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                    if first == "git":
                        changing = [w for w in words if w in CHANGING]
                        if changing:
                            out.append((rel, node.lineno, "git %s" % changing[0]))
                    if first in LAUNCHERS and not (rel in VERSION_PROBES and words[1:2] == ["--version"]):
                        out.append((rel, node.lineno, "launches %s" % first))
        for keyword in node.keywords:
            if keyword.arg == "shell" and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False):
                out.append((rel, node.lineno, "shell="))
    return out


def text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class NoProcessStartOutsideTheAllowlist(unittest.TestCase):

    def test_the_walk_finds_the_core_files(self):
        names = [rel for rel, _ in walked_files()]
        for rel in ("scripts/ship.py", "scripts/ship_core/gitio.py", "scripts/ship_core/stations.py",
                    "scripts/ship_core/visit.py", "scripts/ship_core/fix.py", "scripts/ship_core/pause.py",
                    "scripts/station_core/driver.py", "scripts/back_core/trace.py", "adapters/claude-code/hook.py",
                    "adapters/codex/hook.py"):
            self.assertIn(rel, names)
        self.assertFalse([rel for rel in names if "/tests/" in rel or "/vendor/" in rel])

    def test_the_core_files_hold_the_rule(self):
        found = []
        for rel, path in walked_files():
            found += findings(text(path), rel)
        self.assertEqual(found, [])

    def test_every_plant_is_seen(self):
        plants = [
            "import os, subprocess\n",
            "import sys as s, subprocess as sp\n",
            "import importlib\nimportlib.import_module('subprocess')\n",
            "import os\nos.spawnvp(os.P_WAIT, 'git', ['git', 'commit'])\n",
            "from os import system as run_it\nrun_it('git push')\n",
            "import os as o\no.system('git merge')\n",
            "import os\ngetattr(os, 'system')('git commit')\n",
            "__import__('subprocess').run(['git', 'commit'])\n",
            "import multiprocessing\n",
            "from subprocess import run\n",
            "import os\nos.execvp('git', ['git'])\n",
        ]
        for plant in plants:
            self.assertTrue(findings(plant, "scripts/ship_core/visit.py"), plant)

    def test_a_literal_changing_git_argv_or_a_launcher_is_seen_even_where_processes_are_allowed(self):
        for plant in ("import subprocess\nsubprocess.run(['git', '-C', ws, 'push', 'origin'])\n",
                      "import subprocess\nsubprocess.run(['git', 'merge', 'feat'])\n",
                      "import subprocess\nsubprocess.run(['gh', 'pr', 'create'])\n",
                      "import subprocess\nsubprocess.run(['claude', '-p', 'x'])\n",
                      "import subprocess\nsubprocess.run(['codex', 'exec', 'x'])\n",
                      "subprocess.run(['git', 'status'], shell=True)\n"):
            self.assertTrue(findings(plant, "scripts/ship_core/gitio.py"), plant)

    def test_an_allowlisted_file_may_import_subprocess(self):
        self.assertEqual(findings("import subprocess\n", "scripts/ship_core/stations.py"), [])


class NoChangingGitAtRunTime(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-static-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = testlib.git_workspace(self.tmp, "workspace", {"README.md": "x\n"})

    def test_a_changing_subcommand_through_a_variable_is_refused_before_git_runs(self):
        head = testlib.git(self.ws, ["rev-parse", "HEAD"]).strip()
        testlib.write_text(os.path.join(self.ws, "new.txt"), "y\n")
        for sub in ("add", "commit", "checkout", "stash", "push", "merge", "worktree", "branch", "reset"):
            with self.assertRaises(gitio.GitRefused):
                gitio.run(self.ws, [sub])
        with self.assertRaises(gitio.GitRefused):
            gitio.run(self.ws, ["-c", "user.name=x", "commit"])
        self.assertEqual(testlib.git(self.ws, ["rev-parse", "HEAD"]).strip(), head)
        self.assertEqual(testlib.git(self.ws, ["status", "--porcelain"]).strip(), "?? new.txt")

    def test_every_read_the_core_makes_is_on_the_list(self):
        for sub in ("rev-parse", "status", "diff"):
            self.assertIn(sub, gitio.READ_ONLY)
        self.assertFalse(set(gitio.READ_ONLY) & set(CHANGING))


class TheOneStationCommand(unittest.TestCase):

    def test_ship_runs_a_station_only_for_its_identity(self):
        from ship_core import stations  # noqa: E402
        self.assertEqual(stations.COMMAND, "skill-identity")
        body = text(os.path.join(testlib.SCRIPTS, "ship_core", "stations.py"))
        self.assertEqual(body.count("subprocess.run("), 1)


if __name__ == "__main__":
    unittest.main()
