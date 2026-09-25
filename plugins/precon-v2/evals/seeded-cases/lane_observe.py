"""precon-v2's own observer of the lane facts (lane P; not a shared file, reading CR-7).

    observe_lane(step, case_dir, neutral, facts, via, scratch)

`observe.py` (shared) calls this for every `lane` step of a case of this core. It translates the
case's neutral input and recorded answer into precon-v2's own input and answer, by renaming only,
drives the REAL phase driver (`scripts/precon.py`, as a subprocess, the way the control room's
`select` step does), and fills, from what the driver did, exactly the names the step lists under
`pending` that it has a fact for; `via[name]` is `cli` for each, never over a `_via` entry the
frame already set (the frame keeps what it observed). A name it has no fact for is left out, so
`observe.py` keeps it under `_lane_pending`; nothing is guessed and nothing is read from the
answer file as an outcome.

The drives, each only when a pending name needs it:

    select          check-input, then `select --hunt <step.hunt or scope> --name <idea>`; the idea
                    is the step's `name`, else the slug of its `scope_doc` (or first `documents`) file name
                    -> selection_outcome, selection_candidates
    harvest         after select -> ledger_refused, ledger_refused_lines, ledger_tags
    record-answer   after harvest, the case's answer renamed onto precon-v2's answer (`questions`
                    and `lines` as they are, `run_id` and `answer_version` bound to this run; no
                    field of the executor's judgment, a triage or a gate, is supplied), written
                    as `lane-answer.json` inside the run directory, where `record-answer` reads it
                    -> answer_refused, answer_written, refusal_rules (exit 5), refusal_reason;
                    when precon-v2's answer schema refuses the renamed answer (exit 4: the
                    neutral answer carries no triage and no gate), no answer fact is filled, since
                    that refusal says nothing about the answer's traceability
    request         after harvest, one `--row` per row of the step's `rows`
                    -> authorized_rows, request_documents, request_profiles, refusal_reason

`writes_none`, when pending, is a digest over the case's workspace and staging home before and
after these drives. Standard library only; the run directories live under `scratch`.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
DRIVER = os.path.join(PLUGIN, "skills", "precon-v2", "scripts", "precon.py")
SELECT = ("selection_outcome", "selection_candidates")
LEDGER = ("ledger_refused", "ledger_refused_lines", "ledger_tags")
ANSWER = ("answer_refused", "answer_written", "refusal_rules")
REQUEST = ("authorized_rows", "request_documents", "request_profiles")
SLUG = re.compile(r"^(?:\d{4}-\d{2}-\d{2}-)?(?P<name>[a-z0-9][a-z0-9._-]*?)(?:-scope)?\.md$")


def _digest(*roots):
    entries = []
    for root in roots:
        for base, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d != ".git")
            for name in sorted(files):
                full = os.path.join(base, name)
                with open(full, "rb") as fh:
                    entries.append("%s\0%s" % (os.path.relpath(full, root), hashlib.sha256(fh.read()).hexdigest()))
    return hashlib.sha256("\n".join(sorted(entries)).encode("utf-8")).hexdigest()


class _Driver(object):

    def __init__(self, scratch, facts):
        self.scratch = scratch
        self.facts = facts

    def __call__(self, args):
        proc = subprocess.run([sys.executable, DRIVER] + [str(a) for a in args], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=self.scratch,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        out = proc.stdout.decode("utf-8", "replace")
        self.facts.setdefault("_phases", []).append({"phase": args[0], "exit": proc.returncode, "via": "lane"})
        try:
            doc = json.loads(out) if out.strip() else None
        except ValueError:
            doc = None
        return proc.returncode, doc, proc.stderr.decode("utf-8", "replace")


def _core_input(neutral, run_dir):
    doc = {"input_version": 1, "run_id": re.sub(r"[^A-Za-z0-9._-]", "-", neutral["case"]),
           "workspace": neutral["workspace"], "run_dir": run_dir, "report_only": bool(neutral.get("report_only")),
           "invocation": {"harness": "seeded-case", "caller": "user", "mode": "direct",
                          "session_id": "seeded-session"}}
    if neutral.get("staging"):
        doc["staging"] = neutral["staging"]
    if neutral.get("owner_word"):
        doc["owner_word"] = neutral["owner_word"]
    return doc


def _idea(step):
    if step.get("name"):
        return step["name"]
    for doc in [step.get("scope_doc")] + list(step.get("documents") or []):
        match = SLUG.match(os.path.basename(doc or ""))
        if doc and match:
            return match.group("name")
    return None


def _answer(case_dir, neutral, run_id):
    """The case's recorded answer renamed onto precon-v2's answer; nothing of the executor's added."""
    if not neutral.get("answer"):
        return None
    with open(os.path.join(case_dir, neutral["answer"]), encoding="utf-8") as fh:
        doc = json.load(fh)
    out = {"answer_version": 1, "run_id": run_id, "session_id": doc.get("session_id")}
    for key in ("questions", "lines"):
        if key in doc:
            out[key] = doc[key]
    return out


