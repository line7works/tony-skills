"""vertical-v2's one reading rule for the build doc: strict plain code blocks (the E15 lane contract A8; C1A4-1),
no raw HTML lines (A9; C1A5-1, C1A5-2), exact labels (A10; C1A6-1) and plain structure only (A12; C1A7-1);
contract section 5, "The fence rule", "No raw HTML lines", "Exact labels" and "Plain structure".

    split_lines(text) -> [line with its ending]: CommonMark's line endings only (LF, CRLF, CR)
    bare(line, number) -> the line without its ending (and, on line 1, without a byte order mark)
    fence_line(line) -> True when the line is a fence line (below)
    html_line(line) -> True when the line is a raw HTML line (below)
    scan(lines) -> Scan: `fenced`, the 1-based numbers of every line an accepted fence holds (its opening and
        closing lines included); `problems`, [(line number, what)] for every fence line the rule does not
        accept and every raw HTML line, in line order
    plain_problem(line) -> the words of the plain-structure problem a line outside an accepted fence holds, or
        None (below)
    read(text) -> Doc: the build doc read whole: `lines`, `fenced`, `slices` ([{"name", "short", "status",
        "line", "status_at"}] in document order), `base` ({"line", "commit", "at"} or None), and `problems`: the
        scan's, the plain-structure rule's and the label rule's (below), in line order. Every reader of a build doc reads through `read`
        and stops on its first problem; `scan` alone serves the notes rule (`notes.py`), which never stops

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
any other `## ` line closes it; the header is every line before the first `## ` line. Inside a slice's
section, a line that starts with `Status:` is the slice's label only when

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
one on the label line, and the paragraph's end leaves no later line. A `Status:` line outside every slice and
a `Base:` line outside the header are no label (the spec still removes every `Status:` line, `spec.py`).

THE PLAIN-STRUCTURE RULE (A12, C1A7-1; stated once here and once in the contract). Outside accepted fences, a
line that, after its prefix (above), opens like an ATX heading (one to six `#`, then a space, a tab or the
line's end) or like a `Status:` or `Base:` label is read only when it is PLAIN: its prefix is empty (column 0,
no indent, no marker), and a heading is one to six `#` then exactly one space (the next character is neither a
space nor a tab); a plain label is then read by the label rule above. EVERY other such line is a problem
named with its line number, anywhere in the doc (inside a slice, in the header, between sections): a heading or
a label indented by any spaces or a tab, after a list-item marker or one or more `>`; `##` then a tab, a bare
`##`, `##` then two spaces. Why it holds: CommonMark renders a heading indented one to three spaces, a heading
whose `#`s are followed by a tab or by the line's end, and a label indented one to three spaces just as their
plain forms, and a marker puts a heading or a label inside a container the reader does not follow; the reader
takes structure only where nothing but the plain form can be meant, and refuses the rest instead of modelling
more Markdown. A problem line is never read as structure. A `#` with no space after it (`#hashtag`), seven or
more `#`, and a `Status:` or `Base:` later in a line are text; a line inside an accepted fence is content.

Every reader of the build doc (the spec and its sections, the gate's slices and `Status:` lines, the `Base:`
line) stops the run `doc-unreadable` on the first problem, before any ask, request or packet; the plan's
author edits the doc. A doc these rules accept is then read a second time by a CommonMark reader and the two
readings' decisions compared (A13, `readings.py`, "THE TWO-READINGS RULE"; `spec.read`).
"""
import re

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
STRUCTURE = re.compile(PREFIX + r"(?:(#{1,6})(?:[ \t]|\Z)|(Status:|Base:))")
PLAIN_HEADING = re.compile(r"#{1,6} (?![ \t])")
OFF_PLAIN_HEADING = ("a line that opens like a heading off the plain form (indented, after a list-item or "
                     "block-quote marker, or its `#`s not followed by exactly one space), which CommonMark may "
                     "render as a heading the reader does not take: vertical-v2 reads a heading only when it is "
                     "plain, at column 0, one to six `#` then one space")
OFF_PLAIN_LABEL = ("a line that opens like a `%s` label off the plain form (indented, or after a list-item or "
                   "block-quote marker), which CommonMark may render as the label the reader does not take: "
                   "vertical-v2 reads a label only when it is plain, at column 0")
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
    None when the line opens like no heading and no label, or is plain."""
    match = STRUCTURE.match(line)
    if match is None:
        return None
    if match.group(2) is not None:
        return None if match.start(2) == 0 else OFF_PLAIN_LABEL % match.group(2)
    return None if match.start(1) == 0 and PLAIN_HEADING.match(line) else OFF_PLAIN_HEADING


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
    """The build doc read whole under the fence rule, the raw HTML rule, the plain-structure rule and the label rule
    (module docstring)."""
    lines = split_lines(text)
    found = scan(lines)
    problems = list(found.problems)
    slices, base, base_at, header, current = [], None, None, True, None
    for number, raw in enumerate(lines, 1):
        if number in found.fenced:
            continue
        line = bare(raw, number)
        off = plain_problem(line)
        if off is not None:
            problems.append((number, off))
            continue
        if line.startswith(SECTION):
            header = False
            match = templates.BUILD["slice"].match(line)
            current = {"name": match.group(1), "short": match.group(2), "status": None, "line": number,
                       "status_at": None} if match else None
            if current is not None:
                slices.append(current)
        elif current is not None and line.startswith(STATUS_LABEL):
            value, problem = _label(lines, found.fenced, number, line, STATUS_LABEL, "slice %s" % current["name"],
                                    current["status_at"])
            if problem is not None:
                problems.append((number, problem))
            if current["status_at"] is None:
                current["status"], current["status_at"] = value, number
        elif header and line.startswith(BASE_LABEL):
            value, problem = _label(lines, found.fenced, number, line, BASE_LABEL, "the header", base_at)
            if problem is not None:
                problems.append((number, problem))
            if base_at is None:
                base, base_at = {"line": line.strip(), "commit": value, "at": number}, number
    problems.sort()
    return Doc(lines, found.fenced, problems, slices, base)
