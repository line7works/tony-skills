"""Round 14 (1): a line that renders as a `Status:` label is cut from every packet (the E15 lane contract A21 (1);
Astra's look 4, its BLOCKER; contract section 5, "The spec").

The spec removes from every packet, besides what it removed before, every source line of a rendered paragraph line
that the second reading takes as a `Status:` label candidate, wherever it stands outside accepted fences: a bold
`**Status:** built` above the first slice heading (look 4's document), the same under a `## Summary` heading before
or after the slices, a code-span label there, a bold label under a numbered heading of level 2 or 3, a bold label in
a list item, and a bold label whose rendered line runs over two source lines through an inline comment (both lines
go). Nothing stops on it: each such doc runs, its slices and cards as before, and each line is named in the removed
list. A prose sentence that mentions the status of each slice in its middle, a bold `Status:` in the middle of a
sentence and a fenced bold label stay.

`TheReaders` drives `spec.clean` and the gate's readers directly; `TheStatement` holds the rule's two statements;
`TheRun` drives every shape through the real CLI (gate, ask, scope, local requests, outside requests), records off
and on, and reads every packet and summons copy: the local lenses, the outside repository packet, the outside
packet-only packet and every mandate.
"""
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import gate as gatemod, readings, spec  # noqa: E402

D = vlib.D
BOLD = "**Status:** built"
CODE = "`Status:` built"


def header(lines):
    return vlib.build_doc(extra_header=list(lines))


def after_slices(lines):
    base = vlib.build_doc()
    at = base.index("\n## Build assumptions")
    return base[:at] + "\n" + "\n".join(lines) + "\n" + base[at:]


def number_of(text, line):
    return text.split("\n").index(line) + 1


# (what, doc, the source lines the spec must cut)
CUT_SHAPES = [
    ("look 4's document: a bold label above the first slice heading", header(["", BOLD]), [BOLD]),
    ("a bold label under ## Summary before the slices", header(["", "## Summary", "", BOLD]), [BOLD]),
    ("a code-span label under ## Summary before the slices", header(["", "## Summary", "", CODE]), [CODE]),
    ("a bold label under ## Summary after the slices", after_slices(["", "## Summary", "", BOLD]), [BOLD]),
    ("a bold label under a numbered level 2 heading", header(["", "## 3. Rollout", "", BOLD]), [BOLD]),
    ("a bold label under a numbered level 3 heading", header(["", "### 7.1 Slice 1: the frame", "", BOLD]), [BOLD]),
    ("a bold label in a list item", header(["", "- " + BOLD]), ["- " + BOLD]),
    ("a bold label running over two source lines through an inline comment",
     header(["", BOLD + " <!-- a note", "that ends here -->"]), [BOLD + " <!-- a note", "that ends here -->"]),
]
# (what, doc, the line that stays)
KEEP_SHAPES = [
    ("prose that mentions the status of each slice in its middle",
     header(["", "The gate reads the status of each slice from its label."]),
     "The gate reads the status of each slice from its label."),
    ("a bold Status: in the middle of a sentence",
     header(["", "Each slice records its **Status:** value below its heading."]),
     "Each slice records its **Status:** value below its heading."),
    ("a fenced bold label", header(["", "```", BOLD, "```"]), BOLD),
]


class TheReaders(unittest.TestCase):

    def test_every_rendered_label_line_is_cut_and_named_and_nothing_stops(self):
        for what, text, cut in CUT_SHAPES:
            with self.subTest(shape=what):
                self.assertEqual([(s["name"], s["status"]) for s in gatemod.slices_of(text)],
                                 [("A", "signed off"), ("B", "signed off")], what)
                kept, removed = spec.clean(text)
                for line in cut:
                    self.assertNotIn(line, kept, what)
                    at = number_of(text, line)
                    self.assertIn({"what": "Status: line", "lines": [at, at]}, removed, (what, removed))
                lines = text.split("\n")
                gone = [number for number, line in enumerate(lines, 1) if line in cut]
                self.assertEqual(sorted(r["lines"][0] for r in removed if r["what"] == "Status: line"),
                                 sorted(gone + [number for number, line in enumerate(lines, 1)
                                                if line.startswith("Status: ")]), what)

    def test_the_controls_stay(self):
        for what, text, line in KEEP_SHAPES:
            with self.subTest(shape=what):
                kept, removed = spec.clean(text)
                self.assertIn(line + "\n", kept, what)
                at = number_of(text, line)
                self.assertNotIn(at, [r["lines"][0] for r in removed], what)

    def test_the_second_reading_names_every_source_line_of_a_rendered_label(self):
        text = header(["", BOLD + " <!-- a note", "that ends here -->", "", "## Summary", "", CODE])
        second = readings.second_reading(text, len(text.split("\n")))
        expected = [number_of(text, BOLD + " <!-- a note"), number_of(text, "that ends here -->"), number_of(text, CODE)]
        self.assertTrue(set(expected) <= set(second["status_lines"]), second["status_lines"])


