"""Secrets through a whole run, on fakes (the brief's section 5; the frame's SEC-1, SEC-4, SEC-9, SEC-12, RUN-2,
RUN-13, RISK-1; the reviewer's closing rules D8, H13 and U3 of check 6; the owner's ruling A34).

Every value here reaches the tool the way a real one would: a fake provider's tool returns it in a
field its declaration marks secret, or the session's token channel holds it. The fixtures are the
frame author's (`EVIDENCE/author-9.md` section 6, `author-9c.md` section 1, `author-9d.md` sections
1 and 2), with the one fixture more of the contract's A36.
"""
import json
import os
import unittest

import fab
import harness
import rowlib
from sun_core import protected, results, texts

LEAST = results.LEAST_LENGTH


def kinds(records):
    return [(r["kind"], r.get("step") or r.get("status") or r.get("ending") or "") for r in records]


class SecretCase(harness.Case):
    ROWS = None

    def setUp(self):
        harness.Case.setUp(self)
        self.m = self.machine()

    def begin(self, description="a fixture project", issue=None, rows=None, name="demo", machine=None, **inputs):
        m = machine or self.m
        rows = rows if rows is not None else [rowlib.secret_op("X1")]
        rowlib.install(m, rowlib.lane("sunrise", rows))
        looked = m.look(name, inputs=m.inputs(description=description, **inputs))
        self.assertEqual(looked.ending, "preview", looked.text)
        if callable(issue):
            issue = issue(looked.doc["run"])
        if issue is not None:
            m.plan_fake("fakehost", dict({"command": "issue", "nth": 1}, **issue))
        went = m.go(looked, name)
        return looked.doc["run"], went

    def protected_records(self, run):
        folder = os.path.join(self.m.facts.run_dir(run), "protected")
        return sorted(n for n in os.listdir(folder) if n != "key")

    def envelope(self, run, record):
        with open(os.path.join(self.m.facts.run_dir(run), "protected", record), "rb") as fh:
            return protected.open_envelope(fh.read())

    def forms_text(self, run):
        folder = os.path.join(self.m.facts.run_dir(run), "forms")
        return dict((n, open(os.path.join(folder, n)).read()) for n in sorted(os.listdir(folder)))

    def after(self, run, kind):
        """The journal's records from the operation's start on."""
        records = self.m.journal(run)
        first = next(i for i, r in enumerate(records) if r["kind"] == kind)
        return records[first:]


class TheDisproof(SecretCase):
    """SEC-12's test line, "The disproof"; SEC-1's; SEC-4's ("A value in a secret field that equals a name on record")."""

    NAME = "tidetablename"

    def catch(self):
        rows = [rowlib.secret_op("X1"),
                rowlib.says("Y1", needs=[{"output": "credential", "level": "state", "treatment": "then not applicable"}])]
        run, went = self.begin(self.NAME, {"value": self.NAME}, rows)
        return run, went

    def test_SEC12_SEC4_the_journal_holds_receipt_due_then_the_disproof_then_the_receipt_and_the_run_is_stopped(self):
        run, went = self.catch()
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: a safe ground disproved", went.lines)
        tail = self.after(run, "start")
        self.assertEqual(kinds(tail)[:4], [("start", ""), ("step", "receipt-due"), ("disproof", ""), ("step", "receipt")])
        disproof = tail[2]
        self.assertNotIn(self.NAME, json.dumps(disproof), "the disproof record holds the value")
        record = disproof["rests"]["protected"]["record"]
        self.assertEqual(tail[1]["fields"], [{"field": "token", "record": record}], "the receipt-due record did not name the id the value was kept under")
        self.assertEqual(tail[3]["reference"]["record"], record)
        self.assertEqual(self.envelope(run, record)["raw"], self.NAME)
        self.assertTrue(disproof["found"], "the disproof record does not say where the run's records hold the value")
        self.assertNowhere(self.NAME, went)
        for name, text in self.forms_text(run).items():
            if name.startswith("status"):
                self.assertNotIn(self.NAME, text, name)
                self.assertIn(texts.WITHHELD, text, name)
                self.assertIn("disproof %d" % disproof["n"], text, "the form does not carry the record's reference")
                self.assertIn("[X1]", text, "the form lost its other lines")

    def test_SEC12_SEC1_a_status_a_resume_a_replan_and_a_close_each_withhold_the_name(self):
        run, went = self.catch()
        m = self.m
        manifest = open(os.path.join(m.facts.run_dir(run), "manifest-1.json"), "rb").read()
        records_then = len(m.journal(run))
        calls_then = len(m.calls("fakehost"))
        status = m.summon("status")
        self.assertEqual(status.ending, "stopped", status.text)
        self.assertNowhere(self.NAME, status)
        resumed = m.summon("resume", "demo", "--position", status.doc["position"], "--word", "go on")
        self.assertEqual(resumed.ending, "stopped", resumed.text)
        self.assertNowhere(self.NAME, resumed)
        for call in m.calls("fakehost")[calls_then:]:
            self.assertNotIn(self.NAME, json.dumps(call["argv"]), "a command was started whose argument holds the name")
        replanned = m.summon("replan", "demo", "--inputs", m.inputs(description=self.NAME))
        self.assertEqual(replanned.ending, "stopped", replanned.text)
        self.assertNowhere(self.NAME, replanned)
        self.assertEqual(open(os.path.join(m.facts.run_dir(run), "manifest-1.json"), "rb").read(), manifest)
        self.assertEqual([n for n in os.listdir(m.facts.run_dir(run)) if n.startswith("manifest-")], ["manifest-1.json"])
        closed = m.summon("close", "demo", "--word", "close")
        self.assertEqual(closed.ending, "closed", closed.text)
        self.assertNowhere(self.NAME, closed)
        for record in m.journal(run)[records_then:]:
            self.assertNotIn(self.NAME, json.dumps(record), "a new record holds the name")
        forms = self.forms_text(run)
        later = [n for n in forms if n.startswith("status")]
        self.assertGreaterEqual(len(later), 4)
        for name in later:
            self.assertNotIn(self.NAME, forms[name], name)
            self.assertIn(texts.WITHHELD, forms[name], name)
            self.assertIn("names: demo", forms[name], "another safe field FORM-2's forms hold is gone from %s" % name)

    def test_RUN2_D8_a_caught_run_id_end_to_end_is_listed_by_its_files_name_at_the_keying_refusal(self):
        m = self.m
        second = fab.open_run(m, "plain")
        run, went = self.begin("a fixture project", lambda run_id: {"value": run_id})
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual([k for k in kinds(self.after(run, "start")) if k[0] == "disproof"], [("disproof", "")])
        before = m.snapshot(os.path.join(".sun-v2", "runs"))
        for label, damage in (("removed", lambda: os.remove(m.facts.keying_file)), ("wider", lambda: os.chmod(m.facts.keying_file, 0o644))):
            saved = open(m.facts.keying_file).read()
            damage()
            try:
                refusal = m.summon("resume", "demo")
            finally:
                with open(m.facts.keying_file, "w") as fh:
                    fh.write(saved)
                os.chmod(m.facts.keying_file, 0o600)
            with self.subTest(keying=label):
                first_out = next(e["i"] for e in refusal.events if e["stage"] == "output")
                reads = [e["subject"] for e in refusal.events if e["stage"] == "read" and e["i"] < first_out]
                self.assertIn(os.path.join(m.facts.run_dir(run), "journal.jsonl"), reads, "the withheld read did not stand before the first byte")
                self.assertNowhere(run, refusal)
                self.assertIn(texts.RUN_ON_RECORD + second, refusal.lines)
                name = os.path.basename(m.facts.open_runs_file)
                self.assertIn(texts.RUN_ON_RECORD + texts.WITHHELD + texts.ID_IN_FILE + name, refusal.lines)
                self.assertIn(run, open(m.facts.open_runs_file).read())
                self.assertEqual(m.snapshot(os.path.join(".sun-v2", "runs")), before)


