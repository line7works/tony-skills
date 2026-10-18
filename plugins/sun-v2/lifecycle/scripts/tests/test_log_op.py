"""Groups 3.2 and 3.3 of the frame: the journal (LOG-1 to LOG-3) and operations (OP-1 to OP-11), on fakes.

The kill at every boundary of every fake row, by a real SIGKILL, is `test_kill_sweep.py`; the tests
here that kill do it in-process at one named boundary. `planted(when, act)` stands another actor in
the record: it does `act` once, the first time an event matches, and the invocation goes on.
"""
import json
import os
import shutil
import time
import unittest

import fab
import harness
import killlib
import rowlib
from sun_core import fsio, texts


def planted(when, act):
    done = []

    def hook(event):
        if not done and when(event):
            done.append(event["i"])
            act()
        return False
    return hook


def at(stage, op, subject=None, operation=None):
    def match(event):
        return (event["stage"] == stage and event["op"] == op and (subject is None or str(event["subject"]).endswith(subject))
                and (operation is None or event.get("operation") == operation))
    return match


def journal_after(op_kind, operation):
    return at("post", "journal", op_kind, operation)


class OpCase(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.m = self.machine()

    def clean(self, machine=None, rows=None):
        m = machine or self.m
        rowlib.install(m, rowlib.lane("sunrise", rows, phases=("one",)) if rows is not None else rowlib.clean_lane())
        m.put("shortcuts.txt", "alias other\n")
        m.put("dev/demo-scope.md", "scope\n")
        return m

    def changing(self, machine=None):
        m = machine or self.m
        return [(c["tool"], c["argv"][0]) for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold") for c in m.calls(tool) if c["changing"]]

    def records(self, run, op=None, kind=None):
        return [r for r in self.m.journal(run) if (op is None or r.get("op") == op) and (kind is None or r["kind"] == kind)]


class TheJournal(OpCase):
    def boundaries(self, rows=None):
        m = self.clean(harness.Machine(self.tmp, "count", "count"), rows)
        looked = m.look()
        seen = m.go(looked)
        return [e for e in seen.events if e["stage"] in ("pre", "mid", "post")]

    def test_LOG1_a_kill_at_every_write_boundary_leaves_a_start_record_for_every_effect_the_world_shows(self):
        total = len(self.boundaries())
        ops = {"create": "C1", "cas": "G1", "set": "H1"}
        for point in range(0, total, 5):        # every boundary is killed at by a real SIGKILL in test_kill_sweep.py
            m = self.clean(harness.Machine(self.tmp, "p%d" % point, "p%d" % point))
            looked = m.look()
            count = {"n": -1}

            def kill(event, want=point, count=count):
                if event["stage"] in ("pre", "mid", "post"):
                    count["n"] += 1
                    return count["n"] == want
                return False
            m.recorder.torn = point % 10 == 5
            went = m.go(looked, kill=kill)
            self.assertTrue(went.killed)
            started = set(r["op"] for r in m.journal(looked.doc["run"]) if r["kind"] == "start")
            for tool in ("fakehost", "fakegit"):
                for call in m.calls(tool):
                    if call["changing"]:
                        self.assertIn(ops[call["argv"][0]], started, "kill point %d: an effect call with no start record before it" % point)
            if os.path.exists(os.path.join(m.dev, "demo")):
                self.assertIn("B1", started)
            if "alias demo" in open(m.path("shortcuts.txt")).read():
                self.assertIn("S1", started)
            if os.path.exists(os.path.join(m.dev, "demo", "scope.md")):
                self.assertIn("M1", started)
            # the journal reads back with at most its last record dropped
            if m.open_runs():
                status = m.summon("status")
                self.assertIn(status.ending, ("stopped", "complete", "refused"), "kill point %d: %s" % (point, status.text[:300]))
                self.assertNotEqual((status.lines or [""])[0], texts.RUNDIR_STOP["chain"], "kill point %d left a journal that does not read back" % point)
            shutil.rmtree(m.home, True)

    def test_LOG1_a_record_of_a_kind_the_rule_does_not_list_stops_the_invocation(self):
        m = self.clean(rows=[rowlib.owner_step("O1", mode="on his word")])
        looked, went = m.started()
        run_dir = m.facts.run_dir(looked.doc["run"])
        from sun_core import journal as journalmod
        records = m.journal(looked.doc["run"])
        body = {"n": len(records), "kind": "reopening", "at": "2026-01-01T00:00:00Z", "prev": records[-1]["h"], "inv": records[-1]["inv"]}
        body["h"] = journalmod._hash(body["prev"], body)
        with open(os.path.join(run_dir, "journal.jsonl"), "a") as fh:
            fh.write(fsio.canonical_json(body) + "\n")
        stopped = m.summon("status")
        self.assertEqual((stopped.ending, stopped.lines[0]), ("stopped", texts.RUNDIR_STOP["chain"]))

    def test_LOG1_batch22_each_record_ends_with_its_end_mark_and_a_last_piece_without_it_is_cut_off(self):
        """LOG-1 (batch 22): "Each record is written whole with a mark of its end, which no record's content holds; what
        that mark is, is the build's. A record is whole only where its end mark stands. A cut-off record is a last piece
        that lacks the mark, which a kill or a lost write leaves, and a journal of no bytes holds no record. A piece that
        has its end mark and is no record of the kinds below is not cut off: it is a record of no listed kind, and it stops
        the invocation." Its test line: "The end mark: a last piece of bytes that are no record, with no end mark after
        them, is dropped as a cut-off record and the journal reads back without it; the same bytes with the end mark after
        them stop the invocation as a record of no listed kind; a journal of no bytes reads back as holding no record."
        The end mark as built is the newline (hand-back 1's choice, which the frame now leaves to the build)."""
        from sun_core import journal as journalmod
        m = self.clean(rows=[rowlib.owner_step("O1", mode="on his word")])
        looked, went = m.started(inputs=m.inputs(description="a line\nwith a break inside it"))
        run = looked.doc["run"]
        run_dir = m.facts.run_dir(run)
        path = os.path.join(run_dir, "journal.jsonl")
        data = open(path, "rb").read()
        whole = len(m.journal(run))
        # every record is one piece that ends with the mark, and no record's content holds the mark
        pieces = data.split(b"\n")
        self.assertEqual(pieces[-1], b"", "the last record lacks its end mark")
        self.assertEqual(len(pieces) - 1, whole)
        for piece in pieces[:-1]:
            self.assertNotIn(b"\n", piece)
            json.loads(piece.decode("utf-8"))
        self.assertNotIn(b"\n", fsio.canonical_json({"a": "a line\nwith a break", "b": ["\n"]}).encode("utf-8"))
        no_record = b"these bytes are no record of any kind"
        # without the end mark: dropped as a cut-off record, the journal reads back without it
        with open(path, "ab") as fh:
            fh.write(no_record)
        read = journalmod.Journal.read(fsio.FS(), run_dir)
        self.assertEqual((len(read.records), read.tail), (whole, len(no_record)))
        cut = m.summon("status")
        self.assertEqual(cut.ending, "waiting", cut.text)
        self.assertEqual(cut.doc["position"], whole, "the cut-off piece was counted")
        # the same bytes with the end mark after them: a record of no listed kind; the invocation stops
        with open(path, "wb") as fh:
            fh.write(data + no_record + b"\n")
        os.chmod(path, 0o600)
        with self.assertRaises(journalmod.Broken):
            journalmod.Journal.read(fsio.FS(), run_dir)
        stopped = m.summon("status")
        self.assertEqual((stopped.ending, stopped.lines[0]), ("stopped", texts.RUNDIR_STOP["chain"]))
        self.assertEqual(stopped.doc.get("forms"), None, "a form was rendered from records that failed their check")
        # a journal of no bytes reads back as holding no record
        empty = os.path.join(self.tmp, "no-bytes")
        os.makedirs(empty, 0o700)
        open(os.path.join(empty, "journal.jsonl"), "wb").close()
        read = journalmod.Journal.read(fsio.FS(), empty)
        self.assertEqual((read.records, read.tail), ([], 0))

    def test_LOG2_killed_right_after_an_effect_every_input_of_the_reverse_is_readable_from_the_run_directory_alone(self):
        m = self.clean()
        before = open(m.path("shortcuts.txt"), "rb").read()
        looked = m.look()
        went = m.go(looked, kill=at("post", "swap"))
        self.assertTrue(went.killed)
        run = looked.doc["run"]
        start = self.records(run, "S1", "start")[-1]
        os.remove(m.path("shortcuts.txt"))            # the changed thing is gone: the record alone must do
        saved = open(os.path.join(m.facts.run_dir(run), "protected", start["inputs"][0]["record"]), "rb").read()
        self.assertEqual(saved, before)
        self.assertEqual(start["inputs"][0]["type"], "before-image")
        events = went.events
        record_at = next(e["i"] for e in events if e["op"] == "create" and start["inputs"][0]["record"] in e["subject"] and e["stage"] == "post")
        swap_at = next(e["i"] for e in events if e["op"] == "swap" and e["stage"] == "pre")
        self.assertLess(record_at, swap_at, "the before-image's record does not precede the swap call (LOG-3)")
        step_at = next(e["i"] for e in events if e["op"] == "journal" and e["stage"] == "post" and e["subject"] == "step" and e.get("operation") == "S1" and e.get("step") == "staged")
        self.assertLess(step_at, swap_at, "the step record does not precede the publish")

    def test_LOG2_the_after_state_is_computed_beforehand_so_a_fake_that_leaves_another_state_fails_the_after_check(self):
        m = self.clean()
        m.plan_fake("fakehost", {"command": "set", "state_as": "archived"})
        looked, went = m.started()
        run = looked.doc["run"]
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: the after-check does not show the after-state", went.lines)
        start = self.records(run, "H1", "start")[-1]
        self.assertEqual(start["after"], {"word": "paused"})
        self.assertEqual(self.records(run, "H1", "completion"), [], "a completion was recorded over a failed after-check")
        self.assertIn(run, m.open_runs().values())

    def removals_are_its_own(self, m, result, run_dir, label):
        """LOG-3, as the rule now words it (the owner's ruling A41; the reviewer's L1): every removal lies under the run
        directory, in its staging or its private folder, or is the removal of a lock's file by the invocation that took
        that lock, its own taking of that lock standing earlier in the same invocation's record."""
        taken = set()
        for e in result.events:
            if e["stage"] == "pre" and e["op"] in ("rename", "replace-record") and str(e["subject"]).endswith(".lock"):
                taken.add(e["subject"])           # the lock's record put at its place: a new lock's file, or a left one taken over
            if e["stage"] != "pre" or e["op"] not in ("remove", "unlock-remove"):
                continue
            path = e["subject"]
            if path.startswith(run_dir + os.sep):
                # staging; the private folder (the private password file); and, in the protected folder, a file made to hand
                # a protected input to a child, and no protected record (LOG-3; SEC-3's protected-input row, batch 20)
                inputs = os.path.join(run_dir, "protected", "input-")
                self.assertTrue(path.startswith((os.path.join(run_dir, "staging"), os.path.join(run_dir, "private"), inputs)),
                                "%s: a removal in the run directory that is not the run's own to make: %s" % (label, path))
                continue
            self.assertTrue(path.startswith(m.facts.locks_dir + os.sep) and path.endswith(".lock"),
                            "%s: the run removed something that is not its own: %s" % (label, path))
            self.assertIn(path, taken, "%s: a lock's file removed by an invocation that did not take that lock: %s" % (label, path))

    def test_LOG3_L1_the_run_removes_only_what_is_its_own_and_a_locks_file_only_by_the_invocation_that_took_it(self):
        m = self.clean()
        looked = m.look()
        self.removals_are_its_own(m, looked, m.facts.run_dir(looked.doc["run"]), "the look")
        went = m.go(looked, kill=at("post", "create", "object"))       # a staged object, never published
        run_dir = m.facts.run_dir(looked.doc["run"])
        self.assertTrue(os.listdir(os.path.join(run_dir, "staging")))
        self.removals_are_its_own(m, went, run_dir, "the killed go")
        resumed = m.resume()
        self.assertEqual(resumed.ending, "complete", resumed.text)
        self.assertEqual(os.listdir(os.path.join(run_dir, "staging")), [], "an unpublished staged object is still there after the next run of its operation")
        self.removals_are_its_own(m, resumed, run_dir, "the resume")
        self.assertTrue([e for e in resumed.events if e["op"] == "unlock-remove"], "the resume removed no lock's file of its own")

    def test_LOG3_RUN2_A41_a_killed_holders_left_file_is_removed_only_by_the_invocation_that_next_takes_that_lock(self):
        # RUN-2: "A holder that is killed leaves its file. That file holds no lock from then on; it stays, with its
        # record, until an invocation takes that lock again, and that invocation removes it when it releases the lock";
        # LOG-3's test line: "no invocation removes the file of a lock it did not itself take, and a killed holder's
        # left file is removed only by an invocation that took that lock after it"
        m = self.clean()
        looked = m.look()
        went = m.go(looked, kill=at("post", "journal", "start"))
        self.assertTrue(went.killed)
        left = m.facts.lock_file(m.fingerprint("demo"))
        self.assertEqual([os.path.basename(left)], m.lock_names(), "the killed holder did not leave its lock's file")
        record = open(left).read()
        other = m.look("another")
        self.assertEqual(other.ending, "preview", other.text)
        self.assertEqual([e for e in other.events if e["stage"] == "pre" and e["subject"] == left], [],
                         "an invocation that did not take that lock changed or removed its left file")
        self.assertEqual(open(left).read(), record)
        status = m.summon("status")
        self.assertFalse(os.path.exists(left), "the next taker did not remove the left file at its release")
        took = [e["i"] for e in status.events if e["stage"] == "pre" and e["op"] == "replace-record" and e["subject"] == left]
        removed = [e["i"] for e in status.events if e["stage"] == "pre" and e["op"] == "unlock-remove" and e["subject"] == left]
        self.assertTrue(took and removed and took[0] < removed[0], "the left file was not taken over before it was removed")
        self.removals_are_its_own(m, status, m.facts.run_dir(looked.doc["run"]), "the status")


class Effects(OpCase):
    def test_OP1_OP6_in_the_reference_run_each_effect_is_one_call_between_its_start_and_its_completion_in_order(self):
        m = self.clean()
        looked = m.look()
        went = m.go(looked)
        self.assertEqual(went.ending, "complete")
        events = went.events
        effect_of = {"B1": ("rename", None), "S1": ("swap", None), "M1": ("rename", None), "C1": ("child", "create"), "G1": ("child", "cas"), "H1": ("child", "set")}
        for op, (kind, command) in effect_of.items():
            start = next(e["i"] for e in events if journal_after("start", op)(e))
            completion = next(e["i"] for e in events if journal_after("completion", op)(e))
            between = [e for e in events if start < e["i"] < completion]
            if kind == "child":
                calls = [e for e in between if e["op"] == "child" and e["stage"] == "pre" and e.get("argv", [""])[0] == command]
            else:
                calls = [e for e in between if e["op"] == kind and e["stage"] == "pre" and not e["subject"].startswith(m.facts.tool_home)
                         or (e["op"] == kind and e["stage"] == "pre" and kind == "swap")]
            self.assertEqual(len(calls), 1, "%s: %d state-changing calls between its start and its completion" % (op, len(calls)))
            effect = calls[0]["i"]
            checks = [e["i"] for e in between if e["i"] > effect and (e["stage"] == "read" or (e["op"] == "child" and e["stage"] == "pre"))]
            self.assertTrue(checks, "%s: no after-check read stands after the effect call" % op)
            if op in ("B1", "S1"):
                step = next(e["i"] for e in between if journal_after("step", op)(e) and e.get("step") == "staged")
                self.assertLess(step, effect, "%s: the step record does not precede the publish" % op)
        self.assertEqual(self.changing(), [("fakehost", "create"), ("fakehost", "set"), ("fakegit", "cas")])
        # ORD-5: no two effect calls overlap, and a second run of the fixture records the same sequence
        other = self.clean(harness.Machine(self.tmp, "again", "again"))
        other.started()
        self.assertEqual(self.changing(other), self.changing())

    def test_OP3_D16_a_competing_change_between_the_probe_and_the_call_C1_C2_C4_C5_the_call_fails_and_the_run_is_stopped_and_open(self):
        cases = {
            "C1": ("B1", at("post", "journal", "step", "B1"), lambda m: os.makedirs(os.path.join(m.dev, "demo")), "something is at the place"),
            "C2": ("C1", at("post", "journal", "start", "C1"),
                   lambda m: m.set_fake("fakehost", things={"demo": {"id": "theirs", "kind": "repo", "state": "active", "name": "demo"}}), "the provider refused"),
            "C4": ("G1", at("post", "journal", "start", "G1"), lambda m: m.set_fake("fakegit", refs={"main": "theirs"}), "a command failed"),
            "C5": ("H1", at("post", "journal", "start", "H1"), lambda m: self.set_state(m, "archived"), "a command failed"),
        }
        for index, (construction, (op, when, act, reason)) in enumerate(cases.items()):
            with self.subTest(construction=construction):
                m = self.clean(harness.Machine(self.tmp, "c%d" % index, construction))
                looked = m.look()
                went = m.go(looked, kill=planted(when, lambda m=m, act=act: act(m)))
                run = looked.doc["run"]
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: " + reason, went.lines)
                self.assertIn("operation: " + op, went.lines)
                self.assertNotIn(op, m.statuses(run), "a final status was recorded for an effect that did not happen")
                self.assertIn(run, m.open_runs().values(), "the run is not open after the stop")
                if construction == "C1":
                    self.assertEqual(os.listdir(os.path.join(m.dev, "demo")), [], "the thing at the place was overwritten or taken over")
                if construction == "C2":
                    self.assertEqual(m.fake("fakehost", "state.json")["things"]["demo"]["id"], "theirs")
                if construction == "C4":
                    self.assertEqual(m.fake("fakegit", "state.json")["refs"], {"main": "theirs"})
                if construction == "C5":
                    self.assertEqual(m.fake("fakehost", "state.json")["things"]["demo"]["state"], "archived")

    def set_state(self, m, state):
        things = m.fake("fakehost", "state.json")["things"]
        things["demo"]["state"] = state
        m.set_fake("fakehost", things=things)

    def test_OP3_RISK1_C3_C6_C7_the_outcome_is_the_one_the_named_risk_states_and_the_journal_carries_its_mark(self):
        # C3 under RK2: a writer that ignores the lock, between the hash check and the swap, loses its write
        m = self.clean()
        looked = m.look()
        went = m.go(looked, kill=planted(at("pre", "swap"), lambda: open(m.path("shortcuts.txt"), "a").write("alias theirs\n")))
        run = looked.doc["run"]
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(open(m.path("shortcuts.txt")).read(), "alias other\nalias demo\n")
        marks = sorted((r["op"], r["risk"]) for r in self.records(run) if r.get("step") == "risk-mark")
        self.assertEqual(marks, [("M1", "RK4"), ("S1", "RK13"), ("S1", "RK2"), ("S1", "RK5")])   # RK13 beside RK5 (A63)
        # C7 under RK4: the thing at the source replaced between the first read and the rename: stop, both places named
        m7 = self.clean(harness.Machine(self.tmp, "c7", "c7"))
        looked7 = m7.look()
        source = os.path.join(m7.dev, "demo-scope.md")

        def swap_source():
            os.remove(source)
            with open(source, "w") as fh:
                fh.write("another document\n")
        went7 = m7.go(looked7, kill=planted(at("post", "journal", "start", "M1"), swap_source))
        self.assertEqual(went7.ending, "stopped", went7.text)
        self.assertTrue(any("both places are named" in line for line in went7.lines), went7.lines)
        self.assertEqual([r for r in m7.journal(looked7.doc["run"]) if r["kind"] == "completion" and r["op"] == "M1"], [])
        again = m7.resume()
        self.assertIn("stopped: foreign", again.lines)
        # C6 under RK3, on a row RK3 names: the same change made by another between the read and the request is recorded as its own
        m6 = harness.Machine(self.tmp, "c6", "c6")
        rowlib.install(m6, rowlib.lane("sunrise", [rowlib.refusing("T20", construction="C6")]))
        m6.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}})
        looked6 = m6.look()
        went6 = m6.go(looked6, kill=planted(at("post", "journal", "start", "T20"), lambda: self.set_state(m6, "paused")))
        self.assertEqual(went6.ending, "complete", went6.text)
        self.assertEqual(m6.statuses(looked6.doc["run"]), {"T20": "done"})
        self.assertEqual([r["risk"] for r in m6.journal(looked6.doc["run"]) if r.get("step") == "risk-mark"], ["RK3"])

    def test_OP4_a_build_killed_anywhere_leaves_the_place_empty_or_whole_and_staging_owner_only_and_another_volume_ends_the_look(self):
        rows = [rowlib.build("B1")]
        total = len([e for e in self.clean(harness.Machine(self.tmp, "n", "n"), rows).started()[1].events if e["stage"] in ("pre", "mid", "post")])
        wide = []
        for point in range(total):
            m = self.clean(harness.Machine(self.tmp, "b%d" % point, "b%d" % point), rows)
            looked = m.look()
            count = {"n": -1}
            run_dir = m.facts.run_dir(looked.doc["run"])

            def kill(event, want=point, count=count, run_dir=run_dir):
                staging = os.path.join(run_dir, "staging")
                for base, dirs, files in os.walk(staging):
                    for name in dirs + files:
                        if os.stat(os.path.join(base, name)).st_mode & 0o077:
                            wide.append((event["i"], name))
                if event["stage"] in ("pre", "mid", "post"):
                    count["n"] += 1
                    return count["n"] == want
                return False
            m.go(looked, kill=kill)
            place = os.path.join(m.dev, "demo")
            if os.path.exists(place):
                self.assertEqual(sorted(os.listdir(place)), ["README.md", "docs"], "kill point %d left a partial object at the place" % point)
                self.assertEqual(open(os.path.join(place, "README.md")).read(), "# demo\n")
            shutil.rmtree(m.home, True)
        self.assertEqual(wide, [], "a file in staging was wider than owner-only at a recorded moment")
        far = self.clean(harness.Machine(self.tmp, "far", "far"), rows)
        far.other_volumes = [far.dev]
        ended = far.look()
        self.assertEqual(ended.ending, "refused")
        self.assertIn("the place is on another volume: " + os.path.join(far.dev, "demo"), ended.lines)

    def test_OP4_a_builder_that_asks_for_wider_permissions_still_builds_owner_only_in_staging(self):
        place = rowlib.path(rowlib.DEV, rowlib.NAME)
        built = rowlib.build("B1")
        built["construction"] = {"id": "C1", "builder": "scaffold", "out_param": "out", "mode": 0o755}
        built["commands"] = [rowlib.use("scaffold", "fakescaffold.scaffold")]
        m = self.clean(rows=[built])
        m.plan_fake("fakescaffold", {"command": "scaffold", "mode": "666"})
        looked = m.look()
        seen = []

        def watch(event):
            staging = os.path.join(m.facts.run_dir(looked.doc["run"]), "staging")
            for base, dirs, files in os.walk(staging):
                for name in files:
                    seen.append(os.stat(os.path.join(base, name)).st_mode & 0o777)
            return False
        went = m.go(looked, kill=watch)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertTrue(seen)
        self.assertEqual(set(seen), {0o600})
        self.assertEqual(sorted(os.listdir(os.path.join(m.dev, "demo"))), ["README.md", "src"])


