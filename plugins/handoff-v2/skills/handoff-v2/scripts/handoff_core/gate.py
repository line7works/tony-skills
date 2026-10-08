"""`gate` (contract section 3.3; CR-12): the question gate, the one pause, before ANY write.

The executor supplies the session's questions (v1's sources 1 and 2: unanswered `Questions:` lines of this session's
station outputs, and rulings the owner gave in chat that never became dated ledger lines) in a questions file
(`references/answer.schema.json`, kind `questions`); they take the ids `q1`, `q2`, ... in order. The script adds the
record's own (v1's sources 3 and 4): `r-next`, when the cards and the `Depends on:` chains do not yield exactly one
next slice, carrying the candidates; and `r-q1`, `r-q2`, ..., one per `Questions:` line the doc records in the section
of the slice about to be built (the one next slice, or each candidate when the question is open). Both are read on the
PROSPECTIVE cards (`prospective`): the photograph's cards with every open card taken as cleared, since an open card's
kickoff is the fix list and the slice about to be built is the one after it, and since a grant this run records may
clear it. So the gate asks, in its one batch, every record question the run's answers could make matter. Nothing is
answered here and nothing is written outside the run directory: `gate.json`, and the answer `record-answer` takes
next.
"""
from station_core import validate

from . import common, fences, forms, nextmove

SESSION_SOURCES = ("session-question", "chat-ruling")


def text_problem(text):
    """Why a text cannot land in the build doc as a block field or a ledger line's words, or None: one non-blank
    line, without the line form's separator, every character on vertical-v2's character list (so the doc stays
    readable by the line rules after the write)."""
    if not isinstance(text, str) or not text.strip() or "\n" in text or "\r" in text:
        return "it is not one non-blank line"
    if forms.SEP in text:
        return "it holds the line form's separator ' %s '" % forms.M
    odd = fences.unlisted(text)
    if odd is not None:
        return "%s is outside the character list the build doc keeps" % fences.character(odd[1])
    return None


def rows_of(photo, view, open_findings=None):
    """The slices as `nextmove` reads them: the card after `open_findings` (default: the photograph's open set),
    the `Depends on:` chain as names, the slice's open findings."""
    opened = photo["open"] if open_findings is None else open_findings
    names = [s["name"] for s in view["slices"]]
    cards = dict((c["name"], c) for c in photo["cards"])
    named = set(f["slice"] for f in photo["findings"])
    out = []
    for item in view["slices"]:
        mine = [f for f in opened if f["slice"] == item["name"]]
        card = cards[item["name"]]
        # the records decide a verdict card only where the log names the slice; a Status: line the log never saw
        # is the card as written (contract section 7)
        derive = card["source"] == "records" or item["name"] in named
        out.append({"name": item["name"], "card": nextmove.effective(card["card"], mine) if derive else card["card"],
                    "observed": card["card"], "depends": nextmove.parse_depends(item["depends"], names),
                    "open": mine})
    return out


def prospective(rows):
    """The rows with every open card taken as cleared: a `rejected` or `signed off with conditions` card reads
    `signed off`, and no BLOCKER or MAJOR stays open (contract section 3.3)."""
    out = []
    for row in rows:
        card = nextmove.SIGNED_OFF if row["card"] in nextmove.OPEN_CARDS else row["card"]
        out.append(dict(row, card=card, open=[f for f in row["open"] if f["severity"] not in nextmove.GATING]))
    return out


def record_questions(photo, view):
    rows = prospective(rows_of(photo, view))
    finished = photo["finished"]
    found = nextmove.ambiguous(rows, finished)
    out = []
    targets = []
    if found is not None:
        why = []
        if found["unreadable"]:
            why.append("the Depends on: chain of %s names no slice of the doc" % ", ".join(found["unreadable"]))
        text = ("Which slice is next? The cards and the Depends on: chains give %s%s"
                % ("the candidates %s" % ", ".join(found["names"]) if found["names"] else "no candidate",
                   "; %s" % "; ".join(why) if why else ""))
        out.append({"id": "r-next", "source": "next-slice", "text": text, "candidates": found["names"]})
        targets = found["names"]
    else:
        move = nextmove.resolve(rows, view["doc"], finished=finished)
        if move["shape"] == "clean-boundary":
            targets = [move["slice"]]
    count = 0
    for item in view["slices"]:
        if item["name"] not in targets:
            continue
        for question in item["questions"]:
            if question["text"].casefold() in ("", "none", "nothing"):
                continue
            count += 1
            out.append({"id": "r-q%d" % count, "source": "doc-question", "slice": item["name"],
                        "text": question["text"], "line": question["line"]})
    return out


def handler(ctx, args):
    """`gate --run-dir D --questions FILE`."""
    run = common.open_run(ctx, args.run_dir, ("photographed",), "gate")
    given = common.load_json_file(args.questions, "questions")
    errors = validate.errors_for(given, common.schema("answer.schema.json", ctx), ctx.prefix)
    if not errors and given.get("kind") != "questions":
        errors = [{"path": "/kind", "message": "the gate takes the questions file (kind questions)"}]
    if errors:
        return ctx.emit(ctx.envelope(ok=False, error="invalid", reason="the questions file does not validate; nothing "
                                     "was written", errors=errors), 4)
    refusals = []
    if given["run_id"] != run.checkpoint["run_id"]:
        refusals.append({"rule": "run-id", "why": "the questions file names run %r, not this run %r"
                         % (given["run_id"], run.checkpoint["run_id"])})
    for index, question in enumerate(given["questions"]):
        problem = text_problem(question["text"])
        if problem:
            refusals.append({"rule": "question-text", "why": "question %d cannot land in the block: %s"
                             % (index + 1, problem)})
    if refusals:
        return ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"],
                                     reason="; ".join(r["why"] for r in refusals) + "; nothing was written",
                                     refusals=refusals), 5)
    photo = common.read(run, "photograph.json")
    view = common.read(run, "doc.json")
    questions = [{"id": "q%d" % (index + 1), "source": q["source"], "text": q["text"]}
                 for index, q in enumerate(given["questions"])]
    questions += record_questions(photo, view)
    gate = {"questions": questions, "open": photo["open"], "findings": photo["findings"]}
    common.write(run, "gate.json", gate)
    common.advance(run, "asking")
    return ctx.emit(ctx.envelope(next="record-answer", run_id=run.checkpoint["run_id"], questions=questions,
                                 open=photo["open"], findings=photo["findings"], cards=photo["cards"]))
