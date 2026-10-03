"""Two readings of the build doc (the E15 lane contract A13 and A14; contract section 5, "Two readings").

    line_reading(doc, sections) -> the decisions the line rules take (`fences.read`'s Doc, `spec.sections`)
    second_reading(text, total) -> the decisions a CommonMark reader takes (`commonmark.py`), and its refusals
    compare(first, second) -> (line, what) for the first line where the two take a decision differently or the
        second reading refuses, or None
    difference(text) -> compare's answer for a build doc the line rules accept (None when they refuse it: their own
        problem is named first, `spec.read`)
    notes_difference(text) -> (line, what) when a CommonMark reader declares a Markdown file the builder's notes and
        the line reading does not, or None
    slice_form(level, name), label_heading(name) -> True when a rendered heading meets refusal (b) or (c) below

THE TWO-READINGS RULE (stated once here and once in the contract). vertical-v2 reads the build doc twice: once by its
line rules (`fences.py`, A8 to A12: strict plain code blocks, no raw HTML lines, exact labels, plain structure, kept
as they are and applied first) and once by a pinned CommonMark reader (`commonmark.py`: `markdown-it-py` 3.0.0 with
`mdurl` 0.1.2, vendored, the `commonmark` preset). It compares decisions, never text:

1. the slices: each slice's name and heading line. The line rules take a `## ` line matching the build-doc form's
   slice heading (`templates.BUILD["slice"]`); the second reading takes every level 2 heading, ATX or Setext, wherever
   it stands, whose rendered name, written after `## `, matches that same pattern;
2. each slice's card. The line rules take the slice's one exact `Status:` label. The second reading takes every
   rendered paragraph line inside the slice's section (from its heading to the next heading of level 1 or 2, the
   reach a withheld section has) that starts with `Status:` once its format characters are removed and its leading
   whitespace stripped (THE HIDDEN-LABEL RULE, `fences.label_form`, A15: a label behind a zero-width space, a soft
   hyphen or a no-break space is a label candidate too), and keeps every one of them, a list in document order,
   never one entry per source line (A14, C1A8-1: two rendered lines can carry one line number): none is no card; one
   that reads exactly `Status: ` and one of A11's six values is that value; anything else (two lines, another
   value) is a card the line rules never take;
3. the recorded base. The line rules take the header's one exact `Base:` line. The second reading takes every
   rendered paragraph line before the first slice heading it reads that starts with `Base:` (read as in 2, A15), kept
   and decided as in 2 with 7 to 40 lower-case hex digits;
4. the withheld sections: for each withheld line, the section it belongs to and the name its heading was read from.
   Both readings apply one rule, THE WITHHELD-NAME RULE (`spec.withheld_of`, A14, C1A8-3: a level 1 or 2 heading
   whose name, format characters removed, whitespace collapsed and lower-cased, starts with `punch`, `handoff`,
   `hand-off`, `build assumption`, `deviation` or `discover`): the line rules to the source name (`spec.sections`),
   the second reading to the rendered name, each section running from its heading to the line before the next
   heading of level 1 or 2, or the end;
5. for each other Markdown file of the reviewed commit, its builder's-notes declaration. The line reading is
   `notes.declaration` (the first heading read wide); the second reading is the first heading in the reader's token
   stream, its rendered name tested with `notes.DECLARES`. Only one direction stops (A14, C1A8-4): the second
   reading declares the file and the line reading does not, so the file would reach the packets; a file the wide
   line reading declares and the second reading does not is withheld, as before A13.

A rendered name or line is the reader's inline text with character references decoded, inline markup removed and
whitespace runs collapsed (`commonmark.py`). Any difference stops the run with the named tag `doc-unreadable`,
naming the first line where the two readings take that decision differently and the decision, before any ask,
request or packet, at every reader (the gate's slices and base and its notes check, `spec.clean`, the packet
snapshot): the plan's author edits the doc. When several decisions differ, the earliest line is named (on one line,
the refusals below first, then the order above). A doc both readings take the same way, and the second reading does
not refuse, runs exactly as the line rules alone run it.

THE SECOND READING'S THREE REFUSALS (A14; stated once here and once in the contract). A doc the line rules accept
also stops `doc-unreadable`, naming the line, when the second reading finds:

(a) a rendered paragraph line that starts with `Status:` or `Base:` (read as in 2, A15) in a paragraph whose rendered lines cannot all
    be mapped to source lines (a code span, a link destination or a link title running over a line ending:
    `commonmark.paragraph_lines` marks it not exact), naming the paragraph's first line (C1A8-1), anywhere in the
    doc and whatever the label says, one exact label included: which source line holds which label cannot be told
    there;
(b) a heading of level 1 or 2 whose rendered name, with format characters (Unicode category Cf) removed, starts with
    `slice` in any letter case and is not a level 2 heading whose rendered name matches the build-doc form's slice
    pattern (C1A8-2: an en dash, a hyphen or a colon for the form's dash, no spaces around it, a lower-case `slice`, a
    zero-width character, a level 1 heading): no reading would take it as a slice, so its slice would vanish from
    the sign-off check. A heading of level 3 or more (a `### Slice D <dot> <date>` note) is not touched;
(c) a heading of any level whose rendered name, with format characters removed, starts with `Status:` or `Base:`
    (C1A8-3): no reading takes a heading as a label, so its words would stand beside the slice's card or the base,
    unread.

Each refusal reads the rendered heading or line, which for a plain line is its source text, so one rule covers the
source form and every rendering of it.
"""
from station_core import templates

