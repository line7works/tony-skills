#!/usr/bin/env python3
"""Drive the build core through its REAL CLI on each seeded case and write down what it did.

    PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh observe.py --all --out <dir>
    PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh observe.py --case B2-02-check-fails --out <dir>
    PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh observe.py --list

This script emits FACTS and never an expectation. The outcome of each case lives in an answer
key no builder of this lane has seen, and the control room grades the `observed.json` files
against it. So there is no expected value anywhere in this plugin, and this script has no notion
of a case passing or failing: it builds the case, runs the core's five phases through
`scripts/build.py`, measures the workspace before and after, and writes down what it observed
under the neutral names of `README.md`'s vocabulary table.

`either` is the key's word, not this script's. Where the contract allows two passing shapes the
key holds the alternatives; this script emits the one thing that happened.

A name the core has no fact for is OMITTED, never guessed. A run that stopped before its source
set existed emits no `source_set_*`, and every signoff-only name (`packet_must_include`,
`raised_locations`, `verdict_recorded`, …) is absent from every observation this script writes.

Two things are measured here rather than read out of the core's own result, so that the
observation is an outside one:

    card_after    read from the build doc's `Status:` line by this script's own regex, not from
                  the core's report of what it wrote
    writes_none   a digest over every file of the workspace, the records log included, taken
                  before the run and after it. `.git` is left out: git's own bookkeeping (an
                  index stat cache a read-only `git status` may refresh) is not a write of this
                  core, and nothing here runs a git command that changes a repository.

Standard library only, Python 3.9, no network, no model call, no harness launch. Builds into
`--out` and leaves what it built there for the grader to read. `--out`, or a TMPDIR, that is or
sits under ~/.claude, ~/.codex or a ~/.local/share/skills-v2-* home, as given or resolved, is
refused, exit 2 and nothing created (the setups' home guard, E14 punch list).
The interpreter that runs this file starts before its guard, and the /usr/bin/python3 shim writes into the
temp folder as it starts (inside a Codex sandbox, `xcrun_db`): start this file through
`../../setups/safe-python.sh`, which starts the interpreter with TMPDIR, TEMP and TMP cleared and hands their
values to this guard, or through uv (its own interpreter, not the shim).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
EVALS = os.path.dirname(HERE)
PLUGIN = os.path.dirname(EVALS)
BUILD_PY = os.path.join(PLUGIN, "skills", "build-v2", "scripts", "build.py")

FAMILIES = {
    "B1-scope-adherence": ("B1-01-clean", "B1-02-untracked-outside", "B1-03-committed-outside",
                           "B1-04-changed-outside"),
    "B2-honest-failure": ("B2-01-clean", "B2-02-check-fails", "B2-03-check-cannot-run",
                          "B2-04-answer-claims-built", "B2-05-report-only"),
}

STATUS_LINE = re.compile(r"^\s*Status:\s*(.*?)\s*$")
SLICE_HEADING = re.compile(r"^##\s+Slice\s+(\S+)\s*(?:[—–-]+.*)?$")
ANY_HEADING = re.compile(r"^#{1,6}\s")


class ObserveError(RuntimeError):
    pass


# ---- measuring ---------------------------------------------------------------------------------

def tree_digest(root):
    """A digest over every file under `root` except `.git`: path, mode and content."""
    entries = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root)
            st = os.lstat(full)
            if os.path.islink(full):
                mode, content = "link", os.readlink(full).encode("utf-8", "surrogateescape")
            else:
                mode = "%04o" % (st.st_mode & 0o777)
                with open(full, "rb") as fh:
                    content = fh.read()
            entries.append(rel + "\0" + mode + "\0" + hashlib.sha256(content).hexdigest())
    entries.sort()
    return hashlib.sha256(("\n".join(entries) + "\n").encode("utf-8")).hexdigest()


def status_of(workspace, document, slice_name):
    """The `Status:` text of one slice, read from the document by this script's own reader."""
    path = os.path.join(workspace, document)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    inside = False
    for line in lines:
        heading = SLICE_HEADING.match(line)
        if heading:
            inside = heading.group(1) == slice_name
            continue
        if ANY_HEADING.match(line):
            inside = False
            continue
        if inside:
            found = STATUS_LINE.match(line)
            if found:
                return found.group(1)
    return None


# ---- running -----------------------------------------------------------------------------------

