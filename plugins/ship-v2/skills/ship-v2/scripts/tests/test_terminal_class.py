"""The E15 lane contract A31 (2): every refusal ship-v2 can emit leaves a terminal status reachable (section 7 (3) of the
lane contract, a terminal status for every run; contract section 9).

THE CLASS. The refusals are enumerated from the code: every exit 5 (`common.refuse`, the save step's refusal in
`visit.py`, `lap`'s count) and every exit 2 (`driver.Usage`: `common.open_run`'s stage check, a file that is not there
or not JSON, a flag pair, the wrong station, a missing or takeable result, a report line the form cannot carry, the
argument parser's own) a command prints, each at every stage it is printed at. For each, the test:

1. brings a fresh run to that stage through ship-v2's own commands and the stand-in stations (`slib`);
2. emits the refusal and holds that it wrote nothing (the run directory byte-equal, the stage unchanged);
3. drives ship-v2's own commands from there to a terminal status (`completed` or `stopped`, exit 10, `result.json`
   written), never by a hand edit of the run directory and never by the refused step itself, with the workspace left
   as it stood at the refusal (an executor who cannot or will not take the step the refusal names). A pause is not
   terminal; a pause's answer is one of ship-v2's own commands and may be used. A file handed to a command (a reading,
   a fixes file, an answer) may be a well-formed one: its content is the executor's or the owner's words.

Every refusal writes nothing, so the run directory after it is byte-equal to the run directory before it: the
refusals one stage prints are emitted on one run, and one way out is then driven from there for all of them.

THE STUCK STAGES. Where no command of ship-v2's reaches a terminal status without a step only the executor can take
outside ship-v2 (the window rule's "put them back" for a path inside the footprint nothing names), the test holds the
stage stuck as found, every command it can take listed with its exit, and does NOT give it an ending (the brief's
rule: a stuck stage is a question for the owner, with its output). It then shows that the refusal's own named remedy
(the path put back, the workspace only, never the run directory) followed by ship-v2's commands reaches the end. A
stage that becomes reachable, or a new stuck stage, fails this test: the class is held either way.

Not enumerated here, each named: exit 2 for `SHIP_V2_TEST_NOW` (a test hook, honored only with `SHIP_V2_TEST=1`) and
`--skill-root` (a test-only flag); `check-input`'s own exit 2 before a run exists (no stage); exit 4 (a file that
fails its schema) and exit 1 (the run directory changed by hand, or a defect) are not refusals of A31 (2)'s class.

With `SHIP_V2_CLASS_TABLE` naming a file, the rows (refusal, stage, exit, the commands that reached the end, the
ending, or the stuck stage's output) are written there as JSON when the module ends; nothing else is written outside
the test's temporary folder.
"""
import os
import shlex
import unittest

import slib
import testlib
from test_save_step import COPY_TEXT, MIRROR, MIRROR_TEXT, run_dir_digest

ROWS = []
BOTTOM = "The run ends here. The block says why."
STRAY = "tests/test_stray.py"
STRAY_TEXT = "STRAY = 1\n"
OUTSIDE_EDIT = "README.md"
FIXED = "def spin(count):\n    return count + %d\n"
# the stages each command runs at (common.py, the command handlers); `report` at `fixed` only while the save step was
# not taken (A31 (1)), so it is never out of turn there by stage
RUNS_AT = {
    "select": ("checked",),
    "hook": ("selected",),
    "visit --station": ("hooked", "built", "fixed"),
    "visit --result": ("visiting",),
    "fix": ("fixing",),
    "lap": ("lap-needed", "exhausted"),
    "pause --question": ("selected", "hooked", "built", "visiting", "fixing", "fixed", "lap-needed", "exhausted",
                         "clean"),
    "pause --answer": ("paused",),
    "report": ("clean", "exhausted", "ending", "visiting", "fixed"),
}


def tearDownModule():
    path = os.environ.get("SHIP_V2_CLASS_TABLE")
    if path:
        testlib.write_json(path, {"rows": ROWS})


