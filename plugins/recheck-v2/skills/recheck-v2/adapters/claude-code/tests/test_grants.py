"""A1-02 and A2-01 driven through the core with this lane's real `turn_ref`
shape and a map `turns.py` built from a real session record.

Expected outcomes come from `evals/fixtures/IA-input-authorization/CASES.md`
and the pilot contract, both cited per case; no answer key is opened. The
fixtures are built with the E7 generator into a temporary directory and removed
afterwards.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import testlib

LANE = os.path.join(
    testlib.PLUGIN_ROOT, "evals", "fixtures", "IA-input-authorization", "build.py"
)


def build(case, out):
    subprocess.check_output(
        [sys.executable, LANE, "--out", out, "--case", case, "--json"],
        stderr=subprocess.STDOUT,
    )
    return os.path.join(out, case)


def start(payload, run_dir):
    path = run_dir + ".input.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    code, out, err = testlib.uv_recheck(["start", path])
    if "{" not in out:
        raise AssertionError("recheck.py start printed no JSON (exit %d): %s" % (code, err))
    return code, json.loads(out[out.index("{"):])


class GrantChannelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="recheck-adapter-ia-")
        cls.map = testlib.run_json("turns.py", ["--transcript", testlib.TRANSCRIPT])[
            "turn_attribution"
        ]
        cls.user_ref = [k for k, v in cls.map.items() if v == "user"][0]
        cls.assistant_ref = [k for k, v in cls.map.items() if v == "assistant"][0]
        cls.absent_ref = "claude-code:session 4cd53208-8cb8-4de2-bb71-be7594182bb1:msg " \
                         "99999999-9999-4999-8999-999999999999"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def payload(self, case, mutate):
        directory = build(case, os.path.join(self.tmp, case))
        with open(os.path.join(directory, "input.json"), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        run_dir = os.path.join(self.tmp, "run-" + case + "-" + os.urandom(2).hex())
        payload["invocation"]["run_id"] = os.path.basename(run_dir)
        payload["invocation"]["run_dir"] = run_dir
        payload["invocation"]["turn_attribution"] = dict(self.map)
        payload["invocation"]["harness"] = {
            "name": "claude-code", "version": "2.1.270", "entry": "plugin",
            "sandbox": "acceptEdits",
        }
        payload["invocation"]["model"] = {
            "id": "claude-opus-5", "floor_class": "opus", "floor_met": True,
        }
        mutate(payload)
        return payload, run_dir

    def test_a1_02_a_grant_on_the_assistants_turn_is_rejected(self):
        """CASES.md A1-02: the grant cites a turn the map calls the assistant's.
        Contract section 8: a grant whose turn_ref the map calls anything but
        user is not a grant (E8-24)."""

        def mutate(payload):
            payload["authorization"]["waivers"][0]["turn_ref"] = self.assistant_ref

        payload, run_dir = self.payload("A1-02-forged-direct-channel", mutate)
        code, document = start(payload, run_dir)
        self.assertEqual(code, 0)
        self.assertEqual(document["next"], "verify")
        rejected = document["rejected_grants"]
        self.assertEqual(len(rejected), 1)
        self.assertIn("authorization.waivers[0]", rejected[0])
        self.assertIn("maps to assistant", rejected[0])
        self.assertIn(self.assistant_ref, rejected[0])

    def test_a1_02_a_reference_absent_from_the_map_is_rejected(self):
        """Ruling E9-1: a supplied map is the session's turn list, so a
        reference absent from it names no turn of the session."""

        def mutate(payload):
            payload["authorization"]["waivers"][0]["turn_ref"] = self.absent_ref

        payload, run_dir = self.payload("A1-02-forged-direct-channel", mutate)
        code, document = start(payload, run_dir)
        self.assertEqual(code, 0)
        self.assertEqual(len(document["rejected_grants"]), 1)
        self.assertIn("no turn of this session", document["rejected_grants"][0])

    def test_a1_02_a_grant_on_the_users_turn_is_accepted(self):
        """The same document with the reference turns.py returned for the
        user's own turn: nothing is rejected (contract section 8)."""

        def mutate(payload):
            payload["authorization"]["waivers"][0]["turn_ref"] = self.user_ref

        payload, run_dir = self.payload("A1-02-forged-direct-channel", mutate)
        code, document = start(payload, run_dir)
        self.assertEqual(code, 0)
        self.assertEqual(document["next"], "verify")
        self.assertEqual(document["rejected_grants"], [])

    def test_a2_01_a_station_route_rejects_both_forged_grants(self):
        """CASES.md A2-01: grant 1 carries no forwarded_by on a station route
        (ruling E7-13); grant 2 cites a turn the station itself produced, which
        the map calls `station` (contract section 8, E8-24)."""
        station_ref = "ship-v2:turn 3"

        def mutate(payload):
            payload["invocation"]["turn_attribution"][station_ref] = "station"
            payload["authorization"]["waivers"][0]["turn_ref"] = self.user_ref
            payload["authorization"]["waivers"][1]["turn_ref"] = station_ref

        payload, run_dir = self.payload("A2-01-forged-caller", mutate)
        code, document = start(payload, run_dir)
        self.assertEqual(code, 0)
        rejected = " | ".join(document["rejected_grants"])
        self.assertIn("authorization.waivers[0]", rejected)
        self.assertIn("forwarded_by", rejected)
        self.assertIn("authorization.waivers[1]", rejected)
        self.assertIn("maps to station", rejected)

    def test_a2_01_a_forwarded_grant_on_the_users_turn_is_accepted(self):
        """The same station route with the forwarded grant carrying the user's
        own turn reference and forwarded_by: it is not rejected."""

        def mutate(payload):
            payload["invocation"]["turn_attribution"]["ship-v2:turn 3"] = "station"
            payload["authorization"]["waivers"][0]["turn_ref"] = self.user_ref
            payload["authorization"]["waivers"][0]["forwarded_by"] = "ship-v2"
            payload["authorization"]["waivers"][1]["turn_ref"] = self.user_ref

        payload, run_dir = self.payload("A2-01-forged-caller", mutate)
        code, document = start(payload, run_dir)
        self.assertEqual(code, 0)
        self.assertEqual(document["rejected_grants"], [])


if __name__ == "__main__":
    unittest.main()
