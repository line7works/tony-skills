"""Part G22: the reviewer's four findings on G19 to G21, her boundary tests, and three small gaps (brief-31, section 2).

Every test's name carries the item's id (G22_n) and the frame's rule it rests on. The rows, the lanes and the provider
declarations here are fixtures under the tests, written with `rowlib`; none is a lane's row.
"""
import copy
import json
import os

import harness
import rowlib
import test_g19_machinery as g19
import test_g20_machinery as g20
import test_g21_machinery as g21


# ---- G22-1. A held request parameter and its echo stay held (SEC-1, SEC-4, SEC-6; her F1) ----------------------------
class EchoHost(g20.BodyHost):
    """The fake host echoes the held id it was sent back in a field `echo`."""

    def request(self, host, method, path, headers, timeout, body=None):
        g20.BodyHost.request(self, host, method, path, headers, timeout, body)
        sent = json.loads(body.decode("utf-8")) if body else {}
        return 200, json.dumps({"echo": (sent.get("link") or {}).get("id", "")}).encode("utf-8")


class HeldEcho(harness.Case):
    def test_G22_1_SEC4_SEC1_a_held_id_sent_to_its_issuer_and_echoed_back_stays_held_in_journal_form_and_output(self):
        m = self.machine()
        providers = g20.body_providers()
        providers["fakehost"]["commands"]["api-post"]["fields"] = [
            rowlib._field("echo", "id", "equal", equals={"param": "id"}, **rowlib.IDF)]
        k = rowlib.check("K1", needs=[{"output": "remote", "level": "made", "treatment": "then not applicable"}])
        k["thing"]["passes"] = [{"read": "command", "command": "api", "result": "success"}]
        k["commands"] = [rowlib.use("api", "fakehost.api-post", name=rowlib.NAME, id={"output": "remote.id"})]
        k["form_lines"] = {"preview": "inspect", "status": "echo <echo>"}
        m.transport = EchoHost()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.create("C1"), k]), providers=providers)
        looked, went = m.started()
        held = m.fake("fakehost", "state.json")["things"]["demo"]["id"]
        sent = [r for r in m.transport.records if r["method"] == "POST"]
        self.assertEqual(len(sent), 1, m.transport.records)
        self.assertIn(held, sent[0]["body"].decode("utf-8"), "the held id did not go back to its issuer")
        self.assertNotIn(held, json.dumps(m.journal(looked.doc["run"])), "the echoed held id is in a journal record")
        self.assertNotIn(held, g20.form_text(went), "the echoed held id is in a form")
        self.assertNowhere(held, went)


# ---- G22-2. Issuer provenance for every held request value, family members among them (SEC-2, SEC-4; her F2) --------
def issuer_providers(where):
    """fakehost issues a held list; `other` is a second provider whose request carries a value in its body or its query."""
    out = g19.keys_provs()
    other = g20.body_providers()["fakehost"]
    other.update(provider="other", host="other.invalid", identity="none")
    other.pop("token", None)
    post = other["commands"]["api-post"]
    if where == "body":
        post["query"] = [{"name": "team", "value": {"literal": "fixture-team"}}]
    else:
        post["body"] = {"private": {"literal": True}}
    out["other"] = other
    return out


class FamilyIssuer(harness.Case):
    def look(self, label, where, use):
        m = self.machine(label, label)
        commands = [rowlib.use("envs", "fakehost.envs"), rowlib.use("api", use, name={"each": "member"}, id=rowlib.lit("safe"))]
        k = g19.checking("K1", [{"read": "command", "command": "api", "result": "success"}], commands=commands)
        k["thing"]["family"] = {"read": "command", "command": "envs", "field": "custom"}
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0, "stdout": {"envs": [{"slug": "private-label"}]}})
        providers = issuer_providers(where)
        providers["fakehost"]["commands"]["api-post"] = providers["other"]["commands"]["api-post"]
        rowlib.install(m, rowlib.lane("sunrise", [k]), providers=providers)
        m.transport = g20.BodyHost()
        return m, m.look()

    def test_G22_2_SEC2_a_family_member_from_one_providers_held_list_in_another_providers_request_fails_the_build(self):
        for where in ("body", "query"):
            with self.subTest(where=where):
                m, looked = self.look("f" + where, where, "other.api-post")
                self.assertEqual(looked.ending, "refused", looked.text)
                self.assertIn("row K1-custom-1, entry commands: a held value goes back only to the provider that issued it "
                              "(SEC-2)", looked.lines)
                self.assertEqual([r for r in m.transport.records if r["host"] == "other.invalid"], [])
                self.assertNowhere("private-label", looked)

    def test_G22_2_SEC2_the_same_member_going_back_to_its_issuer_builds(self):
        for where in ("body", "query"):
            with self.subTest(where=where):
                m, looked = self.look("s" + where, where, "fakehost.api-post")
                self.assertEqual(looked.ending, "preview", looked.text)
                self.assertNowhere("private-label", looked)


