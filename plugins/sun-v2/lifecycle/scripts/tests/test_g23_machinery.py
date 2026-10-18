"""Part G23: the mechanisms the three lanes asked for (brief-32, section 2).

Every test's name carries the item's id (G23_n) and the frame's rule it rests on. The rows, the lanes and the provider
declarations here are fixtures under the tests, written with `rowlib`; none is a lane's row.
"""
import copy
import json
import os
import subprocess

import harness
import rowlib
import test_g19_machinery as g19
import test_g20_machinery as g20
import test_g21_machinery as g21

L = rowlib.lit
GIT = "/usr/bin/git"


def git(repo, *a):
    env = {"HOME": repo, "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "LANG": "C"}
    return subprocess.run([GIT, "-C", repo, "-c", "user.email=f@x.invalid", "-c", "user.name=f", "-c", "commit.gpgsign=false"]
                          + list(a), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, check=True).stdout.decode().strip()


def one_commit(m):
    repo = m.path("dev", "demo")
    os.makedirs(repo)
    git(repo, "init", "-q", "--initial-branch", "main")
    m.put("dev/demo/a.txt", "a\n")
    git(repo, "add", "--all")
    git(repo, "commit", "-q", "-m", "one")
    return repo, git(repo, "rev-parse", "HEAD")


# ---- G23-1. A passed check binds its output's fields; a head check observes the commit it read (ORD-1, OP-8) ----------
class CheckBinds(harness.Case):
    def test_G23_1_ORD1_OP8_a_passed_check_binds_its_output_fields_and_the_commit_of_the_head_it_read(self):
        m = self.machine()
        repo, sha = one_commit(m)
        where = rowlib.path(rowlib.DEV, rowlib.NAME)
        k = rowlib.check("K1", place=where, output="scanned",
                         thing={"role": "every commit to be pushed", "tracked": ["exists"], "subject_git": "head",
                                "passes": [{"read": "ref", "repo": where, "ref": "main", "exists": True}]})
        k["output"] = {"name": "scanned", "fields": {"commit": {"observed": "commit"}, "branch": L("main")}}
        needs = [{"output": "scanned", "level": "passed", "treatment": "then not applicable"}]
        y = rowlib.says("Y1", words={"text": [{"output": "scanned.branch"}, L(" "), {"output": "scanned.commit"}]}, needs=needs)
        rowlib.install(m, rowlib.lane("sunrise", [k, y]))
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        self.assertIn("main " + sha, m.calls("fakehost", "noop")[-1]["argv"])


def state_of(m, run):
    """The run's state, as the engine derives it from the manifest and the journal (ORD-1)."""
    from sun_core import state as statemod

    class Journal(object):
        records = m.journal(run)
    return statemod.State(g20.manifest_of(m, run), Journal())


def held_text(m, run, value):
    from sun_core import protected
    return protected.read(m.world().fs, m.facts.run_dir(run), value.reference).decode("utf-8")


# ---- G23-2. An output's held fields bind each held field the output names (ORD-1, SEC-4; SR09's account) ------------
class HeldFields(harness.Case):
    def test_G23_2_ORD1_SEC4_each_held_field_an_output_names_binds_that_field_of_the_answer_not_the_creates_id(self):
        m = self.machine()
        providers = rowlib.providers()
        providers["fakehost"]["commands"]["create"]["fields"].append(rowlib._field("account", "id", "held", required=(), **rowlib.IDF))
        m.plan_fake("fakehost", {"command": "create", "extra": {"account": "acct1fixture"}})
        made = rowlib.create("C1")
        made["output"]["fields"]["account"] = {"held": "account"}
        rowlib.install(m, rowlib.lane("sunrise", [made]), providers=providers)
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        run = looked.doc["run"]
        bound = state_of(m, run).outputs["remote"]
        made_id = m.fake("fakehost", "state.json")["things"]["demo"]["id"]
        self.assertEqual(held_text(m, run, bound["id"]), made_id)
        self.assertEqual(held_text(m, run, bound["account"]), "acct1fixture")
        self.assertNowhere("acct1fixture", went)


# ---- G23-3. The identity reads come before a family's read; a row's capability is settled before it (RUN-5, OP-8) -----
def team_providers():
    """g19's keys providers, with a list read that takes the team: `envs-of --team <team>`."""
    out = g19.keys_provs()
    out["fakehost"]["commands"]["envs-of"] = rowlib._command(
        "fakehost", rowlib._t("noop", "--team", rowlib.P("team")),
        [dict(rowlib._field("custom", "name", "held", alphabet="a-z-", max_length=64), place=["envs", "*", "slug"], many=True)])
    return out


class FamilyOrder(harness.Case):
    def test_G23_3_RUN5_SEC4_C_a_familys_look_read_carrying_the_account_is_made_after_the_identity_reads(self):
        m = self.machine()
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0, "stdout": {"envs": [{"slug": "one-env"}]}})
        k = g19.checking("K1", [{"read": "path", "path": rowlib.DEV, "is": "dir"}],
                         commands=[rowlib.use("envs", "fakehost.envs-of", team={"account": "fakehost"})])
        k["thing"]["family"] = {"read": "command", "command": "envs", "field": "custom"}
        rowlib.install(m, rowlib.lane("sunrise", [k]), providers=team_providers())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        listed = [c["argv"] for c in m.calls("fakehost", "noop")]
        self.assertEqual(listed, [["noop", "--team", "fixture-account"]])
        whoami = [i for i, c in enumerate(m.calls("fakehost")) if c["argv"][:1] == ["whoami"]]
        noop = [i for i, c in enumerate(m.calls("fakehost")) if c["argv"][:1] == ["noop"]]
        self.assertEqual(len(whoami), 1, "one identity read, not two")
        self.assertLess(whoami[0], noop[0], "the family's read was made before the identity read")

    def test_G23_3_OP8_a_family_rows_capability_is_settled_before_its_read_and_the_row_is_not_applicable(self):
        m = self.machine()
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0, "stdout": {"envs": [{"slug": "one-env"}]}})
        h = rowlib.refusing("H1", name={"each": "member"})
        h["commands"].append(rowlib.use("envs", "fakehost.envs"))
        h["thing"]["family"] = {"read": "command", "command": "envs", "field": "custom"}
        h["thing"]["capability"] = "routines"
        rowlib.install(m, rowlib.lane("sunrise", [h, rowlib.check("K1")]), providers=g19.keys_provs())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(m.calls("fakehost", "noop"), [], "the family was read on a harness that lacks its capability")
        manifest = g20.manifest_of(m, looked.doc["run"])
        self.assertEqual([(n["row"], n["reason"]) for n in manifest["not_applicable"]], [("H1", "not available on this harness")])
        self.assertEqual([o["id"] for o in manifest["operations"]], ["K1"])


