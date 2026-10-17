"""The run directory and RUN-4's two checks.

`<runs>/<run id>/` holds: `inputs.json` and every input a re-plan saved (`inputs_names`); `manifest-<n>.json`, every one; `journal.jsonl`;
`protected/` (the protected records, the review files, the run's fingerprint key, and the files made from a
protected record to hand it to a child as a protected input, SEC-3); `forms/`; `staging/`; `tmp/` (a child's
private TMPDIR, SEC-3) and `private/` (the private password file, SEC-2).

The checks, made at the start of every invocation that continues a run and on every other run
directory an invocation reads: the directory and everything in it is owner-only, and the journal's
chain holds. A link in the run directory is a failure of the first check everywhere but inside
staging, where a built object may hold one.
"""
import os
import stat as statmod

from . import journal as journalmod
from . import protected

FOLDERS = ("protected", "forms", "staging", "tmp", "private")
PASSWORD_PREFIX = "password-"     # the private password file of an operation: `private/password-<operation>` (SEC-2)


def left_password_files(fs, run_dir):
    """Every private password file in the run directory: once the startup checks of an invocation that continues the
    run have passed, any that stands there is one a kill left (SEC-2, SEC-12)."""
    folder = os.path.join(run_dir, "private")
    if not fs.isdir(folder):
        return []
    return [os.path.join(folder, n) for n in fs.listdir(folder) if n.startswith(PASSWORD_PREFIX)]



def inputs_names(number):
    """The names an input saved for plan `number` may take, in order: `inputs.json` for the first look; for a re-plan
    `inputs-<n>.json`, and where a re-plan that a planning stop ended (RUN-12) already saved its inputs under that name,
    `inputs-<n>-<k>.json`, k from 2. The run directory keeps every input (RUN-4) and a run removes none (LOG-3), so an
    input an earlier invocation saved is never replaced; and nothing a look read is carried to a later invocation except
    through the manifest (RUN-5), so a later re-plan saves and reads its own."""
    if number == 1:
        yield "inputs.json"
        return
    yield "inputs-%d.json" % number
    k = 2
    while True:
        yield "inputs-%d-%d.json" % (number, k)
        k += 1


def is_inputs_name(name):
    """Whether a file of the run directory is one `inputs_names` gives: an input saved for the run (SEC-12's "the saved
    inputs")."""
    if name == "inputs.json":
        return True
    if not (name.startswith("inputs-") and name.endswith(".json")):
        return False
    parts = name[len("inputs-"):-len(".json")].split("-")
    return 1 <= len(parts) <= 2 and all(p.isdigit() and p[0] != "0" for p in parts)

class Failed(RuntimeError):
    """RUN-4's checks failed. `cause` is `missing`, `permissions`, `chain` or `disproof-unreadable`."""

    def __init__(self, cause):
        RuntimeError.__init__(self, cause)
        self.cause = cause


def create(world, facts, run_id):
    """A new run directory, owner-only, with its folders and its fingerprint key. A run id that
    already has a directory is never reused (the invocation made the id itself, so this is a defect)."""
    fs = world.fs
    fs.makedirs(facts.runs_root)
    run_dir = facts.run_dir(run_id)
    fs.mkdir(run_dir)
    for name in FOLDERS:
        fs.mkdir(os.path.join(run_dir, name))
    protected.make_key(world, run_dir)
    return run_dir


def owner_only(fs, run_dir):
    """Whether the directory and everything in it is owner-only."""
    staging = os.path.join(run_dir, "staging") + os.sep
    try:
        paths = [run_dir] + fs.walk(run_dir)
        for path in paths:
            st = fs.lstat(path)
            if statmod.S_ISLNK(st.st_mode):
                if not path.startswith(staging):
                    return False
                continue
            if statmod.S_IMODE(st.st_mode) & 0o077:
                return False
    except OSError:
        return False
    return True


def check(fs, run_dir):
    """RUN-4's two checks, in order; returns the journal read strictly."""
    if not fs.isdir(run_dir):
        raise Failed("missing")
    if not owner_only(fs, run_dir):
        raise Failed("permissions")
    try:
        return journalmod.Journal.read(fs, run_dir)
    except (journalmod.Broken, OSError):
        raise Failed("chain")
