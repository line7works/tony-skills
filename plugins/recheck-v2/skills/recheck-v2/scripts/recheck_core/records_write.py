"""Every record the recording transaction writes, as events for `records.py append`.

E13 slice 1, brief 3.3. The pilot decides exactly what it decided before (ruling E13-1); the
decision is now an EVENT, and the Markdown it places is that event rendered by
`records.py render --run-id <run_id>`. The rendering is byte-identical to the pilot's own
renderers, which is what the parity suite proves.

The order inside one append is the order section 8 fixes for the document, so the rendered block
and grants come back in the order the pilot places them:

    reopened (per accepted reopening grant, by date then index)
    disposition (per checklist item, in checklist order)
    defect_raised (per fix-introduced defect)
    waived (per accepted waiver grant, by date then index)

`card_set` is NOT in that batch. A status-line step the boundary check cancels must leave no
`card_set` behind, so a card is recorded in a second, later append, under the same receipt
pattern, only for a status step that actually landed.

Every event carries `actor` with the run's `run_id` and `recheck-v2` as the station. A clear
(`disposition`, `waived`) carries the full six-field `verified_source` with `known: true`; the
component refuses it (exit 6) when that identity is not the one it computes in the workspace, which
is why the pilot's identity applies the component's fixed `docs/records/` exclusion (CR-3).
"""
import os

from . import ledger, records_client as rcl, records_view as rview

STATION = rcl.STATION


def _hook(name):
    return os.environ.get("RECHECK_TEST") == "1" and os.environ.get(name) == "1"


def actor(run_id, harness):
    return {"station": STATION, "run_id": run_id, "harness": harness}


def source(identity):
    return {"known": True, "identity": dict(identity)}


def location_of(location):
    """The component's location object from the pilot's `{file, line}`."""
    return {"raw": "%s:%s" % (location["file"], location["line"]), "file": location["file"],
            "line": location["line"], "line_end": None, "tag": None, "more": [], "resolved": True}


def _base(document, run_id, harness, at, identity):
    return {"v": 1, "at": at, "ledger_doc": document, "actor": actor(run_id, harness),
            "origin": {"kind": "native"}, "source": source(identity)}


def transaction_events(document, run_id, harness, at, identity, view, checklist, item_results,
                       new_defects, waivers, reopenings, defect_causes=()):
    """The events of one recording transaction, in the order section 8 fixes.

    `waivers` and `reopenings` are the accepted grants as the plan takes them
    (`[{"index": i, "grant": g}]`); `view` resolves each grant and each checklist item to the
    finding the log already holds. `defect_causes` is the checkpoint's `new_defect_causes`, the
    checklist index behind each defect, which names the causing finding on the event.
    """
    events = []
    clear_source = source(identity)

    def finding_of(location, claim, what):
        entries = rview.match_entries(view.entries, location["file"], location["line"], claim)
        if len(entries) != 1:
            raise MissingFinding("%s names %s:%s (%s), which matches %s in the log" % (
                what, location["file"], location["line"], claim,
                "no finding" if not entries else "%d findings" % len(entries)))
        return entries[0]["finding"]

    for g in sorted(reopenings, key=lambda x: (x["grant"]["date"], x["index"])):
        grant = g["grant"]
        item = grant["item"]
        event = _base(document, run_id, harness, at, identity)
        event.update({"kind": "reopened",
                      "finding": finding_of(item["location"], item["claim"], "a reopening grant"),
                      "words": ledger.ledger_words(grant["quoted_words"]),
                      "grant_date": grant["date"], "join_basis": None})
        events.append(event)

    for item, result in zip(checklist, item_results):
        event = _base(document, run_id, harness, at, identity)
        event.update({"kind": "disposition",
                      "finding": finding_of(item["location"], item["claim"], "a checklist item"),
                      "disposition": "fixed" if result["disposition"] == "fixed" else "not_fixed",
                      "how": ledger.render_how(result["verification"]),
                      "verified_source": clear_source, "join_basis": None})
        events.append(event)

    for index, defect in enumerate(new_defects):
        event = _base(document, run_id, harness, at, identity)
        caused = defect_causes[index] if index < len(defect_causes) else None
        caused_finding = None
        if isinstance(caused, int) and 0 <= caused < len(checklist):
            caused_item = checklist[caused]
            caused_finding = finding_of(caused_item["location"], caused_item["claim"], "a fix-introduced defect")
        event.update({"kind": "defect_raised", "slice": defect["charged_to_slice"],
                      "severity": defect["severity"], "location": location_of(defect["location"]),
                      "claim": defect["claim"], "scenario": defect["failure_scenario"],
                      "raised_by": None, "caused_by": caused_finding})
        events.append(event)

    for g in sorted(waivers, key=lambda x: (x["grant"]["date"], x["index"])):
        grant = g["grant"]
        item = grant["item"]
        event = _base(document, run_id, harness, at, identity)
        event.update({"kind": "waived",
                      "finding": finding_of(item["location"], item["claim"], "a waiver grant"),
                      "severity": grant["severity"],
                      "words": ledger.ledger_words(grant["quoted_words"]),
                      "grant_date": grant["date"], "verified_source": clear_source,
                      "join_basis": None})
        events.append(event)

    return _injected(events)


def card_events(document, run_id, harness, at, identity, moves):
    """One `card_set` per status-line step that LANDED: `moves` is [(slice, before, after)]."""
    events = []
    for name, before, after in moves:
        event = _base(document, run_id, harness, at, identity)
        event.update({"kind": "card_set", "slice": name, "before": before, "after": after})
        events.append(event)
    return events


class MissingFinding(RuntimeError):
    """A record the transaction would write names no single finding in the log."""


def _injected(events):
    """The gated test hooks of brief 3.4: each makes the component refuse the real way."""
    if _hook("RECHECK_TEST_RECORDS_WRONG_SOURCE"):
        for event in events:
            if "verified_source" in event:
                spoiled = dict(event["verified_source"]["identity"])
                spoiled["commit"] = "0" * 40
                event["verified_source"] = {"known": True, "identity": spoiled}
    if _hook("RECHECK_TEST_RECORDS_INVALID_EVENT"):
        for event in events:
            event["seq"] = 0  # seq is the component's to assign; an event carrying one is exit 4
    return events


def split_grant_lines(grants):
    """`render`'s standalone lines, split the way section 8 places them: reopenings open the
    transaction, waivers land after the block."""
    reopened, waived = [], []
    for line in grants or []:
        if line.lstrip("- ").startswith(ledger.REOPENED):
            reopened.append(line)
        else:
            waived.append(line)
    return reopened, waived
