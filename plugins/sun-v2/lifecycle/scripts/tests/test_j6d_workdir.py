"""Part J6d: a provider child with no declared working folder runs in a fresh, empty, owner-only folder outside the run
directory, made for that call in the tool's own folder (`work/`) and kept, with what the child left in it: LOG-3 lets a run
remove nothing outside its run directory but a lock's file, and nothing it did not make (RUN-4: a run directory holds only
what the tool wrote).

Found live: the real `vercel integration add supabase` (SR17's db-add, which declares no working folder) wrote agent skill
files into the folder it ran in, then the run directory: `.agents/skills/supabase/`, `skills-lock.json` and a symlink
`.claude/skills/supabase -> ../../.agents/skills/supabase`. RUN-4's owner-only check refuses a symlink outside
`staging/`, so every later look of those names ended "the read failed: an earlier run's directory does not check out".
The fake db-add now writes the same three things into its working folder (`fakes/prov_fake.py`).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_prov_rise as prov  # noqa: E402
from sun_core import fsio, rundir  # noqa: E402

DROPPED = (".agents", "skills-lock.json", ".claude")


class WorkingFolder(harness.Case):
    def test_SR17_RUN4_SEC3_a_childs_files_in_its_working_folder_never_reach_the_run_directory_and_a_later_look_checks_it_out(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        looked, went = prov.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        run_dir = m.facts.run_dir(looked.doc["run"])
        self.assertEqual(len(provlib.calls(m, "vercel", "db-add")), 1)
        # the earlier run's directory holds only what the tool wrote: none of the child's three, no link outside staging/
        walked = fsio.FS().walk(run_dir)
        self.assertEqual([p for p in walked if os.path.basename(p) in DROPPED or os.path.islink(p)], [])
        self.assertTrue(rundir.owner_only(fsio.FS(), run_dir))
        # what the child left stands in the folder made for its call, in the tool's own folder, which no check reads
        work = os.path.join(m.facts.tool_home, "work")
        left = [os.path.join(work, n) for n in os.listdir(work) if os.path.lexists(os.path.join(work, n, "skills-lock.json"))]
        self.assertEqual(len(left), 1)
        self.assertTrue(os.path.islink(os.path.join(left[0], ".claude", "skills", "supabase")))
        self.assertEqual(os.stat(work).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(left[0]).st_mode & 0o777, 0o700)
        # nor in the project folder, which db-add does not name as its working folder
        self.assertEqual([n for n in DROPPED if os.path.lexists(m.path("dev", "demo", n))], [])
        # a later look of the same names reads the earlier run whole (RUN-4's checks pass on it)
        again = prov.look(m)
        self.assertNotIn("does not check out", again.text)

    def test_SR17_SEC3_the_working_folder_is_fresh_empty_and_owner_only_for_each_call(self):
        m = self.machine()
        prov.sunrise(m)
        prov.env_values(m)
        provlib.put_state(m, "vercel", look_around=True)        # the fake db-add records what its working folder held
        looked, went = prov.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        seen = provlib.state(m, "vercel")["seen_cwd"]
        run_dir = m.facts.run_dir(looked.doc["run"])
        self.assertEqual(seen["entries"], [])
        self.assertEqual(seen["mode"], "0o700")
        self.assertFalse(seen["path"].startswith(run_dir + os.sep) or seen["path"] == run_dir)
        self.assertNotEqual(os.path.realpath(seen["path"]), os.path.realpath(m.path("dev", "demo")))
        self.assertEqual(os.path.dirname(seen["path"]), os.path.join(m.facts.tool_home, "work"))
        # each call has its own: every child that names no working folder started in a folder of its own, none reused
        work = os.path.join(m.facts.tool_home, "work")
        starts = [e for e in went.events if e["op"] == "mkdir" and e["stage"] == "pre" and str(e["subject"]).startswith(work + os.sep)]
        self.assertEqual(len(starts), len(set(e["subject"] for e in starts)))
        self.assertGreater(len(starts), 1)


if __name__ == "__main__":
    import unittest
    unittest.main()