class TheProbe(OpCase):
    """OP-5's six answers and what OP-6 does with each, per kind that has an effect."""

    def after_start(self, op, rows=None):
        m = self.clean(harness.Machine(self.tmp, "pr-%s-%d" % (op, len(os.listdir(self.tmp))), op), rows)
        looked = m.look()
        went = m.go(looked, kill=at("post", "journal", "start", op))
        self.assertTrue(went.killed, went.text)
        return m, looked.doc["run"]

    def test_OP5_OP6_EV1_the_by_hand_fixture_never_yields_done(self):
        # a start record on disk, the run killed before the effect, the world then put in the after-state by another actor
        m, run = self.after_start("S1")
        with open(m.path("shortcuts.txt"), "a") as fh:
            fh.write("alias demo\n")
        self.assertEqual(m.resume().ending, "complete")
        self.assertEqual(m.statuses(run)["S1"], "not proven")
        status = [r for r in m.journal(run) if r["kind"] == "status" and r["op"] == "S1"][0]
        self.assertEqual(status["way_back"], {"offered": False, "reason": "not proven"})
        m, run = self.after_start("M1")
        os.rename(os.path.join(m.dev, "demo-scope.md"), os.path.join(m.dev, "demo", "scope.md"))
        m.resume()
        self.assertEqual(m.statuses(run)["M1"], "not proven")
        m, run = self.after_start("G1")
        m.set_fake("fakegit", refs={"main": "c1"})
        m.resume()
        self.assertEqual(m.statuses(run)["G1"], "not proven")
        m, run = self.after_start("H1")
        things = m.fake("fakehost", "state.json")["things"]
        things["demo"]["state"] = "paused"
        m.set_fake("fakehost", things=things)
        m.resume()
        self.assertEqual(m.statuses(run)["H1"], "not proven")
        self.assertEqual(m.calls("fakehost", "set"), [])
        m, run = self.after_start("B1")
        os.makedirs(os.path.join(m.dev, "demo"))
        with open(os.path.join(m.dev, "demo", "README.md"), "w") as fh:
            fh.write("# demo\n")
        stopped = m.resume()
        self.assertIn("stopped: foreign", stopped.lines)
        self.assertNotIn("B1", m.statuses(run))
        m, run = self.after_start("C1")
        m.set_fake("fakehost", things={"demo": {"id": "theirs", "kind": "repo", "state": "active", "name": "demo"}})
        stopped = m.resume()
        self.assertIn("stopped: an outstanding create", stopped.lines)
        self.assertNotIn("C1", m.statuses(run))
        self.assertEqual(m.calls("fakehost", "create"), [], "a create was sent again on its own")

    def test_OP5_OP6_not_landed_starts_again_with_a_new_start_record_and_landed_completes_on_its_ground(self):
        m, run = self.after_start("S1")
        self.assertEqual(m.resume().ending, "complete")
        starts = [r for r in m.journal(run) if r["kind"] == "start" and r["op"] == "S1"]
        self.assertEqual([s["probe"] for s in starts], ["ready", "not landed"])
        self.assertEqual([s["start"] for s in starts], [1, 2])
        self.assertEqual(open(m.path("shortcuts.txt")).read().count("alias demo"), 1)
        marks = [(r["op"], r["risk"]) for r in m.journal(run) if r.get("step") == "risk-mark" and r["op"] == "S1"]
        self.assertEqual(sorted(marks), [("S1", "RK13"), ("S1", "RK2"), ("S1", "RK5")], "a mark was recorded twice after the kill and the resume (RISK-1)")
        # killed after the publish: the object in place has the staged identity on record: done, on ground (b)
        m2 = self.clean(harness.Machine(self.tmp, "landed", "landed"))
        looked = m2.look()
        m2.go(looked, kill=at("post", "rename", "demo"))
        self.assertEqual(m2.resume().ending, "complete")
        done = [r for r in m2.journal(looked.doc["run"]) if r["kind"] == "completion" and r["op"] == "B1"][0]
        self.assertEqual(done["ground"], "b")
        swapped = self.clean(harness.Machine(self.tmp, "swapped", "swapped"))
        looked = swapped.look()
        swapped.go(looked, kill=at("post", "swap"))
        swapped.resume()
        done = [r for r in swapped.journal(looked.doc["run"]) if r["kind"] == "completion" and r["op"] == "S1"][0]
        self.assertEqual((done["ground"], done["way_back"]["offered"]), ("b", True))
        # a create killed after its answer record: done on resume by a read of that id, on ground (c)
        made = self.clean(harness.Machine(self.tmp, "made", "made"))
        looked = made.look()
        made.go(looked, kill=at("post", "journal", "answer", "C1"))
        self.assertEqual(made.resume().ending, "complete")
        done = [r for r in made.journal(looked.doc["run"]) if r["kind"] == "completion" and r["op"] == "C1"][0]
        self.assertEqual(done["ground"], "c")
        self.assertEqual(len(made.calls("fakehost", "create")), 1)

    def test_EV1_the_killed_after_publish_fixture_yields_done_on_resume_only_where_the_object_in_place_has_the_staged_identity_on_record(self):
        """EV-1's test line: "the killed-after-publish fixture yields `done` on resume only where the object in place has the
        staged identity on record". Each object the run builds in staging and then puts at its place: a build's folder and a
        keep's file (C1, published by a rename), and a swap's file (C3). Each is killed right after its publish. Left as it
        is, the resume finds the staged identity in place and the operation is `done`, on ground (b). Replaced by another
        actor, after the publish and before the resume, by an object of another identity with the same content, it is never
        `done`: a build and a keep are `foreign` and the run stops (OP-5's C1 row), and a swap is `not proven` (OP-6)."""
        def again(path):
            """Another actor puts at `path` an object of another identity with the same content."""
            if os.path.isdir(path):
                shutil.copytree(path, path + ".theirs")
                shutil.rmtree(path)
            else:
                shutil.copy2(path, path + ".theirs")
            os.rename(path + ".theirs", path)

        def keep_machine(label):
            m = harness.Machine(self.tmp, "ev1-" + label, "ev1-" + label)
            rowlib.install(m, rowlib.lane("sunset", [rowlib.keep("P1", "keeping")], phases=("keeping", "retiring on this machine",
                                                                                          "retiring at the providers", "the last record")))
            m.put("dev/demo.env", "DATABASE_URL=postgres://appuser:%s@db.fixture.invalid:5432/appdb\n" % ("pw" + harness.canary("ev1")), 0o600)
            m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}})
            return m, "sunset"

        cases = (("a build", "B1", lambda m: os.path.join(m.dev, "demo"), at("post", "rename", "demo")),
                 ("a keep", "P1", lambda m: os.path.join(m.dev, "demo-dump.txt"), at("post", "rename", "demo-dump.txt")),
                 ("a swap", "S1", lambda m: m.path("shortcuts.txt"), at("post", "swap")))
        for label, op, place, published in cases:
            for replaced in (False, True):
                with self.subTest(kind=label, replaced=replaced):
                    name = "%s-%s" % (op, "theirs" if replaced else "ours")
                    if op == "P1":
                        m, lane = keep_machine(name)
                    else:
                        m, lane = self.clean(harness.Machine(self.tmp, "ev1-" + name, "ev1-" + name)), "sunrise"
                    looked = m.look(kind=lane)
                    self.assertEqual(looked.ending, "preview", looked.text)
                    run = looked.doc["run"]
                    went = m.go(looked, kind=lane, kill=published)
                    self.assertTrue(went.killed, went.text)
                    self.assertTrue(os.path.exists(place(m)), "the kill did not fall after the publish")
                    self.assertNotIn(op, m.statuses(run))
                    if replaced:
                        before = os.lstat(place(m))
                        again(place(m))
                        self.assertNotEqual((os.lstat(place(m)).st_dev, os.lstat(place(m)).st_ino), (before.st_dev, before.st_ino))
                    position = m.summon("status", kind=lane).doc["position"]
                    resumed = m.summon("resume", "demo", "--position", position, "--word", "go on")
                    done = [r for r in m.journal(run) if r["kind"] == "completion" and r["op"] == op]
                    if not replaced:
                        self.assertEqual(m.statuses(run).get(op), "done", resumed.text)
                        self.assertEqual([r["ground"] for r in done], ["b"])
                    else:
                        self.assertNotEqual(m.statuses(run).get(op), "done", resumed.text)
                        self.assertEqual(done, [], "a completion was recorded for an object that is not the one the run built")
                        if op == "S1":
                            self.assertEqual(m.statuses(run).get(op), "not proven", resumed.text)
                        else:
                            self.assertEqual(resumed.ending, "stopped", resumed.text)
                            self.assertIn("stopped: foreign", resumed.lines)
                            self.assertIn("operation: %s" % op, resumed.lines)

    def test_OP5_foreign_and_unreadable_stop_with_no_state_changing_call(self):
        m, run = self.after_start("S1")
        with open(m.path("shortcuts.txt"), "w") as fh:
            fh.write("something else entirely\n")
        stopped = m.resume()
        self.assertIn("stopped: foreign", stopped.lines)
        self.assertEqual(open(m.path("shortcuts.txt")).read(), "something else entirely\n")
        m, run = self.after_start("H1")
        m.plan_fake("fakehost", {"command": "get", "do": "raw", "text": "{not json"})
        before = len(m.calls("fakehost", "set"))
        stopped = m.resume()
        self.assertIn("stopped: unreadable", stopped.lines)
        self.assertEqual(len(m.calls("fakehost", "set")), before)
        m, run = self.after_start("M1")
        with open(os.path.join(m.dev, "demo", "scope.md"), "w") as fh:
            fh.write("both places hold something\n")
        self.assertIn("stopped: foreign", m.resume().lines)

    def test_OP6_EV2_already_so_in_the_run_is_recorded_for_a_change_and_stops_a_build_and_a_create_with_nothing_pushed(self):
        m = self.clean()
        looked = m.look()
        with open(m.path("shortcuts.txt"), "a") as fh:
            fh.write("alias demo\n")
        went = m.go(looked)
        self.assertEqual(m.statuses(looked.doc["run"])["S1"], "already so")
        b = self.clean(harness.Machine(self.tmp, "taken", "taken"))
        looked = b.look()
        os.makedirs(os.path.join(b.dev, "demo"))
        stopped = b.go(looked)
        self.assertIn("stopped: something is at the place", stopped.lines)
        c = self.clean(harness.Machine(self.tmp, "named", "named"))
        looked = c.look()
        c.set_fake("fakehost", things={"demo": {"id": "theirs", "kind": "repo", "state": "active", "name": "demo"}})
        stopped = c.go(looked)
        self.assertIn("stopped: something has the name", stopped.lines)
        self.assertEqual(c.calls("fakehost", "create"), [])
        self.assertEqual(c.calls("fakegit", "cas"), [], "something was pushed to a remote the run did not make (EV-2)")

    def test_EV2_an_empty_remote_of_the_approved_name_planted_before_the_create_runs_stops_the_run_with_nothing_pushed_to_it_and_nothing_linked_to_it(self):
        """EV-2's test line, its first clause: "an empty remote repository of the approved name, planted before the create
        runs, stops the run with nothing pushed to it and nothing linked to it". The stop and nothing pushed are asserted by
        `test_OP6_EV2_already_so_in_the_run_is_recorded_for_a_change_and_stops_a_build_and_a_create_with_nothing_pushed`;
        here "nothing linked to it" too. In the clean lane the remote is the create C1's output, "remote"; the operations that
        refer to it are the push, G1 (a need on it at the made level), and H1, which changes the thing at the fake host that
        bears the remote's name (`{"output": "remote.name"}`): the link of the fixture. Planted after the look and before the
        go, an empty repository of the approved name stops the run at the create, and in that invocation and in a resume
        after it: no operation that refers to the remote has a record in the journal, no fake records a state-changing call
        (no create, no push, no change of the thing), and the planted repository is as it was planted."""
        c = self.clean(harness.Machine(self.tmp, "linked", "linked"))
        looked = c.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        manifest = json.load(open(os.path.join(c.facts.run_dir(run), "manifest-1.json")))
        referring = sorted(o["id"] for o in manifest["operations"]
                           if o["id"] != "C1" and ('"output": "remote' in json.dumps(o, sort_keys=True)))
        self.assertEqual(referring, ["G1", "H1"], "the fixture's operations that refer to the remote are not the push and the link")
        planted_thing = {"demo": {"id": "theirs", "kind": "repo", "state": "active", "name": "demo"}}
        c.set_fake("fakehost", things=planted_thing)
        c.set_fake("fakegit", refs={})
        for summons in ("go", "resume"):
            with self.subTest(summons=summons):
                ended = c.go(looked) if summons == "go" else c.resume()
                self.assertEqual(ended.ending, "stopped", ended.text)
                self.assertIn("stopped: something has the name", ended.lines)
                self.assertIn("operation: C1", ended.lines)
                self.assertEqual([r for r in c.journal(run) if r.get("op") in referring], [],
                                 "an operation that refers to the remote has a record in the journal")
                self.assertEqual(self.changing(c), [], "a fake recorded a state-changing call: something was made, pushed or linked")
                self.assertEqual(c.fake("fakehost", "state.json")["things"], planted_thing, "the planted repository was changed")
                self.assertEqual((c.fake("fakegit", "state.json") or {}).get("refs") or {}, {}, "something was pushed to it")

    def test_EV2_no_operation_that_refers_to_a_field_of_an_output_the_run_was_to_make_runs_before_its_provider_is_done_whatever_a_read_shows(self):
        """EV-2's test line, its third clause: "no operation that refers to a field of an output the run was to make runs
        before that output's provider is `done` or `adopted`, whatever state a read shows". EV-2's table: the thing is
        bound, "For a thing the run was to make: `done` or `adopted`, and nothing else", and that is what allows "references
        to the output's fields (RUN-6)". The output is the create C1's, "remote", which the run was to make. The operation
        R1 refers to its field, the name (`{"output": "remote.name"}`), and changes the thing at the fake host that bears
        it; R1 has no need on "remote", so that no need of ORD-1 is what keeps it back. In each pass a thing of that name,
        active, is put at the fake host by another actor, so that a read by the name shows the state R1's before-test asks.

        - its provider not run yet: R1 stands in the phase before C1's, so that its turn comes first;
        - its provider not `done`: R1 stands after C1, and C1 is killed after its start record, before its send, and so is
          outstanding (OP-7); the thing is planted after the kill, and the run is resumed twice.

        In each: R1 has no record in the journal and is not `done`, no fake records R1's change (`set`), and the thing is
        as it was planted."""
        def r1(phase):
            return rowlib.refusing("R1", phase, name={"output": "remote.name"}, output="state-R1")

        planted_thing = {"demo": {"id": "theirs", "kind": "repo", "state": "active", "name": "demo"}}
        for label in ("its provider not run yet", "its provider not done"):
            with self.subTest(provider=label):
                m = harness.Machine(self.tmp, "ref-%d" % len(os.listdir(self.tmp)), "ref")
                rows = rowlib.clean_rows()
                if label == "its provider not run yet":
                    rows.insert(rows.index([r for r in rows if r["id"] == "C1"][0]) - 1, r1("prepare"))
                else:
                    rows.insert(rows.index([r for r in rows if r["id"] == "C1"][0]) + 1, r1("remote"))
                self.clean(m, None)
                rowlib.install(m, rowlib.lane("sunrise", rows, phases=("prepare", "remote")))
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                run = looked.doc["run"]
                order = [o["id"] for o in json.load(open(os.path.join(m.facts.run_dir(run), "manifest-1.json")))["operations"]]
                if label == "its provider not run yet":
                    self.assertLess(order.index("R1"), order.index("C1"))
                    m.set_fake("fakehost", things=planted_thing)
                    ended = [m.go(looked)]
                else:
                    self.assertLess(order.index("C1"), order.index("R1"))
                    went = m.go(looked, kill=at("post", "journal", "start", "C1"))
                    self.assertTrue(went.killed, went.text)
                    self.assertEqual(m.calls("fakehost", "create"), [], "the kill did not fall before the send")
                    m.set_fake("fakehost", things=planted_thing)
                    ended = [m.resume(), m.resume()]
                for result in ended:
                    self.assertNotEqual(result.ending, "complete", result.text)
                self.assertEqual([r for r in m.journal(run) if r.get("op") == "R1"], [], "R1 has a record in the journal")
                self.assertNotIn("R1", m.statuses(run))
                self.assertEqual(m.calls("fakehost", "set"), [], "R1's change was made before its provider was done")
                self.assertEqual(m.fake("fakehost", "state.json")["things"], planted_thing, "the thing a read showed was changed")


