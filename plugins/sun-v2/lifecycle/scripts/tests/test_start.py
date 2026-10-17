"""RUN-1's start (the owner's ruling, A47), as RUN-1's test line has it.

The shipped entry point `lifecycle/scripts/sun` is started as a child, by `/bin/sh` and its full path, in a
fixture home with nothing else handed to it: no fake, no rows, no code the environment names. Then, one at a
time, the settings of the test line are planted in the session and each start must answer byte-equal to the
start without it, with no marker run. A probe started by the same line as the entry point lists every module
then loaded. No file of the tool declares an outside package or a launcher. The tool's own schema check
refuses a document that breaks a schema and passes one that meets it.
"""
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
ENTRY = os.path.join(SCRIPTS, "sun")
PLUGIN = os.path.dirname(os.path.dirname(SCRIPTS))
STARTS = (["--help"], ["look", "--help"], ["skill-identity"], ["check-examples"], ["look"], ["no-such-command"],
          ["look", "--kind", "sunrise", "--name", "demo", "--inputs", "{}"])


class Starting(unittest.TestCase):
    """What every start of the shipped entry point here shares: a fixture home, the session, the plants."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sunv2-start-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.markers = os.path.join(self.tmp, "markers")
        os.makedirs(self.markers)

    def session(self, **more):
        env = {"HOME": self.home, "USER": os.environ.get("USER", "fixture"), "LOGNAME": os.environ.get("LOGNAME", "fixture"),
               "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        env.update(more)
        return env

    def start(self, argv, env, entry=ENTRY):
        proc = subprocess.run(["/bin/sh", entry] + list(argv), env=env, cwd=self.tmp, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        return proc.returncode, proc.stdout, proc.stderr

    def snapshot(self):
        out = {}
        for base, dirs, files in os.walk(self.home):
            for name in dirs + files:
                p = os.path.join(base, name)
                out[os.path.relpath(p, self.home)] = open(p, "rb").read() if os.path.isfile(p) and not os.path.islink(p) else None
        return out

    def marker_code(self, kind):
        return "import os\nopen(os.path.join(%r, %r), 'w').close()\n" % (self.markers, kind)

    def plants(self):
        """(label, session) for each setting of the test line, planted one at a time."""
        code_dir = os.path.join(self.tmp, "code")
        os.makedirs(code_dir)
        for module in ("json", "argparse", "hashlib"):          # modules of names the tool imports
            with open(os.path.join(code_dir, module + ".py"), "w") as fh:
                fh.write(self.marker_code("pythonpath-" + module))
        site = os.path.join(self.home, "Library", "Python", "3.9", "lib", "python", "site-packages")
        decoys = os.path.join(self.tmp, "decoys")
        os.makedirs(decoys)
        for name in ("python3", "env", "sh", "dirname"):
            path = os.path.join(decoys, name)
            with open(path, "w") as fh:
                fh.write("#!/bin/sh\n: > %s/decoy-%s\nexec /usr/bin/%s \"$@\"\n" % (self.markers, name, name))
            os.chmod(path, 0o755)

        def usercustomize():
            os.makedirs(site, exist_ok=True)
            with open(os.path.join(site, "usercustomize.py"), "w") as fh:
                fh.write(self.marker_code("usercustomize"))
            with open(os.path.join(site, "zz-marker.pth"), "w") as fh:
                fh.write("import os; open(os.path.join(%r, 'pth'), 'w').close()\n" % self.markers)
        return [("DEVELOPER_DIR set to a folder that does not exist", self.session(DEVELOPER_DIR=os.path.join(self.tmp, "no-such-folder")), None),
                ("a Python setting naming a folder of code", self.session(PYTHONPATH=code_dir, PYTHONSTARTUP=os.path.join(code_dir, "json.py"),
                                                                          PYTHONHOME=os.path.join(self.tmp, "no-home")), None),
                ("a customizing module in the account's folder of packages", self.session(), usercustomize),
                ("a decoy first on the session's path", self.session(PATH=decoys + ":" + os.environ.get("PATH", "/usr/bin:/bin")), None)]


class Start(Starting):
    def test_RUN1_A47_the_start_ignores_each_planted_setting_and_runs_no_marker(self):
        base = dict((tuple(a), self.start(a, self.session())) for a in STARTS)
        for argv, (code, out, err) in base.items():
            self.assertNotEqual(code, 127, "the entry point did not start: %s %r" % (argv, err))
        self.assertEqual(os.listdir(self.markers), [])
        for label, env, prepare in self.plants():
            if prepare:
                prepare()
            before = self.snapshot()
            for argv in STARTS:
                with self.subTest(plant=label, argv=argv):
                    self.assertEqual(self.start(argv, env), base[tuple(argv)], "the start did not answer byte-equal")
            self.assertEqual(os.listdir(self.markers), [], "%s: a planted marker ran" % label)
            self.assertEqual(self.snapshot(), before, "%s: the start changed the fixture home" % label)

    def exec_line(self):
        """The one line of the entry point that starts the interpreter (RUN-1's start line)."""
        text = open(ENTRY).read()
        lines = [l for l in text.splitlines() if "/usr/bin/python3" in l and not l.lstrip().startswith("#")]
        self.assertEqual(len(lines), 1, "the entry point has not exactly one line that starts the interpreter")
        return text, lines[0]

    def test_RUN1_A47_the_start_line_is_the_system_shell_and_the_system_python_by_full_paths_with_a_cleared_environment(self):
        text, line = self.exec_line()
        self.assertTrue(text.startswith("#!/bin/sh\n"))
        self.assertIn("/usr/bin/env -i ", line)
        self.assertIn(" /usr/bin/python3 -I -S -B ", line)
        names = re.findall(r"\b([A-Z_][A-Z0-9_]*)=\"\$\{?\1", line.split("/usr/bin/env -i ", 1)[1])
        self.assertEqual(sorted(names), ["HOME", "LOGNAME", "USER"], "the start passes a name the frame has the tool not read")

    def test_RUN1_A47_a_probe_started_by_the_same_line_loads_only_the_tools_files_and_that_pythons_own_library(self):
        text, line = self.exec_line()
        probe = os.path.join(SCRIPTS, "tests", "fixtures", "start-probe.py")
        self.assertIn('"$here/sun.py"', line)
        entry = os.path.join(self.tmp, "probe-entry")
        with open(entry, "w") as fh:
            fh.write(text.replace('"$here/sun.py"', '"%s" "%s"' % (probe, SCRIPTS)))
        code, out, err = self.start([], self.session(PYTHONPATH=self.tmp), entry=entry)
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertNotIn("jsonschema", doc["modules"])
        stdlib = os.path.join(doc["prefix"], "lib", "python%s" % doc["version"])
        outside = [f for f in doc["files"] if not (f.startswith(SCRIPTS + os.sep) or
                                                   (f.startswith(stdlib + os.sep) and os.sep + "site-packages" + os.sep not in f))]
        self.assertEqual(outside, [], "a module loaded from outside the tool's own files and that Python's own library")
        self.assertTrue(any(f.startswith(os.path.join(SCRIPTS, "sun_core")) for f in doc["files"]))
        self.assertEqual(doc["isolated"], 1)

    def test_RUN1_A47_no_file_of_the_tool_declares_an_outside_package_or_a_launcher(self):
        found = []
        for base, dirs, files in os.walk(PLUGIN):
            dirs[:] = [d for d in dirs if d not in ("tests", "evals", "examples")]
            for name in files:
                path = os.path.join(base, name)
                try:
                    text = open(path, encoding="utf-8").read()
                except (UnicodeDecodeError, OSError):
                    continue
                for pattern in (r"# /// script", r"dependencies\s*=", r"#!/usr/bin/env python", r"\buv run\b", r"\bjsonschema\b", r"pip install"):
                    if re.search(pattern, text):
                        found.append((os.path.relpath(path, PLUGIN), pattern))
        self.assertEqual(found, [])

    def test_RUN1_A47_the_tools_own_check_refuses_a_document_that_breaks_a_schema_and_passes_one_that_meets_it(self):
        sys.path.insert(0, SCRIPTS)
        from sun_core import schemas
        doc = json.load(open(os.path.join(PLUGIN, "lifecycle", "references", "examples", "settings", "valid", sorted(
            os.listdir(os.path.join(PLUGIN, "lifecycle", "references", "examples", "settings", "valid")))[0])))
        self.assertEqual(schemas.errors("settings", doc), [])
        broken = dict(doc, settings_version="one")
        self.assertNotEqual(schemas.errors("settings", broken), [])
        self.assertNotEqual(schemas.errors("settings", dict(doc, unknown_field=1)), [])
        self.assertNotIn("jsonschema", sys.modules)


# SEC-12: "The tool's own first code is the code that runs up to the withheld read and makes it: the file the start
# hands to the interpreter, and the modules of the tool that the read uses, whether one or several; no other module of
# the tool is part of it." Written here by hand from the read as built (`withheld.read` and what it loads, the world it
# reads through), and never taken from the code: the test holds the set the code must keep to.
FIRST_CODE = ("sun.py", "sun_core/__init__.py", "sun_core/world.py", "sun_core/fsio.py", "sun_core/facts.py",
              "sun_core/withheld.py", "sun_core/disproofs.py", "sun_core/protected.py", "sun_core/journal.py",
              "sun_core/locks.py", "sun_core/rundir.py", "sun_core/screen.py", "sun_core/texts.py")


def fixed_number():
    """The fixed number of a start that cannot run the tool's own code, as its one place, the entry point, writes it."""
    found = re.findall(r"^FAILED_START=([0-9]+)$", open(ENTRY).read(), re.M)
    return int(found[0]) if found else None


def copy_of_the_tool(dest):
    """A copy of the shipped tool in the test's temporary folder: the entry point, the file it hands to the
    interpreter, every module, the references and the plugin's own record. No test file."""
    lifecycle = os.path.join(PLUGIN, "lifecycle")
    scripts = os.path.join(dest, "lifecycle", "scripts")
    os.makedirs(scripts)
    for name in ("sun", "sun.py"):
        shutil.copy2(os.path.join(SCRIPTS, name), os.path.join(scripts, name))
    shutil.copytree(os.path.join(SCRIPTS, "sun_core"), os.path.join(scripts, "sun_core"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(lifecycle, "references"), os.path.join(dest, "lifecycle", "references"))
    shutil.copy2(os.path.join(lifecycle, "skills.json"), os.path.join(dest, "lifecycle", "skills.json"))
    shutil.copytree(os.path.join(PLUGIN, ".claude-plugin"), os.path.join(dest, ".claude-plugin"))
    return os.path.join(scripts, "sun"), scripts


def cut_short(path):
    """The file cut short so that it cannot be read as code: the shortest cut at or after its middle that does not
    compile. The test asserts that it does not."""
    data = open(path, "rb").read()
    for end in range(len(data) // 2, len(data)):
        try:
            compile(data[:end], path, "exec")
        except SyntaxError:
            with open(path, "wb") as fh:
                fh.write(data[:end])
            return
    raise AssertionError("no cut of %s fails to compile" % path)


class FailedStart(Starting):
    """RUN-1 (A50, A51, A52, A94): "A start that cannot run the tool's own code prints nothing on either output stream and
    ends with one fixed exit number"; its test line: "A failed start, in four cases, the fixture home holding a run that
    has caught a word of the tool's help text, each asked for the tool's help: a copy of the tool in the test's
    temporary folder whose start line points the stand-in at a folder that does not exist; a copy whose start line points
    it at a folder that is there and holds no developer tools, the nearest a test makes of SEC-12's first cause, the
    developer tools missing; a copy in which one file of the first code (SEC-12) is cut short so that it cannot be read as
    code, run once for each of its files in turn, the file the start hands to the interpreter among them; and the shipped
    start, untouched. In the first three, both output streams are empty, to the byte, and the exit number is the fixed
    one; in the fourth, the help is printed with the fixed words of withholding in the caught word's place, and the exit
    number is not the fixed one. A copy in which a module outside the first code is cut short, the first code whole,
    prints the tool's own failure line under the withheld read, the caught word in no output, and its exit number is not
    the fixed one. A probe started by the shipped start's line lists the tool's files loaded at the moment the withheld
    read is made: each is a file of the first code, and none of the tool's other modules (its runner, its forms, a lane's
    rows) is among them. No path of the tool's own code ends with the fixed number: a search of the tool's exit numbers
    finds it written once. The machine's own case, no developer folder chosen and none at its usual places, is asked of no
    test: a test would have to change the machine's own setting or its tools to make it." The test line's second case is
    `test_RUN1_A51_the_developer_tools_missing_a_start_prints_nothing_and_ends_with_the_fixed_number`; its first, third
    and fourth are the first test below."""

    WORD = "ok"      # a word of the tool's help text ("look", "lock"), and of its own failure line ("broken")

    def setUp(self):
        import harness
        Starting.setUp(self)
        self.m = harness.Machine(self.tmp, "fixture-home")
        self.home = self.m.home

    def fixed(self):
        return fixed_number()

    def caught(self):
        import fab
        run = fab.open_run(self.m, "demo")
        fab.catch(self.m, run, self.WORD)
        return run

    def copy(self, label):
        return copy_of_the_tool(os.path.join(self.tmp, "copy-" + label))

    def test_RUN1_A50_A52_a_failed_start_prints_nothing_and_ends_with_the_fixed_number_and_the_shipped_start_does_not(self):
        import harness
        from sun_core import texts
        self.caught()
        fixed = self.fixed()
        word, withheld = self.WORD.encode(), texts.WITHHELD.encode()
        # the first case: the start line points the stand-in at a folder that does not exist
        entry, _scripts = self.copy("stand-in")
        text = open(entry).read()
        pointed = text.replace("/usr/bin/env -i ", "/usr/bin/env -i DEVELOPER_DIR=%s " % os.path.join(self.tmp, "no-such-folder"), 1)
        self.assertNotEqual(pointed, text)
        with open(entry, "w") as fh:
            fh.write(pointed)
        before = harness.tree(self.home)
        self.assertEqual(self.start(["--help"], self.session(), entry=entry), (fixed, b"", b""), "the stand-in pointed at no folder")
        self.assertEqual(harness.tree(self.home), before)
        # the third case: each file of the first code cut short in turn, the file the start hands to the interpreter among them
        # (the second, a folder there with no developer tools, is the test after this one)
        for rel in FIRST_CODE:
            with self.subTest(cut=rel):
                entry, scripts = self.copy(rel.replace("/", "-"))
                cut_short(os.path.join(scripts, rel))
                self.assertEqual(self.start(["--help"], self.session(), entry=entry), (fixed, b"", b""), "%s cut short" % rel)
                self.assertEqual(harness.tree(self.home), before)
        # the fourth case: the shipped start, untouched
        code, out, err = self.start(["--help"], self.session())
        self.assertNotEqual(code, fixed)
        self.assertNotIn(word, out + err)
        self.assertIn(withheld, out, "the help is not printed with the fixed words in the caught word's place")
        self.assertEqual(harness.tree(self.home), before)

    def test_RUN1_A51_the_developer_tools_missing_a_start_prints_nothing_and_ends_with_the_fixed_number(self):
        """SEC-12's first cause of a start that cannot run the tool's first code, "the developer tools missing" (A50; the
        cause A51 records as having no test), run as RUN-1's test line words a failed start, on a copy: the fixture home
        holding a run that has caught a word of the help text, the help asked for. A test cannot take the developer tools
        off the machine, nor change the machine's own setting of where they are; on a copy it can point the stand-in at a
        developer folder that is there and holds no developer tools, which is the stand-in's own other failure beside the
        first case's folder that does not exist: both streams empty, the fixed number, the fixture home byte-equal."""
        import harness
        self.caught()
        fixed = self.fixed()
        empty = os.path.join(self.tmp, "a-developer-folder-with-no-tools")
        os.makedirs(empty)
        # the cause, shown apart from the start: the stand-in pointed there cannot run, and says so on its own stream,
        # which the start must keep from showing; the folder is there (the first case's is not)
        alone = subprocess.run(["/usr/bin/env", "-i", "DEVELOPER_DIR=" + empty, "/usr/bin/python3", "-I", "-S", "-B", "-c", "pass"],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        self.assertNotEqual(alone.returncode, 0, "the stand-in ran with no developer tools in its folder")
        self.assertNotEqual(alone.stderr, b"", "the stand-in printed no line of its own")
        self.assertTrue(os.path.isdir(empty))
        entry, _scripts = self.copy("no-tools")
        text = open(entry).read()
        pointed = text.replace("/usr/bin/env -i ", "/usr/bin/env -i DEVELOPER_DIR=%s " % empty, 1)
        self.assertNotEqual(pointed, text)
        with open(entry, "w") as fh:
            fh.write(pointed)
        before = harness.tree(self.home)
        self.assertEqual(self.start(["--help"], self.session(), entry=entry), (fixed, b"", b""), "the developer tools missing")
        self.assertEqual(harness.tree(self.home), before)
        self.assertEqual(os.listdir(empty), [], "the start put something in the developer folder")

    def test_RUN1_A52_a_module_outside_the_first_code_cut_short_prints_the_tools_own_failure_line_under_the_read(self):
        from sun_core import texts
        fixed = self.fixed()
        for rel in ("sun_core/cli.py", "sun_core/out.py", "sun_core/startup.py"):
            with self.subTest(cut=rel):
                self.assertNotIn(rel, FIRST_CODE)
                entry, scripts = self.copy(rel.replace("/", "-"))
                cut_short(os.path.join(scripts, rel))
                code, out, err = self.start(["--help"], self.session(), entry=entry)
                self.assertNotEqual(code, fixed)
                self.assertEqual(out, b"")
                self.assertEqual(err.decode("utf-8"), texts.FAILURE + "\n", "the tool's own failure line, whole, with no run on record")
                self.assertIn(self.WORD, texts.FAILURE)
        self.caught()
        for rel in ("sun_core/cli.py", "sun_core/out.py", "sun_core/startup.py"):
            with self.subTest(cut=rel, caught=True):
                entry, scripts = self.copy(rel.replace("/", "-") + "-caught")
                cut_short(os.path.join(scripts, rel))
                code, out, err = self.start(["--help"], self.session(), entry=entry)
                self.assertNotEqual(code, fixed)
                self.assertNotIn(self.WORD.encode(), out + err, "the caught word is in the output")
                self.assertEqual(err.decode("utf-8"), texts.WITHHELD + "\n", "the failure line is not passed under the read")

    def test_RUN1_A52_at_the_withheld_read_only_the_first_codes_files_are_loaded(self):
        self.caught()
        text, line = Start.exec_line(self)
        probe = os.path.join(SCRIPTS, "tests", "fixtures", "first-code-probe.py")
        report = os.path.join(self.tmp, "probe.json")
        entry = os.path.join(self.tmp, "probe-entry")
        with open(entry, "w") as fh:
            fh.write(text.replace('"$here/sun.py"', '"%s" "%s" "%s"' % (probe, SCRIPTS, report)))
        code, out, err = self.start(["--help"], self.session(), entry=entry)
        self.assertEqual(code, 0, err)
        doc = json.load(open(report))
        self.assertTrue(doc["reads"], "the probe saw no read of the withheld read")
        loaded = sorted(set(f for files in doc["reads"] for f in files))
        real = os.path.realpath(SCRIPTS)
        expected = sorted(os.path.join(real, rel) for rel in FIRST_CODE)
        self.assertEqual([f for f in loaded if f not in expected], [], "a module outside the first code was loaded at the read")
        for other in ("runner.py", "forms.py", "rows.py", "lanes.py", "cli.py", "out.py", "startup.py"):
            self.assertNotIn(os.path.join(real, "sun_core", other), loaded)
        self.assertIn(os.path.join(real, "sun_core", "withheld.py"), loaded)

    def test_RUN1_A50_the_fixed_number_is_written_once_and_no_path_of_the_tools_code_ends_with_it(self):
        # RUN-1: "That number is written once in the tool, among its exit numbers, and the tool uses it for nothing else"
        # and "No path of the tool's own code ends with the fixed number: a search of the tool's exit numbers finds it
        # written once." Its one place is the entry point's line `FAILED_START=<n>` (brief-5 item 5 (c): the entry point
        # must have it where `sun_core/exits.py` too is gone); `exits.py` lists it in its table of exit numbers and assigns
        # it to no name.
        import ast
        fixed = self.fixed()
        shell = open(ENTRY).read()
        self.assertEqual(len(re.findall(r"^FAILED_START=[0-9]+$", shell, re.M)), 1, "the entry point does not write it once")
        self.assertNotRegex(shell, r"\bexit\s+%d\b" % fixed, "the entry point writes the fixed number a second time")
        source = open(os.path.join(SCRIPTS, "sun_core", "exits.py")).read()
        tree = ast.parse(source)
        numbers = [(n.targets[0].id, n.value.value) for n in tree.body if isinstance(n, ast.Assign)
                   and isinstance(n.value, ast.Constant) and isinstance(n.value.value, int) and isinstance(n.targets[0], ast.Name)]
        self.assertEqual([name for name, value in numbers if value == fixed], [], "exits.py assigns the fixed number a second time")
        self.assertRegex(source, r"(?m)^\s+%d\s+the start could not run" % fixed, "exits.py's table does not list the fixed number")
        files = [os.path.join(SCRIPTS, "sun.py")] + [os.path.join(SCRIPTS, "sun_core", n) for n in sorted(os.listdir(os.path.join(SCRIPTS, "sun_core")))
                                                     if n.endswith(".py")]
        for path in files:
            for node in ast.walk(ast.parse(open(path).read())):
                if isinstance(node, (ast.Attribute, ast.Name)) and getattr(node, "attr", getattr(node, "id", None)) == "FAILED_START":
                    self.fail("%s names the fixed number" % path)
                if isinstance(node, (ast.Return, ast.Call)) and path.endswith(("sun.py", "cli.py")):
                    values = [node.value] if isinstance(node, ast.Return) else list(node.args)
                    for value in values:
                        if isinstance(value, ast.Constant) and value.value == fixed and not isinstance(value.value, bool):
                            self.fail("%s ends a path with the fixed number as a literal" % path)

    def test_RUN1_A50_with_exits_py_gone_and_the_first_code_broken_the_start_still_ends_with_the_fixed_number(self):
        # brief-5 item 5 (c): report-4's choice left this start with no number at all; RUN-1 asks the fixed number of
        # every start that cannot run the tool's own code
        import harness
        self.caught()
        before = harness.tree(self.home)
        entry, scripts = self.copy("no-exits")
        os.remove(os.path.join(scripts, "sun_core", "exits.py"))
        cut_short(os.path.join(scripts, "sun.py"))
        self.assertEqual(self.start(["--help"], self.session(), entry=entry), (self.fixed(), b"", b""))
        self.assertEqual(harness.tree(self.home), before)


class TheInterpretersOwnLines(Starting):
    """Brief-5 item 5 (d), report-4's own note: after the first code has run, a line the interpreter itself writes (a
    `BaseException` beyond `Exception` and `KeyboardInterrupt`, an "Exception ignored in" line, a warning) would print
    outside the withheld read. SEC-12: "No output of the shipped tool stands outside this paragraph"; "every line the
    tool's code prints, the failure of a later module among them, is passed against those values"; SEC-5: "An
    exception is reported as its type and the operation; its message is never printed." Each copy changes one module
    outside the first code; each is asked for the help."""

    def setUp(self):
        import harness
        Starting.setUp(self)
        self.m = harness.Machine(self.tmp, "fixture-home")
        self.home = self.m.home

    def planted(self, label, code):
        entry, scripts = copy_of_the_tool(os.path.join(self.tmp, "copy-" + label))
        path = os.path.join(scripts, "sun_core", "cli.py")
        with open(path, "a") as fh:
            fh.write("\n" + code + "\n")
        return entry

    def test_SEC12_SEC5_after_the_first_code_ran_no_line_of_the_interpreters_own_stands_outside_the_withheld_read(self):
        from sun_core import cli, exits, texts
        cases = (("base-exception", "raise GeneratorExit('marker-base-exception')", True),
                 ("exception-ignored", "class _Late(object):\n    def __del__(self):\n        raise ValueError('marker-ignored')\n_late = _Late()", False),
                 ("warning", "import warnings\nwarnings.warn('marker-warning')", False))
        for label, code, fails in cases:
            with self.subTest(case=label):
                code_, out, err = self.start(["--help"], self.session(), entry=self.planted(label, code))
                for word in (b"marker-", b"Traceback", b"Exception ignored", b"Warning", b"GeneratorExit"):
                    self.assertNotIn(word, out + err, "%s: a line of the interpreter's own stands outside the read" % label)
                if fails:
                    self.assertEqual(err.decode("utf-8"), texts.FAILURE + "\n", "the tool's own failure line, under the read")
                    self.assertEqual((code_, out), (exits.GENERAL, b""))
                else:
                    self.assertEqual(out.decode("utf-8"), cli.HELP.rstrip("\n") + "\n", "the help is not printed whole")
                    self.assertEqual((code_, err), (exits.SUCCESS, b""))


def git(cwd, *argv):
    """Git inside the test's own temporary repository, with a synthetic author and no configuration of the account."""
    home = os.path.join(os.path.dirname(os.path.abspath(cwd)), ".git-home")
    os.makedirs(home, exist_ok=True)
    env = {"HOME": home, "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "fixture",
           "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_NAME": "fixture",
           "GIT_COMMITTER_EMAIL": "fixture@example.invalid", "LANG": "C"}
    proc = subprocess.run(["/usr/bin/git"] + list(argv), cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    if proc.returncode != 0:
        raise AssertionError("git %s: %s" % (" ".join(argv), proc.stderr.decode("utf-8", "replace")))
    return proc.stdout.decode("utf-8").strip()


def commit_all(top):
    git(top, "init", "-q")
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "fixture")
    return git(top, "rev-parse", "HEAD")


class IdentityCommit(Starting):
    """SEC-12 (A54): "The commit an identity answer shows is the commit of the tool's own files as the tool reads it
    itself, in its own process, on this machine ... It is read from the nearest repository at or above the folder of
    the tool's own files, and only where that repository holds those files in its commit. A repository that does not
    hold them, as one that a copy of the tool merely sits inside, is not theirs, and its commit is in no output. Where
    no repository holds them, the answer gives the tool's own fixed words for no commit. A git child's answer of it is
    shown only where it equals that read, as the tool's own copy; where it differs, the answer gives the fixed fact
    that it differs (SEC-4)." SEC-3's test line: "The identity answer's commit, in four places of the fixture copy: at
    the top of a repository of its own, and as a folder that a larger repository holds in its commit, the tool reads
    that repository's commit itself and the answer shows it; placed inside another repository that does not hold it,
    and in no repository at all, the answer gives the fixed words for no commit, and the other repository's commit is
    in no output. A fake git that answers the commit the tool read is shown as the tool's own copy; a fake git that
    answers another commit makes the answer give the fixed fact that it differs, and that other commit is in no
    output." And: "A start that is no summons and starts a child, as the identity command does where it reads the
    commit through a fake git, starts it with no `TMPDIR` among the names of its environment, and the fixture home is
    byte-equal after it." Each copy is started as a child of its own entry point, by /bin/sh, with a fixture home."""

    def setUp(self):
        import harness
        Starting.setUp(self)
        self.m = harness.Machine(self.tmp, "fixture-home")
        self.home = self.m.home

    def identity(self, entry):
        import harness
        before = harness.tree(self.home)
        code, out, err = self.start(["skill-identity"], self.session(), entry=entry)
        self.assertEqual(code, 0, err)
        self.assertEqual(harness.tree(self.home), before, "the identity command changed the fixture home")
        return json.loads(out.decode("utf-8")), out + err

    def test_SEC3_SEC12_A54_the_identity_answers_commit_in_four_places_of_the_fixture_copy(self):
        from sun_core import gitread, results, texts
        # at the top of a repository of its own
        own = os.path.join(self.tmp, "own")
        entry, _ = copy_of_the_tool(own)
        commit = commit_all(own)
        doc, _ = self.identity(entry)
        self.assertEqual(doc["commit"], commit, "a repository of its own: the tool's read commit is not shown")
        self.assertEqual(doc["commit_by_git"], commit, "git's equal answer is not shown as the tool's own copy")
        # as a folder that a larger repository holds in its commit
        larger = os.path.join(self.tmp, "larger")
        entry, _ = copy_of_the_tool(os.path.join(larger, "plugins", "sun-v2"))
        with open(os.path.join(larger, "README.md"), "w") as fh:
            fh.write("a larger fixture repository\n")
        commit = commit_all(larger)
        doc, _ = self.identity(entry)
        self.assertEqual(doc["commit"], commit, "a larger repository that holds it: its commit is not shown")
        # placed inside another repository that does not hold it
        other = os.path.join(self.tmp, "other")
        os.makedirs(other)
        with open(os.path.join(other, "README.md"), "w") as fh:
            fh.write("another fixture repository\n")
        theirs = commit_all(other)
        entry, _ = copy_of_the_tool(os.path.join(other, "sub", "sun-v2"))
        doc, printed = self.identity(entry)
        self.assertEqual(doc["commit"], texts.NO_COMMIT)
        self.assertNotIn(theirs.encode(), printed, "the other repository's commit is in the output")
        self.assertEqual(doc["commit_by_git"], results.DIFFERS, "git's answer of another commit is not the fixed fact")
        # in no repository at all
        bare = os.path.join(self.tmp, "bare", "sun-v2")
        entry, _ = copy_of_the_tool(bare)
        self.assertIsNone(gitread.nearest(bare), "the fixture's temporary folder stands inside a repository")
        doc, printed = self.identity(entry)
        self.assertEqual(doc["commit"], texts.NO_COMMIT)
        self.assertEqual(doc["commit_by_git"], texts.NO_ANSWER)

    def test_SEC12_A54_the_tools_own_read_reads_a_repository_whose_objects_are_packed_and_deltified(self):
        # a mechanism of the read, not a clause of the test line: a repository as git keeps it after a while, its
        # objects in a pack with deltas and its references packed, read by the tool's own code (RUN-1: no git library)
        from sun_core import gitread
        top = os.path.join(self.tmp, "packed")
        entry, scripts = copy_of_the_tool(top)
        commit_all(top)
        with open(os.path.join(scripts, "sun_core", "texts.py"), "a") as fh:
            fh.write("# a second commit, so that the pack holds deltas\n")
        git(top, "commit", "-q", "-a", "-m", "second")
        git(top, "gc", "-q", "--aggressive", "--prune=now")
        head = git(top, "rev-parse", "HEAD")
        self.assertFalse([d for d in os.listdir(os.path.join(top, ".git", "objects")) if len(d) == 2], "objects left loose")
        self.assertTrue(os.path.isfile(os.path.join(top, ".git", "packed-refs")))
        from sun_core import cli
        self.assertEqual(gitread.commit_holding(top, cli.tool_files(top)), head)
        doc, _ = self.identity(entry)
        self.assertEqual(doc["commit"], head)
        # a file of the tool changed on disk: the commit no longer holds those files
        with open(os.path.join(scripts, "sun_core", "texts.py"), "a") as fh:
            fh.write("# changed after the commit\n")
        self.assertIsNone(gitread.commit_holding(top, cli.tool_files(top)))

    def test_SEC3_SEC12_A54_A53_a_fake_git_equal_is_shown_as_the_tools_own_copy_and_another_commit_is_the_fixed_fact(self):
        from sun_core import results
        top = os.path.join(self.tmp, "fake")
        entry, scripts = copy_of_the_tool(top)
        facts = os.path.join(scripts, "sun_core", "facts.py")
        text = open(facts).read()
        passed_over = text.replace('SYSTEM_FOLDERS = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")', "SYSTEM_FOLDERS = ()")
        self.assertNotEqual(passed_over, text, "the copy's search list could not pass the system folders over")
        with open(facts, "w") as fh:
            fh.write(passed_over)        # so that the fake git in the folder the fixture's settings name is the one found
        commit = commit_all(top)
        bin_dir = os.path.join(self.tmp, "fake-bin")
        record = os.path.join(self.tmp, "fake-git-env.txt")
        answer = os.path.join(self.tmp, "fake-git-answer.json")
        os.makedirs(bin_dir)
        with open(os.path.join(bin_dir, "git"), "w") as fh:
            fh.write("#!/bin/sh\n/usr/bin/env | /usr/bin/sed 's/=.*//' > %s\n/bin/cat %s\n" % (record, answer))
        os.chmod(os.path.join(bin_dir, "git"), 0o755)
        self.m.settings["program_folders"] = [bin_dir]
        self.m.write_settings()
        another = "f" * 40
        self.assertNotEqual(another, commit)
        for said, want in ((commit, commit), (another, results.DIFFERS)):
            with self.subTest(fake_git_answers=said):
                with open(answer, "w") as fh:
                    json.dump({"commit": said}, fh)
                if os.path.exists(record):
                    os.remove(record)
                doc, printed = self.identity(entry)
                self.assertEqual(doc["commit"], commit)
                self.assertEqual(doc["commit_by_git"], want)
                if said != commit:
                    self.assertNotIn(said.encode(), printed, "the other commit is in the output")
                names = open(record).read().split()
                self.assertTrue(names, "the fake git was not started")
                self.assertNotIn("TMPDIR", names, "the identity command's child was given a TMPDIR")
                self.assertEqual(sorted(n for n in names if n not in ("PWD", "SHLVL", "_")),
                                 sorted(["HOME", "LANG", "LC_ALL", "LOGNAME", "PATH", "USER"]))


# SEC-12's test line, "Every shipped start, in two fixtures". The seven starts with no summons, as the frame names them.
# The seventh (A53): "a start whose own code runs and finds missing a file of the tool outside its first code ... and
# prints the tool's own failure line"; "The seventh is started so on a copy of the shipped tool in the test's temporary
# folder, the one change to it being a file outside the first code removed." The file removed: `sun_core/cli.py`.
SEVENTH = "a start with what the tool depends on missing"
REMOVED = "sun_core/cli.py"
SEVEN = (("the tool's help", ["--help"]), ("a command's help", ["look", "--help"]), ("the identity command", ["skill-identity"]),
         ("the check of examples", ["check-examples"]), ("a usage error", ["look"]), ("an unknown command", ["no-such-command"]),
         (SEVENTH, ["--help"]))
HOLDING = ("the tool's help", "a command's help", "the identity command", "the check of examples")      # on standard output
HOLDING_ERR = (SEVENTH,)                                                                                  # on standard error


class EveryShippedStart(Starting):
    """The first fixture: the shipped tool itself, each start a child of the shipped entry point, by /bin/sh and its
    full path, with a fixture home as its home and nothing else handed to it (no fake, no code the environment
    names). The reviewer's D8-A closing rule: "Put every shipped output path covered by this interface, including
    help, identity and validation diagnostics, behind the withheld read and screening, with subprocess tests proving
    that caught fixed text cannot escape." The second fixture, the order, is in `test_withheld_read.py`."""

    WORD = "ok"      # stands in the help text ("look"), a command's help, the identity answer and the examples' check

    def setUp(self):
        import harness
        Starting.setUp(self)
        self.m = harness.Machine(self.tmp, "fixture-home")
        self.home = self.m.home

    def entry_for(self, label):
        """The shipped entry point; for the seventh, the copy with one file outside the first code removed."""
        if label != SEVENTH:
            return ENTRY
        if not getattr(self, "seventh_entry", None):
            self.assertNotIn(REMOVED, FIRST_CODE)
            self.seventh_entry, scripts = copy_of_the_tool(os.path.join(self.tmp, "copy-seventh"))
            os.remove(os.path.join(scripts, REMOVED))
        return self.seventh_entry

    def test_SEC12_D8A_every_shipped_start_as_a_child_withholds_a_caught_word_and_ignores_each_planted_setting(self):
        import fab
        import harness
        from sun_core import cli, exits, texts
        word, withheld = self.WORD.encode(), texts.WITHHELD.encode()
        whole = dict((label, self.start(argv, self.session(), entry=self.entry_for(label))) for label, argv in SEVEN)
        self.assertEqual(whole[SEVENTH][2].decode("utf-8"), texts.FAILURE + "\n", "the seventh start does not print the tool's own failure line")
        self.assertNotIn(whole[SEVENTH][0], (fixed_number(), exits.SUCCESS), "the seventh start's exit")
        for label in HOLDING_ERR:
            self.assertIn(word, whole[label][2], "the fixture's word does not stand in the output of %s" % label)
        for label, (code, out, err) in whole.items():
            self.assertNotEqual(code, 127, "%s: the entry point did not start: %r" % (label, err))
            self.assertNotIn(withheld, out + err, "%s: with no run on record something was withheld" % label)
        for label in HOLDING:
            self.assertIn(word, whole[label][1], "the fixture's word does not stand in the output of %s" % label)
        self.assertEqual(whole["the tool's help"][1].decode("utf-8"), cli.HELP.rstrip("\n") + "\n", "the help is not printed whole")
        run = fab.open_run(self.m, "demo")
        fab.catch(self.m, run, self.WORD)
        caught = {}
        for label, argv in SEVEN:
            with self.subTest(start=label):
                before = harness.tree(self.home)
                code, out, err = caught[label] = self.start(argv, self.session(), entry=self.entry_for(label))
                self.assertNotIn(word, out, "%s: the caught word is on standard output" % label)
                self.assertNotIn(word, err, "%s: the caught word is on standard error" % label)
                if label in HOLDING:
                    self.assertIn(withheld, out, "%s: the fixed words of withholding do not stand in the word's place" % label)
                if label in HOLDING_ERR:
                    self.assertIn(withheld, err, "%s: the fixed words of withholding do not stand in the word's place" % label)
                self.assertEqual(code, whole[label][0], "%s: the exit changed" % label)
                self.assertEqual(harness.tree(self.home), before, "%s: the start changed the fixture home" % label)
        for plant, env, prepare in self.plants():
            if prepare:
                prepare()
            before = harness.tree(self.home)
            for label, argv in SEVEN:
                with self.subTest(plant=plant, start=label):
                    self.assertEqual(self.start(argv, env, entry=self.entry_for(label)), caught[label], "the start did not answer byte-equal")
            self.assertEqual(os.listdir(self.markers), [], "%s: a planted marker ran" % plant)
            self.assertEqual(harness.tree(self.home), before, "%s: the start changed the fixture home" % plant)


class HelpsLineBreaks(Starting):
    """The reviewer's D8-N (A139, A142): help screened each of its lines and then wrote the line's break, and its blank
    lines, unscreened. SEC-12: "every write to the journal, a manifest, a form, the CLI's output or an error consults
    it"; the withheld read: "A line of fixed text that holds one of them is not printed, and the fixed words of
    withholding stand in its place"; the register's paragraph: "Where the fixed words of withholding would themselves
    hold an entry, nothing is written in that place." So help screens each complete line, its line break included, as
    the error writer does. The caught record is made by the fixture's own hand (`fab.catch`), not through a
    declaration, since a secret field may no longer admit a line break (A142). Each start is a child of the shipped
    entry point, with the fixture home as its home and nothing else handed to it."""

    HELPS = (("the tool's help", ["--help"]), ("a command's help", ["look", "--help"]))

    def setUp(self):
        import harness
        Starting.setUp(self)
        self.m = harness.Machine(self.tmp, "fixture-home")
        self.home = self.m.home

    def today(self, word):
        """Help's bytes as the tool wrote them before this part, a caught word that is no line break in its text: each line
        that holds the word gives way whole to the fixed words, every other line is written whole, each with its break."""
        from sun_core import cli, texts
        return "".join((texts.WITHHELD if word in line else line) + "\n" for line in cli.HELP.rstrip("\n").split("\n")).encode("utf-8")

    def test_SEC12_D8N_help_with_a_caught_value_that_is_one_line_break_writes_no_line_break_and_nothing_else(self):
        import fab
        import harness
        run = fab.open_run(self.m, "demo")
        fab.catch(self.m, run, "\n")
        for label, argv in self.HELPS:
            with self.subTest(start=label):
                before = harness.tree(self.home)
                code, out, err = self.start(argv, self.session())
                self.assertNotIn(b"\n", out + err, "%s: a caught line break left through help" % label)
                for form in (b"%0A", b"%0a", b"Cg==", b"Cg"):
                    self.assertNotIn(form, out + err, "%s: a form of the caught line break left through help" % label)
                # each line of help, written whole with its break, holds the value; so would the fixed words of withholding
                # written with theirs; "nothing is written in that place"
                self.assertEqual((code, out, err), (0, b"", b""), label)
                self.assertEqual(harness.tree(self.home), before, "%s: the start changed the fixture home" % label)

    def test_SEC12_D8N_help_with_no_caught_value_and_with_a_caught_word_is_byte_equal_to_what_it_was(self):
        import fab
        from sun_core import cli
        for label, argv in self.HELPS:
            with self.subTest(start=label, caught=None):
                self.assertEqual(self.start(argv, self.session()), (0, (cli.HELP.rstrip("\n") + "\n").encode("utf-8"), b""))
        word = "ok"
        self.assertIn(word, cli.HELP)
        run = fab.open_run(self.m, "demo")
        fab.catch(self.m, run, word)
        for label, argv in self.HELPS:
            with self.subTest(start=label, caught=word):
                self.assertEqual(self.start(argv, self.session()), (0, self.today(word), b""))

    @staticmethod
    def forms(value):
        """The forms a leak can take, written here by hand and not taken from the tool's screen (S2): the value whole, its
        percent-encoding plain and with the form encoding's plus, each in capital and in lower-case escapes, and its base64 in
        the standard and the link-safe alphabets, each with and without its padding."""
        import base64
        import urllib.parse
        out = [value]
        for quoted in (urllib.parse.quote(value, safe=""), urllib.parse.quote_plus(value, safe="")):
            out += [quoted, re.sub("%[0-9A-F]{2}", lambda m: m.group(0).lower(), quoted)]
        for encoded in (base64.b64encode(value.encode("utf-8")), base64.urlsafe_b64encode(value.encode("utf-8"))):
            out += [encoded.decode("ascii"), encoded.decode("ascii").rstrip("=")]
        return sorted(set(out))

    def test_SEC12_D8L_help_with_a_caught_value_across_a_lines_end_writes_the_fixed_words_in_place_of_the_whole_help(self):
        """The reviewer's D8-L (check 3, `multiline.py`): help passed each line on its own, so a caught value that spans the
        end of one line and the start of the next left whole across two writes. SEC-12: "every write to the journal, a
        manifest, a form, the CLI's output or an error consults it"; the withheld read: "A line of fixed text that holds one
        of them is not printed, and the fixed words of withholding stand in its place"; the register's paragraph: "Where the
        fixed words of withholding would themselves hold an entry, nothing is written in that place." Brief-27: help passes
        its whole text, as one text, against the screens before any of it is written, as `Printer.document` passes a whole
        document; where it still holds a value, the fixed words with their line break stand in place of the whole help."""
        import fab
        import harness
        from sun_core import cli, texts
        whole = cli.HELP.rstrip("\n") + "\n"
        cases = (("the reviewer's case, a value across a line's end", "gave it," + "\n" + "`--also`"),
                 ("a caught blank line", "\n" + "\n"))
        for index, (case, value) in enumerate(cases):
            self.assertIn(value, whole, "%s: the fixture's value does not stand in help" % case)
            self.assertFalse([line for line in whole.split("\n") if value in line + "\n"], "%s: a single line of help holds it" % case)
            m = harness.Machine(self.tmp, "fixture-home-d8l-%d" % index)
            self.home = m.home
            run = fab.open_run(m, "demo")
            fab.catch(m, run, value)
            for label, argv in self.HELPS:
                with self.subTest(caught=case, start=label):
                    before = harness.tree(self.home)
                    code, out, err = self.start(argv, self.session())
                    for form in self.forms(value):
                        self.assertNotIn(form.encode("utf-8"), out, "%s: the caught value left in standard output as %r" % (label, form))
                        self.assertNotIn(form.encode("utf-8"), err, "%s: the caught value left in standard error as %r" % (label, form))
                    self.assertEqual((code, out, err), (0, (texts.WITHHELD + "\n").encode("utf-8"), b""), label)
                    self.assertEqual(harness.tree(self.home), before, "%s: the start changed the fixture home" % label)


if __name__ == "__main__":
    unittest.main()
