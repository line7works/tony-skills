"""The blind review (brief 3.7, required test 7): `request` and `save-take`.

One readers request per named reviewer, the scope doc the single document and nothing else,
`profile: starved`, the mandate equal to the instruction the lane contract quotes; `authorized`
only on an outside row the input's `owner_word` names, never on a Claude row; readers' own
`validate` accepts the request. A take is saved verbatim before any triage, under the v1 review
home and in the run directory, and a repeat on the same lane and day takes `-2`, `-3`.
"""
import json
import os
import re
import subprocess
import unittest

import archlib
import testlib

CONTRACT = os.path.join(testlib.REF, "architect-v2-contract.md")
ROSTER = testlib.readers_roster()


def quoted_mandate():
    with open(CONTRACT, encoding="utf-8") as fh:
        text = fh.read()
    match = re.search(r"<!-- mandate -->\n> (.+?)\n<!-- /mandate -->", text, re.S)
    return match.group(1).replace("\n> ", " ") if match else None


@unittest.skipIf(ROSTER is None, "no readers component beside this core (the installed shape)")
class Request(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-review-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp)

    def written(self, **extra):
        run = archlib.ArchRun(self.tmp, self.ws, **extra)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 0, out + err)
        run.record(archlib.clean_answer())
        self.assertEqual(run.write()[0], 0)
        return run

    def test_the_packet_is_the_scope_doc_alone(self):
        run = self.written(owner_word={"rows": ["gpt-astra"], "words": "send it to gpt-astra"})
        code, doc, out, err = run.request("gpt-astra", "claude-session", roster=ROSTER, session_model="claude-model-x")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(len(doc["requests"]), 2)
        scope = os.path.join(self.ws, archlib.SCOPE_REL)
        for entry in doc["requests"]:
            req = testlib.load_json(entry["path"])
            self.assertEqual(req["documents"], [scope])
            self.assertNotIn("workspace", req)
            self.assertEqual(req["profile"], "starved")
            self.assertEqual(req["protocol_version"], 1)
            self.assertEqual(req["mandate"], archlib.MANDATE)
            self.assertEqual(req["mandate"], quoted_mandate())
            self.assertEqual(set(req) - {"protocol_version", "run_id", "call_id", "row", "mandate", "documents",
                                         "profile", "authorized", "session_model", "model"}, set())
            self.assertTrue(entry["path"].startswith(run.run_dir + os.sep))
        by_row = {testlib.load_json(e["path"])["row"]: testlib.load_json(e["path"]) for e in doc["requests"]}
        self.assertIs(by_row["gpt-astra"].get("authorized"), True)
        self.assertNotIn("authorized", by_row["claude-session"])
        self.assertEqual(by_row["claude-session"]["session_model"], "claude-model-x")
        self.assertNotIn("session_model", by_row["gpt-astra"])
        self.assertEqual(len({r["call_id"] for r in by_row.values()}), 2)
        self.assertEqual(len({r["run_id"] for r in by_row.values()}), 1)

    def test_authorized_only_where_the_owner_word_is(self):
        run = self.written()
        code, doc, out, err = run.request("gpt-astra", "gemini", roster=ROSTER)
        self.assertEqual(code, 0, out + err)
        for entry in doc["requests"]:
            self.assertNotIn("authorized", testlib.load_json(entry["path"]))
        run2 = archlib.ArchRun(self.tmp, self.ws, name="run-b", run_id="run-0002",
                               owner_word={"rows": ["gemini", "claude-session"], "words": "gemini and claude"})
        run2.to_harvest()
        run2.record(archlib.clean_answer(run_id="run-0002"))
        run2.write()
        code, doc, out, err = run2.request("gpt-astra", "gemini", "claude-session", roster=ROSTER)
        self.assertEqual(code, 0, out + err)
        got = {testlib.load_json(e["path"])["row"]: testlib.load_json(e["path"]).get("authorized")
               for e in doc["requests"]}
        self.assertEqual(got, {"gpt-astra": None, "gemini": True, "claude-session": None})

    def test_a_docless_run_builds_no_request(self):
        ws = testlib.git_workspace(self.tmp, "plain")
        staging = os.path.join(self.tmp, "staging")
        os.makedirs(staging)
        run = archlib.ArchRun(self.tmp, ws, staging, name="run-d")
        run.check_input()
        run.select("scope")
        run.select("architecture", "bench-counter")
        run.harvest()
        code, doc, out, err = run.request("gpt-astra", roster=ROSTER)
        self.assertEqual(code, 2, out + err)

    def test_an_unknown_row_is_usage(self):
        run = self.written()
        self.assertEqual(run.request("no-such-row", roster=ROSTER)[0], 2)

    def not_a_folder(self, run, plant):
        """`request` with `plant(<run>/requests)` in place: exit 1, the stop's sentence on stderr naming the path,
        stdout empty, no traceback, nothing written in the run directory or the workspace."""
        folder = os.path.join(run.run_dir, "requests")
        plant(folder)
        before_run = archlib.listing(run.run_dir)
        before_ws = archlib.listing(self.ws)
        code, doc, out, err = run.request("gpt-astra", roster=ROSTER)
        self.assertEqual(code, 1, out + err)
        self.assertEqual(out, "")
        self.assertNotIn("Traceback", err)
        self.assertIn(folder, err)
        self.assertIn("unreadable run directory", err)
        # slice 3b round 3 R6(b): the path the stop names is the request this call would write, never a placeholder
        self.assertIn("stands on the way to %s)" % os.path.join(folder, "run-0001-review-gpt-astra.json"), err)
        self.assertIn("nothing was written", err)
        self.assertIn("run `request` again", err)
        self.assertEqual(archlib.listing(run.run_dir), before_run)
        self.assertEqual(archlib.listing(self.ws), before_ws)
        return folder

    def test_a_regular_file_where_the_requests_folder_goes_is_exit_1_and_nothing_is_written(self):
        """Slice 3b R2 (the control room's wording, C4): a regular file at `<run>/requests` is an unreadable run
        directory, exit 1 before any write; the run stays where it was, so the file removed, `request` runs."""
        run = self.written()
        folder = self.not_a_folder(run, lambda path: testlib.write_text(path, "not a folder\n"))
        self.assertEqual(testlib.read_text(folder), "not a folder\n")
        os.remove(folder)
        code, doc, out, err = run.request("gpt-astra", roster=ROSTER)
        self.assertEqual(code, 0, out + err)
        self.assertTrue(os.path.isfile(doc["requests"][0]["path"]))

    def test_a_symlink_to_a_file_or_to_nothing_inside_the_run_is_exit_1(self):
        """A symlink to a regular file is no directory either, and neither is a link that leads to nothing; a link
        that leads out of the run directory stays `request-outside-run` (exit 5, ASymlinkedRequestsFolder)."""
        run = self.written()

        def to_file(path):
            target = os.path.join(run.run_dir, "requests-file")
            testlib.write_text(target, "a file\n")
            os.symlink(target, path)
        folder = self.not_a_folder(run, to_file)
        os.remove(folder)
        self.not_a_folder(run, lambda path: os.symlink(os.path.join(run.run_dir, "no-such-folder"), path))

    @unittest.skipIf(os.geteuid() == 0, "root lists and writes any folder")
    def test_a_requests_folder_it_cannot_list_is_exit_1_and_nothing_is_written(self):
        """Slice 3b round 2 R1 (CA3B-1): a `requests` folder the process cannot list or write is the same unreadable
        run directory, exit 1 before the folder is read; its mode restored, `request` runs."""
        run = self.written()

        def locked(path):
            os.makedirs(path)
            os.chmod(path, 0)
            self.addCleanup(os.chmod, path, 0o755)
        folder = self.not_a_folder(run, locked)
        os.chmod(folder, 0o755)
        code, doc, out, err = run.request("gpt-astra", roster=ROSTER)
        self.assertEqual(code, 0, out + err)

    def test_a_folder_where_the_receipt_goes_is_exit_1_and_nothing_is_written(self):
        """Slice 3b round 2 R5: every request write also rewrites `<run>/receipt.json`; a folder planted there (the
        file removed by hand) is exit 1 before the first request lands, never a request written and then a
        traceback."""
        run = self.written()
        receipt = os.path.join(run.run_dir, "receipt.json")
        os.remove(receipt)
        os.makedirs(receipt)
        before_run = archlib.listing(run.run_dir)
        code, doc, out, err = run.request("gpt-astra", roster=ROSTER)
        self.assertEqual(code, 1, out + err)
        self.assertNotIn("Traceback", err)
        self.assertIn("unreadable run directory: %s is a folder where this run writes a file" % receipt, err)
        self.assertIn("run `request` again", err)
        self.assertEqual(archlib.listing(run.run_dir), before_run)
        self.assertFalse(os.path.exists(os.path.join(run.run_dir, "requests")))

    def test_a_symlink_to_a_folder_inside_the_run_is_a_folder(self):
        run = self.written()
        target = os.path.join(run.run_dir, "requests-real")
        os.makedirs(target)
        os.symlink(target, os.path.join(run.run_dir, "requests"))
        code, doc, out, err = run.request("gpt-astra", roster=ROSTER)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(os.listdir(target), [os.path.basename(doc["requests"][0]["path"])])

    @unittest.skipIf(testlib.readers_entry() is None, "no readers entry beside this core")
    def test_readers_validate_accepts_it(self):
        run = self.written(owner_word={"rows": ["gpt-astra"], "words": "send it to gpt-astra"})
        code, doc, out, err = run.request("claude-session", "gpt-astra", "gemini", roster=ROSTER,
                                          session_model="opus")
        self.assertEqual(code, 0, out + err)
        home = os.path.join(self.tmp, "readers-home")
        testlib.write_json(os.path.join(home, "plugins", "readers", "last-picks.json"),
                           {"protocol_version": 1, "picks": {}})
        env = testlib.base_env({"READERS_CHECKOUT": home, "READERS_RUN_ROOT": os.path.join(self.tmp, "readers-runs")})
        verdicts = {}
        for entry in doc["requests"]:
            proc = subprocess.run(["/bin/sh", testlib.readers_entry(), "validate", entry["path"]],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=run.cwd)
            text = proc.stdout.decode().strip()
            verdicts[entry["row"]] = json.loads(text).get("status") if text.startswith("{") else text
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "readers-runs")), "validate writes nothing")
        self.assertEqual(verdicts["claude-session"], "valid", verdicts)
        self.assertEqual(verdicts["gemini"], "unauthorized", "no word for gemini, so readers refuses it: %s" % verdicts)
        if verdicts["gpt-astra"] == "lane-unavailable":
            self.skipTest("gpt-astra's transport is absent from this shell (readers says lane-unavailable); "
                          "claude-session and gemini were checked: %s" % verdicts)
        self.assertEqual(verdicts["gpt-astra"], "valid", verdicts)


