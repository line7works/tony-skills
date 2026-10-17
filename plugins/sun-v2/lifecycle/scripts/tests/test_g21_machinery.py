"""Part G21: the last machinery the lanes' rows need, each item by its smallest mechanism (brief-30, section 2).

Every test's name carries the item's id (G21_n) and the frame's rule it rests on. The rows, the lanes and the provider
declarations here are fixtures under the tests, written with `rowlib`; none is a lane's row.
"""
import copy
import json
import os
import subprocess

import harness
import rowlib
from test_g19_machinery import checking, provs

L = rowlib.lit
RK18_FORMS = {"form_changes": dict(rowlib.FORM_CHANGES, **{"the RK18 mark": "carried under v1's own risk for this step (RK18): {what}"})}


def manifest_of(m, run_id, number=1):
    with open(os.path.join(m.facts.run_dir(run_id), "manifest-%d.json" % number)) as fh:
        return json.load(fh)


def op_of(manifest, op):
    return [o for o in manifest["operations"] if o["id"] == op][0]


def manifests(m, run_id):
    return [n for n in os.listdir(m.facts.run_dir(run_id)) if n.startswith("manifest")]


class Rise(harness.Case):
    def looked(self, m, rows, lane_more=None, providers=None, inputs=None):
        rowlib.install(m, rowlib.lane("sunrise", rows, **(lane_more or {})), providers=providers or provs())
        return m.look(inputs=inputs)

    def ran(self, m, rows, lane_more=None, providers=None, inputs=None, ending="complete"):
        looked = self.looked(m, rows, lane_more, providers, inputs)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked)
        if ending is not None:
            self.assertEqual(went.ending, ending, went.text)
        return looked, went

    # ---- G21-1 (M-1). A lane table keyed by a fact (RUN-6) -----------------------------------------------------------
    def test_G21_1_RUN6_a_value_chosen_from_the_lanes_own_table_by_a_planning_fact_the_look_settled(self):
        tables = {"scaffold output": {"web app": L(".next/BUILD_ID"), "static site": L("dist/index.html")}}
        pick = {"table": {"name": "scaffold output", "by": "flags.scaffold"}}
        for word, want in (("web app", ".next/BUILD_ID"), ("static site", "dist/index.html")):
            with self.subTest(word=word):
                m = self.machine("t" + word[:3], "t" + word[:3])
                y = rowlib.says("Y1", words={"text": [L("built "), pick]})
                k = rowlib.says("Y2", words=rowlib.path(rowlib.DEV, pick))
                looked = self.looked(m, [y, k], {"tables": copy.deepcopy(tables)}, inputs=m.inputs(flags={"scaffold": word}))
                self.assertEqual(looked.ending, "preview", looked.text)
                manifest = manifest_of(m, looked.doc["run"])
                self.assertEqual(op_of(manifest, "Y1")["commands"][0]["params"]["words"], L("built " + want))
                self.assertEqual(op_of(manifest, "Y2")["commands"][0]["params"]["words"], L(os.path.join(m.dev, want)))
        # a fact the table holds no entry for: a value the look cannot settle, and no manifest
        m = self.machine("tno", "tno")
        looked = self.looked(m, [rowlib.says("Y1", words=pick)], {"tables": copy.deepcopy(tables)},
                             inputs=m.inputs(flags={"scaffold": "desktop app"}))
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("a value the look cannot settle", looked.text)

    # ---- G21-2 (M-2). The destination read first: "already adopted" (OP-6, EV-1) -------------------------------------
    STAGED = {"name": "staged.scope", "read": "files", "folder": rowlib.path(rowlib.DEV, "staged"), "glob": "demo-scope*.md",
              "date": True, "choose": True, "validators": {"name": "one line of plain words"},
              "adopted": {"folder": rowlib.path(rowlib.DEV, rowlib.NAME, "docs", "scope"), "glob": "*-demo.md"}}

    def staged_look(self, label, destination):
        m = self.machine(label, label)
        for name, text in (("demo-scope-a.md", "2026-09-01: a\n"), ("demo-scope-b.md", "2026-09-02: b\n")):
            m.put("dev/staged/" + name, text)
        if destination:
            m.put("dev/demo/docs/scope/2026-08-30-demo.md", "2026-08-30: adopted before\n")
        y = rowlib.says("Y1", words={"text": [{"fact": "staged.scope.path"}]},
                        condition={"on": "fact", "fact": "staged.scope.found", "equals": True, "reason": "nothing staged"})
        return m, self.looked(m, [y], {"facts": [copy.deepcopy(self.STAGED)]})

    def test_G21_2_OP6_EV1_a_document_already_at_its_destination_is_already_adopted_and_its_staged_source_not_looked_for(self):
        m, looked = self.staged_look("a1", True)
        self.assertEqual(looked.ending, "preview", looked.text)
        na = manifest_of(m, looked.doc["run"])["not_applicable"]
        self.assertEqual([(n["row"], n["reason"]) for n in na],
                         [("Y1", "already adopted: " + m.path("dev", "demo", "docs", "scope", "2026-08-30-demo.md"))])
        self.assertNotIn("Several staged documents", looked.text)
        # with nothing at the destination, the staged source is read as before (G20-7): two match, and the look asks
        m, looked = self.staged_look("a2", False)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("Several staged documents match for staged.scope", looked.text)

    # ---- G21-3 (M-4). The `ref` read with `equals` and as an output field; RK18 on a C1 row (A151) ---------------------
    def test_G21_3_SEC4_the_ref_read_equals_a_commit_bound_as_an_output_field(self):
        m = self.machine()
        repo = m.path("dev", "demo")
        os.makedirs(repo)

        def git(*a):
            return subprocess.run(["/usr/bin/git", "-C", repo, "-c", "user.email=f@x.invalid", "-c", "user.name=f"] + list(a),
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout.decode().strip()
        git("init", "-q", "--initial-branch", "main")
        m.put("dev/demo/notes.txt", "")
        git("add", "--all")
        git("commit", "-q", "-m", "one")
        where = rowlib.path(rowlib.DEV, rowlib.NAME)
        s = rowlib.swap_add("S1", file=rowlib.path(rowlib.DEV, rowlib.NAME, "notes.txt"), line=L("one note"), output="head")
        s["before_test"] = s["before_test"][:1]
        s["construction"]["risks"] = ["RK2"]
        s["output"] = {"name": "head", "fields": {"commit": {"observed": "commit"}}}
        s["thing"]["commit_of"] = {"repo": where, "ref": "main"}
        k = checking("K2", [{"read": "ref", "repo": where, "ref": "main", "equals": {"output": "head.commit"}}],
                     needs=[{"output": "head", "level": "state", "treatment": "then not applicable"}])
        looked, went = self.ran(m, [s, k])
        self.assertEqual(m.statuses(looked.doc["run"])["K2"], "passed")

    def test_G21_3_RISK2_A151_RK18_on_a_C1_row_admits_its_condition_on_another_file_read_just_before_the_effect(self):
        m = self.machine()
        b = rowlib.build("B1")
        b["construction"].update(risks=["RK18"], risk_line="a file made beside it between the read and the publish is not seen")
        b["before_test"].append({"id": "other", "on": "other", "read": "path", "path": rowlib.path(rowlib.DEV, "elsewhere.txt"), "is": "absent"})
        looked, went = self.ran(m, [b], copy.deepcopy(RK18_FORMS))
        self.assertTrue(os.path.isdir(m.path("dev", "demo")))
        # the same condition on a C1 row that carries no RK18 stays closed (RISK-2)
        m2 = self.machine("n2", "n2")
        b2 = rowlib.build("B1")
        b2["before_test"].append({"id": "other", "on": "other", "read": "path", "path": rowlib.path(rowlib.DEV, "elsewhere.txt"), "is": "absent"})
        looked2 = self.looked(m2, [b2])
        self.assertEqual(looked2.ending, "refused", looked2.text)
        self.assertIn("which the construction does not enforce (RISK-2)", looked2.text)

    # ---- G21-4 (M-6, R7, A153). C1 runs the build's program in an empty staged folder; its `.git` is never published -----
    def test_G21_4_SEC7_A153_C1_runs_the_builder_in_an_empty_staged_folder_and_publishes_no_git_it_made_there(self):
        m = self.machine()
        b = rowlib.build("B1")
        b["construction"] = {"id": "C1", "builder": "scaffold", "out_param": "out", "in_folder": True, "mode": 0o755,
                             "risks": ["RK18"], "risk_line": "a scaffolder that writes a secret publishes it as it stands"}
        b["after_check"] = [{"read": "path", "path": rowlib.path(rowlib.DEV, rowlib.NAME, "README.md"), "is": "file"}]
        b["commands"] = [rowlib.use("scaffold", "fakescaffold.scaffold")]
        rowlib.install(m, rowlib.lane("sunrise", [b], **copy.deepcopy(RK18_FORMS)), providers=provs())
        m.plan_fake("fakescaffold", {"command": "scaffold", "dot_git": True})
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        call = [c for c in m.calls("fakescaffold") if c["argv"][:1] == ["scaffold"]][0]
        staged = os.path.join(m.facts.run_dir(looked.doc["run"]), "staging", "B1", "object")
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(staged))
        made = []
        for base, dirs, files in os.walk(m.path("dev", "demo")):
            made += [os.path.relpath(os.path.join(base, n), m.path("dev", "demo")) for n in dirs + files]
        self.assertEqual(sorted(made), ["README.md", "src", os.path.join("src", "main.txt")])

    # ---- G21-5 (M-7). A read of one line at a given line number --------------------------------------------------------
    def test_G21_5_RUN6_a_read_of_one_line_at_a_given_line_number_of_a_file(self):
        for number, status in ((1, "passed"), (2, None)):
            with self.subTest(number=number):
                m = self.machine("l%d" % number, "l%d" % number)
                m.put("dev/CLAUDE.md", "@AGENTS.md\nmore\n")
                k = checking("K1", [{"read": "line", "path": rowlib.path(rowlib.DEV, "CLAUDE.md"), "line": L("@AGENTS.md"), "number": number}])
                looked, went = self.ran(m, [k], ending=None)
                got = m.statuses(looked.doc["run"]).get("K1")
                if status:
                    self.assertEqual(got, status, went.text)
                else:
                    self.assertNotEqual(got, "passed", went.text)

    # ---- G21-6 (M-8, R8). A validator on each value filled into a row's text, refusing the input in the look -----------
    def test_G21_6_SEC9_R8_each_value_filled_into_a_rows_text_is_checked_and_a_failing_one_refuses_the_input_in_the_look(self):
        shortcut = {"checked": {"value": {"input": "answers.shortcut"}, "validator": "a shortcut's name"}}
        folder = {"checked": {"value": {"output": "project folder.path"}, "validator": "a path a shell line may hold"}}
        line = {"text": [L("alias "), shortcut, L("=\"cd "), folder, L("\"")]}
        cases = (("ok", "dm", "my-proj", "preview"), ("badcut", "Bad!", "my-proj", "refused"), ("badpath", "dm", "my$proj", "refused"))
        for label, answer, name, ending in cases:
            with self.subTest(label=label):
                m = self.machine(label, label)
                os.makedirs(m.path("dev", name))
                y = rowlib.says("Y1", words=line, needs=[{"output": "project folder", "level": "state", "treatment": "then not applicable"}])
                y["content_classes"]["validators"] = ["a shortcut's name", "a path a shell line may hold"]
                looked = self.looked(m, [rowlib.adopt("D1"), y],
                                     inputs=m.inputs(answers={"shortcut": answer}, adopt={"project folder": m.path("dev", name)}))
                self.assertEqual(looked.ending, ending, looked.text)
                if ending == "refused":
                    self.assertIn("A value filled into row Y1 fails its check", looked.text)
                    self.assertEqual(manifests(m, looked.doc["run"]), [])
                    continue
                went = m.go(looked)
                self.assertEqual(went.ending, "complete", went.text)
                self.assertIn('alias dm="cd %s"' % m.path("dev", name), m.calls("fakehost", "noop")[-1]["argv"])

    # ---- G21-7 (M-10). A check's pass dropped with the need it names, settled `then not needed` (ORD-1, ORD-2) ---------
    def test_G21_7_ORD2_a_checks_pass_is_dropped_with_the_need_it_names_where_that_need_is_settled_then_not_needed(self):
        m = self.machine()
        k = checking("K1", [{"read": "path", "path": rowlib.DEV, "is": "dir"},
                            {"read": "path", "path": {"output": "pushed.path"}, "is": "file"}],
                     needs=[{"output": "pushed", "level": "made", "treatment": "then not needed"}])
        looked, went = self.ran(m, [k])
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual(op_of(manifest, "K1")["thing"]["passes"], [{"read": "path", "path": L(m.dev), "is": "dir"}])
        self.assertEqual([(s["operation"], s["need"]) for s in manifest["settled_needs"]], [("K1", "pushed")])
        self.assertEqual(m.statuses(looked.doc["run"])["K1"], "passed")


