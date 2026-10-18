"""Part G25: five mechanisms the reviewer's lane checks proved (brief-34, section 2).

Every test's name carries the item's id (G25_n) and the frame's rule it rests on. The rows, the lanes and the provider
declarations here are fixtures under the tests, written with `rowlib`; none is a lane's row.
"""
import copy
import hashlib
import json
import os

import harness
import rowlib
import test_g19_machinery as g19
import test_g20_machinery as g20
import test_g21_machinery as g21
import test_g23_machinery as g23
from sun_core import plan

L = rowlib.lit
P = plan.RETIREMENT_PHASES
FORMS = copy.deepcopy(g21.RK18_FORMS)


# ---- G25-1. The look keeps a retiring row's identity read; a mark compares against it (EV-1, EV-3, GOV-1; prov P1) -----
SAME = {"read": "command", "command": "look", "result": "success", "field": "id", "equals": {"identity": "planned"}, "compare_held": True}


def pause_retiring(keeps=(), planned=True):
    """g23's pause row made a retirement at a provider: the look reads its target's identity (`thing.identity_read`), and
    its before-test and after-check each compare the id read then with the one the look read (`{"identity": "planned"}`)."""
    row = g23.pause_row("T21", P[2], "active", "paused", "fakehost.api-pause", {"read": {"command": "look", "field": "id"}},
                        way_back={"none": "the row declares none"}, keeps_required=list(keeps))
    row["thing"].update({"retires": True, "where": "provider", "identity_read": {"command": "look", "field": "id"}})
    if planned:
        row["before_test"].append(dict(SAME, id="same"))
        row["after_check"].append(dict(SAME))
    return row


class ReplacedHost(g23.PauseHost):
    """The fake host of the pause, where another actor replaces the paused thing under its name before the confirming read:
    the thing then has another id."""

    def request(self, host, method, path, headers, timeout, body=None):
        code, doc = g23.PauseHost.request(self, host, method, path, headers, timeout, body)
        state = self.m.fake("fakehost", "state.json")
        state["things"]["demo"]["id"] = "t2new"
        self.m.set_fake("fakehost", things=state["things"])
        return code, doc


class PlannedIdentity(harness.Case):
    def sunset(self, label, transport=g23.PauseHost):
        m = self.machine(label, label)
        m.set_fake("fakehost", things=copy.deepcopy(g23.THING))
        rowlib.install(m, rowlib.lane("sunset", [pause_retiring()], phases=P, **copy.deepcopy(FORMS)), providers=g23.pause_providers())
        m.transport = transport(m)
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        return m, looked

    def test_G25_1_EV1_EV3_SEC4_the_look_keeps_the_identity_it_read_held_and_the_pause_lands_on_that_thing(self):
        m, looked = self.sunset("a")
        manifest = g20.manifest_of(m, looked.doc["run"])
        op = [o for o in manifest["operations"] if o["id"] == "T21"][0]
        same = [c for c in op["before_test"] if c.get("id") == "same"][0]
        self.assertEqual(sorted(same["equals"]), ["record"], same)
        self.assertEqual(same["equals"]["record"]["type"], "held field")
        self.assertNotIn("t1abc", json.dumps(manifest), "the held id stands in the manifest")
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"])["T21"], "done")
        self.assertEqual([(r["path"], r["id"]) for r in m.transport.records], [("/v1/pause", "t1abc")])
        self.assertNowhere("t1abc", went)

    def test_G25_1_GOV1_EV3_a_thing_replaced_under_its_name_after_the_look_is_foreign_and_is_never_paused(self):
        m, looked = self.sunset("b")
        things = copy.deepcopy(g23.THING)
        things["demo"]["id"] = "t2new"                   # another actor replaces it, keeping its name and its state
        m.set_fake("fakehost", things=things)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("foreign", went.text)
        self.assertNotIn("T21", m.statuses(looked.doc["run"]))
        self.assertEqual(m.transport.records, [], "an effect was sent to the replacement")
        self.assertEqual(m.fake("fakehost", "state.json")["things"]["demo"]["state"], "active")

    def test_G25_1_EV1_GOV1_a_thing_replaced_between_the_pause_and_its_confirming_read_fails_the_after_check(self):
        m, looked = self.sunset("c", transport=ReplacedHost)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the after-check does not show the after-state", went.text)
        self.assertNotIn("T21", m.statuses(looked.doc["run"]), "the pause was recorded done on another thing's read")
        self.assertEqual([(r["path"], r["id"]) for r in m.transport.records], [("/v1/pause", "t1abc")])
        self.assertFalse([r for r in m.journal(looked.doc["run"]) if r["kind"] == "completion" and r.get("op") == "T21"])


