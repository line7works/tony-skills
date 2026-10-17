"""A restore's own look (the frame's EV-5, EV-7, FORM-3; LOG-1's record of a run's opening; RISK-1's RK14), on fakes.

EV-7: "A retiring run is a sunset. The look tells one among the key's earlier runs by the kind its journal's record of
its opening names (LOG-1), and uses that kind only once it has read that run as SEC-12 has another run's journal read
... Of the runs so read, the latest sunset is the retiring run EV-5 builds from: the one whose record of its opening
holds the latest time of go (LOG-1). The machine's clock orders a project's runs (the owner's ruling, A68); where it was
set back between two runs of the project, the later run reads as the earlier one, which is RK14 (RISK-1). Where two
sunsets carry the same time and no sunset a later one, the look cannot tell which is the latest, no rule picks one, and
it stops (GOV-1)".

The fixture's sunsets move files of the developer root (C7, each row declaring its way back, a move back); which sunset
a restore builds from is read from its manifest: the reverses it offers are that sunset's.
"""
import json
import os

import harness
import rowlib
from sun_core import plan, texts

P = plan.RETIREMENT_PHASES
BACK = "putting back"
LAST = "the last record"


def clock_at(tick):
    """What the fixture's clock gives at its `tick`-th reading (`harness.Machine.now`)."""
    return "2026-01-01T00:%02d:%02dZ" % (tick // 60 % 60, tick % 60)


def mover(rid, stem):
    """A sunset's move of `dev/<stem>.md` to `dev/<stem>-moved.md`, its way back a move back in the restore's phase."""
    forward = rowlib.move(rid, P[1], source=rowlib.path(rowlib.DEV, stem + ".md"), target=rowlib.path(rowlib.DEV, stem + "-moved.md"),
                          output="moved " + stem)
    forward["way_back"]["reverse"]["phase"] = BACK
    forward["way_back"]["reverse"]["output"] = {"name": "back " + stem, "fields": {}}
    return forward


def restore_lane(rows=(), phases=(BACK,)):
    return rowlib.lane("restore", list(rows), phases=phases)


def changing_calls(m):
    return [c for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold") for c in m.calls(tool) if c.get("changing")]


def manifest_of(m, run_id, number=1):
    with open(os.path.join(m.facts.run_dir(run_id), "manifest-%d.json" % number)) as fh:
        return json.load(fh)


def form_text(m, result):
    out = ""
    for path in (result.doc or {}).get("forms") or []:
        with open(path) as fh:
            out += fh.read()
    return out


class RestoreCase(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.count = 0

    def fresh(self):
        self.count += 1
        m = harness.Machine(self.tmp, "r%d" % self.count, "r%d" % self.count)
        rowlib.install(m, restore_lane())
        return m

    def sunset(self, m, rows, tick=None, restore=None, name="demo", ending="complete"):
        """A sunset of `rows` that has its go, the go's record of the run's opening at the fixture clock's `tick`."""
        rowlib.install(m, rowlib.lane("sunset", rows, phases=P), restore or restore_lane())
        looked = m.look(name, kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        if tick is not None:
            m.clock = tick - 1
        went = m.go(looked, name, kind="sunset")
        self.assertEqual(went.ending, ending, went.text)
        return looked.doc["run"]


class TheClock(RestoreCase):
    def test_LOG1_A68_the_record_of_a_runs_opening_names_its_kind_and_holds_the_time_the_clock_gave_at_its_go(self):
        """LOG-1's test line: "The kind: the record of the opening of a sunrise, of a sunset and of a restore each names
        that run's kind, and holds the time the fixture's clock gave at its go.\""""
        m = self.fresh()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]), restore_lane())
        looked = m.look("dawn")
        m.clock = 299
        self.assertEqual(m.go(looked, "dawn").ending, "waiting")
        opening = m.journal(looked.doc["run"])[0]
        self.assertEqual((opening["kind"], opening["run_kind"], opening["at"]), ("open", "sunrise", clock_at(300)))
        m.put("dev/a.md", "a\n")
        sunset = self.sunset(m, [mover("MA", "a")], tick=400)
        opening = m.journal(sunset)[0]
        self.assertEqual((opening["kind"], opening["run_kind"], opening["at"]), ("open", "sunset", clock_at(400)))
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        m.clock = 499
        self.assertEqual(m.go(looked, kind="restore").ending, "complete")
        opening = m.journal(looked.doc["run"])[0]
        self.assertEqual((opening["kind"], opening["run_kind"], opening["at"]), ("open", "restore", clock_at(500)))

    def test_EV7_RISK1_A68_RK14_the_latest_sunset_by_its_time_of_go_and_two_at_one_time_stop_the_look(self):
        """EV-7's test line: "The clock: two sunsets of one key have their goes at two times the fixture's clock gives in
        order, and a restore reads the one with the later time; with the fixture's clock set back between them, so that
        the second carries the earlier time, the restore reads the first (RK14); with both at one time to the clock's
        grain, the restore's look ends `refused` before any preview with the fixed words that two retirements of the
        project carry the same time, and no fake records an effect call". RISK-1's: no record carries a mark for RK14,
        "a restore that read the later of two sunsets by their times" among them."""
        for case, second_tick, reads in (("in order", 200, "MB-reverse"), ("set back", 50, "MA-reverse"), ("one time", 100, None)):
            with self.subTest(clock=case):
                m = self.fresh()
                m.put("dev/a.md", "a\n")
                m.put("dev/b.md", "b\n")
                first = self.sunset(m, [mover("MA", "a")], tick=100)
                second = self.sunset(m, [mover("MB", "b")], tick=second_tick)
                self.assertEqual(m.journal(first)[0]["at"], clock_at(100))
                self.assertEqual(m.journal(second)[0]["at"], clock_at(second_tick))
                calls, files = len(changing_calls(m)), m.snapshot("dev")
                looked = m.look(kind="restore")
                if reads is None:
                    self.assertEqual(looked.ending, "refused", looked.text)
                    self.assertIn(texts.RETIREMENTS_AT_ONE_TIME, looked.lines)
                    self.assertIn(texts.RETIREMENTS_AT_ONE_TIME, form_text(m, looked))
                    names = os.listdir(m.facts.run_dir(looked.doc["run"]))
                    self.assertFalse([n for n in names if n.startswith("manifest") or n == "journal.jsonl"], names)
                    self.assertEqual((len(changing_calls(m)), m.snapshot("dev")), (calls, files), "an effect was made")
                    continue
                self.assertEqual(looked.ending, "preview", looked.text)
                self.assertEqual([o["id"] for o in manifest_of(m, looked.doc["run"])["operations"]], [reads])
                went = m.go(looked, kind="restore")
                self.assertEqual(went.ending, "complete", went.text)
                for run in m.run_ids():
                    self.assertNotIn("RK14", json.dumps(m.journal(run)), "a record carries a mark for RK14")


def owner_with_reverse(rid, input_rel):
    """An owner step on his word whose row declares a way back, an owner step of the restore's, and the one input that
    reverse needs: a file read and saved before the step is shown (OP-9)."""
    reverse = rowlib.owner_step(rid + "-reverse", BACK, mode="on his word", safe_content={"step": "put the fixture's setting back by hand"},
                                output="back " + rid)
    return rowlib.owner_step(rid, P[2], mode="on his word", output="done " + rid, way_back={"reverse": reverse},
                             reverse_inputs=[{"read": "file", "path": rowlib.path(rowlib.DEV, input_rel), "type": "definition",
                                              "label": "what the owner's step changed"}])


class WhatARestoreOffers(RestoreCase):
    """EV-5: "A restore builds its manifest from the retiring run's journal. It offers the reverse of each operation that
    has a way back on record (EV-4) and of no other, with two additions the owner ruled (A6): for an operation that ended
    `not proven`, it lists it and offers the reverse only if the owner asks for that line in the restore's look, and every
    form then says it runs on his word and was not proven the run's; for an owner step that ended `done by owner`, in either
    mode, it offers the reverse as an owner step in the same mode, where the retiring run saved what that reverse needs
    (OP-9), and offers none where its preview said none could be. ... Everything it does not offer it lists, with the reason
    EV-4 recorded. Every reverse is an ordinary operation under every rule of this frame. A reverse that needs the output of
    a reverse that is not offered is planned by ORD-2." FORM-3: "A restore has a preview, a status form, a summary, and its
    entry in the project's record (KEEP-5)."""

    def every_status(self, m):
        """A sunset whose journal holds a `done` move with a way back (MD), a move left `not proven` (MN: killed after its
        start record, the file then moved by another actor), a `done` move whose reverse needs MN's reverse's output (MX),
        an owner step done on his word whose reverse's input was saved (OS), one previewed with no reverse (ON: its input is
        no file at the look), and a check that `passed` (KD)."""
        from test_log_op import at
        for stem in ("md", "mn", "mx"):
            m.put("dev/%s.md" % stem, stem + "\n")
        m.put("dev/os-input.txt", "the setting before\n")
        mx = mover("MX", "mx")
        mx["way_back"]["reverse"]["needs"] = [{"output": "back mn", "level": "made", "treatment": "then not applicable"}]
        rows = [rowlib.check("KD", P[0], output="checked"), mover("MD", "md"), mover("MN", "mn"), mx,
                owner_with_reverse("OS", "os-input.txt"), owner_with_reverse("ON", "on-input-absent.txt")]
        rowlib.install(m, rowlib.lane("sunset", rows, phases=P), restore_lane([rowlib.last_record("L1", LAST)], phases=(BACK, LAST)))
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("no reverse can be offered for this step", open(looked.doc["forms"][0]).read())
        went = m.go(looked, kind="sunset", kill=at("post", "journal", "start", "MN"))
        self.assertTrue(went.killed, went.text)
        os.rename(m.path("dev", "mn.md"), m.path("dev", "mn-moved.md"))           # another actor finishes the move
        self.assertEqual(m.resume().ending, "waiting")
        self.assertEqual(m.resume("demo", None, "--done", "OS").ending, "waiting")
        self.assertEqual(m.resume("demo", None, "--done", "ON").ending, "complete")
        sunset = looked.doc["run"]
        self.assertEqual(m.statuses(sunset), {"KD": "passed", "MD": "done", "MN": "not proven", "MX": "done",
                                              "OS": "done by owner, on his word", "ON": "done by owner, on his word"})
        return sunset

    def test_EV5_FORM3_the_restore_offers_the_reverses_on_record_and_lists_the_rest_with_their_reasons(self):
        """EV-5's test line: "from a sunset journal holding one operation of each final status, the restore's manifest holds
        the reverse of the `done` operation with a way back, the `not proven` reverse only with the owner's answer and with
        its form line saying so, the owner step's reverse as an owner step where its inputs were saved and none for an owner
        step previewed as having no reverse, and no other; ... a reverse that needs the output of one not offered is settled
        as ORD-2's test line says." FORM-3's: "its preview lists exactly the reverses EV-5 offers and, with its reason, each
        operation not offered"."""
        m = self.fresh()
        self.every_status(m)
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual([o["id"] for o in manifest["operations"]], ["MD-reverse", "OS-reverse", "L1"])
        owner = [o for o in manifest["operations"] if o["id"] == "OS-reverse"][0]
        self.assertEqual((owner["kind"], owner["resolved_mode"]), ("owner step", "on his word"))
        self.assertEqual(sorted((i["row"], i["reason"]) for i in manifest["not_offered"]),
                         [("KD", "the row declares none"), ("MN", "not proven"), ("ON", "an input is missing")])
        self.assertEqual([(s["operation"], s["treatment"]) for s in manifest["settled_needs"]], [("MX-reverse", "left out")])
        preview = form_text(m, looked)
        for row, reason, what in (("KD", "the row declares none", "the fake row KD"), ("MN", "not proven", "the fake row MN"),
                                  ("ON", "an input is missing", "the fake row ON")):
            self.assertIn(rowlib.FORM_CHANGES["not offered"].format(reason=reason, what=what), preview)
        self.assertNotIn("not proven the retirement's", preview)
        asked = m.look(kind="restore", inputs=m.inputs(name="asked.json", restore_lines=["MN"]))
        self.assertEqual(asked.ending, "preview", asked.text)
        manifest = manifest_of(m, asked.doc["run"])
        self.assertEqual([o["id"] for o in manifest["operations"]], ["MD-reverse", "MN-reverse", "MX-reverse", "OS-reverse", "L1"])
        self.assertTrue([o for o in manifest["operations"] if o["id"] == "MN-reverse"][0].get("not_proven"))
        preview = form_text(m, asked)
        self.assertIn(rowlib.FORM_CHANGES["not proven, on his word"].format(what="the fake row MN-reverse"), preview)
        self.assertEqual(sorted(i["row"] for i in manifest["not_offered"]), ["KD", "ON"])

    def test_FORM3_EV5_a_restore_renders_its_preview_its_status_form_its_summary_and_its_entry(self):
        """FORM-3's test line: "a restore run renders each of the four; its preview lists exactly the reverses EV-5 offers
        and, with its reason, each operation not offered; each of the four holds, for every status that occurred in that
        restore, the line FORM-2 or the lane's list of form changes gives it." The summary is the status form its ending
        renders; the entry is its last record (KEEP-5), rendered from its journal alone."""
        m = self.fresh()
        self.every_status(m)
        looked = m.look(kind="restore", inputs=m.inputs(name="asked.json", restore_lines=["MN"]))
        restore = looked.doc["run"]
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "waiting", went.text)
        waiting = form_text(m, went)
        self.assertIn("[OS-reverse] waiting on you: put the fixture's setting back by hand; mode: on his word", waiting)
        self.assertIn("[MD-reverse] done: the fake row MD-reverse", waiting)
        self.assertIn(rowlib.FORM_CHANGES["not proven, on his word"].format(what="the fake row MN-reverse"), waiting)
        done = m.resume("demo", None, "--done", "OS-reverse")
        self.assertEqual(done.ending, "complete", done.text)
        summary = form_text(m, done)
        entry_path = os.path.join(m.dev, "demo-record-%s.txt" % restore)
        entry = open(entry_path).read()
        for text in (summary, entry):
            for op in ("MD-reverse", "MN-reverse", "MX-reverse"):
                self.assertIn("[%s] done: the fake row %s" % (op, op), text)
            self.assertIn("[OS-reverse] done by you, on your word; no read checked it: the fake row OS-reverse", text)
            self.assertIn(rowlib.FORM_CHANGES["not proven, on his word"].format(what="the fake row MN-reverse"), text)
        for stem in ("md", "mn", "mx"):
            self.assertTrue(os.path.isfile(m.path("dev", stem + ".md")), stem)


