"""record-answer's own content checks, and the view the shared refusals read (contract section 7).

The shared refusals (E14-11) are `station_core/answer.py`'s, called once with `view(answer)` and
`ALLOWED_TRACES`; this module never repeats them. `view` maps every line of the answer to the
shared shape by its own tag: a requirement and a constraint are what the build doc asserts as
settled, so they are `decided` there and a line of either kind that traces to a `parked` or
`open` ledger line is held to the shared `quietly-resolved` rule; an out-of-scope line is tagged
`out-of-scope`, since carrying a parked scope line or a deferred architecture line forward as out
of scope is the pass-forward E14-11 names, not a resolution. A scope `Open:` item is the owner's
call and not a descoping: an out-of-scope line that carries one forward with no answered question
of this run touching it is this core's own refusal, `open-item-descoped`, by the item's id and by
its words alike (round 3, R3), whatever the line's trace. The words are compared through the frame's
own readings (round 4, R1; E14-3): the line through `station_core.answer.forms`, the row through
`row_forms`, so every decoration the frame knows (a trailing period, a marked label, a list mark, an
invisible character, a ledger tail, the row decorated) is seen through the same way the shared
`quietly-resolved` rule sees through it. This core adds only what the frame has no reading for: the
item before its reason (cut at the first dash, colon, semicolon, comma or parenthesis, after a
leading list mark and section label such as `Out of scope:`).

The view carries each line's ORIGINAL text (round 5, R3): the shared forms own every decoration, a
marked label such as `R2 <dash> ` or `R12: ` included, and a BARE item label (`R4 `, `R12.3 `) is part
of the words when both sides carry one (the frame's rule): `R4 budget approval` is not the parked
`R3 budget approval`, `R12.3 W` is the parked `W`, and a plain `budget approval` is the parked
`R3 budget approval`. This core's own readings keep the label too: the reason cut is taken from the
line as written and from its bare words with the line's bare label put back in front, never from a
label-free reading of a labelled line.

The trace kinds this core allows (ruling R1 of round 2, the owner's words as a trace): `ledger`,
`repo_path`, `question` and `owner_words` (the owner's words quoted verbatim, not blank: the schema
refuses a blank quote). `assumed` is refused for these lines: assumptions have their own field.

`own(answer, run_input, harvest)` returns blueprint's own refusals, each `{"rule", "message", ...}`
in the shared shape, one per finding:

    session-mismatch          the answer's session_id is not the input's invocation.session_id
    run-id-mismatch           the answer's run_id is not this run's
    criterion-without-verify  a criterion with no `verify` form, or one that is none of the three forms
                              (`VERIFY_FORMS`, round 3 R4: a named test, a path, steps of two words;
                              round 4 R2: the rest after the prefix holds a letter or digit)
    open-item-descoped        an out-of-scope line carrying a scope `Open:` item, by its id or by its
                              words, that no answered question of this run touched
    duplicate-id              two lines, two criteria or two slices sharing an id or a name
    unknown-id                a slice naming a requirement line, a criterion or a slice that is not there
    depends-forward           a slice depending on itself or on a slice after it
    unplaced                  with a build doc: a requirement line or a criterion no slice carries
    no-slice                  needs_build_doc true with no slice
    slices-without-build-doc  needs_build_doc false with slices
    feature-not-hunted        the answer's feature is not the name the build hunt ran with
"""
import re
import unicodedata

from station_core import answer as shared

ALLOWED_TRACES = ("ledger", "repo_path", "question", "owner_words")
RULES = ("session-mismatch", "run-id-mismatch", "criterion-without-verify", "open-item-descoped",
         "duplicate-id", "unknown-id", "depends-forward", "unplaced", "no-slice", "slices-without-build-doc",
         "feature-not-hunted")