# ---- Group B: slice 4's rows (rows-set section 8, items 11 to 15) ------------------------------------------------------
class Set(harness.Case):
    def ran(self, m, rows, providers=None, lane_more=None, ending="complete", inputs=None):
        rowlib.install(m, rowlib.lane("sunrise", rows, **(lane_more or {})), providers=providers or provs())
        looked = m.look(inputs=inputs)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked)
        if ending is not None:
            self.assertEqual(went.ending, ending, went.text)
        return looked, went

    # ---- G21-8 (item 11, S9). A C6 command's protected input made from a computed text (SEC-3) -----------------------
    def test_G21_8_SEC3_a_C6_commands_protected_input_made_from_a_computed_text_written_owner_only_and_handed_by_its_slot(self):
        m = self.machine()
        canary = harness.canary("cron")
        table = "0 1 * * * keep %s\n5 * * * * /x/demo/run\n10 * * * * other\n" % canary
        m.plan_fake("fakehost", {"command": "noop", "do": "raw", "text": table})
        providers = provs()
        providers["fakehost"]["commands"]["take"] = rowlib._command(
            "fakehost", rowlib._t("take", "--file", {"slot": "table"}), [], effects=1,
            protected_inputs=[{"slot": "table", "accepts": "after-image"}])
        t = rowlib.row("change", "T1", "one",
                       thing={"role": "the account's table", "identity": "named value", "before_word": "listed", "after_word": "taken out"},
                       planning_test=[{"read": "command", "command": "listing", "result": "success"}],
                       before_test=[{"id": "there", "read": "text", "command": "listing", "text": L("/x/demo"), "present": True}],
                       after_test=[{"read": "text", "command": "listing", "text": L("/x/demo"), "present": False}],
                       construction={"id": "C6", "command": "take", "risks": ["RK18"], "risk_line": "a line written in between is lost",
                                     "computed": {"param": "table", "from": {"command": "listing"},
                                                  "edit": {"kind": "remove-line", "holding": L("/x/demo")},
                                                  "type": "after-image", "label": "the table after"}},
                       commands=[rowlib.use("listing", "fakehost.listing"), rowlib.use("take", "fakehost.take")],
                       after_check=[{"read": "path", "path": L(os.path.join(m.home, ".fakes", "fakehost", "taken.jsonl")), "is": "file"}],
                       way_back={"none": "the row declares none"})
        looked, went = self.ran(m, [t], providers, copy.deepcopy(RK18_FORMS))
        taken = m.fake("fakehost", "taken.jsonl")
        self.assertEqual([(s["text"], s["mode"]) for s in taken], [(table.replace("5 * * * * /x/demo/run\n", ""), "0o600")])
        self.assertTrue(taken[0]["file"].startswith(os.path.join(m.facts.run_dir(looked.doc["run"]), "protected")), taken[0]["file"])
        self.assertNowhere(canary, went)

    # ---- G21-9 (item 12, S7). A family instance's outputs and needs carry its item's index n ---------------------------
    def test_G21_9_ORD1_a_family_instances_outputs_and_needs_carry_its_items_index_and_a_reverse_keeps_its_forward_rows(self):
        m = self.machine()
        for name in ("a.plist", "b.plist"):
            m.put("dev/agents/" + name, "<plist>demo</plist>\n")
        os.makedirs(m.path("dev", "archive"))
        family = {"read": "files", "folder": rowlib.path(rowlib.DEV, "agents"), "glob": "*.plist", "holding": rowlib.NAME,
                  "validators": {"name": "a launch agent's label"}}
        u = checking("U1", [{"read": "path", "path": {"each": "path"}, "is": "file"}], output={"name": "unloaded {each.n}", "fields": {}})
        u["thing"]["family"] = copy.deepcopy(family)
        a = rowlib.move("A1", source={"each": "path"}, target=rowlib.path(rowlib.DEV, "archive", {"each": "name"}), output="archived {each.n}",
                        needs=[{"output": "unloaded {each.n}", "level": "state", "treatment": "then not applicable"}])
        a["thing"]["family"] = copy.deepcopy(family)
        a["way_back"]["reverse"]["output"] = {"name": "back {each.n}", "fields": {}}
        rowlib.install(m, rowlib.lane("sunrise", [u, a]), providers=provs())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = manifest_of(m, looked.doc["run"])
        for n in (1, 2):
            self.assertEqual(op_of(manifest, "U1-%d" % n)["output"]["name"], "unloaded %d" % n)
            moved = op_of(manifest, "A1-%d" % n)
            self.assertEqual(moved["output"]["name"], "archived %d" % n)
            self.assertEqual([x["output"] for x in moved["needs"]], ["unloaded %d" % n])
            self.assertEqual(moved["way_back"]["reverse"]["output"]["name"], "back %d" % n)

    # ---- G21-10 (item 13, S1). A keep of a folder of this machine copied whole; `project_memory` (KEEP-1, E16-12) -------
    def test_G21_10_KEEP1_E16_12_a_folder_of_this_machine_copied_whole_on_its_names_and_fingerprints_read_before_and_after(self):
        import re
        from sun_core import effects, fsio, protected
        m = self.machine()
        m.settings["locations"]["memory_projects"] = m.path("mem")
        m.write_settings()
        store = os.path.join(m.path("mem"), re.sub(r"[^A-Za-z0-9]", "-", m.path("dev", "demo")), "memory")
        m.put(os.path.relpath(os.path.join(store, "MEMORY.md"), m.home), "# memory\n")
        m.put(os.path.relpath(os.path.join(store, "notes", "one.md"), m.home), "one\n")
        place = rowlib.path(rowlib.DEV, "demo-memory")
        k = rowlib.row("keep", "K1", "one",
                       thing={"role": "the copy of the project's memory store", "identity": "path", "place": place,
                              "tracked": ["exists", "identity"]},
                       planning_test=[{"read": "path", "path": place, "is": "absent"}],
                       before_test=[{"id": "free", "read": "path", "path": place, "is": "absent"}],
                       after_test=[{"read": "path", "path": place, "is": "dir"}],
                       construction={"id": "C1", "copy_folder": {"project_memory": rowlib.path(rowlib.DEV, rowlib.NAME)}, "mode": 0o700,
                                     "risks": ["RK18"], "risk_line": "a note changed and changed back while it is copied is not seen"},
                       after_check=[{"read": "path", "path": place, "is": "dir"}],
                       keep_scope={"scope": "every file of the store", "same_state": "names and fingerprints read before and after",
                                   "content_checks": []},
                       content_classes={"reads": ["protected"], "stores": ["protected"], "shows": ["safe"], "validators": [], "resting_places": ["the sunset folder"]},
                       output={"name": "memory copy", "fields": {"path": place}})
        looked, went = self.ran(m, [k], lane_more=copy.deepcopy(RK18_FORMS))
        copied = m.path("dev", "demo-memory")
        self.assertEqual(open(os.path.join(copied, "notes", "one.md")).read(), "one\n")
        self.assertEqual(os.stat(copied).st_mode & 0o777, 0o700)
        run_dir = m.facts.run_dir(looked.doc["run"])
        done = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion" and r["op"] == "K1"][0]
        listing = [["MEMORY.md", fsio.sha256_hex(b"# memory\n")], [os.path.join("notes", "one.md"), fsio.sha256_hex(b"one\n")]]
        self.assertEqual(json.loads(protected.read(fsio.FS(), run_dir, done["keep"]["inventory"]).decode("utf-8")), listing)
        self.assertEqual(done["keep"]["sha256"], fsio.sha256_hex(fsio.canonical_json(listing).encode("utf-8")))
        # a note changed during the copy fails the keep, and nothing is published (KEEP-1)
        m2 = self.machine("k2", "k2")
        m2.settings["locations"]["memory_projects"] = m2.path("mem")
        m2.write_settings()
        store2 = os.path.join(m2.path("mem"), re.sub(r"[^A-Za-z0-9]", "-", m2.path("dev", "demo")), "memory")
        m2.put(os.path.relpath(os.path.join(store2, "MEMORY.md"), m2.home), "# memory\n")
        real = effects.folder_listing

        def changing(engine, folder, op=None):
            out = real(engine, folder, op)
            if folder == store2:
                with open(os.path.join(store2, "MEMORY.md"), "a") as fh:
                    fh.write("more\n")
            return out
        effects.folder_listing = changing
        try:
            self.ran(m2, [copy.deepcopy(k)], lane_more=copy.deepcopy(RK18_FORMS), ending="stopped")
        finally:
            effects.folder_listing = real
        self.assertFalse(os.path.exists(m2.path("dev", "demo-memory")))

    # ---- G21-11 (item 14, S10; G20's question 1). The summary and the hand-off prompt at a `complete` ending (FORM-1) ----
    def test_G21_11_FORM1_FORM2_at_a_complete_ending_the_summary_and_the_hand_off_prompt_are_rendered_safe_only(self):
        fixed = {"preview": [L("Sunset preview")], "summary": [L("Sunset: what the run did.")],
                 "handoff": [L("Paste this into the app: the project is archived."),
                             {"line": L("Database: backed up, not paused"), "when": "K2"},
                             {"text": [L("Its reason: "), {"input": "description"}]}]}
        k2 = checking("K2", [{"read": "path", "path": rowlib.DEV, "is": "dir"}],
                      condition={"on": "fact", "fact": "flags.db", "equals": True, "reason": "a layer the project lacks"})
        for db, want in ((True, True), (False, False)):
            with self.subTest(db=db):
                m = self.machine("h%s" % db, "h%s" % db)
                looked, went = self.ran(m, [checking("K1", [{"read": "path", "path": rowlib.DEV, "is": "dir"}]), copy.deepcopy(k2)],
                                        lane_more={"fixed_text": copy.deepcopy(fixed)}, inputs=m.inputs(flags={"db": db}))
                names = [os.path.basename(f) for f in went.doc["forms"]]
                self.assertEqual(names, ["status-1.txt", "summary-1.txt", "handoff-1.txt"])
                summary = open(went.doc["forms"][1]).read().split("\n")
                self.assertEqual(summary[0], "Sunset: what the run did.")
                self.assertEqual(summary[1:], open(went.doc["forms"][0]).read().split("\n"))
                handoff = open(went.doc["forms"][2]).read()
                expected = ["Paste this into the app: the project is archived."] + (["Database: backed up, not paused"] if want else []) \
                    + ["Its reason: a fixture project"]
                self.assertEqual(handoff, "\n".join(expected) + "\n")
        # a run that stops renders neither
        m = self.machine("hs", "hs")
        stop = checking("K1", [{"read": "path", "path": rowlib.path(rowlib.DEV, "nowhere"), "is": "dir"}])
        looked, went = self.ran(m, [stop], lane_more={"fixed_text": copy.deepcopy(fixed)}, ending=None)
        self.assertNotEqual(went.ending, "complete")
        self.assertEqual([os.path.basename(f) for f in went.doc.get("forms") or [] if "summary" in f or "handoff" in f], [])

    # ---- G21-12 (item 15, S8). A family item inside a folder a plan's move moves is placed by that move's output (RUN-6) --
    def test_G21_12_RUN6_a_family_item_inside_a_folder_the_plan_moves_is_placed_by_that_moves_output(self):
        m = self.machine()
        m.put("dev/vf/inside.md", "see OLD/\n")
        m.put("dev/outside.md", "see OLD/\n")
        vf, vfa = rowlib.path(rowlib.DEV, "vf"), rowlib.path(rowlib.DEV, "vf-archived")
        mv = rowlib.move("T13", source=vf, target=vfa, output="vault folder archived")
        for test in ("planning_test", "before_test", "after_test", "after_check"):
            for c in mv[test]:
                if c.get("path") == vf and c.get("is") == "file":
                    c["is"] = "dir"
                if c.get("path") == vfa and c.get("is") == "file":
                    c["is"] = "dir"
        mv["way_back"] = {"none": "the row declares none"}
        mv["reverse_inputs"] = "none"
        within = {"folder": vf, "output": "vault folder archived.path"}
        rows = [mv]
        for rid, glob in (("F1", "vf/*.md"), ("F2", "*.md")):
            f = checking(rid, [{"read": "path", "path": {"each": "place"}, "is": "file"}], output={"name": rid + " {each.n}", "fields": {}},
                         needs=[{"output": "vault folder archived", "level": "made", "treatment": "then not applicable"}])
            f["thing"]["family"] = {"read": "files", "folder": rowlib.DEV, "glob": glob, "holding": L("OLD/"),
                                    "validators": {"name": "one line of plain words"}, "within": copy.deepcopy(within)}
            rows.append(f)
        looked, went = self.ran(m, rows)
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual(op_of(manifest, "F1-1")["thing"]["passes"][0]["path"],
                         {"path": [{"output": "vault folder archived.path"}, L("inside.md")]})
        self.assertEqual(op_of(manifest, "F2-1")["thing"]["passes"][0]["path"], L(m.path("dev", "outside.md")))
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual((statuses["F1-1"], statuses["F2-1"]), ("passed", "passed"))