class TheRosterResolver(unittest.TestCase):
    """Slice 3b R9 (A7 section 5): `review.readers_roster` is the shared `station_core.readers_roster.find`, route
    3a (the checkout sibling) then route 3b (the installed shape, the highest canonical version), keeping this
    core's own `RosterMissing` and its "pass --roster FILE" (exit 2 at `request`)."""

    ROSTER_REL = os.path.join("skills", "readers", "assets", "roster.json")

    def setUp(self):
        testlib.add_scripts_to_path()
        from architect_core import review
        self.review = review
        self.tmp = testlib.make_scratch("arch-roster-")
        self.addCleanup(testlib.rmtree, self.tmp)

    def plugin(self, root, name, version, roster=True):
        testlib.write_json(os.path.join(root, ".claude-plugin", "plugin.json"), {"name": name, "version": version})
        if roster:
            testlib.write_json(os.path.join(root, self.ROSTER_REL), {"rows": [{"id": "gpt-astra", "provider": "o"}]})
        return root

    def test_route_3a_the_checkout_sibling(self):
        plugins = os.path.join(self.tmp, "plugins")
        me = self.plugin(os.path.join(plugins, "architect-v2"), "architect-v2", "0.1.0", roster=False)
        readers = self.plugin(os.path.join(plugins, "readers"), "readers", "0.3.0")
        self.assertEqual(os.path.normpath(self.review.readers_roster(me)), os.path.join(readers, self.ROSTER_REL))

    def test_route_3b_the_installed_shape_takes_the_highest_version(self):
        market = os.path.join(self.tmp, "cache", "market")
        me = self.plugin(os.path.join(market, "architect-v2", "0.1.0"), "architect-v2", "0.1.0", roster=False)
        for version in ("0.3.0", "0.10.0", "0.9.9"):
            self.plugin(os.path.join(market, "readers", version), "readers", version)
        self.plugin(os.path.join(market, "readers", "01.2"), "readers", "01.2")
        self.assertEqual(os.path.normpath(self.review.readers_roster(me)),
                         os.path.join(market, "readers", "0.10.0", self.ROSTER_REL))

    def test_nothing_found_is_this_cores_roster_missing_naming_the_places_looked(self):
        plugins = os.path.join(self.tmp, "plugins")
        me = self.plugin(os.path.join(plugins, "architect-v2"), "architect-v2", "0.1.0", roster=False)
        self.plugin(os.path.join(plugins, "readers"), "readers", "0.3.0", roster=False)
        with self.assertRaises(self.review.RosterMissing) as caught:
            self.review.readers_roster(me)
        message = str(caught.exception)
        self.assertTrue(message.endswith("; pass --roster FILE"), message)
        self.assertIn("readers' roster was not found", message)
        self.assertIn(os.path.join(plugins, "architect-v2", os.pardir, "readers") + " (no roster)", message)
        self.assertIn(os.path.join(plugins, "architect-v2", os.pardir, os.pardir, "readers") + " (no such directory)",
                      message)
        self.assertIsInstance(caught.exception, LookupError)

    def test_a_symlinked_plugin_root_returns_the_path_find_checked(self):
        """Slice 3b round 2 R4 (the checker's observation 1): the path is the one the shared `find` validated, not
        its `normpath`: through a symlinked plugin root the physical sibling holds the roster and the lexical sibling
        does not exist, and the path returned is a file."""
        real = os.path.join(self.tmp, "real", "plugins")
        self.plugin(os.path.join(real, "architect-v2"), "architect-v2", "0.1.0", roster=False)
        readers = self.plugin(os.path.join(real, "readers"), "readers", "0.3.0")
        linked = os.path.join(self.tmp, "linked")
        os.makedirs(linked)
        me = os.path.join(linked, "architect-v2")
        os.symlink(os.path.join(real, "architect-v2"), me)
        self.assertFalse(os.path.exists(os.path.join(linked, "readers")))
        path = self.review.readers_roster(me)
        self.assertTrue(os.path.isfile(path), path)
        self.assertTrue(os.path.samefile(path, os.path.join(readers, self.ROSTER_REL)))

    def test_the_old_helpers_are_gone(self):
        self.assertFalse(hasattr(self.review, "_manifest_name"))
        self.assertFalse(hasattr(self.review, "_version_key"))

    @unittest.skipIf(ROSTER is None, "no readers component beside this core (the installed shape)")
    def test_request_without_roster_reads_the_checkout_sibling(self):
        ws = archlib.repo_workspace(self.tmp)
        run = archlib.ArchRun(self.tmp, ws)
        self.assertEqual(run.to_harvest()[0], 0)
        self.assertEqual(run.record(archlib.clean_answer())[0], 0)
        self.assertEqual(run.write()[0], 0)
        code, doc, out, err = run.cli("request", "--run-dir", run.run_dir, "--row", "gpt-astra")
        self.assertEqual(code, 0, out + err)
        self.assertEqual([r["row"] for r in doc["requests"]], ["gpt-astra"])