class Run(object):
    """One fresh run of a copy of this core beside the stand-in stations, driven to a stage through its own commands."""

    def __init__(self, test, harness="claude-code", ignore_reviews=False, prefix="ship-class-"):
        self.t = test
        self.tmp = testlib.make_scratch(prefix)
        test.addCleanup(testlib.rmtree, self.tmp)
        self.ws = slib.make_repo(self.tmp)
        if ignore_reviews:
            testlib.write_text(os.path.join(self.ws, ".gitignore"), "docs/reviews/\n")
            slib.commit_all(self.ws, "ignore the reviews")
        self.harness = harness
        self.tree = slib.Tree(self.tmp)
        self.drive, self.run_dir = slib.start(test, self.tree, self.tmp, self.ws, harness=harness)
        self.finding = None
        self.files = 0
        self.fixed = None
        self.visit_out = None

    # ---- plumbing --------------------------------------------------------------------------------------------------

    def name(self, stem):
        self.files += 1
        return "%s-%d.json" % (stem, self.files)

    def path(self, rel):
        return os.path.join(self.ws, rel)

    def write(self, rel, text):
        testlib.write_text(self.path(rel), text)

    def phase(self):
        return testlib.load_json(os.path.join(self.run_dir, "checkpoint.json"))["phase"]

    def cmd(self, words, *rest):
        """`words` (`visit --station`, `report`, ...) with `--run-dir` and the rest of its arguments; a flag the rest
        repeats from `words` (`pause --answer`, then `--answer FILE`) is given once."""
        parts = words.split()
        rest = [str(r) for r in rest]
        if len(parts) > 1 and rest and rest[0] == parts[1]:
            parts = parts[:1]
        return self.drive([parts[0], "--run-dir", self.run_dir] + parts[1:] + rest)

    def ok(self, words, *rest):
        code, out, err = self.cmd(words, *rest)
        self.t.assertEqual(code, 0, (words, rest, out, err))
        return out

    def hook_file(self, harness=None, armed=False):
        return slib.hook_file(self.tmp, harness or self.harness, armed, name=self.name("hook"))

    def fixes_file(self, lap, fixes, spec_change=()):
        return slib.fixes_file(self.tmp, self.run_dir, lap, fixes, spec_change, name=self.name("fixes"))

    def question(self, text="A question for the owner, verbatim.", source="station", station="signoff-v2"):
        return slib.question_file(self.tmp, self.run_dir, text, source=source, station=station,
                                  name=self.name("question"))

    def answer(self, pause, words="Go on as you were.", effect=None):
        return slib.answer_file(self.tmp, self.run_dir, pause, words, effect, name=self.name("answer"))

    def plain(self, name, text):
        path = os.path.join(self.tmp, name)
        testlib.write_text(path, text)
        return path

    # ---- the stages --------------------------------------------------------------------------------------------------

    def to_selected(self):
        self.ok("select", "--doc", slib.DOC)
        return self

    def to_hooked(self):
        self.to_selected()
        self.ok("hook", "--reading", self.hook_file())
        return self

    def to_built(self):
        self.to_hooked()
        code, out, err = slib.visit(self.t, self.drive, self.run_dir, "build-v2", "completed", self.ws,
                                    before_result=lambda visit: slib.set_status(self.ws, "A", "built"))
        self.t.assertEqual((code, out["next"]), (0, "visit --station signoff-v2"), (out, err))
        return self

    def signoff(self, mirror=True):
        """signoff-v2's visit as the stand-in writes it: its finding and card through the records, its `Status:` line,
        and the verdict mirror under `docs/reviews/`, untracked, listed in its result and its receipt."""
        out = self.ok("visit --station", "signoff-v2")
        before = slib.sha(self.path(slib.DOC))
        self.finding = slib.raise_finding(self.tmp, self.ws)
        slib.set_status(self.ws, "A", "signed off with conditions")
        if mirror:
            self.write(MIRROR, MIRROR_TEXT)
        after = slib.sha(self.path(slib.DOC))
        result = slib.station_result("signoff-v2", "findings", out, self.ws, doc_move=(before, after))
        if mirror:
            result["records_written"].append({"kind": "verdict_doc", "path": self.path(MIRROR)})
            receipt = testlib.load_json(result["receipt"])
            receipt["steps"].append({"kind": "verdict_doc", "target": MIRROR, "before_sha256": None,
                                     "after_sha256": slib.sha(self.path(MIRROR)), "state": "done"})
            testlib.write_json(result["receipt"], receipt)
        slib.put_result(out, result)
        return self.cmd("visit --result")

    def to_fixing(self):
        self.to_built()
        code, out, err = self.signoff()
        self.t.assertEqual((code, out["next"]), (0, "fix"), (out, err))
        return self

    def fix(self, lap):
        self.write("src/turnstile.py", FIXED % (lap + 1))
        out = self.ok("fix", "--fixes", self.fixes_file(lap, [{"finding": self.finding, "paths": ["src/turnstile.py"],
                                                                "summary": "lap %d" % lap}]))
        self.t.assertEqual(out["next"], "visit --station recheck-v2", out)
        self.fixed = out
        return out

    def to_fixed(self):
        self.to_fixing()
        self.fix(1)
        return self

    def take_step(self, step=None):
        step = step or self.fixed["save_step"]
        for command in step["commands"]:
            argv = shlex.split(command)
            self.t.assertEqual(argv[0], "git", command)
            testlib.git(self.ws, argv[1:])

    def to_fixed_saved(self):
        self.to_fixed()
        self.take_step()
        return self

    def open_recheck(self):
        self.visit_out = self.ok("visit --station", "recheck-v2")
        return self.visit_out

    def recheck(self, which="not_clear", append=False):
        out = self.open_recheck()
        writes = []
        if append:
            before = slib.sha(self.path(MIRROR))
            with open(self.path(MIRROR), "a", encoding="utf-8") as fh:
                fh.write(COPY_TEXT)
            writes = [{"kind": "verdict_doc_copy", "path": self.path(MIRROR), "appended": True, "sha256_before": before,
                       "sha256_after": slib.sha(self.path(MIRROR))}]
        slib.put_result(out, slib.station_result("recheck-v2", which, out, self.ws, writes=writes))
        return self.cmd("visit --result")

    def to_lap_needed(self):
        self.to_fixed_saved()
        code, out, err = self.recheck()
        self.t.assertEqual((code, out["next"]), (0, "lap"), (out, err))
        return self

    def to_exhausted(self):
        self.to_lap_needed()
        self.t.assertEqual(self.ok("lap")["next"], "fix")
        self.fix(2)
        self.t.assertIsNone(self.fixed["save_step"], "the mirror stands committed: no step on lap 2")
        code, out, err = self.recheck()
        self.t.assertEqual((code, out["next"]), (0, "report"), (out, err))
        self.t.assertEqual(self.phase(), "exhausted")
        return self

    def to_clean(self):
        self.to_built()
        code, out, err = slib.visit(self.t, self.drive, self.run_dir, "signoff-v2", "clean", self.ws)
        self.t.assertEqual((code, out["next"]), (0, "report"), (out, err))
        self.t.assertEqual(self.phase(), "clean")
        return self

    def to_ending(self):
        self.to_hooked()
        code, out, err = slib.visit(self.t, self.drive, self.run_dir, "build-v2", "partial", self.ws)
        self.t.assertEqual((code, out["next"]), (0, "report"), (out, err))
        self.t.assertEqual(self.phase(), "ending")
        return self

    def to_visiting(self):
        self.to_hooked()
        self.visit_out = self.ok("visit --station", "build-v2")
        return self

    def to_paused(self, stage_fn):
        stage_fn()
        stage = self.phase()
        self.t.assertEqual(self.ok("pause --question", "--question", self.question())["next"], "pause --answer")
        return stage

    # ---- a valid file for every command, so an out-of-turn refusal is the stage check's ---------------------------

    def any_args(self, words):
        return {"select": ["--doc", slib.DOC], "hook": ["--reading", self.hook_file()],
                "visit --station": ["build-v2"], "visit --result": [],
                "fix": ["--fixes", self.fixes_file(1, [])], "lap": [],
                "pause --question": ["--question", self.question()],
                "pause --answer": ["--answer", self.answer(1)],
                "report": ["--bottom-line", BOTTOM]}[words]


