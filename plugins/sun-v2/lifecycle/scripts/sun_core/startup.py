"""How every invocation starts (the frame's RUN-1, RUN-2, RUN-3, RUN-4, SEC-12).

In this order, and nothing before it, the cue included:

1. The gate: first the withheld read (`withheld.read`), before anything is printed; then the vault's
   four checks and the keying value's check.
2. The locks: (a) the name check, against the secrets read without the project (the hosting token),
   and for a slash, the name "." or "..", and ".." as a part between slashes (the owner's ruling A135),
   and for no letter or digit, a leading hyphen, a backslash, a control character, a line break or an
   invisible mark (the owner's pick on PS47);
   (b) the first locks, in sorted order, the keying value made now where the machine has none; (c)
   the early look for an open run; (d) for a new summons and a re-plan, the alias reads; (e) the
   later locks and the second look for an open run. All of it before a run directory is opened or
   made.
3. The run directory: made for a first look; opened, with RUN-4's checks, for every other summons;
   and, for a run that is continued or is to have its go recorded, the disproof read.

Until these have passed, the invocation uses no runner, parses no result, checks no input but the
names, and writes only: the tool's fixed text and run ids, each as the withheld read lets it be
printed; a key's fingerprint and a run id in a lock; and, once on a machine, the keying value. A
refusal here ends `refused`, or `stopped` where a run that has its go fails RUN-4's checks, with
nothing created.

`Session.first_records` then writes the invocation's first journal records in the one order SEC-12
gives: the disproof records owed, the receipts owed, EV-7's `closed` record where the handover owes
it, then the record of what the invocation was summoned for (H13).
"""
import os

from . import channels, disproof, exits, journal as journalmod, keys, lanes, locks as locksmod
from . import rundir, screen as screenmod, texts, withheld

NEW = ("look",)                       # a new summons: it continues no run
TO_GO = ("go",)                       # it is to record a go on a manifest an earlier invocation made
CONTINUING = ("resume", "status", "close", "replan")
ALIAS_READERS = ("look", "go", "replan")


class Ended(Exception):
    """The invocation has its ending. `fields` is the document's content; `code` the exit."""

    def __init__(self, ending, lines, code=exits.TERMINAL, **fields):
        Exception.__init__(self, ending)
        self.ending = ending
        self.lines = lines
        self.code = code
        self.fields = fields


def run_kind_of(run_id):
    return run_id.split("-", 1)[0] if isinstance(run_id, str) and "-" in run_id else ""


def name_form_refused(name):
    """RUN-2's part (a), beside the register's cause: a name must "hold no slash, be neither "." nor "..", and hold no
    ".." as a part between slashes (the owner's ruling, A135)". A name with ".." as a part between slashes holds a slash
    as well; it is named apart because the rule names it apart.

    And the owner's pick on PS47: "These are refused: a name with no letter or digit, or one that starts with a hyphen;
    and a name holding a backslash, a control character, any line break or an invisible mark. The invisible marks are the
    zero-width and direction marks. Spaces stay allowed." A letter or a digit is what the key's fold keeps
    (`keys.fold`, `str.isalnum`), so a name with none is a name that folds to no key. The characters are `chars.py`'s
    one core (A142), with the backslash beside it."""
    from . import chars
    if "/" in name or name in (".", "..") or ".." in name.split("/"):
        return True
    if not keys.fold(name) or name.startswith("-"):
        return True
    return any(chars.barred_in_a_name(ch) for ch in name)


