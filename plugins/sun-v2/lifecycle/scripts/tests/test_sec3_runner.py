"""SEC-3: the child process. The one runner (`sun_core/runner.py`) against the fake provider's tool.

Frame lines answered: SEC-3's table (command, environment, refusals, files it makes, input and
output, lifetime) and its test line's runner half; the reviewer's D16 row for SEC-3 (an oversized
stream; secret-bearing environment values; process-group cleanup when the call ends, not only at the
time limit; the values of the environment, not only its names). The manifest-build half of the test
line (four templates that fail; a protected input that builds) is in `test_rows_build.py`.
"""
import base64
import json
import os
import signal
import time
import unittest
import urllib.parse

import harness
import rowlib
from sun_core import results, runner, screen

BASE = ["HOME", "LANG", "LC_ALL", "LOGNAME", "PATH", "TMPDIR", "USER"]


class RunnerBase(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.m = self.machine()
        self.run_dir = os.path.join(self.m.home, "rundir")
        os.makedirs(os.path.join(self.run_dir, "tmp"), mode=0o700)
        os.chmod(self.run_dir, 0o700)
        self.register = screen.Screen()
        self.world = self.m.world(env={"FAKEHOST_DEBUG": "1", "FAKEHOST_TOKEN": harness.canary("token"), "DEBUG": "*"})
        self.decl = {"tool": "fakehost", "time_limit": 20, "trace_flags": ["--debug", "--verbose", "--trace"]}

    def call(self, argv, env=None, decl="default", cwd=None):
        from sun_core import facts as factsmod
        search = factsmod.Facts(self.world.env).search_list(self.world.fs)        # the settings as they stand now
        context = runner.Context(self.register, self.run_dir, search)
        return runner.run(self.world, context, self.decl if decl == "default" else decl, argv, env or {}, cwd or self.m.home)

    def calls(self, tool="fakehost"):
        path = os.path.join(self.m.home, ".fakes", tool, "calls.jsonl")
        return [json.loads(line) for line in open(path)] if os.path.exists(path) else []


class RunnerCase(RunnerBase):
    def test_SEC3_environment_is_built_from_nothing_base_names_plus_registered(self):
        raw = self.call(["noop"], env={"FAKEHOST_REGION": "fixed-value"})
        self.assertEqual(raw.exit_code, 0)
        call = self.calls()[-1]
        self.assertEqual(call["env_names"], sorted(BASE + ["FAKEHOST_REGION"]))
        for absent in ("FAKEHOST_DEBUG", "FAKEHOST_TOKEN", "DEBUG"):
            self.assertNotIn(absent, call["env_names"])
        values = call["env_values"]
        self.assertEqual((values["LANG"], values["LC_ALL"]), (runner.LOCALE, runner.LOCALE))
        self.assertEqual(values["TMPDIR"], os.path.join(self.run_dir, "tmp"))
        self.assertEqual(values["HOME"], self.m.home)
        self.assertNotIn(self.world.env["FAKEHOST_TOKEN"], json.dumps(values), "a session secret reached a child's environment")

    def test_SEC3_refusals_before_the_start(self):
        secret = harness.canary("register")
        self.register.add("user:" + secret + "@host", [secret], None, "channel")
        with self.assertRaises(runner.Refused):
            self.call(["noop"], decl=None)
        with self.assertRaises(runner.Refused):
            self.call(["noop", "--trace"])
        forms = {"whole": "user:" + secret + "@host", "component": "x" + secret, "percent": urllib.parse.quote("user:" + secret + "@host", safe=""),
                 "base64": base64.b64encode(secret.encode()).decode()}
        for label, text in forms.items():
            with self.subTest(form=label, where="argument"):
                with self.assertRaises(runner.Refused):
                    self.call(["noop", "--name", text])
            with self.subTest(form=label, where="environment value"):
                with self.assertRaises(runner.Refused):
                    self.call(["noop"], env={"FAKEHOST_REGION": text})
        self.assertEqual(self.calls(), [], "a refused command was started")

    def test_SEC3_a_file_the_child_creates_is_owner_only_and_its_stdin_is_empty(self):
        target = os.path.join(self.m.home, "made-by-child.env")
        raw = self.call(["write", "--out", target])
        self.assertEqual(raw.exit_code, 0)
        self.assertEqual(os.stat(target).st_mode & 0o777, 0o600)

    def test_SEC3_a_fake_that_hangs_after_starting_a_child_is_ended_at_its_limit_with_that_child(self):
        plan = os.path.join(self.m.home, ".fakes", "fakehost", "plan.json")
        os.makedirs(os.path.dirname(plan))
        json.dump([{"command": "noop", "do": "hang", "child": True}], open(plan, "w"))
        self.decl["time_limit"] = 1
        started = time.time()
        raw = self.call(["noop"])
        self.assertLess(time.time() - started, 15)
        self.assertTrue(raw.timed_out)
        self.assertEqual(results.Parser({"exits": {"0": "success"}}, raw, self.register).finish().kind, "timeout")
        self.assert_children_gone()

    def assert_children_gone(self):
        path = os.path.join(self.m.home, ".fakes", "fakehost", "children.jsonl")
        deadline = time.time() + 5
        while not os.path.exists(path) and time.time() < deadline:
            time.sleep(0.05)
        children = [json.loads(line) for line in open(path)] if os.path.exists(path) else []
        for child in children:
            for _ in range(100):
                try:
                    os.kill(child["pid"], 0)
                except OSError:
                    break
                time.sleep(0.05)
            else:
                os.kill(child["pid"], signal.SIGKILL)
                self.fail("a descendant of the child outlived the call")
        return children

    def test_SEC3_D16_the_group_is_ended_when_the_call_ends_not_only_at_the_limit(self):
        plan = os.path.join(self.m.home, ".fakes", "fakehost", "plan.json")
        os.makedirs(os.path.dirname(plan))
        json.dump([{"command": "noop", "do": "child"}], open(plan, "w"))
        raw = self.call(["noop"])
        self.assertEqual((raw.exit_code, raw.timed_out), (0, False))
        time.sleep(0.3)
        self.assert_children_gone()

    def test_SEC3_D16_an_oversized_stream_is_discarded_and_the_result_is_malformed(self):
        plan = os.path.join(self.m.home, ".fakes", "fakehost", "plan.json")
        os.makedirs(os.path.dirname(plan))
        json.dump([{"command": "noop", "do": "big", "bytes": runner.MOST_OUTPUT + 4096}], open(plan, "w"))
        raw = self.call(["noop"])
        self.assertTrue(raw.oversize)
        self.assertEqual(raw.stdout, b"")
        self.assertEqual(results.Parser({"exits": {"0": "success"}}, raw, self.register).finish().kind, "malformed")

    def test_SEC3_the_record_shows_the_child_started_and_ended(self):
        mark = self.m.recorder.mark()
        self.call(["noop"])
        events = [(e["stage"], e["op"]) for e in self.m.recorder.since(mark) if e["op"] == "child"]
        self.assertEqual(events, [("pre", "child"), ("mid", "child"), ("post", "child")])


def program(folder, name, marker):
    """A program that leaves a marker when it is started, and answers as the fake host does."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\n: > %s\nexec %s \"$@\"\n" % (marker, os.path.join(harness.FAKES, "fakehost")))
    os.chmod(path, 0o755)
    return path


class AStartThatIsNoSummons(RunnerBase):
    """SEC-3's environment row (A53): "A child of a start that is no summons is given no `TMPDIR`: that start makes no
    run directory (SEC-12), and nothing of the session may stand in its place." The runner's half: a context with no
    run directory gives the child no `TMPDIR`, and the session's own `TMPDIR` does not stand in its place. The
    identity command's half of the test line waits on question 16 of report-4 (not written)."""

    def test_SEC3_A53_a_child_of_a_context_with_no_run_directory_is_given_no_TMPDIR_and_none_of_the_sessions(self):
        from sun_core import facts as factsmod
        self.world.env["TMPDIR"] = os.path.join(self.tmp, "the-sessions-own")
        search = factsmod.Facts(self.world.env).search_list(self.world.fs)
        raw = runner.run(self.world, runner.Context(self.register, None, search), self.decl, ["noop"], {}, self.m.home)
        self.assertEqual(raw.exit_code, 0)
        call = self.calls()[-1]
        self.assertEqual(call["env_names"], sorted(n for n in BASE if n != "TMPDIR"))
        self.assertNotIn(self.world.env["TMPDIR"], json.dumps(call["env_values"]))


class TheSearchList(RunnerBase):
    """SEC-3's command and environment rows and its test line, "The search list" and "The order"; RUN-5; RUN-7;
    the owner's rulings A46 and A48 (RK11); the order and the four fixed folders, decided on his behalf (A49)."""

    def setUp(self):
        RunnerBase.setUp(self)
        self.markers = os.path.join(self.m.root, "markers")
        os.makedirs(self.markers)

    def named(self, *folders):
        self.m.settings["program_folders"] = list(folders)
        self.m.write_settings()

    def started_paths(self, mark):
        return [e.get("path") for e in self.m.recorder.since(mark) if e["op"] == "child" and e["stage"] == "pre"]

    def test_SEC3_RUN5_a_decoy_first_on_the_sessions_path_is_never_started_and_the_named_folders_program_is_started_by_its_full_path(self):
        decoys = os.path.join(self.m.root, "decoys")
        program(decoys, "fakehost", os.path.join(self.markers, "decoy"))
        self.world.env["PATH"] = decoys + os.pathsep + harness.FAKES + os.pathsep + "/usr/bin:/bin"
        self.named(harness.FAKES)
        mark = self.m.recorder.mark()
        raw = self.call(["noop"])
        self.assertEqual(raw.exit_code, 0)
        self.assertEqual(os.listdir(self.markers), [], "the decoy on the session's path was started")
        self.assertEqual(self.started_paths(mark), [os.path.join(harness.FAKES, "fakehost")], "not started by its full path")
        values = self.calls()[-1]["env_values"]
        self.assertEqual(values["PATH"], os.pathsep.join(["/usr/bin", "/bin", "/usr/sbin", "/sbin", harness.FAKES]),
                         "the child's PATH is not the search list")
        self.assertNotIn(decoys, values["PATH"])
        self.assertEqual((values["HOME"], values["USER"], values["LOGNAME"]),
                         (self.world.env["HOME"], self.world.env["USER"], self.world.env["LOGNAME"]), "HOME, USER, LOGNAME not as the tool has them")

    def test_SEC3_RUN7_a_program_in_no_folder_of_the_search_list_is_not_found_and_nothing_is_started(self):
        decoys = os.path.join(self.m.root, "decoys")
        program(decoys, "fakehost", os.path.join(self.markers, "decoy"))
        self.world.env["PATH"] = decoys + os.pathsep + harness.FAKES
        self.named()
        with self.assertRaises(runner.Refused) as refused:
            self.call(["noop"])
        self.assertEqual((refused.exception.reason, refused.exception.program), ("tool not found", "fakehost"))
        self.assertEqual(self.calls(), [])
        self.assertEqual(os.listdir(self.markers), [])

    def test_SEC3_A49_a_system_folder_comes_before_his_folders_and_his_folders_in_the_order_he_writes_them(self):
        self.assertTrue(os.path.isfile("/usr/bin/true") and not os.path.exists("/bin/true"), "the fixture needs true in /usr/bin alone")
        mine = os.path.join(self.m.root, "mine")
        program(mine, "true", os.path.join(self.markers, "mine-true"))
        self.named(mine)
        mark = self.m.recorder.mark()
        raw = self.call([], decl={"tool": "true", "time_limit": 20})
        self.assertEqual(raw.exit_code, 0)
        self.assertEqual(self.started_paths(mark), ["/usr/bin/true"], "his folder's file was started before the system folder's")
        self.assertEqual(os.listdir(self.markers), [])
        first, second = os.path.join(self.m.root, "first"), os.path.join(self.m.root, "second")
        program(first, "sunv2ordered", os.path.join(self.markers, "first"))
        program(second, "sunv2ordered", os.path.join(self.markers, "second"))
        for order, want in (((first, second), "first"), ((second, first), "second")):
            with self.subTest(order=[os.path.basename(f) for f in order]):
                for name in os.listdir(self.markers):
                    os.remove(os.path.join(self.markers, name))
                self.named(*order)
                mark = self.m.recorder.mark()
                self.call(["noop"], decl={"tool": "sunv2ordered", "time_limit": 20})
                self.assertEqual(os.listdir(self.markers), [want], "not the folder written first was started")
                self.assertEqual(self.started_paths(mark), [os.path.join(order[0], "sunv2ordered")])


class TheRegisterOnEveryValue(RunnerBase):
    """SEC-3's refusals row: the check "is made on every argument and every environment value of the child as it
    would be started, the values of the base names and the path of the temporary folder among them". The reviewer's
    D8-C closing rule: "Apply register matching to every final child argument and environment value, including base
    names and TMPDIR, and test collisions in those fields before child creation." """

    def test_SEC3_D8C_an_entry_equal_to_the_users_name_or_part_of_the_temporary_folders_path_refuses_before_any_child(self):
        tmp_part = os.path.basename(self.run_dir)                   # in TMPDIR, and in no other value of the child
        self.assertNotIn(tmp_part, self.world.env["HOME"] + harness.FAKES)
        for label, entry in (("the user's name, a base name's value", self.world.env["USER"]),
                             ("a part of the temporary folder's path", tmp_part),
                             ("a part of a folder of the search list, in PATH's value", "fakes")):
            with self.subTest(entry=label):
                self.register = screen.Screen()
                self.register.add(entry, (), None, "channel")
                mark = self.m.recorder.mark()
                with self.assertRaises(runner.Refused) as refused:
                    self.call(["noop"])
                self.assertEqual(refused.exception.reason, "register entry")
                self.assertEqual([e for e in self.m.recorder.since(mark) if e["op"] == "child"], [], "a child was created")
        self.assertEqual(self.calls(), [], "a refused command was started")


class TheRefusalThroughARun(harness.Case):
    """SEC-3's test line: an entry equal to a base name's value (the user's name) and, in a second pass, a part of the
    temporary folder's path "each refuse the command before any child is created, the fake recording no start, and
    the run ends `stopped`; each of the two, met by the first command of a first look, ends that look `refused`, with
    no child created, no manifest and no journal written, no run open under the key and the entry in no output or
    form, and met in the look of a re-plan of a run that has its go ends that invocation `stopped`, with the manifest
    in force byte-equal". The register's entry comes in by the hosting token's channel (SEC-2), set to that value."""

    USER = "zzuserq9"
    PASSES = (("the user's name", lambda m: {"USER": TheRefusalThroughARun.USER, "FAKEHOST_TOKEN": TheRefusalThroughARun.USER}),
              ("a part of the temporary folder's path", lambda m: {"FAKEHOST_TOKEN": os.sep + "runs" + os.sep}))

    def machine_for(self, label, identity=True):
        m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
        providers = rowlib.providers()
        if not identity:
            providers["fakehost"]["identity"] = rowlib.NONE      # so that the operation's command is the first command
        rows = [rowlib.owner_step("O1", mode="on his word"),
                rowlib.says("Y1", needs=[{"output": "connected", "level": "state", "accepts": ["his word"], "treatment": "then not applicable"}])]
        rowlib.install(m, rowlib.lane("sunrise", rows), providers=providers)
        return m

    def entry_of(self, env):
        return env.get("FAKEHOST_TOKEN")

    def everything_written(self, m, result):
        """Both output streams and every form of every run (found by listing: a form's path in the output may
        itself give way to the fixed words where it holds the entry)."""
        text = result.text
        for run in m.run_ids():
            folder = os.path.join(m.facts.run_dir(run), "forms")
            for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
                with open(os.path.join(folder, name)) as fh:
                    text += fh.read()
        return text

    def test_SEC3_D8C_RUN12_an_operations_command_is_refused_and_the_run_ends_stopped(self):
        for label, env_of in self.PASSES:
            with self.subTest(entry=label):
                m = self.machine_for(label, identity=False)
                looked, went = m.started(inputs=m.inputs(description="a plain project"))
                self.assertEqual(went.ending, "waiting", went.text)
                calls = len(m.calls("fakehost"))
                env = env_of(m)
                position = m.summon("status").doc["position"]
                resumed = m.summon("resume", "demo", "--position", position, "--done", "O1", env=env)
                self.assertEqual(resumed.ending, "stopped", resumed.text)
                self.assertIn("the runner refused the command: register entry", self.everything_written(m, resumed))
                self.assertEqual(len(m.calls("fakehost")), calls, "a child was started")
                self.assertNotIn("Y1", m.statuses(looked.doc["run"]))
                self.assertNotIn(self.entry_of(env), self.everything_written(m, resumed))

    def test_SEC3_D8C_RUN7_met_by_the_first_command_of_a_first_look_the_look_ends_refused_and_leaves_nothing_open(self):
        for label, env_of in self.PASSES:
            with self.subTest(entry=label):
                m = self.machine_for(label)
                env = env_of(m)
                looked = m.look(inputs=m.inputs(description="a plain project"), env=env)
                self.assertEqual(looked.ending, "refused", looked.text)
                self.assertEqual(m.calls("fakehost"), [], "a child was created")
                self.assertEqual(m.open_runs(), {}, "a run is open under the key")
                for run in m.run_ids():
                    names = os.listdir(m.facts.run_dir(run))
                    self.assertNotIn("journal.jsonl", names)
                    self.assertEqual([n for n in names if n.startswith("manifest-")], [])
                self.assertNotIn(self.entry_of(env), self.everything_written(m, looked))

    def test_SEC3_D8C_RUN11_met_in_the_look_of_a_replan_the_invocation_ends_stopped_with_the_manifest_in_force_byte_equal(self):
        for label, env_of in self.PASSES:
            with self.subTest(entry=label):
                m = self.machine_for(label)
                looked, went = m.started(inputs=m.inputs(description="a plain project"))
                self.assertEqual(went.ending, "waiting", went.text)
                run_dir = m.facts.run_dir(looked.doc["run"])
                before = dict((n, open(os.path.join(run_dir, n), "rb").read()) for n in os.listdir(run_dir) if n.startswith("manifest-"))
                calls = len(m.calls("fakehost"))
                env = env_of(m)
                replanned = m.summon("replan", "demo", "--inputs", m.inputs(description="a plain project"), env=env)
                self.assertEqual(replanned.ending, "stopped", replanned.text)
                self.assertEqual(len(m.calls("fakehost")), calls, "a child was created")
                after = dict((n, open(os.path.join(run_dir, n), "rb").read()) for n in os.listdir(run_dir) if n.startswith("manifest-"))
                self.assertEqual(after, before, "the manifest in force changed, or a new one was written")
                self.assertNotIn(self.entry_of(env), self.everything_written(m, replanned))


class TheProgramsPath(harness.Case):
    """SEC-3's refusals row: the runner refuses "any argument or environment value that holds an entry of the secret register
    in any form SEC-12 names. That check is made on every argument and every environment value of the child as it would be
    started". The child is started with the program's full path first and its arguments after it (`[program] + argv`, the
    list `runner.run` hands the system's start), so that path is checked as an argument is, in `runner.check` and in
    `runner.run`, before any record that a receipt is due and before any child (the reviewer's D8-X; the owner's ruling, A140).

    What the check lets through and what it refuses, each through a real summons on fakes, the entry coming in by the hosting
    token's channel at the resume alone: a register entry equal to the program's own name, equal to a folder part of its path,
    and equal to the whole path, are refused; a value in none of them is let through. Each pass is made twice: at a command
    with no secret field (`runner.run`), and at a command with a secret field, whose check (`runner.check`) is made before the
    record that a receipt is due. Where the command refused is an operation's, "the operation is not started and the run ends
    `stopped` on that refusal" (the refusals row). A register entry equal to a folder part of the path stands in the child's
    `PATH` too, which is the search list, so it is refused there as well, as it was before this part."""

    PASSES = (("the program's own name", lambda: "fakehost", True),
              ("a folder part of its path", lambda: os.path.basename(rowlib.FAKES), True),
              ("the whole path", lambda: os.path.join(rowlib.FAKES, "fakehost"), True),
              ("a value in none of them", lambda: harness.canary("in-none"), False))
    everything_written = TheRefusalThroughARun.everything_written

    def machine_for(self, label, secret):
        m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
        providers = rowlib.providers()
        providers["fakehost"]["identity"] = rowlib.NONE      # so that the operation's command is the resume's first
        needs = [{"output": "connected", "level": "state", "accepts": ["his word"], "treatment": "then not applicable"}]
        if secret:
            # the secret field's command is the fake host's `issue`; its probe's read goes to another program, the fake git,
            # so that the first command whose program is the fake host is the one with the secret field (`runner.check`)
            providers["fakegit"]["commands"]["issued"] = dict(providers["fakehost"]["commands"]["issued"], tool="fakegit")
            second = rowlib.secret_op("X1", needs=needs)
            second["commands"][0] = rowlib.use("look", "fakegit.issued")
        else:
            second = rowlib.says("Y1", needs=needs)
        rows = [rowlib.owner_step("O1", mode="on his word"), second]
        rowlib.install(m, rowlib.lane("sunrise", rows), providers=providers)
        return m

    def test_SEC3_D8X_the_programs_path_is_checked_as_an_argument_is_in_check_and_in_run(self):
        for secret, op in ((False, "Y1"), (True, "X1")):
            for label, entry_of, refused in self.PASSES:
                with self.subTest(command="with a secret field" if secret else "with no secret field", entry=label):
                    m = self.machine_for(label, secret)
                    looked, went = m.started(inputs=m.inputs(description="a plain project"))
                    self.assertEqual(went.ending, "waiting", went.text)
                    run = looked.doc["run"]
                    records = len(m.journal(run))
                    host_calls = len(m.calls("fakehost"))
                    entry = entry_of()
                    env = {"FAKEHOST_TOKEN": entry}
                    position = m.summon("status").doc["position"]
                    resumed = m.summon("resume", "demo", "--position", position, "--done", "O1", env=env)
                    new = m.journal(run)[records:]
                    host_children = [e for e in resumed.events if e["op"] == "child" and e["stage"] == "pre"
                                     and e.get("path") == os.path.join(rowlib.FAKES, "fakehost")]
                    if refused:
                        self.assertEqual(resumed.ending, "stopped", resumed.text)
                        self.assertIn("stopped: the runner refused the command: register entry", resumed.lines, "not stopped on that refusal")
                        self.assertIn("operation: " + op, resumed.lines, "the form does not name the operation")
                        self.assertIn("the runner refused the command: register entry", self.everything_written(m, resumed))
                        self.assertEqual(host_children, [], "a child of the fake host's program was created")
                        self.assertEqual(len(m.calls("fakehost")), host_calls, "the fake recorded a call")
                        self.assertNotIn(op, m.statuses(run), "the operation got a final status")
                        # where the refused command is a check's read, or the read of a change's probe, the operation is not
                        # started; where it is a change's effect call, met after the start record, the operation stays as that
                        # record left it: no completion is recorded, and no record of the command's execution follows the start
                        # record (the refusals row). An entry equal to a folder part of the path stands in every child's PATH,
                        # so it is met at the probe's read, the first child, and not at the effect call
                        at_effect = secret and label != "a folder part of its path"
                        self.assertEqual([(r["kind"], r.get("step")) for r in new if r.get("op") == op],
                                         [("start", None)] if at_effect else [], "the operation is not as the refusals row has it")
                        self.assertEqual([r for r in new if r.get("step") == "receipt-due"], [], "a record that a receipt is due was written")
                        self.assertNotIn(entry, self.everything_written(m, resumed))
                    else:
                        self.assertTrue(host_children, "the fake host's program was not started")
                        self.assertGreater(len(m.calls("fakehost")), host_calls, "the fake recorded no call")
                        self.assertNotIn("register entry", self.everything_written(m, resumed))
                        if secret:
                            self.assertEqual(len([r for r in new if r.get("step") == "receipt-due"]), 1, "the secret field's command was not let through")
                            self.assertEqual(len(m.calls("fakehost", "issue")), 1)
                        else:
                            self.assertEqual(resumed.ending, "complete", resumed.text)
                            self.assertEqual(m.statuses(run).get(op), "passed")

    def test_SEC3_D8X_the_runner_itself_checks_the_programs_path_in_check_and_in_run_before_any_child(self):
        """The runner's own half, with no run: `runner.check` and `runner.run` each refuse, with "register entry", a command whose
        program's path holds an entry, the fake recording no call; and let a command through where none does."""
        from sun_core import facts as factsmod
        m = self.machine()
        world = m.world()
        search = factsmod.Facts(world.env).search_list(world.fs)
        run_dir = os.path.join(m.home, "rundir")
        os.makedirs(os.path.join(run_dir, "tmp"), mode=0o700)
        decl = {"tool": "fakehost", "time_limit": 20}
        path = os.path.join(m.home, ".fakes", "fakehost", "calls.jsonl")
        for label, entry_of, refused in self.PASSES:
            for how in ("check", "run"):
                with self.subTest(entry=label, at=how):
                    register = screen.Screen()
                    register.add(entry_of(), (), None, "channel")
                    context = runner.Context(register, run_dir, search)
                    before = open(path).read() if os.path.exists(path) else ""
                    act = (lambda: runner.check(world, context, decl, ["noop"], {})) if how == "check" else \
                        (lambda: runner.run(world, context, decl, ["noop"], {}, m.home))
                    if refused:
                        with self.assertRaises(runner.Refused) as caught:
                            act()
                        self.assertEqual(caught.exception.reason, "register entry")
                    else:
                        act()
                    after = open(path).read() if os.path.exists(path) else ""
                    self.assertEqual(after != before, not refused and how == "run", "what the fake recorded")


class TheRefusalAtALaterStart(harness.Case):
    """SEC-3's refusals row (A53): "Where it is a read that a later invocation makes at its start, the reads RUN-10 (b)
    compares and OP-9's reads among them, the refusal is no changed context and asks for no re-plan, whose look would
    meet the same refusal (GOV-1): no effect is applied, and the run ends `stopped` on that refusal, its form naming
    it." Its test line: "met by the identity read of a resume on his current word, it ends that resume with no effect
    call and the run `stopped`, the form naming the refusal and asking for no re-plan." The same two entries as the
    class above, by the hosting token's channel."""

    PASSES = TheRefusalThroughARun.PASSES
    machine_for = TheRefusalThroughARun.machine_for
    entry_of = TheRefusalThroughARun.entry_of
    everything_written = TheRefusalThroughARun.everything_written

    def assert_stopped_on_the_refusal(self, m, result, env, calls):
        from sun_core import texts
        self.assertEqual(result.ending, "stopped", result.text)
        written = self.everything_written(m, result)
        self.assertIn("the runner refused", written, "the form does not name the refusal")
        self.assertNotIn(texts.REPLAN_NEEDED, written, "a re-plan was asked for")
        self.assertNotIn("re-plan is needed", written)
        self.assertEqual(len(m.calls("fakehost")), calls, "a child was started")
        self.assertNotIn(self.entry_of(env), written)
        again = m.summon("status")
        self.assertEqual(again.ending, "stopped", "the run does not stand stopped: %s" % again.text)

    def test_SEC3_A53_RUN10_met_by_the_identity_read_of_a_resume_on_his_current_word_the_run_ends_stopped_asking_for_no_replan(self):
        for label, env_of in self.PASSES:
            with self.subTest(entry=label):
                m = self.machine_for(label)
                looked, went = m.started(inputs=m.inputs(description="a plain project"))
                self.assertEqual(went.ending, "waiting", went.text)
                before = m.statuses(looked.doc["run"])
                calls = len(m.calls("fakehost"))
                env = env_of(m)
                resumed = m.resume("demo", env=env)
                self.assert_stopped_on_the_refusal(m, resumed, env, calls)
                self.assertEqual(m.statuses(looked.doc["run"]), before, "an effect was applied")

    def test_SEC3_A53_OP9_met_by_a_waiting_steps_read_at_a_status_summons_the_run_ends_stopped(self):
        for label, env_of in self.PASSES:
            with self.subTest(entry=label):
                m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
                providers = rowlib.providers()
                providers["fakehost"]["identity"] = rowlib.NONE       # so that the step's read is the one command
                rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="read back")]), providers=providers)
                looked, went = m.started(inputs=m.inputs(description="a plain project"))
                self.assertEqual(went.ending, "waiting", went.text)
                calls = len(m.calls("fakehost"))
                env = env_of(m)
                status = m.summon("status", env=env)
                self.assert_stopped_on_the_refusal(m, status, env, calls)