# ---- G25-2. `keeps_required` naming a family row stands for every member (KEEP-2; prov P2) ----------------------------
def tie_providers():
    out = g23.pause_providers()
    out["fakehost"]["commands"].update(copy.deepcopy(g19.keys_provs()["fakehost"]["commands"]))
    return out


def env_keep(rid, place, name):
    """g19's keep of the saved env values in the keeping phase, its source's identity the fake host's `get --name` id."""
    k = g19.keep_row(rid, scope={"inventory_from": {"lines": "FIXTURE_"}})
    k["phase"] = P[0]
    k["thing"]["place"] = k["planning_test"][0]["path"] = k["before_test"][0]["path"] = place
    k["after_test"][0]["path"] = k["after_check"][0]["path"] = place
    k["output"] = {"name": "env copy " + rid, "fields": {"path": place}}
    k["commands"] = [c for c in k["commands"] if c["name"] != "ident"] + [rowlib.use("ident", "fakehost.get", name=name)]
    k["keep_scope"]["source_identity_read"] = {"command": "ident", "field": "id"}
    return k


def tie_rows():
    fixed = env_keep("P1", rowlib.path(rowlib.DEV, {"text": [rowlib.NAME, L("-env.txt")]}), rowlib.NAME)
    custom = env_keep("PF", rowlib.path(rowlib.DEV, {"text": [rowlib.NAME, L("-env-"), {"each": "label"}, L(".txt")]}), {"each": "label"})
    custom["commands"].append(rowlib.use("envs", "fakehost.envs"))
    custom["thing"]["family"] = {"read": "command", "command": "envs", "field": "custom"}
    custom["output"]["name"] = "env copy {each.label}"
    return [fixed, custom, pause_retiring(keeps=["P1", "PF"], planned=False)]


class DemoHost(g23.PauseHost):
    """The pause's fake host where a custom environment's thing carries the project's id too: the pause is of the project."""

    def request(self, host, method, path, headers, timeout, body=None):
        sent = json.loads(body.decode("utf-8")) if body else {}
        self.records.append({"host": host, "path": path, "id": sent.get("id")})
        state = self.m.fake("fakehost", "state.json")
        if host != "api.fakehost.invalid" or state["things"]["demo"]["id"] != sent.get("id"):
            return 404, b"{}"
        state["things"]["demo"]["state"] = "paused"
        self.m.set_fake("fakehost", things=state["things"])
        return 200, b"{}"


class FamilyKeeps(harness.Case):
    def sunset(self, label, custom_id="t1abc"):
        m = self.machine(label, label)
        things = copy.deepcopy(g23.THING)
        things["custom-1"] = {"id": custom_id, "kind": "env", "state": "active", "name": "custom-1"}
        m.set_fake("fakehost", things=things)
        m.plan_fake("fakehost", {"command": "noop", "do": "fail", "exit": 0, "stdout": {"envs": [{"slug": "one-env"}]}})
        rowlib.install(m, rowlib.lane("sunset", tie_rows(), phases=P, **copy.deepcopy(FORMS)), providers=tie_providers())
        m.transport = DemoHost(m)
        return m

    def test_G25_2_KEEP2_a_family_keep_named_by_a_retirement_stands_for_every_member_bound_before_the_go(self):
        m = self.sunset("a")
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = g20.manifest_of(m, looked.doc["run"])
        ops = dict((o["id"], o) for o in manifest["operations"])
        self.assertIn("PF-custom-1", ops)
        self.assertIn("T21", ops, manifest["not_applicable"])
        self.assertEqual(ops["T21"]["keeps_required"], ["P1", "PF-custom-1"])
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual([r["path"] for r in m.transport.records], ["/v1/pause"])

    def test_G25_2_KEEP2_a_custom_environments_keep_of_another_source_unties_the_retirement_at_the_look(self):
        m = self.sunset("b", custom_id="t9zzz")
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = g20.manifest_of(m, looked.doc["run"])
        self.assertIn("PF-custom-1", [o["id"] for o in manifest["operations"]])
        self.assertNotIn("T21", [o["id"] for o in manifest["operations"]])
        self.assertIn(("T21", "cannot be tied to its copy"), [(n["row"], n["reason"]) for n in manifest["not_applicable"]])
        self.assertTrue([c for c in m.calls("fakehost", "get") if c["argv"][1:] == ["--name", "custom-1"]],
                        "the look read no source identity of the custom environment's keep")
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.transport.records, [], "the pause was sent")

    def test_G25_2_KEEP2_each_members_recorded_source_is_compared_again_before_the_pause(self):
        m = self.sunset("c")
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        state = m.fake("fakehost", "state.json")
        state["things"]["custom-1"]["id"] = "t9zzz"        # the custom environment's source changes after the look
        m.set_fake("fakehost", things=state["things"])
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the target is not the thing its keep copied", went.text)
        self.assertIn("PF-custom-1", open(went.doc["forms"][0]).read(), "the stop does not name the member's keep")
        self.assertEqual(m.transport.records, [], "the pause was sent")
        self.assertEqual(m.statuses(looked.doc["run"]).get("PF-custom-1"), "done")