# the tag each line of the answer carries in the view the shared refusals read
VIEW_TAGS = {"requirement": "decided", "constraint": "decided", "out-of-scope": "out-of-scope"}
# the build doc template's three verify forms, and what each must hold (round 3, R4): `existing test`
# names the test, one token; `new test at` a path that looks like one, one token holding a `/` or a
# file extension; `manual:` steps of at least two words. A placeholder (`TBD`, `n/a`, `later`) is
# none of them, and neither is a token with no letter or digit (`?`, `/`, `- -`; round 4, R2).
VERIFY_FORMS = ("existing test <name>", "new test at <path>", "manual: <steps>")
EXISTING = re.compile(r"^existing test (\S+)$")
NEW = re.compile(r"^new test at (\S+)$")
MANUAL = re.compile(r"^manual: (\S+(?:\s+\S+)+)$")
EXTENSION = re.compile(r"\.[A-Za-z0-9]+$")
PLACEHOLDERS = frozenset(("tbd", "tba", "tbc", "todo", "na", "none", "null", "nil", "later", "soon", "unknown",
                          "pending", "fixme", "wip", "xxx", "somewhere", "sometime", "whatever", "etc"))
# a leading list mark or section label, left out before the reason cut (the item label is kept: round 5, R3)
LIST_MARK = re.compile(r"^[-*+]\s+")
LABEL = re.compile(r"^(?:constraints?|out of scope|out-of-scope|assumed|assumption|open|requirement)\s*:\s*",
                   re.I)
# where an out-of-scope line's item ends and its reason begins (round 3, R3; round 4, R1 adds the comma)
REASON = re.compile(r"\s+[\u2014\u2013]\s+|\s+--?\s+|:\s+|;\s+|,\s+|\s+\(")
# a bare item label as the station forms write one (the frame's label letters; round 5, R3), and two labels
# no line of a real answer carries, used to ask the frame's own rule whether a line carries a bare label
ITEM_LABEL = re.compile(r"^(?:R|AC|C|Q|O|A|D)-?\d{1,5}(?:\.\d{1,3})*[a-z]?$")
PROBE_LABELS = ("D99999", "A99998")


def _refusal(rule, message, **where):
    row = {"rule": rule, "message": message}
    row.update(where)
    return row


def words(text):
    """A line without its leading list mark or section label (`Out of scope:`, `Constraint:`), so the
    reason cut finds the item's own separator; its item label (`R4 `) is kept (round 5, R3)."""
    if not isinstance(text, str):
        return text
    out = text.strip()
    for _ in range(3):
        before = out
        out = LIST_MARK.sub("", out, count=1)
        out = LABEL.sub("", out, count=1)
        out = out.strip()
        if out == before:
            break
    return out or text


def _labelled_bare(text):
    """The line's bare words (`station_core.answer.bare`) with its bare item label put back in front, so a
    reading taken from them keeps the label (round 5, R3); the bare words alone for an unlabelled line;
    None when the line carries a bare label this core cannot place (then no reading is taken from them).
    Whether the line carries one is the frame's own rule, asked through the public forms: an unlabelled
    line meets a row of its words under any label, a labelled line meets only its own label's."""
    bare = shared.bare(text)
    if not bare:
        return None
    line = shared.forms(text)
    if all(line & shared.row_forms(probe + " " + bare) for probe in PROBE_LABELS):
        return bare
    for token in text.split():
        token = "".join(ch for ch in token if unicodedata.category(ch) != "Cf")
        # a marked label (`R2:`, `(R2)`, `[R2]`, `**R2:**`, `r2:`, `r2 : `) is a label as the bare one is (ruling
        # A5(1)); the frame keys a marked label in any case, and this loop runs only for a line the frame reads as
        # labelled, the forms check below confirming the label, so a token's letters are read in upper case whether
        # or not a mark was stripped from it (`r2 : budget`, whose colon is a token of its own)
        token = token.strip("*_`~").lstrip("([").rstrip(".:)]\uff1a").strip("*_`~")
        token = re.sub(r"^[A-Za-z]+", lambda m: m.group(0).upper(), token)
        if ITEM_LABEL.match(token) and line & shared.row_forms(token + " " + bare):
            return token + " " + bare
    return None


def line_forms(text):
    """Every reading of an out-of-scope line's words, all of them the frame's (`station_core.answer.forms`):
    the line as written, the line without a leading list mark or section label (`words`), and the item
    before its reason, cut from those words and from the bare words with the line's bare label kept
    (`_labelled_bare`). Compared with `station_core.answer.row_forms` of a row."""
    if not isinstance(text, str):
        return set()
    stripped = words(text)
    out = set(shared.forms(text)) | set(shared.forms(stripped))
    for base in (stripped, _labelled_bare(stripped)):
        if not base:
            continue
        cut = REASON.search(base)
        if cut and base[:cut.start()].strip():
            out |= shared.forms(base[:cut.start()])
    out.discard("")
    return out


