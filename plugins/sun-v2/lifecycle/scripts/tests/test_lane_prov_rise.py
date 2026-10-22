"""Slice 3, the providers: the sunrise rows (rows-prov section 3.2) as the join leaves them, in slice 2's shipped
`sunrise/lane.json`, run over the four fakes on slice 2's own fixture machine (`test_lane_rise.machine_for_sunrise`, which
`provlib.wire` completes): a whole sunrise, slice 2's rows giving the outputs these rows need (no stand-in).

Every test's name carries the row's id and the rule's id.
"""
import copy
import json
import os
import stat
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_rise as rise  # noqa: E402
from sun_core import journal as journalmod, plan, protected, rows as rowsmod, state as statemod  # noqa: E402

ROWS = ("SR08", "SR09", "SR15", "SR16", "SR17", "SR17c", "SR19")


def sunrise(m, **inputs):
    """Slice 2's fixture machine, slice 3's fakes wired into it, the shipped lane; a web app scaffolded at <dev>/demo."""
    rise.machine_for_sunrise(m)
    rise.install(m)
    m.rise_inputs = rise.sunrise_inputs(m, **inputs)
    return m.path("dev", "demo")


def look(m, **kw):
    return m.look(also=rise.ALSO, inputs=m.rise_inputs, caps=rise.CAPS, **kw)


def go(m, looked, **kw):
    return m.go(looked, also=rise.ALSO, caps=rise.CAPS, **kw)


def started(m):
    looked = look(m)
    assert looked.doc and looked.doc.get("manifest_sha256"), looked.text
    return looked, go(m, looked)


def resume(m):
    return m.resume(also=rise.ALSO, caps=rise.CAPS)


def head(repo):
    return provlib.git(repo, "rev-parse", "HEAD")


def lane_row(rid):
    return [r for r in provlib.shipped("sunrise", "lane.json")["rows"] if r["id"] == rid][0]


def env_values(m):
    """The project's variables at the fake host, by environment: two plain, one Sensitive, each in every environment."""
    secret = harness.canary("rise-env")
    every = ["development", "preview", "production"]
    provlib.put_state(m, "vercel", envs={"demo": [{"key": "DATABASE_URL", "value": "postgres://u:%s@db.invalid/demo" % secret,
                                                   "type": "encrypted", "target": every},
                                                  {"key": "FEATURE", "value": "on", "type": "plain", "target": every},
                                                  {"key": "SIGNING_KEY", "value": harness.canary("sensitive"), "type": "sensitive",
                                                   "target": every}]})
    return secret


def read_file(path):
    with open(path) as fh:
        return fh.read()


def outputs(m, run):
    with open(os.path.join(m.facts.run_dir(run), "manifest-1.json")) as fh:
        manifest = json.load(fh)
    state = statemod.State(manifest, journalmod.Journal(m.facts.run_dir(run), m.journal(run)))
    return state.outputs


def read_held(m, run, value):
    return protected.read(m.world().fs, m.facts.run_dir(run), value.reference).decode()


def another_main(m):
    """Another's commit pushed to the remote's main, from a repository of its own."""
    other = m.path("other")
    os.makedirs(other)
    provlib.git(other, "init", "-q")
    m.put("other/x.txt", "another's\n")
    provlib.git(other, "add", "-A")
    provlib.git(other, "commit", "-q", "-m", "another's")
    provlib.git(other, "push", "-q", os.path.join(m.home, ".fakes", "gh", "remotes", provlib.ACCOUNT, "demo.git"), "main")
    return provlib.remote_head(m)


class Admission(harness.Case):
    def test_ROW1_ROW3_the_joined_sunrise_lane_is_admitted_with_its_checklist_answered(self):
        lane = provlib.shipped("sunrise", "lane.json")
        decls = provlib.providers()
        self.assertEqual(plan.admit_all(lane, plan.expand(lane, decls), decls), [])
        ids = [r["id"] for r in lane["rows"]]
        self.assertEqual([i for i in ids if i in ROWS], list(ROWS))
        self.assertEqual(sorted(set(r["phase"] for r in lane["rows"] if r["id"] in ROWS)), ["sunrise"])
        # the checklist fails naming the item where one names a row the lane does not hold
        broken = copy.deepcopy(lane)
        broken["checklist"].append({"item": "a planted item", "answered_by": {"row": "SR99"}})
        self.assertIn({"item": "a planted item", "finding": "names a row that does not exist"}, rowsmod.checklist_findings(broken))


