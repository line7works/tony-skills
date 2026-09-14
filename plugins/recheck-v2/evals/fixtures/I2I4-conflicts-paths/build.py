#!/usr/bin/env python3
"""Generator for the I2I4-conflicts-paths fixture lane (checks I2 and I4).

Builds the cases CASES.md describes: the widget project with its export module at a base
commit and a fix commit, the build doc(s) and punch-list blocks per case, and the input.json
each case carries. Standard library only; git runs inside the generated workspaces only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_lib"))

import fixturelib  # noqa: E402
from fixturelib import Fixture, GIT_BASE_DATE, GIT_FIX_DATE  # noqa: E402

LANE = "I2I4-conflicts-paths"
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
REVIEW_DATE = "2026-09-19"
EXPORT_DOC = "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC)
IMPORT_DOC = "docs/plans/%s-widget-import.md" % DOC_DATE
BASE_MESSAGE = "Add the widget export module and the Slice A review"
FIX_MESSAGE = "Quote CSV fields through the csv module"

EXPORT_BASE = '''"""CSV export for widget rows."""
import sys


def to_csv_row(title, qty):
    """Return one CSV line for a widget row."""
    return ",".join([title, str(qty)])


def main(argv):
    title, qty = argv[0], argv[1]
    print(to_csv_row(title, qty))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

EXPORT_FIX = '''"""CSV export for widget rows."""
import csv
import io
import sys


def to_csv_row(title, qty):
    """Return one CSV line for a widget row."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow([title, str(qty)])
    return buf.getvalue()


def main(argv):
    title, qty = argv[0], argv[1]
    print(to_csv_row(title, qty))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

IMPORTER = '''"""Import widget rows from title,qty strings."""
import sys


def parse_row(text):
    """Split 'title,qty' into a (title, qty) pair."""
    title, qty = text.split(",", 1)
    return title, qty


def total(rows):
    """Sum the quantities of parsed rows."""
    return sum(qty for _, qty in rows)


def main(argv):
    rows = [parse_row(a) for a in argv]
    print(total(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

SUMMARY = '''"""Summaries over widget rows."""
import sys


def total_qty(rows):
    """Sum the qty field of every row."""
    return sum(int(r.split(",", 1)[1]) for r in rows[1:])


def main(argv):
    print(total_qty(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

PROSE_A = "Slice A exports one widget row as a CSV line."
PROSE_B_SUMMARY = "Slice B totals the qty field over a list of rows."
PROSE_B_HEADER = "Slice B writes the CSV header row."
PROSE_IMPORT_A = "Slice A parses title,qty strings and totals the quantities."

EXPORT_FINDING = {
    "severity": "BLOCKER",
    "file": "src/widget/export.py",
    "line": 7,
    "claim": "CSV export writes unescaped commas inside quoted fields",
    "scenario": "export a row whose title contains a comma; the produced CSV has one extra column",
}
EXPORT_FINDING_B = dict(
    EXPORT_FINDING,
    scenario="export any row whose title contains a comma; the CSV reader parses one extra column",
)
IMPORT_FINDING = {
    "severity": "BLOCKER",
    "file": "src/widget/importer.py",
    "line": 13,
    "claim": "import totals quantities as strings",
    "scenario": "import the rows bolt,2 and nut,3; total raises TypeError instead of printing 5",
}
SUMMARY_FINDING = {
    "severity": "MAJOR",
    "file": "src/widget/summary.py",
    "line": 7,
    "claim": "summary skips the first row",
    "scenario": "summarize the rows bolt,2 and nut,3; the printed total is 3",
}

ITEM_EXPORT = {
    "severity": "BLOCKER",
    "location": {"file": "src/widget/export.py", "line": 7},
    "claim": EXPORT_FINDING["claim"],
    "failure_scenario": EXPORT_FINDING["scenario"],
    "record": {
        "document": EXPORT_DOC,
        "heading": "### %s — review: Slice A" % REVIEW_DATE,
        "date": REVIEW_DATE,
    },
    "slice": "A",
}


# ---- shared pieces -----------------------------------------------------------------------

def skeleton(fx):
    fx.skeleton(TOPIC, DOC_DATE)
    fx.write("src/widget/__init__.py", "")
    fx.write("src/widget/export.py", EXPORT_BASE)


def default_doc(fx):
    doc = fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                       [{"name": "A", "title": "CSV export", "status": "rejected"}],
                       prose={"A": PROSE_A})
    fx.review_block(doc, REVIEW_DATE, "A", [EXPORT_FINDING])
    return doc


def two_slice_doc(fx, b_status, b_finding):
    doc = fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                       [{"name": "A", "title": "CSV export", "status": "rejected"},
                        {"name": "B", "title": "Quantity summary", "status": b_status}],
                       prose={"A": PROSE_A, "B": PROSE_B_SUMMARY})
    fx.review_block(doc, REVIEW_DATE, "A", [EXPORT_FINDING])
    if b_finding is not None:
        fx.review_block(doc, REVIEW_DATE, "B", [b_finding])
    return doc


