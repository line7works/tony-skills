"""The docless set-aside (round 3 R1, CA2-1): v1's input gate in a workspace whose one scope doc is
another project's.

The scope hunt finds one scope doc; its `Intent:` line names another project, so it is not this
project's scope doc and the hunt counts as `none`: the executor asks the owner once, and his "none"
opens the docless gate. The input's `station.docless: true` (with `station.docless_reason`, the
reason the executor states, required with it) carries that into the run: `harvest` sets the single
hit aside (recorded in the scope selection as `set_aside`, with the hit's path and the reason),
never refuses the owner's working name, and the docless gate opens with that reason in the answer
and the doc's header. `several` still asks. Every case drives the real CLI.
"""
import os
import unittest

import archlib
import testlib

D = archlib.D
OTHER_REL = "docs/scope/2026-09-18-metronome.md"
OTHER = ("# Metronome %(D)s scope doc (2026-09-18)\n\n"
         "Intent: a click track for the rehearsal room, so a drummer can set a tempo by ear.\n"
         "Decisions:\n"
         "- One tempo at a time %(D)s decided (the owner's words)\n"
         "Out of scope:\n"
         "Research:\n"
         "Open:\n"
         "Next: /blueprint when ready.\n") % {"D": D}
REASON = ("the one scope doc in the repository is Metronome's; the owner said no scope doc exists for the "
          "turn counter, and wants it drawn before any precon")


def docless_answer(reason=REASON, **over):
    a = archlib.clean_answer(**over)
    a["questions"] = [{"id": "Q0", "text": "Is there a scope doc for the turn counter somewhere the glob cannot see?",
                       "touches": [], "answer": "none", "about": "scope-doc"}] + \
        [q for q in a["questions"] if q["id"] != "Q2"]
    a["poured_concrete"] = [{"text": "language %s Python 3.9 %s the bench" % (D, D), "tag": "decided",
                             "trace": {"kind": "question", "ref": "Q3"}}]
    a["deferred"] = []
    a["review"] = {"outcome": "not-offered"}
    a["docless"] = {"reason": reason, "home": "workspace"}
    return a


class _SetAside(unittest.TestCase):

    STATION = {"docless": True, "docless_reason": REASON}

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-set-aside-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.staging = os.path.join(self.tmp, "staging")
        os.makedirs(self.staging)
        self.ws = testlib.git_workspace(self.tmp, "ws", {"README.md": "# Bench\n", OTHER_REL: OTHER})
        self.run = archlib.ArchRun(self.tmp, self.ws, self.staging, station=dict(self.STATION))

    def harvested(self):
        code, doc, out, err = self.run.check_input()
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = self.run.select("scope")
        self.assertEqual((code, doc["outcome"]), (0, "one"), out + err)
        code, doc, out, err = self.run.select("architecture", "turnstile")
        self.assertEqual(code, 0, out + err)
        return self.run.harvest()


