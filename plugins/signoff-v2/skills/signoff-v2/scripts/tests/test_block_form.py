"""The review block is the component's rendering, and the document levels again afterwards.

Amendment A4 put the review block inside the records component: `render --run-id R` now returns
`review`, one block per slice the run's `finding_raised` events name, and `import-legacy`
recognises a line byte-equal to what `render` produced for a native event the log already holds
(`native_rendered`). So `signoff_core/blocks.py` is gone and this station places the component's
bytes, which is what ruling E13-3 asked for in the first place.

Three things this suite holds:

1. **The placed block IS the component's `review` text**, byte for byte, obtained by asking the
   component directly. The rendered line writes the claim as `(<claim>)` — the component's own
   reading of Appendix A, since that is the form its reader round-trips — and this station does
   not post-process it.
2. **Nothing else of the run is dropped.** Signoff writes no `disposition`, `defect_raised`,
   `waived` or `reopened`, so `render`'s recheck block and grants must come back empty; if they
   ever do not, placing `review` alone would silently lose them.
3. **The document levels again.** The pin that used to record the exit-5 defect is inverted:
   after a signoff run writes its block, `import-legacy --dry-run` over that document reports
   `would_import: 0`, no ambiguity, and `native_rendered` equal to the number of lines the run
   wrote — its review lines plus the `Status:` line when the card moved.

The round trip against a FRESH log stays: a document carrying this block, imported where no log
holds the run, still reads back as the same findings with the same identities.
"""
import json
import os
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()

DOC = "docs/plans/2026-09-18-signpost-rows.md"
LOG = "docs/records/docs__plans__2026-09-18-signpost-rows.events.jsonl"
SEP = " · "


class AfterASignoffRun(unittest.TestCase):
    """One completed signoff run over S1-02, then questions about what it left behind."""

    CASE = "S1-02-untracked-defect"
    RUN_ID = "blockform"

    def setUp(self):
        self.dir = testlib.make_scratch("signoff-blockform-")
        self.addCleanup(testlib.rmtree, self.dir)
        family = testlib.family_of(self.CASE)
        self.case = testlib.build_case(family, self.CASE, os.path.join(self.dir, family))
        self.workspace = os.path.join(self.case, "workspace")
        self.run_dir = os.path.join(self.case, "run")
        self.env = {"RECORDS_ROOT": testlib.RECORDS_ROOT}

    def records(self, *args):
        proc = subprocess.run(
            [testlib.GEN_PYTHON, os.path.join(testlib.RECORDS_ROOT, "scripts", "records.py")]
            + list(args),
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")

    def run_signoff(self, run_id=None, report_only=False):
        run_id = run_id or self.RUN_ID
        seeded = testlib.load_json(os.path.join(self.case, "input.json"))
        doc = {"protocol_version": 1,
               "invocation": {"mode": "headless", "caller": "test", "run_id": run_id,
                              "run_dir": self.run_dir, "run_date": "2026-09-21", "harness": None,
                              "sessions": seeded["sessions"]},
               "workspace": self.workspace,
               "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                          "base": seeded["base"]},
               "report_only": report_only, "review": {"depth": "LEAN", "route": "test"}}
        path = testlib.write_json(os.path.join(self.case, "in-%s.json" % run_id), doc)
        for args in (["check-input", path], ["scope", "--run-dir", self.run_dir],
                     ["request", "--run-dir", self.run_dir],
                     ["record-answer", "--run-dir", self.run_dir, "--answer",
                      os.path.join(self.case, "answer.json")]):
            code, body, err = testlib.signoff(args, env=self.env)
            self.assertEqual(code, 0, err or json.dumps(body))
        code, body, err = testlib.signoff(["record", "--run-dir", self.run_dir], env=self.env)
        self.assertEqual(code, 10, err or json.dumps(body))
        self.assertEqual(body["status"], "completed", json.dumps(body))
        return body

    def rendered(self, run_id=None):
        code, out, err = self.records("render", "--workspace", self.workspace, "--doc", DOC,
                                      "--run-id", run_id or self.RUN_ID)
        self.assertEqual(code, 0, err)
        return json.loads(out)


class ThePlacedBlockIsTheComponentsRendering(AfterASignoffRun):
    def test_the_build_doc_carries_the_components_review_text_byte_for_byte(self):
        self.run_signoff()
        got = self.rendered()
        self.assertTrue(got["review"].strip(), json.dumps(got))
        build_doc = testlib.read_text(os.path.join(self.workspace, DOC))
        self.assertIn(got["review"].strip("\n"), build_doc,
                      "the placed block is not the component's `review` text")

    def test_the_line_writes_the_claim_in_parentheses_and_is_not_post_processed(self):
        """The component's reading of Appendix A. This station does not touch it."""
        self.run_signoff()
        line = self.rendered()["review_lines"][0]
        fields = line[2:].split(SEP)
        self.assertEqual(len(fields), 5, line)
        self.assertEqual(fields[0], "MAJOR")
        self.assertEqual(fields[1], "src/signpost/pad.py:6")
        self.assertTrue(fields[2].startswith("(") and fields[2].endswith(")"), fields[2])
        self.assertEqual(fields[4], "D")
        build_doc = testlib.read_text(os.path.join(self.workspace, DOC))
        self.assertIn(line, build_doc, "the line reached the document unmodified")

    def test_the_heading_names_one_slice(self):
        """The component writes the heading slice as `Slice D`, the same way the pilot's recheck
        heading has always written one. That is its bytes and this station takes them."""
        self.run_signoff()
        got = self.rendered()
        self.assertEqual(got["review_slices"], ["D"])
        self.assertIn("### 2026-09-21 — review: Slice D", got["review"])
        build_doc = testlib.read_text(os.path.join(self.workspace, DOC))
        self.assertIn("### 2026-09-21 — review: Slice D", build_doc)

    def test_signoff_renders_no_recheck_block_and_no_grant(self):
        """Placing `review` alone is only safe while the run produces nothing else. Signoff
        never clears a finding, so it never does — and this is the test that says so."""
        self.run_signoff()
        got = self.rendered()
        self.assertEqual(got["block"], "", "signoff wrote a recheck block")
        self.assertEqual(got["lines"], [])
        self.assertEqual(got["grants"], [], "signoff granted a waiver or a reopening")
        self.assertEqual(got["rendered"], len(got["review_lines"]))


class TheDocumentLevelsAgain(AfterASignoffRun):
    """The inversion of the exit-5 pin this suite used to carry.

    Before amendment A4, a document this station wrote could not be levelled again: the importer
    read the station's own rendered line as a second raise of the finding that produced it and
    stopped with exit 5. It now recognises the line by its bytes.
    """

    def test_a_dry_run_over_the_written_document_imports_nothing(self):
        body = self.run_signoff()
        code, out, err = self.records("import-legacy", "--workspace", self.workspace,
                                      "--doc", DOC, "--dry-run")
        self.assertEqual(code, 0, "the levelling stopped: %s%s" % (out, err))
        report = json.loads(out)
        self.assertEqual(report["would_import"], 0, json.dumps(report))
        self.assertEqual(report["ambiguities"], [])
        self.assertEqual((report["counts"] or {}).get("legacy_unparsed", 0), 0)

    def test_native_rendered_counts_every_line_the_run_wrote(self):
        body = self.run_signoff()
        lines = len(self.rendered()["review_lines"])
        result = testlib.load_json(body["result"])
        self.assertTrue(result["card"]["moved"], "this case moves its card")
        code, out, err = self.records("import-legacy", "--workspace", self.workspace,
                                      "--doc", DOC, "--dry-run")
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["native_rendered"], lines + 1,
                         "the review line(s) and the `Status:` line the card moved: %s"
                         % json.dumps(report))

    def test_the_real_levelling_writes_nothing_new(self):
        self.run_signoff()
        before = testlib.read_text(os.path.join(self.workspace, LOG))
        code, out, err = self.records("import-legacy", "--workspace", self.workspace, "--doc", DOC)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["imported"], 0)
        self.assertEqual(testlib.read_text(os.path.join(self.workspace, LOG)), before,
                         "a levelling of an unchanged document appended to the log")

    def test_a_hand_written_line_beside_the_rendered_one_is_still_news(self):
        """Recognition is by bytes, so it never swallows a record a person added."""
        self.run_signoff()
        path = os.path.join(self.workspace, DOC)
        text = testlib.read_text(path)
        text += "- " + SEP.join(["MINOR", "src/signpost/render.py:3",
                                  "(the width is a bare constant)",
                                  "a second caller would repeat it", "D"]) + "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        code, out, err = self.records("import-legacy", "--workspace", self.workspace,
                                      "--doc", DOC, "--dry-run")
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual((report["counts"] or {}).get("finding_raised"), 1,
                         "the hand-written line was swallowed: %s" % json.dumps(report))
        self.assertEqual(report["native_rendered"], 2,
                         "the run's own two lines are still recognised beside it")
        self.assertEqual((report["counts"] or {}).get("legacy_unparsed", 0), 0)


