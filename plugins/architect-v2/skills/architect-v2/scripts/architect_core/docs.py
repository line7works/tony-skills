"""The architecture doc: rendered from the answer, continued in place, never rewritten (E14-12, E14-1).

A first run renders the whole doc through `station_core/templates.render_architecture_doc` and
`render_run_block`. A re-run continues the living doc it harvested:

- the title stays; the three header lines are this run's (`Scope doc:` or `Docless:`, then
  `Blind review:`, then `Artifact:` when a URL is recorded), in that order;
- in `## Walkthrough target` and `## v0 drawing`, a label line whose value changed is struck
  through (`~~...~~`) and the new line goes below it; an unchanged one stays;
- `## Poured concrete (one-way doors)` and `## Deferred` are the answer's entries in order: a new
  line, a prior line carried as it stands, or a prior line struck;
- `## Run log` keeps every block byte for byte and gains `### Run <N>`
  (`station_core/runlog.append_run`, N one more than the highest).

`losses(before, after)` is the no-loss check: `runlog.losses` (a prior run-log block dropped or
changed, a prior poured-concrete line dropped) and, for every other line of the prior doc outside
the header, that it survives as it was or struck through.
"""
from station_core import runlog, templates

from .common import D, HEADER_LABELS, M

POURED = "## Poured concrete (one-way doors)"
DEFERRED = "## Deferred"
WALK = "## Walkthrough target"
DRAWING = "## v0 drawing"
RUN_LOG = "## Run log"
NA = "n/a %s exit ramp" % D


class DocRefused(ValueError):
    """The answer names a prior line the living doc does not hold, or the doc cannot be continued."""

    def __init__(self, rule, message):
        ValueError.__init__(self, message)
        self.rule = rule


# ---- values -------------------------------------------------------------------------------------

def must_value(walkthrough):
    return "; ".join(walkthrough["must"])


def walkthrough_line(walkthrough):
    return "Who: %s  %s  When: %s  %s  Must be able to: %s" % (
        walkthrough["who"], M, walkthrough["when"], M, must_value(walkthrough))


def components_value(components):
    return "; ".join("%s (serves: %s)" % (c["name"], c["serves"]) for c in components) or "none"


def exit_ramp_value(exit_ramp):
    if exit_ramp["continued"]:
        return "system %s the interview continued; %s" % (D, exit_ramp["why"])
    return "no system %s the interview ended here; %s" % (D, exit_ramp["why"])


def step31(answer):
    if not answer["exit_ramp"]["continued"]:
        return NA
    w = answer["walkthrough"]
    return "%s, %s: %s" % (w["who"], w["when"], must_value(w))


def step32(answer):
    if not answer["exit_ramp"]["continued"]:
        return NA
    shown = "; ".join("%s (%s)" % (c["name"], ", ".join(c["categories"])) for c in answer["candidates"])
    rejected = ", ".join("%s %s %s" % (r["name"], D, r["why"]) for r in answer["rejected"]) or "none"
    return "%s; chosen: %s; rejected: %s" % (shown, answer["pick"], rejected)


def step33(answer):
    if not answer["exit_ramp"]["continued"] or not answer.get("doors"):
        return NA
    return answer["doors"]["settled"]


def blind_review_value(review, takes, workspace):
    from .common import display
    outcome = review["outcome"]
    if outcome == "declined":
        return "declined %s" % review["date"]
    if outcome == "failed":
        return "failed %s %s %s" % (review["date"], D, review["reason"])
    if outcome == "not-offered":
        return "none %s docless" % D
    if outcome == "done":
        return ", ".join("%s (%s, %s)" % (display(t["path"], workspace), t["model"], t["date"]) for t in takes)
    return "none yet"


def rulings_value(review, rulings, passed):
    outcome = review["outcome"]
    if outcome == "declined":
        head = "declined"
    elif outcome == "failed":
        head = "failed %s %s" % (D, review["reason"])
    elif outcome == "not-offered":
        head = "not offered %s docless" % D
    elif outcome == "done":
        n = len(rulings)
        head = "blind review: agreed on %s; %d disagreement%s" % (review["spine"], n, "" if n == 1 else "s")
        if n:
            head += ": " + "; ".join("%d. %s: %s (%s)" % (i, r["disagreement"], r["ruling"], ", ".join(r["reviewers"]))
                                     for i, r in enumerate(rulings, 1))
    else:
        head = "none yet"
    tail = ", ".join("%s (%s)" % (row["id"], row["text"]) for row in passed) or "none"
    return "%s; passed forward untouched: %s" % (head, tail)


def passed_forward(ledger, answer):
    """Every decided ledger line the answer's questions did not touch (all of them, in an accepted
    answer, since touching one is refused), in ledger order."""
    touched = set()
    for q in answer["questions"]:
        touched.update(q.get("touches") or [])
    return [row for row in ledger if row["tag"] == "decided" and row["id"] not in touched]


def entry_line(entry):
    """The section line of one poured-concrete or deferred entry, without its '- '."""
    if "carried" in entry:
        return entry["carried"]
    if "strike" in entry:
        return runlog.strike("- " + entry["strike"])[2:]
    return entry["text"]


def section_items(answer, key):
    items = [entry_line(e) for e in answer[key]]
    if key == "deferred":
        items += ["NEEDS CHECK: %s" % line["text"] for line in answer["lines"]]
    return items


