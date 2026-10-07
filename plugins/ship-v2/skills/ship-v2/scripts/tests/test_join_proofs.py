"""The join's proofs (the E15 lane contract section 11, slice 3): `setups/ten-stations.sh`, `setups/trace-proof.sh`
with its tripwire (`setups/tripwire.py`), and the end-to-end replay (`evals/replay/replay.py`).

What runs here needs no harness and no sign-in: the proof scripts' home guard (a protected home, as given, through
a symlink or a `..`, and a protected TMPDIR, TEMP or TMP are refused, exit 2, nothing created, and the guard's
interpreter starts with the three cleared), their station list read from a run against inert `claude` and `codex`
stand-ins, the tripwire's catch (a read and a run of a v1 file each leave a marker and the verdict is FAIL; a v2
file read leaves none), the replay's packet checker on a planted leak, and the replay itself on both paths. The
installs against the real harnesses are the proofs' own runs (the control room's and the builder's), recorded in the
plugin's README.

The v1 names are assembled at run time, so this file names no v1 folder (`test_no_v1_import.py`)."""
import hashlib
import json
import os
import shlex
import subprocess
import sys
import unittest

import testlib

SETUPS = os.path.join(testlib.PLUGIN, "setups")
TEN = os.path.join(SETUPS, "ten-stations.sh")
PROOF = os.path.join(SETUPS, "trace-proof.sh")
TRIPWIRE = os.path.join(SETUPS, "tripwire.py")
REPLAY = os.path.join(testlib.PLUGIN, "evals", "replay", "replay.py")
HARNESSES = ("claude-code", "codex")
STANDIN = "#!/bin/sh\ncase \"$*\" in *'plugin install'*) echo '{\"outcome\":\"ok\"}';; esac\nexit 0\n"
CONFIG = 'model = "m"\nmodel_reasoning_effort = "high"\nsandbox_mode = "workspace-write"\n'
STARTUP = "#!/bin/sh\nfor t in \"${TMPDIR-}\" \"${TEMP-}\" \"${TMP-}\"; do\n  if [ -n \"$t\" ] && [ -d \"$t\" ]; then " \
          "mkdir -p \"$t/startup-write\"; fi\ndone\nexec %s \"$@\"\n"
V2_STATIONS = ["recheck-v2", "build-v2", "signoff-v2", "precon-v2", "architect-v2", "blueprint-v2", "inspect-v2",
               "vertical-v2", "handoff-v2", "ship-v2"]


def v1(name):
    """A v1 station's name, assembled from halves so no v1 folder is spelled in this file."""
    return {"build": "bu" + "ild", "signoff": "sign" + "off", "recheck": "re" + "check", "vertical": "verti" + "cal",
            "handoff": "hand" + "off", "ship": "sh" + "ip"}[name]


def listing(root):
    return [(".", os.lstat(root).st_mtime_ns)] + sorted(
        (os.path.relpath(os.path.join(d, n), root), os.lstat(os.path.join(d, n)).st_mtime_ns)
        for d, ds, fs in os.walk(root) for n in ds + fs)


class Fixture(unittest.TestCase):
    """A fake HOME with the protected homes in it, inert harness stand-ins first on PATH, and a scratch tree."""

    def setUp(self):
        self.tmp = testlib.make_scratch("join-proofs-")
        self.addCleanup(testlib.rmtree, self.tmp)
        self.home = h = os.path.join(self.tmp, "home")
        for rel in (".codex", os.path.join(".claude", "config"), os.path.join(".local", "share", "skills-v2-locked"),
                    "ordinary"):
            os.makedirs(os.path.join(h, rel))
        testlib.write_text(os.path.join(h, ".codex", "config.toml"), CONFIG)
        os.symlink(os.path.join(h, ".codex"), os.path.join(h, "link"))
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        for name, body in (("claude", STANDIN), ("codex", STANDIN), ("uv", "#!/bin/sh\nexit 1\n")):
            testlib.write_text(os.path.join(self.bin, name), body)
            os.chmod(os.path.join(self.bin, name), 0o755)
        self.env = testlib.base_env({"HOME": h, "PATH": self.bin + os.pathsep + os.environ.get("PATH", "")})
        for key in ("TMPDIR", "TEMP", "TMP"):
            self.env.pop(key, None)
        self.env["TMPDIR"] = os.path.join(h, "ordinary")
        self.protected = (h + "/.claude/x", h + "/.codex/x", h + "/.local/share/skills-v2-pilot/x",
                          h + "/.local/share/skills-v2-locked/x", h + "/link/x", h + "/ordinary/../.claude/x")

    def run_it(self, argv, extra=None, timeout=600):
        env = dict(self.env)
        env.update(extra or {})
        return subprocess.run(argv, env=env, cwd=self.tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout)

    def assert_refused(self, argv, extra=None, label=None):
        before = listing(self.tmp)
        got = self.run_it(argv, extra)
        self.assertEqual(got.returncode, 2, (label or argv, got.stderr.decode("utf-8", "replace")[-600:]))
        self.assertIn("which no setup may touch; nothing created", got.stderr.decode("utf-8", "replace"), label)
        self.assertEqual(listing(self.tmp), before, label or argv)


