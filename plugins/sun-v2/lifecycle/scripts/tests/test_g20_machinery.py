"""Part G20: the rest of G19, each item by its smallest mechanism (brief-29, section 2).

Every test's name carries the item's id (G20_n) and the frame's rule it rests on. The rows, the lanes and the provider
declarations here are fixtures under the tests, written with `rowlib`; none is a lane's row.
"""
import copy
import json
import os

import harness
import rowlib
from sun_core import plan, screen

P = plan.RETIREMENT_PHASES


def manifest_of(m, run_id, number=1):
    with open(os.path.join(m.facts.run_dir(run_id), "manifest-%d.json" % number)) as fh:
        return json.load(fh)


def op_of(manifest, op):
    return [o for o in manifest["operations"] if o["id"] == op][0]


def form_text(result):
    return "".join(open(p).read() for p in (result.doc or {}).get("forms") or [])


# ---- G20-1. The dump's password file, one libpq service section (SEC-2, SEC-3) -------------------------------------
SERVICE_ENV = {"PGSERVICEFILE": {"class": "private path", "param": "passfile"}, "PGSERVICE": {"class": "fixed", "value": "sun"}}


def service_providers(inventory_slot=True):
    out = rowlib.providers()
    commands = out["fakedump"]["commands"]
    commands["dump"]["env"] = copy.deepcopy(SERVICE_ENV)
    if inventory_slot:
        commands["inventory"]["env"] = copy.deepcopy(SERVICE_ENV)
    return out


class PasswordFile(harness.Case):
    def fresh(self, label, address, providers):
        m = self.machine(label, label)
        rowlib.install(m, rowlib.lane("sunset", [rowlib.keep("P1", P[0])], phases=P), providers=providers)
        m.put("dev/demo.env", "# fixture\nDATABASE_URL=%s\n" % address, 0o600)
        return m

    def test_G20_1_SEC2_the_dumps_password_file_is_one_libpq_service_section_named_by_PGSERVICEFILE_with_PGSERVICE_fixed(self):
        password = "pw" + harness.canary("svc")
        address = "postgres://appuser:%s@db.fixture.invalid:5432/appdb?sslmode=require&connect_timeout=9" % password
        m = self.fresh("s1", address, service_providers(inventory_slot=False))
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        seen = [s for s in m.fake("fakedump", "passfile.jsonl") if s["passfile"]]
        self.assertEqual(len(seen), 1, seen)
        self.assertEqual(seen[0]["passfile_text"], "[sun]\nhost=db.fixture.invalid\nport=5432\ndbname=appdb\nuser=appuser\n"
                                                   "password=%s\nsslmode=require\nconnect_timeout=9\n" % password)
        self.assertEqual(seen[0]["passfile_mode"], "0o600")
        self.assertTrue(seen[0]["passfile"].startswith(os.path.join(m.facts.run_dir(looked.doc["run"]), "private") + os.sep))
        self.assertFalse(os.path.exists(seen[0]["passfile"]), "the password file is not gone after the call")
        dump = [c for c in m.calls("fakedump") if c["argv"][:1] == ["dump"]][-1]
        self.assertEqual(dump["env_values"].get("PGSERVICE"), "sun")
        self.assertEqual(dump["env_values"].get("PGSERVICEFILE"), seen[0]["passfile"])
        text = json.dumps(dump["argv"]) + json.dumps(dict((k, v) for k, v in dump["env_values"].items() if k != "PGSERVICEFILE"))
        for part in (password, "appuser", "db.fixture.invalid", "5432", "appdb", "sslmode"):
            self.assertNotIn(part, text)
        self.assertNowhere(password, went)

    def test_G20_1_SEC2_GOV1_an_address_whose_part_cannot_be_one_line_of_the_section_stops_the_dump_before_any_file(self):
        password = "pw" + harness.canary("brk")
        address = "postgres://appuser:%s%%0Ahost=elsewhere.invalid@db.fixture.invalid:5432/appdb" % password
        m = self.fresh("s2", address, service_providers(inventory_slot=False))
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the connection cannot be written as a service file", went.text)
        self.assertEqual([c for c in m.calls("fakedump") if c["argv"][:1] == ["dump"]], [], "the dump tool was started")
        private = os.path.join(m.facts.run_dir(looked.doc["run"]), "private")
        self.assertEqual([n for n in os.listdir(private) if n.startswith("password-")] if os.path.isdir(private) else [], [])

    def test_G20_1_SEC2_G9_the_same_file_is_built_for_a_looks_command_that_declares_the_slot_and_gone_after_it(self):
        password = "pw" + harness.canary("look")
        address = "postgres://appuser:%s@db.fixture.invalid/appdb" % password
        m = self.fresh("s3", address, service_providers(inventory_slot=True))
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        seen = [s for s in m.fake("fakedump", "passfile.jsonl") if s["passfile"]]
        self.assertEqual(len(seen), 1, "the look's inventory was not handed the password file")
        self.assertEqual(seen[0]["passfile_text"], "[sun]\nhost=db.fixture.invalid\ndbname=appdb\nuser=appuser\npassword=%s\n" % password)
        self.assertEqual(seen[0]["passfile_mode"], "0o600")
        self.assertFalse(os.path.exists(seen[0]["passfile"]), "the look left its password file")
        self.assertNowhere(password, looked)
        self.assertNotIn(password, json.dumps(manifest_of(m, looked.doc["run"])))


