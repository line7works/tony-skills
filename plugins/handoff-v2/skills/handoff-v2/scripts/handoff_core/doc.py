"""The build doc as handoff-v2 reads it and the two insertions it may make (contract sections 5 and 6).

    read(text) -> Doc, or DocUnreadable naming the first line it refuses
    identity(path, text) -> (feature, how) or (None, None)          CR-15
    plan(text, block_lines, grant_lines, eol=None) -> (new text, inserted 0-based line indexes)
    block_text(doc, block) -> the block's lines, its trailing blank lines left out

THE READING (CR-17, the E15 lane contract A22 (1)). Every line this core reads from a build doc to decide anything
goes through vertical-v2's line rules first: `fences.read` (a byte-for-byte copy of vertical-v2's
`vertical_core/fences.py`, held equal by `tests/test_line_rules.py`: A8's strict fences, A9's raw HTML lines,
A10 and A11's exact labels, A12's plain structure, A16's character list, A18's stray `Status:` line and leading
marks). Any problem it names stops the run before any write, naming the line. `templates.parse` decides nothing
here. On a doc those rules accept, this module then reads, outside accepted fences only:

- the sections: every `## ` line (a plain level-2 heading) opens one, which runs to the next plain level 1 or
  level 2 heading outside an accepted fence (the way vertical-v2's spec ends a withheld section; the slice 1b
  check's C1B1-3), so a `# Appendix` after the ledger is no part of it; `## Handoffs` and `## Punch list` by their
  exact names, at most one of each (a second is refused, named);
- the slices: `fences.read`'s slices (the build-doc form's `## Slice <name> <dash> <short>` heading and its one
  exact `Status:` label), each running to its section's end;
- in each slice's section, this core's own two labels, read the plain way A12 reads a label: a line that, after
  any prefix (indent, list-item or block-quote markers) and any leading listed mark, folds (`fences.fold`) to
  `depends on` or `questions`, spaces or tabs, then a colon, is read only when it starts at column 0 with exactly
  `Depends on:` or `Questions:`; any other such line in a slice's section is refused, named; a second
  `Depends on:` line in one slice is refused, named; a `Questions:` line whose value is empty is refused, named,
  always, and one whose value is `none` or `nothing` followed by any non-blank line in its paragraph is refused,
  named: each open question goes on its own `Questions:` line, or the label reads `Questions: none` (the E15 lane
  contract A24 (2), the slice 1b re-check's R1B1-2, which widens C1B1-4's list rule); and either label that starts
  inside an inline HTML comment its paragraph opened earlier (`<!--` with no `-->` yet), or sits in a paragraph
  holding a link reference definition, is refused, named, since CommonMark hides it there (C1B1-9);
- the handoff blocks: a line reading exactly `### <YYYY-MM-DD> <dash> handoff` (the dash `forms.D`, one constant)
  opens a block, which runs to the next level 1, 2 or 3 heading or the doc's end; a block in any section other
  than `## Handoffs` is reported (`Doc.misplaced`), never moved;
- the record blocks: a line reading `### <YYYY-MM-DD> <dash> review: ` or `recheck: ` opens one (the ledger
  home's rule, `home`).

THE TWO INSERTIONS (CR-13 (1) and (2); `plan`). The block goes at the tail of `## Handoffs`: after the section's
last non-blank line, one blank line before it and, when a non-blank line follows, one after it; a missing
`## Handoffs` is created right before `## Punch list`, or at the doc's end when the doc has neither. The rendered
grant lines go directly after the last non-blank line of the ledger home: the section holding the latest-dated
record block (a date tie: the later in the file), else `## Punch list`, else a `## Punch list` created at the doc's
end. Every other line keeps its bytes and its order; the caller holds the plan to that (`additive`). A record block
outside every named section (at the doc's top, or under a level 1 heading) is homed in the run of lines between the
plain level 1 or level 2 headings around it.

THE CARD (the E15 lane contract A23 (2); `set_statuses`). A grant that moves a slice's card rewrites that slice's
one exact `Status:` line to the new card, keeping the line's prefix, trailing spaces and ending: the one line this
core edits, in the same transaction as the `card_set` event (`write.py`).

THE TAIL RULE (A23 (1); `levelling_problem`). The records component accepts an imported record line that only
moved (its raw bytes and its order among the imported lines unchanged, matched in order by its raw text). A
planned doc keeps every imported record line, in order, and adds no line byte-equal to one, or the write is
refused before anything is written. When the component already refuses the doc, `tail_rule_way_out` says how to
settle it, naming the line where the refused imported line stands NOW (the slice 1b re-check's R1B1-5).
"""
import re
import unicodedata

