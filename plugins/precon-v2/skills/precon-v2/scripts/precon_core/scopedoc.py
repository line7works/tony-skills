"""The scope doc: its header, its board, and the plan of every document write a run makes.

Everything here takes and returns text; nothing writes a file. `plan` is called twice with the
same inputs: by `record-answer`, which refuses an answer whose documents cannot be rendered and
read back (`unrenderable`), and by `write`, which writes exactly what it planned.

The forms are the shared templates' (`station_core/templates.py`, E14-12): a new doc is
`render_scope_doc` with one added line, the triage comment, after its title; a continued doc is
changed only by insertions at the tail of its sections, the one comment line when it has none,
and the lines this run's answer settled (a parked or assumed Decisions line rewritten in place as
decided, under the same ledger id; an Open item removed, its decided line appended to
`Decisions:`; a parked, open or assumed row an answered question settled and the answer rules out
removed, its out-of-scope line appended to `Out of scope:`; an Open item written inline on the
label line leaves the label alone, `Open:`, the form's line for zero items). Every other prior
line is kept byte for byte, and the plan checks that it is.
"""
import os
import re

from station_core import ledger, templates

from . import text as textmod

D = templates.D
M = templates.M
TIERS = ("napkin", "bounded", "architectural")
TIER_COMMENT = "<!-- precon-v2 triage: %s -->"
TIER_LINE = re.compile(r"^<!-- precon-v2 triage: (napkin|bounded|architectural) -->$")
# a triage comment as a hand may have typed it, recognized over the whole text with invisibles dropped:
# any spacing or none, any case, any separator between `precon`, `v2` and `triage` (an underscore or a
# non-breaking hyphen included), across lines, unterminated; every match counts, and one that is not
# exactly TIER_LINE alone on its line is off its form (CP1-6)
TIER_ANY = re.compile(r"<!--(?:(?!-->).)*?precon[\W_]*v2[\W_]*triage(?:(?!-->).)*?(?:-->|$)",
                      re.IGNORECASE | re.DOTALL)
OPEN_LABEL = "Open:"
TITLE = re.compile(r"^# (?P<title>.+) %s scope doc \((?P<date>.+)\)$" % D)
PARKED_REASONS = ("needs research", "needs prototype")
WAITING = "waiting on "
SECTION_LABELS = ("Intent:", "Decisions:", "Out of scope:", "Research:", "Open:", "Next:")
COLD_POINTER = "cold read: %s"


class PlanError(ValueError):
    """A value of the answer that the documents cannot carry. `problems` is [{"message", ...}]."""

    def __init__(self, problems):
        self.problems = list(problems)
        ValueError.__init__(self, "; ".join(p["message"] for p in self.problems))


# ---- reading -------------------------------------------------------------------------------------

def header(text):
    """{"title", "date", "intent", "tier"} of a scope doc (None where a field is absent)."""
    lines = [raw.rstrip("\r\n") for raw in text.splitlines(True)]
    out = {"title": None, "date": None, "intent": None, "tier": None}
    for line in lines:
        match = TITLE.match(line)
        if match and out["title"] is None:
            out["title"], out["date"] = match.group("title"), match.group("date")
            continue
        match = TIER_LINE.match(line)
        if match and out["tier"] is None and out["intent"] is None:
            out["tier"] = match.group(1)
            continue
        if line.startswith("Intent:") and out["intent"] is None:
            out["intent"] = line[len("Intent:"):].strip()
    return out


def comments(text):
    """[(line number, exact)] for every triage comment in the text, in any hand's spelling, across lines:
    the match is read on the text with invisibles dropped, and `exact` says it is TIER_LINE standing
    alone on its line of the text as written (no invisible, no other character beside it)."""
    visible, where = [], []
    for index, char in enumerate(text):
        if not textmod.invisible(char):
            visible.append(char)
            where.append(index)
    visible = "".join(visible)
    out = []
    for match in TIER_ANY.finditer(visible):
        start = where[match.start()]
        end = where[match.end() - 1] + 1
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", start)
        line = text[line_start:len(text) if line_end < 0 else line_end].rstrip("\r")
        exact = bool(TIER_LINE.match(line)) and text[start:end] == line
        out.append((text.count("\n", 0, start) + 1, exact, line))
    return out


