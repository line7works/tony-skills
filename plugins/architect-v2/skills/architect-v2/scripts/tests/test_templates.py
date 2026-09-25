"""The templates (E14-12, required test 4): parse then render is byte-identical.

On each form as shipped under `references/templates/` and on a filled example of each document
(LF, CRLF, and no final newline); a changed label is detected; the renderers given the form's own
placeholders produce the form byte for byte; the reading beside a form is never rendered.
"""
import os
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import templates  # noqa: E402

D = "\u2014"
M = "·"

SCOPE = """# Widget %(D)s scope doc (2026-09-20)

Intent: a small widget that counts turns, for the owner's bench tests.
Decisions:
- Python 3.9 standard library only %(D)s decided (Q1)
- One module %(D)s assumed (small and reversible)
- The storage format %(D)s parked: needs research
Out of scope: a web view %(D)s declined
Research: docs/research/turns.md
Open: how often the counter resets
Next: /blueprint when ready.
""" % {"D": D}

ARCH = """# Widget %(D)s architecture (2026-09-21)

Scope doc: docs/scope/2026-09-20-widget.md
Blind review: none yet
Artifact: https://example.invalid/artifact/widget

## Walkthrough target
Who: Sam Bench  %(M)s  When: 2026-10-01  %(M)s  Must be able to: count turns, reset

## v0 drawing
Components: one module `widget.py`
Data flow: the bench script calls `spin()` and prints the count.
Diagram: bench -> widget

## Poured concrete (one-way doors)
- language %(D)s Python 3.9 %(D)s every caller imports it

## Deferred
- a web view %(D)s door stays open because the module has no I/O

## Run log
### Run 1 %(D)s 2026-09-21 %(D)s trigger: first run
Exit ramp: system; the interview continued
Step 3.1 (walkthrough target): Sam Bench, 2026-10-01, count and reset
Step 3.2 (candidates): module; CLI; service. chosen: module; rejected: service %(D)s nothing needs a server
Step 3.3 (one-way doors): language settled
Rulings: declined
Changed this run: first run
""" % {"D": D, "M": M}

BUILD = """# Widget %(D)s build plan (2026-09-22)

Intent: count turns for the owner's bench tests.
Constraints: Python 3.9 standard library; `python3 -m unittest`.
Out of scope: a web view %(D)s declined in the scope doc
Plan: inspected 2026-09-23 by claude-opus-5 %(M)s 0 BLOCKER %(M)s 1 MAJOR %(M)s 0 MINOR

## Slice A %(D)s Count turns
Goal: `spin()` returns the number of turns.
Requirements:
- R1 %(D)s `spin()` returns an int
Acceptance criteria:
- AC1: `spin()` returns 3 after three calls %(D)s verify: new test at tests/test_widget.py
Footprint: src/widget.py, tests/test_widget.py
Not in this slice: the reset
Depends on: nothing
Status: not started

## Build assumptions
## Deviations
## Discovered
## Handoffs
## Punch list
""" % {"D": D, "M": M}

DOCS = {"scope-doc": SCOPE, "architecture-doc": ARCH, "build-doc": BUILD}


class TheFormsLoad(unittest.TestCase):

    def test_every_template_has_one_form_and_a_reading(self):
        for name in templates.NAMES:
            form = templates.form(name)
            self.assertTrue(form.endswith("\n"), name)
            self.assertNotIn("```", form, name)
            reading = templates.reading(name)
            self.assertTrue(reading.strip(), name)
            self.assertNotIn(reading.strip().split("\n")[0], form, "the reading is never in the form")