class EndToEnd(harness.Case):
    def test_SR08_SR09_SR15_SR16_SR17_SR17c_SR19_RUN8_OP2_a_sunrise_over_the_fakes_looked_previewed_approved_and_complete(self):
        m = self.machine()
        repo = sunrise(m)
        secret = env_values(m)
        looked = look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        with open(looked.doc["forms"][0]) as fh:
            preview = fh.read()
        for line in ("GitHub: create the private repository demo as fixture-account (no push)",
                     "Hosting: create demo as fixture-team, connected to fixture-account/demo",
                     "GitHub: push main once (the scanned commit)", "Database: Supabase through the Marketplace, demo-db",
                     "Env: pull the development values to .env.local (owner-only, ignored)",
                     "acts at github as: fixture-account", "acts at vercel as: fixture-team",
                     "carried under v1's own risk for this step (RK18): a resource of that name made by another"):
            self.assertIn(line, preview)
        # RUN-5: the look made only reads at the fakes
        # (J6c: SR08 reads by the repository's address, `repo-at`, and SR17 the team's resources, `db-all`)
        self.assertEqual([c["command"] for c in provlib.calls(m, "gh")], ["whoami", "repo-at"])
        self.assertEqual(sorted(set(c["command"] for c in provlib.calls(m, "vercel") if "command" in c)), ["cli-team", "db-all", "db-installed"])
        self.assertEqual([r["request"] for r in provlib.requests(m)], ["GET", "GET"])
        went = go(m, looked)
        self.assertEqual(went.ending, "complete", went.text)
        statuses = m.statuses(run)
        for op in ("SR08", "SR09", "SR15", "SR17", "SR17c", "SR19"):
            self.assertEqual(statuses.get(op), "done", op)
        self.assertEqual(statuses.get("SR16"), "passed")
        # SR08: one private repository, made once
        gh = provlib.state(m, "gh")
        self.assertEqual(sorted(gh["things"]), ["demo"])
        self.assertTrue(gh["things"]["demo"]["private"])
        self.assertEqual([c["command"] for c in provlib.calls(m, "gh")].count("create"), 1)
        # SR15: the remote's main is the scanned commit, slice 2's first commit, one push
        self.assertEqual(provlib.remote_head(m), head(repo))
        # SR09: one project at the host, linked to the repository; created by one request of the frame's own, with the token
        host = provlib.state(m, "vercel")
        self.assertEqual(sorted(t for t, v in host["things"].items() if v["kind"] == "project"), ["demo"])
        self.assertEqual(host["things"]["demo"]["repo"], "demo")
        posts = provlib.requests(m, "POST")
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["body"], {"gitRepository": {"repo": "fixture-account/demo", "type": "github"}, "name": "demo"})
        self.assertTrue(all(r["token"] for r in provlib.requests(m)))
        # SR17, SR17c: one resource demo-db, connected to the project
        self.assertEqual(sorted(host["resources"]), ["demo-db"])
        self.assertEqual((host["resources"]["demo-db"]["connected"], host["resources"]["demo-db"]["project"]), (True, "demo"))
        # SR19: the pulled env file, owner-only, holding the development values; the Sensitive value is nowhere
        env_file = os.path.join(repo, ".env.local")
        self.assertEqual(stat.S_IMODE(os.stat(env_file).st_mode), 0o600)
        with open(env_file) as fh:
            pulled = fh.read()
        self.assertIn(secret, pulled)
        self.assertIn('SIGNING_KEY=""', pulled)
        self.assertNowhere(secret, went)
        self.assertNowhere(secret, looked)
        for form in went.doc["forms"]:
            with open(form) as fh:
                self.assertNotIn(secret, fh.read())
        # SR16: the deployment read for the pushed commit and the address's status
        status = "".join(read_file(p) for p in went.doc["forms"])
        # the join's punch list (b), the reviewer's P4: one line for either outcome, which never says live (Machinery request 3
        # for rows-prov section 5's two lines)
        self.assertIn("[SR16] the check passed: Verify: the deployment reads READY and https://demo.vercel.app/ answered 200, "
                      "for the pushed commit", status)
        self.assertEqual(len(provlib.calls(m, "web", "status")), 1)
        with open(os.path.join(os.environ.get("SUN_V2_PROV_FORMS", m.root), "rise-forms.txt"), "w") as fh:
            fh.write(preview + "\n=====\n" + status)

    def test_seam_SR08_SR09_SR15_SR16_SR17_SR17c_SR19_each_output_slice_2_takes_is_made_with_its_fields(self):
        m = self.machine()
        repo = sunrise(m)
        env_values(m)
        looked, went = started(m)
        self.assertEqual(went.ending, "complete", went.text)
        run = looked.doc["run"]
        bound = outputs(m, run)
        gh = provlib.state(m, "gh")["things"]["demo"]
        host = provlib.state(m, "vercel")
        self.assertEqual(sorted(bound["remote repository"]), ["address", "id", "name"])
        self.assertEqual(read_held(m, run, bound["remote repository"]["id"]), gh["id"])
        self.assertEqual(bound["remote repository"]["name"], "demo")
        self.assertEqual(bound["remote repository"]["address"], "https://github.com/fixture-account/demo")
        self.assertEqual(sorted(bound["hosting project"]), ["account", "address", "id", "slug"])
        self.assertEqual(read_held(m, run, bound["hosting project"]["id"]), host["things"]["demo"]["id"])
        self.assertEqual(bound["hosting project"]["address"], "https://demo.vercel.app")
        self.assertEqual(bound["push"], {"commit": provlib.remote_head(m)})
        # `deployment` is a check's output, bound at its pass with no field (G23-1); slice 2 takes it at the `passed` level
        self.assertEqual(bound["deployment"], {})
        self.assertEqual(m.statuses(run)["SR16"], "passed")
        # G23-2 (part one's machinery request 5): `hosting project.account` binds the create's own `accountId`, not its id
        self.assertEqual(read_held(m, run, bound["hosting project"]["account"]), host["things"]["demo"]["account"])
        self.assertNotEqual(host["things"]["demo"]["account"], host["things"]["demo"]["id"])
        self.assertEqual(sorted(bound["database"]), ["name", "resource"])
        self.assertEqual(bound["database"]["name"], "demo-db")
        self.assertEqual(read_held(m, run, bound["database"]["resource"]), host["resources"]["demo-db"]["id"])
        self.assertIn("database connected", bound)
        self.assertEqual(bound["env file"], {"path": os.path.join(repo, ".env.local")})


