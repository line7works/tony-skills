"""`record-answer`'s shared refusals (ruling E14-11, control room reading CR-3).

One implementation for the four cores. A core maps its own recorded answer onto the neutral view
this module reads, then calls `check` (pure) or `record` (writes `answer.json` only when the
answer is accepted):

    {"questions": [{"id": "Q1", "text": "...", "touches": [<ledger line id>, ...], "answer": "..."}],
     "lines":     [{"text": "...", "tag": "decided" | "assumed" | "parked" | "open" | ...,
                    "trace": {"kind": <trace kind>, "ref": "..."}}]}

`questions` are the questions the executor put to the owner in this run, each with the ledger
line ids it touches and the owner's answer. `lines` are the lines the executor asserts, each with
its trace. The trace kinds:

    ledger        a ledger line id of the scope doc this run read
    repo_path     a path that exists inside the workspace
    question      the id of a question of this run that the owner answered
    assumed       the executor's why, where the core's lane contract allows assumptions
    owner_words   the owner's words quoted, where the core's lane contract allows them

`DEFAULT_TRACES` is the three E14-11 names; a core passes `allowed` to widen it for its own
lines. The refusals, each `{"rule", "message", ...}` naming the question or line:

    shape              the answer is not the view above (not a refusal a person could fix by
                       asking something else, but it is refused the same way, never repaired)
    re-asked-decided   a question touches a `decided` ledger line, or its text is a `decided`
                       line's text (whitespace collapsed, case folded) whatever it touches
    unknown-line       a question touches an id the ledger does not hold
    untraced           a line with no trace, a trace kind the core does not allow, or a trace
                       that names nothing (an unknown ledger id, a path that is not in the
                       workspace, a question not answered in this run, an empty why or quote)
    quietly-resolved   a line asserted as `decided` whose trace is a `parked` or `open` ledger
                       line that no ANSWERED question of this run touched (a question asked and
                       left without an answer settles nothing)

Any refusal is exit 5 and nothing is written (station-loop.md section 3.4).

The text match of `re-asked-decided` catches deterministic repetition only: a question whose text,
with its whitespace collapsed and its case folded, equals a decided line's text. It does not
detect a paraphrase; whether a reworded question re-asks a decided line is the executor's to
judge and the reader's to check (E14-4), never this module's.
"""
import os
import re
import unicodedata

from . import exits, fsio

DEFAULT_TRACES = ("ledger", "repo_path", "question")
KNOWN_TRACES = DEFAULT_TRACES + ("assumed", "owner_words")


def _refusal(rule, message, **where):
    row = {"rule": rule, "message": message}
    row.update(where)
    return row


_FIELD_SPLIT = re.compile(u"\\s+(?:\u00b7|\u2014|\u2013|--|\\|)\\s+")
# The decorations the four stations' forms put around a line's words (the class the quiet-upgrade rule must see
# through; four escapes in slice 2, each behind one of these, and two false refusals in round 4 around item
# labels): a list mark (`- `, `* `, `+ `, `• `, `– `, `> `, `# `, `1. `, `2) `, `(3) `, `a) `, `- [ ] `), a leading
# item label (`R2`, `AC1:`, `C3.`, `Q4`, `(R2)`, `[R2]`, `R-2:`, `AC-1:`, `R2a:`, `R12.3`), a wrapping pair of
# `**`, `*`, `_`, `~~`, backticks or quotes, a trailing `(waits on: ...)` / `[parked: ...]` / `(assumed: ...)`
# parenthesis to any nesting, a trailing ` <dash> <tag> (...)` or ` <dash> <tag>: ...` ledger tail, trailing
# punctuation, and invisible characters. The strips run until nothing changes, so two decorations at once (a
# parenthesis, then a period) cannot escape.
_BULLET = re.compile(u"^(?:- \\[[ xX]\\]|\\[[ xX]\\]|[-*+\u2022\u2013\u25e6\u2023>]|#{1,6}|\\d{1,3}[.)]|\\(\\d{1,3}\\)|[a-hj-z][.)]|[ivx]{1,4}[.)])\\s+")
# The item labels the station forms use (R<n> requirement, AC<n> criterion, C<n> constraint, Q<n> question,
# O<n> open item, A<n> assumption, D<n> decision), with or without a hyphen, brackets, a dotted sub-number, a
# letter suffix or a trailing mark; a label is stripped only when a separator or a mark follows it, or when it
# is one of these known letters alone before a space, so a content token such as `S3`, `IPv6` or `H264` is never
# a label. A label is part of the words when BOTH sides carry one (round 4, lanes L and A: `Q4 budget` is not
# `Q3 budget`, and a line relabelled against a labelled row is a reworded line, the executor's and the reader's
# to judge, E14-4); a line or field that is only a label has no words.
_LABEL_CORE = r"(?:R|AC|C|Q|O|A|D)-?\d{1,4}(?:\.\d{1,3})*[a-z]?"
_LABEL = re.compile(r"^(?:[(\[]" + _LABEL_CORE + r"[)\]][.:]?\s*"
                    r"|" + _LABEL_CORE + r"(?:[.:)]\s*|\s+(?:\u00b7|\u2014|\u2013|--|-|:)\s+|\s+))"
                    r"(?:\u00b7|\u2014|\u2013|--|-|:)?\s*")
