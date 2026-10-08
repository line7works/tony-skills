"""The load-bearing forms of vertical-v2 (ruling E15-11): rendered and parsed here, and only here.

The verdict doc is one file per build, `docs/reviews/<date>-vertical-<feature>.md`; each run adds one
dated block at its end and never edits an earlier one. A block carries v1's three sections in v1's
order, `### THE VERDICT` (the merged verified findings alone, in the punch-list line form), `### Method
line` and `### Unverified appendix` under v1's banner, byte for byte. A reviewer's raw text sits in
the appendix verbatim between two marker lines; the opening marker carries its length in characters,
so a raw text that imitates the form is read as raw text and nothing else.

The `VERTICAL:` chat block is v1's, byte for byte, dashes included. The em dash in v1's banner, in the
`Dropped:` and `REVIEW.md:` lines of the chat block, and in the build doc's own form are v1 forms
copied byte for byte: the one exception to the no-dash rule (contract section 8). Every renderer here
has a parser, and parse then render gives the bytes back (`scripts/tests/test_forms.py`).
"""
import re

D = "\u2014"
M = "·"
SEP = " %s " % M
BANNER = ("*Raw reviewer output %s unverified. Findings here that are absent from the verdict above were refuted or "
          "could not be verified. Nothing in this appendix has standing.*" % D)
HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2}) %s vertical run (\S+)$" % M)
RAW_OPEN = re.compile(r"^<!-- raw (.+) chars=(\d+) -->$")
TITLE = "# Vertical review %s %%s\n" % M
VERDICTS = ("SIGNED OFF", "SIGNED OFF WITH CONDITIONS", "REJECTED")


class FormError(ValueError):
    """A text that does not read as the form, or a value the form cannot carry."""


def one_line(value, what):
    if not isinstance(value, str) or "\n" in value or "\r" in value or not value.strip():
        raise FormError("%s is one non-blank line of text" % what)
    return value


def _field(value, what):
    one_line(value, what)
    if SEP in value:
        raise FormError("%s holds the line form's separator ' %s '" % (what, M))
    return value


def finding_line(f):
    parts = [f["severity"], "`%s`" % _field(f["location"], "a location"), _field(f["claim"], "a claim"),
             _field(f["scenario"], "a scenario"), _field(", ".join(f["reviewers"]), "the reviewers"), f["stamp"]]
    if f.get("regrade"):
        parts.append("re-graded: %s" % _field(f["regrade"], "a re-grade"))
    return "- " + SEP.join(parts)


def parse_finding(line):
    if not line.startswith("- "):
        raise FormError("a finding line starts with '- ': %r" % line)
    parts = line[2:].split(SEP)
    if len(parts) not in (6, 7) or not (parts[1].startswith("`") and parts[1].endswith("`")):
        raise FormError("a finding line reads '- SEVERITY %s `file:line` %s claim %s scenario %s reviewers %s stamp': %r"
                        % (M, M, M, M, M, line))
    regrade = None
    if len(parts) == 7:
        if not parts[6].startswith("re-graded: "):
            raise FormError("a finding line's seventh field is its re-grade: %r" % line)
        regrade = parts[6][len("re-graded: "):]
    return {"severity": parts[0], "location": parts[1][1:-1], "claim": parts[2], "scenario": parts[3],
            "reviewers": parts[4].split(", "), "stamp": parts[5], "regrade": regrade}


def _list(label, items):
    return ["%s:" % label] + (["- %s" % one_line(i, label) for i in items] or ["- none"])


def render_block(f):
    if f["verdict"] not in VERDICTS:
        raise FormError("a verdict is one of %s" % ", ".join(VERDICTS))
    lines = ["## %s %s vertical run %s" % (f["date"], M, f["run_id"]), "", "### THE VERDICT", "",
             "Verdict: %s" % f["verdict"], "Refuted: %d" % f["refuted"], "", "Findings:"]
    lines += [finding_line(x) for x in f["findings"]] or ["- none"]
    lines += [""] + _list("Repeats", f["repeats"]) + [""] + _list("Misses to verify", f["misses"]) + [""]
    lines += ["Ledger notes: %s" % (one_line(f["ledger_notes"], "the ledger notes") if f["ledger_notes"] else "none"),
              "REVIEW.md: %s" % one_line(f["review_line"], "the REVIEW.md line")]
    lines += ["- %s" % one_line(s, "a sheet line") for s in f["sheet_lines"]]
    lines += ["", "### Method line", ""] + ["- %s" % one_line(m, "a method line") for m in f["method"]]
    lines += ["", "### Unverified appendix", "", BANNER, ""]
    text = "\n".join(lines) + "\n"
    for entry in f["appendix"]:
        label = one_line(entry["label"], "an appendix label")
        text += "<!-- raw %s chars=%d -->\n%s\n<!-- end raw %s -->\n\n" % (label, len(entry["raw"]), entry["raw"], label)
    return text