def commit_pair(fx):
    fx.commit(BASE_MESSAGE, GIT_BASE_DATE)
    fx.write("src/widget/export.py", EXPORT_FIX)
    fx.commit(FIX_MESSAGE, GIT_FIX_DATE)


def invocation(fx, mode="interactive", caller="direct", run_dir=None):
    return {
        "mode": mode,
        "caller": caller,
        "run_id": "%s-run" % fx.case_id,
        "run_dir": run_dir or fx.run_dir,
        "resume": False,
    }


def default_input(fx, target=None, **extra):
    doc = {
        "protocol_version": 1,
        "invocation": invocation(fx),
        "workspace": fx.workspace,
        "target": target or {"build_doc": EXPORT_DOC, "slice": "A"},
    }
    doc.update(extra)
    return doc


def default_repo(fx):
    skeleton(fx)
    default_doc(fx)
    commit_pair(fx)


def summary_repo(fx):
    skeleton(fx)
    fx.write("src/widget/summary.py", SUMMARY)
    two_slice_doc(fx, "rejected", SUMMARY_FINDING)
    commit_pair(fx)


# ---- I2 cases ----------------------------------------------------------------------------

def i2_01(fx):
    fx.checks = ["I2"]
    skeleton(fx)
    fx.write("src/widget/importer.py", IMPORTER)
    default_doc(fx)
    doc = fx.build_doc("widget-import", DOC_DATE, "Widget import",
                       [{"name": "A", "title": "Row import", "status": "rejected"}],
                       prose={"A": PROSE_IMPORT_A})
    fx.review_block(doc, REVIEW_DATE, "A", [IMPORT_FINDING])
    commit_pair(fx)
    fx.write_input(default_input(fx))
    fx.manifest(
        trial_conditions={"adapter_request": "recheck slice A"},
        notes="two build docs under docs/plans/ each with slice A at rejected; the request "
              "names no doc; the ambiguity sits at the adapter, input.json carries the first doc",
    )


def i2_02(fx):
    fx.checks = ["I2"]
    default_repo(fx)
    fx.write_input(default_input(fx, named_items=[
        {"location": {"file": "src/widget/export.py", "line": 99},
         "claim": "export drops the header row"},
    ]))
    fx.manifest(notes="named_items names a location and claim no record holds")


def i2_03(fx):
    fx.checks = ["I2"]
    skeleton(fx)
    doc = fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                       [{"name": "A", "title": "CSV export", "status": "rejected"},
                        {"name": "B", "title": "CSV header", "status": "rejected"}],
                       prose={"A": PROSE_A, "B": PROSE_B_HEADER})
    fx.review_block(doc, REVIEW_DATE, "A", [EXPORT_FINDING])
    fx.review_block(doc, REVIEW_DATE, "B", [EXPORT_FINDING_B])
    commit_pair(fx)
    fx.write_input(default_input(fx, named_items=[
        {"location": {"file": "src/widget/export.py", "line": 7},
         "claim": EXPORT_FINDING["claim"]},
    ]))
    fx.manifest(notes="named_items names a location and claim held by two review blocks "
                      "(Slice A and Slice B) with different scenarios")


def i2_04(fx):
    fx.checks = ["I2"]
    summary_repo(fx)
    fx.write_input(default_input(fx, target={"build_doc": EXPORT_DOC}))
    fx.manifest(notes="build_doc without slice; A and B both rejected with latest blocks "
                      "dated 2026-09-19")


def i2_05(fx):
    fx.checks = ["I2"]
    skeleton(fx)
    two_slice_doc(fx, "signed off", None)
    commit_pair(fx)
    fx.write_input(default_input(fx, target={"build_doc": EXPORT_DOC}))
    fx.manifest(notes="build_doc without slice; A rejected with a 2026-09-19 block, B signed "
                      "off with no block")


def i2_06(fx):
    fx.checks = ["I2"]
    summary_repo(fx)
    doc = default_input(fx, target={"build_doc": EXPORT_DOC})
    doc["invocation"] = invocation(fx, mode="headless", caller="ship-v2")
    fx.write_input(doc)
    fx.manifest(notes="I2-04's workspace and target under a headless station caller (ship-v2)")


def i2_07(fx):
    fx.checks = ["I2"]
    summary_repo(fx)
    doc = default_input(fx, target={"build_doc": EXPORT_DOC})
    doc["invocation"] = invocation(fx, mode="headless", caller="direct")
    fx.write_input(doc)
    fx.manifest(notes="I2-04's workspace and target under a direct headless invocation")


# ---- I4 cases ----------------------------------------------------------------------------

def i4_01(fx):
    fx.checks = ["I4"]
    default_repo(fx)
    fx.write_input(default_input(fx, workspace="workspace"))
    fx.manifest(input_validates=False,
                notes="workspace is the relative name 'workspace'; the schema's ^/ pattern "
                      "fails on it")


