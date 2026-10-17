"""Groups 3.4 and 3.5 of the frame: proof (EV-1 to EV-4) and order (ORD-1 to ORD-5), on fakes.

EV-1's fixtures (by hand, killed after the publish, a create killed after its answer record) are in
`test_log_op.TheProbe`, where the probe that decides them is tested. EV-5 to EV-7 are a restore's.
"""
import hashlib
import json
import os
import unittest

import harness
import rowlib
from sun_core import state as statemod
from test_log_op import at, planted

NEED = "the thing"


def need(level, **more):
    out = {"output": NEED, "level": level, "treatment": "then not applicable"}
    out.update(more)
    return [out]


class OrdCase(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.count = 0

    def fresh(self, rows, **lane):
        self.count += 1
        m = harness.Machine(self.tmp, "m%d" % self.count, "m%d" % self.count)
        rowlib.install(m, rowlib.lane("sunrise", rows, **lane))
        m.put("shortcuts.txt", "alias other\n")
        return m

    # ---- one provider ended in each of the thirteen final statuses --------------------------------
    def provider(self, status, needing, last_record=False):
        """A machine on which the provider of NEED has ended `status`, with the run driven as far as
        it goes; returns (machine, run id, the last result). With `last_record`, the lane has a run's last record (KEEP-5)
        alone in a last phase."""
        if last_record:
            plain = self.fresh

            def fresh(rows, **lane):
                return plain(list(rows) + [rowlib.last_record("Z9")], phases=("one", "the last record"), **lane)
            self.fresh = fresh
            try:
                return self.provider(status, needing)
            finally:
                self.fresh = plain
        set_host = lambda m, state: m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": state, "name": "demo"}})  # noqa: E731
        if status == "done":
            m = self.fresh([rowlib.build("P", output=NEED), needing])
            looked, last = m.started()
        elif status == "already so":
            # found already so in the run: the look saw the before-state, and the after-state holds before the run acts
            m = self.fresh([rowlib.refusing("P", output=NEED), needing])
            set_host(m, "active")
            looked = m.look()
            set_host(m, "paused")
            last = m.go(looked)
        elif status == "not proven":
            m = self.fresh([rowlib.refusing("P", output=NEED), needing])
            set_host(m, "active")
            looked = m.look()
            m.go(looked, kill=at("post", "journal", "start", "P"))
            set_host(m, "paused")
            last = m.resume()
        elif status == "adopted":
            m = self.fresh([dict(rowlib.adopt("P"), output={"name": "project folder", "fields": {"path": {"input": "adopt.project folder"}}}),
                            dict(needing, needs=[dict(needing["needs"][0], output="project folder")])])
            folder = os.path.dirname(m.put("dev/prototype/README.md", "# mine\n"))
            looked, last = m.started(inputs=m.inputs(adopt={"project folder": folder}))
        elif status == "passed":
            m = self.fresh([rowlib.check("P", output=NEED), needing])
            looked, last = m.started()
        elif status == "unavailable":
            row = rowlib.check("P", output=NEED)
            row["thing"]["capability"] = "canary"
            m = self.fresh([row, needing])
            looked, last = m.started()
        elif status == "refused":
            create = rowlib.create("P", output=NEED)
            create["construction"]["alternatives"] = ["terms"]
            terms = rowlib.owner_answer("T", condition={"on": "alternative", "operation": "P", "result": "terms"})
            m = self.fresh([create, terms, needing])
            m.plan_fake("fakehost", {"command": "create", "do": "terms"})
            looked, last = m.started()
        elif status == "done by owner, read back":
            m = self.fresh([rowlib.owner_step("P", mode="read back", output=NEED), needing])
            set_host(m, "connected")
            looked, last = m.started()
        elif status == "done by owner, on his word":
            m = self.fresh([rowlib.owner_step("P", mode="on his word", output=NEED), needing])
            looked, _ = m.started()
            last = m.resume("demo", None, "--done", "P")
        elif status == "answered":
            m = self.fresh([rowlib.owner_answer("P", output=NEED), needing])
            looked, _ = m.started()
            last = m.resume("demo", None, "--answer", "P=use it")
        elif status == "left":
            m = self.fresh([rowlib.owner_answer("P", output=NEED), needing])
            looked, _ = m.started()
            last = m.resume("demo", None, "--leave", "P")
        elif status == "not needed":
            first = rowlib.create("Q", output="first try")
            first["construction"]["alternatives"] = ["terms"]
            second = rowlib.check("P", output=NEED, condition={"on": "alternative", "operation": "Q", "result": "terms"})
            m = self.fresh([first, second, needing])
            looked, last = m.started()
        elif status == "held":
            m = self.fresh([rowlib.owner_answer("L", output="his answer"),
                            rowlib.check("P", output=NEED, needs=[{"output": "his answer", "level": "state", "treatment": "then not applicable"}]), needing])
            looked, _ = m.started()
            last = m.resume("demo", None, "--leave", "L")
        else:
            raise AssertionError(status)
        return m, looked.doc["run"], last

    # ORD-1's table, written here by hand from the frame (hash 9900a598d4b7e2f1), never from the code's own table (the
    # reviewer's T1): "| The provider's final status | state | made | passed | answered |", row by row.
    FRAME_ORD1 = (
        ("done", ("meets", "meets", "stop", "stop")),
        ("already so", ("meets", "stop", "stop", "stop")),
        ("not proven", ("meets", "stop", "stop", "stop")),
        ("adopted", ("meets", "stop", "stop", "stop")),
        ("passed", ("stop", "stop", "meets, as OP-8 limits it", "stop")),
        ("unavailable", ("stop", "stop", "meets where the need is marked as accepting it; otherwise stop", "stop")),
        ("refused", ("branch", "branch", "branch", "branch")),
        ("done by owner, read back", ("meets", "stop", "stop", "stop")),
        ("done by owner, on his word", ("meets where the need is marked as accepting his word; otherwise stop", "stop", "stop", "stop")),
        ("answered", ("stop", "stop", "stop", "meets with a value the need names; his with any other value")),
        ("left", ("his", "his", "his", "his")),
        ("not needed", ("branch", "branch", "branch", "branch")),
        ("held", ("his", "his", "his", "his")),
    )
    FRAME_LEVELS = ("state", "made", "passed", "answered")
    # how a fixture marks a need as accepting (the row schema's words; an input of the fixture, not an expected answer)
    MARKS = {"unavailable": "unavailable", "done by owner, on his word": "his word"}

    def test_ORD1_T1_the_fifty_two_pairs_each_assert_the_cell_of_the_frames_table_written_by_hand(self):
        self.assertEqual(len(self.FRAME_ORD1) * len(self.FRAME_LEVELS), 52)
        self.assertEqual(sorted(statemod.FINAL), sorted(s_ for s_, _ in self.FRAME_ORD1), "the code's statuses are not the frame's")
        self.assertEqual(tuple(statemod.LEVELS), self.FRAME_LEVELS)
        seen = 0
        for status, cells in self.FRAME_ORD1:
            for level, cell in zip(self.FRAME_LEVELS, cells):
                if cell.startswith("meets where the need is marked"):
                    variants = [("meets", {"accepts": [self.MARKS[status]]}), ("stop", {})]
                elif cell.startswith("meets with a value the need names"):
                    variants = [("meets", {"value": "use it"}), ("his", {"value": "keep the old file"})]
                else:
                    variants = [(cell.split(",")[0], {})]
                if level == "answered":
                    variants = [(want, dict(more, value=more.get("value", "use it"))) for want, more in variants]
                for want, more in variants:
                    with self.subTest(status=status, level=level, cell=want):
                        self.assert_cell(status, level, want, more)
                        seen += 1
        self.assertEqual(seen, 52 + 3)

    def assert_cell(self, status, level, want, more):
        needing = rowlib.check("N", needs=need(level, **more), output="needed")
        m, run, last = self.provider(status, needing, last_record=True)
        statuses = m.statuses(run)
        self.assertEqual(statuses.get("P"), status, "the fixture's provider did not end %s: %s" % (status, last.text[:400]))
        published = [n for n in os.listdir(m.dev) if n.startswith("demo-record-")]
        if (status, level) == ("adopted", "made"):
            # ORD-1: "a need at the made level on an output that only an adopt provides is settled there too (ORD-2), so the
            # cell of `adopted` at the made level is reached only where another operation provides that output as well"
            self.assertEqual(statuses.get("P"), "adopted")
            self.assertNotIn("N", statuses)
            manifest = json.load(open(os.path.join(m.facts.run_dir(run), "manifest-1.json")))
            self.assertEqual([s_["operation"] for s_ in manifest["settled_needs"]], ["N"])
            return
        if want == "meets":
            self.assertEqual(statuses.get("N"), "passed", "%s at the %s level should meet: %s" % (status, level, last.text[:300]))
            return
        if want in ("stop", "branch"):
            # "the run ends `stopped` with the reason kind "need unmet" and the operation, the need and the status named, no
            # `held` record is written, the run is open, and no last record is published"
            self.assertEqual(last.ending, "stopped", last.text[:400])
            self.assertIn("stopped: need unmet", last.lines)
            self.assertIn("operation: N", last.lines)
            form = open(last.doc["forms"][0]).read()
            self.assertIn("the need: %s at the %s level; P ended %s" % (NEED if status != "adopted" else "project folder", level, status), form)
            self.assertNotIn("N", statuses, "the operation that has the need got a status")
            self.assertFalse([r for r in m.journal(run) if r.get("status") == "held"], "a held record was written")
            self.assertIn(run, m.open_runs().values(), "the run is not open after a need-unmet stop")
            self.assertEqual(published, [], "a last record was published")
            return
        self.assertEqual(want, "his")
        # "for `his`, the operation is `held` with its reason, the rest of the run goes on, and the run ends `ended with exceptions`"
        self.assertEqual(statuses.get("N"), "held")
        self.assertEqual(last.ending, "ended with exceptions", last.text[:400])
        form = open(last.doc["forms"][0]).read()
        self.assertIn("not run:", form)
        self.assertIn("P ended %s" % status, form)
        self.assertEqual(statuses.get("Z9"), "done", "the rest of the run did not go on")

    def test_ORD1_with_two_providers_stop_outranks_his_and_his_outranks_branch(self):
        def two(first_status, second_status):
            first = rowlib.refusing("P1", output=NEED) if first_status == "not proven" else rowlib.create("P1", output=NEED)
            if first_status == "refused":
                first["construction"]["alternatives"] = ["terms"]
            if second_status == "left":
                second = rowlib.owner_answer("P2", output=NEED, condition={"on": "alternative", "operation": "P1", "result": "terms"} if first_status == "refused" else rowlib.NONE)
            else:
                second = rowlib.check("P2", output=NEED, condition={"on": "alternative", "operation": "P0", "result": "terms"})
            rows = [first, second, rowlib.check("N", needs=need("state"), output="needed")]
            if second_status == "not needed":
                zero = rowlib.create("P0", output="zero", name=rowlib.lit("zero"))
                zero["construction"]["alternatives"] = ["terms"]
                rows.insert(0, zero)
            return rows
        # `not proven` beside `left` stops. No manifest that ORD-3 lets build has both of two alternatives run (question 5
        # of the report), so this one is asserted on the journal's reading alone, with the records written by hand
        class Journal(object):
            records = [{"n": 0, "kind": "status", "op": "P1", "status": "not proven"}, {"n": 1, "kind": "status", "op": "P2", "status": "left"}]
        manifest = {"operations": [dict(rowlib.refusing("P1", output=NEED)), dict(rowlib.owner_answer("P2", output=NEED))], "phases": ["one"]}
        for level in ("state", "made"):
            verdict = statemod.State(manifest, Journal()).need({"output": NEED, "level": level})
            self.assertEqual(verdict, ("met", "P1", "not proven") if level == "state" else ("stop", "P1", "not proven"))
        # `refused` beside `left` is held
        m = self.fresh(two("refused", "left"))
        m.plan_fake("fakehost", {"command": "create", "do": "terms"})
        looked, _ = m.started()
        last = m.resume("demo", None, "--leave", "P2")
        self.assertEqual(m.statuses(looked.doc["run"]), {"P1": "refused", "P2": "left", "N": "held"})
        self.assertEqual(last.ending, "ended with exceptions")
        # `refused` beside `not needed` stops: every branch of the plan ended and none provided the thing
        first = rowlib.create("P1", output=NEED)
        first["construction"]["alternatives"] = ["terms", "conflict"]
        rows = [first, rowlib.check("P2", output=NEED, condition={"on": "alternative", "operation": "P1", "result": "conflict"}),
                rowlib.owner_answer("T", output="terms seen", condition={"on": "alternative", "operation": "P1", "result": "terms"}),
                rowlib.check("N", needs=need("state"), output="needed")]
        m = self.fresh(rows)
        m.plan_fake("fakehost", {"command": "create", "do": "terms"})
        looked, last = m.started()
        self.assertEqual(m.statuses(looked.doc["run"]), {"P1": "refused", "P2": "not needed"}, last.text)
        self.assertIn("stopped: need unmet", last.lines)
        self.assertIn(looked.doc["run"], m.open_runs().values())

    def test_ORD2_a_need_with_no_treatment_and_a_circle_of_needs_fail_the_build_naming_the_row_and_a_treatment_settles(self):
        bare = rowlib.check("N", needs=[{"output": "nothing provides this", "level": "state"}])
        m = self.fresh([bare])
        failed = m.look()
        self.assertEqual(failed.code, 4)
        self.assertEqual([(f["row"], f["entry"]) for f in failed.doc["findings"]], [("N", "needs")])
        a = rowlib.check("A", output="a", needs=[{"output": "b", "level": "passed", "treatment": "then not applicable"}])
        b = rowlib.check("B", output="b", needs=[{"output": "a", "level": "passed", "treatment": "then not applicable"}])
        circle = self.fresh([a, b]).look()
        self.assertEqual(circle.code, 4)
        self.assertIn("a circle of needs (ORD-2)", json.dumps(circle.doc["findings"]))
        left_out = rowlib.check("N", needs=[{"output": "nothing provides this", "level": "state", "treatment": "then not applicable"}])
        dropped = rowlib.check("M", needs=[{"output": "nothing provides this", "level": "state", "treatment": "then not needed"}])
        m = self.fresh([left_out, dropped])
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = json.load(open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")))
        self.assertEqual([o["id"] for o in manifest["operations"]], ["M"])
        self.assertEqual(manifest["operations"][0]["needs"], "none")
        for flags in ({"database": True}, {"database": False}):
            hosted = rowlib.check("H", output="hosted", condition={"on": "fact", "fact": "flags.database", "equals": True, "reason": "a flag"})
            user = rowlib.check("U", needs=[{"output": "hosted", "level": "passed", "treatment": "then not applicable"}])
            m = self.fresh([hosted, user])
            looked = m.look(inputs=m.inputs(flags=flags))
            self.assertEqual(looked.ending, "preview", "a combination of flags the owner may ask for does not build: %s" % looked.text[:300])
            self.assertEqual(m.go(looked).ending, "complete")

    def test_ORD2_ORD1_after_a_need_unmet_stop_a_replan_settles_the_need_by_its_rows_treatment_and_the_run_goes_on(self):
        needing = rowlib.check("N", needs=need("made"), output="needed")
        m, run, last = self.provider("done by owner, read back", needing)
        self.assertIn("stopped: need unmet", last.lines)
        replanned = m.summon("replan", "demo", "--inputs", m.inputs())
        preview = open(replanned.doc["forms"][0]).read()
        self.assertIn("N: left out (%s ended done by owner, read back)" % NEED, preview)
        went = m.run("go", "--kind", "sunrise", "--name", "demo", "--run", run, "--manifest-sha256", replanned.doc["manifest_sha256"])
        self.assertEqual(went.ending, "complete", went.text)

    def terms_rows(self):
        first = rowlib.create("P1", output="database")
        first["construction"]["alternatives"] = ["terms"]
        accept = rowlib.owner_step("T1", mode="on his word", output="terms accepted", condition={"on": "alternative", "operation": "P1", "result": "terms"})
        second = rowlib.create("P2", output="database", condition={"on": "alternative", "operation": "P1", "result": "terms"},
                               needs=[{"output": "terms accepted", "level": "state", "accepts": ["his word"], "treatment": "then not applicable"}])
        user = rowlib.cas("G1", needs=[{"output": "database", "level": "made", "treatment": "then not applicable"}])
        return [first, accept, second, user]

    def test_ORD3_an_alternative_result_takes_the_other_branch_and_the_dependents_run_once_after_the_output_is_established(self):
        m = self.fresh(self.terms_rows())
        m.plan_fake("fakehost", {"command": "create", "nth": 1, "do": "terms"})
        looked, went = m.started()
        run = looked.doc["run"]
        self.assertEqual(went.ending, "waiting", went.text)
        self.assertEqual(m.statuses(run), {"P1": "refused"})
        self.assertEqual(m.calls("fakegit", "cas"), [], "a dependent ran before the output was established")
        done = m.resume("demo", None, "--done", "T1")
        self.assertEqual(done.ending, "complete", done.text)
        self.assertEqual(m.statuses(run), {"P1": "refused", "T1": "done by owner, on his word", "P2": "done", "G1": "done"})
        self.assertEqual(len(m.calls("fakegit", "cas")), 1)
        self.assertIn("the branch was not taken", open(done.doc["forms"][0]).read())
        ok = self.fresh(self.terms_rows())
        looked, went = ok.started()
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(ok.statuses(looked.doc["run"]), {"P1": "done", "T1": "not needed", "P2": "not needed", "G1": "done"})
        self.assertEqual(len(ok.calls("fakegit", "cas")), 1)

    def test_ORD3_a_condition_on_an_answers_value_and_on_a_planning_fact(self):
        rows = [rowlib.owner_answer("A1", output="choice"),
                rowlib.check("Y", output="on yes", condition={"on": "answer", "operation": "A1", "equals": "use it"}),
                rowlib.check("Z", output="on no", condition={"on": "answer", "operation": "A1", "equals": "keep the old file"}),
                rowlib.check("F", output="flagged", condition={"on": "fact", "fact": "flags.extra", "equals": True, "reason": "a flag"})]
        m = self.fresh(rows)
        looked, _ = m.started(inputs=m.inputs(flags={"extra": False}))
        self.assertIn("not applicable (a flag)", open(looked.doc["forms"][0]).read())
        last = m.resume("demo", None, "--answer", "A1=use it")
        self.assertEqual(m.statuses(looked.doc["run"]), {"A1": "answered", "Y": "passed", "Z": "not needed"})

    def test_ORD3_D16_two_alternatives_with_no_condition_between_them_or_conditioned_on_the_same_result_fail_the_build(self):
        plain = [rowlib.build("B1", output="one output"), rowlib.build("B2", output="one output", place=rowlib.path(rowlib.DEV, "elsewhere"))]
        failed = self.fresh(plain).look()
        self.assertEqual(failed.code, 4)
        self.assertIn("two alternatives that could run at the same time (ORD-3)", json.dumps(failed.doc["findings"]))
        first = rowlib.create("P0", output="zero")
        first["construction"]["alternatives"] = ["terms"]
        same = {"on": "alternative", "operation": "P0", "result": "terms"}
        overlapping = [first, rowlib.check("X1", output="one output", condition=dict(same)), rowlib.check("X2", output="one output", condition=dict(same))]
        failed = self.fresh(overlapping).look()
        self.assertEqual(failed.code, 4, failed.text)
        self.assertEqual([f["row"] for f in failed.doc["findings"]], ["X2"])

    def test_ORD4_a_waiting_step_holds_back_its_dependents_and_the_next_phase_and_nothing_else(self):
        rows = [rowlib.owner_step("O1", "first", mode="on his word", output="his step"),
                rowlib.check("K1", "first", output="free of it"),
                rowlib.check("K2", "first", output="needs it", needs=[{"output": "his step", "level": "state", "accepts": ["his word"], "treatment": "then not applicable"}]),
                rowlib.check("K3", "second", output="later")]
        m = self.fresh(rows, phases=["first", "second"])
        looked, went = m.started()
        self.assertEqual(went.ending, "waiting")
        self.assertEqual(m.statuses(looked.doc["run"]), {"K1": "passed"})
        done = m.resume("demo", None, "--done", "O1")
        self.assertEqual(done.ending, "complete")

    def test_ORD4_a_manifest_whose_phases_break_the_rule_fails_its_build(self):
        from sun_core import plan
        retire = rowlib.retiring(rowlib.refusing("T22"))
        m = self.fresh([])
        m.put("dev/demo.env", "DATABASE_URL=postgres://app:" + harness.canary("dbpass") + "@db.invalid/app\n", 0o600)
        m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}}, identity="db-" + hashlib.sha256(m.home.encode()).hexdigest()[:10])   # one identity on both sides (KEEP-2)
        keep = rowlib.keep("P1", plan.RETIREMENT_PHASES[0])
        rowlib.install(m, rowlib.lane("sunset", [keep, dict(retire, phase="keeping")], phases=plan.RETIREMENT_PHASES))
        failed = m.look(kind="sunset")
        self.assertEqual(failed.code, 4, failed.text)
        self.assertIn("a retiring operation in the keeping phase (ORD-4)", json.dumps(failed.doc["findings"]))
        swapped = [plan.RETIREMENT_PHASES[i] for i in (0, 2, 1, 3)]
        rowlib.install(m, rowlib.lane("sunset", [keep, dict(retire, phase=plan.RETIREMENT_PHASES[2])], phases=swapped))
        failed = m.look(kind="sunset")
        self.assertEqual(failed.code, 4)
        self.assertIn("in that order (ORD-4)", json.dumps(failed.doc["findings"]))
        back = rowlib.move("V1", "moving", output="the repository")
        load = rowlib.owner_step("V2", "moving", mode="on his word", output="schedule loaded")
        load["thing"].update({"starts": True, "runs_on": ["the repository"]})
        # a restore builds from the key's latest retiring run (EV-7): one is put on record first, closed
        rowlib.install(m, rowlib.lane("sunset", [rowlib.owner_step("O1", plan.RETIREMENT_PHASES[2], mode="on his word")],
                                      phases=plan.RETIREMENT_PHASES))
        self.assertEqual(m.started(kind="sunset")[1].ending, "waiting")
        self.assertEqual(m.summon("close", "demo", "--word", "close").ending, "closed")
        rowlib.install(m, rowlib.lane("restore", [back, load], phases=["moving", "starting"]))
        m.put("dev/demo-scope.md", "x\n")
        failed = m.look(kind="restore")
        self.assertEqual(failed.code, 4, failed.text)
        self.assertIn("it starts something running in the phase that puts back what it runs on (ORD-4)", json.dumps(failed.doc["findings"]))

    def test_ORD4_in_a_retirement_no_provider_retirement_is_called_before_the_last_machine_retirement_is_final(self):
        from sun_core import plan
        P = plan.RETIREMENT_PHASES
        machine = rowlib.retiring(rowlib.move("T12", P[1], output="archived"), where="machine")
        provider = rowlib.retiring(rowlib.refusing("T22", P[2]))
        m = self.fresh([])
        rowlib.install(m, rowlib.lane("sunset", [rowlib.keep("P1", P[0]), provider, machine], phases=P))
        m.put("dev/demo.env", "DATABASE_URL=postgres://app:" + harness.canary("dbpass") + "@db.invalid/app\n", 0o600)
        m.put("dev/demo-scope.md", "x\n")
        m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}}, identity="db-" + hashlib.sha256(m.home.encode()).hexdigest()[:10])   # one identity on both sides (KEEP-2)
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        events = went.events
        moved = next(e["i"] for e in events if at("post", "journal", "completion", "T12")(e))
        retired = next(e["i"] for e in events if e["op"] == "child" and e["stage"] == "pre" and e.get("argv", [""])[0] == "set")
        self.assertLess(moved, retired)

    def test_ORD5_D16_the_first_eligible_operation_in_the_manifests_order_runs_first(self):
        rows = [rowlib.check("K%d" % i, output="o%d" % i) for i in (3, 1, 2)]
        m = self.fresh(rows)
        looked, went = m.started()
        order = [r["op"] for r in m.journal(looked.doc["run"]) if r["kind"] == "attempt"]
        self.assertEqual(order, ["K3", "K1", "K2"], "the operations did not run in the manifest's order")


