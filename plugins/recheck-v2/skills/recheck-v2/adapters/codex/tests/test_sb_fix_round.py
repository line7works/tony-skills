"""SB-12, N4: the wall witness tests the process's APPLIED sandbox, not a file's mode.

Her probe made an ordinary file, chmod 000, named it `RECHECK_WALL_PROBE` and declared
`RECHECK_HARNESS_SANDBOX=sandbox-exec` in a process with no bench wall at all. The witness
accepted it, and on that acceptance the verifier may select `codex exec -s
danger-full-access`. A file's permission bits are not a confinement.

The witness now asks the operating system whether a sandbox policy is APPLIED to this
process: `sandbox_check(getpid(), NULL, 0)` out of libsystem through ctypes. Measured on this
Mac (macOS 26.6.2, 2026-09-19): 0 in a plain process, 1 inside `/usr/bin/sandbox-exec -f`
with a tiny profile. Both measurements are made again by the tests below, with no model.

Standard library only. Nothing here launches Codex: the verifier's own gate is exercised
through its canned-record path.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import turns                                                        # noqa: E402

SANDBOX_EXEC = "/usr/bin/sandbox-exec"


class AppliedSandbox(unittest.TestCase):
    """The measurement itself, on this Mac, both ways."""

    def test_a_plain_process_reports_no_applied_sandbox(self):
        applied, why = turns.applied_sandbox()
        self.assertIs(applied, False, why)
        self.assertIn("sandbox_check", why)

    @unittest.skipUnless(os.path.isfile(SANDBOX_EXEC), "this machine has no sandbox-exec")
    def test_a_sandbox_exec_child_reports_an_applied_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "tiny.sb"
            profile.write_text('(version 1)\n(allow default)\n'
                               '(deny file-read* (subpath "%s"))\n' % (Path(tmp) / "closed"))
            source = ("import json,sys;sys.path.insert(0,%r);import turns;"
                      "print(json.dumps(turns.applied_sandbox()))" % str(ROOT))
            got = subprocess.run([SANDBOX_EXEC, "-f", str(profile), sys.executable,
                                  "-c", source],
                                 capture_output=True, text=True, cwd=tmp,
                                 env={"PATH": "/usr/bin:/bin",
                                      "PYTHONDONTWRITEBYTECODE": "1"})
            self.assertEqual(got.returncode, 0, got.stderr)
            applied, why = json.loads(got.stdout)
            self.assertIs(applied, True, why)


class TheWitness(unittest.TestCase):
    """Her four probe cases, and the witness they feed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.readable = self.dir / "readable"
        self.readable.write_text("ordinary")
        self.missing = self.dir / "missing"
        self.denied = self.dir / "mode-zero"
        self.denied.write_text("ordinary")
        self.denied.chmod(0)
        self.addCleanup(self.denied.chmod, 0o600)

    # ---- her four cases ------------------------------------------------------------------

    def test_a_readable_probe_is_not_a_refusal(self):
        self.assertIs(turns.wall_refuses(str(self.readable))[0], False)

    def test_an_absent_probe_is_not_a_refusal(self):
        self.assertIs(turns.wall_refuses(str(self.missing))[0], False)

    def test_a_mode_000_file_is_a_refusal_but_NOT_a_witness(self):
        """`wall_refuses` answers "was this read refused", honestly: it was.

        What it cannot answer is WHO refused it, and that is the whole of N4. The witness
        asks the OS instead, and in this process - which has no bench wall - it says no.
        """
        self.assertIs(turns.wall_refuses(str(self.denied))[0], True)
        with mock.patch.dict(os.environ,
                             {"RECHECK_HARNESS_SANDBOX": turns.WALL_MARKER,
                              "RECHECK_WALL_PROBE": str(self.denied)}):
            accepted, why = turns.wall_witness()
        self.assertIs(accepted, False, why)
        self.assertIn("sandbox", why.lower())

    def test_a_declared_wall_without_an_applied_policy_is_refused(self):
        with mock.patch.dict(os.environ,
                             {"RECHECK_HARNESS_SANDBOX": turns.WALL_MARKER,
                              "RECHECK_WALL_PROBE": str(self.denied)}):
            self.assertIs(turns.wall_witness()[0], False)

    # ---- the three halves --------------------------------------------------------------

    def test_the_marker_is_still_required(self):
        with mock.patch.dict(os.environ, {"RECHECK_HARNESS_SANDBOX": "something-else",
                                          "RECHECK_WALL_PROBE": str(self.denied)}):
            accepted, why = turns.wall_witness()
        self.assertIs(accepted, False)
        self.assertIn(turns.WALL_MARKER, why)

    def test_all_three_halves_together_are_the_witness(self):
        with mock.patch.dict(os.environ,
                             {"RECHECK_HARNESS_SANDBOX": turns.WALL_MARKER,
                              "RECHECK_WALL_PROBE": str(self.denied)}), \
                mock.patch.object(turns, "applied_sandbox",
                                  return_value=(True, "a seatbelt is applied")):
            accepted, why = turns.wall_witness()
        self.assertIs(accepted, True, why)
        self.assertIn("applied", why)

    def test_a_sandboxed_process_whose_probe_reads_is_still_no_witness(self):
        with mock.patch.dict(os.environ,
                             {"RECHECK_HARNESS_SANDBOX": turns.WALL_MARKER,
                              "RECHECK_WALL_PROBE": str(self.readable)}), \
                mock.patch.object(turns, "applied_sandbox",
                                  return_value=(True, "a seatbelt is applied")):
            self.assertIs(turns.wall_witness()[0], False)

    def test_an_unavailable_ctypes_or_symbol_FAILS_the_witness(self):
        """"If ctypes or the symbol is unavailable the witness FAILS" (SB-12, item 4)."""
        with mock.patch.dict(os.environ,
                             {"RECHECK_HARNESS_SANDBOX": turns.WALL_MARKER,
                              "RECHECK_WALL_PROBE": str(self.denied)}), \
                mock.patch.object(turns, "applied_sandbox",
                                  return_value=(None, "sandbox_check is unavailable here")):
            accepted, why = turns.wall_witness()
        self.assertIs(accepted, False, why)
        self.assertIn("unavailable", why)


