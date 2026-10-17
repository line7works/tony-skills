"""Group 3.6 of the frame: keeping, retiring, and a run's last record (KEEP-1 to KEEP-5), with SEC-2's private
password file, on fakes.

Not here, and said in the report: KEEP-4's "after a sunset, a restore and a second sunset" and KEEP-5's "a
second sunset after a restore" need a restore, which this slice did not build; KEEP-1's "ends the look with its
name" is question 8; SEC-2's "gone ... after a kill and resume" is question 1.
"""
import hashlib
import json
import os
import unittest

import harness
import rowlib
from sun_core import fsio, plan, texts
from test_log_op import at, planted

P = plan.RETIREMENT_PHASES
PASSWORD = "pw" + harness.canary("dbpass")
ADDRESS = "postgres://appuser:%s@db.fixture.invalid:5432/appdb?sslmode=require" % PASSWORD


class KeepCase(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.count = 0

    def fresh(self, rows, tied=True):
        self.count += 1
        m = harness.Machine(self.tmp, "k%d" % self.count, "k%d" % self.count)
        rowlib.install(m, rowlib.lane("sunset", rows, phases=P))
        m.put("dev/demo.env", "# fixture\nDATABASE_URL=%s\n" % ADDRESS, 0o600)
        m.put("dev/demo-scope.md", "scope\n")
        identity = "db-" + hashlib.sha256(m.home.encode()).hexdigest()[:10]
        m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}},
                   identity=identity if tied else None)
        return m

    def rows(self, last=False):
        out = [rowlib.keep("P1", P[0]),
               rowlib.retiring(rowlib.move("T12", P[1], output="archived"), where="machine"),
               rowlib.retiring(rowlib.refusing("T22", P[2]))]
        if last:
            out.append(rowlib.last_record("L1", P[3]))
        return out

    def run_sunset(self, m, **kw):
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        return looked.doc["run"], m.go(looked, kind="sunset", **kw)

    def dump(self, m):
        return os.path.join(m.dev, "demo-dump.txt")


