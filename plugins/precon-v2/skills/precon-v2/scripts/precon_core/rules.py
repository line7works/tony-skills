"""precon-v2's own refusals of a recorded answer (lane contract section 5).

Run after `station_core/answer.py`'s shared refusals, never instead of them: a line with no trace,
a trace naming nothing, a re-asked decided line and a parked or open line quietly resolved are the
shared rules' (`untraced`, `re-asked-decided`, `unknown-line`, `quietly-resolved`), and nothing
here repeats them. One refusal here carries the shared `quietly-resolved` name because it is that
rule's family on a path the frame does not read (the out-of-scope items, A13, below). Each refusal
is `{"rule", "message", ...where}`, the shared shape. Any refusal is exit 5 and nothing is written.

The rules, each named once:

    run-mismatch            the answer's run_id is not this run's
    session-mismatch        the answer's session_id is not the input's invocation.session_id
    decided-without-source  a decided line traced as an assumption, or an assumed ledger line
                            asserted as decided with no answered question of this run touching it
    assumed-without-why     an assumed line whose trace is not its why (kind `assumed`), unless it
                            passes an assumed ledger line forward
    parked-without-reason   a parked line whose reason is none of: needs research, needs
                            prototype, waiting on <x>
    open-without-call       an open line that does not say which call of the owner's it waits on
    source-kind             a parked or open line, or an out-of-scope item, traced to anything but
                            the owner's words or a question he answered
    retagged                a line naming a ledger line (by `row` or a `ledger` trace, the id
                            being the trace) under another tag, other than a parked, open or
                            assumed line settled as decided, or a parked line passed forward with
                            another reason; a line or a new open item that repeats the words of a
                            Decisions or Open ledger line under any trace but that line's id
                            (`scopedoc.twins`: the frame's readings of the line against the
                            frame's readings of the row, `forms(line) & row_forms(row)`, the row
                            the line names left out); an out-of-scope item that does, or names
                            such a line by `row`, unless it names a parked, open or assumed line
                            by `row` and an answered question of this run (not one marked needs
                            research) touched that line (the write then removes that row; the
                            item's words alone after such a question are `quietly-resolved`
                            below); an out-of-scope item ruling out a row this answer settles
                            as decided by its id; two entries of one answer whose readings meet,
                            one read as a line and the other as a row (`forms(a) &
                            row_forms(b)`, both ways): each a twin the doc would hold beside the
                            line it repeats
    quietly-resolved        (the frame's family, on the out-of-scope path the frame does not read)
                            an out-of-scope item whose words repeat a parked, open or assumed
                            ledger line it does not name by `row`, after an answered question of
                            this run touched that line: ruling a row out moves it, so the item
                            carries the row's id and the question never stands in for it (A13,
                            under A5(4))
    research-resolved       a question marked needs research that a line or an out-of-scope item
                            of this run resolves, or that leaves a parked line of another reason
    research-not-parked     a question marked needs research that leaves no parked line
    napkin-outcome          "no scope doc" asked for outside napkin, with lines, over a doc, or with
                            a sitting that continues
    doc-fields              a new doc without its title and intent, or those fields on an
                            existing doc
    gate-missing            no gate line, a blank one, or one that is not one line (`text.blank` and
                            `text.one_line`: a line separator, a format character or an invisible
                            letter anywhere in it refuses it)
    unrenderable            a value the scope doc or the cold-read doc cannot carry and read back
                            (an open line's call with unbalanced or two-deep parentheses among them)
    exit-test-rows          the exit test's rows are not the rows this run built requests for
    exit-test-unrecorded    a built request with no result recorded by readers
    disposition-before-raw  dispositions in the run that writes the readers' raw text
    disposition             a disposition outside the three, left downstream with no why, for a
                            row with no section, or with no summary
    cold-read-doc           dispositions for a cold-read doc this run did not select
"""
from . import exit_test, scopedoc, text

# the trace kinds a parked or open line, and an out-of-scope item, may carry: the owner's words or
# a question he answered (a line passed forward by its ledger id is checked as a pass-forward)
SOURCES = ("owner_words", "question")


def refusal(rule, message, **where):
    row = {"rule": rule, "message": message}
    row.update(where)
    return row


_blank = blank = text.blank


