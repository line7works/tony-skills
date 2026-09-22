#!/usr/bin/env python3
"""observe.py: drive signoff-v2 over a seeded case and write down what it did.

    PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --case S1-02-untracked-defect --out DIR
    PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --all --out DIR
    PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --list

This writes FACTS, never expectations. The answer key lives outside this repository and nobody
here has seen it, so nothing in this file says what a case "should" produce: each run is driven
through the REAL CLI — `check-input`, `scope`, `request`, `record-answer`, `record` — with the
case's own `answer.json` fed at the phase that takes a reviewer's answer, and whatever comes back
is written to `<out>/<case id>/observed.json` in the neutral vocabulary of `README.md`.

A name the table lists and this core has a fact for is emitted. A name it has no fact for is
OMITTED, never guessed: `out_of_scope_paths` and `checks_skipped` belong to the build core and
never appear here. `either` is the key's word for "two shapes both pass"; this file never writes
one, because a fact is not an alternative.

Three of the table's names are assertion-shaped rather than fact-shaped, and `RUNNING.md` says
how each is answered:

- `packet_must_include` and `packet_must_exclude` both carry the packet's COMPLETE file list, so
  an include assertion is a membership test against it and an exclude assertion is a
  disjointness test against it. The list is complete, so anything absent from it is excluded.
- `claims_absent_from_packet` carries the delivered material VERBATIM, so an absence assertion
  is a substring test against the bytes the reviewer actually received.

Keys beginning with `_` are for a person reading the file and are not part of the vocabulary.

Standard library only, Python 3.9, no network, no model call, no harness launch. Each case is
built into a temporary directory with the family's own generator and cleaned up afterwards.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
SIGNOFF = os.path.join(PLUGIN, "skills", "signoff-v2", "scripts", "signoff.py")
PYTHON = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
FAMILIES = ("S1-review-scope", "S2-evidence", "S3-independence")
PHASES = ("check-input", "scope", "request", "record-answer", "record")

EXAMPLES = """examples:
  PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --all --out /tmp/observed
  -> one <case id>/observed.json per case, plus a summary on stdout

