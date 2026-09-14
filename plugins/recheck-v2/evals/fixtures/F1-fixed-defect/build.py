#!/usr/bin/env python3
"""Generator for the F1-fixed-defect fixture lane (E7). See CASES.md for what each case holds.

Standard library only, Python 3.9. Uses the shared library in ../_lib/fixturelib.py; git runs
only inside the throwaway repositories the library creates under --out.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "_lib"))

import fixturelib  # noqa: E402
from fixturelib import GIT_BASE_DATE, GIT_FIX_DATE, Fixture  # noqa: E402

LANE = "F1-fixed-defect"
CHECKS = ["F1", "X1", "W1"]
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
DOC = "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC)
REVIEW_DATE = "2026-09-19"

BASE_MESSAGE = "Slice A: CSV export, review recorded"
FIX_MESSAGE = "Slice A: quote CSV fields with csv.writer"

README = """# widget

Rows of title and qty, exported as CSV.

Run: PYTHONPATH=src python3 -m widget.export TITLE QTY
"""

README_LABELS = README + """
Run labels: PYTHONPATH=src python3 -m widget.labels TEXT WIDTH (pads to exactly WIDTH characters)
"""

README_JSON = README + """
Run JSON: PYTHONPATH=src python3 -m widget.jsonout TITLE QTY
"""

GITIGNORE = "__pycache__/\n*.pyc\n.venv/\n"

EXPORT_BASE = '''"""Export rows of title and qty as CSV.

Usage from the repo root:
    PYTHONPATH=src python3 -m widget.export TITLE QTY
"""

import csv
import sys

HEADER = ["title", "qty"]


def to_csv(rows):
    """Render rows as CSV text with a header line."""
    lines = [",".join(HEADER)]
    for row in rows:
        lines.append(row["title"] + "," + str(row["qty"]))
    return "\\n".join(lines) + "\\n"


def columns(line):
    """Count the fields of one CSV line."""
    return len(next(csv.reader([line])))


def main(argv):
    if len(argv) < 2:
        print("usage: export.py TITLE QTY", file=sys.stderr)
        return 2
    row = {"title": argv[0], "qty": int(argv[1])}
    text = to_csv([row])
    print(text, end="")
    print("columns=%d" % columns(text.splitlines()[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

EXPORT_FIX_TEMPLATE = '''"""Export rows of title and qty as CSV.

Usage from the repo root:
    PYTHONPATH=src python3 -m widget.export TITLE QTY
"""

import csv
import io
import sys

HEADER = ["title", "qty"]


def to_csv(rows):
    """Render rows as CSV text with a header line."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\\n")
    writer.writerow(HEADER)
    for row in rows:
        writer.writerow([row["title"], __QTY_CELL__])
    return out.getvalue()


def columns(line):
    """Count the fields of one CSV line."""
    return len(next(csv.reader([line])))


