"""Part J6e: three refusals of the live sunset look (SunLiveTest), each found read-only, each fixed test first.

- L-12, T03: `channels.read_connection` read the env file's first line whose key is among the row's keys, so the real
  `vercel env pull`'s order (POSTGRES_URL, the pooled address with `sslmode` and `supa`, before POSTGRES_URL_NON_POOLING;
  no DATABASE_URL) gave the pooled address, whose `supa` the real psql refuses in a service file ("syntax error in service
  file ..., line 8", exit 2). The one core change: the first of the row's keys, in the row's order, that the file holds.
  T03's keys name POSTGRES_URL_NON_POOLING first.
- L-10, T05: the project's own memory store absent (no session was ever opened in the project) is nothing to keep: T05 is
  not applicable, as v1 skips an absent store. A present store is kept as before.
- L-11, T21 and V11: the real project-read prints no `paused` on a live project (live-survey-1.txt line 35, "field paused
  ... optional MISSING" for an existing live project). An absent `paused` reads live, `paused: true` paused.

The fakes answer as the real tools: `provlib.sunset_world`'s env file in the real order, the fake psql refusing a service
file line libpq does not know, the fake project-read printing `paused` only when paused.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_prov_set as pset  # noqa: E402
import test_lane_set_lib as lib  # noqa: E402
from sun_core import channels, reads, results  # noqa: E402


def manifest(m, run):
    with open(os.path.join(m.facts.run_dir(run), "manifest-1.json")) as fh:
        return json.load(fh)


class EnvKeys(harness.Case):
    """L-12, T03 (the control room's binding: the direct, non-pooled key first, never the pooled one before it)."""

    def test_T03_SEC2_L12_the_row_reads_the_non_pooled_key_first_though_the_file_lists_the_pooled_one_first(self):
        keys = pset.sunset_row("T03")["thing"]["secret_read"]["keys"]
        self.assertEqual(keys[0], "POSTGRES_URL_NON_POOLING")
        self.assertLess(keys.index("POSTGRES_URL_NON_POOLING"), keys.index("POSTGRES_URL"))
        m = self.machine()
        password = harness.canary("j6e-pw")                 # SEC-11: a planted secret built at run time, never a literal
        pooled = "postgres://u:%s@pooler.invalid:6543/d?sslmode=require&supa=x" % password
        direct = "postgres://u:%s@db.invalid:5432/d" % password
        m.put("env.txt", 'POSTGRES_URL="%s"\nPOSTGRES_URL_NON_POOLING="%s"\n' % (pooled, direct))
        self.assertEqual(channels.read_connection(m.world(), m.path("env.txt"), keys), direct)
        # the next key in the row's order where the first is not in the file, and none where the file holds none of them
        m.put("env2.txt", 'POSTGRES_URL="%s"\nOTHER="x"\n' % pooled)
        self.assertEqual(channels.read_connection(m.world(), m.path("env2.txt"), keys), pooled)
        m.put("env3.txt", 'OTHER="x"\n')
        self.assertIsNone(channels.read_connection(m.world(), m.path("env3.txt"), keys))

    def test_T03_SEC2_KEEP1_L12_a_sunset_over_the_real_files_order_dumps_through_the_direct_address_alone(self):
        m = pset.world(self)
        with open(os.path.join(m.world_made[0], ".env.local")) as fh:
            text = fh.read()
        self.assertLess(text.index("POSTGRES_URL="), text.index("POSTGRES_URL_NON_POOLING="))
        self.assertNotIn("DATABASE_URL", text)
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"])["T03"], "done")
        reads = provlib.calls(m, "pg")
        self.assertTrue(reads)
        # every psql and pg_dump went through the direct address: its service section never held the pooler's `supa`
        self.assertEqual([c["command"] for c in reads if "supa" in (c.get("service_keys") or [])], [])
        self.assertTrue(all(c.get("service_keys") for c in reads))


class MemoryStore(harness.Case):
    """L-10, T05."""

    def test_T05_KEEP1_L10_an_absent_memory_store_is_not_applicable_and_the_sunset_completes(self):
        m = pset.world(self)
        shutil.rmtree(lib.store_of(m))
        looked = pset.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        na = dict((n["row"], n["reason"]) for n in manifest(m, looked.doc["run"])["not_applicable"])
        self.assertEqual(na.get("T05"), "the project has no memory store")
        went = lib.go(m, looked)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertFalse(os.path.lexists(os.path.join(pset.folder(m), "memory")))

    def test_T05_KEEP1_L10_a_present_memory_store_is_kept_as_before(self):
        m = pset.world(self)
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"])["T05"], "done")
        self.assertTrue(os.path.isfile(os.path.join(pset.folder(m), "memory", "notes", "one.md")))


# ---- the shipped rows' `paused` reads, each answer as the provider prints it (live-survey-1.txt l.35: no `paused` when live)
ANSWERS = {"absent": {"id": "prj_fixture1", "accountId": "team_fixture1"},
           "false": {"id": "prj_fixture1", "accountId": "team_fixture1", "paused": False},
           "true": {"id": "prj_fixture1", "accountId": "team_fixture1", "paused": True}}


class _Register(object):
    def holds(self, text):
        return False


class _Session(object):
    class world(object):
        fs = None


def paused_reads(test, answer):
    """The `paused` entries of one of the shipped rows' tests, evaluated by the tool's own Reader on `answer`."""
    decl = provlib.shipped("providers", "vercel.json")["commands"]["project-read"]

    def caller(session, command, outputs, op, journal):
        parser = results.Parser(decl, results.Raw(200, json.dumps(ANSWERS[answer]).encode("utf-8")), _Register())   # HTTP 200
        parser.secrets()
        return parser.finish()
    entries = [dict((k, v) for k, v in c.items() if k not in ("id", "on")) for c in test if c.get("field") == "paused"]
    assert entries, test
    return reads.Reader(_Session(), {}, [{"name": "look", "use": "vercel.project-read"}], caller).evaluate(entries)


def live_and_paused_tests():
    t21 = pset.sunset_row("T21")
    v11 = t21["way_back"]["reverse"]
    live = {"T21 planning test": t21["planning_test"], "T21 before test": t21["before_test"],
            "V11 after test": v11["after_test"], "V11 after-check": v11["after_check"]}
    paused = {"T21 after test": t21["after_test"], "T21 after-check": t21["after_check"],
              "V11 planning test": v11["planning_test"], "V11 before test": v11["before_test"]}
    return live, paused


class PausedReads(harness.Case):
    """L-11 and the owner's ruling on Question 4 (J6f item 2): an absent `paused` and an explicit `"paused": false` both read
    live, and only `"paused": true` reads paused, in T21's planning and before tests and V11's after test and after-check
    (`equals "false"` with `or_absent`, J6f's change to `reads.Reader.condition`)."""

    def test_T21_V11_L11_Q4_absent_and_false_read_live_and_paused_true_reads_paused(self):
        live, paused = live_and_paused_tests()
        for name, test in sorted(live.items()):
            with self.subTest(test=name):
                self.assertIs(paused_reads(test, "absent"), True)
                self.assertIs(paused_reads(test, "false"), True)
                self.assertIs(paused_reads(test, "true"), False)
        for name, test in sorted(paused.items()):
            with self.subTest(test=name):
                self.assertIs(paused_reads(test, "true"), True)
                self.assertIs(paused_reads(test, "absent"), False)
                self.assertIs(paused_reads(test, "false"), False)


class Paused(harness.Case):
    """L-11, T21 and restore's V11."""

    def test_T21_V11_OP5_L11_a_live_project_without_a_paused_field_is_paused_then_restored_to_live(self):
        m = pset.world(self)
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"])["T21"], "done")
        self.assertEqual(provlib.state(m, "vercel")["things"]["demo"]["state"], "paused")
        back = lib.look(m, "restore")
        self.assertEqual(back.ending, "preview", back.text)
        returned = lib.go(m, back, "restore")
        self.assertEqual(returned.ending, "complete", returned.text)
        self.assertEqual(m.statuses(back.doc["run"]).get("V11"), "done")
        self.assertEqual(provlib.state(m, "vercel")["things"]["demo"]["state"], "active")

    def test_T21_Q4_L11_a_project_answering_paused_false_reads_live_and_is_paused(self):
        """The owner's ruling on Question 4 (J6f item 2): an explicit `"paused": false` is live, as an absent field is; until
        J6f it was in neither state and the look stopped by name."""
        m = pset.world(self)
        things = provlib.state(m, "vercel")["things"]
        things["demo"]["paused_field"] = False          # the fake prints `"paused": false`, which no survey line has shown
        provlib.put_state(m, "vercel", things=things)
        looked, went = pset.started(m)
        self.assertNotIn("the thing is in neither state the row names: row T21", looked.text)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"])["T21"], "done")


if __name__ == "__main__":
    import unittest
    unittest.main()
