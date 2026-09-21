"""The event log: addresses, the chain walk, the lock, and the optimistic append.

Records E12 contract sections 6 (the log and the event), 7 (finding identity), 8.3 (a record
cannot clear findings against a different source revision), and 10 (conflicting writes).

Nothing here rewrites an event (E12-5): a log is replaced whole with its old bytes plus new
lines at the tail, through a temporary file beside it and a rename over it (the pilot's
`canon.atomic_write`). The lock file is the one other file this module writes.

The failures this module raises carry the contract's exit codes: 4 a line or an event failed
validation, 5 an ambiguous identity, 6 `stale_source`, 7 `conflict` (chain break, head mismatch,
lock held). Every failure names the line or the event it found, and an append that fails writes
nothing at all: the batch is assembled and checked whole before the first byte is written
(section 10, "batches are atomic").

Section 8.3's third condition needs to know whether a finding is open. `finding_status` answers
that from the log alone with section 9.2's deciding-event rule; since slice 2 the rule itself
lives in `state.py`, which owns the whole of section 9, and this module calls it.
"""
import errno
import fcntl
import json
import os
import subprocess

from . import canon, identity as identity_mod, ids, validate

ZERO_HEAD = "0" * 64
RECORDS_DIR = "docs/records"
LOG_SUFFIX = ".events.jsonl"
LOCK_SUFFIX = ".lock"
IMPORTER_STATION = "records-import"
RAISE_KINDS = ("finding_raised", "defect_raised")
CLEAR_KINDS = ("disposition", "waived", "reopened")
COMPONENT_ASSIGNED = ("seq", "prev")


class RecordsError(Exception):
    """A failure carrying one of the contract's exit codes and the document to report."""

    def __init__(self, code, document):
        Exception.__init__(self, document.get("reason") or document.get("error") or "records error")
        self.code = code
        self.document = document


def _fail(code, error, reason, **extra):
    doc = {"ok": False, "error": error, "reason": reason}
    doc.update(extra)
    raise RecordsError(code, doc)


# ---- addresses (section 6.1) ------------------------------------------------------------------

def slug_of(doc):
    """`docs/plans/2026-09-06-readers.md` -> `docs__plans__2026-09-06-readers`.

    Amendment A8: the slug is one-to-one. A literal `%` is written `%25` and a literal `_` is
    written `%5F` BEFORE every `/` becomes `__`, so `docs/a/b.md` and `docs/a__b.md` no longer
    share one log (`docs__a__b` against `docs__a%5F%5Fb`). The escape order matters: `%` first,
    or `%5F` in a name would decode as an underscore.
    """
    rel = doc.replace("\\", "/").strip("/")
    if rel.endswith(".md"):
        rel = rel[:-3]
    return rel.replace("%", "%25").replace("_", "%5F").replace("/", "__")


def log_relpath(doc):
    return "%s/%s%s" % (RECORDS_DIR, slug_of(doc), LOG_SUFFIX)


def log_path(workspace, doc):
    """The log's absolute path, refused (exit 4) when any step of it is a symbolic link.

    Amendment A8: a log, a lock, or the `docs/records/` directory reached through a symbolic
    link is refused, so a write cannot leave the workspace and a read cannot be pointed at a
    specification file. The whole chain below the workspace root is checked, and the resolved
    path must still sit inside the root.
    """
    path = os.path.join(workspace, *log_relpath(doc).split("/"))
    root = os.path.realpath(workspace)
    for target in (path, lock_path(path)):
        cursor = workspace
        for part in os.path.relpath(target, workspace).split(os.sep):
            cursor = os.path.join(cursor, part)
            if os.path.islink(cursor):
                _fail(4, "invalid", "a records path cannot traverse a symbolic link: %s" % cursor,
                      path=cursor)
        resolved = os.path.realpath(target)
        if resolved != root and not resolved.startswith(root + os.sep):
            _fail(4, "invalid", "a records path resolves outside the workspace: %s" % target,
                  path=target)
    return path


def lock_path(log):
    return log + LOCK_SUFFIX


