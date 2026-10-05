"""The build doc as ship-v2 reads it (CR-27; the E15 lane contract A22, A25 and A26; contract section 5).

    read(text) -> Doc, or DocUnreadable naming the first line it refuses
    slice_of(doc, name) -> the slice's row, or None
    in_footprint(path, entries) -> whether a workspace path lies inside the slice's footprint
    footprint_entries(value) -> the paths a `Footprint:` value names

What ship-v2 decides from a build doc: which slices it holds (the slice it ships must be one), that slice's card (the
`Status:` line, for the `SHIP:` block's `Card:`), and that slice's footprint (the paths a fix may touch, stop 4). Each
is read twice, and the first line where the two readings take a decision differently stops the run
`doc-unreadable`, naming the line, before any visit and before any write:

1. THE LINE RULES (A22): vertical-v2's plain-structure rules, `fences.read` (a byte-for-byte copy of vertical-v2's
   `vertical_core/fences.py`, held equal by `tests/test_doc_reading.py`: A8's strict fences, A9's raw HTML lines, A10
   and A11's exact labels, A12's plain structure, A16's character list, A18's stray `Status:` line and leading
   marks). Any problem it names stops the run (when the first is a stray `Status:` line, an earlier line the second
   reading names is named instead, as `spec.read` does, A18 (1)). The slices and their cards are its slices; each slice's section runs
   from its heading to the next plain level 1 or level 2 heading outside an accepted fence.
2. THE SECOND READING (A13, as A25 copied it into handoff-v2): vertical-v2's CommonMark reading and its comparison,
   `readings.compare(readings.line_reading(...), readings.second_reading(...))` over byte-for-byte copies of
   `commonmark.py`, `readings.py`, `spec.py` and `notes.py` and the vendored reader under `scripts/vendor/`: the
   slices (name and heading line), each slice's card, the recorded base, the withheld sections, and its four
   refusals. `templates.parse` decides nothing here.

THE FOOTPRINT RULE (A26's one rule for a label this core reads; stated once here and once in the contract, section
5). Inside a slice's section, a line that, after any prefix (indent, list-item or block-quote markers) and any leading
listed mark (`fences.marks_off`), folds (`fences.fold`) to `footprint`, spaces or tabs, then a colon, is read only in
its plain form: at column 0 with exactly `Footprint:`, its value on the same line. Any other such line stops,
named; a `Footprint:` line whose value is empty stops, named, always (build-v2's bulleted form under a bare label
puts the paths on later lines, which this reading never takes: "write the slice's paths on the label's own line");
a second `Footprint:` line in one slice stops, named. In the second reading, every rendered heading (any level) or
paragraph line from a slice's heading to its next rendered heading of level 1 or 2 whose text reads as a
`Footprint:` label candidate (format characters removed and leading whitespace stripped, `fences.label_form`; the
leading listed marks set aside; folded) must be that slice's plain `Footprint:` line in the line reading, on the same
source line: a bold `**Footprint:**`, a code-span label, a `### Footprint:` heading, a label in a paragraph whose
rendered lines cannot all be mapped to source lines (named at the paragraph's first line), or a rendered label line
running over more than one source line all stop. Unlike handoff-v2's labels, a `Footprint:` paragraph may go on
with any line: a value written on the next line is never read, so the footprint is only ever read narrower than a
person sees it, and a narrower footprint only stops more fixes (stop 4), never fewer.

THE FOOTPRINT'S PATHS. The value is split on commas outside code spans; an entry holding code spans names the code
spans' contents, any other entry names its text, trimmed (`footprint_entries`). Containment is build-v2's rule
(build-contract section 6): a path lies inside the footprint when it equals an entry, when it sits under one as a
directory, or when an entry ends in `/` and the path starts with it; only literal leading `./` segments are removed,
a filename's leading dot is part of the name, and a shared prefix of a file name is no relationship (`src/a.py` is
not inside `src/a`). A slice with no `Footprint:` line names no path, so every fix of it is outside its footprint.
"""
import re

from . import commonmark, fences, readings, spec

D = "\u2014"
STOP_TAG = "doc-unreadable"
TOP = re.compile(r"^#{1,2} ")
FOOT = re.compile(r"footprint[ \t]*:")
LABEL = "Footprint:"
WAY = "write the slice's paths on the label's own line, `Footprint: <path>, <path>`"
RULE = ("ship-v2 runs only on a doc vertical-v2's line rules and a CommonMark reader take the same way (CR-27, as "
        "the E15 lane contract A25 reads it for handoff-v2)")
PLAIN = ("ship-v2 reads a slice's footprint only in its plain form: a paragraph line that starts at column 0 with "
         "exactly `Footprint:`, its value on the same line (CR-27, the E15 lane contract A26's one rule)")


class DocUnreadable(ValueError):
    """The first line the reading refuses: `line` (1-based) and `words`."""

    def __init__(self, line, words):
        self.line, self.words = line, words
        ValueError.__init__(self, "line %d: %s" % (line, words))


class Doc(object):
    pass


def footprint_entries(value):
    """The paths a `Footprint:` value names (module docstring, THE FOOTPRINT'S PATHS)."""
    entries, current, inside = [], "", False
    for char in value:
        if char == "`":
            inside = not inside
        if char == "," and not inside:
            entries.append(current)
            current = ""
        else:
            current += char
    entries.append(current)
    out = []
    for entry in entries:
        spans = re.findall(r"`([^`]*)`", entry)
        names = [s.strip() for s in spans] if spans else [entry.strip()]
        for name in names:
            if name and name not in out:
                out.append(name)
    return out


