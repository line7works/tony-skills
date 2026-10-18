"""E16 slice 4: the lane brief's required items, the seams this lane provides, and the lane's files as shipped (ROW-3).

Each test's name carries the item or the row and the frame's rule. The lane's files are read as they ship
(`test_lane_set_lib`); slice 3's are stand-ins.
"""
import copy
import json
import os

import harness
import rowlib
import test_lane_set_lib as lib

SKILL = os.path.join(harness.PLUGIN, "skills", "sunset-v2", "SKILL.md")


def json_of(m, run_id):
    """Every journal record, the manifests and the forms of a run, as text: what a value must not stand in."""
    run_dir = m.facts.run_dir(run_id)
    journal = os.path.join(run_dir, "journal.jsonl")
    out = [open(journal).read()] if os.path.exists(journal) else []      # a look that ended before any preview has none
    for name in sorted(os.listdir(run_dir)):
        if name.startswith("manifest"):
            out.append(open(os.path.join(run_dir, name)).read())
    forms = os.path.join(run_dir, "forms")
    for name in sorted(os.listdir(forms)):
        out.append(open(os.path.join(forms, name)).read())
    return "\n".join(out)


class Shipped(harness.Case):
    """The lane's files, as they ship under the plugin's own `lifecycle/rows/`, admitted by `rows.py` (ROW-1, ROW-3)."""

    def test_ROW1_ROW3_both_lanes_as_shipped_are_admitted_with_their_checklists_answered_and_their_schemas_held(self):
        from sun_core import plan, rows, schemas
        decls = lib.providers()
        for kind in ("sunset", "restore"):
            with self.subTest(kind=kind):
                lane = lib.shipped_lane(kind)
                # G23-17 (the first part's machinery request 4): a family reverse takes its member's suffix from the tool, so
                # the lane writes its reverses' ids plain and the lane schema holds every row
                self.assertEqual(schemas.errors("lane", lane), [])
                self.assertEqual([r["id"] for r in lane["rows"] if "{each." in json.dumps((r.get("way_back") or {}) if
                                                                                         isinstance(r.get("way_back"), dict) else {})
                                  and "{each." in str((r["way_back"].get("reverse") or {}).get("id"))], [])
                self.assertEqual(rows.checklist_findings(lane), [])
                self.assertEqual(plan.admit_all(lane, plan.expand(lane, decls), decls), [])
                for item in lane["checklist"]:
                    self.assertIn(list(item["answered_by"])[0], ("row", "form_line", "reason"))
        for name, decl in lib.shipped_providers().items():
            with self.subTest(provider=name):
                self.assertEqual(schemas.errors("provider", decl), [])
                self.assertEqual([c["tool"] for c in decl["commands"].values() if c["tool"].startswith("fixture-")], [])

    def test_ROW3_an_unanswered_item_of_the_shipped_checklist_fails_the_admission_naming_it(self):
        from sun_core import rows
        lane = lib.shipped_lane("sunset")
        lane["checklist"][3]["answered_by"] = {"row": "T99"}
        self.assertEqual(rows.checklist_findings(lane), [{"item": lane["checklist"][3]["item"], "finding": "names a row that does not exist"}])

    def test_SEC3_the_tests_declarations_are_the_shipped_ones_with_only_the_tool_renamed(self):
        for name, decl in lib.shipped_providers().items():
            fixture = lib.providers()[name]
            for command, spec in decl["commands"].items():
                self.assertEqual(dict(fixture["commands"][command], tool=spec["tool"]), spec)
                self.assertEqual(fixture["commands"][command]["tool"], "fixture-" + spec["tool"])
        self.assertEqual(sorted(lib.shipped_providers()["launchd"]["commands"]), ["label", "listed", "load", "unload"])
        self.assertEqual(sorted(lib.shipped_providers()["cron"]["commands"]), ["read", "replace"])

    def test_rows_rise_3_1_adapter_canary_as_slice_2_writes_it(self):
        canary = lib.shipped_providers()["adapter"]["commands"]["canary"]
        self.assertEqual((canary["via"], canary["time_limit"], canary["effects"], canary["exits"]), ("adapter", 120, 0, {"0": "success"}))
        self.assertEqual(canary["fields"], [{"name": "match", "place": ["match"], "type": "state", "disposition": "fixed",
                                             "list": ["same", "differs"], "required_in": ["success"]}])
        self.assertEqual(canary["definite"], {"success": ["success"], "refusals": []})


