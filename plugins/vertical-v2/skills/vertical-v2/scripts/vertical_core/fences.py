"""vertical-v2's one reading rule for the build doc: strict plain code blocks (the E15 lane contract A8; C1A4-1),
no raw HTML lines (A9; C1A5-1, C1A5-2), exact labels (A10; C1A6-1), plain structure only (A12; C1A7-1), a
character allowlist (A16; C1A9-1), and a stray `Status:` line and a label's leading marks (A18; C1A11-1, C1A11-3);
contract section 5, "The fence rule", "No raw HTML lines", "Exact labels", "Plain structure" and "The character
list".

    split_lines(text) -> [line with its ending]: CommonMark's line endings only (LF, CRLF, CR)
    bare(line, number) -> the line without its ending (and, on line 1, without a byte order mark)
    fence_line(line) -> True when the line is a fence line (below)
    html_line(line) -> True when the line is a raw HTML line (below)
    scan(lines) -> Scan: `fenced`, the 1-based numbers of every line an accepted fence holds (its opening and
        closing lines included); `problems`, [(line number, what)] for every fence line the rule does not
        accept and every raw HTML line, in line order
    plain_problem(line) -> the words of the plain-structure problem a line outside an accepted fence holds, or
        None (below)
    unformatted(text) -> the text with every format character (Unicode category Cf) removed and its whitespace runs
        collapsed: the form a heading's name is tested in for the near misses (the E15 lane contract A14;
        `spec.withheld_of`, `readings.py`)
    label_form(text) -> the text with every format character (Unicode category Cf) removed and its leading whitespace
        (any Unicode space) stripped: the form a line is tested in for a `Status:` or `Base:` label by the second
        reading and by the spec (THE HIDDEN-LABEL RULE, below; the E15 lane contract A15)
    fold(text) -> THE FOLD (below): NFKD normalization with every combining mark removed, then NFKC normalization,
        then case folding: the form every label, slice-heading and withheld-name test compares in (the E15 lane
        contract A16 (3), A17 (1))
    marks_off(text) -> the text with its leading marks set aside (THE LEADING MARKS, below; A18 (3))
    label_candidate(text) -> `Status:` or `Base:` when the text, its leading marks set aside (THE LEADING MARKS) and
        folded (THE FOLD), opens with `status` or `base`, any spaces or tabs, then a colon (a label candidate, A16 (3),
        A17 (1), A18 (3)), else None
    unlisted(text) -> (column, character) for the first character of the text outside THE CHARACTER LIST (below,
        `LISTED`), else None
    read(text) -> Doc: the build doc read whole: `lines`, `fenced`, `slices` ([{"name", "short", "status",
        "line", "status_at"}] in document order), `base` ({"line", "commit", "at"} or None), and `problems`: the
        scan's, the character list's, the plain-structure rule's, the label rule's and the stray-label rule's (below),
        in line order (on one line, in that order). Every reader of a build doc reads through `read` and stops on
        its first problem; `scan` alone serves the notes rule (`notes.py`), which never stops

THE PREFIX. A line's prefix is any indent (spaces or tabs) and any block-quote markers (`>`) or list-item
markers (`-`, `+`, `*`, or one to nine digits then `.` or `)`, followed by a space or a tab), in any order and
number.

THE FENCE RULE (stated once here and once in the contract). A fence line is any line whose first characters,
after its prefix, are three or more backticks or three or more tildes. A fence is ACCEPTED only when:

1. its opening line starts at column 0 (no indent, no list marker, no `>`) with three or more backticks or
   three or more tildes, and, for backticks, an info string holding no backtick (CommonMark's rule);
2. its closing line is the first later line that starts at column 0 with the same character, repeated at
   least as many times, with nothing after it but spaces or tabs;
3. no line between them is a fence line off column 0 (one indented up to three spaces could close the fence
   to CommonMark; the rule never asks which). Every other line between is the fence's content, whatever it
   looks like (a shorter fence, the other character, a heading, a `Status:` label, a `<` line).

ANY other fence line anywhere in the build doc is a problem, named with its line number: a fence line off
column 0 (indented, inside a list item, after one or more `>`), a backtick line whose info string holds a
backtick, and an opening line that never closes. The reader follows no list, block-quote or
lazy-continuation rule: off column 0 there is no accepted fence.

THE RAW HTML RULE (A9; stated once here and once in the contract). A raw HTML line is any line outside an
accepted fence whose first characters, after its prefix, are `<` followed by an ASCII letter, `/`, `!` or
`?`. EVERY such line is a problem, named with its line number: a tag, a closing tag, a comment, a processing
instruction, a declaration, a CDATA section, and also a line that only opens with an inline `<placeholder>` or
an autolink (by design: the rule never asks which a line is). The reader does not track where a raw HTML block
ends. A `<` line inside an accepted fence is content; a `<` later in a line, or followed by anything else (a
space, a digit, another sign), is text.

THE LABEL RULE (A10 and A11, C1A6-1; stated once here and once in the contract). Outside accepted fences, a `## ` line
that matches the build-doc form's slice heading (`## Slice <name> <dash> <short>`) opens a slice's section and
any other `## ` line closes it; the header is every line before the first `## ` line. A line "starts with `Status:`"
(or `Base:`) when it is a label candidate (`label_candidate`, A16 (3)): its leading marks set aside (THE LEADING
MARKS, below, A18 (3)) and folded (THE FOLD, below), it opens with `status` (or `base`), any spaces or tabs, then a
colon, so `status: built`, `Status : built`, `St` U+00E4 `tus: built` and U+2018 `Status: built` are such lines.
Inside a slice's section, a line that starts with `Status:` is the slice's label only when

1. it reads exactly `Status: ` (one space) and one of `not started`, `in progress`, `built`, `rejected`,
   `signed off with conditions`, `signed off` (A11's six), with nothing after but spaces or tabs; and
2. it is the last line of its paragraph: the next line is empty or holds only spaces and tabs (never any other
   Unicode space), is an ATX heading (up to three spaces, one to six `#`, then a space, a tab or the line's
   end), opens an accepted fence, or the doc ends.

A slice holds at most one. In the header, a line that starts with `Base:` is the recorded base only when it
reads exactly `Base: ` and 7 to 40 lower-case hex digits, with nothing after but spaces or tabs, and meets 2;
the header holds at most one. ANY other line starting with those labels there (a wrong value, text after it,
a following paragraph line or a Setext underline, a second label) is a problem named with its line number, and
a second label's problem names the first label's line too. Why it holds: CommonMark renders nothing of a line
held inside an inline comment opened mid-line, a link reference definition's title or an inline link's title,
and each needs a closing mark after the held line in the same paragraph; the exact value leaves no room for
one on the label line, and the paragraph's end leaves no later line. A `Base:` line outside the header is no label,
and a `Status:` line in the header is no label (the spec still removes every `Status:` line, `spec.py`).

THE STRAY-LABEL RULE (A18 (1), C1A11-1; stated once here, `STRAY`, and once in the contract). A line that starts with
`Status:` (a label candidate, above) after the build doc's first `## ` line and outside every slice's section (in a
section a non-slice `## ` line opened, a withheld section included) is a problem named with its line number. Only
the source lines outside accepted fences are read for it, never the second reading's rendered lines. Why it holds: a
`## ` heading a person reads as a slice heading but neither reading takes as one (a section number, `## 1. Slice B`,
`## (1) Slice B`, `## A. Slice B`; a lookalike letter, `## SIice B`, `## S1ice B`; a word before it, `## Next: Slice
B`, `## The Slice B`; U+00B2 before it) closes the slice above it and opens no slice, so its `Status:` line lands
outside every slice's section, where no rule read it and its slice vanished from the sign-off check; whatever the
heading's spelling, that trace is the same. This replaces, for those lines only, the rule that a `Status:` line
outside every slice is no label; a `Status:` line before the first `## ` line is in the header and keeps it.

THE PLAIN-STRUCTURE RULE (A12, C1A7-1; stated once here and once in the contract). Outside accepted fences, a
line that, after its prefix (above), opens like an ATX heading (one to six `#`, then a space, a tab or the
line's end) or like a `Status:` or `Base:` label (a label candidate, folded by THE FOLD, A16 (3)) is read only
when it is PLAIN: its prefix is empty (column 0, no indent, no marker), and a heading is one to six `#` then
exactly one space (the next character is neither a space nor a tab); a plain label is then read by the label rule above. EVERY other such line is a problem
named with its line number, anywhere in the doc (inside a slice, in the header, between sections): a heading or
a label indented by any spaces or a tab, after a list-item marker or one or more `>`; `##` then a tab, a bare
`##`, `##` then two spaces. Why it holds: CommonMark renders a heading indented one to three spaces, a heading
whose `#`s are followed by a tab or by the line's end, and a label indented one to three spaces just as their
plain forms, and a marker puts a heading or a label inside a container the reader does not follow; the reader
takes structure only where nothing but the plain form can be meant, and refuses the rest instead of modelling
more Markdown. A problem line is never read as structure. A `#` with no space after it (`#hashtag`), seven or
more `#`, and a `Status:` or `Base:` later in a line are text; a line inside an accepted fence is content.

THE CHARACTER LIST (A16, C1A9-1; stated once here, `LISTED`, and once in the contract). Outside accepted fences,
every character of the build doc must be printable ASCII (U+0020 to U+007E), a tab, a line ending (LF, CR, CRLF:
`split_lines` ends a line there, so no line holds one) or a byte order mark at the start of line 1 (`bare` drops
it), or one of the fixed list: the punctuation and symbols the owner's real plans use (U+00A7, U+00B2, U+00B7,
U+00D7, U+2013, U+2014, U+2019, U+2026, U+2190 to U+2194, U+2197, U+2212, U+2248, U+2264, U+2265, U+2715), the
curly quotes U+2018, U+201C, U+201D, and the accented Latin letters U+00C0 to U+00FF except U+00F7. Any other
character is a problem naming its code point, its column and its line: a format character, a Unicode space, a
combining or default-ignorable mark, a Hangul filler, a braille blank, a control character, a letter of another
script or a full-width form. Why it holds: each round of the class found one more character a reader renders as
nothing (or as a letter it is not) in front of a label, a base, a slice heading, a withheld heading or a label
heading, so that both readings missed the structure a person sees; a short list of characters the owner's plans
really use leaves no such character to find. Inside an accepted fence no character is refused (the fence rule
comes first, and a fence's lines are content). On one line the fence rule's and the raw HTML rule's problem is named
first, then the character, then the plain-structure or label rule's problem: a line whose label only looks exact,
or whose heading only looks plain, is named for the character that makes it so.

THE LEADING MARKS (A18 (3), C1A11-3; stated once here, `MARKS` and `marks_off`, and once in the contract). Before a
line is tested for a `Status:` or `Base:` label (every label test THE FOLD names below), its leading run of Unicode
spaces (category Z) and of the listed non-ASCII punctuation and symbols is set aside: the character list's fixed
punctuation and symbols (U+00A7, U+00B2, U+00B7, U+00D7, U+2013, U+2014, U+2019, U+2026, U+2190 to U+2194, U+2197,
U+2212, U+2248, U+2264, U+2265, U+2715) and the curly quotes U+2018, U+201C, U+201D. So U+2018 `Status: built`,
U+201C `Status: built` U+201D, U+00A7 `Status: built`, U+2026 `Status: built`, U+00B7 `Status: built` and U+2018
`Base: 1234567` are label candidates, not exact, and stop at their line where the label rule or the stray-label rule
reads them; the spec removes such a `Status:` line wherever it stands; a heading named so is refusal (c) of the second
reading. ASCII punctuation is never set aside (`*Status:`, `(Status:`, `-Status:` stay text): setting it aside would
stop real plans. Why it holds: a reader passes over a leading quote, section sign or dot and sees the label, so both
readings must take it as one.

THE FOLD (A16 (3), A17 (1), C1A10-1; stated once here, `fold`, and once in the contract). Every label test (the
label rule, the plain-structure rule, the spec's removal, the second reading's cards, base and refusals (a) and (c)),
every slice-heading test (the second reading's refusal (b)) and every withheld-name test (`spec.name_key`) compares
the text folded: NFKD normalization with every combining mark (Unicode category M) removed, then NFKC normalization,
then case folding. So an accented letter the character list admits folds to its plain letter (`St` U+00E4 `tus` reads
`status`, `Sl` U+00EF `ce` reads `slice`, `B` U+00E4 `se` reads `base`), a compatibility form to its plain form and
upper case to lower case. The fold cannot reach the nine listed letters that have no decomposition (U+00C6, U+00D0,
U+00D8, U+00DE, U+00DF and U+00E6, U+00F0, U+00F8, U+00FE): case folding takes each upper-case one to its lower-case
one and U+00DF to `ss`, and the withheld-name key then maps U+00F0 to `d`, U+00F8 to `o`, U+00FE to `th` and U+00E6
to `ae` (A18 (2), `spec.LETTERS`), so a letter the list admits hides no withheld name. The label and slice-heading
tests do not map them: none of the nine is a letter of `status`, `base` or `slice`, so a word spelled with one is
another word to both readings. The builder's-notes declaration test reads the heading folded the same way
(`notes.declares_name`).

Every reader of the build doc (the spec and its sections, the gate's slices and `Status:` lines, the `Base:`
line) stops the run `doc-unreadable` on the first problem, before any ask, request or packet; the plan's
author edits the doc. A doc these rules accept is then read a second time by a CommonMark reader and the two
readings' decisions compared (A13, `readings.py`, "THE TWO-READINGS RULE"; `spec.read`).
"""
import re
import unicodedata