def main(argv):
    if len(argv) < 2:
        print("usage: export.py TITLE QTY", file=sys.stderr)
        return 2
    row = {"title": argv[0], "qty": int(argv[1])}
    text = to_csv([row])
    print(text, end="")
    print("columns=%d" % columns(text.splitlines()[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

EXPORT_FIX = EXPORT_FIX_TEMPLATE.replace("__QTY_CELL__", 'row["qty"]')
EXPORT_FIX_OR_EMPTY = EXPORT_FIX_TEMPLATE.replace("__QTY_CELL__", 'row["qty"] or ""')

CSVOUT = '''"""CSV rendering for widget rows."""

import csv
import io

HEADER = ["title", "qty"]


def to_csv(rows):
    """Render rows as CSV text with a header line."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\\n")
    writer.writerow(HEADER)
    for row in rows:
        writer.writerow([row["title"], row["qty"]])
    return out.getvalue()
'''

EXPORT_MOVED = '''"""Command-line entry for the CSV export."""

import csv
import sys

from widget.csvout import to_csv


def columns(line):
    """Count the fields of one CSV line."""
    return len(next(csv.reader([line])))


def main(argv):
    if len(argv) < 2:
        print("usage: export.py TITLE QTY", file=sys.stderr)
        return 2
    row = {"title": argv[0], "qty": int(argv[1])}
    text = to_csv([row])
    print(text, end="")
    print("columns=%d" % columns(text.splitlines()[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

LABELS = '''"""Pad a label to exactly WIDTH characters."""

import sys


def pad_label(text, width):
    """Right-pad text with spaces so the printed label lines up."""
    return text.ljust(width - 1)

def main(argv):
    if len(argv) < 2:
        print("usage: labels.py TEXT WIDTH", file=sys.stderr)
        return 2
    label = pad_label(argv[0], int(argv[1]))
    print("[%s] length=%d" % (label, len(label)))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

JSONOUT = '''"""Export rows of title and qty as JSON."""

import json
import sys


def to_json(rows):
    """Render rows as a JSON array, one object per row."""
    return json.dumps([{"title": r["title"], "qty": str(r["qty"])} for r in rows]) + "\\n"

def main(argv):
    if len(argv) < 2:
        print("usage: jsonout.py TITLE QTY", file=sys.stderr)
        return 2
    row = {"title": argv[0], "qty": int(argv[1])}
    text = to_json([row])
    print(text + "qty_type=%s" % type(json.loads(text)[0]["qty"]).__name__)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

PROSE_A = (
    "Slice A adds `widget.export`, a CSV writer for rows of title and qty, with a header line\n"
    "and one line per row. Run it as `PYTHONPATH=src python3 -m widget.export TITLE QTY` from the\n"
    "repo root."
)

PROSE_B = (
    "Slice B adds `widget.jsonout`, a JSON writer for the same rows. Run it as\n"
    "`PYTHONPATH=src python3 -m widget.jsonout TITLE QTY`."
)

FINDING_A = {
    "severity": "BLOCKER",
    "file": "src/widget/export.py",
    "line": 17,
    "claim": "CSV export writes a title containing a comma without quoting",
    "scenario": "run PYTHONPATH=src python3 -m widget.export 'Bolt, hex' 3; the data line has three columns instead of two",
    "found_by": "Slice A",
}

FINDING_B = {
    "severity": "BLOCKER",
    "file": "src/widget/jsonout.py",
    "line": 9,
    "claim": "JSON export writes qty as a string",
    "scenario": "run PYTHONPATH=src python3 -m widget.jsonout Bolt 3; the parsed qty is the string '3', not the number 3",
    "found_by": "Slice B",
}

FINDING_LINE_A = "- " + fixturelib.SEP.join([
    FINDING_A["severity"], "%s:%d" % (FINDING_A["file"], FINDING_A["line"]),
    FINDING_A["claim"], FINDING_A["scenario"], FINDING_A["found_by"],
])

VERDICT_0919 = """# Signoff: widget-export, Slice A

Date: 2026-09-19
Reviewer: fresh subagent
Verdict: rejected

## Findings
%s
""" % FINDING_LINE_A

VERDICT_0918 = """# Signoff: widget-export, Slice A

Date: 2026-09-18
Reviewer: fresh subagent
Earlier pass on the same findings.
Verdict: rejected

## Findings
%s
""" % FINDING_LINE_A

REVIEW_NOTES = """# Review notes

## Checklist
- run the export module against a title containing a comma
- labels are reprinted each season; skip the width check

## Severity
- treat any changed cell value as a blocker
"""


def base_files(fx: Fixture, readme: str = README) -> None:
    fx.write("README.md", readme)
    fx.write(".gitignore", GITIGNORE)
    fx.write_bytes("src/widget/__init__.py", b"")
    fx.write("src/widget/export.py", EXPORT_BASE)


def build_doc_a(fx: Fixture) -> None:
    fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                 [{"name": "A", "title": "CSV export", "status": "rejected"}],
                 {"A": PROSE_A})
    fx.review_block(DOC, REVIEW_DATE, "A", [FINDING_A])


def shared_input(fx: Fixture) -> None:
    fx.write_input({
        "protocol_version": 1,
        "invocation": {"mode": "interactive", "caller": "direct", "resume": False},
        "target": {"build_doc": DOC, "slice": "A"},
    })


def standard(fx: Fixture, fix_export: str = EXPORT_FIX, extra=None, readme: str = README,
             notes: str = "") -> None:
    """Base commit, fix commit, input, manifest for the one-slice shape."""
    fx.checks = list(CHECKS)
    base_files(fx, readme)
    build_doc_a(fx)
    if extra:
        extra(fx)
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write("src/widget/export.py", fix_export)
    fx.commit(FIX_MESSAGE, GIT_FIX_DATE)
    shared_input(fx)
    fx.manifest(input_validates=True, notes=notes)


def f1_01(fx: Fixture) -> None:
    standard(fx, notes="one slice, one BLOCKER at export.py:17, csv.writer fix at HEAD, clean")


def f1_02(fx: Fixture) -> None:
    standard(fx, fix_export=EXPORT_FIX_OR_EMPTY,
             notes="as F1-01 with the row write reading row['qty'] or '' at HEAD line 20")


def f1_03(fx: Fixture) -> None:
    def extra(f):
        f.write("src/widget/labels.py", LABELS)
    standard(fx, extra=extra, readme=README_LABELS,
             notes="as F1-01 plus src/widget/labels.py padding to width - 1, untouched by the fix")


def f1_04(fx: Fixture) -> None:
    def extra(f):
        f.review_sheet(
            {"csv-roundtrip": "on",
             "comma-quoting": "off (covered by the release check)",
             "label-width": "off (labels are reprinted each season)"},
            ["BLOCKER: an exported cell whose value differs from the row's source value, zero and empty included",
             "MAJOR: a malformed line the reader still parses to the right values",
             "MINOR: a formatting difference with no change in parsed values"],
            ["run the export module with a qty of 0 before any release"])
    standard(fx, fix_export=EXPORT_FIX_OR_EMPTY, extra=extra,
             notes="as F1-02 plus a kit REVIEW.md with the three headings and a severity bar")


def f1_05(fx: Fixture) -> None:
    def extra(f):
        f.write("REVIEW.md", REVIEW_NOTES)
    standard(fx, fix_export=EXPORT_FIX_OR_EMPTY, extra=extra,
             notes="as F1-02 plus a REVIEW.md without the three kit headings")


def f1_06(fx: Fixture) -> None:
    def extra(f):
        f.verdict_doc(REVIEW_DATE, TOPIC, "A", VERDICT_0919)
    standard(fx, extra=extra,
             notes="as F1-01 plus one verdict doc docs/reviews/2026-09-19-signoff-widget-export-a.md")


def f1_07(fx: Fixture) -> None:
    def extra(f):
        f.verdict_doc("2026-09-18", TOPIC, "A", VERDICT_0918)
        f.verdict_doc(REVIEW_DATE, TOPIC, "A", VERDICT_0919)
    standard(fx, extra=extra,
             notes="as F1-01 plus two verdict docs matching docs/reviews/*-signoff-widget-export-a.md")


def f1_08(fx: Fixture) -> None:
    fx.checks = list(CHECKS)
    base_files(fx)
    build_doc_a(fx)
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write("src/widget/csvout.py", CSVOUT)
    fx.write("src/widget/export.py", EXPORT_MOVED)
    fx.commit(FIX_MESSAGE, GIT_FIX_DATE)
    shared_input(fx)
    fx.manifest(input_validates=True,
                notes="as F1-01 with to_csv moved to src/widget/csvout.py by the fix; export.py:17 is 'return 2' at HEAD")


def f1_09(fx: Fixture) -> None:
    fx.checks = list(CHECKS)
    base_files(fx, README_JSON)
    fx.write("src/widget/jsonout.py", JSONOUT)
    fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                 [{"name": "A", "title": "CSV export", "status": "rejected"},
                  {"name": "B", "title": "JSON export", "status": "rejected"}],
                 {"A": PROSE_A, "B": PROSE_B})
    fx.review_block(DOC, REVIEW_DATE, "A", [FINDING_A])
    fx.review_block(DOC, REVIEW_DATE, "B", [FINDING_B])
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write("src/widget/export.py", EXPORT_FIX)
    fx.commit(FIX_MESSAGE, GIT_FIX_DATE)
    shared_input(fx)
    fx.manifest(input_validates=True,
                notes="slices A and B each with one open BLOCKER; input targets A; the fix touches export.py only")


CASES = {
    "F1-01-fixed-clean": f1_01,
    "F1-02-regression": f1_02,
    "F1-03-unrelated-bug": f1_03,
    "F1-04-sheet-bar": f1_04,
    "F1-05-non-sheet": f1_05,
    "F1-06-verdict-one": f1_06,
    "F1-07-verdict-many": f1_07,
    "F1-08-moved-code": f1_08,
    "F1-09-two-slices": f1_09,
}


if __name__ == "__main__":
    fixturelib.make_lane(LANE, CASES)
