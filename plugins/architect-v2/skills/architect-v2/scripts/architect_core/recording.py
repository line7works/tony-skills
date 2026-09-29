"""`record-answer`'s content checks (brief 3.4, CR-9): the shared refusals, then architect's own.

`evaluate(answer, ctx)` -> (refusals, plan). The answer has passed its schema already. The shared
refusals of rule E14-11 are `station_core/answer.check`'s, run once on the neutral view of the
answer (`view`): its questions, and every line that records a decision with its trace (the
walkthrough's values one by one, each new or struck poured-concrete and deferred line, each `lines`
entry's own text, each ruling), against the harvested ledger, with the trace kinds this core admits
(`ALLOWED`). The doc's rendering (the `Who: ... Must be able to:` line, the `NEEDS CHECK:` prefix) is
added after the check and is never the answer's words.
Architect's own refusals follow, each `{"rule", "message", ...}`; then the proposed doc is built
and held to the no-loss check against the preservation baseline (`ctx["living_text"]`: the
harvested living doc, or after the first write the first write's snapshot, round 7 R1). `plan`
carries the proposed doc.

Nothing here writes. The executor's judgment is never repaired: a refused answer is refused.
"""
import itertools

from station_core import answer as shared

from . import docs
from .common import ALLOWED_TRACES, blank, display

ALLOWED = ALLOWED_TRACES
SHARED_RULES = ("shape", "re-asked-decided", "unknown-line", "untraced", "quietly-resolved")
OWN_RULES = ("session-mismatch", "run-mismatch", "docless-without-reason", "docless-with-scope-doc",
             "docless-unasked", "docless-home", "docless-reason-mismatch", "exit-ramp-ended-with-candidates", "candidates-fewer-than-two",
             "candidates-more-than-three", "candidate-names-repeat", "candidates-not-distinct",
             "pick-not-a-candidate", "rejected-mismatch", "rejected-without-why", "doors-missing", "razor",
             "review-offer", "review-fields", "review-no-take", "rulings-without-review", "publish-against-input",
             "republish-url", "unknown-prior-line", "amendment-outside-rulings", "no-loss")
RULES = SHARED_RULES + OWN_RULES
AMENDABLE = ("review", "rulings", "changed", "questions", "publish_url")


def refusal(rule, message, **where):
    row = {"rule": rule, "message": message}
    row.update(where)
    return row


def context(harvest, living_text, session_id=None, takes=(), prior=None, run_id=None, requested=(),
            repeat_strike=False):
    """`requested` is the readers rows a `request` of this run built (for `failed_lanes`).
    `living_text` is the preservation baseline: the harvested doc, or after the first write the
    first write's snapshot without the current run's block (round 7 R1), when `repeat_strike` is
    set so a strike the first answer recorded may be repeated."""
    return {"harvest": harvest, "living_text": living_text, "session_id": session_id, "takes": list(takes),
            "prior": prior, "run_id": run_id if run_id is not None else harvest.get("run_id"),
            "requested": list(requested), "repeat_strike": bool(repeat_strike)}


POURED_SPLIT = " %s " % docs.D


def poured_fields(text):
    """(category, decision, why) of a poured-concrete line on its form, `<category> <dash> <decision>
    <dash> <why>` (the decision everything between the first field and the last, so a decision that
    itself holds the dash stays whole), or None when the line has fewer than three fields."""
    parts = text.split(POURED_SPLIT)
    if len(parts) < 3:
        return None
    return parts[0], POURED_SPLIT.join(parts[1:-1]), parts[-1]