# ---- G22-3. RK19's floor for a hosting environment's saved values alone (SEC-4 A150, A153, RK19; her F3) ------------
def hosting_keep(marked=True):
    """The keep that saves a hosting environment's values (G19-29's pairs keep), marked as such where `marked`."""
    row = g19.keep_row(scope={"inventory_from": {"pairs": "pairs"}})
    row["construction"]["builder"] = "values"
    row["commands"] = [rowlib.use("values", "fakehost.values"), rowlib.use("ident", "fakehost.identify")]
    if marked:
        row["construction"]["hosting_env"] = True
    return row


class HostingFloor(harness.Case):
    def kept(self, label, value, marked):
        m = self.machine(label, label)
        m.set_fake("fakehost", identity="source-one")
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0,
                                 "stdout": {"envs": [{"key": "FIXTURE_A", "value": value},
                                                     {"key": "FIXTURE_B", "value": "pw" + harness.canary("floor")}]}})
        later = rowlib.says("Y2", words=rowlib.lit("told " + value.strip()))
        rowlib.install(m, rowlib.lane("sunrise", [hosting_keep(marked), later]), providers=g20.secret_pairs_providers())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        return m, m.go(looked)

    def test_G22_3_SEC4_RK19_a_short_member_of_a_secret_pair_list_outside_the_hosting_keep_is_registered(self):
        m = self.machine()
        providers = g20.secret_pairs_providers()
        providers["fakehost"]["commands"]["values"]["fields"][0]["place"] = ["codes", "*"]
        k = rowlib.check("K1")
        k["thing"]["passes"] = [{"read": "command", "command": "codes", "result": "success"}]
        k["commands"] = [rowlib.use("codes", "fakehost.values")]
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0, "stdout": {"codes": [{"key": "CODE", "value": "tiny"}]}})
        rowlib.install(m, rowlib.lane("sunrise", [k, rowlib.says("Y2", words=rowlib.lit("told tiny"))]), providers=providers)
        looked, went = m.started()
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("stopped: a safe ground disproved", went.lines)
        self.assertEqual([c for c in m.calls() if "told tiny" in c["argv"]], [], "the short secret went out in an argument")

    def test_G22_3_SEC4_RK19_the_same_short_member_in_a_keep_not_marked_as_the_hosting_keep_is_registered(self):
        m, went = self.kept("n1", "tiny", marked=False)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual([c for c in m.calls() if "told tiny" in c["argv"]], [])

    def test_G22_3_SEC4_RK19_the_hosting_keeps_floor_counts_utf8_bytes_with_edge_white_space_left_out(self):
        cases = ((" " + "x" * 7 + " ", "complete"), (" " + "x" * 8 + " ", "stopped"),
                 ("é" * 3, "complete"), ("é" * 4, "stopped"))
        for n, (value, ending) in enumerate(cases):
            with self.subTest(value=value):
                m, went = self.kept("h%d" % n, value, marked=True)
                self.assertEqual(went.ending, ending, went.text)
                told = [c for c in m.calls() if "told " + value.strip() in c["argv"]]
                if ending == "complete":
                    # saved: the keep holds it whole; and no entry: the later line holding it went out as it stands
                    self.assertIn('FIXTURE_A="%s"' % value, open(m.path("dev", "demo-env.txt"), encoding="utf-8").read())
                    self.assertEqual(len(told), 1)
                else:
                    self.assertEqual(told, [])

    def test_G22_3_RK19_KEEP1_the_hosting_environments_mark_on_a_row_that_is_no_keep_built_by_its_builder_fails_the_build(self):
        m = self.machine()
        made = rowlib.create("C1")
        made["construction"]["hosting_env"] = True
        rowlib.install(m, rowlib.lane("sunrise", [made]))
        looked = m.look()
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row C1, entry construction: the hosting environment's mark stands only on a keep built by its builder "
                      "(RK19, KEEP-1)", looked.lines)