class RoundTrip(unittest.TestCase):

    def assertRoundTrip(self, name, text):
        parsed = templates.parse(name, text)
        self.assertEqual(templates.render(parsed), text, name)

    def test_each_form_as_shipped(self):
        for name in templates.NAMES:
            self.assertRoundTrip(name, templates.form(name))

    def test_each_filled_document(self):
        for name, text in DOCS.items():
            self.assertRoundTrip(name, text)

    def test_crlf_and_no_final_newline(self):
        for name, text in DOCS.items():
            self.assertRoundTrip(name, text.replace("\n", "\r\n"))
            self.assertRoundTrip(name, text.rstrip("\n"))

    def test_the_inspect_lines(self):
        lines = [templates.render_stamp("2026-09-23", "gpt-6-astra", blocker=1, major=2, minor=0),
                 templates.render_stamp("2026-09-23", "gpt-6-astra", question=2),
                 templates.render_stamp("2026-09-23", "gpt-6-astra"),
                 templates.render_question("docs/plans/x.md", 12, "confirm R2 was decided", "gpt-6-astra"),
                 templates.render_clean("gpt-6-astra")]
        for line in lines:
            parsed = templates.parse_line(line)
            self.assertEqual(templates.render_line(parsed), line)


class Conformance(unittest.TestCase):

    def test_the_forms_and_the_filled_documents_conform(self):
        for name in ("scope-doc", "architecture-doc", "build-doc"):
            self.assertEqual(templates.check(name, templates.form(name)), [], name)
            self.assertEqual(templates.check(name, DOCS[name]), [], name)

    def test_a_changed_label_is_detected(self):
        changes = [("scope-doc", "Out of scope:", "Out-of-scope:"),
                   ("scope-doc", "Decisions:", "Decision:"),
                   ("architecture-doc", "Blind review:", "Blind-review:"),
                   ("architecture-doc", "## Poured concrete (one-way doors)", "## Poured concrete"),
                   ("build-doc", "Acceptance criteria:", "Acceptance:"),
                   ("build-doc", "Status: not started", "State: not started"),
                   ("build-doc", "## Punch list", "## Punchlist")]
        for name, old, new in changes:
            text = DOCS[name].replace(old, new, 1)
            self.assertNotEqual(text, DOCS[name])
            findings = templates.check(name, text)
            self.assertTrue(findings, "%s: %r -> %r not detected" % (name, old, new))
            self.assertTrue(any(old.split(":")[0].lstrip("# ") in f["message"] for f in findings),
                            (name, old, findings))

    def test_a_label_out_of_order_is_detected(self):
        text = SCOPE.replace("Research: docs/research/turns.md\n", "").replace(
            "Intent:", "Research: docs/research/turns.md\nIntent:")
        self.assertTrue(templates.check("scope-doc", text))

    def test_a_changed_title_form_is_detected(self):
        self.assertTrue(templates.check("scope-doc", SCOPE.replace("scope doc (", "scope (")))
        self.assertTrue(templates.check("build-doc", BUILD.replace("build plan (", "plan (")))

    def test_a_changed_stamp_is_detected(self):
        for bad in ("Plan: inspected 2026-09-23 by m %s 1 BLOCKERS %s 0 MAJOR %s 0 MINOR" % (M, M, M),
                    "Plan: inspected 2026-09-23 by m - clean",
                    "QUESTION %s x.md %s what %s m" % (M, M, M)):
            self.assertIsNone(templates.parse_line(bad), bad)