def after(op, *kinds):
    """A kill right after the first durable journal record of one of `kinds` for operation `op`."""
    return lambda e: e["stage"] == "post" and e["op"] == "journal" and e.get("operation") == op and str(e["subject"]) in kinds


class TheProbesTable(OpCase):
    """OP-5's test line, as the reviewer's T1 asks it of the whole table: "for each kind that has an effect, a fixture for
    each answer that kind can give yields that answer and no state-changing call: all six for a build, a keep, a change and
    a move, and five for a create, which never answers `not landed` (OP-6, OP-7), its fixture with a start record and no
    answer record being outstanding whatever the world shows; a fixture with no record in which both tests hold yields
    `already so`, and one with a start record in which both states hold yields `landed`; for a swap, a file replaced by
    another actor with the after-content yields `landed`, and one with any other content `foreign`; for a build, an object
    with another identity at the place yields `foreign`; for a move with a start record, the recorded object at the source
    with nothing at the target yields `not landed`, nothing at the source with the recorded object at the target yields
    `landed`, and every other pairing (both places hold something, neither does, or either holds an object of another
    identity) yields `foreign`."

    The expected answer of each fixture is written by hand below, from that line and OP-5's table. The invocation that makes
    the probe is ended right after the record its answer leads to (a start record, a completion, a status), or ends on its
    own at a stop; across it the world (every file outside the tool's own folder, every fake's state) is unchanged and no
    fake records a state-changing call."""

    def keep_machine(self):
        m = harness.Machine(self.tmp, "kp%d" % len(os.listdir(self.tmp)), "kp%d" % len(os.listdir(self.tmp)))
        rowlib.install(m, rowlib.lane("sunset", [rowlib.keep("P1", "keeping")], phases=("keeping", "retiring on this machine",
                                                                                      "retiring at the providers", "the last record")))
        m.put("dev/demo.env", "DATABASE_URL=postgres://appuser:%s@db.fixture.invalid:5432/appdb\n" % ("pw" + harness.canary("op5")), 0o600)
        m.put("dev/demo-scope.md", "scope\n")
        m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}})
        return m, "sunset"

    def both_rows(self):
        """A change whose before-test and after-test can both hold: the thing exists, and the thing is paused."""
        row = rowlib.refusing("H1")
        row["before_test"] = [{"id": "was", "read": "command", "command": "look", "result": "success"}]
        row["construction"]["conditions"] = ["was"]
        return row

    def machine_for(self, which):
        if which == "keep":
            return self.keep_machine()
        n = len(os.listdir(self.tmp))
        m = harness.Machine(self.tmp, "t%d" % n, "t%d" % n)
        if which == "both":
            rowlib.install(m, rowlib.lane("sunrise", [self.both_rows()]))
            m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}})
            return m, "sunrise"
        return self.clean(m), "sunrise"

    def probe_answer(self, m, run, op, result, starts_before):
        lines = result.lines
        for word, answer in (("stopped: foreign", "foreign"), ("stopped: unreadable", "unreadable"),
                             ("stopped: something is at the place", "already so"), ("stopped: something has the name", "already so"),
                             ("stopped: an outstanding create", "outstanding")):
            if word in lines and "operation: %s" % op in lines:
                return answer
        records = [r for r in m.journal(run) if r.get("op") == op]
        starts = [r for r in records if r["kind"] == "start"]
        if len(starts) > starts_before:
            return starts[-1]["probe"]
        if any(r["kind"] == "status" and r.get("status") == "already so" for r in records):
            return "already so"
        if any(r["kind"] == "completion" for r in records) or any(r.get("status") == "not proven" for r in records):
            return "landed"
        return "none: %s" % result.text[:300]

    def unreadable_at(self, m, path, method="lexists"):
        """A test seam: the fixture file system's read of `path` fails as an unreadable folder makes it fail."""
        plain = m.world

        def world(env=None):
            w = plain(env)
            real = getattr(w.fs, method)

            def failing(p, *a, **k):
                if p == path:
                    raise PermissionError(13, "Permission denied", p)
                return real(p, *a, **k)
            setattr(w.fs, method, failing)
            return w
        m.world = world

    BEFORE = {"S1": "B1", "M1": "S1", "C1": "M1"}       # the operation of the clean lane whose completion comes before each

    def case(self, kind, which, op, want, prepare=None, between=None, first_kill=None, probe_kill=None):
        """One fixture: a look; a go (killed at `first_kill`, or else right after the completion of the operation that runs
        before `op`, where there is one; and then `between` done by another actor); then the invocation that makes the probe
        of `op`, killed right after the record its answer leads to."""
        m, lane = self.machine_for(which)
        if first_kill is None and which == "clean" and op in self.BEFORE:
            first_kill = after(self.BEFORE[op], "completion")
        if prepare:
            prepare(m)
        looked = m.look(kind=lane)
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        stop_after = probe_kill or after(op, "start", "completion", "status", "answer")
        if first_kill is None:
            if between:
                between(m)
            calls, facts = self.changing(m), killlib.world_facts(m)
            result = m.go(looked, kind=lane, kill=stop_after)
            starts_before = 0
            self.assertTrue(result.killed or result.ending in ("stopped", "refused"), result.text)
        else:
            went = m.go(looked, kind=lane, kill=first_kill)
            self.assertTrue(went.killed, went.text)
            if between:
                between(m)
            starts_before = len([r for r in m.journal(run) if r.get("op") == op and r["kind"] == "start"])
            calls, facts = self.changing(m), killlib.world_facts(m)
            position = m.summon("status", kind=lane).doc["position"]
            result = m.summon("resume", "demo", "--position", position, "--word", "go on", kill=stop_after)
        got = self.probe_answer(m, run, op, result, starts_before)
        with self.subTest(kind=kind, answer=want, op=op):
            self.assertEqual(got, want)
            self.assertEqual(self.changing(m), calls, "a state-changing call was made across the probe")
            if want not in ("landed",):
                self.assertEqual(killlib.world_facts(m), facts, "the world changed across the probe")

    def test_OP5_T1_each_kind_with_an_effect_gives_each_answer_it_can_give_and_no_state_changing_call(self):
        dev = lambda m, *p: os.path.join(m.dev, *p)          # noqa: E731
        start = lambda op: after(op, "start")                  # noqa: E731

        def put(path, text="another actor's\n"):
            def act(m):
                full = path(m)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "w") as fh:
                    fh.write(text)
            return act

        def remove(path):
            return lambda m: os.remove(path(m))

        def chain(*acts):
            def act(m):
                for a in acts:
                    a(m)
            return act

        def mkdir_demo(m):
            os.makedirs(dev(m, "demo"))
            with open(dev(m, "demo", "README.md"), "w") as fh:
                fh.write("# demo\n")
        demo = lambda m: dev(m, "demo")                          # noqa: E731
        dump = lambda m: dev(m, "demo-dump.txt")                 # noqa: E731
        source = lambda m: dev(m, "demo-scope.md")              # noqa: E731
        target = lambda m: dev(m, "demo", "scope.md")           # noqa: E731
        shortcuts = lambda m: m.path("shortcuts.txt")           # noqa: E731

        def thing_state(state):
            def act(m):
                things = (m.fake("fakehost", "state.json") or {}).get("things") or {}
                things.setdefault("demo", {"id": "x", "kind": "db", "name": "demo"})["state"] = state
                m.set_fake("fakehost", things=things)
            return act

        def seam(path, method="lexists"):
            return lambda m: self.unreadable_at(m, path(m), method)

        # ---- a build (B1: the project folder, C1) -----------------------------------------------------------
        self.case("build", "clean", "B1", "ready")
        self.case("build", "clean", "B1", "already so", between=mkdir_demo)
        self.case("build", "clean", "B1", "not landed", first_kill=start("B1"))
        self.case("build", "clean", "B1", "landed", first_kill=at("post", "rename", "demo"))
        self.case("build", "clean", "B1", "foreign", first_kill=start("B1"), between=mkdir_demo)       # another identity
        self.case("build", "clean", "B1", "unreadable", between=seam(demo))
        # ---- a keep (P1: the database's dump, C1 with a builder) ----------------------------------------------
        self.case("keep", "keep", "P1", "ready")
        self.case("keep", "keep", "P1", "already so", between=put(dump))
        self.case("keep", "keep", "P1", "not landed", first_kill=start("P1"))
        self.case("keep", "keep", "P1", "landed", first_kill=at("post", "rename", "demo-dump.txt"))
        self.case("keep", "keep", "P1", "foreign", first_kill=start("P1"), between=put(dump))
        self.case("keep", "keep", "P1", "unreadable", between=seam(dump))
        # ---- a change (S1: a swap, C3) --------------------------------------------------------------------------
        self.case("change", "clean", "S1", "ready")
        self.case("change", "clean", "S1", "already so", between=put(shortcuts, "alias other\nalias demo\n"))
        self.case("change", "clean", "S1", "not landed", first_kill=start("S1"))
        self.case("change", "clean", "S1", "landed", first_kill=at("post", "swap"))
        self.case("change", "clean", "S1", "landed", first_kill=start("S1"), between=put(shortcuts, "alias other\nalias demo\n"))
        self.case("change", "clean", "S1", "foreign", first_kill=start("S1"), between=put(shortcuts, "something else entirely\n"))
        self.case("change", "clean", "S1", "unreadable", between=seam(shortcuts, "read"))
        # ---- a change whose two tests can both hold (H1: C5) ------------------------------------------------------
        self.case("change", "both", "H1", "already so", between=thing_state("paused"))
        self.case("change", "both", "H1", "landed", first_kill=start("H1"), between=thing_state("paused"))
        # ---- a move (M1, C7) ----------------------------------------------------------------------------------
        self.case("move", "clean", "M1", "ready")
        self.case("move", "clean", "M1", "already so", between=lambda m: os.rename(source(m), target(m)))
        self.case("move", "clean", "M1", "not landed", first_kill=start("M1"))
        self.case("move", "clean", "M1", "landed", first_kill=start("M1"), between=lambda m: os.rename(source(m), target(m)))
        self.case("move", "clean", "M1", "foreign", first_kill=start("M1"), between=put(target))                    # both hold
        self.case("move", "clean", "M1", "foreign", first_kill=start("M1"), between=remove(source))                 # neither
        self.case("move", "clean", "M1", "foreign", first_kill=start("M1"), between=chain(remove(source), put(source)))  # another at the source
        self.case("move", "clean", "M1", "foreign", first_kill=start("M1"),
                  between=chain(lambda m: os.rename(source(m), target(m)), remove(target), put(target)))    # another at the target
        self.case("move", "clean", "M1", "unreadable", between=seam(source))
        # ---- a create (C1, C2): five answers; with a start record and no answer record it is outstanding -------------
        self.case("create", "clean", "C1", "ready")
        self.case("create", "clean", "C1", "already so", between=lambda m: m.set_fake(
            "fakehost", things={"demo": {"id": "theirs", "kind": "repo", "state": "active", "name": "demo"}}))
        self.case("create", "clean", "C1", "landed", first_kill=after("C1", "answer"))
        self.case("create", "clean", "C1", "foreign", first_kill=after("C1", "answer"), between=lambda m: m.set_fake("fakehost", things={}))
        self.case("create", "clean", "C1", "unreadable",
                  between=lambda m: m.plan_fake("fakehost", {"command": "get", "do": "raw", "text": "{not json"}))
        self.case("create", "clean", "C1", "outstanding", first_kill=start("C1"))
        self.case("create", "clean", "C1", "outstanding", first_kill=start("C1"), between=lambda m: m.set_fake(
            "fakehost", things={"demo": {"id": "theirs", "kind": "repo", "state": "active", "name": "demo"}}))

    def test_OP5_batch39_a_create_whose_answer_record_is_there_and_whose_read_by_that_id_finds_nothing_is_foreign_and_never_sent_again(self):
        """OP-5's test line (batch 39): "a create with its answer record whose read by the recorded id finds nothing yields
        `foreign`, never `not landed`, the run stops, and the fake records no second send (OP-6; Part 5's third
        example)". Asserted over two later invocations, not only across the probe."""
        m = self.clean()
        looked = m.look()
        run = looked.doc["run"]
        went = m.go(looked, kill=after("C1", "answer"))
        self.assertTrue(went.killed, went.text)
        self.assertEqual(len(m.calls("fakehost", "create")), 1)
        m.set_fake("fakehost", things={})                    # by the recorded id, the read now finds nothing
        for turn in ("the resume", "a second resume"):
            result = m.resume()
            with self.subTest(turn=turn):
                self.assertEqual(result.ending, "stopped", result.text)
                self.assertIn("stopped: foreign", result.lines)
                self.assertIn("operation: C1", result.lines)
                starts = [r for r in m.journal(run) if r["kind"] == "start" and r.get("op") == "C1"]
                self.assertEqual(len(starts), 1, "a create with its answer record was started again")
                self.assertNotIn("not landed", [r.get("probe") for r in starts])
                self.assertEqual(len(m.calls("fakehost", "create")), 1, "the fake recorded a second send")
                self.assertNotIn("C1", m.statuses(run), "the create was given a final status")
                self.assertTrue(m.open_runs(), "the run is not open")


class LostAnswers(OpCase):
    """OP-7."""

    def lost(self, way, machine_name):
        m = harness.Machine(self.tmp, machine_name, machine_name)
        row = rowlib.create("C1")
        if way == "status-read":
            row["lost_answer"] = {"way": "status-read", "document": "the fake's own document", "command": "status", "field": "made"}
            row["commands"].append(rowlib.use("status", "fakehost.request-status", name=rowlib.NAME))
        elif way == "drop":
            row["lost_answer"] = {"way": "by dropping the layer only"}
            row["thing"]["layer"] = "hosting"
        rowlib.install(m, rowlib.lane("sunrise", [row]))
        m.plan_fake("fakehost", {"command": "create", "nth": 1, "do": "lose-answer"})
        looked, went = m.started()
        self.assertIn("stopped: an outstanding create", went.lines)
        self.assertIn("a create was sent and no answer came", open(went.doc["forms"][0]).read())
        return m, looked.doc["run"]

    def test_OP7_the_resume_stops_as_outstanding_and_no_invocation_under_the_same_manifest_sends_it_again(self):
        m, run = self.lost("unique", "u1")
        m.set_fake("fakehost", things={})          # the provider lists nothing for a while
        for _ in range(3):
            again = m.resume()
            self.assertIn("stopped: an outstanding create", again.lines)
        self.assertEqual(len(m.calls("fakehost", "create")), 1)

    def test_OP7_a_guarantee_lets_a_replan_offer_it_again_and_it_is_sent_only_after_that_replans_own_go(self):
        m, run = self.lost("unique", "u2")
        m.set_fake("fakehost", things={})
        replanned = m.summon("replan", "demo", "--inputs", m.inputs())
        self.assertIn("an earlier send got no answer", open(replanned.doc["forms"][0]).read())
        self.assertEqual(len(m.calls("fakehost", "create")), 1, "the create was sent before the re-plan's own go")
        went = m.run("go", "--kind", "sunrise", "--name", "demo", "--run", run, "--manifest-sha256", replanned.doc["manifest_sha256"])
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(len(m.calls("fakehost", "create")), 2)
        self.assertEqual(sorted(m.fake("fakehost", "state.json")["things"]), ["demo"], "the fake's state holds two things")

    def test_OP7_with_the_name_then_found_taken_the_replan_is_a_planning_stop(self):
        m, run = self.lost("unique", "u3")
        replanned = m.summon("replan", "demo", "--inputs", m.inputs())
        self.assertEqual(replanned.ending, "stopped")
        self.assertIn("the place is taken by a thing this run did not make: row C1", replanned.lines)
        self.assertEqual(len(m.calls("fakehost", "create")), 1)

    def test_OP7_a_status_read_that_answers_made_completes_on_ground_c_with_no_second_send_and_nothing_lets_a_replan_send(self):
        m, run = self.lost("status-read", "s1")
        replanned = m.summon("replan", "demo", "--inputs", m.inputs())
        went = m.run("go", "--kind", "sunrise", "--name", "demo", "--run", run, "--manifest-sha256", replanned.doc["manifest_sha256"])
        self.assertEqual(went.ending, "complete", went.text)
        done = [r for r in m.journal(run) if r["kind"] == "completion"][0]
        self.assertEqual(done["ground"], "c")
        self.assertEqual([r["source"] for r in m.journal(run) if r["kind"] == "answer"], ["status-read"])
        self.assertEqual(len(m.calls("fakehost", "create")), 1)
        m2, run2 = self.lost("status-read", "s2")
        m2.set_fake("fakehost", things={}, requests={})
        replanned = m2.summon("replan", "demo", "--inputs", m2.inputs())
        went = m2.run("go", "--kind", "sunrise", "--name", "demo", "--run", run2, "--manifest-sha256", replanned.doc["manifest_sha256"])
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(len(m2.calls("fakehost", "create")), 2)
        self.assertEqual(sorted(m2.fake("fakehost", "state.json")["things"]), ["demo"])

    def test_OP7_dropping_the_layer_yields_a_manifest_without_it_and_no_send(self):
        m, run = self.lost("drop", "d1")
        replanned = m.summon("replan", "demo", "--inputs", m.inputs(drop_layers=["hosting"]))
        self.assertIn("not applicable (a layer the project lacks)", open(replanned.doc["forms"][0]).read())
        went = m.run("go", "--kind", "sunrise", "--name", "demo", "--run", run, "--manifest-sha256", replanned.doc["manifest_sha256"])
        self.assertEqual(len(m.calls("fakehost", "create")), 1)
        self.assertIn(went.ending, ("complete", "stopped"), went.text)


