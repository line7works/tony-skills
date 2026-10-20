"""E16 slice 5, the join (J1 item 3): the whole sequence on fakes (contract section 11), on the three joined lanes as they
ship: a sunrise of a disposable project end to end; a sunrise killed at one write boundary and resumed to the unkilled
run's end state; the sunset of that project; its restore.

One fixture machine holds every lane's fakes: slice 2's (`test_lane_rise.machine_for_sunrise`: the scaffolders, the recorded
git), slice 3's (`provlib.wire`: `gh`, `vercel`, `psql`, `pg_dump`, `curl`, the fake host of the frame's own requests) and
slice 4's (`test_lane_set_lib.programs`: the schedule tools and the adapter, under fixture names). Its locations are slice
2's, with the ones only slice 4's rows read added (rows-set C11); every name of the project is `demo` (rows-rise 3.0's three
by place, rows-set C3's three). Each step is asserted by name: the files with their bytes, the fakes' state and call
records, the journal's lines. The forms of each step are written to the test's error stream, as the tool printed them.

What this sequence does not assert, and the tests that do (the join's J1e, the reviewer's J3):
- launch agents, harness routines and crontab lines: none is seeded here, so T10a to T10d and V14a to V14d find none;
  `test_lane_set.SunsetAndRestore`'s T10a/T10b/V14b/V14a, T10c/V14c and T10d/V14d tests retire and restore each;
- staged documents: none is staged, so the SR06 rows are not applicable; `test_lane_rise.Rows`'s SR06 tests move them;
- notes outside the project's vault folder that link it: none; `test_lane_set_g24.NotesBack` repoints and restores them;
- custom hosting environments: none, so T04c finds none; `test_lane_prov_set.EndToEnd`'s sunset keeps one;
- the resumed sunrise's end state is compared by the rise sweep's comparison (`test_lane_rise_sweep.world_facts`), which
  leaves out the memory store and agent files and reduces each fake's state to its things, refs and sets; the database
  resource's connection is asserted on both machines below, and in `test_lane_prov_rise.EndToEnd`;
- each step's whole journal and call sequence: selected statuses, files and calls here; every row's own test, and the
  lanes' kill sweeps, assert their order;
- one kill boundary (after SR15's start record); the kill sweeps kill at every boundary of each lane.
"""
import json
import os
import re
import sys

import harness
import rowlib
import test_lane_rise as rise
import test_lane_rise_sweep as rise_sweep
import test_lane_set_lib as setlib

provlib = rise.provlib
NAMES = ("demo", "demo")              # --also: the slug and the memory stem (rise), the vault folder and the note's stem (set)
CAPS = ("canary", "memory stores", "routines")
DESCRIPTION = "a disposable project of the join"
DATE = "2026-01-01"


def seed(m):
    """The one machine of the sequence (the module's docstring), before any run."""
    rise.machine_for_sunrise(m)
    setlib.programs(m)
    m.settings["locations"].update({
        "vault_root": m.vault, "vault_archive": os.path.join(m.vault, "archive"), "vault_projects_rel": "projects",
        "vault_archive_rel": "archive", "memory_projects": m.path("mem", "projects"), "launch_agents": m.path("agents"),
        "shortcut_root_text": m.dev})
    m.write_settings()
    os.makedirs(m.path("agents"))
    # the values the host holds for the project the sunrise makes, and the database they name (slice 3's fakes)
    m.password = harness.canary("db-password")
    url = "postgres://fixture:%s@db.invalid:5432/demo" % m.password
    every = provlib.ALL_ENVS
    provlib.put_state(m, "vercel", hidden=0, envs={"demo": [{"key": "DATABASE_URL", "value": url, "type": "encrypted", "target": every},
                                                  {"key": "FEATURE", "value": "on", "type": "plain", "target": every}]})
    provlib.put_state(m, "pg", password=m.password, identity="7000000000000000001", tables={"alpha": ["1", "2"]}, unreadable=[])
    # the three shipped lanes, every shipped declaration (slice 4's three under their fixture names, `setlib.providers`)
    lanes = []
    for kind in ("sunrise", "sunset", "restore"):
        with open(os.path.join(rise.ROWS, kind, "lane.json")) as fh:
            lanes.append(json.load(fh))
    rowlib.install(m, *lanes, providers=setlib.providers())
    return m


