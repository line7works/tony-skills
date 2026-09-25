"""`request` (lane contract section 4, required test 5; family I1), through the real CLI.

A packet directory holding anything but its three named files (a summary, a prior verdict, repo
code, a dotfile, an empty file, a folder) is refused with the file named and nothing built; so is
a packet file whose bytes moved after `packet`. The clean packet's requests carry the three files
and the fixed mandates verbatim; `authorized` only where the input's owner word names the outside
row; a Claude row never carries it; `readers validate` accepts each Claude request; a displayed
model that `suggest` no longer shows stops the run `model-changed` and builds nothing.
"""
import json
import os
import subprocess
import unittest

import ilib
import testlib

testlib.add_scripts_to_path()

from inspect_core import mandates  # noqa: E402

NEEDS = testlib.checkout_sibling("blueprint-v2") is None or testlib.records_root() is None or \
    testlib.checkout_sibling("readers") is None


@unittest.skipIf(NEEDS, "the installed shape: no blueprint-v2, records or readers beside this core")
class _Req(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("request-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = ilib.workspace(self.tmp)
        self.run = ilib.Runner(self.tmp, self.ws)

    def requests(self):
        return self.run.artifact("requests.json")["calls"]

    def request_doc(self, call):
        return testlib.load_json(call["request_file"])


class ThePacketRule(_Req):

    def plant(self, name, text, folder=False):
        self.run.upto("packet")
        for entry in self.run.artifact("packet.json")["dirs"]:
            path = os.path.join(entry["dir"], name)
            if folder:
                os.makedirs(path)
            else:
                testlib.write_text(path, text)
        code, doc, out, err = self.run.phase("request")
        return code, doc, out, err

    def assert_refused(self, name, code, doc, out, err):
        self.assertEqual(code, 5, out + err)
        self.assertFalse(doc["accepted"])
        self.assertIn(name, json.dumps(doc["refusals"]))
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "requests.json")))
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "requests")))
        self.assertEqual(self.run.artifact("checkpoint.json")["phase"], "packeted")

    def test_a_summary_file(self):
        self.assert_refused("summary.md", *self.plant("summary.md", "1: A summary of the discussion.\n"))

    def test_a_prior_verdict(self):
        self.assert_refused("prior-verdict.md", *self.plant("prior-verdict.md", "1: Verdict: APPROVED\n"))

    def test_a_repo_file(self):
        self.assert_refused("turnstile.py", *self.plant("turnstile.py", "1: def spin(count):\n"))

    def test_a_dotfile_an_empty_file_and_a_folder(self):
        self.assert_refused(".notes", *self.plant(".notes", "x\n"))

    def test_an_empty_file(self):
        self.assert_refused("empty.md", *self.plant("empty.md", ""))

    def test_a_folder(self):
        self.assert_refused("more", *self.plant("more", None, folder=True))

    def test_a_packet_file_whose_bytes_moved(self):
        self.run.upto("packet")
        target = os.path.join(self.run.artifact("packet.json")["dirs"][0]["dir"], "build-doc.md")
        testlib.write_text(target, "1: a summary instead of the record\n")
        code, doc, out, err = self.run.phase("request")
        self.assert_refused("build-doc.md", code, doc, out, err)

    def test_a_missing_file(self):
        self.run.upto("packet")
        os.remove(os.path.join(self.run.artifact("packet.json")["dirs"][1]["dir"], "code-book.md"))
        code, doc, out, err = self.run.phase("request")
        self.assert_refused("code-book.md", code, doc, out, err)