def clean_env():
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/"),
           "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1"}
    for name in ("RECORDS_ROOT",):
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def build_case(family, case_id, out_dir):
    """Build one case with its family's own generator, unchanged."""
    generator = os.path.join(HERE, family, "build.py")
    proc = subprocess.run([sys.executable, generator, "--out", out_dir, "--case", case_id, "--json"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=clean_env())
    if proc.returncode != 0:
        raise ObserveError("building %s failed (%d): %s"
                           % (case_id, proc.returncode, proc.stderr.decode("utf-8", "replace")))
    summary = json.loads(proc.stdout.decode("utf-8"))
    return summary["cases"][0]["path"]


def run_phase(args, python=None):
    proc = subprocess.run([python or sys.executable, BUILD_PY] + [str(a) for a in args],
                          cwd=tempfile.gettempdir(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=clean_env())
    return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def core_input(case_dir, seeded):
    """The seeded input translated into this core's own input document.

    The seeded shape is deliberately not a core's input schema (the cases' README): each core's
    adapter reads what it needs from it. This is that translation, and it invents nothing — every
    field comes from the seeded input or is a fact about this run.
    """
    return {
        "input_version": 1,
        "run_id": "observe-%s" % seeded["case"],
        "workspace": seeded["workspace"],
        "run_dir": seeded["run_dir"],
        "build_doc": seeded["build_doc"],
        "slice": seeded["slice"],
        "base": seeded["base"],
        "case": seeded["case"],
        "report_only": bool(seeded.get("report_only")),
        "allow_open_blocker": False,
        "rerun_checks": False,
        "invocation": {"harness": "seeded-cases", "caller": "observe.py", "mode": "station"},
    }


def observe_case(family, case_id, out_dir, python=None):
    """Build one case, drive the core through it, and write `observed.json` beside the case."""
    case_dir = build_case(family, case_id, os.path.join(out_dir, family))
    seeded = json.load(open(os.path.join(case_dir, "input.json"), encoding="utf-8"))
    workspace = seeded["workspace"]
    document, slice_name = seeded["build_doc"], seeded["slice"]

    before_digest = tree_digest(workspace)
    card_before = status_of(workspace, document, slice_name)

    input_path = os.path.join(case_dir, "core-input.json")
    with open(input_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(core_input(case_dir, seeded), indent=2, sort_keys=True) + "\n")
    answer_path = os.path.join(case_dir, seeded.get("answer") or "answer.json")
    run_dir = seeded["run_dir"]

    phases = [
        ("check-input", ["check-input", input_path]),
        ("contract", ["contract", "--run-dir", run_dir]),
        ("preflight", ["preflight", "--run-dir", run_dir]),
        ("record-answer", ["record-answer", "--run-dir", run_dir, "--answer", answer_path]),
        ("report", ["report", "--run-dir", run_dir]),
    ]
    transcript = []
    for name, args in phases:
        code, out, err = run_phase(args, python)
        transcript.append({"phase": name, "exit": code, "stderr": err.strip()[-500:]})
        if code == 10:
            break            # the run reached a terminal status; later phases have nothing to do
        if code != 0:
            transcript[-1]["stdout"] = out.strip()[-2000:]
            break

    after_digest = tree_digest(workspace)
    card_after = status_of(workspace, document, slice_name)
    result_path = os.path.join(run_dir, "result.json")
    result = None
    if os.path.isfile(result_path):
        with open(result_path, "rb") as fh:
            result = json.loads(fh.read().decode("utf-8"))

    observed = observation(result, card_after, before_digest == after_digest)
    observed["_case"] = case_id
    observed["_family"] = family
    observed["_case_dir"] = case_dir
    observed["_result"] = result_path if result is not None else None
    observed["_phases"] = transcript
    observed["_card_before_document"] = card_before

    path = os.path.join(case_dir, "observed.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(observed, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return {"case": case_id, "family": family, "case_dir": case_dir, "observed": path}


def observation(result, card_after, unchanged):
    """The neutral vocabulary, emitted only for the names this core has a fact for."""
    observed = {"writes_none": bool(unchanged)}
    if card_after is not None:
        observed["card_after"] = card_after
    if result is None:
        return observed

    observed["terminal_status"] = result["terminal_status"]
    observed["answer_refused"] = result["status"] == "answer_refused"
    if result.get("refusal_reason"):
        observed["refusal_reason"] = result["refusal_reason"]

    source = result.get("source_set")
    if source:
        observed["base_ref"] = source["base"]
        observed["source_set_committed"] = list(source["committed"])
        observed["source_set_changed"] = list(source["changed"])
        observed["source_set_untracked"] = list(source["untracked"])

    if result.get("contract") is not None:
        observed["out_of_scope_paths"] = sorted(row["path"] for row in result.get("out_of_scope") or [])

    named = [row for row in result.get("checks") or [] if row.get("named_by_slice")]
    if named:
        observed["checks_passed"] = sorted(r["name"] for r in named if r["result"] == "passed")
        observed["checks_failing"] = sorted(r["name"] for r in named if r["result"] == "failing")
        observed["checks_skipped"] = sorted(r["name"] for r in named if r["result"] == "not_run")
        observed["checks_not_passed"] = sorted(r["name"] for r in named if r["result"] != "passed")
        observed["check_output_contains"] = dict((r["name"], r.get("output") or "") for r in named)
    return observed


# ---- the CLI -------------------------------------------------------------------------------------

def family_of(case_id):
    for family, cases in FAMILIES.items():
        if case_id in cases:
            return family
    raise ObserveError("unknown case id: %s" % case_id)


def _same_below(path, base):
    """The part of `path` below `base` by the file system's own identity ("" when they are the same
    folder), or None. macOS names one folder by more than one path that neither abspath nor realpath
    rewrites (/System/Volumes/Data/..., /.nofollow/..., /.resolve/N/...), so the nearest existing
    ancestor of `path` is compared with `base` by device and inode."""
    try:
        want = os.stat(base)
    except OSError:
        return None
    probe, tail = os.path.realpath(path), []
    while True:
        try:
            if os.path.samestat(os.stat(probe), want):
                return os.sep.join(reversed(tail)).casefold()
        except OSError:
            pass
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        tail.append(os.path.basename(probe))
        probe = parent


def _below_home(path, base, home):
    """`_same_below`, and for a `base` that does not exist yet the same answer read through HOME: `path` is
    compared with HOME by device and inode and the part below HOME is read against `base`'s place below it."""
    got = _same_below(path, base)
    if got is not None:
        return got
    below = _same_below(path, home)
    if below is None:
        return None
    rel = os.path.relpath(base, home).casefold()
    return "" if below == rel else (below[len(rel) + 1:] if below.startswith(rel + os.sep) else None)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="observe.py",
        description="Drive the build core through the seeded cases and write down what it did. "
                    "Emits facts under the README's neutral vocabulary; no expected value appears "
                    "here or anywhere else in this plugin.",
        epilog="examples:\n"
               "  observe.py --all --out /tmp/observe\n"
               "  observe.py --case B2-05-report-only --out /tmp/observe\n"
               "  observe.py --list\n\n"
               "side effects: builds each case under --out (an existing case directory there is "
               "rebuilt) and writes observed.json beside it. Nothing outside --out is written.\n"
               "exit: 0 every case was observed, 2 a usage slip, 1 a case could not be built or run.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", metavar="DIR", help="where the cases are built and observed")
    parser.add_argument("--case", metavar="ID", action="append", default=[],
                        help="observe only these cases (repeatable)")
    parser.add_argument("--all", action="store_true", help="observe every case of both families")
    parser.add_argument("--list", action="store_true", help="print the case ids, one per line")
    parser.add_argument("--python", metavar="EXE", default=None,
                        help="the interpreter the core runs under (default: this one)")
    args = parser.parse_args(argv)

    if args.list:
        for family in sorted(FAMILIES):
            for case in FAMILIES[family]:
                sys.stdout.write(case + "\n")
        return 0
    if not args.out:
        parser.error("--out DIR is required")
    if not args.all and not args.case:
        parser.error("--all or --case ID is required")

    if args.all:
        wanted = [(family, case) for family in sorted(FAMILIES) for case in FAMILIES[family]]
    else:
        wanted = [(family_of(case), case) for case in args.case]

    # The setups' home guard (E14 slice 3c fix 3-2; E14 punch list), TMPDIR, TEMP and TMP included, before
    # anything is created.
    out = os.path.abspath(args.out)
    home = os.environ.get("HOME", "")
    share = os.path.join(home, ".local", "share")
    temps = [os.environ[name] for name in ("TMPDIR", "TEMP", "TMP") if os.environ.get(name)] or ["/tmp"]
    for path in [out, os.path.realpath(out)] + [form(t) for t in temps for form in (os.path.abspath, os.path.realpath)]:
        for base in (os.path.join(home, ".claude"), os.path.join(home, ".codex"), share):
            for form in (os.path.abspath(base), os.path.realpath(base), None):
                p, b = path.casefold(), (form or "").casefold().rstrip(os.sep)
                below = (_below_home(path, base, home) if form is None
                         else "" if p == b else (p[len(b) + 1:] if p.startswith(b + os.sep) else None))
                if below is None or (base == share and not below.split(os.sep)[0].startswith("skills-v2-")):
                    continue
                sys.stderr.write("observe.py: %s is under %s, which no setup may touch; nothing created\n"
                                 % (path, base if base != share else os.path.join(share, below.split(os.sep)[0])))
                return 2
    if not os.path.isabs(home):
        sys.stderr.write("observe.py: HOME is not an absolute path; nothing created\n")
        return 2
    os.makedirs(args.out, exist_ok=True)
    rows = []
    for family, case in wanted:
        rows.append(observe_case(family, case, args.out, args.python))
    sys.stdout.write(json.dumps({"observed": len(rows), "out": os.path.abspath(args.out),
                                 "cases": rows}, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ObserveError as exc:
        sys.stderr.write("%s\n" % exc)
        sys.exit(1)
