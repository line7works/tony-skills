"""The repo's inspection sheet, `REVIEW.md`, read as v1 signoff reads it.

v1 Step 1's sheet test is mechanical, so it belongs in a script rather than in prose. A file is
the sheet only when it carries the template's three headings — `## Passes`, `## Severity bar`,
`## Repo-specific checks` — AND every `## Passes` line reads `- <name>: on` or `- <name>: off`
with an optional parenthetical. Anything else under that name is NOT the sheet: the run uses this
skill's defaults and reports `present but not the kit sheet`. The file is the repo's and is never
overwritten by this core.

Pick P5 keeps every rule of v1's word for word:

- a pass name outside the four the template carries is reported as unknown and ignored;
- a pass marked `off` never runs, even at DEEP, and the verdict names the skip with its reason;
- `spec` and `seams` are the loop's own and are not passes: nothing here turns them off;
- `correctness: off` is honoured for the lens and reported, and the `spec` lens still runs.

What this core does NOT do is write the file. v1 writes it on exactly two occasions — the
first-run render on the user's word, and the second-failure append with its `verified:` stamp —
and both need a judgement this core does not hold: the user's word in the first case, and a
comparison across earlier verdict docs in the second. `SKILL.md` carries both as the executor's
steps, so the policy is unchanged and the writes stay where a person can authorize them.
"""
import os
import re

HEADINGS = ("## Passes", "## Severity bar", "## Repo-specific checks")
KNOWN_PASSES = ("correctness", "security", "accessibility", "data-safety")
DEFAULT_PASSES = {"correctness": True, "security": True, "accessibility": True,
                  "data-safety": True}
PASS_LINE = re.compile(r"^-\s*(?P<name>[A-Za-z][A-Za-z0-9_-]*)\s*:\s*(?P<state>on|off)\s*"
                       r"(?:\((?P<why>[^)]*)\))?\s*$")
BULLET = re.compile(r"^-\s+(?P<text>.*\S)\s*$")

# The lenses of the loop itself. `spec` matters most and is the one a generic code review misses.
LOOP_LENSES = ("spec", "seams")
SHEET_LENSES = {"correctness": "correctness", "security": "security",
                "accessibility": "accessibility", "data-safety": "data-safety"}


def sections(text):
    """{heading: [lines]} for every `## ` section of the document."""
    out, current = {}, None
    for line in text.split("\n"):
        if line.startswith("## "):
            current = line.rstrip()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)
    return out


def read(workspace, name="REVIEW.md"):
    """What the repo's sheet says, or the defaults and why they are being used."""
    path = os.path.join(workspace, name)
    base = {"path": name, "is_sheet": False, "state": "absent",
            "passes": dict(DEFAULT_PASSES), "skipped": [], "skip_reasons": {},
            "unknown_passes": [], "bar": [], "repo_checks": []}
    if not os.path.isfile(path):
        return base
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        base["state"] = "present but not the kit sheet"
        return base

    found = sections(text)
    if not all(heading in found for heading in HEADINGS):
        base["state"] = "present but not the kit sheet"
        return base

    passes, skip_reasons, unknown = {}, {}, []
    for line in found["## Passes"]:
        if not line.strip():
            continue
        match = PASS_LINE.match(line.strip())
        if not match:
            # A pass with no on/off means the file is not the sheet, whatever else it holds.
            base["state"] = "present but not the kit sheet"
            return base
        name_of = match.group("name")
        if name_of not in KNOWN_PASSES:
            unknown.append(name_of)
            continue
        passes[name_of] = match.group("state") == "on"
        if match.group("state") == "off" and match.group("why"):
            skip_reasons[name_of] = match.group("why").strip()

    bar = [m.group("text") for m in
           (BULLET.match(line.strip()) for line in found["## Severity bar"]) if m]
    checks = [m.group("text") for m in
              (BULLET.match(line.strip()) for line in found["## Repo-specific checks"]) if m]
    checks = [row for row in checks if not row.startswith("(")]

    return {
        "path": name,
        "is_sheet": True,
        "state": "read",
        "passes": passes or dict(DEFAULT_PASSES),
        "skipped": sorted(name for name, on in passes.items() if not on),
        "skip_reasons": skip_reasons,
        "unknown_passes": sorted(unknown),
        "bar": bar,
        "repo_checks": checks,
    }


def lenses_for(depth, passes):
    """v1 Step 3's lens sets, with the sheet's passes applied.

    LIGHT is one fused reviewer and never grows a second. LEAN is the loop's two lenses plus the
    passes that are on. DEEP adds `tests`, and `security` when the sheet leaves it on.
    """
    passes = dict(passes or DEFAULT_PASSES)
    on = [SHEET_LENSES[name] for name in KNOWN_PASSES
          if passes.get(name, DEFAULT_PASSES.get(name, False)) and name in SHEET_LENSES]
    if depth == "LIGHT":
        fused = ["spec"] + [name for name in on if name == "correctness"]
        return [" + ".join(fused)]
    lenses = ["spec", "correctness", "seams"] if depth in ("LEAN", "DEEP") else list(LOOP_LENSES)
    lenses = [name for name in lenses if name not in SHEET_LENSES or name in on]
    for name in on:
        if name not in lenses and (depth == "DEEP" or name not in ("security",)):
            lenses.append(name)
    if depth == "DEEP":
        if "tests" not in lenses:
            lenses.append("tests")
    return lenses


def reported(got):
    """The block the result carries, and the line the chat block prints."""
    return {"path": got["path"], "state": got["state"], "is_sheet": got["is_sheet"],
            "skipped": list(got["skipped"]), "skip_reasons": dict(got["skip_reasons"]),
            "unknown_passes": list(got["unknown_passes"]),
            "repo_checks": list(got["repo_checks"]), "bar": list(got["bar"])}


def chat_line(got):
    if got["state"] == "absent":
        return "REVIEW.md: absent — defaults"
    if not got["is_sheet"]:
        return "REVIEW.md: present but not the kit sheet — defaults"
    skips = ", ".join("%s (%s)" % (name, got["skip_reasons"].get(name, "no reason given"))
                      for name in got["skipped"]) or "none skipped"
    unknown = (" · unknown passes ignored: %s" % ", ".join(got["unknown_passes"])
               if got["unknown_passes"] else "")
    return ("REVIEW.md: read — passes skipped: %s · %d repo-specific check(s) tried%s"
            % (skips, len(got["repo_checks"]), unknown))
