"""The two state files a run keeps, and the integrity block both carry.

`checkpoint.json` carries what one run hands from phase to phase; `receipt.json` carries the one
transaction it makes. Both are written the same way, which is the pilot's rule (pilot contract
section 11) and the guide's finding L33:

    integrity = {"seq": n, "prev": <the previous write's self, null at 0>, "self": <this one's>}

`self` is the SHA-256 of the canonical serialization of the document with `integrity.self`
removed. Before each rename, the line `<seq> <self>` is appended to the file's log and flushed to
disk; the rename follows. A crash between the two therefore leaves a log one line ahead of the
file — the one tolerated state — and never a file ahead of its log, so a rewritten file cannot
pass as a new write.

What "corrupt" means here, in the order it is checked: the file does not parse; `self` does not
recompute; `(seq, self)` is not the log's last line; `prev` is not the hash on the line before
(or is not null at seq 0); the log has a gap or a repeated seq. The one tolerated state is a log
whose last line announces a seq one past the file's while the file's own `(seq, self)` is the
line before it: that rename never landed, the last line is dropped, and the run continues.
"""
import os

from . import canon


class StateCorrupt(RuntimeError):
    """The file, its log, or the chain between them does not hold."""


def self_hash(doc):
    body = dict(doc)
    integrity = dict(body.get("integrity") or {})
    integrity["self"] = "0" * 64
    body["integrity"] = integrity
    return canon.sha256_hex(canon.canonical_json(body))


def serialize(doc):
    return (canon.canonical_json(doc).decode("utf-8") + "\n").encode("utf-8")


def read_log(path):
    """[(seq, self)] from a log file, in file order. A line that is not `<int> <64 hex>` is corrupt."""
    if not os.path.isfile(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for index, line in enumerate(fh.read().split("\n")):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) != 64:
                raise StateCorrupt("%s line %d is not an announcement: %r" % (path, index + 1, line))
            rows.append((int(parts[0]), parts[1]))
    return rows


class StateFile:
    """One state document, its log, and the write discipline above."""

    def __init__(self, path, log_path, doc):
        self.path = path
        self.log_path = log_path
        self.doc = doc

    @classmethod
    def create(cls, path, log_path, doc):
        """First write: seq 0, prev null. Any earlier file is a defect of the caller, not of this."""
        state = cls(path, log_path, dict(doc))
        state._write(0, None)
        return state

    @classmethod
    def open(cls, path, log_path):
        """Read and verify. Raises StateCorrupt naming what failed; never repairs anything but the
        one tolerated state."""
        if not os.path.isfile(path):
            raise StateCorrupt("%s is not there" % path)
        try:
            doc = canon.read_json(path)
        except ValueError as exc:
            raise StateCorrupt("%s does not parse: %s" % (path, exc))
        integrity = doc.get("integrity") or {}
        seq, own, prev = integrity.get("seq"), integrity.get("self"), integrity.get("prev")
        if not isinstance(seq, int) or not isinstance(own, str):
            raise StateCorrupt("%s carries no integrity block" % path)
        if self_hash(doc) != own:
            raise StateCorrupt("%s does not hash to its own `self`" % path)
        rows = read_log(log_path)
        if not rows:
            raise StateCorrupt("%s has no log at %s" % (path, log_path))
        seen = [row[0] for row in rows]
        if seen != list(range(len(seen))):
            raise StateCorrupt("%s has a gap or a repeated seq: %s" % (log_path, seen))
        if rows[-1] == (seq, own):
            pass
        elif len(rows) >= 2 and rows[-1][0] == seq + 1 and rows[-2] == (seq, own):
            # the one tolerated state: a rename that never landed. Drop the announcement.
            rows = rows[:-1]
            with open(log_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("".join("%d %s\n" % row for row in rows))
        else:
            raise StateCorrupt("%s is not the last write its log announces (file %s, log last %s)"
                               % (path, (seq, own[:12]), (rows[-1][0], rows[-1][1][:12])))
        if seq == 0:
            if prev is not None:
                raise StateCorrupt("%s is the first write and carries a `prev`" % path)
        else:
            if prev != rows[-2][1]:
                raise StateCorrupt("%s does not link to the write before it" % path)
        return cls(path, log_path, doc)

    def save(self):
        integrity = self.doc["integrity"]
        self._write(integrity["seq"] + 1, integrity["self"])

    def _write(self, seq, prev):
        self.doc["integrity"] = {"seq": seq, "prev": prev, "self": "0" * 64}
        self.doc["integrity"]["self"] = self_hash(self.doc)
        canon.log_then_rename(self.log_path, "%d %s" % (seq, self.doc["integrity"]["self"]),
                              self.path, serialize(self.doc))


def checkpoint_paths(run_dir):
    return os.path.join(run_dir, "checkpoint.json"), os.path.join(run_dir, "checkpoint.log")


def receipt_paths(run_dir):
    return os.path.join(run_dir, "receipt.json"), os.path.join(run_dir, "receipt.log")
