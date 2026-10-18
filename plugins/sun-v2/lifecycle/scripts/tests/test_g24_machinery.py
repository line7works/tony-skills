"""Part G24: six gaps the lanes' second parts proved (brief-33, section 2).

Every test's name carries the item's id (G24_n) and the frame's rule it rests on. The rows, the lanes and the provider
declarations here are fixtures under the tests, written with `rowlib`; none is a lane's row.
"""
import copy
import os

import harness
import rowlib
import test_g19_machinery as g19
import test_g20_machinery as g20
import test_g21_machinery as g21
import test_g23_machinery as g23

L = rowlib.lit
TAG = "refs/tags/sunset-2026-10-01"


# ---- G24-1. An equality on a field that stands nowhere is false (OP-5, OP-6; prov T01, SR15) --------------------------
def tag_providers():
    """The fake providers, with a read of one named value whose `head` field stands nowhere where the value is absent (a
    remote's tag or branch, read before it exists)."""
    out = rowlib.providers()
    out["fakegit"]["commands"]["head"] = rowlib._command(
        "fakegit", rowlib._t("head", "--ref", rowlib.P("ref")), [rowlib._field("head", "name", "fixed", required=(), **rowlib.NAMEF)])
    return out


def tag_rows():
    """A check that gives the commit to tag (`tag scan.commit`), and the tag's one push (C4), its after-test the equality
    rows-prov writes for T01: the tag's `head` equal to the scanned commit; its before-test the tag absent."""
    scan = rowlib.check("K1", output="tag scan")
    scan["output"] = {"name": "tag scan", "fields": {"commit": L("c1")}}
    absent = {"read": "command", "command": "look", "result": "success", "field": "head", "present": False}
    equal = {"read": "command", "command": "look", "result": "success", "field": "head", "equals": {"output": "tag scan.commit"}}
    tag = rowlib.row("change", "T01", "one",
                     thing={"role": "the remote's sunset tag", "identity": "named value", "before_word": "absent", "after_word": "the head"},
                     planning_test=[dict(absent)], before_test=[dict(absent, id="notag")], after_test=[dict(equal)],
                     construction={"id": "C4", "command": "push"},
                     commands=[rowlib.use("look", "fakegit.head", ref=L(TAG)),
                               rowlib.use("push", "fakegit.cas", ref=L(TAG), new={"output": "tag scan.commit"}, old=L("none"))],
                     repo_commands=["push"], after_check=[dict(equal)],
                     needs=[{"output": "tag scan", "level": "passed", "treatment": "then not applicable"}],
                     way_back={"none": "the row declares none: a tag is history"},
                     output={"name": "sunset tag", "fields": {"ref": L(TAG)}})
    return [scan, tag]


class AbsentFieldEquality(harness.Case):
    def test_G24_1_OP5_an_equality_on_a_field_that_stands_nowhere_is_false_so_a_fresh_tag_is_ready_and_pushed(self):
        m = self.machine()
        rowlib.install(m, rowlib.lane("sunrise", tag_rows()), providers=tag_providers())
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"])["T01"], "done")
        self.assertEqual(m.fake("fakegit", "state.json")["refs"], {TAG: "c1"})

    def test_G24_1_OP5_OP6_a_tag_made_by_another_on_another_commit_is_foreign_and_stops_never_already_so(self):
        m = self.machine()
        m.set_fake("fakegit", refs={TAG: "c2"})
        rowlib.install(m, rowlib.lane("sunrise", tag_rows()), providers=tag_providers())
        looked, went = m.started()
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("foreign", went.text)
        self.assertNotIn("T01", m.statuses(looked.doc["run"]), "the tag of another commit was given a status")
        self.assertFalse([r for r in m.journal(looked.doc["run"]) if r.get("op") == "T01" and r.get("status") == "already so"])
        self.assertEqual([c["argv"][0] for c in m.calls("fakegit") if c["argv"][:1] == ["cas"]], [], "a push was sent")
        self.assertEqual(m.fake("fakegit", "state.json")["refs"], {TAG: "c2"})


