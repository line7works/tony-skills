"""Where the lanes' rows and the providers' declarations are read from (the contract's CR-2 reading).

    <rows root>/providers/<provider>.json      one declaration per provider (slice 3 writes these)
    <rows root>/<kind>/lane.json                the rows of sunrise, of sunset and of restore, each with
                                                its alias reads, phases, planning facts, questions, form
                                                changes and checklist (slices 2 and 4 write these)

The rows root is the plugin's own `lifecycle/rows/` unless the world names another. These are the
tool's own bundled declarations, read with plain file reads: they are no thing of the project and
no fact of the machine.
"""
import json
import os

KINDS = ("sunrise", "sunset", "restore")


class Unreadable(RuntimeError):
    pass


def rows_root(world):
    if world.rows_root:
        return world.rows_root
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(os.path.dirname(here)), "rows")


def _read(path):
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError):
        raise Unreadable(os.path.basename(path))


def providers(world):
    """{provider name: declaration}; {} where the folder is not there."""
    folder = os.path.join(rows_root(world), "providers")
    out = {}
    if not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json"):
            doc = _read(os.path.join(folder, name))
            if not isinstance(doc, dict) or not isinstance(doc.get("provider"), str):
                raise Unreadable(name)
            out[doc["provider"]] = doc
    return out


def lane(world, kind):
    """The lane's file for one kind of run; None where no lane has written it yet."""
    if kind not in KINDS:
        raise Unreadable(kind)
    path = os.path.join(rows_root(world), kind, "lane.json")
    if not os.path.isfile(path):
        return None
    doc = _read(path)
    if not isinstance(doc, dict):
        raise Unreadable("lane.json")
    return doc