class LoadBearingFields(unittest.TestCase):
    """Finding 3 of the reviewer's short look (round 3): the walkthrough target line carries its
    three fields, and a QUESTION or clean line with a blank field is not a line of the form."""

    WHO = "Who: Sam Bench  %(M)s  When: 2026-10-01  %(M)s  Must be able to: count turns, reset" % {"M": M}

    def findings(self, replacement):
        text = ARCH.replace(self.WHO, replacement)
        self.assertNotEqual(text, ARCH)
        line_no = text.split("\n").index(replacement) + 1
        found = templates.check("architecture-doc", text)
        self.assertEqual(templates.render(templates.parse("architecture-doc", text)), text)
        return line_no, found

    def test_a_missing_recased_or_empty_field_is_a_finding_naming_the_line(self):
        shapes = {"missing-when": "Who: Sam  %s  Must be able to: count" % M,
                  "wrong-case": "Who: Sam  %s  when: tomorrow  %s  Must be able to: count" % (M, M),
                  "blank-when": "Who: Sam  %s  When:   %s  Must be able to: count" % (M, M),
                  "blank-who": "Who:   %s  When: 2026-10-01  %s  Must be able to: count" % (M, M),
                  "blank-must": "Who: Sam  %s  When: 2026-10-01  %s  Must be able to:  " % (M, M),
                  "out-of-order": "Who: Sam  %s  Must be able to: count  %s  When: 2026-10-01" % (M, M),
                  "no-separator": "Who: Sam  When: 2026-10-01  Must be able to: count"}
        for key, replacement in shapes.items():
            line_no, found = self.findings(replacement)
            self.assertTrue(found, key)
            self.assertIn(line_no, [f["line"] for f in found], key)
            self.assertTrue(any("Who:, When:, and Must be able to:" in f["message"] for f in found), (key, found))

    def test_the_filled_line_and_the_form_still_conform(self):
        for text in (ARCH, ARCH.replace("\n", "\r\n"), ARCH.rstrip("\n"), templates.form("architecture-doc")):
            self.assertEqual(templates.check("architecture-doc", text), [])

    def test_a_question_line_with_a_blank_field_does_not_parse(self):
        for line in ("QUESTION %s a.md:1 %s   %s model" % (M, M, M),
                     "QUESTION %s a.md:1 %s question %s   " % (M, M, M),
                     "QUESTION %s   :1 %s question %s model" % (M, M, M)):
            self.assertIsNone(templates.parse_line(line), line)
        self.assertIsNotNone(templates.parse_line("QUESTION %s a.md:1 %s question %s model" % (M, M, M)))

    def test_a_clean_line_with_a_blank_model_does_not_parse(self):
        self.assertIsNone(templates.parse_line("clean %s no surviving findings or questions %s   " % (D, M)))
        self.assertIsNotNone(templates.parse_line("clean %s no surviving findings or questions %s m" % (D, M)))