class ProofBase(OrdCase):
    test_ORD1_T1_the_fifty_two_pairs_each_assert_the_cell_of_the_frames_table_written_by_hand = None
    test_ORD1_with_two_providers_stop_outranks_his_and_his_outranks_branch = None
    test_ORD2_a_need_with_no_treatment_and_a_circle_of_needs_fail_the_build_naming_the_row_and_a_treatment_settles = None
    test_ORD2_ORD1_after_a_need_unmet_stop_a_replan_settles_the_need_by_its_rows_treatment_and_the_run_goes_on = None
    test_ORD3_an_alternative_result_takes_the_other_branch_and_the_dependents_run_once_after_the_output_is_established = None
    test_ORD3_a_condition_on_an_answers_value_and_on_a_planning_fact = None
    test_ORD3_D16_two_alternatives_with_no_condition_between_them_or_conditioned_on_the_same_result_fail_the_build = None
    test_ORD4_a_waiting_step_holds_back_its_dependents_and_the_next_phase_and_nothing_else = None
    test_ORD4_a_manifest_whose_phases_break_the_rule_fails_its_build = None
    test_ORD4_in_a_retirement_no_provider_retirement_is_called_before_the_last_machine_retirement_is_final = None
    test_ORD5_D16_the_first_eligible_operation_in_the_manifests_order_runs_first = None