_LABEL_ALONE = re.compile(r"^[(\[]?" + _LABEL_CORE + r"[)\]]?[.:]?$")
_PAREN_WORDS = re.compile(r"^(?:waits? on|waiting on|parked|assumed|decided|open|needs research|needs prototype|later)\b",
                          re.IGNORECASE)
_TAG_TAIL = re.compile(u"(?:\\s+(?:\u00b7|\u2014|\u2013|--|-)\\s*|\\s*(?:\u00b7|\u2014|\u2013|--)\\s*)(?:decided|assumed|parked|open)\\b.*$",
                       re.IGNORECASE)
_WRAP = (("**", "**"), ("~~", "~~"), ("*", "*"), ("_", "_"), ("`", "`"), ('"', '"'), (u"\u201c", u"\u201d"),
         ("'", "'"), (u"\u2018", u"\u2019"))
_TRAILING = u" .;,:!?\u2026\u3002"
_EXTRA_INVISIBLE = frozenset(u"\u3164\u2800\u034f\u115f\u1160\uffa0\x0b\x0c\u180b\u180c\u180d\u180e\u17b4\u17b5"
                             + u"".join(chr(c) for c in range(0xfe00, 0xfe10)) + u"".join(chr(c) for c in range(0xe0100, 0xe01f0)))
# A reading of a labelled ROW's words with its label dropped, and of an unlabelled LINE's words, carry this
# mark, so that with plain set intersection a labelled line meets an unlabelled row (its words), an unlabelled
# line meets a labelled row (the row's words), equal labels meet, and two different labels never do.
_ROW_MARK = u"\x00"


def _visible(text):
    """The text with every invisible character dropped: Unicode format characters (Cf: zero-width, BOM,
    bidi marks, joiners), combining marks (Mn, Me: an accent reads the same composed or decomposed, and a
    word of marks alone is no word), line and paragraph separators (Zl, Zp), the C0/C1 controls other than
    tab, newline and carriage return, the variation selectors and the letter-shaped fillers (U+3164, U+2800, U+034F,
    U+115F, U+1160, U+17B4, U+17B5, U+180B to U+180D, U+FFA0)."""
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in ("Cf", "Zl", "Zp", "Mn", "Me") or ch in _EXTRA_INVISIBLE:
            continue
        if cat == "Cc" and ch not in "\t\n\r":
            continue
        out.append(ch)
    return "".join(out)


def _fields(text):
    """The whole fields of a `·`-, dash- or pipe-separated line."""
    return _FIELD_SPLIT.split(text)


def _normalized(text):
    """The text with invisibles dropped, its whitespace collapsed and its case folded, for the repeat check."""
    return " ".join(_visible(text).split()).casefold()


def _strip_paren_tail(text):
    """The text without a trailing `(waits on: ...)`, `[parked: ...]` or other ledger parenthesis, to any
    depth of nesting (lane P's round 4 builder: a call such as `(waits on: the bench call (see (Q2) first))`)."""
    out = text.rstrip()
    if not out or out[-1] not in ")]":
        return text
    close = out[-1]
    opener = "(" if close == ")" else "["
    depth = 0
    for index in range(len(out) - 1, -1, -1):
        if out[index] == close:
            depth += 1
        elif out[index] == opener:
            depth -= 1
            if depth == 0:
                inner = out[index + 1:-1].strip()
                if _PAREN_WORDS.match(inner):
                    return out[:index].rstrip()
                return text
    return text


def _split(text):
    """(label, words): a line's or field's words with every known decoration stripped, the strips repeated
    until nothing changes, and the item label it carried in front as a key of letters and digits ('' when
    none). A text that is only a label has no words."""
    out = _visible(text).strip()
    label = ""
    while True:
        before = out
        out = _BULLET.sub("", out, count=1)
        match = _LABEL.match(out)
        if match and match.end() < len(out):
            label = label or re.sub(r"[^a-z0-9]", "", match.group(0).casefold())
            out = out[match.end():]
        for left, right in _WRAP:
            if len(out) > len(left) + len(right) and out.startswith(left) and out.endswith(right):
                out = out[len(left):-len(right)]
        out = _TAG_TAIL.sub("", out)
        out = _strip_paren_tail(out)
        out = out.strip().rstrip(_TRAILING).strip()
        if out == before:
            break
    if _LABEL_ALONE.match(out):
        label = label or re.sub(r"[^a-z0-9]", "", out.casefold())
        out = ""
    return label, " ".join(out.split()).casefold()


