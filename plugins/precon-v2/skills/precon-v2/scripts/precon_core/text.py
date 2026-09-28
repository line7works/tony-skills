"""What precon-v2 alone needs to read a value it checks, writes and compares (lane contract section 5).

precon-v2 has no normalizer of its own (E14-3: nothing shared is reinvented in a lane). Its word
readings are the frame's (`station_core/answer.py`), and its notion of an invisible character is
the frame's too; what stays here is what precon alone needs:

    invisible(char)   true exactly when the frame's `answer._visible(char)` drops the character
                      (format characters, line and paragraph separators, the controls other than
                      tab, line feed and carriage return, the variation selectors, the letter-shaped
                      fillers, U+034F): one invisible set, the frame's
    blank(value)      not a string, or nothing a reader can see: whitespace, invisibles, and
                      combining marks with nothing to sit on (categories Mn and Me)
    one_line(value)   not blank, broken nowhere a line reader breaks a line (`str.splitlines`: the
                      line feed and carriage return, VT, FF, the file, group and record separators,
                      NEL, U+2028, U+2029), and holding no invisible character: a value the scope
                      doc can carry and read back as the words it was given
    one_deep(value)   every opening bracket (Unicode category Ps) closed in order by a closer (Pe),
                      none nested inside another: the call precon writes in its ` (waits on: <call>)`
                      suffix, so every suffix it writes is one the frame's parenthesis reading strips
                      (CP4-3; `record-answer` refuses any other call `unrenderable`)
    readings(text)    every reading of a LINE's words: the frame's `answer.forms`
    row_readings(text)  every reading of a ledger ROW's words: the frame's `answer.row_forms`

precon reads no suffix of its own: an `Open:` item it wrote is read by the frame's readings alone.
"""
import unicodedata

from station_core import answer as shared


def invisible(char):
    return shared._visible(char) == ""


def _mark(char):
    return unicodedata.category(char) in ("Mn", "Me")


def blank(value):
    return not isinstance(value, str) or all(c.isspace() or invisible(c) or _mark(c) for c in value)


def one_line(value):
    return (not blank(value) and value.splitlines() == [value]
            and not any(invisible(c) for c in value))


def one_deep(value):
    depth = 0
    for char in value if isinstance(value, str) else "":
        category = unicodedata.category(char)
        if category == "Ps":
            depth += 1
            if depth > 1:
                return False
        elif category == "Pe":
            depth -= 1
            if depth < 0:
                return False
    return isinstance(value, str) and depth == 0


def readings(text):
    if not isinstance(text, str):
        return set()
    return shared.forms(text)


def row_readings(text):
    if not isinstance(text, str):
        return set()
    return shared.row_forms(text)