class Session(object):
    def __init__(self, world, printer, command):
        self.world = world
        self.printer = printer
        self.command = command
        self.facts = None
        self.view = None
        self.register = printer.register
        self.providers = {}
        self.lane = None
        self.tokens = {}
        self.names = []               # every name the summons carries
        self.alias_names = []         # every further name form the alias reads showed
        self.keying = None
        self.prints = {}              # fingerprint -> True, every key the invocation holds the lock of
        self.locks = None
        self.open_map = {}
        self.run_id = None
        self.run_dir = None
        self.run_kind = None
        self.journal = None
        self.is_open = False          # the run is on the record of open runs
        self.over = None              # a restore's look or go: the open retirement it would close
        self.partner = None           # the handover's other run, where one is found
        self.owed = []
        self.receipts_owed = []
        self.closed_owed = None       # (retirement's run dir, restore's run id) where EV-7's record is missing
        self.passed = False
        self.identities_read = {}     # provider -> the account its identity read gave in this invocation
        self.continues = False        # the invocation opened an existing run directory (RUN-1's third step)
        self.learnt = []              # a re-plan's alias reads: name forms whose key the run does not hold (A72)
        world.session = self

    # ---- 1. the gate ----------------------------------------------------------------------------
    def withheld_read(self, view=None):
        """The withheld read: the one the tool's first code made (`sun.py`), handed on; or, where a caller of
        `cli.main` made none, made here by the same function."""
        from . import facts as factsmod
        self.facts = factsmod.Facts(self.world.env)
        self.view = view if view is not None else withheld.read(self.world, self.facts)
        self.printer.view = self.view
        return self.view

    def refuse(self, lines, ending="refused"):
        raise Ended(ending, [line for line in lines if line])

    def gate(self):
        fs, facts, view = self.world.fs, self.facts, self.view
        vault = facts.vault(fs)
        if not vault or not isinstance(vault.get("path"), str) or not vault.get("path"):
            self.refuse([view.line(texts.GATE["vault-settings"])])
        path = vault["path"]
        if not fs.isdir(path):
            self.refuse([view.line(texts.GATE["vault-missing"])])
        if not fs.isfile(os.path.join(path, str(vault.get("marker_file") or ""))) or not vault.get("marker_file"):
            self.refuse([view.line(texts.GATE["vault-marker"])])
        if not vault.get("projects_dir") or not fs.isdir(os.path.join(path, str(vault.get("projects_dir")))):
            self.refuse([view.line(texts.GATE["vault-projects"])])
        segments = [s for s in vault.get("synced_segments") or [] if isinstance(s, str) and s]
        real = fs.realpath(path)
        if any(segment in real.split(os.sep) for segment in segments):
            self.refuse([view.line(texts.GATE["vault-synced"])])
        state = keys.keying_state(fs, facts)
        on_record = bool(locksmod.lock_files(fs, facts)) or fs.lexists(facts.open_runs_file)
        if state == "wide" or (state == "missing" and on_record):
            head = texts.GATE["keying-wide" if state == "wide" else "keying-missing"]
            ways = [view.line(sentence) for sentence in texts.WAYS_ON]      # after the listing, each passed (A43)
            self.refuse([view.line(head), view.line(texts.KEYING_PLACE + facts.keying_file)] + view.listing() + ways)
        self.keying_state = state

    # ---- 2. the locks ---------------------------------------------------------------------------
    def name_check(self, names):
        """(a): every name the summons carries, checked in memory: against the register, into which the hosting token is
        read first, and for its form (`name_form_refused`, the owner's ruling A135). Either cause is refused with the one
        fixed text, before any lock is taken."""
        self.providers = lanes.providers(self.world)
        self.tokens = channels.read_tokens(self.world, self.facts, self.providers, self.register)
        self.names = list(names)
        for name in self.names:
            if self.register.holds(name) or name_form_refused(name):
                self.refuse([self.view.line(texts.NAME_REFUSED)])

    def _take(self, prints, run_for_record):
        for mark in sorted(prints):
            if mark in self.prints:
                continue
            try:
                self.locks.take(mark, run_for_record or "")
            except locksmod.Held as held:
                self.locks.release_all()
                if held.run:
                    self.refuse([self.view.naming(texts.LOCK_HELD, held.run)])
                self.refuse([self.view.line(texts.LOCK_HELD_NO_ID)])
            self.prints[mark] = True

    def _refuse_open(self, run_id):
        self.locks.release_all()
        self.refuse([self.view.naming(texts.RUN_OPEN, run_id), self.view.line(texts.RUN_OPEN_WAYS)])

    def _look_for_open(self, prints, wanted_run, kind):
        """One look for an open run under `prints`. Returns the open run the summons continues, or
        None; refuses a summons the record turns away (RUN-3)."""
        self.open_map = locksmod.read_open_runs(self.world.fs, self.facts)
        hits = sorted(set(self.open_map[m] for m in prints if m in self.open_map))
        if self.command in NEW or self.command in TO_GO:
            if not hits:
                return None
            # the one exception (EV-7): a restore over the retirement that is open under the key
            if kind == "restore" and len(hits) == 1 and run_kind_of(hits[0]) == "sunset":
                self.over = hits[0]
                return None
            if self.command in TO_GO and hits == [wanted_run]:
                return wanted_run               # a re-plan's go, on a run that is open: the handler decides
            self._refuse_open(hits[0])
        if not hits:
            return None
        if len(hits) > 1:
            self.locks.release_all()
            self.refuse([self.view.line(texts.MORE_THAN_ONE_OPEN)])
        found = hits[0]
        if wanted_run and wanted_run != found:
            if run_kind_of(found) == "restore" and run_kind_of(wanted_run) == "sunset":
                self.partner = found            # a retirement a restore may have closed: the handover
                return wanted_run
            self._refuse_open(found)
        if kind and run_kind_of(found) != kind:
            if run_kind_of(found) == "restore" and kind == "sunset":
                self.partner = found            # the retirement is found through the restore's opening
                return None
            self._refuse_open(found)
        return found

    def lock_and_look(self, kind, wanted_run, prospective):
        """(b) to (e). `prospective` is the id the invocation made for a new run."""
        fs, facts = self.world.fs, self.facts
        self.locks = locksmod.Locks(self.world, facts)
        if self.keying_state == "missing":
            self.keying = keys.make_keying(self.world, facts)
        else:
            self.keying = keys.read_keying(fs, facts)
        first = set(keys.fingerprint(self.keying, keys.fold(n)) for n in self.names)
        self._take(first, wanted_run or prospective)                                      # (b)
        found = self._look_for_open(first, wanted_run, kind)                              # (c)
        if found is not None and self.partner is None and (self.command in CONTINUING or self.command in TO_GO):
            # (c): a summons that continues a run, a resume, a status, a re-plan, a close or the go of a re-plan, and carries
            # a name whose key that run is not open under, is turned away here: `refused`, the run unchanged, no key added,
            # none of RUN-12's five endings recorded (RUN-2, RUN-12; resting on A72)
            under = set(m for m, r in self.open_map.items() if r == found)
            if first - under:
                self.locks.release_all()
                self.refuse([self.view.line(texts.NOT_OPEN_UNDER_NAME)])
        target = found or wanted_run
        if self.command in CONTINUING:
            if found is None and self.partner is None and not wanted_run:
                self.locks.release_all()
                self.refuse([self.view.line(texts.NOTHING_TO_RESUME)])
            run_for_keys = self.partner or found
            if run_for_keys:
                self._take(set(m for m, r in self.open_map.items() if r == run_for_keys), target or run_for_keys)
        if self.over:
            self._take(set(m for m, r in self.open_map.items() if r == self.over), wanted_run or prospective)
        if self.command in ALIAS_READERS:                                                 # (d)
            lane_kind = kind or run_kind_of(target or prospective or "")
            self.lane = lanes.lane(self.world, lane_kind) if lane_kind else None
        if self.command in ALIAS_READERS and not (self.command in TO_GO and found):
            # (d) is made for a new summons and for a re-plan, and for no other: the go of a re-plan's manifest continues
            # an open run, which is opened under no key after its first go (RUN-2, RUN-3; A72)
            later, learnt = set(), []
            for name in self._alias_reads():
                key = keys.fold(name)
                if key:
                    mark = keys.fingerprint(self.keying, key)
                    if mark not in self.prints:
                        learnt.append(name)
                    self.alias_names.append(name)
                    later.add(mark)
            later -= set(self.prints)
            if later and self.command == "replan":
                # a name form whose key the run does not hold: no lock is taken under it and no key is added; the re-plan's
                # look ends at once as a planning stop once the startup checks have passed (RUN-2, A72)
                self.learnt = learnt
            elif later:
                self._take(later, target or prospective)                                  # (e)
                self._look_for_open(later, wanted_run, kind)
        self.is_open = found is not None
        return found

    def _alias_reads(self):
        """The reads of this machine's own files that the lane's rows declare as showing another
        name form of the project: in-process, no runner, no provider."""
        names = []
        locations = self.facts.locations(self.world.fs)
        for spec in (self.lane or {}).get("alias_reads") or []:
            base = locations.get(spec.get("location") or "")
            if not base:
                continue
            for name in self.names:
                parts = [str(p).replace("{name}", name) for p in spec.get("path") or []]
                if any(os.sep in p or p in ("", ".", "..") for p in parts):
                    continue
                path = os.path.join(base, *parts)
                try:
                    if not self.world.fs.isfile(path):
                        continue
                    text = self.world.fs.read_text(path)
                except (OSError, UnicodeDecodeError):
                    continue
                for line in text.splitlines():
                    line = line.strip()
                    if line and line not in names and line not in self.names:
                        names.append(line)
        return names

    # ---- 3. the run directory -------------------------------------------------------------------
    def _stop_on_rundir(self, cause, run_id, has_go):
        self.locks.release_all()
        lines = [self.view.line(texts.RUNDIR_STOP[cause]), self.view.naming(texts.THE_RUN, run_id)]
        raise Ended("stopped" if has_go else "refused", [l for l in lines if l])

    def open_run_directory(self, run_id, secret_reads_of):
        """Open a run directory that exists: RUN-4's checks, then that run's disproof read."""
        fs = self.world.fs
        self.run_id = run_id
        self.run_kind = run_kind_of(run_id)
        self.run_dir = self.facts.run_dir(run_id)
        has_go = self.is_open or self.partner is not None
        try:
            self.journal = rundir.check(fs, self.run_dir)
        except rundir.Failed as failed:
            self._stop_on_rundir(failed.cause, run_id, has_go)
        try:
            self.owed, self.receipts_owed = disproof.startup_read(
                self.world, self.run_dir, self.journal, self.register, self.tokens, secret_reads_of(self))
        except rundir.Failed as failed:
            self._stop_on_rundir(failed.cause, run_id, has_go or self.journal.count() > 0)
        self.continues = True
        self.locks.rewrite(run_id)

    def make_run_directory(self, run_id):
        self.run_id = run_id
        self.run_kind = run_kind_of(run_id)
        self.run_dir = rundir.create(self.world, self.facts, run_id)
        self.journal = journalmod.Journal(self.run_dir, [])
        self.register.add(self._fingerprint_key(), (), None, "fingerprint key")

    def _fingerprint_key(self):
        from . import protected
        return protected.read_key(self.world.fs, self.run_dir)

    def startup_passed(self):
        """The startup checks have passed. One act stands here, before the first journal record, and is no journal
        record: an invocation that continues a run removes a private password file that a kill left in that run
        directory, whatever it was summoned for, a status and a close among them (SEC-12, the order of first records;
        SEC-2; the reviewer's P1). A stop by the startup checks never reaches here, and leaves the file where it is."""
        self.passed = True
        self.printer.passed = True
        if self.continues and self.run_dir:
            for path in rundir.left_password_files(self.world.fs, self.run_dir):
                self.world.fs.remove(path)

    # ---- once the startup checks have passed ----------------------------------------------------
    def first_records(self, word=None):
        """The one order of first records (SEC-12): disproof records owed, receipts owed, EV-7's
        `closed` record where the handover owes it, then the record of what the invocation was
        summoned for. Returns the records written."""
        written = disproof.write_owed(self.world, self.journal, self.register, self.owed, self.receipts_owed)
        self.owed, self.receipts_owed = [], []
        if self.closed_owed is not None:
            retirement, restore_id = self.closed_owed
            retirement.append(self.world, "run-end", register=self.register, ending="closed", by="a restore's go",
                              restore=restore_id)
            self.closed_owed = None
        if word is not None:
            kind, fields = word
            written.append(self.journal.append(self.world, kind, register=self.register, **fields))
        return written

    def finish(self):
        """The invocation is ending: every lock it holds is released."""
        if self.locks is not None:
            self.locks.release_all()