def store(m):
    """The project's own memory store, as the harness keeps one (the machine-facts module's `project_memory`, E16-12)."""
    return os.path.join(m.path("mem", "projects"), re.sub(r"[^A-Za-z0-9]", "-", m.path("dev", "demo")), "memory")


def look(m, kind, inputs, **kw):
    return m.look("demo", kind, also=NAMES, inputs=inputs, caps=CAPS, **kw)


def go(m, looked, kind, **kw):
    return m.go(looked, "demo", kind, also=NAMES, caps=CAPS, **kw)


def rise_inputs(m):
    return rise.sunrise_inputs(m, description=DESCRIPTION)


def set_inputs(m, **flags):
    """rows-set's inputs alone (the join's J1b item 5): his reason and his flags."""
    return m.inputs("set-inputs-%d.json" % len(os.listdir(m.root)), description=DESCRIPTION, flags=flags)


def forms(step, looked, went):
    """The forms of one step as the tool printed them, to the error stream (the report shows them)."""
    out = []
    for result, names in ((looked, ("preview",)), (went, ("status", "summary"))):
        for path in ((result.doc or {}).get("forms") or []):
            if os.path.basename(path).split("-")[0] in names:
                with open(path) as fh:
                    out.append("---- %s %s ----\n%s" % (step, os.path.basename(path).split("-")[0], fh.read()))
    sys.stderr.write("\n" + "\n".join(out))
    return out


def git(repo, *args):
    return provlib.git(repo, *args)


