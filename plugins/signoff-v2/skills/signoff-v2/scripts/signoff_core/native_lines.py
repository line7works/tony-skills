"""Which record lines of a document the records component itself rendered (Astra's N1).

Records keeps a ranged location on the review line it renders (E13 amendment A7, F9), and the
legacy Appendix A grammar has no range: applied to a NATIVE line, the unchanged stop check called
the component's own rendering unplaceable and stopped the next build, signoff and recheck. Her
text: identify native occurrences THROUGH THE RECORDS CLI (event kind, finding identity in slice
context, exact rendered bytes), consume each once, and apply the unchanged Appendix A stop only to
the hand-written records that remain. The log is never opened here.

What the CLI says, and what this module does with it:

1. `import-legacy --dry-run` reports `native_rendered`: how many lines of the document the
   component recognises as the rendering of a native event it holds, by kind, by the finding
   identity its own reader computes in the line's slice context, and by bytes (record lines and
   `Status:` lines both). A refusal, or a count of zero, ends the consultation: nothing is
   consumed.
2. `events` gives every event, so the station knows the native runs (a run holding any legacy
   event is an import pass and renders nothing), each native event's kind and the slice of the
   finding it names, and the last card each slice holds.
3. `render --run-id` gives, for each native run, the exact lines the component writes: its review
   blocks (one per slice), its recheck block, its grant lines.

Each document record line that is byte-equal to a rendered line, sits under a heading of the
rendered line's kind (a review line under a review heading charged to the event's slice; a recheck
block line under a recheck heading naming the finding's slice; a grant anywhere), and is not a
line an earlier import already recorded, may answer for that occurrence. Each occurrence answers
for one line and each line takes at most one, in file order (a maximum matching, iterative). The
consumption is accepted ONLY when the count agrees with the component: the lines consumed, plus
the `Status:` lines matching their slice's last native card, equal `native_rendered`. When the
two disagree (a line the component does not recognise, say a ranged defect whose first-line form
reads as another finding), nothing is consumed and the stop check reads the document whole, as it
always did: a disagreement fails closed.

The stop check itself is unchanged: the consumed lines are blanked (line numbers kept) and the
pilot's own `parse_document` and `open_set` read the rest. So a hand-written line stops exactly as
before, and a second copy of a rendered line stops too (one occurrence, one line; the importer
itself refuses the copy as a second raise, so its dry run consumes nothing).

This file is shared by the build and signoff cores byte for byte; the pilot carries the same
functions in `recheck_core/records_view.py`.
"""
from . import record_grammar as grammar
from .records_client import RecordsRefusal

REVIEW_KIND = "finding_raised"
BLOCK_KINDS = ("disposition", "defect_raised")
GRANT_KINDS = ("waived", "reopened")
RENDERED_KINDS = (REVIEW_KIND,) + BLOCK_KINDS + GRANT_KINDS
RAISE_KINDS = ("finding_raised", "defect_raised")
CARD_KINDS = ("card_set", "card_observed")


def _lines(text):
    """The record lines of rendered block text: every non-blank line that is not a heading."""
    return [line.rstrip() for line in (text or "").split("\n")
            if line.strip() and not line.startswith("### ")]


def _is_legacy(event):
    return (event.get("origin") or {}).get("kind") == "legacy"


def native_runs(rows):
    """The run ids whose events are all native and include a rendered kind, first-seen order."""
    order, legacy_runs, rendering = [], set(), set()
    for row in rows:
        event = row.get("event") or {}
        run_id = (event.get("actor") or {}).get("run_id")
        if not isinstance(run_id, str):
            continue
        if _is_legacy(event):
            legacy_runs.add(run_id)
            continue
        if run_id not in order:
            order.append(run_id)
        if event.get("kind") in RENDERED_KINDS:
            rendering.add(run_id)
    return [run_id for run_id in order if run_id not in legacy_runs and run_id in rendering]


def occurrences_of_run(rendered, run_events, raised):
    """[{text, where, slice}] for one native run, from its `render` response.

    `run_events` is [(seq, event)] of the run in seq order; `raised` maps a finding id to the
    event that raised it. `render` writes the review blocks one per slice in `review_slices` order,
    each slice's `finding_raised` events in seq order; the recheck block one line per
    `disposition` or `defect_raised` in seq order; then one line per grant. A part whose line
    count disagrees with its events yields nothing (and the count check then fails closed).
    """
    out = []
    slices = list(rendered.get("review_slices") or [])

    def slice_rank(row):
        name = row[1].get("slice") or "none"
        return (slices.index(name) if name in slices else len(slices), row[0])

    review = sorted([row for row in run_events if row[1].get("kind") == REVIEW_KIND],
                    key=slice_rank)
    lines = _lines(rendered.get("review"))
    if len(lines) == len(review):
        for (_, event), text in zip(review, lines):
            out.append({"text": text, "where": "review", "slice": event.get("slice") or "none"})
    block = [row for row in run_events if row[1].get("kind") in BLOCK_KINDS]
    lines = _lines(rendered.get("block"))
    if len(lines) == len(block):
        for (_, event), text in zip(block, lines):
            if event.get("kind") == "defect_raised":
                name = event.get("slice")
            else:
                name = (raised.get(event.get("finding")) or {}).get("slice")
            out.append({"text": text, "where": "recheck", "slice": name or "none"})
    grants = [row for row in run_events if row[1].get("kind") in GRANT_KINDS]
    lines = [line.rstrip() for line in (rendered.get("grants") or [])]
    if len(lines) == len(grants):
        for _row, text in zip(grants, lines):
            out.append({"text": text, "where": None, "slice": None})
    return out