class TheRefusalAtAGo(harness.Case):
    """SEC-3's refusals row reaches the go's own reads (report-4's note, brief-5 item 5 (a)): "Where it is a read that a
    later invocation makes at its start, the reads RUN-10 (b) compares and OP-9's reads among them, the refusal is no
    changed context and asks for no re-plan, whose look would meet the same refusal (GOV-1): no effect is applied, and
    the run ends `stopped` on that refusal, its form naming it." SEC-12's table has the invocation that records a go make
    "what RUN-10 (b) compares". Before a run's first go there is no run to stand `stopped`: RUN-12, "Before a run's first
    go there is no open run, nothing to resume, and none of the five ... `refused`", with its refusal form; in a re-plan's
    go, the run ends `stopped`, its status form naming the refusal."""

    PASSES = TheRefusalThroughARun.PASSES
    machine_for = TheRefusalThroughARun.machine_for
    entry_of = TheRefusalThroughARun.entry_of
    everything_written = TheRefusalThroughARun.everything_written

    def test_SEC3_A53_RUN10_RUN12_a_first_go_whose_identity_read_is_refused_ends_refused_naming_the_refusal_and_no_look_again(self):
        from sun_core import texts
        for label, env_of in self.PASSES:
            with self.subTest(entry=label):
                m = self.machine_for(label)
                looked = m.look(inputs=m.inputs(description="a plain project"))
                self.assertEqual(looked.ending, "preview", looked.text)
                calls = len(m.calls("fakehost"))
                env = env_of(m)
                went = m.go(looked, env=env)
                self.assertEqual(went.ending, "refused", went.text)
                written = self.everything_written(m, went)
                self.assertIn("the runner refused", written, "the refusal is not named")
                self.assertNotIn(texts.CONTEXT_CHANGED_BEFORE_GO, written, "a changed context was said")
                self.assertNotIn("Look again", written)
                self.assertEqual(len(m.calls("fakehost")), calls, "a child was started")
                self.assertNotIn(self.entry_of(env), written)
                self.assertEqual(m.journal(looked.doc["run"]), [], "a journal record was written before a first go")
                self.assertEqual(m.open_runs(), {})


    def test_SEC3_A53_RUN10_a_replans_go_whose_identity_read_is_refused_ends_the_run_stopped_naming_the_refusal(self):
        from sun_core import texts
        for label, env_of in self.PASSES:
            with self.subTest(entry=label):
                m = self.machine_for(label)
                looked, went = m.started(inputs=m.inputs(description="a plain project"))
                self.assertEqual(went.ending, "waiting", went.text)
                replanned = m.summon("replan", "demo", "--inputs", m.inputs(name="again.json", description="a plain project"))
                self.assertTrue(replanned.doc and replanned.doc.get("manifest_sha256"), replanned.text)
                before = m.statuses(looked.doc["run"])
                calls = len(m.calls("fakehost"))
                env = env_of(m)
                gone = m.run("go", "--kind", "sunrise", "--name", "demo", "--run", looked.doc["run"],
                             "--manifest-sha256", replanned.doc["manifest_sha256"], env=env)
                self.assertEqual(gone.ending, "stopped", gone.text)
                written = self.everything_written(m, gone)
                self.assertIn("the runner refused", written)
                self.assertNotIn(texts.CONTEXT_CHANGED_BEFORE_GO, gone.text)
                self.assertEqual(len(m.calls("fakehost")), calls, "a child was started")
                self.assertNotIn(self.entry_of(env), written)
                self.assertEqual(m.statuses(looked.doc["run"]), before, "an effect was applied")
                self.assertFalse([r for r in m.journal(looked.doc["run"]) if r["kind"] == "go"], "the go was recorded")