from station_core import templates

LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$")
PREFIX = r"^[ \t]*(?:(?:>|(?:[-+*]|\d{1,9}[.)])(?=[ \t]))[ \t]*)*"
FENCE_LINE = re.compile(PREFIX + r"(?:`{3,}|~{3,})")
HTML_LINE = re.compile(PREFIX + r"<[A-Za-z/!?]")
MARGIN = re.compile(r"^(`{3,}|~{3,})(.*)$")
OFF_MARGIN = ("a fence line off the left margin (indented, inside a list item or after a block-quote marker): "
              "only a fence that opens and closes at column 0 is read")
RAW_HTML = ("a raw HTML line (it opens with `<` and an ASCII letter, `/`, `!` or `?`), where CommonMark may read raw "
            "HTML and no heading, label or fence: vertical-v2 reads no raw HTML line in a build doc")
SECTION = "## "
STATUS_LABEL = "Status:"
BASE_LABEL = "Base:"
STATUS_VALUES = ("not started", "in progress", "built", "rejected", "signed off with conditions",
                 "signed off")    # A11: the six (A10's four, plus the two cards the records and the v2 stations write)
STATUS_EXACT = re.compile(r"Status: (%s)[ \t]*\Z" % "|".join(re.escape(v) for v in STATUS_VALUES))
BASE_EXACT = re.compile(r"Base: ([0-9a-f]{7,40})[ \t]*\Z")
BLANK = re.compile(r"[ \t]*\Z")
ATX_HEADING = re.compile(r" {0,3}#{1,6}(?:[ \t]|\Z)")
PREFIX_ONLY = re.compile(PREFIX)
HEADING_OPEN = re.compile(r"#{1,6}(?:[ \t]|\Z)")
CANDIDATE = re.compile(r"(status|base)[ \t]*:")
PLAIN_HEADING = re.compile(r"#{1,6} (?![ \t])")
OFF_PLAIN_HEADING = ("a line that opens like a heading off the plain form (indented, after a list-item or "
                     "block-quote marker, or its `#`s not followed by exactly one space), which CommonMark may "
                     "render as a heading the reader does not take: vertical-v2 reads a heading only when it is "
                     "plain, at column 0, one to six `#` then one space")
