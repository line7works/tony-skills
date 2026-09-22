"""Every case of both families, driven through `observe.py` and the real CLI.

What this suite may assert, and what it may not. The outcome of each case lives in an answer key
this lane never sees, and the control room grades `observed.json` against it. So these tests
assert only what the LANE CONTRACT guarantees for every run, never what a particular case
"should" produce:

    a terminal status exists, and it is `stop` or `completion`
    the source set has three lists and a base, and the base is the ref the case named
    the result validates against its schema and passes the semantic checks
    the report-only case wrote nothing to the workspace and nothing to the log
    a refused answer is neither acted on nor repaired
    every emitted name is one of the README's neutral vocabulary
    nothing is emitted that the core has no fact for

One assertion here is about the observer rather than the core, and it is the important one: no
expected value appears anywhere in this plugin. The test reads every file of the plugin and
fails on a comparison against a case id, because a builder that wrote one would be grading
itself.
"""
import json
import os
import re
import subprocess
import unittest

import testlib

testlib.add_scripts_to_path()

from build_core import validate  # noqa: E402

# The README's table. `either` is the key's word, not the observer's: this core emits facts.
VOCABULARY = {
    "base_ref", "source_set_committed", "source_set_changed", "source_set_untracked",
    "out_of_scope_paths", "checks_passed", "checks_failing", "checks_skipped",
    "checks_not_passed", "check_output_contains", "card_after", "terminal_status",
    "answer_refused", "writes_none", "refusal_reason",
}
CASE_COUNT = {"B1-scope-adherence": 4, "B2-honest-failure": 5}


def observe_all(out_dir, extra=None):
    """Run `observe.py --all --out <dir>` and return {case id: observed.json}."""
    argv = [testlib.GEN_PYTHON, testlib.OBSERVE, "--all", "--out", out_dir]
    proc = subprocess.run(argv + list(extra or []), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=testlib.base_env())
    if proc.returncode != 0:
        raise AssertionError("observe.py --all failed (%d):\n%s\n%s"
                             % (proc.returncode, proc.stdout.decode("utf-8", "replace")[-3000:],
                                proc.stderr.decode("utf-8", "replace")[-3000:]))
    summary = json.loads(proc.stdout.decode("utf-8"))
    out = {}
    for row in summary["cases"]:
        out[row["case"]] = testlib.load_json(row["observed"])
    return summary, out


_RUN = {}


def setUpModule():
    """Both families are built and observed ONCE for this whole file: nine cases, one pass."""
    scratch = testlib.make_scratch("build-v2-observe-")
    _RUN["scratch"] = scratch
    _RUN["summary"], _RUN["observed"] = observe_all(scratch)


def tearDownModule():
    testlib.rmtree(_RUN.get("scratch") or "")


class _Observed(unittest.TestCase):
    """Reads the one observation pass of this module."""

    @property
    def observed(self):
        return _RUN["observed"]

    @property
    def summary(self):
        return _RUN["summary"]


class EveryCaseIsObserved(_Observed):

    def test_every_case_of_both_families_produced_an_observation(self):
        for family, count in CASE_COUNT.items():
            got = [c for c in self.observed if c.startswith(family.split("-")[0] + "-")]
            self.assertEqual(len(got), count, "%s: %s" % (family, sorted(got)))
        self.assertEqual(len(self.observed), sum(CASE_COUNT.values()))

    def test_the_run_of_every_case_produced_a_result(self):
        for case, row in sorted(self.observed.items()):
            self.assertTrue(row.get("_result"), case)
            self.assertTrue(os.path.isfile(row["_result"]), case)


