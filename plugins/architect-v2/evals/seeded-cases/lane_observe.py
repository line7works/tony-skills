"""architect-v2's lane observer (E14 slice 2, lane A; reading CR-7). Not a shared file.

`observe.py` (shared) calls `observe_lane(step, case_dir, neutral, facts, via, scratch)` for each
`lane` step of this core's cases. This module translates the case's neutral input and recorded
answer into this core's own terms (a renaming, never an invention), drives the library functions
this core's commands call, and fills exactly the names the step lists under `pending`, from what
the drive did. It never states what a fact should be; the answer key does, elsewhere.

The two families with lane steps:

A2 (the candidates and the razor): `answer_refused`, `refusal_reason`. The recorded answer's
`exit_ramp` ("system" or "no system") is renamed to this core's `exit_ramp.continued` (true or
false), its `walkthrough.must`, `candidates`, `pick`, `rejected` and `components` are taken as they
are, and `architect_core.recording.candidate_refusals` and `razor_refusals` are run on them: the
same functions `record-answer` runs for these checks. The case's answer carries no trace, no
poured-concrete, deferred or doors field and no run id, so the full `record-answer` (whose schema
requires them) is not driven; `_via` says so. `refusal_reason` is the rule name of each refusal,
sorted and joined with ", ", or null when nothing is refused.

A4 (the two actions): `visual_rendered`, `published`, `artifact_line_unchanged`, `terminal_status`.
The case's living doc (the one `docs/architecture/*-<slug>.md` in its workspace) is read;
`architect_core.visual.render` renders it and the visual is written beside it through this core's
receipt (the `render-visual` path); `architect_core.publishing.decide` records the publish with
the answer's `publish` (false as well when the neutral input carries `station_publish: false`,
this core's `station.publish`) and the answer's `publish_url` as the URL the publish returned (the
`record-publish --url` argument); a changed doc is written the same way; `terminal_status` is
`architect_core.publishing.status_after`, the status `report` gives that publish outcome (the case
records no review outcome, the one other thing `report` reads). The drive runs in the case's own
throwaway workspace, so `observe.py`'s measured `writes_none` sees what the drive wrote.
"""
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(PLUGIN, "skills", os.path.basename(PLUGIN), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True

from architect_core import docs, harvesting, publishing, recording, visual  # noqa: E402
from architect_core.receipt import Receipt  # noqa: E402

A2 = ("answer_refused", "refusal_reason")
A4 = ("visual_rendered", "published", "artifact_line_unchanged", "terminal_status")


class LaneObserveError(RuntimeError):
    pass


def _answer(case_dir, neutral):
    if not neutral.get("answer"):
        raise LaneObserveError("the case carries no recorded answer")
    with open(os.path.join(case_dir, neutral["answer"]), encoding="utf-8") as fh:
        return json.load(fh)


def _exit_ramp(value):
    renamed = {"system": True, "no system": False}
    if value not in renamed:
        raise LaneObserveError("the recorded exit ramp %r is neither 'system' nor 'no system'" % (value,))
    return renamed[value]


def _fill(step, facts, via, values, how):
    for name in step.get("pending", []):
        if name in values:
            facts[name] = values[name]
            via[name] = how


def observe_a2(step, case_dir, neutral, facts, via):
    doc = _answer(case_dir, neutral)
    answer = {"exit_ramp": {"continued": _exit_ramp(doc["exit_ramp"])},
              "walkthrough": {"must": list(doc["walkthrough"]["must"])},
              "candidates": doc["candidates"], "pick": doc["pick"], "rejected": doc["rejected"],
              "components": doc["components"]}
    refusals = recording.candidate_refusals(answer) + recording.razor_refusals(answer)
    rules = sorted(set(r["rule"] for r in refusals))
    _fill(step, facts, via, {"answer_refused": bool(refusals), "refusal_reason": ", ".join(rules) or None},
          "library: architect_core.recording.candidate_refusals and razor_refusals (the checks record-answer runs); "
          "the case's answer lacks the fields record-answer's schema requires")


def observe_a4(step, case_dir, neutral, facts, via, scratch):
    doc = _answer(case_dir, neutral)
    found = sorted(glob.glob(os.path.join(neutral["workspace"], "docs", "architecture", "*.md")))
    if len(found) != 1:
        raise LaneObserveError("the case's workspace holds %d architecture docs, not one" % len(found))
    path = found[0]
    with open(path, encoding="utf-8", newline="") as fh:
        before = fh.read()
    receipt = Receipt(scratch)
    slug = harvesting.slug_of(path)
    html = os.path.join(os.path.dirname(path), "%s-architecture.html" % slug)
    receipt.write(html, visual.render(before))
    publish = bool(doc["publish"]) and neutral.get("station_publish", True) is not False
    decision = publishing.decide(before, publish, doc.get("publish_url"))
    after = before
    if decision["refusal"] is not None:
        raise LaneObserveError("the publish record was refused: %s" % decision["refusal"]["message"])
    if decision["changed"]:
        receipt.write(path, decision["text"], expect=_sha(before))
        after = decision["text"]
    line_before = [l for l in before.split("\n") if l.startswith("Artifact:")]
    line_after = [l for l in after.split("\n") if l.startswith("Artifact:")]
    status = publishing.status_after(decision["outcome"])[0]
    _fill(step, facts, via, {"visual_rendered": os.path.isfile(html) and os.path.getsize(html) > 0,
                             "published": decision["outcome"] == "published",
                             "artifact_line_unchanged": line_before == line_after and
                             docs.artifact_url(before) == docs.artifact_url(after),
                             "terminal_status": status},
          "library: architect_core.visual.render, publishing.decide and publishing.status_after, written through "
          "architect_core.receipt (the render-visual and record-publish paths) in the case's workspace")


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def observe_lane(step, case_dir, neutral, facts, via, scratch):
    pending = set(step.get("pending", []))
    if pending & set(A2):
        observe_a2(step, case_dir, neutral, facts, via)
    if pending & set(A4):
        observe_a4(step, case_dir, neutral, facts, via, scratch)
