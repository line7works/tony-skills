"""Slice 3, the providers: the four declarations (rows-prov section 3.0; the frame's SEC-3 and SEC-4), and the git reads
the other lanes asked of this module (rows-rise section 7, rows-set section 7), each run on a test's own repository
through the frame's own runner and parser.

Every test's name carries the declaration's or the row's id and the rule's id.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
from sun_core import calls, results, runner, schemas, screen  # noqa: E402


def run(machine, provider, name, cwd=None, **params):
    """One declared command run by the frame's runner as the row would give it, its answer read by the frame's parser.
    Returns (results.Result, the raw exit)."""
    decl = dict(provlib.providers()[provider]["commands"][name])
    decl.setdefault("trace_flags", provlib.providers()[provider]["trace_flags"])
    argv = []
    for part in decl["template"]:
        argv.append(str(part["literal"]) if "literal" in part else str(params[part.get("param") or part.get("slot")]))
    env = dict((k, str(v.get("value", ""))) for k, v in (decl.get("env") or {}).items() if v.get("class") == "fixed")
    world = machine.world()
    run_dir = os.path.join(machine.root, "rundir-" + machine.seed)
    os.makedirs(run_dir, exist_ok=True)
    register = screen.Screen()
    context = runner.Context(register, run_dir, machine.facts.search_list(world.fs, world.system_folders))
    fields = []
    for field in decl.get("fields") or []:
        spec = field.get("equals") or {}
        field = dict(field)
        if "literal" in spec:
            field["equals_value"] = spec["literal"]
        elif "param" in spec and spec["param"] in params:
            field["equals_value"] = params[spec["param"]]
        elif "settings" in spec:
            field["equals_value"] = list(machine.settings["accounts"].get(spec["settings"], []))
        fields.append(field)
    decl["fields"] = fields
    raw = runner.run(world, context, decl, argv, env, cwd or run_dir)
    return results.Parser(decl, raw, register).finish(), raw.exit_code


class Declarations(harness.Case):
    def test_SEC3_SEC4_the_four_provider_declarations_ship_under_the_rows_root_and_pass_the_provider_schema(self):
        for name in ("github", "vercel", "postgres", "web"):
            with self.subTest(provider=name):
                doc = provlib.shipped("providers", name + ".json")
                self.assertEqual(doc["provider"], name)
                self.assertEqual(schemas.errors("provider", doc), [])
        # the alternatives column is `none` throughout (ORD-3): no command declares an alternative result
        for name in ("github", "vercel", "postgres", "web"):
            for cname, decl in provlib.shipped("providers", name + ".json")["commands"].items():
                self.assertFalse(decl.get("alternatives"), (name, cname))

    def test_SEC3_G19_10_trace_flags_by_meaning_per_command_psql_v_is_no_trace_flag_and_gits_are_its_own(self):
        decls = provlib.shipped("providers", "postgres.json")["commands"]
        self.assertNotIn("-v", decls["inventory"]["trace_flags"])
        self.assertIn("-v", decls["dump"]["trace_flags"])
        gh = provlib.shipped("providers", "github.json")
        self.assertEqual(gh["trace_flags"], ["--verbose", "--debug"])
        self.assertEqual(gh["commands"]["push"]["trace_flags"], ["--verbose", "-v"])
        self.assertEqual(gh["commands"]["push"]["env"], {"GIT_TERMINAL_PROMPT": {"class": "fixed", "value": "0"}})
        self.assertEqual(sorted(gh["commands"]["create"]["env"]), ["GH_NO_UPDATE_NOTIFIER", "GH_PROMPT_DISABLED", "NO_COLOR"])

    def test_SEC2_SEC4_G19_9_vercel_has_one_identity_read_per_route_each_equal_to_his_settings(self):
        vercel = provlib.shipped("providers", "vercel.json")
        # each route's one parameter `team` takes each name his settings hold for vercel (G23-4; part one's machinery request 1
        # for the request route, part two's machinery request 1 for the runner route, met by G24-2's `text` part)
        team = {"team": {"settings": "vercel"}}
        self.assertEqual(vercel["identity"], {"request": {"command": "team", "field": "slug", "params": team},
                                              "runner": {"command": "cli-team", "field": "slug", "params": team}})
        self.assertEqual(vercel["commands"]["cli-team"]["template"],
                         [{"literal": "api"}, {"text": [{"literal": "/v2/teams/"}, {"param": "team"}]}, {"literal": "--non-interactive"},
                          {"literal": "--no-color"}, {"literal": "--scope"}, {"param": "team"}])
        self.assertEqual(vercel["commands"]["team"]["via"], "request")
        self.assertNotEqual(vercel["commands"]["cli-team"].get("via"), "request")
        for command in ("team", "cli-team"):
            self.assertEqual(vercel["commands"][command]["fields"][0]["equals"], {"settings": "vercel"})


class IdentityFromSettings(harness.Case):
    def test_G23_4_RUN5_SEC4_C_vercels_request_identity_is_read_with_each_team_his_settings_hold_until_one_proves_equal(self):
        """Part one's machinery request 1, met by G23-4 for the request route: the shipped `team` read, no stand-in, is made
        with each name his settings hold for vercel in their order; the host does not know the first (404, not-found, passed
        over), the second proves equal and is the account the manifest records."""
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_lane_prov_rise import sunrise
        m = provlib.wire(self.machine())
        m.settings["accounts"]["vercel"] = ["other-team", provlib.TEAM]
        m.write_settings()
        sunrise(m)
        self.assertEqual(provlib.providers()["vercel"], provlib.shipped("providers", "vercel.json"))     # no route has a stand-in
        looked = m.look(inputs=provlib.rise_inputs(m))
        teams = [r["path"] for r in provlib.requests(m, "GET") if r["path"][:2] == ["v2", "teams"]]
        self.assertEqual(teams, [["v2", "teams", "other-team"], ["v2", "teams", provlib.TEAM]])
        # Not written, pending part three's Question 1: the look's ending and the manifest's account where his settings hold
        # two vercel names. The runner route now reads with each name too (G24-2), and the CLI's exit for a team its session
        # cannot act for is 1, `other` (rows-prov 3.0), which G23-4 does not pass over as it does a `not-found`

    def test_G24_2_RUN5_SEC4_C_vercels_runner_identity_cli_team_takes_his_team_into_the_path_and_the_scope(self):
        """Part two's machinery request 1, met by G24-2: the shipped `cli-team`, no stand-in, is `vercel api /v2/teams/<team>`
        and the CLI flags ending `--scope <team>`, the one name of his settings in both (rows-prov 3.0: "runner: `vercel api
        /v2/teams/<account vercel>` + the CLI flags"); the look proves it, and the manifest records the team."""
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_lane_prov_rise import sunrise
        m = provlib.wire(self.machine())
        sunrise(m)
        self.assertEqual(provlib.providers()["vercel"], provlib.shipped("providers", "vercel.json"))
        looked = m.look(inputs=provlib.rise_inputs(m))
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual([c["argv"] for c in provlib.calls(m, "vercel", "cli-team")],
                         [["api", "/v2/teams/" + provlib.TEAM, "--non-interactive", "--no-color", "--scope", provlib.TEAM]])
        with open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")) as fh:
            self.assertEqual(json.load(fh)["accounts"]["vercel"], provlib.TEAM)

    def test_G23_4_RUN5_no_team_of_his_settings_known_to_the_host_ends_the_look_as_the_wrong_account(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_lane_prov_rise import sunrise
        m = provlib.wire(self.machine())
        m.settings["accounts"]["vercel"] = ["other-team"]
        m.write_settings()
        sunrise(m)
        looked = m.look(inputs=provlib.rise_inputs(m))
        self.assertNotEqual(looked.ending, "preview", looked.text)
        self.assertIn("the read was made as the wrong account: vercel reports an account your settings do not name", looked.text)
        self.assertEqual(provlib.requests(m, "POST"), [])


def commit_row(repo):
    """A stand-in of slice 2's SR07 (rows-rise 3.8), only as far as this test needs it: a C6 commit of what is staged, its
    before-test the index differing from the head (`staged-diff` conflict), its after-test the two equal; the commit is
    github.json's `commit` as shipped, a plain `git -C <repo> commit -q -m <message>`."""
    import rowlib
    repo_v = rowlib.lit(repo)
    return rowlib.row(
        "change", "SR07s", "sunrise",
        thing={"role": "the branch main (slice 2's SR07, stand-in)", "identity": "named value", "before_word": "staged",
               "after_word": "committed"},
        planning_test=[{"read": "command", "command": "staged", "result": "conflict"}],
        before_test=[{"id": "staged", "read": "command", "command": "staged", "result": "conflict", "on": "target"}],
        after_test=[{"read": "command", "command": "staged", "result": "success"}],
        construction={"id": "C6", "command": "commit", "risks": ["RK18"],
                      "risk_line": "something staged by hand between the scan and the commit is committed unscanned"},
        commands=[rowlib.use("staged", "github.staged-diff", work=repo_v),
                  rowlib.use("commit", "github.commit", repo=repo_v, message=rowlib.lit("sunrise: the scaffold"))],
        repo_commands=["commit"],
        after_check=[{"read": "command", "command": "staged", "result": "success"}],
        output={"name": "first commit", "fields": {}},
        way_back={"none": "a commit is history"},
        content_classes={"reads": ["safe"], "stores": ["safe"], "shows": ["safe"], "validators": [], "resting_places": []},
        form_lines={"preview": "commit what is staged", "status": "committed what was staged"})


class CommitHooks(harness.Case):
    def test_item3_SR07s_OP6_a_pre_commit_hook_that_exits_1_fails_the_commit_and_the_run_stops(self):
        """Item 3, the owner's pick ("Hooks run, as v1"): github.json's `commit` carries no hook word, so a repository's own
        pre-commit hook runs; one that exits 1 fails the commit, nothing is committed and the run stops. The control: the
        same repository without the hook commits and completes."""
        import rowlib
        self.assertNotIn("core.hooksPath=/dev/null",
                         [p.get("literal") for p in provlib.shipped("providers", "github.json")["commands"]["commit"]["template"]])
        for hook, ending in ((True, "stopped"), (False, "complete")):
            with self.subTest(hook=hook):
                m = provlib.wire(self.machine("k%s" % hook, "k%s" % hook))
                repo, first = provlib.project_repo(m)
                m.put("dev/demo/new.txt", "new\n")
                provlib.git(repo, "add", "new.txt")
                if hook:
                    path = os.path.join(repo, ".git", "hooks", "pre-commit")
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as fh:
                        fh.write("#!/bin/sh\nexit 1\n")
                    os.chmod(path, 0o755)
                lane = provlib.lane("sunrise", [commit_row(repo)], ("sunrise",),
                                    part={"rows": [], "form_changes": {"the RK18 mark": provlib.RK18}})
                provlib.install(m, lane)
                looked = m.look(inputs=provlib.rise_inputs(m))
                self.assertEqual(looked.ending, "preview", looked.text)
                went = m.go(looked)
                self.assertEqual(went.ending, ending, went.text)
                head = provlib.git(repo, "rev-parse", "HEAD")
                self.assertEqual(head == first, hook, "the commit landed despite the hook" if hook else "no commit")


class GitReads(harness.Case):
    """Required item 3: the git reads slices 2 and 4 asked of this module, each run on a test's own repository."""

    def repo(self, m, committed=True):
        m = provlib.wire(m)
        repo, commit = provlib.project_repo(m) if committed else (m.path("dev", "demo"), None)
        return m, repo, commit

    def test_seam_SR00_git_config_email_and_name_success_where_his_git_names_him_not_found_where_it_does_not(self):
        m, repo, _ = self.repo(self.machine())
        for name in ("config-email", "config-name"):
            self.assertEqual(run(m, "github", name)[0].kind, "success", name)
        with open(m.path(".config", "git", "config"), "w") as fh:
            fh.write("[init]\n\tdefaultBranch = main\n")
        for name in ("config-email", "config-name"):
            self.assertEqual(run(m, "github", name)[0].kind, "not-found", name)

    def test_seam_SR07_git_staged_diff_success_where_the_index_is_the_head_conflict_where_it_differs(self):
        m, repo, _ = self.repo(self.machine())
        self.assertEqual(run(m, "github", "staged-diff", work=repo)[0].kind, "success")
        m.put("dev/demo/new.txt", "new\n")
        provlib.git(repo, "add", "new.txt")
        self.assertEqual(run(m, "github", "staged-diff", work=repo)[0].kind, "conflict")

    def test_seam_SR13_git_agents_committed_success_where_the_head_holds_AGENTS_md_not_found_where_not(self):
        m, repo, _ = self.repo(self.machine())
        self.assertEqual(run(m, "github", "agents-committed", work=repo)[0].kind, "not-found")
        m.put("dev/demo/AGENTS.md", "# agents\n")
        provlib.git(repo, "add", "AGENTS.md")
        provlib.git(repo, "commit", "-q", "-m", "agents")
        self.assertEqual(run(m, "github", "agents-committed", work=repo)[0].kind, "success")
        # its exact path and case: agents.md is not AGENTS.md
        m2, repo2, _ = self.repo(self.machine("h2", "h2"))
        m2.put("dev/demo/docs/AGENTS.md", "# agents\n")
        provlib.git(repo2, "add", "-A")
        provlib.git(repo2, "commit", "-q", "-m", "deep")
        self.assertEqual(run(m2, "github", "agents-committed", work=repo2)[0].kind, "not-found")

    def test_seam_T12_git_tracked_clean_success_where_nothing_tracked_changed_conflict_where_it_did(self):
        m, repo, _ = self.repo(self.machine())
        self.assertEqual(run(m, "github", "tracked_clean", repo=repo)[0].kind, "success")
        m.put("dev/demo/README.md", "# changed\n")
        self.assertEqual(run(m, "github", "tracked_clean", repo=repo)[0].kind, "conflict")

    def test_seam_T12_git_untracked_none_measured_exit_1_is_none_untracked_and_0_is_some(self):
        m, repo, _ = self.repo(self.machine())
        result, code = run(m, "github", "untracked_none", repo=repo)
        self.assertEqual((code, result.kind), (1, "success"))
        m.put("dev/demo/loose.txt", "loose\n")
        result, code = run(m, "github", "untracked_none", repo=repo)
        self.assertEqual((code, result.kind), (0, "conflict"))
        # a file the repository ignores is no untracked file
        os.remove(m.path("dev/demo/loose.txt"))
        m.put("dev/demo/.env.local", "X=1\n")
        result, code = run(m, "github", "untracked_none", repo=repo)
        self.assertEqual((code, result.kind), (1, "success"))
        # outside a repository: 128, other
        os.makedirs(m.path("dev", "plain"))
        result, code = run(m, "github", "untracked_none", repo=m.path("dev", "plain"))
        self.assertEqual((code, result.kind), (128, "other"))

    def test_seam_T12_git_unpushed_count_reads_the_count_at_the_answers_top_level_equal_to_0(self):
        m, repo, commit = self.repo(self.machine())
        result, _ = run(m, "github", "unpushed_count", repo=repo)
        self.assertEqual(result.kind, "success")
        self.assertFalse(result.fields["count"].equal)          # one commit no remote holds: not 0
        bare = m.path("bare.git")
        provlib.git(m.home, "init", "-q", "--bare", bare)
        provlib.git(repo, "remote", "add", "origin", bare)
        provlib.git(repo, "push", "-q", "origin", "main")
        result, _ = run(m, "github", "unpushed_count", repo=repo)
        self.assertTrue(result.fields["count"].equal)
        self.assertEqual(result.fields["count"].safe, 0)

    def test_seam_SR05_SR07_git_writes_init_branch_main_add_all_commit_and_the_clean_read(self):
        m = provlib.wire(self.machine())
        work = m.path("dev", "fresh")
        self.assertEqual(run(m, "github", "init", path=work)[0].kind, "success")
        self.assertTrue(os.path.isdir(os.path.join(work, ".git")))
        self.assertEqual(provlib.git(work, "symbolic-ref", "HEAD"), "refs/heads/main")
        m.put("dev/fresh/a.txt", "a\n")
        self.assertEqual(run(m, "github", "add-all", repo=work)[0].kind, "success")
        self.assertEqual(run(m, "github", "commit", repo=work, message="first")[0].kind, "success")
        self.assertEqual(run(m, "github", "clean", repo=work)[0].kind, "success")
        m.put("dev/fresh/a.txt", "changed\n")
        self.assertEqual(run(m, "github", "clean", repo=work)[0].kind, "conflict")
        provlib.git(work, "checkout", "-q", "-b", "trunk")
        self.assertEqual(run(m, "github", "branch-main", repo=work, old="trunk")[0].kind, "other")    # main exists: 128
        provlib.git(work, "branch", "-q", "-D", "main")
        self.assertEqual(run(m, "github", "branch-main", repo=work, old="trunk")[0].kind, "success")
        self.assertEqual(provlib.git(work, "symbolic-ref", "HEAD"), "refs/heads/main")


if __name__ == "__main__":
    import unittest
    unittest.main()
