"""Slice 4's test helpers (sunset and restore): no tests here.

The lane's own files are read as they ship, from the plugin's `lifecycle/rows/`. Three things are the tests' own:

- the tools. Every declaration of the lane's providers (launchd, cron, the adapter) and the stand-in of slice 3's git reads
  is installed with its tool renamed `fixture-<tool>`, whose wrapper in a folder of the fixture's own starts
  `fakes/set_tools.py`. No real `plutil`, `launchctl`, `crontab`, harness adapter or `git` is ever on a test's search
  list under the name a declaration uses, so no test can reach the real launchd, the real crontab or a real harness.
- the stand-ins of slice 3 (the brief's section 1): its git declaration (`fixtures/set/standin-git.json`, the three reads
  rows-set section 7 asks for) and its rows by its names and fields, `tag scan`, `sunset tag` {ref, commit}, `dump`
  {path}, `hosting env production` {path}, `archived repository`, `paused project`, `restored repository`, `live project`,
  in the phases rows-set section 7 gives them. The control room replaces each at the join.
- the fixture machine: the locations rows-set C11 names, a project with every layer, and the fakes' states.
"""
import copy
import json
import os
import re

import harness
import rowlib

LIFECYCLE = harness.LIFECYCLE
# the lane's files as they ship; `SUN_V2_SET_ROWS` names another folder of the same shape, for a mutation copy's red only
ROWS = os.environ.get("SUN_V2_SET_ROWS") or os.path.join(LIFECYCLE, "rows")
SET_TOOLS = os.path.join(harness.FAKES, "set_tools.py")
FIXTURES = os.path.join(harness.TESTS, "fixtures", "set")
TOOLS = ("plutil", "launchctl", "crontab", "sun-adapter", "git")
NAMES = ("demo", "demo-vault", "demo_notes")
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
    return dict((name, read_json(ROWS, "providers", name + ".json")) for name in ("launchd", "cron", "adapter"))


def renamed(decl):
    """A declaration with every command's tool renamed `fixture-<tool>` (the module's docstring)."""
    out = copy.deepcopy(decl)
    for command in out["commands"].values():
        command["tool"] = "fixture-" + command["tool"]
    return out


def providers():
    out = rowlib.providers()
    for name, decl in shipped_providers().items():
        out[name] = renamed(decl)
    out["git"] = renamed(read_json(FIXTURES, "standin-git.json"))
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


def plant(machine, shortcut="dm"):
    """A project with every layer the lane retires, and the fakes' states."""
    m = machine
    repo = m.path("dev", "demo")
    m.put("dev/demo/README.md", "# demo\n")
    m.put("vault/projects/demo-vault/_index.md", "---\ntitle: demo\nstatus: active\n---\n# demo\nsee [[projects/demo-vault/plan]]\n")
    m.put("vault/projects/demo-vault/plan.md", "the plan, from [[projects/demo-vault/_index]]\n")
    m.put("vault/notes/elsewhere.md", "links [[projects/demo-vault/_index]] and [[archive/old/_index]]\n")
    m.put("vault/notes/unrelated.md", "nothing here\n")
    m.put("vault/_index.md", "# Index\n## Active\n- [[projects/demo-vault/_index|demo]]\n- [[projects/other/_index|other]]\n")
    m.put("mem/home/project_demo_notes.md", "---\nname: demo-vault\ndescription: the demo\n---\nnotes\n")
    m.put("mem/home/MEMORY.md", "- [Demo](project_demo_notes.md) the demo\n- [Other](project_other.md) other\n")
    store = os.path.relpath(store_of(m), m.home)
    m.put(os.path.join(store, "MEMORY.md"), "# memory\n")
    m.put(os.path.join(store, "notes", "one.md"), "one\n")
    m.put("agents/com.fixture.demo.plist", PLIST % ("com.fixture.demo", os.path.join(repo, "run.sh")))
    m.put("agents/com.fixture.other.plist", PLIST % ("com.fixture.other", "/elsewhere/run.sh"))
    m.put("shortcuts.txt", 'alias other="cd /elsewhere"\nalias %s="cd %s"\n' % (shortcut, repo))
    m.set_fake("fakehost", things={"demo": {"id": "t1", "kind": "repo", "state": "active", "name": "demo"},
                                   "demo-host": {"id": "t2", "kind": "project", "state": "active", "name": "demo-host"}})
    fake_state(m, "launchctl", loaded=["com.fixture.demo", "com.fixture.other"])
    fake_state(m, "crontab", table="0 1 * * * other\n5 * * * * %s/run.sh\n" % repo)
    fake_state(m, "sun-adapter", routines={
        "r-one": {"text": "nightly build in %s" % repo, "state": "active", "definition": "nightly build, every night\n"},
        "r-two": {"text": "nightly build elsewhere", "state": "active", "definition": "elsewhere\n"}})
    fake_state(m, "git", clean=True, untracked=False, unpushed=0)


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


