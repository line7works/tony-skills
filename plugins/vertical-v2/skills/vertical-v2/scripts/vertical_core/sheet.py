"""The repo's inspection sheet, `REVIEW.md` (contract section 6; the sheet test signoff-v2's contract
section 13 states, restated here in this core's words).

The sheet is read from the reviewed commit only, never from the working tree (A4, B1): `packet.Snapshot`
hands `parse` the bytes the commit stores for a regular file `REVIEW.md` at its root, or nothing, and an
absent or non-regular one in that commit means no sheet. A file named `REVIEW.md` is the sheet only when it carries the three headings
`## Passes`, `## Severity bar` and `## Repo-specific checks` AND every non-blank line under `## Passes`
reads `- <name>: on` or `- <name>: off`, with an optional parenthetical. Anything else under that name is
`present but not the kit sheet`, and the defaults apply. The four passes the sheet may name are
`correctness`, `security`, `accessibility` and `data-safety`; another name is reported as unknown and
ignored. `spec` and `seams` are the loop's own lenses and no sheet turns them off.
"""
import re

PASSES = ("correctness", "security", "accessibility", "data-safety")
HEADINGS = ("## Passes", "## Severity bar", "## Repo-specific checks")
PASS_LINE = re.compile(r"^- ([a-z][a-z-]*): (on|off)(?: \((.+)\))?\s*$")


def _sections(text):
    out = {}
    current = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current = line
            out.setdefault(current, [])
        elif current is not None:
            out[current].append(line)
    return out


def absent():
    return {"state": "absent", "passes": [], "unknown": [], "skipped": [], "checks": [], "bar": [], "text": None}


def parse(text):
    """{"state", "passes": [{"pass", "on", "reason"}], "unknown": [...], "skipped": [...], "checks": [...],
    "bar": [...], "text"} for the commit's `REVIEW.md` text (None: no regular file there); the state is
    `read`, `present but not the kit sheet` or `absent`."""
    empty = absent()
    if text is None:
        return empty
    sections = _sections(text)
    not_sheet = dict(empty, state="present but not the kit sheet", text=text)
    if any(h not in sections for h in HEADINGS):
        return not_sheet
    passes, unknown = [], []
    for line in sections["## Passes"]:
        if not line.strip():
            continue
        match = PASS_LINE.match(line)
        if not match:
            return not_sheet
        name, state, reason = match.group(1), match.group(2), match.group(3)
        if name not in PASSES:
            unknown.append(name)
            continue
        passes.append({"pass": name, "on": state == "on", "reason": reason})
    checks = [line[2:].strip() for line in sections["## Repo-specific checks"] if line.startswith("- ") and line[2:].strip()]
    bar = [line for line in sections["## Severity bar"] if line.strip()]
    skipped = [{"pass": p["pass"], "reason": p["reason"] or "marked off"} for p in passes if not p["on"]]
    return {"state": "read", "passes": passes, "unknown": unknown, "skipped": skipped, "checks": checks, "bar": bar,
            "text": text}


def lenses(depth, sheet):
    """The lens set: the depth's, less the sheet's passes marked off, plus its passes marked on."""
    out = ["spec", "correctness", "seams"]
    if depth == "DEEP":
        out += ["security", "tests"]
    for entry in sheet.get("passes") or []:
        if not entry["on"] and entry["pass"] in out:
            out.remove(entry["pass"])
        elif entry["on"] and entry["pass"] not in out:
            out.append(entry["pass"])
    return out


def line(sheet):
    """The VERTICAL block's `REVIEW.md:` line body, v1's form."""
    if sheet["state"] == "absent":
        return "absent \u2014 defaults"
    if sheet["state"] != "read":
        return "present but not the kit sheet \u2014 defaults"
    skipped = ", ".join("%s (%s)" % (s["pass"], s["reason"]) for s in sheet["skipped"]) or "none skipped"
    head = "read \u2014 passes skipped: %s" % skipped if sheet["skipped"] else "read \u2014 passes skipped: none skipped"
    return "%s · %d repo-specific checks tried" % (head, len(sheet["checks"]))
