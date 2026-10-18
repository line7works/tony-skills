"""E16 slice 4: the lane run end to end over fakes (a sunset, then its restore), and a kill at every write boundary of each
(the common brief's section 4, item 3; contract section 12, L6; the frame's LOG-1, OP-6).

The sweep is slice 1's helper (`killlib.Sweep`), given this lane's fixture: its summonses carry the lane's three names
(rows-set C3) and the adapter's capabilities, and its rows are the lane's files as they ship with slice 3's stand-ins
(`test_lane_set_lib`). At every kill point the rerun ends in the unkilled run's end state, or in that state with an
operation listed as not proven where the frame says so, or stops plainly; no effect is applied twice.
"""
import hashlib
import os
import re
import sys

import harness
import killlib
import test_lane_set_lib as lib


def prepared(machine, then_sunset=False, case=None):
    lib.programs(machine)
    lib.locations(machine)
    machine.write_settings()
    lib.plant(machine)
    lib.install(machine)
    caps = machine.capabilities(list(lib.CAPS))
    look, go, drive, summon = machine.look, machine.go, machine.drive, machine.summon
    also = []
    for name in lib.ALSO:
        also += ["--also", name]

    def look_(name="demo", kind="sunset", **kw):
        return look(name, kind, also=lib.ALSO, inputs=lib.inputs(machine), caps=list(lib.CAPS), **kw)

    def go_(looked, name="demo", kind="sunset", **kw):
        return go(looked, name, kind, also=lib.ALSO, caps=list(lib.CAPS), **kw)

    def drive_(*argv, **kw):
        return drive(*(list(argv) + also + ["--capabilities", caps]), **kw)

    def summon_(command, name="demo", *more, **kw):
        kw.setdefault("also", lib.ALSO)
        kw.setdefault("caps", list(lib.CAPS))
        return summon(command, name, *more, **kw)
    machine.look, machine.go, machine.drive, machine.summon = look_, go_, drive_, summon_
    if then_sunset:
        looked = machine.look("demo", "sunset")
        went = machine.go(looked, "demo", "sunset")
        assert went.ending == "complete", went.text
    return machine


