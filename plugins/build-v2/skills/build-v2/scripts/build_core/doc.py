"""The build doc, read for its STRUCTURE: slices, cards, and what each slice names.

The spec is the only source of requirements (v1 build, "The spine"), so everything the contract
phase writes comes from the document and nothing from a conversation. What this module reads:

    ## Slice <name> — <title>     a slice heading
    Status: <text>                that slice's card, the one line this core ever writes
    Footprint:                    the paths the slice names: the scope the source set is judged against
    Requirements:                 what the slice asks for
    Checks:                       `<name>: <command>`, the checks the slice names
    Not in this slice:            the boundaries the slice states

Records are NOT read here. A finding, a recheck line, a waiver and a reopening are the records
component's, read through `records.py state`, and the punch list in the document is a rendering
of them. This module never parses one, which is why a document whose records the importer
cannot place is a stop (amendment A3 item 3) rather than something this core reads its own way.

`set_status` replaces the text after `Status: ` on one slice's card line and nothing else, and
the file keeps its trailing newline. That single line is the only byte this core writes into a
workspace.
"""
import os
import re

SLICE_HEADING = re.compile(r"^##\s+Slice\s+(\S+)\s*(?:[—–-]+\s*(.*?))?\s*$")
ANY_HEADING = re.compile(r"^#{1,6}\s")
STATUS = re.compile(r"^(\s*Status:\s*)(.*?)(\s*)$")
LABEL = re.compile(r"^([A-Z][A-Za-z ]*):\s*$")
BULLET = re.compile(r"^[-*]\s+(.*?)\s*$")
CHECK = re.compile(r"^([^:]+?)\s*:\s*(.+?)\s*$")

LABELS = {
    "footprint": "footprint",
    "requirements": "requirements",
    "checks": "checks",
    "not in this slice": "not_in_slice",
    "depends on": "depends_on",
}

CARD_VALUES = ("not started", "built", "rejected", "signed off with conditions", "signed off", "none")
"""The pilot's six card values, which the records component's `card_value` enum publishes. A
`Status:` text that is not one of them reads as `none` there, and this core never writes one."""


class DocumentError(RuntimeError):
    """The document is not there, or it does not carry the slice the input names."""


def read(workspace, document):
    """The document's text. A document that is not there is a stop, never an empty one."""
    path = os.path.join(workspace, document)
    if not os.path.isfile(path):
        raise DocumentError("the build doc %s is not in the workspace" % document)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def parse(text):
    """Every slice of the document, in file order.

    Each slice: `{name, title, line, status_line, status, sections}` where `sections` holds the
    labelled lists this module knows, each a list of the bullet lines under it.
    """
    lines = text.split("\n")
    slices = []
    current = None
    label = None
    for index, line in enumerate(lines):
        heading = SLICE_HEADING.match(line)
        if heading:
            current = {"name": heading.group(1), "title": (heading.group(2) or "").strip(),
                       "line": index + 1, "status_line": None, "status": None,
                       "sections": {}}
            slices.append(current)
            label = None
            continue
        if ANY_HEADING.match(line):
            current = None
            label = None
            continue
        if current is None:
            continue
        status = STATUS.match(line)
        if status and current["status_line"] is None:
            current["status_line"] = index + 1
            current["status"] = status.group(2)
            label = None
            continue
        named = LABEL.match(line)
        if named:
            label = LABELS.get(named.group(1).strip().lower())
            if label:
                current["sections"].setdefault(label, [])
            continue
        bullet = BULLET.match(line)
        if bullet and label:
            current["sections"][label].append(bullet.group(1))
            continue
        if line.strip() and not bullet:
            label = None
    return slices


def find_slice(text, name):
    """One slice by name. A slice the document does not carry is a stop (v1 build, step 1)."""
    for entry in parse(text):
        if entry["name"] == name:
            return entry
    known = ", ".join(e["name"] for e in parse(text)) or "none"
    raise DocumentError("the build doc carries no slice %r (it carries: %s)" % (name, known))


def named_paths(entry):
    """The slice's `Footprint:` entries: the paths the slice names. The scope of the build."""
    return list(entry["sections"].get("footprint") or [])


def not_in_slice(entry):
    """The slice's stated boundaries. Reported beside an out-of-scope path, never the test for one:
    the test is the footprint, so a path the slice mentions nowhere is out of scope too."""
    return list(entry["sections"].get("not_in_slice") or [])


def requirements(entry):
    return list(entry["sections"].get("requirements") or [])


def checks(entry):
    """`[{"name", "command"}]` from the `Checks:` list, in document order.

    A line with no `<name>: <command>` shape keeps the whole line as the name and carries no
    command, so a malformed check is visible rather than dropped.
    """
    out = []
    for row in entry["sections"].get("checks") or []:
        match = CHECK.match(row)
        if match:
            out.append({"name": match.group(1).strip(), "command": match.group(2).strip()})
        else:
            out.append({"name": row.strip(), "command": None})
    return out


def _normal(value):
    """A path with only its literal leading `./` segments removed (Astra's F14).

    A filename-leading dot is part of the name: `.config.env` and `config.env` are two distinct
    paths, so `lstrip("./")`, which strips any run of `.` and `/` characters, is never used here.
    """
    value = value.strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def in_named_paths(path, names):
    """Is one source-set path inside the paths the slice names?

    A named path is a file when it names a file and a directory prefix when it ends in `/` or
    when the source path sits under it as a directory. Nothing else matches: a path the slice
    does not name is out of scope, and this function never guesses a relationship from a shared
    prefix of a file name (`src/a.py` is not inside `src/a`), and a leading dot is part of a name
    (`.config.env` is not `config.env`).
    """
    normal = _normal(path)
    for name in names:
        candidate = _normal(name)
        if not candidate:
            continue
        if candidate.endswith("/"):
            if normal.startswith(candidate):
                return True
            continue
        if normal == candidate:
            return True
        if normal.startswith(candidate + "/"):
            return True
    return False


def set_status(text, entry, value):
    """The document with one slice's `Status:` text replaced, and nothing else changed.

    Returns the new text. The line keeps its leading whitespace, its `Status: ` prefix and its
    trailing whitespace; every other byte of the file is the byte it was.
    """
    if entry["status_line"] is None:
        raise DocumentError("slice %s has no `Status:` line, so its card cannot be set" % entry["name"])
    lines = text.split("\n")
    index = entry["status_line"] - 1
    match = STATUS.match(lines[index])
    if not match:
        raise DocumentError("line %d of the build doc is not a `Status:` line" % entry["status_line"])
    lines[index] = "%s%s%s" % (match.group(1), value, match.group(3))
    return "\n".join(lines)