# ---- slice 3's stand-in rows, by its names and fields (rows-prov 3.3, 3.4; rows-set section 7) -------------------------
def _check(rid, phase, output, fields, needs="none", passes=None):
    k = rowlib.check(rid, phase, output=output)
    k["output"] = {"name": output, "fields": fields}
    k["thing"]["passes"] = passes or [{"read": "path", "path": rowlib.DEV, "is": "dir"}]
    k["needs"] = needs
    k["form_lines"] = {"preview": "stand-in of slice 3's %s" % rid, "status": "stand-in of slice 3's %s" % rid}
    return k


def _provider_change(rid, back_id, name, before, after, output, back_output, needs, back_needs, back_phase):
    forward = rowlib.refusing(rid, "retiring at the providers", name=L(name), before=before, after=after, construction="C6",
                              output=output, needs=needs)
    forward["thing"].update({"retires": True, "where": "provider"})
    forward["keeps_required"] = []
    forward["form_lines"] = {"preview": "stand-in of slice 3's %s" % rid, "status": "stand-in of slice 3's %s" % rid}
    back = rowlib.refusing(back_id, back_phase, name=L(name), before=after, after=before, construction="C6", output=back_output,
                           needs=back_needs)
    back["way_back"] = {"none": "the row declares none: it is itself a reverse"}
    back["form_lines"] = {"preview": "stand-in of slice 3's %s" % back_id, "status": "stand-in of slice 3's %s" % back_id}
    forward["way_back"] = {"reverse": back}
    forward["reverse_inputs"] = [{"read": "value", "value": L(name), "type": "values", "label": "the thing's name"}]
    return forward


def standin_rows():
    sf = {"output": "sunset folder.path"}
    made = lambda o, t="then not applicable": [{"output": o, "level": "made", "treatment": t}]      # noqa: E731
    state = lambda o, t="then not needed": [{"output": o, "level": "state", "treatment": t}]       # noqa: E731
    passed = lambda o, t="then not needed": [{"output": o, "level": "passed", "treatment": t}]     # noqa: E731
    return [
        _check("T01s", "keeping", "tag scan", {"commit": L("stand-in-commit")}),
        _check("T01", "keeping", "sunset tag", {"ref": L("refs/tags/sunset-stand-in"), "commit": L("stand-in-commit")},
               needs=[{"output": "tag scan", "level": "passed", "treatment": "then not applicable"}]),
        _check("T03", "keeping", "dump", {"path": rowlib.path(sf, "demo-db.sql")}, needs=made("sunset folder"),
               passes=[{"read": "path", "path": sf, "is": "dir"}]),
        _check("T04-production", "keeping", "hosting env production", {"path": rowlib.path(sf, "hosting-env.production")},
               needs=made("sunset folder"), passes=[{"read": "path", "path": sf, "is": "dir"}]),
        # rows-set section 7: T20 needs `repository archived`, made; slice 3's own rows name `repository moved` (state), which
        # a check of this lane provides and which ORD-1 meets only at `passed` (the report's seam finding)
        _provider_change("T20", "V10", "demo", "active", "archived", "archived repository", "restored repository",
                         made("repository archived", "then not needed") + passed("sunset tag"), state("repository back"),
                         "putting back at the providers"),
        _provider_change("T21", "V11", "demo-host", "active", "paused", "paused project", "live project",
                         passed("repository moved"), state("restored repository"), "putting back at the providers"),
    ]


def install(machine, sunset_extra=(), restore_extra=(), standins=True, sunset_lane=None, restore_lane=None, decls=None):
    """The rows root of the fixture: the lane's files as they ship, slice 3's stand-ins joined to them."""
    sunset = sunset_lane or shipped_lane("sunset")
    sunset["rows"] = list(sunset["rows"]) + (standin_rows() if standins else []) + list(sunset_extra)
    restore = restore_lane or shipped_lane("restore")
    restore["rows"] = list(restore["rows"]) + list(restore_extra)
    return rowlib.install(machine, sunset, restore, providers=decls or providers())


def machine(case, label="m", shortcut="dm", standins=True, plant_it=True):
    m = harness.Machine(case.tmp, label, label)
    programs(m)
    locations(m)
    m.write_settings()
    if plant_it:
        plant(m, shortcut)
    install(m, standins=standins)
    return m


def inputs(m, **more):
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
