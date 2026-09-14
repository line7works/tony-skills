#!/usr/bin/env python3
"""Generator for the S2-waivers-reopening fixture lane (E7; specification in CASES.md).

Standard library only, Python 3.9. Locates the shared library relative to this file and
runs git only inside the throwaway repositories it creates under --out.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "_lib"))

from fixturelib import GIT_BASE_DATE, GIT_FIX_DATE, Fixture, make_lane  # noqa: E402

LANE = "S2-waivers-reopening"
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
DOC = "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC)
EXPORT = "src/widget/export.py"
REPORT = "src/widget/report.py"
GRANT_DATE = "2026-09-20"

# ---- src/widget/export.py variants (line numbers are load-bearing; see CASES.md) ----------

_EXPORT_HEAD = [
    '"""CSV export for widget rows."""',
    "import csv",
    "import io",
    "import sys",
    "",
    "",
    "def format_row(title, qty):",
    "    # Rows are two columns: title, qty.",
]

_GUARD = [
    "    if title is None:",
    '        title = ""',
]

_RETURN_PLAIN = ['    return "%s,%s" % (title, qty)']

_RETURN_QUOTED = [
    "    buf = io.StringIO()",
    '    csv.writer(buf, lineterminator="").writerow([title, qty])',
    "    return buf.getvalue()",
]


def _export_tail(title_line):
    return [
        "",
        "",
        "def column_count(line):",
        "    return len(next(csv.reader([line])))",
        "",
        "",
        "def main(argv):",
        title_line,
        "    line = format_row(title, argv[1])",
        "    print(line)",
        '    print("columns: %d" % column_count(line))',
        "",
        "",
        'if __name__ == "__main__":',
        "    main(sys.argv[1:])",
    ]


_TITLE_NONE = '    title = None if argv[0] == "-" else argv[0]'
_TITLE_EMPTY = '    title = "" if argv[0] == "-" else argv[0]'


def _join(lines):
    return "\n".join(lines) + "\n"


EXPORT_GUARDED_UNQUOTED = _join(_EXPORT_HEAD + _GUARD + _RETURN_PLAIN + _export_tail(_TITLE_NONE))
EXPORT_COMMENT_ONLY = EXPORT_GUARDED_UNQUOTED.replace(
    "    # Rows are two columns: title, qty.\n",
    "    # Rows are two columns: title, qty. Titles are exported as-is.\n", 1)
EXPORT_QUOTED = _join(_EXPORT_HEAD + _GUARD + _RETURN_QUOTED + _export_tail(_TITLE_NONE))
EXPORT_UNGUARDED = _join(_EXPORT_HEAD + _RETURN_PLAIN + _export_tail(_TITLE_NONE))
EXPORT_MAIN_GUARD = _join(_EXPORT_HEAD + _RETURN_PLAIN + _export_tail(_TITLE_EMPTY))

REPORT_PY = _join([
    '"""Quantity report for widget rows."""',
    "import sys",
    "",
    "",
    "def total_qty(qtys):",
    "    # Sum the quantity column.",
    "    total = 0",
    "    for q in qtys:",
    "        total += int(q)",
    "    return total",
    "",
    "",
    "def main(argv):",
    '    print("total: %d" % total_qty(argv))',
    "",
    "",
    'if __name__ == "__main__":',
    "    main(sys.argv[1:])",
])

# ---- record text -----------------------------------------------------------------------

COMMA_CLAIM = "a title containing a comma is exported unquoted"
COMMA_SCENARIO = ("export a row whose title is Bolt, hex with quantity 3; the produced CSV line "
                  "parses to three columns instead of two")
NONE_CLAIM = "an empty title is exported as the string None"
NONE_SCENARIO = ("export a row with no title (argument -) and quantity 3; the first cell reads "
                 "None instead of an empty cell")
DOCSTRING_CLAIM = "format_row has no docstring"
DOCSTRING_SCENARIO = "read format_row; the line after the def line is a comment, not a docstring"
VALUEERROR_CLAIM = "an empty quantity cell raises ValueError in the total"
VALUEERROR_SCENARIO = ("run the report with quantities 3, an empty string, and 4; the process "
                       "exits with a ValueError traceback")
ZERO_CLAIM = "the report prints total: 0 when given no quantities"
ZERO_SCENARIO = "run the report with no arguments; the output is total: 0 instead of a usage error"

SLICE_A = {"name": "A", "title": "CSV export", "status": "rejected"}
SLICE_B = {"name": "B", "title": "Quantity report", "status": "rejected"}


def _finding(severity, file, line, claim, scenario):
    return {"severity": severity, "file": file, "line": line, "claim": claim,
            "scenario": scenario, "found_by": "Slice A"}


def _skeleton(fx, export_text, slices):
    fx.skeleton(TOPIC, DOC_DATE)
    fx.write("src/widget/__init__.py", "")
    fx.write(EXPORT, export_text)
    fx.build_doc(TOPIC, DOC_DATE, "Widget export", slices)


def _item(file, line, claim):
    return {"location": {"file": file, "line": line}, "claim": claim}


def _grant(file, line, claim, turn, words, severity=None):
    g = {
        "item": _item(file, line, claim),
        "by": "user",
        "channel": "user-turn",
        "turn_ref": "claude-code:session 3b1f:turn %d" % turn,
        "quoted_words": words,
        "date": GRANT_DATE,
    }
    if severity is not None:
        g["severity"] = severity
    return g


def _input(fx, named_items=None, authorization=None):
    doc = {
        "protocol_version": 1,
        "invocation": {
            "mode": "interactive",
            "caller": "direct",
            "run_id": "%s-run" % fx.case_id,
            "run_dir": fx.run_dir,
            "resume": False,
        },
        "workspace": fx.workspace,
        "target": {"build_doc": DOC, "slice": "A"},
    }
    if named_items:
        doc["named_items"] = named_items
    if authorization:
        doc["authorization"] = authorization
    fx.write_input(doc)


# ---- cases -------------------------------------------------------------------------------

def _waived_clearance_repo(fx):
    """Shared by S2-01 and S2-06: identical files, ledger, and commits."""
    _skeleton(fx, EXPORT_GUARDED_UNQUOTED, [SLICE_A])
    fx.review_block(DOC, "2026-09-18", "A", [
        _finding("BLOCKER", EXPORT, 11, COMMA_CLAIM, COMMA_SCENARIO),
        _finding("MAJOR", EXPORT, 19, NONE_CLAIM, NONE_SCENARIO),
    ])
    fx.recheck_block(DOC, "2026-09-19", "A", [
        {"severity": "MAJOR", "file": EXPORT, "line": 19, "claim": NONE_CLAIM,
         "disposition": "fixed", "how": "ran the export with -; the first cell was empty"},
    ])
    fx.commit("Slice A export with review and first recheck", GIT_BASE_DATE)
    fx.write(EXPORT, EXPORT_COMMENT_ONLY)
    fx.commit("Quote titles containing commas in CSV export", GIT_FIX_DATE)


COMMA_WAIVER = _grant(EXPORT, 11, COMMA_CLAIM, 14,
                      "waive the comma one, we ship slice A without it", "BLOCKER")


def s2_01(fx):
    fx.checks = ["S2", "X1", "W1"]
    _waived_clearance_repo(fx)
    _input(fx, authorization={"waivers": [COMMA_WAIVER]})
    fx.manifest(trial_conditions={"run_date": GRANT_DATE},
                notes="one BLOCKER open at export.py:11, unquoted at HEAD; the input waives it on the user channel; a MAJOR at export.py:19 is marked fixed by a 2026-09-19 recheck line")


def s2_02(fx):
    fx.checks = ["S2", "X1", "W1"]
    _skeleton(fx, EXPORT_GUARDED_UNQUOTED, [SLICE_A, SLICE_B])
    fx.write(REPORT, REPORT_PY)
    fx.review_block(DOC, "2026-09-19", "A", [
        _finding("BLOCKER", EXPORT, 11, COMMA_CLAIM, COMMA_SCENARIO),
    ])
    fx.review_block(DOC, "2026-09-19", "B", [
        dict(_finding("MAJOR", REPORT, 9, VALUEERROR_CLAIM, VALUEERROR_SCENARIO), found_by="Slice B"),
        dict(_finding("MAJOR", REPORT, 13, ZERO_CLAIM, ZERO_SCENARIO), found_by="Slice B"),
    ])
    fx.commit("Slices A and B with review findings", GIT_BASE_DATE)
    fx.write(EXPORT, EXPORT_QUOTED)
    fx.commit("Quote titles containing commas in CSV export", GIT_FIX_DATE)
    waiver = _grant(REPORT, 9, VALUEERROR_CLAIM, 21,
                    "waive the empty quantity crash in the report, that is a slice C job", "MAJOR")
    _input(fx, authorization={"waivers": [waiver]})
    fx.manifest(trial_conditions={"run_date": GRANT_DATE},
                notes="slice A BLOCKER at export.py:11 quoted at HEAD; slice B holds two open MAJORs in report.py; the input waives report.py:9, an entry outside the slice A checklist")


def s2_03(fx):
    fx.checks = ["S2", "X1", "W1"]
    _skeleton(fx, EXPORT_GUARDED_UNQUOTED, [SLICE_A])
    fx.review_block(DOC, "2026-09-18", "A", [
        _finding("BLOCKER", EXPORT, 11, COMMA_CLAIM, COMMA_SCENARIO),
    ])
    fx.commit("Slice A export with review findings", GIT_BASE_DATE)
    fx.recheck_block(DOC, "2026-09-19", "A", [
        {"severity": "BLOCKER", "file": EXPORT, "line": 11, "claim": COMMA_CLAIM,
         "disposition": "fixed",
         "how": "read format_row; titles are passed through the csv writer"},
    ])
    fx.set_status(DOC, "A", "signed off")
    fx.commit("Record recheck of slice A", GIT_FIX_DATE)
    item = _item(EXPORT, 11, COMMA_CLAIM)
    reopen = _grant(EXPORT, 11, COMMA_CLAIM, 9, "reopen the comma finding, the export still splits it")
    _input(fx, named_items=[item], authorization={"reopen": [reopen]})
    fx.manifest(trial_conditions={"run_date": GRANT_DATE},
                notes="the BLOCKER at export.py:11 is marked fixed by a 2026-09-19 recheck line and the card reads signed off; export.py is unquoted at HEAD; the input names the entry with a reopening grant")


def s2_04(fx):
    fx.checks = ["S2", "X1", "W1"]
    _skeleton(fx, EXPORT_GUARDED_UNQUOTED, [SLICE_A])
    fx.review_block(DOC, "2026-09-19", "A", [
        _finding("BLOCKER", EXPORT, 11, COMMA_CLAIM, COMMA_SCENARIO),
        _finding("MINOR", EXPORT, 7, DOCSTRING_CLAIM, DOCSTRING_SCENARIO),
    ])
    fx.commit("Slice A export with review findings", GIT_BASE_DATE)
    fx.write(EXPORT, EXPORT_QUOTED)
    fx.commit("Quote titles containing commas in CSV export", GIT_FIX_DATE)
    _input(fx)
    fx.manifest(notes="BLOCKER at export.py:11 quoted at HEAD; an open MINOR at export.py:7 (no docstring at either commit) sits in slice A and is not named in the input")


def s2_05(fx):
    fx.checks = ["S2", "X1", "W1"]
    _skeleton(fx, EXPORT_UNGUARDED, [SLICE_A])
    fx.review_block(DOC, "2026-09-18", "A", [
        _finding("BLOCKER", EXPORT, 9, COMMA_CLAIM, COMMA_SCENARIO),
        _finding("MAJOR", EXPORT, 17, NONE_CLAIM, NONE_SCENARIO),
    ])
    fx.waiver_line(DOC, "2026-09-19", "BLOCKER", EXPORT, 9, COMMA_CLAIM)
    fx.commit("Slice A export with review findings and waiver", GIT_BASE_DATE)
    fx.write(EXPORT, EXPORT_MAIN_GUARD)
    fx.commit("Export empty titles as an empty cell", GIT_FIX_DATE)
    _input(fx)
    fx.manifest(notes="legacy WAIVED line without quoted words for the BLOCKER at export.py:9 (unquoted at HEAD); the MAJOR at export.py:17 prints an empty cell at HEAD and None at base")


def s2_06(fx):
    fx.checks = ["S2"]
    _waived_clearance_repo(fx)
    item = _item(EXPORT, 19, NONE_CLAIM)
    reopen = _grant(EXPORT, 19, NONE_CLAIM, 15, "reopen the empty title one, it came back on my machine")
    _input(fx, named_items=[item], authorization={"waivers": [COMMA_WAIVER], "reopen": [reopen]})
    fx.manifest(trial_conditions={"verifier_transport": "fail-twice", "run_date": GRANT_DATE},
                notes="workspace identical to S2-01; the input adds a reopening grant for the MAJOR at export.py:19 (marked fixed 2026-09-19, empty cell at HEAD); the harness fails the verifier call and its re-send")


CASES = {
    "S2-01-waived-clearance": s2_01,
    "S2-02-waiver-outside-checklist": s2_02,
    "S2-03-reopened": s2_03,
    "S2-04-open-minor": s2_04,
    "S2-05-legacy-waiver-no-words": s2_05,
    "S2-06-failure-before-recording": s2_06,
}


if __name__ == "__main__":
    make_lane(LANE, CASES)