def i4_02(fx):
    fx.checks = ["I4"]
    default_repo(fx)
    doc = default_input(fx)
    doc["invocation"] = invocation(fx, run_dir=os.path.join(fx.workspace, ".recheck-run"))
    fx.write_input(doc)
    fx.manifest(notes="run_dir is <workspace>/.recheck-run, a path inside the workspace; "
                      "nothing exists there on disk")


def i4_03(fx):
    fx.checks = ["I4"]
    default_repo(fx)
    fx.write_input(default_input(fx, target={
        "build_doc": "docs/plans/../plans/%s-%s.md" % (DOC_DATE, TOPIC), "slice": "A"}))
    fx.manifest(input_validates=False,
                notes="build_doc holds a /../ segment; the schema's contained_relative_path "
                      "rejects it")


def i4_04(fx):
    fx.checks = ["I4"]
    skeleton(fx)
    default_doc(fx)
    text = fx.read(EXPORT_DOC)
    fx.remove(EXPORT_DOC)
    outside = os.path.join(fx.case_dir, "_outside", "%s-%s.md" % (DOC_DATE, TOPIC))
    os.makedirs(os.path.dirname(outside))
    with open(outside, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.chmod(outside, 0o644)
    link = os.path.join(fx.workspace, EXPORT_DOC)
    os.symlink("../../../_outside/%s-%s.md" % (DOC_DATE, TOPIC), link)
    commit_pair(fx)
    fx.write_input(default_input(fx))
    fx.manifest(notes="docs/plans build doc is a committed symlink to ../../../_outside/ "
                      "beside the workspace; the resolved file lies outside the workspace")


def i4_05(fx):
    fx.checks = ["I4"]
    default_repo(fx)
    fx.write_input(default_input(fx, target={"items": [dict(ITEM_EXPORT), dict(ITEM_EXPORT)]}))
    fx.manifest(notes="target.items holds two byte-identical elements sharing location and claim")


def i4_06(fx):
    fx.checks = ["I4"]
    default_repo(fx)
    item = dict(ITEM_EXPORT)
    item["claim"] = "CSV export writes unescaped commas · inside quoted fields"
    fx.write_input(default_input(fx, target={"items": [item]}))
    fx.manifest(input_validates=False,
                notes="target.items[0].claim contains the U+00B7 separator")


def i4_07(fx):
    fx.checks = ["I4"]
    default_repo(fx)
    item = dict(ITEM_EXPORT)
    item["claim"] = "CSV export writes unescaped commas\ninside quoted fields"
    fx.write_input(default_input(fx, target={"items": [item]}))
    fx.manifest(input_validates=False,
                notes="target.items[0].claim contains a line feed")


def i4_08(fx):
    fx.checks = ["I4"]
    default_repo(fx)
    doc = default_input(fx)
    doc["invocation"] = invocation(fx, mode="interactive", caller="ship-v2")
    fx.write_input(doc)
    fx.manifest(input_validates=False,
                notes="caller ship-v2 with mode interactive; the schema's else branch "
                      "requires headless for a non-direct caller")


def i4_09(fx):
    fx.checks = ["I4"]
    default_repo(fx)
    doc = default_input(fx, target={"items": [dict(ITEM_EXPORT), dict(ITEM_EXPORT)]})
    doc["invocation"] = invocation(fx, mode="headless", caller="ship-v2")
    fx.write_input(doc)
    fx.manifest(notes="I4-05's duplicate items under a headless station caller (ship-v2)")


def i4_10(fx):
    fx.checks = ["I4"]
    default_repo(fx)
    doc = default_input(fx)
    doc["invocation"] = invocation(fx, mode="headless", caller="ship-v2",
                                   run_dir=os.path.join(fx.workspace, ".recheck-run"))
    fx.write_input(doc)
    fx.manifest(notes="I4-02's run_dir inside the workspace under a headless station caller "
                      "(ship-v2)")


CASES = {
    "I2-01-two-build-docs": i2_01,
    "I2-02-named-item-none": i2_02,
    "I2-03-named-item-two": i2_03,
    "I2-04-multiple-candidate-slices": i2_04,
    "I2-05-single-candidate": i2_05,
    "I4-01-relative-workspace": i4_01,
    "I4-02-run-dir-inside-workspace": i4_02,
    "I4-03-build-doc-dotdot": i4_03,
    "I4-04-build-doc-symlink-escape": i4_04,
    "I4-05-duplicate-items": i4_05,
    "I4-06-claim-with-separator": i4_06,
    "I4-07-claim-with-newline": i4_07,
    "I4-08-station-caller-interactive": i4_08,
    "I2-06-headless-two-candidates": i2_06,
    "I2-07-direct-headless-two-candidates": i2_07,
    "I4-09-station-duplicate-items": i4_09,
    "I4-10-station-run-dir-inside-workspace": i4_10,
}


if __name__ == "__main__":
    fixturelib.make_lane(LANE, CASES)