from . import commonmark, fences, notes

DECISIONS = {"slices": "the slices (each slice's name and heading line)",
             "card": "a slice's card (its Status: label)",
             "base": "the recorded base (the header's Base: line)",
             "withheld": "the withheld sections (each one's name, first and last line)",
             "notes": "the builder's notes declaration (the file's first heading)"}
ORDER = ("unmapped", "slice-form", "label-heading", "slices", "card", "base", "withheld")
SLICE = templates.BUILD["slice"]
D = templates.D
LABELS = (fences.STATUS_LABEL, fences.BASE_LABEL)


def line_reading(doc, sections):
    """The line rules' decisions: {"slices": {heading line: name}, "cards": [[(label line, value, True)]], "base":
    [(line, commit, True)], "withheld": {line: (section, name key)}, "refused": [], "total": lines}."""
    cards = []
    for item in doc.slices:
        cards.append([(item["status_at"], item["status"], True)] if item["status_at"] is not None else [])
    withheld = {}
    for what, first, last, key in sections:
        for number in range(first, last + 1):
            withheld[number] = (what, key)
    base = [] if doc.base is None else [(doc.base["at"], doc.base["commit"], True)]
    return {"slices": dict((s["line"], s["name"]) for s in doc.slices), "cards": cards, "base": base,
            "withheld": withheld, "refused": [], "total": len(doc.lines)}


def _labels(lines, exact):
    """[(line, value, True)] for a rendered label line that is exact, [(line, its text, False)] for any other: every
    line kept, in document order (A14, C1A8-1)."""
    out = []
    for number, text in lines:
        match = exact.match(text)
        out.append((number, match.group(1), True) if match else (number, text, False))
    return out


def slice_form(level, name):
    """Refusal (b): a level 1 or 2 heading whose rendered name, format characters removed, starts with `slice` in
    any case and is not a level 2 heading on the build-doc form's slice pattern."""
    if level > 2 or not fences.unformatted(name).lower().startswith("slice"):
        return False
    return not (level == 2 and SLICE.match("## " + name))


def label_heading(name):
    """Refusal (c): a heading whose rendered name, format characters removed, starts with `Status:` or `Base:`."""
    return fences.unformatted(name).startswith(LABELS)


def second_reading(text, total):
    """The CommonMark reader's decisions, in line_reading's shape (module docstring, 1 to 4), and its refusals
    (module docstring, (a) to (c)) as [(line, kind, rendered text, level)] in document order."""
    from . import spec   # the withheld-name rule, applied as the line reading applies it
    stream = commonmark.tokens(text)
    heads = commonmark.headings(stream)
    paragraphs = commonmark.paragraph_lines(stream)
    refused = []
    for level, name, line in heads:
        if label_heading(name):
            refused.append((line, "label-heading", name, level))
        elif slice_form(level, name):
            refused.append((line, "slice-form", name, level))
    paragraphs = [(line, fences.label_form(rendered), exact) for line, rendered, exact in paragraphs]   # A15
    for line, rendered, exact in paragraphs:
        if not exact and rendered.startswith(LABELS):
            refused.append((line, "unmapped", rendered, None))
    refused.sort(key=lambda item: (item[0], ORDER.index(item[1])))
    tops = [(level, name, line) for level, name, line in heads if level <= 2]
    slices = []
    for level, name, line in tops:
        match = SLICE.match("## " + name) if level == 2 else None
        if match:
            slices.append((line, match.group(1)))
    cards = []
    for line, name in slices:
        end = next((at for level, title, at in tops if at > line), total + 1)
        cards.append(_labels([(n, t) for n, t, exact in paragraphs if line < n < end and t.startswith(fences.STATUS_LABEL)],
                             fences.STATUS_EXACT))
    first_slice = slices[0][0] if slices else total + 1
    base = _labels([(n, t) for n, t, exact in paragraphs if n < first_slice and t.startswith(fences.BASE_LABEL)],
                   fences.BASE_EXACT)
    withheld = {}
    for index, (level, name, line) in enumerate(tops):
        what = spec.withheld_of(name)
        if what is None:
            continue
        end = tops[index + 1][2] - 1 if index + 1 < len(tops) else total
        for number in range(line, end + 1):
            withheld[number] = (what, spec.name_key(name))
    return {"slices": dict(slices), "cards": cards, "base": base, "withheld": withheld, "refused": refused,
            "total": total}


def _decided(labels):
    """One card or base decision from a list of label lines: None for none, the value of one exact label line, else
    the label lines as read (a decision the line rules never take)."""
    if not labels:
        return None
    if len(labels) == 1 and labels[0][2]:
        return labels[0][1]
    return tuple((number, text) for number, text, exact in labels)


