"""vertical-v2's requests (contract sections 3.4 and 3.5; readings CR-5, CR-6 and CR-9).

One readers request per local lens, built by the copied `readers_request.py`: on Claude Code the
`claude-session` row with `repo-with-tools`, on Codex the portable `claude-opus-cli` row with the profile
it offers; the workspace a fresh copy cut for that call alone; the spec and `REVIEW.md` as documents; the
floor; never `authorized`. Every summons gets a fresh copy from the packet builder, held to its output
and to scope's fingerprint before any request is written (A4). No outside request
file exists under the run directory until `record-local` has completed: `request --outside` before it is
refused (exit 5). readers' identity is read through its own CLI before the summons, and a readers root
that the refusal rule refuses stops the run with a `refused` trace line.
"""
import json
import os
import shutil
import unittest

import testlib
import vlib


@unittest.skipUnless(vlib.records_usable() and testlib.checkout_sibling("readers") is not None,
                     "requests run after the gate, the ask and scope (records, readers' roster, jsonschema)")
class _Request(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("vreq-")
        self.addCleanup(testlib.rmtree, self.tmp)


class TheLocalRequests(_Request):

    def test_one_request_per_lens_on_the_session_row_with_tools(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        code, out, err = drive(["request", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        calls = vlib.load(run_dir, "requests-local.json")["calls"]
        self.assertEqual([c["lens"] for c in calls], ["spec", "correctness", "seams"])
        for call in calls:
            req = testlib.load_json(call["request_file"])
            self.assertEqual(req["row"], "claude-session")
            self.assertEqual(req["profile"], "repo-with-tools")
            self.assertEqual(req["workspace"], os.path.join(run_dir, "summons", call["call_id"], "workspace"))
            self.assertEqual([os.path.basename(d) for d in req["documents"]], ["spec.md", "REVIEW.md"])
            self.assertEqual(req["floor"], "opus")
            self.assertEqual(req["session_model"], "claude-opus-5-5")
            self.assertEqual(req["call_id"], "run-0001-local-%s" % call["lens"])
            self.assertEqual(req["run_dir"], os.path.join(run_dir, "readers"))
            for absent in ("authorized", "model", "effort", "isolation", "raw_path"):
                self.assertNotIn(absent, req)
        self.assertEqual(vlib.outside_files(run_dir), [])
        self.assertIn("depth LEAN", out["depth_line"])

    def test_on_codex_the_portable_claude_row_with_the_profile_it_offers(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp, harness="codex-cli")
        code, out, err = drive(["request", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        for call in vlib.load(run_dir, "requests-local.json")["calls"]:
            req = testlib.load_json(call["request_file"])
            self.assertEqual((req["row"], req["profile"]), ("claude-opus-cli", "repo"))
            self.assertNotIn("session_model", req)
            self.assertNotIn("authorized", req)
        self.assertIn("claude-opus-cli", out["route"])
        self.assertIn("runs no check", out["route"])

    def test_a_change_to_scopes_preview_never_reaches_a_summons(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        testlib.write_text(os.path.join(run_dir, "packets", "local-spec", "workspace", "src", "turnstile.py"), "# changed\n")
        testlib.write_text(os.path.join(run_dir, "packets", "local-spec", "workspace", "notes.md"), "a builder's aside\n")
        code, out, err = drive(["request", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))
        req = testlib.load_json(vlib.load(run_dir, "requests-local.json")["calls"][0]["request_file"])
        self.assertFalse(os.path.exists(os.path.join(req["workspace"], "notes.md")))
        self.assertNotEqual(testlib.read_text(os.path.join(req["workspace"], "src", "turnstile.py")), "# changed\n")

    def test_every_call_gets_its_own_copy(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        self.assertEqual(drive(["request", "--run-dir", run_dir])[0], 0)
        calls = vlib.load(run_dir, "requests-local.json")["calls"]
        workspaces = [testlib.load_json(c["request_file"])["workspace"] for c in calls]
        self.assertEqual(len(set(workspaces)), len(calls))

    def test_a_copy_left_from_an_earlier_attempt_is_refused_and_nothing_is_built(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        testlib.write_text(os.path.join(run_dir, "summons", "run-0001-local-seams", "workspace", "x.py"), "X = 1\n")
        code, out, err = drive(["request", "--run-dir", run_dir])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("single-use", out["reason"])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-local.json")))
        self.assertEqual(sorted(os.listdir(os.path.join(run_dir, "summons"))), ["run-0001-local-seams"])

    def test_a_claude_code_run_without_the_session_model_is_refused(self):
        ws, info = vlib.make_repo(self.tmp, records=True)
        run_dir = os.path.join(self.tmp, "run")
        doc = vlib.make_input(ws, run_dir)
        del doc["station"]["session_model"]
        path = vlib.write(self.tmp, "input.json", doc)
        drive = vlib.Driver(self.tmp)
        self.assertEqual(drive(["check-input", path])[0], 0)
        code, out, err = vlib.through_ask(drive, self.tmp, run_dir)
        self.assertEqual(drive(["scope", "--run-dir", run_dir])[0], 0)
        code, out, err = drive(["request", "--run-dir", run_dir])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("session_model", out["reason"])


class TheSummonsFolder(_Request):
    """C1A5-3: `request` refuses, before any copy is written, when the run directory's `summons` folder is a link
    or resolves outside the run directory; the outside folder stays empty and no request file is written."""

    def plant(self, run_dir):
        outside = os.path.join(self.tmp, "OUTSIDE")
        os.makedirs(outside)
        summons = os.path.join(run_dir, "summons")
        if os.path.isdir(summons) and not os.path.islink(summons):
            os.rename(summons, os.path.join(run_dir, "summons-moved"))
        os.symlink(outside, summons)
        return outside

    def assert_refused(self, code, out, err, outside):
        self.assertEqual(code, 5, (out, err))
        self.assertIn("summons", out["reason"])
        self.assertIn("link", out["reason"])
        self.assertEqual(os.listdir(outside), [])

    def test_a_linked_summons_folder_refuses_the_local_requests_and_writes_nothing_outside(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        outside = self.plant(run_dir)
        code, out, err = drive(["request", "--run-dir", run_dir])
        self.assert_refused(code, out, err, outside)
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-local.json")))
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests")))
        self.assertEqual(vlib.load(run_dir, "checkpoint.json")["phase"], "scoped")

    def test_a_linked_summons_folder_refuses_the_outside_requests_and_writes_nothing_outside(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp)
        outside = self.plant(run_dir)
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assert_refused(code, out, err, outside)
        self.assertEqual(vlib.outside_files(run_dir), [])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-outside.json")))

    def test_a_linked_summons_folder_refuses_a_resend(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        outside = self.plant(run_dir)
        code, out, err = drive(["request", "--run-dir", run_dir, "--resend", "spec", "--status", "empty"])
        self.assert_refused(code, out, err, outside)
        self.assertEqual(vlib.load(run_dir, "requests-local.json")["resent"], [])

    def test_a_summons_link_to_a_folder_inside_the_run_directory_is_refused_too(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        inside = os.path.join(run_dir, "elsewhere")
        os.makedirs(inside)
        os.symlink(inside, os.path.join(run_dir, "summons"))
        code, out, err = drive(["request", "--run-dir", run_dir])
        self.assert_refused(code, out, err, inside)


class LocalBeforeOutside(_Request):

    def test_an_outside_request_before_record_local_is_refused_and_no_file_exists(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("record-local", out["reason"])
        self.assertEqual(drive(["request", "--run-dir", run_dir])[0], 0)
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 5, (out, err))
        self.assertEqual(vlib.outside_files(run_dir), [])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-outside.json")))


class LocalFirstRestsOnTheRecord(_Request):
    """C1A-4, then A4's receipt (test_receipt.py forges each piece): `request --outside` refuses unless the
    local review is on record as record-local wrote it, whatever the checkpoint's phase says."""

    def force_phase(self, run_dir, phase):
        path = os.path.join(run_dir, "checkpoint.json")
        checkpoint = testlib.load_json(path)
        checkpoint["phase"] = phase
        testlib.write_json(path, checkpoint)

    def test_a_hand_written_checkpoint_with_no_local_record_is_refused(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        self.force_phase(run_dir, "recorded-local")
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("local-receipt.json", out["reason"])
        self.assertEqual(vlib.outside_files(run_dir), [])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-outside.json")))

    def test_a_local_record_that_stopped_or_names_other_calls_is_refused(self):
        drive, run_dir, ws, info = vlib.through_local_requests(self.tmp)
        self.force_phase(run_dir, "recorded-local")
        calls = [{"call_id": c, "row": "claude-session", "lens": c.rsplit("-", 1)[-1], "status": "ok"}
                 for c in vlib.local_ids(run_dir)]
        for doc in ({"calls": calls, "findings": [], "tried": [], "method": None, "stopped": "local-incomplete"},
                    {"calls": calls[:1], "findings": [], "tried": [], "method": "read"},
                    {"calls": [dict(c, status="empty") for c in calls], "findings": [], "tried": [], "method": "read"},
                    ["not", "an", "object"]):
            testlib.write_json(os.path.join(run_dir, "local.json"), doc)
            code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
            self.assertEqual(code, 5, (doc, out, err))
            self.assertEqual(vlib.outside_files(run_dir), [])

    def test_the_legal_path_still_releases_the_outside_requests(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp)
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(len(vlib.outside_files(run_dir)), 2)


class SurvivorsContinue(_Request):
    """C1A-1: a row the ask showed as dropped and the owner named is recorded with its status and reason and
    never sent; the run continues with the survivors."""

    def test_the_only_named_row_dropped_is_recorded_and_the_run_reaches_the_verdict(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra",), dropped=("gpt-astra",))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "verdict")
        self.assertEqual(vlib.outside_files(run_dir), [])
        recorded = vlib.load(run_dir, "requests-outside.json")
        self.assertEqual(recorded["calls"], [])
        self.assertEqual(recorded["dropped"], [{"row": "gpt-astra", "status": "dropped at suggest",
                                                "reason": "dropped: gpt-astra is unavailable"}])
        code, out, err = drive(["verdict", "--run-dir", run_dir])
        self.assertEqual(code, 0, (out, err))

    def test_a_dropped_row_beside_a_live_one_sends_the_live_one_only(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra", "gemini"),
                                                             dropped=("gpt-astra",))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["next"], "record-outside")
        self.assertEqual([c["row"] for c in out["calls"]], ["gemini"])
        self.assertEqual([os.path.basename(p) for p in vlib.outside_files(run_dir)], ["run-0001-gemini.json"])
        self.assertEqual([d["row"] for d in vlib.load(run_dir, "requests-outside.json")["dropped"]], ["gpt-astra"])

    def test_a_row_the_answer_did_not_name_is_still_refused(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra",), dropped=("gpt-astra",))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside", "--row", "gemini"])
        self.assertEqual(code, 5, (out, err))
        self.assertEqual(vlib.outside_files(run_dir), [])


class TheRowSubset(_Request):
    """C1A2-1 and C1A2-2: a `--row` subset never leaves a named, available row unsent and unnamed, and a row
    named twice is refused; nothing is built either way."""

    def assertNothingOutside(self, run_dir):
        self.assertEqual(vlib.outside_files(run_dir), [])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-outside.json")))
        self.assertEqual(vlib.load(run_dir, "checkpoint.json")["phase"], "recorded-local")

    def test_a_subset_that_leaves_out_a_named_available_row_is_refused(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra", "gemini"))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside", "--row", "gemini"])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("gpt-astra", out["reason"])
        self.assertNothingOutside(run_dir)

    def test_a_subset_of_dropped_rows_alone_never_skips_a_named_survivor(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra", "gemini"),
                                                             dropped=("gpt-astra",))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside", "--row", "gpt-astra"])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("gemini", out["reason"])
        self.assertNothingOutside(run_dir)

    def test_a_row_named_twice_is_refused(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gemini",))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside", "--row", "gemini", "--row", "gemini"])
        self.assertEqual(code, 5, (out, err))
        self.assertIn("twice", out["reason"])
        self.assertNothingOutside(run_dir)

    def test_a_subset_naming_every_available_row_still_goes(self):
        drive, run_dir, ws, info = vlib.through_record_local(self.tmp, rows=("gpt-astra", "gemini"),
                                                             dropped=("gpt-astra",))
        code, out, err = drive(["request", "--run-dir", run_dir, "--outside", "--row", "gemini"])
        self.assertEqual(code, 0, (out, err))
        self.assertEqual([c["row"] for c in out["calls"]], ["gemini"])


class TheResend(_Request):

    def test_one_resend_per_lens_on_a_retryable_status_with_a_fresh_call_id(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        drive(["request", "--run-dir", run_dir])
        code, out, err = drive(["request", "--run-dir", run_dir, "--resend", "seams", "--status", "transport-failed"])
        self.assertEqual(code, 0, (out, err))
        ids = vlib.local_ids(run_dir)
        self.assertIn("run-0001-local-seams-2", ids)
        code, out, err = drive(["request", "--run-dir", run_dir, "--resend", "seams", "--status", "empty"])
        self.assertEqual(code, 5, (out, err))

    def test_a_resend_gets_a_fresh_copy_and_never_the_first_fleets_scratch(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        drive(["request", "--run-dir", run_dir])
        first = os.path.join(run_dir, "summons", "run-0001-local-spec", "workspace")
        testlib.write_text(os.path.join(first, ".pytest_cache", "v", "lastfailed"), "{}\n")
        testlib.write_text(os.path.join(run_dir, "packets", "local-seams", "mandate.md"), "a changed mandate\n")
        code, out, err = drive(["request", "--run-dir", run_dir, "--resend", "spec", "--status", "incomplete"])
        self.assertEqual(code, 0, (out, err))
        req = testlib.load_json(out["call"]["request_file"])
        self.assertEqual(req["workspace"], os.path.join(run_dir, "summons", "run-0001-local-spec-2", "workspace"))
        self.assertFalse(os.path.exists(os.path.join(req["workspace"], ".pytest_cache")))
        code, out, err = drive(["request", "--run-dir", run_dir, "--resend", "seams", "--status", "incomplete"])
        self.assertEqual(code, 0, (out, err))
        mandate = testlib.read_text(testlib.load_json(out["call"]["request_file"])["mandate"])
        self.assertIn("lens: seams", mandate)

    def test_a_deterministic_refusal_is_never_resent(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        drive(["request", "--run-dir", run_dir])
        for status in ("unknown-model", "invalid-request", "lane-unavailable", "profile-unsupported",
                       "version-mismatch", "floor-refused"):
            code, out, err = drive(["request", "--run-dir", run_dir, "--resend", "spec", "--status", status])
            self.assertEqual(code, 5, (status, out, err))


class ReadersIdentity(_Request):

    def test_readers_identity_is_read_through_its_cli_and_recorded(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        drive(["request", "--run-dir", run_dir])
        readers = vlib.load(run_dir, "requests-local.json")["readers"]
        self.assertEqual(readers["identity"]["name"], "readers")
        self.assertEqual(readers["identity"]["interface_version"], 1)
        self.assertIn(readers["route"], ("3a", "argument"))

    def test_a_readers_root_under_a_v1_folder_is_refused_with_a_trace_line(self):
        drive, run_dir, ws, info = vlib.through_scope(self.tmp)
        planted = os.path.join(self.tmp, "plugins", "sh" + "ip")
        shutil.copytree(testlib.checkout_sibling("readers"), planted,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        code, out, err = drive(["request", "--run-dir", run_dir, "--readers-root", planted])
        self.assertEqual(code, 10, (out, err))
        self.assertEqual(out["stop_tag"], "station-refused")
        lines = [json.loads(l) for l in open(os.path.join(run_dir, "trace.jsonl"))]
        self.assertEqual([l["kind"] for l in lines], ["refused"])
        self.assertIn("v1-root", lines[0]["refusal"]["rules"])
        self.assertFalse(os.path.exists(os.path.join(run_dir, "requests-local.json")))


if __name__ == "__main__":
    unittest.main()
