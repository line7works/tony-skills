"""Part J6h (L-16): the real preview pull carries 20 system and build entries the CLI adds beside the project's keys, and
T04-preview failed "the keep is not whole". The ruling: the three T04 rows' `cli_keys` name Vercel's documented system and
build entries, exact names, and those lines are left out of the copy; anything unlisted still fails. The Board's binding: a
listed name is dropped only where that target's env API inventory (the before read) does not hold it; a key the project
defines itself (CI, VERCEL_URL, a TURBO_* set by hand) is a project key and stays in the copy.

The fake's preview pull is the real preview shape, by key names; production's real shape is unseen, and the fake gives it
the same with its environment named (`fakes/prov_fake.py`, `CLI_ADDED`).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import prov_fake  # noqa: E402
import test_lane_prov_set as pset  # noqa: E402
import test_j6g_cli_keys as j6g  # noqa: E402

T04 = ("T04-development", "T04-preview", "T04-production")
LISTED = sorted([k for k, _v in prov_fake.CLI_ADDED] + [
    "VERCEL_OIDC_TOKEN", "CI", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_REGION", "VERCEL_DEPLOYMENT_ID",
    "VERCEL_PROJECT_ID", "VERCEL_SKEW_PROTECTION_ENABLED", "VERCEL_AUTOMATION_BYPASS_SECRET"])


def keys_of(data):
    return [l.split("=", 1)[0] for l in data.decode("utf-8").split("\n") if "=" in l and not l.startswith("#")]


class CliList(harness.Case):
    def test_T04_ROW1_L16_the_three_rows_name_the_same_29_cli_entries(self):
        self.assertEqual(len(prov_fake.CLI_ADDED), 20)
        self.assertEqual(len(LISTED), 29)
        for op in T04:
            with self.subTest(row=op):
                self.assertEqual(sorted(pset.sunset_row(op)["keep_scope"]["inventory_from"]["cli_keys"]), LISTED)

    def test_T04_KEEP1_L16_the_real_preview_shape_is_kept_whole_without_the_cli_lines_and_all_three_keeps_complete(self):
        m = pset.world(self)
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual([m.statuses(looked.doc["run"]).get(op) for op in T04], ["done", "done", "done"])
        copies = j6g.env_copies(m)
        self.assertEqual(len(copies), 3)
        for path, data in copies:
            self.assertEqual([k for k in keys_of(data) if k in LISTED], [], path)
            self.assertEqual(keys_of(data), sorted(keys_of(data)), path)
            self.assertIn("FEATURE", keys_of(data))

    def test_T04_KEEP1_L16_one_unlisted_key_the_cli_adds_still_fails_the_keep(self):
        m = pset.world(self)
        provlib.put_state(m, "vercel", cli_extra=["TURBO_UNLISTED_ENTRY"])
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(pset.stop_of(m, looked.doc["run"]), {"kind": "the keep is not whole", "op": "T04-development"})

    def test_T04_KEEP1_L16_Board_a_listed_name_the_project_defines_itself_stays_in_its_copy_and_the_keep_is_whole(self):
        values = [{"key": "CI", "value": "project-ci", "type": "plain", "target": list(provlib.ALL_ENVS)},
                  {"key": "FEATURE", "value": "on", "type": "plain", "target": list(provlib.ALL_ENVS)},
                  {"key": "VERCEL_URL", "value": "project-url", "type": "plain", "target": ["preview"]}]
        m = pset.world(self, values=values)
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual([m.statuses(looked.doc["run"]).get(op) for op in T04], ["done", "done", "done"])
        copies = dict((os.path.basename(p), d) for p, d in j6g.env_copies(m))
        self.assertEqual(len(copies), 3)
        for name, data in sorted(copies.items()):
            with self.subTest(copy=name):
                self.assertIn(b'CI="project-ci"', data)
                self.assertNotIn(b"VERCEL_OIDC_TOKEN", data)
        preview = [d for n, d in copies.items() if "preview" in n]
        self.assertEqual(len(preview), 1)
        self.assertIn(b'VERCEL_URL="project-url"', preview[0])       # the project's own, kept
        others = [d for n, d in copies.items() if "preview" not in n]
        self.assertTrue(all(b"VERCEL_URL" not in d for d in others))  # the CLI's, in production, dropped


if __name__ == "__main__":
    import unittest
    unittest.main()