class TheRefusedSend(OpCase):
    """A refused send is no send (the owner's ruling, A99; batch 43, A100). LOG-2: "Where the runner refuses a create's send
    before any child is created (SEC-3), a step record of that refusal, naming the create and saying that no child was
    created, is written and synced before the run stops; it is written in that case and in no other, so it stands only where
    no request left the tool". The register entry is the user's name, a base name's value, by the hosting token's channel at
    that invocation alone (SEC-3's test line plants one so): every child of that invocation is refused, and the create's
    look, made by the fake host's own request (SEC-2), starts no child (`rowlib.install_refused_send`)."""

    USER = "zzuserq9"
    ENTRY = {"USER": USER, "FAKEHOST_TOKEN": USER}

    def refused(self, label):
        m = rowlib.install_refused_send(harness.Machine(self.tmp, label, label))
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, env=self.ENTRY)
        return m, looked.doc["run"], went

    def of_c1(self, m, run):
        return [r for r in m.journal(run) if r.get("op") == "C1"]

    def refusal_records(self, m, run):
        return [r for r in self.of_c1(m, run) if r["kind"] == "step" and r.get("step") == "send-refused"]

    def test_LOG2_A99_a_refused_send_leaves_its_start_record_then_the_step_record_of_the_refusal_and_no_call(self):
        """LOG-2's test line: "A refused send: a create whose send the runner refuses leaves in the journal its start record
        and then the step record of that refusal, and the fake records no call; a fake that answers no request, or is killed
        after the child starts, leaves no such record." """
        m, run, went = self.refused("refused")
        self.assertEqual(went.ending, "stopped", went.text)
        records = self.of_c1(m, run)
        self.assertEqual([(r["kind"], r.get("step")) for r in records if r["kind"] != "step" or r.get("step") != "risk-mark"],
                         [("start", None), ("step", "send-refused")], "the journal does not hold the start record, then the refusal's")
        refusal = self.refusal_records(m, run)[0]
        self.assertEqual(refusal["op"], "C1", "the record does not name the create")
        self.assertEqual(refusal["child"], "none created", "the record does not say that no child was created")
        self.assertEqual(refusal["refusal"], "register entry")
        self.assertEqual(m.calls("fakehost"), [], "the fake recorded a call")
        # in no other case: a fake that answers no request (its answer lost; then, apart, one that never answers and is ended
        # at its limit), and a child killed once it has started
        for label, plan, kill in (("lost", {"command": "create", "do": "lose-answer"}, None),
                                  ("hangs", {"command": "create", "do": "hang"}, None),
                                  ("killed", None, lambda e: e["stage"] == "mid" and e["op"] == "child" and e["subject"] == "fakehost")):
            with self.subTest(case=label):
                n = harness.Machine(self.tmp, "no-" + label, "no-" + label)
                decls = rowlib.refused_send_providers()
                decls["fakehost"]["commands"]["create"]["time_limit"] = 1
                rowlib.install(n, rowlib.lane("sunrise", [rowlib.create_looked_by_request("C1")]), providers=decls)
                n.transport = rowlib.ThingsByName(n)
                if plan:
                    n.plan_fake("fakehost", plan)
                looked = n.look()
                went = n.go(looked, kill=kill)
                self.assertTrue(went.killed or went.ending == "stopped", went.text)
                self.assertTrue([e for e in went.events if e["op"] == "child" and e["stage"] == "mid" and e.get("started")],
                                "the child was not started")
                for _ in range(200 if kill else 0):  # a killed invocation's child goes on to its end: wait for it
                    if (n.fake("fakehost", "state.json") or {}).get("things"):
                        break
                    time.sleep(0.05)
                self.assertEqual(len(n.calls("fakehost", "create")), 1, "the child was not started")
                self.assertEqual(self.refusal_records(n, looked.doc["run"]), [], "a step record of a refusal was written")
                self.assertEqual([r["kind"] for r in self.of_c1(n, looked.doc["run"]) if r["kind"] != "step"], ["start"])
                self.assertIn("stopped: an outstanding create", n.resume().lines)

    def test_OP5_A99_a_create_whose_send_was_refused_yields_not_landed_with_nothing_under_its_name_and_foreign_with_a_thing_under_it(self):
        """OP-5's test line: "a create answering `not landed` only where the step record of its send's refusal follows its start
        record (OP-6, OP-7; the owner's ruling, A99), its fixture with a start record and no other record being outstanding
        whatever the world shows; a create whose send was refused yields `not landed` with nothing under its name and
        `foreign` with a thing under it". Each probe yields its answer with no state-changing call: the `not landed` pass is
        ended right after the start record its answer leads to."""
        m, run, went = self.refused("nothing")
        self.assertEqual(went.ending, "stopped", went.text)
        position = m.summon("status").doc["position"]
        probed = m.summon("resume", "demo", "--position", position, "--word", "go on",
                          kill=lambda e: e["stage"] == "post" and e["op"] == "journal" and e.get("operation") == "C1"
                          and e["subject"] == "start")
        self.assertTrue(probed.killed, probed.text)
        starts = [r for r in self.of_c1(m, run) if r["kind"] == "start"]
        self.assertEqual([r["probe"] for r in starts], ["ready", "not landed"], "the probe did not answer `not landed`")
        self.assertEqual(m.calls("fakehost", "create"), [], "a state-changing call was made across the probe")
        # a thing under its name, made by another actor after the refusal
        m, run, went = self.refused("taken")
        m.set_fake("fakehost", things={"demo": {"id": "theirs", "kind": "repo", "state": "active", "name": "demo"}})
        before = m.fake("fakehost", "state.json")
        probed = m.resume()
        self.assertEqual(probed.ending, "stopped", probed.text)
        self.assertIn("stopped: foreign", probed.lines)
        self.assertIn("operation: C1", probed.lines)
        self.assertEqual(len([r for r in self.of_c1(m, run) if r["kind"] == "start"]), 1, "a new start record was written")
        self.assertEqual(m.calls("fakehost", "create"), [], "a state-changing call was made across the probe")
        self.assertEqual(m.fake("fakehost", "state.json"), before)

    def test_OP6_A99_a_refused_send_stops_on_the_refusal_and_the_next_resume_on_his_word_starts_it_again_and_sends_once(self):
        """OP-6's test line: "A refused send: a create whose send the runner refuses ends that invocation `stopped` on the
        refusal with no call recorded by the fake; the next resume, on his word to go on, writes a new start record and sends
        once, and the fake holds one thing." Its `not landed` cell for a create: "a new start record; the send, on his word to
        go on (RUN-10)": a summons with no word sends nothing."""
        m, run, went = self.refused("again")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: the runner refused the command: register entry", went.lines)
        self.assertIn("operation: C1", went.lines)
        self.assertIn("the runner refused the command: register entry", open(went.doc["forms"][0]).read())
        self.assertEqual(m.calls("fakehost"), [], "the fake recorded a call")
        status = m.summon("status")
        self.assertEqual(status.ending, "stopped", status.text)
        self.assertEqual(m.calls("fakehost", "create"), [], "a summons with no word sent the create")
        resumed = m.resume()
        self.assertEqual(resumed.ending, "complete", resumed.text)
        starts = [r for r in self.of_c1(m, run) if r["kind"] == "start"]
        self.assertEqual([r["probe"] for r in starts], ["ready", "not landed"])
        self.assertEqual(len(m.calls("fakehost", "create")), 1, "the create was not sent once")
        self.assertEqual(sorted(m.fake("fakehost", "state.json")["things"]), ["demo"], "the fake does not hold one thing")
        self.assertEqual([r["ground"] for r in self.of_c1(m, run) if r["kind"] == "completion"], ["a"])

    def test_OP7_A99_after_the_refusal_record_the_create_is_not_outstanding_and_a_kill_before_it_leaves_it_outstanding_for_ever(self):
        """OP-7's test line: "A refused send: with the step record of the refusal after its start record, the create is not
        outstanding and the next resume sends it once; a kill after the start record and before that step record leaves it
        outstanding, and no later invocation under the same manifest sends it (the owner's ruling, A99)." OP-7: "An outstanding
        create stays in the journal, is read by every later look for the project key": a later run's look reads a refused
        send as no outstanding create, and a create killed before its refusal record as one (a row resolved only by dropping
        its layer: a planning stop)."""
        m, run, went = self.refused("sent")
        self.assertEqual(len(self.refusal_records(m, run)), 1)
        resumed = m.resume()
        self.assertEqual(resumed.ending, "complete", resumed.text)
        self.assertEqual(len(m.calls("fakehost", "create")), 1)
        # killed after the start record and before the step record of the refusal
        k = rowlib.install_refused_send(harness.Machine(self.tmp, "kill", "kill"))
        looked = k.look()
        killed = k.go(looked, env=self.ENTRY, kill=lambda e: e["stage"] == "pre" and e["op"] == "journal"
                      and e.get("operation") == "C1" and e.get("step") == "send-refused")
        self.assertTrue(killed.killed, killed.text)
        self.assertEqual([r["kind"] for r in self.of_c1(k, looked.doc["run"]) if r["kind"] != "step"], ["start"])
        self.assertEqual(self.refusal_records(k, looked.doc["run"]), [])
        for turn in range(3):
            again = k.resume()
            with self.subTest(turn=turn):
                self.assertIn("stopped: an outstanding create", again.lines)
                self.assertEqual(k.calls("fakehost", "create"), [], "a later invocation under the same manifest sent it")
        # a later run's look under the same key, each earlier run closed, its row resolved only by dropping its layer
        for machine, outstanding in ((None, False), (k, True)):
            n = machine if machine is not None else self.refused("later")[0]
            with self.subTest(earlier="a refused send" if not outstanding else "killed before the refusal record"):
                self.assertEqual(n.summon("close", "demo", "--word", "close").ending, "closed")
                row = rowlib.create_looked_by_request("C1")
                row["lost_answer"] = {"way": "by dropping the layer only"}
                row["thing"]["layer"] = "hosting"
                rowlib.install_refused_send(n, [row])
                later = n.look()
                cause = "a create was sent and no answer came, and only dropping its layer resolves it: row C1"
                if outstanding:
                    self.assertEqual(later.ending, "refused", later.text)
                    self.assertIn(cause, later.lines)
                else:
                    self.assertEqual(later.ending, "preview", later.text)
                    self.assertNotIn(cause, later.text)
                    self.assertNotIn("an earlier send got no answer", open(later.doc["forms"][0]).read())


class ARefusedCommandOwesNoReceipt(OpCase):
    """SEC-12 (batch 44, A102; A104): "A command the runner refuses (SEC-3) has no execution and starts no child: the runner's
    check is made before that step record, and where it refuses, no receipt is due." Its test line: "A refused command with a
    secret field: the runner refuses a create's send whose declaration has one; the journal holds no receipt-due record for
    it, and no status form says that a secret may have been received and lost." The create of `TheRefusedSend`, its send's
    declaration given a secret field (`rowlib.secret_send_providers`); the register entry the user's name, a base name's value,
    by the hosting token's channel at the go alone."""

    ENTRY = TheRefusedSend.ENTRY
    LOST = "a secret may have been received and lost"

    def test_SEC12_A102_a_refused_command_with_a_secret_field_has_no_receipt_due_and_no_status_form_says_a_secret_may_have_been_lost(self):
        m = rowlib.install_refused_send(harness.Machine(self.tmp, "secret", "secret"), providers=rowlib.secret_send_providers())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        went = m.go(looked, env=self.ENTRY)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: the runner refused the command: register entry", went.lines)
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] in ("pre", "mid")], [], "a child was created")
        self.assertEqual(m.calls("fakehost"), [], "the fake recorded a call")
        self.assertTrue(went.doc.get("forms"), went.text)
        for path in went.doc["forms"]:
            self.assertNotIn(self.LOST, open(path).read(), "a status form says that a secret may have been received and lost")
        self.assertNotIn(self.LOST, went.text)
        status = m.summon("status")
        self.assertEqual(status.ending, "stopped", status.text)
        self.assertNotIn(self.LOST, open(status.doc["forms"][0]).read(), "a later status form says that a secret may have been lost")
        self.assertEqual([r for r in m.journal(run) if r.get("step") == "receipt-due"], [],
                         "the journal holds a receipt-due record for a command the runner refused")
        self.assertEqual([(r["kind"], r.get("step")) for r in m.journal(run) if r.get("op") == "C1"],
                         [("start", None), ("step", "send-refused")])
        # the next resume, on his word and with no entry, sends it once: that send is the command's first execution, its
        # receipt-due record before the child and its receipt after it
        resumed = m.resume()
        self.assertEqual(resumed.ending, "complete", resumed.text)
        self.assertEqual(len(m.calls("fakehost", "create")), 1)
        dues = [r for r in m.journal(run) if r.get("step") == "receipt-due"]
        self.assertEqual([(r["op"], r["execution"]) for r in dues], [("C1", 1)])
        receipts = [r for r in m.journal(run) if r.get("step") == "receipt"]
        self.assertEqual([(r["op"], r["execution"], r["field"]) for r in receipts], [("C1", 1, "token")])
        self.assertNotIn(self.LOST, open(resumed.doc["forms"][0]).read())


class TheFramesOwnRequestRefused(OpCase):
    """RK16 (the owner's ruling A103; batch 44B, A104). LOG-2: "A create whose send is a request of the frame's own (SEC-2),
    refused before any connection to the host is opened, has its start record and no record of the refusal, and is
    outstanding (OP-7): that is RK16". OP-7: "A create whose send is a request of the frame's own (SEC-2), refused before any
    connection to the host is opened, has no such record and is outstanding". The create's send is the fake host's own
    request `api-make` (`rowlib.install_request_send`); its look and after-check are children. The frame refuses the request
    before any connection in two passes: a register entry in a part of its path (the hosting token's channel, at the go
    alone, holds `v1/make`, which the request's path holds and no child's argument or environment does), and a fake host
    with no host."""

    TOKEN = "v1/make"
    PASSES = (("register entry", True, {"FAKEHOST_TOKEN": "v1/make"}), ("no host", False, {}))

    def refused(self, label, host, env):
        m = rowlib.install_request_send(harness.Machine(self.tmp, label, label), host=host)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, env=env)
        return m, looked.doc["run"], went

    def of_c1(self, m, run):
        return [r for r in m.journal(run) if r.get("op") == "C1"]

    def test_LOG2_A103_RK16_a_create_whose_own_request_is_refused_before_any_connection_leaves_its_start_record_alone(self):
        """LOG-2's test line: "A create whose send is a request of the frame's own, refused before any connection to the fake
        host is opened, leaves its start record alone, with no record of the refusal, and the fake host records no connection
        (A103; RK16)." """
        for word, host, env in self.PASSES:
            with self.subTest(refusal=word):
                m, run, went = self.refused(word.replace(" ", "-"), host, env)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: the runner refused the command: %s" % word, went.lines)
                self.assertEqual([(r["kind"], r.get("step")) for r in self.of_c1(m, run)], [("start", None)],
                                 "the journal does not hold the start record alone")
                self.assertEqual([r for r in m.journal(run) if r.get("step") == "send-refused"], [], "a record of the refusal was written")
                self.assertEqual(m.transport.records, [], "the fake host records a connection")
                self.assertEqual(m.calls("fakehost", "create"), [])
                self.assertNotIn(self.TOKEN, went.text)

    def test_OP7_A103_RK16_the_next_resume_finds_it_outstanding_stops_and_sends_nothing_and_no_later_invocation_sends_it(self):
        """OP-7's test line: "A refused request of the frame's own: a create whose send is such a request, refused before any
        connection to the fake host is opened, is outstanding at the next resume, which stops and sends nothing, and no later
        invocation under the same manifest sends it (A103; RK16)." OP-7's rule: "An outstanding create stays in the journal, is
        read by every later look for the project key": a later run's look reads it as outstanding (a row resolved only by
        dropping its layer: a planning stop)."""
        for word, host, env in self.PASSES:
            with self.subTest(refusal=word):
                m, run, went = self.refused("o-" + word.replace(" ", "-"), host, env)
                self.assertEqual(went.ending, "stopped", went.text)
                for turn in range(3):
                    again = m.resume()
                    self.assertEqual(again.ending, "stopped", again.text)
                    self.assertIn("stopped: an outstanding create", again.lines)
                    self.assertEqual(m.transport.records, [], "a later invocation under the same manifest sent it")
                    self.assertEqual(m.calls("fakehost", "create"), [])
                self.assertEqual([r["kind"] for r in self.of_c1(m, run)], ["start"], "a new start record was written")
                status = m.summon("status")
                self.assertEqual(status.ending, "stopped", status.text)
                self.assertIn("a create was sent and no answer came", open(status.doc["forms"][0]).read())
                self.assertEqual(m.summon("close", "demo", "--word", "close").ending, "closed")
                row = rowlib.create_sent_by_request("C1")
                row["lost_answer"] = {"way": "by dropping the layer only"}
                row["thing"]["layer"] = "hosting"
                rowlib.install_request_send(m, [row], host=host)
                later = m.look()
                self.assertEqual(later.ending, "refused", later.text)
                self.assertIn("a create was sent and no answer came, and only dropping its layer resolves it: row C1", later.lines)
                self.assertEqual(m.transport.records, [])

    def test_RISK1_A103_RK16_no_record_carries_a_mark_for_RK16_and_a_create_left_outstanding_after_its_own_request_was_refused_carries_none(self):
        """RISK-1: "RK1, RK6, RK7, RK8, RK10, RK11, RK12, RK14, RK15 and RK16 belong to no one operation, and no mark is recorded
        for any of them." Its test line: "no record carries a mark for ... RK16, ... and a create left outstanding after its own
        request was refused before any connection among them." A row that would carry RK16 on its construction is not built
        (ROW-1: "an accepted risk that does not cover its construction")."""
        for word, host, env in self.PASSES:
            with self.subTest(refusal=word):
                m, run, went = self.refused("r-" + word.replace(" ", "-"), host, env)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: an outstanding create", m.resume().lines)
                for record in m.journal(run):
                    self.assertNotEqual(record.get("step"), "risk-mark", "a record carries a mark: %r" % record)
                    self.assertNotIn("risk", record)
                    self.assertNotIn("RK16", json.dumps(record))
        n = harness.Machine(self.tmp, "rk16-row", "rk16-row")
        row = rowlib.create_sent_by_request("C1")
        row["construction"]["risks"] = ["RK16"]
        rowlib.install_request_send(n, [row])
        looked = n.look()
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row C1, entry construction: an accepted risk that does not cover its construction", looked.lines)


