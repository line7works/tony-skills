"""Small file helpers: hashes, canonical JSON, atomic writes. Standard library only."""
import hashlib
import json
import os
import tempfile


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha256_file_or_none(path):
    try:
        return sha256_file(path)
    except OSError:
        return None


def canonical_json(doc):
    return json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def dumps(doc):
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def atomic_write(path, data):
    """Write `data` (bytes) to `path` through a temporary file in the same directory and a rename."""
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=folder)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def write_json(path, doc):
    atomic_write(path, dumps(doc).encode("utf-8"))


def read_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def inside(path, root):
    """Whether the real path of `path` is `root` or lies under it (both resolved)."""
    real, base = os.path.realpath(path), os.path.realpath(root)
    return real == base or real.startswith(base.rstrip(os.sep) + os.sep)
