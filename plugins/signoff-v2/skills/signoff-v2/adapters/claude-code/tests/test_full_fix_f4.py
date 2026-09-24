"""E13 full-review fix round, Astra's F4 (BLOCKER) on the Claude Code adapter: typed text never
becomes the building session.

Her `probe_session_provenance.py` recorded a build with the harness fixture's session id, then
reviewed from that same session: `--build-result <actual result>` stopped on independence, and
`--building-session an-unrelated-session` printed `completed / verdict_recorded true`. The runtime
override is removed; the building session comes from the selected build run's own result, bound to
the same workspace, document and slice; the reviewing session from this harness's record; a
missing record is never a different building session: no --build-result leaves it null and
unavailable, and a selected result that records no `invocation.session_id` is refused, exit 3,
with no invocation emitted (Astra's N1).
"""

import json
import os
import shutil
import tempfile
import unittest

import corelib
import testlib

HELPER = "invocation.py"
DOC = "docs/plans/2026-09-18-signpost-rows.md"


def session_record_at(work, workspace):
    """The fixture transcript with its cwd records naming `workspace` (ruling E9-28's binding)."""
    rows = testlib.records()
    for row in rows:
        if row.get("cwd"):
            row["cwd"] = workspace
    return testlib.fixture_args(testlib.write_records(work, rows))


def build_result(run_dir, workspace, session, doc=DOC, slice_name="F", typed="typed-by-the-executor",
                 recorded=True):
    """A build-v2 result as the build core writes it, in its own run directory. The build run's
    harness identity is `invocation.session_id` (send-back 1); `answer.session_id` is the
    executor's typed copy and is deliberately something else here, so a helper that reads it is
    caught."""
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, "result.json")
    with open(path, "w") as handle:
        json.dump({"result_version": 1, "interface_version": 1, "run_id": os.path.basename(run_dir),
                   "status": "completed", "terminal_status": "completion",
                   "workspace": workspace, "run_dir": run_dir, "build_doc": doc,
                   "slice": slice_name,
                   "invocation": dict({"harness": "claude-code", "caller": "user", "mode": "direct"},
                                      **({"session_id": session} if recorded else {})),
                   "answer": {"session_id": typed, "claimed_status": "complete",
                              "claimed_card": "built", "accepted": True, "refusals": [],
                              "path": os.path.join(run_dir, "answer.json")}}, handle)
    return path


class TheOverrideIsGone(unittest.TestCase):
    def test_building_session_is_not_an_argument(self):
        code, out, err = testlib.run(HELPER, testlib.fixture_args()
                                     + ["--building-session", "an-unrelated-session"])
        self.assertEqual(code, 2, "the typed override was accepted: %s" % out)

    def test_no_selected_build_run_is_unavailable_provenance(self):
        doc = testlib.run_json(HELPER, testlib.fixture_args())
        self.assertIsNone(doc["invocation"]["sessions"]["building"])
        self.assertEqual(doc["measurement"]["building_provenance"], "unavailable")
        self.assertIn("unavailable", doc["measurement"]["_sources"]["sessions.building"])


class TheBuildResultIsBound(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="f4-")
        self.workspace = os.path.join(self.work, "workspace")
        os.makedirs(self.workspace)
        self.path = build_result(os.path.join(self.work, "build-run"), self.workspace, "b-9")

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def args(self, **over):
        values = {"--workspace": self.workspace, "--build-doc": DOC, "--slice": "F"}
        values.update(over)
        out = session_record_at(self.work, self.workspace) + ["--build-result", self.path]
        for key, value in values.items():
            if value is not None:
                out += [key, value]
        return out

    def test_a_bound_result_names_the_building_session(self):
        doc = testlib.run_json(HELPER, self.args())
        self.assertEqual(doc["invocation"]["sessions"]["building"], "b-9")
        self.assertEqual(doc["measurement"]["building_provenance"], "build run build-run")

    def test_the_binding_arguments_are_required(self):
        for missing in ("--workspace", "--build-doc", "--slice"):
            code, out, err = testlib.run(HELPER, self.args(**{missing: None}))
            self.assertEqual(code, 2, "%s missing: %s" % (missing, out))

    def test_another_workspace_document_or_slice_is_refused(self):
        other = os.path.join(self.work, "other")
        os.makedirs(other)
        # the result names another workspace than the one this session reviews
        self.path = build_result(os.path.join(self.work, "build-run-2"), other, "b-9")
        code, out, err = testlib.run(HELPER, self.args())
        self.assertEqual(code, 2, out)
        self.assertIn("build result", err)
        self.path = build_result(os.path.join(self.work, "build-run"), self.workspace, "b-9")
        for over in ({"--build-doc": "docs/plans/other.md"}, {"--slice": "G"}):
            code, out, err = testlib.run(HELPER, self.args(**over))
            self.assertEqual(code, 2, "%s: %s" % (over, out))
            self.assertIn("build result", err)

    def test_a_result_outside_its_own_run_directory_is_refused(self):
        moved = os.path.join(self.work, "elsewhere.json")
        shutil.copyfile(self.path, moved)
        self.path = moved
        code, out, err = testlib.run(HELPER, self.args())
        self.assertEqual(code, 2, out)


