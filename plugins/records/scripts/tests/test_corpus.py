"""This repository's own legacy records (contract evidence item 9, section 13's corpus test).

The contract: "`survey` and `import-legacy --dry-run` over every ledger document under `docs/`
finish without an error exit other than 5, classify every line under a record heading, leave
every document's hash and `git status` unchanged, and the dry run of
`docs/plans/2026-09-06-readers.md` reports the waiver line and nine cards; the counts the builder
observes go in its report, not in an assertion that would pin this repository's documents
forever."

So nothing here asserts a corpus count. What it asserts is the shape of the run: the exit codes,
that every line under a record heading came out classified as something, that the repository is
byte-identical afterwards, and the one property the contract names for the readers pair. The
counts are printed into the slice 2 report by the builder, from `survey`, not from a test.

`import-legacy` is never run here without `--dry-run`: a real import would write tracked files
into this repository, which is a separate job on the owner's word (section 11.8).
"""
import os
import re
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()

from records_core import canon, legacy  # noqa: E402

REPO = testlib.REPO
DOCS = os.path.join(REPO, "docs")
READERS = "docs/plans/2026-09-06-readers.md"
REVIEWS = "docs/reviews/"


def ledger_documents():
    """Every document under `docs/` that carries an Appendix A record and is not a mirror."""
    out = []
    for rel in testlib.markdown_documents(DOCS):
        doc = "docs/" + rel
        if doc.startswith(REVIEWS):
            continue
        with open(os.path.join(REPO, *doc.split("/")), encoding="utf-8") as fh:
            text = fh.read()
        parsed = legacy.tolerant_document(text, doc)
        if parsed["blocks"] or any(i["kind"] in ("waiver", "reopening") for i in parsed["items"]):
            out.append(doc)
    return out


def repo_state():
    """(git status --porcelain, {document: sha256}) for the whole repository's documents."""
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    status = sorted(line for line in proc.stdout.decode("utf-8", "replace").split("\n") if line)
    digests = {}
    for rel in testlib.markdown_documents(DOCS):
        path = os.path.join(DOCS, *rel.split("/"))
        with open(path, "rb") as fh:
            digests["docs/" + rel] = canon.sha256_hex(fh.read())
    return status, digests


class TheCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = ledger_documents()
        cls.before = repo_state()
        code, cls.survey, err = testlib.run_json(["survey", "--workspace", REPO])
        assert code == 0, err
        cls.runs = {}
        for doc in cls.documents:
            code, body, err = testlib.run_json(
                ["import-legacy", "--workspace", REPO, "--doc", doc, "--dry-run"])
            cls.runs[doc] = (code, body, err)

    def test_there_is_a_corpus_to_read(self):
        self.assertGreater(len(self.documents), 10,
                           "evidence item 9 names this repository's own ledger documents")

    def test_survey_finishes_clean(self):
        self.assertTrue(self.survey["ok"])
        self.assertEqual(self.survey["report"], "survey")
        self.assertGreater(self.survey["counts"]["ledger_documents"], 10)
        self.assertGreater(self.survey["counts"]["mirrors"], 0)

    def test_survey_validates_against_the_import_report_schema(self):
        from records_core import validate
        self.assertEqual(validate.validate_document("import_report", self.survey,
                                                    testlib.schemas()), [])

    def test_survey_lists_every_ledger_document_the_reader_finds(self):
        listed = set(row["doc"] for row in self.survey["documents"] if row["role"] == "ledger")
        for doc in self.documents:
            self.assertIn(doc, listed, doc)

    def test_a_verdict_doc_is_listed_as_a_mirror_and_never_surveyed_as_a_ledger(self):
        mirrors = [row for row in self.survey["documents"] if row["doc"].startswith(REVIEWS)]
        self.assertTrue(mirrors)
        for row in mirrors:
            self.assertEqual(row["role"], "mirror", row["doc"])
            self.assertIsNone(row["ambiguous"], row["doc"])
            self.assertEqual(row["stops"], [], row["doc"])

    def test_every_dry_run_finishes_with_no_error_exit_other_than_five(self):
        for doc, (code, body, err) in sorted(self.runs.items()):
            self.assertIn(code, (0, 5), "%s: exit %d, %s" % (doc, code, err))
            self.assertIsNotNone(body, doc)
            self.assertEqual(body["report"], "import", doc)
            self.assertTrue(body["dry_run"], doc)

    def test_every_line_under_a_record_heading_is_classified(self):
        """Every record bullet of every document comes out as an event or as a stop.

        The outside review's finding 13: the expectation used to be `tolerant_document`'s own
        item list, which is the reader this checks, so a reader that dropped every unparseable
        line passed. The lines to account for are now read out of the documents here, by a scan
        that knows only Appendix A's shapes: a `- ` bullet under a `review:` or `recheck:`
        heading, and a `WAIVED`/`REOPENED (per user)` grant line with or without its bullet
        (amendment A3). Fenced blocks are skipped, as the fence rule E8-20 requires.
        """
        for doc in sorted(self.documents):
            with open(os.path.join(REPO, *doc.split("/")), encoding="utf-8") as fh:
                lines = fh.read().split("\n")
            expected = set()
            fence, under_a_record_heading = None, False
            for number, line in enumerate(lines, 1):
                marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
                if marker:
                    if fence is None:
                        fence = marker.group(1)[0]
                    elif fence == marker.group(1)[0]:
                        fence = None
                    continue
                if fence is not None:
                    continue
                if line.startswith("#"):
                    under_a_record_heading = bool(
                        re.match(r"^###\s+\d{4}-\d{2}-\d{2}\s+[\u2014\u2013-]\s+(review|recheck):", line))
                    continue
                if under_a_record_heading and line.startswith("- "):
                    expected.add(number)
                if re.match(r"^(?:- )?(?:WAIVED|REOPENED) \(per user\) \u00b7 ", line):
                    expected.add(number)
            plan = testlib.plan_for(REPO, doc)
            accounted = set(event["origin"]["line"] for event in plan["events"]
                            if event["kind"] != "card_observed")
            accounted.update(stop["line"] for stop in plan["ambiguities"])
            missing = sorted(expected - accounted)
            self.assertEqual(missing, [],
                             "%s: %d record line(s) came out as nothing at all: %r"
                             % (doc, len(missing), [lines[n - 1] for n in missing[:3]]))

    def test_a_stopped_document_still_says_what_it_read(self):
        stopped = [(doc, body) for doc, (code, body, _) in self.runs.items() if code == 5]
        self.assertTrue(stopped, "no document of this repository stops; the corpus changed")
        for doc, body in stopped:
            self.assertEqual(body["error"], "ambiguous_identity", doc)
            self.assertTrue(body["ambiguities"], doc)
            self.assertTrue(body["counts"], doc)
            for stop in body["ambiguities"]:
                self.assertTrue(stop["raw"], doc)
                self.assertTrue(stop["reason"], doc)
                self.assertIsInstance(stop["candidates"], list)

    def test_the_readers_dry_run_reports_the_waiver_line_and_nine_cards(self):
        """The one property section 13 names for this repository's richest pair."""
        code, body, err = self.runs[READERS]
        self.assertIn(code, (0, 5), err)
        self.assertEqual(body["counts"].get("waived"), 1)
        self.assertEqual(body["counts"].get("card_observed"), 9)
        with open(os.path.join(REPO, *READERS.split("/")), encoding="utf-8") as fh:
            parsed = legacy.tolerant_document(fh.read(), READERS)
        self.assertEqual(len([s for s in parsed["slices"] if s["status_line"] is not None]), 9,
                         "one card per slice that carries a Status: line")
        self.assertEqual(len([i for i in parsed["items"] if i["kind"] == "waiver"]), 1)

    def test_the_waiver_line_is_the_one_written_without_a_bullet(self):
        with open(os.path.join(REPO, *READERS.split("/")), encoding="utf-8") as fh:
            parsed = legacy.tolerant_document(fh.read(), READERS)
        waiver = [i for i in parsed["items"] if i["kind"] == "waiver"][0]
        self.assertFalse(waiver["text"].startswith("- "))
        self.assertEqual(waiver["severity"], "BLOCKER")
        self.assertEqual(waiver["date"], "2026-09-06")

    def test_mirrors_runs_over_the_readers_pair(self):
        code, body, err = testlib.run_json(["mirrors", "--workspace", REPO, "--doc", READERS])
        self.assertEqual(code, 0, err)
        self.assertTrue(body["mirrors"])
        for row in body["mirrors"]:
            self.assertIn(row["state"], ("same", "differs", "absent"), row["slice"])

    def test_nothing_in_this_repository_moved(self):
        status, digests = repo_state()
        self.assertEqual(status, self.before[0],
                         "survey and the dry runs changed `git status --porcelain`")
        self.assertEqual(digests, self.before[1],
                         "survey and the dry runs changed a document's bytes")

    def test_no_log_was_written_anywhere_in_this_repository(self):
        self.assertFalse(os.path.isdir(os.path.join(REPO, "docs", "records")),
                         "a dry run writes nothing; a real import over this repository is a "
                         "separate job on the owner's word (section 11.8)")


if __name__ == "__main__":
    unittest.main()