class Custody(SecretCase):
    """U3 and A34 through an operation: SEC-4's test line from "A valid secret beside an invalid required field" on."""

    def expect_kept(self, run, went, value, disproved=False):
        tail = self.after(run, "start")
        want = [("start", ""), ("step", "receipt-due")] + ([("disproof", "")] if disproved else []) + [("step", "receipt")]
        self.assertEqual(kinds(tail)[:len(want)], want)
        receipt = tail[len(want) - 1]
        self.assertEqual(receipt["outcome"], "kept")
        self.assertEqual(self.envelope(run, receipt["reference"]["record"])["raw"], value, "the protected record does not hold the value as it was read")
        self.assertEqual(went.ending, "stopped", went.text)
        if isinstance(value, str) and value.strip():
            self.assertNowhere(value.strip(), went)
        if disproved:
            self.assertIn("stopped: a safe ground disproved", went.lines)
        else:
            self.assertIn("stopped: a command failed", went.lines)
            self.assertEqual([r for r in tail if r["kind"] == "disproof"], [])
        self.assertEqual([r for r in tail if r["kind"] in ("completion", "answer")], [], "a field of a malformed result was kept")

    def test_SEC4_U3_a_valid_secret_beside_an_absent_then_a_failing_required_field_then_in_the_saved_inputs(self):
        secret = "zz9" + harness.canary("u3")[-12:]
        for label, issue, description in (("absent", {"value": secret, "omit": ["state"]}, "a fixture project"),
                                          ("failing", {"value": secret, "extra": {"state": "bogus"}}, "a fixture project"),
                                          ("in the saved inputs", {"value": secret, "omit": ["state"]}, "about " + secret)):
            with self.subTest(pass_=label):
                self.m = harness.Machine(self.tmp, "home-" + label.split()[0], label)
                run, went = self.begin(description, issue)
                self.expect_kept(run, went, secret, disproved=label == "in the saved inputs")

    def test_SEC4_A34_a_failing_value_at_the_least_length_and_five_times_it_is_kept_and_stops_on_a_disproof_when_saved(self):
        for label, value, description in (("at the least length", "A" * LEAST, "a fixture project"),
                                          ("five times it", "B" * (5 * LEAST), "a fixture project"),
                                          ("saved", "A" * LEAST, "it says " + "A" * LEAST)):
            with self.subTest(pass_=label):
                self.m = harness.Machine(self.tmp, "home-" + label.split()[0], label)
                run, went = self.begin(description, {"value": value})
                self.expect_kept(run, went, value, disproved=label == "saved")

    def test_SEC4_A34_five_failing_values_under_the_least_length_are_dropped_and_enter_nothing(self):
        passes = [("one byte under", {"value": "A" * (LEAST - 1)}, "it says " + "A" * (LEAST - 1)),
                  ("one byte", {"value": "A"}, "A fixture"),
                  ("empty", {"value": ""}, "a fixture project"),
                  ("white space", {"value": " " * 6 + "A" + " " * 6}, "a fixture project"),
                  ("a truth value", {"text": '{"token": true, "state": "issued"}'}, "a fixture project")]
        for index, (label, issue, description) in enumerate(passes):
            with self.subTest(pass_=label):
                self.m = harness.Machine(self.tmp, "home-%d" % index, label)
                run, went = self.begin(description, issue)
                tail = self.after(run, "start")
                self.assertEqual(kinds(tail)[:3], [("start", ""), ("step", "receipt-due"), ("step", "receipt")])
                self.assertEqual(tail[2]["outcome"], results.DROPPED)
                self.assertEqual(self.protected_records(run), [], "a protected record was written for a dropped value")
                self.assertEqual([r for r in tail if r["kind"] == "disproof"], [])
                self.assertIn("stopped: a command failed", went.lines)
                if index < 2:
                    status = self.m.summon("status")
                    form = open(status.doc["forms"][0]).read()
                    self.assertIn("in your words: " + description, form, "the saved input is not shown as text")
                    self.assertNotIn(texts.WITHHELD, form)

    def test_SEC4_nothing_at_the_place_and_the_answers_word_for_no_value(self):
        for label, issue in (("nothing", {"omit": ["token"]}), ("null", {"text": '{"token": null, "state": "issued"}'})):
            with self.subTest(place=label):
                self.m = harness.Machine(self.tmp, "home-" + label, label)
                run, went = self.begin("a fixture project", issue)
                tail = self.after(run, "start")
                self.assertEqual(kinds(tail)[:3], [("start", ""), ("step", "receipt-due"), ("step", "receipt")])
                self.assertEqual(tail[2]["outcome"], results.NO_VALUE)
                self.assertEqual(self.protected_records(run), [])

    def test_SEC4_white_space_at_its_ends_both_saved_forms_disprove(self):
        core = "A" * LEAST
        for label, description in (("with its two spaces", "it says [ %s ] there" % core), ("without them", "it says [%s] there" % core)):
            with self.subTest(saved=label):
                self.m = harness.Machine(self.tmp, "home-" + label.split()[0], label)
                run, went = self.begin(description, {"value": " " + core + " "})
                self.expect_kept(run, went, " " + core + " ", disproved=True)

    def test_SEC4_a_failing_number_and_a_failing_object_through_an_operation(self):
        digits = "12345678" * 2
        long_text, short_text = "L" * (LEAST + 3), "shrt"
        obj = '{"inner": "%s", "small": "%s", "n": 4242}' % (long_text, short_text)
        passes = [("the digits saved", '{"state": "issued", "token": %s}' % digits, "order " + digits, digits, True),
                  ("the longer text saved", '{"token": %s, "state": "issued"}' % obj, "see " + long_text, obj, True),
                  ("only the short pieces saved", '{"token": %s, "state": "issued"}' % obj, "shrt 4242 inner", obj, False)]
        for index, (label, text, description, raw, disproved) in enumerate(passes):
            with self.subTest(pass_=label):
                self.m = harness.Machine(self.tmp, "home-%d" % index, label)
                run, went = self.begin(description, {"text": text})
                self.expect_kept(run, went, raw, disproved=disproved)
                if not disproved:
                    form = open(self.m.summon("status").doc["forms"][0]).read()
                    self.assertIn("in your words: shrt 4242 inner", form)

    def test_SEC4_A36_one_fixture_more_a_text_in_a_list_in_an_object(self):
        long_text, short = "D" * LEAST, "tiny"
        obj = '{"outer": [["%s", "%s", 7], {"deep": "%s"}]}' % (short, long_text, short)
        for label, description, disproved in (("the long text saved", "note " + long_text, True), ("only shorter pieces saved", "tiny 7 outer deep", False)):
            with self.subTest(saved=label):
                self.m = harness.Machine(self.tmp, "home-" + label.split()[1], label)
                run, went = self.begin(description, {"text": '{"state": "issued", "token": %s}' % obj})
                self.expect_kept(run, went, obj, disproved=disproved)

    def test_SEC4_V1_a_secrets_value_ending_in_one_line_break_fails_its_alphabet_through_an_operation_and_stays_in_custody(self):
        """The reviewer's V1 (check 3, `newline-operation.py`): a fake issues a value of lower-case letters and digits
        followed by one line break, and the go ended `complete`, the value passing `a-z0-9`. SEC-4: a declared field that
        fails its validator turns the result `malformed`, but for a secret, which stays in custody; a failing value at the
        least length or over "is kept whole, as it was read, in its protected record"; the register holds the value "without
        the white space at its ends, where that differs", so the search finds it where the saved inputs hold it."""
        secret = "zz9" + harness.canary("v1")[-12:]
        for index, (label, description) in enumerate((("a value in no input of the fixture's", "a fixture project"),
                                                      ("the value in the fixture's saved inputs", "about " + secret))):
            with self.subTest(pass_=label):
                self.m = harness.Machine(self.tmp, "home-v1-%d" % index, label)
                run, went = self.begin(description, {"value": secret + "\n"})
                self.expect_kept(run, went, secret + "\n", disproved=index == 1)
                self.assertEqual([r for r in self.m.journal(run) if r["kind"] == "completion"], [], "the operation completed")
                status = self.m.summon("status")
                self.assertNowhere(secret, status)
                for form in status.doc.get("forms", []):
                    self.assertNotIn(secret, open(form).read(), "the value is in the next status form")
        with self.subTest(pass_="a plain value"):
            self.m = harness.Machine(self.tmp, "home-v1-plain", "plain")
            run, went = self.begin("a fixture project", {"value": secret})
            self.assertEqual(went.ending, "complete", went.text)
            self.assertEqual([r.get("outcome") for r in self.m.journal(run) if r.get("step") == "receipt"], ["kept"])
            self.assertEqual(len([r for r in self.m.journal(run) if r["kind"] == "completion"]), 1)