def check(answer, run_input, harvest, requests, run_dir):
    out = []
    if answer.get("run_id") != run_input.get("run_id"):
        out.append(refusal("run-mismatch", "the answer names run %r; this run is %r"
                           % (answer.get("run_id"), run_input.get("run_id"))))
    expected = (run_input.get("invocation") or {}).get("session_id")
    if answer.get("session_id") != expected:
        out.append(refusal("session-mismatch", "the answer names session %r; the input's invocation, read by the "
                                               "adapter, names %r" % (answer.get("session_id"), expected)))
    gate = answer.get("gate")
    if not text.one_line(gate):
        out.append(refusal("gate-missing", "the answer carries no gate line: one line justifying that every branch "
                                           "was visited or parked"))
    out += _one_answer(answer)
    out += _lines(answer, harvest)
    out += _items(answer, harvest)
    out += _research(answer, harvest)
    out += _triage(answer, harvest)
    out += _exit_test(answer, harvest, requests, run_dir)
    return out


def _settling(answer, ident):
    """The answered questions of this run, none marked needs research, that touch ledger line `ident`."""
    return [q["id"] for q in answer.get("questions") or []
            if ident in (q.get("touches") or []) and not _blank(q.get("answer")) and not q.get("needs_research")]


def _one_answer(answer):
    """Two entries of one answer (lines, out-of-scope items, open items, in any mix) whose frame
    readings meet, one read as a line and the other as a row (`forms(a) & row_forms(b)` or
    `forms(b) & row_forms(a)`), under any tags (CP2-2, R3 of round 5): the doc would hold both."""
    out, seen = [], []
    entries = [("line %d" % i, line.get("text"), {"line": i}) for i, line in enumerate(answer.get("lines") or [])]
    entries += [("out-of-scope item %d" % i, item.get("text"), {"out_of_scope": i})
                for i, item in enumerate(answer.get("out_of_scope") or [])]
    entries += [("open item %d" % i, item, {"open_items": i}) for i, item in enumerate(answer.get("open_items") or [])]
    for label, value, where in entries:
        forms = text.readings(value)
        if not forms:
            continue
        rows = text.row_readings(value)
        # each entry read as a line against the other read as a row, both ways (R3 of round 5): two line-side
        # readings meet through their unlabelled alternatives, so `Q3 budget` and `Q4 budget` would be one
        prior = next((name for name, earlier, earlier_rows in seen if forms & earlier_rows or earlier & rows), None)
        if prior is not None:
            out.append(refusal("retagged", "the answer asserts %r twice (%s and %s): one line per item, or the doc "
                                           "holds an item and its twin" % (value, prior, label), **where))
        seen.append((label, forms, rows))
    return out


