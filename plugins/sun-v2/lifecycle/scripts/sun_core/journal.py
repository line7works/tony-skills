"""The journal: written ahead, durable, chained (the frame's LOG-1).

One file per run, `journal.jsonl`, one record per line. A record is appended, flushed and synced
together with its directory before the step it describes begins. Every record carries the hash of
the record before it (`prev`) and its own (`h`, over `prev` and the record's canonical bytes), so a
record changed anywhere, the last one included, breaks the chain.

Reading back. A record is whole when its line ends in a newline. A last line with no newline is a
cut-off record: it is discarded and its operation is treated as if that record had never been
written. Anything else that does not read back (a whole line that does not parse, a hash that does
not match, a number out of order, a kind this rule does not list) is a break in the chain, and the
invocation stops. Nothing but this one tolerated state is repaired.

The kinds, and no other (LOG-1):

    open            the run's opening under its keys, with the go that opened it (RUN-3, RUN-9)
    go              a later go, on a re-plan's manifest (RUN-11)
    word            a later word of the owner's: to go on, that a step is done, to leave it (RUN-10)
    start, step, answer, completion, status     an operation's records (LOG-2, OP-6)
    attempt         one making of a check (OP-8)
    waiting, owner-answer                       an owner operation's records (OP-9)
    disproof        a safe ground disproved (SEC-12)
    invocation-end  how an invocation ended (RUN-12)
    run-end         how the run ended; `closed` among the endings (RUN-13, EV-7)
"""
import hashlib
import json
import os

from . import fsio

FILE_NAME = "journal.jsonl"
KINDS = ("open", "go", "word", "start", "step", "answer", "completion", "status", "attempt", "waiting",
         "owner-answer", "disproof", "invocation-end", "run-end")
ZERO = "0" * 64
FIRST_MOST = 65536        # bytes: the bound past which the look does not read a journal's first line (RUN-5)


def opening_most(count):
    """The longest record of a run's opening the go can write under `count` keys, its end mark included: every other field
    at the longest its schema lets it be (RUN-5: the bound is set "above the longest record of a run's opening the tool
    writes"). A key's fingerprint is 64 characters, so only the count of keys moves it."""
    body = {"n": 0, "kind": "open", "at": "0" * 40, "prev": ZERO, "inv": "i-" + "f" * 16, "run": "restore-" + "f" * 16,
            "run_kind": "restore", "keys": ["f" * 64] * count, "manifest": 2 ** 63, "manifest_sha256": "f" * 64, "word": "go",
            "closes": "restore-" + "f" * 16, "h": "f" * 64}
    return len(fsio.canonical_json(body).encode("utf-8")) + 1


def opening_fits(count):
    """Whether a run opened under `count` keys keeps its record of its opening within what a look reads of a first record
    (`FIRST_MOST`): a line is read whole only where its end mark stands within the first `FIRST_MOST` bytes."""
    return opening_most(count) <= FIRST_MOST


class Broken(RuntimeError):
    """The journal does not read back whole (RUN-4's second check)."""


class Withheld(RuntimeError):
    """A record would have carried a value the register holds; it was not written (SEC-12)."""


def path_of(run_dir):
    return os.path.join(run_dir, FILE_NAME)


def _hash(prev, body):
    return hashlib.sha256((prev + fsio.canonical_json(body)).encode("utf-8")).hexdigest()


def _parse(data):
    """(records, whole, tail): every record that reads back in order, whether the chain held from
    the first record to the last, and the byte length of a cut-off last record (0 where none)."""
    records, prev, whole = [], ZERO, True
    lines = data.split(b"\n")
    tail = len(lines[-1])
    for index, raw in enumerate(lines[:-1]):
        try:
            record = json.loads(raw.decode("utf-8"))
            body = dict((k, v) for k, v in record.items() if k != "h")
            good = (isinstance(record, dict) and record.get("n") == index and record.get("prev") == prev
                    and record.get("h") == _hash(prev, body) and record.get("kind") in KINDS)
        except (ValueError, AttributeError):
            record, good = None, False
        if not good:
            whole = False
            if isinstance(record, dict):
                records.append(record)
                prev = record.get("h") if isinstance(record.get("h"), str) else prev
            continue
        records.append(record)
        prev = record["h"]
    return records, whole, tail


