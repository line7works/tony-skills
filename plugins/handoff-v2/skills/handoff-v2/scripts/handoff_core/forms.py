"""The load-bearing forms of handoff-v2 (ruling E15-11): rendered and parsed here, and only here.

    heading(date), parse_heading(line)                 the block heading, v1's bytes
    next_move_text(move) -> {"line", "kickoff", "alternative"}
    render_block(fields), parse_block(text)            the dated block in `## Handoffs`
    render_report(fields), parse_report(text)          the `HANDOFF:` chat block, v1's bytes
    render_gate_open(fields), parse_gate_open(text)    the gate-open form, v1's bytes

THE EM DASH. v1's block heading, `HANDOFF:` first line and gate-open closer carry an em dash (U+2014). It is this
module's one constant `D`, written as an escape and typed nowhere in this core's files: standing rule 10's one named
exception (the E15 lane contract E15-11), stated in `references/handoff-contract.md` section 8. Every renderer here
has a parser, and parse then render gives the bytes back (`scripts/tests/test_forms.py`).

THE STATION NAMES. The kickoff lines name the v2 stations while v1 stays installed (A2, Q5): `/ship-v2 <slice>
<doc>`, the by-hand alternative `/build-v2 <slice> <doc>` stated once, an open card's `/recheck-v2 <slice> <doc>`,
and the gate-open closer's `/handoff-v2`. The station name is a value of the form; the form's bytes around it are
v1's.
"""
import re

D = "\u2014"
M = "\u00b7"
SEP = " %s " % M
WIDE = "  %s  " % M
HEADING = re.compile(r"^### (\d{4}-\d{2}-\d{2}) %s handoff$" % D)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SAFE = "Thread is safe to clear."
NOT_SAFE = ("Thread is NOT safe to clear %s answer the questions and re-run /handoff-v2, or clear and accept the "
            "loss." % D)
LABELS = ("Next", "Cards", "Open", "Repo", "Suite", "Question", "Perishable")


class FormError(ValueError):
    """A text that does not read as the form, or a value the form cannot carry."""


def one_line(value, what):
    if not isinstance(value, str) or "\n" in value or "\r" in value or not value.strip():
        raise FormError("%s is one non-blank line of text" % what)
    return value


def field(value, what):
    one_line(value, what)
    if SEP in value or value.startswith(M + " ") or value.endswith(" " + M):
        raise FormError("%s holds the line form's separator ' %s '" % (what, M))
    return value


def heading(date):
    if not isinstance(date, str) or not DATE.match(date):
        raise FormError("a block's date reads YYYY-MM-DD: %r" % (date,))
    return "### %s %s handoff" % (date, D)


def parse_heading(line):
    match = HEADING.match(line)
    return match.group(1) if match else None


# ---- the next move ------------------------------------------------------------------------------------

def kickoff(slice_name, doc):
    return "/ship-v2 %s %s" % (field(slice_name, "a slice name"), field(doc, "the doc's path"))


def by_hand(slice_name, doc):
    return "/build-v2 %s %s" % (slice_name, doc)


def recheck(slice_name, doc):
    return "/recheck-v2 %s %s" % (slice_name, doc)


def next_move_text(move):
    """The next move as one line, with the kickoff and its alternative when the shape has them."""
    shape, doc = move["shape"], move["doc"]
    if shape == "clean-boundary":
        line = "%s%sby hand: %s" % (kickoff(move["slice"], doc), SEP, by_hand(move["slice"], doc))
        return {"line": line, "kickoff": kickoff(move["slice"], doc), "alternative": by_hand(move["slice"], doc)}
    if shape == "open-card":
        count = len(move.get("fix_list") or [])
        then = ", then ".join(recheck(s, doc) for s in move.get("recheck") or [])
        if count:
            what = "fix the %d open item%s listed under Open" % (count, "" if count == 1 else "s")
        else:
            what = "fix what the card names (the records name no open item)"
        return {"line": "%s, then %s" % (what, then), "kickoff": None, "alternative": None}
    if shape == "loop-complete":
        return {"line": "none: the loop is complete; the next move is the owner's (a new blueprint, or nothing)",
                "kickoff": None, "alternative": None}
    if shape == "owner-holds":
        return {"line": "none: the owner holds the next move (his answer to the next-slice question)",
                "kickoff": None, "alternative": None}
    raise FormError("a next move of shape %r has no line (an unresolved move is never written)" % shape)


