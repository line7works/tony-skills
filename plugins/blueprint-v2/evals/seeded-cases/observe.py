#!/usr/bin/env python3
"""Drive this core on each of its seeded cases and write down what it did (E14 slice 1).

    PYTHONDONTWRITEBYTECODE=1 python3 observe.py --all --out <dir>
    PYTHONDONTWRITEBYTECODE=1 python3 observe.py --case P2-03-two-homes --out <dir>
    PYTHONDONTWRITEBYTECODE=1 python3 observe.py --list

Identical in the four front cores (`references/shared-files.txt`); the core is this file's own
plugin, and the families are the folders beside it. This script emits FACTS and never an
expectation: the outcome of each case lives in an answer key outside every builder's reach, and
the control room grades `observed.json` against it. It has no notion of a case passing.

Each case is built by its family's `build.py` into `--out`; then the steps of its `drive.json`
are run, in order:

    select    the REAL CLI: `check-input` on the neutral input translated into this core's input,
              then `select --hunt H [--name N]`
    ledger    `station_core/ledger.py` on a document of the case
    answer    `station_core/answer.py` (record-answer's shared refusals) on the recorded answer,
              against the ledger of the case's scope doc; `record` into a scratch run directory
    form      `station_core/templates.py`'s check and round trip on a document of the case
    runlog    `station_core/runlog.py` on a document before and a proposed document after
    request   `station_core/readers_request.py` for each named row, against readers' roster
    v1scan    the no-v1-import scan (`scripts/tests/test_no_v1_import.py`) on a scratch copy of
              this core's skill, with the case's plant placed in it when there is one
    lane      the lane's own facts: when `lane_observe.py` sits beside this file (the core's own,
              written in its slice 2 lane, never shared), its `observe_lane(step, case_dir,
              neutral, facts, via, scratch)` is called and the names it fills are the lane's
              facts; any name the step lists under `pending` that it did not fill stays under
              `_lane_pending` and is never guessed. Without that module every name stays pending.

The library steps drive the shared code the lanes' phases will call; `_via` names which facts came
from the CLI and which from the library. `writes_none` is measured, not read: a digest over the
workspace and the staging home before the first step and after the last.

`--out` is refused, exit 2 and nothing created, when it is or sits under ~/.claude, ~/.codex or a
~/.local/share/skills-v2-* home, as given or resolved (the setups' home guard, E14 slice 3c).

Needs jsonschema for the `select` step (run it under `uv run --with jsonschema==4.25.1`, or an
interpreter that has it). Standard library otherwise, Python 3.9, no network, no model call.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
CORE = os.path.basename(PLUGIN)
SKILL = os.path.join(PLUGIN, "skills", CORE)
SCRIPTS = os.path.join(SKILL, "scripts")
STATION = CORE.split("-")[0]
DRIVER = os.path.join(SCRIPTS, STATION + ("_v2.py" if STATION == "inspect" else ".py"))
GEN_PYTHON = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
FAMILY = re.compile(r"^[A-Z][0-9]+-")

sys.path.insert(0, SCRIPTS)
from station_core import answer as answermod  # noqa: E402
from station_core import ledger as ledgermod  # noqa: E402
from station_core import readers_request, runlog, templates  # noqa: E402


class ObserveError(RuntimeError):
    pass


def families():
    return sorted(n for n in os.listdir(HERE) if FAMILY.match(n) and os.path.isdir(os.path.join(HERE, n)))


def case_ids(family):
    proc = subprocess.run([GEN_PYTHON, os.path.join(HERE, family, "build.py"), "--list"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise ObserveError("%s/build.py --list failed: %s" % (family, proc.stderr.decode()[-400:]))
    return [l for l in proc.stdout.decode().splitlines() if l.strip()]


def build_case(family, case, out):
    proc = subprocess.run([GEN_PYTHON, os.path.join(HERE, family, "build.py"), "--out", out,
                           "--case", case, "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if proc.returncode != 0:
        raise ObserveError("build of %s failed: %s" % (case, proc.stderr.decode()[-600:]))
    return json.loads(proc.stdout.decode())["cases"][0]["path"]


def digest(*roots):
    entries = []
    for root in roots:
        for base, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d != ".git")
            for name in sorted(files):
                full = os.path.join(base, name)
                with open(full, "rb") as fh:
                    entries.append("%s\0%s" % (os.path.relpath(full, os.path.dirname(root)),
                                               hashlib.sha256(fh.read()).hexdigest()))
    return hashlib.sha256("\n".join(sorted(entries)).encode("utf-8")).hexdigest()


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def core_input(neutral, run_dir):
    doc = {"input_version": 1, "run_id": re.sub(r"[^A-Za-z0-9._-]", "-", neutral["case"]),
           "workspace": neutral["workspace"], "run_dir": run_dir,
           "report_only": bool(neutral.get("report_only")),
           "invocation": {"harness": "seeded-case", "caller": "user", "mode": "direct",
                          "session_id": "seeded-session"}}
    if neutral.get("staging"):
        doc["staging"] = neutral["staging"]
    if neutral.get("owner_word"):
        doc["owner_word"] = neutral["owner_word"]
    return doc


def relative(case_dir, path):
    return os.path.relpath(path, case_dir)


def step_select(step, case_dir, neutral, facts, via, scratch):
    run_dir = os.path.join(scratch, "select-run")
    doc = core_input(neutral, run_dir)
    input_path = os.path.join(scratch, "select-input.json")
    with open(input_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([sys.executable, DRIVER, "check-input", input_path], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env, cwd=scratch)
    facts["_phases"].append({"phase": "check-input", "exit": proc.returncode})
    if proc.returncode != 0:
        facts["_errors"].append("check-input exit %d: %s%s" % (proc.returncode, proc.stdout.decode()[-300:],
                                                              proc.stderr.decode()[-300:]))
        return
    argv = [sys.executable, DRIVER, "select", "--run-dir", run_dir]
    if step.get("hunt"):
        argv += ["--hunt", step["hunt"]]
    if step.get("name"):
        argv += ["--name", step["name"]]
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=scratch)
    facts["_phases"].append({"phase": "select", "exit": proc.returncode})
    if proc.returncode != 0:
        facts["_errors"].append("select exit %d: %s" % (proc.returncode, proc.stderr.decode()[-300:]))
        return
    out = json.loads(proc.stdout.decode())
    facts["selection_outcome"] = out["outcome"]
    facts["selection_candidates"] = sorted(relative(case_dir, c["path"]) for c in out["candidates"])
    via["selection_outcome"] = via["selection_candidates"] = "cli"


def step_ledger(step, case_dir, neutral, facts, via, scratch):
    try:
        lines = ledgermod.read(read_text(os.path.join(case_dir, step["doc"])))
        facts["ledger_refused"] = False
        facts["ledger_tags"] = ledgermod.counts(lines)
    except ledgermod.LedgerRefused as exc:
        facts["ledger_refused"] = True
        facts["ledger_refused_lines"] = sorted(row["line"] for row in exc.lines)
    via["ledger_refused"] = "library"


def step_answer(step, case_dir, neutral, facts, via, scratch):
    lines = []
    if step.get("scope_doc"):
        lines = ledgermod.read(read_text(os.path.join(case_dir, step["scope_doc"])))
    doc = read_json(os.path.join(case_dir, neutral["answer"]))
    view = {"questions": doc.get("questions"), "lines": doc.get("lines")}
    allowed = tuple(step.get("allowed") or answermod.DEFAULT_TRACES)
    run_dir = os.path.join(scratch, "answer-run")
    os.makedirs(run_dir)
    code, report = answermod.record(run_dir, view, lines, workspace=neutral["workspace"], allowed=allowed)
    facts["answer_refused"] = code != 0
    facts["refusal_rules"] = sorted(set(r["rule"] for r in report["refusals"]))
    facts["answer_written"] = os.path.isfile(os.path.join(run_dir, "answer.json"))
    via["answer_refused"] = "library"


def step_form(step, case_dir, neutral, facts, via, scratch):
    text = read_text(os.path.join(case_dir, step["doc"]))
    findings = templates.check(step["form"], text)
    facts["form_holds"] = not findings
    facts["form_finding_count"] = len(findings)
    facts["round_trip_identical"] = templates.render(templates.parse(step["form"], text)) == text
    via["form_holds"] = "library"


def step_runlog(step, case_dir, neutral, facts, via, scratch):
    before = read_text(os.path.join(case_dir, step["before"]))
    facts["next_run"] = runlog.next_run(before)
    refused = False
    if step.get("after"):
        losses = runlog.losses(before, read_text(os.path.join(case_dir, step["after"])))
        facts["losses_count"] = len(losses)
        refused = refused or bool(losses)
    if step.get("block"):
        try:
            runlog.append_run(before, read_text(os.path.join(case_dir, step["block"])))
        except runlog.RunLogRefused:
            refused = True
    facts["runlog_refused"] = refused
    via["runlog_refused"] = "library"


def roster():
    path = os.path.join(os.path.dirname(PLUGIN), "readers", "skills", "readers", "assets", "roster.json")
    if not os.path.isfile(path):
        raise ObserveError("readers' roster is not beside this core: %s" % path)
    return readers_request.load_roster(path)


def step_request(step, case_dir, neutral, facts, via, scratch):
    doc = core_input(neutral, os.path.join(scratch, "request-run"))
    ros = roster()
    authorized, documents, profiles = [], set(), set()
    for index, row in enumerate(step["rows"]):
        req = readers_request.build(row, doc, ros, mandate=step.get("mandate", "read this document"),
                                    profile=step.get("profile", "starved"), run_id=doc["run_id"],
                                    call_id="%s-%d" % (doc["run_id"], index),
                                    documents=[os.path.join(case_dir, d) for d in step.get("documents", [])],
                                    session_model="claude-seeded" if row == "claude-session" else None)
        if req.get("authorized") is True:
            authorized.append(row)
        documents.update(os.path.basename(d) for d in req.get("documents", []))
        profiles.add(req["profile"])
    facts["authorized_rows"] = sorted(authorized)
    facts["request_documents"] = sorted(documents)
    facts["request_profiles"] = sorted(profiles)
    via["authorized_rows"] = "library"


def step_v1scan(step, case_dir, neutral, facts, via, scratch):
    copy = os.path.join(scratch, "skill-copy")
    shutil.copytree(SKILL, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    plant = step.get("plant")
    if plant:
        path = os.path.join(copy, plant["rel"])
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("".join(plant["text_parts"]) if plant.get("text_parts") else plant["text"])
    sys.path.insert(0, os.path.join(SCRIPTS, "tests"))
    try:
        import test_no_v1_import as scan  # noqa: E402
    finally:
        sys.path.pop(0)
    found = scan.findings(copy)
    facts["v1_findings_present"] = bool(found)
    facts["v1_finding_count"] = len(found)
    via["v1_findings_present"] = "library"


def lane_observe(step, case_dir, neutral, facts, via, scratch):
    """The lane's own observer, `lane_observe.py` beside this file, when the lane has written it.

    The observer works on its own dict, its own `via` and deep copies of the step and the neutral
    input; the names its step lists under `pending` are read BEFORE the call and returned, so an
    observer can neither extend nor empty that list. Only a listed name no frame step observed is
    taken from it, with that name's `via` entry; every other name it fills (or `via` entry it
    adds) is recorded under `_errors` and never merged. Its `_phases` and `_errors` are appended
    to the run's. Any error it raises, `SystemExit` included, lands in `_errors`. Returns the
    listed names as read before the call."""
    listed = list(step.get("pending", []))
    path = os.path.join(HERE, "lane_observe.py")
    if not os.path.isfile(path):
        return listed
    import copy
    import importlib.util
    spec = importlib.util.spec_from_file_location("lane_observe", path)
    module = importlib.util.module_from_spec(spec)
    lane = {"_phases": [], "_errors": []}
    lane_via = {}
    try:
        spec.loader.exec_module(module)
        module.observe_lane(copy.deepcopy(step), case_dir, copy.deepcopy(neutral), lane, lane_via, scratch)
    except BaseException as exc:  # noqa: BLE001  (a lane observer's error is a fact of the run)
        if isinstance(exc, KeyboardInterrupt):
            raise
        lane.setdefault("_errors", []).append({"step": "lane", "error": "%s: %s" % (type(exc).__name__, exc)})
    phases = lane.pop("_phases", None)
    errors = lane.pop("_errors", None)
    if isinstance(phases, list):
        facts["_phases"].extend(phases)
    elif phases is not None:
        facts["_errors"].append({"step": "lane", "error": "the lane observer's _phases is not a list: %r" % (phases,)})
    if isinstance(errors, list):
        for entry in errors:
            if isinstance(entry, dict) and isinstance(entry.get("error"), str):
                facts["_errors"].append(entry)
            else:
                facts["_errors"].append({"step": "lane", "error": "a lane _errors entry is not a mapping with an "
                                         "error: %r" % (entry,)})
    elif errors is not None:
        facts["_errors"].append({"step": "lane", "error": "the lane observer's _errors is not a list: %r" % (errors,)})
    for bad in [key for key in list(lane) + list(lane_via) if not isinstance(key, str)]:
        facts["_errors"].append({"step": "lane", "error": "the lane observer used a key that is not a string: %r; "
                                 "not merged" % (bad,)})
        lane.pop(bad, None)
        lane_via.pop(bad, None)
    merged = []
    for name in sorted(lane):
        if name in listed and name not in facts:
            facts[name] = lane[name]
            merged.append(name)
        else:
            facts["_errors"].append({"step": "lane", "error": "the lane observer filled %r, which its step does "
                                     "not list or the frame already observed; not merged" % name})
    for name in sorted(lane_via):
        if name in merged and isinstance(lane_via[name], str) and lane_via[name].strip():
            via[name] = lane_via[name]
        elif name in merged:
            facts["_errors"].append({"step": "lane", "error": "the lane observer's via for %r is not a non-empty "
                                     "string: %r; not merged" % (name, lane_via[name])})
            del lane_via[name]
        else:
            facts["_errors"].append({"step": "lane", "error": "the lane observer set a provenance for %r, which "
                                     "it did not fill as a listed fact; not merged" % name})
    for name in merged:
        if name not in lane_via:
            facts["_errors"].append({"step": "lane", "error": "the lane observer filled %r with no via" % name})
    return listed


STEPS = {"select": step_select, "ledger": step_ledger, "answer": step_answer, "form": step_form,
         "runlog": step_runlog, "request": step_request, "v1scan": step_v1scan}


def observe(family, case, out):
    case_dir = build_case(family, case, out)
    neutral = read_json(os.path.join(case_dir, "input.json"))
    drive = read_json(os.path.join(case_dir, "drive.json"))
    facts = {"_case": case, "_family": family, "_core": CORE, "_phases": [], "_errors": []}
    via = {}
    pending = []
    roots = [neutral["workspace"], neutral["staging"]]
    before = digest(*roots)
    scratch = tempfile.mkdtemp(prefix="observe-")
    try:
        for index, step in enumerate(drive["steps"]):
            if step["kind"] == "lane":
                sub = os.path.join(scratch, "step-%d" % index)
                os.makedirs(sub)
                listed = lane_observe(step, case_dir, neutral, facts, via, sub)
                pending.extend(name for name in listed if name not in facts)
                continue
            sub = os.path.join(scratch, "step-%d" % index)
            os.makedirs(sub)
            STEPS[step["kind"]](step, case_dir, neutral, facts, via, sub)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    facts["writes_none"] = digest(*roots) == before
    facts["_via"] = via
    if pending:
        facts["_lane_pending"] = sorted(set(pending))
    if not facts["_errors"]:
        del facts["_errors"]
    with open(os.path.join(case_dir, "observed.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(facts, indent=2, sort_keys=True) + "\n")
    return facts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Observe %s on its seeded cases." % CORE)
    parser.add_argument("--all", action="store_true", help="every case of every family of this core")
    parser.add_argument("--case", action="append", default=[], help="one case id (repeatable)")
    parser.add_argument("--list", action="store_true", help="print family and case ids")
    parser.add_argument("--out", help="the output directory the cases are built into")
    args = parser.parse_args(argv)
    # The setups' home guard (E14 slice 3c fix 3-2), before anything is created.
    out = os.path.abspath(args.out or os.curdir)
    home = os.environ.get("HOME", "")
    share = os.path.join(home, ".local", "share")
    temps = [os.environ[name] for name in ("TMPDIR", "TEMP", "TMP") if os.environ.get(name)] or ["/tmp"]
    for path in [out, os.path.realpath(out)] + [form(t) for t in temps for form in (os.path.abspath, os.path.realpath)]:
        for base in (os.path.join(home, ".claude"), os.path.join(home, ".codex"), share):
            for form in (os.path.abspath(base), os.path.realpath(base)):
                p, b = path.casefold(), form.casefold().rstrip(os.sep)
                below = "" if p == b else (p[len(b) + 1:] if p.startswith(b + os.sep) else None)
                if below is None or (base == share and not below.split(os.sep)[0].startswith("skills-v2-")):
                    continue
                sys.stderr.write("observe.py: %s is under %s, which no setup may touch; nothing created\n"
                                 % (path, base if base != share else os.path.join(share, below.split(os.sep)[0])))
                return 2
    if not os.path.isabs(home):
        sys.stderr.write("observe.py: HOME is not an absolute path; nothing created\n")
        return 2
    catalog = [(f, c) for f in families() for c in case_ids(f)]
    if args.list:
        for f, c in catalog:
            print("%s  %s" % (f, c))
        return 0
    if not args.out or not (args.all or args.case):
        parser.error("--out and one of --all or --case are required")
    wanted = catalog if args.all else [(f, c) for f, c in catalog if c in args.case]
    unknown = sorted(set(args.case) - set(c for _, c in catalog))
    if unknown:
        sys.stderr.write("unknown case id(s): %s\n" % ", ".join(unknown))
        return 2
    os.makedirs(args.out, exist_ok=True)
    rows = []
    for family, case in wanted:
        facts = observe(family, case, os.path.join(args.out, family))
        rows.append({"case": case, "observed": os.path.join(args.out, family, case, "observed.json"),
                     "errors": facts.get("_errors", [])})
    sys.stdout.write(json.dumps({"core": CORE, "cases": rows}, indent=2, sort_keys=True) + "\n")
    return 1 if any(r["errors"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
