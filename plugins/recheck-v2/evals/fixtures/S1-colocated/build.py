#!/usr/bin/env python3
"""Generator for the S1-colocated fixture lane (recheck-v2 E7).

Builds the three cases of CASES.md: a widget project with a CSV export module, a build doc
whose review block holds findings at one shared location, and a fix commit on top of the base
review commit. Standard library only; git runs only inside the throwaway repos under --out.
"""
import os
import sys

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
sys.path.insert(0, os.path.normpath(LIB_DIR))

import fixturelib  # noqa: E402
from fixturelib import Fixture, GIT_BASE_DATE, GIT_FIX_DATE  # noqa: E402

LANE = "S1-colocated"
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
REVIEW_DATE = "2026-09-19"
EXPORT = "src/widget/export.py"

README = "# widget\nCSV export for widget rows lives in `src/widget/export.py`.\n"

SLICE_PROSE = (
    "Slice A renders widget rows as CSV lines through `widget.export.format_row`. The CLI\n"
    "`python3 -m widget.export` prints one row and the column count a CSV reader sees."
)

HEAD_PART = '''"""CSV export for widget rows."""
import argparse
import csv
import io

FIELDS = ("id", "title", "qty")


def format_row(row):
    """Render one row as a CSV line."""
'''

TAIL_PART = '''

def column_count(line):
    """Count the columns a CSV reader sees in one line."""
    return len(next(csv.reader(io.StringIO(line))))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="widget.export")
    parser.add_argument("--id", default="1")
    parser.add_argument("--title")
    parser.add_argument("--qty", default="2")
    args = parser.parse_args(argv)
    row = {"id": args.id, "qty": args.qty}
    if args.title is not None:
        row["title"] = args.title
    line = format_row(row)
    print(line)
    print("columns=%d" % column_count(line))


if __name__ == "__main__":
    main()
'''

EXPORT_BASE = HEAD_PART + '    return ",".join(str(row.get(k)) for k in FIELDS)\n' + TAIL_PART

EXPORT_Q = HEAD_PART + '''    return ",".join(quote(str(row.get(k))) for k in FIELDS)


def quote(value):
    """Wrap a value in double quotes when it holds a comma."""
    if "," in value:
        return '"' + value.replace('"', '""') + '"'
    return value
''' + TAIL_PART

EXPORT_QN = HEAD_PART + '''    return ",".join(quote(row.get(k)) for k in FIELDS)


def quote(value):
    """Render a cell: a missing value is an empty quoted field, a comma forces quotes."""
    if value is None:
        return '""'
    value = str(value)
    if "," in value:
        return '"' + value.replace('"', '""') + '"'
    return value
''' + TAIL_PART

COMMA_CLAIM = "CSV export does not quote a field that contains a comma"
COMMA_SCENARIO = "export a row whose title contains a comma; the produced CSV has one extra column"
NONE_CLAIM = "a missing title exports as the string None"
NONE_SCENARIO = "export a row with no title; the CSV cell reads None instead of an empty quoted field"


def comma_finding():
    return {"severity": "BLOCKER", "file": EXPORT, "line": 11, "claim": COMMA_CLAIM,
            "scenario": COMMA_SCENARIO, "found_by": "Slice A"}


def legacy_line(severity, scenario):
    return "- " + fixturelib.SEP.join([severity, "%s:11" % EXPORT, scenario, "Slice A"])


def base_state(fx):
    """The shared repo at the base commit, minus the ledger lines; returns the doc path."""
    fx.skeleton(TOPIC, DOC_DATE)
    fx.write("README.md", README)
    fx.write_bytes("src/widget/__init__.py", b"")
    fx.write(EXPORT, EXPORT_BASE)
    doc = fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                       [{"name": "A", "title": "CSV export", "status": "rejected"}],
                       prose={"A": SLICE_PROSE})
    return doc


def finish(fx, fix_text, notes):
    fx.commit("Slice A: CSV export, review recorded", GIT_BASE_DATE)
    fx.write(EXPORT, fix_text)
    fx.commit("Slice A: quote CSV fields", GIT_FIX_DATE)
    fx.write_input({
        "protocol_version": 1,
        "invocation": {"mode": "interactive", "caller": "direct",
                       "run_id": "%s-run" % fx.case_id, "run_dir": fx.run_dir, "resume": False},
        "workspace": fx.workspace,
        "target": {"build_doc": "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC), "slice": "A"},
    })
    fx.checks = ["S1", "W3"]
    fx.manifest(input_validates=True, notes=notes)


def s1_01(fx):
    doc = base_state(fx)
    fx.review_block(doc, REVIEW_DATE, "A", [
        comma_finding(),
        {"severity": "MAJOR", "file": EXPORT, "line": 11, "claim": NONE_CLAIM,
         "scenario": NONE_SCENARIO, "found_by": "Slice A"},
    ])
    finish(fx, EXPORT_Q,
           "two full-shape entries at src/widget/export.py:11; fix commit is variant Q (comma quoting only)")


def s1_02(fx):
    doc = base_state(fx)
    fx.review_block(doc, REVIEW_DATE, "A", [comma_finding()])
    fx.raw_ledger_line(doc, legacy_line("MAJOR", NONE_SCENARIO))
    finish(fx, EXPORT_QN,
           "a full-shape entry and a legacy four-field entry at src/widget/export.py:11; fix commit is variant QN")


def s1_03(fx):
    doc = base_state(fx)
    fx.raw_ledger_line(doc, "\n### %s — review: Slice A\n%s\n"
                       % (REVIEW_DATE, legacy_line("BLOCKER", COMMA_SCENARIO)))
    finish(fx, EXPORT_Q,
           "one legacy four-field entry at src/widget/export.py:11, no other entry at that location; fix commit is variant Q")


CASES = {
    "S1-01-two-claims-one-location": s1_01,
    "S1-02-legacy-claimless-shared": s1_02,
    "S1-03-legacy-claimless-unique": s1_03,
}


if __name__ == "__main__":
    fixturelib.make_lane(LANE, CASES)
