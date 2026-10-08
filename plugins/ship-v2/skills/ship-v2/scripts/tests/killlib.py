"""The kill sweep's fixtures (the E15 lane contract A29 (2)): a ship run driven step by step, then killed at a line.

A `Case` is one ship run on the stand-in tree (`slib.Tree`), its workspace and run directory under `<tmp>/case`, the
copied plugins beside it (so a restore copies only the case). A flow is the list of its steps, each a ship command
(`Ship`) or what the session or a station does between commands (`Do`: a station's own records and result, an input
file). `Sweep` runs the flow once to its end (the reference), copying the case before every swept command and taking
what the run holds after it; then, for each swept command, it runs the command once under `killpoint.py record` to
find its first and last write, and for EVERY line between them (the lines of this core's own scripts, numbered as
the interpreter runs them) it restores the copy, starts the command under `killpoint.py stop K`, SIGKILLs that PID
when it stops at line K, runs the same command again (the executor's next command), and requires:

- the run then holds exactly what the uninterrupted command left (`facts`): every file of the workspace (`.git`
  aside) and of the run directory byte for byte, so no records event, trace line, run file, receipt or doc line is
  written twice and no temporary file or journal is left; a grant's receipt may carry `settled` (the settle's own
  word that the next command finished it), nothing else;
- every later step of the flow exits as it did in the reference, and the run reaches the same terminal status with
  the same `station_result` and the same files.

The rerun and the byte comparison run at every kill point. The rest of the flow is replayed to its terminal status
once per distinct state a kill leaves (every byte of the workspace and the run directory, before the rerun): two kill
points that leave the same bytes start the same deterministic commands (the clock is fixed, `SHIP_V2_TEST_NOW`), so
the replay of the first stands for both, and `ran` says how many replays ran. `ran` counts the kill points per
command for the report.
"""
import copy
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time

import cr25lib
import slib
import testlib

KILLPOINT = os.path.join(testlib.TESTS, "killpoint.py")
BOTTOM = "The slice went through the loop. Read the block."
# the receipt key the settle adds when the next command finishes a cut-off grant (grant.settle)
SETTLE_WORDS = ("settled",)


class Ship(object):
    def __init__(self, name, args, swept=True):
        self.name, self.args, self.swept = name, args, swept


class Do(object):
    def __init__(self, name, fn):
        self.name, self.fn = name, fn


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


class Case(object):
    """One ship run under `<tmp>/case` on the stand-in tree, driven the way the executor drives it."""

    def __init__(self, test, tmp, majors=1):
        self.test, self.tmp = test, tmp
        self.tree = slib.Tree(tmp)
        self.dir = os.path.join(tmp, "case")
        os.makedirs(self.dir)
        self.ws = slib.make_repo(self.dir, slib.build_doc(slices=cr25lib.ONE_SLICE))
        self.drive, self.run_dir = slib.start(test, self.tree, self.dir, self.ws)
        self.findings = []
        self.majors = majors

    def path(self, name):
        return os.path.join(self.dir, name)

    def ship(self, args):
        return self.drive(args)

    def visit_out(self):
        """The open visit's run id and run directory, as `visit --station` printed them (from `ship.json`)."""
        visit = testlib.load_json(os.path.join(self.run_dir, "ship.json"))["visit"]
        return {"visit_run_id": visit["run_id"], "visit_run_dir": visit["run_dir"]}

    def doc_sha(self):
        return slib.sha(os.path.join(self.ws, slib.DOC))

    # ---- what the stations write while their visit is open (their own records and result) ------------------------

    def build_runs(self):
        visit, before = self.visit_out(), self.doc_sha()
        cr25lib.card(self.dir, self.ws, "build-v2", "not started", "built", "build-run")
        slib.put_result(visit, slib.station_result("build-v2", "completed", visit, self.ws,
                                                   doc_move=(before, self.doc_sha())))

    def signoff_runs(self):
        visit, before = self.visit_out(), self.doc_sha()
        del self.findings[:]
        for index in range(self.majors):
            at = slib.MAJOR_AT if index == 0 else cr25lib.SECOND_AT
            self.findings.append(slib.raise_finding(self.dir, self.ws, location=at, card=None,
                                                    claim="the counter skips turn %d" % index))
        cr25lib.card(self.dir, self.ws, "signoff-v2", "built", "signed off with conditions", "signoff-run")
        slib.put_result(visit, slib.station_result("signoff-v2", "findings", visit, self.ws,
                                                   doc_move=(before, self.doc_sha())))

    def recheck_runs(self, which, fixed=None, card=None, run_id="recheck-run"):
        visit, before = self.visit_out(), self.doc_sha()
        if fixed is not None:
            cr25lib.recheck(self.dir, self.ws, self.findings[0], fixed, card[0], card[1], run_id)
        row = slib.doc_write(self.ws, before)
        slib.put_result(visit, slib.station_result("recheck-v2", which, visit, self.ws, writes=[row] if row else []))

    def fixes(self, lap, name, touch=True):
        rows = []
        if touch:
            testlib.write_text(os.path.join(self.ws, "src", "turnstile.py"),
                               "def spin(count):\n    return count + %d\n" % (lap + 5))
            rows.append({"finding": self.findings[0], "paths": ["src/turnstile.py"], "summary": "attempt %d" % lap})
        slib.fixes_file(self.dir, self.run_dir, lap, rows, name=name)


