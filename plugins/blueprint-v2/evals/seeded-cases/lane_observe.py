"""blueprint-v2's lane facts for its seeded families (lane L; reading CR-7; not a shared file).

`observe.py` calls `observe_lane(step, case_dir, neutral, facts, via, scratch)` for every `lane`
step of this core's cases. This module drives the REAL phase driver, `scripts/blueprint.py`, as a
subprocess (check-input, select, harvest, record-answer, write, report), and fills exactly the
names the step lists under `pending`, from what the drive printed and what it left on disk; never
from what a case expects, which this module does not know. A name it has no fact for is left
unfilled, and `observe.py` keeps it under `_lane_pending`.

    answer_refused, refusal_reason
        record-answer on the case's recorded answer, translated into this core's answer by
        renaming (section "The translation" below). `answer_refused` is true when record-answer
        exits 5 (refused on content); `refusal_reason` is this core's own refusal rule names (the
        rules the frame's shared check does not make), sorted and joined by ", ".
    extended_in_place, protected_lines_identical, importer_reads
        a full run over a SCRATCH COPY of the case's workspace (so the case's own tree is never
        written and `writes_none` keeps measuring the case), with the lane's own extension answer
        (one more slice, traced to a repo path of the case). `extended_in_place`: write exited 0
        with action `extended` on the build doc the hunt found, and no other file appeared under
        `docs/plans/`. `protected_lines_identical`: every `Status:` line of the doc before the
        write (its label in any case, at any indent) is still there, in order, byte for byte;
        every `Plan: inspected` line is identical; and every line from `## Build assumptions` to
        the end is identical. Read here from the doc's bytes after the drive in every branch, a
        write that stopped or wrote nothing included, never set from an exit code nor through the
        core's own guard. `importer_reads`: the records component's
        `import-legacy --dry-run`, reached through the resolver and the CLI only, on another scratch
        copy of the written workspace, answers with no ambiguity and one slice per slice heading.

The translation (the neutral answer into this core's answer). The recorded answer's `questions`,
`lines` and `criteria` are carried as they are, and its `session_id` too; `answer_version` and
`run_id` are the run's own; the neutral answer carries no slice and no ceremony, so the translated
answer carries `slices: []`, `assumptions: []`, `open_questions: []` and
`ceremony: {"needs_build_doc": false, ...}`, the one ceremony consistent with no slice. The
neutral bookkeeping (`seeded_answer`, `case`, `role`) is dropped.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(PLUGIN, "skills", "blueprint-v2", "scripts")
DRIVER = os.path.join(SCRIPTS, "blueprint.py")
SHARED_RULES = ("shape", "re-asked-decided", "unknown-line", "untraced", "quietly-resolved")
DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-")
D = "\u2014"


class Drive(object):
    """One run of the real driver in `scratch`."""

    def __init__(self, scratch, workspace, run_id, session="seeded-session"):
        os.makedirs(scratch, exist_ok=True)
        self.scratch = scratch
        self.workspace = workspace
        self.run_dir = os.path.join(scratch, "run")
        self.run_id = run_id
        self.session = session
        self.phases = []

    def cli(self, args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run([sys.executable, DRIVER] + list(args), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=env, cwd=self.scratch)
        out = proc.stdout.decode("utf-8", "replace")
        try:
            doc = json.loads(out) if out.strip() else None
        except ValueError:
            doc = None
        self.phases.append({"phase": args[0], "exit": proc.returncode})
        if doc is None and proc.returncode not in (0, 4, 5, 10):
            raise RuntimeError("%s exit %d: %s" % (args[0], proc.returncode,
                                                   proc.stderr.decode("utf-8", "replace")[-400:]))
        return proc.returncode, doc

    def start(self, name):
        doc = {"input_version": 1, "run_id": self.run_id, "workspace": self.workspace, "run_dir": self.run_dir,
               "report_only": False, "invocation": {"harness": "seeded-case", "caller": "user", "mode": "direct",
                                                    "session_id": self.session}}
        path = os.path.join(self.scratch, "input.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        self.expect(self.cli(["check-input", path]), 0)
        for hunt, hunt_name in (("scope", None), ("architecture", None), ("build", name)):
            args = ["select", "--run-dir", self.run_dir, "--hunt", hunt]
            if hunt_name:
                args += ["--name", hunt_name]
            self.expect(self.cli(args), 0)
        return self.expect(self.cli(["harvest", "--run-dir", self.run_dir]), 0)

    def record(self, answer):
        path = os.path.join(self.scratch, "answer.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(answer, fh)
        return self.cli(["record-answer", "--run-dir", self.run_dir, "--answer", path])

    @staticmethod
    def expect(result, code):
        if result[0] != code:
            raise RuntimeError("expected exit %d, got %d: %s" % (code, result[0], json.dumps(result[1])[:400]))
        return result[1]


def _slug(path):
    base = os.path.basename(path)[:-len(".md")]
    return DATED.sub("", base)


def _feature(workspace):
    """The feature's slug, from the case's own documents' file names (plans first, then scope)."""
    for folder in ("docs/plans", "docs/scope"):
        full = os.path.join(workspace, folder)
        if os.path.isdir(full):
            names = sorted(n for n in os.listdir(full) if n.endswith(".md"))
            if names:
                return _slug(names[0])
    raise RuntimeError("the case holds no build or scope doc to name its feature by")


