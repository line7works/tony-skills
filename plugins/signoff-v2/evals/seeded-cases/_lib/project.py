"""The synthetic project every seeded-case family builds its workspace from.

`signpost` renders trail markers as fixed-width text rows. Everything here is written for these
cases: no text is copied from another repository, and nothing personal, legal or financial
appears in it. Standard library only, Python 3.9.

Module map:
  src/signpost/columns.py   joins marker fields with the column separator "|"
  src/signpost/pad.py       pads the name field to a fixed width
  src/signpost/render.py    renders one marker and prints its column count
  tests/test_columns.py     unittest cases over columns.join / columns.count
  checks/unit.sh            the named check "unit"
  checks/field-widths.sh    the named check "field-widths"
"""

DOC = "docs/plans/2026-09-18-signpost-rows.md"
DOC_TITLE = "Signpost rows"

README = """# signpost

Renders trail markers as fixed-width text rows.

Run: PYTHONPATH=src /usr/bin/python3 -m signpost.render NAME MILES
"""

GITIGNORE = """__pycache__/
*.pyc
build/
"""

INIT = '"""signpost: fixed-width trail marker rows."""\n'

# ---- columns.py ---------------------------------------------------------------------------

COLUMNS_BARE = '''"""Join marker fields into one row."""

SEP = "|"
ESC = "\\\\"


def join(fields):
    """Join the fields of one marker with the column separator."""
    return SEP.join(str(f) for f in fields)


def count(row):
    """Count the fields of one rendered row."""
    return len(row.split(SEP))
'''

# join() concatenates bare; count() already walks the escape character, so a caller that
# escapes its own field before joining is enough to make a row count two fields.
COLUMNS_BARE_JOIN = '''"""Join marker fields into one row."""

SEP = "|"
ESC = "\\\\"


def join(fields):
    """Join the fields of one marker with the column separator."""
    return SEP.join(str(f) for f in fields)


def count(row):
    """Count the fields of one rendered row."""
    fields = 1
    i = 0
    while i < len(row):
        if row[i] == ESC:
            i += 2
            continue
        if row[i] == SEP:
            fields += 1
        i += 1
    return fields
'''

# The module before any slice introduces join(): constants and the naive field count only.
COLUMNS_NOJOIN = '''"""Column constants for marker rows."""

SEP = "|"
ESC = "\\\\"


def count(row):
    """Count the fields of one rendered row."""
    return len(row.split(SEP))
'''

COLUMNS_ESCAPED = '''"""Join marker fields into one row."""

SEP = "|"
ESC = "\\\\"


def escape(field):
    """Protect the separator and the escape character inside one field."""
    return str(field).replace(ESC, ESC + ESC).replace(SEP, ESC + SEP)


def join(fields):
    """Join the fields of one marker with the column separator."""
    return SEP.join(escape(f) for f in fields)


def count(row):
    """Count the fields of one rendered row."""
    fields = 1
    i = 0
    while i < len(row):
        if row[i] == ESC:
            i += 2
            continue
        if row[i] == SEP:
            fields += 1
        i += 1
    return fields
'''

COLUMNS_ESCAPED_WEAK = '''"""Join marker fields into one row."""

SEP = "|"
ESC = "\\\\"


def escape(field):
    """Protect the separator inside one field."""
    return str(field).replace(SEP, ESC + SEP)


def join(fields):
    """Join the fields of one marker with the column separator."""
    return SEP.join(escape(f) for f in fields)


def count(row):
    """Count the fields of one rendered row."""
    fields = 1
    i = 0
    while i < len(row):
        if row[i] == ESC:
            i += 2
            continue
        if row[i] == SEP:
            fields += 1
        i += 1
    return fields
'''

# ---- pad.py -------------------------------------------------------------------------------

PAD_SHORT = '''"""Pad a marker field to a fixed width."""


def pad(text, width):
    """Right-pad text with spaces, leaving one column for the rule."""
    return text.ljust(width - 1)
'''

PAD_EXACT = '''"""Pad a marker field to a fixed width."""


def pad(text, width):
    """Right-pad text with spaces to exactly width characters."""
    return text.ljust(width)
'''

# ---- render.py ----------------------------------------------------------------------------

_RENDER = '''"""Render one trail marker row."""

import sys

%(imports)s

WIDTH = 12


def row(name, miles):
    """Render one marker as a padded, separated row."""
    return join([%(name_expr)s, miles])


def main(argv):
    if len(argv) < 2:
        print("usage: render.py NAME MILES", file=sys.stderr)
        return 2
    text = row(argv[0], int(argv[1]))
    print(text)
    print("columns=%%d" %% count(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

_IMPORT_COLUMNS = "from signpost.columns import count, join"
_IMPORT_COLUMNS_ESC = "from signpost.columns import ESC, SEP, count, join"
_IMPORT_PAD = "from signpost.pad import pad"

# Pads inline; no pad module involved.
RENDER_INLINE = _RENDER % {"imports": _IMPORT_COLUMNS, "name_expr": "name.ljust(WIDTH)"}

# Calls pad with WIDTH + 1, so a pad that subtracts one still yields exactly WIDTH characters.
RENDER_PAD_COMPENSATED = _RENDER % {
    "imports": _IMPORT_COLUMNS + "\n" + _IMPORT_PAD,
    "name_expr": "pad(name, WIDTH + 1)",
}

# Calls pad with WIDTH, so a pad that subtracts one yields WIDTH - 1 characters.
RENDER_PAD_PLAIN = _RENDER % {
    "imports": _IMPORT_COLUMNS + "\n" + _IMPORT_PAD,
    "name_expr": "pad(name, WIDTH)",
}

# Escapes the separator inside the name before padding and joining.
RENDER_PAD_ESCAPING = _RENDER % {
    "imports": _IMPORT_COLUMNS_ESC + "\n" + _IMPORT_PAD,
    "name_expr": "pad(name.replace(SEP, ESC + SEP), WIDTH)",
}

# Joins inline with the separator; used before a slice introduces columns.join().
RENDER_INLINE_JOIN = '''"""Render one trail marker row."""

