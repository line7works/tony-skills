"""Slice 2's lane under slice 1's kill-sweep helper (`killlib.Sweep`): a kill at every write boundary of the reference run
of the joined sunrise lane (a web app, every layer, slice 3's remote rows among them since the join), a real SIGKILL of a
child process,
then a status summons and a resume on its position, as an executor would make them (LOG-1, OP-6, E16-6).

Two things of this lane's world are not the same bytes on two fixture machines, and the comparison of end states reads them
by what they are, said plainly: a file that holds the machine's own home path (the seed's local path, the alias line, the
memory note) is compared with that path written as `<HOME>`; the repository is compared by its branch, its head commit's
tree, its message and its status, since git writes a commit's time and each machine's file stamps into `.git`; and the
hosting link file, which holds the fake host's ids (made from each machine's own home), by its keys and its mode. The
child drive is `provlib`'s (the fixture's system folders, the fake host of the frame's own requests, the hosting token):
it finds the system's own git in the fixture's system folder of slice 3's, on the test's own temporary repository, and the
scaffolder fakes in a program folder he names.
"""
import hashlib
import json
import os
import subprocess
import sys

import harness
import killlib
import test_lane_rise as rise

provlib = rise.provlib


class RiseMachine(provlib.Machine):
    """A fixture machine whose look carries the three names by place and the sunrise inputs, as an executor gives them."""

    def look(self, name="demo", kind="sunrise", also=(), inputs=None, caps=None, **kw):
        return provlib.Machine.look(self, name, kind, also=rise.ALSO, inputs=inputs or self.rise_inputs, caps=caps, **kw)


def prepare(machine):
    rise.machine_for_sunrise(machine, into_system=False)
    rise.install(machine)
    machine.rise_inputs = rise.sunrise_inputs(machine)
    # SEC-7: the hosting link file is the one place outside the run directory the fake host's ids rest (rows-rise 3.9)
    machine.secret_places = (machine.path("dev", "demo", ".vercel", "project.json"),)


def world_facts(machine):
    """`killlib.world_facts`, with this lane's machine-made bytes read by what they are (the module's docstring)."""
    facts = ORIGINAL(machine)
    project = machine.path("dev", "demo")
    files = {}
    for rel, (kind, mode, digest) in facts["files"].items():
        full = os.path.join(machine.home, rel)
        if rel.split(os.sep)[:3] == ["dev", "demo", ".git"]:
            continue
        if kind == "file" and rel == os.path.join("dev", "demo", ".vercel", "project.json"):
            with open(full) as fh:
                digest = "keys " + ",".join(sorted(json.load(fh)))
        elif kind == "file":
            with open(full, "rb") as fh:
                data = fh.read().replace(machine.home.encode("utf-8"), b"<HOME>")
            digest = hashlib.sha256(data).hexdigest()
        files[rel] = (kind, mode, digest)
    if os.path.isdir(os.path.join(project, ".git")):
        def git(*a):
            return subprocess.run(["/usr/bin/git", "-C", project] + list(a), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode()
        files["dev/demo/.git (as git reads it)"] = ("repo", 0, "|".join(
            [git("rev-parse", "--abbrev-ref", "HEAD").strip(), git("log", "--format=%T %s").strip(), git("status", "--porcelain")]))
    facts["files"] = files
    return facts


ORIGINAL = killlib.world_facts


class Sweep(provlib.Sweep):
    """`provlib.Sweep`, its machines `RiseMachine`s. A plain stop besides an outstanding create: `need unmet`, where a kill
    falls after SR07's commit and before its completion record, so that OP-6 records SR07 `not proven` and a row that needs
    `first commit` at the `made` level (slice 3's SR08) stops naming that need (ORD-1)."""

    def __init__(self, test, tmp, prepare):
        provlib.Sweep.__init__(self, test, tmp, prepare, harness.canary("sweep-vercel-token"), machine_kind=RiseMachine,
                               plain_stops=("an outstanding create", "need unmet"))


class EveryBoundaryOfTheLanesReferenceRun(harness.Case):
    def test_LOG1_OP6_E16_6_SR00_to_SR25_a_kill_at_every_write_boundary_of_the_sunrise_lanes_run(self):
        killlib.world_facts = world_facts
        try:
            sweep = Sweep(self, self.tmp, prepare)
            failures = sweep.everywhere()
        finally:
            killlib.world_facts = ORIGINAL
        row = sweep.ran
        sys.stderr.write("rise kill sweep: %d kill points of %d recorded, %d failed, %d worker(s); outcomes: %s\n"
                         % (row["kill_points"], row["recorded"], row["failed"], row["workers"],
                            ", ".join("%s %d" % kv for kv in sorted(row["outcomes"].items()))))
        self.assertEqual(sweep.statuses.get("SR25"), "passed", sweep.statuses)
        self.assertGreater(row["recorded"], 40)
        self.assertEqual(row["kill_points"], row["recorded"])
        self.assertEqual(failures, [], "%d of %d kill points failed:\n%s" % (len(failures), row["recorded"], "\n".join(failures[:15])))
        self.assertIn("complete", row["outcomes"])
        self.assertEqual(row["scanned"], row["recorded"])
        self.assertTrue(row["scanned_reference"])
