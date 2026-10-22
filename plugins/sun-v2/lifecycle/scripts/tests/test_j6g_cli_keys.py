"""Part J6g (L-15): the real `vercel env pull` adds a key of its own, VERCEL_OIDC_TOKEN, a short-lived token that is no
project variable. The env list API does not return it, so T04's keep failed "the keep is not whole". The owner's ruling: the
saved copy holds the project's variables only. T04's `inventory_from` names the CLI's own keys (`cli_keys`), and the tool
drops exactly those lines from the staged copy before the keep is checked; every other extra key still fails the keep.

The token is never in the withheld register, so no output scan of the tool's would catch it: the marker test here drives a
real-shaped pull (the comment line, 16 project keys, the token carrying a marker) and scans everything the run touched.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_prov_set as pset  # noqa: E402

T04 = ("T04-development", "T04-preview", "T04-production")
SKIP = (".fakes",)          # the fakes' own state, which holds what the fake provider is: not the tool's


def files_under(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for name in dirs + files:
            yield os.path.join(base, name)


def holding(root, text):
    """Every file under `root` (links not followed) whose bytes hold `text`, and every path whose name holds it."""
    found, needle = [], text.encode("utf-8")
    for path in files_under(root):
        if text in path:
            found.append(path)
        if os.path.isfile(path) and not os.path.islink(path):
            with open(path, "rb") as fh:
                if needle in fh.read():
                    found.append(path)
    return found


def env_copies(m):
    """The kept environment copies in the sunset folder: each file whose text has a project key line."""
    out = []
    for path in files_under(pset.folder(m)):
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                data = fh.read()
            if b'FEATURE="on"' in data or b'KEY_01="' in data:
                out.append((path, data))
    return out


def sixteen():
    return [{"key": "KEY_%02d" % i, "value": "value-%02d" % i, "type": "encrypted", "target": list(provlib.ALL_ENVS)}
            for i in range(1, 17)]


class CliKeys(harness.Case):
    def test_T04_KEEP1_L15_the_token_the_cli_adds_is_left_out_and_each_copy_is_whole(self):
        m = pset.world(self)
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        statuses = m.statuses(looked.doc["run"])
        self.assertEqual([statuses.get(op) for op in T04], ["done", "done", "done"])
        copies = env_copies(m)
        self.assertEqual(len(copies), 3)
        for path, data in copies:
            self.assertNotIn(b"VERCEL_OIDC_TOKEN", data, path)
            self.assertTrue(data.startswith(b"# Created by Vercel CLI\n"), path)

    def test_T04_KEEP1_L15_a_pull_with_no_token_is_still_whole(self):
        m = pset.world(self)
        provlib.put_state(m, "vercel", no_oidc=True)
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual([m.statuses(looked.doc["run"]).get(op) for op in T04], ["done", "done", "done"])

    def test_T04_KEEP1_L15_any_other_key_the_copy_holds_still_fails_the_keep(self):
        m = pset.world(self)
        provlib.put_state(m, "vercel", cli_extra=["VERCEL_OTHER_ADDED"])
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertEqual(pset.stop_of(m, looked.doc["run"]), {"kind": "the keep is not whole", "op": "T04-development"})
        self.assertNotEqual(m.statuses(looked.doc["run"]).get("T04-development"), "done")

    def test_T04_SEC1_L15_the_tokens_value_reaches_no_copy_record_form_output_or_folder_of_the_run(self):
        marker = harness.canary("oidc-token")
        m = pset.world(self, values=sixteen())
        provlib.put_state(m, "vercel", oidc_token=marker)
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        run = looked.doc["run"]
        self.assertEqual([m.statuses(run).get(op) for op in T04], ["done", "done", "done"])
        # the pull did carry it: the fake's record of what it wrote holds the marker, in the real shape (16 keys, then it)
        copies = env_copies(m)
        self.assertEqual(len(copies), 3)
        for _path, data in copies:
            lines = data.decode("utf-8").split("\n")
            self.assertEqual(lines[0], "# Created by Vercel CLI")
            self.assertEqual([l.split("=", 1)[0] for l in lines[1:-1]], ["KEY_%02d" % i for i in range(1, 17)])
            self.assertEqual(lines[-1], "")
        self.assertEqual(provlib.state(m, "vercel")["oidc_token"], marker)
        # nowhere the tool wrote: the run directory whole (its forms, journal, manifest, protected/, staging/, tmp/), the
        # archive folder, the tool's own folder (its `work/` folders among it), the vault, his home; and no invocation's output
        for root in (m.facts.run_dir(run), m.archive, m.facts.tool_home, m.home):
            self.assertEqual(holding(root, marker), [], root)
        for result in (looked, went):
            self.assertNotIn(marker, result.out)
            self.assertNotIn(marker, result.err)
            self.assertNowhere(marker, result)


if __name__ == "__main__":
    import unittest
    unittest.main()