from . import fences

D = "\u2014"
SECTION = "## "
HANDOFFS = "## Handoffs"
PUNCH = "## Punch list"
BLOCK = re.compile(r"^### (\d{4}-\d{2}-\d{2}) %s handoff$" % D)
RECORD = re.compile(r"^### (\d{4}-\d{2}-\d{2}) %s (review|recheck): " % D)
UPPER_HEADING = re.compile(r"^#{1,3} ")
OWN = re.compile(r"(depends[ \t]+on|questions)[ \t]*:")
TOP = re.compile(r"^#{1,2} ")
LINK_REFERENCE = re.compile(r"^ {0,3}\[[^\]]*\]:")
NO_QUESTION = ("none", "nothing")
QUESTIONS_WAY = "write each open question on its own `Questions:` line, or `Questions: none`"
TAIL_RULE = "records section 11.7 accepts only lines that moved"
OWN_EXACT = {"depends on": "Depends on:", "questions": "Questions:"}
DATED = re.compile(r"^docs/plans/\d{4}-\d{2}-\d{2}-(.+)\.md$")
FLAT = re.compile(r"^docs/([^/]+)-build-plan\.md$")
FORM_TITLE = re.compile(r"^(.+?) %s build plan \(.+\)$" % D)
STOP_TAG = "doc-unreadable"
OFF_OWN = ("a `%s` line off the plain form (indented, after a list-item or block-quote marker, or not spelled "
           "exactly `%s` at column 0): handoff-v2 reads its own labels only in their plain form, as vertical-v2's "
           "plain-structure rule reads `Status:` (the E15 lane contract A12, A22)")


class DocUnreadable(ValueError):
    """The first line the reading refuses: `line` (1-based) and `words`."""

    def __init__(self, line, words):
        self.line, self.words = line, words
        ValueError.__init__(self, "line %d: %s" % (line, words))


class Doc(object):
    pass


def _blank(line):
    return not line.strip(" \t")


def _tops(lines, fenced):
    """The 1-based numbers of every plain level 1 or level 2 heading outside an accepted fence."""
    return [number for number, line in enumerate(lines, 1) if number not in fenced and TOP.match(line)]


def _sections(lines, fenced):
    """Every `## ` section, each running to the next plain level 1 or level 2 heading outside an accepted fence, or
    the doc's end (C1B1-3)."""
    tops = _tops(lines, fenced)
    out = []
    for index, number in enumerate(tops):
        if lines[number - 1].startswith(SECTION):
            end = tops[index + 1] if index + 1 < len(tops) else len(lines) + 1
            out.append({"name": lines[number - 1].rstrip(" \t"), "line": number, "end": end})
    return out


def _section_of(sections, number):
    """The index of the `## ` section holding 1-based line `number`, or -1 when no section holds it (before the
    first, or under a level 1 heading after a section's end)."""
    for index, section in enumerate(sections):
        if section["line"] <= number < section["end"]:
            return index
    return -1


def _paragraph(lines, fenced, number, first, last):
    """(start, end) 1-based inclusive of the paragraph holding line `number` within [first, last]: the run of
    non-blank lines outside accepted fences around it, a heading ending it."""
    def inside(n):
        if n < first or n > last or n in fenced:
            return False
        line = lines[n - 1]
        return not _blank(line) and not fences.ATX_HEADING.match(line)
    start = end = number
    while inside(start - 1):
        start -= 1
    while inside(end + 1):
        end += 1
    return start, end


