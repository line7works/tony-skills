"""E16 slice 4, the lane's own rows: sunset and restore (rows-set.md revision 3; contract section 10).

Every test's name carries the row's id and the frame's rule it rests on. The rows are the lane's files as they ship, in
the plugin's own `lifecycle/rows/`; the tools are the fakes of `fakes/set_tools.py` under fixture names, and slice 3's
rows and git reads are stand-ins (`test_lane_set_lib`). Each test runs the whole lane over its own fixture machine and
asserts by name what one row did: the files with their bytes, the fakes' states and call records, the journal's lines.
"""
import json
import os
import stat

import harness
import test_lane_set_lib as lib

L = lib.L


def journal(m, run_id, kind=None, op=None):
    return [r for r in m.journal(run_id) if (kind is None or r["kind"] == kind) and (op is None or r.get("op") == op)]


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def sunset_folder(m):
    return m.path("dev", "_archive", "demo.sunset-2026-01-01")


class SunsetAndRestore(harness.Case):
    """Rows of rows-set 3.2 and their reverses of 3.3, each by its planned effect and its way back."""

    def sunset(self, m=None, **more):
        m = m or lib.machine(self)
        looked, went = lib.run(self, m, **more)
        return m, looked, went

    def restore(self, m, ending="complete", **more):
        return lib.run(self, m, "restore", ending=ending, **more)

    # ---- T02a, T02: the archive folder and the sunset folder (A2 Q4; SEC-7) ----------------------------------------
    def test_T02a_T02_OP2_SEC7_the_archive_folder_where_missing_and_the_sunset_folder_owner_only(self):
        m, looked, went = self.sunset()
        self.assertEqual(mode(m.path("dev", "_archive")), 0o755)
        self.assertEqual(mode(sunset_folder(m)), 0o700)
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual((statuses["T02a"], statuses["T02"]), ("done", "done"))
        preview = lib.form(looked, "preview")
        self.assertIn("[T02] build: make %s, owner-only, for the copies; Not saved: files in the database provider's storage, "
                      "and GitHub's issues, pull requests and releases" % sunset_folder(m), preview)
        self.assertIn("[T02] done: Saved copies: %s; Not saved:" % sunset_folder(m), lib.form(went, "status"))

    def test_T02a_RUN7_an_archive_folder_already_there_is_not_applicable_already_there(self):
        m = lib.machine(self)
        os.makedirs(m.path("dev", "_archive"))
        looked = lib.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("not applicable (already there): make <path>", lib.form(looked, "preview"))
        self.assertNotIn("T02a", [o["id"] for o in lib.manifest(m, looked.doc["run"])["operations"]])
        self.assertEqual(lib.go(m, looked).ending, "complete")

    def test_T02_RUN7_a_second_sunset_of_one_project_on_one_date_stops_at_its_place(self):
        m = lib.machine(self)
        os.makedirs(sunset_folder(m))
        looked = lib.look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the place is taken by a thing this run did not make: row T02", looked.text)

    # ---- T05: the memory copy (E16-1; RK18; A151) ---------------------------------------------------------------
    def test_T05_KEEP1_A151_RK18_the_project_memory_store_copied_whole_owner_only_and_left_in_place(self):
        m, looked, went = self.sunset()
        copy = os.path.join(sunset_folder(m), "memory")
        self.assertEqual(mode(copy), 0o700)
        self.assertEqual(lib.read(m, os.path.relpath(os.path.join(copy, "notes", "one.md"), m.home)), "one\n")
        self.assertEqual(mode(os.path.join(copy, "MEMORY.md")), 0o600)
        self.assertTrue(os.path.isfile(os.path.join(lib.store_of(m), "MEMORY.md")), "the store is left in place")
        done = journal(m, looked.doc["run"], "completion", "T05")[0]
        self.assertTrue({"inventory", "sha256", "size"} <= set(done["keep"]), done["keep"])
        marks = [r for r in journal(m, looked.doc["run"], "step", "T05") if r.get("step") == "risk-mark"]
        self.assertEqual([r["risk"] for r in marks], ["RK18"])

    def test_T05_RUN7_without_the_memory_stores_capability_the_copy_is_not_applicable(self):
        m = lib.machine(self)
        looked = lib.look(m, caps=["routines"])
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("not applicable (not available on this harness): copy the project's memory store whole",
                      lib.form(looked, "preview"))

    # ---- T10a, T10b, V14b, V14a: each launch agent unloaded, its file moved, and back (A4 Q7; RK18; RK4) ------------
    def test_T10a_T10b_V14b_V14a_A4_RK18_each_launch_agent_unloaded_its_file_moved_and_both_put_back(self):
        m, looked, went = self.sunset()
        self.assertEqual(lib.fake(m, "launchctl")["loaded"], ["com.fixture.other"])
        moved = os.path.join(sunset_folder(m), "com.fixture.demo.plist")
        self.assertTrue(os.path.isfile(moved))
        self.assertFalse(os.path.exists(m.path("agents", "com.fixture.demo.plist")))
        self.assertTrue(os.path.isfile(m.path("agents", "com.fixture.other.plist")), "an agent not tied to the project stays")
        self.assertEqual([c["argv"][0] for c in lib.calls(m, "launchctl") if c["argv"][0] != "list"], ["unload"])
        self.assertEqual(lib.fake(m, "launchctl")["sets"], [{"do": "unload", "label": "com.fixture.demo"}])
        _rlooked, _rwent = self.restore(m)
        self.assertTrue(os.path.isfile(m.path("agents", "com.fixture.demo.plist")))
        self.assertFalse(os.path.exists(moved))
        self.assertEqual(sorted(lib.fake(m, "launchctl")["loaded"]), ["com.fixture.demo", "com.fixture.other"])

    def test_T10a_T10b_T11_ORD1_G21_9_two_members_each_with_its_own_reverse_and_every_one_put_back(self):
        m = lib.machine(self)
        m.put("agents/com.fixture.demo2.plist", lib.PLIST % ("com.fixture.demo2", m.path("dev", "demo", "two.sh")))
        lib.fake_state(m, "launchctl", loaded=["com.fixture.demo", "com.fixture.demo2", "com.fixture.other"])
        with open(m.path("shortcuts.txt"), "a") as fh:
            fh.write('alias dm2="cd %s"\n' % m.path("dev", "demo"))
        _m, looked, went = self.sunset(m)
        self.assertEqual(lib.fake(m, "launchctl")["loaded"], ["com.fixture.other"])
        self.assertEqual(lib.read(m, "shortcuts.txt"), 'alias other="cd /elsewhere"\n')
        rlooked, _rwent = self.restore(m)
        ids = [o["id"] for o in lib.manifest(m, rlooked.doc["run"])["operations"]]
        for rid in ("V14a-1", "V14a-2", "V14b-1", "V14b-2", "V13-1", "V13-2"):
            self.assertEqual(ids.count(rid), 1, ids)
        self.assertEqual(sorted(lib.fake(m, "launchctl")["loaded"]), ["com.fixture.demo", "com.fixture.demo2", "com.fixture.other"])
        self.assertEqual(sorted(os.listdir(m.path("agents"))), ["com.fixture.demo.plist", "com.fixture.demo2.plist", "com.fixture.other.plist"])
        self.assertEqual(lib.read(m, "shortcuts.txt"), 'alias other="cd /elsewhere"\nalias dm="cd %s"\nalias dm2="cd %s"\n'
                         % (m.path("dev", "demo"), m.path("dev", "demo")))

    def test_T10a_GOV1_a_launch_agent_whose_label_differs_from_its_file_name_stops_the_look(self):
        m = lib.machine(self)
        m.put("agents/com.fixture.demo.plist", lib.PLIST % ("com.fixture.another", m.path("dev", "demo", "run.sh")))
        looked = lib.look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row T10a-1", looked.text)
        self.assertEqual([c["argv"][0] for c in lib.calls(m, "launchctl") if c["argv"][0] != "list"], [], "nothing unloaded")

    # ---- T10c, V14c: each harness routine disabled, its definition saved, and enabled again (RK18; A6 O2) -----------
    def test_T10c_V14c_RK18_A6_each_routine_disabled_its_definition_saved_first_and_the_same_id_enabled_again(self):
        from sun_core import protected
        m, looked, went = self.sunset()
        routines = lib.fake(m, "sun-adapter")["routines"]
        self.assertEqual((routines["r-one"]["state"], routines["r-two"]["state"]), ("disabled", "active"))
        start = journal(m, looked.doc["run"], "start", "T10c-custom-1")[0]
        run_dir = m.facts.run_dir(looked.doc["run"])
        saved = [protected.read(m.world().fs, run_dir, ref).decode("utf-8") for ref in start["inputs"]]
        self.assertEqual([ref["type"] for ref in start["inputs"]], ["definition", "held field"])
        self.assertEqual(saved, ["nightly build, every night\n", "r-one"])
        self.assertNowhere("r-one", went)
        self.assertNotIn("r-one", lib.form(went, "status"))
        self.restore(m)
        self.assertEqual(lib.fake(m, "sun-adapter")["sets"], [{"do": "routine-disable", "id": "r-one"},
                                                             {"do": "routine-enable", "id": "r-one"}])
        self.assertEqual(sorted(lib.fake(m, "sun-adapter")["routines"]), ["r-one", "r-two"], "no new routine is made")

    def test_T10c_RUN7_without_the_routines_capability_the_row_is_not_applicable_with_his_step(self):
        m = lib.machine(self)
        looked = lib.look(m, caps=["memory stores"])
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("not available on this harness", lib.form(looked, "preview"))

    # ---- T10d, V14d: the project's crontab lines, whole table saved, put back only where it stands (RK18; A147; EV-6) -
    def test_T10d_V14d_RK18_A147_the_crontab_lines_taken_out_the_whole_table_saved_and_put_back(self):
        from sun_core import protected
        m = lib.machine(self)
        table = lib.fake(m, "crontab")["table"]
        _m, looked, went = self.sunset(m)
        self.assertEqual(lib.fake(m, "crontab")["table"], "0 1 * * * other\n")
        given = [c for c in lib.calls(m, "crontab") if c["argv"] != ["-l"]]
        self.assertEqual([(c["text"], c["mode"]) for c in given], [("0 1 * * * other\n", "0o600")])
        start = journal(m, looked.doc["run"], "start", "T10d")[0]
        run_dir = m.facts.run_dir(looked.doc["run"])
        self.assertEqual([protected.read(m.world().fs, run_dir, r).decode("utf-8") for r in start["inputs"]],
                         [table, "0 1 * * * other\n"])
        self.assertNotIn("/run.sh", lib.form(went, "status") + went.text, "the table is never shown")
        self.restore(m)
        self.assertEqual(lib.fake(m, "crontab")["table"], table)

    def test_V14d_EV6_a_crontab_changed_since_the_sunset_where_its_table_no_longer_stands_is_not_put_back(self):
        m, _looked, _went = self.sunset()
        lib.fake_state(m, "crontab", table="0 2 * * * other, edited\n")
        looked, went = self.restore(m, ending=None)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("V14d", went.text)
        self.assertEqual(lib.fake(m, "crontab")["table"], "0 2 * * * other, edited\n", "nothing changed")

    # ---- T11, V13: the shortcut line (v1 Phase 4; RK2, RK5, RK13) ---------------------------------------------------
    def test_T11_V13_RK2_RK5_the_shortcut_line_removed_its_line_saved_and_put_back_at_the_end(self):
        m, looked, went = self.sunset()
        self.assertEqual(lib.read(m, "shortcuts.txt"), 'alias other="cd /elsewhere"\n')
        self.restore(m)
        self.assertEqual(lib.read(m, "shortcuts.txt"), 'alias other="cd /elsewhere"\nalias dm="cd %s"\n' % m.path("dev", "demo"))

    # ---- T12, V01: the repository (v1 Phase 4; RK4) ---------------------------------------------------------------
    def test_T12_V01_RK4_the_repository_moved_to_the_archive_and_back(self):
        m, looked, went = self.sunset()
        self.assertFalse(os.path.exists(m.path("dev", "demo")))
        self.assertEqual(lib.read(m, "dev", "_archive", "demo", "README.md"), "# demo\n")
        self.restore(m)
        self.assertEqual(lib.read(m, "dev", "demo", "README.md"), "# demo\n")
        self.assertFalse(os.path.exists(m.path("dev", "_archive", "demo")))

    def test_T12_RUN7_an_archived_repository_of_the_same_name_stops_the_look(self):
        m = lib.machine(self)
        os.makedirs(m.path("dev", "_archive", "demo"))
        looked = lib.look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row T12", looked.text)

    # ---- T13a, T13, V02: the vault folder (v1 Phase 1) ------------------------------------------------------------
    def test_T13a_T13_V02_RK4_the_vault_folder_moved_into_the_archive_folder_made_for_it_and_back_the_tombstone_kept(self):
        m, looked, went = self.sunset()
        self.assertEqual(mode(m.path("vault", "archive")), 0o755)
        self.assertFalse(os.path.exists(m.path("vault", "projects", "demo-vault")))
        self.assertTrue(os.path.isfile(m.path("vault", "archive", "demo-vault", "plan.md")))
        self.restore(m)
        tomb = "_sunset-%s.md" % looked.doc["run"]
        self.assertTrue(os.path.isfile(m.path("vault", "projects", "demo-vault", tomb)), "the tombstone stays in it")

    # ---- T14, V03: the index file's status (v1 Phase 1; EV-6) -------------------------------------------------------
    def test_T14_V03_EV6_the_index_files_status_archived_with_its_date_and_back_to_active(self):
        m = lib.machine(self)
        before = lib.read(m, "vault", "projects", "demo-vault", "_index.md")
        # the note also links the old folder, so T17 repoints that link and its V06 puts it back, before V03's phase
        # (part 3); T14's own lines are the status lines
        repointed = before.replace("[[projects/demo-vault/plan]]", "[[archive/demo-vault/plan]]")
        self.sunset(m)
        self.assertEqual(lib.read(m, "vault", "archive", "demo-vault", "_index.md"),
                         repointed.replace("status: active\n", "status: archived\narchived: 2026-01-01\n"))
        self.restore(m)
        self.assertEqual(lib.read(m, "vault", "projects", "demo-vault", "_index.md"), before)

    # ---- T16, V05: the root index line under ## Archived (v1 Phase 1 step 4; G19-14) ---------------------------------
    def test_T16_V05_EV6_the_root_index_line_moved_under_archived_repointed_and_back_between_its_neighbours(self):
        m = lib.machine(self)
        self.sunset(m)
        self.assertEqual(lib.read(m, "vault", "_index.md"),
                         "# Index\n## Active\n- [[projects/other/_index|other]]\n## Archived\n- [[archive/demo-vault/_index|demo]]\n")
        self.restore(m)
        # V05 puts T16's saved before-image back whole (the fix round, C1), the heading T16 added with it
        self.assertEqual(lib.read(m, "vault", "_index.md"),
                         "# Index\n## Active\n- [[projects/demo-vault/_index|demo]]\n- [[projects/other/_index|other]]\n")

    # ---- T18, V07: the home memory note (v1 Phase 2) ----------------------------------------------------------------
    def test_T18_V07_EV6_the_home_memory_note_marked_archived_and_back(self):
        m = lib.machine(self)
        before = lib.read(m, "mem", "home", "project_demo_notes.md")
        self.sunset(m)
        self.assertEqual(lib.read(m, "mem", "home", "project_demo_notes.md"),
                         before.replace("name: demo-vault\n", "name: demo-vault\nstatus: archived\narchived: 2026-01-01\n"))
        self.restore(m)
        self.assertEqual(lib.read(m, "mem", "home", "project_demo_notes.md"), before)

    def test_T18_RUN7_without_the_memory_stores_capability_the_note_is_not_applicable(self):
        m = lib.machine(self)
        looked = lib.look(m, caps=["routines"])
        self.assertIn("not applicable (not available on this harness): mark the home memory note archived", lib.form(looked, "preview"))

    # ---- T30, V30: the run's last record (A4; KEEP-5; EV-7) ----------------------------------------------------------
    def test_T30_KEEP5_A6_the_tombstone_under_v1s_head_lines_saying_how_to_restore(self):
        m, looked, went = self.sunset()
        path = m.path("vault", "archive", "demo-vault", "_sunset-%s.md" % looked.doc["run"])
        text = open(path).read()
        self.assertTrue(text.startswith("---\ncreated: 2026-01-01\nsource: sun-v2\ntype: sunset\nstatus: archived\n"
                                        "tags: [meta, archived]\n---\n\n# Sunset: demo\n\n- Date: 2026-01-01\n"
                                        "- Reason: %s\n\n" % lib.DESCRIPTION), text[:400])
        self.assertIn("To restore: summon restore with this project's names on this machine", text)
        self.assertIn("[T10d] done", text)
        self.assertEqual(mode(path), 0o644)

    def test_V30_KEEP5_EV7_the_restores_entry_beside_the_tombstone(self):
        m, slooked, _went = self.sunset()
        looked, went = self.restore(m)
        path = m.path("vault", "projects", "demo-vault", "_restore-%s.md" % looked.doc["run"])
        self.assertTrue(open(path).read().startswith("---\ncreated: 2026-01-01\nsource: sun-v2\ntype: restore\n---\n\n# Restore: demo\n"))
        self.assertTrue(os.path.isfile(m.path("vault", "projects", "demo-vault", "_sunset-%s.md" % slooked.doc["run"])))
        self.assertTrue(os.path.isdir(sunset_folder(m)), "the sunset folder stays")