class CustodyBesideAnUnlistedExit(SecretCase):
    """SEC-4 (the reviewer's D8-U; the owner's ruling, A140): an exit is safe where "the declaration lists that exit value and
    maps it to a kind or an outcome", and "a fixed field off its list ... turns the whole result into kind `malformed` with
    nothing kept, but for one thing: a secret. A value at a secret field's place stays in the tool's custody whatever becomes
    of the rest of the result ...: it is in the register; it is written to its protected record; the search for it is made;
    the disproof record is written where the search finds it; and the receipt is given, all as SEC-12 orders." Where nothing
    stands at the place, "the receipt says that the result held no such value". SEC-12, where a disproof is written: "Then the
    invocation ends: `stopped` in a run that has its go".

    Through an operation: the fake host's `issue` (a secret field `token`, a fixed field `state`) answers with an exit its
    declaration does not list (7; it lists 0, 3 and 4)."""

    UNLISTED = 7
    expect_kept = Custody.expect_kept

    def answer(self, text):
        self.assertNotIn(str(self.UNLISTED), rowlib.providers()["fakehost"]["commands"]["issue"]["exits"])
        return {"do": "raw", "text": text, "exit": self.UNLISTED}

    def test_SEC4_D8U_a_valid_secret_beside_an_unlisted_exit_is_kept_searched_disproved_where_saved_and_receipted(self):
        secret = "zz9" + harness.canary("d8u")[-12:]
        for label, description in (("a token in no input of the fixture's", "a fixture project"),
                                   ("the token in the fixture's saved inputs", "about " + secret)):
            with self.subTest(pass_=label):
                self.m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
                self.assertNotIn(secret, "a fixture project")
                run, went = self.begin(description, self.answer(json.dumps({"token": secret, "state": "issued"})))
                self.expect_kept(run, went, secret, disproved=label.startswith("the token"))
                self.assertEqual(self.protected_records(run), [self.after(run, "start")[1]["fields"][0]["record"]],
                                 "the protected record is not the one the receipt-due record named")

    def test_SEC4_D8U_an_unlisted_exit_with_nothing_at_the_place_or_an_answer_not_well_formed_receipts_no_such_value(self):
        """Nothing at the place: "the receipt says that the result held no such value". An answer that is not well-formed
        beside an unlisted exit is read as one beside a listed exit is (the control pass): no structured answer, so nothing at
        the place, and the same receipt."""
        for label, text, code in (("nothing at the place", json.dumps({"state": "issued"}), self.UNLISTED),
                                  ("not well-formed, beside an unlisted exit", "not json {", self.UNLISTED),
                                  ("not well-formed, beside a listed exit (the control)", "not json {", 0)):
            with self.subTest(pass_=label):
                self.m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
                run, went = self.begin("a fixture project", {"do": "raw", "text": text, "exit": code})
                tail = self.after(run, "start")
                self.assertEqual(kinds(tail)[:3], [("start", ""), ("step", "receipt-due"), ("step", "receipt")])
                self.assertEqual(tail[2]["outcome"], results.NO_VALUE)
                self.assertEqual(self.protected_records(run), [], "a protected record was written")
                self.assertEqual([r for r in tail if r["kind"] == "disproof"], [])
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: a command failed", went.lines)
                self.assertEqual([r for r in tail if r["kind"] in ("completion", "answer")], [], "a field of a malformed result was kept")

    def test_SEC4_D8M_a_complete_secret_member_before_the_damage_is_kept_searched_disproved_where_saved_and_receipted(self):
        """The reviewer's D8-M (check 3, `custody.py`, "broken-tail"): a fake answers `{"token": "<value>", "state":`
        beside an unlisted exit; the receipt said "no such value", and with the value in the saved inputs no disproof was
        written and the next status form showed it. The owner's pick (brief-27, item 3): "The tool pulls the complete secret
        out of the damaged reply and protects it like any other." So it is kept, its protected record written, the search
        made, the disproof written where the saved inputs hold it, and the receipt names the record; the result stays
        `malformed`; the value is in no later output, the next status form among them. A member whose string the damage cuts
        off is not kept as a whole value, and its receipt stays as it was."""
        secret = "zz9" + harness.canary("d8m")[-12:]
        broken = '{"token": %s, "state":' % json.dumps(secret)
        passes = (("the reviewer's broken tail, the token in no input of the fixture's", "a fixture project", self.UNLISTED),
                  ("the reviewer's broken tail, the token in the fixture's saved inputs", "about " + secret, self.UNLISTED),
                  ("the broken tail beside a listed exit", "a fixture project", 0))
        for index, (label, description, code) in enumerate(passes):
            with self.subTest(pass_=label):
                self.m = harness.Machine(self.tmp, "home-d8m-%d" % index, label)
                run, went = self.begin(description, {"do": "raw", "text": broken, "exit": code})
                self.expect_kept(run, went, secret, disproved=index == 1)
                self.assertEqual(self.protected_records(run), [self.after(run, "start")[1]["fields"][0]["record"]],
                                 "the protected record is not the one the receipt-due record named")
                status = self.m.summon("status")
                self.assertNowhere(secret, status)
                forms = status.doc.get("forms", [])
                self.assertTrue(forms, "the status summons rendered no form")
                for form in forms:
                    self.assertNotIn(secret, open(form).read(), "the value is in the next status form")
                for record in self.m.journal(run):
                    self.assertNotIn(secret, json.dumps(record), "a journal record holds the value")
        with self.subTest(pass_="a member whose string the damage cuts off, the token in the saved inputs"):
            self.m = harness.Machine(self.tmp, "home-d8m-cut", "cut")
            run, went = self.begin("about " + secret, {"do": "raw", "text": '{"token": "%s' % secret, "exit": self.UNLISTED})
            tail = self.after(run, "start")
            self.assertEqual(kinds(tail)[:3], [("start", ""), ("step", "receipt-due"), ("step", "receipt")])
            self.assertEqual(tail[2]["outcome"], results.NO_VALUE)
            self.assertEqual(self.protected_records(run), [], "a value cut off by the damage was kept as a whole value")
            self.assertEqual([r for r in tail if r["kind"] == "disproof"], [])
            self.assertIn("stopped: a command failed", went.lines)