class SaveTake(unittest.TestCase):

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-take-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp)
        self.run = archlib.ArchRun(self.tmp, self.ws)
        self.run.to_harvest()
        self.run.record(archlib.clean_answer())
        self.assertEqual(self.run.write()[0], 0)
        code, doc, out, err = self.run.request("gpt-astra", "gemini", "claude-session", session_model="model-x")
        self.assertEqual(code, 0, out + err)

    def take(self, text, name="take.md"):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as fh:
            fh.write(text.encode("utf-8"))
        return path

    def test_verbatim_with_the_repeat_rule(self):
        body = "Walkthrough target: Sam\n\n  keeps  its   spacing\n"
        paths = []
        for n in range(3):
            code, doc, out, err = self.run.save_take("gpt-astra", self.take(body, "t%d.md" % n), model="gpt-model-x")
            self.assertEqual(code, 0, out + err)
            paths.append(doc["path"])
        base = os.path.join(self.ws, "docs", "reviews", "%s-architect-review-turnstile-gpt" % archlib.TODAY)
        self.assertEqual(paths, [base + ".md", base + "-2.md", base + "-3.md"])
        for path in paths:
            text = testlib.read_text(path)
            first, rest = text.split("\n", 1)
            self.assertIn("gpt-astra", first)
            self.assertIn("gpt-model-x", first)
            self.assertIn("sandbox-enforced", first)
            self.assertIn("/tmp/sidecar.json", first)
            self.assertEqual(rest, "\n" + body)
        copies = sorted(os.listdir(os.path.join(self.run.run_dir, "takes")))
        self.assertEqual(copies, sorted(os.path.basename(p) for p in paths))
        receipt = testlib.load_json(os.path.join(self.run.run_dir, "receipt.json"))
        recorded = [w["path"] for w in receipt["writes"] if w["kind"] == "document"]
        for path in paths:
            self.assertIn(path, recorded)

    def test_an_empty_take_is_refused(self):
        code, doc, out, err = self.run.save_take("gemini", self.take("  \n\n"))
        self.assertEqual(code, 5, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "reviews")))

    def test_a_row_that_is_no_roster_id_is_usage(self):
        before = archlib.listing(self.ws)
        for row in ("../../escape", "GPT Astra", ""):
            code, doc, out, err = self.run.save_take(row, self.take("a take\n"))
            self.assertEqual(code, 2, (row, out + err))
        self.assertEqual(archlib.listing(self.ws), before)

    def test_a_first_line_field_with_a_line_break_is_usage(self):
        code, doc, out, err = self.run.save_take("gemini", self.take("a take\n"), model="model-x\n## injected")
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "reviews")))

    def planted(self, run, node, ws=None):
        """`save-take` with a regular file at `node`: exit 1, the stop's sentence naming it, stdout empty, no
        traceback, nothing written in the run directory or the workspace; the file is removed after."""
        testlib.write_text(node, "not a folder\n")
        ws = ws or self.ws
        before_run, before_ws = archlib.listing(run.run_dir), archlib.listing(ws)
        code, doc, out, err = run.save_take("gpt-astra", self.take("a take\n"))
        self.assertEqual(code, 1, out + err)
        self.assertEqual(out, "")
        self.assertNotIn("Traceback", err)
        self.assertIn("unreadable run directory: %s is not a folder this run can write" % node, err)
        self.assertIn("nothing was written and the run stays where it was", err)
        self.assertIn("run `save-take` again", err)
        self.assertEqual(archlib.listing(run.run_dir), before_run)
        self.assertEqual(archlib.listing(ws), before_ws)
        os.remove(node)

    def one_take(self, run, doc, folder):
        self.assertEqual(sorted(os.listdir(folder)), [os.path.basename(doc["path"])])
        self.assertFalse(doc["path"].endswith("-2.md"), doc["path"])
        self.assertEqual(len(testlib.load_json(os.path.join(run.run_dir, "takes.json"))), 1)

    def test_a_file_where_the_takes_folder_goes_is_exit_1_and_the_retry_saves_one_take(self):
        """Slice 3b round 2 R1 (CA3B-1): the take no longer lands in docs/reviews before the traceback; the
        file removed, the retry saves ONE take, no `-2` beside an orphan."""
        self.planted(self.run, os.path.join(self.run.run_dir, "takes"))
        code, doc, out, err = self.run.save_take("gpt-astra", self.take("a take\n"))
        self.assertEqual(code, 0, out + err)
        self.one_take(self.run, doc, os.path.join(self.ws, "docs", "reviews"))

    def test_a_file_where_the_review_folder_goes_is_exit_1(self):
        self.planted(self.run, os.path.join(self.ws, "docs", "reviews"))
        code, doc, out, err = self.run.save_take("gpt-astra", self.take("a take\n"))
        self.assertEqual(code, 0, out + err)
        self.one_take(self.run, doc, os.path.join(self.ws, "docs", "reviews"))

    def test_report_only_files_where_the_reviews_and_takes_folders_go_are_exit_1(self):
        ws = archlib.repo_workspace(self.tmp, name="ws-ro")
        run = archlib.ArchRun(self.tmp, ws, name="run-ro", report_only=True)
        self.assertEqual(run.to_harvest()[0], 0)
        self.assertEqual(run.record(archlib.clean_answer())[0], 0)
        self.assertEqual(run.write()[0], 0)
        self.assertEqual(run.request("gpt-astra")[0], 0)
        self.planted(run, os.path.join(run.run_dir, "reviews"), ws)
        self.planted(run, os.path.join(run.run_dir, "takes"), ws)
        code, doc, out, err = run.save_take("gpt-astra", self.take("a take\n"))
        self.assertEqual(code, 0, out + err)
        self.one_take(run, doc, os.path.join(run.run_dir, "reviews"))

    def test_a_folder_where_takes_json_goes_is_exit_1(self):
        """Slice 3b round 2 R5: `<run>/takes.json` is written after both copies; a folder there is refused before
        the first."""
        node = os.path.join(self.run.run_dir, "takes.json")
        os.makedirs(node)
        before_run, before_ws = archlib.listing(self.run.run_dir), archlib.listing(self.ws)
        code, doc, out, err = self.run.save_take("gpt-astra", self.take("a take\n"))
        self.assertEqual(code, 1, out + err)
        self.assertNotIn("Traceback", err)
        self.assertIn("unreadable run directory: %s is a folder where this run writes a file" % node, err)
        self.assertEqual(archlib.listing(self.run.run_dir), before_run)
        self.assertEqual(archlib.listing(self.ws), before_ws)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "docs", "reviews")))
        os.rmdir(node)
        code, doc, out, err = self.run.save_take("gpt-astra", self.take("a take\n"))
        self.assertEqual(code, 0, out + err)
        self.one_take(self.run, doc, os.path.join(self.ws, "docs", "reviews"))

    def test_the_lane_names(self):
        code, doc, out, err = self.run.save_take("claude-session", self.take("a take\n"))
        self.assertEqual(code, 0, out + err)
        self.assertTrue(doc["path"].endswith("-architect-review-turnstile-claude.md"), doc["path"])
        code, doc, out, err = self.run.save_take("gemini", self.take("a take\n"))
        self.assertTrue(doc["path"].endswith("-architect-review-turnstile-gemini.md"), doc["path"])


