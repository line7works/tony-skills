"""The withheld read, and what a refusal prints (the frame's SEC-12; RUN-1, RUN-2, RUN-3, RUN-12).

The first act of the gate at every start, before anything is printed. It reads the record of every
lock and the record of open runs and, for every run either of them holds (a run on record, other
projects' included), makes RUN-4's checks on that run directory and, whatever they find, reads the
disproof records of that journal as far as they can be read, and each value from where its record
says it rests. It holds those values for printing only: they are no entries of the register, and no
check of a name or of an input sees them. It reads nothing outside the tool's own folder and those
run directories, and it writes nothing. A check that fails here stops nothing: it bears only on
whether that run's id may be printed.

Until the startup checks have passed, every line the invocation prints is passed against those
values. A line of fixed text that holds one of them gives way to the fixed words of withholding. A
run's id is printed only where that run's disproof records were read whole and the id holds none of
the values. The read is whole where two things hold: the journal's chain holds from its first
record to its last, and the value of every disproof record in it was read from where its record
says it rests. Whether the directory is owner-only does not enter into it (the frame's own words;
the author's choice, `author-9b.md` section 3). Otherwise the fixed words stand in the id's place,
with the name of a file whose record holds that id: the record of open runs or a lock's file.

This module is the whole of that read and of the printing rule. `read(world, facts)` is called once,
by the gate; nothing else in the core reads another run's disproof records for printing.
"""
import os

from . import disproofs
from . import journal as journalmod
from . import locks as locksmod
from . import rundir
from . import screen as screenmod
from . import texts


class Run(object):
    """One run on record, and whether its id may be printed."""

    def __init__(self, run_id):
        self.id = run_id
        self.files = []          # base names of the files whose records hold its id, in printing order
        self.in_open_runs = False
        self.whole = False       # its disproof records were read whole
        self.owner_only = None   # RUN-4's other check, as found; it decides nothing here


class View(object):
    """What the withheld read gave: the values, held for printing only, and the runs on record."""

    def __init__(self, facts):
        self.facts = facts
        self.values = screenmod.Screen()
        self.runs = {}           # run id -> Run, in the order met
        self.order = []
        # one of the three records of the tool's own failed (a lock's record, the folder of locks, the record of open
        # runs): every start then stops at the withheld read with the one sentence of the owner's ruling A40
        self.unreadable = False

    # ---- the printing rule ----------------------------------------------------------------------
    def may_print_id(self, run_id):
        run = self.runs.get(run_id)
        return bool(run and run.whole and not self.values.holds(run_id))

    def line(self, text):
        """One line, passed against the values: printed whole, or giving way to the fixed words;
        an empty text where the fixed words hold a value too."""
        return self.values.line(text)

    def printable_file(self, run_id):
        """The name of a file whose record holds the id and whose name holds no caught value: the
        record of open runs or the run's lock's file, whichever may be printed. None where neither."""
        run = self.runs.get(run_id)
        for name in (run.files if run else []):
            if not self.values.holds(name):
                return name
        return None

    def run_text(self, run_id):
        """What stands for a run in a line: its id where it may be printed; otherwise the fixed
        words of withholding and the name of a file whose record holds the id; otherwise the fixed
        words alone."""
        if self.may_print_id(run_id):
            return run_id
        name = self.printable_file(run_id)
        if name is None:
            return self.values.words()
        return self.values.words() + texts.ID_IN_FILE + name

    def naming(self, head, run_id):
        """A line of fixed text that names one run, as the read lets it be printed."""
        return self.line(head + self.run_text(run_id))

    def listing(self):
        """The keying value's refusal lists every run on record (RUN-2): by its id, by the fixed
        words and a file's name, or, where neither file's name may be printed, by one fixed line
        that holds no path and no name, with the place of the lock files and the record of open runs
        in a line apart (the owner's ruling, A35). A line that cannot be written is left out."""
        lines, unnamed = [], False
        for run_id in self.order:
            if self.may_print_id(run_id) or self.printable_file(run_id) is not None:
                lines.append(self.naming(texts.RUN_ON_RECORD, run_id))
            else:
                lines.append(self.line(texts.RUN_ON_RECORD_UNNAMED))
                unnamed = True
        if unnamed:
            lines.append(self.line(texts.LOCKS_PLACE + self.facts.locks_dir))
        return [line for line in lines if line]


def _add(view, run_id, file_name, in_open_runs=False):
    if run_id not in view.runs:
        view.runs[run_id] = Run(run_id)
        view.order.append(run_id)
    run = view.runs[run_id]
    if file_name not in run.files:
        run.files.append(file_name)
    run.in_open_runs = run.in_open_runs or in_open_runs


def read(world, facts):
    """The withheld read. Reads only; never raises on what it finds."""
    fs = world.fs
    view = View(facts)
    if not facts.tool_home:
        return view
    try:
        present = fs.lexists(facts.tool_home)
    except OSError:
        present = False
    if not present:
        return view
    # the record of open runs first, so that its name is the one offered before a lock's
    # each of the three records is read as far as it can be; one that is not there has not failed (A40). Where one
    # fails, the read still goes on over every record that can be read, and the sentence is passed against what that
    # gave; what a run only the failed record names had caught, the read does not know (RK10)
    try:
        for _mark, run_id in sorted(locksmod.read_open_runs(fs, facts).items()):
            _add(view, run_id, os.path.basename(facts.open_runs_file), in_open_runs=True)
    except (OSError, ValueError):
        view.unreadable = True
    try:
        names = locksmod.lock_files(fs, facts)
    except OSError:
        names = []
        view.unreadable = True                   # the folder of locks cannot be listed
    for name in names:
        found, run_id = locksmod.lock_record(fs, os.path.join(facts.locks_dir, name))
        if found == "unreadable":
            view.unreadable = True
        elif found == "read" and run_id:         # "gone": a lock released between the listing and the read (A41)
            _add(view, run_id, name)
    for run_id in view.order:
        run = view.runs[run_id]
        run_dir = facts.run_dir(run_id)
        try:
            there = fs.isdir(run_dir)
        except OSError:
            there = False
        if not there:
            # a run that only a lock names may not have made its directory yet: it has caught
            # nothing. A run the record of open runs holds has a journal, so its absence is a read
            # that is not whole.
            run.whole = not run.in_open_runs
            continue
        run.owner_only = rundir.owner_only(fs, run_dir)      # RUN-4's first check: found, and not used
        records, chain, _there = journalmod.Journal.read_lenient(fs, run_dir)
        if run.in_open_runs and not records:
            chain = False
        found, every = disproofs.read_all(fs, run_dir, records)
        for record, value, components in found:
            view.values.add(value, components, None, "withheld read")
        run.whole = bool(chain and every)
    return view
