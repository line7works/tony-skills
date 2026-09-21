"""The legacy importer (records E12 contract section 11).

`import-legacy` reads ONE ledger document and writes (or, under `--dry-run`, only reports) the
events that represent its records, in file order, into that document's log. It never writes to
the document, to a verdict doc, or to anything outside `docs/records/`. It runs no git command
that changes state; `git blame` is read-only and is the only one it runs.

What it produces, per line of the document, in file order:

    a `Status:` line whose text is new for its slice  -> card_observed (amendment A4)
    a review finding line                            -> finding_raised
    a fix-introduced defect line                     -> defect_raised
    a recheck line                                   -> disposition
    a `WAIVED (per user)` line                       -> waived
    a `REOPENED (per user)` line                     -> reopened
    a line under a record heading that fits nothing  -> legacy_unparsed
    an answer from a resolutions file                -> resolution_applied, then what it enables

bracketed by `import_started` and `import_finished`, and preceded by `log_opened` when the log
does not exist yet. Nothing at all is written when the pass finds no new record (section 11.7,
"a second import of an unchanged document appends nothing").

Owner ruling O4: every imported clear carries `source` and `verified_source` of
`{"known": false}` and keeps its effect, so history is not changed; derived state marks the
finding `cleared_unbound`. That exemption from section 8.3 is reachable only through
`events.append(..., importer=True)`, which this module is the one caller of.

Readings this module takes where the contract left a choice; each is in the slice 2 report:

- The join table of section 11.4 holds the findings raised EARLIER in the file (and in earlier
  imports of the same document). A clear that matches only a finding raised further down is
  ambiguous under rule 4, because E12-4 makes file order time order and because `append` itself
  refuses an event naming a finding the log does not yet hold (section 7).
- Rule 1 needs a non-empty claim key on both sides; a line with no claim goes to rule 2, which
  is the pilot's own rule for a claim-less record.
- `at` is the block heading's date on a block line, the grant's date on a waiver or reopening
  line, `answered_on` on a `resolution_applied`, and the import's own UTC date on a
  `card_observed`, because a `Status:` line carries no date and section 6.2 says a `card_observed`
  records what the line said "when an import read it". `import_started` and `import_finished`
  are not legacy records at all: they carry `origin.kind: "native"` and an RFC 3339 instant.
- Owner amendment A4: a `Status:` line is an observation, not a record. It is outside both of
  section 11.7's checks (changed or moved, and the tail rule), and each pass appends a
  `card_observed` for a slice only when the current text differs from the `value` of that slice's
  last `card_observed` in the log, or when the log holds none for it. A slice whose `Status:`
  line is gone appends nothing, and a pass whose only news is one flipped card appends
  `import_started`, that `card_observed`, and `import_finished`. RECORD lines keep section 11.7
  exactly as written.
- A resolutions file carries `answered_by`, `answered_on`, and one answer per line, each with
  the `raw` text of the line as the answer was given, which is what makes section 11.5's
  "a resolution that names a line whose raw text has changed ... is rejected" checkable. The
  exit-5 report is the template: it hands back every field an answer needs.
"""
import datetime
import os
import re

from . import canon, events as events_mod, identity as identity_mod, ids, legacy

STATION = "records-import"
UNKNOWN_SOURCE = {"known": False}
COMMIT_RE = re.compile(r"(?<![0-9a-zA-Z])[0-9a-f]{40}(?![0-9a-zA-Z])")
JOIN_EXACT = "exact"
JOIN_NO_CLAIM = "location_only_no_claim"
JOIN_LOCATION = "location_only"
REJECTIONS = ("line_not_asked", "raw_changed", "unknown_finding", "answer_does_not_fit")
ITEM_KINDS = {"finding": "finding_raised", "defect": "defect_raised", "recheck": "disposition",
              "waiver": "waived", "reopening": "reopened", "unparsed": "legacy_unparsed"}
CLEAR_ITEMS = ("recheck", "waiver", "reopening")
RAISE_ITEMS = ("finding", "defect")
GRANT_ITEMS = ("waiver", "reopening")  # section 11.7: these carry the grant's own date
CUT_CLAIM_REASON = ("the field separator cut a parenthesized claim in half: this line's claim "
                    "field reads %r and its closing parenthesis is in a later field, so where "
                    "the claim ends is not written down (amendment A9)")
CUT_CLAIM_WHY = ("A claim carrying the field separator cannot be read from the line (Appendix A "
                 "forbids it there), and an answer cannot supply the claim the line does not "
                 "write down (amendment A10). Skip a raising line; for a clearing line, name an "
                 "existing finding or skip it.")


def _fail(code, error, reason, **extra):
    events_mod._fail(code, error, reason, **extra)


def utc_now():
    """This instant in UTC, whole seconds, as an AWARE datetime (carry item 5, amendment A11).

    The old `utcnow` call returned a naive datetime that only claimed to be UTC, and is
    deprecated from Python 3.12; `datetime.now(timezone.utc)` says so in the object. Every
    reader of this value formats it with `strftime` (`stamp`, `run_id_for`, a card's date),
    and `%Y`, `%m`, `%d`, `%H`, `%M` and `%S` read the same fields from either kind, with the
    `Z` a literal in the format string. The bytes this component writes are unchanged.
    """
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def run_id_for(doc, moment):
    """A deterministic run id for one import pass: the document's slug and the instant."""
    return "import-%s-%s" % (events_mod.slug_of(doc), moment.strftime("%Y%m%dT%H%M%SZ"))