def view(answer):
    """The neutral view `station_core/answer.py` reads: the questions, and each asserted line.

    The walkthrough gives one row per value (round 6 R1): `who`, `when` and each `must` item, each its
    own text with its place named (`walkthrough/who`, `walkthrough/must/0`), never the formatted
    walkthrough line; each `lines` entry gives its own text, never the `NEEDS CHECK:` the doc renders
    before it. The formatting is the doc's rendering, added after the check, so an unanswered open
    or parked item asserted as a walkthrough value or a `lines` entry meets the shared text rule.

    Every new entry of the Deferred section, and every `lines` entry (which the doc renders there as `NEEDS CHECK:`), gives a second row under the tag `deferred` when its own tag is not one of `station_core.answer.MOVED_BACK` (slice 3a round 4, C3A2-1): the next station reads the Deferred section as parked, so a decided scope row named there is refused as moved back.

    A new poured-concrete line on its form gives two rows (round 3 R4, CS-1's lane half): the whole
    line, and its DECISION field as the row's text with the `category` and the `why` beside it, so
    the shared text rule meets a parked or open line re-asserted as the decision alone as well as
    the whole line, even where the decision holds the form's dash. Both rows name the same place,
    and `shared_refusals` reports a refusal of that place once.

    Every row an entry or a `lines` entry gives (its own, the Deferred section's second row, the
    poured decision field's) carries the entry's `row` when it names one (slice 3b R7, A5(4)): each
    names the same ledger row, and the frame judges the line by that id, never by its words against
    that row. The neutral filter drops a `row` the entry does not carry.

    Returns (neutral, places): `places[i]` is `(where, unit)` for the i-th line, `unit` the place a
    missing or empty trace is reported against once (the walkthrough carries one trace for its
    values, so an untraced walkthrough is one refusal)."""
    walk = answer["walkthrough"]
    lines = []
    values = [("who", walk["who"]), ("when", walk["when"])]
    values += [("must/%d" % index, text) for index, text in enumerate(walk["must"])]
    for field, text in values:
        lines.append({"text": text, "tag": "decided", "trace": walk.get("trace"),
                      "where": "walkthrough/%s" % field, "unit": "walkthrough"})
    for key in ("poured_concrete", "deferred"):
        for index, entry in enumerate(answer[key]):
            if "carried" in entry:
                continue
            if "strike" in entry:
                lines.append({"text": entry["strike"], "tag": "struck", "trace": entry.get("trace"),
                              "where": "%s/%d (struck)" % (key, index)})
                continue
            where = "%s/%d" % (key, index)
            lines.append({"text": entry["text"], "tag": entry["tag"], "trace": entry.get("trace"),
                          "row": entry.get("row"), "where": where})
            if key == "deferred" and entry["tag"] not in shared.MOVED_BACK:
                # the Deferred section is read as parked by the next station: every entry of it is a move
                lines.append({"text": entry["text"], "tag": "deferred", "trace": entry.get("trace"),
                              "row": entry.get("row"), "where": where})
            fields = poured_fields(entry["text"]) if key == "poured_concrete" else None
            if fields:
                lines.append({"text": fields[1], "category": fields[0], "why": fields[2], "tag": entry["tag"],
                              "trace": entry.get("trace"), "row": entry.get("row"), "where": where})
    for index, line in enumerate(answer["lines"]):
        lines.append({"text": line["text"], "tag": line["tag"], "trace": line.get("trace"), "row": line.get("row"),
                      "where": "lines/%d" % index})
        if line["tag"] not in shared.MOVED_BACK:
            # a NEEDS CHECK line renders into the Deferred section (docs.section_items), read as parked downstream
            lines.append({"text": line["text"], "tag": "deferred", "trace": line.get("trace"), "row": line.get("row"),
                          "where": "lines/%d" % index})
    for index, ruling in enumerate(answer["rulings"]):
        lines.append({"text": "%s: %s" % (ruling["disagreement"], ruling["ruling"]), "tag": "ruling",
                      "trace": ruling.get("trace"), "where": "rulings/%d" % index})
    neutral = [dict((k, v) for k, v in row.items() if k not in ("where", "unit") and v is not None) for row in lines]
    return {"questions": [{"id": q["id"], "text": q["text"], "touches": q["touches"], "answer": q["answer"]}
                          for q in answer["questions"]],
            "lines": neutral}, [(row["where"], row.get("unit", row["where"])) for row in lines]


def shared_refusals(answer, ctx):
    neutral, places = view(answer)
    result = shared.check(neutral, ctx["harvest"]["ledger"], workspace=ctx["harvest"]["workspace"], allowed=ALLOWED)
    out = []
    seen = set()
    for row in result["refusals"]:
        row = dict(row)
        if "line" in row and isinstance(row["line"], int) and row["line"] < len(places):
            where, unit = places[row["line"]]
            # an untraced walkthrough is one refusal (its values share one trace); every other rule names
            # the value it met, and the decision row of a poured line is folded into its whole line
            row["field"] = unit if row["rule"] == "untraced" else where
            if (row["rule"], row["field"]) in seen:
                continue
            seen.add((row["rule"], row["field"]))
        out.append(row)
    return out


