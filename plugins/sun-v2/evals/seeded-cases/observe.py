#!/usr/bin/env python3
"""observe.py: drives the seeded cases of sun-v2's lifecycle frame and prints what it observed.

    python3 observe.py --out DIR (--all | --case ID [--case ID ...])

`--out` is the folder the families' `build.py` built into. For each case it reads `case.json`, drives its
steps through the real command line on the fakes, and prints one JSON object of facts on standard output:
the exit and the ending of every step, the lines the tool printed, the files of the fixture home with their
mode and SHA-256, the fakes' state and call records, the journal's lines. It states no outcome and grades
nothing. Side effects: it changes the fixture machines under `--out` and nothing else. Exit 0 when every
case was driven, 2 on a usage error.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_lib"))

import caselib  # noqa: E402
import harness  # noqa: E402
import killlib  # noqa: E402
import scan  # noqa: E402
import test_no_v1_import as v1scan  # noqa: E402

HIDE = (".sun-v2", ".fakes", ".config", "Library")


def files_of(m):
    out = {}
    for rel, (kind, mode, digest) in harness.tree(m.home).items():
        if rel.split(os.sep)[0] in HIDE:
            continue
        out[rel] = {"kind": kind, "mode": oct(mode), "sha256": digest}
    return out


def fakes_of(m):
    out = {}
    root = os.path.join(m.home, ".fakes")
    for tool in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        state = m.fake(tool, "state.json") or {}
        out[tool] = {"things": dict((k, {"kind": v.get("kind"), "state": v.get("state")}) for k, v in (state.get("things") or {}).items()),
                     "refs": state.get("refs") or {},
                     "calls": [c["argv"][0] for c in m.calls(tool)],
                     "changing_calls": [c["argv"][0] for c in m.calls(tool) if c["changing"]]}
    return out


def journal_of(m, run):
    return ["%s %s %s" % (r["kind"], r.get("op") or "-", r.get("step") or r.get("status") or r.get("answer") or r.get("ending") or r.get("probe") or "-")
            for r in m.journal(run)] if run else []


def said(result):
    return {"exit": result.code, "ending": result.ending, "lines": [line.replace(caselib_root, "<OUT>") for line in result.lines],
            "killed": result.killed, "forms": len((result.doc or {}).get("forms") or [])}


caselib_root = ""


def observe(out, case):
    global caselib_root
    caselib_root = os.path.realpath(out)
    with open(os.path.join(out, case, "case.json")) as fh:
        spec = json.load(fh)
    facts = spec["facts"]
    seen = {"case": case, "family": spec["family"], "steps": []}
    if not spec.get("fixture"):
        for step in spec["drive"]:
            if step["do"] == "v1scan":
                root = harness.PLUGIN
                if step.get("plant"):
                    import shutil
                    root = os.path.join(out, case, "copy")
                    shutil.rmtree(root, True)
                    shutil.copytree(harness.PLUGIN, root, ignore=shutil.ignore_patterns("__pycache__"))
                    with open(os.path.join(root, step["plant"]["rel"]), "a") as fh:
                        fh.write("".join(step["plant"]["text_parts"]))
                found = v1scan.findings(root)
                seen["steps"].append({"do": "v1scan", "v1_findings_present": bool(found), "v1_finding_count": len(found)})
        return seen
    m = caselib.machine(out, case, create=False)
    m.rows_root = facts.get("rows_root")
    env = facts.get("env") or {}
    looked, run, results = None, None, []
    before = harness.tree(m.home)
    for step in spec["drive"]:
        do = step["do"]
        row = {"do": do}
        if do == "look":
            looked = m.look(step.get("name", "demo"), step.get("kind", "sunrise"), env=env)
            run = (looked.doc or {}).get("run")
            results.append(looked)
            row.update(said(looked))
            row["manifest_written"] = bool(run and os.path.exists(os.path.join(m.facts.run_dir(run), "manifest-1.json")))
            row["home_unchanged"] = harness.tree(m.home) == before
            row["cue_calls"] = list(m.cue_calls)
        elif do == "go":
            kill = None
            if step.get("kill_after_journal"):
                kind, op = step["kill_after_journal"]
                kill = lambda e, kind=kind, op=op: e["op"] == "journal" and e["stage"] == "post" and e["subject"] == kind and e.get("operation") == op  # noqa: E731
            if step.get("kill_mid_append_of"):
                kind, op = step["kill_mid_append_of"]
                armed = []

                def kill(e, kind=kind, op=op, armed=armed):
                    if e["op"] == "journal" and e["stage"] == "pre" and e["subject"] == kind and e.get("operation") == op:
                        armed.append(1)
                    return bool(armed) and e["op"] == "append" and e["stage"] == "mid"
            if step.get("kill_mid_child"):
                kill = lambda e, c=step["kill_mid_child"]: e["op"] == "child" and e["stage"] == "mid" and e["subject"] == c  # noqa: E731
            m.recorder.torn = bool(step.get("torn"))
            sha = "0" * 64 if step.get("wrong_hash") else looked.doc["manifest_sha256"]
            went = m.run("go", "--kind", step.get("kind", "sunrise"), "--name", "demo", "--run", run, "--manifest-sha256", sha, env=env, kill=kill)
            results.append(went)
            row.update(said(went))
        elif do in ("status", "resume", "close"):
            more = []
            if do == "resume":
                position = (m.summon("status", env=env).doc or {}).get("position")
                more = ["--position", position if position is not None else len(m.journal(run)), "--word", "go on"]
            if do == "close":
                more = ["--word", "close"]
            result = m.summon(do, "demo", *more, env=env)
            results.append(result)
            row.update(said(result))
        elif do == "alter-manifest":
            path = os.path.join(m.facts.run_dir(run), "manifest-1.json")
            doc = json.load(open(path))
            if step.get("inject"):
                doc["operations"].append(dict(doc["operations"][0], id="INJECTED"))
            else:
                doc["inputs"]["description"] = "changed after the go"
            with open(path, "w") as fh:
                json.dump(doc, fh)
            os.chmod(path, 0o600)
        elif do == "link-at-the-env-files-place":
            target = os.path.join(m.home, "elsewhere.txt")
            os.symlink(target, os.path.join(m.dev, "demo.pulled.env"))
            row["link_planted"] = True
        elif do == "owner-acts":
            things = m.fake("fakehost", "state.json")["things"]
            things["demo"]["state"] = "connected"
            m.set_fake("fakehost", things=things)
        elif do == "second-summons-while-held":
            close = m.hold_lock("demo", run or "sunrise-" + "0" * 16)
            try:
                result = m.look("demo", env=env)
            finally:
                close()
            results.append(result)
            row.update(said(result))
        elif do == "sweep":
            sweep = killlib.Sweep(type("T", (), {"assertEqual": staticmethod(lambda a, b, c=None: None), "assertTrue": staticmethod(lambda a, b=None: None)})(),
                                  os.path.join(out, case, "sweep"), lambda mm: caselib.FIXTURES[spec["fixture"]](mm, dict(facts)))
            failures = sweep.everywhere()
            row.update({"kill_points": sweep.ran["kill_points"], "recorded": sweep.ran["recorded"], "outcomes": sweep.ran["outcomes"],
                        "failures": failures, "reference_statuses": sweep.statuses})
        seen["steps"].append(row)
    seen["files"] = files_of(m)
    seen["fakes"] = fakes_of(m)
    seen["journal"] = journal_of(m, run)
    seen["open_runs"] = len(m.open_runs())
    seen["lock_files"] = len(m.lock_names())
    seen["run_directories"] = len(m.run_ids())
    if spec["family"].startswith("L4"):
        values = [(facts[k], []) for k in ("token", "env_value", "dump_data", "owner_line", "echo") if facts.get(k)]
        values.append((facts["address"], [facts["password"], "appuser:" + facts["password"]]))
        values += [(v, []) for v in scan.issued(m)]
        m.secret_places = tuple(os.path.join(m.dev, n) for n in ("demo.env", "demo.pulled.env", "demo-dump.txt"))
        m.owner_files = (m.path("shortcuts.txt"),)
        found = scan.scan(m, values, results)
        seen["scan_findings"] = [where.replace(caselib_root, "<OUT>") for where, _what in found]
        seen["values_scanned_for"] = len(values)
        seen["session_names_a_fake_was_given"] = sorted(set(n for tool in ("fakehost", "fakegit", "fakedump") for c in m.calls(tool)
                                                           for n in c["env_names"] if n in ("FAKEHOST_DEBUG", "DEBUG", "FAKEHOST_TOKEN")))
        own = m.fake("fakehost", "own.log", None)
        seen["canary_in_the_fakes_own_log"] = bool(own)
        seen["written_through_the_link"] = os.path.exists(os.path.join(m.home, "elsewhere.txt"))
        seen["secret_files"] = dict((n, {"present": os.path.exists(os.path.join(m.dev + ("-real" if os.path.islink(m.dev) else ""), n)),
                                         "mode": oct(os.stat(os.path.join(m.dev, n)).st_mode & 0o777) if os.path.exists(os.path.join(m.dev, n)) else None,
                                         "holds_its_canary": os.path.exists(os.path.join(m.dev, n)) and
                                         facts[key] in open(os.path.join(m.dev, n)).read()})
                                    for n, key in (("demo.pulled.env", "env_value"), ("demo-dump.txt", "dump_data")))
    return seen


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    cases = sorted(d for d in os.listdir(args.out) if os.path.isfile(os.path.join(args.out, d, "case.json"))) if args.all else args.case
    if not cases:
        parser.error("name a case with --case, or give --all")
    print(json.dumps({"observed": [observe(args.out, case) for case in cases]}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