class Keeps(KeepCase):
    def test_KEEP1_the_completion_record_holds_the_inventory_the_size_the_fingerprint_and_the_sources_identity_of_one_state(self):
        m = self.fresh([rowlib.keep("P1", P[0])])
        m.plan_fake("fakedump", {"command": "dump", "then_add_table": "gamma"})      # the source changes right after the snapshot
        run, went = self.run_sunset(m)
        self.assertEqual(went.ending, "complete", went.text)
        done = [r for r in m.journal(run) if r["kind"] == "completion"][0]
        data = open(self.dump(m), "rb").read()
        self.assertEqual((done["keep"]["size"], done["keep"]["sha256"]), (len(data), fsio.sha256_hex(data)))
        folder = os.path.join(m.facts.run_dir(run), "protected")
        self.assertEqual(open(os.path.join(folder, done["keep"]["inventory"]["record"])).read(), "2")
        self.assertEqual(json.loads(open(os.path.join(folder, done["keep"]["source"]["record"])).read()),
                         "db-" + hashlib.sha256(m.home.encode()).hexdigest()[:10])
        self.assertEqual(data.count(b"TABLE "), 2, "the copy does not match the inventory of the state it was taken in")
        self.assertEqual(os.stat(self.dump(m)).st_mode & 0o777, 0o600)
        self.assertNotIn(done["keep"]["source"]["label"], ["db-"])
        for record in m.journal(run):
            self.assertNotIn("db-" + hashlib.sha256(m.home.encode()).hexdigest()[:10], json.dumps(record), "a held identity is in the journal")

    def test_KEEP1_a_schema_that_appears_between_the_look_and_the_copy_is_in_the_copy_or_the_keep_fails(self):
        m = self.fresh([rowlib.keep("P1", P[0])])
        looked = m.look(kind="sunset")
        state = m.fake("fakedump", "state.json")
        state["database"]["tables"].append("appeared")
        m.set_fake("fakedump", database=state["database"])
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertIn(b"TABLE appeared", open(self.dump(m), "rb").read())
        short = self.fresh([rowlib.keep("P1", P[0])])
        short.plan_fake("fakedump", {"command": "dump", "report_count": 3})     # the copy and its inventory disagree
        run, went = self.run_sunset(short)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: the keep is not whole", went.lines)
        self.assertFalse(os.path.exists(self.dump(short)), "a partial copy was published as a keep")
        self.assertEqual(short.statuses(run), {})

    def test_KEEP1_a_table_that_cannot_be_read_ends_the_look_and_no_input_yields_a_partial_keep(self):
        m = self.fresh([rowlib.keep("P1", P[0])])
        m.set_fake("fakedump", unreadable=["beta"])
        ended = m.look(kind="sunset", inputs=m.inputs(flags={"partial": True, "skip_unreadable": True}))
        self.assertEqual(ended.ending, "refused", ended.text)
        # K1 (her MINOR), closing rule: "Resolve the naming requirement through a permitted protected reference or an
        # explicit owner ruling, then assert that resolved behavior in the unreadable-table test." KEEP-1 now: "The form
        # of either tells what cannot be read as SEC-6 has held names told: the kind of thing, how many by the tool's own
        # count, and the private file that lists them; a name a provider gave is in no form and no output"; its test line:
        # "a planning stop whose form says that one table cannot be read and names a private file, with that table's name
        # in the file and in no form or output".
        run_dir = m.facts.run_dir(ended.doc["run"])
        form = open(ended.doc["forms"][0]).read()
        private = [line for line in ended.lines if line.startswith("1 table of row P1 cannot be read; its name is in a private file: ")]
        self.assertEqual(len(private), 1, ended.lines)
        path = private[0].split(": ", 1)[1]
        self.assertTrue(path.startswith(os.path.join(run_dir, "protected") + os.sep), path)
        self.assertIn(private[0], form)
        self.assertIn("beta", open(path).read(), "the table's name is not in the private file")
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertNowhere("beta", ended)
        self.assertNotIn("beta", form)
        self.assertEqual([n for n in os.listdir(run_dir) if n.startswith("manifest")], [])
        whole = self.fresh([rowlib.keep("P1", P[0])])
        a = whole.look(kind="sunset", inputs=whole.inputs(flags={"partial": True}))
        manifest = json.load(open(os.path.join(whole.facts.run_dir(a.doc["run"]), "manifest-1.json")))
        self.assertEqual(manifest["operations"][0]["keep_scope"]["scope"], "every table of the fake database")

    def test_SEC2_the_whole_address_travels_in_the_private_password_file_and_no_part_of_it_in_an_argument_or_the_environment(self):
        m = self.fresh([rowlib.keep("P1", P[0])])
        run, went = self.run_sunset(m)
        self.assertEqual(went.ending, "complete", went.text)
        seen = [s for s in m.fake("fakedump", "passfile.jsonl") if s["passfile"]]
        self.assertTrue(seen, "the fake dump tool was given no password file")
        used = seen[-1]
        self.assertTrue(used["passfile"].startswith(os.path.join(m.facts.run_dir(run), "private") + os.sep))
        self.assertEqual(used["passfile_mode"], "0o600")
        # G20-1: the whole address as one libpq service section, its name the one the declaration fixes for PGSERVICE
        self.assertEqual(used["passfile_text"], "[sun]\nhost=db.fixture.invalid\nport=5432\ndbname=appdb\nuser=appuser\n"
                                                "password=%s\nsslmode=require\n" % PASSWORD)
        self.assertFalse(os.path.exists(used["passfile"]), "the password file is not gone after the call")
        parts = [ADDRESS, PASSWORD, "appuser", "db.fixture.invalid", "5432", "appdb", "sslmode=require"]
        for call in m.calls("fakedump"):
            text = json.dumps(call["argv"]) + json.dumps(dict((k, v) for k, v in call["env_values"].items() if k != "FAKEDUMP_PASSFILE"))
            for part in parts:
                self.assertNotIn(part, text, "a part of the address is in an argument or an environment value")
            self.assertEqual(call["env_values"].get("FAKEDUMP_PASSFILE", used["passfile"]), used["passfile"])
        for part in (ADDRESS, PASSWORD):
            self.assertNowhere(part, went)
            for record in m.journal(run):
                self.assertNotIn(part, json.dumps(record))
            self.assertNotIn(part, open(os.path.join(m.facts.run_dir(run), "manifest-1.json")).read())


