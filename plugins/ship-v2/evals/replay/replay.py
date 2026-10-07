#!/usr/bin/env python3
"""The end-to-end replay across the back of the loop (the E15 lane contract section 11, item 5).

    sh ../../setups/safe-python.sh replay.py [--keep DIR] [--path clean|findings|both]
                                             [--root STATION=DIR ...] [--trace-out FILE]

`--keep DIR` is refused, exit 2 and nothing created, when it is or sits under ~/.claude, ~/.codex or a
~/.local/share/skills-v2-* home, as given or resolved (the setups' home guard); so are TMPDIR, TEMP and TMP. The
interpreter that runs this file starts before its guard, and the /usr/bin/python3 shim writes into the temp folder as
it starts: start this file through `../../setups/safe-python.sh`, which starts the interpreter with TMPDIR, TEMP and
TMP cleared and hands their values to this guard, or through uv (its own interpreter, not the shim).

One fixture project (`fixtures/turnstile/`: a bench-rig turn counter, one slice) is copied into a fresh temporary
tree, made a git work tree on a feature branch, and walked through the back of the loop, each station through its
REAL phase driver:

    ship-v2      check-input, select, hook (the Codex adapter's own reading: NOT armed), then the loop:
                 visit build-v2, visit signoff-v2, (fix, the save step as `fix` printed it, visit recheck-v2),
                 report
    build-v2     check-input, contract, preflight, record-answer, report: run where ship-v2's visit names it
    signoff-v2   check-input, scope, request, record-answer, record: run where ship-v2's visit names it
    recheck-v2   check-input, start, record-call, adjudicate, record: run where ship-v2's visit names it
    handoff-v2   check-input, select, photograph, gate, record-answer, write, report
    vertical-v2  check-input, gate, ask (the two readers `suggest` calls run as printed), scope, request, the three
                 local lenses through readers' own runner on a canned reply (`READERS_TEST=1`, readers' test
                 interface: no child is launched), record-local, request --outside, the outside row the same way,
                 record-outside, verdict, report

Two paths, each in its own tree: `clean` (the build is right, the reviewer finds nothing, ALL CLEAR with recheck not
run) and `findings` (the reviewer raises one MAJOR, the session fixes it, recheck-v2's verifier finds it fixed, ALL
CLEAR after one lap). Between the loop and handoff-v2, and between handoff-v2 and vertical-v2, the executor takes a
local checkpoint commit (handoff-v2's named step; vertical-v2's clean-tree precondition). On the findings path the
executor takes ship-v2's named save step after the lap's `fix` and before the recheck visit, as `fix` printed it
(`save_step`: a local commit of exactly signoff-v2's verdict mirror under `docs/reviews/`; ship-v2's SKILL.md step 5,
its contract's section 3.11, the E15 lane contract A30 (1)): recheck-v2's own stated precondition for the loop (its
contract's section 9, E13's F8), without which ship-v2 refuses the recheck visit, and recheck-v2's boundary check
would read the mirror's change as a violation, end `not_clear` and freeze the card.

THE RECORDED ANSWERS (`fixtures/turnstile/answers.json`) stand in for every model's part and nothing else: the
executor's edits and fixes, build-v2's recorded answer (each check's output is the output of running the check named
in the slice in the workspace, captured by this script, never typed), signoff-v2's reviewer answer (through signoff-v2's
own test interface, `SIGNOFF_TEST=1` with an Opus-class replay model id, which signoff-v2 names as synthetic in its
result), recheck-v2's verifier report (a canned report in recheck-v2's section 7 shape), handoff-v2's answers, and
vertical-v2's ask answer (local and one outside row), its lens and outside replies and its merged findings. No
reader is launched, no model is called and no harness runs.

The script's own assertions, one JSON summary (exit 0 only when every one held):

    loop       ship-v2's run ends as the recorded answers say: `completed`, Result ALL CLEAR, the five fields
               (clean: Signoff signed off, Recheck not run, Laps 0; findings: Signoff signed off with conditions,
               Recheck ALL CLEAR, Laps 1), Card signed off; every command's exit as its contract says
    trace      ship-v2's trace names only v2 identities (build-v2, signoff-v2, recheck-v2 with interface 1, roots
               under no v1 folder), opening and closing lines in the loop's order, and validates with
               `validate-trace.py`; no `refused` line
    photograph handoff-v2's photograph matches the records: each slice's card and the open set as the records
               component's `state` gives them, the branch and the tree as git gives them; the block it writes
               carries the photograph's cards; the loop complete gives no kickoff line
    vertical   vertical-v2's gate passes (every card signed off, the records agree), and every packet `scope` and
               `request` cut follows its contract: no file under `docs/reviews/` or `docs/records/`, no history
               (`.git`), the build doc reduced to its spec (no `## Punch list`, `## Handoffs`, `## Build
               assumptions`, `## Deviations`, `## Discovered` heading and no `Status:` line), each of those named
               as withheld, and no line of the review record (the verdict doc, the punch-list block, the handoff
               block) in any packet or summons copy; local first (no outside request file before record-local);
               the refuted outside finding counted
    confined   nothing written outside each path's tree (this checkout's plugins tree unchanged: paths, sizes and
               modification times)

`--root STATION=DIR` runs ship-v2, handoff-v2, vertical-v2, readers or records from DIR (a plugin root) instead of
this checkout's sibling, and `--watch DIR` adds a folder the `confined` assertion holds unchanged; build-v2, signoff-v2 and recheck-v2 always run from the root ship-v2's visit names, as an executor would.
The trace proof (`../../setups/trace-proof.sh`) uses it to run the installed copies. `--trace-out FILE` writes every
trace line each path's ship-v2 and vertical-v2 runs wrote, as one JSON document. Runtimes: the stations run through
the interpreter running this script when it imports `jsonschema`, else through `uv run --offline --python
/usr/bin/python3 --with jsonschema==4.25.1 python`; the summary names which. Standard library only, Python 3.9; no
network, no model call, no harness launch. `--keep DIR` builds the trees in DIR (which must not exist) and leaves
them; otherwise the temporary tree is removed.
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "turnstile")
PLUGINS = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
DOC = "docs/plans/2026-10-06-turnstile.md"
SLICE = "A"
DATE = "2026-10-06"
DASH = "\u2014"
DRIVERS = {"ship-v2": "ship.py", "build-v2": "build.py", "signoff-v2": "signoff.py", "recheck-v2": "recheck.py",
           "handoff-v2": "handoff.py", "vertical-v2": "vertical.py"}
OWN_ROOTS = ("ship-v2", "handoff-v2", "vertical-v2")
SESSIONS = {"ship": "replay-ship-session", "build": "replay-build-session", "review": "replay-review-session"}
REPLAY_MODEL = "claude-opus-5-5"
GIT_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "Replay", "GIT_AUTHOR_EMAIL": "replay@example.invalid",
           "GIT_COMMITTER_NAME": "Replay", "GIT_COMMITTER_EMAIL": "replay@example.invalid",
           "GIT_AUTHOR_DATE": "2026-10-06T09:00:00+00:00", "GIT_COMMITTER_DATE": "2026-10-06T09:00:00+00:00"}
GIT_ARGS = ["-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]
WITHHELD_HEADINGS = ("## Punch list", "## Handoffs", "## Build assumptions", "## Deviations", "## Discovered")


class Stop(Exception):
    """A step did not go as its contract says; the replay stops there and reports it."""


def interpreter():
    """This interpreter when it imports jsonschema from a place the stations see too (the stations run with a fake
    HOME, so a user-site copy under the real HOME is not one), else uv with the pin."""
    why = "does not import jsonschema"
    try:
        import jsonschema  # noqa: F401
        if not under(jsonschema.__file__, os.path.expanduser("~")):
            return [sys.executable], "this interpreter (%s), which imports jsonschema" % sys.executable
        why = "imports jsonschema only from a user site under HOME, which the stations' fake HOME hides"
    except ImportError:
        pass
    return (["uv", "run", "--offline", "--quiet", "--python", "/usr/bin/python3", "--with",
             "jsonschema==4.25.1", "python"],
            "uv run --offline --python /usr/bin/python3 --with jsonschema==4.25.1 python (this interpreter, %s, %s)"
            % (sys.executable, why))


def tree_state(root, skip=()):
    """{relative path: (size, mtime_ns)} under root, `.git` and the names in `skip` excepted."""
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != ".git" and os.path.join(base, d) not in skip)
        for name in files:
            full = os.path.join(base, name)
            st = os.lstat(full)
            out[os.path.relpath(full, root)] = (st.st_size, st.st_mtime_ns)
    return out


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return path


def read_text(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def read_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def sha256_of(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def under(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


def v1_names():
    """The ten v1 station names, assembled so no file of this core names a v1 folder."""
    return ("pre" + "con", "archi" + "tect", "blue" + "print", "in" + "spect", "bu" + "ild", "sign" + "off",
            "re" + "check", "verti" + "cal", "hand" + "off", "sh" + "ip")


def v1_part(path):
    """The v1 name a path's own folders carry (`plugins/<v1>`, `<v1>/<dotted version>`, a folder named for a v1
    station), or None."""
    parts = [p for p in os.path.normpath(os.path.realpath(path)).split(os.sep) if p]
    names = v1_names()
    for index, part in enumerate(parts):
        if part in names and (index == 0 or parts[index - 1] == "plugins"
                              or (index + 1 < len(parts) and re.match(r"^\d+(?:\.\d+)*$", parts[index + 1]))):
            return part
    return None


class Path(object):
    """One path through the loop, in its own tree under the replay's root."""

    def __init__(self, root, kind, roots, answers, python, python_note):
        self.root = root
        self.kind = kind
        self.roots = roots
        self.answers = answers
        self.mine = answers["paths"][kind]
        self.python, self.python_note = python, python_note
        self.ws = os.path.join(root, "workspace")
        self.runs = os.path.join(root, "runs")
        self.cwd = os.path.join(self.runs, "cwd")
        self.home = os.path.join(root, "home")
        self.readers_checkout = os.path.join(root, "readers-checkout")
        self.env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": self.home, "LANG": "C", "LC_ALL": "C",
                    "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": os.path.join(root, "tmp"),
                    "READERS_CHECKOUT": self.readers_checkout}
        # uv's own cache is named, never found through the fake HOME (no network); a hook the trace proof loads
        # (PYTHONPATH) and its own variables pass through
        uv_cache = os.environ.get("UV_CACHE_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "uv")
        self.env["UV_CACHE_DIR"] = uv_cache
        for key, value in os.environ.items():
            if key == "PYTHONPATH" or key.startswith("TRIPWIRE_"):
                self.env[key] = value
        self.log = []
        self.problems = []
        self.facts = {"kind": kind}
        self.ship_run = os.path.join(self.runs, "ship")
        self.visits = []
        self.track_mirror = True

    # ---- plumbing -------------------------------------------------------------------------------------------

    def setup(self):
        shutil.copytree(os.path.join(FIXTURE, "workspace"), self.ws)
        template = os.path.join(self.ws, DOC + ".in")
        with open(template, "r", encoding="utf-8") as fh:
            text = fh.read().replace("{DASH}", DASH)
        os.remove(template)
        with open(os.path.join(self.ws, DOC), "w", encoding="utf-8") as fh:
            fh.write(text)
        for folder in (self.runs, self.cwd, self.home, self.env["TMPDIR"],
                       os.path.join(self.readers_checkout, "plugins", "readers")):
            os.makedirs(folder, exist_ok=True)
        write_json(os.path.join(self.readers_checkout, "plugins", "readers", "last-picks.json"),
                   {"protocol_version": 1, "picks": {}})
        self.git(["init", "-q", "-b", "main"])
        self.git(["add", "-A"])
        self.git(["commit", "-q", "-m", "base"])
        self.git(["tag", "base"])
        self.git(["checkout", "-q", "-b", "feat/turnstile"])

    def git(self, args):
        env = dict(self.env, **GIT_ENV)
        proc = subprocess.run(["git"] + GIT_ARGS + args, cwd=self.ws, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise Stop("git %s: %s" % (" ".join(args), proc.stderr.decode("utf-8", "replace").strip()))
        return proc.stdout.decode("utf-8")

    def checkpoint_commit(self, message):
        """The executor's named local checkpoint commit (handoff-v2's step 6; vertical-v2's clean tree)."""
        self.git(["add", "-A"])
        self.git(["commit", "-q", "-m", message])
        self.log.append({"station": "executor", "command": "git commit (local checkpoint): %s" % message})

    def run(self, label, argv, want, env_extra=None, parse=True):
        env = dict(self.env)
        env.update(env_extra or {})
        proc = subprocess.run(argv, cwd=self.cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace")
        doc = None
        if parse and out.strip():
            try:
                doc = json.loads(out)
            except ValueError:
                doc = None
        entry = {"station": label[0], "command": label[1], "exit": proc.returncode, "want": want}
        if isinstance(doc, dict):
            for key in ("next", "status", "reason"):
                if isinstance(doc.get(key), str):
                    entry[key] = doc[key][:300]
        self.log.append(entry)
        if want is not None and proc.returncode != want:
            entry["stderr"] = proc.stderr.decode("utf-8", "replace")[-1200:]
            entry["stdout"] = out[-1200:]
            raise Stop("%s %s exited %d, the contract says %d" % (label[0], label[1], proc.returncode, want))
        return doc if parse else out

    def driver(self, station, root):
        return os.path.join(root, "skills", station, "scripts", DRIVERS[station])

    def cli(self, station, root, args, want, env_extra=None):
        return self.run((station, args[0]), self.python + [self.driver(station, root)] + [str(a) for a in args],
                        want, env_extra)

    def ship(self, args, want):
        return self.cli("ship-v2", self.roots["ship-v2"], args + (["--run-dir", self.ship_run]
                                                                  if args[0] != "check-input" else []), want)

    def expect(self, ok, what, evidence=None):
        if not ok:
            self.problems.append({"path": self.kind, "assertion": what, "evidence": evidence})
        return ok

    def run_check(self, command):
        """The executor runs a check the slice names, from the workspace root, and keeps what it printed."""
        proc = subprocess.run(command.split(), cwd=self.ws, env=self.env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        return proc.returncode, proc.stdout.decode("utf-8", "replace").strip()

    def apply(self, edits_from):
        source = os.path.join(FIXTURE, edits_from)
        written = []
        for base, dirs, files in os.walk(source):
            dirs.sort()
            for name in sorted(files):
                rel = os.path.relpath(os.path.join(base, name), source)
                dest = os.path.join(self.ws, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copyfile(os.path.join(base, name), dest)
                written.append(rel)
        self.log.append({"station": "executor", "command": "edit %s" % ", ".join(written)})
        return written

    def answer_file(self, name, doc):
        return write_json(os.path.join(self.runs, "answers", name), doc)

    def records(self, *args):
        root = self.roots["records"]
        return self.run(("records", args[0]), self.python + [os.path.join(root, "scripts", "records.py")]
                        + list(args), 0)

    # ---- ship-v2's loop ---------------------------------------------------------------------------------------

    def loop(self):
        self.begin()
        self.build_visit()
        after = self.signoff_visit()
        if after.get("next") == "fix":
            fixed = self.fix(after)
            if self.track_mirror:
                self.take_save_step(fixed.get("save_step"))
            self.recheck_visit()
        self.finish()

    def begin(self):
        ship_input = {"input_version": 1, "run_id": "replay-%s-ship" % self.kind, "workspace": self.ws,
                      "run_dir": self.ship_run,
                      "invocation": {"harness": "codex-cli", "caller": "user", "mode": "direct",
                                     "session_id": SESSIONS["ship"]},
                      "station": {"slice": SLICE}}
        path = write_json(os.path.join(self.runs, "inputs", "ship.json"), ship_input)
        self.ship(["check-input", path], 0)
        got = self.ship(["select", "--doc", DOC], 0)
        self.expect(got.get("footprint") == ["src/turnstile.py", "tests/"], "ship-v2 reads the slice's footprint",
                    got.get("footprint"))
        hook = os.path.join(self.runs, "answers", "hook.json")
        reading = self.run(("ship-v2", "adapters/codex/hook.py"),
                           ["/usr/bin/python3", os.path.join(self.roots["ship-v2"], "skills", "ship-v2", "adapters",
                                                             "codex", "hook.py")], 0)
        write_json(hook, reading)
        self.ship(["hook", "--reading", hook], 0)

    def take_save_step(self, step):
        """ship-v2's named save step (its SKILL.md step 5, contract section 3.11; recheck-v2's own precondition, its
        contract's section 9, E13 F8), taken by the executor as ship-v2 printed it: every command a git command, run
        in the workspace as printed (through this replay's git, whose only additions are the fixture repository's
        hooks-off and no-signing settings). The step names exactly the verdict mirror signoff-v2's result lists, and
        the commit it makes holds exactly that file."""
        mirrors = sorted(os.path.relpath(row["path"], self.ws) for row in self.signoff_result.get("records_written")
                         or [] if row.get("kind") == "verdict_doc")
        if not self.expect(isinstance(step, dict) and step.get("files") == mirrors and mirrors,
                           "ship-v2 names the save step for the verdict mirror signoff-v2 wrote",
                           {"step": step, "mirrors": mirrors}):
            raise Stop("ship-v2 named no save step for %s" % mirrors)
        for command in step["commands"]:
            argv = shlex.split(command)
            if not self.expect(argv[:1] == ["git"] and not set(argv) & {"push", "--no-verify", "-n"},
                               "the save step's commands are local git commands", command):
                raise Stop("the save step holds %r" % command)
            self.git(argv[1:])
        self.log.append({"station": "executor", "command": "save step: %s" % " then ".join(step["commands"])})
        committed = sorted(self.git(["show", "--name-only", "--format=", "HEAD"]).split())
        self.expect(committed == mirrors, "the save step's commit holds exactly the verdict mirror",
                    {"committed": committed, "mirrors": mirrors})
        self.facts["save_step"] = {"files": step["files"], "commands": step["commands"], "committed": committed}

    def finish(self):
        self.ship_result = self.ship(["report", "--bottom-line", "The replay's slice A went through the loop."], 10)
        self.facts["ship_result"] = read_json(os.path.join(self.ship_run, "result.json"))

    def open_visit(self, station):
        visit = self.ship(["visit", "--station", station], 0)
        root = visit.get("root")
        self.expect(visit.get("visited") == station and isinstance(root, str), "ship-v2 hands over %s" % station,
                    visit)
        self.expect(os.path.realpath(visit.get("skill_md", "")) == os.path.realpath(
            os.path.join(root, "skills", station, "SKILL.md")), "the SKILL.md handed over is the station's own",
            visit.get("skill_md"))
        self.visits.append({"station": station, "root": root, "route": visit.get("route"),
                            "identity": visit.get("identity"), "run_dir": visit.get("visit_run_dir")})
        return visit, root

    def close_visit(self):
        return self.ship(["visit", "--result"], 0)

    def build_visit(self):
        visit, root = self.open_visit("build-v2")
        mine = self.mine["build"]
        run_dir = visit["visit_run_dir"]
        doc = {"input_version": 1, "run_id": visit["visit_run_id"], "run_dir": run_dir, "workspace": self.ws,
               "build_doc": DOC, "slice": SLICE, "base": "base",
               "invocation": {"harness": None, "caller": visit["caller"], "mode": visit["mode"],
                              "session_id": SESSIONS["build"]}}
        path = write_json(run_dir + ".input.json", doc)
        self.cli("build-v2", root, ["check-input", path], 0)
        contract = self.cli("build-v2", root, ["contract", "--run-dir", run_dir], 0)
        self.cli("build-v2", root, ["preflight", "--run-dir", run_dir], 0)
        self.apply(mine["edits_from"])
        checks = []
        for check in contract["contract"]["checks"]:
            code, output = self.run_check(check["command"])
            checks.append({"name": check["name"], "command": check["command"], "exit_code": code, "output": output,
                           "result": "passed" if code == 0 else "failing"})
        answer = {"seeded_answer": 1, "case": "replay-%s" % self.kind, "role": "executor",
                  "session_id": SESSIONS["build"], "claimed_status": mine["claimed_status"],
                  "claimed_card": mine["claimed_card"], "edits": mine["edits"], "checks": checks,
                  "notes": mine["notes"]}
        self.cli("build-v2", root, ["record-answer", "--run-dir", run_dir, "--answer",
                                    self.answer_file("build.json", answer)], 0)
        self.cli("build-v2", root, ["report", "--run-dir", run_dir], 10)
        self.build_result = os.path.join(run_dir, "result.json")
        self.facts["build_status"] = read_json(self.build_result).get("status")
        self.close_visit()

    def signoff_visit(self):
        visit, root = self.open_visit("signoff-v2")
        mine = self.mine["review"]
        run_dir = visit["visit_run_dir"]
        replay_env = {"SIGNOFF_TEST": "1", "SIGNOFF_TEST_REPLAY_MODEL": REPLAY_MODEL}
        doc = {"protocol_version": 1, "workspace": self.ws, "report_only": False,
               "invocation": {"mode": visit["mode"], "caller": visit["caller"], "run_id": visit["visit_run_id"],
                              "run_dir": run_dir, "run_date": DATE, "harness": None,
                              "sessions": {"building": SESSIONS["build"], "reviewing": SESSIONS["review"]}},
               "target": {"build_doc": DOC, "slice": SLICE, "base": "base"},
               "review": {"depth": "LEAN", "route": "recorded-answer", "builder_conversation": []}}
        path = write_json(run_dir + ".input.json", doc)
        self.cli("signoff-v2", root, ["check-input", path], 0, replay_env)
        self.cli("signoff-v2", root, ["scope", "--run-dir", run_dir], 0, replay_env)
        self.cli("signoff-v2", root, ["request", "--run-dir", run_dir], 0, replay_env)
        executed = []
        for name, command in (("unit", "sh checks/unit.sh"),):
            code, output = self.run_check(command)
            executed.append({"name": name, "command": command, "exit_code": code, "output": output})
        findings = []
        for finding in mine["findings"]:
            rel, line = finding["location"].rsplit(":", 1)
            with open(os.path.join(self.ws, rel), "r", encoding="utf-8") as fh:
                held = fh.read().split("\n")[int(line) - 1]
            self.expect(held == finding["at_line"], "the recorded finding's location holds the line it names",
                        {"location": finding["location"], "holds": held})
            findings.append(dict((k, v) for k, v in finding.items() if k != "at_line"))
        answer = {"role": "reviewer", "session_id": SESSIONS["review"], "model": REPLAY_MODEL,
                  "checks_executed": executed, "findings": findings, "notes_kept": mine["notes_kept"],
                  "verdict": mine["verdict"], "notes": mine["notes"]}
        self.cli("signoff-v2", root, ["record-answer", "--run-dir", run_dir, "--answer",
                                      self.answer_file("signoff.json", answer)], 0, replay_env)
        self.cli("signoff-v2", root, ["record", "--run-dir", run_dir], 10, replay_env)
        self.signoff_result = read_json(os.path.join(run_dir, "result.json"))
        return self.close_visit()

    def fix(self, after):
        mine = self.mine["fix"]
        named = after.get("named") or []
        self.facts["named"] = named
        if not self.expect(len(named) == 1, "ship-v2 names the one finding the reviewer raised", named):
            raise Stop("ship-v2 named %d findings to fix" % len(named))
        written = self.apply(mine["edits_from"])
        fixes = {"answer_version": 1, "kind": "fixes", "lap": 1, "run_id": "replay-%s-ship" % self.kind,
                 "fixes": [{"finding": named[0]["id"], "paths": written, "summary": mine["summary"]}],
                 "spec_change": []}
        return self.ship(["fix", "--fixes", self.answer_file("fixes.json", fixes)], 0)

    def recheck_visit(self):
        visit, root = self.open_visit("recheck-v2")
        mine = self.mine["verifier"]
        run_dir = visit["visit_run_dir"]
        doc = {"protocol_version": 1, "workspace": self.ws, "target": {"build_doc": DOC, "slice": SLICE},
               "invocation": {"mode": visit["mode"], "caller": visit["caller"], "run_id": visit["visit_run_id"],
                              "run_dir": run_dir, "resume": False, "run_date": DATE,
                              "harness": {"name": "replay", "version": "0", "entry": "explicit path",
                                          "sandbox": "none"},
                              "model": {"id": REPLAY_MODEL, "floor_class": "opus", "floor_met": True},
                              "session_wrote_fix": True}}
        path = write_json(run_dir + ".input.json", doc)
        self.cli("recheck-v2", root, ["check-input", path], 0)
        started = self.cli("recheck-v2", root, ["start", path], 0)
        if not self.expect(started.get("next") == "verify", "recheck-v2 starts and asks for the verifier",
                           started.get("next")):
            raise Stop("recheck-v2 did not reach verify")
        rows = []
        for index, item in enumerate(mine["items"]):
            rows.append({"index": index, "location": started["checklist"][index]["location"]
                         if isinstance(started["checklist"][index].get("location"), str)
                         else "%s:%s" % (started["checklist"][index]["location"]["file"],
                                         started["checklist"][index]["location"]["line"]),
                         "disposition": item["disposition"], "reason": item.get("reason"), "method": "executed",
                         "static_reason": None, "blocked": None, "missing": None, "missed_case": None,
                         "evidence": [{"kind": "command", "detail": item["detail"], "artifact": None}],
                         "location_after_fix": item.get("location_after_fix")})
        tail = {"recheck_verifier_report": 1, "items": rows, "new_defects": [], "grant_claims": [],
                "injection_attempts": [], "refused_actions": []}
        raw = os.path.join(run_dir, "verifier", "raw.md")
        os.makedirs(os.path.dirname(raw), exist_ok=True)
        with open(raw, "w", encoding="utf-8") as fh:
            fh.write("# Verifier report\n\n%s\n\n```json\n%s\n```\n" % (mine["prose"],
                                                                       json.dumps(tail, indent=1)))
        called = self.cli("recheck-v2", root, ["record-call", "--run-dir", run_dir, "--call-id", started["call_id"],
                                               "--status", "ok", "--raw", raw, "--model", REPLAY_MODEL,
                                               "--kind", "recorded"], 0)
        for item in called.get("items") or []:
            self.cli("recheck-v2", root, ["adjudicate", "--run-dir", run_dir, "--item", str(item["index"]),
                                          "--action", "confirmed"], 0)
        self.cli("recheck-v2", root, ["record", "--run-dir", run_dir], 10)
        self.recheck_result = read_json(os.path.join(run_dir, "result.json"))
        return self.close_visit()

    # ---- handoff-v2's photograph ------------------------------------------------------------------------------

    def handoff(self):
        root = self.roots["handoff-v2"]
        run_dir = os.path.join(self.runs, "handoff")
        doc = {"input_version": 1, "run_id": "replay-%s-handoff" % self.kind, "run_dir": run_dir,
               "workspace": self.ws, "station": {"slice": SLICE},
               "invocation": {"harness": "codex-cli", "caller": "user", "mode": "direct",
                              "session_id": SESSIONS["ship"]}}
        path = write_json(os.path.join(self.runs, "inputs", "handoff.json"), doc)
        self.cli("handoff-v2", root, ["check-input", path], 0)
        self.cli("handoff-v2", root, ["select", "--run-dir", run_dir, "--doc", DOC], 0)
        photo = self.cli("handoff-v2", root, ["photograph", "--run-dir", run_dir, "--suite-record",
                                              self.build_result], 0)
        self.facts["photograph"] = photo
        self.state_after_loop = self.records("state", "--workspace", self.ws, "--doc", DOC)
        gate = self.cli("handoff-v2", root, ["gate", "--run-dir", run_dir, "--questions",
                                             self.answer_file("handoff-questions.json",
                                                              {"answer_version": 1, "kind": "questions",
                                                               "questions": [], "run_id": doc["run_id"]})], 0)
        self.facts["handoff_questions"] = gate.get("questions")
        answers = {"answer_version": 1, "kind": "answers", "answers": [], "run_id": doc["run_id"],
                   "perishables": self.answers["handoff"]["perishables"]}
        self.cli("handoff-v2", root, ["record-answer", "--run-dir", run_dir, "--answer",
                                      self.answer_file("handoff-answers.json", answers)], 0)
        self.handoff_write = self.cli("handoff-v2", root, ["write", "--run-dir", run_dir], 0)
        self.cli("handoff-v2", root, ["report", "--run-dir", run_dir, "--bottom-line",
                                      "Slice A is signed off and the loop is complete."], 10)
        self.handoff_result = read_json(os.path.join(run_dir, "result.json"))

    # ---- vertical-v2's gate and packets -----------------------------------------------------------------------

    def readers(self, argv, want=0, env_extra=None):
        script = os.path.join(self.roots["readers"], "skills", "readers", "assets", "readers.py")
        return self.run(("readers", argv[0] if not argv[0].startswith("/") else "run"),
                        self.python + [script] + list(argv), want, env_extra)

    def canned_claude(self, text):
        folder = os.path.join(self.root, "canned", "claude-lens")
        os.makedirs(folder, exist_ok=True)
        write_json(os.path.join(folder, "stdout.json"),
                   {"type": "result", "subtype": "success", "is_error": False, "stop_reason": "end_turn",
                    "session_id": "00000000-0000-4000-8000-0000000000aa", "num_turns": 1, "result": text,
                    "modelUsage": {REPLAY_MODEL: {"inputTokens": 10, "outputTokens": 40}},
                    "permission_denials": []})
        open(os.path.join(folder, "stderr.txt"), "w").close()
        with open(os.path.join(folder, "exit"), "w") as fh:
            fh.write("0\n")
        return folder

    def canned_codex(self, text):
        folder = os.path.join(self.root, "canned", "codex-outside")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "events.jsonl"), "w", encoding="utf-8") as fh:
            for event in ({"type": "thread.started", "thread_id": "replay-thread"}, {"type": "turn.started"},
                          {"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 0,
                                                               "output_tokens": 20}}):
                fh.write(json.dumps(event) + "\n")
        with open(os.path.join(folder, "output.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
        open(os.path.join(folder, "stderr.txt"), "w").close()
        with open(os.path.join(folder, "exit"), "w") as fh:
            fh.write("0\n")
        return folder

    def vertical(self):
        root = self.roots["vertical-v2"]
        mine = self.mine["vertical"]
        run_dir = os.path.join(self.runs, "vertical")
        self.vertical_run = run_dir
        run_id = "replay-%s-vertical" % self.kind
        doc = {"input_version": 1, "run_id": run_id, "run_dir": run_dir, "workspace": self.ws, "station": {},
               "invocation": {"harness": "codex-cli", "caller": "user", "mode": "direct",
                              "session_id": SESSIONS["ship"]}}
        path = write_json(os.path.join(self.runs, "inputs", "vertical.json"), doc)
        self.cli("vertical-v2", root, ["check-input", path], 0)
        self.vertical_gate = self.cli("vertical-v2", root, ["gate", "--run-dir", run_dir, "--doc", DOC], 0)
        ask = self.cli("vertical-v2", root, ["ask", "--run-dir", run_dir], 0)
        files = []
        for index, call in enumerate(ask.get("suggest") or []):
            out = self.readers(call["argv"], 0, None)
            files.append(write_json(os.path.join(self.runs, "answers", "suggest-%d.json" % index), out))
        if not self.expect(len(files) == 2, "vertical-v2's ask names two suggest calls", ask.get("suggest")):
            raise Stop("vertical-v2's ask did not name two suggest calls")
        self.cli("vertical-v2", root, ["ask", "--run-dir", run_dir, "--local-suggest", files[0],
                                       "--outside-suggest", files[1]], 0)
        answer = {"answer_version": 1, "kind": "ask", "run_id": run_id, "rows": mine["ask"]["rows"],
                  "words": mine["ask"]["words"]}
        self.cli("vertical-v2", root, ["ask", "--run-dir", run_dir, "--answer",
                                       self.answer_file("vertical-ask.json", answer)], 0)
        self.vertical_scope = self.cli("vertical-v2", root, ["scope", "--run-dir", run_dir], 0)
        self.packets_after_scope = self.packet_facts(os.path.join(run_dir, "packets"))
        local = self.cli("vertical-v2", root, ["request", "--run-dir", run_dir], 0)
        self.facts["outside_before_record_local"] = sorted(
            n for n in os.listdir(os.path.join(run_dir, "requests")) if "outside" in n) if os.path.isdir(
            os.path.join(run_dir, "requests")) else []
        self.facts["requests_outside_file_before_record_local"] = os.path.exists(
            os.path.join(run_dir, "requests-outside.json"))
        self.summons_after_local = self.packet_facts(os.path.join(run_dir, "summons"))
        canned = {"READERS_TEST": "1", "READERS_CANNED_CLAUDE": self.canned_claude(mine["lens_reply"])}
        for call in local["calls"]:
            self.readers([call["request_file"]], 0, canned)
        tried = mine["local"]["tried"]
        record = {"answer_version": 1, "kind": "local", "run_id": run_id, "method": mine["local"]["method"],
                  "findings": mine["local"]["findings"], "tried": tried}
        self.cli("vertical-v2", root, ["record-local", "--run-dir", run_dir, "--answer",
                                       self.answer_file("vertical-local.json", record)], 0)
        outside = self.cli("vertical-v2", root, ["request", "--run-dir", run_dir, "--outside"], 0)
        self.summons_after_outside = self.packet_facts(os.path.join(run_dir, "summons"))
        canned = {"READERS_TEST": "1", "READERS_CANNED_CODEX": self.canned_codex(mine["outside_reply"])}
        calls = outside.get("calls") or []
        for call in calls:
            self.readers([call["request_file"]], 0, canned)
        findings = []
        for finding in mine["outside"]["findings"]:
            findings.append(dict(finding, found_by=[c["call_id"] for c in calls]))
        record = {"answer_version": 1, "kind": "outside", "run_id": run_id, "findings": findings}
        self.cli("vertical-v2", root, ["record-outside", "--run-dir", run_dir, "--answer",
                                       self.answer_file("vertical-outside.json", record)], 0)
        self.vertical_verdict = self.cli("vertical-v2", root, ["verdict", "--run-dir", run_dir], 0)
        self.cli("vertical-v2", root, ["report", "--run-dir", run_dir, "--bottom-line",
                                       "The vertical of slice A holds; nothing to fix."], 10)
        self.vertical_result = read_json(os.path.join(run_dir, "result.json"))

    def packet_facts(self, folder):
        """{packet: {"files": {relative path: sha256}, "listed": files.json, "withheld": withheld.json}} for every
        packet or summons copy under `folder`."""
        out = {}
        if not os.path.isdir(folder):
            return out
        for name in sorted(os.listdir(folder)):
            base = os.path.join(folder, name)
            if not os.path.isdir(base) or os.path.islink(base):
                continue
            files, texts = {}, {}
            for top, dirs, names in os.walk(base):
                dirs.sort()
                for leaf in sorted(names + [d for d in dirs if d == ".git"]):
                    full = os.path.join(top, leaf)
                    rel = os.path.relpath(full, base)
                    if os.path.isfile(full) and not os.path.islink(full):
                        files[rel] = sha256_of(full)
                        with open(full, "r", encoding="utf-8", errors="replace") as fh:
                            texts[rel] = fh.read()
                    else:
                        files[rel] = "not a file"
            listed = os.path.join(base, "files.json")
            withheld = os.path.join(base, "withheld.json")
            out[name] = {"files": files, "texts": texts,
                         "listed": read_json(listed) if os.path.isfile(listed) else None,
                         "withheld": read_json(withheld) if os.path.isfile(withheld) else None}
        return out

    # ---- the assertions ---------------------------------------------------------------------------------------

    def trace_lines(self, run_dir):
        path = os.path.join(run_dir, "trace.jsonl")
        if not os.path.isfile(path):
            return []
        with open(path, "r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def validate_trace(self, run_dir, root, station):
        script = os.path.join(root, "skills", station, "scripts", "validate-trace.py")
        path = os.path.join(run_dir, "trace.jsonl")
        if not os.path.isfile(path):
            return None
        return self.run((station, "validate-trace.py"), self.python + [script, path], 0)

    def identity_holds(self, line, expected):
        identity = line.get("identity") or {}
        root = identity.get("root") or ""
        problems = []
        if identity.get("name") != expected:
            problems.append("names itself %r" % identity.get("name"))
        if identity.get("name") in v1_names():
            problems.append("a v1 name")
        if identity.get("interface_version") != 1:
            problems.append("interface %r" % identity.get("interface_version"))
        if not root or v1_part(root) is not None:
            problems.append("root %r sits under a v1 folder" % root)
        if line.get("route") not in ("3a", "3b"):
            problems.append("route %r" % line.get("route"))
        manifest = os.path.join(root, ".claude-plugin", "plugin.json")
        if os.path.isfile(manifest) and read_json(manifest).get("version") != identity.get("version"):
            problems.append("version %r is not its root's manifest's" % identity.get("version"))
        return problems

    def assert_loop(self):
        result = self.facts["ship_result"]
        sr = result.get("station_result") or {}
        want = {"clean": {"signoff": "signed off", "recheck": "not run", "laps": 0},
                "findings": {"signoff": "signed off with conditions", "recheck": "ALL CLEAR", "laps": 1}}[self.kind]
        got = {"status": result.get("status"), "stop_tag": result.get("stop_tag"),
               "result_line": sr.get("result_line"), "build": sr.get("build"), "signoff": sr.get("signoff"),
               "recheck": sr.get("recheck"), "card": sr.get("card"), "laps": (sr.get("laps") or {}).get("taken"),
               "build_status": self.facts.get("build_status")}
        wanted = {"status": "completed", "stop_tag": None, "result_line": "ALL CLEAR", "build": "COMPLETE",
                  "signoff": want["signoff"], "recheck": want["recheck"], "card": "signed off",
                  "laps": want["laps"], "build_status": "completed"}
        self.expect(got == wanted, "ship-v2's run ends as the recorded answers say", {"got": got, "want": wanted})
        got = dict(got, save_step=self.facts.get("save_step"))
        if self.kind == "findings":
            self.expect(self.recheck_result.get("result") == "all_clear", "recheck-v2's verifier finds the fix landed",
                        self.recheck_result.get("result"))
        bad = [e for e in self.log if e.get("want") is not None and e.get("exit") != e.get("want")]
        self.expect(not bad, "every command exits as its contract says", bad)
        return got

    def assert_trace(self):
        lines = self.trace_lines(self.ship_run)
        order = [(l.get("kind"), l.get("expected"), l.get("status")) for l in lines]
        stations = ["build-v2", "signoff-v2"] + (["recheck-v2"] if self.kind == "findings" else [])
        closing = {"build-v2": "completed", "signoff-v2": "completed", "recheck-v2": "completed"}
        want = []
        for station in stations:
            want += [("visit", station, "visiting"), ("visit", station, closing[station])]
        self.expect(order == want, "ship-v2's trace holds the loop's visits in order", {"got": order, "want": want})
        identity_problems = {}
        for index, line in enumerate(lines):
            problems = self.identity_holds(line, line.get("expected"))
            if problems:
                identity_problems[index] = problems
        self.expect(not identity_problems, "every ship-v2 trace line names a v2 identity", identity_problems)
        checked = self.validate_trace(self.ship_run, self.roots["ship-v2"], "ship-v2")
        self.expect(checked is not None and checked.get("ok") is True, "validate-trace.py holds ship-v2's trace",
                    checked)
        vlines = self.trace_lines(self.vertical_run)
        summons = [(l.get("kind"), l.get("expected"), l.get("status"), l.get("row")) for l in vlines]
        self.expect(len(vlines) == 4 and all(s[:3] == ("summons", "readers", "ok") for s in summons),
                    "vertical-v2's trace holds one ok summons line per reader call (three lenses, one outside row)",
                    summons)
        vproblems = {}
        for index, line in enumerate(vlines):
            identity = line.get("identity") or {}
            root = identity.get("root") or ""
            if identity.get("name") != "readers" or not root or v1_part(root) is not None:
                vproblems[index] = identity
        self.expect(not vproblems, "every vertical-v2 trace line names readers at a root under no v1 folder",
                    vproblems)
        vchecked = self.validate_trace(self.vertical_run, self.roots["vertical-v2"], "vertical-v2")
        self.expect(vchecked is not None and vchecked.get("ok") is True,
                    "validate-trace.py holds vertical-v2's trace", vchecked)
        return {"ship": order, "vertical": summons,
                "identities": sorted(set("%s %s (interface %s, route %s)" % (
                    (l.get("identity") or {}).get("name"), (l.get("identity") or {}).get("version"),
                    (l.get("identity") or {}).get("interface_version"), l.get("route")) for l in lines + vlines))}

    def assert_photograph(self):
        photo = self.facts["photograph"]
        state = self.state_after_loop
        records_cards = dict((s["name"], {"card": s.get("card_observed"), "card_derived": s.get("card_derived")})
                             for s in state.get("slices") or [] if s.get("name") != "none")
        photo_cards = dict((c["name"], {"card": c.get("card"), "card_derived": c.get("card_derived")})
                           for c in photo.get("cards") or [])
        self.expect(photo_cards == records_cards, "handoff-v2's cards are the records' cards",
                    {"photograph": photo_cards, "records": records_cards})
        records_open = sorted(f["id"] for f in state.get("findings") or [] if f.get("status") == "open")
        photo_open = sorted((o.get("id") if isinstance(o, dict) else o) for o in photo.get("open") or [])
        self.expect(photo_open == records_open, "handoff-v2's open set is the records' open set",
                    {"photograph": photo_open, "records": records_open})
        branch = self.facts["branch_at_photograph"]
        repo = photo.get("repo") or {}
        self.expect(repo.get("branch") == branch and repo.get("tree") == "clean" and not repo.get("dirt"),
                    "handoff-v2's branch and tree are git's", {"photograph": repo, "git_branch": branch})
        for name, card in records_cards.items():
            self.expect(card["card"] == "signed off", "the records hold slice %s signed off after the loop" % name,
                        card)
        block = (self.handoff_write.get("block") or {}).get("text") or ""
        cards_line = "- Cards: %s" % ", ".join("%s %s" % (n, c["card"]) for n, c in sorted(records_cards.items()))
        self.expect(cards_line in block.split("\n"), "the handoff block carries the photograph's cards",
                    {"want": cards_line, "block": block})
        move = self.handoff_write.get("next_move") or {}
        self.expect(move.get("shape") == "loop-complete" and move.get("kickoff") is None,
                    "the loop complete gives no kickoff line", move)
        return {"cards": photo_cards, "open": photo_open, "repo": {"branch": repo.get("branch"),
                                                                  "tree": repo.get("tree")},
                "next_move": move.get("shape"), "suite": (photo.get("suite") or {}).get("state")}

    def review_record_lines(self):
        """Lines of the review record at the reviewed commit (the verdict docs, the records log, and the build doc's
        withheld sections) that appear in no other tracked file: none may reach a packet."""
        listed = self.git(["ls-files"]).split("\n")
        record, other = set(), set()
        for rel in [r for r in listed if r]:
            with open(os.path.join(self.ws, rel), "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().split("\n")
            if rel.startswith("docs/reviews/") or rel.startswith("docs/records/"):
                record.update(l.strip() for l in lines)
            elif rel == DOC:
                section = None
                for line in lines:
                    if line.startswith("## "):
                        section = line.strip()
                    if section in WITHHELD_HEADINGS or line.startswith("Status:"):
                        record.add(line.strip())
                    else:
                        other.add(line.strip())
            else:
                other.update(l.strip() for l in lines)
        return sorted(l for l in record - other if len(l) >= 12)

    def packet_problems(self, facts, record_lines):
        out = {}
        for name, packet in facts.items():
            problems = []
            for rel, digest in packet["files"].items():
                parts = rel.split(os.sep)
                if ".git" in parts:
                    problems.append("history in the packet: %s" % rel)
                inner = rel.split("workspace" + os.sep, 1)[-1] if rel.startswith("workspace" + os.sep) else None
                if inner and (inner.startswith("docs/reviews/") or inner.startswith("docs/records/")):
                    problems.append("a review record in the packet: %s" % rel)
                if digest == "not a file":
                    continue
                text = packet["texts"][rel]
                lines = set(l.strip() for l in text.split("\n"))
                for heading in WITHHELD_HEADINGS:
                    if heading in lines:
                        problems.append("%s holds the withheld heading %s" % (rel, heading))
                if any(l.startswith("Status:") for l in lines) and rel.endswith(".md"):
                    problems.append("%s holds a Status: line" % rel)
                leaked = [l for l in record_lines if l in lines]
                if leaked:
                    problems.append("%s holds %d line(s) of the review record, first: %s" % (rel, len(leaked),
                                                                                        leaked[0]))
            listed = packet.get("listed")
            if listed is not None:
                for row in listed.get("files") or []:
                    at = row.get("at")
                    if packet["files"].get(at) != row.get("sha256"):
                        problems.append("files.json names %s at a hash the copy does not hold" % at)
            withheld = packet.get("withheld")
            if withheld is not None:
                named = " | ".join(w.get("what", "") for w in withheld.get("withheld") or [])
                for want in ("docs/reviews/", "docs/records/", "Status:") + WITHHELD_HEADINGS:
                    if want not in named:
                        problems.append("withheld.json does not name %s" % want)
            if problems:
                out[name] = problems
        return out

    def assert_vertical(self):
        gate = self.vertical_gate
        self.expect(gate.get("next") == "ask", "vertical-v2's gate passes every slice signed off", gate)
        record_lines = self.review_record_lines()
        problems = {"packets": self.packet_problems(self.packets_after_scope, record_lines),
                    "summons (local)": self.packet_problems(self.summons_after_local, record_lines),
                    "summons (outside)": self.packet_problems(self.summons_after_outside, record_lines)}
        self.expect(not any(problems.values()), "every packet vertical-v2 cut follows its contract", problems)
        names = sorted(self.packets_after_scope)
        self.expect(names == ["local-correctness", "local-seams", "local-spec", "outside-gpt-astra"],
                    "scope cuts one packet per local lens and per outside row named", names)
        self.expect(not self.facts["outside_before_record_local"]
                    and not self.facts["requests_outside_file_before_record_local"],
                    "no outside request file exists before record-local",
                    {"files": self.facts["outside_before_record_local"],
                     "requests-outside.json": self.facts["requests_outside_file_before_record_local"]})
        sr = self.vertical_result.get("station_result") or {}
        refuted = sr.get("refuted")
        want_refuted = sum(1 for f in self.mine["vertical"]["outside"]["findings"] if f.get("stamp") == "REFUTED")
        self.expect(self.vertical_result.get("status") == "completed" and refuted == want_refuted,
                    "vertical-v2 ends completed and counts what was refuted",
                    {"status": self.vertical_result.get("status"), "refuted": refuted, "want": want_refuted})
        return {"packets": names, "record_lines_checked": len(record_lines),
                "withheld_named": sorted(set(w.get("what", "").split(" ")[0] if w.get("what", "").startswith("docs/r")
                                             else w.get("what", "") for p in self.packets_after_scope.values()
                                             for w in (p.get("withheld") or {}).get("withheld") or [])),
                "verdict": sr.get("verdict"), "refuted": refuted, "verdict_doc": sr.get("verdict_doc")}

    def walk(self):
        self.setup()
        self.loop()
        self.checkpoint_commit("loop checkpoint (local)")
        self.facts["branch_at_photograph"] = self.git(["rev-parse", "--abbrev-ref", "HEAD"]).strip()
        self.handoff()
        self.checkpoint_commit("handoff checkpoint (local)")
        self.vertical()
        return {"loop": self.assert_loop(), "trace": self.assert_trace(), "photograph": self.assert_photograph(),
                "vertical": self.assert_vertical()}


def _same_below(path, base):
    """The part of `path` below `base` by the file system's own identity ("" when they are the same
    folder), or None. macOS names one folder by more than one path that neither abspath nor realpath
    rewrites (/System/Volumes/Data/..., /.nofollow/..., /.resolve/N/...), so the nearest existing
    ancestor of `path` is compared with `base` by device and inode."""
    try:
        want = os.stat(base)
    except OSError:
        return None
    probe, tail = os.path.realpath(path), []
    while True:
        try:
            if os.path.samestat(os.stat(probe), want):
                return os.sep.join(reversed(tail)).casefold()
        except OSError:
            pass
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        tail.append(os.path.basename(probe))
        probe = parent


def _below_home(path, base, home):
    """`_same_below`, and for a `base` that does not exist yet the same answer read through HOME: `path` is
    compared with HOME by device and inode and the part below HOME is read against `base`'s place below it."""
    got = _same_below(path, base)
    if got is not None:
        return got
    below = _same_below(path, home)
    if below is None:
        return None
    rel = os.path.relpath(base, home).casefold()
    return "" if below == rel else (below[len(rel) + 1:] if below.startswith(rel + os.sep) else None)


def guard(paths):
    """The setups' home guard, before anything is created: None, or the refusal line."""
    home = os.environ.get("HOME", "")
    if not os.path.isabs(home):
        return "replay.py: HOME is not an absolute path; nothing created"
    share = os.path.join(home, ".local", "share")
    temps = [os.environ[name] for name in ("TMPDIR", "TEMP", "TMP") if os.environ.get(name)] or ["/tmp"]
    for path in [form(p) for p in paths for form in (os.path.abspath, os.path.realpath)] + \
            [form(t) for t in temps for form in (os.path.abspath, os.path.realpath)]:
        for base in (os.path.join(home, ".claude"), os.path.join(home, ".codex"), share):
            for form in (os.path.abspath(base), os.path.realpath(base), None):
                p, b = path.casefold(), (form or "").casefold().rstrip(os.sep)
                below = (_below_home(path, base, home) if form is None
                         else "" if p == b else (p[len(b) + 1:] if p.startswith(b + os.sep) else None))
                if below is None or (base == share and not below.split(os.sep)[0].startswith("skills-v2-")):
                    continue
                return ("replay.py: %s is under %s, which no setup may touch; nothing created"
                        % (path, base if base != share else os.path.join(share, below.split(os.sep)[0])))
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(prog="replay.py", description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keep", metavar="DIR", help="build the trees in DIR (must not exist) and keep them")
    parser.add_argument("--path", choices=("clean", "findings", "both"), default="both",
                        help="which path to walk (default both)")
    parser.add_argument("--root", action="append", default=[], metavar="STATION=DIR",
                        help="run ship-v2, handoff-v2, vertical-v2, readers or records from DIR")
    parser.add_argument("--watch", action="append", default=[], metavar="DIR",
                        help="a folder that must not change (this checkout's plugins tree always is one)")
    parser.add_argument("--trace-out", metavar="FILE", help="write every trace line the paths' runs wrote")
    args = parser.parse_args(argv)
    roots = {}
    for given in args.root:
        station, _, folder = given.partition("=")
        if station not in OWN_ROOTS + ("readers", "records") or not folder:
            parser.error("--root takes STATION=DIR, STATION one of %s" % ", ".join(OWN_ROOTS + ("readers", "records")))
        roots[station] = os.path.abspath(folder)
    if args.keep and os.path.exists(args.keep):
        parser.error("--keep %s exists" % args.keep)
    refused = guard(([args.keep] if args.keep else [os.environ.get("TMPDIR") or "/tmp"])
                    + ([args.trace_out] if args.trace_out else []))
    if refused:
        sys.stderr.write(refused + "\n")
        return 2
    for station in OWN_ROOTS + ("readers", "records"):
        roots.setdefault(station, os.path.join(PLUGINS, station))
    root = os.path.abspath(args.keep) if args.keep else tempfile.mkdtemp(prefix="back-replay-")
    os.makedirs(root, exist_ok=True)
    root = os.path.realpath(root)
    watched = [PLUGINS] + [os.path.abspath(w) for w in args.watch]
    before = dict((w, tree_state(w)) for w in watched)
    python, note = interpreter()
    answers = read_json(os.path.join(FIXTURE, "answers.json"))
    kinds = ("clean", "findings") if args.path == "both" else (args.path,)
    summary = {"replay": "back of the loop, E15 slice 3 (lane contract section 11, item 5)",
               "stations_run_by": note, "roots": roots, "paths": {}, "problems": []}
    traces = {}
    try:
        for kind in kinds:
            path = Path(os.path.join(root, kind), kind, roots, answers, python, note)
            entry = {"commands": path.log}
            summary["paths"][kind] = entry
            try:
                entry["assertions"] = path.walk()
                entry["visited"] = path.visits
            except Stop as exc:
                path.problems.append({"path": kind, "assertion": "the replay ran to its end", "evidence": str(exc)})
            finally:
                traces[kind] = {"ship": path.trace_lines(path.ship_run),
                                "vertical": path.trace_lines(os.path.join(path.runs, "vertical"))}
            summary["problems"].extend(path.problems)
        confined = dict((w, tree_state(w) == before[w]) for w in watched)
        summary["confined"] = confined
        if not all(confined.values()):
            summary["problems"].append({"assertion": "nothing written outside each path's tree",
                                        "evidence": confined})
        if args.trace_out:
            write_json(os.path.abspath(args.trace_out), traces)
    finally:
        if not args.keep:
            shutil.rmtree(root, ignore_errors=True)
    summary["tree"] = root if args.keep else "removed"
    summary["ok"] = not summary["problems"]
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
