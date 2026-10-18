"""Slice 2: sunrise's own rows, the local half (rows-rise.md revision 4), as shipped in `lifecycle/rows/sunrise/lane.json`
with the scaffold declarations in `lifecycle/rows/providers/scaffold.json`.

Every test's name carries the row's id and the frame's rule it rests on. The other lanes are stand-ins here (the common
brief, section 2): slice 3's git declaration and slice 4's `adapter.canary` under `fixtures/rise/`, and the rows that give
slice 3's outputs by its names, built by `standin_rows`. The programs are fakes (`fakes/rise_tools.py`): git is recorded
and then the system's own git runs on the test's own temporary repository; each scaffolder writes a small tree.
"""
import copy
import json
import os
import subprocess

import harness
import rowlib
from sun_core import facts as factsmod, plan, rows as rowsmod

ROWS = os.path.join(harness.LIFECYCLE, "rows")
FIXTURES = os.path.join(harness.TESTS, "fixtures", "rise")
TOOLS = os.path.join(harness.FAKES, "rise_tools.py")
PROGRAMS = ("git", "npx", "npm", "uv", "python3", "riseadapter")
L = rowlib.lit
F = {"output": "project folder.path"}
CAPS = ("canary", "memory stores")
# the three names by place (RUN-2 (a), rows-rise 3.0): <Name>, <slug>, <slug_>; for the name `demo` all three are `demo`
ALSO = ("demo", "demo")


def shipped():
    with open(os.path.join(ROWS, "sunrise", "lane.json")) as fh:
        lane = json.load(fh)
    with open(os.path.join(ROWS, "providers", "scaffold.json")) as fh:
        scaffold = json.load(fh)
    return lane, scaffold


def standin_providers():
    out = {}
    for name in ("standin-git.json", "standin-adapter.json"):
        with open(os.path.join(FIXTURES, name)) as fh:
            doc = json.load(fh)
        out[doc["provider"]] = doc
    return out


def providers():
    lane, scaffold = shipped()
    out = standin_providers()
    out["scaffold"] = scaffold
    out["fakehost"] = rowlib.providers()["fakehost"]      # the stand-in creates of slice 3's outputs
    return out


def standin_rows(env_value):
    """The rows that give slice 3's outputs by its names and fields (seams 1 to 5): STAND-INS, each replaced at the join."""
    slug = {"name": 1}
    remote = rowlib.create("SR08-standin", "sunrise", name={"text": [slug, L("-repo")]}, output="remote repository",
                           needs=[{"output": "first commit", "level": "made", "treatment": "then not applicable"}])
    remote["output"]["fields"] = {"id": {"held": "id"}, "name": {"text": [slug, L("-repo")]},
                                  "address": {"text": [L("https://github.invalid/"), slug]}}
    remote["thing"]["layer"] = "github"
    host = rowlib.create("SR09-standin", "sunrise", name={"text": [slug, L("-host")]}, output="hosting project",
                         needs=[{"output": "remote repository", "level": "made", "treatment": "then not applicable"}])
    host["output"]["fields"] = {"id": {"held": "id"}, "account": {"held": "id"}, "slug": slug,
                                "address": {"text": [L("https://"), slug, L(".vercel.invalid")]}}
    host["thing"]["layer"] = "hosting"
    ledger = rowlib.path(rowlib.DEV, "remote-ledger.txt")
    push = rowlib.row("change", "SR15-standin", "sunrise",
                      thing={"role": "the remote's branch, as the fake ledger records it", "identity": "path", "place": ledger,
                             "tracked": ["exists", "sha256"], "commit_of": {"repo": F, "ref": "main"}, "layer": "github"},
                      planning_test=[{"read": "path", "path": ledger, "is": "file"}],
                      before_test=[{"read": "line", "path": ledger, "line": L("pushed main"), "present": False}],
                      after_test=[{"read": "line", "path": ledger, "line": L("pushed main"), "count": 1}],
                      construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "append-line", "line": L("pushed main")}},
                      after_check=[{"read": "line", "path": ledger, "line": L("pushed main"), "count": 1}],
                      way_back={"none": "a stand-in: the push is slice 3's"},
                      output={"name": "push", "fields": {"commit": {"observed": "commit"}}},
                      needs=[{"output": "scanned for the push", "level": "passed", "treatment": "then not applicable"},
                             {"output": "remote repository", "level": "made", "treatment": "then not applicable"}])
    deployed = rowlib.check("SR16-standin", "sunrise", place=F, output="deployment",
                            thing={"layer": "hosting", "passes": [{"read": "path", "path": F, "is": "dir"}]},
                            needs=[{"output": "push", "level": "made", "treatment": "then not applicable"}])
    env_file = rowlib.path(F, ".env.local")
    pulled = rowlib.row("build", "SR19-standin", "sunrise",
                        thing={"role": "the pulled env file", "identity": "path", "place": env_file, "tracked": ["exists", "identity"],
                               "layer": "hosting"},
                        planning_test=[{"read": "path", "path": env_file, "is": "absent"}],
                        before_test=[{"id": "free", "read": "path", "path": env_file, "is": "absent"}],
                        after_test=[{"read": "path", "path": env_file, "is": "file"}],
                        construction={"id": "C1", "mode": 0o600, "single_file": True,
                                      "files": [{"rel": "env", "text": L("DATABASE_URL=%s\nVERCEL=1\n" % env_value)}]},
                        after_check=[{"read": "path", "path": env_file, "is": "file"}],
                        output={"name": "env file", "fields": {"path": env_file}},
                        needs=[{"output": "hosting project", "level": "made", "treatment": "then not applicable"}])
    return [remote, host, push, deployed, pulled]


def install(m, extra=(), lane_edit=None, standins=True):
    """A rows root for the machine: the shipped lane and scaffold declarations, the stand-ins, and `extra` rows."""
    lane, _scaffold = shipped()
    lane["rows"] += (standin_rows(harness.canary("env")) if standins else []) + list(extra)
    if lane_edit:
        lane_edit(lane)
    root = os.path.join(m.root, "rows-" + m.seed)
    for folder in ("providers", "sunrise"):
        os.makedirs(os.path.join(root, folder), exist_ok=True)
    for name, decl in providers().items():
        with open(os.path.join(root, "providers", name + ".json"), "w") as fh:
            json.dump(decl, fh, indent=1, sort_keys=True)
    with open(os.path.join(root, "sunrise", "lane.json"), "w") as fh:
        json.dump(lane, fh, indent=1, sort_keys=True)
    m.rows_root = root
    return lane


def programs(m, into_system=True):
    """The fake programs, each a wrapper of its name in a folder of the fixture's own. In-process, that folder stands first
    among the fixture's system folders (so even git is the recorded one); for a child drive, among his program folders."""
    folder = os.path.join(m.root, "programs-" + m.seed)
    os.makedirs(folder, exist_ok=True)
    for tool in PROGRAMS:
        path = os.path.join(folder, tool)
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\nexec /usr/bin/python3 -B '%s' %s \"$@\"\n" % (TOOLS.replace("'", "'\\''"), tool))
        os.chmod(path, 0o755)
    if into_system:
        m.system_folders = (folder, harness.FAKE_SYSTEM) + tuple(factsmod.SYSTEM_FOLDERS)
    m.settings["program_folders"] = [harness.FAKES, folder]
    m.write_settings()
    return folder


