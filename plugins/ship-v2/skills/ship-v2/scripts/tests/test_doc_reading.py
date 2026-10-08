"""CR-27, the doc reading as slice 1b ended it (A22, A25, A26; contract section 5).

Every line ship-v2 reads from a build doc to decide anything (the slices, the slice's card, its footprint) is read
twice: by vertical-v2's plain-structure line rules (A22: `ship_core/fences.py`, vertical-v2's file byte for byte) and
by vertical-v2's second reading (A13: `commonmark.py`, `readings.py`, `spec.py` and `notes.py` byte for byte, over the
vendored reader), and the first line where the two disagree stops `doc-unreadable` before any visit or write. The
one label ship-v2 reads of its own, `Footprint:`, follows A26's one rule: the plain form on one source line with its
value on the same line; any other rendered form stops. `TheCopy` holds the five files and the vendored tree to
vertical-v2's (skipped, never passed, in the installed shape). `TheReading` drives `ship_core/doc.py`; `TheStops`
drives the real CLI: each stop names its line, before any visit, with nothing written.
"""
import hashlib
import os
import unittest

import slib
import testlib

testlib.add_scripts_to_path()
from ship_core import doc as docmod  # noqa: E402

D = slib.D
COPIED = ("fences.py", "commonmark.py", "readings.py", "spec.py", "notes.py")


def vertical_scripts():
    path = testlib.checkout_sibling("vertical-v2")
    return None if path is None else os.path.join(path, "skills", "vertical-v2", "scripts")


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def tree(root):
    out = []
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            out.append(os.path.relpath(os.path.join(base, name), root).replace(os.sep, "/"))
    return sorted(out)


class TheCopy(unittest.TestCase):

    def theirs(self):
        scripts = vertical_scripts()
        if scripts is None or not os.path.isdir(scripts):
            self.skipTest("vertical-v2 is not beside this core (the installed shape): the copy cannot be compared "
                          "here, and this is reported as skipped, not passed")
        return scripts

    def test_the_two_readings_are_vertical_v2s_code_byte_for_byte(self):
        scripts = self.theirs()
        for name in COPIED:
            mine = os.path.join(testlib.SCRIPTS, "ship_core", name)
            self.assertTrue(os.path.isfile(mine), name)
            self.assertEqual(digest(mine), digest(os.path.join(scripts, "vertical_core", name)), name)

    def test_the_vendored_reader_is_vertical_v2s_tree_byte_for_byte(self):
        scripts = self.theirs()
        mine, theirs = os.path.join(testlib.SCRIPTS, "vendor"), os.path.join(scripts, "vendor")
        self.assertEqual(tree(mine), tree(theirs))
        for rel in tree(theirs):
            self.assertEqual(digest(os.path.join(mine, *rel.split("/"))), digest(os.path.join(theirs, *rel.split("/"))),
                             rel)

    def test_none_of_them_is_a_back_frame_file(self):
        with open(os.path.join(testlib.REF, "back-files.txt"), encoding="utf-8") as fh:
            listed = fh.read()
        for name in COPIED:
            self.assertNotIn("ship_core/" + name, listed)
        self.assertNotIn("vendor", listed)

    def test_the_statement(self):
        from ship_core import fences, readings  # noqa: E402
        for name in ("THE TWO-READINGS RULE", "THE SECOND READING'S FOUR REFUSALS"):
            self.assertIn(name, readings.__doc__)
        for name in ("THE FENCE RULE", "THE LABEL RULE", "THE PLAIN-STRUCTURE RULE", "THE CHARACTER LIST"):
            self.assertIn(name, fences.__doc__)
        self.assertIn("THE FOOTPRINT RULE", docmod.__doc__)


def with_slice_a(lines):
    """The fixture doc with slice A's section replaced by `lines` (its heading kept)."""
    text = slib.build_doc(slices=[("B", "the spinner", "not started")],
                          raw_slice=["## Slice A %s the counter" % D] + list(lines))
    return text


PLAIN = ["Goal: one sentence.", "Footprint: `src/turnstile.py`, tests/, `docs/notes.md` (new)",
         "Not in this slice: the encoder", "Depends on: nothing", "Status: built"]


