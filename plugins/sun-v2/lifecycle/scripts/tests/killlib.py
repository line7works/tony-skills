"""The kill-sweep helper (the contract's section 12, L6; the frame's LOG-1, OP-6, E16-6).

A sweep takes one fixture and one flow: a look, then a go. It runs the flow once to its end (the
reference), with the go in a child process that records every act; the number of write boundaries of
that go is the number of kill points. Then, for EVERY boundary, on a fresh fixture machine of its
own, it starts the go again in a child and that child ends itself with a real SIGKILL when the
boundary is reached (a write made and not yet synced is lost first); the test then goes on as an
executor would: a status summons, a resume on the position it gave, until the run ends or stops.
It requires, at every kill point:

- no effect applied twice: the fakes' state never holds two things for one create, no state change
  was recorded twice, no line stands twice in a file, nothing was moved twice;
- the rerun ends in the reference end state (every file outside the tool's own folder byte for
  byte, every fake's state), or in that state with an operation listed as `not proven` where OP-6
  says so, or stops plainly with one of the reasons the flow names as a plain stop.
- SEC-11's scan over that kill point's executions (the reviewer's S1): every invocation's output and
  the fixture home it left hold neither the sweep's hosting token, a marked canary in the session of
  every invocation, nor any value a fake issued, outside SEC-7's places (`scan_point`).

The kill points run side by side: `SUN_V2_SWEEP_WORKERS` workers (a positive whole number; unset, a
quarter of the machine's processors, at least 1 and at most 8, so that the two runtimes' sweeps
running at once take half of it), each on fixture machines of its own. `count_problem` names a
sweep that did not kill at exactly the boundaries the reference recorded, each once.
"""
import hashlib
import json
import os
import shutil
import threading

import harness
import scan

WORKERS = "SUN_V2_SWEEP_WORKERS"
MOST_WORKERS = 8
SKIP = (".sun-v2", ".fakes", ".config", "Library")


def sweep_token():
    """The sweep's hosting token: a marked canary, built at run time, in the session of every invocation of the sweep, so
    that the name check reads it into the register (SEC-2, SEC-11)."""
    return harness.canary("sweep-token")


def scan_point(machine, results):
    """SEC-11's scan over one execution of the sweep: the fixture home it left and every invocation's output, for the
    sweep's token and every value a fake issued. [(where, what)]: empty where nothing rests outside SEC-7's places."""
    values = [(sweep_token(), [])] + [(v, []) for v in scan.issued(machine)]
    return scan.scan(machine, values, results)