def machine_for_sunrise(m, wired=True, identity=True, into_system=True):
    """His machine as sunrise reads it: the locations of rows-rise 3.0, git's identity, the vault's root index, the memory
    index, the shortcut file wired into his shell startup, and a fake remote's ledger."""
    loc = m.settings["locations"]
    loc.update({"staged_docs": m.path("staged"), "vault_projects": os.path.join(m.vault, "projects"),
                "vault_index": os.path.join(m.vault, "_index.md"), "vault_link_prefix": "projects",
                "memory_home": m.path("memory"), "memory_index": m.path("memory", "MEMORY.md"),
                "shortcut_file": m.path("shortcuts.txt"), "shell_startup": m.path(".zshrc")})
    m.write_settings()
    os.makedirs(m.path("staged"))
    m.put("vault/_index.md", "# Vault\n\n## Active projects\n- [[projects/other/_index|Other]]\n")
    m.put("memory/MEMORY.md", "# Memory\n- [Other](project_other.md): another project\n")
    m.put("shortcuts.txt", "alias oth=\"cd /x/other\"\n")
    m.put(".zshrc", ("source $HOME/shortcuts.txt  # project-shortcuts\n" if wired else "export X=1\n"))
    m.put("dev/remote-ledger.txt", "ledger\n")
    if identity:
        m.put(".gitconfig", "[user]\n\temail = fixture@example.invalid\n\tname = Fixture Owner\n")
    else:
        m.put(".gitconfig", "[user]\n\tname = Fixture Owner\n")
    programs(m, into_system)
    return m


def sunrise_inputs(m, type_="web app", scaffold="web app", drop=(), local_proof=None, hosting=True, shortcut="dm", **more):
    flags = {"scaffold": scaffold, "hosting": hosting}
    if local_proof:
        flags["local_proof"] = local_proof
    doc = {"type": type_, "flags": flags, "drop_layers": list(drop), "answers": {"shortcut": shortcut}}
    doc.update(more)
    return m.inputs(**doc)


def git(repo, *args):
    return subprocess.run(["/usr/bin/git", "-C", repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          check=True).stdout.decode("utf-8")


def manifest_of(m, run_id, number=1):
    with open(os.path.join(m.facts.run_dir(run_id), "manifest-%d.json" % number)) as fh:
        return json.load(fh)


def read(*path):
    with open(os.path.join(*path)) as fh:
        return fh.read()


def git_writes(m):
    """The recorded git calls that can change a repository, in order: their subcommand words."""
    out = []
    for call in m.calls("git"):
        argv = call["argv"]
        word = next((a for a in argv if a in ("init", "add", "commit", "branch")), None)
        if word:
            out.append(word)
    return out


LOCAL_ONLY = ("github", "hosting", "database")
# `flags.local_proof` for a scaffold that builds, one word per scaffold (the report's choice: a build check's output folders
# are the row's own literal words, so each scaffold that builds has its own row, SR25-build-next, -astro, -electron)
BUILDS = {"web app": "build next", "static site": "build astro", "desktop app": "build electron"}
OUTPUTS = {"build next": [".next"], "build astro": ["dist", ".astro"], "build electron": ["out"]}
# SR03-envex-keys as one row per key (the fix round's choice, report-3), in the key order of rows-rise 3.5
ENVEX_KEYS = ("SR03-envex-keys-postgres-url", "SR03-envex-keys-postgres-url-non-pooling", "SR03-envex-keys-database-url")
# v1's old AGENTS.md stub, its two content lines (v1 a1d88e2 to f2b055c~1), the merge's pointer (G24-5)
V1_STUB = ("The canonical agent file for this repo is **`CLAUDE.md`** in the same directory.\n"
           "This stub exists for tools that look for `AGENTS.md`. Read `CLAUDE.md`.")


def wrote(m):
    """What the fake build wrote, each path relative to the project it built in."""
    try:
        with open(os.path.join(m.home, ".fakes", "npm", "wrote.jsonl")) as fh:
            return [json.loads(line)["rel"] for line in fh if line.strip()]
    except OSError:
        return []


def operation(m, run, rid):
    return [o for o in manifest_of(m, run)["operations"] if o["id"] == rid][0]


class Base(harness.Case):
    def sun(self, label, type_="web app", scaffold="web app", drop=(), local_proof=None, extra=(), wired=True, identity=True,
            caps=CAPS, lane_edit=None, standins=True, prepare=None, ending="complete", **more):
        m = machine_for_sunrise(self.machine(label, label), wired=wired, identity=identity)
        if prepare:
            prepare(m)
        install(m, extra, lane_edit, standins)
        looked = m.look(also=ALSO, inputs=sunrise_inputs(m, type_, scaffold, drop, local_proof, hosting=not drop, **more), caps=caps)
        if ending is None:
            return m, looked, None
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, also=ALSO, caps=caps)
        if ending != "any":
            self.assertEqual(went.ending, ending, went.text)
        return m, looked, went


# ---- the lane as shipped (ROW-1, ROW-3) -----------------------------------------------------------------------------
class Admission(harness.Case):
    def test_ROW1_ROW3_the_shipped_lane_is_admitted_with_its_checklist_answered(self):
        lane, scaffold = shipped()
        decls = providers()
        expanded = plan.expand(lane, decls)
        self.assertEqual(plan.admit_all(lane, expanded, decls), [])
        self.assertEqual(rowsmod.checklist_findings(lane), [])
        ids = [r["id"] for r in lane["rows"]]
        self.assertEqual(len(ids), 52)
        self.assertEqual(lane["kind"], "sunrise")
        self.assertEqual(lane["phases"], ["sunrise"])
        self.assertEqual(lane["types"], ["web app", "static site", "desktop app", "script or CLI"])
        self.assertEqual(sorted(scaffold["commands"]), ["astro", "build", "electron", "next", "npm", "package", "run-py", "uv"])

    def test_SR03_docs_SR12b_dir_SR06_coldread_SR06_review_ROW1_G24_3_G24_4_the_folder_and_staged_read_rows_ship_in_the_lane(self):
        lane, _scaffold = shipped()
        ids = [r["id"] for r in lane["rows"]]
        for rid in ("SR03-docs", "SR03-docs-scope", "SR03-docs-architecture", "SR03-docs-reviews", "SR12b-dir", "SR06-coldread",
                    "SR06-review"):
            self.assertIn(rid, ids)
        self.assertFalse(os.path.exists(os.path.join(FIXTURES, "held-folder-rows.json")))

    def test_ROW1_a_row_of_the_shipped_lane_with_an_entry_left_out_fails_the_build_naming_it(self):
        lane, _scaffold = shipped()
        decls = providers()
        broken = copy.deepcopy(lane)
        del broken["rows"][0]["content_classes"]
        found = plan.admit_all(broken, plan.expand(broken, decls), decls)
        self.assertIn({"row": "SR00", "entry": "content_classes", "finding": "the entry is left out"}, found)

    def test_ROW3_a_checklist_item_left_unanswered_fails_the_admission_naming_the_item(self):
        lane, _scaffold = shipped()
        broken = copy.deepcopy(lane)
        broken["checklist"][0]["answered_by"] = {}
        self.assertEqual(rowsmod.checklist_findings(broken)[0]["finding"], "unanswered")