class Seams(harness.Case):
    def test_seam_SR15_ORD1_G23_1_the_shipped_SR15_pushes_the_commit_slice_2s_scanned_for_the_push_check_bound_at_its_pass(self):
        """Slice 2's `scanned for the push` (SR14) is a check whose `commit` binds at its pass, so the shipped SR15 pushes that
        commit, slice 2's first commit (the join: SR14 is the shipped row, no stand-in)."""
        m = self.machine()
        repo = sunrise(m)
        env_values(m)
        self.assertIn({"output": "scanned for the push.commit"}, [c["params"].get("commit") for c in lane_row("SR15")["commands"]])
        looked, went = started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(provlib.remote_head(m), head(repo))
        self.assertEqual(outputs(m, looked.doc["run"])["scanned for the push"], {"commit": head(repo)})

    def test_seam_SR09_SR10_G23_2_slice_2s_link_file_gets_orgId_from_hosting_project_account(self):
        """Slice 2's SR10 (the shipped row, no stand-in) builds `.vercel/project.json` from SR09's held `id` and `account` as
        `projectId` and `orgId`; `orgId` is the project's accountId at the host (G23-2)."""
        m = self.machine()
        repo = sunrise(m)
        env_values(m)
        looked, went = started(m)
        self.assertEqual(went.ending, "complete", went.text)
        project = provlib.state(m, "vercel")["things"]["demo"]
        with open(os.path.join(repo, ".vercel", "project.json")) as fh:
            linked = json.load(fh)
        self.assertEqual(linked, {"projectId": project["id"], "orgId": project["account"]})


