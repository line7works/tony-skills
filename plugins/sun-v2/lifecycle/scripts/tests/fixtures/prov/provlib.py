"""Slice 3's test side, as the join (slice 5) leaves it: the fixture machine wired to the four providers' fakes, and a
drive in a child process with the same wiring (for the kill sweeps of all three lanes).

Nothing here is a lane's row and nothing here stands in for one: every lane reads the shipped `lane.json` files, which
hold slice 3's rows since the join, and every provider declaration is the shipped one. `wire` adds this lane's fakes to a
fixture machine whatever else it holds (slice 2's programs, slice 4's): the fake `gh`, `vercel`, `psql` and `pg_dump` in a
folder of his, the fake `curl` and the system's own git in a system folder of the fixture's own (so that no real curl and no
network is ever reached), git's own user-level file naming the fake GitHub's bare repositories in place of
https://github.com/, the frame's own requests answered by `VercelAPI`, and the hosting token in the session.
"""
import json
import os
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.dirname(TESTS)
ROWS = os.path.join(os.path.dirname(SCRIPTS), "rows")
FAKE = os.path.join(TESTS, "fakes", "prov_fake.py")
ME = os.path.abspath(__file__)
for p in (TESTS, os.path.join(TESTS, "fakes")):
    if p not in sys.path:
        sys.path.insert(0, p)

import harness  # noqa: E402
import killlib  # noqa: E402
import prov_fake  # noqa: E402
from sun_core import facts as factsmod  # noqa: E402

TEAM = "fixture-team"
ACCOUNT = "fixture-account"
PROGRAMS = ("gh", "vercel", "psql", "pg_dump")
TOKEN = "VERCEL_TOKEN"


def shipped(*parts):
    with open(os.path.join(ROWS, *parts)) as fh:
        return json.load(fh)


def providers():
    """Every shipped declaration under the plugin's `lifecycle/rows/providers/`, as it stands."""
    folder = os.path.join(ROWS, "providers")
    return dict((name[:-5], shipped("providers", name)) for name in sorted(os.listdir(folder)) if name.endswith(".json"))


def wrapper(path, line):
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\n" + line + "\n")
    os.chmod(path, 0o755)


def wire(machine, token=None):
    """This lane's fakes added to the fixture machine (the module's docstring). The machine's own system folders are kept,
    but the system's real ones, which hold a real curl: the fixture's system folder of this lane stands in their place."""
    programs = os.path.join(machine.root, "prov-programs-" + machine.seed.replace("/", "_"))
    system = os.path.join(machine.root, "prov-system-" + machine.seed.replace("/", "_"))
    for folder in (programs, system):
        os.makedirs(folder, exist_ok=True)
    for tool in PROGRAMS:
        wrapper(os.path.join(programs, tool), "exec /usr/bin/python3 -B '%s' %s \"$@\"" % (FAKE, tool))
    wrapper(os.path.join(system, "curl"), "exec /usr/bin/python3 -B '%s' curl \"$@\"" % FAKE)
    wrapper(os.path.join(system, "git"), 'exec /usr/bin/git "$@"')
    kept = tuple(f for f in machine.system_folders if f not in factsmod.SYSTEM_FOLDERS and f != system)
    machine.system_folders = kept + (system,)
    folders = [f for f in machine.settings.get("program_folders") or [] if f != programs]
    machine.settings["program_folders"] = folders + [programs]
    machine.settings["accounts"].update({"github": [ACCOUNT], "vercel": [TEAM]})
    machine.write_settings()
    remotes = os.path.join(machine.home, ".fakes", "gh", "remotes")
    os.makedirs(remotes, exist_ok=True)
    os.makedirs(os.path.join(machine.home, ".config", "git"), exist_ok=True)
    # git's own user-level file under `~/.config` (outside what the kill sweep compares; it holds this machine's path); the
    # identity git commits as is the fixture's own `~/.gitconfig`, where a test writes one (slice 2's SR00 reads it)
    with open(os.path.join(machine.home, ".config", "git", "config"), "w") as fh:
        fh.write('[url "%s/"]\n\tinsteadOf = https://github.com/\n[init]\n\tdefaultBranch = main\n' % remotes)
    machine.token = token or getattr(machine, "token", None) or harness.canary("vercel-token")
    machine.env[TOKEN] = machine.token
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
    return repo, git(repo, "rev-parse", "HEAD")