# ---- G23-4. An identity read takes a parameter from his settings for that provider (RUN-5, SEC-4's ground C) ---------
class IdentityParam(harness.Case):
    def test_G23_4_RUN5_SEC4_C_an_identity_read_is_made_with_each_name_his_settings_hold_until_one_proves_equal(self):
        m = self.machine()
        m.settings["accounts"]["fakehost"] = ["other-team", "fixture-account"]
        m.write_settings()
        providers = rowlib.providers()
        host = providers["fakehost"]
        host["commands"]["team"] = rowlib._command(
            "fakehost", rowlib._t("whoami", "--team", rowlib.P("team")),
            [rowlib._field("account", "name", "equal", equals={"settings": "fakehost"}, **rowlib.NAMEF)], refusals=("not-found",))
        host["identity"] = {"command": "team", "field": "account", "params": {"team": {"settings": "fakehost"}}}
        m.plan_fake("fakehost", {"command": "whoami", "do": "fail", "exit": 3, "stdout": {"kind": "not-found"}, "nth": 1})
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1", words={"account": "fakehost"})]), providers=providers)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual([c["argv"] for c in m.calls("fakehost", "whoami")],
                         [["whoami", "--team", "other-team"], ["whoami", "--team", "fixture-account"]])
        manifest = g20.manifest_of(m, looked.doc["run"])
        self.assertEqual(manifest["accounts"], {"fakehost": "fixture-account"})

    def test_G23_4_RUN5_no_name_of_his_settings_proving_equal_ends_the_look_as_the_wrong_account(self):
        m = self.machine()
        providers = rowlib.providers()
        host = providers["fakehost"]
        host["commands"]["team"] = rowlib._command(
            "fakehost", rowlib._t("whoami", "--team", rowlib.P("team")),
            [rowlib._field("account", "name", "equal", equals={"settings": "fakehost"}, **rowlib.NAMEF)], refusals=("not-found",))
        host["identity"] = {"command": "team", "field": "account", "params": {"team": {"settings": "fakehost"}}}
        m.plan_fake("fakehost", {"command": "whoami", "do": "fail", "exit": 3, "stdout": {"kind": "not-found"}})
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1", words={"account": "fakehost"})]), providers=providers)
        looked = m.look()
        self.assertNotEqual(looked.ending, "preview", looked.text)
        self.assertIn("the read was made as the wrong account: fakehost reports an account your settings do not name", looked.text)


# ---- G23-5. A held field the row's own command read, back to its issuer; a restore's saved copy, its issuer's (SEC-2) --
def pause_providers(other=False):
    """fakehost, with two requests of the frame's own: POST /v1/pause and /v1/unpause, the thing's id in the body. With
    `other`, the pause is a second provider's, `other`, at another host."""
    out = rowlib.providers()
    for word in ("pause", "unpause"):
        out["fakehost"]["commands"]["api-" + word] = {
            "tool": "fakehost", "via": "request", "method": "POST", "template": rowlib._t("v1", word), "time_limit": 20,
            "effects": 1, "exits": {"200": "success"}, "fields": [], "definite": {"success": ["success"], "refusals": []},
            "body": {"id": {"param": "id"}}}
    if other:
        decl = copy.deepcopy(out["fakehost"])
        decl.update(provider="other", host="other.invalid", identity="none")
        decl.pop("token", None)
        decl["credential_env"] = []
        decl["commands"] = {"api-pause": decl["commands"]["api-pause"]}
        out["other"] = decl
    return out


class PauseHost(object):
    """The fake host of the frame's own requests: a pause or an unpause sets the state of the fake's thing of that id."""

    def __init__(self, machine):
        self.m, self.records = machine, []

    def request(self, host, method, path, headers, timeout, body=None):
        sent = json.loads(body.decode("utf-8")) if body else {}
        self.records.append({"host": host, "path": path, "id": sent.get("id")})
        state = self.m.fake("fakehost", "state.json")
        found = [k for k, t in state["things"].items() if t["id"] == sent.get("id")]
        if host != "api.fakehost.invalid" or not found:
            return 404, b"{}"
        state["things"][found[0]]["state"] = "paused" if path.endswith("/pause") else "active"
        self.m.set_fake("fakehost", things=state["things"])
        return 200, b"{}"


def pause_row(rid, phase, before, after, command, id_mark, **more):
    look = rowlib.use("look", "fakehost.get", name=rowlib.NAME)
    return rowlib.row(
        "change", rid, phase,
        thing={"role": "the thing at the fake host", "identity": "provider id", "before_word": before, "after_word": after},
        planning_test=[{"read": "command", "command": "look", "result": "success"}],
        before_test=[{"id": "was", "read": "command", "command": "look", "result": "success", "field": "state", "equals": before}],
        after_test=[{"read": "command", "command": "look", "result": "success", "field": "state", "equals": after}],
        construction={"id": "C6", "command": "act", "risks": ["RK3"], "risk_line": "another changes it between the read and the request"},
        commands=[look, rowlib.use("act", command, id=id_mark)],
        after_check=[{"read": "command", "command": "look", "result": "success", "field": "state", "equals": after}],
        content_classes={"reads": ["safe", "held"], "stores": ["held field"], "shows": ["safe"], "validators": [],
                         "resting_places": ["the protected folder"]},
        output={"name": "out-" + rid, "fields": {}}, **more)


THING = {"demo": {"id": "t1abc", "kind": "repo", "state": "active", "name": "demo"}}


class HeldRead(harness.Case):
    def test_G23_5_SEC2_SEC4_a_held_field_the_rows_own_command_read_goes_back_to_its_issuer_and_stays_held(self):
        m = self.machine()
        m.set_fake("fakehost", things=copy.deepcopy(THING))
        row = pause_row("T21", "one", "active", "paused", "fakehost.api-pause", {"read": {"command": "look", "field": "id"}},
                        way_back={"none": "the row declares none"})
        rowlib.install(m, rowlib.lane("sunrise", [row], **copy.deepcopy(g21.RK18_FORMS)), providers=pause_providers())
        m.transport = PauseHost(m)
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual([(r["host"], r["path"], r["id"]) for r in m.transport.records], [("api.fakehost.invalid", "/v1/pause", "t1abc")])
        self.assertNotIn("t1abc", json.dumps(m.journal(looked.doc["run"])))
        self.assertNowhere("t1abc", went)

    def test_G23_5_SEC2_a_held_field_read_by_one_providers_command_in_anothers_request_fails_the_build(self):
        m = self.machine()
        m.set_fake("fakehost", things=copy.deepcopy(THING))
        row = pause_row("T21", "one", "active", "paused", "other.api-pause", {"read": {"command": "look", "field": "id"}},
                        way_back={"none": "the row declares none"})
        rowlib.install(m, rowlib.lane("sunrise", [row], **copy.deepcopy(g21.RK18_FORMS)), providers=pause_providers(other=True))
        m.transport = PauseHost(m)
        looked = m.look()
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row T21, entry commands: a held value goes back only to the provider that issued it (SEC-2)", looked.lines)
        self.assertEqual(m.transport.records, [])

    def test_G23_5_SEC2_EV5_a_restores_saved_copy_of_a_held_field_goes_back_to_the_forward_rows_issuer(self):
        m = self.machine()
        m.set_fake("fakehost", things=copy.deepcopy(THING))
        reverse = pause_row("V11", g19.BACK, "paused", "active", "fakehost.api-unpause", {"saved": 0},
                            way_back={"none": "the row declares none"})
        forward = pause_row("T21", g19.P[1], "active", "paused", "fakehost.api-pause", {"read": {"command": "look", "field": "id"}},
                            way_back={"reverse": reverse},
                            reverse_inputs=[{"read": "command", "command": "look", "field": "id", "type": "held field",
                                             "label": "the thing's id"}])
        rowlib.install(m, rowlib.lane("sunset", [forward], phases=g19.P, **copy.deepcopy(g21.RK18_FORMS)),
                       rowlib.lane("restore", [], phases=(g19.BACK,), **copy.deepcopy(g21.RK18_FORMS)), providers=pause_providers())
        m.transport = PauseHost(m)
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(m.go(looked, kind="sunset").ending, "complete")
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", (went.text, m.transport.records))
        self.assertEqual([r["path"] for r in m.transport.records], ["/v1/pause", "/v1/unpause"])
        self.assertEqual(m.transport.records[1]["id"], "t1abc")
        self.assertEqual(m.fake("fakehost", "state.json")["things"]["demo"]["state"], "active")
        self.assertNowhere("t1abc", went)


