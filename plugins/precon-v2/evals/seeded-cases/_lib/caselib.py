"""Shared generator library for the E14 seeded-case families (lane contract section 14).

Trimmed from build-v2's `evals/seeded-cases/_lib/caselib.py` (E13's slice 0 writer's): the git
determinism, the tree hash and the CLI are kept; the build-doc helpers are gone, and a case is
built from a spec rather than by hand. Identical in the four front cores
(`references/shared-files.txt`). Standard library only, Python 3.9. Every family's build.py
locates this file relative to its own `__file__`, holds a `SPECS` table, and ends with
`make_family()`. Its `--out` is refused, exit 2 and nothing created, when it is or sits under
~/.claude, ~/.codex or a ~/.local/share/skills-v2-* home, as given or resolved (the setups' home
guard, E14 slice 3c).

A spec is a dict:

    {"git": bool,                         the workspace is a git work tree with one commit
     "workspace": {rel: text},            files of the workspace (committed when git)
     "staging": {rel: text},              files of the staging home
     "case_files": {rel: text},           files beside the workspace in the case directory
     "input": {...},                      neutral input fields beyond the defaults below
     "drive": [...],                      what observe.py drives, step by step (never an outcome)
     "notes": "..."}

Encoding decisions that make two builds of one case byte-identical: git runs with
GIT_CONFIG_NOSYSTEM=1, GIT_CONFIG_GLOBAL=/dev/null, a fixed author, committer and date, and fixed
config flags; `tree_sha256()` hashes every file under the case directory except manifest.json and
`.git`, with the absolute output directory replaced by `<OUT>` first.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

GIT_DATE = "2026-09-19T09:00:00-07:00"
GIT_CONFIG_ARGS = ["-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                   "-c", "core.autocrlf=false", "-c", "core.fileMode=true"]


class CaseError(RuntimeError):
    """Any generator failure."""


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def _git(cwd, args):
    exe = shutil.which("git")
    if not exe:
        raise CaseError("git is not on PATH; the case library needs git 2.x")
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/"), "LANG": "C",
           "LC_ALL": "C", "TZ": "UTC", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_TERMINAL_PROMPT": "0", "GIT_AUTHOR_NAME": "Case Author",
           "GIT_AUTHOR_EMAIL": "case@example.invalid", "GIT_COMMITTER_NAME": "Case Author",
           "GIT_COMMITTER_EMAIL": "case@example.invalid", "GIT_AUTHOR_DATE": GIT_DATE,
           "GIT_COMMITTER_DATE": GIT_DATE}
    proc = subprocess.run([exe] + GIT_CONFIG_ARGS + args, cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise CaseError("git %s failed (%d): %s" % (" ".join(args), proc.returncode,
                                                   proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8")


def tree_sha256(case_dir, out_dir):
    out_bytes = os.path.abspath(out_dir).encode("utf-8")
    entries = []
    for root, dirs, files in os.walk(case_dir):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, case_dir)
            if rel == "manifest.json":
                continue
            st = os.lstat(full)
            with open(full, "rb") as fh:
                content = fh.read()
            if out_bytes in content:
                content = content.replace(out_bytes, b"<OUT>")
            entries.append(rel + "\0" + "%04o" % (st.st_mode & 0o777) + "\0" + sha256_hex(content))
    entries.sort()
    return sha256_hex(("\n".join(entries) + "\n").encode("utf-8") if entries else b"")


def _write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.chmod(path, 0o644)


def _write_json(path, doc):
    _write(path, json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def _inside(base, rel):
    if os.path.isabs(rel) or rel.split("/")[0] == "..":
        raise CaseError("case paths are relative and inside their home: %r" % rel)
    return os.path.join(base, rel)


def build(out_dir, case_id, family, core, spec, answers_dir):
    out_dir = os.path.abspath(out_dir)
    case_dir = os.path.join(out_dir, case_id)
    if os.path.lexists(case_dir):
        shutil.rmtree(case_dir)
    workspace = os.path.join(case_dir, "workspace")
    staging = os.path.join(case_dir, "staging")
    run_dir = os.path.join(case_dir, "run")
    for folder in (workspace, staging, run_dir):
        os.makedirs(folder)
    for rel, text in sorted((spec.get("workspace") or {}).items()):
        _write(_inside(workspace, rel), text)
    head = None
    if spec.get("git", True):
        _git(workspace, ["init", "-q", "-b", "main"])
        _git(workspace, ["add", "-A"])
        _git(workspace, ["commit", "-q", "--allow-empty", "-m", "base"])
        head = _git(workspace, ["rev-parse", "HEAD"]).strip()
    for rel, text in sorted((spec.get("staging") or {}).items()):
        _write(_inside(staging, rel), text)
    for rel, text in sorted((spec.get("case_files") or {}).items()):
        _write(_inside(case_dir, rel), text)
    answer = None
    src = os.path.join(answers_dir, case_id + ".json")
    if os.path.exists(src):
        with open(src, encoding="utf-8") as fh:
            doc = json.load(fh)
        if doc.get("case") != case_id:
            raise CaseError("answers/%s.json names case %r" % (case_id, doc.get("case")))
        _write_json(os.path.join(case_dir, "answer.json"), doc)
        answer = "answer.json"
    neutral = {"seeded_input": 1, "case": case_id, "core": core, "workspace": workspace,
               "staging": staging, "run_dir": run_dir, "report_only": False, "answer": answer}
    neutral.update(spec.get("input") or {})
    _write_json(os.path.join(case_dir, "input.json"), neutral)
    _write_json(os.path.join(case_dir, "drive.json"), {"case": case_id, "steps": spec.get("drive") or []})
    manifest = {"case": case_id, "family": family, "core": core, "workspace": "workspace",
                "staging": "staging", "run_dir": "run", "input": "input.json", "drive": "drive.json",
                "answer": answer, "head": head, "notes": spec.get("notes", ""), "tree_sha256": ""}
    manifest["tree_sha256"] = tree_sha256(case_dir, out_dir)
    _write_json(os.path.join(case_dir, "manifest.json"), manifest)
    return case_dir, manifest


def make_family(family, core, specs, argv=None):
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    answers_dir = os.path.join(here, "answers")
    parser = argparse.ArgumentParser(prog="build.py", description="Build the %s seeded cases." % family)
    parser.add_argument("--out", metavar="DIR", help="output directory (created; existing case dirs are rebuilt)")
    parser.add_argument("--case", metavar="ID", action="append", default=[],
                        help="build only these cases (repeatable); an unknown id exits 2")
    parser.add_argument("--list", action="store_true", help="print case ids, one per line")
    parser.add_argument("--json", action="store_true", help="print a JSON summary on stdout")
    args = parser.parse_args(argv)
    if args.list:
        for cid in specs:
            print(cid)
        sys.exit(0)
    if not args.out:
        parser.error("--out DIR is required to build")
    unknown = [c for c in args.case if c not in specs]
    if unknown:
        sys.stderr.write("unknown case id(s): %s\n" % ", ".join(unknown))
        sys.exit(2)
    # The setups' home guard (E14 slice 3c fix 3-2), before anything is created or rebuilt.
    out = os.path.abspath(args.out)
    home = os.environ.get("HOME", "")
    share = os.path.join(home, ".local", "share")
    for path in (out, os.path.realpath(out)):
        for base in (os.path.join(home, ".claude"), os.path.join(home, ".codex"), share):
            for form in (os.path.abspath(base), os.path.realpath(base)):
                p, b = path.casefold(), form.casefold().rstrip(os.sep)
                below = "" if p == b else (p[len(b) + 1:] if p.startswith(b + os.sep) else None)
                if below is None or (base == share and not below.split(os.sep)[0].startswith("skills-v2-")):
                    continue
                sys.stderr.write("build.py: %s is under %s, which no setup may touch; nothing created\n"
                                 % (args.out, base if base != share else os.path.join(share, below.split(os.sep)[0])))
                sys.exit(2)
    if not os.path.isabs(home):
        sys.stderr.write("build.py: HOME is not an absolute path; nothing created\n")
        sys.exit(2)
    os.makedirs(args.out, exist_ok=True)
    summary = []
    try:
        for cid in args.case or list(specs):
            path, manifest = build(args.out, cid, family, core, specs[cid], answers_dir)
            summary.append({"case": cid, "path": path, "tree_sha256": manifest["tree_sha256"],
                            "head": manifest["head"]})
    except CaseError as exc:
        sys.stderr.write("%s\n" % exc)
        sys.exit(3 if "git is not on PATH" in str(exc) else 1)
    if args.json:
        print(json.dumps({"family": family, "cases": summary}, indent=2, sort_keys=True))
    else:
        for row in summary:
            print("%s  %s" % (row["case"], row["tree_sha256"]))
    sys.exit(0)