def observe_lane(step, case_dir, neutral, facts, via, scratch):
    pending = set(step.get("pending") or [])
    if not pending:
        return
    roots = [r for r in (neutral.get("workspace"), neutral.get("staging")) if r]
    before = _digest(*roots)
    run = _Driver(scratch, facts)
    found = {}

    def fill(name, value):
        if name in pending:
            found[name] = value

    run_dir = os.path.join(scratch, "lane-run")
    doc = _core_input(neutral, run_dir)
    input_path = os.path.join(scratch, "lane-input.json")
    with open(input_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    needs_select = pending & set(SELECT + LEDGER + ANSWER + REQUEST + ("refusal_reason",))
    idea = _idea(step)
    if needs_select and idea:
        code, out, err = run(["check-input", input_path])
        if code == 0:
            code, out, err = run(["select", "--run-dir", run_dir, "--hunt", step.get("hunt") or "scope",
                                  "--name", idea])
            if code == 0 and out:
                fill("selection_outcome", out["outcome"])
                fill("selection_candidates", sorted(os.path.relpath(c["path"], case_dir) for c in out["candidates"]))
                _after_select(step, case_dir, neutral, run, run_dir, doc["run_id"], pending, fill)
    if "writes_none" in pending:
        fill("writes_none", _digest(*roots) == before)
    for name, value in found.items():
        facts[name] = value
        if name not in via:
            via[name] = "cli"


def _after_select(step, case_dir, neutral, run, run_dir, run_id, pending, fill):
    if not pending & set(LEDGER + ANSWER + REQUEST + ("refusal_reason",)):
        return
    code, out, err = run(["harvest", "--run-dir", run_dir])
    if code == 10 and out and out.get("stop_tag") == "ledger-refused":
        fill("ledger_refused", True)
        fill("ledger_refused_lines", sorted(r["line"] for r in out["station_result"]["ledger_refused"]))
        return
    if code != 0 or not out:
        return
    fill("ledger_refused", False)
    fill("ledger_tags", out["counts"])
    if pending & set(REQUEST) and step.get("rows"):
        args = ["request", "--run-dir", run_dir]
        for row in step["rows"]:
            args += ["--row", row]
        if "claude-session" in step["rows"]:
            args += ["--session-model", "claude-seeded"]
        code, out, err = run(args)
        if code == 0 and out:
            built = []
            for row in out["requests"]:
                with open(row["path"], encoding="utf-8") as fh:
                    built.append(json.load(fh))
            fill("authorized_rows", sorted(r["row"] for r in built if r.get("authorized") is True))
            fill("request_documents", sorted(set(os.path.basename(d) for r in built for d in r.get("documents", []))))
            fill("request_profiles", sorted(set(r["profile"] for r in built)))
        elif code == 2:
            fill("authorized_rows", [])
            fill("request_documents", [])
            fill("request_profiles", [])
            fill("refusal_reason", err.strip())
        return
    answer = _answer(case_dir, neutral, run_id)
    if answer is None or not pending & set(ANSWER + ("refusal_reason",)):
        return
    # inside the run directory: `record-answer` reads an answer only from the workspace, the staging home
    # or the run directory (the property line), and the case's workspace is never written
    path = os.path.join(run_dir, "lane-answer.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(answer, fh)
    code, out, err = run(["record-answer", "--run-dir", run_dir, "--answer", path])
    if code not in (0, 5):
        # exit 4: the renamed answer fails precon-v2's own schema before any content rule runs; the
        # answer facts stay pending rather than be filled from a refusal of the translation (CP1-14)
        return
    fill("answer_refused", code != 0)
    fill("answer_written", os.path.isfile(os.path.join(run_dir, "answer.json")))
    if code == 5 and out:
        fill("refusal_rules", sorted(set(r["rule"] for r in out["refusals"])))
        fill("refusal_reason", out.get("reason"))