# ---- G21-13 (A153). RK19: a hosting value under the least length is saved and makes no entry (SEC-4) ---------------------
class ShortMembers(harness.Case):
    def test_G21_13_SEC4_RK19_a_saved_hosting_value_under_eight_bytes_makes_no_register_entry_and_one_at_eight_does(self):
        import test_g19_machinery as g19
        from test_g20_machinery import secret_pairs_providers
        long_value = "pw" + harness.canary("rk19")
        for short, ending in (("1", "complete"), ("abcdefg", "complete"), ("abcdefgh", "stopped")):
            with self.subTest(short=short):
                m = self.machine("r%d" % len(short), "r%d" % len(short))
                m.set_fake("fakehost", identity="source-one")
                m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0,
                                         "stdout": {"envs": [{"key": "FIXTURE_A", "value": short}, {"key": "FIXTURE_B", "value": long_value}]}})
                row = g19.keep_row(scope={"inventory_from": {"pairs": "pairs"}})
                row["construction"]["builder"] = "values"
                row["construction"]["hosting_env"] = True       # the keep that saves a hosting environment's values (G22-3)
                row["commands"] = [rowlib.use("values", "fakehost.values"), rowlib.use("ident", "fakehost.identify")]
                later = rowlib.says("Y2", words=L("told " + short))
                rowlib.install(m, rowlib.lane("sunrise", [row, later]), providers=secret_pairs_providers())
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                went = m.go(looked)
                self.assertEqual(went.ending, ending, went.text)
                if ending == "complete":
                    # saved: the keep holds it; and no entry: the later line holding it went out as it stands
                    self.assertIn('FIXTURE_A="%s"' % short, open(m.path("dev", "demo-env.txt")).read() if os.path.exists(m.path("dev", "demo-env.txt"))
                                  else open([os.path.join(m.dev, n) for n in os.listdir(m.dev) if n.endswith("-env.txt")][0]).read())
                    self.assertIn("told " + short, m.calls("fakehost", "noop")[-1]["argv"])


