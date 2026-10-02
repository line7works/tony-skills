"""`record-answer`'s shared refusals (ruling E14-11, control room reading CR-3).

One implementation for the four cores. A core maps its own recorded answer onto the neutral view
this module reads, then calls `check` (pure) or `record` (writes `answer.json` only when the
answer is accepted):

    {"questions": [{"id": "Q1", "text": "...", "touches": [<ledger line id>, ...], "answer": "..."}],
     "lines":     [{"text": "...", "tag": "decided" | "assumed" | "parked" | "open" | ...,
                    "trace": {"kind": <trace kind>, "ref": "..."},
                    "row": <ledger line id>}]}

`questions` are the questions the executor put to the owner in this run, each with the ledger
line ids it touches and the owner's answer. `lines` are the lines the executor asserts, each with
its trace. `row` (ruling A5(4)) is the id of the ledger row the line decides, settles, passes
forward or moves; it is absent on a new line, one that names no existing row. A line with no
`row` whose trace is `ledger` names the trace's row; `row` may repeat that trace, never differ from
it. The trace kinds:

    ledger        a ledger line id of the scope doc this run read
    repo_path     a path that exists inside the workspace
    question      the id of a question of this run that the owner answered
    assumed       the executor's why, where the core's lane contract allows assumptions
    owner_words   the owner's words quoted, where the core's lane contract allows them

`DEFAULT_TRACES` is the three E14-11 names; a core passes `allowed` to widen it for its own
lines. The refusals, each `{"rule", "message", ...}` naming the question or line:

    shape              the answer is not the view above (not a refusal a person could fix by
                       asking something else, but it is refused the same way, never repaired);
                       a line whose `row` and `ledger` trace differ is one
    re-asked-decided   a question touches a `decided` ledger line, or its text is a `decided`
                       line's text (every known decoration seen through) whatever it touches;
                       or a line names a `decided` row under the tag `parked`, `open` or `deferred`
                       (architect's deferred list, which blueprint reads as parked): a decided line
                       passes forward and is never moved back; any other tag is the core's own
                       pass-forward vocabulary, not judged here
    unknown-line       a question touches an id the ledger does not hold, or a line's `row`
                       names one
    untraced           a line with no trace, a trace kind the core does not allow, or a trace
                       that names nothing (an unknown ledger id, a path that is not in the
                       workspace, a question not answered in this run, an empty why or quote)
    quietly-resolved   a line asserted as `decided` whose row is a `parked` or `open` ledger
                       line that no ANSWERED question of this run touched (a question asked and
                       left without an answer settles nothing); the line is judged by the id and
                       its words are never matched against its own row. And the guard on the
                       id-less path: a line asserted as `decided` whose words restate a `parked`
                       or `open` row OTHER than the one it names is refused with "name the row's
                       id", whether or not an answered question of this run touched that row: a
                       line that settles a ledger row carries the row's id

Any refusal is exit 5 and nothing is written (station-loop.md section 3.4).

The guard compares a line's words with a row's words with every known decoration stripped on both
sides (`forms` against `row_forms`). An item label is part of the words on both sides, bare
(`R2 `) or marked (`AC1:`, `(R2)`, `[R2]`, `**R2:**`): `R2: budget` never meets `R3: budget`, and a
labelled line still meets an unlabelled row by its words. A line that meets a row it did not
name is cured by naming the row, never by rewording it.

The text match of `re-asked-decided` catches deterministic repetition only: a question whose words,
every known decoration stripped, meet a decided line's words (`forms` against `row_forms`). It does not
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
# `a) `, `- [ ] `, `[x] `, a check or arrow mark), a section label (`Open: `, `Constraint: `, the templates' `When: `,
# `Must be able to: `, `Step 3.1 (...): `), an item label, MARKED (`R2:`, `C3.`, `(R2)`, `[R2]`, `R-2:`, `AC-1:`,
# `R2a:`, `R12.3:`, `R2 <dash> `, bold or italic around it) or BARE (`R2 `, `Q4 `), stripped from the words and kept
# as the label, part of the words when both sides carry one (ruling A5(1)), a wrapping pair of `**`, `*`, `_`, `~~`,
# backticks, quotes, guillemets or brackets, emphasis or an inline link around part of the words, a trailing
# `(waits on: ...)` / `[parked: ...]` / `(assumed: ...)` parenthesis in any bracket kind to any nesting, a trailing
# ` <dash> <tag> (...)` or ` <dash> <tag>: ...` ledger tail, a trailing check, cross, box, emoji, dash or punctuation
# mark (fullwidth included), and invisible characters. The strips run until nothing changes, so two decorations at
# once cannot escape. Text is compared in NFC, so a composed and a decomposed accent read the same; combining marks
# are visible characters (a Thai or Hebrew word keeps its marks); a line break of any kind (U+2028, U+2029, NEL, VT,
# FF) reads as a space.
_BULLET = re.compile(u"^(?:- \\[[ xX]\\]|\\[[ xX]\\]|[-*+\u2022\u2013\u25e6\u2023>\u2713\u2714\u2192\u2705\u2611]|#{1,6}|\\d{1,3}[.)]|\\d{1,3}(?:\\.\\d{1,3})+\\.|\\((?:\\d{1,3}|[a-zA-Z]|[ivxIVX]{1,4})\\)|[a-hj-zA-HJ-Z][.)]|[ivxIVX]{1,4}[.)])\\s+")
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
    return (cat in ("Pd", "So", "Sm", "Sk") or (cat in ("Po", "Pi", "Pf") and ch not in "#%&@/\\\"'"))


def _keyed(ch):
    """A trailing sign that can be the line's meaning (the seam 14 reader, CS14-1): plus, minus, a math sign, an
    arrow, a star, degree or prime; read after NFKC, so a fullwidth plus is a plus. A check, cross, box, emoji,
    dash or punctuation mark is not: it is the ledger's own decoration on both sides."""
    code = ord(ch)
    return (ch in u"+-\u2605\u2606\u00b0\u2032\u2033" or unicodedata.category(ch) == "Sm" or 0x2190 <= code <= 0x21FF
            or 0x27F0 <= code <= 0x27FF or 0x2900 <= code <= 0x297F)