class _Rulings(unittest.TestCase):
    """A run with its doc written, the visual rendered, the publish recorded and one take saved."""

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-rulings-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp)
        self.run = archlib.ArchRun(self.tmp, self.ws)
        self.run.to_harvest()
        self.first = archlib.clean_answer()
        self.assertEqual(self.run.record(self.first)[0], 0)
        self.assertEqual(self.run.write()[0], 0)
        self.assertEqual(self.run.render()[0], 0)
        self.assertEqual(self.run.publish("https://example.invalid/artifact/turnstile")[0], 0)
        self.assertEqual(self.run.request("gpt-astra")[0], 0)
        take = os.path.join(self.tmp, "take.md")
        testlib.write_text(take, "a module and a reset, no server\n")
        code, doc, out, err = self.run.save_take("gpt-astra", take, model="gpt-model-x")
        self.assertEqual(code, 0, out + err)
        self.take_path = doc["path"]

    def amended(self, **over):
        a = archlib.clean_answer(review={"outcome": "done", "spine": "a module, no server"},
                                 rulings=[{"disagreement": "the take cuts reset()", "ruling": "reset() stays",
                                           "reviewers": ["gpt"], "changes": [],
                                           "trace": {"kind": "question", "ref": "Q5"}}])
        a["questions"].append({"id": "Q5", "text": "Keep reset()?", "touches": [], "answer": "yes, it stays"})
        a.update(over)
        return a