class RequiredItems(harness.Case):
    # ---- item 1: S10, the owner's tracker ruling (A152) ---------------------------------------------------------------
    def test_item1_S10_E16_1_A152_the_skill_tells_claude_to_mention_other_trackers_in_its_summary_and_act_on_none(self):
        with open(SKILL) as fh:
            text = fh.read()
        line = ("- In the summary you give the owner, mention any other tracker you notice in the repository, beyond the hosting "
                "config files the tool lists; add no tool step for it and do not act on it.\n")
        self.assertEqual(text.count(line), 1)
        self.assertEqual(text.count("other tracker"), 1)
        self.assertNotIn("Notion", text)

    # ---- item 2: S13, a shortcut name that fails its validator (SEC-1) --------------------------------------------------
    def test_item2_S13_SEC1_T11_a_shortcut_name_failing_its_validator_is_in_no_form_output_or_journal_record(self):
        bad = "Bad!Name"
        m = lib.machine(self, shortcut=bad)
        looked, went = lib.run(self, m)
        run = looked.doc["run"]
        self.assertNotIn(bad, json_of(m, run))
        self.assertNowhere(bad, looked)
        self.assertNowhere(bad, went)
        preview = lib.form(looked, "preview")
        # G23-18 (the first part's machinery request 5): the held name's member records no way back, "an input is missing",
        # and the preview says so (rows-set T11 entry 15; EV-4)
        self.assertIn("[T11-1] change: remove the shortcut #1 that opens the project's folder, its line saved first; no way back "
                      "can be recorded: an input is missing", preview)
        status = lib.form(went, "status")
        self.assertIn("[T11-1] done: removed the shortcut #1; its line and its name are in the private files below", status)
        self.assertIn("the shortcut's name: %s" % os.path.join(m.facts.run_dir(run), "protected"), status)
        self.assertEqual(lib.read(m, "shortcuts.txt"), 'alias other="cd /elsewhere"\n')
        done = [r for r in m.journal(run) if r["kind"] == "completion" and r["op"] == "T11-1"][0]
        self.assertEqual(done["way_back"], {"offered": False, "reason": "an input is missing"})
        # the restore offers no way back for it, lists it with that reason, and the held name reaches no check and no form
        rlooked = lib.look(m, "restore")
        self.assertEqual(rlooked.ending, "preview", rlooked.text)
        rmanifest = lib.manifest(m, rlooked.doc["run"])
        self.assertNotIn("V13-1", [o["id"] for o in rmanifest["operations"]])
        self.assertIn("not offered by this restore (an input is missing): remove the shortcut #1 that opens the project's folder",
                      lib.form(rlooked, "preview"))
        self.assertNowhere(bad, rlooked)
        self.assertNotIn(bad, json_of(m, rlooked.doc["run"]))

    def test_item2_MR1_G23_19_SEC1_T11_a_name_rows_set_validator_passes_is_shown_and_offered_back(self):
        # `a shortcut name` (rows-set 8 item 1) passes `Dm_2`, which rise's `a shortcut's name` held
        m = lib.machine(self, shortcut="Dm_2")
        looked, went = lib.run(self, m)
        self.assertIn("[T11-1] change: remove the shortcut Dm_2 that opens the project's folder, its line saved first\n",
                      lib.form(looked, "preview"))
        rlooked, rwent = lib.run(self, m, "restore")
        self.assertIn("[V13-1] change: the shortcut Dm_2 back at the end of the shortcut file; open a new tab", lib.form(rlooked, "preview"))
        self.assertEqual(lib.read(m, "shortcuts.txt"), 'alias other="cd /elsewhere"\nalias Dm_2="cd %s"\n' % m.path("dev", "demo"))

    # ---- item 3: T10d's reverse inputs and T17's tree read, through this lane's rows (G22-7) -----------------------------
    def test_item3_G22_7_LOG2_T10d_the_commands_protected_text_is_the_before_image_and_the_computed_table_the_after_image(self):
        from sun_core import protected
        m = lib.machine(self)
        table = lib.fake(m, "crontab")["table"]
        looked, went = lib.run(self, m)
        start = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "start" and r["op"] == "T10d"][0]
        refs = start["inputs"]
        self.assertEqual([(r["type"], r["label"]) for r in refs], [("before-image", "the crontab before"), ("after-image", "the crontab after")])
        run_dir = m.facts.run_dir(looked.doc["run"])
        before, after = [protected.read(m.world().fs, run_dir, r).decode("utf-8") for r in refs]
        self.assertEqual(before, table)
        sent = [c["text"] for c in lib.calls(m, "crontab") if c["argv"] != ["-l"]]
        self.assertEqual(sent, [after], "the after-image is the very table the replace was handed")
        done = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion" and r["op"] == "T10d"][0]
        self.assertTrue(done["way_back"]["offered"])

    def shipped_t17(self):
        return [r for r in lib.shipped_lane("sunset")["rows"] if r["id"] == "T17"][0]

    def test_item3_Q3_G22_7_G23_15_RUN6_T17_the_tree_read_finds_notes_at_every_depth_each_path_safe_inside_ones_by_rel(self):
        from sun_core import plan
        m = lib.machine(self)
        m.put("vault/deep/a/b/note.md", "see [[projects/demo-vault/_index]]\n")
        row = self.shipped_t17()
        self.assertTrue(row["thing"]["family"]["tree"])
        self.assertEqual(row["thing"]["family"]["validators"], {"path": "a path a shell line may hold"})
        looked = lib.look(m)                     # a look of the shipped lane, for a run directory the records may rest in
        self.assertEqual(looked.ending, "preview", looked.text)
        look = plan.Look({"description": "x"}, list(lib.NAMES), m.facts.locations(m.world().fs), [], looked.doc["run"])

        class Session(object):
            pass
        session = Session()
        session.world = m.world()
        session.run_dir = m.facts.run_dir(looked.doc["run"])
        from sun_core import screen
        session.register = screen.Screen()
        members = plan.expand_family(session, look, row)
        self.assertEqual(len(members), 5, [mm["id"] for mm in members])
        # Question 3, the control room's reading: each path made safe by `a path a shell line may hold`, so no place is held;
        # a note outside the moved folder is placed where it stands, and one inside it by the move's output and its path
        # relative to the folder (G21-12, G23-15's `rel`)
        vf = m.path("vault", "projects", "demo-vault")
        places = {}
        for member in members:
            place = member["thing"]["place"]
            self.assertNotIn("record", json.dumps(place), member["id"])
            places[place.get("literal") or json.dumps(place, sort_keys=True)] = member["id"]
        inside = dict((json.dumps({"path": [{"output": "vault folder archived.path"}, {"literal": rel}]}, sort_keys=True), rel)
                      for rel in ("_index.md", "plan.md"))
        self.assertEqual(sorted(places), sorted([m.path("vault", "_index.md"), m.path("vault", "deep", "a", "b", "note.md"),
                                                 m.path("vault", "notes", "elsewhere.md")] + list(inside)))
        self.assertTrue(all(not p.startswith(vf) for p in places if not p.startswith("{")))