class TheHitIsSetAside(_SetAside):

    def test_harvest_opens_the_docless_gate_and_records_the_set_aside(self):
        before = archlib.listing(self.ws)
        code, doc, out, err = self.harvested()
        self.assertEqual(code, 0, out + err)
        self.assertTrue(doc["docless"])
        self.assertIsNone(doc["scope_doc"])
        self.assertEqual(doc["ledger"], [])
        self.assertEqual(doc["slug"], "turnstile")
        aside = {"path": os.path.join(self.ws, OTHER_REL), "reason": REASON}
        self.assertEqual(doc["set_aside"], aside)
        selection = testlib.load_json(os.path.join(self.run.run_dir, "selection-scope.json"))
        self.assertEqual(selection["set_aside"], aside)
        self.assertEqual(selection["outcome"], "one")
        harvest = testlib.load_json(os.path.join(self.run.run_dir, "harvest.json"))
        self.assertEqual(harvest["set_aside"], aside)
        self.assertTrue(harvest["docless"])
        self.assertEqual(archlib.listing(self.ws), before)

    def test_the_docless_answer_lands_its_reason_in_the_header_and_report_completes(self):
        self.assertEqual(self.harvested()[0], 0)
        code, doc, out, err = self.run.record(docless_answer())
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        path = os.path.join(self.ws, "docs", "architecture", "%s-turnstile.md" % archlib.TODAY)
        self.assertEqual(doc["doc"], path)
        text = testlib.read_text(path)
        self.assertEqual(text.split("\n")[2:4], ["Docless: %s" % REASON, "Blind review: none %s docless" % D])
        self.assertEqual(testlib.read_text(os.path.join(self.ws, OTHER_REL)), OTHER)
        self.assertEqual(self.run.render()[0], 0)
        self.assertEqual(self.run.publish("https://example.invalid/artifact/turnstile")[0], 0)
        code, doc, out, err = self.run.report()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["status"], "completed", out)
        self.assertTrue(doc["station_result"]["docless"])
        self.assertIsNone(doc["station_result"]["scope_doc"])
        self.assertEqual(doc["selection"]["scope"]["set_aside"]["path"], os.path.join(self.ws, OTHER_REL))
        path = os.path.join(self.run.run_dir, "result.json")
        code, out, err = testlib.run_script("validate-result.py", [path], cwd=self.run.cwd)
        self.assertEqual(code, 0, out + err)

    def test_an_answer_whose_reason_is_not_the_inputs_is_refused(self):
        self.assertEqual(self.harvested()[0], 0)
        before = archlib.listing(self.run.run_dir)
        code, doc, out, err = self.run.record(docless_answer(reason="a spike"))
        self.assertEqual(code, 5, out + err)
        self.assertIn("docless-reason-mismatch", [r["rule"] for r in doc["refusals"]])
        self.assertEqual(archlib.listing(self.run.run_dir), before)

    def test_the_gate_question_is_still_required(self):
        self.assertEqual(self.harvested()[0], 0)
        a = docless_answer()
        a["questions"] = [q for q in a["questions"] if q.get("about") != "scope-doc"]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)
        self.assertIn("docless-unasked", [r["rule"] for r in doc["refusals"]])

    def test_a_request_on_the_set_aside_run_is_usage(self):
        self.assertEqual(self.harvested()[0], 0)
        self.assertEqual(self.run.record(docless_answer())[0], 0)
        self.assertEqual(self.run.write()[0], 0)
        code, doc, out, err = self.run.request("gpt-astra")
        self.assertEqual(code, 2, out + err)


class WithoutTheFlag(_SetAside):
    """The checker's p05 shape, before the fix's flag: harvest takes the other project's doc and
    refuses the owner's working name; that stays so without `station.docless`."""

    STATION = {}

    def test_the_other_projects_slug_is_still_refused(self):
        code, doc, out, err = self.harvested()
        self.assertEqual(code, 2, out + err)
        self.assertIn("metronome", err)


class SeveralStillAsks(_SetAside):

    def test_several_stops_selection_several(self):
        testlib.write_text(os.path.join(self.ws, "docs", "scope", "2026-09-19-drum-log.md"), OTHER)
        code, doc, out, err = self.run.check_input()
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = self.run.select("scope")
        self.assertEqual((code, doc["outcome"]), (0, "several"))
        self.run.select("architecture", "turnstile")
        code, doc, out, err = self.run.harvest()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["stop_tag"], "selection-several")


class TheInputRules(unittest.TestCase):

    def check(self, station):
        tmp = testlib.make_scratch("arch-set-aside-input-")
        self.addCleanup(testlib.rmtree, tmp)
        ws = testlib.git_workspace(tmp, "ws")
        run = archlib.ArchRun(tmp, ws, station=station)
        return run.check_input()

    def test_docless_needs_its_reason(self):
        code, doc, out, err = self.check({"docless": True})
        self.assertEqual(code, 4, out + err)

    def test_docless_and_a_scope_doc_exclude_each_other(self):
        code, doc, out, err = self.check({"docless": True, "docless_reason": REASON, "scope_doc": "/abs/scope.md"})
        self.assertEqual(code, 4, out + err)

    def test_a_reason_without_docless_is_refused(self):
        code, doc, out, err = self.check({"docless_reason": REASON})
        self.assertEqual(code, 4, out + err)
        code, doc, out, err = self.check({"docless": False, "docless_reason": REASON})
        self.assertEqual(code, 4, out + err)

    def test_a_blank_reason_is_refused(self):
        code, doc, out, err = self.check({"docless": True, "docless_reason": "  "})
        self.assertEqual(code, 4, out + err)

    def test_the_set_aside_input_is_accepted(self):
        code, doc, out, err = self.check({"docless": True, "docless_reason": REASON})
        self.assertEqual(code, 0, out + err)


class TheProcedureSaysWhen(unittest.TestCase):

    def test_step_1_item_3_names_the_flag(self):
        with open(os.path.join(testlib.SKILL, "SKILL.md"), encoding="utf-8") as fh:
            skill = " ".join(fh.read().split())
        for words in ("`station.docless: true`", "`station.docless_reason`"):
            self.assertTrue(words in skill, "SKILL.md does not name %s" % words)


if __name__ == "__main__":
    unittest.main()