def _by_line(labels):
    """{line: [(value or text, exact)]} from a list of label lines, every one kept."""
    out = {}
    for number, text, exact in labels:
        out.setdefault(number, []).append((text, exact))
    return out


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


def _refusal(kind, rendered, level):
    if kind == "unmapped":
        return ("a CommonMark reader renders %r here, a label line in a paragraph whose rendered lines it cannot map to "
                "source lines (a code span, a link destination or a link title runs over a line ending), so which "
                "line holds which label cannot be told; vertical-v2 reads a Status: or Base: label only in a paragraph "
                "whose every rendered line maps to its own source line" % rendered)
    if kind == "slice-form":
        return ("a level %d heading a CommonMark reader renders as %r reads like a slice heading (it starts with "
                "\"slice\") but is off the build-doc form's slice heading \"## Slice <name> %s <short name>\", so no "
                "reading takes it as a slice and its slice would vanish from the sign-off check; vertical-v2 reads a "
                "level 1 or 2 heading that starts with \"slice\" only on that form" % (level, rendered, D))
    return ("a heading a CommonMark reader renders as %r starts like a Status: or Base: label, and no reading takes a "
            "heading as a label, so its words would stand beside the slice's card or the base unread; vertical-v2 "
            "reads a label only as a plain paragraph line" % rendered)


def compare(first, second):
    """(line, what) for the earliest line where the second reading refuses the doc or the two readings take a
    decision differently, or None."""
    found = []
    for line, kind, rendered, level in second.get("refused") or []:
        found.append((line, ORDER.index(kind), _refusal(kind, rendered, level)))
    if first["slices"] != second["slices"]:
        line = _first_line(first["slices"], second["slices"])
        found.append((line, ORDER.index("slices"), _differ("slices", "the line rules read %s and a CommonMark reader "
                                                                       "reads %s" % (_slice_at(first["slices"], line),
                                                                                     _slice_at(second["slices"], line)))))
    else:
        names = [first["slices"][n] for n in sorted(first["slices"])]
        for name, mine, theirs in zip(names, first["cards"], second["cards"]):
            a, b = _decided(mine), _decided(theirs)
            if a != b:
                found.append((_first_line(_by_line(mine), _by_line(theirs)), ORDER.index("card"),
                              _differ("card", "slice %s: the line rules take the card %s and a CommonMark reader, from "
                                              "the rendered text, takes %s" % (name, _say(a, "none"), _say(b, "none")))))
                break
    a, b = _decided(first["base"]), _decided(second["base"])
    if a != b:
        found.append((_first_line(_by_line(first["base"]), _by_line(second["base"])), ORDER.index("base"),
                      _differ("base", "the line rules take the base %s and a CommonMark reader, from the rendered "
                                      "text, takes %s" % (_say(a, "none (the station would fall back to its own base)"),
                                                          _say(b, "none")))))
    if first["withheld"] != second["withheld"]:
        line = _first_line(first["withheld"], second["withheld"])
        found.append((line, ORDER.index("withheld"), _differ("withheld", "the line rules hold this line %s and a "
                                                                         "CommonMark reader holds it %s"
                                                             % (_held(first["withheld"], line),
                                                                _held(second["withheld"], line)))))
    if not found:
        return None
    line, rank, words = min(found)
    return line, words


def _differ(decision, words):
    return ("the two readings differ on %s: %s; vertical-v2 runs only on a doc its line rules and a CommonMark reader "
            "take the same way" % (DECISIONS[decision], words))


def _slice_at(slices, line):
    return "slice %s's heading there" % slices[line] if line in slices else "no slice heading there"


def _held(withheld, line):
    if line not in withheld:
        return "in no withheld section"
    return "in the withheld section %s (its heading's name read as %r)" % withheld[line]


def difference(text):
    """compare's answer for a doc the line rules accept; None when they refuse it (their problem comes first)."""
    from . import spec
    doc = fences.read(text)
    if doc.problems:
        return None
    return compare(line_reading(doc, spec.sections(doc)), second_reading(text, len(doc.lines)))


def notes_difference(text):
    """(line, what) when a CommonMark reader declares a Markdown file the builder's notes and the line reading does
    not (module docstring, 5), or None. A file only the wide line reading declares is no difference: it is withheld
    (A14, C1A8-4)."""
    mine = notes.declaration(text)
    heads = commonmark.headings(commonmark.tokens(text))
    theirs = (heads[0][1], heads[0][2]) if heads and notes.DECLARES.search(heads[0][1]) else None
    if theirs is None or mine is not None:
        return None
    return theirs[1], ("the two readings differ on %s: a CommonMark reader's first heading, from the rendered text, is "
                       "%r, at line %d, which declares the file the builder's notes, and the line reading finds no "
                       "heading declaring it, so the file would reach the packets; vertical-v2 stops when a CommonMark "
                       "reader declares a builder's notes file the line reading does not" % (
                           DECISIONS["notes"], theirs[0], theirs[1]))
