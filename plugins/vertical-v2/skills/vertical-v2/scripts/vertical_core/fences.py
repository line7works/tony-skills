"""vertical-v2's one fence rule: strict plain code blocks (the E15 lane contract A8; C1A4-1; contract section 5,
"The fence rule").

    split_lines(text) -> [line with its ending]: CommonMark's line endings only (LF, CRLF, CR)
    bare(line, number) -> the line without its ending (and, on line 1, without a byte order mark)
    fence_line(line) -> True when the line is a fence line (below)
    scan(lines) -> Scan: `fenced`, the 1-based numbers of every line an accepted fence holds (its opening and
        closing lines included); `problems`, [(line number, what)] for every fence line the rule does not
        accept, in line order

THE RULE (stated once here and once in the contract). A fence line is any line whose first characters, after
any indent (spaces or tabs) and after any block-quote markers (`>`) or list-item markers (`-`, `+`, `*`, or one
to nine digits then `.` or `)`, followed by a space or a tab), are three or more backticks or three or more
tildes. A fence is ACCEPTED only when:

1. its opening line starts at column 0 (no indent, no list marker, no `>`) with three or more backticks or
   three or more tildes, and, for backticks, an info string holding no backtick (CommonMark's rule);
2. its closing line is the first later line that starts at column 0 with the same character, repeated at
   least as many times, with nothing after it but spaces or tabs;
3. no line between them is a fence line off column 0 (one indented up to three spaces could close the fence
   to CommonMark; the rule never asks which). Every other line between is the fence's content, whatever it
   looks like (a shorter fence, the other character, a heading, a `Status:` label).

ANY other fence line anywhere in the build doc is a problem, named with its line number: a fence line off
column 0 (indented, inside a list item, after one or more `>`), a backtick line whose info string holds a
backtick, an opening line that never closes, and a fence line inside a raw HTML block (from a line opening
with `<` and a letter, `/`, `!` or `?`, to its end: the matching end marker for `<pre`, `<script`, `<style`,
`<textarea`, `<!--`, `<?`, `<!X` and `<![CDATA[`, a blank line for any other), where CommonMark reads no
fence. Every reader of the build doc (the spec, the gate's slices and `Status:` lines, the `Base:` line) stops
the run `doc-unreadable` on the first problem, before any ask, request or packet. The reader follows no list,
block-quote or lazy-continuation rule: off column 0 there is no accepted fence.
"""
import re

LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$")
FENCE_LINE = re.compile(r"^[ \t]*(?:(?:>|(?:[-+*]|\d{1,9}[.)])(?=[ \t]))[ \t]*)*(?:`{3,}|~{3,})")
MARGIN = re.compile(r"^(`{3,}|~{3,})(.*)$")
HTML_START = re.compile(r"^ {0,3}<[A-Za-z/!?]")
HTML_ENDS = ((re.compile(r"^ {0,3}<(?:pre|script|style|textarea)(?:[ \t>]|$)", re.I),
              re.compile(r"</(?:pre|script|style|textarea)>", re.I)),
             (re.compile(r"^ {0,3}<!--"), re.compile(r"-->")),
             (re.compile(r"^ {0,3}<\?"), re.compile(r"\?>")),
             (re.compile(r"^ {0,3}<!\[CDATA\["), re.compile(r"\]\]>")),
             (re.compile(r"^ {0,3}<![A-Za-z]"), re.compile(r">")))
OFF_MARGIN = ("a fence line off the left margin (indented, inside a list item or after a block-quote marker): "
              "only a fence that opens and closes at column 0 is read")


class Scan(object):
    def __init__(self, fenced, problems):
        self.fenced, self.problems = fenced, problems


def split_lines(text):
    """The text's lines with their endings; only LF, CRLF and CR end a line (CommonMark's rule)."""
    return LINE.findall(text)


def bare(line, number=None):
    """A line without its ending (and, on the first line, without a byte order mark)."""
    out = line.rstrip("\r\n")
    return out[1:] if number == 1 and out.startswith("﻿") else out


def fence_line(line):
    return bool(FENCE_LINE.match(line))


def scan(lines):
    fenced, problems = set(), []
    fence = None            # (character, length, opening line) of the accepted fence the reader is inside
    html_end = None         # the end marker of the raw HTML block the reader is inside, or "blank"
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
        if html_end is not None:
            if html_end == "blank" and not line.strip():
                html_end = None
                continue
            if fence_line(line):
                problems.append((number, "a fence line inside a raw HTML block, where CommonMark reads no fence"))
            if html_end != "blank" and html_end.search(line):
                html_end = None
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
        if HTML_START.match(line):
            html_end = "blank"
            for start, end in HTML_ENDS:
                if start.match(line):
                    html_end = None if end.search(line[line.index("<") + 1:]) else end
                    break
    if fence is not None:
        problems.append((fence[2], "a fence opened here never closes, so what follows it cannot be told from code"))
    problems.sort()
    return Scan(fenced, problems)
