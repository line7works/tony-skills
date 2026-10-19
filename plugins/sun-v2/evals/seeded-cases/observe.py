#!/usr/bin/env python3
"""observe.py: drives the seeded cases of sun-v2's lifecycle frame and prints what it observed.

    python3 observe.py --out DIR (--all | --case ID [--case ID ...])

`--out` is the folder the families' `build.py` built into. For each case it reads `case.json`, drives its
steps through the real command line on the fakes, and prints one JSON object of facts on standard output:
the exit and the ending of every step, the lines the tool printed, the files of the fixture home with their
mode and SHA-256, the fakes' state and call records, the journal's lines. It states no outcome and grades
nothing. Side effects: it changes the fixture machines under `--out` and nothing else. Exit 0 when every
case was driven, 2 on a usage error, 3 when a case's observation holds a secret or held value of its machine (the joined
families' SEC-11 scan): nothing is printed on standard output, and standard error names the case and the value's name.
"""
import argparse
import hashlib
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
    if spec.get("fixture") in caselib.JOINED:
        return observe_joined(out, case, spec)
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


# ---- the joined lanes (the join's part J2): the families L0, L2, L3, L5, L7 and L8 ---------------------------------------
# A case on the joined lanes is driven through the real command line in-process on its fixture machine (`caselib.joined`),
# each summons as the join's sequence makes it (`--also demo --also demo` and the harness's capabilities file). What is
# printed is facts: every step's ending and lines, the forms the tool printed, each run's statuses and journal, the files of
# the fixture home (a repository's own `.git` left out; its state is read with git), the fakes' states and call records, and
# a `named` block of the facts each family's row in section 12 names (heads, the address's answer, the env file's key names
# as a comparison, the checks' answers, the lines present and how often, the git record, the keeps, the schedules).
# No held or protected value is copied (the join's J2c, D8; the owner's design step, "Reuse the tool's own scanner"): a field
# a declaration holds (the database's identity and tables, a provider's ids, the host's env keys, a routine's id) appears by
# its name only, as a comparison or a count; a file's text is printed only for the layer files the evidence names, every
# other file by its mode and SHA-256. Then the whole observation, before anything is printed, goes through the SEC-11
# scanner (`tests/scan.py`), fed every secret and held value the case's machine holds, each in the scanner's own forms; a hit
# stops it, naming the case and the value's name, and prints nothing of the value (`Disclosed`).
LANE_HIDE = (".sun-v2", ".fakes", ".config", "Library")
TEXT_LIMIT = 16384
NAMED_TEXT = (os.path.join("dev", "demo"), os.path.join("dev", "_archive", "demo"))
KIT_FILES = ("AGENTS.md", "CLAUDE.md", "README.md", ".gitignore", ".env.example", "vercel.json", os.path.join("public", "index.html"))
LEAST_LENGTH = 8             # the frame's least length of a kept value (SEC-4's eight bytes): shorter ones are kept out by shape
PROJECT_PLACES = (os.path.join("dev", "demo"), os.path.join("dev", "_archive", "demo"))
LINES = {"root index, active": "- [[projects/demo/_index|demo]]", "root index, archived": "- [[archive/demo/_index|demo]]"}


def named_text(rel):
    """Whether a file's text is printed: the layer files the evidence names, and the staged documents and launch agents of
    the fixture. Every other file is printed by its mode and SHA-256 only."""
    parts = rel.split(os.sep)
    for project in NAMED_TEXT:
        if rel.startswith(project + os.sep):
            inside = rel[len(project) + 1:]
            return inside in KIT_FILES or (inside.startswith("docs" + os.sep) and inside.endswith(".md"))
    if parts[0] == "vault":
        return rel == os.path.join("vault", "_index.md") or parts[1:3] in (["projects", "demo"], ["archive", "demo"])
    return rel in (os.path.join("memory", "MEMORY.md"), os.path.join("memory", "project_demo.md"), "shortcuts.txt") \
        or parts[0] == "staged" or (parts[0] == "agents" and rel.endswith(".plist"))


def lane_files(m):
    out = {}
    for rel, (kind, mode, digest) in sorted(harness.tree(m.home).items()):
        parts = rel.split(os.sep)
        if parts[0] in LANE_HIDE or ".git" in parts:
            continue
        entry = {"kind": kind, "mode": oct(mode), "sha256": digest}
        full = os.path.join(m.home, rel)
        if kind == "file" and named_text(rel) and os.path.getsize(full) <= TEXT_LIMIT:
            try:
                with open(full) as fh:
                    entry["text"] = fh.read()
            except UnicodeDecodeError:
                pass
        out[rel] = entry
    return out