_SECTION = re.compile(r"^(?:constraints?|out of scope|out-of-scope|assumed|assumptions?|open|requirements?|decided|parked|"
                      r"research|questions?|decisions?|deferred|poured concrete(?: \(one-way doors\))?|one-way doors|not in this slice|"
                      r"acceptance criteria|goal|intent|next|discovered|deviations?|build assumptions|punch list|rulings?|components|"
                      r"data flow|diagram|footprint|depends on|status|who|scope doc|plan|exit ramp|changed this run|blind review|"
                      r"artifact|walkthrough target|v0 drawing|handoffs|run log|when|must be able to|step \d+(?:\.\d+)* \([^()]*\))"
                      r"\s*(?::\s+|\uff1a\s*)",
                      re.IGNORECASE)
# The item labels the station forms use (R<n> requirement, AC<n> criterion, C<n> constraint, Q<n> question,
# O<n> open item, A<n> assumption, D<n> decision), with or without a hyphen, a dotted sub-number or a letter
# suffix. MARKED (brackets, a trailing mark, or a following separator, any case) and BARE (the known letters in upper
# case and digits, then a space, no mark) alike: the label of the rule, stripped from the words and kept as their
# key, part of the words when both sides carry one (ruling A5(1): the slice 2 reading of a marked label as mere
# decoration is reversed), so `Q4 budget` is not `Q3 budget`, `R2: budget` is not `R3: budget` and a relabelled line
# is a reworded one (E14-4), while a content token such as `S3`, `IPv6` or `H264` is never a label. The first label
# is the key; a marked label is stripped as often as it appears, and a bare one behind a marked one is words
# (`R2: Q3 budget` carries the label `r2` and the words `q3 budget`). A text that is only a label has no words.
_LABEL_CORE = r"(?:R|AC|C|Q|O|A|D)-?\d{1,5}(?:\.\d{1,3})*[a-z]?"
_MARKED_LABEL = re.compile(r"^(?:[(\[]" + _LABEL_CORE + r"[)\]][.:]?\s*"
                           r"|" + _LABEL_CORE + r"(?:[.:)\uff1a](?!\d)\s*|\s*(?:\u2014|\u2013)\s*|\s+(?:\u00b7|\u2014|\u2013|--|-|:)\s+))"
                           r"(?:\u00b7|\u2014|\u2013|--|-|:)?\s*", re.IGNORECASE)
_BARE_LABEL = re.compile(r"^" + _LABEL_CORE + r"\s+")
_LABEL_KEY = re.compile(_LABEL_CORE, re.IGNORECASE)
_END_LABEL = re.compile(r"\s*[(\[]" + _LABEL_CORE + r"[)\]]$", re.IGNORECASE)
_LABEL_ALONE = re.compile(r"^[(\[]?" + _LABEL_CORE + r"[)\]]?[.:]?$", re.IGNORECASE)
_BOLD_LABEL = re.compile(r"^(\*{1,3}|_{1,3}|`|~~)(" + _LABEL_CORE + r")([.:)]?)\1[ \t]*", re.IGNORECASE)
_LEDGER_WORDS = (r"waits? on|waiting on|parked|assumed|decided|open|needs research|needs prototype|later|"
                 r"deferred|pending|tbd|not now|undecided|to decide|to be decided")
