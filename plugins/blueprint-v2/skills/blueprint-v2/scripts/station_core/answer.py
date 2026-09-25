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


_FIELD_SPLIT = re.compile(u"\\s+(?:\u00b7|\u2014|\u2013|--|-|\\|)\\s+")
# The decorations the four stations' forms put around a line's words (the class the quiet-upgrade rule must see
# through; four escapes in slice 2, each behind one of these, two false refusals in round 4 around item labels,
# and the seam 11 reader's regressions): a list mark (`- `, `* `, `+ `, `• `, `– `, `> `, `# `, `1. `, `2) `, `(3) `,
# `a) `, `- [ ] `, `[x] `, a check or arrow mark), a section label (`Open: `, `Constraint: `), a MARKED item label
# (`R2:`, `C3.`, `(R2)`, `[R2]`, `R-2:`, `AC-1:`, `R2a:`, `R12.3:`, `R2 <dash> `, bold or italic around it: the form's
# decoration on both sides), a BARE item label (`R2 `, `Q4 `: part of the words when both sides carry one), a
# wrapping pair of `**`, `*`, `_`, `~~`, backticks, quotes, guillemets or brackets, a trailing `(waits on: ...)` /
# `[parked: ...]` / `(assumed: ...)` parenthesis to any nesting, a trailing ` <dash> <tag> (...)` or ` <dash> <tag>:
# ...` ledger tail, trailing punctuation (fullwidth included), and invisible characters. The strips run until
# nothing changes, so two decorations at once cannot escape. Text is compared in NFC, so a composed and a
# decomposed accent read the same; combining marks are visible characters (a Thai or Hebrew word keeps its marks).
_BULLET = re.compile(u"^(?:- \\[[ xX]\\]|\\[[ xX]\\]|[-*+\u2022\u2013\u25e6\u2023>\u2713\u2714\u2192\u2705\u2611]|#{1,6}|\\d{1,3}[.)]|\\d{1,3}(?:\\.\\d{1,3})+\\.|\\(\\w{1,3}\\)|[a-hj-zA-HJ-Z][.)]|[ivxIVX]{1,4}[.)])\\s+")
_LEAD_TOKEN = re.compile(r"^(\S{1,3})\s+")
_TAIL_TOKEN = re.compile(r"\s+(\S{1,3})$")


def _markish(ch):
    """A list or check mark, an arrow, a dash or a bullet: punctuation (not a quote, #, %, &, @ or a slash), a
    symbol of the So category, or an arrow or bullet operator; never a letter, digit, currency or math sign."""
    cat = unicodedata.category(ch)
    code = ord(ch)
    if ch in "+>*|\u2219":
        return True
    if 0x2190 <= code <= 0x21FF or 0x27F0 <= code <= 0x27FF or 0x2900 <= code <= 0x297F:
        return True
    return (cat in ("Pd", "So") or (cat == "Po" and ch not in "#%&@/\\\"'"))
_SECTION = re.compile(r"^(?:constraints?|out of scope|out-of-scope|assumed|assumptions?|open|requirements?|decided|parked|"
                      r"research|questions?|decisions?|deferred|poured concrete(?: \(one-way doors\))?|one-way doors|not in this slice|"
                      r"acceptance criteria|goal|intent|next|discovered|deviations?|build assumptions|punch list|rulings?)\s*:\s+",
                      re.IGNORECASE)
# The item labels the station forms use (R<n> requirement, AC<n> criterion, C<n> constraint, Q<n> question,
# O<n> open item, A<n> assumption, D<n> decision), with or without a hyphen, a dotted sub-number or a letter
# suffix. MARKED (brackets, a trailing mark, or a following separator, any case): a decoration, stripped on both
# sides as often as it appears (`R2: Q3 budget` still carries `Q3 budget`). BARE (the known letters in upper case
# and digits, then a space, no mark; once): the label of the rule, part of the words when both sides carry one, so
# `Q4 budget` is not `Q3 budget` and a relabelled bare token is a reworded line (E14-4), while a content token such
# as `S3`, `IPv6` or `H264` is never a label. A text that is only a label has no words.
_LABEL_CORE = r"(?:R|AC|C|Q|O|A|D)-?\d{1,5}(?:\.\d{1,3})*[a-z]?"
_MARKED_LABEL = re.compile(r"^(?:[(\[]" + _LABEL_CORE + r"[)\]][.:]?\s*"
                           r"|" + _LABEL_CORE + r"(?:[.:)\uff1a](?!\d)\s*|\s*(?:\u2014|\u2013)\s*|\s+(?:\u00b7|\u2014|\u2013|--|-|:)\s+))"
                           r"(?:\u00b7|\u2014|\u2013|--|-|:)?\s*", re.IGNORECASE)
