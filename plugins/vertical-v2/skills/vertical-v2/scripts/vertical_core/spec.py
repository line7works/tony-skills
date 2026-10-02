"""The spec a reviewer receives (ruling E15-8; reading CR-4): the build doc with its ledger removed.

Removed through the build-doc form's own parse (`station_core/templates.py`, unchanged): the
`## Punch list` section and every block in it, the `## Handoffs` section and every block in it, each
from its heading to the line before the next `## ` heading (or the end), and every slice's `Status:`
line. Everything else stays, byte for byte: the header, every slice's other labels, `## Build
assumptions`, `## Deviations`, `## Discovered`. Each removal is reported, so a packet's withheld list
can name it.
"""
from station_core import templates

REMOVED_SECTIONS = ("## Punch list", "## Handoffs")


def clean(text):
    """(the spec's text, [{"what", "lines": [first, last]}]) for one build doc's text."""
    parsed = templates.parse("build-doc", text)
    lines = parsed["lines"]
    drop = set()
    removed = []
    outline = parsed["outline"]
    headings = [row for row in outline if row["role"] == "heading"]
    for index, row in enumerate(headings):
        key = row.get("key", "").rstrip()
        if key in REMOVED_SECTIONS:
            end = headings[index + 1]["line"] - 1 if index + 1 < len(headings) else len(lines)
            drop.update(range(row["line"], end + 1))
            removed.append({"what": key, "lines": [row["line"], end]})
    in_slice = False
    for row in outline:
        if row["role"] == "heading":
            in_slice = templates.BUILD["slice"].match(row.get("key", "").rstrip()) is not None
        elif row["role"] == "label" and row.get("key") == "Status:" and in_slice and row["line"] not in drop:
            drop.add(row["line"])
            removed.append({"what": "Status: line", "lines": [row["line"], row["line"]]})
    kept = "".join(line for number, line in enumerate(lines, 1) if number not in drop)
    removed.sort(key=lambda r: r["lines"][0])
    return kept, removed
