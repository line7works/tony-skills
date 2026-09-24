"""Where a block lands in the build doc, and where the verdict doc lives.

This module places text; it never decides what the text says. The record grammar is Appendix A's
and the lines themselves come from the records component's `render`, byte for byte. What is here
is the placement Appendix A fixes and the component does not do:

- **The ledger home.** Where the doc's punch-list blocks already live; the `## Punch list`
  section when none exist yet (created then); when records sit in more than one place, the place
  whose tail comes last in the file, so a record this run appends is the last record in file
  order and never dead under the open filter. One home per doc. Appends land at the home's tail.
- **The card.** One `Status:` line per slice, under the slice's `## Slice <X> —` heading.
- **The verdict doc.** `docs/reviews/<YYYY-MM-DD>-signoff-<feature>-<slice>.md`, where `<feature>`
  is the build doc's topic (`docs/plans/<YYYY-MM-DD>-<topic>.md`, else the filename minus
  `-build-plan.md`) and `<slice>` is the slice's letter or name lower-cased with spaces as
  hyphens. Exactly one match receives the copy; none means this is the slice's first run and the
  file is created. That glob is the component's `mirrors` glob, which is why the copy is checked
  rather than trusted.

Nothing here parses a record into a decision. The pilot's `ledger.py` is byte-frozen by the
records component (records E12-2) and is neither imported nor copied.
"""
import os
import re

from . import canon

RECORD_HEADING = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})\s+—\s+(review|recheck):\s*(.+?)\s*$")
SECTION = re.compile(r"^##\s+(.*?)\s*$")
SLICE_HEADING = re.compile(r"^##\s+Slice\s+(\S+?)\s*(?:—.*)?$")
STATUS = re.compile(r"^Status:\s*(.*?)\s*$")
PUNCH_LIST = "Punch list"
PLAN_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}-(?P<topic>.+)$")


class DocumentShape(RuntimeError):
    """The document does not hold what a placement rule needs."""


def lines_of(text):
    return text.split("\n")


def section_bounds(lines):
    """[(title, start index of the heading, end index exclusive)] for every `## ` section."""
    marks = [(index, SECTION.match(line).group(1))
             for index, line in enumerate(lines) if SECTION.match(line)]
    out = []
    for position, (index, title) in enumerate(marks):
        end = marks[position + 1][0] if position + 1 < len(marks) else len(lines)
        out.append((title, index, end))
    return out


def ledger_home(text):
    """(insert index, created section text or None): where an appended block's first line goes.

    The home is the section holding the LAST record heading in the file; with no record heading,
    the `## Punch list` section; with neither, a `## Punch list` section this call reports as one
    to create at the end of the document.
    """
    lines = lines_of(text)
    sections = section_bounds(lines)
    last_record = None
    for index, line in enumerate(lines):
        if RECORD_HEADING.match(line):
            last_record = index
    if last_record is not None:
        for title, start, end in sections:
            if start <= last_record < end:
                return _tail_of(lines, start, end), None
        return len(lines), None
    for title, start, end in sections:
        if title == PUNCH_LIST:
            return _tail_of(lines, start, end), None
    return len(lines), "## %s\n" % PUNCH_LIST


def _tail_of(lines, start, end):
    """The index just past the last non-empty line of a section, so an append lands at its tail."""
    index = end
    while index > start + 1 and not lines[index - 1].strip():
        index -= 1
    return index


def append_at_home(text, block):
    """`text` with `block` placed at the ledger home's tail. Returns the new text."""
    insert, created = ledger_home(text)
    lines = lines_of(text)
    payload = block if block.endswith("\n") else block + "\n"
    piece = lines_of(payload.rstrip("\n"))
    if created:
        tail = lines[insert:]
        head = lines[:insert]
        while head and not head[-1].strip():
            head.pop()
        new = head + ["", created.rstrip("\n")] + piece + tail
    else:
        new = lines[:insert] + piece + lines[insert:]
    out = "\n".join(new)
    if not out.endswith("\n"):
        out += "\n"
    return out