def _comment_open_at(lines, start, number):
    """The 1-based line where an inline HTML comment still open at the start of line `number` opened, scanning the
    paragraph's lines from `start` (a `<!--` with no `-->` after it before that line), or None."""
    inside = None
    for other in range(start, number):
        line, at = lines[other - 1], 0
        while True:
            if inside is None:
                found = line.find("<!--", at)
                if found < 0:
                    break
                inside, at = other, found + 4
            else:
                found = line.find("-->", at)
                if found < 0:
                    break
                inside, at = None, found + 3
    return inside


def _own_label_problem(lines, fenced, number, exact, value, first, last):
    """C1B1-9 and A24 (2) for one of this core's labels at line `number` of a slice section [first, last]. C1B1-9 is
    read as the check meant it, hiding: the label starts inside an inline HTML comment its paragraph opened earlier
    (a `<!--` not yet closed by `-->`), or its paragraph holds a link reference definition. A comment opened and
    closed before the label hides nothing, and stops nothing (one of the 25 real plans holds one beside a label).

    A24 (2), the slice 1b re-check's R1B1-2: a `Questions:` line whose value is empty is refused always (its question
    may stand on the next line, which CommonMark renders as the label's own text, or anywhere after it); one whose
    value is `none` or `nothing` is refused when any non-blank line follows it in its paragraph, which CommonMark
    renders as part of the label's value. This widens C1B1-4's list rule to every line."""
    start, end = _paragraph(lines, fenced, number, first, last)
    opened = _comment_open_at(lines, start, number)
    linked = [other for other in range(start, end + 1) if LINK_REFERENCE.match(lines[other - 1])]
    for other, hiding in ([(opened, "`<!--` (an inline HTML comment still open at the label)")] if opened else []) + \
            [(n, "a link reference definition") for n in linked[:1]]:
        if hiding is not None:
            return ("a `%s` line in a paragraph that also holds %s (line %d): CommonMark may hide the label inside "
                    "an inline HTML comment or a link reference definition's title, so handoff-v2 does not read it; "
                    "put the label in a paragraph of its own (the slice 1b check's C1B1-9)" % (exact, hiding, other))
    if exact != OWN_EXACT["questions"]:
        return None
    if not value:
        return ("a `Questions:` line with no question on it (%r): %s, since handoff-v2 reads one question per line "
                "and an empty label tells it nothing (the E15 lane contract A24 (2))" % (lines[number - 1], QUESTIONS_WAY))
    if value.casefold() in NO_QUESTION and end > number:
        return ("a `Questions: %s` line followed by line %d in its paragraph, which CommonMark reads as part of the "
                "label's value: %s with nothing after it in its paragraph (the E15 lane contract A24 (2))"
                % (value, number + 1, QUESTIONS_WAY))
    return None


