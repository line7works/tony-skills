"""punch-F1: the source pin misses a restored deletion and a mode-bit change (E13 punch list).

Astra's recheck of the full-fix round left F1 (BLOCKER) partly closed: "Stricter probes restore a
deleted tracked file or change an executable bit after the kill: identity changes, but resume
prints `completed`, `card.after: built`, `card.moved: true`."

The pin kept one content digest per changed or untracked path and used `None` both for "this path
is deleted" and for "this path is not in the set", so a tracked file deleted before the decision
and restored after the kill compared equal; and the digest carried no mode, so an executable bit
turned on or off on a path whose bytes did not change compared equal too.

Each shape below runs through the real `build.py` in front of the real records component, the
kill and the in-flight change injected by the stand-in `records.py` of `shimlib.py`. Beyond her
two instances this module covers: the exec bit off as well as on, a path deleted before the
decision and re-created with the same bytes but another mode, a file replaced by a symlink, a
file replaced by a directory, a tracked-and-unchanged file whose exec bit flips, the same
restored deletion and mode flip landing while the append is in flight (no kill), and the controls
(an unchanged resume still completes once).
"""
import os
import shutil
import stat
import unittest

import shimlib
import testlib
from test_transaction import _Transaction, card_sets

testlib.add_scripts_to_path()

WIDGET = "src/widget.py"
OTHER = "src/other.py"
HEAD_BYTES = "def spin():\n    return 0\n"


def chmod_x(path, on):
    mode = os.stat(path).st_mode
    os.chmod(path, (mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) if on
             else (mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)))


class _Punch(_Transaction):

    def path(self, rel):
        return os.path.join(self.ws, rel)

    def kill_after_append(self):
        shimlib.fault(self.fault, command="append", kind="card_set", action="kill_after")
        self.assertNotEqual(self.report()[0], 10, "the first pass is killed after its append")
        self.assertEqual(len(card_sets(self.events(), "A")), 1)
        shimlib.disarm(self.fault)

    def assert_source_changed(self, moved_path, appended=1):
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual((result["status"], result.get("stop_tag")), ("stopped", "source_changed"),
                         "%s\n%s" % (result.get("reason") or result.get("stop_reason"), out))
        self.assertFalse(result["card"]["moved"])
        self.assertNotEqual(result["card"]["after"], "built")
        self.assertEqual(self.status_line(), "not started", "the `Status:` line was not written")
        self.assertIn(moved_path, result.get("source_moved") or [], "the moved path is named")
        self.assertEqual(len(card_sets(self.events(), "A")), appended, "never a second append")
        if appended:
            self.assertEqual(len(result["records"]["appended"]), 1, "the landed append is kept")
            self.assertTrue(self.receipt()["card_append"].get("head"))
        return result


class PunchF1RestoredDeletion(_Punch):
    """Her first stricter probe: a tracked file deleted when the decision was made, restored
    after the kill."""

    def test_a_deletion_restored_after_the_kill_stops(self):
        os.remove(self.path(WIDGET))
        self.to_report()
        self.kill_after_append()
        testlib.write_text(self.path(WIDGET), HEAD_BYTES)
        self.assert_source_changed(WIDGET)
        self.assert_source_changed(WIDGET)          # a second resume says the same, writes nothing

    def test_a_deletion_re_created_with_the_same_bytes_and_another_mode_stops(self):
        os.remove(self.path(WIDGET))
        self.to_report()
        self.kill_after_append()
        testlib.write_text(self.path(WIDGET), HEAD_BYTES)
        chmod_x(self.path(WIDGET), True)
        self.assert_source_changed(WIDGET)