class TheIdentityReadAtAStatus(harness.Case):
    """SEC-12's table: "a summons with no word or a stale one ... renders status and ends | for each provider that has a
    waiting read-back step, its identity read and that step's read (OP-9); no planning read"; OP-9: "Every waiting step in
    read-back mode is read again at the start of each invocation but a close, after its provider's identity read
    (SEC-12's table)"; SEC-12's test line: "a status-only summons records, beyond the common reads, the identity read and
    the waiting step's read, and no planning read" (brief-5 item 5 (b))."""

    def test_SEC12_OP9_a_status_summons_makes_the_providers_identity_read_and_then_the_waiting_steps_read_and_no_other(self):
        m = harness.Machine(self.tmp, "home", "status")
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.owner_step("O1", mode="read back")]))
        looked, went = m.started()
        self.assertEqual(went.ending, "waiting", went.text)
        before = len(m.calls("fakehost"))
        status = m.summon("status")
        self.assertEqual(status.ending, "waiting", status.text)
        made = [c["argv"][0] for c in m.calls("fakehost")[before:]]
        self.assertEqual(made, ["whoami", "get"], "not the identity read and then the step's read, and no other")


class TheSearchListInALook(harness.Case):
    """RUN-5's test line: "a tool that stands on the session's path and in no folder of the search list is not found,
    and the look ends as RUN-7's planning stop, naming it"; RUN-7's: "a program a candidate needs that is in no folder
    of the search list, with the program named and the settings file named as where a folder is put on the list";
    SEC-3's: "with that folder not named in the fixture's settings, the look ends as a planning stop that names the
    program and the settings file, and no decoy is started"."""

    def test_SEC3_RUN5_RUN7_a_program_on_the_sessions_path_alone_ends_the_look_naming_it_and_the_settings_file(self):
        m = self.machine()
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.says("Y1")]))
        markers = os.path.join(m.root, "markers")
        os.makedirs(markers)
        decoys = os.path.join(m.root, "decoys")
        program(decoys, "fakehost", os.path.join(markers, "decoy"))
        m.settings["program_folders"] = []
        m.write_settings()
        m.env["PATH"] = decoys + os.pathsep + harness.FAKES + os.pathsep + m.env["PATH"]
        looked = m.look(inputs=m.inputs(description="a plain project"))
        self.assertEqual(looked.ending, "refused", looked.text)
        form = open(looked.doc["forms"][0]).read() if looked.doc.get("forms") else ""
        said = looked.text + form
        self.assertIn("the program fakehost is in no folder of the search list", said)
        self.assertIn(os.path.join(m.home, ".config", "sun-v2", "settings.json"), said, "the settings file is not named")
        self.assertIn("a folder is put on the list only by your naming it in your settings file", said)
        self.assertEqual(os.listdir(markers), [], "the decoy was started")
        self.assertEqual(m.calls("fakehost"), [])



