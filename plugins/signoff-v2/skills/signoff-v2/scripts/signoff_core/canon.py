"""Canonical serialization, hashing and the two-step write (the pilot's `recheck_core.canon`).

Every artifact this station writes is replaced whole: the new content goes to a temporary file
beside the target and is renamed over it, so a target is always at the hash before or the hash
after a planned step, never in between. A receipt is announced in its log before the rename, so
an interrupted rewrite leaves the one tolerated state.
"""
import hashlib
import json
import os
import tempfile


def canonical_json(doc):
    """Sorted keys, no insignificant whitespace, non-ASCII kept; UTF-8 bytes."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file_or_none(path):
    return sha256_file(path) if os.path.isfile(path) else None


def atomic_write(path, data):
    """Write `data` (str or bytes) to `path` through a sibling temporary file and a rename."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    folder = os.path.dirname(os.path.abspath(path)) or "."
    if not os.path.isdir(folder):
        os.makedirs(folder)
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return path


def write_json(path, doc):
    """A JSON artifact a person reads: two-space indent, sorted keys, one trailing newline."""
    text = json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return atomic_write(path, text)


def log_then_rename(path, doc, line):
    """Announce the write in `<path>.log`, then replace `path`.

    The log line lands first, so an interrupt between the two leaves a log whose last line
    describes a write the file may not carry — a state a reader can name — rather than a file
    whose provenance nothing recorded (the guide's L33)."""
    log_path = path + ".log" if not path.endswith(".json") else path[:-len(".json")] + ".log"
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(line.rstrip("\n") + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    write_json(path, doc)
    return path, log_path


def read_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def relpath_inside(root, path):
    """`path` as a normalized workspace-relative path, or None when it escapes `root`.

    Only one side is resolved (the guide's L144): the root's real path is compared with the
    candidate's real path, so a symbolic link out of the workspace is caught."""
    root_real = os.path.realpath(root)
    candidate = path if os.path.isabs(path) else os.path.join(root, path)
    real = os.path.realpath(candidate)
    if real != root_real and not real.startswith(root_real + os.sep):
        return None
    rel = os.path.relpath(real, root_real)
    return "" if rel == "." else rel.replace(os.sep, "/")
