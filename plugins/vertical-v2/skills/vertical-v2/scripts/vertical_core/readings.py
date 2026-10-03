"""Two readings of the build doc (the E15 lane contract A13; contract section 5, "Two readings").

    line_reading(doc, sections) -> the decisions the line rules take (`fences.read`'s Doc, `spec.sections`)
    second_reading(text, total) -> the decisions a CommonMark reader takes (`commonmark.py`)
    compare(first, second) -> (line, what) for the first line where the two take a decision differently, or None
    difference(text) -> compare's answer for a build doc the line rules accept (None when they refuse it: their own
        problem is named first, `spec.read`)
    notes_difference(text) -> (line, what) when the two readings decide a Markdown file's builder's-notes declaration
        differently, or None

THE TWO-READINGS RULE (stated once here and once in the contract). vertical-v2 reads the build doc twice: once by its
line rules (`fences.py`, A8 to A12: strict plain code blocks, no raw HTML lines, exact labels, plain structure, kept
as they are and applied first) and once by a pinned CommonMark reader (`commonmark.py`: `markdown-it-py` 3.0.0 with
`mdurl` 0.1.2, vendored, the `commonmark` preset). It compares decisions, never text:

1. the slices: each slice's name and heading line. The line rules take a `## ` line matching the build-doc form's
   slice heading (`templates.BUILD["slice"]`); the second reading takes every level 2 heading, ATX or Setext, wherever
   it stands, whose rendered name, written after `## `, matches that same pattern;
2. each slice's card. The line rules take the slice's one exact `Status:` label. The second reading takes every
   rendered paragraph line inside the slice's section (from its heading to the next heading of level 1 or 2, the
   reach a withheld section has) that starts with `Status:`: none is no card; one that reads exactly `Status: ` and
   one of A11's six values is that value; anything else (two lines, another value) is a card the line rules never
   take;
3. the recorded base. The line rules take the header's one exact `Base:` line. The second reading takes every
   rendered paragraph line before the first slice heading it reads that starts with `Base:`, decided as in 2 with
   7 to 40 lower-case hex digits;
4. the withheld sections: each one's name and its first and last line. The line rules take `spec.sections`. The
   second reading takes every heading of level 1 or 2 whose rendered name, lower-cased, is one of the five
   (`spec.WITHHELD`), running from its first line to the line before the next heading of level 1 or 2, or the end;
5. for each other Markdown file of the reviewed commit, its builder's-notes declaration (yes or no). The line
   reading is `notes.declaration` (the first heading read wide); the second reading is the first heading in the
   reader's token stream, its rendered name tested with `notes.DECLARES`.

A rendered name or line is the reader's inline text with character references decoded, inline markup removed and
whitespace runs collapsed (`commonmark.py`). Any difference stops the run with the named tag `doc-unreadable`,
naming the first line where the two readings take that decision differently and the decision, before any ask,
request or packet, at every reader (the gate's slices and base and its notes check, `spec.clean`, the packet
snapshot): the plan's author edits the doc. When several decisions differ, the earliest line is named (on one line,
the order above). A doc both readings take the same way runs exactly as the line rules alone run it.
"""
from station_core import templates

from . import commonmark, fences, notes

DECISIONS = {"slices": "the slices (each slice's name and heading line)",
             "card": "a slice's card (its Status: label)",
             "base": "the recorded base (the header's Base: line)",
             "withheld": "the withheld sections (each one's name, first and last line)",
             "notes": "the builder's notes declaration (the file's first heading)"}
ORDER = ("slices", "card", "base", "withheld")
SLICE = templates.BUILD["slice"]


def line_reading(doc, sections):
    """The line rules' decisions: {"slices": {heading line: name}, "cards": [{label line: (value, True)}], "base":
    {line: (commit, True)}, "withheld": {line: section}, "total": lines}."""
    cards = []
    for item in doc.slices:
        cards.append({item["status_at"]: (item["status"], True)} if item["status_at"] is not None else {})
    withheld = {}
    for what, first, last in sections:
        for number in range(first, last + 1):
            withheld[number] = what
    base = {} if doc.base is None else {doc.base["at"]: (doc.base["commit"], True)}
    return {"slices": dict((s["line"], s["name"]) for s in doc.slices), "cards": cards, "base": base,
            "withheld": withheld, "total": len(doc.lines)}


def _labels(lines, exact):
    """{line: (value, True)} for a rendered label line that is exact, {line: (its text, False)} for any other."""
    out = {}
    for number, text in lines:
        match = exact.match(text)
        out[number] = (match.group(1), True) if match else (text, False)
    return out