def _take(lines, index, want):
    if index >= len(lines) or lines[index] != want:
        raise FormError("expected %r at line %d, read %r" % (want, index + 1, lines[index] if index < len(lines) else None))
    return index + 1


def _read_list(lines, index, label):
    index = _take(lines, index, "%s:" % label)
    items = []
    while index < len(lines) and lines[index].startswith("- "):
        items.append(lines[index][2:])
        index += 1
    if items == ["none"]:
        items = []
    return items, index


def parse_block(text, whole=True):
    """The fields of one block (the inverse of `render_block`). With `whole` false, text after the
    block (the next block of a doc) is left unread."""
    marker = "\n### Unverified appendix\n\n%s\n\n" % BANNER
    cut = text.find(marker)
    if cut < 0:
        raise FormError("the block holds no appendix under v1's banner")
    head, rest = text[:cut + 1], text[cut + len(marker):]
    lines = head.split("\n")
    match = HEADING.match(lines[0])
    if not match:
        raise FormError("a block opens with '## <date> %s vertical run <run id>': %r" % (M, lines[0]))
    f = {"date": match.group(1), "run_id": match.group(2)}
    index = _take(lines, 1, "")
    index = _take(lines, index, "### THE VERDICT")
    index = _take(lines, index, "")
    if not lines[index].startswith("Verdict: "):
        raise FormError("expected the Verdict: line")
    f["verdict"] = lines[index][len("Verdict: "):]
    index += 1
    if not lines[index].startswith("Refuted: "):
        raise FormError("expected the Refuted: line")
    f["refuted"] = int(lines[index][len("Refuted: "):])
    index = _take(lines, index + 1, "")
    index = _take(lines, index, "Findings:")
    findings = []
    while lines[index].startswith("- "):
        if lines[index] != "- none":
            findings.append(parse_finding(lines[index]))
        index += 1
    f["findings"] = findings
    index = _take(lines, index, "")
    f["repeats"], index = _read_list(lines, index, "Repeats")
    index = _take(lines, index, "")
    f["misses"], index = _read_list(lines, index, "Misses to verify")
    index = _take(lines, index, "")
    if not lines[index].startswith("Ledger notes: "):
        raise FormError("expected the Ledger notes: line")
    notes = lines[index][len("Ledger notes: "):]
    f["ledger_notes"] = None if notes == "none" else notes
    index += 1
    if not lines[index].startswith("REVIEW.md: "):
        raise FormError("expected the REVIEW.md: line")
    f["review_line"] = lines[index][len("REVIEW.md: "):]
    index += 1
    f["sheet_lines"] = []
    while lines[index].startswith("- "):
        f["sheet_lines"].append(lines[index][2:])
        index += 1
    index = _take(lines, index, "")
    index = _take(lines, index, "### Method line")
    index = _take(lines, index, "")
    f["method"] = []
    while index < len(lines) and lines[index].startswith("- "):
        f["method"].append(lines[index][2:])
        index += 1
    f["appendix"] = []
    while rest and (whole or rest.startswith("<!-- raw ")):
        first, _, after = rest.partition("\n")
        match = RAW_OPEN.match(first)
        if not match:
            raise FormError("expected an appendix marker, read %r" % first)
        label, count = match.group(1), int(match.group(2))
        raw = after[:count]
        tail = "\n<!-- end raw %s -->\n\n" % label
        if after[count:count + len(tail)] != tail:
            raise FormError("the raw text of %s does not close where its marker says" % label)
        f["appendix"].append({"label": label, "raw": raw})
        rest = after[count + len(tail):]
    return f


def new_doc(feature, block):
    return TITLE % one_line(feature, "the feature") + "\n" + block


