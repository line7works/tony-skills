"""Contract section 12.1 as amendment A6 rules it: how a station reaches this component.

There is no station in E12, so the resolution is documented rather than built into a station:
`references/interface.md` carries the two snippets, one Python and one POSIX shell, under the
markers `<!-- resolver: python -->` and `<!-- resolver: sh -->`. This suite EXTRACTS them from
that document and runs them, so the thing tested is the thing a station would copy.

The ruled order is four lookups: the `--records-root` argument, `RECORDS_ROOT`, route 3a
(`<station plugin root>/../records`, the checkout shape), route 3b
(`<station plugin root>/../../records/<V>/`, the installed shape). Routes 1, 2 and 3a are
exercised on a real checkout; route 3b is exercised against a fake installed cache built in a
temporary directory (never a live `~/.claude` or `~/.codex`, which this suite never reads).
Nothing beyond the four is searched, and this suite proves that too. The confirm step
(`component-identity`'s `interface_version`) is exercised against real and stubbed components,
and the two snippets are held to the same messages byte for byte.
"""
import json
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
# a stand-in component: `component-identity` and nothing else, so a fake cache is cheap.
STUB = ("import json, sys\n"
        "sys.stdout.write(json.dumps({\"ok\": True, \"interface_version\": %d,\n"
        "                             \"name\": \"records\", \"version\": %s}))\n")


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