# ---- G24-2. A template part built from literals and parameters (SEC-3, RUN-5; prov vercel's `cli-team`) --------------
class TextTemplatePart(harness.Case):
    def test_G24_2_RUN5_SEC4_C_the_runner_routes_identity_read_takes_his_team_into_a_path_and_a_flag(self):
        m = self.machine()
        m.settings["accounts"]["fakehost"] = ["other-team", "fixture-account"]
        m.write_settings()
        providers = rowlib.providers()
        host = providers["fakehost"]
        host["commands"]["cli-team"] = rowlib._command(
            "fakehost", [L("whoami"), {"text": [L("/v2/teams/"), rowlib.P("team")]}, L("--scope"), rowlib.P("team")],
            [rowlib._field("account", "name", "equal", equals={"settings": "fakehost"}, **rowlib.NAMEF)], refusals=("not-found",))
        host["identity"] = {"runner": {"command": "cli-team", "field": "account", "params": {"team": {"settings": "fakehost"}}}}
        m.plan_fake("fakehost", {"command": "whoami", "do": "fail", "exit": 3, "stdout": {"kind": "not-found"}, "nth": 1})
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1", words={"account": "fakehost"})]), providers=providers)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual([c["argv"] for c in m.calls("fakehost", "whoami")],
                         [["whoami", "/v2/teams/other-team", "--scope", "other-team"],
                          ["whoami", "/v2/teams/fixture-account", "--scope", "fixture-account"]])
        self.assertEqual(g20.manifest_of(m, looked.doc["run"])["accounts"], {"fakehost": "fixture-account"})


# ---- G24-3. A found file's `suffix` and `lane` on the names precon and architect stage (RUN-6, SEC-1; rise SR06) ----------
STAGED = ("demo-cold-read-2026-10-01-2.md", "demo-cold-read-2026-10-01.md", "demo-review-2026-10-01-gemini-2.md",
          "demo-review-2026-10-01-gpt.md")


class StagedNames(harness.Case):
    def test_G24_3_RUN6_SEC1_a_dated_cold_reads_day_is_no_suffix_and_a_reviews_lane_is_read_after_its_date(self):
        from sun_core import plan as planmod
        m = self.machine()
        for name in STAGED:
            m.put("dev/staged/" + name, "x\n")
        found = planmod.found_items(m.world().fs, {"read": "files", "folder": m.path("dev", "staged"), "glob": "demo-*.md",
                                                   "suffix": True, "lane": True})
        self.assertEqual([(i["name"], i["suffix"], i.get("lane")) for i in found],
                         [("demo-cold-read-2026-10-01-2.md", "-2", None), ("demo-cold-read-2026-10-01.md", "", None),
                          ("demo-review-2026-10-01-gemini-2.md", "-2", "gemini"), ("demo-review-2026-10-01-gpt.md", "", "gpt")])

    def test_G24_3_RUN6_SEC1_G23_12_a_name_that_begins_with_its_date_or_has_none_reads_as_before(self):
        from sun_core import plan as planmod
        m = self.machine()
        m.put("dev/staged/2026-10-01-gpt-review-demo.md", "a\n")
        m.put("dev/staged/2026-10-02-gemini-review-demo-2.md", "b\n")
        m.put("dev/staged/notes-12.md", "c\n")
        found = planmod.found_items(m.world().fs, {"read": "files", "folder": m.path("dev", "staged"), "glob": "*.md",
                                                   "suffix": True, "lane": True})
        self.assertEqual([(i["name"], i["suffix"], i.get("lane")) for i in found],
                         [("2026-10-01-gpt-review-demo.md", "", "gpt"), ("2026-10-02-gemini-review-demo-2.md", "-2", "gemini"),
                          ("notes-12.md", "-12", None)])

    def test_G24_3_RUN6_the_staged_cold_read_and_review_are_placed_by_their_suffix_and_lane(self):
        for glob, target, want in (
                ("precon-cold-reads/demo-cold-read-*.md", [{"each": "date"}, L("-precon-cold-read-demo"), {"each": "suffix"}, L(".md")],
                 ["2026-10-01-precon-cold-read-demo-2.md", "2026-10-01-precon-cold-read-demo.md"]),
                ("architect-reviews/demo-review-*.md",
                 [{"each": "date"}, L("-architect-review-demo-"), {"each": "lane"}, {"each": "suffix"}, L(".md")],
                 ["2026-10-01-architect-review-demo-gemini-2.md", "2026-10-01-architect-review-demo-gpt.md"])):
            with self.subTest(glob=glob):
                m = self.machine(glob[:6], glob[:6])
                for name in STAGED:
                    sub = "precon-cold-reads" if "cold-read" in name else "architect-reviews"
                    m.put("dev/staged/%s/%s" % (sub, name), "x\n")
                k = g19.checking("K1", [{"read": "path", "path": rowlib.path(rowlib.DEV, "reviews", {"text": target}), "is": "absent"}],
                                 output={"name": "staged {each.n}", "fields": {}})
                k["thing"]["family"] = {"read": "files", "folder": rowlib.path(rowlib.DEV, "staged"), "glob": glob, "date": True,
                                        "suffix": True, "lane": True, "validators": {"lane": "one line of plain words"}}
                rowlib.install(m, rowlib.lane("sunrise", [k]), providers=g19.provs())
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                placed = [o["thing"]["passes"][0]["path"] for o in g20.manifest_of(m, looked.doc["run"])["operations"]]
                self.assertEqual(placed, [L(m.path("dev", "reviews", w)) for w in want])