def read(text):
    lines_raw = fences.split_lines(text)
    found = fences.read(text)
    if found.problems:
        number, words = found.problems[0]
        raise DocUnreadable(number, words)
    lines = [fences.bare(raw, number) for number, raw in enumerate(lines_raw, 1)]
    fenced = found.fenced
    sections = _sections(lines, fenced)
    doc = Doc()
    doc.raw, doc.lines, doc.fenced, doc.sections = lines_raw, lines, fenced, sections
    doc.tops = _tops(lines, fenced)
    doc.handoffs = doc.punch = None
    for index, section in enumerate(sections):
        for name, attr in ((HANDOFFS, "handoffs"), (PUNCH, "punch")):
            if section["name"] == name:
                if getattr(doc, attr) is not None:
                    raise DocUnreadable(section["line"], "a second `%s` section (the first is line %d): the build doc "
                                                         "holds one, so handoff-v2 cannot tell where its writes land"
                                        % (name, sections[getattr(doc, attr)]["line"]))
                setattr(doc, attr, index)
    slices = []
    for item in found.slices:
        index = _section_of(sections, item["line"])
        row = dict(item, end=sections[index]["end"], depends=None, depends_at=None, questions=[])
        last = row["end"] - 1
        for number in range(item["line"] + 1, row["end"]):
            if number in fenced:
                continue
            line = lines[number - 1]
            at = fences.PREFIX_ONLY.match(line).end()
            match = OWN.match(fences.fold(fences.marks_off(line[at:])))
            if match is None:
                continue
            key = " ".join(match.group(1).split())
            exact = OWN_EXACT[key]
            if at != 0 or not line.startswith(exact):
                raise DocUnreadable(number, OFF_OWN % (exact, exact))
            value = line[len(exact):].strip(" \t")
            problem = _own_label_problem(lines, fenced, number, exact, value, item["line"] + 1, last)
            if problem is not None:
                raise DocUnreadable(number, problem)
            if key == "depends on":
                if row["depends_at"] is not None:
                    raise DocUnreadable(number, "a second `Depends on:` line in slice %s (the first is line %d)"
                                        % (item["name"], row["depends_at"]))
                row["depends"], row["depends_at"] = value, number
            else:
                row["questions"].append({"line": number, "text": value})
        slices.append(row)
    doc.slices = slices
    blocks, records = [], []
    for number, line in enumerate(lines, 1):
        if number in fenced:
            continue
        block = BLOCK.match(line)
        record = RECORD.match(line)
        if block or record:
            end = len(lines) + 1
            for later in range(number + 1, len(lines) + 1):
                if later not in fenced and UPPER_HEADING.match(lines[later - 1]):
                    end = later
                    break
            row = {"date": (block or record).group(1), "line": number, "end": end,
                   "section": _section_of(sections, number)}
            if block:
                blocks.append(row)
            else:
                records.append(dict(row, kind=record.group(2)))
    doc.blocks, doc.records = blocks, records
    doc.misplaced = [b for b in blocks if doc.handoffs is None or b["section"] != doc.handoffs]
    doc.title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else None
    return doc


def block_text(doc, block):
    """The block's raw lines, from its heading to the line before its end, trailing blank lines left out."""
    rows = list(doc.raw[block["line"] - 1:block["end"] - 1])
    while rows and _blank(fences.bare(rows[-1])):
        rows.pop()
    return "".join(rows)


def slug(text):
    folded = fences.fold(text)
    ascii_only = "".join(c for c in unicodedata.normalize("NFKD", folded) if ord(c) < 128)
    return re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")


def identity(path, text):
    """CR-15, one way per doc: the `<topic>` of `docs/plans/<YYYY-MM-DD>-<topic>.md`, else the `<feature>` of
    `docs/<feature>-build-plan.md`, else a slug of the doc's own title (its first line, a plain `# ` heading; the
    build-doc form's ` <dash> build plan (<date>)` tail set aside), else (None, None)."""
    rel = path.replace("\\", "/")
    match = DATED.match(rel)
    if match and match.group(1):
        return match.group(1), "dated-plan"
    match = FLAT.match(rel)
    if match and match.group(1):
        return match.group(1), "flat-plan"
    lines = fences.split_lines(text)
    first = fences.bare(lines[0], 1) if lines else ""
    if first.startswith("# ") and first[2:].strip():
        title = first[2:].strip()
        form = FORM_TITLE.match(title)
        name = slug(form.group(1) if form else title)
        if name:
            return name, "title"
    return None, None


# ---- the two insertions -----------------------------------------------------------------------------

def _eol(raw):
    for line in raw:
        for ending in ("\r\n", "\n", "\r"):
            if line.endswith(ending):
                return ending
    return "\n"


def _tail(raw, start, end):
    """The 0-based index right after the last non-blank line of [start, end), never before start + 1."""
    k = end
    while k - 1 > start and _blank(fences.bare(raw[k - 1])):
        k -= 1
    return k


def _closed(raw, eol):
    """The raw lines, the last one given a line ending when it has none (the one byte change an insertion after it
    needs); the caller's additivity check reads the lines without their endings."""
    out = list(raw)
    if out and not out[-1].endswith(("\n", "\r")):
        out[-1] = out[-1] + eol
    return out


