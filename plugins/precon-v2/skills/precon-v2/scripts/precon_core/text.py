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
    readings(text)    every reading of a LINE's words: the frame's `answer.forms`, also of the text
                      without precon's own ` (waits on: <call>)` suffix
    row_readings(text)  every reading of a ledger ROW's words: the frame's `answer.row_forms`, also
                      of the row without that suffix

`without_waits` stays for one case the frame's parenthesis rule does not read: precon writes an
`Open:` item as `<text> (waits on: <call>)` with the call as the owner gave it, and a call holding
a parenthesis two deep, or an unbalanced one (`the bench call (see (Q2) first)`), is not stripped by
the frame, so the item's bare words would not meet the row (test_twins,
TheOwnSuffixTheFrameCannotRead). Every other decoration is the frame's to see through.
"""
import re
import unicodedata

from station_core import answer as shared

# precon's own suffix, as it writes it (and a trailing mark after it): everything from the
# ` (waits on:` to the last closing parenthesis
WAITS = re.compile(r"^(?P<text>.*?\S)\s*\(\s*waits on\s*:.*\)[\s.;,:!?]*$", re.IGNORECASE | re.DOTALL)


def invisible(char):
    return shared._visible(char) == ""


def _mark(char):
    return unicodedata.category(char) in ("Mn", "Me")


def blank(value):
    return not isinstance(value, str) or all(c.isspace() or invisible(c) or _mark(c) for c in value)


def one_line(value):
    return (not blank(value) and value.splitlines() == [value]
            and not any(invisible(c) for c in value))


def without_waits(text):
    """The text before precon's trailing ` (waits on: <call>)`, or the text itself."""
    match = WAITS.match(shared._visible(text))
    return match.group("text") if match else text


def readings(text):
    if not isinstance(text, str):
        return set()
    return shared.forms(text) | shared.forms(without_waits(text))


def row_readings(text):
    if not isinstance(text, str):
        return set()
    return shared.row_forms(text) | shared.row_forms(without_waits(text))
