"""SEC-4: what a provider's result may carry. The parser alone (`sun_core/results.py`), on answers a
test writes by hand; the same rule through a whole run is in `test_secrets_end_to_end.py`.

Frame lines answered: SEC-4's table of dispositions and of the ten types; "An undeclared field is
dropped ... nothing kept, but for one thing: a secret"; the least length (the owner's ruling, A34);
the reviewer's U3 closing rule; the reviewer's D16 row for SEC-4 (a syntactically valid id declared
with credential meaning; an echo field before the secret field, in both field orders).
"""
import json
import unittest

import harness
from sun_core import results, screen

LEAST = 8


def decl(fields, **more):
    base = {"tool": "fakehost", "exits": {"0": "success", "3": "not-found", "4": "conflict", "6": "terms"},
            "fields": fields, "definite": {"success": ["success"], "refusals": ["conflict", "not-found"]},
            "alternatives": ["terms"]}
    base.update(more)
    return base


def field(name, kind, disposition, **more):
    out = {"name": name, "place": [name], "type": kind, "disposition": disposition, "required_in": ["success"]}
    out.update(more)
    return out


def parse(declaration, answer, code=0, register=None, text=None):
    register = register if register is not None else screen.Screen()
    raw = results.Raw(code, (text if text is not None else json.dumps(answer)).encode("utf-8"))
    parser = results.Parser(declaration, raw, register)
    secrets = list(parser.secrets())
    for found in secrets:
        if found.outcome == "kept":
            register.add(found.raw, found.components, None, "secret field")
    return parser.finish(), secrets, register


