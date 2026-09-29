"""precon-v2's `write` (precon-v2-contract.md section 6; required test 6 of lane P), through the real CLI.

A new doc byte-identical to `templates.render_scope_doc` (its one added line, the triage comment,
taken out) and passing `templates.check`; a continued doc whose prior lines stay byte-identical
and whose new lines land at the tail of `Decisions:`; a settled parked line rewritten in place
under its own id; a napkin run that writes nothing; the receipt's hashes; a doc changed after
harvest left as found; report-only writing nothing outside the run directory.
"""
import hashlib
import json
import os
import unittest

import preconlib
import testlib
from preconlib import D

testlib.add_scripts_to_path()
from station_core import ledger, templates  # noqa: E402

COMMENT = "<!-- precon-v2 triage: bounded -->\n"


class _Write(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("write-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.fx = preconlib.Fixture(self.tmp)

    def through_write(self, answer_fields, station=None, report_only=False):
        run = self.fx.new_run(station=station, report_only=report_only)
        run.select()
        code, doc, err = run.harvest()
        self.assertEqual(code, 0, err)
        code, doc, err = run.record(preconlib.answer(run, **answer_fields))
        self.assertEqual(code, 0, json.dumps(doc))
        code, doc, err = run.write()
        return run, code, doc, err


class NewDoc(_Write):

    def fields(self):
        return {"doc": preconlib.new_doc_fields(), "lines": [
            preconlib.owner_line("Python 3.9 standard library only", "no dependencies on the bench"),
            {"text": "One module, no package", "tag": "assumed",
             "trace": {"kind": "assumed", "ref": "small and reversible; nothing imports it yet"}},
            {"text": "Where the count is kept between sessions", "tag": "parked", "reason": "needs research",
             "trace": {"kind": "owner_words", "ref": "I need to look into storage"}},
            {"text": "Whether resets are logged", "tag": "open", "waits_on": "the owner's call on logging",
             "trace": {"kind": "owner_words", "ref": "ask me later"}}],
            "out_of_scope": [{"text": "a web dashboard", "reason": "the owner declined it for the first version",
                              "trace": {"kind": "owner_words", "ref": "no dashboard yet"}}],
            "open_items": ["how often the counter resets"]}

    def test_the_new_doc_is_the_rendered_form(self):
        run, code, doc, err = self.through_write(self.fields())
        self.assertEqual(code, 0, err)
        path = os.path.join(self.fx.ws, preconlib.SCOPE_REL)
        text = preconlib.read(path)
        self.assertEqual(text.split("\n")[1] + "\n", COMMENT)
        expected = templates.render_scope_doc(
            "Turnstile", preconlib.DATE, preconlib.new_doc_fields()["intent"],
            [templates.render_ledger_line("Python 3.9 standard library only", "decided",
                                          "the owner's words: \"no dependencies on the bench\""),
             templates.render_ledger_line("One module, no package", "assumed",
                                          "small and reversible; nothing imports it yet"),
             templates.render_ledger_line("Where the count is kept between sessions", "parked", "needs research")],
            out_of_scope=["a web dashboard %s the owner declined it for the first version" % D],
            open_items=["Whether resets are logged (waits on: the owner's call on logging)",
                        "how often the counter resets"])
        self.assertEqual(text.replace(COMMENT, "", 1), expected)
        self.assertEqual(templates.check("scope-doc", text), [])
        self.assertEqual(templates.render(templates.parse("scope-doc", text)), text)
        tags = ledger.counts(ledger.read(text))
        self.assertEqual((tags["decided"], tags["assumed"], tags["parked"], tags["open"]), (1, 1, 1, 2))

    def test_the_receipt_names_the_write_and_its_hashes(self):
        run, code, doc, err = self.through_write(self.fields())
        self.assertEqual(code, 0, err)
        path = os.path.join(self.fx.ws, preconlib.SCOPE_REL)
        receipt = testlib.load_json(run.run_file("receipt.json"))
        self.assertEqual(receipt["writes"], [{"path": path, "kind": "document", "sha256_before": None,
                                              "sha256_after": testlib.sha256_file(path)}])
        self.assertEqual(doc["writes"], receipt["writes"])

    def test_the_staging_home(self):
        run, code, doc, err = self.through_write(self.fields(), station={"home": "staging"})
        self.assertEqual(code, 0, err)
        self.assertTrue(os.path.isfile(os.path.join(self.fx.staging, "turnstile-scope.md")))
        self.assertFalse(os.path.exists(os.path.join(self.fx.ws, "docs")))

    def test_no_settled_line_writes_no_doc(self):
        run, code, doc, err = self.through_write({"open_items": ["how often the counter resets"]})
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["writes"], [])
        self.assertFalse(os.path.exists(os.path.join(self.fx.ws, "docs")))
        self.assertIn("first settled line", doc["reason"])

    def test_a_napkin_run_writes_nothing(self):
        before = testlib.tree_digest(self.fx.ws)
        run, code, doc, err = self.through_write(
            {"triage": {"tier": "napkin", "why": "one sentence", "no_scope_doc": True}})
        self.assertEqual(code, 0, err)
        self.assertEqual(doc["writes"], [])
        self.assertEqual(testlib.tree_digest(self.fx.ws), before)
        code, result, err = run.report()
        self.assertEqual((code, result["status"], result["stop_tag"]), (10, "stopped", "no-scope-doc"))

    def test_a_file_that_appeared_after_harvest_is_left_as_found(self):
        run = self.fx.new_run()
        run.select()
        run.harvest()
        self.assertEqual(run.record(preconlib.answer(run, **self.fields()))[0], 0)
        path = preconlib.ensure_scope_doc(self.fx, text="someone else's bytes\n")
        digest = testlib.sha256_file(path)
        code, doc, err = run.write()
        self.assertEqual(code, 10, err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "doc-changed"))
        self.assertEqual(testlib.sha256_file(path), digest)


