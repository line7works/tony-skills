"""The review block's bytes, pinned to Appendix A, and proved against the component's own reader.

`blocks.py` is PROVISIONAL: at records interface version 1 `records.py render` renders no
`finding_raised` line, so this station renders the review block itself. The control room has put
a component-side renderer to the owner. Until he rules, two tests stand in for the component's
guarantee, and they are what make the swap safe whichever way he rules:

1. **The line form is Appendix A's**, field for field:
   `- <severity> · <file:line> · <claim> · <failure scenario> · <which slice's review found it>`
   under a heading `### <YYYY-MM-DD> — review: <slice>`, with the separator ` · ` forbidden
   inside any field.

2. **The round trip holds.** The component's OWN reader, over a document carrying a block this
   station wrote, reads back exactly the facts this station appended: the same location, the
   same severity, the same claim, the same scenario. That is measured by importing the written
   document into a fresh log through `import-legacy` and comparing the events it produces with
   the native events of the run that wrote the block. If the bytes were wrong, the component's
   reader would place them differently or refuse them.
"""
import json
import os
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()
from signoff_core import blocks  # noqa: E402

DOC = "docs/plans/2026-09-18-signpost-rows.md"
SEP = " · "


def an_event(**over):
    event = {"kind": "finding_raised", "severity": "MAJOR",
             "location": {"raw": "src/signpost/pad.py:6", "file": "src/signpost/pad.py",
                          "line": 6, "line_end": None, "tag": None, "more": [], "resolved": True},
             "claim": "pad() returns width - 1 characters",
             "scenario": "run sh checks/field-widths.sh; it prints 11, not 12, and exits 1",
             "raised_by": "D"}
    event.update(over)
    return {"seq": 1, "event": event}


class TheLineFormIsAppendixAs(unittest.TestCase):
    def test_the_five_fields_in_order(self):
        line = blocks.finding_line(an_event()["event"])
        self.assertTrue(line.startswith("- "))
        fields = line[2:].split(SEP)
        self.assertEqual(len(fields), 5, line)
        self.assertEqual(fields[0], "MAJOR")
        self.assertEqual(fields[1], "src/signpost/pad.py:6")
        self.assertEqual(fields[2], "pad() returns width - 1 characters")
        self.assertEqual(fields[3],
                         "run sh checks/field-widths.sh; it prints 11, not 12, and exits 1")
        self.assertEqual(fields[4], "D")

    def test_the_heading_names_the_run_date_and_the_slice(self):
        got = blocks.review_block([an_event()], "2026-09-21", ["D"])
        self.assertEqual(got["block"].split("\n")[1], "### 2026-09-21 — review: D")
        self.assertEqual(got["block"].split("\n")[0], "",
                         "the block opens with a blank line, as the component's does")
        self.assertEqual(got["rendered"], 1)

    def test_a_field_carrying_the_separator_is_refused(self):
        with self.assertRaises(blocks.GrammarBroken):
            blocks.finding_line(an_event(claim="a" + SEP + "b")["event"])

    def test_a_field_spanning_lines_is_refused(self):
        with self.assertRaises(blocks.GrammarBroken):
            blocks.finding_line(an_event(scenario="one\ntwo")["event"])

    def test_an_event_that_is_not_a_finding_raised_is_skipped_never_dropped_silently(self):
        got = blocks.review_block([{"seq": 2, "event": {"kind": "card_set"}}], "2026-09-21", ["D"])
        self.assertEqual(got["rendered"], 0)
        self.assertEqual(got["skipped"], [{"seq": 2, "kind": "card_set"}])

    def test_no_findings_renders_no_block_at_all(self):
        got = blocks.review_block([], "2026-09-21", ["D"])
        self.assertEqual(got["block"], "")
        self.assertEqual(got["text"], "")
        self.assertIsNone(got["date"])


