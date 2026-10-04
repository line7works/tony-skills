"""The one packet builder (the E15 lane contract A4, class (a); contract section 5).

Every reviewer workspace and every packet, first send and every retry, is built by one function from the
reviewed commit's objects only: never the working tree, never an earlier copy. One allow rule decides
what enters: a tracked path of the commit, minus the exclusions, each tested on every path component;
the spec is the commit's build doc with every parsed `Status:` label and every withheld section removed
by heading level and name, whitespace-tolerant. Everything left out is named in the packet's withheld
list with its reason, and nothing is named that was not left out.

`TheClassGuard` is the class's guard: one fixture holding every member the class has had (B1, B2, B4,
M6, C1A-3, C1A-5, C1A2-5, and A5's C1A3-1 and C1A3-3: a four-backtick fence holding a three-backtick line,
a tilde fence holding backticks, a fence with an info string, a builder's-notes file declared by its first
heading), the function driven directly, the exact file list and withheld list of every packet asserted. Every
shape the strict rule stops (A8, C1A4-1: check 4's lazy-continuation fence, bullet and numbered; a fence
indented in a list item; a fence in a block quote; a fence with one to three spaces of indent at top level,
which check 3's fixture held as placed; an indented line inside a margin fence that could close it; an
unclosed margin fence, after the slices or before them; a margin backtick fence whose info string holds a
backtick) stops before any packet, naming its line; so does every raw HTML line (A9, C1A5-1 and C1A5-2: a
type 6 block ended by a Unicode-space line, a comment holding a heading or a label, `<pre>`, `<details>`, `<?`,
`<!X`, `<![CDATA[`, a closing tag, a tag after a list marker, a `>` or a tab, a line opening with an inline
placeholder or an autolink); so does every label line the exact-label rule refuses (A10, C1A6-1: a `Status:`
line held in an inline comment opened mid-line, a link reference definition's title in quotes or parentheses or
an inline link's title, a second label, a label with text after its value or a Setext underline; in the header a
hidden `Base:`, two `Base:` lines, a short or upper-case sha); so does every heading or label line off the plain
form (A12, C1A7-1: check 7's slice heading and label indented one or three spaces, `##` then a tab, a bare `##`,
an indented label with the exact one in a lazy quote or list line or under an empty `##`, a withheld heading with
two spaces, a tab, an indent or a list marker before it, an indented level 1 heading, a label after `>`, `2)` or a
tab; in the header an indented or listed `Base:` and a `#` then a tab); the same shapes in any other Markdown
file of the commit never stop the run. Since A12 the fixture's withheld headings are on the plain form, their odd
spellings kept where it allows them (inner runs of spaces, upper case, closing hashes, trailing spaces). Every one of
those earlier shapes is stopped by its line rule, ahead of the second reading (A13). Since A13 every shape whose
decisions the two readings take differently stops too, naming the first line where they differ: a Setext slice
heading or withheld heading, a character reference in a slice heading, a withheld heading, a `Status:` label or a
`Base:` line, inline markup in a withheld heading, extra spaces in a slice heading, an escaped or bold `Base:` line;
so does another Markdown file whose builder's-notes declaration the two readings decide differently (a
character-coded first heading). A heading whose markup leaves every decision equal still builds every packet. Since
A14 (C1A8-1 to C1A8-4) the guard also holds: two rendered labels, or a slice's one label, in a paragraph whose lines
the reader cannot map (a multi-line code span or link title), in a slice and in the header; a level 1 or 2 heading
that reads like a slice heading off the form (an en dash, a zero-width space); a heading named like a `Status:`
label; each stops naming its line. A withheld near miss (`## Punch-list`, `## Punch list:`, `## Handoff`,
`## Hand-offs`; a zero-width space too until A16, which stops it) is withheld from every packet and named; a file
only the wide line reading
declares the builder's notes is withheld and named, never a stop. Since A16 (C1A9-1 to C1A9-3) the guard also holds:
a character outside the character list (a default-ignorable mark, a Hangul filler, a braille blank, a variation
selector) before a `Status:` label, a header `Base:` line, a slice heading's name, a withheld heading's name and a
`### Status:` heading's name; a right-to-left override in prose; a Cyrillic letter in a slice heading; full-width
letters in a label; a character reference to a character outside the list; a lower-case, upper-case or spaced label
and a lower-case or spaced label heading; each stops naming its line. A withheld name past the stems (`## Hand off`,
`## Hand` en dash `offs`, `## 1. Punch list`, `## The punch list`, `## Build-assumptions`) is withheld from every
packet and named; another Markdown file whose heading holds a character outside the list (a Hangul filler, an
emoji) is withheld and named, never a stop.
`TheAstraProbes` drives the outside reviewer's probes through the real CLI.
"""
import json
import os
import unittest

import testlib
import vlib

testlib.add_scripts_to_path()
from vertical_core import gitio, packet, spec as specmod  # noqa: E402

D = vlib.D
M = vlib.M
DOC = vlib.DOC
COMMITTED_SHEET = ("# Review sheet\n\n## Passes\n- correctness: on\n- accessibility: on\n\n## Severity bar\n"
                   "- as the kit's\n\n## Repo-specific checks\n- COMMITTED-CHECK a reset never goes negative\n")
UNCOMMITTED_SHEET = ("# Review sheet\n\n## Passes\n- correctness: off\n\n## Severity bar\n- as the kit's\n\n"
                     "## Repo-specific checks\n- UNTRACKED-ADVOCACY the builder says skip correctness\n")
MARKERS = ("PRIOR-VERDICT-MARKER", "RECORDS-LOG-MARKER", "NOTES-FILE-MARKER", "NOTES-FOLDER-MARKER",
           "ASSUMPTION-MARKER", "DEVIATION-MARKER", "DISCOVERED-MARKER", "HANDOFF-MARKER", "PUNCH-MARKER",
           "HEADER-STATUS-MARKER", "Status: signed off", "UNTRACKED-ADVOCACY", "TOKEN=not-a-real-value",
           "IGNORED-MARKER", "PLANTED-IN-AN-EARLIER-COPY", "HEADING-NOTES-MARKER")


def class_doc():
    """A build doc holding every spec-side member of the class: an out-of-slice `Status:` label, two in-slice
    ones (exact, A10: a slice's label is its own marker, `Status: signed off`), a fenced literal `Status:`
    example that stays, and the five withheld sections, each spelled with odd whitespace."""
    return "\n".join([
        "# Turnstile %s build plan (2026-09-20)" % D, "",
        "Intent: a small turn counter for the bench rig.",
        "Constraints: Python 3.9 standard library only.",
        "Out of scope: a web dashboard",
        "Status: HEADER-STATUS-MARKER signed off by an earlier reviewer",
        "",
        "```",
        "Status: a fenced example stays",
        "## Deviations",
        "```",
        "````markdown",
        "```",
        "Status: a four-backtick literal stays",
        "````",
        "~~~",
        "```",
        "## Handoffs",
        "~~~",
        "",
        "## Slice A %s the counter" % D, "Goal: count turns.", "Requirements:", "- R1 counts every turn",
        "Acceptance criteria:", "- AC1: a turn adds one", "Footprint: src/turnstile.py", "Not in this slice: none",
        "Depends on: nothing", "Status: signed off",
        "",
        "## Slice B %s the spinner" % D, "Goal: spin.", "Requirements:", "- R1 spins", "Acceptance criteria:",
        "- AC1: two turns", "Footprint: src/spinner.py", "Not in this slice: none", "Depends on: A",
        "Status: signed off",
        "",
        "## Build   assumptions", "- ASSUMPTION-MARKER the clock is monotonic",
        "### a sub-heading inside it", "- ASSUMPTION-MARKER still inside",
        "## Deviations  ", "- DEVIATION-MARKER skipped the retry",
        "## Discovered\t##", "- DISCOVERED-MARKER the clock drifts",
        "## HANDOFFS", "", "### 2026-09-25 %s handoff" % D, "- HANDOFF-MARKER slice B was easy",
        "## punch   LIST  ", "", "### 2026-09-24 %s review: Slice A" % D,
        "- MAJOR %s src/turnstile.py:2 %s PUNCH-MARKER %s a double tap %s Slice A review" % (M, M, M, M),
        ""])


