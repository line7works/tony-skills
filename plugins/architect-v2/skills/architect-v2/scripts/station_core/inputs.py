"""The input: read it, fill its defaults, and hold it to the path rules a schema cannot state.

One validated input document per run (station-loop.md section 4). Every caller value arrives as
data, an argv item or a file, and nothing is ever pasted into shell text. The path rules:

    the workspace is an existing absolute directory
    the staging home, when given, is an existing absolute directory
    the run directory is absolute and lies inside neither the workspace nor the staging home, so a
      run's own artifacts are never part of what it reads, and a report-only run can write them
      while writing nothing where the owner's documents live

A failure is reported the way a schema finding is, `{"path": "<json pointer>", "message": ...}`,
so a caller reads one list.
"""
import json
import os
import re

from . import fsio, validate

DEFAULTS = {"report_only": False, "station": {}}


class InputUnreadable(RuntimeError):
    """The file is not there, or it is not a JSON object: a usage slip, not a validation failure."""


def read(path):
    if not os.path.isfile(path):
        raise InputUnreadable("no such input file: %s" % path)
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise InputUnreadable("the input file is not JSON: %s (%s)" % (path, exc))
    if not isinstance(doc, dict):
        raise InputUnreadable("the input file is not a JSON object: %s" % path)
    return doc


def with_defaults(doc):
    out = dict(doc)
    for key, value in DEFAULTS.items():
        out.setdefault(key, value if not isinstance(value, dict) else dict(value))
    return out


def path_rules(doc):
    errors = []
    workspace = doc.get("workspace")
    staging = doc.get("staging")
    run_dir = doc.get("run_dir")
    if isinstance(workspace, str) and workspace:
        if not os.path.isabs(workspace):
            errors.append({"path": "/workspace", "message": "the workspace is an absolute path"})
        elif not os.path.isdir(workspace):
            errors.append({"path": "/workspace", "message": "the workspace is an existing directory: %s" % workspace})
    if isinstance(staging, str) and staging:
        if not os.path.isabs(staging):
            errors.append({"path": "/staging", "message": "the staging home is an absolute path"})
        elif not os.path.isdir(staging):
            errors.append({"path": "/staging", "message": "the staging home is an existing directory: %s" % staging})
    if isinstance(run_dir, str) and run_dir:
        if not os.path.isabs(run_dir):
            errors.append({"path": "/run_dir", "message": "the run directory is an absolute path"})
        else:
            for label, home in (("workspace", workspace), ("staging home", staging)):
                if isinstance(home, str) and home and os.path.isdir(home) and fsio.inside(run_dir, home):
                    errors.append({"path": "/run_dir",
                                   "message": "the run directory lies outside the %s; %s is inside %s"
                                              % (label, run_dir, home)})
    owner_word = doc.get("owner_word")
    if isinstance(owner_word, dict):
        words = owner_word.get("words")
        from . import answer as _answer
        if isinstance(words, str) and not _answer._visible(words).strip():
            errors.append({"path": "/owner_word/words", "message": "the owner's words are not blank, whitespace "
                                                                    "or invisible characters only"})
    return errors


def validate_input(doc, schema, prefix):
    """[{path, message}]: the schema's findings, then the path rules', in that order."""
    errors = validate.errors_for(doc, schema, prefix)
    if errors:
        return errors
    return path_rules(doc)


def input_digest(doc):
    return fsio.sha256_bytes(fsio.canonical_json(doc).encode("utf-8"))
