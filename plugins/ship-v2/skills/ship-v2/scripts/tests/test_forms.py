"""The load-bearing form (ruling E15-11; contract section 8): v1's `SHIP:` block, rendered and parsed by one module.

`ship_core/forms.py` renders the block from the result and parses it back; parse then render gives the bytes back.
The em dash of the first line is `forms.D`, an escape, typed in no file of this core (standing rule 10's one named
exception). The station names in every line ship-v2 renders are the v2 stations' (CR-26).
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()
from ship_core import forms  # noqa: E402
from back_core import trace  # noqa: E402

D, M = "\u2014", "\u00b7"
DOC = "docs/plans/2026-09-20-turnstile.md"


def fields(**extra):
    out = {"slice": "A", "doc": DOC, "hook": "armed", "result": "ALL CLEAR", "build": "COMPLETE",
           "signoff": "signed off with conditions", "recheck": "ALL CLEAR", "card": "signed off", "laps": 1,
           "bottom_line": "Slice A went through one lap and is clear. Run handoff-v2 next.",
           "fixed": [{"finding": "the counter skips a turn", "location": "src/turnstile.py:2",
                      "line": "the double tap now counts"}],
           "remains": [{"finding": "the spinner wraps early", "severity": "MINOR",
                        "needed": "MINOR, never gates; fix it when the owner orders it"}],
           "skill_note": None}
    out.update(extra)
    return out


class TheShipBlock(unittest.TestCase):

    def test_v1s_bytes(self):
        text = forms.render(fields())
        lines = text.split("\n")
        self.assertEqual(lines[0], "SHIP: A %s %s" % (D, DOC))
        self.assertEqual(lines[1], "Hook: armed")
        self.assertEqual(lines[2], "Result: ALL CLEAR")
        self.assertEqual(lines[3], "Build: COMPLETE  %s  Signoff: signed off with conditions  %s  Recheck: ALL CLEAR  "
                                   "%s  Card: signed off  %s  Laps: 1" % (M, M, M, M))
        self.assertEqual(lines[4], "")
        self.assertTrue(lines[5].startswith("Bottom line: "))
        self.assertEqual(lines[6], "")
        self.assertEqual(lines[7], "Fixed: the counter skips a turn %s src/turnstile.py:2 %s the double tap now counts"
                         % (M, M))
        self.assertEqual(lines[8], "Remains: the spinner wraps early %s MINOR %s MINOR, never gates; fix it when the "
                                   "owner orders it" % (M, M))
        self.assertNotIn("SKILL NOTE:", text)

    def test_the_round_trip(self):
        for one in (fields(), fields(fixed=[], remains=[]), fields(hook="NOT armed (run unwrapped)",
                                                                   result="STOPPED (condition 4: a fix wants files "
                                                                          "outside the slice scope)",
                                                                   skill_note="the hook could not be read")):
            text = forms.render(one)
            self.assertEqual(forms.render(forms.parse(text)), text)

    def test_empty_fixed_and_remains_are_omitted(self):
        text = forms.render(fields(fixed=[], remains=[]))
        self.assertNotIn("Fixed:", text)
        self.assertNotIn("Remains:", text)

    def test_the_four_stop_lines(self):
        self.assertEqual([forms.result_line(n) for n in (1, 2, 3, 4)], [
            "STOPPED (condition 1: the extra lap is exhausted without ALL CLEAR)",
            "STOPPED (condition 2: a fix would change the spec)",
            "STOPPED (condition 3: build-v2 stopped mid-slice)",
            "STOPPED (condition 4: a fix wants files outside the slice scope)"])

    def test_the_hook_labels(self):
        self.assertEqual(forms.hook_label(True), "armed")
        self.assertEqual(forms.hook_label(False), "NOT armed (run unwrapped)")

    def test_a_value_that_cannot_land_is_refused(self):
        with self.assertRaises(forms.FormError):
            forms.render(fields(bottom_line="two\nlines"))


class TheNames(unittest.TestCase):

    def test_every_summon_names_a_v2_station(self):
        for station in ("build-v2", "signoff-v2", "recheck-v2"):
            line = forms.summon(station, "A", DOC)
            self.assertEqual(line, "/%s A %s" % (station, DOC))
        self.assertEqual(forms.summon_goal("A", DOC), "/goal /ship-v2 A %s" % DOC)
        for name in trace.v1_names():
            with self.assertRaises(forms.FormError):
                forms.summon(name, "A", DOC)


class NoTypedDash(unittest.TestCase):
    """Standing rule 10: no file this core writes holds a typed em dash; the form carries it as `forms.D`."""

    def test_no_file_of_this_core_holds_a_typed_em_dash(self):
        found = []
        for base, dirs, names in os.walk(testlib.PLUGIN):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git"))
            for name in sorted(names):
                path = os.path.join(base, name)
                try:
                    with open(path, encoding="utf-8") as fh:
                        if "\u2014" in fh.read():
                            found.append(os.path.relpath(path, testlib.PLUGIN))
                except (UnicodeDecodeError, OSError):
                    continue
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