class Visibility(harness.Case):
    def test_J1c_SR08_SR08_public_ORD3_with_his_public_the_repository_is_public_and_without_it_private_as_v1(self):
        """The join's J1c, the owner's pick "Keep --public, as v1": `flags.public`, given only where he asks for a public
        repository, makes SR08-public create it public (`private=false`); without it SR08 creates it private, as v1's
        default. The preview says which; the fake's state and its call record say what was made."""
        for public in (True, None):
            with self.subTest(public=public):
                m = self.machine("p%s" % public, "p%s" % public)
                sunrise(m, public=public)
                looked = look(m)
                self.assertEqual(looked.ending, "preview", looked.text)
                preview = read_file(looked.doc["forms"][0])
                word = "public" if public else "private"
                self.assertIn("GitHub: create the %s repository demo as fixture-account (no push)" % word, preview)
                went = go(m, looked)
                self.assertEqual(went.ending, "complete", went.text)
                statuses = m.statuses(looked.doc["run"])
                self.assertEqual(statuses.get("SR08-public" if public else "SR08"), "done")
                self.assertNotIn("SR08" if public else "SR08-public", statuses)
                self.assertEqual(provlib.state(m, "gh")["things"]["demo"]["private"], not public)
                made = provlib.calls(m, "gh", "create")
                self.assertEqual(len(made), 1)
                self.assertIn("private=%s" % ("false" if public else "true"), made[0]["argv"])


class VisibilityFalse(harness.Case):
    def test_J1d_SR08_false_ORD3_GOV1_his_public_given_as_false_creates_the_repository_private_as_absent_does(self):
        """The join's J1d: `flags.public` given as `false` matched neither SR08 (absent) nor SR08-public (`true`), and the run
        made no repository at all, silently (GOV-1). It now plans SR08-false, a private create as SR08's, by the one condition
        the existing marks express (`flags.public` equals `false`): a private repository, one create, `private=true`."""
        m = self.machine()
        sunrise(m, public=False)
        looked = look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("GitHub: create the private repository demo as fixture-account (no push)", read_file(looked.doc["forms"][0]))
        went = go(m, looked)
        self.assertEqual(went.ending, "complete", went.text)
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual(statuses.get("SR08-false"), "done")
        self.assertEqual([op for op in ("SR08", "SR08-public") if op in statuses], [])
        self.assertTrue(provlib.state(m, "gh")["things"]["demo"]["private"])
        made = provlib.calls(m, "gh", "create")
        self.assertEqual(len(made), 1)
        self.assertIn("private=true", made[0]["argv"])
        self.assertEqual(provlib.remote_head(m), head(m.path("dev", "demo")))


def adopted_with(m, setup):
    """Her fixture (the reviewer's join check, J1 and J2): an adopted repository at <dev>/demo, made and configured by
    `setup` before the look, the shipped lane, the inputs of an adopted web app."""
    rise.machine_for_sunrise(m)
    repo = m.path("dev", "demo")
    os.makedirs(repo)
    provlib.git(repo, "init", "-q")
    setup(m, repo)
    rise.install(m)
    m.rise_inputs = rise.sunrise_inputs(m, scaffold="adopted", adopt={"project folder": repo})
    env_values(m)
    return repo


def has_main(bare):
    import subprocess
    return subprocess.run(["/usr/bin/git", "--git-dir", bare, "rev-parse", "--verify", "-q", "refs/heads/main"],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).returncode == 0


