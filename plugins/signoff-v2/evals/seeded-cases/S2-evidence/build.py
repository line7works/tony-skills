#!/usr/bin/env python3
"""Generator for the S2-evidence family (E13 lane contract section 12, signoff core).

Standard library only, Python 3.9. Uses ../_lib/caselib.py and ../_lib/project.py; git runs only
inside the throwaway repositories the library creates under --out. See CASES.md for what each
case holds.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "_lib"))
sys.dont_write_bytecode = True

import caselib  # noqa: E402
import project as pj  # noqa: E402
from caselib import GIT_BASE_DATE, GIT_WORK_DATE, Case  # noqa: E402

FAMILY = "S2-evidence"
SLICE = "E"
BASE_MESSAGE = "signpost: rows joined inline"
WORK_MESSAGE = "Slice E: a joiner module and a padder module"

INTENT = (
    "Slice E moves the joining into `signpost.columns.join` and the padding into\n"
    "`signpost.pad.pad`, so a row is built from two named helpers instead of inline code."
)

SLICE_E = {
    "name": SLICE,
    "title": "A joiner module and a padder module",
    "status": "built",
    "intent": INTENT,
    "footprint": ["src/signpost/columns.py", "src/signpost/pad.py", "src/signpost/render.py",
                  "tests/test_columns.py"],
    "requirements": [
        "R1. `join` renders a field containing the column separator so that `count` of the "
        "joined row is 2.",
        "R2. The rendered name field is exactly `WIDTH` characters.",
    ],
    "checks": [
        "unit: %s" % pj.CHECK_UNIT_CMD,
        "field-widths: %s" % pj.CHECK_WIDTHS_CMD,
    ],
    "not_in_slice": ["checks/", "README.md"],
}


def base(case: Case) -> None:
    """The base commit: the project before Slice E, tagged `base`."""
    pj.base_files(case, columns=pj.COLUMNS_NOJOIN, render=pj.RENDER_INLINE_JOIN,
                  tests=pj.TESTS_COUNT)
    case.build_doc(pj.DOC, pj.DOC_TITLE, [SLICE_E])
    case.commit(BASE_MESSAGE, GIT_BASE_DATE)
    case.tag("base")


def work(case: Case, columns: str, pad: str, render: str, tests: str) -> None:
    case.write("src/signpost/columns.py", columns)
    case.write("src/signpost/pad.py", pad)
    case.write("src/signpost/render.py", render)
    case.write("tests/test_columns.py", tests)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)


def write_input(case: Case) -> None:
    case.write_input({
        "build_doc": pj.DOC,
        "slice": SLICE,
        "base": "base",
        "answer": "answer.json",
        "sessions": {"building": "sess-build-1", "reviewing": "sess-review-1"},
    })


def planted(case: Case) -> None:
    """The workspace shared by S2-02, S2-03 and S2-04."""
    base(case)
    work(case, pj.COLUMNS_BARE, pj.PAD_SHORT, pj.RENDER_PAD_COMPENSATED, pj.TESTS_BASE)
    write_input(case)


def s2_01(case: Case) -> None:
    base(case)
    work(case, pj.COLUMNS_ESCAPED, pj.PAD_EXACT, pj.RENDER_PAD_PLAIN, pj.TESTS_FULL)
    write_input(case)
    case.manifest(notes="join() escapes each field and count() walks the escape character; "
                        "pad() returns text.ljust(width) and render calls pad(name, WIDTH)")


def s2_02(case: Case) -> None:
    planted(case)
    case.manifest(notes="join() concatenates the fields with a bare separator; pad() returns "
                        "text.ljust(width - 1) and render calls pad(name, WIDTH + 1)")


def s2_03(case: Case) -> None:
    planted(case)
    case.manifest(notes="the workspace of S2-02; the recorded answer's one finding carries no "
                        "evidence kind")


def s2_04(case: Case) -> None:
    planted(case)
    case.manifest(notes="the workspace of S2-02; the recorded answer carries a second finding "
                        "located in src/signpost/__init__.py, which is unchanged since base")


CASES = {
    "S2-01-clean": s2_01,
    "S2-02-real-and-disproved": s2_02,
    "S2-03-no-evidence-kind": s2_03,
    "S2-04-location-outside-set": s2_04,
}


if __name__ == "__main__":
    caselib.make_family(FAMILY, CASES)