class TheShortcutCheck(harness.Case):
    """SEC-3's command row (the owner's ruling A55; RK12): "The check that a shortcut's name is free starts his shell, zsh,
    which the runner finds in the system folders of the search list, the way a terminal window starts it by default: as
    a login and interactive shell, with an environment built as the next row says. It hands the shell one fixed line
    written in the tool, which asks whether a command of that name exists, and passes the name as a separate argument,
    never written into the line. The declaration maps the shell's exit number to taken or free, and nothing the shell
    prints is read." Its test line: "The shortcut check: the fake shell in a system folder of the fixture's list is
    started as a login and interactive shell, and records the line written in the tool and the shortcut's name as
    separate arguments, the name never inside the line; a name that holds shell marks reaches it as that one argument and
    nothing it marks is run; the fake's exit as for a command found reads taken, and as for none, free; and a fake that
    also prints a canary leaves the canary in no output, form or record." The fake shell (`tests/fakes/fakeshell.py`)
    stands in the fixture's own system folder, `harness.FAKE_SYSTEM`, first of the fixture's system folders."""

    def machine_for(self, label, name="demo", rows=None, kind="sunrise"):
        m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
        rows = rows if rows is not None else [rowlib.swap_add("S1")]
        rowlib.install(m, rowlib.lane(kind, rows))
        m.put("shortcuts.txt", "alias other\n")
        return m

    def shell_calls(self, m):
        return m.fake("zsh", "calls.jsonl", []) or []

    def started_shells(self, result):
        return [e.get("path") for e in result.events if e["op"] == "child" and e["stage"] == "pre" and e["subject"] == "zsh"]

    def everything_written(self, m, result):
        text = result.text
        for run in m.run_ids():
            run_dir = m.facts.run_dir(run)
            for base, _dirs, files in os.walk(run_dir):
                for name in files:
                    with open(os.path.join(base, name), "rb") as fh:
                        text += fh.read().decode("utf-8", "replace")
        return text

    def test_SEC3_A55_RK12_the_shell_from_a_system_folder_is_started_login_and_interactive_with_the_line_and_the_name_apart(self):
        from sun_core import shellcheck
        m = self.machine_for("apart")
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        calls = self.shell_calls(m)
        self.assertEqual(len(calls), 1, "the look did not ask the shell once")
        self.assertEqual(calls[0]["argv"], ["-l", "-i", "-c", shellcheck.LINE, "zsh", "demo"],
                         "not a login and interactive shell handed the one fixed line and the name apart")
        self.assertNotIn("demo", calls[0]["argv"][3], "the name is inside the line")
        self.assertEqual(self.started_shells(looked), [os.path.join(harness.FAKE_SYSTEM, "zsh")],
                         "not the zsh of the fixture's system folder, by its full path")
        self.assertEqual(calls[0]["env_names"], BASE, "not an environment built as SEC-3's environment row says")
        self.assertEqual(calls[0]["env_values"]["PATH"], os.pathsep.join(list(m.system_folders) + [harness.FAKES]),
                         "the shell's PATH is not the tool's search list")
        # a name that holds shell marks reaches it as that one argument, and nothing it marks is run
        marks = "q$(touch${IFS}marked)y;touch${IFS}marked2"
        mm = self.machine_for("marks")
        looked = mm.look(marks)
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual([c["argv"][-1] for c in self.shell_calls(mm)], [marks])
        self.assertNotIn(marks, self.shell_calls(mm)[0]["argv"][3])
        for base, _dirs, files in os.walk(self.tmp):
            self.assertFalse([f for f in files if f.startswith("marked")], "a mark of the name was run")

    def test_SEC3_RUN7_A55_the_shells_exit_reads_taken_or_free_and_nothing_it_prints_is_kept(self):
        from sun_core import texts
        canary = harness.canary("shell-prints")
        m = self.machine_for("prints")
        os.makedirs(os.path.join(m.home, ".fakes", "zsh"))
        with open(os.path.join(m.home, ".fakes", "zsh", "plan.json"), "w") as fh:
            json.dump({"print": canary}, fh)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", "as for no command found, the name reads free: %s" % looked.text)
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(len(self.shell_calls(m)), 2, "the look and the probe did not each ask the shell")
        for result in (looked, went):
            self.assertNotIn(canary, self.everything_written(m, result), "what the shell printed was kept or shown")
        import scan
        self.assertEqual(scan.scan(m, [(canary, [])], (looked, went)), [])
        # as for a command found, the name reads taken: the look ends with that condition named
        taken = self.machine_for("taken")
        taken.put(".zshrc", "alias demo=ls\n")
        stopped = taken.look()
        self.assertEqual(stopped.ending, "refused", stopped.text)
        self.assertIn(texts.SHORTCUT_NAME_TAKEN.format(row="S1"), stopped.lines)
        self.assertEqual([n for n in os.listdir(taken.facts.run_dir(stopped.doc["run"])) if n.startswith("manifest")], [])

    def test_SEC3_A58_RK12_the_shells_TMPDIR_is_the_accounts_own_from_the_system_and_every_other_child_keeps_the_run_directorys(self):
        """SEC-3's environment row (A58): "the shell that the check of a shortcut's name starts ... is given as its
        `TMPDIR` his account's own temporary folder, the one a terminal window uses by default, which the tool reads from
        the system and not from the session ... Every other child keeps the run directory's folder." Its test line: "with
        the session's `TMPDIR` set to a decoy folder, the fake shell's `TMPDIR` is the fixture account's own temporary
        folder as the fixture's system gives it, and neither the decoy nor a folder of the run directory; a fake shell
        that writes a file to its `TMPDIR` leaves that file there and nothing in the run directory, which holds after the
        check only what the tool itself wrote; and every other child that run starts has its `TMPDIR` in the run
        directory (the owner's ruling, A58; RK12)." RISK-1: no record carries a mark for RK12, "a look that made the
        shortcut check among them"."""
        m = self.machine_for("tmpdir", rows=[rowlib.swap_add("S1"), rowlib.says("Y1")])
        decoy = os.path.join(self.tmp, "the-sessions-decoy")
        os.makedirs(decoy)
        m.env["TMPDIR"] = decoy
        os.makedirs(os.path.join(m.home, ".fakes", "zsh"))
        with open(os.path.join(m.home, ".fakes", "zsh", "plan.json"), "w") as fh:
            json.dump({"tmpfile": True}, fh)
        looked = m.look(inputs=m.inputs(description="a plain project"))
        self.assertEqual(looked.ending, "preview", looked.text)
        run_dir = m.facts.run_dir(looked.doc["run"])
        went = m.go(looked)
        self.assertEqual(went.ending, "complete", went.text)
        shells = self.shell_calls(m)
        self.assertTrue(shells)
        for call in shells:
            self.assertEqual(call["env_values"]["TMPDIR"], m.user_temp, "not the fixture account's own temporary folder")
            self.assertFalse(call["env_values"]["TMPDIR"].startswith(run_dir), "a folder of the run directory")
            self.assertNotEqual(call["env_values"]["TMPDIR"], decoy, "the session's TMPDIR")
        self.assertEqual(len([n for n in os.listdir(m.user_temp) if n.startswith("zsh-cache-")]), len(shells),
                         "the file the shell wrote to its TMPDIR is not there")
        self.assertEqual(os.listdir(decoy), [])
        self.assertEqual(os.listdir(os.path.join(run_dir, "tmp")), [], "the shell wrote into the run directory")
        written = set()
        for result in (looked, went):
            for e in result.events:
                if e["stage"] == "pre" and e["op"] in ("create", "append", "replace", "rename", "swap"):
                    written.add(e["subject"])
        for base, _dirs, files in os.walk(run_dir):
            for name in files:
                self.assertIn(os.path.join(base, name), written, "a file in the run directory the tool did not write")
        others = m.calls("fakehost")
        self.assertTrue(others, "the run started no other child")
        for call in others:
            self.assertEqual(call["env_values"]["TMPDIR"], os.path.join(run_dir, "tmp"), "another child's TMPDIR is not the run directory's")
        journal = json.dumps(m.journal(looked.doc["run"]))
        self.assertNotIn("RK12", journal, "a record carries a mark for RK12")
        self.assertEqual(sorted(r["risk"] for r in m.journal(looked.doc["run"]) if r.get("step") == "risk-mark"), ["RK13", "RK2", "RK5"])

    SYSTEM_FOUR = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")

    def program_on(self, name, folders=SYSTEM_FOUR):
        return any(os.path.isfile(os.path.join(f, name)) and os.access(os.path.join(f, name), os.X_OK) for f in folders)

    def system_zsh(self, name, before=None):
        """The tool's fixed line run by the system's zsh with no startup files (`-f`) and the name as its one argument:
        `zsh -f -c LINE zsh NAME`, its environment the system folders' PATH and a home under the test's own folder. Where
        the fixture needs a thing of that shell defined first (a function behind a reserved word), the system zsh runs that
        definition and then the fixed line itself, unchanged, as `eval "$0"` with the line as `$0` and the name as `$1`.
        Returns the exit number."""
        import subprocess
        from sun_core import shellcheck
        home = os.path.join(self.tmp, "zsh-home")
        os.makedirs(home, exist_ok=True)
        env = {"HOME": home, "PATH": os.pathsep.join(self.SYSTEM_FOUR), "LANG": "C", "LC_ALL": "C"}
        if before is None:
            argv = ["/bin/zsh", "-f", "-c", shellcheck.LINE, "zsh", name]
        else:
            argv = ["/bin/zsh", "-f", "-c", before + '\neval "$0"', shellcheck.LINE, name]
        return subprocess.call(argv, env=env, cwd=home, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)

    def test_SEC3_RUN7_A63_the_fixed_line_itself_in_the_systems_zsh_with_no_startup_files_counts_every_kind(self):
        """SEC-3's test line (batch 23, A63): "The fixed line itself, run by the system's zsh with no startup files and the
        name as its one argument, exits as taken for a name that is only a builtin, only a reserved word, a builtin with a
        program of its name behind it, and a reserved word with a function of its name, and as free for a name that is
        none of these (the owner's ruling, A63)." RUN-7's `in` row: "Each counts where it exists for that shell, whatever
        that shell would run first for the name". The batch 22B list of names a program of which stands on the search
        list while `whence -w` read them free (`test`, `cd`, `echo`, `printf`, `kill`, `pwd`, `time`) is run too."""
        from sun_core import shellcheck
        self.assertTrue(os.path.exists("/bin/zsh"), "no system zsh to run the line in")
        none = "zz" + harness.canary("none").lower().replace("-", "")[:20]
        cases = [
            ("only a builtin", "source", None, False),
            ("only a reserved word", "if", None, False),
            ("a builtin with a program of its name behind it", "test", None, True),
            ("a reserved word with a function of its name", "do", "function do { :; }", False),
        ]
        for label, name, before, program in cases:
            with self.subTest(taken=label):
                self.assertEqual(self.program_on(name), program, "the fixture's premise about a program of %r" % name)
                self.assertEqual(self.system_zsh(name, before), int(shellcheck.TAKEN), label)
        for name in ("cd", "echo", "printf", "kill", "pwd", "time"):
            with self.subTest(taken="a program on the path behind another command: %s" % name):
                self.assertTrue(self.program_on(name), "the fixture's premise: a program of %r on the system folders" % name)
                self.assertEqual(self.system_zsh(name), int(shellcheck.TAKEN), name)
        with self.subTest(free="a name that is none of these"):
            self.assertFalse(self.program_on(none))
            self.assertEqual(self.system_zsh(none), int(shellcheck.FREE))
        # the name is the line's one argument, never in it: a name that holds the shell's marks is taken as that word
        with self.subTest(free="a name with the shell's marks"):
            marked = os.path.join(self.tmp, "zsh-home", "marked")
            self.assertEqual(self.system_zsh("q$(touch ${HOME}/marked)y"), int(shellcheck.FREE))
            self.assertFalse(os.path.exists(marked), "a mark of the name was run")

    def test_RUN7_A63_a_name_his_login_zsh_holds_as_any_kind_of_command_is_taken_whatever_runs_first(self):
        """RUN-7's test line (batch 23, A63): "so does a name that the fixture's login zsh would run first as a builtin,
        and in a second pass as a reserved word, and that also names a program in a folder of that shell's path, and in a
        third pass a reserved word that is also the name of a shell function there, each with the name taken. A name that
        is only a builtin there, with no program, alias or function of it, and in a second pass only a reserved word, each
        ends the look with the name taken; so does a name that is a builtin only because the fixture's startup file loads a
        zsh module (the owner's ruling, A63)". Each: the look ends `refused` with the condition named and no manifest
        (RUN-7: "ends the look with the condition named and no manifest")."""
        from sun_core import texts
        plants = [
            ("run first as a builtin, a program of it on that shell's path", "test", None, True),
            ("run first as a reserved word, a program of it on that shell's path", "time", None, True),
            ("a reserved word that is also a shell function there", "do", "function do { ls }\n", False),
            ("only a builtin there", "source", None, False),
            ("only a reserved word there", "if", None, False),
            ("a builtin only because the startup file loads a zsh module", "strftime", "zmodload zsh/datetime\n", False),
        ]
        for label, name, zshrc, program in plants:
            with self.subTest(taken=label):
                m = self.machine_for(label)
                self.assertEqual(self.program_on(name, m.system_folders), program, "the fixture's premise about %r" % name)
                if zshrc:
                    m.put(".zshrc", zshrc)
                stopped = m.look(name)
                self.assertEqual(stopped.ending, "refused", stopped.text)
                self.assertIn(texts.SHORTCUT_NAME_TAKEN.format(row="S1"), stopped.lines)
                self.assertEqual([n for n in os.listdir(m.facts.run_dir(stopped.doc["run"])) if n.startswith("manifest")], [])
                self.assertEqual([c["argv"][-1] for c in self.shell_calls(m)], [name])
        # the module's builtin is there only because the startup file loads it: without that line the name is free
        with self.subTest(free="strftime with no zmodload"):
            m = self.machine_for("no module")
            looked = m.look("strftime")
            self.assertEqual(looked.ending, "preview", looked.text)

    def test_SEC3_RUN7_GOV1_with_no_owner_only_account_folder_the_shell_is_not_started_and_the_first_look_is_refused(self):
        """SEC-3's environment row (batch 22): "Where the system gives no such folder, or gives one that is not an
        owner-only folder of his account, that shell is not started: the check is a failed read, and the look ends as
        RUN-7's planning stop, naming the check. No rule gives that shell another folder, and the tool never picks one
        (GOV-1)". Its test line: "With the fixture's system giving no folder for the account, and in a second pass one
        that other accounts may read or write, the fake shell is not started, and a first look ends `refused` before any
        preview, with the shortcut check named as a failed read and no manifest written (GOV-1)." The second pass is run
        twice: a folder others may read, and one others may write."""
        passes = [("the system gives no folder", None), ("a folder other accounts may read", 0o755),
                  ("a folder other accounts may write", 0o733)]
        for label, mode in passes:
            with self.subTest(account_folder=label):
                m = self.machine_for(label)
                if mode is None:
                    m.user_temp = None
                else:
                    os.chmod(m.user_temp, mode)
                stopped = m.look()
                if mode is not None:
                    os.chmod(m.user_temp, 0o700)
                self.assertEqual(stopped.ending, "refused", stopped.text)
                self.assertEqual(self.shell_calls(m), [], "the shell was started")
                self.assertEqual(self.started_shells(stopped), [], "a child zsh was started")
                failed = "the read failed: whether the shortcut's name is free of row S1"
                self.assertIn(failed, stopped.lines, "the shortcut check is not named as a failed read")
                self.assertNotIn("preview", [f.rsplit(os.sep, 1)[-1].split("-")[0] for f in stopped.doc.get("forms") or []])
                form = open(stopped.doc["forms"][0]).read()
                self.assertIn(failed, form)
                run_dir = m.facts.run_dir(stopped.doc["run"])
                self.assertEqual([n for n in os.listdir(run_dir) if n.startswith("manifest") or n == "journal.jsonl"], [],
                                 "a manifest or a journal was written")
                if mode is not None:
                    self.assertEqual(os.listdir(m.user_temp), [], "something was written in the account's folder")

    def test_SEC3_RUN7_batch28_with_no_zsh_in_a_system_folder_no_shell_is_started_and_the_first_look_is_refused(self):
        """SEC-3's command row (batch 28): "Where no system folder of the search list holds zsh, the check cannot be made: it
        is a failed read, and the look ends as RUN-7's planning stop for a read that failed, naming the check. It is not
        RUN-7's line for a program in no folder of the search list, whose form points him at his settings file, since no
        folder he names is searched for this shell." Its test line: "No zsh in a system folder: with no zsh in any system
        folder of the fixture's list, and in a second pass with one in a folder the fixture's settings name and none in a
        system folder, no shell is started and a first look ends `refused` before any preview, with the shortcut check
        named as a failed read, no manifest written, and the settings file named nowhere in its form; the shell in the
        folder the settings name is never started."
        """
        import shutil
        for label in ("no zsh in any system folder", "a zsh in a folder the settings name and none in a system folder"):
            with self.subTest(zsh=label):
                m = self.machine_for(label)
                bare = os.path.join(m.root, "bare-system-" + m.seed.replace(" ", "-"))
                os.makedirs(bare)
                m.system_folders = (bare,)                  # the fixture's system folders: one, holding no zsh
                if label.startswith("a zsh"):
                    named = os.path.join(m.root, "named-" + m.seed.replace(" ", "-"))
                    os.makedirs(named)
                    shutil.copy2(os.path.join(harness.FAKE_SYSTEM, "zsh"), os.path.join(named, "zsh"))
                    m.settings["program_folders"] = [named] + list(m.settings["program_folders"])
                    m.write_settings()
                stopped = m.look()
                self.assertEqual(stopped.ending, "refused", stopped.text)
                self.assertEqual(self.shell_calls(m), [], "a shell was started")
                self.assertEqual(self.started_shells(stopped), [], "a child zsh was started")
                failed = "the read failed: whether the shortcut's name is free of row S1"
                self.assertIn(failed, stopped.lines, "the shortcut check is not named as a failed read")
                form = open(stopped.doc["forms"][0]).read()
                self.assertIn(failed, form)
                self.assertNotIn(m.facts.settings_path, form, "the settings file is named in the form")
                self.assertNotIn("settings file", form)
                self.assertNotIn("preview", [f.rsplit(os.sep, 1)[-1].split("-")[0] for f in stopped.doc.get("forms") or []])
                run_dir = m.facts.run_dir(stopped.doc["run"])
                self.assertEqual([n for n in os.listdir(run_dir) if n.startswith("manifest") or n == "journal.jsonl"], [])

    def test_EV6_A55_an_alias_line_returns_at_the_end_only_when_its_name_is_free_as_the_fixtures_login_zsh_finds_them(self):
        """EV-6's test line (batch 23): "an alias line returns at the end of the shortcut file only when its name is free:
        a program of that name in the package manager's folder, an alias of that name, a shell function of that name, a
        builtin of that name and a reserved word of that name, each found by the fixture's login zsh, each stop the
        restore's look with the name taken (the owner's ruling, A63), and with none of them the line is added." RISK-1:
        "a shortcut's add and its put-back carry RK5's mark and RK13's beside RK2's"." The put-back is a sunset's own
        reverse (EV-5, part F): the sunset removes the alias line by a swap that declares its way back, the line put back at
        the end of the unordered shortcut file, and the restore's look plans that reverse from the sunset's journal."""
        from sun_core import plan, texts
        P = plan.RETIREMENT_PHASES
        put_back = rowlib.swap_add("S1", phase="back")
        put_back.update(way_back={"none": "the row declares none: it is itself a reverse"}, reverse_inputs="none", span="none")
        removal = rowlib.swap_add("T11", phase=P[1])["way_back"]["reverse"]
        removal.update(id="T11", phase=P[1], way_back={"reverse": put_back}, span={"placement": "at the end", "ordered": False},
                       reverse_inputs=[{"read": "file", "path": {"location": "shortcut_file"}, "type": "before-image",
                                        "label": "the shortcut file before the line was taken out"}])

        def machine(label, name):
            mm = self.machine_for(label, rows=[removal], kind="sunset")
            rowlib.install(mm, rowlib.lane("sunset", [removal], phases=P), rowlib.lane("restore", [], phases=("back",)))
            mm.put("shortcuts.txt", "alias other\nalias %s\n" % name)
            self.assertEqual(mm.started(name, "sunset")[1].ending, "complete")
            self.assertEqual(open(mm.path("shortcuts.txt")).read(), "alias other\n")
            return mm
        plants = {
            "a program of that name in the package manager's folder": ("demo", lambda mm: (
                mm.put("opt/pm/bin/demo", "#!/bin/sh\n", 0o755), mm.put(".zprofile", "path+=(%s)\n" % mm.path("opt", "pm", "bin")))),
            "an alias of that name": ("demo", lambda mm: mm.put(".zshrc", "alias demo=ls\n")),
            "a shell function of that name": ("demo", lambda mm: mm.put(".zshrc", "demo() { ls }\n")),
            # batch 23 (A63): "a builtin of that name and a reserved word of that name, each found by the fixture's
            # login zsh, each stop the restore's look with the name taken"
            "a builtin of that name": ("source", lambda mm: None),
            "a reserved word of that name": ("if", lambda mm: None),
        }
        for label, (name, plant) in plants.items():
            with self.subTest(taken=label):
                mm = machine(label, name)
                plant(mm)
                before = open(mm.path("shortcuts.txt")).read()
                stopped = mm.look(name, kind="restore")
                self.assertEqual(stopped.ending, "refused", stopped.text)
                self.assertIn(texts.SHORTCUT_NAME_TAKEN.format(row="S1"), stopped.lines)
                self.assertEqual(open(mm.path("shortcuts.txt")).read(), before)
        free = machine("free", "demo")
        looked = free.look(kind="restore")
        self.assertEqual(looked.ending, "preview", looked.text)
        went = free.go(looked, kind="restore")
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(open(free.path("shortcuts.txt")).read(), "alias other\nalias demo\n", "the line is not at the end")
        marks = sorted((r["op"], r["risk"]) for r in free.journal(looked.doc["run"]) if r.get("step") == "risk-mark")
        self.assertEqual(marks, [("S1", "RK13"), ("S1", "RK2"), ("S1", "RK5")], "the put-back's marks (RISK-1, A63)")


