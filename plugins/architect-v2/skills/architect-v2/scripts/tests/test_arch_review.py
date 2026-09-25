"""The blind review (brief 3.7, required test 7): `request` and `save-take`.

One readers request per named reviewer, the scope doc the single document and nothing else,
`profile: starved`, the mandate equal to the instruction the lane contract quotes; `authorized`
only on an outside row the input's `owner_word` names, never on a Claude row; readers' own
`validate` accepts the request. A take is saved verbatim before any triage, under the v1 review
home and in the run directory, and a repeat on the same lane and day takes `-2`, `-3`.
"""
import json
import os
import re
import subprocess
import unittest

import archlib
import testlib

CONTRACT = os.path.join(testlib.REF, "architect-v2-contract.md")
ROSTER = testlib.readers_roster()


def quoted_mandate():
    with open(CONTRACT, encoding="utf-8") as fh:
        text = fh.read()
    match = re.search(r"<!-- mandate -->\n> (.+?)\n<!-- /mandate -->", text, re.S)
    return match.group(1).replace("\n> ", " ") if match else None


@unittest.skipIf(ROSTER is None, "no readers component beside this core (the installed shape)")
class Request(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-review-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp)

    def written(self, **extra):
        run = archlib.ArchRun(self.tmp, self.ws, **extra)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 0, out + err)
        run.record(archlib.clean_answer())
        self.assertEqual(run.write()[0], 0)
        return run

    def test_the_packet_is_the_scope_doc_alone(self):
        run = self.written(owner_word={"rows": ["gpt-astra"], "words": "send it to gpt-astra"})
        code, doc, out, err = run.request("gpt-astra", "claude-session", roster=ROSTER, session_model="claude-model-x")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(len(doc["requests"]), 2)
        scope = os.path.join(self.ws, archlib.SCOPE_REL)
        for entry in doc["requests"]:
            req = testlib.load_json(entry["path"])
            self.assertEqual(req["documents"], [scope])
            self.assertNotIn("workspace", req)
            self.assertEqual(req["profile"], "starved")
            self.assertEqual(req["protocol_version"], 1)
            self.assertEqual(req["mandate"], archlib.MANDATE)
            self.assertEqual(req["mandate"], quoted_mandate())
            self.assertEqual(set(req) - {"protocol_version", "run_id", "call_id", "row", "mandate", "documents",
                                         "profile", "authorized", "session_model", "model"}, set())
            self.assertTrue(entry["path"].startswith(run.run_dir + os.sep))
        by_row = {testlib.load_json(e["path"])["row"]: testlib.load_json(e["path"]) for e in doc["requests"]}
        self.assertIs(by_row["gpt-astra"].get("authorized"), True)
        self.assertNotIn("authorized", by_row["claude-session"])
        self.assertEqual(by_row["claude-session"]["session_model"], "claude-model-x")
        self.assertNotIn("session_model", by_row["gpt-astra"])
        self.assertEqual(len({r["call_id"] for r in by_row.values()}), 2)
        self.assertEqual(len({r["run_id"] for r in by_row.values()}), 1)

    def test_authorized_only_where_the_owner_word_is(self):
        run = self.written()
        code, doc, out, err = run.request("gpt-astra", "gemini", roster=ROSTER)
        self.assertEqual(code, 0, out + err)
        for entry in doc["requests"]:
            self.assertNotIn("authorized", testlib.load_json(entry["path"]))
        run2 = archlib.ArchRun(self.tmp, self.ws, name="run-b", run_id="run-0002",
                               owner_word={"rows": ["gemini", "claude-session"], "words": "gemini and claude"})
        run2.to_harvest()
        run2.record(archlib.clean_answer(run_id="run-0002"))
        run2.write()
        code, doc, out, err = run2.request("gpt-astra", "gemini", "claude-session", roster=ROSTER)
        self.assertEqual(code, 0, out + err)
        got = {testlib.load_json(e["path"])["row"]: testlib.load_json(e["path"]).get("authorized")
               for e in doc["requests"]}
        self.assertEqual(got, {"gpt-astra": None, "gemini": True, "claude-session": None})

    def test_a_docless_run_builds_no_request(self):
        ws = testlib.git_workspace(self.tmp, "plain")
        staging = os.path.join(self.tmp, "staging")
        os.makedirs(staging)
        run = archlib.ArchRun(self.tmp, ws, staging, name="run-d")
        run.check_input()
        run.select("scope")
        run.select("architecture", "bench-counter")
        run.harvest()
        code, doc, out, err = run.request("gpt-astra", roster=ROSTER)
        self.assertEqual(code, 2, out + err)

    def test_an_unknown_row_is_usage(self):
        run = self.written()
        self.assertEqual(run.request("no-such-row", roster=ROSTER)[0], 2)

    @unittest.skipIf(testlib.readers_entry() is None, "no readers entry beside this core")
    def test_readers_validate_accepts_it(self):
        run = self.written(owner_word={"rows": ["gpt-astra"], "words": "send it to gpt-astra"})
        code, doc, out, err = run.request("claude-session", "gpt-astra", "gemini", roster=ROSTER,
                                          session_model="opus")
        self.assertEqual(code, 0, out + err)
        home = os.path.join(self.tmp, "readers-home")
        testlib.write_json(os.path.join(home, "plugins", "readers", "last-picks.json"),
                           {"protocol_version": 1, "picks": {}})
        env = testlib.base_env({"READERS_CHECKOUT": home, "READERS_RUN_ROOT": os.path.join(self.tmp, "readers-runs")})
        verdicts = {}
        for entry in doc["requests"]:
            proc = subprocess.run(["/bin/sh", testlib.readers_entry(), "validate", entry["path"]],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=run.cwd)
            text = proc.stdout.decode().strip()
            verdicts[entry["row"]] = json.loads(text).get("status") if text.startswith("{") else text
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "readers-runs")), "validate writes nothing")
        self.assertEqual(verdicts["claude-session"], "valid", verdicts)
        self.assertEqual(verdicts["gemini"], "unauthorized", "no word for gemini, so readers refuses it: %s" % verdicts)
        if verdicts["gpt-astra"] == "lane-unavailable":
            self.skipTest("gpt-astra's transport is absent from this shell (readers says lane-unavailable); "
                          "claude-session and gemini were checked: %s" % verdicts)
        self.assertEqual(verdicts["gpt-astra"], "valid", verdicts)


