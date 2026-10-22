"""Part J6i: a sunset re-planned after its moves (L-17), and the family members done before a re-plan (L-18).

- L-17: the sunset's dirty-repository question reads the repository at `developer_root/<name 0>`, which T12 moved, so no
  sunset could be re-planned once T12 was done (live: stopped `foreign` at T16 after another session wrote the vault root
  index; the re-plan refused "the read failed: the lane's question for flags.archive_as_is"). The question names what it
  guards (`"guards": ["T12"]`); in a re-plan, where every guarded operation has a done-class final record (done, not proven,
  already so), the question stands as it stood at the look that approved them and is not read again.
- L-18: a re-plan expands each family row afresh, and a member done before it whose own change removed what the read looks
  for (T11's shortcut line) was no longer found, so it fell out of the new manifest, and a restore, which offers from the
  manifest in force, could not put it back. Now such a member is carried into the new manifest from the manifest in force,
  with its saved values and its place in the order.
"""
import json
import os

import harness
import test_lane_set_lib as lib
from sun_core import plan

INDEX_LINE = "- [[projects/third/_index|third]]\n"      # what "another session" adds to the vault root index


def manifest(m, run, number):
    with open(os.path.join(m.facts.run_dir(run), "manifest-%d.json" % number)) as fh:
        return json.load(fh)


def numbers(m, run):
    return sorted(int(n[len("manifest-"):-len(".json")]) for n in os.listdir(m.facts.run_dir(run))
                  if n.startswith("manifest-") and n.endswith(".json"))


def replan(m, kind="sunset", **more):
    return m.summon("replan", lib.NAMES[0], "--inputs", lib.inputs(m, **more), also=lib.ALSO, caps=list(lib.CAPS))


def go_on(m, replanned, kind="sunset"):
    return m.go(replanned, lib.NAMES[0], kind, also=lib.ALSO, caps=list(lib.CAPS))


def stopped_foreign_at_t16(case, links_inside=True):
    """A sunset over the fakes whose go stops `foreign` at T16: once T14 is done, another session adds a line to the vault
    root index, whose tracked fingerprint the look recorded (EV-3), after T10, T11, T12 and T13 are done (the live case).
    With `links_inside` false, the project's own vault notes link nowhere into the project's folder, so that T17's members
    are the notes outside it alone (L-19, the report's J6i section: a member inside the moved folder, found again by a
    re-plan after T13, is placed by its archive path, and its restore's reverse meets that path gone)."""
    m = lib.machine(case)
    if not links_inside:
        m.put("vault/projects/demo/_index.md", "---\ntitle: demo\nstatus: active\n---\n# demo\n")
        m.put("vault/projects/demo/plan.md", "the plan\n")
    looked = lib.look(m)
    case.assertEqual(looked.ending, "preview", looked.text)
    run = looked.doc["run"]
    written = []

    def hook(event):
        if not written and event["op"] == "append" and event["stage"] == "post" and m.statuses(run).get("T14") == "done":
            with open(m.path("vault", "_index.md"), "a") as fh:
                fh.write(INDEX_LINE)
            written.append(True)
        return False
    went = lib.go(m, looked, kill=hook)
    return m, looked, went


class Settled(harness.Case):
    """The rule alone: `plan.question_settled`."""

    class State(object):
        def __init__(self, finals):
            self.finals = finals

    def test_J6i_L17_a_question_is_settled_only_where_every_guarded_operation_has_a_done_class_record(self):
        q = {"guards": ["T12"], "input": "flags.archive_as_is"}
        for status, settled in (("done", True), ("not proven", True), ("already so", True), ("refused", False),
                                (None, False)):
            with self.subTest(status=status):
                finals = {} if status is None else {"T12": status}
                self.assertIs(plan.question_settled(q, self.State(finals)), settled)
        self.assertIs(plan.question_settled(q, None), False)                       # a first look: never
        self.assertIs(plan.question_settled({"input": "x"}, self.State({"T12": "done"})), False)      # no guards: never
        self.assertIs(plan.question_settled({"guards": ["T12", "T13"]}, self.State({"T12": "done"})), False)

    def test_J6i_L17_the_shipped_question_guards_T12(self):
        questions = lib.shipped_lane("sunset")["questions"]
        self.assertEqual([q.get("guards") for q in questions if q.get("input") == "flags.archive_as_is"], [["T12"]])