def translate(recorded, run_id):
    return {"answer_version": 1, "run_id": run_id, "session_id": recorded.get("session_id"),
            "questions": recorded.get("questions") or [], "lines": recorded.get("lines") or [],
            "criteria": recorded.get("criteria") or [], "slices": [], "assumptions": [], "open_questions": [],
            "ceremony": {"needs_build_doc": False,
                         "why": "the recorded answer carries no slice, so it records no build doc"}}


def _record_facts(step, case_dir, neutral, facts, via, scratch):
    with open(os.path.join(case_dir, neutral["answer"]), encoding="utf-8") as fh:
        recorded = json.load(fh)
    run_id = re.sub(r"[^A-Za-z0-9._-]", "-", neutral["case"])
    drive = Drive(scratch, neutral["workspace"], run_id, session=recorded.get("session_id") or "seeded-session")
    drive.start(_feature(neutral["workspace"]))
    code, out = drive.record(translate(recorded, run_id))
    facts["_phases"].extend(dict(p, lane=True) for p in drive.phases)
    if "answer_refused" in step["pending"]:
        facts["answer_refused"] = code == 5
        via["answer_refused"] = "cli: blueprint.py record-answer (exit %d)" % code
    if "refusal_reason" in step["pending"] and code == 5:
        own = sorted(set(r["rule"] for r in out["refusals"] if r["rule"] not in SHARED_RULES))
        if own:
            facts["refusal_reason"] = ", ".join(own)
            via["refusal_reason"] = "cli: blueprint.py record-answer, this core's own refusal rules"


def _labelled(line, label):
    return line.lstrip().casefold().startswith(label.casefold())


def _status_and_stamps(text):
    lines = text.splitlines(True)
    start = next((i for i, l in enumerate(lines) if l.rstrip("\r\n") == "## Build assumptions"), len(lines))
    return ([l for l in lines[:start] if _labelled(l, "Status:")],
            [l for l in lines[:start] if _labelled(l, "Plan: inspected")], lines[start:])


def _read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def _extension_answer(harvest, run_id, session):
    existing = [s["name"] for s in (harvest.get("build") or {}).get("slices") or []]
    letters = [chr(c) for c in range(ord("A"), ord("Z") + 1) if chr(c) not in existing]
    name = letters[0]
    anchor = "README.md"
    return {"answer_version": 1, "run_id": run_id, "session_id": session,
            "feature": harvest["build_name"], "title": "Observer probe", "intent": "the lane observer's probe",
            "questions": [],
            "lines": [{"id": "RP1", "tag": "requirement", "text": "RP1 %s the lane observer's probe slice" % D,
                       "trace": {"kind": "repo_path", "ref": anchor}},
                      {"id": "CP1", "tag": "constraint", "text": "the lane observer's probe constraint",
                       "trace": {"kind": "repo_path", "ref": anchor}}],
            "criteria": [{"id": "ACP1", "text": "ACP1: the probe slice is present",
                          "verify": "manual: read the build doc"}],
            "slices": [{"name": name, "short": "Observer probe", "goal": "the lane observer's probe slice.",
                        "requirements": ["RP1"], "criteria": ["ACP1"], "footprint": [anchor],
                        "not_in_slice": "everything else", "depends_on": existing[-1:]}],
            "assumptions": [], "open_questions": [],
            "ceremony": {"needs_build_doc": True, "why": "the lane observer's probe"}}


