"""The ONE fix round after the reviewer's verification of the sealed bench (SB-12).

Six items, her labels: N1 (judgment extraction), N2 (the launcher alias and the wall's broad
deny), N3 (typed read outcomes and one refusal per label), N4 (the applied seatbelt as the
Codex witness), N5 (stop recovery, retained-pair aliases, producer selection), N6 (journal
membership, PermissionError is ALIVE, the campaign-wide liveness scan).

Standard library only, Python 3.9, runs from any working directory. No test opens
`evals/answer-key/`, the held-out set or any routing request, and nothing here launches a live
model: every model-facing route is driven with canned records.
"""
import copy
import json
import os
import shutil
import unittest
from unittest.mock import patch

from testlib import RunnerCase, runner


ITEM = {"file": "src/demo.py", "line": 7}
LOCATION = "src/demo.py:7"
EXPECTED_ITEMS = [{"location": dict(ITEM), "disposition": "not_fixed",
                   "reason": "reproduces"}]
GOOD = ("MAJOR · src/demo.py:7 · (counter remains wrong) · not fixed "
        "(reproduces) · executed counter")
WRONG = ("MAJOR · src/demo.py:7 · (counter remains wrong) · fixed · "
         "checked counter")


class JudgmentExtraction(RunnerCase):
    """N1: every candidate call is collected; a conflict is `unextracted`, never first-wins.

    Her probe inputs, whole: `two-lines`, `reverse-lines`, `two-dispositions`, `plain-prose`.
    """

    def record_with(self, name, reply, chat=None):
        record = os.path.join(self.scratch, "judgment", name)
        runner.ensure_dir(record)
        runner.write_text(os.path.join(record, "reply.md"), reply)
        if chat is not None:
            runner.write_text(os.path.join(record, "chat.md"), chat)
        return record

    def judge(self, name, reply, expected=None, result=None, chat=None, entry=None):
        record = self.record_with(name, reply, chat=chat)
        return runner._judgment(record, result,
                                {"items": expected if expected is not None
                                 else copy.deepcopy(EXPECTED_ITEMS)},
                                entry or {})

    # ---- the conflict --------------------------------------------------------------------

    def test_two_lines_with_two_dispositions_are_unextracted_not_first_wins(self):
        judgment = self.judge("two-lines", GOOD + "\n" + WRONG + "\n")
        row = judgment["items"][0]
        self.assertEqual(row["source"], runner.UNEXTRACTED)
        self.assertFalse(judgment["ok"])
        self.assertEqual(judgment["unextracted"], 1)
        self.assertIn("not_fixed", row["why"])
        self.assertIn("fixed", row["why"])
        self.assertIn("conflict", row["why"])

    def test_the_reverse_order_gives_the_same_block(self):
        forward = self.judge("conflict-forward", GOOD + "\n" + WRONG + "\n")
        reverse = self.judge("conflict-reverse", WRONG + "\n" + GOOD + "\n")
        self.assertEqual(forward["checks"], reverse["checks"])
        self.assertEqual(forward["sources"], reverse["sources"])
        self.assertEqual(forward["items"][0]["source"], runner.UNEXTRACTED)
        self.assertEqual(reverse["items"][0]["source"], runner.UNEXTRACTED)
        self.assertFalse(forward["ok"])
        self.assertFalse(reverse["ok"])

    def test_two_dispositions_on_one_line_are_a_conflict_too(self):
        judgment = self.judge("one-line", GOOD + " · fixed\n")
        self.assertEqual(judgment["items"][0]["source"], runner.UNEXTRACTED)
        self.assertFalse(judgment["ok"])

    def test_two_reasons_for_one_item_are_a_conflict(self):
        other = GOOD.replace("(reproduces)", "(missed_case)")
        judgment = self.judge("two-reasons", GOOD + "\n" + other + "\n")
        self.assertEqual(judgment["items"][0]["source"], runner.UNEXTRACTED)
        self.assertIn("reproduces", judgment["items"][0]["why"])
        self.assertIn("missed_case", judgment["items"][0]["why"])

    def test_the_same_call_twice_is_not_a_conflict(self):
        judgment = self.judge("repeat", GOOD + "\n" + GOOD + "\n")
        row = judgment["items"][0]
        self.assertEqual(row["source"], "reply.md")
        self.assertEqual(row["disposition"], "not_fixed")
        self.assertEqual(row["reason"], "reproduces")
        self.assertTrue(judgment["ok"], judgment["because"])

    def test_a_line_that_states_no_reason_does_not_conflict_with_one_that_does(self):
        bare = "MAJOR · src/demo.py:7 · (counter remains wrong) · not fixed"
        judgment = self.judge("reason-absent", bare + "\n" + GOOD + "\n")
        self.assertEqual(judgment["items"][0]["source"], "reply.md")
        self.assertEqual(judgment["items"][0]["reason"], "reproduces")

    # ---- ordinary prose ------------------------------------------------------------------

    def test_an_ordinary_prose_call_is_extracted_without_the_middle_dot_block(self):
        judgment = self.judge("prose",
                              "src/demo.py:7 is not fixed (reproduces).\n")
        row = judgment["items"][0]
        self.assertEqual(row["source"], "reply.md")
        self.assertEqual(row["disposition"], "not_fixed")
        self.assertEqual(row["reason"], "reproduces")
        self.assertEqual(judgment["unextracted"], 0)
        self.assertTrue(judgment["ok"], judgment["because"])

    def test_prose_still_not_fixed_is_the_same_call(self):
        judgment = self.judge("prose-still",
                              "I checked src/demo.py:7 and it is still not fixed "
                              "(reproduces).\n")
        self.assertEqual(judgment["items"][0]["disposition"], "not_fixed")
        self.assertTrue(judgment["ok"], judgment["because"])

    def test_prose_is_fixed_is_read_as_fixed_and_fails_the_key(self):
        judgment = self.judge("prose-fixed",
                              "src/demo.py:7 is fixed; the counter now reads eight.\n")
        self.assertEqual(judgment["items"][0]["disposition"], "fixed")
        self.assertFalse(judgment["ok"])
        self.assertFalse(judgment["checks"]["no_false_fixed"])

    def test_prose_never_reads_not_fixed_as_fixed(self):
        self.assertEqual(runner._prose_calls("src/demo.py:7 is not fixed."),
                         ["not_fixed"])
        self.assertEqual(runner._prose_calls("it is still not fixed"), ["not_fixed"])
        self.assertEqual(runner._prose_calls("this one is fixed"), ["fixed"])

    def test_a_prose_conflict_is_unextracted(self):
        judgment = self.judge(
            "prose-conflict",
            "src/demo.py:7 is not fixed (reproduces).\nsrc/demo.py:7 is fixed.\n")
        self.assertEqual(judgment["items"][0]["source"], runner.UNEXTRACTED)
        self.assertFalse(judgment["ok"])

    def test_a_prose_call_named_by_its_claim_text_is_extracted(self):
        expected = [{"location": dict(ITEM), "claim": "the counter remains wrong",
                     "disposition": "not_fixed", "reason": "reproduces"}]
        judgment = self.judge(
            "prose-claim",
            "The counter remains wrong: not fixed (reproduces).\n",
            expected=expected)
        row = judgment["items"][0]
        self.assertEqual(row["source"], "reply.md")
        self.assertEqual(row["location"], LOCATION)
        self.assertEqual(row["disposition"], "not_fixed")

    def test_prose_naming_two_items_on_one_line_is_never_guessed(self):
        expected = [{"location": dict(ITEM), "disposition": "not_fixed",
                     "reason": "reproduces"},
                    {"location": {"file": "src/other.py", "line": 2},
                     "disposition": "not_fixed", "reason": "reproduces"}]
        judgment = self.judge("prose-two",
                              "src/demo.py:7 and src/other.py:2 are not fixed.\n",
                              expected=expected)
        self.assertEqual(sorted(r["source"] for r in judgment["items"]),
                         [runner.UNEXTRACTED, runner.UNEXTRACTED])

    # ---- what must NOT change ------------------------------------------------------------

    def test_the_four_unchanged_probe_readings_still_read_the_same(self):
        correct = self.judge("keep-correct", GOOD + "\n")
        self.assertTrue(correct["ok"], correct["because"])
        self.assertEqual(correct["sources"], {"reply.md": 1})
        wrong = self.judge("keep-wrong", WRONG + "\n")
        self.assertFalse(wrong["ok"])
        self.assertFalse(wrong["checks"]["dispositions_all_matched"])
        empty = self.judge("keep-empty", "")
        self.assertEqual(empty["sources"], {runner.UNEXTRACTED: 1})
        self.assertEqual(empty["unextracted"], 1)
        chat = self.judge("keep-chat", "", chat=GOOD + "\n")
        self.assertEqual(chat["sources"], {"chat.md": 1})
        self.assertTrue(chat["ok"], chat["because"])

    def test_source_priority_keeps_the_record_first(self):
        result = {"items": [{"location": dict(ITEM), "disposition": "not_fixed",
                             "reason": "reproduces",
                             "verification": {"evidence": [
                                 {"kind": "command", "detail": "ran it"}]}}]}
        judgment = self.judge("priority", GOOD + "\n" + WRONG + "\n", result=result)
        self.assertEqual(judgment["sources"], {"result.json": 1})
        self.assertEqual(judgment["items"][0]["source"], "result.json")

    def test_not_measurable_is_unchanged_for_a_reply_sourced_call(self):
        judgment = self.judge("structural", GOOD + "\n")
        rows = {r["check"]: r for r in judgment["not_measurable"]}
        self.assertEqual(rows["evidence_sufficient"]["why"],
                         "the extraction's source cannot carry evidence entries")
        self.assertTrue(rows["evidence_sufficient"]["structural"])

    def test_the_extraction_does_not_branch_on_condition(self):
        """Identical inputs in both conditions give identical blocks."""
        blocks = []
        for condition in ("available", "absent"):
            judgment = self.judge("condition-%s" % condition, GOOD + "\n",
                                  entry={"condition": condition, "setup": "claude-code"})
            blocks.append({k: v for k, v in judgment.items() if k != "items"})
        self.assertEqual(blocks[0], blocks[1])

    def test_a_still_open_line_is_still_not_an_item_line(self):
        rows = runner._reply_item_lines(
            "Still open: BLOCKER · a.py:1 · the title is not quoted · fix it\n")
        self.assertEqual(rows, [])


