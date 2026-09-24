"""The input: read it, validate it, and hold it to the rules a schema cannot state.

One validated input structure per run (lane contract section 8). Every caller value arrives as
data — an argv item or a file — and nothing is ever pasted into shell text.

The path rules, which the schema cannot express and this module enforces:

    the workspace is an absolute git work tree ROOT with a HEAD commit
    the run directory is absolute and OUTSIDE the workspace, so a run's own artifacts are never
      part of the source it judges (and a report-only run can write them while writing nothing
      to the workspace)
    the build doc is workspace-relative, normalized, inside the workspace, ends in `.md`, and is
      not under docs/records/ or docs/reviews/, which the records component refuses as ledger
      addresses anyway

A failure of any of them is a validation failure reported the same way a schema failure is:
`{"path": "<json pointer>", "message": "..."}`, so a caller reads one list.
"""
import json
import os

from . import canon, sources, validate

DEFAULTS = {"report_only": False, "allow_open_blocker": False, "rerun_checks": False}
FORBIDDEN_DOC_PREFIXES = ("docs/records/", "docs/reviews/")


class InputUnreadable(RuntimeError):
    """The file is not there, or it is not a JSON object: a usage slip, not a validation failure."""


def read(path):
    """The document at `path`. A missing or unparsable file is a usage slip (exit 2)."""
    if not os.path.isfile(path):
        raise InputUnreadable("no such input file: %s" % path)
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except ValueError as exc:
        raise InputUnreadable("the input file is not JSON: %s (%s)" % (path, exc))
    if not isinstance(doc, dict):
        raise InputUnreadable("the input file is not a JSON object: %s" % path)
    return doc


def with_defaults(doc):
    """The input with the optional switches filled in, so every later phase reads one shape."""
    out = dict(doc)
    for key, value in DEFAULTS.items():
        out.setdefault(key, value)
    return out


def path_rules(doc):
    """[{path, message}] for the rules the schema cannot state; empty when they all hold."""
    errors = []
    workspace = doc.get("workspace")
    run_dir = doc.get("run_dir")
    document = doc.get("build_doc")

    if isinstance(workspace, str) and workspace:
        if not os.path.isabs(workspace):
            errors.append({"path": "/workspace", "message": "the workspace is an absolute path"})
        else:
            ok, why = sources.is_work_tree_root(workspace)
            if not ok:
                errors.append({"path": "/workspace", "message": "the workspace %s" % why})

    if isinstance(run_dir, str) and run_dir:
        if not os.path.isabs(run_dir):
            errors.append({"path": "/run_dir", "message": "the run directory is an absolute path"})
        elif isinstance(workspace, str) and workspace and os.path.isdir(workspace):
            real_run = os.path.realpath(run_dir)
            real_ws = os.path.realpath(workspace)
            if real_run == real_ws or real_run.startswith(real_ws + os.sep):
                errors.append({"path": "/run_dir",
                               "message": "the run directory is outside the workspace; %s is inside %s"
                                          % (run_dir, workspace)})

    if isinstance(document, str) and document:
        if os.path.isabs(document):
            errors.append({"path": "/build_doc", "message": "the build doc is workspace-relative"})
        else:
            normal = os.path.normpath(document)
            if normal != document:
                errors.append({"path": "/build_doc",
                               "message": "the build doc is normalized: %r reads as %r" % (document, normal)})
            if normal.startswith(".."):
                errors.append({"path": "/build_doc", "message": "the build doc is inside the workspace"})
            if not normal.endswith(".md"):
                errors.append({"path": "/build_doc", "message": "the build doc is a Markdown document"})
            for prefix in FORBIDDEN_DOC_PREFIXES:
                if normal.startswith(prefix):
                    errors.append({"path": "/build_doc",
                                   "message": "%s is not a ledger address: %s is the records "
                                              "component's own history or a mirror of one"
                                              % (normal, prefix)})
    return errors


def validate_input(doc, schemas=None, root=None, environ=None):
    """[{path, message}]: the schema's findings, then the path rules', in that order."""
    schema = (schemas or {}).get("input") or validate.load_schema("input", root, environ)
    errors = validate.errors_for(doc, schema, environ)
    if errors:
        return errors
    return path_rules(doc)


def input_digest(doc):
    """The canonical digest a later phase binds against, so a run cannot be re-pointed."""
    return canon.sha256_hex(canon.canonical_json(doc))
