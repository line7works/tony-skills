"""E13 full review, Astra's F1 (BLOCKER): build settled an obsolete scope decision.

Her `probe_recovery_source.py` killed `report` after its real `card_set` append, added
`src/late.py`, and resumed: `exit 10 / completed / card.moved true / out_of_scope []`, with
`?? src/late.py` in `git status`. Her `probe_windows.py` did the same without a kill, adding the
file while the append was in flight. Recovery kept the old scope decision and guarded only the
document.

The source state is now pinned with the build decision and verified before the append, before
the document half, and at the start of every recovery pass. Only this transaction's receipted
document change is permitted. Other source that moved is the named stop `source_changed`, which
publishes the current changed paths (out-of-scope ones included), preserves any landed append and
its receipt, and never advances the card, rewrites the baseline, reruns a check or appends twice.

Every shape runs through the real CLI in front of the real component, the faults injected by the
stand-in `records.py` of `shimlib.py`. Written red first; the red output is kept in the fix
round's scratch folder.
"""
import json
import os
import unittest

import shimlib
import testlib
from test_transaction import _Transaction, card_sets

testlib.add_scripts_to_path()

LATE = "src/late.py"


class _F1(_Transaction):

    def add_late(self):
        testlib.write_text(os.path.join(self.ws, LATE), "LATE = True\n")

    def assert_source_changed(self, appended):
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "stopped", out)
        self.assertEqual(result["stop_tag"], "source_changed", result.get("stop_reason"))
        self.assertFalse(result["card"]["moved"])
        self.assertEqual(result["card"]["after"], "not started")
        self.assertEqual(self.status_line(), "not started", "the `Status:` line was not written")
        self.assertIn(LATE, result.get("source_moved") or [], "the moved path is published")
        self.assertIn(LATE, result["source_set"]["untracked"], "the source set is the current one")
        self.assertIn(LATE, [row["path"] for row in result["out_of_scope"]],
                      "the out-of-scope late path is published too")
        self.assertEqual(len(card_sets(self.events(), "A")), appended, "never a second append")
        if appended:
            self.assertEqual(len(result["records"]["appended"]), 1, "the landed append is reported")
            self.assertTrue(result["records"]["wrote"])
            self.assertTrue(self.receipt()["card_append"].get("head"),
                            "the landed append's outcome is kept in the receipt")
        else:
            self.assertEqual(result["records"]["appended"], [])
        self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "receipt.json")))
        self.assertNotIn("validation", json.loads(out), "the stop validates")
        return result


class F1ALateFileAfterAKilledAppend(_F1):
    """F1, `probe_recovery_source.py`: killed after the real append, a new untracked file, resume."""

    def test_the_resume_stops_source_changed_and_keeps_the_one_event(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10)
        self.assertEqual(len(card_sets(self.events(), "A")), 1)
        shimlib.disarm(self.fault)
        self.add_late()
        self.assert_source_changed(appended=1)
        # a second resume says the same and writes nothing more
        self.assert_source_changed(appended=1)


class F1BLateFileDuringTheAppend(_F1):
    """F1, `probe_windows.py`: the file lands while the append is in flight, no kill."""

    def test_the_first_pass_stops_before_the_document_half(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="mutate",
                      path=os.path.join(self.ws, LATE), text="LATE = True\n")
        self.assert_source_changed(appended=1)
        shimlib.disarm(self.fault)
        self.assert_source_changed(appended=1)


class F1CLateFileAfterAKillBeforeTheAppend(_F1):
    """F1: killed before the append, a new file, resume. A stale decision is never appended."""

    def test_the_resume_appends_nothing(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_before")
        self.assertNotEqual(self.report()[0], 10)
        shimlib.disarm(self.fault)
        self.add_late()
        self.assert_source_changed(appended=0)


class F1DControls(_F1):
    """F1 controls: unchanged source still settles; a document-only edit is still `outside_edit`;
    a tracked source edit after a kill is `source_changed` too."""

    def test_an_unchanged_resume_completes_with_one_event(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10)
        shimlib.disarm(self.fault)
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        self.assertEqual(self.result()["status"], "completed", out)
        self.assertEqual(len(card_sets(self.events(), "A")), 1)
        self.assertEqual(self.status_line(), "built")

    def test_a_document_edit_alone_is_outside_edit(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="mutate",
                      path=os.path.join(self.ws, testlib.DOC_PATH), text="\nan edit\n")
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        self.assertEqual(self.result()["stop_tag"], "outside_edit", out)

    def test_a_tracked_edit_after_a_kill(self):
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10)
        shimlib.disarm(self.fault)
        testlib.write_text(os.path.join(self.ws, "src", "other.py"), "VALUE = 2\n")
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["stop_tag"], "source_changed", out)
        self.assertIn("src/other.py", result["source_moved"])
        self.assertEqual(self.status_line(), "not started")


if __name__ == "__main__":
    unittest.main()
