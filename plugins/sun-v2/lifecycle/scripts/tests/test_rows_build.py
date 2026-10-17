"""Group 3.9 of the frame (ROW-1 to ROW-3) and Part 4's RISK-2, with every rule whose test line says "fails the
manifest build": OP-2, OP-3's C5 clause, OP-10, OP-11, EV-4, EV-6, KEEP-4, SEC-3's four templates, SEC-8 and
SEC-12's look clause.

A row is admitted through `sun_core.rows.admit` exactly as a lane's row is; the fixtures are the fake
rows of `rowlib.py`. Where a test drives the command line, a failed build is exit 4 with the row and
the entry named, and no child process is started for it.
"""
import copy
import json
import os
import unittest

import harness
import rowlib
from sun_core import plan, rows, texts

SAMPLES = {
    "thing": {"role": "a thing"}, "planning_test": [{"read": "path", "path": rowlib.DEV, "is": "dir"}],
    "before_test": [{"id": "x", "read": "path", "path": rowlib.DEV, "is": "dir"}], "after_test": [{"read": "path", "path": rowlib.DEV, "is": "dir"}],
    "construction": {"id": "C1"}, "commands": [rowlib.use("extra", "fakehost.noop")], "repo_commands": ["extra"],
    "after_check": [{"read": "path", "path": rowlib.DEV, "is": "dir"}], "lost_answer": {"way": "by dropping the layer only"},
    "way_back": {"none": "a reason"}, "reverse_inputs": [{"read": "value", "value": rowlib.lit("x"), "type": "line", "label": "x"}],
    "span": {"placement": "in place", "ordered": False}, "mode": "read back", "safe_content": {"step": "a step"},
    "answers": ["yes"], "review_file": {"content": rowlib.lit("x"), "type": "definition", "label": "x"},
    "owner_names": {"input": "adopt.project folder"}, "keep_scope": {"scope": "s", "same_state": "s", "content_checks": []},
    "keeps_required": ["P1"],
}


def admitted(row, providers=None):
    providers = providers or rowlib.providers()
    expanded = plan.expand({"rows": [row]}, providers)[0]
    return rows.admit(expanded, providers, plan.held_outputs([expanded]))


