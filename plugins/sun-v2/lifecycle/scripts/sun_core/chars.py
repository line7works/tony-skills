"""The characters the owner's two rulings bar, named once (A142, PS46; PS47).

One core serves both rulings, as the frame's author named it for both questions (A142, batch 62B): a control
character (Unicode's category Cc), a format character (category Cf: among them the zero-width marks, U+200B to
U+200D, U+2060 and U+FEFF, and the direction marks, U+200E, U+200F, U+061C, U+202A to U+202E and U+2066 to
U+2069), and a line break of any kind, the line and paragraph separators U+2028 and U+2029 among them (every
character at which `str.splitlines` breaks a line).

- A secret's alphabet (PS46, A142): "A declaration whose secret field's registered alphabet admits any white space,
  any control character or any format character fails its manifest build, and the row is named." White space is
  every character `str.isspace` holds as such, the space, the tab and the no-break space among them. The check is
  `rows._command_findings`'s; `alphabet_admits_barred` decides it.
- A project's name (PS47): "a name with no letter or digit, or one that starts with a hyphen; and a name holding a
  backslash, a control character, any line break or an invisible mark ... Spaces stay allowed." The check is RUN-2's
  part (a), `startup.name_form_refused`; `barred_in_a_name` decides the characters of it.

The categories are those of the Unicode database of the Python that runs the tool (`unicodedata.unidata_version`).
"""
import re
import sys
import unicodedata

LINE_BREAKS = frozenset("\n\r\x0b\x0c\x1c\x1d\x1e\x85  ")    # where `str.splitlines` breaks a line
BACKSLASH = "\\"


def in_core(ch):
    """A control character, a format character, or a line break (the one core of A142 and PS47)."""
    return ch in LINE_BREAKS or unicodedata.category(ch) in ("Cc", "Cf")


def barred_in_a_secret(ch):
    """A character a secret field's alphabet may not admit (A142): the core, and every white space."""
    return in_core(ch) or ch.isspace()


def barred_in_a_name(ch):
    """A character a project's name may not hold (PS47): the core, and the backslash. A space is allowed."""
    return in_core(ch) or ch == BACKSLASH


_SECRET_BARRED = []


def _secret_barred():
    """Every character `barred_in_a_secret` holds, made once in a process, by a pass over every code point."""
    if not _SECRET_BARRED:
        _SECRET_BARRED.extend(chr(c) for c in range(sys.maxunicode + 1) if barred_in_a_secret(chr(c)))
    return _SECRET_BARRED


def alphabet_admits_barred(alphabet):
    """Whether a registered alphabet admits a character barred from a secret (A142).

    An alphabet is written as a declaration writes it: the inside of one character class, which the field's validator
    reads as `^[<alphabet>]+$` (`results._valid`). It admits a character where that class, `[<alphabet>]`, matches the
    character alone. The alphabet admits a barred character where it admits any one of the characters
    `barred_in_a_secret` holds, each tried in turn: the set is finite, so the answer is exact for the class as the
    validator reads it, whatever ranges, escapes or negation the class is written with. An alphabet that cannot be read
    as a class at all is not proven to admit none, and counts as admitting one (GOV-1)."""
    if not isinstance(alphabet, str):
        return True
    try:
        pattern = re.compile("[%s]" % alphabet)
    except (re.error, OverflowError, RecursionError):
        return True
    return any(pattern.fullmatch(ch) for ch in _secret_barred())