# ---- the document ------------------------------------------------------------------------------

def read_document(workspace, doc):
    """(text, sha256, lines) for the ledger document, read once and never written."""
    path = os.path.join(workspace, *doc.split("/"))
    if not os.path.isfile(path):
        _fail(2, "usage", "--doc names no file in the workspace: %s" % doc, doc=doc)
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(4, "invalid", "%s is not UTF-8: %s" % (doc, exc), doc=doc)
    return text, canon.sha256_hex(data), text.split("\n")


def blame_commits(workspace, doc):
    """{1-based line: commit} from `git blame`, or {} when the document is not tracked.

    Read-only, and the only git command the importer runs. `origin.recorded_commit` says when a
    line was written down; nothing treats it as the source the line verified (section 11.7).
    """
    out = identity_mod.git(workspace, ["blame", "--line-porcelain", "--", doc], binary=True,
                           check=False)
    if out is None:
        return {}
    commits = {}
    for line in out.decode("utf-8", "replace").split("\n"):
        parts = line.split(" ")
        if len(parts) >= 3 and len(parts[0]) == 40 and COMMIT_RE.match(parts[0]):
            try:
                commits[int(parts[2])] = parts[0]
            except ValueError:
                continue
    return commits


def commit_named_in(raw):
    m = COMMIT_RE.search(raw or "")
    return m.group(0) if m else None


# ---- units: one document line, one or more events ----------------------------------------------

class Unit(object):
    """One line of the document and the events it produces, before ids and joins are settled."""

    def __init__(self, line_no, raw, kind, item=None, slice_name=None, heading=None):
        self.line_no = line_no
        self.raw = raw
        self.kind = kind  # an item kind, or "card"
        self.item = item
        self.slice_name = slice_name
        self.heading = heading


def units_of(parsed, doc):
    """Every line this import would record, in file order: the cards, then the items, merged."""
    units = []
    for s in parsed["slices"]:
        if s["status_line"] is None:
            continue
        units.append(Unit(s["status_line"] + 1, parsed["lines"][s["status_line"]].rstrip(),
                          "card", slice_name=s["name"], heading=s))
    for item in parsed["items"]:
        # Review finding 14: the line's own bytes, not the reader's rstripped copy, so that
        # section 11.7's comparison sees a changed line as changed.
        units.append(Unit(item["line_no"], parsed["lines"][item["line_no"] - 1], item["kind"],
                          item=item, heading=item.get("heading")))
    units.sort(key=lambda u: u.line_no)
    return units


# ---- section 11.7: the document has only grown ------------------------------------------------

def previously_imported(existing_events, doc):
    """{line: raw} for every RECORD line of `doc` an earlier pass of this importer recorded.

    A `card_observed` is not one of them (owner amendment A4): a `Status:` line is an
    observation, not a record, so it is outside both of section 11.7's checks. A card that a
    station flips in place, or that moves because lines were written above it, is therefore not a
    conflict; what it is instead is decided in `plan_import`, by comparing its text with the last
    value observed for that slice.
    """
    seen = {}
    for event in existing_events:
        origin = event.get("origin")
        if not isinstance(origin, dict) or origin.get("kind") != "legacy":
            continue
        if origin.get("doc") != doc or event.get("kind") == "card_observed":
            continue
        line = origin.get("line")
        if isinstance(line, int):
            seen.setdefault(line, origin.get("raw"))
    return seen


def last_card_values(existing_events, doc):
    """{slice name: the `value` of that slice's LAST `card_observed` in the log} (amendment A4).

    Matched by slice name, never by line number, so a `Status:` line that moved is still the same
    slice's card. A `card_set` is a native card move, not an observation of the document's text,
    and does not count here.
    """
    out = {}
    for event in existing_events:
        if event.get("kind") != "card_observed" or event.get("ledger_doc") != doc:
            continue
        name = event.get("slice")
        if isinstance(name, str):
            out[name] = event.get("value")
    return out


def check_only_grown(seen, lines, doc, log_rel):
    """Section 11.7: re-read every previously imported line and match its raw text and number.

    A line that changed or moved is exit 7 (`conflict`) naming the first such line; nothing is
    written and the owner decides what happened.
    """
    for line in sorted(seen):
        raw = seen[line]
        current = lines[line - 1] if 0 < line <= len(lines) else None
        if current == raw:
            continue
        _fail(7, "conflict",
              "line %d of %s was imported as %r and now reads %r; a document whose imported lines "
              "changed or moved is not an append (section 11.7). Nothing was written."
              % (line, doc, raw, current),
              line=line, imported_raw=raw, current_raw=current, doc=doc, log=log_rel)


def high_water_line(existing_events, doc):
    """The highest line of `doc` an earlier pass imported as a RECORD, or None.

    A `card_observed` is left out in both directions: a `Status:` line sits above every record of
    its document and would make the mark useless, and a `Status:` line that appears or moves is
    not a record moving. Owner amendment A4 settles the rest: a `Status:` line is an observation
    and is outside both of section 11.7's checks.
    """
    highest = None
    for event in existing_events:
        origin = event.get("origin")
        if not isinstance(origin, dict) or origin.get("kind") != "legacy":
            continue
        if origin.get("doc") != doc or event.get("kind") == "card_observed":
            continue
        line = origin.get("line")
        if isinstance(line, int) and (highest is None or line > highest):
            highest = line
    return highest


