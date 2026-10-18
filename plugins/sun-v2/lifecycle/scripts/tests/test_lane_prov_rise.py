"""Slice 3, the providers: the sunrise rows (rows-prov section 3.2), run over the four fakes with slice 2's outputs from
stand-in rows (provlib), as slice 2's `sunrise/lane.json` will hold them at the join.

Every test's name carries the row's id and the rule's id.
"""
import json
import os
import stat
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
from sun_core import journal as journalmod, plan, protected, state as statemod  # noqa: E402

ROWS = ("SR08", "SR09", "SR15", "SR16", "SR17", "SR17c", "SR19")


def sunrise(m, link=True):
    """The test lane: slice 2's stand-ins, then slice 3's sunrise part as shipped (part one's test-lane substitution of SR15's
    and SR16's commit is gone: G23-1 binds `scanned for the push.commit` at the stand-in check's pass)."""
    repo, commit = provlib.project_repo(m)
    provlib.install(m, provlib.lane("sunrise", provlib.rise_standins(repo, commit, link), ("sunrise",)))
    return repo, commit


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


class Admission(harness.Case):
    def test_ROW1_ROW3_the_sunrise_part_with_stand_ins_is_admitted_with_its_checklist_answered(self):
        lane = provlib.lane("sunrise", provlib.rise_standins("/x/demo", "0" * 40), ("sunrise",))
        expanded = plan.expand(lane, provlib.providers())
        self.assertEqual(plan.admit_all(lane, expanded, provlib.providers()), [])
        self.assertEqual([r["id"] for r in provlib.shipped("sunrise", "provider-rows.json")["rows"]], list(ROWS))
        # the checklist fails naming the item where one names a row the part does not hold
        broken = provlib.shipped("sunrise", "provider-rows.json")
        broken["checklist"].append({"item": "a planted item", "answered_by": {"row": "SR99"}})
        lane = provlib.lane("sunrise", provlib.rise_standins("/x/demo", "0" * 40), ("sunrise",), part=broken)
        found = plan.admit_all(lane, plan.expand(lane, provlib.providers()), provlib.providers())
        self.assertIn("a planted item: names a row that does not exist", [f["finding"] for f in found])


class EndToEnd(harness.Case):
    def test_SR08_SR09_SR15_SR16_SR17_SR17c_SR19_RUN8_OP2_a_sunrise_over_the_fakes_looked_previewed_approved_and_complete(self):
        m = provlib.wire(self.machine())
        repo, commit = sunrise(m)
        secret = env_values(m)
        looked = m.look(inputs=provlib.rise_inputs(m))
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        with open(looked.doc["forms"][0]) as fh:
            preview = fh.read()
        self.FORMS = {"preview": preview}
        for line in ("GitHub: create the private repository demo as fixture-account (no push)",
                     "Hosting: create demo as fixture-team, connected to fixture-account/demo",
                     "GitHub: push main once (the scanned commit)", "Database: Supabase through the Marketplace, demo-db",
                     "Env: pull the development values to .env.local (owner-only, ignored)",
                     "acts at github as: fixture-account", "acts at vercel as: fixture-team",
                     "carried under v1's own risk for this step (RK18): a resource of that name made by another"):
            self.assertIn(line, preview)
        # RUN-5: the look made only reads at the fakes
        self.assertEqual([c["command"] for c in provlib.calls(m, "gh")], ["whoami", "repo-read"])
        self.assertEqual(sorted(set(c["command"] for c in provlib.calls(m, "vercel") if "command" in c)), ["cli-team", "db-installed", "db-list"])
        self.assertEqual([r["request"] for r in provlib.requests(m)], ["GET", "GET"])
        went = m.go(looked)
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
        # SR15: the remote's main is the scanned commit, one push
        self.assertEqual(provlib.remote_head(m), commit)
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
        self.assertIn("Verify: live at https://demo.vercel.app/, answering 200 for the pushed commit; the deployment reads READY", status)
        self.assertEqual(len(provlib.calls(m, "web", "status")), 1)
        with open(os.path.join(os.environ.get("SUN_V2_PROV_FORMS", m.root), "rise-forms.txt"), "w") as fh:
            fh.write(preview + "\n=====\n" + status)

    def test_seam_SR08_SR09_SR15_SR16_SR17_SR17c_SR19_each_output_slice_2_takes_is_made_with_its_fields(self):
        m = provlib.wire(self.machine())
        sunrise(m)
        env_values(m)
        looked, went = m.started(inputs=provlib.rise_inputs(m))
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
        self.assertEqual(bound["env file"], {"path": os.path.join(m.path("dev", "demo"), ".env.local")})