# ---- G23-6. A keep's two-read inventory filtered by a parallel list field holding the row's environment (KEEP-1) -----
def target_provs():
    """g19's keys providers, the key list's read given a parallel list of each key's targets (a list of names per key)."""
    out = g19.keys_provs()
    out["fakehost"]["commands"]["keys"]["fields"].append(
        dict(rowlib._field("targets", "name", "held", required=(), alphabet="a-z", max_length=16), place=["envs", "*", "target"],
             many=True, lists=True))
    return out


def targeted(*pairs):
    return {"envs": [{"key": k, "target": list(t)} for k, t in pairs]}


class InventoryTarget(harness.Case):
    def test_G23_6_KEEP1_A149_a_two_read_inventory_takes_only_the_keys_whose_targets_hold_the_rows_environment(self):
        doc = targeted(("FIXTURE_URL", ["production"]), ("FIXTURE_KEY", ["production", "preview"]), ("PREVIEW_ONLY", ["preview"]))
        cases = (("production", "complete"), ("preview", "stopped"))
        for env, ending in cases:
            with self.subTest(environment=env):
                m = self.machine("t" + env, "t" + env)
                m.set_fake("fakehost", identity="source-one")
                m.plan_fake("fakehost", *[{"command": "noop", "do": "fail", "exit": 0, "stdout": doc, "nth": n} for n in (1, 2)])
                row = g19.keep_row(scope={"inventory_from": {"command": "keys", "field": "keys", "copy_keys": "=",
                                                             "target": {"field": "targets", "holds": L(env)}}})
                row["construction"]["hosting_env"] = True
                rowlib.install(m, rowlib.lane("sunrise", [row]), providers=target_provs())
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                went = m.go(looked)
                # production: its two keys are the copy's two; preview: its keys (FIXTURE_KEY, PREVIEW_ONLY) are not the
                # copy's (FIXTURE_URL, FIXTURE_KEY), and the keep fails
                self.assertEqual(went.ending, ending, went.text)
                if ending == "complete":
                    from sun_core import protected
                    completion = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion"][0]
                    listed = json.loads(protected.read(m.world().fs, m.facts.run_dir(looked.doc["run"]), completion["keep"]["inventory"]))
                    self.assertEqual(sorted(listed), ["FIXTURE_KEY", "FIXTURE_URL"])


# ---- G23-7. A pairs read takes the members whose value is returned; the rest set apart by a type list (KEEP-1, A148) --
def typed_pairs_providers():
    out = g20.secret_pairs_providers()
    out["fakehost"]["commands"]["values"]["fields"].append(
        dict(rowlib._field("types", "name", "held", required=(), alphabet="a-z", max_length=16), place=["envs", "*", "type"], many=True))
    return out


class PairsApart(harness.Case):
    def kept(self, label, envs):
        import test_g22_machinery as g22
        m = self.machine(label, label)
        m.set_fake("fakehost", identity="source-one")
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0, "stdout": {"envs": envs}})
        row = g22.hosting_keep()
        row["keep_scope"]["inventory_from"]["apart"] = {"field": "types", "equals": "sensitive"}
        rowlib.install(m, rowlib.lane("sunrise", [row]), providers=typed_pairs_providers())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        return m, looked, m.go(looked)

    def test_G23_7_KEEP1_A148_a_member_whose_value_is_not_returned_is_set_apart_by_its_type_and_the_keep_is_whole(self):
        from sun_core import protected
        value = "pw" + harness.canary("pairs")
        m, looked, went = self.kept("a", [{"key": "FIXTURE_A", "value": value, "type": "plain"}, {"key": "FIXTURE_S", "type": "sensitive"}])
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(open(m.path("dev", "demo-env.txt"), encoding="utf-8").read(), 'FIXTURE_A="%s"\n' % value)
        completion = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion"][0]
        apart = protected.read(m.world().fs, m.facts.run_dir(looked.doc["run"]), completion["keep"]["apart"])
        self.assertEqual(json.loads(apart), ["FIXTURE_S"])
        self.assertNowhere(value, went)

    def test_G23_7_KEEP1_a_member_whose_value_is_not_returned_and_whose_type_is_not_set_apart_fails_the_keep(self):
        m, looked, went = self.kept("b", [{"key": "FIXTURE_A", "value": "pw" + harness.canary("p2"), "type": "plain"},
                                          {"key": "FIXTURE_B", "type": "plain"}])
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the keep is not whole", went.text)
        self.assertFalse(os.path.exists(m.path("dev", "demo-env.txt")))


# ---- G23-8. A keep's `apart` keys named by key, as not saved, in the preview and the tombstone (SEC-6 as A148) -------


class ApartShown(harness.Case):
    def test_G23_8_SEC6_A148_the_keys_set_apart_are_named_by_key_in_the_preview_and_in_the_last_record(self):
        m = self.machine()
        m.set_fake("fakehost", identity="source-one")
        doc = {"envs": [{"key": "FIXTURE_URL", "type": "plain"}, {"key": "FIXTURE_KEY", "type": "sensitive"}]}
        m.plan_fake("fakehost", *[{"command": "noop", "do": "fail", "exit": 0, "stdout": doc, "nth": n} for n in (1, 2, 3)])
        row = g19.keep_row(scope={"inventory_from": {"command": "keys", "field": "keys", "copy_keys": "=",
                                                     "apart": {"field": "types", "equals": "sensitive"}}})
        row["construction"]["hosting_env"] = True
        row["form_lines"] = {"preview": "save the env values", "status": "the env values saved"}
        lane = rowlib.lane("sunrise", [row, rowlib.last_record("L1")], phases=("one", "the last record"),
                           form_changes=dict(rowlib.FORM_CHANGES))
        rowlib.install(m, lane, providers=g19.keys_provs())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        line = "not saved, its value is never returned: FIXTURE_KEY (save the env values)"
        preview = open(looked.doc["forms"][0], encoding="utf-8").read()
        self.assertIn(line, preview)
        self.assertNotIn("FIXTURE_URL", preview)
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        record = open(m.path("dev", "demo-record-%s.txt" % looked.doc["run"]), encoding="utf-8").read()
        self.assertIn("not saved, its value is never returned: FIXTURE_KEY (the env values saved)", record)