# ---- G25-3. A keep's `scope` reads at the look where its place is the plan's to make (KEEP-1, RUN-7; prov P3, T03) ----
PASSWORD = "pw" + harness.canary("g25pass")
ADDRESS = "postgres://appuser:%s@db.fixture.invalid:5432/appdb?sslmode=require" % PASSWORD
PAGES = {"read": "command", "command": "pages", "result": "success", "field": "next", "present": False}


def scope_providers():
    out = rowlib.providers()
    out["fakehost"]["commands"]["pages"] = rowlib._command(
        "fakehost", rowlib._t("list"), [rowlib._field("next", "name", "held", required=(), **rowlib.NAMEF)])
    return out


def folder_keep(paged=False):
    """A build of the sunset folder, then the dump of rowlib's keep placed in it (its place the build's output, as T03's
    and T04's are), its `scope` read the dump tool's inventory; with `paged`, a second `scope` read of a listing's next
    page (T04's `next` present false)."""
    folder = rowlib.build("B1", P[0], place=rowlib.path(rowlib.DEV, "sunset"), output="sunset folder")
    place = rowlib.path({"output": "sunset folder.path"}, {"text": [rowlib.NAME, L("-dump.txt")]})
    keep = rowlib.keep("P1", P[0], place=place, needs=[{"output": "sunset folder", "level": "made", "treatment": "then not applicable"}])
    if paged:
        keep["planning_test"].append(dict(PAGES, id="scope"))
        keep["commands"].append(rowlib.use("pages", "fakehost.pages"))
    return [folder, keep]


class ScopeAtTheLook(harness.Case):
    def sunset(self, label, paged=False):
        m = self.machine(label, label)
        rowlib.install(m, rowlib.lane("sunset", folder_keep(paged), phases=P), providers=scope_providers())
        m.put("dev/demo.env", "# fixture\nDATABASE_URL=%s\n" % ADDRESS, 0o600)
        m.set_fake("fakehost", identity="db-" + hashlib.sha256(m.home.encode()).hexdigest()[:10])
        return m

    def test_G25_3_KEEP1_RUN7_T03_a_table_that_cannot_be_read_ends_the_look_though_the_keeps_place_is_the_plans(self):
        m = self.sunset("a")
        m.set_fake("fakedump", unreadable=["beta"])
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the whole scope of a keep cannot be read or established: row P1", looked.lines)
        self.assertTrue([l for l in looked.lines if l.startswith("1 table of row P1 cannot be read; its name is in a private file: ")], looked.lines)
        self.assertTrue(m.calls("fakedump"), "the scope was not read at the look")
        self.assertEqual(set(c["argv"][0] for c in m.calls("fakedump")), {"inventory"}, "more than the scope was read at the look")
        self.assertNowhere("beta", looked)
        self.assertNowhere(PASSWORD, looked)
        self.assertFalse(os.path.exists(m.path("dev", "sunset")))

    def test_G25_3_KEEP1_RUN7_T04_a_listing_already_known_to_be_paged_ends_the_look(self):
        m = self.sunset("b", paged=True)
        m.plan_fake("fakehost", {"command": "list", "stdout": {"next": "cursortwo"}})
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the whole scope of a keep cannot be read or established: row P1", looked.lines)
        self.assertEqual([c["argv"][0] for c in m.calls("fakehost", "list")], ["list"])
        self.assertNowhere("cursortwo", looked)

    def test_G25_3_KEEP1_a_whole_scope_read_at_the_look_lets_the_run_build_the_folder_and_keep_into_it(self):
        m = self.sunset("c", paged=True)
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("inventory", [c["argv"][0] for c in m.calls("fakedump")])
        self.assertEqual(len(m.calls("fakehost", "list")), 1)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertTrue(os.path.isfile(m.path("dev", "sunset", "demo-dump.txt")))