def check_only_grew_at_the_tail(units, highest, doc, log_rel):
    """Section 11.7 and E12-4: a record that appeared ABOVE the imported tail is not an append.

    `check_only_grown` proves the lines an earlier pass read are still where they were and still
    say what they said. It cannot see a record written into the gap above them, which would land
    in the log after records that sit below it in the file, and file order is time order (E12-4).
    A new record line below the mark is therefore exit 7 (`conflict`) naming the first one;
    nothing is written and the owner decides what happened.

    `card` units are outside this rule in both directions: they neither set the mark nor are
    judged by it (owner amendment A4).
    """
    if highest is None:
        return
    for unit in units:
        if unit.kind == "card" or unit.line_no > highest:
            continue
        _fail(7, "conflict",
              "line %d of %s is a new record above line %d, the last line an earlier import read; "
              "a document that grew anywhere but at its tail is not an append (section 11.7, and "
              "E12-4: file order is time order). Nothing was written."
              % (unit.line_no, doc, highest),
              line=unit.line_no, current_raw=unit.raw, last_imported_line=highest,
              doc=doc, log=log_rel)


# ---- section 7 and section 11.4: identity and the join ----------------------------------------

class Finding(object):
    def __init__(self, finding_id, slice_name, line_no, location_key, claim_key):
        self.id = finding_id
        self.slice = slice_name
        self.line_no = line_no
        self.location_key = location_key
        self.claim_key = claim_key


def findings_from_log(events, doc):
    """The findings an earlier pass of this importer already raised for this document."""
    out = []
    for event in events:
        if event.get("kind") not in events_mod.RAISE_KINDS:
            continue
        origin = event.get("origin")
        line_no = origin.get("line") if isinstance(origin, dict) else None
        # Amendment A9 (2): the join key is the CLAIM key. A finding with no claim has an
        # empty one, so a recheck line whose claim happens to repeat that finding's scenario
        # text no longer joins to it as `exact`; section 7 still builds the ID from the
        # scenario, and that ID is read from the event, never recomputed here.
        out.append(Finding(event.get("finding"), event.get("slice"),
                           line_no if isinstance(line_no, int) else 0,
                           ids.location_key(event.get("location")),
                           ids.claim_key(event.get("claim"))))
    return out


def join_of(item, candidates, heading):
    """(finding, join_basis, candidates) for a clear line, by section 11.4's four rules, in order."""
    location = ids.location_key(item["location"])
    claim = ids.claim_key(item.get("claim"))
    same_location = [f for f in candidates if f.location_key == location]
    if claim:
        exact = [f for f in same_location if f.claim_key == claim]
        if len(exact) == 1:
            return exact[0], JOIN_EXACT, exact
    else:
        if len(same_location) == 1:
            return same_location[0], JOIN_NO_CLAIM, same_location
    if len(same_location) == 1:
        heading_names = list((heading or {}).get("slices") or [])
        if same_location[0].slice in heading_names:
            return same_location[0], JOIN_LOCATION, same_location
    return None, None, same_location


def join_reason(item, same_location):
    if not same_location:
        return ("no finding of this document holds the location %r"
                % ids.location_key(item["location"]))
    if len(same_location) > 1:
        return ("%d findings of this document hold the location %r and none matches the claim"
                % (len(same_location), ids.location_key(item["location"])))
    return ("one finding holds the location %r, its claim is worded differently, and its slice "
            "%r is not one of the heading's (%s)"
            % (ids.location_key(item["location"]), same_location[0].slice,
               ", ".join((item.get("heading") or {}).get("slices") or []) or "none"))


# ---- resolutions (section 11.5) ---------------------------------------------------------------

def answers_by_line(resolutions):
    """{line: the one answer for that line}, or exit 4 when two answers name one line.

    Review finding 5: `setdefault` kept the first of two contradictory answers and dropped the
    second without a word, while the later check counted both as used because it compares only
    line numbers. One line takes one answer.
    """
    out = {}
    for answer in (resolutions or {}).get("answers") or []:
        line = answer.get("line")
        if line in out:
            _fail(4, "invalid",
                  "the resolutions file holds more than one answer for line %r; one ambiguous "
                  "line takes one answer (section 11.5). Nothing was written." % (line,),
                  line=line, answers=[out[line], answer])
        out[line] = answer
    return out


def _answer_shape(answer):
    if "finding" in answer:
        return "finding"
    if answer.get("new_finding") is True:
        return "new_finding"
    if answer.get("skip") is True:
        return "skip"
    return None


# ---- the pass ----------------------------------------------------------------------------------

