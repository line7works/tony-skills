"""The spec a reviewer receives (ruling E15-8 as A3 widened it and A4 amended it; the E15 lane contract A5 (2)
and A8; contract section 5): the build doc of the reviewed commit with its ledger and the builder's working
records removed.

What is fenced is decided by vertical-v2's one fence rule, strict plain code blocks (`fences.py`, A8: a fence
opens and closes at column 0, outside any list item or block quote), never by the frame's `templates.parse`
(frozen in E15, whose toggle a longer or an unclosed fence defeats, C1A3-1). Any fence line the rule does not
accept, any raw HTML line outside an accepted fence (A9, C1A5-1 and C1A5-2: a line opening, after any indent
and container markers, with `<` and a letter, `/`, `!` or `?`), any slice `Status:` line or header `Base:`
line the label rule does not take (A10, C1A6-1), and any heading or label line off the plain form (A12, C1A7-1:
indented, after a list-item or block-quote marker, or a heading whose `#`s are not followed by exactly one
space; `fences.read`) raises SpecUnreadable naming the line, so the run stops (`doc-unreadable`) before any
packet is built. A doc the line rules accept is then read a second time by a CommonMark reader, and any decision
the two readings take differently (the slices, a card, the recorded base, the withheld sections), or any of the
second reading's four refusals (A14: a rendered label line in a paragraph it cannot map to source lines, a level 1
or 2 heading off the slice form that starts with "slice", a heading that starts with `Status:` or `Base:`; A16: a
rendered character outside the character list), raises SpecUnreadable naming the first such line (A13, A14, A16;
`readings.py`, "THE TWO-READINGS RULE" and "THE SECOND READING'S FOUR REFUSALS"; `read`). A character outside the
character list anywhere outside an accepted fence is a line rule's problem (A16, `fences.py`, "THE CHARACTER LIST").
Outside fences, removed:

- the five withheld sections, `## Punch list` and `## Handoffs` (the ledger) and `## Build assumptions`,
  `## Deviations` and `## Discovered` (the builder's working records), each found by its heading level and
  name under THE WITHHELD-NAME RULE (stated once here, `withheld_of`, and once in the contract; the E15 lane
  contract A14, C1A8-3, A16 (4), A17 (2) and A18 (2)): a heading of level 1 or 2 whose name, with any closing hashes
  dropped, its format characters (Unicode category Cf) removed, folded (`fences.fold`, THE FOLD: NFKD with the
  combining marks removed, NFKC, case folding), U+00F0 then read as `d`, U+00F8 as `o`, U+00FE as `th` and U+00E6 as
  `ae` (`LETTERS`: the listed letters the fold cannot reach; their upper-case forms fold to them), every character of
  Unicode category P, S or Z read as a space (punctuation of any kind, ASCII included, symbols and spaces), its runs
  of whitespace collapsed, and every leading numbering or `the` dropped, again and again (`LEADING`: a number with an
  optional letter, `1`, `1a`; a single letter, `a`; a lower-case roman numeral read as any run of the letters i, v,
  x, l and c, `ii`, `iv`; or `the`; each followed by a space or the end of the name, so `1.`, `1.1`, `2)`, `(1)`,
  `A.`, `a)`, `(a)`, `II.`, `1:`, `1.)`, `#1` and `[1]` are dropped once their marks read as spaces; `name_key`),
  STARTS WITH one of the stems (`STEMS`) `punch`, `handoff`, `hand off`, `build assumption`, `buildassumption`,
  `builder assumption`, `builderassumption`, `builders assumption`, `builder s assumption`, `deviation` or
  `discover` is the withheld section the stem names (`## Punch list`, `## Handoffs`, `## Build assumptions`,
  `## Deviations`, `## Discovered`), so a near miss (`## Punch-list`, `## Punch list:`, `## Handoff`,
  `## Hand-offs`, `## Hand off`, `## Hand` joined by any listed or ASCII mark (an en dash, U+2212, U+00B7, U+2019,
  U+201C, U+2026, U+00D7, U+2192, `.`, `/`, `+`, `~`, `'`) `offs`, an accented `## H` U+00E0 `ndoffs` or `## P`
  U+00FC `nch list`, `## ` U+00D0 `eviations`, `## Hand` U+00D8 `ffs`, `## 1 Punch list`, `## 1. Punch list`,
  `## 1.1 Punch list`, `## (1) Punch list`, `## A. Punch list`, `## a) Punch list`, `## II. Punch list`,
  `## #1 Punch list`, `## The punch list`, `## Build-assumptions`, `## Buildassumptions`, `## Builder assumptions`,
  `## Builder's assumptions`, `## Builders assumptions`,
  a dated `## Handoff, <date>`) is withheld and named as the section it reads as. A name that only CONTAINS a stem
  is not withheld (A17 rejected a contains rule: it would withhold an ordinary heading of a real plan), so
  `## Open punch list` reaches the packets (a carried item). Each runs from its
  heading to the line before the next heading of level 1 or 2 outside a fence (or the end), every block inside it
  included (C1A2-5). The CommonMark reading applies the same rule to the rendered name (`readings.py`), and the
  two readings must agree on every withheld line, the section and the name it was read from. A wider match only
  ever withholds more. The heading test below still tolerates up to three leading spaces and spaces or tabs
  after the hashes, but since A12 every heading off the plain form has already stopped the run in
  `fences.read`, so only plain headings reach it;
- every `Status:` label (a line that starts with `Status:`, the build-doc form's label test, read after its
  format characters are removed and its leading whitespace stripped: THE HIDDEN-LABEL RULE, `fences.label_form`,
  the E15 lane contract A15, so a `Status:` line behind a zero-width space, a soft hyphen or a no-break space is
  removed too; and read as a label candidate, `fences.label_candidate`, A16 (3) and A18 (3), so `status: draft`,
  `Status : draft` and a `Status:` line after a leading curly quote, section sign or middle dot are removed too), in a
  slice's section or outside one, the header's included (M6). Since A18 (1) a `Status:` line after the first `## `
  line and outside every slice's section has already stopped the run (`fences.read`), so only the header's and the
  slices' reach this removal.

Everything else stays, byte for byte. Each removal is reported with its line numbers, so every packet's
withheld list can name it.
"""
import re
import unicodedata