def _insert(raw, at, rows, inserted):
    for index in range(len(inserted)):
        if inserted[index] >= at:
            inserted[index] += len(rows)
    raw[at:at] = rows
    inserted.extend(range(at, at + len(rows)))


def plan(text, block_lines, grant_lines, eol=None):
    """(the new text, the 0-based indexes of every inserted line in it). `block_lines` is the block's lines with no
    ending, its heading first; `grant_lines` the rendered grant lines with no ending (possibly none)."""
    doc = read(text)
    eol = eol or _eol(doc.raw)
    raw = _closed(doc.raw, eol)
    inserted = []
    block_rows = [line + eol for line in block_lines]
    if doc.handoffs is not None:
        section = doc.sections[doc.handoffs]
        at = _tail(raw, section["line"] - 1, section["end"] - 1)
        rows = [eol] + block_rows
        if at < len(raw) and not _blank(fences.bare(raw[at])):
            rows.append(eol)
        _insert(raw, at, rows, inserted)
    elif doc.punch is not None:
        at = doc.sections[doc.punch]["line"] - 1
        _insert(raw, at, [HANDOFFS + eol, eol] + block_rows + [eol], inserted)
    else:
        rows = ([eol] if raw and not _blank(fences.bare(raw[-1])) else []) + [HANDOFFS + eol, eol] + block_rows
        _insert(raw, len(raw), rows, inserted)
    if grant_lines:
        middle = "".join(raw)
        again = read(middle)
        grant_rows = [line + eol for line in grant_lines]
        place = home(again)
        if place is None:
            rows = ([eol] if raw and not _blank(fences.bare(raw[-1])) else []) + [PUNCH + eol] + grant_rows
            _insert(raw, len(raw), rows, inserted)
        else:
            start, end = place
            _insert(raw, _tail(raw, start, end), grant_rows, inserted)
    return "".join(raw), sorted(inserted)


def home(doc):
    """(start, end) 0-based of the ledger home's lines, or None when the doc has no record block and no
    `## Punch list`: the section holding the latest-dated record block (a date tie: the later in the file; the doc's
    top, before any `## ` line, when that is where it sits), else the `## Punch list` section."""
    if doc.records:
        latest = max(doc.records, key=lambda r: (r["date"], r["line"]))
        index = latest["section"]
        if index < 0:
            return _region(doc, latest["line"])
        section = doc.sections[index]
        return section["line"] - 1, section["end"] - 1
    if doc.punch is not None:
        section = doc.sections[doc.punch]
        return section["line"] - 1, section["end"] - 1
    return None


def _region(doc, number):
    """(start, end) 0-based of the run of lines holding 1-based line `number` between the plain level 1 or level 2
    headings around it (the doc's top or end where there is none)."""
    before = [top for top in doc.tops if top <= number]
    after = [top for top in doc.tops if top > number]
    return (before[-1] - 1 if before else 0), (after[0] - 1 if after else len(doc.raw))


def set_statuses(text, changes):
    """The text with each slice's one exact `Status:` line set to its new card, every other byte kept: `changes` is
    [(1-based line, the card the line reads, the new card)]. A line that does not read exactly `Status: <the card>`
    raises ValueError (A23 (2): the card moves only from the card the line and the records agree on)."""
    raw = fences.split_lines(text)
    for number, before, after in changes:
        if not 0 < number <= len(raw):
            raise ValueError("line %d is not a line of the doc" % number)
        line = raw[number - 1]
        bare = fences.bare(line, number)
        match = fences.STATUS_EXACT.match(bare)
        if match is None or match.group(1) != before:
            raise ValueError("line %d reads %r, not `Status: %s`" % (number, bare, before))
        ending = line[len(line.rstrip("\r\n")):]
        raw[number - 1] = "Status: %s%s%s" % (after, bare[match.end(1):], ending)
    return "".join(raw)