class TheRefusalAtAProbe(harness.Case):
    """SEC-3's test line (batch 40, A94): "a register entry equal to the value of a base name, the fixture's user name, and
    in a second pass one that is a part of the temporary folder's path, each refuse the command before any child is created
    ... and, met by the shortcut check's shell at an operation's probe at run time, the read of that operation's
    before-test, it ends the run `stopped` on that refusal, the operation not started, no start record of it written and no
    effect call made, the form naming the refusal, and no exception reported." SEC-3's refusals row: "Where the refused
    command is an operation's, the operation is not started and the run ends `stopped` on that refusal." The shell's
    temporary folder is his account's own (SEC-3's environment row, A58), so the second pass plants a part of that
    folder's path. The look is made with no entry, so that the shell's check there reads the name free; the entry comes
    in by the hosting token's channel (SEC-2) at the go, whose first runner use is then the shell at S1's probe."""

    PASSES = (("the user's name, a base name's value", lambda m: {"USER": "zzuserq9", "FAKEHOST_TOKEN": "zzuserq9"}),
              ("a part of the shell's temporary folder's path", lambda m: {"FAKEHOST_TOKEN": os.path.basename(m.user_temp)}))

    def machine_for(self, label, rows, text):
        m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
        providers = rowlib.providers()
        providers["fakehost"]["identity"] = rowlib.NONE      # so that the shell at the probe is the go's first runner use
        rowlib.install(m, rowlib.lane("sunrise", rows), providers=providers)
        m.put("shortcuts.txt", text)
        return m

    def assert_stopped_at_the_probe(self, rows, text):
        """Each pass: the look reads the name free; the go, with the entry in its register, ends `stopped` on the runner's
        refusal at S1's probe, as SEC-3's test line words it."""
        from sun_core import texts
        written = TheShortcutCheck.everything_written
        op = rows[0]["id"]
        for label, env_of in self.PASSES:
            with self.subTest(entry=label):
                m = self.machine_for(label, rows, text)
                looked = m.look(inputs=m.inputs(description="a plain project"))
                self.assertEqual(looked.ending, "preview", looked.text)
                shells = len(m.fake("zsh", "calls.jsonl", []) or [])
                self.assertEqual(shells, 1, "the look did not ask the shell")
                before = open(m.path("shortcuts.txt"), "rb").read()
                env = env_of(m)
                entry = env["FAKEHOST_TOKEN"]
                self.assertIn(entry, json.dumps({"USER": env.get("USER"), "TMPDIR": m.user_temp}), "the fixture's premise")
                went = m.go(looked, env=env)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
                self.assertIn("stopped: the runner refused the command: register entry", went.lines, "not stopped on that refusal")
                self.assertIn("operation: %s" % op, went.lines)
                form = open(went.doc["forms"][0]).read()
                self.assertIn("the runner refused the command: register entry", form, "the form does not name the refusal")
                journal = m.journal(looked.doc["run"])
                self.assertTrue([r for r in journal if r["kind"] == "open" and r.get("word") == "go"], "the go is not on record")
                self.assertEqual([r for r in journal if r.get("op") == op and r["kind"] in ("start", "completion", "status")], [],
                                 "the operation was started, or given a status")
                self.assertEqual(len(m.fake("zsh", "calls.jsonl", []) or []), shells, "the shell was started at the probe")
                self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "pre"], [], "a child was created")
                self.assertEqual(open(m.path("shortcuts.txt"), "rb").read(), before, "an effect was made")
                self.assertNotIn(entry, written(self, m, went), "the entry is in an output, a form or a record")
                again = m.summon("status")
                self.assertEqual(again.ending, "stopped", "the run does not stand stopped: %s" % again.text)

    def test_SEC3_A94_met_by_the_shortcut_checks_shell_at_an_operations_probe_the_run_ends_stopped_on_that_refusal(self):
        """The frame's case: the read of the operation's before-test, a shortcut's add (its `name-free` read)."""
        self.assert_stopped_at_the_probe([rowlib.swap_add("S1")], "alias other\n")

    def test_SEC3_A94_the_same_refusal_met_at_another_read_of_a_probe_the_after_tests_ends_the_run_the_same_way(self):
        """Another read of a probe that the same path reaches (report-13, item 1): the after-test, which OP-5 has the probe
        ask before the before-test. A removal of a shortcut's line whose after-state names the name free: the probe meets the
        shell at its after-test read. SEC-3's refusals row gives it the same words: the refused command is the operation's."""
        removal = rowlib.swap_add("S1")["way_back"]["reverse"]
        removal.update(id="S1", after_test=removal["after_test"] + [{"id": "name", "read": "name-free", "name": rowlib.NAME}])
        self.assert_stopped_at_the_probe([removal], "alias other\nalias demo\n")


class TheRefusalOutsideAProbe(harness.Case):
    """SEC-3's refusals row (batch 41, A96): "A refused command met after the operation's start record, at its effect call
    or at its after-check, leaves the operation as that record left it: no completion is recorded, the run ends `stopped`
    on that refusal, its form naming it, and the next invocation's probe reads the world again, as OP-6 has it for an
    effect call that fails and an after-check that does not show the after-state. An owner step's read, made when the step
    is first reached, is a command of that operation: where it is refused, the step is not shown, no `waiting` record is
    written, and the run ends `stopped` on that refusal (OP-9). ... Where it is a read that a later invocation makes at its
    start, the reads RUN-10 (b) compares and OP-9's reads among them, ... no effect is applied, and the run ends `stopped`
    on that refusal, its form naming it. That holds for a summons with no word too, whose OP-9 reads are among them: a run
    left `waiting` then ends `stopped` on that refusal". Its test line: "A refusal met outside a probe, each with no
    exception reported: at a change's after-check, once its effect call has been made, by an entry that only that
    invocation's register holds, the run ends `stopped` on that refusal with the start record standing and no completion
    recorded, and the next resume's probe, its register without that entry, answers `landed`; at the read-back read of an
    owner step the run first reaches, the step is in no form, no `waiting` record is written and the run ends `stopped` on
    that refusal; and at the read-back read of a step left `waiting`, made at the start of a resume on his current word and
    in a second pass of a summons with no word, each ends with no effect call and the run `stopped` on that refusal, its
    form naming it."

    The entry comes in by the hosting token's channel (SEC-2) at the one invocation that is to meet it, and is gone from
    the channel at the next. Each read is made in two kinds: the shortcut check's shell (a `name-free` read, the shell's
    temporary folder his account's own, A58), with the two entries of SEC-3's test line, the user's name and a part of
    that shell's temporary folder's path; and, for an owner step, a row's command (the fake host's `get`), with the user's
    name. The fake host's identity read is `none`, so that the read under test is the first runner use of its
    invocation."""

    SHELL = TheRefusalAtAProbe.PASSES
    COMMAND = TheRefusalThroughARun.PASSES[:1]
    STEP = "connect the fake host by hand"

    def machine_for(self, label, rows, shortcuts=None, zshrc=None, phases=("one",)):
        m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
        providers = rowlib.providers()
        providers["fakehost"]["identity"] = rowlib.NONE
        rowlib.install(m, rowlib.lane("sunrise", rows, phases=phases), providers=providers)
        if shortcuts is not None:
            m.put("shortcuts.txt", shortcuts)
        if zshrc is not None:
            m.put(".zshrc", zshrc)
        return m

    def shells(self, m):
        return len(m.fake("zsh", "calls.jsonl", []) or [])

    def written(self, m, result):
        return TheShortcutCheck.everything_written(self, m, result)

    def assert_ended_on_the_refusal(self, m, result, op, entry):
        from sun_core import texts
        self.assertEqual(result.ending, "stopped", result.text)
        self.assertNotIn(texts.DEFECT, result.text, "an exception was reported")
        self.assertIn("stopped: the runner refused the command: register entry", result.lines, "not stopped on that refusal")
        self.assertIn("operation: %s" % op, result.lines)
        self.assertTrue(result.doc.get("forms"), "no status form was rendered: %s" % result.text)
        form = open(result.doc["forms"][0]).read()
        self.assertIn("the runner refused the command: register entry", form, "the form does not name the refusal")
        self.assertEqual([e for e in result.events if e["op"] == "child" and e["stage"] == "pre"], [], "a child was created")
        self.assertNotIn(entry, self.written(m, result), "the entry is in an output, a form or a record")

    # ---- at a change's after-check, once its effect call has been made -------------------------------------------
    def test_SEC3_A96_a_refusal_at_a_changes_after_check_stops_the_run_with_the_start_record_standing_and_the_next_probe_answers_landed(self):
        """A change by C3 (a removal of a shortcut's line) whose after-check also asks the shortcut check's shell; its probe
        makes no runner use, its effect is the swap. The go's register holds the entry, so the swap is made and the shell
        at the after-check is refused; the next resume's register does not."""
        removal = rowlib.swap_add("S1")["way_back"]["reverse"]
        removal.update(id="S1", after_check=removal["after_check"] + [{"id": "name", "read": "name-free", "name": rowlib.NAME}])
        for label, env_of in self.SHELL:
            with self.subTest(entry=label):
                m = self.machine_for(label, [removal], shortcuts="alias other\nalias demo\n")
                looked = m.look(inputs=m.inputs(description="a plain project"))
                self.assertEqual(looked.ending, "preview", looked.text)
                shells = self.shells(m)        # the look reads no after-check
                env = env_of(m)
                entry = env["FAKEHOST_TOKEN"]
                went = m.go(looked, env=env)
                self.assert_ended_on_the_refusal(m, went, "S1", entry)
                run = looked.doc["run"]
                journal = m.journal(run)
                starts = [r for r in journal if r.get("op") == "S1" and r["kind"] == "start"]
                self.assertEqual(len(starts), 1, "the start record does not stand")
                self.assertEqual([r for r in journal if r.get("op") == "S1" and r["kind"] in ("completion", "status")], [],
                                 "a completion or a status was recorded")
                self.assertEqual(open(m.path("shortcuts.txt")).read(), "alias other\n", "the effect call was not made")
                self.assertEqual(self.shells(m), shells, "the shell was started at the after-check")
                self.assertEqual(m.summon("status").ending, "stopped", "the run does not stand stopped")
                # the next resume, its register without that entry: the probe reads the world again and answers `landed`
                resumed = m.resume("demo")
                self.assertEqual(resumed.ending, "complete", resumed.text)
                journal = m.journal(run)
                self.assertEqual(len([r for r in journal if r.get("op") == "S1" and r["kind"] == "start"]), 1,
                                 "a new start record: the probe did not answer `landed`")
                completions = [r for r in journal if r.get("op") == "S1" and r["kind"] == "completion"]
                self.assertEqual([c.get("ground") for c in completions], ["b"], "not completed on the `landed` row's ground")
                self.assertEqual(self.shells(m), shells + 1, "the after-check was not made again")
                self.assertEqual(open(m.path("shortcuts.txt")).read(), "alias other\n")

    # ---- an owner step's read, made when the step is first reached -------------------------------------------------
    def first_reached(self, kind):
        if kind == "shell":
            return rowlib.owner_step("O1", mode="read back", after_test=[{"id": "name", "read": "name-free", "name": rowlib.NAME}],
                                     commands=rowlib.NONE)
        return rowlib.owner_step("O1", mode="read back")

    def test_SEC3_A96_OP9_a_refusal_at_an_owner_steps_read_first_reached_shows_no_step_writes_no_waiting_record_and_stops(self):
        for kind, passes in (("shell", self.SHELL), ("command", self.COMMAND)):
            for label, env_of in passes:
                with self.subTest(read=kind, entry=label):
                    m = self.machine_for(label, [self.first_reached(kind)], zshrc="alias demo=true\n")
                    looked = m.look(inputs=m.inputs(description="a plain project"))
                    self.assertEqual(looked.ending, "preview", looked.text)
                    shells, hosts = self.shells(m), len(m.calls("fakehost"))
                    env = env_of(m)
                    entry = env["FAKEHOST_TOKEN"]
                    went = m.go(looked, env=env)
                    self.assert_ended_on_the_refusal(m, went, "O1", entry)
                    journal = m.journal(looked.doc["run"])
                    self.assertEqual([r for r in journal if r.get("op") == "O1" and r["kind"] in ("waiting", "status")], [],
                                     "a `waiting` record or a status was written")
                    self.assertNotIn(self.STEP, open(went.doc["forms"][0]).read(), "the step is shown in the form")
                    self.assertNotIn(self.STEP, went.text, "the step is shown in the output")
                    self.assertEqual((self.shells(m), len(m.calls("fakehost"))), (shells, hosts), "the read's child was started")
                    self.assertEqual(m.summon("status").ending, "stopped", "the run does not stand stopped")

    # ---- the read-back read of a step left `waiting`, at the start of a later invocation --------------------------
    def test_SEC3_A96_OP9_RUN10_a_refusal_at_a_waiting_steps_read_at_a_resume_on_his_word_and_at_a_summons_with_no_word_stops_the_run(self):
        """Two passes of the summons: a resume on his current word, and a summons with no word (a status). A run left
        `waiting` whose summons with no word meets the refusal ends `stopped` (A96: "it is the refusal that ends the
        invocation and not RUN-10's own ending"). A second operation, which needs nothing of the step, is the effect that
        a resume would make were it not stopped: it is held back by the step's phase, so the run stays as it was."""
        for summons in ("resume on his current word", "summons with no word"):
            for kind, passes in (("shell", self.SHELL), ("command", self.COMMAND)):
                for label, env_of in passes:
                    with self.subTest(summons=summons, read=kind, entry=label):
                        rows = [self.first_reached(kind), rowlib.says("Y1", phase="two")]
                        m = self.machine_for(label, rows, zshrc="alias demo=true\n", phases=("one", "two"))
                        looked, went = m.started(inputs=m.inputs(description="a plain project"))
                        self.assertEqual(went.ending, "waiting", went.text)
                        run = looked.doc["run"]
                        before = m.statuses(run)
                        position = m.summon("status").doc["position"]
                        shells, hosts = self.shells(m), len(m.calls("fakehost"))
                        env = env_of(m)
                        entry = env["FAKEHOST_TOKEN"]
                        if summons == "summons with no word":
                            ended = m.summon("status", env=env)
                        else:
                            ended = m.summon("resume", "demo", "--position", position, "--word", "go on", env=env)
                        self.assert_ended_on_the_refusal(m, ended, "O1", entry)
                        self.assertNotIn("re-plan is needed", ended.text, "a re-plan was asked for")
                        self.assertEqual(m.statuses(run), before, "an effect was applied, or a status recorded")
                        self.assertEqual((self.shells(m), len(m.calls("fakehost"))), (shells, hosts), "the read's child was started")
                        self.assertEqual(m.summon("status").ending, "stopped", "the run does not stand stopped")
                        last = [r for r in m.journal(run) if r["kind"] == "invocation-end"][-1]
                        self.assertEqual(last.get("ending"), "stopped", "the run does not stand stopped")

    def test_OP9_A120_a_waiting_steps_read_refused_by_the_runner_at_a_resume_on_his_word_leaves_the_step_in_no_form(self):
        """OP-9 (batch 51, A120): "a waiting step whose read this invocation did not make ... is in no form this invocation
        renders, neither from the manifest's text nor from an earlier form's: where the runner refuses that read, and the
        invocation ends `stopped` on the refusal (SEC-3's refusals row)". Its test line: "A waiting step with no fresh read:
        its read refused by the runner at the start of a resume on his current word; ... in each, neither the manifest's text
        of the step nor an earlier form's is in any form the invocation renders, and it ends `stopped`". A second pass, a
        summons with no word, is the same sentence's. The step's line is the lane's list's (FORM-2, A120)."""
        from sun_core import texts
        for summons in ("resume on his current word", "summons with no word"):
            for label, env_of in self.COMMAND:
                with self.subTest(summons=summons, entry=label):
                    rows = [self.first_reached("command"), rowlib.says("Y1", phase="two")]
                    m = self.machine_for(label, rows, phases=("one", "two"))
                    looked, went = m.started(inputs=m.inputs(description="a plain project"))
                    self.assertEqual(went.ending, "waiting", went.text)
                    self.assertIn(self.STEP, open(went.doc["forms"][0]).read(), "the fixture's premise: the step is shown while it waits")
                    position = m.summon("status").doc["position"]
                    env = env_of(m)
                    if summons == "summons with no word":
                        ended = m.summon("status", env=env)
                    else:
                        ended = m.summon("resume", "demo", "--position", position, "--word", "go on", env=env)
                    self.assert_ended_on_the_refusal(m, ended, "O1", env["FAKEHOST_TOKEN"])
                    for path in ended.doc["forms"]:
                        self.assertNotIn(self.STEP, open(path).read(), "the step is in a form this invocation renders")
                    self.assertNotIn(self.STEP, ended.text, "the step is in the output")
                    line = rowlib.FORM_CHANGES["waiting, not shown"].format(what="the fake row O1", mode="read back", how="by its own read")
                    self.assertIn("[O1] " + line, open(ended.doc["forms"][0]).read(), "the step has not the lane's line")
                    self.assertNotIn(texts.DEFECT, ended.text)

    def test_OP9_A122_while_a_replans_manifest_awaits_his_go_a_waiting_steps_read_refused_at_a_summons_with_no_word_is_in_neither_manifests_text(self):
        """OP-9's test line (batch 52, A122): "and while a re-plan's manifest awaits his go, a summons with no word whose read
        of a waiting step the runner refuses renders that step in neither manifest's text nor an earlier form's." The run is
        left `waiting` on O1 and re-planned, the new manifest holding O1 again with the same step; the summons with no word
        then meets the entry at O1's read, made at its start."""
        from sun_core import texts
        for label, env_of in self.COMMAND:
            with self.subTest(entry=label):
                rows = [self.first_reached("command"), rowlib.says("Y1", phase="two")]
                m = self.machine_for(label, rows, phases=("one", "two"))
                looked, went = m.started(inputs=m.inputs(description="a plain project"))
                self.assertEqual(went.ending, "waiting", went.text)
                self.assertIn(self.STEP, open(went.doc["forms"][0]).read(), "the fixture's premise: the step is shown while it waits")
                replanned = m.summon("replan", "demo", "--inputs", m.inputs(name="again.json", description="a plain project"))
                self.assertTrue(replanned.doc and replanned.doc.get("manifest_sha256"), replanned.text)
                run = looked.doc["run"]
                folder = m.facts.run_dir(run)
                manifests = sorted(n for n in os.listdir(folder) if n.startswith("manifest-"))
                self.assertEqual(len(manifests), 2, "the fixture's premise: a re-plan's manifest awaits his go")
                for name in manifests:
                    self.assertIn(self.STEP, open(os.path.join(folder, name)).read(), "the fixture's premise: each manifest holds the step")
                env = env_of(m)
                ended = m.summon("status", env=env)
                self.assert_ended_on_the_refusal(m, ended, "O1", env["FAKEHOST_TOKEN"])
                for path in ended.doc["forms"]:
                    self.assertNotIn(self.STEP, open(path).read(), "the step is in a form this invocation renders")
                self.assertNotIn(self.STEP, ended.text, "the step is in the output")
                line = rowlib.FORM_CHANGES["waiting, not shown"].format(what="the fake row O1", mode="read back", how="by its own read")
                self.assertIn("[O1] " + line, open(ended.doc["forms"][0]).read(), "the step has not the lane's line")
                self.assertNotIn(texts.DEFECT, ended.text)


