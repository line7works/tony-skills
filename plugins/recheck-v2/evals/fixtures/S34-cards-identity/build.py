#!/usr/bin/env python3
"""Generator for lane S34-cards-identity (E7). Specification: CASES.md beside this file.

Standard library only; git runs only inside the throwaway repositories the shared library
creates under --out. Locates _lib relative to this file so it works from any directory.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "_lib"))

import fixturelib  # noqa: E402
from fixturelib import EMPTY_SHA256, GIT_BASE_DATE, GIT_FIX_DATE, Fixture  # noqa: E402

LANE = "S34-cards-identity"
TOPIC = "widget-export"
DOC_DATE = "2026-09-18"
BUILD_DOC = "docs/plans/%s-%s.md" % (DOC_DATE, TOPIC)
REVIEW_DATE = "2026-09-19"

PROSE = (
    "Slice A writes widget rows to CSV through the widget.export command line. The header "
    "row is constant; each data row is the title and the quantity."
)

COMMA_FINDING = {
    "severity": "BLOCKER",
    "file": "src/widget/export.py",
    "line": 11,
    "claim": "a title containing a comma is written unquoted",
    "scenario": 'run PYTHONPATH=src python3 -m widget.export --title "Widget, large" --qty 3; '
                "the data row splits into three columns against a two-column header",
    "found_by": "Slice A",
}
NONE_FINDING = {
    "severity": "BLOCKER",
    "file": "src/widget/export.py",
    "line": 7,
    "claim": "a missing title exports as the string None",
    "scenario": "run PYTHONPATH=src python3 -m widget.export --qty 3; the title cell of the "
                "data row reads None instead of an empty field",
    "found_by": "Slice A",
}

EXPORT_HEAD = '"""CSV export for widget rows."""\n\nimport argparse\n\n\n'

FORMAT_TITLE_BASE = (
    "def format_title(title):\n"
    "    return \"\" if title is None else str(title)\n"
)
FORMAT_TITLE_STR = (
    "def format_title(title):\n"
    "    return str(title)\n"
)
FORMAT_TITLE_FIX = (
    "def format_title(title):\n"
    "    text = \"\" if title is None else str(title)\n"
    "    if \",\" in text or '\"' in text:\n"
    "        text = '\"' + text.replace('\"', '\"\"') + '\"'\n"
    "    return text\n"
)

EXPORT_TAIL = (
    "\n\n"
    "def format_row(title, qty):\n"
    "    return \"{},{}\".format(format_title(title), qty)\n"
    "\n\n"
    "def to_csv(title, qty):\n"
    "    return \"title,qty\\n\" + format_row(title, qty) + \"\\n\"\n"
    "\n\n"
    "def main(argv=None):\n"
    "    parser = argparse.ArgumentParser(prog=\"widget.export\")\n"
    "    parser.add_argument(\"--title\", default=None, help=\"row title\")\n"
    "    parser.add_argument(\"--qty\", type=int, required=True, help=\"row quantity\")\n"
    "    args = parser.parse_args(argv)\n"
    "    print(to_csv(args.title, args.qty), end=\"\")\n"
    "    return 0\n"
    "\n\n"
    "if __name__ == \"__main__\":\n"
    "    raise SystemExit(main())\n"
)

PNG_SIGNATURE = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def export_source(format_title_text):
    return EXPORT_HEAD + format_title_text + EXPORT_TAIL


def write_base(fx, format_title_text=FORMAT_TITLE_BASE, findings=None):
    """The shared base state: five files, build doc with one review block, nothing committed."""
    fx.write("README.md", "# widget\n")
    fx.write(".gitignore", "__pycache__/\n*.pyc\n.venv/\n")
    fx.write_bytes("src/widget/__init__.py", b"")
    fx.write("src/widget/export.py", export_source(format_title_text))
    doc = fx.build_doc(TOPIC, DOC_DATE, "Widget export",
                       [{"name": "A", "title": "CSV export", "status": "rejected"}],
                       prose={"A": PROSE})
    fx.review_block(doc, REVIEW_DATE, "A", findings or [COMMA_FINDING])
    return doc


def base_and_fix(fx):
    """The shared two commits; returns the fix commit hash."""
    write_base(fx)
    fx.commit("Slice A review state", GIT_BASE_DATE)
    fx.write("src/widget/export.py", export_source(FORMAT_TITLE_FIX))
    return fx.commit("quote titles that hold a comma", GIT_FIX_DATE)


def default_input(fx, pin=None):
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
    }
    if pin is not None:
        doc["source_identity"] = pin
    doc["target"] = {"build_doc": BUILD_DOC, "slice": "A"}
    fx.write_input(doc)


def clean_pin(commit):
    return {
        "commit": commit,
        "dirty": False,
        "tracked_diff_sha256": EMPTY_SHA256,
        "untracked": [],
        "untracked_sha256": EMPTY_SHA256,
        "submodules": [],
    }


# ---- cases --------------------------------------------------------------------------------

def s3_01_built_card(fx):
    fx.checks = ["S3"]
    doc = write_base(fx, FORMAT_TITLE_STR, [COMMA_FINDING, NONE_FINDING])
    fx.commit("Slice A review state", GIT_BASE_DATE)
    fx.write("src/widget/export.py", export_source(FORMAT_TITLE_FIX))
    fx.set_status(doc, "A", "built")
    fx.commit("rebuild Slice A: quote commas, blank missing titles", GIT_FIX_DATE)
    default_input(fx)
    fx.manifest(notes="slice A card reads built at HEAD; two BLOCKER review lines; clean tree")


def s4_01_staged_change(fx):
    fx.checks = ["S4"]
    fix = base_and_fix(fx)
    pin = fx.identity()
    assert pin == clean_pin(fix), pin
    fx.write("README.md", "# widget\n\nExports rows as CSV.\n")
    fx.stage("README.md")
    default_input(fx, pin)
    fx.manifest(notes="pin is the clean fix commit; README.md edit staged, not committed")


def s4_02_binary_change(fx):
    fx.checks = ["S4"]
    logo = PNG_SIGNATURE + bytes(range(256))
    write_base(fx)
    fx.write_bytes("assets/logo.png", logo)
    fx.commit("Slice A review state", GIT_BASE_DATE)
    fx.write("src/widget/export.py", export_source(FORMAT_TITLE_FIX))
    fix = fx.commit("quote titles that hold a comma", GIT_FIX_DATE)
    pin = fx.identity()
    assert pin == clean_pin(fix), pin
    fx.write_bytes("assets/logo.png", logo[:-8] + b"\xff" * 8)
    default_input(fx, pin)
    fx.manifest(notes="pin is the clean fix commit; assets/logo.png last 8 bytes changed, unstaged")


def s4_03_untracked_content_change(fx):
    fx.checks = ["S4"]
    base_and_fix(fx)
    fx.untracked("notes.txt", "pin content\n")
    pin = fx.identity()
    fx.untracked("notes.txt", "later content\n")
    default_input(fx, pin)
    fx.manifest(notes="pin computed with notes.txt holding pin content; file now holds later content")


def s4_04_submodule(fx):
    fx.checks = ["S4"]
    base_and_fix(fx)
    fx.add_submodule("theme")
    default_input(fx)
    fx.manifest(notes="initialized submodule theme at a third commit; no pin (schema allows no submodule paths)")


def s4_05_clean_match(fx):
    fx.checks = ["S4"]
    fix = base_and_fix(fx)
    pin = fx.identity()
    assert pin == clean_pin(fix), pin
    default_input(fx, pin)
    fx.manifest(notes="pin equals the workspace identity as built; clean fix commit")


CASES = {
    "S3-01-built-card": s3_01_built_card,
    "S4-01-staged-change": s4_01_staged_change,
    "S4-02-binary-change": s4_02_binary_change,
    "S4-03-untracked-content-change": s4_03_untracked_content_change,
    "S4-04-submodule": s4_04_submodule,
    "S4-05-clean-match": s4_05_clean_match,
}


if __name__ == "__main__":
    fixturelib.make_lane(LANE, CASES)