# ---- G20-2. A query and a JSON body on the frame's own request (SEC-2) ------------------------------------------------
class BodyHost(object):
    """A fake host of the frame's own requests that records each request whole, its body among it."""

    def __init__(self):
        self.records = []

    def request(self, host, method, path, headers, timeout, body=None):
        self.records.append({"host": host, "method": method, "path": path, "headers": dict(headers), "body": body})
        return 200, b"{}"


def body_providers():
    out = rowlib.providers()
    out["fakehost"]["commands"]["api-post"] = {
        "tool": "fakehost", "via": "request", "method": "POST", "template": rowlib._t("v1", "things"), "time_limit": 20,
        "effects": 0, "exits": {"200": "success"}, "fields": [], "definite": {"success": ["success"], "refusals": []},
        "query": [{"name": "team", "value": {"literal": "fixture-team"}}, {"name": "name", "value": {"param": "name"}}],
        "body": {"name": {"param": "name"}, "link": {"type": {"literal": "github"}, "id": {"param": "id"}}, "private": {"literal": True}}}
    return out


class RequestBody(harness.Case):
    def test_G20_2_SEC2_a_query_and_a_json_body_on_the_frames_own_request_a_held_leaf_going_back_to_its_issuer(self):
        m = self.machine()
        made = rowlib.create("C1")
        k = rowlib.check("K1", needs=[{"output": "remote", "level": "made", "treatment": "then not applicable"}])
        k["thing"]["passes"] = [{"read": "command", "command": "api", "result": "success"}]
        k["commands"] = [rowlib.use("api", "fakehost.api-post", name=rowlib.NAME, id={"output": "remote.id"})]
        rowlib.install(m, rowlib.lane("sunrise", [made, k]), providers=body_providers())
        m.transport = BodyHost()
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        sent = [r for r in m.transport.records if r["method"] == "POST"]
        self.assertEqual(len(sent), 1, m.transport.records)
        self.assertEqual(sent[0]["host"], "api.fakehost.invalid")
        self.assertEqual(sent[0]["path"], "/v1/things?team=fixture-team&name=demo")
        self.assertEqual(sent[0]["headers"].get("Content-Type"), "application/json")
        held = m.fake("fakehost", "state.json")["things"]["demo"]["id"]
        self.assertEqual(json.loads(sent[0]["body"].decode("utf-8")),
                         {"name": "demo", "link": {"type": "github", "id": held}, "private": True})
        for record in m.journal(looked.doc["run"]):
            self.assertNotIn(held, json.dumps(record))

    def test_G20_2_SEC12_a_body_or_query_value_that_holds_a_register_entry_goes_no_further(self):
        from sun_core import hostcall, results
        register = screen.Screen()
        register.add("canary-" + harness.canary("body"))
        world = type("W", (), {"transport": BodyHost(), "note": lambda self, *a: None})()
        provider = {"host": "api.fakehost.invalid"}
        declaration = {"method": "POST", "time_limit": 5}
        entry = register.entries[0].value
        for query, body in (([("q", entry)], None), ([], {"k": "x" + entry})):
            with self.assertRaises(hostcall.Refused):
                hostcall.send(world, register, provider, declaration, ["v1"], None, query=query, body=body)
        self.assertEqual(world.transport.records, [])
        raw = hostcall.send(world, register, provider, declaration, ["v1"], None, query=[("q", "plain")], body={"k": "plain"})
        self.assertIsInstance(raw, results.Raw)
        self.assertEqual(world.transport.records[0]["path"], "/v1?q=plain")