class TheRulingsRound(_Rulings):
    """After the takes: an amended answer carries the review's outcome and its rulings; the doc
    changes only where a ruling says so, and the visual and the publish are redone before report."""

    def test_the_second_round_lands_and_report_completes(self):
        code, doc, out, err = self.run.record(self.amended())
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.run.write()[0], 0)
        self.assertEqual(self.run.report()[0], 2, "the visual is redone after the rulings before report")
        self.assertEqual(self.run.render()[0], 0)
        self.assertEqual(self.run.report()[0], 2, "the republish is recorded before report")
        self.assertEqual(self.run.publish("https://example.invalid/artifact/turnstile")[0], 0)
        code, doc, out, err = self.run.report()
        self.assertEqual(code, 10, out + err)
        self.assertEqual(doc["status"], "completed", out)
        text = testlib.read_text(os.path.join(self.ws, "docs", "architecture", "%s-turnstile.md" % archlib.TODAY))
        rel = os.path.relpath(self.take_path, self.ws)
        self.assertIn("Blind review: %s (gpt-model-x, %s)\n" % (rel, archlib.TODAY), text)
        self.assertIn("Rulings: blind review: agreed on a module, no server; 1 disagreement: "
                      "1. the take cuts reset(): reset() stays (gpt)", text)
        self.assertEqual(testlib.read_text(self.take_path).split("\n", 1)[1], "\na module and a reset, no server\n")

    def test_a_change_no_ruling_names_is_refused(self):
        a = self.amended(data_flow="the fixture calls a server")
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)
        self.assertIn("amendment-outside-rulings", [r["rule"] for r in doc["refusals"]])

    def test_a_change_a_ruling_names_is_accepted(self):
        a = self.amended(data_flow="the fixture calls turnstile.py; reset() zeroes it on demand")
        a["rulings"][0]["changes"] = ["data_flow"]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 0, out + err)



class AnUnreadableRequestsFolder(_Rulings):
    """Slice 3b round 3 R2 (CA3B2-1): `record-answer` (the amendment, through its context) and `save-take` read
    `<run>/requests` before their first write; a folder the process cannot list, or a folder named like a request
    inside it, is exit 1 naming the folder and the command, stdout empty, no traceback, every listing unchanged."""

    def unreadable(self, call, command, folder):
        roots = [self.run.run_dir, self.ws]
        before = [archlib.listing(r) for r in roots]
        phase = testlib.load_json(os.path.join(self.run.run_dir, "checkpoint.json"))["phase"]
        code, doc, out, err = call()
        self.assertEqual(code, 1, out + err)
        self.assertEqual(out, "")
        self.assertNotIn("Traceback", err)
        self.assertIn("unreadable run directory: %s cannot be read (" % folder, err)
        self.assertIn("nothing was written and the run stays where it was: fix %s by hand, then run `%s` again"
                      % (folder, command), err)
        self.assertEqual([archlib.listing(r) for r in roots], before)
        self.assertEqual(testlib.load_json(os.path.join(self.run.run_dir, "checkpoint.json"))["phase"], phase)

    def take(self):
        path = os.path.join(self.tmp, "take-2.md")
        testlib.write_text(path, "a second take\n")
        return path

    def locked(self):
        folder = os.path.join(self.run.run_dir, "requests")
        os.chmod(folder, 0)
        self.addCleanup(os.chmod, folder, 0o755)
        return folder, lambda: os.chmod(folder, 0o755)

    def planted(self):
        folder = os.path.join(self.run.run_dir, "requests")
        node = os.path.join(folder, "x.json")
        os.makedirs(node)
        return folder, lambda: os.rmdir(node)

    def at_the_amendment(self, plant):
        folder, undo = plant()
        self.unreadable(lambda: self.run.record(self.amended()), "record-answer", folder)
        undo()
        code, doc, out, err = self.run.record(self.amended())
        self.assertEqual(code, 0, out + err)

    def at_save_take(self, plant):
        folder, undo = plant()
        self.unreadable(lambda: self.run.save_take("gpt-astra", self.take()), "save-take", folder)
        undo()
        code, doc, out, err = self.run.save_take("gpt-astra", self.take())
        self.assertEqual(code, 0, out + err)
        self.assertTrue(doc["path"].endswith("-gpt-2.md"), doc["path"])

    @unittest.skipIf(os.geteuid() == 0, "root lists any folder")
    def test_a_requests_folder_it_cannot_list_at_the_amendment(self):
        self.at_the_amendment(self.locked)

    @unittest.skipIf(os.geteuid() == 0, "root lists any folder")
    def test_a_requests_folder_it_cannot_list_at_save_take(self):
        self.at_save_take(self.locked)

    def test_a_folder_named_like_a_request_at_the_amendment(self):
        self.at_the_amendment(self.planted)

    def test_a_folder_named_like_a_request_at_save_take(self):
        self.at_save_take(self.planted)

