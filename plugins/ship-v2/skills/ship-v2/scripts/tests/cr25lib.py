"""CR-25, measured: a mid-run waiver or reopening, then each way a ship run continues or ends (contract section 6.2).

E15-9 says ship-v2 writes only the `waived` and `reopened` events the owner gives mid-run; the stations it visits
write their own records (a card move is a `card_set` and its `Status:` line, written by the station that moves it).
Slice 1b found that a `waived` event with no card move left vertical-v2's gate stalling a waived slice and passing a
reopened one (C1B1-2), and the owner ruled the card move for handoff-v2 (A23 (2)). This module measures the same
question for ship-v2, with the real stations' result files (their accepted examples, set to the visit's run), the
records events each station writes for what its result says (the shapes of its own code: signoff-v2's
`finding_raised` and `card_set`, recheck-v2's `disposition` and `card_set`, build-v2's `card_set`), and vertical-v2's
real gate run through its own CLI on the workspace the run leaves. Each scenario returns one row:

    {"scenario", "ship_end", "ship_events", "card_observed", "card_derived", "status_line", "v1_card", "gate",
     "gate_tag", "disagrees", "gate_passes_reopened"}

`v1_card` is the card by v1's rule after the grants (a verdict card takes what its open findings give, waived ones
excluded), which the records component's `card_derived` implements; `disagrees` is true when the card the records
hold (`card_observed`) or the slice's `Status:` line differs from it. Used by `test_cr25.py` and by the builder's
measurement table; it decides nothing.
"""
import json
import os
import re
import subprocess
import sys

import slib
import testlib

ONE_SLICE = [("A", "the counter", "not started")]
SECOND_AT = "src/turnstile.py:1"


def vertical_skill():
    path = testlib.checkout_sibling("vertical-v2")
    return None if path is None else os.path.join(path, "skills", "vertical-v2")