# ---- G20-3. The lane's kept types; an input's declared validator (RUN-5, SEC-9) ---------------------------------------
KEPT = ["web app", "static site", "desktop app", "script"]


class KeptTypes(harness.Case):
    def test_G20_3_RUN5_a_type_off_the_lanes_kept_list_is_refused_before_the_look_in_plain_words(self):
        for kind, ending in (("library", "refused"), ("web app", "preview")):
            with self.subTest(type=kind):
                m = self.machine(kind.replace(" ", ""), kind.replace(" ", ""))
                rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1")], types=list(KEPT)))
                looked = m.look(inputs=m.inputs(type=kind))
                self.assertEqual(looked.ending, ending, looked.text)
                if ending == "refused":
                    self.assertIn("the project type library is not one this tool keeps; the kept types: web app, static site, "
                                  "desktop app, script", looked.text)
                    self.assertEqual(m.calls("fakehost"), [], "the look read before it refused the type")

    def test_G20_3_SEC9_a_lane_inputs_declared_validator_refuses_the_input_in_the_look(self):
        question = {"question": "The shortcut's name, 2 to 5 lowercase letters or digits?", "input": "shortcut", "required": True,
                    "validator": "a shortcut's name"}
        for answer, ending in (("Bad!", "refused"), ("toolong", "refused"), ("dm", "preview")):
            with self.subTest(answer=answer):
                m = self.machine("v" + answer.strip("!"), "v" + answer.strip("!"))
                rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1")], questions=[question]))
                looked = m.look(inputs=m.inputs(answers={"shortcut": answer}))
                self.assertEqual(looked.ending, ending, looked.text)
                if ending == "refused":
                    self.assertIn("The shortcut's name, 2 to 5 lowercase letters or digits? (the answer given fails its check, "
                                  "a shortcut's name; answer again)", looked.text)
                    self.assertEqual([n for n in os.listdir(m.facts.run_dir(looked.doc["run"])) if n.startswith("manifest")], [])


# ---- G20-4. A question asked only where its read fails; a preview line where a path is present (RUN-5, RUN-8) --------
class ReadQuestions(harness.Case):
    QUESTION = {"question": "The thing at the host is not active. Mend it and summon again, or summon again with as_is.",
                "input": "flags.as_is", "required": True, "layer": "github",
                "when_read_fails": [{"read": "command", "command": "look", "result": "success", "field": "state", "equals": "active"}],
                "commands": [rowlib.use("look", "fakehost.get", name=rowlib.NAME)]}

    def test_G20_4_RUN5_a_lane_question_is_asked_only_where_its_declared_read_fails(self):
        cases = (("active", {}, "preview"), ("paused", {}, "refused"), ("paused", {"flags": {"as_is": True}}, "preview"),
                 ("paused", {"drop_layers": ["github"]}, "preview"))
        for n, (state, more, ending) in enumerate(cases):
            with self.subTest(state=state, more=more):
                m = self.machine("q%d" % n, "q%d" % n)
                m.set_fake("fakehost", things={"demo": {"id": "x", "kind": "repo", "state": state, "name": "demo"}})
                rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1")], questions=[copy.deepcopy(self.QUESTION)]))
                looked = m.look(inputs=m.inputs(**more))
                self.assertEqual(looked.ending, ending, looked.text)
                if ending == "refused":
                    self.assertIn(self.QUESTION["question"], looked.text)
                read = [c for c in m.calls("fakehost") if c["argv"][:1] == ["get"]]
                self.assertEqual(len(read), 0 if more else 1)

    def test_G20_4_RUN8_a_preview_line_is_shown_where_a_named_path_is_present(self):
        present = [{"path": rowlib.path(rowlib.DEV, "wrangler.toml"),
                    "line": {"text": [rowlib.lit("loose end, yours to handle, never acted on: wrangler.toml in "), rowlib.DEV]}}]
        for there in (True, False):
            with self.subTest(there=there):
                m = self.machine("p%s" % there, "p%s" % there)
                if there:
                    m.put("dev/wrangler.toml", "name = 'x'\n")
                rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1")], present_lines=present))
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                line = "loose end, yours to handle, never acted on: wrangler.toml in %s" % m.path("dev")
                self.assertEqual(line in form_text(looked), there)
                self.assertEqual(manifest_of(m, looked.doc["run"]).get("present_lines", []), [line] if there else [])