def orphan_temporaries(log):
    """The sibling temporary files a killed write can leave beside `log`, as relative paths.

    Review finding 15: `canon.atomic_write` writes through `.<log name>.<random>.tmp` in the
    same directory and renames it over the log, so a process killed between the two leaves that
    file behind as well as its lock. Nothing removes it silently: `--break-lock` reports what it
    finds and a person decides.
    """
    directory = os.path.dirname(log) or "."
    prefix = "." + os.path.basename(log) + "."
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return []
    return ["%s/%s" % (RECORDS_DIR, name) for name in names
            if name.startswith(prefix) and name.endswith(".tmp")]


def history_address(doc, seq):
    return {"log": log_relpath(doc), "seq": seq}


def spec_address(doc, slice_name=None):
    return {"doc": doc, "slice": slice_name}


# ---- reading and the chain (section 10) -------------------------------------------------------

def line_hash(raw):
    """The hash a `prev` names: SHA-256 of the line's bytes without its newline."""
    return canon.sha256_hex(raw)


def head_of(raw_lines):
    return ZERO_HEAD if not raw_lines else line_hash(raw_lines[-1])


def split_log(data):
    """The log's lines as bytes, or a validation failure about its framing.

    The log is UTF-8, one object per line, LF endings, one trailing newline (section 6.1).
    """
    if data == b"":
        return []
    if b"\r" in data:
        line = data.split(b"\r", 1)[0].count(b"\n") + 1
        _fail(4, "invalid", "the log holds a carriage return; lines are LF-terminated (section 6.1)", line=line)
    if not data.endswith(b"\n"):
        _fail(4, "invalid", "the log does not end with a newline (section 6.1)", line=data.count(b"\n") + 1)
    parts = data.split(b"\n")[:-1]
    for i, raw in enumerate(parts):
        if raw == b"":
            _fail(4, "invalid", "the log holds an empty line (section 6.1)", line=i + 1)
    return parts


def walk(path, schemas, doc=None):
    """Read and check a log. Returns {"exists", "raw", "events", "head"}; raises on the first bad line.

    The order is the contract's: every line parses and validates (exit 4, the line named; an
    unknown `v` is refused here, never skipped, E12-7), then `seq` equals the line index and
    `prev` equals the hash of the line before (exit 7, `conflict`, the first bad line named).

    With `doc` given, every reader also checks that each event names the document this log
    belongs to (amendment A8): a log holding another document's event was joined or edited from
    outside, which is exit 7 (`conflict`) the way a joined tail is.
    """
    if not os.path.isfile(path):
        return {"exists": False, "raw": [], "events": [], "head": ZERO_HEAD}
    with open(path, "rb") as fh:
        data = fh.read()
    raw_lines = split_log(data)
    events = []
    expected_prev = ZERO_HEAD
    for i, raw in enumerate(raw_lines):
        number = i + 1
        try:
            event = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            _fail(4, "invalid", "line %d does not parse as JSON: %s" % (number, exc), line=number)
        errors = validate.validate_event(event, schemas)
        if errors:
            _fail(4, "invalid", "line %d fails the event schema at %s: %s"
                  % (number, errors[0]["path"] or "/", errors[0]["message"]),
                  line=number, errors=errors)
        if raw != canon.canonical_json(event):
            # Section 6.1: one CANONICAL JSON object per line. A line that parses and validates
            # but is not canonical hashes differently from the same event written by this
            # component, so every `prev` after it would be unreproducible (review finding 7).
            _fail(4, "invalid", "line %d is not canonical JSON (section 6.1: sorted keys, no "
                                "insignificant whitespace)" % number, line=number)
        if event["seq"] != i:
            _fail(7, "conflict", "line %d carries seq %d; the line index is %d (E12-4)"
                  % (number, event["seq"], i), line=number, seq=event["seq"], expected_seq=i)
        if event["prev"] != expected_prev:
            _fail(7, "conflict", "line %d carries prev %s; the line before hashes to %s"
                  % (number, event["prev"], expected_prev),
                  line=number, prev=event["prev"], expected_prev=expected_prev)
        if doc is not None and event.get("ledger_doc") != doc:
            _fail(7, "conflict", "line %d names ledger_doc %r; this log belongs to %r (amendment A8)"
                  % (number, event.get("ledger_doc"), doc), line=number,
                  ledger_doc=event.get("ledger_doc"), expected_ledger_doc=doc)
        events.append(event)
        expected_prev = line_hash(raw)
    return {"exists": True, "raw": raw_lines, "events": events, "head": head_of(raw_lines)}


