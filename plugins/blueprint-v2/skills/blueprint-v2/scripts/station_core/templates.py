"""The load-bearing forms: parse, render and check (ruling E14-12). One module for the four cores.

The forms live in `references/templates/<name>.md`, each the v1 station's fenced form byte for
byte inside the one block fenced as `form`; the text beside it is v1's reading, for the executor,
and is never rendered. This module:

- loads a form (`form(name)`) and its reading (`reading(name)`);
- parses a document into its lines and an outline of the labels and headings it holds, and renders
  it back byte for byte (`parse`, `render`): the round trip changes nothing, whatever the line
  endings and whether or not the file ends in a newline;
- checks a document against its form's labels and headings (`check`): a label missing, renamed or
  out of order, a changed title form, a heading the form does not have, a stamp line that does not
  read the stamp form, an architecture doc's walkthrough target line without its `Who:`, `When:`
  and `Must be able to:` fields in order and each filled, each one finding with its line;
- renders a document from values (`render_scope_doc`, `render_build_doc`,
  `render_architecture_doc`, `render_run_block`, `render_ledger_line`), laid out exactly as the
  form lays it out, so the forms given their own placeholders render back to themselves;
- renders and parses the lines inspect writes itself (`render_stamp`, `render_question`,
  `render_clean`, `parse_line`, `render_line`); a QUESTION line with a blank path, line, what or
  model, or a clean line with a blank model, is not a line of the form and parses to None.

It never judges what a document says (E14-4): it holds the form, nothing more.
"""
import os
import re

from . import validate

NAMES = ("scope-doc", "architecture-doc", "build-doc", "inspect-lines")
D = "\u2014"     # the dash the v1 forms use as their separator; carried, never typed
M = "·"          # the middle dot of the v1 line forms
FENCE_OPEN = "```form\n"
FENCE_CLOSE = "```\n"
PARKED_REASONS = ("needs research", "needs prototype")
PARKED_WAITING = "waiting on "
LEDGER_SECTIONS = ("## Build assumptions", "## Deviations", "## Discovered", "## Handoffs",
                   "## Punch list")


class FormError(ValueError):
    """A template that cannot be read, or a value a form cannot carry."""


# ---- the templates ------------------------------------------------------------------------------

def template_path(name, root=None):
    if name not in NAMES:
        raise FormError("no template named %r (the four are %s)" % (name, ", ".join(NAMES)))
    return os.path.join(validate.references_dir(root), "templates", name + ".md")


def _template_text(name, root=None):
    try:
        with open(template_path(name, root), "r", encoding="utf-8", newline="") as fh:
            return fh.read()
    except OSError as exc:
        raise FormError("reference unavailable: references/templates/%s.md (%s)" % (name, exc))


def form(name, root=None):
    """The form: the bytes between the `form` fence and its closing fence, final newline kept."""
    text = _template_text(name, root)
    start = text.find(FENCE_OPEN)
    if start < 0 or text.count(FENCE_OPEN) != 1:
        raise FormError("references/templates/%s.md holds no single `form` block" % name)
    start += len(FENCE_OPEN)
    end = text.find("\n" + FENCE_CLOSE, start - 1)
    if end < 0:
        raise FormError("references/templates/%s.md: the `form` block is not closed" % name)
    return text[start:end + 1]


def reading(name, root=None):
    """v1's words about the form, as the template quotes them (never rendered)."""
    text = _template_text(name, root)
    marker = "\n## Reading"
    start = text.find(marker)
    if start < 0:
        raise FormError("references/templates/%s.md holds no reading" % name)
    body = text[text.find("\n", start + 1) + 1:]
    stop = body.find("\n## ")
    return body if stop < 0 else body[:stop + 1]


# ---- parse and render ---------------------------------------------------------------------------

def parse(name, text):
    """{"kind", "lines", "outline"}: the lines with their endings, and what each one is."""
    if name not in NAMES:
        raise FormError("no template named %r" % name)
    lines = text.splitlines(True)
    outline = []
    fence = False
    for index, raw in enumerate(lines, 1):
        line = raw.rstrip("\r\n")
        if line.startswith("```"):
            fence = not fence
            outline.append({"line": index, "role": "fence"})
            continue
        if fence:
            outline.append({"line": index, "role": "text"})
            continue
        if name == "inspect-lines":
            parsed = parse_line(line)
            outline.append({"line": index, "role": parsed["kind"] if parsed else "text"})
            continue
        if line.startswith("# "):
            outline.append({"line": index, "role": "title"})
        elif line.startswith("## "):
            outline.append({"line": index, "role": "heading", "key": line})
        elif line.startswith("### "):
            outline.append({"line": index, "role": "subheading", "key": line})
        else:
            label = _label_of(name, line)
            outline.append({"line": index, "role": "label" if label else "text", "key": label})
    return {"kind": name, "lines": lines, "outline": outline}