# ---- G23-9. A keep's `ends-with` checked when it is built; each line of one prefix paired with a section (KEEP-1) -----
class DumpChecks(harness.Case):
    def kept(self, label, plan, checks):
        m = self.machine(label, label)
        m.put("dev/demo.env", "DATABASE_URL=postgres://u:%s@db.fixture.invalid/app\n" % ("pw" + harness.canary(label)))
        m.plan_fake("fakedump", dict({"command": "dump", "do": "sections"}, **plan))
        row = rowlib.keep("P1")
        row["keep_scope"]["content_checks"] += checks
        rowlib.install(m, rowlib.lane("sunrise", [row]))
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        return m, m.go(looked)

    def test_G23_9_KEEP1_KEEP3_a_cut_copy_fails_the_keep_when_it_is_built_and_is_never_published(self):
        ends = [{"check": "ends-with", "text": "-- END OF DUMP\n"}]
        for cut, ending in ((False, "complete"), (True, "stopped")):
            with self.subTest(cut=cut):
                m, went = self.kept("e%s" % cut, {"cut_end": cut}, ends)
                self.assertEqual(went.ending, ending, went.text)
                self.assertEqual(os.path.exists(m.path("dev", "demo-dump.txt")), not cut)
                if cut:
                    self.assertIn("the keep is not whole", went.text)

    def test_G23_9_KEEP1_each_line_of_one_prefix_has_its_section_of_another_or_the_keep_fails(self):
        pair = [{"check": "has-section", "prefix": "TABLE ", "section": "SECTION "}]
        for drop, ending in ((None, "complete"), ("beta", "stopped")):
            with self.subTest(drop=drop):
                m, went = self.kept("s%s" % drop, {"drop": drop} if drop else {}, pair)
                self.assertEqual(went.ending, ending, went.text)
                self.assertEqual(os.path.exists(m.path("dev", "demo-dump.txt")), drop is None)


# ---- G23-10. A planning test's own stop line, in the row's own words (RUN-7; SR17's terms) ---------------------------
class OwnStopLine(harness.Case):
    def test_G23_10_RUN7_a_failing_planning_test_that_carries_its_own_stop_line_ends_the_look_with_that_line(self):
        said = "Accept the fake host's terms once: run fakehost accept-terms, then summon sunrise again."
        for own, want in ((True, said), (False, "the place is taken by a thing this run did not make: row C1")):
            with self.subTest(own=own):
                m = self.machine("o%s" % own, "o%s" % own)
                m.set_fake("fakehost", things=copy.deepcopy(THING))
                made = rowlib.create("C1")
                if own:
                    made["planning_test"][0]["stop_line"] = said
                rowlib.install(m, rowlib.lane("sunrise", [made]))
                looked = m.look()
                self.assertEqual(looked.ending, "refused", looked.text)
                self.assertIn(want, looked.lines)
                if own:
                    self.assertNotIn("the place is taken by a thing this run did not make: row C1", looked.lines)


# ---- G23-11. A change of an absent folder published as C1 publishes; `already so` where it stands (OP-2 as A154) -------
def folder_row(rid, rel, gitkeep):
    place = rowlib.path(rowlib.DEV, rowlib.NAME, *rel.split("/"))
    return rowlib.row("change", rid, "one",
                      thing={"role": "the kit folder " + rel, "identity": "path", "place": place, "tracked": ["exists", "identity"]},
                      planning_test=[{"read": "path", "path": g19.PROJECT, "is": "dir"}],
                      before_test=[{"id": "free", "read": "path", "path": place, "is": "absent"}],
                      after_test=[{"read": "path", "path": place, "is": "dir"}],
                      construction={"id": "C3", "risks": ["RK2"], "edit": dict({"kind": "folder"}, **({"gitkeep": True} if gitkeep else {})),
                                    "make_parents": {"within": g19.PROJECT}, "mode": 0o755},
                      after_check=[{"read": "path", "path": place, "is": "dir"}], way_back={"none": "the row declares none: no sunrise undo"},
                      output={"name": "kit " + rel, "fields": {"path": place}})


class FolderChange(harness.Case):
    def test_G23_11_OP2_A154_a_change_of_an_absent_folder_is_published_as_C1_publishes_with_or_without_a_gitkeep(self):
        m = self.machine()
        os.makedirs(m.path("dev", "demo"))
        rows = [folder_row("SR03-docs", "docs", True), folder_row("SR03-scope", "docs/scope/notes", False)]
        rowlib.install(m, rowlib.lane("sunrise", rows))
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(sorted(os.listdir(m.path("dev", "demo", "docs"))), [".gitkeep", "scope"])
        self.assertEqual(open(m.path("dev", "demo", "docs", ".gitkeep"), "rb").read(), b"")
        self.assertEqual(os.listdir(m.path("dev", "demo", "docs", "scope", "notes")), [])
        self.assertEqual(os.stat(m.path("dev", "demo", "docs")).st_mode & 0o777, 0o755)
        self.assertEqual(m.statuses(looked.doc["run"]), {"SR03-docs": "done", "SR03-scope": "done"})
        starts = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "start"]
        self.assertEqual([s["thing"]["exists"] for s in starts], [False, False])

    def test_G23_11_OP2_OP5_a_folder_that_stands_is_already_so_and_a_kill_after_the_publish_is_landed(self):
        m = self.machine("a", "a")
        os.makedirs(m.path("dev", "demo", "docs"))
        rowlib.install(m, rowlib.lane("sunrise", [folder_row("SR03-docs", "docs", True)]))
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        manifest = g20.manifest_of(m, looked.doc["run"])      # found so at the look: `already so`, no operation (RUN-7)
        self.assertEqual([a["row"] for a in manifest["already_so"]], ["SR03-docs"])
        self.assertEqual(manifest["operations"], [])
        self.assertEqual(os.listdir(m.path("dev", "demo", "docs")), [])
        m = self.machine("k", "k")
        os.makedirs(m.path("dev", "demo"))
        rowlib.install(m, rowlib.lane("sunrise", [folder_row("SR03-docs", "docs", True)]))
        looked = m.look()
        killed = m.go(looked, kill=lambda e: e["stage"] == "post" and e["op"] == "rename" and str(e["subject"]).endswith("docs"))
        self.assertTrue(killed.killed, killed.text)
        self.assertTrue(os.path.isdir(m.path("dev", "demo", "docs")))
        self.assertEqual(m.resume().ending, "complete")
        self.assertEqual(m.statuses(looked.doc["run"]), {"SR03-docs": "done"})