class Replan(harness.Case):
    def test_T16_T11_L17_L18_EV3_a_sunset_stopped_foreign_at_T16_is_re_planned_completes_and_its_restore_puts_the_line_back(self):
        m, looked, went = stopped_foreign_at_t16(self, links_inside=False)
        run = looked.doc["run"]
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("T16", went.text)
        statuses = m.statuses(run)
        for op in ("T11-1", "T12", "T13"):
            self.assertEqual(statuses.get(op), "done", op)
        with open(m.path("shortcuts.txt")) as fh:
            self.assertNotIn('alias dm="', fh.read())
        # L-17: the re-plan builds, the moved repository not read again for the question
        replanned = replan(m)
        self.assertNotIn("the read failed: the lane's question", replanned.text)
        self.assertIn(replanned.ending, ("stopped", "waiting"), replanned.text)
        self.assertTrue(replanned.doc.get("manifest_sha256"), replanned.text)
        latest = numbers(m, run)[-1]
        self.assertGreater(latest, 1)
        # L-18: T11's member, done and no longer found, is carried with its saved values, in its place in the order
        first, again = manifest(m, run, 1), manifest(m, run, latest)
        ids_first = [o["id"] for o in first["operations"]]
        ids_again = [o["id"] for o in again["operations"]]
        self.assertIn("T11-1", ids_again)
        self.assertEqual([o for o in again["operations"] if o["id"] == "T11-1"][0],
                         [o for o in first["operations"] if o["id"] == "T11-1"][0])
        self.assertEqual([i for i in ids_first if i in ids_again], [i for i in ids_again if i in ids_first])
        self.assertNotIn("T11", [n["row"] for n in again["not_applicable"]])
        # its go completes from T16 on
        done = go_on(m, replanned)
        self.assertEqual(done.ending, "complete", done.text)
        self.assertEqual(m.statuses(run).get("T16"), "done")
        # the restore offers T11-1's reverse and puts the line back byte-equal to the saved line
        back = lib.look(m, "restore")
        self.assertEqual(back.ending, "preview", back.text)
        restored = lib.go(m, back, "restore")
        self.assertEqual(restored.ending, "complete", restored.text)
        self.assertEqual(m.statuses(back.doc["run"]).get("V13-1"), "done")
        with open(m.path("shortcuts.txt")) as fh:
            self.assertEqual(fh.read(), 'alias other="cd /elsewhere"\nalias dm="cd %s"\n' % m.path("dev", "demo"))

    def test_L17_RUN7_a_re_plan_before_T12_still_reads_the_question_and_a_dirty_repository_still_asks_it(self):
        m = lib.machine(self)
        looked = lib.look(m)
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        went = lib.go(m, looked, kill=lambda e: e["op"] == "append" and e["stage"] == "post" and m.statuses(run).get("T11-1") == "done")
        self.assertTrue(went.killed, went.text)
        self.assertNotIn("T12", m.statuses(run))
        m.put("dev/demo/scratch.txt", "an untracked file\n")
        replanned = replan(m)
        self.assertIn("The repository has uncommitted changes or unpushed commits", replanned.text)

    def test_V01_V02_L17_a_restore_stopped_after_its_moves_back_is_re_planned_and_completes(self):
        m = lib.machine(self)
        lib.run(self, m)
        back = lib.look(m, "restore")
        self.assertEqual(back.ending, "preview", back.text)
        run = back.doc["run"]
        went = lib.go(m, back, "restore", kill=lambda e: e["op"] == "append" and e["stage"] == "post"
                      and m.statuses(run).get("V01") == "done" and m.statuses(run).get("V02") == "done")
        self.assertTrue(went.killed, went.text)
        replanned = m.summon("replan", lib.NAMES[0], "--inputs", lib.inputs(m), also=lib.ALSO, caps=list(lib.CAPS))
        self.assertTrue(replanned.doc.get("manifest_sha256"), replanned.text)
        done = go_on(m, replanned, "restore")
        self.assertEqual(done.ending, "complete", done.text)


if __name__ == "__main__":
    import unittest
    unittest.main()
