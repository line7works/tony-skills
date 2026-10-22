"""Part J6c: the three provider reads the live survey found off their real shapes (SCRATCH/live-survey-1.txt), read as the
real tools answer, on fakes that answer in those shapes (`fakes/prov_fake.py`).

- L-4, GitHub: SR08, SR08-public and SR08-false read the repository by its address (GraphQL `resource(url:)`), which answers
  an absent repository with exit 0 and a null (`github.repo-at`).
- L-5, the Marketplace's installations: installed is an installation whose `slug` is `supabase` (`vercel.db-installed`,
  without the `--integration` filter, whose quirk lists none).
- L-6, the database: SR17 reads the team's resources by `list --all` (`vercel.db-all`): its planned name absent before the
  create, and after it the resource of product Supabase under that name whose id is the one the create's answer gave.
  SR17c reads the project's resources by `list <slug>` (`vercel.db-list`): the one of product Supabase whose projects
  hold the slug, with the id SR17 saved.

The one core mechanism (results.py, the owner's allowance for J6c): a list field's `where` filter with `one`. Exactly one
member matching reads present, none reads absent, more than one leaves the result `malformed` (GOV-1: the tool never picks).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_prov_rise as prov  # noqa: E402
from sun_core import results  # noqa: E402


class Register(object):
    def holds(self, text):
        return False


def parse(decl, doc, code=0):
    parser = results.Parser(decl, results.Raw(code, json.dumps(doc).encode("utf-8")), Register())
    parser.secrets()
    return parser.finish()


def key(name, place, value, **more):
    """A filter's key, as calls.py leaves it: an equal field with its value settled (`equals_value`)."""
    field = {"name": name, "place": place, "type": "name", "disposition": "equal", "equals": {"literal": value},
             "alphabet": "A-Za-z0-9 ._-", "max_length": 100, "required_in": [], "equals_value": value}
    field.update(more)
    return field


def chosen(where, place=("items", "*", "id")):
    return {"name": "chosen", "place": list(place), "type": "id", "disposition": "held", "alphabet": "A-Za-z0-9_-",
            "max_length": 64, "required_in": [], "where": where, "one": True}


ITEMS = [{"id": "a1", "kind": "Supabase", "tags": ["demo", "x"]}, {"id": "b2", "kind": "Neon", "tags": ["demo"]},
         {"id": "c3", "kind": "Supabase", "tags": ["other"]}]


class WhereOne(harness.Case):
    """The mechanism on its own: equality on a declared key, an item of a list key (`holds`), and `one`."""

    def decl(self, *where_and_keys):
        where, keys = where_and_keys
        return {"exits": {"0": "success"}, "definite": {"success": ["success"], "refusals": []},
                "fields": keys + [chosen(where)]}

    def test_J6c_GOV1_exactly_one_member_matching_reads_present_holding_its_value(self):
        decl = self.decl([{"field": "kind"}, {"field": "tag", "holds": True}],
                         [key("kind", ["kind"], "Supabase"), key("tag", ["tags"], "demo")])
        got = parse(decl, {"items": ITEMS})
        self.assertEqual(got.kind, "success")
        self.assertEqual(got.held("chosen"), "a1")
        self.assertNotIn("kind", got.fields)            # a key is read only through its filter
        self.assertNotIn("tag", got.fields)

    def test_J6c_GOV1_no_member_matching_reads_absent(self):
        decl = self.decl([{"field": "kind"}], [key("kind", ["kind"], "Resend email")])
        got = parse(decl, {"items": ITEMS})
        self.assertEqual(got.kind, "success")
        self.assertNotIn("chosen", got.fields)
        self.assertNotIn("chosen", parse(decl, {"items": []}).fields)

    def test_J6c_GOV1_RUN7_more_than_one_member_matching_is_malformed_the_tool_never_picks(self):
        decl = self.decl([{"field": "kind"}], [key("kind", ["kind"], "Supabase")])
        self.assertEqual(parse(decl, {"items": ITEMS}).kind, "malformed")

    def test_J6c_a_filter_naming_no_declared_field_or_a_key_with_no_settled_value_is_malformed(self):
        self.assertEqual(parse(self.decl([{"field": "nothing"}], [key("kind", ["kind"], "Supabase")]), {"items": ITEMS}).kind,
                         "malformed")
        unsettled = key("kind", ["kind"], "Supabase")
        del unsettled["equals_value"]
        self.assertEqual(parse(self.decl([{"field": "kind"}], [unsettled]), {"items": ITEMS}).kind, "malformed")
        # a key whose value comes from his settings or the tool's own count is no value the filter takes (literal or param)
        settings = key("kind", ["kind"], "Supabase", equals={"settings": "vercel"})
        self.assertEqual(parse(self.decl([{"field": "kind"}], [settings]), {"items": ITEMS}).kind, "malformed")

    def test_J6c_holds_compares_an_item_of_a_list_by_equality_only(self):
        decl = self.decl([{"field": "tag", "holds": True}], [key("tag", ["tags"], "oth")])
        self.assertNotIn("chosen", parse(decl, {"items": ITEMS}).fields)        # no part of an item matches
        decl = self.decl([{"field": "tag", "holds": True}], [key("tag", ["tags"], "other")])
        self.assertEqual(parse(decl, {"items": ITEMS}).held("chosen"), "c3")