# ---- G25-4. A `text` read with an `under` heading (OP-5, OP-6; set C2, T16) ------------------------------------------
IDX = rowlib.path(rowlib.DEV, "vault", "_index.md")
MOVE = {"kind": "move-line", "holding": L("OLD/_index"), "old": L("OLD"), "new": L("NEW"), "under": L("## Archived")}


def index_row(edit=None):
    under = lambda t, **k: dict({"read": "text", "path": IDX, "text": L(t), "under": L("## Archived")}, **k)      # noqa: E731
    plain = lambda t, **k: dict({"read": "text", "path": IDX, "text": L(t)}, **k)       # noqa: E731
    after = [under("NEW/_index", count=1), plain("OLD/_index", present=False)]
    return rowlib.row("change", "T16", "one",
                      thing={"role": "the root index", "identity": "path", "place": IDX, "tracked": ["exists", "sha256"], "span": True},
                      planning_test=[{"read": "path", "path": IDX, "is": "file"}],
                      before_test=[plain("OLD/_index", count=1)], after_test=after,
                      construction={"id": "C3", "risks": ["RK2"], "edit": copy.deepcopy(edit or MOVE)},
                      after_check=copy.deepcopy(after), way_back={"none": "the row declares none"},
                      output={"name": "root index archived", "fields": {}})


class UnderHeading(harness.Case):
    def run_index(self, label, text, edit=None):
        m = self.machine(label, label)
        m.put("dev/vault/_index.md", text)
        rowlib.install(m, rowlib.lane("sunrise", [index_row(edit)]), providers=g19.provs())
        return m, m.look()

    def test_G25_4_OP5_OP6_a_link_already_under_another_heading_is_not_already_so(self):
        m, looked = self.run_index("a", "# Index\n## Active\n- [[NEW/_index|demo]]\n")
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the thing is in neither state the row names: row T16", looked.lines)
        self.assertEqual(open(m.path("dev", "vault", "_index.md")).read(), "# Index\n## Active\n- [[NEW/_index|demo]]\n")

    def test_G25_4_OP6_the_after_check_fails_where_the_line_does_not_stand_under_its_heading(self):
        m, looked = self.run_index("b", "# Index\n## Active\n- [[OLD/_index|demo]]\n",
                                   edit={"kind": "replace", "old": L("OLD/_index"), "new": L("NEW/_index")})
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("the after-check does not show the after-state", went.text)
        self.assertNotIn("T16", m.statuses(looked.doc["run"]))

    def test_G25_4_OP5_OP6_the_line_moved_under_its_heading_is_done_and_one_already_there_already_so(self):
        cases = (("c", "# Index\n## Active\n- [[OLD/_index|demo]]\n", "done", "# Index\n## Active\n## Archived\n- [[NEW/_index|demo]]\n"),
                 ("d", "# Index\n## Archived\n- [[NEW/_index|demo]]\n## Later\n", "already so", None))
        for label, text, status, after in cases:
            with self.subTest(status=status):
                m, looked = self.run_index(label, text)
                self.assertEqual(looked.ending, "preview", looked.text)
                went = m.go(looked)
                self.assertEqual(went.ending, "complete", went.text)
                if status == "done":
                    self.assertEqual(m.statuses(looked.doc["run"])["T16"], "done")
                    self.assertEqual(open(m.path("dev", "vault", "_index.md")).read(), after)
                else:
                    self.assertNotIn("T16", [o["id"] for o in g20.manifest_of(m, looked.doc["run"])["operations"]])


# ---- G25-5. A restore's reverse whose place an earlier phase's reverse changes is tested by the probe (RUN-6; set V05) -
BACKS = ("putting back", "putting back the indexes")
VAULT = {"vault/_index.md": "status: active\nsee [[OLD/x]]\n", "vault/other.md": "see [[OLD/y]]\n"}