# ---- G22-4. Two reads stand for one state only for the hosting keep and a folder copied under RK18 (KEEP-1; her F4) --
def folder_keep(source, risks):
    """Her FOLDER_NO_RK18 row: a folder of this machine copied whole by the tool, with or without RK18."""
    dest = rowlib.path(rowlib.DEV, "copy")
    construction = {"id": "C1", "copy_folder": rowlib.lit(source), "mode": 0o700}
    if risks:
        construction.update(risks=["RK18"], risk_line="a file changed and changed back while it is copied is not seen")
    return rowlib.row("keep", "K1", "one",
                      thing={"role": "folder copy", "identity": "path", "place": dest, "tracked": ["exists", "identity"]},
                      planning_test=[{"read": "path", "path": dest, "is": "absent"}],
                      before_test=[{"id": "free", "read": "path", "path": dest, "is": "absent"}],
                      after_test=[{"read": "path", "path": dest, "is": "dir"}], construction=construction,
                      after_check=[{"read": "path", "path": dest, "is": "dir"}],
                      keep_scope={"scope": "all files", "same_state": "two reads", "content_checks": []},
                      content_classes={"reads": ["protected"], "stores": ["protected"], "shows": ["safe"], "validators": [],
                                       "resting_places": ["the sunset folder"]},
                      output={"name": "copy", "fields": {"path": dest}})


class TwoReads(harness.Case):
    def test_G22_4_KEEP1_RISK1_RISK2_a_folder_copied_whole_with_no_RK18_fails_the_build_naming_the_row(self):
        m = self.machine()
        m.put("source/one.txt", "private content")
        row = folder_keep(m.path("source"), risks=False)
        rowlib.install(m, rowlib.lane("sunrise", [row]))
        looked = m.look()
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row K1, entry construction: a folder copied whole stands only in a row RK18 names (KEEP-1, A151)",
                      looked.lines)
        self.assertFalse(os.path.exists(m.path("dev", "copy")))

    def test_G22_4_KEEP1_A148_A149_a_two_read_inventory_on_a_keep_not_marked_as_the_hosting_keep_fails_the_build(self):
        m = self.machine()
        m.set_fake("fakehost", identity="source-one")
        m.plan_fake("fakehost", *[{"command": "noop", "do": "fail", "exit": 0, "stdout": g19.keys_doc("FIXTURE_URL", "FIXTURE_KEY"),
                                   "nth": n} for n in (1, 2)])
        row = g19.keep_row(scope={"inventory_from": {"command": "keys", "field": "keys", "copy_keys": "="}})
        row["thing"]["role"] = "database inventory copy"
        row["keep_scope"]["scope"] = "database rows"
        rowlib.install(m, rowlib.lane("sunrise", [row]), providers=g19.keys_provs())
        looked = m.look()
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("row P1, entry keep_scope: an inventory read before and after the copy stands only for a hosting "
                      "environment's variables (KEEP-1, A149)", looked.lines)
        self.assertFalse(os.path.exists(m.path("dev", "demo-env.txt")))

    def test_G22_4_KEEP1_the_same_two_reads_on_the_hosting_keep_and_the_folder_under_RK18_build(self):
        m = self.machine("h", "h")
        m.set_fake("fakehost", identity="source-one")
        m.plan_fake("fakehost", *[{"command": "noop", "do": "fail", "exit": 0, "stdout": g19.keys_doc("FIXTURE_URL", "FIXTURE_KEY"),
                                   "nth": n} for n in (1, 2)])
        row = g19.keep_row(scope={"inventory_from": {"command": "keys", "field": "keys", "copy_keys": "="}})
        row["construction"]["hosting_env"] = True
        rowlib.install(m, rowlib.lane("sunrise", [row]), providers=g19.keys_provs())
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        m = self.machine("f", "f")
        m.put("source/one.txt", "private content")
        row = folder_keep(m.path("source"), risks=True)
        rowlib.install(m, rowlib.lane("sunrise", [row], **copy.deepcopy(g21.RK18_FORMS)))
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        self.assertTrue(os.path.isfile(m.path("dev", "copy", "one.txt")))