class TheFramesOwnRequestWithASecretField(OpCase):
    """RK17 (the owner's ruling A107; batch 45B, A108). SEC-12: "A request of the frame's own (SEC-2) that has a secret field is
    not so: its step record that a receipt is due is written before the frame's own checks of that request, and where the
    frame refuses it before any connection to the host is opened, the receipt stays due and is never given: every status
    form of that run says that a secret may have been received and lost, though nothing was sent. That is RK17, which the
    owner accepted (A107; RISK-1)." The create of `TheFramesOwnRequestRefused`, its send the fake host's own request
    `api-make`, given a secret field `token` (`rowlib.secret_request_providers`); the same two passes."""

    PASSES = TheFramesOwnRequestRefused.PASSES
    LOST = "a secret may have been received and lost: operation C1, execution 1, field token"

    def refused(self, label, host, env):
        m = rowlib.install_request_send(harness.Machine(self.tmp, label, label), host=host,
                                        providers=rowlib.secret_request_providers(host))
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, env=env)
        return m, looked.doc["run"], went

    def test_SEC12_A107_RK17_a_refused_request_of_the_frames_own_with_a_secret_field_leaves_its_receipt_due_and_every_status_form_says_so(self):
        """SEC-12's test line: "A refused request of the frame's own with a secret field: the frame refuses it for an entry of
        the register in a part of its path, and in a second pass for a provider with no host; the fake host records no
        connection, the journal holds the receipt-due record and no receipt after it, and the next status form says that a
        secret may have been received and lost, naming the operation, the execution and the field, though nothing was sent
        (A107; RK17)." """
        for word, host, env in self.PASSES:
            with self.subTest(refusal=word):
                m, run, went = self.refused("rk17-" + word.replace(" ", "-"), host, env)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: the runner refused the command: %s" % word, went.lines)
                self.assertEqual(m.transport.records, [], "the fake host records a connection")
                self.assertEqual(m.calls("fakehost", "create"), [])
                c1 = [r for r in m.journal(run) if r.get("op") == "C1"]
                self.assertEqual([(r["kind"], r.get("step")) for r in c1], [("start", None), ("step", "receipt-due")],
                                 "not the receipt-due record with no receipt after it")
                due = [r for r in c1 if r.get("step") == "receipt-due"][0]
                self.assertEqual((due["execution"], [f["field"] for f in due["fields"]]), (1, ["token"]))
                self.assertIn(self.LOST, open(went.doc["forms"][0]).read(), "the go's status form does not say so")
                status = m.summon("status")
                self.assertEqual(status.ending, "stopped", status.text)
                self.assertIn(self.LOST, open(status.doc["forms"][0]).read(),
                              "the next status form does not say that a secret may have been received and lost")
                self.assertEqual([r for r in m.journal(run) if r.get("step") == "receipt"], [], "a receipt was given")
                self.assertNotIn(self.TOKEN_WORD, went.text + status.text)

    TOKEN_WORD = TheFramesOwnRequestRefused.TOKEN

    def test_RISK1_A107_RK17_no_record_carries_a_mark_for_RK17_and_a_receipt_left_due_after_its_own_request_was_refused_carries_none(self):
        """RISK-1: "RK1, RK6, RK7, RK8, RK10, RK11, RK12, RK14, RK15, RK16 and RK17 belong to no one operation, and no mark is
        recorded for any of them." Its test line: "no record carries a mark for ... RK17, ... and a receipt left due after a
        request of the frame's own with a secret field was refused before any connection, among them." A row that would carry
        RK17 on its construction is not built (ROW-1: "an accepted risk that does not cover its construction")."""
        for word, host, env in self.PASSES:
            with self.subTest(refusal=word):
                m, run, went = self.refused("rk17m-" + word.replace(" ", "-"), host, env)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertEqual(m.summon("status").ending, "stopped")
                self.assertTrue([r for r in m.journal(run) if r.get("step") == "receipt-due"], "the fixture's premise: a receipt due")
                for record in m.journal(run):
                    self.assertNotEqual(record.get("step"), "risk-mark", "a record carries a mark: %r" % record)
                    self.assertNotIn("risk", record)
                    self.assertNotIn("RK17", json.dumps(record))
        n = harness.Machine(self.tmp, "rk17-row", "rk17-row")
        row = rowlib.create_sent_by_request("C1")
        row["construction"]["risks"] = ["RK17"]
        rowlib.install_request_send(n, [row], providers=rowlib.secret_request_providers())
        looked = n.look()
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row C1, entry construction: an accepted risk that does not cover its construction", looked.lines)


def then(first, second):
    """Two hooks over one event: `first` (a planted act, which never kills) and then `second` (a kill, or None)."""
    def hook(event):
        hit = first(event)
        return hit or (second is not None and second(event))
    return hook


class AProgramNotFound(OpCase):
    """A program not found at an operation (the owner's ruling A109; batch 46, A110). SEC-3's command row: "For a command of an
    operation it is also a refusal of the runner's (the refusals row), and so is a file that the runner found and that is
    gone as it starts it, so that no child is created; a start that creates a child is no refusal, however that child ends
    (OP-6) (the owner's ruling, A109)." The create of `TheRefusedSend` (its look the fake host's own request, no child; its
    send `fakehost create`, a child). The fake host's program stands in one folder of the fixture's own, which its settings
    name in the place of the tests' fakes folder (`rowlib.program_folder`). Two passes: the program removed from the search
    list after the look, its file taken out of that folder before the go; and its file removed by the fixture's file system
    as the runner starts it, at the runner's own record that it is about to start that child (`pre child`)."""

    PASSES = ("at the search", "as the runner starts it")
    LOST = "a secret may have been received and lost"

    def refused(self, label, where, providers=None, kill=None):
        m = rowlib.install_refused_send(harness.Machine(self.tmp, label, label), providers=providers)
        folder = rowlib.program_folder(m)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        if where == "at the search":
            rowlib.take_program(folder)
            hook = kill
        else:
            hook = then(planted(at("pre", "child", "fakehost"), lambda: rowlib.take_program(folder)), kill)
        went = m.go(looked, kill=hook)
        return m, looked.doc["run"], went, folder

    def of_c1(self, m, run):
        return [r for r in m.journal(run) if r.get("op") == "C1"]

    def no_start(self, m, went, where):
        """The fake records no start: no call of its own, and no child the runner started."""
        self.assertEqual(m.calls("fakehost"), [], "the fake recorded a call")
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "mid"], [], "a child was started")
        if where == "as the runner starts it":     # the pass's premise: the runner found the file and was starting it
            self.assertTrue([e for e in went.events if e["op"] == "child" and e["stage"] == "pre" and e["subject"] == "fakehost"],
                            "the runner did not come to start the child")

    def test_LOG2_A109_a_program_not_found_at_the_send_leaves_the_start_record_then_the_refusals_step_record_and_no_start(self):
        """LOG-2's test line: "A program not found at the send, removed from the search list after the look, and in a second
        pass its file removed as the runner starts it, so that no child is created: the create leaves its start record and
        then the step record of that refusal, and the fake records no start (the owner's ruling, A109)." """
        for where in self.PASSES:
            with self.subTest(where=where):
                m, run, went, _folder = self.refused("log2-" + where.split()[-1], where)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
                self.assertEqual([(r["kind"], r.get("step")) for r in self.of_c1(m, run)], [("start", None), ("step", "send-refused")],
                                 "the journal does not hold the start record and then the step record of the refusal")
                refusal = [r for r in self.of_c1(m, run) if r.get("step") == "send-refused"][0]
                self.assertEqual((refusal["refusal"], refusal["child"]), ("tool not found", "none created"))
                self.no_start(m, went, where)

    def test_OP6_A109_the_invocation_ends_stopped_on_the_refusal_and_the_next_resume_the_program_put_back_sends_once(self):
        """OP-6's test line: "So too a create's send whose program is not found, removed from the search list after the look,
        and in a second pass its file removed as the runner starts it: the invocation ends `stopped` on that refusal with no
        start recorded by the fake, and the next resume, the program put back, on his word writes a new start record and sends
        once, and the fake holds one thing (the owner's ruling, A109)." """
        for where in self.PASSES:
            with self.subTest(where=where):
                m, run, went, folder = self.refused("op6-" + where.split()[-1], where)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: the runner refused the command: tool not found", went.lines, "not stopped on that refusal")
                self.assertIn("operation: C1", went.lines)
                self.assertIn("the runner refused the command: tool not found", open(went.doc["forms"][0]).read())
                self.no_start(m, went, where)
                rowlib.put_program(folder)
                status = m.summon("status")                       # no word: nothing is sent
                self.assertEqual(status.ending, "stopped", status.text)
                self.assertEqual(m.calls("fakehost", "create"), [], "a summons with no word sent the create")
                resumed = m.resume()
                self.assertEqual(resumed.ending, "complete", resumed.text)
                starts = [r for r in self.of_c1(m, run) if r["kind"] == "start"]
                self.assertEqual([r["probe"] for r in starts], ["ready", "not landed"], "no new start record from `not landed`")
                self.assertEqual(len(m.calls("fakehost", "create")), 1, "the create was not sent once")
                self.assertEqual(sorted(m.fake("fakehost", "state.json")["things"]), ["demo"], "the fake does not hold one thing")

    def test_OP7_A109_with_the_refusals_record_it_is_not_outstanding_a_kill_before_it_or_a_fake_started_then_killed_leaves_it_outstanding(self):
        """OP-7's test line: "A program not found at the send, at the runner's search and in a second pass as it starts the
        file it found: with the step record of that refusal after its start record, the create is not outstanding and the
        next resume sends it once; a kill after the start record and before that step record leaves it outstanding, and no
        later invocation under the same manifest sends it; and a fake that is started and then killed leaves it outstanding
        (the owner's ruling, A109)." """
        before_the_record = lambda e: (e["stage"] == "pre" and e["op"] == "journal" and e.get("operation") == "C1"   # noqa: E731
                                       and e.get("step") == "send-refused")
        for where in self.PASSES:
            with self.subTest(where=where, kill="none"):
                m, run, went, folder = self.refused("op7-" + where.split()[-1], where)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertNotIn("an outstanding create", went.text)
                rowlib.put_program(folder)
                status = m.summon("status")
                self.assertNotIn("a create was sent and no answer came", open(status.doc["forms"][0]).read(), "it reads as outstanding")
                self.assertEqual(m.resume().ending, "complete")
                self.assertEqual(len(m.calls("fakehost", "create")), 1, "the next resume did not send it once")
            with self.subTest(where=where, kill="after the start record, before the step record"):
                k, run, killed, folder = self.refused("op7k-" + where.split()[-1], where, kill=before_the_record)
                self.assertTrue(killed.killed, killed.text)
                self.assertEqual([r["kind"] for r in self.of_c1(k, run)], ["start"])
                rowlib.put_program(folder)
                for turn in range(3):
                    again = k.resume()
                    self.assertIn("stopped: an outstanding create", again.lines, "turn %d" % turn)
                    self.assertEqual(k.calls("fakehost", "create"), [], "a later invocation under the same manifest sent it")
        with self.subTest(kill="a fake started and then killed"):
            d = rowlib.install_refused_send(harness.Machine(self.tmp, "op7-died", "op7-died"))
            rowlib.program_folder(d)
            d.plan_fake("fakehost", {"command": "create", "nth": 1, "do": "die"})
            looked = d.look()
            went = d.go(looked)
            self.assertEqual(went.ending, "stopped", went.text)
            self.assertTrue([e for e in went.events if e["op"] == "child" and e["stage"] == "mid" and e.get("started")],
                            "the child was not started")
            self.assertEqual(len(d.calls("fakehost", "create")), 1, "the fake was not started")
            self.assertEqual([r for r in self.of_c1(d, looked.doc["run"]) if r.get("step") == "send-refused"], [],
                             "a step record of a refusal was written for a child that was started")
            for turn in range(2):
                again = d.resume()
                self.assertIn("stopped: an outstanding create", again.lines, "turn %d" % turn)
                self.assertEqual(len(d.calls("fakehost", "create")), 1, "a later invocation sent it again")

    def test_SEC12_A109_a_program_not_found_for_a_command_with_a_secret_field_owes_no_receipt_at_the_search_and_gives_each_receipt_at_the_start(self):
        """SEC-12: "The runner's search for the program is part of its check: a program in no folder of the search list is
        refused there, before that step record, and no receipt is due (SEC-3; the owner's ruling, A109). Where the file the
        runner found is gone as it starts it, so that no child is created, the refusal is met after that step record: a step
        record then gives the receipt of each field, one for each, saying that no child was started, and none is left due
        (A109)." Its test line: "A program not found, for a command with a secret field: with the program removed from the
        search list after the look, the runner refuses it at its search, the fake recording no start, the journal holds no
        receipt-due record for it, and no status form says that a secret may have been received and lost; in a second pass the
        fixture's file system removes the file as the runner starts it, no child is created, the journal holds the receipt-due
        record and then each field's receipt saying in fixed words that no child was started, and no status form says so
        either (the owner's ruling, A109)." The create's send given a secret field (`rowlib.secret_send_providers`)."""
        for where in self.PASSES:
            with self.subTest(where=where):
                m, run, went, _folder = self.refused("sec12-" + where.split()[-1], where, providers=rowlib.secret_send_providers())
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: the runner refused the command: tool not found", went.lines)
                self.no_start(m, went, where)
                c1 = [(r["kind"], r.get("step")) for r in self.of_c1(m, run)]
                receipts = [r for r in self.of_c1(m, run) if r.get("step") == "receipt"]
                if where == "at the search":
                    self.assertEqual(c1, [("start", None), ("step", "send-refused")], "a receipt-due record was written")
                else:
                    self.assertEqual(c1, [("start", None), ("step", "receipt-due"), ("step", "receipt"), ("step", "send-refused")],
                                     "not the receipt-due record and then each field's receipt")
                    due = [r for r in self.of_c1(m, run) if r.get("step") == "receipt-due"][0]
                    self.assertEqual([f["field"] for f in due["fields"]], ["token"])
                    self.assertEqual([(r["execution"], r["field"], r["outcome"]) for r in receipts], [(1, "token", "no child started")],
                                     "the receipt does not say in fixed words that no child was started")
                    self.assertNotIn("reference", receipts[0])
                for path in went.doc["forms"]:
                    self.assertNotIn(self.LOST, open(path).read(), "a status form says that a secret may have been lost")
                status = m.summon("status")
                self.assertEqual(status.ending, "stopped", status.text)
                self.assertNotIn(self.LOST, open(status.doc["forms"][0]).read(), "a later status form says so")
                self.assertNotIn(self.LOST, went.text + status.text)