def view(answer):
    """The answer as the shared refusals read it: its questions, and its lines tagged by `VIEW_TAGS`,
    each line's ORIGINAL text (round 5, R3: the shared forms own the decorations, and a bare label is
    part of the words when both sides carry one)."""
    lines = []
    for line in answer.get("lines") or []:
        row = {"text": line.get("text"), "tag": VIEW_TAGS.get(line.get("tag"), "decided")}
        if "trace" in line:
            row["trace"] = line["trace"]
        lines.append(row)
    return {"questions": answer.get("questions"), "lines": lines}


def _placeholder(token):
    """A token that names nothing: one with no letter or digit (round 4, R2), or a placeholder, whole or
    as any one of its path parts."""
    if not any(ch.isalnum() for ch in token):
        return True
    for part in [token] + re.split(r"[/\\]", token):
        if re.sub(r"[^a-z0-9]", "", EXTENSION.sub("", part).casefold()) in PLACEHOLDERS:
            return True
    return False


def _verify_holds(value):
    """One of the template's three verify forms, on one line, naming something real."""
    if not isinstance(value, str) or "\n" in value or "\r" in value:
        return False
    value = value.strip()
    match = EXISTING.match(value)
    if match:
        return not _placeholder(match.group(1))
    match = NEW.match(value)
    if match:
        path = match.group(1)
        return ("/" in path or EXTENSION.search(path) is not None) and not _placeholder(path)
    match = MANUAL.match(value)
    if match:
        steps = match.group(1).split()
        return not all(_placeholder(step) for step in steps)
    return False


def _answered_touches(answer):
    """The ledger ids an answered question of this run touches (an unanswered one settles nothing)."""
    out = set()
    for q in answer.get("questions") or []:
        if isinstance(q, dict) and isinstance(q.get("answer"), str) and q["answer"].strip():
            out.update(t for t in q.get("touches") or [] if isinstance(t, str))
    return out