def _lines(answer, harvest):
    out = []
    rows = harvest.get("ledger") or []
    ledger = dict((row["id"], row) for row in rows)
    research = set(q["id"] for q in answer.get("questions") or [] if q.get("needs_research"))
    for index, line in enumerate(answer.get("lines") or []):
        where = {"line": index, "text": line.get("text")}
        tag = line.get("tag")
        trace = line.get("trace") if isinstance(line.get("trace"), dict) else {}
        kind, ref = trace.get("kind"), trace.get("ref")
        # the row the line names, by `row` or a `ledger` trace (R8a of 3b): the id is the trace (A5(4)), so the
        # named row is judged by its id and never matched against the line's own words
        own = scopedoc.named(line)
        twin = next(iter(scopedoc.twins(line.get("text"), rows, own=own)), None)
        if twin is not None:
            # the shared quietly-resolved covers a parked or open line's words asserted as decided without the
            # row's id, a question touching it or not (F3); this covers every twin, under every trace kind, a ledger trace to
            # another line included (an assumed or decided line repeated, a parked or open line repeated
            # even after a question touched it, an Open line this core wrote with its `(waits on: ...)`
            # named by its bare words, any tag): the doc would hold the line and its twin, so the line is
            # passed forward, or settled, by its id only (CP1-1)
            out.append(refusal("retagged", "the line %r repeats the %s ledger line %s: pass it forward by its "
                                           "id, and settle it only with an answered question that touches it"
                               % (line.get("text"), twin["tag"], twin["id"]), **where))
        if own in ledger:
            # a line naming its row by `row` reads as one naming it by a `ledger` trace (R8a of 3b): passed
            # forward under the row's own tag (a parked row with its own reason), settled as decided by an
            # answered question, or refused `retagged`, so the doc never holds the line beside its unchanged row
            row = ledger[own]
            if tag == row["tag"]:
                if tag == "parked" and "reason" in line and line.get("reason") != row["source"]:
                    out.append(refusal("retagged", "the line %r passes the parked line %s forward with the reason %r; "
                                                   "the ledger says %r" % (line.get("text"), own, line.get("reason"),
                                                                           row["source"]), **where))
            elif tag == "decided" and row["tag"] in ("parked", "open", "assumed"):
                qids = [q["id"] for q in answer.get("questions") or []
                        if own in (q.get("touches") or []) and not _blank(q.get("answer"))]
                settling = [q for q in qids if q not in research]
                if row["tag"] == "assumed" and not settling:
                    out.append(refusal("decided-without-source", "the line %r turns the assumed line %s into a decision "
                                                                 "that no answered question of this run touches"
                                       % (line.get("text"), own), **where))
                if row["tag"] in ("parked", "open") and qids and not settling:
                    out.append(refusal("research-resolved", "the line %r resolves %s, which only a question marked "
                                                            "needs research touches; it stays parked"
                                       % (line.get("text"), own), **where))
            else:
                out.append(refusal("retagged", "the line %r is asserted as %s, but its ledger line %s is %s"
                                   % (line.get("text"), tag, own, row["tag"]), **where))
            # a line naming its row by `row` under another trace kind still answers for that trace: a decided line
            # is never sourced by an assumption, and nothing resolves a needs-research question
            if kind == "ledger" or kind is None:
                continue
            if tag == "decided" and kind == "assumed":
                out.append(refusal("decided-without-source", "the line %r is asserted as decided with an assumption for "
                                                             "its source: a decided line traces to the owner's words, an "
                                                             "answered question or the repo" % line.get("text"), **where))
            if tag in ("decided", "assumed") and kind == "question" and ref in research:
                out.append(refusal("research-resolved", "the line %r resolves question %s, which is marked needs "
                                                        "research: it is a parked line, never resolved in the run"
                                   % (line.get("text"), ref), **where))
            continue
        if tag in ("parked", "open") and kind is not None and kind not in SOURCES:
            out.append(refusal("source-kind", "the %s line %r carries a %s trace: a %s line traces to the owner's words "
                                              "or a question he answered" % (tag, line.get("text"), kind, tag), **where))
        if tag == "decided" and kind == "assumed":
            out.append(refusal("decided-without-source", "the line %r is asserted as decided with an assumption for "
                                                         "its source: a decided line traces to the owner's words, an "
                                                         "answered question or the repo" % line.get("text"), **where))
        if tag == "assumed" and kind is not None and kind != "assumed":
            out.append(refusal("assumed-without-why", "the line %r is assumed but carries a %s trace, not its why"
                               % (line.get("text"), kind), **where))
        if tag in ("decided", "assumed") and kind == "question" and ref in research:
            out.append(refusal("research-resolved", "the line %r resolves question %s, which is marked needs "
                                                    "research: it is a parked line, never resolved in the run"
                               % (line.get("text"), ref), **where))
        if tag == "parked" and kind == "question" and ref in research and line.get("reason") != "needs research":
            out.append(refusal("research-resolved", "the line %r parks question %s, which is marked needs research, "
                                                    "as %r: what a needs-research question leaves is a parked "
                                                    "needs research line" % (line.get("text"), ref, line.get("reason")),
                               **where))
        if tag == "parked" and not scopedoc.valid_parked(line.get("reason")):
            out.append(refusal("parked-without-reason", "the parked line %r carries the reason %r: one of needs "
                                                        "research, needs prototype, waiting on <x>"
                               % (line.get("text"), line.get("reason")), **where))
        if tag == "open" and _blank(line.get("waits_on")):
            out.append(refusal("open-without-call", "the open line %r does not say which of the owner's calls it "
                                                    "waits on" % line.get("text"), **where))
    return out