class AStartTheSystemRefuses(OpCase):
    """A start the system refuses before the program runs, the file still there (the owner's ruling A113; batches 48 and 48B,
    A114, A115). SEC-3's command row: "So too is a start of a command of an operation that the system refuses before the
    program runs, the file still there: the file not runnable, a program its first line names missing, a format the system
    cannot run, the working folder gone, or no process to be had, wherever the system's answer shows that the program never
    ran. Such a start creates no child of the program, whatever the system made for the start and ended before the program
    ran (the owner's ruling, A113). A start whose answer the runner cannot read as one in which the program never ran, and a
    start that creates a child, are no refusal, however that child ends: they stay as OP-6 has a killed child, a create
    there outstanding (OP-7; A109, A113)." The create of `TheRefusedSend` (its look the fake host's own request, no child; its
    send `fakehost create`, a child), the fake host's program in a folder of the fixture's own (`rowlib.program_folder`).
    Five passes, one per cause, each planted after the look (`rowlib.refuse_start`); the row's working folder is the run
    directory, where the runner starts a row's command that declares none; and the pass of an answer the runner cannot read,
    which the fixture's system gives, as it gives the answer that no process can be had (A115)."""

    CAUSES = rowlib.START_CAUSES
    LOST = "a secret may have been received and lost"
    REFUSED = "the runner refused the command: start refused"

    def refused(self, label, cause, providers=None, kill=None):
        m = rowlib.install_refused_send(harness.Machine(self.tmp, label, label), providers=providers)
        folder = rowlib.program_folder(m)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        hook, put_right = rowlib.refuse_start(m, cause, os.path.join(folder, "fakehost"), m.facts.run_dir(run), "fakehost")
        went = m.go(looked, kill=then(hook, kill) if hook is not None else kill)
        return m, run, went, put_right

    def label(self, kind, cause):
        return "%s-%d" % (kind, (self.CAUSES + (rowlib.UNREADABLE_START,)).index(cause))

    def of_c1(self, m, run):
        return [r for r in m.journal(run) if r.get("op") == "C1"]

    def no_start(self, m, went):
        """The fake records no start: no call of its own, no child the runner started; and the pass's premise, that the
        runner found the file and came to start it."""
        self.assertEqual(m.calls("fakehost"), [], "the fake recorded a call")
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "mid"], [], "a child was started")
        self.assertTrue([e for e in went.events if e["op"] == "child" and e["stage"] == "pre" and e["subject"] == "fakehost"],
                        "the runner did not come to start the child")

    def test_LOG2_A113_a_start_the_system_refuses_with_the_file_still_there_leaves_the_start_record_then_the_refusals_step_record_and_no_start(self):
        """LOG-2's test line: "A start the system refuses with the file still there, in five passes after the look (the
        fixture's file made not runnable, its first line made to name a program in no folder, its bytes replaced by bytes of
        no format the system can run with no first line naming a program, the row's working folder removed, and the
        fixture's system answering the start that no process can be had): the create leaves its start record and then the
        step record of that refusal, and the fake records no start; a start whose failure the runner cannot read as the
        program never having run leaves no such record (the owner's ruling, A113)." """
        for cause in self.CAUSES:
            with self.subTest(cause=cause):
                m, run, went, _put_right = self.refused(self.label("log2", cause), cause)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
                self.assertEqual([(r["kind"], r.get("step")) for r in self.of_c1(m, run)], [("start", None), ("step", "send-refused")],
                                 "the journal does not hold the start record and then the step record of the refusal")
                refusal = [r for r in self.of_c1(m, run) if r.get("step") == "send-refused"][0]
                self.assertEqual((refusal["refusal"], refusal["child"]), ("start refused", "none created"))
                self.no_start(m, went)
        with self.subTest(cause=rowlib.UNREADABLE_START):
            m, run, went, _put_right = self.refused(self.label("log2", rowlib.UNREADABLE_START), rowlib.UNREADABLE_START)
            self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
            self.assertEqual([(r["kind"], r.get("step")) for r in self.of_c1(m, run)], [("start", None)],
                             "a step record of a refusal was written for a start the runner cannot read as never ran")
            self.assertEqual(m.calls("fakehost"), [], "the fixture's system started the fake")

    def test_OP6_A113_the_invocation_ends_stopped_on_the_refusal_and_the_next_resume_the_cause_put_right_sends_once(self):
        """OP-6's test line: "So too in five passes of a start the system refuses with the file still there (the fixture's
        file made not runnable after the look, its first line made to name a program in no folder, its bytes replaced by
        bytes of no format the system can run with no first line naming a program, the row's working folder removed, and the
        fixture's system answering the start that no process can be had): the invocation ends `stopped` on that refusal with
        no start recorded by the fake, and the next resume, the cause put right, on his word writes a new start record and
        sends once, and the fake holds one thing (the owner's ruling, A113)." """
        for cause in self.CAUSES:
            with self.subTest(cause=cause):
                m, run, went, put_right = self.refused(self.label("op6", cause), cause)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: " + self.REFUSED, went.lines, "not stopped on that refusal")
                self.assertIn("operation: C1", went.lines)
                self.assertIn(self.REFUSED, open(went.doc["forms"][0]).read(), "the form does not name the refusal")
                self.no_start(m, went)
                put_right()
                status = m.summon("status")                       # no word: nothing is sent
                self.assertEqual(status.ending, "stopped", status.text)
                self.assertEqual(m.calls("fakehost", "create"), [], "a summons with no word sent the create")
                resumed = m.resume()
                self.assertEqual(resumed.ending, "complete", resumed.text)
                starts = [r for r in self.of_c1(m, run) if r["kind"] == "start"]
                self.assertEqual([r["probe"] for r in starts], ["ready", "not landed"], "no new start record from `not landed`")
                self.assertEqual(len(m.calls("fakehost", "create")), 1, "the create was not sent once")
                self.assertEqual(sorted(m.fake("fakehost", "state.json")["things"]), ["demo"], "the fake does not hold one thing")

    def test_OP7_A113_with_the_refusals_record_it_is_not_outstanding_a_kill_before_it_or_an_answer_not_read_as_never_ran_leaves_it_outstanding(self):
        """OP-7's test line: "A start the system refuses with the file still there, in the same five passes as LOG-2's test
        line: with the step record of that refusal after its start record, the create is not outstanding and the next resume
        sends it once; a kill after the start record and before that step record leaves it outstanding; and a start whose
        failure the runner cannot read as the program never having run leaves it outstanding; in both no later invocation
        under the same manifest sends it (the owner's ruling, A113)." """
        before_the_record = lambda e: (e["stage"] == "pre" and e["op"] == "journal" and e.get("operation") == "C1"   # noqa: E731
                                       and e.get("step") == "send-refused")
        for cause in self.CAUSES:
            with self.subTest(cause=cause, kill="none"):
                m, run, went, put_right = self.refused(self.label("op7", cause), cause)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertNotIn("an outstanding create", went.text)
                put_right()
                status = m.summon("status")
                self.assertNotIn("a create was sent and no answer came", open(status.doc["forms"][0]).read(), "it reads as outstanding")
                self.assertEqual(m.resume().ending, "complete")
                self.assertEqual(len(m.calls("fakehost", "create")), 1, "the next resume did not send it once")
            with self.subTest(cause=cause, kill="after the start record, before the step record"):
                k, run, killed, put_right = self.refused(self.label("op7k", cause), cause, kill=before_the_record)
                self.assertTrue(killed.killed, killed.text)
                self.assertEqual([r["kind"] for r in self.of_c1(k, run)], ["start"])
                put_right()
                for turn in range(3):
                    again = k.resume()
                    self.assertIn("stopped: an outstanding create", again.lines, "turn %d" % turn)
                    self.assertEqual(k.calls("fakehost", "create"), [], "a later invocation under the same manifest sent it")
        with self.subTest(cause=rowlib.UNREADABLE_START):
            u, run, went, put_right = self.refused(self.label("op7", rowlib.UNREADABLE_START), rowlib.UNREADABLE_START)
            self.assertEqual(went.ending, "stopped", went.text)
            self.assertEqual([r["kind"] for r in self.of_c1(u, run)], ["start"], "not its start record alone")
            put_right()
            for turn in range(3):
                again = u.resume()
                self.assertIn("stopped: an outstanding create", again.lines, "turn %d" % turn)
                self.assertEqual(u.calls("fakehost", "create"), [], "a later invocation under the same manifest sent it")

    def test_OP7_A117_a_start_the_system_refuses_for_an_argument_list_too_long_leaves_the_create_outstanding_and_no_later_invocation_sends_it(self):
        """OP-7's test line (batch 49, A117): "and a start whose failure the runner cannot read as the program never having run
        leaves it outstanding, and so does a start the system refuses for a cause that is none of the five, an argument list
        too long; in each no later invocation under the same manifest sends it (the owner's ruling, A113; A116)." SEC-3's
        command row: "for one of these five causes and for no other". The fixture's system answers E2BIG naming the file the
        runner started, a file still there (`rowlib.ARG_LIST_TOO_LONG`)."""
        m, run, went, put_right = self.refused("op7-e2big", rowlib.ARG_LIST_TOO_LONG)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
        self.assertIn("stopped: an outstanding create", went.lines, went.text)
        self.assertNotIn(self.REFUSED, went.text, "a cause none of the five was named as a refusal")
        self.assertEqual([(r["kind"], r.get("step")) for r in self.of_c1(m, run)], [("start", None)],
                         "a step record of a refusal was written for a cause none of the five")
        self.assertEqual(m.calls("fakehost"), [], "the fixture's system started the fake")
        status = m.summon("status")
        self.assertIn("a create was sent and no answer came", open(status.doc["forms"][0]).read(), "it does not read as outstanding")
        put_right()
        for turn in range(3):
            again = m.resume()
            self.assertIn("stopped: an outstanding create", again.lines, "turn %d" % turn)
            self.assertEqual(m.calls("fakehost", "create"), [], "a later invocation under the same manifest sent it")

    def test_SEC12_A113_a_start_the_system_refuses_for_a_command_with_a_secret_field_gives_each_receipt_saying_no_child_was_started(self):
        """SEC-12: "Where the file the runner found is gone as it starts it, or the system refuses the start before the
        program runs, its answer showing that the program never ran (SEC-3), so that no child is created, the refusal is met
        after that step record: a step record then gives the receipt of each field, one for each, saying that no child was
        started, and none is left due (A109, A113)." Its test line: "A start the system refuses with the file still there,
        for a command with a secret field, in five passes after the look (...): the fake records no start, the journal holds
        the receipt-due record and then each field's receipt saying in fixed words that no child was started, and no status
        form says that a secret may have been received and lost (the owner's ruling, A113)." The create's send given a
        secret field (`rowlib.secret_send_providers`)."""
        for cause in self.CAUSES:
            with self.subTest(cause=cause):
                m, run, went, _put_right = self.refused(self.label("sec12", cause), cause, providers=rowlib.secret_send_providers())
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: " + self.REFUSED, went.lines)
                self.no_start(m, went)
                self.assertEqual([(r["kind"], r.get("step")) for r in self.of_c1(m, run)],
                                 [("start", None), ("step", "receipt-due"), ("step", "receipt"), ("step", "send-refused")],
                                 "not the receipt-due record and then each field's receipt")
                due = [r for r in self.of_c1(m, run) if r.get("step") == "receipt-due"][0]
                self.assertEqual([f["field"] for f in due["fields"]], ["token"])
                receipts = [r for r in self.of_c1(m, run) if r.get("step") == "receipt"]
                self.assertEqual([(r["execution"], r["field"], r["outcome"]) for r in receipts], [(1, "token", "no child started")],
                                 "the receipt does not say in fixed words that no child was started")
                self.assertNotIn("reference", receipts[0])
                for path in went.doc["forms"]:
                    self.assertNotIn(self.LOST, open(path).read(), "a status form says that a secret may have been lost")
                status = m.summon("status")
                self.assertEqual(status.ending, "stopped", status.text)
                self.assertNotIn(self.LOST, open(status.doc["forms"][0]).read(), "a later status form says so")
                self.assertNotIn(self.LOST, went.text + status.text)


# G23-24: the time limit of the reads below that a test makes run past their time (a fake that hangs). Long enough that a read
# that answers on a machine under load (the two runtimes' suites side by side) answers within it, and short against the
# hanging fake's ten minutes; it was one second, and a read made only to set up the case then ran out of time under load
UNDER_LOAD = 8


def failing_get_providers(base=None):
    """The fake providers with the fake host's `get` able to fail as RUN-7's test line has a read fail (test_run): its exit 5
    `other` (the read failed), 7 `auth` (the read made as the wrong account), and a time limit of `UNDER_LOAD` seconds (the
    read runs past its time); a partial answer is one the parser cannot read whole (`malformed`)."""
    providers = base or rowlib.providers()
    providers["fakehost"]["commands"]["get"]["exits"].update({"5": "other", "7": "auth"})
    providers["fakehost"]["commands"]["get"]["time_limit"] = UNDER_LOAD
    return providers


READS_THAT_DO_NOT_ANSWER = (("the read fails", {"do": "fail", "exit": 5}),
                            ("the read answers part", {"do": "raw", "text": '{"state": "act'}),
                            ("the read answers as the wrong account", {"do": "fail", "exit": 7}),
                            ("the read runs past its time limit", {"do": "hang"}))


def next_get(m):
    """The number the fake host's next `get` call will have (the fake counts each command's calls)."""
    return int((m.fake("fakehost", "counts.json") or {}).get("get", 0)) + 1


class AnOwnerStepsReadThatFails(OpCase):
    """OP-9 (batch 50, A118): "Where an owner step's read, the read that builds the step or reads back its after-state, fails,
    is partial, is made as the wrong account or runs out of time (OP-5's last row), whether it is made when the step is first
    reached or when a waiting step is read again at the start of an invocation, the step is not shown, since it is shown only
    as a fresh read builds it, and the run ends `stopped`, its form naming the step and the read that failed, with no effect
    applied. These are two stops that rest on GOV-1: no rule says how a step stands on a read that did not answer. At the
    start of an invocation it is that failed read, and not RUN-10's own ending, that ends the invocation, a summons with no
    word among them (RUN-12)." Its test line: "A read of an owner step that does not answer: a fake that fails the read when
    the step is first reached, and in further passes answers part, answers as the wrong account and runs past its time
    limit, ends the run `stopped` with no effect call, the step in no form and the form naming the step and the read that
    failed; a waiting step in read-back mode whose read fails at the start of a resume on his current word, and in a second
    pass of a summons with no word, ends that invocation `stopped` with no effect call, the step's earlier text in no form
    (GOV-1)."

    The owner step O1 in read-back mode, its read the fake host's `get`; beside it a change H1 that needs nothing of it, the
    effect a run not stopped would make: in the same phase, after it, where the step is first reached; in a later phase
    where the step waits. The fake host's thing stands `active`, so that O1's read, where it answers, shows the step not
    done."""

    STEP = "connect the fake host by hand"

    def machine_for(self, label, phases):
        m = harness.Machine(self.tmp, label, label)
        h1 = rowlib.refusing("H1", phase=phases[-1])
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="read back"), h1], phases=phases),
                       providers=failing_get_providers())
        m.set_fake("fakehost", things={"demo": {"id": "x1", "kind": "db", "state": "active", "name": "demo"}})
        return m

    def assert_stopped_unshown(self, m, run, ended, earlier_records):
        self.assertEqual(ended.ending, "stopped", ended.text)
        self.assertNotIn(texts.DEFECT, ended.text, "an exception was reported")
        self.assertIn("operation: O1", ended.lines, "the output does not name the step")
        self.assertTrue(ended.doc.get("forms"), "no form was rendered: %s" % ended.text)
        for path in ended.doc["forms"]:
            form = open(path).read()
            self.assertNotIn(self.STEP, form, "the step is shown in the form")
            self.assertIn("operation O1", form, "the form does not name the step")
            self.assertIn("the step's read", form, "the form does not name the read that failed")
        self.assertNotIn(self.STEP, ended.text, "the step is shown in the output")
        self.assertEqual(self.changing(m), [], "an effect call was made")
        self.assertEqual([r for r in m.journal(run) if r.get("op") == "H1"], [], "the change beside it was started")
        self.assertEqual([r for r in m.journal(run) if r.get("op") == "O1" and r["kind"] not in earlier_records], [],
                         "a record of the step was written")

    def test_OP9_A118_a_read_that_fails_answers_part_answers_as_the_wrong_account_or_runs_past_its_time_when_the_step_is_first_reached_ends_stopped_the_step_in_no_form(self):
        for number, (label, plan) in enumerate(READS_THAT_DO_NOT_ANSWER):
            with self.subTest(read=label):
                m = self.machine_for("first-%d" % number, ("one",))
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                run = looked.doc["run"]
                m.plan_fake("fakehost", dict(plan, command="get", nth=next_get(m)))
                went = m.go(looked)
                self.assert_stopped_unshown(m, run, went, ())
                self.assertIn("stopped: unreadable", went.lines, "not stopped on the read that failed")
                self.assertEqual([r for r in m.journal(run) if r.get("op") == "O1"], [], "a `waiting` record or a status was written")

    def test_OP9_A118_a_waiting_steps_read_that_fails_at_a_resume_on_his_word_and_at_a_summons_with_no_word_ends_stopped_its_earlier_text_in_no_form(self):
        for summons in ("a resume on his current word", "a summons with no word"):
            with self.subTest(summons=summons):
                m = self.machine_for("again-%s" % summons[2:8], ("one", "two"))
                looked, went = m.started()
                self.assertEqual(went.ending, "waiting", went.text)
                self.assertIn(self.STEP, open(went.doc["forms"][0]).read(), "the fixture's premise: the step is shown while it waits")
                run = looked.doc["run"]
                position = m.summon("status").doc["position"]
                m.plan_fake("fakehost", {"command": "get", "nth": next_get(m), "do": "fail", "exit": 5})
                if summons == "a summons with no word":
                    ended = m.summon("status")
                else:
                    ended = m.summon("resume", "demo", "--position", position, "--word", "go on")
                self.assert_stopped_unshown(m, run, ended, ("waiting",))
                self.assertIn("stopped: unreadable", ended.lines, "not stopped on the read that failed")
                self.assertNotIn("re-plan is needed", ended.text, "a re-plan was asked for")
                last = [r for r in m.journal(run) if r["kind"] == "invocation-end"][-1]
                self.assertEqual(last.get("ending"), "stopped", "the invocation did not end `stopped`")


def identity_failing_providers(base=None):
    """The fake providers of `failing_get_providers`, with the fake host's identity read (`whoami`) able to fail as RUN-7's
    test line has a read fail: its exit 5 `other` (the read failed), and a time limit of `UNDER_LOAD` seconds (the read runs
    past its time); a partial answer is one the parser cannot read whole (`malformed`)."""
    providers = failing_get_providers(base)
    # exit 7 `auth`: the provider refuses the read's credentials (OP-9, batch 52, A122: "one whose credentials the provider
    # refuses shows no account at all, and is one that fails")
    providers["fakehost"]["commands"]["whoami"]["exits"].update({"5": "other", "7": "auth"})
    providers["fakehost"]["commands"]["whoami"]["time_limit"] = UNDER_LOAD
    return providers


IDENTITY_READS_THAT_DO_NOT_ANSWER = (("the identity read fails", {"do": "fail", "exit": 5}),
                                     ("the identity read answers part", {"do": "raw", "text": '{"account": "fix'}),
                                     ("the identity read runs past its time limit", {"do": "hang"}))
IDENTITY_CREDENTIALS_REFUSED = ("the provider refuses the identity read's credentials", {"do": "fail", "exit": 7})


def next_call(m, command):
    """The number the fake host's next call of `command` will have (the fake counts each command's calls)."""
    return int((m.fake("fakehost", "counts.json") or {}).get(command, 0)) + 1