class TenTypes(harness.Case):
    def test_SEC4_a_fresh_value_in_each_of_the_ten_types_is_malformed_or_held_and_never_kept_as_text(self):
        fresh = harness.canary("fresh")
        fixed_types = {"kind": {}, "state": {"list": ["active", "paused"]}, "flag": {}}
        for kind, more in fixed_types.items():
            with self.subTest(type=kind):
                result, _s, _r = parse(decl([field("f", kind, "fixed", **more)]), {"f": fresh})
                self.assertEqual(result.kind, "malformed")
                self.assertEqual(result.fields, {})
        with self.subTest(type="exit"):
            result, _s, _r = parse(decl([]), {}, code=77)
            self.assertEqual(result.kind, "malformed")
        held = {"count": 123456789, "time": "2026-01-01T00:00:00Z", "id": fresh, "name": fresh,
                "hash": "a" * 40, "address": "https://example.invalid/" + fresh}
        more = {"time": {"form": r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$"}, "id": {"alphabet": "a-z0-9", "max_length": 64},
                "name": {"alphabet": "a-z0-9._-", "max_length": 64}, "hash": {"form": "^[0-9a-f]{40}$"},
                "count": {"equals": {"literal": 5}}, "address": {"equals": {"literal": "https://example.invalid/built"}}}
        dispositions = {"count": "equal", "time": "held", "id": "held", "name": "held", "hash": "held", "address": "equal"}
        for kind, value in held.items():
            with self.subTest(type=kind):
                result, _s, _r = parse(decl([field("f", kind, dispositions[kind], **more.get(kind, {}))]), {"f": value})
                self.assertEqual(result.kind, "success")
                kept = result.fields["f"]
                self.assertTrue(kept.is_held, "a value no ground proved was not held")
                self.assertNotIn(str(value), json.dumps(result.safe()), "the value is in what the result keeps as safe")
                if dispositions[kind] == "equal":
                    self.assertIs(kept.equal, False)

    def test_SEC4_each_ground_is_shown_to_work(self):
        result, _s, _r = parse(decl([field("s", "state", "fixed", list=["active", "paused"])]), {"s": "active"})
        self.assertEqual(result.safe()["s"], "active")
        sent = decl([field("n", "name", "equal", alphabet="a-z0-9-", max_length=40, equals_value="tide-table")])
        result, _s, _r = parse(sent, {"n": "tide-table"})
        self.assertEqual(result.safe()["n"], "tide-table")
        self.assertIs(result.fields["n"].equal, True)
        result, _s, _r = parse(sent, {"n": "other-name"})
        self.assertIs(result.fields["n"].equal, False)
        self.assertTrue(result.fields["n"].is_held)
        self.assertEqual(result.safe()["n"], results.DIFFERS)
        counted = decl([field("c", "count", "equal", equals_value=3)])
        self.assertEqual(parse(counted, {"c": 3})[0].safe()["c"], 3)
        account = decl([field("a", "name", "equal", alphabet="a-z0-9-", max_length=40, equals_value=["fixture-account"])])
        self.assertEqual(parse(account, {"a": "fixture-account"})[0].safe()["a"], "fixture-account")
        other = parse(account, {"a": "someone-else"})[0]
        self.assertNotIn("someone-else", json.dumps(other.safe()))

    def test_SEC4_no_ground_proves_a_value_that_holds_a_register_entry(self):
        register = screen.Screen()
        register.add("tide-table", (), "disproof 4", "disproof")
        sent = decl([field("n", "name", "equal", alphabet="a-z0-9-", max_length=40, equals_value="tide-table")])
        result, _s, _r = parse(sent, {"n": "tide-table"}, register=register)
        self.assertTrue(result.fields["n"].is_held)
        self.assertNotIn("tide-table", json.dumps(result.safe()))
        fixed = decl([field("s", "state", "fixed", list=["tide-table", "paused"])])
        result, _s, _r = parse(fixed, {"s": "tide-table"}, register=register)
        self.assertNotIn("tide-table", json.dumps(result.safe()))

    def test_SEC4_undeclared_dropped_mistyped_and_missing_required_malformed_optional_may_be_absent(self):
        d = decl([field("s", "state", "fixed", list=["active"]), field("c", "count", "held", required_in=[])])
        result, _s, _r = parse(d, {"s": "active", "extra": "dropped"})
        self.assertEqual(result.kind, "success")
        self.assertEqual(sorted(result.fields), ["s"])
        self.assertEqual(parse(d, {"s": "active", "c": "not a number"})[0].kind, "malformed")
        self.assertEqual(parse(d, {"s": "active", "c": "not a number"})[0].fields, {})
        self.assertEqual(parse(d, {})[0].kind, "malformed")
        self.assertEqual(parse(d, {"s": "active"})[0].kind, "success")

    def test_SEC4_definite_and_indefinite_results(self):
        d = decl([field("s", "state", "fixed", list=["active"], required_in=["success"])])
        self.assertEqual(parse(d, {"s": "active"})[0].definite, "success")
        self.assertEqual(parse(d, {}, code=4)[0].definite, "refusal")
        self.assertEqual(parse(d, {}, code=4)[0].kind, "conflict")
        terms = parse(d, {}, code=6)[0]
        self.assertEqual((terms.kind, terms.definite, terms.alternative), ("terms", "refusal", True))
        self.assertIsNone(parse(d, {}, code=77)[0].definite)
        self.assertIsNone(results.Parser(d, results.Raw(None, b"", timed_out=True), screen.Screen()).finish().definite)
        self.assertEqual(results.Parser(d, results.Raw(None, b"", timed_out=True), screen.Screen()).finish().kind, "timeout")
        self.assertEqual(results.Parser(d, results.Raw(0, b"", oversize=True), screen.Screen()).finish().kind, "malformed")


SECRET = field("token", "id", "secret", alphabet="a-z0-9", max_length=64)
OTHER = field("state", "state", "fixed", list=["issued"])


class Custody(harness.Case):
    """U3 and A34: a value at a secret field's place is the tool's to keep, whatever the rest is."""

    def test_SEC4_U3_a_valid_secret_beside_an_absent_and_beside_a_failing_required_field(self):
        secret = "s" + harness.canary("u3")[-20:]
        for label, answer in (("absent", {"token": secret}), ("failing", {"token": secret, "state": "not-on-the-list"})):
            with self.subTest(other_field=label):
                result, secrets, register = parse(decl([OTHER, SECRET]), answer)
                self.assertEqual(result.kind, "malformed")
                self.assertEqual(result.fields, {}, "another field of a malformed result was kept")
                self.assertEqual([(s.outcome, s.raw, s.passed) for s in secrets], [("kept", secret, True)])
                self.assertTrue(register.holds("x" + secret + "y"))

    def test_SEC4_D8U_a_secret_at_its_place_beside_an_exit_the_declaration_does_not_list_is_read_and_the_result_stays_malformed(self):
        """SEC-4's type table, the exit row: safe where "the declaration lists that exit value and maps it to a kind or an
        outcome"; and "a fixed field off its list ... turns the whole result into kind `malformed` with nothing kept, but for
        one thing: a secret. A value at a secret field's place stays in the tool's custody whatever becomes of the rest of the
        result". An exit the declaration does not list is a fixed field off its list (A139, A140): the structured answer is
        read for its secret fields' places, and for those alone, and the result is `malformed` with nothing else kept. Where
        nothing stands at the place, "the receipt says that the result held no such value"; an answer that is not well-formed
        is read as it is beside an exit the declaration lists."""
        secret = "s" + harness.canary("d8u")[-20:]
        unlisted = 7
        self.assertNotIn(str(unlisted), decl([OTHER, SECRET])["exits"])
        result, secrets, register = parse(decl([OTHER, SECRET]), {"token": secret, "state": "issued"}, code=unlisted)
        self.assertEqual(result.kind, "malformed")
        self.assertEqual(result.fields, {}, "a field of a malformed result was kept")
        self.assertEqual([(s.outcome, s.raw, s.passed) for s in secrets], [("kept", secret, True)], "the secret at its place was not read")
        self.assertTrue(register.holds("x" + secret + "y"))
        for label, text in (("nothing at the place", json.dumps({"state": "issued"})), ("an answer that is not well-formed", "not json {")):
            for code in (unlisted, 0):
                with self.subTest(answer=label, exit="unlisted" if code == unlisted else "listed"):
                    result, secrets, register = parse(decl([OTHER, SECRET]), None, code=code, text=text)
                    self.assertEqual(result.kind, "malformed")
                    self.assertEqual([s.outcome for s in secrets], [results.NO_VALUE])
                    self.assertEqual(register.entries, [])

    def test_SEC4_D8M_a_complete_secret_member_before_the_damage_of_an_answer_is_read_from_its_place_and_kept(self):
        """The reviewer's D8-M (check 3, `custody.py`, "broken-tail"): `{"token": "<value>", "state":` failed to decode whole
        and the secret at its place got the receipt that the result held no such value. SEC-4: "A value at a secret field's
        place stays in the tool's custody whatever becomes of the rest of the result"; "The frame reads a field only from its
        declared place, never by searching the tool's text". The owner's pick (brief-27, item 3): "The tool pulls the
        complete secret out of the damaged reply and protects it like any other." So a declared secret field whose place is
        a top-level member of that name, whose value is a complete JSON string before the damage, is read from that place,
        member by member as the decoder reads, and kept as from a whole answer; nothing else of the result is kept and the
        result stays `malformed`; where no such member stands, the receipt stays as it was."""
        secret = "s" + harness.canary("d8m")[-20:]
        kept = (
            ("the reviewer's broken tail", '{"token": %s, "state":' % json.dumps(secret)),
            ("after a whole member of another name", '{"state": "issued", "token": %s, "more": [1, ' % json.dumps(secret)),
            ("the answer cut short just after the member", '{"token": %s' % json.dumps(secret)),
            ("damage that is no JSON after the member", '{"token": %s, "state": issued}' % json.dumps(secret)),
        )
        for label, text in kept:
            for code in (0, 7):
                with self.subTest(answer=label, exit="listed" if code == 0 else "unlisted"):
                    result, secrets, register = parse(decl([OTHER, SECRET]), None, code=code, text=text)
                    self.assertEqual(result.kind, "malformed")
                    self.assertEqual(result.fields, {}, "a field of a damaged result was kept")
                    self.assertEqual([(s.outcome, s.raw, s.passed) for s in secrets], [("kept", secret, True)],
                                     "the complete secret before the damage was not read from its place")
                    self.assertTrue(register.holds("x" + secret + "y"))
        with self.subTest(answer="bytes that are not UTF-8 after the member"):
            raw = results.Raw(0, ('{"token": %s, "state": "' % json.dumps(secret)).encode("utf-8") + b"\xff\xfe")
            parser = results.Parser(decl([OTHER, SECRET]), raw, screen.Screen())
            self.assertEqual([(s.outcome, s.raw) for s in parser.secrets()], [("kept", secret)])
            self.assertEqual(parser.finish().kind, "malformed")
        with self.subTest(answer="a failing value before the damage, at the least length"):
            result, secrets, register = parse(decl([OTHER, SECRET]), None, text='{"token": "%s", "state":' % ("A" * LEAST))
            self.assertEqual([(s.outcome, s.raw, s.passed) for s in secrets], [("kept", "A" * LEAST, False)])
            self.assertEqual(result.kind, "malformed")
        not_kept = (
            ("not json {", "not json {"),
            ("a member whose string the damage cuts off", '{"token": "%s' % secret),
            ("a member whose string the damage cuts off inside an escape", '{"token": "%s\\' % secret),
            ("the member after the damage", '{"state": , "token": %s}' % json.dumps(secret)),
            ("a value-shaped string under another name", '{"other": %s, "state":' % json.dumps(secret)),
            ("the secret's name as a value, not a member", '["token", %s, ' % json.dumps(secret)),
        )
        for label, text in not_kept:
            with self.subTest(answer=label):
                result, secrets, register = parse(decl([OTHER, SECRET]), None, code=7, text=text)
                self.assertEqual(result.kind, "malformed")
                self.assertEqual([s.outcome for s in secrets], [results.NO_VALUE], "a value was kept that stands at no complete place")
                self.assertEqual(register.entries, [])

    def test_SEC4_V1_a_value_ending_in_one_line_break_fails_its_alphabet_and_a_plain_value_still_passes(self):
        """The reviewer's V1 (check 3): the validator applied an alphabet as `^[...]+$`, and `$` passes one line break at the
        end, so a secret id's value ending in one line break passed `a-z0-9`. SEC-4's id row: "the provider's identifier: an
        alphabet and a length limit the module registers"; "A declared field that fails its validator ... turns the whole
        result into kind `malformed` with nothing kept, but for one thing: a secret"; "A failing value at the least length or
        over is kept whole, as it was read, in its protected record", and the register holds "the value without the white
        space at its ends, where that differs"; a failing value under the least length is dropped."""
        plain = "s" + harness.canary("v1")[-20:]
        self.assertTrue(results._valid(SECRET, plain))
        self.assertFalse(results._valid(SECRET, plain + "\n"), "a value ending in a line break passed an alphabet that holds none")
        with self.subTest(value="a secret's value ending in one line break, at the least length or over"):
            result, secrets, register = parse(decl([OTHER, SECRET]), {"token": plain + "\n", "state": "issued"})
            self.assertEqual(result.kind, "malformed")
            self.assertEqual(result.fields, {}, "a field of a malformed result was kept")
            self.assertEqual([(s.outcome, s.raw, s.passed) for s in secrets], [("kept", plain + "\n", False)])
            self.assertIn(plain, secrets[0].components, "the value without its line break is no component")
            self.assertTrue(register.holds("x" + plain + "y"))
        with self.subTest(value="a secret's value ending in one line break, under the least length once it is left out"):
            result, secrets, register = parse(decl([OTHER, SECRET]), {"token": "abc" + "\n", "state": "issued"})
            self.assertEqual(result.kind, "malformed")
            self.assertEqual([s.outcome for s in secrets], [results.DROPPED])
            self.assertEqual(register.entries, [])
        with self.subTest(value="a plain value"):
            result, secrets, register = parse(decl([OTHER, SECRET]), {"token": plain, "state": "issued"})
            self.assertEqual(result.kind, "success")
            self.assertEqual([(s.outcome, s.raw, s.passed) for s in secrets], [("kept", plain, True)])
        # every field the alphabet is applied to: a held id and an equal name, as well as a secret
        held = field("ident", "id", "held", alphabet="a-z0-9", max_length=64)
        equal = field("label", "name", "equal", alphabet="a-z0-9-", max_length=64, equals_value="tide-table")
        for label, declared, good in (("a held id", held, "abc123"), ("an equal name", equal, "tide-table")):
            with self.subTest(field=label):
                name = declared["name"]
                self.assertEqual(parse(decl([OTHER, declared]), {name: good, "state": "issued"})[0].kind, "success")
                failed = parse(decl([OTHER, declared]), {name: good + "\n", "state": "issued"})[0]
                self.assertEqual((failed.kind, failed.fields), ("malformed", {}), "%s ending in a line break passed" % label)

    def test_SEC4_A34_a_failing_value_at_the_least_length_and_five_times_it_is_kept_whole(self):
        for value in ("A" * LEAST, "B" * (5 * LEAST)):
            with self.subTest(length=len(value)):
                result, secrets, register = parse(decl([OTHER, SECRET]), {"token": value, "state": "issued"})
                self.assertEqual(result.kind, "malformed", "a secret field's failing value did not make the result malformed")
                self.assertEqual([(s.outcome, s.raw, s.passed) for s in secrets], [("kept", value, False)])
                self.assertTrue(register.holds(value))

    def test_SEC4_A34_five_failing_values_under_the_least_length_are_dropped(self):
        passes = [("one byte under", "A" * (LEAST - 1)), ("one byte", "A"), ("empty", ""),
                  ("long with its white space, one byte without", " " * 6 + "A" + " " * 6), ("a truth value", True)]
        for label, value in passes:
            with self.subTest(value=label):
                result, secrets, register = parse(decl([OTHER, SECRET]), {"token": value, "state": "issued"})
                self.assertEqual(result.kind, "malformed")
                self.assertEqual([s.outcome for s in secrets], [results.DROPPED])
                self.assertEqual(register.entries, [], "a dropped value entered the register")

    def test_SEC4_nothing_at_the_place_and_the_answers_word_for_no_value(self):
        for label, answer in (("nothing", {"state": "issued"}), ("null", {"token": None, "state": "issued"})):
            with self.subTest(place=label):
                result, secrets, register = parse(decl([OTHER, SECRET]), answer)
                self.assertEqual([s.outcome for s in secrets], [results.NO_VALUE])
                self.assertEqual(register.entries, [])
                self.assertEqual(result.kind, "malformed", "a required secret field that is missing did not make the result malformed")
        optional = dict(SECRET, required_in=[])
        result, secrets, _r = parse(decl([OTHER, optional]), {"state": "issued"})
        self.assertEqual((result.kind, [s.outcome for s in secrets]), ("success", [results.NO_VALUE]))

    def test_SEC4_white_space_at_its_ends_kept_as_read_and_held_in_both_forms(self):
        core = "A" * LEAST
        value = " " + core + " "
        result, secrets, register = parse(decl([OTHER, SECRET]), {"token": value, "state": "issued"})
        self.assertEqual([(s.outcome, s.raw) for s in secrets], [("kept", value)])
        self.assertIn(core, secrets[0].components)
        self.assertTrue(register.holds("saved:" + value))
        self.assertTrue(register.holds("saved:" + core + "!"), "the value without the white space at its ends is no entry")

    def test_SEC4_a_failing_number_of_twice_the_least_length_in_digits_is_kept_whole(self):
        digits = "12345678" * 2
        result, secrets, register = parse(decl([OTHER, SECRET]), None, text='{"state": "issued", "token": %s}' % digits)
        self.assertEqual([(s.outcome, s.raw, s.is_text) for s in secrets], [("kept", digits, False)])
        self.assertTrue(register.holds("an input of " + digits))

    def test_SEC4_a_failing_object_is_kept_whole_and_only_its_long_pieces_are_entries(self):
        long_text, short_text, number = "L" * (LEAST + 3), "shrt", 4242
        text = '{"token": {"inner": "%s", "small": "%s", "n": %d}, "state": "issued"}' % (long_text, short_text, number)
        result, secrets, register = parse(decl([OTHER, SECRET]), None, text=text)
        found = secrets[0]
        self.assertEqual(found.outcome, "kept")
        self.assertEqual(found.raw, '{"inner": "%s", "small": "%s", "n": %d}' % (long_text, short_text, number))
        self.assertTrue(register.holds("x " + long_text))
        for piece in (short_text, str(number), "inner", "small"):
            self.assertFalse(register.holds(" " + piece + " "), "%r is an entry and should be none" % piece)

    def test_SEC4_A36_one_fixture_more_a_text_in_a_list_in_an_object_at_any_depth(self):
        long_text, short = "D" * LEAST, "tiny"
        text = '{"state": "issued", "token": {"outer": [["%s", "%s", 7], {"deep": "%s"}]}}' % (short, long_text, short)
        result, secrets, register = parse(decl([OTHER, SECRET]), None, text=text)
        self.assertEqual(secrets[0].outcome, "kept")
        self.assertIn(long_text, secrets[0].components)
        self.assertTrue(register.holds("saved " + long_text + " input"))
        self.assertFalse(register.holds("saved " + short + " input"))
        self.assertFalse(register.holds("outer deep"))

    def test_SEC4_D16_an_echo_field_beside_the_secret_field_in_both_field_orders(self):
        secret = "e" + harness.canary("echo")[-20:]
        echo = field("echo", "name", "equal", alphabet="a-z0-9", max_length=64, equals_value=secret)
        for label, fields, answer in (
                ("the echo field first", [echo, SECRET], '{"echo": "%s", "token": "%s"}' % (secret, secret)),
                ("the secret field first", [SECRET, echo], '{"token": "%s", "echo": "%s"}' % (secret, secret))):
            with self.subTest(order=label):
                result, secrets, register = parse(decl(fields), None, text=answer)
                self.assertEqual(secrets[0].outcome, "kept")
                self.assertTrue(result.fields["echo"].is_held, "a value was promoted to safe while it is a secret")
                self.assertNotIn(secret, json.dumps(result.safe()))

    def test_SEC4_D16_a_syntactically_valid_id_declared_with_credential_meaning_is_sealed(self):
        valid = "abc123def456"
        result, secrets, register = parse(decl([SECRET]), {"token": valid})
        self.assertEqual([(s.outcome, s.passed) for s in secrets], [("kept", True)])
        self.assertTrue(register.holds(valid))
        self.assertNotIn(valid, json.dumps(result.safe()))


if __name__ == "__main__":
    unittest.main()
