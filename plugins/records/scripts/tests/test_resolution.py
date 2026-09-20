"""Contract section 12.1: how a station reaches this component, proved on a checkout.

There is no station in E12, so the resolution is documented rather than built into a station:
`references/interface.md` carries the two snippets, one Python and one POSIX shell, under the
markers `<!-- resolver: python -->` and `<!-- resolver: sh -->`. This suite EXTRACTS them from
that document and runs them, so the thing tested is the thing a station would copy.

Each is exercised on a real checkout, for all three routes in order, for a candidate that exists
but holds no `scripts/records.py`, and for the not-found message. No fourth lookup exists, and
this suite proves that too: a component that sits somewhere none of the three names is not found.
"""
import os
import re
import subprocess
import tempfile
import unittest

import testlib

MESSAGE = "missing dependency: records component (looked in: "
PYTHON_MARKER = "<!-- resolver: python -->"
SH_MARKER = "<!-- resolver: sh -->"
INTERFACE = os.path.join(testlib.REFERENCES, "interface.md")
# the checkout this component sits in: `plugins/recheck-v2` stands in for a station plugin root,
# whose sibling `plugins/records` is this component. Both are read as paths only.
CHECKOUT = testlib.REPO
STATION_ON_A_CHECKOUT = os.path.join(CHECKOUT, "plugins", "recheck-v2")
COMPONENT_ON_A_CHECKOUT = os.path.join(CHECKOUT, "plugins", "records")


def snippet(marker):
    """The fenced block that follows a marker in interface.md."""
    with open(INTERFACE, encoding="utf-8") as fh:
        text = fh.read()
    if marker not in text:
        raise AssertionError("interface.md carries no %s marker" % marker)
    after = text.split(marker, 1)[1]
    block = re.search(r"```[a-z]*\n(.*?)```", after, re.S)
    if block is None:
        raise AssertionError("no fenced block after %s in interface.md" % marker)
    return block.group(1)


class ResolverCase(unittest.TestCase):
    """One test body per snippet: `resolve` runs the snippet and returns (exit, stdout, stderr)."""

    def setUp(self):
        self.scratch = testlib.make_scratch("records-resolve-")
        self.empty = os.path.join(self.scratch, "empty-dir")
        os.makedirs(self.empty)
        self.station_without_a_sibling = os.path.join(self.scratch, "plugins", "station")
        os.makedirs(self.station_without_a_sibling)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    def resolve(self, argument=None, station=None, environ=None):
        raise NotImplementedError

    def assert_found(self, result, expected):
        code, out, err = result
        self.assertEqual(code, 0, err)
        self.assertEqual(os.path.realpath(out.strip()), os.path.realpath(expected))

    def assert_not_found(self, result, *named):
        code, out, err = result
        self.assertEqual(code, 3, out)
        self.assertEqual(out.strip(), "")
        self.assertTrue(err.strip().startswith(MESSAGE),
                        "the message is not the contract's: %r" % err)
        for path in named:
            self.assertIn(path, err)


class TheSnippetsResolve(object):
    """The eight checks, run against whichever snippet the subclass drives."""

    def test_route_1_the_argument(self):
        self.assert_found(self.resolve(argument=COMPONENT_ON_A_CHECKOUT),
                          COMPONENT_ON_A_CHECKOUT)

    def test_route_2_the_environment_variable(self):
        self.assert_found(self.resolve(environ={"RECORDS_ROOT": COMPONENT_ON_A_CHECKOUT}),
                          COMPONENT_ON_A_CHECKOUT)

    def test_route_3_the_plugin_beside_the_station(self):
        self.assert_found(self.resolve(station=STATION_ON_A_CHECKOUT),
                          COMPONENT_ON_A_CHECKOUT)

    def test_the_argument_wins_over_the_variable_and_the_sibling(self):
        self.assert_found(
            self.resolve(argument=COMPONENT_ON_A_CHECKOUT, station=self.station_without_a_sibling,
                         environ={"RECORDS_ROOT": self.empty}),
            COMPONENT_ON_A_CHECKOUT)

    def test_the_variable_wins_over_the_sibling(self):
        self.assert_found(
            self.resolve(station=self.station_without_a_sibling,
                         environ={"RECORDS_ROOT": COMPONENT_ON_A_CHECKOUT}),
            COMPONENT_ON_A_CHECKOUT)

    def test_a_candidate_that_holds_no_records_py_is_passed_over(self):
        """The rule is "the first that HOLDS scripts/records.py", not "the first that exists"."""
        self.assert_found(
            self.resolve(argument=self.empty, environ={"RECORDS_ROOT": COMPONENT_ON_A_CHECKOUT}),
            COMPONENT_ON_A_CHECKOUT)

    def test_nothing_found_is_exit_3_with_the_contracts_message(self):
        self.assert_not_found(
            self.resolve(argument=self.empty, station=self.station_without_a_sibling,
                         environ={"RECORDS_ROOT": self.empty}),
            self.empty, self.station_without_a_sibling)

    def test_no_fourth_lookup(self):
        """A component none of the three names is not found, however close it sits."""
        elsewhere = os.path.join(self.scratch, "plugins", "records-elsewhere")
        os.makedirs(os.path.join(elsewhere, "scripts"))
        testlib.write(os.path.join(elsewhere, "scripts", "records.py"), "# a decoy\n")
        self.assert_not_found(self.resolve(station=self.station_without_a_sibling),
                              self.station_without_a_sibling)

    def test_nothing_given_at_all_is_still_the_same_refusal(self):
        code, out, err = self.resolve()
        self.assertEqual(code, 3, out)
        self.assertIn("nothing given", err)