def read_journals(m, result):
    """The run directories whose journal the invocation read whole."""
    out = set()
    for e in result.events:
        subject = str(e.get("subject"))
        if e["stage"] == "read" and e["op"] == "read" and subject.endswith(os.sep + "journal.jsonl"):
            out.add(os.path.basename(os.path.dirname(subject)))
    return sorted(out)


class TheRetiringRun(RestoreCase):
    """EV-7: which run a restore builds from, the stops of its look, and a retirement a restore has closed."""

    def test_EV7_GOV1_no_retiring_run_ends_the_look_refused_and_a_replan_stopped(self):
        """EV-7's test line: "No retiring run: that restore's look ends `refused` before any preview, with no manifest and no
        journal written and its form holding the fixed words that no retiring run of the project is found; so does a restore
        summoned under a name whose key has no earlier run, and one under a name whose key's one earlier run is a sunrise; in
        each, no fake records an effect call (GOV-1). A re-plan: a restore that has its go stops; the fixture's owner then
        moves the sunset's run directory out of the folder of run directories; the look of a re-plan ends `stopped`, with the
        manifest in force byte-equal, its form holding the same fixed words, and no fake records an effect call." (The pass
        after a new keying value is `test_run`'s `test_RUN5_EV7_after_a_new_keying_value_...`.)"""
        m = self.fresh()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]), restore_lane())
        self.assertEqual(m.started("dawn")[1].ending, "waiting")
        self.assertEqual(m.summon("close", "dawn", "--word", "close").ending, "closed")
        for name in ("nobody", "dawn"):
            with self.subTest(name=name):
                refused = m.look(name, kind="restore")
                self.assertEqual(refused.ending, "refused", refused.text)
                self.assertIn(texts.NO_RETIRING_RUN, refused.lines)
                self.assertIn(texts.NO_RETIRING_RUN, form_text(m, refused))
                names = os.listdir(m.facts.run_dir(refused.doc["run"]))
                self.assertFalse([n for n in names if n.startswith("manifest") or n == "journal.jsonl"], names)
                self.assertEqual(changing_calls(m), [])
        m.put("dev/a.md", "a\n")
        sunset = self.sunset(m, [mover("MA", "a")])
        failing = rowlib.check("K9", BACK, place=rowlib.path(rowlib.DEV, "absent-folder"))
        rowlib.install(m, restore_lane([failing]))
        looked = m.look(kind="restore")
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "stopped", went.text)
        restore_dir = m.facts.run_dir(looked.doc["run"])
        manifests = dict((n, open(os.path.join(restore_dir, n), "rb").read()) for n in os.listdir(restore_dir) if n.startswith("manifest-"))
        os.rename(m.facts.run_dir(sunset), os.path.join(m.root, "moved-out"))
        replanned = m.summon("replan", "demo", "--inputs", m.inputs(name="again.json"))
        self.assertEqual(replanned.ending, "stopped", replanned.text)
        self.assertIn(texts.NO_RETIRING_RUN, replanned.lines)
        self.assertIn(texts.NO_RETIRING_RUN, form_text(m, replanned))
        self.assertEqual(dict((n, open(os.path.join(restore_dir, n), "rb").read()) for n in os.listdir(restore_dir) if n.startswith("manifest-")),
                         manifests, "the manifest in force changed")
        self.assertEqual(changing_calls(m), [])

    def test_EV7_SEC12_the_kind_a_sunrise_and_a_sunset_are_read_and_the_sunset_is_the_retiring_run(self):
        """EV-7's test line: "The kind: a key's earlier runs are a sunrise and then a sunset; a restore's look reads both
        journals, each after that run's disproof read, takes the sunset as its retiring run by the kind its record of its
        opening names, and plans from it; with a file of the sunrise's run directory given wider permissions, the restore's
        look ends as a failed read." SEC-12's row for a restore's first look: "the journals of the key's earlier runs that
        read finds, each after that run's disproof read; of the latest retiring run among them, the records EV-7 needs"
        """
        m = self.fresh()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word")]), restore_lane())
        dawn = m.started()[0].doc["run"]
        self.assertEqual(m.summon("close", "demo", "--word", "close").ending, "closed")
        m.put("dev/a.md", "a\n")
        sunset = self.sunset(m, [mover("MA", "a")])
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(read_journals(m, looked), sorted([dawn, sunset]))
        self.assertEqual([o["id"] for o in manifest_of(m, looked.doc["run"])["operations"]], ["MA-reverse"])
        self.assertEqual(manifest_of(m, looked.doc["run"])["retiring"], sunset)
        wide = os.path.join(m.facts.run_dir(dawn), "journal.jsonl")
        os.chmod(wide, 0o644)
        failed = m.look(kind="restore")
        os.chmod(wide, 0o600)
        self.assertEqual(failed.ending, "refused", failed.text)
        self.assertIn("the read failed: an earlier run's directory does not check out", failed.lines)

    def test_EV7_a_missing_protected_record_takes_only_its_dependents_out_of_the_offer(self):
        """EV-7's test line: "a missing protected record ... each take only their dependents out of the offer, with the
        reason in the preview." EV-7: "Where a protected record or a keep that the restore needs is missing or fails its
        fingerprint, the operations that need it are planned `not applicable` with that reason, and the rest are still
        offered"
        """
        m = self.fresh()
        m.put("dev/a.md", "a\n")
        m.put("dev/b.md", "b\n")
        sunset = self.sunset(m, [mover("MA", "a"), mover("MB", "b")])
        completion = [r for r in m.journal(sunset) if r["kind"] == "completion" and r["op"] == "MA"][0]
        record = completion["way_back"]["inputs"][0]["record"]
        os.remove(os.path.join(m.facts.run_dir(sunset), "protected", record))
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual([o["id"] for o in manifest["operations"]], ["MB-reverse"])
        self.assertIn({"row": "MA-reverse", "reason": "a record it needs is missing", "what": "the fake row MA-reverse"}, manifest["not_applicable"])
        self.assertIn("not applicable (a record it needs is missing): the fake row MA-reverse", form_text(m, looked))

    def test_EV5_EV3_a_reverse_whose_thing_is_not_in_the_last_tracked_state_the_retiring_journal_holds_stops(self):
        """EV-5's test line: "a reverse whose thing is not in the last tracked state the retiring journal holds stops under
        EV-3". The moved file is replaced by another file of the same name after the sunset."""
        m = self.fresh()
        m.put("dev/a.md", "a\n")
        self.sunset(m, [mover("MA", "a")])
        os.remove(m.path("dev", "a-moved.md"))
        m.put("dev/a-moved.md", "another file\n")
        files = m.snapshot("dev")
        stopped = m.look(kind="restore")
        self.assertEqual(stopped.ending, "refused", stopped.text)
        told = [l for l in stopped.lines if l.startswith("the thing is not in the last tracked state the retiring run's journal holds")]
        self.assertEqual(len(told), 1, stopped.lines)
        self.assertIn("row MA-reverse", told[0])
        self.assertIn(m.path("dev", "a-moved.md"), told[0])
        self.assertEqual(m.snapshot("dev"), files)

    def test_EV7_KEEP5_a_retirement_a_restore_closed_is_read_again_and_what_was_put_back_is_already_so(self):
        """EV-7's test line: "A retirement a restore closed: a restore over a sunset that moved a folder and changed a file has
        its go and ends `complete`; a second restore under the same name reads that sunset's journal again, its preview lists
        the move and the change `already so` and holds no reverse to run, and no fake records an effect call in its look; given
        his go, it publishes its own entry once where the fixture's lane has one, the first restore's entry staying
        byte-equal, and ends `complete` with no other effect call; where the fixture's lane has no entry, it ends `complete`
        with no effect call at all". The move here is of a file (`rowlib.move` moves what stands at a path); the change takes
        the alias line out of the shortcut file, its way back the line put back at the end (EV-6). Not built here: the
        sub-case "with the sunset having also removed a file that the first restore put back" (no reverse that makes a file
        from a record is built in this part)."""
        m = self.fresh()
        m.put("dev/a.md", "a\n")
        m.put("shortcuts.txt", "alias other\nalias demo\n")
        put_back = rowlib.swap_add("S1", phase=BACK)
        put_back.update(way_back={"none": "the row declares none: it is itself a reverse"}, reverse_inputs="none", span="none")
        removal = rowlib.swap_add("T11", phase=P[1])["way_back"]["reverse"]
        removal.update(id="T11", phase=P[1], way_back={"reverse": put_back}, span={"placement": "at the end", "ordered": False},
                       reverse_inputs=[{"read": "file", "path": {"location": "shortcut_file"}, "type": "before-image",
                                        "label": "the shortcut file before the line was taken out"}])
        with_entry = restore_lane([rowlib.last_record("L1", LAST)], phases=(BACK, LAST))
        sunset = self.sunset(m, [mover("MA", "a"), removal], restore=with_entry)
        first = m.look(kind="restore")
        self.assertEqual([o["id"] for o in manifest_of(m, first.doc["run"])["operations"]], ["MA-reverse", "S1", "L1"])
        self.assertEqual(m.go(first, kind="restore").ending, "complete")
        self.assertEqual(open(m.path("shortcuts.txt")).read(), "alias other\nalias demo\n")
        first_entry = os.path.join(m.dev, "demo-record-%s.txt" % first.doc["run"])
        entry_bytes = open(first_entry, "rb").read()
        files = m.snapshot()
        second = m.look(kind="restore")
        self.assertEqual(second.ending, "preview", second.text)
        self.assertIn(sunset, read_journals(m, second), "the retirement's journal is not read again")
        manifest = manifest_of(m, second.doc["run"])
        self.assertEqual([o["id"] for o in manifest["operations"]], ["L1"])
        self.assertEqual(sorted(i["row"] for i in manifest["already_so"]), ["MA-reverse", "S1"])
        preview = form_text(m, second)
        for what in ("the fake row MA-reverse", "the fake row S1"):
            self.assertIn("found already so; a restore will not reverse it: " + what, preview)
        self.assertEqual(changing_calls(m), [])
        went = m.go(second, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(open(first_entry, "rb").read(), entry_bytes, "the first restore's entry changed")
        after = m.snapshot()
        added = sorted(k for k in after if k not in files and not k.startswith(".sun-v2"))
        self.assertEqual(added, [os.path.join("dev", "demo-record-%s.txt" % second.doc["run"])], "not one entry, published once")
        self.assertEqual(dict((k, v) for k, v in after.items() if k in files and not k.startswith(".sun-v2")),
                         dict((k, v) for k, v in files.items() if not k.startswith(".sun-v2")), "something else changed")
        rowlib.install(m, restore_lane([], phases=(BACK,)))
        files = m.snapshot()
        third = m.look(kind="restore")
        self.assertEqual([o["id"] for o in manifest_of(m, third.doc["run"])["operations"]], [])
        went = m.go(third, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(dict((k, v) for k, v in m.snapshot().items() if not k.startswith(".sun-v2")),
                         dict((k, v) for k, v in files.items() if not k.startswith(".sun-v2")), "an effect was made")
        self.assertEqual(changing_calls(m), [])


class TheLookAsBatch30WordsIt(RestoreCase):
    """EV-4, EV-5 and EV-7 as the frame's batch 30 words them (A75)."""

    def test_EV5_EV4_batch30_an_operation_with_no_final_record_and_a_change_ended_not_needed_are_listed_with_their_reasons(self):
        """EV-5: "An operation of the retiring run's manifest in force that has no final record in its journal is listed
        too, with the tool's fixed words that it was not run to its end and that no way back is on record for it." Its test
        line: "an operation the sunset's manifest holds and its journal shows no final record for is listed as not offered,
        with the fixed words, and a change that ended `not needed` is listed with that reason"."""
        m = self.fresh()
        words = getattr(texts, "NOT_RUN_TO_ITS_END", "<no fixed words for an operation not run to its end>")
        m.put("dev/mn.md", "mn\n")
        q = rowlib.create("Q", P[1], output="first try")
        q["construction"]["alternatives"] = ["terms"]
        mn = mover("MN", "mn")
        mn["condition"] = {"on": "alternative", "operation": "Q", "result": "terms"}
        ow = rowlib.owner_step("OW", P[2], mode="on his word", output="done OW")
        sunset = self.sunset(m, [q, mn, ow], ending="waiting")
        self.assertEqual(m.statuses(sunset), {"Q": "done", "MN": "not needed"})
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual([o["id"] for o in manifest["operations"]], [])
        self.assertEqual(sorted((i["row"], i["reason"]) for i in manifest["not_offered"]),
                         [("MN", "not needed"), ("OW", words), ("Q", "the row declares none")])
        preview = form_text(m, looked)
        for reason, what in (("not needed", "the fake row MN"), (words, "the fake row OW")):
            self.assertIn(rowlib.FORM_CHANGES["not offered"].format(reason=reason, what=what), preview)

    def test_EV7_batch30_an_open_retirement_that_is_not_the_latest_by_the_clock_ends_the_look_refused(self):
        """EV-7's test line: "with a first sunset ended, the fixture's clock then set back, and a second sunset that goes at
        an earlier time left `stopped`, a restore's look ends `refused` before any preview with the fixed words that an open
        retirement of the project is not its latest by the clock, both sunsets' journals byte-equal and no `closed` record
        written, and no fake records an effect call; once the open one is closed by the fixture's owner, the restore builds
        from the first (RK14).\""""
        m = self.fresh()
        words = getattr(texts, "OPEN_RETIREMENT_NOT_LATEST", "<no fixed words for an open retirement that is not the latest>")
        m.put("dev/a.md", "a\n")
        m.put("dev/b.md", "b\n")
        first = self.sunset(m, [mover("MA", "a")], tick=100)
        failing = rowlib.check("K9", P[0], place=rowlib.path(rowlib.DEV, "absent-folder"))
        second = self.sunset(m, [failing, mover("MB", "b")], tick=50, ending="stopped")
        journals = dict((run, open(os.path.join(m.facts.run_dir(run), "journal.jsonl"), "rb").read()) for run in (first, second))
        calls, files = len(changing_calls(m)), m.snapshot("dev")
        refused = m.look(kind="restore")
        self.assertEqual(refused.ending, "refused", refused.text)
        self.assertIn(words, refused.lines)
        self.assertIn(words, form_text(m, refused))
        names = os.listdir(m.facts.run_dir(refused.doc["run"]))
        self.assertFalse([n for n in names if n.startswith("manifest") or n == "journal.jsonl"], names)
        self.assertEqual(dict((run, open(os.path.join(m.facts.run_dir(run), "journal.jsonl"), "rb").read()) for run in (first, second)),
                         journals, "a journal changed")
        self.assertEqual((len(changing_calls(m)), m.snapshot("dev")), (calls, files), "an effect was made")
        self.assertEqual(m.summon("close", "demo", "--word", "close").ending, "closed")
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(manifest_of(m, looked.doc["run"])["retiring"], first)
        self.assertEqual([o["id"] for o in manifest_of(m, looked.doc["run"])["operations"]], ["MA-reverse"])

    def test_EV5_EV3_batch30_a_reverse_whose_thing_changes_after_the_look_stops_at_its_turn(self):
        """EV-5's test line: "a reverse whose thing, at the restore's look, is in neither the state the retiring journal last
        tracked for it nor the reverse's after-state ends the look as RUN-7's planning stop, `refused` before a first go, and
        one whose thing changes after the look stops at its turn under EV-3". The first half is
        `TheRetiringRun.test_EV5_EV3_...`; here the moved file is replaced by another of the same name after the restore's
        look and before its go."""
        m = self.fresh()
        m.put("dev/a.md", "a\n")
        self.sunset(m, [mover("MA", "a")])
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        os.remove(m.path("dev", "a-moved.md"))
        m.put("dev/a-moved.md", "another file\n")
        files = m.snapshot("dev")
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: foreign", went.lines)
        self.assertIn("operation: MA-reverse", went.lines)
        self.assertIn("the staged document, %s" % m.path("dev", "a-moved.md"), form_text(m, went))
        self.assertEqual(m.snapshot("dev"), files, "the thing was moved")
        self.assertNotIn("MA-reverse", m.statuses(looked.doc["run"]))


class ARestoreOverACaughtSunset(RestoreCase):
    """SEC-12's test line, "The disproof", its second fixture: "a fixture run has its go; its saved inputs, its manifest and
    its journal hold a name the owner typed and a path the tool built from it. A fake then returns that name in a secret
    field ... and the run is `stopped`. Each of these then passes its startup checks: ...; and, in a second fixture that is a
    sunset, the first look of a restore over it. In every one the name is in no output, form, error, new record or argument,
    alone or inside the path ... The restore plans the reverses whose inputs hold the name `not applicable`, with that
    reason, and offers the rest. The same six are run after a kill between the protected record and the disproof record:
    each withholds the name all the same ... With the protected record removed, ... each that reads it from another run ends
    its look as a failed read." SEC-12, "Another run's journal": "A restore plans an operation that would need such content
    `not applicable`, with that reason, and still offers the rest (the owner's ruling, A26; EV-7)."""

    NAME = "tidetablename"

    def caught_sunset(self, m, kill=False):
        m.put("dev/%s.md" % self.NAME, "a\n")
        m.put("dev/b.md", "b\n")
        built = {"text": [{"input": "description"}, rowlib.lit(".md")]}
        moved = {"text": [{"input": "description"}, rowlib.lit("-moved.md")]}
        ma = rowlib.move("MA", P[1], source=rowlib.path(rowlib.DEV, built), target=rowlib.path(rowlib.DEV, moved), output="moved a")
        ma["way_back"]["reverse"]["phase"] = BACK
        ma["way_back"]["reverse"]["output"] = {"name": "back a", "fields": {}}
        rows = [ma, mover("MB", "b"), rowlib.secret_op("X1", P[2])]
        rowlib.install(m, rowlib.lane("sunset", rows, phases=P), restore_lane())
        looked = m.look("demo", kind="sunset", inputs=m.inputs(description=self.NAME))
        self.assertEqual(looked.ending, "preview", looked.text)
        m.plan_fake("fakehost", {"command": "issue", "nth": 1, "value": self.NAME})
        seen = {"due": False}

        def hook(e):
            if e["stage"] == "post" and e["op"] == "journal" and str(e["subject"]).endswith("step") and e.get("operation") == "X1":
                seen["due"] = True
            return seen["due"] and e["stage"] == "post" and e["op"] == "create" and os.sep + "protected" + os.sep in str(e["subject"])
        went = m.go(looked, "demo", kind="sunset", kill=hook if kill else None)
        if kill:
            self.assertTrue(went.killed, went.text)
        else:
            self.assertEqual(went.ending, "stopped", went.text)
            self.assertIn("stopped: a safe ground disproved", went.lines)
        self.assertEqual((m.statuses(looked.doc["run"]).get("MA"), m.statuses(looked.doc["run"]).get("MB")), ("done", "done"))
        return looked.doc["run"]

    def nowhere_in_the_restore(self, m, result):
        self.assertNowhere(self.NAME, result)
        restore_dir = m.facts.run_dir(result.doc["run"])
        for root, _dirs, files in os.walk(restore_dir):
            for name in files:
                with open(os.path.join(root, name), "rb") as fh:
                    self.assertNotIn(self.NAME.encode("utf-8"), fh.read(), "a new record of the restore holds the name: " + name)
        for call in [c for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold") for c in m.calls(tool)]:
            self.assertNotIn(self.NAME, json.dumps(call.get("argv")), "an argument holds the name")

    def test_SEC12_A26_EV7_the_first_look_of_a_restore_over_a_caught_sunset_plans_the_reverse_whose_input_holds_it_not_applicable(self):
        for kill in (False, True):
            with self.subTest(killed_between_the_protected_record_and_the_disproof_record=kill):
                m = self.fresh()
                sunset = self.caught_sunset(m, kill)
                looked = m.look(kind="restore")
                self.assertEqual(looked.ending, "preview", looked.text)
                manifest = manifest_of(m, looked.doc["run"])
                self.assertEqual([o["id"] for o in manifest["operations"]], ["MB-reverse"])
                self.assertIn({"row": "MA-reverse", "reason": "it would carry a value this tool may not show", "what": "the fake row MA-reverse"},
                              manifest["not_applicable"])
                self.assertIn("not applicable (it would carry a value this tool may not show): the fake row MA-reverse", form_text(m, looked))
                self.nowhere_in_the_restore(m, looked)
                if kill:
                    continue
                # the protected record the disproof record names, removed: the restore's read of that run fails
                disproof = [r for r in m.journal(sunset) if r["kind"] == "disproof"][0]
                os.remove(os.path.join(m.facts.run_dir(sunset), "protected", disproof["rests"]["protected"]["record"]))
                failed = m.look(kind="restore")
                self.assertEqual(failed.ending, "refused", failed.text)
                self.assertIn("the read failed: an earlier run's record of a withheld value cannot be read", failed.lines)
                self.nowhere_in_the_restore(m, failed)


class AReverseThatCopiesFromAKeep(RestoreCase):
    """EV-5: "It may copy from a keep (KEEP-4)." EV-7: "Where a protected record or a keep that the restore needs is missing
    or fails its fingerprint, the operations that need it are planned `not applicable` with that reason, and the rest are
    still offered"; its test line: "a missing protected record, and a keep whose fingerprint no longer matches, each take
    only their dependents out of the offer, with the reason in the preview", and "with the sunset having also removed a file
    that the first restore put back, the second restore's look ends as a planning stop that names that place as taken".
    SEC-7, a restore's row: "the working memory store copied back from its keep | new files: staged and published by C1 at
    the original place, which must be empty of anything; with the permissions recorded at the retirement, never wider"; its
    test line: "a link planted at any of them fails the operation with nothing written through it". KEEP-4: "No operation of
    any run changes, moves or removes a keep." The fixture's store is a file the sunset keeps (the fake dump) and then moves
    away; its way back is a build that copies the store back from that keep."""

    def store_sunset(self, m, extra=()):
        m.put("dev/demo.env", "DATABASE_URL=postgres://app:%s@db.fixture.invalid/app\n" % harness.canary("keep-copy"), 0o600)
        m.put("dev/demo-store.txt", "the store\n", 0o640)
        source = rowlib.path(rowlib.DEV, "demo-store.txt")
        back = rowlib.row("build", "MS-reverse", BACK,
                          thing={"role": "the store, copied back from its keep", "identity": "path", "place": source, "tracked": ["exists", "identity"]},
                          planning_test=[{"read": "path", "path": source, "is": "absent"}],
                          before_test=[{"id": "free", "read": "path", "path": source, "is": "absent"}],
                          after_test=[{"read": "path", "path": source, "is": "file"}],
                          construction={"id": "C1", "from_keep": "P1", "single_file": True},
                          after_check=[{"read": "path", "path": source, "is": "file"}],
                          output={"name": "back store", "fields": {"path": source}})
        ms = rowlib.move("MS", P[1], source=source, target=rowlib.path(rowlib.DEV, "demo-store-moved.txt"), output="moved store")
        ms["thing"]["tracked"] = ["exists", "identity", "mode"]
        ms["way_back"]["reverse"] = back
        return self.sunset(m, [rowlib.keep("P1", P[0]), ms] + list(extra))

    def test_EV5_KEEP4_SEC7_EV7_a_reverse_copies_the_store_back_from_its_keep_and_a_second_restore_finds_its_place_taken(self):
        m = self.fresh()
        sunset = self.store_sunset(m)
        keep_path = m.path("dev", "demo-dump.txt")
        keep_bytes = open(keep_path, "rb").read()
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual([o["id"] for o in manifest_of(m, looked.doc["run"])["operations"]], ["MS-reverse"])
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        store = m.path("dev", "demo-store.txt")
        self.assertEqual(open(store, "rb").read(), keep_bytes, "the store is not the keep's copy")
        self.assertEqual(os.stat(store).st_mode & 0o777, 0o640, "not the permissions recorded at the retirement")
        self.assertEqual(open(keep_path, "rb").read(), keep_bytes, "the keep changed (KEEP-4)")
        self.assertTrue(os.path.isfile(m.path("dev", "demo-store-moved.txt")))
        # a second restore: the reverse would make the store where the first restore made one; its place is taken
        files = m.snapshot("dev")
        second = m.look(kind="restore")
        self.assertEqual(second.ending, "refused", second.text)
        self.assertIn("the place is taken by a thing this run did not make: row MS-reverse", second.lines)
        self.assertIn("the place taken: %s" % store, second.lines)
        self.assertEqual(m.snapshot("dev"), files)
        self.assertEqual(changing_calls(m), [c for c in changing_calls(m) if c["argv"][0] == "dump"], "an effect of the restore was made")
        self.assertTrue(sunset)

    def test_EV7_a_keep_whose_fingerprint_no_longer_matches_takes_only_its_dependents_out_of_the_offer(self):
        m = self.fresh()
        m.put("dev/a.md", "a\n")
        self.store_sunset(m, extra=[mover("MA", "a")])
        with open(m.path("dev", "demo-dump.txt"), "ab") as fh:
            fh.write(b"one more line\n")
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual([o["id"] for o in manifest["operations"]], ["MA-reverse"])
        reason = "a keep it needs is missing or fails its fingerprint"
        self.assertIn({"row": "MS-reverse", "reason": reason, "what": "the fake row MS-reverse"}, manifest["not_applicable"])
        self.assertIn("not applicable (%s): the fake row MS-reverse" % reason, form_text(m, looked))

    def test_SEC7_a_link_planted_at_the_stores_place_fails_the_operation_with_nothing_written_through_it(self):
        m = self.fresh()
        self.store_sunset(m)
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        elsewhere = m.put("elsewhere/target.txt", "not the store\n")
        os.symlink(elsewhere, m.path("dev", "demo-store.txt"))
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(open(elsewhere).read(), "not the store\n", "something was written through the link")
        self.assertTrue(os.path.islink(m.path("dev", "demo-store.txt")))
        self.assertNotIn("MS-reverse", m.statuses(looked.doc["run"]))


def span_rows(kind, span="two", ordered=True):
    """A sunset's change of a span of a file, its way back the span put back (EV-6). `replace`: the status line of
    dev/status.txt replaced, put back where its recorded after-image occurs once. `remove`: the span `span` (one line, or
    several joined by a newline) of dev/ordered.txt taken out, put back `in place` between its recorded neighbours, and, where
    the row marks the file `ordered`, the head before them as recorded. Every value the reverse needs is an input saved by
    the forward operation (LOG-2), named in the reverse by its place among those inputs ({"saved": n}); the restore binds
    each to its own copy of that record."""
    if kind == "replace":
        f = rowlib.path(rowlib.DEV, "status.txt")
        old, new = rowlib.lit("status: live"), rowlib.lit("status: retired")
        reverse = rowlib.row("change", "RS-reverse", BACK,
                             thing={"role": "the status file", "identity": "path", "place": f, "tracked": ["exists"], "span": True},
                             planning_test=[{"read": "path", "path": f, "is": "file"}],
                             before_test=[{"id": "once", "read": "line", "path": f, "line": {"saved": 1}, "count": 1}],
                             after_test=[{"read": "line", "path": f, "line": {"saved": 0}, "count": 1},
                                         {"read": "line", "path": f, "line": {"saved": 1}, "present": False}],
                             construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace", "old": {"saved": 1}, "new": {"saved": 0}}},
                             after_check=[{"read": "line", "path": f, "line": {"saved": 0}, "count": 1}],
                             way_back={"none": "the row declares none: it is itself a reverse"}, output={"name": "back status", "fields": {}})
        return [rowlib.row("change", "RS", P[1],
                           thing={"role": "the status file", "identity": "path", "place": f, "tracked": ["exists", "sha256"], "span": True},
                           planning_test=[{"read": "path", "path": f, "is": "file"}],
                           before_test=[{"id": "has", "read": "line", "path": f, "line": old, "count": 1}],
                           after_test=[{"read": "line", "path": f, "line": new, "count": 1}],
                           construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace", "old": old, "new": new}},
                           after_check=[{"read": "line", "path": f, "line": new, "count": 1}],
                           way_back={"reverse": reverse},
                           reverse_inputs=[{"read": "value", "value": old, "type": "before-image", "label": "the status line before"},
                                           {"read": "value", "value": new, "type": "after-image", "label": "the status line after"}],
                           span={"placement": "in place", "ordered": False}, output={"name": "status", "fields": {}})]
    f = rowlib.path(rowlib.DEV, "ordered.txt")
    line = rowlib.lit(span)
    edit = {"kind": "insert-between", "line": {"saved": 0}, "above": {"saved": 1}, "below": {"saved": 2}, "ordered": bool(ordered)}
    if ordered:
        edit["head"] = {"saved": 3}
    reverse = rowlib.row("change", "RL-reverse", BACK,
                         thing={"role": "the ordered file", "identity": "path", "place": f, "tracked": ["exists"], "span": True},
                         planning_test=[{"read": "path", "path": f, "is": "file"}],
                         before_test=[{"id": "absent", "read": "line", "path": f, "line": {"saved": 0}, "present": False}],
                         after_test=[{"read": "line", "path": f, "line": {"saved": 0}, "count": 1}],
                         construction={"id": "C3", "risks": ["RK2"], "edit": edit},
                         after_check=[{"read": "line", "path": f, "line": {"saved": 0}, "count": 1}],
                         way_back={"none": "the row declares none: it is itself a reverse"}, output={"name": "back line", "fields": {}})
    return [rowlib.row("change", "RL", P[1],
                       thing={"role": "the ordered file", "identity": "path", "place": f, "tracked": ["exists", "sha256"], "span": True},
                       planning_test=[{"read": "path", "path": f, "is": "file"}],
                       before_test=[{"id": "has", "read": "line", "path": f, "line": line, "count": 1}],
                       after_test=[{"read": "line", "path": f, "line": line, "present": False}],
                       construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "remove-line", "line": line}},
                       after_check=[{"read": "line", "path": f, "line": line, "present": False}],
                       way_back={"reverse": reverse},
                       reverse_inputs=[{"read": "value", "value": line, "type": "line", "label": "the line taken out"},
                                       {"read": "line-above", "path": f, "line": line, "type": "line", "label": "the line above it"},
                                       {"read": "line-below", "path": f, "line": line, "type": "line", "label": "the line below it"}]
                       + ([{"read": "head", "path": f, "line": line, "type": "before-image", "label": "the file before the line"}] if ordered else []),
                       span={"placement": "in place", "ordered": bool(ordered)}, output={"name": "taken out", "fields": {}})]


class PuttingTextBack(RestoreCase):
    """EV-6: "A span the retiring run replaced is put back only when its recorded after-image occurs in the file exactly once;
    the recorded before-image then takes its place and nothing else in the file moves. A span the retiring run removed is put
    back by the placement its row declares. `in place`: the recorded lines on each side are found next to each other exactly
    once and, for a file the row marks as ordered (one where a line's meaning depends on what stands before it), everything
    before that point is as recorded. ... Where the declared placement cannot be met the probe answers `foreign`; the form
    names the file, the place and the protected records, and shows no text of the file or of a record." Its test line: "a
    status line the owner edited after the sunset stops the restore with nothing changed and no file text in any output; so
    does an after-image that occurs twice, and so do recorded neighbours that occur next to each other twice; a removed line
    between two different lines returns between them, and with a line inserted above it in an ordered file the restore
    stops". SEC-7: "the same | a span put back into its file (EV-6) | a swap, C3, of the file it was taken from and no other;
    the file keeps the permissions it has, never wider"."""

    TEXTS = ("status: live", "status: retired", "two", "one", "three", "zero", "four", "five")

    def stopped_with_nothing_changed(self, m, result, path, before):
        self.assertIn(result.ending, ("refused", "stopped"), result.text)
        self.assertEqual(open(path).read(), before, "the file changed")
        told = [l for l in result.lines + form_text(m, result).replace("(", "\n").replace(")", "\n").split("\n")
                if l.startswith("the declared placement cannot be met")][:1]
        self.assertEqual(len(told), 1, result.lines)
        self.assertIn(path, told[0])
        self.assertIn("p-", told[0], "the protected records are not named")
        shown = result.text + form_text(m, result)
        for text in self.TEXTS:
            self.assertNotIn(text, shown.replace(path, ""), "a text of the file or of a record is shown")

    def test_EV6_a_replaced_span_is_put_back_where_its_after_image_occurs_once_and_stops_where_edited_or_twice(self):
        for case, after_sunset in (("once", None), ("edited by the owner", "status: retired by hand\n"),
                                   ("twice", "status: retired\nstatus: retired\n")):
            with self.subTest(case=case):
                m = self.fresh()
                m.put("dev/status.txt", "head line\nstatus: live\ntail line\n", 0o640)
                self.sunset(m, span_rows("replace"))
                path = m.path("dev", "status.txt")
                self.assertEqual(open(path).read(), "head line\nstatus: retired\ntail line\n")
                if after_sunset is not None:
                    with open(path, "w") as fh:
                        fh.write("head line\n" + after_sunset + "tail line\n")
                    before = open(path).read()
                    looked = m.look(kind="restore")
                    self.stopped_with_nothing_changed(m, looked, path, before)
                    continue
                looked = m.look(kind="restore")
                self.assertEqual(looked.ending, "preview", looked.text)
                went = m.go(looked, kind="restore")
                self.assertEqual(went.ending, "complete", went.text)
                self.assertEqual(open(path).read(), "head line\nstatus: live\ntail line\n", "not put back, or something else moved")
                self.assertEqual(os.stat(path).st_mode & 0o777, 0o640, "the file's permissions changed")

    def test_EV6_a_removed_line_returns_between_its_neighbours_and_stops_where_they_occur_twice_or_the_head_changed(self):
        for case, after_sunset in (("between two different lines", None), ("neighbours next to each other twice", "one\nthree\nzero\none\nthree\n"),
                                   ("a line inserted above it in an ordered file", "zero\none\nthree\n")):
            with self.subTest(case=case):
                m = self.fresh()
                m.put("dev/ordered.txt", "one\ntwo\nthree\n")
                self.sunset(m, span_rows("remove"))
                path = m.path("dev", "ordered.txt")
                self.assertEqual(open(path).read(), "one\nthree\n")
                if after_sunset is not None:
                    with open(path, "w") as fh:
                        fh.write(after_sunset)
                looked = m.look(kind="restore")
                self.assertEqual(looked.ending, "preview", looked.text)
                before = open(path).read()
                went = m.go(looked, kind="restore")
                if after_sunset is not None:
                    self.stopped_with_nothing_changed(m, went, path, before)
                    self.assertIn("stopped: foreign", went.lines)
                    continue
                self.assertEqual(went.ending, "complete", went.text)
                self.assertEqual(open(path).read(), "one\ntwo\nthree\n", "the line did not return between its neighbours")


    def test_EV6_A83_a_removed_first_line_and_a_removed_last_line_return_at_the_files_edge_and_stop_where_a_line_was_added_there(self):
        """EV-6 as batch 35 words it (A84): "For a span that stood at its file's start or at its end, the file's start, or its
        end, stands as the recorded line on that side, and the sunset's save records it so: the span goes back only where the
        recorded line on the other side stands at that edge of the file and the pair is found exactly once, and, for an
        ordered file, everything before that point is as recorded (the owner's ruling, A83, given of one line; a span of more
        lines rests on A83)." Its test line: "a removed first line returns at the file's start, before the line that followed
        it, and a removed last line returns at the file's end, after the line that stood before it (the owner's ruling,
        A83); with a line added at the file's start before the first of those restores, and a line added at its end before
        the second, each restore stops, its probe answering `foreign` (OP-5), with nothing changed and no file text in any
        output". The file is marked unordered here, so that the pair alone decides; the ordered file is the next test's."""
        start, end = "one\ntwo\nthree\n", None
        for case, span, sunset_left, added, back in (
                ("the first line", "one", "two\nthree\n", None, start),
                ("the last line", "three", "one\ntwo\n", None, start),
                ("the first line, a line added at the start", "one", "two\nthree\n", "zero\ntwo\nthree\n", end),
                ("the last line, a line added at the end", "three", "one\ntwo\n", "one\ntwo\nfour\n", end)):
            with self.subTest(case=case):
                self.edge_restore(start, span, False, sunset_left, added, back)

    def test_EV6_A84_a_span_of_more_lines_at_the_files_edge_returns_there_and_an_ordered_files_head_is_asked(self):
        """EV-6, "a span of more lines rests on A83" (A84; report-9's seen line: a span of more than one line was not tested),
        in an ordered file: a span of two lines taken from the file's start, and one taken from its end, each go back at that
        edge; with a line added at that edge before the restore, each restore stops, its probe answering `foreign`; and at the
        end, "for an ordered file, everything before that point is as recorded": a line changed above the recorded neighbour,
        which still stands at the end, stops the restore too."""
        start = "one\ntwo\nthree\nfour\n"
        for case, span, sunset_left, added, back in (
                ("two lines at the start", "one\ntwo", "three\nfour\n", None, start),
                ("two lines at the end", "three\nfour", "one\ntwo\n", None, start),
                ("two lines at the start, a line added at the start", "one\ntwo", "three\nfour\n", "zero\nthree\nfour\n", None),
                ("two lines at the end, a line added at the end", "three\nfour", "one\ntwo\n", "one\ntwo\nfive\n", None),
                ("two lines at the end, the head changed", "three\nfour", "one\ntwo\n", "one, edited\ntwo\n", None)):
            with self.subTest(case=case):
                self.edge_restore(start, span, True, sunset_left, added, back)

    def edge_restore(self, start, span, ordered, sunset_left, added, back):
        m = self.fresh()
        path = m.put("dev/ordered.txt", start)
        sunset = self.sunset(m, span_rows("remove", span=span, ordered=ordered))
        self.assertEqual(open(path).read(), sunset_left, "the sunset did not take the span out")
        # the sunset's save records the file's edge as the line on that side: the operation is `done` with its way back
        done = [r for r in m.journal(sunset) if r["kind"] == "completion" and r.get("op") == "RL"]
        self.assertEqual(len(done), 1, "the sunset's change did not complete")
        self.assertTrue(done[0]["way_back"]["offered"], done[0]["way_back"])
        if added is not None:
            with open(path, "w") as fh:          # a line added at that edge, before the restore
                fh.write(added)
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        before = open(path).read()
        went = m.go(looked, kind="restore")
        if back is None:
            self.stopped_with_nothing_changed(m, went, path, before)
            self.assertIn("stopped: foreign", went.lines)
            restore = looked.doc["run"]
            self.assertEqual([r for r in m.journal(restore) if r["kind"] == "start"], [],
                             "the put-back was started: the probe did not answer `foreign`")
            return
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(open(path).read(), back, "the span did not return at the file's edge")

class SEC7ARestoresPlaces(AReverseThatCopiesFromAKeep):
    """SEC-7's test line, its restore half: "clean runs of sunrise, sunset and restore produce each artifact this table names
    (... the moved launch agent's file, the span put back, the store copied back ...), and the canary and each held value are
    found only at these places, each reached by the construction and holding the permissions the table gives". Its rows: "the
    place a thing was taken from, on a restore | a launch agent's file moved back | the file itself, moved by C7 to its
    original place and no other; it keeps the permissions it had"; the span and the store as in `PuttingTextBack` and
    `AReverseThatCopiesFromAKeep`, whose planted links are tested there."""

    test_EV5_KEEP4_SEC7_EV7_a_reverse_copies_the_store_back_from_its_keep_and_a_second_restore_finds_its_place_taken = None
    test_EV7_a_keep_whose_fingerprint_no_longer_matches_takes_only_its_dependents_out_of_the_offer = None
    test_SEC7_a_link_planted_at_the_stores_place_fails_the_operation_with_nothing_written_through_it = None

    def test_SEC7_a_clean_restore_puts_back_the_agents_file_the_span_and_the_store_and_the_canary_rests_only_at_SEC7s_places(self):
        import scan
        m = self.fresh()
        agent_canary = harness.canary("launch-agent")
        agent = m.put("dev/agent.plist", "<plist>%s</plist>\n" % agent_canary, 0o600)
        os.makedirs(m.path("dev", "sunset"), 0o700)
        identity = (os.stat(agent).st_dev, os.stat(agent).st_ino)
        moved = rowlib.move("MA", P[1], source=rowlib.path(rowlib.DEV, "agent.plist"), target=rowlib.path(rowlib.DEV, "sunset", "agent.plist"),
                            output="moved agent")
        moved["way_back"]["reverse"]["phase"] = BACK
        moved["way_back"]["reverse"]["output"] = {"name": "back agent", "fields": {}}
        m.put("dev/status.txt", "head line\nstatus: live\ntail line\n", 0o600)
        self.store_sunset(m, extra=[moved] + span_rows("replace"))
        self.assertFalse(os.path.exists(agent))
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual((os.stat(agent).st_dev, os.stat(agent).st_ino), identity, "not the file itself, moved back")
        self.assertEqual(os.stat(agent).st_mode & 0o777, 0o600, "the agent's file did not keep its permissions")
        self.assertEqual(open(m.path("dev", "status.txt")).read(), "head line\nstatus: live\ntail line\n")
        self.assertEqual(os.stat(m.path("dev", "status.txt")).st_mode & 0o777, 0o600)
        self.assertEqual(open(m.path("dev", "demo-store.txt"), "rb").read(), open(m.path("dev", "demo-dump.txt"), "rb").read())
        self.assertFalse(os.stat(m.path("dev", "demo-store.txt")).st_mode & 0o007, "the store is wider than at the retirement")
        m.secret_places = (agent, m.path("dev", "demo-dump.txt"), m.path("dev", "demo-store.txt"))
        m.owner_files = (m.path("dev", "demo.env"),)
        self.assertEqual(scan.scan(m, [(agent_canary, [])], [went, looked]), [])


class KeepsAndEntries(RestoreCase):
    def test_KEEP4_KEEP5_after_a_sunset_a_restore_and_a_second_sunset_the_keeps_and_the_entries_stay(self):
        """KEEP-4's test line: "after a sunset, a restore and a second sunset, every keep of the first exists at its place and
        equals its recorded fingerprint." KEEP-5's: "a second sunset after a restore adds an entry and leaves the first
        byte-equal." KEEP-5: "No run rewrites or removes an entry once it is published, its own included. The project's record
        is a history: each run adds its own entry"."""
        import hashlib
        m = self.fresh()
        m.put("dev/demo.env", "DATABASE_URL=postgres://app:%s@db.fixture.invalid/app\n" % harness.canary("keep4"), 0o600)
        m.put("dev/a.md", "a\n")
        entry = rowlib.last_record("L9", LAST)
        first_rows = [rowlib.keep("P1", P[0]), mover("MA", "a"), entry]
        restore = restore_lane([rowlib.last_record("L1", LAST)], phases=(BACK, LAST))
        sunset = self.sunset(m, first_rows, restore=restore)
        kept = [r for r in m.journal(sunset) if r["kind"] == "completion" and r["op"] == "P1"][0]["keep"]
        keep_path = m.path("dev", "demo-dump.txt")
        first_entry = m.path("dev", "demo-record-%s.txt" % sunset)
        entry_bytes = open(first_entry, "rb").read()
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(m.go(looked, kind="restore").ending, "complete")
        m.put("dev/b.md", "b\n")
        second_rows = [rowlib.keep("P2", P[0], place=rowlib.path(rowlib.DEV, "demo-dump-2.txt")), mover("MB", "b"), entry]
        second = self.sunset(m, second_rows, restore=restore)
        with open(keep_path, "rb") as fh:
            data = fh.read()
        self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (kept["size"], kept["sha256"]), "the first sunset's keep changed")
        self.assertEqual(open(first_entry, "rb").read(), entry_bytes, "the first sunset's entry changed")
        self.assertTrue(os.path.isfile(m.path("dev", "demo-record-%s.txt" % second)), "the second sunset added no entry")
        self.assertTrue(os.path.isfile(m.path("dev", "demo-record-%s.txt" % looked.doc["run"])), "the restore added no entry")