def git_of(repo):
    js = caselib.join_sequence()

    def ask(*args):
        try:
            return js.provlib.git(repo, *args)
        except AssertionError:
            return None
    return {"main": ask("rev-parse", "--verify", "-q", "refs/heads/main"), "current_branch": ask("rev-parse", "--abbrev-ref", "HEAD"),
            "subjects": (ask("log", "--format=%s", "main") or "").split("\n") if ask("rev-parse", "--verify", "-q", "refs/heads/main") else [],
            "origin": ask("config", "--local", "--get", "remote.origin.url"),
            "main_upstream": ask("rev-parse", "--abbrev-ref", "main@{upstream}"),
            "tracked": sorted((ask("ls-files") or "").split("\n")) if ask("ls-files") else [],
            "status_porcelain": ask("status", "--porcelain")}


def remote_of(m):
    js = caselib.join_sequence()
    bare = js.provlib.prov_fake.remote(js.provlib.ACCOUNT, "demo", m.home)
    if not os.path.isdir(bare):
        return None
    refs = js.provlib.git(m.home, "--git-dir", bare, "for-each-ref", "--format=%(refname) %(objectname)")
    return dict(line.split(" ", 1) for line in refs.split("\n") if line)


def env_keys(path):
    if not os.path.isfile(path):
        return None
    with open(path) as fh:
        return [line.split("=", 1)[0] for line in fh.read().split("\n") if "=" in line and not line.startswith("#")]


def env_file_keys(m, project):
    """The env file's key names as a comparison with the keys the fake host holds for the project's development environment
    (the keys are held: never copied), and their count."""
    keys = env_keys(os.path.join(project, ".env.local")) if project else None
    if keys is None:
        return None
    host = caselib.join_sequence().provlib.state(m, "vercel")
    development = [e["key"] for e in (host.get("envs") or {}).get("demo", []) if not e.get("custom") and "development" in (e.get("target") or [])]
    return {"count": len(keys), "equal to the host's development keys": sorted(keys) == sorted(development)}


def schedules_of(m):
    """The schedule layers by name (the join's J2c, J2-2): the launch agents' files and the labels the fake launchd holds
    loaded, the fake crontab's table (its SHA-256, its lines, those naming the project's folder), each routine of the fake
    adapter by its place in id order (its id is held: never copied), and every call of the schedule fakes, by its words."""
    folder = m.path("agents")
    plists = sorted(n for n in os.listdir(folder) if n.endswith(".plist")) if os.path.isdir(folder) else []
    table = (m.fake("crontab", "state.json") or {}).get("table") or ""
    project = m.path("dev", "demo")
    routines = (m.fake("sun-adapter", "state.json") or {}).get("routines") or {}
    calls = {}
    for tool in ("plutil", "launchctl", "crontab", "sun-adapter"):
        words = [" ".join("<path>" if a.startswith(os.sep) else a for a in c["argv"][:2]) for c in m.calls(tool)]
        if words:
            calls[tool] = words
    return {"launch agent files": len(plists), "plists": plists,
            "loaded labels": sorted((m.fake("launchctl", "state.json") or {}).get("loaded") or []),
            "crontab lines": len([x for x in table.split("\n") if x]), "crontab lines naming the project": len([x for x in table.split("\n") if project + "/" in x]),
            "crontab sha256": hashlib.sha256(table.encode("utf-8")).hexdigest() if table else None,
            "routines": [{"state": routines[k].get("state"), "names the project": project in (routines[k].get("text") or "")} for k in sorted(routines)],
            "calls": calls}


def provider_facts(m):
    js = caselib.join_sequence()
    provlib = js.provlib
    gh, host, pg = provlib.state(m, "gh"), provlib.state(m, "vercel"), provlib.state(m, "pg")
    return {"github": {"things": dict((n, {"state": t.get("state"), "private": t.get("private")}) for n, t in (gh.get("things") or {}).items()),
                       "sets": gh.get("sets") or [], "calls": [c.get("command") for c in provlib.calls(m, "gh")]},
            "hosting": {"things": dict((n, {"kind": t.get("kind"), "state": t.get("state"), "repo": t.get("repo")})
                                       for n, t in (host.get("things") or {}).items()),
                        "resources": dict((n, {"connected": r.get("connected"), "project": r.get("project")})
                                          for n, r in (host.get("resources") or {}).items()),
                        "env_key_count": dict((slug, len(envs)) for slug, envs in (host.get("envs") or {}).items()),
                        "sets": host.get("sets") or [],
                        "cli_calls": [c.get("command") for c in provlib.calls(m, "vercel") if "request" not in c],
                        "requests": ["%s %s" % (c["request"], "/".join(c["path"][:2])) for c in provlib.requests(m)]},
            "database": {"identity_present": pg.get("identity") is not None, "table_count": len(pg.get("tables") or {}),
                         "calls": [c.get("command") for c in provlib.calls(m, "pg")]},
            "web": {"calls": [c["argv"][-1] for c in provlib.calls(m, "web")]}}


