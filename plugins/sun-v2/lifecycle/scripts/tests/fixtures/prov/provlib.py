"""Slice 3's test side: the fixture machine wired to the four providers' fakes, the lane built from slice 3's shipped
files and the other lanes' stand-ins, and a drive in a child process with the same wiring (for the kill sweep).

Nothing here is a lane's row. The stand-ins give, by the providing lane's names and fields (rows-prov section 7), the
outputs slices 2 and 4 give; the control room replaces every one at the join (slice 5). The four provider declarations
are the shipped ones, with no stand-in: vercel's request route `team` takes his settings' names by G23-4, and its runner
route `cli-team` takes the same one name into `/v2/teams/<team>` and `--scope <team>` by G24-2's `text` part.
"""
import copy
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.dirname(TESTS)
ROWS = os.path.join(os.path.dirname(SCRIPTS), "rows")
FAKE = os.path.join(TESTS, "fakes", "prov_fake.py")
for p in (TESTS, os.path.join(TESTS, "fakes")):
    if p not in sys.path:
        sys.path.insert(0, p)

import harness  # noqa: E402
import rowlib  # noqa: E402
import prov_fake  # noqa: E402

L = rowlib.lit
TEAM = "fixture-team"
ACCOUNT = "fixture-account"
PROGRAMS = ("gh", "vercel", "psql", "pg_dump")
SET_PHASES = ("keeping", "retiring on this machine", "retiring at the providers", "the last record")
RESTORE_PHASES = ("putting back on this machine", "putting back at the providers", "starting again", "the last record")
RK18 = "carried under v1's own risk for this step (RK18): {what}"


def shipped(*parts):
    with open(os.path.join(ROWS, *parts)) as fh:
        return json.load(fh)


def providers():
    """Slice 3's four shipped declarations, as they stand (G23-4 and G24-2 fill vercel's two identity reads with each name
    his settings hold for vercel)."""
    return dict((name, shipped("providers", name + ".json")) for name in ("github", "vercel", "postgres", "web"))


def wrapper(path, line):
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\n" + line + "\n")
    os.chmod(path, 0o755)


def wire(machine, token=None):
    """The fixture machine wired to the fakes: a folder of his (on his settings' list) holding gh, vercel, psql and
    pg_dump; the fixture's system folder holding git (the real one, by its full path) and curl (the fake), so that no
    real curl and no network is reached; his git configuration naming the fake GitHub's bare repositories in place of
    https://github.com/; the frame's own requests answered by `VercelAPI`."""
    programs = os.path.join(machine.root, "prov-programs-" + machine.seed)
    system = os.path.join(machine.root, "prov-system-" + machine.seed)
    for folder in (programs, system):
        os.makedirs(folder, exist_ok=True)
    for tool in PROGRAMS:
        wrapper(os.path.join(programs, tool), "exec /usr/bin/python3 -B '%s' %s \"$@\"" % (FAKE, tool))
    wrapper(os.path.join(system, "curl"), "exec /usr/bin/python3 -B '%s' curl \"$@\"" % FAKE)
    wrapper(os.path.join(system, "git"), 'exec /usr/bin/git "$@"')
    machine.system_folders = (system,)
    machine.settings["program_folders"] = [harness.FAKES, programs]
    machine.settings["accounts"].update({"github": [ACCOUNT], "vercel": [TEAM]})
    machine.write_settings()
    remotes = os.path.join(machine.home, ".fakes", "gh", "remotes")
    os.makedirs(remotes, exist_ok=True)
    os.makedirs(os.path.join(machine.home, ".config", "git"), exist_ok=True)
    # git's own user-level file under `~/.config` (outside what the kill sweep compares; it holds this machine's path)
    with open(os.path.join(machine.home, ".config", "git", "config"), "w") as fh:
        fh.write('[url "%s/"]\n\tinsteadOf = https://github.com/\n[user]\n\temail = fixture@example.invalid\n\tname = fixture\n'
                 '[init]\n\tdefaultBranch = main\n' % remotes)
    machine.token = token or harness.canary("vercel-token")
    machine.env["VERCEL_TOKEN"] = machine.token
    machine.transport = prov_fake.VercelAPI(machine.home, machine.token)
    machine.set_fake("vercel", team=TEAM)
    return machine


def state(machine, provider):
    return prov_fake.load_at(machine.home, provider)


def put_state(machine, provider, **fields):
    found = state(machine, provider)
    found.update(fields)
    prov_fake.save_at(machine.home, provider, found)