def _items(answer, harvest):
    out = []
    rows = harvest.get("ledger") or []
    ledger = dict((row["id"], row) for row in rows)
    # the rows this answer settles as decided by their id (a `ledger` trace or `row`)
    decided = set(scopedoc.named(line) for line in answer.get("lines") or []
                  if isinstance(line, dict) and line.get("tag") == "decided" and scopedoc.named(line) in ledger)
    for index, item in enumerate(answer.get("out_of_scope") or []):
        trace = item.get("trace") if isinstance(item.get("trace"), dict) else {}
        kind = trace.get("kind")
        if kind is not None and kind not in SOURCES:
            out.append(refusal("source-kind", "the out-of-scope item %r carries a %s trace: what the owner ruled out "
                                              "traces to his words or a question he answered" % (item.get("text"), kind),
                               out_of_scope=index))
        own = scopedoc.named(item)
        ruled = scopedoc.twins(item.get("text"), rows, own=own)
        if own in ledger:
            # the row the item names by `row` (R8b of 3b): ruled out by its id, whatever the item's words
            ruled.insert(0, ledger[own])
        both = next((row for row in ruled if row["id"] in decided), None)
        if both is not None:
            # CP4-2: one answer settling a row as decided and ruling the same row out would leave the doc
            # holding the item decided and out of scope at once
            out.append(refusal("retagged", "the answer settles %s as decided and rules it out (the out-of-scope item "
                                           "%r): one ruling per item" % (both["id"], item.get("text")),
                               out_of_scope=index))
            continue
        # A13 (A5(4)): ruling a row out moves it, so the item names that row by its id (`row`); only the row it
        # names may pass, and only when an answered question of this run touched it. A row the item's words
        # repeat without naming it never passes, whether or not a question touched it
        twin = next((row for row in ruled
                     if row["id"] != own
                     or not (row["tag"] in ("parked", "open", "assumed") and _settling(answer, row["id"]))), None)
        if twin is not None and twin["id"] != own and twin["tag"] in ("parked", "open", "assumed") \
                and _settling(answer, twin["id"]):
            # the frame's `quietly-resolved` family on the out-of-scope path the frame does not read: an answered
            # question touching the row does not stand in for its id
            out.append(refusal("quietly-resolved", "the out-of-scope item %r rules out the %s ledger line %s by its "
                                                   "words without naming it: an answered question touching the line "
                                                   "does not stand in for its id; an item that moves a ledger row "
                                                   "out of scope carries the row's id (`row`)"
                               % (item.get("text"), twin["tag"], twin["id"]), out_of_scope=index))
            continue
        if twin is not None:
            # CP2-3: ruling out a parked or open line is settling it, so only an answered question of this run
            # that touches it opens the way (and the write then removes the row, R4); a decided line is never
            # ruled out, by its words or its id
            how = "names" if twin["id"] == own else "repeats"
            if twin["id"] == own and twin["tag"] == "decided":
                # the same refusal, its own sentence (R2 of 3b round 2, wording only): a question touching a
                # decided row is the frame's `re-asked-decided`, so the word-twin sentence is untrue here
                out.append(refusal("retagged", "the out-of-scope item %r names the decided ledger line %s: a decided "
                                               "line is settled in place and is not ruled out; pass it forward by "
                                               "its id" % (item.get("text"), twin["id"]), out_of_scope=index))
                continue
            out.append(refusal("retagged", "the out-of-scope item %r %s the %s ledger line %s, which no answered "
                                           "question of this run touched: the doc would hold the line and its twin"
                               % (item.get("text"), how, twin["tag"], twin["id"]), out_of_scope=index))
    for index, item in enumerate(answer.get("open_items") or []):
        twin = next(iter(scopedoc.twins(item, rows)), None)
        if twin is not None:
            out.append(refusal("retagged", "the open item %r repeats the %s ledger line %s: the doc would hold the "
                                           "line and its twin" % (item, twin["tag"], twin["id"]), open_items=index))
    return out


def _research(answer, harvest):
    out = []
    ledger = dict((row["id"], row) for row in harvest.get("ledger") or [])
    for q in answer.get("questions") or []:
        if not q.get("needs_research"):
            continue
        for index, item in enumerate(answer.get("out_of_scope") or []):
            trace = item.get("trace") if isinstance(item.get("trace"), dict) else {}
            if trace.get("kind") == "question" and trace.get("ref") == q.get("id"):
                out.append(refusal("research-resolved", "the out-of-scope item %r is ruled out by question %s, "
                                                        "which is marked needs research: it is parked, never "
                                                        "resolved in the run" % (item.get("text"), q.get("id")),
                                   out_of_scope=index, question=q.get("id")))
        parked = any(line.get("tag") == "parked" and line.get("reason") == "needs research"
                     and isinstance(line.get("trace"), dict) and line["trace"].get("kind") == "question"
                     and line["trace"].get("ref") == q.get("id") for line in answer.get("lines") or [])
        kept = any(ledger.get(ident, {}).get("tag") == "parked" and ledger[ident].get("reason") == "needs research"
                   for ident in q.get("touches") or [])
        if not (parked or kept):
            out.append(refusal("research-not-parked", "question %s is marked needs research but leaves no parked "
                                                      "line: park it as needs research, traced to the question"
                               % q.get("id"), question=q.get("id")))
    return out