class LeftPasswordFile(KeepCase):
    """The reviewer's P1, closing rule: "Remove a leftover private password file at the next permitted startup point,
    including status and close, and verify its absence without requiring the keep to execute again." SEC-2: "Where a
    kill left it, the next invocation that continues the run removes it, at the one place SEC-12's order of first
    records gives." SEC-12: "once its startup checks have passed, and not before, every invocation that continues a run
    removes a private password file that a kill left in that run directory (SEC-2), whatever it was summoned for, a
    status and a close among them. A stop by the startup checks leaves the file where it is." SEC-2's test line: "A
    kill after the file is written and before the dump tool starts leaves it; in three passes the next summons is a
    resume, a status summons and a close, and in each the file is gone once that invocation's startup checks have
    passed and before its first journal record, the keep not having run again in the second and third; with that run
    directory given wider permissions first, the invocation stops on RUN-4's checks and the file is still there."
    """

    def killed_with_the_file(self, label):
        m = self.fresh([rowlib.keep("P1", P[0])])
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="sunset", kill=at("post", "create", "password-P1"))
        self.assertTrue(went.killed, "the kill after the password file was written did not come")
        run_dir = m.facts.run_dir(looked.doc["run"])
        left = os.path.join(run_dir, "private", "password-P1")
        self.assertTrue(os.path.isfile(left), "the kill did not leave the password file")
        self.assertEqual([s for s in m.fake("fakedump", "passfile.jsonl", []) if s["passfile"]], [], "the dump tool started before the kill")
        return m, run_dir, left

    def summon(self, m, label, position=None):
        if label == "resume":
            return m.resume() if position is None else m.summon("resume", "demo", "--position", position, "--word", "go on")
        if label == "status":
            return m.summon("status")
        return m.summon("close", "demo", "--word", "close")

    def test_SEC2_SEC12_LOG3_P1_the_next_resume_status_and_close_each_remove_it_once_their_startup_checks_have_passed(self):
        for label in ("resume", "status", "close"):
            with self.subTest(next_summons=label):
                m, run_dir, left = self.killed_with_the_file(label)
                # the resume carries the current position itself: no status summons stands before it
                result = self.summon(m, label, position=len(m.journal(os.path.basename(run_dir))))
                self.assertFalse(os.path.exists(left), "%s: the password file a kill left is still there" % label)
                events = result.events
                removed = [e["i"] for e in events if e["stage"] == "pre" and e["op"] == "remove" and e["subject"] == left]
                self.assertTrue(removed, "%s: no removal of the left file is recorded" % label)
                first_record = [e["i"] for e in events if e["stage"] == "pre" and e["op"] == "append"
                                and e["subject"] == os.path.join(run_dir, "journal.jsonl")]
                if label != "status":        # a status summons that owes no record writes none (SEC-12's table)
                    self.assertTrue(first_record, "%s: the invocation wrote no journal record" % label)
                if first_record:
                    self.assertLess(removed[0], first_record[0], "%s: the removal does not stand before the first journal record" % label)
                # once the startup checks have passed: RUN-4's read of the journal, then the disproof read's read of the
                # run's fingerprint key, both before the removal
                journal_read = [e["i"] for e in events if e["stage"] == "read" and e["subject"] == os.path.join(run_dir, "journal.jsonl")]
                key_read = [e["i"] for e in events if e["stage"] == "read" and e["subject"] == os.path.join(run_dir, "protected", "key")]
                self.assertTrue(journal_read and key_read)
                self.assertLess(journal_read[0], removed[0])
                self.assertLess(key_read[0], removed[0])
                if label != "resume":
                    self.assertEqual([s for s in m.fake("fakedump", "passfile.jsonl", []) if s["passfile"]], [], "%s: the keep ran again" % label)
                    self.assertEqual(m.calls("fakedump", "dump"), [], "%s: the keep ran again" % label)

    def test_SEC2_SEC12_P1_a_stop_by_RUN4s_checks_leaves_the_file_where_it_is(self):
        for label in ("resume", "status", "close"):
            with self.subTest(next_summons=label):
                m, run_dir, left = self.killed_with_the_file(label)
                os.chmod(run_dir, 0o755)
                result = self.summon(m, label, position=len(m.journal(os.path.basename(run_dir))))
                self.assertEqual(result.ending, "stopped", result.text)
                self.assertEqual(result.lines[0], texts.RUNDIR_STOP["permissions"])
                self.assertTrue(os.path.isfile(left), "%s: a stop by RUN-4's checks removed the file" % label)
                self.assertEqual([e for e in result.events if e["stage"] == "pre" and e["subject"] == left], [])
                os.chmod(run_dir, 0o700)