# ---- G22-5. Her boundary tests (her F5): G19-4's other held output, and G19-17's mark once across a kill ------------
class Boundaries(harness.Case):
    def test_G22_5_G19_4_SEC4_a_held_compare_against_a_different_held_output_is_false(self):
        for equal, ending in ((True, "complete"), (False, "stopped")):
            with self.subTest(equal=equal):
                m = self.machine("c%s" % equal, "c%s" % equal)
                first = rowlib.create("C1", name=rowlib.lit("one"), output="first")
                second = rowlib.create("C2", name=rowlib.lit("two"), output="second",
                                       needs=[{"output": "first", "level": "made", "treatment": "then not applicable"}])
                second["after_check"] = [{"read": "command", "command": "look", "result": "success", "field": "id",
                                          "equals": {"output": ("second" if equal else "first") + ".id"}, "compare_held": True}]
                rowlib.install(m, rowlib.lane("sunrise", [first, second]))
                looked, went = m.started()
                self.assertEqual(went.ending, ending, went.text)
                if not equal:
                    self.assertIn("the after-check does not show the after-state", went.text)

    def test_G22_5_G19_17_RISK1_RK18s_mark_is_recorded_once_across_a_kill_and_a_resume(self):
        def journal_after(kind, op):
            return lambda event: event["stage"] == "post" and event["op"] == "journal" and str(event["subject"]).endswith(kind) \
                and event.get("operation") == op
        for kind in ("start", "step"):
            with self.subTest(killed_after=kind):
                m = self.machine("k" + kind, "k" + kind)
                m.put("source/one.txt", "private content")
                rowlib.install(m, rowlib.lane("sunrise", [folder_keep(m.path("source"), risks=True)], **copy.deepcopy(g21.RK18_FORMS)))
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                went = m.go(looked, kill=journal_after(kind, "K1"))
                self.assertTrue(went.killed)
                self.assertEqual(m.resume().ending, "complete")
                marks = [(r["op"], r["risk"]) for r in m.journal(looked.doc["run"]) if r.get("step") == "risk-mark"]
                self.assertEqual(marks, [("K1", "RK18")])
                self.assertEqual(len([r for r in m.journal(looked.doc["run"]) if r["kind"] == "start"]), 2)


# ---- G22-6. An address no service file can hold stops under GOV-1 before any file is written (SEC-2, A153) ----------
# Each address is written with `{pw}` where its password stands, filled with a canary at run time: no address with a
# password is a literal of this file (SEC-11's scan, `test_sec_forms`).
CANNOT = (("a line break in a part", "postgres://appuser:{pw}%0Ahost=elsewhere@db.fixture.invalid/appdb"),
          ("Part 2's core in a part", "postgres://appuser:{pw}@db.fixture.invalid/app%E2%80%8Bdb"),
          ("white space at the start of a part", "postgres://appuser:%20{pw}@db.fixture.invalid/appdb"),
          ("white space at the end of a part", "postgres://appuser:{pw}%20@db.fixture.invalid/appdb"),
          ("white space at the end of a parameter", "postgres://appuser:{pw}@db.fixture.invalid/appdb?sslmode=require%20"),
          ("= in a parameter's name", "postgres://appuser:{pw}@db.fixture.invalid/appdb?ssl%3Dmode=require"),
          ("several hosts", "postgres://appuser:{pw}@one.fixture.invalid,two.fixture.invalid/appdb"))