def resource(m, name, product="Supabase", projects=()):
    host = provlib.state(m, "vercel")
    found = dict(host.get("resources") or {})
    found[name] = {"id": "res_" + name.replace("-", ""), "name": name, "product": product, "projects": list(projects),
                   "project": None, "connected": False}
    provlib.put_state(m, "vercel", resources=found)


class GitHub(harness.Case):
    """L-4 (survey (a)): SR08's reads by the repository's address."""

    def test_SR08_L4_RUN7_an_absent_repository_reads_free_and_the_look_previews(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        looked = prov.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        reads = [c for c in provlib.calls(m, "gh") if c["command"] == "repo-at"]
        self.assertEqual(len(reads), 1)
        self.assertIn("url=https://github.com/fixture-account/demo", reads[0]["argv"])

    def test_SR08_L4_RUN7_a_repository_at_the_address_is_a_planning_stop_by_name(self):
        m = self.machine()
        prov.sunrise(m)
        provlib.put_state(m, "gh", things={"demo": {"id": "R_theirs01", "kind": "repo", "state": "active", "name": "demo"}})
        looked = prov.look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the place is taken by a thing this run did not make: row SR08", looked.text)
        self.assertEqual(provlib.calls(m, "gh", "create"), [])

    def test_SR08_L4_OP5_the_made_repository_is_read_back_by_its_address_and_bound(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        looked, went = prov.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        bound = prov.outputs(m, looked.doc["run"])
        self.assertEqual(prov.read_held(m, looked.doc["run"], bound["remote repository"]["id"]),
                         provlib.state(m, "gh")["things"]["demo"]["id"])


class Installed(harness.Case):
    """L-5 (survey lines 79-82, 88): installed is an installation whose slug is `supabase`."""

    def test_SR17_L5_G23_10_the_team_without_a_supabase_installation_ends_the_look_on_the_rows_terms_line(self):
        m = self.machine()
        prov.sunrise(m)
        provlib.put_state(m, "vercel", installed=False)
        looked = prov.look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("Accept the Marketplace's terms for Supabase once", looked.text)
        reads = provlib.calls(m, "vercel", "db-installed")
        self.assertTrue(reads)
        self.assertNotIn("--integration", reads[0]["argv"])

    def test_SR17_L5_RUN7_the_team_with_a_supabase_installation_among_others_reads_installed(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        looked = prov.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertNotIn("Accept the Marketplace's terms", looked.text)

    def test_SR17_L5_GOV1_RUN7_two_supabase_installations_are_a_planning_stop_naming_the_row(self):
        m = self.machine()
        prov.sunrise(m)
        provlib.put_state(m, "vercel", installations=["supabase", "resend", "neon"])
        looked = prov.look(m)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertIn("the read was partial: the place of row SR17", looked.text)
        self.assertEqual(provlib.calls(m, "vercel", "db-add"), [])


class Database(harness.Case):
    """L-6 (survey lines 22-29, 73-78, 84-87) and the control room's two binding points: SR17 never adopts a database it
    did not make."""

    def test_SR17_L6_RUN7_no_resource_under_the_planned_name_reads_free_while_others_stand(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        resource(m, "other-db", "Supabase", ["other"])
        resource(m, "mail", "Resend email", ["demo"])
        looked = prov.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertTrue(provlib.calls(m, "vercel", "db-all"))

    def test_SR17_L6_GOV1_RUN7_a_resource_already_under_the_planned_name_is_a_planning_stop_by_name_never_adopted(self):
        for product in ("Supabase", "Neon"):
            with self.subTest(product=product):
                m = self.machine(product, product)
                prov.sunrise(m)
                resource(m, "demo-db", product)
                looked = prov.look(m)
                self.assertEqual(looked.ending, "refused", looked.text)
                self.assertIn("the place is taken by a thing this run did not make: row SR17", looked.text)
                self.assertEqual(provlib.calls(m, "vercel", "db-add"), [])

    def test_SR17_L6_OP5_a_resource_under_the_name_made_between_the_look_and_the_go_stops_it_and_nothing_is_made(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        looked = prov.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        resource(m, "demo-db", "Supabase")
        went = prov.go(m, looked)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(went.doc["lines"][1:3], ["stopped: something has the name", "operation: SR17"])
        self.assertNotEqual(m.statuses(looked.doc["run"]).get("SR17"), "done")
        self.assertEqual(provlib.calls(m, "vercel", "db-add"), [])

    def test_SR17_SR17c_L6_OP5_the_made_database_is_read_back_by_its_id_through_list_all_then_connected(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        resource(m, "mail", "Resend email", ["demo"])
        looked, went = prov.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        run = looked.doc["run"]
        statuses = m.statuses(run)
        self.assertEqual((statuses["SR17"], statuses["SR17c"]), ("done", "done"))
        host = provlib.state(m, "vercel")
        bound = prov.outputs(m, run)
        self.assertEqual(prov.read_held(m, run, bound["database"]["resource"]), host["resources"]["demo-db"]["id"])
        self.assertEqual((host["resources"]["demo-db"]["connected"], host["resources"]["demo-db"]["project"]), (True, "demo"))
        self.assertTrue([c for c in provlib.calls(m, "vercel", "db-all")])
        self.assertTrue([c for c in provlib.calls(m, "vercel", "db-list") if "demo" in c["argv"]])

    def test_SR17_L6_OP6_an_answer_whose_id_the_team_does_not_list_under_the_name_fails_the_after_check(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        provlib.plan(m, "vercel", {"command": "db-add", "nth": 1, "do": "other-id"})
        looked, went = prov.started(m)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(went.doc["lines"][1:3], ["stopped: the after-check does not show the after-state", "operation: SR17"])
        self.assertNotEqual(m.statuses(looked.doc["run"]).get("SR17"), "done")
        self.assertEqual(provlib.calls(m, "vercel", "db-connect"), [])

    def test_SR17c_L6_GOV1_two_supabase_resources_connected_to_the_project_stop_the_run_by_name_and_nothing_is_connected(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        resource(m, "theirs-one", "Supabase", ["demo"])
        resource(m, "theirs-two", "Supabase", ["demo"])
        looked = prov.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        went = prov.go(m, looked)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(went.doc["lines"][1:3], ["stopped: unreadable", "operation: SR17c"])
        self.assertNotIn("SR17c", [op for op, s in m.statuses(looked.doc["run"]).items() if s == "done"])
        self.assertEqual(provlib.calls(m, "vercel", "db-connect"), [])

    def test_SR17c_L6_OP5_a_supabase_resource_of_anothers_connected_to_the_project_is_foreign_and_nothing_is_connected(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        resource(m, "theirs-one", "Supabase", ["demo"])
        looked, went = prov.started(m)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(went.doc["lines"][1:3], ["stopped: foreign", "operation: SR17c"])
        self.assertEqual(provlib.calls(m, "vercel", "db-connect"), [])


if __name__ == "__main__":
    import unittest
    unittest.main()
