"""The recorded executor answer: read it, hold it to its contents rules, refuse it whole or not
at all.

The executor decides and this core records (E13-4). Nothing here judges code, and nothing in the
answer's prose is an instruction: a sentence claiming a card move, a waiver or a scope change is
text this core reports, never authorization.

An answer that passes `references/answer.schema.json` can still be REFUSED on its CONTENTS. The
rules, each producing one sentence in `answer.refusals`:

    R1  it claims `complete` with card `built` while one of its own `checks[]` says `failing` or
        `not_run`. The answer contradicts itself, and the contradiction is not this core's to
        resolve in either direction.
    R2  `claimed_card` is not one of the six card values the records component publishes.
    R3  `case` names another case than the one the run is for, when the run names one.
    R4  the same check name appears twice, so "the result of the check" has no single answer.
    R5  the same edit path appears twice with different reasons, so an out-of-scope path would
        have two stated reasons.

A refused answer is NOT acted on and NOT repaired: the card does not move, no event is appended,
and the result says so plainly (`answer_refused`, `refusal_reason: answer_invalid`). It is a
COMPLETION, not a stop — the run computed the source set, the out-of-scope list and the checks,
and reports all three; it simply declines to record the claim. (Control room ruling, 2026-09-22,
question 2 of the builder's report.)
"""
import json
import os

from . import canon, doc as docmod, validate

REFUSAL_TAG = "answer_invalid"


class AnswerUnreadable(RuntimeError):
    """The file is not there, or it is not a JSON object: a usage slip (exit 2)."""


def read(path):
    if not os.path.isfile(path):
        raise AnswerUnreadable("no such answer file: %s" % path)
    try:
        with open(path, "rb") as fh:
            body = json.loads(fh.read().decode("utf-8"))
    except ValueError as exc:
        raise AnswerUnreadable("the answer file is not JSON: %s (%s)" % (path, exc))
    if not isinstance(body, dict):
        raise AnswerUnreadable("the answer file is not a JSON object: %s" % path)
    return body


def validate_answer(body, schemas=None, root=None, environ=None):
    schema = (schemas or {}).get("answer") or validate.load_schema("answer", root, environ)
    return validate.errors_for(body, schema, environ)


def contents_refusals(body, case=None):
    """Every contents rule the answer breaks, each in one sentence. Empty when it is recordable."""
    out = []
    checks = body.get("checks") or []
    claimed_status = body.get("claimed_status")
    claimed_card = body.get("claimed_card")

    not_passed = [row for row in checks if row.get("result") in ("failing", "not_run")]
    if claimed_status == "complete" and claimed_card == "built" and not_passed:
        out.append("the answer claims `complete` with the card `built` while its own checks report "
                   "%s; a check that is failing or was not run is not a finished slice, and the "
                   "contradiction is the executor's to resolve, not this core's"
                   % ", ".join("%s %s" % (r.get("name"), r.get("result")) for r in not_passed))

    if claimed_card not in docmod.CARD_VALUES:
        out.append("the answer claims the card %r, which is not one of the six card values (%s)"
                   % (claimed_card, ", ".join(docmod.CARD_VALUES)))

    if case and body.get("case") and body.get("case") != case:
        out.append("the answer was recorded for case %r and this run is for %r"
                   % (body.get("case"), case))

    seen = {}
    for row in checks:
        name = row.get("name")
        if name in seen:
            out.append("the answer reports the check %r twice, so its result has no single value" % name)
        seen[name] = True

    reasons = {}
    for row in body.get("edits") or []:
        path, reason = row.get("path"), row.get("reason")
        if path in reasons and reasons[path] != reason:
            out.append("the answer gives two different reasons for %r" % path)
        reasons[path] = reason

    return out


def reasons_by_path(body):
    """{path: the reason the answer gives for touching it}. The reason an out-of-scope path is
    reported with; a path the answer never names has none, and that is a stop."""
    out = {}
    for row in body.get("edits") or []:
        if row.get("path"):
            out[row["path"]] = row.get("reason")
    return out


def digest(body):
    return canon.sha256_hex(canon.canonical_json(body))