if __name__ == "__main__":                                      # pragma: no cover
    unittest.main()


class LauncherAliasAndTheWall(RunnerCase):
    """N2: a different PATHNAME is not proof of a fake launcher.

    Her probe took a symlink to the setup's own `launch.sh` under `sealed: true`: the runner
    called it fake, dropped the wall and returned an argv with no `sandbox-exec` in it. A
    launcher that IS the staged launcher, however it is spelled, gets the wall; a launcher
    that is not it is REFUSED on a sealed real campaign; only the campaign the test harness
    marks synthetic through `--fake-launcher` runs a stand-in.
    """

    setups = ("claude-code", "codex")

    def staged_launcher(self, campaign=None, harness="codex"):
        """The setup's own staged `launch.sh`, where that campaign's stage actually holds it."""
        campaign = campaign or runner.Campaign(self.campaign)
        directory = os.path.join(campaign.stage, "plugins", "recheck-v2", "setups", harness)
        runner.ensure_dir(directory)
        path = os.path.join(directory, "launch.sh")
        runner.write_text(path, "#!/bin/sh\nexit 0\n")
        os.chmod(path, 0o755)
        return path

    def alias_of(self, target, name="real-launcher-alias.sh"):
        alias = os.path.join(self.scratch, name)
        if not os.path.lexists(alias):
            os.symlink(target, alias)
        return alias

    def setup(self, campaign=None, name="codex", plan=None):
        campaign = campaign or runner.Campaign(self.campaign)
        return runner.setup_for(campaign, plan or self.plan_document, name)

    def seal(self, synthetic=False, name=None):
        """A campaign whose plan says `sealed: true`, real unless a test asks otherwise."""
        campaign = runner.Campaign(os.path.join(self.scratch,
                                                name or "sealed-%s" % synthetic))
        campaign.ensure()
        document = dict(self.plan_document)
        document["sealed"] = True
        document["synthetic"] = bool(synthetic)
        runner.write_json(campaign.campaign_json, document)
        runner.write_json(campaign.stage_json, {"campaign": campaign.root,
                                                "stage": campaign.stage})
        if synthetic:
            campaign.mark_synthetic("a test marked this campaign synthetic")
        return campaign

    # ---- the classifier ------------------------------------------------------------------

    def test_an_alias_of_the_real_launcher_is_never_classified_fake(self):
        sealed = self.seal(name="alias-real")
        own = self.staged_launcher(sealed)
        alias = self.alias_of(own)
        setup = self.setup(sealed)
        self.assertEqual(os.path.realpath(alias), os.path.realpath(own))
        self.assertFalse(runner.launch_is_fake(setup, alias))
        self.assertFalse(runner.launch_is_fake(setup, alias, sealed))

    def test_a_copy_path_spelling_of_the_real_launcher_is_never_fake(self):
        sealed = self.seal(name="alias-spelling")
        own = self.staged_launcher(sealed)
        setup = self.setup(sealed)
        spelled = os.path.join(os.path.dirname(own), ".", "launch.sh")
        self.assertFalse(runner.launch_is_fake(setup, spelled))

    def test_a_different_launcher_is_fake_only_when_the_campaign_is_synthetic(self):
        real, synthetic = self.seal(name="real-1"), self.seal(synthetic=True, name="synth-1")
        self.staged_launcher(real)
        self.staged_launcher(synthetic)
        stand_in = os.path.join(self.scratch, "stand-in.sh")
        runner.write_text(stand_in, "#!/bin/sh\nexit 0\n")
        self.assertTrue(runner.launch_is_fake(self.setup(synthetic), stand_in, synthetic))
        self.assertFalse(runner.launch_is_fake(self.setup(real), stand_in, real))

    # ---- the sealed gate -----------------------------------------------------------------

    def test_a_sealed_real_campaign_refuses_a_launcher_that_is_not_its_own(self):
        sealed = self.seal(name="refuses")
        self.staged_launcher(sealed)
        setup = self.setup(sealed)
        stand_in = os.path.join(self.scratch, "stand-in-2.sh")
        runner.write_text(stand_in, "#!/bin/sh\nexit 0\n")
        with self.assertRaises(runner.Usage) as caught:
            runner.require_wall(sealed, setup, stand_in, "the probe")
        message = str(caught.exception)
        self.assertIn("launch.sh", message)
        self.assertIn(stand_in, message)

    def test_a_sealed_synthetic_campaigns_stand_in_is_exempt_not_refused(self):
        """The one exemption the brief names: the explicit fake-session mechanism.

        A4's own test (`test_a_fake_launcher_is_exempt_from_the_sealed_gate`) keeps this
        route open; N2 only narrows WHAT counts as a fake. A REAL launch on a sealed
        synthetic campaign still raises, which `test_a_sealed_and_synthetic_campaign_
        refuses_a_real_launch` in the wall suite asserts.
        """
        sealed = self.seal(synthetic=True, name="synth-2")
        self.staged_launcher(sealed)
        setup = self.setup(sealed)
        gate = runner.require_wall(sealed, setup,
                                   os.path.join(self.scratch, "stand-in-3.sh"), "the probe")
        self.assertFalse(gate["required"])
        self.assertIn("synthetic", gate["why"])

    def test_an_unsealed_campaign_needs_no_wall_and_raises_nothing(self):
        self.staged_launcher()
        setup = self.setup()
        gate = runner.require_wall(runner.Campaign(self.campaign), setup,
                                   os.path.join(self.scratch, "anything.sh"), "the probe")
        self.assertFalse(gate["required"])

    # ---- the argv the alias actually gets ------------------------------------------------

    def test_an_alias_launch_is_walled_and_its_argv_carries_sandbox_exec(self):
        campaign = self.seal(name="argv")
        own = self.staged_launcher(campaign)
        alias = self.alias_of(own, "walled-alias.sh")
        setup = self.setup(campaign)
        out_dir = os.path.join(self.scratch, "alias-capture")
        with runner.walled(campaign, setup, "available", out_dir, launcher=alias) as wall:
            argv = wall.prefix([alias])
            self.assertTrue(wall.record["sealed"], wall.record)
            self.assertEqual(argv[0], runner.SANDBOX_EXEC)
            self.assertIn(alias, argv)

    def test_a_synthetic_campaigns_fake_launcher_still_bypasses_the_wall(self):
        """The fake end-to-end tests rest on this: no harness, nothing to confine."""
        self.staged_launcher()
        campaign = runner.Campaign(self.campaign)          # every test campaign is synthetic
        setup = self.setup()
        fake = self.fake_launcher("codex")
        with runner.walled(campaign, setup, "available",
                           os.path.join(self.scratch, "fake-capture"),
                           launcher=fake) as wall:
            self.assertFalse(wall.record["sealed"])
            self.assertEqual(wall.prefix(["x"]), ["x"])


