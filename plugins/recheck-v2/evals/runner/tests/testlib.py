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

    def dispatch_launcher(self):
        """One stub that dispatches to EACH HARNESS's own fake launcher (E10-59 (25)).

        A campaign of three lanes handed one harness's launcher wrote three claude-code
        records, so every codex and opencode lane carried an incomplete catalog and a record
        in the wrong native shape: the detached test's `complete: 3` proved the campaign ran,
        not that the three lanes recorded themselves. The runner tells the launcher which
        harness it is by the one pointer name it passes (E10-7's allowlist), so the stub can
        pick the right fake from its own environment.
        """
        path = os.path.join(self.scratch, "dispatch-launcher.sh")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                "#!/bin/sh\n"
                "h=claude-code\n"
                '[ -n "$RECHECK_CODEX_HOME" ] && h=codex\n'
                '[ -n "$RECHECK_OPENCODE_SETUP" ] && h=opencode\n'
                'exec /usr/bin/python3 "%s/fakelib.py" "$h" "$@"\n' % FAKE)
        os.chmod(path, 0o755)
        return path

    def held_out_stand_in(self, entries=2):
        """A held-out trigger-set file THIS TEST WROTE (E10-21, E10-59 (25)).

        `default_plan` asks for `routing: {"entries": "all"}`, and "all" is the tuning set plus
        the held-out set; the plan tests therefore reached the real
        `evals/trigger-set/held-out/requests.json`. A copy of the runner without it — the
        reviewer's copy, and any copy behind the wall — failed those tests for a missing file
        rather than for anything the runner does. The stand-in carries synthetic entries in the
        set's own shape and is never a copy of a real one.
        """
        path = os.path.join(self.scratch, "held-out-stand-in.json")
        runner.write_json(path, {"requests": [
            {"id": "H-%02d-stand-in" % n,
             "text": "a request this test wrote, entry %d" % n,
             "expected": {"target": "recheck-v2"},
             "competitors": []}
            for n in range(1, entries + 1)]})
        return path

    def held_out_env(self, extra=None, entries=2):
        """The `cli` environment with this test's own held-out stand-in named (E10-21)."""
        environment = {"RECHECK_RUNNER_TEST": "1",
                       "RECHECK_RUNNER_HELDOUT": self.held_out_stand_in(entries)}
        environment.update(extra or {})
        return self.child_env(environment)

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

    def cut_stub(self, name, advance_on_term=False, hold=60, mixed=True):
        """A stub that plants a checkpoint/log pair and then waits to be cut (E10-47, E10-55).

        `advance_on_term` makes the stub advance the checkpoint to `done, done` when it is
        terminated — the exact race finding 15 describes, made deterministic. Before E10-55
        that race won and the cut was invalid; with the group frozen before the capture the
        stub cannot advance until the pair is already retained, which is what the freeze is
        for.

        `mixed=False` writes a state that is never a cut point (both items pending) and exits,
        so the poller never sees one: the other invalid cut E10-47 names, and the shape one
        live Claude hand-off trial produced.

        A resume prompt names no run directory, so the stub answers it and exits at once
        rather than holding for `hold` seconds.
        """
        path = os.path.join(self.scratch, "cut-%s.sh" % name)
        lines = []
        lines.append("#!/bin/sh")
        lines.append('PROMPT="$1"; WS="$2"; OUT="$3"')
        # E10-54(b): the prompt names the run id before the run directory.
        lines.append('RUN=$(sed -n \'s|^Use run id .* and the run directory \\(.*\\)\\.$|\\1|p\''
                     ' "$PROMPT")')
        lines.append('mkdir -p "$OUT"')
        lines.append('cat > "$OUT/trace.jsonl" <<TRACE')
        lines.append('{"type":"system","subtype":"init","session_id":"cut-session-1",'
                     '"model":"claude-opus-5[1m]"}')
        lines.append('TRACE')
        # the resume prompt names no run directory: answer and exit rather than hold
        lines.append('if [ -z "$RUN" ]; then echo \'{"fake":"cut-stub","resume":true}\'; exit 0; fi')
        lines.append('mkdir -p "$RUN"')
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
        if mixed:
            lines.append('write_state 3 pending null 4')
        else:
            # never a cut point: item 0 pending too, so `done` is 0 on every poll
            lines.append('cat > "$RUN/checkpoint.json" <<CP')
            lines.append('{"phase":"adjudicating","integrity":{"seq":2},'
                         '"start_identity":{"commit":"cut-commit"},"continuations":0,'
                         '"scope":{"items":[{"index":0,"state":"pending"},'
                         '{"index":1,"state":"pending"}]}}')
            lines.append('CP')
            lines.append(': > "$RUN/checkpoint.log"')
            lines.append('echo \'{"fake":"cut-stub","mixed":false}\'')
            lines.append('exit 0')
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