# ---- G20-5. The lane's slot for v1's fixed text; the last record's head lines (FORM-1, KEEP-5) ------------------------
class FixedText(harness.Case):
    def test_G20_5_FORM1_the_lanes_slot_for_v1s_fixed_text_carried_in_the_manifest_and_the_preview_rendered_with_its_own(self):
        fixed = {"preview": [{"text": [rowlib.lit("Sunrise for "), rowlib.NAME, rowlib.lit(" (v1's fixed head)")]}],
                 "summary": [rowlib.lit("Summary: the fixed text of v1")], "handoff": [{"text": [rowlib.lit("Project "), rowlib.NAME, rowlib.lit(" is active.")]}]}
        m = self.machine()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1")], fixed_text=fixed))
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = manifest_of(m, looked.doc["run"])
        self.assertEqual(manifest["fixed_text"], {"preview": ["Sunrise for demo (v1's fixed head)"], "summary": ["Summary: the fixed text of v1"],
                                                  "handoff": ["Project demo is active."]})
        self.assertEqual(open(looked.doc["forms"][0]).read().split("\n")[0], "Sunrise for demo (v1's fixed head)")

    def test_G20_5_KEEP5_the_last_record_is_wrapped_in_the_lanes_fixed_head_lines(self):
        head = [rowlib.lit("---"), {"text": [rowlib.lit("name: "), rowlib.NAME]}, {"text": [rowlib.lit("date: "), {"clock": "date"}]},
                rowlib.lit("---"), {"text": [rowlib.lit("# "), rowlib.NAME, rowlib.lit(", sunset")]}]
        m = self.machine()
        rowlib.install(m, rowlib.lane("sunset", [rowlib.last_record("L1", P[3])], phases=P, last_record_head=head))
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        record = [n for n in os.listdir(m.path("dev")) if n.startswith("demo-record-")]
        self.assertEqual(len(record), 1)
        lines = open(m.path("dev", record[0])).read().split("\n")
        self.assertEqual(lines[:5], ["---", "name: demo", "date: 2026-01-01", "---", "# demo, sunset"])
        self.assertTrue(lines[5].startswith("SUNSET: the record of run "), lines[5])


# ---- G20-6. A secret list field: each member entered in the register (SEC-4 as A150 words it) ------------------------
def secret_pairs_providers():
    import test_g19_machinery as g19
    out = g19.keys_provs()
    field = out["fakehost"]["commands"]["values"]["fields"][0]
    field["disposition"] = "secret"
    return out


class SecretList(harness.Case):
    def run_keep(self, label, values, later=None):
        import test_g19_machinery as g19
        m = self.machine(label, label)
        m.set_fake("fakehost", identity="source-one")
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0,
                                 "stdout": {"envs": [{"key": "FIXTURE_A", "value": values[0]}, {"key": "FIXTURE_B", "value": values[1]}]}})
        row = g19.keep_row(scope={"inventory_from": {"pairs": "pairs"}})
        row["construction"]["builder"] = "values"
        row["commands"] = [rowlib.use("values", "fakehost.values"), rowlib.use("ident", "fakehost.identify")]
        rowlib.install(m, rowlib.lane("sunrise", [row] + ([later] if later else [])), providers=secret_pairs_providers())
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        return m, looked, m.go(looked)

    def test_G20_6_SEC4_A150_each_member_of_a_secret_list_is_entered_in_the_register_as_a_secret_fields_value_is(self):
        values = ["first-member-" + harness.canary("one"), "second-member-" + harness.canary("two")]
        m, looked, went = self.run_keep("s1", values)
        self.assertEqual(went.ending, "complete", went.text)
        journal = m.journal(looked.doc["run"])
        receipts = [r for r in journal if r["kind"] == "step" and r.get("step") == "receipt" and r.get("field") == "pairs"]
        self.assertEqual([r["outcome"] for r in receipts], ["kept"])
        self.assertEqual(receipts[0]["reference"]["type"], "secret field")
        for value in values:
            self.assertNotIn(value, json.dumps(journal))
            self.assertNowhere(value, went)
            self.assertNotIn(value, form_text(went))
        # the second member is entered in the register on receipt and searched for in the run's records at once, as a secret
        # field's value is (SEC-12): with the manifest holding it as text, the search finds it, a safe ground is disproved,
        # and the run stops at the keep before anything is written
        m2, looked2, went2 = self.run_keep("s2", values, later=rowlib.says("Y2", words=rowlib.lit("told " + values[1])))
        self.assertEqual(went2.ending, "stopped", went2.text)
        self.assertIn("stopped: a safe ground disproved", went2.lines)
        self.assertEqual([r["kind"] for r in m2.journal(looked2.doc["run"]) if r["kind"] == "disproof"], ["disproof"])
        self.assertFalse(os.path.exists(m2.path("dev", "demo-env.txt")))
        self.assertEqual([c for c in m2.calls("fakehost") if "told" in " ".join(c["argv"])], [])


