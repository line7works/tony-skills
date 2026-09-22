"""Schema loading, and the checks a schema cannot make.

`jsonschema` is the one declared dependency, at the pilot's pin, through `uv run`. A command that
needs it and cannot import it exits 3 with one line on stderr and nothing on stdout; `--help` and
argument checking work without it, so a caller can always find out what a command takes.

The semantic checks close what Draft 2020-12 leaves open for this station:

- the run directory is outside the workspace, and every artifact the result names sits under it;
- a raised finding's location file is in the source set, and a note's is not;
- the verdict is the severity mapping over the raised findings;
- a result with no raised findings carries a non-empty `checks_executed`, each with output;
- a result that records a verdict has status `completed` and is not report-only;
- a report-only result wrote nothing and recorded no verdict;
- every path in `records_written` is the run directory, the ledger document, its verdict doc, or
  the component's log — nothing else is an authorized write of this station.
"""
import os
import sys

from . import verdict as vdmod
from .constants import MISSING_JSONSCHEMA, RECORDS_PREFIX


class MissingDependency(RuntimeError):
    pass


def load_jsonschema():
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        raise MissingDependency(MISSING_JSONSCHEMA)
    return jsonschema


def exit_missing_dependency(message=MISSING_JSONSCHEMA):
    sys.stderr.write(message.rstrip("\n") + "\n")
    raise SystemExit(3)


def schema_errors(doc, schema):
    """[{path, message}] in path order, [] when the document validates."""
    jsonschema = load_jsonschema()
    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for error in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        pointer = "/" + "/".join(str(part) for part in error.absolute_path)
        out.append({"path": pointer if pointer != "/" else "/", "message": error.message})
    return out


def path_rules(doc):
    """[] when the input's paths hold, else one reason each. Not expressible in a schema."""
    reasons = []
    workspace = doc.get("workspace", "")
    run_dir = (doc.get("invocation") or {}).get("run_dir", "")
    if workspace and run_dir:
        ws = os.path.realpath(workspace)
        rd = os.path.realpath(run_dir)
        if rd == ws or rd.startswith(ws + os.sep):
            reasons.append("the run directory %s is inside the workspace; a run's artifacts are "
                           "never part of the source it reviews" % run_dir)
    if workspace and not os.path.isdir(workspace):
        reasons.append("the workspace %s does not exist or is not a directory" % workspace)
    build_doc = (doc.get("target") or {}).get("build_doc", "")
    if workspace and build_doc:
        real = os.path.realpath(os.path.join(workspace, build_doc))
        ws = os.path.realpath(workspace)
        if real != ws and not real.startswith(ws + os.sep):
            reasons.append("the build doc %s reaches outside the workspace" % build_doc)
    for rel in ((doc.get("review") or {}).get("builder_conversation") or []):
        if rel.startswith("/") or ".." in rel.split("/"):
            reasons.append("the declared builder-conversation path %r is not workspace-relative"
                           % rel)
    return reasons


def authorized_write(rel, run_dir, workspace, build_doc, verdict_doc):
    """Is this path one of the writes this station is allowed to make?"""
    absolute = rel if os.path.isabs(rel) else os.path.join(workspace, rel)
    real = os.path.realpath(absolute)
    if real.startswith(os.path.realpath(run_dir) + os.sep) or real == os.path.realpath(run_dir):
        return True
    ws = os.path.realpath(workspace)
    if not (real == ws or real.startswith(ws + os.sep)):
        return False
    inside = os.path.relpath(real, ws).replace(os.sep, "/")
    if inside == build_doc:
        return True
    if verdict_doc and inside == verdict_doc:
        return True
    return inside.startswith(RECORDS_PREFIX)


def semantic(result, input_doc=None):
    """[] when the result holds together, else one finding per rule it breaks."""
    out = []
    raised = result.get("findings") or []
    notes = result.get("notes") or []
    checks = result.get("checks_executed") or []
    source = result.get("source_set") or {}
    in_set = set(source.get("committed", []) + source.get("changed", [])
                 + source.get("untracked", []))

    if source:
        for row in raised:
            if row.get("file") not in in_set:
                out.append({"path": "/findings", "message":
                            "the raised finding at %s sits outside the source set; a location "
                            "outside the set is kept as a note, never raised" % row.get("location")})
        for row in notes:
            if row.get("why") == "the location is outside the source set" and row.get("file") in in_set:
                out.append({"path": "/notes", "message":
                            "the note at %s is inside the source set but was not raised"
                            % row.get("location")})

    if result.get("status") == "completed" and not result.get("report_only"):
        want = vdmod.verdict_for([row.get("severity") for row in raised])
        if result.get("verdict") != want:
            out.append({"path": "/verdict", "message":
                        "the verdict %r is not the severity mapping over the raised findings (%r)"
                        % (result.get("verdict"), want)})

    listed = [row for row in checks if str(row.get("output") or "").strip()]
    if not raised and result.get("status") == "completed" and not listed:
        out.append({"path": "/checks_executed", "message":
                    "a review with no findings carries the checks it executed, each with its "
                    "output; an empty list is not a clean verdict"})
    if result.get("clean_review_checks_listed") and not listed:
        out.append({"path": "/clean_review_checks_listed", "message":
                    "clean_review_checks_listed is true but no executed check carries output"})

    if result.get("verdict_recorded"):
        if result.get("status") != "completed":
            out.append({"path": "/verdict_recorded", "message":
                        "a verdict is recorded only by a completed run; this one is %r"
                        % result.get("status")})
        if result.get("report_only"):
            out.append({"path": "/verdict_recorded", "message":
                        "a report-only run records no verdict"})
    if result.get("refusal_reason") and result.get("verdict_recorded"):
        out.append({"path": "/verdict_recorded", "message":
                    "the run refused for %r and still recorded a verdict"
                    % result.get("refusal_reason")})

    if result.get("report_only"):
        project = [row for row in (result.get("records_written") or [])
                   if row.get("kind") != "run_artifact"]
        if project:
            out.append({"path": "/records_written", "message":
                        "a report-only run writes nothing to the workspace and nothing to the "
                        "log; it listed %d project write(s)" % len(project)})
        if not result.get("writes_none"):
            out.append({"path": "/writes_none", "message":
                        "a report-only run reports writes_none true"})

    run = result.get("run") or {}
    if run.get("run_dir") and run.get("workspace"):
        for row in (result.get("records_written") or []):
            if not authorized_write(row["path"], run["run_dir"], run["workspace"],
                                    run.get("build_doc") or "", result.get("verdict_doc")):
                out.append({"path": "/records_written", "message":
                            "%s is not an authorized write of this station" % row["path"]})

    if input_doc is not None:
        target = input_doc.get("target") or {}
        if run.get("build_doc") and target.get("build_doc") \
                and run["build_doc"] != target["build_doc"]:
            out.append({"path": "/run/build_doc", "message":
                        "the result names a different build doc than the input"})
        if bool(input_doc.get("report_only")) != bool(result.get("report_only")):
            out.append({"path": "/report_only", "message":
                        "the result's report_only differs from the input's"})
    return out