class OriginAndUpstream(harness.Case):
    def test_J1e_J1_SR15_origin_GOV1_OP5_an_origin_naming_another_repository_is_foreign_and_nothing_is_pushed(self):
        """The reviewer's J1: an adopted repository whose `origin` names another repository, the intended address under
        another remote. SR15-origin reads `origin`'s own URL, which must equal the intended address (and no push URL of its
        own): here it does not, so the probe reads `foreign` and the run stops there, before SR15 sends anything; neither the
        wrong repository nor the intended one receives a commit."""
        def setup(m, repo):
            other = m.path("other.git")
            provlib.git(m.home, "init", "-q", "--bare", other)
            provlib.git(repo, "remote", "add", "origin", other)
            provlib.git(repo, "remote", "add", "backup", "https://github.com/fixture-account/demo")
        m = self.machine()
        adopted_with(m, setup)
        looked = look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = go(m, looked)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("foreign", went.text)
        self.assertIn("SR15-origin", went.text)
        statuses = m.statuses(looked.doc["run"])
        self.assertNotIn("SR15-origin", statuses)
        self.assertNotIn("SR15", statuses)
        self.assertFalse(has_main(m.path("other.git")), "the wrong repository received a commit")
        self.assertIsNone(provlib.remote_head(m), "the intended repository received a commit")

    def test_J1e_J2_SR15_upstream_GOV1_OP5_mains_own_upstream_is_read_and_another_branchs_lines_never_satisfy_it(self):
        """The reviewer's J2: before the adoption, `main` tracks `backup`'s `other`, and the branch `other` holds the lines
        `remote = origin` and `merge = refs/heads/main`. SR15-upstream reads `main`'s own `remote` and `merge`: they are not
        `origin` and `refs/heads/main`, nor absent, so the probe reads `foreign` and the run stops; it never reads `already
        so`, and `main`'s upstream is never left wrong behind a `complete`."""
        def setup(m, repo):
            for key, value in (("branch.main.remote", "backup"), ("branch.main.merge", "refs/heads/other"),
                               ("branch.other.remote", "origin"), ("branch.other.merge", "refs/heads/main")):
                provlib.git(repo, "config", key, value)
        m = self.machine()
        repo = adopted_with(m, setup)
        looked = look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = go(m, looked)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("foreign", went.text)
        self.assertIn("SR15-upstream", went.text)
        self.assertNotIn("SR15-upstream", m.statuses(looked.doc["run"]))
        self.assertEqual((provlib.git(repo, "config", "branch.main.remote"), provlib.git(repo, "config", "branch.main.merge")),
                         ("backup", "refs/heads/other"), "main's upstream was changed")