class BroadDenyOfTheUserCaches(unittest.TestCase):
    """N2, second half: the readable user caches the profile left open.

    Her probe evaluated `/private/var/folders/zz/some-cache/key.json` as ALLOWED for reading,
    and `/System/Volumes/Data/Users/...` with it. Both are spellings of the user area the
    wall exists to close. The profile is NOT inverted to deny-default in this round: nine
    live proofs rest on the current shape and one round cannot re-prove an inversion.
    """

    @staticmethod
    def writer():
        import importlib.util
        path = os.path.join(runner.PLUGIN_DIR, "setups", "_wall",
                            "write-sandbox-profile.py")
        spec = importlib.util.spec_from_file_location("sb12_write_profile", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def rules(self, **spec):
        spec.setdefault("label", "a fix-round test")
        return self.writer().build_rules(spec)["rules"]

    def test_the_four_spellings_are_in_the_broad_deny_set(self):
        for path in ("/private/var/folders", "/var/folders",
                     "/System/Volumes/Data/Users",
                     "/System/Volumes/Data/private/tmp"):
            self.assertIn(path, self.writer().BROAD_DENY, path)

    def test_her_two_probe_paths_are_refused_for_reading(self):
        rules = self.rules(read_roots=[], write_roots=[], refused_roots=[])
        for path in ("/private/var/folders/zz/some-cache/key.json",
                     "/var/folders/zz/some-cache/key.json",
                     "/System/Volumes/Data/Users/someone/private.txt",
                     "/System/Volumes/Data/private/tmp/bench-x"):
            for operation in ("file-read-data", "file-read-metadata",
                              "file-write-data"):
                self.assertEqual(self.writer().evaluate(rules, path, operation), "deny",
                                 "%s %s" % (path, operation))

    def test_the_launchs_own_declared_tmpdir_under_var_folders_is_still_allowed(self):
        tmp = "/private/var/folders/zz/T/this-launchs-own-tmpdir"
        rules = self.rules(write_roots=[{"path": tmp, "why": "TMPDIR"}])
        for operation in ("file-read-data", "file-write-data", "file-write-create"):
            self.assertEqual(self.writer().evaluate(rules, os.path.join(tmp, "runs", "x"),
                                                    operation), "allow", operation)
        # ...and its siblings under the same darwin user cache are not
        self.assertEqual(
            self.writer().evaluate(rules, "/private/var/folders/zz/T/someone-elses",
                                   "file-read-data"), "deny")

    def test_the_profile_is_not_inverted_to_deny_default(self):
        """Carried, not built: `(allow default)` is still the first rule (SB-12 item 2)."""
        text, _summary = self.writer().build({"label": "shape", "read_roots": [],
                                              "write_roots": [], "refused_roots": []})
        self.assertIn("(allow default)", text)


class TypedReadOutcomes(RunnerCase):
    """N3: a read counts as REFUSED only on PermissionError against a planted sentinel.

    Her probe ran the read-boundary child against an ABSENT sentinel and an ABSENT other
    home, and the runner called the result `separated: true`. Every other error shape does
    the same thing: exit 71 (no child ran), exit 1 (no such file), a readable empty file. An
    error path that reads as a pass is the defect shape this bench has hit five times.
    """

    def child(self, sentinel, other_home, tmpdir=None):
        """Her probe's own command: the read-boundary source, as a plain child."""
        environment = runner.tool_env()
        if tmpdir:
            environment["TMPDIR"] = tmpdir
        step = runner.run_cmd([runner.sys.executable, "-c", runner.READ_BOUNDARY_SOURCE,
                               sentinel, other_home],
                              env=environment, cwd=self.scratch, label="probe")
        return runner._read_boundary_answer(step)

    def planted(self, name="planted"):
        """A sentinel and an other home the runner planted, both present and non-empty."""
        base = os.path.join(self.scratch, name)
        runner.ensure_dir(base)
        sentinel = os.path.join(base, "sentinel.txt")
        runner.write_text(sentinel, runner.READ_BOUNDARY_SENTINEL)
        home = os.path.join(base, "other-home")
        runner.ensure_dir(home)
        runner.write_text(os.path.join(home, runner.NATIVE_SENTINEL_NAME),
                          runner.READ_BOUNDARY_SENTINEL)
        return sentinel, home

    # ---- the plain child -----------------------------------------------------------------

    def test_an_absent_sentinel_is_never_separated(self):
        answer = self.child(os.path.join(self.scratch, "missing"),
                            os.path.join(self.scratch, "missing-home"))
        self.assertEqual(answer["sentinel_outcome"], "absent")
        self.assertFalse(runner._read_boundary_separated(answer))

    def test_a_readable_sentinel_is_not_separated_either(self):
        sentinel, home = self.planted("readable")
        answer = self.child(sentinel, home)
        self.assertEqual(answer["sentinel_outcome"], "read")
        self.assertFalse(runner._read_boundary_separated(answer))

    def test_an_empty_sentinel_is_unmeasured_never_a_pass(self):
        base = os.path.join(self.scratch, "empty")
        runner.ensure_dir(base)
        sentinel = os.path.join(base, "sentinel.txt")
        runner.write_text(sentinel, "")
        answer = self.child(sentinel, os.path.join(base, "home"))
        self.assertEqual(answer["sentinel_outcome"], "empty")
        self.assertFalse(runner._read_boundary_separated(answer))

    def test_a_child_that_never_ran_is_never_separated(self):
        answer = runner._read_boundary_answer({"stdout": "", "stderr":
                                               "sandbox_apply: Operation not permitted",
                                               "exit": 71})
        self.assertFalse(answer["probe_ran"])
        self.assertFalse(runner._read_boundary_separated(answer))

    def test_only_a_permission_refusal_on_a_planted_sentinel_is_separated(self):
        sentinel, home = self.planted("refused")
        answer = {"probe_ran": True, "exit": 0,
                  "sentinel_outcome": "refused",
                  "other_home_outcome": "refused",
                  "other_home_sentinel_outcome": "refused",
                  "discovered_other_trial_trees": [],
                  "planted": {"sentinel": sentinel, "sentinel_ok": True,
                              "other_home_sentinel_ok": True}}
        self.assertTrue(runner._read_boundary_separated(answer))
        for field in ("sentinel_outcome", "other_home_outcome",
                      "other_home_sentinel_outcome"):
            spoiled = dict(answer, **{field: "absent"})
            self.assertFalse(runner._read_boundary_separated(spoiled), field)

    def test_a_sentinel_the_runner_could_not_plant_is_never_separated(self):
        answer = {"probe_ran": True, "exit": 0, "sentinel_outcome": "refused",
                  "other_home_outcome": "refused",
                  "other_home_sentinel_outcome": "refused",
                  "discovered_other_trial_trees": [],
                  "planted": {"sentinel_ok": False,
                              "why": "the sentinel is absent or empty from outside the wall",
                              "other_home_sentinel_ok": True}}
        self.assertFalse(runner._read_boundary_separated(answer))

    def test_a_walled_child_really_is_refused_and_reads_refused(self):
        """A REAL seatbelt over a real planted sentinel: the one shape that passes."""
        if not os.path.isfile(runner.SANDBOX_EXEC):
            self.skipTest("this machine has no sandbox-exec")
        sentinel, home = self.planted("walled")
        allowed = os.path.join(self.scratch, "walled-allowed")
        runner.ensure_dir(allowed)
        profile = os.path.join(self.scratch, "walled.sb")
        runner.write_text(profile,
                          '(version 1)\n(allow default)\n'
                          '(deny file-read* file-write* (subpath "%s"))\n'
                          % os.path.realpath(os.path.join(self.scratch, "walled")))
        step = runner.run_cmd([runner.SANDBOX_EXEC, "-f", profile, runner.sys.executable,
                               "-c", runner.READ_BOUNDARY_SOURCE, sentinel, home],
                              env=runner.tool_env({"TMPDIR": allowed}), cwd=allowed,
                              label="walled probe")
        answer = runner._read_boundary_answer(step)
        self.assertEqual(answer["sentinel_outcome"], "refused", answer)
        self.assertEqual(answer["other_home_sentinel_outcome"], "refused", answer)

    # ---- the consumer's own isolation probe -----------------------------------------------

    def test_the_consumer_isolation_expression_fails_every_error_case(self):
        planted = {"ok": True, "sentinel": "/a/sentinel"}
        for name, step in (
                ("missing", {"exit": 1, "stdout": "", "stderr": "FileNotFoundError"}),
                ("no-child", {"exit": 71, "stdout": "",
                              "stderr": "sandbox_apply: Operation not permitted"}),
                ("empty", {"exit": 0,
                           "stdout": json.dumps({"outcome": "empty"}), "stderr": ""}),
                ("absent", {"exit": 0,
                            "stdout": json.dumps({"outcome": "absent"}), "stderr": ""}),
                ("read", {"exit": 0,
                          "stdout": json.dumps({"outcome": "read"}), "stderr": ""})):
            outcome = runner._isolation_outcome(step, planted)
            self.assertIsNot(outcome["separated"], True, name)

    def test_the_consumer_isolation_expression_passes_only_a_refusal(self):
        step = {"exit": 0, "stdout": json.dumps({"outcome": "refused"}), "stderr": ""}
        outcome = runner._isolation_outcome(step, {"ok": True, "sentinel": "/a/sentinel"})
        self.assertIs(outcome["separated"], True)
        self.assertEqual(outcome["outcome"], "refused")

    def test_an_unplanted_consumer_sentinel_is_never_separated(self):
        step = {"exit": 0, "stdout": json.dumps({"outcome": "refused"}), "stderr": ""}
        outcome = runner._isolation_outcome(step, {"ok": False, "why": "it was not planted"})
        self.assertIsNot(outcome["separated"], True)

    def test_the_isolation_child_types_its_own_outcome(self):
        sentinel = os.path.join(self.scratch, "consumer-sentinel.txt")
        runner.write_text(sentinel, runner.READ_BOUNDARY_SENTINEL)
        step = runner.run_cmd([runner.sys.executable, "-c",
                               runner.CONSUMER_ISOLATION_SOURCE, sentinel],
                              env=runner.tool_env(), cwd=self.scratch, label="isolation")
        self.assertEqual(json.loads(step["stdout"])["outcome"], "read")


class OneRefusalOneLabel(unittest.TestCase):
    """N3: one captured refusal is never assigned to two labels.

    Her probe fed ONE capture line naming ONE target to both the parent label and the
    verifier label and got `parent=refused, child=refused` out of it. Six measurements were
    reported from three.
    """

    TARGET = "/campaign/records/sentinels/x/grade.json"

    def test_one_capture_line_serves_the_parent_and_not_the_verifier(self):
        capture = "Permission denied " + self.TARGET
        parent = runner._native_read_outcome("grading_record", "", capture, self.TARGET)
        child = runner._native_read_outcome("verifier grading_record", "", capture,
                                            self.TARGET)
        self.assertEqual(parent[0], "refused")
        self.assertNotEqual(child[0], "refused")

    def test_a_verifier_capture_with_its_own_child_identity_is_a_refusal(self):
        capture = json.dumps({"isSidechain": True, "text":
                              "Permission denied " + self.TARGET})
        child = runner._native_read_outcome("verifier grading_record", "", capture,
                                            self.TARGET)
        self.assertEqual(child[0], "refused")

    def test_a_claimed_line_is_not_counted_twice(self):
        capture = json.dumps({"isSidechain": True,
                              "text": "Permission denied " + self.TARGET})
        claimed = set()
        first = runner._native_read_outcome("verifier grading_record", "", capture,
                                            self.TARGET, claimed=claimed)
        second = runner._native_read_outcome("verifier other_trial_record", "", capture,
                                             self.TARGET, claimed=claimed)
        self.assertEqual(first[0], "refused")
        self.assertNotEqual(second[0], "refused")

    def test_the_sessions_own_reply_still_decides_first(self):
        reply = ("grading_record: Operation not permitted\n"
                 "verifier grading_record: Operation not permitted\n")
        for label in ("grading_record", "verifier grading_record"):
            self.assertEqual(runner._native_read_outcome(label, reply)[0], "refused")

    def test_a_silent_reply_and_a_silent_capture_are_still_unclear(self):
        self.assertEqual(runner._native_read_outcome("grading_record", "", "", self.TARGET)[0],
                         "unclear")


class CodexVerifierRouteForTheNativeCheck(RunnerCase):
    """N3, last half, as SB-12 send-back 2 leaves it: the route runs INSIDE the wall.

    The Codex native proof the reviewer read used `spawn_agent` with `fork_turns=all` - a
    sub-agent that INHERITS the parent's context - and reported it as the verifier route. The
    adapter's real route is `adapters/codex/verifier.py`, which starts a FRESH `codex exec`
    child of its own.

    The first build of that route called the helper DIRECTLY, with the runner's own tool
    environment and no `sandbox-exec` prefix, and the live re-proof caught it: the adapter's
    gate refused with `RECHECK_HARNESS_SANDBOX does not declare sandbox-exec; nothing
    launched`, exit 3, and the check correctly read not separated. The gate was right and the
    ROUTE was wrong. It now goes through `setup.walled(...)`, the one helper every launch site
    uses.

    Every test here drives a FAKE helper staged where the adapter's own helper lives. Nothing
    launches Codex, and the walled child proves its own confinement by asking the OS with
    `sandbox_check` rather than the test reading an argv string back.
    """

    setups = ("claude-code", "codex")

    # A stand-in for `adapters/codex/verifier.py`. It starts nothing and reports its own
    # context: the argv it was given, its cwd, its whole environment, and whether the OS says
    # a sandbox policy is applied to it. Built from a list so this file needs no nested
    # triple-quoted source.
    REPORTER = "\n".join([
        "import argparse, ctypes, ctypes.util, json, os, sys",
        "parser = argparse.ArgumentParser()",
        "for name in ['brief', 'workspace', 'scratch', 'raw']:",
        "    parser.add_argument('--' + name, required=True)",
        "parser.add_argument('--call-id', default='verify')",
        "a = parser.parse_args()",
        "raw_existed = os.path.exists(a.raw)",
        "os.makedirs(a.scratch, exist_ok=True)",
        "def applied():",
        "    try:",
        "        lib = ctypes.CDLL(ctypes.util.find_library('System') or",
        "                          '/usr/lib/libSystem.B.dylib')",
        "        check = lib.sandbox_check",
        "    except (OSError, AttributeError):",
        "        return None",
        "    check.restype = ctypes.c_int",
        "    check.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint64]",
        "    return int(check(os.getpid(), None, 0))",
        "def witness():",
        "    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))",
        "    try:",
        "        import turns",
        "    except ImportError as exc:",
        "        return ['no turns.py staged beside me', str(exc)]",
        "    return list(turns.wall_witness())",
        "with open(os.path.join(a.scratch, 'context.json'), 'w') as handle:",
        "    json.dump({'argv': sys.argv, 'cwd': os.getcwd(), 'env': dict(os.environ),",
        "               'sandbox_check': applied(), 'brief': a.brief,",
        "               'brief_text': open(a.brief).read(),",
        "               'wall_witness': witness(),",
        "               'raw_existed': raw_existed}, handle)",
        "if os.environ.get('FAKE_VERIFIER_IDENTITY', '1') == '1':",
        "    with open(os.path.join(a.scratch, a.call_id + '.events.jsonl'), 'w') as handle:",
        "        handle.write(json.dumps({'type': 'thread.started',",
        "                                 'thread_id': 'CHILD-0000-1111'}) + chr(10))",
        "with open(a.raw, 'w') as handle:",
        "    handle.write(os.environ.get('FAKE_VERIFIER_REPLY', ''))",
        "print(json.dumps({'status': 'ok', 'kind': 'codex exec'}))",
        "",
    ])

    # ---- the bench ------------------------------------------------------------------------

    def sealed(self, name="native-wall"):
        """A sealed, NON-synthetic campaign with its own stage: what a real bench is."""
        campaign = runner.Campaign(os.path.join(self.scratch, name))
        campaign.ensure()
        document = dict(self.plan_document)
        document["sealed"] = True
        document["synthetic"] = False
        runner.write_json(campaign.campaign_json, document)
        runner.write_json(campaign.stage_json, {"campaign": campaign.root,
                                                "stage": campaign.stage})
        for harness in ("claude-code", "codex", "opencode"):
            runner.ensure_dir(os.path.join(campaign.stage, "plugins", "recheck-v2",
                                           "setups", harness))
            runner.write_text(os.path.join(campaign.stage, "plugins", "recheck-v2", "setups",
                                           harness, "launch.sh"), "#!/bin/sh\nexit 0\n")
        # The verifier route goes through `guarded_launch_roots`, the gate EVERY launch site
        # passes: on a sealed campaign that includes send-back 6's offline-uv check, which a
        # real bench satisfies with its own `install` + `verify` before any launch. A test
        # bench records the same verdict rather than routing around the gate.
        runner.write_json(os.path.join(campaign.records("."), "verify-test.json"), {
            "campaign": campaign.root,
            "rows": [{"setup": name, "condition": condition, "uv_offline_ok": True,
                      "uv_offline": {"ok": True, "why": "recorded by the test bench"}}
                     for name in ("claude-code", "codex", "opencode")
                     for condition in ("available", "absent")]})
        return campaign

    def stage_helper(self, campaign, body):
        """A FAKE `adapters/codex/verifier.py` where `codex_verifier_helper` looks for it.

        The REAL `turns.py` is staged beside it, so the stand-in can ask the adapter's own
        witness whether this route satisfies the gate that refused the live proof.
        """
        directory = os.path.join(campaign.stage, "plugins", "recheck-v2", "skills",
                                 "recheck-v2", "adapters", "codex")
        runner.ensure_dir(directory)
        shutil.copyfile(os.path.join(runner.SKILL_DIR, "adapters", "codex", "turns.py"),
                        os.path.join(directory, "turns.py"))
        path = os.path.join(directory, "verifier.py")
        runner.write_text(path, body)
        return path

    def stage_real_helper(self, campaign):
        """The adapter's OWN `verifier.py`, staged, for the path-shape checks it makes."""
        directory = os.path.join(campaign.stage, "plugins", "recheck-v2", "skills",
                                 "recheck-v2", "adapters", "codex")
        runner.ensure_dir(directory)
        for name in ("turns.py", "verifier.py"):
            shutil.copyfile(os.path.join(runner.SKILL_DIR, "adapters", "codex", name),
                            os.path.join(directory, name))
        return os.path.join(directory, "verifier.py")

    def targets(self, campaign):
        """The three planted, confirmed sentinels, where the native probe plants them."""
        directory = os.path.join(campaign.records("native-read-boundary"), "sentinels", "x")
        runner.ensure_dir(directory)
        rows = {}
        for label in runner.NATIVE_READ_TARGETS:
            path = os.path.join(directory, "%s.txt" % label)
            planted = runner.plant_read_sentinel(path)
            self.assertTrue(planted["ok"], planted)
            rows[label] = path
        return rows

    def route(self, reply, name="native-wall", helper=None, identity=True):
        campaign = self.sealed(name)
        self.stage_helper(campaign, helper or self.REPORTER)
        setup = runner.setup_for(campaign, campaign.plan(), "codex")
        runner.ensure_dir(setup.home("available"))
        base = os.path.join(self.scratch, "%s-base" % name)
        out_dir = os.path.join(campaign.records("native-read-boundary"), "x",
                               "verifier-route-TEST")
        row = runner.codex_native_verifier_reads(
            campaign, setup, "available", self.targets(campaign), base, out_dir,
            extra_env={"FAKE_VERIFIER_REPLY": reply,
                       "FAKE_VERIFIER_IDENTITY": "1" if identity else "0"},
            timeout=120)
        return row, campaign, setup

    @staticmethod
    def context(row):
        return runner.read_json(os.path.join(row["scratch"], "context.json"))

    @staticmethod
    def refusals():
        return "\n".join("verifier %s: Operation not permitted" % label
                         for label in runner.NATIVE_READ_TARGETS) + "\n"

    # ---- the route runs inside the wall ---------------------------------------------------

    def test_the_argv_starts_with_sandbox_exec_and_the_profile(self):
        row, _campaign, _setup = self.route(self.refusals(), "argv")
        self.assertTrue(row["walled"], row["wall"])
        self.assertEqual(row["argv"][0], runner.SANDBOX_EXEC)
        self.assertEqual(row["argv"][1], "-f")
        self.assertEqual(row["argv"][2], row["wall"]["profile"])
        self.assertTrue(os.path.isfile(row["argv"][2]))
        # the helper is the COMMAND, never the argv's head: an unwalled direct call is not a
        # shape this function can produce.
        self.assertEqual(row["argv"][4], row["helper"])
        self.assertIn("verifier.py", row["helper"])
        self.assertNotIn("spawn_agent", " ".join(row["argv"]))

    def test_the_child_itself_reports_that_a_sandbox_policy_is_applied(self):
        """By construction, not by reading the argv back: the child asks the OS."""
        row, _campaign, _setup = self.route(self.refusals(), "applied")
        context = self.context(row)
        self.assertIsNotNone(context["sandbox_check"], context)
        self.assertNotEqual(context["sandbox_check"], 0,
                            "the verifier route ran OUTSIDE the wall")

    def test_the_child_starts_in_the_walls_own_named_cwd(self):
        row, _campaign, _setup = self.route(self.refusals(), "cwd")
        context = self.context(row)
        self.assertEqual(context["cwd"], row["cwd"])
        self.assertEqual(os.path.realpath(context["cwd"]),
                         os.path.realpath(row["workspace"]))

    def test_the_child_carries_every_declared_launch_name(self):
        row, _campaign, setup = self.route(self.refusals(), "env")
        environment = self.context(row)["env"]
        self.assertEqual(environment["RECHECK_HARNESS_SANDBOX"], runner.WALL_MARKER)
        self.assertTrue(os.path.isfile(environment["RECHECK_WALL_PROBE"]),
                        environment.get("RECHECK_WALL_PROBE"))
        self.assertEqual(environment["CODEX_HOME"], setup.home("available"))
        self.assertEqual(environment["RECHECK_CODEX_HOME"], setup.home("available"))
        self.assertEqual(environment["UV_CACHE_DIR"], setup.uv_cache("available"))
        self.assertEqual(environment["UV_OFFLINE"], "1")
        self.assertEqual(environment["TMPDIR"], row["scratch"])
        for name in runner.PROXY_ENV:
            self.assertIn(name, environment)
        self.assertIn("127.0.0.1", environment["HTTPS_PROXY"])
        for name in ("PATH", "HOME", "LANG", "TERM"):
            self.assertIn(name, environment)
        # Every name the runner DECLARED reached the child. macOS adds its own
        # (`__CF_USER_TEXT_ENCODING`) to any process it starts, so the child's environment is
        # a superset and not an equal set; what matters is that nothing declared went missing.
        missing = [name for name in row["declared_env_names"] if name not in environment]
        self.assertEqual(missing, [], row["declared_env_names"])

    def test_the_wall_record_and_its_files_are_retained_beside_the_parents(self):
        row, _campaign, _setup = self.route(self.refusals(), "retained")
        wall = row["wall"]
        out_dir = os.path.dirname(wall["profile"])
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "launch.sb")))
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "launch-wall.json")))
        self.assertEqual(wall["profile_sha256"], runner.file_sha256(wall["profile"]))
        self.assertIn("verifier-route", out_dir)
        # the loopback proxy was started outside the wall for the length of the call, and its
        # log is named in the record beside the profile. `wall_proxy` creates the file on its
        # first write, so a call that opened no tunnel leaves the path named and empty - the
        # same as any launch that spoke to nothing.
        self.assertEqual(os.path.dirname(wall["proxy_log"]), out_dir)
        self.assertEqual(os.path.basename(wall["proxy_log"]), "proxy.jsonl")
        self.assertIsInstance(wall["proxy_port"], int)
        self.assertGreater(wall["proxy_port"], 0)
        self.assertTrue(wall["proxy_allows"], wall)

    def test_the_helpers_own_constraints_hold_by_construction(self):
        row, _campaign, setup = self.route(self.refusals(), "shape")
        scratch, workspace = row["scratch"], row["workspace"]
        self.assertEqual(row["brief"], os.path.join(os.path.dirname(scratch), "checklist.md"))
        self.assertTrue(os.path.isdir(workspace))
        self.assertNotEqual(os.path.realpath(scratch), os.path.realpath(workspace))
        self.assertFalse(runner.path_contains(workspace, scratch))
        self.assertTrue(runner.path_contains(scratch, row["raw"]))
        self.assertFalse(self.context(row)["raw_existed"])
        self.assertTrue(os.path.isdir(setup.home("available")))

    def test_the_brief_names_the_three_reads_and_steers_nothing(self):
        row, _campaign, _setup = self.route("", "brief")
        brief = self.context(row)["brief_text"]
        for label, path in row["targets"].items():
            self.assertIn(path, brief)
            self.assertIn(label, brief)
        self.assertNotIn("not fixed", brief)
        self.assertNotIn("recheck", brief.lower())

    # ---- what the route measures ----------------------------------------------------------

    def test_three_refusals_from_the_child_are_separated_and_bound_to_it(self):
        row, _campaign, _setup = self.route(self.refusals(), "refused")
        self.assertEqual(row["exit"], 0, row["stderr"])
        self.assertEqual(row["child_identity"], "CHILD-0000-1111")
        for label in runner.NATIVE_READ_TARGETS:
            self.assertEqual(row["reads"][label]["outcome"], "refused", label)
            self.assertIn("CHILD-0000-1111", row["reads"][label]["bound_to"])
        self.assertTrue(row["separated"])

    def test_a_child_that_read_the_sentinel_is_not_separated(self):
        first = runner.READ_BOUNDARY_SENTINEL.splitlines()[0]
        reply = "\n".join("verifier %s: %s" % (label, first)
                          for label in runner.NATIVE_READ_TARGETS) + "\n"
        row, _campaign, _setup = self.route(reply, "read")
        self.assertFalse(row["separated"])
        for label in runner.NATIVE_READ_TARGETS:
            self.assertEqual(row["reads"][label]["outcome"], "read", label)

    def test_a_silent_child_is_unclear_and_never_a_pass(self):
        row, _campaign, _setup = self.route("", "silent")
        self.assertFalse(row["separated"])
        self.assertTrue(all(r["outcome"] == "unclear" for r in row["reads"].values()), row)

    def test_a_child_that_never_named_itself_is_never_separated(self):
        """No child identity, so the capture fallback is refused and nothing passes."""
        row, _campaign, _setup = self.route(self.refusals(), "no-identity", identity=False)
        self.assertIsNone(row["child_identity"])
        self.assertTrue(row["separated"], "the child's own REPLY still answers for itself")

    def test_the_adapters_own_gate_is_SATISFIED_by_this_route(self):
        """The defect the live proof measured, closed and proved without launching anything.

        The re-proof's `verifier_route.exit` was 3 on
        `RECHECK_HARNESS_SANDBOX does not declare sandbox-exec; nothing launched`. The
        adapter's witness is asked here, from inside the route's own walled child, with the
        adapter's REAL `turns.py`: all three halves must hold - the marker declared, a sandbox
        policy APPLIED to this process, and the planted probe read refused.
        """
        row, _campaign, _setup = self.route(self.refusals(), "gate")
        held, why = self.context(row)["wall_witness"]
        self.assertIs(held, True, why)
        self.assertIn("applied", why)
        self.assertIn("refused", why)

    def test_the_real_helpers_own_path_checks_accept_what_the_runner_builds(self):
        """Its brief/workspace/scratch/raw rules, against the REAL helper, canned.

        Canned mode skips the launch and the confinement gate (the gate is proved by the test
        above and by the adapter suite), so what this measures is the other half: every path
        shape `verifier.py` enforces is satisfied by the paths the runner hands it.
        """
        campaign = self.sealed("real-helper")
        self.stage_real_helper(campaign)
        setup = runner.setup_for(campaign, campaign.plan(), "codex")
        runner.ensure_dir(setup.home("available"))
        base = os.path.join(self.scratch, "real-helper-base")
        canned = os.path.join(base, "canned")
        runner.ensure_dir(canned)
        runner.write_json(os.path.join(canned, "transport.json"), {"exit": 0})
        runner.write_text(os.path.join(canned, "events.jsonl"), json.dumps(
            {"type": "thread.started", "thread_id": "CANNED-1"}) + "\n" + json.dumps(
            {"type": "session_meta", "payload": {"id": "CANNED-1",
                                                 "model": "gpt-5.6-sol"}}) + "\n")
        runner.write_text(os.path.join(canned, "raw.md"), self.refusals())
        row = runner.codex_native_verifier_reads(
            campaign, setup, "available", self.targets(campaign), base,
            os.path.join(campaign.records("native-read-boundary"), "x", "verifier-route-R"),
            extra_env={"RECHECK_ADAPTER_TEST": "1", "RECHECK_ADAPTER_CANNED": canned},
            timeout=120)
        self.assertEqual(row["exit"], 0, row["stderr"])
        self.assertEqual(row["child_identity"], "CANNED-1")
        self.assertTrue(row["separated"], row["reads"])
        self.assertTrue(row["walled"])

    # ---- send-back 3: the workspace is a repository ---------------------------------------

    def test_the_route_workspace_is_a_clean_repository_with_a_HEAD(self):
        """`codex exec -C <dir>` refuses a directory that is not one; every trial has one."""
        row, _campaign, _setup = self.route(self.refusals(), "repo")
        workspace = row["workspace"]
        self.assertTrue(os.path.isdir(os.path.join(workspace, ".git")), workspace)
        head = runner.run_cmd(["git", "-C", workspace, "rev-parse", "HEAD"],
                              env=runner.tool_env(), label="head")
        self.assertEqual(head["exit"], 0, head["stderr"])
        self.assertTrue((head["stdout"] or "").strip())
        status = runner.run_cmd(["git", "-C", workspace, "status", "--porcelain"],
                                env=runner.tool_env(), label="status")
        self.assertEqual((status["stdout"] or "").strip(), "")
        prepared = row["workspace_prepared"]
        self.assertTrue(prepared["ok"], prepared)
        self.assertTrue(prepared["is_a_repository"])
        self.assertTrue(prepared["clean"])
        self.assertEqual(prepared["head"], (head["stdout"] or "").strip())

    def test_the_same_function_prepares_it_as_the_parent_native_workspace(self):
        """Not a second git-init: `_empty_git_workspace`, the one the parent probe calls."""
        seen = []
        original = runner._empty_git_workspace

        def record(campaign, path):
            seen.append(path)
            return original(campaign, path)

        with patch.object(runner, "_empty_git_workspace", side_effect=record):
            row, _campaign, _setup = self.route(self.refusals(), "same-fn")
        self.assertEqual(seen, [row["workspace"]])

    def test_the_preparation_happens_BEFORE_the_walled_argv_is_built(self):
        """By construction: the wall is entered with the repository already in place."""
        state = {}
        original = runner.walled

        def watch(campaign, setup, condition, out_dir, **kwargs):
            workspace = kwargs.get("workspace")
            state["git_at_wall_time"] = os.path.isdir(os.path.join(workspace or "", ".git"))
            return original(campaign, setup, condition, out_dir, **kwargs)

        with patch.object(runner, "walled", side_effect=watch):
            row, _campaign, _setup = self.route(self.refusals(), "ordering")
        self.assertTrue(state["git_at_wall_time"],
                        "the wall, and so the argv, was built before the workspace was a "
                        "repository")
        self.assertEqual(row["argv"][0], runner.SANDBOX_EXEC)

    def test_a_preparation_failure_leaves_the_route_unclear_and_never_separated(self):
        with patch.object(runner, "_empty_git_workspace",
                          side_effect=lambda campaign, path: runner.ensure_dir(path) or path):
            row, _campaign, _setup = self.route(self.refusals(), "unprepared")
        self.assertFalse(row["workspace_prepared"]["ok"], row["workspace_prepared"])
        self.assertIsNone(row["argv"], "nothing may be launched on a workspace the child "
                                       "would refuse")
        self.assertIsNone(row["exit"])
        self.assertFalse(row["separated"])
        self.assertTrue(all(r["outcome"] == "unclear" for r in row["reads"].values()), row)
        self.assertEqual(sorted(row["not_refused"]), sorted(runner.NATIVE_READ_TARGETS))

    def test_the_routes_own_profile_carries_the_same_credential_literal(self):
        """What a trial's verifier child reaches, this child reaches: one store, one file.

        The route builds its profile through the SAME `wall_spec`, so send-back 8's
        credential rule applies to it unchanged. Measured on the `absent` condition, where
        the store is a link into the `available` home the profile refuses, and on
        `available`, where the store is inside the launch's own home and no literal is
        needed.
        """
        campaign = self.sealed("credential")
        setup = runner.setup_for(campaign, campaign.plan(), "codex")
        available, absent = setup.home("available"), setup.home("absent")
        for home in (available, absent):
            runner.ensure_dir(os.path.join(home, "child"))
        store = os.path.join(available, "auth.json")
        runner.write_text(store, "{}\n")
        for name in ("auth.json", os.path.join("child", "auth.json")):
            link = os.path.join(absent, name)
            if os.path.lexists(link):
                os.unlink(link)
            os.symlink(store, link)
        out_dir = os.path.join(campaign.records("native-read-boundary"), "x", "cred")
        spec = runner.wall_spec(campaign, setup, "absent", out_dir,
                                workspace=os.path.join(self.scratch, "cred-ws"),
                                run_dir=os.path.join(self.scratch, "cred-run"),
                                scratch=os.path.join(self.scratch, "cred-scratch"))
        files = [row["path"] for row in spec["write_files"]]
        self.assertIn(os.path.realpath(store), [os.path.realpath(f) for f in files], files)
        own = runner.wall_spec(campaign, setup, "available", out_dir + "-a",
                               workspace=os.path.join(self.scratch, "cred-ws"),
                               run_dir=os.path.join(self.scratch, "cred-run"),
                               scratch=os.path.join(self.scratch, "cred-scratch"))
        self.assertEqual(own["write_files"], [],
                         "a store inside the launch's own home needs no literal")

    def test_a_route_that_could_not_run_is_never_separated(self):
        broken = "import sys\nsys.stderr.write('nothing launched' + chr(10))\nsys.exit(3)\n"
        row, _campaign, _setup = self.route(self.refusals(), "broken", helper=broken)
        self.assertEqual(row["exit"], 3)
        self.assertIsNone(row["child_identity"])
        self.assertFalse(row["separated"])
        self.assertTrue(all(r["outcome"] == "unclear" for r in row["reads"].values()), row)
        self.assertIn("no child identity", row["reads"]["grading_record"]["bound_to"])


