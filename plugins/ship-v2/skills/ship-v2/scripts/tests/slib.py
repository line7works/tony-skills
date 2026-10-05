"""Fixtures for ship-v2's own tests (not a back-frame file): a synthetic build in a git work tree, and a plugins tree.

Every fixture is built under a temporary directory and removed; git runs only there, with a fixed author and date
(`testlib.git`). The build is a made-up bench-rig turn counter.

The plugins tree. ship-v2 resolves the stations it visits beside its own plugin root (route 3a) or in the installed
shape (route 3b), never by a personal path, so a test that needs particular stations runs a COPY of this plugin from
a temporary `plugins/` folder (`make_tree`), beside the stations the test places there:

- a stand-in v2 station (`standin`): its own manifest (the real station's name and version), the real station's
  `references/result.schema.json`, and a `scripts/<station>.py` that answers `skill-identity` and nothing else;
- a planted station (`plant_v1`, `plant_link`): a tripwire whose every executable writes a marker when run and
  whose manifest can be a named pipe, so a resolver that opens or runs it is caught.

A station's result is the real station's own accepted example (`references/examples/`), with its run fields set to
the visit's, written into the visit's run directory as the station itself would write it (`put_result`). The
records log is written through the records component's own CLI, never by hand: `import-legacy` of the build doc's
punch list, or `append` of the events a station writes (`raise_finding`, `fix_finding`).

    Tree(tmp, stations=..., recheck_interface=1) -> .root (the plugins folder), .ship (the copied plugin), .script
    Driver(tree, tmp) -> a callable running the copied CLI with the test hooks on: (exit, document or None, stderr)
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys

import testlib

D = "\u2014"                    # the dash of the v1 forms; carried as an escape, never typed
M = "\u00b7"
DOC = "docs/plans/2026-09-20-turnstile.md"
FEATURE = "turnstile"
NOW = "2026-10-05T12:00:00Z"
TODAY = NOW[:10]
PREFIX = "SHIP_V2"
SCRIPTS = {"build-v2": "build.py", "signoff-v2": "signoff.py", "recheck-v2": "recheck.py"}
STATIONS = ("build-v2", "signoff-v2", "recheck-v2")
MAJOR_AT = "src/turnstile.py:2"

STANDIN = '''import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MARKER = %(marker)r
if MARKER:
    with open(os.path.join(PLUGIN, MARKER), "w") as fh:
        fh.write("ran")
with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
    manifest = json.load(fh)
if sys.argv[1:] != ["skill-identity"]:
    sys.stderr.write("a stand-in station answers skill-identity only\\n")
    sys.exit(2)
out = {"ok": True, "name": %(name)s, "version": manifest["version"], "commit": "unversioned",
       "content_sha256": hashlib.sha256(manifest["name"].encode("utf-8")).hexdigest()}
if %(interface)r is not None:
    out["interface_version"] = %(interface)r
sys.stdout.write(json.dumps(out) + "\\n")
'''


def real_station(name):
    """The real station beside this core in the checkout, or None (the installed shape)."""
    return testlib.checkout_sibling(name)


def stations_present():
    return all(real_station(name) is not None for name in STATIONS)


def slice_lines(name, short, status, footprint="`src/turnstile.py`, `tests/`", depends="nothing"):
    lines = ["## Slice %s %s %s" % (name, D, short), "Goal: one sentence about %s." % short,
             "Requirements:", "- R1 %s the %s counts every turn" % (D, short), "Acceptance criteria:",
             "- AC1: a turn adds one %s verify: new test at tests/test_turnstile.py" % D]
    if footprint is not None:
        lines.append("Footprint: %s" % footprint)
    lines.append("Not in this slice: the encoder")
    if depends is not None:
        lines.append("Depends on: %s" % depends)
    if status is not None:
        lines.append("Status: %s" % status)
    return lines


def review_block(date="2026-09-24", slice_name="A", findings=None):
    findings = findings if findings is not None else [("MAJOR", MAJOR_AT, "the counter skips a turn",
                                                       "a double tap loses one")]
    lines = ["", "### %s %s review: Slice %s" % (date, D, slice_name)]
    for severity, location, claim, scenario in findings:
        lines.append("- %s %s %s %s %s %s %s %s Slice %s review" % (severity, M, location, M, claim, M, scenario, M,
                                                                    slice_name))
    return lines


def build_doc(slices=None, punch=None, footprint="`src/turnstile.py`, `tests/`", raw_slice=None):
    """The build doc's text. `slices`: [(name, short, status)]; `punch`: lines under `## Punch list`; `raw_slice`:
    lines placed as one more slice section, as written (a test's planted shape)."""
    slices = slices if slices is not None else [("A", "the counter", "not started"), ("B", "the spinner",
                                                                                      "not started")]
    lines = ["# Turnstile %s build plan (2026-09-20)" % D, "",
             "Intent: a small turn counter for the bench rig, so one bench session reports its turns.",
             "Constraints: Python 3.9 standard library only; test command `python3 -m unittest`.",
             "Out of scope: a web dashboard %s the owner declined it for the first version" % D]
    for name, short, status in slices:
        lines += [""] + slice_lines(name, short, status, footprint=footprint if name == "A" else
                                    "`src/spinner.py`")
    if raw_slice:
        lines += [""] + list(raw_slice)
    lines += ["", "## Build assumptions", "- the bench clock is monotonic", "## Deviations", "## Discovered",
              "## Handoffs", "## Punch list"] + list(punch or [])
    return "\n".join(lines) + "\n"


BASE_FILES = {"README.md": "# Turnstile\n\nA bench-rig turn counter.\n",
              "src/turnstile.py": "def spin(count):\n    return count\n",
              "src/spinner.py": "def twice(count):\n    return count\n"}


def make_repo(tmp, doc_text=None, records=False, name="workspace"):
    ws = testlib.git_workspace(tmp, name, dict(BASE_FILES))
    testlib.git(ws, ["checkout", "-q", "-b", "feat"])
    files = {"src/turnstile.py": "def spin(count):\n    return count + 1\n",
             DOC: doc_text if doc_text is not None else build_doc()}
    for rel, text in sorted(files.items()):
        testlib.write_text(os.path.join(ws, rel), text)
    testlib.git(ws, ["add", "-A"])
    testlib.git(ws, ["commit", "-q", "-m", "the build"], when="2026-09-20T10:00:00-07:00")
    if records:
        import_log(ws)
        commit_all(ws, "the records log")
    return ws


def commit_all(ws, subject="a commit"):
    testlib.git(ws, ["add", "-A"])
    testlib.git(ws, ["commit", "-q", "--allow-empty", "-m", subject], when="2026-09-20T11:00:00-07:00")


# ---- the plugins tree ------------------------------------------------------------------------------

class Tree(object):
    """A `plugins/` folder under `tmp` holding a copy of this plugin and the stations a test names."""

    def __init__(self, tmp, stations=STATIONS, recheck_interface=1, name="tree"):
        self.root = os.path.join(tmp, name, "plugins")
        os.makedirs(self.root)
        self.ship = os.path.join(self.root, "ship-v2")
        shutil.copytree(testlib.PLUGIN, self.ship, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.skill = os.path.join(self.ship, "skills", "ship-v2")
        self.script = os.path.join(self.skill, "scripts", "ship.py")
        for station in stations:
            standin(self.root, station, interface=recheck_interface if station == "recheck-v2" else 1)


def standin(parent, name, interface=1, folder=None, manifest_name=None, marker=None, identity_name=None):
    """A stand-in v2 station under `parent/<folder or name>`; returns its root."""
    root = os.path.join(parent, folder or name)
    real = real_station(name)
    version = testlib.load_json(os.path.join(real, ".claude-plugin", "plugin.json"))["version"] if real else "0.1.0"
    testlib.write_json(os.path.join(root, ".claude-plugin", "plugin.json"),
                       {"name": manifest_name or name, "version": version})
    skill = os.path.join(root, "skills", name)
    testlib.write_text(os.path.join(skill, "SKILL.md"), "---\nname: %s\ndescription: a stand-in station.\n---\n"
                       "# A stand-in\n" % name)
    if real is not None:
        os.makedirs(os.path.join(skill, "references"))
        shutil.copyfile(os.path.join(real, "skills", name, "references", "result.schema.json"),
                        os.path.join(skill, "references", "result.schema.json"))
    testlib.write_text(os.path.join(skill, "scripts", SCRIPTS[name]), STANDIN % {
        "marker": marker, "name": "manifest[\"name\"]" if identity_name is None else repr(identity_name),
        "interface": interface})
    return root


def plant_v1(parent, v1_name, as_name):
    """A v1-shaped station at `parent/<v1_name>`: its manifest a named pipe (an open blocks), its script a tripwire.
    Returns its root."""
    root = os.path.join(parent, v1_name)
    os.makedirs(os.path.join(root, ".claude-plugin"))
    os.mkfifo(os.path.join(root, ".claude-plugin", "plugin.json"))
    testlib.write_text(os.path.join(root, "skills", as_name, "scripts", SCRIPTS[as_name]),
                       "import os\nopen(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'V1_RAN'), 'w')"
                       ".write('ran')\nprint('{}')\n")
    return root


def ran(root, name):
    return os.path.exists(os.path.join(root, "skills", name, "scripts", "V1_RAN"))


# ---- the driver ------------------------------------------------------------------------------------

def env(extra=None):
    out = {PREFIX + "_TEST": "1", PREFIX + "_TEST_NOW": NOW}
    root = testlib.records_root()
    if root is not None:
        out["RECORDS_ROOT"] = root
    out.update(extra or {})
    return testlib.base_env(out)


class Driver(object):
    """The CLI of `tree`'s copy of this plugin (or of this checkout when `tree` is None), with the test hooks on."""

    def __init__(self, tree, tmp, extra_env=None):
        self.script = tree.script if tree is not None else testlib.DRIVER
        self.tmp = tmp
        self.env = env(extra_env)
        self.calls = []

    def __call__(self, args):
        proc = subprocess.run([sys.executable, self.script] + [str(a) for a in args], cwd=self.tmp, env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace")
        try:
            doc = json.loads(out) if out.strip() else None
        except ValueError:
            doc = None
        self.calls.append((list(args), proc.returncode))
        return proc.returncode, doc, proc.stderr.decode("utf-8", "replace")


def make_input(ws, run_dir, run_id="run", harness="claude-code", report_only=False, **station):
    doc = testlib.make_input(ws, run_dir)
    doc["run_id"] = run_id
    doc["invocation"]["harness"] = harness
    doc["station"] = dict(station)
    if report_only:
        doc["report_only"] = True
    return doc


def start(test, tree, tmp, ws, run="run", harness="claude-code", report_only=False, **station):
    """check-input for a fresh run; returns (driver, run_dir)."""
    station.setdefault("slice", "A")
    station = dict((key, value) for key, value in station.items() if value is not None)
    run_dir = os.path.join(tmp, run)
    doc = make_input(ws, run_dir, run_id=run, harness=harness, report_only=report_only, **station)
    path = os.path.join(tmp, run + "-input.json")
    testlib.write_json(path, doc)
    drive = Driver(tree, tmp)
    code, out, err = drive(["check-input", path])
    test.assertEqual(code, 0, (out, err))
    return drive, run_dir


def hook_file(tmp, harness="claude-code", armed=False, name="hook.json"):
    path = os.path.join(tmp, name)
    testlib.write_json(path, {"answer_version": 1, "kind": "hook", "harness": harness, "armed": armed,
                              "how": "a test reading", "evidence": None})
    return path


def through_hook(test, drive, tmp, run_dir, doc=DOC, armed=False, harness="claude-code"):
    code, out, err = drive(["select", "--run-dir", run_dir, "--doc", doc])
    test.assertEqual(code, 0, (out, err))
    code, out, err = drive(["hook", "--run-dir", run_dir, "--reading", hook_file(tmp, harness, armed)])
    test.assertEqual(code, 0, (out, err))
    return out


# ---- the stations' results -------------------------------------------------------------------------

EXAMPLES = {
    ("build-v2", "completed"): "result/valid/completed-card-moved.json",
    ("build-v2", "partial"): "result/valid/not-complete.json",
    ("build-v2", "checks"): "result/valid/checks-not-passed.json",
    ("build-v2", "stopped"): "result/valid/stopped-open-blocker.json",
    ("build-v2", "report-only"): "result/valid/report-only.json",
    ("signoff-v2", "clean"): "result-clean.json",
    ("signoff-v2", "findings"): "result-completed.json",
    ("signoff-v2", "stopped"): "result-stopped-independence.json",
    ("signoff-v2", "stale"): "result-stale-source-moved.json",
    ("signoff-v2", "report-only"): "result-report-only.json",
    ("recheck-v2", "all_clear"): "result-completed.json",
    ("recheck-v2", "partial"): "result-completed.json",
    ("recheck-v2", "not_clear"): "result-completed.json",
    ("recheck-v2", "nothing_open"): "result-nothing-open.json",
    ("recheck-v2", "stopped"): "result-stopped.json",
}


def example(station, which):
    real = real_station(station)
    return testlib.load_json(os.path.join(real, "skills", station, "references", "examples", EXAMPLES[(station, which)]))


def station_result(station, which, visit, ws, doc=DOC, slice_name="A"):
    """The real station's accepted example `which`, its run fields set to the visit's (`visit` is visit's output)."""
    out = copy.deepcopy(example(station, which))
    run_id, run_dir = visit["visit_run_id"], visit["visit_run_dir"]
    if "plugin_version" in out:
        out["plugin_version"] = testlib.load_json(os.path.join(real_station(station), ".claude-plugin",
                                                               "plugin.json"))["version"]
    if station == "build-v2":
        out.update(run_id=run_id, run_dir=run_dir, workspace=ws, build_doc=doc, slice=slice_name)
    elif station == "signoff-v2":
        out["run"].update(run_id=run_id, run_dir=run_dir, workspace=ws, build_doc=doc, slice=slice_name)
    else:
        out["run"].update(run_id=run_id, run_dir=run_dir)
        if which in ("all_clear", "partial", "not_clear"):
            out["result"] = which
            keep = {"all_clear": ("fixed",), "not_clear": ("not_fixed",)}.get(which)
            if keep is not None:
                out["items"] = [item for item in out["items"] if item["disposition"] in keep]
                out["checklist"]["count"] = len(out["items"])
            if which == "all_clear":
                out["still_open"] = []
    return out


def put_result(visit, doc):
    path = os.path.join(visit["visit_run_dir"], "result.json")
    testlib.write_json(path, doc)
    return path


def visit(test, drive, run_dir, station, which, ws, before_result=None):
    """One visit: `visit --station`, the station's result written as the station would, `visit --result`."""
    code, out, err = drive(["visit", "--run-dir", run_dir, "--station", station])
    test.assertEqual(code, 0, (station, out, err))
    if before_result is not None:
        before_result(out)
    put_result(out, station_result(station, which, out, ws))
    return drive(["visit", "--run-dir", run_dir, "--result"])


# ---- the records component, through its CLI -------------------------------------------------------

def records_cli(ws, args, check=True):
    root = testlib.records_root()
    proc = subprocess.run([sys.executable, os.path.join(root, "scripts", "records.py")] + args,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ws, env=testlib.base_env())
    if check and proc.returncode != 0:
        raise RuntimeError("records %s exited %d: %s %s" % (args[0], proc.returncode, proc.stdout.decode()[-600:],
                                                            proc.stderr.decode()[-600:]))
    return json.loads(proc.stdout.decode()) if proc.stdout.strip() else None


def import_log(ws, doc=DOC):
    return records_cli(ws, ["import-legacy", "--workspace", ws, "--doc", doc])


def state(ws, doc=DOC, slice_name=None):
    args = ["state", "--workspace", ws, "--doc", doc] + (["--slice", slice_name] if slice_name else [])
    return records_cli(ws, args)


def head(ws, doc=DOC):
    return records_cli(ws, ["verify", "--workspace", ws, "--doc", doc])["head"]


def identity(ws):
    return records_cli(ws, ["identity", "--workspace", ws])["identity"]


def append(tmp, ws, events, doc=DOC):
    path = os.path.join(tmp, "events-%d.json" % len(os.listdir(tmp)))
    testlib.write_json(path, events)
    return records_cli(ws, ["append", "--workspace", ws, "--doc", doc, "--events", path, "--expect-head",
                            head(ws, doc)])


def _base(station, run_id, ws, doc=DOC):
    return {"v": 1, "at": NOW, "ledger_doc": doc, "actor": {"station": station, "run_id": run_id,
                                                            "harness": "claude-code"},
            "origin": {"kind": "native"}, "source": {"known": True, "identity": identity(ws)}}


def raise_finding(tmp, ws, severity="MAJOR", location=MAJOR_AT, claim="the counter skips a turn",
                  card=("built", "signed off with conditions"), slice_name="A", run_id="signoff-run", doc=DOC):
    """What signoff-v2 writes for one raised finding: a `finding_raised` and the card it sets (its contract)."""
    path, line = location.split(":")
    raised = dict(_base("signoff-v2", run_id, ws, doc), kind="finding_raised", slice=slice_name, severity=severity,
                  location={"raw": location, "file": path, "line": int(line), "line_end": None, "tag": None,
                            "more": [], "resolved": True},
                  claim=claim, scenario="a double tap loses one", raised_by="Slice %s review" % slice_name)
    events = [raised]
    if card is not None:
        events.append(dict(_base("signoff-v2", run_id, ws, doc), kind="card_set", slice=slice_name, before=card[0],
                           after=card[1]))
    append(tmp, ws, events, doc)
    return finding_id(ws, location, doc)


def finding_id(ws, location=MAJOR_AT, doc=DOC):
    return next(f["id"] for f in state(ws, doc)["findings"] if f["location"]["raw"] == location)


def fix_finding(tmp, ws, finding, card=("signed off with conditions", "signed off"), slice_name="A",
                run_id="recheck-run", doc=DOC):
    """What recheck-v2 writes for one fixed finding: a `disposition` fixed and the card it sets."""
    ident = identity(ws)
    events = [dict(_base("recheck-v2", run_id, ws, doc), kind="disposition", finding=finding, disposition="fixed",
                   how="the case re-ran and held", verified_source={"known": True, "identity": ident},
                   join_basis=None)]
    if card is not None:
        events.append(dict(_base("recheck-v2", run_id, ws, doc), kind="card_set", slice=slice_name, before=card[0],
                           after=card[1]))
    append(tmp, ws, events, doc)


def set_status(ws, slice_name, value, doc=DOC):
    """The slice's `Status:` line set to `value`, as the station that moved the card writes it."""
    path = os.path.join(ws, doc)
    text = testlib.read_text(path)
    lines = text.split("\n")
    at = next(i for i, l in enumerate(lines) if l.startswith("## Slice %s " % slice_name))
    for index in range(at + 1, len(lines)):
        if lines[index].startswith("Status: "):
            lines[index] = "Status: %s" % value
            break
    testlib.write_text(path, "\n".join(lines))


def log_lines(ws, doc=DOC):
    slug = doc[:-3].replace("%", "%25").replace("_", "%5F").replace("/", "__")
    path = os.path.join(ws, "docs", "records", slug + ".events.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def jsonschema_here():
    testlib.add_scripts_to_path()
    from station_core import validate
    return not validate.jsonschema_unavailable("SLIB")


def usable():
    """The suite's preconditions: jsonschema, the records component and the three stations beside this core."""
    return jsonschema_here() and testlib.records_root() is not None and stations_present()


# ---- the executor's files --------------------------------------------------------------------------

def fixes_file(tmp, run_dir, lap, fixes=(), spec_change=(), name=None):
    path = os.path.join(tmp, name or "fixes-%d.json" % lap)
    testlib.write_json(path, {"answer_version": 1, "kind": "fixes", "run_id": os.path.basename(run_dir), "lap": lap,
                              "fixes": [dict(f) for f in fixes], "spec_change": [dict(s) for s in spec_change]})
    return path


def question_file(tmp, run_dir, text, source="station", station="signoff-v2", finding=None, name="question.json"):
    path = os.path.join(tmp, name)
    testlib.write_json(path, {"answer_version": 1, "kind": "question", "run_id": os.path.basename(run_dir),
                              "source": source, "station": station, "text": text, "finding": finding})
    return path


def answer_file(tmp, run_dir, pause, words, effect=None, name="answer.json"):
    path = os.path.join(tmp, name)
    testlib.write_json(path, {"answer_version": 1, "kind": "answer", "run_id": os.path.basename(run_dir),
                              "pause": pause, "words": words, "effect": effect or {"kind": "resume"}})
    return path


def report(drive, run_dir, bottom="The slice went through the loop. Read the block."):
    return drive(["report", "--run-dir", run_dir, "--bottom-line", bottom])


def sha(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def snapshot(ws):
    """What a write outside the run directory would move: every file of the work tree (the log and the doc
    included) and the git HEAD."""
    return {"tree": testlib.tree_digest(ws), "head": testlib.git(ws, ["rev-parse", "HEAD"]).strip()}


def trace(run_dir):
    path = os.path.join(run_dir, "trace.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def validate_trace(run_dir):
    """The frame's shared validator over the run's trace: (exit, document)."""
    proc = subprocess.run([sys.executable, os.path.join(testlib.SCRIPTS, "validate-trace.py"),
                           os.path.join(run_dir, "trace.jsonl")], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=testlib.base_env())
    return proc.returncode, (json.loads(proc.stdout.decode()) if proc.stdout.strip() else None)