def index_and_notes(index_phase=BACKS[1]):
    """Set's T16 and T17 in the shape of the code check's case: T16 a whole-image swap of the root index (its reverse V05
    the whole recorded after-image put back by the before-image, EV-6), and T17 a family over the vault's notes holding
    `OLD/`, the root index one of them, so that T17 changes the root index after T16 (its reverse V06, in an earlier phase
    of the restore than V05's)."""
    line = lambda p, n, **k: dict({"read": "line", "path": p, "line": {"saved": n}}, **k)     # noqa: E731
    text = lambda p, t, **k: dict({"read": "text", "path": p, "text": L(t)}, **k)          # noqa: E731
    v05 = rowlib.row("change", "V05", index_phase,
                     thing={"role": "the root index", "identity": "path", "place": IDX, "tracked": ["exists", "sha256"], "span": True},
                     planning_test=[{"read": "path", "path": IDX, "is": "file"}],
                     before_test=[line(IDX, 1, count=1)], after_test=[line(IDX, 0, count=1), line(IDX, 1, present=False)],
                     construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace", "old": {"saved": 1}, "new": {"saved": 0}}},
                     after_check=[line(IDX, 0, count=1)], way_back={"none": "the row declares none: it is itself a reverse"},
                     output={"name": "root index active", "fields": {}})
    t16 = rowlib.row("change", "T16", P[1],
                     thing={"role": "the root index", "identity": "path", "place": IDX, "tracked": ["exists", "sha256"], "span": True},
                     planning_test=[{"read": "path", "path": IDX, "is": "file"}],
                     before_test=[text(IDX, "status: active", count=1)], after_test=[text(IDX, "status: archived", count=1)],
                     construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace", "old": L("status: active"), "new": L("status: archived")}},
                     after_check=[text(IDX, "status: archived", count=1)], way_back={"reverse": v05},
                     reverse_inputs=[{"read": "file", "path": IDX, "type": "before-image", "label": "the root index before"},
                                     {"read": "computed", "type": "after-image", "label": "the root index after"}],
                     span={"placement": "in place", "ordered": True}, output={"name": "root index archived", "fields": {}})
    back = {"saved": 2}
    v06 = rowlib.row("change", "V06", BACKS[0],
                     thing={"role": "the note", "identity": "path", "place": back, "tracked": ["exists", "sha256"], "span": True},
                     planning_test=[{"read": "path", "path": back, "is": "file"}],
                     before_test=[line(back, 1, count=1)], after_test=[line(back, 0, count=1)],
                     construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace", "old": {"saved": 1}, "new": {"saved": 0}}},
                     after_check=[line(back, 0, count=1)], way_back={"none": "the row declares none: it is itself a reverse"},
                     output={"name": "note back {each.n}", "fields": {}})
    note = {"each": "path"}
    t17 = rowlib.row("change", "T17", P[1],
                     thing={"role": "the note", "identity": "path", "place": note, "tracked": ["exists", "sha256"], "span": True,
                            "family": {"read": "files", "folder": rowlib.path(rowlib.DEV, "vault"), "glob": "*.md", "holding": L("OLD/"),
                                       "validators": {"path": "a path a shell line may hold"}}},
                     planning_test=[{"read": "path", "path": note, "is": "file"}],
                     before_test=[text(note, "OLD/", present=True)], after_test=[text(note, "OLD/", present=False)],
                     construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "replace-all", "old": L("OLD/"), "new": L("NEW/")}},
                     after_check=[text(note, "OLD/", present=False)], way_back={"reverse": v06},
                     reverse_inputs=[{"read": "file", "path": note, "type": "before-image", "label": "the note before"},
                                     {"read": "computed", "type": "after-image", "label": "the note after"},
                                     {"read": "value", "value": {"each": "path"}, "type": "line", "label": "where it was taken from"}],
                     span={"placement": "in place", "ordered": True}, output={"name": "note repointed {each.n}", "fields": {}})
    return [t16, t17]


