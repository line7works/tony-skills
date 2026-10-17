"""The manifest: the plan of a run, written once and never changed once it has its go (RUN-8, RUN-9, RUN-11).

`manifest-<n>.json` in the run directory, one file per plan, every one kept. Its hash is the SHA-256
of the file's bytes; the owner's go is recorded with it, and an invocation refuses a manifest whose
bytes no longer give the recorded hash.
"""
import json
import os

from . import fsio, journal as journalmod, schemas

ENTRIES = ("inputs", "accounts", "capabilities", "locations", "keys", "phases", "operations", "already_so", "not_applicable")


class Altered(Exception):
    """The manifest in force no longer gives the hash its go was recorded with."""


class Invalid(Exception):
    def __init__(self, findings):
        Exception.__init__(self, "the manifest fails its validation")
        self.findings = findings


def path_of(run_dir, number):
    return os.path.join(run_dir, "manifest-%d.json" % number)


def numbers(fs, run_dir):
    out = []
    for name in fs.listdir(run_dir):
        if name.startswith("manifest-") and name.endswith(".json") and name[9:-5].isdigit():
            out.append(int(name[9:-5]))
    return sorted(out)


def validate(doc):
    """A manifest from which any one entry RUN-8 lists is removed fails its validation."""
    if not isinstance(doc, dict):
        raise Invalid([{"path": "/", "rule": "type"}])
    missing = [{"path": "/" + key, "rule": "required"} for key in ENTRIES if key not in doc]
    if missing:
        raise Invalid(missing)
    found = schemas.errors("manifest", doc)
    if found:
        raise Invalid(found)
    return doc


def write(world, run_dir, number, doc, register):
    """Write a new manifest whole. A manifest that would carry a register entry is not written."""
    data = fsio.pretty_json(doc).encode("utf-8")
    if register.holds(data.decode("utf-8")):
        raise journalmod.Withheld("manifest")
    world.fs.write_new(path_of(run_dir, number), data)
    return fsio.sha256_hex(data)


def load(fs, run_dir, number):
    data = fs.read(path_of(run_dir, number))
    return json.loads(data.decode("utf-8")), fsio.sha256_hex(data)


def go_records(journal):
    return [r for r in journal.records if r.get("kind") in ("open", "go")]


def in_force(fs, run_dir, journal):
    """(number, manifest) of the manifest the latest go was recorded on, proven against its hash."""
    gos = go_records(journal)
    if not gos:
        return None, None
    number, want = gos[-1]["manifest"], gos[-1]["manifest_sha256"]
    try:
        doc, sha = load(fs, run_dir, number)
    except (OSError, ValueError):
        raise Altered()
    if sha != want:
        raise Altered()
    return number, doc