def plan_import(workspace, doc, resolutions=None, now=None, existing_events=None):
    """Read the document and work out every event this pass would append, in file order.

    Returns a plan: {"events", "ambiguities", "rejected", "counts", "doc_sha256", "lines_read",
    "units", "run_id", "at"}. It writes nothing and takes no lock; `import_legacy` is what
    appends. An ambiguity or a rejected resolution leaves `events` empty.
    """
    moment = now or utc_now()
    text, doc_sha, lines = read_document(workspace, doc)
    parsed = legacy.tolerant_document(text, doc)
    existing_events = list(existing_events or [])
    log_rel = events_mod.log_relpath(doc)
    seen = previously_imported(existing_events, doc)
    check_only_grown(seen, lines, doc, log_rel)
    blame = blame_commits(workspace, doc)
    units = [u for u in units_of(parsed, doc) if u.line_no not in seen]
    check_only_grew_at_the_tail(units, high_water_line(existing_events, doc), doc, log_rel)
    try:
        answers = answers_by_line(resolutions)
    except events_mod.RecordsError as exc:
        exc.document.setdefault("report", "import")
        exc.document.setdefault("doc", doc)
        exc.document.setdefault("log", log_rel)
        raise
    used_lines = set()
    rejected = []
    ambiguities = []
    out = []
    counts = {}
    candidates = findings_from_log(existing_events, doc)
    by_id = dict((f.id, f) for f in candidates)
    cards_seen = last_card_values(existing_events, doc)
    run_id = run_id_for(doc, moment)
    actor = {"station": STATION, "run_id": run_id, "harness": None}

    def origin_of(unit):
        heading, heading_line = unit.heading, None
        if isinstance(heading, dict):
            if unit.kind == "card":
                heading_line = heading["heading_line"] + 1  # the `## Slice X` line, 1-based
            elif "line_no" in heading:
                heading_line = heading["line_no"]
        return {"kind": "legacy", "doc": doc, "doc_sha256": doc_sha, "line": unit.line_no,
                "raw": unit.raw, "heading_line": heading_line,
                "recorded_commit": blame.get(unit.line_no),
                "commit_named": commit_named_in(unit.raw)}

    def at_of(unit):
        if unit.kind == "card":
            return moment.strftime("%Y-%m-%d")
        item = unit.item or {}
        heading = item.get("heading")
        # Section 11.7: an imported event's `at` is the block heading's date, OR THE GRANT'S DATE
        # on a waiver or reopening line. Review finding 9: the grant's own date used to lose to
        # the heading it happened to sit under, which dated a June waiver in May.
        if item.get("kind") in GRANT_ITEMS and item.get("date"):
            return item["date"]
        if isinstance(heading, dict) and heading.get("date"):
            return heading["date"]
        if item.get("date"):
            return item["date"]
        return moment.strftime("%Y-%m-%d")

    def event_of(unit, kind, **fields):
        event = {"v": 1, "kind": kind, "at": at_of(unit), "ledger_doc": doc,
                 "actor": dict(actor), "origin": origin_of(unit), "source": dict(UNKNOWN_SOURCE)}
        event.update(fields)
        counts[kind] = counts.get(kind, 0) + 1
        return event

    def note_ambiguity(unit, reason, candidate_list):
        ambiguities.append({
            "line": unit.line_no,
            "raw": unit.raw,
            "reason": reason,
            "candidates": [{"finding": f.id, "line": f.line_no, "slice": f.slice}
                           for f in candidate_list],
        })

    def raise_event(unit, item, kind, caused_by_null):
        slice_name = legacy.item_slice(item, doc)
        finding = ids.finding_id(doc, slice_name, item["location"], item.get("claim"),
                                 item.get("scenario"))
        fields = {"finding": finding, "slice": slice_name, "severity": item["severity"],
                  "location": item["location"], "claim": item.get("claim"),
                  "scenario": item.get("scenario"), "raised_by": item.get("raised_by")}
        if caused_by_null:
            fields["caused_by"] = None
        return finding, slice_name, event_of(unit, kind, **fields)

    def register(finding, slice_name, item, unit):
        record = Finding(finding, slice_name, unit.line_no, ids.location_key(item["location"]),
                         ids.claim_key(item.get("claim")))  # amendment A9 (2), as above
        candidates.append(record)
        by_id[finding] = record

    def clear_event(unit, item, finding, basis):
        kind = ITEM_KINDS[item["kind"]]
        if kind == "disposition":
            return event_of(unit, kind, finding=finding,
                            disposition="fixed" if item["disposition"] == "fixed" else "not_fixed",
                            how=item.get("how") or "", verified_source=dict(UNKNOWN_SOURCE),
                            join_basis=basis)
        if kind == "waived":
            return event_of(unit, kind, finding=finding, severity=item["severity"],
                            words=item.get("words"), grant_date=item["date"],
                            verified_source=dict(UNKNOWN_SOURCE), join_basis=basis)
        return event_of(unit, kind, finding=finding, words=item.get("words"),
                        grant_date=item["date"], join_basis=basis)

    def resolution_event(unit, answer):
        shape = _answer_shape(answer)
        if shape == "finding":
            body = {"finding": answer["finding"]}
        elif shape == "new_finding":
            body = {"new_finding": True}
        else:
            body = {"skip": True, "why": answer["why"]}
        event = {"v": 1, "kind": "resolution_applied", "at": resolutions["answered_on"],
                 "ledger_doc": doc, "actor": dict(actor), "origin": origin_of(unit),
                 "source": dict(UNKNOWN_SOURCE), "line": unit.line_no, "answer": body,
                 "answered_by": resolutions["answered_by"],
                 "answered_on": resolutions["answered_on"]}
        counts["resolution_applied"] = counts.get("resolution_applied", 0) + 1
        return event

    def reject(answer, why, reason):
        rejected.append({"line": answer.get("line"), "why": why, "reason": reason,
                         "answer": answer})

    def take_answer(unit, shapes, why=None):
        """The answer for this line, checked against section 11.5's rules; None when there is none."""
        answer = answers.get(unit.line_no)
        if answer is None:
            return None
        used_lines.add(unit.line_no)
        if answer.get("raw") != unit.raw:
            reject(answer, "raw_changed",
                   "the answer records the line as %r; it now reads %r" % (answer.get("raw"), unit.raw))
            return None
        shape = _answer_shape(answer)
        if shape not in shapes:
            reject(answer, "answer_does_not_fit",
                   "line %d asks a question that takes %s; the answer is %r%s"
                   % (unit.line_no, " or ".join(shapes), shape, (". " + why) if why else ""))
            return None
        if shape == "finding" and answer["finding"] not in by_id:
            reject(answer, "unknown_finding",
                   "the answer names finding %s; this document raises no such finding"
                   % answer["finding"])
            return None
        return answer

    for unit in units:
        if unit.kind == "card":
            value = unit.raw[len("Status:"):].strip() if unit.raw.startswith("Status:") else unit.raw
            # Amendment A4: one observation per change. The comparison is against the last value
            # observed for this SLICE, whatever line the `Status:` line sits on now; an unchanged
            # card appends nothing, so a second import of an unchanged document is still empty.
            if unit.slice_name in cards_seen and cards_seen[unit.slice_name] == value:
                continue
            card = value if value in legacy.CARD_VALUES else "none"
            out.append(event_of(unit, "card_observed", slice=unit.slice_name, value=value, card=card))
            cards_seen[unit.slice_name] = value
            continue
        item = unit.item
        if item["kind"] == "unparsed":
            out.append(event_of(unit, "legacy_unparsed", reason=item["reason"]))
            continue
        if ids.claim_is_cut(item.get("claim")):
            # Amendment A9 (1): the field separator cut a parenthesized claim in half, so this
            # line does not say where its claim ends. It is never imported with the claim cut;
            # it stops the document until a person answers for it.
            # Amendment A10: no answer supplies the missing claim, so `new_finding` is refused
            # on both shapes. A cut RAISING line can only be skipped, because a finding raised
            # from `(alpha` would carry the truncated text as its identity for good; a cut
            # CLEARING line can name a finding this document already raises, or be skipped.
            raising = item["kind"] in RAISE_ITEMS
            shapes = ("skip",) if raising else ("finding", "skip")
            answer = take_answer(unit, shapes, why=CUT_CLAIM_WHY)
            if answer is None:
                note_ambiguity(unit, CUT_CLAIM_REASON % ids.collapse(item.get("claim")), [])
                continue
            out.append(resolution_event(unit, answer))
            if _answer_shape(answer) == "skip":
                out.append(event_of(unit, "legacy_unparsed", reason=answer["why"]))
                continue
            out.append(clear_event(unit, item, answer["finding"], None))
            continue
        if item["kind"] in RAISE_ITEMS:
            slice_name = legacy.item_slice(item, doc)
            finding = ids.finding_id(doc, slice_name, item["location"], item.get("claim"),
                                     item.get("scenario"))
            if finding in by_id:
                held = by_id[finding]
                answer = take_answer(unit, ("skip",))
                if answer is not None:
                    out.append(resolution_event(unit, answer))
                    out.append(event_of(unit, "legacy_unparsed", reason=answer["why"]))
                    continue
                note_ambiguity(unit, "this line and line %d compute the same finding id %s "
                                     "(section 7: two raises in one document)" % (held.line_no, finding),
                               [held])
                continue
            _, _, event = raise_event(unit, item, ITEM_KINDS[item["kind"]],
                                      item["kind"] == "defect")
            out.append(event)
            register(finding, slice_name, item, unit)
            continue
        # a clear: a recheck, waiver, or reopening line (section 11.4)
        finding, basis, same_location = join_of(item, candidates, item.get("heading"))
        if finding is None:
            # a reopening line carries no severity (Appendix A: `REOPENED (per user) · <date> ·
            # <file:line> · <claim>`), so it cannot raise a finding of its own; the other two
            # clear shapes can
            reopening = item["kind"] == "reopening"
            answer = take_answer(
                unit, ("finding", "skip") if reopening else ("finding", "new_finding", "skip"),
                why=("A reopening line carries no severity (Appendix A), so it cannot raise a "
                     "finding of its own: name the finding it reopens, or skip it."
                     if reopening else None))
            if answer is None:
                note_ambiguity(unit, join_reason(item, same_location), same_location)
                continue
            out.append(resolution_event(unit, answer))
            shape = _answer_shape(answer)
            if shape == "skip":
                out.append(event_of(unit, "legacy_unparsed", reason=answer["why"]))
                continue
            if shape == "new_finding":
                new_id, slice_name, raised = raise_event(unit, item, "finding_raised", False)
                out.append(raised)
                register(new_id, slice_name, item, unit)
                out.append(clear_event(unit, item, new_id, None))
                continue
            out.append(clear_event(unit, item, answer["finding"], None))
            continue
        out.append(clear_event(unit, item, finding.id, basis))

    for answer in (resolutions or {}).get("answers") or []:
        if answer.get("line") not in used_lines:
            reject(answer, "line_not_asked",
                   "line %r is not a line this import stopped on" % answer.get("line"))

    # the events stay in the plan even when the pass is blocked, so `survey` can report the join
    # bases of a document that would stop; `_stop_on` is what refuses, and it runs before
    # `batch_of` in every write path.
    return {"events": out, "blocked": bool(rejected or ambiguities),
            "ambiguities": ambiguities, "rejected": rejected, "counts": counts,
            "doc_sha256": doc_sha, "lines_read": len(lines), "units": len(units),
            "run_id": run_id, "at": stamp(moment), "date": moment.strftime("%Y-%m-%d"),
            "log": log_rel, "previously_imported": len(seen), "slices": len(parsed["slices"]),
            "blocks": len(parsed["blocks"])}


