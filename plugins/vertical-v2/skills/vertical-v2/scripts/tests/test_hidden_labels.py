"""A label behind invisible characters (the E15 lane contract A15; contract section 5, "Two readings").

The second reading tests every rendered paragraph line for `Status:` and `Base:` after its leading whitespace (any
Unicode space) and its format characters (Unicode category Cf) are removed. A line that reads as a label that way is a
label candidate, so a hidden one becomes a second or a non-exact label and the run stops `doc-unreadable` naming its
line. The spec removes any line that reads as a `Status:` label that way from every packet.

`HIDDEN` are the characters put before the label: a zero-width space, a soft hyphen, a zero-width no-break space, a
word joiner, a no-break space and an ideographic space. `TheReadings` drives the readers directly; `TheGate` drives
each shape through the real CLI with records off and on; `TheScope` drives them through `scope` on the reviewed commit
under the owner's committed-state-only words, records off and on, and holds a hidden header `Status:` line, which no
reading takes as a card, absent from every packet.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import fences, gate as gatemod, spec  # noqa: E402

D = vlib.D
HIDDEN = (("a zero-width space", "​"), ("a soft hyphen", "­"), ("a zero-width no-break space", "﻿"),
          ("a word joiner", "⁠"), ("a no-break space", " "), ("an ideographic space", "　"))


def with_b(lines):
    base = vlib.build_doc(slices=[("A", "the counter", "signed off")])
    at = base.index("\n## Build assumptions")
    block = ["## Slice B %s the spinner" % D, "Goal: one sentence about the spinner.", "Depends on: nothing"]
    return base[:at] + "\n" + "\n".join(block + list(lines)) + "\n" + base[at:]


def number_of(text, line):
    return text.split("\n").index(line) + 1


def slice_shapes():
    """(what, doc, the hidden line): a hidden `Status: built` above slice B's plain label."""
    return [("%s before Status: built in slice B" % what, with_b(["", ch + "Status: built", "", "Status: signed off"]),
             ch + "Status: built") for what, ch in HIDDEN]


def header_shapes():
    """(what, doc, the hidden line): a hidden `Base:` line above the header's plain one."""
    return [("%s before a header Base: line" % what,
             vlib.build_doc(extra_header=["", ch + "Base: 1234567", "", "Base: abcdef1"]), ch + "Base: 1234567")
            for what, ch in HIDDEN]


def header_status_doc(ch):
    """A hidden `Status:` line in the header: no reading takes it as a card; the spec must remove it."""
    return vlib.build_doc(extra_header=["", ch + "Status: built HIDDEN-STATUS-MARKER"])


class TheReadings(unittest.TestCase):

    def test_every_hidden_label_stops_every_reader_naming_its_line(self):
        for what, text, hidden in slice_shapes() + header_shapes():
            with self.subTest(shape=what):
                self.assertEqual(fences.read(text).problems, [], what)
                for name, call in (("slices", gatemod.slices_of), ("base", gatemod.recorded_base),
                                   ("spec", spec.clean)):
                    with self.assertRaises(spec.SpecUnreadable, msg=(what, name)) as caught:
                        call(text)
                    self.assertEqual(caught.exception.line, number_of(text, hidden), (what, name))

    def test_a_hidden_header_status_line_is_removed_from_the_spec(self):
        for what, ch in HIDDEN:
            with self.subTest(shape=what):
                text = header_status_doc(ch)
                kept, removed = spec.clean(text)
                self.assertNotIn("HIDDEN-STATUS-MARKER", kept, what)
                at = number_of(text, ch + "Status: built HIDDEN-STATUS-MARKER")
                self.assertIn({"what": "Status: line", "lines": [at, at]}, removed, what)

    def test_a_plain_doc_is_unchanged(self):
        """A plain doc reads and cleans as before A15: its Status: labels are removed, its Base: line and every other
        line kept byte for byte."""
        text = vlib.build_doc(base_line="Base: 1234567")
        self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(text)],
                         [("A", "signed off"), ("B", "signed off")])
        self.assertEqual(gatemod.recorded_base(text)["commit"], "1234567")
        kept, removed = spec.clean(text)
        lines = text.split("\n")
        status = [n for n, line in enumerate(lines, 1) if line.startswith("Status:")]
        self.assertEqual(sorted(r["lines"][0] for r in removed if r["what"] == "Status: line"), status)
        self.assertIn("\nBase: 1234567\n", kept)


@unittest.skipUnless(vlib.records_usable(), "the gate reads the records component (checkout and jsonschema)")
class TheGate(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vhidden-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def test_every_hidden_label_stops_the_gate(self):
        for what, doc, hidden in slice_shapes() + header_shapes():
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    self.count += 1
                    ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count)
                    drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count)
                    code, out, err = drive(["gate", "--run-dir", run_dir])
                    self.assertEqual(code, 10, (what, out, err))
                    self.assertEqual((out["status"], out["stop_tag"]), ("stopped", "doc-unreadable"), (what, out))
                    self.assertIn("line %d" % number_of(doc, hidden), out["reason"], what)
                    for name in ("ask.json", "packets", "scope.json"):
                        self.assertFalse(os.path.lexists(os.path.join(run_dir, name)), (what, name))


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask and scope (records, readers' roster, jsonschema)")
class TheScope(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vhidden-scope-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def test_scope_stops_on_a_hidden_label_only_in_the_commit(self):
        for what, doc, hidden in slice_shapes() + header_shapes():
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    self.count += 1
                    ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=records, name="ws-%d" % self.count)
                    testlib.write_text(os.path.join(ws, vlib.DOC), vlib.build_doc())
                    drive, run_dir = vlib.start(self.tmp, ws, run="run-%d" % self.count,
                                                owner_words={"committed_only": "review the committed state only"})
                    code, out, err = vlib.through_ask(drive, self.tmp, run_dir)
                    self.assertEqual(code, 0, (what, records, out, err))
                    code, out, err = drive(["scope", "--run-dir", run_dir])
                    self.assertEqual(code, 10, (what, records, out, err))
                    self.assertEqual(out["stop_tag"], "doc-unreadable", what)
                    self.assertIn("line %d" % number_of(doc, hidden), out["reason"], what)
                    self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")), what)

    def test_a_hidden_header_status_line_reaches_no_packet_and_is_named(self):
        for index, (what, ch) in enumerate(HIDDEN):
            with self.subTest(shape=what):
                doc = header_status_doc(ch)
                drive, run_dir, ws, info = vlib.through_scope(os.path.join(self.tmp, "h%d" % index),
                                                              repo={"doc_text": doc})
                at = number_of(doc, ch + "Status: built HIDDEN-STATUS-MARKER")
                root = os.path.join(run_dir, "packets")
                names = sorted(os.listdir(root))
                self.assertTrue(names)
                for name in names:
                    for base, dirs, files in os.walk(os.path.join(root, name)):
                        for leaf in files:
                            if leaf in ("files.json", "withheld.json"):
                                continue
                            with open(os.path.join(base, leaf), "rb") as fh:
                                self.assertNotIn(b"HIDDEN-STATUS-MARKER", fh.read(), (what, name, leaf))
                    withheld = testlib.load_json(os.path.join(root, name, "withheld.json"))["withheld"]
                    self.assertIn("%s Status: line %d" % (vlib.DOC, at), [w["what"] for w in withheld], (what, name))


if __name__ == "__main__":
    unittest.main()