class TheRefusalOfACreatesSend(harness.Case):
    """SEC-3's refusals row (batch 43, A100): "For a create, whose effect call is its send, the refusal is first written as a
    step record of that create (LOG-2): with it no request left the tool, the create is not outstanding, and its next probe
    reads the world again, `not landed` with nothing under its name (OP-5, OP-6, OP-7; the owner's ruling, A99); a create
    with no such record after its start record stays outstanding (OP-7)." Its test line: "At a create's send, by a value
    that only that invocation's register holds, the runner refuses before any child is created: the journal holds the
    start record and then the step record of the refusal, the run ends `stopped` on that refusal with no call recorded by
    the fake, and the next resume, its register without that value, probes the create `not landed` and sends it once on
    his word (the owner's ruling, A99)."

    The value comes in by the hosting token's channel at the go alone, with the two entries of SEC-3's test line: the user's
    name, a base name's value, and a part of the temporary folder's path. The create's look is the fake host's own request
    (SEC-2), which starts no child, so that the send is the go's first child (`rowlib.install_refused_send`)."""

    PASSES = TheRefusalThroughARun.PASSES
    everything_written = TheRefusalThroughARun.everything_written

    def test_SEC3_A99_a_refused_send_writes_the_refusals_step_record_and_the_next_resume_probes_not_landed_and_sends_once(self):
        from sun_core import texts
        for label, env_of in self.PASSES:
            with self.subTest(entry=label):
                m = rowlib.install_refused_send(harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label))
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                run = looked.doc["run"]
                env = env_of(m)
                went = m.go(looked, env=env)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
                self.assertIn("stopped: the runner refused the command: register entry", went.lines, "not stopped on that refusal")
                self.assertIn("operation: C1", went.lines)
                self.assertIn("the runner refused the command: register entry", self.everything_written(m, went))
                self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "pre"], [], "a child was created")
                self.assertEqual(m.calls("fakehost"), [], "the fake recorded a call")
                c1 = [(r["kind"], r.get("step")) for r in m.journal(run) if r.get("op") == "C1"]
                self.assertEqual(c1, [("start", None), ("step", "send-refused")],
                                 "the journal does not hold the start record and then the step record of the refusal")
                self.assertNotIn(env["FAKEHOST_TOKEN"], self.everything_written(m, went))
                resumed = m.resume()                             # its register without that value, on his word
                self.assertEqual(resumed.ending, "complete", resumed.text)
                starts = [r for r in m.journal(run) if r.get("op") == "C1" and r["kind"] == "start"]
                self.assertEqual([r["probe"] for r in starts], ["ready", "not landed"], "the create was not probed `not landed`")
                self.assertEqual(len(m.calls("fakehost", "create")), 1, "the create was not sent once")
                self.assertEqual(sorted(m.fake("fakehost", "state.json")["things"]), ["demo"])


class AProgramNotFoundAtAnOperation(harness.Case):
    """SEC-3's command row (batch 46, A110): "A name found in no folder of the search list is a tool not found (RUN-7). For a
    command of an operation it is also a refusal of the runner's (the refusals row), and so is a file that the runner found
    and that is gone as it starts it, so that no child is created; a start that creates a child is no refusal, however that
    child ends (OP-6) (the owner's ruling, A109)." Its refusals row: "the runner refuses: ... a command of an operation whose
    program is a tool not found (the command row), whether no folder of the search list holds it at the runner's search or
    the file the runner found is gone as it starts it, so that no child is created (the owner's ruling, A109)".

    The fake host's program stands in one folder of the fixture's own that its settings name (`rowlib.program_folder`). A
    create whose look is the fake host's own request and whose send is a child (`rowlib.install_refused_send`), and a change
    (a C5) whose reads are that request and whose effect call is a child (`rowlib.install_change_looked_by_request`): in each
    the first child of the go is the one the operation's effect call starts. Two passes: the program taken out of that
    folder after the look, and its file removed as the runner starts it (at the runner's record `pre child`)."""

    PASSES = ("at the search", "as the runner starts it")

    def gone(self, m, where):
        folder = rowlib.program_folder(m)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        hook = None
        if where == "at the search":
            rowlib.take_program(folder)
        else:
            taken = []

            def hook(event):
                if not taken and event["stage"] == "pre" and event["op"] == "child" and event["subject"] == "fakehost":
                    taken.append(event["i"])
                    rowlib.take_program(folder)
                return False
        return looked, m.go(looked, kill=hook), folder

    def assertRefusedWithNoChild(self, m, went, op):
        from sun_core import texts
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
        self.assertIn("stopped: the runner refused the command: tool not found", went.lines, "not stopped on that refusal")
        self.assertIn("operation: %s" % op, went.lines)
        self.assertIn("the runner refused the command: tool not found", open(went.doc["forms"][0]).read(), "the form does not name it")
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "mid"], [], "a child was created")
        self.assertEqual(m.calls("fakehost"), [], "the fake recorded a start")

    def test_SEC3_A109_a_program_not_found_at_an_operation_is_a_refusal_at_the_search_and_where_its_file_is_gone_at_the_start(self):
        """SEC-3's test line: "A program not found at an operation: with the program removed from the search list after the
        look, the runner refuses a create's send at its search, the fake recording no start; the journal holds the start record
        and then the step record of the refusal, the run ends `stopped` on that refusal, its form naming it, and the next
        resume, the program put back, probes the create `not landed` and sends it once on his word; at a change's effect call,
        the same refusal ends the run `stopped` with the start record standing and no completion recorded. In a second pass the
        fixture's file system removes the file as the runner starts it: no child is created, and the journal, the ending and
        the next resume are the same; a fake that is started and then killed instead leaves the create outstanding (OP-6, OP-7)
        (the owner's ruling, A109)." """
        for where in self.PASSES:
            with self.subTest(where=where, operation="a create's send"):
                m = rowlib.install_refused_send(harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), "c" + where[:2]))
                looked, went, folder = self.gone(m, where)
                run = looked.doc["run"]
                self.assertRefusedWithNoChild(m, went, "C1")
                self.assertEqual([(r["kind"], r.get("step")) for r in m.journal(run) if r.get("op") == "C1"],
                                 [("start", None), ("step", "send-refused")],
                                 "the journal does not hold the start record and then the step record of the refusal")
                rowlib.put_program(folder)
                resumed = m.resume()
                self.assertEqual(resumed.ending, "complete", resumed.text)
                starts = [r for r in m.journal(run) if r.get("op") == "C1" and r["kind"] == "start"]
                self.assertEqual([r["probe"] for r in starts], ["ready", "not landed"], "the create was not probed `not landed`")
                self.assertEqual(len(m.calls("fakehost", "create")), 1, "the create was not sent once")
            with self.subTest(where=where, operation="a change's effect call"):
                m = rowlib.install_change_looked_by_request(harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), "h" + where[:2]))
                looked, went, folder = self.gone(m, where)
                run = looked.doc["run"]
                self.assertRefusedWithNoChild(m, went, "H1")
                h1 = [r for r in m.journal(run) if r.get("op") == "H1"]
                self.assertEqual([r["kind"] for r in h1 if r["kind"] != "step"], ["start"],
                                 "not the start record standing alone: a completion or a status was recorded")
                self.assertEqual(m.fake("fakehost", "state.json")["things"]["demo"]["state"], "active", "the change was made")
        with self.subTest(operation="a fake started and then killed"):
            m = rowlib.install_refused_send(harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), "died"))
            rowlib.program_folder(m)
            m.plan_fake("fakehost", {"command": "create", "nth": 1, "do": "die"})
            looked = m.look()
            went = m.go(looked)
            self.assertEqual(went.ending, "stopped", went.text)
            self.assertIn("stopped: an outstanding create", went.lines, "the start of a child that was then killed is a refusal")
            self.assertEqual(len(m.calls("fakehost", "create")), 1)
            self.assertEqual([r for r in m.journal(looked.doc["run"]) if r.get("step") == "send-refused"], [])


class AStartTheSystemRefusesAtAnOperation(harness.Case):
    """SEC-3's command row (batch 48, A114): "So too is a start of a command of an operation that the system refuses before the
    program runs, the file still there: the file not runnable, a program its first line names missing, a format the system
    cannot run, the working folder gone, or no process to be had, wherever the system's answer shows that the program never
    ran. Such a start creates no child of the program, whatever the system made for the start and ended before the program
    ran (the owner's ruling, A113)." Its refusals row: "a command of an operation whose start the system refuses before the
    program runs, the file still there, where the system's answer shows that the program never ran (the command row; the
    owner's ruling, A113)". The create of `rowlib.install_refused_send`, its program in a folder of the fixture's own; each
    cause planted after the look by `rowlib.refuse_start` (the row's working folder is the run directory)."""

    REFUSED = "the runner refused the command: start refused"

    def test_SEC3_A113_a_start_the_system_refuses_at_a_creates_send_ends_stopped_and_the_next_resume_probes_not_landed_and_sends_once(self):
        """SEC-3's test line (batch 48B, A115): "A start the system refuses with the file still there, in five passes after the
        look: the fixture's file made not runnable, its first line made to name a program in no folder, its bytes replaced by
        bytes of no format the system can run with no first line naming a program, the row's working folder removed, and the
        fixture's system answering the start that no process can be had. At a create's send each ends the run `stopped` on
        the runner's refusal, the fake recording no start, the journal holding the start record and then the step record of
        the refusal, and the next resume, the cause put right, probes the create `not landed` and sends it once on his word;
        a start whose failure the fixture's system answers in words the runner cannot read as the program never having run
        leaves the create outstanding, and no later invocation under the same manifest sends it (OP-6, OP-7) (the owner's
        ruling, A113)." """
        from sun_core import texts
        for number, cause in enumerate(rowlib.START_CAUSES + (rowlib.UNREADABLE_START,)):
            with self.subTest(cause=cause):
                m = rowlib.install_refused_send(harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), "s%d" % number))
                folder = rowlib.program_folder(m)
                looked = m.look()
                self.assertEqual(looked.ending, "preview", looked.text)
                run = looked.doc["run"]
                hook, put_right = rowlib.refuse_start(m, cause, os.path.join(folder, "fakehost"), m.facts.run_dir(run), "fakehost")
                went = m.go(looked, kill=hook)
                self.assertEqual(went.ending, "stopped", went.text)
                self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
                self.assertEqual(m.calls("fakehost"), [], "the fake recorded a start")
                self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "mid"], [], "a child was created")
                self.assertTrue([e for e in went.events if e["op"] == "child" and e["stage"] == "pre" and e["subject"] == "fakehost"],
                                "the runner did not come to start the child")
                c1 = [(r["kind"], r.get("step")) for r in m.journal(run) if r.get("op") == "C1"]
                if cause == rowlib.UNREADABLE_START:
                    self.assertEqual(c1, [("start", None)], "a start the runner cannot read as never ran wrote a refusal's record")
                    self.assertIn("stopped: an outstanding create", went.lines, went.text)
                    put_right()
                    for turn in range(3):
                        again = m.resume()
                        self.assertIn("stopped: an outstanding create", again.lines, "turn %d" % turn)
                        self.assertEqual(m.calls("fakehost", "create"), [], "a later invocation under the same manifest sent it")
                    continue
                self.assertIn("stopped: " + self.REFUSED, went.lines, "not stopped on the runner's refusal")
                self.assertIn(self.REFUSED, open(went.doc["forms"][0]).read(), "the form does not name the refusal")
                self.assertEqual(c1, [("start", None), ("step", "send-refused")],
                                 "the journal does not hold the start record and then the step record of the refusal")
                put_right()
                resumed = m.resume()
                self.assertEqual(resumed.ending, "complete", resumed.text)
                starts = [r for r in m.journal(run) if r.get("op") == "C1" and r["kind"] == "start"]
                self.assertEqual([r["probe"] for r in starts], ["ready", "not landed"], "the create was not probed `not landed`")
                self.assertEqual(len(m.calls("fakehost", "create")), 1, "the create was not sent once")

    def test_SEC3_A117_a_start_refused_for_a_cause_none_of_the_five_an_argument_list_too_long_writes_no_refusals_record_and_the_create_stays_outstanding(self):
        """SEC-3's command row (batch 49, A117): "So too is a start of a command of an operation that the system refuses before
        the program runs, the file still there, for one of these five causes and for no other ... A start the system refuses
        for any cause that is none of the five, a start whose answer the runner cannot read as one in which the program never
        ran, and a start that creates a child, are no refusal, however that child ends: they stay as OP-6 has a killed child,
        a create there outstanding (OP-7; A109, A113, A116)." Its test line: "So does a start the fixture's system refuses at a
        create's send for a cause that is none of the five, an argument list too long: no step record of a refusal is written,
        the create is outstanding, and no later invocation under the same manifest sends it (A113, A116)." The fixture's system
        answers E2BIG naming the very file the runner started, a file still there: the shape of the five's own answers."""
        from sun_core import texts
        m = rowlib.install_refused_send(harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), "e2big"))
        folder = rowlib.program_folder(m)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        hook, put_right = rowlib.refuse_start(m, rowlib.ARG_LIST_TOO_LONG, os.path.join(folder, "fakehost"), m.facts.run_dir(run),
                                              "fakehost")
        went = m.go(looked, kill=hook)
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
        self.assertTrue([e for e in went.events if e["op"] == "child" and e["stage"] == "pre" and e["subject"] == "fakehost"],
                        "the runner did not come to start the child")
        self.assertEqual(m.calls("fakehost"), [], "the fixture's system started the fake")
        self.assertNotIn("the runner refused the command", went.text, "a cause none of the five was named as a refusal")
        self.assertIn("stopped: an outstanding create", went.lines, went.text)
        c1 = [(r["kind"], r.get("step")) for r in m.journal(run) if r.get("op") == "C1"]
        self.assertEqual(c1, [("start", None)], "a step record of a refusal was written for a cause none of the five")
        put_right()
        for turn in range(3):
            again = m.resume()
            self.assertIn("stopped: an outstanding create", again.lines, "turn %d: %s" % (turn, again.text))
            self.assertNotIn("the runner refused the command", again.text)
            self.assertEqual(m.calls("fakehost", "create"), [], "a later invocation under the same manifest sent it")
        self.assertEqual([(r["kind"], r.get("step")) for r in m.journal(run) if r.get("op") == "C1"], [("start", None)])