class RenderFromValues(unittest.TestCase):

    def test_the_scope_doc_renderer_gives_the_form(self):
        form = templates.form("scope-doc")
        lines = form.split("\n")
        rendered = templates.render_scope_doc(
            title="<Idea>", date="<date>",
            intent=lines[2][len("Intent: "):],
            decisions=[l[2:] for l in lines if l.startswith("- ")],
            out_of_scope=[lines[7][len("Out of scope: "):]],
            research=[lines[8][len("Research: "):]],
            open_items=[lines[9][len("Open: "):]],
            next_line=lines[10][len("Next: "):])
        self.assertEqual(rendered, form)

    def test_the_scope_doc_renderer_on_values(self):
        rendered = templates.render_scope_doc(
            title="Widget", date="2026-09-20",
            intent="a small widget that counts turns, for the owner's bench tests.",
            decisions=[templates.render_ledger_line("Python 3.9 standard library only", "decided", "Q1"),
                       templates.render_ledger_line("One module", "assumed", "small and reversible"),
                       templates.render_ledger_line("The storage format", "parked", "needs research")],
            out_of_scope=["a web view %s declined" % D], research=["docs/research/turns.md"],
            open_items=["how often the counter resets"])
        self.assertEqual(rendered, SCOPE)

    def test_a_parked_reason_outside_the_three_is_refused(self):
        with self.assertRaises(templates.FormError):
            templates.render_ledger_line("x", "parked", "later")

    def test_the_build_doc_renderer_on_values(self):
        rendered = templates.render_build_doc(
            title="Widget", date="2026-09-22",
            intent="count turns for the owner's bench tests.",
            constraints="Python 3.9 standard library; `python3 -m unittest`.",
            out_of_scope=["a web view %s declined in the scope doc" % D],
            stamps=[templates.render_stamp("2026-09-23", "claude-opus-5", major=1)],
            slices=[{"name": "A", "short": "Count turns", "goal": "`spin()` returns the number of turns.",
                     "requirements": ["R1 %s `spin()` returns an int" % D],
                     "criteria": [("AC1: `spin()` returns 3 after three calls",
                                   "new test at tests/test_widget.py")],
                     "footprint": "src/widget.py, tests/test_widget.py",
                     "not_in_slice": "the reset", "depends_on": "nothing"}])
        self.assertEqual(rendered, BUILD)

    def test_the_build_doc_renderer_gives_the_form(self):
        form = templates.form("build-doc")
        rendered = templates.render_build_doc(
            title="<Feature>", date="<date>",
            intent="<what this is, who it's for, what it enables %s the why the builder needs>" % D,
            constraints="<stack, conventions, test command, hard requirements>",
            out_of_scope=["<deferred item %s reason it was deferred (this is /signoff's written evidence)>" % D],
            slices=[{"name": "A", "short": "<short name>", "goal": "<one sentence>",
                     "requirements": ["<R1 %s traceable to the discussion>" % D],
                     "criteria": [("<AC1: one measurable end state>",
                                   "<existing test | new test at <path> | manual: <steps>>")],
                     "footprint": "<files expected to change>",
                     "not_in_slice": "<adjacent work that belongs elsewhere>",
                     "depends_on": "<nothing | Slice X>", "status": "not started"},
                    {"name": "B", "short": "..."}])
        self.assertEqual(rendered, form)

    def test_the_architecture_doc_renderer_on_values(self):
        rendered = templates.render_architecture_doc(
            title="Widget", date="2026-09-21",
            scope_doc="docs/scope/2026-09-20-widget.md", blind_review="none yet",
            artifact="https://example.invalid/artifact/widget",
            who="Sam Bench", when="2026-10-01", must="count turns, reset",
            components="one module `widget.py`",
            data_flow="the bench script calls `spin()` and prints the count.",
            diagram="bench -> widget",
            poured=["language %s Python 3.9 %s every caller imports it" % (D, D)],
            deferred=["a web view %s door stays open because the module has no I/O" % D],
            runs=[templates.render_run_block(
                1, "2026-09-21", "first run", exit_ramp="system; the interview continued",
                walkthrough="Sam Bench, 2026-10-01, count and reset",
                candidates="module; CLI; service. chosen: module; rejected: service %s nothing needs a server" % D,
                doors="language settled", rulings="declined", changed="first run")])
        self.assertEqual(rendered, ARCH)

    def test_the_stamp_forms(self):
        self.assertEqual(templates.render_stamp("2026-09-23", "m", blocker=1, major=0, minor=2),
                         "Plan: inspected 2026-09-23 by m %s 1 BLOCKER %s 0 MAJOR %s 2 MINOR" % (M, M, M))
        self.assertEqual(templates.render_stamp("2026-09-23", "m", minor=1, question=3),
                         "Plan: inspected 2026-09-23 by m %s 0 BLOCKER %s 0 MAJOR %s 1 MINOR %s 3 QUESTION"
                         % (M, M, M, M))
        self.assertEqual(templates.render_stamp("2026-09-23", "m"), "Plan: inspected 2026-09-23 by m %s clean" % M)
        self.assertEqual(templates.render_clean("m"), "clean %s no surviving findings or questions %s m" % (D, M))
        self.assertEqual(templates.render_question("a.md", 3, "what", "m"), "QUESTION %s a.md:3 %s what %s m" % (M, M, M))

    def test_the_inspect_form_lines_parse(self):
        for line in templates.form("inspect-lines").rstrip("\n").split("\n"):
            self.assertIsNotNone(templates.parse_line(line), line)

    def test_a_stamp_parses_to_its_counts(self):
        parsed = templates.parse_line(templates.render_stamp("2026-09-23", "m", blocker=1, question=2))
        self.assertEqual((parsed["kind"], parsed["date"], parsed["model"], parsed["counts"], parsed["question"]),
                         ("stamp", "2026-09-23", "m", {"BLOCKER": 1, "MAJOR": 0, "MINOR": 0}, 2))


class NoV1Forms(unittest.TestCase):

    def test_the_templates_name_no_v1_file(self):
        for name in templates.NAMES:
            text = testlib.read_text(os.path.join(testlib.TEMPLATES, name + ".md"))
            for folder in ("precon", "architect", "blueprint", "inspect", "build", "signoff", "recheck"):
                self.assertNotIn("plugins/%s/" % folder, text)


if __name__ == "__main__":
    unittest.main()