def _bare(text):
    """The words of a line with every known decoration stripped (its label included)."""
    return _split(text)[1]


def _readings(text, side, later=False):
    """The readings of one text on the LINE side or the ROW side (see `_ROW_MARK`); a later field of a line
    counts only when it holds two or more words (a one-word why or reason field is no item)."""
    label, words = _split(text)
    if not words or (later and len(words.split()) < 2):
        return set()
    if side == "line":
        return set([label + " " + words, words]) if label else set([words, _ROW_MARK + words])
    return set([label + " " + words, _ROW_MARK + words]) if label else set([words])


def _forms(text):
    """Every reading of a LINE's words the quiet-upgrade rule compares: the whole line, and each whole field
    of a dashed line (a later field when it holds two or more words), each with its label kept and dropped."""
    out = _readings(text, "line")
    for index, field in enumerate(_fields(text)):
        if field.strip():
            out |= _readings(field, "line", later=index > 0)
    return out


_ROW_TAIL_SPLIT = re.compile(u"\\s+(?:\u2014|\u2013|--)\\s+")


def _row_forms(text):
    """Every reading of a ROW's words: the whole row and its first field before a ` <dash> <tag or reason>`
    tail (the ledger's dash; a middle dot or a pipe inside an item is part of the item: `Firmware · update
    path` is one item, lane P's round 4 checker). Never a later field: a row's reason or why is not its words
    (lane L's round 3 checker, CS3-2)."""
    out = _readings(text, "row")
    fields = _ROW_TAIL_SPLIT.split(text)
    if len(fields) > 1 and fields[0].strip():
        out |= _readings(fields[0], "row")
    return out


def bare(text):
    """Public: a line's words with every known decoration stripped (for a lane's own rules; E14-3)."""
    return _bare(text)


def forms(text):
    """Public: every reading of a line's words (for a lane's own rules; E14-3). Compare a line's `forms` with
    a row's `row_forms` by set intersection; the elements are the frame's encoding, not for display."""
    return _forms(text)


def row_forms(text):
    """Public: every reading of a ledger row's words (for a lane's own rules; E14-3)."""
    return _row_forms(text)


def _shape(answer):
    if not isinstance(answer, dict):
        return ["the answer is not an object"]
    problems = []
    for key in ("questions", "lines"):
        if not isinstance(answer.get(key), list):
            problems.append("the answer's %r is a list" % key)
    if problems:
        return problems
    ids = []
    for index, q in enumerate(answer["questions"]):
        if not isinstance(q, dict) or not isinstance(q.get("id"), str) or not q["id"].strip():
            problems.append("question %d carries no id" % index)
            continue
        if not isinstance(q.get("touches", []), list):
            problems.append("question %s: 'touches' is a list of ledger line ids" % q["id"])
        if not isinstance(q.get("text"), str) or not q["text"].strip():
            # a question with no text would skip the decided-text match (C3-1, round 4)
            problems.append("question %s carries no text" % q["id"])
        ids.append(q["id"])
    if len(ids) != len(set(ids)):
        problems.append("two questions share an id")
    for index, line in enumerate(answer["lines"]):
        if not isinstance(line, dict) or not isinstance(line.get("text"), str):
            problems.append("line %d is not an object with its text" % index)
    return problems


def _in_workspace(workspace, rel):
    """A `repo_path` trace names a file or folder inside the workspace: never the workspace itself
    (`.`, `./`, an empty segment) and never anything under `.git`."""
    if not workspace or not isinstance(rel, str) or not rel.strip() or os.path.isabs(rel):
        return False
    normal = os.path.normpath(rel)
    if normal in (".", "") or normal == ".git" or normal.startswith(".git" + os.sep):
        return False
    path = os.path.join(workspace, rel)
    if not (os.path.exists(path) and fsio.inside(path, workspace)):
        return False
    return os.path.realpath(path) != os.path.realpath(workspace)


