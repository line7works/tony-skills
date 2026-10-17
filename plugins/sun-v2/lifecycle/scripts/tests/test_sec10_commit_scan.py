"""SEC-10, on fakes and a fixture repository with content (the owner's rulings A87 and A89; RK15).

SEC-10: "Before every commit a check scans, by content, exactly what will be committed and proves the ignore rule; before
a push a check scans every commit to be pushed. A hit is any entry of the register at the check (SEC-12), or any value of
the pulled env file or of the hosting link file of that working tree (SEC-7), which the check reads in-process at the
check, uses for this match and for nothing else, enters in no register, and drops after it; each is matched whole, by each
component its source declares, and in the percent-encoded and base64 forms of both, as SEC-12 names the forms (the owner's
ruling, A87). ... A hit stops the run, names the file and shows nothing."

The fixture repository is real git, made by the test in its own temporary folder, with a remote the test built on disk
(brief.md section 2). The run's commit and push are the fake git's compare-and-swap rows (`rowlib.cas`): what the tool's
check reads is the real repository's index and commits, and "the commit and the push are made" is the fake's record of
those two calls. The hosting module's fixed words for its own variable are the fixture's, as SEC-10's test line has them
(`1`, `development` for one variable of its own); the shipped lane's list is no part of this test (report-11, question 27).
"""
import base64
import json
import os
import subprocess
import urllib.parse

import harness
import rowlib
from rowlib import DEV, NAME, path
from sun_core import texts

GIT = "/usr/bin/git"
MODULE_VAR = "FAKEHOST_ENV"            # the fixture's hosting module's own variable, which its pull writes beside his
FIXED = {MODULE_VAR: ["1", "development"]}


def forms(value, component=None):
    """The four forms SEC-10's test line plants: whole, by component, percent-encoded and in base64."""
    return {"whole": value, "component": component or value,
            "percent": urllib.parse.quote(value, safe=""), "base64": base64.b64encode(value.encode("utf-8")).decode("ascii")}


def scan_rows(fixed=None):
    repo = path(DEV, NAME)
    spec = {"repo": repo, "env_file": path(DEV, NAME, ".env.local"), "link_file": path(DEV, NAME, ".fakehost", "project.json"),
            "fixed_words": fixed if fixed is not None else FIXED}
    commit_scan = dict(spec, read="commit-scan")
    push_scan = dict(spec, read="push-scan", branch="main", base="refs/remotes/origin/main")
    return [
        rowlib.check("KC", "one", place=repo, output="commit scanned",
                     thing={"role": "what will be committed", "tracked": ["exists"], "subject_git": "index", "passes": [commit_scan]}),
        rowlib.cas("GC", "one", ref="commit", new="c1", old="none", output="committed",
                   needs=[{"output": "commit scanned", "level": "passed", "treatment": "then not applicable"}]),
        rowlib.check("KP", "one", place=repo, output="push scanned",
                     thing={"role": "every commit to be pushed", "tracked": ["exists"], "subject_git": "head", "passes": [push_scan]},
                     needs=[{"output": "committed", "level": "made", "treatment": "then not applicable"}]),
        rowlib.cas("GP", "one", ref="remote", new="c1", old="none", output="pushed",
                   needs=[{"output": "push scanned", "level": "passed", "treatment": "then not applicable"},
                          {"output": "committed", "level": "made", "treatment": "then not applicable"}]),
    ]