# ---- the smallest piece of derived state slice 1 needs (section 8.3, section 9.2) -------------

def raised_ids(events):
    """{finding id: the event that raised it} in seq order."""
    out = {}
    for event in events:
        if event.get("kind") in RAISE_KINDS:
            out.setdefault(event.get("finding"), event)
    return out


def finding_status(events, finding):
    """`open` | `fixed` | `waived` for one finding, or None when the log never raised it.

    Section 9.2's deciding-event rule, owned by `state.py` since slice 2. The import is local
    because `state` imports this module for section 6.1's addresses; this is the only direction
    that would otherwise be a cycle.
    """
    from . import state as state_mod
    return state_mod.finding_status(events, finding)


# ---- the lock (section 10) --------------------------------------------------------------------

def process_start(pid):
    """The process's start time as `ps` reports it, or None when no such process is running.

    A pid is not an identity (guide, skill-helper-recipes L171): a recycled pid carries a
    different start time, so a lock whose pid is alive under a different start time is not held.
    """
    try:
        proc = subprocess.run(["ps", "-o", "lstart=", "-p", str(int(pid))],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, ValueError, TypeError):
        return None
    if proc.returncode != 0:
        return None
    text = proc.stdout.decode("utf-8", "replace").strip()
    return text or None


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError, TypeError) as exc:
        return getattr(exc, "errno", None) == errno.EPERM
    return True


def holder_alive(info):
    """Is the process that took this lock still running? pid plus its recorded start time."""
    if not isinstance(info, dict):
        return False  # a lock file of the wrong shape names no holder (review finding 4)
    pid = info.get("pid")
    if not isinstance(pid, int) or not pid_alive(pid):
        return False
    recorded = info.get("pid_start")
    if not recorded:
        return True  # a lock with no recorded start time: the live pid is all there is to go on
    current = process_start(pid)
    return current is None or current == recorded


def read_lock(path):
    """The lock's contents as an object, or a `{pid, pid_start, unreadable}` stand-in.

    Review finding 4: a lock file that is valid JSON of the WRONG SHAPE (`[]`, a string, a
    number) used to reach `holder_alive` as a list and end the command in a traceback. It is now
    reported the same way an unparseable lock is: a documented refusal, exit 7, with the reason
    in `lock.unreadable`.
    """
    try:
        with open(path, "rb") as fh:
            info = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        return {"pid": None, "pid_start": None, "unreadable": str(exc)}
    if not isinstance(info, dict):
        return {"pid": None, "pid_start": None,
                "unreadable": "the lock file holds a JSON %s, not an object" % type(info).__name__}
    return info


LOCK_FIELDS = ("pid", "pid_start", "command", "unreadable")
FOREIGN_LOCK = "the lock file holds fields this component does not write"


def published_lock(info):
    """The documented lock object, built from whatever the lock file held.

    Send-back 2: `read_lock` returns the file's contents, and a lock file another tool wrote
    was published verbatim, so a SUCCESS response could carry a `broke_lock` its own schema
    refuses (`{"owner": "...", "pid": "999999"}` was the control room's probe). The component
    PUBLISHES a lock; it does not pass one through. `interface.md` already documents the four
    fields, so this is an implementation correction and not a new shape:

    - `pid` is a JSON integer or null; anything else, a bool included, is null;
    - `pid_start` is a string or null;
    - `command` is kept only when it is a non-empty string;
    - `unreadable` is kept when `read_lock` set it, and is otherwise `FOREIGN_LOCK` when any key
      was dropped or any value nulled on a lock that WAS readable JSON, so a reader can tell a
      foreign lock from one of ours;
    - every other key is dropped.

    For every lock this component writes this returns the same object it was given, byte for
    byte in the response. The liveness judgement never comes through here: `holder_alive` reads
    the RAW contents, so no lock that is refused today is broken tomorrow, or the reverse.
    """
    if not isinstance(info, dict):
        return {"pid": None, "pid_start": None,
                "unreadable": "the lock file holds a JSON %s, not an object"
                              % type(info).__name__}
    out = {"pid": None, "pid_start": None}
    dropped = bool(set(info) - set(LOCK_FIELDS))
    pid = info.get("pid")
    if isinstance(pid, int) and not isinstance(pid, bool):
        out["pid"] = pid
    elif info.get("pid") is not None:
        dropped = True
    start = info.get("pid_start")
    if isinstance(start, str):
        out["pid_start"] = start
    elif start is not None:
        dropped = True
    command = info.get("command")
    if isinstance(command, str) and command:
        out["command"] = command
    elif command is not None:
        dropped = True
    unreadable = info.get("unreadable")
    if isinstance(unreadable, str) and unreadable:
        out["unreadable"] = unreadable
    elif unreadable is not None:
        dropped = True
    if dropped and "unreadable" not in out:
        out["unreadable"] = FOREIGN_LOCK
    return out