class TheComponentsOwnReaderReadsTheBlockBack(AfterASignoffRun):
    """The round trip, against a FRESH log that does not hold the run.

    Recognition cannot help here — the log holds no native event to recognise — so this measures
    the bytes themselves: read cold, they are the same findings with the same identities.
    """

    def test_the_written_block_reads_back_as_the_facts_that_were_appended(self):
        self.run_signoff()
        native = [json.loads(line) for line in
                  testlib.read_text(os.path.join(self.workspace, LOG)).split("\n") if line.strip()]
        mine = [e for e in native if e["kind"] == "finding_raised"]
        self.assertEqual(len(mine), 1)

        fresh = os.path.join(self.dir, "fresh")
        os.makedirs(os.path.join(fresh, "docs", "plans"))
        with open(os.path.join(fresh, DOC), "w", encoding="utf-8") as fh:
            fh.write(testlib.read_text(os.path.join(self.workspace, DOC)))
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
                   GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@e.invalid",
                   GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@e.invalid")
        for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "doc"]):
            subprocess.run(["git"] + args, cwd=fresh, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, check=True)
        code, out, err = self.records("import-legacy", "--workspace", fresh, "--doc", DOC)
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["ambiguous"], 0, json.dumps(report))
        self.assertEqual(report["native_rendered"], 0,
                         "a fresh log recognises nothing; the bytes have to stand on their own")

        code, out, err = self.records("events", "--workspace", fresh, "--doc", DOC,
                                      "--kind", "finding_raised")
        self.assertEqual(code, 0, err)
        read_back = [row["event"] for row in json.loads(out)["results"]]
        self.assertEqual(len(read_back), 1, "one line written, one finding read back")
        want, got = mine[0], read_back[0]
        self.assertEqual(got["location"]["raw"], want["location"]["raw"])
        self.assertEqual(got["severity"], want["severity"])
        self.assertEqual(got["claim"], want["claim"])
        self.assertEqual(got["scenario"], want["scenario"])
        self.assertEqual(got["raised_by"], want["raised_by"])
        self.assertEqual(got["slice"], want["slice"])
        self.assertEqual(got["finding"], want["finding"],
                         "the identity computed from the written line is the identity the "
                         "appended event carries")


if __name__ == "__main__":
    unittest.main()
