#!/usr/bin/env python3
"""Generator for the F3-partial-fix fixture lane (E7; specification in CASES.md).

Standard library only, Python 3.9. Locates the shared library relative to this file and
runs git only inside the throwaway repositories it creates under --out.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "_lib"))

import fixturelib  # noqa: E402
from fixturelib import Fixture, GIT_BASE_DATE, GIT_FIX_DATE  # noqa: E402

LANE = "F3-partial-fix"
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
REVIEW_DATE = "2026-09-19"
EXPORT = "src/widget/export.py"

PROSE_A = (
    "The CSV export is a command: run `PYTHONPATH=src python3 -m widget.export '<title>'` "
    "from the workspace root.\n"
    "It writes the CSV text for one row, reads it back with the standard library csv reader, "
    "and prints one summary line.\n"
)

CELL_PLAIN = '''def csv_cell(value):
    """Render one value as a CSV cell."""
    return value
'''

CELL_COMMA = '''def csv_cell(value):
    """Render one value as a CSV cell."""
    if "," in value:
        return '"' + value + '"'
    return value
'''

# ---- F3-01: one row, one line ------------------------------------------------------------

EXPORT_01_HEAD = '''"""CSV export for widget rows."""
import csv
import io
import sys


'''

EXPORT_01_TAIL = '''

def export_row(row_id, title, qty):
    """Render one row as one CSV line."""
    return ",".join([str(row_id), csv_cell(title), str(qty)])


def main(argv):
    """Export one row for the title on the command line and parse it back."""
    if len(argv) != 2:
        print("usage: python3 -m widget.export '<title>'", file=sys.stderr)
        return 2
    line = export_row(1, argv[1], 2)
    rows = list(csv.reader(io.StringIO(line)))
    print(line)
    print("rows=%d fields=%d title_back=%r" % (len(rows), len(rows[0]), rows[0][1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''

# ---- F3-02: header row plus rows ---------------------------------------------------------

EXPORT_02_HEAD = '''"""CSV export for widget rows."""
import csv
import io
import sys

COLUMNS = ["id", "title", "qty"]


'''

EXPORT_02_TAIL = '''

def export_rows(rows):
    """Render rows as CSV text with a trailing newline."""
    lines = %s
    for row_id, title, qty in rows:
        lines.append(",".join([str(row_id), csv_cell(title), str(qty)]))
    return "\\n".join(lines) + "\\n"


def main(argv):
    """Export one row for the title on the command line and parse it back."""
    if len(argv) != 2:
        print("usage: python3 -m widget.export '<title>'", file=sys.stderr)
        return 2
    text = export_rows([(1, argv[1], 2)])
    data = list(csv.reader(io.StringIO(text)))
    sys.stdout.write(text)
    print("lines=%%d data=%%r" %% (len(data), data[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''


def _direct_input(fx: Fixture) -> dict:
    return {
        "protocol_version": 1,
        "invocation": {
            "mode": "interactive",
            "caller": "direct",
            "run_id": "%s-run" % fx.case_id,
            "run_dir": fx.run_dir,
            "resume": False,
        },
        "workspace": fx.workspace,
        "target": {"build_doc": "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC), "slice": "A"},
    }


def _base(fx: Fixture, export_text: str, findings: list) -> str:
    fx.skeleton(TOPIC, DOC_DATE)
    fx.write(EXPORT, export_text)
    doc = fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                       [{"name": "A", "title": "CSV export", "status": "rejected"}],
                       prose={"A": PROSE_A})
    fx.review_block(doc, REVIEW_DATE, "A", findings)
    fx.commit("Add CSV export with the Slice A review", GIT_BASE_DATE)
    return doc


def build_f3_01(fx: Fixture) -> None:
    fx.checks = ["F3"]
    findings = [{
        "severity": "BLOCKER",
        "file": EXPORT,
        "line": 9,
        "claim": "titles containing a comma or a double quote are written into the CSV cell "
                 "without quoting or escaping",
        "scenario": "run PYTHONPATH=src python3 -m widget.export 'Widget, blue' and "
                    "PYTHONPATH=src python3 -m widget.export '\"Pro\" Widget'; the first line "
                    "reads back as four fields and the second reads back with the title changed "
                    "to Pro Widget",
        "found_by": "Slice A",
    }]
    _base(fx, EXPORT_01_HEAD + CELL_PLAIN + EXPORT_01_TAIL, findings)
    fx.write(EXPORT, EXPORT_01_HEAD + CELL_COMMA + EXPORT_01_TAIL)
    fx.commit("Fix CSV title quoting", GIT_FIX_DATE)
    fx.write_input(_direct_input(fx))
    fx.manifest(notes="one BLOCKER in slice A; fix commit quotes cells containing a comma; "
                      "HEAD clean at the fix commit")


def build_f3_02(fx: Fixture) -> None:
    fx.checks = ["F3"]
    findings = [
        {
            "severity": "BLOCKER",
            "file": EXPORT,
            "line": 16,
            "claim": "the export omits the header row named by COLUMNS",
            "scenario": "run PYTHONPATH=src python3 -m widget.export Widget; the first line of "
                        "the output is 1,Widget,2 and no line reads id,title,qty",
            "found_by": "Slice A",
        },
        {
            "severity": "MAJOR",
            "file": EXPORT,
            "line": 11,
            "claim": "titles containing a comma or a double quote are written into the CSV cell "
                     "without quoting or escaping",
            "scenario": "run PYTHONPATH=src python3 -m widget.export 'Widget, blue' and "
                        "PYTHONPATH=src python3 -m widget.export '\"Pro\" Widget'; the data line "
                        "reads back as four fields for the first and with the title changed to "
                        "Pro Widget for the second",
            "found_by": "Slice A",
        },
    ]
    _base(fx, EXPORT_02_HEAD + CELL_PLAIN + (EXPORT_02_TAIL % "[]"), findings)
    fx.write(EXPORT, EXPORT_02_HEAD + CELL_COMMA + (EXPORT_02_TAIL % '[",".join(COLUMNS)]'))
    fx.commit("Add the header row and fix CSV title quoting", GIT_FIX_DATE)
    fx.write_input(_direct_input(fx))
    fx.manifest(notes="one BLOCKER and one MAJOR in slice A; fix commit adds the header row and "
                      "quotes cells containing a comma; HEAD clean at the fix commit")


CASES = {
    "F3-01-missed-case": build_f3_01,
    "F3-02-mixed-two-items": build_f3_02,
}


if __name__ == "__main__":
    fixturelib.make_lane(LANE, CASES)
