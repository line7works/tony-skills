"""Schema loading and event validation (records E12 contract sections 6, 12.3; E12-7).

Schemas are loaded from the component root (the directory holding `scripts/` and
`references/`), resolved from this package's own location (scripts/records_core -> scripts ->
component root) unless a root is given explicitly. Never from a repo checkout or a plugin cache.

jsonschema is the one declared dependency (jsonschema==4.25.1 through `uv run`, the pin in force
in the pilot's `recheck.py` PEP 723 block). It is imported lazily: `require_jsonschema()` exits 3
with the pilot's message on stderr and nothing on stdout when it cannot be imported. The test
hook RECORDS_TEST_NO_JSONSCHEMA=1, honored only together with RECORDS_TEST=1, makes it behave as
if the import had failed.

`validate_event` returns `[{"path", "message"}]`: the schema's findings plus the two checks a
Draft 2020-12 schema cannot make on its own, both of them section 6 rules - a native event's `at`
must be a real calendar instant (the `date-time` format goes unchecked without
`rfc3339-validator`, so the date part is parsed here), and a claim, scenario, `how`, or `words`
field must be a single line with no ` · ` in it (Appendix A's single-line fields), with the one
exception `SEPARATOR_KEPT_ON_LEGACY` names and explains.

`known_version` is the E12-7 gate: a reader refuses an event whose `v` it does not know (exit 4,
naming the line) instead of skipping it.

Slice 2 adds the other three schemas of section 1 (`state`, `import_report`, `resolutions`) to
the same loader; `validate_document(key, doc, schemas)` checks any of them and returns the same
`[{"path", "message"}]` shape. The resolutions file is the one of the three that is an INPUT: it
is checked before the importer reads a single answer, so a malformed file is exit 4 and nothing
is written.
"""
import datetime
import json
import os
import re
import sys

MISSING_DEPENDENCY = "missing dependency: jsonschema==4.25.1 (run through uv run, or install it)"
SCHEMA_FILES = {
    "event": "event.schema.json",
    "state": "state.schema.json",
    "import_report": "import-report.schema.json",
    "resolutions": "resolutions.schema.json",
}
KNOWN_VERSIONS = (1,)
SEP = " · "  # Appendix A's field separator; never inside a single-line field
SINGLE_LINE_FIELDS = ("claim", "scenario", "how", "words", "raised_by")
SEPARATOR_KEPT_ON_LEGACY = ("scenario",)
"""The one field a LEGACY event may carry the separator in (records E12 contract section 11.3).

Appendix A's single-line rule governs what the core WRITES: "The core writes claims, failure
scenarios, and quoted words as single lines: the input schema rejects a carriage return or line
feed anywhere in them and the separator `·` inside them." Section 11.3 then tells the importer
to read a review finding of more than five fields by taking "fields 1 to 4 ... the last field is
`raised_by`; anything between joins the scenario WITH THE SEPARATOR KEPT" (family F2, 64 lines
of the measured corpus). Both stand only if the separator rule holds for what this component
writes natively and not for what a legacy line already said. A claim keeps the rule in every
case, because Appendix A calls a claim containing the separator ambiguous, and the tolerant
reader records such a line as `legacy_unparsed` rather than as a finding. A line break is
refused everywhere: a record is one line of a document, so a legacy field cannot hold one."""
RFC3339_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?Z$")

try:  # the guarded import: a missing jsonschema is reported once, at the first use
    from jsonschema import Draft202012Validator as _Validator, FormatChecker as _FormatChecker
except ImportError:  # pragma: no cover - exercised by the exit-3 tests through a subprocess
    _Validator = None
    _FormatChecker = None


class ReferenceUnavailable(RuntimeError):
    """A schema under the component root is missing, unreadable, or not a schema."""

    def __init__(self, relative_path, cause):
        RuntimeError.__init__(self, "reference unavailable: %s (%s)" % (relative_path, cause))
        self.relative_path = relative_path


class ComponentRootMissing(ValueError):
    """An explicit --component-root that is not a directory: a usage error (exit 2), never exit 1."""


def jsonschema_unavailable():
    """True when jsonschema did not import, or the gated test hook says to act as if it had not."""
    hooked = os.environ.get("RECORDS_TEST") == "1" and os.environ.get("RECORDS_TEST_NO_JSONSCHEMA") == "1"
    return _Validator is None or hooked


def require_jsonschema():
    """Return the Draft 2020-12 validator class, or exit 3 with the pilot's message."""
    if jsonschema_unavailable():
        sys.stderr.write(MISSING_DEPENDENCY + "\n")
        sys.stderr.flush()
        sys.exit(3)
    return _Validator


def component_root(explicit=None):
    """The component root: given explicitly, else two levels above this file."""
    if explicit:
        path = os.path.abspath(explicit)
        if not os.path.isdir(path):
            raise ComponentRootMissing("--component-root is not a directory: %s" % path)
        return path
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def references_dir(root=None):
    return os.path.join(component_root(root), "references")


