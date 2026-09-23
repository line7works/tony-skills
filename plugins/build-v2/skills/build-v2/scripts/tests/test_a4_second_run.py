"""A second build run on one document is clean (E13 amendment A4, owner-ruled "Option A").

Before A4 the records component re-imported a `Status:` line this station had written as a fresh
`card_observed`: the station moved a card, wrote the line, and the next run's levelling read that
line back as news. A4 makes the importer recognise a line the log already records natively —
`render`'s own record lines, and a `Status:` line whose text equals the last card a native
`card_set` or `card_observed` holds for the slice — count it under `native_rendered`, and import
nothing for it.

What this suite holds, each against the real CLI and the real component:

1. **The second run.** Run 1 completes and moves the card; run 2 on the same document levels with
   `would_import` 0 and `native_rendered` at least 1, reads the card where run 1 left it, appends
   no `card_observed` for run 1's line, and proceeds.
2. **Drift detection still works**, and a hand edit is still absorbed. These are the control: A4
   must not have bought the clean second run at the price of the split state going unnoticed.
3. **A build after a signoff on the same document**, which is the loop's real order: a review
   block rendered by the component, placed in the document, is recognised rather than re-imported,
   and its open BLOCKER refuses the run unless the input allows it.

The first test is run RED against the component as it stood before A4, extracted read-only from
history with `git archive` (`testlib.pre_a4_component`), so "A4 is what makes this pass" is
measured here rather than asserted.
"""
import json
import os
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()

LOG = "docs/records/docs__plans__2026-09-20-widget.events.jsonl"


def events_of(workspace):
    path = os.path.join(workspace, LOG)
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh.read().split("\n") if line.strip()]


def kinds(workspace, kind, slice_name=None):
    return [e for e in events_of(workspace)
            if e.get("kind") == kind and (slice_name is None or e.get("slice") == slice_name)]


class _TwoRuns(unittest.TestCase):

    def setUp(self):
        self.scratch = testlib.make_scratch("build-v2-a4-")
        self.addCleanup(testlib.rmtree, self.scratch)
        self.ws = testlib.make_workspace(self.scratch)
        self.answer = os.path.join(self.scratch, "answer.json")
        testlib.write_json(self.answer, testlib.ANSWER)

    def run_build_fully(self, run_id, env=None, **extra):
        """Every phase of one run; returns (last exit code, the result or None)."""
        run_dir = os.path.join(self.scratch, run_id)
        path = os.path.join(self.scratch, "input-%s.json" % run_id)
        testlib.write_json(path, testlib.make_input(run_dir, self.ws, run_id=run_id, **extra))
        code = 0
        for args in (["check-input", path], ["contract", "--run-dir", run_dir],
                     ["preflight", "--run-dir", run_dir],
                     ["record-answer", "--run-dir", run_dir, "--answer", self.answer],
                     ["report", "--run-dir", run_dir]):
            code, out, err = testlib.run_build(args, env=env)
            if code != 0:
                break
        result_path = os.path.join(run_dir, "result.json")
        return code, (testlib.load_json(result_path) if os.path.isfile(result_path) else None)

    def preflight_only(self, run_id, env=None, **extra):
        """check-input, contract, preflight; returns (code, stdout document or None, result)."""
        run_dir = os.path.join(self.scratch, run_id)
        path = os.path.join(self.scratch, "input-%s.json" % run_id)
        testlib.write_json(path, testlib.make_input(run_dir, self.ws, run_id=run_id, **extra))
        document = None
        code = 0
        for args in (["check-input", path], ["contract", "--run-dir", run_dir],
                     ["preflight", "--run-dir", run_dir]):
            code, out, err = testlib.run_build(args, env=env)
            document = json.loads(out) if out.strip() else None
            if code != 0:
                break
        result_path = os.path.join(run_dir, "result.json")
        return code, document, (testlib.load_json(result_path) if os.path.isfile(result_path) else None)

    def status_line(self):
        with open(os.path.join(self.ws, testlib.DOC_PATH), encoding="utf-8") as fh:
            for line in fh.read().split("\n"):
                if line.startswith("Status:"):
                    return line[len("Status:"):].strip()
        return None

    def set_status_by_hand(self, value):
        """Edit the `Status:` line the way a person would, by hand, outside any station.

        The current value is read BEFORE the file is opened for writing: `open(path, "w")`
        truncates at once, so reading it inside that block would read an empty file. (It did, in
        the first draft of this helper, and the edit silently did nothing.)
        """
        current = self.status_line()
        path = os.path.join(self.ws, testlib.DOC_PATH)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        replaced = text.replace("Status: %s" % current, "Status: %s" % value)
        self.assertNotEqual(replaced, text, "the hand edit changed nothing")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(replaced)
        self.assertEqual(self.status_line(), value)