class Admission(harness.Case):
    def test_ROW1_a_well_formed_row_of_each_of_the_nine_kinds_builds(self):
        self.assertEqual([r()["kind"] for r in rowlib.ONE_OF_EACH], list(rows.KINDS))
        for make in rowlib.ONE_OF_EACH:
            self.assertEqual(admitted(make()), [], make.__name__)
        self.assertEqual(len(rows.ENTRIES), 25)
        self.assertEqual(sorted(rows.TABLE), sorted(rows.ENTRIES))

    def test_ROW1_every_entry_of_the_table_for_every_kind_fails_naming_the_entry_when_it_is_misstated(self):
        checked = 0
        for make in rowlib.ONE_OF_EACH:
            base = plan.expand({"rows": [make()]}, rowlib.providers())[0]
            kind = base["kind"]
            for entry in rows.ENTRIES:
                keys = ("id", "kind", "phase") if entry == "id_kind_phase" else (entry,)
                rule = rows.letter(entry, kind)
                for key in keys:
                    cases = [("left out", "delete"), ("left empty", "")]
                    if key == "kind":
                        cases = []
                    if rule == "R" and key not in ("id", "kind", "phase"):
                        cases.append(("a required entry written none", "none"))
                    if rule == "F":
                        cases.append(("a forbidden entry stated", SAMPLES[entry]))
                    if rule == "O":
                        holds = rows._o_condition(entry, base)
                        if holds is True:
                            cases.append(("written none where its condition holds", "none"))
                        elif holds is False:
                            cases.append(("stated where its condition does not hold", SAMPLES[entry]))
                    for label, value in cases:
                        row = copy.deepcopy(base)
                        if value == "delete":
                            del row[key]
                        else:
                            row[key] = value
                        found = rows.admit(row, rowlib.providers(), set())
                        with self.subTest(kind=kind, entry=key, mutation=label):
                            self.assertIn(key, [f["entry"] for f in found], "the build did not fail naming the entry: %s" % found)
                            if key != "id":
                                self.assertTrue(all(f["row"] == base["id"] for f in found if f["entry"] == key))
                        checked += 1
        self.assertGreater(checked, 400)

    def test_ROW1_OP2_an_entry_that_is_stated_and_not_allowed_fails_the_same_way(self):
        other = rowlib.check()
        other["kind"] = "delete"
        self.assertEqual([f["entry"] for f in admitted(other)], ["kind"])
        wrong = rowlib.build()
        wrong["construction"] = {"id": "C7", "risks": ["RK4"], "to": rowlib.DEV}
        self.assertIn("a construction OP-2 does not give its kind", [f["finding"] for f in admitted(wrong)])
        risky = rowlib.move()
        risky["construction"]["risks"] = ["RK4", "RK2"]
        self.assertIn("an accepted risk that does not cover its construction", [f["finding"] for f in admitted(risky)])
        level = rowlib.check(needs=[{"output": "x", "level": "proven", "treatment": "then not needed"}])
        self.assertIn("a level ORD-1 does not have", [f["finding"] for f in admitted(level)])
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["get"]["fields"][0]["disposition"] = "secret"       # a state may only be fixed
        self.assertIn("a disposition SEC-4 does not give its type", [f["finding"] for f in admitted(rowlib.refusing(), providers)])
        reverse = rowlib.swap_add()
        reverse["way_back"]["reverse"]["construction"] = {"id": "C6", "risks": ["RK3"], "command": "x"}
        found = admitted(reverse)
        self.assertTrue(any(f["entry"] == "way_back" and "a reverse EV-4 does not allow" in f["finding"] and f["row"] == "S1" for f in found), found)

    def test_OP2_a_manifest_that_holds_one_well_formed_operation_of_each_of_the_nine_kinds_builds(self):
        """OP-2's test line, its first clause: "a manifest that holds one well-formed operation of each of the nine kinds
        builds". Its second clause, the refusals, is `test_ROW1_OP2_an_entry_that_is_stated_and_not_allowed_fails_the_same_way`.
        One lane holds one well-formed row of each of the nine kinds OP-2's table names (`rowlib.ONE_OF_EACH`), and the
        manifest of that one lane builds: the look ends with a preview, and the manifest it wrote holds the nine operations,
        one of each kind. The build (`rowlib.build`) is given an output of its own, since the adopt (`rowlib.adopt`) provides
        "project folder" and two providers of one output with no condition between them fail the build (ORD-3)."""
        m = self.machine()
        nine = [rowlib.check("K1"), rowlib.build("B1", output="new folder"), rowlib.keep("P1"), rowlib.create("C1"),
                rowlib.swap_add("S1"), rowlib.move("M1"), rowlib.owner_step("O1"), rowlib.owner_answer("A1"), rowlib.adopt("D1")]
        self.assertEqual(sorted(r["kind"] for r in nine), sorted(["check", "build", "keep", "create", "change", "move", "owner step",
                                                                  "owner answer", "adopt"]), "the lane does not hold one row of each of OP-2's nine kinds")
        rowlib.install(m, rowlib.lane("sunrise", nine))
        m.put("shortcuts.txt", "alias other\n")
        m.put("dev/demo-scope.md", "scope\n")
        m.put("dev/demo.env", "DATABASE_URL=postgres://appuser:%s@db.fixture.invalid:5432/appdb\n" % ("pw" + harness.canary("op2")), 0o600)
        folder = os.path.dirname(m.put("dev/prototype/README.md", "# mine\n"))
        looked = m.look(inputs=m.inputs(adopt={"project folder": folder}))
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = json.load(open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")))
        self.assertEqual(sorted((o["kind"], o["planning_outcome"]) for o in manifest["operations"]),
                         sorted((r["kind"], "in") for r in nine), "the manifest does not hold the nine, each planned in")

    def test_ROW1_an_owner_answer_builds_with_its_mode_none_and_the_manifest_holds_the_mode_answer(self):
        m = self.machine()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_answer("A1"), rowlib.check("K1"), rowlib.owner_step("O1", mode="on his word")]))
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = json.load(open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")))
        by_id = dict((o["id"], o) for o in manifest["operations"])
        self.assertEqual((by_id["A1"]["mode"], by_id["A1"]["resolved_mode"]), ("none", "answer"))
        self.assertEqual([by_id[k]["planning_test"] for k in ("A1", "K1", "O1")], ["none"] * 3)
        self.assertEqual([by_id[k]["planning_outcome"] for k in ("A1", "K1", "O1")], ["in"] * 3)

    def test_ROW2_an_owner_step_that_stands_in_for_an_effect_needs_the_owners_ruling_cited(self):
        step = rowlib.owner_step("O1", mode="on his word")
        step["thing"]["stands_in_for"] = "connect the repository to the hosting project: a tool that cannot be split (OP-1)"
        found = admitted(step)
        self.assertEqual([(f["row"], f["entry"]) for f in found], [("O1", "thing")])
        step["thing"]["ruling"] = "the contract's A6, O2"
        self.assertEqual(admitted(step), [])

    def test_ROW3_D16_a_lanes_rows_are_admitted_only_with_its_checklist_answered(self):
        keep = rowlib.keep("P1")
        check = rowlib.check("K1")
        items = [{"item": "A2: the whole database is saved", "answered_by": {"row": "P1"}, "must": {"kind": "keep"}},
                 {"item": "F18: the not-saved list", "answered_by": {"form_line": "not saved"}},
                 {"item": "A4: a launch agent is unloaded and its file moved", "answered_by": {"reason": "not this lane's: sunrise loads none"}}]
        lane = rowlib.lane("sunrise", [keep, check], checklist=items)
        lane["form_changes"]["not saved"] = "not saved: {what}"
        self.assertEqual(rows.checklist_findings(lane), [])
        cases = {"unanswered": dict(items[0], answered_by={}),
                 "names a row that does not exist": dict(items[0], answered_by={"row": "P9"}),
                 "names a form line that does not exist": dict(items[1], answered_by={"form_line": "nowhere"}),
                 "D16: names a row that exists and does not answer it": dict(items[0], answered_by={"row": "K1"}),
                 "a reason left empty": dict(items[2], answered_by={"reason": ""})}
        for label, item in cases.items():
            with self.subTest(item=label):
                broken = dict(lane, checklist=[item])
                found = rows.checklist_findings(broken)
                self.assertEqual([f["item"] for f in found], [item["item"]])
        m = self.machine()
        rowlib.install(m, dict(lane, rows=[check], checklist=[cases["names a row that does not exist"]]))
        failed = m.look()
        self.assertEqual(failed.code, 4)
        self.assertIn("A2: the whole database is saved", failed.doc["findings"][0]["finding"])
        self.assertEqual(m.calls("fakehost"), [])


class Windows(harness.Case):
    """RISK-2, and OP-3's clause on a C5's listed conditions."""

    def test_RISK2_a_window_nobody_accepted_fails_the_build_and_names_the_row(self):
        unnamed = rowlib.refusing("H1", construction="C6")
        self.assertIn("a read-then-ask on a row RK3 does not name (RISK-2)", [f["finding"] for f in admitted(unnamed)])
        for named in rows.RK3_ROWS:
            self.assertEqual(admitted(rowlib.refusing(named, construction="C6")), [])
        table = rowlib.refusing("H2")
        table["construction"] = {"id": "read-then-replace", "command": "set"}
        self.assertEqual([(f["row"], f["entry"]) for f in admitted(table)], [("H2", "construction")])
        loose = rowlib.cas("G1")
        loose["before_test"].append({"id": "other", "read": "path", "path": rowlib.DEV, "is": "dir", "on": "other"})
        found = admitted(loose)
        self.assertTrue(any("does not enforce (RISK-2)" in f["finding"] and f["row"] == "G1" for f in found), found)
        loose["before_test"][-1]["enforced"] = "in the same request"
        self.assertEqual(admitted(loose), [])
        cited = rowlib.refusing("H3")
        cited["before_test"].append({"id": "also", "read": "path", "path": rowlib.DEV, "is": "dir", "on": "other"})
        self.assertTrue(admitted(cited))
        cited["construction"]["conditions"] = ["was", "also"]
        self.assertEqual(admitted(cited), [])
        unmarked = rowlib.swap_add("S1")
        unmarked["construction"]["risks"] = ["RK2", "RK13"]    # a shortcut's name in its before-test, and no RK5
        self.assertIn("its construction's window is carried under no accepted risk (RISK-2)", [f["finding"] for f in admitted(unmarked)])
        # RISK-1 (A63): "RK13's window is the one RK5's is, between the check and the add, so a shortcut's add and its
        # put-back are carried under both": a shortcut's add that names RK5 and not RK13 fails the build the same way
        no_rk13 = rowlib.swap_add("S1")
        no_rk13["construction"]["risks"] = ["RK2", "RK5"]
        self.assertIn("its construction's window is carried under no accepted risk (RISK-2)", [f["finding"] for f in admitted(no_rk13)])
        # and RK13 on a row with no shortcut's name is an accepted risk that does not cover its construction
        stray = rowlib.cas("G1")
        stray["construction"]["risks"] = ["RK13"]
        self.assertIn("an accepted risk that does not cover its construction", [f["finding"] for f in admitted(stray)])
        for row in rowlib.clean_rows():
            self.assertEqual(admitted(row), [], row["id"])

    def test_OP3_a_C5_whose_listed_conditions_do_not_cover_its_whole_before_test_fails_the_build(self):
        partial = rowlib.refusing("H1")
        partial["before_test"].append({"id": "more", "read": "command", "command": "look", "result": "success"})
        found = admitted(partial)
        self.assertEqual([f["finding"] for f in found], ["the cited refusal does not cover the whole before-test (RISK-2)"])
        uncited = rowlib.refusing("H1")
        del uncited["construction"]["document"]
        self.assertIn("no document is cited", [f["finding"] for f in admitted(uncited)])


class ThroughTheCommandLine(harness.Case):
    def failed(self, lane_rows, providers=None, reads_allowed=False, **files):
        m = self.machine("m%d" % len(os.listdir(self.tmp)), "m%d" % len(os.listdir(self.tmp)))
        rowlib.install(m, rowlib.lane("sunrise", lane_rows), providers=providers)
        for rel, text in files.items():
            m.put(rel, text)
        result = m.look()
        self.assertEqual(result.code, 4, result.text)
        self.assertEqual(result.ending, "refused")
        started = [c for tool in ("fakehost", "fakegit", "fakedump", "fakescaffold") for c in m.calls(tool) if c["changing"] or not reads_allowed]
        self.assertEqual(started, [], "a child was started for a manifest whose build failed")
        self.assertEqual([n for n in os.listdir(m.facts.run_dir(m.run_ids()[0])) if n.startswith("manifest")], [])
        return result.doc["findings"]

    def test_SEC3_four_templates_that_put_a_held_or_a_secret_field_into_an_argument_or_an_environment_value_fail_the_build(self):
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["get-env"] = dict(providers["fakehost"]["commands"]["get"],
                                                            env={"FAKEHOST_THING": {"class": "fixed", "param": "thing"}})
        for label, mark, command, param in (("a held field in an argument", {"held": "id"}, "fakehost.get", "name"),
                                            ("a held field in a registered environment value", {"held": "id"}, "fakehost.get-env", "thing"),
                                            ("a secret field in an argument", {"secret": "token"}, "fakehost.get", "name"),
                                            ("a secret field in a registered environment value", {"secret": "token"}, "fakehost.get-env", "thing")):
            with self.subTest(template=label):
                maker = rowlib.create("C1")
                maker["output"]["fields"]["id"] = mark
                user = rowlib.check("K9", needs=[{"output": "remote", "level": "made", "treatment": "then not applicable"}])
                params = {"name": rowlib.NAME, param: {"output": "remote.id"}}
                user["commands"] = [rowlib.use("probe", command, **params)]
                user["thing"]["passes"] = [{"read": "command", "command": "probe", "result": "success"}]
                findings = self.failed([maker, user], providers)
                self.assertEqual([f["row"] for f in findings], ["K9"])
                self.assertIn("SEC-3", findings[0]["finding"])
                self.assertIn("an environment value" if "environment" in label else "an argument", findings[0]["finding"])

    def test_SEC3_a_module_that_registers_PATH_or_another_name_that_chooses_which_program_or_code_runs_as_passed_fails_the_build(self):
        """SEC-3's test line: "a module that registers `PATH`, or another name that chooses which program or which code
        a child runs, as passed fails the manifest build"."""
        for name in ("PATH", "DYLD_INSERT_LIBRARIES", "PYTHONPATH", "GIT_EXEC_PATH", "NODE_OPTIONS"):
            with self.subTest(passed=name):
                providers = rowlib.providers()
                providers["fakehost"]["commands"]["say"] = dict(providers["fakehost"]["commands"]["say"],
                                                                env={name: {"class": "passed", "reason": "a fixture's reason"}})
                findings = self.failed([rowlib.says("Y1")], providers)
                self.assertEqual([f["row"] for f in findings], ["Y1"])
                self.assertIn("chooses which program or which code a child runs (SEC-3)", findings[0]["finding"])
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["say"] = dict(providers["fakehost"]["commands"]["say"],
                                                        env={"FAKEHOST_REGION": {"class": "passed", "reason": "a fixture's reason"}})
        m = self.machine("ok-passed", "ok-passed")
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1")]), providers=providers)
        self.assertEqual(m.look().ending, "preview", "a passed name that chooses nothing was refused")

    def test_SEC3_the_same_held_field_as_a_protected_input_builds_and_reaches_the_fake_as_a_path_to_an_owner_only_file(self):
        m = self.machine()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.create("C1")]))
        seen = {}

        def watch(event):
            if event["stage"] == "pre" and event["op"] == "child" and "--id-file" in event.get("argv", []):
                path = event["argv"][event["argv"].index("--id-file") + 1]
                seen["path"], seen["mode"], seen["content"] = path, os.stat(path).st_mode & 0o777, open(path).read()
            return False
        looked = m.look()
        went = m.go(looked, kill=watch)
        self.assertEqual(went.ending, "complete", went.text)
        issued = [i["value"] for i in m.fake("fakehost", "issued.jsonl")]
        self.assertEqual(seen["content"], issued[0])
        self.assertEqual(seen["mode"], 0o600)
        # SEC-3's protected-input row (batch 20): "That file is made in the run directory's protected folder, the place SEC-7
        # gives the record it is made from"
        self.assertTrue(seen["path"].startswith(os.path.join(m.facts.run_dir(looked.doc["run"]), "protected") + os.sep),
                        "the file is not in the run directory's protected folder: %s" % seen["path"])
        self.assertFalse(os.path.exists(seen["path"]), "the file handed over was left behind")
        # LOG-3's test line: "a file made to hand a protected input to a fake child lies under the run directory and, where it
        # is removed, is removed only after that child has ended"
        events = went.events
        ended = [e["i"] for e in events if e["op"] == "child" and e["stage"] == "post"]
        removed = [e["i"] for e in events if e["stage"] == "pre" and e["op"] == "remove" and e["subject"] == seen["path"]]
        started = [e["i"] for e in events if e["op"] == "child" and e["stage"] == "pre" and seen["path"] in e.get("argv", [])]
        self.assertEqual(len(removed), 1)
        self.assertTrue(started and [i for i in ended if started[0] < i < removed[0]], "removed before its child had ended")
        for call in m.calls("fakehost"):
            self.assertNotIn(issued[0], json.dumps(call["argv"]) + json.dumps(call["env_values"]))
        self.assertNowhere(issued[0], went)

    def test_SEC3_LOG3_a_kill_after_the_protected_input_is_made_and_before_the_child_ends_leaves_it_in_the_protected_folder(self):
        """SEC-3's test line (batch 20): "that file lies in the run directory's protected folder, and a kill after it is made
        and before the fake ends leaves it there, owner-only, the next invocation passing RUN-4's checks and SEC-11's scan
        finding its content at no place but SEC-7's". LOG-3: "the run may remove it once its child has ended", and a kill
        that leaves it is no removal of the tool's."""
        import scan
        m = self.machine()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.create("C1")]))
        seen = {}

        def at_child(event):
            if event["stage"] == "mid" and event["op"] == "child" and not seen:
                handed = [e for e in m.recorder.events if e["op"] == "child" and e["stage"] == "pre" and "--id-file" in e.get("argv", [])]
                if handed and handed[-1]["i"] == event["i"] - 1:
                    seen["path"] = handed[-1]["argv"][handed[-1]["argv"].index("--id-file") + 1]
                    return True
            return False
        looked = m.look()
        went = m.go(looked, kill=at_child)
        self.assertTrue(went.killed, went.text)
        run_dir = m.facts.run_dir(looked.doc["run"])
        self.assertTrue(seen["path"].startswith(os.path.join(run_dir, "protected") + os.sep), seen["path"])
        self.assertTrue(os.path.isfile(seen["path"]), "the kill did not leave the file")
        self.assertEqual(os.stat(seen["path"]).st_mode & 0o777, 0o600)
        issued = [i["value"] for i in m.fake("fakehost", "issued.jsonl")]
        status = m.summon("status")
        self.assertNotIn(status.ending, ("refused", None), status.text)
        self.assertNotEqual((status.lines or [""])[0], texts.RUNDIR_STOP["permissions"], "the next invocation failed RUN-4's checks")
        self.assertEqual(scan.scan(m, [(issued[0], [])], (looked, went, status)), [], "the content is at a place SEC-7 does not give")
        holding = []
        for base, _dirs, files in os.walk(m.home):
            for name in files:
                path = os.path.join(base, name)
                if os.path.relpath(path, m.home).split(os.sep)[0] == ".fakes":
                    continue                  # the provider's side
                if issued[0].encode() in open(path, "rb").read():
                    holding.append(path)
        self.assertTrue(holding)
        for path in holding:
            self.assertTrue(path.startswith(os.path.join(run_dir, "protected") + os.sep), "its content rests outside the protected folder: %s" % path)

    def test_SEC8_a_tool_that_can_only_write_in_place_or_has_a_second_secret_writing_side_effect_is_never_started(self):
        pull = rowlib.build("B1")
        pull["construction"] = {"id": "C1", "builder": "pull", "out_param": "out", "single_file": True, "mode": 0o600}
        pull["commands"] = [rowlib.use("pull", "fakehost.write")]
        place = pull["thing"]["place"]
        pull["after_test"] = [{"read": "path", "path": place, "is": "file"}]
        pull["after_check"] = [{"read": "path", "path": place, "is": "file"}, {"read": "mode", "path": place, "at_most": 0o600}]
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["write"]["secret_output"] = "in place"
        self.assertIn("SEC-8", self.failed([pull], providers)[0]["finding"])
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["write"]["side_effects"] = [{"what": "also writes its own cache of the values", "secret_writing": True}]
        self.assertIn("a secret-writing side effect that cannot be turned off (SEC-8)", self.failed([pull], providers)[0]["finding"])
        ok = self.machine("ok", "ok")
        rowlib.install(ok, rowlib.lane("sunrise", [pull]))
        looked, went = ok.started()
        self.assertEqual(went.ending, "complete", went.text)
        target = os.path.join(ok.dev, "demo")
        self.assertEqual(os.stat(target).st_mode & 0o777, 0o600)
        self.assertEqual(len(open(target).read().splitlines()), 2, "the env file is not complete")
        out_arg = [c["argv"][c["argv"].index("--out") + 1] for c in ok.calls("fakehost", "write")][0]
        self.assertTrue(out_arg.startswith(os.path.join(ok.facts.run_dir(looked.doc["run"]), "staging") + os.sep), "the tool was not pointed at staging")

    def test_OP1_D16_a_command_that_does_more_than_one_thing_with_the_rest_not_turned_off_is_not_run(self):
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["set-if"]["effects"] = 2
        self.assertIn("OP-1", self.failed([rowlib.refusing("H1")], providers)[0]["finding"])
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["set-if"]["side_effects"] = [{"what": "also links the repository"}]
        self.assertIn("OP-1", self.failed([rowlib.refusing("H1")], providers)[0]["finding"])
        providers["fakehost"]["commands"]["set-if"]["side_effects"] = [{"what": "also links the repository", "turned_off_by": ["--no-link"]}]
        self.assertEqual(admitted(rowlib.refusing("H1"), providers), [])

    def test_SEC12_a_row_that_puts_a_command_with_a_secret_field_into_a_look_fails_its_build(self):
        row = rowlib.create("C1")
        row["commands"].append(rowlib.use("peek", "fakehost.issue"))
        row["planning_test"] = [{"read": "command", "command": "peek", "result": "success"}]
        findings = self.failed([row])
        self.assertIn("a command with a secret field in a look (SEC-12)", [f["finding"] for f in findings])

    # ---- a secret's alphabet (the owner's ruling on PS46, A142) -------------------------------------------------------
    # His pick: "Bar them from a secret's alphabet (Recommended)": "A provider whose secret field allows a space, a line
    # break, a control character or an invisible mark fails when its plan is built. The invisible marks are the zero-width
    # and direction marks. The tool names the provider." As A142 records it: "A declaration whose secret field's registered
    # alphabet admits any white space, any control character or any format character fails its manifest build, and the
    # row is named." An alphabet is written as a declaration writes it: the inside of a character class, as the field's
    # validator reads it (`results._valid`: `^[<alphabet>]+$`), a character itself or an escape of the class.
    BARRED_ALPHABETS = (
        ("a space", "a-z0-9 "),
        ("a line break", "a-z0-9\n"),
        ("a line break written as its escape", "a-z0-9\\n"),
        ("a tab", "a-z0-9\t"),
        ("a tab written as its escape", "a-z0-9\\t"),
        ("a zero-width space", "a-z0-9​"),
        ("a zero-width space written as its escape", "a-z0-9\\u200b"),
        ("a direction mark, left-to-right", "a-z0-9‎"),
        ("a direction mark, right-to-left override", "a-z0-9‮"),
        ("the line separator", "a-z0-9 "),
        ("the paragraph separator", "a-z0-9 "),
        ("a no-break space", "a-z0-9 "),
        ("a control character", "a-z0-9\x07"),
        ("the class of white space", "a-z0-9\\s"),
        ("a range that reaches the control characters", "\\x00-\\x7f"),
        ("a class that admits all but some", "^a-z"),
    )

    def secret_alphabet(self, alphabet):
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["issue"]["fields"][0]["alphabet"] = alphabet
        return providers

    def assert_alphabet_finding(self, findings, where):
        self.assertEqual([f["row"] for f in findings], ["X1"], "%s: the build did not fail naming the row alone: %s" % (where, findings))
        self.assertEqual(findings[0]["entry"], "commands")
        words = findings[0]["finding"]
        self.assertIn("A142", words, where)
        self.assertIn("provider fakehost", words, "%s: the finding does not name the provider" % where)

    def test_SEC4_A142_a_secret_fields_alphabet_that_admits_white_space_a_control_or_a_format_character_fails_the_build(self):
        """Each barred alphabet: the row's admission names the row, and a first look over it, through the command line,
        ends `refused` with exit 4 and that finding, no child started and no manifest written."""
        for index, (label, alphabet) in enumerate(self.BARRED_ALPHABETS):
            with self.subTest(alphabet=label):
                providers = self.secret_alphabet(alphabet)
                self.assert_alphabet_finding(admitted(rowlib.secret_op("X1"), providers), label)
                findings = self.failed([rowlib.secret_op("X1")], providers)
                self.assert_alphabet_finding(findings, label)

    def test_SEC4_A142_the_secret_field_of_a_second_command_and_a_second_secret_field_are_each_checked(self):
        """The check is of every secret field of every command the row declares: the create's send with a second secret
        field (`secret_send_providers`), its alphabet given a space, fails the build naming the create's row."""
        providers = rowlib.secret_send_providers()
        fields = providers["fakehost"]["commands"]["create"]["fields"]
        [token] = [f for f in fields if f["disposition"] == "secret"]
        token["alphabet"] = "a-z0-9 "
        found = admitted(rowlib.create_looked_by_request("C1"), providers)
        self.assertEqual([f["row"] for f in found], ["C1"], found)
        self.assertIn("provider fakehost", found[0]["finding"])
        self.assertIn("A142", found[0]["finding"])

    def test_SEC4_A142_the_shipped_declarations_whose_secret_fields_declare_a_z0_9_build_as_before(self):
        """The 15 secret fields of the plugin's shipped files outside its tests all declare `a-z0-9` (A139): each is read
        from its file here, and a row over the fixture providers with that alphabet builds. The fixtures' own secret fields,
        and a held name field whose alphabet holds a space (spaces stay allowed outside a secret), build as before."""
        found = []
        for base, _dirs, files in os.walk(harness.PLUGIN):
            if os.sep + "tests" in base:
                continue
            for name in sorted(files):
                if not name.endswith(".json"):
                    continue
                with open(os.path.join(base, name), "rb") as fh:
                    try:
                        doc = json.loads(fh.read().decode("utf-8"))
                    except ValueError:
                        continue
                stack = [doc]
                while stack:
                    node = stack.pop()
                    if isinstance(node, dict):
                        if node.get("disposition") == "secret":
                            found.append(node.get("alphabet"))
                        stack.extend(node.values())
                    elif isinstance(node, list):
                        stack.extend(node)
        self.assertEqual(found, ["a-z0-9"] * 15)
        for alphabet in sorted(set(found)):
            self.assertEqual(admitted(rowlib.secret_op("X1"), self.secret_alphabet(alphabet)), [])
        self.assertEqual(admitted(rowlib.secret_op("X1")), [])
        self.assertEqual(admitted(rowlib.create_looked_by_request("C1"), rowlib.secret_send_providers()), [])
        self.assertEqual(admitted(rowlib.create_sent_by_request("C1"), rowlib.secret_request_providers()), [])
        self.assertIn(" ", rowlib.NAMEF["alphabet"])
        self.assertEqual(admitted(rowlib.create("C1")), [], "a name field whose alphabet holds a space no longer builds")
        m = self.machine("a142-ok", "a142ok")
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.secret_op("X1")]))
        self.assertEqual(m.look().ending, "preview")

    def test_EV6_OP10_OP11_KEEP4_planted_rows_fail_the_build_naming_the_row(self):
        ordered = rowlib.swap_add("S1")
        ordered["span"] = {"placement": "at the end", "ordered": True}
        self.assertEqual([(f["row"], f["entry"]) for f in self.failed([ordered], None, **{"shortcuts.txt": "x\n"})], [("S1", "span")])
        adopting = rowlib.adopt("D1")
        adopting["output"]["name"] = "remote"
        self.assertIn("OP-10", self.failed([adopting])[0]["finding"])
        providers = rowlib.providers()
        providers["fakescaffold"]["commands"]["scaffold"]["repository_writes"] = "unlisted"
        built = rowlib.build("B1")
        built["construction"] = {"id": "C1", "builder": "scaffold", "out_param": "out"}
        built["commands"] = [rowlib.use("scaffold", "fakescaffold.scaffold")]
        self.assertIn("OP-11", self.failed([built], providers)[0]["finding"])
        keep = rowlib.keep("P1")
        over = rowlib.move("M1", target=keep["thing"]["place"])
        findings = self.failed([keep, over], None, True, **{"dev/demo.env": "DATABASE_URL=postgres://a:" + harness.canary("dbpass") + "@db.invalid/a\n", "dev/demo-scope.md": "x\n"})
        self.assertIn(("M1", "an effect that would write to, move or remove a keep's place (KEEP-4)"), [(f["row"], f["finding"]) for f in findings])


if __name__ == "__main__":
    unittest.main()