class CustodyBesideAFixedFieldNoGroundMayProve(SecretCase):
    """SEC-4: a value at a secret field's place stays in the tool's custody "whatever becomes of the rest of the
    result", shown for a result made `malformed` by a fixed field whose value is on its list and holds an entry
    of the register (the report's question 7; asked for by the control room, 2026-10-13)."""

    WORD = "granted"

    def begin_waiting(self, label, description, token):
        self.m = harness.Machine(self.tmp, "home-" + label, label)
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["issue"]["fields"][1]["list"] = [self.WORD]
        rows = [rowlib.owner_step("O1", mode="on his word"),
                rowlib.secret_op("X1", needs=[{"output": "connected", "level": "state", "accepts": ["his word"], "treatment": "then not applicable"}])]
        rowlib.install(self.m, rowlib.lane("sunrise", rows), providers=providers)
        looked, went = self.m.started(inputs=self.m.inputs(description=description))
        self.assertEqual(went.ending, "waiting", went.text)
        self.m.plan_fake("fakehost", {"command": "issue", "nth": 1, "value": self.secret, "extra": {"state": self.WORD}})
        env = {"FAKEHOST_TOKEN": token} if token else {}
        position = self.m.summon("status").doc["position"]
        return looked.doc["run"], self.m.summon("resume", "demo", "--position", position, "--done", "O1", env=env)

    def test_SEC4_custody_holds_where_a_fixed_field_on_its_list_holds_a_register_entry_and_makes_the_result_malformed(self):
        self.secret = "zz9" + harness.canary("q7")[-12:]
        # the control: with no register entry in the fixed field's word, the same result is whole and the operation is done
        run, went = self.begin_waiting("control", "a fixture project", None)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(self.m.statuses(run)["X1"], "done")
        # the register holds the word the fixed field returns (the session's token is that word): no ground may prove it
        run, went = self.begin_waiting("caught", "a fixture project", self.WORD)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: a command failed", went.lines)
        self.assertNotIn("X1", self.m.statuses(run), "a field of the malformed result was kept, or the operation was completed")
        tail = self.after(run, "start")
        self.assertEqual(kinds(tail)[:3], [("start", ""), ("step", "receipt-due"), ("step", "receipt")])
        receipt = tail[2]
        self.assertEqual(receipt["outcome"], "kept")
        self.assertEqual(tail[1]["fields"], [{"field": "token", "record": receipt["reference"]["record"]}])
        self.assertEqual(self.envelope(run, receipt["reference"]["record"])["raw"], self.secret, "the protected record does not hold the secret")
        self.assertEqual([r for r in tail if r["kind"] == "disproof"], [], "the search found the secret where the run's records do not hold it")
        self.assertNowhere(self.secret, went)
        self.assertNotIn(self.secret, open(went.doc["forms"][0]).read())
        # the search is made: with the secret in the saved inputs it is found, and the disproof record stands before the receipt
        run, went = self.begin_waiting("saved", "about " + self.secret, self.WORD)
        tail = self.after(run, "start")
        self.assertEqual(kinds(tail)[:4], [("start", ""), ("step", "receipt-due"), ("disproof", ""), ("step", "receipt")])
        self.assertEqual(tail[2]["rests"]["protected"]["record"], tail[3]["reference"]["record"])
        self.assertEqual(went.ending, "stopped")
        self.assertIn("stopped: a safe ground disproved", went.lines)
        self.assertNowhere(self.secret, went)
        form = open(went.doc["forms"][0]).read()
        self.assertNotIn(self.secret, form)
        self.assertIn(texts.WITHHELD, form)


