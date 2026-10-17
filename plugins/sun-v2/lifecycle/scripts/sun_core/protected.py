"""Protected records (the frame's SEC-6, SEC-7).

A protected record is a file in the run directory's protected folder, owner-only, kept with the run.
The journal, a manifest and a form refer to it only by a reference: an id the run assigns (never
derived from the content), its type, a label the tool wrote from safe content, and a fingerprint
keyed with a random value made for the run and kept only in that folder. The content is never in a
reference.

A secret field's value is kept in an envelope, so that what the register holds of it can be built
again whenever it is read back (SEC-4): the value as the answer wrote it, whether it is a text, and
whether it passed its validator.
"""
import hashlib
import hmac
import json
import os

from . import fsio

TYPES = ("before-image", "after-image", "definition", "line", "values", "copy", "held field", "secret field")
KEY_NAME = "key"


class Unreadable(RuntimeError):
    """A protected record is missing or fails its fingerprint."""


def folder(run_dir):
    return os.path.join(run_dir, "protected")


def path_of(run_dir, record_id):
    return os.path.join(folder(run_dir), record_id)


def make_key(world, run_dir):
    world.fs.write_new(os.path.join(folder(run_dir), KEY_NAME), (world.random_hex(32) + "\n").encode("ascii"))


def read_key(fs, run_dir):
    return fs.read_text(os.path.join(folder(run_dir), KEY_NAME)).strip()


def fingerprint(key, content):
    return hmac.new(key.encode("ascii"), content, hashlib.sha256).hexdigest()


def write(world, run_dir, record_id, content, kind, label):
    """Write the record and read it back against its fingerprint; returns its reference."""
    if kind not in TYPES:
        raise ValueError("not a type of protected record: %s" % kind)
    fs = world.fs
    key = read_key(fs, run_dir)
    fs.write_new(path_of(run_dir, record_id), content)
    mark = fingerprint(key, content)
    if fingerprint(key, fs.read(path_of(run_dir, record_id))) != mark:
        raise Unreadable(record_id)
    return {"record": record_id, "type": kind, "label": label, "fingerprint": mark}


def read(fs, run_dir, reference):
    """The content a reference names, proven against its fingerprint."""
    try:
        content = fs.read(path_of(run_dir, reference["record"]))
        key = read_key(fs, run_dir)
    except (OSError, KeyError, TypeError):
        raise Unreadable(reference.get("record") if isinstance(reference, dict) else "?")
    if fingerprint(key, content) != reference.get("fingerprint"):
        raise Unreadable(reference["record"])
    return content


def present(fs, run_dir, record_id):
    return fs.lexists(path_of(run_dir, record_id))


def envelope(raw, is_text, passed, components=()):
    """A secret field's value as it is kept: `raw` is the text itself for a text, and for a value
    that is not a text the whole of it as the answer writes it. `components` is what the register
    holds beside the value (SEC-4, SEC-12), so that it holds the same whenever this is read back."""
    return fsio.canonical_json({"secret_field": 1, "raw": raw, "text": bool(is_text), "passed": bool(passed),
                                "components": list(components)}).encode("utf-8")


def open_envelope(content):
    try:
        doc = json.loads(content.decode("utf-8"))
    except ValueError:
        raise Unreadable("envelope")
    if (not isinstance(doc, dict) or doc.get("secret_field") != 1 or not isinstance(doc.get("raw"), str)
            or not isinstance(doc.get("components"), list)):
        raise Unreadable("envelope")
    return doc
