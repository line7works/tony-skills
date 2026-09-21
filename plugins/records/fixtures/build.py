#!/usr/bin/env python3
"""Build the records component's git-backed fixture workspaces (records E12 contract section 1).

    ./build.py --list
    ./build.py --out DIR [--case legacy] [--json]

One case today, `legacy`: the synthetic workspace under `fixtures/legacy/`, copied whole into a
fresh git repository with one commit. Every document there is written to carry one shape family
of contract section 11.1 (L1 to L6, F1 to F4, S1, D1), one join basis of section 11.4, one of
the history cases of section 11.7, the card cases of section 9.3, or the mirror cases of
section 11.6. Nothing in it describes a real project, a real person, or a real system, and
nothing is copied from another repository: the component's repository is public (contract
section 3).

Deterministic: the author, the committer, and both dates are fixed, git runs under the clean
configuration environment the pilot uses (GIT_CONFIG_NOSYSTEM, GIT_CONFIG_GLOBAL=/dev/null,
LANG=C, TZ=UTC and the same -c flags), and file modes are set explicitly, so two builds of one
case produce the same commit hash. `--json` prints it.

This script only ever writes inside `--out`. It runs `git init`, `git add` and `git commit`
there, in a directory it created, and no git command anywhere else. The tests build into a
temporary directory and remove it.

Exit status: 0 built; 2 usage (an unknown case, no --out); 3 git is missing from PATH; 1 any
other failure.
Side effects: creates <out>/<case>/ (removing an existing one first) and a git repository inside
it. Reruns are safe and produce the same bytes.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEGACY = os.path.join(HERE, "legacy")
WHEN = "2026-05-20T09:00:00+00:00"
GIT_CONFIG_ARGS = [
    "-c", "core.hooksPath=/dev/null",
    "-c", "commit.gpgsign=false",
    "-c", "core.autocrlf=false",
    "-c", "core.fileMode=true",
    "-c", "protocol.file.allow=always",
]
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
    "GIT_AUTHOR_DATE": WHEN,
    "GIT_COMMITTER_DATE": WHEN,
}

# The documents the section 11.7 tests grow and change. `GROWN_TAIL` is appended to
# `docs/plans/2026-05-12-history.md` to make the "only grown at its tail" case; `CHANGED_FROM`
# and `CHANGED_TO` make the "an imported line changed" case out of the same document.
HISTORY_DOC = "docs/plans/2026-05-12-history.md"
GROWN_TAIL = """
### 2026-05-14 — recheck: Slice A
- MAJOR · src/list.py:5 · () · not fixed — executed: the list came back unsorted after the merge
"""
CHANGED_FROM = "- MAJOR · src/list.py:5 · the loading list is not sorted · a heavy crate lands on a light one · Slice A review"
CHANGED_TO = "- MAJOR · src/list.py:5 · the loading list is not sorted at all · a heavy crate lands on a light one · Slice A review"

CASES = {"legacy": LEGACY}


class BuildError(RuntimeError):
    pass


def git(cwd, args):
    exe = shutil.which("git")
    if not exe:
        raise BuildError("git is not on PATH")
    proc = subprocess.run([exe] + GIT_CONFIG_ARGS + list(args), cwd=cwd, env=GIT_ENV,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise BuildError("git %s failed (%d): %s" % (" ".join(args), proc.returncode,
                                                     proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8")


def copy_tree(source, target):
    """Copy every file of the fixture tree, with fixed modes and LF endings preserved."""
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for name in sorted(filenames):
            if name.endswith(".pyc") or name == ".DS_Store":
                continue
            src = os.path.join(dirpath, name)
            rel = os.path.relpath(src, source)
            dst = os.path.join(target, rel)
            directory = os.path.dirname(dst)
            if directory and not os.path.isdir(directory):
                os.makedirs(directory)
            with open(src, "rb") as fh:
                data = fh.read()
            with open(dst, "wb") as fh:
                fh.write(data)
            os.chmod(dst, 0o644)


def build_case(out_dir, case="legacy"):
    """Build one case into <out_dir>/<case> and return {case, workspace, commit}."""
    if case not in CASES:
        raise BuildError("unknown case: %s" % case)
    workspace = os.path.abspath(os.path.join(out_dir, case))
    if os.path.lexists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace)
    copy_tree(CASES[case], workspace)
    git(workspace, ["init", "-q", "-b", "main"])
    git(workspace, ["add", "-A"])
    git(workspace, ["commit", "-q", "-m", "the crate packer fixture workspace"])
    commit = git(workspace, ["rev-parse", "HEAD"]).strip()
    return {"case": case, "workspace": workspace, "commit": commit}


def documents(case="legacy"):
    """Every Markdown document of a case, workspace-relative and sorted."""
    root = CASES[case]
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(dirnames)
        for name in sorted(filenames):
            if name.endswith(".md"):
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                out.append(rel.replace(os.sep, "/"))
    return sorted(out)


def ledger_documents(case="legacy"):
    """The case's ledger documents: everything but the verdict docs under docs/reviews/."""
    return [d for d in documents(case) if not d.startswith("docs/reviews/")]


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="Build the records component's git-backed fixture workspaces.",
        epilog="examples:\n  ./build.py --list\n  ./build.py --out /tmp/fx --json\n\n"
               "exit status: 0 built; 2 usage; 3 git missing; 1 any other failure.\n"
               "side effects: creates <out>/<case>/ and a git repository inside it; nothing else "
               "is written and no other git command is run.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", metavar="DIR", default=None, help="output directory (created)")
    parser.add_argument("--case", metavar="ID", action="append", default=[],
                        help="build only these cases (repeatable); default: all")
    parser.add_argument("--list", action="store_true", help="print the case ids and exit")
    parser.add_argument("--json", action="store_true", help="a JSON summary instead of the human one")
    args = parser.parse_args(argv)
    if args.list:
        for case in sorted(CASES):
            sys.stdout.write(case + "\n")
        return 0
    if not args.out:
        sys.stderr.write("build.py: error: --out DIR is required to build\n")
        return 2
    unknown = [c for c in args.case if c not in CASES]
    if unknown:
        sys.stderr.write("build.py: error: unknown case id(s): %s\n" % ", ".join(unknown))
        return 2
    if not shutil.which("git"):
        sys.stderr.write("git is missing from PATH; the fixtures cannot be built without it\n")
        return 3
    selected = args.case or sorted(CASES)
    if not os.path.isdir(args.out):
        os.makedirs(args.out)
    built = []
    try:
        for case in selected:
            built.append(build_case(args.out, case))
    except BuildError as exc:
        sys.stderr.write("%s\n" % exc)
        return 1
    if args.json:
        sys.stdout.write(json.dumps({"cases": built}, indent=2, sort_keys=True) + "\n")
    else:
        for row in built:
            sys.stdout.write("%s  %s  %s\n" % (row["case"], row["workspace"], row["commit"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