class MoreThanOneSecretField(SecretCase):
    """SEC-4's test line, "Two secret fields"; SEC-12's, "More than one secret field"; the reviewer's D8-B closing
    rule: "Preserve custody, register entries, disproof and recoverable receipt coverage for every kept secret
    field of every admitted result, and test a later secret field that equals saved safe content." """

    def two_fields(self, label, description):
        """A declaration that gives two fields of one command the secret disposition, in the order token, second."""
        self.m = harness.Machine(self.tmp, "home-" + label, label)
        providers = rowlib.providers()
        issue = providers["fakehost"]["commands"]["issue"]
        issue["fields"].insert(1, dict(issue["fields"][0], name="second", place=["second"]))
        rowlib.install(self.m, rowlib.lane("sunrise", [rowlib.secret_op("X1")]), providers=providers)
        looked = self.m.look("demo", inputs=self.m.inputs(description=description))
        self.assertEqual(looked.ending, "preview", looked.text)
        return looked

    def go_keeping_the_world(self, looked):
        """The go, in-process, keeping its world, so that the invocation's register can be read after it."""
        from sun_core import cli
        world = self.m.world()
        code = cli.main(["go", "--kind", "sunrise", "--name", "demo", "--run", looked.doc["run"],
                         "--manifest-sha256", looked.doc["manifest_sha256"]], world=world)
        return harness.Result(code, world.output.stdout.getvalue(), world.output.stderr.getvalue(), []), world.session.register

    def test_SEC4_SEC12_D8B_each_secret_field_has_its_record_its_entry_its_search_and_its_receipt_in_the_declarations_order(self):
        first, second = "zz9" + harness.canary("first")[-12:], "zz9" + harness.canary("second")[-12:]
        for label, description, issue, caught in (
                ("the second saved", "about " + second, {"value": first, "extra": {"second": second}}, 1),
                ("the first saved", "about " + first, {"value": first, "extra": {"second": second}}, 0),
                ("the second failing", "a fixture project", {"value": first, "extra": {"second": "A" * LEAST}}, None)):
            with self.subTest(pass_=label):
                looked = self.two_fields(label.split()[1] + "-" + label.split()[2], description)
                run = looked.doc["run"]
                self.m.plan_fake("fakehost", dict({"command": "issue", "nth": 1}, **issue))
                went, register = self.go_keeping_the_world(looked)
                values = [issue["value"], issue["extra"]["second"]]
                tail = self.after(run, "start")
                due = tail[1]
                self.assertEqual(kinds(tail)[:2], [("start", ""), ("step", "receipt-due")])
                self.assertEqual([f["field"] for f in due["fields"]], ["token", "second"], "the due record does not name each field")
                ids = [f["record"] for f in due["fields"]]
                self.assertEqual(len(set(ids)), 2, "the due record does not name two ids")
                want = [("start", ""), ("step", "receipt-due")] + ([("disproof", "")] if caught is not None else []) + \
                       [("step", "receipt"), ("step", "receipt")]
                self.assertEqual(kinds(tail)[:len(want)], want)
                receipts = tail[len(want) - 2:len(want)]
                self.assertEqual([(r["field"], r["outcome"], r["reference"]["record"]) for r in receipts],
                                 [("token", "kept", ids[0]), ("second", "kept", ids[1])], "a receipt is missing or out of the declaration's order")
                for record_id, value in zip(ids, values):
                    self.assertEqual(self.envelope(run, record_id)["raw"], value, "a field's protected record does not hold its value")
                    self.assertTrue(register.holds(value), "a kept secret field's value is not in the register")
                    self.assertNowhere(value, went)
                if caught is None:
                    self.assertIn("stopped: a command failed", went.lines)
                    self.assertEqual([r for r in tail if r["kind"] == "disproof"], [])
                    continue
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: a safe ground disproved", went.lines)
                self.assertEqual(tail[2]["rests"]["protected"]["record"], ids[caught], "the disproof does not refer to the caught field's record")
                self.assertEqual(len([r for r in tail if r["kind"] == "disproof"]), 1)
                form = open(self.m.summon("status").doc["forms"][0]).read()
                self.assertNotIn(values[caught], form)
                self.assertIn(texts.WITHHELD, form, "the next status form does not hold the fixed words in the description's place")
                self.assertNotIn(values[1 - caught], form)

    def test_SEC12_D8B_killed_between_the_two_protected_records_the_second_is_lost_and_the_first_is_recovered_first(self):
        first, second = "zz9" + harness.canary("kfirst")[-12:], "zz9" + harness.canary("ksecond")[-12:]
        looked = self.two_fields("killed", "about " + first)
        run = looked.doc["run"]
        self.m.plan_fake("fakehost", {"command": "issue", "nth": 1, "value": first, "extra": {"second": second}})
        made = []

        def second_record(event):
            if event["stage"] == "pre" and event["op"] == "create" and os.sep + "protected" + os.sep in event["subject"]:
                made.append(event["subject"])
            return len(made) == 2
        went = self.m.go(looked, kill=second_record)
        self.assertTrue(went.killed)
        due = [r for r in self.m.journal(run) if r.get("step") == "receipt-due"][-1]
        ids = [f["record"] for f in due["fields"]]
        self.assertEqual(self.protected_records(run), [ids[0]], "the kill did not fall between the two protected records")
        before = len(self.m.journal(run))
        status = self.m.summon("status")
        form = open(status.doc["forms"][0]).read()
        self.assertIn("a secret may have been received and lost: operation X1, execution 1, field second", form)
        self.assertNotIn("execution 1, field token", form, "the first field, whose record was written, is still said to be lost")
        self.assertNotIn(first, form)
        self.assertIn(texts.WITHHELD, form)
        self.assertNowhere(first, status)
        new = self.m.journal(run)[before:]
        self.assertEqual(kinds(new)[:2], [("disproof", ""), ("step", "receipt")], "the first records are not the disproof, then the receipt")
        self.assertEqual(new[0]["rests"]["protected"]["record"], ids[0])
        self.assertEqual((new[1]["field"], new[1]["reference"]["record"]), ("token", ids[0]))
        self.assertEqual([r for r in self.m.journal(run) if r.get("step") == "receipt" and r.get("field") == "second"], [])


