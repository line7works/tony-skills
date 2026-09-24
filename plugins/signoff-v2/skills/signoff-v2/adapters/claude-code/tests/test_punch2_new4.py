"""punch2-NEW-4: a whitespace-only building session, or the reviewing id in another letter case,
passed the Claude Code helper (E13 punch list round 2, from the independent checker, MINOR).

The checker's shape: a selected build result whose `invocation.session_id` is `"   "`, or the
reviewing session id upper-cased, was accepted by `building_from_result` (`isinstance(...) and
session`), and the core, comparing `building` and `reviewing` byte for byte, read either as a
different session and let the run reach a verdict.

The harness record defines the session id as a UUID (the transcript's `<uuid>.jsonl`,
`CLAUDE_CODE_SESSION_ID`), and a UUID is the same identifier in either letter case. So the helper
strips the recorded id and refuses an empty result exactly as a missing one (exit 3, nothing
printed); an id that reads as a UUID is compared with the reviewing id as a UUID, emitted as the
reviewing id itself when they are the same session (so the core's independence refusal fires), and
in its canonical lower-case form otherwise. An id that is not a UUID is emitted stripped. The core
is unchanged.

Driven end to end: the real helper on the S3 seeded case with a build result in its own run
directory, then, for the same-session shapes, the real core's `check-input` .. `record-answer`.
"""

import json
import os
import shutil
import tempfile
import unittest

import corelib
import testlib
from test_full_fix_f4 import HELPER, build_result, session_record_at

THIS_SESSION = testlib.SESSION
OTHER = "9f1c2e3d-4b5a-4c6d-8e7f-0a1b2c3d4e5f"


class _Case(unittest.TestCase):

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="punch2-new4-")
        self.addCleanup(shutil.rmtree, self.work, True)
        self.case_dir, self.seeded = corelib.build_case(self.work)
        self.ws = self.seeded["workspace"]
        self.tmp = os.path.join(self.work, "tmp")
        os.makedirs(self.tmp)

    def helper(self, recorded_session):
        path = build_result(os.path.join(self.work, "build-run"), self.ws, recorded_session,
                            self.seeded["build_doc"], self.seeded["slice"])
        return testlib.run(HELPER, session_record_at(self.work, self.ws) + [
            "--workspace", self.ws, "--build-doc", self.seeded["build_doc"],
            "--slice", self.seeded["slice"], "--target-token", "F", "--build-result", path],
            env={"TMPDIR": self.tmp})

    def refused_as_missing(self, recorded_session):
        code, out, err = self.helper(recorded_session)
        self.assertEqual(code, 3, out + err)
        body = json.loads(out)
        self.assertEqual(set(body), {"error", "exit"}, out)
        self.assertIn("unavailable provenance", body["error"])
        self.assertIn("no reviewing invocation was emitted", body["error"])
        self.assertEqual(os.listdir(self.tmp), [], "no signoff run directory was made")

    def same_session(self, recorded_session):
        code, out, err = self.helper(recorded_session)
        self.assertEqual(code, 0, out + err)
        invocation = json.loads(out)["invocation"]
        self.assertEqual(invocation["sessions"]["reviewing"], THIS_SESSION)
        self.assertEqual(invocation["sessions"]["building"], THIS_SESSION)
        corelib.independence_run(self, invocation, self.case_dir, self.seeded)

    def other_session(self, recorded_session, emitted):
        code, out, err = self.helper(recorded_session)
        self.assertEqual(code, 0, out + err)
        invocation = json.loads(out)["invocation"]
        self.assertEqual(invocation["sessions"]["building"], emitted)
        self.assertNotEqual(invocation["sessions"]["building"], invocation["sessions"]["reviewing"])


class Punch2New4Whitespace(_Case):
    """A recorded id that is blank once stripped is refused like a missing one."""

    def test_spaces(self):
        self.refused_as_missing("   ")

    def test_tabs_and_line_endings(self):
        self.refused_as_missing("\t\r\n ")


class Punch2New4SameSessionInAnotherSpelling(_Case):
    """The reviewing id in another letter case or UUID spelling is this same session."""

    def test_upper_case(self):
        self.same_session(THIS_SESSION.upper())

    def test_padded_with_blanks(self):
        self.same_session("  %s\n" % THIS_SESSION)

    def test_upper_case_without_hyphens(self):
        self.same_session(THIS_SESSION.replace("-", "").upper())


class Punch2New4Controls(_Case):
    """Another session stays another session, in its canonical form."""

    def test_another_uuid_in_upper_case_is_emitted_canonical(self):
        self.other_session(OTHER.upper(), OTHER)

    def test_an_id_that_is_not_a_uuid_is_emitted_stripped(self):
        self.other_session(" build-session-7 ", "build-session-7")

    def test_the_recorded_same_session_is_still_refused_by_the_core(self):
        self.same_session(THIS_SESSION)


if __name__ == "__main__":
    unittest.main()
