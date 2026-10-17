"""Part G19: the machinery the lanes' rows need, each item by its smallest mechanism (brief-28, section 3).

Every test's name carries the item's id (G19_n) and the frame's rule it rests on. The rows here are fixtures under the
tests, written with `rowlib`; none is a lane's row.
"""
import copy
import json
import os

import harness
import rowlib
from sun_core import plan, values

P = plan.RETIREMENT_PHASES
BACK = "putting back"


def manifest_of(m, run_id, number=1):
    with open(os.path.join(m.facts.run_dir(run_id), "manifest-%d.json" % number)) as fh:
        return json.load(fh)


def op_of(manifest, op):
    return [o for o in manifest["operations"] if o["id"] == op][0]


class Values(harness.Case):
    """A. Values (RUN-6, RUN-8; SEC-1, SEC-4 ground C)."""

    def test_G19_1_RUN8_a_mark_for_the_runs_date_by_the_tools_clock_is_settled_at_the_look_and_frozen_into_the_manifest(self):
        m = self.machine()
        made = rowlib.build("B1")
        made["construction"]["files"] = [{"rel": "AGENTS.md", "text": {"text": [rowlib.lit("verified: "), {"clock": "date"}, rowlib.lit("\n")]}}]
        made["after_check"] = [{"read": "path", "path": rowlib.path(rowlib.DEV, rowlib.NAME, "AGENTS.md"), "is": "file"}]
        rowlib.install(m, rowlib.lane("sunrise", [made]))
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual(op_of(manifest, "B1")["construction"]["files"][0]["text"], {"literal": "verified: 2026-01-01\n"})
        self.assertNotIn('"clock"', json.dumps(manifest))
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        with open(m.path("dev", "demo", "AGENTS.md")) as fh:
            self.assertEqual(fh.read(), "verified: 2026-01-01\n")

    def test_G19_2_SEC4_C_a_mark_for_the_account_his_settings_proved_resolves_from_the_manifests_accounts(self):
        m = self.machine()
        said = rowlib.says("Y1", words={"account": "fakehost"})
        rowlib.install(m, rowlib.lane("sunrise", [said]))
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual(manifest["accounts"], {"fakehost": "fixture-account"})
        self.assertEqual(op_of(manifest, "Y1")["commands"][0]["params"]["words"], {"literal": "fixture-account"})
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertIn("fixture-account", m.calls("fakehost", "noop")[-1]["argv"])

    def test_G19_2_SEC4_C_an_account_no_identity_read_proved_is_no_value_the_look_settles(self):
        m = self.machine()
        said = rowlib.says("Y1", words={"account": "fakegit"})        # fakegit declares no identity read
        rowlib.install(m, rowlib.lane("sunrise", [said]))
        looked = m.look()
        self.assertEqual(looked.code, 4, looked.text)
        self.assertIn("a value the look cannot settle", [f["finding"] for f in looked.doc["findings"]])
        self.assertEqual(m.calls("fakehost", "noop"), [])

    def test_G19_3_SEC1_EV5_a_record_saved_from_safe_content_is_usable_as_text_in_a_restore(self):
        m = harness.Machine(self.tmp, "r1", "r1")
        source = rowlib.path(rowlib.DEV, "a.md")
        target = rowlib.path(rowlib.DEV, "a-moved.md")
        forward = rowlib.move("M1", P[1], source=source, target=target, output="moved a")
        reverse = forward["way_back"]["reverse"]
        reverse["phase"] = BACK
        reverse["output"] = {"name": "back a", "fields": {}}
        # the reverse's target is the input its forward row saved from safe content: the path it was taken from (LOG-2)
        reverse["construction"]["to"] = {"saved": 0}
        reverse["after_test"] = [{"read": "path", "path": target, "is": "absent"}, {"read": "path", "path": {"saved": 0}, "is": "file"}]
        reverse["after_check"] = [{"read": "path", "path": {"saved": 0}, "is": "file"}]
        restore = rowlib.lane("restore", [], phases=(BACK,))
        rowlib.install(m, rowlib.lane("sunset", [forward], phases=P), restore)
        m.put("dev/a.md", "a\n")
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(m.go(looked, kind="sunset").ending, "complete")
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        back = op_of(manifest_of(m, looked.doc["run"]), "M1-reverse")
        self.assertEqual(back["construction"]["to"], {"literal": m.path("dev", "a.md")})
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertTrue(os.path.isfile(m.path("dev", "a.md")))
        self.assertFalse(os.path.exists(m.path("dev", "a-moved.md")))

    def test_G19_3_SEC1_a_record_saved_from_protected_content_stays_a_record_in_a_restore(self):
        saved = [{"record": "p-0000000000000001", "type": "before-image", "label": "x", "fingerprint": "0" * 64}, {"literal": "/x/y"}]
        bound = values.bind_saved({"path": [{"saved": 1}, {"literal": "z"}], "line": {"saved": 0}}, saved)
        self.assertEqual(bound["line"], {"record": saved[0]})
        self.assertEqual(bound["path"], [{"literal": "/x/y"}, {"literal": "z"}])

    def test_G19_4_SEC4_compare_held_reads_the_protected_records_content_so_a_held_compare_can_be_true(self):
        m = self.machine()
        made = rowlib.create("C1")
        made["after_check"] = [{"read": "command", "command": "look", "result": "success", "field": "id",
                                "equals": {"output": "remote.id"}, "compare_held": True}]
        rowlib.install(m, rowlib.lane("sunrise", [made]))
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"]).get("C1"), "done")
        # and a held compare against another thing's id is false: the after-check does not show the after-state
        m2 = self.machine("other", "b")
        other = copy.deepcopy(made)
        other["after_check"][0]["equals"] = {"literal": "not-the-id"}
        rowlib.install(m2, rowlib.lane("sunrise", [other]))
        _looked, went2 = m2.started()
        self.assertEqual(went2.ending, "stopped", went2.text)