_PAREN_WORDS = re.compile(r"^(?:" + _LEDGER_WORDS + r")\b", re.IGNORECASE)
_TAG_TAIL = re.compile(u"(?:\\s+(?:\u00b7|\u2014|\u2013|--|-)\\s*|\\s*(?:\u00b7|\u2014|\u2013|--|,|;)\\s*)"
                       u"(?:" + _LEDGER_WORDS + u")\\b.*$",
                       re.IGNORECASE)
_WRAP = (("**", "**"), ("~~", "~~"), ("==", "=="), ("*", "*"), ("_", "_"), ("`", "`"), ('"', '"'), (u"\u201c", u"\u201d"),
         ("'", "'"), (u"\u2018", u"\u2019"), (u"\u00ab", u"\u00bb"))
_BRACKETS = (("(", ")"), ("[", "]"))
# Emphasis around part of the words (the seam 12 reader, CS12-2): `**` `~~` and backticks anywhere, `*` around a word
# run, and a single `_` only at word boundaries (the reviewer's P-2 and F2), so an identifier such as `__init__` or
# `snake_case` keeps its underscores.
_INNER_EMPHASIS = re.compile(r"(\*\*|~~|==|`)(?=\S)(.+?)(?<=\S)\1")
_INNER_ITALIC = re.compile(r"(?<!\w)(\*)(?=\S)(.+?)(?<=\S)\1(?!\w)")
# Single-underscore emphasis at word boundaries; keep identifiers and dunder names.
_INNER_UNDERSCORE = re.compile(r"(?<![\w_])_(?!_)(?=\S)(.+?)(?<=\S)(?<!_)_(?![\w_])")
# Read an inline Markdown link by its visible text, never by fetching its destination.
_INLINE_LINK = re.compile(r"(?<!!)\[([^\[\]\r\n]+)\]\((?:[^()\\\r\n]|\\.)*\)")
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
_TAIL_MARK = u"\x03"
_LINE_BREAKS = re.compile(u"[\u2028\u2029\x85\x0b\x0c]")


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
    return " ".join(_visible(unicodedata.normalize("NFC", _LINE_BREAKS.sub(" ", text))).split()).casefold()


def _strip_paren_tail(text):
    """The text without a trailing `(waits on: ...)`, `[parked: ...]` or other ledger parenthesis in any bracket
    kind (a closing bracket of the Pe category and its opener, or an angle pair), to any depth of nesting (lane P's
    round 4 builder: a call such as `(waits on: the bench call (see (Q2) first))`; the seam 14 reader, CS14-2), and
    a ledger parenthesis never closed by hand, `(waits on: a (b)` (CP3B-1); a trailing parenthesis that is not ledger
    words is kept."""
    out = text.rstrip()
    if not out or not (unicodedata.category(out[-1]) == "Pe" or out[-1] == ">"):
        return text
    angle = out[-1] == ">"
    depth = 0
    failed = False
    for index in range(len(out) - 1, -1, -1):
        ch = out[index]
        if (ch == ">") if angle else (unicodedata.category(ch) == "Pe"):
            depth += 1
        elif (ch == "<") if angle else (unicodedata.category(ch) == "Ps"):
            depth -= 1
            if depth == 0 and not failed:
                if _PAREN_WORDS.match(out[index + 1:-1].strip()):
                    return out[:index].rstrip()
                # the last parenthesis is not ledger words: keep walking for a ledger opener further left that was
                # never closed, a hand-written `(waits on: a (b)` (lane P's 3b checker, CP3B-1; the control room's fix)
                failed = True
            elif depth < 0:
                if _PAREN_WORDS.match(out[index + 1:-1].strip()):
                    return out[:index].rstrip()
    return text


def _balanced(text):
    """True when every opening bracket (Ps) inside is closed in order and no closer (Pe) comes first; quotes and
    apostrophes (Pi, Pf) inside never block a wrapper."""
    depth = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat == "Ps":
            depth += 1
        elif cat == "Pe":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _label_key(text):
    return re.sub(r"[^a-z0-9.]", "", text.casefold())


def _split(text):
    """(label, words) of `_split_marks`."""
    return _split_marks(text)[:2]