# ---- G24-4. A folder whose publish landed before its mode was set ends at its construction's modes (OP-4, OP-6) --------
class LandedFolderMode(harness.Case):
    def test_G24_4_OP4_OP6_EV1b_a_kill_between_a_folders_publish_and_its_modes_resumes_to_the_modes_the_row_gives(self):
        points = (("post", "rename", "docs"), ("pre", "chmod", "docs"), ("post", "chmod", "docs"), ("pre", "chmod", ".gitkeep"))
        for i, (stage, op, end) in enumerate(points):
            with self.subTest(point="%s %s %s" % (stage, op, end)):
                label = "k%d" % i
                m = self.machine(label, label)
                os.makedirs(m.path("dev", "demo"))
                rowlib.install(m, rowlib.lane("sunrise", [g23.folder_row("SR03-docs", "docs", True)]))
                looked = m.look()
                killed = m.go(looked, kill=lambda e, s=stage, o=op, t=end: e["stage"] == s and e["op"] == o and str(e["subject"]).endswith(t))
                self.assertTrue(killed.killed, killed.text)
                self.assertEqual(m.resume().ending, "complete")
                self.assertEqual(m.statuses(looked.doc["run"]), {"SR03-docs": "done"})
                self.assertEqual(os.stat(m.path("dev", "demo", "docs")).st_mode & 0o777, 0o755)
                self.assertEqual(os.stat(m.path("dev", "demo", "docs", ".gitkeep")).st_mode & 0o777, 0o644)


# ---- G24-5. The merge replaces v1's old two-line AGENTS.md stub as it stands, and nothing else (RUN-6; rise SR03-agents) --
V1_STUB = ("The canonical agent file for this repo is **`CLAUDE.md`** in the same directory.\n"
           "This stub exists for tools that look for `AGENTS.md`. Read `CLAUDE.md`.")


class OldStubMerge(harness.Case):
    def merged(self, label, agents, pointer=V1_STUB):
        m = self.machine(label, label)
        os.makedirs(m.path("dev", "demo"))
        m.put("dev/demo/AGENTS.md", agents)
        m.put("dev/demo/CLAUDE.md", "@AGENTS.md\nan old rule\n")
        gates = L("- Feature branches.")
        lacks = lambda p: [{"read": "text", "path": p, "text": gates, "present": False, "or_absent": True}]   # noqa: E731
        holds = lambda p: [{"read": "text", "path": p, "text": gates, "count": 1}]                         # noqa: E731
        edit = {"kind": "kit", "text": L(g23.BODY), "where_it_stands": "merge", "pointer": L(pointer),
                "lift_from": rowlib.path(rowlib.DEV, rowlib.NAME, "CLAUDE.md"), "lift_heading": L("## Lifted from CLAUDE.md"),
                "stub": L("@AGENTS.md")}
        row = g19.kit_row("SR03-agents", "AGENTS.md", edit, lacks, holds, risks=["RK2", "RK18"],
                          risk_line="a merge or lift v1 would have shown you first is written without showing it")
        rowlib.install(m, rowlib.lane("sunrise", [row], **copy.deepcopy(g21.RK18_FORMS)), providers=g19.provs())
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        return open(m.path("dev", "demo", "AGENTS.md"), encoding="utf-8").read()

    def test_G24_5_RUN6_v1s_two_line_old_stub_is_replaced_by_the_body_as_it_stands(self):
        got = self.merged("a", "# AGENTS.md\n\n" + V1_STUB + "\n")
        self.assertEqual(got, "# AGENTS.md\n\n" + g23.BODY + "## Lifted from CLAUDE.md\nan old rule\n")

    def test_G24_5_RUN6_a_stub_he_wrote_more_into_keeps_every_line_he_wrote(self):
        mine = "# AGENTS.md\n\n" + V1_STUB + "\nmy own line\n"
        got = self.merged("b", mine)
        self.assertTrue(got.startswith(mine), got)
        for line in V1_STUB.split("\n") + ["my own line"]:
            self.assertEqual(got.count(line), 1, line)

    def test_G24_5_RUN6_G23_13_a_one_line_pointer_is_still_replaced(self):
        got = self.merged("c", "# AGENTS\nSee CLAUDE.md\n", pointer="See CLAUDE.md")
        self.assertEqual(got, "# AGENTS\n" + g23.BODY + "## Lifted from CLAUDE.md\nan old rule\n")