def bracket_events(doc, plan, kind, **fields):
    """`import_started` / `import_finished`: this component's own events, not legacy records."""
    return {"v": 1, "kind": kind, "at": plan["at"], "ledger_doc": doc,
            "actor": {"station": STATION, "run_id": plan["run_id"], "harness": None},
            "origin": {"kind": "native"}, "source": dict(UNKNOWN_SOURCE),
            "doc_sha256": plan["doc_sha256"], **fields}


def opening_event(doc, plan, component_version, interface_version):
    return {"v": 1, "kind": "log_opened", "at": plan["at"], "ledger_doc": doc,
            "actor": {"station": STATION, "run_id": plan["run_id"], "harness": None},
            "origin": {"kind": "native"}, "source": dict(UNKNOWN_SOURCE),
            "interface_version": interface_version, "component_version": component_version}


def batch_of(doc, plan, log_exists, component_version, interface_version):
    """The whole batch one pass appends: the opening, the brackets, and the records between."""
    if not plan["events"]:
        return []
    batch = []
    if not log_exists:
        batch.append(opening_event(doc, plan, component_version, interface_version))
    # Section 6.2 gives BOTH brackets `doc_sha256`, `lines_read` and counts (review finding 7).
    batch.append(bracket_events(doc, plan, "import_started", lines_read=plan["lines_read"],
                                counts=dict(plan["counts"])))
    batch.extend(plan["events"])
    batch.append(bracket_events(doc, plan, "import_finished", lines_read=plan["lines_read"],
                                counts=dict(plan["counts"])))
    return batch


