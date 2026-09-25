"""record-answer's own content checks, and the view the shared refusals read (contract section 7).

The shared refusals (E14-11) are `station_core/answer.py`'s, called once with `view(answer)` and
`ALLOWED_TRACES`; this module never repeats them. `view` maps every line of the answer to the
shared shape by its own tag: a requirement and a constraint are what the build doc asserts as
settled, so they are `decided` there and a line of either kind that traces to a `parked` or
`open` ledger line is held to the shared `quietly-resolved` rule; an out-of-scope line is tagged
`out-of-scope`, since carrying a parked scope line or a deferred architecture line forward as out
of scope is the pass-forward E14-11 names, not a resolution. A scope `Open:` item is the owner's
call and not a descoping: an out-of-scope line that carries one forward with no answered question
of this run touching it is this core's own refusal, `open-item-descoped`.

The trace kinds this core allows (ruling R1 of round 2, the owner's words as a trace): `ledger`,
`repo_path`, `question` and `owner_words` (the owner's words quoted verbatim, not blank: the schema
refuses a blank quote). `assumed` is refused for these lines: assumptions have their own field.

`own(answer, run_input, harvest)` returns blueprint's own refusals, each `{"rule", "message", ...}`
in the shared shape, one per finding:

    session-mismatch          the answer's session_id is not the input's invocation.session_id
    run-id-mismatch           the answer's run_id is not this run's
    criterion-without-verify  a criterion with no `verify` form, or one that is none of the three forms
    open-item-descoped        an out-of-scope line carrying a scope `Open:` item that no answered
                              question of this run touched
    duplicate-id              two lines, two criteria or two slices sharing an id or a name
    unknown-id                a slice naming a requirement line, a criterion or a slice that is not there
    depends-forward           a slice depending on itself or on a slice after it
    unplaced                  with a build doc: a requirement line or a criterion no slice carries
    no-slice                  needs_build_doc true with no slice
    slices-without-build-doc  needs_build_doc false with slices
    feature-not-hunted        the answer's feature is not the name the build hunt ran with
"""
import re

ALLOWED_TRACES = ("ledger", "repo_path", "question", "owner_words")
RULES = ("session-mismatch", "run-id-mismatch", "criterion-without-verify", "open-item-descoped",
         "duplicate-id", "unknown-id", "depends-forward", "unplaced", "no-slice", "slices-without-build-doc",
         "feature-not-hunted")
# the tag each line of the answer carries in the view the shared refusals read
VIEW_TAGS = {"requirement": "decided", "constraint": "decided", "out-of-scope": "out-of-scope"}
# the build doc template's three verify forms, and what each must hold
VERIFY_FORMS = ("existing test", "new test at <path>", "manual: <steps>")
VERIFY = re.compile(r"^(?:existing test(?:\s+\S.*)?|new test at \S.*|manual: \S.*)$")


def _refusal(rule, message, **where):
    row = {"rule": rule, "message": message}
    row.update(where)
    return row


def view(answer):
    """The answer as the shared refusals read it: its questions, and its lines tagged by `VIEW_TAGS`."""
    lines = []
    for line in answer.get("lines") or []:
        row = {"text": line.get("text"), "tag": VIEW_TAGS.get(line.get("tag"), "decided")}
        if "trace" in line:
            row["trace"] = line["trace"]
        lines.append(row)
    return {"questions": answer.get("questions"), "lines": lines}


def _verify_holds(value):
    """One of the template's three verify forms, on one line."""
    if not isinstance(value, str) or "\n" in value or "\r" in value:
        return False
    return VERIFY.match(value.strip()) is not None


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
    for index, line in enumerate(answer.get("lines") or []):
        trace = line.get("trace") if isinstance(line.get("trace"), dict) else {}
        ref = trace.get("ref")
        if (line.get("tag") == "out-of-scope" and trace.get("kind") == "ledger" and ref in ledger
                and ledger[ref].get("tag") == "open" and ref not in settled):
            refusals.append(_refusal("open-item-descoped", "the out-of-scope line %r carries the scope doc's open "
                                     "item %r (%s) forward as out of scope, and no answered question of this run "
                                     "touched it: an open item is the owner's call, not a descoping; ask him, or "
                                     "keep it an open question" % (line.get("text"), ledger[ref].get("text"), ref),
                                     line=index, text=line.get("text"), line_id=ref))

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