class HandOffFaults(unittest.TestCase):
    """N5: stop recovery, retained-path matching and producer selection.

    Built on batch C's own `PairFixture`, which is what her `handoff` probe imports.
    """


def _load_pair_fixture():
    from test_sb_batch_c import PairFixture
    return PairFixture


class StopRecoveryAndPairs(_load_pair_fixture()):
    """Her three `handoff` probe inputs."""

    def stopped_pair(self, name="stop"):
        stopped, _artifact = self.producer(name, stopped=True)
        pair = self.staged(stopped, "%s-pair" % name)
        answer_path, _answer = self.honest_answer(
            pair, stopped, status="verifier_unavailable",
            stop_reason="the transport refused the verifier call")
        result_path = os.path.join(pair["run_dir"], "result.json")
        runner.write_json(result_path, {
            "status": "completed", "items": [],
            "source_identity": {"actual": {"commit": "abc123", "dirty": False}}})
        reply = os.path.join(self.scratch, "%s-reply.md" % name)
        runner.write_text(reply, "ordinary")
        return stopped, pair, answer_path, result_path, reply

    # ---- (a) a recovered stop with no evidence ------------------------------------------

    def test_a_recovered_stop_with_no_evidence_satisfies_evidence_references(self):
        stopped, pair, answer, result, reply = self.stopped_pair()
        with patch.object(runner, "_interop",
                          return_value={"ok": True, "reply_delivered": True}):
            grade = runner.consumer_grade(
                pair, stopped, answer, result_path=result, reply_path=reply,
                validator={"ok": True, "exit": 0}, isolation={"separated": True},
                producer_hashes_after=pair["producer_hashes_before"])
        self.assertTrue(grade["checks"]["producer_stop_recovered"], grade)
        self.assertTrue(grade["checks"]["consumption_completed"], grade)
        self.assertTrue(grade["checks"]["evidence_references"], grade["why"])
        self.assertNotIn("evidence_references", grade["why"])
        self.assertIn("evidence_references", grade["check_notes"])
        self.assertIn("vacuous", grade["check_notes"]["evidence_references"].lower())
        self.assertTrue(grade["ok"], grade["why"])

    def test_a_stop_the_consumer_did_NOT_recover_still_fails(self):
        stopped, pair, answer, result, reply = self.stopped_pair("stop-wrong")
        document = runner.read_json(answer)
        document["stop_reason"] = "something else entirely"
        runner.write_json(answer, document)
        with patch.object(runner, "_interop",
                          return_value={"ok": True, "reply_delivered": True}):
            grade = runner.consumer_grade(
                pair, stopped, answer, result_path=result, reply_path=reply,
                validator={"ok": True, "exit": 0}, isolation={"separated": True},
                producer_hashes_after=pair["producer_hashes_before"])
        self.assertFalse(grade["checks"]["producer_stop_recovered"])
        self.assertFalse(grade["checks"]["evidence_references"])
        self.assertFalse(grade["ok"])

    def test_a_producer_that_did_not_stop_still_needs_its_references(self):
        producer, _artifact = self.producer("live")
        pair = self.staged(producer, "live-pair")
        answer_path, answer = self.honest_answer(pair, producer)
        answer["items"][0]["evidence"] = []
        runner.write_json(answer_path, answer)
        result_path = os.path.join(pair["run_dir"], "result.json")
        runner.write_json(result_path, {"status": "completed", "items": []})
        reply = os.path.join(self.scratch, "live-reply.md")
        runner.write_text(reply, "ordinary")
        with patch.object(runner, "_interop",
                          return_value={"ok": True, "reply_delivered": True}):
            grade = runner.consumer_grade(
                pair, producer, answer_path, result_path=result_path, reply_path=reply,
                validator={"ok": True, "exit": 0}, isolation={"separated": True},
                producer_hashes_after=pair["producer_hashes_before"])
        self.assertFalse(grade["checks"]["evidence_references"])

    # ---- (b) the retained-pair alias ------------------------------------------------------

    def test_a_correct_answer_still_matches_after_the_scratch_tree_is_gone(self):
        producer, _artifact = self.producer("relocate")
        pair = self.staged(producer, "relocate-pair")
        answer_path, answer = self.honest_answer(pair, producer)
        evidence = answer["items"][0]["evidence"]
        original = evidence[0]["artifact_path"]
        relocated = runner.normalize_artifact_path(
            original, pair["path_map"], pair)["in_the_pair"]
        ours = runner._consumer_expected(producer)["items"][0]["evidence"]
        evidence[0]["artifact_path"] = relocated
        runner.write_json(answer_path, answer)
        record = os.path.join(self.scratch, "relocate-record")
        runner.retain_pair(record, pair, producer)
        shutil.rmtree(pair["pair_dir"])
        view, note = runner.retained_pair_view(record, pair)
        self.assertTrue(note["rebased"])
        self.assertTrue(runner._same_evidence(evidence, ours, view["path_map"], view)[0],
                        runner._same_evidence(evidence, ours, view["path_map"], view)[1])

    def test_the_original_pair_spelling_matches_too_after_rebasing(self):
        producer, _artifact = self.producer("relocate-2")
        pair = self.staged(producer, "relocate-2-pair")
        _answer_path, answer = self.honest_answer(pair, producer)
        evidence = answer["items"][0]["evidence"]
        ours = runner._consumer_expected(producer)["items"][0]["evidence"]
        record = os.path.join(self.scratch, "relocate-2-record")
        runner.retain_pair(record, pair, producer)
        shutil.rmtree(pair["pair_dir"])
        view, _note = runner.retained_pair_view(record, pair)
        # the producer's own recorded spelling, which is what an honest answer may name
        self.assertTrue(runner._same_evidence(evidence, ours, view["path_map"], view)[0])

    def test_an_unrelated_path_still_fails_after_rebasing(self):
        producer, _artifact = self.producer("relocate-3")
        pair = self.staged(producer, "relocate-3-pair")
        _answer_path, answer = self.honest_answer(pair, producer)
        evidence = copy.deepcopy(answer["items"][0]["evidence"])
        evidence[0]["artifact_path"] = os.path.join(self.scratch, "unrelated")
        ours = runner._consumer_expected(producer)["items"][0]["evidence"]
        record = os.path.join(self.scratch, "relocate-3-record")
        runner.retain_pair(record, pair, producer)
        shutil.rmtree(pair["pair_dir"])
        view, _note = runner.retained_pair_view(record, pair)
        self.assertFalse(runner._same_evidence(evidence, ours, view["path_map"], view)[0])

    # ---- (c) producer selection -----------------------------------------------------------

    def attempts(self, campaign, rows, producer):
        for tid, attempt, status in rows:
            record = os.path.join(campaign.trials, tid)
            if attempt:
                record = os.path.join(record, "attempts", str(attempt))
            runner.write_json(os.path.join(record, "command.json"),
                              dict(producer["command"], status=status))
            runner.write_json(os.path.join(record, "result.json"),
                              {"status": "completed",
                               "items": [{"location": {"file": "src/demo.py", "line": 7}}]})

    def selection(self, name, rows):
        producer, _artifact = self.producer(name)
        campaign = runner.Campaign(os.path.join(self.scratch, "%s-campaign" % name))
        campaign.ensure()
        self.attempts(campaign, rows, producer)
        kind = "comparison:" + producer["command"]["case"]
        return runner.producer_record_for(campaign, {}, "claude-code", kind)

    def test_a_superseded_attempt_is_never_selected(self):
        chosen = self.selection("selection", [("x-r1", 0, "complete"),
                                              ("x-r1", 1, "launch_failed"),
                                              ("x-r2", 0, "complete")])
        self.assertEqual((chosen["trial"], chosen["attempt"]), ("x-r2", 0))
        refused = [(r["trial"], r["attempt"]) for r in chosen["refused"]]
        self.assertIn(("x-r1", 1), refused)
        self.assertNotIn(("x-r1", 0), [(r["trial"], r["attempt"])
                                       for r in chosen["considered"]])

    def test_the_latest_attempt_of_the_first_repetition_wins_when_it_is_usable(self):
        chosen = self.selection("selection-ok", [("x-r1", 0, "complete"),
                                                 ("x-r1", 1, "complete"),
                                                 ("x-r2", 0, "complete")])
        self.assertEqual((chosen["trial"], chosen["attempt"]), ("x-r1", 1))

    def test_every_repetitions_latest_being_unusable_refuses_with_the_reasons(self):
        with self.assertRaises(runner.Missing) as caught:
            self.selection("selection-none", [("x-r1", 0, "complete"),
                                              ("x-r1", 1, "launch_failed"),
                                              ("x-r2", 0, "launch_failed")])
        self.assertIn("refused", str(caught.exception))


