"""Reading a disproof record's value back from where the record says it rests (the frame's SEC-12).

A disproof record holds nothing of the value. For a value from a secret field it names the
protected record that holds it; for a channel secret, of which the tool keeps no copy, it names the
recorded content that holds it, by its place (a file of the run directory) and the span within it.
"""
import os

from . import protected, rundir

CONTENT_FILES_PREFIX = ("manifest-", "journal.jsonl")   # and every saved input (`rundir.is_inputs_name`)


class Unreadable(RuntimeError):
    """The value of a disproof record cannot be read where the record says it rests."""


def reference_of(record):
    """What a form writes beside the fixed words: the disproof record's own place in the journal."""
    return "disproof %d" % record.get("n", -1)


def read_value(fs, run_dir, record):
    """(value, components) of one disproof record."""
    rests = record.get("rests")
    if not isinstance(rests, dict):
        raise Unreadable("rests")
    if "protected" in rests:
        try:
            content = protected.read(fs, run_dir, rests["protected"])
            doc = protected.open_envelope(content)
        except protected.Unreadable:
            raise Unreadable("protected")
        return doc["raw"], [c for c in doc["components"] if isinstance(c, str)]
    span = rests.get("content")
    if not isinstance(span, dict):
        raise Unreadable("rests")
    name, start, end = span.get("file"), span.get("start"), span.get("end")
    if (not isinstance(name, str) or os.sep in name
            or not (rundir.is_inputs_name(name) or name.startswith(CONTENT_FILES_PREFIX))
            or not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end):
        raise Unreadable("span")
    try:
        data = fs.read(os.path.join(run_dir, name))
    except OSError:
        raise Unreadable("content")
    if end > len(data):
        raise Unreadable("span")
    try:
        return data[start:end].decode("utf-8"), []
    except UnicodeDecodeError:
        raise Unreadable("span")


def read_all(fs, run_dir, records):
    """([(record, value, components)], every value read) over the disproof records given."""
    out, every = [], True
    for record in records:
        if record.get("kind") != "disproof":
            continue
        try:
            value, components = read_value(fs, run_dir, record)
        except Unreadable:
            every = False
            continue
        out.append((record, value, components))
    return out, every
