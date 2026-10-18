"""E16 slice 4, the lane's second part: the rows the first part stopped on, built on part G23's mechanisms, and the lane's
own items of its second brief (T17, T19 and V08, T10d with no table, T10c's capability, the restore summons).

Every test's name carries the row's id or the item, and the frame's rule. The rows are the lane's files as they ship
(`test_lane_set_lib`); slice 3's are stand-ins.
"""
import json
import os

import harness
import test_lane_set_lib as lib

OUTSIDE = "links [[projects/demo-vault/_index]] and [[archive/old/_index]]\n"
PLAN = "the plan, from [[projects/demo-vault/_index]]\n"
MEMORY_INDEX = "- [Demo](project_demo_notes.md) the demo\n- [Other](project_other.md) other\n"


def manifest_ops(m, run_id):
    return dict((o["id"], o) for o in lib.manifest(m, run_id)["operations"])


def finals(m, run_id):
    return dict((r["op"], r) for r in m.journal(run_id) if r["kind"] == "completion")


class NotesRepointed(harness.Case):
    """T17 (rows-set 3.2; the control room's reading of Question 3): each note under the vault holding the old folder's
    path, made safe by `a path a shell line may hold`; a note inside the moved folder placed by the move's output (RUN-6)."""

    def test_T17_RUN6_SEC1_Q3_each_note_linking_the_old_folder_repointed_inside_the_moved_folder_and_outside_it(self):
        m = lib.machine(self)
        looked, went = lib.run(self, m)
        run = looked.doc["run"]
        self.assertEqual(lib.read(m, "vault", "notes", "elsewhere.md"),
                         "links [[archive/demo-vault/_index]] and [[archive/old/_index]]\n", "a link already elsewhere is kept")
        self.assertEqual(lib.read(m, "vault", "archive", "demo-vault", "plan.md"), "the plan, from [[archive/demo-vault/_index]]\n")
        self.assertIn("see [[archive/demo-vault/plan]]\n", lib.read(m, "vault", "archive", "demo-vault", "_index.md"))
        self.assertEqual(lib.read(m, "vault", "notes", "unrelated.md"), "nothing here\n")
        ops = manifest_ops(m, run)
        family = sorted(i for i in ops if i.startswith("T17-"))
        self.assertEqual(len(family), 4, family)
        places = dict((ops[i]["thing"]["place"].get("literal") or json.dumps(ops[i]["thing"]["place"], sort_keys=True), i)
                      for i in family)
        # outside the moved folder: the path as it stands; inside it: the move's output and the path relative to it
        self.assertIn(m.path("vault", "notes", "elsewhere.md"), places)
        self.assertIn(m.path("vault", "_index.md"), places)
        self.assertIn(json.dumps({"path": [{"output": "vault folder archived.path"}, {"literal": "plan.md"}]}, sort_keys=True), places)
        statuses = m.statuses(run)
        # the root index: T16 moved and repointed its one line first, so at its turn the note no longer links the old folder
        self.assertEqual(statuses[places[m.path("vault", "_index.md")]], "already so")
        self.assertEqual(sorted(statuses[i] for i in family), ["already so", "done", "done", "done"])
        self.assertIn("[%s] change: repoint the links to the old vault folder in %s" % (places[m.path("vault", "notes", "elsewhere.md")],
                                                                                    m.path("vault", "notes", "elsewhere.md")),
                      lib.form(looked, "preview"))
        # its way back, V06 (part 3, on G24-6 (a) and (b)), is offered for every note it repointed
        for i in family:
            if statuses[i] == "done":
                self.assertTrue(finals(m, run)[i]["way_back"]["offered"], i)