class FolderRecheck(harness.Case):
    def test_G21_10_KEEP3_a_folder_kept_whole_rechecks_by_its_listing_its_size_and_owner_only_permissions(self):
        import tempfile
        from sun_core import effects, fsio
        root = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
        place = os.path.join(root, "copy")
        os.makedirs(os.path.join(place, "notes"), 0o700)
        os.chmod(place, 0o700)
        for rel, text in (("MEMORY.md", "# memory\n"), (os.path.join("notes", "one.md"), "one\n")):
            fd = os.open(os.path.join(place, rel), os.O_WRONLY | os.O_CREAT, 0o600)
            os.write(fd, text.encode())
            os.close(fd)
        listing = [["MEMORY.md", fsio.sha256_hex(b"# memory\n")], [os.path.join("notes", "one.md"), fsio.sha256_hex(b"one\n")]]
        kept = {"size": 13, "sha256": fsio.sha256_hex(fsio.canonical_json(listing).encode("utf-8"))}

        class Engine(object):
            fs, run_dir = fsio.FS(), root

            class state(object):
                completions = {"K1": {"keep": kept}}

            def value(self, mark, op):
                return mark
        operation = {"id": "K1", "thing": {"place": place}, "construction": {"id": "C1", "copy_folder": L("x")}}
        try:
            self.assertTrue(effects.recheck_keep(Engine(), operation))
            os.chmod(os.path.join(place, "MEMORY.md"), 0o644)
            self.assertFalse(effects.recheck_keep(Engine(), operation))
            os.chmod(os.path.join(place, "MEMORY.md"), 0o600)
            with open(os.path.join(place, "notes", "one.md"), "w") as fh:
                fh.write("two\n")
            self.assertFalse(effects.recheck_keep(Engine(), operation))
        finally:
            import shutil
            shutil.rmtree(root)