def admits(record, occurrence):
    """Can this document record be the rendering of this occurrence, by kind and slice context?"""
    if occurrence["where"] is None:
        return True  # a grant line is standalone: its grammar names no slice and no heading
    heading = record.get("heading")
    if not heading or heading.get("kind") != occurrence["where"]:
        return False
    names = heading.get("slices") or []
    if occurrence["where"] == "review":
        return bool(names) and names[0] == occurrence["slice"]
    return occurrence["slice"] in names


def match(records, occurrences):
    """{record position: occurrence index}: a maximum matching in file order, without recursion.

    Each record takes the lowest free occurrence it admits; only when none is free does a
    breadth-first search look for an augmenting path. A record once matched stays matched, so
    which records are matched is decided in file order.
    """
    options = {}
    for position, record in enumerate(records):
        admitted = [index for index, occ in enumerate(occurrences)
                    if occ["text"] == record["text"] and admits(record, occ)]
        if admitted:
            options[position] = admitted
    owner, matched = {}, {}
    for position in sorted(options):
        free = next((index for index in options[position] if index not in owner), None)
        if free is not None:
            owner[free], matched[position] = position, free
            continue
        parent, seen, queue, head = {}, set(), [position], 0
        while head < len(queue):
            current = queue[head]
            head += 1
            found = None
            for index in options[current]:
                if index in seen:
                    continue
                seen.add(index)
                parent[index] = current
                if index not in owner:
                    found = index
                    break
                queue.append(owner[index])
            if found is not None:
                index = found
                while True:
                    line = parent[index]
                    previous = matched.get(line)
                    owner[index], matched[line] = line, index
                    if line == position:
                        break
                    index = previous
                break
    return matched


def native_card_lines(parsed, rows, document):
    """How many `Status:` lines carry their slice's last card, when a NATIVE event wrote it."""
    last = {}
    for row in rows:
        event = row.get("event") or {}
        kind = event.get("kind")
        if kind not in CARD_KINDS or event.get("ledger_doc") != document:
            continue
        name = event.get("slice")
        if not isinstance(name, str):
            continue
        value = event.get("value") if kind == "card_observed" else event.get("after")
        last[name] = (value, not _is_legacy(event))
    count = 0
    for entry in parsed.get("slices") or []:
        held = last.get(entry["name"])
        if entry.get("status") is not None and held and held[1] and held[0] == entry["status"]:
            count += 1
    return count


def consumed_lines(client, workspace, document, parsed):
    """The 1-based line numbers of `document` the component itself rendered, confirmed by its
    `native_rendered`; an empty set whenever anything is refused, missing, or disagrees."""
    try:
        preview = client.import_legacy(workspace, document, dry_run=True)
    except RecordsRefusal:
        return set()
    try:
        expected = int(preview.get("native_rendered") or 0)
    except (TypeError, ValueError):
        return set()
    if expected <= 0:
        return set()
    try:
        rows = client.events(workspace, document).get("results") or []
    except RecordsRefusal:
        return set()
    by_run, raised, imported = {}, {}, set()
    for row in rows:
        event = row.get("event") or {}
        if event.get("kind") in RAISE_KINDS:
            raised.setdefault(event.get("finding"), event)
        origin = event.get("origin") or {}
        if _is_legacy(event) and origin.get("doc") == document \
                and event.get("kind") != "card_observed" and isinstance(origin.get("line"), int):
            imported.add(origin["line"])
        run_id = (event.get("actor") or {}).get("run_id")
        by_run.setdefault(run_id, []).append((row.get("seq"), event))
    occurrences = []
    for run_id in native_runs(rows):
        try:
            rendered = client.render(workspace, document, run_id)
        except RecordsRefusal:
            return set()
        occurrences.extend(occurrences_of_run(rendered, sorted(by_run.get(run_id) or [],
                                                               key=lambda row: row[0]), raised))
    records = [record for record in parsed["records"] if record["line_no"] not in imported]
    matched = match(records, occurrences)
    if len(matched) + native_card_lines(parsed, rows, document) != expected:
        return set()
    return set(records[position]["line_no"] for position in matched)


def remaining_ambiguities(text, document, consumed):
    """Appendix A's stop check, unchanged, over the document with the consumed lines blanked.

    Returns (the original lines, the ambiguous records `open_set` finds in what remains)."""
    lines = text.split("\n")
    if not consumed:
        return lines, grammar.open_set(grammar.parse_document(text, document))["ambiguities"]
    kept = [("" if number + 1 in consumed else line) for number, line in enumerate(lines)]
    parsed = grammar.parse_document("\n".join(kept), document)
    return lines, grammar.open_set(parsed)["ambiguities"]


def hand_written_ambiguities(client, workspace, document, text):
    """The Appendix A ambiguities of the hand-written records of `document` (N1).

    The unchanged check reads the document whole first; only when it finds something does this
    ask the records CLI which lines the component rendered, and read again without those. A
    document with nothing ambiguous costs no CLI call at all."""
    lines, found = remaining_ambiguities(text, document, None)
    if not found or client is None:
        return lines, found
    consumed = consumed_lines(client, workspace, document, grammar.parse_document(text, document))
    if not consumed:
        return lines, found
    return remaining_ambiguities(text, document, consumed)