# ---- G23-12. A found file's fields `suffix` and `lane` (RUN-6, SEC-1; rise SR06-coldread, SR06-review) ----------------
class FoundFields(harness.Case):
    def test_G23_12_RUN6_SEC1_a_found_files_suffix_and_lane_from_its_stem(self):
        from sun_core import plan as planmod
        m = self.machine()
        m.put("dev/staged/2026-10-01-gpt-review-demo.md", "a\n")
        m.put("dev/staged/2026-10-02-gemini-review-demo-2.md", "b\n")
        m.put("dev/staged/notes-12.md", "c\n")
        found = planmod.found_items(m.world().fs, {"read": "files", "folder": m.path("dev", "staged"), "glob": "*.md",
                                                   "suffix": True, "lane": True})
        self.assertEqual([(i["name"], i["suffix"], i.get("lane")) for i in found],
                         [("2026-10-01-gpt-review-demo.md", "", "gpt"), ("2026-10-02-gemini-review-demo-2.md", "-2", "gemini"),
                          ("notes-12.md", "-12", None)])
        plain = planmod.found_items(m.world().fs, {"read": "files", "folder": m.path("dev", "staged"), "glob": "*.md"})
        self.assertNotIn("suffix", plain[0])

    def test_G23_12_SEC1_a_family_members_suffix_is_the_tools_own_match_and_its_lane_safe_by_its_validator(self):
        m = self.machine()
        m.put("dev/staged/2026-10-02-gemini-review-demo-2.md", "b\n")
        target = rowlib.path(rowlib.DEV, {"text": [L("review-"), {"each": "lane"}, {"each": "suffix"}, L(".md")]})
        k = g19.checking("K1", [{"read": "path", "path": target, "is": "absent"}], output={"name": "review {each.n}", "fields": {}})
        k["thing"]["family"] = {"read": "files", "folder": rowlib.path(rowlib.DEV, "staged"), "glob": "*.md", "suffix": True,
                                "lane": True, "validators": {"lane": "one line of plain words"}}
        rowlib.install(m, rowlib.lane("sunrise", [k]), providers=g19.provs())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = g20.manifest_of(m, looked.doc["run"])
        self.assertEqual(manifest["operations"][0]["thing"]["passes"][0]["path"], L(m.path("dev", "review-gemini-2.md")))


# ---- G23-13. The kit edit `merge`, and the lift where the file is absent (RUN-6, OP-2; rise SR03-agents) ---------------
BODY = "## Commands\n- npm run dev\n## Gates\n- Feature branches.\n## Where to look\n- docs/\n"


class KitMerge(harness.Case):
    def merged(self, label, agents, claude="@AGENTS.md\nan old rule\n"):
        m = self.machine(label, label)
        os.makedirs(m.path("dev", "demo"))
        if agents is not None:
            m.put("dev/demo/AGENTS.md", agents)
        m.put("dev/demo/CLAUDE.md", claude)
        gates = L("- Feature branches.")
        lacks = lambda p: [{"read": "text", "path": p, "text": gates, "present": False, "or_absent": True}]   # noqa: E731
        holds = lambda p: [{"read": "text", "path": p, "text": gates, "count": 1}]                         # noqa: E731
        edit = {"kind": "kit", "text": L(BODY), "where_it_stands": "merge", "pointer": L("See CLAUDE.md"),
                "lift_from": rowlib.path(rowlib.DEV, rowlib.NAME, "CLAUDE.md"), "lift_heading": L("## Lifted from CLAUDE.md"),
                "stub": L("@AGENTS.md")}
        row = g19.kit_row("SR03-agents", "AGENTS.md", edit, lacks, holds, risks=["RK2", "RK18"],
                          risk_line="a merge or lift v1 would have shown you first is written without showing it")
        rowlib.install(m, rowlib.lane("sunrise", [row], **copy.deepcopy(g21.RK18_FORMS)), providers=g19.provs())
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        return open(m.path("dev", "demo", "AGENTS.md"), encoding="utf-8").read()

    def test_G23_13_RUN6_merge_adds_each_missing_line_under_its_heading_and_keeps_what_stands(self):
        got = self.merged("a", "# a framework block\n## Commands\n## Gates\nkeep me\n")
        self.assertEqual(got, "# a framework block\n## Commands\n- npm run dev\n## Gates\nkeep me\n- Feature branches.\n"
                              "## Where to look\n- docs/\n## Lifted from CLAUDE.md\nan old rule\n")

    def test_G23_13_RUN6_merge_replaces_the_one_pointer_line_with_the_body(self):
        got = self.merged("p", "# AGENTS\nSee CLAUDE.md\n")
        self.assertEqual(got, "# AGENTS\n" + BODY + "## Lifted from CLAUDE.md\nan old rule\n")

    def test_G23_13_OP2_A147_an_absent_file_gets_the_body_and_the_lift(self):
        self.assertEqual(self.merged("n", None), BODY + "## Lifted from CLAUDE.md\nan old rule\n")


# ---- G23-14. A `line` read of two lines joining a literal and a held line, read by content (SEC-4; set T19, V08) -------
class JoinedLine(harness.Case):
    def test_G23_14_SEC4_EV6_a_two_line_read_of_a_heading_and_a_held_line_tells_the_moved_line_from_the_unmoved(self):
        for under, ending in (("## Archived", "complete"), ("## Live", "stopped")):
            with self.subTest(under=under):
                m = self.machine("j" + under[3:], "j" + under[3:])
                other = "## Archived\n" if under == "## Live" else "## Live\n"
                m.put("dev/notes.md", "%s\nalias d=\"cd /x/demo\"\n%s" % (under, other))
                file = rowlib.path(rowlib.DEV, "notes.md")
                k = g19.checking("K1", [{"read": "line", "path": file, "line": {"text": [L("## Archived\n"), {"each": "line"}]}, "present": True}],
                                 output={"name": "archived {each.n}", "fields": {}})
                k["thing"]["family"] = {"read": "lines", "path": file, "holding": L("/x/demo")}
                rowlib.install(m, rowlib.lane("sunrise", [k]), providers=g19.provs())
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                self.assertNotIn("/x/demo", json.dumps(g20.manifest_of(m, looked.doc["run"])))
                went = m.go(looked)
                self.assertEqual(went.ending, ending, went.text)
                self.assertNowhere("/x/demo", went)


# ---- G23-15. A found read's `rel`: a member's path relative to its `within` folder (RUN-6; set V06) --------------------
class WithinRel(harness.Case):
    def test_G23_15_RUN6_a_member_inside_the_within_folder_carries_its_path_relative_to_it(self):
        m = self.machine()
        m.put("dev/vf/sub/inside.md", "see OLD/\n")
        vf, vfa = rowlib.path(rowlib.DEV, "vf"), rowlib.path(rowlib.DEV, "vf-archived")
        mv = rowlib.move("T13", source=vf, target=vfa, output="vault folder archived")
        for test in ("planning_test", "before_test", "after_test", "after_check"):
            for c in mv[test]:
                if c.get("path") in (vf, vfa) and c.get("is") == "file":
                    c["is"] = "dir"
        mv["way_back"] = {"none": "the row declares none"}
        mv["reverse_inputs"] = "none"
        rel_path = {"path": [{"output": "vault folder archived.path"}, {"each": "rel"}]}
        f = g19.checking("F1", [{"read": "path", "path": rel_path, "is": "file"}], output={"name": "F1 {each.n}", "fields": {}},
                         needs=[{"output": "vault folder archived", "level": "made", "treatment": "then not applicable"}])
        f["thing"]["family"] = {"read": "files", "folder": vf, "glob": "*.md", "holding": L("OLD/"), "tree": True,
                                "validators": {"name": "one line of plain words"}, "within": {"folder": vf, "output": "vault folder archived.path"}}
        rowlib.install(m, rowlib.lane("sunrise", [mv, f]), providers=g19.provs())
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        manifest = g20.manifest_of(m, looked.doc["run"])
        self.assertEqual(g20.op_of(manifest, "F1-1")["thing"]["passes"][0]["path"],
                         {"path": [{"output": "vault folder archived.path"}, L(os.path.join("sub", "inside.md"))]})
        self.assertEqual(m.statuses(looked.doc["run"])["F1-1"], "passed")


