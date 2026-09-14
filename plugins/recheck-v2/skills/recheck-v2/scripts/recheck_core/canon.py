"""Canonical bytes, digests, and the two write primitives the core uses everywhere.

- canonical_json / sha256_hex match fixturelib.canonical_json / sha256_hex byte for byte
  (pilot contract section 11; evals/README.md "Identity encoding"): keys sorted, separators
  "," and ":", UTF-8, non-ASCII unescaped.
- atomic_write replaces a target whole: the bytes go to a temporary file beside the target,
  then os.replace over it (pilot contract section 9).
- log_then_rename fixes the order section 11 requires for checkpoint.json and receipt.json:
  the announcing line is appended to the log (and flushed to disk) BEFORE the rename lands.
"""
import hashlib
import json
import os
import tempfile


def canonical_json(obj) -> bytes:
    """The canonical serialization of section 11 (identical to fixturelib.canonical_json)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    """SHA-256 of a file's bytes, read in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write(path: str, data: bytes) -> None:
    """Write data to path through a temporary file beside it and os.replace.

    The target is therefore always at its old bytes or its new bytes, never in between. The
    temporary file is removed if the write fails before the rename. The parent directory must
    exist.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("atomic_write takes bytes, not %s" % type(data).__name__)
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def log_then_rename(log_path: str, line: str, target: str, data: bytes) -> None:
    """Append one line to the log, flush it to disk, THEN atomically replace the target.

    This is the order pilot contract section 11 fixes for checkpoint.json and receipt.json:
    the log announces the write ("<seq> <self>") before the rename, so a crash between the two
    leaves the one tolerated state (a log one line ahead of the file), never a file ahead of
    its log. `line` is written with exactly one trailing newline.
    """
    text = line.rstrip("\n") + "\n"
    with open(log_path, "ab") as fh:
        fh.write(text.encode("utf-8"))
        fh.flush()
        os.fsync(fh.fileno())
    atomic_write(target, data)