class ServiceFile(harness.Case):
    def test_G22_6_SEC2_GOV1_A153_each_cause_an_address_cannot_be_one_service_section_is_refused(self):
        from sun_core import channels
        pw = "pw" + harness.canary("svc")
        for cause, address in CANNOT:
            with self.subTest(cause=cause):
                with self.assertRaises(ValueError):
                    channels.service_file(address.format(pw=pw), "sun")
        written = channels.service_file("postgres://appuser:{pw}@db.fixture.invalid:5432/appdb?sslmode=require".format(pw=pw), "sun")
        self.assertEqual(written, ("[sun]\nhost=db.fixture.invalid\nport=5432\ndbname=appdb\nuser=appuser\npassword=%s\n"
                                   "sslmode=require\n" % pw).encode("utf-8"))

    def test_G22_6_SEC2_GOV1_A153_white_space_at_a_parts_end_and_several_hosts_stop_the_dump_before_any_file(self):
        for n, (cause, address) in enumerate(CANNOT[2:3] + CANNOT[6:]):
            with self.subTest(cause=cause):
                address = address.format(pw="pw" + harness.canary("svc%d" % n))      # a password no record holds
                m = g20.PasswordFile.fresh(self, "w%d" % n, address, g20.service_providers(inventory_slot=False))
                looked = m.look(kind="sunset")
                self.assertEqual(looked.ending, "preview", looked.text)
                went = m.go(looked, kind="sunset")
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertIn("the connection cannot be written as a service file", went.text)
                self.assertEqual([c for c in m.calls("fakedump") if c["argv"][:1] == ["dump"]], [])
                private = os.path.join(m.facts.run_dir(looked.doc["run"]), "private")
                self.assertEqual([x for x in os.listdir(private) if x.startswith("password-")] if os.path.isdir(private) else [], [])


# ---- G22-7. Slice 4's two small gaps (rows-set T10d's reverse inputs, T17's tree; report-30's lines) ------------------
L = rowlib.lit


def table_change(m, reverse_inputs):
    """G21-8's C6 row (the account's table, its project lines taken out through a computed protected input), with a
    reverse and the reverse inputs given: rows-set T10d's shape."""
    providers = g19.provs()
    providers["fakehost"]["commands"]["take"] = rowlib._command(
        "fakehost", rowlib._t("take", "--file", {"slot": "table"}), [], effects=1,
        protected_inputs=[{"slot": "table", "accepts": "after-image"}])
    commands = [rowlib.use("listing", "fakehost.listing"), rowlib.use("take", "fakehost.take")]
    taken = L(os.path.join(m.home, ".fakes", "fakehost", "taken.jsonl"))
    reverse = rowlib.row("change", "T1-reverse", "one",
                         thing={"role": "the account's table", "identity": "named value", "before_word": "taken out", "after_word": "listed"},
                         planning_test=[{"read": "command", "command": "listing", "result": "success"}],
                         before_test=[{"id": "gone", "read": "text", "command": "listing", "text": L("/x/demo"), "present": False}],
                         after_test=[{"read": "text", "command": "listing", "text": L("/x/demo"), "present": True}],
                         construction={"id": "C6", "command": "take", "risks": ["RK18"], "risk_line": "a line written in between is lost",
                                       "computed": {"param": "table", "from": {"value": {"saved": 0}}, "type": "after-image",
                                                    "label": "the table put back"}},
                         commands=copy.deepcopy(commands), after_check=[{"read": "path", "path": taken, "is": "file"}],
                         way_back={"none": "the row declares none: it is itself a reverse"})
    return providers, rowlib.row(
        "change", "T1", "one",
        thing={"role": "the account's table", "identity": "named value", "before_word": "listed", "after_word": "taken out"},
        planning_test=[{"read": "command", "command": "listing", "result": "success"}],
        before_test=[{"id": "there", "read": "text", "command": "listing", "text": L("/x/demo"), "present": True}],
        after_test=[{"read": "text", "command": "listing", "text": L("/x/demo"), "present": False}],
        construction={"id": "C6", "command": "take", "risks": ["RK18"], "risk_line": "a line written in between is lost",
                      "computed": {"param": "table", "from": {"command": "listing"}, "edit": {"kind": "remove-line", "holding": L("/x/demo")},
                                   "type": "after-image", "label": "the table after"}},
        commands=commands, after_check=[{"read": "path", "path": taken, "is": "file"}],
        way_back={"reverse": reverse}, reverse_inputs=reverse_inputs)


