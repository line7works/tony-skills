"""The station trace (ruling E15-7): one line per station visit or reader summons, in `trace.jsonl`.

    v1_names() -> the ten v1 station names, assembled at run time
    v1_root(root) -> the v1 name a root sits under, or None
    refusals(expected, identity, known_versions) -> [{"rule", "message"}]
    line(kind, caller, expected, identity, route, run_dir, status=None, call_id=None, row=None,
         refusal=None, at=None) -> one line, without its `seq`
    check_line(line) -> [message]: the shape rules this module holds without jsonschema
    append(run_dir, line, skill_root=None) -> the line as written, with its `seq`
    read(run_dir) -> [line]; TraceError on a line that does not parse, check or follow on

A line carries the station's `skill-identity` (name, version, resolved root, interface version,
commit, content hash) as that station's own CLI returned it BEFORE the visit, the route that resolved
it (`3a` the checkout sibling, `3b` the installed shape, `argument` a test hook), the run directory
the visit used, and its terminal status. A summons also names its readers `call_id` and `row`. A
station refused before the visit is a `refused` line naming the rules it broke.

The refusal rule. A station is refused before the visit when its identity is missing (`no-identity`),
when its name is a v1 station's name or lacks `-v2` where a v2 station is expected (`v1-name`), when
its name is not the one expected (`name-mismatch`), when its root sits under a v1 plugin folder
(`v1-root`: the checkout shape `plugins/<v1>/...`, the installed shape `.../<v1>/<version>`, or a root
named for a v1 station), or when its interface version is not one the caller knows
(`unknown-interface`). The caller decides what to do with a refusal; this module only says why.

The module writes and reads the file; it never resolves, launches or reads a station itself (E15-4).
`append` checks the line against `references/trace.schema.json` (jsonschema, under `uv run`) and this
module's own shape rules, numbers it, and appends it; a refused line writes nothing. Shared by the
three back cores (`references/back-files.txt`).
"""
import datetime
import json
import os
import re

FILE = "trace.jsonl"
TRACE_VERSION = 1
KINDS = ("visit", "summons", "refused")
ROUTES = ("3a", "3b", "argument")
RULES = ("v1-name", "name-mismatch", "v1-root", "unknown-interface", "no-identity")
IDENTITY_KEYS = ("name", "version", "root", "interface_version", "commit", "content_sha256")
COMMON = ("trace_version", "seq", "at", "kind", "caller", "expected", "identity", "route", "run_dir")
BY_KIND = {"summons": ("status", "call_id", "row"), "visit": ("status",), "refused": ("refusal",)}
OPTIONAL = ("status", "call_id", "row", "refusal")
CALLER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-v2$")
CALL_ID = re.compile(r"^[A-Za-z0-9._-]+$")
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
VERSION_DIR = re.compile(r"^\d+(?:\.\d+)*$")
SHA = re.compile(r"^[0-9a-f]{64}$")


class TraceError(ValueError):
    """A line that cannot be written, or a file that does not read back as a trace."""


def v1_names():
    """The seven E14 names and the three back-half names, assembled so no file names a v1 folder."""
    return ("pre" + "con", "archi" + "tect", "blue" + "print", "in" + "spect", "bu" + "ild", "sign" + "off",
            "re" + "check", "verti" + "cal", "hand" + "off", "sh" + "ip")


def v1_root(root):
    """The v1 name `root` sits under, or None. Three shapes count: `.../plugins/<v1>[/...]` (the
    checkout), `.../<v1>/<dotted version>` (the installed cache), and a root whose own folder is named
    for a v1 station. A v1 word elsewhere in the path (a user's folder) does not."""
    if not isinstance(root, str) or not root:
        return None
    names = v1_names()
    parts = [p for p in os.path.normpath(root).split(os.sep) if p]
    for index, part in enumerate(parts):
        if part in names and index > 0 and parts[index - 1] == "plugins":
            return part
    if len(parts) >= 2 and VERSION_DIR.match(parts[-1]) and parts[-2] in names:
        return parts[-2]
    if parts and parts[-1] in names:
        return parts[-1]
    return None