def _norm(text):
    return " ".join(text.split()).casefold()


def collapsed(text):
    """The text with its runs of whitespace collapsed to one space and its ends trimmed, case kept: how the
    docless reason is compared with the input's and how it lands in the doc's `Docless:` header (R2, CA3-3)."""
    return " ".join(text.split())


def visible(text):
    """True when the text holds a character the frame's invisible rule keeps that is not whitespace (R2, CA3-2)."""
    return isinstance(text, str) and bool(shared._visible(text).strip())


def categories(candidate):
    """{category: {choices}}, each name and choice casefolded and whitespace-normalized (R4), so a
    re-cased or re-spaced pair is the same pair."""
    out = {}
    for item in candidate["categories"]:
        name, choice = item.split(":", 1)
        out.setdefault(_norm(name), set()).add(_norm(choice))
    return out


def differ(a, b):
    """The one-way-door categories both candidates name in which they share no choice. A category
    only one of them names is no difference, and neither is a second choice padded into a category
    both name while they share the first: padding a candidate distinguishes nothing (R4; round 3
    CA2-4)."""
    ca, cb = categories(a), categories(b)
    return sorted(name for name in set(ca) & set(cb) if not (ca[name] & cb[name]))


def candidate_refusals(answer):
    """The exit ramp, the candidates, the pick and the rejected list (v1's Steps 2 and 3.2)."""
    out = []
    continued = answer["exit_ramp"]["continued"]
    cands = answer["candidates"]
    names = [c["name"] for c in cands]
    if not continued:
        if cands or answer["pick"] is not None or answer["rejected"]:
            out.append(refusal("exit-ramp-ended-with-candidates", "the exit ramp ended the interview (no system), so "
                               "the answer carries no candidates, no pick and no rejected list"))
        return out
    if len(cands) < 2:
        out.append(refusal("candidates-fewer-than-two", "the interview continued with %d candidate(s); at least two "
                           "genuinely distinct candidates go on the table before a pick" % len(cands)))
    if len(cands) > 3:
        out.append(refusal("candidates-more-than-three", "%d candidates; the table holds two or three" % len(cands)))
    if len(set(names)) != len(names):
        out.append(refusal("candidate-names-repeat", "two candidates share a name"))
    for a, b in itertools.combinations(cands, 2):
        if not differ(a, b):
            out.append(refusal("candidates-not-distinct", "the candidates %r and %r differ in no one-way-door "
                               "category (%s)" % (a["name"], b["name"], ", ".join(sorted(set(a["categories"])))),
                               candidates=[a["name"], b["name"]]))
    picked = answer["pick"] is not None and answer["pick"] in names
    if not picked:
        out.append(refusal("pick-not-a-candidate", "the pick %r is not the name of a candidate on the table"
                           % (answer["pick"],)))
    expected = sorted(n for n in names if n != answer["pick"])
    got = sorted(r["name"] for r in answer["rejected"])
    if picked and got != expected:
        out.append(refusal("rejected-mismatch", "the rejected list names %s; every candidate not picked is rejected "
                           "once, with its why (%s)" % (got or "nothing", expected or "none")))
    for r in answer["rejected"]:
        if blank(r["why"]):
            out.append(refusal("rejected-without-why", "the rejected candidate %r carries no why" % r["name"],
                               candidate=r["name"]))
    return out


def doors_refusals(answer):
    """A continued interview records its one-way-door check (v1's Step 3.3)."""
    if answer["exit_ramp"]["continued"] and not answer.get("doors"):
        return [refusal("doors-missing", "the interview continued, so the one-way-door check records what it "
                        "settled (`doors.settled`)")]
    return []


def razor_refusals(answer):
    """Every v0 component names the walkthrough requirement it serves (the razor)."""
    must = set(item.strip() for item in answer["walkthrough"]["must"])
    out = []
    for c in answer["components"]:
        if blank(c["serves"]):
            out.append(refusal("razor", "the component %r serves nothing; every v0 component points at a walkthrough "
                               "requirement or it is cut" % c["name"], component=c["name"]))
        elif c["serves"].strip() not in must:
            out.append(refusal("razor", "the component %r serves %r, which is no walkthrough requirement (%s)"
                               % (c["name"], c["serves"], "; ".join(answer["walkthrough"]["must"])),
                               component=c["name"]))
    return out


