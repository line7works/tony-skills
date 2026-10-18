"""E16 slice 4, the lane's third part: V06, T17's way back, on part G24's (a) and (b), and its place in the restore (ORD-4,
ORD-5; G24-6 (c)).

Every test's name carries the row's id and the frame's rule. The rows are the lane's files as they ship
(`test_lane_set_lib`); slice 3's are stand-ins.
"""
import copy
import os

import harness
import test_lane_set_lib as lib

# the root index also links a note inside the old folder, so T17 repoints the root index after T16 has moved its line
SEE_ALSO = "- see also [[projects/demo-vault/plan]]\n"
NOTES = (("vault", "_index.md"), ("vault", "notes", "elsewhere.md"), ("vault", "notes", "unrelated.md"),
         ("vault", "projects", "demo-vault", "_index.md"), ("vault", "projects", "demo-vault", "plan.md"))


def finals(m, run_id):
    return dict((r["op"], r) for r in m.journal(run_id) if r["kind"] == "completion")


def records(m, run_id, way_back):
    """The way back's saved inputs, by type, as the protected records hold them."""
    from sun_core import protected
    out = {}
    for ref in way_back["inputs"]:
        out[ref["type"]] = protected.read(m.world().fs, m.facts.run_dir(run_id), ref).decode("utf-8")
    return out


class NotesBack(harness.Case):
    """V06 (rows-set 3.3): T17's way back, each note put back from its saved before-image where it still equals the saved
    after-image exactly once (EV-6), placed by its own path outside the moved folder and by the folder put back inside it."""

    def test_T17_V06_EV4_LOG2_G24_6a_6b_each_repointed_note_records_the_note_before_after_and_where_it_was_taken_from(self):
        m = lib.machine(self)
        index = lib.read(m, "vault", "projects", "demo-vault", "_index.md")
        before = {m.path("vault", "notes", "elsewhere.md"): lib.read(m, "vault", "notes", "elsewhere.md"),
                  "plan.md": lib.read(m, "vault", "projects", "demo-vault", "plan.md"),
                  # T14 marks the index file archived before T17's turn, so T17's before-image holds T14's change
                  "_index.md": index.replace("status: active\n", "status: archived\narchived: 2026-01-01\n")}
        now = {m.path("vault", "notes", "elsewhere.md"): ("vault", "notes", "elsewhere.md"),
               "plan.md": ("vault", "archive", "demo-vault", "plan.md"), "_index.md": ("vault", "archive", "demo-vault", "_index.md")}
        looked, went = lib.run(self, m)
        run = looked.doc["run"]
        done = dict((op, r) for op, r in finals(m, run).items() if op.startswith("T17-"))
        self.assertEqual(len(done), 3, sorted(done))
        seen = set()
        for op, record in done.items():
            self.assertTrue(record["way_back"]["offered"], (op, record["way_back"]))
            saved = records(m, run, record["way_back"])
            rel = saved["line"]          # outside the moved folder its whole path; inside it its path relative to the folder
            seen.add(rel)
            self.assertEqual(saved["before-image"], before[rel], op)
            self.assertEqual(saved["after-image"], lib.read(m, *now[rel]), "the after-image is the note as the swap left it")
        self.assertEqual(seen, set(before))

    def test_V06_EV5_EV6_ORD4_ORD5_G24_6c_the_restore_puts_every_note_back_byte_for_byte_inside_and_outside_the_folder(self):
        # a root index T17 also changes, after T16: on G25-5 the restore's look leaves V05's tests to its probe, which runs
        # once V06's phase is final (part 4; the fix round's machinery request 2)
        m = lib.machine(self)
        m.put("vault/_index.md", lib.read(m, "vault", "_index.md") + SEE_ALSO)
        before = dict((parts, lib.read(m, *parts)) for parts in NOTES)
        looked, went = lib.run(self, m)
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual(sorted(statuses[i] for i in statuses if i.startswith("T17-")), ["done"] * 4)
        rlooked, rwent = lib.run(self, m, "restore")
        rstatuses = m.statuses(rlooked.doc["run"])
        self.assertEqual(sorted(i for i in rstatuses if i.startswith("V06-")), ["V06-1", "V06-2", "V06-3", "V06-4"])
        self.assertEqual(set(rstatuses.values()), {"done"}, rstatuses)
        for parts in NOTES[1:]:
            self.assertEqual(lib.read(m, *parts), before[parts], os.path.join(*parts))
        # the root index: T17's change put back by V06 first, then T16's by V05 from T16's saved images (C1), byte for byte
        self.assertEqual(lib.read(m, "vault", "_index.md"), before[NOTES[0]])
        # the order: V06 in the phase that puts the vault folder back, V03 and V05 in the next (ORD-4: only phases and needs
        # order a restore's work, and nothing between them is a need)
        phases = dict((o["id"], o["phase"]) for o in lib.manifest(m, rlooked.doc["run"])["operations"])
        self.assertEqual(set(phases[i] for i in phases if i.startswith("V06-")) | {phases["V02"]}, {"putting back on this machine"})
        self.assertEqual({phases["V03"], phases["V05"]}, {"putting back the indexes"})

    def test_V06_V03_ORD4_ORD5_in_one_phase_with_no_need_between_them_V03_runs_first_and_V06_stops_foreign_on_the_index_file(self):
        """Said plainly: with V03 in V06's phase and no need between them, ORD-5 takes them in the manifest's order, the
        sunset's (T14 before T17), so V03 puts the status back first; the index file then no longer equals T17's saved
        after-image, which holds "status: archived", and V06's member for it stops the restore `foreign` (OP-5, OP-6)."""
        m = lib.machine(self)
        lane = lib.shipped_lane("sunset")
        t14 = [r for r in lane["rows"] if r["id"] == "T14"][0]
        t14["way_back"]["reverse"]["phase"] = "putting back on this machine"
        lib.install(m, sunset_lane=lane)
        looked, went = lib.run(self, m)
        member = [op for op, r in finals(m, looked.doc["run"]).items()
                  if op.startswith("T17-") and records(m, looked.doc["run"], r["way_back"])["line"] == "_index.md"][0]
        rlooked, rwent = lib.run(self, m, "restore", ending="stopped")
        self.assertIn("foreign", rwent.text)
        rstatuses = m.statuses(rlooked.doc["run"])
        self.assertEqual(rstatuses.get("V03"), "done")
        self.assertNotIn("V06-" + member.split("-", 1)[1], rstatuses)
        index = lib.read(m, "vault", "projects", "demo-vault", "_index.md")
        self.assertIn("status: active\n", index)
        self.assertIn("[[archive/demo-vault/plan]]", index, "the index file keeps T17's link: no way back ran on it")


if __name__ == "__main__":
    import unittest
    unittest.main()