class SendBack1TheHarnessIdentityOnly(TheBuildResultIsBound):
    """Send-back 1: the building session is the build run's `invocation.session_id`, the session
    the build adapter read from the harness record; a selected result without it is refused (Astra's
    N1) and never falls back to the executor's typed `answer.session_id`."""

    def test_the_typed_answer_session_is_never_read(self):
        doc = testlib.run_json(HELPER, self.args())
        self.assertEqual(doc["invocation"]["sessions"]["building"], "b-9")
        self.assertNotIn("typed-by-the-executor", json.dumps(doc["invocation"]))

    def test_a_result_with_no_recorded_session_is_refused(self):
        """Astra's N1: a selected build result that records no `invocation.session_id` is refused
        (exit 3) and no invocation is emitted; a null building session would read as independent."""
        self.path = build_result(os.path.join(self.work, "build-run"), self.workspace, "b-9",
                                 recorded=False)
        code, out, err = testlib.run(HELPER, self.args())
        self.assertEqual(code, 3, out)
        body = json.loads(out)
        self.assertNotIn("invocation", body)
        self.assertIn("records no invocation.session_id", body["error"])
        self.assertIn("no reviewing invocation was emitted", body["error"])


class TheProbeThroughTheCore(unittest.TestCase):
    """The shape of her probe: a build recorded from THIS session, then a review from it."""

    def test_a_build_from_this_session_is_refused_on_independence(self):
        work = tempfile.mkdtemp(prefix="f4-core-")
        try:
            case_dir, seeded = corelib.build_case(work)
            path = build_result(os.path.join(work, "build-run"), seeded["workspace"],
                                testlib.SESSION, seeded["build_doc"], seeded["slice"])
            doc = testlib.run_json(HELPER, session_record_at(work, seeded["workspace"]) + [
                "--build-result", path, "--workspace", seeded["workspace"],
                "--build-doc", seeded["build_doc"], "--slice", seeded["slice"],
                "--target-token", "F"], env={"TMPDIR": work})
            sessions = doc["invocation"]["sessions"]
            self.assertEqual(sessions["building"], sessions["reviewing"])
            corelib.independence_run(self, doc["invocation"], case_dir, seeded)
        finally:
            shutil.rmtree(work, ignore_errors=True)


class N1TheLegacyResultFromThisSession(unittest.TestCase):
    """Astra's N1 through the helper and the core: the pre-send-back build result (the typed
    `answer.session_id` only, no recorded `invocation.session_id`), selected from the SAME session
    that now reviews, is refused by the helper and never reaches a verdict."""

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="n1-")
        self.case_dir, self.seeded = corelib.build_case(self.work)
        # the legacy shape: this session typed its own id; no harness identity was recorded
        self.path = build_result(os.path.join(self.work, "build-run"), self.seeded["workspace"],
                                 testlib.SESSION, self.seeded["build_doc"], self.seeded["slice"],
                                 typed=testlib.SESSION, recorded=False)

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def helper(self):
        return testlib.run(HELPER, session_record_at(self.work, self.seeded["workspace"]) + [
            "--build-result", self.path, "--workspace", self.seeded["workspace"],
            "--build-doc", self.seeded["build_doc"], "--slice", self.seeded["slice"],
            "--target-token", "F"], env={"TMPDIR": self.work})

    def test_the_helper_refuses_and_emits_nothing(self):
        code, out, err = self.helper()
        self.assertEqual(code, 3, out)
        body = json.loads(out)
        self.assertEqual(set(body), {"error", "exit"})   # the refusal only: no invocation,
        self.assertEqual(body["exit"], 3)                 # no measurement
        self.assertIn("no reviewing invocation was emitted", body["error"])
        self.assertNotIn(testlib.SESSION, out)     # the typed answer copy is never read

    def test_the_core_records_no_verdict(self):
        code, out, err = self.helper()
        self.assertEqual(code, 3, out)
        # the only input the executor can build without the helper's invocation is refused
        document = {"protocol_version": 1, "workspace": self.seeded["workspace"],
                    "target": {"build_doc": self.seeded["build_doc"],
                               "slice": self.seeded["slice"], "base": self.seeded["base"]}}
        path = os.path.join(self.case_dir, "adapter-input.json")
        with open(path, "w") as handle:
            json.dump(document, handle)
        before = corelib.records_snapshot(self.seeded["workspace"])
        code, doc, err = corelib.core(["check-input", path])
        self.assertEqual(code, 4, err)
        self.assertFalse((doc or {}).get("verdict_recorded"))
        run_dir = os.path.join(self.work, "signoff-v2")
        self.assertFalse(os.path.exists(run_dir), "a run directory was opened")
        self.assertEqual(corelib.records_snapshot(self.seeded["workspace"]), before)


if __name__ == "__main__":
    unittest.main()
