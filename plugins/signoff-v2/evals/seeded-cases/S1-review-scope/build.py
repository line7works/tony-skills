#!/usr/bin/env python3
"""Generator for the S1-review-scope family (E13 lane contract section 12, signoff core).

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

FAMILY = "S1-review-scope"
SLICE = "D"
BASE_MESSAGE = "signpost: rows and the escaping joiner"
WORK_MESSAGE = "Slice D: pad the name field through signpost.pad"

INTENT = (
    "Slice D moves the name padding out of `render.row` into `signpost.pad`, so the rendered\n"
    "name field is exactly WIDTH characters wherever a row is built."
)

SLICE_D = {
    "name": SLICE,
    "title": "Pad the name field through signpost.pad",
    "status": "built",
    "intent": INTENT,
    "footprint": ["src/signpost/pad.py", "src/signpost/render.py"],
    "requirements": [
        "R1. `pad(text, width)` returns a string of exactly `width` characters for any text "
        "shorter than `width`.",
        "R2. `render.row` builds the name field through `pad` and the rendered name field is "
        "exactly `WIDTH` characters.",
    ],
    "checks": [
        "unit: %s" % pj.CHECK_UNIT_CMD,
        "field-widths: %s" % pj.CHECK_WIDTHS_CMD,
    ],
    "not_in_slice": ["src/signpost/columns.py"],
}


def base(case: Case) -> None:
    """The base commit: the project before Slice D, tagged `base`."""
    pj.base_files(case, columns=pj.COLUMNS_ESCAPED, render=pj.RENDER_INLINE,
                  tests=pj.TESTS_FULL)
    case.build_doc(pj.DOC, pj.DOC_TITLE, [SLICE_D])
    case.commit(BASE_MESSAGE, GIT_BASE_DATE)
    case.tag("base")


def write_input(case: Case, report_only: bool = False, building: str = "sess-build-1",
                reviewing: str = "sess-review-1") -> None:
    case.write_input({
        "build_doc": pj.DOC,
        "slice": SLICE,
        "base": "base",
        "answer": "answer.json",
        "report_only": report_only,
        "sessions": {"building": building, "reviewing": reviewing},
    })


def s1_01(case: Case) -> None:
    base(case)
    case.write("src/signpost/pad.py", pj.PAD_EXACT)
    case.write("src/signpost/render.py", pj.RENDER_PAD_PLAIN)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)
    write_input(case)
    case.manifest(notes="pad() returns text.ljust(width); the rendered name field measures 12 "
                        "characters and both named checks return 0")


def s1_02(case: Case) -> None:
    base(case)
    case.write("src/signpost/render.py", pj.RENDER_PAD_PLAIN)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)
    case.write("src/signpost/pad.py", pj.PAD_SHORT)
    write_input(case)
    case.manifest(notes="src/signpost/pad.py is in the work tree and never committed; "
                        ".gitignore does not match it. pad() returns text.ljust(width - 1)")


def s1_03(case: Case) -> None:
    base(case)
    case.write("src/signpost/pad.py", pj.PAD_SHORT)
    case.write("src/signpost/render.py", pj.RENDER_PAD_PLAIN)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)
    write_input(case)
    case.manifest(notes="both files are committed and the work tree is clean, so `git diff` "
                        "against HEAD prints nothing. pad() returns text.ljust(width - 1)")


def s1_04(case: Case) -> None:
    base(case)
    case.write("src/signpost/render.py", pj.RENDER_PAD_PLAIN)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)
    case.write("src/signpost/pad.py", pj.PAD_SHORT)
    case.write("build/cache.py", pj.BUILD_CACHE)
    write_input(case)
    case.manifest(notes="as S1-02 plus build/cache.py, which .gitignore matches through its "
                        "`build/` line; cached_pad() returns text.ljust(width - 1) too")


def s1_05(case: Case) -> None:
    base(case)
    case.write("src/signpost/pad.py", pj.PAD_SHORT)
    case.write("src/signpost/render.py", pj.RENDER_PAD_PLAIN)
    case.commit(WORK_MESSAGE, GIT_WORK_DATE)
    write_input(case, report_only=True)
    case.manifest(notes="the workspace of S1-03 with `report_only` true in the input")


CASES = {
    "S1-01-clean": s1_01,
    "S1-02-untracked-defect": s1_02,
    "S1-03-committed-hidden": s1_03,
    "S1-04-ignored-excluded": s1_04,
    "S1-05-report-only": s1_05,
}


if __name__ == "__main__":
    caselib.make_family(FAMILY, CASES)
