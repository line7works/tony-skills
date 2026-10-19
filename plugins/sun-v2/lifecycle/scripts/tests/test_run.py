"""Group 3.1 of the frame: runs, the look, the plan and the owner's word (RUN-1 to RUN-13), on fakes.

Each test is named for the rule whose test line it answers. Where a branch comes from the
reviewer's D16 table (the brief's section 6) the test's name says D16. What RUN-2, RUN-12 and
RUN-13 say of a caught value is in `test_withheld_read.py` and `test_secrets_end_to_end.py`.
"""
import json
import os
import time
import unittest

import fab
import harness
import rowlib
from sun_core import cli, fsio, journal as journalmod, keys, texts
from sun_core.plan import RETIREMENT_PHASES as RETIREMENT


def stage_index(events, predicate):
    for event in events:
        if predicate(event):
            return event["i"]
    return None


class RunCase(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.m = self.machine()

    def clean(self, machine=None, **kw):
        m = machine or self.m
        rowlib.install(m, rowlib.clean_lane(**kw))
        m.put("shortcuts.txt", "alias other\n")
        m.put("dev/demo-scope.md", "scope\n")
        return m

    def effect_calls(self, machine=None):
        m = machine or self.m
        return [c for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold") for c in m.calls(tool) if c["changing"]]


class RUN1(RunCase):
    def test_RUN1_a_failed_gate_ends_refused_with_the_home_byte_equal_no_lock_and_no_cue(self):
        self.clean()
        cases = {"no vault": lambda: os.rename(self.m.vault, self.m.vault + ".gone"),
                 "a stub vault": lambda: os.remove(os.path.join(self.m.vault, harness.VAULT_MARKER)),
                 "D16: its marker but no projects directory": lambda: os.rmdir(os.path.join(self.m.vault, harness.VAULT_PROJECTS)),
                 "a vault inside a synced folder": None}
        wants = {"no vault": "vault-missing", "a stub vault": "vault-marker", "D16: its marker but no projects directory": "vault-projects",
                 "a vault inside a synced folder": "vault-synced"}
        for index, (label, damage) in enumerate(cases.items()):
            with self.subTest(vault=label):
                m = self.clean(harness.Machine(self.tmp, "home%d" % index, label))
                if damage is None:
                    synced = os.path.join(m.home, harness.SYNCED, "vault")
                    os.makedirs(os.path.dirname(synced))
                    os.rename(m.vault, synced)
                    m.settings["vault"]["path"] = synced
                    m.write_settings()
                else:
                    self.m = m
                    damage()
                before = m.snapshot()
                result = m.look()
                self.assertEqual((result.code, result.ending), (10, "refused"))
                self.assertEqual(result.lines, [texts.GATE[wants[label]]])
                self.assertEqual(m.snapshot(), before, "a failed gate changed the fixture home")
                self.assertEqual(m.lock_names(), [])
                self.assertEqual(m.cue_calls, [], "the cue came before the gate")

    def test_RUN1_on_a_sound_vault_the_steps_stand_in_their_order(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.create("C1")]))
        credentials = m.put("fakehost-credentials.json", json.dumps({"token": harness.canary("file-token")}), 0o600)
        m.settings["locations"]["fakehost_credentials"] = credentials
        m.write_settings()
        fab.keying(m)
        other = fab.open_run(m, "elsewhere")
        m.put("dev/second/names.txt", "second-site\n")
        result = m.look("second")
        self.assertEqual(result.ending, "preview", result.text)
        events = result.events
        facts = m.facts
        order = [
            ("the gate's withheld read", lambda e: e["stage"] == "read" and e["subject"] == facts.open_runs_file),
            ("the vault checks", lambda e: e["stage"] == "read" and e["subject"] == facts.settings_path),
            ("the name check's read of the token's channel", lambda e: e["stage"] == "read" and e["subject"] == credentials),
            ("the first locks", lambda e: e["op"] == "lock"),
            ("the alias reads", lambda e: e["stage"] == "read" and e["subject"].endswith(os.path.join("second", "names.txt")) and e["op"] == "read"),
            ("the run directory", lambda e: e["op"] == "mkdir" and e["subject"].startswith(facts.runs_root + os.sep)),
            ("the reads of the look", lambda e: e["op"] == "child"),
            ("the first byte of output", lambda e: e["stage"] == "output"),
        ]
        found = [(label, stage_index(events, predicate)) for label, predicate in order]
        for label, index in found:
            self.assertIsNotNone(index, "%s is not in the record" % label)
        self.assertEqual([i for _l, i in found], sorted(i for _l, i in found), found)
        locks = [e["i"] for e in events if e["op"] == "lock"]
        early = [e["i"] for e in events if e["stage"] == "read" and e["subject"] == facts.open_runs_file]
        alias = found[4][1]
        self.assertTrue(any(locks[0] < i < alias for i in early), "the early look for an open run does not stand between the first locks and the alias reads")
        self.assertTrue(any(i > alias for i in locks), "no later lock stands after the alias reads")
        self.assertTrue(any(i > max(locks) for i in early), "no second look for an open run stands after the later locks")
        self.assertEqual(m.cue_calls, ["sunrise"])

    def test_RUN1_a_close_records_no_runner_call_and_a_status_only_summons_no_planning_read(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.check("K1"), rowlib.owner_step("O1", mode="on his word")]))
        looked, went = m.started()
        self.assertEqual(went.ending, "waiting")
        status = m.summon("status")
        self.assertEqual([e for e in status.events if e["op"] == "child"], [], "a status-only summons made a planning read")
        closed = m.summon("close", "demo", "--word", "close")
        self.assertEqual([e for e in closed.events if e["op"] == "child"], [])