class TheSecondRunOnOneDocument(_TwoRuns):
    """Run 1 moves the card; run 2 finds nothing to import for the line run 1 wrote."""

    def test_run_one_completes_and_run_two_levels_with_nothing_to_import(self):
        code, result = self.run_build_fully("run-1")
        self.assertEqual(code, 10)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["card"]["moved"])
        self.assertEqual(self.status_line(), "built")
        observed_before = len(kinds(self.ws, "card_observed", "A"))

        code, document, result2 = self.preflight_only("run-2")
        self.assertEqual(code, 0, "run 2 proceeds")
        levelled = document["records"]["levelled"]
        self.assertEqual(levelled["would_import"], 0,
                         "the `Status:` line run 1 wrote is not news to the log that recorded it")
        self.assertGreaterEqual(levelled["native_rendered"], 1,
                                "and the component says it recognised it")
        self.assertEqual(levelled["imported"], 0)
        self.assertEqual(document["card"], "built", "run 2 reads the card run 1 left")
        self.assertEqual(len(kinds(self.ws, "card_observed", "A")), observed_before,
                         "no phantom card_observed was appended for run 1's own line")

    def test_only_one_card_set_exists_after_both_runs(self):
        self.assertEqual(self.run_build_fully("run-1")[0], 10)
        self.assertEqual(self.preflight_only("run-2")[0], 0)
        self.assertEqual(len(kinds(self.ws, "card_set", "A")), 1)

    def test_the_second_run_can_complete_too(self):
        """The card is already `built`, so the second run's move is a no-op the core still records
        honestly: it does not stop, and it does not append a second event for an unchanged card."""
        self.assertEqual(self.run_build_fully("run-1")[0], 10)
        code, result = self.run_build_fully("run-2")
        self.assertEqual(code, 10, "the second run reaches a terminal status")
        self.assertIsNotNone(result)
        self.assertEqual(self.status_line(), "built")


class TheSameRunAgainstThePreA4Component(_TwoRuns):
    """The red: without A4 the second run's levelling DOES find the line to be news."""

    def setUp(self):
        _TwoRuns.setUp(self)
        self.as_extracted = testlib.pre_a4_component(self.scratch)
        if self.as_extracted is None:
            self.skipTest("the pre-A4 component could not be extracted from history")
        self.pre_a4 = self.relabelled(self.as_extracted)
        self.pre_env = testlib.base_env({"RECORDS_ROOT": self.pre_a4})

    def relabelled(self, root):
        """The pre-A4 component, relabelled to speak the interface version this station knows.

        E13 amendment A7 (Astra's F10) moved the records interface to version 2 and this station's
        client with it, so the component as it stood before A4, which says version 1, is refused
        at the confirm step (exit 3) before any run begins; the test below proves that on the real
        extracted component. The red this class exists for is about BEHAVIOUR (what the old
        importer does with a line this station wrote), so it is measured on a copy whose one
        `INTERFACE_VERSION` line says what the station expects and whose every other byte is the
        old component's. The copy is made in this test's scratch directory; history is untouched.
        """
        import re
        import shutil
        copy = os.path.join(self.scratch, "records-pre-a4-relabelled")
        shutil.copytree(root, copy)
        script = os.path.join(copy, "scripts", "records.py")
        with open(script, encoding="utf-8") as fh:
            text = fh.read()
        changed = re.sub(r"\nINTERFACE_VERSION = \d+\n", "\nINTERFACE_VERSION = 2\n", text, count=1)
        self.assertNotEqual(changed, text, "the old component's INTERFACE_VERSION line moved")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(changed)
        return copy

    def test_the_pre_a4_component_as_it_stands_is_refused_at_version_1(self):
        """F10 (E13 amendment A7): this station speaks records interface version 2; the real
        component from before A4 says 1, and the station refuses it, exit 3, and says so."""
        code, out, err = testlib.run_build(["skill-identity", "--records-root", self.as_extracted])
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertIn("speaks interface version 1, not 2", err)

    def test_the_pre_a4_component_does_not_even_have_the_field(self):
        with open(os.path.join(self.pre_a4, "scripts", "records_core", "importer.py"),
                  encoding="utf-8") as fh:
            self.assertNotIn("native_rendered", fh.read())

    def test_without_a4_the_line_this_station_wrote_comes_back_as_news(self):
        code, result = self.run_build_fully("run-1", env=self.pre_env)
        self.assertEqual(code, 10, "run 1 still completes against the old component")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(self.status_line(), "built")

        code, document, _ = self.preflight_only("run-2", env=self.pre_env)
        self.assertEqual(code, 0)
        levelled = document["records"]["levelled"]
        self.assertGreater(levelled["would_import"], 0,
                           "this is the state A4 fixed: the old component reads run 1's own "
                           "`Status:` line back as something to import")
        self.assertIsNone(levelled["native_rendered"],
                          "and it has no notion of a line the log already records natively")