class TheLook(harness.Case):
    """Rows-set section 4: G8, the reason, G10's loose ends; section 5: the hand-off prompt."""

    def test_G8_RUN5_dirty_or_unpushed_work_asks_the_lanes_question_unless_as_is_or_the_layer_is_dropped(self):
        cases = ((dict(clean=False), {}, "refused"), (dict(untracked=True), {}, "refused"), (dict(unpushed=2), {}, "refused"),
                 (dict(clean=False), {"flags": {"archive_as_is": True}}, "preview"),
                 (dict(clean=False), {"drop_layers": ["repository"]}, "preview"), ({}, {}, "preview"))
        for n, (git, more, ending) in enumerate(cases):
            with self.subTest(git=git, more=more):
                m = lib.machine(self, "g%d" % n)
                lib.fake_state(m, "git", **git)
                looked = lib.look(m, **more)
                self.assertEqual(looked.ending, ending, looked.text)
                asked = "The repository has uncommitted changes or unpushed commits." in looked.text
                self.assertEqual(asked, ending == "refused")

    def test_G10_RUN8_a_hosting_config_file_in_the_repository_is_a_loose_end_in_the_preview_never_acted_on(self):
        m = lib.machine(self)
        m.put("dev/demo/netlify.toml", "[build]\n")
        m.put("dev/demo/wrangler.jsonc", "{}\n")
        looked, went = lib.run(self, m)
        preview = lib.form(looked, "preview")
        for name in ("netlify.toml", "wrangler.jsonc"):
            self.assertIn("loose end, yours to handle, never acted on: %s in %s" % (name, m.path("dev", "demo")), preview)
        for name in ("wrangler.toml", "fly.toml", "render.yaml"):
            self.assertNotIn(name, preview)
        self.assertEqual(lib.read(m, "dev", "_archive", "demo", "netlify.toml"), "[build]\n")

    def test_FORM1_G21_11_the_hand_off_prompt_at_a_complete_ending_a_layer_the_run_lacked_left_out(self):
        for drop, want in (([], True), (["schedules"], False)):
            with self.subTest(drop=drop):
                m = lib.machine(self, "h%d" % len(drop))
                looked, went = lib.run(self, m, drop_layers=drop)
                handoff = lib.form(went, "handoff")
                self.assertTrue(handoff.startswith('Heads up: I have sunset (archived) my project "demo" as of 2026-01-01.\n'
                                                   "Reason: %s.\n" % lib.DESCRIPTION), handoff)
                self.assertIn("- Vault: moved to archive/demo-vault/ (status: archived)\n", handoff)
                self.assertIn("- Database: backed up, not paused\n", handoff)
                self.assertEqual("- Scheduled crontab lines: taken out" in handoff, want)
                self.assertNotIn("Notion", handoff)
                self.assertTrue(lib.form(went, "summary").startswith("SUNSET COMPLETE: demo\nSUNSET STATUS\n"))


if __name__ == "__main__":
    import unittest
    unittest.main()