@unittest.skipUnless(slib.usable(), "needs jsonschema, the records component and the three stations beside this core")
class EveryRefusalLeavesATerminalStatus(unittest.TestCase):
    """Each test: one stage (or a planted condition at it), its refusals, then its way out."""

    # ---- the three checks --------------------------------------------------------------------------------------------

    def refused(self, run, label, code, words, *rest, **kw):
        """`words rest` refused with `code` at the run's stage, nothing written; recorded as a row."""
        stage = run.phase()
        digest = run_dir_digest(run.run_dir)
        argv = kw.get("argv")
        got, out, err = run.drive(argv) if argv else run.cmd(words, *rest)
        self.assertEqual(got, code, (label, stage, out, err))
        self.assertEqual((run_dir_digest(run.run_dir), run.phase()), (digest, stage), (label, "nothing written"))
        said = (out or {}).get("reason") or err.strip()
        if kw.get("says"):
            self.assertIn(kw["says"], said, label)
        row = {"refusal": label, "stage": stage, "exit": code, "said": said[:240]}
        self.rows.append(row)
        return out, err

    def out_of_turn(self, run, skip=()):
        """Every command whose stages leave out the run's stage: exit 2, the stage check's words, nothing written."""
        stage = run.phase()
        for words, stages in sorted(RUNS_AT.items()):
            if stage in stages or words in skip:
                continue
            self.refused(run, "out of turn: %s" % words, 2, words, *run.any_args(words), says="is at stage")

    def way_out(self, run, steps, ending):
        """ship-v2's own commands from the run's stage to a terminal status; every row of this stage gets them."""
        done = []
        last = None
        for words, rest in steps:
            code, out, err = run.cmd(words, *rest)
            done.append("%s (exit %d)" % (words, code))
            self.assertIn(code, (0, 10), (words, rest, out, err))
            last = (code, out, err)
        code, out, err = last
        self.assertEqual(code, 10, (out, err))
        self.assertTrue(os.path.isfile(os.path.join(run.run_dir, "result.json")))
        self.assertEqual(run.phase(), "done")
        self.assertEqual((out["status"], out.get("stop_tag")), ending, out)
        self.assertEqual(slib.validate_trace(run.run_dir)[0], 0)
        ending_words = "%s%s" % (out["status"], " " + out["stop_tag"] if out.get("stop_tag") else "")
        for row in self.rows:
            row.update(reached_by=list(done), ending=ending_words, stuck=False)
        ROWS.extend(self.rows)
        self.rows = []
        self.last_way = (done, ending_words)
        return out

    def stuck(self, run, attempts, remedy, steps, ending):
        """The stage stuck as found: each attempt refused (exit 2 or 5) or a pause that comes back to it, no result
        written; recorded with the outputs. Then the refusal's own remedy (the workspace only) and the way out."""
        stage = run.phase()
        seen = []
        for words, rest, code in attempts:
            got, out, err = run.cmd(words, *rest)
            seen.append({"command": words, "exit": got, "said": ((out or {}).get("reason") or err.strip())[:240],
                         "stage_after": run.phase()})
            self.assertEqual(got, code, (words, out, err))
        self.assertFalse(os.path.isfile(os.path.join(run.run_dir, "result.json")))
        self.assertIn(run.phase(), (stage, "paused"))
        for row in self.rows:
            row.update(stuck=True, tried=seen)
        remedy()
        stuck_rows, self.rows = self.rows, []
        out = self.way_out(run, steps, ending)
        for row in stuck_rows:
            row.update(reached_by=None, ending=None, remedy="the path put back (the workspace only)",
                       reached_after_the_remedy=self.last_way[0], ending_after_the_remedy=self.last_way[1])
        ROWS.extend(stuck_rows)
        return out

    def setUp(self):
        self.rows = []

    def report_step(self):
        return ("report", ["--bottom-line", BOTTOM])

    # ---- checked, selected, hooked -----------------------------------------------------------------------------------

    def test_checked(self):
        run = Run(self)
        self.out_of_turn(run)
        self.refused(run, "select: the named doc is not an .md inside the workspace", 5, "select", "--doc",
                     "docs/plans/none.md", says="not an existing .md")
        self.refused(run, "select: --slice against the input's slice", 2, "select", "--doc", slib.DOC, "--slice", "B",
                     says="--slice takes")
        self.refused(run, "select: a hunt name that is not one path segment", 2, "select", "--name", "Turn/Stile")
        self.refused(run, "check-input again on the run directory", 2, None,
                     argv=["check-input", run.run_dir + "-input.json"])
        self.refused(run, "the argument parser: an unknown flag", 2, None,
                     argv=["select", "--run-dir", run.run_dir, "--unknown"])
        self.refused(run, "visit: both --station and --result", 2, "visit --station", "build-v2", "--result")
        self.refused(run, "pause: neither --question nor --answer", 2, "pause")
        self.way_out(run, [("select", ["--doc", slib.DOC]), ("hook", ["--reading", run.hook_file()]),
                           ("visit --station", ["build-v2"]), self.report_step()], ("stopped", "visit-unfinished"))

    def test_selected(self):
        run = Run(self).to_selected()
        self.out_of_turn(run)
        self.refused(run, "hook: no such reading file", 2, "hook", "--reading", os.path.join(run.tmp, "none.json"))
        self.refused(run, "hook: a reading that is not JSON", 2, "hook", "--reading", run.plain("bad.json", "{"))
        self.refused(run, "hook: a reading that is not an object", 2, "hook", "--reading", run.plain("list.json", "[]"))
        self.refused(run, "hook: another harness's reading", 5, "hook", "--reading", run.hook_file(harness="codex-cli"),
                     says="this harness's own adapter")
        self.refused(run, "pause --question: a question for another run", 5, "pause --question", "--question",
                     slib.question_file(run.tmp, run.run_dir + "-other", "Another run's question.",
                                        name=run.name("question")), says="names the run")
        self.way_out(run, [("hook", ["--reading", run.hook_file()]), ("visit --station", ["build-v2"]),
                           self.report_step()], ("stopped", "visit-unfinished"))

    def test_selected_on_codex(self):
        run = Run(self, harness="codex-cli").to_selected()
        self.refused(run, "hook: an armed reading from a harness with no Stop hook", 5, "hook", "--reading",
                     run.hook_file(armed=True), says="only Claude Code has")
        self.way_out(run, [("hook", ["--reading", run.hook_file()]), ("visit --station", ["build-v2"]),
                           self.report_step()], ("stopped", "visit-unfinished"))

    def test_hooked(self):
        run = Run(self).to_hooked()
        self.out_of_turn(run, skip=("visit --station",))
        for station in ("signoff-v2", "recheck-v2"):
            self.refused(run, "visit --station: not the loop's next station (%s)" % station, 2, "visit --station",
                         station, says="compose by name")
        self.refused(run, "visit: neither --station nor --result", 2, "visit")
        self.way_out(run, [("visit --station", ["build-v2"]), self.report_step()], ("stopped", "visit-unfinished"))

    # ---- visiting ----------------------------------------------------------------------------------------------------

    def test_visiting_with_no_result(self):
        run = Run(self).to_visiting()
        self.out_of_turn(run)
        self.refused(run, "visit --result: the station has written no result", 2, "visit --result",
                     says="no result")
        self.way_out(run, [self.report_step()], ("stopped", "visit-unfinished"))

    def test_visiting_with_a_result_it_takes(self):
        run = Run(self).to_visiting()
        before = slib.sha(run.path(slib.DOC))
        slib.set_status(run.ws, "A", "built")
        doc = slib.station_result("build-v2", "completed", run.visit_out, run.ws,
                                  doc_move=(before, slib.sha(run.path(slib.DOC))))
        slib.put_result(run.visit_out, doc)
        self.refused(run, "report at visiting: the result stands and visit --result takes it", 2, "report",
                     "--bottom-line", BOTTOM, says="run `visit --result` first")
        self.way_out(run, [("visit --result", []), ("visit --station", ["signoff-v2"]), self.report_step()],
                     ("stopped", "visit-unfinished"))

    def test_visiting_with_a_result_it_refuses(self):
        run = Run(self).to_visiting()
        slib.put_result(run.visit_out, {"not": "a build-v2 result"})
        self.refused(run, "visit --result: a result that fails the station's own schema", 5, "visit --result",
                     says="own result schema")
        doc = slib.station_result("build-v2", "completed", run.visit_out, run.ws)
        doc["run_id"] = "another-run"
        slib.put_result(run.visit_out, doc)
        self.refused(run, "visit --result: a result for another run", 5, "visit --result", says="another-run")
        self.way_out(run, [self.report_step()], ("stopped", "visit-unfinished"))

    def test_visiting_with_an_unnamed_path_inside_the_footprint(self):
        run = Run(self).to_visiting()
        doc = slib.station_result("build-v2", "completed", run.visit_out, run.ws, doc_move=(None, None))
        slib.put_result(run.visit_out, doc)
        run.write(STRAY, STRAY_TEXT)
        self.refused(run, "visit --result: the window, a path inside the footprint nothing names", 5, "visit --result",
                     says=STRAY)
        self.way_out(run, [self.report_step()], ("stopped", "visit-unfinished"))

    # ---- built -------------------------------------------------------------------------------------------------------

    def test_built(self):
        run = Run(self).to_built()
        self.out_of_turn(run, skip=("visit --station",))
        self.refused(run, "visit --station: not the loop's next station (recheck-v2)", 2, "visit --station",
                     "recheck-v2", says="compose by name")
        self.way_out(run, [("visit --station", ["signoff-v2"]), self.report_step()], ("stopped", "visit-unfinished"))

    def test_built_with_an_unnamed_path_inside_the_footprint(self):
        run = Run(self).to_built()
        run.write(STRAY, STRAY_TEXT)
        self.refused(run, "visit --station: the window, a path inside the footprint nothing names", 5,
                     "visit --station", "signoff-v2", says=STRAY)
        self.stuck(run, [("visit --station", ["signoff-v2"], 5), ("report", ["--bottom-line", BOTTOM], 2),
                         ("pause --question", ["--question", run.question()], 0),
                         ("pause --answer", ["--answer", run.answer(1)], 5), ("report", ["--bottom-line", BOTTOM], 2)],
                   lambda: os.remove(run.path(STRAY)),
                   [("pause --answer", ["--answer", run.answer(1)]), ("visit --station", ["signoff-v2"]),
                    self.report_step()], ("stopped", "visit-unfinished"))

    # ---- fixing and its pause ------------------------------------------------------------------------------------------

    def test_fixing(self):
        run = Run(self).to_fixing()
        self.out_of_turn(run)
        fix = {"finding": run.finding, "paths": ["src/turnstile.py"], "summary": "the fix"}
        self.refused(run, "fix: no such fixes file", 2, "fix", "--fixes", os.path.join(run.tmp, "none.json"))
        self.refused(run, "fix: the argument parser, --fixes missing", 2, "fix")
        self.refused(run, "fix: a fixes file for another lap", 5, "fix", "--fixes", run.fixes_file(2, [fix]),
                     says="for lap 2")
        self.refused(run, "fix: a finding the lap did not name", 5, "fix", "--fixes",
                     run.fixes_file(1, [dict(fix, finding="F-nothing")]), says="not a finding this lap named")
        self.refused(run, "fix: one finding twice", 5, "fix", "--fixes",
                     run.fixes_file(1, [fix, dict(fix, summary="again")]), says="fixed twice")
        self.refused(run, "fix: a path that is not workspace-relative", 5, "fix", "--fixes",
                     run.fixes_file(1, [dict(fix, paths=["../outside.py"])]), says="not workspace-relative")
        self.refused(run, "fix: a fixes file for another run", 5, "fix", "--fixes",
                     slib.fixes_file(run.tmp, run.run_dir + "-other", 1, [fix], name=run.name("fixes")),
                     says="names the run")
        self.way_out(run, [("fix", ["--fixes", run.fixes_file(1, [])]), self.report_step()],
                     ("stopped", "recheck-stopped"))

    def test_fixing_with_an_unnamed_path_inside_the_footprint(self):
        run = Run(self).to_fixing()
        run.write("src/turnstile.py", FIXED % 2)
        run.write(STRAY, STRAY_TEXT)
        fix = {"finding": run.finding, "paths": ["src/turnstile.py"], "summary": "the fix"}
        self.refused(run, "fix: the window, a path inside the footprint no fix names", 5, "fix", "--fixes",
                     run.fixes_file(1, [fix]), says=STRAY)
        self.way_out(run, [("fix", ["--fixes", run.fixes_file(1, [dict(fix, paths=["src/turnstile.py", STRAY])])]),
                           self.report_step()], ("stopped", "recheck-stopped"))

    def test_paused_at_fixing(self):
        run = Run(self)
        run.to_paused(run.to_fixing)
        self.out_of_turn(run)
        self.refused(run, "pause --answer: no such answer file", 2, "pause --answer", "--answer",
                     os.path.join(run.tmp, "none.json"))
        self.refused(run, "pause --answer: an answer to another pause", 5, "pause --answer", "--answer", run.answer(2),
                     says="the open pause")
        self.refused(run, "pause --answer: blank words", 5, "pause --answer", "--answer", run.answer(1, words="   "),
                     says="no words")
        self.refused(run, "pause --answer: an answer for another run", 5, "pause --answer", "--answer",
                     slib.answer_file(run.tmp, run.run_dir + "-other", 1, "Yes.", name=run.name("answer")),
                     says="names the run")
        self.refused(run, "pause --answer: a waiver of a finding the records do not hold", 5, "pause --answer",
                     "--answer", run.answer(1, "Waive it.", {"kind": "waive", "finding": "F-nothing"}),
                     says="hold no finding")
        self.refused(run, "pause --answer: a reopening of a finding that stands open", 5, "pause --answer",
                     "--answer", run.answer(1, "Reopen it.", {"kind": "reopen", "finding": run.finding}),
                     says="stands 'open'")
        self.refused(run, "pause: both --question and --answer", 2, "pause", "--question", run.question(), "--answer",
                     run.answer(1))
        self.way_out(run, [("pause --answer", ["--answer", run.answer(1)]),
                           ("fix", ["--fixes", run.fixes_file(1, [])]), self.report_step()],
                     ("stopped", "recheck-stopped"))

    # ---- fixed: the save step (C3-1) -----------------------------------------------------------------------------------

    def fixed_refusals(self, run, why):
        self.refused(run, "visit --station recheck-v2: the save step not taken (%s)" % why, 5, "visit --station",
                     "recheck-v2", says=why)
        self.refused(run, "visit --station: not the loop's next station (signoff-v2)", 2, "visit --station",
                     "signoff-v2", says="compose by name")

    def test_fixed_the_owner_declines_the_step(self):
        run = Run(self).to_fixed()
        self.out_of_turn(run, skip=("visit --station",))
        self.fixed_refusals(run, "untracked")
        self.way_out(run, [self.report_step()], ("stopped", "recheck-stopped"))

    def test_fixed_a_hook_refuses_the_commit(self):
        from test_unsaved_mirror import REFUSING_HOOK, git_with_hooks
        run = Run(self).to_fixed()
        hooks = os.path.join(run.tmp, "hooks")
        testlib.write_text(os.path.join(hooks, "pre-commit"), REFUSING_HOOK)
        os.chmod(os.path.join(hooks, "pre-commit"), 0o755)
        self.assertEqual([git_with_hooks(run.ws, shlex.split(c)[1:], hooks)[0]
                          for c in run.fixed["save_step"]["commands"]], [0, 1])
        self.fixed_refusals(run, "staged, never committed")
        self.way_out(run, [self.report_step()], ("stopped", "recheck-stopped"))

    def test_fixed_an_ignored_mirror(self):
        run = Run(self, ignore_reviews=True).to_fixed()
        self.fixed_refusals(run, "ignore rules")
        self.way_out(run, [self.report_step()], ("stopped", "recheck-stopped"))

    def test_fixed_paused_then_declined(self):
        run = Run(self)
        run.to_paused(run.to_fixed)
        self.out_of_turn(run)
        self.way_out(run, [("pause --answer", ["--answer", run.answer(1, "No, do not commit it.")]),
                           self.report_step()], ("stopped", "recheck-stopped"))

    def test_fixed_on_the_extra_lap(self):
        run = Run(self).to_fixed_saved()
        code, out, err = run.recheck("not_clear", append=True)
        self.assertEqual((code, out["next"]), (0, "lap"), (out, err))
        run.ok("lap")
        run.fix(2)
        self.fixed_refusals(run, "differs from its committed bytes")
        self.way_out(run, [self.report_step()], ("stopped", "recheck-stopped"))

    def test_fixed_with_the_mirror_saved(self):
        run = Run(self).to_fixed_saved()
        self.out_of_turn(run, skip=("visit --station",))
        self.refused(run, "report at fixed: the mirror committed, the next move is the recheck visit", 2, "report",
                     "--bottom-line", BOTTOM, says="visit --station recheck-v2")
        self.way_out(run, [("visit --station", ["recheck-v2"]), self.report_step()], ("stopped", "visit-unfinished"))

    def test_fixed_saved_with_an_unnamed_path_inside_the_footprint(self):
        run = Run(self).to_fixed_saved()
        run.write(STRAY, STRAY_TEXT)
        self.refused(run, "visit --station recheck-v2: the window, a path inside the footprint nothing names "
                          "(the mirror committed)", 5, "visit --station", "recheck-v2", says=STRAY)
        self.stuck(run, [("visit --station", ["recheck-v2"], 5), ("report", ["--bottom-line", BOTTOM], 2),
                         ("pause --question", ["--question", run.question()], 0),
                         ("pause --answer", ["--answer", run.answer(1)], 5)],
                   lambda: os.remove(run.path(STRAY)),
                   [("pause --answer", ["--answer", run.answer(1)]), ("visit --station", ["recheck-v2"]),
                    self.report_step()], ("stopped", "visit-unfinished"))

    def test_fixed_unsaved_with_an_unnamed_path_inside_the_footprint(self):
        run = Run(self).to_fixed()
        run.write(STRAY, STRAY_TEXT)
        self.refused(run, "visit --station recheck-v2: the window, a path inside the footprint nothing names "
                          "(the mirror unsaved)", 5, "visit --station", "recheck-v2", says=STRAY)
        self.refused(run, "report at fixed: the window, a path inside the footprint nothing names (the mirror "
                          "unsaved)", 5, "report", "--bottom-line", BOTTOM, says=STRAY)
        self.stuck(run, [("visit --station", ["recheck-v2"], 5), ("report", ["--bottom-line", BOTTOM], 5),
                         ("pause --question", ["--question", run.question()], 0),
                         ("pause --answer", ["--answer", run.answer(1)], 5)],
                   lambda: os.remove(run.path(STRAY)),
                   [("pause --answer", ["--answer", run.answer(1)]), self.report_step()],
                   ("stopped", "recheck-stopped"))

    def test_fixed_unsaved_with_a_path_outside_the_footprint(self):
        run = Run(self).to_fixed()
        run.write(OUTSIDE_EDIT, "# Turnstile\n\nedited after the fix\n")
        self.way_out(run, [self.report_step()], ("stopped", "outside-footprint"))

    # ---- lap-needed, exhausted -----------------------------------------------------------------------------------------

    def test_lap_needed(self):
        run = Run(self).to_lap_needed()
        self.out_of_turn(run)
        self.way_out(run, [("lap", []), ("fix", ["--fixes", run.fixes_file(2, [])]),
                           ("visit --station", ["recheck-v2"]), self.report_step()], ("stopped", "visit-unfinished"))

    def test_exhausted(self):
        run = Run(self).to_exhausted()
        self.out_of_turn(run)
        self.refused(run, "lap: a lap beyond the allowed count", 5, "lap", says="beyond the 2 the run allows")
        self.way_out(run, [self.report_step()], ("stopped", "extra-lap-exhausted"))

    def test_exhausted_with_an_unnamed_path_inside_the_footprint(self):
        run = Run(self).to_exhausted()
        run.write(STRAY, STRAY_TEXT)
        self.refused(run, "report at exhausted: the window, a path inside the footprint nothing names", 5, "report",
                     "--bottom-line", BOTTOM, says=STRAY)
        self.stuck(run, [("report", ["--bottom-line", BOTTOM], 5), ("lap", [], 5),
                         ("pause --question", ["--question", run.question()], 0),
                         ("pause --answer", ["--answer", run.answer(1)], 5)],
                   lambda: os.remove(run.path(STRAY)),
                   [("pause --answer", ["--answer", run.answer(1)]), self.report_step()],
                   ("stopped", "extra-lap-exhausted"))

    # ---- clean, ending, done -------------------------------------------------------------------------------------------

    def test_clean(self):
        run = Run(self).to_clean()
        self.out_of_turn(run)
        self.refused(run, "report: no --bottom-line", 2, "report", says="--bottom-line")
        self.refused(run, "report: a bottom line the SHIP: block cannot carry", 2, "report", "--bottom-line",
                     "One line\rtwo.", says="cannot carry")
        self.refused(run, "report: a blank --skill-note", 2, "report", "--bottom-line", BOTTOM, "--skill-note", " ",
                     says="--skill-note")
        self.way_out(run, [self.report_step()], ("completed", None))

    def test_clean_with_an_unnamed_path_inside_the_footprint(self):
        run = Run(self).to_clean()
        run.write(STRAY, STRAY_TEXT)
        self.refused(run, "report at clean: the window, a path inside the footprint nothing names", 5, "report",
                     "--bottom-line", BOTTOM, says=STRAY)
        self.stuck(run, [("report", ["--bottom-line", BOTTOM], 5),
                         ("pause --question", ["--question", run.question()], 0),
                         ("pause --answer", ["--answer", run.answer(1)], 5)],
                   lambda: os.remove(run.path(STRAY)),
                   [("pause --answer", ["--answer", run.answer(1)]), self.report_step()], ("completed", None))

    def test_ending(self):
        run = Run(self).to_ending()
        self.out_of_turn(run)
        self.way_out(run, [self.report_step()], ("stopped", "build-not-complete"))

    def test_done(self):
        run = Run(self).to_ending()
        code, out, err = slib.report(run.drive, run.run_dir, BOTTOM)
        self.assertEqual(code, 10, (out, err))
        self.out_of_turn(run)
        for row in self.rows:
            row.update(reached_by=["none needed: the run is over"], ending="stopped build-not-complete", stuck=False)
        ROWS.extend(self.rows)
        self.rows = []


if __name__ == "__main__":
    unittest.main()