def gate_refusals(answer, ctx):
    """The input gate and the docless reason, the review offer and its record, the publish."""
    harvest = ctx["harvest"]
    out = []
    review = answer["review"]
    if harvest["docless"]:
        docless = answer.get("docless")
        unstated = not docless or not visible(docless.get("reason"))
        if unstated:
            out.append(refusal("docless-without-reason", "no scope doc was found, so the answer records the reason "
                               "the gate discussion landed on (`docless.reason`, holding a visible character: "
                               "whitespace, format and zero-width characters alone record nothing); it lands in "
                               "the doc's header"))
        elif docless["home"] == "staging" and not harvest.get("staging"):
            out.append(refusal("docless-home", "the docless doc's home is the staging home, and the input names none"))
        stated = harvest.get("docless_reason")
        if not unstated and stated and collapsed(docless["reason"]) != collapsed(stated):
            out.append(refusal("docless-reason-mismatch", "the input opened the docless gate with the reason %r "
                               "(`station.docless_reason`); the answer's `docless.reason` is that reason byte for "
                               "byte once runs of whitespace are collapsed, case kept, the one the doc's Docless: "
                               "header carries (%r)" % (stated, docless["reason"])))
        asked = [q for q in answer["questions"] if q.get("about") == "scope-doc" and not blank(q["answer"])]
        if not asked:
            out.append(refusal("docless-unasked", "the hunt found no scope doc; the owner is asked once whether one "
                               "exists where the glob cannot see (a question `about: scope-doc`, answered) before "
                               "the docless gate opens"))
        if review["outcome"] != "not-offered":
            out.append(refusal("review-offer", "a docless run makes no blind-review offer (there is no brief to "
                               "send); its review is `not-offered`"))
    else:
        if "docless" in answer:
            out.append(refusal("docless-with-scope-doc", "this run has a scope doc (%s); a docless block is for a run "
                               "without one" % harvest["scope_doc"]["display"]))
        if review["outcome"] == "not-offered":
            out.append(refusal("review-offer", "a run with a scope doc makes the blind-review offer; its outcome is "
                               "pending, declined, failed or done"))
    need = {"declined": ("date",), "failed": ("date", "reason"), "done": ("spine",)}.get(review["outcome"], ())
    missing = [f for f in need if f not in review]
    if missing:
        out.append(refusal("review-fields", "a %s review records its %s" % (review["outcome"], " and ".join(missing))))
    if "failed_lanes" in review and review["outcome"] != "done":
        out.append(refusal("review-fields", "`failed_lanes` names the lanes that did not return beside a done review; "
                           "a %s review carries none (a review whose every lane failed is `failed`)" % review["outcome"]))
    elif "failed_lanes" in review:
        # round 3 CA2-5: each failed lane is a row a request of this run built, with no saved take, once
        rows = [f["row"] for f in review["failed_lanes"]]
        saved = set(t["row"] for t in ctx["takes"])
        requested = ctx.get("requested") or []
        bad = [r for r in rows if r not in requested or r in saved]
        repeated = sorted(set(r for r in rows if rows.count(r) > 1))
        if bad or repeated:
            out.append(refusal("review-fields", "`failed_lanes` names %s: each failed lane is a row a `request` of "
                               "this run built (%s), with no saved take (%s), named once"
                               % (", ".join(bad + repeated), ", ".join(requested) or "none",
                                  ", ".join(sorted(saved)) or "none")))
    if review["outcome"] == "done" and not ctx["takes"]:
        out.append(refusal("review-no-take", "the review is `done`, and no take was saved in this run (`save-take`); "
                           "a review counts as done when at least one take was saved"))
    if answer["rulings"] and review["outcome"] != "done":
        out.append(refusal("rulings-without-review", "rulings come from the comparison with the saved takes; this "
                           "run's review is %s" % review["outcome"]))
    if answer["publish"] and not harvest.get("input_publish", True):
        out.append(refusal("publish-against-input", "the input says `station.publish: false`; the answer cannot "
                           "publish"))
    recorded = (harvest.get("living_doc") or {}).get("artifact_url")
    if answer["publish"] and recorded and answer["publish_url"] != recorded:
        out.append(refusal("republish-url", "the living doc records the artifact %s; a re-run republishes to that "
                           "URL (`publish_url`), never to a second artifact" % recorded))
    elif answer["publish"] and not recorded and answer["publish_url"] is not None:
        out.append(refusal("republish-url", "the living doc records no artifact yet, so this is a first publish "
                           "and `publish_url` is null"))
    elif not answer["publish"] and answer["publish_url"] is not None:
        out.append(refusal("republish-url", "a run that does not publish names no `publish_url`"))
    return out


