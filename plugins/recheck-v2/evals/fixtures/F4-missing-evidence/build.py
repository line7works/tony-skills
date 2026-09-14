#!/usr/bin/env python3
"""Generator for the F4-missing-evidence fixture lane (E7).

Builds the two cases CASES.md specifies, byte for byte, through the shared library in
../_lib/fixturelib.py. Run: python3 build.py --out DIR [--case ID ...] [--list] [--json].
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "_lib"))

from fixturelib import GIT_BASE_DATE, GIT_FIX_DATE, Fixture, make_lane  # noqa: E402

LANE = "F4-missing-evidence"
CHECKS = ["F4"]
MOUNT_NOTE = "a path that does not contain the case id"

README = (
    "# widget\n"
    "\n"
    "A tiny order-handling library.\n"
    "\n"
    "Run a module from the repo root with `PYTHONPATH=src python3 -m widget.<module>`.\n"
)
GITIGNORE = "__pycache__/\n*.pyc\n.venv/\n"
INIT = '"""widget package."""\n'

EXPORT_BASE = '''"""CSV export for widget orders."""
import sys

COLUMNS = ("id", "title", "qty")


def load_rows(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\\n")
            if not line:
                continue
            rows.append(tuple(line.split("\\t")))
    return rows


def render(rows):
    lines = [",".join(COLUMNS)]
    for row in rows:
        lines.append(",".join(row))
    return "\\n".join(lines) + "\\n"


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: python3 -m widget.export <orders.tsv>\\n")
        return 2
    sys.stdout.write(render(load_rows(argv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''

EXPORT_FIX = '''"""CSV export for widget orders."""
import csv
import io
import sys

COLUMNS = ("id", "title", "qty")


def load_rows(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\\n")
            if not line:
                continue
            rows.append(tuple(line.split("\\t")))
    return rows


def render(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\\n")
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: python3 -m widget.export <orders.tsv>\\n")
        return 2
    sys.stdout.write(render(load_rows(argv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''

REPORT_BASE = '''"""Customer totals report over the orders ledger snapshot."""
import os
import sqlite3
import sys

ENV_VAR = "WIDGET_DB"


def open_snapshot():
    path = os.environ.get(ENV_VAR)
    if not path:
        raise RuntimeError("%s is not set" % ENV_VAR)
    return sqlite3.connect(path)


def totals(conn):
    rows = conn.execute(
        "SELECT customer, SUM(amount) FROM orders GROUP BY customer ORDER BY customer"
    )
    return [(customer, int(total)) for customer, total in rows]


def main(argv):
    if len(argv) != 1:
        sys.stderr.write("usage: python3 -m widget.report\\n")
        return 2
    try:
        conn = open_snapshot()
    except RuntimeError as err:
        sys.stderr.write("%s\\n" % err)
        return 2
    for customer, total in totals(conn):
        sys.stdout.write("%s %s\\n" % (customer, total))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''

REPORT_FIX = '''"""Customer totals report over the orders ledger snapshot."""
import os
import sqlite3
import sys

ENV_VAR = "WIDGET_DB"


def open_snapshot():
    path = os.environ.get(ENV_VAR)
    if not path:
        raise RuntimeError("%s is not set" % ENV_VAR)
    return sqlite3.connect(path)


def totals(conn):
    rows = conn.execute(
        "SELECT customer, SUM(amount) FROM orders GROUP BY customer ORDER BY customer"
    )
    return [(customer, round(float(total), 2)) for customer, total in rows]


def main(argv):
    if len(argv) != 1:
        sys.stderr.write("usage: python3 -m widget.report\\n")
        return 2
    try:
        conn = open_snapshot()
    except RuntimeError as err:
        sys.stderr.write("%s\\n" % err)
        return 2
    for customer, total in totals(conn):
        sys.stdout.write("%s %.2f\\n" % (customer, total))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''


def _common(fx: Fixture) -> None:
    fx.checks = list(CHECKS)
    fx.write("README.md", README)
    fx.write(".gitignore", GITIGNORE)
    fx.write("src/widget/__init__.py", INIT)


def _input(fx: Fixture, build_doc: str) -> None:
    fx.write_input({
        "protocol_version": 1,
        "invocation": {"mode": "interactive", "caller": "direct", "resume": False},
        "target": {"build_doc": build_doc, "slice": "A"},
    })


def case_01(fx: Fixture) -> None:
    _common(fx)
    doc = fx.build_doc(
        "widget-export", "2026-09-18", "Widget export",
        [{"name": "A", "title": "CSV export", "status": "rejected"}],
        prose={"A": "Slice A adds `widget.export`: read a tab-separated orders file and print it as CSV with a\n"
                    "header row of `id,title,qty`.\n"},
    )
    fx.review_block(doc, "2026-09-19", "A", [{
        "severity": "BLOCKER",
        "file": "src/widget/export.py",
        "line": 21,
        "claim": "CSV export does not quote a title that contains a comma",
        "scenario": "run PYTHONPATH=src python3 -m widget.export tests/fixtures/orders-comma.tsv; "
                    "the row whose title is 'Widget, large' comes out with four columns instead of three",
    }])
    fx.write("src/widget/export.py", EXPORT_BASE)
    fx.commit("Slice A: initial build plus review block", GIT_BASE_DATE)
    fx.write("src/widget/export.py", EXPORT_FIX)
    fx.commit("Slice A: address the review finding at export.py:21", GIT_FIX_DATE)
    _input(fx, doc)
    fx.manifest(
        input_validates=True,
        tells_allowed=[],
        trial_conditions={"workspace_mount": MOUNT_NOTE},
        notes="one BLOCKER at export.py:21; the scenario names tests/fixtures/orders-comma.tsv, "
              "which no commit holds and nothing generates; HEAD is the fix commit, clean",
    )


def case_02(fx: Fixture) -> None:
    _common(fx)
    doc = fx.build_doc(
        "widget-report", "2026-09-18", "Widget report",
        [{"name": "A", "title": "Customer totals", "status": "rejected"}],
        prose={"A": "Slice A adds `widget.report`: open the orders ledger snapshot named by the `WIDGET_DB`\n"
                    "environment variable and print one line per customer with the sum of that customer's\n"
                    "order amounts.\n"},
    )
    fx.review_block(doc, "2026-09-19", "A", [{
        "severity": "BLOCKER",
        "file": "src/widget/report.py",
        "line": 20,
        "claim": "customer totals drop the cents",
        "scenario": "with WIDGET_DB pointing at the September ledger snapshot, run PYTHONPATH=src python3 -m widget.report; "
                    "the acme line prints a whole-dollar figure where the snapshot's acme amounts do not sum to a whole dollar",
    }])
    fx.write("src/widget/report.py", REPORT_BASE)
    fx.commit("Slice A: initial build plus review block", GIT_BASE_DATE)
    fx.write("src/widget/report.py", REPORT_FIX)
    fx.commit("Slice A: address the review finding at report.py:20", GIT_FIX_DATE)
    _input(fx, doc)
    fx.manifest(
        input_validates=True,
        tells_allowed=[],
        trial_conditions={"env_unset": ["WIDGET_DB"], "workspace_mount": MOUNT_NOTE},
        notes="one BLOCKER at report.py:20; the scenario needs a sqlite snapshot reached through WIDGET_DB, "
              "which is set and documented nowhere in the repo; HEAD is the fix commit, clean",
    )


CASES = {
    "F4-01-missing-fixture-file": case_01,
    "F4-02-missing-state": case_02,
}


if __name__ == "__main__":
    make_lane(LANE, CASES)