class DriftDetectionStillWorks(_TwoRuns):
    """The control. A4 must not buy the clean second run at the price of missing a split state."""

    def _kill_after_the_append(self):
        import shimlib
        shim_root, fault = shimlib.make_shim(self.scratch, testlib.RECORDS_ROOT)
        env = testlib.base_env(shimlib.env(shim_root, testlib.RECORDS_ROOT, fault))
        run_dir = os.path.join(self.scratch, "run-1")
        path = os.path.join(self.scratch, "input-run-1.json")
        testlib.write_json(path, testlib.make_input(run_dir, self.ws, run_id="run-1"))
        for args in (["check-input", path], ["contract", "--run-dir", run_dir],
                     ["preflight", "--run-dir", run_dir],
                     ["record-answer", "--run-dir", run_dir, "--answer", self.answer]):
            self.assertEqual(testlib.run_build(args, env=env)[0], 0, args)
        shimlib.fault(fault, command="append", kind="card_set", action="kill_after")
        testlib.run_build(["report", "--run-dir", run_dir], env=env)
        shimlib.disarm(fault)
        return env

    def test_a_card_event_whose_document_write_never_landed_is_still_drift(self):
        env = self._kill_after_the_append()
        self.assertEqual(len(kinds(self.ws, "card_set", "A")), 1, "the event landed")
        self.assertEqual(self.status_line(), "not started", "the line did not")

        code, _, result = self.preflight_only("run-2", env=env)
        self.assertEqual(code, 10, "run 2 stops")
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "card_drift")
        self.assertIn("'built'", result["stop_reason"])
        self.assertIn("'not started'", result["stop_reason"])
        self.assertEqual(self.status_line(), "not started", "and repairs nothing")

    def test_a_hand_edit_to_another_value_is_absorbed_and_never_native_rendered(self):
        self.assertEqual(self.run_build_fully("run-1")[0], 10)
        self.set_status_by_hand("signed off")

        code, document, _ = self.preflight_only("run-2")
        self.assertEqual(code, 0, "a hand edit is an observation, not a stop")
        levelled = document["records"]["levelled"]
        self.assertGreater(levelled["would_import"], 0,
                           "a value no native event wrote is news")
        self.assertEqual(levelled["native_rendered"], 0,
                         "and it is never counted as a line the log already records")
        self.assertEqual(document["card"], "signed off", "the card reads what the document says")

    def test_a_hand_edit_back_to_the_value_the_move_started_from_is_drift(self):
        """Indistinguishable by content from a write that never landed, and reported as such:
        the document contradicts the last recorded move, so a person decides."""
        self.assertEqual(self.run_build_fully("run-1")[0], 10)
        self.set_status_by_hand("not started")
        code, _, result = self.preflight_only("run-2")
        self.assertEqual(code, 10)
        self.assertEqual(result["stop_tag"], "card_drift")