class WhatTheContractGuaranteesForEveryRun(_Observed):

    def test_every_case_carries_a_terminal_status_of_one_of_the_two_kinds(self):
        for case, row in sorted(self.observed.items()):
            self.assertIn("terminal_status", row, case)
            self.assertIn(row["terminal_status"], ("stop", "completion"), case)

    def test_every_case_carries_the_three_lists_and_the_base_it_was_given(self):
        for case, row in sorted(self.observed.items()):
            for name in ("source_set_committed", "source_set_changed", "source_set_untracked"):
                self.assertIn(name, row, "%s: %s" % (case, name))
                self.assertIsInstance(row[name], list, case)
                self.assertEqual(row[name], sorted(row[name]), "%s: %s is sorted" % (case, name))
            self.assertEqual(row["base_ref"], "base", case)

    def test_every_result_validates_against_the_schema_and_the_semantic_checks(self):
        schema = validate.load_schema("result")
        for case, row in sorted(self.observed.items()):
            result = testlib.load_json(row["_result"])
            self.assertEqual(validate.errors_for(result, schema), [], case)
            semantic = validate.run_semantic(result, result.get("_input"), None)
            self.assertEqual(semantic["semantic"], [], "%s: %s" % (case, semantic["semantic"]))

    def test_no_run_reports_a_path_in_the_out_of_scope_list_that_is_not_in_the_source_set(self):
        for case, row in sorted(self.observed.items()):
            every = set(row["source_set_committed"]) | set(row["source_set_changed"]) \
                | set(row["source_set_untracked"])
            for path in row.get("out_of_scope_paths") or []:
                self.assertIn(path, every, "%s: %s" % (case, path))

    def test_the_records_log_is_in_no_source_set(self):
        for case, row in sorted(self.observed.items()):
            for name in ("source_set_committed", "source_set_changed", "source_set_untracked"):
                for path in row[name]:
                    self.assertFalse(path.startswith("docs/records/"), "%s: %s" % (case, path))

    def test_every_check_a_run_reports_carries_its_output(self):
        for case, row in sorted(self.observed.items()):
            reported = set((row.get("checks_passed") or []) + (row.get("checks_failing") or [])
                           + (row.get("checks_skipped") or []))
            for name in reported:
                self.assertIn(name, row.get("check_output_contains") or {}, "%s: %s" % (case, name))

    def test_failing_and_skipped_together_are_the_not_passed_set(self):
        for case, row in sorted(self.observed.items()):
            self.assertEqual(sorted(row.get("checks_not_passed") or []),
                             sorted((row.get("checks_failing") or [])
                                    + (row.get("checks_skipped") or [])), case)

    def test_a_run_that_refused_its_answer_moved_no_card_and_appended_no_event(self):
        for case, row in sorted(self.observed.items()):
            if not row.get("answer_refused"):
                continue
            result = testlib.load_json(row["_result"])
            self.assertFalse(result["card"]["moved"], case)
            self.assertEqual(result["records"]["appended"], [], case)
            self.assertFalse(result["answer"]["accepted"], case)
            self.assertTrue(result["answer"]["refusals"], case)
            self.assertEqual(row.get("refusal_reason"), "answer_invalid", case)

    def test_a_report_only_run_wrote_nothing_to_the_workspace_or_the_log(self):
        """`writes_none` is measured by the observer: a digest of the whole workspace, the log
        included, taken before and after the run."""
        report_only = [c for c, row in self.observed.items() if row.get("writes_none")]
        self.assertTrue(report_only, "no case reported writing nothing")
        for case in report_only:
            result = testlib.load_json(self.observed[case]["_result"])
            self.assertTrue(result["report_only"], case)
            self.assertTrue(result["wrote_nothing"], case)
            self.assertEqual(result["records"]["appended"], [], case)
            self.assertTrue((result["records"]["levelled"] or {})["dry_run"], case)
            # the result still carries the checks, the source set and the out-of-scope list
            self.assertTrue(result["checks"], case)
            self.assertIn("source_set", result, case)
            self.assertIn("out_of_scope", result, case)

    def test_a_run_that_moved_a_card_appended_exactly_one_event(self):
        for case, row in sorted(self.observed.items()):
            result = testlib.load_json(row["_result"])
            if not result["card"]["moved"]:
                continue
            self.assertEqual(len(result["records"]["appended"]), 1, case)
            self.assertEqual(result["records"]["appended"][0]["kind"], "card_set", case)
            self.assertEqual(result["card"]["after"], row["card_after"], case)


