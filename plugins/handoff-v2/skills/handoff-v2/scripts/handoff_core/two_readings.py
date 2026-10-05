"""handoff-v2 reads the build doc twice (the E15 lane contract A25 (1), after Astra's look 5; contract section 5).

    difference(text, found, first) -> (line, words) for the first line where the two readings take a decision of
        handoff-v2's differently, or the second reading refuses the doc, or None

THE HANDOFF TWO-READINGS RULE (stated once here and once in the contract, section 5). Every build doc handoff-v2
decides from is read twice: first by A22's line rules (`fences.py`, vertical-v2's file byte for byte) and this core's
own reading on them (`doc.py`), then by vertical-v2's second reading (A13: `commonmark.py`, `readings.py` and the two
modules it reads with, `spec.py` and `notes.py`, vertical-v2's files byte for byte over the vendored `markdown-it-py`
3.0.0 with `mdurl` 0.1.2 under `scripts/vendor/`, held equal by `tests/test_two_readings.py` and `tests/test_vendor.py`).
The first line where the two take a decision differently stops the run `doc-unreadable`, naming the line, before any
write and before the gate (`doc.read` raises; `select` stops). The decisions compared:

1. A13's own, as vertical-v2 compares them (`readings.compare` over `readings.line_reading` and
   `readings.second_reading`, unchanged): the slices (each slice's name and heading line), each slice's card, the
   recorded base, the withheld sections (`## Handoffs` and `## Punch list` among them), and the second reading's four
   refusals ("THE SECOND READING'S FOUR REFUSALS", `readings.py`);
2. the section boundaries: every level 1 or 2 heading (the line rules: a plain `# ` or `## ` line outside an accepted
   fence, `doc.TOP`; the second reading: every heading of level 1 or 2 the reader renders, ATX or Setext, wherever it
   stands), by its line and level, and which one opens `## Handoffs` or `## Punch list` (the line rules: the `## `
   line's exact name; the second reading: a level 2 heading whose rendered name is exactly `Handoffs` or
   `Punch list`), so the section the block lands in is the same section in both readings: a Setext heading inside
   `## Handoffs`, a Setext `Handoffs` heading and a `## Handoffs ##` closing-hash heading each stop at their line,
   and no reading ever adds a second `## Handoffs`;
3. the earlier handoff blocks and the record blocks: each one's heading line, kind and end (the line rules:
   `doc.BLOCK` and `doc.RECORD` on the source line, the block running to the next plain level 1 to 3 heading; the
   second reading: a level 3 heading whose rendered name reads `<YYYY-MM-DD> <dash> handoff`, or
   `<YYYY-MM-DD> <dash> review:` or `recheck:` then a space or the name's end, running to the next rendered heading of
   level 1 to 3), so a marked-up, closing-hashed or character-coded block heading stops at its line;
4. this core's own two labels in each slice's section (the line rules: `doc.read`'s plain `Depends on:` and
   `Questions:` lines; the second reading: every rendered paragraph line from the slice's heading to its next
   rendered heading of level 1 or 2 that reads as a `Depends on:` or `Questions:` label candidate after the same
   folding vertical-v2 applies to `Status:` candidates: format characters removed and leading whitespace stripped
   (`fences.label_form`, A15), the leading listed marks set aside (`fences.marks_off`, A18 (3)), folded
   (`fences.fold`, A17 (1)), then `depends on` or `questions`, spaces or tabs, and a colon, `OWN`), by the source
   line it starts on and the label: a bold `**Questions:**`, a code-span `` `Depends on:` `` or any rendered label
   whose source line is not that label in its plain form stops at its line, and so does a plain label the reader
   renders as no label;
5. one refusal of the second reading's own, refusal (a)'s shape for this core's labels: a rendered paragraph line in
   a slice's section that reads as a `Depends on:` or `Questions:` candidate (as in 4) in a paragraph whose rendered
   lines cannot all be mapped to source lines (`commonmark.paragraph_spans` marks it not exact) stops, naming the
   paragraph's first line: which source line holds which label cannot be told there;
6. THE ONE LABEL RULE (the E15 lane contract A26, after Astra's look 5b; stated once here and once in the contract,
   section 5, "Two readings"): inside a slice's section (from the slice's heading to its next rendered heading of
   level 1 or 2), every rendered block of any kind (a heading of any level, a paragraph line, a list item, a block
   quote, a table cell, a wrapped line) whose rendered text reads as a `Depends on:` or `Questions:` label
   candidate (as in 4) must come from that label in its plain form on one source line, with its value on the same
   line; anything else stops `doc-unreadable` naming the line, before any write. The plain form is a paragraph line
   that starts at column 0 with exactly `Depends on:` or `Questions:` (the line rules, `doc.read`). So: a rendered
   heading that reads as a label stops at its line (`### Questions: Which mode?`, which the line rules never read as
   a label); a rendered label line that runs over more than one source line (an inline HTML tag or comment holding
   its line ending, `commonmark.paragraph_spans`) stops at its first line; a list item, a block quote and a marked-up
   label already stop by 4 and the line rules; and a `Depends on:` line whose value is empty stops at its line as an
   empty `Questions:` does (A24 (2); the line rules' half, `doc._own_label_problem`), so a value on the next line is
   never read as no dependency; and, the value on the label's own line (the control room's send-back 1), a
   `Depends on:` or `Questions:` line whose paragraph continues on the next source line with a line that is not
   `Status:`, `Base:`, `Depends on:` or `Questions:` at column 0 stops at the label line (`Depends on: Slice A,`
   then `Slice B`; `Depends on: nothing` then a sentence; `Questions: Which mode,` then `and why?`), the line rules'
   half again; it only adds stops, and A24 (2)'s `none` and `nothing` rule stands as it is. A table cell is held to
   the rule where the reader renders one; the pinned `commonmark` preset renders no table, so a pipe row is paragraph
   text and reads as a label candidate only when the row's own text does.

When several differ, the earliest line is named; on one line, A13's comparison first, then the order above (the
refusals of 5 and 6 together, last). A doc both readings take the same way runs exactly as the line rules alone run
it. A13's words name vertical-v2, whose rule they are; the words of 2 to 6 are this core's.
"""
import re