class TheVerifiersOwnGate(unittest.TestCase):
    """`verifier.py` refuses to launch on a declaration the OS does not back.

    The gate is called DIRECTLY, never through a child: a test that has to start `codex
    exec` to find out whether the launch gate holds has already defeated its own point, and
    this round runs no live model at all.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.denied = Path(self.tmp.name) / "mode-zero"
        self.denied.write_text("ordinary")
        self.denied.chmod(0)
        self.addCleanup(self.denied.chmod, 0o600)
        import verifier
        self.verifier = verifier

    def test_a_mode_000_probe_no_longer_lets_the_verifier_launch(self):
        with mock.patch.dict(os.environ,
                             {"RECHECK_HARNESS_SANDBOX": turns.WALL_MARKER,
                              "RECHECK_WALL_PROBE": str(self.denied)}):
            os.environ.pop("CODEX_SANDBOX", None)
            with self.assertRaises(turns.Missing) as caught:
                self.verifier.confinement_gate()
        self.assertIn("nothing launched", str(caught.exception))

    def test_no_declaration_at_all_is_still_refused(self):
        with mock.patch.dict(os.environ, {"RECHECK_WALL_PROBE": str(self.denied)}):
            os.environ.pop("CODEX_SANDBOX", None)
            os.environ.pop("RECHECK_HARNESS_SANDBOX", None)
            with self.assertRaises(turns.Missing) as caught:
                self.verifier.confinement_gate()
        self.assertIn("nothing launched", str(caught.exception))

    def test_a_walled_and_applied_process_passes_the_gate(self):
        with mock.patch.dict(os.environ,
                             {"RECHECK_HARNESS_SANDBOX": turns.WALL_MARKER,
                              "RECHECK_WALL_PROBE": str(self.denied)}), \
                mock.patch.object(turns, "applied_sandbox",
                                  return_value=(True, "a seatbelt is applied")):
            os.environ.pop("CODEX_SANDBOX", None)
            self.assertIn("applied", self.verifier.confinement_gate())

    def test_the_legacy_codex_seatbelt_branch_is_unchanged(self):
        """Carried, not changed (SB-12 item 4): it could not be measured without Codex."""
        with mock.patch.dict(os.environ, {"CODEX_SANDBOX": "seatbelt"}):
            self.assertIn("E9-26(a)", self.verifier.confinement_gate())


if __name__ == "__main__":                                          # pragma: no cover
    unittest.main()
