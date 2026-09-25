"""The run directory of a precon-v2 run: its phase gate, its files, and its one result.

The checkpoint's `phase` moves `checked` -> `selected` (the frame's) -> `harvested` ->
`answered` -> `written` -> `done`. A run that reached `done` has a `result.json`; every phase
command against it reports that result again (exit 10) and writes nothing.

The result is assembled here for every ending, a completion or a stop: validated against
`references/result.schema.json` and the shared semantic checks (S1 to S4) before it is written,
written through a rename, and printed with its keys in the order they were built, so the gate is
the last field of `station_result`.
"""
import json
import os
import sys

from station_core import driver, exits, fsio, validate

PHASES = ("checked", "selected", "harvested", "answered", "written", "done")
READERS_DIR = "readers"          # readers' own run directory for the exit test, inside the run
EXIT_TEST_DIR = "exit-test"      # the requests this run built
PREVIEW_DIR = "preview"          # report-only: the documents the run would have written


def emit(document, code):
    """stdout: one JSON document, keys in build order (the gate last), nothing else."""
    sys.stdout.write(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return code


def open_run(ctx, args):
    """The run, or its recorded result printed again when it has already ended (exit 10)."""
    run = ctx.open_run(args.run_dir)
    if run.checkpoint.get("phase") == "done":
        path = os.path.join(run.run_dir, "result.json")
        try:
            doc = fsio.read_json(path)
        except (OSError, ValueError) as exc:
            raise driver.Defect("the run at %s ended but its result cannot be read: %s" % (run.run_dir, exc))
        raise Ended(doc)
    return run


class Ended(RuntimeError):
    """The run has already ended: its result is printed again, exit 10."""

    def __init__(self, document):
        RuntimeError.__init__(self, "ended")
        self.document = document


def need(run, allowed, command, hint):
    phase = run.checkpoint.get("phase")
    if phase not in allowed:
        raise driver.Usage("this run is at phase %r; `%s` runs %s" % (phase, command, hint))
    return phase


class Outside(RuntimeError):
    """A path this run would open or write resolves where it does not belong: a run artifact outside the
    run directory (`outside-run`), or a document outside its home (`outside-home`). Every phase and own
    command refuses it with exit 5 and the refusal on stdout; nothing was written (R1 and R2 of round 5)."""

    def __init__(self, rule, message, target):
        RuntimeError.__init__(self, message)
        self.rule, self.message, self.target = rule, message, target

    def refusal(self):
        return {"rule": self.rule, "message": self.message, "path": self.target}


def path(run, *parts):
    """A run artifact's path, resolved and checked to lie inside the run directory before anything opens
    or writes it: a symlinked artifact folder (`preview`, `exit-test`, `readers`), or a symlinked artifact
    file, that leaves the run is refused, so report-only's "nothing was written outside the run
    directory" holds."""
    full = os.path.join(run.run_dir, *parts)
    if not fsio.inside(full, run.run_dir):
        raise Outside("outside-run", "the run artifact %s resolves outside the run directory %s (a symlink?)"
                      % (full, run.run_dir), full)
    return full


def preflight(run, *names):
    """Every artifact path a command will write, checked before the first is written."""
    return [path(run, *(name if isinstance(name, tuple) else (name,))) for name in names]


def read_json(run, name, default=None):
    full = path(run, name)
    if not os.path.isfile(full):
        return default
    try:
        return fsio.read_json(full)
    except (OSError, ValueError) as exc:
        raise driver.Defect("the run file %s cannot be read: %s" % (full, exc))


def write_json(run, name, doc):
    full = path(run, name)
    fsio.write_json(full, doc)
    return full


def advance(run, phase):
    run.checkpoint["phase"] = phase
    run.save()


def station_input(run):
    return run.input.get("station") or {}


def report_only(run):
    return bool(run.input.get("report_only"))


# ---- the result --------------------------------------------------------------------------------

def _run_artifacts(run):
    """Every file this run wrote under its directory (readers' own directory excluded)."""
    rows = []
    for base, dirs, files in os.walk(run.run_dir):
        rel = os.path.relpath(base, run.run_dir)
        if rel == READERS_DIR or rel.startswith(READERS_DIR + os.sep):
            dirs[:] = []
            continue
        dirs[:] = sorted(d for d in dirs if not (rel == "." and d == READERS_DIR))
        for name in sorted(files):
            full = os.path.join(base, name)
            if rel == "." and name == "result.json":
                continue
            rows.append({"path": full, "kind": "run_artifact", "sha256_before": None,
                         "sha256_after": fsio.sha256_file(full)})
    return rows


def _selections(run):
    out = {}
    for name in sorted(os.listdir(run.run_dir)):
        if name.startswith("selection-") and name.endswith(".json"):
            body = read_json(run, name)
            if isinstance(body, dict):
                out[name[len("selection-"):-len(".json")]] = body
    return out


def finish(ctx, run, status, reason, station_result, stop_tag=None):
    """Assemble, validate, write and print the result; the run is `done`. Exit 10.

    The checkpoint says `done` before the result is assembled, so the result's writes list the
    checkpoint as it ends; a result that does not validate (a defect) puts the checkpoint back at the
    phase it was, so a run is never `done` without its `result.json` (CP1-16)."""
    prior = run.checkpoint.get("phase")
    result_path = path(run, "result.json")
    advance(run, "done")
    try:
        return _finish(ctx, run, status, reason, station_result, stop_tag)
    except BaseException:
        if not os.path.isfile(result_path):
            advance(run, prior)
        raise


def _finish(ctx, run, status, reason, station_result, stop_tag):
    receipt = read_json(run, "receipt.json", {}) or {}
    writes = list(receipt.get("writes") or []) + _run_artifacts(run)
    writes.append({"path": path(run, "result.json"), "kind": "run_artifact", "sha256_before": None,
                   "sha256_after": None})
    outside = [w for w in writes if w["kind"] != "run_artifact"]
    doc = ctx.envelope(run_id=run.checkpoint["run_id"], run_dir=run.run_dir, status=status, stop_tag=stop_tag,
                       reason=reason, report_only=report_only(run), wrote_nothing=not outside, writes=writes,
                       selection=_selections(run), invocation=run.input.get("invocation"),
                       station_result=station_result)
    schema = validate.load_schema("result", ctx.prefix, ctx.skill_root)
    problems = validate.errors_for(doc, schema, ctx.prefix) + validate.semantic(doc)
    if problems:
        raise driver.Defect("the result this run assembled does not validate (a defect of the script): %s"
                            % json.dumps(problems, ensure_ascii=False))
    fsio.atomic_write(path(run, "result.json"), (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return emit(doc, exits.TERMINAL)


def stop(ctx, run, stop_tag, reason, station_result):
    return finish(ctx, run, "stopped", reason, station_result, stop_tag=stop_tag)