def read_lock_bytes(fd):
    """Every byte behind an open lock descriptor, or None when it cannot be read.

    Verification item 4: ownership of a lock is its CONTENTS as well as its inode. The file is
    tiny and written in one `os.write`, so one read from the start is the whole of it; a read
    that fails is reported as "not the bytes I am looking for" rather than as a traceback.
    """
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        return os.read(fd, os.fstat(fd).st_size + 1)
    except OSError:
        return None


class Lock:
    """`<log>.lock`, created with O_CREAT | O_EXCL, holding the pid and its start time.

    A lock that exists is exit 7 with its contents; `--break-lock` removes one only when its pid
    is not alive and says so in the response. No waiting, no retry loop (section 10).

    Review finding 4: the lock is an INODE, not a pathname. The file descriptor stays open for
    the lock's whole life and carries an advisory `flock` (stdlib `fcntl`, macOS and Linux), so:

    - a breaker cannot take a lock whose inode another writer is holding, however dead the pid
      recorded inside it looks (that writer took the file over and published itself into it);
    - `release` unlinks only while the file at the path is still the inode this process created,
      so a holder never deletes its replacement's lock;
    - `assert_owned`, called immediately before the log is replaced, stops a write whose lock was
      removed and re-created under it.

    Verification item 4: the inode is not the whole of the lock's identity. A writer that takes
    an abandoned lock file over publishes itself INTO it, keeping the inode, so the inode checks
    above see nothing. Both sides therefore compare bytes as well: recovery compares the bytes it
    judged stale against the bytes present when it is about to unlink, and release compares the
    bytes it wrote. A lock rewritten in place is refused (exit 7) on recovery and left alone on
    release.
    """

    def __init__(self, log, command):
        self.path = lock_path(log)
        self.command = command
        self.broke = None
        self.held = False
        self.fd = None
        self.owned_bytes = None  # exactly what this process wrote into its own lock

    def _contents(self):
        return {"pid": os.getpid(), "pid_start": process_start(os.getpid()), "command": self.command}

    def _same_inode(self, fd):
        """Is the file at the path still the open file this descriptor names?"""
        try:
            if os.path.islink(self.path):
                return False
            named, held = os.lstat(self.path), os.fstat(fd)
        except OSError:
            return False
        return (named.st_dev, named.st_ino) == (held.st_dev, held.st_ino)

    def _take_inode_lock(self, fd, info=None):
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN):
                raise
            _fail(7, "conflict", "the log's lock is held: another process owns its inode, whatever "
                                 "the pid inside it says (%s)" % self.path,
                  lock=published_lock(info if info is not None else read_lock(self.path)),
                  lock_path=self.path, holder_alive=True)

    def assert_owned(self):
        """The lock at the path is still the one this process took, or exit 7 and no write."""
        if self.fd is None or not self._same_inode(self.fd):
            _fail(7, "conflict", "the log's lock was removed or replaced while this process held "
                                 "it; nothing was written (%s)" % self.path, lock_path=self.path)

    def acquire(self, break_lock=False):
        flags = os.O_RDWR | os.O_NOFOLLOW
        try:
            fd = os.open(self.path, flags | os.O_CREAT | os.O_EXCL, 0o644)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
            fd = self._recover(break_lock)
        try:
            self._take_inode_lock(fd)
            if not self._same_inode(fd):
                _fail(7, "conflict", "the log's lock was replaced while this process was taking it: "
                                     "%s" % self.path, lock_path=self.path)
            self.owned_bytes = canon.canonical_json(self._contents()) + b"\n"
            os.write(fd, self.owned_bytes)
        except BaseException:
            if self._same_inode(fd):
                try:
                    os.unlink(self.path)
                except OSError:
                    pass
            os.close(fd)
            raise
        self.fd = fd
        self.held = True
        return self

    def _recover(self, break_lock):
        """A lock file already exists: refuse it, or remove a stale one and take its place."""
        try:
            existing = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError as exc:
            _fail(7, "conflict", "the log's lock exists and cannot be opened to be read (%s): %s"
                  % (self.path, exc), lock_path=self.path,
                  lock=published_lock({"pid": None, "pid_start": None,
                                       "unreadable": str(exc)}), holder_alive=True)
        try:
            observed = read_lock_bytes(existing)
            info = read_lock(self.path)
            if not break_lock:
                # `holder_alive` reads the RAW contents; only the response is published.
                _fail(7, "conflict", "the log's lock is held: %s" % self.path,
                      lock=published_lock(info), lock_path=self.path,
                      holder_alive=holder_alive(info))
            if holder_alive(info):
                _fail(7, "conflict", "the log's lock is held by a live process; --break-lock removes a "
                                     "lock only when its pid is not alive",
                      lock=published_lock(info), lock_path=self.path, holder_alive=True)
            # The recorded holder is gone. Its INODE must be free too: every holder of this
            # component takes the advisory lock before it publishes itself into the file, so an
            # inode another process still holds belongs to a writer that took this lock over.
            self._take_inode_lock(existing, info)
            if not self._same_inode(existing):
                _fail(7, "conflict", "the log's lock was replaced while this one was being read: %s"
                      % self.path, lock=published_lock(read_lock(self.path)),
                      lock_path=self.path, holder_alive=holder_alive(read_lock(self.path)))
            # The inode is unchanged, but its CONTENTS may not be: a writer that took this file
            # over wrote itself into it while the recorded holder was being judged dead. The
            # lock this process is about to remove must still be the lock it read.
            current = read_lock_bytes(existing)
            if observed is None or current is None or current != observed:
                _fail(7, "conflict", "the lock's contents changed while this one was deciding it "
                                     "was stale; nothing was removed: %s" % self.path,
                      lock=published_lock(read_lock(self.path)), lock_path=self.path,
                      holder_alive=holder_alive(read_lock(self.path)))
            os.unlink(self.path)
            self.broke = published_lock(info)
        finally:
            os.close(existing)
        try:
            return os.open(self.path, os.O_RDWR | os.O_NOFOLLOW | os.O_CREAT | os.O_EXCL, 0o644)
        except OSError as again:
            if again.errno != errno.EEXIST:
                raise
            # another breaker took the lock between the unlink and this open: still a held
            # lock, so it is the same refusal, never an unhandled error
            broke, self.broke = self.broke, None
            _fail(7, "conflict", "the log's lock was taken by another process while this one was "
                                 "breaking the stale lock: %s" % self.path,
                  lock=published_lock(read_lock(self.path)), lock_path=self.path,
                  broke_lock=broke, holder_alive=holder_alive(read_lock(self.path)))

    def release(self):
        if self.fd is None:
            self.held = False
            return
        try:
            # Its own inode AND its own bytes: a lock whose contents another writer replaced in
            # place is that writer's, however much the file this descriptor names looks like it.
            if (self.owned_bytes is not None and self._same_inode(self.fd)
                    and read_lock_bytes(self.fd) == self.owned_bytes):
                try:
                    os.unlink(self.path)
                except OSError:
                    pass
        finally:
            os.close(self.fd)
            self.fd = None
            self.held = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