class TheComponentsOwnReaderReadsTheBlockBack(unittest.TestCase):
    """The round trip: what this station wrote, the component's importer reads as the same facts."""

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-roundtrip-")
        self.addCleanup(testlib.rmtree, self.dir)
        self.case = testlib.build_case("S1-review-scope", "S1-02-untracked-defect",
                                       os.path.join(self.dir, "S1-review-scope"))
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")

    def records(self, *args):
        proc = subprocess.run(
            [testlib.GEN_PYTHON, os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py")]
            + list(args),
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")

    def run_signoff(self):
        seeded = testlib.load_json(os.path.join(self.case, "input.json"))
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "test", "run_id": "roundtrip",
                              "run_dir": self.run_dir, "run_date": "2026-09-21",
                              "harness": None, "sessions": seeded["sessions"]},
               "workspace": self.workspace,
               "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                          "base": seeded["base"]},
               "report_only": False, "review": {"depth": "LEAN", "route": "test"}}
        path = testlib.write_json(os.path.join(self.case, "signoff-input.json"), doc)
        env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}
        for args in (["check-input", path], ["scope", "--run-dir", self.run_dir],
                     ["request", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer",
                      os.path.join(self.case, "answer.json")]):
            code, body, err = testlib.signoff(args, env=env)
            self.assertEqual(code, 0, err or json.dumps(body))
        code, body, err = testlib.signoff(["record", "--run-dir", self.run_dir], env=env)
        self.assertEqual(code, 10, err or json.dumps(body))
        self.assertEqual(body["status"], "completed", json.dumps(body))
        return body

    def test_the_written_block_reads_back_as_the_facts_that_were_appended(self):
        self.run_signoff()
        native = [json.loads(line) for line in
                  testlib.read_text(os.path.join(
                      self.workspace,
                      "docs/records/docs__plans__2026-09-18-signpost-rows.events.jsonl")).split("\n")
                  if line.strip()]
        mine = [e for e in native if e["kind"] == "finding_raised"]
        self.assertEqual(len(mine), 1)

        # A fresh copy of the written document, imported into a log of its own: the component's
        # own reader against this station's bytes, with nothing of the native log to lean on.
        fresh = os.path.join(self.dir, "fresh")
        os.makedirs(os.path.join(fresh, "docs", "plans"))
        text = testlib.read_text(os.path.join(self.workspace, DOC))
        with open(os.path.join(fresh, DOC), "w", encoding="utf-8") as fh:
            fh.write(text)
        for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                     ["-c", "user.name=T", "-c", "user.email=t@e.invalid", "commit", "-qm", "doc"]):
            subprocess.run(["git"] + args, cwd=fresh,
                           env=dict(os.environ, GIT_CONFIG_NOSYSTEM="1",
                                    GIT_CONFIG_GLOBAL="/dev/null",
                                    GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@e.invalid",
                                    GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@e.invalid"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        code, out, err = self.records("import-legacy", "--workspace", fresh, "--doc", DOC)
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["ambiguous"], 0, json.dumps(report))
        self.assertEqual((report["counts"] or {}).get("legacy_unparsed", 0), 0,
                         "the component's reader places every line this station wrote")

        code, out, err = self.records("events", "--workspace", fresh, "--doc", DOC,
                                      "--kind", "finding_raised")
        self.assertEqual(code, 0, err)
        read_back = [row["event"] for row in json.loads(out)["results"]]
        self.assertEqual(len(read_back), 1,
                         "one line written, one finding read back — never two, never none")
        want, got = mine[0], read_back[0]
        self.assertEqual(got["location"]["raw"], want["location"]["raw"])
        self.assertEqual(got["location"]["file"], want["location"]["file"])
        self.assertEqual(got["location"]["line"], want["location"]["line"])
        self.assertEqual(got["severity"], want["severity"])
        self.assertEqual(got["claim"], want["claim"])
        self.assertEqual(got["scenario"], want["scenario"])
        self.assertEqual(got["raised_by"], want["raised_by"])
        self.assertEqual(got["slice"], want["slice"])
        self.assertEqual(got["finding"], want["finding"],
                         "the finding identity computed from the written line is the identity "
                         "computed from the appended event")

    def test_a_second_levelling_of_the_written_document_stops_as_a_second_raise(self):
        """KNOWN OPEN POINT, measured, not designed: after this run appends a native
        `finding_raised` AND writes its Appendix A line into the build doc, the next levelling of
        that document stops with exit 5, `ambiguous_identity`.

        The component's own reason: "this line and line 0 compute the same finding id ...
        (section 7: two raises in one document)". The importer's idempotence is keyed on the
        `origin` records of lines IT imported — a second pass over an unchanged document reports
        `previously_imported: N, imported: 0, ok: true` — and NOT on the finding identities the
        log already holds natively. A line this station wrote was never imported, so the tracking
        never covers it.

        This test pins the behaviour that is actually there, so the day the seam is fixed this
        test fails and says so, rather than a silent duplicate appearing. `plugins/records/` is
        frozen for this step (E13-2) and the question is with the control room; README.md carries
        it as a known open point. What this station must never do is hide it: the levelling stop
        is loud and writes nothing, which the transaction suite proves separately.
        """
        self.run_signoff()
        log = os.path.join(self.workspace,
                           "docs/records/docs__plans__2026-09-18-signpost-rows.events.jsonl")
        before = testlib.read_text(log)
        code, out, err = self.records("import-legacy", "--workspace", self.workspace, "--doc", DOC,
                                      "--dry-run")
        self.assertEqual(code, 5, "expected the ambiguous-identity stop; got %d: %s" % (code, out))
        report = json.loads(out)
        self.assertEqual(report["error"], "ambiguous_identity")
        self.assertEqual(len(report["ambiguities"]), 1)
        self.assertIn("compute the same finding id", report["ambiguities"][0]["reason"])
        self.assertEqual(testlib.read_text(log), before,
                         "the refused levelling wrote nothing at all")


if __name__ == "__main__":
    unittest.main()