def run_block(answer, n, date, ledger, takes):
    return templates.render_run_block(n, date, answer["trigger"], exit_ramp_value(answer["exit_ramp"]),
                                      step31(answer), step32(answer), step33(answer),
                                      rulings_value(answer["review"], answer["rulings"], passed_forward(ledger, answer)),
                                      answer["changed"])


# ---- the living doc -----------------------------------------------------------------------------

def split(text):
    """(title index, header lines, [(heading, body lines)]) of an LF document."""
    lines = text.split("\n")
    first = next(i for i, l in enumerate(lines) if l.strip())
    header, sections = [], []
    index = first + 1
    while index < len(lines) and not lines[index].startswith("## "):
        header.append(lines[index])
        index += 1
    while index < len(lines):
        heading = lines[index]
        body = []
        index += 1
        while index < len(lines) and not lines[index].startswith("## "):
            body.append(lines[index])
            index += 1
        sections.append((heading, body))
    return lines[:first + 1], header, sections


def artifact_url(text):
    title, header, sections = split(text)
    for line in header:
        if line.startswith("Artifact: "):
            return line[len("Artifact: "):].strip() or None
    return None


def items_of(text, heading):
    """The '- ' lines of one section of `text`, without the '- '."""
    title, header, sections = split(text)
    for name, body in sections:
        if name == heading:
            return [line[2:] for line in body if line.startswith("- ")]
    return []


def prior_line_refusals(answer, living_text):
    """Every carried or struck entry must name a line of the living doc's section (a struck one an
    unstruck line); a first run has no prior line to name."""
    out = []
    for key, heading in (("poured_concrete", POURED), ("deferred", DEFERRED)):
        held = items_of(living_text, heading) if living_text is not None else []
        for entry in answer[key]:
            if "carried" in entry and entry["carried"] not in held:
                out.append(("unknown-prior-line", "%s carries %r, which the living doc's %s section does not hold"
                            % (key, entry["carried"], heading[3:])))
            if "strike" in entry and entry["strike"] not in held:
                out.append(("unknown-prior-line", "%s strikes %r, which is no unstruck line of the living doc's %s "
                            "section" % (key, entry["strike"], heading[3:])))
    return out


def _replace_label(body, label, new_line):
    for index, line in enumerate(body):
        if line.startswith(label):
            if line == new_line:
                return body
            return body[:index] + [runlog.strike(line), new_line] + body[index + 1:]
    raise DocRefused("unknown-prior-line", "the living doc holds no %r line to continue" % label)


def _section_body(items, trailing):
    body = ["- %s" % item for item in items]
    return body + ([""] if trailing else [])


def header_lines(scope_display, docless_reason, blind, artifact):
    lines = ["Scope doc: %s" % scope_display if docless_reason is None else "Docless: %s" % docless_reason,
             "Blind review: %s" % blind]
    if artifact:
        lines.append("Artifact: %s" % artifact)
    return lines


def build(answer, values):
    """The whole proposed doc. `values`: n, date, ledger, takes, workspace, scope_display (or None),
    docless_reason (or None), artifact (or None), living_text (or None)."""
    blind = blind_review_value(answer["review"], values["takes"], values["workspace"])
    block = run_block(answer, values["n"], values["date"], values["ledger"], values["takes"])
    w = answer["walkthrough"]
    living = values.get("living_text")
    if living is None:
        return templates.render_architecture_doc(
            answer["project"], values["date"], blind, w["who"], w["when"], must_value(w),
            components_value(answer["components"]), answer["data_flow"], answer["diagram"],
            section_items(answer, "poured_concrete"), section_items(answer, "deferred"), [block],
            scope_doc=values["scope_display"] if values["docless_reason"] is None else None,
            docless=values["docless_reason"], artifact=values["artifact"])
    title, header, sections = split(living)
    out = list(title) + [""] + header_lines(values["scope_display"], values["docless_reason"], blind,
                                            values["artifact"]) + [""]
    for position, (heading, body) in enumerate(sections):
        trailing = position < len(sections) - 1
        if heading == WALK:
            body = _replace_label(body, "Who:", walkthrough_line(w))
        elif heading == DRAWING:
            body = _replace_label(body, "Components:", "Components: %s" % components_value(answer["components"]))
            body = _replace_label(body, "Data flow:", "Data flow: %s" % answer["data_flow"])
            body = _replace_label(body, "Diagram:", "Diagram: %s" % answer["diagram"])
        elif heading == POURED:
            body = _section_body(section_items(answer, "poured_concrete"), trailing)
        elif heading == DEFERRED:
            body = _section_body(section_items(answer, "deferred"), trailing)
        out += [heading] + body
    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    return runlog.append_run(text, block)


def losses(before, after):
    found = list(runlog.losses(before, after))
    kept = set(after.split("\n"))
    title, header, sections = split(before)
    for line in title + header:
        if line.strip() and not line.startswith(HEADER_LABELS) and line not in kept:
            found.append("the line %r of the prior doc's head is gone; the header is Scope doc (or Docless), "
                         "Blind review and Artifact, and nothing else is dropped" % line)
    for heading, body in sections:
        for line in [heading] + body:
            if not line.strip() or (heading == POURED and line.startswith("- ")):
                continue  # a poured-concrete line is runlog.losses' to name
            if line not in kept and runlog.strike(line) not in kept:
                found.append("the line %r of the prior doc is gone; a superseded line is struck through, never "
                             "deleted" % line)
    return found


def counts(text, components):
    return {"components": len(components),
            "poured": sum(1 for item in items_of(text, POURED) if not item.startswith("~~")),
            "deferred": sum(1 for item in items_of(text, DEFERRED) if not item.startswith("~~"))}