from . import commonmark, fences, readings, spec

D = "\u2014"
BLOCK = re.compile(r"(\d{4}-\d{2}-\d{2}) %s handoff\Z" % D)
RECORD = re.compile(r"(\d{4}-\d{2}-\d{2}) %s (review|recheck):(?: |\Z)" % D)
OWN = re.compile(r"(depends[ \t]+on|questions)[ \t]*:")
NAMED = {"Handoffs": "## Handoffs", "Punch list": "## Punch list"}
LABEL = {"depends on": "Depends on:", "questions": "Questions:"}
RULE = ("handoff-v2 runs only on a doc vertical-v2's line rules and a CommonMark reader take the same way (the E15 "
        "lane contract A25)")
PLAIN = ("handoff-v2 reads its own labels only in their plain form: a paragraph line that starts at column 0 with "
         "exactly `Depends on:` or `Questions:`, its value on the same line (THE ONE LABEL RULE, the E15 lane contract "
         "A26)")
UNMAPPED = ("a CommonMark reader renders %r here, a `Depends on:` or `Questions:` label line in a paragraph whose "
            "rendered lines it cannot map to source lines (a code span, a link destination or a link title runs over a "
            "line ending), so which line holds which label cannot be told; handoff-v2 reads its labels only in a "
            "paragraph whose every rendered line maps to its own source line (the E15 lane contract A25)")
HEADED = ("a CommonMark reader renders a level %d heading %r here, which reads as a `%s` label: a label in a heading "
          "is never read, so its question would go unasked or its dependency unread; %s")
WRAPPED = ("a CommonMark reader renders %r here as one line running over more than one source line (to line %d: an "
           "inline HTML tag or comment holds its line ending), a `%s` label line whose value the line rules read only "
           "in part; %s")


def own_candidate(rendered):
    """`depends on` or `questions` when a rendered line reads as one of this core's labels (module docstring, 4),
    else None."""
    match = OWN.match(fences.fold(fences.marks_off(fences.label_form(rendered))))
    return None if match is None else " ".join(match.group(1).split())


