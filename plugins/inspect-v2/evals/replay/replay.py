#!/usr/bin/env python3
"""The end-to-end replay across the front of the loop (E14 slice 3c, item 3.8; contract section 13).

    python3 replay.py [--keep DIR]

`--keep DIR` is refused, exit 2 and nothing created, when it is or sits under ~/.claude, ~/.codex or a
~/.local/share/skills-v2-* home, as given or resolved (the setups' home guard, E14 slice 3c).
The interpreter that runs this file starts before its guard: where TMPDIR, TEMP or TMP may point into a
protected folder, start it through uv or a real interpreter, not the /usr/bin/python3 shim.

One fixture project (`fixtures/turnstile/`, the seeded cases' turnstile idea: a bench-rig turn
counter) is copied into a fresh temporary tree, made a git work tree, and walked through the five
stations in order, each through its REAL phase driver in this checkout:

    precon-v2      check-input, select scope, harvest, record-answer, write, report: the scope doc
    architect-v2   check-input, select scope, select architecture, harvest, record-answer, write,
                   render-visual, report: the architecture doc (publish false, review declined)
    blueprint-v2   check-input, select scope, architecture and build, harvest, record-answer, write,
                   report: the build doc
    inspect-v2     check-input, select build, select scope, harvest, packet, request, record-answer
                   (the recorded reader answer `fixtures/turnstile/inspect-reader-results.json`; no
                   reader is launched), write, report
    build-v2       check-input, then contract for slice A: run, never changed

The recorded answers are the executor's, fixture files: a `@ledger:<text>@` in one stands for the
ledger id the station's own `harvest` printed for the line with that text, `@run@` for the run id,
`@session@` for the session, `@today@` for the date `harvest` recorded. Nothing else is filled.

The script's own assertions, printed as one JSON summary (exit 0 only when every one held):

    handoffs       every hand-off (the scope doc to architect, both docs to blueprint, the build doc
                   and the scope doc to inspect) found by `select` with outcome `one`, no `--path`;
                   and each station's own new-doc hunt (precon's scope, architect's architecture,
                   blueprint's build) found nothing before the doc was written
                   (a hunt with any other outcome stops the replay there, its outcome and
                   candidates named in the problem, the selects so far under `facts`)
    ids_forward    every decided line of the scope doc's ledger reaches the build doc: its id is
                   the trace of a line of blueprint's accepted answer, its text is in the build doc,
                   and no answered question of architect or blueprint touches it (never re-asked)
    contract       build-v2's `contract` for slice A holds the slice's requirements (R1, R2) exactly
                   as the build doc states them and as blueprint's accepted answer gave them
    exits          every command's exit code as the contracts say (0 for a phase with more to do, 10
                   for `report`; inspect-v2's `write` ends the run `records-refused` with exit 10
                   while the records component recognises no inspect mirror, ruling E14-2 as read
                   in slice 3b)
    confined       nothing written outside the fixture workspace and the run directories: the
                   staging home unchanged, nothing else in the temporary tree, and this checkout's
                   `plugins/` tree unchanged (paths, sizes and modification times)

Runtimes: the stations run through the interpreter running this script when it imports
`jsonschema`, else through `uv run --offline --python /usr/bin/python3 --with jsonschema==4.25.1
python` (the stations' declared dependency); the summary names which. Standard library only,
Python 3.9; no network, no model call, no harness launch. `--keep DIR` builds the tree in DIR
(which must not exist) and leaves it; otherwise the temporary tree is removed.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "turnstile")
PLUGINS = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
IDEA = "turnstile"
SLICE = "A"
DATE = "2026-09-20"
SESSION = "session-replay-1"
DRIVERS = {"precon-v2": "precon.py", "architect-v2": "architect.py", "blueprint-v2": "blueprint.py",
           "inspect-v2": "inspect_v2.py", "build-v2": "build.py"}
GIT_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0",
           "GIT_AUTHOR_NAME": "Replay", "GIT_AUTHOR_EMAIL": "replay@example.invalid",
           "GIT_COMMITTER_NAME": "Replay", "GIT_COMMITTER_EMAIL": "replay@example.invalid",
           "GIT_AUTHOR_DATE": "2026-09-19T09:00:00-07:00", "GIT_COMMITTER_DATE": "2026-09-19T09:00:00-07:00"}
GIT_ARGS = ["-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]


def interpreter():
    try:
        import jsonschema  # noqa: F401
        return [sys.executable], "this interpreter (%s), which imports jsonschema" % sys.executable
    except ImportError:
        return (["uv", "run", "--offline", "--quiet", "--python", "/usr/bin/python3", "--with",
                 "jsonschema==4.25.1", "python"],
                "uv run --offline --python /usr/bin/python3 --with jsonschema==4.25.1 python (this "
                "interpreter, %s, does not import jsonschema)" % sys.executable)


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


class Replay(object):
    def __init__(self, root):
        self.root = root
        self.ws = os.path.join(root, "workspace")
        self.staging = os.path.join(root, "staging")
        self.runs = os.path.join(root, "runs")
        self.cwd = os.path.join(self.runs, "cwd")
        self.python, self.python_note = interpreter()
        self.env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/"),
                    "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1",
                    "TMPDIR": os.path.join(root, "tmp")}
        self.log = []          # every command: station, argv tail, exit, wanted
        self.problems = []
        self.facts = {}

    # ---- plumbing ------------------------------------------------------------------------------

    def setup(self):
        shutil.copytree(os.path.join(FIXTURE, "workspace"), self.ws)
        for folder in (self.staging, self.runs, self.cwd, self.env["TMPDIR"]):
            os.makedirs(folder, exist_ok=True)
        self.git(["init", "-q", "-b", "main"])
        self.git(["add", "-A"])
        self.git(["commit", "-q", "-m", "base"])

    def git(self, args):
        env = dict(self.env, **GIT_ENV)
        proc = subprocess.run(["git"] + GIT_ARGS + args, cwd=self.ws, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise RuntimeError("git %s: %s" % (" ".join(args), proc.stderr.decode("utf-8", "replace")))
        return proc.stdout.decode("utf-8")

    def cli(self, station, args, want):
        driver = os.path.join(PLUGINS, station, "skills", station, "scripts", DRIVERS[station])
        proc = subprocess.run(self.python + [driver] + [str(a) for a in args], cwd=self.cwd, env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8", "replace")
        try:
            doc = json.loads(out) if out.strip() else None
        except ValueError:
            doc = None
        entry = {"station": station, "command": args[0], "exit": proc.returncode, "want": want}
        self.log.append(entry)
        if proc.returncode != want:
            entry["stderr"] = proc.stderr.decode("utf-8", "replace")[-800:]
            entry["stdout"] = out[-800:]
            raise Stop("%s %s exited %d, the contract says %d" % (station, args[0], proc.returncode, want))
        return doc

    def run_dir(self, station):
        return os.path.join(self.runs, station)

    def check_input(self, station, doc):
        path = os.path.join(self.runs, "input-%s.json" % station)
        write_json(path, doc)
        return self.cli(station, ["check-input", path], 0)

    def front_input(self, station, run_id, station_fields=None):
        doc = {"input_version": 1, "run_id": run_id, "workspace": self.ws, "staging": self.staging,
               "run_dir": self.run_dir(station),
               "invocation": {"harness": None, "caller": "user", "mode": "direct", "session_id": SESSION}}
        if station_fields is not None:
            doc["station"] = station_fields
        return doc

    def select(self, station, hunt, name=None, handoff=True):
        """`select` with no `--path` (a hand-off), or the new-doc check a station makes before it
        writes a doc of its own (`handoff=False`: the hunt must find nothing)."""
        args = ["select", "--run-dir", self.run_dir(station), "--hunt", hunt]
        if name:
            args += ["--name", name]
        doc = self.cli(station, args, 0)
        found = {"station": station, "hunt": hunt, "outcome": doc.get("outcome"),
                 "candidates": [c["path"] for c in doc.get("candidates") or []], "path_flag": False}
        self.facts.setdefault("handoffs" if handoff else "new_docs", []).append(found)
        want = "one" if handoff else "none"
        if found["outcome"] != want:
            raise Stop("%s select --hunt %s found outcome %s; the %s needs %s (candidates: %s)" % (
                station, hunt, found["outcome"], "hand-off" if handoff else "new doc's own hunt", want,
                ", ".join(found["candidates"]) or "none"))
        return found

    def phase(self, station, name, want, *extra):
        return self.cli(station, [name, "--run-dir", self.run_dir(station)] + list(extra), want)

    def record(self, station, answer, want=0):
        folder = os.path.join(self.run_dir(station), "executor")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "answer.json")
        write_json(path, answer)
        return self.phase(station, "record-answer", want, "--answer", path)

    # ---- the stations --------------------------------------------------------------------------

    def precon(self):
        st = "precon-v2"
        self.check_input(st, self.front_input(st, "replay-precon", {"date": DATE, "home": "repo"}))
        self.select(st, "scope", IDEA, handoff=False)
        harvest = self.phase(st, "harvest", 0)
        answer = fill(load_fixture("precon-answer.json"), "replay-precon", {}, harvest)
        self.record(st, answer)
        written = self.phase(st, "write", 0)
        result = self.phase(st, "report", 10)
        self.expect(result.get("status") == "completed", "precon-v2's run completed", result)
        self.scope_doc = os.path.join(self.ws, "docs", "scope", "%s-%s.md" % (DATE, IDEA))
        self.expect(os.path.isfile(self.scope_doc), "precon-v2 wrote the scope doc", written)
        return result

    def architect(self):
        st = "architect-v2"
        self.check_input(st, self.front_input(st, "replay-architect"))
        self.select(st, "scope")
        self.select(st, "architecture", IDEA, handoff=False)
        harvest = self.phase(st, "harvest", 0)
        ledger = ledger_of(harvest)
        self.scope_ledger = ledger
        answer = fill(load_fixture("architect-answer.json"), "replay-architect", ledger, harvest)
        self.answers = {"architect": answer}
        self.record(st, answer)
        self.phase(st, "write", 0)
        self.phase(st, "render-visual", 0)
        result = self.phase(st, "report", 10)
        self.expect(result.get("status") == "completed", "architect-v2's run completed", result)
        doc = (result.get("station_result") or {}).get("doc_path")
        self.arch_doc = doc
        self.expect(bool(doc) and os.path.isfile(doc), "architect-v2 wrote the architecture doc", result)
        return result

    def blueprint(self):
        st = "blueprint-v2"
        self.check_input(st, self.front_input(st, "replay-blueprint"))
        self.select(st, "scope", IDEA)
        self.select(st, "architecture", IDEA)
        self.select(st, "build", IDEA, handoff=False)
        harvest = self.phase(st, "harvest", 0)
        ledger = ledger_of(harvest)
        answer = fill(load_fixture("blueprint-answer.json"), "replay-blueprint", ledger, harvest)
        self.answers["blueprint"] = answer
        self.blueprint_ledger = ledger
        self.record(st, answer)
        written = self.phase(st, "write", 0)
        result = self.phase(st, "report", 10)
        self.expect(result.get("status") == "completed", "blueprint-v2's run completed", result)
        self.build_doc = (result.get("station_result") or {}).get("doc") or written.get("doc")
        self.expect(bool(self.build_doc) and os.path.isfile(self.build_doc), "blueprint-v2 wrote the build doc",
                    result)
        return result

    def inspect(self):
        st = "inspect-v2"
        doc = self.front_input(st, "replay-inspect", {"row": "claude-session", "session_model": "claude-opus-5-5"})
        self.check_input(st, doc)
        self.select(st, "build", IDEA)
        self.select(st, "scope")
        self.phase(st, "harvest", 0)
        self.phase(st, "packet", 0)
        self.phase(st, "request", 0)
        recorded = fill(load_fixture("inspect-reader-results.json"), "replay-inspect", {}, {})
        answer = {"answer_version": 1, "run_id": "replay-inspect", "session_id": SESSION, "questions": [],
                  "lines": [], "row": "claude-session", "lanes": ["code-book", "repo-reality", "traceability"]}
        answer.update(recorded)
        self.record(st, answer)
        written = self.phase(st, "write", 10)
        self.expect(written.get("status") == "stopped" and written.get("stop_tag") == "records-refused",
                    "inspect-v2's write stops records-refused (no inspect mirror is recognised yet)", written)
        result = self.phase(st, "report", 10)
        self.inspect_result = result
        return result

    def build(self):
        st = "build-v2"
        rel = os.path.relpath(self.build_doc, self.ws)
        doc = {"input_version": 1, "run_id": "replay-build", "workspace": self.ws, "run_dir": self.run_dir(st),
               "build_doc": rel, "slice": SLICE, "base": self.git(["rev-parse", "HEAD"]).strip(),
               "invocation": {"harness": None, "caller": "user", "mode": "direct"}}
        self.check_input(st, doc)
        printed = self.phase(st, "contract", 0)
        with open(os.path.join(self.run_dir(st), "contract.json"), encoding="utf-8") as fh:
            self.contract = json.load(fh)  # the contract the phase wrote (section 11 of its contract)
        return printed

    # ---- the assertions ------------------------------------------------------------------------

    def expect(self, ok, what, evidence=None):
        if not ok:
            self.problems.append({"assertion": what, "evidence": evidence})

    def assert_handoffs(self):
        rows = self.facts.get("handoffs") or []
        bad = [r for r in rows if r["outcome"] != "one" or r["path_flag"]]
        self.expect(len(rows) == 5 and not bad, "every hand-off found by select, outcome one, no --path",
                    rows)
        fresh = self.facts.get("new_docs") or []
        stale = [r for r in fresh if r["outcome"] != "none"]
        self.expect(len(fresh) == 3 and not stale, "each new doc's own hunt found nothing before it was "
                                                   "written", fresh)
        return {"count": len(rows), "all_one": not bad, "rows": rows,
                "new_doc_hunts": {"count": len(fresh), "all_none": not stale, "rows": fresh}}

    def assert_ids_forward(self):
        decided = {i: t for i, (tag, t) in self.scope_ledger.items() if tag == "decided"}
        build_text = read(self.build_doc)
        traced = {}
        for line in self.answers["blueprint"]["lines"]:
            trace = line.get("trace") or {}
            if trace.get("kind") == "ledger":
                traced[trace.get("ref")] = line["text"]
        touched = set()
        for name in ("architect", "blueprint"):
            for q in self.answers[name].get("questions") or []:
                touched.update(q.get("touches") or [])
        rows = []
        for ident, text in sorted(decided.items()):
            row = {"id": ident, "text": text, "traced_by_blueprint": ident in traced,
                   "in_build_doc": ident in traced and traced[ident] in build_text,
                   "re_asked": ident in touched}
            rows.append(row)
        ok = bool(rows) and all(r["traced_by_blueprint"] and r["in_build_doc"] and not r["re_asked"] for r in rows)
        self.expect(ok, "every decided scope line reaches the build doc by its id, never re-asked", rows)
        return {"decided": len(rows), "held": ok, "rows": rows}

    def assert_contract(self):
        build_text = read(self.build_doc)
        section = build_text.split("## Slice %s " % SLICE, 1)[-1].split("\n## ", 1)[0]
        block = section.split("Requirements:\n", 1)[-1].split("Acceptance criteria:", 1)[0]
        in_doc = [line[2:] for line in block.splitlines() if line.startswith("- ")]
        answered = [line["text"] for line in self.answers["blueprint"]["lines"]
                    if line.get("tag") == "requirement"
                    and line.get("id") in self.answers["blueprint"]["slices"][0]["requirements"]]
        held = self.contract.get("requirements")
        ok = (self.contract.get("slice") == SLICE and bool(held) and held == in_doc and held == answered)
        self.expect(ok, "build-v2's contract holds slice A's requirements as the build doc states them",
                    {"contract": held, "build_doc": in_doc, "answer": answered})
        return {"slice": SLICE, "contract_requirements": held, "build_doc_requirements": in_doc, "held": ok}

    def assert_exits(self):
        bad = [e for e in self.log if e["exit"] != e["want"]]
        self.expect(not bad, "every exit code as the contracts say", bad)
        return {"commands": len(self.log), "as_the_contracts_say": not bad}


class Stop(Exception):
    """A command did not exit as its contract says; the replay stops there."""


def load_fixture(name):
    with open(os.path.join(FIXTURE, name), encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def ledger_of(harvest):
    """{id: (tag, text)} of every ledger line the harvest printed (scope doc, architecture doc)."""
    out = {}

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("id"), str) and isinstance(node.get("text"), str) and "tag" in node:
                out[node["id"]] = (node["tag"], node["text"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(harvest)
    return out


PLACEHOLDER = re.compile(r"@(ledger:[^@]+|run|session|today)@")


def fill(node, run_id, ledger, harvest):
    by_text = {}
    for ident, (tag, text) in ledger.items():
        by_text.setdefault(text, ident)
    today = find_date(harvest)

    def one(value):
        if isinstance(value, dict):
            return {k: one(v) for k, v in value.items()}
        if isinstance(value, list):
            return [one(v) for v in value]
        if isinstance(value, str):
            def sub(match):
                key = match.group(1)
                if key == "run":
                    return run_id
                if key == "session":
                    return SESSION
                if key == "today":
                    return today
                text = key[len("ledger:"):]
                if text not in by_text:
                    raise Stop("the recorded answer names a ledger line harvest did not print: %r" % text)
                return by_text[text]
            return PLACEHOLDER.sub(sub, value)
        return value
    return one(node)


def find_date(harvest):
    text = json.dumps(harvest or {})
    found = re.search(r'"(?:today|date|run_date)": "(\d{4}-\d{2}-\d{2})"', text)
    return found.group(1) if found else DATE


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


def main(argv=None):
    parser = argparse.ArgumentParser(prog="replay.py", description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keep", metavar="DIR", help="build the tree in DIR (must not exist) and keep it")
    args = parser.parse_args(argv)
    if args.keep and os.path.exists(args.keep):
        parser.error("--keep %s exists" % args.keep)
    if True:
        # The setups' home guard (E14 slice 3c fix 3-2), before anything is created.
        out = os.path.abspath(args.keep) if args.keep else os.path.abspath(os.environ.get("TMPDIR") or "/tmp")
        home = os.environ.get("HOME", "")
        share = os.path.join(home, ".local", "share")
        temps = [os.environ[name] for name in ("TMPDIR", "TEMP", "TMP") if os.environ.get(name)] or ["/tmp"]
        for path in [out, os.path.realpath(out)] + [form(t) for t in temps for form in (os.path.abspath, os.path.realpath)]:
            for base in (os.path.join(home, ".claude"), os.path.join(home, ".codex"), share):
                for form in (os.path.abspath(base), os.path.realpath(base), None):
                    p, b = path.casefold(), (form or "").casefold().rstrip(os.sep)
                    below = (_same_below(path, base) if form is None
                             else "" if p == b else (p[len(b) + 1:] if p.startswith(b + os.sep) else None))
                    if below is None or (base == share and not below.split(os.sep)[0].startswith("skills-v2-")):
                        continue
                    sys.stderr.write("replay.py: %s is under %s, which no setup may touch; nothing created\n"
                                     % (path, base if base != share else os.path.join(share, below.split(os.sep)[0])))
                    return 2
        if not os.path.isabs(home):
            sys.stderr.write("replay.py: HOME is not an absolute path; nothing created\n")
            return 2
    root = os.path.abspath(args.keep) if args.keep else tempfile.mkdtemp(prefix="front-replay-")
    os.makedirs(root, exist_ok=True)
    root = os.path.realpath(root)
    before_plugins = tree_state(PLUGINS)
    replay = Replay(root)
    summary = {"replay": "front of the loop, E14 slice 3c item 3.8", "stations_run_by": replay.python_note,
               "assertions": {}, "commands": replay.log, "problems": replay.problems}
    stopped = None
    try:
        replay.setup()
        staging_before = tree_state(replay.staging)
        outside_before = set(os.listdir(root))
        replay.precon()
        replay.architect()
        replay.blueprint()
        replay.inspect()
        replay.build()
        a = summary["assertions"]
        a["handoffs"] = replay.assert_handoffs()
        a["ids_forward"] = replay.assert_ids_forward()
        a["contract"] = replay.assert_contract()
        a["exits"] = replay.assert_exits()
        confined = {"staging_unchanged": tree_state(replay.staging) == staging_before,
                    "nothing_else_in_the_tree": set(os.listdir(root)) == outside_before,
                    "checkout_plugins_unchanged": tree_state(PLUGINS) == before_plugins}
        replay.expect(all(confined.values()), "nothing written outside the fixture workspace and the run "
                                              "directories", confined)
        a["confined"] = confined
        summary["documents"] = {"scope": os.path.relpath(replay.scope_doc, root),
                                "architecture": os.path.relpath(replay.arch_doc, root),
                                "build": os.path.relpath(replay.build_doc, root)}
    except Stop as exc:
        summary["facts"] = replay.facts
        stopped = str(exc)
        replay.problems.append({"assertion": "the replay ran to its end", "evidence": stopped})
    finally:
        if not args.keep:
            shutil.rmtree(root, ignore_errors=True)
    summary["tree"] = root if args.keep else "removed"
    summary["ok"] = not replay.problems
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