def report(doc, plan, batch, dry_run, appended=None, head=None, total=None, log_exists=False):
    body = {
        "report": "import",
        "log": plan["log"],
        "doc": doc,
        "doc_sha256": plan["doc_sha256"],
        "dry_run": bool(dry_run),
        "run_id": plan["run_id"],
        "lines_read": plan["lines_read"],
        "lines_classified": plan["units"],
        "previously_imported": plan["previously_imported"],
        "blocks": plan["blocks"],
        "slices": plan["slices"],
        "counts": dict(plan["counts"]),
        "imported": len(batch) if not dry_run else 0,
        "would_import": len(batch) if dry_run else None,
        "ambiguous": len(plan["ambiguities"]),
        "ambiguities": plan["ambiguities"],
        "rejected_resolutions": plan["rejected"],
        "spec": events_mod.spec_address(doc),
        "opened_log": (not log_exists) and bool(batch),
    }
    if appended is not None:
        body["appended"] = appended
    if head is not None:
        body["head"] = head
    if total is not None:
        body["events"] = total
    return body


def import_legacy(workspace, doc, schemas, resolutions=None, dry_run=False, now=None,
                  break_lock=False, component_version="unversioned", interface_version=1):
    """Section 11's import of one ledger document. Returns the report body; raises on a refusal.

    Under `--dry-run` nothing is written, no lock is taken, and the report says what the pass
    would append. Otherwise the lock is taken, the log is re-read under it, and the whole batch
    is appended or none of it is (section 10).
    """
    path = events_mod.log_path(workspace, doc)
    log_rel = events_mod.log_relpath(doc)
    if dry_run:
        walked = events_mod.walk(path, schemas, doc=doc)
        plan = plan_import(workspace, doc, resolutions=resolutions, now=now,
                           existing_events=walked["events"])
        _stop_on(plan, doc, log_rel, walked["head"], len(walked["events"]), dry_run=True)
        batch = batch_of(doc, plan, walked["exists"], component_version, interface_version)
        # Review finding 10: a preview that never assembled the batch could promise one the
        # writer refuses. `prepare_batch` writes nothing, so the preview stays read-only.
        if batch:
            events_mod.prepare_batch(workspace, doc, batch, walked, schemas, importer=True)
        body = report(doc, plan, batch, True, head=walked["head"],
                      total=len(walked["events"]), log_exists=walked["exists"])
        return body
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    orphans = events_mod.orphan_temporaries(path) if break_lock else None
    lock = events_mod.Lock(path, "import-legacy")
    try:
        lock.acquire(break_lock=break_lock)
    except events_mod.RecordsError as exc:
        exc.document.setdefault("log", log_rel)
        raise
    try:
        walked = events_mod.walk(path, schemas, doc=doc)
        plan = plan_import(workspace, doc, resolutions=resolutions, now=now,
                           existing_events=walked["events"])
        _stop_on(plan, doc, log_rel, walked["head"], len(walked["events"]), dry_run=False)
        batch = batch_of(doc, plan, walked["exists"], component_version, interface_version)
        if not batch:
            # Verification item 15: a pass with nothing to append still TOOK the lock, so it
            # still broke a stale one and still looked for orphan temporaries. This early
            # return used to skip both fields, which made `--break-lock` silent about a
            # recovery exactly when nothing else in the report explained it.
            body = report(doc, plan, batch, False, appended=[], head=walked["head"],
                          total=len(walked["events"]), log_exists=walked["exists"])
            return _with_recovery(body, lock, break_lock, orphans)
        prepared = events_mod.prepare_batch(workspace, doc, batch, walked, schemas, importer=True)
        events_mod.commit_batch(path, workspace, doc, walked, prepared, lock=lock, importer=True)
        head = events_mod.line_hash(prepared[-1][1])
        appended = [{"seq": event["seq"], "kind": event["kind"], "finding": event.get("finding"),
                     "history": events_mod.history_address(doc, event["seq"])}
                    for event, _ in prepared]
        body = report(doc, plan, batch, False, appended=appended, head=head,
                      total=len(walked["events"]) + len(prepared), log_exists=walked["exists"])
        return _with_recovery(body, lock, break_lock, orphans)
    finally:
        lock.release()