def append(existing, block):
    """The doc with one more block at its end: the earlier bytes untouched, a blank line between."""
    if not existing.endswith("\n"):
        existing += "\n"
    return existing + "\n" + block


def parse_doc(text):
    """{"title", "blocks": [fields]} for a doc this module wrote (blocks split on their headings, the
    appendix read by length so a raw text cannot split a block)."""
    first, _, rest = text.partition("\n")
    if not first.startswith("# Vertical review %s " % M):
        raise FormError("the verdict doc opens with '# Vertical review %s <feature>'" % M)
    title = first[len("# Vertical review %s " % M):]
    if not rest.startswith("\n"):
        raise FormError("a blank line follows the title")
    rest = rest[1:]
    blocks = []
    while rest:
        parsed = parse_block(rest, whole=False)
        rendered = render_block(parsed)
        if not rest.startswith(rendered):
            raise FormError("a block does not read back to its own bytes")
        blocks.append(parsed)
        rest = rest[len(rendered):]
        if rest:
            if not rest.startswith("\n"):
                raise FormError("a blank line separates two blocks")
            rest = rest[1:]
    return {"title": title, "blocks": blocks}


def render_doc(parsed):
    text = new_doc(parsed["title"], render_block(parsed["blocks"][0]))
    for block in parsed["blocks"][1:]:
        text = append(text, render_block(block))
    return text


# ---- the VERTICAL: chat block (v1's lines, byte for byte) ---------------------------------------------

def render_vertical(f):
    reviewers = ", ".join(f["reviewers"]) or "none"
    dropped = ", ".join("%s %s %s" % (d["row"], D, d["why"]) for d in f["dropped"]) or "none"
    lines = ["VERTICAL: %s @ %s..%s" % (f["doc"], f["base"], f["head"]),
             "Verdict: %s  %s  per /signoff's mapping" % (f["verdict"], M),
             "Reviewers: local + %s  %s  Dropped: %s  %s  Refuted: %d" % (reviewers, M, dropped, M, f["refuted"]),
             "Doc: %s" % f["verdict_doc"],
             "REVIEW.md: %s" % f["review_line"], "",
             "Bottom line: %s" % one_line(f["bottom_line"], "the bottom line")]
    if f.get("skill_note"):
        lines.append("SKILL NOTE: %s" % one_line(f["skill_note"], "the skill note"))
    return "\n".join(lines) + "\n"


VERTICAL_HEAD = re.compile(r"^VERTICAL: (.+) @ ([^ ]+)\.\.([^ ]+)$")
VERDICT_LINE = re.compile(r"^Verdict: (.+)  %s  per /signoff's mapping$" % M)
REVIEWERS_LINE = re.compile(r"^Reviewers: local \+ (.+)  %s  Dropped: (.+)  %s  Refuted: (\d+)$" % (M, M))


def parse_vertical(text):
    lines = text.split("\n")
    head = VERTICAL_HEAD.match(lines[0])
    verdict = VERDICT_LINE.match(lines[1])
    reviewers = REVIEWERS_LINE.match(lines[2])
    if not (head and verdict and reviewers and lines[3].startswith("Doc: ") and lines[4].startswith("REVIEW.md: ")
            and lines[5] == "" and lines[6].startswith("Bottom line: ")):
        raise FormError("the text does not read as the VERTICAL: block")
    dropped = []
    if reviewers.group(2) != "none":
        for item in reviewers.group(2).split(", "):
            row, _, why = item.partition(" %s " % D)
            dropped.append({"row": row, "why": why})
    f = {"doc": head.group(1), "base": head.group(2), "head": head.group(3), "verdict": verdict.group(1),
         "reviewers": [] if reviewers.group(1) == "none" else reviewers.group(1).split(", "),
         "dropped": dropped, "refuted": int(reviewers.group(3)), "verdict_doc": lines[3][len("Doc: "):],
         "review_line": lines[4][len("REVIEW.md: "):], "bottom_line": lines[6][len("Bottom line: "):],
         "skill_note": None}
    index = 7
    if index < len(lines) and lines[index].startswith("SKILL NOTE: "):
        f["skill_note"] = lines[index][len("SKILL NOTE: "):]
        index += 1
    if lines[index:] != [""]:
        raise FormError("the VERTICAL: block ends after its bottom line (and its SKILL NOTE)")
    return f
