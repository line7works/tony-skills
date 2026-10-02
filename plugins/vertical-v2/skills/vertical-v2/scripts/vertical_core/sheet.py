"""The repo's inspection sheet, `REVIEW.md` (contract section 6; the sheet test signoff-v2's contract
section 13 states, restated here in this core's words).

A file named `REVIEW.md` at the workspace root is the sheet only when it carries the three headings
`## Passes`, `## Severity bar` and `## Repo-specific checks` AND every non-blank line under `## Passes`
reads `- <name>: on` or `- <name>: off`, with an optional parenthetical. Anything else under that name is
`present but not the kit sheet`, and the defaults apply. The four passes the sheet may name are
`correctness`, `security`, `accessibility` and `data-safety`; another name is reported as unknown and
ignored. `spec` and `seams` are the loop's own lenses and no sheet turns them off.
"""
import os
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


def read(workspace):
    """{"state", "passes": [{"pass", "on", "reason"}], "unknown": [...], "skipped": [...], "checks": [...],
    "bar": [...], "text"}; the state is `read`, `present but not the kit sheet` or `absent`."""
    path = os.path.join(workspace, "REVIEW.md")
    empty = {"state": "absent", "passes": [], "unknown": [], "skipped": [], "checks": [], "bar": [], "text": None}
    if not os.path.isfile(path) or os.path.islink(path):
        return empty
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
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
