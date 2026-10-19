"""Shared library of the E16 seeded cases over the frame's fake rows (the lane contract's section 12; slice 1).

A case is a fixture machine under `--out/<case>/`, built by its family's `build.py`, and a list of steps
that `observe.py` drives through the real command line on fakes. `case.json` beside the machine holds the
steps; it states no outcome. The fixture machine, the fake providers' tool and the fake rows are the test
suite's own (`lifecycle/scripts/tests/`): a seeded case and a test stand on the same fakes.

Standard library only, as the tool itself is (A47). A canary is built when the case
is built and lives only under `--out`.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TESTS = os.path.join(PLUGIN, "lifecycle", "scripts", "tests")
sys.path.insert(0, TESTS)

import harness  # noqa: E402
import rowlib  # noqa: E402

GUARDED = (os.path.join("~", ".claude"), os.path.join("~", ".codex"))


def refuse_out(out):
    real = os.path.realpath(out)
    for guard in GUARDED:
        base = os.path.realpath(os.path.expanduser(guard))
        if real == base or real.startswith(base + os.sep):
            sys.stderr.write("--out may not be, or sit under, a harness's own home\n")
            sys.exit(2)


def canary(case, tag):
    return "sunv2canary" + hashlib.sha256(("%s:%s:%d" % (case, tag, os.getpid())).encode()).hexdigest()[:20]


def machine(out, case, create=True):
    return harness.Machine(os.path.join(out, case), "home", case, create=create)


# ---- the fixtures a case is built from -----------------------------------------------------------------------
def clean(m, facts):
    rowlib.install(m, rowlib.clean_lane())
    m.put("shortcuts.txt", "alias other\n")
    m.put("dev/demo-scope.md", "scope\n")


def credentials(m, facts):
    """The reference rows with an env pull and a database keep: every source SEC-1 names holds a canary."""
    pull = rowlib.build("E1", "remote", place=rowlib.path(rowlib.DEV, "demo.pulled.env"), output="env file")
    pull["construction"] = {"id": "C1", "builder": "pull", "out_param": "out", "single_file": True, "mode": 0o600}
    pull["commands"] = [rowlib.use("pull", "fakehost.write")]
    place = pull["thing"]["place"]
    pull["after_test"] = [{"read": "path", "path": place, "is": "file"}]
    pull["after_check"] = [{"read": "path", "path": place, "is": "file"}, {"read": "mode", "path": place, "at_most": 0o600},
                           {"read": "line", "path": place, "line": {"text": [rowlib.lit("FIXTURE_URL="), {"input": "answers.unused"}]}, "present": False}]
    pull["after_check"] = pull["after_check"][:2]
    rows = rowlib.clean_rows() + [pull, rowlib.keep("P1", "remote"), rowlib.secret_op("X1", "remote")]
    rowlib.install(m, rowlib.lane("sunrise", rows, phases=("prepare", "remote")))
    case = facts["case"]
    facts["token"] = canary(case, "token")
    facts["password"] = "pw" + canary(case, "password")
    facts["address"] = "postgres://appuser:%s@db.fixture.invalid:5432/appdb" % facts["password"]
    facts["env_value"] = canary(case, "env")
    facts["dump_data"] = canary(case, "dump")
    facts["owner_line"] = "alias " + canary(case, "owner")
    m.put("shortcuts.txt", facts["owner_line"] + "\n")
    m.put("dev/demo-scope.md", "scope\n")
    m.put("dev/demo.env", "DATABASE_URL=%s\n" % facts["address"], 0o600)
    m.set_fake("fakehost", secret=facts["env_value"], things={})
    m.set_fake("fakedump", secret=facts["dump_data"])
    facts["env"] = {"FAKEHOST_TOKEN": facts["token"]}


def owner_step(m, facts):
    rowlib.install(m, rowlib.lane("sunrise", [rowlib.build("B1"), rowlib.owner_step("O1", mode="read back")]))
    m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "db", "state": "active", "name": "demo"}})


FIXTURES = {"clean": clean, "credentials": credentials, "owner-step": owner_step}


def plant(m, facts, what):
    """One planted condition, by its name. Each is a fact about the fixture, not an outcome."""
    kind = what["plant"]
    if kind in JOINED_PLANTS:
        return JOINED_PLANTS[kind](m, facts, what)
    if kind == "no-vault":
        shutil.rmtree(m.vault)
    elif kind == "stub-vault":
        os.remove(os.path.join(m.vault, harness.VAULT_MARKER))
    elif kind == "no-projects-folder":
        os.rmdir(os.path.join(m.vault, harness.VAULT_PROJECTS))
    elif kind == "synced-vault":
        synced = os.path.join(m.home, harness.SYNCED, "vault")
        os.makedirs(os.path.dirname(synced))
        os.rename(m.vault, synced)
        m.settings["vault"]["path"] = synced
        m.write_settings()
    elif kind == "fake-plan":
        entry = dict(what["entry"])
        if entry.get("value") == "<canary>":
            entry["value"] = facts.setdefault("echo", canary(facts["case"], "echo"))
        m.plan_fake(what["tool"], entry)
    elif kind == "missing-tool":
        facts.setdefault("env", {})["PATH"] = "/usr/bin:/bin"
    elif kind == "debug-variable":
        facts.setdefault("env", {}).update({"FAKEHOST_DEBUG": "1", "DEBUG": "*"})
    elif kind == "linked-output":
        os.rename(m.dev, m.dev + "-real")
        os.symlink(m.dev + "-real", m.dev)
    else:
        raise SystemExit("unknown plant: %s" % kind)


def make_family(family, cases):
    parser = argparse.ArgumentParser(description="Build the %s seeded cases under --out." % family)
    parser.add_argument("--out", default=None)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        for case in cases:
            print(case)
        return 0
    if not args.out:
        parser.error("--out is required")
    refuse_out(args.out)
    for case, spec in cases.items():
        folder = os.path.join(args.out, case)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)
        facts = {"case": case, "family": family}
        if spec.get("fixture"):
            m = machine(args.out, case)
            FIXTURES[spec["fixture"]](m, facts)
            for what in spec.get("plants") or []:
                plant(m, facts, what)
            facts["rows_root"] = m.rows_root
        with open(os.path.join(folder, "case.json"), "w") as fh:
            json.dump({"case": case, "family": family, "fixture": spec.get("fixture"), "drive": spec.get("drive") or [], "facts": facts},
                      fh, indent=1, sort_keys=True)
    print(json.dumps({"family": family, "built": sorted(cases), "out": os.path.abspath(args.out)}))
    return 0


# ---- the joined lanes (the join's part J2): the families L0, L2, L3, L5, L7 and L8 ---------------------------------------
# A case of these families is built on the join's one fixture machine (`tests/test_join_sequence.seed`): the three lanes as
# they ship, every shipped declaration, and every lane's fakes (slice 2's scaffolders and recorded git, slice 3's `gh`,
# `vercel`, `psql`, `pg_dump`, `curl` and the fake host of the frame's own requests, slice 4's schedule tools and adapter).
# What the fixture machine holds only in memory (the system folders the fakes stand in, the hosting token, the fake host) is
# kept in `case.json` under `wiring`, and `joined_machine` gives it back when `observe.py` drives the case.
JOINED = ("joined",)
JOINED_NAMES = ("demo", "demo")                      # --also, as the join's sequence gives them
JOINED_CAPS = ("canary", "memory stores", "routines")


def join_sequence():
    import test_join_sequence  # noqa: E402  (the join's fixture; it brings the lanes' helpers onto the path)
    return test_join_sequence


def joined(m, facts):
    """The join's sequence's machine before any run, and the project's own memory store (as the sequence makes it)."""
    js = join_sequence()
    js.seed(m)
    os.makedirs(js.store(m))
    with open(os.path.join(js.store(m), "MEMORY.md"), "w") as fh:
        fh.write("# memory\n")
    facts["wiring"] = {"system_folders": list(m.system_folders), "token": m.token}
    facts["password"] = m.password
    pg = js.provlib.state(m, "pg")
    facts["held"] = {"identity": pg.get("identity"), "tables": sorted(pg.get("tables") or {})}    # for the observation's scan