class Seams(harness.Case):
    def test_seam_SR15_ORD1_G23_1_the_shipped_SR15_pushes_the_commit_slice_2s_scanned_for_the_push_check_bound_at_its_pass(self):
        """Part one's machinery request 4, as SR15 and SR16 used it, met by G23-1: slice 2's `scanned for the push` is a check
        whose `commit` binds at its pass, so the shipped SR15, with no test-lane substitution, pushes that commit (part one's
        test, which pinned a plain stop before any push, now passes on the mechanism)."""
        m = provlib.wire(self.machine())
        repo, commit = sunrise(m)
        env_values(m)
        part = provlib.shipped("sunrise", "provider-rows.json")
        sr15 = [r for r in part["rows"] if r["id"] == "SR15"][0]
        self.assertIn({"output": "scanned for the push.commit"}, [c["params"].get("commit") for c in sr15["commands"]])
        looked, went = m.started(inputs=provlib.rise_inputs(m))
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(provlib.remote_head(m), commit)
        self.assertEqual(outputs(m, looked.doc["run"])["scanned for the push"], {"commit": commit})

    def test_seam_SR09_SR10s_G23_2_slice_2s_link_file_gets_orgId_from_hosting_project_account(self):
        """Part one's machinery request 5, met by G23-2: the stand-in of slice 2's SR10 builds `.vercel/project.json` from
        SR09's held `id` and `account` as `projectId` and `orgId`; `orgId` is the project's accountId at the host."""
        m = provlib.wire(self.machine())
        repo, _ = sunrise(m)
        env_values(m)
        looked, went = m.started(inputs=provlib.rise_inputs(m))
        self.assertEqual(went.ending, "complete", went.text)
        project = provlib.state(m, "vercel")["things"]["demo"]
        with open(os.path.join(repo, ".vercel", "project.json")) as fh:
            linked = json.load(fh)
        self.assertEqual(linked, {"projectId": project["id"], "orgId": project["account"]})