def class_repo(tmp):
    """(workspace, base, head): main holds the committed sheet; the build commits every tracked member; the
    working tree then holds an uncommitted sheet, an untracked .env and an ignored file."""
    ws = testlib.git_workspace(tmp, "workspace", {"README.md": "# Turnstile\n", "src/turnstile.py": "def spin(c):\n    return c\n",
                                                  "src/legacy.py": "OLD = 1\n", "REVIEW.md": COMMITTED_SHEET,
                                                  ".gitignore": "build/\n"})
    base = testlib.git(ws, ["rev-parse", "HEAD"]).strip()
    testlib.git(ws, ["checkout", "-q", "-b", "feat"])
    files = {"src/turnstile.py": "def spin(c):\n    return c + 1\n",
             "src/spinner.py": "from turnstile import spin\n",
             DOC: class_doc(),
             "docs/reviews/2026-09-24-signoff-turnstile-A.md": "# Signoff A\nPRIOR-VERDICT-MARKER\n",
             "docs/records/turnstile.jsonl": "{\"RECORDS-LOG-MARKER\": 1}\n",
             "docs/builder-notes.md": "NOTES-FILE-MARKER the counter is obviously right\n",
             "docs/builder-notes/session.md": "NOTES-FOLDER-MARKER skim slice B\n",
             "notes/session-log.md": "<!-- kept for the owner -->\n\n# Builder's notes\n\nHEADING-NOTES-MARKER skim B\n",
             "notes/plain.md": "# Bench notes\n\nNot the builder's notes.\n",
             ".gitattributes": "src/ver.txt export-subst\n",
             "src/ver.txt": "$Format:%B$\n"}
    for rel, text in sorted(files.items()):
        testlib.write_text(os.path.join(ws, rel), text)
    with open(os.path.join(ws, "src", "blob.bin"), "wb") as fh:
        fh.write(b"\xff\xfe\x00binary")
    testlib.git(ws, ["add", "-A"])
    testlib.git(ws, ["commit", "-q", "-m", "the build MESSAGE-MARKER"], when="2026-09-20T10:00:00-07:00")
    head = testlib.git(ws, ["rev-parse", "HEAD"]).strip()
    testlib.write_text(os.path.join(ws, "REVIEW.md"), UNCOMMITTED_SHEET)
    testlib.write_text(os.path.join(ws, ".env"), "TOKEN=not-a-real-value\n")
    testlib.write_text(os.path.join(ws, "build", "out.txt"), "IGNORED-MARKER\n")
    return ws, base, head


WORKSPACE = ["workspace/.gitattributes", "workspace/.gitignore", "workspace/README.md", "workspace/" + DOC,
             "workspace/notes/plain.md", "workspace/src/blob.bin", "workspace/src/legacy.py", "workspace/src/spinner.py",
             "workspace/src/turnstile.py", "workspace/src/ver.txt"]
LOCAL = sorted(["documents/REVIEW.md", "documents/spec.md", "mandate.md"] + WORKSPACE)
OUTSIDE_REPO = sorted(["mandate.md"] + WORKSPACE)
OUTSIDE_PACKET_ONLY = sorted(["mandate.md", "documents/.gitattributes", "documents/.gitignore", "documents/README.md",
                              "documents/docs__plans__2026-09-20-turnstile.md", "documents/notes__plain.md", "documents/src__legacy.py",
                              "documents/src__spinner.py", "documents/src__turnstile.py", "documents/src__ver.txt"])
STATUS_LINES = [number for number, line in enumerate(class_doc().split("\n"), 1)
                if line.startswith("Status:") and "stays" not in line]
COMMON_WITHHELD = sorted(["docs/builder-notes.md", "docs/builder-notes/session.md", "docs/records/turnstile.jsonl",
                          "docs/reviews/2026-09-24-signoff-turnstile-A.md", "notes/session-log.md"]
                         + ["%s Status: line %d" % (DOC, n) for n in STATUS_LINES] + [
                          "%s ## Build assumptions" % DOC, "%s ## Deviations" % DOC, "%s ## Discovered" % DOC,
                          "%s ## Handoffs" % DOC, "%s ## Punch list" % DOC,
                          ".env", "build/", "REVIEW.md"])


def listing(root):
    out = []
    for base, dirs, files in os.walk(root):
        for name in files:
            rel = os.path.relpath(os.path.join(base, name), root)
            if rel not in ("files.json", "withheld.json"):
                out.append(rel)
    return sorted(out)


def texts_under(root):
    for base, dirs, files in os.walk(root):
        for name in files:
            with open(os.path.join(base, name), "rb") as fh:
                yield os.path.join(base, name), fh.read().decode("utf-8", "replace")