class SliceFour(harness.Case):
    def test_G22_7_LOG2_EV5_T10d_a_commands_protected_text_and_the_computed_table_are_saved_as_the_reverses_inputs(self):
        from sun_core import protected
        m = self.machine()
        canary = harness.canary("cron")
        table = "0 1 * * * keep %s\n5 * * * * /x/demo/run\n10 * * * * other\n" % canary
        m.plan_fake("fakehost", {"command": "noop", "do": "raw", "text": table})
        providers, row = table_change(m, [{"read": "command", "command": "listing", "type": "before-image", "label": "the table before"},
                                          {"read": "computed", "type": "after-image", "label": "the table after"}])
        rowlib.install(m, rowlib.lane("sunrise", [row], **copy.deepcopy(g21.RK18_FORMS)), providers=providers)
        looked, went = m.started()
        self.assertEqual(went.ending, "complete", went.text)
        run_dir = m.facts.run_dir(looked.doc["run"])
        start = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "start" and r["op"] == "T1"][0]
        before, after = [protected.read(m.world().fs, run_dir, ref).decode("utf-8") for ref in start["inputs"]]
        self.assertEqual([ref["type"] for ref in start["inputs"]], ["before-image", "after-image"])
        self.assertEqual(before, table)
        self.assertEqual(after, table.replace("5 * * * * /x/demo/run\n", ""))
        self.assertEqual([s["text"] for s in m.fake("fakehost", "taken.jsonl")], [after], "the table sent is not the after-image saved")
        done = [r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion" and r["op"] == "T1"][0]
        self.assertTrue(done["way_back"]["offered"], done["way_back"])
        self.assertNowhere(canary, went)

    def test_G22_7_RUN6_T17_a_family_read_over_a_folder_tree_finds_the_files_in_every_subfolder(self):
        m = self.machine()
        m.put("dev/vault/top.md", "see OLD/ here\n")
        m.put("dev/vault/a/one.md", "OLD/ again\n")
        m.put("dev/vault/a/b/two.md", "and OLD/\n")
        m.put("dev/vault/a/b/none.md", "nothing\n")
        m.put("dev/vault/a/b/skip.txt", "OLD/ but not a note\n")
        family = {"read": "files", "folder": rowlib.path(rowlib.DEV, "vault"), "glob": "*.md", "holding": "OLD/", "tree": True,
                  "validators": {"path": "a path a shell line may hold"}}
        k = g19.checking("K1", [{"read": "path", "path": {"each": "path"}, "is": "file"}], output={"name": "note {each.n}", "fields": {}})
        k["thing"]["family"] = family
        rowlib.install(m, rowlib.lane("sunrise", [k]), providers=g19.provs())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = g20.manifest_of(m, looked.doc["run"])
        found = sorted(o["thing"]["passes"][0]["path"]["literal"] for o in manifest["operations"] if o["id"].startswith("K1-"))
        self.assertEqual(found, sorted(m.path("dev", "vault", *p.split("/")) for p in ("top.md", "a/one.md", "a/b/two.md")))


# ---- G22-7c. A line with no command cut (rows-rise line 211, M-1; the control room's answer to Question 2) -----------
class LineCut(harness.Case):
    TABLES = {"typecheck": {"web app": L("npm run typecheck")}}

    def looked(self, label, scaffold, cut):
        m = self.machine(label, label)
        pick = {"table": dict({"name": "typecheck", "by": "flags.scaffold"}, **({"cut": "line"} if cut else {}))}
        words = {"text": [L("Run: npm run dev\n"), L("Typecheck: "), pick, L("\n"), L("End")]}
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1", words=words)], tables=copy.deepcopy(self.TABLES)))
        return m, m.look(inputs=m.inputs(flags={"scaffold": scaffold}))

    def test_G22_7c_RUN6_M1_a_text_line_built_from_a_lane_table_whose_key_has_no_entry_is_cut_where_the_text_says_so(self):
        for scaffold, want in (("web app", "Run: npm run dev\nTypecheck: npm run typecheck\nEnd"),
                               ("desktop app", "Run: npm run dev\nEnd")):
            with self.subTest(scaffold=scaffold):
                m, looked = self.looked("c" + scaffold[:3], scaffold, cut=True)
                self.assertEqual(looked.ending, "preview", looked.text)
                words = g20.op_of(g20.manifest_of(m, looked.doc["run"]), "Y1")["commands"][0]["params"]["words"]
                self.assertEqual(words, L(want))

    def test_G22_7c_RUN6_M1_the_same_table_read_with_no_cut_word_stays_a_build_finding(self):
        m, looked = self.looked("n", "desktop app", cut=False)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("a value the look cannot settle", looked.text)