OFF_PLAIN_LABEL = ("a line that opens like a `%s` label off the plain form (indented, or after a list-item or "
                   "block-quote marker), which CommonMark may render as the label the reader does not take: "
                   "vertical-v2 reads a label only when it is plain, at column 0")
MARKS = frozenset(
    [chr(c) for c in (0x00A7, 0x00B2, 0x00B7, 0x00D7, 0x2013, 0x2014, 0x2019, 0x2026, 0x2190, 0x2191, 0x2192,
                      0x2193, 0x2194, 0x2197, 0x2212, 0x2248, 0x2264, 0x2265, 0x2715)]  # punctuation and symbols
    + [chr(c) for c in (0x2018, 0x201C, 0x201D)])                                   # the curly quotes
LISTED = frozenset(
    [chr(c) for c in range(0x20, 0x7F)] + ["\t"]                                   # printable ASCII and a tab
    + list(MARKS)                                       # the listed punctuation and symbols, and the curly quotes
    + [chr(c) for c in range(0x00C0, 0x0100) if c != 0x00F7])                       # the accented Latin letters
UNLISTED = ("%s at column %d is outside vertical-v2's character list (printable ASCII, a tab, a line ending, a byte "
            "order mark at the start of line 1, and the fixed punctuation, symbols, curly quotes and accented Latin "
            "letters the plans use): a character outside the list can hide a heading, a label or a section name "
            "from both readings, so vertical-v2 reads none outside a fence")