class AWaitingStepWithNoFreshRead(OpCase):
    """OP-9 (batch 51, A120): "Since a step is shown only as a fresh read builds it, a waiting step whose read this invocation
    did not make, or made and got no answer from, is in no form this invocation renders, neither from the manifest's text nor
    from an earlier form's: where the runner refuses that read, and the invocation ends `stopped` on the refusal (SEC-3's
    refusals row); where an earlier step's stop ends the invocation before this step is read, and it ends `stopped` on that
    stop; and at a close, which makes no read (SEC-12's table), and ends `closed` (RUN-13). Where the identity read of the
    step's provider, made before the step's read, fails, is partial or runs out of time, so that the step's read is not
    made, the step is in no form and the run ends `stopped`, its form naming the identity read that failed, with no effect
    applied ... An identity read that shows another account is RUN-10 (b)'s. The line such a step has in a form is FORM-2's
    to place." Its test line: "A waiting step with no fresh read: its read refused by the runner at the start of a resume on
    his current word; a later waiting step not reached, an earlier step's read failing first; and a close: in each, neither
    the manifest's text of the step nor an earlier form's is in any form the invocation renders, and it ends `stopped`,
    `stopped` and `closed` in turn. Its provider's identity read failing, and in further passes answering part and running
    past its time limit, at the start of a resume on his current word and of a summons with no word: the step's read is not
    made, the step is in no form, and the invocation ends `stopped` with no effect call, the form naming the identity read
    (GOV-1)." (The runner's refusal is `test_sec3_runner.TheRefusalOutsideAProbe`.)

    FORM-2 (batch 51, A120): "A waiting step that OP-9 does not let a form show has no exact step to give, so its line is not
    this table's `waiting` line, which names the exact step: it is a line the table lacks, for the lane's list of form
    changes to give (A9; OP-9)." Its test line: "A waiting step that OP-9 does not let a form show, its read having got no
    answer: the status form renders where the lane's list of form changes gives its line, with neither the manifest's text of
    the step nor an earlier form's in it, and fails its build where the lane's list gives none."

    The owner step O1 in read-back mode, its read the fake host's `get`, its provider's identity read the fake host's
    `whoami`; beside it, in a later phase, a change H1 that needs nothing of it, the effect a run not stopped would make. The
    fake host's thing stands `active`, so that a read that answers shows the step not done. The lane's line for such a step
    is `rowlib.FORM_CHANGES["waiting, not shown"]`."""

    STEP = "connect the fake host by hand"
    LATER = "pause the second fake thing by hand"
    KEY = "waiting, not shown"

    def machine_for(self, label, rows=None, providers=None, form_changes=None):
        m = harness.Machine(self.tmp, label, label)
        rows = rows or [rowlib.owner_step("O1", mode="read back")]
        more = {} if form_changes is None else {"form_changes": form_changes}
        rowlib.install(m, rowlib.lane("sunrise", list(rows) + [rowlib.refusing("H1", phase="two")], phases=("one", "two"), **more),
                       providers=providers or identity_failing_providers())
        m.set_fake("fakehost", things={"demo": {"id": "x1", "kind": "db", "state": "active", "name": "demo"}})
        return m

    def waiting(self, m, *steps):
        """A look and its go, the run left `waiting` with each step shown (the fixture's premise); and the position of a
        status form, rendered with each step's read made and answered."""
        looked, went = m.started()
        self.assertEqual(went.ending, "waiting", went.text)
        form = open(went.doc["forms"][0]).read()
        for step in steps:
            self.assertIn(step, form, "the fixture's premise: the step is shown while it waits")
        status = m.summon("status")
        self.assertEqual(status.ending, "waiting", status.text)
        return looked.doc["run"], status.doc["position"]

    def lane_line(self, op, mode="read back"):
        return "[%s] %s" % (op, rowlib.FORM_CHANGES[self.KEY].format(what="the fake row " + op, mode=mode, how="by its own read"))

    def assert_in_no_form(self, ended, *steps):
        self.assertNotIn(texts.DEFECT, ended.text, "an exception was reported")
        self.assertTrue(ended.doc.get("forms"), "no form was rendered: %s" % ended.text)
        for path in ended.doc["forms"]:
            form = open(path).read()
            for step in steps:
                self.assertNotIn(step, form, "the step is in a form this invocation renders")
        for step in steps:
            self.assertNotIn(step, ended.text, "the step is in the output")

    def summon(self, m, summons, position):
        if summons == "a summons with no word":
            return m.summon("status")
        return m.summon("resume", "demo", "--position", position, "--word", "go on")

    def test_OP9_A120_a_later_waiting_step_not_reached_an_earlier_steps_read_failing_first_is_in_no_form_and_the_invocation_ends_stopped(self):
        rows = [rowlib.owner_step("O1", mode="read back"), rowlib.owner_step("O2", mode="read back", safe_content={"step": self.LATER},
                                                                            output="connected-2")]
        for summons in ("a resume on his current word", "a summons with no word"):
            with self.subTest(summons=summons):
                m = self.machine_for("later-%s" % summons[2:8], rows)
                run, position = self.waiting(m, self.STEP, self.LATER)
                gets = len(m.calls("fakehost", "get"))
                m.plan_fake("fakehost", {"command": "get", "nth": next_get(m), "do": "fail", "exit": 5})
                ended = self.summon(m, summons, position)
                self.assertEqual(ended.ending, "stopped", ended.text)
                self.assertIn("stopped: unreadable", ended.lines, "not stopped on the earlier step's read")
                self.assertIn("operation: O1", ended.lines)
                self.assertEqual(len(m.calls("fakehost", "get")), gets + 1, "the later step's read was made")
                self.assert_in_no_form(ended, self.STEP, self.LATER)
                form = open(ended.doc["forms"][0]).read()
                self.assertIn(self.lane_line("O2"), form, "the later step has not the lane's line")
                self.assertEqual(self.changing(m), [], "an effect call was made")
                self.assertEqual([r for r in m.journal(run) if r.get("op") == "H1"], [], "the change beside it was started")
                last = [r for r in m.journal(run) if r["kind"] == "invocation-end"][-1]
                self.assertEqual(last.get("ending"), "stopped", "the invocation did not end `stopped`")

    def test_OP9_A120_at_a_close_which_makes_no_read_a_waiting_step_is_in_no_form_and_the_run_ends_closed(self):
        for label, more, ending in (("a close", ("--word", "close"), "closed"),
                                    ("a close summons that does not carry his word", (), "waiting")):
            with self.subTest(summons=label):
                m = self.machine_for("close-%d" % len(more))
                run, _position = self.waiting(m, self.STEP)
                calls = len(m.calls("fakehost"))
                ended = m.summon("close", "demo", *more)
                self.assertEqual(ended.ending, ending, ended.text)
                self.assertEqual(len(m.calls("fakehost")), calls, "a close made a read")
                self.assert_in_no_form(ended, self.STEP)
                self.assertIn(self.lane_line("O1"), open(ended.doc["forms"][0]).read(), "the step has not the lane's line")

    def test_OP9_A120_its_providers_identity_read_failing_answering_part_or_running_past_its_time_ends_stopped_the_step_in_no_form(self):
        for summons in ("a resume on his current word", "a summons with no word"):
            for number, (label, plan) in enumerate(IDENTITY_READS_THAT_DO_NOT_ANSWER):
                with self.subTest(summons=summons, read=label):
                    m = self.machine_for("id-%s-%d" % (summons[2:8], number))
                    run, position = self.waiting(m, self.STEP)
                    gets = len(m.calls("fakehost", "get"))
                    before = m.statuses(run)
                    m.plan_fake("fakehost", dict(plan, command="whoami", nth=next_call(m, "whoami")))
                    ended = self.summon(m, summons, position)
                    self.assertEqual(ended.ending, "stopped", ended.text)
                    self.assertIn("stopped: unreadable", ended.lines, "not stopped on the identity read")
                    self.assertIn("operation: O1", ended.lines)
                    self.assertNotIn("re-plan is needed", ended.text, "a re-plan was asked for")
                    self.assertEqual(len(m.calls("fakehost", "get")), gets, "the step's read was made")
                    self.assert_in_no_form(ended, self.STEP)
                    form = open(ended.doc["forms"][0]).read()
                    self.assertIn("the identity read of fakehost", form, "the form does not name the identity read")
                    self.assertIn(self.lane_line("O1"), form, "the step has not the lane's line")
                    self.assertEqual(self.changing(m), [], "an effect call was made")
                    self.assertEqual(m.statuses(run), before, "a status was recorded")
                    last = [r for r in m.journal(run) if r["kind"] == "invocation-end"][-1]
                    self.assertEqual(last.get("ending"), "stopped", "the invocation did not end `stopped`")

    def test_OP9_A120_RUN10_an_identity_read_that_shows_another_account_stays_RUN10_bs_and_the_step_unread_is_in_no_form(self):
        """"An identity read that shows another account is RUN-10 (b)'s": on his current word it says a re-plan is needed and
        ends with no effect, as the run stood (RUN-10, RUN-12), as built; with no word it ends as the run stood, as built. In
        both the step's read is not made, so by OP-9's first sentence the step is in no form."""
        for summons in ("a resume on his current word", "a summons with no word"):
            with self.subTest(summons=summons):
                m = self.machine_for("acct-%s" % summons[2:8])
                run, position = self.waiting(m, self.STEP)
                gets = len(m.calls("fakehost", "get"))
                m.set_fake("fakehost", account="another-account")
                ended = self.summon(m, summons, position)
                self.assertEqual(ended.ending, "waiting", ended.text)
                if summons == "a resume on his current word":
                    self.assertIn("re-plan is needed", ended.text, "RUN-10 (b): no re-plan asked for")
                self.assertEqual(len(m.calls("fakehost", "get")), gets, "the step's read was made")
                self.assert_in_no_form(ended, self.STEP)
                self.assertIn(self.lane_line("O1"), open(ended.doc["forms"][0]).read(), "the step has not the lane's line")
                self.assertEqual(self.changing(m), [], "an effect call was made")

    def test_FORM2_A120_the_line_of_a_step_OP9_does_not_let_a_form_show_is_the_lanes_and_without_it_the_form_fails_its_build(self):
        """The step's read fails at a summons with no word (A118's case). With the lane's line, the status form renders it, and
        neither the step's text nor FORM-2's `waiting` line of that step is in it. With a lane whose list gives no such line,
        the form fails its build: no status form is written, and the output names the status that has no line."""
        for given in (True, False):
            with self.subTest(lane_gives_the_line=given):
                changes = dict(rowlib.FORM_CHANGES)
                if not given:
                    changes.pop(self.KEY)
                m = self.machine_for("form2-%s" % given, form_changes=changes)
                run, _position = self.waiting(m, self.STEP)
                m.plan_fake("fakehost", {"command": "get", "nth": next_get(m), "do": "fail", "exit": 5})
                ended = m.summon("status")
                self.assertEqual(ended.ending, "stopped", ended.text)
                self.assertNotIn(self.STEP, ended.text, "the step is in the output")
                if given:
                    form = open(ended.doc["forms"][0]).read()
                    self.assertIn(self.lane_line("O1"), form, "the step has not the lane's line")
                    self.assertNotIn("[O1] waiting on you: ", form, "FORM-2's `waiting` line is given to the step")
                    self.assertNotIn(self.STEP, form, "the step is in the form")
                else:
                    self.assertFalse(ended.doc.get("forms"), "a form was rendered with no line for the step")
                    self.assertIn(texts.NO_FORM_LINE + self.KEY, ended.lines, "the output does not name the status with no line")

    # ---- part G12 (batch 52, A122) -------------------------------------------------------------------------------------
    def assert_identity_stop(self, m, run, ended, gets, before):
        """The identity stop of OP-9: `stopped` with no effect call, the step's read not made, the step in no form, and the
        form naming the identity read."""
        self.assertEqual(ended.ending, "stopped", ended.text)
        self.assertIn("stopped: unreadable", ended.lines, "not stopped on the identity read")
        self.assertIn("operation: O1", ended.lines)
        self.assertNotIn("re-plan is needed", ended.text, "a re-plan was asked for")
        self.assertNotIn(texts.CONTEXT_CHANGED_BEFORE_GO, ended.text, "a changed context was said")
        self.assertEqual(len(m.calls("fakehost", "get")), gets, "the step's read was made")
        self.assert_in_no_form(ended, self.STEP)
        form = open(ended.doc["forms"][0]).read()
        self.assertIn("the identity read of fakehost", form, "the form does not name the identity read")
        self.assertIn(self.lane_line("O1"), form, "the step has not the lane's line")
        self.assertEqual(self.changing(m), [], "an effect call was made")
        self.assertEqual(m.statuses(run), before, "a status was recorded")
        last = [r for r in m.journal(run) if r["kind"] == "invocation-end"][-1]
        self.assertEqual(last.get("ending"), "stopped", "the invocation did not end `stopped`")

    def test_OP9_A122_an_identity_read_whose_credentials_the_provider_refuses_at_a_resume_on_his_word_and_at_a_summons_with_no_word_ends_stopped_the_step_in_no_form(self):
        """OP-9 (batch 52, A122): "An identity read that shows another account is RUN-10 (b)'s; one whose credentials the
        provider refuses shows no account at all, and is one that fails (OP-5's last row)." Its test line: "So too where the
        fixture provider answers the identity read by refusing its credentials, at the start of a resume on his current word
        and of a summons with no word." The fake host's `whoami` exits 7, `auth`."""
        label, plan = IDENTITY_CREDENTIALS_REFUSED
        for summons in ("a resume on his current word", "a summons with no word"):
            with self.subTest(summons=summons, read=label):
                m = self.machine_for("auth-%s" % summons[2:8])
                run, position = self.waiting(m, self.STEP)
                gets, before = len(m.calls("fakehost", "get")), m.statuses(run)
                m.plan_fake("fakehost", dict(plan, command="whoami", nth=next_call(m, "whoami")))
                ended = self.summon(m, summons, position)
                self.assert_identity_stop(m, run, ended, gets, before)

    def replanned(self, m):
        """A run left `waiting` on O1, then a re-plan whose manifest awaits his go: (run, the re-plan's result)."""
        run, _position = self.waiting(m, self.STEP)
        replanned = m.summon("replan", "demo", "--inputs", m.inputs(name="again.json"))
        self.assertTrue(replanned.doc and replanned.doc.get("manifest_sha256"), replanned.text)
        return run, replanned

    def test_OP9_A122_at_the_start_of_the_invocation_that_records_his_go_on_a_replans_manifest_the_identity_read_failing_ends_stopped_the_step_in_no_form(self):
        """OP-9's test line (batch 52, A122): "At the start of the invocation that records his go on a re-plan's manifest, the
        identity read failing ends it `stopped` with no effect call and the step in no form." Two passes: the read fails
        (exit 5, `other`), and the provider refuses its credentials (exit 7, `auth`, "one that fails"). No go is recorded on
        the re-plan's manifest."""
        for number, (label, plan) in enumerate((IDENTITY_READS_THAT_DO_NOT_ANSWER[0], IDENTITY_CREDENTIALS_REFUSED)):
            with self.subTest(read=label):
                m = self.machine_for("replan-go-%d" % number)
                run, replanned = self.replanned(m)
                gets, before = len(m.calls("fakehost", "get")), m.statuses(run)
                m.plan_fake("fakehost", dict(plan, command="whoami", nth=next_call(m, "whoami")))
                gone = m.run("go", "--kind", "sunrise", "--name", "demo", "--run", run,
                             "--manifest-sha256", replanned.doc["manifest_sha256"])
                self.assert_identity_stop(m, run, gone, gets, before)
                self.assertEqual([r for r in m.journal(run) if r["kind"] == "go"], [], "his go was recorded")

    # ---- part G13 (batches 57 to 59; the owner's ruling A130; A131, A132) ----------------------------------------------
    def every_fakes_calls(self, m):
        """{fake: the number of calls it has recorded}, for every fake of the fixture machine: the fakes' own records."""
        root = os.path.join(m.home, ".fakes")
        return dict((tool, len(m.calls(tool))) for tool in (sorted(os.listdir(root)) if os.path.isdir(root) else []))

    def assert_no_provider_call_and_no_runner_use(self, m, ended, before):
        """SEC-12's pass, as its close pass and RUN-1's close pass assert it (`test_run`, a close records no runner call), over
        the whole invocation, its start included: the record of acts runs from before the tool's first code (`harness.run`), so
        the withheld read, the gate, the name check, the locks, `open_continued` and the first records are in it. No fake
        records a call; no child is started or readied by the runner; no request of the frame's own is made."""
        self.assertEqual(self.every_fakes_calls(m), before, "a fake recorded a provider call")
        self.assertEqual([(e["stage"], e["op"], e["subject"]) for e in ended.events if e["op"] in ("child", "request")], [],
                         "the runner was used or a request of the frame's own was made")

    def stood(self, m, stood):
        """The fixture of A130 and A132: a run left `waiting` on O1 (read-back mode) or left `stopped` with O1 waiting on him
        beside the stop, then a re-plan whose manifest awaits his go, then the position of a status form rendered after it.
        Returns (run, position). For `stopped` the stop is another operation's: H2, a change in O1's phase, whose effect call
        fails at the go, after O1's `waiting` record (ORD-5's order); the run's last invocation ended `stopped` on H2."""
        if stood == "waiting":
            run, _replanned = self.replanned(m)
        else:
            m.plan_fake("fakehost", {"command": "set", "do": "fail", "exit": 1})
            looked, went = m.started()
            run = looked.doc["run"]
            self.assertEqual(went.ending, "stopped", went.text)
            self.assertIn("operation: H2", went.lines, "the fixture's premise: the stop is H2's")
            self.assertEqual([r["op"] for r in m.journal(run) if r["kind"] == "waiting"], ["O1"],
                             "the fixture's premise: O1 waits on him beside the stop")
            replanned = m.summon("replan", "demo", "--inputs", m.inputs(name="again.json"))
            self.assertTrue(replanned.doc and replanned.doc.get("manifest_sha256"), replanned.text)
        status = m.summon("status")
        self.assertEqual(status.ending, stood, status.text)
        self.assertEqual(len([n for n in os.listdir(m.facts.run_dir(run)) if n.startswith("manifest-") and n.endswith(".json")]), 2,
                         "the fixture's premise: a re-plan's manifest beside the one in force")
        self.assertEqual([r for r in m.journal(run) if r["kind"] == "go"], [], "the fixture's premise: no go on the re-plan's manifest")
        return run, status.doc["position"]

    def machine_stood(self, label, stood):
        rows = [rowlib.owner_step("O1", mode="read back")]
        if stood == "stopped":
            rows.append(rowlib.refusing("H2", phase="one", output="state-H2"))
        return self.machine_for(label, rows)

    def test_OP9_A130_a_resume_on_his_word_while_a_replans_manifest_awaits_its_go_makes_no_identity_read_and_no_read_of_the_step_ends_waiting_and_the_form_says_a_new_plan_awaits_its_go(self):
        """OP-9 (batch 58, A131; the owner's ruling, A130): "Every waiting step in read-back mode is read again at the start of
        each invocation but a close and a resume on his current word while a re-plan's manifest awaits its go (the owner's
        ruling, A130)", and among the steps in no form, "at a resume on his current word while a re-plan's manifest awaits its
        go, which makes no identity read and no read of a waiting step and ends as the run stood". Its test line: "A resume on
        his current word while a re-plan's manifest awaits its go, a step left `waiting` in read-back mode: no fake records an
        identity read or a read of that step, no effect call is made, the run ends `waiting` as it stood, the step is in no
        form, and the form says that a new plan awaits his go (the owner's ruling, A130)." Part G12's test of this resume
        (`test_OP9_A122_a_resume_on_his_word_while_a_replans_manifest_awaits_its_go_makes_no_read_...`), brought to that pass."""
        m = self.machine_stood("a130-op9", "waiting")
        run, position = self.stood(m, "waiting")
        whoamis, gets = len(m.calls("fakehost", "whoami")), len(m.calls("fakehost", "get"))
        ended = m.summon("resume", "demo", "--position", position, "--word", "go on")
        self.assertEqual(len(m.calls("fakehost", "whoami")), whoamis, "a fake recorded an identity read")
        self.assertEqual(len(m.calls("fakehost", "get")), gets, "a fake recorded a read of the step")
        self.assertEqual(self.changing(m), [], "an effect call was made")
        self.assertEqual(ended.ending, "waiting", ended.text)
        self.assert_in_no_form(ended, self.STEP)
        form = open(ended.doc["forms"][0]).read()
        self.assertIn(self.lane_line("O1"), form, "the step has not the lane's line")
        self.assertIn(texts.NEW_PLAN_AWAITS, form, "the form does not say that a new plan awaits his go")

    def test_RUN12_A130_A131_a_resume_on_his_word_while_a_replans_manifest_awaits_its_go_ends_as_the_run_stood_waiting_or_stopped_its_status_form_saying_a_new_plan_awaits_its_go(self):
        """RUN-12 (batches 58 and 59; A130, A131, A132): "So does a resume on his current word while a re-plan's manifest awaits
        its go, which applies nothing and ends as the run stood, `waiting` or `stopped`, its status form saying that a new plan
        awaits his go (the owner's ruling, A130; that a run that stood `stopped` ends `stopped` is the frame's reading of it,
        his to change by a word, A131)." Its test line: "a resume on his current word on a run left `waiting` while a re-plan's
        manifest awaits its go ends `waiting`, with no effect call and its status form saying that a new plan awaits his go
        (the owner's ruling, A130); and one on a run left `stopped`, a step waiting on him beside the stop and a re-plan's
        manifest awaiting its go, records no provider call by any fake and no runner use, makes no effect call and ends
        `stopped`, as it stood, the step in no form and its status form saying that a new plan awaits his go (the frame's
        reading of the owner's ruling, A130, his to change by a word, A131)." Two passes, one for each."""
        for stood in ("waiting", "stopped"):
            with self.subTest(the_run_stood=stood):
                m = self.machine_stood("a130-run12-%s" % stood, stood)
                run, position = self.stood(m, stood)
                before, effects = self.every_fakes_calls(m), self.changing(m)    # the stopped fixture's own failed `set` among them
                ended = m.summon("resume", "demo", "--position", position, "--word", "go on")
                self.assertEqual(ended.ending, stood, ended.text)
                self.assertEqual(self.changing(m), effects, "an effect call was made")
                self.assertNotIn(texts.DEFECT, ended.text, "an exception was reported")
                self.assertTrue(ended.doc.get("forms"), "no status form was rendered: %s" % ended.text)
                form = open(ended.doc["forms"][0]).read()
                self.assertIn("the run now: %s" % stood, form, "the status form does not say how the run stands")
                self.assertIn(texts.NEW_PLAN_AWAITS, form, "the status form does not say that a new plan awaits his go")
                if stood == "stopped":
                    self.assert_no_provider_call_and_no_runner_use(m, ended, before)
                    self.assert_in_no_form(ended, self.STEP)

    def test_SEC12_A130_a_resume_on_his_word_while_a_replans_manifest_awaits_its_go_records_no_provider_call_and_no_runner_use(self):
        """SEC-12's table, the row of a resume on his current word: "while a re-plan's manifest awaits its go, none of these: no
        identity read and no read of a waiting step (the owner's ruling, A130), and no other read RUN-10 (b) compares, since (b)
        bears on applying an effect and this resume applies none (RUN-10)". Its test line: "and a resume on his current word
        while a re-plan's manifest awaits its go records no provider call and no runner use (the owner's ruling, A130)". Over
        the whole invocation, its start included, as the close pass asserts it; on a run left `waiting` and on one left
        `stopped` with a step waiting beside the stop."""
        for stood in ("waiting", "stopped"):
            with self.subTest(the_run_stood=stood):
                m = self.machine_stood("a130-sec12-%s" % stood, stood)
                run, position = self.stood(m, stood)
                before = self.every_fakes_calls(m)
                ended = m.summon("resume", "demo", "--position", position, "--word", "go on")
                self.assertEqual(ended.ending, stood, ended.text)
                self.assert_no_provider_call_and_no_runner_use(m, ended, before)


