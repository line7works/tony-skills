"""`readers_request.py` (required test 10): a `readers` request from the input and the documents.

`authorized` is set only from the input's owner-word field, never on a row whose provider is
`anthropic`, and never from anything but this run's input; `session_model` rides on
`claude-session` only; the built request validates with `readers validate` through the readers
shell entry of this checkout (no dispatch, nothing written). The roster used for the provider
look-up is the checkout's when there is one, a synthetic one otherwise.
"""
import json
import os
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()

from station_core import readers_request as rr  # noqa: E402

SYNTHETIC_ROSTER = {"protocol_version": 1, "rows": [
    {"id": "claude-session", "provider": "anthropic"},
    {"id": "claude-opus-cli", "provider": "anthropic"},
    {"id": "gpt-astra", "provider": "openai"},
    {"id": "gemini", "provider": "google"},
]}


class _Req(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("readers-request-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.doc = os.path.join(self.tmp, "scope-doc.md")
        testlib.write_text(self.doc, "# W \u2014 scope doc (2026-09-20)\n\nIntent: x\n")
        self.roster = SYNTHETIC_ROSTER
        self.input = testlib.make_input(self.tmp, os.path.join(self.tmp, "run"))

    def build(self, row, input_doc=None, **kw):
        kw.setdefault("mandate", "read this scope doc: what is unclear?")
        kw.setdefault("documents", [self.doc])
        kw.setdefault("profile", "starved")
        kw.setdefault("run_id", "run-0001")
        kw.setdefault("call_id", "run-0001-%s" % row)
        return rr.build(row, input_doc or self.input, self.roster, **kw)


class Authorized(_Req):

    def test_an_outside_row_the_owner_word_names(self):
        doc = dict(self.input, owner_word={"rows": ["gpt-astra"], "words": "send it to gpt-astra"})
        self.assertIs(self.build("gpt-astra", doc)["authorized"], True)

    def test_an_outside_row_with_no_owner_word(self):
        self.assertNotIn("authorized", self.build("gpt-astra"))

    def test_an_outside_row_the_owner_word_does_not_name(self):
        doc = dict(self.input, owner_word={"rows": ["gemini"], "words": "gemini please"})
        self.assertNotIn("authorized", self.build("gpt-astra", doc))

    def test_never_on_an_anthropic_row_even_when_named(self):
        doc = dict(self.input, owner_word={"rows": ["claude-session", "claude-opus-cli"],
                                           "words": "send it"})
        for row in ("claude-session", "claude-opus-cli"):
            self.assertNotIn("authorized", self.build(row, doc, session_model="claude-opus-5"))

    def test_no_keyword_can_set_it(self):
        with self.assertRaises(TypeError):
            rr.build("gpt-astra", self.input, self.roster, mandate="m", documents=[self.doc],
                     profile="starved", run_id="r", call_id="c", authorized=True)

    def test_nothing_is_remembered_between_calls(self):
        doc = dict(self.input, owner_word={"rows": ["gpt-astra"], "words": "yes gpt-astra"})
        self.assertIs(self.build("gpt-astra", doc)["authorized"], True)
        self.assertNotIn("authorized", self.build("gpt-astra"))

    def test_an_unknown_row_is_refused(self):
        with self.assertRaises(rr.RequestRefused):
            self.build("no-such-row")


class Fields(_Req):

    def test_the_request_fields(self):
        req = self.build("claude-session", session_model="claude-opus-5")
        self.assertEqual(req["protocol_version"], 1)
        self.assertEqual(req["row"], "claude-session")
        self.assertEqual(req["documents"], [self.doc])
        self.assertEqual(req["session_model"], "claude-opus-5")
        self.assertTrue(set(req) <= set(rr.REQUEST_FIELDS), sorted(req))

    def test_session_model_only_on_claude_session(self):
        req = self.build("gpt-astra", session_model="claude-opus-5")
        self.assertNotIn("session_model", req)

    def test_a_workspace_request(self):
        req = self.build("claude-session", documents=None, workspace=self.tmp, profile="repo",
                         session_model="claude-opus-5")
        self.assertEqual(req["workspace"], self.tmp)
        self.assertNotIn("documents", req)

    def test_documents_or_workspace_is_required(self):
        with self.assertRaises(rr.RequestRefused):
            self.build("claude-session", documents=None)

    def test_an_unknown_profile_is_refused(self):
        with self.assertRaises(rr.RequestRefused):
            self.build("claude-session", profile="everything")


@unittest.skipIf(testlib.readers_entry() is None,
                 "no readers component beside this core (the installed shape): the request is "
                 "validated through the readers shell entry in the checkout only")
class ValidatesWithReaders(_Req):

    def setUp(self):
        _Req.setUp(self)
        self.roster = rr.load_roster(testlib.readers_roster())

    def validate(self, req):
        path = os.path.join(self.tmp, "request.json")
        testlib.write_json(path, req)
        env = testlib.base_env({"READERS_CHECKOUT": os.path.join(self.tmp, "no-checkout"),
                                "READERS_RUN_ROOT": os.path.join(self.tmp, "runs")})
        proc = subprocess.run(["/bin/sh", testlib.readers_entry(), "validate", path], env=env,
                              cwd=self.tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "runs")), "validate writes nothing")
        return proc.returncode, proc.stdout.decode().strip()

    def test_a_claude_session_request_is_valid(self):
        self.assertEqual(self.validate(self.build("claude-session", session_model="claude-opus-5")),
                         (0, "valid"))

    def test_an_outside_request_with_the_word_is_valid(self):
        doc = dict(self.input, owner_word={"rows": ["gemini"], "words": "gemini, send it"})
        self.assertEqual(self.validate(self.build("gemini", doc)), (0, "valid"))

    def test_an_outside_request_without_the_word_is_unauthorized(self):
        self.assertEqual(self.validate(self.build("gemini")), (1, "unauthorized"))


if __name__ == "__main__":
    unittest.main()