def render(parsed):
    """The document, byte for byte as it was parsed."""
    return "".join(parsed["lines"])


# ---- the specs the check reads ------------------------------------------------------------------

SCOPE = {
    "title": re.compile(r"^# .+ %s scope doc \(.+\)$" % D),
    "title_form": "# <Idea> %s scope doc (<date>)" % D,
    "header": [(("Intent:",), True), (("Decisions:",), True), (("Out of scope:",), True),
               (("Research:",), True), (("Open:",), True), (("Next:",), True)],
}
BUILD = {
    "title": re.compile(r"^# .+ %s build plan \(.+\)$" % D),
    "title_form": "# <Feature> %s build plan (<date>)" % D,
    "header": [(("Intent:",), True), (("Constraints:",), True), (("Out of scope:",), True)],
    "slice": re.compile(r"^## Slice (\S+) %s (.+)$" % D),
    "slice_labels": [(("Goal:",), True), (("Requirements:",), True), (("Acceptance criteria:",), True),
                     (("Footprint:",), True), (("Not in this slice:",), True), (("Depends on:",), True),
                     (("Status:",), True)],
    "ledger": LEDGER_SECTIONS,
}
ARCH = {
    "title": re.compile(r"^# .+ %s architecture \(.+\)$" % D),
    "title_form": "# <Project> %s architecture (<date of first run>)" % D,
    "header": [(("Scope doc:", "Docless:"), True), (("Blind review:",), True), (("Artifact:",), False)],
    "sections": [("## Walkthrough target", [(("Who:",), True)]),
                 ("## v0 drawing", [(("Components:",), True), (("Data flow:",), True), (("Diagram:",), True)]),
                 ("## Poured concrete (one-way doors)", []),
                 ("## Deferred", []),
                 ("## Run log", [])],
    "run": re.compile(r"^### Run (\S+) %s (.+?) %s trigger: (.*)$" % (D, D)),
    "run_labels": [(("Exit ramp:",), True), (("Step 3.1 (walkthrough target):",), True),
                   (("Step 3.2 (candidates):",), True), (("Step 3.3 (one-way doors):",), True),
                   (("Rulings:",), True), (("Changed this run:",), True)],
}
SPECS = {"scope-doc": SCOPE, "build-doc": BUILD, "architecture-doc": ARCH}
# the form's `Who: <named real person>  ·  When: <date>  ·  Must be able to: <short list>`
WALKTHROUGH = re.compile(r"Who: (.*?) +%(M)s +When: (.*?) +%(M)s +Must be able to: (.*)" % {"M": M})


def _all_labels(name):
    spec = SPECS.get(name) or {}
    labels = []
    for key in ("header", "slice_labels", "run_labels"):
        for alternatives, _ in spec.get(key, []):
            labels.extend(alternatives)
    for _, slots in spec.get("sections", []):
        for alternatives, _ in slots:
            labels.extend(alternatives)
    return sorted(set(labels), key=len, reverse=True)


def _label_of(name, line):
    for label in _all_labels(name):
        if line.startswith(label):
            return label
    return None


def _check_slots(slots, found, where, first_line):
    """Findings for one context: every required slot present once, in the form's order."""
    findings = []
    index_of = {}
    for position, (alternatives, _) in enumerate(slots):
        for label in alternatives:
            index_of[label] = position
    seen = {}
    order = []
    for line_no, label in found:
        if label not in index_of:
            continue
        position = index_of[label]
        if position in seen:
            findings.append({"line": line_no, "message": "%s: the label '%s' appears twice" % (where, label)})
            continue
        seen[position] = line_no
        order.append((position, line_no, label))
    for position, (alternatives, required) in enumerate(slots):
        if required and position not in seen:
            findings.append({"line": first_line,
                             "message": "%s: missing the label '%s'" % (where, "' or '".join(alternatives))})
    for (pa, _, la), (pb, lb, lbl) in zip(order, order[1:]):
        if pb < pa:
            findings.append({"line": lb, "message": "%s: the label '%s' comes before '%s' in the form"
                                                    % (where, lbl, la)})
    return findings