class MemoryIndexArchived(harness.Case):
    """T19 and V08 (rows-set 3.2, 3.3) on G23-14: the line stands under `## Archived`, read as the heading and the held line
    together, so the moved line is told from the unmoved one."""

    def test_T19_V08_G23_14_EV6_the_memory_index_line_moved_under_archived_and_back_between_its_neighbours(self):
        m = lib.machine(self)
        looked, went = lib.run(self, m)
        self.assertEqual(lib.read(m, "mem", "home", "MEMORY.md"),
                         "- [Other](project_other.md) other\n## Archived\n- [Demo](project_demo_notes.md) the demo\n")
        self.assertEqual(m.statuses(looked.doc["run"])["T19-1"], "done")
        self.assertNotIn("the demo", json.dumps(lib.manifest(m, looked.doc["run"])), "the line is held, never in the manifest")
        self.assertNowhere("- [Demo](project_demo_notes.md)", went)
        self.assertTrue(finals(m, looked.doc["run"])["T19-1"]["way_back"]["offered"])
        rlooked, rwent = lib.run(self, m, "restore")
        self.assertEqual(m.statuses(rlooked.doc["run"])["V08-1"], "done")
        self.assertEqual(lib.read(m, "mem", "home", "MEMORY.md"), MEMORY_INDEX + "## Archived\n")      # the heading stays (G19-14)

    def test_T19_RUN7_G23_14_a_line_already_under_archived_is_already_so_and_nothing_is_moved(self):
        m = lib.machine(self)
        archived = "- [Other](project_other.md) other\n## Archived\n- [Demo](project_demo_notes.md) the demo\n"
        m.put("mem/home/MEMORY.md", archived)
        looked, went = lib.run(self, m)
        self.assertNotIn("T19-1", manifest_ops(m, looked.doc["run"]))
        self.assertEqual(lib.read(m, "mem", "home", "MEMORY.md"), archived)

    def test_T19_RUN7_a_line_under_another_heading_is_moved_under_archived(self):
        m = lib.machine(self)
        m.put("mem/home/MEMORY.md", "## Live\n- [Demo](project_demo_notes.md) the demo\n## Archived\n- [Old](project_old.md) old\n")
        lib.run(self, m)
        self.assertEqual(lib.read(m, "mem", "home", "MEMORY.md"),
                         "## Live\n## Archived\n- [Demo](project_demo_notes.md) the demo\n- [Old](project_old.md) old\n")


class NoCrontab(harness.Case):
    """MR6 on G23-16 (Question 4, the control room's reading): an account with no crontab is T10d's `already so`."""

    def test_T10d_RUN7_G23_16_an_account_with_no_crontab_is_already_so_and_no_table_is_written(self):
        m = lib.machine(self)
        lib.fake_state(m, "crontab", table=None)
        looked, went = lib.run(self, m)
        run = looked.doc["run"]
        self.assertNotIn("T10d", manifest_ops(m, run))
        self.assertIn("T10d", [s.get("row") for s in lib.manifest(m, run).get("already_so") or []])
        self.assertEqual([c["argv"] for c in lib.calls(m, "crontab")], [["-l"]] * len(lib.calls(m, "crontab")), "no table replaced")
        self.assertIsNone(lib.fake(m, "crontab").get("table"))


class RoutinesCapability(harness.Case):
    """MR7 on G23-3: T10c's routines read is made only after its capability is settled."""

    def test_T10c_OP8_G23_3_a_harness_without_routines_reads_no_routine_and_lists_the_row_not_applicable(self):
        m = lib.machine(self)
        looked, went = lib.run(self, m, caps=["memory stores"])
        manifest = lib.manifest(m, looked.doc["run"])
        self.assertEqual(lib.calls(m, "sun-adapter"), [], "the adapter was asked on a harness that lacks the capability")
        self.assertIn(("T10c", "not available on this harness"), [(n["row"], n["reason"]) for n in manifest["not_applicable"]])
        self.assertEqual(sorted(r["state"] for r in lib.fake(m, "sun-adapter")["routines"].values()), ["active", "active"])


class RestoreSummons(harness.Case):
    """Question 6, done by G23-21: the restore summons is `sunset-v2`'s, and it reaches this lane's restore file."""

    def test_Q6_C2_RUN1_G23_21_the_restore_summons_is_sunset_v2s_and_reaches_this_lanes_restore_rows(self):
        from sun_core import lanes
        with open(os.path.join(harness.LIFECYCLE, "skills.json")) as fh:
            skills = json.load(fh)
        self.assertEqual(skills["summonses"]["restore"], "sunset-v2")
        folder = dict((s["name"], s["folder"]) for s in skills["skills"])["sunset-v2"]
        with open(os.path.join(harness.PLUGIN, folder, "SKILL.md")) as fh:
            self.assertIn("restore", fh.read())

        class Plain(object):
            rows_root = None
        lane = lanes.lane(Plain(), "restore")
        self.assertEqual(lane, lib.read_json(harness.LIFECYCLE, "rows", "restore", "lane.json"))
        self.assertEqual(lane["kind"], "restore")
        self.assertIn("V30", [r["id"] for r in lane["rows"]])


if __name__ == "__main__":
    import unittest
    unittest.main()
