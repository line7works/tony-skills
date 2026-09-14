"""turns.py against a real Claude Code session record (tests/fixtures), plus
the discovery candidates the profile's section 4 names."""

import json
import os
import shutil
import tempfile
import unittest

import testlib

SESSION = "4cd53208-8cb8-4de2-bb71-be7594182bb1"
USER_UUID = "2b6beb74-9024-46c4-9060-33537140d252"
PHRASE = "waive the comma one, ship it"


def ref(uuid):
    return "claude-code:session %s:msg %s" % (SESSION, uuid)


class RealRecordTest(unittest.TestCase):
    def setUp(self):
        self.document = testlib.run_json("turns.py", ["--transcript", testlib.TRANSCRIPT])
        self.map = self.document["turn_attribution"]

    def test_the_turn_ref_shape(self):
        self.assertEqual(
            self.document["turn_ref_shape"], "claude-code:session <sessionId>:msg <uuid>"
        )
        for key in self.map:
            self.assertTrue(key.startswith("claude-code:session "))
            self.assertIn(":msg ", key)

    def test_roles(self):
        self.assertEqual(self.map[ref(USER_UUID)], "user")
        self.assertEqual(self.document["counts"]["user_turns"], 1)
        self.assertEqual(self.document["counts"]["assistant_turns"], 4)
        self.assertEqual(
            sorted(set(self.map.values())), ["assistant", "user"]
        )

    def test_tool_results_stay_unmapped(self):
        self.assertEqual(self.document["counts"]["unmapped_tool_results"], 2)
        with open(testlib.TRANSCRIPT, "r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("toolUseResult") is not None:
                    self.assertNotIn(ref(record["uuid"]), self.map)

    def test_a_harness_written_user_record_stays_unmapped(self):
        """The body of a skill the session invokes arrives as a `user` record of
        text blocks carrying isMeta, turnCompanion and sourceToolUseID."""
        self.assertEqual(self.document["counts"]["unmapped_harness_written"], 1)
        with open(testlib.TRANSCRIPT, "r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("isMeta"):
                    self.assertNotIn(ref(record["uuid"]), self.map)

    def test_find_returns_the_user_turn_and_not_the_assistant_turn(self):
        document = testlib.run_json(
            "turns.py", ["--transcript", testlib.TRANSCRIPT, "--find", PHRASE]
        )
        found = [entry["turn_ref"] for entry in document["found"]]
        self.assertEqual(found, [ref(USER_UUID)])
        # the same sentence sits in an assistant turn of the same transcript
        with open(testlib.TRANSCRIPT, "r", encoding="utf-8") as handle:
            assistants = [
                json.loads(line)
                for line in handle
                if json.loads(line).get("type") == "assistant"
            ]
        repeated = [
            record
            for record in assistants
            if PHRASE in json.dumps(record.get("message", {}).get("content"))
        ]
        self.assertEqual(len(repeated), 1)
        self.assertEqual(self.map[ref(repeated[0]["uuid"])], "assistant")

    def test_find_prints_no_user_text(self):
        code, out, _err = testlib.run(
            "turns.py", ["--transcript", testlib.TRANSCRIPT, "--find", PHRASE]
        )
        self.assertEqual(code, 0)
        body = json.loads(out)
        self.assertEqual(body["find"], PHRASE)
        out_without_find = out.replace(json.dumps(PHRASE), "")
        self.assertNotIn(PHRASE, out_without_find)

    def test_station_refs_are_mapped_station(self):
        document = testlib.run_json(
            "turns.py",
            ["--transcript", testlib.TRANSCRIPT, "--station-ref", "ship-v2:turn 3"],
        )
        self.assertEqual(document["turn_attribution"]["ship-v2:turn 3"], "station")


class SidechainTest(unittest.TestCase):
    """Claude Code 2.1.270 wrote no sidechain record in any session this lane
    measured (an Agent subagent's turns never enter the caller's transcript), so
    this one record is built by the test and labelled synthetic."""

    def test_a_sidechain_record_stays_unmapped(self):
        directory = tempfile.mkdtemp(prefix="recheck-adapter-side-")
        self.addCleanup(shutil.rmtree, directory, True)
        path = os.path.join(directory, "s.jsonl")
        with open(testlib.TRANSCRIPT, "r", encoding="utf-8") as handle:
            records = [json.loads(line) for line in handle if line.strip()]
        synthetic = dict(records[0])
        synthetic["isSidechain"] = True
        synthetic["uuid"] = "00000000-0000-4000-8000-000000000001"
        with open(path, "w", encoding="utf-8") as handle:
            for record in records + [synthetic]:
                handle.write(json.dumps(record) + "\n")
        document = testlib.run_json("turns.py", ["--transcript", path])
        self.assertEqual(document["counts"]["unmapped_sidechain"], 1)
        self.assertNotIn(ref(synthetic["uuid"]), document["turn_attribution"])


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="recheck-adapter-cfg-")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.projects = os.path.join(self.home, "projects", "-tmp-widget-workspace")
        os.makedirs(self.projects)
        self.copy = os.path.join(self.projects, "%s.jsonl" % SESSION)
        shutil.copyfile(testlib.TRANSCRIPT, self.copy)

    def test_the_session_id_in_the_environment_finds_the_transcript(self):
        document = testlib.run_json(
            "turns.py",
            [],
            env={"CLAUDE_CONFIG_DIR": self.home, "CLAUDE_CODE_SESSION_ID": SESSION},
        )
        self.assertEqual(document["discovery"], "env CLAUDE_CODE_SESSION_ID")
        self.assertEqual(document["transcript"], self.copy)

    def test_the_workspace_candidate_finds_it_and_reports_ambiguity(self):
        document = testlib.run_json(
            "turns.py",
            ["--workspace", "/tmp/widget-workspace"],
            env={"CLAUDE_CONFIG_DIR": self.home, "TMPDIR": self.home},
        )
        self.assertEqual(
            document["discovery"], "newest transcript whose cwd is the workspace"
        )
        self.assertIsNone(document["note"])
        second = os.path.join(self.projects, "11111111-1111-4111-8111-111111111111.jsonl")
        shutil.copyfile(testlib.TRANSCRIPT, second)
        document = testlib.run_json(
            "turns.py",
            ["--workspace", "/tmp/widget-workspace"],
            env={"CLAUDE_CONFIG_DIR": self.home, "TMPDIR": self.home},
        )
        self.assertIn("2 transcripts name this workspace", document["note"])

    def test_a_hook_payload_keyed_by_claude_pid_is_read(self):
        tmp = tempfile.mkdtemp(prefix="recheck-adapter-tmp-")
        self.addCleanup(shutil.rmtree, tmp, True)
        payload_dir = os.path.join(tmp, "recheck-v2", "claude-code")
        os.makedirs(payload_dir)
        with open(os.path.join(payload_dir, "4242.json"), "w", encoding="utf-8") as handle:
            json.dump({"session_id": SESSION, "transcript_path": self.copy}, handle)
        document = testlib.run_json(
            "turns.py",
            [],
            env={"CLAUDE_CONFIG_DIR": self.home, "TMPDIR": tmp, "CLAUDE_PID": "4242"},
        )
        self.assertEqual(document["discovery"], "hook payload")
        self.assertEqual(document["session_id"], SESSION)


if __name__ == "__main__":
    unittest.main()