def visit_steps(case, station, runs):
    run = case.run_dir
    return [Ship("visit --station %s" % station, ["visit", "--run-dir", run, "--station", station]),
            Do("%s runs" % station, runs),
            Ship("visit --result (%s)" % station, ["visit", "--run-dir", run, "--result"])]


def through_signoff(case):
    run = case.run_dir
    return ([Ship("select", ["select", "--run-dir", run, "--doc", slib.DOC]),
             Do("the hook reading", lambda: slib.hook_file(case.dir)),
             Ship("hook", ["hook", "--run-dir", run, "--reading", case.path("hook.json")])]
            + visit_steps(case, "build-v2", case.build_runs) + visit_steps(case, "signoff-v2", case.signoff_runs))


def grant_flow(case):
    """select, hook, three visits, ship's own waive-or-hold question and the owner's waiver, the lap's (empty)
    fixes, recheck-v2 finding nothing open, and the report: every command that saves but `lap`."""
    run = case.run_dir

    def question():
        slib.question_file(case.dir, run, "Only you can rule this finding: waive it or hold?", source="ship",
                           station=None, finding=case.findings[0], name="q1.json")

    def answer():
        slib.answer_file(case.dir, run, 1, "Waive it, a bench quirk", {"kind": "waive", "finding": case.findings[0]},
                         name="a1.json")
    return (through_signoff(case)
            + [Do("the question file", question),
               Ship("pause --question", ["pause", "--run-dir", run, "--question", case.path("q1.json")]),
               Do("the answer file", answer),
               Ship("pause --answer (a waiver)", ["pause", "--run-dir", run, "--answer", case.path("a1.json")]),
               Do("the lap's fixes file", lambda: case.fixes(1, "fixes-1.json", touch=False)),
               Ship("fix", ["fix", "--run-dir", run, "--fixes", case.path("fixes-1.json")])]
            + visit_steps(case, "recheck-v2", lambda: case.recheck_runs("nothing_open"))
            + [Ship("report", ["report", "--run-dir", run, "--bottom-line", BOTTOM])])


def lap_flow(case):
    """A first lap whose recheck is not clear, then `lap` (the one command the grant flow does not reach), the extra
    lap's fix, recheck-v2 ALL CLEAR and the report. Only `lap` is swept here."""
    run = case.run_dir
    steps = [Ship(s.name, s.args, swept=False) if isinstance(s, Ship) else s for s in through_signoff(case)]
    steps += [Do("lap 1's fixes", lambda: case.fixes(1, "fixes-1.json")),
              Ship("fix", ["fix", "--run-dir", run, "--fixes", case.path("fixes-1.json")], swept=False)]
    steps += [Ship(s.name, s.args, swept=False) if isinstance(s, Ship) else s for s in visit_steps(
        case, "recheck-v2", lambda: case.recheck_runs("not_clear", False, ("signed off with conditions",
                                                                           "signed off with conditions"),
                                                      "recheck-1"))]
    steps += [Ship("lap", ["lap", "--run-dir", run]),
              Do("lap 2's fixes", lambda: case.fixes(2, "fixes-2.json")),
              Ship("fix", ["fix", "--run-dir", run, "--fixes", case.path("fixes-2.json")], swept=False)]
    steps += [Ship(s.name, s.args, swept=False) if isinstance(s, Ship) else s for s in visit_steps(
        case, "recheck-v2", lambda: case.recheck_runs("all_clear", True, ("signed off with conditions",
                                                                          "signed off"), "recheck-2"))]
    return steps + [Ship("report", ["report", "--run-dir", run, "--bottom-line", BOTTOM], swept=False)]


