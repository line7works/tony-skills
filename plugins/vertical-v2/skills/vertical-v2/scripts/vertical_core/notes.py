"""A builder's-notes file declared by its first heading (C1A3-3; the E15 lane contract A5 (3); contract
section 5, the allow rule's (3)).

    declares(text) -> the heading text that declares the file the builder's notes, or None
    declaration(text) -> (that heading text, its line), or None: the line is the ATX heading's own, or a Setext
        heading's first text line
    declares_name(heading) -> True when a heading's text declares the builder's notes (`DECLARES`, read folded,
        a curly apostrophe read as `'`); both readings call it
    unlisted_heading(text) -> (line, character) for the first heading line the declaration test reads (below) that
        holds a character outside the character list (`fences.LISTED`), or None (the E15 lane contract A16 (2): the
        file is a notes candidate, withheld and named, never a stop; `readings.notes_unlisted`)

Since the E15 lane contract A13 this is the line reading of a file's declaration; `readings.notes_difference`
reads the file a second time with a CommonMark reader, and a file the CommonMark reader declares and this reading
does not stops the run (`packet.declared_notes`); a file this wide reading declares and the CommonMark reader does
not is withheld, as before A13 (A14, C1A8-4).

The slice review withholds a Markdown file whose first heading says it is the builder's notes, and so does
this core: a `.md` blob of the reviewed commit (a regular file, never a link) whose first heading holds
"notes from the builder", "builder notes", "builder's notes", "builders notes" or "build notes" (letter case
aside; the heading is folded first, NFKC normalization and case folding, A16 (3), and a curly apostrophe, U+2018 or
U+2019, is read as `'`, A16 send-back 1) is left out of every packet and named. The file-name and folder-name leg is `packet.left_out_by_rule`.

Which heading is first is read WIDE, so a declaration is never missed where a CommonMark reader would find
one; a wider reading only ever withholds more, and what it withholds is named. Every heading-shaped line is
a candidate until the first CERTAIN heading, which is a candidate too:

- a candidate is an ATX heading (`#` to `######`, then a space, a tab or the line's end) or the text of a
  Setext heading (the run of non-blank lines above an `===` or `---` underline, joined by spaces), read
  after any block-quote and list-item markers are stripped, whatever its indentation, and whether or not a
  fence, a raw HTML block, a block quote, a list or a front matter block holds it;
- a CERTAIN heading is an ATX heading at the left margin, outside every fence the strict rule accepts
  (`fences.py`, the E15 lane contract A8), BEFORE the first line that rule does not place (a fence line it does
  not accept, or a raw HTML line, A9: past it, where a fence or a raw HTML block ends is not known, so no
  heading is certain and every heading-shaped line stays a candidate, C1A4-1), with no line opening with `<`
  before it (a raw HTML block may hold it) and, when the file opens
  with a `---` line, after that block's closing `---` or `...` line (front matter, which the slice review
  also reads as a thematic break with a Setext heading above it: both readings are candidates here). A
  heading at the left margin before any such line can be held by nothing else: a list item's or a block
  quote's content is indented or marked, and an ATX heading is never a lazy line.

A notes file is not the build doc: a fence line the strict rule does not accept, or a raw HTML line, never
stops the run here; it only widens the reading.

CRLF and CR endings are line endings and a leading byte order mark is dropped.

A HEADING LINE OUTSIDE THE CHARACTER LIST (A16 (2) as send-back 1 of fix round 10 narrowed it; stated once here and
once in the contract). A file one of whose heading lines holds a character outside the character list (`fences.py`,
"THE CHARACTER LIST") is a notes candidate: withheld and named with the line and the character, never a stop,
because such a character can hide the declaration's words from a reader. The heading lines tested are the ones the
declaration test itself reads: the candidates above, up to and including the first certain heading, each an ATX
heading's line or the text lines of a Setext heading, never a line an accepted fence holds. They are found twice,
once in the file as written and once with every character outside the list set aside on each line (so a character
that keeps a line from reading as a heading, `<U+3164># Builder notes`, still counts), and the line as written is
tested. A heading past the first certain heading, or a fenced sample, holding such a character leaves the file an
ordinary one. `readings.notes_unlisted` adds the CommonMark reader's first heading (the one its declaration test
reads), its rendered name before whitespace is collapsed, so a character reference counts as the character it names.
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
    found = declaration(text)
    return None if found is None else found[0]


def declares_name(heading):
    """The declaration test on one heading's text, the same in both readings: folded (NFKC, case folding, A16 (3)),
    a curly apostrophe (U+2018, U+2019) read as `'` (A16 send-back 1), then `DECLARES`."""
    return bool(DECLARES.search(fences.fold(heading).replace("\u2018", "'").replace("\u2019", "'")))


def declaration(text):
    for heading, at, lines in candidates(text):
        if declares_name(heading):
            return heading, at
    return None


def candidates(text):
    """[(heading text, its first line, [the 1-based lines its text is read from])] in file order, up to and including
    the first certain heading: every heading the declaration test reads (module docstring)."""
    if text.startswith("\ufeff"):
        text = text[1:]
    raw = fences.split_lines(text)
    lines = [line.rstrip("\r\n") for line in raw]
    scan = fences.scan(raw)
    fenced = scan.fenced
    unplaced = scan.problems[0][0] if scan.problems else None
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    front = first is not None and bool(FRONT_OPEN.match(lines[first]))
    certain_allowed = not front
    html_seen = False
    para, found, para_at = [], [], []
    for index, line in enumerate(lines):
        stripped = CONTAINERS.sub("", line)
        if stripped.lstrip().startswith("<"):
            html_seen = True
        atx = ATX.match(stripped)
        if atx:
            found.append((atx.group(1) or "", index + 1, [index + 1]))
            para = []
        elif UNDERLINE.match(stripped) and para:
            found.append((" ".join(para), para_at[0], list(para_at)))
            para = []
        elif stripped.strip():
            if not para:
                para_at = []
            para.append(stripped.strip())
            para_at.append(index + 1)
        else:
            para = []
        if unplaced is not None and index + 1 >= unplaced:
            certain_allowed = False
            front = False
        if certain_allowed and not html_seen and index + 1 not in fenced and CERTAIN.match(line):
            break
        if front and not certain_allowed and index > first and FRONT_CLOSE.match(line):
            certain_allowed = True
    return found


def unlisted_heading(text):
    """(line, character) for the first heading line the declaration test reads that holds a character outside the
    character list, or None (module docstring, "A HEADING LINE OUTSIDE THE CHARACTER LIST")."""
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = [line.rstrip("\r\n") for line in fences.split_lines(text)]
    visible = "".join("".join(c for c in line if c in fences.LISTED) + "\n" for line in lines)
    read = set()
    for version in (text, visible):
        fenced = fences.scan(fences.split_lines(version)).fenced
        for heading, at, numbers in candidates(version):
            read.update(n for n in numbers if n not in fenced)
    for number in sorted(read):
        odd = fences.unlisted(lines[number - 1])
        if odd is not None:
            return number, odd[1]
    return None