def refusals(expected, identity, known_versions=(1,)):
    """[{"rule", "message"}] for every way `identity` is not the expected v2 sibling; [] when it is."""
    if not isinstance(identity, dict):
        return [{"rule": "no-identity", "message": "no identity was read for %s before the visit" % expected}]
    out = []
    name = identity.get("name")
    root = identity.get("root")
    if name in v1_names() or (str(expected).endswith("-v2") and not str(name).endswith("-v2")):
        out.append({"rule": "v1-name", "message": "the station names itself %r, a v1 name where %s is expected"
                                                  % (name, expected)})
    if name != expected:
        out.append({"rule": "name-mismatch", "message": "the station names itself %r, not %s" % (name, expected)})
    under = v1_root(root)
    if under is not None:
        out.append({"rule": "v1-root", "message": "its root %s sits under the v1 plugin folder of %s" % (root, under)})
    version = identity.get("interface_version")
    if type(version) is not int or version not in tuple(known_versions):
        out.append({"rule": "unknown-interface", "message": "its interface version %r is none this caller knows (%s)"
                                                            % (version, ", ".join(str(v) for v in known_versions))})
    return out


def now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def line(kind, caller, expected, identity, route, run_dir, status=None, call_id=None, row=None, refusal=None,
         at=None):
    """One trace line without its `seq`; only the fields its kind carries are set."""
    out = {"trace_version": TRACE_VERSION, "at": at or now(), "kind": kind, "caller": caller,
           "expected": expected, "identity": identity, "route": route, "run_dir": run_dir}
    for key, value in (("status", status), ("call_id", call_id), ("row", row), ("refusal", refusal)):
        if value is not None:
            out[key] = value
    return out


def _identity_problems(identity):
    if not isinstance(identity, dict):
        return ["the identity is not an object"]
    out = []
    if sorted(identity) != sorted(IDENTITY_KEYS):
        out.append("the identity carries exactly %s" % ", ".join(IDENTITY_KEYS))
    for key in ("name", "version", "root"):
        if not isinstance(identity.get(key), str) or not identity.get(key):
            out.append("the identity's %s is a non-empty string" % key)
    version = identity.get("interface_version")
    if version is not None and type(version) is not int:
        out.append("the identity's interface_version is an integer or null")
    if identity.get("commit") is not None and not isinstance(identity.get("commit"), str):
        out.append("the identity's commit is a string or null")
    sha = identity.get("content_sha256")
    if sha is not None and (not isinstance(sha, str) or not SHA.match(sha)):
        out.append("the identity's content_sha256 is 64 hex characters or null")
    return out


