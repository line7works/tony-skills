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

# No test touches a real pilot home. The relocation is set BEFORE `runner` is imported, and
# `cli` hands the same two names to every child (the runner honours them only together).
TEST_PILOT_ROOT = os.path.join(tempfile.gettempdir(), "recheck-runner-test-pilot")
os.environ["RECHECK_RUNNER_TEST_PILOT"] = "1"
os.environ.setdefault("RECHECK_PILOT_ROOT", TEST_PILOT_ROOT)
os.environ.setdefault("RECHECK_RUNNER_TOOL_TMPDIR",
                      os.path.join(tempfile.gettempdir(), "recheck-runner-tool-tmp"))

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
    environment["RECHECK_RUNNER_TEST_PILOT"] = "1"
    environment["RECHECK_PILOT_ROOT"] = os.environ["RECHECK_PILOT_ROOT"]
    environment.setdefault("RECHECK_RUNNER_TOOL_TMPDIR",
                           os.path.join(tempfile.gettempdir(), "recheck-runner-tool-tmp"))
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
        # E10-40: the runner holds the two key directories at mode 000 for the whole of every
        # launch. Every test restores them, whatever it did, so a failing test cannot leave
        # the checkout closed behind it.
        self.addCleanup(runner.open_key, None, "a test finished")
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
            "routing_entries": list((plan.get("routing") or {}).get("entries") or []),
            "routing_order": runner.routing_order(
                plan, (plan.get("routing") or {}).get("entries") or [])
            if plan.get("routing") else {},
            "manual_only_order": runner.manual_only_order(plan) if plan.get("routing") else {},
            "continuation_order": runner.continuation_order(plan)
            if plan.get("continuation") else {},
            # E10-45 (finding 9): a key stand-in is honoured only for a campaign the runner
            # itself marks synthetic. Every test campaign says so, in the record and on disk.
            "synthetic": True,
        })
        document["counts"] = {
            "comparison": sum(len(v) for v in document["order"].values()),
            "routing": sum(len(v) for v in document["routing_order"].values()),
            "manual_only": sum(len(v) for v in document["manual_only_order"].values()),
            "continuation": sum(len(v) for v in document["continuation_order"].values()),
        }
        document["counts"]["total"] = sum(document["counts"].values())
        runner.write_json(campaign.campaign_json, document)
        campaign.mark_synthetic("a test built this campaign")
        self.plan_document = document
        return campaign

    @staticmethod
    def setup_spec(name):
        if name == "opencode":
            return {"name": "opencode", "harness": "opencode", "model": "qwen"}
        return {"name": name, "harness": name}

    def fake_launcher(self, harness):
        return os.path.join(FAKE, "%s-launch.sh" % harness)

    def stub_launcher(self, harness, name, sleep=None, **settings):
        """A stub launcher this test WROTE, carrying its behaviour in the file itself.

        Finding 25: the timeout test used to hand `RECHECK_FAKE_SLEEP` to `cli`, and the
        runner's own allowlist (E10-7) removed it before the launcher ever ran, so the child
        never slept and the test proved nothing. Behaviour now travels in the stub's own text
        and in its arguments, which the allowlist cannot touch.
        """
        path = os.path.join(self.scratch, "stub-%s-%s.sh" % (harness, name))
        lines = ["#!/bin/sh"]
        if sleep is not None:
            lines.append("sleep %s" % sleep)
        for key, value in sorted(settings.items()):
            lines.append("%s='%s'; export %s" % (key, value, key))
        lines.append('exec /usr/bin/python3 "%s/fakelib.py" %s "$@"' % (FAKE, harness))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.chmod(path, 0o755)
        return path

    def cut_stub(self, name, advance_on_term=False, hold=60):
        """A stub that plants a checkpoint/log pair and then waits to be cut (E10-47).

        `advance_on_term` makes the stub advance the checkpoint to `done, done` when it is
        terminated — the exact race finding 15 describes, made deterministic — so the runner
        must retain the pair AFTER the process is gone and call the cut invalid.
        """
        path = os.path.join(self.scratch, "cut-%s.sh" % name)
        lines = []
        lines.append("#!/bin/sh")
        lines.append('PROMPT="$1"; WS="$2"; OUT="$3"')
        lines.append('RUN=$(sed -n \'s|^Use the run directory \\(.*\\)\\.$|\\1|p\' "$PROMPT")')
        lines.append('mkdir -p "$OUT" "$RUN"')
        lines.append('cat > "$OUT/trace.jsonl" <<TRACE')
        lines.append('{"type":"system","subtype":"init","session_id":"cut-session-1",'
                     '"model":"claude-opus-5[1m]"}')
        lines.append('TRACE')
        lines.append('write_state() {')
        lines.append('  cat > "$RUN/checkpoint.json" <<CP')
        lines.append('{"phase":"adjudicating","integrity":{"seq":$1},'
                     '"source_identity":{"commit":"cut-commit"},"continuations":0,'
                     '"scope":{"items":[{"index":0,"state":"done","disposition":"fixed"},'
                     '{"index":1,"state":"$2","disposition":"$3"}]}}')
        lines.append('CP')
        lines.append('  : > "$RUN/checkpoint.log"')
        lines.append('  i=0')
        lines.append('  while [ $i -lt $4 ]; do echo "line $i" >> "$RUN/checkpoint.log"; '
                     'i=$((i+1)); done')
        lines.append('}')
        lines.append('write_state 3 pending null 4')
        if advance_on_term:
            lines.append('trap \'write_state 4 done fixed 5; exit 143\' TERM')
        lines.append('sleep %d' % hold)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.chmod(path, 0o755)
        return path

    def run_trial(self, harness="claude-code", case=CASE, condition="available", rep=1,
                  env=None, extra_args=(), launcher=None):
        tid = runner.trial_id(harness, case, condition, rep)
        args = ["run", "--campaign", self.campaign, tid,
                "--fake-launcher", launcher or self.fake_launcher(harness)] + list(extra_args)
        return tid, cli(args, env=env)

    # ---- the stand-in key of E10-21
    def stand_in_key(self, case=CASE, expected=None, runs_at="E10"):
        """A key a test wrote itself: synthetic entries in the key's shape, never a copy."""
        directory = os.path.join(self.scratch, "key-stand-in-%s" % runs_at.lower())
        os.makedirs(directory, exist_ok=True)
        lane = runner.lane_index()[case]
        entry = {
            "case": case,
            "checks": ["F1"],
            "requirements": ["R5"],
            "runs_at": runs_at,
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