class Refusals(harness.Case):
    def test_SR08_RUN7_a_repository_of_that_name_already_at_github_ends_the_look_with_the_place_taken(self):
        m = provlib.wire(self.machine())
        sunrise(m)
        provlib.put_state(m, "gh", account=provlib.ACCOUNT, things={"demo": {"id": "R_x", "kind": "repo", "state": "active", "name": "demo"}})
        looked = m.look(inputs=provlib.rise_inputs(m))
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the place is taken by a thing this run did not make: row SR08", looked.text)
        self.assertEqual(provlib.calls(m, "gh", "create"), [])

    def test_SR09_RUN7_A4_a_project_of_that_name_at_the_host_ends_the_look_with_the_place_taken(self):
        m = provlib.wire(self.machine())
        sunrise(m)
        provlib.put_state(m, "vercel", things={"demo": {"id": "prj_x", "kind": "project", "state": "active", "name": "demo",
                                                        "account": "team_x"}})
        looked = m.look(inputs=provlib.rise_inputs(m))
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the place is taken by a thing this run did not make: row SR09", looked.text)

    def test_SR17_RUN7_G23_10_the_marketplace_terms_not_accepted_end_the_look_in_the_rows_own_words(self):
        """Part one's machinery request 13, met by G23-10: the terms' planning test carries its own stop line (rows-prov
        section 4), and the look ends with it, not with the generic "place is taken" line."""
        m = provlib.wire(self.machine())
        sunrise(m)
        provlib.put_state(m, "vercel", installed=False)
        looked = m.look(inputs=provlib.rise_inputs(m))
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("Accept the Marketplace's terms for Supabase once: run `vercel integration accept-terms supabase`, "
                      "then summon sunrise again.", looked.text)
        self.assertNotIn("the place is taken by a thing this run did not make: row SR17", looked.text)
        self.assertEqual(provlib.calls(m, "vercel", "db-add"), [])

    def test_SR17_SR17c_SR19_ORD3_flags_db_false_leaves_the_three_not_applicable(self):
        m = provlib.wire(self.machine())
        sunrise(m)
        looked = m.look(inputs=provlib.rise_inputs(m, db=False))
        self.assertEqual(looked.ending, "preview", looked.text)
        with open(os.path.join(m.facts.run_dir(looked.doc["run"]), "manifest-1.json")) as fh:
            manifest = json.load(fh)
        self.assertEqual(sorted(n["row"] for n in manifest["not_applicable"]), ["SR17", "SR17c", "SR19"])
        self.assertEqual(sorted(o["id"] for o in manifest["operations"] if o["id"] in ROWS), ["SR08", "SR09", "SR15", "SR16"])

    def test_SR15_OP3_C4_a_commit_on_the_remotes_main_before_the_push_stops_it_and_no_second_push(self):
        m = provlib.wire(self.machine())
        repo, commit = sunrise(m)
        env_values(m)
        looked = m.look(inputs=provlib.rise_inputs(m))
        self.assertEqual(looked.ending, "preview", looked.text)
        # killed just after SR08's completion record: the remote stands, empty
        went = m.go(looked, kill=lambda e: e["op"] == "append" and e["stage"] == "post" and m.statuses(looked.doc["run"]).get("SR08") == "done")
        self.assertTrue(went.killed, went.text)
        other = m.path("other")
        os.makedirs(other)
        provlib.git(other, "init", "-q")
        m.put("other/x.txt", "another's\n")
        provlib.git(other, "add", "-A")
        provlib.git(other, "commit", "-q", "-m", "another's")
        provlib.git(other, "push", "-q", os.path.join(m.home, ".fakes", "gh", "remotes", provlib.ACCOUNT, "demo.git"), "main")
        theirs = provlib.remote_head(m)
        resumed = m.resume()
        self.assertEqual(resumed.ending, "stopped", resumed.text)
        self.assertEqual(provlib.remote_head(m), theirs)
        self.assertNotEqual(theirs, commit)

    def test_SR15_OP5_OP6_G24_1_a_main_another_pushed_before_SR15s_probe_is_foreign_and_no_push_is_made(self):
        """G24-1 (part two's Question 2): SR15's after-test and after-check are rows-prov's equality, the remote's `head` equal to
        `scanned for the push.commit`. Another's commit on the remote's main before SR15's own probe (here the run is killed
        just after SR08 made the repository, and SR15 is not yet started, so the resume probes it fresh): after-test false,
        before-test false, `foreign`, which stops at SR15; before, on the head's presence, it read `already so` and the run
        stopped later, at SR16's need. The fresh push is the end-to-end run and `Seams.test_seam_SR15_ORD1_G23_1_...`."""
        m = provlib.wire(self.machine())
        repo, commit = sunrise(m)
        env_values(m)
        looked = m.look(inputs=provlib.rise_inputs(m))
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        went = m.go(looked, kill=lambda e: e["op"] == "append" and e["stage"] == "post" and m.statuses(run).get("SR08") == "done")
        self.assertTrue(went.killed, went.text)
        self.assertNotIn("SR15", m.statuses(run))
        other = m.path("other")
        os.makedirs(other)
        provlib.git(other, "init", "-q")
        m.put("other/x.txt", "another's\n")
        provlib.git(other, "add", "-A")
        provlib.git(other, "commit", "-q", "-m", "another's")
        provlib.git(other, "push", "-q", os.path.join(m.home, ".fakes", "gh", "remotes", provlib.ACCOUNT, "demo.git"), "main")
        theirs = provlib.remote_head(m)
        resumed = m.resume()
        self.assertEqual(resumed.ending, "stopped", resumed.text)
        self.assertIn("foreign", resumed.text)
        self.assertIn("SR15", resumed.text)
        self.assertNotIn("SR15", m.statuses(run), "another's main was given a status")
        self.assertEqual([r["kind"] for r in m.journal(run) if r.get("op") == "SR15" and r["kind"] in ("start", "status")], [],
                         "SR15 was started or given a status")
        self.assertEqual(provlib.remote_head(m), theirs)
        self.assertNotEqual(theirs, commit)
        # the shipped row's after-test and after-check, rows-prov's SR15 entries 5 and 9
        sr15 = [r for r in provlib.shipped("sunrise", "provider-rows.json")["rows"] if r["id"] == "SR15"][0]
        equality = {"read": "command", "command": "look", "result": "success", "field": "head",
                    "equals": {"output": "scanned for the push.commit"}}
        self.assertEqual((sr15["after_test"], sr15["after_check"]), ([equality], [equality]))

    def test_SR16_OP8_a_build_still_running_fails_the_attempt_and_the_next_resume_attempts_it_again(self):
        m = provlib.wire(self.machine())
        sunrise(m)
        env_values(m)
        provlib.plan(m, "vercel", {"command": "GET v13/deployments", "nth": 1, "do": "fail", "status": 200,
                                   "stdout": {"readyState": "BUILDING"}})
        looked, went = m.started(inputs=provlib.rise_inputs(m))
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("a check failed", went.text)
        again = m.resume()
        self.assertEqual(again.ending, "complete", again.text)
        self.assertEqual(m.statuses(looked.doc["run"]).get("SR16"), "passed")


if __name__ == "__main__":
    import unittest
    unittest.main()