FIXTURES["joined"] = joined


def joined_machine(out, case, facts):
    """The case's fixture machine as `observe.py` drives it: its wiring given back (`joined`'s note)."""
    js = join_sequence()
    m = harness.Machine(os.path.join(out, case), "home", case, create=False)
    m.rows_root = facts.get("rows_root")
    m.system_folders = tuple(facts["wiring"]["system_folders"])
    m.token = facts["wiring"]["token"]
    m.env[js.provlib.TOKEN] = m.token
    m.transport = js.provlib.prov_fake.VercelAPI(m.home, m.token)
    return m


def _put(m, facts, what):
    m.put(what["rel"], what["text"], int(what.get("mode", "644"), 8))
    if what.get("note_sha256_as"):
        facts[what["note_sha256_as"]] = hashlib.sha256(what["text"].encode("utf-8")).hexdigest()


def _program_on_login_path(m, facts, what):
    m.put(os.path.join("opt", "pm", "bin", what["name"]), "#!/bin/sh\n", 0o755)
    m.put(".zprofile", "path+=(%s)\n" % m.path("opt", "pm", "bin"))


def _provider_state(m, facts, what):
    join_sequence().provlib.put_state(m, what["provider"], **what["fields"])


def _provider_plan(m, facts, what):
    join_sequence().provlib.plan(m, what["provider"], *what["entries"])


def _provider_thing_gone(m, facts, what):
    provlib = join_sequence().provlib
    state = provlib.state(m, what["provider"])
    del state["things"][what["name"]]
    provlib.prov_fake.save_at(m.home, what["provider"], state)