STRAY = ("a `Status:` line after the build doc's first level 2 heading and outside every slice's section (a "
         "`## Slice <name> <dash> <short>` heading opens a slice's section and any other `## ` heading closes it), "
         "which no reading takes as any slice's card: a slice heading neither reading takes (a section number, a "
         "lookalike letter or a word before `Slice`) leaves its `Status:` line here, so its slice would vanish from "
         "the sign-off check; vertical-v2 reads a `Status:` line after the header only inside a slice's section")
LABELS = {
    STATUS_LABEL: ("one of %s" % ", ".join("`%s`" % v for v in STATUS_VALUES), STATUS_EXACT, "a slice holds one"),
    BASE_LABEL: ("7 to 40 lower-case hex digits", BASE_EXACT, "the header holds one"),
}


class Scan(object):
    def __init__(self, fenced, problems):
        self.fenced, self.problems = fenced, problems


class Doc(object):
    def __init__(self, lines, fenced, problems, slices, base):
        self.lines, self.fenced, self.problems, self.slices, self.base = lines, fenced, problems, slices, base


def split_lines(text):
    """The text's lines with their endings; only LF, CRLF and CR end a line (CommonMark's rule)."""
    return LINE.findall(text)


def bare(line, number=None):
    """A line without its ending (and, on the first line, without a byte order mark)."""
    out = line.rstrip("\r\n")
    return out[1:] if number == 1 and out.startswith("﻿") else out