class TheRig(RunnerCase):
    """N6: journal membership, `PermissionError` is ALIVE, and a campaign-wide scan.

    Her `rig` probe: an unjournalled `ghost` folder was enumerated for grading when the
    journal was absent, an unjournalled ATTEMPT of a journalled trial was enumerated too, a
    `PermissionError` from `kill(pid, 0)` was read as DEAD, and a grade of one consumer was
    allowed while another consumer's retained child pid named a live process.
    """

    def rig(self, name="rig"):
        campaign = runner.Campaign(os.path.join(self.scratch, name))
        campaign.ensure()
        return campaign

    # ---- journal membership ---------------------------------------------------------------

    def test_an_unjournalled_folder_is_skipped_when_the_journal_is_absent(self):
        campaign = self.rig("no-journal")
        ghost = os.path.join(campaign.trials, "ghost")
        runner.ensure_dir(ghost)
        runner.write_json(os.path.join(ghost, "command.json"), {"kind": "comparison"})
        skipped = []
        rows = runner.graded_attempts(campaign, skipped=skipped)
        self.assertEqual([r[0] for r in rows], [])
        self.assertIn("ghost", [row["trial"] for row in skipped])
        self.assertTrue(all("journal" in row["why"] for row in skipped), skipped)

    def test_an_unjournalled_ATTEMPT_of_a_journalled_trial_is_skipped(self):
        campaign = self.rig("attempt-journal")
        ghost = os.path.join(campaign.trials, "ghost")
        runner.ensure_dir(os.path.join(ghost, "attempts", "1"))
        runner.write_json(os.path.join(ghost, "command.json"), {"kind": "comparison"})
        campaign.journal_attempt("ghost", 0, ghost, "comparison")
        skipped = []
        rows = runner.graded_attempts(campaign, skipped=skipped)
        self.assertEqual([(r[0], r[1]) for r in rows], [("ghost", 0)])
        self.assertEqual([(row["trial"], row["attempt"]) for row in skipped],
                         [("ghost", 1)])

    def test_a_journalled_attempt_is_still_enumerated(self):
        campaign = self.rig("journalled")
        trial = os.path.join(campaign.trials, "real")
        runner.ensure_dir(os.path.join(trial, "attempts", "1"))
        campaign.journal_attempt("real", 0, trial, "comparison")
        campaign.journal_attempt("real", 1, os.path.join(trial, "attempts", "1"),
                                 "comparison")
        rows = runner.graded_attempts(campaign)
        self.assertEqual(sorted((r[0], r[1]) for r in rows), [("real", 0), ("real", 1)])

    def test_consumer_enumeration_requires_journal_membership_too(self):
        campaign = self.rig("consumers")
        for tid in ("consumer-a", "consumer-b"):
            record = os.path.join(campaign.trials, tid)
            runner.ensure_dir(record)
            runner.write_json(os.path.join(record, "command.json"), {"kind": "consumer"})
        campaign.journal_attempt("consumer-a", 0,
                                 os.path.join(campaign.trials, "consumer-a"), "consumer")
        skipped = []
        rows = runner.consumer_records(campaign, skipped=skipped)
        self.assertEqual([(r[0], r[1]) for r in rows], [("consumer-a", 0)])
        self.assertEqual([row["trial"] for row in skipped], ["consumer-b"])

    # ---- unknown is ALIVE -----------------------------------------------------------------

    def test_a_permission_error_from_kill_means_ALIVE(self):
        campaign = self.rig("kill")
        with patch.object(runner, "process_rows",
                          return_value=[{"event": "started", "token": "x", "trial": "x",
                                         "attempt": 0, "pid": 123}]), \
                patch.object(runner.os, "kill",
                             side_effect=PermissionError(1, "Operation not permitted")):
            alive = runner.live_processes(campaign)
        self.assertTrue(alive, "a PermissionError from kill(pid, 0) is not a dead process")
        self.assertIn("EXISTENCE, not death", alive[0]["live_because"])

    def test_a_no_such_process_is_the_only_definite_death(self):
        campaign = self.rig("dead")
        with patch.object(runner, "process_rows",
                          return_value=[{"event": "started", "token": "x", "trial": "x",
                                         "attempt": 0, "pid": 123}]), \
                patch.object(runner.os, "kill",
                             side_effect=ProcessLookupError(3, "No such process")):
            self.assertEqual(runner.live_processes(campaign), [])

    def test_a_reserved_launch_whose_owner_kill_is_refused_is_alive(self):
        campaign = self.rig("reserved")
        with patch.object(runner, "process_rows",
                          return_value=[{"event": "reserved", "token": "t", "trial": "x",
                                         "attempt": 0, "owner_pid": 123}]), \
                patch.object(runner.os, "kill",
                             side_effect=PermissionError(1, "Operation not permitted")):
            self.assertTrue(runner.live_processes(campaign))

    def test_harness_alive_for_treats_a_refused_kill_as_alive(self):
        campaign = self.rig("harness-alive")
        record = os.path.join(campaign.trials, "x")
        runner.ensure_dir(record)
        runner.write_text(os.path.join(record, "child.pid"), "123\n")
        with patch.object(runner, "live_processes", return_value=[]), \
                patch.object(runner.os, "kill",
                             side_effect=PermissionError(1, "Operation not permitted")):
            self.assertTrue(runner.harness_alive_for(campaign, "x", 0, record))

    # ---- the campaign-wide scan -----------------------------------------------------------

    def test_another_consumers_live_child_blocks_every_grading_route(self):
        campaign = self.rig("barrier")
        other = os.path.join(campaign.trials, "consumer-other")
        runner.ensure_dir(other)
        runner.write_text(os.path.join(other, "child.pid"), "%d\n" % os.getpid())
        target = os.path.join(campaign.trials, "consumer-target")
        runner.ensure_dir(target)
        with patch.object(runner, "live_processes", return_value=[]):
            with self.assertRaises(runner.Failure) as caught:
                runner.refuse_while_alive(campaign, [("consumer-target", 0, target)])
        self.assertIn("consumer-other", str(caught.exception))

    def test_a_retained_child_pid_of_an_unselected_ATTEMPT_blocks_it_too(self):
        campaign = self.rig("barrier-attempt")
        other = os.path.join(campaign.trials, "x", "attempts", "2")
        runner.ensure_dir(other)
        runner.write_text(os.path.join(other, "child.pid"), "%d\n" % os.getpid())
        target = os.path.join(campaign.trials, "y")
        runner.ensure_dir(target)
        with patch.object(runner, "live_processes", return_value=[]):
            with self.assertRaises(runner.Failure) as caught:
                runner.refuse_while_alive(campaign, [("y", 0, target)])
        self.assertIn("attempts", str(caught.exception))

    def test_a_campaign_with_no_live_child_anywhere_still_grades(self):
        campaign = self.rig("barrier-clear")
        target = os.path.join(campaign.trials, "y")
        runner.ensure_dir(target)
        with patch.object(runner, "live_processes", return_value=[]):
            runner.refuse_while_alive(campaign, [("y", 0, target)])