class AStartTheSystemRefusesAtAChange(harness.Case):
    """SEC-3's refusals row: "A refused command met after the operation's start record, at its effect call or at its
    after-check, leaves the operation as that record left it: no completion is recorded, the run ends `stopped` on that
    refusal, its form naming it, and the next invocation's probe reads the world again, as OP-6 has it for an effect call that
    fails and an after-check that does not show the after-state." Its test line (batch 49, A117): "The five at a change: at a
    change's effect call, and in another pass at a change's after-check once its effect call has been made, each of the five
    ends the run `stopped` on the runner's refusal with the start record standing and no completion recorded, the form naming
    the refusal; with the cause put right, the next resume's probe answers `not landed` after the refused effect call and
    `landed` after the refused after-check (the refusals row; A113, A116)."

    The change of `rowlib.install_change_checked_by_child`: a C5 whose probe reads are the fake host's own request (no child),
    whose effect call, `fakehost set`, is the go's first child, and whose after-check's read, `fakehost get`, is its second;
    the fake host's program in a folder of the fixture's own (`rowlib.program_folder`); each cause planted after the look, for
    the first start (`rowlib.refuse_start`) or for the second (`rowlib.refuse_start_at`). The row's working folder is the run
    directory."""

    REFUSED = "the runner refused the command: start refused"

    def went(self, label, cause, nth):
        m = rowlib.install_change_checked_by_child(harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label))
        folder = rowlib.program_folder(m)
        looked = m.look()
        self.assertEqual(looked.ending, "preview", looked.text)
        run = looked.doc["run"]
        hook, put_right = rowlib.refuse_start_at(m, cause, os.path.join(folder, "fakehost"), m.facts.run_dir(run), "fakehost", nth)
        return m, run, m.go(looked, kill=hook), put_right

    def of_h1(self, m, run):
        return [r for r in m.journal(run) if r.get("op") == "H1"]

    def assert_stopped_on_the_refusal(self, m, run, went):
        from sun_core import texts
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
        self.assertIn("stopped: " + self.REFUSED, went.lines, "not stopped on the runner's refusal")
        self.assertIn("operation: H1", went.lines)
        self.assertIn(self.REFUSED, open(went.doc["forms"][0]).read(), "the form does not name the refusal")
        h1 = self.of_h1(m, run)
        self.assertEqual(len([r for r in h1 if r["kind"] == "start"]), 1, "the start record does not stand")
        self.assertEqual([r for r in h1 if r["kind"] in ("completion", "status")], [], "a completion or a status was recorded")

    def thing_state(self, m):
        return m.fake("fakehost", "state.json")["things"]["demo"]["state"]

    def test_SEC3_A117_each_of_the_five_at_a_changes_effect_call_ends_stopped_the_start_record_standing_and_the_next_probe_answers_not_landed(self):
        for number, cause in enumerate(rowlib.START_CAUSES):
            with self.subTest(cause=cause):
                m, run, went, put_right = self.went("e%d" % number, cause, 1)
                self.assert_stopped_on_the_refusal(m, run, went)
                self.assertEqual(m.calls("fakehost"), [], "the fake recorded a start: the effect call was made")
                self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "mid"], [], "a child was created")
                self.assertEqual(self.thing_state(m), "active", "the change was made")
                put_right()
                resumed = m.resume()
                self.assertEqual(resumed.ending, "complete", resumed.text)
                starts = [r for r in self.of_h1(m, run) if r["kind"] == "start"]
                self.assertEqual([r["probe"] for r in starts], ["ready", "not landed"], "the next probe did not answer `not landed`")
                self.assertEqual([r["kind"] for r in self.of_h1(m, run) if r["kind"] == "completion"], ["completion"])
                self.assertEqual(len(m.calls("fakehost", "set")), 1, "the effect call was not made once")
                self.assertEqual(self.thing_state(m), "paused")

    def test_SEC3_A117_each_of_the_five_at_a_changes_after_check_ends_stopped_the_start_record_standing_and_the_next_probe_answers_landed(self):
        for number, cause in enumerate(rowlib.START_CAUSES):
            with self.subTest(cause=cause):
                m, run, went, put_right = self.went("a%d" % number, cause, 2)
                self.assert_stopped_on_the_refusal(m, run, went)
                self.assertEqual([c["argv"][0] for c in m.calls("fakehost")], ["set"], "not the effect call alone")
                self.assertEqual(self.thing_state(m), "paused", "the effect call was not made")
                children = [e for e in went.events if e["op"] == "child" and e["subject"] == "fakehost"]
                self.assertEqual([e["stage"] for e in children], ["pre", "mid", "post", "pre", "post"],
                                 "not the effect call's child and then a start of the after-check's that created none")
                put_right()
                resumed = m.resume()
                self.assertEqual(resumed.ending, "complete", resumed.text)
                h1 = self.of_h1(m, run)
                self.assertEqual(len([r for r in h1 if r["kind"] == "start"]), 1, "a new start record: the probe did not answer `landed`")
                self.assertEqual([r.get("status") for r in h1 if r["kind"] == "status"], ["not proven"],
                                 "not OP-6's `landed` cell for a change that is no swap")
                self.assertEqual(len(m.calls("fakehost", "set")), 1, "the effect call was made again")


class TheShortcutChecksZshAtAProbe(harness.Case):
    """SEC-3's command row (batch 54, A125): "At an operation's probe at run time, where the check is the read of that
    operation's before-test and the shell is that operation's command (A94), no zsh in a system folder is no failed read and
    answers no `unreadable`: it is a program that operation needs missing when the runner looks for it, the runner's refusal
    of a command of an operation, and so is a zsh that the runner found in a system folder and that is gone as it starts it,
    so that no child is created (below; the owner's ruling, A109). In each the operation is not started, no start record is
    written and no effect call is made, and the run ends `stopped` on that refusal (the refusals row), its form naming it."
    and, the shell at a probe being that operation's command (A94, A112, A115), "So too is a start of a command of an
    operation that the system refuses before the program runs, the file still there". The fixture's one system folder is its own (`rowlib.zsh_system_folder`), its zsh a file a test may change
    or take away; the shortcut check's working folder is the one its declaration names, his home. The look reads the name
    free; each pass is planted after the look; the go's first runner use is the shell at S1's probe, the read of a
    shortcut's add's before-test (the fake host's identity read none)."""

    def machine_for(self, label):
        m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
        providers = rowlib.providers()
        providers["fakehost"]["identity"] = rowlib.NONE
        rowlib.install(m, rowlib.lane("sunrise", [rowlib.swap_add("S1")]), providers=providers)
        m.put("shortcuts.txt", "alias other\n")
        zsh = rowlib.zsh_system_folder(m)
        return m, zsh

    def shells(self, m):
        return len(m.fake("zsh", "calls.jsonl", []) or [])

    def go_after(self, label, plant):
        """The look, then `plant(machine, zsh, home)` (which returns a hook or None), then the go. Returns the facts a pass
        asserts."""
        m, zsh = self.machine_for(label)
        looked = m.look(inputs=m.inputs(description="a plain project"))
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertEqual(self.shells(m), 1, "the look did not ask the shell")
        before = open(m.path("shortcuts.txt"), "rb").read()
        hook = plant(m, zsh, m.home)
        went = m.go(looked, kill=hook)
        journal = m.journal(looked.doc["run"])
        return m, looked, went, journal, before

    def assert_no_add(self, m, went, journal, before):
        from sun_core import texts
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
        self.assertTrue([r for r in journal if r["kind"] == "open" and r.get("word") == "go"], "the go is not on record")
        self.assertEqual([r for r in journal if r.get("op") == "S1" and r["kind"] in ("start", "completion", "status")], [],
                         "the add was started, or given a status")
        self.assertEqual(self.shells(m), 1, "the shortcut check's shell recorded a start at the probe")
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "mid"], [], "a child was created")
        self.assertEqual(open(m.path("shortcuts.txt"), "rb").read(), before, "an effect was made")

    def test_SEC3_A125_with_no_zsh_in_a_system_folder_after_the_look_the_check_at_the_probe_starts_no_shell_and_the_run_ends_stopped_on_the_runners_refusal(self):
        """SEC-3's command row (batch 54, A125): "At an operation's probe at run time, where the check is the read of that
        operation's before-test and the shell is that operation's command (A94), no zsh in a system folder is no failed read
        and answers no `unreadable`: it is a program that operation needs missing when the runner looks for it, the runner's
        refusal of a command of an operation ... In each the operation is not started, no start record is written and no
        effect call is made, and the run ends `stopped` on that refusal (the refusals row), its form naming it." Its test
        line: "At run time, with the zsh of the fixture's system folder removed after the look, the shortcut check at the
        probe of a shortcut's add starts no shell, and the run ends `stopped` on the runner's refusal, the add not started, no
        start record of it written and no effect call made, the form naming the refusal". It replaces part G9's test of the
        frame before batch 54, where the probe answered `unreadable`."""
        m, looked, went, journal, before = self.go_after("no zsh", lambda m, zsh, home: os.remove(zsh))
        self.assert_no_add(m, went, journal, before)
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "pre"], [], "a shell was started")
        refused = "the runner refused the command: tool not found"
        self.assertIn("stopped: " + refused, went.lines, "not stopped on the runner's refusal")
        self.assertIn("operation: S1", went.lines)
        self.assertIn(refused, open(went.doc["forms"][0]).read(), "the form does not name the refusal")
        self.assertNotIn("stopped: unreadable", went.lines, "met as a failed read, not as the runner's refusal")

    def test_SEC3_A112_A113_a_zsh_gone_as_the_runner_starts_it_and_a_start_of_it_the_system_refuses_end_the_run_stopped_on_the_refusal(self):
        """SEC-3's test line: "in a second pass the fixture's file system removes that zsh as the runner starts it, no child is
        created, and the run ends `stopped` on the runner's refusal, the add not started, no start record of it written and
        no effect call made, the form naming the refusal (the owner's ruling, A109). In five more passes, after the look, a
        start of that zsh the system refuses with the file still there: the zsh made not runnable, its first line made to
        name a program in no folder, its bytes replaced by bytes of no format the system can run with no first line naming a
        program, the working folder the shortcut check's declaration names removed, and the fixture's system answering the
        start that no process can be had; in each no child is created, the shortcut check's shell records no start, and the
        run ends `stopped` on the runner's refusal, the add not started, no start record of it written and no effect call
        made, the form naming the refusal (the owner's ruling, A113)." """
        def gone_at_start(m, zsh, home):
            done = []

            def hook(event):
                if not done and event["stage"] == "pre" and event["op"] == "child" and event["subject"] == "zsh":
                    done.append(event["i"])
                    os.remove(zsh)
                return False
            return hook

        def cause_of(cause):
            return lambda m, zsh, home: rowlib.refuse_start(m, cause, zsh, home, "zsh")[0]
        passes = [("the zsh gone as the runner starts it", gone_at_start, "tool not found")]
        passes += [(cause, cause_of(cause), "start refused") for cause in rowlib.START_CAUSES]
        for number, (label, plant, word) in enumerate(passes):
            with self.subTest(cause=label):
                m, looked, went, journal, before = self.go_after("z%d" % number, plant)
                self.assert_no_add(m, went, journal, before)
                refused = "the runner refused the command: " + word
                self.assertIn("stopped: " + refused, went.lines, "not stopped on the runner's refusal")
                self.assertIn("operation: S1", went.lines)
                self.assertIn(refused, open(went.doc["forms"][0]).read(), "the form does not name the refusal")
                self.assertTrue([e for e in went.events if e["op"] == "child" and e["stage"] == "pre" and e["subject"] == "zsh"],
                                "the runner did not come to start the shell")
                self.assertTrue(os.path.isdir(m.home), "the fixture's home is not back")


