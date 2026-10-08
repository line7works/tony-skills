"""The E15 lane contract A29 (1): every save of the run's state and its checkpoint is crash-safe (Astra's look 6, L6-1).

L6-1's smallest case: one slice with one open MAJOR, a ship pause answered with a waiver, and the process killed after
`ship.json` is replaced and before its new hash and stage reach `checkpoint.json`. Before A29 every later command
refused the run as "changed by hand" and it could never reach a terminal status. Now the next command finishes the
interrupted save (the bytes it finds are the ones this run was saving) and the run goes on to its end with nothing
written twice, and vertical-v2's real gate reads the waived slice as before. A hand edit still refuses: of `ship.json`
after a clean save, and of any file an interrupted save names, before the next command finishes it.

The kill is a real SIGKILL on a PID the test starts, stopped by `killpoint.py` at the line right after the routine that
writes `ship.json` returns (the write found by its file name, so the same test ran red on the code before A29).
"""
import json
import os
import shutil
import unittest

import cr25lib
import killlib
import slib
import testlib
from test_card_with_grant import ours, status_of


def phase(run_dir):
    return testlib.load_json(os.path.join(run_dir, "checkpoint.json"))["phase"]


def run_files(run_dir):
    out = {}
    for name in sorted(os.listdir(run_dir)):
        path = os.path.join(run_dir, name)
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                out[name] = fh.read()
    return out


def waived_run(test, tmp, name):
    """A run at `paused` (ship's own waive-or-hold question on the open MAJOR) and the owner's waiver file."""
    run = cr25lib.Run(test, tmp, name)
    run.build()
    run.signoff()
    code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--question", slib.question_file(
        run.tmp, run.run_dir, "Only you can rule this finding: waive it or hold?", source="ship", station=None,
        finding=run.findings[0], name="q-l6.json")])
    test.assertEqual(code, 0, (out, err))
    answer = slib.answer_file(run.tmp, run.run_dir, out["pause"], "Waive this MAJOR.",
                              {"kind": "waive", "finding": run.findings[0]}, name="a-l6.json")
    return run, answer


def kill_between_state_and_checkpoint(test, run, args):
    """`args` run once under the tracer to find the write of `ship.json` that a write of `checkpoint.json` follows,
    then, on the same run directory restored, killed at the line right after that write returns."""
    keep = os.path.join(os.path.dirname(run.tmp), os.path.basename(run.tmp) + "-keep")
    shutil.copytree(run.tmp, keep, symlinks=True)
    case = killlib.Case.__new__(killlib.Case)
    case.dir, case.drive = run.tmp, run.drive
    code, seen = killlib.recorded(case, args, os.path.join(os.path.dirname(run.tmp), "record-l6.json"))
    writes = seen["writes"]
    at = None
    for index, row in enumerate(writes):
        if row.get("path") == "ship.json" and any(w.get("path") == "checkpoint.json" for w in writes[index + 1:]):
            at = row["return"]
    test.assertIsNotNone(at, "a write of ship.json followed by a write of checkpoint.json: %s" % writes)
    testlib.rmtree(run.tmp)
    shutil.copytree(keep, run.tmp, symlinks=True)
    testlib.rmtree(keep)
    test.assertTrue(killlib.killed_at(case, args, at, os.path.join(os.path.dirname(run.tmp), "stop-l6.json")),
                    "the command was stopped at line %d and killed there" % at)
    return at


@unittest.skipUnless(slib.usable() and cr25lib.vertical_skill() is not None,
                     "needs jsonschema, the records component, the three stations and vertical-v2 beside this core")