class Continued(_Write):

    def setUp(self):
        _Write.setUp(self)
        self.path = preconlib.ensure_scope_doc(self.fx)
        self.before = preconlib.read(self.path)

    def test_prior_lines_identical_and_new_lines_at_the_tail_of_decisions(self):
        run, code, doc, err = self.through_write({
            "lines": [preconlib.owner_line("Counts print to stdout", "print it, nothing fancy"),
                      {"text": "Reverse turns count as negative", "tag": "parked", "reason": "needs prototype",
                       "trace": {"kind": "owner_words", "ref": "show me on the rig"}}],
            "out_of_scope": [{"text": "a phone app", "reason": "the owner declined it",
                              "trace": {"kind": "owner_words", "ref": "no phone app"}}],
            "research": ["notes/encoder-survey.md"],
            "open_items": ["who owns the bench log"]})
        self.assertEqual(code, 0, err)
        after = preconlib.read(self.path)
        old, new = self.before.split("\n"), after.split("\n")
        added = [line for line in new if line not in old]
        self.assertEqual([line for line in new if line in old], old, "every prior line, in order, byte-identical")
        self.assertEqual(added, [
            COMMENT.rstrip("\n"),
            "- Counts print to stdout %s decided (the owner's words: \"print it, nothing fancy\")" % D,
            "- Reverse turns count as negative %s parked: needs prototype" % D,
            "- a phone app %s the owner declined it" % D,
            "- notes/encoder-survey.md",
            "- who owns the bench log"])
        # the new Decisions lines sit directly above `Out of scope:`
        at = new.index("Out of scope: a web dashboard %s the owner declined it for the first version" % D)
        self.assertEqual(new[at - 2:at], added[1:3])
        self.assertEqual(templates.check("scope-doc", after), [])
        receipt = testlib.load_json(run.run_file("receipt.json"))
        self.assertEqual(receipt["writes"][0]["sha256_before"], hashlib.sha256(self.before.encode("utf-8")).hexdigest())
        self.assertEqual(receipt["writes"][0]["sha256_after"], testlib.sha256_file(self.path))

    def test_a_settled_parked_line_is_rewritten_in_place_under_its_id(self):
        q = {"id": "Q1", "text": "Where is the count kept between sessions?",
             "touches": [preconlib.PARKED_RESEARCH_ID], "answer": "in memory only"}
        run, code, doc, err = self.through_write({"questions": [q], "lines": [
            {"text": "Where the count is kept between sessions", "tag": "decided",
             "trace": {"kind": "ledger", "ref": preconlib.PARKED_RESEARCH_ID}}]})
        self.assertEqual(code, 0, err)
        after = preconlib.read(self.path)
        self.assertIn("- Where the count is kept between sessions %s decided (answer to Q1 (run %s): in memory only)"
                      % (D, run.run_id), after)
        self.assertNotIn("parked: needs research", after)
        rows = dict((r["id"], r) for r in ledger.read(after))
        self.assertEqual(rows[preconlib.PARKED_RESEARCH_ID]["tag"], "decided")
        old = [l for l in self.before.split("\n") if "needs research" not in l]
        self.assertEqual([l for l in after.split("\n") if l in old], old)

    def test_a_settled_open_item_moves_to_the_tail_of_decisions(self):
        q = {"id": "Q1", "text": "How often does the counter reset?", "touches": [preconlib.OPEN_ID],
             "answer": "at every power cycle"}
        run, code, doc, err = self.through_write({"questions": [q], "lines": [
            {"text": "how often the counter resets", "tag": "decided",
             "trace": {"kind": "ledger", "ref": preconlib.OPEN_ID}}]})
        self.assertEqual(code, 0, err)
        after = preconlib.read(self.path)
        lines = after.split("\n")
        self.assertNotIn("- how often the counter resets", lines)
        at = lines.index("Out of scope: a web dashboard %s the owner declined it for the first version" % D)
        self.assertEqual(lines[at - 1], "- how often the counter resets %s decided (answer to Q1 (run %s): at every "
                                        "power cycle)" % (D, run.run_id))

    def test_a_line_passed_forward_writes_nothing_new(self):
        run, code, doc, err = self.through_write({"lines": [
            {"text": "Python 3.9 standard library only", "tag": "decided",
             "trace": {"kind": "ledger", "ref": preconlib.DECIDED_ID}}]})
        self.assertEqual(code, 0, err)
        after = preconlib.read(self.path)
        self.assertEqual(after.replace(COMMENT, "", 1), self.before)

    def test_a_doc_edited_after_harvest_is_left_as_found(self):
        run = self.fx.new_run()
        run.select()
        run.harvest()
        answer = preconlib.answer(run, lines=[preconlib.owner_line("Counts print to stdout", "print it")])
        self.assertEqual(run.record(answer)[0], 0)
        testlib.write_text(self.path, self.before + "\n")
        digest = testlib.sha256_file(self.path)
        code, doc, err = run.write()
        self.assertEqual(code, 10, err)
        self.assertEqual((doc["status"], doc["stop_tag"]), ("stopped", "doc-changed"))
        self.assertEqual(testlib.sha256_file(self.path), digest)
        if os.path.exists(run.run_file("receipt.json")):
            self.assertEqual(testlib.load_json(run.run_file("receipt.json"))["writes"], [])

    def test_write_before_an_answer_is_usage(self):
        run = self.fx.new_run()
        run.select()
        run.harvest()
        self.assertEqual(run.write()[0], 2)


