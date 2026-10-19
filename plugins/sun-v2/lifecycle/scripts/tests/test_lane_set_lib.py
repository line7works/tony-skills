"""Slice 4's test helpers (sunset and restore): no tests here.

The lane's own files are read as they ship, from the plugin's `lifecycle/rows/`; since the join (slice 5) the sunset lane
holds slice 3's rows too, and no stand-in is left. Three things are the tests' own:

- the tools. Every declaration of this lane's providers (launchd, cron, the adapter) is installed with its tool renamed
  `fixture-<tool>`, whose wrapper in a folder of the fixture's own starts `fakes/set_tools.py`. No real `plutil`,
  `launchctl`, `crontab` or harness adapter is ever on a test's search list under the name a declaration uses, so no test
  can reach the real launchd, the real crontab or a real harness. Slice 3's declarations (`github`, `vercel`, `postgres`,
  `web`) are installed as they ship, and `provlib.wire` puts their fakes on the search list (git is the system's own, on
  the test's own repository).
- the fixture machine: the locations rows-set C11 names, a project with every layer, and the fakes' states, slice 3's world
  among them (`provlib.sunset_world`: the repository pushed to the fake GitHub, the project at the fake host, the database).
- the inputs: rows-set's alone (since the join's J1b, item 5, slice 3's rows read the dropped layers and the names).
"""
import copy
import json
import os
import re
import sys

import harness
import rowlib

sys.path.insert(0, os.path.join(harness.TESTS, "fixtures", "prov"))
import provlib  # noqa: E402

LIFECYCLE = harness.LIFECYCLE
# the lane's files as they ship; `SUN_V2_SET_ROWS` names another folder of the same shape, for a mutation copy's red only
ROWS = os.environ.get("SUN_V2_SET_ROWS") or os.path.join(LIFECYCLE, "rows")
SET_TOOLS = os.path.join(harness.FAKES, "set_tools.py")
TOOLS = ("plutil", "launchctl", "crontab", "sun-adapter")
OWN = ("launchd", "cron", "adapter")
# the repository folder, the vault folder (the slug, as sunrise names it and as slice 3's rows read it, place 1: the
# join's J1b item 5) and the memory note's stem
NAMES = ("demo", "demo", "demo_notes")
ALSO = NAMES[1:]
CAPS = ("memory stores", "routines")
DESCRIPTION = "a fixture project, retired"
L = rowlib.lit


def read_json(*parts):
    with open(os.path.join(*parts)) as fh:
        return json.load(fh)


def shipped_lane(kind):
    return read_json(ROWS, kind, "lane.json")


def shipped_providers():
    return dict((name, read_json(ROWS, "providers", name + ".json")) for name in OWN)


def renamed(decl):
    """A declaration with every command's tool renamed `fixture-<tool>` (the module's docstring)."""
    out = copy.deepcopy(decl)
    for command in out["commands"].values():
        command["tool"] = "fixture-" + command["tool"]
    return out


def providers():
    """Every shipped declaration, this lane's three with their tools renamed (the module's docstring)."""
    out = dict((name[:-5], read_json(ROWS, "providers", name)) for name in sorted(os.listdir(os.path.join(ROWS, "providers")))
               if name.endswith(".json"))
    for name, decl in shipped_providers().items():
        out[name] = renamed(decl)
    return out


def programs(machine):
    """The fixture's own folder of the fakes' wrappers, put on his settings' list of program folders."""
    folder = os.path.join(machine.root, "set-programs-" + machine.seed.replace("/", "_"))
    os.makedirs(folder, exist_ok=True)
    for tool in TOOLS:
        with open(os.path.join(folder, "fixture-" + tool), "w") as fh:
            fh.write("#!/bin/sh\nexec /usr/bin/python3 -B '%s' %s \"$@\"\n" % (SET_TOOLS, tool))
        os.chmod(os.path.join(folder, "fixture-" + tool), 0o755)
    machine.settings["program_folders"] = list(machine.settings.get("program_folders") or []) + [folder]
    return folder


def locations(machine):
    home = machine.home
    machine.settings["locations"].update({
        "vault_root": machine.vault, "vault_projects": os.path.join(machine.vault, "projects"),
        "vault_archive": os.path.join(machine.vault, "archive"), "vault_projects_rel": "projects",
        "vault_archive_rel": "archive", "vault_index": os.path.join(machine.vault, "_index.md"),
        "memory_home": os.path.join(home, "mem", "home"), "memory_projects": os.path.join(home, "mem", "projects"),
        "launch_agents": os.path.join(home, "agents"), "shortcut_root_text": machine.dev})


def store_of(machine):
    """The project's own memory store, as the machine-facts module resolves it (E16-12)."""
    return os.path.join(machine.home, "mem", "projects", re.sub(r"[^A-Za-z0-9]", "-", machine.path("dev", "demo")), "memory")


PLIST = ('<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0">\n<dict>\n<key>Label</key>\n<string>%s</string>\n'
         '<key>ProgramArguments</key>\n<array><string>%s</string></array>\n</dict>\n</plist>\n')