class ABuildAfterASignoffOnTheSameDocument(_TwoRuns):
    """The loop's real order: signoff raises findings and renders its block into the document,
    then build runs. The rendered block is recognised, not re-imported, and its open BLOCKER
    refuses the run."""

    def _signoff_raises_and_renders(self, severity="BLOCKER"):
        """Raise a finding through the component and place `render`'s own text in the document."""
        records = os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py")

        def run(args):
            proc = subprocess.run([testlib.GEN_PYTHON, records] + args, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=testlib.base_env())
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
            return json.loads(proc.stdout.decode("utf-8"))

        head = run(["verify", "--workspace", self.ws, "--doc", testlib.DOC_PATH])["head"]
        events = os.path.join(self.scratch, "review.json")
        testlib.write_json(events, [{
            "v": 1, "at": "2026-09-22T09:00:00Z", "ledger_doc": testlib.DOC_PATH,
            "actor": {"station": "signoff-v2", "run_id": "review-1", "harness": "test-harness"},
            "origin": {"kind": "native"}, "source": {"known": False},
            "kind": "finding_raised", "slice": "A", "severity": severity,
            "location": {"raw": "src/widget.py:2", "file": "src/widget.py", "line": 2,
                         "line_end": None, "tag": None, "more": [], "resolved": True},
            "claim": "spin() counts the wrong number of turns",
            "scenario": "spin() answers 0 after one turn", "raised_by": "A"}])
        run(["append", "--workspace", self.ws, "--doc", testlib.DOC_PATH,
             "--events", events, "--expect-head", head])
        rendered = run(["render", "--workspace", self.ws, "--doc", testlib.DOC_PATH,
                        "--run-id", "review-1"])
        self.assertTrue(rendered["text"].strip(), "the component rendered a review block")

        path = os.path.join(self.ws, testlib.DOC_PATH)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.rstrip("\n") + "\n" + rendered["text"])
        return rendered["text"]

    def test_a_rendered_review_block_is_recognised_and_the_blocker_refuses_the_run(self):
        self._signoff_raises_and_renders()
        code, _, result = self.preflight_only("run-1")
        self.assertEqual(code, 10, "an open BLOCKER refuses the run")
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["stop_tag"], "open_blocker")
        self.assertEqual(result["records"]["open"]["BLOCKER"], 1)
        levelled = result["records"]["levelled"]
        self.assertGreaterEqual(levelled["native_rendered"], 1,
                                "the block the component rendered is already in the log")
        self.assertEqual(levelled["unparsed"], 0,
                         "and a rendered review line is never `legacy_unparsed`")
        self.assertEqual(len(kinds(self.ws, "finding_raised", "A")), 1,
                         "the finding is in the log once, not once per levelling pass")

    def test_the_user_can_say_to_build_on_it_anyway(self):
        self._signoff_raises_and_renders()
        code, document, _ = self.preflight_only("run-1", allow_open_blocker=True)
        self.assertEqual(code, 0)
        self.assertEqual(document["open"]["BLOCKER"], 1)
        self.assertGreaterEqual(document["records"]["levelled"]["native_rendered"], 1)
        self.assertEqual(len(kinds(self.ws, "finding_raised", "A")), 1)

    def test_a_major_does_not_refuse_the_run_and_the_build_completes(self):
        self._signoff_raises_and_renders(severity="MAJOR")
        code, result = self.run_build_fully("run-1")
        self.assertEqual(code, 10, "a MAJOR is not a refusal; only a BLOCKER is")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["records"]["open"]["MAJOR"], 1)
        self.assertEqual(self.status_line(), "built")

    def test_the_rendered_block_is_still_in_the_document_untouched(self):
        block = self._signoff_raises_and_renders(severity="MAJOR")
        self.assertEqual(self.run_build_fully("run-1")[0], 10)
        with open(os.path.join(self.ws, testlib.DOC_PATH), encoding="utf-8") as fh:
            text = fh.read()
        for line in [l for l in block.split("\n") if l.strip()]:
            self.assertIn(line, text, "build never touches punch-list history")


if __name__ == "__main__":
    unittest.main()