class TheObserverEmitsFactsAndNothingElse(_Observed):

    def test_every_emitted_name_is_in_the_neutral_vocabulary(self):
        for case, row in sorted(self.observed.items()):
            for name in row:
                if name.startswith("_"):
                    continue          # the observer's own bookkeeping, not an assertion name
                self.assertIn(name, VOCABULARY, "%s: %s" % (case, name))

    def test_no_signoff_only_name_is_emitted(self):
        """Names this core has no fact for are omitted, not guessed."""
        signoff_only = ("packet_must_include", "packet_must_exclude", "claims_absent_from_packet",
                        "raised_locations", "not_raised_locations", "note_locations",
                        "raised_severities", "raised_evidence_kinds", "verdict_recorded",
                        "clean_review_checks_listed")
        for case, row in sorted(self.observed.items()):
            for name in signoff_only:
                self.assertNotIn(name, row, "%s: %s" % (case, name))

    def test_the_observer_never_emits_the_keys_own_word(self):
        for case, row in sorted(self.observed.items()):
            self.assertNotIn("either", row, case)
            self.assertNotIn("any_of", json.dumps(row), case)


class NoExpectedValueIsInThisPlugin(unittest.TestCase):
    """The builder never sees the key, so it cannot write one; this makes that checkable.

    A comparison against a case id anywhere in the plugin would be a builder grading itself.
    """

    CASE_ID = re.compile(r"\bB[12]-0[0-9]-[a-z-]+\b")

    def test_no_shipped_file_compares_against_a_case_id(self):
        offenders = []
        for base, dirs, files in os.walk(testlib.PLUGIN):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
            for name in files:
                full = os.path.join(base, name)
                relative = os.path.relpath(full, testlib.PLUGIN)
                # the cases' own folder carries their ids by definition: it is the catalog
                if relative.startswith(os.path.join("evals", "seeded-cases") + os.sep):
                    if os.path.basename(base) in ("B1-scope-adherence", "B2-honest-failure",
                                                  "answers", "_lib"):
                        continue
                if not name.endswith((".py", ".json", ".md")):
                    continue
                try:
                    with open(full, encoding="utf-8") as fh:
                        text = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue
                for line in text.split("\n"):
                    if self.CASE_ID.search(line) and ("==" in line or "assert" in line.lower()):
                        offenders.append((relative, line.strip()[:120]))
        self.assertEqual(offenders, [], "an expected outcome for a named case is in the plugin")

    def test_the_cases_are_the_evidence_copies_unchanged(self):
        """A case, an answer or a generator is never edited by this lane."""
        for family in testlib.FAMILIES:
            folder = os.path.join(testlib.SEEDED, family)
            self.assertTrue(os.path.isfile(os.path.join(folder, "build.py")), family)
            self.assertTrue(os.path.isfile(os.path.join(folder, "CASES.md")), family)
            answers = os.path.join(folder, "answers")
            self.assertTrue(os.listdir(answers), family)
            for name in os.listdir(answers):
                body = testlib.load_json(os.path.join(answers, name))
                self.assertEqual(body["role"], "executor", name)
                self.assertEqual(body["case"], name[:-len(".json")], name)


class TheObserverIsDeterministic(unittest.TestCase):

    def test_two_runs_of_one_case_observe_the_same_facts(self):
        scratch = testlib.make_scratch("build-v2-observe-twice-")
        self.addCleanup(testlib.rmtree, scratch)
        first = self._one(scratch, "a")
        second = self._one(scratch, "b")
        self.assertEqual(first, second)

    def _one(self, scratch, name):
        out = os.path.join(scratch, name)
        argv = [testlib.GEN_PYTHON, testlib.OBSERVE, "--case", "B2-01-clean", "--out", out]
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=testlib.base_env())
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        summary = json.loads(proc.stdout.decode("utf-8"))
        body = testlib.load_json(summary["cases"][0]["observed"])
        return dict((k, v) for k, v in body.items() if not k.startswith("_"))


if __name__ == "__main__":
    unittest.main()
