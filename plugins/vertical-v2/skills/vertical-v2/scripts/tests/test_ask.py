"""vertical-v2's ask (contract section 3.2): the two `suggest` calls in v1's order, the ask rendered for
the executor, and the owner's answer recorded with the rows he named and his words.

The local row first, with the floor (`--floor opus`), then the outside rows with none, both under this
run's id and its readers run directory; the script prints the commands and never runs readers. The ask
shows, per row, the model suggest showed, any drop note, and the profile the row runs under. Silence
never proceeds: nothing after the ask runs until an answer is recorded. The answer is this run's alone.
"""
import json
import os
import unittest

import testlib
import vlib

RUN_ID = "run-0001"


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "the ask reads the records component and readers' roster (checkout and jsonschema)")
class _Ask(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vask-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws, self.info = vlib.make_repo(self.tmp)

    def gated(self, harness="claude-code"):
        drive, run_dir = vlib.start(self.tmp, self.ws, harness=harness)
        code, out, err = drive(["gate", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        return drive, run_dir

    def suggests(self, run_dir, local_row="claude-session", run_id=RUN_ID, dropped=()):
        local = vlib.write(self.tmp, "local.json", vlib.suggest_doc(run_id, run_dir, [local_row], floor="opus"))
        outside = vlib.write(self.tmp, "outside.json", vlib.suggest_doc(run_id, run_dir, vlib.OUTSIDE_ROWS, dropped=dropped))
        return local, outside


class TheSuggestCalls(_Ask):

    def test_the_local_row_with_the_floor_first_then_the_outside_rows(self):
        drive, run_dir = self.gated()
        code, out, err = drive(["ask", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        first, second = out["suggest"]
        readers_dir = os.path.join(run_dir, "readers")
        self.assertEqual(first["argv"], ["suggest", "claude-session", "--run", RUN_ID, "--run-dir", readers_dir,
                                         "--floor", "opus"])
        self.assertEqual(second["argv"], ["suggest", "gpt-astra,gpt-sol,gemini,deepseek,qwen", "--run", RUN_ID,
                                          "--run-dir", readers_dir])
        self.assertFalse(os.path.exists(readers_dir), "the script never runs readers")

    def test_on_codex_the_local_row_is_the_portable_claude_row(self):
        drive, run_dir = self.gated(harness="codex-cli")
        code, out, err = drive(["ask", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["suggest"][0]["argv"][1], "claude-opus-cli")

    def test_the_ask_runs_only_after_the_gate(self):
        drive, run_dir = vlib.start(self.tmp, self.ws)
        code, out, err = drive(["ask", "--run-dir", run_dir])
        self.assertEqual(code, 2)
        self.assertIn("gate", err)


class TheAsk(_Ask):

    def test_the_ask_names_every_row_with_its_model_drop_note_and_profile(self):
        drive, run_dir = self.gated()
        local, outside = self.suggests(run_dir, dropped=("qwen",))
        code, out, err = drive(["ask", "--run-dir", run_dir, "--local-suggest", local, "--outside-suggest", outside])
        self.assertEqual(code, 0, (out, err))
        ask = vlib.load(run_dir, "ask.json")
        rows = dict((r["row"], r) for r in ask["rows"])
        self.assertEqual(rows["claude-session"]["profile"], "repo-with-tools")
        self.assertEqual(rows["gpt-astra"]["profile"], "repo")
        self.assertEqual(rows["gemini"]["profile"], "repo")
        self.assertEqual(rows["deepseek"]["profile"], "packet-only")
        self.assertFalse(rows["qwen"]["available"])
        self.assertIn("unavailable", rows["qwen"]["drop_note"])
        self.assertIn("Local-only review, or local + outside reviewers?", out["ask"])
        for row in ("claude-session", "gpt-astra", "gpt-sol", "gemini", "deepseek", "qwen"):
            self.assertIn(row, out["ask"])
        self.assertEqual(out["next"], "ask --answer")

    def test_on_codex_the_local_profile_is_what_the_row_offers_and_the_ask_says_no_check_runs(self):
        drive, run_dir = self.gated(harness="codex-cli")
        local, outside = self.suggests(run_dir, local_row="claude-opus-cli")
        code, out, err = drive(["ask", "--run-dir", run_dir, "--local-suggest", local, "--outside-suggest", outside])
        self.assertEqual(code, 0, (out, err))
        rows = dict((r["row"], r) for r in vlib.load(run_dir, "ask.json")["rows"])
        self.assertEqual(rows["claude-opus-cli"]["profile"], "repo")
        self.assertIn("runs no check", out["ask"])

    def test_a_suggest_for_another_run_is_refused(self):
        drive, run_dir = self.gated()
        local, outside = self.suggests(run_dir, run_id="another-run")
        code, out, err = drive(["ask", "--run-dir", run_dir, "--local-suggest", local, "--outside-suggest", outside])
        self.assertEqual(code, 5, (out, err))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "ask.json")))

    def test_a_suggest_missing_a_row_is_refused(self):
        drive, run_dir = self.gated()
        local = vlib.write(self.tmp, "local.json", vlib.suggest_doc(RUN_ID, run_dir, ["claude-session"], floor="opus"))
        outside = vlib.write(self.tmp, "outside.json", vlib.suggest_doc(RUN_ID, run_dir, ["gpt-astra"]))
        code, out, err = drive(["ask", "--run-dir", run_dir, "--local-suggest", local, "--outside-suggest", outside])
        self.assertEqual(code, 5, (out, err))

    def test_a_local_suggest_without_the_floor_is_refused(self):
        drive, run_dir = self.gated()
        local = vlib.write(self.tmp, "local.json", vlib.suggest_doc(RUN_ID, run_dir, ["claude-session"]))
        outside = vlib.write(self.tmp, "outside.json", vlib.suggest_doc(RUN_ID, run_dir, vlib.OUTSIDE_ROWS))
        code, out, err = drive(["ask", "--run-dir", run_dir, "--local-suggest", local, "--outside-suggest", outside])
        self.assertEqual(code, 5, (out, err))


class TheAnswer(_Ask):

    def asked(self):
        drive, run_dir = self.gated()
        local, outside = self.suggests(run_dir)
        code, out, err = drive(["ask", "--run-dir", run_dir, "--local-suggest", local, "--outside-suggest", outside])
        self.assertEqual(code, 0, (out, err))
        return drive, run_dir

    def answer(self, drive, run_dir, **fields):
        doc = {"answer_version": 1, "kind": "ask", "run_id": RUN_ID, "rows": ["gpt-astra"], "words": "local plus GPT"}
        doc.update(fields)
        return drive(["ask", "--run-dir", run_dir, "--answer", vlib.write(self.tmp, "answer.json", doc)])

    def test_the_answer_is_recorded_with_the_rows_and_the_words(self):
        drive, run_dir = self.asked()
        code, out, err = self.answer(drive, run_dir, rows=["gpt-astra", "gemini"], words="local + GPT + Gemini")
        self.assertEqual(code, 0, (out, err))
        answer = vlib.load(run_dir, "ask.json")["answer"]
        self.assertEqual((answer["rows"], answer["words"]), (["gpt-astra", "gemini"], "local + GPT + Gemini"))
        self.assertEqual(out["next"], "scope")

    def test_a_local_only_answer_names_no_row(self):
        drive, run_dir = self.asked()
        code, out, err = self.answer(drive, run_dir, rows=[], words="local only")
        self.assertEqual(code, 0, (out, err))

    def test_silence_never_proceeds(self):
        drive, run_dir = self.asked()
        code, out, err = drive(["scope", "--run-dir", run_dir])
        self.assertEqual(code, 2, (out, err))

    def test_an_answer_with_blank_words_or_for_another_run_is_refused(self):
        drive, run_dir = self.asked()
        code, out, err = self.answer(drive, run_dir, words="   ")
        self.assertEqual(code, 4, (out, err))
        code, out, err = self.answer(drive, run_dir, run_id="another-run")
        self.assertEqual(code, 5, (out, err))
        self.assertIsNone(vlib.load(run_dir, "ask.json").get("answer"))

    def test_an_answer_with_an_unknown_key_is_refused(self):
        drive, run_dir = self.asked()
        code, out, err = self.answer(drive, run_dir, remember=True)
        self.assertEqual(code, 4, (out, err))


if __name__ == "__main__":
    unittest.main()
