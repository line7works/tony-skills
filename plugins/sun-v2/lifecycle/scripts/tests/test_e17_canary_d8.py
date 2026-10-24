"""E17's canary: every caught CLI secret gets its lasting withhold record.

D8's closing rule (the outside reviewer's J7 check): "Persist value-free disproof for every newly caught secret before
stopping, and prove that subsequent status forms withhold both while earlier records remain byte-identical." Here both of
T04's named CLI secrets (`cli_secrets`: the OIDC token and the automation bypass secret) arrive in one pull and both already
stand in the run's own records (the run's description holds both). The go records one value-free disproof for each and
stops once; the next status form, and every form of the resume, withholds both; the look's own records stay byte-identical.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_set_lib as lib  # noqa: E402
import test_lane_prov_set as pset  # noqa: E402
import test_j7_review as j7  # noqa: E402
from sun_core.screen import forms_of  # noqa: E402


def rested(run_dir, record):
    """The text a disproof record's span rests on in the run's own records."""
    span = record["rests"]["content"]
    return j7.read(os.path.join(run_dir, span["file"]))[span["start"]:span["end"]].decode("utf-8")


class EveryCaughtSecret(harness.Case):
    """D8's closing rule, two secrets in one pull."""

    def test_D8_SEC12_two_dropped_cli_secrets_both_in_the_runs_records_get_one_disproof_each_and_every_later_form_withholds_both(self):
        token, bypass = harness.canary("canarytoken"), harness.canary("canarybypass")
        every = provlib.ALL_ENVS
        # the bypass secret arrives as a line of its own in each pull: a project value that breaks onto a new line in the
        # pulled copy (the fake's `raw-break`), so that the CLI's copy holds the key the row names among its secrets
        m = pset.world(self, values=[{"key": "SPLIT", "value": "a first line\nVERCEL_AUTOMATION_BYPASS_SECRET=" + bypass,
                                      "type": "encrypted", "target": every}])
        provlib.plan(m, "vercel", {"command": "env-pull", "do": "raw-break"})
        provlib.put_state(m, "vercel", oidc_token=token)
        looked = lib.look(m, description="%s %s" % (token, bypass))
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        run_dir = m.facts.run_dir(run)
        before = dict((p, j7.sha(p)) for p in j7.text_files(run_dir))
        went = lib.go(m, looked)
        # the go meets both secrets in T04-development's pull, finds each already in the run's records, records a disproof
        # for each and stops once (SEC-12)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertIn("a safe ground disproved", went.text)
        ends = [r for r in m.journal(run) if r["kind"] == "invocation-end"]
        self.assertEqual(ends[-1]["reason"], {"kind": "a safe ground disproved", "op": "T04-development"})
        disproofs = [r for r in m.journal(run) if r["kind"] == "disproof"]
        self.assertEqual(len(disproofs), 2, disproofs)
        self.assertEqual([r.get("channel") for r in disproofs], ["cli-added secret", "cli-added secret"])
        # each record reads back to a different one of the two secrets, not two spans of one
        self.assertEqual(sorted(rested(run_dir, r) for r in disproofs), sorted([token, bypass]))
        for secret in (token, bypass):
            for form in forms_of(secret):
                self.assertNotIn(form, json.dumps(disproofs))
            self.assertNotIn(secret, went.text)
        # the next status form reads both records back and withholds both values
        status = m.summon("status", lib.NAMES[0], also=lib.ALSO, caps=list(lib.CAPS))
        # the resume reads them back too, withholds both, and completes
        resumed = m.resume(lib.NAMES[0], None, also=lib.ALSO, caps=list(lib.CAPS))
        self.assertEqual(resumed.ending, "complete", resumed.text)
        for result in (went, status, resumed):
            for secret in (token, bypass):
                self.assertNotIn(secret, result.text)
            for form in result.doc.get("forms") or []:
                with open(form) as fh:
                    text = fh.read()
                for secret in (token, bypass):
                    self.assertNotIn(secret, text, form)
        # no disproof was written after the go's two: the later invocations found both already withheld
        self.assertEqual(len([r for r in m.journal(run) if r["kind"] == "disproof"]), 2)
        # every form and record written after the look holds neither; the look's own records are as they were
        for path in j7.text_files(run_dir):
            if path in before:
                self.assertEqual(j7.sha(path), before[path], path)
            else:
                for secret in (token, bypass):
                    self.assertNotIn(secret.encode("utf-8"), j7.read(path), path)
        for path in j7.text_files(pset.folder(m)):
            for secret in (token, bypass):
                self.assertNotIn(secret.encode("utf-8"), j7.read(path), path)


    def test_D8_SEC12_a_caught_cli_secret_that_holds_an_earlier_withheld_value_gets_its_own_disproof_record(self):
        # the signoff's MAJOR (effects.py:758): an earlier record withholds the OIDC token; the bypass secret's value holds
        # the token's whole and stands in the run's records too, so it is no secret an earlier record withholds and is owed
        # its own record and the stop
        token = harness.canary("canarytoken")
        bypass = token + harness.canary("canarybypass")
        every = provlib.ALL_ENVS
        m = pset.world(self, values=[{"key": "SPLIT", "value": "a first line\nVERCEL_AUTOMATION_BYPASS_SECRET=" + bypass,
                                      "type": "encrypted", "target": every}])
        provlib.put_state(m, "vercel", oidc_token=token)
        looked = lib.look(m, description="%s %s" % (token, bypass))
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        run_dir = m.facts.run_dir(run)
        # the first go's pull drops the token alone (the split value stays one quoted line): one record, the stop
        went = lib.go(m, looked)
        self.assertEqual(went.ending, "stopped", went.text)
        disproofs = [r for r in m.journal(run) if r["kind"] == "disproof"]
        self.assertEqual([rested(run_dir, r) for r in disproofs], [token])
        # the resume's pull drops both: the token, withheld by the first record, and the bypass secret, owed its own
        provlib.plan(m, "vercel", {"command": "env-pull", "do": "raw-break"})
        resumed = m.resume(lib.NAMES[0], None, also=lib.ALSO, caps=list(lib.CAPS))
        self.assertEqual(resumed.ending, "stopped", resumed.text)
        self.assertIn("a safe ground disproved", resumed.text)
        disproofs = [r for r in m.journal(run) if r["kind"] == "disproof"]
        self.assertEqual([rested(run_dir, r) for r in disproofs], [token, bypass])
        self.assertEqual([r.get("channel") for r in disproofs], ["cli-added secret", "cli-added secret"])
        # every later form withholds both, and no later invocation writes a third record
        status = m.summon("status", lib.NAMES[0], also=lib.ALSO, caps=list(lib.CAPS))
        again = m.resume(lib.NAMES[0], None, also=lib.ALSO, caps=list(lib.CAPS))
        self.assertEqual(again.ending, "complete", again.text)
        self.assertEqual(len([r for r in m.journal(run) if r["kind"] == "disproof"]), 2)
        # the first go's forms were written before any pull had dropped the bypass secret, so they withhold the token
        # only; every form after the resume's record withholds the bypass secret whole, its tail beyond the token too
        tail = bypass[len(token):]
        for result, secrets in ((went, (token, bypass)), (resumed, (token, bypass, tail)), (status, (token, bypass, tail)),
                                (again, (token, bypass, tail))):
            for text in [result.text] + [j7.read(f).decode("utf-8") for f in result.doc.get("forms") or []]:
                for secret in secrets:
                    self.assertNotIn(secret, text)


if __name__ == "__main__":
    import unittest
    unittest.main()