from station_core import driver

from . import fences, readings

STEMS = (("punch", "## Punch list"), ("handoff", "## Handoffs"), ("hand off", "## Handoffs"),
         ("build assumption", "## Build assumptions"), ("buildassumption", "## Build assumptions"),
         ("builder assumption", "## Build assumptions"), ("builderassumption", "## Build assumptions"),
         ("builders assumption", "## Build assumptions"), ("builder s assumption", "## Build assumptions"),
         ("deviation", "## Deviations"),
         ("discover", "## Discovered"))     # A14, A16 (4), A17 (2), A18 (2): THE WITHHELD-NAME RULE's stems
LETTERS = {"\u00f0": "d", "\u00f8": "o", "\u00fe": "th", "\u00e6": "ae"}   # A18 (2): the listed letters the fold
#                                              cannot reach (no decomposition); upper case folds to them first
LEADING = re.compile(r"(?:[0-9]+[a-z]?|[a-z]|[ivxlc]+|the)(?= |\Z) *")   # A18 (2): a leading numbering
#                                              (`1`, `1.1`, `1a`, a single letter, a run of i, v, x, l and c) or `the`
LEDGER = ("## Punch list", "## Handoffs")
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$")
CLOSING = re.compile(r"(?:^|[ \t]+)#+$")
LABEL = fences.STATUS_LABEL
STOP_TAG = "doc-unreadable"


class SpecUnreadable(driver.Usage):
    """A build doc holding a line this reader cannot place (a fence line the fence rule does not accept, a raw
    HTML line, a heading or label off the plain form, a label line the label rule does not take), or a line where
    the line rules and a CommonMark reader take a decision differently (A13): the run stops before any ask,
    request or packet."""

    def __init__(self, line, what):
        driver.Usage.__init__(self, "the build doc's line %d: %s; the doc cannot be read cleanly there, so nothing "
                                    "was taken from it and no packet was built: vertical-v2 reads only plain code "
                                    "blocks whose fences open and close at the left margin, outside any list item "
                                    "or block quote, no raw HTML line, headings and labels only in their plain form "
                                    "at column 0, only exact Status: and Base: labels that end their paragraph, and "
                                    "only a doc a CommonMark reader takes the same way; the plan's author edits the "
                                    "doc and commits" % (line, what))
        self.line, self.what = line, what


class NotesUnreadable(SpecUnreadable):
    """Another Markdown file of the reviewed commit that a CommonMark reader declares the builder's notes and the
    line reading does not (A13, A14): the run stops before any ask, request or packet."""

    def __init__(self, path, line, what):
        driver.Usage.__init__(self, "the reviewed commit's file %s, line %d: %s; nothing was taken from it and no "
                                    "packet was built: the plan's author edits the file (a plain first heading) "
                                    "and commits" % (path, line, what))
        self.path, self.line, self.what = path, line, what