def remote_head(machine, name="demo", ref="refs/heads/main"):
    return prov_fake.remote_ref(ACCOUNT, name, ref, machine.home)


ALL_ENVS = ["development", "preview", "production"]


def sunset_world(m, values=None, tables=None, custom=None):
    """What a sunset finds at the providers: the project's repository pushed to the fake GitHub with its origin's main
    fetched; the project at the host, linked from the repository, with its variables; the database the env file names, with
    a canary password. (Slice 4's layers of this machine are its own fixture's: `test_lane_set_lib.plant`.)"""
    repo, commit = project_repo(m)
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
    os.makedirs(os.path.join(repo, ".vercel"))                      # what slice 2's SR10 left (ignored)
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


# ---- a drive in a child process, with this wiring (the kill sweeps of all three lanes) --------------------------------
class Machine(harness.Machine):
    """A fixture machine whose real-kill drive is this file's child, wired as `wire` wires it: the fixture's system folders,
    the fake host of the frame's own requests, and the session's hosting token."""

    def drive(self, *argv, **kw):
        self.drives += 1
        env = dict(kw.get("env") or {})
        env.setdefault(TOKEN, self.env.get(TOKEN))
        config = {"root": self.root, "name": self.name, "seed": "%s/drive-%d" % (self.seed, self.drives),
                  "rows_root": self.rows_root, "kill_at": kw.get("kill_at"), "torn": bool(kw.get("torn")),
                  "events": kw.get("events"), "env": env, "clock": self.clock + 1000 * self.drives,
                  "system": list(self.system_folders)}
        path = os.path.join(self.root, "drive-%s-%d.json" % (self.seed.replace("/", "_"), self.drives))
        with open(path, "w") as fh:
            json.dump(config, fh)
        environ = dict(os.environ)
        environ["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run([sys.executable, ME, "--drive", path] + [str(a) for a in argv], env=environ, cwd=self.root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        return harness.Result(proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8"), [], proc.returncode == -9)


def child(config_path, argv):
    """`tests/drive.py`'s `main`, with this wiring: the fixture's system folders, the fake host of the frame's own requests
    (state on disk, so the child and the parent see one host), and the session's token."""
    with open(config_path) as fh:
        config = json.load(fh)
    machine = harness.Machine(config["root"], config["name"], config["seed"], create=False)
    machine.rows_root = config.get("rows_root")
    machine.clock = int(config.get("clock") or 0)
    machine.env.update(dict((k, v) for k, v in (config.get("env") or {}).items() if v is not None))
    machine.system_folders = tuple(config["system"])
    machine.transport = prov_fake.VercelAPI(machine.home, machine.env.get(TOKEN))
    sink = os.open(config["events"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600) if config.get("events") else None
    recorder = harness.Recorder(sink)
    recorder.torn = bool(config.get("torn"))
    machine.recorder = recorder
    world = machine.world()
    world.output = harness.worldmod.Output()
    if config.get("kill_at") is not None:
        seen = {"n": -1}

        def boundary(event):
            if event["stage"] in ("pre", "mid", "post"):
                seen["n"] += 1
                return seen["n"] == config["kill_at"]
            return False
        recorder.kill_at = boundary
        recorder.on_kill = lambda event: os.kill(os.getpid(), signal.SIGKILL)
    import sun
    return sun.start(argv, world)


class Sweep(killlib.Sweep):
    """`killlib.Sweep` over machines of this module's `Machine` kind (or the subclass a lane gives), each wired by `wire`
    before the lane's own preparation, and the hosting token in every invocation's session."""

    def __init__(self, test, tmp, prepare, token, machine_kind=None, **kw):
        self.token = token
        self.machine_kind = machine_kind or Machine
        killlib.Sweep.__init__(self, test, tmp, prepare, **kw)

    def fresh(self, label):
        machine = self.machine_kind(os.path.join(self.tmp, label), "home", "sweep")
        wire(machine, self.token)
        self.prepare(machine)
        self.env = dict(self.env, **{TOKEN: self.token})
        return machine


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--drive":
        sys.exit(child(sys.argv[2], sys.argv[3:]))