class EndToEnd(harness.Case):
    def test_E2E_EV5_EV7_a_sunset_over_fakes_looked_previewed_approved_and_executed_then_its_restore_both_complete(self):
        m = harness.Machine(self.tmp, "e2e", "e2e")
        prepared(m)
        before = harness.tree(m.home)
        looked = m.look("demo", "sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, "demo", "sunset")
        self.assertEqual(went.ending, "complete", went.text)
        statuses = m.statuses(looked.doc["run"])
        # one `already so`: T17's member for the root index, whose one link T16 moved and repointed before its turn
        self.assertEqual(sorted(statuses.values()).count("already so"), 1, statuses)
        self.assertEqual(sorted(set(statuses.values())), ["already so", "done", "passed"], statuses)
        self.assertEqual([os.path.basename(f).split("-")[0] for f in went.doc["forms"]], ["status", "summary", "handoff"])
        rlooked = m.look("demo", "restore")
        self.assertEqual(rlooked.ending, "preview", rlooked.text)
        rwent = m.go(rlooked, "demo", "restore")
        self.assertEqual(rwent.ending, "complete", rwent.text)
        self.assertEqual(sorted(set(m.statuses(rlooked.doc["run"]).values())), ["done"])
        after = harness.tree(m.home)
        # every layer back, byte-equal where the bytes are ours, the copies and records still in the archive (L7's clean case)
        skip = (".sun-v2", ".fakes", ".config")
        kept = dict((rel, v) for rel, v in before.items() if rel.split(os.sep)[0] not in skip)
        changed = sorted(rel for rel, v in kept.items() if after.get(rel) != v)
        # the memory index keeps its `## Archived` heading (G19-14, T19's way back); every note T17 repointed is back byte for
        # byte, by V06 (part 3), and the root index by V05 from T16's saved images (the fix round, C1)
        self.assertEqual(changed, ["mem/home/MEMORY.md"], changed)
        self.assertEqual(lib.read(m, "mem", "home", "MEMORY.md"), "- [Demo](project_demo_notes.md) the demo\n"
                                                                 "- [Other](project_other.md) other\n## Archived\n")
        added = sorted(rel for rel in after if rel not in before and rel.split(os.sep)[0] not in skip)
        tomb = os.path.join("vault", "projects", "demo-vault", "_sunset-%s.md" % looked.doc["run"])
        entry = os.path.join("vault", "projects", "demo-vault", "_restore-%s.md" % rlooked.doc["run"])
        sf = os.path.join("dev", "_archive", "demo.sunset-2026-01-01")
        self.assertEqual(added, sorted([os.path.join("dev", "_archive"), sf, os.path.join(sf, "memory"),
                                        os.path.join(sf, "memory", "MEMORY.md"), os.path.join(sf, "memory", "notes"),
                                        os.path.join(sf, "memory", "notes", "one.md"), os.path.join("vault", "archive"), tomb, entry]))
        for name in ("preview", "status", "summary", "handoff"):
            sys.stderr.write("\n---- sunset %s ----\n%s" % (name, lib.form(looked if name == "preview" else went, name)))
        for name in ("preview", "status", "summary"):
            sys.stderr.write("\n---- restore %s ----\n%s" % (name, lib.form(rlooked if name == "preview" else rwent, name)))


def world_facts(machine):
    """`killlib.world_facts`, with the fixture home's own path read out of the files' names and bytes: the project's memory
    store is named by the project folder's path (E16-12) and a launch agent's file holds it, and every kill point has a home
    of its own. A run's last record is compared by its head lines (below)."""
    home = machine.home
    munged = re.sub(r"[^A-Za-z0-9]", "-", home)
    files = {}
    for rel, (kind, mode, digest) in harness.tree(home).items():
        if rel.split(os.sep)[0] in killlib.SKIP:
            continue
        if kind == "file":
            with open(os.path.join(home, rel), "rb") as fh:
                data = fh.read().replace(home.encode("utf-8"), b"<home>")
            if re.match(r"_(sunset|restore)-", os.path.basename(rel)):
                # a run's last record renders its journal (KEEP-5), whose record names and `not proven` lines a kill may
                # change: its head lines, the lane's own, are compared, and the rest is the journal's to show
                data = re.split(rb"\n(SUNSET|RESTORE): the record of run ", data)[0]
            digest = hashlib.sha256(data).hexdigest()
        files[rel.replace(munged, "<home>")] = (kind, mode, digest)
    return {"files": files, "fakes": REAL_FACTS(machine)["fakes"]}


REAL_FACTS = killlib.world_facts


class EveryBoundary(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        killlib.world_facts = world_facts
        self.addCleanup(setattr, killlib, "world_facts", REAL_FACTS)

    def sweep(self, kind):
        # a kill after a move's rename and before its completion leaves the move `not proven` (OP-6), and ORD-1 meets no
        # `made` need on a `not proven` provider: rows-set's T14, T16 and T30 need `vault folder archived` made, so the rerun
        # stops plainly on that need (the report's section 8)
        sweep = killlib.Sweep(self, self.tmp, lambda machine: prepared(machine, then_sunset=kind == "restore"), "demo", kind,
                              plain_stops=("need unmet",))
        failures = sweep.everywhere()
        ran = sweep.ran
        sys.stderr.write("lane set kill sweep (%s): %d kill points of %d recorded, %d failed, %d worker(s); outcomes: %s\n"
                         % (kind, ran["kill_points"], ran["recorded"], ran["failed"], ran["workers"],
                            ", ".join("%s %d" % kv for kv in sorted(ran["outcomes"].items()))))
        self.assertEqual(ran["kill_points"], ran["recorded"])
        self.assertEqual(failures, [], "%d of %d kill points failed:\n%s" % (len(failures), ran["recorded"], "\n".join(failures[:15])))
        self.assertIn("complete", ran["outcomes"])
        self.assertEqual(ran["scanned"], ran["recorded"])

    def test_LOG1_OP6_L6_a_kill_at_every_write_boundary_of_the_lanes_sunset(self):
        self.sweep("sunset")

    def test_LOG1_OP6_L6_EV7_a_kill_at_every_write_boundary_of_the_lanes_restore(self):
        self.sweep("restore")


if __name__ == "__main__":
    import unittest
    unittest.main()