# ---- G23-16. A text read over a command's protected text holds where the command answers a declared refusal ------------
class OrRefused(harness.Case):
    def test_G23_16_RUN7_SEC4_a_text_read_or_refused_holds_on_a_declared_refusal_as_or_absent_does_for_a_file(self):
        cases = (("no table, or_refused", 3, True, "complete"), ("no table, no word", 3, False, "stopped"),
                 ("an answer no refusal declares", 4, True, "stopped"))
        for label, code, word, ending in cases:
            with self.subTest(case=label):
                m = self.machine("r%d%s" % (code, word), "r%d%s" % (code, word))
                providers = g19.provs()
                providers["fakehost"]["commands"]["listing"]["definite"]["refusals"] = ["not-found"]
                m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": code, "stdout": {"kind": "not-found"}})
                read = {"read": "text", "command": "listing", "text": L("/x/demo"), "present": False}
                if word:
                    read["or_refused"] = True
                k = g19.checking("K1", [read], commands=[rowlib.use("listing", "fakehost.listing")])
                rowlib.install(m, rowlib.lane("sunrise", [k]), providers=providers)
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                went = m.go(looked)
                self.assertEqual(went.ending, ending, went.text)
                if ending == "stopped":
                    self.assertIn("unreadable", went.text)


# ---- G23-17. A family reverse's id carries its member's `n`: two members, two reverses (EV-5, ORD-1; set item 12) ------
class FamilyReverseIds(harness.Case):
    def test_G23_17_EV5_a_restore_of_two_family_members_has_two_reverses_and_puts_both_back(self):
        m = self.machine()
        for name in ("a.plist", "b.plist"):
            m.put("dev/agents/" + name, "<plist>demo</plist>\n")
        os.makedirs(m.path("dev", "archive"))
        family = {"read": "files", "folder": rowlib.path(rowlib.DEV, "agents"), "glob": "*.plist", "holding": rowlib.NAME,
                  "validators": {"name": "a launch agent's label"}}
        a = rowlib.move("A1", g19.P[1], source={"each": "path"}, target=rowlib.path(rowlib.DEV, "archive", {"each": "name"}),
                        output="archived {each.n}")
        a["thing"]["family"] = family
        a["way_back"]["reverse"]["phase"] = g19.BACK
        a["way_back"]["reverse"]["output"] = {"name": "back {each.n}", "fields": {}}
        rowlib.install(m, rowlib.lane("sunset", [a], phases=g19.P), rowlib.lane("restore", [], phases=(g19.BACK,)), providers=g19.provs())
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = g20.manifest_of(m, looked.doc["run"])
        self.assertEqual([o["way_back"]["reverse"]["id"] for o in manifest["operations"]], ["A1-reverse-1", "A1-reverse-2"])
        self.assertEqual(m.go(looked, kind="sunset").ending, "complete")
        self.assertEqual(sorted(os.listdir(m.path("dev", "archive"))), ["a.plist", "b.plist"])
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(sorted(o["id"] for o in g20.manifest_of(m, looked.doc["run"])["operations"]), ["A1-reverse-1", "A1-reverse-2"])
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(sorted(os.listdir(m.path("dev", "agents"))), ["a.plist", "b.plist"])


# ---- G23-18. A family member whose named field is held records no way back: "an input is missing" (EV-4; set T11) -----
class HeldNoWayBack(harness.Case):
    def test_G23_18_EV4_a_member_whose_named_field_is_held_has_no_way_back_and_the_preview_says_so(self):
        m = self.machine()
        m.put("shortcuts.txt", 'alias dm="cd /x/demo"\nalias Bad_X="cd /x/demo/b"\nalias o="cd /x/other"\n')
        file = {"location": "shortcut_file"}
        gone = rowlib.swap_add("S1")
        gone["before_test"] = [{"id": "has", "read": "line", "path": file, "line": {"each": "line"}, "count": 1}]
        gone["after_test"] = [{"read": "line", "path": file, "line": {"each": "line"}, "present": False}]
        gone["after_check"] = list(gone["after_test"])
        gone["construction"] = {"id": "C3", "risks": ["RK2"], "edit": {"kind": "remove-line", "line": {"each": "line"}}}
        gone["reverse_inputs"] = [{"read": "value", "value": {"each": "line"}, "type": "line", "label": "the line"}]
        gone["span"] = {"placement": "at the end", "ordered": False}
        gone["thing"]["family"] = {"read": "lines", "path": file, "holding": L("cd /x/demo"), "name_after": "alias ",
                                   "validators": {"name": "a shortcut's name"}, "no_way_back_if_held": "name"}
        gone["output"] = {"name": "shortcut removed {each.n}", "fields": {}}
        rowlib.install(m, rowlib.lane("sunrise", [gone]), providers=g19.provs())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        preview = open(looked.doc["forms"][0], encoding="utf-8").read()
        self.assertIn("[S1-2] change: the fake row S1; no way back can be recorded: an input is missing", preview)
        self.assertNotIn("[S1-1] change: the fake row S1; no way back", preview)
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        ways = dict((r["op"], r["way_back"]) for r in m.journal(looked.doc["run"]) if r["kind"] == "completion")
        self.assertTrue(ways["S1-1"]["offered"])
        self.assertEqual(ways["S1-2"], {"offered": False, "reason": "an input is missing"})
        self.assertNowhere("Bad_X", went)


# ---- G23-19. The validator `a shortcut name`, as rows-set section 8 item 1 writes it (SEC-1; set T11) -----------------
class ShortcutNameValidator(harness.Case):
    def test_G23_19_SEC1_a_shortcut_name_is_the_pattern_rows_set_writes(self):
        from sun_core import values
        check = values.VALIDATORS.get("a shortcut name")
        self.assertIsNotNone(check, "the tool has no validator `a shortcut name`")
        for name in ("gs", "Bad_X", "_x", "a.b-c", "x" * 64):
            self.assertIsNotNone(check.fullmatch(name), name)
        for name in ("", "-x", ".x", "x" * 65, "a b", "a=b", "a\n", "a$b", "a/b"):
            self.assertIsNone(check.fullmatch(name), name)
        # rise's narrower validator stays as it was
        self.assertEqual(values.VALIDATORS["a shortcut's name"].pattern, "[a-z0-9]{2,5}")


# ---- G23-20. A build check: the project's own build made on every attempt, its writes its ignored output folder alone ----
def build_providers():
    out = rowlib.providers()
    out["fakescaffold"]["commands"]["build"] = rowlib._command("fakescaffold", rowlib._t("build", "--work", rowlib.P("work")), [],
                                                               effects=1, exits={"0": "success", "1": "other"})
    return out


