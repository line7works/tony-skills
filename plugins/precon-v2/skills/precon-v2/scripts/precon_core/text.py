"""One reading of a value precon-v2 checks, writes and compares (lane contract section 5).

The refusals (`rules.py`) and the plan of every write (`scopedoc.py`) call the same functions, so
what the answer's check accepts is exactly what the documents can carry and read back:

    blank(value)      not a string, or nothing a reader can see: whitespace, format characters
                      (Unicode category Cf: a zero-width space, a byte-order mark, a word joiner),
                      the invisible letters (the Hangul fillers, the blank Braille pattern) and
                      combining marks with nothing to sit on (categories Mn and Me)
    one_line(value)   not blank, broken nowhere a line reader breaks a line (`str.splitlines`: the
                      line feed and carriage return, VT, FF, the file, group and record separators,
                      NEL, U+2028, U+2029), and holding no format character or invisible letter
    normalized(text)  invisibles dropped, whitespace collapsed, case folded
    readings(text)    every form of a text the twin rule compares: the whole text, the text with a
                      trailing ` (waits on: <call>)` removed, and (unless `fields=False`) each whole
                      field of a middle-dot or dashed line, bare of that suffix too. The rule reads
                      an asserted line with its fields and a ledger row or another line of the same
                      answer without, so two lines that only share a field are never twins
"""
import re
import unicodedata

FILLERS = frozenset(u"\u115f\u1160\u3164\uffa0\u2800")
WAITS = re.compile(r"^(?P<text>.*?\S)\s*\(\s*waits on\s*:.*\)\s*$", re.IGNORECASE | re.DOTALL)
FIELDS = re.compile(u"\\s+(?:\u00b7|\u2014|\u2013|--)\\s+")


def invisible(char):
    return unicodedata.category(char) == "Cf" or char in FILLERS


def _mark(char):
    return unicodedata.category(char) in ("Mn", "Me")


def blank(value):
    return not isinstance(value, str) or all(c.isspace() or invisible(c) or _mark(c) for c in value)


def one_line(value):
    return (not blank(value) and value.splitlines() == [value]
            and not any(invisible(c) for c in value))


def normalized(text):
    return " ".join("".join(c for c in text if not invisible(c)).split()).casefold()


def without_waits(text):
    """The text before a trailing ` (waits on: <call>)`, or the text itself."""
    match = WAITS.match(text)
    return match.group("text") if match else text


def readings(text, fields=True):
    out = set()
    text = "".join(c for c in text if not invisible(c))
    parts = FIELDS.split(text) if fields else []
    for part in [text] + (parts if len(parts) > 1 else []):
        for form in (part, without_waits(part)):
            norm = normalized(form)
            if norm:
                out.add(norm)
    return out