class SaveTake(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-take-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp)
        self.run = archlib.ArchRun(self.tmp, self.ws)
        self.run.to_harvest()
        self.run.record(archlib.clean_answer())
        self.assertEqual(self.run.write()[0], 0)

    def take(self, text, name="take.md"):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as fh:
            fh.write(text.encode("utf-8"))
        return path

    def test_verbatim_with_the_repeat_rule(self):
        body = "Walkthrough target: Sam\n\n  keeps  its   spacing\n"
        paths = []
        for n in range(3):
            code, doc, out, err = self.run.save_take("gpt-astra", self.take(body, "t%d.md" % n), model="gpt-model-x")
            self.assertEqual(code, 0, out + err)
            paths.append(doc["path"])
        base = os.path.join(self.ws, "docs", "reviews", "%s-architect-review-turnstile-gpt" % archlib.TODAY)
        self.assertEqual(paths, [base + ".md", base + "-2.md", base + "-3.md"])
        for path in paths:
            text = testlib.read_text(path)
            first, rest = text.split("\n", 1)
            self.assertIn("gpt-astra", first)
            self.assertIn("gpt-model-x", first)
            self.assertIn("sandbox-enforced", first)
            self.assertIn("/tmp/sidecar.json", first)
            self.assertEqual(rest, "\n" + body)
        copies = sorted(os.listdir(os.path.join(self.run.run_dir, "takes")))
        self.assertEqual(copies, sorted(os.path.basename(p) for p in paths))
        receipt = testlib.load_json(os.path.join(self.run.run_dir, "receipt.json"))
        recorded = [w["path"] for w in receipt["writes"] if w["kind"] == "document"]
        for path in paths:
            self.assertIn(path, recorded)

    def test_an_empty_take_is_refused(self):
        code, doc, out, err = self.run.save_take("gemini", self.take("  \n\n"))
        self.assertEqual(code, 5, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "reviews")))

    def test_a_row_that_is_no_roster_id_is_usage(self):
        before = archlib.listing(self.ws)
        for row in ("../../escape", "GPT Astra", ""):
            code, doc, out, err = self.run.save_take(row, self.take("a take\n"))
            self.assertEqual(code, 2, (row, out + err))
        self.assertEqual(archlib.listing(self.ws), before)

    def test_a_first_line_field_with_a_line_break_is_usage(self):
        code, doc, out, err = self.run.save_take("gemini", self.take("a take\n"), model="model-x\n## injected")
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "reviews")))

    def test_the_lane_names(self):
        code, doc, out, err = self.run.save_take("claude-session", self.take("a take\n"))
        self.assertEqual(code, 0, out + err)
        self.assertTrue(doc["path"].endswith("-architect-review-turnstile-claude.md"), doc["path"])
        code, doc, out, err = self.run.save_take("gemini", self.take("a take\n"))
        self.assertTrue(doc["path"].endswith("-architect-review-turnstile-gemini.md"), doc["path"])