class BuildCheck(harness.Case):
    def repo(self, m, ignore="out/\n"):
        repo = m.path("dev", "demo")
        os.makedirs(repo)
        git(repo, "init", "-q", "--initial-branch", "main")
        m.put("dev/demo/.gitignore", ignore)
        m.put("dev/demo/package.json", "{}\n")
        git(repo, "add", "--all")
        git(repo, "commit", "-q", "-m", "one")
        return repo

    def checked(self, label, plan=None, stale=True, ignore="out/\n"):
        m = self.machine(label, label)
        self.repo(m, ignore)
        if stale:
            m.put("dev/demo/out/main.js", "left by an earlier build\n")
        if plan:
            m.plan_fake("fakescaffold", dict({"command": "build"}, **plan))
        where = rowlib.path(rowlib.DEV, rowlib.NAME)
        k = g19.checking("K1", [{"read": "path", "path": rowlib.path(rowlib.DEV, rowlib.NAME, "out", "main.js"), "is": "file"}],
                         commands=[rowlib.use("build", "fakescaffold.build", work=where)], output={"name": "local baseline", "fields": {}})
        k["thing"].update({"place": where, "build": {"command": "build", "repo": where, "output": "out"}})
        rowlib.install(m, rowlib.lane("sunrise", [k]), providers=build_providers())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        return m, looked, m.go(looked)

    def test_G23_20_OP8_A154_a_build_check_over_a_stale_output_whose_scaffold_cannot_build_fails(self):
        m, looked, went = self.checked("f", plan={"do": "fail", "exit": 1})
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: a check failed", went.lines)
        self.assertEqual([r["answer"] for r in m.journal(looked.doc["run"]) if r["kind"] == "attempt"], ["failed"])

    def test_G23_20_OP8_A154_a_build_check_over_an_output_that_builds_runs_the_build_and_passes(self):
        m, looked, went = self.checked("p")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(len(m.calls("fakescaffold", "build")), 1)
        self.assertEqual(open(m.path("dev", "demo", "out", "main.js")).read(), "built 1\n")

    def test_G23_20_OP8_A154_an_output_an_earlier_build_left_never_passes(self):
        # a build that ends 0 and writes nothing: what an earlier build left was taken away before it, and the check fails
        m, looked, went = self.checked("s", plan={"do": "fail", "exit": 0})
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertFalse(os.path.exists(m.path("dev", "demo", "out", "main.js")))

    def test_G23_20_OP8_A154_a_build_that_writes_outside_its_output_folder_stops_on_the_clean_read(self):
        m, looked, went = self.checked("w", plan={"stray": True})
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the clean read after the build is not clean", went.text)
        self.assertEqual([r["answer"] for r in m.journal(looked.doc["run"]) if r["kind"] == "attempt"], ["failed"])

    def test_G23_20_OP8_A154_an_output_folder_the_project_does_not_ignore_is_neither_cleared_nor_built(self):
        m, looked, went = self.checked("i", ignore="other/\n")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(open(m.path("dev", "demo", "out", "main.js")).read(), "left by an earlier build\n")
        self.assertEqual(m.calls("fakescaffold", "build"), [])

    def test_G23_20_OP8_A154_a_build_on_a_row_that_is_no_check_or_outside_the_project_fails_the_build(self):
        where = rowlib.path(rowlib.DEV, rowlib.NAME)
        for label, kind, output in (("c", "change", "out"), ("o", "check", "../elsewhere")):
            with self.subTest(case=label):
                m = self.machine("b" + label, "b" + label)
                k = g19.checking("K1", [{"read": "path", "path": where, "is": "dir"}],
                                 commands=[rowlib.use("build", "fakescaffold.build", work=where)])
                k["thing"].update({"place": where, "build": {"command": "build", "repo": where, "output": output}})
                row = k
                if kind == "change":
                    row = rowlib.refusing("H1")
                    row["commands"].append(rowlib.use("build", "fakescaffold.build", work=where))
                    row["thing"]["build"] = {"command": "build", "repo": where, "output": output}
                rowlib.install(m, rowlib.lane("sunrise", [row]), providers=build_providers())
                looked = m.look()
                self.assertEqual(looked.ending, "refused", looked.text)
                self.assertIn("a build stands only on a check, its output folder inside the project (OP-8, A154)", looked.text)


# ---- G23-21. `skills.json` maps the restore summons to the skill that makes it: sunset-v2 (rows-set C2) ----------------
class SkillsMap(harness.Case):
    def test_G23_21_RUN1_every_kind_of_run_is_summoned_by_a_skill_the_plugin_lists_restore_by_sunset_v2(self):
        lifecycle = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(lifecycle, "skills.json"), encoding="utf-8") as fh:
            doc = json.load(fh)
        listed = dict((s["name"], s["folder"]) for s in doc["skills"])
        self.assertEqual(doc["summonses"], {"sunrise": "sunrise-v2", "sunset": "sunset-v2", "restore": "sunset-v2"})
        for kind, skill in doc["summonses"].items():
            self.assertIn(skill, listed, kind)
            self.assertTrue(os.path.isdir(os.path.join(os.path.dirname(lifecycle), listed[skill])), skill)


# ---- G23-23. The kill sweep's point in the middle of a git child: the frame's cell for a child that outlives the kill ----
class SweepChildRace(harness.Case):
    """A kill as the go's cas child runs leaves that child running (it starts in a session of its own): it can land between
    the rerun's two probe reads, which then read neither state. OP-5 gives `foreign`, OP-6 stops, and the next probe reads
    the world again. The race is made to fall there: the fake cas is slow, and the first resume waits at its first read's end
    until the cas has landed."""

    def test_G23_23_OP5_OP6_a_rerun_racing_a_child_the_kill_left_running_stops_foreign_and_the_next_resume_reaches_the_reference(self):
        import killlib
        import test_kill_sweep

        def prepare(machine):
            test_kill_sweep.prepare(machine)
            machine.plan_fake("fakegit", {"command": "cas", "do": "late", "seconds": 1.0})

        sweep = killlib.Sweep(self, self.tmp, prepare)
        # the go's cas: the `mid child fakegit` right after its operation's start record (point 190 on the reference rows)
        point = [p for p in sweep.points if sweep.describe(p) == "mid child fakegit" and sweep.describe(p - 2) == "post journal start"][0]
        seen = {"reads": 0}

        def hook(machine, event):
            if event["op"] == "child" and str(event["subject"]) == "fakegit" and event["stage"] == "post":
                seen["reads"] += 1
                if seen["reads"] == 1:
                    import time
                    deadline = time.time() + 60
                    while ((machine.fake("fakegit", "state.json") or {}).get("refs") or {}).get("main") != "c1" and time.time() < deadline:
                        time.sleep(0.05)
            return False
        word, problem = sweep.kill_at(point, hook=hook)
        self.assertIsNone(problem, problem)
        self.assertTrue(word.startswith("stopped foreign, then "), word)