def heading_of(line):
    """(level, name with whitespace collapsed) for a markdown heading line, else None."""
    match = HEADING.match(line)
    if not match:
        return None
    name = CLOSING.sub("", match.group(2))
    return len(match.group(1)), " ".join(name.split())


def name_key(name):
    """A heading's name as THE WITHHELD-NAME RULE tests it (A14, A16 (4), A17 (2), A18 (2)): format characters
    removed, folded (`fences.fold`), the four letters of `LETTERS` mapped, every character of Unicode category P, S or
    Z read as a space, whitespace runs collapsed, and every leading numbering (`LEADING`) and leading `the` dropped."""
    folded = "".join(LETTERS.get(c, c) for c in fences.fold(fences.unformatted(name)))
    key = " ".join("".join(" " if unicodedata.category(c)[0] in "PSZ" else c for c in folded).split())
    while True:
        match = LEADING.match(key)
        if match is None or not match.end():
            return key
        key = key[match.end():]


def withheld_of(name):
    """THE WITHHELD-NAME RULE (module docstring): the canonical heading of the withheld section a level 1 or 2
    heading's name opens, else None. Both readings call it, the line reading with the source name and the
    CommonMark reading with the rendered one."""
    key = name_key(name)
    for stem, canonical in STEMS:
        if key.startswith(stem):
            return canonical
    return None


def withheld_name(line):
    """The canonical heading of a withheld section the line opens, else None."""
    found = heading_of(line)
    if found is None or found[0] > 2:
        return None
    return withheld_of(found[1])


def sections(doc):
    """[(canonical heading, first line, last line, the name's key)] of the withheld sections in a doc `fences.read`
    accepted: each from its heading (level 1 or 2, outside a fence, named as `withheld_name` reads it) to the line
    before the next heading of level 1 or 2 outside a fence, or the end; the key is `name_key` of the heading's
    name, which the two readings compare."""
    lines, fenced = doc.lines, doc.fenced
    top = []
    for number, raw in enumerate(lines, 1):
        if number in fenced:
            continue
        found = heading_of(fences.bare(raw, number))
        if found is not None and found[0] <= 2:
            top.append(number)
    out = []
    for index, number in enumerate(top):
        found = heading_of(fences.bare(lines[number - 1], number))
        name = withheld_of(found[1])
        if name is not None:
            out.append((name, number, top[index + 1] - 1 if index + 1 < len(top) else len(lines), name_key(found[1])))
    return out


def read(text):
    """The build doc read twice (A13): `fences.read` under the line rules (A8 to A12), whose first problem raises
    SpecUnreadable naming its line; then a CommonMark reader, whose decisions are compared with the line rules'
    (`readings.py`, "THE TWO-READINGS RULE"), the first line where they differ raising SpecUnreadable. Returns the
    Doc. Every reader of the build doc reads through here: the gate's slices and base, and `clean`.

    One exception to "the line rules first" (A18 (1)): when the first line-rule problem is a stray `Status:` line
    (`fences.STRAY`), the second reading is asked too, and a refusal or difference it names on an EARLIER line is named
    instead (a slice heading refusal (b) or the slices comparison already names, such as `## Sl` U+00EF `ce B`, keeps
    being named at its heading, A14 (2), A17 (1)); the run stops either way."""
    doc = fences.read(text)
    found = None
    if not doc.problems or doc.problems[0][1] == fences.STRAY:
        found = readings.compare(readings.line_reading(doc, sections(doc)),
                                 readings.second_reading(text, len(doc.lines)))
    if doc.problems and (found is None or found[0] >= doc.problems[0][0]):
        raise SpecUnreadable(*doc.problems[0])
    if found is not None:
        raise SpecUnreadable(*found)
    return doc


def clean(text):
    """(the spec's text, [{"what", "lines": [first, last]}]) for one build doc's text; SpecUnreadable when a
    fence is unclosed or a line cannot be placed (a fence line the rule does not accept, a raw HTML line, a
    label line the label rule does not take: `fences.read`), or when the two readings differ (A13, `read`)."""
    doc = read(text)
    lines, fenced = doc.lines, doc.fenced
    drop = set()
    removed = []
    for name, number, end, key in sections(doc):
        drop.update(range(number, end + 1))
        removed.append({"what": name, "lines": [number, end]})
    for number, raw in enumerate(lines, 1):
        if number in fenced or number in drop:
            continue
        if fences.label_candidate(fences.label_form(fences.bare(raw, number))) == LABEL:     # A15, A16 (3)
            drop.add(number)
            removed.append({"what": "Status: line", "lines": [number, number]})
    kept = "".join(line for number, line in enumerate(lines, 1) if number not in drop)
    removed.sort(key=lambda r: r["lines"][0])
    return kept, removed