class EarlierReverse(harness.Case):
    def sunset(self, label, index_phase=BACKS[1]):
        m = self.machine(label, label)
        for rel, body in VAULT.items():
            m.put("dev/" + rel, body)
        rowlib.install(m, rowlib.lane("sunset", index_and_notes(index_phase), phases=P), rowlib.lane("restore", [], phases=BACKS),
                       providers=g19.provs())
        looked = m.look(kind="sunset")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(open(m.path("dev", "vault", "_index.md")).read(), "status: archived\nsee [[NEW/x]]\n")
        return m

    def test_G25_5_RUN6_EV6_a_reverse_whose_place_an_earlier_phases_reverse_changes_is_tested_by_its_probe(self):
        m = self.sunset("a")
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        manifest = g20.manifest_of(m, looked.doc["run"])
        self.assertIn("V05", [o["id"] for o in manifest["operations"]])
        went = m.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"])["V05"], "done")
        for rel, body in VAULT.items():
            self.assertEqual(open(m.path("dev", rel)).read(), body, rel)

    def test_G25_5_RUN6_a_reverse_in_the_same_phase_as_the_other_is_still_read_at_the_look(self):
        m = self.sunset("b", index_phase=BACKS[0])
        before = open(m.path("dev", "vault", "_index.md")).read()
        looked = m.look(kind="restore")
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the thing is in neither state the row names: row V05", looked.lines)
        self.assertEqual(open(m.path("dev", "vault", "_index.md")).read(), before)


# ---- G25-R1. The planned identity through the effect's target and every state classification (GOV-1, OP-5, EV-3; the
# reviewer's G25 check) ------------------------------------------------------------------------------------------------
class PlannedThroughTheEffect(harness.Case):
    sunset = PlannedIdentity.sunset

    def test_G25_R1_GOV1_OP5_a_thing_replaced_just_after_the_probe_never_receives_the_effect(self):
        from sun_core import effects
        m, looked = self.sunset("r1")
        probe = effects.probe

        def replaced_after(engine, operation):
            answer = probe(engine, operation)
            if operation["id"] == "T21":
                things = copy.deepcopy(g23.THING)
                things["demo"]["id"] = "t2new"      # another actor replaces it just after the probe's identity read
                m.set_fake("fakehost", things=things)
            return answer
        effects.probe = replaced_after
        try:
            went = m.go(looked, kind="sunset")
        finally:
            effects.probe = probe
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual([r["id"] for r in m.transport.records], ["t1abc"], "the effect was not sent to the planned thing")
        self.assertEqual(m.fake("fakehost", "state.json")["things"]["demo"]["state"], "active", "the replacement received the pause")
        self.assertNotIn("T21", m.statuses(looked.doc["run"]))

    def test_G25_R1_OP5_EV3_a_replacement_already_in_the_after_state_is_foreign_never_already_so(self):
        m, looked = self.sunset("r2")
        things = copy.deepcopy(g23.THING)
        things["demo"].update(id="t2new", state="paused")
        m.set_fake("fakehost", things=things)
        went = m.go(looked, kind="sunset")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("foreign", went.text)
        self.assertNotIn("T21", m.statuses(looked.doc["run"]))
        self.assertFalse([r for r in m.journal(looked.doc["run"]) if r.get("op") == "T21" and r.get("status") == "already so"])
        self.assertEqual(m.transport.records, [])

    def test_G25_R1_OP5_a_replacement_in_the_after_state_after_a_start_record_is_foreign_never_landed(self):
        from test_log_op import at
        m, looked = self.sunset("r3")
        killed = m.go(looked, kind="sunset", kill=at("post", "journal", "start", "T21"))
        self.assertTrue(killed.killed, killed.text)
        things = copy.deepcopy(g23.THING)
        things["demo"].update(id="t2new", state="paused")
        m.set_fake("fakehost", things=things)
        went = m.resume()
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("foreign", went.text)
        self.assertNotIn("the after-check does not show the after-state", went.text, "it was read as landed")
        self.assertEqual(m.transport.records, [])

    def test_G25_R1_EV1_the_manifest_binds_the_effects_target_and_every_test_to_the_planned_identity(self):
        m, looked = self.sunset("r4")
        manifest = g20.manifest_of(m, looked.doc["run"])
        op = [o for o in manifest["operations"] if o["id"] == "T21"][0]
        same = [c for c in op["before_test"] if c.get("id") == "same"][0]["equals"]
        act = [c for c in op["commands"] if c["name"] == "act"][0]
        self.assertEqual(act["params"]["id"], same, "the effect's id is not the planned identity")
        for key in ("before_test", "after_test", "after_check"):
            self.assertIn(same, [c.get("equals") for c in op[key]], key)
        self.assertNotIn("t1abc", json.dumps(manifest))