# ---- the block ------------------------------------------------------------------------------------------

def card_text(card):
    text = "%s %s" % (field(card["name"], "a slice name"), field(card["card"], "a card"))
    if card.get("after") and card["after"] != card["card"]:
        text += " (after this run's grants: %s)" % field(card["after"], "a card")
    return text


def repo_text(repo):
    parts = [field(repo["branch"] or "detached HEAD", "the branch")]
    if repo.get("base"):
        parts.append("%d ahead of %s" % (repo["ahead"], field(repo["base"], "the default branch")))
    else:
        parts.append("no default branch")
    if repo.get("checkpoint"):
        parts.append("checkpointed %s" % repo["checkpoint"][:12])
    elif repo["tree"] == "clean":
        parts.append("clean")
    else:
        parts.append("dirty (%d path%s)" % (len(repo.get("dirt") or []), "" if len(repo.get("dirt") or []) == 1 else "s"))
    return SEP.join(parts)


def suite_text(suite):
    if not suite or suite.get("state") in (None, "none recorded"):
        return "none recorded"
    return "%s%s%s" % (field(suite["state"], "the suite state"), SEP, field(suite["provenance"], "its provenance"))


def open_text(finding):
    return SEP.join([field(finding["severity"], "a severity"), field(finding["location"], "a location"),
                     field(finding["claim"] or "(no claim)", "a claim")])


def render_block(fields):
    """The dated block: its heading, then one `- <Label>: <value>` line per item, \u00b7-separated fields where fields
    exist. A field given as `<label>_line` (from `parse_block`) is carried as it reads."""
    lines = [heading(fields["date"])]
    lines.append("- Next: %s" % one_line(fields.get("next_line") or next_move_text(fields["next"])["line"], "Next"))
    lines.append("- Cards: %s" % one_line(fields.get("cards_line") or (SEP.join(card_text(c) for c in fields["cards"])
                                                                      or "the doc holds no slice"), "Cards"))
    opens = fields.get("open_lines")
    if opens is None:
        opens = [open_text(f) for f in fields["open"]]
    lines += ["- Open: %s" % one_line(o, "Open") for o in opens] or ["- Open: none"]
    lines.append("- Repo: %s" % one_line(fields.get("repo_line") or repo_text(fields["repo"]), "Repo"))
    lines.append("- Suite: %s" % one_line(fields.get("suite_line") or suite_text(fields["suite"]), "Suite"))
    for q in fields["questions"]:
        lines.append("- Question: %s" % SEP.join([field(q["question"], "a question"), field(q["answer"], "an answer"),
                                                    field(q["landed"], "where it landed")]))
    for p in fields["perishables"]:
        lines.append("- Perishable: %s" % field(p, "a perishable"))
    return "\n".join(lines) + "\n"


def block_lines(fields):
    return render_block(fields).rstrip("\n").split("\n")


def parse_block(text):
    rows = text.rstrip("\n").split("\n")
    date = parse_heading(rows[0]) if rows else None
    if date is None:
        raise FormError("a block opens with its heading: %r" % (rows[:1],))
    out = {"date": date, "next_line": None, "cards_line": None, "open_lines": [], "repo_line": None, "suite_line": None,
           "questions": [], "perishables": []}
    for row in rows[1:]:
        match = re.match(r"^- (%s): (.*)$" % "|".join(LABELS), row)
        if match is None:
            raise FormError("a block line reads '- <Label>: <value>': %r" % row)
        label, value = match.groups()
        if label == "Question":
            parts = value.split(SEP)
            if len(parts) != 3:
                raise FormError("a Question line holds question %s answer %s where it landed: %r" % (M, M, row))
            out["questions"].append({"question": parts[0], "answer": parts[1], "landed": parts[2]})
        elif label == "Perishable":
            out["perishables"].append(value)
        elif label == "Open":
            if value != "none":
                out["open_lines"].append(value)
        else:
            out["%s_line" % label.lower()] = value
    return out