def own(answer, run_input, harvest):
    refusals = []
    session = ((run_input or {}).get("invocation") or {}).get("session_id")
    if answer.get("session_id") != session:
        refusals.append(_refusal("session-mismatch", "the answer names the session %r, and this run's input "
                                 "names %r: the recorded answer is the executor's of this session"
                                 % (answer.get("session_id"), session)))
    if answer.get("run_id") != (run_input or {}).get("run_id"):
        refusals.append(_refusal("run-id-mismatch", "the answer names the run %r, and this run is %r"
                                 % (answer.get("run_id"), (run_input or {}).get("run_id"))))
    for index, criterion in enumerate(answer.get("criteria") or []):
        verify = criterion.get("verify")
        if not _verify_holds(verify):
            what = "carries no verify form" if not (isinstance(verify, str) and verify.strip()) else (
                "carries the verify %r, which is none of the forms" % verify)
            refusals.append(_refusal("criterion-without-verify", "the criterion %r %s (existing test | new test at "
                                     "<path> | manual: <steps>); a criterion a grader cannot check is not a "
                                     "criterion" % (criterion.get("text"), what), criterion=index,
                                     text=criterion.get("text")))

    ledger = dict((row["id"], row) for row in (harvest or {}).get("ledger_view") or [])
    settled = _answered_touches(answer)
    open_rows = [row for row in ledger.values() if row.get("tag") == "open" and isinstance(row.get("text"), str)]
    for index, line in enumerate(answer.get("lines") or []):
        if line.get("tag") != "out-of-scope":
            continue
        trace = line.get("trace") if isinstance(line.get("trace"), dict) else {}
        ref = trace.get("ref")
        # by its id (a ledger trace to the open item) or by its words (round 3, R3), whatever the trace,
        # the words read through the frame's own readings on both sides (round 4, R1)
        carried = []
        if trace.get("kind") == "ledger" and ref in ledger and ledger[ref].get("tag") == "open":
            carried.append(ledger[ref])
        forms = line_forms(line.get("text"))
        carried.extend(row for row in open_rows if forms & shared.row_forms(row["text"]))
        carried = next((row for row in carried if row["id"] not in settled), None)
        if carried is not None:
            refusals.append(_refusal("open-item-descoped", "the out-of-scope line %r carries the scope doc's open "
                                     "item %r (%s) forward as out of scope, and no answered question of this run "
                                     "touched it: an open item is the owner's call, not a descoping; ask him, or "
                                     "keep it an open question" % (line.get("text"), carried.get("text"),
                                                                   carried["id"]),
                                     line=index, text=line.get("text"), line_id=carried["id"]))

    lines = answer.get("lines") or []
    criteria = answer.get("criteria") or []
    slices = answer.get("slices") or []
    for what, items, key in (("line", lines, "id"), ("criterion", criteria, "id"), ("slice", slices, "name")):
        seen = set()
        for item in items:
            value = item.get(key)
            if value is None:
                continue
            if value in seen:
                refusals.append(_refusal("duplicate-id", "two of the answer's %ss share the %s %r"
                                         % (what, "name" if key == "name" else "id", value), id=value))
            seen.add(value)

    requirement_ids = set(l["id"] for l in lines if l.get("tag") == "requirement" and l.get("id"))
    criterion_ids = set(c["id"] for c in criteria if c.get("id"))
    existing = [s["name"] for s in ((harvest or {}).get("build") or {}).get("slices") or []]
    order = [s.get("name") for s in slices]
    for position, sl in enumerate(slices):
        name = sl.get("name")
        for ident in sl.get("requirements") or []:
            if ident not in requirement_ids:
                refusals.append(_refusal("unknown-id", "slice %s names the requirement %r, and no requirement "
                                         "line of the answer has that id" % (name, ident), slice=name, id=ident))
        for ident in sl.get("criteria") or []:
            if ident not in criterion_ids:
                refusals.append(_refusal("unknown-id", "slice %s names the criterion %r, and no criterion of the "
                                         "answer has that id" % (name, ident), slice=name, id=ident))
        for dep in sl.get("depends_on") or []:
            if dep in order[position:]:
                refusals.append(_refusal("depends-forward", "slice %s depends on slice %s, which is itself or comes "
                                         "after it: slices are dependency-ordered" % (name, dep), slice=name, id=dep))
            elif dep not in order and dep not in existing:
                refusals.append(_refusal("unknown-id", "slice %s depends on slice %s, which neither the answer nor "
                                         "the existing build doc holds" % (name, dep), slice=name, id=dep))

    needs = ((answer.get("ceremony") or {}).get("needs_build_doc"))
    if needs is False and slices:
        refusals.append(_refusal("slices-without-build-doc", "the answer says this does not need a build doc and "
                                 "carries %d slice(s)" % len(slices)))
    if needs is True:
        if not slices:
            refusals.append(_refusal("no-slice", "the answer needs a build doc and carries no slice"))
        placed_r = set(i for s in slices for i in s.get("requirements") or [])
        placed_c = set(i for s in slices for i in s.get("criteria") or [])
        for index, line in enumerate(lines):
            if line.get("tag") == "requirement" and line.get("id") not in placed_r:
                refusals.append(_refusal("unplaced", "the requirement %r is carried by no slice%s, so the build "
                                         "doc would drop it" % (line.get("text"), "" if line.get("id") else
                                                                 " (it has no id a slice could name)"),
                                         line=index, text=line.get("text")))
        for index, criterion in enumerate(criteria):
            if criterion.get("id") not in placed_c:
                refusals.append(_refusal("unplaced", "the criterion %r is carried by no slice%s, so the build doc "
                                         "would drop it" % (criterion.get("text"), "" if criterion.get("id") else
                                                            " (it has no id a slice could name)"),
                                         criterion=index, text=criterion.get("text")))
        hunted = (harvest or {}).get("build_name")
        if answer.get("feature") != hunted:
            refusals.append(_refusal("feature-not-hunted", "the answer's feature is %r, and the build hunt ran "
                                     "with --name %r: a doc for %r was never looked for, so writing one could "
                                     "fork a second plan" % (answer.get("feature"), hunted, answer.get("feature"))))
    return refusals
