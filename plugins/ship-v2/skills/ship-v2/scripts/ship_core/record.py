"""ship-v2's use of the records component (ruling E15-9, CR-24; contract sections 6 and 10).

    client(run, records_root=None) -> the component, confirmed at interface version 2 (exit 3 when it is missing)
    open_findings(run, ...) -> the findings the records hold open, from `state`, never recomputed here
    named(run, ...) -> the findings a lap fixes: every open BLOCKER and MAJOR charged to the slice, the fix-introduced
        defects charged to it, and its open MINORs when the owner's invocation ordered them
    event(run, kind, finding, words, identity, at) -> a grant's `waived` or `reopened` event

Reads: `state` (the open set and the cards). The grant itself, the one write ship-v2 makes (its event with the owner's
words verbatim, `grant_date` the run's date, `actor` this station, this run's id and the harness, and the card it moves
by v1's rule), is `grant.py`'s, in build-v2's transaction (the E15 lane contract A27 (1)); the stations ship-v2 visits
write their own records. The component is reached through the resolver
snippet and the CLI only (`station_core/records_client.py`, `records_link.py`); no log file is opened here.
"""
from station_core import records_link

from . import common

GRANTS = {"waive": "waived", "reopen": "reopened"}
ADMITS = {"waived": ("open", "fixed"), "reopened": ("fixed", "waived")}


def client(run, records_root=None):
    return records_link.open_client(common.STATION, records_root=records_root)


def findings(run, records_root=None):
    """Every finding the records hold for the doc, from `state`."""
    body = client(run, records_root).state(common.workspace(run), common.state(run)["doc"])
    return body.get("findings") or []


def open_findings(run, slice_name=None, records_root=None):
    rows = [f for f in findings(run, records_root) if f.get("status") == "open"]
    if slice_name is not None:
        rows = [f for f in rows if f.get("slice") == slice_name]
    return rows


def named(run, slice_name, records_root=None):
    """The findings a lap fixes (module docstring), each {"id", "severity", "location", "claim", "why"}."""
    minors = bool(common.station(run).get("minor_fixes"))
    out = []
    for row in open_findings(run, slice_name, records_root):
        severity = row.get("severity")
        defect = row.get("caused_by") is not None
        if severity in common.BLOCKING or defect or (minors and severity == "MINOR"):
            why = ("fix-introduced" if defect else "a %s charged to slice %s" % (severity, slice_name)
                   if severity in common.BLOCKING else "a MINOR the owner's invocation ordered fixed")
            out.append({"id": row["id"], "severity": severity, "location": (row.get("location") or {}).get("raw"),
                        "claim": row.get("claim"), "why": why})
    return out


def blocking(rows):
    return [r for r in rows if r.get("severity") in common.BLOCKING]


def event(run, kind, finding, words, identity, at):
    out = {"v": 1, "kind": kind, "at": at, "ledger_doc": common.state(run)["doc"],
           "actor": records_link.actor(common.STATION, common.run_id(run), common.harness(run)),
           "origin": {"kind": "native"}, "source": {"known": True, "identity": identity},
           "finding": finding["id"], "words": words, "grant_date": at[:10]}
    if kind == "waived":
        out.update(severity=finding["severity"], verified_source={"known": True, "identity": identity},
                   join_basis=None)
    else:
        out.update(join_basis=None)
    return out