class TheCrashInstant(SecretCase):
    """SEC-12's test line, "RK8's case" and "The receipt"; RISK-1's; RUN-13's (H13)."""

    SAFE = "safelinefromamanifest"

    def killed(self, where):
        rows = [rowlib.secret_op("X1")]
        rowlib.install(self.m, rowlib.lane("sunrise", rows))
        looked = self.m.look("demo", inputs=self.m.inputs(description=self.SAFE))
        self.m.plan_fake("fakehost", {"command": "issue", "nth": 1, "value": self.SAFE})
        went = self.m.go(looked, kill=lambda e: e["stage"] == where and e["op"] == "create" and os.sep + "protected" + os.sep in e["subject"])
        self.assertTrue(went.killed)
        return looked.doc["run"]

    def test_SEC12_RK8_killed_before_the_protected_record_the_status_says_lost_the_line_is_still_shown_the_resume_goes_on(self):
        run = self.killed("pre")
        self.assertEqual(self.protected_records(run), [])
        status = self.m.summon("status")
        form = open(status.doc["forms"][0]).read()
        self.assertIn("a secret may have been received and lost: operation X1, execution 1", form)
        self.assertIn("in your words: " + self.SAFE, form, "the line the run holds as safe is no longer shown")
        self.assertEqual([r for r in self.m.journal(run) if r["kind"] == "disproof"], [])
        resumed = self.m.summon("resume", "demo", "--position", status.doc["position"], "--word", "go on")
        self.assertEqual(resumed.ending, "complete", resumed.text)
        self.assertEqual(self.m.statuses(run)["X1"], "not proven")
        issued = [i["value"] for i in self.m.fake("fakehost", "issued.jsonl", [])]
        for value in issued:
            self.assertNowhere(value, resumed)
        # RISK-1: no record carries a mark for RK8; the receipt due and not given is the record of what happened
        self.assertEqual([r for r in self.m.journal(run) if r.get("step") == "risk-mark"], [])
        again = open(self.m.summon("status").doc["forms"][0] if self.m.summon("status").doc.get("forms") else resumed.doc["forms"][0]).read()
        self.assertIn("operation X1, execution 1", again, "a later status form no longer says the receipt is due")

    def test_SEC12_RK8_killed_after_the_protected_record_the_next_status_withholds_the_line_and_writes_disproof_then_receipt(self):
        run = self.killed("post")
        self.assertEqual(len(self.protected_records(run)), 1)
        before = len(self.m.journal(run))
        status = self.m.summon("status")
        form = open(status.doc["forms"][0]).read()
        self.assertNotIn(self.SAFE, form)
        self.assertIn(texts.WITHHELD, form)
        self.assertNowhere(self.SAFE, status)
        self.assertEqual(kinds(self.m.journal(run)[before:])[:2], [("disproof", ""), ("step", "receipt")])

    def test_RUN13_H13_a_close_that_owes_a_disproof_record_and_a_receipt_writes_those_two_then_the_close_record(self):
        run = self.killed("post")
        before = len(self.m.journal(run))
        calls = len(self.m.calls("fakehost"))
        closed = self.m.summon("close", "demo", "--word", "close")
        self.assertEqual(closed.ending, "closed", closed.text)
        self.assertEqual(kinds(self.m.journal(run)[before:]), [("disproof", ""), ("step", "receipt"), ("run-end", "closed")])
        self.assertEqual(len(self.m.calls("fakehost")), calls, "a close made a provider call")
        self.assertNowhere(self.SAFE, closed)

    def test_RUN13_a_close_that_owes_nothing_writes_one_record_and_without_his_word_none(self):
        rowlib.install(self.m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]))
        looked, went = self.m.started()
        self.assertEqual(went.ending, "waiting", went.text)
        run = looked.doc["run"]
        before = len(self.m.journal(run))
        calls = len(self.m.calls("fakehost"))
        unsaid = self.m.summon("close", "demo")
        self.assertEqual(unsaid.ending, "waiting")
        self.assertEqual(len(self.m.journal(run)), before, "a close with no word recorded something")
        self.assertIn(run, self.m.open_runs().values())
        closed = self.m.summon("close", "demo", "--word", "close")
        self.assertEqual(closed.ending, "closed")
        self.assertEqual(kinds(self.m.journal(run)[before:]), [("run-end", "closed")])
        self.assertEqual(len(self.m.calls("fakehost")), calls)
        self.assertEqual(self.m.open_runs(), {})
        again = self.m.summon("resume", "demo", "--run", run, "--position", before + 1, "--word", "go on")
        self.assertEqual(again.ending, "refused")
        self.assertEqual(again.lines, [texts.CLOSED_NEVER_RESUMES])