def check(name, text):
    """[{line, message}]: how `text` departs from the form's labels and headings; [] when it holds."""
    if name not in SPECS:
        raise FormError("check reads the three documents, not %r" % name)
    spec = SPECS[name]
    lines = [raw.rstrip("\r\n") for raw in text.splitlines(True)]
    findings = []
    first = next((i for i, l in enumerate(lines, 1) if l.strip()), None)
    if first is None:
        return [{"line": 1, "message": "the document is empty"}]
    if not spec["title"].match(lines[first - 1]):
        findings.append({"line": first, "message": "the title line does not read '%s'" % spec["title_form"]})

    contexts = [{"kind": "header", "key": "header", "line": first, "labels": []}]
    fence = False
    for line_no, line in enumerate(lines, 1):
        if line_no == first:
            continue
        if line.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        current = contexts[-1]
        if line.startswith("## "):
            contexts.append({"kind": "section", "key": line, "line": line_no, "labels": [], "runs": []})
            continue
        if line.startswith("### "):
            if current.get("kind") in ("section", "run") and name == "architecture-doc":
                section = current if current["kind"] == "section" else current["parent"]
                if section["key"] == "## Run log":
                    run = {"kind": "run", "key": line, "line": line_no, "labels": [], "parent": section}
                    section["runs"].append(run)
                    contexts.append(run)
            continue
        label = _label_of(name, line)
        if label:
            current["labels"].append((line_no, label))
            if name == "architecture-doc" and label == "Who:" and not _walkthrough_holds(line):
                findings.append({"line": line_no, "message": "the walkthrough target requires Who:, When:, and "
                                 "Must be able to: in order, separated by %s, each with a value" % M})
        elif name == "build-doc" and current["kind"] == "header" and line.startswith("Plan: inspected"):
            parsed = parse_line(line)
            if parsed is None or parsed["kind"] != "stamp":
                findings.append({"line": line_no, "message": "a stamp line does not read "
                                 "'Plan: inspected <YYYY-MM-DD> by <model> %s <counts>'" % M})

    header = contexts[0]
    findings += _check_slots(spec["header"], header["labels"], "the header", header["line"])
    sections = [c for c in contexts if c["kind"] == "section"]
    if name == "scope-doc":
        for section in sections:
            findings.append({"line": section["line"], "message": "the form has no section '%s'" % section["key"]})
    elif name == "build-doc":
        findings += _check_build_sections(sections)
    else:
        findings += _check_arch_sections(sections)
    findings.sort(key=lambda f: (f["line"], f["message"]))
    return findings


def _walkthrough_holds(line):
    """The walkthrough target line carries its three fields, in the form's order, each filled."""
    fields = WALKTHROUGH.fullmatch(line)
    return fields is not None and all(value.strip() for value in fields.groups())


def _check_build_sections(sections):
    findings = []
    slices = []
    ledger = []
    for section in sections:
        match = BUILD["slice"].match(section["key"])
        if match:
            if ledger:
                findings.append({"line": section["line"],
                                 "message": "a slice section '%s' comes after the ledger sections" % section["key"]})
            slices.append((section, match))
        elif section["key"] in LEDGER_SECTIONS:
            ledger.append(section)
        else:
            findings.append({"line": section["line"], "message": "the form has no section '%s'" % section["key"]})
    if not slices:
        findings.append({"line": 1, "message": "no '## Slice <name> %s <short name>' section" % D})
    for section, match in slices:
        placeholder = match.group(2) == "..." and not section["labels"]
        if not placeholder:
            findings += _check_slots(BUILD["slice_labels"], section["labels"],
                                     "slice %s" % match.group(1), section["line"])
    keys = [s["key"] for s in ledger]
    for heading in LEDGER_SECTIONS:
        if heading not in keys:
            findings.append({"line": 1, "message": "missing the section '%s'" % heading})
    present = [h for h in keys if h in LEDGER_SECTIONS]
    if present != [h for h in LEDGER_SECTIONS if h in present]:
        findings.append({"line": ledger[0]["line"] if ledger else 1,
                         "message": "the ledger sections are not in the form's order (%s)"
                                    % ", ".join(LEDGER_SECTIONS)})
    return findings