# ---- B. Reads and facts (RUN-5 to RUN-7) -------------------------------------------------------------------------
def provs():
    """The fake providers, with three commands of this part: a listing whose whole answer is protected text, a count at
    the answer's top level, and a read whose id field may stand nowhere."""
    out = rowlib.providers()
    commands = out["fakehost"]["commands"]
    commands["listing"] = rowlib._command("fakehost", rowlib._t("noop"), [], answer="protected text")
    commands["count"] = rowlib._command("fakehost", rowlib._t("noop"), [dict(rowlib._field("count", "count", "equal", equals={"literal": 0}), place=[])])
    return out


def checking(rid, passes, commands="none", **more):
    k = rowlib.check(rid)
    k["thing"]["passes"] = passes
    k["commands"] = commands
    k.update(more)
    return k


class Reads(harness.Case):
    def ran(self, m, rows, lane_more=None, providers=None, inputs=None, ending="complete"):
        rowlib.install(m, rowlib.lane("sunrise", rows, **(lane_more or {})), providers=providers or provs())
        looked = m.look(inputs=inputs)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked)
        self.assertEqual(went.ending, ending, went.text)
        return looked, went

    def test_G19_5_RUN6_RUN7_a_lane_fact_from_one_read_of_a_thing_there_before_the_run_in_a_condition_and_as_a_value(self):
        startup = rowlib.path(rowlib.DEV, "startup.zsh")
        facts = [{"name": "wired.shortcut", "read": "line", "path": startup, "holding": rowlib.lit("project-shortcuts")},
                 {"name": "present.notes", "read": "path", "path": rowlib.path(rowlib.DEV, "notes")}]
        k = rowlib.check("K1", condition={"on": "fact", "fact": "wired.shortcut", "equals": True, "reason": "the shortcut file is not wired into your shell"})
        y = rowlib.says("Y1", words={"fact": "present.notes"})
        for wired, notes in ((True, True), (False, False)):
            with self.subTest(wired=wired):
                m = self.machine("h%s" % wired, "s%s" % wired)
                m.put("dev/startup.zsh", "source ~/project-shortcuts.zsh\n" if wired else "export X=1\n")
                if notes:
                    m.put("dev/notes/a.txt", "a\n")
                rowlib.install(m, rowlib.lane("sunrise", [k, y], facts=facts), providers=provs())
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                manifest = manifest_of(m, looked.doc["run"])
                ids = [o["id"] for o in manifest["operations"]]
                self.assertEqual("K1" in ids, wired)
                if not wired:
                    self.assertEqual(manifest["not_applicable"][0]["reason"], "the shortcut file is not wired into your shell")
                self.assertEqual(op_of(manifest, "Y1")["commands"][0]["params"]["words"], {"literal": notes})

    def test_G19_6_SEC1_found_files_and_lines_an_items_field_safe_where_its_validator_passes_else_held(self):
        from sun_core import plan as planmod
        m = self.machine()
        m.put("dev/agents/one.plist", "runs demo\n")
        m.put("dev/agents/two.plist", "runs demo too\n")
        m.put("dev/agents/three.plist", "runs other\n")
        m.put("dev/agents/bad name!.plist", "runs demo\n")
        m.put("dev/staged/demo-scope.md", "2026-09-01: the scope\n")
        rowlib.install(m, rowlib.lane("sunrise", []), providers=provs())
        found = planmod.found_items(m.world().fs, {"read": "files", "folder": m.path("dev", "agents"), "glob": "*.plist",
                                                   "holding": "demo", "validators": {"stem": "a launch agent's label"}})
        self.assertEqual([i["name"] for i in found], ["bad name!.plist", "one.plist", "two.plist"])
        self.assertEqual([i["stem"] for i in found], ["bad name!", "one", "two"])
        lines = planmod.found_items(m.world().fs, {"read": "lines", "path": m.put("shortcuts.txt", 'alias x="cd /d/demo"\nalias y="cd /d/other"\n'),
                                                   "holding": 'cd /d/demo"', "name_after": "alias "})
        self.assertEqual(lines, [{"line": 'alias x="cd /d/demo"', "name": "x"}])
        dated = planmod.found_items(m.world().fs, {"read": "files", "folder": m.path("dev", "staged"), "glob": "demo-scope.md", "date": True})
        self.assertEqual(dated[0]["date"], "2026-09-01")
        named = planmod.found_items(m.world().fs, {"read": "files", "folder": m.path("dev", "staged"), "glob": "*-x.md", "date": True}) or []
        self.assertEqual(named, [])
        m.put("dev/staged/2026-08-02-x.md", "no date here\n")
        named = planmod.found_items(m.world().fs, {"read": "files", "folder": m.path("dev", "staged"), "glob": "*-x.md", "date": True})
        self.assertEqual(named[0]["date"], "2026-08-02")

    def test_G19_7_RUN6_a_family_row_expands_at_the_look_into_ordinary_operations_each_with_its_own_id(self):
        m = self.machine()
        m.put("dev/agents/one.plist", "runs demo\n")
        m.put("dev/agents/two.plist", "runs demo\n")
        m.put("dev/agents/bad name!.plist", "runs demo\n")
        m.put("dev/agents/three.plist", "runs other\n")
        k = checking("K1", [{"read": "path", "path": {"each": "path"}, "is": "file"}],
                     form_lines={"preview": "check the agent {each.stem}", "status": "checked {each.stem}"})
        k["thing"]["family"] = {"read": "files", "folder": rowlib.path(rowlib.DEV, "agents"), "glob": rowlib.lit("*.plist"),
                                "holding": rowlib.NAME, "validators": {"name": "one line of plain words", "stem": "a launch agent's label"}}
        k["content_classes"]["validators"] = ["one line of plain words", "a launch agent's label"]
        k["output"] = {"name": "agent checked {each.stem}", "fields": {}}
        looked, went = self.ran(m, [k])
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual([o["id"] for o in manifest["operations"]], ["K1-1", "K1-2", "K1-3"])
        by = dict((o["id"], o) for o in manifest["operations"])
        self.assertEqual(by["K1-2"]["thing"]["passes"][0]["path"], {"literal": m.path("dev", "agents", "one.plist")})
        self.assertEqual(by["K1-2"]["form_lines"]["preview"], "check the agent one")
        self.assertEqual(by["K1-2"]["output"]["name"], "agent checked one")
        # a name its validator does not pass is held: in a protected record, and its place in a line is the member's number
        self.assertIn("record", by["K1-1"]["thing"]["passes"][0]["path"])
        self.assertEqual(by["K1-1"]["form_lines"]["preview"], "check the agent #1")
        self.assertNotIn("bad name", json.dumps(manifest))
        self.assertEqual(m.statuses(looked.doc["run"]), {"K1-1": "passed", "K1-2": "passed", "K1-3": "passed"})

    def test_G19_7_LOG2_a_family_members_held_line_is_its_edit_and_its_saved_reverse_input_by_content(self):
        from sun_core import protected
        m = self.machine()
        m.put("shortcuts.txt", 'alias d="cd /x/demo"\nalias o="cd /x/other"\n')
        file = {"location": "shortcut_file"}
        gone = rowlib.swap_add("S1")
        gone["before_test"] = [{"id": "has", "read": "line", "path": file, "line": {"each": "line"}, "count": 1}]
        gone["after_test"] = [{"read": "line", "path": file, "line": {"each": "line"}, "present": False}]
        gone["after_check"] = list(gone["after_test"])
        gone["construction"] = {"id": "C3", "risks": ["RK2"], "edit": {"kind": "remove-line", "line": {"each": "line"}}}
        gone["reverse_inputs"] = [{"read": "value", "value": {"each": "line"}, "type": "line", "label": "the line"}]
        gone["span"] = {"placement": "at the end", "ordered": False}
        gone["thing"]["family"] = {"read": "lines", "path": file, "holding": rowlib.lit('cd /x/demo"'), "name_after": "alias "}
        gone["output"] = {"name": "shortcut removed {each.name}", "fields": {}}
        looked, went = self.ran(m, [gone])
        with open(m.path("shortcuts.txt")) as fh:
            self.assertEqual(fh.read(), 'alias o="cd /x/other"\n')
        start = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "start"][0]
        saved = protected.read(m.world().fs, m.facts.run_dir(looked.doc["run"]), start["inputs"][0])
        self.assertEqual(saved, b'alias d="cd /x/demo"')
        self.assertNotIn("cd /x/demo", json.dumps(manifest_of(m, looked.doc["run"])))

    def test_G19_8_SEC4_A147_a_count_of_the_lines_of_a_file_and_of_a_commands_protected_text_that_hold_a_value(self):
        m = self.machine()
        m.put("dev/table.txt", "a demo\nb\nc demo\n")
        canary = harness.canary("tab")
        m.plan_fake("fakehost", {"command": "noop", "do": "raw", "text": "x demo %s\ny\n" % canary})
        k = checking("K1", [{"read": "text", "path": rowlib.path(rowlib.DEV, "table.txt"), "text": rowlib.NAME, "count": 2},
                            {"read": "text", "path": rowlib.path(rowlib.DEV, "table.txt"), "text": rowlib.lit("zzz"), "present": False},
                            {"read": "text", "command": "listing", "text": rowlib.NAME, "count": 1}],
                     commands=[rowlib.use("listing", "fakehost.listing")])
        looked, went = self.ran(m, [k])
        self.assertEqual(m.statuses(looked.doc["run"]), {"K1": "passed"})
        self.assertNowhere(canary, went)
        for name in os.listdir(m.facts.run_dir(looked.doc["run"])):
            full = os.path.join(m.facts.run_dir(looked.doc["run"]), name)
            if os.path.isfile(full):
                self.assertNotIn(canary, open(full, encoding="utf-8", errors="replace").read(), name)

    def test_G19_9_SEC4_a_test_that_a_commands_optional_field_stood_nowhere(self):
        for has_id, ending in ((False, "complete"), (True, "stopped")):
            with self.subTest(has_id=has_id):
                m = self.machine("h%s" % has_id, "p%s" % has_id)
                doc = {"state": "active", "name": "demo"}
                if has_id:
                    doc["id"] = "abc123"
                m.plan_fake("fakehost", {"command": "get", "stdout": doc})
                k = checking("K1", [{"read": "command", "command": "look", "result": "success", "field": "id", "present": False}],
                             commands=[rowlib.use("look", "fakehost.get", name=rowlib.NAME)])
                self.ran(m, [k], ending=ending)

    def test_G19_12_SEC4_a_top_level_answer_place_reads_the_whole_answer(self):
        for text, ending in (("0\n", "complete"), ("3\n", "stopped")):
            with self.subTest(text=text):
                m = self.machine("t%s" % text.strip(), "t%s" % text.strip())
                m.plan_fake("fakehost", {"command": "noop", "do": "raw", "text": text})
                k = checking("K1", [{"read": "command", "command": "n", "result": "success", "field": "count", "is_equal": True}],
                             commands=[rowlib.use("n", "fakehost.count")])
                self.ran(m, [k], ending=ending)

    def test_G19_11_SEC3_RK5_name_free_as_an_after_check_that_the_name_is_now_taken(self):
        m = self.machine()
        m.put(".zshrc", "alias gsx='ls'\n")
        k = checking("K1", [{"read": "name-free", "name": rowlib.lit("gsx"), "free": False},
                            {"read": "name-free", "name": rowlib.lit("qzxw"), "free": True}])
        looked, went = self.ran(m, [k])
        self.assertEqual(m.statuses(looked.doc["run"]), {"K1": "passed"})

    def test_G19_10_SEC10_index_current_and_a_branchs_commit_read_from_the_repository_itself_also_as_an_output_field(self):
        import subprocess
        m = self.machine()
        repo = m.path("dev", "demo")
        os.makedirs(repo)

        def git(*a):
            return subprocess.run(["/usr/bin/git", "-C", repo, "-c", "user.email=f@x.invalid", "-c", "user.name=f"] + list(a),
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout.decode().strip()
        git("init", "-q", "--initial-branch", "main")
        m.put("dev/demo/.gitignore", "ignored.txt\n")
        m.put("dev/demo/a.txt", "a\n")
        m.put("dev/demo/notes.txt", "")
        git("add", "--all")
        git("commit", "-q", "-m", "one")
        sha = git("rev-parse", "main")
        m.put("dev/demo/ignored.txt", "x\n")
        where = rowlib.path(rowlib.DEV, rowlib.NAME)
        k = checking("K1", [{"read": "index-current", "repo": where, "is": True},
                            {"read": "ref", "repo": where, "ref": "main", "exists": True},
                            {"read": "ref", "repo": where, "ref": "other", "exists": False},
                            {"read": "ref", "repo": where, "ref": "main", "equals": rowlib.lit(sha)}],
                     )
        note = rowlib.path(rowlib.DEV, rowlib.NAME, "notes.txt")
        s = rowlib.swap_add("S1", file=note, line=rowlib.lit("one note"), output="head")
        s["before_test"] = s["before_test"][:1]
        s["construction"]["risks"] = ["RK2"]
        s["output"] = {"name": "head", "fields": {"commit": {"observed": "commit"}}}
        s["thing"]["commit_of"] = {"repo": where, "ref": "main"}
        y = rowlib.says("Y1", words={"output": "head.commit"}, needs=[{"output": "head", "level": "state", "treatment": "then not applicable"}])
        looked, went = self.ran(m, [k, s, y])
        self.assertIn(sha, m.calls("fakehost", "noop")[-1]["argv"])
        # an untracked file that is not ignored, and a tracked file changed: the index is not current
        for change in ("dev/demo/new.txt", "dev/demo/a.txt"):
            with self.subTest(change=change):
                m2 = self.machine("g%d" % len(change), "g%d" % len(change))
                repo2 = m2.path("dev", "demo")
                os.makedirs(repo2)
                subprocess.run(["/usr/bin/git", "-C", repo2, "init", "-q"], check=True)
                m2.put("dev/demo/a.txt", "a\n")
                subprocess.run(["/usr/bin/git", "-C", repo2, "add", "--all"], check=True)
                m2.put(change, "changed\n")
                k2 = checking("K1", [{"read": "index-current", "repo": where, "is": False}])
                self.ran(m2, [k2])


# ---- C. Constructions and edits (OP-2, OP-3, EV-6) ---------------------------------------------------------------
PROJECT = rowlib.path(rowlib.DEV, rowlib.NAME)


def kit_row(rid, rel, edit, before, after, **more):
    place = rowlib.path(rowlib.DEV, rowlib.NAME, *rel.split("/"))
    out = rowlib.row("change", rid, "one",
                     thing={"role": "the kit file " + rel, "identity": "path", "place": place, "tracked": ["exists", "sha256"]},
                     planning_test=[{"read": "path", "path": PROJECT, "is": "dir"}],
                     before_test=before(place), after_test=after(place),
                     construction=dict({"id": "C3", "risks": ["RK2"], "edit": edit, "make_parents": {"within": PROJECT}}, **more),
                     after_check=after(place), way_back={"none": "the row declares none: no sunrise undo"},
                     output={"name": "kit " + rel, "fields": {"path": place}})
    return out


class Constructions(harness.Case):
    def go(self, m, rows, ending="complete", kind="sunrise", phases=("one",)):
        rowlib.install(m, rowlib.lane(kind, rows, phases=phases), providers=provs())
        looked = m.look(kind=kind)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind=kind)
        self.assertEqual(went.ending, ending, went.text)
        return looked, went

    def read(self, m, *rel):
        with open(m.path(*rel)) as fh:
            return fh.read()

    def test_G19_13_OP2_A147_a_change_of_an_absent_file_publishes_as_C1_does_its_missing_parent_made_inside_the_project_folder(self):
        m = self.machine()
        os.makedirs(m.path("dev", "demo"))
        absent = lambda p: [{"read": "path", "path": p, "is": "absent"}]       # noqa: E731
        there = lambda p: [{"read": "path", "path": p, "is": "file"}]          # noqa: E731
        row = kit_row("SR03-readme", "docs/notes/README.md", {"kind": "kit", "text": {"text": [rowlib.lit("# "), rowlib.NAME, rowlib.lit("\n")]},
                                                               "where_it_stands": "keep"}, absent, there, mode=0o644)
        looked, _went = self.go(m, [row])
        self.assertEqual(self.read(m, "dev", "demo", "docs", "notes", "README.md"), "# demo\n")
        self.assertEqual(os.stat(m.path("dev", "demo", "docs", "notes", "README.md")).st_mode & 0o777, 0o644)
        start = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "start"][0]
        self.assertEqual(start["thing"]["exists"], False)
        self.assertEqual(m.statuses(looked.doc["run"]), {"SR03-readme": "done"})

    def test_G19_13_RUN6_the_kit_edit_adds_the_template_below_what_stands_and_lifts_claudes_other_lines(self):
        m = self.machine()
        m.put("dev/demo/AGENTS.md", "# a framework block\n")
        m.put("dev/demo/CLAUDE.md", "@AGENTS.md\nan old rule\n")
        gates = rowlib.lit("- Feature branches + PRs. Never push to main.")
        lacks = lambda p: [{"read": "text", "path": p, "text": gates, "present": False, "or_absent": True}]   # noqa: E731
        holds = lambda p: [{"read": "text", "path": p, "text": gates, "count": 1}]                         # noqa: E731
        claude = rowlib.path(rowlib.DEV, rowlib.NAME, "CLAUDE.md")
        agents = kit_row("SR03-agents", "AGENTS.md", {"kind": "kit", "text": rowlib.lit("## Gates\n- Feature branches + PRs. Never push to main.\n"),
                                                     "where_it_stands": "append", "lift_from": claude,
                                                     "lift_heading": rowlib.lit("## Lifted from CLAUDE.md"), "stub": rowlib.lit("@AGENTS.md")},
                         lacks, holds)
        self.go(m, [agents])
        self.assertEqual(self.read(m, "dev", "demo", "AGENTS.md"),
                         "# a framework block\n## Gates\n- Feature branches + PRs. Never push to main.\n## Lifted from CLAUDE.md\nan old rule\n")

    def test_G19_13_the_kit_edit_makes_claude_the_stub_only_where_each_of_its_other_lines_stands_in_agents(self):
        stub = rowlib.lit("@AGENTS.md")
        lacks = lambda p: [{"read": "line", "path": p, "line": stub, "count": 1}, {"read": "text", "path": p, "text": rowlib.lit("old rule"), "present": True}]  # noqa: E731
        only = lambda p: [{"read": "text", "path": p, "text": rowlib.lit("old rule"), "present": False}, {"read": "line", "path": p, "line": stub, "count": 1}]  # noqa: E731
        agents = rowlib.path(rowlib.DEV, rowlib.NAME, "AGENTS.md")
        for lifted, ending in ((True, "complete"), (False, "stopped")):
            with self.subTest(lifted=lifted):
                m = self.machine("k%s" % lifted, "k%s" % lifted)
                m.put("dev/demo/AGENTS.md", "# kit\nan old rule\n" if lifted else "# kit\n")
                m.put("dev/demo/CLAUDE.md", "@AGENTS.md\nan old rule\n")
                row = kit_row("SR03-claude", "CLAUDE.md", {"kind": "kit", "text": rowlib.lit("@AGENTS.md\n"), "where_it_stands": "stub",
                                                           "lift_from": agents, "stub": stub}, lacks, only)
                self.go(m, [row], ending=ending)
                self.assertEqual(self.read(m, "dev", "demo", "CLAUDE.md"), "@AGENTS.md\n" if lifted else "@AGENTS.md\nan old rule\n")

    def test_G19_13_C7_a_move_makes_a_missing_parent_folder_of_its_target_inside_the_project_folder_and_no_other(self):
        for inside, ending in ((True, "complete"), (False, "stopped")):
            with self.subTest(inside=inside):
                m = self.machine("m%s" % inside, "m%s" % inside)
                os.makedirs(m.path("dev", "demo"))
                m.put("dev/staged/demo-scope.md", "scope\n")
                source = rowlib.path(rowlib.DEV, "staged", "demo-scope.md")
                target = rowlib.path(rowlib.DEV, rowlib.NAME, "docs", "scope", "demo.md") if inside else rowlib.path(rowlib.DEV, "elsewhere", "demo.md")
                moved = rowlib.move("SR06", source=source, target=target)
                moved["way_back"] = {"none": "the row declares none: no sunrise undo"}
                moved["reverse_inputs"] = "none"
                moved["construction"]["make_parents"] = {"within": PROJECT}
                self.go(m, [moved], ending=ending)
                self.assertEqual(os.path.isfile(m.path("dev", "demo", "docs", "scope", "demo.md")), inside)
                self.assertFalse(os.path.exists(m.path("dev", "elsewhere")))

    def test_G19_14_EV6_replace_all_every_occurrence_of_a_text(self):
        m = self.machine()
        m.put("dev/note.md", "see old/a and old/b\nold/c\n")
        place = rowlib.path(rowlib.DEV, "note.md")
        old, new = rowlib.lit("old/"), rowlib.lit("new/")
        row = rowlib.row("change", "T17", "one", thing={"role": "a note", "identity": "path", "place": place, "tracked": ["exists", "sha256"]},
                         planning_test=[{"read": "path", "path": place, "is": "file"}],
                         before_test=[{"read": "text", "path": place, "text": old, "present": True}],
                         after_test=[{"read": "text", "path": place, "text": old, "present": False}, {"read": "text", "path": place, "text": new, "count": 2}],
                         construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace-all", "old": old, "new": new}},
                         after_check=[{"read": "text", "path": place, "text": old, "present": False}],
                         way_back={"none": "the row declares none"})
        self.go(m, [row])
        self.assertEqual(self.read(m, "dev", "note.md"), "see new/a and new/b\nnew/c\n")

    def test_G19_14_EV6_move_line_under_its_heading_and_its_reverse_back_between_its_recorded_neighbours(self):
        m = harness.Machine(self.tmp, "r1", "r1")
        m.put("dev/index.md", "# index\n## Active\n- [[proj/demo/_index|demo]]\n- [[proj/other/_index|other]]\n")
        place = rowlib.path(rowlib.DEV, "index.md")
        old, new = rowlib.lit("proj/demo/_index"), rowlib.lit("arch/demo/_index")
        reverse = rowlib.row("change", "T16-reverse", BACK, thing={"role": "the index", "identity": "path", "place": place, "tracked": ["exists", "sha256"], "span": True},
                             planning_test=[{"read": "path", "path": place, "is": "file"}],
                             before_test=[{"read": "text", "path": place, "text": new, "count": 1}],
                             after_test=[{"read": "text", "path": place, "text": new, "present": False}, {"read": "text", "path": place, "text": old, "count": 1}],
                             construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "move-line", "holding": new, "old": new, "new": old,
                                                                                  "above": {"saved": 0}, "below": {"saved": 1}}},
                             after_check=[{"read": "text", "path": place, "text": old, "count": 1}],
                             way_back={"none": "the row declares none: it is itself a reverse"}, output={"name": "index back", "fields": {}})
        forward = rowlib.row("change", "T16", P[1], thing={"role": "the index", "identity": "path", "place": place, "tracked": ["exists", "sha256"], "span": True},
                             planning_test=[{"read": "path", "path": place, "is": "file"}],
                             before_test=[{"read": "text", "path": place, "text": old, "count": 1}],
                             after_test=[{"read": "text", "path": place, "text": old, "present": False}, {"read": "text", "path": place, "text": new, "count": 1}],
                             construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "move-line", "holding": old, "old": old, "new": new,
                                                                                  "under": rowlib.lit("## Archived")}},
                             after_check=[{"read": "text", "path": place, "text": new, "count": 1}],
                             way_back={"reverse": reverse},
                             reverse_inputs=[{"read": "line-above", "path": place, "holding": old, "type": "line", "label": "the line above"},
                                             {"read": "line-below", "path": place, "holding": old, "type": "line", "label": "the line below"}],
                             span={"placement": "in place", "ordered": False}, output={"name": "index archived", "fields": {}})
        rowlib.install(m, rowlib.lane("sunset", [forward], phases=P), rowlib.lane("restore", [], phases=(BACK,)), providers=provs())
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(m.go(looked, kind="sunset").ending, "complete")
        self.assertEqual(self.read(m, "dev", "index.md"), "# index\n## Active\n- [[proj/other/_index|other]]\n## Archived\n- [[arch/demo/_index|demo]]\n")
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(self.read(m, "dev", "index.md"), "# index\n## Active\n- [[proj/demo/_index|demo]]\n- [[proj/other/_index|other]]\n## Archived\n")

    def test_G19_15_LOG2_SEC6_a_read_command_that_writes_into_staging_its_file_kept_as_a_protected_record_of_the_declared_type(self):
        from sun_core import protected
        m = self.machine()
        m.put("shortcuts.txt", "alias other\n")
        added = rowlib.swap_add("S1")
        added["commands"] = [rowlib.use("definition", "fakehost.definition")]
        added["reverse_inputs"] = [{"read": "command", "command": "definition", "out_param": "out", "type": "definition", "label": "the routine's definition"}]
        providers = provs()
        providers["fakehost"]["commands"]["definition"] = rowlib._command("fakehost", rowlib._t("write", "--out", rowlib.P("out")), [], secret_output="staging")
        rowlib.install(m, rowlib.lane("sunrise", [added]), providers=providers)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        start = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "start"][0]
        reference = start["inputs"][0]
        self.assertEqual(reference["type"], "definition")
        self.assertTrue(protected.read(m.world().fs, m.facts.run_dir(looked.doc["run"]), reference).startswith(b"FIXTURE_URL="))
        staging = os.path.join(m.facts.run_dir(looked.doc["run"]), "staging")
        self.assertEqual([f for _r, _d, fs in os.walk(staging) for f in fs], [])