exit status: 0 every case ran to a terminal status; 2 usage; 1 a case could not be built or
driven at all (which is itself reported, never hidden).
side effects: writes <out>/<case id>/observed.json. Cases are built into a temporary directory
and removed; nothing is written into the repository.
"""


def families():
    return [f for f in FAMILIES if os.path.isdir(os.path.join(HERE, f))]


def case_ids(family):
    proc = subprocess.run([PYTHON, os.path.join(HERE, family, "build.py"), "--list"],
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("--list of %s failed: %s" % (family, proc.stderr.decode("utf-8", "replace")))
    return [line for line in proc.stdout.decode("utf-8").split("\n") if line.strip()]


def all_cases():
    out = []
    for family in families():
        for case_id in case_ids(family):
            out.append((family, case_id))
    return out


def family_of(case_id):
    for family in families():
        if case_id in case_ids(family):
            return family
    raise KeyError("no family holds the case %r" % case_id)


def build(family, case_id, into):
    proc = subprocess.run([PYTHON, os.path.join(HERE, family, "build.py"), "--out", into,
                           "--case", case_id, "--json"],
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("build of %s failed: %s"
                           % (case_id, proc.stderr.decode("utf-8", "replace")[-400:]))
    return json.loads(proc.stdout.decode("utf-8"))["cases"][0]["path"]


def signoff(args, env=None):
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if env:
        e.update(env)
    proc = subprocess.run([PYTHON, SIGNOFF] + [str(a) for a in args], env=e,
                          cwd=tempfile.gettempdir(),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    body = None
    if out.strip():
        try:
            body = json.loads(out)
        except ValueError:
            body = None
    return proc.returncode, body, proc.stderr.decode("utf-8", "replace")


def core_input(case_dir, seeded):
    """The seeded case's neutral input, read into this core's own input structure.

    The seeded `input.json` is deliberately not any core's schema (README, "The run input"), so
    this is the adapter the README says each core writes. Nothing is invented: every value comes
    from the case.
    """
    return {
        "protocol_version": 1,
        "invocation": {
            "mode": "headless",
            "caller": "seeded-case",
            "run_id": "observe-%s" % seeded["case"],
            "run_dir": seeded["run_dir"],
            "run_date": "2026-09-21",
            "harness": None,
            "sessions": seeded["sessions"],
        },
        "workspace": seeded["workspace"],
        "target": {"build_doc": seeded["build_doc"], "slice": seeded["slice"],
                   "base": seeded["base"]},
        "report_only": bool(seeded.get("report_only")),
        "review": {"depth": "LEAN", "route": "recorded-answer", "builder_conversation": []},
    }


def drive(case_dir, seeded, records_root=None):
    """Run every phase in order, stopping at the first terminal one. Returns (result, trail)."""
    run_dir = seeded["run_dir"]
    input_path = os.path.join(case_dir, "signoff-input.json")
    with open(input_path, "w", encoding="utf-8") as fh:
        json.dump(core_input(case_dir, seeded), fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    env = {"RECORDS_ROOT": records_root} if records_root else {}
    answer = os.path.join(case_dir, seeded.get("answer", "answer.json"))
    calls = {"check-input": ["check-input", input_path],
             "scope": ["scope", "--run-dir", run_dir],
             "request": ["request", "--run-dir", run_dir],
             "record-answer": ["record-answer", "--run-dir", run_dir, "--answer", answer],
             "record": ["record", "--run-dir", run_dir]}
    trail = []
    for phase in PHASES:
        code, body, err = signoff(calls[phase], env=env)
        trail.append({"phase": phase, "exit": code,
                      "stderr": err.strip()[-400:] if err.strip() else None})
        if code != 0:
            break
    result_path = os.path.join(run_dir, "result.json")
    result = None
    if os.path.isfile(result_path):
        with open(result_path, "rb") as fh:
            result = json.loads(fh.read().decode("utf-8"))
    return result, trail


# ---- the neutral vocabulary ----------------------------------------------------------------

def card_now(workspace, build_doc, slice_name):
    """The slice's `Status:` line as it stands after the run — the card, measured, not inferred."""
    path = os.path.join(workspace, build_doc)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    inside = False
    for line in lines:
        if line.startswith("## "):
            head = line[3:].strip()
            inside = head.startswith("Slice ") and head[6:].split()[0].rstrip(":") == slice_name
            continue
        if inside and line.startswith("Status:"):
            return line[len("Status:"):].strip()
    return None


def observed_of(result, seeded, workspace, trail):
    """What the run reported, in the README's names. Facts only; unknown names are omitted."""
    out = {"_case": seeded["case"], "_trail": trail}
    if result is None:
        out["_no_result"] = "the run wrote no result.json; the trail says where it stopped"
        return out

    out["_status"] = result["status"]
    out["_stop_reason_code"] = result.get("stop_reason_code")
    out["_verdict"] = result.get("verdict")
    out["terminal_status"] = result["terminal_status"]
    out["answer_refused"] = bool(result.get("answer_refused"))
    out["writes_none"] = bool(result.get("writes_none"))
    out["verdict_recorded"] = bool(result.get("verdict_recorded"))
    if result.get("refusal_reason") is not None:
        out["refusal_reason"] = result["refusal_reason"]
    out["clean_review_checks_listed"] = bool(result.get("clean_review_checks_listed"))

    source = result.get("source_set")
    if source:
        out["base_ref"] = source["base_ref"]
        out["source_set_committed"] = sorted(source["committed"])
        out["source_set_changed"] = sorted(source["changed"])
        out["source_set_untracked"] = sorted(source["untracked"])

    packet = result.get("packet")
    if packet:
        files = sorted(row["path"] for row in packet["files"])
        out["_packet_files"] = files
        out["packet_must_include"] = files
        out["packet_must_exclude"] = files
        material = packet.get("material_path")
        if material and os.path.isfile(material):
            with open(material, "r", encoding="utf-8") as fh:
                out["claims_absent_from_packet"] = fh.read()
        out["_packet_withheld"] = [row["what"] for row in packet.get("withheld", [])]

    raised = result.get("findings") or []
    notes = result.get("notes") or []
    out["raised_locations"] = sorted(row["location"] for row in raised)
    out["note_locations"] = sorted(row["location"] for row in notes if row.get("location"))
    out["raised_severities"] = {row["location"]: row["severity"] for row in raised}
    out["raised_evidence_kinds"] = {row["location"]: row["evidence_kind"] for row in raised}

    seen = set()
    for row in raised + notes:
        if row.get("location"):
            seen.add(row["location"])
    for row in read_answer_locations(workspace, seeded):
        seen.add(row)
    out["not_raised_locations"] = sorted(seen - set(out["raised_locations"]))

    checks = result.get("checks_executed") or []
    passed = [row["name"] for row in checks if row.get("exit_code") == 0]
    failing = [row["name"] for row in checks if row.get("exit_code") not in (0, None)]
    if checks:
        out["checks_passed"] = sorted(passed)
        out["checks_failing"] = sorted(failing)
        out["checks_not_passed"] = sorted(failing)
        out["check_output_contains"] = {row["name"]: (row.get("output") or "") for row in checks}

    card = card_now(workspace, seeded["build_doc"], seeded["slice"])
    if card is not None:
        out["card_after"] = card
    return out


