"""The spec a reviewer receives (ruling E15-8 as A3 widened it and A4 amended it; contract section 5): the
build doc of the reviewed commit with its ledger and the builder's working records removed.

Removed, read through the build-doc form's own parse (`station_core/templates.py`, unchanged) so a fenced
block is never mistaken for a heading or a label:

- the five withheld sections, `## Punch list` and `## Handoffs` (the ledger) and `## Build assumptions`,
  `## Deviations` and `## Discovered` (the builder's working records), each found by its heading level and
  name: a heading of level 1 or 2 (up to three leading spaces, one or more spaces or tabs after the hashes)
  whose name, with its runs of whitespace collapsed and any closing hashes dropped, is one of the five,
  compared without regard to case; each runs from its heading to the line before the next heading of
  level 1 or 2 (or the end), every block inside it included (C1A2-5);
- every parsed `Status:` label, in a slice's section or outside one, the header's included (M6).

Everything else stays, byte for byte. Each removal is reported with its line numbers, so every packet's
withheld list can name it.
"""
import re

from station_core import templates

WITHHELD = {"punch list": "## Punch list", "handoffs": "## Handoffs", "build assumptions": "## Build assumptions",
            "deviations": "## Deviations", "discovered": "## Discovered"}
LEDGER = ("## Punch list", "## Handoffs")
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$")
CLOSING = re.compile(r"(?:^|[ \t]+)#+$")


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
    """(the spec's text, [{"what", "lines": [first, last]}]) for one build doc's text."""
    parsed = templates.parse("build-doc", text)
    lines = parsed["lines"]
    fenced = set()
    inside = False
    for row in parsed["outline"]:
        if row["role"] == "fence":
            inside = not inside
            fenced.add(row["line"])
        elif inside:
            fenced.add(row["line"])
    top = []
    for number, raw in enumerate(lines, 1):
        if number in fenced:
            continue
        found = heading_of(raw.rstrip("\r\n"))
        if found is not None and found[0] <= 2:
            top.append(number)
    drop = set()
    removed = []
    for index, number in enumerate(top):
        name = withheld_name(lines[number - 1].rstrip("\r\n"))
        if name is None:
            continue
        end = top[index + 1] - 1 if index + 1 < len(top) else len(lines)
        drop.update(range(number, end + 1))
        removed.append({"what": name, "lines": [number, end]})
    for row in parsed["outline"]:
        if row["role"] == "label" and row.get("key") == "Status:" and row["line"] not in drop:
            drop.add(row["line"])
            removed.append({"what": "Status: line", "lines": [row["line"], row["line"]]})
    kept = "".join(line for number, line in enumerate(lines, 1) if number not in drop)
    removed.sort(key=lambda r: r["lines"][0])
    return kept, removed
