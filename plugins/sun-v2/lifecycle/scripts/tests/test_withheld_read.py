"""The withheld read (the frame's SEC-12, "The withheld read, and what a refusal prints"; RUN-1, RUN-2,
RUN-3, RUN-12; the reviewer's D8 closing rule, first half).

The code under test is one module, `sun_core/withheld.py`. Every test here carries one assertion in
common, `self.read_first(...)`: the withheld read's reads stand before the first byte of output, shown
from the recording file system's own list of acts and not from the order of the code.

Fixtures: `EVIDENCE/author-9.md` section 6 (D8's first sequence; every early path),
`EVIDENCE/author-9b.md` section 3 (the cut that breaks the chain; another run's directory),
`EVIDENCE/author-9d.md` section 3 (PS15). The states are built by `fab.py` with the core's own
writers; `test_secrets_end_to_end.py` reaches the same states through a fake that returns the value
in a secret field.
"""
import json
import os
import unittest

import harness
import fab
from sun_core import texts



def look(machine, name, **kw):
    return machine.run("look", "--kind", "sunrise", "--name", name, "--inputs", machine.inputs(), **kw)


class WithheldReadCase(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.m = fab.lane_min(self.machine())

    # the one assertion every test carries
    def read_first(self, result, runs, locks=()):
        events = result.events
        first = next((e["i"] for e in events if e["stage"] == "output"), None)
        self.assertIsNotNone(first, "the invocation printed nothing")
        before = [e["subject"] for e in events if e["stage"] == "read" and e["i"] < first]
        facts = self.m.facts
        if os.path.exists(facts.open_runs_file):
            self.assertIn(facts.open_runs_file, before, "the record of open runs was not read before the first byte")
        for name in locks:
            self.assertIn(os.path.join(facts.locks_dir, name), before, "a lock's record was not read before the first byte")
        for run in runs:
            journal = os.path.join(facts.run_dir(run), "journal.jsonl")
            self.assertIn(journal, before, "run %s: its journal was not read before the first byte" % run)
            for record in self.m.journal(run):
                if record["kind"] != "disproof":
                    continue
                rests = record["rests"]
                where = (os.path.join(facts.run_dir(run), "protected", rests["protected"]["record"]) if "protected" in rests
                         else os.path.join(facts.run_dir(run), rests["content"]["file"]))
                self.assertIn(where, before, "run %s: a disproof record's value was not read before the first byte" % run)
        # the withheld read is the first act: nothing of the machine is read before the tool's own folder
        reads = [e["subject"] for e in events if e["stage"] == "read"]
        if reads:
            self.assertTrue(reads[0].startswith(facts.tool_home), "the first read was not of the tool's own folder: %s" % reads[0])
        # and it writes nothing: no write of any kind stands before the first byte on a refused path
        return before

    def two_runs(self, caught=None):
        """Two open runs: `demo`, which has caught `caught` (its own id when None), and `plain`."""
        first = fab.open_run(self.m, "demo")
        second = fab.open_run(self.m, "plain")
        value = first if caught is None else caught
        fab.catch(self.m, first, value)
        return first, second, value


class FirstAct(WithheldReadCase):
    def test_SEC12_withheld_read_stands_before_first_byte_on_a_failed_vault_check(self):
        first, second, value = self.two_runs()
        os.rename(self.m.vault, self.m.vault + ".gone")
        before = self.m.snapshot()
        result = look(self.m, "demo")
        self.read_first(result, [first, second])
        self.assertEqual(result.code, 10)
        self.assertEqual(result.ending, "refused")
        self.assertEqual(result.lines, [texts.GATE["vault-missing"]])
        self.assertNowhere(first, result)
        self.assertEqual(self.m.snapshot(), before, "a failed gate changed the fixture home")

    def test_SEC12_withheld_read_writes_nothing_and_reads_only_the_tools_folder_and_run_directories(self):
        first, second, value = self.two_runs()
        os.remove(self.m.facts.keying_file)
        result = look(self.m, "demo")
        self.read_first(result, [first, second])
        first_out = next(e["i"] for e in result.events if e["stage"] == "output")
        early = [e for e in result.events if e["i"] < first_out]
        self.assertEqual([e for e in early if e["stage"] in ("pre", "mid", "post")], [], "something was written before the first byte")
        withheld = []
        for event in early:
            if event["stage"] == "read" and not event["subject"].startswith(self.m.facts.tool_home):
                break
            withheld.append(event)
        self.assertTrue(withheld)
        for event in withheld:
            self.assertTrue(event["subject"].startswith(self.m.facts.tool_home))

    def test_SEC12_withheld_values_are_no_entries_of_the_register_so_no_name_check_sees_them(self):
        # author-9.md section 9: a run that caught its own project's name is still reachable by that name
        run = fab.open_run(self.m, "demo")
        fab.catch(self.m, run, "demo")
        result = self.m.run("status", "--name", "demo")
        self.read_first(result, [run])
        self.assertNotEqual(result.lines, [texts.NAME_REFUSED], "a withheld-read value reached the name check")


class EarlyPaths(WithheldReadCase):
    """RUN-12's test line, "A caught value on each early path"; SEC-12's, "The early paths"."""

    def drive(self, path, run, name):
        m = self.m
        if path == "vault":
            os.rename(m.vault, m.vault + ".gone")
            try:
                return look(m, name), None
            finally:
                os.rename(m.vault + ".gone", m.vault)
        if path == "keying":
            saved = open(m.facts.keying_file).read()
            os.remove(m.facts.keying_file)
            try:
                return m.run("resume", "--name", name), "listed"
            finally:
                with open(m.facts.keying_file, "w") as fh:
                    fh.write(saved)
                os.chmod(m.facts.keying_file, 0o600)
        if path == "name":
            token = harness.canary("token")
            return look(m, token, env={"FAKEHOST_TOKEN": token}), None
        if path == "first-lock":
            close = m.hold_lock(name, run)
            try:
                return look(m, name), "lock"
            finally:
                close()
        if path == "later-lock":
            m.put("dev/third-%s/names.txt" % name, name + "\n")
            close = m.hold_lock(name, run)
            try:
                return look(m, "third-" + name), "lock"
            finally:
                close()
        if path == "early-look":
            return look(m, name), "open"
        if path == "second-look":
            m.put("dev/third-%s/names.txt" % name, name + "\n")
            return look(m, "third-" + name), "open"
        if path == "rundir":
            inputs = os.path.join(m.facts.run_dir(run), "inputs.json")
            os.chmod(inputs, 0o644)
            try:
                return m.run("resume", "--name", name), "stopped"
            finally:
                os.chmod(inputs, 0o600)
        raise AssertionError(path)

    PATHS = ("vault", "keying", "name", "first-lock", "later-lock", "early-look", "second-look", "rundir")

    def check_paths(self, first, second, values, word_pass):
        for path in self.PATHS:
            with self.subTest(path=path, run="the run that caught"):
                result, names_run = self.drive(path, first, "demo")
                self.read_first(result, [first, second])
                self.assertEqual(result.code, 10)
                for value in values:
                    self.assertNowhere(value, result, "on the early path %s" % path)
                if word_pass or names_run:
                    self.assertIn(texts.WITHHELD, result.out, "the fixed words do not stand in the value's place on %s" % path)
                if names_run and not word_pass:
                    named = [n for n in (os.path.basename(self.m.facts.open_runs_file),) + tuple(self.m.lock_names())
                             if n in result.out]
                    self.assertTrue(named, "no file's name stands beside the fixed words on %s" % path)
            with self.subTest(path=path, run="a run that caught nothing"):
                result, names_run = self.drive(path, second, "plain")
                self.read_first(result, [first, second])
                for value in values:
                    self.assertNowhere(value, result, "on the early path %s" % path)
                if names_run and not word_pass:
                    self.assertIn(second, result.out, "a run that caught nothing is not named by its id on %s" % path)

    def test_RUN12_SEC12_a_caught_run_id_is_in_no_output_on_any_early_path(self):
        first, second, value = self.two_runs()
        self.check_paths(first, second, [value], word_pass=False)

    def test_RUN12_SEC12_a_caught_word_of_the_fixed_refusal_text_is_in_no_output_on_any_early_path(self):
        # one word of each early path's own fixed text: the gate's, a refusal's, a stop's
        words = ["failed", "Refused", "Stopped"]
        for word, text in zip(words, (texts.GATE["vault-missing"], texts.LOCK_HELD, texts.RUNDIR_STOP["permissions"])):
            self.assertIn(word, text)
            self.assertNotIn(word, texts.WITHHELD)
        self.assertIn("Refused", texts.NAME_REFUSED)
        self.assertIn("Refused", texts.RUN_OPEN)
        self.assertIn("failed", texts.GATE["keying-missing"])
        first, second, value = self.two_runs(caught=words[0])
        for word in words[1:]:
            fab.catch(self.m, first, word)
        self.check_paths(first, second, words, word_pass=True)

    def test_SEC12_a_usage_error_also_of_a_command_the_tool_does_not_know_prints_only_after_the_read_and_no_caught_word(self):
        # brief 5.5: every place that can print before a run's startup checks have passed stands under the read
        word = texts.USAGE.split()[0]
        self.assertNotIn(word, texts.WITHHELD)
        first, second, value = self.two_runs(caught=word)
        for argv in (["look"], ["look", "demo", "--no-such-flag"], ["no-such-command"], ["no-such-command", "demo"]):
            with self.subTest(argv=argv):
                result = self.m.run(*argv)
                self.assertEqual(result.code, 2)
                self.assertEqual(result.out, "")
                self.assertNotIn(word, result.err)
                self.assertIn(texts.WITHHELD, result.err)
                reads = [e["subject"] for e in result.events if e["stage"] == "read"]
                first_out = next(e["i"] for e in result.events if e["stage"] == "output")
                before = [e["subject"] for e in result.events if e["stage"] == "read" and e["i"] < first_out]
                self.assertIn(os.path.join(self.m.facts.run_dir(first), "journal.jsonl"), before, "the read did not stand before the usage line")
                self.assertEqual([e for e in result.events if e["stage"] in ("pre", "mid", "post")], [], "a usage error wrote something")

    def test_SEC12_a_disproof_record_cut_from_the_journal_breaks_the_chain_and_the_id_stays_withheld(self):
        first, second, value = self.two_runs()
        number = [r["n"] for r in self.m.journal(first) if r["kind"] == "disproof"][0]
        fab.cut_record(self.m, first, number)
        for path in ("keying", "first-lock", "later-lock", "early-look", "second-look", "rundir"):
            with self.subTest(path=path):
                result, _ = self.drive(path, first, "demo")
                first_out = next(e["i"] for e in result.events if e["stage"] == "output")
                before = [e["subject"] for e in result.events if e["stage"] == "read" and e["i"] < first_out]
                self.assertIn(os.path.join(self.m.facts.run_dir(first), "journal.jsonl"), before)
                self.assertNowhere(first, result, "after the cut, on %s" % path)
                self.assertIn(texts.WITHHELD, result.out)
                named = [n for n in (os.path.basename(self.m.facts.open_runs_file),) + tuple(self.m.lock_names()) if n in result.out]
                self.assertTrue(named, "the name of the file whose record holds the id does not stand in its place on %s" % path)

    def test_SEC12_an_unreadable_disproof_value_withholds_that_runs_id_on_every_path(self):
        first, second, value = self.two_runs(caught="something-else-entirely")
        record = [r for r in self.m.journal(first) if r["kind"] == "disproof"][0]
        os.remove(os.path.join(self.m.facts.run_dir(first), "protected", record["rests"]["protected"]["record"]))
        for path in ("keying", "first-lock", "early-look"):
            with self.subTest(path=path):
                result, _ = self.drive(path, first, "demo")
                self.assertNowhere(first, result, "with its disproof value unreadable, on %s" % path)
                self.assertIn(texts.WITHHELD, result.out)
        result = self.m.run("resume", "--name", "demo")
        self.assertEqual(result.ending, "stopped")
        self.assertEqual(result.lines[0], texts.RUNDIR_STOP["disproof-unreadable"])
        self.assertNowhere(first, result)

    def test_SEC12_where_the_fixed_words_of_withholding_hold_a_caught_value_nothing_is_written_in_that_place(self):
        first = fab.open_run(self.m, "demo")
        fab.catch(self.m, first, "withheld")
        self.assertIn("withheld", texts.WITHHELD)
        result, _ = self.drive("early-look", first, "demo")
        self.read_first(result, [first])
        self.assertNowhere("withheld", result)
        self.assertEqual(result.code, 10)


class AnotherRunsDirectory(WithheldReadCase):
    """SEC-12's test line, "Another run's directory" (author-9b.md section 3)."""

    def setUp(self):
        WithheldReadCase.setUp(self)
        self.second = fab.open_run(self.m, "plain")

    def passes(self):
        inputs = os.path.join(self.m.facts.run_dir(self.second), "inputs.json")
        yield "wider permissions", lambda: os.chmod(inputs, 0o644), True
        yield "a record cut from the middle", lambda: (os.chmod(inputs, 0o600), fab.cut_record(self.m, self.second, 1)), False

    def test_SEC12_a_failed_check_on_another_runs_directory_stops_nothing_at_the_gate(self):
        fab.open_run(self.m, "filler")  # so that the cut record stands between two that stay
        journal = fab.journal_of(self.m, self.second)
        journal.append(fab.quiet(self.m), "invocation-end", ending="stopped", reason={"kind": "fixture"})
        for label, damage, id_printable in self.passes():
            with self.subTest(damage=label):
                damage()
                result = look(self.m, "elsewhere")
                self.read_first(result, [self.second])
                self.assertEqual(result.ending, "preview", "a summons for another project did not pass the gate and go on")
                saved = open(self.m.facts.keying_file).read()
                os.remove(self.m.facts.keying_file)
                try:
                    refusal = look(self.m, "elsewhere")
                finally:
                    with open(self.m.facts.keying_file, "w") as fh:
                        fh.write(saved)
                    os.chmod(self.m.facts.keying_file, 0o600)
                self.read_first(refusal, [self.second])
                self.assertEqual(refusal.lines[0], texts.GATE["keying-missing"])
                if id_printable:
                    self.assertIn(self.second, refusal.out, "the directory's permissions entered into the whole read")
                else:
                    self.assertNowhere(self.second, refusal)
                    self.assertIn(texts.WITHHELD, refusal.out)
                    self.assertIn(os.path.basename(self.m.facts.open_runs_file), refusal.out)
                stopped = self.m.run("resume", "--name", "plain")
                self.assertEqual(stopped.ending, "stopped")
                cause = "permissions" if id_printable else "chain"
                self.assertTrue(stopped.lines and stopped.lines[0].startswith(texts.RUNDIR_STOP[cause]), stopped.lines)

    def test_SEC12_the_whole_read_does_not_ask_whether_the_directory_is_owner_only(self):
        os.chmod(self.m.facts.run_dir(self.second), 0o755)
        close = self.m.hold_lock("plain", self.second)
        try:
            result = look(self.m, "plain")
        finally:
            close()
        self.read_first(result, [self.second])
        self.assertEqual(result.lines, [texts.LOCK_HELD + self.second])


class KeyingRefusal(WithheldReadCase):
    """RUN-2's test line: "A caught id" (D8's first sequence) and "A caught file name" (PS15, A35)."""

    def remove_keying(self):
        self.saved = open(self.m.facts.keying_file).read()
        os.remove(self.m.facts.keying_file)

    def test_RUN2_D8_first_sequence_the_keying_refusal_lists_a_caught_id_by_its_files_name(self):
        for label in ("removed", "wider permissions"):
            with self.subTest(keying=label):
                m = self.m = fab.lane_min(harness.Machine(self.tmp, "home-" + label.split()[0], label))
                first, second, value = self.two_runs()
                if label == "removed":
                    os.remove(m.facts.keying_file)
                    head = texts.GATE["keying-missing"]
                else:
                    os.chmod(m.facts.keying_file, 0o644)
                    head = texts.GATE["keying-wide"]
                before = m.snapshot(os.path.join(".sun-v2", "runs"))
                result = m.run("resume", "--name", "demo")
                self.read_first(result, [first, second])
                self.assertEqual(result.code, 10)
                self.assertEqual(result.ending, "refused")
                self.assertEqual(result.lines[0], head)
                self.assertEqual(result.lines[1], texts.KEYING_PLACE + m.facts.keying_file)
                self.assertIn(texts.RUN_ON_RECORD + second, result.lines)
                self.assertNowhere(first, result)
                name = os.path.basename(m.facts.open_runs_file)
                self.assertIn(texts.RUN_ON_RECORD + texts.WITHHELD + texts.ID_IN_FILE + name, result.lines)
                self.assertIn(first, open(m.facts.open_runs_file).read(), "the file the output names does not hold that id")
                self.assertEqual(m.snapshot(os.path.join(".sun-v2", "runs")), before, "a run directory changed")
                if label == "removed":
                    self.assertFalse(os.path.exists(m.facts.keying_file), "a new keying value was made")

    def test_RUN2_PS15_where_neither_files_name_may_be_printed_a_fixed_line_and_the_place_apart(self):
        m = self.m
        first = fab.open_run(m, "demo")
        second = fab.open_run(m, "plain")
        fab.catch(m, first, first)
        fab.catch(m, first, m.fingerprint("demo"))      # the fingerprint that names its lock's file
        word = "open-runs"                               # a word that is part of the record's name
        self.assertIn(word, os.path.basename(m.facts.open_runs_file))
        fab.catch(m, first, word)
        close = m.hold_lock("demo", first)
        try:
            self.remove_keying()
            result = look(m, "elsewhere")
            self.read_first(result, [first, second], locks=m.lock_names())
            self.assertEqual(result.lines[0], texts.GATE["keying-missing"])
            self.assertIn(texts.RUN_ON_RECORD_UNNAMED, result.lines)
            self.assertIn(texts.LOCKS_PLACE + m.facts.locks_dir, result.lines)
            self.assertNotEqual(result.lines.index(texts.RUN_ON_RECORD_UNNAMED),
                                result.lines.index(texts.LOCKS_PLACE + m.facts.locks_dir))
            self.assertNotIn(os.sep, texts.RUN_ON_RECORD_UNNAMED)
            self.assertNowhere(first, result)
            self.assertNowhere(os.path.basename(m.facts.open_runs_file), result)
            for name in m.lock_names():
                self.assertNowhere(name, result)
            self.assertIn(texts.RUN_ON_RECORD + second, result.lines)
            # one more caught value, part of that place's path: the second line gives way, the first stands
            fab.catch(m, first, os.path.basename(m.facts.tool_home))
            again = look(m, "elsewhere")
            self.read_first(again, [first, second], locks=m.lock_names())
            self.assertIn(texts.RUN_ON_RECORD_UNNAMED, again.lines)
            self.assertNotIn(texts.LOCKS_PLACE + m.facts.locks_dir, again.lines)
            self.assertNowhere(m.facts.locks_dir, again)
            self.assertIn(texts.WITHHELD, again.lines)
        finally:
            close()

    def test_RUN2_A36_a_run_that_stands_in_only_one_file_is_named_by_that_one_files_name_or_not_at_all(self):
        m = self.m
        first = fab.open_run(m, "demo")
        fab.catch(m, first, first)
        self.remove_keying()
        only = look(m, "elsewhere")
        self.read_first(only, [first])
        name = os.path.basename(m.facts.open_runs_file)
        self.assertIn(texts.RUN_ON_RECORD + texts.WITHHELD + texts.ID_IN_FILE + name, only.lines)
        with open(m.facts.keying_file, "w") as fh:
            fh.write(self.saved)
        os.chmod(m.facts.keying_file, 0o600)
        fab.catch(m, first, "open-runs")
        os.remove(m.facts.keying_file)
        none = look(m, "elsewhere")
        self.read_first(none, [first])
        self.assertIn(texts.RUN_ON_RECORD_UNNAMED, none.lines)
        self.assertNowhere(name, none)
        self.assertNowhere(first, none)


class TheWaysOn(WithheldReadCase):
    """RUN-2 (the owner's ruling A43): "After its listing the refusal prints each of them as one fixed sentence of the
    tool's own, all three whichever of the two it found"; its test line, "The three sentences" and "A caught word in one
    of them"."""

    def refusal(self, label, caught=None):
        m = self.m = fab.lane_min(harness.Machine(self.tmp, "home-%s-%s" % (label.split()[0], caught or "none"), label))
        first, second, value = self.two_runs()
        if caught:
            fab.catch(m, second, caught)
        if label == "removed":
            os.remove(m.facts.keying_file)
        else:
            os.chmod(m.facts.keying_file, 0o644)
        before = m.snapshot()
        result = m.run("resume", "--name", "demo")
        self.read_first(result, [first, second])
        self.assertEqual(m.snapshot(), before, "%s: the tool took a step of the ways on" % label)
        return m, result, (first, second)

    def test_RUN2_A43_after_its_listing_the_refusal_prints_the_three_ways_on_the_same_in_both_passes(self):
        ways = {}
        for label in ("removed", "wider permissions"):
            with self.subTest(keying=label):
                m, result, runs = self.refusal(label)
                lines = result.lines
                self.assertEqual(lines[-3:], list(texts.WAYS_ON), "%s: the three sentences are not the refusal's last lines" % label)
                listed = [i for i, line in enumerate(lines) if line.startswith(texts.RUN_ON_RECORD)]
                self.assertTrue(listed)
                self.assertLess(max(listed), len(lines) - 3, "the three do not stand after the listing")
                names = [os.path.basename(m.facts.keying_file), os.path.basename(m.facts.open_runs_file)] + m.lock_names()
                for sentence in texts.WAYS_ON:
                    self.assertNotIn(os.sep, sentence)
                    for name in names + list(runs) + [m.home]:
                        self.assertNotIn(name, sentence, "a way on holds a file's name, a path or a run's id")
                ways[label] = lines[-3:]
        self.assertEqual(ways["removed"], ways["wider permissions"])

    def test_RUN2_A43_a_caught_word_of_the_second_sentence_gives_way_and_the_first_and_third_are_printed_whole(self):
        others = [texts.WAYS_ON[0], texts.WAYS_ON[2], texts.GATE["keying-missing"], texts.KEYING_PLACE, texts.RUN_ON_RECORD,
                  texts.ID_IN_FILE, texts.WITHHELD]
        word = next(w for w in texts.WAYS_ON[1].replace(",", " ").replace(".", " ").split()
                    if len(w) > 3 and not any(w in other for other in others))
        m, result, runs = self.refusal("removed", caught=word)
        self.assertNowhere(word, result)
        lines = result.lines
        self.assertEqual(lines[-3:], [texts.WAYS_ON[0], texts.WITHHELD, texts.WAYS_ON[2]])


def home_state(root):
    """{path: (kind, mode, size, sha256 or None)} of everything under `root`, a file that cannot be read by its mode and
    size alone, a folder that cannot be listed with nothing beneath it: the fixture home, as far as it can be read."""
    import hashlib, stat
    out = {}
    for base, dirs, files in os.walk(root):
        for name in dirs + files:
            full = os.path.join(base, name)
            st = os.lstat(full)
            digest = None
            if stat.S_ISREG(st.st_mode):
                try:
                    with open(full, "rb") as fh:
                        digest = hashlib.sha256(fh.read()).hexdigest()
                except OSError:
                    digest = "unreadable"
            out[os.path.relpath(full, root)] = (stat.S_IFMT(st.st_mode), stat.S_IMODE(st.st_mode), st.st_size, digest)
    return out


class ARecordOfTheToolsOwnCannotBeRead(WithheldReadCase):
    """SEC-12 (the owner's ruling A40; RK10): "Where one of the three fails, every start stops at the withheld read ...
    The start prints one fixed sentence and nothing else"; its test line, "A record of the tool's own that cannot be
    read", whole: the three passes (and the second form of the first), the four summonses and the seven starts, the
    sentence the same bytes everywhere, no lock, no cue, no read of the vault or of the keying value's file, the home
    byte-equal; the thing put back; that lock's file removed instead, and the record of open runs removed; a lock
    released during the read; the sentence under the withheld read; what the sentence does not hide (RK10); where two
    meet. RUN-12's test line: "a summons at such a start ends `refused`, with the fixture home byte-equal and with its
    output SEC-12's one sentence and nothing else." The seven starts run in this process, as `EveryShippedStartInOrder`
    runs them."""

    def fixture(self, label="spoil"):
        m = self.m = fab.lane_min(harness.Machine(self.tmp, "home-%d" % len(os.listdir(self.tmp)), label))
        first = fab.open_run(m, "demo")
        second = fab.open_run(m, "plain")
        third_run = m.next_id("sunrise")
        lock = fab.stale_lock(m, "third", third_run)       # a killed holder left the lock's file of a third project
        return m, first, second, lock

    def spoils(self, m, lock):
        """(label, spoil, mend) for each pass."""
        def overwrite():
            self.saved = open(lock, "rb").read()
            with open(lock, "wb") as fh:
                fh.write(b"these bytes are no lock's record\n")

        def put_back():
            with open(lock, "wb") as fh:
                fh.write(self.saved)
        yield "a lock's record overwritten", overwrite, put_back
        yield "a lock's record unreadable to its owner", lambda: os.chmod(lock, 0), lambda: os.chmod(lock, 0o600)
        yield "the folder of locks unlistable", lambda: os.chmod(m.facts.locks_dir, 0o300), lambda: os.chmod(m.facts.locks_dir, 0o700)

        def cut():
            self.saved_open = open(m.facts.open_runs_file, "rb").read()
            with open(m.facts.open_runs_file, "wb") as fh:
                fh.write(self.saved_open[:len(self.saved_open) // 2])

        def uncut():
            with open(m.facts.open_runs_file, "wb") as fh:
                fh.write(self.saved_open)
        yield "the record of open runs cut short", cut, uncut

    def starts(self, m):
        from test_start import SEVEN
        position = str(len(m.journal(m.run_ids()[0])) if m.run_ids() else 0)
        out = [("a new summons for a fourth project", ["look", "--kind", "sunrise", "--name", "fourth", "--inputs", m.inputs()]),
               ("a resume", ["resume", "--name", "plain", "--position", position, "--word", "go on"]),
               ("a status summons", ["status", "--name", "plain"]),
               ("a close", ["close", "--name", "plain", "--word", "close"])]
        return out + [(label, argv) for label, argv in SEVEN]

    def start(self, m, label, argv, **kw):
        import sys
        from test_start import SEVENTH
        if label != SEVENTH:
            return m.run(*argv, **kw)
        saved = sys.modules.get("sun_core.cli")
        sys.modules["sun_core.cli"] = None
        try:
            return m.run(*argv, **kw)
        finally:
            if saved is None:
                sys.modules.pop("sun_core.cli", None)
            else:
                sys.modules["sun_core.cli"] = saved

    def test_SEC12_RUN12_A40_RK10_every_start_prints_the_one_sentence_and_nothing_else_in_each_pass(self):
        m, first, second, lock = self.fixture()
        sentence = (texts.RECORD_UNREADABLE + "\n").encode()
        self.assertNotIn(os.sep, texts.RECORD_UNREADABLE)
        from test_start import SEVEN
        seven = [label for label, _argv in SEVEN]
        before_all = dict((label, self.start(m, label, argv)) for label, argv in self.starts(m) if label in seven)
        for label, spoil, mend in self.spoils(m, lock):
            spoil()
            try:
                for start, argv in self.starts(m):
                    with self.subTest(spoiled=label, start=start):
                        cues = list(m.cue_calls)
                        before = home_state(m.home)
                        result = self.start(m, start, argv)
                        self.assertEqual((result.out + result.err).encode(), sentence, "not the one sentence and nothing else")
                        self.assertEqual(result.err, "")
                        self.assertEqual(result.code, 10)
                        for run in (first, second):
                            self.assertNotIn(run, result.out)
                        self.assertNotIn(m.home, result.out)
                        self.assertEqual([e for e in result.events if e["op"] == "lock"], [], "a lock was taken")
                        self.assertEqual(m.cue_calls, cues, "the cue's fake recorded a call")
                        reads = [e["subject"] for e in result.events if e["stage"] == "read"]
                        self.assertFalse([r for r in reads if str(r).startswith(m.vault)], "the vault was read")
                        self.assertNotIn(m.facts.keying_file, reads, "the keying value's file was read")
                        self.assertEqual([e for e in result.events if e["stage"] in ("pre", "mid", "post")], [], "something was written")
                        self.assertEqual(home_state(m.home), before, "the fixture home changed")
            finally:
                mend()
            for start, argv in self.starts(m):
                with self.subTest(put_back=label, start=start):
                    again = self.start(m, start, argv)
                    self.assertNotIn(texts.RECORD_UNREADABLE, again.text)
                    if start in before_all:       # a summons changes its run, so only the starts that are no summons are compared whole
                        self.assertEqual((again.code, again.out, again.err), (before_all[start].code, before_all[start].out, before_all[start].err),
                                         "with the spoiled thing put back the start does not answer as it did before")

    def test_SEC12_A40_A41_that_locks_file_removed_or_the_record_of_open_runs_removed_prints_no_sentence(self):
        m, first, second, lock = self.fixture()
        os.remove(lock)
        result = m.run("--help")
        self.assertNotIn(texts.RECORD_UNREADABLE, result.text)
        self.assertEqual(result.code, 0)
        os.remove(m.facts.open_runs_file)
        result = m.run("status", "--name", "plain")
        self.assertNotIn(texts.RECORD_UNREADABLE, result.text)
        self.assertEqual(result.lines, [texts.NOTHING_TO_RESUME])

    def test_SEC12_A40_A41_a_lock_released_during_the_read_is_no_record_that_cannot_be_read(self):
        from test_log_op import at, planted
        m, first, second, lock = self.fixture()
        released = planted(at("read", "listdir", m.facts.locks_dir), lambda: os.remove(lock))
        result = m.run("look", "--kind", "sunrise", "--name", "third", "--inputs", m.inputs(), kill=released)
        listed = [e["i"] for e in result.events if e["stage"] == "read" and e["op"] == "listdir" and e["subject"] == m.facts.locks_dir]
        self.assertTrue(listed, "the folder of locks was not listed")
        self.assertNotIn(texts.RECORD_UNREADABLE, result.text)
        self.assertEqual(result.ending, "preview", "the start did not go on as if no such lock were held")

    def test_SEC12_A40_the_sentence_under_the_withheld_read_and_RK10_what_it_does_not_hide(self):
        word = "record"
        self.assertIn(word, texts.RECORD_UNREADABLE)
        self.assertNotIn(word, texts.WITHHELD)
        # the first pass again: the second run, whose records can all be read, has caught a word of that sentence
        m, first, second, lock = self.fixture("under")
        fab.catch(m, second, word)
        with open(lock, "wb") as fh:
            fh.write(b"no lock's record\n")
        result = m.run("--help")
        self.assertEqual(result.out, texts.WITHHELD + "\n")
        self.assertNowhere(word, result)
        # the third pass again: the first run, which the spoiled record of open runs alone names, has caught it (RK10)
        m, first, second, lock = self.fixture("rk10")
        fab.catch(m, first, word)
        data = open(m.facts.open_runs_file, "rb").read()
        with open(m.facts.open_runs_file, "wb") as fh:
            fh.write(data[:len(data) // 2])
        result = m.run("--help")
        self.assertEqual(result.out, texts.RECORD_UNREADABLE + "\n", "RK10: the sentence is printed whole")

    def test_SEC12_RUN2_A40_where_two_meet_the_one_sentence_and_then_the_keying_refusal_once_the_record_is_mended(self):
        m, first, second, lock = self.fixture("meet")
        os.remove(m.facts.keying_file)
        saved = open(lock, "rb").read()
        with open(lock, "wb") as fh:
            fh.write(b"no lock's record\n")
        for argv in (["--help"], ["status", "--name", "plain"], ["look", "--kind", "sunrise", "--name", "fourth", "--inputs", m.inputs()]):
            result = m.run(*argv)
            self.assertEqual(result.out + result.err, texts.RECORD_UNREADABLE + "\n")
            for way in texts.WAYS_ON:
                self.assertNotIn(way, result.text)
        with open(lock, "wb") as fh:
            fh.write(saved)
        refusal = m.run("status", "--name", "plain")
        self.assertEqual(refusal.lines[0], texts.GATE["keying-missing"])
        self.assertIn(texts.RUN_ON_RECORD + second, refusal.lines)
        self.assertEqual(refusal.lines[-3:], list(texts.WAYS_ON))


class EveryShippedStartInOrder(WithheldReadCase):
    """SEC-12's test line, "Every shipped start", the second fixture: the order. The test's own driver calls, in its
    own process, the code the entry point runs for each start (`sun.start`, through `Machine.run`), with the recording
    file system it stands up and an output it records. The first fixture, the shipped tool as a child, is in
    `test_start.py`. The seventh start, a file of the tool outside its first code missing: in this process the file
    cannot be taken away from under the modules already loaded, so the import of the one removed in the first fixture
    (`sun_core/cli.py`) is made to find nothing, as the import system has it for a module that is not there."""

    def test_SEC12_D8A_for_each_start_with_no_summons_every_read_of_the_withheld_read_ends_before_the_first_byte(self):
        from test_start import SEVEN
        word = "ok"
        first = fab.open_run(self.m, "demo")
        fab.catch(self.m, first, word)
        second = fab.open_run(self.m, "plain")
        fab.stale_lock(self.m, "demo", first)
        locks = self.m.lock_names()
        self.assertEqual(len(locks), 1)
        import sys
        from test_start import SEVENTH
        for label, argv in SEVEN:
            with self.subTest(start=label):
                if label == SEVENTH:
                    saved = sys.modules.get("sun_core.cli")
                    sys.modules["sun_core.cli"] = None          # the import of a module that is not there
                    try:
                        result = self.m.run(*argv)
                    finally:
                        if saved is None:
                            sys.modules.pop("sun_core.cli", None)
                        else:
                            sys.modules["sun_core.cli"] = saved
                    self.assertEqual(result.err, texts.WITHHELD + "\n", "the seventh start's failure line is not passed under the read")
                    self.assertEqual(result.out, "")
                else:
                    result = self.m.run(*argv)
                self.read_first(result, [first, second], locks)
                self.assertNotIn(word, result.out, label)
                self.assertNotIn(word, result.err, label)
                writes = [e for e in result.events if e["stage"] in ("pre", "post") and e["op"] not in ("child",)]
                self.assertEqual(writes, [], "%s: a start that is no summons wrote something" % label)


if __name__ == "__main__":
    unittest.main()