class TheReading(unittest.TestCase):

    def stop(self, text, line):
        with self.assertRaises(docmod.DocUnreadable) as caught:
            docmod.read(text)
        self.assertEqual(text.split("\n")[caught.exception.line - 1], line, caught.exception.words)
        return caught.exception

    def test_the_plain_footprint_reads(self):
        doc = docmod.read(with_slice_a(PLAIN))
        row = docmod.slice_of(doc, "A")
        self.assertEqual(row["status"], "built")
        self.assertEqual(row["footprint"], ["src/turnstile.py", "tests/", "docs/notes.md"])
        self.assertTrue(docmod.in_footprint("tests/test_turnstile.py", row["footprint"]))
        self.assertTrue(docmod.in_footprint("./src/turnstile.py", row["footprint"]))
        self.assertFalse(docmod.in_footprint("src/turnstile.pyc", row["footprint"]))
        self.assertFalse(docmod.in_footprint("src/spinner.py", row["footprint"]))

    def test_a_slice_without_a_footprint_names_none(self):
        doc = docmod.read(with_slice_a(["Goal: one sentence.", "Status: built"]))
        self.assertEqual(docmod.slice_of(doc, "A")["footprint"], [])

    def test_an_empty_footprint_label_stops(self):
        self.stop(with_slice_a(["Footprint:", "- src/turnstile.py", "", "Status: built"]), "Footprint:")

    def test_a_bold_footprint_stops(self):
        line = "**Footprint:** `src/turnstile.py`"
        self.stop(with_slice_a(["Goal: one.", line, "", "Status: built"]), line)

    def test_a_footprint_heading_stops(self):
        line = "### Footprint: src/turnstile.py"
        self.stop(with_slice_a(["Goal: one.", "", line, "", "Status: built"]), line)

    def test_a_footprint_in_a_list_item_stops(self):
        line = "- Footprint: src/turnstile.py"
        self.stop(with_slice_a(["Goal: one.", line, "", "Status: built"]), line)

    def test_a_second_footprint_stops(self):
        line = "Footprint: src/spinner.py"
        self.stop(with_slice_a(["Footprint: src/turnstile.py", line, "Status: built"]), line)

    def test_a_footprint_behind_a_leading_mark_stops(self):
        line = "\u2018Footprint: src/turnstile.py"
        self.stop(with_slice_a(["Goal: one.", line, "Status: built"]), line)

    def test_a_footprint_in_a_paragraph_the_reader_cannot_map_stops(self):
        """A code span running over a line ending: which source line holds the label cannot be told."""
        self.stop(with_slice_a(["Goal: one `a", "b` c", "Footprint: src/spinner.py", "", "Status: built"]),
                  "Goal: one `a")

    def test_a_footprint_outside_every_slice_is_not_read(self):
        text = slib.build_doc(punch=["- Footprint: anything at all"])
        docmod.read(text)

    def test_an_a13_refusal_stops_before_anything_is_read(self):
        line = "## 2. Slice C"
        text = slib.build_doc(raw_slice=[line, "Status: not started"])
        self.stop(text, line)

    def test_a_label_the_line_rules_refuse_stops(self):
        line = "Status: built and tested"
        self.stop(with_slice_a(["Goal: one.", line]), line)


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class TheStops(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-doc-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.tree = slib.Tree(self.tmp)

    def test_select_stops_doc_unreadable_with_nothing_written(self):
        line = "**Footprint:** `src/turnstile.py`"
        ws = slib.make_repo(self.tmp, with_slice_a(["Goal: one.", line, "", "Status: not started"]))
        before = slib.snapshot(ws)
        drive, run_dir = slib.start(self, self.tree, self.tmp, ws)
        code, out, err = drive(["select", "--run-dir", run_dir, "--doc", slib.DOC])
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        self.assertIn("doc-unreadable", out["stop_tag"])
        code, out, err = drive(["hook", "--run-dir", run_dir, "--reading", slib.hook_file(self.tmp)])
        self.assertEqual(code, 2)
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual((code, out["stop_tag"]), (10, "doc-unreadable"), (out, err))
        self.assertEqual(slib.trace(run_dir), [])
        self.assertEqual(before, slib.snapshot(ws))

    def test_a_doc_that_turns_unreadable_stops_the_fix_before_it_is_recorded(self):
        ws = slib.make_repo(self.tmp)
        drive, run_dir = slib.start(self, self.tree, self.tmp, ws)
        slib.through_hook(self, drive, self.tmp, run_dir)
        slib.visit(self, drive, run_dir, "build-v2", "completed", ws)
        finding = slib.raise_finding(self.tmp, ws)
        code, out, err = slib.visit(self, drive, run_dir, "signoff-v2", "findings", ws)
        self.assertEqual(out["next"], "fix")
        path = os.path.join(ws, slib.DOC)
        testlib.write_text(path, testlib.read_text(path).replace("Footprint: `src/turnstile.py`",
                                                                 "**Footprint:** `src/turnstile.py`"))
        code, out, err = drive(["fix", "--run-dir", run_dir, "--fixes", slib.fixes_file(self.tmp, run_dir, 1, [
            {"finding": finding, "paths": ["src/turnstile.py"], "summary": "x"}])])
        self.assertEqual((code, out["next"]), (0, "report"), (out, err))
        code, out, err = slib.report(drive, run_dir)
        self.assertEqual(out["stop_tag"], "doc-unreadable")


if __name__ == "__main__":
    unittest.main()