def levelling_problem(text, inserted, imported):
    """Why the planned `text` would leave a doc the records component's widened section 11.7 refuses, or None (A23
    (1)). `imported` is [(line, raw)] of every record line the log imported from the doc; `inserted` the 0-based
    indexes of the lines the plan adds. The importer matches the imported lines in order by their raw text, so the
    plan adds no line byte-equal to one (it would take that line's place), and every one still stands in the doc,
    in its order."""
    raws = set(raw.rstrip("\r") for _, raw in imported)
    lines = fences.split_lines(text)
    for index in sorted(inserted):
        if index < len(lines) and fences.bare(lines[index]) in raws:
            return ("the write would add line %d, byte-equal to a record line the log imported, and the importer "
                    "matches imported lines by their bytes, in order (records section 11.7)" % (index + 1))
    rows, at = text.split("\n"), 0
    for line, raw in sorted(imported):
        while at < len(rows) and rows[at] != raw:
            at += 1
        if at == len(rows):
            return ("the record line the log imported from line %d (%r) would not stand in the doc in its order "
                    "(records section 11.7)" % (line, raw))
        at += 1
    return None


def _heading_shift(text, old, headings):
    """How far the record block heading of imported line `old` has moved, or None: the record block headings the
    imported lines were read under (`headings`, {imported line: its heading's line then}) are matched in order with
    the doc's record block headings now (new record blocks only ever arrive at the tail, section 11.7)."""
    then = sorted(set(h for h in (headings or {}).values() if isinstance(h, int)))
    mine = (headings or {}).get(old)
    if not isinstance(mine, int) or mine not in then:
        return None
    try:
        now = [r["line"] for r in read(text).records]
    except DocUnreadable:
        return None
    if len(now) < len(then):
        return None
    return now[then.index(mine)] - mine


def tail_rule_way_out(text, imported, body, headings=None):
    """How the owner settles a doc the records component's widened section 11.7 refuses (the slice 1b re-check's
    R1B1-5): `imported` is [(line, raw)] of every record line the log imported from the doc, `headings` {line: the
    line of the record block heading it was read under then}, `body` the refusal's fields. An imported line that
    changed, was dropped or was reordered is named at the line where it stands NOW (the component names the number
    it had when imported): its number then, shifted by as far as its record block heading has moved, or, without one,
    by as far as its nearest imported neighbour that still reads its imported text has moved. A new record above the
    imported tail is named where it stands. The words end with the rule."""
    lines = [fences.bare(raw, number) for number, raw in enumerate(fences.split_lines(text), 1)]
    raw_of = body.get("imported_raw") if isinstance(body, dict) else None
    old = body.get("line") if isinstance(body, dict) else None
    if isinstance(raw_of, str) and isinstance(old, int):
        shift = _heading_shift(text, old, headings)
        if shift is not None:
            return "put line %d back to its imported text %r; %s" % (old + shift, raw_of, TAIL_RULE)
        where, at = {}, 0
        for line, raw in sorted(imported):
            k = at
            while k < len(lines) and lines[k] != raw:
                k += 1
            if k < len(lines):
                where[line] = k + 1
                at = k + 1
        before = [line for line in sorted(where) if line < old]
        after = [line for line in sorted(where) if line > old]
        neighbour = before[-1] if before else (after[0] if after else None)
        now = old + (where[neighbour] - neighbour if neighbour is not None else 0)
        return "put line %d back to its imported text %r; %s" % (now, raw_of, TAIL_RULE)
    if isinstance(old, int) and isinstance(body.get("last_imported_line"), int):
        return ("move the record on line %d below the last imported record line (line %d now), or take it out; %s"
                % (old, body["last_imported_line"], TAIL_RULE))
    return "settle the doc against the records log; %s" % TAIL_RULE


def additive(old, new, inserted):
    """Whether `new` is `old` with exactly the lines at `inserted` added, every other line's text and order kept (the
    lines compared without their endings, since `_closed` may end the old last line)."""
    old_lines = [fences.bare(r) for r in fences.split_lines(old)]
    kept = [fences.bare(r) for index, r in enumerate(fences.split_lines(new)) if index not in set(inserted)]
    return old_lines == kept