def fence_line(line):
    return bool(FENCE_LINE.match(line))


def html_line(line):
    return bool(HTML_LINE.match(line))


def plain_problem(line):
    """The plain-structure rule (module docstring) for one line outside an accepted fence: the problem's words, or
    None when the line opens like no heading and no label, or is plain. After its prefix, a line opens like a label
    when it is a label candidate (`label_candidate`, A16 (3))."""
    at = PREFIX_ONLY.match(line).end()
    rest = line[at:]
    if HEADING_OPEN.match(rest):
        return None if at == 0 and PLAIN_HEADING.match(line) else OFF_PLAIN_HEADING
    label = label_candidate(rest)
    if label is not None:
        return None if at == 0 else OFF_PLAIN_LABEL % label
    return None


def fold(text):
    """THE FOLD (module docstring; A16 (3), A17 (1)): NFKD normalization with every combining mark (Unicode category
    M) removed, then NFKC normalization, then case folding: `Status`, `STATUS`, `St` U+00E4 `tus` and a full-width
    `Status` fold alike."""
    marks_off = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.category(c).startswith("M"))
    return unicodedata.normalize("NFKC", marks_off).casefold()


def marks_off(text):
    """THE LEADING MARKS (module docstring; A18 (3)): the text with its leading run of Unicode spaces (category Z) and
    of the listed non-ASCII punctuation and symbols (`MARKS`) set aside; ASCII punctuation is never set aside."""
    at = 0
    while at < len(text) and (text[at] in MARKS or unicodedata.category(text[at]).startswith("Z")):
        at += 1
    return text[at:]