# ---- the append (sections 7, 8.3, 10) ---------------------------------------------------------

def _refuse_component_fields(event, position):
    for field in COMPONENT_ASSIGNED:
        if field in event:
            _fail(4, "invalid", "event %d carries `%s`; seq and prev are assigned by the component, "
                                "never by the caller (section 10)" % (position, field),
                  event_index=position, errors=[{"path": "/" + field, "message": "assigned by the component"}])


def _clear_source(event):
    """The source identity a clear was decided against (section 8.3)."""
    return event.get("verified_source")


def _is_clear(event):
    kind = event.get("kind")
    return (kind == "disposition" and event.get("disposition") == "fixed") or kind == "waived"


def _is_legacy_import(event):
    origin = event.get("origin")
    actor = event.get("actor")
    return (isinstance(origin, dict) and origin.get("kind") == "legacy"
            and isinstance(actor, dict) and actor.get("station") == IMPORTER_STATION)


def _refuse_legacy_from_a_station(event, position):
    """Only the importer writes legacy records into a log (sections 8.3, 11; owner ruling O4).

    A caller that is not the importer may not present an event carrying `origin.kind: "legacy"`
    or the importer's station, whatever else it says: those two fields are what the O4 exemption
    is read from, and they are written by the caller.
    """
    origin = event.get("origin")
    actor = event.get("actor")
    legacy = isinstance(origin, dict) and origin.get("kind") == "legacy"
    importer_station = isinstance(actor, dict) and actor.get("station") == IMPORTER_STATION
    if not (legacy or importer_station):
        return
    field = "/origin/kind" if legacy else "/actor/station"
    _fail(4, "invalid", "event %d is presented as a legacy record (%s); a legacy record enters a log "
                        "only through `import-legacy`, which reads it from the document itself "
                        "(section 11). `append` writes native events." % (position, field),
          event_index=position,
          errors=[{"path": field, "message": "legacy records are the importer's to write, not a station's"}])


