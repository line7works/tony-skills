"""Schema loading and validation, the jsonschema guard, and the result's semantic checks.

Schemas are loaded from the skill root (the directory holding SKILL.md), resolved from this
package's own location (`scripts/station_core` -> `scripts` -> the skill root) unless a root is
given; never from a checkout path and never from a plugin cache. A reference that is missing or
does not parse stops the command rather than being worked around.

`jsonschema==4.25.1` is the one declared dependency, supplied by `uv run` through the driver's
PEP 723 block. It is imported lazily: `require_jsonschema()` writes the one-line message to stderr
and exits 3 with nothing on stdout when it cannot be imported, so `--help` and every argument check
still work without it.

The semantic checks of a result (station-loop.md section 5):

    S1  a `stopped` result carries a stop tag and a reason; a `completed` one carries no tag
    S2  a report-only result lists no write outside the run directory and says `wrote_nothing`
    S3  `wrote_nothing` is true exactly when no write lies outside the run directory
    S4  a write under the run directory is a `run_artifact`, and a `run_artifact` lies under it
"""
import json
import os
import re
import sys

MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"

try:  # the guarded import: a missing jsonschema is reported once, at the first use
    from jsonschema import Draft202012Validator as _Validator, FormatChecker as _FormatChecker
except ImportError:  # pragma: no cover - exercised through a subprocess by the exit-3 tests
    _Validator = None
    _FormatChecker = None

SCHEMA_FILES = {"input": "input.schema.json", "result": "result.schema.json"}
CHECK_IDS = ("S1", "S2", "S3", "S4")


class ReferenceUnavailable(RuntimeError):
    """A schema under the skill root is missing, unreadable, or not a schema."""


class SkillRootMissing(RuntimeError):
    """An explicit `--skill-root` that is not a directory: a usage slip."""


def prefix_of(station):
    """`PRECON_V2` for `precon-v2`: the prefix of every test hook a core honors."""
    return re.sub(r"[^A-Z0-9]", "_", station.upper())


def jsonschema_unavailable(prefix, environ=None):
    environ = os.environ if environ is None else environ
    if environ.get(prefix + "_TEST") == "1" and environ.get(prefix + "_TEST_NO_JSONSCHEMA") == "1":
        return True
    return _Validator is None


def require_jsonschema(prefix, environ=None):
    """The Draft 2020-12 validator class, or exit 3 with the one-line message on stderr."""
    if jsonschema_unavailable(prefix, environ):
        sys.stderr.write(MISSING_DEPENDENCY + "\n")
        sys.stderr.flush()
        sys.exit(3)
    return _Validator


def skill_root(explicit=None):
    """The directory holding SKILL.md: given explicitly, else two levels above this package."""
    if explicit:
        path = os.path.abspath(explicit)
        if not os.path.isdir(path):
            raise SkillRootMissing("--skill-root is not a directory: %s" % path)
        return path
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def references_dir(root=None):
    return os.path.join(skill_root(root), "references")


def plugin_version(root=None):
    """The build, from `.claude-plugin/plugin.json` above the skill root."""
    plugin = os.path.dirname(os.path.dirname(skill_root(root)))
    try:
        with open(os.path.join(plugin, ".claude-plugin", "plugin.json"), "rb") as fh:
            return json.loads(fh.read().decode("utf-8")).get("version") or "unknown"
    except (OSError, ValueError):
        return "unknown"


def load_schema(name, prefix, root=None, environ=None):
    """One schema by name. A missing or unparsable schema is a reference failure, not a default."""
    require_jsonschema(prefix, environ)
    path = os.path.join(references_dir(root), SCHEMA_FILES[name])
    if not os.path.isfile(path):
        raise ReferenceUnavailable("reference unavailable: references/%s" % SCHEMA_FILES[name])
    try:
        with open(path, "rb") as fh:
            schema = json.loads(fh.read().decode("utf-8"))
    except ValueError as exc:
        raise ReferenceUnavailable("reference unavailable: references/%s (%s)" % (SCHEMA_FILES[name], exc))
    if not isinstance(schema, dict):
        raise ReferenceUnavailable("reference unavailable: references/%s (not an object)" % SCHEMA_FILES[name])
    return schema


def _restore_path(error):
    """jsonschema 4.25.1 reports a `"<key>": false` rule at the PARENT path with a truncated schema
    path (guide finding L58), so the forbidden key is put back on the pointer here."""
    pointer = "/" + "/".join(str(p) for p in error.absolute_path)
    schema_path = list(error.absolute_schema_path)
    if schema_path and schema_path[-1] is False:
        schema_path = schema_path[:-1]
    if len(schema_path) >= 2 and schema_path[-2] == "properties":
        key = str(schema_path[-1])
        if not pointer.endswith("/" + key):
            pointer = pointer.rstrip("/") + "/" + key
    return pointer if pointer != "" else "/"


def errors_for(document, schema, prefix="STATION"):
    """[{path, message}] for every schema finding, sorted by path; [] when it validates."""
    validator_class = require_jsonschema(prefix)
    validator = validator_class(schema, format_checker=_FormatChecker())
    out = []
    for error in validator.iter_errors(document):
        out.append({"path": _restore_path(error), "message": error.message})
    out.sort(key=lambda row: (row["path"], row["message"]))
    return out


def _under(path, run_dir):
    if not isinstance(path, str) or not isinstance(run_dir, str) or not run_dir:
        return False
    a = os.path.normpath(path)
    b = os.path.normpath(run_dir)
    return a == b or a.startswith(b.rstrip(os.sep) + os.sep)


def semantic(result):
    """[{id, path, message}] for every semantic check a result fails (S1 to S4)."""
    out = []
    if not isinstance(result, dict):
        return [{"id": "S1", "path": "/", "message": "the result is not an object"}]
    status = result.get("status")
    tag = result.get("stop_tag")
    if status == "stopped" and (not tag or not result.get("reason")):
        out.append({"id": "S1", "path": "/stop_tag", "message": "a stop carries a tag and a reason"})
    if status == "completed" and tag:
        out.append({"id": "S1", "path": "/stop_tag", "message": "a completion carries no stop tag"})
    run_dir = result.get("run_dir")
    writes = [w for w in (result.get("writes") or []) if isinstance(w, dict)]
    outside = [w for w in writes if not _under(w.get("path"), run_dir)]
    if result.get("report_only") and (outside or result.get("wrote_nothing") is not True):
        out.append({"id": "S2", "path": "/writes",
                    "message": "a report-only run writes nothing outside the run directory and says so"})
    if bool(result.get("wrote_nothing")) != (not outside):
        out.append({"id": "S3", "path": "/wrote_nothing",
                    "message": "wrote_nothing is true exactly when no write lies outside the run directory"})
    for index, write in enumerate(writes):
        under = _under(write.get("path"), run_dir)
        if under != (write.get("kind") == "run_artifact"):
            out.append({"id": "S4", "path": "/writes/%d" % index,
                        "message": "a write under the run directory is a run_artifact, and only such a write is"})
    return out