def read_answer_locations(workspace, seeded):
    """Every location the recorded answer named, so `not_raised_locations` is a fact about what
    the run was given and not only about what it kept."""
    path = os.path.join(os.path.dirname(workspace), seeded.get("answer", "answer.json"))
    if not os.path.isfile(path):
        return []
    with open(path, "rb") as fh:
        answer = json.loads(fh.read().decode("utf-8"))
    out = []
    for key in ("findings", "notes_kept"):
        for row in (answer.get(key) or []):
            if isinstance(row, dict) and row.get("location"):
                out.append(row["location"])
    return out


# ---- main -----------------------------------------------------------------------------------

def observe_one(family, case_id, out_dir, records_root=None, keep=None):
    scratch = keep or tempfile.mkdtemp(prefix="signoff-observe-")
    try:
        case_dir = build(family, case_id, os.path.join(scratch, family))
        with open(os.path.join(case_dir, "input.json"), "rb") as fh:
            seeded = json.loads(fh.read().decode("utf-8"))
        workspace = seeded["workspace"]
        result, trail = drive(case_dir, seeded, records_root=records_root)
        observed = observed_of(result, seeded, workspace, trail)
    finally:
        if keep is None:
            shutil.rmtree(scratch, ignore_errors=True)
    folder = os.path.join(out_dir, case_id)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    path = os.path.join(folder, "observed.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(observed, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return path, observed


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="observe.py",
        description="Drive signoff-v2 over the seeded cases through its real CLI and write what "
                    "it did, in the neutral vocabulary. Facts only; no expected value appears "
                    "anywhere in this plugin.",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", metavar="ID", action="append", default=[],
                        help="observe this case (repeatable)")
    parser.add_argument("--all", action="store_true", help="observe every case of every family")
    parser.add_argument("--out", metavar="DIR", help="where the observed.json files go")
    parser.add_argument("--list", action="store_true", help="print the case ids, one per line")
    parser.add_argument("--records-root", metavar="DIR",
                        help="pass this to the core as the records component root")
    args = parser.parse_args(argv)

    if args.list:
        for family, case_id in all_cases():
            sys.stdout.write(case_id + "\n")
        return 0
    if not args.out:
        parser.error("--out DIR is required")
    if not args.case and not args.all:
        parser.error("name --case ID or pass --all")

    wanted = all_cases() if args.all else [(family_of(c), c) for c in args.case]
    rows, failed = [], 0
    for family, case_id in wanted:
        try:
            path, observed = observe_one(family, case_id, args.out, records_root=args.records_root)
        except Exception as failure:                        # reported, never hidden
            failed += 1
            rows.append({"case": case_id, "family": family, "error": str(failure)})
            continue
        rows.append({"case": case_id, "family": family, "observed": path,
                     "terminal_status": observed.get("terminal_status"),
                     "status": observed.get("_status")})
    sys.stdout.write(json.dumps({"cases": rows, "failed": failed, "out": os.path.abspath(args.out)},
                                indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