# ---- what the run holds -------------------------------------------------------------------------------------------

def _normal(rel, data):
    """A grant's receipt without the settle's own word; every other file as its bytes."""
    if os.path.basename(rel).startswith("receipt-") and rel.endswith(".json"):
        try:
            doc = json.loads(data.decode("utf-8"))
        except ValueError:
            return data
        for key in SETTLE_WORDS:
            doc.pop(key, None)
        return json.dumps(doc, sort_keys=True).encode("utf-8")
    return data


def facts(case, raw=False):
    """Every file of the workspace (`.git` aside) and of the run directory, by its sha256 (receipts normalized and
    `result.json` left to `ending`, unless `raw`)."""
    out = {}
    for label, base in (("ws", case.ws), ("run", case.run_dir)):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d != ".git")
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, base).replace(os.sep, "/")
                if label == "run" and rel == "result.json" and not raw:
                    continue
                with open(full, "rb") as fh:
                    data = fh.read()
                out["%s/%s" % (label, rel)] = sha_bytes(data if raw else _normal(rel, data))
    return out


def ending(case):
    """The run's terminal facts: its stage and, when it has one, its result's status, tag, station result and the
    paths and kinds of its writes."""
    phase = testlib.load_json(os.path.join(case.run_dir, "checkpoint.json"))["phase"]
    path = os.path.join(case.run_dir, "result.json")
    if not os.path.exists(path):
        return {"phase": phase}
    doc = testlib.load_json(path)
    return {"phase": phase, "status": doc["status"], "stop_tag": doc["stop_tag"],
            "station_result": doc["station_result"], "trace": doc["trace"],
            "writes": sorted((w["path"], w["kind"]) for w in doc["writes"])}


def diff(want, got):
    keys = sorted(set(want) | set(got))
    return ["%s: %s != %s" % (k, (want.get(k) or "absent")[:12] if isinstance(want.get(k), str) else want.get(k),
                              (got.get(k) or "absent")[:12] if isinstance(got.get(k), str) else got.get(k))
            for k in keys if want.get(k) != got.get(k)]


# ---- the tracer ---------------------------------------------------------------------------------------------------