class NoLength(KeepCase):
    """SEC-12: "a component of no length is no part of an entry: nothing is searched for and nothing is withheld for
    it" (the author's reading, A45; report-3 marked it met, and this confirms it by test); its test line: "A connection
    address whose password is of no length is entered whole, and the status form of that run is rendered whole all the
    same."
    """

    def test_SEC12_A44_A45_a_component_of_no_length_is_no_part_of_an_entry_and_the_form_is_rendered_whole(self):
        from sun_core import channels, disproof, screen
        empty = "postgres://appuser:@db.fixture.invalid:5432/appdb"
        register = screen.Screen()
        entry = register.add(empty, channels.address_components(empty) + [""], None, "channel")
        self.assertEqual(entry.value, empty, "the address is not entered whole")
        self.assertEqual(entry.components, [], "a component of no length is part of the entry")
        self.assertNotIn("", entry.forms)
        self.assertNotIn(b"", disproof._needles(entry), "a search is made for a component of no length")
        self.assertFalse(register.holds("a line that holds no part of the address"))
        self.assertTrue(register.holds("before " + empty + " after"))
        m = self.fresh([rowlib.keep("P1", P[0]), rowlib.owner_step("O1", P[0], mode="on his word")])
        m.put("dev/demo.env", "# fixture\nDATABASE_URL=%s\n" % empty, 0o600)
        run, went = self.run_sunset(m)
        self.assertEqual(went.ending, "waiting", went.text)
        form = open(went.doc["forms"][0]).read()
        self.assertNotIn(texts.WITHHELD, form, "the status form is not rendered whole")
        self.assertNotIn(texts.WITHHELD, went.text)
        status = m.summon("status")
        self.assertNotIn(texts.WITHHELD, open(status.doc["forms"][0]).read())
        self.assertEqual([r for r in m.journal(run) if r["kind"] == "disproof"], [])