class RUN2(RunCase):
    def test_RUN2_two_spellings_of_one_name_meet_on_one_lock_with_no_probe_call(self):
        m = self.clean()
        fab.keying(m)
        self.assertEqual(keys.fold("Demo-App"), keys.fold("demo_app"))
        close = m.hold_lock("Demo-App", "sunrise-" + "0" * 16)
        try:
            second = m.look("demo_app")
        finally:
            close()
        self.assertEqual(second.ending, "refused")
        self.assertEqual(second.lines, [texts.LOCK_HELD + "sunrise-" + "0" * 16])
        self.assertEqual([e for e in second.events if e["op"] == "child"], [], "a probe call was made behind a held lock")
        after_lock = [e for e in second.events if e["i"] > stage_index(second.events, lambda e: e["op"] == "lock")]
        self.assertEqual([e for e in after_lock if e["stage"] == "read" and e["subject"] == m.facts.open_runs_file], [],
                         "a refusal at a first lock read the record of open runs after the gate's withheld read")
        self.assertEqual([e for e in second.events if e["stage"] == "read" and e["subject"].startswith(m.dev)], [], "it read a thing of the project")
        self.assertEqual(m.run_ids(), [])

    def test_RUN2_a_name_the_alias_reads_show_is_locked_too_in_sorted_order_and_a_held_later_lock_creates_nothing(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.check()]))
        fab.keying(m)
        m.put("dev/first/names.txt", "zeta-name\nalpha-name\n")
        close = m.hold_lock("alpha-name", "sunrise-" + "1" * 16)
        try:
            refused = m.look("first")
        finally:
            close()
        self.assertEqual(refused.lines, [texts.LOCK_HELD + "sunrise-" + "1" * 16])
        self.assertEqual(m.run_ids(), [], "a held lock on a later key left a run directory")
        self.assertEqual(m.lock_names(), [], "the locks taken before it were left behind")
        project_reads = [e["subject"] for e in refused.events if e["stage"] == "read" and e["subject"].startswith(m.dev)]
        self.assertEqual(set(os.path.basename(p) for p in project_reads), {"names.txt"}, "a refusal at a later lock read more of the project than the alias reads")
        went = m.look("first")
        self.assertEqual(went.ending, "preview", went.text)
        # each lock's file as it is asked for (its record is built whole beside it first, A41; that staged name is not a lock's)
        taken = [os.path.basename(e["subject"]) for e in went.events if e["op"] == "lock" and e["subject"].endswith(".lock")]
        later = [n for n in taken if n != m.fingerprint("first") + ".lock"]
        self.assertEqual(later, sorted(later), "the added keys were not taken in sorted order")
        self.assertEqual(set(later), {m.fingerprint("alpha-name") + ".lock", m.fingerprint("zeta-name") + ".lock"})
        run_dir_made = stage_index(went.events, lambda e: e["op"] == "mkdir" and e["subject"].startswith(m.facts.runs_root + os.sep))
        self.assertTrue(all(e["i"] < run_dir_made for e in went.events if e["op"] == "lock"), "a lock was taken after the run directory was made")

    def test_RUN2_a_name_only_a_provider_shows_ends_the_look_refused_with_the_name_in_a_private_file_and_no_lock_under_it(self):
        m = self.m
        row = rowlib.refusing("H1", name=rowlib.NAME)
        row["thing"]["name_form"] = {"command": "look", "field": "name"}
        rowlib.install(m, rowlib.lane("sunrise", [row]))
        other = "othername" + harness.canary("alias")[-6:]
        m.set_fake("fakehost", things={"demo": {"id": "x1", "kind": "repo", "state": "active", "name": "demo"}})
        m.plan_fake("fakehost", {"command": "get", "name_as": other})
        refused = m.look("demo")
        self.assertEqual(refused.ending, "refused", refused.text)
        self.assertNowhere(other, refused)
        self.assertIn("a provider shows the project under another name", refused.text)
        form = open(refused.doc["forms"][0]).read()
        self.assertNotIn(other, form)
        named = [w.rstrip(";") for line in refused.lines for w in line.split() if os.sep + "protected" + os.sep in w]
        self.assertEqual(open(named[0]).read(), other, "the private file does not hold the other name")
        self.assertEqual(m.lock_names(), [])
        self.assertNotIn(m.fingerprint(other), json.dumps(m.open_runs()))
        self.assertEqual([n for n in os.listdir(m.facts.run_dir(refused.doc["run"])) if n.startswith(("manifest", "journal"))], [])

    def test_RUN2_after_the_first_is_killed_a_third_takes_the_locks_and_goes_on(self):
        m = self.clean()
        looked = m.look()
        killed = m.go(looked, kill=lambda e: e["op"] == "journal" and e["stage"] == "post" and e["subject"] == "start")
        self.assertTrue(killed.killed)
        self.assertEqual(len(m.lock_names()), 1, "a killed holder's lock file should be left, unlocked")
        third = m.summon("status")
        self.assertEqual(third.ending, "stopped", third.text)
        self.assertEqual(m.lock_names(), [])

    def test_RUN2_A41_at_every_write_boundary_of_taking_taking_over_and_release_a_second_start_reads_no_file_the_old_record_or_the_new_whole(self):
        # RUN-2: "A lock's record is never at its place half written: whether the file is made or a left one is taken
        # over, another start reads no file, the record as it was, or the new record whole, so that the taking of a lock
        # is never a record that cannot be read (SEC-12)"; its test line: "At every write boundary of one invocation's
        # taking of a lock, of its taking over of a left file, and of its release, a second start's read of that lock's
        # record finds no file, the record as it was or the new record whole, and the second start never prints the
        # sentence for a record that cannot be read."
        from sun_core import locks as locksmod, withheld
        m = self.clean()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]))
        lock = m.facts.lock_file(m.fingerprint("demo")) if os.path.exists(m.facts.keying_file) else None
        seen, problems = [], []

        def second_start(event):
            if event["stage"] not in ("pre", "mid", "post") or not str(event["subject"]).startswith(m.facts.locks_dir):
                return False
            world = fab.quiet(m)
            view = withheld.read(world, m.facts)
            if view.unreadable:
                problems.append(("a second start would print the sentence", event["op"], event["stage"], event["subject"]))
            for name in m.lock_names():
                path = os.path.join(m.facts.locks_dir, name)
                try:
                    data = open(path, "rb").read()
                except FileNotFoundError:
                    continue
                found, run = locksmod.lock_record(world.fs, path)
                seen.append((event["op"], event["stage"], name, data))
                if found != "read":
                    problems.append(("half written", event["op"], event["stage"], name, data))
            return False

        # taking: the first look makes the keying value and the lock's file; release at its end
        looked = m.look(kill=second_start)
        self.assertEqual(looked.ending, "preview", looked.text)
        # taking over a left file: a killed holder's file, its record naming another run
        fab.stale_lock(m, "demo", m.next_id("sunrise"))
        self.assertEqual(len(m.lock_names()), 1)
        went = m.go(looked, kill=second_start)
        self.assertEqual(went.ending, "waiting", went.text)
        # a summons that continues the run, which rewrites its lock's record to the run it continues, and releases it
        status = m.summon("status", kill=second_start)
        self.assertEqual(status.ending, "waiting", status.text)
        self.assertTrue(seen, "no write boundary of a lock was met")
        self.assertEqual(problems, [])
        self.assertEqual(m.lock_names(), [])

    def test_RUN2_two_runs_of_different_projects_that_change_one_shared_file_both_land_their_change(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.swap_add("S1")]))
        m.put("shortcuts.txt", "alias other\n")
        for name in ("alpha", "beta"):
            looked, went = m.started(name)
            self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(open(m.path("shortcuts.txt")).read(), "alias other\nalias alpha\nalias beta\n")

    def test_RUN2_a_name_is_written_nowhere_but_as_a_fingerprint_and_two_machines_give_two(self):
        name = "Canary-" + harness.canary("name")
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]))
        looked, went = m.started(name)
        self.assertEqual(went.ending, "waiting")
        fab.stale_lock(m, name, looked.doc["run"])
        import base64, urllib.parse
        forms = []
        for value in (name, keys.fold(name)):
            forms += [value, urllib.parse.quote(value, safe=""), base64.b64encode(value.encode()).decode()]
        record = open(m.facts.open_runs_file).read()
        for lock in m.lock_names():
            body = open(os.path.join(m.facts.locks_dir, lock)).read()
            for form in forms:
                self.assertNotIn(form, lock)
                self.assertNotIn(form, body)
            self.assertEqual(sorted(json.loads(body)), ["fingerprint", "run"])
        for form in forms:
            self.assertNotIn(form, record)
        self.assertEqual(list(json.loads(record)["open"].values()), [looked.doc["run"]])
        other = harness.Machine(self.tmp, "second-machine", "b")
        fab.keying(other)
        self.assertNotEqual(m.fingerprint(name), other.fingerprint(name))

    FAKE_TOOLS = ("fakehost", "fakegit", "fakedump", "fakescaffold", "fakeadapter")

    def fakes_record(self, m):
        return dict((tool, m.calls(tool)) for tool in self.FAKE_TOOLS)

    def test_RUN2_A135_a_name_with_a_slash_or_dot_or_dotdot_or_dotdot_between_slashes_is_refused_at_a_and_one_with_none_is_accepted(self):
        """RUN-2's part (a): every name the summons carries "must also hold no slash, be neither "." nor "..", and hold no
        ".." as a part between slashes (the owner's ruling, A135). A name that fails is refused with the tool's fixed
        text: nothing of it is written, in any form, no lock is taken and nothing is created". Its test line: "a first
        look summoned with a name that holds a slash, and in further passes with the name ".", with the name ".." and
        with a name that holds ".." as a part between slashes, and a go summons and a summons with a further name each
        carrying one of them, each end refused with the tool's fixed text, no lock taken, nothing written in the fixture
        home and no call recorded by any fake, and a name that holds none of them is accepted (the owner's ruling,
        A135)". Each of the four is carried in each of four places: the first look's name, a further name of a first
        look, and a go summons's name and its further name (the look it answers made under a sound name)."""
        mark = harness.canary("a135")
        causes = (("a slash", mark + "/inside"), ("the name .", "."), ("the name ..", ".."),
                  ("'..' as a part between slashes", mark + "/../escape"))
        for index, (cause, bad) in enumerate(causes):
            for place in ("the first look's name", "a further name of a first look", "a go summons's name",
                          "a further name of a go summons"):
                with self.subTest(cause=cause, place=place):
                    m = self.clean(harness.Machine(self.tmp, "a135-%d-%s" % (index, place.replace(" ", "-").replace("'", "")),
                                                   "a135%d%s" % (index, place[:5])))
                    if place == "the first look's name":
                        summon = lambda: m.look(bad)
                    elif place == "a further name of a first look":
                        summon = lambda: m.look("demo", also=(bad,))
                    else:
                        looked = m.look("demo")
                        self.assertEqual(looked.ending, "preview", looked.text)
                        if place == "a go summons's name":
                            summon = lambda: m.go(looked, bad)
                        else:
                            summon = lambda: m.go(looked, "demo", also=(bad,))
                    before, fakes, runs = m.snapshot(), self.fakes_record(m), m.run_ids()
                    refused = summon()
                    self.assertEqual((refused.code, refused.ending, refused.lines), (10, "refused", [texts.NAME_REFUSED]),
                                     refused.text)
                    self.assertEqual([e for e in refused.events if e["op"] == "lock"], [], "a lock was taken")
                    self.assertEqual(m.lock_names(), [])
                    self.assertEqual(m.snapshot(), before, "a refused name wrote something in the fixture home")
                    self.assertEqual(m.run_ids(), runs)
                    self.assertEqual(self.fakes_record(m), fakes, "a fake recorded a call")
                    self.assertEqual([e for e in refused.events if e["op"] == "child"], [], "a child was started")
                    if mark in bad:
                        self.assertNowhere(mark, refused)
        # a name that holds none of them is accepted: dots that are not a whole part, and ".." inside a part
        for index, good in enumerate(("Tide.Table", "a..b", "demo.", ".demo")):
            for place in ("the first look's name", "a further name of a first look"):
                with self.subTest(accepted=good, place=place):
                    m = self.clean(harness.Machine(self.tmp, "a135-ok-%d-%s" % (index, place[:5].replace(" ", "-")),
                                                   "a135ok%d%s" % (index, place[:5])))
                    looked = m.look(good) if place == "the first look's name" else m.look("demo", also=(good,))
                    self.assertEqual(looked.ending, "preview", looked.text)

    def test_RUN2_PS47_a_name_with_no_letter_or_digit_a_leading_hyphen_a_backslash_a_control_a_line_break_or_an_invisible_mark_is_refused_at_a(self):
        """The owner's pick on PS47, as brief-26 quotes it: "Refuse those names too (Recommended)", the option: "These are
        refused: a name with no letter or digit, or one that starts with a hyphen; and a name holding a backslash, a
        control character, any line break or an invisible mark. The invisible marks are the zero-width and direction
        marks. Spaces stay allowed. Each is refused the way a name with a slash is: nothing written, no lock taken." So
        RUN-2's part (a) refuses each with the name check's existing fixed text, before any lock, as it refuses a slash
        (A135). "Any line break" includes the line and paragraph separators. The command line's own usage error for a name
        that folds to no key gives way to this refusal. Each cause is carried in each of four places: the first look's
        name, a further name of a first look, a go summons's name and its further name (the look it answers made under a
        sound name); each ends refused with the fixed text, no lock taken, nothing written in the fixture home, no call
        recorded by any fake and no child started. A name with a space, and a plain name, are accepted."""
        mark = harness.canary("ps47")
        causes = (
            ("no letter or digit: three dots", "..."), ("no letter or digit: marks and a space", "+_ -"),
            ("no letter or digit: one space", " "), ("no letter or digit: no character at all", ""),
            ("a leading hyphen", "-" + mark), ("two leading hyphens", "--" + mark), ("hyphens alone", "---"),
            ("a backslash", mark + "\\inside"), ("a backslash alone at the end", mark + "\\"),
            ("a control character", mark + "\x07"), ("a tab", mark + "\tx"), ("the delete character", mark + "\x7f"),
            ("a line feed", mark + "\nx"), ("a carriage return", mark + "\rx"), ("a vertical tab", mark + "\x0bx"),
            ("a form feed", mark + "\x0cx"), ("the next-line character", mark + "\x85x"),
            ("the line separator", mark + " x"), ("the paragraph separator", mark + " x"),
            ("a zero-width space", mark + "​x"), ("a zero-width joiner", mark + "‍x"),
            ("a word joiner", mark + "⁠x"), ("a zero-width no-break space", mark + "﻿x"),
            ("a left-to-right mark", mark + "‎x"), ("a right-to-left mark", mark + "‏x"),
            ("a right-to-left override", mark + "‮x"), ("a first-strong isolate", mark + "⁨x"),
        )
        for index, (cause, bad) in enumerate(causes):
            for place in ("the first look's name", "a further name of a first look", "a go summons's name",
                          "a further name of a go summons"):
                with self.subTest(cause=cause, place=place):
                    m = self.clean(harness.Machine(self.tmp, "ps47-%d-%s" % (index, place.replace(" ", "-").replace("'", "")),
                                                   "ps47%d%s" % (index, place[:5])))
                    if place == "the first look's name":
                        summon = lambda: m.look(bad)
                    elif place == "a further name of a first look":
                        summon = lambda: m.look("demo", also=(bad,))
                    else:
                        looked = m.look("demo")
                        self.assertEqual(looked.ending, "preview", looked.text)
                        if place == "a go summons's name":
                            summon = lambda: m.go(looked, bad)
                        else:
                            summon = lambda: m.go(looked, "demo", also=(bad,))
                    before, fakes, runs = m.snapshot(), self.fakes_record(m), m.run_ids()
                    refused = summon()
                    self.assertEqual((refused.code, refused.ending, refused.lines), (10, "refused", [texts.NAME_REFUSED]),
                                     refused.text)
                    self.assertEqual([e for e in refused.events if e["op"] == "lock"], [], "a lock was taken")
                    self.assertEqual(m.lock_names(), [])
                    self.assertEqual(m.snapshot(), before, "a refused name wrote something in the fixture home")
                    self.assertEqual(m.run_ids(), runs)
                    self.assertEqual(self.fakes_record(m), fakes, "a fake recorded a call")
                    self.assertEqual([e for e in refused.events if e["op"] == "child"], [], "a child was started")
                    if mark in bad:
                        self.assertNowhere(mark, refused)
        # accepted: a name with a space, a plain name, and a hyphen that does not lead
        for index, good in enumerate(("Tide Table", "tide", "tide-table", "Tide  Table 2")):
            for place in ("the first look's name", "a further name of a first look"):
                with self.subTest(accepted=good, place=place):
                    m = self.clean(harness.Machine(self.tmp, "ps47-ok-%d-%s" % (index, place[:5].replace(" ", "-")),
                                                   "ps47ok%d%s" % (index, place[:5])))
                    looked = m.look(good) if place == "the first look's name" else m.look("demo", also=(good,))
                    self.assertEqual(looked.ending, "preview", looked.text)

    def test_RUN2_PS47_through_the_shipped_start_a_name_of_hyphens_alone_meets_the_name_check_and_not_the_usage_error(self):
        """The command line's own usage error for a name that folds to no key gives way to RUN-2 (a)'s refusal (brief-26
        item 2): through the shipped entry point, a child process, "---" given to `--name` as its own argument ends with the
        name check's fixed text and exit 10, nothing on standard error; a missing value of `--name` is still a usage
        error."""
        m = self.clean()
        refused = m.run_child("resume", "--name", "---")
        self.assertEqual(refused.code, 10, refused.text)
        self.assertEqual(json.loads(refused.out)["lines"], [texts.NAME_REFUSED])
        self.assertEqual(refused.err, "")
        missing = m.run_child("resume", "--name")
        self.assertEqual((missing.code, missing.out, missing.err.strip()), (2, "", texts.USAGE))

    def test_RUN2_PS47_a_name_that_is_the_word_help_is_a_name_and_is_refused_and_help_after_a_name_is_still_help(self):
        """A name that starts with a hyphen is refused at RUN-2 (a) (PS47), "--help" and "-h" among them, as the word given
        to `--name` or `--also`: each ends with the name check's fixed text, no lock taken and nothing written; a summons
        that asks for help beside a sound name still prints the help."""
        for index, argv in enumerate((["look", "--kind", "sunrise", "--name", "--help"], ["status", "--name", "-h"],
                                      ["status", "--name", "demo", "--also", "--help"])):
            with self.subTest(argv=argv):
                m = self.clean(harness.Machine(self.tmp, "ps47-help-%d" % index, "ps47h%d" % index))
                if argv[0] == "look":
                    argv = argv + ["--inputs", m.inputs()]
                before = m.snapshot()
                refused = m.run(*argv)
                self.assertEqual((refused.code, refused.ending, refused.lines), (10, "refused", [texts.NAME_REFUSED]), refused.text)
                self.assertEqual([e for e in refused.events if e["op"] == "lock"], [], "a lock was taken")
                self.assertEqual(m.snapshot(), before)
        m = self.clean(harness.Machine(self.tmp, "ps47-help-ok", "ps47hok"))
        for argv in (["look", "--name", "demo", "--help"], ["status", "-h", "--name", "demo"]):
            with self.subTest(help=argv):
                asked = m.run(*argv)
                self.assertEqual((asked.code, asked.out), (0, cli.HELP.rstrip("\n") + "\n"), asked.text)

    def test_RUN2_the_keying_values_file_missing_or_wide_fails_the_gate_and_the_ways_on_are_his(self):
        m = self.clean()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]))
        looked, went = m.started()
        run = looked.doc["run"]
        saved = open(m.facts.keying_file).read()
        os.remove(m.facts.keying_file)
        refused = m.look("another")
        self.assertEqual(refused.lines, [texts.GATE["keying-missing"], texts.KEYING_PLACE + m.facts.keying_file, texts.RUN_ON_RECORD + run]
                         + list(texts.WAYS_ON))      # A43: the three ways on after the listing
        self.assertFalse(os.path.exists(m.facts.keying_file), "the tool made a new value while a run was on record")
        with open(m.facts.keying_file, "w") as fh:
            fh.write(saved)
        os.chmod(m.facts.keying_file, 0o600)
        self.assertEqual(m.summon("status").ending, "waiting", "with the file put back the next summons did not pass the gate")
        os.chmod(m.facts.keying_file, 0o644)
        wide = m.summon("status")
        self.assertEqual(wide.lines[0], texts.GATE["keying-wide"])
        os.chmod(m.facts.keying_file, 0o600)
        self.assertEqual(m.summon("status").ending, "waiting")
        # the one way left where he has no copy: he removes the lock files and the record himself
        os.remove(m.facts.keying_file)
        os.remove(m.facts.open_runs_file)
        fresh = m.look("another")
        self.assertEqual(fresh.ending, "preview", fresh.text)
        self.assertNotEqual(open(m.facts.keying_file).read(), saved, "no new value was made")
        self.assertEqual(m.summon("status").lines, [texts.NOTHING_TO_RESUME], "the tool still sees a run it can no longer tie to a lock")


    def test_RUN2_A56_a_record_of_open_runs_that_holds_no_run_with_the_keying_file_removed_stops_the_gate_listing_no_run(self):
        """RUN-2's test line (the owner's ruling A56): "A record of open runs that holds no run: a fixture run has its go and
        ends `complete`, so that the record of open runs is there, holds no run, and no lock file is left; the keying
        value's file is then removed. The next summons fails the gate, its output being fixed text that names the missing
        file and its place, lists no run, and gives the three sentences of the ways on; no new value is made, and the
        fixture home is byte-equal after it." """
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.check("K1")]))
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        self.assertTrue(os.path.exists(m.facts.open_runs_file), "the record of open runs is not there")
        self.assertEqual(m.open_runs(), {}, "the record of open runs holds a run")
        self.assertEqual(m.lock_names(), [], "a lock file is left")
        os.remove(m.facts.keying_file)
        before = m.snapshot()
        refused = m.look("another")
        self.assertEqual(refused.ending, "refused", refused.text)
        self.assertEqual(refused.lines, [texts.GATE["keying-missing"], texts.KEYING_PLACE + m.facts.keying_file] + list(texts.WAYS_ON))
        self.assertFalse([l for l in refused.lines if l.startswith((texts.RUN_ON_RECORD, texts.RUN_ON_RECORD_UNNAMED))], "a run is listed")
        self.assertFalse(os.path.exists(m.facts.keying_file), "a new value was made")
        self.assertEqual(m.snapshot(), before, "the fixture home changed")

    def test_RUN2_LOG3_Q18_two_starts_that_find_no_file_at_a_locks_place_at_once_one_holds_it_and_the_other_leaves_nothing(self):
        """RUN-2 (batch 20): "Where the record is built beside the place and put there whole, and two starts find no file at
        once, the start whose record meets the other's file at the place has met a held lock: it removes the record it
        built, which never became a lock's file (LOG-3), and ends as at a held lock." Its test line: "Two starts that find
        no file at a lock's place at once: one holds the lock; the other ends at the held lock, the record it built is
        removed, and no file of its making is left in the tool's folder." LOG-3 names that removal (report-5's question 18,
        settled in the frame as built). The other start is planted at the instant between this start's finding no file and
        its rename into the place."""
        m = self.clean()
        fab.keying(m)
        place = m.facts.lock_file(m.fingerprint("demo"))
        other = "sunrise-0000000000000other"
        holder = {}

        def plant(event):
            if not holder and event["stage"] == "pre" and event["op"] == "rename" and event["subject"] == place:
                holder["close"] = m.hold_lock("demo", other)       # the other start's file takes the place, held
            return False
        refused = m.look(kill=plant)
        self.assertTrue(holder, "the race was not reached")
        self.assertEqual(refused.ending, "refused", refused.text)
        # it ends as at a held lock; the holder came after its withheld read, so that run was never read and its id is not
        # printed (SEC-12: "A run's id is printed only where the disproof records of that run were read whole")
        self.assertEqual(refused.lines, [texts.LOCK_HELD + texts.WITHHELD])
        staged = place + ".taking"
        self.assertFalse(os.path.exists(staged), "the record it built is left")
        removed = [e for e in refused.events if e["stage"] == "pre" and e["op"] in ("remove", "unlock-remove") and e["subject"] == staged]
        self.assertEqual(len(removed), 1, "the record it built was not removed by it")
        self.assertEqual(sorted(os.listdir(m.facts.locks_dir)), [os.path.basename(place)], "a file of its making is left in the tool's folder")
        self.assertEqual(json.load(open(place))["run"], other, "the holder's record was changed")
        holder["close"]()
        self.assertEqual(os.listdir(m.facts.locks_dir), [])


