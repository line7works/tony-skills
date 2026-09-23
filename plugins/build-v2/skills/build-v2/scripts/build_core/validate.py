"""Schema loading and validation, and the semantic checks a schema cannot make.

Schemas are loaded from the skill root (the directory holding SKILL.md), resolved from this
package's own location (`scripts/build_core` -> `scripts` -> the skill root) unless a root is
given; never from a checkout path and never from a plugin cache. A reference that is missing or
does not parse stops the run rather than being worked around.

`jsonschema==4.25.1` is the one declared dependency, supplied by `uv run` through `build.py`'s
PEP 723 block. It is imported lazily: `require_jsonschema()` writes the pilot's one-line message
to stderr and exits 3 with nothing on stdout when it cannot be imported, so `--help` and every
argument check still work without it.

The semantic checks (`run_semantic`) close what the result schema cannot say:

    V1  the card moved only when the answer claimed complete, every named check passed, and no
        path was out of scope without a reason
    V2  `status` and `terminal_status` agree; every stop (`stopped` and `answer_refused`) carries
        a reason, and a `stopped` result carries a tag
    V3  every out-of-scope path is in the source set and outside the slice's named paths, and
        every source-set path outside them that is not sanctioned is listed
    V4  every named check of the contract has exactly one row in `checks`
    V5  every write is an authorized destination: a run artifact under the run directory, the
        build doc, or the log the component reports. Nothing else is authorized.
    V6  a report-only run lists no write outside the run directory, says `wrote_nothing`, and
        appended no event
    V7  a refused answer moved no card and appended no event
    V8  `records.appended` agrees with `records.wrote`, and a refusal carries no appended event
    V9  a check reported `failing` or `not_run` and a status of `completed` cannot both stand
    V10 the identity is present exactly when a card event was appended (the event carries it)
    V11 a named check this core could not run (`rerun_refused`) or could not attribute to its own
        command (`attribution_refused`) is `not_run`, never a result; a report-only run reran
        nothing; and a run whose check reruns changed the workspace never says `wrote_nothing`
        (Astra's F2 and F15)
"""
import json
import os
import sys

MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"
TEST_FLAG = "BUILD_TEST"
NO_JSONSCHEMA_HOOK = "BUILD_TEST_NO_JSONSCHEMA"

try:  # the guarded import: a missing jsonschema is reported once, at the first use
    from jsonschema import Draft202012Validator as _Validator, FormatChecker as _FormatChecker
except ImportError:  # pragma: no cover - exercised through a subprocess by the exit-3 tests
    _Validator = None
    _FormatChecker = None

SCHEMA_FILES = {
    "input": "input.schema.json",
    "answer": "answer.schema.json",
    "result": "result.schema.json",
    "receipt": "receipt.schema.json",
    "checkpoint": "checkpoint.schema.json",
}

CHECK_IDS = ["V%d" % i for i in range(1, 12)]


class ReferenceUnavailable(RuntimeError):
    """A schema under the skill root is missing, unreadable, or not a schema."""


class SkillRootMissing(RuntimeError):
    """An explicit `--skill-root` that is not a directory: a usage slip."""


def jsonschema_unavailable(environ=None):
    environ = os.environ if environ is None else environ
    if environ.get(TEST_FLAG) == "1" and environ.get(NO_JSONSCHEMA_HOOK) == "1":
        return True
    return _Validator is None


def require_jsonschema(environ=None):
    """The Draft 2020-12 validator class, or exit 3 with the one-line message on stderr."""
    if jsonschema_unavailable(environ):
        sys.stderr.write(MISSING_DEPENDENCY + "\n")
        sys.stderr.flush()
        sys.exit(3)
    return _Validator


def skill_root(explicit=None):
    """The directory holding SKILL.md: given explicitly, else two levels above this file."""
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
    manifest = os.path.join(plugin, ".claude-plugin", "plugin.json")
    try:
        with open(manifest, "rb") as fh:
            return json.loads(fh.read().decode("utf-8")).get("version") or "unknown"
    except (OSError, ValueError):
        return "unknown"