class InlineOpen(_Write):
    """CP1-2 (ruling R2): a single `Open:` item written inline, the form `render_scope_doc` writes for
    one item (precon-v2's own new docs included), settles: the label line stays as `Open:` alone,
    the form's line for zero items, and the decided line lands at the tail of `Decisions:`."""

    WAITS = "the owner's call on logging"

    def born(self):
        # run 1: precon-v2 births the doc with one open item (and one decided line, its first settled line)
        run, code, doc, err = self.through_write({"doc": preconlib.new_doc_fields(), "lines": [
            preconlib.owner_line("Python 3.9 standard library only", "no dependencies on the bench"),
            {"text": "Whether resets are logged", "tag": "open", "waits_on": self.WAITS,
             "trace": {"kind": "owner_words", "ref": "ask me later"}}]})
        self.assertEqual(code, 0, err)
        path = os.path.join(self.fx.ws, preconlib.SCOPE_REL)
        text = preconlib.read(path)
        item = "Whether resets are logged (waits on: %s)" % self.WAITS
        self.assertIn("Open: %s\n" % item, text, "one open item is written inline")
        return path, text, item

    def settle(self, item, extra=None):
        ident = preconlib.ids(preconlib.read(os.path.join(self.fx.ws, preconlib.SCOPE_REL)))[item]
        q = {"id": "Q1", "text": "Are resets logged?", "touches": [ident], "answer": "yes, to the bench log"}
        fields = {"questions": [q], "lines": [{"text": item, "tag": "decided",
                                               "trace": {"kind": "ledger", "ref": ident}}]}
        fields.update(extra or {})
        return self.through_write(fields)

    def test_a_single_inline_open_item_settles(self):
        path, before, item = self.born()
        run, code, doc, err = self.settle(item)
        self.assertEqual(code, 0, "%s %s" % (json.dumps(doc), err))
        after = preconlib.read(path)
        lines = after.split("\n")
        self.assertIn("Open:", lines, "the label line stays, empty, as the form writes zero items")
        self.assertNotIn("Open: %s" % item, lines)
        at = lines.index("Out of scope:")
        self.assertEqual(lines[at - 1], "- %s %s decided (answer to Q1 (run %s): yes, to the bench log)"
                         % (item, D, run.run_id))
        self.assertEqual(templates.check("scope-doc", after), [])
        self.assertEqual(templates.render(templates.parse("scope-doc", after)), after)
        rows = ledger.read(after)
        self.assertEqual([r["tag"] for r in rows if r["text"] == item], ["decided"])
        # every other prior line is kept byte for byte, in order
        old = [l for l in before.split("\n") if l != "Open: %s" % item]
        self.assertEqual([l for l in lines if l in old], old)

    def test_a_settled_inline_item_and_a_new_open_item_in_one_run(self):
        path, before, item = self.born()
        run, code, doc, err = self.settle(item, {"open_items": ["who owns the bench log"]})
        self.assertEqual(code, 0, "%s %s" % (json.dumps(doc), err))
        after = preconlib.read(path)
        self.assertIn("Open:\n- who owns the bench log\nNext:", after)
        self.assertEqual(templates.check("scope-doc", after), [])

    def test_a_hand_written_inline_open_item_settles_and_line_endings_are_kept(self):
        text = preconlib.SCOPE_DOC.replace("Open:\n- how often the counter resets\n",
                                           "Open: how often the counter resets\n").replace("\n", "\r\n")
        path = preconlib.ensure_scope_doc(self.fx, text=text)
        with open(path, "wb") as fh:
            fh.write(text.encode("utf-8"))
        run, code, doc, err = self.settle("how often the counter resets")
        self.assertEqual(code, 0, "%s %s" % (json.dumps(doc), err))
        with open(path, "rb") as fh:
            raw = fh.read().decode("utf-8")
        self.assertIn("\r\nOpen:\r\nNext:", raw)
        self.assertEqual(raw.count("\n"), raw.count("\r\n"), "no bare line feed")


