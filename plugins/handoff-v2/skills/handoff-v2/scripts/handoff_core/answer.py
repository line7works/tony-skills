"""`record-answer` (contract section 3.4; CR-11, CR-12): the owner's answers held to the record.

The answer file (`references/answer.schema.json`, kind `answers`) carries one entry per gate question (`answered`
true with the owner's `words` and its `effect`, or false), the perishables, and, optionally, what the executor
believes of the photograph (`asserts`). In this order:

1. Refused, exit 5, nothing written (the run stays at `asking`, so a corrected file can be offered): an asserted
   card, open item, branch, commits-ahead count or tree state that the script's read contradicts (the record over
   the recollection); an answer to a question the gate never asked, or two to one; a waiver of a finding the log
   does not hold `open` or `fixed`, a reopening of one it does not hold `waived` or `fixed`, two grants on one
   finding, or a grant on a record question; a next-slice answer naming no slice of the doc that can start (the
   slice must be the doc's and stand `not started` or `in progress`, a candidate of the record or not: the slice 1b
   check's C1B1-5, since a chain the record cannot read leaves the owner's word the only way to name it); words, a
   perishable or a
   question that cannot land in the doc (`gate.text_problem`); and a set of answers whose grants leave the next move
   unresolved with no answer to `r-next` (the answer file then carries the owner's answer to that question, which
   the refusal names).
2. Any question unanswered, some or all: the run ends `gate-open` (exit 10) with nothing written anywhere (the doc,
   the log, the pointer), the result carrying v1's gate-open form. A partial set of answers never buys a partial
   handoff.
3. Otherwise `answers.json` is written in the run directory: each answer with its question, the grants a waiver or
   a reopening becomes (the event is written by `write`, after the gate has resolved), and the summary of where
   each answer lands. Nothing is written outside the run directory here.
"""
from station_core import validate

from . import common, forms, gate as gatemod, nextmove, report

GRANTS = {"waive": ("open", "fixed"), "reopen": ("waived", "fixed")}


def _assertions(asserts, photo):
    out = []
    if not asserts:
        return out
    cards = dict((c["name"], c["card"]) for c in photo["cards"])
    for name, card in sorted((asserts.get("cards") or {}).items()):
        if name not in cards:
            out.append({"rule": "asserted-card", "why": "the answer asserts a card for slice %s, which the build doc "
                                                        "does not hold" % name})
        elif cards[name] != card:
            out.append({"rule": "asserted-card", "why": "the answer asserts slice %s is %r; the records and the doc "
                                                        "say %r" % (name, card, cards[name])})
    held = set()
    for f in photo["open"]:
        held.update([f["id"], f["location"]])
    for item in asserts.get("open") or []:
        if item not in held:
            out.append({"rule": "asserted-open", "why": "the answer asserts %r is open; the records hold no open finding "
                                                        "there" % item})
    repo = photo["repo"]
    for key, label in (("branch", "the branch"), ("ahead", "the commits ahead of %s" % (repo.get("base") or "main")),
                       ("tree", "the tree")):
        if key in asserts and asserts[key] != repo.get(key):
            out.append({"rule": "asserted-%s" % key, "why": "the answer asserts %s is %r; git says %r"
                                                            % (label, asserts[key], repo.get(key))})
    return out


def post_grant_open(photo, grants):
    """The open set after the grants: waived findings leave it, reopened ones join it (with their severity)."""
    by_id = dict((f["id"], f) for f in photo["findings"])
    gone = set(g["finding"] for g in grants if g["kind"] == "waived")
    back = [by_id[g["finding"]] for g in grants if g["kind"] == "reopened"]
    out = [f for f in photo["open"] if f["id"] not in gone]
    out += [dict(f, status="open") for f in back if f["id"] not in set(o["id"] for o in out)]
    return out


