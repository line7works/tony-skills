"""Shared paths, fixtures, and helpers for the records component's tests (stdlib only).

Every path derives from this file's location, so the suite runs from any working directory:

    PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s <this directory> -v
    uv run --with jsonschema==4.25.1 python3 -m unittest discover -s <this directory> -v

Fixtures are built into a temporary directory under RECORDS_TEST_SCRATCH when that variable
names a directory, else under the system temporary directory; never into the worktree. Every
test that builds cleans up what it built, and every subprocess runs with
PYTHONDONTWRITEBYTECODE=1 so no `__pycache__` is left anywhere.

The git fixtures here are built by the tests themselves: a fresh repository with one commit,
under the same clean configuration the identity helper uses, so nothing in the machine's git
configuration can change what a test observes.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(TESTS)
ROOT = os.path.dirname(SCRIPTS)
REFERENCES = os.path.join(ROOT, "references")
CLI = os.path.join(SCRIPTS, "records.py")
EXAMPLES_CLI = os.path.join(SCRIPTS, "validate-examples.py")
FLOOR_PYTHON = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"
ZERO = "0" * 64
DOC = "docs/plans/2026-04-01-widget.md"

GIT_ENV = {
    "PATH": os.environ.get("PATH", ""),
    "HOME": os.environ.get("HOME", "/"),
    "LANG": "C",
    "LC_ALL": "C",
    "TZ": "UTC",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "Fixture Author",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "Fixture Author",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_AUTHOR_DATE": "2026-04-01T09:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-04-01T09:00:00+00:00",
}


def add_scripts_to_path():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)


def scratch_base():
    base = os.environ.get("RECORDS_TEST_SCRATCH")
    if base and os.path.isdir(base):
        return base
    return tempfile.gettempdir()


def make_scratch(prefix="records-test-"):
    return tempfile.mkdtemp(prefix=prefix, dir=scratch_base())


def rmtree(path):
    shutil.rmtree(path, ignore_errors=True)


def git(cwd, *args):
    proc = subprocess.run(["git"] + list(args), cwd=cwd, env=GIT_ENV,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("git %s failed in %s: %s" % (" ".join(args), cwd,
                                                        proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8", "replace")


def write(path, text):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def make_workspace(parent=None, doc=DOC):
    """A git work tree root with one commit holding a ledger document. Returns its path."""
    workspace = make_scratch("records-ws-") if parent is None else os.path.join(parent, "workspace")
    if not os.path.isdir(workspace):
        os.makedirs(workspace)
    write(os.path.join(workspace, *doc.split("/")),
          "# Widget\n\n## Slice A - the retry loop\n\nStatus: built\n\n## Punch list\n")
    write(os.path.join(workspace, "src", "widget.py"), "def widget():\n    return 1\n")
    git(workspace, "init", "-q", ".")
    git(workspace, "add", "-A")
    git(workspace, "commit", "-qm", "the widget")
    return workspace


def env_for_child(extra=None):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        env.update(extra)
    return env


def run_cli(args, cwd=None, env=None, python=None, script=None):
    """Run the CLI; return (exit code, stdout, stderr). The default cwd is deliberately elsewhere."""
    cmd = [python or FLOOR_PYTHON, script or CLI] + [str(a) for a in args]
    proc = subprocess.run(cmd, cwd=cwd or tempfile.gettempdir(), env=env_for_child(env),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def run_json(args, **kwargs):
    """Run the CLI and parse its stdout; (exit code, document, stderr)."""
    code, out, err = run_cli(args, **kwargs)
    try:
        doc = json.loads(out) if out.strip() else None
    except ValueError:
        doc = None
    return code, doc, err


def stub_without_jsonschema(parent):
    """A directory holding a jsonschema package that refuses to import; first on PYTHONPATH."""
    stub = os.path.join(parent, "no-jsonschema")
    os.makedirs(os.path.join(stub, "jsonschema"))
    write(os.path.join(stub, "jsonschema", "__init__.py"),
          'raise ImportError("jsonschema stubbed out for the exit-3 test")\n')
    return stub


# ---- event builders ---------------------------------------------------------------------------

STATION = {"station": "signoff", "run_id": "2026-04-01-widget-a", "harness": "claude-code"}
IMPORTER = {"station": "records-import", "run_id": "import-1", "harness": "claude-code"}
DOC_SHA = "7b1d9e5c3a08f46b2d71c0e8a95f34b6d2c7801e5f9a3b4c6d8e0f1a2b3c4d5e"


def location(raw, file=None, line=None, line_end=None, tag=None, more=None, resolved=None):
    if resolved is None:
        resolved = file is not None and line is not None
    return {"raw": raw, "file": file, "line": line, "line_end": line_end, "tag": tag,
            "more": more or [], "resolved": resolved}


def native(kind, at="2026-04-01T09:00:00Z", doc=DOC, identity=None, actor=None, **fields):
    event = {"v": 1, "kind": kind, "at": at, "ledger_doc": doc, "actor": dict(actor or STATION),
             "origin": {"kind": "native"},
             "source": {"known": True, "identity": copy.deepcopy(identity)} if identity else {"known": False}}
    event.update(fields)
    return event


def legacy_origin(line=51, raw="- MAJOR . src/widget.py:88 . the retry loop never ends"):
    return {"kind": "legacy", "doc": DOC, "doc_sha256": DOC_SHA, "line": line, "raw": raw,
            "heading_line": 40, "recorded_commit": None, "commit_named": None}


def opened(identity=None, doc=DOC):
    return native("log_opened", doc=doc, identity=identity, interface_version=1, component_version="0.1.0")


def raised(claim="the retry loop never ends", slice_name="A", severity="BLOCKER",
           loc=None, identity=None, doc=DOC, at="2026-04-01T09:00:01Z", scenario="it spins forever"):
    return native("finding_raised", at=at, doc=doc, identity=identity, slice=slice_name, severity=severity,
                  location=loc or location("src/widget.py:88", "src/widget.py", 88),
                  claim=claim, scenario=scenario, raised_by=slice_name)


def disposition(finding, identity, value="fixed", how="ran the widget suite",
                at="2026-04-01T11:00:00Z", doc=DOC, verified=None):
    return native("disposition", at=at, doc=doc, identity=identity, finding=finding, disposition=value,
                  how=how, join_basis=None,
                  verified_source=verified if verified is not None
                  else {"known": True, "identity": copy.deepcopy(identity)})


def events_file(parent, events, name="batch.json"):
    """Write a batch OUTSIDE the workspace, so writing it never changes the workspace's identity."""
    path = os.path.join(parent, name)
    write(path, json.dumps(events, ensure_ascii=False) + "\n")
    return path


def log_file(workspace, doc=DOC):
    add_scripts_to_path()
    from records_core import events as events_mod
    return events_mod.log_path(workspace, doc)


def read_log(workspace, doc=DOC):
    path = log_file(workspace, doc)
    if not os.path.isfile(path):
        return b""
    with open(path, "rb") as fh:
        return fh.read()