# ---- G20-7. A staged document chosen in the look (A150, the control room's reading) -----------------------------------
STAGED = {"name": "staged.scope", "read": "files", "folder": rowlib.path(rowlib.DEV, "staged"), "glob": "demo-scope*.md",
          "date": True, "choose": True, "validators": {"name": "one line of plain words"}}


class StagedChoice(harness.Case):
    def look(self, label, files, answers=None):
        m = self.machine(label, label)
        for name, text in files:
            m.put("dev/staged/" + name, text)
        y = rowlib.says("Y1", words={"text": [{"fact": "staged.scope.path"}, rowlib.lit(" "), {"fact": "staged.scope.date"}]},
                        condition={"on": "fact", "fact": "staged.scope.found", "equals": True, "reason": "nothing staged"})
        rowlib.install(m, rowlib.lane("sunrise", [y], facts=[copy.deepcopy(STAGED)]))
        return m, m.look(inputs=m.inputs(answers=answers or {}))

    def test_G20_7_A150_several_staged_documents_are_listed_by_the_tools_numbers_and_his_number_chooses_before_the_preview(self):
        files = [("demo-scope-a.md", "2026-09-01: scope a\n"), ("demo-scope-b.md", "2026-09-02: scope b\n")]
        m, looked = self.look("c1", files)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("Several staged documents match for staged.scope; answer with the number of the one to take, as "
                      "answers.staged.scope: 1: demo-scope-a.md; 2: demo-scope-b.md", looked.text)
        m, looked = self.look("c2", files, {"staged.scope": "2"})
        self.assertEqual(looked.ending, "preview", looked.text)
        words = op_of(manifest_of(m, looked.doc["run"]), "Y1")["commands"][0]["params"]["words"]
        self.assertEqual(words, {"literal": "%s 2026-09-02" % m.path("dev", "staged", "demo-scope-b.md")})
        m, looked = self.look("c3", files, {"staged.scope": "3"})
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("as answers.staged.scope: 1: demo-scope-a.md; 2: demo-scope-b.md", looked.text)

    def test_G20_7_A150_a_staged_document_with_no_date_asks_for_one_and_the_date_he_types_binds(self):
        files = [("demo-scope.md", "the scope, undated\n")]
        m, looked = self.look("d1", files)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("The staged document for staged.scope has no date in its first line or its name; type its date (YYYY-MM-DD) "
                      "as answers.staged.scope.date", looked.text)
        m, looked = self.look("d2", files, {"staged.scope.date": "not a date"})
        self.assertEqual(looked.ending, "refused", looked.text)
        m, looked = self.look("d3", files, {"staged.scope.date": "2026-09-03"})
        self.assertEqual(looked.ending, "preview", looked.text)
        words = op_of(manifest_of(m, looked.doc["run"]), "Y1")["commands"][0]["params"]["words"]
        self.assertEqual(words, {"literal": "%s 2026-09-03" % m.path("dev", "staged", "demo-scope.md")})

    def test_G20_7_A150_one_dated_staged_document_asks_nothing_and_none_is_not_applicable(self):
        m, looked = self.look("o1", [("demo-scope.md", "2026-09-04: the scope\n")])
        self.assertEqual(looked.ending, "preview", looked.text)
        m, looked = self.look("o2", [])
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(manifest_of(m, looked.doc["run"])["not_applicable"][0]["reason"], "nothing staged")