# ---- the reference run, end to end (one run of the lane over fakes) ---------------------------------------------------
class EndToEnd(Base):
    def test_SR00_to_SR25_RUN9_a_web_app_sunrise_looked_previewed_approved_and_executed_ends_complete(self):
        m, looked, went = self.sun("e2e")
        run = looked.doc["run"]
        project = m.path("dev", "demo")
        statuses = m.statuses(run)
        want = {"SR00": "passed", "SR02-next": "done", "SR03-agents": "done", "SR03-claude": "already so", "SR03-readme": "done",
                "SR03-ignore": "done", "SR03-envex": "done", "SR03-envex-keys-postgres-url": "done",
                "SR03-envex-keys-postgres-url-non-pooling": "done", "SR03-envex-keys-database-url": "done", "SR05": "done", "SR05-main": "already so",
                "SR07-stage": "done", "SR07-scan": "passed", "SR07": "done", "SR10": "done", "SR13-agents": "passed",
                "SR13-claude": "passed", "SR13-canary": "passed", "SR14": "passed", "SR20": "done", "SR20-github": "done",
                "SR20-hosting": "done", "SR20-database": "done", "SR21": "done", "SR22": "done", "SR23": "done", "SR24": "done",
                "SR25": "passed"}
        for op, status in want.items():
            self.assertEqual(statuses.get(op), status, op)
        # the files, with their bytes
        agents = read(project, "AGENTS.md")
        self.assertTrue(agents.startswith("<!-- BEGIN:nextjs-agent-rules -->\n"), agents[:80])
        for line in ("# demo", "<!-- verified: 2026-01-01 -->", "a fixture project",
                     "Stack: Next.js, by create-next-app. Started 2026-01-01 via sunrise; green baseline.",
                     "- Run: `npm run dev`", "- Build: `npm run build`", "- Typecheck: `npx tsc --noEmit`",
                     "- Feature branches + PRs. Never push to `main`."):
            self.assertEqual(agents.split("\n").count(line), 1, line)
        self.assertEqual(read(project, "CLAUDE.md"), "@AGENTS.md\n")
        self.assertEqual(read(project, "README.md"), "# demo\n\na fixture project\n\nRun: `npm run dev`\n")
        self.assertTrue(read(project, ".gitignore").endswith(".env*\n.vercel\n!.env.example\n"))
        self.assertEqual(read(project, ".env.example"),
                         "# the keys this project reads, with no values\nPOSTGRES_URL=\nPOSTGRES_URL_NON_POOLING=\nDATABASE_URL=\n")
        link = os.path.join(project, ".vercel", "project.json")
        self.assertEqual(sorted(json.loads(read(link))), ["orgId", "projectId"])
        self.assertEqual(os.stat(link).st_mode & 0o777, 0o600)
        # the repository: one commit on main, the kit in it, the env and link files ignored and untracked
        self.assertEqual(git(project, "log", "--format=%s").strip(), "sunrise: the scaffold, the repo doc kit and the adopted docs")
        self.assertEqual(git(project, "rev-parse", "--abbrev-ref", "HEAD").strip(), "main")
        tracked = git(project, "ls-files").split()
        self.assertIn("AGENTS.md", tracked)
        self.assertNotIn(".env.local", tracked)
        self.assertNotIn(".vercel/project.json", tracked)
        # the vault, the memory store, the shortcut
        seed = read(m.vault, "projects", "demo", "_index.md")
        for line in ("status: active", "- **Local path:** %s" % project, "- **Terminal shortcut:** `dm`", "- **Branch:** main",
                     "- **GitHub:** https://github.invalid/demo", "- **Vercel:** https://demo.vercel.invalid",
                     "- **Database:** Supabase via Vercel Marketplace"):
            self.assertEqual(seed.split("\n").count(line), 1, line)
        self.assertIn("- [[projects/demo/_index|demo]]\n", read(m.vault, "_index.md"))
        self.assertEqual(read(m.path("memory", "MEMORY.md")).split("\n").count("- [demo](project_demo.md): a fixture project"), 1)
        note = m.path("memory", "project_demo.md")
        self.assertTrue(read(note).startswith("---\nname: demo\n"))
        self.assertNotIn("status:", read(note))
        self.assertEqual(os.stat(note).st_mode & 0o777, 0o600)
        self.assertTrue(read(m.path("shortcuts.txt")).endswith('alias dm="cd %s"\n' % project))
        # OP-11: the fake git's record of state-changing calls equals the manifest's list, in order
        listed = []
        for operation in manifest_of(m, run)["operations"]:
            for name in operation.get("repo_commands") if isinstance(operation.get("repo_commands"), list) else []:
                if statuses.get(operation["id"]) == "done":
                    listed.append({"init": "init", "rename": "branch", "stage": "add", "commit": "commit"}[name])
        self.assertEqual(git_writes(m), listed)
        self.assertEqual(listed, ["init", "add", "commit"])
        # the forms, kept for the report
        forms = dict((os.path.basename(p), read(p)) for p in looked.doc["forms"] + went.doc["forms"])
        out = os.environ.get("RISE_FORMS_OUT")
        if out:
            with open(out, "w") as fh:
                for name in sorted(forms):
                    fh.write("==== %s ====\n%s\n" % (name, forms[name]))
        self.assertIn("SUNRISE PREVIEW: demo  \"a fixture project\"", forms["preview-1.txt"])
        self.assertIn("SUNRISE COMPLETE: demo  \"a fixture project\"", forms["summary-1.txt"])
        self.assertIn("- GitHub: the private repository", forms["handoff-1.txt"])