class OneAmendment(_Rulings):
    """R1 (CA1-1, CA1-2): one recorded answer and ONE amendment per run. A second `record-answer`
    before the next `write` is held to the first answer exactly as the amendment is; a second
    amendment after the rewrite is usage, never a quiet replacement of the owner's rulings."""

    def smuggling(self):
        a = self.amended()
        a["candidates"].append({"name": "cli", "categories": ["platform:command line"], "assumes": "a shell",
                                "later_cost": "argument parsing"})
        a["rejected"].append({"name": "cli", "why": "the bench imports"})
        a["components"].append({"name": "logger", "serves": "count turns"})
        a["poured_concrete"].append({"text": "platform %s macOS %s bench" % (archlib.D, archlib.D), "tag": "decided",
                                     "trace": {"kind": "question", "ref": "Q5"}})
        return a

    def test_a_re_record_before_write_is_held_to_the_first_answer(self):
        code, doc, out, err = self.run.record(self.amended())
        self.assertEqual(code, 0, out + err)
        first = archlib.sha(os.path.join(self.run.run_dir, "answer-round-1.json"))
        before_run = archlib.listing(self.run.run_dir)
        before_ws = archlib.listing(self.ws)
        code, doc, out, err = self.run.record(self.smuggling())
        self.assertEqual(code, 5, out + err)
        self.assertIn("amendment-outside-rulings", [r["rule"] for r in doc["refusals"]])
        self.assertEqual(archlib.listing(self.run.run_dir), before_run)
        self.assertEqual(archlib.listing(self.ws), before_ws)
        self.assertEqual(archlib.sha(os.path.join(self.run.run_dir, "answer-round-1.json")), first)

    def test_a_corrected_amendment_before_write_replaces_the_amendment_only(self):
        self.assertEqual(self.run.record(self.amended())[0], 0)
        first = testlib.load_json(os.path.join(self.run.run_dir, "answer-round-1.json"))
        corrected = self.amended()
        corrected["rulings"][0]["ruling"] = "reset() stays, documented"
        code, doc, out, err = self.run.record(corrected)
        self.assertEqual(code, 0, out + err)
        self.assertEqual((doc["round"], doc["amendment"]), (2, True))
        self.assertEqual(testlib.load_json(os.path.join(self.run.run_dir, "answer-round-1.json")), first)
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer-round-2.json")))

    def test_a_second_amendment_is_usage(self):
        self.assertEqual(self.run.record(self.amended())[0], 0)
        self.assertEqual(self.run.write()[0], 0)
        self.assertEqual(self.run.render()[0], 0)
        self.assertEqual(self.run.publish("https://example.invalid/artifact/turnstile")[0], 0)
        before_run = archlib.listing(self.run.run_dir)
        again = self.amended()
        again["rulings"] = [{"disagreement": "the take keeps a server", "ruling": "no server", "reviewers": ["gpt"],
                             "changes": [], "trace": {"kind": "question", "ref": "Q5"}}]
        code, doc, out, err = self.run.record(again)
        self.assertEqual(code, 2, out + err)
        self.assertIn("one amended answer per run; start a new run for more", err)
        self.assertEqual(archlib.listing(self.run.run_dir), before_run)


D = archlib.D
STORAGE = "storage %s none in v0 %s nothing is remembered" % (D, D)
LANGUAGE = "language %s Python 3.9 %s every bench script imports it" % (D, D)
JSON_FILE = "storage %s a JSON file %s the count survives a restart" % (D, D)


def ruled(answer, *changes):
    answer["rulings"][0]["changes"] = list(changes)
    return answer


class TheFirstWriteIsTheBaseline(_Rulings):
    """Round 7 R1 (A1): after the first write, the written doc is kept as an immutable snapshot in
    the run directory, and the amendment is held to it, on a first run as on a re-run: a ruling
    authorizes a changed decision, never the deletion of the line it changes, which stays verbatim
    or struck; a missing line is `no-loss` before `answer.json` or the doc is written."""

    def doc_path(self):
        return os.path.join(self.ws, "docs", "architecture", "%s-turnstile.md" % archlib.TODAY)

    def snapshot(self):
        return os.path.join(self.run.run_dir, "written-doc.md")

    def test_the_first_write_is_kept_once(self):
        self.assertTrue(os.path.isfile(self.snapshot()))
        first = testlib.read_text(self.snapshot())
        self.assertIn("- %s\n" % STORAGE, first)
        self.assertIn("### Run 1 %s" % D, first)
        a = self.amended()
        self.assertEqual(self.run.record(a)[0], 0)
        self.assertEqual(self.run.write()[0], 0)
        self.assertEqual(testlib.read_text(self.snapshot()), first, "the snapshot is never rewritten")

    def test_a_ruling_never_deletes_a_first_written_line(self):
        a = ruled(self.amended(), "poured_concrete")
        a["poured_concrete"] = a["poured_concrete"][:1]
        a["changed"] = "remove storage decision"
        before_run = archlib.listing(self.run.run_dir)
        before_ws = archlib.listing(self.ws)
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)
        rules = [r["rule"] for r in doc["refusals"]]
        self.assertIn("no-loss", rules, doc["refusals"])
        self.assertTrue(any(STORAGE in r["message"] for r in doc["refusals"] if r["rule"] == "no-loss"))
        self.assertEqual(archlib.listing(self.run.run_dir), before_run, "answer.json and the rest unchanged")
        self.assertEqual(archlib.listing(self.ws), before_ws, "the doc unchanged")

    def test_a_ruled_strike_keeps_the_line_struck(self):
        a = ruled(self.amended(), "poured_concrete")
        a["poured_concrete"] = [{"carried": LANGUAGE},
                                {"strike": STORAGE, "trace": {"kind": "question", "ref": "Q5"}},
                                {"text": JSON_FILE, "tag": "decided", "trace": {"kind": "question", "ref": "Q5"}}]
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        text = testlib.read_text(self.doc_path())
        self.assertIn("- %s\n- ~~%s~~\n- %s\n" % (LANGUAGE, STORAGE, JSON_FILE), text)
        from station_core import templates
        self.assertEqual(templates.check("architecture-doc", text), [])

    def test_a_ruled_drawing_change_strikes_the_first_written_line(self):
        old = "Data flow: the fixture calls turnstile.py; reset() zeroes the count"
        a = ruled(self.amended(data_flow="the fixture calls turnstile.py; reset() zeroes it on demand"), "data_flow")
        self.assertEqual(self.run.record(a)[0], 0)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        text = testlib.read_text(self.doc_path())
        self.assertIn("~~%s~~\nData flow: the fixture calls turnstile.py; reset() zeroes it on demand\n" % old, text)

    def test_the_run_block_is_regenerated_with_its_rulings(self):
        self.assertEqual(self.run.record(self.amended())[0], 0)
        self.assertEqual(self.run.write()[0], 0)
        text = testlib.read_text(self.doc_path())
        from station_core import runlog
        self.assertEqual([n for n, _ in runlog.runs(text)], [1])
        self.assertIn("Rulings: blind review: agreed on a module, no server; 1 disagreement", text)
        self.assertNotIn("Rulings: none yet", text)

    def test_a_changed_snapshot_is_a_defect(self):
        with open(self.snapshot(), "a", encoding="utf-8") as fh:
            fh.write("- a line typed into the snapshot\n")
        before_ws = archlib.listing(self.ws)
        code, doc, out, err = self.run.record(self.amended())
        self.assertEqual(code, 1, out + err)
        self.assertIn("written-doc.md", err)
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer-round-1.json")))
        self.assertEqual(archlib.listing(self.ws), before_ws)

    def defect(self, step):
        """`step()` exits 1 naming the snapshot's path, stdout empty, nothing written in the run or the workspace."""
        before_run = archlib.listing(self.run.run_dir)
        before_ws = archlib.listing(self.ws)
        code, doc, out, err = step()
        self.assertEqual(code, 1, out + err)
        self.assertEqual(out, "")
        self.assertNotIn("Traceback", err)
        self.assertIn(self.snapshot(), err)
        self.assertIn("missing or not a file", err)
        self.assertIn("nothing was written", err)
        self.assertEqual(archlib.listing(self.run.run_dir), before_run)
        self.assertEqual(archlib.listing(self.ws), before_ws)
        return err

    def deleting(self):
        a = ruled(self.amended(), "poured_concrete")
        a["poured_concrete"] = a["poured_concrete"][:1]
        a["changed"] = "remove storage decision"
        return a

    def test_a_removed_snapshot_is_a_defect(self):
        """Slice 3b R3 (CA7-1): the receipt records the snapshot, so its absence never returns the amendment to
        the harvested baseline (her A1 deletion): exit 1, nothing written."""
        os.remove(self.snapshot())
        self.defect(lambda: self.run.record(self.deleting()))
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "answer-round-1.json")))
        self.assertIn("- %s\n" % STORAGE, testlib.read_text(self.doc_path()))

    def test_a_snapshot_replaced_by_a_folder_is_a_defect(self):
        os.remove(self.snapshot())
        os.makedirs(self.snapshot())
        self.defect(lambda: self.run.record(self.deleting()))
        self.assertTrue(os.path.isdir(self.snapshot()))

    def test_a_snapshot_removed_after_the_amendment_is_recorded_stops_the_write(self):
        self.assertEqual(self.run.record(self.amended())[0], 0)
        os.remove(self.snapshot())
        self.defect(self.run.write)


