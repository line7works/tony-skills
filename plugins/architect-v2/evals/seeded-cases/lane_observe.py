"""architect-v2's lane observer (E14 slice 2, lane A; reading CR-7). Not a shared file.

`observe.py` (shared) calls `observe_lane(step, case_dir, neutral, facts, via, scratch)` for each
`lane` step of this core's cases. This module translates the case's neutral input and recorded
answer into this core's own terms (a renaming where the case says it; where a full answer needs
more than the case records, a stated translation choice, never a fact of the case), drives this
core's real CLI (A4) or the library functions its commands call (A2), saying which in `_via`, and
fills exactly the names the step lists under `pending`, from what the drive did. It never states
what a fact should be; the answer key does, elsewhere.

The two families with lane steps:

A2 (the candidates and the razor): `answer_refused`, `refusal_reason`. The recorded answer's
`exit_ramp` ("system" or "no system") is renamed to this core's `exit_ramp.continued` (true or
false), its `walkthrough.must`, `candidates`, `pick`, `rejected` and `components` are taken as they
are, and `architect_core.recording.candidate_refusals` and `razor_refusals` are run on them: the
same functions `record-answer` runs for these checks. The case's answer carries no trace, no
poured-concrete, deferred or doors field and no run id, so the full `record-answer` (whose schema
requires them) is not driven; `_via` says so. `refusal_reason` is the rule name of each refusal,
sorted and joined with ", ", or null when nothing is refused.

A4 (the two actions): `visual_rendered`, `published`, `artifact_line_unchanged`, `terminal_status`,
from a REAL drive of this core's CLI (`scripts/architect.py`) in a copy of the case (its workspace
and staging home copied under the observer's scratch, so the case's own tree is not written):
`check-input`, `select --hunt scope`, `select --hunt architecture --name <slug>`, `harvest`,
`record-answer`, `write`, `render-visual`, `record-publish` and `report`, each phase with its exit
under `_phases`. The facts are what the drive printed and left: `visual_rendered` is
`render-visual` exiting 0 with its file on disk, `published` and `terminal_status` are the
`report` result's `station_result.published` and `status`, and `artifact_line_unchanged` compares
the copied doc's `Artifact:` lines before the drive and after it.

The translation into this core's answer. A renaming of the case where the case says it: the
answer's `publish` (false as well when the neutral input carries `station_publish: false`, which
also becomes the input's `station.publish: false`); the case's `publish_url`, which is the URL the
executor's publish returned, becomes the `record-publish --url` argument (none when it is null),
and the answer's own `publish_url` is the living doc's recorded URL when the run publishes (the
same URL across runs), else null; the case's `questions`, `lines` and `session_id` as they are.
The rest of a full answer is the living doc carried forward as it stands: the project from its
title; the walkthrough from its `Who:` line (the `must` items split on the renderer's `; `), traced
to the doc's own path in the workspace (`repo_path`); the exit ramp and the doors from its last
run block; the candidates, the pick and each rejected why from the last run block that lists
them; the data flow and the diagram as they read; every poured-concrete and deferred line
carried. Translation CHOICES, facts of no case: the review is declined by the owner on the run's
date (v1 allows declining; the A4 cases record no blind-review outcome, and `report` stops
`review-pending` on none); each candidate's one-way-door category is `structure:<its name>` (the
doc's form records no category per candidate); a component the doc lists without `(serves: ...)`
serves the walkthrough's first requirement; the trigger is `re-render and publish` and the change
line `nothing changed; the visual re-rendered and its publish recorded`.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(PLUGIN, "skills", os.path.basename(PLUGIN), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True

from architect_core import docs, harvesting, recording  # noqa: E402
from architect_core.common import D, M  # noqa: E402

DRIVER = os.path.join(SCRIPTS, "architect.py")

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


def _cli(argv, scratch, lane, phase):
    proc = subprocess.run([sys.executable, DRIVER] + argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), cwd=scratch)
    lane["_phases"].append({"phase": phase, "exit": proc.returncode})
    out = proc.stdout.decode("utf-8")
    try:
        doc = json.loads(out) if out.strip() else None
    except ValueError:
        doc = None
    return proc.returncode, doc, out + proc.stderr.decode("utf-8")


def _must(code, want, phase, text):
    if code != want:
        raise LaneObserveError("%s exited %d, not %d: %s" % (phase, code, want, text[-600:]))


def _artifact_lines(text):
    return [l for l in text.split("\n") if l.startswith("Artifact:")]


def _label(body, label):
    for line in body:
        if line.startswith(label):
            return line[len(label):].strip()
    raise LaneObserveError("the living doc holds no %r line" % label)


def _last_block_value(text, label, skip=("unchanged",)):
    """The value of `label` in the latest run block where it says something other than `skip`."""
    found = None
    for line in text.split("\n"):
        if line.startswith(label):
            value = line[len(label):].strip()
            if value not in skip:
                found = value
    if found is None:
        raise LaneObserveError("no run block records %r" % label)
    return found


def translate(doc_text, doc_rel, case_answer, publish, today):
    """This core's answer for an A4 case: the case's own fields renamed, the living doc carried."""
    title, header, sections = docs.split(doc_text)
    match = re.match(r"^# (.+) %s architecture \(" % D, title[-1])
    if not match:
        raise LaneObserveError("the living doc's title is not on its form: %r" % title[-1])
    body = dict(sections)
    who_line = [l for l in body[docs.WALK] if l.startswith("Who:") and not l.startswith("~~")]
    parts = re.match(r"^Who: (.+)  %s  When: (.+)  %s  Must be able to: (.+)$" % (M, M), who_line[-1])
    if not parts:
        raise LaneObserveError("the walkthrough line is not on its form: %r" % who_line[-1])
    must = parts.group(3).split("; ")
    ramp = _last_block_value(doc_text, "Exit ramp:")
    continued = not ramp.startswith("no system")
    step32 = _last_block_value(doc_text, "Step 3.2 (candidates):")
    shown, rest = step32.split("; chosen: ", 1)
    pick, rejected_text = rest.split("; rejected: ", 1)
    names = shown.split("; ")
    rejected = []
    for item in rejected_text.split(", "):
        name, why = item.split(" %s " % D, 1)
        rejected.append({"name": name, "why": why})
    components = []
    for item in _label(body[docs.DRAWING], "Components:").split("; "):
        served = re.match(r"^(.+) \(serves: (.+)\)$", item)
        components.append({"name": served.group(1), "serves": served.group(2)} if served
                          else {"name": item, "serves": must[0]})
    carried = lambda heading: [{"carried": l[2:]} for l in body.get(heading, []) if l.startswith("- ")]
    return {
        "answer_version": 1, "run_id": None, "session_id": case_answer.get("session_id"),
        "project": match.group(1), "trigger": "re-render and publish",
        "changed": "nothing changed; the visual re-rendered and its publish recorded",
        "questions": case_answer.get("questions") or [],
        "exit_ramp": {"continued": continued, "why": ramp},
        "walkthrough": {"who": parts.group(1), "when": parts.group(2), "must": must,
                        "trace": {"kind": "repo_path", "ref": doc_rel}},
        "candidates": [{"name": n, "categories": ["structure:%s" % n], "assumes": "as the living doc records it",
                        "later_cost": "as the living doc records it"} for n in names] if continued else [],
        "pick": pick if continued else None, "rejected": rejected if continued else [],
        "components": components,
        "data_flow": _label(body[docs.DRAWING], "Data flow:"), "diagram": _label(body[docs.DRAWING], "Diagram:"),
        "doors": {"settled": _last_block_value(doc_text, "Step 3.3 (one-way doors):", skip=())} if continued else None,
        "poured_concrete": carried(docs.POURED), "deferred": carried(docs.DEFERRED),
        "lines": case_answer.get("lines") or [],
        "review": {"outcome": "declined", "date": today}, "rulings": [],
        "publish": publish, "publish_url": docs.artifact_url(doc_text) if publish else None,
    }


def observe_a4(step, case_dir, neutral, facts, via, scratch):
    case_answer = _answer(case_dir, neutral)
    copy = os.path.join(scratch, "case-copy")
    ws = os.path.join(copy, "workspace")
    staging = os.path.join(copy, "staging")
    shutil.copytree(neutral["workspace"], ws, symlinks=True)
    shutil.copytree(neutral["staging"], staging, symlinks=True)
    run_dir = os.path.join(scratch, "run")
    input_publish = neutral.get("station_publish", True) is not False
    doc = {"input_version": 1, "run_id": re.sub(r"[^A-Za-z0-9._-]", "-", neutral["case"]), "workspace": ws,
           "staging": staging, "run_dir": run_dir, "report_only": bool(neutral.get("report_only")),
           "invocation": {"harness": "seeded-case", "caller": "user", "mode": "direct",
                          "session_id": "seeded-session"}}
    if not input_publish:
        doc["station"] = {"publish": False}
    input_path = os.path.join(scratch, "input.json")
    with open(input_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    code, out, text = _cli(["check-input", input_path], scratch, facts, "check-input")
    _must(code, 0, "check-input", text)
    code, out, text = _cli(["select", "--run-dir", run_dir, "--hunt", "scope"], scratch, facts, "select")
    _must(code, 0, "select --hunt scope", text)
    if out["outcome"] != "one":
        raise LaneObserveError("the scope hunt found %s, not one scope doc" % out["outcome"])
    slug = harvesting.slug_of(out["candidates"][0]["path"])
    code, out, text = _cli(["select", "--run-dir", run_dir, "--hunt", "architecture", "--name", slug], scratch, facts,
                           "select")
    _must(code, 0, "select --hunt architecture", text)
    code, out, text = _cli(["harvest", "--run-dir", run_dir], scratch, facts, "harvest")
    _must(code, 0, "harvest", text)
    if not out.get("living_doc"):
        raise LaneObserveError("the harvest found no living doc in the case's copy")
    doc_path = out["living_doc"]["path"]
    with open(doc_path, encoding="utf-8", newline="") as fh:
        before = fh.read()
    with open(os.path.join(run_dir, "harvest.json"), encoding="utf-8") as fh:
        today = json.load(fh)["today"]
    publish = bool(case_answer["publish"]) and input_publish
    answer = translate(before, os.path.relpath(doc_path, ws), case_answer, publish, today)
    answer["run_id"] = doc["run_id"]
    answer_path = os.path.join(scratch, "answer.json")
    with open(answer_path, "w", encoding="utf-8") as fh:
        json.dump(answer, fh)
    code, out, text = _cli(["record-answer", "--run-dir", run_dir, "--answer", answer_path], scratch, facts,
                           "record-answer")
    _must(code, 0, "record-answer", text)
    code, out, text = _cli(["write", "--run-dir", run_dir], scratch, facts, "write")
    _must(code, 0, "write", text)
    code, out, text = _cli(["render-visual", "--run-dir", run_dir], scratch, facts, "render-visual")
    rendered = code == 0 and bool(out) and os.path.isfile(out["visual"]) and os.path.getsize(out["visual"]) > 0
    _must(code, 0, "render-visual", text)
    argv = ["record-publish", "--run-dir", run_dir]
    if publish and case_answer.get("publish_url"):
        argv += ["--url", case_answer["publish_url"]]
    code, out, text = _cli(argv, scratch, facts, "record-publish")
    _must(code, 0, "record-publish", text)
    code, result, text = _cli(["report", "--run-dir", run_dir], scratch, facts, "report")
    _must(code, 10, "report", text)
    with open(doc_path, encoding="utf-8", newline="") as fh:
        after = fh.read()
    how = ("cli: a real drive of check-input, select (scope, architecture), harvest, record-answer, write, "
           "render-visual, record-publish and report on a copy of the case (the translation and its choices are "
           "this module's docstring)")
    _fill(step, facts, via, {"visual_rendered": rendered,
                             "published": result["station_result"]["published"],
                             "artifact_line_unchanged": _artifact_lines(before) == _artifact_lines(after),
                             "terminal_status": result["status"]}, how)


def observe_lane(step, case_dir, neutral, facts, via, scratch):
    pending = set(step.get("pending", []))
    if pending & set(A2):
        observe_a2(step, case_dir, neutral, facts, via)
    if pending & set(A4):
        observe_a4(step, case_dir, neutral, facts, via, scratch)