# ---- each row: its planned effect, its stops ------------------------------------------------------------------------
class Rows(Base):
    def test_SR00_OP8_without_an_email_to_commit_as_the_run_stops_on_the_check_before_any_project_file(self):
        m, looked, went = self.sun("noid", identity=False, ending="stopped")
        self.assertEqual(m.statuses(looked.doc["run"]).get("SR00"), "failed")
        self.assertFalse(os.path.exists(m.path("dev", "demo")))

    def test_SR01_OP10_a_folder_he_names_is_adopted_and_the_kit_and_repository_are_laid_in_it(self):
        def prepare(m):
            m.put("dev/demo/notes.txt", "his own notes\n")
            m.put("dev/demo/AGENTS.md", "Read CLAUDE.md for this project's rules.\n")
            m.put("dev/demo/CLAUDE.md", "# His rules\nan old rule of his\n")
        # the adopt input names the folder by its full path; `flags.scaffold` is the word `adopted`, which no SR02 row holds
        m2 = machine_for_sunrise(self.machine("adopt2", "adopt2"))
        prepare(m2)
        install(m2)
        looked = m2.look(also=ALSO, inputs=sunrise_inputs(m2, scaffold="adopted", adopt={"project folder": m2.path("dev", "demo")}), caps=CAPS)
        self.assertEqual(looked.ending, "preview", looked.text)
        ids = [o["id"] for o in manifest_of(m2, looked.doc["run"])["operations"]]
        self.assertIn("SR01", ids)
        self.assertFalse([i for i in ids if i.startswith("SR02")])
        went = m2.go(looked, also=ALSO, caps=CAPS)
        self.assertEqual(went.ending, "complete", went.text)
        project = m2.path("dev", "demo")
        self.assertEqual(m2.statuses(looked.doc["run"])["SR01"], "adopted")
        self.assertEqual(read(project, "notes.txt"), "his own notes\n")
        agents = read(project, "AGENTS.md")
        self.assertIn("Stack: an existing folder, adopted as it stands.", agents)
        self.assertNotIn("- Run:", agents)                       # no scaffold, no command: each Commands line cut (M-1)
        self.assertTrue(agents.endswith("## Lifted from CLAUDE.md\n# His rules\nan old rule of his\n"), agents[-120:])
        self.assertEqual(read(project, "CLAUDE.md"), "@AGENTS.md\n")
        self.assertIn("notes.txt", git(project, "ls-files").split())

    def test_SR02_OP11_SEC7_each_named_scaffold_runs_its_declared_command_in_the_empty_staged_folder(self):
        cases = (("web app", "web app", "npx", ["--yes", "create-next-app@latest", ".", "--yes", "--disable-git"], "app/page.tsx"),
                 ("static site", "static site", "npm", ["create", "--yes", "astro@latest", "--", ".", "--template", "minimal",
                                                         "--install", "--no-git", "--yes", "--skip-houston"], "src/pages/index.astro"),
                 ("static site", "static site, single file", None, None, "index.html"),
                 ("desktop app", "desktop app", "npm", ["create", "--yes", "@quick-start/electron@latest", ".", "--", "--template",
                                                         "vanilla"], "src/main/index.js"),
                 ("script or CLI", "script or CLI", "npm", ["init", "--yes"], "package.json"),
                 ("script or CLI", "script or CLI, Python", "uv", ["init", "--vcs", "none", "--app", "."], "main.py"))
        proofs = {"web app": "build next", "static site": "build astro", "static site, single file": "html",
                  "desktop app": "build electron", "script or CLI": "npm", "script or CLI, Python": "uv"}
        for n, (type_, word, tool, argv, made) in enumerate(cases):
            with self.subTest(scaffold=word):
                m, looked, went = self.sun("s%d" % n, type_=type_, scaffold=word, drop=LOCAL_ONLY, local_proof=proofs[word])
                rid = [o["id"] for o in manifest_of(m, looked.doc["run"])["operations"] if o["id"].startswith("SR02")]
                self.assertEqual(len(rid), 1)
                self.assertEqual(m.statuses(looked.doc["run"])[rid[0]], "done")
                self.assertTrue(os.path.isfile(m.path("dev", "demo", made)), made)
                if tool:
                    call = [c for c in m.calls(tool) if c["argv"] == argv]
                    self.assertEqual(len(call), 1, m.calls(tool))
                    staged = os.path.join(m.facts.run_dir(looked.doc["run"]), "staging", rid[0], "object")
                    self.assertEqual(os.path.realpath(call[0]["cwd"]), os.path.realpath(staged))
                else:
                    self.assertEqual(read(m.path("dev", "demo", "index.html")),
                                     "<!doctype html>\n<title>demo</title>\n<p>a fixture project</p>\n")

    def test_SR02_RUN7_a_folder_already_at_the_place_is_a_planning_stop_never_clobbered(self):
        m, looked, _ = self.sun("taken", prepare=lambda m: m.put("dev/demo/x.txt", "x\n"), ending=None)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the place is taken by a thing this run did not make: row SR02-next", looked.text)
        self.assertEqual(read(m.path("dev", "demo", "x.txt")), "x\n")

    def test_SR03_agents_SR03_claude_A151_a_scaffolders_agents_file_keeps_its_block_and_claude_becomes_the_stub(self):
        m, looked, went = self.sun("kit")
        agents = read(m.path("dev", "demo", "AGENTS.md"))
        self.assertTrue(agents.startswith("<!-- BEGIN:nextjs-agent-rules -->\nThis is a fixture framework block.\n<!-- END:nextjs-agent-rules -->\n# demo\n"))
        marks = [(r["op"], r["risk"]) for r in m.journal(looked.doc["run"]) if r["kind"] == "step" and r.get("step") == "risk-mark"]
        self.assertIn(("SR03-agents", "RK18"), marks)
        self.assertIn(("SR03-agents", "RK2"), marks)

    def test_SR05_SR05_main_OP3_RK18_the_repository_is_made_on_main_and_an_existing_main_is_never_replaced(self):
        def prepare(m):
            os.makedirs(m.path("dev", "demo"))
            m.put("dev/demo/a.txt", "a\n")
            subprocess.run(["/usr/bin/git", "-C", m.path("dev", "demo"), "init", "-q", "--initial-branch", "master"], check=True)
        m = machine_for_sunrise(self.machine("main", "main"))
        prepare(m)
        install(m)
        looked = m.look(also=ALSO, inputs=sunrise_inputs(m, scaffold="adopted", adopt={"project folder": m.path("dev", "demo")}), caps=CAPS)
        went = m.go(looked, also=ALSO, caps=CAPS)
        self.assertEqual(went.ending, "complete", went.text)
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual((statuses["SR05"], statuses["SR05-main"]), ("already so", "done"))
        self.assertEqual(git(m.path("dev", "demo"), "rev-parse", "--abbrev-ref", "HEAD").strip(), "main")
        # a main that exists while another branch is current: never replaced; the run stops on that row
        m2 = machine_for_sunrise(self.machine("main2", "main2"))
        repo = m2.path("dev", "demo")
        prepare(m2)
        m2.put("dev/demo/b.txt", "b\n")
        for args in (("add", "--all"), ("-c", "user.email=f@x.invalid", "-c", "user.name=f", "commit", "-q", "-m", "one"),
                     ("branch", "main")):
            subprocess.run(["/usr/bin/git", "-C", repo] + list(args), check=True, stdout=subprocess.DEVNULL)
        install(m2)
        looked = m2.look(also=ALSO, inputs=sunrise_inputs(m2, scaffold="adopted", adopt={"project folder": repo}), caps=CAPS)
        went = m2.go(looked, also=ALSO, caps=CAPS)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("SR05-main", went.text)
        self.assertEqual(git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip(), "master")
        self.assertNotIn("branch", git_writes(m2))

    def test_SR03_docs_SR03_docs_scope_architecture_reviews_OP2_A154_each_folder_is_published_where_absent_its_parent_first(self):
        m, looked, went = self.sun("folders")
        project = m.path("dev", "demo")
        statuses = m.statuses(looked.doc["run"])
        for rid in ("SR03-docs", "SR03-docs-scope", "SR03-docs-architecture", "SR03-docs-reviews"):
            self.assertEqual(statuses[rid], "done", rid)
        self.assertEqual(sorted(os.listdir(os.path.join(project, "docs"))), [".gitkeep", "architecture", "reviews", "scope"])
        self.assertEqual(read(project, "docs", ".gitkeep"), "")
        for sub in ("scope", "architecture", "reviews"):
            self.assertEqual(os.listdir(os.path.join(project, "docs", sub)), [])
        # each published as C1 publishes: its start record's before-state the absence (OP-2, A154), the parent's first
        starts = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "start" and r["op"].startswith("SR03-docs")]
        self.assertEqual([r["op"] for r in starts][0], "SR03-docs")
        self.assertEqual([r["thing"]["exists"] for r in starts], [False] * 4)
        self.assertIn("docs/.gitkeep", git(project, "ls-files").split())

    def test_SR03_docs_OP5_a_docs_folder_that_stands_is_already_so_and_its_own_files_are_kept(self):
        def prepare(m):
            m.put("dev/demo/docs/notes.md", "his notes\n")
            m.put("dev/demo/docs/scope/old.md", "an old scope\n")
        m = machine_for_sunrise(self.machine("docs2", "docs2"))
        prepare(m)
        install(m)
        looked = m.look(also=ALSO, inputs=sunrise_inputs(m, scaffold="adopted", adopt={"project folder": m.path("dev", "demo")}), caps=CAPS)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, also=ALSO, caps=CAPS)
        self.assertEqual(went.ending, "complete", went.text)
        statuses = m.statuses(looked.doc["run"])
        # the folder he named is bound at the go (OP-10), so the folders are probed then: `already so` (OP-5, OP-6)
        self.assertEqual((statuses["SR03-docs"], statuses["SR03-docs-scope"]), ("already so", "already so"))
        self.assertEqual((statuses["SR03-docs-architecture"], statuses["SR03-docs-reviews"]), ("done", "done"))
        self.assertFalse(os.path.exists(m.path("dev", "demo", "docs", ".gitkeep")))
        self.assertEqual(read(m.path("dev", "demo", "docs", "notes.md")), "his notes\n")

    def test_SR06_scope_SR06_architecture_OP6_EV1_C7_staged_docs_move_into_the_folders_the_folder_rows_lay(self):
        def staged(m):
            m.put("staged/demo-scope.md", "# demo scope doc (2026-09-03)\nbody\n")
            m.put("staged/demo-architecture.md", "# demo architecture (2026-09-04)\nbody\n")
        m, looked, went = self.sun("staged", prepare=staged)
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual((statuses["SR06-scope"], statuses["SR06-architecture"]), ("done", "done"))
        project = m.path("dev", "demo")
        self.assertEqual(read(project, "docs", "scope", "2026-09-03-demo.md"), "# demo scope doc (2026-09-03)\nbody\n")
        self.assertEqual(read(project, "docs", "architecture", "2026-09-04-demo.md"), "# demo architecture (2026-09-04)\nbody\n")
        self.assertFalse(os.path.exists(m.path("staged", "demo-scope.md")))
        self.assertFalse(os.path.exists(m.path("staged", "demo-architecture.md")))
        tracked = git(project, "ls-files").split()
        self.assertIn("docs/scope/2026-09-03-demo.md", tracked)
        self.assertIn("docs/architecture/2026-09-04-demo.md", tracked)
        # ORD-4: each move after its folder's row
        order = [r["op"] for r in m.journal(looked.doc["run"]) if r["kind"] == "start"]
        self.assertLess(order.index("SR03-docs-scope"), order.index("SR06-scope"))
        self.assertLess(order.index("SR03-docs-architecture"), order.index("SR06-architecture"))
        # one already at its destination, in the folder he names: "already adopted", and its staged source not looked for
        def prepare(m):
            m.put("dev/demo/docs/scope/2026-08-30-demo.md", "adopted before\n")
            m.put("staged/demo-scope.md", "# again (2026-09-03)\n")
        m2 = machine_for_sunrise(self.machine("staged2", "staged2"))
        prepare(m2)
        install(m2)
        looked = m2.look(also=ALSO, inputs=sunrise_inputs(m2, scaffold="adopted", adopt={"project folder": m2.path("dev", "demo")}), caps=CAPS)
        self.assertEqual(looked.ending, "preview", looked.text)
        na = dict((n["row"], n["reason"]) for n in manifest_of(m2, looked.doc["run"])["not_applicable"])
        self.assertEqual(na["SR06-scope"], "already adopted: " + m2.path("dev", "demo", "docs", "scope", "2026-08-30-demo.md"))

    def test_SR06_coldread_SR06_review_G24_3_RUN6_C7_staged_reads_move_under_their_date_lane_and_suffix_dated_and_undated(self):
        # the names precon and architect stage (`<slug>-cold-read-<date>[-<n>].md`, `<slug>-review-<date>-<lane>[-<n>].md`),
        # and an undated name, its date read from the doc's first line (M-2)
        cases = (("dated", [("SR06-coldread", "precon-cold-reads/demo-cold-read-2026-10-01.md", "# demo cold read\nbody\n",
                             "2026-10-01-precon-cold-read-demo.md"),
                            ("SR06-review", "architect-reviews/demo-review-2026-10-01-gpt.md", "row gpt-astra\nbody\n",
                             "2026-10-01-architect-review-demo-gpt.md")]),
                 ("again", [("SR06-coldread", "precon-cold-reads/demo-cold-read-2026-10-01-2.md", "# demo cold read\nagain\n",
                             "2026-10-01-precon-cold-read-demo-2.md"),
                            ("SR06-review", "architect-reviews/demo-review-2026-10-01-gemini-2.md", "row gemini\nagain\n",
                             "2026-10-01-architect-review-demo-gemini-2.md")]),
                 ("undated", [("SR06-coldread", "precon-cold-reads/demo-cold-read-draft.md", "# demo cold read (2026-10-02)\nbody\n",
                               "2026-10-02-precon-cold-read-demo.md")]))
        for label, staged in cases:
            with self.subTest(names=label):
                m, looked, went = self.sun("r" + label, prepare=lambda m, s=staged: [m.put("staged/" + r, t) for _i, r, t, _n in s])
                run = looked.doc["run"]
                statuses = m.statuses(run)
                project = m.path("dev", "demo")
                order = [r["op"] for r in m.journal(run) if r["kind"] == "start"]
                self.assertEqual(sorted(os.listdir(os.path.join(project, "docs", "reviews"))), sorted(n for _i, _r, _t, n in staged))
                for rid, rel, text, name in staged:
                    self.assertEqual(statuses[rid], "done", rid)
                    self.assertEqual(read(project, "docs", "reviews", name), text)
                    self.assertFalse(os.path.exists(m.path("staged", rel)))
                    self.assertIn("docs/reviews/" + name, git(project, "ls-files").split())
                    self.assertLess(order.index("SR03-docs-reviews"), order.index(rid))

    def test_SR06_review_G24_3_RUN6_a_staged_review_whose_name_carries_no_lane_NOT_WRITTEN(self):
        """Not written: Question 1 of report-3. A staged review with no lane in its name (no date in it, or none after the
        date) leaves the target's `<lane>` unsettled, and the whole look is refused (SCRATCH/red/part3-undated-review-probe.txt);
        rows-rise 3.7 writes the target with `<lane>` and says nothing of a name without one."""
        self.skipTest("Question 1 (report-3): a staged review with no lane in its name")

    def test_SR03_docs_G24_4_OP4_OP6_EV1b_a_kill_between_a_folders_publish_and_its_mode_resumes_to_the_rows_modes(self):
        points = (("post", "rename", "docs"), ("pre", "chmod", "docs"), ("post", "chmod", "docs"), ("pre", "chmod", ".gitkeep"),
                  ("post", "rename", "scope"), ("pre", "chmod", "scope"))
        for n, (stage, op, end) in enumerate(points):
            with self.subTest(point="%s %s %s" % (stage, op, end)):
                m = machine_for_sunrise(self.machine("kdocs%d" % n, "kdocs%d" % n))
                install(m)
                looked = m.look(also=ALSO, inputs=sunrise_inputs(m), caps=CAPS)
                self.assertEqual(looked.ending, "preview", looked.text)
                killed = m.go(looked, also=ALSO, caps=CAPS,
                              kill=lambda e, s=stage, o=op, t=end: e["stage"] == s and e["op"] == o and str(e["subject"]).endswith(t))
                self.assertTrue(killed.killed, killed.text)
                self.assertEqual(m.resume(also=ALSO, caps=CAPS).ending, "complete")
                statuses = m.statuses(looked.doc["run"])
                self.assertEqual((statuses["SR03-docs"], statuses["SR03-docs-scope"]), ("done", "done"))
                docs = m.path("dev", "demo", "docs")
                self.assertEqual(os.stat(docs).st_mode & 0o777, 0o755)
                self.assertEqual(os.stat(os.path.join(docs, "scope")).st_mode & 0o777, 0o755)
                self.assertEqual(os.stat(os.path.join(docs, ".gitkeep")).st_mode & 0o777, 0o644)

    def test_SR12a_SR12b_dir_SR12b_OP2_A154_a_desktop_app_with_hosting_gets_public_and_its_placeholder_page(self):
        m, looked, went = self.sun("desk", type_="desktop app", scaffold="desktop app")
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual((statuses["SR12a"], statuses["SR12b-dir"], statuses["SR12b"]), ("done", "done", "done"))
        project = m.path("dev", "demo")
        self.assertEqual(read(project, "vercel.json"), '{"outputDirectory": "public"}\n')
        self.assertEqual(read(project, "public", "index.html"),
                         "<!doctype html>\n<title>demo</title>\n<p>This is the hosting placeholder of a desktop app.</p>\n")
        order = [r["op"] for r in m.journal(looked.doc["run"]) if r["kind"] == "start"]
        self.assertLess(order.index("SR12b-dir"), order.index("SR12b"))
        self.assertIn("public/index.html", git(project, "ls-files").split())

    def test_SR07_scan_SEC10_a_value_of_the_env_file_in_a_file_to_be_committed_stops_the_run_before_any_commit(self):
        value = harness.canary("leak")

        def prepare(m):
            m.put("dev/demo/notes.txt", "his notes %s\n" % value)
            m.put("dev/demo/.env.local", "DATABASE_URL=%s\n" % value)
        m = machine_for_sunrise(self.machine("leak", "leak"))
        prepare(m)
        install(m)
        looked = m.look(also=ALSO, inputs=sunrise_inputs(m, scaffold="adopted", adopt={"project folder": m.path("dev", "demo")}), caps=CAPS)
        went = m.go(looked, also=ALSO, caps=CAPS)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(m.statuses(looked.doc["run"]).get("SR07-scan"), "failed")
        self.assertNotIn("commit", git_writes(m))
        self.assertNowhere(value, went)

    def test_SR13_canary_OP8_on_a_harness_without_the_canary_the_check_is_unavailable_and_the_run_completes(self):
        m, looked, went = self.sun("nocan", caps=("memory stores",))
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual(statuses["SR13-canary"], "unavailable")
        self.assertEqual(statuses["SR25"], "passed")

    def test_SR20_RUN7_a_vault_folder_already_there_is_a_planning_stop(self):
        m, looked, _ = self.sun("vault", prepare=lambda m: m.put("vault/projects/demo/_index.md", "x\n"), ending=None)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row SR20", looked.text)

    def test_SR21_RUN7_a_root_index_without_its_heading_is_a_planning_stop(self):
        m, looked, _ = self.sun("index", prepare=lambda m: m.put("vault/_index.md", "# Vault\n"), ending=None)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row SR21", looked.text)

    def test_SR22_SR23_RUN7_on_a_harness_without_memory_stores_both_are_not_applicable(self):
        m, looked, went = self.sun("nomem", caps=("canary",))
        na = dict((n["row"], n["reason"]) for n in manifest_of(m, looked.doc["run"])["not_applicable"])
        self.assertEqual((na["SR22"], na["SR23"]), ("not available on this harness", "not available on this harness"))
        self.assertFalse(os.path.exists(m.path("memory", "project_demo.md")))

    def test_SR24_ORD3_a_shortcut_file_not_wired_into_his_shell_is_not_applicable_and_no_line_is_added(self):
        m, looked, went = self.sun("unwired", wired=False)
        na = dict((n["row"], n["reason"]) for n in manifest_of(m, looked.doc["run"])["not_applicable"])
        self.assertEqual(na["SR24"], "the shortcut file is not wired into your shell")
        self.assertEqual(read(m.path("shortcuts.txt")), "alias oth=\"cd /x/other\"\n")

    def test_SR24_SEC9_a_shortcut_off_its_form_is_refused_in_the_look(self):
        m, looked, _ = self.sun("badcut", shortcut="Bad!", ending=None)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("a shortcut's name", looked.text)
        self.assertFalse(looked.doc.get("manifest_sha256"))

    def test_SR25_SR25_npm_SR25_uv_SR25_html_ORD2_without_hosting_the_local_baseline_proves_the_scaffold_and_no_push_is_needed(self):
        for word, proof, rid in (("script or CLI", "npm", "SR25-npm"), ("script or CLI, Python", "uv", "SR25-uv"),
                                 ("static site, single file", "html", "SR25-html")):
            with self.subTest(proof=proof):
                type_ = "static site" if proof == "html" else "script or CLI"
                m, looked, went = self.sun("b" + proof, type_=type_, scaffold=word, drop=LOCAL_ONLY, local_proof=proof)
                statuses = m.statuses(looked.doc["run"])
                self.assertEqual((statuses[rid], statuses["SR25"]), ("passed", "passed"))
                settled = [(s["operation"], s["need"]) for s in manifest_of(m, looked.doc["run"])["settled_needs"]]
                self.assertIn(("SR25", "push"), settled)
                sr25 = [o for o in manifest_of(m, looked.doc["run"])["operations"] if o["id"] == "SR25"][0]
                self.assertFalse([p for p in sr25["thing"]["passes"] if p.get("read") == "ref"])
                if proof == "uv":
                    self.assertTrue([c for c in m.calls("python3") if c["argv"][-1] == m.path("dev", "demo", "main.py")])
                if proof == "npm":
                    self.assertTrue([c for c in m.calls("npm") if c["argv"][2:] == ["pkg", "get", "name"]])

    def test_SR25_build_R9_OP8_A154_each_scaffolds_fake_build_writes_only_inside_the_folders_its_row_names(self):
        for type_, proof in sorted(BUILDS.items()):
            with self.subTest(proof=proof):
                rid = "SR25-" + proof.replace(" ", "-")
                m, looked, went = self.sun("w" + proof.split()[1], type_=type_, scaffold=type_, drop=LOCAL_ONLY, local_proof=proof)
                statuses = m.statuses(looked.doc["run"])
                self.assertEqual((statuses[rid], statuses["SR25"]), ("passed", "passed"))
                named = operation(m, looked.doc["run"], rid)["thing"]["build"]["output"]
                self.assertEqual(named, OUTPUTS[proof])
                written = wrote(m)
                self.assertTrue(written)
                for rel in written:
                    self.assertIn(rel.split("/")[0], named, rel)
                self.assertEqual(git(m.path("dev", "demo"), "status", "--porcelain"), "")

    def test_SR25_build_R9_OP8_A154_a_stale_output_while_the_scaffold_cannot_build_fails_the_check(self):
        def prepare(m):
            m.plan_fake("npx", {"stale": True})
            m.plan_fake("npm", {"when": "--prefix", "do": "fail"})
        m, looked, went = self.sun("stale", drop=LOCAL_ONLY, local_proof="build next", prepare=prepare, ending="stopped")
        run = looked.doc["run"]
        self.assertEqual(m.statuses(run).get("SR25-build-next"), "failed")
        self.assertNotEqual(m.statuses(run).get("SR25"), "passed")
        self.assertEqual([r["answer"] for r in m.journal(run) if r["kind"] == "attempt" and r["op"] == "SR25-build-next"], ["failed"])
        self.assertEqual(len([c for c in m.calls("npm") if c["argv"][2:4] == ["run", "build"]]), 1)
        self.assertFalse(os.path.exists(m.path("dev", "demo", ".next", "BUILD_ID")))     # the stale output taken away

    def test_SR25_build_R9_OP8_A154_a_stale_output_with_a_scaffold_that_builds_the_build_runs_and_the_check_passes(self):
        m, looked, went = self.sun("build", drop=LOCAL_ONLY, local_proof="build next",
                                   prepare=lambda m: m.plan_fake("npx", {"stale": True}))
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual((statuses["SR25-build-next"], statuses["SR25"]), ("passed", "passed"))
        self.assertEqual([c["argv"] for c in m.calls("npm") if c["argv"][2:4] == ["run", "build"]],
                         [["--prefix", m.path("dev", "demo"), "run", "build"]])
        self.assertEqual(read(m.path("dev", "demo", ".next", "BUILD_ID")), "built\n")

    def test_SR25_build_R9_OP8_A154_a_build_that_writes_outside_the_folders_its_row_names_stops(self):
        m, looked, went = self.sun("stray", drop=LOCAL_ONLY, local_proof="build next",
                                   prepare=lambda m: m.plan_fake("npm", {"when": "--prefix", "stray": True}), ending="stopped")
        self.assertIn("the build wrote outside its output folder", went.text)
        self.assertEqual(m.statuses(looked.doc["run"]).get("SR25-build-next"), "failed")
        self.assertIn("next-env.d.ts", wrote(m))

    def test_SR25_SEC10_D20_the_end_proofs_read_the_head_the_push_sent_and_a_clean_tree(self):
        m, looked, went = self.sun("ends")
        project = m.path("dev", "demo")
        head = git(project, "rev-parse", "main").strip()
        pushed = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion" and r["op"] == "SR15-standin"][0]
        self.assertEqual(pushed["observed"]["commit"], head)
        self.assertEqual(m.statuses(looked.doc["run"])["SR25"], "passed")
        self.assertEqual(git(project, "status", "--porcelain"), "")