# ---- G23-24. test_log_op's failing reads: a time limit fit for a test under load, the test's rule unchanged -------------
class ReadLimitUnderLoad(harness.Case):
    def test_G23_24_RUN7_a_read_of_the_failing_providers_that_answers_slowly_under_load_is_no_timeout(self):
        import test_log_op
        m = self.machine()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.refusing("H1")]), providers=test_log_op.identity_failing_providers())
        m.set_fake("fakehost", things={"demo": {"id": "x1", "kind": "db", "state": "active", "name": "demo"}})
        # a machine under load: each read answers, a second and a half late
        m.plan_fake("fakehost", {"command": "get", "do": "late", "seconds": 1.5}, {"command": "whoami", "do": "late", "seconds": 1.5})
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertNotIn("ran out of time", looked.text)


# ---- Fix round (the reviewer's G23 check) ---------------------------------------------------------------------------
class BuildBoundary(harness.Case):
    """G23-F1 (OP-8, A154): the output folder or folders the row names must be ignored by the project's own `.gitignore`, and
    a write to any path outside them, ignored or not, stops the attempt; the clean read still follows."""

    def built(self, label, output, ignore, plan=None, exclude=None):
        m = self.machine(label, label)
        BuildCheck.repo(self, m, ignore)
        if exclude is not None:
            m.put("dev/demo/.git/info/exclude", exclude)
        if plan:
            m.plan_fake("fakescaffold", dict({"command": "build"}, **plan))
        where = rowlib.path(rowlib.DEV, rowlib.NAME)
        k = g19.checking("K1", [{"read": "path", "path": rowlib.path(rowlib.DEV, rowlib.NAME, "out", "main.js"), "is": "file"}],
                         commands=[rowlib.use("build", "fakescaffold.build", work=where)], output={"name": "local baseline", "fields": {}})
        k["thing"].update({"place": where, "build": {"command": "build", "repo": where, "output": output}})
        rowlib.install(m, rowlib.lane("sunrise", [k]), providers=build_providers())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        return m, looked, m.go(looked)

    def test_G23_F1_OP8_A154_a_write_to_an_ignored_path_outside_the_output_folder_stops_the_attempt(self):
        m, looked, went = self.built("f1s", "out", "out/\nstray.txt\n", plan={"stray": True})
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the build wrote outside its output folder", went.text)
        self.assertEqual([r["answer"] for r in m.journal(looked.doc["run"]) if r["kind"] == "attempt"], ["failed"])

    def test_G23_F1_OP8_A154_an_output_ignored_only_by_the_repositorys_exclude_file_is_neither_cleared_nor_built(self):
        m, looked, went = self.built("f1x", "out", "unrelated/\n", exclude="out/\n")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the build's output folder is not one the project's own .gitignore ignores", open(went.doc["forms"][0]).read())
        self.assertEqual(m.calls("fakescaffold", "build"), [])

    def test_G23_F1_OP8_A154_a_row_may_name_several_output_folders_each_ignored_and_the_build_writes_them_alone(self):
        m, looked, went = self.built("f1c", ["out", ".cache"], "out/\n.cache/\n", plan={"cache": True})
        self.assertEqual(went.ending, "complete", went.text)
        self.assertTrue(os.path.isfile(m.path("dev", "demo", ".cache", "build.bin")))
        m, looked, went = self.built("f1n", "out", "out/\n.cache/\n", plan={"cache": True})
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the build wrote outside its output folder", went.text)


class QuotedTables(harness.Case):
    """G23-F2 (KEEP-1, KEEP-3): `has-section` compares each table's whole identity, a quoted name with its spaces among it,
    and fails a name it cannot read whole."""

    def kept(self, label, tables, drop=None):
        m = self.machine(label, label)
        m.put("dev/demo.env", "DATABASE_URL=postgres://u:%s@db.fixture.invalid/app\n" % ("pw" + harness.canary(label)))
        m.set_fake("fakedump", database={"identity": "source-one", "tables": tables})
        m.plan_fake("fakedump", dict({"command": "dump", "do": "sections"}, **({"drop": drop} if drop else {})))
        row = rowlib.keep("P1")
        row["keep_scope"]["content_checks"] += [{"check": "has-section", "prefix": "TABLE ", "section": "SECTION "}]
        rowlib.install(m, rowlib.lane("sunrise", [row]))
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        return m, m.go(looked)

    def test_G23_F2_KEEP1_two_quoted_names_that_share_their_first_word_are_two_tables(self):
        tables = ['public."first table"', 'public."first other"']
        for drop, ending in ((tables[1], "stopped"), (None, "complete")):
            with self.subTest(drop=drop):
                m, went = self.kept("q%s" % bool(drop), tables, drop)
                self.assertEqual(went.ending, ending, went.text)
                self.assertEqual(os.path.exists(m.path("dev", "demo-dump.txt")), drop is None)

    def test_G23_F2_KEEP1_a_name_the_check_cannot_read_whole_fails_the_keep(self):
        m, went = self.kept("u", ['public."unclosed'])
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the keep is not whole", went.text)
        self.assertFalse(os.path.exists(m.path("dev", "demo-dump.txt")))

    def test_G23_F2_KEEP3_the_barriers_recheck_compares_the_whole_names_too(self):
        from sun_core import effects
        data = b'TABLE public."first table" (\nSECTION public."first table" FROM stdin;\nTABLE public."first other" (\n'
        check = {"check": "has-section", "prefix": "TABLE ", "section": "SECTION "}
        self.assertFalse(effects.text_checks_hold(data, check))
        self.assertTrue(effects.text_checks_hold(data + b'SECTION public."first other" FROM stdin;\n', check))


class ApartBothReads(harness.Case):
    """G23-F3 (KEEP-1, RISK-1, RK18): the keys listed apart are compared across the two inventory reads, as the returned keys
    are; either changing fails the keep."""

    def test_G23_F3_KEEP1_RK18_a_key_set_apart_replaced_between_the_two_reads_fails_the_keep(self):
        def doc(key):
            return {"envs": [{"key": "FIXTURE_URL", "type": "plain", "target": ["production"]},
                             {"key": "FIXTURE_KEY", "type": "plain", "target": ["production"]},
                             {"key": key, "type": "sensitive", "target": ["production"]}]}
        for later, ending in (("FIRST", "complete"), ("SECOND", "stopped")):
            with self.subTest(after=later):
                m = self.machine("a" + later, "a" + later)
                m.set_fake("fakehost", identity="source-one")
                # the look's read, then the keep's two: the apart key the same, or replaced, at the second
                m.plan_fake("fakehost", *[{"command": "noop", "do": "fail", "exit": 0, "stdout": doc(key), "nth": n}
                                          for n, key in ((1, "FIRST"), (2, "FIRST"), (3, later))])
                row = g19.keep_row(scope={"inventory_from": {"command": "keys", "field": "keys", "copy_keys": "=",
                                                             "target": {"field": "targets", "holds": L("production")},
                                                             "apart": {"field": "types", "equals": "sensitive"}}})
                row["construction"]["hosting_env"] = True
                rowlib.install(m, rowlib.lane("sunrise", [row]), providers=target_provs())
                looked, went = m.started()
                self.assertEqual(went.ending, ending, went.text)
                if ending == "stopped":
                    self.assertIn("the keep is not whole", went.text)
                    self.assertFalse(os.path.exists(m.path("dev", "demo-env.txt")))