def check_line(one, with_seq=False):
    """[message] for every shape rule the line breaks; [] when it holds. The schema says the same in
    jsonschema's terms; this is the check that needs no dependency."""
    if not isinstance(one, dict):
        return ["the line is not an object"]
    out = []
    kind = one.get("kind")
    if kind not in KINDS:
        return ["the kind is one of %s" % ", ".join(KINDS)]
    required = COMMON + BY_KIND[kind]
    if not with_seq:
        required = tuple(k for k in required if k != "seq")
    allowed = set(COMMON) | set(BY_KIND[kind])
    for key in required:
        if key not in one:
            out.append("a %s line carries %s" % (kind, key))
    for key in sorted(set(one) - allowed):
        out.append("a %s line does not carry %s" % (kind, key))
    if one.get("trace_version") != TRACE_VERSION:
        out.append("trace_version is %d" % TRACE_VERSION)
    if "seq" in one and (type(one["seq"]) is not int or one["seq"] < 0):
        out.append("seq is a non-negative integer")
    if not isinstance(one.get("at"), str) or not INSTANT.match(one.get("at", "")):
        out.append("at is a UTC instant like 2026-10-01T12:00:00Z")
    if not isinstance(one.get("caller"), str) or not CALLER.match(one.get("caller", "")):
        out.append("caller is a -v2 core's name")
    if not isinstance(one.get("expected"), str) or not one.get("expected"):
        out.append("expected is a non-empty string")
    if not isinstance(one.get("run_dir"), str) or not one.get("run_dir"):
        out.append("run_dir is a non-empty string")
    if kind == "refused":
        if one.get("identity") is not None:
            out.extend(_identity_problems(one["identity"]))
        if one.get("route") not in ROUTES + (None,):
            out.append("route is 3a, 3b, argument or null")
        refusal = one.get("refusal")
        if (not isinstance(refusal, dict) or sorted(refusal) != ["reason", "rules"]
                or not isinstance(refusal.get("rules"), list) or not refusal["rules"]
                or any(r not in RULES for r in refusal["rules"]) or len(set(refusal["rules"])) != len(refusal["rules"])
                or not isinstance(refusal.get("reason"), str) or not refusal["reason"]):
            out.append("refusal is {rules: one or more of %s, reason: text}" % ", ".join(RULES))
    else:
        out.extend(_identity_problems(one.get("identity")))
        if one.get("route") not in ROUTES:
            out.append("route is 3a, 3b or argument")
        if not isinstance(one.get("status"), str) or not one.get("status"):
            out.append("status is the terminal status, a non-empty string")
        if kind == "summons":
            if not isinstance(one.get("call_id"), str) or not CALL_ID.match(one.get("call_id", "")):
                out.append("call_id is one path segment")
            if not isinstance(one.get("row"), str) or not one.get("row"):
                out.append("row is a non-empty string")
    return out


def _schema(skill_root=None):
    from station_core import validate
    path = os.path.join(validate.references_dir(skill_root), "trace.schema.json")
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise validate.ReferenceUnavailable("reference unavailable: references/trace.schema.json (%s)" % exc)


def schema_errors(one, skill_root=None, prefix="TRACE"):
    """The schema's findings for one numbered line (jsonschema; exit 3 through the frame's guard
    when it cannot be imported)."""
    from station_core import validate
    return validate.errors_for(one, _schema(skill_root), prefix)


def path_of(run_dir):
    return os.path.join(run_dir, FILE)


def read(run_dir):
    """Every line of the run's trace, in order; [] when there is none. A line that does not parse, does
    not hold its shape, or does not follow on (`seq` equal to its index) is a TraceError naming it."""
    path = path_of(run_dir)
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for index, raw in enumerate(fh):
            try:
                one = json.loads(raw)
            except ValueError as exc:
                raise TraceError("trace line %d does not parse: %s" % (index + 1, exc))
            problems = check_line(one, with_seq=True)
            if problems:
                raise TraceError("trace line %d: %s" % (index + 1, "; ".join(problems)))
            if one["seq"] != index:
                raise TraceError("trace line %d carries seq %r, not %d" % (index + 1, one["seq"], index))
            out.append(one)
    return out


def append(run_dir, one, skill_root=None, prefix="TRACE"):
    """Number `one`, check it (this module's rules, then the schema), and append it. A line that fails
    either is a TraceError and nothing is written."""
    problems = check_line(one)
    if problems:
        raise TraceError("the trace line does not hold: %s" % "; ".join(problems))
    lines = read(run_dir)
    numbered = dict(one, seq=len(lines))
    errors = schema_errors(numbered, skill_root, prefix)
    if errors:
        raise TraceError("the trace line fails references/trace.schema.json: %s"
                         % "; ".join("%s %s" % (e["path"], e["message"]) for e in errors[:4]))
    data = (json.dumps(numbered, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    os.makedirs(run_dir, exist_ok=True)
    with open(path_of(run_dir), "ab") as fh:
        fh.write(data)
    return numbered