def _split_marks(text):
    """(label, words, marks): a line's or field's words in NFC with every known decoration stripped, the strips
    repeated until nothing changes; the item label it carried, bare or marked, in front or as a trailing `(R2)`,
    as a key of letters, digits and dots ('' when none; ruling A5(1)); and the trailing sign that can be the
    meaning (`_keyed`: `+`, `-`, a math sign, an arrow, a star, degree or prime; '' when none). A text that is
    only a label has no words."""
    out = _visible(unicodedata.normalize("NFC", _LINE_BREAKS.sub(" ", text))).strip()
    label = ""
    marks = ""
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
            # a marked label is keyed the way a bare one is (ruling A5(1)), and stripped from the words
            label = label or _label_key(_LABEL_KEY.search(marked.group(0)).group(0))
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
            if len(out) > 2 and out.startswith(left) and out.endswith(right) and _balanced(out[1:-1]):
                out = out[1:-1]
        pair = len(out) > 2 and unicodedata.category(out[0]) in ("Ps", "Pi", "Pf") \
            and unicodedata.category(out[-1]) in ("Pe", "Pf", "Pi") \
            and _balanced(out[1:-1])
        if pair or (len(out) > 2 and out[0] == "<" and out[-1] == ">" and "<" not in out[1:-1]):
            out = out[1:-1]
        out = _INLINE_LINK.sub(r"\1", out)
        out = _INNER_UNDERSCORE.sub(r"\1", out)
        out = _INNER_EMPHASIS.sub(r"\2", out)
        out = _INNER_ITALIC.sub(r"\2", out)
        out = _TAG_TAIL.sub("", out)
        end = _END_LABEL.search(out)
        if end:
            label = label or _label_key(_LABEL_KEY.search(end.group(0)).group(0))
            out = out[:end.start()]
        tail = _TAIL_TOKEN.search(out)
        if tail and tail.start() > 0 and all(_markish(c) for c in tail.group(1)):
            key = unicodedata.normalize("NFKC", tail.group(1))
            if all(_keyed(c) for c in key):
                marks = marks or key
            out = out[:tail.start()]
        out = _strip_paren_tail(out)
        out = out.strip().rstrip(_TRAILING).strip()
        if out == before:
            break
    if _LABEL_ALONE.match(out):
        label = label or _label_key(out)
        out = ""
    return label, " ".join(out.split()).casefold(), marks


def _bare(text):
    """The words of a line with every known decoration stripped (its label included)."""
    return _split(text)[1]


def _readings(text, side, later=False):
    """The readings of one text on the LINE side or the ROW side (see `_ROW_MARK`); a later field of a line
    counts only when it holds two or more words (a one-word why or reason field is no item)."""
    label, words, marks = _split_marks(text)
    if not words or (later and len(words.split()) < 2):
        return set()
    if side == "line":
        labels = [label + " ", ""] if label else ["", _ROW_MARK]
        tails = [marks + _TAIL_MARK, ""] if marks else ["", _TAIL_MARK]
    else:
        labels = [label + " ", _ROW_MARK] if label else [""]
        tails = [marks + _TAIL_MARK, _TAIL_MARK] if marks else [""]
    return set(a + b + words for a in labels for b in tails)


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


def label(text):
    """Public: the item label the frame keys for a line or field, exactly as `_split_marks` finds it (bare or
    marked, in front or trailing, in any case, through every decoration and invisible the frame strips): a key
    of letters, digits and dots (`r2`, `ac1`, `r2.3a`), or '' when the text carries none or is not a string.
    A lane asks this instead of re-deriving the frame's label rule (slice 3a round 7, R1)."""
    if not isinstance(text, str):
        return ""
    return _split_marks(text)[0]


def forms(text):
    """Public: every reading of a line's words (for a lane's own rules; E14-3). Compare a line's `forms` with
    a row's `row_forms` by set intersection; the elements are the frame's encoding, not for display."""
    return _forms(text)


def row_forms(text):
    """Public: every reading of a ledger row's words (for a lane's own rules; E14-3)."""
    return _row_forms(text)