def _check_arch_sections(sections):
    findings = []
    order = [heading for heading, _ in ARCH["sections"]]
    slots = dict(ARCH["sections"])
    keys = [s["key"] for s in sections]
    for section in sections:
        if section["key"] not in slots:
            findings.append({"line": section["line"], "message": "the form has no section '%s'" % section["key"]})
            continue
        findings += _check_slots(slots[section["key"]], section["labels"], section["key"], section["line"])
    for heading in order:
        if heading not in keys:
            findings.append({"line": 1, "message": "missing the section '%s'" % heading})
    present = [k for k in keys if k in slots]
    if present != [h for h in order if h in present]:
        findings.append({"line": 1, "message": "the sections are not in the form's order"})
    for section in sections:
        if section["key"] == "## Run log":
            if not section["runs"]:
                findings.append({"line": section["line"], "message": "the run log holds no '### Run <N>' block"})
            for run in section["runs"]:
                if not ARCH["run"].match(run["key"]):
                    findings.append({"line": run["line"], "message": "a run heading does not read "
                                     "'### Run <N> %s <date> %s trigger: <...>'" % (D, D)})
                findings += _check_slots(ARCH["run_labels"], run["labels"], run["key"], run["line"])
    return findings


# ---- render from values -------------------------------------------------------------------------

def _labelled(label, items):
    items = [i for i in (items or [])]
    if not items:
        return [label]
    if len(items) == 1:
        return ["%s %s" % (label, items[0])]
    return [label] + ["- %s" % i for i in items]


def _one_line(value, what):
    if not isinstance(value, str) or "\n" in value or "\r" in value:
        raise FormError("%s is one line of text" % what)
    return value


def render_ledger_line(text, tag, detail):
    """One `Decisions:` line body (no leading `- `): `<text> \u2014 decided (<source>)`, `<text> \u2014
    assumed (<why>)`, `<text> \u2014 parked: <needs research | needs prototype | waiting on <x>>`."""
    _one_line(text, "a ledger line")
    if not text.strip():
        raise FormError("a ledger line has text")
    if tag in ("decided", "assumed"):
        if not isinstance(detail, str) or not detail.strip():
            raise FormError("a %s line carries its %s" % (tag, "source" if tag == "decided" else "why"))
        return "%s %s %s (%s)" % (text, D, tag, _one_line(detail, "a detail"))
    if tag == "parked":
        ok = detail in PARKED_REASONS or (isinstance(detail, str) and detail.startswith(PARKED_WAITING)
                                          and detail[len(PARKED_WAITING):].strip())
        if not ok:
            raise FormError("a parked line carries one of: needs research, needs prototype, waiting on <x>")
        return "%s %s parked: %s" % (text, D, detail)
    raise FormError("a Decisions line is decided, assumed or parked, not %r" % (tag,))


def render_scope_doc(title, date, intent, decisions, out_of_scope=(), research=(), open_items=(),
                     next_line="/blueprint when ready."):
    lines = ["# %s %s scope doc (%s)" % (title, D, date), "", "Intent: %s" % intent, "Decisions:"]
    lines += ["- %s" % d for d in decisions]
    lines += _labelled("Out of scope:", out_of_scope)
    lines += _labelled("Research:", research)
    lines += _labelled("Open:", open_items)
    lines += ["Next: %s" % next_line]
    return "\n".join(lines) + "\n"


def render_build_doc(title, date, intent, constraints, out_of_scope, slices, stamps=()):
    lines = ["# %s %s build plan (%s)" % (title, D, date), "", "Intent: %s" % intent,
             "Constraints: %s" % constraints]
    lines += _labelled("Out of scope:", out_of_scope)
    lines += list(stamps)
    for s in slices:
        lines += ["", "## Slice %s %s %s" % (s["name"], D, s["short"])]
        if set(s) - {"name", "short"}:
            lines += ["Goal: %s" % s["goal"], "Requirements:"]
            lines += ["- %s" % r for r in s.get("requirements", [])]
            lines += ["Acceptance criteria:"]
            lines += ["- %s %s verify: %s" % (c, D, v) for c, v in s.get("criteria", [])]
            lines += ["Footprint: %s" % s["footprint"], "Not in this slice: %s" % s["not_in_slice"],
                      "Depends on: %s" % s["depends_on"], "Status: %s" % s.get("status", "not started")]
    lines += [""] + list(LEDGER_SECTIONS)
    return "\n".join(lines) + "\n"


def render_run_block(n, date, trigger, exit_ramp, walkthrough, candidates, doors, rulings, changed):
    return "\n".join([
        "### Run %s %s %s %s trigger: %s" % (n, D, date, D, trigger),
        "Exit ramp: %s" % exit_ramp,
        "Step 3.1 (walkthrough target): %s" % walkthrough,
        "Step 3.2 (candidates): %s" % candidates,
        "Step 3.3 (one-way doors): %s" % doors,
        "Rulings: %s" % rulings,
        "Changed this run: %s" % changed,
    ])