def second(text, total, slices):
    """The second reading's decisions of 2 to 6: {"tops": {line: (level, opens)}, "names": {line: rendered name},
    "blocks": {line: (kind, end)}, "own": {line: [label]}, "refused": [(line, words)]}; `slices` is A13's second
    reading's slices ({heading line: name})."""
    stream = commonmark.tokens(text)
    heads = commonmark.headings(stream)
    tops, names = {}, {}
    for level, name, line in heads:
        if level <= 2:
            tops[line] = (level, NAMED.get(name) if level == 2 else None)
            names[line] = name
    upper = sorted(line for level, name, line in heads if level <= 3)
    blocks = {}
    for level, name, line in heads:
        if level != 3:
            continue
        kind = "handoff" if BLOCK.match(name) else "record" if RECORD.match(name) else None
        if kind is not None:
            blocks[line] = (kind, next((at for at in upper if at > line), total + 1))
    ends = sorted(tops)
    reach = [(line, next((at for at in ends if at > line), total + 1)) for line in sorted(slices)]

    def inside(line):
        return any(start < line < end for start, end in reach)

    own, refused = {}, []
    for level, name, line in heads:
        key = own_candidate(name)
        if key is not None and inside(line):
            refused.append((line, HEADED % (level, name, LABEL[key], PLAIN)))
    for line, last, rendered, exact in commonmark.paragraph_spans(stream):
        if not inside(line):
            continue
        key = own_candidate(rendered)
        if key is None:
            continue
        if not exact:
            refused.append((line, UNMAPPED % rendered))
            continue
        if last != line:
            refused.append((line, WRAPPED % (rendered, last, LABEL[key], PLAIN)))
        own.setdefault(line, []).append(key)
    for labels in own.values():
        labels.sort()
    return {"tops": tops, "names": names, "blocks": blocks, "own": own, "refused": refused}


def _first_line(left, right):
    return min(n for n in set(left) | set(right) if left.get(n) != right.get(n))


def _top(top, name=None):
    if top is None:
        return "no level 1 or 2 heading there"
    level, opens = top
    named = " named %r" % name if name is not None else ""
    return "a level %d heading%s%s" % (level, named, " opening `%s`" % opens if opens else "")


def _block(block):
    if block is None:
        return "no handoff or record block there"
    kind, end = block
    return "a %s block running to line %d" % ("handoff" if kind == "handoff" else "record", end - 1)


def _own(labels):
    if not labels:
        return "no `Depends on:` or `Questions:` label there"
    return " and ".join("a `%s` label" % LABEL[key] for key in labels)


def difference(text, found, first):
    """(line, words) for the first line where the two readings differ (module docstring), or None. `found` is
    `fences.read`'s Doc of a doc the line rules accept; `first` the line reading's decisions of 2 to 4 in `second`'s
    shape: {"tops", "blocks", "own"}."""
    total = len(found.lines)
    theirs = readings.second_reading(text, total)
    out = []
    a13 = readings.compare(readings.line_reading(found, spec.sections(found)), theirs)
    if a13 is not None:
        out.append((a13[0], 0, a13[1]))
    mine = second(text, total, theirs["slices"])
    if first["tops"] != mine["tops"]:
        line = _first_line(first["tops"], mine["tops"])
        out.append((line, 1, "the two readings differ on the section boundaries (every level 1 or 2 heading, and the "
                             "one that opens `## Handoffs` or `## Punch list`, where the handoff block lands): the "
                             "line rules read %s and a CommonMark reader, from the rendered text, reads %s; %s"
                    % (_top(first["tops"].get(line)), _top(mine["tops"].get(line), mine["names"].get(line)), RULE)))
    if first["blocks"] != mine["blocks"]:
        line = _first_line(first["blocks"], mine["blocks"])
        out.append((line, 2, "the two readings differ on the earlier handoff blocks and the record blocks (each one's "
                             "heading line, kind and end): the line rules read %s and a CommonMark reader, from the "
                             "rendered text, reads %s; handoff-v2 reads a block heading only in its plain form, "
                             "`### <YYYY-MM-DD> %s handoff` with no markup; %s"
                    % (_block(first["blocks"].get(line)), _block(mine["blocks"].get(line)), D, RULE)))
    if first["own"] != mine["own"]:
        line = _first_line(first["own"], mine["own"])
        out.append((line, 3, "the two readings differ on this core's own labels in a slice's section: the line rules "
                             "read %s and a CommonMark reader, from the rendered text, reads %s; handoff-v2 reads a "
                             "`Depends on:` or `Questions:` label only in its plain form, at column 0 with no markup; "
                             "%s" % (_own(first["own"].get(line)), _own(mine["own"].get(line)), RULE)))
    for line, words in mine["refused"]:
        out.append((line, 4, words))
    if not out:
        return None
    line, rank, words = min(out)
    return line, words