class ThePythonSnippet(ResolverCase, TheSnippetsResolve):
    def resolve(self, argument=None, station=None, environ=None):
        path = os.path.join(self.scratch, "records_root.py")
        testlib.write(path, snippet(PYTHON_MARKER))
        argv = [testlib.FLOOR_PYTHON, path]
        if argument:
            argv += ["--records-root", argument]
        if station:
            argv += ["--station-plugin-root", station]
        env = dict(os.environ)
        env.pop("RECORDS_ROOT", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env.update(environ or {})
        proc = subprocess.run(argv, cwd=tempfile.gettempdir(), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
                proc.stderr.decode("utf-8", "replace"))


class TheShellSnippet(ResolverCase, TheSnippetsResolve):
    def resolve(self, argument=None, station=None, environ=None):
        function = os.path.join(self.scratch, "records_root.sh")
        testlib.write(function, snippet(SH_MARKER))
        driver = os.path.join(self.scratch, "drive.sh")
        testlib.write(driver, '. "$1"\nrecords_root "$2" "$3"\n')
        env = dict(os.environ)
        env.pop("RECORDS_ROOT", None)
        env.update(environ or {})
        proc = subprocess.run(["/bin/sh", driver, function, argument or "", station or ""],
                              cwd=tempfile.gettempdir(), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
                proc.stderr.decode("utf-8", "replace"))


class TheDocumentCarriesBothSnippets(unittest.TestCase):
    def test_the_python_snippet_is_there_and_is_python(self):
        text = snippet(PYTHON_MARKER)
        self.assertIn("def records_root(", text)
        self.assertIn("RECORDS_ROOT", text)
        compile(text, "<interface.md python snippet>", "exec")

    def test_the_shell_snippet_is_there_and_parses(self):
        text = snippet(SH_MARKER)
        self.assertIn("records_root()", text)
        path = os.path.join(tempfile.mkdtemp(prefix="records-sh-"), "snippet.sh")
        try:
            testlib.write(path, text)
            proc = subprocess.run(["/bin/sh", "-n", path],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        finally:
            testlib.rmtree(os.path.dirname(path))

    def test_both_name_the_three_routes_in_the_contracts_order(self):
        for text, argument_token, sibling_token in (
                (snippet(PYTHON_MARKER), "argument", "os.pardir"),
                (snippet(SH_MARKER), '"$1"', "/../records")):
            body = text.split("records_root", 1)[1]
            self.assertLess(body.index(argument_token), body.index("RECORDS_ROOT"), text)
            self.assertLess(body.index("RECORDS_ROOT"), body.index(sibling_token), text)

    def test_the_component_root_this_suite_points_at_is_the_real_one(self):
        self.assertTrue(os.path.isfile(os.path.join(COMPONENT_ON_A_CHECKOUT, "scripts", "records.py")))
        self.assertTrue(os.path.isdir(STATION_ON_A_CHECKOUT),
                        "the checkout's station stand-in is gone; route 3 would not be exercised")


if __name__ == "__main__":
    unittest.main()
