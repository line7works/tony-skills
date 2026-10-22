"""Part J6j (L-20): a run's date is fixed by its first look and kept in the run's own record (its first manifest's `date`);
a re-plan reads it from there and never derives it again. Live: a re-plan just after midnight UTC re-dated every dated
operation (T02's archive folder, T01's tag, T14's and T18's dated text, the lane's fixed text and last record head), and the
preview showed the done T02 and T01 under names that did not exist.

The fixture's clock reads 2026-01-01 (`harness.Machine.now`); a test sets it to the next day for its re-plan.
"""
import json
import os

import harness
import test_lane_set_lib as lib
import test_j6i_replan as j6i

D, NEXT = "2026-01-01", "2026-01-02"
DATED = ("T02", "T01", "T14", "T18")


def next_day(m):
    count = [0]

    def now():
        count[0] += 1
        return "%sT00:36:%02dZ" % (NEXT, count[0] % 60)
    m.now = now


def dated(doc, op):
    return json.dumps([o for o in doc["operations"] if o["id"] == op][0], sort_keys=True)


def as_planned(doc, op):
    """An operation as its row's values froze it, the look's own reads of the moment left out: `tracked_state` (what the look
    read of the thing then) and `needs` (settled against what stood then); a carried operation is not read again."""
    return dict((k, v) for k, v in [o for o in doc["operations"] if o["id"] == op][0].items() if k not in ("tracked_state", "needs"))


class RunDate(harness.Case):
    def test_RUN8_L20_a_re_plan_across_midnight_keeps_every_dated_name_and_text_of_the_first_look_and_completes(self):
        m, looked, went = j6i.stopped_foreign_at_t16(self, links_inside=False)
        run = looked.doc["run"]
        self.assertEqual(went.ending, "stopped", went.text)
        first = j6i.manifest(m, run, 1)
        self.assertEqual(first.get("date"), D)
        next_day(m)
        replanned = j6i.replan(m)
        self.assertTrue(replanned.doc.get("manifest_sha256"), replanned.text)
        again = j6i.manifest(m, run, j6i.numbers(m, run)[-1])
        self.assertEqual(again.get("date"), D)
        self.assertNotIn(NEXT, json.dumps(again))
        for op in DATED:
            with self.subTest(op=op):
                self.assertIn(D, dated(first, op))
                self.assertEqual(as_planned(again, op), as_planned(first, op))
        for entry in ("fixed_text", "last_record_head"):
            self.assertEqual(again.get(entry), first.get(entry), entry)
        with open(replanned.doc["forms"][0]) as fh:
            self.assertNotIn(NEXT, fh.read())
        done = j6i.go_on(m, replanned)
        self.assertEqual(done.ending, "complete", done.text)
        self.assertTrue(os.path.isdir(os.path.join(m.archive, "demo.sunset-" + D)))
        self.assertFalse(os.path.lexists(os.path.join(m.archive, "demo.sunset-" + NEXT)))
        self.assertTrue(os.path.isfile(m.path("vault", "archive", "demo", "_sunset-%s.md" % run)))

    def test_RUN8_L20_a_first_look_on_a_new_day_takes_that_day(self):
        m = lib.machine(self)
        next_day(m)
        looked = lib.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        doc = j6i.manifest(m, looked.doc["run"], 1)
        self.assertEqual(doc.get("date"), NEXT)
        self.assertIn("sunset-" + NEXT, dated(doc, "T02"))
        self.assertNotIn(D, json.dumps(doc))


class Fallback(harness.Case):
    """A run made before J6j: its first manifest holds no `date`, and the run's date is the day of its `open` record."""

    def session(self, doc, at, sha=None):
        from sun_core import fsio
        run_dir = os.path.join(self.tmp, "run-%d" % len(os.listdir(self.tmp)))
        os.makedirs(run_dir)
        data = json.dumps(doc).encode("utf-8")
        with open(os.path.join(run_dir, "manifest-1.json"), "wb") as fh:
            fh.write(data)

        class Journal(object):
            records = [{"kind": "open", "manifest": 1, "manifest_sha256": sha or fsio.sha256_hex(data), "at": at}]

        class World(object):
            fs = fsio.FS()

        class Session(object):
            journal = Journal()
            world = World()
        Session.run_dir = run_dir
        return Session()

    def test_RUN8_L20_the_date_comes_from_the_first_manifest_else_from_the_open_record_and_never_from_the_clock(self):
        from sun_core import plan
        self.assertEqual(plan.run_date(self.session({"date": D}, NEXT + "T00:10:00Z")), D)
        self.assertEqual(plan.run_date(self.session({}, D + "T23:59:00Z")), D)
        with self.assertRaises(plan.PlanningStop):
            plan.run_date(self.session({"date": D}, D + "T23:59:00Z", sha="0" * 64))      # a manifest that fails its hash


if __name__ == "__main__":
    import unittest
    unittest.main()