_BARE_LABEL = re.compile(r"^" + _LABEL_CORE + r"\s+")
_END_LABEL = re.compile(r"\s*[(\[]" + _LABEL_CORE + r"[)\]]$", re.IGNORECASE)
_LABEL_ALONE = re.compile(r"^[(\[]?" + _LABEL_CORE + r"[)\]]?[.:]?$", re.IGNORECASE)
_BOLD_LABEL = re.compile(r"^(\*{1,3}|_{1,3}|`|~~)(" + _LABEL_CORE + r")([.:)]?)\1[ \t]*", re.IGNORECASE)
_PAREN_WORDS = re.compile(r"^(?:waits? on|waiting on|parked|assumed|decided|open|needs research|needs prototype|later|"
                          r"deferred|pending|tbd|not now|undecided|to decide|to be decided)\b",
                          re.IGNORECASE)
_TAG_TAIL = re.compile(u"(?:\\s+(?:\u00b7|\u2014|\u2013|--|-)\\s*|\\s*(?:\u00b7|\u2014|\u2013|--|,|;)\\s*)"
                       u"(?:decided|assumed|parked|open|deferred|later|waits? on|waiting on|needs research|needs prototype)\\b.*$",
                       re.IGNORECASE)
_WRAP = (("**", "**"), ("~~", "~~"), ("*", "*"), ("_", "_"), ("`", "`"), ('"', '"'), (u"\u201c", u"\u201d"),
         ("'", "'"), (u"\u2018", u"\u2019"), (u"\u00ab", u"\u00bb"))
_BRACKETS = (("(", ")"), ("[", "]"))
# Emphasis around part of the words (the seam 12 reader, CS12-2): `**` `~~` and backticks anywhere, `*` around a word
# run; never `_` (a name such as `__init__` keeps its underscores).
_INNER_EMPHASIS = re.compile(r"(\*\*|~~|`)(?=\S)(.+?)(?<=\S)\1")
_INNER_ITALIC = re.compile(r"(?<!\w)(\*)(?=\S)(.+?)(?<=\S)\1(?!\w)")
_TRAILING = u" .;,:!?\u2026\u3002\uff0e\uff0c\uff1a\uff1b\uff01\uff1f\u3001\uff61\u203c\u2049\u2047\u2048\u2025\u0964\u0965\u06d4\u061f\u060c\u061b\u0589\u037e"
# The default-ignorable code points (Unicode's list, the unassigned ones included: Python 3.9's tables know
# nothing of U+2065 or U+E0080), plus the letter-shaped fillers and two controls; every Cf, Zl, Zp and C0/C1
# character other than tab, newline and carriage return is invisible too.
_IGNORABLE = ((0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5),
              (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x2800, 0x2800),
              (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8),
              (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF))
_EXTRA_INVISIBLE = frozenset(u"\x0b\x0c")
# A reading of a labelled ROW's words with its label dropped, and of an unlabelled LINE's words, carry this
# mark, so that with plain set intersection a labelled line meets an unlabelled row (its words), an unlabelled
# line meets a labelled row (the row's words), equal labels meet, and two different labels never do.
_ROW_MARK = u"\x00"


def _ignorable(ch):
    code = ord(ch)
    for low, high in _IGNORABLE:
        if low <= code <= high:
            return True
    return False