# ---- the control room's four more items (G19-25 to G19-28), and the family from a held list ------------------------
def keep_row(rid="P1", scope=None):
    place = rowlib.path(rowlib.DEV, {"text": [rowlib.NAME, rowlib.lit("-env.txt")]})
    return rowlib.row("keep", rid, "one",
                      thing={"role": "the saved env values", "identity": "path", "place": place, "tracked": ["exists", "identity", "sha256"]},
                      planning_test=[{"read": "path", "path": place, "is": "absent"}],
                      before_test=[{"id": "free", "read": "path", "path": place, "is": "absent"}],
                      after_test=[{"read": "path", "path": place, "is": "file"}],
                      construction={"id": "C1", "builder": "pull", "out_param": "out", "single_file": True, "mode": 0o600},
                      commands=[rowlib.use("pull", "fakehost.write"), rowlib.use("keys", "fakehost.keys"), rowlib.use("ident", "fakehost.identify")],
                      after_check=[{"read": "path", "path": place, "is": "file"}],
                      keep_scope=dict({"scope": "every key", "same_state": "the key list read before and after the pull", "content_checks": [],
                                       "source_identity_read": {"command": "ident", "field": "identity"}}, **(scope or {})),
                      content_classes={"reads": ["secret"], "stores": ["secret"], "shows": ["safe"], "validators": [], "resting_places": ["the sunset folder"]},
                      output={"name": "env copy", "fields": {"path": place}})


