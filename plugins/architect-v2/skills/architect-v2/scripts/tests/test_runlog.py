"""`runlog.py`: the architecture doc's run-log continuation and strikethrough rule (E14-1).

A re-run appends `### Run <N>` with N one more than the highest; superseded lines are struck
through, never deleted; a proposed document that drops a prior run-log block or a prior
poured-concrete line is caught before anything is written.
"""
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import runlog, templates  # noqa: E402

D = "\u2014"
DOC = """# Widget %(D)s architecture (2026-09-21)

Scope doc: docs/scope/2026-09-20-widget.md
Blind review: none yet
Artifact: https://example.invalid/artifact/widget

## Poured concrete (one-way doors)
- language %(D)s Python 3.9 %(D)s every caller imports it
- storage %(D)s none %(D)s nothing is remembered

## Deferred
- a web view %(D)s door stays open because the module has no I/O

## Run log
### Run 1 %(D)s 2026-09-21 %(D)s trigger: first run
Exit ramp: system; the interview continued
Changed this run: first run

### Run 3 %(D)s 2026-09-23 %(D)s trigger: changed direction
Exit ramp: system
Changed this run: storage reconsidered
""" % {"D": D}


class Numbers(unittest.TestCase):

    def test_the_next_run_is_one_more_than_the_highest(self):
        self.assertEqual([n for n, _ in runlog.runs(DOC)], [1, 3])
        self.assertEqual(runlog.next_run(DOC), 4)

    def test_a_doc_with_no_run_is_run_one(self):
        self.assertEqual(runlog.next_run("# W %s architecture (2026-09-21)\n\n## Run log\n" % D), 1)


class Append(unittest.TestCase):

    def test_the_block_lands_at_the_tail_of_the_run_log(self):
        block = templates.render_run_block(4, "2026-09-24", "idea blossomed", exit_ramp="system",
                                           walkthrough="n/a", candidates="n/a", doors="n/a",
                                           rulings="declined", changed="the storage door")
        out = runlog.append_run(DOC, block)
        self.assertTrue(out.startswith(DOC.rstrip("\n")))
        self.assertTrue(out.endswith(block if block.endswith("\n") else block + "\n"))
        self.assertEqual([n for n, _ in runlog.runs(out)], [1, 3, 4])
        self.assertEqual(runlog.losses(DOC, out), [])

    def test_a_block_with_the_wrong_number_is_refused(self):
        block = templates.render_run_block(2, "2026-09-24", "x", exit_ramp="system", walkthrough="n/a",
                                           candidates="n/a", doors="n/a", rulings="declined",
                                           changed="x")
        with self.assertRaises(runlog.RunLogRefused):
            runlog.append_run(DOC, block)

    def test_a_run_log_section_is_created_when_absent(self):
        doc = "# W %s architecture (2026-09-21)\n\nScope doc: a\n" % D
        block = templates.render_run_block(1, "2026-09-21", "first run", exit_ramp="no system",
                                           walkthrough="n/a %s exit ramp" % D, candidates="n/a", doors="n/a",
                                           rulings="declined", changed="first run")
        out = runlog.append_run(doc, block)
        self.assertIn("\n## Run log\n### Run 1 ", out)


class Strike(unittest.TestCase):

    def test_a_list_line_is_struck_inside_its_marker(self):
        line = "- storage %s none %s nothing is remembered" % (D, D)
        self.assertEqual(runlog.strike(line), "- ~~storage %s none %s nothing is remembered~~" % (D, D))

    def test_a_struck_line_stays_struck(self):
        once = runlog.strike("- a")
        self.assertEqual(runlog.strike(once), once)

    def test_strike_in_a_document_keeps_every_other_byte(self):
        target = "- storage %s none %s nothing is remembered" % (D, D)
        out = runlog.strike_in(DOC, target)
        self.assertEqual(out.replace("- ~~storage %s none %s nothing is remembered~~" % (D, D), target), DOC)
        self.assertEqual(runlog.losses(DOC, out), [])

    def test_strike_of_a_line_that_is_not_there_is_refused(self):
        with self.assertRaises(runlog.RunLogRefused):
            runlog.strike_in(DOC, "- not in the doc")


class Losses(unittest.TestCase):

    def test_a_dropped_run_block_is_a_loss(self):
        dropped = DOC.split("### Run 3")[0]
        found = runlog.losses(DOC, dropped)
        self.assertTrue(any("Run 3" in f for f in found), found)

    def test_an_edited_run_block_is_a_loss(self):
        edited = DOC.replace("Changed this run: storage reconsidered", "Changed this run: nothing")
        self.assertTrue(runlog.losses(DOC, edited))

    def test_a_deleted_poured_concrete_line_is_a_loss(self):
        deleted = DOC.replace("- storage %s none %s nothing is remembered\n" % (D, D), "")
        found = runlog.losses(DOC, deleted)
        self.assertTrue(any("storage" in f for f in found), found)

    def test_check_refuses_before_anything_is_written(self):
        with self.assertRaises(runlog.RunLogRefused):
            runlog.check_no_loss(DOC, DOC.split("## Run log")[0])


if __name__ == "__main__":
    unittest.main()
