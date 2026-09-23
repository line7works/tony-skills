"""Drive the signoff core with an adapter-built invocation (required test 2, the independence
refusal reached THROUGH the core). Standard library only; the core runs under `uv run` with the
pinned jsonschema, exactly as SKILL.md runs it; the seeded case is built by its own generator."""

import json
import os
import subprocess
import tempfile

TESTS = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(os.path.dirname(TESTS)))
PLUGIN = os.path.dirname(os.path.dirname(SKILL))
SIGNOFF = os.path.join(SKILL, "scripts", "signoff.py")
S3 = os.path.join(PLUGIN, "evals", "seeded-cases", "S3-independence", "build.py")
GEN = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else "python3"


def build_case(out, case="S3-01-clean"):
    proc = subprocess.run([GEN, S3, "--out", out, "--case", case, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if proc.returncode != 0:
        raise AssertionError("case build failed: %s" % proc.stderr.decode()[-400:])
    path = json.loads(proc.stdout.decode())["cases"][0]["path"]
    with open(os.path.join(path, "input.json")) as handle:
        seeded = json.load(handle)
    return path, seeded


def core(args):
    proc = subprocess.run(["uv", "run", "--quiet", "--python", "/usr/bin/python3", SIGNOFF]
                          + list(args), cwd=tempfile.gettempdir(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    out = proc.stdout.decode("utf-8")
    try:
        doc = json.loads(out) if out.strip() else None
    except ValueError:
        doc = {"_raw": out}
    return proc.returncode, doc, proc.stderr.decode("utf-8")


def independence_run(test, invocation, case_dir, seeded):
    """check-input, scope, request, record-answer on the case, with `invocation` whole."""
    document = {"protocol_version": 1, "invocation": invocation,
                "workspace": seeded["workspace"],
                "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                           "base": seeded["base"]}}
    path = os.path.join(case_dir, "adapter-input.json")
    with open(path, "w") as handle:
        json.dump(document, handle)
    run_dir = invocation["run_dir"]
    code, doc, err = core(["check-input", path])
    test.assertEqual(code, 0, err)
    test.assertFalse(doc["independent"])
    code, doc, err = core(["scope", "--run-dir", run_dir])
    test.assertEqual(code, 0, err)
    code, doc, err = core(["request", "--run-dir", run_dir])
    test.assertEqual(code, 0, err)
    test.assertFalse(doc["summon"])
    test.assertFalse(os.path.exists(os.path.join(run_dir, "request.json")))
    code, doc, err = core(["record-answer", "--run-dir", run_dir,
                           "--answer", os.path.join(case_dir, seeded["answer"])])
    test.assertEqual(code, 10, err)
    test.assertEqual(doc["refusal_reason"], "independence")
    test.assertIsNone(doc["verdict"])
    test.assertFalse(doc["verdict_recorded"])
    return doc


def records_snapshot(workspace):
    """Every file under the workspace (its `.git` aside) with its bytes' SHA-256: equal snapshots
    before and after a run mean the run recorded nothing in the project."""
    import hashlib
    out = {}
    for root, dirs, files in os.walk(workspace):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in files:
            path = os.path.join(root, name)
            with open(path, "rb") as handle:
                out[os.path.relpath(path, workspace)] = hashlib.sha256(handle.read()).hexdigest()
    return out