def _remote_with_a_commit(m, facts, what):
    """A repository of the project's name at the fake GitHub, with another's commit on its main."""
    provlib = join_sequence().provlib
    bare = provlib.prov_fake.remote(provlib.ACCOUNT, "demo", m.home)
    os.makedirs(os.path.dirname(bare), exist_ok=True)
    provlib.git(m.home, "init", "-q", "--bare", bare)
    other = m.path("other")
    os.makedirs(other)
    provlib.git(other, "init", "-q")
    m.put("other/x.txt", "another's\n")
    provlib.git(other, "add", "-A")
    provlib.git(other, "commit", "-q", "-m", "another's")
    provlib.git(other, "push", "-q", bare, "main")
    provlib.put_state(m, "gh", account=provlib.ACCOUNT,
                      things={"demo": {"id": "R_another1", "kind": "repo", "state": "active", "name": "demo"}})


def _committed_secret(m, facts, what):
    """His folder at the project's place, a repository on main whose one commit holds a value of its env file."""
    provlib = join_sequence().provlib
    facts["leak"] = canary(facts["case"], "leak")
    repo = m.path("dev", "demo")
    os.makedirs(repo)
    provlib.git(repo, "init", "-q")
    m.put("dev/demo/notes.txt", "his notes %s\n" % facts["leak"])
    m.put("dev/demo/.gitignore", ".env*\n")
    provlib.git(repo, "add", "-A")
    provlib.git(repo, "commit", "-q", "-m", "his")
    m.put("dev/demo/.env.local", "DATABASE_URL=%s\n" % facts["leak"], 0o600)


def _tag_push_refused(m, facts, what):
    """The fake GitHub's repository refuses every tag pushed to it (a hook of the bare repository's own)."""
    provlib = join_sequence().provlib
    hook = os.path.join(provlib.prov_fake.remote(provlib.ACCOUNT, "demo", m.home), "hooks", "pre-receive")
    with open(hook, "w") as fh:
        fh.write("#!/bin/sh\nwhile read old new ref; do case $ref in refs/tags/*) echo 'tags are refused here' >&2; exit 1;; "
                 "esac; done\nexit 0\n")
    os.chmod(hook, 0o755)


def _edit_text(m, facts, what):
    path = m.path(what["rel"])
    with open(path) as fh:
        text = fh.read()
    with open(path, "w") as fh:
        fh.write(text.replace(what["old"], what["new"], 1))


def _schedule_layers(m, facts, what):
    """The set lane's schedule layers for the project, as its own fixture plants them (`test_lane_set_lib.plant`): a launch
    agent naming the project's folder and another's, both loaded; a crontab with another's line and the project's; two
    routines of the adapter, one naming the project's folder. Planted once the project's folder stands (after a sunrise)."""
    setlib = join_sequence().setlib
    repo = m.path("dev", "demo")
    m.put("agents/com.fixture.demo.plist", setlib.PLIST % ("com.fixture.demo", os.path.join(repo, "run.sh")))
    m.put("agents/com.fixture.other.plist", setlib.PLIST % ("com.fixture.other", "/elsewhere/run.sh"))
    setlib.fake_state(m, "launchctl", loaded=["com.fixture.demo", "com.fixture.other"])
    setlib.fake_state(m, "crontab", table="0 1 * * * other\n5 * * * * %s/run.sh\n" % repo)
    setlib.fake_state(m, "sun-adapter", routines={
        "r-one": {"text": "nightly build in %s" % repo, "state": "active", "definition": "nightly build, every night\n"},
        "r-two": {"text": "nightly build elsewhere", "state": "active", "definition": "elsewhere\n"}})


def _dump_of_another_database(m, facts, what):
    """The fake `pg_dump` alone, in the case's own program folder, first turns the fake database into another one (another
    identity, another table) and then dumps it: the inventory read before it sees the database the project names (the
    reviewer's probe, J2-3)."""
    provlib = join_sequence().provlib
    helper = os.path.join(m.root, "dump-of-another-database.py")
    with open(helper, "w") as fh:
        fh.write("import json, os, runpy\n"
                 "path = os.path.join(os.environ['HOME'], '.fakes', 'pg', 'state.json')\n"
                 "state = json.load(open(path))\nstate.update(%s)\njson.dump(state, open(path, 'w'))\n"
                 "runpy.run_path(%r, run_name='__main__')\n" % (repr(what["becomes"]), provlib.FAKE))
    programs = os.path.join(m.root, "prov-programs-" + m.seed.replace("/", "_"))
    provlib.wrapper(os.path.join(programs, "pg_dump"), "exec /usr/bin/python3 -B '%s' pg_dump \"$@\"" % helper)


JOINED_PLANTS = {"put": _put, "program-on-login-path": _program_on_login_path, "provider-state": _provider_state,
                 "provider-plan": _provider_plan, "provider-thing-gone": _provider_thing_gone,
                 "remote-with-a-commit": _remote_with_a_commit, "committed-secret": _committed_secret,
                 "tag-push-refused": _tag_push_refused, "edit-text": _edit_text, "schedule-layers": _schedule_layers,
                 "dump-of-another-database": _dump_of_another_database}
