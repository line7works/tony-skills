"""Canonical bytes, digests and the two write primitives this core uses everywhere.

The same three rules the pilot fixes (pilot contract sections 9 and 11):

- `canonical_json` / `sha256_hex`: keys sorted, separators "," and ":", UTF-8, non-ASCII
  unescaped. Two machines hash one object to one value.
- `atomic_write` replaces a target whole: the bytes go to a temporary file beside the target,
  then `os.replace` over it, so the target is always at its old bytes or its new bytes and never
  in between. A run killed inside a write leaves a `.<name>.<random>.tmp` beside the target and
  nothing half written.
- `log_then_rename` fixes the order for `receipt.json` and `checkpoint.json`: the announcing
  line reaches the log and the disk BEFORE the rename lands, so a crash between the two leaves
  the one tolerated state (a log one line ahead of the file), never a file ahead of its log.
"""
import hashlib
import json
import os
import tempfile


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def sha256_text(text):
    return sha256_hex(text.encode("utf-8"))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file_or_none(path):
    """The file's digest, or None when it is not there. A missing target is a state, not an error."""
    if not os.path.isfile(path):
        return None
    return sha256_file(path)


def atomic_write(path, data):
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


def write_json(path, doc):
    """A run artifact: the document, indented and key-sorted, written whole."""
    atomic_write(path, (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))


def read_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def log_then_rename(log_path, line, target, data):
    """Append one line to the log, flush it to disk, THEN atomically replace the target."""
    text = line.rstrip("\n") + "\n"
    with open(log_path, "ab") as fh:
        fh.write(text.encode("utf-8"))
        fh.flush()
        os.fsync(fh.fileno())
    atomic_write(target, data)