class Seams(harness.Case):
    """Item 5: the outputs this lane provides, by the names and fields rows-set section 7 gives them, each made with its field
    (ORD-1): `sunset folder` {path}, `repository archived` {path}, `repository moved`, `repository back` {path}."""

    def bound(self, m, run_id):
        from sun_core import manifest as manifestmod, rundir, state as statemod
        fs = m.world().fs
        journal = rundir.check(fs, m.facts.run_dir(run_id))
        _n, doc = manifestmod.in_force(fs, m.facts.run_dir(run_id), journal)
        return statemod.State(doc, journal).outputs

    def test_item5_ORD1_sunset_folder_repository_archived_repository_moved_and_repository_back_are_made_with_their_fields(self):
        m = lib.machine(self)
        looked, went = lib.run(self, m)
        outputs = self.bound(m, looked.doc["run"])
        self.assertEqual(outputs["sunset folder"], {"path": m.path("dev", "_archive", "demo.sunset-2026-01-01")})
        self.assertEqual(outputs["repository archived"], {"path": m.path("dev", "_archive", "demo")})
        statuses = m.statuses(looked.doc["run"])
        # `repository moved` has no field: its check passed, and the stand-in of slice 3's T21, which needs it at `passed`, ran
        self.assertEqual((statuses["T12m"], statuses["T20"], statuses["T21"], statuses["T03"]), ("passed", "done", "done", "passed"))
        t21 = [o for o in lib.manifest(m, looked.doc["run"])["operations"] if o["id"] == "T21"][0]
        self.assertEqual([n["output"] for n in t21["needs"]], ["repository moved"])
        rlooked, rwent = lib.run(self, m, "restore")
        routputs = self.bound(m, rlooked.doc["run"])
        self.assertEqual(routputs["repository back"], {"path": m.path("dev", "demo")})
        self.assertEqual(m.statuses(rlooked.doc["run"])["V10"], "done")


if __name__ == "__main__":
    import unittest
    unittest.main()