def keys_provs():
    out = provs()
    commands = out["fakehost"]["commands"]
    commands["keys"] = rowlib._command("fakehost", rowlib._t("noop"), [dict(rowlib._field("keys", "name", "held", alphabet="A-Z_", max_length=64),
                                                                          place=["envs", "*", "key"], many=True)])
    commands["keys"]["fields"].append(dict(rowlib._field("types", "name", "held", required=(), alphabet="a-z", max_length=16), place=["envs", "*", "type"], many=True))
    # G20-6: the saved hosting env values are a secret list (SEC-4 as A150 words it), each member entered in the register
    commands["values"] = rowlib._command("fakehost", rowlib._t("noop"), [dict(rowlib._field("pairs", "name", "secret", alphabet="A-Z_", max_length=64),
                                                                            place=["envs", "*"], many=True, pairs={"key": "key", "value": "value"})])
    commands["envs"] = rowlib._command("fakehost", rowlib._t("noop"), [dict(rowlib._field("custom", "name", "held", alphabet="a-z-", max_length=64),
                                                                          place=["envs", "*", "slug"], many=True)])
    return out


def keys_doc(*keys):
    return {"envs": [{"key": k} for k in keys]}


class MoreItems(harness.Case):
    def go(self, m, rows, ending="complete", providers=None):
        rowlib.install(m, rowlib.lane("sunrise", rows), providers=providers or keys_provs())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked)
        self.assertEqual(went.ending, ending, went.text)
        return looked, went

    def test_G19_25_KEEP1_a_keeps_inventory_from_the_copys_lines_with_a_declared_prefix(self):
        from sun_core import protected
        m = self.machine()
        m.set_fake("fakehost", identity="source-one")
        looked, _went = self.go(m, [keep_row(scope={"inventory_from": {"lines": "FIXTURE_"}})])
        completion = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion"][0]
        listed = json.loads(protected.read(m.world().fs, m.facts.run_dir(looked.doc["run"]), completion["keep"]["inventory"]).decode())
        self.assertEqual(len(listed), 2)
        self.assertTrue(all(line.startswith("FIXTURE_") for line in listed))

    def test_G19_25_KEEP1_A148_a_keeps_inventory_read_just_before_and_just_after_its_builder_equal_both_times_and_to_the_copy(self):
        sensitive = {"envs": [{"key": "FIXTURE_URL", "type": "plain"}, {"key": "FIXTURE_KEY", "type": "sensitive"}]}
        cases = (("the same both times and the copy's", [keys_doc("FIXTURE_URL", "FIXTURE_KEY")] * 2, "complete"),
                 ("a key added between the two reads", [keys_doc("FIXTURE_URL", "FIXTURE_KEY"), keys_doc("FIXTURE_URL", "FIXTURE_KEY", "NEW")], "stopped"),
                 ("a returned key the copy lacks", [keys_doc("FIXTURE_URL", "FIXTURE_KEY", "LOST")] * 2, "stopped"),
                 ("a key of the copy that is neither returned nor listed apart", [keys_doc("FIXTURE_URL")] * 2, "stopped"),
                 ("a key whose value is never returned, listed apart", [sensitive] * 2, "complete"))
        for label, docs, ending in cases:
            with self.subTest(case=label):
                m = self.machine("i%d" % len(label), "i%d" % len(label))
                m.set_fake("fakehost", identity="source-one")
                m.plan_fake("fakehost", *[{"command": "noop", "do": "fail", "exit": 0, "stdout": d, "nth": n} for n, d in enumerate(docs, 1)])
                spec = {"command": "keys", "field": "keys", "copy_keys": "="}
                if label.startswith("a key whose value"):
                    spec["apart"] = {"field": "types", "equals": "sensitive"}
                row = keep_row(scope={"inventory_from": spec})
                row["construction"]["hosting_env"] = True       # the two reads are the hosting keep's alone (G22-4)
                looked, went = self.go(m, [row], ending=ending)
                if label.startswith("a key whose value"):
                    from sun_core import protected
                    completion = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion"][0]
                    self.assertEqual(json.loads(protected.read(m.world().fs, m.facts.run_dir(looked.doc["run"]), completion["keep"]["apart"])), ["FIXTURE_KEY"])
                if ending == "stopped":
                    self.assertIn("the keep is not whole", went.text)

    def test_G19_7_G19_25_a_family_expands_from_a_provider_commands_held_list_beside_fixed_members(self):
        m = self.machine()
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0, "stdout": {"envs": [{"slug": "staging-a"}, {"slug": "staging-b"}]}})
        k = checking("K1", [{"read": "path", "path": rowlib.DEV, "is": "dir"}], commands=[rowlib.use("envs", "fakehost.envs")],
                     form_lines={"preview": "save the environment {each.member}", "status": "saved {each.member}"})
        k["thing"]["family"] = {"read": "command", "command": "envs", "field": "custom", "also": ["development", "preview"]}
        k["output"] = {"name": "env {each.member}", "fields": {}}
        looked, _went = self.go(m, [k])
        manifest = manifest_of(m, looked.doc["run"])
        # a member found in the list stays held, and the row carries the tool's own label `custom-<n>` (the control room's
        # G19-7, widened); a fixed member is its own label
        self.assertEqual([o["id"] for o in manifest["operations"]], ["K1-development", "K1-preview", "K1-custom-1", "K1-custom-2"])
        self.assertEqual([o["form_lines"]["preview"] for o in manifest["operations"]],
                         ["save the environment development", "save the environment preview", "save the environment custom-1",
                          "save the environment custom-2"])
        self.assertNotIn("staging-a", json.dumps(manifest))

    def test_G19_26_RUN5_SEC4_C_one_identity_read_per_route_each_compared_with_his_settings(self):
        for other, ending in (("fixture-account", "preview"), ("someone-else", "refused")):
            with self.subTest(other=other):
                m = self.machine("a%d" % len(other), "a%d" % len(other))
                providers = keys_provs()
                host = providers["fakehost"]
                host["commands"]["whoami-cli"] = rowlib._command("fakehost", rowlib._t("noop"), [rowlib._field("account", "name", "equal", equals={"settings": "fakehost"}, **rowlib.NAMEF)])
                host["identity"] = {"request": {"command": "whoami", "field": "account"}, "runner": {"command": "whoami-cli", "field": "account"}}
                m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0, "stdout": {"account": other}})
                rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1")]), providers=providers)
                looked = m.look()
                self.assertEqual(looked.ending, ending, looked.text)
                self.assertEqual(len(m.calls("fakehost", "whoami")), 1)
                self.assertNowhere("someone-else", looked)

    def test_G19_27_SEC3_a_commands_own_trace_flags_replace_the_modules_for_it(self):
        for own, ending in ((None, "stopped"), (["--loud"], "complete")):
            with self.subTest(own=own):
                m = self.machine("t%s" % bool(own), "t%s" % bool(own))
                providers = keys_provs()
                if own is not None:
                    providers["fakehost"]["commands"]["say"]["trace_flags"] = own
                self.go(m, [rowlib.says("Y1", words=rowlib.lit("--verbose"))], ending=ending, providers=providers)

    def test_G19_28_G19_23_FORM1_a_form_line_filled_from_the_rows_frozen_safe_values_and_its_records_safe_fields_never_a_held_one(self):
        m = self.machine()
        m.set_fake("fakehost", things={"demo": {"id": "abc123secretid", "kind": "repo", "state": "active", "name": "demo"}})
        k = checking("K1", [{"read": "command", "command": "look", "result": "success", "field": "state", "equals": "active"}],
                     commands=[rowlib.use("look", "fakehost.get", name=rowlib.NAME)],
                     form_lines={"preview": "check <name> at the host", "status": "<name> is <state>; its id <id>"})
        looked, went = self.go(m, [k])
        with open(looked.doc["forms"][0]) as fh:
            self.assertIn("check demo at the host", fh.read())
        status = "".join(open(p).read() for p in went.doc["forms"])
        self.assertIn("demo is active; its id <id>", status)
        self.assertNotIn("abc123secretid", status)