class Refusals(harness.Case):
    def test_SR08_RUN7_a_repository_of_that_name_already_at_github_ends_the_look_with_the_place_taken(self):
        m = self.machine()
        sunrise(m)
        provlib.put_state(m, "gh", account=provlib.ACCOUNT, things={"demo": {"id": "R_x", "kind": "repo", "state": "active", "name": "demo"}})
        looked = look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the place is taken by a thing this run did not make: row SR08", looked.text)
        self.assertEqual(provlib.calls(m, "gh", "create"), [])

    def test_SR09_RUN7_A4_a_project_of_that_name_at_the_host_ends_the_look_with_the_place_taken(self):
        m = self.machine()
        sunrise(m)
        provlib.put_state(m, "vercel", things={"demo": {"id": "prj_x", "kind": "project", "state": "active", "name": "demo",
                                                        "account": "team_x"}})
        looked = look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the place is taken by a thing this run did not make: row SR09", looked.text)

    def test_SR17_RUN7_G23_10_the_marketplace_terms_not_accepted_end_the_look_in_the_rows_own_words(self):
        """The terms' planning test carries its own stop line (rows-prov section 4), and the look ends with it, not with the
        generic "place is taken" line (G23-10)."""
        m = self.machine()
        sunrise(m)
        provlib.put_state(m, "vercel", installed=False)
        looked = look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("Accept the Marketplace's terms for Supabase once: run `vercel integration accept-terms supabase`, "
                      "then summon sunrise again.", looked.text)
        self.assertNotIn("the place is taken by a thing this run did not make: row SR17", looked.text)
        self.assertEqual(provlib.calls(m, "vercel", "db-add"), [])

    def test_SR17_SR17c_SR19_ORD3_flags_db_false_leaves_the_three_not_applicable(self):
        m = self.machine()
        sunrise(m, drop=("database",))
        looked = look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        with open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")) as fh:
            manifest = json.load(fh)
        self.assertEqual(sorted(n["row"] for n in manifest["not_applicable"] if n["row"] in ROWS), ["SR17", "SR17c", "SR19"])
        self.assertEqual(sorted(o["id"] for o in manifest["operations"] if o["id"] in ROWS), ["SR08", "SR09", "SR15", "SR16"])

    def test_SR15_OP3_C4_a_commit_on_the_remotes_main_before_the_push_stops_it_and_no_second_push(self):
        m = self.machine()
        repo = sunrise(m)
        env_values(m)
        looked = look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        # killed just after SR08's completion record: the remote stands, empty
        went = go(m, looked, kill=lambda e: e["op"] == "append" and e["stage"] == "post" and m.statuses(looked.doc["run"]).get("SR08") == "done")
        self.assertTrue(went.killed, went.text)
        theirs = another_main(m)
        resumed = resume(m)
        self.assertEqual(resumed.ending, "stopped", resumed.text)
        self.assertEqual(provlib.remote_head(m), theirs)
        self.assertNotEqual(theirs, head(repo))

    def test_SR15_OP5_OP6_G24_1_a_main_another_pushed_before_SR15s_probe_is_foreign_and_no_push_is_made(self):
        """G24-1: SR15's after-test and after-check are rows-prov's equality, the remote's `head` equal to `scanned for the
        push.commit`. Another's commit on the remote's main before SR15's own probe (the run killed just after SR08 made the
        repository, SR15 not yet started, so the resume probes it fresh): `foreign`, which stops at SR15."""
        m = self.machine()
        repo = sunrise(m)
        env_values(m)
        looked = look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        went = go(m, looked, kill=lambda e: e["op"] == "append" and e["stage"] == "post" and m.statuses(run).get("SR08") == "done")
        self.assertTrue(went.killed, went.text)
        self.assertNotIn("SR15", m.statuses(run))
        theirs = another_main(m)
        resumed = resume(m)
        self.assertEqual(resumed.ending, "stopped", resumed.text)
        self.assertIn("foreign", resumed.text)
        self.assertIn("SR15", resumed.text)
        self.assertNotIn("SR15", m.statuses(run), "another's main was given a status")
        self.assertEqual([r["kind"] for r in m.journal(run) if r.get("op") == "SR15" and r["kind"] in ("start", "status")], [],
                         "SR15 was started or given a status")
        self.assertEqual(provlib.remote_head(m), theirs)
        self.assertNotEqual(theirs, head(repo))
        # the join's punch list (e), G24 F2's G24-1 row, completing `test_g24_machinery`'s `AbsentFieldEquality`: the
        # repository's held id, read by the same `repo-read` whose `head` decided `foreign`, is in no output of the run (SEC-1)
        self.assertNowhere(provlib.state(m, "gh")["things"]["demo"]["id"], resumed)
        # the shipped row's after-test and after-check, rows-prov's SR15 entries 5 and 9
        sr15 = lane_row("SR15")
        equality = {"read": "command", "command": "look", "result": "success", "field": "head",
                    "equals": {"output": "scanned for the push.commit"}}
        self.assertEqual((sr15["after_test"], sr15["after_check"]), ([equality], [equality]))

    def test_SR16_OP8_a_build_still_running_fails_the_attempt_and_the_next_resume_attempts_it_again(self):
        m = self.machine()
        sunrise(m)
        env_values(m)
        provlib.plan(m, "vercel", {"command": "GET v13/deployments", "nth": 1, "do": "fail", "status": 200,
                                   "stdout": {"readyState": "BUILDING"}})
        looked, went = started(m)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("a check failed", went.text)
        # the join's punch list (b), the reviewer's P4: the failed check's line does not say live
        status = "".join(read_file(p) for p in went.doc["forms"])
        sr16 = [line for line in status.split("\n") if line.startswith("[SR16]")]
        self.assertEqual(len(sr16), 1, status)
        self.assertNotIn("live", sr16[0])
        again = resume(m)
        self.assertEqual(again.ending, "complete", again.text)
        self.assertEqual(m.statuses(looked.doc["run"]).get("SR16"), "passed")


if __name__ == "__main__":
    import unittest
    unittest.main()
