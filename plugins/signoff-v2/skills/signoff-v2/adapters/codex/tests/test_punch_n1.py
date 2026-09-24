"""punch-N1: the first independent look at the N1 repair, end to end, on the Codex adapter.

Astra's recheck, N1 (BLOCKER): "Both helpers successfully emit null building identity when a
selected result lacks `invocation.session_id`. The core treats null as different from the reviewer,
violating the independence gate." The repair (`f7526c8`) put her exact refusal into
`building_from_result`. This module checks it end to end on the S3 seeded case shape: a legacy build
result from THIS session (no `invocation.session_id`, the typed `answer.session_id` equal to the
reviewing id), selected with `--build-result`: the helper refuses with exit 3, prints no invocation
and no session id, and nothing is written to the project (its whole tree, `.git` included), to the
build run, or to a signoff run directory.

It also pins today's reading of the question the repair left open (the punch-list report records
it): the core's input carries no fact saying whether a build result was selected (`sessions` admits
`building` and `reviewing` only), so the core reads `building: null` as "not known" and the run as
independent, exactly as it reads the helper's own no-`--build-result` invocation. The signoff
contract (section 5) puts the refusal of a selected result without an identity on the helper.
"""

import hashlib
import json
import os
import shutil
import tempfile
import unittest

import corelib
import testlib
from test_full_fix_f4 import HELPER, build_result, rollout_at

THIS_SESSION = testlib.THREAD


def tree(root):
    """{path: sha256} for every file under `root`, `.git` INCLUDED, symlinks as their text."""
    out = {}
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(base, name)
            if os.path.islink(full):
                data = os.readlink(full).encode("utf-8", "surrogateescape")
            else:
                with open(full, "rb") as handle:
                    data = handle.read()
            out[os.path.relpath(full, root)] = hashlib.sha256(data).hexdigest()
    return out


class _Case(unittest.TestCase):

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="punch-n1-")
        self.addCleanup(shutil.rmtree, self.work, True)
        self.case_dir, self.seeded = corelib.build_case(self.work)
        self.ws = self.seeded["workspace"]
        self.tmp = os.path.join(self.work, "tmp")
        os.makedirs(self.tmp)

    def helper(self, extra):
        env = rollout_at(self.work, self.ws)
        env["TMPDIR"] = self.tmp
        return testlib.run(HELPER, [
            "--workspace", self.ws, "--build-doc", self.seeded["build_doc"],
            "--slice", self.seeded["slice"], "--target-token", "F"] + extra, env=env)


class PunchN1TheLegacyResultEndToEnd(_Case):

    def test_refused_exit_3_nothing_printed_nothing_written(self):
        path = build_result(os.path.join(self.work, "build-run"), self.ws, THIS_SESSION,
                            self.seeded["build_doc"], self.seeded["slice"],
                            typed=THIS_SESSION, recorded=False)
        run_before = tree(os.path.dirname(path))
        before = tree(self.ws)
        code, out, err = self.helper(["--build-result", path])
        self.assertEqual(code, 3, out + err)
        body = json.loads(out)
        self.assertEqual(set(body), {"error", "exit"}, out)
        self.assertIn("unavailable provenance", body["error"])
        self.assertIn("no reviewing invocation was emitted", body["error"])
        self.assertNotIn(THIS_SESSION, out + err, "no session id, typed or read, is printed")
        self.assertNotIn("invocation", body, "no invocation object is printed")
        self.assertEqual(tree(self.ws), before, "the project, .git included, is untouched")
        self.assertEqual(tree(os.path.dirname(path)), run_before, "the build run is untouched")
        self.assertEqual(os.listdir(self.tmp), [], "no signoff run directory was made")

    def test_the_recorded_control_reaches_the_core_and_is_refused_there(self):
        path = build_result(os.path.join(self.work, "build-run"), self.ws, THIS_SESSION,
                            self.seeded["build_doc"], self.seeded["slice"],
                            typed=THIS_SESSION, recorded=True)
        code, out, err = self.helper(["--build-result", path])
        self.assertEqual(code, 0, out + err)
        invocation = json.loads(out)["invocation"]
        self.assertEqual(invocation["sessions"]["building"], invocation["sessions"]["reviewing"])
        corelib.independence_run(self, invocation, self.case_dir, self.seeded)


class PunchN1TheCoreReadsNullAsUnknown(_Case):
    """Pins today's behaviour: the core has no selection fact, and null reads as independent."""

    def core_input(self, invocation, name="adapter-input.json"):
        document = {"protocol_version": 1, "invocation": invocation, "workspace": self.ws,
                    "target": {"build_doc": self.seeded["build_doc"],
                               "slice": self.seeded["slice"], "base": self.seeded["base"]}}
        path = os.path.join(self.case_dir, name)
        with open(path, "w") as handle:
            json.dump(document, handle)
        return path

    def test_no_build_result_is_null_and_the_core_reads_it_as_independent(self):
        code, out, err = self.helper([])
        self.assertEqual(code, 0, out + err)
        doc = json.loads(out)
        self.assertIsNone(doc["invocation"]["sessions"]["building"])
        self.assertEqual(doc["measurement"]["building_provenance"], "unavailable")
        code, body, err = corelib.core(["check-input", self.core_input(doc["invocation"])])
        self.assertEqual(code, 0, err)
        self.assertTrue(body["independent"])

    def test_the_core_input_has_no_field_that_says_a_build_result_was_selected(self):
        code, out, err = self.helper([])
        invocation = json.loads(out)["invocation"]
        invocation["sessions"]["building_provenance"] = "build run selected"
        code, body, err = corelib.core(["check-input", self.core_input(invocation, "x.json")])
        self.assertEqual(code, 4, "the schema admits no selection fact: %s %s" % (body, err))


if __name__ == "__main__":
    unittest.main()