def next_slice_problem(name, photo, view):
    """Why the owner's answer naming slice `name` as next cannot be taken, or None: the doc must hold the slice and
    its card stand `not started` or `in progress` (C1B1-5: whether or not the record found it a candidate)."""
    rows = dict((r["name"], r) for r in gatemod.rows_of(photo, view))
    if name not in rows:
        return ("the answer names slice %r, which the build doc does not hold (it holds %s)"
                % (name, ", ".join(rows) or "none"))
    if rows[name]["card"] not in nextmove.STARTABLE:
        return ("the answer names slice %r, which stands %s: the next slice is one of the doc that can start (%s)"
                % (name, rows[name]["card"], " or ".join(nextmove.STARTABLE)))
    return None


def resolve_after(photo, view, grants, owner):
    rows = gatemod.rows_of(photo, view, post_grant_open(photo, grants))
    return rows, nextmove.resolve(rows, view["doc"], finished=photo["finished"], owner=owner)


def handler(ctx, args):
    """`record-answer --run-dir D --answer FILE`."""
    run = common.open_run(ctx, args.run_dir, ("asking",), "record-answer")
    given = common.load_json_file(args.answer, "answer")
    errors = validate.errors_for(given, common.schema("answer.schema.json", ctx), ctx.prefix)
    if not errors and given.get("kind") != "answers":
        errors = [{"path": "/kind", "message": "record-answer takes the answers file (kind answers)"}]
    if errors:
        return ctx.emit(ctx.envelope(ok=False, error="invalid", reason="the answer file does not validate; nothing "
                                     "was written", errors=errors), 4)
    gate = common.read(run, "gate.json")
    photo = common.read(run, "photograph.json")
    view = common.read(run, "doc.json")
    questions = dict((q["id"], q) for q in gate["questions"])
    findings = dict((f["id"], f) for f in photo["findings"])
    refusals = []
    if given["run_id"] != run.checkpoint["run_id"]:
        refusals.append({"rule": "run-id", "why": "the answer names run %r, not this run %r"
                         % (given["run_id"], run.checkpoint["run_id"])})
    refusals += _assertions(given.get("asserts"), photo)
    seen, granted, grants, owner, late_next = set(), set(), [], None, None
    for entry in given["answers"]:
        qid = entry["question"]
        if qid in seen:
            refusals.append({"rule": "answered-twice", "why": "question %s is answered twice" % qid})
            continue
        seen.add(qid)
        if qid not in questions and qid != "r-next":
            refusals.append({"rule": "unknown-question", "why": "the gate asked no question %s" % qid})
            continue
        if not entry["answered"]:
            continue
        problem = gatemod.text_problem(entry["words"])
        if problem:
            refusals.append({"rule": "words", "why": "the answer to %s cannot land in the doc: %s" % (qid, problem)})
        effect = entry["effect"]
        question = questions.get(qid, {"id": "r-next", "source": "next-slice", "candidates": None})
        if (question["source"] == "next-slice") != (effect["kind"] == "next-slice"):
            refusals.append({"rule": "effect", "why": "question %s takes %s, not a %s answer"
                             % (qid, "the next slice" if question["source"] == "next-slice" else "a note, a waiver or a "
                                "reopening", effect["kind"])})
            continue
        if effect["kind"] == "next-slice":
            if qid not in questions:
                late_next = entry
            elif effect["slice"] is not None and next_slice_problem(effect["slice"], photo, view):
                refusals.append({"rule": "next-slice", "why": next_slice_problem(effect["slice"], photo, view)})
            owner = {"slice": effect["slice"], "words": entry["words"]}
            continue
        if effect["kind"] in GRANTS:
            if question["source"] not in gatemod.SESSION_SOURCES:
                refusals.append({"rule": "effect", "why": "a waiver or a reopening answers a session question or a "
                                                          "chat ruling, not the record's question %s" % qid})
                continue
            found = findings.get(effect["finding"])
            if found is None or found["status"] not in GRANTS[effect["kind"]]:
                refusals.append({"rule": effect["kind"], "why": "the answer to %s %ss %s, which the records hold %s; a "
                                 "%s takes a finding that stands %s" % (
                                     qid, effect["kind"], effect["finding"],
                                     "nowhere" if found is None else "as %s" % found["status"], effect["kind"],
                                     " or ".join(GRANTS[effect["kind"]]))})
                continue
            if effect["finding"] in granted:
                refusals.append({"rule": effect["kind"], "why": "two grants name %s" % effect["finding"]})
                continue
            granted.add(effect["finding"])
            grants.append({"kind": "waived" if effect["kind"] == "waive" else "reopened", "finding": found["id"],
                           "severity": found["severity"], "location": found["location"], "claim": found["claim"],
                           "slice": found["slice"], "words": entry["words"], "question": qid})
    for index, item in enumerate(given.get("perishables") or []):
        problem = gatemod.text_problem(item)
        if problem:
            refusals.append({"rule": "perishable", "why": "perishable %d cannot land in the block: %s" % (index + 1,
                                                                                                      problem)})
    unanswered = [q for qid, q in questions.items()
                  if not any(e["question"] == qid and e["answered"] for e in given["answers"])]
    if not refusals and not unanswered:
        rows, move = resolve_after(photo, view, grants, None)
        if move["shape"] == "unresolved" and owner is None:
            refusals.append({"rule": "next-slice-needed", "why": "after this run's grants the record gives %s as the "
                             "next slice, not exactly one: put the next-slice question to the owner and add his answer "
                             "as question r-next (effect next-slice, a candidate or null)"
                             % (", ".join(move["candidates"]) or "no candidate")})
        elif late_next is not None and move["shape"] != "unresolved":
            refusals.append({"rule": "unknown-question", "why": "the gate asked no question r-next, and the record "
                                                               "resolves the next move without one"})
        elif late_next is not None and owner["slice"] is not None and \
                next_slice_problem(owner["slice"], photo, view):
            refusals.append({"rule": "next-slice", "why": next_slice_problem(owner["slice"], photo, view)})
    if refusals:
        return ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"],
                                     reason="; ".join(r["why"] for r in refusals) + "; nothing was written and the run "
                                            "stays where it was", refusals=refusals), 5)
    if unanswered:
        chat = forms.render_gate_open({"feature": view["feature"], "doc": view["doc"],
                                       "unanswered": [q["text"] for q in gate["questions"] if q in unanswered]})
        report.finish(ctx, run, "stopped", "gate-open",
                      "%d of %d question(s) unanswered: the run ends with nothing written (the doc, the log and the "
                      "pointer are as found); answer them and run handoff again, or clear and accept the loss"
                      % (len(unanswered), len(questions)), extra={"chat": chat})
    answered = []
    for entry in given["answers"]:
        if not entry["answered"]:
            continue
        question = questions.get(entry["question"]) or {"id": "r-next", "source": "next-slice",
                                                        "text": "Which slice is next?"}
        landed = "ledger line" if entry["effect"]["kind"] in GRANTS else "block"
        answered.append({"question": question["id"], "source": question["source"], "text": question["text"],
                         "words": entry["words"], "effect": entry["effect"], "landed": landed})
    summary = {"asked": len(questions) + (1 if late_next else 0), "answered": len(answered),
               "in_block": len([a for a in answered if a["landed"] == "block"]),
               "as_ledger_lines": len([a for a in answered if a["landed"] == "ledger line"])}
    record = {"answers": answered, "grants": grants, "perishables": list(given.get("perishables") or []),
              "asserts": given.get("asserts"), "owner_next": owner, "summary": summary}
    common.write(run, "answers.json", record)
    common.advance(run, "answered")
    return ctx.emit(ctx.envelope(next="write", run_id=run.checkpoint["run_id"], answered=len(answered),
                                 grants=[{"kind": g["kind"], "finding": g["finding"]} for g in grants],
                                 summary=summary))