def _normal(value):
    value = value.strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def in_footprint(path, entries):
    """build-v2's containment (build-contract section 6, its `in_named_paths`), restated (E15-6)."""
    normal = _normal(path)
    for name in entries or ():
        candidate = _normal(name)
        if not candidate:
            continue
        if candidate.endswith("/"):
            if normal.startswith(candidate):
                return True
            continue
        if normal == candidate or normal.startswith(candidate + "/"):
            return True
    return False


def _candidate(text):
    return FOOT.match(fences.fold(fences.marks_off(text))) is not None


def _tops(lines, fenced):
    return [number for number, line in enumerate(lines, 1) if number not in fenced and TOP.match(line)]


def read(text):
    found = fences.read(text)
    if found.problems:
        first = found.problems[0]
        if first[1] == fences.STRAY:        # spec.read's one exception (A18 (1)): an earlier second-reading line wins
            a13 = readings.compare(readings.line_reading(found, spec.sections(found)),
                                   readings.second_reading(text, len(found.lines)))
            if a13 is not None and a13[0] < first[0]:
                raise DocUnreadable(*a13)
        raise DocUnreadable(*first)
    lines = [fences.bare(raw, number) for number, raw in enumerate(found.lines, 1)]
    fenced = found.fenced
    tops = _tops(lines, fenced)
    slices = []
    for item in found.slices:
        end = next((t for t in tops if t > item["line"]), len(lines) + 1)
        row = dict(item, end=end, footprint=[], footprint_at=None, footprint_value=None)
        for number in range(item["line"] + 1, end):
            if number in fenced:
                continue
            line = lines[number - 1]
            at = fences.PREFIX_ONLY.match(line).end()
            if not _candidate(line[at:]):
                continue
            if at != 0 or not line.startswith(LABEL):
                raise DocUnreadable(number, "a `Footprint:` line off the plain form (indented, after a list-item or "
                                            "block-quote marker, behind a leading mark, or not spelled exactly "
                                            "`Footprint:` at column 0): %s" % PLAIN)
            value = line[len(LABEL):].strip(" \t")
            if not value:
                raise DocUnreadable(number, "a `Footprint:` line with no path on it: %s, since %s" % (WAY, PLAIN))
            if row["footprint_at"] is not None:
                raise DocUnreadable(number, "a second `Footprint:` line in slice %s (the first is line %d): a slice "
                                            "holds one" % (item["name"], row["footprint_at"]))
            row.update(footprint=footprint_entries(value), footprint_at=number, footprint_value=value)
        slices.append(row)
    differ = _second(text, found, slices)
    if differ is not None:
        raise DocUnreadable(*differ)
    doc = Doc()
    doc.lines, doc.fenced, doc.slices = lines, fenced, slices
    return doc


def _second(text, found, slices):
    """(line, words) for the first line where the second reading differs or refuses (module docstring), or None."""
    total = len(found.lines)
    theirs = readings.second_reading(text, total)
    out = []
    a13 = readings.compare(readings.line_reading(found, spec.sections(found)), theirs)
    if a13 is not None:
        out.append((a13[0], 0, a13[1]))
    stream = commonmark.tokens(text)
    heads = commonmark.headings(stream)
    ends = sorted(line for level, name, line in heads if level <= 2)
    reach = [(line, next((at for at in ends if at > line), total + 1)) for line in sorted(theirs["slices"])]

    def inside(line):
        return any(start < line < end for start, end in reach)

    mine = dict((row["footprint_at"], True) for row in slices if row["footprint_at"] is not None)
    rendered = {}
    for level, name, line in heads:
        if inside(line) and _candidate(fences.label_form(name)):
            out.append((line, 2, "a CommonMark reader renders a level %d heading %r here, which reads as a "
                                 "`Footprint:` label: a label in a heading is never read; %s" % (level, name, PLAIN)))
    for line, last, words, exact in commonmark.paragraph_spans(stream):
        if not inside(line) or not _candidate(fences.label_form(words)):
            continue
        if not exact:
            out.append((line, 2, "a CommonMark reader renders %r here, a `Footprint:` label line in a paragraph whose "
                                 "rendered lines it cannot map to source lines, so which line holds the label cannot "
                                 "be told; %s" % (words, PLAIN)))
            continue
        if last != line:
            out.append((line, 2, "a CommonMark reader renders %r here as one line running over more than one source "
                                 "line (to line %d), a `Footprint:` label whose value the line rules read only in "
                                 "part; %s" % (words, last, PLAIN)))
        rendered[line] = True
    if mine != rendered:
        line = min(n for n in set(mine) | set(rendered) if mine.get(n) != rendered.get(n))
        out.append((line, 1, "the two readings differ on the slice's footprint: the line rules read %s and a "
                             "CommonMark reader, from the rendered text, reads %s; %s; %s"
                    % ("a `Footprint:` label" if mine.get(line) else "no `Footprint:` label",
                       "a `Footprint:` label" if rendered.get(line) else "none", PLAIN, RULE)))
    if not out:
        return None
    line, rank, words = min(out)
    return line, words


def slice_of(doc, name):
    return next((row for row in doc.slices if row["name"] == name), None)