class TheFirstWriteIsTheBaselineOnARerun(unittest.TestCase):
    """R1 on a re-run: the lines the first write introduced are held as the harvested ones are, a
    strike the first answer recorded may be repeated (idempotent), a line the first write
    introduced may be struck, and every earlier run block stays byte for byte."""

    def setUp(self):
        from test_arch_record import LIVING, LIVING_REL, rerun_answer
        self.tmp = testlib.make_scratch("arch-rulings-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp, files={LIVING_REL: LIVING})
        self.living = LIVING
        self.doc = os.path.join(self.ws, LIVING_REL)
        self.run = archlib.ArchRun(self.tmp, self.ws)
        self.assertEqual(self.run.to_harvest()[0], 0)
        self.first = rerun_answer()
        for step in (lambda: self.run.record(self.first), self.run.write, self.run.render,
                     lambda: self.run.publish("https://example.invalid/artifact/turnstile"),
                     lambda: self.run.request("gpt-astra")):
            code, doc, out, err = step()
            self.assertEqual(code, 0, out + err)
        take = os.path.join(self.tmp, "take.md")
        testlib.write_text(take, "a module and a file, no server\n")
        self.assertEqual(self.run.save_take("gpt-astra", take, model="gpt-model-x")[0], 0)

    def amended(self, *changes):
        from test_arch_record import rerun_answer
        a = rerun_answer(review={"outcome": "done", "spine": "a module and a file"},
                         rulings=[{"disagreement": "the take keeps the file", "ruling": "the file stays",
                                   "reviewers": ["gpt"], "changes": list(changes),
                                   "trace": {"kind": "question", "ref": "Q6"}}])
        a["questions"].append({"id": "Q6", "text": "Keep the JSON file?", "touches": [], "answer": "not yet"})
        return a

    def test_dropping_a_line_the_first_write_introduced_is_no_loss(self):
        a = self.amended("poured_concrete")
        a["poured_concrete"] = a["poured_concrete"][:2]
        before_run = archlib.listing(self.run.run_dir)
        before_ws = archlib.listing(self.ws)
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 5, out + err)
        self.assertTrue(any(r["rule"] == "no-loss" and JSON_FILE in r["message"] for r in doc["refusals"]),
                        doc["refusals"])
        self.assertEqual(archlib.listing(self.run.run_dir), before_run)
        self.assertEqual(archlib.listing(self.ws), before_ws)

    def test_a_repeated_strike_and_a_strike_of_a_first_written_line(self):
        a = self.amended("poured_concrete")
        a["poured_concrete"][2] = {"strike": JSON_FILE, "trace": {"kind": "question", "ref": "Q6"}}
        code, doc, out, err = self.run.record(a)
        self.assertEqual(code, 0, out + err)
        code, doc, out, err = self.run.write()
        self.assertEqual(code, 0, out + err)
        text = testlib.read_text(self.doc)
        self.assertIn("- %s\n- ~~%s~~\n- ~~%s~~\n" % (LANGUAGE, STORAGE, JSON_FILE), text)
        self.assertEqual(text.count(STORAGE), 1)
        from station_core import runlog, templates
        self.assertEqual([n for n, _ in runlog.runs(text)], [1, 2])
        self.assertEqual(runlog._blocks(text)[1], runlog._blocks(self.living)[1], "Run 1 byte for byte")
        self.assertIn("Rulings: blind review: agreed on a module and a file; 1 disagreement", runlog._blocks(text)[2])
        self.assertEqual(templates.check("architecture-doc", text), [])

    def test_the_unchanged_amendment_keeps_every_line(self):
        code, doc, out, err = self.run.record(self.amended())
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.run.write()[0], 0)
        text = testlib.read_text(self.doc)
        self.assertIn("- ~~%s~~\n- %s\n" % (STORAGE, JSON_FILE), text)