def _triage(answer, harvest):
    out = []
    triage = answer.get("triage") or {}
    doc = harvest.get("doc")
    if triage.get("no_scope_doc"):
        why = []
        if triage.get("tier") != "napkin":
            why.append("'no scope doc' is the napkin outcome, and this idea is triaged %s" % triage.get("tier"))
        if any(answer.get(key) for key in ("lines", "out_of_scope", "research", "open_items", "exit_test", "doc")):
            why.append("'no scope doc' carries no line, no item and no exit test: the counts are zero")
        if doc is not None:
            why.append("the idea already has a scope doc (%s); 'no scope doc' cannot unwrite it" % doc["path"])
        if answer.get("sitting") != "ends":
            why.append("'no scope doc' ends the sitting: the answer's sitting is 'ends', not %r"
                       % (answer.get("sitting"),))
        for sentence in why:
            out.append(refusal("napkin-outcome", sentence))
        return out
    parts = scopedoc.classify(answer, harvest.get("ledger") or [], answer.get("run_id"))
    fields = answer.get("doc")
    if doc is None and scopedoc.settles_anything(parts):
        if not isinstance(fields, dict) or _blank(fields.get("title")) or _blank(fields.get("intent")):
            out.append(refusal("doc-fields", "a new scope doc needs its title and its intent (the answer's doc.title "
                                             "and doc.intent)"))
    if doc is not None and fields is not None:
        out.append(refusal("doc-fields", "the scope doc exists (%s): its title and intent are kept as found, so the "
                                         "answer carries no doc fields" % doc["path"]))
    return out


def _exit_test(answer, harvest, requests, run_dir):
    out = []
    et = answer.get("exit_test")
    built = (requests or {}).get("requests") or []
    if et is None:
        if built:
            out.append(refusal("exit-test-rows", "requests were built for %s but the answer records no exit test"
                               % ", ".join(r["row"] for r in built)))
        return out
    rows = et.get("rows") or []
    has_dispositions = et.get("dispositions") is not None or et.get("summary") is not None or \
        et.get("cold_read_doc") is not None
    if rows or built:
        if sorted(rows) != sorted(r["row"] for r in built) or len(set(rows)) != len(rows):
            out.append(refusal("exit-test-rows", "the exit test names %s; this run built requests for %s"
                               % (", ".join(rows) or "no row", ", ".join(r["row"] for r in built) or "no row")))
        for req in built:
            call = exit_test.read_call(run_dir, exit_test.read_request(req["path"]))
            if isinstance(call, str):
                out.append(refusal("exit-test-unrecorded", call, row=req["row"]))
        if has_dispositions:
            out.append(refusal("disposition-before-raw", "the run that writes the readers' raw text carries no "
                                                         "disposition: the raw text lands before any triage, and a "
                                                         "later run records the dispositions"))
        return out
    if not has_dispositions:
        return out
    cold = harvest.get("cold_read") or {}
    candidates = dict((c["path"], c) for c in cold.get("candidates") or [])
    target = et.get("cold_read_doc")
    if target not in candidates:
        out.append(refusal("cold-read-doc", "the dispositions name %r, which is no cold-read doc this run selected "
                                            "(select --hunt cold-read --name <idea>)" % (target,)))
        return out
    sections = set(candidates[target].get("rows") or [])
    if not text.one_line(et.get("summary")):
        out.append(refusal("disposition", "the dispositions carry a one-line summary of what was taken and what was "
                                          "left behind"))
    items = et.get("dispositions") or []
    if not items:
        out.append(refusal("disposition", "a disposition run marks every item it read"))
    for index, item in enumerate(items):
        where = {"disposition": index}
        if item.get("disposition") not in exit_test.DISPOSITIONS:
            out.append(refusal("disposition", "the disposition %r is none of: surfaced, absorbed, left downstream"
                               % (item.get("disposition"),), **where))
        if item.get("disposition") == "left downstream" and _blank(item.get("why")):
            out.append(refusal("disposition", "an item left downstream says why", **where))
        if item.get("row") not in sections:
            out.append(refusal("disposition", "the row %r has no section in %s" % (item.get("row"), target), **where))
        for key in ("item", "why"):
            value = item.get(key)
            if (key == "item" or not _blank(value)) and not text.one_line(value):
                out.append(refusal("disposition", "a disposition's %s is one line of text" % key, **where))
    return out