import sys

from signpost.columns import SEP, count

WIDTH = 12


def row(name, miles):
    """Render one marker as a padded, separated row."""
    return SEP.join([name.ljust(WIDTH), str(miles)])


def main(argv):
    if len(argv) < 2:
        print("usage: render.py NAME MILES", file=sys.stderr)
        return 2
    text = row(argv[0], int(argv[1]))
    print(text)
    print("columns=%d" % count(text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

# ---- an untracked helper a slice's footprint does not name ---------------------------------

ESCAPES_HELPER = '''"""Separator escaping helpers."""

from signpost.columns import ESC, SEP


def protect(field):
    """Return the field with every separator escaped."""
    return str(field).replace(SEP, ESC + SEP)
'''

# ---- an ignored artifact -------------------------------------------------------------------

BUILD_CACHE = '''"""A generated render cache. Rebuilt by the packaging step."""


def cached_pad(text, width):
    return text.ljust(width - 1)
'''

# ---- tests --------------------------------------------------------------------------------

TESTS_BASE = '''"""Tests for signpost.columns."""

import unittest

from signpost.columns import count, join


class JoinTest(unittest.TestCase):

    def test_plain_fields_join(self):
        self.assertEqual(join(["Fork Ridge", 4]), "Fork Ridge|4")

    def test_plain_row_counts_two(self):
        self.assertEqual(count(join(["Fork Ridge", 4])), 2)


if __name__ == "__main__":
    unittest.main()
'''

# Exercises count() only; written before a slice introduces join().
TESTS_COUNT = '''"""Tests for signpost.columns."""

import unittest

from signpost.columns import count


class CountTest(unittest.TestCase):

    def test_one_separator_counts_two(self):
        self.assertEqual(count("Fork Ridge  |4"), 2)

    def test_no_separator_counts_one(self):
        self.assertEqual(count("Fork Ridge"), 1)


if __name__ == "__main__":
    unittest.main()
'''

TESTS_FULL = '''"""Tests for signpost.columns."""

import unittest

from signpost.columns import count, join


class JoinTest(unittest.TestCase):

    def test_plain_fields_join(self):
        self.assertEqual(join(["Fork Ridge", 4]), "Fork Ridge|4")

    def test_plain_row_counts_two(self):
        self.assertEqual(count(join(["Fork Ridge", 4])), 2)

    def test_separator_in_name_counts_two(self):
        self.assertEqual(count(join(["Fork|Ridge", 4])), 2)

    def test_escape_in_name_counts_two(self):
        self.assertEqual(count(join(["Fork\\\\", 4])), 2)


if __name__ == "__main__":
    unittest.main()
'''

# ---- check scripts -------------------------------------------------------------------------

CHECK_UNIT = '''#!/bin/sh
# The named check "unit": the project's unittest cases.
cd "$(dirname "$0")/.."
PYTHONPATH=src exec /usr/bin/python3 -m unittest discover -s tests -q
'''

CHECK_WIDTHS_RUNS = '''#!/bin/sh
# The named check "field-widths": the rendered name field is exactly WIDTH characters.
cd "$(dirname "$0")/.."
PYTHONPATH=src exec /usr/bin/python3 -c '
from signpost.render import WIDTH, row
name = row("Fork Ridge", 4).split("|")[0]
if len(name) != WIDTH:
    raise SystemExit("field-widths: name field is %d characters, not %d" % (len(name), WIDTH))
print("field-widths: name field is %d characters" % len(name))
'
'''

CHECK_WIDTHS_BLOCKED = '''#!/bin/sh
# The named check "field-widths": compares rendered rows against the sample markers.
# The sample markers live in the directory SIGNPOST_FIXTURE_DIR names.
if [ -z "${SIGNPOST_FIXTURE_DIR}" ]; then
  echo "field-widths: SIGNPOST_FIXTURE_DIR is unset, the sample markers are not on this machine; check not run" >&2
  exit 127
fi
cd "$(dirname "$0")/.."
PYTHONPATH=src exec /usr/bin/python3 -c '
import os
from signpost.render import WIDTH, row
samples = os.path.join(os.environ["SIGNPOST_FIXTURE_DIR"], "markers.txt")
with open(samples) as fh:
    for line in fh:
        name = row(line.strip(), 4).split("|")[0]
        if len(name) != WIDTH:
            raise SystemExit("field-widths: %r renders %d characters" % (line.strip(), len(name)))
print("field-widths: every sample marker renders %d characters" % WIDTH)
'
'''

CHECK_UNIT_CMD = "sh checks/unit.sh"
CHECK_WIDTHS_CMD = "sh checks/field-widths.sh"


def base_files(case, columns=COLUMNS_BARE, render=RENDER_INLINE, tests=TESTS_BASE,
               pad=None, widths=CHECK_WIDTHS_RUNS):
    """Write the project's files into the case workspace, before any commit."""
    case.write("README.md", README)
    case.write(".gitignore", GITIGNORE)
    case.write("src/signpost/__init__.py", INIT)
    case.write("src/signpost/columns.py", columns)
    case.write("src/signpost/render.py", render)
    if pad is not None:
        case.write("src/signpost/pad.py", pad)
    case.write("tests/test_columns.py", tests)
    case.write("checks/unit.sh", CHECK_UNIT, executable=True)
    case.write("checks/field-widths.sh", widths, executable=True)
