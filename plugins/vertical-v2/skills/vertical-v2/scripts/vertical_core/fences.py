"""vertical-v2's own fence reader (the E15 lane contract A5 (2); C1A3-1; contract section 5).

    split_lines(text) -> [line with its ending]: CommonMark's line endings only (LF, CRLF, CR)
    scan(lines) -> Scan: `fenced`, the 1-based numbers of every line a fence holds (its opening and
        closing lines included); `problems`, [(line number, what)] for every line the reader cannot
        place, in line order

The frame's `templates.parse` (frozen in E15) toggles a fence on any line that starts with three
backticks; this reader follows CommonMark's fence rule instead, at the document's left margin:

- An opening fence is a line of up to three spaces, then three or more backticks or three or more
  tildes, then an info string. A backtick line whose info string holds a backtick opens nothing: it is
  text, as CommonMark reads it.
- The fence closes only on a line of up to three spaces, then the SAME character repeated at least as
  many times as the opening, then nothing but spaces or tabs. Every line between is the fence's content,
  whatever it looks like (a shorter fence, the other character, a heading, a `Status:` label).
- A fence still open at the end of the text cannot be told from what follows it: a problem, named at its
  opening line.

The lines this reader cannot place, each a problem with its line number, because a container the reader
does not follow decides where CommonMark's fence ends:

- a fence marker after a block-quote or list-item marker on the same line (`> ````, `- ~~~`, `1. ````):
  the fence lives in the container, and its closing line, back at the margin, would read as an opening;
- inside a fence opened with indentation while a list item was open, a non-blank line indented less than
  the opening line: CommonMark ends the list item there, and the fence with it;
- a fence marker inside a raw HTML block (from a line opening with `<` and a letter, `/`, `!` or `?`, to
  its end: the matching end marker for `<pre`, `<script`, `<style`, `<textarea`, `<!--`, `<?`, `<!X` and
  `<![CDATA[`, a blank line for any other): CommonMark reads no fence there.

The reader errs toward "not fenced" everywhere else, so a heading or a label it cannot place inside a fence
is read as one and removed, never kept unnamed.
"""
import re

LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$")
OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
CONTAINER_FENCE = re.compile(r"^ {0,3}(?:(?:>|[-+*]|\d{1,9}[.)])[ \t]*)+(?:`{3,}|~{3,})")
LIST_ITEM = re.compile(r"^ {0,3}(?:[-+*]|\d{1,9}[.)])(?:[ \t]|$)")
HTML_START = re.compile(r"^ {0,3}<[A-Za-z/!?]")
HTML_ENDS = ((re.compile(r"^ {0,3}<(?:pre|script|style|textarea)(?:[ \t>]|$)", re.I),
              re.compile(r"</(?:pre|script|style|textarea)>", re.I)),
             (re.compile(r"^ {0,3}<!--"), re.compile(r"-->")),
             (re.compile(r"^ {0,3}<\?"), re.compile(r"\?>")),
             (re.compile(r"^ {0,3}<!\[CDATA\["), re.compile(r"\]\]>")),
             (re.compile(r"^ {0,3}<![A-Za-z]"), re.compile(r">")))


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


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def scan(lines):
    fenced, problems = set(), []
    fence = None            # (character, length, opening line, indent opened while a list item was open, or None)
    list_open = False
    html_end = None         # the end marker of the raw HTML block the reader is inside, or "blank"
    for number, raw in enumerate(lines, 1):
        line = bare(raw, number)
        if fence is not None:
            char, length, start, list_indent = fence
            fenced.add(number)
            if list_indent is not None and line.strip() and _indent(line) < list_indent:
                problems.append((number, "a line indented less than the fence opened at line %d inside a list item: "
                                         "CommonMark ends the list item, and the fence, here" % start))
                fence = None
                continue
            close = CLOSE.match(line)
            if close and close.group(1)[0] == char and len(close.group(1)) >= length:
                fence = None
            continue
        if html_end is not None:
            if html_end == "blank":
                if not line.strip():
                    html_end = None
                    continue
            if OPEN.match(line) or CONTAINER_FENCE.match(line):
                problems.append((number, "a fence marker inside a raw HTML block, where CommonMark reads no fence"))
            if html_end != "blank" and html_end.search(line):
                html_end = None
            continue
        opening = OPEN.match(line)
        if opening and not (opening.group(2)[0] == "`" and "`" in opening.group(3)):
            indent = len(opening.group(1))
            fence = (opening.group(2)[0], len(opening.group(2)), number, indent if indent and list_open else None)
            fenced.add(number)
            continue
        if CONTAINER_FENCE.match(line):
            problems.append((number, "a fence marker inside a block quote or a list item, a container this reader "
                                     "does not follow"))
            continue
        if HTML_START.match(line):
            html_end = "blank"
            for start, end in HTML_ENDS:
                if start.match(line):
                    html_end = None if end.search(line[line.index("<") + 1:]) else end
                    break
            continue
        if LIST_ITEM.match(line):
            list_open = True
        elif line.strip() and not line[0] in " \t":
            list_open = False
    if fence is not None:
        problems.append((fence[2], "a fence opened here never closes, so what follows it cannot be told from code"))
    problems.sort()
    return Scan(fenced, problems)