class RUN3(RunCase):
    def waiting_under_two_keys(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]),
                       rowlib.lane("sunset", [rowlib.check("K1")], phases=["keeping", "retiring on this machine", "retiring at the providers", "the last record"]))
        m.put("dev/demo/names.txt", "demo-site\n")
        looked, went = m.started()
        self.assertEqual(went.ending, "waiting", went.text)
        self.assertEqual(sorted(m.open_runs()), sorted([m.fingerprint("demo"), m.fingerprint("demo-site")]))
        return looked.doc["run"]

    def test_RUN3_a_new_summons_is_refused_at_the_early_look_and_at_the_second_naming_the_open_run_having_made_nothing(self):
        run = self.waiting_under_two_keys()
        m = self.m
        m.put("dev/third/names.txt", "demo\n")
        for name, look in (("demo", "early"), ("demo-site", "early"), ("third", "second")):
            with self.subTest(name=name):
                before = m.snapshot()
                refused = m.look(name, "sunset")
                self.assertEqual(refused.lines, [texts.RUN_OPEN + run, texts.RUN_OPEN_WAYS])
                self.assertEqual(refused.ending, "refused")
                self.assertEqual([e for e in refused.events if e["op"] == "child"], [], "it read a provider")
                project = set(os.path.relpath(e["subject"], m.dev) for e in refused.events if e["stage"] == "read" and e["subject"].startswith(m.dev + os.sep))
                self.assertEqual(project, set() if look == "early" else {os.path.join("third", "names.txt")})
                self.assertEqual(m.snapshot(), before, "a refused summons made a file or a folder")

    def test_RUN3_A42_a_restore_while_that_sunrise_is_open_is_refused_at_the_early_look_as_the_sunset_is(self):
        """RUN-3's test line: "a restore summoned under either of those two names while that sunrise is open is refused at
        the early look as the sunset is, with the open run named as the withheld read lets it be and with no file and no
        folder left (the owner's ruling, A42)"; brief-2 section 7 item 7: "'refused at the early look as the sunset is'
        means as a sunset summoned there is refused"."""
        run = self.waiting_under_two_keys()
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]), rowlib.lane("restore", [], phases=["back"]))
        for name in ("demo", "demo-site"):
            for kind in ("sunset", "restore"):
                with self.subTest(name=name, kind=kind):
                    before = m.snapshot()
                    refused = m.look(name, kind)
                    self.assertEqual((refused.ending, refused.lines), ("refused", [texts.RUN_OPEN + run, texts.RUN_OPEN_WAYS]))
                    self.assertEqual([e for e in refused.events if e["op"] == "child"], [], "it read a provider")
                    self.assertEqual([e for e in refused.events if e["stage"] == "read" and e["subject"].startswith(m.dev + os.sep)], [],
                                     "it read a thing of the project")
                    self.assertEqual(m.snapshot(), before, "a refused summons made a file or a folder")

    def test_RUN3_a_kill_between_the_go_and_the_opening_record_leaves_the_run_open_under_all_keys_or_none(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]))
        m.put("dev/demo/names.txt", "demo-site\n")
        looked = m.look()
        index = 0
        while True:
            fresh = harness.Machine(self.tmp, "kill%d" % index, "k%d" % index)
            rowlib.install(fresh, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]))
            fresh.put("dev/demo/names.txt", "demo-site\n")
            seen = fresh.look()
            count = {"n": -1}

            def at(event, want=index, count=count):
                if event["stage"] in ("pre", "mid", "post"):
                    count["n"] += 1
                    return count["n"] == want
                return False
            went = fresh.go(seen, kill=at)
            if not went.killed:
                break
            self.assertIn(len(fresh.open_runs()), (0, 2), "the run is open under one of its two keys (kill point %d)" % index)
            index += 1
        self.assertGreater(index, 10)

    def test_RUN3_a_resume_a_replan_and_a_close_of_the_open_run_are_each_accepted(self):
        run = self.waiting_under_two_keys()
        m = self.m
        self.assertEqual(m.summon("status").ending, "waiting")
        self.assertEqual(m.resume().ending, "waiting")
        replanned = m.summon("replan", "demo", "--inputs", m.inputs())
        self.assertIn("manifest_sha256", replanned.doc, replanned.text)
        self.assertEqual(m.summon("close", "demo-site", "--word", "close").ending, "closed")


class RUN4(RunCase):
    def stopped_run(self):
        m = self.clean()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word"), rowlib.check("K1", needs=[
            {"output": "connected", "level": "state", "accepts": ["his word"], "treatment": "then not applicable"}])]))
        looked, went = m.started()
        return looked.doc["run"]

    def test_RUN4_wider_permissions_or_a_changed_byte_stop_the_next_invocation_before_it_reads_a_thing_of_the_project(self):
        run = self.stopped_run()
        m = self.m
        journal = os.path.join(m.facts.run_dir(run), "journal.jsonl")
        self.assertEqual(m.summon("status").ending, "waiting", "with the run directory untouched the second invocation did not go on")
        os.chmod(journal, 0o644)
        wide = m.summon("status")
        self.assertEqual((wide.ending, wide.lines[0]), ("stopped", texts.RUNDIR_STOP["permissions"]))
        self.assertEqual([e for e in wide.events if e["op"] == "child" or (e["stage"] == "read" and e["subject"].startswith(m.dev))], [])
        os.chmod(journal, 0o600)
        data = open(journal, "rb").read()
        middle = data.index(b"\n") + 40
        with open(journal, "wb") as fh:
            fh.write(data[:middle] + bytes([data[middle] ^ 1]) + data[middle + 1:])
        os.chmod(journal, 0o600)
        broken = m.summon("status")
        self.assertEqual((broken.ending, broken.lines[0]), ("stopped", texts.RUNDIR_STOP["chain"]))
        self.assertEqual([e for e in broken.events if e["op"] == "child"], [])
        self.assertEqual(broken.doc.get("forms"), None, "a status form was rendered from records that failed their check")

    def test_RUN4_D16_a_cut_off_last_record_is_discarded_and_a_malformed_whole_last_record_stops(self):
        run = self.stopped_run()
        m = self.m
        journal = os.path.join(m.facts.run_dir(run), "journal.jsonl")
        data = open(journal, "rb").read()
        whole = len(m.journal(run))
        with open(journal, "ab") as fh:
            fh.write(b'{"n": %d, "kind": "status", "cut off in the mid' % whole)
        os.chmod(journal, 0o600)
        cut = m.summon("status")
        self.assertEqual(cut.ending, "waiting", cut.text)
        self.assertEqual(cut.doc["position"], whole, "a cut-off last record was counted")
        with open(journal, "wb") as fh:
            fh.write(data + b'{"n": %d, "kind": "status", "op": "O1", "status": "left"}\n' % whole)
        os.chmod(journal, 0o600)
        malformed = m.summon("status")
        self.assertEqual((malformed.ending, malformed.lines[0]), ("stopped", texts.RUNDIR_STOP["chain"]),
                         "a malformed whole last record was discarded as if it were cut off")