def _write_facts(step, case_dir, neutral, facts, via, scratch):
    os.makedirs(scratch, exist_ok=True)
    workspace = os.path.join(scratch, "workspace-copy")
    shutil.copytree(neutral["workspace"], workspace, symlinks=True)
    run_id = re.sub(r"[^A-Za-z0-9._-]", "-", neutral["case"])
    drive = Drive(scratch, workspace, run_id)
    harvest = drive.start(_feature(workspace))
    build = harvest.get("build")
    plans = os.path.join(workspace, "docs", "plans")
    listing = sorted(os.listdir(plans)) if os.path.isdir(plans) else []
    before = _read(build["path"]) if build else None
    Drive.expect(drive.record(_extension_answer(harvest, run_id, drive.session)), 0)
    code, out = drive.cli(["write", "--run-dir", drive.run_dir])
    written = code == 0
    if written:
        Drive.expect(drive.cli(["report", "--run-dir", drive.run_dir]), 10)
    facts["_phases"].extend(dict(p, lane=True) for p in drive.phases)
    # the doc's bytes after the drive, read in every branch: a write that stopped is measured too
    after = _read(build["path"]) if build and os.path.isfile(build["path"]) else None
    names = step["pending"]
    if "extended_in_place" in names:
        facts["extended_in_place"] = bool(written and build and out.get("action") == "extended"
                                          and out.get("doc") == build["path"]
                                          and sorted(os.listdir(plans)) == listing)
        via["extended_in_place"] = "cli: blueprint.py write on a scratch copy of the case workspace (exit %d)" % code
    if "protected_lines_identical" in names and before is not None:
        if after is None:
            facts["protected_lines_identical"] = False
        else:
            status_a, stamps_a, tail_a = _status_and_stamps(before)
            status_b, stamps_b, tail_b = _status_and_stamps(after)
            facts["protected_lines_identical"] = (status_b[:len(status_a)] == status_a and stamps_a == stamps_b
                                                  and tail_a == tail_b)
        via["protected_lines_identical"] = ("bytes of the doc before and after the cli write (exit %d), compared "
                                            "here" % code)
    if "importer_reads" in names and written and after is not None:
        facts["importer_reads"] = _importer_reads(workspace, build["path"], after, scratch)
        via["importer_reads"] = "records component CLI: import-legacy --dry-run on a scratch copy (resolver route)"


def _importer_reads(workspace, doc_path, text, scratch):
    sys.path.insert(0, SCRIPTS)
    try:
        from station_core import records_link, records_client
    finally:
        sys.path.pop(0)
    copy = os.path.join(scratch, "importer-copy")
    shutil.copytree(workspace, copy, symlinks=True)
    client = records_link.open_client("blueprint-v2")
    try:
        body = client.import_legacy(copy, os.path.relpath(doc_path, workspace), dry_run=True)
    except records_client.RecordsRefusal:
        return False
    headings = len(re.findall(r"^## Slice \S+ %s " % D, text, re.M))
    return bool(body.get("dry_run") is True and body.get("ambiguous") == 0 and body.get("slices") == headings)


def observe_lane(step, case_dir, neutral, facts, via, scratch):
    pending = set(step.get("pending") or [])
    if pending & {"answer_refused", "refusal_reason"}:
        _record_facts(step, case_dir, neutral, facts, via, os.path.join(scratch, "record"))
    if pending & {"extended_in_place", "protected_lines_identical", "importer_reads"}:
        _write_facts(step, case_dir, neutral, facts, via, os.path.join(scratch, "write"))
