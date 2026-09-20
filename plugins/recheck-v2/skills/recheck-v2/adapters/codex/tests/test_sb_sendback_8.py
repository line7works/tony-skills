"""Send-back 8, defect 2: the executor-rollout append check behind the sealed bench's wall.

The measured failure (control room, 2026-09-19, root `wall-proof-codex-20260920T005305Z`):
`trials/codex-F1-01-fixed-clean-available-r1` completed, activated the skill and exited 0 from
`validate`, and still graded nothing - `result.json` reads `status: verifier_unavailable`,
`stop_reason: unknown_capability: invocation.model is absent`, because `invocation.py` exited 3
with `writable executor rollout refused: <CODEX_HOME>/sessions/.../rollout-...jsonl (E9-37)`.

E9-37 requires the executor's own rollout to be UNWRITABLE by the session. Under Codex's own
workspace-write sandbox that held: the tool shells could not write the home. Under SB-2 Codex's
sandbox is off (`--sandbox danger-full-access`, because macOS refuses a second seatbelt inside
the first) and the confinement is the launcher's one `sandbox-exec` wall around the whole
process tree - Codex itself must write that rollout, so every shell it starts can too. The
check could never pass behind the wall, so no walled with-skill Codex trial could ever grade.

The fix follows the precedent batch A set in `verifier.py`: a writable executor rollout is
accepted ONLY when `RECHECK_HARNESS_SANDBOX=sandbox-exec` is declared AND a read of
`RECHECK_WALL_PROBE` is refused with PermissionError. The witness code is SHARED, not copied:
it lives in `turns.py` and `verifier.py` imports it.

What these tests pin. No model, no `codex`, no launch: the PermissionError is a mode-000
directory, which is the same error a seatbelt profile produces.

1. a writable rollout with NO marker is refused, with today's E9-37 message unchanged;
2. the marker with a probe that READS is refused the same way (a declaration is not a witness);
3. the marker with a probe that is REFUSED accepts the writable rollout, and the invocation's
   `harness.sandbox` DECLARES it rather than passing silently;
4. an unwritable rollout behaves exactly as it does today, witness or no witness;
5. `sandbox_policy.type: danger-full-access`, which is what the rollout carries behind the
   wall, is not refused as a value when the witness holds, and the E9-37 gate still refuses
   the writable rollout when it does not.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import turns                                                                    # noqa: E402
import verifier                                                                 # noqa: E402


class WalledRolloutCase(unittest.TestCase):
    """An installed helper tree, one executor rollout, and a probe this test can close."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('RECHECK_TEST_SCRATCH'))
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.helpers = self.home / 'plugins/cache/m/p/v/skills/recheck-v2/adapters/codex'
        self.helpers.mkdir(parents=True)
        for name in ['turns.py', 'invocation.py', 'verifier.py']:
            shutil.copyfile(ROOT / name, self.helpers / name)
        self.rows = turns.read_records(ROOT / 'tests/fixtures/real-rollout.jsonl')
        self.meta = turns.facts(self.rows)[0]
        self.thread = self.meta['id']
        # the probe the wall refuses: a mode-000 directory, the same PermissionError a
        # seatbelt produces. Restored in cleanup or the temporary directory cannot be removed.
        self.closed = self.home / 'closed'
        self.closed.mkdir()
        self.probe = self.closed / 'wall-probe.txt'
        self.probe.write_text('the file the wall must refuse\n')
        self.closed.chmod(0o000)
        self.addCleanup(self.reopen)
        self.readable = self.home / 'readable-probe.txt'
        self.readable.write_text('a probe nothing refuses\n')

    def reopen(self):
        if self.closed.exists():
            self.closed.chmod(0o755)

    def record(self, writable=False, sandbox=None):
        """The executor rollout the helpers locate, optionally carrying a sandbox type."""
        rows = [dict(row) for row in self.rows]
        if sandbox:
            for row in rows:
                if row.get('type') == 'turn_context':
                    payload = dict(row['payload'])
                    policy = dict(payload.get('sandbox_policy') or {})
                    policy['type'] = sandbox
                    payload['sandbox_policy'] = policy
                    row['payload'] = payload
        path = self.home / 'sessions/2026/09/20' / ('rollout-executor-' + self.thread + '.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        path.chmod(0o644 if writable else 0o444)
        return path

    def env(self, marker=None, probe=None):
        environment = dict(os.environ, CODEX_HOME=str(self.home / 'child'),
                           CODEX_THREAD_ID=self.thread, PYTHONDONTWRITEBYTECODE='1')
        for key in ['RECHECK_ADAPTER_TEST', 'RECHECK_ADAPTER_RECORD',
                    'RECHECK_HARNESS_SANDBOX', 'RECHECK_WALL_PROBE']:
            environment.pop(key, None)
        if marker is not None:
            environment['RECHECK_HARNESS_SANDBOX'] = marker
        if probe is not None:
            environment['RECHECK_WALL_PROBE'] = str(probe)
        return environment

    def call(self, helper, marker=None, probe=None):
        return subprocess.run(
            [sys.executable, str(self.helpers / helper), '--workspace', self.meta['cwd']],
            cwd=self.home, env=self.env(marker, probe), capture_output=True, text=True)

    def both(self, marker=None, probe=None):
        return [(helper, self.call(helper, marker, probe))
                for helper in ['turns.py', 'invocation.py']]


class TheWitnessGatesTheWritableRolloutTest(WalledRolloutCase):

    def test_a_writable_rollout_with_no_marker_is_refused_with_todays_message(self):
        path = self.record(writable=True)
        before = path.read_bytes()
        for helper, got in self.both():
            self.assertEqual(got.returncode, 3, helper + ': ' + got.stderr)
            self.assertIn('writable executor rollout refused: ' + str(path), got.stderr)
            self.assertIn('(E9-37)', got.stderr)
        self.assertEqual(path.read_bytes(), before)

    def test_the_marker_with_a_probe_that_READS_is_refused(self):
        """A launcher's word is not a witness. The message is E9-37's, unchanged."""
        path = self.record(writable=True)
        for helper, got in self.both(marker=turns.WALL_MARKER, probe=self.readable):
            self.assertEqual(got.returncode, 3, helper + ': ' + got.stderr)
            self.assertIn('writable executor rollout refused: ' + str(path), got.stderr)

    def test_the_marker_with_no_probe_named_at_all_is_refused(self):
        path = self.record(writable=True)
        for helper, got in self.both(marker=turns.WALL_MARKER):
            self.assertEqual(got.returncode, 3, helper + ': ' + got.stderr)
            self.assertIn('writable executor rollout refused: ' + str(path), got.stderr)

    def test_a_refused_probe_with_NO_marker_is_refused(self):
        """E9-26(a) stands: the declaration is half the witness, not an optional half."""
        path = self.record(writable=True)
        for helper, got in self.both(probe=self.probe):
            self.assertEqual(got.returncode, 3, helper + ': ' + got.stderr)
            self.assertIn('writable executor rollout refused: ' + str(path), got.stderr)

    def test_a_wrong_marker_value_is_refused(self):
        self.record(writable=True)
        for helper, got in self.both(marker='seatbelt', probe=self.probe):
            self.assertEqual(got.returncode, 3, helper + ': ' + got.stderr)
            self.assertIn('(E9-37)', got.stderr)

    def test_the_marker_with_a_REFUSED_probe_accepts_the_writable_rollout(self):
        path = self.record(writable=True)
        before = path.read_bytes()
        for helper, got in self.both(marker=turns.WALL_MARKER, probe=self.probe):
            self.assertEqual(got.returncode, 0, helper + ': ' + got.stderr)
            document = json.loads(got.stdout)
            mapping = document if helper == 'turns.py' else document['turn_attribution']
            self.assertEqual(mapping, turns.attribution(self.rows))
        self.assertEqual(path.read_bytes(), before, 'the check must not write the rollout')

    def test_a_probe_that_is_simply_absent_is_not_a_refusal(self):
        """Fail closed: FileNotFoundError is not PermissionError."""
        self.record(writable=True)
        for helper, got in self.both(marker=turns.WALL_MARKER,
                                     probe=self.home / 'no-such-probe.txt'):
            self.assertEqual(got.returncode, 3, helper + ': ' + got.stderr)
            self.assertIn('(E9-37)', got.stderr)


class TheUnwritableRolloutIsUnchangedTest(WalledRolloutCase):

    def test_an_unwritable_rollout_is_accepted_with_no_witness_at_all(self):
        self.record()
        for helper, got in self.both():
            self.assertEqual(got.returncode, 0, helper + ': ' + got.stderr)

    def test_an_unwritable_rollout_is_accepted_with_the_witness_too(self):
        self.record()
        for helper, got in self.both(marker=turns.WALL_MARKER, probe=self.probe):
            self.assertEqual(got.returncode, 0, helper + ': ' + got.stderr)

    def test_an_unwritable_rollout_declares_no_wall_in_the_sandbox_string(self):
        """The declaration belongs to the ACCEPTED-WRITABLE case only."""
        self.record()
        got = self.call('invocation.py')
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertNotIn('sandbox-exec', json.loads(got.stdout)['harness']['sandbox'])


class TheAcceptedCaseIsDeclaredInTheRecordTest(WalledRolloutCase):

    def sandbox_string(self, **witness):
        got = self.call('invocation.py', **witness)
        self.assertEqual(got.returncode, 0, got.stderr)
        return json.loads(got.stdout)['harness']['sandbox']

    def test_the_sandbox_string_says_the_wall_is_the_sandbox(self):
        self.record(writable=True, sandbox='danger-full-access')
        said = self.sandbox_string(marker=turns.WALL_MARKER, probe=self.probe)
        self.assertIn('danger-full-access', said)
        self.assertIn(turns.WALL_MARKER, said)

    def test_the_sandbox_string_says_the_executor_rollout_is_writable_under_it(self):
        self.record(writable=True, sandbox='danger-full-access')
        said = self.sandbox_string(marker=turns.WALL_MARKER, probe=self.probe)
        self.assertIn('writable', said)
        self.assertIn('rollout', said)

    def test_the_declaration_names_SB_2(self):
        self.record(writable=True, sandbox='danger-full-access')
        self.assertIn('SB-2', self.sandbox_string(marker=turns.WALL_MARKER, probe=self.probe))


class DangerFullAccessIsNotRefusedAsAValueTest(WalledRolloutCase):
    """Behind the wall `sandbox_policy.type` reads `danger-full-access`. Nothing may refuse
    that VALUE when the witness holds, and the E9-37 gate must still refuse without it."""

    def test_it_is_carried_through_when_the_witness_holds(self):
        self.record(writable=True, sandbox='danger-full-access')
        got = self.call('invocation.py', marker=turns.WALL_MARKER, probe=self.probe)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertTrue(json.loads(got.stdout)['harness']['sandbox']
                        .startswith('danger-full-access'))

    def test_it_is_carried_through_on_an_unwritable_rollout_with_no_witness(self):
        self.record(sandbox='danger-full-access')
        got = self.call('invocation.py')
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(json.loads(got.stdout)['harness']['sandbox'], 'danger-full-access')

    def test_a_writable_rollout_carrying_it_is_still_refused_without_the_witness(self):
        path = self.record(writable=True, sandbox='danger-full-access')
        for helper, got in self.both():
            self.assertEqual(got.returncode, 3, helper + ': ' + got.stderr)
            self.assertIn('writable executor rollout refused: ' + str(path), got.stderr)

    def test_the_verifier_still_refuses_a_walled_launch_with_a_readable_probe(self):
        """The other half of SB-2, unchanged: `verifier.py` shares this witness code."""
        self.assertIs(verifier.wall_refuses, turns.wall_refuses)
        self.assertEqual(verifier.WALL_MARKER, turns.WALL_MARKER)
        self.assertEqual(turns.wall_refuses(str(self.readable))[0], False)
        self.assertEqual(turns.wall_refuses(str(self.probe))[0], True)
        self.assertEqual(turns.wall_refuses(None)[0], False)


class TheWitnessHelperItselfTest(WalledRolloutCase):

    def test_the_witness_needs_both_halves(self):
        os.environ.pop('RECHECK_HARNESS_SANDBOX', None)
        os.environ.pop('RECHECK_WALL_PROBE', None)
        self.assertIs(turns.wall_witness()[0], False)
        try:
            os.environ['RECHECK_HARNESS_SANDBOX'] = turns.WALL_MARKER
            self.assertIs(turns.wall_witness()[0], False)
            os.environ['RECHECK_WALL_PROBE'] = str(self.readable)
            self.assertIs(turns.wall_witness()[0], False)
            os.environ['RECHECK_WALL_PROBE'] = str(self.probe)
            held, why = turns.wall_witness()
            self.assertIs(held, True)
            self.assertIn('refused', why)
        finally:
            os.environ.pop('RECHECK_HARNESS_SANDBOX', None)
            os.environ.pop('RECHECK_WALL_PROBE', None)


if __name__ == '__main__':
    unittest.main()