def slice_heading_index(text, slice_name):
    """The index of the `## Slice <X> —` heading for this slice, or None."""
    for index, line in enumerate(lines_of(text)):
        match = SLICE_HEADING.match(line)
        if match and match.group(1).rstrip(":") == slice_name:
            return index
    return None


def card_of(text, slice_name):
    """(current card text or None, index of the `Status:` line or None) for one slice."""
    lines = lines_of(text)
    start = slice_heading_index(text, slice_name)
    if start is None:
        return None, None
    for index in range(start + 1, len(lines)):
        if SECTION.match(lines[index]):
            break
        match = STATUS.match(lines[index])
        if match:
            return match.group(1), index
    return None, None


def set_card(text, slice_name, value):
    """`text` with the slice's `Status:` line set to `value`. The line must already exist: a slice
    with no card is reported, never given one by this station."""
    current, index = card_of(text, slice_name)
    if index is None:
        raise DocumentShape("the slice %r has no `Status:` line in the document" % slice_name)
    lines = lines_of(text)
    lines[index] = "Status: %s" % value
    out = "\n".join(lines)
    return out if out.endswith("\n") else out + "\n"


def feature_of(build_doc):
    """The build doc's identity for the verdict-doc glob."""
    name = os.path.splitext(os.path.basename(build_doc))[0]
    match = PLAN_NAME.match(name)
    if match:
        return match.group("topic")
    if name.endswith("-build-plan"):
        return name[:-len("-build-plan")]
    return name


def slice_token(slice_name):
    return str(slice_name).strip().lower().replace(" ", "-")


def verdict_doc_candidates(workspace, build_doc, slice_name):
    """Every existing `docs/reviews/*-signoff-<feature>-<slice>.md`, sorted."""
    folder = os.path.join(workspace, "docs", "reviews")
    suffix = "-signoff-%s-%s.md" % (feature_of(build_doc), slice_token(slice_name))
    if not os.path.isdir(folder):
        return []
    return sorted("docs/reviews/" + name for name in os.listdir(folder) if name.endswith(suffix))


def verdict_doc_path(workspace, build_doc, slice_name, run_date):
    """(workspace-relative path, existed): the slice's verdict doc, appended to or created."""
    found = verdict_doc_candidates(workspace, build_doc, slice_name)
    if len(found) == 1:
        return found[0], True
    if len(found) > 1:
        raise DocumentShape("the verdict-doc glob matched %d files: %s"
                            % (len(found), ", ".join(found)))
    return ("docs/reviews/%s-signoff-%s-%s.md"
            % (run_date, feature_of(build_doc), slice_token(slice_name))), False


def verdict_doc_text(existing, build_doc, slice_name, run_date, verdict, block, method_lines):
    """The verdict doc after this run's block. Additive: an earlier run's text is never rewritten.

    The block is the component's rendering, copied whole, so `mirrors` reads the twin blocks as
    `same`. The verdict word and the method sit outside the block, where they are this station's
    record and not a record line.
    """
    head = existing
    if not head:
        head = ("# Sign-off: %s, slice %s\n\n"
                "Verdict docs are records of this station's inspections of one slice. Each run\n"
                "appends; nothing here is ever rewritten. The build doc holds the working state.\n"
                % (build_doc, slice_name))
    if head and not head.endswith("\n"):
        head += "\n"
    piece = ["", "## %s — sign-off: %s" % (run_date, slice_name), "",
             "Verdict: %s" % verdict, ""]
    piece.extend(method_lines)
    piece.append("")
    out = head + "\n".join(piece) + "\n" + block.strip("\n") + "\n"
    return out


def write_text(workspace, rel, text):
    path = os.path.join(workspace, rel)
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    canon.atomic_write(path, text)
    return path


def read_text(workspace, rel):
    path = os.path.join(workspace, rel)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()
