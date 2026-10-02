"""A builder's-notes file declared by its first heading (C1A3-3; the E15 lane contract A5 (3); contract
section 5, the allow rule's (3)).

    declares(text) -> the heading text that declares the file the builder's notes, or None

The slice review withholds a Markdown file whose first heading says it is the builder's notes, and so does
this core: a `.md` blob of the reviewed commit (a regular file, never a link) whose first heading holds
"notes from the builder", "builder notes", "builder's notes", "builders notes" or "build notes" (letter case
aside) is left out of every packet and named. The file-name and folder-name leg is `packet.left_out_by_rule`.

Which heading is first is read WIDE, so a declaration is never missed where a CommonMark reader would find
one; a wider reading only ever withholds more, and what it withholds is named. Every heading-shaped line is
a candidate until the first CERTAIN heading, which is a candidate too:

- a candidate is an ATX heading (`#` to `######`, then a space, a tab or the line's end) or the text of a
  Setext heading (the run of non-blank lines above an `===` or `---` underline, joined by spaces), read
  after any block-quote and list-item markers are stripped, whatever its indentation, and whether or not a
  fence, a raw HTML block, a block quote, a list or a front matter block holds it;
- a CERTAIN heading is an ATX heading at the left margin, outside every fence (this core's fence reader:
  `fences.py`; an unclosed fence runs to the end), with no line opening with `<` before it (a raw HTML block
  may hold it) and, when the file opens with a `---` line, after that block's closing `---` or `...` line
  (front matter, which the slice review also reads as a thematic break with a Setext heading above it:
  both readings are candidates here). A heading at the left margin can be held by nothing else: a list
  item's or a block quote's content is indented or marked, and an ATX heading is never a lazy line.

CRLF and CR endings are line endings and a leading byte order mark is dropped.
"""
import re

from . import fences

DECLARES = re.compile(r"notes from the builder|builder'?s? notes|build notes", re.I)
CONTAINERS = re.compile(r"^(?:[ \t]*(?:>|[-+*](?=[ \t]|$)|\d{1,9}[.)](?=[ \t]|$))[ \t]?)+")
ATX = re.compile(r"^[ \t]*#{1,6}(?:[ \t]+(.*?)|)[ \t]*$")
UNDERLINE = re.compile(r"^[ \t]*(?:=+|-+)[ \t]*$")
CERTAIN = re.compile(r"^#{1,6}(?:[ \t]|$)")
FRONT_OPEN = re.compile(r"^---[ \t]*$")
FRONT_CLOSE = re.compile(r"^(?:---|\.\.\.)[ \t]*$")


def declares(text):
    if text.startswith("﻿"):
        text = text[1:]
    raw = fences.split_lines(text)
    lines = [line.rstrip("\r\n") for line in raw]
    fenced = fences.scan(raw).fenced
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    front = first is not None and bool(FRONT_OPEN.match(lines[first]))
    certain_allowed = not front
    html_seen = False
    para, candidates = [], []
    for index, line in enumerate(lines):
        stripped = CONTAINERS.sub("", line)
        if stripped.lstrip().startswith("<"):
            html_seen = True
        atx = ATX.match(stripped)
        if atx:
            candidates.append(atx.group(1) or "")
            para = []
        elif UNDERLINE.match(stripped) and para:
            candidates.append(" ".join(para))
            para = []
        elif stripped.strip():
            para.append(stripped.strip())
        else:
            para = []
        if certain_allowed and not html_seen and index + 1 not in fenced and CERTAIN.match(line):
            break
        if front and not certain_allowed and index > first and FRONT_CLOSE.match(line):
            certain_allowed = True
    for heading in candidates:
        if DECLARES.search(heading):
            return heading
    return None
