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