def _shape(answer):
    """[(message, where)]: the answer's shape problems, `where` `{"line": index}` (with the line's `text` when
    it has one) for a problem of one line (the index in the answer the frame was given, as every other line
    refusal carries it, so a core's view can map it to the line's place and report one line once; CA3B-3) and
    `{}` for a problem of the answer or a question."""
    if not isinstance(answer, dict):
        return [("the answer is not an object", {})]
    problems = []
    for key in ("questions", "lines"):
        if not isinstance(answer.get(key), list):
            problems.append(("the answer's %r is a list" % key, {}))
    if problems:
        return problems
    ids = []
    for index, q in enumerate(answer["questions"]):
        if not isinstance(q, dict) or not isinstance(q.get("id"), str) or not q["id"].strip():
            problems.append(("question %d carries no id" % index, {}))
            continue
        if not isinstance(q.get("touches", []), list):
            problems.append(("question %s: 'touches' is a list of ledger line ids" % q["id"], {}))
        if not isinstance(q.get("text"), str) or not q["text"].strip():
            # a question with no text would skip the decided-text match (C3-1, round 4)
            problems.append(("question %s carries no text" % q["id"], {}))
        ids.append(q["id"])
    if len(ids) != len(set(ids)):
        problems.append(("two questions share an id", {}))
    for index, line in enumerate(answer["lines"]):
        where = {"line": index}
        if not isinstance(line, dict) or not isinstance(line.get("text"), str):
            problems.append(("line %d is not an object with its text" % index, where))
            continue
        if "row" not in line:
            continue
        # the line is an object with its text here: name it by its words, as every other line refusal does (CF3B2-1)
        where = {"line": index, "text": line["text"]}
        if not isinstance(line["row"], str) or not line["row"].strip():
            problems.append(("the line %r: 'row' is the id of a ledger line" % line["text"], where))
            continue
        trace = line.get("trace")
        if isinstance(trace, dict) and trace.get("kind") == "ledger" and trace.get("ref") != line["row"]:
            # `row` may repeat a ledger trace, never differ from it (R4-1)
            problems.append(("the line %r names row %s but traces to ledger row %s"
                             % (line["text"], line["row"], trace.get("ref")), where))
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


# the tags that move a decided row back (C3): parked, open, and architect's deferred, which blueprint's ledger
# view reads as parked
MOVED_BACK = ("parked", "open", "deferred")


def check(answer, ledger_lines, workspace=None, allowed=DEFAULT_TRACES):
    """{"exit": 0 | 5, "refusals": [...]}; pure, nothing written."""
    problems = _shape(answer)
    if problems:
        return {"exit": exits.REFUSED,
                "refusals": [_refusal("shape", message, **where) for message, where in problems]}
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
        # the row this line names (R4-1): its `row`, else the ref of a `ledger` trace, else none (a new line)
        named = line.get("row")
        if named is None and kind == "ledger":
            named = ref
        stop = False
        if "row" in line and named not in ledger:
            refusals.append(_refusal("unknown-line", "the line %r names the row %r, which is no line of the scope "
                                     "doc's ledger" % (line["text"], named), line_id=named, **where))
            stop = True
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
            stop = True
        if stop:
            continue
        row_named = ledger.get(named) if named is not None else None
        tag = line.get("tag")
        if row_named is not None and row_named["tag"] == "decided" and tag in MOVED_BACK:
            # C3 (as the control room narrowed it in slice 3a, `deferred` added by C3A-2): a decided line named as
            # `parked`, `open` or `deferred` is moved back, the same act as a question that re-asks it; any other
            # tag is the core's own pass-forward vocabulary (a blueprint `constraint`, an architect or inspect tag)
            # and the frame does not judge it
            refusals.append(_refusal("re-asked-decided", "the line %r names the decided ledger line %s as %s; a "
                                     "decided line passes forward and is never moved back to parked, open or deferred"
                                     % (line["text"], named, tag), line_id=named, **where))
            continue
        if tag != "decided":
            continue
        if row_named is not None and row_named["tag"] in ("parked", "open") and named not in touched:
            # R4-2: settling a row by its id takes an answered question of this run touching that row; the
            # line's words are never matched against its own row
            refusals.append(_refusal("quietly-resolved", "the line %r is asserted as decided, but its ledger "
                                     "line %s is %s and no question of this run settled it"
                                     % (line["text"], named, row_named["tag"]), **where))
            continue
        # R4-3: an answered question does not substitute for the line's row id.
        # Compare against every parked or open row other than the row it names.
        # (The guard on the id-less path: a decided line's words, every reading and every known decoration
        # seen through; a meeting is a row settled without its id: lane P's CP1-1, lane L's CS-4, the slice 2
        # escapes and the slice 3c review's F3, each closed as a class, not an instance.)
        candidates = _forms(line["text"])
        for row in ledger_lines:
            if (row["tag"] in ("parked", "open") and row["id"] != named
                    and candidates & _row_forms(row["text"])):
                refusals.append(_refusal("quietly-resolved", "the line %r is asserted as decided under a %s trace, "
                                         "but it restates the %s ledger line %s without naming it: a line that "
                                         "settles a ledger row carries the row's id (`row`)"
                                         % (line["text"], kind, row["tag"], row["id"]), **where))
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