class TheComment(_Write):
    """CP1-6: one triage comment, kept as found; a continued doc that has one never gains another."""

    def test_a_doc_with_a_comment_keeps_it_and_gains_none(self):
        text = preconlib.SCOPE_DOC.replace("\n\nIntent:", "\n<!-- precon-v2 triage: architectural -->\n\nIntent:", 1)
        path = preconlib.ensure_scope_doc(self.fx, text=text)
        run, code, doc, err = self.through_write({"lines": [preconlib.owner_line("Counts print to stdout",
                                                                                 "print it")]})
        self.assertEqual(code, 0, err)
        after = preconlib.read(path)
        self.assertEqual(after.count("<!-- precon-v2 triage:"), 1)
        self.assertIn("<!-- precon-v2 triage: architectural -->\n", after)


class TheCommentInAnyHand(unittest.TestCase):
    """CP1-6 (round 4, R3): `render_continued` adds no comment when the text holds any match, a comment
    split over lines or spelled another way included."""

    def test_no_second_comment(self):
        testlib.add_scripts_to_path()
        from precon_core import scopedoc
        parts = {"decisions": [], "rewrites": {}, "removals": set(), "out_of_scope": [], "research": [], "open": []}
        for comment in ("<!--\nprecon-v2 triage: bounded -->", "<!-- precon-v2triage: bounded -->",
                        "<!-- precon\u2011v2 triage: bounded -->",
                        # R1 of 3b: recognized by content, not spelling
                        "<!-- precon-v 2 triage: bounded -->", "<!-- \uff50\uff52\uff45\uff43\uff4f\uff4e-v2 triage: bounded -->",
                        "<!-- triage (precon-v2): bounded -->"):
            text = preconlib.SCOPE_DOC.replace("\n\nIntent:", "\n%s\n\nIntent:" % comment, 1)
            self.assertEqual(scopedoc.render_continued(text, "napkin", parts), text, repr(comment))


