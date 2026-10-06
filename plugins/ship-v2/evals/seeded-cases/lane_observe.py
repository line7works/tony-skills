"""ship-v2's own observer of its facts (not a back-frame file; the E14 seam `observe.py` calls).

    observe_lane(step, case_dir, neutral, facts, via, scratch)

`observe.py` (precon-v2's, byte for byte) calls this for every `lane` step of a case of this core. ship-v2 resolves
the stations it visits beside its own plugin root, so the observer runs a COPY of this plugin from a plugins folder
under `scratch` (the checkout or installed shape alike), beside a stand-in for each station: the real station's own
manifest, a `SKILL.md` (the file ship-v2 hands the executor, held inside the root, C2-5) and result schema (found the
way ship-v2 finds the real one, `ship_core/stations.py`, route 3a or 3b) and a script that answers `skill-identity` with interface version 1 and nothing else; or, where the case plants one, a
v1-shaped station (a link into a v1-named folder, a manifest naming a v1 station, an identity naming one, no
interface version), whose every executable leaves a marker when run.

It then plays the case's recorded answer (`answer.json`'s `script`, what the executor does, in order) through the
REAL phase driver (the copy's `scripts/ship.py`, as a subprocess): `check-input`, `select --doc`, `hook`, then each
action: `visit` (the station's own result, the real station's accepted example with its run fields set to the
visit's, written into the visit's run directory as the station writes it, together with the records events and the
`Status:` line that station writes for it, through the records component's own CLI), `fix`, `lap`, `pause` (a
question), `answer` (the owner's answer), `report`. It fills, from what the driver did and what the run directory
and the workspace hold after it, exactly the names the step lists under `pending` that it has a fact for (`via` is
`cli`); a name it has no fact for is left out, so `observe.py` keeps it under `_lane_pending`. Nothing is read from
the answer file as an outcome. Standard library only; the driver needs jsonschema (run under uv).
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(PLUGIN, "skills", "ship-v2", "scripts")
DOC = "docs/plans/2026-09-20-turnstile.md"
NOW = "2026-10-05T12:00:00Z"
STATIONS = ("build-v2", "signoff-v2", "recheck-v2")
SCRIPT = {"build-v2": "build.py", "signoff-v2": "signoff.py", "recheck-v2": "recheck.py"}
MAJOR_AT = "src/turnstile.py:2"
EXAMPLES = {
    ("build-v2", "completed"): "result/valid/completed-card-moved.json",
    ("build-v2", "partial"): "result/valid/not-complete.json",
    ("signoff-v2", "clean"): "result-clean.json",
    ("signoff-v2", "findings"): "result-completed.json",
    ("recheck-v2", "all_clear"): "result-completed.json",
    ("recheck-v2", "not_clear"): "result-completed.json",
}
STANDIN = '''import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if %(marker)r:
    open(os.path.join(PLUGIN, %(marker)r), "w").write("ran")
manifest = json.load(open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8"))
if sys.argv[1:] != ["skill-identity"]:
    sys.exit(2)
out = {"ok": True, "name": %(name)s, "version": manifest["version"], "commit": "unversioned",
       "content_sha256": hashlib.sha256(manifest["name"].encode("utf-8")).hexdigest()}
if %(interface)r is not None:
    out["interface_version"] = %(interface)r
print(json.dumps(out))
'''
V1 = ("bu" + "ild",)            # the v1 build station's name, assembled, never typed whole


def _write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
    return path


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _real(name):
    """The real station's root, found the way ship-v2 finds it (allowlist identity, route 3a then 3b)."""
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    from ship_core import stations
    return stations.resolve(name)["root"]


def _records_root():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    from station_core import records_client
    return records_client.records_root(None, records_client.station_plugin_root(), {})