class L6_1_AKillInsideTheSave(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-l6-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def test_the_waiver_killed_between_the_state_and_the_checkpoint_reaches_a_terminal_status(self):
        run, answer = waived_run(self, self.tmp, "l6")
        args = ["pause", "--run-dir", run.run_dir, "--answer", answer]
        kill_between_state_and_checkpoint(self, run, args)
        self.assertEqual(status_of(run.ws), "Status: signed off", "the grant's Status: line landed before the kill")
        events = ours(run.ws)
        self.assertEqual([e["kind"] for e in events], ["waived", "card_set"])
        code, out, err = run.drive(args)
        self.assertIn(code, (0, 2), (out, err))
        if code == 2:
            self.assertIn("run `fix` instead", err, "the interrupted save was finished: the run is at `fixing`")
        self.assertEqual(phase(run.run_dir), "fixing")
        code, out, err = run.drive(args)
        self.assertEqual(code, 2, "a second answer is out of turn")
        self.assertEqual(ours(run.ws), events, "no event appended twice")
        recorded = testlib.load_json(os.path.join(run.run_dir, "events.json"))
        self.assertEqual([e["kind"] for e in recorded["events"]], ["waived", "card_set"], "recorded once")
        self.assertEqual(len(recorded["grants"]), 1)
        pauses = testlib.load_json(os.path.join(run.run_dir, "pauses.json"))["pauses"]
        self.assertEqual([p["answer"]["words"] for p in pauses], ["Waive this MAJOR."])
        code, out, err = run.drive(["fix", "--run-dir", run.run_dir, "--fixes", slib.fixes_file(
            run.tmp, run.run_dir, 1, [], name="fixes-l6.json")])
        self.assertEqual((code, out.get("next")), (0, "visit --station recheck-v2"), (out, err))
        self.assertEqual(run.recheck("nothing_open")["next"], "report")
        out = run.end()
        self.assertEqual(out["status"], "completed", out)
        self.assertEqual(ours(run.ws), events, "no event appended twice")
        lines = slib.trace(run.run_dir)
        self.assertEqual([(l["expected"], l["status"]) for l in lines],
                         [("build-v2", "visiting"), ("build-v2", "completed"), ("signoff-v2", "visiting"),
                          ("signoff-v2", "completed"), ("recheck-v2", "visiting"), ("recheck-v2", "nothing_open")],
                         "no trace line written twice")
        self.assertEqual(sorted(n for n in os.listdir(run.run_dir) if n.startswith(".")), [],
                         "no temporary file or journal left behind")
        self.assertEqual(slib.validate_trace(run.run_dir)[0], 0)
        slib.commit_all(run.ws, "after the interrupted waiver")
        code, gate = cr25lib.vertical_gate(run.tmp, run.ws, "vertical-after-l6")
        self.assertEqual((code, (gate or {}).get("next")), (0, "ask"), "vertical-v2 passes the waived slice: %s" % gate)

    def test_a_hand_edit_of_the_state_after_a_clean_save_still_refuses(self):
        run, answer = waived_run(self, self.tmp, "hand")
        path = os.path.join(run.run_dir, "ship.json")
        doc = testlib.load_json(path)
        doc["lap"] = 0
        testlib.write_json(path, doc)
        before = run_files(run.run_dir)
        code, out, err = run.drive(["pause", "--run-dir", run.run_dir, "--answer", answer])
        self.assertEqual(code, 1, (out, err))
        self.assertIn("changed by hand", err)
        self.assertEqual(run_files(run.run_dir), before, "nothing written")
        self.assertEqual([e["kind"] for e in ours(run.ws)], [], "no event")

    def test_a_hand_edit_of_the_state_an_interrupted_save_was_writing_refuses(self):
        run, answer = waived_run(self, self.tmp, "hand-cut")
        args = ["pause", "--run-dir", run.run_dir, "--answer", answer]
        kill_between_state_and_checkpoint(self, run, args)
        path = os.path.join(run.run_dir, "ship.json")
        doc = testlib.load_json(path)
        doc["lap"] = 2
        testlib.write_json(path, doc)
        before = run_files(run.run_dir)
        for attempt in range(2):
            code, out, err = run.drive(args)
            self.assertEqual(code, 1, (out, err))
            self.assertIn("changed by hand", err)
        self.assertEqual(run_files(run.run_dir), before, "nothing written, nothing finished over the hand edit")
        self.assertEqual(phase(run.run_dir), "paused")

    def test_a_hand_edit_of_another_file_the_interrupted_save_names_refuses(self):
        run, answer = waived_run(self, self.tmp, "hand-pauses")
        args = ["pause", "--run-dir", run.run_dir, "--answer", answer]
        kill_between_state_and_checkpoint(self, run, args)
        path = os.path.join(run.run_dir, "pauses.json")
        doc = testlib.load_json(path)
        doc["pauses"][0]["question"]["text"] = "a different question"
        testlib.write_json(path, doc)
        before = run_files(run.run_dir)
        code, out, err = run.drive(args)
        self.assertEqual(code, 1, (out, err))
        self.assertIn("changed by hand", err)
        self.assertEqual(run_files(run.run_dir), before)


@unittest.skipUnless(slib.jsonschema_here(), "needs jsonschema")
class TheSaveRoutine(unittest.TestCase):
    """The routine itself, through its own functions (`common.save`, `common.recover`)."""

    def setUp(self):
        self.tmp = testlib.make_scratch("ship-save-")
        self.addCleanup(testlib.rmtree, self.tmp)
        testlib.add_scripts_to_path()

    def test_a_trace_line_the_save_writes_is_the_bytes_trace_append_writes(self):
        from back_core import trace
        from ship_core import common
        line = trace.line(kind="visit", caller="ship-v2", expected="build-v2",
                          identity={"name": "build-v2", "version": "0.1.0", "root": "/plugins/build-v2",
                                    "interface_version": 1, "commit": None, "content_sha256": None},
                          route="3a", run_dir=os.path.join(self.tmp, "a", "visits", "0-build-v2"), status="visiting",
                          at=slib.NOW)
        one, two = os.path.join(self.tmp, "a"), os.path.join(self.tmp, "b")
        os.makedirs(one)
        os.makedirs(two)
        trace.append(one, line)
        trace.append(one, dict(line, status="completed"))
        numbered = common.trace_bytes(two, [line, dict(line, status="completed")])
        with open(trace.path_of(one), "rb") as fh:
            self.assertEqual(fh.read(), numbered)

    def test_a_journal_whose_own_hash_does_not_hold_refuses(self):
        from ship_core import common
        from station_core import driver
        run = self._run()
        common.save(run, {"lap": 1}, "selected")
        journal = os.path.join(run.run_dir, common.JOURNAL)
        body = {"journal_version": 1, "run_id": "run", "writes": [], "sha256": "0" * 64}
        with open(journal, "w", encoding="utf-8") as fh:
            json.dump(body, fh)
        with self.assertRaises(driver.Defect) as caught:
            common.recover(run)
        self.assertIn("changed by hand", str(caught.exception))
        self.assertTrue(os.path.exists(journal), "nothing removed")

    def test_a_leftover_temporary_file_of_a_cut_off_write_is_removed(self):
        from ship_core import common
        run = self._run()
        common.save(run, {"lap": 1}, "selected")
        stray = os.path.join(run.run_dir, ".ship.json" + common.TEMP)
        with open(stray, "w") as fh:
            fh.write("half")
        common.recover(run)
        self.assertFalse(os.path.exists(stray))
        self.assertEqual(common.state(run), {"lap": 1})

    def _run(self):
        from station_core import driver
        run_dir = os.path.join(self.tmp, "run")
        doc = testlib.make_input(self.tmp, run_dir)
        doc["run_id"] = "run"
        return driver.Run.create(run_dir, doc)


if __name__ == "__main__":
    unittest.main()