def check(answer, ledger_lines, workspace=None, allowed=DEFAULT_TRACES):
    """{"exit": 0 | 5, "refusals": [...]}; pure, nothing written."""
    problems = _shape(answer)
    if problems:
        return {"exit": exits.REFUSED,
                "refusals": [_refusal("shape", p) for p in problems]}
    ledger = dict((row["id"], row) for row in ledger_lines)
    refusals = []
    answered = set()
    touched = set()
    for q in answer["questions"]:
        if isinstance(q.get("answer"), str) and q["answer"].strip():
            answered.add(q["id"])
        question_text = q.get("text")
        if isinstance(question_text, str):
            # the decided text asked again with its id left out of `touches` (round 3, finding 2);
            # a question that names the line is refused below, once
            forms_of_question = _forms(question_text)
            for row in ledger_lines:
                if (row["tag"] == "decided" and forms_of_question & _row_forms(row["text"])
                        and row["id"] not in q.get("touches", [])):
                    refusals.append(_refusal("re-asked-decided", "question %s repeats a decided line's text: "
                                             "%r (%s); a decided line passes forward and is never asked again"
                                             % (q["id"], row["text"], row["id"]),
                                             question=q["id"], line_id=row["id"]))
        for ident in q.get("touches", []):
            row = ledger.get(ident)
            if row is None:
                refusals.append(_refusal("unknown-line", "question %s touches %r, which is no line of the "
                                         "scope doc's ledger" % (q["id"], ident), question=q["id"], line_id=ident))
                continue
            if q["id"] in answered:
                # only an answered question of this run settles a line (C1-9); an unanswered one
                # that touches a parked or open line settles nothing
                touched.add(ident)
            if row["tag"] == "decided":
                refusals.append(_refusal("re-asked-decided", "question %s re-asks a decided line: %r (%s); a "
                                         "decided line passes forward and is never asked again"
                                         % (q["id"], row["text"], ident), question=q["id"], line_id=ident))
    for index, line in enumerate(answer["lines"]):
        trace = line.get("trace")
        kind = trace.get("kind") if isinstance(trace, dict) else None
        ref = trace.get("ref") if isinstance(trace, dict) else None
        where = {"line": index, "text": line["text"]}
        why = None
        if kind is None:
            why = "it carries no trace"
        elif kind not in allowed:
            why = "its trace kind %r is not one this core allows (%s)" % (kind, ", ".join(allowed))
        elif kind == "ledger" and ref not in ledger:
            why = "its ledger id %r is no line of the scope doc's ledger" % (ref,)
        elif kind == "repo_path" and not _in_workspace(workspace, ref):
            why = "its path %r is not in the workspace" % (ref,)
        elif kind == "question" and ref not in answered:
            why = "its question %r was not answered in this run" % (ref,)
        elif kind in ("assumed", "owner_words") and not (isinstance(ref, str) and _visible(ref).strip()):
            why = "its %s is empty" % ("why" if kind == "assumed" else "quote")
        if why:
            refusals.append(_refusal("untraced", "the line %r is refused: %s" % (line["text"], why), **where))
            continue
        if kind == "ledger" and line.get("tag") == "decided" and ledger[ref]["tag"] in ("parked", "open") \
                and ref not in touched:
            refusals.append(_refusal("quietly-resolved", "the line %r is asserted as decided, but its ledger "
                                     "line %s is %s and no question of this run settled it"
                                     % (line["text"], ref, ledger[ref]["tag"]), **where))
        elif line.get("tag") == "decided" and isinstance(line.get("text"), str):
            # the same evasion by text (lane P's checker, CP1-1; lane L's round 2 checker, CS-4): a parked or
            # open line's words asserted as decided under another trace kind, OR under a ledger trace to some
            # other line, with no question of this run touching the parked or open line
            # every reading of the line's words (whole, bare of decorations, and each field) against every
            # reading of the parked or open row's words (the Board window's BF pattern note: four escapes,
            # each behind one decoration; the class is closed here, not the instance)
            candidates = _forms(line["text"])
            for row in ledger_lines:
                if (row["tag"] in ("parked", "open") and candidates & _row_forms(row["text"])
                        and row["id"] not in touched and not (kind == "ledger" and ref == row["id"])):
                    refusals.append(_refusal("quietly-resolved", "the line %r is asserted as decided under a %s "
                                             "trace, but it is the %s ledger line %s and no question of this "
                                             "run settled it" % (line["text"], kind, row["tag"], row["id"]),
                                             **where))
                    break
    return {"exit": exits.REFUSED if refusals else exits.SUCCESS, "refusals": refusals}


def record(run_dir, answer, ledger_lines, workspace=None, allowed=DEFAULT_TRACES):
    """(exit code, report). `answer.json` is written in `run_dir` only when the answer is accepted."""
    result = check(answer, ledger_lines, workspace=workspace, allowed=allowed)
    if result["exit"] != exits.SUCCESS:
        return result["exit"], {"accepted": False, "refusals": result["refusals"],
                                "reason": "the recorded answer was refused on its content (%d refusal(s)); "
                                          "nothing was written" % len(result["refusals"])}
    path = os.path.join(run_dir, "answer.json")
    fsio.write_json(path, answer)
    return exits.SUCCESS, {"accepted": True, "refusals": [], "answer": path,
                           "sha256": fsio.sha256_file(path)}