class TheCleanPacket(_Req):

    def test_the_claude_lane_three_calls(self):
        code, doc, out, err = self.run.upto("request", doc=ilib.make_input(
            self.ws, self.run.run_dir, session_model="claude-test-model"))
        self.assertEqual(code, 0, out + err)
        calls = self.requests()
        self.assertEqual([c["lens"] for c in calls], ["traceability", "code-book", "repo-reality"])
        self.assertEqual([c["call_id"] for c in calls],
                         ["run-0001-traceability", "run-0001-code-book", "run-0001-repo-reality"])
        want_docs = {"traceability": ["build-doc.md", "scope-doc.md"],
                     "code-book": ["code-book.md", "build-doc.md"], "repo-reality": ["build-doc.md"]}
        for call in calls:
            req = self.request_doc(call)
            self.assertEqual([os.path.basename(d) for d in req["documents"]], want_docs[call["lens"]])
            self.assertEqual(req["mandate"], mandates.CLAUDE[call["lens"]] + "\n\n" + mandates.REPORTING)
            self.assertNotIn("authorized", req)
            self.assertNotIn("floor", req, "v1 inspect sends no floor")
            self.assertEqual(req["session_model"], "claude-test-model")
            self.assertEqual(req["protocol_version"], 1)
            self.assertEqual(req["run_dir"], os.path.join(self.run.run_dir, "readers"))
            for path in req["documents"]:
                self.assertTrue(path.startswith(self.run.run_dir + os.sep))
            if call["lens"] == "repo-reality":
                self.assertEqual((req["profile"], req["workspace"]), ("repo", self.ws))
            else:
                self.assertEqual(req["profile"], "packet-only")
                self.assertNotIn("workspace", req)

    def test_the_outside_lane_with_the_owner_word(self):
        doc = ilib.make_input(self.ws, self.run.run_dir, row="gpt-astra",
                              owner_word={"rows": ["gpt-astra"], "words": "send it to gpt-astra"})
        code, out_doc, out, err = self.run.upto("request", doc=doc)
        self.assertEqual(code, 0, out + err)
        calls = self.requests()
        self.assertEqual([(c["lens"], c["row"]) for c in calls], [("paper", "gpt-astra"), ("repo-reality", "claude-session")])
        paper = self.request_doc(calls[0])
        self.assertIs(paper["authorized"], True)
        self.assertEqual(paper["mandate"], mandates.OUTSIDE_LINE)
        self.assertEqual(paper["call_id"], "run-0001-gpt-astra")
        self.assertEqual([os.path.basename(d) for d in paper["documents"]], ["packet.md"])
        self.assertEqual(paper["raw_path"], os.path.join(
            self.ws, "docs", "reviews", "%s-inspect-turnstile-gpt.md" % ilib.TODAY))
        body = testlib.read_text(paper["documents"][0])
        self.assertNotIn("[CODE_BOOK]", body)
        self.assertIn(ilib.numbered(ilib.BUILD_DOC), body)
        self.assertIn(ilib.numbered(ilib.SCOPE_DOC), body)
        self.assertTrue(body.startswith("# Plan-check mandate"))
        self.assertNotIn("authorized", self.request_doc(calls[1]))
        self.assertEqual(self.request_doc(calls[1])["call_id"], "run-0001-repo-reality")

    def test_an_outside_row_without_the_word_is_not_authorized(self):
        doc = ilib.make_input(self.ws, self.run.run_dir, row="gpt-astra",
                              owner_word={"rows": ["gemini"], "words": "gemini only"})
        code, out_doc, out, err = self.run.upto("request", doc=doc)
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("authorized", self.request_doc(self.requests()[0]))
        self.assertFalse(self.requests()[0]["authorized"])

    def test_a_claude_row_named_in_the_word_is_still_not_authorized(self):
        doc = ilib.make_input(self.ws, self.run.run_dir,
                              owner_word={"rows": ["claude-session"], "words": "claude it"})
        code, out_doc, out, err = self.run.upto("request", doc=doc)
        self.assertEqual(code, 0, out + err)
        self.assertTrue(all("authorized" not in self.request_doc(c) for c in self.requests()))

    def test_report_only_files_no_raw_copy(self):
        doc = ilib.make_input(self.ws, self.run.run_dir, row="gpt-astra", report_only=True,
                              owner_word={"rows": ["gpt-astra"], "words": "send it"})
        code, out_doc, out, err = self.run.upto("request", doc=doc)
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("raw_path", self.request_doc(self.requests()[0]))

    def test_readers_validate_accepts_each_claude_request(self):
        entry = testlib.readers_entry()
        if entry is None:
            self.skipTest("no readers entry beside this core")
        code, doc, out, err = self.run.upto("request", doc=ilib.make_input(
            self.ws, self.run.run_dir, session_model="claude-test-model"))
        self.assertEqual(code, 0, out + err)
        for call in self.requests():
            proc = subprocess.run([entry, "validate", call["request_file"]], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=testlib.base_env())
            self.assertEqual(proc.stdout.decode().strip(), "valid",
                             "%s: %s %s" % (call["lens"], proc.stdout.decode(), proc.stderr.decode()))


class TheSuggestCheck(_Req):

    def suggest(self, model):
        path = os.path.join(self.tmp, "suggest.json")
        testlib.write_json(path, {"run_id": "run-0001", "suggestions": [
            {"row": "gpt-astra", "model": model, "source": "roster default"}]})
        return path

    def input(self):
        return ilib.make_input(self.ws, self.run.run_dir, row="gpt-astra", displayed_model="gpt-shown",
                               owner_word={"rows": ["gpt-astra"], "words": "send it"})

    def test_another_model_than_the_one_displayed_stops_and_builds_nothing(self):
        self.run.upto("packet", doc=self.input())
        code, doc, out, err = self.run.phase("request", "--suggest", self.suggest("gpt-other"))
        self.assertEqual(code, 10, out + err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "model-changed"))
        self.assertIn("gpt-shown", doc["reason"])
        self.assertIn("gpt-other", doc["reason"])
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "requests.json")))

    def test_the_same_model_proceeds(self):
        self.run.upto("packet", doc=self.input())
        code, doc, out, err = self.run.phase("request", "--suggest", self.suggest("gpt-shown"))
        self.assertEqual(code, 0, out + err)

    def test_a_displayed_model_needs_the_suggest_file(self):
        self.run.upto("packet", doc=self.input())
        code, doc, out, err = self.run.phase("request")
        self.assertEqual(code, 2, out + err)
        self.assertIn("--suggest", err)


if __name__ == "__main__":
    unittest.main()
