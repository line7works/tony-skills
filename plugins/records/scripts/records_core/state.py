"""Derived state (records E12 contract section 9).

State is a pure function of the log's bytes (9.1): the same log gives the same state object,
byte for byte, on any machine. Nothing is cached on disk in E12, and nothing here reads the
workspace, the ledger document, or the clock.

Per finding (9.2): `id`, `slice`, `severity`, `location`, `claim`, `scenario`, `status`
(`open` | `fixed` | `waived`), `cleared_unbound` (true when the deciding clear has
`known: false`), `join_basis` of the deciding event, `raised` and `decided` as history
addresses, and `events` (every `seq` that names it). The deciding event is the last event in
`seq` order that names the finding among `disposition`, `waived`, `reopened`; none means open.
This is Appendix A's open filter with the finding ID as the join key, so "later in the file
wins" becomes "later in `seq` wins" (E12-4).

Per slice (9.3): `open` by severity, `card_derived`, `card_observed`, `card_drift`.
`card_derived` is Appendix A's mapping over everything still open for the slice, with the one
exception section 9.3 names: a slice last observed or set at `built` keeps `built`.
`docs/punch-list.md` has no card, so its slices carry null cards and never drift. The component
reports drift; it never corrects a card in E12.

`at_source` is section 8.4: per cleared finding, `cleared_at_this_source` is true only when the
clear's `verified_source.identity.commit` equals the given commit and the clear was bound. It
changes no state.
"""
from . import events as events_mod, legacy

STATUSES = ("open", "fixed", "waived")
SEVERITIES = ("BLOCKER", "MAJOR", "MINOR")
DECIDING_KINDS = ("disposition", "waived", "reopened")
BUILT = "built"
NO_CARD_DOC = legacy.PUNCH_LIST_DOC


def _status_after(event, current):
    kind = event.get("kind")
    if kind == "disposition":
        return "fixed" if event.get("disposition") == "fixed" else "open"
    if kind == "waived":
        return "waived"
    if kind == "reopened":
        return "open"
    return current


def _finding_rows(doc, events):
    """{finding id: the per-finding object of section 9.2}, in the order the findings were raised."""
    rows = {}
    order = []
    for event in events:
        finding = event.get("finding")
        if not isinstance(finding, str):
            continue
        kind = event.get("kind")
        if kind in events_mod.RAISE_KINDS:
            if finding in rows:
                continue  # section 7 refuses a second raise; a log that holds one keeps the first
            order.append(finding)
            rows[finding] = {
                "id": finding,
                "slice": event.get("slice"),
                "severity": event.get("severity"),
                "location": event.get("location"),
                "claim": event.get("claim"),
                "scenario": event.get("scenario"),
                "status": "open",
                "cleared_unbound": False,
                "join_basis": None,
                "raised": events_mod.history_address(doc, event["seq"]),
                "decided": None,
                "events": [event["seq"]],
                "raised_by": event.get("raised_by"),
                "caused_by": event.get("caused_by") if kind == "defect_raised" else None,
            }
            continue
        row = rows.get(finding)
        if row is None:
            continue  # a log whose chain `append` wrote can hold no such event (section 7)
        row["events"].append(event["seq"])
        if kind not in DECIDING_KINDS:
            continue
        row["status"] = _status_after(event, row["status"])
        row["decided"] = events_mod.history_address(doc, event["seq"])
        row["join_basis"] = event.get("join_basis")
        source = event.get("verified_source")
        cleared = row["status"] in ("fixed", "waived")
        row["cleared_unbound"] = bool(
            cleared and not (isinstance(source, dict) and source.get("known") is True))
        row["_deciding_source"] = source if cleared else None
    return order, rows


def _card_events(events):
    """{slice: the last card value observed or set}, plus the raw text of the last observation."""
    cards = {}
    for event in events:
        kind = event.get("kind")
        if kind == "card_observed":
            cards[event.get("slice")] = {"card": event.get("card"), "text": event.get("value"),
                                         "seq": event["seq"], "kind": kind}
        elif kind == "card_set":
            cards[event.get("slice")] = {"card": event.get("after"), "text": event.get("after"),
                                         "seq": event["seq"], "kind": kind}
    return cards