class Journal(object):
    def __init__(self, run_dir, records, tail=0, size=0):
        self.run_dir = run_dir
        self.path = path_of(run_dir)
        self.records = records
        self.tail = tail        # bytes of a cut-off last record still in the file
        self.size = size        # bytes of the whole records

    @classmethod
    def exists(cls, fs, run_dir):
        return fs.lexists(path_of(run_dir))

    @classmethod
    def read(cls, fs, run_dir):
        """The journal, strictly: a break anywhere but a cut-off last record raises `Broken`."""
        if not fs.lexists(path_of(run_dir)):
            return cls(run_dir, [])
        data = fs.read(path_of(run_dir))
        records, whole, tail = _parse(data)
        if not whole:
            raise Broken("chain")
        return cls(run_dir, records, tail, len(data) - tail)

    @classmethod
    def read_lenient(cls, fs, run_dir):
        """(records as far as they can be read, whether the chain held first to last). Never raises
        on content: the withheld read uses it on other runs' journals, whatever state they are in."""
        if not fs.lexists(path_of(run_dir)):
            return [], True, False
        try:
            data = fs.read(path_of(run_dir))
        except OSError:
            return [], False, True
        records, whole, _tail = _parse(data)
        return records, whole, True

    @classmethod
    def first_record(cls, fs, run_dir):
        """What a run directory's journal holds first, read as RUN-5 has the look read it, and nothing more of it:

        - ("none", None): no journal, the directory having none (or the entry being no directory);
        - ("cut", None): the journal holds only a cut-off record: its first line has no newline, by LOG-1's own test (a
          record is whole when its line ends in a newline), a file of no bytes among them (an append cut off at once);
        - ("open", record): its first record, whole, is a record of a run's opening: it reads back as the first record of
          its chain (its number, the hash before it and its own hash), with its keys as fingerprints;
        - ("unreadable", None): the first record is there and cannot be read: the journal or the directory cannot be
          read by its owner, or its first whole line is no record of a run's opening (the owner's ruling, A57).
        A first line longer than `FIRST_MOST` bytes is not read past that bound and is one that cannot be read."""
        path = path_of(run_dir)
        try:
            fs.lstat(path)
        except (FileNotFoundError, NotADirectoryError):
            return "none", None
        except OSError:
            return "unreadable", None
        try:
            line, whole = fs.read_first_record(path, FIRST_MOST)
        except OSError:
            return "unreadable", None
        if whole is False:
            return "cut", None
        if whole is None:
            return "unreadable", None
        try:
            record = json.loads(line.decode("utf-8"))
            body = dict((k, v) for k, v in record.items() if k != "h") if isinstance(record, dict) else None
        except (UnicodeDecodeError, ValueError):
            return "unreadable", None
        keys = record.get("keys") if isinstance(record, dict) else None
        if (body is None or record.get("kind") != "open" or record.get("n") != 0 or record.get("prev") != ZERO
                or record.get("h") != _hash(ZERO, body) or not isinstance(keys, list)
                or not all(isinstance(k, str) for k in keys)):
            return "unreadable", None
        return "open", record

    def count(self):
        return len(self.records)

    def last_hash(self):
        return self.records[-1]["h"] if self.records else ZERO

    def of_kind(self, *kinds):
        return [r for r in self.records if r.get("kind") in kinds]

    def for_op(self, op):
        return [r for r in self.records if r.get("op") == op]

    def append(self, world, kind, register=None, **fields):
        """One record, durable before this returns. A record that would carry a register entry is
        not written (SEC-12)."""
        if kind not in KINDS:
            raise ValueError("not a kind of journal record: %s" % kind)
        body = {"n": len(self.records), "kind": kind, "at": world.now(), "prev": self.last_hash(),
                "inv": world.invocation}
        body.update(fields)
        record = dict(body)
        record["h"] = _hash(body["prev"], body)
        line = fsio.canonical_json(record)
        if register is not None and register.holds(line):
            raise Withheld(kind)
        from . import schemas
        schemas.check("journal-record", record)
        if self.tail:
            world.fs.truncate(self.path, self.size)
            self.tail = 0
        world.note("pre", "journal", kind, operation=fields.get("op"), step=fields.get("step"))
        world.fs.append(self.path, (line + "\n").encode("utf-8"))
        self.size += len(line.encode("utf-8")) + 1
        self.records.append(record)
        world.note("post", "journal", kind, operation=fields.get("op"), step=fields.get("step"))
        return record
