"""E16 slice 4, the lane's fix round: the outside reviewer's code check, findings C1 and C3, and C2 on G25-4's `under` read
(part 4).

Every test's name carries the finding, the row's id and the frame's rule. The rows are the lane's files as they ship
(`test_lane_set_lib`), slice 3's rows among them since the join (no stand-in).
"""
import harness
import test_lane_set_lib as lib

INDEX = ("vault", "_index.md")
NOTE = ("vault", "projects", "demo", "_index.md")
MEMORY_NOTE = ("mem", "home", "project_demo_notes.md")


def way_back(m, run_id, op):
    for r in m.journal(run_id):
        if r["kind"] == "completion" and r["op"] == op:
            return r["way_back"]
    return None


def images(m, run_id, op):
    """The way back's saved before-image and after-image, as the protected records hold them."""
    from sun_core import protected
    out = {}
    for ref in way_back(m, run_id, op)["inputs"]:
        if ref["type"] in ("before-image", "after-image"):
            out[ref["type"]] = protected.read(m.world().fs, m.facts.run_dir(run_id), ref).decode("utf-8")
    return out


class RootIndexImages(harness.Case):
    """C1 (T16, V05; ROW-1, GOV-1, EV-4, EV-6): T16 saves the root index before and after (rows-set T16 entry 15), and V05
    puts the before-image back only where the whole after-image stands (V05 entries 4 to 6), so nothing T16 did not do is
    reversed and the bytes come back."""

    def test_C1_T16_V05_EV4_EV6_the_root_index_images_saved_and_the_index_back_byte_for_byte(self):
        m = lib.machine(self)
        before = lib.read(m, *INDEX)
        looked, went = lib.run(self, m)
        saved = images(m, looked.doc["run"], "T16")
        self.assertEqual(saved, {"before-image": before, "after-image": lib.read(m, *INDEX)})
        lib.run(self, m, "restore")
        self.assertEqual(lib.read(m, *INDEX), before, "the root index is back byte for byte, T16's heading with it")

    def test_C1_T16_V05_GOV1_EV6_a_link_already_on_the_archive_in_the_moved_line_is_kept_by_the_restore(self):
        m = lib.machine(self)
        before = "# Index\n## Active\n- [[projects/demo/_index|demo]] also [[archive/demo/plan]]\n- other\n"
        m.put("vault/_index.md", before)
        looked, went = lib.run(self, m)
        self.assertEqual(lib.read(m, *INDEX), "# Index\n## Active\n- other\n## Archived\n"
                                              "- [[archive/demo/_index|demo]] also [[archive/demo/plan]]\n")
        rlooked, rwent = lib.run(self, m, "restore")
        self.assertEqual(m.statuses(rlooked.doc["run"])["V05"], "done")
        self.assertEqual(lib.read(m, *INDEX), before, "the link that was on the archive before the sunset stays there")


class HeadingPlacement(harness.Case):
    """C2 (T16; OP-5, OP-6), on G25-4: T16's after-test and after-check read the archived link under `## Archived` (rows-set
    T16 entry 5, "one line holding `{NEW}/_index` stands under `## Archived`")."""

    def test_C2_T16_OP5_OP6_G25_4_the_archived_link_under_another_heading_with_no_archived_heading_is_not_already_so(self):
        m = lib.machine(self)
        text = "# Index\n## Active\n- [[archive/demo/_index|demo]]\n"
        m.put("vault/_index.md", text)
        looked = lib.look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the thing is in neither state the row names: row T16", looked.lines)
        self.assertEqual(lib.read(m, *INDEX), text, "nothing is written")

    def test_C2_T16_OP5_G25_4_the_archived_link_already_under_archived_is_already_so(self):
        m = lib.machine(self)
        text = "# Index\n## Active\n- [[projects/other/_index|other]]\n## Archived\n- [[archive/demo/_index|demo]]\n"
        m.put("vault/_index.md", text)
        looked, went = lib.run(self, m)
        self.assertIn("T16", [s.get("row") for s in lib.manifest(m, looked.doc["run"]).get("already_so") or []])
        self.assertEqual(lib.read(m, *INDEX), text)

    def test_C2_T16_OP6_G25_4_the_moved_line_stands_under_archived_and_the_after_check_reads_it_there(self):
        m = lib.machine(self)
        looked, went = lib.run(self, m)
        self.assertEqual(m.statuses(looked.doc["run"])["T16"], "done")
        t16 = [o for o in lib.manifest(m, looked.doc["run"])["operations"] if o["id"] == "T16"][0]
        self.assertTrue([c for c in t16["after_check"] if c.get("read") == "text" and c.get("under") == {"literal": "## Archived"}],
                        t16["after_check"])
        self.assertEqual(lib.read(m, *INDEX), "# Index\n## Active\n- [[projects/other/_index|other]]\n## Archived\n"
                                              "- [[archive/demo/_index|demo]]\n")


class BoundedLines(harness.Case):
    """C3 (T14, T18; ROW-1): the edits and the saved spans carry the line boundaries rows-set writes (T14 entry 6
    `"\\nstatus: active\\n"`, T18 entry 6 `"\\nname: {name1}\\n"`), so the same words in unrelated prose are neither a second
    target nor changed."""

    def test_C3_T14_V03_ROW1_EV6_the_status_words_in_unrelated_prose_are_kept_and_the_status_line_archived_and_back(self):
        m = lib.machine(self)
        before = lib.read(m, *NOTE) + "example status: active suffix\n"
        m.put("vault/projects/demo/_index.md", before)
        looked, went = lib.run(self, m)
        self.assertEqual(m.statuses(looked.doc["run"])["T14"], "done")
        archived = lib.read(m, "vault", "archive", "demo", "_index.md")
        self.assertIn("\nstatus: archived\narchived: 2026-01-01\n", archived)
        self.assertTrue(archived.endswith("example status: active suffix\n"), "the prose is unchanged")
        self.assertEqual(images(m, looked.doc["run"], "T14"),
                         {"before-image": "\nstatus: active\n", "after-image": "\nstatus: archived\narchived: 2026-01-01\n"})
        lib.run(self, m, "restore")
        self.assertEqual(lib.read(m, *NOTE), before)

    def test_C3_T18_V07_ROW1_EV6_the_name_words_in_unrelated_prose_are_kept_and_the_note_archived_and_back(self):
        m = lib.machine(self)
        before = lib.read(m, *MEMORY_NOTE) + "example name: demo suffix\n"
        m.put("mem/home/project_demo_notes.md", before)
        looked, went = lib.run(self, m)
        self.assertEqual(m.statuses(looked.doc["run"])["T18"], "done")
        self.assertEqual(lib.read(m, *MEMORY_NOTE),
                         before.replace("\nname: demo\n", "\nname: demo\nstatus: archived\narchived: 2026-01-01\n"))
        self.assertEqual(images(m, looked.doc["run"], "T18"),
                         {"before-image": "\nname: demo\n",
                          "after-image": "\nname: demo\nstatus: archived\narchived: 2026-01-01\n"})
        lib.run(self, m, "restore")
        self.assertEqual(lib.read(m, *MEMORY_NOTE), before)


if __name__ == "__main__":
    import unittest
    unittest.main()