class RUN5to8(RunCase):
    def test_RUN5_the_look_only_reads_and_reads_the_identities_the_capabilities_and_the_keys_earlier_journals(self):
        m = self.clean()
        earlier = m.started()[0].doc["run"]
        m.summon("close", "demo", "--word", "close")
        for stale in ("dev/demo", "dev/demo-scope-moved.md"):
            pass
        m2 = self.clean(harness.Machine(self.tmp, "second", "s"))
        first = m2.started()
        m2.summon("close", "demo", "--word", "close")
        earlier = first[0].doc["run"]
        import shutil
        shutil.rmtree(os.path.join(m2.dev, "demo"))
        m2.put("shortcuts.txt", "alias other\n")
        m2.put("dev/demo-scope.md", "scope\n")
        m2.set_fake("fakehost", things={})
        m2.set_fake("fakegit", refs={})
        fakes_before = dict((tool, json.dumps(m2.fake(tool, "state.json"), sort_keys=True)) for tool in ("fakehost", "fakegit"))
        outside_before = dict((k, v) for k, v in m2.snapshot().items() if not k.startswith((".sun-v2", ".fakes")))
        calls_before = len(self.effect_calls(m2))
        looked = m2.look(caps=["canary"])
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(len(self.effect_calls(m2)), calls_before, "a look made a state-changing call")
        self.assertTrue(m2.calls("fakehost", "whoami"), "the look made no identity read")
        reads = [e["subject"] for e in looked.events if e["stage"] == "read"]
        self.assertIn(m2.capabilities(["canary"]), reads, "the adapter's capability declaration was not read")
        self.assertIn(os.path.join(m2.facts.run_dir(earlier), "journal.jsonl"), reads, "the key's earlier journal was not read")
        self.assertEqual(dict((tool, json.dumps(m2.fake(tool, "state.json"), sort_keys=True)) for tool in ("fakehost", "fakegit")), fakes_before)
        self.assertEqual(dict((k, v) for k, v in m2.snapshot().items() if not k.startswith((".sun-v2", ".fakes"))), outside_before)

    def test_RUN5_a_look_with_an_unanswered_question_ends_with_the_question_listed_and_no_manifest(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.check()], questions=[{"question": "One line: what is it?", "input": "description", "required": True}]))
        asked = m.look(inputs=m.inputs(description=""))
        self.assertEqual(asked.ending, "refused")
        self.assertEqual(asked.lines, [texts.QUESTIONS, "One line: what is it?"])
        self.assertEqual([n for n in os.listdir(m.facts.run_dir(asked.doc["run"])) if n.startswith("manifest")], [])

    def test_RUN6_the_look_reads_nothing_a_planned_operation_would_make_and_dependents_hold_references(self):
        m = self.clean()
        looked = m.look()
        project = os.path.join(m.dev, "demo")
        inside = [e["subject"] for e in looked.events if e["stage"] == "read" and e["subject"].startswith(project + os.sep)
                  and not e["subject"].endswith(os.sep + "names.txt")]       # the lane's declared alias read (RUN-2, part d)
        self.assertEqual(inside, [], "the look read a path that only a planned operation would make")
        manifest = json.load(open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")))
        by_id = dict((o["id"], o) for o in manifest["operations"])
        self.assertEqual(by_id["H1"]["commands"][0]["params"]["name"], {"output": "remote.name"})
        self.assertNotIn("tracked_state", by_id["H1"])
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        gets = [c for c in m.calls("fakehost", "get") if "--name" in c["argv"]]
        self.assertTrue(gets, "the dependent's probe did not read the produced thing")

    def test_RUN6_a_produced_thing_that_is_not_in_the_dependents_before_state_stops_at_that_probe(self):
        m = self.clean()
        looked = m.look()
        state = m.fake("fakehost", "state.json") or {}
        went = m.go(looked, kill=lambda e: e["op"] == "journal" and e["stage"] == "post" and e["subject"] == "completion" and e.get("operation") == "G1")
        self.assertTrue(went.killed)
        things = m.fake("fakehost", "state.json")["things"]
        things["demo"]["state"] = "archived"
        m.set_fake("fakehost", things=things)
        resumed = m.resume()
        self.assertEqual(resumed.ending, "stopped", resumed.text)
        self.assertIn("stopped: foreign", resumed.lines)
        self.assertIn("operation: H1", resumed.lines)
        self.assertEqual([c for c in m.calls("fakehost", "set")], [], "the effect was applied to a thing not in its before-state")

    def test_RUN6_on_a_sunset_the_operations_on_files_inside_a_folder_to_be_moved_are_planned_from_their_present_paths_and_probed_at_the_moved_path(self):
        """RUN-6: "A thing that lies inside a thing another operation moves is named relative to that operation's output: the
        look reads it where it is, and the probe reads it where the move's record says it went." Its test line: "on a sunset
        fixture the operations on files inside a folder to be moved are planned from their present paths and probed at the
        moved path". The fixture: a sunset moves the folder dev/demo to the archive (C7), and then changes dev/demo/notes.txt,
        a line taken out (C3), its row naming the file by the move's output; a second fixture whose file is not in the
        change's before-state at the look ends the look as RUN-7's planning stop, read where it is."""
        from sun_core.plan import RETIREMENT_PHASES as P
        folder, moved = rowlib.path(rowlib.DEV, rowlib.NAME), rowlib.path({"location": "archive_root"}, rowlib.NAME)
        mover = rowlib.move("MV", P[1], source=folder, target=moved, output="archived")
        mover["thing"].update({"role": "the project folder"})
        mover["planning_test"] = [{"read": "path", "path": folder, "is": "dir"}]
        mover["before_test"] = [{"id": "there", "read": "path", "path": folder, "is": "dir"},
                                {"id": "free", "read": "path", "path": moved, "is": "absent"}]
        mover["after_test"] = [{"read": "path", "path": folder, "is": "absent"}, {"read": "path", "path": moved, "is": "dir"}]
        mover["after_check"] = [{"read": "path", "path": moved, "is": "dir"}]
        mover["way_back"] = {"none": "the row declares none"}
        mover["reverse_inputs"] = rowlib.NONE
        notes = {"path": [{"output": "archived.path"}, rowlib.lit("notes.txt")]}      # named relative to the move's output
        line = rowlib.lit("status: live")
        change = rowlib.row("change", "CN", P[1],
                            thing={"role": "the project's notes", "identity": "path", "place": notes, "tracked": ["exists", "sha256"]},
                            planning_test=[{"read": "path", "path": notes, "is": "file"}],
                            before_test=[{"id": "has", "read": "line", "path": notes, "line": line, "count": 1}],
                            after_test=[{"read": "line", "path": notes, "line": line, "present": False}],
                            construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "remove-line", "line": line}},
                            after_check=[{"read": "line", "path": notes, "line": line, "present": False}],
                            way_back={"none": "the row declares none"},
                            needs=[{"output": "archived", "level": "made", "treatment": "then not applicable"}],
                            output={"name": "notes changed", "fields": {}})
        for index, (case, text) in enumerate((("in its before-state", "a note\nstatus: live\n"), ("in neither state the row names", "a note\nstatus: live\nstatus: live\n"))):
            with self.subTest(file=case):
                m = harness.Machine(self.tmp, "mv%d" % index, "mv%d" % index)
                rowlib.install(m, rowlib.lane("sunset", [mover, change], phases=P), rowlib.lane("restore", [], phases=("putting back",)))
                m.put("dev/demo/notes.txt", text)
                os.makedirs(m.archive, exist_ok=True)
                present = os.path.join(m.dev, "demo", "notes.txt")
                at_moved = os.path.join(m.archive, "demo", "notes.txt")
                looked = m.look(kind="sunset")
                read_present = [e for e in looked.events if e["stage"] == "read" and e["subject"] == present]
                read_moved = [e for e in looked.events if e["stage"] == "read" and str(e["subject"]).startswith(os.path.join(m.archive, "demo") + os.sep)]
                self.assertEqual(read_moved, [], "the look read the moved path")
                self.assertTrue(read_present, "the look did not read the file where it is: " + looked.text)
                if case == "in neither state the row names":
                    self.assertEqual(looked.ending, "refused", looked.text)
                    self.assertIn("the thing is in neither state the row names: row CN", looked.lines)
                    continue
                self.assertEqual(looked.ending, "preview", looked.text)
                manifest = json.load(open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")))
                by_id = dict((o["id"], o) for o in manifest["operations"])
                self.assertEqual(by_id["CN"]["thing"]["place"], notes, "the manifest does not hold the reference")
                self.assertEqual(by_id["CN"]["planning_outcome"], "in")
                self.assertEqual(by_id["CN"]["tracked_state"].get("path"), present, "the state recorded at the look is not the present one")
                went = m.go(looked, kind="sunset")
                self.assertEqual(went.ending, "complete", went.text + open(went.doc["forms"][0]).read())
                renamed = stage_index(went.events, lambda e: e["op"] == "rename" and e["stage"] == "post")
                probed = [e for e in went.events if e["stage"] == "read" and e["subject"] == at_moved and e["i"] > renamed]
                self.assertTrue(probed, "the probe did not read the file at the moved path")
                self.assertEqual([e for e in went.events if e["stage"] == "read" and e["subject"] == present and e["i"] > renamed], [],
                                 "the probe read the file at its old path")
                self.assertEqual(open(at_moved).read(), "a note\n", "the change did not land at the moved path")

    def test_RUN7_on_a_clear_fixture_every_candidate_is_in_and_each_never_clobber_condition_ends_the_look_named(self):
        m = self.clean()
        clear = m.look()
        self.assertEqual(clear.ending, "preview")
        manifest = json.load(open(os.path.join(m.facts.run_dir(clear.doc["run"]), "manifest-1.json")))
        self.assertEqual([o["planning_outcome"] for o in manifest["operations"]], ["in"] * 8)
        conditions = {
            "an existing folder": (lambda mm: os.makedirs(os.path.join(mm.dev, "demo")), "the place is taken by a thing this run did not make: row B1"),
            "an existing remote of that name at the host": (lambda mm: mm.set_fake("fakehost", things={"demo": {"id": "old", "kind": "repo", "state": "active", "name": "demo"}}),
                                                             "the place is taken by a thing this run did not make: row C1"),
            # RUN-7 (batch 23): "a shortcut whose name a program, an alias, a shell function, a builtin or a reserved word
            # already has, as the fixture's login zsh finds them" (A55, A63): the fake zsh of the fixture's system folder runs
            # the tool's line over his login and interactive files; the builtin and the reserved word, and the names zsh
            # would run first as another command, are planted in test_sec3_runner.TheShortcutCheck.test_RUN7_A63_...
            "a shortcut whose name a program on his login path has": (
                lambda mm: (mm.put("opt/pm/bin/demo", "#!/bin/sh\n", 0o755), mm.put(".zprofile", "path+=(%s)\n" % mm.path("opt", "pm", "bin"))),
                texts.SHORTCUT_NAME_TAKEN.format(row="S1")),
            "a shortcut whose name an alias has": (lambda mm: mm.put(".zshrc", "alias demo=ls\n"), texts.SHORTCUT_NAME_TAKEN.format(row="S1")),
            "a shortcut whose name a shell function has": (lambda mm: mm.put(".zshrc", "demo() { ls }\n"), texts.SHORTCUT_NAME_TAKEN.format(row="S1")),
        }
        for index, (label, (plant, cause)) in enumerate(conditions.items()):
            with self.subTest(planted=label):
                mm = self.clean(harness.Machine(self.tmp, "nc%d" % index, label))
                plant(mm)
                stopped = mm.look()
                self.assertEqual(stopped.ending, "refused", stopped.text)
                self.assertIn(cause, stopped.lines)
                self.assertEqual([n for n in os.listdir(mm.facts.run_dir(stopped.doc["run"])) if n.startswith("manifest")], [])

    def test_RUN7_a_failed_a_partial_a_wrong_account_and_a_timed_out_read_each_end_the_look_named(self):
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["get"]["exits"].update({"5": "other", "7": "auth"})
        providers["fakehost"]["commands"]["get"]["time_limit"] = 1
        plans = {"the read failed": {"command": "get", "do": "fail", "exit": 5},
                 "the read was partial": {"command": "get", "do": "raw", "text": '{"state": "act'},
                 "the read was made as the wrong account": {"command": "get", "do": "fail", "exit": 7},
                 "the read ran out of time": {"command": "get", "do": "hang"}}
        for index, (cause, plan) in enumerate(plans.items()):
            with self.subTest(cause=cause):
                m = harness.Machine(self.tmp, "rd%d" % index, cause)
                rowlib.install(m, rowlib.lane("sunrise", [rowlib.create("C1")]), providers=providers)
                m.plan_fake("fakehost", plan)

                # the join's J2b (the class of J1b item 6): the read's one-second limit counts from the runner's `mid child`
                # event (the child started); under load the fake's own first act, its call record, came 1.6 to 2.7 s after
                # it, and the limit ended a child that was about to answer. The limit is made to fall where the test means it,
                # after the fake has started and recorded its call, by that event: at `mid child`, before the limit counts,
                # wait (60 s at most) for this child's own record (one more than at its `pre child` event: the look's
                # identity read is a child of the fake too). Its rule, each cause ending the look named, is unchanged
                def started(e, m=m, seen={}):
                    if e["op"] == "child" and e["subject"] == "fakehost" and e["stage"] == "pre":
                        seen["before"] = len(m.calls("fakehost"))
                    if e["op"] == "child" and e["stage"] == "mid" and e.get("started") and e["subject"] == "fakehost":
                        until = time.time() + 60
                        while len(m.calls("fakehost")) <= seen.get("before", 0) and time.time() < until:
                            time.sleep(0.01)
                    return False
                stopped = m.look(kill=started)
                self.assertEqual(stopped.ending, "refused", stopped.text)
                self.assertTrue(any(line.startswith(cause) for line in stopped.lines), stopped.lines)
        m = harness.Machine(self.tmp, "acct", "acct")
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.create("C1")]))
        reported = "someone" + harness.canary("account")[-8:]
        m.set_fake("fakehost", account=reported)
        wrong = m.look()
        self.assertEqual(wrong.ending, "refused")
        self.assertTrue(any(line.startswith("the read was made as the wrong account") for line in wrong.lines), wrong.lines)
        self.assertNowhere(reported, wrong)

    def test_RUN7_D16_already_so_a_flag_a_dropped_layer_and_an_absent_capability_each_plan_without_stopping(self):
        m = self.m
        m.put("dev/demo-scope-moved.md", "scope\n")
        flagged = rowlib.check("K9", condition={"on": "fact", "fact": "flags.database", "equals": True, "reason": "a flag"})
        layered = rowlib.check("K8")
        layered["thing"]["layer"] = "hosting"
        capable = rowlib.owner_step("O9", mode="on his word")
        capable["thing"]["capability"] = "routines"
        checked = rowlib.check("K7")
        checked["thing"]["capability"] = "canary"
        retired = rowlib.refusing("H1")
        m.set_fake("fakehost", things={"demo": {"id": "x1", "kind": "db", "state": "paused", "name": "demo"}})
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.move("M1"), flagged, layered, capable, checked, retired]))
        looked = m.look(inputs=m.inputs(flags={"database": False}, drop_layers=["hosting"]), caps=[])
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = json.load(open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")))
        self.assertEqual([o["id"] for o in manifest["operations"]], ["K7"])
        self.assertEqual(sorted((n["row"], n["reason"]) for n in manifest["not_applicable"]),
                         [("K8", "a layer the project lacks"), ("K9", "a flag"), ("O9", "not available on this harness")])
        self.assertEqual(sorted(a["row"] for a in manifest["already_so"]), ["H1", "M1"])
        preview = open(looked.doc["forms"][0]).read()
        self.assertEqual(preview.count("found already so; a restore will not reverse it"), 2)
        self.assertIn("the check could not be made on this harness", preview)
        went = m.go(looked, caps=[])
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"]), {"K7": "unavailable"})
        self.assertIn("the check could not be made on this harness", open(went.doc["forms"][0]).read())
        self.assertEqual(self.effect_calls(), [])

    def test_RUN8_the_preview_is_the_manifest_rendered_twice_byte_equal_with_every_fake_removed(self):
        from sun_core import forms, manifest as manifestmod
        m = self.clean()
        looked = m.look()
        shown = open(looked.doc["forms"][0]).read()
        import shutil
        shutil.rmtree(harness.FAKES + "-nowhere", True)
        m.env["PATH"] = "/nonexistent"
        doc, _sha = manifestmod.load(fsio.FS(), m.facts.run_dir(looked.doc["run"]), 1)
        first = "\n".join(forms.preview_lines(doc)) + "\n"
        second = "\n".join(forms.preview_lines(json.loads(json.dumps(doc)))) + "\n"
        self.assertEqual(first, second)
        self.assertEqual(first, shown)
        for entry in manifestmod.ENTRIES:
            broken = dict(doc)
            del broken[entry]
            with self.assertRaises(manifestmod.Invalid, msg=entry):
                manifestmod.validate(broken)
        manifestmod.validate(doc)


class EarlierRuns(RunCase):
    """RUN-5's paragraph on how the look finds the key's earlier runs (batches 20C and 20D; the owner's ruling A57) and
    its test line, with RUN-7's (a planning stop for a first record that cannot be read and for a folder of run
    directories that cannot be listed), SEC-12's "Another run's journal" and EV-7's "The sunset it finds". RUN-5: "To
    find them the look reads that record in every run directory, and nothing else of a run it has not found. It uses that
    record for one thing: to compare each fingerprint it holds with the fingerprints the invocation made itself ... A
    directory with no journal, or whose journal holds only a cut-off record (LOG-1), is of a run that had no go (RUN-12)
    and is no earlier run. Where the look cannot tell, it stops and tells (the owner's ruling, A57)."

    The fake file system's record is the measure: a `read-first-record` act is the read of a journal's first record, and
    of nothing after its newline; a `read` act of a journal is a read of the whole of it; a `walk` is RUN-4's check."""

    LANES = staticmethod(lambda: (rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]),
                                  rowlib.lane("sunset", [rowlib.owner_step("O1", "keeping", mode="on his word")], phases=RETIREMENT),
                                  rowlib.lane("restore", [rowlib.check("K1", "only")], phases=("only",))))

    def closed_run(self, m, name, kind="sunrise", names=None):
        if names is not None:
            m.put(os.path.join("dev", name, "names.txt"), names + "\n")
        looked, went = m.started(name, kind)
        self.assertEqual(went.ending, "waiting", went.text)
        closed = m.summon("close", name, "--word", "close")
        self.assertEqual(closed.ending, "closed", closed.text)
        if names is not None:
            os.remove(m.path("dev", name, "names.txt"))
        return looked.doc["run"]

    def three(self, m=None):
        """Three closed runs: two opened under the key of `demo`, the second of them also under the key of `demo-site`,
        which only its alias reads showed; a third under the key of `other`."""
        m = m or self.m
        rowlib.install(m, *self.LANES())
        first = self.closed_run(m, "demo")
        second = self.closed_run(m, "demo", names="demo-site")
        third = self.closed_run(m, "other")
        self.assertEqual(sorted(m.journal(second)[0]["keys"]), sorted([m.fingerprint("demo"), m.fingerprint("demo-site")]))
        self.three_ids = (first, second, third)
        return first, second, third

    def acts_in(self, m, result, run_id):
        """{op: [paths]} of every read act of that run directory, and in it, made by the look: from the look's making of its
        own run directory on (RUN-1's third step), so that the gate's withheld read of a run on record is not counted."""
        run_dir = m.facts.run_dir(run_id)
        made = [e["i"] for e in result.events if e["op"] == "mkdir" and str(e["subject"]).startswith(m.facts.runs_root + os.sep)
                and os.path.dirname(e["subject"]) == m.facts.runs_root]
        start = made[0] if made else 0
        out = {}
        for e in result.events:
            subject = str(e["subject"])
            if e["i"] >= start and e["stage"] == "read" and (subject == run_dir or subject.startswith(run_dir + os.sep)):
                out.setdefault(e["op"], []).append(os.path.relpath(subject, run_dir))
        return out

    def read_whole(self, m, result):
        """The run directories whose journal the look read whole."""
        return sorted(r for r in m.run_ids() if "journal.jsonl" in self.acts_in(m, result, r).get("read", []))

    def assert_first_record_only(self, m, result, run_id):
        acts = self.acts_in(m, result, run_id)
        self.assertEqual(acts.get("read-first-record"), ["journal.jsonl"], acts)
        self.assertEqual(sorted(acts), ["lstat", "read-first-record"], "more than its journal's first record was read: %s" % acts)

    def test_RUN5_SEC12_earlier_runs_are_found_by_the_fingerprints_of_the_keys_held_and_nothing_else_of_another_run_is_read(self):
        first, second, third = self.three()
        m = self.m
        looked = m.look("demo")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(self.read_whole(m, looked), sorted([first, second]), "not the first two runs' journals, read whole")
        self.assert_first_record_only(m, looked, third)
        for run in (first, second):
            self.assertEqual(self.acts_in(m, looked, run).get("walk"), ["."], "RUN-4's check was not made on a run found")
        site = m.look("demo-site")
        self.assertEqual(site.ending, "preview", site.text)
        self.assertEqual(self.read_whole(m, site), [second], "a look under the second key reads the one run opened under it")
        for run in (first, third):
            self.assert_first_record_only(m, site, run)

    def test_RUN5_EV7_after_a_new_keying_value_no_run_opened_before_it_is_an_earlier_run(self):
        first, second, third = self.three()
        m = self.m
        rowlib.install(m, *self.LANES())
        sunset = self.closed_run(m, "dusk", "sunset")
        found = m.look("dusk", "restore")
        self.assertEqual(found.ending, "preview", found.text)
        self.assertEqual(self.read_whole(m, found), [sunset], "a restore under the name of a closed sunset does not read its journal")
        dirs = dict((r, m.snapshot(os.path.join(".sun-v2", "runs", r))) for r in (first, second, third, sunset))
        os.remove(m.facts.keying_file)
        os.remove(m.facts.open_runs_file)
        for name in m.lock_names():
            os.remove(os.path.join(m.facts.locks_dir, name))
        looked = m.look("demo")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertTrue(os.path.exists(m.facts.keying_file), "no new value was made")
        self.assertEqual(self.read_whole(m, looked), [], "a run opened under the earlier value is read as an earlier run")
        calls = len([c for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold") for c in m.calls(tool) if c["changing"]])
        restore = m.look("dusk", "restore")
        # EV-7 (batch 24): "after the fixture's owner has removed the keying value's file ... a restore summoned under the same
        # name reads that sunset's journal as no retiring run's, no manifest it writes holds a reverse of that sunset's
        # operations, and no fake records an effect call. No retiring run: that restore's look ends `refused` before any
        # preview, with no manifest and no journal written and its form holding the fixed words"
        self.assertEqual(restore.ending, "refused", restore.text)
        self.assertIn(texts.NO_RETIRING_RUN, restore.lines)
        self.assertEqual(self.read_whole(m, restore), [], "the sunset is still read as a retiring run's after a new value")
        names = os.listdir(m.facts.run_dir(restore.doc["run"]))
        self.assertFalse([n for n in names if n.startswith("manifest") or n == "journal.jsonl"], names)
        self.assertEqual(len([c for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold") for c in m.calls(tool) if c["changing"]]), calls)
        for run, before in dirs.items():
            self.assertEqual(m.snapshot(os.path.join(".sun-v2", "runs", run)), before, "a run directory changed")

    def test_RUN5_SEC12_a_directory_not_found_is_read_no_further_and_its_failed_checks_fail_no_read(self):
        first, second, third = self.three()
        m = self.m
        third_dir, journal = m.facts.run_dir(third), os.path.join(m.facts.run_dir(third), "journal.jsonl")
        saved = open(journal, "rb").read()
        os.chmod(third_dir, 0o755)
        wide = m.look("demo")
        os.chmod(third_dir, 0o700)
        self.assertEqual(wide.ending, "preview", wide.text)
        self.assert_first_record_only(m, wide, third)
        fab.cut_record(m, third, 1)
        os.chmod(journal, 0o600)
        cut = m.look("demo")
        self.assertEqual(cut.ending, "preview", cut.text)
        self.assert_first_record_only(m, cut, third)
        with open(journal, "wb") as fh:
            fh.write(saved)
        # the same two changes made to the first run's directory: a run found, so a failed read (RUN-7)
        first_dir = m.facts.run_dir(first)
        kept = open(os.path.join(first_dir, "journal.jsonl"), "rb").read()
        os.chmod(first_dir, 0o755)
        failed = m.look("demo")
        os.chmod(first_dir, 0o700)
        self.assertEqual(failed.ending, "refused", failed.text)
        self.assertTrue(any(l.startswith("the read failed") for l in failed.lines), failed.lines)
        fab.cut_record(m, first, 1)
        os.chmod(os.path.join(first_dir, "journal.jsonl"), 0o600)
        failed = m.look("demo")
        self.assertEqual(failed.ending, "refused", failed.text)
        self.assertTrue(any(l.startswith("the read failed") for l in failed.lines), failed.lines)
        with open(os.path.join(first_dir, "journal.jsonl"), "wb") as fh:
            fh.write(kept)

    def test_RUN5_LOG1_a_directory_with_no_journal_and_one_whose_journal_holds_only_a_cut_off_record_are_passed_by(self):
        first, second, third = self.three()
        m = self.m
        fourth = m.next_id("sunrise")
        os.makedirs(os.path.join(m.facts.run_dir(fourth), "protected"), 0o700)
        m.put(os.path.join(".sun-v2", "runs", fourth, "inputs.json"), "{}\n", 0o600)
        fifth = m.next_id("sunrise")
        os.makedirs(m.facts.run_dir(fifth), 0o700)
        line = open(os.path.join(m.facts.run_dir(first), "journal.jsonl"), "rb").read().split(b"\n")[0]
        with open(os.path.join(m.facts.run_dir(fifth), "journal.jsonl"), "wb") as fh:
            fh.write(line[: len(line) // 2])           # a cut-off record: the first record's bytes, no newline
        os.chmod(os.path.join(m.facts.run_dir(fifth), "journal.jsonl"), 0o600)
        looked = m.look("demo")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(self.read_whole(m, looked), sorted([first, second]))
        acts = self.acts_in(m, looked, fourth)
        self.assertFalse(set(acts) & {"read", "read-first-record", "walk"}, "a file was read in a directory with no journal: %s" % acts)
        acts = self.acts_in(m, looked, fifth)
        self.assertEqual(sorted(acts), ["lstat", "read-first-record"], acts)

    def test_RUN5_SEC12_a_fingerprint_a_run_not_found_has_caught_is_in_no_output_and_changes_nothing_of_what_is_read(self):
        first, second, third = self.three()
        m = self.m
        plain = m.look("demo")
        caught = m.journal(third)[0]["keys"][0]
        fab.catch(m, third, caught)
        looked = m.look("demo")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(self.read_whole(m, looked), self.read_whole(m, plain))
        self.assertNowhere(caught, looked)
        run_dir = m.facts.run_dir(looked.doc["run"])
        for name in ["manifest-1.json"] + [os.path.join("forms", f) for f in os.listdir(os.path.join(run_dir, "forms"))]:
            self.assertNotIn(caught, open(os.path.join(run_dir, name)).read(), name)

    def damaged_first_record(self, m, run_id, how):
        journal = os.path.join(m.facts.run_dir(run_id), "journal.jsonl")
        saved = open(journal, "rb").read()
        if how == "bytes that are no record":
            with open(journal, "wb") as fh:
                fh.write(b"these bytes are no record of a run's opening\n" + saved.split(b"\n", 1)[1])
            os.chmod(journal, 0o600)
        else:
            os.chmod(journal, 0o000)

        def put_back():
            os.chmod(journal, 0o600)
            with open(journal, "wb") as fh:
                fh.write(saved)
        return put_back

    def assert_stop_told(self, m, result, words, ending="refused"):
        self.assertEqual(result.ending, ending, result.text)
        form = open(result.doc["forms"][0]).read()
        for said in (result.lines, form):
            text = "\n".join(said) if isinstance(said, list) else said
            self.assertIn(words, text)
            self.assertIn(texts.RUNS_KEPT_AT + m.facts.runs_root, text, "where the run directories are kept is not said")
        own = result.doc.get("run")
        for other in m.run_ids():
            if other != own:
                self.assertNotIn(other, result.text + form, "a directory is named")

    def test_RUN5_RUN7_A57_a_first_record_that_cannot_be_read_ends_every_look_as_a_failed_read_naming_no_directory(self):
        first, second, third = self.three()
        m = self.m
        for index, how in enumerate(("bytes that are no record", "unreadable to its owner")):
            with self.subTest(first_record=how):
                live, went = m.started("live%d" % index)
                self.assertEqual(went.ending, "waiting", went.text)
                live_dir = m.facts.run_dir(live.doc["run"])
                put_back = self.damaged_first_record(m, third, how)
                for name, kind in (("demo", "sunrise"), ("another", "sunrise"), ("demo", "restore")):
                    stopped = m.look(name, kind)
                    self.assert_stop_told(m, stopped, texts.FIRST_RECORD_UNREADABLE)
                    names = os.listdir(m.facts.run_dir(stopped.doc["run"]))
                    self.assertFalse([n for n in names if n.startswith("manifest") or n == "journal.jsonl"], names)
                manifests = dict((n, open(os.path.join(live_dir, n), "rb").read()) for n in os.listdir(live_dir) if n.startswith("manifest-"))
                replanned = m.summon("replan", "live%d" % index, "--inputs", m.inputs(name="again.json"))
                self.assert_stop_told(m, replanned, texts.FIRST_RECORD_UNREADABLE, "stopped")
                self.assertEqual(dict((n, open(os.path.join(live_dir, n), "rb").read()) for n in os.listdir(live_dir) if n.startswith("manifest-")),
                                 manifests, "the manifest in force changed")
                put_back()
                again = m.look("demo")
                self.assertEqual(again.ending, "preview", again.text)
                self.assertEqual(self.read_whole(m, again), sorted([first, second]))
                restore = m.look("demo", "restore")          # past the stop: the key's earlier runs are sunrises (EV-7)
                self.assertEqual((restore.ending, restore.lines[1:]), ("refused", [texts.NO_RETIRING_RUN]), restore.text)

    def test_RUN5_LOG1_batch22_the_end_mark_the_bound_of_a_first_record_and_a_journal_that_cannot_be_examined(self):
        """RUN-5's test line (batch 22): "The end mark (LOG-1): in the third run's directory a journal whose one piece is
        bytes that are no record, with no end mark after them, is passed by as a cut-off record, and so is a journal of no
        bytes, the look reaching its preview; the same bytes with the end mark after them end the look as a first record
        that cannot be read does. So do a first record longer than the most the look reads of it, and a journal that cannot
        be examined, its directory made unsearchable to its owner with its other permissions kept: each ends the look
        `refused` with the same fixed words and no directory named." The most the look reads of a first record is
        `journal.FIRST_MOST` (65536 bytes as built)."""
        from sun_core import journal as journalmod
        first, second, third = self.three()
        m = self.m
        third_dir = m.facts.run_dir(third)
        path = os.path.join(third_dir, "journal.jsonl")
        saved = open(path, "rb").read()
        no_record = b"these bytes are no record of a run's opening"

        def journal_of(data):
            with open(path, "wb") as fh:
                fh.write(data)
            os.chmod(path, 0o600)

        passed = [("one piece of bytes that are no record, no end mark", no_record), ("no bytes", b"")]
        for label, data in passed:
            with self.subTest(passed_by=label):
                journal_of(data)
                looked = m.look("demo")
                self.assertEqual(looked.ending, "preview", looked.text)
                self.assertEqual(self.read_whole(m, looked), sorted([first, second]))
                self.assertEqual(sorted(self.acts_in(m, looked, third)), ["lstat", "read-first-record"])
        # an opening record of the tool's own shape, whole and of a sound chain head, made longer than the bound by keys
        # that are fingerprints of nothing: read past the bound it would be read as another key's run and passed by
        opening = json.loads(saved.split(b"\n", 1)[0])
        body = dict((k, v) for k, v in opening.items() if k != "h")
        body["keys"] = list(body["keys"]) + ["%064x" % i for i in range(1, journalmod.FIRST_MOST // 67 + 2)]
        body["h"] = journalmod._hash(journalmod.ZERO, body)
        over = fsio.canonical_json(body).encode("utf-8") + b"\n"
        self.assertGreater(len(over) - 1, journalmod.FIRST_MOST)
        stops = [("the same bytes with the end mark after them", lambda: journal_of(no_record + b"\n")),
                 ("a first record longer than the most the look reads of it", lambda: journal_of(over)),
                 ("a journal that cannot be examined, its directory unsearchable to its owner",
                  lambda: (journal_of(saved), os.chmod(third_dir, 0o600)))]
        for label, spoil in stops:
            with self.subTest(stops=label):
                spoil()
                try:
                    stopped = m.look("demo")
                finally:
                    os.chmod(third_dir, 0o700)
                self.assert_stop_told(m, stopped, texts.FIRST_RECORD_UNREADABLE)
                names = os.listdir(m.facts.run_dir(stopped.doc["run"]))
                self.assertFalse([n for n in names if n.startswith("manifest") or n == "journal.jsonl"], names)
                if label.startswith("a first record longer"):
                    reads = [e for e in stopped.events if e["op"] == "read-first-record" and e["subject"] == path]
                    self.assertEqual(len(reads), 1)
        journal_of(saved)
        self.assertEqual(m.look("demo").ending, "preview")

    def inputs_files(self, run_dir):
        return dict((n, open(os.path.join(run_dir, n), "rb").read()) for n in sorted(os.listdir(run_dir))
                    if n.startswith("inputs") and n.endswith(".json"))

    def stopped_replan(self, live_name, words):
        """A run with its go, a re-plan of it ended by a planning stop (A57's, on the third run's directory), the third
        run's directory then put back. Returns (the live run's id, its directory, the stopped re-plan's result)."""
        first, second, third = self.three()
        m = self.m
        live, went = m.started(live_name, inputs=m.inputs(name="first.json", description="the first plan's words"))
        self.assertEqual(went.ending, "waiting", went.text)
        live_dir = m.facts.run_dir(live.doc["run"])
        put_back = self.damaged_first_record(m, third, "bytes that are no record")
        stopped = m.summon("replan", live_name, "--inputs", m.inputs(name="stopped.json", description=words))
        put_back()
        self.assert_stop_told(m, stopped, texts.FIRST_RECORD_UNREADABLE, "stopped")
        self.assertEqual(sorted(n for n in os.listdir(live_dir) if n.startswith("manifest-")), ["manifest-1.json"])
        return live.doc["run"], live_dir, stopped

    def test_RUN11_RUN12_RUN5_LOG3_a_replan_after_a_replan_a_planning_stop_ended_makes_its_own_whole_look(self):
        """RUN-12: "A planning stop, a refused input or a lacking answer met in the look of a re-plan, in a run that already
        has a go, ends that invocation `stopped`, with the manifest in force unchanged." RUN-11: going on "takes a re-plan:
        a full look, a new manifest, a new preview and a new go". RUN-5: "Nothing a look read is carried to a later
        invocation except through the manifest." RUN-4: the run directory "holds the inputs, every manifest". LOG-3: "The
        only objects a run may remove are" those it lists, and an input is none of them. So a later re-plan makes its own
        whole look from its own inputs; what the stopped one saved stays, byte-equal, and nothing of it is carried."""
        m = self.m
        run, live_dir, stopped = self.stopped_replan("live", "the stopped plan's words")
        left = self.inputs_files(live_dir)
        self.assertEqual(len(left), 2, "the stopped re-plan did not save its inputs (SEC-9, RUN-4)")
        manifest_1 = open(os.path.join(live_dir, "manifest-1.json"), "rb").read()
        again = m.summon("replan", "live", "--inputs", m.inputs(name="again.json", description="the later plan's words"))
        self.assertIn("manifest_sha256", again.doc, again.text)
        self.assertEqual(again.ending, "waiting", again.text)
        self.assertEqual(sorted(n for n in os.listdir(live_dir) if n.startswith("manifest-")), ["manifest-1.json", "manifest-2.json"])
        self.assertEqual(open(os.path.join(live_dir, "manifest-1.json"), "rb").read(), manifest_1, "the superseded manifest changed")
        now = self.inputs_files(live_dir)
        for name, data in left.items():
            self.assertEqual(now.get(name), data, "an input an earlier invocation saved was changed or removed: %s" % name)
        added = [name for name in now if name not in left]
        self.assertEqual(len(added), 1, now)
        self.assertEqual(json.loads(now[added[0]])["description"], "the later plan's words")
        manifest_2 = json.load(open(os.path.join(live_dir, "manifest-2.json")))
        self.assertEqual(manifest_2["inputs"]["description"], "the later plan's words")
        preview = open(again.doc["forms"][0]).read()
        for said in (json.dumps(manifest_2), preview, again.text):
            self.assertNotIn("the stopped plan's words", said, "what the stopped look read was carried")
        went = m.run("go", "--kind", "sunrise", "--name", "live", "--run", run, "--manifest-sha256", again.doc["manifest_sha256"])
        self.assertEqual(went.ending, "waiting", went.text)
        self.assertEqual([r["kind"] for r in m.journal(run)].count("go"), 1, "the later plan's go was not recorded")
        # and a third re-plan after a second stopped one: the same
        put_back = self.damaged_first_record(m, self.three_ids[2], "bytes that are no record")
        stopped_again = m.summon("replan", "live", "--inputs", m.inputs(name="stopped2.json", description="a second stop"))
        put_back()
        self.assertEqual(stopped_again.ending, "stopped", stopped_again.text)
        third = m.summon("replan", "live", "--inputs", m.inputs(name="third.json", description="the third plan's words"))
        self.assertIn("manifest_sha256", third.doc, third.text)
        for name, data in now.items():
            self.assertEqual(self.inputs_files(live_dir).get(name), data, name)

    def test_SEC12_RUN11_a_stopped_replans_saved_inputs_are_searched_as_the_saved_inputs_are(self):
        """SEC-12: "Each time a value enters the register, the invocation searches for it in what its run has on record as
        safe: the saved inputs, every manifest and the journal." The inputs a stopped re-plan saved are saved inputs of the
        run (SEC-9, RUN-4). Its test line, "The hosting token: a fixture run whose saved description holds the fixture's
        current token renders its next status form with the fixed words in the token's place and then holds a disproof
        record", run with the description saved by a re-plan a planning stop ended."""
        m = self.m
        token = harness.canary("stopped-replan-token")
        run, live_dir, stopped = self.stopped_replan("live", "it mentions " + token)
        self.assertNotIn(token, json.dumps(m.journal(run)))
        status = m.summon("status", "live", env={"FAKEHOST_TOKEN": token})
        self.assertNowhere(token, status)
        form = open(status.doc["forms"][0]).read()
        self.assertNotIn(token, form)
        new = [r for r in m.journal(run) if r["kind"] == "disproof"]
        self.assertEqual(len(new), 1, "no disproof record for a value the stopped re-plan's saved inputs hold")
        span = new[0]["rests"]["content"]
        data = open(os.path.join(live_dir, span["file"]), "rb").read()
        self.assertEqual(data[span["start"]:span["end"]].decode(), token, "the record's span does not hold the value")
        self.assertNotIn(token, json.dumps(new[0]))
        # the next invocation reads that disproof record's value back from where it rests (SEC-12's disproof read)
        again = m.summon("status", "live")
        self.assertNotEqual((again.lines or [""])[0], texts.RUNDIR_STOP["disproof-unreadable"], again.text)
        self.assertNowhere(token, again)

    def test_RUN5_RUN7_A59_a_folder_of_run_directories_that_cannot_be_listed_ends_the_look_the_same_way(self):
        self.three()
        m = self.m
        mode = os.stat(m.facts.runs_root).st_mode & 0o777
        os.chmod(m.facts.runs_root, mode & ~0o444)
        try:
            stopped = m.look("demo")
        finally:
            os.chmod(m.facts.runs_root, mode)
        self.assert_stop_told(m, stopped, texts.RUNS_UNLISTABLE)
        self.assertEqual(m.look("demo").ending, "preview")


class RUN9to11(RunCase):
    def test_RUN9_no_effect_without_a_go_and_a_manifest_altered_after_the_go_is_refused_before_any_operation(self):
        m = self.clean()
        looked = m.look()
        self.assertEqual(self.effect_calls(), [], "an effect call was made with no go on record")
        wrong = m.run("go", "--kind", "sunrise", "--name", "demo", "--run", looked.doc["run"], "--manifest-sha256", "0" * 64)
        self.assertEqual((wrong.ending, wrong.lines), ("refused", [texts.NOT_THE_PREVIEWED]))
        self.assertEqual(self.effect_calls(), [])
        went = m.go(looked, kill=lambda e: e["op"] == "journal" and e["stage"] == "post" and e["subject"] == "completion" and e.get("operation") == "B1")
        path = os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")
        doc = json.load(open(path))
        doc["operations"].append(dict(doc["operations"][-1], id="INJECTED"))
        calls = len(self.effect_calls())
        with open(path, "w") as fh:
            json.dump(doc, fh)
        os.chmod(path, 0o600)
        for altered in (m.summon("status"),
                        m.summon("resume", "demo", "--position", len(m.journal(looked.doc["run"])), "--word", "go on")):
            self.assertEqual((altered.ending, altered.lines), ("stopped", [texts.MANIFEST_ALTERED]))
        self.assertEqual(len(self.effect_calls()), calls)

    def test_RUN9_with_a_go_on_record_for_an_unaltered_manifest_the_operations_it_holds_run_and_no_other(self):
        m = self.clean()
        looked, went = m.started()
        self.assertEqual(went.ending, "complete")
        manifest = json.load(open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")))
        self.assertEqual(sorted(m.statuses(looked.doc["run"])), sorted(o["id"] for o in manifest["operations"]))

    def waiting(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word"),
                                                 rowlib.create("C1", needs=[{"output": "connected", "level": "state", "accepts": ["his word"],
                                                                             "treatment": "then not applicable"}])]))
        looked, went = m.started(caps=["canary"])
        self.assertEqual(went.ending, "waiting", went.text)
        return looked.doc["run"], went.doc["position"]

    def test_RUN10_no_position_a_stale_one_or_D16_a_current_one_without_his_word_does_nothing_but_render_status(self):
        run, position = self.waiting()
        m = self.m
        tries = {"no position": ["--word", "go on"], "a stale position": ["--position", position - 1, "--done", "O1"],
                 "D16: the current position without his word": ["--position", position]}
        for label, more in tries.items():
            with self.subTest(resume=label):
                before = len(m.journal(run))
                result = m.summon("resume", "demo", *more, caps=["canary"])
                self.assertEqual(result.ending, "waiting", result.text)
                self.assertEqual(result.lines[0], texts.WORD_NEEDED)
                self.assertTrue(os.path.exists(result.doc["forms"][0]))
                self.assertEqual(self.effect_calls(), [])
                self.assertEqual(len(m.journal(run)), before)
        done = m.summon("resume", "demo", "--position", position, "--done", "O1", caps=["canary"])
        self.assertEqual(done.ending, "complete", done.text)
        self.assertEqual(len(self.effect_calls()), 1)

    def test_RUN10_a_changed_account_capability_or_machine_location_asks_for_a_replan_with_no_effect(self):
        changes = {"a different account": lambda m: m.set_fake("fakehost", account="another-account"),
                   "a capability changed": None,
                   "a machine location changed": lambda m: (m.settings["locations"].update(developer_root=m.dev + "-moved"), m.write_settings())}
        for index, (label, change) in enumerate(changes.items()):
            with self.subTest(changed=label):
                self.m = harness.Machine(self.tmp, "ctx%d" % index, label)
                run, position = self.waiting()
                caps = ["canary"]
                if change is None:
                    caps = ["canary", "routines"]
                else:
                    change(self.m)
                result = self.m.summon("resume", "demo", "--position", position, "--done", "O1", caps=caps)
                self.assertEqual(result.ending, "waiting", result.text)
                self.assertEqual(result.lines[0], texts.REPLAN_NEEDED)
                self.assertEqual(self.effect_calls(), [])
                self.assertEqual(self.m.statuses(run), {})

    def test_RUN11_a_replan_carries_what_is_finished_drops_the_layer_keeps_the_old_manifest_and_waits_for_a_new_go(self):
        m = self.m
        hosted = rowlib.create("C1", needs=[{"output": "project folder", "level": "made", "treatment": "then not applicable"}])
        hosted["thing"]["layer"] = "hosting"
        push = rowlib.cas("G1", needs=[{"output": "remote", "level": "made", "treatment": "then not applicable"}])
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.build("B1"), hosted, push]))
        m.plan_fake("fakehost", {"command": "create", "do": "fail", "exit": 4, "stdout": {"kind": "conflict"}})
        looked, went = m.started()
        run = looked.doc["run"]
        self.assertEqual(went.ending, "stopped", went.text)
        old = open(os.path.join(m.facts.run_dir(run), "manifest-1.json"), "rb").read()
        calls = len(self.effect_calls())
        replanned = m.summon("replan", "demo", "--inputs", m.inputs(drop_layers=["hosting"]))
        self.assertEqual(replanned.ending, "stopped", replanned.text)
        preview = open(replanned.doc["forms"][0]).read()
        self.assertIn("[B1] finished earlier in this run (done)", preview)
        self.assertIn("not applicable (a layer the project lacks)", preview)
        self.assertEqual(open(os.path.join(m.facts.run_dir(run), "manifest-1.json"), "rb").read(), old, "the superseded manifest changed")
        # D16: nothing of the new plan runs before its own go (RUN-9)
        early = m.resume()
        self.assertEqual(early.lines[0], texts.NEW_PLAN_AWAITS)
        self.assertEqual(len(self.effect_calls()), calls)
        went_again = m.run("go", "--kind", "sunrise", "--name", "demo", "--run", run, "--manifest-sha256", replanned.doc["manifest_sha256"])
        self.assertEqual(went_again.ending, "complete", went_again.text)
        self.assertEqual(len(self.effect_calls()), calls, "a finished operation's effect call was recorded a second time, or a dropped one ran")
        self.assertEqual([r["kind"] for r in m.journal(run) if r["kind"] in ("open", "go")], ["open", "go"])

    def test_RUN11_a_create_left_outstanding_is_still_outstanding_in_a_new_plan_that_does_not_resolve_it(self):
        m = self.m
        row = rowlib.create("C1")
        row["lost_answer"] = {"way": "by dropping the layer only"}
        rowlib.install(m, rowlib.lane("sunrise", [row]))
        m.plan_fake("fakehost", {"command": "create", "do": "lose-answer"})
        looked, went = m.started()
        self.assertIn("stopped: an outstanding create", went.lines)
        replanned = m.summon("replan", "demo", "--inputs", m.inputs())
        self.assertEqual(replanned.ending, "stopped")
        self.assertIn("a create was sent and no answer came, and only dropping its layer resolves it: row C1", replanned.lines)
        self.assertEqual(len(m.calls("fakehost", "create")), 1)


class RUN12(RunCase):
    def test_RUN12_the_reference_run_ends_complete_and_an_owner_step_ends_waiting_with_no_lock_held(self):
        m = self.clean()
        looked, went = m.started()
        self.assertEqual(went.ending, "complete")
        self.assertEqual(m.journal(looked.doc["run"])[-1]["ending"], "complete")
        self.assertEqual(m.open_runs(), {})
        w = harness.Machine(self.tmp, "w", "w")
        rowlib.install(w, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word"), rowlib.check("K1")]))
        _l, waiting = w.started()
        self.assertEqual(waiting.ending, "waiting")
        form = open(waiting.doc["forms"][0]).read()
        self.assertIn("waiting on you: connect the fake host by hand; mode: on his word", form)
        self.assertEqual(w.lock_names(), [], "a waiting run holds a lock")
        self.assertEqual(w.statuses(_l.doc["run"]), {"K1": "passed"}, "an operation that does not need the waiting step did not run")
        for again in (w.summon("status"), w.summon("resume", "demo")):
            self.assertEqual(again.ending, "waiting")
            self.assertTrue(os.path.exists(again.doc["forms"][0]))
        left = w.summon("resume", "demo", "--position", w.summon("status").doc["position"], "--leave", "O1")
        self.assertEqual(left.ending, "ended with exceptions", left.text)
        self.assertIn("left, by your word", open(left.doc["forms"][0]).read())

    def test_RUN12_a_planted_stop_inside_an_operation_ends_stopped_with_that_operation_named_and_stays_stopped(self):
        m = self.clean()
        m.plan_fake("fakegit", {"command": "cas", "do": "fail", "exit": 9})
        looked, went = m.started()
        self.assertEqual(went.ending, "stopped")
        self.assertIn("operation: G1", went.lines)
        form = open(went.doc["forms"][0]).read()
        self.assertIn("stopped: a command failed; operation G1; the command you can run: fakegit cas --ref main --new c1 --old none", form)
        self.assertIn("the ways on: resume, re-plan, close", form)
        again = m.summon("status")
        self.assertEqual(again.ending, "stopped")
        endings = [r["ending"] for r in m.journal(looked.doc["run"]) if r["kind"] in ("invocation-end", "run-end")]
        self.assertTrue(set(endings) <= {"complete", "ended with exceptions", "waiting", "stopped", "closed"})

    def test_RUN12_a_planning_stop_in_a_first_look_is_refused_with_a_form_and_leaves_nothing_to_resume(self):
        m = self.clean()
        os.makedirs(os.path.join(m.dev, "demo"))
        refused = m.look()
        self.assertEqual(refused.ending, "refused")
        run_dir = m.facts.run_dir(refused.doc["run"])
        self.assertIn("row B1", open(refused.doc["forms"][0]).read())
        self.assertEqual([n for n in os.listdir(run_dir) if n.startswith(("manifest", "journal"))], [])
        self.assertEqual(m.open_runs(), {})
        self.assertEqual(m.summon("resume", "demo").lines, [texts.NOTHING_TO_RESUME])

    def test_RUN12_a_secret_no_file_on_the_machine_holds_ends_the_first_look_refused_with_the_lanes_one_command(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.keep("P1")]))
        refused = m.look()
        self.assertEqual(refused.ending, "refused", refused.text)
        self.assertIn("fakehost write --out <the env file>", open(refused.doc["forms"][0]).read())
        self.assertEqual(m.calls("fakehost", "issue") + m.calls("fakedump", "dump"), [])
        address = "postgres://app:" + harness.canary("dbpass") + "@db.invalid:5432/app"
        m.put("dev/demo.env", "DATABASE_URL=%s\n" % address, 0o600)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertNowhere(address, looked)

    def test_RUN12_before_the_startup_checks_pass_a_stop_holds_fixed_text_and_nothing_from_the_records(self):
        m = self.m
        typed = "typedname" + harness.canary("typed")[-6:]
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]))
        looked, went = m.started(inputs=m.inputs(description=typed))
        os.chmod(os.path.join(m.facts.run_dir(looked.doc["run"]), "inputs.json"), 0o644)
        stopped = m.summon("status")
        self.assertEqual(stopped.ending, "stopped")
        self.assertEqual(stopped.lines, [texts.RUNDIR_STOP["permissions"], texts.THE_RUN + looked.doc["run"]])
        self.assertNowhere(typed, stopped)
        self.assertIsNone(stopped.doc.get("forms"))


class TheBound(RunCase):
    """RUN-5 (batch 27; RUN-7's planning-stop row): "Nothing else caps the keys a run is opened under (RUN-2), so where the
    keys a look holds, with those its alias reads show, would make the record of its run's opening longer than that, the
    tool cannot write the record and keep this bound, no rule says what follows, and the look stops (GOV-1). It ends as
    RUN-7's planning stop, `refused` before a first go, its form saying in the tool's fixed words that the project has
    more names than one run can be opened under ... A re-plan adds no key (RUN-3), so it never meets this bound: a name
    form it shows that the run does not hold ends it at RUN-2's stop first. So no record of a run's opening is longer than
    the most a look reads of a first record." The most a look reads is the build's (`journal.FIRST_MOST`, 65536 bytes); the
    most keys a look lets through follows from it (`journal.opening_fits`)."""

    def names_file(self, m, name, count):
        m.put(os.path.join("dev", name, "names.txt"), "".join("%s-n%05d\n" % (name, i) for i in range(count)))

    def test_RUN5_RUN7_RUN2_A72_the_keys_a_look_holds_bound_its_opening_record_and_the_most_it_lets_through_fits(self):
        """RUN-5's test line (batch 27): "The bound: a fixture whose alias reads show so many name forms that the record of
        the run's opening would be longer than the most the look reads of a first record ends its first look `refused`
        before any preview, with the fixed words that the project has more names than one run can be opened under, and no
        manifest and no journal written; the same name forms met by a re-plan end it at RUN-2's stop for a name the run
        does not hold, `stopped` with the manifest in force byte-equal, and not with this bound's words; and the record of
        the opening of a run under the most keys a look lets through is no longer than the most the look reads of a first
        record."
        """
        most = max(n for n in range(1, 4000) if journalmod.opening_fits(n))
        self.assertFalse(journalmod.opening_fits(most + 1))
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]))
        # the most keys a look lets through: the summoned name's and most - 1 more its alias reads show
        self.names_file(m, "demo", most - 1)
        looked, went = m.started("demo")
        self.assertEqual(went.ending, "waiting", went.text)
        run = looked.doc["run"]
        with open(os.path.join(m.facts.run_dir(run), "journal.jsonl"), "rb") as fh:
            first_line = fh.read().split(b"\n", 1)[0]
        self.assertEqual(len(json.loads(first_line.decode("utf-8"))["keys"]), most)
        self.assertLessEqual(len(first_line) + 1, journalmod.FIRST_MOST, "the record of the opening is longer than the look reads")
        self.assertEqual(journalmod.Journal.first_record(m.world().fs, m.facts.run_dir(run))[0], "open",
                         "a later look cannot read that record of the opening whole")
        # one key more: the look stops before any preview
        self.names_file(m, "big", most)
        refused = m.look("big")
        self.assertEqual(refused.ending, "refused", refused.text)
        self.assertIn(texts.TOO_MANY_NAMES, refused.lines)
        self.assertIn(texts.TOO_MANY_NAMES, open(refused.doc["forms"][0]).read())
        names = os.listdir(m.facts.run_dir(refused.doc["run"]))
        self.assertFalse([n for n in names if n.startswith("manifest") or n == "journal.jsonl"], names)
        # the same name forms met by a re-plan of the run that has its go: RUN-2's stop, not the bound's words
        run_dir = m.facts.run_dir(run)
        manifests = dict((n, open(os.path.join(run_dir, n), "rb").read()) for n in os.listdir(run_dir) if n.startswith("manifest-"))
        self.names_file(m, "demo", most)
        replanned = m.summon("replan", "demo", "--inputs", m.inputs(name="again.json"))
        self.assertEqual(replanned.ending, "stopped", replanned.text)
        self.assertNotIn(texts.TOO_MANY_NAMES, replanned.text)
        self.assertTrue([l for l in replanned.lines if l.startswith(texts.NEW_NAME_IN_REPLAN.split("{")[0])], replanned.lines)
        self.assertEqual(dict((n, open(os.path.join(run_dir, n), "rb").read()) for n in os.listdir(run_dir) if n.startswith("manifest-")),
                         manifests, "the manifest in force changed")