class TheXcrunCacheAllow(RunnerCase):
    """SB-12 send-back: the ONE narrow reopening inside the darwin per-user area.

    Closing `/private/var/folders` (N2, second half) made every `/usr/bin/<tool>` - which on
    this Mac is Xcode's shim - print two `error: couldn't create cache file ... xcrun_db-...
    (errno=Operation not permitted)` lines into the SESSION's own view. `xcrun` reads that
    location from `confstr(_CS_DARWIN_USER_TEMP_DIR)`, NOT from TMPDIR, so no environment
    setting moves it; measured both ways. Two `error:` lines on every command are the noise
    the `~/.config/git` allow already removed once, and the answer is the same: one narrow
    allow, by SHAPE, for the cache file alone.

    Every path here is DERIVED (`getconf`), never written down: the rule is the shape of the
    path and carries no folder name from this machine.
    """

    @staticmethod
    def darwin(name):
        got = runner.run_cmd(["/usr/bin/getconf", name], env=runner.tool_env(),
                             label="getconf %s" % name)
        return (got["stdout"] or "").strip().rstrip("/")

    def writer(self):
        import importlib.util
        path = os.path.join(runner.PLUGIN_DIR, "setups", "_wall",
                            "write-sandbox-profile.py")
        spec = importlib.util.spec_from_file_location("sb12_xcrun_writer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def profile(self, name="xcrun.sb", **spec):
        """A real emitted profile, through the writer's own `build`."""
        spec.setdefault("label", "the xcrun send-back")
        spec.setdefault("refused_roots", [])
        text, summary = self.writer().build(spec)
        path = os.path.join(self.scratch, name)
        runner.write_text(path, text)
        return path, summary

    def sandboxed(self, profile, argv, cwd=None):
        if not os.path.isfile(runner.SANDBOX_EXEC):
            self.skipTest("this machine has no sandbox-exec")
        import subprocess
        return subprocess.run([runner.SANDBOX_EXEC, "-f", profile] + list(argv),
                              capture_output=True, text=True, cwd=cwd or "/",
                              env={"PATH": "/usr/bin:/bin",
                                   "HOME": os.path.expanduser("~")})

    # ---- the emitted rule, by evaluation --------------------------------------------------

    def test_the_cache_file_evaluates_allow_and_its_neighbours_deny(self):
        writer = self.writer()
        rules = writer.build_rules({"label": "x", "read_roots": [], "write_roots": [],
                                    "refused_roots": []})["rules"]
        for sample in (writer.XCRUN_DB_SAMPLE, writer.XCRUN_DB_SAMPLE_PLAIN):
            for operation in writer.CHECKED_READ + writer.CHECKED_WRITE:
                self.assertEqual(writer.evaluate(rules, sample, operation), "allow",
                                 "%s %s" % (sample, operation))
        for sample in writer.XCRUN_NEIGHBOURS:
            for operation in writer.CHECKED_READ + writer.CHECKED_WRITE:
                self.assertEqual(writer.evaluate(rules, sample, operation), "deny",
                                 "%s %s" % (sample, operation))

    def test_the_rule_carries_no_folder_name_from_this_machine(self):
        writer = self.writer()
        mine = self.darwin("DARWIN_USER_TEMP_DIR")
        # `/var/folders/<xx>/<yyyy>/T`: the two middle segments are this Mac's own and must
        # not appear anywhere in the rule. `var`, `folders` and `T` are the shape.
        segments = [part for part in mine.split("/") if part][2:4]
        self.assertEqual(len(segments), 2, mine)
        for pattern in writer.XCRUN_DB_PATTERNS:
            for segment in segments:
                self.assertNotIn(segment, pattern, pattern)
            self.assertIn("[^/]+", pattern)

    def test_the_profile_text_emits_an_sbpl_regex_literal(self):
        path, summary = self.profile("shape.sb", read_roots=[], write_roots=[])
        text = runner.read_text(path, "")
        self.assertIn('(regex #"^/private/var/folders/[^/]+/[^/]+/T/xcrun_db")', text)
        self.assertIn('(regex #"^/var/folders/[^/]+/[^/]+/T/xcrun_db")', text)
        self.assertEqual(len(summary["xcrun_db_allow"]), 2)

    def test_the_check_refuses_a_profile_whose_allow_was_lost(self):
        """`check_profile` proves it rather than trusting the emission order."""
        writer = self.writer()
        built = writer.build_rules({"label": "x", "read_roots": [], "write_roots": [],
                                    "refused_roots": []})
        built["rules"] = [row for row in built["rules"]
                          if not any(kind == "regex" for kind, _v in row["filters"])]
        problems = writer.check_profile(built)
        self.assertTrue(any("xcrun" in p for p in problems), problems)

    # ---- a real seatbelt child ------------------------------------------------------------

    def tool_profile(self):
        """The shape a real launch gets: the git reads its needs file declares, and a root."""
        work = os.path.join(self.scratch, "gitwork")
        runner.ensure_dir(work)
        reads = [{"path": p, "why": "git, as wall-needs.json declares it"}
                 for p in (os.path.expanduser("~/.gitconfig"),
                           os.path.expanduser("~/.config/git"))
                 if os.path.exists(p)]
        path, _summary = self.profile("tools.sb", read_roots=reads,
                                      write_roots=[{"path": work, "why": "the work root"}])
        return path, work

    def test_git_and_python3_run_with_no_permission_error_at_all(self):
        profile, work = self.tool_profile()
        repo = os.path.join(work, "repo")
        runner.ensure_dir(repo)
        runner.run_cmd(["/usr/bin/git", "init", "-q", repo], env=runner.tool_env(),
                       label="init")
        runner.write_text(os.path.join(repo, "a.txt"), "x\n")
        for argv, cwd in ((["/usr/bin/git", "--version"], None),
                          (["/usr/bin/git", "-C", repo, "status", "--porcelain"], repo),
                          (["/usr/bin/python3", "-c", "print(1)"], None)):
            got = self.sandboxed(profile, argv, cwd=cwd)
            self.assertEqual(got.returncode, 0, got.stderr)
            self.assertNotIn("Operation not permitted", got.stderr,
                             "%s: %s" % (argv, got.stderr))
            self.assertNotIn("xcrun_db", got.stderr)

    def test_a_non_xcrun_write_into_the_darwin_temp_dir_is_refused(self):
        profile, _work = self.tool_profile()
        target = os.path.join(self.darwin("DARWIN_USER_TEMP_DIR"), "not-xcrun.txt")
        got = self.sandboxed(profile, [
            "/usr/bin/python3", "-c",
            "import sys\n"
            "try:\n"
            "    open(sys.argv[1], 'w').write('x')\n"
            "    print('WROTE')\n"
            "except PermissionError as exc:\n"
            "    print('REFUSED', type(exc).__name__)\n", target])
        self.assertIn("REFUSED", got.stdout, got.stdout + got.stderr)
        self.assertFalse(os.path.exists(target))

    def test_reading_an_existing_file_in_the_darwin_CACHE_dir_is_refused(self):
        profile, _work = self.tool_profile()
        cache = self.darwin("DARWIN_USER_CACHE_DIR")
        readable = None
        for base, _dirs, files in os.walk(cache):
            for name in sorted(files):
                candidate = os.path.join(base, name)
                try:
                    with open(candidate, "rb") as handle:
                        handle.read(1)
                except OSError:
                    continue
                readable = candidate
                break
            if readable:
                break
        if not readable:
            self.skipTest("no readable file in the darwin user cache to try")
        got = self.sandboxed(profile, [
            "/usr/bin/python3", "-c",
            "import sys\n"
            "try:\n"
            "    open(sys.argv[1], 'rb').read(1)\n"
            "    print('READ')\n"
            "except PermissionError:\n"
            "    print('REFUSED')\n", readable])
        self.assertIn("REFUSED", got.stdout, got.stdout + got.stderr)

    def test_the_temp_and_cache_directories_are_still_unlistable(self):
        """No `file-read-data` and no `file-read-metadata` rule was emitted, and none is
        needed: the cache file is created with the whole ancestor chain still denied, and a
        listing of either directory still raises. Measured, not assumed."""
        profile, _work = self.tool_profile()
        for name in ("DARWIN_USER_TEMP_DIR", "DARWIN_USER_CACHE_DIR"):
            got = self.sandboxed(profile, [
                "/usr/bin/python3", "-c",
                "import os, sys\n"
                "try:\n"
                "    print('ENTRIES', len(os.listdir(sys.argv[1])))\n"
                "except PermissionError:\n"
                "    print('REFUSED')\n", self.darwin(name)])
            self.assertEqual(got.stdout.strip(), "REFUSED",
                             "%s: %s" % (name, got.stdout + got.stderr))

    def test_a_spec_that_refuses_the_darwin_temp_dir_still_wins(self):
        """The allow is emitted BEFORE every refusal, so an explicit refusal overrides it."""
        writer = self.writer()
        temp = "/private/var/folders/aa/bbbbbbbb/T"
        rules = writer.build_rules({"label": "x", "read_roots": [], "write_roots": [],
                                    "refused_roots": [{"path": temp, "why": "a test"}]})["rules"]
        self.assertEqual(writer.evaluate(rules, writer.XCRUN_DB_SAMPLE, "file-read-data"),
                         "deny")