class AStepOnHisWordAndAnOwnerAnswer(OpCase):
    """OP-9 (batch 52, A122): "A step on his word, which has no read, and an owner answer are built from the safe content their
    row gives (ROW-1) and are shown from it each time, a close's form among them: the fresh read this rule asks for is the
    read of a step that has one." Its test line: "A waiting step on his word and a waiting owner answer: a resume, a summons
    with no word and a close each render it from its row's safe content, and no fake records a read of it."

    ROW-1's entry "the safe content its step or its question is built from" is the row's `safe_content` (R for an owner step
    and an owner answer); the manifest carries it frozen (`plan.build`, `values.freeze_all`). The owner step O1 on his word,
    its step `STEP`; the owner answer A1, its question `QUESTION`; beside them, in a later phase, a change H1 that needs
    nothing of them, the effect a run not stopped would make, its commands the fake host's."""

    STEP = "sign the fake paper by hand"
    QUESTION = "use the merged file?"

    def machine_for(self, label):
        m = harness.Machine(self.tmp, label, label)
        rows = [rowlib.owner_step("O1", mode="on his word", safe_content={"step": self.STEP}),
                rowlib.owner_answer("A1"),                     # its row's question is `QUESTION` (rowlib)
                rowlib.refusing("H1", phase="two")]
        rowlib.install(m, rowlib.lane("sunrise", rows, phases=("one", "two")))
        m.set_fake("fakehost", things={"demo": {"id": "x1", "kind": "db", "state": "active", "name": "demo"}})
        return m

    def reads_of_them(self, m, calls_before):
        """What the fakes recorded since `calls_before`, but the provider's identity read (`whoami`): a read of either would be
        a call of the fake host's (their rows declare no command), and none is allowed."""
        return [c["argv"][0] for c in m.calls("fakehost")[calls_before:] if c["argv"][0] != "whoami"]

    def test_OP9_A122_a_waiting_step_on_his_word_and_a_waiting_owner_answer_are_rendered_from_their_rows_safe_content_at_a_resume_a_summons_with_no_word_and_a_close(self):
        for summons, ending in (("a resume on his current word", "waiting"), ("a summons with no word", "waiting"),
                                ("a close", "closed")):
            with self.subTest(summons=summons):
                m = self.machine_for("word-%s" % summons[2:8])
                looked, went = m.started()
                self.assertEqual(went.ending, "waiting", went.text)
                run = looked.doc["run"]
                position = m.summon("status").doc["position"]
                calls = len(m.calls("fakehost"))
                if summons == "a resume on his current word":
                    ended = m.summon("resume", "demo", "--position", position, "--word", "go on")
                elif summons == "a summons with no word":
                    ended = m.summon("status")
                else:
                    ended = m.summon("close", "demo", "--word", "close")
                self.assertEqual(ended.ending, ending, ended.text)
                self.assertNotIn(texts.DEFECT, ended.text, "an exception was reported")
                self.assertTrue(ended.doc.get("forms"), "no form was rendered: %s" % ended.text)
                form = open(ended.doc["forms"][0]).read()
                self.assertIn("[O1] waiting on you: %s; mode: on his word; the tool will know it is done by your word alone"
                              % self.STEP, form, "the step on his word is not rendered from its row's safe content")
                self.assertIn("[A1] waiting on you: %s; mode: answer; the tool will know it is done by your answer"
                              % self.QUESTION, form, "the owner answer is not rendered from its row's safe content")
                self.assertNotIn("waiting on you, not shown", form, "a step with no read is given the line of a step not shown")
                self.assertEqual(self.reads_of_them(m, calls), [], "a fake recorded a read of the step or the answer")
                self.assertEqual(self.changing(m), [], "an effect call was made")


class AnAfterCheckThatDoesNotAnswer(OpCase):
    """OP-6 (its rule text): "For every other kind, an effect call that fails, or an after-check that does not show the
    after-state, stops the run with no completion recorded, and the next probe reads the world again." Its test line (batch
    50, A118): "An after-check whose read fails, and in a second pass runs out of time, does not show the after-state: the run
    stops with the start record standing and no completion recorded, and the next resume's probe reads the world again." The
    change of `rowlib.install_change_checked_by_child` (a C5; its probe reads the fake host's own request, its effect call
    `fakehost set`, its after-check's read `fakehost get`), `get` failing as `failing_get_providers` lets it."""

    def test_OP6_A118_an_after_check_whose_read_fails_or_runs_out_of_time_stops_with_the_start_record_standing_and_the_next_probe_reads_again(self):
        for number, (label, plan) in enumerate((READS_THAT_DO_NOT_ANSWER[0], READS_THAT_DO_NOT_ANSWER[3])):
            with self.subTest(read=label):
                m = rowlib.install_change_checked_by_child(harness.Machine(self.tmp, "ac-%d" % number, "ac-%d" % number),
                                                           providers=failing_get_providers(rowlib.refused_send_providers()))
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                run = looked.doc["run"]
                m.plan_fake("fakehost", dict(plan, command="get", nth=next_get(m)))
                went = m.go(looked)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
                self.assertIn("stopped: the after-check does not show the after-state", went.lines, went.text)
                self.assertIn("operation: H1", went.lines)
                h1 = [r for r in m.journal(run) if r.get("op") == "H1"]
                self.assertEqual(len([r for r in h1 if r["kind"] == "start"]), 1, "the start record does not stand")
                self.assertEqual([r for r in h1 if r["kind"] in ("completion", "status")], [], "a completion or a status was recorded")
                self.assertEqual([c["argv"][0] for c in m.calls("fakehost")], ["set", "get"], "not the effect call and the after-check's read")
                reads_before = len(m.transport.records)
                resumed = m.resume()
                self.assertEqual(resumed.ending, "complete", resumed.text)
                self.assertGreater(len(m.transport.records), reads_before, "the next probe did not read the world again")
                h1 = [r for r in m.journal(run) if r.get("op") == "H1"]
                self.assertEqual(len([r for r in h1 if r["kind"] == "start"]), 1, "a new start record: the probe did not answer `landed`")
                self.assertEqual([r.get("status") for r in h1 if r["kind"] == "status"], ["not proven"])
                self.assertEqual(len(m.calls("fakehost", "set")), 1, "the effect call was made again")


class ChecksAndOwners(OpCase):
    def test_OP8_a_failing_check_stops_and_is_attempted_again_and_D16_an_unreadable_subject_stops(self):
        m = self.clean()
        looked = m.look()
        went = m.go(looked, kill=planted(at("post", "journal", "completion", "C1"), lambda: os.remove(os.path.join(m.dev, "demo", "README.md"))))
        run = looked.doc["run"]
        self.assertIn("stopped: a check failed", went.lines)
        self.assertEqual([r["answer"] for r in m.journal(run) if r["kind"] == "attempt" and r["op"] == "K2"], ["failed"])
        with open(os.path.join(m.dev, "demo", "README.md"), "w") as fh:
            fh.write("# demo\n")
        self.assertEqual(m.resume().ending, "complete")
        self.assertEqual([r["answer"] for r in m.journal(run) if r["kind"] == "attempt" and r["op"] == "K2"], ["failed", "passed"])
        u = harness.Machine(self.tmp, "unread", "unread")
        probe = rowlib.check("K5")
        probe["thing"]["passes"] = [{"read": "command", "command": "look", "result": "success"}]
        probe["commands"] = [rowlib.use("look", "fakehost.get", name=rowlib.NAME)]
        rowlib.install(u, rowlib.lane("sunrise", [probe]))
        u.plan_fake("fakehost", {"command": "get", "do": "raw", "text": "{"})
        looked, went = u.started()
        self.assertIn("stopped: unreadable", went.lines)
        self.assertEqual([r for r in u.journal(looked.doc["run"]) if r["kind"] == "attempt"], [], "an unreadable subject was recorded as an attempt")

    def test_OP8_a_pass_of_an_earlier_invocation_is_attempted_again_before_the_effect_it_lets_run(self):
        m = self.clean()
        looked = m.look()
        m.go(looked, kill=at("post", "journal", "attempt", "K2"))
        run = looked.doc["run"]
        self.assertEqual(m.resume().ending, "complete")
        attempts = [r for r in m.journal(run) if r["kind"] == "attempt" and r["op"] == "K2"]
        self.assertEqual([a["attempt"] for a in attempts], [1, 2])
        self.assertNotEqual(attempts[0]["inv"], attempts[1]["inv"])
        start = [r for r in m.journal(run) if r["kind"] == "start" and r["op"] == "G1"][0]
        self.assertEqual(start["checked"], [{"check": "K2", "attempt": 2, "subject": attempts[1]["subject"]}])
        self.assertEqual(start["inv"], attempts[1]["inv"])

    def test_OP8_a_pass_on_one_state_does_not_let_the_push_run_once_an_approved_operation_has_changed_the_subject(self):
        project = {"output": "project folder.path"}
        readme = rowlib.path(project, "README.md")
        scan = rowlib.check("K2", place=readme, output="scanned",
                            thing={"tracked": ["exists", "sha256"], "passes": [{"read": "path", "path": readme, "is": "file"}]},
                            needs=[{"output": "project folder", "level": "state", "treatment": "then not applicable"}])
        edit = rowlib.swap_add("E1", line=rowlib.lit("an approved edit"), file=readme, output="edited",
                               needs=[{"output": "scanned", "level": "passed", "treatment": "then not applicable"}])
        edit["before_test"] = [c for c in edit["before_test"] if c["read"] != "name-free"]
        edit["construction"]["risks"] = ["RK2"]
        push = rowlib.cas("G1", needs=[{"output": "scanned", "level": "passed", "treatment": "then not applicable"},
                                        {"output": "edited", "level": "state", "treatment": "then not applicable"}])
        m = self.clean(rows=[rowlib.build("B1"), scan, edit, push])
        looked, went = m.started()
        run = looked.doc["run"]
        self.assertEqual(went.ending, "complete", went.text)
        attempts = [r for r in m.journal(run) if r["kind"] == "attempt"]
        self.assertEqual(len(attempts), 2, "the check was not attempted again on the new state")
        self.assertNotEqual(attempts[0]["subject"]["sha256"], attempts[1]["subject"]["sha256"])
        start = [r for r in m.journal(run) if r["kind"] == "start" and r["op"] == "G1"][0]
        self.assertEqual(start["checked"][0]["subject"], attempts[1]["subject"], "the push's start record does not name the state its attempt read")

    def test_OP9_read_back_completes_on_the_read_alone_and_never_on_his_word_alone(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="read back")]))
        m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}})
        looked, went = m.started()
        run = looked.doc["run"]
        self.assertEqual(went.ending, "waiting")
        said = m.resume("demo", None, "--done", "O1")
        self.assertEqual(said.ending, "waiting", "a read-back step completed on his word alone")
        self.assertIn("its read now shows: name demo, state active", open(said.doc["forms"][0]).read())
        things = m.fake("fakehost", "state.json")["things"]
        things["demo"]["state"] = "connected"
        m.set_fake("fakehost", things=things)
        silent = m.summon("status")
        self.assertEqual(silent.ending, "complete", silent.text)
        self.assertEqual(m.statuses(run), {"O1": "done by owner, read back"})
        self.assertIn("done by you, and a read checked it", open(silent.doc["forms"][0]).read())
        self.assertEqual([c for c in m.calls("fakehost") if c["changing"]], [], "a fake recorded a call that performs the owner's step")

    def test_OP9_on_his_word_an_answer_off_the_list_and_leave_it(self):
        m = self.m
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="on his word"), rowlib.owner_answer("A1")]))
        looked, went = m.started()
        run = looked.doc["run"]
        form = open(went.doc["forms"][0]).read()
        self.assertIn("waiting on you: use the merged file?; mode: answer", form)
        done = m.resume("demo", None, "--done", "O1")
        self.assertEqual(m.statuses(run)["O1"], "done by owner, on his word")
        self.assertIn("done by you, on your word; no read checked it", open(done.doc["forms"][0]).read())
        refused = m.resume("demo", None, "--answer", "A1=something else")
        self.assertEqual(refused.ending, "waiting")
        self.assertNotIn("A1", m.statuses(run))
        self.assertEqual([r for r in m.journal(run) if r["kind"] == "owner-answer" and r["op"] == "A1"], [])
        answered = m.resume("demo", None, "--answer", "A1=use it")
        self.assertEqual(answered.ending, "complete", answered.text)
        self.assertEqual(m.statuses(run)["A1"], "answered")
        left = harness.Machine(self.tmp, "left", "left")
        rowlib.install(left, rowlib.lane("sunrise", [rowlib.owner_answer("A1")]))
        looked, went = left.started()
        ended = left.resume("demo", None, "--leave", "A1")
        self.assertEqual(ended.ending, "ended with exceptions")
        self.assertEqual(left.statuses(looked.doc["run"]), {"A1": "left"})

    def test_OP9_an_owner_step_with_a_way_back_is_shown_only_after_its_reverses_inputs_are_saved_and_read_back(self):
        definition = "the whole definition of a fixture schedule " + harness.canary("schedule")
        m = self.m
        m.put("schedule.txt", definition)
        step = rowlib.owner_step("O1", mode="on his word")
        reverse = rowlib.owner_step("O1-reverse", mode="on his word")
        step["way_back"] = {"reverse": reverse}
        step["reverse_inputs"] = [{"read": "file", "path": rowlib.path({"location": "developer_root"}, "..", "schedule.txt"),
                                   "type": "definition", "label": "the schedule's definition"}]
        rowlib.install(m, rowlib.lane("sunrise", [step]))
        looked = m.look()
        self.assertNotIn("no reverse can be offered", open(looked.doc["forms"][0]).read())
        went = m.go(looked)
        run = looked.doc["run"]
        waiting = [r for r in m.journal(run) if r["kind"] == "waiting"][0]
        record = waiting["inputs"][0]["record"]
        events = went.events
        saved = next(e["i"] for e in events if e["op"] == "create" and e["stage"] == "post" and record in e["subject"])
        read_back = next(e["i"] for e in events if e["op"] == "read" and record in e["subject"] and e["i"] > saved)
        record_at = next(e["i"] for e in events if at("pre", "journal", "waiting", "O1")(e))
        form_at = next(e["i"] for e in events if e["op"] == "create" and "status-" in e["subject"])
        self.assertTrue(saved < read_back < record_at < form_at)
        os.remove(m.path("schedule.txt"))
        self.assertEqual(open(os.path.join(m.facts.run_dir(run), "protected", record)).read(), definition)
        self.assertNowhere(definition, went)
        form = open(went.doc["forms"][0]).read()
        self.assertNotIn(definition, form)
        self.assertIn("the schedule's definition: " + os.path.join(m.facts.run_dir(run), "protected", record), form)
        # where the look cannot read an input, the preview says no reverse can be offered
        blind = harness.Machine(self.tmp, "blind", "blind")
        rowlib.install(blind, rowlib.lane("sunrise", [step]))
        looked = blind.look()
        self.assertIn("no reverse can be offered for this step", open(looked.doc["forms"][0]).read())
        # where the look could read it and the save then fails, the run stops and the step is not shown
        gone = harness.Machine(self.tmp, "gone", "gone")
        gone.put("schedule.txt", definition)
        rowlib.install(gone, rowlib.lane("sunrise", [step]))
        looked = gone.look()
        os.remove(gone.path("schedule.txt"))
        stopped = gone.go(looked)
        self.assertEqual(stopped.ending, "stopped", stopped.text)
        self.assertEqual([r for r in gone.journal(looked.doc["run"]) if r["kind"] == "waiting"], [])
        self.assertNotIn("waiting on you", open(stopped.doc["forms"][0]).read())

    def test_OP10_adoption_only_on_the_owners_input_and_the_folder_must_be_as_the_manifest_recorded(self):
        rows = [rowlib.build("B1", condition={"on": "fact", "fact": "flags.promote", "equals": False, "reason": "a flag"}),
                rowlib.adopt("D1"),
                rowlib.check("K2", place=rowlib.path({"output": "project folder.path"}, "README.md"), output="scanned",
                             needs=[{"output": "project folder", "level": "state", "treatment": "then not applicable"}],
                             thing={"passes": [{"read": "path", "path": rowlib.path({"output": "project folder.path"}, "README.md"), "is": "file"}]})]
        rows[1]["condition"] = {"on": "fact", "fact": "flags.promote", "equals": True, "reason": "a flag"}
        found = self.clean(rows=rows)
        os.makedirs(os.path.join(found.dev, "demo"))
        stop = found.look(inputs=found.inputs(flags={"promote": False}))
        self.assertEqual(stop.ending, "refused")
        self.assertIn("the place is taken by a thing this run did not make: row B1", stop.lines)
        named = self.clean(harness.Machine(self.tmp, "named", "named"), rows)
        folder = named.put("dev/prototype/README.md", "# mine\n")
        folder = os.path.dirname(folder)
        looked = named.look(inputs=named.inputs(flags={"promote": True}, adopt={"project folder": folder}))
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = json.load(open(os.path.join(named.facts.run_dir(looked.doc["run"]), "manifest-1.json")))
        self.assertEqual([(o["id"], o["kind"]) for o in manifest["operations"]], [("D1", "adopt"), ("K2", "check")])
        went = named.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(named.statuses(looked.doc["run"]), {"D1": "adopted", "K2": "passed"})
        self.assertIn("taken as the project's on the owner's input", open(went.doc["forms"][0]).read())
        changed = self.clean(harness.Machine(self.tmp, "changed", "changed"), rows)
        folder = os.path.dirname(changed.put("dev/prototype/README.md", "# mine\n"))
        looked = changed.look(inputs=changed.inputs(flags={"promote": True}, adopt={"project folder": folder}))
        shutil.rmtree(folder)
        os.makedirs(folder)
        stopped = changed.go(looked)
        self.assertEqual(stopped.ending, "stopped")
        self.assertEqual(changed.statuses(looked.doc["run"]), {})

    def test_OP11_the_repository_changing_calls_equal_the_manifests_list_in_order_also_across_a_kill_and_a_resume(self):
        m = self.clean()
        looked = m.look()
        manifest = json.load(open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")))
        listed = [(o["id"], name) for o in manifest["operations"] if isinstance(o.get("repo_commands"), list) for name in o["repo_commands"]]
        self.assertEqual(listed, [("G1", "swap")])
        went = m.go(looked, kill=at("post", "journal", "start", "G1"))
        self.assertEqual(m.calls("fakegit", "cas"), [])
        self.assertEqual(m.resume().ending, "complete")
        self.assertEqual([c["argv"][0] for c in m.calls("fakegit") if c["changing"]], ["cas"])


if __name__ == "__main__":
    unittest.main()