class PunchF1ModeBit(_Punch):
    """Her second stricter probe: an executable bit changed after the kill."""

    def test_exec_bit_on_after_the_kill_stops(self):
        testlib.write_text(self.path(WIDGET), "def spin():\n    return 1\n")
        self.to_report()
        self.kill_after_append()
        chmod_x(self.path(WIDGET), True)
        self.assert_source_changed(WIDGET)

    def test_exec_bit_off_after_the_kill_stops(self):
        testlib.write_text(self.path(WIDGET), "def spin():\n    return 1\n")
        chmod_x(self.path(WIDGET), True)
        self.to_report()
        self.kill_after_append()
        chmod_x(self.path(WIDGET), False)
        self.assert_source_changed(WIDGET)

    def test_exec_bit_on_an_untracked_file_after_the_kill_stops(self):
        testlib.write_text(self.path(WIDGET), "def spin():\n    return 1\n")
        testlib.write_text(self.path("src/helper.py"), "H = 1\n")
        answer = dict(testlib.ANSWER)
        answer["edits"] = list(answer["edits"]) + [{"path": "src/helper.py",
                                                    "reason": "a helper the spin needs"}]
        testlib.write_json(self.answer, answer)
        self.to_report()
        self.kill_after_append()
        chmod_x(self.path("src/helper.py"), True)
        self.assert_source_changed("src/helper.py")

    def test_exec_bit_on_a_tracked_unchanged_file_after_the_kill_stops(self):
        self.to_report()
        self.kill_after_append()
        chmod_x(self.path(OTHER), True)
        self.assert_source_changed(OTHER)


class PunchF1TypeChange(_Punch):
    """Type changes on a pinned path: file to symlink, file to directory."""

    def test_a_file_replaced_by_a_symlink_to_the_same_bytes_stops(self):
        testlib.write_text(self.path(WIDGET), "def spin():\n    return 1\n")
        self.to_report()
        self.kill_after_append()
        twin = self.path("src/twin.txt")
        shutil.copyfile(self.path(WIDGET), twin)
        os.remove(self.path(WIDGET))
        os.symlink("twin.txt", self.path(WIDGET))
        self.assert_source_changed(WIDGET)

    def test_a_file_replaced_by_a_directory_stops(self):
        testlib.write_text(self.path(WIDGET), "def spin():\n    return 1\n")
        self.to_report()
        self.kill_after_append()
        os.remove(self.path(WIDGET))
        os.makedirs(self.path(WIDGET))
        testlib.write_text(os.path.join(self.path(WIDGET), "inner.py"), "X = 1\n")
        self.assert_source_changed(WIDGET)


class PunchF1InFlight(_Punch):
    """The same two shapes landing while the append is in flight, no kill."""

    def test_a_deletion_restored_during_the_append_stops(self):
        os.remove(self.path(WIDGET))
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="write",
                      path=self.path(WIDGET), text=HEAD_BYTES)
        self.assert_source_changed(WIDGET)

    def test_an_exec_bit_changed_during_the_append_stops(self):
        testlib.write_text(self.path(WIDGET), "def spin():\n    return 1\n")
        self.to_report()
        shimlib.fault(self.fault, command="append", kind="card_set", action="chmod",
                      path=self.path(WIDGET), mode="755")
        self.assert_source_changed(WIDGET)


class PunchF1Controls(_Punch):
    """Controls: an unchanged resume completes once, with a deletion or a mode change that was
    already there when the decision was made."""

    def _completes(self):
        code, out, err = self.report()
        self.assertEqual(code, 10, err)
        result = self.result()
        self.assertEqual(result["status"], "completed", out)
        self.assertEqual(len(card_sets(self.events(), "A")), 1)
        self.assertEqual(self.status_line(), "built")

    def test_a_standing_deletion_resumes_to_completed(self):
        os.remove(self.path(WIDGET))
        self.to_report()
        self.kill_after_append()
        self._completes()

    def test_a_standing_exec_bit_resumes_to_completed(self):
        testlib.write_text(self.path(WIDGET), "def spin():\n    return 1\n")
        chmod_x(self.path(WIDGET), True)
        self.to_report()
        self.kill_after_append()
        self._completes()


if __name__ == "__main__":
    unittest.main()