def _read_json(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


class Schemas:
    """The component's schema documents and their validators, loaded from one component root."""

    def __init__(self, root=None):
        V = require_jsonschema()
        self.root = component_root(root)
        self.docs = {}
        for key, name in SCHEMA_FILES.items():
            rel = os.path.join("references", name)
            path = os.path.join(self.root, rel)
            try:
                self.docs[key] = _read_json(path)
            except (OSError, ValueError) as exc:
                raise ReferenceUnavailable(rel, exc)
            try:
                V.check_schema(self.docs[key])
            except Exception as exc:  # noqa: BLE001 - a file that parses but is not a schema is the same stop
                raise ReferenceUnavailable(rel, "not a valid schema: %s" % exc)
        fc = format_checker()
        self.validators = dict((key, V(doc, format_checker=fc)) for key, doc in self.docs.items())
        self.event = self.validators["event"]


def format_checker():
    """A fresh jsonschema FormatChecker (E8-A34); require_jsonschema() has run by then."""
    return _FormatChecker()


_CACHE = {}


def load_schemas(root=None):
    key = component_root(root)
    if key not in _CACHE:
        _CACHE[key] = Schemas(key)
    return _CACHE[key]


def _pointer(parts):
    return "/" + "/".join(str(p) for p in parts) if parts else ""


def _walk(doc, parts):
    cur = doc
    for p in parts:
        cur = cur[p]
    return cur


def _error_path(err, doc):
    """The instance path of an error, with the segment jsonschema drops for a `false` schema restored.

    jsonschema 4.25.1's `descend()` yields the error for a `false` subschema before it appends the
    property name, so a rule such as `"claim": false` reports at the parent. The offending value is
    the error's instance object; find it in its parent by identity and append its key (the pilot's
    `recheck_core/validate._error_path`, same defect, same repair).
    """
    parts = list(err.absolute_path)
    if not (err.validator is None and err.schema is False):
        return parts
    try:
        parent = _walk(doc, parts)
    except (KeyError, IndexError, TypeError):
        return parts
    if isinstance(parent, dict):
        hits = [k for k, v in parent.items() if v is err.instance]
    elif isinstance(parent, list):
        hits = [i for i, v in enumerate(parent) if v is err.instance]
    else:
        hits = []
    if len(hits) == 1:
        parts.append(hits[0])
    return parts


def _errors(validator, doc):
    out = [{"path": _pointer(_error_path(err, doc)), "message": err.message} for err in validator.iter_errors(doc)]
    out.sort(key=lambda e: (e["path"], e["message"]))
    return out


def known_version(event):
    """E12-7: is this event's `v` one this reader knows?"""
    return isinstance(event, dict) and event.get("v") in KNOWN_VERSIONS


def unknown_version_error(event):
    return {"path": "/v", "message": "unknown event version %r; this reader knows %s (E12-7)"
                                     % (event.get("v") if isinstance(event, dict) else None,
                                        ", ".join(str(v) for v in KNOWN_VERSIONS))}


def _semantic_errors(event):
    """The two section 6 rules a Draft 2020-12 schema cannot make on its own."""
    out = []
    at = event.get("at")
    origin = event.get("origin")
    native = not (isinstance(origin, dict) and origin.get("kind") == "legacy")
    if native and isinstance(at, str):
        m = RFC3339_RE.match(at)
        if m is not None:
            try:
                datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                if not (int(m.group(4)) < 24 and int(m.group(5)) < 60 and int(m.group(6)) < 61):
                    raise ValueError("time out of range")
            except ValueError as exc:
                out.append({"path": "/at", "message": "%s is not a real instant: %s" % (at, exc)})
    for field in SINGLE_LINE_FIELDS:
        value = event.get(field)
        if not isinstance(value, str):
            continue
        if "\n" in value or "\r" in value:
            out.append({"path": "/" + field, "message": "a %s is a single line (Appendix A)" % field})
        if SEP in value and (native or field not in SEPARATOR_KEPT_ON_LEGACY):
            out.append({"path": "/" + field, "message": "a %s never contains the field separator %r (Appendix A)" % (field, SEP)})
    out.sort(key=lambda e: (e["path"], e["message"]))
    return out


def validate_event(event, schemas):
    """[{"path", "message"}] for one event: the unknown-version gate, the schema, then the two
    semantic rules. An unknown `v` is reported alone, because no schema of this component
    describes that event."""
    if not isinstance(event, dict):
        return [{"path": "", "message": "an event is a JSON object, not %s" % type(event).__name__}]
    if not known_version(event):
        return [unknown_version_error(event)]
    return _errors(schemas.event, event) + _semantic_errors(event)


def validate_document(key, doc, schemas):
    """`[{"path", "message"}]` for any of this component's schemas but the event's.

    The event has its own entry point (`validate_event`) because it carries the E12-7 version
    gate and the two semantic rules a Draft 2020-12 schema cannot make; the other three are plain
    schema checks.
    """
    if key == "event":
        return validate_event(doc, schemas)
    validator = schemas.validators.get(key)
    if validator is None:
        raise ReferenceUnavailable(SCHEMA_FILES.get(key, key), "no such schema")
    return _errors(validator, doc)
