"""Locks and the record of open runs (the frame's RUN-2, RUN-3).

A lock is a file in the tool's lock folder named by the fingerprint of a project key, held with an
advisory lock the system releases when its holder dies. It is never broken by age and never waited
for. Its record, the file's content, holds the fingerprint and the id of the run that holds it, and
nothing else. The file is made when the lock is taken and removed when it is released, so an
invocation that is turned away leaves nothing behind; a holder that was killed leaves its file,
unlocked, and the next taker takes it over.

The record of open runs is one file beside the lock files: fingerprints of project keys against run
ids, and nothing else. It is replaced whole by one rename, so a run is recorded as open under all
of its keys or under none (RUN-3), and a restore's handover is one deciding write (EV-7).
"""
import json
import os

from . import facts as factsmod
from . import fsio

RECORD_VERSION = 1


class Held(RuntimeError):
    """Another invocation holds the lock. `run` is the id in the lock's record, or None."""

    def __init__(self, fingerprint, run):
        RuntimeError.__init__(self, "held")
        self.fingerprint = fingerprint
        self.run = run


def read_lock_record(fs, path):
    """The run id a lock's record holds; None where the record does not read as one."""
    try:
        doc = json.loads(fs.read_text(path))
    except (OSError, ValueError):
        return None
    run = doc.get("run") if isinstance(doc, dict) else None
    return run if isinstance(run, str) and run else None


def lock_record(fs, path):
    """What the withheld read finds of one lock's record (SEC-12; the owner's rulings A40, A41): ("gone", None) where the
    file that was listed is gone when its record is read, which is a lock released; ("read", run id, "" for a record
    that names no run yet) for a lock's record; ("unreadable", None) where the file cannot be read, or what is read is
    no lock's record: an object of exactly the fingerprint, which is the file's own name, and the run."""
    try:
        data = fs.read(path)
    except FileNotFoundError:
        return "gone", None
    except OSError:
        return "unreadable", None
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return "unreadable", None
    name = os.path.basename(path)
    if (not isinstance(doc, dict) or sorted(doc) != ["fingerprint", "run"] or not isinstance(doc["run"], str)
            or doc["fingerprint"] + factsmod.LOCK_SUFFIX != name):
        return "unreadable", None
    return "read", doc["run"]


def lock_files(fs, facts):
    """The lock files present, by base name, sorted."""
    if not fs.lexists(facts.locks_dir):
        return []
    return [n for n in fs.listdir(facts.locks_dir) if n.endswith(factsmod.LOCK_SUFFIX)]


def read_open_runs(fs, facts):
    """{fingerprint: run id}; {} where the record is not there. A record that does not read back is
    an error: nothing may be decided from it."""
    if not fs.lexists(facts.open_runs_file):
        return {}
    doc = json.loads(fs.read_text(facts.open_runs_file))
    found = doc.get("open") if isinstance(doc, dict) else None
    if (not isinstance(found, dict) or sorted(doc) != ["open", "record_version"] or doc.get("record_version") != RECORD_VERSION
            or not all(isinstance(k, str) and isinstance(v, str) and v for k, v in found.items())):
        raise ValueError("the record of open runs does not read back")      # what is read is no such record (A40)
    return dict(found)


def write_open_runs(world, facts, mapping):
    """The record replaced whole by one rename. A record that holds no open run is kept as such and never removed:
    the run removes only what is its own, and outside its run directory only the file of a lock it took (LOG-3, A41);
    so once a machine has had a go, the record exists, and RUN-2's gate reads it so."""
    fs = world.fs
    doc = {"record_version": RECORD_VERSION, "open": dict(sorted(mapping.items()))}
    fs.replace_atomic(facts.open_runs_file, fsio.pretty_json(doc).encode("utf-8"))


class Locks(object):
    """The locks one invocation holds. Taken in the order asked, never waited for, released together."""

    def __init__(self, world, facts):
        self.world = world
        self.facts = facts
        self.held = {}      # fingerprint -> descriptor
        self.order = []     # fingerprints in the order taken

    def _staged(self, path, run_id, fingerprint):
        """The lock's record built whole beside its place, owner-only and synced, and locked: (descriptor, its path), or
        (None, its path) where another start is taking this very lock now. Its name does not end as a lock's file does,
        so no start lists it as a lock. A file a killed taker left under that name is taken over and filled again."""
        fs = self.world.fs
        staged = path + ".taking"
        data = fsio.pretty_json({"fingerprint": fingerprint, "run": run_id}).encode("utf-8")
        try:
            fs.write_new(staged, data)
            return fs.lock_exclusive(staged, create=False), staged
        except fsio.Exists:
            fd = fs.lock_exclusive(staged, create=False)
            if fd is not None:
                fs.fill_staged(fd, staged, data)
            return fd, staged

    def take(self, fingerprint, run_id):
        """The lock of one key, never waited for. Its record is never at its place half written (RUN-2, A41): a new
        lock's file appears at its place by an exclusive rename of the record built whole beside it; a left file is
        taken over by holding its lock and putting the new record whole in its place by one rename."""
        if fingerprint in self.held:
            return
        fs = self.world.fs
        fs.makedirs(self.facts.locks_dir)
        path = self.facts.lock_file(fingerprint)
        while True:
            try:
                left = fs.lock_exclusive(path, create=False)
            except FileNotFoundError:
                left = False                       # no file: a new lock
            if left is None:
                raise Held(fingerprint, read_lock_record(fs, path))
            fd, staged = self._staged(path, run_id, fingerprint)
            if fd is None:                         # another start is taking this lock in the same instant
                if left not in (None, False):
                    fs.unlock(left, path, remove=False)
                raise Held(fingerprint, read_lock_record(fs, path))
            if left is False:
                try:
                    fs.rename_noreplace(staged, path)
                except fsio.Exists:
                    # another start made this lock's file in the same instant: the record built here was never
                    # published as a lock's file and goes (report-5's question 18), and the lock is asked for again
                    fs.unlock(fd, staged, remove=True)
                    continue
            else:
                fs.replace_into(staged, path)      # a killed holder's left file, taken over
                fs.unlock(left, path, remove=False)
            break
        self.held[fingerprint] = fd
        self.order.append(fingerprint)

    def rewrite(self, run_id):
        """Every held lock's record renamed to the run the invocation now continues, each put whole in its place."""
        for fingerprint in self.order:
            path = self.facts.lock_file(fingerprint)
            fd, staged = self._staged(path, run_id, fingerprint)
            if fd is None:                         # no other start can be taking a lock this invocation holds
                raise Held(fingerprint, run_id)
            self.world.fs.replace_into(staged, path)
            self.world.fs.unlock(self.held[fingerprint], path, remove=False)
            self.held[fingerprint] = fd

    def release_all(self):
        for fingerprint in reversed(self.order):
            self.world.fs.unlock(self.held.pop(fingerprint), self.facts.lock_file(fingerprint), remove=True)
        self.order = []
