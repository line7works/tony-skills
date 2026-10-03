"""The spec a reviewer receives (ruling E15-8 as A3 widened it and A4 amended it; the E15 lane contract A5 (2)
and A8; contract section 5): the build doc of the reviewed commit with its ledger and the builder's working
records removed.

What is fenced is decided by vertical-v2's one fence rule, strict plain code blocks (`fences.py`, A8: a fence
opens and closes at column 0, outside any list item or block quote), never by the frame's `templates.parse`
(frozen in E15, whose toggle a longer or an unclosed fence defeats, C1A3-1). Any fence line the rule does not
accept, and any raw HTML line outside an accepted fence (A9, C1A5-1 and C1A5-2: a line opening, after any indent
and container markers, with `<` and a letter, `/`, `!` or `?`), raises SpecUnreadable naming the line, so the
run stops (`doc-unreadable`) before any packet is built.
Outside fences, removed:

- the five withheld sections, `## Punch list` and `## Handoffs` (the ledger) and `## Build assumptions`,
  `## Deviations` and `## Discovered` (the builder's working records), each found by its heading level and
  name: a heading of level 1 or 2 (up to three leading spaces, one or more spaces or tabs after the hashes)
  whose name, with its runs of whitespace collapsed and any closing hashes dropped, is one of the five,
  compared without regard to case; each runs from its heading to the line before the next heading of
  level 1 or 2 outside a fence (or the end), every block inside it included (C1A2-5);
- every `Status:` label (a line that starts with `Status:`, the build-doc form's label test), in a slice's
  section or outside one, the header's included (M6).

Everything else stays, byte for byte. Each removal is reported with its line numbers, so every packet's
withheld list can name it.
"""
import re

from station_core import driver

from . import fences

WITHHELD = {"punch list": "## Punch list", "handoffs": "## Handoffs", "build assumptions": "## Build assumptions",
            "deviations": "## Deviations", "discovered": "## Discovered"}
LEDGER = ("## Punch list", "## Handoffs")
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$")
CLOSING = re.compile(r"(?:^|[ \t]+)#+$")
LABEL = "Status:"
STOP_TAG = "doc-unreadable"


class SpecUnreadable(driver.Usage):
    """A build doc holding a line this reader cannot place (a fence line the fence rule does not accept, or a raw
    HTML line): the run stops before any packet is built."""

    def __init__(self, line, what):
        driver.Usage.__init__(self, "the build doc's line %d: %s; its ledger cannot be told from content there, so "
                                    "no packet was built: vertical-v2 reads only plain code blocks whose fences open "
                                    "and close at the left margin, outside any list item or block quote, and no raw "
                                    "HTML line; the plan's author edits the doc and commits" % (line, what))
        self.line, self.what = line, what


def heading_of(line):
    """(level, name with whitespace collapsed) for a markdown heading line, else None."""
    match = HEADING.match(line)
    if not match:
        return None
    name = CLOSING.sub("", match.group(2))
    return len(match.group(1)), " ".join(name.split())


def withheld_name(line):
    """The canonical heading of a withheld section the line opens, else None."""
    found = heading_of(line)
    if found is None or found[0] > 2:
        return None
    return WITHHELD.get(found[1].lower())


def clean(text):
    """(the spec's text, [{"what", "lines": [first, last]}]) for one build doc's text; SpecUnreadable when a
    fence is unclosed or a line cannot be placed (a fence line the rule does not accept, a raw HTML line)."""
    lines = fences.split_lines(text)
    scan = fences.scan(lines)
    if scan.problems:
        raise SpecUnreadable(*scan.problems[0])
    fenced = scan.fenced
    top = []
    for number, raw in enumerate(lines, 1):
        if number in fenced:
            continue
        found = heading_of(fences.bare(raw, number))
        if found is not None and found[0] <= 2:
            top.append(number)
    drop = set()
    removed = []
    for index, number in enumerate(top):
        name = withheld_name(fences.bare(lines[number - 1], number))
        if name is None:
            continue
        end = top[index + 1] - 1 if index + 1 < len(top) else len(lines)
        drop.update(range(number, end + 1))
        removed.append({"what": name, "lines": [number, end]})
    for number, raw in enumerate(lines, 1):
        if number in fenced or number in drop:
            continue
        if fences.bare(raw, number).startswith(LABEL):
            drop.add(number)
            removed.append({"what": "Status: line", "lines": [number, number]})
    kept = "".join(line for number, line in enumerate(lines, 1) if number not in drop)
    removed.sort(key=lambda r: r["lines"][0])
    return kept, removed