class TheClassGuard(unittest.TestCase):
    """One fixture, every member of the class, the function driven directly; the exact file list and the
    exact withheld list of every packet."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vpacket-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws, self.base, self.head = class_repo(self.tmp)
        self.snap = packet.Snapshot(self.ws, self.head, DOC)
        self.gate = {"base": {"commit": self.base}, "head": self.head,
                     "boundary": gitio.name_status(self.ws, self.base)}
        self.wt = packet.worktree_names(self.ws)

    def build(self, spec):
        return packet.build(self.snap, spec, self.gate, testlib.SKILL, self.wt)

    def cut(self, spec, name):
        built = self.build(spec)
        dest = os.path.join(self.tmp, "cuts", name)
        packet.cut(built, dest)
        self.assertEqual(packet.check(built, dest), [])
        return built, dest

    def withheld(self, dest):
        return sorted(w["what"] for w in testlib.load_json(os.path.join(dest, "withheld.json"))["withheld"])

    def test_the_local_packet_is_exactly_the_allowed_files_the_spec_and_the_committed_sheet(self):
        built, dest = self.cut({"name": "local-spec", "side": "local", "lens": "spec", "profile": "repo-with-tools"}, "l")
        self.assertEqual(listing(dest), LOCAL)
        self.assertEqual(self.withheld(dest), COMMON_WITHHELD)
        sheet = testlib.read_text(os.path.join(dest, "documents", "REVIEW.md"))
        self.assertEqual(sheet, COMMITTED_SHEET)
        self.assertIn("COMMITTED-CHECK", testlib.read_text(os.path.join(dest, "mandate.md")))

    def test_the_outside_repo_packet_is_exactly_the_allowed_files(self):
        built, dest = self.cut({"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"}, "o")
        self.assertEqual(listing(dest), OUTSIDE_REPO)
        self.assertEqual(self.withheld(dest), sorted(COMMON_WITHHELD + ["REVIEW.md"]))
        whys = [w["why"] for w in testlib.load_json(os.path.join(dest, "withheld.json"))["withheld"] if w["what"] == "REVIEW.md"]
        self.assertTrue(any("local lenses only" in why for why in whys), whys)
        self.assertTrue(any("working-tree" in why for why in whys), whys)

    def test_the_outside_packet_only_packet_is_exactly_the_allowed_text_files(self):
        built, dest = self.cut({"name": "outside-deepseek", "side": "outside", "row": "deepseek", "profile": "packet-only"}, "p")
        self.assertEqual(listing(dest), OUTSIDE_PACKET_ONLY)
        self.assertEqual(self.withheld(dest), sorted(COMMON_WITHHELD + ["REVIEW.md", "src/blob.bin"]))
        self.assertEqual(built["left_out"], ["src/blob.bin"])

    def test_no_member_of_the_class_reaches_any_packet(self):
        for spec, name in (({"name": "local-spec", "side": "local", "lens": "spec", "profile": "repo"}, "l"),
                           ({"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"}, "o"),
                           ({"name": "outside-deepseek", "side": "outside", "row": "deepseek", "profile": "packet-only"}, "p")):
            built, dest = self.cut(spec, name)
            for path, text in texts_under(dest):
                if os.path.basename(path) in ("files.json", "withheld.json"):
                    continue
                for marker in MARKERS + ("MESSAGE-MARKER",):
                    self.assertNotIn(marker, text, (name, path, marker))

    def test_the_spec_keeps_everything_else_byte_for_byte(self):
        built, dest = self.cut({"name": "local-spec", "side": "local", "lens": "spec", "profile": "repo"}, "l")
        spec = testlib.read_text(os.path.join(dest, "documents", "spec.md"))
        self.assertEqual(spec, testlib.read_text(os.path.join(dest, "workspace", DOC)))
        lines = class_doc().split("\n")
        first_withheld = lines.index("## Build   assumptions") + 1
        kept = "".join(line + "\n" for number, line in enumerate(lines, 1)
                       if number < first_withheld and number not in STATUS_LINES)
        self.assertEqual(STATUS_LINES, [6, 30, 41])
        self.assertEqual(spec, kept)
        self.assertIn("Status: a fenced example stays\n## Deviations\n", spec)
        self.assertIn("````markdown\n```\nStatus: a four-backtick literal stays\n````\n", spec)
        self.assertIn("~~~\n```\n## Handoffs\n~~~\n", spec)

    def test_a_builders_notes_file_declared_by_its_first_heading_is_withheld_and_named(self):
        built, dest = self.cut({"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"}, "o")
        whys = dict((w["what"], w["why"]) for w in testlib.load_json(os.path.join(dest, "withheld.json"))["withheld"])
        self.assertIn("first heading", whys["notes/session-log.md"])
        self.assertTrue(os.path.isfile(os.path.join(dest, "workspace", "notes", "plain.md")))

    def recommit_doc(self, text):
        testlib.write_text(os.path.join(self.ws, DOC), text)
        testlib.git(self.ws, ["add", DOC])
        testlib.git(self.ws, ["commit", "-q", "-m", "the doc again"], when="2026-09-20T12:00:00-07:00")
        return testlib.git(self.ws, ["rev-parse", "HEAD"]).strip()

    def test_an_unclosed_fence_after_the_slices_stops_before_any_packet(self):
        text = class_doc().replace("## Build   assumptions\n", "````\n```\n## Build   assumptions\n")
        head = self.recommit_doc(text)
        with self.assertRaises(specmod.SpecUnreadable) as caught:
            packet.Snapshot(self.ws, head, DOC)
        lines = text.split("\n")
        self.assertEqual(caught.exception.line, lines.index("## Build   assumptions") - 1)

    def test_an_unclosed_fence_before_the_slices_stops_before_any_packet(self):
        text = class_doc().replace("## Slice A", "~~~~\n\n## Slice A", 1)
        head = self.recommit_doc(text)
        with self.assertRaises(specmod.SpecUnreadable) as caught:
            packet.Snapshot(self.ws, head, DOC)
        self.assertEqual(caught.exception.line, text.split("\n").index("~~~~") + 1)

    STRICT_SHAPES = (
        ("check 4's lazy continuation", ["- a note on the spinner", "that continues lazily", "  ```text",
                                         "##  Build assumptions", "```"], "  ```text"),
        ("the numbered lazy continuation", ["1. a note", "continues lazily", "   ~~~", "## Handoffs", "~~~"], "   ~~~"),
        ("a fence indented in a list item", ["- an item", "", "  ```", "  ## Punch list", "  ```"], "  ```"),
        ("a fence in a block quote", ["> a quote", "> ```", "> ## Punch list", "> ```"], "> ```"),
        ("one space of indent at top level", [" ```", "## Deviations", " ```"], " ```"),
        ("three spaces of indent at top level", ["   ```text", "   ## Discovered", "   ```"], "   ```text"),
        ("an indented line inside a margin fence that could close it", ["```", "x", "  ```", "## Punch list", "```"],
         "  ```"),
        ("an unclosed margin fence", ["```text", "## Punch list"], "```text"),
        ("a backtick info string holding a backtick", ["```x`y", "text"], "```x`y"),
        ("a raw HTML block ended by a no-break space line (C1A5-1)", ["<div>", "\u00a0", "```", ""], "<div>"),
        ("a raw HTML block ended by a form feed line (C1A5-1)", ["<div>", "\x0c", "```", ""], "<div>"),
        ("a comment holding a level 2 heading (C1A5-2)", ["<!--", "## Notes", "-->"], "<!--"),
        ("a comment holding a Status: label (C1A5-2)", ["<!--", "Status: signed off", "-->"], "<!--"),
        ("a pre block holding a heading", ["<pre>", "## Punch list", "</pre>"], "<pre>"),
        ("a details block", ["<details>", "## Handoffs", "</details>"], "<details>"),
        ("a processing instruction", ["<?x y ?>"], "<?x y ?>"),
        ("a declaration", ["<!X y>"], "<!X y>"),
        ("a CDATA section", ["<![CDATA[", "## Deviations", "]]>"], "<![CDATA["),
        ("a closing tag", ["</div>"], "</div>"),
        ("a tag after a list marker", ["- <div>", "## Discovered"], "- <div>"),
        ("a tag after a block-quote marker", ["> <div>"], "> <div>"),
        ("a tag after a tab", ["\t<div>"], "\t<div>"),
        ("a line opening with an inline placeholder", ["text that wraps", "<path> is the counter's file"],
         "<path> is the counter's file"),
        ("a line opening with an autolink", ["<https://example.com/turnstile>"], "<https://example.com/turnstile>"),
        ("an inline comment opened mid-line hiding a label (C1A6-1)", ["Depends on: A <!--", "Status: in progress", "-->"],
         "Status: in progress"),
        ("a link reference definition title in double quotes hiding a label (C1A6-1)",
         ["[plan-note]: /plan \"", "Status: not started", "\""], "Status: not started"),
        ("a link reference definition title in parentheses hiding a label (C1A6-1)",
         ["[plan-note]: /plan (", "Status: built", ")"], "Status: built"),
        ("an inline link title hiding a label (C1A6-1)", ["see [the plan](/plan \"", "Status: in progress", "\")"],
         "Status: in progress"),
        ("a second plain label in one slice (A10)", ["Status: built"], "Status: built"),
        ("a label with text after its value (A10)", ["Status: built today"], "Status: built today"),
        ("a label followed by a Setext underline (A10)", ["Status: built", "---"], "Status: built"),
    )
    HEADER_SHAPES = (
        ("an inline comment opened mid-line hiding a base (C1A6-1)",
         ["the branch point, see <!--", "Base: 1111111", "-->", "Base: 2222222"], "Base: 1111111"),
        ("a link reference definition title hiding a base (C1A6-1)",
         ["[b]: /plan \"", "Base: 1111111", "\"", "Base: 2222222"], "Base: 1111111"),
        ("an inline link title hiding a base (C1A6-1)", ["see [the plan](/plan \"", "Base: 1111111", "\")"],
         "Base: 1111111"),
        ("two Base lines (A10)", ["Base: 1111111", "", "Base: 2222222"], "Base: 2222222"),
        ("a short sha (A10)", ["Base: abc123"], "Base: abc123"),
        ("an upper-case sha (A10)", ["Base: ABCDEF1"], "Base: ABCDEF1"),
    )
    PLAIN_SHAPES = (
        ("check 7's slice heading and label indented one space (A12, C1A7-1)",
         [" ## Slice C %s the encoder" % D, " Status: built"], " ## Slice C %s the encoder" % D),
        ("check 7's slice heading and label indented three spaces (A12, C1A7-1)",
         ["   ## Slice C %s the encoder" % D, "   Status: built"], "   ## Slice C %s the encoder" % D),
        ("a slice heading with a tab after its hashes (A12, C1A7-1)", ["##\tSlice C %s the encoder" % D, "Status: built"],
         "##\tSlice C %s the encoder" % D),
        ("a bare ## (A12, C1A7-1)", ["##", "a paragraph under an empty heading"], "##"),
        ("an indented label with the exact one in a lazy block-quote line (A12, C1A7-1)",
         [" Status: built", "", "> Earlier draft:", "Status: signed off"], " Status: built"),
        ("an indented label with the exact one in a lazy list line (A12, C1A7-1)",
         [" Status: built", "", "- earlier draft:", "Status: signed off"], " Status: built"),
        ("an indented label with the exact one under an empty ## (A12, C1A7-1)",
         [" Status: built", "", "##", "Status: signed off"], " Status: built"),
        ("a withheld heading with two spaces after its hashes (A12; C1A2-5's spelling)", ["##  Deviations", "- LEAK"],
         "##  Deviations"),
        ("a withheld heading with a tab after its hashes (A12)", ["##\tDiscovered", "- LEAK"], "##\tDiscovered"),
        ("an indented withheld heading (A12)", ["  ## Handoffs", "- LEAK"], "  ## Handoffs"),
        ("a withheld heading after a list marker (A12)", ["- ## Punch list", "- LEAK"], "- ## Punch list"),
        ("a level 1 heading indented (A12)", ["   # Appendix"], "   # Appendix"),
        ("a label after a block-quote marker (A12)", ["> Status: built"], "> Status: built"),
        ("a label after a numbered marker (A12)", ["2) Status: built"], "2) Status: built"),
        ("a label after a tab (A12)", ["\tStatus: built"], "\tStatus: built"),
    )
    PLAIN_HEADER_SHAPES = (
        ("an indented Base: line (A12, C1A7-1)", [" Base: 1111111"], " Base: 1111111"),
        ("a Base: line after a list marker (A12)", ["* Base: 1111111"], "* Base: 1111111"),
        ("a heading with a tab after its hashes in the header (A12)", ["#\tTurnstile again"], "#\tTurnstile again"),
    )
    HEADER_AT = "signed off by an earlier reviewer\n"
    TWO_READINGS_SHAPES = (
        ("a Setext slice heading hides a slice (A13, family 1)", ["Slice C %s the encoder" % D, "---", "Goal: encode."],
         "Slice C %s the encoder" % D),
        ("a Setext withheld heading hides a withheld section (A13, family 1)", ["Punch list", "---", "- LEAK"],
         "Punch list"),
        ("a character-coded dash hides a slice (A13, family 2)", ["## Slice C &#8212; the encoder", "Status: built"],
         "## Slice C &#8212; the encoder"),
        ("a character-coded space hides a withheld section (A13, family 2)", ["## Punch&#32;list", "- LEAK"],
         "## Punch&#32;list"),
        ("a character-coded colon makes a second rendered label (A13, family 2)", ["Status&#58; built"],
         "Status&#58; built"),
        ("bold markup hides a withheld section (A13, family 3)", ["## **Punch list**", "- LEAK"], "## **Punch list**"),
        ("two spaces inside a slice heading hide a slice (A13, family 4)", ["## Slice  C %s the encoder" % D,
                                                                             "Status: built"],
         "## Slice  C %s the encoder" % D),
    )
    TWO_READINGS_HEADER_SHAPES = (
        ("an escaped colon hides a base (A13, family 5)", ["Base\\: 1111111"], "Base\\: 1111111"),
        ("a bold label hides a base (A13, family 5)", ["**Base:** 1111111"], "**Base:** 1111111"),
        ("a character-coded colon hides a base (A13, families 2 and 5)", ["Base&#58; 1111111"], "Base&#58; 1111111"),
    )

    # A14 (C1A8-1 to C1A8-3): (what, the text replaced in class_doc, its replacement, the line the stop names)
    ROUND_9_STOPS = (
        ("a bold Status: built above slice B's plain label, after a multi-line code span (C1A8-1)",
         "Depends on: A\nStatus: signed off", "Depends on: A\n\nNote `a\nb` here.\n**Status:** built\nStatus: signed off",
         "Note `a"),
        ("a character-coded Status: built above the plain label, after a multi-line link title (C1A8-1)",
         "Depends on: A\nStatus: signed off",
         "Depends on: A\n\nSee [the plan](/plan \"a\nb\").\n&#83;tatus: built\nStatus: signed off",
         "See [the plan](/plan \"a"),
        ("two rendered Base: lines in the header, after a multi-line code span (C1A8-1)",
         HEADER_AT, HEADER_AT + "\nNote `a\nb` here.\n**Base:** 1234567\nBase: abcdef1\n", "Note `a"),
        ("slice B's heading with an en dash (C1A8-2)", "## Slice B %s the spinner" % D, "## Slice B – the spinner",
         "## Slice B – the spinner"),
        ("slice B's heading with a zero-width space inside Slice (C1A8-2)", "## Slice B %s the spinner" % D,
         "## Sl​ice B %s the spinner" % D, "## Sl​ice B %s the spinner" % D),
        ("a ### Status: built heading above slice B's plain label (C1A8-3)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\n### Status: built\n\nStatus: signed off", "### Status: built"),
    )
    # A14 (C1A8-3): (what, a withheld near miss's heading, its canonical name); each is withheld from every packet
    ROUND_9_WITHHELD = (
        ("Punch-list", "## Punch-list", "## Punch list"),
        ("Punch list with a colon", "## Punch list:", "## Punch list"),
        ("a singular Handoff", "## Handoff", "## Handoffs"),
        ("Hand-offs", "## Hand-offs", "## Handoffs"),
    )

    # A15 (round 9, send-back 1): a label behind invisible characters (a zero-width space, a soft hyphen, a no-break
    # space), in slice B above its plain label and in the header above a plain Base: line; each stops naming its line
    # (since A16 the character list stops each first, naming the character)
    A15_STOPS = (
        ("a zero-width space before Status: built in slice B (A15)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\n\u200bStatus: built\n\nStatus: signed off", "\u200bStatus: built"),
        ("a soft hyphen before Status: built in slice B (A15)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\n\u00adStatus: built\n\nStatus: signed off", "\u00adStatus: built"),
        ("a no-break space before Status: built in slice B (A15)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\n\u00a0Status: built\n\nStatus: signed off", "\u00a0Status: built"),
        ("a zero-width space before a header Base: line (A15)", HEADER_AT,
         HEADER_AT + "\n\u200bBase: 1234567\n\nBase: abcdef1\n", "\u200bBase: 1234567"),
        ("a word joiner before a header Base: line (A15)", HEADER_AT,
         HEADER_AT + "\n\u2060Base: 1234567\n\nBase: abcdef1\n", "\u2060Base: 1234567"),
    )

    def test_every_a15_shape_stops_before_any_packet_naming_its_line(self):
        from vertical_core import fences  # noqa: E402
        for what, old, new, first in self.A15_STOPS:
            text = class_doc().replace(old, new, 1)
            self.assertNotEqual(text, class_doc(), what)
            problems = fences.read(text).problems            # A16: the character list, first
            self.assertEqual(problems[0][0], text.split("\n").index(first) + 1, what)
            self.assertIn("U+%04X" % ord(first[0]), problems[0][1], what)
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, what)

    def test_a_hidden_header_status_line_now_stops_before_any_packet_naming_its_character(self):
        """A15: a `Status:` line behind a format character or a Unicode space in the header is no card to either
        reading, and the spec removed it from every packet; since A16 its character stops the snapshot first."""
        for index, ch in enumerate(("\u200b", "\u00ad", "\ufeff", "\u00a0", "\u3000")):
            line = "%sStatus: HIDDEN-HEADER-MARKER built" % ch
            text = class_doc().replace(self.HEADER_AT, self.HEADER_AT + "\n" + line + "\n", 1)
            at = text.split("\n").index(line) + 1
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, at, repr(ch))
            self.assertIn("U+%04X" % ord(ch), caught.exception.what, repr(ch))

    def test_every_round_9_shape_stops_before_any_packet_naming_its_line(self):
        """A14: a rendered label in a paragraph whose lines cannot all be mapped, a level 1 or 2 heading that reads
        like a slice heading off the form, and a heading named like a label each stop the snapshot naming the line."""
        from vertical_core import fences  # noqa: E402
        for what, old, new, first in self.ROUND_9_STOPS:
            text = class_doc().replace(old, new, 1)
            self.assertNotEqual(text, class_doc(), what)
            odd = fences.unlisted(first)
            if odd is not None:     # A16: the zero-width space is outside the character list, so it stops first
                problems = fences.read(text).problems
                self.assertEqual(problems[0][0], text.split("\n").index(first) + 1, what)
                self.assertIn("U+%04X" % ord(odd[1]), problems[0][1], what)
            else:
                self.assertEqual(fences.read(text).problems, [], what)
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, what)

    def test_every_round_9_withheld_near_miss_reaches_no_packet_and_is_named(self):
        """A14 (C1A8-3): a level 1 or 2 section whose name starts with a withheld name's stem is withheld by both
        readings, absent from every packet and named with its lines."""
        for index, (what, heading, canonical) in enumerate(self.ROUND_9_WITHHELD):
            text = class_doc().replace("## Build   assumptions\n", heading + "\n- NEAR-MISS-MARKER skim slice B\n\n"
                                                                    "## Build   assumptions\n")
            first = text.split("\n").index(heading) + 1
            self.snap = packet.Snapshot(self.ws, self.recommit_doc(text), DOC)
            for spec, name in (({"name": "local-spec", "side": "local", "lens": "spec", "profile": "repo"}, "l"),
                               ({"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"},
                                "o"),
                               ({"name": "outside-deepseek", "side": "outside", "row": "deepseek",
                                 "profile": "packet-only"}, "p")):
                built, dest = self.cut(spec, "%s-%d" % (name, index))
                for path, body in texts_under(dest):
                    if os.path.basename(path) in ("files.json", "withheld.json"):
                        continue
                    self.assertNotIn("NEAR-MISS-MARKER", body, (what, path))
                withheld = testlib.load_json(os.path.join(dest, "withheld.json"))["withheld"]
                self.assertTrue(any(w["what"] == "%s %s" % (DOC, canonical) and
                                    "lines %d to %d" % (first, first + 2) in w["why"] for w in withheld), (what, withheld))

    def test_a_notes_file_only_the_wide_line_reading_declares_is_withheld_and_named(self):
        """A14 (C1A8-4): a file opening with an HTML line and a later builder's-notes heading is declared by the line
        reading's wide first heading and not by CommonMark's: no stop, and the file stays withheld."""
        testlib.write_text(os.path.join(self.ws, "notes", "readme-like.md"),
                           "<p align=\"center\">Turnstile</p>\n\n# Turnstile\n\n## Build notes\n\nWIDE-NOTES-MARKER\n")
        testlib.git(self.ws, ["add", "notes/readme-like.md"])
        testlib.git(self.ws, ["commit", "-q", "-m", "a readme-like file"], when="2026-09-20T12:00:00-07:00")
        self.snap = packet.Snapshot(self.ws, testlib.git(self.ws, ["rev-parse", "HEAD"]).strip(), DOC)
        built, dest = self.cut({"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"},
                               "o")
        self.assertIn("notes/readme-like.md", self.withheld(dest))
        for path, body in texts_under(dest):
            self.assertNotIn("WIDE-NOTES-MARKER", body, path)

    # A16 (C1A9-1 to C1A9-3): (what, the text replaced in class_doc, its replacement, the line the stop names, the
    # code point named or None)
    A16_STOPS = (
        ("U+3164 before Status: built in slice B (C1A9-1)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\n\u3164Status: built\n\nStatus: signed off", "\u3164Status: built", 0x3164),
        ("U+034F before a header Base: line (C1A9-1)", HEADER_AT, HEADER_AT + "\n\u034fBase: 1234567\n",
         "\u034fBase: 1234567", 0x034F),
        ("U+2800 before Slice in slice B's heading (C1A9-1)", "## Slice B %s the spinner" % D,
         "## \u2800Slice B %s the spinner" % D, "## \u2800Slice B %s the spinner" % D, 0x2800),
        ("U+FE0F before a withheld heading's name (C1A9-1)", "## Build   assumptions\n",
         "## \ufe0fPunch list\n- A16-LEAK-MARKER\n\n## Build   assumptions\n", "## \ufe0fPunch list", 0xFE0F),
        ("U+180B before a ### Status: heading (C1A9-1)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\n### \u180bStatus: built\n\nStatus: signed off", "### \u180bStatus: built", 0x180B),
        ("a right-to-left override in prose (A16)", "Goal: spin.", "Goal: spin \u202e back.",
         "Goal: spin \u202e back.", 0x202E),
        ("a Cyrillic letter in slice B's heading (C1A9-3)", "## Slice B %s the spinner" % D,
         "## \u0405lice B %s the spinner" % D, "## \u0405lice B %s the spinner" % D, 0x0405),
        ("full-width letters in a label (C1A9-3)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\n\uff33tatus: built\n\nStatus: signed off", "\uff33tatus: built", 0xFF33),
        ("a character reference to U+3164 before Status: built (A16, refusal (d))", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\n&#x3164;Status: built\n\nStatus: signed off", "&#x3164;Status: built", 0x3164),
        ("a lower-case status: label above slice B's plain one (C1A9-3)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\nstatus: built\n\nStatus: signed off", "status: built", None),
        ("a Status : label with a space before the colon (C1A9-3)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\nStatus : built\n\nStatus: signed off", "Status : built", None),
        ("a lower-case ### status: heading (C1A9-3)", "Depends on: A\nStatus: signed off",
         "Depends on: A\n\n### status: built\n\nStatus: signed off", "### status: built", None),
        ("a lower-case base: line in the header (C1A9-3)", HEADER_AT, HEADER_AT + "\nbase: 1234567\n",
         "base: 1234567", None),
        ("a zero-width space in a Punch list heading (A14's near miss, stopped since A16)", "## Build   assumptions\n",
         "## Punch\u200b list\n- A16-LEAK-MARKER\n\n## Build   assumptions\n", "## Punch\u200b list", 0x200B),
    )
    # A16 (4), C1A9-2: (what, a withheld name past the stems, its canonical name); each is withheld from every packet
    A16_WITHHELD = (
        ("Hand off", "## Hand off", "## Handoffs"),
        ("Hand-offs with an en dash", "## Hand\u2013offs", "## Handoffs"),
        ("a numbered Punch list", "## 1. Punch list", "## Punch list"),
        ("The punch list", "## The punch list", "## Punch list"),
        ("Build-assumptions", "## Build-assumptions", "## Build assumptions"),
    )

    def test_every_a16_shape_stops_before_any_packet_naming_its_line(self):
        from vertical_core import fences  # noqa: E402
        for what, old, new, first, code in self.A16_STOPS:
            text = class_doc().replace(old, new, 1)
            self.assertNotEqual(text, class_doc(), what)
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, what)
            if code is not None:
                self.assertIn("U+%04X" % code, caught.exception.what, what)
        self.assertTrue(fences.LISTED)

    def test_every_a16_withheld_name_reaches_no_packet_and_is_named(self):
        for index, (what, heading, canonical) in enumerate(self.A16_WITHHELD):
            text = class_doc().replace("## Build   assumptions\n", heading + "\n- A16-NEAR-MISS-MARKER skim slice B\n\n"
                                                                    "## Build   assumptions\n")
            first = text.split("\n").index(heading) + 1
            self.snap = packet.Snapshot(self.ws, self.recommit_doc(text), DOC)
            for spec, name in (({"name": "local-spec", "side": "local", "lens": "spec", "profile": "repo"}, "l"),
                               ({"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"},
                                "o"),
                               ({"name": "outside-deepseek", "side": "outside", "row": "deepseek",
                                 "profile": "packet-only"}, "p")):
                built, dest = self.cut(spec, "a16-%s-%d" % (name, index))
                for path, body in texts_under(dest):
                    if os.path.basename(path) in ("files.json", "withheld.json"):
                        continue
                    self.assertNotIn("A16-NEAR-MISS-MARKER", body, (what, path))
                withheld = testlib.load_json(os.path.join(dest, "withheld.json"))["withheld"]
                self.assertTrue(any(w["what"] == "%s %s" % (DOC, canonical) and
                                    "lines %d to %d" % (first, first + 2) in w["why"] for w in withheld), (what, withheld))

    def test_a_markdown_file_whose_heading_holds_an_unlisted_character_is_withheld_and_named(self):
        """A16 (2): a notes candidate, never a stop; the plain files stay."""
        files = {"notes/filler.md": "# Bench\u3164guide\n\nA16-FILLER-MARKER\n",
                 "notes/emoji.md": "# Rocket \U0001f680 notes\n\nA16-EMOJI-MARKER\n",
                 "notes/deep.md": "# Bench guide\n\n## \U0001f680 Features\n\nA16-DEEP-KEPT\n",
                 "notes/curly.md": "# Builder\u2019s notes\n\nA16-CURLY-MARKER\n"}
        for rel, text in sorted(files.items()):
            testlib.write_text(os.path.join(self.ws, rel), text)
        testlib.git(self.ws, ["add", "notes"])
        testlib.git(self.ws, ["commit", "-q", "-m", "two guides"], when="2026-09-20T12:00:00-07:00")
        self.snap = packet.Snapshot(self.ws, testlib.git(self.ws, ["rev-parse", "HEAD"]).strip(), DOC)
        for spec, name in (({"name": "local-spec", "side": "local", "lens": "spec", "profile": "repo"}, "l"),
                           ({"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"}, "o"),
                           ({"name": "outside-deepseek", "side": "outside", "row": "deepseek", "profile": "packet-only"},
                            "p")):
            built, dest = self.cut(spec, "a16-notes-%s" % name)
            whys = dict((w["what"], w["why"]) for w in testlib.load_json(os.path.join(dest, "withheld.json"))["withheld"])
            self.assertIn("U+3164", whys.get("notes/filler.md", ""), name)
            self.assertIn("U+1F680", whys.get("notes/emoji.md", ""), name)
            self.assertIn("first heading", whys.get("notes/curly.md", ""), name)
            for path, body in texts_under(dest):
                self.assertNotIn("A16-FILLER-MARKER", body, path)
                self.assertNotIn("A16-EMOJI-MARKER", body, path)
                self.assertNotIn("A16-CURLY-MARKER", body, path)
            self.assertNotIn("notes/plain.md", whys, name)
            self.assertNotIn("notes/deep.md", whys, name)

    def test_every_shape_the_two_readings_take_differently_stops_before_any_packet_naming_its_line(self):
        """A13: the line rules accept each shape; the second reading takes a decision differently, so the snapshot
        stops naming the first line where they differ."""
        from vertical_core import fences  # noqa: E402
        for what, shape, first in self.TWO_READINGS_SHAPES:
            text = class_doc().replace("## Build   assumptions\n", "\n".join(shape) + "\n\n## Build   assumptions\n")
            self.assertEqual(fences.read(text).problems, [], what)
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, what)
            self.assertIn("CommonMark", str(caught.exception), what)
        for what, shape, first in self.TWO_READINGS_HEADER_SHAPES:
            text = class_doc().replace(self.HEADER_AT, self.HEADER_AT + "\n" + "\n".join(shape) + "\n", 1)
            self.assertEqual(fences.read(text).problems, [], what)
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, what)

    def test_every_earlier_shape_is_stopped_by_its_line_rule_ahead_of_the_second_reading(self):
        """A13 keeps A8 to A12 as they are: each earlier shape is refused by the line rules, naming its line, before
        the two readings are compared."""
        from vertical_core import fences  # noqa: E402
        for shapes, at in ((self.STRICT_SHAPES + self.PLAIN_SHAPES, "## Build   assumptions\n"),
                           (self.HEADER_SHAPES + self.PLAIN_HEADER_SHAPES, self.HEADER_AT)):
            for what, shape, first in shapes:
                if at == self.HEADER_AT:
                    text = class_doc().replace(at, at + "\n" + "\n".join(shape) + "\n", 1)
                else:
                    text = class_doc().replace(at, "\n".join(shape) + "\n\n" + at)
                problems = fences.read(text).problems
                self.assertTrue(problems, what)
                self.assertEqual(problems[0][0], text.split("\n").index(first) + 1, what)

    def test_a_notes_file_the_two_readings_decide_differently_stops_before_any_packet(self):
        """A13: a character-coded first heading declares the file the builder's notes to CommonMark and not to the
        line reading; the snapshot stops naming the file and the line."""
        testlib.write_text(os.path.join(self.ws, "notes", "coded.md"), "# Builder&#32;notes\n\nCODED-NOTES-MARKER\n")
        testlib.git(self.ws, ["add", "notes/coded.md"])
        testlib.git(self.ws, ["commit", "-q", "-m", "coded notes"], when="2026-09-20T12:00:00-07:00")
        head = testlib.git(self.ws, ["rev-parse", "HEAD"]).strip()
        with self.assertRaises(specmod.SpecUnreadable) as caught:
            packet.Snapshot(self.ws, head, DOC)
        self.assertEqual(caught.exception.line, 1)
        self.assertIn("notes/coded.md", str(caught.exception))

    def test_markup_that_leaves_every_decision_equal_still_builds_every_packet(self):
        text = class_doc().replace("## Slice B %s the spinner" % D, "## Slice B %s the `spinner` **loop**" % D)
        head = self.recommit_doc(text)
        snap = packet.Snapshot(self.ws, head, DOC)
        self.assertIn("## Slice B %s the `spinner` **loop**" % D, snap.spec)
        self.assertEqual(sorted(r["what"] for r in snap.removed if r["what"] != "Status: line"),
                         ["## Build assumptions", "## Deviations", "## Discovered", "## Handoffs", "## Punch list"])


    def test_every_shape_the_strict_rule_stops_stops_before_any_packet_naming_its_line(self):
        for what, shape, first in self.STRICT_SHAPES:
            text = class_doc().replace("## Build   assumptions\n", "\n".join(shape) + "\n\n## Build   assumptions\n")
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, what)

    def test_every_header_shape_the_label_rule_stops_stops_before_any_packet_naming_its_line(self):
        """A10, C1A6-1: a `Base:` line in the header that is not exact, not the last line of its paragraph, or a
        second one, stops the snapshot naming its line."""
        for what, shape, first in self.HEADER_SHAPES:
            text = class_doc().replace(self.HEADER_AT, self.HEADER_AT + "\n" + "\n".join(shape) + "\n", 1)
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, what)

    def test_every_shape_the_plain_structure_rule_stops_stops_before_any_packet_naming_its_line(self):
        """A12, C1A7-1: a heading or a `Status:` or `Base:` label off the plain form (indented, after a list-item or
        block-quote marker, a heading not followed by exactly one space) stops the snapshot naming its line, in a
        slice and in the header."""
        for what, shape, first in self.PLAIN_SHAPES:
            text = class_doc().replace("## Build   assumptions\n", "\n".join(shape) + "\n\n## Build   assumptions\n")
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, what)
        for what, shape, first in self.PLAIN_HEADER_SHAPES:
            text = class_doc().replace(self.HEADER_AT, self.HEADER_AT + "\n" + "\n".join(shape) + "\n", 1)
            head = self.recommit_doc(text)
            with self.assertRaises(specmod.SpecUnreadable) as caught:
                packet.Snapshot(self.ws, head, DOC)
            self.assertEqual(caught.exception.line, text.split("\n").index(first) + 1, what)

    def test_the_strict_shapes_in_another_markdown_file_never_stop_the_run(self):
        """The rule reads the build doc; another `.md` file of the commit is copied as it is (its first heading is
        still read for the builder's-notes rule, never a stop)."""
        body = "# Bench guide\n\n" + "\n\n".join("\n".join(shape) for what, shape, first
                                                     in self.STRICT_SHAPES + self.HEADER_SHAPES + self.PLAIN_SHAPES
                                                     + self.PLAIN_HEADER_SHAPES) + "\n"
        testlib.write_text(os.path.join(self.ws, "notes", "bench-guide.md"), body)
        testlib.git(self.ws, ["add", "notes/bench-guide.md"])
        testlib.git(self.ws, ["commit", "-q", "-m", "a guide"], when="2026-09-20T12:00:00-07:00")
        head = testlib.git(self.ws, ["rev-parse", "HEAD"]).strip()
        snap = packet.Snapshot(self.ws, head, DOC)
        self.assertEqual(snap.tree["notes/bench-guide.md"], body.encode("utf-8"))

    def test_the_copies_hold_the_commits_bytes_with_no_attribute_applied(self):
        built, dest = self.cut({"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"}, "o")
        self.assertEqual(testlib.read_text(os.path.join(dest, "workspace", "src", "ver.txt")), "$Format:%B$\n")
        self.assertFalse(os.path.exists(os.path.join(dest, "workspace", ".git")))

    def test_the_sheet_and_the_lenses_come_from_the_commit(self):
        self.assertEqual(self.snap.sheet["state"], "read")
        self.assertEqual(self.snap.sheet["checks"], ["COMMITTED-CHECK a reset never goes negative"])

    def test_a_retry_is_a_fresh_copy_and_a_planted_file_in_an_earlier_copy_never_reaches_it(self):
        spec = {"name": "local-spec", "side": "local", "lens": "spec", "profile": "repo-with-tools"}
        first, one = self.cut(spec, "first")
        testlib.write_text(os.path.join(one, "workspace", "docs", "reviews", "prior.md"), "PLANTED-IN-AN-EARLIER-COPY\n")
        testlib.write_text(os.path.join(one, "workspace", ".pytest_cache", "v"), "PLANTED-IN-AN-EARLIER-COPY\n")
        testlib.write_text(os.path.join(one, "documents", "spec.md"), "PLANTED-IN-AN-EARLIER-COPY\n")
        self.assertEqual(sorted(packet.check(first, one)), sorted([
            "workspace/docs/reviews/prior.md was added after the packet was cut",
            "workspace/.pytest_cache/v was added after the packet was cut",
            "documents/spec.md changed after the packet was cut"]))
        retry, two = self.cut(spec, "retry")
        self.assertEqual(listing(two), LOCAL)
        self.assertEqual(self.withheld(two), COMMON_WITHHELD)
        for path, text in texts_under(two):
            self.assertNotIn("PLANTED-IN-AN-EARLIER-COPY", text, path)
        self.assertEqual(packet.digest(first), packet.digest(retry))

    def test_the_withheld_list_names_nothing_that_was_delivered(self):
        for spec, name in (({"name": "local-spec", "side": "local", "lens": "spec", "profile": "repo"}, "l"),
                           ({"name": "outside-gpt-astra", "side": "outside", "row": "gpt-astra", "profile": "repo"}, "o")):
            built, dest = self.cut(spec, name)
            delivered = set(p[len("workspace/"):] for p in listing(dest) if p.startswith("workspace/"))
            for what in self.withheld(dest):
                if what == "REVIEW.md":
                    continue
                self.assertNotIn(what, delivered, (name, what))


class TheAllowRule(unittest.TestCase):
    """The exclusions, each tested on every path component."""

    def test_each_exclusion_and_what_it_lets_through(self):
        for path in ("docs/reviews/x.md", "docs/records/a.jsonl", "pkg/docs/reviews/x.md", "Docs/Reviews/x.md",
                     "REVIEW.md", "docs/builder-notes.md", "docs/builder-notes/session.md", "notes/Build_Notes/a.txt",
                     "a/BUILDER.NOTES/b/c.py", "../escape.py"):
            self.assertIsNotNone(packet.left_out_by_rule(path), path)
        for path in ("docs/review.md", "docs/reviewsx/a.md", "src/records/a.py", "sub/REVIEW.md", "docs/notes.md",
                     "src/build.py", "README.md"):
            self.assertIsNone(packet.left_out_by_rule(path), path)


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the probes run the gate, the ask, scope and the requests (records, readers' roster, jsonschema)")
class TheAstraProbes(unittest.TestCase):
    """The outside reviewer's probes on 3706302 (B1, B2, B4, M6) and C1A2-5, through the real CLI."""

    def setUp(self):
        self.tmp = testlib.make_scratch("vprobe-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def every_reviewer_text(self, run_dir):
        for folder in ("packets", "summons"):
            root = os.path.join(run_dir, folder)
            if not os.path.isdir(root):
                continue
            for path, text in texts_under(root):
                if os.path.basename(path) not in ("files.json", "withheld.json"):
                    yield path, text
        for base, dirs, files in os.walk(os.path.join(run_dir, "requests")):
            for name in files:
                yield os.path.join(base, name), testlib.read_text(os.path.join(base, name))

    def withheld_of_every_packet(self, run_dir):
        out = []
        for folder in ("packets", "summons"):
            root = os.path.join(run_dir, folder)
            for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
                out.append((name, testlib.load_json(os.path.join(root, name, "withheld.json"))["withheld"]))
        return out

    def test_b1_an_untracked_sheet_never_reaches_a_packet_or_picks_the_lenses(self):
        ws, info = vlib.make_repo(self.tmp, review_sheet=None, records=True)
        testlib.write_text(os.path.join(ws, "REVIEW.md"), UNCOMMITTED_SHEET)
        drive, run_dir = vlib.start(self.tmp, ws)
        self.assertEqual(vlib.through_ask(drive, self.tmp, run_dir)[0], 0)
        code, out, err = drive(["scope", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["lenses"], ["spec", "correctness", "seams"])
        self.assertEqual(out["review_sheet"], "absent")
        self.assertEqual(drive(["request", "--run-dir", run_dir])[0], 0)
        for path, text in self.every_reviewer_text(run_dir):
            self.assertNotIn("UNTRACKED-ADVOCACY", text, path)
        for name, withheld in self.withheld_of_every_packet(run_dir):
            whys = [w["why"] for w in withheld if w["what"] == "REVIEW.md"]
            self.assertEqual(len(whys), 1, (name, whys))
            self.assertIn("untracked", whys[0])

    def test_b1_a_committed_sheet_is_read_from_the_commit_not_the_working_tree(self):
        ws, info = vlib.make_repo(self.tmp, review_sheet=COMMITTED_SHEET, records=True)
        testlib.write_text(os.path.join(ws, "REVIEW.md"), UNCOMMITTED_SHEET)
        drive, run_dir = vlib.start(self.tmp, ws, owner_words={"committed_only": "review the committed state only"})
        self.assertEqual(vlib.through_ask(drive, self.tmp, run_dir)[0], 0)
        code, out, err = drive(["scope", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["lenses"], ["spec", "correctness", "seams", "accessibility"])
        self.assertEqual(drive(["request", "--run-dir", run_dir])[0], 0)
        seen = False
        for path, text in self.every_reviewer_text(run_dir):
            self.assertNotIn("UNTRACKED-ADVOCACY", text, path)
            seen = seen or "COMMITTED-CHECK" in text
        self.assertTrue(seen)

    def test_b2_a_retry_gets_a_fresh_copy_and_a_plant_in_the_earlier_copy_never_reaches_it(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        first = [c for c in vlib.load(run_dir, "requests-local.json")["calls"] if c["lens"] == "spec"][0]
        old = testlib.load_json(first["request_file"])
        testlib.write_text(os.path.join(old["workspace"], "docs", "reviews", "prior.md"), "PLANTED-IN-AN-EARLIER-COPY\n")
        testlib.write_text(os.path.join(run_dir, "packets", "local-spec", "workspace", "docs", "reviews", "prior.md"),
                           "PLANTED-IN-AN-EARLIER-COPY\n")
        code, out, err = drive(["request", "--run-dir", run_dir, "--resend", "spec", "--status", "incomplete"])
        self.assertEqual(code, 0, (out, err))
        new = testlib.load_json(out["call"]["request_file"])
        self.assertNotEqual(new["workspace"], old["workspace"])
        self.assertFalse(os.path.exists(os.path.join(new["workspace"], "docs", "reviews")))
        self.assertEqual(listing(os.path.dirname(new["workspace"])),
                         [p for p in listing(os.path.dirname(old["workspace"])) if p != "workspace/docs/reviews/prior.md"])
        for path, text in texts_under(os.path.dirname(new["workspace"])):
            self.assertNotIn("PLANTED-IN-AN-EARLIER-COPY", text, path)

    def test_b4_a_builder_notes_folder_reaches_no_packet_and_is_named(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp, repo={"extra_build_files": {
            "docs/builder-notes/session.md": "BUILDER-DIRECTORY-ADVOCACY skim it\n"}})
        for path, text in self.every_reviewer_text(run_dir):
            self.assertNotIn("BUILDER-DIRECTORY-ADVOCACY", text, path)
        packets = self.withheld_of_every_packet(run_dir)
        self.assertTrue(packets)
        for name, withheld in packets:
            self.assertIn("docs/builder-notes/session.md", [w["what"] for w in withheld], name)

    def test_m6_a_header_status_line_reaches_no_packet_and_is_named(self):
        doc = vlib.build_doc(extra_header=["Status: signed off by previous reviewer HEADER-STATUS"])
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp, repo={"doc_text": doc})
        for path, text in self.every_reviewer_text(run_dir):
            self.assertNotIn("HEADER-STATUS", text, path)
        line = doc.split("\n").index("Status: signed off by previous reviewer HEADER-STATUS") + 1
        for name, withheld in self.withheld_of_every_packet(run_dir):
            self.assertIn("%s Status: line %d" % (DOC, line), [w["what"] for w in withheld], name)

    def test_c1a2_5_a_withheld_heading_with_two_spaces_now_stops_the_gate_naming_its_line(self):
        """A12: `##` then two spaces is off the plain form, so the gate stops `doc-unreadable` before any packet."""
        doc = vlib.build_doc().replace("## Deviations\n", "##  Deviations\n- DEVIATION-MARKER skipped it\n")
        ws, info = vlib.make_repo(self.tmp, doc_text=doc, records=True)
        drive, run_dir = vlib.start(self.tmp, ws)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        self.assertEqual((code, (out or {}).get("stop_tag")), (10, "doc-unreadable"), (out, err))
        self.assertIn("line %d" % (doc.split("\n").index("##  Deviations") + 1), out["reason"])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "packets")))

    def test_c1a2_5_a_withheld_heading_in_odd_case_and_spacing_on_the_plain_form_is_withheld_and_named(self):
        doc = vlib.build_doc().replace("## Deviations\n", "## DEVIATIONS  \n- DEVIATION-MARKER skipped it\n")
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp, repo={"doc_text": doc})
        for path, text in self.every_reviewer_text(run_dir):
            self.assertNotIn("DEVIATION-MARKER", text, path)
        for name, withheld in self.withheld_of_every_packet(run_dir):
            self.assertIn("%s ## Deviations" % DOC, [w["what"] for w in withheld], name)

    def test_every_summons_copy_is_held_to_what_scope_recorded(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        path = os.path.join(run_dir, "scope.json")
        scope = testlib.load_json(path)
        scope["packets"][0]["digest"] = "0" * 64
        testlib.write_json(path, scope)
        code, out, err = drive(["request", "--run-dir", run_dir])
        self.assertEqual(code, 5, (out, err))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-local.json")))
        self.assertFalse(os.path.isdir(os.path.join(run_dir, "requests")))


if __name__ == "__main__":
    unittest.main()
