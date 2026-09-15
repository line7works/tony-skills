"""Shared helpers for the runner's tests.

Standard library only, Python 3.9. Every test runs from any working directory (the suite is
discovered with `python3 -m unittest discover -s <this directory>` from elsewhere) and builds
whatever it needs in a scratch directory it removes afterwards.

No test opens `evals/answer-key/` or `evals/trigger-set/held-out/`. The grading tests point the
runner at a stand-in key they write themselves, under `RECHECK_RUNNER_TEST=1` (E10-21).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
RUNNER_DIR = os.path.dirname(TESTS_DIR)
RUNNER = os.path.join(RUNNER_DIR, "runner.py")
FAKE = os.path.join(TESTS_DIR, "fake")
EVALS = os.path.dirname(RUNNER_DIR)
PLUGIN = os.path.dirname(EVALS)
REPO = os.path.dirname(os.path.dirname(PLUGIN))

if RUNNER_DIR not in sys.path:
    sys.path.insert(0, RUNNER_DIR)
import runner  # noqa: E402

CASE = "F1-01-fixed-clean"
TWO_ITEM_CASE = "F3-02-mixed-two-items"


def scratch_root():
    """A scratch root the environment may pin (the brief's own scratch), else a temp dir."""
    pinned = os.environ.get("RECHECK_RUNNER_TEST_SCRATCH")
    if pinned:
        if not os.path.isdir(pinned):
            os.makedirs(pinned)
        return tempfile.mkdtemp(prefix="runner-test-", dir=pinned)
    return tempfile.mkdtemp(prefix="runner-test-")


def cli(args, env=None, cwd=None, interpreter=None):
    """`runner.py <args>` as a child process, from a directory that is not the runner's."""
    environment = dict(os.environ if env is None else env)
    environment.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return subprocess.run([interpreter or sys.executable, RUNNER] + list(args),
                          capture_output=True, text=True,
                          cwd=cwd or os.path.expanduser("~"), env=environment)


def parse_stdout(completed):
    """Every subcommand prints one JSON document on stdout and nothing else (A7a)."""
    if not completed.stdout.strip():
        raise AssertionError("no stdout; stderr was: %s" % completed.stderr[-2000:])
    return json.loads(completed.stdout)


class RunnerCase(unittest.TestCase):
    """A campaign directory with a stage record and a one-setup plan, built without a model."""

    setups = ("claude-code",)
    cases = (CASE,)
    conditions = ("available",)
    repetitions = 1

    def setUp(self):
        self.scratch = scratch_root()
        self.addCleanup(shutil.rmtree, self.scratch, True)
        self.campaign = os.path.join(self.scratch, "campaign")
        self.stage = os.path.join(self.scratch, "stage")
        self.make_campaign()

    # ---- fixtures the tests build
    def make_campaign(self, plan_overrides=None):
        campaign = runner.Campaign(self.campaign)
        campaign.ensure()
        for harness in ("claude-code", "codex", "opencode"):
            os.makedirs(os.path.join(self.stage, "plugins", "recheck-v2", "setups", harness),
                        exist_ok=True)
        runner.write_json(campaign.stage_json, {
            "campaign": campaign.root, "checkout": REPO, "commit": "test-commit",
            "stage": self.stage, "plugin_tree_sha256": "test-tree", "evals_excluded": True,
            "answer_key_or_held_out_in_stage": [], "canonical_content_sha256": None,
            "skill_identity_exit": 0, "files_copied": 0, "staged_at": runner.now_iso()})
        plan = runner.default_plan("test")
        plan["setups"] = [self.setup_spec(name) for name in self.setups]
        plan["cases"] = list(self.cases)
        plan["conditions"] = list(self.conditions)
        plan["repetitions"] = self.repetitions
        plan["routing"] = {"entries": ["T-01-slash-v2-slice"], "repetitions": 1}
        plan["continuation"] = {"case": TWO_ITEM_CASE, "condition": "available",
                                "repetitions": 1}
        plan.update(plan_overrides or {})
        document = dict(plan)
        document.update({
            "planned_at": runner.now_iso(), "campaign": campaign.root,
            "stage": runner.read_json(campaign.stage_json),
            "path_entries": runner.path_entries(require=False),
            "allowlisted_env_names": list(runner.ALLOWED_ENV),
            "case_lanes": {c: runner.lane_index()[c] for c in plan["cases"]},
            "order": runner.order_of(plan),
            "routing_entries": list(plan["routing"]["entries"]),
            "routing_order": runner.routing_order(plan, plan["routing"]["entries"]),
            "continuation_order": runner.continuation_order(plan),
        })
        document["counts"] = {
            "comparison": sum(len(v) for v in document["order"].values()),
            "routing": sum(len(v) for v in document["routing_order"].values()),
            "continuation": sum(len(v) for v in document["continuation_order"].values()),
        }
        document["counts"]["total"] = sum(document["counts"].values())
        runner.write_json(campaign.campaign_json, document)
        self.plan_document = document
        return campaign

    @staticmethod
    def setup_spec(name):
        if name == "opencode":
            return {"name": "opencode", "harness": "opencode", "model": "qwen"}
        return {"name": name, "harness": name}

    def fake_launcher(self, harness):
        return os.path.join(FAKE, "%s-launch.sh" % harness)

    def run_trial(self, harness="claude-code", case=CASE, condition="available", rep=1,
                  env=None, extra_args=()):
        tid = runner.trial_id(harness, case, condition, rep)
        args = ["run", "--campaign", self.campaign, tid,
                "--fake-launcher", self.fake_launcher(harness)] + list(extra_args)
        return tid, cli(args, env=env)

    # ---- the stand-in key of E10-21
    def stand_in_key(self, case=CASE, expected=None):
        """A key a test wrote itself: synthetic entries in the key's shape, never a copy."""
        directory = os.path.join(self.scratch, "key-stand-in")
        os.makedirs(directory, exist_ok=True)
        lane = runner.lane_index()[case]
        entry = {
            "case": case,
            "checks": ["F1"],
            "requirements": ["R5"],
            "runs_at": "E10",
            "expected": expected if expected is not None else {
                "status": "completed",
                "items": [{"disposition": "fixed"}],
            },
            "must_not": ["a stand-in written by the test, never a key value"],
        }
        coverage = {"case": "_coverage", "requirements": {"R5": [case]}, "checks": {"F1": [case]}}
        runner.write_json(os.path.join(directory, "%s.json" % lane), [entry, coverage])
        return directory

    def child_env(self, extra=None):
        """The environment a `cli` child gets: the test flag plus a stand-in, and nothing more."""
        environment = dict(os.environ)
        environment.update(extra or {})
        return environment