def load_schema(name, root=None, environ=None):
    """One schema by name. A missing or unparsable schema is a reference failure, not a default."""
    require_jsonschema(environ)
    path = os.path.join(references_dir(root), SCHEMA_FILES[name])
    if not os.path.isfile(path):
        raise ReferenceUnavailable("reference unavailable: references/%s" % SCHEMA_FILES[name])
    try:
        with open(path, "rb") as fh:
            schema = json.loads(fh.read().decode("utf-8"))
    except ValueError as exc:
        raise ReferenceUnavailable("reference unavailable: references/%s (%s)"
                                   % (SCHEMA_FILES[name], exc))
    if not isinstance(schema, dict):
        raise ReferenceUnavailable("reference unavailable: references/%s (not an object)"
                                   % SCHEMA_FILES[name])
    return schema


def load_schemas(root=None, environ=None):
    return dict((name, load_schema(name, root, environ)) for name in SCHEMA_FILES)


def _restore_path(error):
    """jsonschema 4.25.1 reports a `"<key>": false` rule at the PARENT path with a truncated
    schema path (guide finding L58), so the forbidden key is put back on the pointer here."""
    pointer = "/" + "/".join(str(p) for p in error.absolute_path)
    schema_path = list(error.absolute_schema_path)
    if schema_path and schema_path[-1] is False:
        schema_path = schema_path[:-1]
    if len(schema_path) >= 2 and schema_path[-2] == "properties":
        key = str(schema_path[-1])
        if not pointer.endswith("/" + key):
            pointer = (pointer.rstrip("/") + "/" + key)
    return pointer or "/"


def errors_for(document, schema, environ=None):
    """[{path, message}] in path order; empty when the document validates."""
    validator_class = require_jsonschema(environ)
    validator = validator_class(schema, format_checker=_FormatChecker())
    out = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        out.append({"path": _restore_path(error), "message": error.message})
    return out


# ---- the semantic checks ---------------------------------------------------------------------

def _finding(check_id, path, message):
    return {"id": check_id, "path": path, "message": message}