def card_derived(open_severities, observed_card):
    """Appendix A's mapping (section 9.3). A slice last observed or set at `built` keeps `built`."""
    if observed_card == BUILT:
        return BUILT
    if "BLOCKER" in open_severities:
        return "rejected"
    if "MAJOR" in open_severities:
        return "signed off with conditions"
    return "signed off"


def _slice_rows(doc, order, rows, cards):
    has_card = doc != NO_CARD_DOC
    names = set()
    for finding in order:
        names.add(rows[finding]["slice"] or "none")
    names.update(name for name in cards if isinstance(name, str))
    out = []
    for name in legacy.sort_slices(sorted(names)):
        open_counts = dict((s, 0) for s in SEVERITIES)
        open_severities = set()
        for finding in order:
            row = rows[finding]
            if (row["slice"] or "none") != name or row["status"] != "open":
                continue
            severity = row["severity"]
            if severity in open_counts:
                open_counts[severity] += 1
            open_severities.add(severity)
        seen = cards.get(name)
        observed = seen["card"] if seen else None
        derived = card_derived(open_severities, observed) if has_card else None
        out.append({
            "name": name,
            "open": open_counts,
            "open_total": sum(open_counts.values()),
            "card_derived": derived,
            "card_observed": observed if has_card else None,
            "card_observed_text": (seen["text"] if seen else None) if has_card else None,
            "card_drift": bool(has_card and observed is not None and derived is not None
                               and observed != derived),
        })
    return out


def state_of(doc, events, at_source=None, slice_name=None):
    """The derived-state object of section 9 for one document's events.

    `at_source` is section 8.4's identity: when given, every cleared finding carries
    `cleared_at_this_source`. `slice_name` filters both findings and slices to one slice.
    """
    order, rows = _finding_rows(doc, events)
    cards = _card_events(events)
    findings = []
    for finding in order:
        row = dict(rows[finding])
        source = row.pop("_deciding_source", None)
        if at_source is not None:
            row["cleared_at_this_source"] = bool(
                isinstance(source, dict) and source.get("known") is True
                and isinstance(source.get("identity"), dict)
                and source["identity"].get("commit") == at_source.get("commit"))
        findings.append(row)
    slices = _slice_rows(doc, order, rows, cards)
    if slice_name is not None:
        findings = [f for f in findings if (f["slice"] or "none") == slice_name]
        slices = [s for s in slices if s["name"] == slice_name]
    totals = dict((s, 0) for s in SEVERITIES)
    for row in findings:
        if row["status"] == "open" and row["severity"] in totals:
            totals[row["severity"]] += 1
    return {
        "spec": events_mod.spec_address(doc, slice_name),
        "findings": findings,
        "slices": slices,
        "open": totals,
        "counts": {
            "findings": len(findings),
            "open": sum(totals.values()),
            "fixed": sum(1 for f in findings if f["status"] == "fixed"),
            "waived": sum(1 for f in findings if f["status"] == "waived"),
            "cleared_unbound": sum(1 for f in findings if f["cleared_unbound"]),
        },
        "at_source": {"commit": at_source.get("commit")} if at_source is not None else None,
        "filters": {"slice": slice_name},
    }


def finding_status(events, finding):
    """`open` | `fixed` | `waived` for one finding, or None when the log never raised it.

    Section 8.3's third condition, answered from the same walk the whole state object uses.
    `events.py` calls this one (slice 1 carried its own copy until slice 2 landed section 9).
    """
    status = None
    for event in events:
        if event.get("finding") != finding:
            continue
        kind = event.get("kind")
        if kind in events_mod.RAISE_KINDS:
            status = "open"
        elif kind in DECIDING_KINDS:
            status = _status_after(event, status or "open")
    return status