class TheShortcutChecksZshBeyondTheProbe(harness.Case):
    """SEC-3's command row (batches 49 and 55, A117, A126): "The shell is a command of that operation wherever the check is
    made for it, at that operation's after-check and at an owner step's read as at its probe ... There too no zsh in a
    system folder is no failed read: it is a program that operation needs missing when the runner looks for it, the
    runner's refusal (the owner's ruling, A109); and so is a zsh gone as the runner starts it, or a start of it the system
    refuses for one of the five causes below. Each ends as the refusals row has it for that place: at an after-check, the
    start record standing, no completion recorded and the run `stopped` on that refusal; at an owner step's read, the step
    not shown, no `waiting` record written and the run `stopped` on that refusal (A109, A113, A116)."

    Two fixtures, each with the fixture's one system folder its own (`rowlib.zsh_system_folder`): a change by C3 (a removal of
    a shortcut's line) whose after-check makes the shortcut check, its probe and its effect making no runner use; and an owner
    step in read-back mode whose read is the shortcut check, first reached at the go, with a build after it in the same phase
    that needs nothing of it, the effect a run not stopped would make. The fake host's identity read is none, so that the
    shell is the go's first child. Each pass is planted after the look."""

    STEP = TheRefusalOutsideAProbe.STEP

    def machine_for(self, label, rows, shortcuts=None, zshrc=None):
        m = harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label)
        providers = rowlib.providers()
        providers["fakehost"]["identity"] = rowlib.NONE
        rowlib.install(m, rowlib.lane("sunrise", rows), providers=providers)
        if shortcuts is not None:
            m.put("shortcuts.txt", shortcuts)
        if zshrc is not None:
            m.put(".zshrc", zshrc)
        zsh = rowlib.zsh_system_folder(m)
        return m, zsh

    def after_check_row(self):
        removal = rowlib.swap_add("S1")["way_back"]["reverse"]
        removal.update(id="S1", after_check=removal["after_check"] + [{"id": "name", "read": "name-free", "name": rowlib.NAME}])
        return removal

    def owner_rows(self):
        step = rowlib.owner_step("O1", mode="read back", after_test=[{"id": "name", "read": "name-free", "name": rowlib.NAME}],
                                 commands=rowlib.NONE)
        return [step, rowlib.build("B1")]

    def shells(self, m):
        return len(m.fake("zsh", "calls.jsonl", []) or [])

    def gone_at_start(self, zsh):
        done = []

        def hook(event):
            if not done and event["stage"] == "pre" and event["op"] == "child" and event["subject"] == "zsh":
                done.append(event["i"])
                os.remove(zsh)
            return False
        return hook

    def passes(self):
        """(label, plant(m, zsh) -> hook, put_right(m), the runner's word): the zsh removed as the runner starts it, and the
        zsh made not runnable (SEC-3's test line, "in the same two passes")."""
        def not_runnable(m, zsh):
            os.chmod(zsh, 0o644)
            return None
        return [("the zsh removed as the runner starts it", lambda m, zsh: self.gone_at_start(zsh), lambda m: rowlib.zsh_system_folder(m),
                 "tool not found"),
                ("the zsh made not runnable", not_runnable, lambda m: os.chmod(m.system_folders[0] + "/zsh", 0o755), "start refused")]

    def assert_no_child(self, went):
        from sun_core import texts
        self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "mid"], [], "a child was created")

    # ---- at an after-check -------------------------------------------------------------------------------------------
    def test_SEC3_A117_at_a_changes_after_check_a_zsh_gone_as_the_runner_starts_it_or_not_runnable_ends_stopped_on_the_refusal_the_start_record_standing(self):
        """SEC-3's test line: "Beyond the probe: a fixture row whose after-check makes the shortcut check, the zsh removed as
        the runner starts it, and in a second pass made not runnable, ends the run `stopped` on the runner's refusal with no
        child created, the start record standing and no completion recorded, the form naming the refusal"."""
        for number, (label, plant, put_right, word) in enumerate(self.passes()):
            with self.subTest(cause=label):
                m, zsh = self.machine_for("ac%d" % number, [self.after_check_row()], shortcuts="alias other\nalias demo\n")
                looked = m.look(inputs=m.inputs(description="a plain project"))
                self.assertEqual(looked.ending, "preview", looked.text)
                self.assertEqual(self.shells(m), 0, "the look asked the shell")
                went = m.go(looked, kill=plant(m, zsh))
                run = looked.doc["run"]
                self.assertEqual(went.ending, "stopped", went.text)
                self.assert_no_child(went)
                refused = "the runner refused the command: " + word
                self.assertIn("stopped: " + refused, went.lines, "not stopped on the runner's refusal")
                self.assertIn("operation: S1", went.lines)
                self.assertIn(refused, open(went.doc["forms"][0]).read(), "the form does not name the refusal")
                self.assertTrue([e for e in went.events if e["op"] == "child" and e["stage"] == "pre" and e["subject"] == "zsh"],
                                "the runner did not come to start the shell")
                s1 = [r for r in m.journal(run) if r.get("op") == "S1"]
                self.assertEqual(len([r for r in s1 if r["kind"] == "start"]), 1, "the start record does not stand")
                self.assertEqual([r for r in s1 if r["kind"] in ("completion", "status")], [], "a completion or a status was recorded")
                self.assertEqual(open(m.path("shortcuts.txt")).read(), "alias other\n", "the effect call was not made")
                self.assertEqual(self.shells(m), 0, "the shell recorded a start")

    # ---- at an owner step's read, first reached ------------------------------------------------------------------------
    def test_SEC3_A117_at_an_owner_steps_read_first_reached_a_zsh_gone_or_not_runnable_ends_stopped_on_the_refusal_with_the_step_in_no_form(self):
        """SEC-3's test line: "and a fixture owner step whose read makes the shortcut check when the step is first reached, in
        the same two passes, ends the run `stopped` on the runner's refusal with the step in no form and no `waiting` record
        written (A109, A113, A116)."""
        for number, (label, plant, put_right, word) in enumerate(self.passes()):
            with self.subTest(cause=label):
                m, zsh = self.machine_for("os%d" % number, self.owner_rows(), zshrc="alias demo=true\n")
                looked = m.look(inputs=m.inputs(description="a plain project"))
                self.assertEqual(looked.ending, "preview", looked.text)
                shells = self.shells(m)
                went = m.go(looked, kill=plant(m, zsh))
                run = looked.doc["run"]
                self.assertEqual(went.ending, "stopped", went.text)
                self.assert_no_child(went)
                refused = "the runner refused the command: " + word
                self.assertIn("stopped: " + refused, went.lines, "not stopped on the runner's refusal")
                self.assertIn("operation: O1", went.lines)
                form = open(went.doc["forms"][0]).read()
                self.assertIn(refused, form, "the form does not name the refusal")
                self.assertNotIn(self.STEP, form, "the step is shown in the form")
                self.assertNotIn(self.STEP, went.text, "the step is shown in the output")
                self.assertEqual([r for r in m.journal(run) if r.get("op") == "O1" and r["kind"] in ("waiting", "status")], [],
                                 "a `waiting` record or a status was written")
                self.assertEqual([r for r in m.journal(run) if r.get("op") == "B1"], [], "the build after it was started")
                self.assertFalse(os.path.exists(os.path.join(m.dev, "demo")), "an effect was made")
                self.assertEqual(self.shells(m), shells, "the shell recorded a start")

    # ---- with no zsh in a system folder, beyond the probe (A126) ----------------------------------------------------------
    def test_SEC3_A126_with_no_zsh_in_a_system_folder_a_changes_after_check_starts_no_shell_ends_stopped_on_the_runners_refusal_and_the_next_resume_reads_again(self):
        """SEC-3's command row (batch 55, A126): "There too no zsh in a system folder is no failed read: it is a program that
        operation needs missing when the runner looks for it, the runner's refusal (the owner's ruling, A109) ... Each ends as
        the refusals row has it for that place: at an after-check, the start record standing, no completion recorded and the
        run `stopped` on that refusal". Its test line: "With the zsh of the fixture's system folder removed after the look,
        the same fixture row's after-check starts no shell and ends the run `stopped` on the runner's refusal, the start
        record standing, no completion recorded and the form naming the refusal, and with the zsh put back the next resume's
        probe reads the world again". It replaces part G10's test of the frame before batch 55, where it was a failed read."""
        m, zsh = self.machine_for("acnz", [self.after_check_row()], shortcuts="alias other\nalias demo\n")
        looked = m.look(inputs=m.inputs(description="a plain project"))
        self.assertEqual(looked.ending, "preview", looked.text)
        os.remove(zsh)
        went = m.go(looked)
        run = looked.doc["run"]
        self.assertEqual(went.ending, "stopped", went.text)
        self.assert_no_child(went)
        refused = "the runner refused the command: tool not found"
        self.assertIn("stopped: " + refused, went.lines, "not stopped on the runner's refusal")
        self.assertIn("operation: S1", went.lines)
        self.assertIn(refused, open(went.doc["forms"][0]).read(), "the form does not name the refusal")
        self.assertNotIn("stopped: the after-check does not show the after-state", went.lines, "met as a failed read")
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "pre"], [], "a shell was started")
        s1 = [r for r in m.journal(run) if r.get("op") == "S1"]
        self.assertEqual(len([r for r in s1 if r["kind"] == "start"]), 1, "the start record does not stand")
        self.assertEqual([r for r in s1 if r["kind"] in ("completion", "status")], [], "a completion or a status was recorded")
        self.assertEqual(open(m.path("shortcuts.txt")).read(), "alias other\n", "the effect call was not made")
        rowlib.zsh_system_folder(m)                            # the zsh put back
        resumed = m.resume()
        self.assertEqual(resumed.ending, "complete", resumed.text)
        s1 = [r for r in m.journal(run) if r.get("op") == "S1"]
        self.assertEqual(len([r for r in s1 if r["kind"] == "start"]), 1, "a new start record: the probe did not answer `landed`")
        self.assertEqual([c.get("ground") for c in s1 if c["kind"] == "completion"], ["b"], "not completed on the `landed` row's ground")
        self.assertEqual(self.shells(m), 1, "the after-check was not made again by the next resume")

    def test_SEC3_A126_with_no_zsh_in_a_system_folder_an_owner_steps_read_first_reached_starts_no_shell_and_ends_stopped_on_the_runners_refusal_with_the_step_in_no_form(self):
        """SEC-3's command row (batch 55, A126): "There too no zsh in a system folder is no failed read ... at an owner step's
        read, the step not shown, no `waiting` record written and the run `stopped` on that refusal". Its test line: "and the
        same fixture owner step starts no shell and ends the run `stopped` on the runner's refusal, the step in no form, no
        `waiting` record written and no effect call made (the owner's ruling, A109)." It replaces part G10's test of the frame
        before batch 55, where it was a failed read."""
        m, zsh = self.machine_for("osnz", self.owner_rows(), zshrc="alias demo=true\n")
        looked = m.look(inputs=m.inputs(description="a plain project"))
        self.assertEqual(looked.ending, "preview", looked.text)
        os.remove(zsh)
        went = m.go(looked)
        run = looked.doc["run"]
        self.assertEqual(went.ending, "stopped", went.text)
        self.assert_no_child(went)
        refused = "the runner refused the command: tool not found"
        self.assertIn("stopped: " + refused, went.lines, "not stopped on the runner's refusal")
        self.assertNotIn("stopped: unreadable", went.lines, "met as a failed read")
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "pre"], [], "a shell was started")
        self.assertIn("operation: O1", went.lines)
        form = open(went.doc["forms"][0]).read()
        self.assertIn(refused, form, "the form does not name the refusal")
        self.assertNotIn(self.STEP, form, "the step is shown in the form")
        self.assertNotIn(self.STEP, went.text, "the step is shown in the output")
        self.assertEqual([r for r in m.journal(run) if r.get("op") == "O1" and r["kind"] in ("waiting", "status")], [],
                         "a `waiting` record or a status was written")
        self.assertEqual([r for r in m.journal(run) if r.get("op") == "B1"], [], "the build after it was started")
        self.assertFalse(os.path.exists(os.path.join(m.dev, "demo")), "an effect was made")
        self.assertEqual(m.summon("status").ending, "stopped", "the run does not stand stopped")

    def test_SEC3_A126_with_no_zsh_in_a_system_folder_a_waiting_steps_read_at_a_resume_on_his_word_and_at_a_summons_with_no_word_ends_stopped_on_the_runners_refusal(self):
        """SEC-3's command row (batch 55, A126) names "an owner step's read" without limit, and its refusals row has a read a
        later invocation makes at its start, "OP-9's reads among them", end the run `stopped` on that refusal, "a summons
        with no word too". No test line names this place; the same code reaches it, so it is shown here (part G12's
        report). The owner step O1 waits, its name taken by an alias of the fixture's `.zshrc`; the zsh of the fixture's
        system folder is then removed, and the waiting step's read is made again at the start of a resume on his current
        word and, in a second pass, of a summons with no word."""
        for summons in ("a resume on his current word", "a summons with no word"):
            with self.subTest(summons=summons):
                m, zsh = self.machine_for("rr-%s" % summons[2:8], self.owner_rows(), zshrc="alias demo=true\n")
                looked, went = m.started(inputs=m.inputs(description="a plain project"))
                self.assertEqual(went.ending, "waiting", went.text)
                self.assertIn(self.STEP, open(went.doc["forms"][0]).read(), "the fixture's premise: the step is shown while it waits")
                run = looked.doc["run"]
                position = m.summon("status").doc["position"]
                before = m.statuses(run)
                os.remove(zsh)
                if summons == "a summons with no word":
                    ended = m.summon("status")
                else:
                    ended = m.summon("resume", "demo", "--position", position, "--word", "go on")
                self.assertEqual(ended.ending, "stopped", ended.text)
                self.assert_no_child(ended)
                refused = "the runner refused the command: tool not found"
                self.assertIn("stopped: " + refused, ended.lines, "not stopped on the runner's refusal")
                self.assertNotIn("stopped: unreadable", ended.lines, "met as a failed read")
                self.assertNotIn("re-plan is needed", ended.text, "a re-plan was asked for")
                self.assertEqual([e for e in ended.events if e["op"] == "child" and e["stage"] == "pre"], [], "a shell was started")
                form = open(ended.doc["forms"][0]).read()
                self.assertIn(refused, form, "the form does not name the refusal")
                self.assertNotIn(self.STEP, form, "the step is shown in the form")
                self.assertNotIn(self.STEP, ended.text, "the step is shown in the output")
                self.assertEqual(m.statuses(run), before, "an effect was applied, or a status recorded")


if __name__ == "__main__":
    unittest.main()