class Fixture(object):
    """One fixture machine with a repository at the developer root's `demo`, its first commit pushed to a bare remote.

    `gitignore` is the top ignore file of the first commit. `worktree`: the repository is made at `demo-main`, and `demo`,
    where the rows work, is a linked worktree of it (its `.git` a file; the exclude file it shares is the main
    repository's). `pushed`: the first commit is pushed (the remote's branch then holds it), else the remote holds
    nothing and every commit is to be sent. `first`: further files of the first commit, {path: text}."""

    def __init__(self, case, env_lines, link_doc, fixed=None, gitignore=".env.local\n.fakehost/\n", worktree=False,
                 pushed=True, first=None):
        case.count += 1
        self.m = harness.Machine(case.tmp, "c%d" % case.count, "c%d" % case.count)
        rowlib.install(self.m, rowlib.lane("sunrise", scan_rows(fixed)))
        self.repo = self.m.path("dev", "demo")
        self.main = self.m.path("dev", "demo-main") if worktree else self.repo
        self.remote = os.path.join(self.m.root, "remote-%d.git" % case.count)
        os.makedirs(self.main)
        self.git("init", "-q", "-b", "main", cwd=self.main)
        self.write("README.md", "# demo\n", root=self.main)
        self.write(".gitignore", gitignore, root=self.main)
        names = ["README.md", ".gitignore"]
        for rel, text in sorted((first or {}).items()):
            self.write(rel, text, root=self.main)
            names.append(rel)
        self.git("add", *names, cwd=self.main)
        self.git("commit", "-q", "-m", "first", cwd=self.main)
        self.git("init", "-q", "--bare", self.remote, cwd=self.m.root)
        self.git("remote", "add", "origin", self.remote, cwd=self.main)
        if pushed:
            self.git("push", "-q", "origin", "main", cwd=self.main)
        if worktree:
            self.git("worktree", "add", "-q", "-b", "wt", self.repo, cwd=self.main)
        self.env_text = "".join(line + "\n" for line in env_lines)
        self.write(".env.local", self.env_text, 0o600)
        self.link_text = json.dumps(link_doc, sort_keys=True) + "\n"
        self.write(os.path.join(".fakehost", "project.json"), self.link_text, 0o600)

    def git(self, *args, **kw):
        env = {"HOME": self.m.home, "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
               "LANG": "C"}
        subprocess.run([GIT, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false"]
                       + list(args), cwd=kw.get("cwd", self.repo), env=env, check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)

    def write(self, rel, text, mode=0o644, root=None):
        full = os.path.join(root or self.repo, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(text)
        os.chmod(full, mode)

    def stage(self, rel, text):
        self.write(rel, text)
        self.git("add", rel)

    def run(self, env=None):
        looked = self.m.look(env=env)
        assert looked.doc and looked.doc.get("manifest_sha256"), looked.text
        self.went = self.m.go(looked, env=env)
        return self.went

    def made(self):
        """(the commit made, the push made): the fake git's record of its two swaps."""
        refs = [c["argv"][c["argv"].index("--ref") + 1] for c in self.m.calls("fakegit", "cas")]
        return "commit" in refs, "remote" in refs


class Case(harness.Case):
    def setUp(self):
        harness.Case.setUp(self)
        self.count = 0
        self.token = harness.canary("sec10-token")
        self.password = "pw" + harness.canary("sec10-password")
        self.address = "postgres://fixture:%s@db.fixture.invalid:5432/app" % self.password
        self.project_id = "prj" + harness.canary("sec10-project")

    def env(self):
        return {"FAKEHOST_TOKEN": self.token}

    def fixture(self, env_lines=None, link_doc=None, fixed=None, **layout):
        env_lines = env_lines if env_lines is not None else ['%s="development"' % MODULE_VAR, 'DATABASE_URL="%s"' % self.address]
        link_doc = link_doc if link_doc is not None else {"projectId": self.project_id, "orgId": "org" + harness.canary("sec10-org")}
        return Fixture(self, env_lines, link_doc, fixed, **layout)

    def attempts(self, fx, result, op):
        return [r["answer"] for r in fx.m.journal(result.doc["run"]) if r["kind"] == "attempt" and r["op"] == op]

    def assertStoppedBefore(self, fx, result, which, rel, *values):
        commit, push = fx.made()
        self.assertEqual(result.ending, "stopped", result.text)
        if which == "commit":
            self.assertFalse(commit, "the commit was made")
        self.assertFalse(push, "the push was made")
        self.assertIn(rel, result.text, "the output names the file")
        for value in values:
            for form in forms(value).values():
                self.assertNowhere(form, result)

    def assertMade(self, fx, result):
        self.assertEqual(result.ending, "complete", result.text)
        self.assertEqual(fx.made(), (True, True))


class WhatAHitIs(Case):
    def test_SEC10_a_canary_about_to_be_committed_stops_the_commit_also_where_the_working_tree_file_was_cleaned(self):
        canary = harness.canary("sec10-staged")
        fx = self.fixture()
        fx.stage("notes.txt", "the token: %s\n" % self.token)    # about to be committed: a register entry
        fx.write("notes.txt", "cleaned\n")                  # the working-tree file cleaned since: the index still holds it
        result = fx.run(self.env())
        self.assertStoppedBefore(fx, result, "commit", "notes.txt", self.token, canary)

    def test_SEC10_a_canary_in_a_working_tree_file_not_part_of_the_commit_stops_nothing_and_with_none_both_are_made(self):
        fx = self.fixture()
        fx.stage("notes.txt", "plain words\n")
        fx.write("README.md", "# demo\n%s\n" % self.token)    # changed in the working tree, not staged
        fx.write("loose.txt", "%s\n" % self.password)          # untracked
        self.assertMade(fx, fx.run(self.env()))
        clean = self.fixture()
        clean.stage("notes.txt", "plain words\n")
        self.assertMade(clean, clean.run(self.env()))

    def test_SEC10_A87_a_register_entry_an_env_value_and_a_link_id_in_four_forms_each_stop_the_commit(self):
        planted = {"the hosting token": forms(self.token), "an env value": forms(self.address, self.password),
                   "a link id": forms(self.project_id)}
        for what, by_form in sorted(planted.items()):
            for form, text in sorted(by_form.items()):
                fx = self.fixture()
                fx.stage("notes.txt", "plain\n%s\n" % text)
                result = fx.run(self.env())
                with self.subTest(what=what, form=form):
                    self.assertStoppedBefore(fx, result, "commit", "notes.txt", self.token, self.address, self.password,
                                             self.project_id)

    def test_SEC10_A87_the_same_three_in_a_commit_made_earlier_by_hand_stop_the_push(self):
        for what, text in (("the hosting token", self.token), ("an env value", self.password),
                           ("a link id", base64.b64encode(self.project_id.encode()).decode())):
            fx = self.fixture()
            fx.stage("earlier.txt", "%s\n" % text)
            fx.git("commit", "-q", "-m", "by hand")
            fx.stage("notes.txt", "plain words\n")
            result = fx.run(self.env())
            with self.subTest(what=what):
                self.assertEqual(fx.made()[0], True, "the commit, which holds no hit, was made")
                self.assertStoppedBefore(fx, result, "push", "earlier.txt", self.token, self.address, self.password,
                                         self.project_id)

    def test_SEC10_A87_an_env_value_of_no_length_and_a_text_in_no_entry_and_neither_file_stop_nothing(self):
        fx = self.fixture(env_lines=['EMPTY_ONE=""', "EMPTY_TWO=", 'DATABASE_URL="%s"' % self.address])
        fx.stage("notes.txt", "plain words and %s\n" % harness.canary("sec10-nowhere"))
        self.assertMade(fx, fx.run(self.env()))

    def test_SEC10_A87_SEC7_the_check_reads_the_two_files_keeps_no_copy_and_enters_nothing_in_the_register(self):
        # the register: the description the look saves equals a value of the env file; had the check entered that value in
        # the register, SEC-12's search would find it in the saved inputs and write a disproof record, and stop
        note = "note" + harness.canary("sec10-note")
        fx = self.fixture(env_lines=['%s="development"' % MODULE_VAR, 'OWNER_NOTE="%s"' % note, 'DATABASE_URL="%s"' % self.address])
        fx.stage("notes.txt", "plain words\n")
        looked = fx.m.look(inputs=fx.m.inputs(description=note), env=self.env())
        self.assertTrue(looked.doc and looked.doc.get("manifest_sha256"), looked.text)
        went = fx.m.go(looked, env=self.env())
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(fx.made(), (True, True))
        self.assertNotIn("disproof", [r["kind"] for r in fx.m.journal(looked.doc["run"])])
        form = "".join(open(f).read() for f in went.doc.get("forms") or [])
        self.assertIn(note, form, "the status form the go renders after the check shows the description as text")
        self.assertNotIn(texts.WITHHELD, form)
        # the reads, and no copy: a plain description, every file of the fixture home but the two files and the repository's
        # own folder searched for each value of the two files
        fx = self.fixture()
        fx.stage("notes.txt", "plain words\n")
        went = fx.run(self.env())
        self.assertEqual(went.ending, "complete", went.text)
        env_file, link_file = os.path.join(fx.repo, ".env.local"), os.path.join(fx.repo, ".fakehost", "project.json")
        reads = [e["subject"] for e in went.events if e["stage"] == "read" and e["op"] == "read"]
        self.assertIn(env_file, reads)
        self.assertIn(link_file, reads)
        for root, _dirs, files in os.walk(fx.m.home):
            for name in files:
                full = os.path.join(root, name)
                if full in (env_file, link_file) or full.startswith(os.path.join(fx.repo, ".git") + os.sep):
                    continue
                with open(full, "rb") as fh:
                    data = fh.read()
                for value in (self.address, self.password, self.project_id):
                    self.assertNotIn(value.encode(), data, "a copy of a value of the two files in %s" % full)


class WhatIsNoHit(Case):
    def test_SEC10_A89_RK15_a_module_word_on_its_list_and_short_values_stop_nothing_and_carry_no_mark(self):
        short = "k" + harness.canary("sec10-short")[-6:]            # seven bytes
        padded = " " + "p" + harness.canary("sec10-pad")[-6:] + " "  # seven bytes, a space at each end
        cases = (("development", ['%s="development"' % MODULE_VAR]),
                 (short, ['OWNER_SHORT="%s"' % short]),
                 (padded, ['OWNER_PADDED="%s"' % padded]))
        for value, env_lines in cases:
            for form, text in sorted(forms(value).items()):
                fx = self.fixture(env_lines=env_lines)
                fx.stage("notes.txt", "plain\n%s\n" % text)
                result = fx.run(self.env())
                with self.subTest(value=value, form=form):
                    self.assertMade(fx, result)
                    run_id = result.doc["run"]
                    self.assertEqual([r for r in fx.m.journal(run_id) if r.get("step") == "risk-mark"], [],
                                     "a commit made past a value of the env file under eight bytes carries no mark (RISK-1)")

    def test_SEC10_A89_eight_bytes_a_module_word_under_his_own_variable_and_a_word_off_the_list_each_stop_the_commit(self):
        eight = "e" + harness.canary("sec10-eight")[-7:]
        cases = (("eight bytes under his variable", eight, ['OWNER_EIGHT="%s"' % eight], None),
                 ("development under his variable", "development", ['OWNER_STAGE="development"'], None),
                 ("the module's word off its list", "development", ['%s="development"' % MODULE_VAR], {MODULE_VAR: ["1"]}))
        for what, value, env_lines, fixed in cases:
            for form, text in sorted(forms(value).items()):
                fx = self.fixture(env_lines=env_lines, fixed=fixed)
                fx.stage("notes.txt", "plain\n%s\n" % text)
                result = fx.run(self.env())
                with self.subTest(what=what, form=form):
                    self.assertStoppedBefore(fx, result, "commit", "notes.txt", value)


class TheIgnoreRule(Case):
    def test_SEC10_SEC7_the_ignore_rule_is_proven_before_the_commit_and_a_file_it_does_not_cover_stops_it(self):
        fx = self.fixture()
        fx.git("rm", "-q", "--cached", ".gitignore")
        fx.write(".gitignore", ".fakehost/\n")
        fx.git("add", ".gitignore")
        fx.stage("notes.txt", "plain words\n")
        result = fx.run(self.env())
        self.assertStoppedBefore(fx, result, "commit", ".env.local", self.address, self.password)
        tracked = self.fixture()
        tracked.git("add", "-f", ".fakehost/project.json")
        result = tracked.run(self.env())
        self.assertEqual(result.ending, "stopped", result.text)
        self.assertEqual(tracked.made(), (False, False))


class WhatIsScanned(Case):
    """SEC-10 (batch 39): "What will be committed is what the commit changes: each path whose content in the index differs
    from the head commit's, and every path where there is no head commit. Every commit to be pushed is each commit the push
    sends that the base the row names, the remote's branch, does not hold, and every commit where the row names none; each
    is scanned by its own message and by each file it changes against its first parent, every file of a commit with no
    parent." Its test line: "What is scanned: a canary already in the head commit, in a file the next commit does not
    change, does not stop that commit, and where the head commit is still to be sent the push stops on it, naming the file;
    a canary in a commit's message, and one in a commit with no parent, each stop the push; a canary that a merge commit
    brings from a second parent still to be sent stops the push in the commit on that parent's side that brought it." The
    canary is the fixture's hosting token, a register entry at the check."""

    def head(self, fx):
        return subprocess.run([GIT, "rev-parse", "HEAD"], cwd=fx.repo, stdout=subprocess.PIPE, check=True,
                              env={"PATH": "/usr/bin:/bin", "HOME": fx.m.home}).stdout.decode().strip()

    def test_SEC10_batch39_a_canary_in_the_head_commit_unchanged_passes_the_commit_and_stops_the_push_while_that_commit_is_to_be_sent(self):
        fx = self.fixture()
        fx.stage("earlier.txt", "%s\n" % self.token)
        fx.git("commit", "-q", "-m", "by hand")
        fx.stage("notes.txt", "plain words\n")             # the next commit does not change earlier.txt
        result = fx.run(self.env())
        self.assertEqual(self.attempts(fx, result, "KC"), ["passed"], "the commit scan scanned content already in the head")
        self.assertEqual(fx.made()[0], True, "the commit was stopped")
        self.assertStoppedBefore(fx, result, "push", "earlier.txt", self.token)
        sent = self.fixture()
        sent.stage("earlier.txt", "%s\n" % self.token)
        sent.git("commit", "-q", "-m", "by hand")
        sent.git("push", "-q", "origin", "main")           # the head commit is on the remote's branch: not to be sent
        sent.stage("notes.txt", "plain words\n")
        self.assertMade(sent, sent.run(self.env()))

    def test_SEC10_batch39_a_canary_in_a_commits_message_and_one_in_a_commit_with_no_parent_each_stop_the_push(self):
        fx = self.fixture()
        fx.stage("other.txt", "plain words\n")
        fx.git("commit", "-q", "-m", "about %s" % self.token)
        said = self.head(fx)
        fx.stage("notes.txt", "plain words\n")
        result = fx.run(self.env())
        self.assertEqual(fx.made()[0], True)
        self.assertStoppedBefore(fx, result, "push", said, self.token)
        root = self.fixture(pushed=False, first={"seed.txt": "%s\n" % self.token})
        root.stage("notes.txt", "plain words\n")
        result = root.run(self.env())
        self.assertEqual(root.made()[0], True)
        self.assertStoppedBefore(root, result, "push", "seed.txt", self.token)

    def test_SEC10_batch39_a_canary_a_merge_brings_from_a_second_parent_to_be_sent_stops_the_push_in_that_sides_commit(self):
        for gone in (False, True):
            fx = self.fixture()
            fx.git("checkout", "-q", "-b", "side")
            fx.stage("side.txt", "%s\n" % self.token)
            fx.git("commit", "-q", "-m", "on the side")
            if gone:      # taken out again on the side: the merge commit itself then changes no file holding it
                fx.git("rm", "-q", "side.txt")
                fx.git("commit", "-q", "-m", "taken out")
            fx.git("checkout", "-q", "main")
            fx.git("merge", "-q", "--no-ff", "-m", "merge", "side")
            if gone:
                self.assertFalse(os.path.exists(os.path.join(fx.repo, "side.txt")))
            fx.stage("notes.txt", "plain words\n")
            result = fx.run(self.env())
            with self.subTest(taken_out_on_the_side=gone):
                self.assertEqual(fx.made()[0], True)
                self.assertStoppedBefore(fx, result, "push", "side.txt", self.token)


class ThePushNamesItsAttempt(Case):
    """OP-8's test line: "a scan that passed on one commit does not let the push run when an approved operation has since
    made another commit the head: it is attempted again on the new head, and the push's start record names the same
    commit as the attempt that let it run." Part 5, example 1: "variant: attempt 1 passed on c2, and an approved operation
    has since made c3 the head | the subject's tracked state is c3 | attempt 1 no longer meets the push's need: a new
    attempt is made on c3, and the push names c3"."""

    def test_OP8_SEC10_a_push_scan_passed_on_one_commit_is_attempted_again_on_the_new_head_and_the_push_names_that_commit(self):
        rows = scan_rows()
        kc, gc, kp, gp = rows
        # an approved operation between the push's scan and the push: a second commit (its effect is the fake's swap of
        # `commit2`; the fixture makes the real commit at that call, so that the run's own operation makes the new head)
        again = rowlib.cas("GC2", "one", ref="commit2", new="c2", old="none", output="committed again",
                           needs=[{"output": "push scanned", "level": "passed", "treatment": "then not applicable"}])
        gp["needs"] = gp["needs"] + [{"output": "committed again", "level": "made", "treatment": "then not applicable"}]
        fx = self.fixture()
        rowlib.install(fx.m, rowlib.lane("sunrise", [kc, gc, kp, again, gp]))
        fx.stage("notes.txt", "plain words\n")
        first = WhatIsScanned.head(self, fx)
        made = []

        def commit_at_the_swap(event):
            argv = event.get("argv") or []
            if not made and event["stage"] == "pre" and event["op"] == "child" and argv[:3] == ["cas", "--ref", "commit2"]:
                fx.stage("later.txt", "an approved change\n")
                fx.git("commit", "-q", "-m", "an approved commit")
                made.append(WhatIsScanned.head(self, fx))
            return False
        looked = fx.m.look(env=self.env())
        self.assertTrue(looked.doc and looked.doc.get("manifest_sha256"), looked.text)
        went = fx.m.go(looked, env=self.env(), kill=commit_at_the_swap)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(len(made), 1, "the approved commit was not made")
        second = made[0]
        self.assertNotEqual(first, second)
        journal = fx.m.journal(looked.doc["run"])
        attempts = [r for r in journal if r["kind"] == "attempt" and r["op"] == "KP"]
        self.assertEqual([a["answer"] for a in attempts], ["passed", "passed"], "the push's scan was not attempted again")
        self.assertEqual([a["subject"].get("word") for a in attempts], [first, second],
                         "each attempt's subject is not the head commit it scanned")
        start = [r for r in journal if r["kind"] == "start" and r["op"] == "GP"]
        self.assertEqual(len(start), 1)
        self.assertEqual(start[0]["checked"], [{"check": "KP", "attempt": 2, "subject": {"word": second}}],
                         "the push's start record does not name the commit of the attempt that let it run")
        self.assertEqual(WhatIsScanned.head(self, fx), second)


class TheIgnoreRuleByGitsOwnRules(Case):
    """SEC-10 (batch 39): "The ignore rule is proven for each of the pulled env file and the hosting link file that stands
    in the working tree: that it is in no stage of the index and that git ignores it. Where the check cannot prove that,
    the attempt is `failed` (OP-8) and the run stops as at a hit, naming the file and showing nothing." Its test line: "The
    ignore rule: the pulled env file staged in the index, and in a second pass standing in the working tree with no pattern
    that ignores it, each make the attempt `failed` and stop the run before the commit, the output naming the file and
    holding none of its values; with the file unstaged and ignored by a plain line of the repository's top ignore file the
    attempt passes and the commit is made." Brief-12 item 1 (contract A92): the proof follows git's own rules for that
    repository; beside the test line's passes, each ignoring the env file by another of git's ways, the attempt passes."""

    def values(self):
        return (self.address, self.password, "development")

    def assertProvenAndMade(self, fx, result, what):
        with self.subTest(way=what):
            self.assertMade(fx, result)
            self.assertEqual(self.attempts(fx, result, "KC"), ["passed"], "the commit scan's attempt")

    def assertFailedAndStopped(self, fx, result, what):
        with self.subTest(way=what):
            self.assertStoppedBefore(fx, result, "commit", ".env.local", *self.values())
            self.assertEqual(self.attempts(fx, result, "KC"), ["failed"], "the commit scan's attempt")
            self.assertTrue(any(texts.SEC10_IGNORE in line for line in result.lines), result.text)

    def test_SEC10_batch39_the_env_file_staged_or_standing_with_no_pattern_fails_the_attempt_and_a_plain_top_line_passes(self):
        staged = self.fixture()
        staged.git("add", "-f", ".env.local")
        staged.stage("notes.txt", "plain words\n")
        self.assertFailedAndStopped(staged, staged.run(self.env()), "the env file staged in the index")
        bare = self.fixture(gitignore=".fakehost/\n")
        bare.stage("notes.txt", "plain words\n")
        self.assertFailedAndStopped(bare, bare.run(self.env()), "the env file standing with no pattern that ignores it")
        plain = self.fixture(gitignore=".env.local\n.fakehost/\n")
        plain.stage("notes.txt", "plain words\n")
        self.assertProvenAndMade(plain, plain.run(self.env()), "a plain line of the top ignore file")

    def test_SEC10_A92_a_negated_example_line_a_double_star_his_own_excludes_file_and_a_shared_exclude_each_prove_it_ignored(self):
        # the ignore file the skill writes today: every env file, then the example back in
        example = self.fixture(gitignore=".env*\n!.env.example\n.fakehost/\n", first={".env.example": "DATABASE_URL=\n"})
        example.stage("notes.txt", "plain words\n")
        self.assertProvenAndMade(example, example.run(self.env()), "`.env*` then `!.env.example`")
        stars = self.fixture(gitignore="**/.env.local\n.fakehost/**\n")
        stars.stage("notes.txt", "plain words\n")
        self.assertProvenAndMade(stars, stars.run(self.env()), "a `**` pattern")
        # the owner's own excludes file in the fixture home: where git looks for it by default, and where his settings
        # of git name it
        default = self.fixture(gitignore=".fakehost/\n")
        os.makedirs(os.path.join(default.m.home, ".config", "git"))
        with open(os.path.join(default.m.home, ".config", "git", "ignore"), "w") as fh:
            fh.write(".env.local\n")
        default.stage("notes.txt", "plain words\n")
        self.assertProvenAndMade(default, default.run(self.env()), "his excludes file where git looks for it by default")
        named = self.fixture(gitignore=".fakehost/\n")
        excludes = os.path.join(named.m.home, "my-excludes")
        with open(excludes, "w") as fh:
            fh.write(".env.local\n")
        with open(os.path.join(named.m.home, ".gitconfig"), "w") as fh:
            fh.write("[core]\n\texcludesFile = %s\n" % excludes)
        named.stage("notes.txt", "plain words\n")
        self.assertProvenAndMade(named, named.run(self.env()), "his excludes file named by his settings of git")
        # a linked worktree whose shared exclude file, the main repository's, is the only thing that ignores the env file
        shared = self.fixture(gitignore=".fakehost/\n", worktree=True)
        self.assertTrue(os.path.isfile(os.path.join(shared.repo, ".git")), "the rows' repository is not a linked worktree")
        with open(os.path.join(shared.main, ".git", "info", "exclude"), "a") as fh:
            fh.write(".env.local\n")
        shared.stage("notes.txt", "plain words\n")
        self.assertProvenAndMade(shared, shared.run(self.env()), "a linked worktree's shared exclude file")
        alone = self.fixture(gitignore=".fakehost/\n", worktree=True)
        alone.stage("notes.txt", "plain words\n")
        self.assertFailedAndStopped(alone, alone.run(self.env()), "the same linked worktree with no exclude line")

    def test_SEC10_A94_an_excludes_file_only_the_sessions_XDG_CONFIG_HOME_names_fails_the_attempt_and_stops_naming_the_file(self):
        """SEC-10 (batch 40, A94): "The proof is of the git the runner starts, in the environment SEC-3 builds for it: the git
        and the environment the run's own commits and pushes go through." Its test line: "The proof's git: with the env file
        ignored only by an excludes file in a folder that the session's `XDG_CONFIG_HOME` names, and by no file the git the
        runner starts reads in its own environment, the attempt is `failed` and the run stops naming the file." The excludes
        file stands in the fixture home (brief.md section 2), where git looks for it under that folder (`git/ignore`)."""
        fx = self.fixture(gitignore=".fakehost/\n")
        xdg = os.path.join(fx.m.home, "xdg-config")
        os.makedirs(os.path.join(xdg, "git"))
        with open(os.path.join(xdg, "git", "ignore"), "w") as fh:
            fh.write(".env.local\n")
        fx.stage("notes.txt", "plain words\n")
        # the fixture's premise: a git started with the session's XDG_CONFIG_HOME ignores the env file, and one started in
        # the environment the runner builds (HOME as the tool has it, no XDG_CONFIG_HOME) does not, reading no other file
        # that ignores it
        for name in (os.path.join(".config", "git", "ignore"), ".gitconfig", os.path.join(".config", "git", "config")):
            self.assertFalse(os.path.exists(os.path.join(fx.m.home, name)), "a file the runner's git reads: %s" % name)
        with open(os.path.join(fx.repo, ".git", "info", "exclude")) as fh:
            self.assertNotIn(".env.local", fh.read())
        plain = {"HOME": fx.m.home, "PATH": "/usr/bin:/bin", "LANG": "C"}

        def ignored(env):
            return subprocess.call([GIT, "check-ignore", "-q", "--", ".env.local"], cwd=fx.repo, env=env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
        self.assertTrue(ignored(dict(plain, XDG_CONFIG_HOME=xdg)), "the session's git does not ignore it")
        self.assertFalse(ignored(plain), "a git with the runner's environment ignores it")
        result = fx.run(dict(self.env(), XDG_CONFIG_HOME=xdg))
        self.assertFailedAndStopped(fx, result, "an excludes file only the session's XDG_CONFIG_HOME names")
        self.assertIn(texts.SEC10_FILE + ".env.local", result.lines, "the stop does not name the file")
        gits = [e for e in result.events if e["op"] == "child" and e["stage"] == "pre" and e["subject"] == "git"]
        self.assertTrue(gits, "the proof's git was not started")
        for e in gits:
            self.assertNotIn("XDG_CONFIG_HOME", e["env_names"], "the session's XDG_CONFIG_HOME reached the proof's git")

    def test_SEC10_A92_a_later_negated_line_that_unignores_the_env_file_itself_stops_as_the_second_pass_does(self):
        fx = self.fixture(gitignore=".env*\n!.env.local\n.fakehost/\n")
        fx.stage("notes.txt", "plain words\n")
        self.assertFailedAndStopped(fx, fx.run(self.env()), "`.env*` then `!.env.local`")


class TheRefusalOfTheProofsGit(Case):
    """SEC-10 (batch 40, A94): "Where the runner refuses a command of this check, the proof's git or a read of the scan, the
    check is not made and no attempt is recorded: as SEC-3's refusals row has it for every operation's command, the
    operation is not started and the run ends `stopped` on that refusal, its form naming the refusal." Its test line: "A
    refusal: a fake returns, in a secret field of the operation before the check, a value equal to a part of the temporary
    folder's path, as SEC-3's test line plants one; the runner then refuses the proof's git before any child is created; no
    attempt is recorded, the check's operation is not started, the run ends `stopped` on that refusal, and the form names
    the refusal and holds no part of that path."

    The operation before the check is a C5 whose one request (the fake host's `issue`) returns the value in its secret
    field; the fixture's declaration lets that field hold a path's marks, so that the value passes its validator and is
    kept as a secret (SEC-4), and its after-check reads this machine alone, so that the proof's git is the first child
    started once the value is in the register. The part planted is the one SEC-3's test line plants, `/runs/`, which the
    temporary folder of every child of an operation holds (`<run directory>/tmp`) and no other value of the git's."""

    PART = os.sep + "runs" + os.sep

    def test_SEC10_SEC3_A94_a_refusal_of_the_proofs_git_records_no_attempt_and_stops_the_run_on_that_refusal(self):
        providers = rowlib.providers()
        token = [f for f in providers["fakehost"]["commands"]["issue"]["fields"] if f["name"] == "token"][0]
        token["alphabet"] = "a-z0-9/"
        x1 = rowlib.secret_op("X1", "one")
        x1["after_check"] = [{"read": "path", "path": DEV, "is": "dir"}]
        fx = self.fixture()
        rowlib.install(fx.m, rowlib.lane("sunrise", [x1] + scan_rows()), providers=providers)
        fx.stage("notes.txt", "plain words\n")
        fx.m.plan_fake("fakehost", {"command": "issue", "nth": 1, "value": self.PART})
        looked = fx.m.look(env=self.env())
        self.assertTrue(looked.doc and looked.doc.get("manifest_sha256"), looked.text)
        run_dir = fx.m.facts.run_dir(looked.doc["run"])
        tmpdir = os.path.join(run_dir, "tmp")
        self.assertIn(self.PART, tmpdir, "the fixture's premise: the part is of the temporary folder's path")
        went = fx.m.go(looked, env=self.env())
        journal = fx.m.journal(looked.doc["run"])
        # the value came in a secret field of the operation before the check, and was kept (SEC-4, SEC-12)
        self.assertEqual(fx.m.statuses(looked.doc["run"]).get("X1"), "done", went.text)
        self.assertTrue([r for r in journal if r["kind"] == "step" and r.get("op") == "X1" and r.get("step") == "receipt"],
                        "no receipt of the secret field")
        # the runner refused the proof's git before any child was created: no attempt, the check not made
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
        self.assertIn("stopped: the runner refused the command: register entry", went.lines, "not stopped on that refusal")
        self.assertIn("operation: KC", went.lines)
        self.assertEqual(self.attempts(fx, went, "KC"), [], "an attempt was recorded")
        self.assertFalse([line for line in went.lines if texts.SEC10_IGNORE in line or texts.SEC10_HIT in line],
                         "the stop is SEC-10's failed attempt, not the refusal")
        x1_done = max(r["n"] for r in journal if r.get("op") == "X1")
        self.assertFalse([r for r in journal if r["n"] > x1_done and r["kind"] not in ("invocation-end",)],
                         "a record after the operation before the check, but the invocation's ending")
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["subject"] == "git"], [], "a git child was created")
        self.assertEqual(fx.made(), (False, False), "the commit or the push was made")
        # the form's path in the output holds the part, and gives way to the fixed words of withholding (SEC-12): the form
        # is found by listing the run directory's forms
        folder = os.path.join(run_dir, "forms")
        form = "".join(open(os.path.join(folder, n)).read() for n in sorted(os.listdir(folder)) if n.startswith("status-"))
        self.assertIn("the runner refused the command: register entry", form, "the form does not name the refusal")
        for written in (went.out, went.err, form):
            self.assertNotIn(self.PART, written, "the part of the path is shown")
            self.assertNotIn(tmpdir, written, "the temporary folder's path is shown")
        again = fx.m.summon("status", env=self.env())
        self.assertEqual(again.ending, "stopped", again.text)
        self.assertEqual(self.attempts(fx, again, "KC"), [], "a later status recorded an attempt")


class TheProofsGitGoneAtItsStart(Case):
    """SEC-10: "Where the runner refuses a command of this check, the proof's git or a read of the scan, the check is not made
    and no attempt is recorded: as SEC-3's refusals row has it for every operation's command, the operation is not started
    and the run ends `stopped` on that refusal, its form naming the refusal." SEC-3's refusals row (batch 46, A110): "the
    runner refuses: ... a command of an operation whose program is a tool not found (the command row), whether no folder of
    the search list holds it at the runner's search or the file the runner found is gone as it starts it, so that no child
    is created (the owner's ruling, A109)". The check's git is a command of that operation. Here only the second pass: the
    git the runner finds first stands in a system folder of the fixture's own put first on its list, which the fixture's
    file system empties as the runner starts it; at the search, the system's own git stands behind it, and a git in no
    folder of the list is the runner's refusal at its search for every command, as built before this part."""

    def test_SEC10_SEC3_A109_the_proofs_git_gone_as_the_runner_starts_it_is_a_refusal_no_attempt_is_recorded_and_the_run_stops(self):
        fx = self.fixture()
        fx.stage("notes.txt", "plain words\n")
        folder = os.path.join(fx.m.root, "git-first")
        os.makedirs(folder)
        wrapper = os.path.join(folder, "git")
        with open(wrapper, "w") as fh:
            fh.write("#!/bin/sh\nexec %s \"$@\"\n" % GIT)
        os.chmod(wrapper, 0o755)
        fx.m.system_folders = (folder,) + tuple(fx.m.system_folders)
        looked = fx.m.look(env=self.env())
        self.assertTrue(looked.doc and looked.doc.get("manifest_sha256"), looked.text)
        taken = []

        def hook(event):
            if not taken and event["stage"] == "pre" and event["op"] == "child" and event["subject"] == "git":
                taken.append(event.get("path"))
                os.remove(wrapper)
            return False
        went = fx.m.go(looked, env=self.env(), kill=hook)
        self.assertEqual(taken, [wrapper], "the fixture's premise: the runner found the git first on the list and came to start it")
        self.assertEqual(went.ending, "stopped", went.text)
        self.assertNotIn(texts.DEFECT, went.text, "an exception was reported")
        self.assertIn("stopped: the runner refused the command: tool not found", went.lines, "not stopped on that refusal")
        self.assertIn("operation: KC", went.lines)
        self.assertEqual(self.attempts(fx, went, "KC"), [], "an attempt was recorded")
        self.assertEqual([e for e in went.events if e["op"] == "child" and e["stage"] == "mid"], [], "a child was created")
        self.assertEqual(fx.made(), (False, False), "the commit or the push was made")


if __name__ == "__main__":
    import unittest
    unittest.main()