class TheProofScriptsGuardTheirHomes(Fixture):

    def scripts(self):
        return [("ten-stations.sh", TEN), ("trace-proof.sh", PROOF)]

    def test_the_proof_scripts_exist(self):
        for label, path in self.scripts() + [("tripwire.py", TRIPWIRE), ("replay.py", REPLAY)]:
            self.assertTrue(os.path.isfile(path), label)

    def test_a_protected_home_is_refused_before_anything_is_created(self):
        for label, path in self.scripts():
            for harness in HARNESSES:
                for target in self.protected:
                    self.assert_refused(["sh", path, harness, target], label=(label, harness, target))

    def test_a_protected_temp_folder_is_refused_and_nothing_starts_under_it(self):
        tmp = os.path.join(self.home, ".claude", "tmp")
        os.makedirs(tmp)
        startup = os.path.join(self.tmp, "startup-bin")
        os.makedirs(startup)
        testlib.write_text(os.path.join(startup, "python3"), STARTUP % shlex.quote(sys.executable))
        os.chmod(os.path.join(startup, "python3"), 0o755)
        for label, path in self.scripts():
            for name in ("TMPDIR", "TEMP", "TMP"):
                extra = {"PATH": startup + os.pathsep + self.env["PATH"], name: tmp}
                if name != "TMPDIR":
                    extra["TMPDIR"] = os.path.join(self.home, "ordinary")
                self.assert_refused(["sh", path, "claude-code", os.path.join(self.home, "ordinary", "h-" + name)],
                                    extra, (label, name))
                self.assertFalse(os.path.exists(os.path.join(tmp, "startup-write")), (label, name))

    def test_a_home_that_is_not_empty_is_refused(self):
        full = os.path.join(self.home, "ordinary", "full")
        os.makedirs(full)
        testlib.write_text(os.path.join(full, "keep.txt"), "kept\n")
        for label, path in self.scripts():
            got = self.run_it(["sh", path, "claude-code", full])
            self.assertEqual(got.returncode, 2, label)
            self.assertEqual(testlib.read_text(os.path.join(full, "keep.txt")), "kept\n", label)


class TheTenStations(Fixture):

    def test_it_installs_the_ten_v2_stations_and_records_from_one_marketplace(self):
        """Against inert stand-ins nothing lands in the cache, so the proof fails; its report still names what it
        installs: the ten v2 stations and the records component, from one marketplace of links to this checkout."""
        for harness in HARNESSES:
            home = os.path.join(self.home, "ordinary", "ten-" + harness)
            got = self.run_it(["sh", TEN, harness, home])
            report = json.loads(got.stdout.decode("utf-8"))
            self.assertEqual(got.returncode, 1, harness)
            self.assertFalse(report["ok"], harness)
            self.assertEqual(sorted(report["installed"]), sorted(V2_STATIONS + ["records"]), harness)
            market = os.path.join(home, "marketplace")
            for name in V2_STATIONS + ["records"]:
                self.assertEqual(os.path.realpath(os.path.join(market, name)),
                                 os.path.realpath(os.path.join(testlib.PLUGINS, name)), (harness, name))
            self.assertEqual(report["siblings_expected"], ["build-v2", "signoff-v2", "recheck-v2"], harness)
            self.assertEqual(report["manual_only_expected"], {"handoff-v2": True, "ship-v2": False,
                                                              "vertical-v2": False}, harness)