class TakesAnswerRequests(unittest.TestCase):
    """CA1-13: `request` sends the scope doc harvest read, never another file under its name, and
    `save-take` saves a take only for a row this run requested."""

    def setUp(self):
        self.tmp = testlib.make_scratch("arch-requests-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.ws = archlib.repo_workspace(self.tmp)
        self.run = archlib.ArchRun(self.tmp, self.ws)
        self.run.to_harvest()
        self.run.record(archlib.clean_answer())
        self.assertEqual(self.run.write()[0], 0)
        self.take = os.path.join(self.tmp, "take.md")
        testlib.write_text(self.take, "a take\n")

    def test_a_row_never_requested_is_usage(self):
        self.assertEqual(self.run.request("gpt-astra")[0], 0)
        before = archlib.listing(self.ws)
        code, doc, out, err = self.run.save_take("gemini", self.take)
        self.assertEqual(code, 2, out + err)
        self.assertIn("gemini", err)
        self.assertEqual(archlib.listing(self.ws), before)
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "takes")))

    def test_a_scope_doc_changed_since_harvest_is_usage(self):
        path = os.path.join(self.ws, archlib.SCOPE_REL)
        testlib.write_text(path, archlib.SCOPE + "- a line added after the harvest\n")
        code, doc, out, err = self.run.request("gpt-astra")
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "requests")))

    def test_a_harvest_record_naming_another_file_is_usage(self):
        record_path = os.path.join(self.run.run_dir, "harvest.json")
        record = testlib.load_json(record_path)
        record["scope_doc"]["path"] = os.path.join(self.ws, "docs", "architecture",
                                                   "%s-turnstile.md" % archlib.TODAY)
        testlib.write_json(record_path, record)
        code, doc, out, err = self.run.request("gpt-astra")
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.run.run_dir, "requests")))


class ASymlinkedRequestsFolder(unittest.TestCase):
    """Round 6 R2 (the outside reviewer's A4): `request` writes through the same containment check the
    document and take writers use. A `<run>/requests` that resolves outside the run directory (here a
    symlink into the workspace) is refused, exit 5, with nothing written, in report-only and
    otherwise; a plain run still writes its requests."""

    def run_to_write(self, **extra):
        tmp = testlib.make_scratch("arch-request-link-")
        self.addCleanup(testlib.rmtree, tmp)
        ws = archlib.repo_workspace(tmp)
        run = archlib.ArchRun(tmp, ws, **extra)
        code, doc, out, err = run.to_harvest()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(run.record(archlib.clean_answer())[0], 0)
        self.assertEqual(run.write()[0], 0)
        return tmp, ws, run

    def linked(self, **extra):
        tmp, ws, run = self.run_to_write(**extra)
        leak = os.path.join(ws, "requests-leak")
        os.symlink(leak, os.path.join(run.run_dir, "requests"))
        before_ws = archlib.listing(ws)
        before_run = archlib.listing(run.run_dir)
        code, doc, out, err = run.request("gpt-astra")
        self.assertEqual(code, 5, out + err)
        self.assertNotIn("Traceback", err)
        self.assertFalse(doc["accepted"])
        self.assertEqual([r["rule"] for r in doc["refusals"]], ["request-outside-run"], doc["refusals"])
        self.assertFalse(os.path.lexists(leak), "nothing created where the link leads")
        self.assertEqual(archlib.listing(ws), before_ws)
        self.assertEqual(archlib.listing(run.run_dir), before_run)
        return run

    def test_refused_under_report_only(self):
        self.linked(report_only=True)

    def test_refused_otherwise(self):
        self.linked()

    def test_a_link_to_an_existing_folder_is_refused_too(self):
        tmp, ws, run = self.run_to_write(report_only=True)
        leak = os.path.join(ws, "requests-leak")
        os.makedirs(leak)
        os.symlink(leak, os.path.join(run.run_dir, "requests"))
        code, doc, out, err = run.request("gpt-astra")
        self.assertEqual(code, 5, out + err)
        self.assertEqual(os.listdir(leak), [])

    def test_a_plain_run_writes_its_requests(self):
        for extra in ({}, {"report_only": True}):
            tmp, ws, run = self.run_to_write(**extra)
            code, doc, out, err = run.request("gpt-astra", "gemini")
            self.assertEqual(code, 0, out + err)
            self.assertEqual(len(doc["requests"]), 2)
            for entry in doc["requests"]:
                self.assertTrue(os.path.isfile(entry["path"]))
                self.assertEqual(os.path.dirname(entry["path"]), os.path.join(run.run_dir, "requests"))


class ASymlinkedReviewHome(unittest.TestCase):
    """CA1-3: `docs/reviews` a symlink to a folder outside the workspace: `save-take` is usage,
    never a crash, and nothing lands outside."""

    def test_usage_and_nothing_outside(self):
        tmp = testlib.make_scratch("arch-take-link-")
        self.addCleanup(testlib.rmtree, tmp)
        ws = archlib.repo_workspace(tmp)
        outside = os.path.join(tmp, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(ws, "docs", "reviews"))
        run = archlib.ArchRun(tmp, ws)
        run.to_harvest()
        run.record(archlib.clean_answer())
        self.assertEqual(run.write()[0], 0)
        self.assertEqual(run.request("gpt-astra")[0], 0)
        take = os.path.join(tmp, "take.md")
        testlib.write_text(take, "a take\n")
        code, doc, out, err = run.save_take("gpt-astra", take)
        self.assertEqual(code, 2, out + err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(os.listdir(outside), [])

    def test_a_link_into_the_run_directory_is_usage(self):
        """CA2-3: `docs/reviews` linked to a folder inside the run directory."""
        tmp = testlib.make_scratch("arch-take-link-")
        self.addCleanup(testlib.rmtree, tmp)
        ws = archlib.repo_workspace(tmp)
        run = archlib.ArchRun(tmp, ws)
        run.to_harvest()
        inner = os.path.join(run.run_dir, "inner")
        os.makedirs(inner)
        os.symlink(inner, os.path.join(ws, "docs", "reviews"))
        run.record(archlib.clean_answer())
        self.assertEqual(run.write()[0], 0)
        self.assertEqual(run.request("gpt-astra")[0], 0)
        take = os.path.join(tmp, "take.md")
        testlib.write_text(take, "a take\n")
        code, doc, out, err = run.save_take("gpt-astra", take)
        self.assertEqual(code, 2, out + err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(os.listdir(inner), [])


if __name__ == "__main__":
    unittest.main()