class PairsKeep(harness.Case):
    """G19-29: a keep whose builder's answer is a held list of key and text pairs, written by the frame as one reversible
    line each, its inventory the answer's keys, and the staged copy decoded back to the answer's pairs whole (the reviewer's
    N3)."""

    def test_G19_29_KEEP1_SEC7_a_keep_built_from_an_answers_pairs_round_trips_each_value_whole(self):
        from sun_core import effects, protected
        m = self.machine()
        m.set_fake("fakehost", identity="source-one")
        pairs = [["SPLIT", "a\nOTHER=1"], ["QUOTED", 'say "hi" \\ there'], ["EMPTY", ""], ["SEP", "x\u2028y"]]
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0, "stdout": {"envs": [{"key": k, "value": v} for k, v in pairs]}})
        row = keep_row(scope={"inventory_from": {"pairs": "pairs"}})
        row["construction"]["builder"] = "values"
        row["commands"] = [rowlib.use("values", "fakehost.values"), rowlib.use("ident", "fakehost.identify")]
        rowlib.install(m, rowlib.lane("sunrise", [row]), providers=keys_provs())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        with open(m.path("dev", "demo-env.txt"), "rb") as fh:
            data = fh.read()
        self.assertEqual(data.count(b"\n"), 4)
        self.assertEqual(effects.decode_pairs(data), pairs)
        completion = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion"][0]
        self.assertEqual(json.loads(protected.read(m.world().fs, m.facts.run_dir(looked.doc["run"]), completion["keep"]["inventory"])),
                         ["SPLIT", "QUOTED", "EMPTY", "SEP"])

    def test_G19_29_a_staged_copy_altered_by_one_byte_does_not_decode_to_the_answers_pairs(self):
        from sun_core import effects
        pairs = [["SPLIT", "a\nOTHER=1"], ["QUOTED", 'q"\\'], ["EMPTY", ""]]
        data = effects.encode_pairs(pairs)
        self.assertEqual(effects.decode_pairs(data), pairs)
        for at in range(len(data)):
            altered = data[:at] + bytes([data[at] ^ 0x01]) + data[at + 1:]
            self.assertNotEqual(effects.decode_pairs(altered), pairs, at)


