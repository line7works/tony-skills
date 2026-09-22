"""Scope adherence: the source set against the paths the slice names.

Lane contract section 9. The contract phase writes the slice's requirements and its named paths
to the run's contract file BEFORE any edit is recorded, so the scope is fixed before the
comparison rather than fitted to it afterwards. At report time every path of the source set that
the slice does not name is listed as out of scope WITH the executor's stated reason, from the
recorded answer's `edits[].reason`; a path with no reason stops the run. Never silently.

What "with a reason" does and does not mean: a stated reason does not make the path in scope, and
this core never judges whether the reason is a good one — that is the inspector's job. It means
the executor said why, in writing, and the reason travels with the path into the result so a
reader can weigh it.
"""
from . import doc as docmod, sources


def out_of_scope(source, named_paths, reasons, not_in_slice=()):
    """[{path, lists, reason, reason_given, named_in_not_in_slice}], sorted by path.

    A SANCTIONED path of the source set is passed over: it is in the set, a reader sees it there
    with the reason it is sanctioned, and it is never out of scope. Today that is the ledger
    document this run is executing, which the loop writes into by design.
    """
    sanctioned = sources.sanctioned_paths(source)
    rows = []
    for path in sources.all_paths(source):
        if path in sanctioned or docmod.in_named_paths(path, named_paths):
            continue
        reason = reasons.get(path)
        rows.append({
            "path": path,
            "lists": sources.lists_holding(source, path),
            "reason": reason,
            "reason_given": bool(reason and reason.strip()),
            "named_in_not_in_slice": docmod.in_named_paths(path, not_in_slice),
        })
    rows.sort(key=lambda row: row["path"])
    return rows


def unexplained(rows):
    return [row for row in rows if not row["reason_given"]]


def stop_sentence(rows):
    """The stop a path with no stated reason produces, naming every such path."""
    missing = unexplained(rows)
    return ("%d path(s) of the source set are outside the paths the slice names and the recorded "
            "answer gives no reason for them: %s. A path outside the slice's scope is reported "
            "with the executor's stated reason or the run stops; it is never passed over in "
            "silence." % (len(missing), ", ".join(row["path"] for row in missing)))