class TheChannel(SecretCase):
    """SEC-12's test line: "The go" and "The hosting token"; SEC-9's; RUN-2's names."""

    def test_SEC12_the_go_a_token_equal_to_a_saved_description_records_no_go_and_opens_no_run(self):
        token = harness.canary("go-token")
        rowlib.install(self.m, rowlib.lane("sunrise", [rowlib.check()]))
        looked = self.m.look("demo", inputs=self.m.inputs(description=token))
        self.assertEqual(looked.ending, "preview")
        went = self.m.go(looked, env={"FAKEHOST_TOKEN": token})
        self.assertEqual(went.ending, "refused", went.text)
        self.assertEqual(went.lines, [texts.DISPROVED_BEFORE_GO])
        self.assertNowhere(token, went)
        run = looked.doc["run"]
        self.assertEqual(self.m.journal(run), [], "a journal record was written before a first go")
        self.assertEqual(self.m.open_runs(), {})
        form = open(went.doc["forms"][0]).read()
        self.assertIn(texts.WITHHELD, form)
        self.assertNotIn(token, form)
        fresh = self.m.look("demo", inputs=self.m.inputs(description="another description"))
        self.assertEqual(fresh.ending, "preview")
        self.assertNotEqual(fresh.doc["run"], run, "the next summons did not start a new look")

    def test_SEC12_the_hosting_token_found_in_a_saved_description_is_withheld_in_the_next_status_form_then_on_record(self):
        token = harness.canary("later-token")
        rowlib.install(self.m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]))
        looked, went = self.m.started(inputs=self.m.inputs(description="it mentions " + token))
        run = looked.doc["run"]
        before = len(self.m.journal(run))
        status = self.m.summon("status", env={"FAKEHOST_TOKEN": token})
        form = open(status.doc["forms"][0]).read()
        self.assertNotIn(token, form)
        self.assertIn(texts.WITHHELD, form)
        self.assertNowhere(token, status)
        new = self.m.journal(run)[before:]
        self.assertEqual(kinds(new)[:1], [("disproof", "")])
        self.assertEqual(new[0]["rests"]["content"]["file"], "inputs.json")
        data = open(os.path.join(self.m.facts.run_dir(run), "inputs.json"), "rb").read()
        span = new[0]["rests"]["content"]
        self.assertEqual(data[span["start"]:span["end"]].decode(), token, "the record's span does not hold the value")
        self.assertNotIn(token, json.dumps(new[0]))
        copies = [rel for rel, (kind, _m, _d) in self.m.snapshot(".sun-v2").items()
                  if kind == "file" and token in open(os.path.join(self.m.home, ".sun-v2", rel), errors="replace").read()]
        # what was rendered before the disproof keeps what it held (SEC-12); nothing written after it holds the value
        self.assertEqual(sorted(os.path.basename(c) for c in copies), ["inputs.json", "manifest-1.json", "preview-1.txt", "status-1.txt"],
                         "a new copy of the channel secret was written")

    def test_SEC9_RUN2_a_name_or_an_input_that_holds_the_token_is_refused_and_stored_nowhere(self):
        token = harness.canary("name-token")
        rowlib.install(self.m, rowlib.lane("sunrise", [rowlib.check()]))
        before = self.m.snapshot()
        for label, argv in (("the name", ["look", "--kind", "sunrise", "--name", token, "--inputs", self.m.inputs()]),
                            ("a further name", ["look", "--kind", "sunrise", "--name", "demo", "--also", token, "--inputs", self.m.inputs()])):
            with self.subTest(carried_as=label):
                refused = self.m.run(*argv, env={"FAKEHOST_TOKEN": token})
                self.assertEqual((refused.ending, refused.lines), ("refused", [texts.NAME_REFUSED]))
                self.assertNowhere(token, refused)
                self.assertEqual(self.m.snapshot(), before, "a refused name left something in the fixture home")
        described = self.m.look("demo", inputs=self.m.inputs(description="holds " + token), env={"FAKEHOST_TOKEN": token})
        self.assertEqual(described.ending, "refused")
        self.assertEqual(described.lines, [texts.INPUT_REFUSED])
        typed_password = harness.canary("pw-in-description")     # built at run time (SEC-11; the contract's section 3)
        address = self.m.look("demo", inputs=self.m.inputs(description="postgres://user:" + typed_password + "@db.invalid/x"))
        self.assertEqual(address.lines, [texts.INPUT_REFUSED])
        for rel, (kind, _m, _d) in self.m.snapshot().items():
            if kind == "file":
                text = open(os.path.join(self.m.home, rel), errors="replace").read()
                self.assertNotIn(token, text, rel)
                self.assertNotIn(typed_password, text, rel)
        fine = self.m.look("demo", inputs=self.m.inputs(description="a plain description"))
        self.assertEqual(fine.ending, "preview")
        manifest = json.load(open(os.path.join(self.m.facts.run_dir(fine.doc["run"]), "manifest-1.json")))
        self.assertEqual(manifest["inputs"]["description"], "a plain description")


if __name__ == "__main__":
    unittest.main()