def prepare_batch(workspace, doc, incoming, existing, schemas, identity_of=None, importer=False):
    """Assemble the batch: assign seq and prev, apply sections 7 and 8.3, validate every event.

    Returns [(event, line bytes)] in order. Raises on the first refusal; nothing is written by
    this function, so a refusal leaves the log untouched (section 10, batches are atomic).

    `importer` is False for every caller but slice 2's `importer.py`, and the CLI never sets it.
    With it False, an event carrying `origin.kind: "legacy"` or the importer's station is refused
    before anything else about it is judged (exit 4), so owner ruling O4's exemption cannot be
    claimed by declaring it. With it True, that exemption applies to a clear whose origin is
    legacy and whose station is `records-import`, and to nothing else.
    """
    if identity_of is None:
        identity_of = identity_mod.source_identity
    events = list(existing["events"])
    prev = existing["head"]
    known = raised_ids(events)
    prepared = []
    workspace_identity = [None]  # computed once, and only when a clear needs it

    def actual_identity():
        if workspace_identity[0] is None:
            workspace_identity[0] = identity_of(workspace)
        return workspace_identity[0]

    for position, given in enumerate(incoming, 1):
        if not isinstance(given, dict):
            _fail(4, "invalid", "event %d is not a JSON object" % position, event_index=position)
        if not importer:
            _refuse_legacy_from_a_station(given, position)
        _refuse_component_fields(given, position)
        if not validate.known_version(given):
            err = validate.unknown_version_error(given)
            _fail(4, "invalid", "event %d: %s" % (position, err["message"]), event_index=position, errors=[err])
        event = dict(given)
        event["seq"] = len(events)
        event["prev"] = prev
        if event.get("ledger_doc") != doc:
            _fail(4, "invalid", "event %d names ledger_doc %r; this log is the one for %r"
                  % (position, event.get("ledger_doc"), doc), event_index=position,
                  errors=[{"path": "/ledger_doc", "message": "must equal the document this log belongs to"}])
        kind = event.get("kind")
        if kind in RAISE_KINDS:
            computed = ids.id_of_event(event)
            if "finding" in event and event["finding"] != computed:
                _fail(4, "invalid", "event %d carries finding %r; its fields compute to %s (section 7)"
                      % (position, event.get("finding"), computed), event_index=position,
                      errors=[{"path": "/finding", "message": "the finding ID is computed from the event's own fields"}])
            event["finding"] = computed
        # the schema runs before sections 7 and 8.3, so those rules read a well-formed event
        errors = validate.validate_event(event, schemas)
        if errors:
            _fail(4, "invalid", "event %d fails the event schema at %s: %s"
                  % (position, errors[0]["path"] or "/", errors[0]["message"]),
                  event_index=position, errors=errors)
        if kind in RAISE_KINDS and event["finding"] in known:
            held = known[event["finding"]]
            _fail(5, "ambiguous_identity", "event %d raises a finding the log already holds (%s, raised at seq %d); "
                                           "send a `reopened` or a new claim, never a second raise (section 7)"
                  % (position, event["finding"], held["seq"]),
                  event_index=position, finding=event["finding"],
                  candidates=[history_address(doc, held["seq"])])
        named = []
        if kind in CLEAR_KINDS:
            named.append(("/finding", event.get("finding")))
        if kind == "defect_raised" and event.get("caused_by") is not None:
            named.append(("/caused_by", event.get("caused_by")))
        for path, finding in named:
            if finding not in known:
                _fail(5, "ambiguous_identity", "event %d names finding %s at %s; the log does not hold it (section 7)"
                      % (position, finding, path), event_index=position, finding=finding, path=path)
        if _is_clear(event):
            _check_clear(event, position, events, doc, actual_identity, importer)
        raw = canon.canonical_json(event)
        prepared.append((event, raw))
        events.append(event)
        if kind in RAISE_KINDS:
            known[event["finding"]] = event
        prev = line_hash(raw)
    return prepared