def label_candidate(text):
    """`Status:` or `Base:` when the text, its leading marks set aside (THE LEADING MARKS, `marks_off`, A18 (3)) and
    folded (THE FOLD), opens with `status` or `base`, any spaces or tabs, then a colon (A16 (3), A17 (1)), else None.
    Whether such a line is the label is the label rule's exact test, on the line as written."""
    match = CANDIDATE.match(fold(marks_off(text)))
    if match is None:
        return None
    return STATUS_LABEL if match.group(1) == "status" else BASE_LABEL


def unlisted(text):
    """(1-based column, character) for the first character of the text outside THE CHARACTER LIST (`LISTED`), or
    None."""
    for index, char in enumerate(text):
        if char not in LISTED:
            return index + 1, char
    return None


def character(char):
    """A character named for a person: its code point and its Unicode name."""
    return "U+%04X (%s)" % (ord(char), unicodedata.name(char, "a control or unnamed character"))


def unlisted_problem(column, char):
    return UNLISTED % (character(char), column)


def unformatted(text):
    """The text with every format character (Unicode category Cf: a zero-width space or joiner, a soft hyphen, a byte
    order mark) removed, then its whitespace runs collapsed to one space and trimmed (A14)."""
    return " ".join("".join(c for c in text if unicodedata.category(c) != "Cf").split())


def label_form(text):
    """THE HIDDEN-LABEL RULE (A15; stated once here and once in the contract, section 5, "Two readings"): a line reads
    as a `Status:` or `Base:` label when, after every format character (Unicode category Cf: a zero-width space, a soft
    hyphen, a zero-width no-break space, a word joiner) is removed and its leading whitespace (any Unicode space, as
    `str.isspace` reads it: a no-break space, an ideographic space) is stripped, it starts with that label. The second
    reading tests every rendered paragraph line this way (`readings.py`), so a label hidden behind such characters is a
    label candidate there, a second or a non-exact label the line rules never take, and the run stops `doc-unreadable`
    naming its line; the spec removes every line outside fences that reads as a `Status:` label this way
    (`spec.clean`), so a hidden one the cards do not see (in the header, between sections) reaches no packet."""
    return "".join(c for c in text if unicodedata.category(c) != "Cf").lstrip()


def scan(lines):
    fenced, problems = set(), []
    fence = None            # (character, length, opening line) of the accepted fence the reader is inside
    for number, raw in enumerate(lines, 1):
        line = bare(raw, number)
        margin = MARGIN.match(line)
        if fence is not None:
            char, length, start = fence
            fenced.add(number)
            if margin is None and fence_line(line):
                problems.append((number, "%s, inside the fence opened at line %d" % (OFF_MARGIN, start)))
            elif margin and margin.group(1)[0] == char and len(margin.group(1)) >= length \
                    and not margin.group(2).strip(" \t"):
                fence = None
            continue
        if margin is not None:
            if margin.group(1)[0] == "`" and "`" in margin.group(2):
                problems.append((number, "a backtick fence line whose info string holds a backtick, which "
                                         "CommonMark never opens"))
                continue
            fence = (margin.group(1)[0], len(margin.group(1)), number)
            fenced.add(number)
            continue
        if fence_line(line):
            problems.append((number, OFF_MARGIN))
            continue
        if html_line(line):
            problems.append((number, RAW_HTML))
    if fence is not None:
        problems.append((fence[2], "a fence opened here never closes, so what follows it cannot be told from code"))
    problems.sort()
    return Scan(fenced, problems)