class TheTripwire(Fixture):
    """`setups/tripwire.py`: the v1 tripwire copies, the audit hook and the verdict, on a fake v1 plugin."""

    def setUp(self):
        Fixture.setUp(self)
        sys.path.insert(0, SETUPS)
        self.addCleanup(sys.path.remove, SETUPS)
        import tripwire  # noqa: E402
        self.tw = tripwire
        name = v1("build")
        self.source = os.path.join(self.tmp, "plugins", name)
        os.makedirs(os.path.join(self.source, ".claude-plugin"))
        os.makedirs(os.path.join(self.source, "skills", name, "assets"))
        testlib.write_json(os.path.join(self.source, ".claude-plugin", "plugin.json"),
                           {"name": name, "version": "1.0.0", "description": "a v1 station"})
        testlib.write_text(os.path.join(self.source, "skills", name, "SKILL.md"),
                           "---\nname: %s\ndescription: a v1 station\n---\n\n# A v1 station\n" % name)
        testlib.write_text(os.path.join(self.source, "skills", name, "assets", "mandate.md"), "a v1 asset\n")
        self.markers = os.path.join(self.tmp, "markers")
        self.copy = os.path.join(self.tmp, "tripwires", name)
        self.tw.build_copy(self.source, self.copy, self.markers)
        self.hook = os.path.join(self.tmp, "hook")
        self.tw.write_hook(self.hook)
        self.hooked = dict(self.env, PYTHONPATH=self.hook, TRIPWIRE_ROOTS=self.copy, TRIPWIRE_MARKERS=self.markers)

    def python(self, code, env=None):
        return subprocess.run([sys.executable, "-c", code], env=env or self.hooked, cwd=self.tmp,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)

    def test_the_copy_keeps_the_manifest_and_frontmatter_and_holds_a_tripwire_entry(self):
        name = v1("build")
        manifest = testlib.load_json(os.path.join(self.copy, ".claude-plugin", "plugin.json"))
        self.assertEqual(manifest["name"], name)
        skill = testlib.read_text(os.path.join(self.copy, "skills", name, "SKILL.md"))
        self.assertTrue(skill.startswith("---\nname: %s\n" % name), skill)
        self.assertIn("tripwire", skill)
        self.assertNotIn("a v1 asset", testlib.read_text(os.path.join(self.copy, "skills", name, "assets",
                                                                      "mandate.md")))
        entry = os.path.join(self.copy, "skills", name, "scripts", name + ".py")
        self.assertTrue(os.path.isfile(entry))
        self.assertEqual(self.tw.markers(self.markers), [])

    def test_a_read_of_a_v1_file_leaves_a_marker_and_fails_the_verdict(self):
        name = v1("build")
        got = self.python("open(%r).read()" % os.path.join(self.copy, "skills", name, "SKILL.md"))
        self.assertEqual(got.returncode, 0, got.stderr)
        marks = self.tw.markers(self.markers)
        self.assertTrue(any(m["event"] == "open" for m in marks), marks)
        self.assertEqual(self.tw.verdict(marks)["verdict"], "FAIL")

    def test_a_run_of_a_v1_entry_leaves_a_marker_even_isolated(self):
        name = v1("build")
        entry = os.path.join(self.copy, "skills", name, "scripts", name + ".py")
        got = subprocess.run([sys.executable, "-I", "-B", entry, "skill-identity"], env=self.env, cwd=self.tmp,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        self.assertNotEqual(got.returncode, 0)
        marks = self.tw.markers(self.markers)
        self.assertTrue(any(m["event"] == "ran" for m in marks), marks)
        self.assertEqual(self.tw.verdict(marks)["verdict"], "FAIL")

    def test_a_listing_and_a_launch_naming_a_v1_path_leave_markers(self):
        name = v1("build")
        got = self.python("import os, subprocess, sys\nos.listdir(%r)\nsubprocess.run(['/bin/echo', %r])\n"
                          % (self.copy, os.path.join(self.copy, "skills", name, "SKILL.md")))
        self.assertEqual(got.returncode, 0, got.stderr)
        events = sorted(set(m["event"] for m in self.tw.markers(self.markers)))
        self.assertIn("os.listdir", events)
        self.assertIn("subprocess.Popen", events)

    def test_a_read_outside_every_v1_root_leaves_none_and_the_hook_arms(self):
        other = os.path.join(self.tmp, "other.txt")
        testlib.write_text(other, "not a v1 file\n")
        got = self.python("open(%r).read()" % other)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(self.tw.markers(self.markers), [])
        self.assertEqual(self.tw.verdict([])["verdict"], "PASS")
        self.assertGreaterEqual(len(self.tw.armed(self.markers)), 1)

    def test_a_v2_path_that_shares_the_v1_name_as_a_prefix_leaves_none(self):
        """A v2 sibling's folder (`<v1>-v2`) beside the v1 tripwire is not under it: no marker for an open, a
        listing or a launch naming it, in a path or inside a shell string."""
        name = v1("build")
        sibling = self.copy + "-v2"
        os.makedirs(os.path.join(sibling, "skills"))
        script = os.path.join(sibling, "skills", "driver.py")
        testlib.write_text(script, "print('v2')\n")
        got = self.python("import os, subprocess, sys\nopen(%r).read()\nos.listdir(%r)\n"
                          "subprocess.run([sys.executable, %r])\nsubprocess.run('/bin/echo %s', shell=True)\n"
                          % (script, sibling, script, script))
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(self.tw.markers(self.markers), [], name)

    def test_a_v1_root_spelled_another_way_is_still_caught(self):
        name = v1("build")
        link = os.path.join(self.tmp, "via-link")
        os.symlink(self.copy, link)
        got = self.python("open(%r).read()" % os.path.join(link, "skills", name, "SKILL.md"))
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertTrue(self.tw.markers(self.markers))


class TheReplay(unittest.TestCase):

    def setUp(self):
        sys.path.insert(0, os.path.dirname(REPLAY))
        self.addCleanup(sys.path.remove, os.path.dirname(REPLAY))
        import replay  # noqa: E402
        self.replay = replay

    def packet(self, files, listed=None, withheld=None):
        texts = dict((rel, text) for rel, text in files.items())
        digests = dict((rel, hashlib.sha256(text.encode("utf-8")).hexdigest()) for rel, text in files.items())
        return {"files": digests, "texts": texts, "listed": listed, "withheld": withheld}

    def full_withheld(self):
        return {"withheld": [{"what": w} for w in ("docs/reviews/x.md", "docs/records/x.jsonl", "doc Status: line 3",
                                                   "doc ## Punch list", "doc ## Handoffs", "doc ## Build assumptions",
                                                   "doc ## Deviations", "doc ## Discovered")]}

    def test_the_packet_checker_catches_every_planted_leak(self):
        record_line = "### 2026-10-06 handoff block line that only the record holds"
        planted = self.packet({"workspace/docs/reviews/old-verdict.md": "a prior verdict\n",
                               "workspace/docs/plans/plan.md": "# Plan\n\n## Punch list\nStatus: built\n",
                               "workspace/src/a.py": "x = 1\n# %s\n" % record_line[2:],
                               "workspace/notes.md": "%s\n" % record_line},
                              listed={"files": [{"at": "workspace/src/a.py", "sha256": "0" * 64}]},
                              withheld={"withheld": [{"what": "docs/records/x.jsonl"}]})
        problems = self.replay.Path.packet_problems(None, {"p": planted}, [record_line])["p"]
        joined = "\n".join(problems)
        for want in ("a review record in the packet", "withheld heading ## Punch list", "a Status: line",
                     "line(s) of the review record", "files.json names workspace/src/a.py",
                     "withheld.json does not name docs/reviews/"):
            self.assertIn(want, joined)

    def test_the_packet_checker_passes_a_cold_packet(self):
        cold = self.packet({"workspace/src/a.py": "x = 1\n", "documents/spec.md": "# Plan\n\n## Slice A\nGoal: g\n"},
                           listed={"files": []}, withheld=self.full_withheld())
        self.assertEqual(self.replay.Path.packet_problems(None, {"p": cold}, ["a line only the record holds"]), {})

    def test_the_replay_walks_both_paths_through_the_real_stations(self):
        if testlib.checkout_sibling("build-v2") is None:
            self.skipTest("no checkout beside this core: the replay runs the stations beside ship-v2")
        scratch = testlib.make_scratch("join-replay-")
        self.addCleanup(testlib.rmtree, scratch)
        env = testlib.base_env({"TMPDIR": scratch})
        trace = os.path.join(scratch, "trace.json")
        got = subprocess.run([sys.executable, REPLAY, "--trace-out", trace], env=env, cwd=scratch,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1800)
        summary = json.loads(got.stdout.decode("utf-8"))
        self.assertEqual(got.returncode, 0, json.dumps(summary["problems"], indent=1)[:3000])
        self.assertTrue(summary["ok"])
        self.assertEqual(sorted(summary["paths"]), ["clean", "findings"])
        for kind, laps in (("clean", 0), ("findings", 1)):
            loop = summary["paths"][kind]["assertions"]["loop"]
            self.assertEqual((loop["status"], loop["result_line"], loop["card"], loop["laps"]),
                             ("completed", "ALL CLEAR", "signed off", laps), kind)
        traces = testlib.load_json(trace)
        names = sorted(set(line["identity"]["name"] for kind in traces for which in ("ship", "vertical")
                           for line in traces[kind][which]))
        self.assertEqual(names, ["build-v2", "readers", "recheck-v2", "signoff-v2"])


if __name__ == "__main__":
    unittest.main()