def child_env(environ=None):
    """The environment every snippet run gets: no inherited RECORDS_ROOT, no bytecode written."""
    env = dict(os.environ)
    env.pop("RECORDS_ROOT", None)
    env.pop("RECORDS_PYTHON", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(environ or {})
    return env


def run_python_snippet(scratch, argument=None, station=None, environ=None, known=None):
    path = os.path.join(scratch, "records_root.py")
    testlib.write(path, snippet(PYTHON_MARKER))
    argv = [testlib.FLOOR_PYTHON, path]
    if argument:
        argv += ["--records-root", argument]
    if station:
        argv += ["--station-plugin-root", station]
    if known:
        argv += ["--known-interface-versions", known]
    proc = subprocess.run(argv, cwd=tempfile.gettempdir(), env=child_env(environ),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def run_sh_snippet(scratch, argument=None, station=None, environ=None, known=None):
    function = os.path.join(scratch, "records_root.sh")
    testlib.write(function, snippet(SH_MARKER))
    driver = os.path.join(scratch, "drive.sh")
    testlib.write(driver,
                  '. "$1"\n'
                  'root=$(records_root "$2" "$3") || exit 3\n'
                  'records_confirm "$root" "$4" >/dev/null || exit 3\n'
                  'printf \'%s\\n\' "$root"\n')
    proc = subprocess.run(["/bin/sh", driver, function, argument or "", station or "",
                           known or "2"],  # E13 A7: the snippet's default is 2
                          cwd=tempfile.gettempdir(), env=child_env(environ),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


class ResolverCase(unittest.TestCase):
    """One test body per snippet: `resolve` runs the snippet and returns (exit, stdout, stderr)."""

    def setUp(self):
        self.scratch = testlib.make_scratch("records-resolve-")
        self.empty = os.path.join(self.scratch, "empty-dir")
        os.makedirs(self.empty)
        self.station_without_a_sibling = os.path.join(self.scratch, "plugins", "station")
        os.makedirs(self.station_without_a_sibling)
        # the installed shape both harnesses measured: <cache>/<marketplace>/<plugin>/<version>/,
        # so the station's own root carries its version and route 3b is <cache>/<mk>/records/<V>/.
        self.marketplace = os.path.join(self.scratch, "cache", "a-marketplace")
        self.station = os.path.join(self.marketplace, "station", "0.3.0")
        self.installed_base = os.path.join(self.marketplace, "records")
        # the same directory as `installed_base`, spelled the way a snippet builds it from the
        # station's root, which is how the not-found message names it.
        self.named_base = os.path.join(self.station, os.pardir, os.pardir, "records")
        os.makedirs(self.station)

    def tearDown(self):
        testlib.rmtree(self.scratch)

    # ---- fixtures ------------------------------------------------------------------------

    def installed(self, name, version=None, records_py=True, manifest=True,
                  interface_version=2, body=None):
        """One folder under route 3b's directory. Returns its path, spelled as the message does.

        `version` is what the folder's own plugin.json claims; None means the folder's name.
        `manifest` False writes no plugin.json at all; `version` False writes one without a
        `version`; a `version` of "" writes a manifest that is not JSON.
        """
        folder = os.path.join(self.installed_base, name)
        os.makedirs(folder)
        if manifest:
            claimed = name if version is None else version
            if claimed == "":
                testlib.write(os.path.join(folder, ".claude-plugin", "plugin.json"), "not json")
            elif claimed is False:
                testlib.write_json(os.path.join(folder, ".claude-plugin", "plugin.json"),
                                   {"name": "records"})
            else:
                testlib.write_json(os.path.join(folder, ".claude-plugin", "plugin.json"),
                                   {"name": "records", "version": claimed})
        if records_py:
            testlib.write(os.path.join(folder, "scripts", "records.py"),
                          body if body is not None
                          else STUB % (interface_version, json.dumps(name)))
        return os.path.join(self.named_base, name)

    def stub_component(self, name, interface_version=2, body=None):
        """A component root outside any cache, for the confirm step's own tests."""
        root = os.path.join(self.scratch, name)
        testlib.write(os.path.join(root, "scripts", "records.py"),
                      body if body is not None else STUB % (interface_version, json.dumps(name)))
        return root

    # ---- driving -------------------------------------------------------------------------

    def resolve(self, argument=None, station=None, environ=None, known=None):
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
        self.assertEqual(len(err.strip().split("\n")), 1, "the message is not one line: %r" % err)
        for path in named:
            self.assertIn(path, err)

    def assert_rejected(self, result, folder, why):
        """The not-found message names one folder with its reason, in the ruled few words."""
        code, out, err = result
        self.assertEqual(code, 3, out)
        self.assertIn("%s (%s)" % (folder, why), err)

    def assert_refused(self, result, *fragments):
        """The confirm step's refusal: exit 3, one line on stderr, nothing on stdout."""
        code, out, err = result
        self.assertEqual(code, 3, out)
        self.assertEqual(out.strip(), "")
        self.assertEqual(len(err.strip().split("\n")), 1, "not one line: %r" % err)
        for fragment in fragments:
            self.assertIn(fragment, err)


class TheSnippetsResolve(object):
    """Every check, run against whichever snippet the subclass drives."""

    # ---- routes 1, 2 and 3a, on a real checkout ------------------------------------------

    def test_route_1_the_argument(self):
        self.assert_found(self.resolve(argument=COMPONENT_ON_A_CHECKOUT),
                          COMPONENT_ON_A_CHECKOUT)

    def test_route_2_the_environment_variable(self):
        self.assert_found(self.resolve(environ={"RECORDS_ROOT": COMPONENT_ON_A_CHECKOUT}),
                          COMPONENT_ON_A_CHECKOUT)

    def test_route_3a_the_plugin_beside_the_station_on_a_checkout(self):
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

    def test_nothing_given_at_all_is_still_the_same_refusal(self):
        code, out, err = self.resolve()
        self.assertEqual(code, 3, out)
        self.assertIn("nothing given", err)

    def test_route_3bs_directory_is_named_even_when_it_is_not_there(self):
        self.assert_not_found(self.resolve(station=self.station_without_a_sibling),
                              os.path.join(self.station_without_a_sibling, "..", "..", "records")
                              + " (no such directory)")

    # ---- A6 case 1: one labeled folder ---------------------------------------------------

    def test_3b_one_labeled_folder_is_picked(self):
        folder = self.installed("0.4.0")
        self.assert_found(self.resolve(station=self.station), folder)

    def test_3b_a_name_that_differs_from_its_version_is_never_a_candidate(self):
        """The negative of the case above: the same folder, renamed, is no longer picked."""
        folder = self.installed("0.4.0-rc", version="0.4.0")
        result = self.resolve(station=self.station)
        self.assert_not_found(result, self.named_base)
        self.assert_rejected(result, folder, "name differs from version 0.4.0")

    # ---- A6 case 2: several labeled folders ----------------------------------------------

    def test_3b_the_highest_dotted_integer_version_wins(self):
        """`0.10.0` beats `0.9.0`: text order and integer order disagree here."""
        self.installed("0.9.0")
        self.installed("0.2.0")
        winner = self.installed("0.10.0")
        self.assert_found(self.resolve(station=self.station), winner)

    def test_3b_modification_time_never_decides_between_labeled_folders(self):
        """The negative: the newest folder by mtime is the LOWER version, and still loses."""
        newest = self.installed("0.9.0")
        winner = self.installed("0.10.0")
        old, new = 1_400_000_000, 1_800_000_000
        for path in (winner, os.path.join(winner, "scripts", "records.py")):
            os.utime(path, (old, old))
        for path in (newest, os.path.join(newest, "scripts", "records.py")):
            os.utime(path, (new, new))
        self.assertGreater(os.stat(newest).st_mtime, os.stat(winner).st_mtime)
        self.assert_found(self.resolve(station=self.station), winner)

    # ---- A6 case 3: hash-named and unlabeled folders beside a labeled one ------------------

    def test_3b_a_labeled_folder_beats_hash_named_and_unlabeled_neighbours(self):
        labeled = self.installed("0.2.0")
        hashed = self.installed("9f3c1ab5d27e4408b6c0d1e2f3a4b5c6d7e8f901", manifest=False)
        self.installed("nightly", version=False)
        old, new = 1_400_000_000, 1_800_000_000
        os.utime(labeled, (old, old))
        os.utime(hashed, (new, new))
        self.assertGreater(os.stat(hashed).st_mtime, os.stat(labeled).st_mtime)
        self.assertTrue(os.path.isfile(os.path.join(hashed, "scripts", "records.py")),
                        "the hash-named decoy must hold a working component to be a real decoy")
        self.assert_found(self.resolve(station=self.station), labeled)

    def test_3b_with_the_labeled_folder_gone_every_rejection_is_named(self):
        """The negative: nothing is picked, and each rejected folder is named with its reason."""
        hashed = self.installed("9f3c1ab5d27e4408b6c0d1e2f3a4b5c6d7e8f901", manifest=False)
        unlabeled = self.installed("nightly", version=False)
        unreadable = self.installed("0.7.0", version="")
        result = self.resolve(station=self.station)
        self.assert_not_found(result, self.named_base)
        self.assert_rejected(result, hashed, "no plugin.json")
        self.assert_rejected(result, unlabeled, "no version")
        self.assert_rejected(result, unreadable, "plugin.json unreadable")

    # ---- A6 case 4: a labeled folder without scripts/records.py ---------------------------

    def test_3b_a_labeled_folder_without_records_py_loses_to_a_lower_one_that_has_it(self):
        self.installed("0.5.0", records_py=False)
        lower = self.installed("0.4.0")
        self.assert_found(self.resolve(station=self.station), lower)

    def test_3b_a_labeled_folder_without_records_py_is_rejected_by_name(self):
        """The negative: alone, it is not picked, and the reason is the ruled one."""
        folder = self.installed("0.5.0", records_py=False)
        result = self.resolve(station=self.station)
        self.assert_not_found(result, self.named_base)
        self.assert_rejected(result, folder, "no scripts/records.py")

    # ---- A6 case 5: nothing acceptable ----------------------------------------------------

    def test_3b_nothing_acceptable_is_exit_3_with_every_candidate_named(self):
        folders = {
            self.installed("abc1234", manifest=False): "no plugin.json",
            self.installed("nightly", version=False): "no version",
            self.installed("latest", version="1.2.0"): "name differs from version 1.2.0",
            self.installed("1.2.x", version="1.2.x"): "version not dotted integers",
            self.installed("2.0.0", records_py=False): "no scripts/records.py",
        }
        result = self.resolve(station=self.station)
        self.assert_not_found(result, self.named_base)
        for folder, why in folders.items():
            self.assert_rejected(result, folder, why)

    def test_3b_a_version_that_is_not_dotted_integers_is_never_compared_as_text(self):
        """`1.2.x` would sort above `1.2.0` as text; it is rejected instead."""
        lower = self.installed("1.2.0")
        self.installed("1.2.x", version="1.2.x")
        self.assert_found(self.resolve(station=self.station), lower)

    def test_3b_a_leading_zero_component_is_not_a_dotted_integer(self):
        """`1.0` and `01.0` would share one integer key, so `01.0` is rejected and `1.0` wins.

        Without this there is a real tie: two differently named folders, one key, and whichever
        folder the reading code happened to keep.
        """
        self.installed("0.9.0")
        self.installed("0.10.0")
        self.installed("01.0", version="01.0")
        winner = self.installed("1.0", version="1.0")
        self.assert_found(self.resolve(station=self.station), winner)

    def test_3b_a_leading_zero_folder_alone_is_rejected_by_name(self):
        """The negative: with `1.0` gone nothing is picked, and `01.0`'s reason is named."""
        rejected = self.installed("01.0", version="01.0")
        also = self.installed("1.00", version="1.00")
        result = self.resolve(station=self.station)
        self.assert_not_found(result, self.named_base)
        self.assert_rejected(result, rejected, "version not dotted integers")
        self.assert_rejected(result, also, "version not dotted integers")

    def test_3b_a_bare_zero_and_a_zero_first_version_stay_valid(self):
        """`0` and `0.10.0` are dotted integers; only a padded component is not."""
        self.installed("0", version="0")
        winner = self.installed("0.10.0")
        self.assert_found(self.resolve(station=self.station), winner)

    # ---- the order of the four ------------------------------------------------------------

    def test_3a_wins_over_3b(self):
        beside = os.path.join(self.marketplace, "station", "records")
        testlib.write(os.path.join(beside, "scripts", "records.py"), STUB % (2, '"beside"'))
        self.installed("9.9.9")
        self.assert_found(self.resolve(station=self.station), beside)

    def test_routes_1_and_2_win_over_3a_and_3b(self):
        beside = os.path.join(self.marketplace, "station", "records")
        testlib.write(os.path.join(beside, "scripts", "records.py"), STUB % (2, '"beside"'))
        self.installed("9.9.9")
        self.assert_found(self.resolve(argument=COMPONENT_ON_A_CHECKOUT, station=self.station),
                          COMPONENT_ON_A_CHECKOUT)
        self.assert_found(self.resolve(station=self.station,
                                       environ={"RECORDS_ROOT": COMPONENT_ON_A_CHECKOUT}),
                          COMPONENT_ON_A_CHECKOUT)

    def test_no_fifth_lookup(self):
        """A component none of the four names is not found, however close it sits.

        Three decoys: a sibling of the station's own parent, a folder one level above route 3b's
        directory, and a folder nested a level below an acceptable version's place.
        """
        for where in (os.path.join(self.marketplace, "records-elsewhere"),
                      os.path.join(self.scratch, "cache", "records"),
                      os.path.join(self.installed_base, "0.4.0", "inner", "0.4.0")):
            testlib.write(os.path.join(where, "scripts", "records.py"), STUB % (1, '"decoy"'))
            testlib.write_json(os.path.join(where, ".claude-plugin", "plugin.json"),
                               {"name": "records", "version": "0.4.0"})
        self.assert_not_found(self.resolve(station=self.station), self.named_base)

    def test_no_walk_upward_and_no_look_inside_the_station(self):
        """Nothing above route 3b's directory is reached, and nothing under the station's own root.

        Route 3b globs `<station plugin root>/../../records/*` and stops there: it never walks
        further up, and it never treats that directory itself as a component root.
        """
        for where in (os.path.join(self.scratch, "records"),
                      os.path.join(self.scratch, "cache", "records"),
                      os.path.join(self.station, "records"),
                      self.installed_base):
            testlib.write(os.path.join(where, "scripts", "records.py"), STUB % (1, '"decoy"'))
            testlib.write_json(os.path.join(where, ".claude-plugin", "plugin.json"),
                               {"name": "records", "version": "0.4.0"})
        self.assert_not_found(self.resolve(station=self.station), self.named_base)

    # ---- the confirm step -----------------------------------------------------------------

    def test_the_confirm_step_passes_on_interface_version_1(self):
        root = self.stub_component("speaks-1", interface_version=1)
        self.assert_found(self.resolve(argument=root, known="1"), root)

    def test_the_confirm_step_exits_3_on_an_unknown_interface_version(self):
        root = self.stub_component("speaks-2", interface_version=2)
        self.assert_refused(self.resolve(argument=root, known="1"),
                            "missing dependency: records component at",
                            root, "speaks interface version 2, not 1")

    def test_the_confirm_step_accepts_a_version_the_station_does_know(self):
        root = self.stub_component("speaks-2", interface_version=2)
        self.assert_found(self.resolve(argument=root, known="1 2"), root)

    def test_the_confirm_step_exits_3_on_a_records_py_that_prints_no_json(self):
        root = self.stub_component("mute", body="import sys\nsys.stdout.write('not json\\n')\n")
        self.assert_refused(self.resolve(argument=root, known="1"),
                            root, "did not report an interface version")

    def test_the_confirm_step_exits_3_when_records_py_fails(self):
        root = self.stub_component("broken", body="import sys\nsys.exit(1)\n")
        self.assert_refused(self.resolve(argument=root, known="1"),
                            root, "did not report an interface version")

    def test_the_confirm_step_runs_on_a_root_route_3b_picked(self):
        """The confirm step is on whatever root ANY route returns, 3b included."""
        self.installed("0.6.0", interface_version=7)
        self.assert_refused(self.resolve(station=self.station, known="1"),
                            "speaks interface version 7, not 1")


class ThePythonSnippet(ResolverCase, TheSnippetsResolve):
    def resolve(self, argument=None, station=None, environ=None, known=None):
        return run_python_snippet(self.scratch, argument, station, environ, known)


class TheShellSnippet(ResolverCase, TheSnippetsResolve):
    def resolve(self, argument=None, station=None, environ=None, known=None):
        return run_sh_snippet(self.scratch, argument, station, environ, known)


class TheTwoSnippetsAgree(ResolverCase):
    """A6 requires one rule, not two: the same pick and the same message text from both."""

    def both(self, **kwargs):
        return (run_python_snippet(self.scratch, **kwargs),
                run_sh_snippet(self.scratch, **kwargs))

    def assert_agree(self, **kwargs):
        python, shell = self.both(**kwargs)
        self.assertEqual(python[0], shell[0], "the exit codes differ: %r %r" % (python, shell))
        self.assertEqual(os.path.realpath(python[1].strip() or os.curdir),
                         os.path.realpath(shell[1].strip() or os.curdir),
                         "the roots differ: %r %r" % (python[1], shell[1]))
        self.assertEqual(python[2], shell[2], "the messages differ")
        return python

    def test_they_pick_the_same_installed_version(self):
        self.installed("0.9.0")
        self.installed("0.10.0")
        self.installed("abc1234", manifest=False)
        result = self.assert_agree(station=self.station)
        self.assertEqual(result[0], 0, result[2])

    def test_they_pick_the_same_winner_where_a_leading_zero_would_have_tied(self):
        """`1.0` beside `01.0`: one key, two names, and the two snippets used to disagree."""
        self.installed("0.9.0")
        self.installed("0.10.0")
        self.installed("01.0", version="01.0")
        winner = self.installed("1.0", version="1.0")
        result = self.assert_agree(station=self.station)
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(os.path.realpath(result[1].strip()), os.path.realpath(winner))

    def test_they_print_the_same_not_found_message_with_every_rejection(self):
        self.installed("abc1234", manifest=False)
        self.installed("nightly", version=False)
        self.installed("latest", version="1.2.0")
        self.installed("1.2.x", version="1.2.x")
        self.installed("2.0.0", records_py=False)
        self.installed("0.7.0", version="")
        result = self.assert_agree(station=self.station)
        self.assertEqual(result[0], 3, result[1])
        self.assertTrue(result[2].startswith(MESSAGE), result[2])

    def test_they_print_the_same_message_when_route_3bs_directory_is_missing(self):
        self.assert_agree(station=self.station_without_a_sibling, argument=self.empty)

    def test_they_print_the_same_confirm_refusals(self):
        self.assert_agree(argument=self.stub_component("speaks-2", interface_version=2), known="1")
        self.assert_agree(argument=self.stub_component("mute", body="pass\n"), known="1")

    # ---- the outside review's finding 11: every row of the table where they disagreed ------

    def test_they_agree_that_a_version_with_an_empty_part_is_not_a_version(self):
        """`1.` matched its manifest, and shell field splitting dropped the empty component."""
        self.installed("1.", version="1.")
        result = self.assert_agree(station=self.station)
        self.assertEqual(result[0], 3, result[1])

    def test_they_agree_on_versions_wider_than_eighteen_digits(self):
        """Padding to a fixed width made the shell compare the truncated head of a number."""
        self.installed("999999999999999999", version="999999999999999999")
        winner = self.installed("1000000000000000000", version="1000000000000000000")
        result = self.assert_agree(station=self.station)
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(os.path.realpath(result[1].strip()), os.path.realpath(winner))

    def test_they_agree_that_a_manifest_of_the_wrong_shape_is_unreadable(self):
        folder = os.path.join(self.installed_base, "1.0.0")
        os.makedirs(os.path.join(folder, ".claude-plugin"))
        testlib.write(os.path.join(folder, ".claude-plugin", "plugin.json"), "[]\n")
        testlib.write(os.path.join(folder, "scripts", "records.py"), STUB % (1, '"records"'))
        result = self.assert_agree(station=self.station)
        self.assertEqual(result[0], 3, result[1])
        self.assertIn("plugin.json unreadable", result[2])

    def test_they_agree_on_a_folder_name_holding_a_newline(self):
        self.installed("1.0\n0", version="9.9.9")
        result = self.assert_agree(station=self.station)
        self.assertEqual(result[0], 3, result[1])
        self.assertEqual(len(result[2].strip().split("\n")), 1,
                         "the refusal is one line whatever a folder is called: %r" % result[2])

    def test_they_agree_on_what_an_interface_version_may_be(self):
        """One typed rule: a JSON integer, never a bool, a float or a string."""
        for literal, accepted in (("1", True), ("true", False), ("1.0", False),
                                  ('"1"', False), ("null", False)):
            body = ("import json, sys\n"
                    "sys.stdout.write(json.dumps({\"ok\": True, \"name\": \"records\",\n"
                    "                             \"version\": \"1.0.0\"})"
                    ".replace('}', ', \"interface_version\": %s}'))\n" % literal)
            root = self.stub_component("says-" + literal.strip('"'), body=body)
            result = self.assert_agree(argument=root, known="1")
            self.assertEqual(result[0], 0 if accepted else 3, (literal, result))


class TheDocumentCarriesBothSnippets(unittest.TestCase):
    def test_the_python_snippet_is_there_and_is_python(self):
        text = snippet(PYTHON_MARKER)
        self.assertIn("def records_root(", text)
        self.assertIn("def confirm_interface(", text)
        self.assertIn("RECORDS_ROOT", text)
        compile(text, "<interface.md python snippet>", "exec")

    def test_the_shell_snippet_is_there_and_parses(self):
        text = snippet(SH_MARKER)
        self.assertIn("records_root()", text)
        self.assertIn("records_confirm()", text)
        path = os.path.join(tempfile.mkdtemp(prefix="records-sh-"), "snippet.sh")
        try:
            testlib.write(path, text)
            proc = subprocess.run(["/bin/sh", "-n", path],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        finally:
            testlib.rmtree(os.path.dirname(path))

    def test_both_name_the_four_routes_in_the_ruled_order(self):
        """1, then 2, then 3a, then 3b, and nothing after 3b.

        Since the outside review's finding 11 the shell snippet wraps the same implementation
        the Python snippet is, so the order is read out of that one body in both: two spellings
        of one rule were exactly what let the two disagree.
        """
        for text in (snippet(PYTHON_MARKER), snippet(SH_MARKER)):
            body = text.split("def records_root(", 1)[1]
            self.assertLess(body.index("argument"), body.index("RECORDS_ROOT"), text)
            self.assertLess(body.index("RECORDS_ROOT"), body.index("# route 3a"), text)
            self.assertLess(body.index("# route 3a"), body.index("# route 3b"), text)

    def test_the_shell_snippet_runs_the_python_snippets_own_rule(self):
        """Finding 11: one numeric rule and one typed rule, in one implementation."""
        shell, python = snippet(SH_MARKER), snippet(PYTHON_MARKER)
        for function in ("def version_key(", "def installed_versions(", "def records_root(",
                         "def confirm_interface("):
            self.assertIn(function, shell, "the shell snippet does not carry %s" % function)
            self.assertIn(function, python)
        for name in ("records_root()", "records_confirm()"):
            self.assertIn(name, shell)

    def test_neither_snippet_reads_a_clock_or_a_home(self):
        """A6: modification time is never used, and no fifth lookup goes near a home."""
        for text in (snippet(PYTHON_MARKER), snippet(SH_MARKER)):
            for forbidden in ("st_mtime", "getmtime", "expanduser", "HOME",
                              "os.environ[\"HOME\"]", "-newer", ".claude/", ".codex/"):
                self.assertNotIn(forbidden, text, "the snippet reads %s" % forbidden)

    def test_the_document_states_the_ruled_order_and_the_clock_rule(self):
        with open(INTERFACE, encoding="utf-8") as fh:
            text = fh.read()
        section = text.split("## Reaching the component", 1)[1].split("\n## ", 1)[0]
        for phrase in ("3a", "3b", "Modification time is never used",
                       "`0.10.0` beats `0.9.0`", "component-identity"):
            self.assertIn(phrase, section, "interface.md does not say %r" % phrase)

    def test_the_component_root_this_suite_points_at_is_the_real_one(self):
        self.assertTrue(os.path.isfile(os.path.join(COMPONENT_ON_A_CHECKOUT, "scripts", "records.py")))
        self.assertTrue(os.path.isdir(STATION_ON_A_CHECKOUT),
                        "the checkout's station stand-in is gone; route 3a would not be exercised")


if __name__ == "__main__":
    unittest.main()
