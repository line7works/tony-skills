"""The cards after this run's grants, the next-slice candidates and the next move (CR-14; contract section 7).

    parse_depends(value, names) -> [slice names] or None (a chain the reading cannot place)
    effective(card, open_findings) -> the card after v1's update rule (verdict cards only)
    candidates(rows) -> {"names": [...], "unreadable": [...]}
    finished_of(rows, given=None) -> the just-finished slice's name, or None
    ambiguous(rows, finished) -> the next-slice question's candidates, or None when the record yields one answer
    resolve(rows, doc, finished=None, owner=None) -> the move

A row is `{"name", "card", "depends", "open"}`: the slice's card (for `resolve`, after this run's grants), its
`Depends on:` chain as names (None when unreadable), and its open findings (each `{"id", "slice", "severity",
"location", "claim"}`). The script reads; the rule decides nothing about wisdom (ruling E15-4).

THE CARD AFTER THE GRANTS (v1's Step 4 rule, which the records component's `card_derived` implements; E15-9: no
card event and no `Status:` write here). A slice whose card is a verdict (`rejected`, `signed off with conditions`,
`signed off`) takes the card its open findings give, waived ones excluded: any BLOCKER open gives `rejected`, else
any MAJOR open gives `signed off with conditions`, else `signed off`. Any other card (`built`, `in progress`,
`not started`, `none`) is kept: a rebuilt slice never takes a verdict from a grant.

THE CANDIDATES. A slice whose card is `not started` or `in progress` and whose every `Depends on:` slice stands
`signed off`; a slice of those two cards whose chain cannot be read is named as unreadable and is no candidate.

THE SHAPES, in this order (v1's Step 7):

1. `open-card`: any slice's card is `rejected` or `signed off with conditions`, or any BLOCKER or MAJOR is open.
   The move is the fix list (every open BLOCKER and MAJOR, slices in document order) then `recheck-v2` on each such
   slice. No kickoff line to ship.
2. `loop-complete`: the doc holds slices and every one stands `signed off`. No kickoff line.
3. the owner's answer to the next-slice question: a slice name gives `clean-boundary` on that slice, `how` owner (it
   must be a slice of the doc: never a slice that does not exist; `record-answer` takes only one that stands `not
   started` or `in progress`, a candidate or not, C1B1-5); null gives `owner-holds`, no kickoff line.
4. `clean-boundary`: the just-finished slice (if any) stands `signed off` and exactly one candidate exists.
5. otherwise `unresolved`, with the candidates: the record does not yield exactly one answer, which is the
   next-slice question the gate asks (and `record-answer` refuses a set of answers that leaves the move here).
"""
import re

VERDICT_CARDS = ("rejected", "signed off with conditions", "signed off")
OPEN_CARDS = ("rejected", "signed off with conditions")
SIGNED_OFF = "signed off"
STARTABLE = ("not started", "in progress")
GATING = ("BLOCKER", "MAJOR")
NOTHING = ("", "nothing", "none")


def parse_depends(value, names):
    """The slice names a `Depends on:` value lists, or None when a part names no slice of the doc (the chain is then
    unreadable, and the next-slice question asks). Parenthesized asides are set aside first; `nothing`, `none` and an
    empty value list none; parts are split on commas and on ` and `; a leading `Slice ` or `Slices ` and a trailing
    `merged`, `has merged` or `is merged` are set aside from each part. Nothing else is read: a part such as an
    outside pull request or `after Slice E has merged` names no slice and leaves the chain unreadable."""
    if value is None:
        return None
    text = value
    while True:
        shorter = re.sub(r"\([^()]*\)", "", text)
        if shorter == text:
            break
        text = shorter
    text = text.strip().rstrip(".").strip()
    if text.casefold() in NOTHING:
        return []
    out = []
    for part in re.split(r",|\band\b", text):
        part = part.strip()
        if not part:
            continue
        part = re.sub(r"^(?:slices?)\s+", "", part, flags=re.IGNORECASE)
        part = re.sub(r"\s+(?:(?:has|is)\s+)?merged$", "", part, flags=re.IGNORECASE).strip()
        if part not in names:
            return None
        out.append(part)
    return out


def effective(card, open_findings):
    if card not in VERDICT_CARDS:
        return card
    severities = set(f["severity"] for f in open_findings)
    if "BLOCKER" in severities:
        return "rejected"
    if "MAJOR" in severities:
        return "signed off with conditions"
    return SIGNED_OFF


def candidates(rows):
    cards = dict((r["name"], r["card"]) for r in rows)
    names, unreadable = [], []
    for row in rows:
        if row["card"] not in STARTABLE:
            continue
        if row["depends"] is None:
            unreadable.append(row["name"])
            continue
        if all(cards.get(dep) == SIGNED_OFF for dep in row["depends"]):
            names.append(row["name"])
    return {"names": names, "unreadable": unreadable}


def finished_of(rows, given=None):
    """The just-finished slice: the one the input names, else the last slice in document order whose card is not
    `not started`, else None."""
    if given:
        return given
    started = [r["name"] for r in rows if r["card"] != "not started"]
    return started[-1] if started else None


def _open_card(rows):
    gating = [f for r in rows for f in r["open"] if f["severity"] in GATING]
    return any(r["card"] in OPEN_CARDS for r in rows) or bool(gating)


def ambiguous(rows, finished):
    """The candidates the next-slice question offers, or None when the record yields one answer (or the move is the
    fix list, or the loop is complete)."""
    if rows and (_open_card(rows) or all(r["card"] == SIGNED_OFF for r in rows)):
        return None
    found = candidates(rows)
    cards = dict((r["name"], r["card"]) for r in rows)
    if rows and (finished is None or cards.get(finished) == SIGNED_OFF) and len(found["names"]) == 1:
        return None
    return found


def resolve(rows, doc, finished=None, owner=None):
    names = [r["name"] for r in rows]
    if rows and _open_card(rows):
        fix = [f for r in rows for f in r["open"] if f["severity"] in GATING]
        recheck = [r["name"] for r in rows if r["card"] in OPEN_CARDS
                   or any(f["severity"] in GATING for f in r["open"])]
        return {"shape": "open-card", "doc": doc, "fix_list": fix, "recheck": recheck}
    if rows and all(r["card"] == SIGNED_OFF for r in rows):
        return {"shape": "loop-complete", "doc": doc}
    if owner is not None:
        if owner.get("slice") is None:
            return {"shape": "owner-holds", "doc": doc, "words": owner.get("words")}
        if owner["slice"] not in names:
            raise ValueError("the owner's answer names slice %r, which the build doc does not hold" % owner["slice"])
        return {"shape": "clean-boundary", "doc": doc, "slice": owner["slice"], "how": "owner",
                "words": owner.get("words")}
    found = candidates(rows)
    cards = dict((r["name"], r["card"]) for r in rows)
    if rows and (finished is None or cards.get(finished) == SIGNED_OFF) and len(found["names"]) == 1:
        return {"shape": "clean-boundary", "doc": doc, "slice": found["names"][0], "how": "record"}
    return {"shape": "unresolved", "doc": doc, "candidates": found["names"], "unreadable": found["unreadable"]}