def comment_findings(text):
    """[{line, message}] for a triage comment off its form (a tier outside the three, another
    spelling, other spacing, split over lines) or a second comment: a doc carries one comment, as
    this core writes it, or none."""
    out = []
    for seen, (number, exact, line) in enumerate(comments(text), 1):
        if not exact:
            out.append({"line": number, "message": "the triage comment %r is not %r with a tier of napkin, bounded "
                                                   "or architectural, alone on its line"
                                                   % (line, TIER_COMMENT % "<tier>")})
        elif seen > 1:
            out.append({"line": number, "message": "a second triage comment %r: a doc carries one" % line})
    return out


def counts(rows):
    return ledger.counts(rows)


def board(tag_counts):
    return "decided %d %s assumed %d %s parked %d %s open your-calls %d" % (
        tag_counts["decided"], M, tag_counts["assumed"], M, tag_counts["parked"], M, tag_counts["open"])


def final_counts(tag_counts):
    """v1's report counts: decided, assumed, parked, out of scope."""
    return {"decided": tag_counts["decided"], "assumed": tag_counts["assumed"], "parked": tag_counts["parked"],
            "out_of_scope": tag_counts["out-of-scope"]}


def parked_lines(rows):
    return ["%s %s parked: %s" % (row["text"], D, row["source"]) for row in rows if row["tag"] == "parked"]


def twins(value, rows, own=None):
    """Every `Decisions:` or `Open:` ledger row whose words `value` repeats, other than the row `own` a
    ledger trace names: the frame's readings of the line against the frame's readings of each row
    (`answer.forms(line) & answer.row_forms(row)`, through `text.readings` and `text.row_readings`)."""
    forms = textmod.readings(value)
    if not forms:
        return []
    return [row for row in rows if row["section"] in ("Decisions", "Open") and row["id"] != own
            and forms & textmod.row_readings(row["text"])]


def valid_parked(reason):
    return isinstance(reason, str) and (reason in PARKED_REASONS or (
        reason.startswith(WAITING) and bool(reason[len(WAITING):].strip())))


# ---- the lines an answer adds ----------------------------------------------------------------------

def one_line(value, what, problems, where=None):
    """`text.one_line`, the check the refusals use too: no line separator, no invisible letter."""
    if not textmod.one_line(value):
        problem = {"message": "%s is one line of visible text, not blank, with no line separator or invisible "
                              "character" % what}
        if where:
            problem.update(where)
        problems.append(problem)
        return False
    return True


def source_of(trace, answer, run_id):
    """The source a new decided line carries, from its trace (never typed by the executor)."""
    kind, ref = trace.get("kind"), trace.get("ref")
    if kind == "owner_words":
        return "the owner's words: \"%s\"" % ref
    if kind == "repo_path":
        return "the repo: %s" % ref
    if kind == "question":
        return settled_by(answer, [ref], run_id)
    return None


def settled_by(answer, question_ids, run_id):
    by_id = dict((q["id"], q) for q in answer.get("questions") or [])
    parts = ["answer to %s (run %s): %s" % (qid, run_id, (by_id.get(qid) or {}).get("answer", ""))
             for qid in question_ids]
    return "; ".join(parts)


def answered_touching(answer, line_id):
    return [q["id"] for q in answer.get("questions") or []
            if line_id in (q.get("touches") or []) and isinstance(q.get("answer"), str) and q["answer"].strip()
            and not q.get("needs_research")]


def _reads_back(body, text, tag, detail, problems, where):
    """The Decisions line `- <body>` reads back through the ledger reader as exactly this text, tag
    and detail; a text or detail holding the form's own separator would be read as another line."""
    try:
        rows = ledger.read("Decisions:\n- %s\n" % body)
    except ledger.LedgerRefused as exc:
        problems.append(dict(where, message="the line %r would not read back: %s" % (body, exc.lines[0]["why"])))
        return False
    row = rows[0]
    if (row["text"], row["tag"], row["source"]) != (text, tag, detail):
        problems.append(dict(where, message="the line %r would read back as the %s line %r with %r"
                                            % (body, row["tag"], row["text"], row["source"])))
        return False
    return True