def tool_calls(m):
    out = {}
    for tool in ("git", "npx", "npm", "uv", "python3", "sun-adapter"):
        calls = m.calls(tool)
        if calls:
            out[tool] = {"calls": len(calls), "changing": [c["argv"] for c in calls if c.get("changing")]}
    return out


def journal_lines(m, run):
    out = []
    for r in m.journal(run):
        line = [r["kind"], r.get("op") or "-"]
        for key in ("status", "answer", "step", "ending", "ground"):
            if r.get(key) is not None:
                line.append("%s=%s" % (key, r[key]))
        if r["kind"] == "attempt" and r.get("safe"):
            line.append("safe=%s" % json.dumps(r["safe"], sort_keys=True))
        if r.get("keep"):
            line.append("keep size=%s sha256=%s" % (r["keep"].get("size"), r["keep"].get("sha256")))
        if isinstance(r.get("way_back"), dict) and r["kind"] in ("completion", "status"):
            line.append("way_back=%s" % ("offered" if r["way_back"].get("offered") else "none: %s" % r["way_back"].get("reason")))
        out.append(" ".join(line))
    return out


def manifest_facts(m, run):
    path = os.path.join(m.facts.run_dir(run), "manifest-1.json") if run else None
    if not path or not os.path.exists(path):
        return {"manifest_written": False}
    with open(path) as fh:
        doc = json.load(fh)
    return {"manifest_written": True,
            "operations": ["%s %s" % (o["id"], o.get("planning_outcome")) for o in doc.get("operations") or []],
            "repo_commands": dict((o["id"], o["repo_commands"]) for o in doc.get("operations") or [] if isinstance(o.get("repo_commands"), list)),
            "not_applicable": ["%s: %s" % (n.get("row"), n.get("reason")) for n in doc.get("not_applicable") or []],
            "already_so": [a.get("row") if isinstance(a, dict) else a for a in doc.get("already_so") or []]}


def forms_of(result):
    out = {}
    for path in (result.doc or {}).get("forms") or []:
        with open(path) as fh:
            out[os.path.basename(path)] = fh.read().split("\n")
    return out


def named_facts(m, facts, runs):
    """The facts section 12's rows name, each by its name (the module's note above)."""
    project = next((os.path.join(m.home, p) for p in PROJECT_PLACES if os.path.isdir(os.path.join(m.home, p, ".git"))), None)
    local = git_of(project) if project else None
    attempts, keeps, address = {}, {}, []
    for run in runs:
        for r in m.journal(run):
            if r["kind"] == "attempt":
                attempts.setdefault(r["op"], []).append(r.get("answer"))
                if r["op"] == "SR16":
                    address.append(r.get("safe"))
            if r["kind"] == "completion" and r.get("keep"):
                keeps[r["op"]] = {"size": r["keep"].get("size"), "sha256": r["keep"].get("sha256"),
                                  "at_its_place_sha256": (r.get("observed") or {}).get("sha256")}
    texts = {}
    for label, rel in (("vault root index", os.path.join("vault", "_index.md")), ("memory index", os.path.join("memory", "MEMORY.md")),
                       ("shortcut file", "shortcuts.txt")):
        full = m.path(rel)
        texts[label] = open(full).read().split("\n") if os.path.isfile(full) else None
    shortcut = 'alias dm="cd %s"' % m.path("dev", "demo")
    counts = dict((label, (texts["vault root index"] or []).count(line)) for label, line in LINES.items())
    counts["memory index, the project's line"] = len([x for x in texts["memory index"] or [] if "(project_demo.md)" in x])
    counts["shortcut file, the project's line"] = (texts["shortcut file"] or []).count(shortcut)
    js = caselib.join_sequence()
    pushes = [c["argv"] for c in m.calls("git") if "push" in c["argv"]]
    return {"project_folder": os.path.relpath(project, m.home) if project else None,
            "local_main": (local or {}).get("main"), "local_git": local, "remote_refs": remote_of(m),
            "address_answers": address,
            "env_file_keys": env_file_keys(m, project),
            "check_answers": attempts,
            "lines_present": counts,
            "git_state_changing_calls": js.rise.git_writes(m),
            "git_pushes": len(pushes),
            "scaffolder_calls": dict((t, [c["argv"] for c in m.calls(t) if c["argv"][:1] in (["--yes"], ["create"], ["init"])])
                                     for t in ("npx", "npm", "uv") if m.calls(t)),
            "keeps": keeps,
            "schedules": schedules_of(m),
            "staged_source_sha256": dict((k, v) for k, v in facts.items() if k.startswith("sha256 of ")),
            "vault_folder": [p for p in (os.path.join("vault", "projects", "demo"), os.path.join("vault", "archive", "demo"))
                             if os.path.isdir(m.path(p))],
            "sunset_folders": sorted(n for n in (os.listdir(m.path("dev", "_archive")) if os.path.isdir(m.path("dev", "_archive")) else [])
                                     if ".sunset-" in n)}