def _check_clear(event, position, events, doc, actual_identity, importer=False):
    """Section 8.3: a record cannot clear findings against a different source revision.

    All three conditions are one rule and one refusal (exit 6, `stale_source`), with the reason
    naming the condition that failed and both identities in the response wherever they exist.
    The importer is the one writer allowed to append a clear with `known: false`, and only with
    `origin.kind: "legacy"` (owner ruling O4); such a clear is exempt from all three, because an
    imported clear keeps its effect and history is not changed. The exemption needs the caller to
    BE the importer (`importer=True`, which the CLI never passes), not merely to say it is.
    """
    if importer and _is_legacy_import(event):
        return
    source = _clear_source(event)
    if not (isinstance(source, dict) and source.get("known") is True):
        _fail(6, "stale_source", "event %d clears %s with no known source; a clear written from E12 onward "
                                 "carries a full source identity (section 8.3)" % (position, event.get("finding")),
              event_index=position, finding=event.get("finding"), condition="known",
              expected=(source.get("identity") if isinstance(source, dict) else None),
              actual=actual_identity())
    expected = source.get("identity")
    actual = actual_identity()
    differing = identity_mod.differing_fields(expected, actual)
    if differing:
        _fail(6, "stale_source", "event %d clears %s against a source that is not the workspace: %s differ "
                                 "(section 8.3)" % (position, event.get("finding"), ", ".join(differing)),
              event_index=position, finding=event.get("finding"), condition="identity",
              differing_fields=differing, expected=expected, actual=actual)
    status = finding_status(events, event.get("finding"))
    if status != "open":
        _fail(6, "stale_source", "event %d clears %s, which is %s at the log's current head, not open "
                                 "(section 8.3)" % (position, event.get("finding"), status),
              event_index=position, finding=event.get("finding"), condition="open",
              status=status, expected=expected, actual=actual)