def classify(answer, ledger_rows, run_id):
    """What the answer adds to the ledger: new Decisions lines, settlements, and section items."""
    by_id = dict((row["id"], row) for row in ledger_rows)
    problems = []
    decisions, rewrites, removals, open_items = [], {}, set(), []
    for index, line in enumerate(answer.get("lines") or []):
        where = {"line": index}
        text, tag = line.get("text"), line.get("tag")
        trace = line.get("trace") if isinstance(line.get("trace"), dict) else {}
        if trace.get("kind") == "ledger" and trace.get("ref") in by_id:
            row = by_id[trace["ref"]]
            if tag == "decided" and row["tag"] in ("parked", "assumed", "open"):
                qids = answered_touching(answer, row["id"])
                source = settled_by(answer, qids, run_id)
                try:
                    body = templates.render_ledger_line(row["text"], "decided", source)
                except templates.FormError as exc:
                    problems.append(dict(where, message="the settled line %r cannot be rendered: %s" % (row["text"], exc)))
                    continue
                if not _reads_back(body, row["text"], "decided", source, problems, where):
                    continue
                if row["section"] == "Decisions":
                    rewrites[row["line"]] = "- " + body
                else:
                    removals.add(row["line"])
                    decisions.append(body)
            continue
        if not one_line(text, "a line's text", problems, where):
            continue
        try:
            if tag in ("decided", "assumed", "parked"):
                detail = {"decided": lambda: source_of(trace, answer, run_id), "assumed": lambda: trace.get("ref"),
                          "parked": lambda: line.get("reason")}[tag]()
                body = templates.render_ledger_line(text, tag, detail)
                if _reads_back(body, text, tag, detail, problems, where):
                    decisions.append(body)
            elif tag == "open":
                if one_line(line.get("waits_on"), "an open line's call", problems, where):
                    open_items.append("%s (waits on: %s)" % (text, line["waits_on"]))
        except templates.FormError as exc:
            problems.append(dict(where, message="the line %r cannot be rendered: %s" % (text, exc)))
    out_of_scope = []
    for index, item in enumerate(answer.get("out_of_scope") or []):
        where = {"out_of_scope": index}
        if one_line(item.get("text"), "an out-of-scope item", problems, where) and \
                one_line(item.get("reason"), "an out-of-scope reason", problems, where):
            out_of_scope.append("%s %s %s" % (item["text"], D, item["reason"]))
            # R4 (CP3-2): the item rules out a parked, open or assumed row an answered question of this run
            # settled, so that row leaves the doc in the same write (the removal path of a settled Open item,
            # a Decisions line too): the doc never holds the out-of-scope line and its twin
            for row in twins(item["text"], ledger_rows):
                if row["tag"] in ("parked", "open", "assumed") and answered_touching(answer, row["id"]) \
                        and row["line"] not in rewrites:
                    removals.add(row["line"])
    research = []
    for index, item in enumerate(answer.get("research") or []):
        if one_line(item, "a research item", problems, {"research": index}):
            research.append(item)
    for index, item in enumerate(answer.get("open_items") or []):
        if one_line(item, "an open item", problems, {"open_items": index}):
            open_items.append(item)
    return {"decisions": decisions, "rewrites": rewrites, "removals": removals, "out_of_scope": out_of_scope,
            "research": research, "open": open_items, "problems": problems}


def settles_anything(parts):
    return bool(parts["decisions"] or parts["rewrites"] or parts["out_of_scope"])


# ---- a new doc ----------------------------------------------------------------------------------------

def render_new(title, date, intent, tier, parts):
    text = templates.render_scope_doc(title, date, intent, parts["decisions"], out_of_scope=parts["out_of_scope"],
                                      research=parts["research"], open_items=parts["open"])
    first, rest = text.split("\n", 1)
    return first + "\n" + TIER_COMMENT % tier + "\n" + rest


# ---- a continued doc ----------------------------------------------------------------------------------

def _ending(lines):
    for raw in lines:
        if raw.endswith("\r\n"):
            return "\r\n"
        if raw.endswith("\n"):
            return "\n"
    return "\n"


def _labels(lines):
    """{label: index} of the first line of each form label, 0-based."""
    out = {}
    for index, raw in enumerate(lines):
        for label in SECTION_LABELS:
            if raw.startswith(label) and label not in out:
                out[label] = index
    return out


def _tail(lines, labels, label):
    """The 0-based index after the last non-blank line of the section `label` opens."""
    start = labels[label]
    later = sorted(i for i in labels.values() if i > start)
    end = later[0] if later else len(lines)
    last = start
    for index in range(start, end):
        if lines[index].strip():
            last = index
    return last + 1