class ReadsBackWhatWasWritten(unittest.TestCase):
    """CP2-4 (ruling R4): a planned doc that would read back more items than the plan wrote is
    refused, whatever character made the reader see a second item."""

    def test_the_item_count_is_checked(self):
        testlib.add_scripts_to_path()
        from precon_core import scopedoc
        text = templates.render_scope_doc("Turnstile", preconlib.DATE, "a counter", ["Counts print %s decided "
                                          "(the owner's words: \"print it\")" % D], open_items=["a", "b"])
        self.assertEqual(scopedoc.check_rendered(text, items=3), [])
        problems = scopedoc.check_rendered(text, items=2)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("3 items", problems[0]["message"])


class ReportOnly(_Write):

    def test_report_only_writes_nothing_outside_the_run_directory(self):
        path = preconlib.ensure_scope_doc(self.fx)
        before = (testlib.tree_digest(self.fx.ws), testlib.tree_digest(self.fx.staging))
        run, code, doc, err = self.through_write(
            {"lines": [preconlib.owner_line("Counts print to stdout", "print it")]}, report_only=True)
        self.assertEqual(code, 0, err)
        self.assertEqual((testlib.tree_digest(self.fx.ws), testlib.tree_digest(self.fx.staging)), before)
        self.assertEqual(doc["writes"], [])
        self.assertEqual([p["path"] for p in doc["planned"]], [path])
        preview = doc["planned"][0]["preview"]
        self.assertTrue(preview.startswith(run.run_dir + os.sep))
        self.assertIn("Counts print to stdout", preconlib.read(preview))
        code, result, err = run.report()
        self.assertEqual(code, 10, err)
        self.assertTrue(result["wrote_nothing"])
        self.assertTrue(all(w["kind"] == "run_artifact" for w in result["writes"]))

    def test_report_only_new_doc_writes_nothing(self):
        before = testlib.tree_digest(self.fx.ws)
        run, code, doc, err = self.through_write(
            {"doc": preconlib.new_doc_fields(), "lines": [preconlib.owner_line("Counts print to stdout", "print it")]},
            report_only=True)
        self.assertEqual(code, 0, err)
        self.assertEqual(testlib.tree_digest(self.fx.ws), before)


if __name__ == "__main__":
    unittest.main()