def commit_batch(path, workspace, doc, existing, prepared, lock=None, importer=False,
                 identity_of=None):
    """Write the batch, from the bytes that were validated and only if nothing moved under it.

    Review finding 3. The writer used to re-read the file it had already walked and append to
    whatever it found; a log truncated, or a tracked source file changed, between the walk and
    the write therefore landed a batch that was never checked against what it was written onto.
    The old bytes are now rebuilt from `existing["raw"]`, the lines the walk validated, and:

    - the file on disk must still be exactly those bytes (exit 7, `conflict`);
    - the workspace identity must still equal the one every bound clear in the batch names
      (exit 6, `stale_source`), which is section 8.3 re-asked at the moment of the write;
    - this process must still own the lock inode it took (exit 7, review finding 4).

    Nothing is written when any of the three fails.
    """
    if identity_of is None:
        identity_of = identity_mod.source_identity
    old = b"".join(raw + b"\n" for raw in existing["raw"])
    try:
        with open(path, "rb") as fh:
            current = fh.read()
        exists = True
    except (IOError, OSError):
        current, exists = b"", False
    if exists != existing["exists"] or current != old:
        _fail(7, "conflict", "the log changed between the walk that validated it and this write; "
                             "nothing was written. Re-read the log and decide (section 10)",
              log=log_relpath(doc), head=existing["head"], events=len(existing["events"]))
    actual = None
    for position, (event, _) in enumerate(prepared, 1):
        if not _is_clear(event) or (importer and _is_legacy_import(event)):
            continue
        if actual is None:
            actual = identity_of(workspace)
        expected = (event.get("verified_source") or {}).get("identity")
        differing = identity_mod.differing_fields(expected, actual)
        if differing:
            _fail(6, "stale_source", "the workspace changed between the check and this write: %s "
                                     "differ from what event %d clears against (section 8.3). "
                                     "Nothing was written." % (", ".join(differing), position),
                  event_index=position, finding=event.get("finding"), condition="identity",
                  differing_fields=differing, expected=expected, actual=actual,
                  log=log_relpath(doc), head=existing["head"], events=len(existing["events"]))
    if lock is not None:
        lock.assert_owned()
    canon.atomic_write(path, old + b"".join(raw + b"\n" for _, raw in prepared))


def append(workspace, doc, incoming, expect_head, schemas, break_lock=False, identity_of=None,
           importer=False):
    """Sections 7, 8.3 and 10's append. Returns the response body; raises RecordsError on refusal.

    The order is: take the lock (a held lock is exit 7 with its contents), walk the log (a break
    is exit 4 or 7), compare the head the caller read with the head on disk (exit 7 with both),
    assemble and check the whole batch, then write old bytes plus the new lines through a
    temporary file beside the log and a rename over it. Nothing is written unless every event
    passed.

    `importer=True` is slice 2's `importer.py` and nothing else: it admits legacy-origin events
    and owner ruling O4's unbound clear. `records.py append` never passes it, and has no flag
    that could.
    """
    path = log_path(workspace, doc)
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)  # docs/records/ holds the log and its lock; both are excluded from 8.2's identity
    lock = Lock(path, "append")
    try:
        lock.acquire(break_lock=break_lock)
    except RecordsError as exc:
        exc.document.setdefault("log", log_relpath(doc))
        raise
    orphans = orphan_temporaries(path) if break_lock else None
    try:
        existing = walk(path, schemas, doc=doc)
        if expect_head != existing["head"]:
            _fail(7, "conflict", "the log's head is %s; the caller expected %s. Re-read the log and decide "
                                 "(section 10)" % (existing["head"], expect_head),
                  expected_head=expect_head, actual_head=existing["head"],
                  log=log_relpath(doc), head=existing["head"], events=len(existing["events"]))
        try:
            prepared = prepare_batch(workspace, doc, incoming, existing, schemas,
                                     identity_of=identity_of, importer=importer)
        except RecordsError as exc:
            # every response that involves a log carries its address, head and count (section 12.2)
            exc.document.setdefault("log", log_relpath(doc))
            exc.document.setdefault("head", existing["head"])
            exc.document.setdefault("events", len(existing["events"]))
            raise
        if not prepared:
            _fail(2, "usage", "the events file holds no event")
        commit_batch(path, workspace, doc, existing, prepared, lock=lock, importer=importer,
                     identity_of=identity_of)
        head = line_hash(prepared[-1][1])
        body = {
            "log": log_relpath(doc),
            "head": head,
            "events": len(existing["events"]) + len(prepared),
            "appended": [{"seq": event["seq"], "kind": event["kind"], "finding": event.get("finding"),
                          "history": history_address(doc, event["seq"])} for event, _ in prepared],
            "spec": spec_address(doc),
            "expected_head": expect_head,
        }
        if lock.broke is not None:
            body["broke_lock"] = lock.broke
        if break_lock:
            body["orphan_temporaries"] = orphans
        return body
    finally:
        lock.release()