class Retirements(KeepCase):
    def test_KEEP2_a_database_the_providers_side_cannot_identify_keeps_the_keep_and_leaves_the_idle_out(self):
        m = self.fresh(self.rows(), tied=False)
        run, went = self.run_sunset(m)
        manifest = json.load(open(os.path.join(m.facts.run_dir(run), "manifest-1.json")))
        self.assertEqual([o["id"] for o in manifest["operations"]], ["P1", "T12"])
        self.assertEqual([(n["row"], n["reason"]) for n in manifest["not_applicable"]], [("T22", "cannot be tied to its copy")])
        self.assertIn("not applicable (cannot be tied to its copy)", open(os.path.join(m.facts.run_dir(run), "forms", "preview-1.txt")).read())
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.calls("fakehost", "set"), [], "the idle was called for a database that could not be tied to its copy")
        self.assertTrue(os.path.exists(self.dump(m)))

    def test_KEEP2_a_target_that_is_not_the_thing_its_keep_copied_stops_before_the_retirements_call(self):
        for label, when in (("a dump of another database", "before the go"), ("its identity changes after the go", "after the go")):
            with self.subTest(case=label):
                m = self.fresh(self.rows())
                looked = m.look(kind="sunset")
                change = lambda m=m: m.set_fake("fakehost", identity="db-another-one")      # noqa: E731
                if when == "before the go":
                    change()
                    went = m.go(looked, kind="sunset")
                else:
                    went = m.go(looked, kind="sunset", kill=planted(at("post", "journal", "completion", "T12"), change))
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: the target is not the thing its keep copied", went.lines)
                self.assertEqual(m.calls("fakehost", "set"), [])
                self.assertEqual(m.fake("fakehost", "state.json")["things"]["demo"]["state"], "active")
        same = self.fresh(self.rows())
        run, went = self.run_sunset(same)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(len(same.calls("fakehost", "set")), 1, "with one identity on both sides the idle was not made")

    def test_KEEP3_the_barrier_with_every_keep_intact_the_retirements_run_also_after_a_resume(self):
        m = self.fresh(self.rows())
        looked = m.look(kind="sunset")
        m.go(looked, kind="sunset", kill=at("post", "journal", "completion", "P1"))
        self.assertTrue(os.path.exists(os.path.join(m.dev, "demo-scope.md")))
        resumed = m.resume()
        self.assertEqual(resumed.ending, "complete", resumed.text)
        self.assertEqual(m.fake("fakehost", "state.json")["things"]["demo"]["state"], "paused")

    def test_KEEP3_D16_a_keep_that_no_longer_checks_out_stops_the_resume_at_the_barrier_with_nothing_further_retired(self):
        def cut(m, run):
            data = open(self.dump(m), "rb").read()
            with open(self.dump(m), "wb") as fh:
                fh.write(data[: len(data) // 2])

        def wide(m, run):
            os.chmod(self.dump(m), 0o644)

        def record(m, run):
            done = [r for r in m.journal(run) if r["kind"] == "completion" and r["op"] == "P1"][0]
            path = os.path.join(m.facts.run_dir(run), "protected", done["keep"]["inventory"]["record"])
            with open(path, "w") as fh:
                fh.write("3")
            os.chmod(path, 0o600)
        damages = {"a dump cut short": cut, "D16: wider permissions": wide, "D16: a failed content check with the size and fingerprint as recorded": record}
        for label, damage in damages.items():
            for after in ("P1", "T12"):
                with self.subTest(damage=label, between="after " + after):
                    m = self.fresh(self.rows())
                    looked = m.look(kind="sunset")
                    run = looked.doc["run"]
                    m.go(looked, kind="sunset", kill=at("post", "journal", "completion", after))
                    damage(m, run)
                    moved_before = not os.path.exists(os.path.join(m.dev, "demo-scope.md"))
                    resumed = m.resume()
                    self.assertEqual(resumed.ending, "stopped", resumed.text)
                    self.assertIn("stopped: the barrier: a keep is not done or does not check out", resumed.lines)
                    self.assertEqual(m.calls("fakehost", "set"), [], "a provider was retired past the barrier")
                    self.assertEqual(m.fake("fakehost", "state.json")["things"]["demo"]["state"], "active", "a fake is no longer live")
                    self.assertEqual(not os.path.exists(os.path.join(m.dev, "demo-scope.md")), moved_before, "a path was moved past the barrier")
                    self.assertEqual(moved_before, after == "T12")


class LastRecord(KeepCase):
    def lane_rows(self):
        return [rowlib.keep("P1", P[0]), rowlib.owner_step("O22", P[2], mode="read back"), rowlib.last_record("L1", P[3])]

    def records(self, m):
        return sorted(n for n in os.listdir(m.dev) if n.startswith("demo-record-"))

    def test_KEEP5_no_last_record_while_a_step_waits_and_once_it_is_read_back_one_is_written_from_the_journal_alone(self):
        m = self.fresh(self.lane_rows())
        run, went = self.run_sunset(m)
        self.assertEqual(went.ending, "waiting", went.text)
        self.assertEqual(self.records(m), [], "a last record exists while a step waits")
        m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "connected", "name": "demo"}})
        done = m.resume()
        self.assertEqual(done.ending, "complete", done.text)
        self.assertEqual(self.records(m), ["demo-record-%s.txt" % run])
        text = open(os.path.join(m.dev, self.records(m)[0])).read()
        self.assertIn("[O22] done by you, and a read checked it", text)
        self.assertIn("[P1] done:", text)
        # rendered again with every fake removed, from the manifest and the journal alone: the same, byte for byte
        from sun_core import effects, journal as journalmod, state as statemod

        class Offline(object):
            pass
        offline = Offline()
        offline.manifest = json.load(open(os.path.join(m.facts.run_dir(run), "manifest-1.json")))
        records = [r for r in m.journal(run) if r["n"] < [x for x in m.journal(run) if x["kind"] == "step" and x["op"] == "L1"][0]["n"]]
        offline.journal = journalmod.Journal(m.facts.run_dir(run), records)
        offline.state = statemod.State(offline.manifest, offline.journal)
        offline.run_dir = m.facts.run_dir(run)
        self.assertEqual(effects.last_record(offline), text)
        self.assertEqual(len([r for r in m.journal(run) if r["kind"] == "completion" and r["op"] == "L1"]), 1)

    def reach_publish(self):
        m = self.fresh(self.lane_rows())
        m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "connected", "name": "demo"}})
        looked = m.look(kind="sunset")
        run = looked.doc["run"]
        went = m.go(looked, kind="sunset", kill=at("post", "rename", "demo-record-%s.txt" % run))
        self.assertTrue(went.killed, went.text)
        self.assertEqual(self.records(m), ["demo-record-%s.txt" % run])
        return m, run

    def test_KEEP5_a_kill_between_the_publish_and_its_completion_is_confirmed_on_resume_with_no_second_publish(self):
        m, run = self.reach_publish()
        before = open(os.path.join(m.dev, self.records(m)[0]), "rb").read()
        resumed = m.resume()
        self.assertEqual(resumed.ending, "complete", resumed.text)
        self.assertEqual(self.records(m), ["demo-record-%s.txt" % run])
        self.assertEqual(open(os.path.join(m.dev, self.records(m)[0]), "rb").read(), before)
        self.assertEqual([r["ground"] for r in m.journal(run) if r["kind"] == "completion" and r["op"] == "L1"], ["b"])
        # a lock's record put at its place is a rename in the tool's own folder (A41), and no publish
        self.assertEqual(len([e for e in resumed.events if e["op"] == "rename" and not e["subject"].startswith(m.facts.locks_dir)]), 0,
                         "the entry was published a second time")

    def test_KEEP5_D16_an_entry_damaged_after_its_publish_leaves_the_run_stopped_untouched_and_only_resume_and_close_go_on(self):
        m, run = self.reach_publish()
        path = os.path.join(m.dev, self.records(m)[0])
        with open(path, "a") as fh:
            fh.write("a line someone added\n")
        damaged = open(path, "rb").read()
        resumed = m.resume()
        self.assertEqual(resumed.ending, "stopped", resumed.text)
        self.assertIn("stopped: the entry is at its place and unconfirmed", resumed.lines)
        self.assertEqual(open(path, "rb").read(), damaged, "the tool rewrote or removed a published entry")
        form = open(resumed.doc["forms"][0]).read()
        self.assertIn("the ways on: resume, close", form)
        self.assertNotIn("re-plan", form.split("the ways on:")[-1])
        manifests = sorted(n for n in os.listdir(m.facts.run_dir(run)) if n.startswith("manifest"))
        replanned = m.summon("replan", "demo", "--inputs", m.inputs())
        self.assertEqual(replanned.lines[0], texts.UNCONFIRMED_NO_REPLAN)
        self.assertEqual(sorted(n for n in os.listdir(m.facts.run_dir(run)) if n.startswith("manifest")), manifests, "a re-plan was made")
        self.assertEqual(m.summon("close", "demo", "--word", "close").ending, "closed")
        self.assertEqual(open(path, "rb").read(), damaged)

    # the register entry, by the hosting token's channel at one invocation alone, as SEC-3's test line plants it: a base
    # name's value (the user's name), and a part of the temporary folder's path; each makes the runner refuse every child
    REFUSING = (("the user's name", {"USER": "zzuserq9", "FAKEHOST_TOKEN": "zzuserq9"}),
                ("a part of the temporary folder's path", {"FAKEHOST_TOKEN": os.sep + "runs" + os.sep}))

    def latest_status_form(self, m, run):
        folder = os.path.join(m.facts.run_dir(run), "forms")
        names = [n for n in os.listdir(folder) if n.startswith("status-") and n.endswith(".txt")]
        return open(os.path.join(folder, max(names, key=lambda n: int(n[len("status-"):-len(".txt")])))).read()

    def test_KEEP5_A98_SEC3_a_refused_after_check_of_a_landed_entry_names_the_refusal_beside_the_entry_unconfirmed_and_the_next_resume_confirms_it(self):
        """KEEP-5 (batch 42, A98): "An after-check of the entry that the runner refuses is one that cannot confirm it: the
        form says both, the refusal by name (SEC-3) beside the entry at its place and unconfirmed, and the ways on stay
        resume and close." Its test line: "A refused after-check: the kill falls between the publish and the completion
        record, and the resume's probe finds the entry `landed`; its after-check reads through the runner, and a value that
        only that invocation's register holds makes the runner refuse it; the run ends `stopped` with no completion recorded
        and no second publish, its form naming the refusal and the entry at its place and unconfirmed, the ways on resume and
        close and no re-plan; the next resume, its register without that value, confirms the one entry and ends the run
        `complete`." The entry's after-check also asks the fake host (`noop`), a child; the fake host's identity read is
        `none`, so that the after-check's child is the resume's first."""
        from sun_core import texts
        for label, env in self.REFUSING:
            with self.subTest(entry=label):
                self.count += 1
                m = harness.Machine(self.tmp, "r%d" % self.count, "r%d" % self.count)
                providers = rowlib.providers()
                providers["fakehost"]["identity"] = rowlib.NONE
                last = rowlib.last_record("L1", P[3])
                last["commands"] = [rowlib.use("ping", "fakehost.noop")]
                last["after_check"] = last["after_check"] + [{"read": "command", "command": "ping", "result": "success"}]
                rowlib.install(m, rowlib.lane("sunset", [rowlib.check("K1", P[0]), last], phases=P), providers=providers)
                looked = m.look(kind="sunset")
                self.assertEqual(looked.ending, "preview", looked.text)
                run = looked.doc["run"]
                went = m.go(looked, kind="sunset", kill=at("post", "rename", "demo-record-%s.txt" % run))
                self.assertTrue(went.killed, went.text)
                self.assertEqual(self.records(m), ["demo-record-%s.txt" % run])
                path = os.path.join(m.dev, self.records(m)[0])
                published = open(path, "rb").read()
                calls = len(m.calls("fakehost"))
                resumed = m.resume(env=env)
                self.assertEqual(resumed.ending, "stopped", resumed.text)
                self.assertNotIn(texts.DEFECT, resumed.text, "an exception was reported")
                self.assertIn("stopped: the entry is at its place and unconfirmed", resumed.lines)
                form = self.latest_status_form(m, run)       # by listing: its path in the output may give way to the fixed words
                stop = [line for line in form.splitlines() if line.startswith("stopped: ")]
                self.assertEqual(len(stop), 1, form)
                self.assertIn("the entry is at its place and unconfirmed", stop[0])
                self.assertIn("the runner refused the command: register entry", stop[0], "the form does not name the refusal")
                self.assertIn(path, stop[0], "the form does not name the entry's place")
                self.assertTrue(stop[0].endswith("the ways on: resume, close"), stop[0])
                self.assertEqual([e for e in resumed.events if e["op"] == "child" and e["stage"] == "pre"], [], "a child was created")
                self.assertEqual(len(m.calls("fakehost")), calls, "the fake recorded a call")
                self.assertNotIn(env["FAKEHOST_TOKEN"], resumed.text)
                self.assertNotIn(env["FAKEHOST_TOKEN"], form)
                self.assertEqual([r for r in m.journal(run) if r.get("op") == "L1" and r["kind"] in ("completion", "status")], [],
                                 "a completion or a status was recorded")
                self.assertEqual(self.records(m), ["demo-record-%s.txt" % run], "a second entry was published")
                self.assertEqual(open(path, "rb").read(), published, "the entry was rewritten")
                self.assertEqual(len([e for e in resumed.events if e["op"] == "rename" and not e["subject"].startswith(m.facts.locks_dir)]),
                                 0, "the entry was published a second time")
                manifests = sorted(n for n in os.listdir(m.facts.run_dir(run)) if n.startswith("manifest"))
                replanned = m.summon("replan", "demo", "--inputs", m.inputs())
                self.assertEqual(replanned.lines[0], texts.UNCONFIRMED_NO_REPLAN, "a re-plan was let through")
                self.assertEqual(sorted(n for n in os.listdir(m.facts.run_dir(run)) if n.startswith("manifest")), manifests)
                self.assertEqual(m.summon("status").ending, "stopped")
                status = self.latest_status_form(m, run)
                self.assertIn("the runner refused the command: register entry", status, "a later status form does not name it")
                confirmed = m.resume()                       # its register without that value
                self.assertEqual(confirmed.ending, "complete", confirmed.text)
                self.assertEqual(self.records(m), ["demo-record-%s.txt" % run])
                self.assertEqual(open(path, "rb").read(), published)
                self.assertEqual([r["ground"] for r in m.journal(run) if r["kind"] == "completion" and r["op"] == "L1"], ["b"])
                self.assertEqual(len(m.calls("fakehost", "noop")), 1, "the after-check's child was not started once")

    def test_KEEP5_each_run_adds_its_own_entry_and_an_earlier_runs_entry_is_no_collision(self):
        self.count += 1
        m = harness.Machine(self.tmp, "two", "two")
        rowlib.install(m, rowlib.lane("sunset", [rowlib.check("K1", P[0]), rowlib.last_record("L1", P[3])], phases=P))
        first_run, first = self.run_sunset(m)
        self.assertEqual(first.ending, "complete", first.text)
        first_bytes = open(os.path.join(m.dev, self.records(m)[0]), "rb").read()
        second_run, second = self.run_sunset(m)
        self.assertEqual(second.ending, "complete", second.text)
        self.assertEqual(self.records(m), sorted(["demo-record-%s.txt" % first_run, "demo-record-%s.txt" % second_run]))
        self.assertEqual(open(os.path.join(m.dev, "demo-record-%s.txt" % first_run), "rb").read(), first_bytes)

    def test_KEEP5_a_last_record_that_is_not_alone_in_the_last_phase_fails_the_build(self):
        self.count += 1
        m = harness.Machine(self.tmp, "bad", "bad")
        rowlib.install(m, rowlib.lane("sunset", [rowlib.last_record("L1", P[3]), rowlib.check("K1", P[3])], phases=P))
        failed = m.look(kind="sunset")
        self.assertEqual(failed.code, 4)
        self.assertIn("a run's last record is alone in the last phase (KEEP-5)", json.dumps(failed.doc["findings"]))


if __name__ == "__main__":
    unittest.main()