class Proof(ProofBase):
    def test_EV3_completion_is_history_one_more_commit_after_the_kill_and_no_probe_of_a_final_operation(self):
        tracked = rowlib.path(rowlib.DEV, "tracked.txt")
        first = rowlib.cas("G1", ref="main", new="c1", old="none", output="first commit")
        edit = rowlib.swap_add("E1", line=rowlib.lit("an approved edit"), file=tracked, output="edited",
                               needs=[{"output": "first commit", "level": "made", "treatment": "then not applicable"}])
        edit["before_test"] = [c for c in edit["before_test"] if c["read"] != "name-free"]
        edit["construction"]["risks"] = ["RK2"]
        second = rowlib.cas("G2", ref="main", new="c2", old={"output": "first commit.ref"}, output="second commit",
                            needs=[{"output": "edited", "level": "state", "treatment": "then not applicable"}])
        second["thing"]["also"] = [{"role": "the tracked file", "identity": "path", "place": tracked, "tracked": ["exists", "sha256"]}]
        for label, plant in (("clean", None), ("an unapproved edit", "edit")):
            with self.subTest(resume_after=label):
                m = self.fresh([first, edit, second])
                m.put("dev/tracked.txt", "line one\n")
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                went = m.go(looked, kill=at("post", "journal", "completion", "E1"))
                self.assertTrue(went.killed)
                if plant:
                    with open(os.path.join(m.dev, "tracked.txt"), "a") as fh:
                        fh.write("an unapproved edit\n")
                calls_before = len(m.calls("fakegit"))
                resumed = m.resume()
                later = m.calls("fakegit")[calls_before:]
                if plant:
                    self.assertEqual(resumed.ending, "stopped")
                    self.assertIn("stopped: foreign", resumed.lines)
                    # EV-3: named "by its role in the row, and by its safe name where it has one"
                    self.assertIn("stopped: foreign (the tracked file, %s); operation G2" % os.path.join(m.dev, "tracked.txt"),
                                  open(resumed.doc["forms"][0]).read())
                    self.assertEqual([c for c in later if c["changing"]], [])
                else:
                    self.assertEqual(resumed.ending, "complete", resumed.text)
                    self.assertEqual([c["argv"][0] for c in later if c["changing"]], ["cas"], "not exactly one more commit")
                    self.assertEqual(m.fake("fakegit", "state.json")["refs"], {"main": "c2"})
                    for call in later:
                        self.assertNotIn("c1", [call["argv"][call["argv"].index("--new") + 1]] if "--new" in call["argv"] else [],
                                         "a finished operation was applied again")
                    probed = [c for c in later if "--expect" in c["argv"] or c["argv"][0] == "ref"]
                    self.assertTrue(all("none" not in c["argv"] for c in probed), "an operation with a final record was probed again")

    def test_EV3_A45_a_thing_whose_only_identity_is_a_held_id_is_named_by_its_role_its_kind_and_its_records_reference(self):
        # EV-3: "where its identity is a held value (SEC-4), by its role, its kind and the reference of the protected
        # record that holds that identity, as SEC-6 has a form refer to one, and never by the held value. That last is
        # run with a thing whose only identity is an id a fake provider made: the stop's form names the role, the kind
        # and the record's reference, and the id is in no output, form or journal record."
        made = rowlib.create("C1", output="remote")
        made["thing"]["after_word"] = "active"      # the state its after-check reads; its completion records it as observed
        later = rowlib.build("B1", needs=[{"output": "remote", "level": "made", "treatment": "then not applicable"}])
        later["thing"]["also"] = [{"role": "the thing the run made at the fake host", "identity": "provider id",
                                   "kind": "a repository at the fake host", "id": {"output": "remote.id"},
                                   "read": {"command": "by-id", "field": "state"}}]
        later["commands"] = (later.get("commands") if isinstance(later.get("commands"), list) else []) + [
            rowlib.use("by-id", "fakehost.get-by-id", idfile={"output": "remote.id"})]
        for label, change in (("untouched", False), ("changed by another actor", True)):
            with self.subTest(thing=label):
                m = self.fresh([made, later])
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)

                def pause():
                    state = m.fake("fakehost", "state.json")
                    for thing in state["things"].values():
                        thing["state"] = "paused"
                    m.set_fake("fakehost", things=state["things"])
                hook = planted(at("post", "journal", "completion", "C1"), pause) if change else None
                went = m.go(looked, kill=hook)
                run = looked.doc["run"]
                if not change:
                    self.assertEqual(went.ending, "complete", went.text)
                    continue
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("stopped: foreign", went.lines)
                ident = [t["id"] for t in m.fake("fakehost", "state.json")["things"].values()][0]
                answer = [r for r in m.journal(run) if r["kind"] == "answer" and r.get("op") == "C1"][0]
                record = answer["held"]["record"]           # the protected record the answer record refers to (LOG-2)
                form = open(went.doc["forms"][0]).read()
                # "the stop's form names the role, the kind and the record's reference, and the id is in no output, form or
                # journal record"
                self.assertIn("the thing the run made at the fake host", form)
                self.assertIn("a repository at the fake host", form)
                self.assertIn(record, form, "the protected record's reference is not named")
                for text in (form, went.text):
                    self.assertNotIn(ident, text, "the held id is shown")
                for item in m.journal(run):
                    self.assertNotIn(ident, json.dumps(item), "the held id is in a journal record")
                self.assertNotIn("B1", m.statuses(run))

    def test_EV3_OP5_batch34_the_targets_own_state_at_its_turn_gives_ready_already_so_or_foreign_as_OP5s_rows_give_them(self):
        """EV-3's test line as batch 34 words it (A82): "The target's own state, asked at every operation of every run: in a
        sunset fixture whose change of a tracked file has no record in the journal, the target at its turn in the state the
        manifest recorded at the look gives `ready` (OP-5) and the change runs; with the file put in the row's after-state by
        another actor before its turn, it gives `already so`, which is recorded and the run goes on (OP-6), with no stop for
        the difference from the state recorded at the look; and with the file put by another actor in a state that is
        neither, it gives `foreign`, the run stops, and the form names the file as the operation's target by its role and
        its safe name." The fixture is the sunset's replaced status line of `test_restore.span_rows`; "neither" is run twice:
        the line twice, so that neither test of the row holds, and the file's other bytes changed with the line still there
        once, so that it is in neither the state the manifest recorded at the look nor the row's after-state (OP-5's `ready`:
        "each thing the operation names is in its expected state (EV-3) and the before-test holds")."""
        from sun_core import plan
        from test_restore import span_rows
        cases = (("in the state recorded at the look", None),
                 ("in the row's after-state", "head line\nstatus: retired\ntail line\n"),
                 ("neither: the line twice", "head line\nstatus: live\nstatus: live\ntail line\n"),
                 ("neither: the line once and the rest changed", "head line, edited\nstatus: live\ntail line\n"))
        for case, by_another in cases:
            with self.subTest(target=case):
                self.count += 1
                m = harness.Machine(self.tmp, "e%d" % self.count, "e%d" % self.count)
                rowlib.install(m, rowlib.lane("sunset", span_rows("replace"), phases=plan.RETIREMENT_PHASES),
                               rowlib.lane("restore", [], phases=("putting back",)))
                path = m.put("dev/status.txt", "head line\nstatus: live\ntail line\n")
                looked = m.look(kind="sunset")
                self.assertEqual(looked.ending, "preview", looked.text)
                run = looked.doc["run"]
                if by_another is not None:
                    with open(path, "w") as fh:          # another actor, before the operation's turn
                        fh.write(by_another)
                went = m.go(looked, kind="sunset")
                starts = [r for r in m.journal(run) if r["kind"] == "start" and r.get("op") == "RS"]
                if by_another is None:
                    self.assertEqual(went.ending, "complete", went.text)
                    self.assertEqual([r.get("probe") for r in starts], ["ready"], "the target at its turn did not give `ready`")
                    self.assertEqual(open(path).read(), "head line\nstatus: retired\ntail line\n", "the change did not run")
                elif case == "in the row's after-state":
                    self.assertEqual(went.ending, "complete", went.text)
                    self.assertEqual(m.statuses(run).get("RS"), "already so", "`already so` was not recorded")
                    self.assertEqual(starts, [], "the change ran on a target already in its after-state")
                    self.assertNotIn("foreign", went.text + open(went.doc["forms"][0]).read())
                    self.assertEqual(open(path).read(), by_another)
                else:
                    self.assertEqual(went.ending, "stopped", went.text)
                    self.assertIn("stopped: foreign", went.lines)
                    self.assertEqual(starts, [], "the change was started")
                    self.assertEqual(open(path).read(), by_another, "the file was changed")
                    # named as the operation's target, by its role in the row and its safe name
                    self.assertIn("stopped: foreign (the status file, %s); operation RS" % path, open(went.doc["forms"][0]).read())

    def test_EV4_a_way_back_is_recorded_only_for_a_done_operation_whose_inputs_are_on_record(self):
        m = self.fresh(rowlib.clean_rows(), phases=("prepare", "remote"))
        m.put("dev/demo-scope.md", "scope\n")
        looked, went = m.started()
        run = looked.doc["run"]
        completions = dict((r["op"], r) for r in m.journal(run) if r["kind"] == "completion")
        for op in ("S1", "M1"):
            self.assertTrue(completions[op]["way_back"]["offered"], op)
            self.assertTrue(completions[op]["way_back"]["inputs"], op)
        for op in ("B1", "C1", "G1", "H1"):
            self.assertEqual(completions[op]["way_back"], {"offered": False, "reason": "the row declares none"}, op)
        # a done operation with an input removed: no way back, "an input is missing"
        lost = self.fresh(rowlib.clean_rows(), phases=("prepare", "remote"))
        lost.put("dev/demo-scope.md", "scope\n")
        looked = lost.look()
        lost.go(looked, kill=at("post", "swap"))
        run = looked.doc["run"]
        start = [r for r in lost.journal(run) if r["kind"] == "start" and r["op"] == "S1"][-1]
        os.remove(os.path.join(lost.facts.run_dir(run), "protected", start["inputs"][0]["record"]))
        lost.resume()
        done = [r for r in lost.journal(run) if r["kind"] == "completion" and r["op"] == "S1"][0]
        self.assertEqual(done["way_back"], {"offered": False, "reason": "an input is missing"})

    def test_EV4_each_final_status_other_than_done_records_no_way_back_with_its_reason(self):
        needing = rowlib.check("N", needs=need("state"), output="needed")
        wants = {"already so": "found already so", "not proven": "not proven", "left": "the row declares none", "held": None,
                 "done by owner, on his word": "the row declares none", "refused": "the row declares none"}
        for status, reason in wants.items():
            with self.subTest(status=status):
                m, run, last = self.provider(status, needing)
                records = [r for r in m.journal(run) if r["kind"] == "status" and r["status"] == status]
                if status == "already so":
                    reason = "found already so"
                if status == "held":
                    m, run, last = self.provider("left", rowlib.check("N", needs=need("state"), output="needed"))
                    records = [r for r in m.journal(run) if r["kind"] == "status" and r["status"] == "held"]
                    reason = "the row declares none"
                self.assertTrue(records, last.text[:300])
                self.assertEqual((records[0]["way_back"]["offered"], records[0]["way_back"]["reason"]), (False, reason))
        m = self.fresh(rowlib.clean_rows(), phases=("prepare", "remote"))
        m.put("dev/demo-scope.md", "scope\n")
        with open(m.path("shortcuts.txt"), "a") as fh:
            fh.write("")
        looked = m.look()
        with open(m.path("shortcuts.txt"), "a") as fh:
            fh.write("alias demo\n")
        m.go(looked)
        found = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "status" and r["op"] == "S1"][0]
        self.assertEqual(found["way_back"], {"offered": False, "reason": "found already so"})

    def test_EV4_batch30_where_none_of_the_five_reasons_is_true_the_reason_is_the_operations_own_final_status(self):
        """EV-4 (batch 30): "Where none of these is true of an operation, the reason is its own final status, named as such: a
        `not needed`, `refused`, `left` or `held` change whose row declares a way back among them." Its test line: "a change
        whose row declares a way back and that ended `not needed` has the reason `not needed`, and every final record of the
        run holds a way-back field." Here: a move declaring a way back, `not needed` (its condition is the other branch of a
        create that succeeded); an owner step declaring one, `left`; another declaring one, `held` on the first; a check
        (`passed`), an owner answer (`answered`) and the create (`done`), whose rows declare none."""
        m = self.fresh([])
        q = rowlib.create("Q", output="first try")
        q["construction"]["alternatives"] = ["terms"]
        mn = rowlib.move("MN", condition={"on": "alternative", "operation": "Q", "result": "terms"})

        def stepping(rid, **more):
            reverse = rowlib.owner_step(rid + "-reverse", mode="on his word", safe_content={"step": "put it back by hand"}, output="back " + rid)
            return rowlib.owner_step(rid, mode="on his word", output="done " + rid, way_back={"reverse": reverse},
                                     reverse_inputs=[{"read": "file", "path": rowlib.path(rowlib.DEV, "step-input.txt"), "type": "definition",
                                                      "label": "what the owner's step changed"}], **more)
        ol = stepping("OL")
        oh = stepping("OH", needs=[{"output": "done OL", "level": "state", "treatment": "then not applicable"}])
        rows = [rowlib.check("K"), q, mn, ol, oh, rowlib.owner_answer("A1")]
        rowlib.install(m, rowlib.lane("sunrise", rows))
        m.put("dev/demo-scope.md", "scope\n")
        m.put("dev/step-input.txt", "the setting before\n")
        looked, went = m.started()
        self.assertEqual(went.ending, "waiting", went.text)
        self.assertEqual(m.resume("demo", None, "--leave", "OL").ending, "waiting")
        last = m.resume("demo", None, "--answer", "A1=use it")
        self.assertEqual(last.ending, "ended with exceptions", last.text)
        run = looked.doc["run"]
        self.assertEqual(m.statuses(run), {"K": "passed", "Q": "done", "MN": "not needed", "OL": "left", "OH": "held", "A1": "answered"})
        finals = {}
        for record in m.journal(run):
            if record["kind"] in ("completion", "status") or (record["kind"] == "attempt" and record.get("answer") in ("passed", "unavailable")):
                finals[record["op"]] = record
        for op, record in sorted(finals.items()):
            self.assertIn("way_back", record, "the final record of %s holds no way-back field" % op)
        want = {"MN": "not needed", "OL": "left", "OH": "held", "K": "the row declares none", "A1": "the row declares none",
                "Q": "the row declares none"}
        self.assertEqual(dict((op, (finals[op].get("way_back") or {}).get("reason")) for op in want), want)
        self.assertFalse(any((finals[op].get("way_back") or {}).get("offered") for op in want))


if __name__ == "__main__":
    unittest.main()