def plant(machine, shortcut="dm", **world):
    """A project with every layer the lane retires, and the fakes' states; slice 3's world by `provlib.sunset_world`, with
    `world` its arguments (values, tables, custom)."""
    m = machine
    repo = m.path("dev", "demo")
    m.world_made = provlib.sunset_world(m, **world)        # the repository (README.md `# demo`), the hosting project, the database
    m.put("vault/projects/demo/_index.md", "---\ntitle: demo\nstatus: active\n---\n# demo\nsee [[projects/demo/plan]]\n")
    m.put("vault/projects/demo/plan.md", "the plan, from [[projects/demo/_index]]\n")
    m.put("vault/notes/elsewhere.md", "links [[projects/demo/_index]] and [[archive/old/_index]]\n")
    m.put("vault/notes/unrelated.md", "nothing here\n")
    m.put("vault/_index.md", "# Index\n## Active\n- [[projects/demo/_index|demo]]\n- [[projects/other/_index|other]]\n")
    m.put("mem/home/project_demo_notes.md", "---\nname: demo\ndescription: the demo\n---\nnotes\n")
    m.put("mem/home/MEMORY.md", "- [Demo](project_demo_notes.md) the demo\n- [Other](project_other.md) other\n")
    store = os.path.relpath(store_of(m), m.home)
    m.put(os.path.join(store, "MEMORY.md"), "# memory\n")
    m.put(os.path.join(store, "notes", "one.md"), "one\n")
    m.put("agents/com.fixture.demo.plist", PLIST % ("com.fixture.demo", os.path.join(repo, "run.sh")))
    m.put("agents/com.fixture.other.plist", PLIST % ("com.fixture.other", "/elsewhere/run.sh"))
    m.put("shortcuts.txt", 'alias other="cd /elsewhere"\nalias %s="cd %s"\n' % (shortcut, repo))
    fake_state(m, "launchctl", loaded=["com.fixture.demo", "com.fixture.other"])
    fake_state(m, "crontab", table="0 1 * * * other\n5 * * * * %s/run.sh\n" % repo)
    fake_state(m, "sun-adapter", routines={
        "r-one": {"text": "nightly build in %s" % repo, "state": "active", "definition": "nightly build, every night\n"},
        "r-two": {"text": "nightly build elsewhere", "state": "active", "definition": "elsewhere\n"}})


def fake_state(machine, tool, **fields):
    folder = os.path.join(machine.home, ".fakes", tool)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "state.json")
    state = {}
    if os.path.exists(path):
        with open(path) as fh:
            state = json.load(fh)
    state.update(fields)
    with open(path, "w") as fh:
        json.dump(state, fh, indent=1, sort_keys=True)


def fake(machine, tool):
    return machine.fake(tool, "state.json") or {}


def calls(machine, tool):
    return machine.fake(tool, "calls.jsonl", []) or []


def install(machine, sunset_extra=(), restore_extra=(), sunset_lane=None, restore_lane=None, decls=None):
    """The rows root of the fixture: the lane's files as they ship (slice 3's rows in them since the join)."""
    sunset = sunset_lane or shipped_lane("sunset")
    sunset["rows"] = list(sunset["rows"]) + list(sunset_extra)
    restore = restore_lane or shipped_lane("restore")
    restore["rows"] = list(restore["rows"]) + list(restore_extra)
    return rowlib.install(machine, sunset, restore, providers=decls or providers())


def machine(case, label="m", shortcut="dm", plant_it=True, kind=None, **world):
    m = (kind or harness.Machine)(case.tmp, label, label)
    prepare(m, shortcut, plant_it, **world)
    return m


def prepare(m, shortcut="dm", plant_it=True, **world):
    """The fixture machine of this lane: its programs and locations, slice 3's fakes (`provlib.wire`), the project, the
    shipped lanes."""
    programs(m)
    locations(m)
    m.write_settings()
    provlib.wire(m)
    if plant_it:
        plant(m, shortcut, **world)
    install(m)
    return m


def inputs(m, **more):
    """rows-set's inputs: his reason, and what `more` gives (flags, dropped layers)."""
    fields = {"description": DESCRIPTION}
    fields.update(more)
    return m.inputs("inputs-%s.json" % len(os.listdir(m.root)), **fields)


def look(m, kind="sunset", caps=CAPS, **more):
    return m.look(NAMES[0], kind, also=ALSO, inputs=inputs(m, **more), caps=list(caps) if caps is not None else None)


def go(m, looked, kind="sunset", caps=CAPS, **kw):
    return m.go(looked, NAMES[0], kind, also=ALSO, caps=list(caps) if caps is not None else None, **kw)


def run(case, m, kind="sunset", ending="complete", caps=CAPS, **more):
    looked = look(m, kind, caps, **more)
    case.assertEqual(looked.ending, "preview", looked.text)
    went = go(m, looked, kind, caps)
    if ending is not None:
        case.assertEqual(went.ending, ending, went.text)
    return looked, went


def manifest(m, run_id, number=1):
    return read_json(m.facts.run_dir(run_id), "manifest-%d.json" % number)


def form(result, name):
    for path in (result.doc or {}).get("forms") or []:
        if os.path.basename(path).startswith(name + "-"):
            with open(path) as fh:
                return fh.read()
    preview = (result.doc or {}).get("preview")
    if name == "preview" and preview:
        with open(preview) as fh:
            return fh.read()
    return None


def read(m, *parts):
    with open(m.path(*parts)) as fh:
        return fh.read()