def _standin(parent, name, folder=None, manifest_name=None, identity_name=None, interface=1, marker=None):
    root = os.path.join(parent, folder or name)
    real = _real(name)
    version = _load(os.path.join(real, ".claude-plugin", "plugin.json"))["version"]
    _write(os.path.join(root, ".claude-plugin", "plugin.json"), {"name": manifest_name or name, "version": version})
    refs = os.path.join(root, "skills", name, "references")
    os.makedirs(refs)
    with open(os.path.join(root, "skills", name, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nname: %s\ndescription: a stand-in station.\n---\n# A stand-in\n" % name)
    shutil.copyfile(os.path.join(real, "skills", name, "references", "result.schema.json"),
                    os.path.join(refs, "result.schema.json"))
    script = os.path.join(root, "skills", name, "scripts", SCRIPT[name])
    os.makedirs(os.path.dirname(script))
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(STANDIN % {"marker": marker, "interface": interface,
                            "name": "manifest[\"name\"]" if identity_name is None else repr(identity_name)})
    return root


def _tree(scratch, plant):
    plugins = os.path.join(scratch, "tree", "plugins")
    os.makedirs(plugins)
    ship = os.path.join(plugins, "ship-v2")
    shutil.copytree(PLUGIN, ship, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    plant = plant or {}
    for name in STATIONS:
        if plant.get("station") != name:
            _standin(plugins, name)
            continue
        shape = plant["shape"]
        if shape == "link-to-v1":
            v1 = _standin(plugins, name, folder=V1[0], marker="V1_RAN")
            os.symlink(v1, os.path.join(plugins, name))
        elif shape == "manifest-v1":
            _standin(plugins, name, manifest_name=V1[0], marker="V1_RAN")
        elif shape == "identity-v1":
            _standin(plugins, name, identity_name=V1[0])
        elif shape == "no-interface":
            _standin(plugins, name, interface=None)
    return plugins, os.path.join(ship, "skills", "ship-v2", "scripts", "ship.py")


class _Driver(object):

    def __init__(self, script, scratch, facts, records_root):
        self.script, self.scratch, self.facts = script, scratch, facts
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SHIP_V2_TEST="1", SHIP_V2_TEST_NOW=NOW,
                        RECORDS_ROOT=records_root)

    def __call__(self, args):
        proc = subprocess.run([sys.executable, self.script] + [str(a) for a in args], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=self.scratch, env=self.env)
        out = proc.stdout.decode("utf-8", "replace")
        self.facts.setdefault("_phases", []).append({"phase": str(args[0]), "exit": proc.returncode, "via": "lane"})
        try:
            doc = json.loads(out) if out.strip() else None
        except ValueError:
            doc = None
        return proc.returncode, doc


class _Records(object):
    """The records component through its own CLI: what a station writes for its result."""

    def __init__(self, root, ws, scratch):
        self.root, self.ws, self.scratch, self.count = root, ws, scratch, 0

    def cli(self, args):
        proc = subprocess.run([sys.executable, os.path.join(self.root, "scripts", "records.py")] + args,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.ws,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if proc.returncode != 0:
            raise RuntimeError("records %s exited %d: %s" % (args[0], proc.returncode, proc.stderr.decode()[-300:]))
        return json.loads(proc.stdout.decode())

    def base(self, station):
        ident = self.cli(["identity", "--workspace", self.ws])["identity"]
        return {"v": 1, "at": NOW, "ledger_doc": DOC, "actor": {"station": station, "run_id": station + "-seeded",
                                                                "harness": "seeded-case"},
                "origin": {"kind": "native"}, "source": {"known": True, "identity": ident}}

    def append(self, events):
        self.count += 1
        path = _write(os.path.join(self.scratch, "events-%d.json" % self.count), events)
        head = self.cli(["verify", "--workspace", self.ws, "--doc", DOC])["head"]
        self.cli(["append", "--workspace", self.ws, "--doc", DOC, "--events", path, "--expect-head", head])

    def findings(self):
        return self.cli(["state", "--workspace", self.ws, "--doc", DOC])["findings"]

    def status(self, value):
        path = os.path.join(self.ws, DOC)
        with open(path, encoding="utf-8", newline="") as fh:
            lines = fh.read().split("\n")
        start = next(i for i, l in enumerate(lines) if l.startswith("## Slice A "))
        for index in range(start + 1, len(lines)):
            if lines[index].startswith("Status: "):
                lines[index] = "Status: " + value
                break
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(lines))

    def card(self, station, before, after):
        self.append([dict(self.base(station), kind="card_set", slice="A", before=before, after=after)])
        self.status(after)

    def write(self, what):
        """The records events and the `Status:` line a station writes for the result it returns."""
        if what == "card-built":
            self.card("build-v2", "not started", "built")
        elif what == "raise-major":
            path, line = MAJOR_AT.split(":")
            self.append([dict(self.base("signoff-v2"), kind="finding_raised", slice="A", severity="MAJOR",
                              location={"raw": MAJOR_AT, "file": path, "line": int(line), "line_end": None,
                                        "tag": None, "more": [], "resolved": True},
                              claim="the counter skips a turn", scenario="a double tap loses one",
                              raised_by="Slice A review")])
            self.card("signoff-v2", "built", "signed off with conditions")
        elif what in ("fixed", "not-fixed"):
            ident = self.cli(["identity", "--workspace", self.ws])["identity"]
            finding = next(f["id"] for f in self.findings() if f["location"]["raw"] == MAJOR_AT)
            self.append([dict(self.base("recheck-v2"), kind="disposition", finding=finding,
                              disposition="fixed" if what == "fixed" else "not_fixed", how="the case re-ran",
                              verified_source={"known": True, "identity": ident}, join_basis=None)])
            if what == "fixed":
                self.card("recheck-v2", "signed off with conditions", "signed off")

    def finding_at(self, location):
        return next((f["id"] for f in self.findings() if f["location"]["raw"] == location), "f1:" + "0" * 20)


def _sha(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _result(name, which, visit, ws, writes=None):
    """The real station's accepted example, its run fields set to the visit's. recheck-v2's slice, doc, name and
    version are its `checklist` and `run.skill` (C2-4), and its `records_written` lists the project files this visit's
    station wrote (`writes`), its run artifacts moved to the visit's run directory (C2-1)."""
    real = _real(name)
    if which == "v1-text":
        return {"status": "COMPLETE", "station": V1[0], "report": "BUILD: A"}
    out = copy.deepcopy(_load(os.path.join(real, "skills", name, "references", "examples", EXAMPLES[(name, which)])))
    run_id, run_dir = visit["visit_run_id"], visit["visit_run_dir"]
    if "plugin_version" in out:
        out["plugin_version"] = _load(os.path.join(real, ".claude-plugin", "plugin.json"))["version"]
    if name == "build-v2":
        out.update(run_id=run_id, run_dir=run_dir, workspace=ws, build_doc=DOC, slice="A")
    elif name == "signoff-v2":
        out["run"].update(run_id=run_id, run_dir=run_dir, workspace=ws, build_doc=DOC, slice="A")
    else:
        out["run"].update(run_id=run_id, run_dir=run_dir)
        version = _load(os.path.join(real, ".claude-plugin", "plugin.json"))["version"]
        out["run"]["skill"].update(name=name, version=version)
        out["checklist"].update(build_doc=DOC, slice="A")
        out["records_written"] = [dict(r, path=os.path.join(run_dir, os.path.basename(r["path"])))
                                  for r in out.get("records_written") or [] if r.get("kind") == "run_artifact"]
        out["records_written"] += list(writes or [])
        out["result"] = which
        keep = ("fixed",) if which == "all_clear" else ("not_fixed",)
        out["items"] = [i for i in out["items"] if i["disposition"] in keep]
        out["checklist"]["count"] = len(out["items"])
        if which == "all_clear":
            out["still_open"] = []
    return out


def _digest(root):
    entries = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            full = os.path.join(base, name)
            with open(full, "rb") as fh:
                entries.append("%s\0%s" % (os.path.relpath(full, root), hashlib.sha256(fh.read()).hexdigest()))
    return hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()


def _trace(run_dir):
    path = os.path.join(run_dir, "trace.jsonl")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def observe_lane(step, case_dir, neutral, facts, via, scratch):
    pending = set(step.get("pending") or [])
    if not pending:
        return
    found = {}

    def fill(name, value):
        if name in pending:
            found[name] = value

    answer = _load(os.path.join(case_dir, neutral["answer"])) if neutral.get("answer") else {}
    plugins, script = _tree(scratch, step.get("plant"))
    ws = neutral["workspace"]
    records_root = _records_root()
    records = _Records(records_root, ws, scratch)
    run = _Driver(script, scratch, facts, records_root)
    run_dir = os.path.join(scratch, "run")
    run_id = neutral["case"].replace("_", "-")
    doc = {"input_version": 1, "run_id": run_id, "workspace": ws, "run_dir": run_dir,
           "report_only": bool(neutral.get("report_only")),
           "invocation": {"harness": "claude-code", "caller": "user", "mode": "direct", "session_id": "seeded-session"},
           "station": dict(neutral.get("station") or {"slice": "A"})}
    code, out = run(["check-input", _write(os.path.join(scratch, "input.json"), doc)])
    if code != 0:
        return _finish(found, facts, via)
    code, out = run(["select", "--run-dir", run_dir, "--doc", DOC])
    if code != 0:
        return _finish(found, facts, via)
    code, out = run(["hook", "--run-dir", run_dir, "--reading", _write(os.path.join(scratch, "hook.json"), {
        "answer_version": 1, "kind": "hook", "harness": "claude-code", "armed": False, "how": "a seeded reading",
        "evidence": None})])
    exits = {"visit_open": [], "visit_result": [], "lap": [], "fix": [], "report_while_paused": None, "pause": []}
    before_log = len(records.cli(["events", "--workspace", ws, "--doc", DOC]).get("results") or [])
    workspace_before = None
    ended = None
    for number, action in enumerate(answer.get("script") or [], 1):
        kind = action["do"]
        if kind == "visit":
            code, visit = run(["visit", "--run-dir", run_dir, "--station", action["station"]])
            exits["visit_open"].append(code)
            if code != 0 or visit.get("next") != "visit --result":
                continue
            if action.get("question"):
                workspace_before = _digest(ws)
                code, asked = run(["pause", "--run-dir", run_dir, "--question", _write(
                    os.path.join(scratch, "question-%d.json" % number), {
                        "answer_version": 1, "kind": "question", "run_id": run_id, "source": "station",
                        "station": action["station"], "text": action["question"], "finding": None})])
                exits["pause"].append(code)
                code, out = run(["report", "--run-dir", run_dir, "--bottom-line", "The owner has not answered."])
                exits["report_while_paused"] = code
                if not action.get("answered"):
                    ended = "paused"
                    break
                code, out = run(["pause", "--run-dir", run_dir, "--answer", _write(
                    os.path.join(scratch, "answer-%d.json" % number), {
                        "answer_version": 1, "kind": "answer", "run_id": run_id, "pause": asked["pause"],
                        "words": action["answered"], "effect": {"kind": "resume"}})])
            doc_before = _sha(os.path.join(ws, DOC))
            if action.get("writes"):
                records.write(action["writes"])
            doc_after = _sha(os.path.join(ws, DOC))
            writes = [] if doc_after == doc_before else [{"kind": "status_line", "path": DOC, "appended": False,
                                                          "sha256_before": doc_before, "sha256_after": doc_after}]
            _write(os.path.join(visit["visit_run_dir"], "result.json"),
                   _result(action["station"], action["result"], visit, ws, writes))
            code, out = run(["visit", "--run-dir", run_dir, "--result"])
            exits["visit_result"].append(code)
            if code != 0:
                ended = "visit-result-refused"
                break
        elif kind == "fix":
            for rel, text in sorted((action.get("touch") or {}).items()):
                path = os.path.join(ws, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
            fixes = [dict(f, finding=records.finding_at(f["finding_at"])) for f in action.get("fixes") or []]
            for fix in fixes:
                del fix["finding_at"]
            specs = [dict(s, finding=records.finding_at(s.pop("finding_at"))) if "finding_at" in s else s
                     for s in copy.deepcopy(action.get("spec_change") or [])]
            code, out = run(["fix", "--run-dir", run_dir, "--fixes", _write(
                os.path.join(scratch, "fixes-%d.json" % number), {"answer_version": 1, "kind": "fixes",
                                                                  "run_id": run_id, "lap": action["lap"],
                                                                  "fixes": fixes, "spec_change": specs})])
            exits["fix"].append(code)
        elif kind == "lap":
            code, out = run(["lap", "--run-dir", run_dir])
            exits["lap"].append(code)
        elif kind == "waive":
            code, asked = run(["pause", "--run-dir", run_dir, "--question", _write(
                os.path.join(scratch, "question-%d.json" % number), {
                    "answer_version": 1, "kind": "question", "run_id": run_id, "source": "ship", "station": None,
                    "text": action["question"], "finding": records.finding_at(action["finding_at"])})])
            exits["pause"].append(code)
            code, out = run(["pause", "--run-dir", run_dir, "--answer", _write(
                os.path.join(scratch, "answer-%d.json" % number), {
                    "answer_version": 1, "kind": "answer", "run_id": run_id, "pause": asked["pause"],
                    "words": action["words"], "effect": {"kind": "waive",
                                                         "finding": records.finding_at(action["finding_at"])}})])
        elif kind == "report":
            code, out = run(["report", "--run-dir", run_dir, "--bottom-line", "The loop ran. The block says where."])
            if code == 10 and out:
                ended = "reported"
                fill("terminal_status", out.get("status"))
                fill("stop_tag", out.get("stop_tag"))
                fill("result_line", out["station_result"]["result_line"])
                fill("laps_taken", out["station_result"]["laps"]["taken"])
                fill("owner_words_recorded", [l["owner_words"] for l in out["station_result"]["laps"]["opened"]
                                              if l["owner_words"]])
    lines = _trace(run_dir)
    fill("trace_lines", ["%s %s %s" % (l["kind"], l["expected"], l.get("status") or "-") for l in lines])
    fill("refused_rules", sorted(set(r for l in lines if l["kind"] == "refused" for r in l["refusal"]["rules"])))
    fill("visit_open_exits", exits["visit_open"])
    fill("visit_result_exits", exits["visit_result"])
    fill("lap_exits", exits["lap"])
    fill("fix_exits", exits["fix"])
    fill("report_while_paused_exit", exits["report_while_paused"])
    fill("run_ended", ended or "open")
    fill("v1_station_ran", any(os.path.exists(os.path.join(base, n)) for base, d, files in os.walk(plugins)
                               for n in files if n == "V1_RAN"))
    events = records.cli(["events", "--workspace", ws, "--doc", DOC]).get("results") or []
    mine = [r["event"] for r in events[before_log:] if r["event"]["actor"]["station"] == "ship-v2"]
    fill("ship_events", [e["kind"] for e in mine])
    fill("ship_event_words", [e.get("words") for e in mine])
    if workspace_before is not None:
        fill("workspace_unchanged_while_paused", _digest(ws) == workspace_before)
    state_path = os.path.join(run_dir, "checkpoint.json")
    if os.path.isfile(state_path):
        fill("stage", _load(state_path).get("phase"))
    return _finish(found, facts, via)


def _finish(found, facts, via):
    for name, value in found.items():
        facts[name] = value
        if name not in via:
            via[name] = "cli"