class TheStatement(unittest.TestCase):
    """The rule stated once in code and once in the contract."""

    def test_the_rule_is_stated_in_the_contract(self):
        with open(os.path.join(testlib.REF, "vertical-contract.md"), encoding="utf-8") as fh:
            text = fh.read()
        start = text.index("**The spec**")
        para = " ".join(text[start:text.index("\n\n", start)].split())
        for words in ("A21 (1)", "every source line of a rendered paragraph line",
                      "wherever it stands outside accepted fences", "nothing stops on it"):
            self.assertIn(words, para)

    def test_the_rule_is_stated_in_the_code(self):
        doc = " ".join(spec.__doc__.split())
        for words in ("A21 (1)", "every source line of a rendered paragraph line",
                      "wherever it stands outside accepted fences", "nothing stops on it"):
            self.assertIn(words, doc)


def every_reviewer_text(run_dir):
    for folder in ("packets", "summons"):
        for base, dirs, files in os.walk(os.path.join(run_dir, folder)):
            for name in files:
                if name not in ("files.json", "withheld.json"):
                    with open(os.path.join(base, name), "rb") as fh:
                        yield os.path.join(base, name), fh.read().decode("utf-8", "replace")
    for base, dirs, files in os.walk(os.path.join(run_dir, "requests")):
        for name in files:
            yield os.path.join(base, name), testlib.read_text(os.path.join(base, name))


def withheld_of_every_copy(run_dir):
    out = []
    for folder in ("packets", "summons"):
        root = os.path.join(run_dir, folder)
        for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
            out.append((folder + "/" + name, testlib.load_json(os.path.join(root, name, "withheld.json"))["withheld"]))
    return out


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the run drives the gate, the ask, scope and both requests (records, readers' roster, jsonschema)")
class TheRun(unittest.TestCase):
    """Every shape through the real CLI, records off and on, to the outside requests: no cut line reaches any packet
    or summons copy (the local lenses, the outside repository packet, the outside packet-only packet, every mandate),
    each is named in every withheld list, and the controls reach the packets."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vrendered-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.count = 0

    def run_to_outside(self, doc, records):
        self.count += 1
        tmp = os.path.join(self.tmp, "r%d" % self.count)
        drive, run_dir, ws, info = vlib.through_outside(tmp, rows=("gpt-astra", "deepseek"),
                                                        repo={"doc_text": doc, "records": records})
        copies = withheld_of_every_copy(run_dir)
        names = [name for name, withheld in copies]
        self.assertTrue(any(n.startswith("packets/local-") for n in names), names)
        self.assertTrue(any(n.startswith("packets/outside-gpt-astra") for n in names), names)
        self.assertTrue(any(n.startswith("packets/outside-deepseek") for n in names), names)
        self.assertTrue(any(n.startswith("summons/") for n in names), names)
        texts = list(every_reviewer_text(run_dir))
        self.assertTrue(any(os.path.basename(path) == "mandate.md" for path, text in texts), run_dir)
        return run_dir, copies, texts

    def test_no_cut_line_reaches_any_packet_and_each_is_named(self):
        for what, doc, cut in CUT_SHAPES:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    run_dir, copies, texts = self.run_to_outside(doc, records)
                    for line in cut:
                        for path, text in texts:
                            self.assertNotIn(line, text, (what, path))
                        at = number_of(doc, line)
                        for name, withheld in copies:
                            self.assertIn("%s Status: line %d" % (vlib.DOC, at), [w["what"] for w in withheld],
                                          (what, name))

    def test_the_controls_reach_the_packets(self):
        for what, doc, line in KEEP_SHAPES:
            for records in (False, True):
                with self.subTest(shape=what, records=records):
                    run_dir, copies, texts = self.run_to_outside(doc, records)
                    specs = [text for path, text in texts if path.endswith(os.path.join("documents", "spec.md"))]
                    self.assertTrue(specs, what)
                    for text in specs:
                        self.assertIn(line, text, what)


if __name__ == "__main__":
    unittest.main()