class ANameLearntMidway(RunCase):
    """RUN-2, RUN-3 and RUN-7's row (the owner's ruling A72; batch 29): "Where the alias reads of a re-plan show a name form
    whose key the run does not hold, no lock is taken under it and no key is added: the re-plan's look ends at once as a
    planning stop (RUN-7), `stopped`, with the manifest in force unchanged, its form saying in the tool's fixed words that
    the project now shows another name and, as for a name a provider shows, naming the private file that holds it. The ways
    on are a close of the run (RUN-13) and a new summons that gives all the names. It is a stop the owner ruled on its own
    (A72)." RUN-3: "No key is added after that first go"."""

    def test_RUN3_RUN2_A72_a_replan_whose_alias_reads_show_a_further_name_stops_and_takes_no_lock_under_it(self):
        """RUN-3's test line: "A name learnt midway: that sunrise is stopped, and the fixture's alias reads then show a third
        name; a re-plan of it ends `stopped`, with the manifest in force byte-equal, no lock taken under the third name's
        key, the record of open runs and the run's journal holding no fingerprint of that key, and its form saying in fixed
        words that the project now shows another name and naming the private file that holds it; no fake records an effect
        call. A close of that run is then accepted, and a new summons under all three names takes all three locks and, at its
        go, is opened under all three keys (the owner's ruling, A72)." RUN-2's: "the alias reads of a re-plan that show a name
        form whose key the run does not hold take no lock under it, the lock fake recording none, and end that re-plan
        `stopped` as RUN-3's test line has it"."""
        m = self.m
        # a check of a folder that is not there fails, and the sunrise ends `stopped` (OP-8)
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.check("K1", place=rowlib.path(rowlib.DEV, "absent-folder"))]))
        m.put("dev/demo/names.txt", "demo-site\n")
        looked, went = m.started("demo")
        self.assertEqual(went.ending, "stopped", went.text)
        run = looked.doc["run"]
        run_dir = m.facts.run_dir(run)
        self.assertEqual(sorted(m.journal(run)[0]["keys"]), sorted([m.fingerprint("demo"), m.fingerprint("demo-site")]))
        m.put("dev/demo/names.txt", "demo-site\ndemo-shop\n")
        third = m.fingerprint("demo-shop")
        manifests = dict((n, open(os.path.join(run_dir, n), "rb").read()) for n in os.listdir(run_dir) if n.startswith("manifest-"))
        calls = [c for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold") for c in m.calls(tool) if c.get("changing")]
        replanned = m.summon("replan", "demo", "--inputs", m.inputs(name="again.json"))
        self.assertEqual(replanned.ending, "stopped", replanned.text)
        told = [l for l in replanned.lines if l.startswith(texts.NEW_NAME_IN_REPLAN.split("{")[0])]
        self.assertEqual(len(told), 1, replanned.lines)
        private = told[0].split("the private file that holds it: ", 1)[1].split(";", 1)[0]
        self.assertTrue(private.startswith(os.path.join(run_dir, "protected") + os.sep), private)
        self.assertIn("demo-shop", open(private).read(), "the private file does not hold the name")
        form = open(replanned.doc["forms"][0]).read()
        self.assertIn(told[0], form)
        self.assertNotIn("demo-shop", replanned.text + form, "the name is shown")
        self.assertEqual([e for e in replanned.events if third in str(e.get("subject"))], [], "a lock was taken under the third key")
        self.assertNotIn(third, json.dumps(m.open_runs()))
        self.assertNotIn(third, json.dumps(m.journal(run)))
        self.assertEqual(dict((n, open(os.path.join(run_dir, n), "rb").read()) for n in os.listdir(run_dir) if n.startswith("manifest-")),
                         manifests, "the manifest in force changed")
        self.assertEqual([c for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold") for c in m.calls(tool) if c.get("changing")], calls)
        self.assertEqual(m.summon("close", "demo", "--word", "close").ending, "closed")
        os.remove(m.path("dev", "demo", "names.txt"))
        looked, went = m.started("demo", also=("demo-site", "demo-shop"))
        self.assertEqual(went.ending, "stopped", went.text)
        three = sorted([m.fingerprint("demo"), m.fingerprint("demo-site"), third])
        self.assertEqual(sorted(m.journal(looked.doc["run"])[0]["keys"]), three)
        self.assertEqual(sorted(k for k, v in m.open_runs().items() if v == looked.doc["run"]), three)


class AGoHoldsExactlyItsLooksKeys(RunCase):
    """RUN-8 (batch 31): a manifest holds "the keys the look held, each by its fingerprint (RUN-2)". RUN-9 (batches 31 and 33;
    the owner's rulings A76 and A79): "A first go recorded by an invocation other than its look's is recorded only where the
    keys that invocation holds are exactly those its manifest records (RUN-8): where its alias reads show, or a name it
    carries gives, a key the look did not hold, no go is recorded and it ends `refused`, as RUN-2 says (the owner's ruling,
    A76). Where it holds fewer keys than its look did, a name form being gone from its alias reads, no go is recorded either:
    it ends `refused`, its form saying in fixed words that the project no longer shows a name its look showed and naming the
    private file that holds it, as RUN-2 says (the owner's ruling, A79)." RUN-2: "a summons that continues a run, a resume, a
    re-plan or the go of a re-plan, and carries a name whose key that run is not open under, is turned away at part (c) as
    RUN-3 turns a summons away: `refused`, the run unchanged (RUN-12), the output the tool's fixed text that the run is not
    open under a name the summons gave. No key is added for it." (that stop rests on A72).

    RUN-2 as batch 34 words it (A82; report-9's questions 24 and 25 answered): "The go of a first look that an earlier
    invocation made is a new summons and makes its alias reads again, and takes at part (e) the lock of each name form they
    show, as every new summons does. Which keys that look held it learns from the keys its manifest records (RUN-8), and
    from nothing else; the manifest is in the run directory, so the go reads those keys only once its startup checks have
    passed, RUN-4's checks on that run directory and its disproof read among them (SEC-12), and compares them in memory
    with the keys it holds." And "A summons that continues a run, a resume with his word or with none (a status), a re-plan,
    the go of a re-plan or a close (SEC-12), and carries a name whose key that run is not open under, is turned away at part
    (c)"."""

    def go_reads_its_run_directory_after_run4(self, m, result, run):
        """RUN-2's test line (A82): "the fixture file system recording no read in the run directory before RUN-4's checks on
        it, the manifest read after them". RUN-4's checks, as the frame words them: "the run directory and everything in it
        must be owner-only and the journal's chain (LOG-1) must hold". So the first act in the run directory is the check
        that it is there, then the walk of everything in it; the journal's read closes the checks; every read of a manifest
        comes after that."""
        run_dir = m.facts.run_dir(run)
        inside = [e for e in result.events if e["subject"] == run_dir or str(e["subject"]).startswith(run_dir + os.sep)]
        self.assertTrue(inside, "the go read nothing of its run directory")
        walk = stage_index(inside, lambda e: e["op"] == "walk" and e["subject"] == run_dir)
        self.assertIsNotNone(walk, "no owner-only check of the run directory (RUN-4)")
        before = [e for e in inside if e["i"] < walk]
        self.assertEqual([(e["op"], e["subject"]) for e in before], [("lstat", run_dir)],
                         "a read in the run directory before RUN-4's checks on it")
        journal = os.path.join(run_dir, "journal.jsonl")
        checked = stage_index(inside, lambda e: e["i"] > walk and e["subject"] == journal)
        self.assertIsNotNone(checked, "RUN-4's chain check of the journal was not made")
        manifests = [e for e in inside if e["stage"] == "read" and os.path.basename(str(e["subject"])).startswith("manifest-")
                     and e["op"] == "read"]
        self.assertTrue(manifests, "the go did not read its manifest")
        self.assertTrue(all(e["i"] > checked for e in manifests), "the manifest was read before RUN-4's checks ended")

    def lane(self, m):
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.create("C1")]))

    def names(self, m, *names):
        if names:
            m.put("dev/demo/names.txt", "".join(n + "\n" for n in names))
        elif os.path.exists(m.path("dev", "demo", "names.txt")):
            os.remove(m.path("dev", "demo", "names.txt"))

    def no_go(self, m, run, refused, line, holds, hidden):
        self.assertEqual(refused.ending, "refused", refused.text)
        run_dir = m.facts.run_dir(run)
        self.assertFalse([n for n in os.listdir(run_dir) if n.startswith("journal")], "a journal was written: no go may be recorded")
        self.assertNotIn(run, json.dumps(m.open_runs()), "a run was opened")
        for name in ("demo",) + tuple(holds):
            self.assertNotIn(m.fingerprint(name), json.dumps(m.open_runs()), "the record of open runs holds a key of " + name)
        self.assertEqual(m.lock_names(), [], "a lock's file of that summons was left")
        self.assertEqual(self.effect_calls(), [], "a fake recorded an effect call")
        told = [l for l in refused.lines if l.startswith(line.split("{")[0])]
        self.assertEqual(len(told), 1, refused.lines)
        private = told[0].split("the private file that holds it: ", 1)[1].split(";", 1)[0]
        self.assertTrue(private.startswith(os.path.join(run_dir, "protected") + os.sep), private)
        held = open(private).read()
        for name in holds:
            self.assertIn(name, held, "the private file does not hold the name")
        form = open(refused.doc["forms"][0]).read()
        self.assertIn(told[0], form, "the refusal form does not say it")
        for name in hidden:
            self.assertNotIn(name, refused.text + form, "a name its alias reads showed is shown")

    def test_RUN8_A76_a_manifest_records_the_keys_its_look_held_and_one_without_them_fails_its_validation(self):
        """RUN-8's test line: "a manifest from which any one entry this rule lists is removed fails its validation, and no
        preview is rendered from it"; the entry is named here by hand ("keys"), not taken from the code's own list."""
        from sun_core import manifest as manifestmod
        m = self.m
        self.lane(m)
        self.names(m, "demo-site")
        looked = m.look("demo")
        self.assertEqual(looked.ending, "preview", looked.text)
        doc, _sha = manifestmod.load(fsio.FS(), m.facts.run_dir(looked.doc["run"]), 1)
        self.assertEqual(doc.get("keys"), sorted([m.fingerprint("demo"), m.fingerprint("demo-site")]))
        self.assertNotIn("demo-site", json.dumps(doc.get("keys")))
        broken = dict(doc)
        del broken["keys"]
        with self.assertRaises(manifestmod.Invalid):
            manifestmod.validate(broken)

    def test_RUN9_RUN2_A76_a_name_that_appears_between_the_look_and_the_go_ends_the_go_refused_with_no_go(self):
        """RUN-9's test line: "A name between the look and the go: a first look ends with its preview; the fixture's alias
        reads then show a further name; the go, summoned in a later invocation, takes no lock under that name, records no go,
        writes no journal, opens no run and ends `refused`, its refusal form saying in fixed words that the project now shows
        another name and naming the private file that holds it, and no fake records an effect call; a go summons that carries
        a further name of its own ends the same way; a new summons under all the names then makes a new look, and its go is
        recorded with every key (the owner's ruling, A76)." As batch 34 words it (A82): "the go, summoned in a later
        invocation, takes that name's lock and releases it as it ends, leaving no lock's file". RUN-2's test line: "the lock
        fake recording that name's lock taken at part (e) and released as the go ends, and the fixture file system recording
        no read in the run directory before RUN-4's checks on it, the manifest read after them"."""
        m = self.m
        line = getattr(texts, "NEW_NAME_AT_GO", "the project now shows another name{")
        self.lane(m)
        looked = m.look("demo")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.names(m, "demo-shop")
        refused = m.go(looked, "demo")
        self.no_go(m, looked.doc["run"], refused, line, ("demo-shop",), ("demo-shop",))
        # the further name's lock: taken at part (e), before the run directory is opened, and released as the go ends
        shop = m.facts.lock_file(m.fingerprint("demo-shop"))
        taken = stage_index(refused.events, lambda e: e["op"] == "lock" and e["subject"] == shop)
        released = stage_index(refused.events, lambda e: e["op"] == "unlock-remove" and e["stage"] == "post" and e["subject"] == shop)
        opened = stage_index(refused.events, lambda e: e["subject"] == m.facts.run_dir(looked.doc["run"]))
        self.assertIsNotNone(taken, "the further name's lock was not taken at part (e)")
        self.assertIsNotNone(released, "the further name's lock was not released as the go ended")
        self.assertLess(taken, opened, "the further name's lock was taken after the run directory was opened")
        self.assertLess(opened, released)
        self.assertFalse(os.path.lexists(shop), "the further name's lock's file was left")
        self.go_reads_its_run_directory_after_run4(m, refused, looked.doc["run"])
        # a go summons that carries a further name of its own (the alias reads showing nothing new)
        self.names(m)
        looked = m.look("demo")
        self.assertEqual(looked.ending, "preview", looked.text)
        refused = m.go(looked, "demo", also=("demo-extra",))
        self.no_go(m, looked.doc["run"], refused, line, ("demo-extra",), ())
        # a new summons under all the names: a new look, and its go recorded with every key
        self.names(m, "demo-shop")
        looked, went = m.started("demo")
        self.assertNotEqual(went.ending, "refused", went.text)
        self.assertEqual(sorted(m.journal(looked.doc["run"])[0]["keys"]), sorted([m.fingerprint("demo"), m.fingerprint("demo-shop")]))

    def test_RUN9_RUN2_A79_a_name_gone_between_the_look_and_the_go_ends_the_go_refused_with_no_go(self):
        """RUN-9's test line: "A name gone between the look and the go: a first look whose alias reads showed a second name
        ends with its preview; the fixture's alias reads then no longer show it; the go, summoned in a later invocation, takes
        no lock under the second name, records no go, writes no journal, opens no run and ends `refused`, its refusal form
        saying in fixed words that the project no longer shows a name its look showed and naming the private file that holds
        it; the record of open runs holds no fingerprint of either key, and no fake records an effect call; a go summons that
        leaves off a name the owner gave that look, which no alias read shows, ends the same way; a new summons under the
        names the project now shows then makes a new look, and its go is recorded with the first key alone (the owner's
        ruling, A79).\""""
        m = self.m
        line = getattr(texts, "NAME_GONE_AT_GO", "the project no longer shows a name its look showed{")
        self.lane(m)
        self.names(m, "demo-site")
        looked = m.look("demo")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.names(m)
        refused = m.go(looked, "demo")
        second = m.fingerprint("demo-site")
        self.assertEqual([e for e in refused.events if e["op"] == "lock" and second in str(e.get("subject"))], [],
                         "a lock was taken under the second name")
        self.no_go(m, looked.doc["run"], refused, line, ("demo-site",), ("demo-site",))
        # RUN-2's test line: "and so do those that no longer show a name that look's alias reads showed"
        self.go_reads_its_run_directory_after_run4(m, refused, looked.doc["run"])
        # a go summons that leaves off a name the owner gave that look, which no alias read shows
        looked = m.look("demo", also=("demo-typed",))
        self.assertEqual(looked.ending, "preview", looked.text)
        refused = m.go(looked, "demo")
        self.no_go(m, looked.doc["run"], refused, line, ("demo-typed",), ())
        # a new summons under the names the project now shows: its go is recorded with the first key alone
        looked, went = m.started("demo")
        self.assertNotEqual(went.ending, "refused", went.text)
        self.assertEqual(m.journal(looked.doc["run"])[0]["keys"], [m.fingerprint("demo")])

    def test_RUN2_RUN12_A72_a_summons_that_continues_a_run_with_a_name_it_is_not_open_under_is_turned_away_at_c(self):
        """RUN-2's test line: "a resume, and in a second pass a re-plan, of a fixture run, summoned with the run's own name and a
        further name whose key the run is not open under, is refused at the early look with the tool's fixed text, the run's
        journal and the record of open runs byte-equal and no lock's file of that summons left". RUN-12's: "a resume of a run
        left `stopped`, carrying a further name the run is not open under, ends `refused` with fixed text, the run's journal
        byte-equal and its status still `stopped`". A third pass is the go of a re-plan, which RUN-2's rule text names."""
        m = self.m
        line = getattr(texts, "NOT_OPEN_UNDER_NAME", "<no fixed text for a name the run is not open under>")
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.check("K1", place=rowlib.path(rowlib.DEV, "absent-folder"))]))
        looked, went = m.started("demo")
        self.assertEqual(went.ending, "stopped", went.text)
        run = looked.doc["run"]
        journal = os.path.join(m.facts.run_dir(run), "journal.jsonl")

        def turned_away(result):
            self.assertEqual(result.ending, "refused", result.text)
            self.assertEqual(result.lines, [line])
            self.assertEqual(open(journal, "rb").read(), before_journal, "the run's journal changed")
            self.assertEqual(open(m.facts.open_runs_file, "rb").read(), before_open, "the record of open runs changed")
            self.assertEqual(m.lock_names(), [], "a lock's file of that summons was left")
            self.assertEqual([e for e in result.events if e["stage"] == "read" and str(e["subject"]).startswith(m.dev)], [],
                             "it read a thing of the project: it was not turned away at the early look")
            self.assertNotIn(m.fingerprint("demo-other"), json.dumps(m.open_runs()))
            self.assertEqual(m.summon("status", "demo").ending, "stopped")

        position = m.summon("status", "demo").doc["position"]
        before_journal, before_open = open(journal, "rb").read(), open(m.facts.open_runs_file, "rb").read()
        turned_away(m.summon("resume", "demo", "--position", position, "--word", "go on", also=("demo-other",)))
        turned_away(m.summon("replan", "demo", "--inputs", m.inputs(name="again.json"), also=("demo-other",)))
        replanned = m.summon("replan", "demo", "--inputs", m.inputs(name="again-2.json"))
        self.assertTrue(replanned.doc.get("manifest_sha256"), replanned.text)
        before_journal, before_open = open(journal, "rb").read(), open(m.facts.open_runs_file, "rb").read()
        turned_away(m.go(replanned, "demo", also=("demo-other",)))

    def test_RUN2_RUN12_A82_a_status_and_a_close_that_carry_a_name_the_run_is_not_open_under_are_turned_away_at_c(self):
        """RUN-2's test line as batch 34 words it (A82): "a resume, and in further passes a status summons, a re-plan and a
        close, of a fixture run, summoned with the run's own name and a further name whose key the run is not open under, is
        refused at the early look with the tool's fixed text, the run's journal and the record of open runs byte-equal, no
        status form and no close record written, and no lock's file of that summons left". The resume and the re-plan are
        the test above; these are the status and the close (report-9's question 25)."""
        m = self.m
        line = getattr(texts, "NOT_OPEN_UNDER_NAME", "<no fixed text for a name the run is not open under>")
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.check("K1", place=rowlib.path(rowlib.DEV, "absent-folder"))]))
        looked, went = m.started("demo")
        self.assertEqual(went.ending, "stopped", went.text)
        run = looked.doc["run"]
        run_dir = m.facts.run_dir(run)
        journal = os.path.join(run_dir, "journal.jsonl")
        forms_dir = os.path.join(run_dir, "forms")
        before_journal, before_open = open(journal, "rb").read(), open(m.facts.open_runs_file, "rb").read()
        before_forms = sorted(os.listdir(forms_dir))
        for result in (m.summon("status", "demo", also=("demo-other",)),
                       m.summon("close", "demo", "--word", "close", also=("demo-other",))):
            self.assertEqual(result.ending, "refused", result.text)
            self.assertEqual(result.lines, [line])
            self.assertNotIn("forms", result.doc or {}, "a form was named")
            self.assertEqual(sorted(os.listdir(forms_dir)), before_forms, "a status form was written")
            self.assertEqual(open(journal, "rb").read(), before_journal, "the run's journal changed: a close record was written")
            self.assertEqual(open(m.facts.open_runs_file, "rb").read(), before_open, "the record of open runs changed")
            self.assertEqual(m.lock_names(), [], "a lock's file of that summons was left")
            self.assertEqual([e for e in result.events if e["stage"] == "read" and str(e["subject"]).startswith(m.dev)], [],
                             "it read a thing of the project: it was not turned away at the early look")
            self.assertEqual([e for e in result.events if e["stage"] in ("pre", "post") and str(e["subject"]).startswith(run_dir)], [],
                             "it wrote in the run directory")
            self.assertNotIn(m.fingerprint("demo-other"), json.dumps(m.open_runs()))
        self.assertEqual(m.summon("status", "demo").ending, "stopped", "the run is no longer as it stood")


if __name__ == "__main__":
    unittest.main()