# ---- G24-6. A C3's computed after-image as a reverse input; `rel` for a member outside its `within` folder; a restore's
# reverses ordered by the lane's phases and needs, never the sunset's order backwards (EV-4, EV-5, EV-6, EV-7, ORD-4; set V06)
BACK2 = ("putting back", "putting back the index")


def note_rows(index_phase=BACK2[1]):
    """Set's T13, T14 and T17 and their reverses V02, V03 and V06, as rows-set 3.2 and 3.3 write them, on a vault of three
    notes linking the old folder: one outside the moved folder and two inside it, its `_index.md` changed by T14 and T17."""
    vault = rowlib.path(rowlib.DEV, "vault")
    vf, vfa = rowlib.path(rowlib.DEV, "vault", "proj", "demo"), rowlib.path(rowlib.DEV, "vault", "arch", "demo")
    t13 = rowlib.move("T13", g19.P[1], source=vf, target=vfa, output="vault folder archived")
    for key in ("planning_test", "before_test", "after_test", "after_check"):
        for row in (t13, t13["way_back"]["reverse"]):
            for c in row[key]:
                c["is"] = "dir" if c.get("is") == "file" else c["is"]
    v02 = t13["way_back"]["reverse"]
    v02.update({"id": "V02", "phase": BACK2[0], "output": {"name": "vault folder back", "fields": {"path": vf}}})
    made = [{"output": "vault folder archived", "level": "made", "treatment": "then not applicable"}]
    back = [{"output": "vault folder back", "level": "state", "treatment": "then not applicable"}]
    index = rowlib.path({"output": "vault folder archived.path"}, "_index.md")
    index_back = rowlib.path({"output": "vault folder back.path"}, "_index.md")
    text = lambda p, t, **k: dict({"read": "text", "path": p, "text": t}, **k)      # noqa: E731
    line = lambda p, t, **k: dict({"read": "line", "path": p, "line": t}, **k)      # noqa: E731  (a held image, read by its content)
    v03 = rowlib.row("change", "V03", index_phase,
                     thing={"role": "the index file", "identity": "path", "place": index_back, "tracked": ["exists", "sha256"], "span": True},
                     planning_test=[{"read": "path", "path": index_back, "is": "file"}],
                     before_test=[line(index_back, {"saved": 1}, count=1)],
                     after_test=[line(index_back, {"saved": 0}, count=1), line(index_back, {"saved": 1}, present=False)],
                     construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace", "old": {"saved": 1}, "new": {"saved": 0}}},
                     after_check=[line(index_back, {"saved": 0}, count=1)], needs=back,
                     way_back={"none": "the row declares none: it is itself a reverse"}, output={"name": "index active", "fields": {}})
    t14 = rowlib.row("change", "T14", g19.P[1],
                     thing={"role": "the index file", "identity": "path", "place": index, "tracked": ["exists", "sha256"], "span": True},
                     planning_test=[{"read": "path", "path": index, "is": "file"}],
                     before_test=[text(index, L("status: active"), count=1)],
                     after_test=[text(index, L("status: archived"), count=1)],
                     construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace", "old": L("status: active"), "new": L("status: archived")}},
                     after_check=[text(index, L("status: archived"), count=1)], needs=made, way_back={"reverse": v03},
                     reverse_inputs=[{"read": "value", "value": L("status: active"), "type": "before-image", "label": "the old text"},
                                     {"read": "value", "value": L("status: archived"), "type": "after-image", "label": "the new text"}],
                     span={"placement": "in place", "ordered": True}, output={"name": "index archived", "fields": {}})
    place_back = {"path": [{"output": "vault folder back.path"}, {"saved": 2}]}
    whole = lambda n: {"read": "line", "path": place_back, "line": {"saved": n}, "count": 1}     # noqa: E731
    v06 = rowlib.row("change", "V06", BACK2[0],
                     thing={"role": "the note", "identity": "path", "place": place_back, "tracked": ["exists", "sha256"], "span": True},
                     planning_test=[{"read": "path", "path": place_back, "is": "file"}],
                     before_test=[whole(1)], after_test=[whole(0)],
                     construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace", "old": {"saved": 1}, "new": {"saved": 0}}},
                     after_check=[whole(0)], needs=back, way_back={"none": "the row declares none: it is itself a reverse"},
                     output={"name": "note back {each.n}", "fields": {}})
    note = {"each": "place"}
    t17 = rowlib.row("change", "T17", g19.P[1],
                     thing={"role": "the note", "identity": "path", "place": note, "tracked": ["exists", "sha256"], "span": True,
                            "family": {"read": "files", "folder": vault, "glob": "*.md", "holding": L("OLD/"), "tree": True,
                                       "validators": {"path": "a path a shell line may hold"},
                                       "within": {"folder": vf, "output": "vault folder archived.path"}}},
                     planning_test=[{"read": "path", "path": note, "is": "file"}],
                     before_test=[text(note, L("OLD/"), present=True)], after_test=[text(note, L("OLD/"), present=False)],
                     construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace-all", "old": L("OLD/"), "new": L("NEW/")}},
                     after_check=[text(note, L("OLD/"), present=False)], needs=made, way_back={"reverse": v06},
                     reverse_inputs=[{"read": "file", "path": note, "type": "before-image", "label": "the note before"},
                                     {"read": "computed", "type": "after-image", "label": "the note after"},
                                     {"read": "value", "value": {"each": "rel"}, "type": "line", "label": "where it was taken from"}],
                     span={"placement": "in place", "ordered": True}, output={"name": "note repointed {each.n}", "fields": {}})
    return [t13, t14, t17]