class TheRulingsRound(unittest.TestCase):
    """After the takes: an amended answer carries the review's outcome and its rulings; the doc
    changes only where a ruling says so, and the visual and the publish are redone before report."""

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-rulings-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp)
        self.run = archlib.ArchRun(self.tmp, self.ws)
        self.run.to_harvest()
        self.first = archlib.clean_answer()
        self.assertEqual(self.run.record(self.first)[0], 0)
        self.assertEqual(self.run.write()[0], 0)
        self.assertEqual(self.run.render()[0], 0)
        self.assertEqual(self.run.publish("https://example.invalid/artifact/turnstile")[0], 0)
        take = os.path.join(self.tmp, "take.md")
        testlib.write_text(take, "a module and a reset, no server\n")
        code, doc, out, err = self.run.save_take("gpt-astra", take, model="gpt-model-x")
        self.assertEqual(code, 0, out + err)
        self.take_path = doc["path"]

    def amended(self, **over):
        a = archlib.clean_answer(review={"outcome": "done", "spine": "a module, no server"},
                                 rulings=[{"disagreement": "the take cuts reset()", "ruling": "reset() stays",
                                           "reviewers": ["gpt"], "changes": [],
                                           "trace": {"kind": "question", "ref": "Q5"}}])
        a["questions"].append({"id": "Q5", "text": "Keep reset()?", "touches": [], "answer": "yes, it stays"})
        a.update(over)
        return a

    def test_the_second_round_lands_and_report_completes(self):
        code, doc, out, err = self.run.record(self.amended())
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.run.write()[0], 0)
        self.assertEqual(self.run.report()[0], 2, "the visual is redone after the rulings before report")
        self.assertEqual(self.run.render()[0], 0)
        self.assertEqual(self.run.report()[0], 2, "the republish is recorded before report")
        self.assertEqual(self.run.publish("https://example.invalid/artifact/turnstile")[0], 0)
        code, doc, out, err = self.run.report()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["status"], "completed", out)
        text = testlib.read_text(os.path.join(self.ws, "docs", "architecture", "%s-turnstile.md" % archlib.TODAY))
        rel = os.path.relpath(self.take_path, self.ws)
        self.assertIn("Blind review: %s (gpt-model-x, %s)\n" % (rel, archlib.TODAY), text)
        self.assertIn("Rulings: blind review: agreed on a module, no server; 1 disagreement: "
                      "1. the take cuts reset(): reset() stays (gpt)", text)
        self.assertEqual(testlib.read_text(self.take_path).split("\n", 1)[1], "\na module and a reset, no server\n")

    def test_a_change_no_ruling_names_is_refused(self):
        a = self.amended(data_flow="the fixture calls a server")
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)
        self.assertIn("amendment-outside-rulings", [r["rule"] for r in doc["refusals"]])

    def test_a_change_a_ruling_names_is_accepted(self):
        a = self.amended(data_flow="the fixture calls turnstile.py; reset() zeroes it on demand")
        a["rulings"][0]["changes"] = ["data_flow"]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 0, out + err)


if __name__ == "__main__":
    unittest.main()