def render_continued(text, tier, parts):
    """The continued doc and the check that every prior line not settled here is kept."""
    lines = text.splitlines(True)
    nl = _ending(lines)
    labels = _labels(lines)
    for label in SECTION_LABELS:
        if label not in labels:
            raise PlanError([{"message": "the doc has no '%s' label, so nothing can be placed" % label}])
    before = {}      # 0-based index -> [lines inserted before it]

    def insert(at, items):
        if items:
            if at >= len(lines):
                raise PlanError([{"message": "a section ends the file; the form puts 'Next:' last"}])
            before.setdefault(at, []).extend("- %s%s" % (item, nl) for item in items)

    has_comment = bool(comments(text))
    title_at = next((i for i, raw in enumerate(lines) if raw.strip()), 0)
    if not has_comment:
        before.setdefault(title_at + 1, []).append(TIER_COMMENT % tier + nl)
    insert(_tail(lines, labels, "Decisions:"), parts["decisions"])
    insert(_tail(lines, labels, "Out of scope:"), parts["out_of_scope"])
    insert(_tail(lines, labels, "Research:"), parts["research"])
    insert(_tail(lines, labels, "Open:"), parts["open"])
    out, kept_old, kept_new = [], [], []
    relabelled = 0
    for index, raw in enumerate(lines):
        out.extend(before.get(index, []))
        number = index + 1
        ending = raw[len(raw.rstrip("\r\n")):]
        if number in parts["removals"]:
            if raw.startswith(OPEN_LABEL):
                # the item sat inline on the label line: the label stays, alone, as the form writes zero items
                out.append(OPEN_LABEL + ending)
                relabelled += 1
            continue
        if number in parts["rewrites"]:
            out.append(parts["rewrites"][number] + ending)
            continue
        kept_old.append(raw)
        out.append(raw)
        kept_new.append(len(out) - 1)
    new = "".join(out)
    # the no-loss check: every prior line this run did not settle is in the new doc, in order; a settled
    # inline Open item's label line is rewritten, not dropped, and counted as such
    removed = len(parts["removals"]) - relabelled
    if [out[i] for i in kept_new] != kept_old or \
            len(kept_old) != len(lines) - removed - relabelled - len(parts["rewrites"]) or \
            len(out) != len(lines) - removed + sum(len(v) for v in before.values()):
        raise PlanError([{"message": "the continued doc would drop or change a prior line"}])
    return new


# ---- the checks every planned scope doc passes ----------------------------------------------------------

def check_rendered(text, items=None):
    """[{message}] when the planned doc would not read back through the ledger reader or the form, or
    (given `items`, the count the plan wrote) would read back another number of items (CP2-4)."""
    problems = []
    try:
        rows = ledger.read(text)
    except ledger.LedgerRefused as exc:
        rows = None
        for row in exc.lines:
            problems.append({"message": "the planned doc's line %d would not read back: %r (%s)"
                                        % (row["line"], row["raw"], row["why"])})
    if rows is not None and items is not None and len(rows) != items:
        problems.append({"message": "the planned doc would read back %d items; the plan wrote %d" % (len(rows), items)})
    for finding in templates.check("scope-doc", text):
        problems.append({"message": "the planned doc departs from the form at line %d: %s"
                                    % (finding["line"], finding["message"])})
    if templates.render(templates.parse("scope-doc", text)) != text:
        problems.append({"message": "the planned doc does not round-trip byte for byte"})
    return problems


def contained(target, root):
    """Whether `target`'s nearest existing folder resolves inside `root` (a symlinked folder that
    leaves the workspace or the staging home is not)."""
    folder = os.path.dirname(target)
    while folder and not os.path.exists(folder):
        parent = os.path.dirname(folder)
        if parent == folder:
            break
        folder = parent
    real, base = os.path.realpath(folder), os.path.realpath(root)
    return real == base or real.startswith(base.rstrip(os.sep) + os.sep)


def new_doc_path(station, workspace, staging, date, idea):
    if station.get("home") == "staging":
        return os.path.join(staging, "%s-scope.md" % idea)
    return os.path.join(workspace, "docs", "scope", "%s-%s.md" % (date, idea))


def root_of(doc_path, doc_home, workspace, staging):
    return staging if doc_home == "staging" else workspace