# ---- the brief's required items ------------------------------------------------------------------------------------
class Required(Base):
    def test_R7_SR02_electron_OP11_A153_a_scaffolders_own_git_in_staging_reaches_no_project_and_SR05_makes_the_repository(self):
        m = machine_for_sunrise(self.machine("r7", "r7"))
        install(m)
        folder = os.path.join(m.home, ".fakes", "npm")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "plan.json"), "w") as fh:
            json.dump([{"when": "create", "dot_git": True}], fh)
        looked = m.look(also=ALSO, inputs=sunrise_inputs(m, type_="desktop app", scaffold="desktop app", drop=LOCAL_ONLY,
                                                         local_proof="build electron"),
                        caps=CAPS)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, also=ALSO, caps=CAPS)
        self.assertEqual(went.ending, "complete", went.text)
        project = m.path("dev", "demo")
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual((statuses["SR02-electron"], statuses["SR05"]), ("done", "done"))
        self.assertFalse(os.path.exists(os.path.join(project, "src", ".git")))
        self.assertEqual(read(project, ".git", "HEAD"), "ref: refs/heads/main\n")
        self.assertNotIn("the fake electron scaffolder", read(project, ".git", "config"))
        operations = dict((o["id"], o) for o in manifest_of(m, looked.doc["run"])["operations"])
        self.assertEqual(operations["SR02-electron"]["repo_commands"], "none")
        self.assertEqual(git_writes(m), ["init", "add", "commit"])
        scaffolder = [c for c in m.calls("npm") if c["argv"][:1] == ["create"]]
        self.assertEqual(len(scaffolder), 1)

    def test_M1_G22_7c_RUN6_a_scaffold_with_no_typecheck_entry_has_no_typecheck_line_in_AGENTS(self):
        m, looked, went = self.sun("astro", type_="static site", scaffold="static site", drop=LOCAL_ONLY, local_proof="build astro")
        agents = read(m.path("dev", "demo", "AGENTS.md"))
        self.assertNotIn("Typecheck", agents)
        self.assertIn("- Build: `npm run build`\n", agents)
        m2, looked2, went2 = self.sun("next", drop=LOCAL_ONLY, local_proof="build next")
        self.assertIn("- Typecheck: `npx tsc --noEmit`\n", read(m2.path("dev", "demo", "AGENTS.md")))

    def test_SEAMS_ORD1_project_folder_first_commit_and_hosting_link_are_made_with_their_fields(self):
        reader = rowlib.check("SEAM-reader", "sunrise", place=F, output="seams read",
                              thing={"passes": [{"read": "path", "path": F, "is": "dir"},
                                                {"read": "ref", "repo": F, "ref": "main", "equals": {"output": "first commit.commit"}},
                                                {"read": "path", "path": {"output": "hosting link.path"}, "is": "file"}]},
                              needs=[{"output": "project folder", "level": "made", "treatment": "then not applicable"},
                                     {"output": "first commit", "level": "made", "treatment": "then not applicable"},
                                     {"output": "hosting link", "level": "made", "treatment": "then not applicable"}])
        m, looked, went = self.sun("seams", extra=[reader])
        self.assertEqual(m.statuses(looked.doc["run"])["SEAM-reader"], "passed")

    def test_SEAMS_SR14_ORD1_OP8_scanned_for_the_push_is_made_with_the_commit_of_the_head_it_scanned(self):
        reader = rowlib.check("SEAM-push-reader", "sunrise", place=F, output="push seam read",
                              thing={"passes": [{"read": "ref", "repo": F, "ref": "main", "equals": {"output": "scanned for the push.commit"}}]},
                              needs=[{"output": "scanned for the push", "level": "passed", "treatment": "then not applicable"}])
        m, looked, went = self.sun("seam14", extra=[reader])
        run = looked.doc["run"]
        self.assertEqual(m.statuses(run)["SEAM-push-reader"], "passed")
        self.assertEqual(operation(m, run, "SR14")["output"]["fields"], {"commit": {"observed": "commit"}})
        head = git(m.path("dev", "demo"), "rev-parse", "main").strip()
        scanned = [r for r in m.journal(run) if r["kind"] == "attempt" and r["op"] == "SR14" and r["answer"] == "passed"][-1]
        self.assertEqual(scanned["subject"]["word"], head)

    def test_SR03_agents_G23_13_RUN6_merge_adds_each_missing_line_under_its_heading_and_keeps_his_own(self):
        def prepare(m):
            m.put("dev/demo/AGENTS.md", "# His agents file\n## Gates\n- his own gate\n")
            m.put("dev/demo/CLAUDE.md", "@AGENTS.md\n")
        m, looked, went = self.adopted("merge", prepare)
        agents = read(m.path("dev", "demo", "AGENTS.md"))
        lines = agents.split("\n")
        self.assertEqual(lines[:3], ["# His agents file", "## Gates", "- his own gate"])
        self.assertEqual(lines[3], "- Feature branches + PRs. Never push to `main`.")      # the kit's Gates lines under his heading
        self.assertEqual(lines.count("## Gates"), 1)
        self.assertEqual(lines.count("## Commands"), 1)
        self.assertIn("## Where to look", lines)
        self.assertNotIn("## Lifted from CLAUDE.md", lines)
        self.assertEqual(m.statuses(looked.doc["run"])["SR03-agents"], "done")

    def test_SR03_agents_G24_5_RUN6_v1s_two_line_old_stub_is_replaced_by_the_body_and_the_body_lifted(self):
        def prepare(m):
            m.put("dev/demo/AGENTS.md", "# AGENTS.md\n\n%s\n" % V1_STUB)
            m.put("dev/demo/CLAUDE.md", "# His rules\nan old rule of his\n")
        m, looked, went = self.adopted("pointer", prepare)
        agents = read(m.path("dev", "demo", "AGENTS.md"))
        for line in V1_STUB.split("\n"):
            self.assertNotIn(line, agents)
        self.assertTrue(agents.startswith("# AGENTS.md\n\n# demo\n<!-- verified: 2026-01-01 -->\n"), agents[:120])
        self.assertTrue(agents.endswith("## Lifted from CLAUDE.md\n# His rules\nan old rule of his\n"), agents[-120:])
        self.assertEqual(read(m.path("dev", "demo", "CLAUDE.md")), "@AGENTS.md\n")

    def test_SR03_agents_G24_5_RUN6_v1s_stub_with_a_line_he_wrote_keeps_every_line_he_wrote(self):
        mine = "# AGENTS.md\n\n%s\nmy own line\n" % V1_STUB

        def prepare(m):
            m.put("dev/demo/AGENTS.md", mine)
            m.put("dev/demo/CLAUDE.md", "@AGENTS.md\n")
        m, looked, went = self.adopted("mine", prepare)
        agents = read(m.path("dev", "demo", "AGENTS.md"))
        self.assertTrue(agents.startswith(mine), agents[:200])
        for line in V1_STUB.split("\n") + ["my own line"]:
            self.assertEqual(agents.split("\n").count(line), 1, line)
        self.assertIn("- Feature branches + PRs. Never push to `main`.", agents)

    def test_SR03_agents_SR03_claude_G23_13_OP2_A147_where_AGENTS_is_absent_the_body_and_the_lift_are_laid_and_CLAUDE_becomes_the_stub(self):
        def prepare(m):
            m.put("dev/demo/CLAUDE.md", "# His rules\nan old rule of his\n")
        m, looked, went = self.adopted("absent", prepare)
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual((statuses["SR03-agents"], statuses["SR03-claude"]), ("done", "done"))
        agents = read(m.path("dev", "demo", "AGENTS.md"))
        self.assertTrue(agents.startswith("# demo\n"), agents[:40])
        self.assertTrue(agents.endswith("## Lifted from CLAUDE.md\n# His rules\nan old rule of his\n"), agents[-120:])
        self.assertEqual(read(m.path("dev", "demo", "CLAUDE.md")), "@AGENTS.md\n")

    def test_C1_SR03_envex_keys_ROW1_only_the_missing_key_lines_are_added_and_his_lines_kept(self):
        # the reviewer's code check C1: partial combinations, the first key already present among them
        keys = ["POSTGRES_URL=", "POSTGRES_URL_NON_POOLING=", "DATABASE_URL="]
        for n, have in enumerate((["POSTGRES_URL="], ["DATABASE_URL="], ["POSTGRES_URL=", "DATABASE_URL="],
                                  ["POSTGRES_URL_NON_POOLING="], keys)):
            with self.subTest(have=have):
                his = "# his keys\nOTHER_KEY=\n" + "".join(k + "\n" for k in have)
                m, looked, went = self.adopted("envk%d" % n, lambda m, t=his: m.put("dev/demo/.env.example", t))
                text = read(m.path("dev", "demo", ".env.example"))
                self.assertEqual(text, his + "".join(k + "\n" for k in keys if k not in have))
                lines = text.split("\n")
                for k in keys:
                    self.assertEqual(lines.count(k), 1, k)
                statuses = m.statuses(looked.doc["run"])
                for k, rid in zip(keys, ENVEX_KEYS):
                    self.assertEqual(statuses[rid], "already so" if k in have else "done", rid)

    def adopted(self, label, prepare):
        m = machine_for_sunrise(self.machine(label, label))
        prepare(m)
        install(m)
        looked = m.look(also=ALSO, inputs=sunrise_inputs(m, scaffold="adopted", adopt={"project folder": m.path("dev", "demo")}), caps=CAPS)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, also=ALSO, caps=CAPS)
        self.assertEqual(went.ending, "complete", went.text)
        return m, looked, went