# ---- D. Keeps and risks (KEEP-1 to KEEP-3, RISK-1, RISK-2) --------------------------------------------------------
def admitted(row, providers=None):
    from sun_core import rows as rowsmod
    providers = providers or provs()
    expanded = plan.expand({"rows": [row]}, providers)[0]
    return rowsmod.admit(expanded, providers, plan.held_outputs([expanded]))


class KeepsAndRisks(harness.Case):
    def test_G19_16_KEEP2_a_retiring_row_may_state_an_empty_list_of_keeps_it_requires(self):
        moved = rowlib.move("T12", P[1])
        moved["thing"].update({"retires": True, "where": "machine"})
        moved["keeps_required"] = []
        self.assertEqual(admitted(moved), [])
        moved["keeps_required"] = "none"
        self.assertIn("keeps_required", [f["entry"] for f in admitted(moved)])

    def test_G19_17_RISK1_RISK2_OP3_A147_RK18_admits_a_C6_carries_its_mark_once_and_has_its_form_line(self):
        unnamed = rowlib.refusing("SR05", construction="C6")
        self.assertIn("a read-then-ask on a row RK3 does not name (RISK-2)", [f["finding"] for f in admitted(unnamed)])
        named = rowlib.refusing("SR05", construction="C6")
        named["construction"]["risks"] = ["RK18"]
        named["construction"]["risk_line"] = "a branch made by hand between the read and the rename is the one renamed"
        self.assertEqual(admitted(named), [])
        no_line = copy.deepcopy(named)
        del no_line["construction"]["risk_line"]
        self.assertIn("RK18 is carried with no line of what can go wrong (RISK-1)", [f["finding"] for f in admitted(no_line)])
        swap = rowlib.swap_add("SR03")
        swap["before_test"] = swap["before_test"][:1]
        swap["construction"]["risks"] = ["RK2", "RK18"]
        swap["construction"]["risk_line"] = "a merge you would not have taken lands, nothing removed"
        self.assertEqual(admitted(swap), [])
        m = self.machine()
        m.set_fake("fakehost", things={"demo": {"id": "abc", "kind": "repo", "state": "active", "name": "demo"}})
        lane = rowlib.lane("sunrise", [named])
        lane["form_changes"]["the RK18 mark"] = "carried under v1's own risk for this step (RK18): {what}"
        rowlib.install(m, lane, providers=provs())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        with open(looked.doc["forms"][0]) as fh:
            self.assertIn("carried under v1's own risk for this step (RK18): a branch made by hand", fh.read())
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        marks = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "step" and r.get("step") == "risk-mark"]
        self.assertEqual([(r["op"], r["risk"]) for r in marks], [("SR05", "RK18")])

    def test_G19_18_KEEP1_A147_the_sources_identity_read_just_before_the_copy_where_the_copying_tool_reports_none(self):
        from sun_core import protected
        m = self.machine()
        m.set_fake("fakehost", identity="source-one")
        rowlib.install(m, rowlib.lane("sunrise", [keep_row(scope={"inventory_from": {"lines": "FIXTURE_"}})]), providers=keys_provs())
        looked = m.look()
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        completion = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion"][0]
        self.assertEqual(json.loads(protected.read(m.world().fs, m.facts.run_dir(looked.doc["run"]), completion["keep"]["source"])), "source-one")
        idents = [c["nth"] for c in m.calls("fakehost", "identify")]
        writes = [c["nth"] for c in m.calls("fakehost", "write")]
        self.assertEqual((len(idents), len(writes)), (1, 1))
        order = [c["argv"][0] for c in m.calls("fakehost") if c["argv"][0] in ("identify", "write")]
        self.assertEqual(order, ["identify", "write"])