def _with_recovery(body, lock, break_lock, orphans):
    """What this pass recovered before it ran, on every import that took the lock.

    `broke_lock` when a stale lock was removed, and `orphan_temporaries` on every
    `--break-lock` pass, empty list included: "I looked and found none" is an answer.
    """
    if lock.broke is not None:
        body["broke_lock"] = lock.broke
    if break_lock:
        body["orphan_temporaries"] = orphans
    return body


def _stop_on(plan, doc, log_rel, head, total, dry_run):
    """Section 11.5: an ambiguity stops the document, and a rejected resolution stops it too."""
    common = {"report": "import", "log": log_rel, "doc": doc, "head": head, "events": total,
              "dry_run": bool(dry_run), "counts": dict(plan["counts"]),
              "lines_read": plan["lines_read"], "lines_classified": plan["units"],
              "spec": events_mod.spec_address(doc)}
    if plan["rejected"]:
        first = plan["rejected"][0]
        _fail(4, "invalid",
              "the resolutions file was rejected at line %r (%s): %s. Nothing was written."
              % (first["line"], first["why"], first["reason"]),
              rejected_resolutions=plan["rejected"], ambiguities=plan["ambiguities"], **common)
    if plan["ambiguities"]:
        _fail(5, "ambiguous_identity",
              "%d line(s) of %s are ambiguous; the import of this document wrote nothing. Answer "
              "each in a resolutions file (section 11.5): every field an answer needs is in the "
              "`ambiguities` list below." % (len(plan["ambiguities"]), doc),
              ambiguities=plan["ambiguities"], **common)


# ---- section 11.6: verdict docs are mirrors ---------------------------------------------------

def _block_lines(parsed, block):
    """The item lines that belong to one record block, in file order."""
    after = [b["line_no"] for b in parsed["blocks"] if b["line_no"] > block["line_no"]]
    end = min(after) if after else len(parsed["lines"]) + 1
    return [item for item in parsed["items"]
            if block["line_no"] < item["line_no"] < end and item["heading"] is block]


def _block_key(block):
    return (block["date"], block["kind"], tuple(block["slices"]))


def _blocks_with_lines(parsed):
    out = []
    counter = {}
    for block in parsed["blocks"]:
        key = _block_key(block)
        counter[key] = counter.get(key, 0) + 1
        out.append({"block": block, "key": key, "nth": counter[key],
                    "lines": [item["text"] for item in _block_lines(parsed, block)],
                    "items": _block_lines(parsed, block)})
    return out


def mirrors(workspace, doc):
    """Section 11.6: report the verdict docs the pilot's glob associates with `D`'s slices.

    Each block of a verdict doc is `same`, `differs`, or `absent` against the ledger document,
    and every record the mirror holds that the ledger document does not is `only_in_mirror`. A
    difference is reported, never repaired, never imported, and never blocks an import: a verdict
    doc holds copies of blocks (pilot contract section 9, write 5) and is never a second source.
    """
    text, _, _ = read_document(workspace, doc)
    parsed = legacy.tolerant_document(text, doc)
    ledger_blocks = _blocks_with_lines(parsed)
    ledger_keys = {}
    for entry in ledger_blocks:
        ledger_keys[(entry["key"], entry["nth"])] = entry
    ledger_records = {}
    for item in parsed["items"]:
        if item["kind"] == "unparsed" or item["location"] is None:
            continue
        ledger_records.setdefault(
            (item["kind"], ids.location_key(item["location"]), ids.claim_key(item.get("claim"))),
            []).append(item["line_no"])
    out = []
    for slice_row in parsed["slices"]:
        name = slice_row["name"]
        found = legacy.verdict_doc_glob(workspace, doc, name)
        if not found:
            out.append({"slice": name, "verdict_doc": None, "state": "absent",
                        "reason": "no verdict doc matches the glob for this slice", "blocks": []})
            continue
        for rel in found:
            out.append(_one_mirror(workspace, doc, rel, name, ledger_keys, ledger_records))
    return {"doc": doc, "slices": [s["name"] for s in parsed["slices"]], "mirrors": out,
            "counts": _mirror_counts(out), "spec": events_mod.spec_address(doc)}


def _one_mirror(workspace, doc, rel, slice_name, ledger_keys, ledger_records):
    text, sha, _ = read_document(workspace, rel)
    parsed = legacy.tolerant_document(text, rel)
    rows = []
    only = []
    for entry in _blocks_with_lines(parsed):
        twin = ledger_keys.get((entry["key"], entry["nth"]))
        if twin is None:
            state = "absent"
        elif twin["lines"] == entry["lines"]:
            state = "same"
        else:
            state = "differs"
        rows.append({"heading": entry["block"]["text"], "line": entry["block"]["line_no"],
                     "state": state, "lines": len(entry["lines"]),
                     "ledger_line": twin["block"]["line_no"] if twin else None,
                     "ledger_lines": len(twin["lines"]) if twin else 0})
    for item in parsed["items"]:
        if item["kind"] == "unparsed" or item["location"] is None:
            continue
        key = (item["kind"], ids.location_key(item["location"]), ids.claim_key(item.get("claim")))
        if key not in ledger_records:
            only.append({"line": item["line_no"], "kind": item["kind"], "raw": item["text"]})
    return {"slice": slice_name, "verdict_doc": rel, "doc_sha256": sha,
            "state": _mirror_state(rows), "blocks": rows, "only_in_mirror": only}