def _visible(text):
    """The text with every invisible character dropped: Unicode format characters (Cf: zero-width, BOM,
    bidi marks, joiners), the default-ignorable code points (the variation selectors, the Mongolian and Khmer
    selectors, the fillers U+3164, U+2800, U+115F, U+1160, U+FFA0, the tag characters, assigned or not), line
    and paragraph separators (Zl, Zp), and the C0/C1 controls other than tab, newline and carriage return.
    Combining marks are visible: they change what the reader sees."""
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in ("Cf", "Zl", "Zp") or ch in _EXTRA_INVISIBLE or _ignorable(ch):
            continue
        if cat == "Cc" and ch not in "\t\n\r":
            continue
        out.append(ch)
    return "".join(out)


def _fields(text):
    """The whole fields of a `·`-, dash-, hyphen- or pipe-separated line."""
    return _FIELD_SPLIT.split(text)


def _normalized(text):
    """The text in NFC with invisibles dropped, its whitespace collapsed and its case folded."""
    return " ".join(_visible(unicodedata.normalize("NFC", text)).split()).casefold()


def _strip_paren_tail(text):
    """The text without a trailing `(waits on: ...)`, `[parked: ...]` or other ledger parenthesis, to any
    depth of nesting (lane P's round 4 builder: a call such as `(waits on: the bench call (see (Q2) first))`)."""
    out = text.rstrip()
    if not out or out[-1] not in u")]\uff09\u3011":
        return text
    close = out[-1]
    opener = {")": "(", "]": "[", u"\uff09": u"\uff08", u"\u3011": u"\u3010"}[close]
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


def _label_key(text):
    return re.sub(r"[^a-z0-9.]", "", text.casefold())


def _split(text):
    """(label, words): a line's or field's words in NFC with every known decoration stripped, the strips
    repeated until nothing changes, and the BARE item label it carried in front as a key of letters, digits and
    dots ('' when none; a marked label is a decoration and leaves no key). A text that is only a label has no
    words."""
    out = _visible(unicodedata.normalize("NFC", text)).strip()
    label = ""
    while True:
        before = out
        out = _BULLET.sub("", out, count=1)
        lead = _LEAD_TOKEN.match(out)
        if lead and lead.end() < len(out) and all(_markish(c) for c in lead.group(1)):
            out = out[lead.end():]
        out = _BOLD_LABEL.sub(lambda m: m.group(2) + (m.group(3) or ":") + " ", out, count=1)
        out = _SECTION.sub("", out, count=1)
        marked = _MARKED_LABEL.match(out)
        if marked and marked.end() < len(out):
            out = out[marked.end():]
        elif not label:
            bare = _BARE_LABEL.match(out)
            if bare and bare.end() < len(out):
                label = _label_key(bare.group(0))
                out = out[bare.end():]
        for left, right in _WRAP:
            if len(out) > len(left) + len(right) and out.startswith(left) and out.endswith(right):
                out = out[len(left):-len(right)]
        for left, right in _BRACKETS:
            if len(out) > 2 and out.startswith(left) and out.endswith(right) and not any(c in out[1:-1] for c in "()[]"):
                out = out[1:-1]
        pair = len(out) > 2 and unicodedata.category(out[0]) in ("Ps", "Pi", "Pf") \
            and unicodedata.category(out[-1]) in ("Pe", "Pf", "Pi") \
            and not any(unicodedata.category(c) in ("Ps", "Pe", "Pi", "Pf") for c in out[1:-1])
        if pair or (len(out) > 2 and out[0] == "<" and out[-1] == ">" and "<" not in out[1:-1]):
            out = out[1:-1]
        out = _INNER_EMPHASIS.sub(r"\2", out)
        out = _INNER_ITALIC.sub(r"\2", out)
        out = _TAG_TAIL.sub("", out)
        out = _END_LABEL.sub("", out)
        tail = _TAIL_TOKEN.search(out)
        if tail and tail.start() > 0 and all(_markish(c) for c in tail.group(1)):
            out = out[:tail.start()]
        out = _strip_paren_tail(out)
        out = out.strip().rstrip(_TRAILING).strip()
        if out == before:
            break
    if _LABEL_ALONE.match(out):
        label = label or _label_key(out)
        out = ""
    return label, " ".join(out.split()).casefold()


def _bare(text):
    """The words of a line with every known decoration stripped (its bare label included)."""
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
