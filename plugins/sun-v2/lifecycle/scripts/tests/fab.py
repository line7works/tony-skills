"""Fixture states built with the core's own writers, by the fixture's own hands (nothing recorded).

Used where a test needs a state on disk that a whole run would take many steps to reach: an open run,
a run that has caught a value, a stale lock. Every file is written by the same modules the tool
writes it with, so the state is one the tool could have left.
"""
import hashlib
import json
import os

import harness
from sun_core import fsio, journal as journalmod, keys, locks as locksmod, protected, rundir
from sun_core import world as worldmod


def quiet(machine):
    """A world on the fixture machine whose acts are not recorded: the fixture's own hands."""
    world = worldmod.World()
    world.env = dict(machine.env)
    world.fs = fsio.FS()
    world.now = machine.now
    world.new_id = machine.next_id
    world.random_hex = machine.next_hex
    world.invocation = machine.next_id("i")
    return world


def keying(machine):
    world = quiet(machine)
    if not os.path.exists(machine.facts.keying_file):
        keys.make_keying(world, machine.facts)
    return keys.read_keying(world.fs, machine.facts)


def open_run(machine, name, kind="sunrise", more_names=(), description="a fixture project", lock=False):
    """A run with its go on record, open under the keys of its names. Returns its id."""
    world = quiet(machine)
    value = keying(machine)
    run_id = machine.next_id(kind)
    run_dir = rundir.create(world, machine.facts, run_id)
    inputs = {"input_version": 1, "kind": kind, "names": [name] + list(more_names), "description": description,
              "answers": {}, "flags": {}}
    world.fs.write_new(os.path.join(run_dir, "inputs.json"), fsio.pretty_json(inputs).encode("utf-8"))
    manifest = fsio.pretty_json({"manifest_version": 1, "run": run_id, "fixture": True}).encode("utf-8")
    world.fs.write_new(os.path.join(run_dir, "manifest-1.json"), manifest)
    prints = sorted(keys.fingerprint(value, keys.fold(n)) for n in [name] + list(more_names))
    journal = journalmod.Journal(run_dir, [])
    journal.append(world, "open", run=run_id, run_kind=kind, keys=prints, manifest=1,
                   manifest_sha256=hashlib.sha256(manifest).hexdigest(), word="go", closes=None)
    journal.append(world, "invocation-end", ending="stopped", reason={"kind": "fixture"})
    current = locksmod.read_open_runs(world.fs, machine.facts)
    for mark in prints:
        current[mark] = run_id
    world.fs.makedirs(machine.facts.locks_dir)
    locksmod.write_open_runs(world, machine.facts, current)
    if lock:
        stale_lock(machine, name, run_id)
    return run_id


def journal_of(machine, run_id):
    return journalmod.Journal.read(fsio.FS(), machine.facts.run_dir(run_id))


def catch(machine, run_id, value, components=()):
    """The run catches `value` in a secret field: its protected record and its disproof record."""
    world = quiet(machine)
    run_dir = machine.facts.run_dir(run_id)
    record_id = machine.next_id("p")
    reference = protected.write(world, run_dir, record_id, protected.envelope(value, True, True, components),
                                "secret field", "a secret field of a fixture command")
    journal = journal_of(machine, run_id)
    record = journal.append(world, "disproof", rests={"protected": reference}, source="secret field")
    journal.append(world, "invocation-end", ending="stopped", reason={"kind": "a safe ground disproved"})
    return record


def catch_in_inputs(machine, run_id, value):
    """The run catches a channel secret that its saved inputs hold: the record names the span."""
    world = quiet(machine)
    run_dir = machine.facts.run_dir(run_id)
    data = open(os.path.join(run_dir, "inputs.json"), "rb").read()
    start = data.index(value.encode("utf-8"))
    journal = journal_of(machine, run_id)
    record = journal.append(world, "disproof", source="channel", channel="hosting-token",
                            rests={"content": {"file": "inputs.json", "start": start, "end": start + len(value.encode("utf-8"))}})
    journal.append(world, "invocation-end", ending="stopped", reason={"kind": "a safe ground disproved"})
    return record


def stale_lock(machine, name, run_id):
    """A lock file a killed invocation left: its record on disk, nobody holding it."""
    keying(machine)
    mark = machine.fingerprint(name)
    os.makedirs(machine.facts.locks_dir, exist_ok=True)
    path = machine.facts.lock_file(mark)
    with open(path, "w") as fh:
        fh.write(fsio.pretty_json({"fingerprint": mark, "run": run_id}))
    os.chmod(path, 0o600)
    return path


def cut_record(machine, run_id, number):
    """Cut one record out of a journal, from between two records that stay."""
    path = os.path.join(machine.facts.run_dir(run_id), "journal.jsonl")
    lines = open(path).read().split("\n")
    assert 0 < number < len(lines) - 2, "the record cut must stand between two that stay"
    del lines[number]
    with open(path, "w") as fh:
        fh.write("\n".join(lines))


def lane_min(machine):
    machine.rows_root = os.path.join(harness.TESTS, "fixtures", "lane-min")
    return machine
