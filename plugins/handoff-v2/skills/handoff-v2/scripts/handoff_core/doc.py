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

- the sections: every `## ` line (a plain level-2 heading); `## Handoffs` and `## Punch list` by their exact
  names, at most one of each (a second is refused, named);
- the slices: `fences.read`'s slices (the build-doc form's `## Slice <name> <dash> <short>` heading and its one
  exact `Status:` label), each section running to the next `## ` line;
- in each slice's section, this core's own two labels, read the plain way A12 reads a label: a line that, after
  any prefix (indent, list-item or block-quote markers) and any leading listed mark, folds (`fences.fold`) to
  `depends on` or `questions`, spaces or tabs, then a colon, is read only when it starts at column 0 with exactly
  `Depends on:` or `Questions:`; any other such line in a slice's section is refused, named; a second
  `Depends on:` line in one slice is refused, named;
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
end. Every other line keeps its bytes and its order; the caller holds the plan to that (`additive`).
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


def _sections(lines, fenced):
    out = []
    for number, line in enumerate(lines, 1):
        if number in fenced or not line.startswith(SECTION):
            continue
        out.append({"name": line.rstrip(" \t"), "line": number, "end": None})
    for index, section in enumerate(out):
        section["end"] = out[index + 1]["line"] if index + 1 < len(out) else len(lines) + 1
    return out


def _section_of(sections, number):
    """The index of the `## ` section holding 1-based line `number`, or -1 before the first."""
    found = -1
    for index, section in enumerate(sections):
        if section["line"] <= number:
            found = index
    return found


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
            return 0, (doc.sections[0]["line"] - 1 if doc.sections else len(doc.raw))
        section = doc.sections[index]
        return section["line"] - 1, section["end"] - 1
    if doc.punch is not None:
        section = doc.sections[doc.punch]
        return section["line"] - 1, section["end"] - 1
    return None


def additive(old, new, inserted):
    """Whether `new` is `old` with exactly the lines at `inserted` added, every other line's text and order kept (the
    lines compared without their endings, since `_closed` may end the old last line)."""
    old_lines = [fences.bare(r) for r in fences.split_lines(old)]
    kept = [fences.bare(r) for index, r in enumerate(fences.split_lines(new)) if index not in set(inserted)]
    return old_lines == kept