def plan(machine, provider, *entries):
    folder = os.path.join(machine.home, ".fakes", provider)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "plan.json"), "w") as fh:
        json.dump(list(entries), fh)


def calls(machine, provider, command=None):
    path = os.path.join(machine.home, ".fakes", provider, "calls.jsonl")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        found = [json.loads(line) for line in fh if line.strip()]
    return [c for c in found if command is None or c.get("command") == command]


def requests(machine, method=None):
    return [c for c in calls(machine, "vercel") if "request" in c and (method is None or c["request"] == method)]


FIXED_DATE = "2026-01-01T00:00:00Z"


def git(repo, *args, **kw):
    """The fixture's own git, never the session's configuration: HOME is the fixture machine's home where given (its git
    config names the fake GitHub in place of https://github.com/), else a folder that does not exist."""
    env = {"PATH": "/usr/bin:/bin", "HOME": kw.get("home") or "/nonexistent-fixture-home", "GIT_AUTHOR_DATE": FIXED_DATE,
           "GIT_COMMITTER_DATE": FIXED_DATE, "GIT_CONFIG_NOSYSTEM": "1"}
    proc = subprocess.run(["/usr/bin/git", "-C", repo, "-c", "user.email=fixture@example.invalid", "-c", "user.name=fixture",
                           "-c", "init.defaultBranch=main"] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if proc.returncode != 0:
        raise AssertionError("git %s: %s" % (" ".join(args), proc.stderr.decode()))
    return proc.stdout.decode().strip()


def project_repo(machine, name="demo", files=None):
    """The project folder under his developer root with one commit on main (what slice 2's SR01 to SR07 leave)."""
    repo = machine.path("dev", name)
    os.makedirs(repo, exist_ok=True)
    git(repo, "init", "-q")
    for rel, text in sorted((files or {"README.md": "# demo\n", ".gitignore": ".env.local\n.vercel\n"}).items()):
        machine.put(os.path.join("dev", name, rel), text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "first")
    os.makedirs(os.path.join(repo, ".vercel"), exist_ok=True)       # where slice 2's SR10 writes the link file (ignored)
    return repo, git(repo, "rev-parse", "HEAD")


def forget_index(repo):
    """The repository's index removed: it holds the files' inode numbers and times, which differ on every fixture machine, and
    no row of this lane reads it (the kill sweep compares every file outside the tool's own folders byte for byte)."""
    os.remove(os.path.join(repo, ".git", "index"))


def remote_head(machine, name="demo", ref="refs/heads/main"):
    return prov_fake.remote_ref(ACCOUNT, name, ref, machine.home)


# ---- the lane: slice 3's shipped part of a kind's lane file, with stand-in rows of the other lanes ---------------------
LANE_KEYS = ("rows", "facts", "questions", "tables", "form_changes", "checklist", "present_lines", "fixed_text")


def lane(kind, standins, phases, part=None, **more):
    """A test lane: the stand-in rows first, then every entry slice 3's file for this kind gives, under the lane file's
    own key names (`lane.schema.json`), each key's entries joined to the stand-ins' (the join's copy, slice 5)."""
    part = copy.deepcopy(part if part is not None else shipped(kind, "provider-rows.json"))
    out = rowlib.lane(kind, list(standins), phases=phases)
    out["alias_reads"] = []
    out["form_changes"]["the RK18 mark"] = RK18
    for key in LANE_KEYS:
        if key not in part:
            continue
        if key == "rows":
            out["rows"] = list(standins) + part["rows"]
        elif isinstance(part[key], dict):
            out.setdefault(key, {}).update(part[key])
        else:
            out[key] = list(out.get(key) or []) + part[key]
    out.update(more)
    return out


def substitute(node, old, new):
    """`node` with every mark `{"output": old}` made `{"output": new}`."""
    if isinstance(node, list):
        return [substitute(v, old, new) for v in node]
    if isinstance(node, dict):
        if node == {"output": old}:
            return {"output": new}
        return dict((k, substitute(v, old, new)) for k, v in node.items())
    return node


def install(machine, *lanes):
    rowlib.install(machine, *lanes, providers=providers())


# stand-in rows of slices 2 and 4, each giving one output by its providing lane's name and fields
def stand_in_check(rid, phase, output, fields, needs=rowlib.NONE):
    k = rowlib.check(rid, phase, output=output, needs=needs)
    k["output"] = {"name": output, "fields": fields}
    k["form_lines"] = {"preview": "stand-in %s" % rid, "status": "stand-in %s" % rid}
    return k


def stand_in_build(rid, phase, output, fields, place, needs=rowlib.NONE, files=None):
    b = rowlib.build(rid, phase, place=place, output=output, needs=needs)
    b["construction"] = {"id": "C1", "single_file": True, "mode": 0o644,
                         "files": files or [{"rel": "x", "text": L("stand-in %s\n" % rid)}]}
    b["thing"]["tracked"] = ["exists", "identity", "sha256"]
    b["after_test"] = [{"read": "path", "path": place, "is": "file"}]
    b["after_check"] = [{"read": "path", "path": place, "is": "file"}]
    b["output"] = {"name": output, "fields": dict(fields, path=place) if "path" in fields else fields}
    b["form_lines"] = {"preview": "stand-in %s" % rid, "status": "stand-in %s" % rid}
    return b


def stand_in_adopt(rid, phase):
    """`project folder` {path}: slice 2's SR01 under `--promote`, an adopt of the folder his inputs name (OP-10)."""
    a = rowlib.adopt(rid, phase)
    a["form_lines"] = {"preview": "stand-in %s" % rid, "status": "stand-in %s" % rid}
    return a


def made(output, treatment="then not applicable", level="made"):
    return {"output": output, "level": level, "treatment": treatment}


DEV = rowlib.DEV


def rise_standins(repo, commit, link_json=True):
    """Slice 2's outputs: `project folder` {path}, `first commit` {commit}, `scanned for the push` {commit} and `hosting
    link` {path} (SR10, built from SR09's held id and account as projectId and orgId)."""
    marker = lambda n: rowlib.path(DEV, {"text": [{"input": "answers.slug"}, L("-standin-%s.txt" % n)]})   # noqa: E731
    out = [
        stand_in_adopt("SR01s", "sunrise"),
        stand_in_build("SR07s", "sunrise", "first commit", {"commit": L(commit)}, marker("sr07")),
        stand_in_check("SR14s", "sunrise", "scanned for the push", {"commit": L(commit)},
                       needs=[made("first commit")]),
    ]
    if link_json:
        link = rowlib.path(L(repo), ".vercel", "project.json")
        b = stand_in_build("SR10s", "sunrise", "hosting link", {"path": link}, link, needs=[made("hosting project")],
                           files=[{"rel": "project.json", "text": {"held_fields": {"projectId": {"output": "hosting project.id"},
                                                                                      "orgId": {"output": "hosting project.account"}}}}])
        b["thing"]["role"] = "the hosting link file (slice 2's SR10, stand-in)"
        b["content_classes"] = {"reads": ["held"], "stores": ["held"], "shows": ["safe"], "validators": [],
                                "resting_places": ["the project folder"]}
        b["construction"]["mode"] = 0o600
        out.append(b)
    return out


def rise_inputs(machine, **flags):
    every = {"github": True, "vercel": True, "db": True, "public": False}
    every.update(flags)
    return machine.inputs(answers={"repo": "demo", "slug": "demo"}, flags=every, type="web app",
                          adopt={"project folder": machine.path("dev", "demo")})


# ---- sunset and restore: slice 4's outputs by its names and fields (rows-set section 7) --------------------------------
def set_standins(tombstone=True):
    """`sunset folder` {path} (T02); `repository archived` {path} (T12, a move of the repository to the archive folder, whose
    reverse gives restore's `repository back` {path}, V01); `repository moved` (T12m, a check of the moved repository with no
    field: slice 4 gives this output as a check's, so a need on it is met at `passed`, lane-report-set item 5); and the run's
    last record (T30, the tombstone, which names the keys set apart, G23-8), left out where `tombstone` is false: it renders
    the journal, which a kill legitimately changes (KEEP-5), so the kill sweep's byte comparison takes the lane without it."""
    folder = rowlib.path({"location": "archive_root"}, {"text": [{"name": 0}, L("-sunset")]})
    t02 = rowlib.build("T02s", "keeping", place=folder, output="sunset folder")
    t02["construction"] = {"id": "C1", "mode": 0o700, "files": [{"rel": "README.md", "text": L("the sunset folder (stand-in)\n")}]}
    t02["after_check"] = [{"read": "path", "path": rowlib.path(folder, "README.md"), "is": "file"}]
    t02["form_lines"] = {"preview": "stand-in T02s", "status": "stand-in T02s"}
    repo = rowlib.path({"location": "developer_root"}, {"name": 0})
    moved = rowlib.path({"location": "archive_root"}, {"name": 0})
    t12 = rowlib.move("T12s", "retiring on this machine", source=repo, target=moved, output="repository archived")
    t12["way_back"]["reverse"].update(id="V01s", phase="putting back on this machine",
                                      output={"name": "repository back", "fields": {"path": repo}},
                                      form_lines={"preview": "stand-in V01s", "status": "stand-in V01s"})
    t12 = json.loads(json.dumps(t12).replace('"is": "file"', '"is": "dir"'))          # a folder, not a file
    t12["thing"]["role"] = "the project's repository (slice 4's T12, stand-in)"
    t12["form_lines"] = {"preview": "stand-in T12s", "status": "stand-in T12s"}
    t12["output"]["fields"] = {"path": moved}
    t12m = stand_in_check("T12ms", "retiring on this machine", "repository moved", {},
                          needs=[made("repository archived", "then not needed")])
    t12m["thing"]["place"] = moved
    t12m["thing"]["passes"] = [{"read": "path", "path": moved, "is": "dir"}]
    t30 = rowlib.last_record("T30s", "the last record", output="tombstone")
    t30["thing"]["place"] = t30["planning_test"][0]["path"] = rowlib.path(
        {"location": "archive_root"}, {"text": [{"name": 0}, L("-tombstone-"), {"run": "id"}, L(".txt")]})
    for entry in ("before_test", "after_test", "after_check"):
        t30[entry][0]["path"] = t30["thing"]["place"]
    t30["output"]["fields"]["path"] = t30["thing"]["place"]
    t30["form_lines"] = {"preview": "stand-in T30s", "status": "stand-in T30s"}
    return [t02, t12, t12m] + ([t30] if tombstone else [])


def tombstone(m, run):
    """The stand-in T30's record of the run (the tombstone)."""
    with open(os.path.join(m.archive, "demo-tombstone-%s.txt" % run)) as fh:
        return fh.read()


ALL_ENVS = ["development", "preview", "production"]


def sunset_world(m, values=None, tables=None, custom=None):
    """What a sunset finds: the project's repository pushed to the fake GitHub with its origin's main fetched; the project at
    the host, linked from the repository, with its variables; the database the env file names, with a canary password."""
    repo, commit = project_repo(m)
    os.makedirs(m.archive, exist_ok=True)                    # his archive folder, where slice 4's T02 and T12 write
    bare = os.path.join(m.home, ".fakes", "gh", "remotes", ACCOUNT, "demo.git")
    os.makedirs(os.path.dirname(bare), exist_ok=True)
    git(m.home, "init", "-q", "--bare", bare)
    git(repo, "remote", "add", "origin", "https://github.com/%s/demo.git" % ACCOUNT)     # his git config names the fake's
    git(repo, "push", "-q", "origin", "main", home=m.home)          # which also records the remote's main as origin/main
    put_state(m, "gh", account=ACCOUNT, things={"demo": {"id": "R_fixturerepo1", "kind": "repo", "state": "active", "name": "demo"}})
    password = harness.canary("db-password")
    with open(os.path.join(repo, ".env.local"), "w") as fh:
        fh.write('DATABASE_URL="postgres://fixture:%s@db.invalid:5432/demo"\n' % password)
    os.chmod(os.path.join(repo, ".env.local"), 0o600)
    with open(os.path.join(repo, ".vercel", "project.json"), "w") as fh:
        json.dump({"projectId": "prj_fixture1", "orgId": "team_fixture1"}, fh)
    envs = values if values is not None else [
        {"key": "DATABASE_URL", "value": "postgres://fixture:%s@db.invalid:5432/demo" % password, "type": "encrypted", "target": ALL_ENVS},
        {"key": "FEATURE", "value": "on", "type": "plain", "target": ALL_ENVS},
        {"key": "SIGNING_KEY", "value": harness.canary("sensitive"), "type": "sensitive", "target": ALL_ENVS}]
    put_state(m, "vercel", team=TEAM, hidden=0,
              things={"demo": {"id": "prj_fixture1", "kind": "project", "state": "active", "name": "demo", "account": "team_fixture1",
                               "repo": "demo"}},
              envs={"demo": envs}, custom={"demo": custom or []})
    put_state(m, "pg", password=password, identity="7000000000000000001",
              tables=tables if tables is not None else {"alpha": ["1", "2"], "beta": ["x"]}, unreadable=[])
    return repo, commit, password


def set_inputs(m, **flags):
    every = {"keep_github": False, "keep_vercel": False, "keep_db": False}
    every.update(flags)
    return m.inputs(answers={"repo": "demo", "slug": "demo"}, flags=every)


def set_lane(part=None, extra=(), tombstone=True):
    return lane("sunset", set_standins(tombstone) + list(extra), SET_PHASES, part=part)


def restore_lane():
    return lane("restore", [], RESTORE_PHASES)