def recorded(case, args, out):
    proc = subprocess.run([sys.executable, KILLPOINT, "record", out, "-", case.drive.script] + list(args),
                          cwd=case.dir, env=case.drive.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, testlib.load_json(out)


def killed_at(case, args, line, out, deadline=120):
    """True once the command, stopped at `line`, was SIGKILLed by this test; False when it ended first."""
    proc = subprocess.Popen([sys.executable, KILLPOINT, "stop", out, str(line), case.drive.script] + list(args),
                            cwd=case.dir, env=case.drive.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    until = time.time() + deadline
    try:
        while time.time() < until:
            pid, status = os.waitpid(proc.pid, os.WUNTRACED | os.WNOHANG)
            if pid and os.WIFSTOPPED(status):
                os.kill(proc.pid, signal.SIGKILL)
                os.waitpid(proc.pid, 0)
                proc.returncode = -signal.SIGKILL
                return True
            if pid:
                proc.returncode = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                return False
            time.sleep(0.002)
        raise AssertionError("the command never reached line %d nor ended" % line)
    finally:
        if proc.returncode is None:
            proc.kill()
            proc.wait()


# ---- the sweep ----------------------------------------------------------------------------------------------------

class Sweep(object):
    """One flow, run once as the reference, then killed at every line between each swept command's first and last
    write (module docstring)."""

    def __init__(self, test, tmp, flow, majors=1):
        self.test, self.tmp = test, tmp
        self.case = Case(test, tmp, majors=majors)
        self.steps = flow(self.case)
        self.snaps = os.path.join(tmp, "snaps")
        os.makedirs(self.snaps)
        self.pre, self.post, self.codes = {}, {}, {}
        self.ran = {}
        self._reference()

    def _copy(self, index):
        return os.path.join(self.snaps, "pre-%d" % index)

    def _restore(self, index):
        testlib.rmtree(self.case.dir)
        shutil.copytree(self._copy(index), self.case.dir, symlinks=True)

    def _run(self, index):
        step = self.steps[index]
        if isinstance(step, Do):
            step.fn()
            return None
        code, out, err = self.case.ship(step.args)
        return code, out, err

    def _reference(self):
        for index, step in enumerate(self.steps):
            if isinstance(step, Ship) and step.swept:
                shutil.copytree(self.case.dir, self._copy(index), symlinks=True)
            got = self._run(index)
            if got is not None:
                code, out, err = got
                self.test.assertIn(code, (0, 10), (step.name, out, err))
                self.codes[index] = code
                if step.swept:
                    self.post[index] = facts(self.case)
        self.final = ending(self.case)
        self.final_facts = facts(self.case)
        self.test.assertEqual(self.final.get("phase"), "done", self.final)

    def swept(self):
        return [i for i, s in enumerate(self.steps) if isinstance(s, Ship) and s.swept]

    def window(self, index):
        """(first line, last line, lines run): the swept command's first write to the line after its last."""
        self._restore(index)
        code, seen = recorded(self.case, self.steps[index].args, os.path.join(self.tmp, "record.json"))
        self.test.assertEqual(code, self.codes[index], self.steps[index].name)
        self.test.assertEqual(diff(self.post[index], facts(self.case)), [], "the traced run is the reference run")
        writes = seen["writes"]
        self.test.assertTrue(writes, "%s writes nothing the tracer sees" % self.steps[index].name)
        first = min(w["call"] for w in writes)
        last = max(w["return"] if w["return"] is not None else seen["lines"] for w in writes)
        return first, min(last, seen["lines"] - 1), seen["lines"]

    def kill_everywhere(self, index, lines=None, stride=1):
        """Kill the command at every line of its window (or at `lines`), each time on a restored copy; returns the
        failures as words (empty when every kill point holds)."""
        step = self.steps[index]
        first, last, total = self.window(index)
        points = list(lines) if lines is not None else list(range(first, last + 1, stride))
        failures, replayed = [], {}
        for line in points:
            self._restore(index)
            if not killed_at(self.case, step.args, line, os.path.join(self.tmp, "stop.json")):
                failures.append("line %d: the command ended before it" % line)
                continue
            left = sha_bytes(json.dumps(facts(self.case, raw=True), sort_keys=True).encode("utf-8"))
            problem = self._after_kill(index, line, replay=left not in replayed)
            replayed.setdefault(left, line)
            if problem:
                failures.append(problem)
        self.ran[step.name] = {"window": [first, last], "lines": total, "kill_points": len(points),
                               "states": len(replayed), "failed": len(failures)}
        return failures

    def _after_kill(self, index, line, replay=True):
        step = self.steps[index]
        code, out, err = self.case.ship(step.args)
        if code not in (self.codes[index], 2):
            return "line %d: the next command exited %d: %s %s" % (line, code, out, err.strip()[:300])
        if code == 2 and "instead" not in err:
            return "line %d: the next command exited 2 without naming the command to run: %s" % (line, err.strip())
        got = facts(self.case)
        if got != self.post[index]:
            return "line %d: after the next command the run differs from the uninterrupted one: %s" % (
                line, "; ".join(diff(self.post[index], got))[:600])
        if not replay:
            return None
        for later in range(index + 1, len(self.steps)):
            res = self._run(later)
            if res is not None and res[0] != self.codes[later]:
                return "line %d: the later step %r exited %d (the reference %d): %s %s" % (
                    line, self.steps[later].name, res[0], self.codes[later], res[1], res[2].strip()[:300])
        end = ending(self.case)
        if end != self.final:
            return "line %d: the run ended otherwise than the reference: %s" % (
                line, "; ".join(diff(self.final, end))[:600])
        got = facts(self.case)
        if got != self.final_facts:
            return "line %d: the finished run differs from the reference: %s" % (
                line, "; ".join(diff(self.final_facts, got))[:600])
        return None


def copy_of(doc):
    return copy.deepcopy(doc)