class Sequence(harness.Case):
    def made(self, label):
        """A machine of its own folder, every machine of the sequence with one seed, so that two of them are comparable."""
        os.makedirs(os.path.join(self.tmp, label))
        return provlib.Machine(os.path.join(self.tmp, label), "home", "seq")

    def test_JOIN_S11_ORD4_OP6_RUN12_J1b_2_3_5_a_sunrise_a_killed_sunrise_resumed_the_sunset_and_its_restore_on_the_joined_lanes(self):
        # ---- 1. the sunrise of a disposable project, end to end ------------------------------------------------------
        m = seed(self.made("one"))
        os.makedirs(store(m))
        with open(os.path.join(store(m), "MEMORY.md"), "w") as fh:
            fh.write("# memory\n")
        looked = look(m, "sunrise", rise_inputs(m))
        self.assertEqual(looked.ending, "preview", looked.text)
        went = go(m, looked, "sunrise")
        self.assertEqual(went.ending, "complete", went.text)
        rise_forms = forms("sunrise", looked, went)
        run = looked.doc["run"]
        statuses = m.statuses(run)
        for op in ("SR02-next", "SR05", "SR07", "SR08", "SR09", "SR10", "SR15", "SR17", "SR17c", "SR19", "SR20", "SR21", "SR22",
                   "SR23", "SR24"):
            self.assertEqual(statuses.get(op), "done", op)
        for op in ("SR00", "SR07-scan", "SR13-agents", "SR13-claude", "SR13-canary", "SR14", "SR16", "SR25"):
            self.assertEqual(statuses.get(op), "passed", op)
        project = m.path("dev", "demo")
        head = git(project, "rev-parse", "main")
        self.assertEqual(git(project, "log", "--format=%s"), "sunrise: the scaffold, the repo doc kit and the adopted docs")
        self.assertEqual(open(os.path.join(project, "CLAUDE.md")).read(), "@AGENTS.md\n")
        self.assertEqual(provlib.remote_head(m), head)                                         # SR15: one push of the head
        self.assertEqual(provlib.state(m, "gh")["things"]["demo"]["state"], "active")          # SR08
        host = provlib.state(m, "vercel")
        self.assertEqual(host["things"]["demo"]["repo"], "demo")                               # SR09
        self.assertEqual((host["resources"]["demo-db"]["connected"], host["resources"]["demo-db"]["project"]), (True, "demo"))
        self.assertIn(m.password, open(os.path.join(project, ".env.local")).read())            # SR19, owner-only
        self.assertEqual(os.stat(os.path.join(project, ".env.local")).st_mode & 0o777, 0o600)
        seed_text = open(m.path("vault", "projects", "demo", "_index.md")).read()
        for line in ("status: active", "- **GitHub:** https://github.com/fixture-account/demo", "- **Vercel:** https://demo.vercel.app"):
            self.assertEqual(seed_text.split("\n").count(line), 1, line)
        self.assertIn("- [[projects/demo/_index|demo]]\n", open(m.path("vault", "_index.md")).read())
        self.assertTrue(open(m.path("shortcuts.txt")).read().endswith('alias dm="cd %s"\n' % project))
        self.assertEqual([c["command"] for c in provlib.calls(m, "gh")].count("create"), 1)
        self.assertEqual(len(provlib.requests(m, "POST")), 1)
        self.assertEqual([r["kind"] for r in m.journal(run)][-1], "run-end")
        self.assertNowhere(m.password, went)
        self.assertTrue(any("SUNRISE COMPLETE: demo" in f for f in rise_forms))

        # ---- 2. the same sunrise, killed at one write boundary and resumed to the unkilled run's end state ------------
        k = seed(self.made("two"))
        os.makedirs(store(k))
        with open(os.path.join(store(k), "MEMORY.md"), "w") as fh:
            fh.write("# memory\n")
        klooked = look(k, "sunrise", rise_inputs(k))
        self.assertEqual(klooked.ending, "preview", klooked.text)
        krun = klooked.doc["run"]
        # the kill: just after SR15's start record is on disk, before its push (OP-6: `not landed`, a new start, the push)
        killed = go(k, klooked, "sunrise",
                    kill=lambda e: e["op"] == "append" and e["stage"] == "post"
                    and "SR15" in [r["op"] for r in k.journal(krun) if r["kind"] == "start"])
        self.assertTrue(killed.killed, killed.text)
        self.assertNotIn("SR15", k.statuses(krun))
        self.assertIsNone(provlib.remote_head(k))
        resumed = k.resume(also=NAMES, caps=CAPS)
        self.assertEqual(resumed.ending, "complete", resumed.text)
        sys.stderr.write("\n---- killed sunrise: the resume ----\n%s\n" % resumed.text)
        self.assertEqual(k.statuses(krun), statuses)
        ends = [rise_sweep.world_facts(x) for x in (m, k)]
        for facts in ends:
            facts["files"] = dict((rel, v) for rel, v in facts["files"].items() if not rel.startswith(("mem", "agents")))
        self.assertEqual(ends[1], ends[0], "the resumed run's end state differs from the unkilled run's")
        for x in (m, k):          # the database resource's connection, which the comparison above does not hold (J3)
            resource = provlib.state(x, "vercel")["resources"]["demo-db"]
            self.assertEqual((resource["connected"], resource["project"]), (True, "demo"))
        self.assertEqual(len([s for s in provlib.state(k, "vercel").get("things", {}).values() if s.get("kind") == "project"]), 1)

        # ---- 3. the sunset of that project ---------------------------------------------------------------------------
        # (the join's J1b item 2: the sunrise left `origin` and main's upstream as v1 did, so G8's reads find no dirty work)
        before = dict((rel, v) for rel, v in harness.tree(m.home).items() if ".git" not in rel.split(os.sep))
        memory = open(m.path("memory", "MEMORY.md")).read()
        slooked = look(m, "sunset", set_inputs(m))
        self.assertEqual(slooked.ending, "preview", slooked.text)
        swent = go(m, slooked, "sunset")
        self.assertEqual(swent.ending, "complete", swent.text)
        forms("sunset", slooked, swent)
        srun = slooked.doc["run"]
        sstatuses = m.statuses(srun)
        for op in ("T02", "T05", "T11-1", "T12", "T13", "T14", "T16", "T18", "T19-1", "T01", "T03", "T04-development",
                   "T04-preview", "T04-production", "T20", "T21", "T30"):
            self.assertEqual(sstatuses.get(op), "done", op)
        self.assertEqual((sstatuses.get("T01s"), sstatuses.get("T12m")), ("passed", "passed"))
        sf = os.path.join(m.archive, "demo.sunset-" + DATE)
        self.assertTrue(open(os.path.join(sf, "demo-db.sql")).read().endswith("-- PostgreSQL database dump complete\n--\n\n\\unrestrict " + provlib.prov_fake.RESTRICT_KEY + "\n\n"))
        self.assertIn('FEATURE="on"', open(os.path.join(sf, "hosting-env.production")).read())
        self.assertFalse(os.path.exists(project))
        self.assertTrue(os.path.isdir(os.path.join(m.archive, "demo", ".git")))
        self.assertEqual(provlib.remote_head(m, ref="refs/tags/sunset-" + DATE), head)        # T01: the tag is the head
        self.assertEqual(provlib.state(m, "gh")["things"]["demo"]["state"], "archived")        # T20
        self.assertEqual(provlib.state(m, "vercel")["things"]["demo"]["state"], "paused")      # T21
        self.assertNotIn("alias dm=", open(m.path("shortcuts.txt")).read())                    # T11
        self.assertTrue(os.path.isfile(m.path("vault", "archive", "demo", "_sunset-%s.md" % srun)))
        self.assertIn("status: archived", open(m.path("vault", "archive", "demo", "_index.md")).read())
        self.assertNowhere(m.password, swent)

        # ---- 4. its restore ------------------------------------------------------------------------------------------
        rlooked = look(m, "restore", set_inputs(m))
        self.assertEqual(rlooked.ending, "preview", rlooked.text)
        rwent = go(m, rlooked, "restore")
        self.assertEqual(rwent.ending, "complete", rwent.text)
        forms("restore", rlooked, rwent)
        rstatuses = m.statuses(rlooked.doc["run"])
        for op in ("V01", "V02", "V03", "V05", "V07", "V08-1", "V10", "V11", "V13-1", "V30"):
            self.assertEqual(rstatuses.get(op), "done", op)
        # every file of the project's layers back byte for byte (J1b item 3: V08 puts the memory index line SR23 appended at
        # the file's end back right after its line above); the memory index keeps T19's `## Archived` heading (G19-14), and
        # the sunset folder, the tombstone and the restore's entry are what the runs added
        after = dict((rel, v) for rel, v in harness.tree(m.home).items() if ".git" not in rel.split(os.sep))
        skip = (".sun-v2", ".fakes", ".config")
        changed = sorted(rel for rel, v in before.items() if rel.split(os.sep)[0] not in skip and after.get(rel) != v)
        self.assertEqual(changed, [os.path.join("memory", "MEMORY.md")], changed)
        self.assertEqual(open(m.path("memory", "MEMORY.md")).read(), memory + "## Archived\n")
        added = sorted(rel for rel in after if rel not in before and rel.split(os.sep)[0] not in skip)
        self.assertTrue(all(rel.startswith((os.path.join("dev", "_archive"), os.path.join("vault", "archive")))
                            or os.path.basename(rel).startswith(("_sunset-", "_restore-")) for rel in added), added)
        self.assertEqual(git(project, "rev-parse", "main"), head)
        self.assertEqual(provlib.state(m, "gh")["things"]["demo"]["state"], "active")
        self.assertEqual(provlib.state(m, "vercel")["things"]["demo"]["state"], "active")
        self.assertEqual(open(m.path("vault", "projects", "demo", "_index.md")).read(), seed_text)
        self.assertTrue(open(m.path("shortcuts.txt")).read().endswith('alias dm="cd %s"\n' % project))
        self.assertTrue(os.path.isdir(sf), "the sunset folder stays")


if __name__ == "__main__":
    import unittest
    unittest.main()