def _mirror_state(rows):
    if not rows:
        return "absent"
    if any(r["state"] == "differs" for r in rows):
        return "differs"
    if all(r["state"] == "same" for r in rows):
        return "same"
    return "absent" if all(r["state"] == "absent" for r in rows) else "differs"


def _mirror_counts(out):
    counts = {"same": 0, "differs": 0, "absent": 0, "only_in_mirror": 0}
    for row in out:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
        counts["only_in_mirror"] += len(row.get("only_in_mirror") or [])
    return counts


# ---- section 11.8: survey -----------------------------------------------------------------------

SKIP_DIRS = (".git", "node_modules", "__pycache__", ".venv")
REVIEWS_DIR = "docs/reviews"
REVIEWS_SEGMENT = "/docs/reviews/"


def is_mirror(rel):
    """Is this document a verdict doc, which holds copies of blocks and is never a source?

    E12-3 puts verdict docs under `docs/reviews/`. The test is on the path SEGMENT, not only on
    the workspace's own prefix, so a workspace that carries a nested tree of its own (this
    component's `fixtures/legacy/`, for one) has its verdict docs read as the mirrors they are.
    """
    return ("/" + rel.replace(os.sep, "/")).find(REVIEWS_SEGMENT) >= 0


def ledger_documents(workspace):
    """Every Markdown document in the workspace that carries an Appendix A record, sorted.

    A document under a `docs/reviews/` directory is a mirror (E12-3), never a ledger document; it
    is listed with `role: "mirror"` and never imported. `docs/records/` holds the logs and is
    skipped.
    """
    out = []
    records_dir = os.path.normpath(events_mod.RECORDS_DIR)
    for dirpath, dirnames, filenames in os.walk(workspace):
        rel_dir = os.path.relpath(dirpath, workspace).replace(os.sep, "/")
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if os.path.normpath(rel_dir) == records_dir:
            dirnames[:] = []
            continue
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            rel = os.path.normpath(os.path.join(rel_dir, name)).replace(os.sep, "/")
            out.append(rel)
    return sorted(out)


SURVEY_LIMIT = 50
"""Amendment A9 (3): how many documents `survey` returns when the caller names no limit.

Interface version 1 promises bounded output, as the house guide requires. The workspace-wide
counts still cover every document: the limit is a page of the `documents` list, never a smaller
survey.
"""


def survey(workspace, now=None, limit=SURVEY_LIMIT, offset=0):
    """Section 11.8's read-only survey: per document, the counts and the lines that would stop.

    It reads every Markdown document of the workspace, keeps the ones that carry a record, and
    reports for each the counts by record kind, the counts by join basis, and every line that
    would stop an import. It writes nothing and appends nothing.

    `limit` and `offset` page the `documents` list, in path order (amendment A9). Every document
    is still read and still counted: `counts` describes the workspace, `total` says how many
    documents there are, `returned` how many this page holds, and `truncated` whether anything
    was left out of it.
    """
    moment = now or utc_now()
    rows = []
    for rel in ledger_documents(workspace):
        try:
            text, sha, lines = read_document(workspace, rel)
        except events_mod.RecordsError:
            continue
        parsed = legacy.tolerant_document(text, rel)
        if not parsed["blocks"] and not any(i["kind"] in ("waiver", "reopening")
                                            for i in parsed["items"]):
            continue
        mirror = is_mirror(rel)
        row = {"doc": rel, "role": "mirror" if mirror else "ledger", "doc_sha256": sha,
               "lines": len(lines), "blocks": len(parsed["blocks"]),
               "slices": len(parsed["slices"]),
               "records": _kind_counts(parsed["items"])}
        if mirror:
            row["join_basis"] = {}
            row["stops"] = []
            row["ambiguous"] = None
        else:
            plan = plan_import(workspace, rel, now=moment)
            row["join_basis"] = _basis_counts(plan)
            row["stops"] = plan["ambiguities"]
            row["ambiguous"] = len(plan["ambiguities"])
            row["events"] = sum(plan["counts"].values())
            row["event_counts"] = dict(plan["counts"])
        rows.append(row)
    ledgers = [r for r in rows if r["role"] == "ledger"]
    page = rows[offset:offset + limit] if limit else []
    return {
        "report": "survey",
        "workspace": workspace,
        "documents": page,
        "total": len(rows),
        "returned": len(page),
        "offset": offset,
        "truncated": len(page) < len(rows),
        "counts": {
            "documents": len(rows),
            "ledger_documents": len(ledgers),
            "mirrors": len(rows) - len(ledgers),
            "blocks": sum(r["blocks"] for r in rows),
            "records": sum(sum(r["records"].values()) for r in rows),
            "stops": sum(len(r["stops"]) for r in ledgers),
            "documents_that_would_stop": sum(1 for r in ledgers if r["stops"]),
        },
    }


def _kind_counts(items):
    counts = {}
    for item in items:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    return counts


def _basis_counts(plan):
    counts = {JOIN_EXACT: 0, JOIN_NO_CLAIM: 0, JOIN_LOCATION: 0, "resolved": 0}
    for event in plan["events"]:
        if event.get("kind") not in ("disposition", "waived", "reopened"):
            continue
        basis = event.get("join_basis")
        counts["resolved" if basis is None else basis] += 1
    return counts