def second_reading(text, total):
    """The CommonMark reader's decisions, in line_reading's shape (module docstring, 1 to 4)."""
    from . import spec   # the withheld names, compared as the line reader compares them
    stream = commonmark.tokens(text)
    heads = commonmark.headings(stream)
    paragraphs = commonmark.paragraph_lines(stream)
    tops = [(level, name, line) for level, name, line in heads if level <= 2]
    slices = []
    for level, name, line in tops:
        match = SLICE.match("## " + name) if level == 2 else None
        if match:
            slices.append((line, match.group(1)))
    cards = []
    for line, name in slices:
        end = next((at for level, title, at in tops if at > line), total + 1)
        cards.append(_labels([(n, t) for n, t in paragraphs if line < n < end and t.startswith(fences.STATUS_LABEL)],
                             fences.STATUS_EXACT))
    first_slice = slices[0][0] if slices else total + 1
    base = _labels([(n, t) for n, t in paragraphs if n < first_slice and t.startswith(fences.BASE_LABEL)],
                   fences.BASE_EXACT)
    withheld = {}
    for index, (level, name, line) in enumerate(tops):
        what = spec.WITHHELD.get(name.lower())
        if what is None:
            continue
        end = tops[index + 1][2] - 1 if index + 1 < len(tops) else total
        for number in range(line, end + 1):
            withheld[number] = what
    return {"slices": dict(slices), "cards": cards, "base": base, "withheld": withheld, "total": total}


def _decided(labels):
    """One card or base decision from _labels' map: None for no label line, the value of one exact label line, else
    the label lines as read (a decision the line rules never take)."""
    if not labels:
        return None
    if len(labels) == 1:
        value, exact = list(labels.values())[0]
        if exact:
            return value
    return tuple((number, text) for number, (text, exact) in sorted(labels.items()))


def _first_line(left, right):
    lines = set(left) | set(right)
    differ = [n for n in lines if left.get(n) != right.get(n)]
    return min(differ or lines or [1])


def _say(value, nothing):
    if value is None:
        return nothing
    if isinstance(value, tuple):
        return "the label lines %s" % ", ".join("%d (%r)" % pair for pair in value)
    return repr(value)


def compare(first, second):
    """(line, what) for the earliest line where the two readings take a decision differently, or None."""
    found = []
    if first["slices"] != second["slices"]:
        line = _first_line(first["slices"], second["slices"])
        found.append((line, ORDER.index("slices"), "the line rules read %s and a CommonMark reader reads %s" % (
            _slice_at(first["slices"], line), _slice_at(second["slices"], line)), "slices"))
    else:
        names = [first["slices"][n] for n in sorted(first["slices"])]
        for name, mine, theirs in zip(names, first["cards"], second["cards"]):
            a, b = _decided(mine), _decided(theirs)
            if a != b:
                found.append((_first_line(mine, theirs), ORDER.index("card"),
                              "slice %s: the line rules take the card %s and a CommonMark reader, from the rendered "
                              "text, takes %s" % (name, _say(a, "none"), _say(b, "none")), "card"))
                break
    a, b = _decided(first["base"]), _decided(second["base"])
    if a != b:
        found.append((_first_line(first["base"], second["base"]), ORDER.index("base"),
                      "the line rules take the base %s and a CommonMark reader, from the rendered text, takes %s"
                      % (_say(a, "none (the station would fall back to its own base)"), _say(b, "none")), "base"))
    if first["withheld"] != second["withheld"]:
        line = _first_line(first["withheld"], second["withheld"])
        found.append((line, ORDER.index("withheld"), "the line rules hold this line %s and a CommonMark reader holds it %s"
                      % (_held(first["withheld"], line), _held(second["withheld"], line)), "withheld"))
    if not found:
        return None
    line, rank, words, decision = min(found)
    return line, ("the two readings differ on %s: %s; vertical-v2 runs only on a doc its line rules and a CommonMark "
                  "reader take the same way" % (DECISIONS[decision], words))


def _slice_at(slices, line):
    return "slice %s's heading there" % slices[line] if line in slices else "no slice heading there"


def _held(withheld, line):
    return "in the withheld section %s" % withheld[line] if line in withheld else "in no withheld section"


def difference(text):
    """compare's answer for a doc the line rules accept; None when they refuse it (their problem comes first)."""
    from . import spec
    doc = fences.read(text)
    if doc.problems:
        return None
    return compare(line_reading(doc, spec.sections(doc)), second_reading(text, len(doc.lines)))


def notes_difference(text):
    """(line, what) when the line reading and the CommonMark reader decide a Markdown file's builder's-notes
    declaration differently (module docstring, 5), or None."""
    mine = notes.declaration(text)
    heads = commonmark.headings(commonmark.tokens(text))
    theirs = (heads[0][1], heads[0][2]) if heads and notes.DECLARES.search(heads[0][1]) else None
    if (mine is None) == (theirs is None):
        return None
    line = theirs[1] if theirs is not None else mine[1]
    first = ("%r, at line %d" % (heads[0][1], heads[0][2])) if heads else "none"
    return line, ("the two readings differ on %s: the line reading %s, and a CommonMark reader's first heading, from "
                  "the rendered text, is %s, which %s; vertical-v2 withholds a builder's notes file only when both "
                  "readings decide it the same way" % (
                      DECISIONS["notes"],
                      ("declares the file the builder's notes by the heading %r at line %d" % mine) if mine is not None
                      else "finds no heading declaring the file the builder's notes",
                      first, "declares it" if theirs is not None else "does not declare it"))