def render_architecture_doc(title, date, blind_review, who, when, must, components, data_flow,
                            diagram, poured, deferred, runs, scope_doc=None, docless=None,
                            artifact=None):
    if (scope_doc is None) == (docless is None):
        raise FormError("an architecture doc names its scope doc or its docless reason, one of the two")
    lines = ["# %s %s architecture (%s)" % (title, D, date), ""]
    lines.append("Scope doc: %s" % scope_doc if scope_doc is not None else "Docless: %s" % docless)
    lines.append("Blind review: %s" % blind_review)
    if artifact is not None:
        lines.append("Artifact: %s" % artifact)
    lines += ["", "## Walkthrough target",
              "Who: %s  %s  When: %s  %s  Must be able to: %s" % (who, M, when, M, must),
              "", "## v0 drawing", "Components: %s" % components, "Data flow: %s" % data_flow,
              "Diagram: %s" % diagram, "", "## Poured concrete (one-way doors)"]
    lines += ["- %s" % p for p in poured]
    lines += ["", "## Deferred"]
    lines += ["- %s" % d for d in deferred]
    lines += ["", "## Run log"]
    for index, block in enumerate(runs):
        if index:
            lines.append("")
        lines += block.rstrip("\n").split("\n")
    return "\n".join(lines) + "\n"


# ---- the lines inspect writes itself --------------------------------------------------------------

_COUNT = r"(?:\d+|N)"
STAMP = re.compile(r"^Plan: inspected (?P<date>\d{4}-\d{2}-\d{2}|<YYYY-MM-DD>) by (?P<model>[^\s%(M)s]+) %(M)s "
                   r"(?P<tail>clean|<N BLOCKER %(M)s N MAJOR %(M)s N MINOR>|"
                   r"(?P<b>%(C)s) BLOCKER %(M)s (?P<j>%(C)s) MAJOR %(M)s (?P<n>%(C)s) MINOR"
                   r"(?: %(M)s (?P<q>%(C)s) QUESTION)?)$" % {"M": M, "C": _COUNT})
QUESTION = re.compile(r"^QUESTION %(M)s (?P<path>[^\s%(M)s]+):(?P<line>\d+|<line>) %(M)s (?P<what>.+) "
                      r"%(M)s (?P<model>[^%(M)s]+)$" % {"M": M})
CLEAN = re.compile(r"^clean %s no surviving findings or questions %s (?P<model>[^%s]+)$" % (D, M, M))


def _count(value):
    return int(value) if value is not None and value.isdigit() else value


def render_stamp(date, model, blocker=0, major=0, minor=0, question=0):
    if blocker == major == minor == question == 0:
        return "Plan: inspected %s by %s %s clean" % (date, model, M)
    line = "Plan: inspected %s by %s %s %d BLOCKER %s %d MAJOR %s %d MINOR" % (
        date, model, M, blocker, M, major, M, minor)
    if question:
        line += " %s %d QUESTION" % (M, question)
    return line


def render_question(path, line, what, model):
    return "QUESTION %s %s:%s %s %s %s %s" % (M, path, line, M, what, M, model)


def render_clean(model):
    return "clean %s no surviving findings or questions %s %s" % (D, M, model)


def parse_line(line):
    """The stamp, a QUESTION line or the clean line as a dict, or None for anything else."""
    line = line.rstrip("\r\n")
    match = STAMP.match(line)
    if match:
        tail = match.group("tail")
        counts = None
        if match.group("b") is not None:
            counts = {"BLOCKER": _count(match.group("b")), "MAJOR": _count(match.group("j")),
                      "MINOR": _count(match.group("n"))}
        return {"kind": "stamp", "date": match.group("date"), "model": match.group("model"),
                "tail": tail, "clean": tail == "clean", "counts": counts,
                "question": _count(match.group("q")) if match.group("q") is not None else 0}
    match = QUESTION.match(line)
    if match and all(match.group(key).strip() for key in ("path", "line", "what", "model")):
        return {"kind": "question", "path": match.group("path"), "line": match.group("line"),
                "what": match.group("what"), "model": match.group("model")}
    match = CLEAN.match(line)
    if match and match.group("model").strip():
        return {"kind": "clean", "model": match.group("model")}
    return None


def render_line(parsed):
    if parsed["kind"] == "stamp":
        return "Plan: inspected %s by %s %s %s" % (parsed["date"], parsed["model"], M, parsed["tail"])
    if parsed["kind"] == "question":
        return render_question(parsed["path"], parsed["line"], parsed["what"], parsed["model"])
    if parsed["kind"] == "clean":
        return render_clean(parsed["model"])
    raise FormError("no line form %r" % parsed.get("kind"))
