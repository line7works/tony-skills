#!/usr/bin/env python3
"""Generator for the B1-scope-adherence family (E13 lane contract section 12, build core).

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

FAMILY = "B1-scope-adherence"
SLICE = "B"
BASE_MESSAGE = "signpost: rows, padding and the column joiner"
WORK_MESSAGE = "Slice B: escape the column separator"

INTENT = (
    "Slice B makes `signpost.render.row` render a marker name that contains the column\n"
    "separator as one field, so `columns.count` of the rendered row is still 2."
)

SLICE_B = {
    "name": SLICE,
    "title": "Escape the column separator in rendered rows",
    "status": "not started",
    "intent": INTENT,
    "footprint": ["src/signpost/render.py"],
    "requirements": [
        "R1. `row(name, miles)` renders a name containing the column separator so that "
        "`columns.count` of the rendered row is 2.",
    ],
    "checks": ["unit: %s" % pj.CHECK_UNIT_CMD],
    "not_in_slice": ["src/signpost/columns.py", "src/signpost/pad.py"],
}


def base(case: Case) -> None:
    """The base commit: the project before Slice B, tagged `base`."""
    pj.base_files(case, columns=pj.COLUMNS_BARE_JOIN, render=pj.RENDER_PAD_PLAIN,
                  tests=pj.TESTS_BASE, pad=pj.PAD_EXACT)
    case.build_doc(pj.DOC, pj.DOC_TITLE, [SLICE_B])
    case.commit(BASE_MESSAGE, GIT_BASE_DATE)
    case.tag("base")


def write_input(case: Case) -> None:
    case.write_input({
        "build_doc": pj.DOC,
        "slice": SLICE,
        "base": "base",
        "answer": "answer.json",
    })


def b1_01(case: Case) -> None:
    base(case)
    case.write("src/signpost/render.py", pj.RENDER_PAD_ESCAPING)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)
    write_input(case)
    case.manifest(notes="the separator escape lands in src/signpost/render.py; the work tree "
                        "is clean and no file outside the footprint carries a change")


def b1_02(case: Case) -> None:
    base(case)
    case.write("src/signpost/render.py", pj.RENDER_PAD_ESCAPING)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)
    case.write("src/signpost/escapes.py", pj.ESCAPES_HELPER)
    write_input(case)
    case.manifest(notes="as B1-01 plus src/signpost/escapes.py, written into the work tree and "
                        "never committed; .gitignore does not match it")


def b1_03(case: Case) -> None:
    base(case)
    case.write("src/signpost/columns.py", pj.COLUMNS_ESCAPED)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)
    write_input(case)
    case.manifest(notes="the escape lands in src/signpost/columns.py, which the slice lists "
                        "under Not in this slice; src/signpost/render.py is unchanged since base")


def b1_04(case: Case) -> None:
    base(case)
    case.write("src/signpost/render.py", pj.RENDER_PAD_ESCAPING)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)
    case.write("src/signpost/pad.py", pj.PAD_SHORT)
    write_input(case)
    case.manifest(notes="as B1-01 plus an uncommitted edit to src/signpost/pad.py, which the "
                        "slice lists under Not in this slice")


CASES = {
    "B1-01-clean": b1_01,
    "B1-02-untracked-outside": b1_02,
    "B1-03-committed-outside": b1_03,
    "B1-04-changed-outside": b1_04,
}


if __name__ == "__main__":
    caselib.make_family(FAMILY, CASES)