def joined_kill(m, run, spec):
    """The case's kill, by a recorded event (the harness's in-process kill): after an operation's start record is on disk,
    after its final status is on disk, or at a named act on a path."""
    if not spec:
        return None
    if spec.get("after_start_of"):
        op = spec["after_start_of"]
        return lambda e: e["op"] == "append" and e["stage"] == "post" and op in [r["op"] for r in m.journal(run) if r["kind"] == "start"]
    if spec.get("after_status"):
        op, status = spec["after_status"]
        return lambda e: e["op"] == "append" and e["stage"] == "post" and m.statuses(run).get(op) == status
    return lambda e: e["stage"] == spec["stage"] and e["op"] == spec["act"] and str(e["subject"]).endswith(spec["subject_endswith"])


def lane_inputs(m, step):
    js = caselib.join_sequence()
    given = dict(step.get("inputs") or {})
    if step.get("kind", "sunrise") == "sunrise":
        if given.pop("adopt", False):
            given["adopt"] = {"project folder": m.path("dev", "demo")}
        given.setdefault("description", js.DESCRIPTION)
        for old, new in (("type", "type_"),):
            if old in given:
                given[new] = given.pop(old)
        return js.rise.sunrise_inputs(m, **given)
    return js.set_inputs(m, **given)


def observe_joined(out, case, spec):
    facts = spec["facts"]
    m = caselib.joined_machine(out, case, facts)
    seen = {"case": case, "family": spec["family"], "steps": []}
    looks, runs = {}, []
    for step in spec["drive"]:
        do, kind = step["do"], step.get("kind", "sunrise")
        row = {"do": do, "kind": kind}
        result = None
        if do == "look":
            caps = tuple(step.get("caps") or caselib.JOINED_CAPS)
            result = m.look("demo", kind, also=caselib.JOINED_NAMES, inputs=lane_inputs(m, step), caps=caps)
            run = (result.doc or {}).get("run")
            looks[kind] = (result, caps)
            if run and run not in runs:
                runs.append(run)
            row.update(manifest_facts(m, run))
            row["capabilities"] = list(caps)
        elif do in ("go", "resume", "status"):
            looked, caps = looks.get(kind, (None, caselib.JOINED_CAPS))
            if looked is None or not (looked.doc or {}).get("manifest_sha256"):
                row["not_driven"] = "the look of this case gave no manifest to go on"
            elif do == "go":
                result = m.go(looked, "demo", kind, also=caselib.JOINED_NAMES, caps=caps,
                              kill=joined_kill(m, looked.doc["run"], step.get("kill")))
            elif do == "resume":
                result = m.resume(also=caselib.JOINED_NAMES, caps=caps)
            else:
                result = m.summon("status", "demo", also=caselib.JOINED_NAMES, caps=caps)
        elif do == "plant":
            caselib.plant(m, facts, step["what"])
            row["planted"] = step["what"]["plant"]
        elif do == "snapshot":
            row["label"] = step["label"]
            row["files"] = lane_files(m)
            row["providers"] = provider_facts(m)
            row["named"] = named_facts(m, facts, runs)
        if result is not None:
            row.update({"exit": result.code, "ending": result.ending, "lines": result.lines, "killed": result.killed,
                        "forms": forms_of(result)})
            run = (result.doc or {}).get("run")
            if not run and looks.get(kind):
                run = (looks[kind][0].doc or {}).get("run")
            if run:
                row["run_kind"] = run.split("-")[0]
                row["statuses"] = m.statuses(run)
        seen["steps"].append(row)
    seen["files"] = lane_files(m)
    seen["providers"] = provider_facts(m)
    seen["programs"] = tool_calls(m)
    seen["journals"] = dict((run, journal_lines(m, run)) for run in runs)
    seen["named"] = named_facts(m, facts, runs)
    seen["open_runs"] = len(m.open_runs())
    seen["lock_files"] = len(m.lock_names())
    seen["run_directories"] = len(m.run_ids())
    text = json.dumps(seen, sort_keys=True)
    for root in sorted(set((os.path.realpath(out), os.path.abspath(out))), key=len, reverse=True):
        text = text.replace(root, "<OUT>")
    seen = json.loads(text)
    seen["values_scanned_for"] = screened(m, facts, case, text)
    return seen