def run_semantic(result, input_doc=None, run_dir=None):
    """The checks the schema cannot make. Returns {"semantic": [...], "skipped": [...]}

    Never raises on a malformed document. These checks run over results this core did not write
    — `validate-result.py` takes any file — so a shape the schema would have refused reaches them
    too, and a crash here would be a validator that cannot say what is wrong with its input. Each
    check reads defensively and reports what it can.
    """
    findings = []
    skipped = []
    status = result.get("status")
    terminal = result.get("terminal_status")
    card = result.get("card") if isinstance(result.get("card"), dict) else {}
    checks = result.get("checks") or []
    source = result.get("source_set") if isinstance(result.get("source_set"), dict) else {}
    contract = result.get("contract") if isinstance(result.get("contract"), dict) else {}
    records = result.get("records") if isinstance(result.get("records"), dict) else {}
    answer = result.get("answer") if isinstance(result.get("answer"), dict) else {}

    checks = [row for row in checks if isinstance(row, dict)]
    named_checks = [row for row in checks if row.get("named_by_slice")]
    not_passed = [row for row in named_checks if row.get("result") != "passed"]
    out_rows = [row for row in (result.get("out_of_scope") or []) if isinstance(row, dict)]
    unexplained = [row for row in out_rows if not row.get("reason_given")]

    # V1: the card moves only on the three conditions together
    if card.get("moved"):
        if answer.get("claimed_status") != "complete":
            findings.append(_finding("V1", "/card/moved",
                                     "the card moved while the answer claimed %r, not `complete`"
                                     % answer.get("claimed_status")))
        if not_passed:
            findings.append(_finding("V1", "/card/moved",
                                     "the card moved while %d named check(s) did not pass: %s"
                                     % (len(not_passed), ", ".join(r.get("name", "?") for r in not_passed))))
        if unexplained:
            findings.append(_finding("V1", "/card/moved",
                                     "the card moved while %d out-of-scope path(s) carried no reason"
                                     % len(unexplained)))
        if card.get("after") != "built":
            findings.append(_finding("V1", "/card/after",
                                     "a moved card reads %r; this core only ever moves one to `built`"
                                     % card.get("after")))
        if not answer.get("accepted"):
            findings.append(_finding("V1", "/card/moved", "the card moved on an answer this run refused"))

    # V2: the two status fields agree
    if status in ("stopped", "answer_refused"):
        if terminal != "stop":
            findings.append(_finding("V2", "/terminal_status", "%r is a stop" % status))
        if not result.get("stop_reason"):
            findings.append(_finding("V2", "/stop_reason", "a stop carries a reason"))
        if status == "stopped" and not result.get("stop_tag"):
            findings.append(_finding("V2", "/stop_tag", "a `stopped` result carries a tag"))
    elif status is not None:
        if terminal != "completion":
            findings.append(_finding("V2", "/terminal_status",
                                     "%r is a completion, not a stop" % status))
        if result.get("stop_reason"):
            findings.append(_finding("V2", "/stop_reason", "a completion carries no stop reason"))

    # V3: the out-of-scope list is exactly the source-set paths outside the named paths, less
    # the sanctioned ones
    if source and contract and status == "stopped" and not result.get("out_of_scope"):
        skipped.append({"id": "V3",
                        "reason": "skipped: the run stopped before the scope comparison ran"})
    elif source and contract:
        from . import doc as docmod
        names = contract.get("named_paths") or []
        sanctioned = set(row.get("path") for row in (source.get("sanctioned") or [])
                         if isinstance(row, dict))
        every = sorted(set(source.get("committed") or []) | set(source.get("changed") or [])
                       | set(source.get("untracked") or []))
        expected = sorted(p for p in every
                          if p not in sanctioned and not docmod.in_named_paths(p, names))
        listed = sorted(row.get("path") or "" for row in out_rows)
        if listed != expected:
            findings.append(_finding("V3", "/out_of_scope",
                                     "the out-of-scope list is %s; the source-set paths outside the "
                                     "slice's named paths are %s" % (listed, expected)))
    elif not source:
        skipped.append({"id": "V3", "reason": "skipped: the run stopped before a source set existed"})

    # V4: one row per named check, and no named check missing
    if contract and status == "stopped" and not checks:
        skipped.append({"id": "V4", "reason": "skipped: the run stopped before its checks were read"})
    elif contract:
        want = [row.get("name") for row in (contract.get("checks") or [])]
        got = [row.get("name") for row in named_checks]
        if sorted(want) != sorted(got):
            findings.append(_finding("V4", "/checks",
                                     "the slice names %s; the result carries %s as named" % (want, got)))
    else:
        skipped.append({"id": "V4", "reason": "skipped: the run stopped before a contract existed"})

    # V5: every write is authorized
    authorized_run_dir = (input_doc or {}).get("run_dir") or result.get("run_dir") or run_dir
    for entry in result.get("writes") or []:
        if not isinstance(entry, dict):
            findings.append(_finding("V5", "/writes", "a write entry is not an object"))
            continue
        path, kind = entry.get("path") or "", entry.get("kind")
        if kind == "run_artifact":
            if authorized_run_dir and not os.path.realpath(path).startswith(
                    os.path.realpath(authorized_run_dir) + os.sep):
                findings.append(_finding("V5", "/writes", "%s is not inside the run directory" % path))
        elif kind == "status_line":
            if path != result.get("build_doc"):
                findings.append(_finding("V5", "/writes",
                                         "a status-line write targets %s, not the build doc %s"
                                         % (path, result.get("build_doc"))))
        elif kind == "records_log":
            if records.get("log") and path != records["log"]:
                findings.append(_finding("V5", "/writes",
                                         "a log write targets %s, not the log the component reports (%s)"
                                         % (path, records["log"])))
        else:
            findings.append(_finding("V5", "/writes", "%r is not an authorized write kind" % kind))

    # V6: report-only wrote nothing outside the run directory
    if result.get("report_only"):
        outside = [e for e in (result.get("writes") or [])
                   if isinstance(e, dict) and e.get("kind") != "run_artifact"]
        if outside:
            findings.append(_finding("V6", "/writes",
                                     "a report-only run wrote %d file(s) outside the run directory"
                                     % len(outside)))
        if result.get("wrote_nothing") is not True:
            findings.append(_finding("V6", "/wrote_nothing", "a report-only run says it wrote nothing"))
        if records.get("appended"):
            findings.append(_finding("V6", "/records/appended", "a report-only run appends no event"))
        if records.get("wrote"):
            findings.append(_finding("V6", "/records/wrote", "a report-only run writes nothing to the log"))
        if (records.get("levelled") or {}).get("dry_run") is False:
            findings.append(_finding("V6", "/records/levelled/dry_run",
                                     "a report-only run levels the log with a dry run, which takes no lock"))

    # V7: a refused answer changes nothing
    if status == "answer_refused":
        if answer.get("accepted"):
            findings.append(_finding("V7", "/answer/accepted", "a refused answer is not accepted"))
        if not (answer.get("refusals") or []):
            findings.append(_finding("V7", "/answer/refusals", "a refusal says which rule the answer broke"))
        if card.get("moved"):
            findings.append(_finding("V7", "/card/moved", "a refused answer moves no card"))
        if records.get("appended"):
            findings.append(_finding("V7", "/records/appended", "a refused answer appends no event"))
        if not result.get("refusal_reason"):
            findings.append(_finding("V7", "/refusal_reason", "a refused answer carries its tag"))

    # V8: the log's own bookkeeping
    appended = [row for row in (records.get("appended") or []) if isinstance(row, dict)]
    if appended and not records.get("wrote"):
        findings.append(_finding("V8", "/records/wrote", "events were appended but `wrote` is false"))
    if records.get("refused") and appended:
        findings.append(_finding("V8", "/records/appended",
                                 "a refusal the component returned appended nothing"))
    if len(appended) > 1:
        findings.append(_finding("V8", "/records/appended",
                                 "a build run records one card event at most; this one records %d"
                                 % len(appended)))
    for entry in appended:
        if entry.get("kind") != "card_set":
            findings.append(_finding("V8", "/records/appended",
                                     "build raises nothing and clears nothing; %r is not a card event"
                                     % entry.get("kind")))

    # V9: an honest failure is never a `completed`
    if status == "completed" and not_passed:
        findings.append(_finding("V9", "/status",
                                 "%d named check(s) did not pass, so the run is `checks_not_passed`"
                                 % len(not_passed)))
    if status == "checks_not_passed" and not not_passed:
        findings.append(_finding("V9", "/status", "no named check is failing or not run"))

    # V10: the identity is there exactly when an event carries it
    if appended and not result.get("identity"):
        findings.append(_finding("V10", "/identity",
                                 "a card event carries the six-field identity, so the result reports it"))

    # V11: a check this core could not run or attribute is `not_run`, and child writes are writes
    for index, row in enumerate(checks):
        where = "/checks/%d/result" % index
        if row.get("rerun_refused") and row.get("source") == "rerun" \
                and row.get("result") != "not_run":
            findings.append(_finding("V11", where,
                                     "the rerun of %r could not execute (%s), so it is `not_run`, "
                                     "not %r" % (row.get("name"), row.get("rerun_refused"),
                                                 row.get("result"))))
        if row.get("attribution_refused") and row.get("result") != "not_run":
            findings.append(_finding("V11", where,
                                     "the answer ran another command under %r, so its output is "
                                     "not this check's and the check is `not_run`, not %r"
                                     % (row.get("name"), row.get("result"))))
        if result.get("report_only") and row.get("source") == "rerun" \
                and row.get("result") != "not_run":
            findings.append(_finding("V11", where,
                                     "a report-only run runs no check command in the live "
                                     "workspace, so %r cannot carry an observed result"
                                     % row.get("name")))
    if result.get("checks_changed_workspace") and result.get("wrote_nothing"):
        findings.append(_finding("V11", "/wrote_nothing",
                                 "a check this core reran changed the workspace, so the run did "
                                 "not write nothing"))

    return {"semantic": findings, "skipped": skipped}