def vertical_gate(tmp, ws, run):
    """vertical-v2's own gate through its real CLI (check-input, then gate), as the next station runs it."""
    skill = vertical_skill()
    run_dir = os.path.join(tmp, run)
    doc = testlib.make_input(ws, run_dir)
    doc["run_id"] = run
    doc["station"] = {"session_model": "claude-opus-5-5"}
    path = os.path.join(tmp, run + "-input.json")
    testlib.write_json(path, doc)
    env = slib.env({"VERTICAL_V2_TEST": "1"})
    out = None
    for args in (["check-input", path], ["gate", "--run-dir", run_dir, "--name", slib.FEATURE]):
        proc = subprocess.run([sys.executable, os.path.join(skill, "scripts", "vertical.py")] + args, cwd=tmp, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            out = json.loads(proc.stdout.decode("utf-8"))
        except ValueError:
            out = None
        if proc.returncode != 0:
            return proc.returncode, out if out is not None else {"stderr": proc.stderr.decode("utf-8", "replace")}
    return 0, out


def card(tmp, ws, station, before, after, run_id):
    """A station's card move: its `card_set` through the component and its `Status:` line."""
    slib.append(tmp, ws, [dict(slib._base(station, run_id, ws), kind="card_set", slice="A", before=before,
                               after=after)])
    slib.set_status(ws, "A", after)


def recheck(tmp, ws, finding, fixed, before, after, run_id):
    """What recheck-v2 writes for one checklist item: its disposition, then the card when it moves."""
    ident = slib.identity(ws)
    slib.append(tmp, ws, [dict(slib._base("recheck-v2", run_id, ws), kind="disposition", finding=finding,
                               disposition="fixed" if fixed else "not_fixed", how="the case re-ran",
                               verified_source={"known": True, "identity": ident}, join_basis=None)])
    if before != after:
        card(tmp, ws, "recheck-v2", before, after, run_id)


class Run(object):
    """One ship run on the stand-in tree, driven the way the executor drives it."""

    def __init__(self, test, tmp, name, majors=1, prior=False):
        self.test, self.tmp = test, os.path.join(tmp, name)
        os.makedirs(self.tmp)
        self.ws = slib.make_repo(self.tmp, slib.build_doc(slices=ONE_SLICE))
        self.tree = slib.Tree(self.tmp)
        self.findings = []
        if prior:
            self.findings.append(slib.raise_finding(self.tmp, self.ws, card=("not started", "signed off with "
                                                                                           "conditions"),
                                                    run_id="earlier-signoff"))
            slib.set_status(self.ws, "A", "signed off with conditions")
        self.drive, self.run_dir = slib.start(test, self.tree, self.tmp, self.ws)
        slib.through_hook(test, self.drive, self.tmp, self.run_dir)
        self.majors = majors
        self.pauses = 0

    def visit(self, station, which, before_result=None):
        return slib.visit(self.test, self.drive, self.run_dir, station, which, self.ws, before_result=before_result)

    def build(self, which="completed"):
        code, out, err = self.visit("build-v2", which)
        if which == "completed":
            card(self.tmp, self.ws, "build-v2", "not started", "built", "build-run")
        return out

    def signoff(self):
        for index in range(self.majors):
            at = slib.MAJOR_AT if index == 0 else SECOND_AT
            self.findings.append(slib.raise_finding(self.tmp, self.ws, location=at, card=None,
                                                    claim="the counter skips turn %d" % index))
        card(self.tmp, self.ws, "signoff-v2", "built", "signed off with conditions", "signoff-run")
        code, out, err = self.visit("signoff-v2", "findings")
        return out

    def grant(self, kind, finding, words):
        self.pauses += 1
        code, out, err = self.drive(["pause", "--run-dir", self.run_dir, "--question", slib.question_file(
            self.tmp, self.run_dir, "Only you can rule this finding: waive it or hold?", source="ship", station=None,
            finding=finding, name="q%d.json" % self.pauses)])
        self.test.assertEqual(code, 0, (out, err))
        code, out, err = self.drive(["pause", "--run-dir", self.run_dir, "--answer", slib.answer_file(
            self.tmp, self.run_dir, out["pause"], words, {"kind": kind, "finding": finding},
            name="a%d.json" % self.pauses)])
        self.test.assertEqual(code, 0, (out, err))
        return out

    def hold_open(self, text="Which mode should the spinner use?"):
        """A pause left unanswered: the run waits."""
        self.pauses += 1
        code, out, err = self.drive(["pause", "--run-dir", self.run_dir, "--question", slib.question_file(
            self.tmp, self.run_dir, text, name="q%d.json" % self.pauses)])
        self.test.assertEqual(code, 0, (out, err))

    def fix(self, lap, findings=(), spec_change=(), outside=False):
        rows = []
        for finding in findings:
            testlib.write_text(os.path.join(self.ws, "src", "turnstile.py"),
                               "def spin(count):\n    return count + %d\n" % (lap + 5))
            rows.append({"finding": finding, "paths": ["src/turnstile.py"], "summary": "attempt %d" % lap})
        if outside:
            if rows:
                rows[0]["paths"].append("src/spinner.py")
            else:
                rows.append({"finding": self.findings[-1], "paths": ["src/spinner.py"], "summary": "the spinner too"})
        code, out, err = self.drive(["fix", "--run-dir", self.run_dir, "--fixes", slib.fixes_file(
            self.tmp, self.run_dir, lap, rows, spec_change, name="fixes-%d-%d.json" % (lap, len(os.listdir(self.tmp))))])
        self.test.assertEqual(code, 0, (out, err))
        return out

    def recheck(self, which, writes=None):
        """recheck-v2's visit; `writes`, what recheck-v2 itself writes during it (its disposition and card)."""
        return self.visit("recheck-v2", which, before_result=(lambda visit: writes()) if writes else None)[1]

    def lap(self):
        return self.drive(["lap", "--run-dir", self.run_dir])

    def end(self):
        code, out, err = slib.report(self.drive, self.run_dir)
        self.test.assertEqual(code, 10, (out, err))
        return out

    def measure(self, scenario, ship_end):
        mine = [e["kind"] for e in slib.log_lines(self.ws) if e["actor"]["station"] == "ship-v2"]
        state = slib.state(self.ws)
        row = next(s for s in state["slices"] if s["name"] == "A")
        text = testlib.read_text(os.path.join(self.ws, slib.DOC))
        status = next(l[len("Status: "):] for l in text.split("\n") if l.startswith("Status: "))
        slib.commit_all(self.ws, "after the ship run")
        code, out = vertical_gate(self.tmp, self.ws, "vertical-" + re.sub(r"[^A-Za-z0-9]+", "-", scenario).strip("-"))
        gate = "passes" if code == 0 and (out or {}).get("next") == "ask" else "stops"
        tag = None if gate == "passes" else ((out or {}).get("stop_tag") or (out or {}).get("stderr"))
        reopened = "reopened" in mine
        v1_card = row["card_derived"]
        return {"scenario": scenario, "ship_end": ship_end, "ship_events": mine, "card_observed": row["card_observed"],
                "card_derived": row["card_derived"], "status_line": status, "v1_card": v1_card, "gate": gate,
                "gate_tag": tag, "disagrees": row["card_observed"] != v1_card or status != v1_card,
                "gate_passes_reopened": reopened and gate == "passes" and v1_card != "signed off"}


def _ended(out):
    return "%s %s" % (out["status"], out["stop_tag"] or "")


def scenarios():
    """(name, function(test, tmp) -> row), in the table's order."""

    def waive_clean_end(test, tmp):
        run = Run(test, tmp, "w-clean")
        run.build()
        run.signoff()
        run.grant("waive", run.findings[0], "Waive it, a bench quirk")
        run.fix(1)
        run.recheck("nothing_open")
        return run.measure("waiver, then a clean end", _ended(run.end()))

    def waive_stop_1(test, tmp):
        run = Run(test, tmp, "w-stop1", majors=2)
        run.build()
        run.signoff()
        run.grant("waive", run.findings[0], "Waive the first")
        run.fix(1, [run.findings[1]])
        run.recheck("not_clear", lambda: recheck(run.tmp, run.ws, run.findings[1], False, "signed off with conditions",
                                                 "signed off with conditions", "recheck-1"))
        run.lap()
        run.fix(2, [run.findings[1]])
        run.recheck("not_clear", lambda: recheck(run.tmp, run.ws, run.findings[1], False, "signed off with conditions",
                                                 "signed off with conditions", "recheck-2"))
        code, out, err = run.lap()
        test.assertEqual(code, 5)
        return run.measure("waiver, then a lap refused and stop 1", _ended(run.end()))

    def waive_stop_2(test, tmp):
        run = Run(test, tmp, "w-stop2", majors=2)
        run.build()
        run.signoff()
        run.grant("waive", run.findings[0], "Waive the first")
        run.fix(1, spec_change=[{"finding": run.findings[1], "why": "the fix needs the requirement changed"}])
        return run.measure("waiver, then stop 2", _ended(run.end()))

    def waive_stop_3(test, tmp):
        run = Run(test, tmp, "w-stop3", prior=True)

        def asked(visit):
            run.grant("waive", run.findings[0], "Waive the earlier MAJOR, build anyway")
        run.visit("build-v2", "partial", before_result=asked)
        return run.measure("waiver during the build, then stop 3", _ended(run.end()))

    def waive_stop_4(test, tmp):
        run = Run(test, tmp, "w-stop4", majors=2)
        run.build()
        run.signoff()
        run.grant("waive", run.findings[0], "Waive the first")
        run.fix(1, [run.findings[1]], outside=True)
        return run.measure("waiver, then stop 4", _ended(run.end()))

    def waive_pause(test, tmp):
        run = Run(test, tmp, "w-pause")
        run.build()
        run.signoff()
        run.grant("waive", run.findings[0], "Waive it")
        run.hold_open()
        return run.measure("waiver, then a pause the owner has not answered", "paused (the run waits)")

    def reopen_after_clear(run):
        run.build()
        run.signoff()
        run.fix(1, [run.findings[0]])
        run.recheck("all_clear", lambda: recheck(run.tmp, run.ws, run.findings[0], True, "signed off with conditions",
                                                 "signed off", "recheck-1"))
        run.grant("reopen", run.findings[0], "Reopen it, it came back on the bench")

    def reopen_clean_end(test, tmp):
        run = Run(test, tmp, "r-clean")
        reopen_after_clear(run)
        run.lap()
        run.fix(2, [run.findings[0]])
        run.recheck("all_clear", lambda: recheck(run.tmp, run.ws, run.findings[0], True, "signed off", "signed off",
                                                 "recheck-2"))
        return run.measure("reopening, then the extra lap clears it", _ended(run.end()))

    def reopen_stop_1(test, tmp):
        run = Run(test, tmp, "r-stop1")
        reopen_after_clear(run)
        run.lap()
        run.fix(2, [run.findings[0]])
        run.recheck("not_clear", lambda: recheck(run.tmp, run.ws, run.findings[0], False, "signed off",
                                                 "signed off with conditions", "recheck-2"))
        code, out, err = run.lap()
        test.assertEqual(code, 5)
        return run.measure("reopening, then a lap refused and stop 1", _ended(run.end()))

    def reopen_stop_2(test, tmp):
        run = Run(test, tmp, "r-stop2")
        reopen_after_clear(run)
        run.lap()
        run.fix(2, spec_change=[{"finding": run.findings[0], "why": "the fix needs the requirement changed"}])
        return run.measure("reopening, then stop 2", _ended(run.end()))

    def reopen_stop_4(test, tmp):
        run = Run(test, tmp, "r-stop4")
        reopen_after_clear(run)
        run.lap()
        run.fix(2, [run.findings[0]], outside=True)
        return run.measure("reopening, then stop 4", _ended(run.end()))

    def reopen_pause(test, tmp):
        run = Run(test, tmp, "r-pause")
        reopen_after_clear(run)
        run.hold_open()
        return run.measure("reopening, then a pause the owner has not answered", "paused (the run waits)")

    return [("waive_clean_end", waive_clean_end), ("waive_stop_1", waive_stop_1), ("waive_stop_2", waive_stop_2),
            ("waive_stop_3", waive_stop_3), ("waive_stop_4", waive_stop_4), ("waive_pause", waive_pause),
            ("reopen_clean_end", reopen_clean_end), ("reopen_stop_1", reopen_stop_1),
            ("reopen_stop_2", reopen_stop_2), ("reopen_stop_4", reopen_stop_4), ("reopen_pause", reopen_pause)]