class Disclosed(Exception):
    """A secret or held value of the case's machine found in its observation: the observation stops (D8)."""


class _NoHome(object):
    """The scanner's machine for an observation alone: a home that does not exist, so that `scan.scan` reads only the
    observation it is given as its one result."""
    home = os.path.join(os.sep, "nonexistent-observation-home")


class _Text(object):
    def __init__(self, text):
        self.out, self.err = text, ""


def literals(root):
    """Every text of the shipped rows and declarations the case installs: a value that is one of the tool's own literals is
    safe content (SEC-1), never a held value of the machine's."""
    found = set()

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            found.add(node)
    for base, _dirs, files in os.walk(root or ""):
        for name in files:
            if name.endswith(".json"):
                with open(os.path.join(base, name)) as fh:
                    walk(json.load(fh))
    return found


def secrets_and_held(m, facts):
    """[(name, value, components)]: every secret and held value the case's machine holds, by a name that tells nothing of it.
    Secrets: the database password, the hosting token, a planted leak, every env value at the fake host (a connection
    address with its password and its user and password pair as components, SEC-12). Held: the database's identity and its
    tables (at the build and now), every id the fake providers hold for a thing, every env key at the host, every value a
    fake issued. Each of the frame's least length or more, and none of the shipped rows' own texts."""
    import urllib.parse
    js = caselib.join_sequence()
    provlib = js.provlib
    out = [("the database password", facts.get("password"), ()), ("the hosting token", (facts.get("wiring") or {}).get("token"), ()),
           ("the planted leak", facts.get("leak"), ())]
    host, gh, pg = provlib.state(m, "vercel"), provlib.state(m, "gh"), provlib.state(m, "pg")
    for n, item in enumerate(e for envs in (host.get("envs") or {}).values() for e in envs):
        value = item.get("value") or ""
        parts = urllib.parse.urlsplit(value) if "://" in value else None
        components = (parts.password, "%s:%s" % (parts.username, parts.password)) if parts and parts.password else ()
        out.append(("a hosting env value (#%d)" % (n + 1), value, components))
        out.append(("a hosting env key (#%d)" % (n + 1), item.get("key"), ()))
    held = facts.get("held") or {}
    out.append(("the database identity at the build", held.get("identity"), ()))
    out.append(("the database identity", pg.get("identity"), ()))
    out.append(("the database password at the fake database", pg.get("password"), ()))
    for n, name in enumerate(sorted(set(list(held.get("tables") or []) + list(pg.get("tables") or {})))):
        out.append(("a table name of the database (#%d)" % (n + 1), name, ()))
    for label, state in (("a GitHub id", gh), ("a hosting id", host)):
        things = list((state.get("things") or {}).values()) + list((state.get("resources") or {}).values())
        for n, value in enumerate(sorted(set(v for t in things for k, v in t.items() if k in ("id", "account") and isinstance(v, str)))):
            out.append(("%s (#%d)" % (label, n + 1), value, ()))
    for n, value in enumerate(scan.issued(m)):
        out.append(("an issued value (#%d)" % (n + 1), value, ()))
    shipped = literals(m.rows_root)
    return [(name, value, components) for name, value, components in out
            if isinstance(value, str) and len(value.strip().encode("utf-8")) >= LEAST_LENGTH
            and not any(value in literal for literal in shipped)]


def screened(m, facts, case, text):
    """The SEC-11 scan of the observation (`tests/scan.py`'s own `scan`, its forms its `needles`), one value at a time so
    that a hit can be named; returns how many values were looked for. A hit raises `Disclosed` with the case and the name."""
    values = secrets_and_held(m, facts)
    for name, value, components in values:
        if scan.scan(_NoHome(), [(value, list(components))], [_Text(text)]):
            raise Disclosed("case %s: %s" % (case, name))
    return len(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    cases = sorted(d for d in os.listdir(args.out) if os.path.isfile(os.path.join(args.out, d, "case.json"))) if args.all else args.case
    if not cases:
        parser.error("name a case with --case, or give --all")
    try:
        observed = [observe(args.out, case) for case in cases]
    except Disclosed as found:
        sys.stderr.write("observation stopped: %s is in the observation (SEC-11's scan); nothing of it is printed\n" % found)
        return 3
    print(json.dumps({"observed": observed}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