def ends_paragraph(lines, fenced, number):
    """True when line `number` is the last line of its paragraph under the label rule: the next line is empty or
    only spaces and tabs, is an ATX heading, opens an accepted fence (a fenced line right after an unfenced one
    is a fence's opening line), or there is none."""
    after = number + 1
    if after > len(lines):
        return True
    if after in fenced:
        return True
    line = bare(lines[after - 1], after)
    return bool(BLANK.match(line) or ATX_HEADING.match(line))


def _label(lines, fenced, number, line, label, where, first):
    """(the label's value or None, the problem's words or None) for a line that starts with `label`."""
    value_words, exact, one = LABELS[label]
    match = exact.match(line)
    wrong = []
    if match is None:
        wrong.append("does not read exactly `%s ` and %s with nothing after but spaces or tabs" % (label, value_words))
    if not ends_paragraph(lines, fenced, number):
        wrong.append("is not the last line of its paragraph (the next line is not empty or spaces and tabs only, a "
                     "heading or an accepted fence's opening line), so CommonMark may hold it hidden in an inline "
                     "comment, a link title or a link reference definition")
    if first is not None:
        wrong.append("is a second `%s` line in %s (the first is line %d): %s" % (label, where, first, one))
    if not wrong:
        return match.group(1), None
    return None, ("a `%s` line in %s that %s; vertical-v2 reads a label only when it is exact and ends its paragraph"
                  % (label, where, "; and ".join(wrong)))


def read(text):
    """The build doc read whole under the fence rule, the raw HTML rule, the plain-structure rule, the label rule and
    the character list (module docstring)."""
    lines = split_lines(text)
    found = scan(lines)
    problems = list(found.problems)
    slices, base, base_at, header, current = [], None, None, True, None
    for number, raw in enumerate(lines, 1):
        if number in found.fenced:
            continue
        line = bare(raw, number)
        odd = unlisted(line)                       # THE CHARACTER LIST (A16): named before the line's other problem
        if odd is not None:
            problems.append((number, unlisted_problem(*odd)))
        off = plain_problem(line)
        if off is not None:
            problems.append((number, off))
        elif line.startswith(SECTION):
            header = False
            match = templates.BUILD["slice"].match(line)
            current = {"name": match.group(1), "short": match.group(2), "status": None, "line": number,
                       "status_at": None} if match else None
            if current is not None:
                slices.append(current)
        elif current is not None and label_candidate(line) == STATUS_LABEL:
            value, problem = _label(lines, found.fenced, number, line, STATUS_LABEL, "slice %s" % current["name"],
                                    current["status_at"])
            if problem is not None:
                problems.append((number, problem))
            if current["status_at"] is None:
                current["status"], current["status_at"] = value, number
        elif not header and label_candidate(line) == STATUS_LABEL:      # THE STRAY-LABEL RULE (A18 (1))
            problems.append((number, STRAY))
        elif header and label_candidate(line) == BASE_LABEL:
            value, problem = _label(lines, found.fenced, number, line, BASE_LABEL, "the header", base_at)
            if problem is not None:
                problems.append((number, problem))
            if base_at is None:
                base, base_at = {"line": line.strip(), "commit": value, "at": number}, number
    problems.sort(key=lambda problem: problem[0])      # stable: on one line, the scan's, then the loop's, in order
    return Doc(lines, found.fenced, problems, slices, base)
