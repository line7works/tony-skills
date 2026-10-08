"""The architecture doc's run log: continuation, strikethrough, and the no-loss check (E14-1).

The rule the v1 architect station states for its one living doc, as code:

- a re-run appends a new `### Run <N>` block at the tail of `## Run log`, N one more than the
  highest block already there (`next_run`, `append_run`);
- a superseded line elsewhere in the doc is struck through, `~~like this~~`, never deleted
  (`strike`, `strike_in`);
- a proposed document that would drop or change a prior run-log block, or drop a prior
  poured-concrete line (struck or not), is refused before anything is written (`losses`,
  `check_no_loss`).

Every function takes and returns text; none writes a file.
"""
import re

D = "\u2014"
RUN = re.compile(r"^### Run (\d+) %s " % D)
RUN_LOG = "## Run log"
POURED = "## Poured concrete (one-way doors)"


class RunLogRefused(ValueError):
    """A run-log write that would break the one-living-doc rule."""


def _lines(text):
    return [raw.rstrip("\r\n") for raw in text.splitlines(True)]


def runs(text):
    """[(N, line number)] for every `### Run <N>` heading, in document order."""
    return [(int(m.group(1)), i) for i, line in enumerate(_lines(text), 1) for m in [RUN.match(line)] if m]


def next_run(text):
    numbers = [n for n, _ in runs(text)]
    return max(numbers) + 1 if numbers else 1


def _blocks(text):
    """{N: the block's text} for every run block: the heading through the line before the next
    heading of any level (or the end)."""
    lines = _lines(text)
    out = {}
    for index, line in enumerate(lines):
        match = RUN.match(line)
        if not match:
            continue
        end = index + 1
        while end < len(lines) and not lines[end].startswith("#"):
            end += 1
        block = lines[index:end]
        while block and not block[-1].strip():
            block.pop()
        out[int(match.group(1))] = "\n".join(block)
    return out


def _section_items(text, heading):
    lines = _lines(text)
    out = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = line == heading
            continue
        if inside and line.startswith("- "):
            out.append(line)
    return out


def append_run(text, block):
    """`text` with `block` appended at the tail of `## Run log` (the section created at the end of
    the doc when absent). The block's number must be `next_run(text)`."""
    head = block.lstrip("\n").split("\n", 1)[0]
    match = RUN.match(head)
    if not match:
        raise RunLogRefused("the block does not open with '### Run <N> %s <date> %s trigger: ...'" % (D, D))
    expected = next_run(text)
    if int(match.group(1)) != expected:
        raise RunLogRefused("the block is Run %s; the next run of this doc is Run %d"
                            % (match.group(1), expected))
    newline = "\r\n" if "\r\n" in text else "\n"
    body = block.strip("\n").replace("\n", newline) + newline
    lines = text.splitlines(True)
    start = next((i for i, raw in enumerate(lines) if raw.rstrip("\r\n") == RUN_LOG), None)
    if start is None:
        base = text if text.endswith(("\n", "\r")) or not text else text + newline
        return base + newline + RUN_LOG + newline + body
    end = start + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    section = "".join(lines[start:end])
    if not section.endswith(("\n", "\r")):
        section += newline
    stripped = section.rstrip("\r\n") + newline
    has_runs = any(RUN.match(raw.rstrip("\r\n")) for raw in lines[start + 1:end])
    joined = stripped + (newline if has_runs else "") + body
    tail = "".join(lines[end:])
    if tail:
        joined += newline
    return "".join(lines[:start]) + joined + tail


def strike(line):
    """`- ~~text~~` for `- text`, `~~text~~` for any other line; a struck line stays as it is."""
    marker = "- " if line.startswith("- ") else ""
    body = line[len(marker):]
    if body.startswith("~~") and body.endswith("~~") and len(body) >= 4:
        return line
    return "%s~~%s~~" % (marker, body)


def strike_in(text, line):
    """`text` with its one line equal to `line` struck through; every other byte unchanged."""
    lines = text.splitlines(True)
    hits = [i for i, raw in enumerate(lines) if raw.rstrip("\r\n") == line]
    if len(hits) != 1:
        raise RunLogRefused("the line to strike appears %d times, not once: %r" % (len(hits), line))
    raw = lines[hits[0]]
    ending = raw[len(raw.rstrip("\r\n")):]
    lines[hits[0]] = strike(line) + ending
    return "".join(lines)


def losses(before, after):
    """[sentence] for every prior run-log block dropped or changed and every prior poured-concrete
    line dropped (a line struck through in `after` is kept, not lost)."""
    found = []
    after_blocks = _blocks(after)
    for number, block in sorted(_blocks(before).items()):
        if number not in after_blocks:
            found.append("the run-log block Run %d is gone" % number)
        elif after_blocks[number] != block:
            found.append("the run-log block Run %d was changed; a run's record is never rewritten" % number)
    kept = set(_section_items(after, POURED))
    for line in _section_items(before, POURED):
        if line not in kept and strike(line) not in kept:
            found.append("the poured-concrete line %r is gone; a superseded line is struck through, "
                         "never deleted" % line)
    return found


def check_no_loss(before, after):
    found = losses(before, after)
    if found:
        raise RunLogRefused("; ".join(found))