def default_workers(cpus):
    return max(1, min(MOST_WORKERS, (cpus or 1) // 4))


def worker_count(environ=None, cpus=None):
    environ = os.environ if environ is None else environ
    raw = (environ.get(WORKERS) or "").strip()
    if not raw:
        return default_workers(os.cpu_count() if cpus is None else cpus)
    if not (raw.isascii() and raw.isdigit()) or int(raw) < 1:
        raise ValueError("%s is a positive whole number of workers, not %r" % (WORKERS, raw))
    return int(raw)


def count_problem(points, done):
    if sorted(done) == sorted(points):
        return None
    want, got = set(points), set(done)
    twice = sorted(set(p for p in done if done.count(p) > 1))
    parts = ["the sweep killed at %d of %d recorded kill points" % (len(got & want), len(want))]
    if want - got:
        parts.append("never at %s" % ", ".join(str(n) for n in sorted(want - got)[:20]))
    if twice:
        parts.append("twice at %s" % ", ".join(str(n) for n in twice[:20]))
    if got - want:
        parts.append("at points the reference did not record: %s" % ", ".join(str(n) for n in sorted(got - want)[:20]))
    return "; ".join(parts)


def world_facts(machine):
    """What the run did to the world: every file under the fixture home outside the tool's own
    folder, the fakes' folder and the settings, and every fake's state."""
    files = {}
    for rel, (kind, mode, digest) in harness.tree(machine.home).items():
        if rel.split(os.sep)[0] in SKIP:
            continue
        files[rel] = (kind, mode, digest)
    fakes = {}
    root = os.path.join(machine.home, ".fakes")
    for tool in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        state = machine.fake(tool, "state.json") or {}
        fakes[tool] = {"things": dict((k, (v.get("kind"), v.get("state"))) for k, v in (state.get("things") or {}).items()),
                       "refs": state.get("refs") or {}, "sets": state.get("sets") or []}
    return {"files": files, "fakes": fakes}


def twice(facts):
    """The words for any effect applied twice, from the world's facts."""
    found = []
    for tool, state in facts["fakes"].items():
        for key in state["things"]:
            if "#" in key:
                found.append("%s holds two things for one create: %s" % (tool, key))
        seen = [json.dumps(s, sort_keys=True) for s in state["sets"]]
        if len(seen) != len(set(seen)):
            found.append("%s recorded one state change twice" % tool)
    return found


class Sweep(object):
    def __init__(self, test, tmp, prepare, name="demo", kind="sunrise", plain_stops=("an outstanding create",), also_ok=None):
        self.test, self.tmp, self.prepare = test, tmp, prepare
        self.name, self.kind = name, kind
        self.plain_stops = plain_stops
        self.env = {"FAKEHOST_TOKEN": sweep_token()}
        self.scanned = 0
        self.scanned_reference = False
        self.ran = {}
        self.lock = threading.Lock()
        self._reference()

    def fresh(self, label):
        machine = harness.Machine(os.path.join(self.tmp, label), "home", "sweep")
        self.prepare(machine)
        return machine

    def _reference(self):
        os.makedirs(os.path.join(self.tmp, "ref"))
        machine = self.fresh("ref")
        looked = machine.look(self.name, self.kind, env=self.env)
        self.test.assertEqual(looked.ending, "preview", looked.text)
        events = os.path.join(self.tmp, "ref-events.jsonl")
        went = machine.drive("go", "--kind", self.kind, "--name", self.name, "--run", looked.doc["run"],
                             "--manifest-sha256", looked.doc["manifest_sha256"], events=events, env=self.env)
        self.test.assertEqual(went.code, 10, went.text)
        self.test.assertEqual(went.ending, "complete", went.text)
        self.test.assertEqual(scan_point(machine, [looked, went]), [], "the reference run left a value outside SEC-7's places")
        self.scanned_reference = True
        with open(events) as fh:
            self.events = [json.loads(line) for line in fh]
        self.boundaries = [e for e in self.events if e["stage"] in ("pre", "mid", "post")]
        self.points = list(range(len(self.boundaries)))
        self.facts = world_facts(machine)
        self.statuses = machine.statuses(looked.doc["run"])
        self.test.assertEqual(twice(self.facts), [])

    def kill_at(self, point):
        """One kill point on a machine of its own. Returns (the outcome's word, the failure as words or None)."""
        folder = os.path.join(self.tmp, "k%d" % point)
        os.makedirs(folder)
        try:
            machine = self.fresh("k%d" % point)
            looked = machine.look(self.name, self.kind, env=self.env)
            run = looked.doc["run"]
            died = machine.drive("go", "--kind", self.kind, "--name", self.name, "--run", run,
                                 "--manifest-sha256", looked.doc["manifest_sha256"], kill_at=point, env=self.env)
            results = [looked, died]
            if not died.killed:
                return "ended first", "point %d: the command ended before the boundary (exit %s)" % (point, died.code)
            ending, reason = None, None
            for _round in range(6):
                ended = [r for r in machine.journal(run) if r["kind"] == "run-end"]
                status = machine.summon("status", self.name, env=self.env)
                results.append(status)
                if ended:
                    # the kill fell after the run's own ending was on record: the run has ended, and says so
                    if status.ending != "refused":
                        return "bad ending", "point %d: a run whose ending is on record was not refused" % point
                    ending = ended[-1]["ending"]
                    break
                if status.ending in ("complete", "ended with exceptions"):
                    ending = status.ending        # every operation was final: the summons recorded the run's ending
                    break
                if status.ending == "refused" and not machine.open_runs():
                    # the kill fell before the run was recorded as open: the go is given again
                    again = machine.go(looked, self.name, self.kind, env=self.env)
                    results.append(again)
                    ending = again.ending
                else:
                    if status.doc is None or status.doc.get("position") is None:
                        return "broken", "point %d: the status summons gave no position: %s" % (point, status.text[:300])
                    again = machine.summon("resume", self.name, "--position", status.doc["position"], "--word", "go on",
                                           env=self.env)
                    results.append(again)
                    ending = again.ending
                if ending in ("complete", "ended with exceptions"):
                    break
                if ending == "stopped":
                    reason = [l for l in again.lines if l.startswith("stopped: ")]
                    reason = reason[0][len("stopped: "):] if reason else ""
                    break
            found = scan_point(machine, results)            # SEC-11 over this kill point's executions (S1)
            with self.lock:
                self.scanned += 1
            if found:
                return "scan", "point %d (%s): the scan found %s" % (point, self.describe(point), "; ".join(w for w, _ in found[:3]))
            facts = world_facts(machine)
            doubled = twice(facts)
            if doubled:
                return "twice", "point %d (%s): %s" % (point, self.describe(point), "; ".join(doubled))
            statuses = machine.statuses(run)
            if ending == "complete":
                if facts != self.facts:
                    return "differs", "point %d (%s): the finished run differs from the reference: %s" % (
                        point, self.describe(point), diff(self.facts, facts))
                unproven = sorted(op for op, st in statuses.items() if st == "not proven")
                return ("not proven: " + ",".join(unproven)) if unproven else "complete", None
            if ending == "stopped" and reason in self.plain_stops:
                return "stopped: " + reason, None
            return "bad ending", "point %d (%s): the rerun ended %s (%s)" % (point, self.describe(point), ending, reason)
        finally:
            shutil.rmtree(folder, True)

    def describe(self, point):
        event = self.boundaries[point]
        return "%s %s %s" % (event["stage"], event["op"], os.path.basename(str(event["subject"])))

    def everywhere(self, workers=None):
        """Kill at every boundary. Returns the failures as words; `self.ran` holds the counts."""
        workers = workers or worker_count()
        pending = list(self.points)
        done, failures, outcomes = [], [], {}

        def work():
            while True:
                with self.lock:
                    if not pending:
                        return
                    point = pending.pop(0)
                try:
                    word, problem = self.kill_at(point)
                except Exception as exc:        # a worker's own failure is the test's failure, with the point named
                    word, problem = "error", "point %d: %s: %s" % (point, type(exc).__name__, exc)
                with self.lock:
                    done.append(point)
                    outcomes[word.split(":")[0]] = outcomes.get(word.split(":")[0], 0) + 1
                    if problem:
                        failures.append(problem)
        threads = [threading.Thread(target=work) for _ in range(max(1, min(workers, len(self.points))))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        problem = count_problem(self.points, done)
        if problem:
            failures.append(problem)
        self.ran = {"kill_points": len(set(done)), "recorded": len(self.points), "outcomes": outcomes,
                    "failed": len(failures), "workers": len(threads), "scanned": self.scanned,
                    "scanned_reference": self.scanned_reference}
        return sorted(failures)


def diff(want, got):
    out = []
    for part in ("files", "fakes"):
        keys = sorted(set(want[part]) | set(got[part]))
        out += ["%s/%s" % (part, k) for k in keys if want[part].get(k) != got[part].get(k)]
    return ", ".join(out)[:500]
