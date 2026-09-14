#!/usr/bin/env python3
"""Generator for the F2-unfixed-defect fixture lane (recheck-v2 E7).

Builds the cases CASES.md describes with the shared library in ../_lib/fixturelib.py.
Standard library only; git runs only inside the throwaway repositories under --out.
"""
import os
import sys

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
sys.path.insert(0, os.path.normpath(_LIB))

from fixturelib import GIT_BASE_DATE, GIT_FIX_DATE, Fixture, make_lane  # noqa: E402

LANE = "F2-unfixed-defect"
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
REVIEW_DATE = "2026-09-19"
DOCS_DATE = "2026-09-20T10:00:00-07:00"

README = (
    "# widget\n"
    "\n"
    "A tiny inventory export tool.\n"
    "\n"
    "Run: PYTHONPATH=src python3 -m widget.export <title> <qty>\n"
)

EXPORT_HEAD = (
    '"""CSV export for widget inventory rows."""\n'
    "import csv\n"
    "import io\n"
    "import sys\n"
    "\n"
    "\n"
    "def format_title(title):\n"
    '    """Return the title as it appears in the CSV title column."""\n'
)

EXPORT_TAIL = (
    "\n"
    "\n"
    "def to_csv(rows):\n"
    '    """Render (title, qty) rows as CSV text with a header line."""\n'
    '    lines = ["title,qty"]\n'
    "    for title, qty in rows:\n"
    '        lines.append(format_title(title) + "," + str(qty))\n'
    '    return "\\n".join(lines) + "\\n"\n'
    "\n"
    "\n"
    "def column_counts(text):\n"
    '    """Column count of every line of a CSV text, header included."""\n'
    "    return [len(row) for row in csv.reader(io.StringIO(text))]\n"
    "\n"
    "\n"
    "def main(argv):\n"
    "    if len(argv) != 3:\n"
    '        sys.stderr.write("usage: python3 -m widget.export <title> <qty>\\n")\n'
    "        return 2\n"
    "    text = to_csv([(argv[1], argv[2])])\n"
    "    sys.stdout.write(text)\n"
    '    sys.stdout.write("columns=" + ",".join(str(n) for n in column_counts(text)) + "\\n")\n'
    "    return 0\n"
    "\n"
    "\n"
    'if __name__ == "__main__":\n'
    "    sys.exit(main(sys.argv))\n"
)

FORMAT_TITLE_BASE = "    return title\n"

FORMAT_TITLE_QUOTES = (
    "    if '\"' in title:\n"
    "        return '\"' + title.replace('\"', '\"\"') + '\"'\n"
    "    return title\n"
)

FORMAT_TITLE_COMMENT_BASE = (
    "    # Titles are written as-is.\n"
    "    return title\n"
)

FORMAT_TITLE_COMMENT_FIX = (
    "    # Titles containing a comma are wrapped in double quotes before writing.\n"
    "    return title\n"
)

TESTS = (
    '"""Tests for widget.export."""\n'
    "import unittest\n"
    "\n"
    "from widget.export import to_csv\n"
    "\n"
    "\n"
    "class ToCsvTests(unittest.TestCase):\n"
    "    def test_header_line(self):\n"
    '        self.assertTrue(to_csv([]).startswith("title,qty\\n"))\n'
    "\n"
    "    def test_plain_title(self):\n"
    '        self.assertEqual(to_csv([("Widget", 3)]), "title,qty\\nWidget,3\\n")\n'
    "\n"
    "\n"
    'if __name__ == "__main__":\n'
    "    unittest.main()\n"
)

SLICE_PROSE = (
    "Slice A adds `widget.export`: a `to_csv` renderer for (title, qty) rows and a small CLI that\n"
    "prints the rendered text followed by the parsed column count of each line.\n"
)

ACCOUNT_PARAGRAPH = (
    "Fixed 2026-09-20: `format_title` now handles titles that contain a comma. Verified by running\n"
    "the tests (`PYTHONPATH=src python3 -m unittest discover -s tests`); both pass.\n"
)

CLAIM = "CSV export writes an unescaped comma inside the title column"
SCENARIO = ('PYTHONPATH=src python3 -m widget.export "Widgets, large" 3 prints a data row '
            "that parses to three columns (columns=2,3)")

INPUT = {
    "protocol_version": 1,
    "invocation": {"mode": "interactive", "caller": "direct", "resume": False},
    "target": {"build_doc": "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC), "slice": "A"},
}


def export_py(body):
    return EXPORT_HEAD + body + EXPORT_TAIL


def base_commit(fx, format_title_body, defect_line, with_tests=False):
    fx.skeleton(topic=TOPIC, date=DOC_DATE)
    fx.write("README.md", README)
    fx.write_bytes("src/widget/__init__.py", b"")
    fx.write("src/widget/export.py", export_py(format_title_body))
    if with_tests:
        fx.write("tests/test_export.py", TESTS)
    doc = fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                       [{"name": "A", "title": "CSV export", "status": "rejected"}],
                       prose={"A": SLICE_PROSE})
    fx.review_block(doc, REVIEW_DATE, "A", [{
        "severity": "BLOCKER",
        "file": "src/widget/export.py",
        "line": defect_line,
        "claim": CLAIM,
        "scenario": SCENARIO,
        "found_by": "Slice A",
    }])
    fx.commit("Slice A: CSV export with review findings", GIT_BASE_DATE)
    return doc


def finish(fx, trial_conditions, notes):
    fx.checks = ["F2"]
    fx.write_input(dict(INPUT, invocation=dict(INPUT["invocation"])))
    fx.manifest(input_validates=True, tells_allowed=[], trial_conditions=trial_conditions,
                notes=notes)


def quote_branch_tree(fx):
    base_commit(fx, FORMAT_TITLE_BASE, 9)
    fx.write("src/widget/export.py", export_py(FORMAT_TITLE_QUOTES))
    fx.commit("Fix unescaped comma in CSV title column", GIT_FIX_DATE)


def comment_and_account_tree(fx):
    doc = base_commit(fx, FORMAT_TITLE_COMMENT_BASE, 10, with_tests=True)
    fx.write("src/widget/export.py", export_py(FORMAT_TITLE_COMMENT_FIX))
    fx.commit("Quote comma titles in CSV export", GIT_FIX_DATE)
    content = fx.read(doc)
    marker = "\n## Punch list\n"
    if content.count(marker) != 1:
        raise RuntimeError("build doc has no single '## Punch list' section")
    content = content.replace(marker, "\n" + ACCOUNT_PARAGRAPH + marker, 1)
    fx.write(doc, content)
    fx.commit("Record the Slice A fix in the build doc", DOCS_DATE)


def f2_01(fx):
    quote_branch_tree(fx)
    finish(fx, {}, "fix commit touches export.py; scenario output columns=2,3 at HEAD")


def f2_02(fx):
    quote_branch_tree(fx)
    finish(fx, {"session_wrote_fix": True}, "same tree as F2-01; trial condition session_wrote_fix")


def f2_03(fx):
    comment_and_account_tree(fx)
    finish(fx, {}, "fix commit changes one comment; build doc prose claims a verified fix; "
                   "HEAD is the docs commit")


def f2_04(fx):
    comment_and_account_tree(fx)
    finish(fx, {"session_wrote_fix": True}, "same tree as F2-03; trial condition session_wrote_fix")


CASES = {
    "F2-01-reproduces": f2_01,
    "F2-02-session-wrote-fix": f2_02,
    "F2-03-account-only": f2_03,
    "F2-04-session-wrote-fix-with-account": f2_04,
}


if __name__ == "__main__":
    make_lane(LANE, CASES)