NOTES = {"vault/other.md": "see [[OLD/x]]\n", "vault/proj/demo/_index.md": "status: active\nsee [[OLD/x]]\n",
         "vault/proj/demo/inside.md": "see [[OLD/y]] and [[NEW/z]]\n"}


class NotesBack(harness.Case):
    def sunset(self, label, index_phase=BACK2[1]):
        m = self.machine(label, label)
        for rel, body in NOTES.items():
            m.put("dev/" + rel, body)
        os.makedirs(m.path("dev", "vault", "arch"))
        rowlib.install(m, rowlib.lane("sunset", note_rows(index_phase), phases=g19.P), rowlib.lane("restore", [], phases=BACK2),
                       providers=g19.provs())
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        return m, looked

    def test_G24_6a_EV4_LOG2_a_C3s_computed_after_image_is_saved_as_its_reverses_input_before_the_effect(self):
        from sun_core import protected
        m, looked = self.sunset("a")
        run = looked.doc["run"]
        ways = dict((r["op"], r["way_back"]) for r in m.journal(run) if r["kind"] == "completion")
        members = sorted(op for op in ways if op.startswith("T17-"))
        self.assertEqual(len(members), 3)
        for op in members:
            self.assertTrue(ways[op]["offered"], (op, ways[op]))
            after = [i for i in ways[op]["inputs"] if i["type"] == "after-image"][0]
            saved = protected.read(m.world().fs, m.facts.run_dir(run), after).decode("utf-8")
            self.assertNotIn("OLD/", saved)
            self.assertIn("NEW/", saved)
        self.assertEqual(open(m.path("dev", "vault", "arch", "demo", "_index.md")).read(), "status: archived\nsee [[NEW/x]]\n")

    def test_G24_6b_RUN6_a_member_outside_its_within_folder_carries_its_whole_path_as_rel(self):
        m, looked = self.sunset("b")
        manifest = g20.manifest_of(m, looked.doc["run"])
        rels = sorted(o["reverse_inputs"][2]["value"]["literal"] for o in manifest["operations"] if o["id"].startswith("T17-"))
        self.assertEqual(rels, sorted([m.path("dev", "vault", "other.md"), "_index.md", "inside.md"]))
        outside = [o for o in manifest["operations"] if o["id"].startswith("T17-") and o["thing"]["place"] == L(m.path("dev", "vault", "other.md"))]
        self.assertEqual(len(outside), 1, "the note outside the moved folder is placed by its own path")

    def test_G24_6c_EV5_EV7_ORD4_the_restore_runs_its_reverses_by_the_lanes_phases_and_puts_every_note_back(self):
        m, looked = self.sunset("c")
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        for rel, body in NOTES.items():
            self.assertEqual(open(m.path("dev", rel)).read(), body, rel)
        self.assertFalse(os.path.exists(m.path("dev", "vault", "arch", "demo")))