# ---- the HANDOFF: block and the gate-open form ----------------------------------------------------------

def render_report(fields):
    """v1's `HANDOFF:` block, byte for byte in its frame: the four header lines, the bottom line, the open findings
    and the skill note only when any, and the safe-to-clear closer."""
    lines = ["HANDOFF: %s %s after %s" % (one_line(fields["feature"], "the feature"), D, one_line(fields["after"], "after")),
             "Doc: %s%sNext: %s" % (one_line(fields["doc"], "Doc"), WIDE, one_line(fields["next"], "Next")),
             "Repo: %s%sSuite: %s" % (one_line(fields["repo"], "Repo"), WIDE, one_line(fields["suite"], "Suite")),
             "Questions: %s%sPerishables: %d carried" % (one_line(fields["questions"], "Questions"), WIDE,
                                                          int(fields["perishables"])),
             "", "Bottom line: %s" % one_line(fields["bottom_line"], "the bottom line")]
    tail = ["Open: %s" % one_line(o, "Open") for o in fields.get("open") or []]
    if fields.get("skill_note"):
        tail.append("SKILL NOTE: %s" % one_line(fields["skill_note"], "the skill note"))
    if tail:
        lines += [""] + tail
    lines += ["", SAFE]
    return "\n".join(lines) + "\n"


def parse_report(text):
    rows = text.rstrip("\n").split("\n")
    head = re.match(r"^HANDOFF: (.+) %s after (.+)$" % D, rows[0])
    doc = re.match(r"^Doc: (.+?)%sNext: (.+)$" % re.escape(WIDE), rows[1])
    repo = re.match(r"^Repo: (.+?)%sSuite: (.+)$" % re.escape(WIDE), rows[2])
    questions = re.match(r"^Questions: (.+?)%sPerishables: (\d+) carried$" % re.escape(WIDE), rows[3])
    if not (head and doc and repo and questions) or rows[4] != "" or not rows[5].startswith("Bottom line: ") \
            or rows[-1] != SAFE:
        raise FormError("the text does not read as the HANDOFF: block")
    out = {"feature": head.group(1), "after": head.group(2), "doc": doc.group(1), "next": doc.group(2),
           "repo": repo.group(1), "suite": repo.group(2), "questions": questions.group(1),
           "perishables": int(questions.group(2)), "bottom_line": rows[5][len("Bottom line: "):], "open": [],
           "skill_note": None}
    for row in rows[6:-1]:
        if row.startswith("Open: "):
            out["open"].append(row[len("Open: "):])
        elif row.startswith("SKILL NOTE: "):
            out["skill_note"] = row[len("SKILL NOTE: "):]
    return out


def render_gate_open(fields):
    lines = ["HANDOFF: %s %s GATE OPEN, nothing written" % (one_line(fields["feature"], "the feature"), D),
             "Doc: %s" % one_line(fields["doc"], "Doc")]
    lines += ["Unanswered: %s" % one_line(q, "a question") for q in fields["unanswered"]]
    lines += ["", NOT_SAFE]
    return "\n".join(lines) + "\n"


def parse_gate_open(text):
    rows = text.rstrip("\n").split("\n")
    head = re.match(r"^HANDOFF: (.+) %s GATE OPEN, nothing written$" % D, rows[0])
    if not head or not rows[1].startswith("Doc: ") or rows[-1] != NOT_SAFE or rows[-2] != "":
        raise FormError("the text does not read as the gate-open form")
    return {"feature": head.group(1), "doc": rows[1][len("Doc: "):],
            "unanswered": [r[len("Unanswered: "):] for r in rows[2:-2]]}