def amendment_refusals(answer, prior):
    """After a write, an amended answer changes only the review, the rulings, `changed`, the
    questions (appended to) and `publish_url`, plus the fields a ruling names in `changes`."""
    allowed = set(AMENDABLE)
    for ruling in answer["rulings"]:
        allowed.update(ruling["changes"])
    out = []
    for key in sorted(set(answer) | set(prior)):
        if key in allowed or answer.get(key) == prior.get(key):
            continue
        out.append(refusal("amendment-outside-rulings", "the amended answer changes %r, which no ruling names in "
                           "its `changes`; the doc changes only where a ruling says so" % key, field=key))
    if prior["questions"] != answer["questions"][:len(prior["questions"])]:
        out.append(refusal("amendment-outside-rulings", "the amended answer rewrites a question the first answer "
                           "recorded; questions are only added", field="questions"))
    return out


def target_path(answer, harvest):
    if harvest["target"]["path"]:
        return harvest["target"]["path"]
    from .harvesting import new_doc_path
    docless = answer.get("docless") or {}
    home = docless.get("home") or "staging"
    if home == "staging" and not harvest.get("staging"):
        return None
    return new_doc_path(home, harvest["workspace"], harvest.get("staging"), harvest["today"], harvest["slug"])


def _header_reason(answer):
    reason = (answer.get("docless") or {}).get("reason")
    return collapsed(reason) if isinstance(reason, str) else reason


def build_values(answer, harvest, living_text, takes, artifact):
    living = harvest.get("living_doc")
    return {"n": living["next_run"] if living else 1, "date": harvest["today"], "ledger": harvest["ledger"],
            "takes": takes, "workspace": harvest["workspace"],
            "scope_display": harvest["scope_doc"]["display"] if harvest["scope_doc"] else None,
            "docless_reason": _header_reason(answer) if harvest["docless"] else None,
            "artifact": artifact, "living_text": living_text}


def plan(answer, harvest, living_text, takes, artifact):
    """The proposed doc and what the result says about it."""
    text = docs.build(answer, build_values(answer, harvest, living_text, takes, artifact))
    living = harvest.get("living_doc")
    return {"doc_text": text, "doc_path": target_path(answer, harvest), "run": living["next_run"] if living else 1,
            "passed_forward": [row["id"] for row in docs.passed_forward(harvest["ledger"], answer)],
            "losses": docs.losses(living_text, text) if living_text is not None else []}


def evaluate(answer, ctx):
    harvest = ctx["harvest"]
    refusals = []
    if ctx.get("run_id") is not None and answer["run_id"] != ctx["run_id"]:
        refusals.append(refusal("run-mismatch", "the answer names run %r; this run is %r" % (answer["run_id"], ctx["run_id"])))
    if answer["session_id"] != ctx.get("session_id"):
        refusals.append(refusal("session-mismatch", "the answer's session %r is not the input's invocation session %r "
                                "(the adapter's answer_fields.session_id, typed by no one)"
                                % (answer["session_id"], ctx.get("session_id"))))
    refusals += shared_refusals(answer, ctx)
    refusals += gate_refusals(answer, ctx)
    refusals += candidate_refusals(answer)
    refusals += doors_refusals(answer)
    refusals += razor_refusals(answer)
    prior_lines = docs.prior_line_refusals(answer, ctx["living_text"], repeat_strike=ctx.get("repeat_strike"))
    refusals += [refusal(rule, message) for rule, message in prior_lines]
    if ctx.get("prior") is not None:
        refusals += amendment_refusals(answer, ctx["prior"])
    result = None
    blocking = ("docless-home", "docless-without-reason", "review-fields", "unknown-prior-line")
    buildable = not any(r["rule"] in blocking for r in refusals)
    if buildable:
        artifact = (harvest.get("living_doc") or {}).get("artifact_url")
        result = plan(answer, harvest, ctx["living_text"], ctx["takes"], artifact)
        for message in result["losses"]:
            refusals.append(refusal("no-loss", "refused before any write: %s" % message))
    return refusals, result


__all__ = ["RULES", "context", "evaluate", "plan", "view", "display"]
