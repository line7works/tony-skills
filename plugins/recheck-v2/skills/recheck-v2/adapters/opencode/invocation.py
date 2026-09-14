#!/usr/bin/env python3
"""The invocation facts for the OpenCode adapter (recheck-v2, E9 lane Q).

Prints the object the executor copies under ``invocation`` in the input document:
``run_id``, ``run_dir``, ``harness``, ``model``, ``run_date``, ``session_wrote_fix`` and
``turn_attribution`` and nothing else, so the result validates against
``references/input.schema.json`` (``invocation`` is a closed object). The executor still adds
``mode``, ``caller`` and ``resume`` itself.

Every value is a fact read from a harness record or a harness command, or a flag the profile
names as instruction-bound. This helper composes no model id, no version, no attribution and
no ``floor_met``. How each field was obtained is written to stderr.

Arguments
---------
--workspace DIR        the repo root under test (default: the current working directory).
                       Used to resolve the session when nothing else does.
--target-token T       the slice or target token in the run id (default ``run``).
--session-wrote-fix    report ``session_wrote_fix`` true (E9-14: the executor's honest
                       answer about its own session; default false, never guessed).
--run-date YYYY-MM-DD  pin the run date (default: the machine's local calendar date).
--caller NAME          a caller route: keep the caller's ids. Requires --run-id and --run-dir.
--run-id ID            the caller's run id.
--run-dir DIR          the caller's absolute run directory.
--floor CLASS          the capability class to assert against (default ``opus``, the
                       contract's ``policy.model_floor`` default).
--session ID           use this session id instead of resolving one.
--setup DIR            the isolated pilot setup (default $RECHECK_OPENCODE_SETUP, else
                       ~/.local/share/skills-v2-pilot/opencode).
--opencode PATH        the opencode binary (default: $OPENCODE_BIN, else the setup's own,
                       else ``opencode`` on PATH).
--help                 this text.

The floor map (E9 lane contract ruling E9-3, **provisional for the pilot**: the control room
made it because ruling D3a fixes these two models and an unclassified id would stop every
graded run; Tony confirms or overturns it):

===========================  =========  =========
model id                     class      floor_met
===========================  =========  =========
qwen/qwen3.8-flash           opus       true
deepseek/deepseek-v4.1-flash opus       true
anything else                unknown    null
===========================  =========  =========

Example::

    python3 invocation.py --workspace /Users/x/Developer/widget --target-token A

prints ``{"run_id": "recheck-a-20260920-4f1c", "run_dir": "/tmp/recheck-v2/recheck-a-...",
"harness": {"name": "opencode", "version": "1.18.31", "entry": "...", "sandbox": "..."},
"model": {"id": "qwen/qwen3.8-flash", "floor_class": "opus", "floor_met": true, ...},
"run_date": "2026-09-20", "session_wrote_fix": false, "turn_attribution": {...}}``.

Exit status: 0 success; 2 a usage slip; 3 a record or binary this helper needs is absent (the
session store, a session for the workspace, the opencode binary); 1 anything else.
Side effects: none. It creates no run directory: ``recheck.py start`` does that.
"""

import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import turns as turns_helper  # noqa: E402  (resolved from this helper's own directory)

HARNESS = "opencode"

# Ruling E9-3, provisional for the pilot.
FLOOR_MAP = {
    "qwen/qwen3.8-flash": "opus",
    "deepseek/deepseek-v4.1-flash": "opus",
}
CLASS_RANK = {"haiku": 1, "sonnet": 2, "opus": 3}
UNKNOWN_CLASS = "unknown"

SAFE_TOKEN = re.compile(r"[^a-z0-9]+")


class Usage(Exception):
    pass


class Missing(Exception):
    pass


def note(text):
    sys.stderr.write("invocation.py: %s\n" % text)


def mint_run_id(target_token, run_date):
    """recheck-<target token, lowercase>-<YYYYMMDD>-<4 hex>, single use.

    The date is the run date, so the id and the records the run writes carry the same day.
    """
    token = SAFE_TOKEN.sub("-", (target_token or "run").lower()).strip("-") or "run"
    stamp = run_date.replace("-", "")
    return "recheck-%s-%s-%s" % (token, stamp, os.urandom(2).hex())


def default_run_dir(run_id):
    return os.path.join(os.environ.get("TMPDIR", "/tmp"), "recheck-v2", run_id)


def find_opencode(explicit, setup):
    for candidate in (explicit, os.environ.get("OPENCODE_BIN")):
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    in_setup = os.path.join(setup, "npm", "node_modules", ".bin", "opencode")
    if os.path.isfile(in_setup) and os.access(in_setup, os.X_OK):
        return in_setup
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, "opencode")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise Missing("the opencode binary was not found (tried --opencode, $OPENCODE_BIN, %s, PATH)" % in_setup)


def run_opencode(binary, args, setup):
    """Run a non-model opencode command inside the isolated setup.

    The XDG homes are pinned to the setup unless the caller's environment already points at
    it, so a helper run from outside a session still reports the setup's own configuration
    and never the machine's live ~/.config/opencode.
    """
    env = dict(os.environ)
    for name, leaf in (
        ("XDG_CONFIG_HOME", "xdg-config"),
        ("XDG_DATA_HOME", "xdg-data"),
        ("XDG_CACHE_HOME", "xdg-cache"),
        ("XDG_STATE_HOME", "xdg-state"),
    ):
        wanted = os.path.join(setup, leaf)
        if os.path.isdir(wanted):
            env[name] = wanted
    # Measured on opencode 1.18.31: a debug/list command cuts its stdout at 65,536 bytes when
    # stdout is a pipe and writes all of it to a file, so stdout is captured by redirection.
    handle, path = tempfile.mkstemp(prefix="recheck-v2-opencode-", suffix=".out")
    try:
        with os.fdopen(handle, "wb") as sink:
            proc = subprocess.Popen(
                [binary] + args, stdout=sink, stderr=subprocess.PIPE, env=env
            )
            _unused, err = proc.communicate()
        with open(path, "rb") as source:
            out = source.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def installed_entry():
    """Where this adapter (and therefore the skill) is installed, measured from its own path."""
    skill_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parent = os.path.dirname(skill_root)
    base = os.path.basename(parent)
    grandparent = os.path.basename(os.path.dirname(parent))
    if base in ("skill", "skills") and grandparent == "opencode":
        kind = "opencode skill directory"
    elif base == "skills" and grandparent in (".claude", ".agents"):
        kind = "%s/skills directory" % grandparent
    elif base in ("skill", "skills") and grandparent == ".opencode":
        kind = "project .opencode skill directory"
    else:
        kind = "explicit path"
    return "%s: %s" % (kind, skill_root), skill_root


def sandbox_of(binary, agent, setup):
    """The permission ruleset in force for the session's agent, as the harness resolves it."""
    code, out, err = run_opencode(binary, ["debug", "agent", agent], setup)
    if code != 0:
        note("opencode debug agent %s exited %d: %s" % (agent, code, err.strip()[:200]))
        return "agent %s (permission ruleset unavailable: opencode debug agent exited %d)" % (agent, code)
    try:
        resolved = json.loads(out)
    except ValueError:
        return "agent %s (permission ruleset unreadable)" % agent
    rules = []
    for rule in resolved.get("permission", []):
        rules.append(
            "%s %s=%s" % (rule.get("permission"), rule.get("pattern"), rule.get("action"))
        )
    tools = resolved.get("tools", {})
    off = sorted(name for name, on in tools.items() if on is False)
    return "agent %s; tools off: %s; permissions: %s" % (
        agent,
        ",".join(off) if off else "none",
        "; ".join(rules) if rules else "none",
    )


def model_catalog(binary, provider, model_id, setup):
    """The model record the installed harness holds: limits, cost, capabilities, variants."""
    code, out, err = run_opencode(binary, ["models", provider, "--verbose"], setup)
    if code != 0:
        note("opencode models %s --verbose exited %d: %s" % (provider, code, err.strip()[:200]))
        return None
    header = "%s/%s" % (provider, model_id)
    lines = out.split("\n")
    try:
        start = lines.index(header)
    except ValueError:
        note("the installed catalog does not list %s" % header)
        return None
    depth = 0
    body = []
    for line in lines[start + 1:]:
        body.append(line)
        depth += line.count("{") - line.count("}")
        if body and depth == 0:
            break
    try:
        return json.loads("\n".join(body))
    except ValueError:
        note("the catalog block for %s did not parse" % header)
        return None


def session_facts(con, session_id):
    row = con.execute(
        "select id, agent, model, version, directory from session where id = ?",
        (session_id,),
    ).fetchone()
    if row is None:
        raise Missing("no session %s in the session store" % session_id)
    try:
        model = json.loads(row["model"]) if row["model"] else {}
    except ValueError:
        model = {}
    return {
        "agent": row["agent"] or "build",
        "version": row["version"],
        "directory": row["directory"],
        "model_id": model.get("id"),
        "provider": model.get("providerID"),
        "variant": model.get("variant"),
    }


def model_from_messages(con, session_id):
    """The model the harness recorded on this session's own messages."""
    for row in con.execute(
        "select data from message where session_id = ? order by time_created desc",
        (session_id,),
    ):
        try:
            data = json.loads(row["data"])
        except ValueError:
            continue
        if data.get("modelID"):
            return data.get("modelID"), data.get("providerID")
        model = data.get("model") or {}
        if model.get("modelID"):
            return model.get("modelID"), model.get("providerID")
    return None, None


def classify(model_id, floor):
    if not model_id:
        return UNKNOWN_CLASS, None
    bare = model_id.split("/", 1)[1] if model_id.startswith("openrouter/") else model_id
    klass = FLOOR_MAP.get(bare, UNKNOWN_CLASS)
    if klass == UNKNOWN_CLASS:
        return UNKNOWN_CLASS, None
    floor_rank = CLASS_RANK.get(floor)
    if floor_rank is None:
        return klass, None
    return klass, CLASS_RANK[klass] >= floor_rank


def parse_args(argv):
    opts = {
        "workspace": os.getcwd(),
        "target-token": "run",
        "session-wrote-fix": False,
        "run-date": None,
        "caller": None,
        "run-id": None,
        "run-dir": None,
        "floor": "opus",
        "session": None,
        "setup": None,
        "opencode": None,
    }
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in ("-h", "--help"):
            sys.stdout.write(__doc__)
            raise SystemExit(0)
        if arg == "--session-wrote-fix":
            opts["session-wrote-fix"] = True
            index += 1
            continue
        if arg.startswith("--") and arg[2:] in opts:
            if index + 1 >= len(argv):
                raise Usage("%s needs a value" % arg)
            opts[arg[2:]] = argv[index + 1]
            index += 2
            continue
        raise Usage("unknown argument %s" % arg)
    if opts["run-date"] is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", opts["run-date"]):
        raise Usage("--run-date must be YYYY-MM-DD")
    if opts["caller"] and not (opts["run-id"] and opts["run-dir"]):
        raise Usage("--caller needs --run-id and --run-dir (a caller route keeps its own ids)")
    if opts["run-id"] and not opts["run-dir"]:
        raise Usage("--run-id needs --run-dir")
    if opts["run-dir"] and not os.path.isabs(opts["run-dir"]):
        raise Usage("--run-dir must be absolute")
    return opts


def main(argv):
    try:
        opts = parse_args(argv)
    except Usage as exc:
        sys.stderr.write("invocation.py: %s\ninvocation.py: see --help\n" % exc)
        return 2
    try:
        setup = os.path.abspath(
            opts["setup"]
            or os.environ.get("RECHECK_OPENCODE_SETUP")
            or turns_helper.DEFAULT_SETUP
        )
        binary = find_opencode(opts["opencode"], setup)
        store = turns_helper.store_path(opts["setup"], None)
        con = turns_helper.connect(store)
        session_id, directory, resolved_by, candidates = turns_helper.resolve_session(
            con, opts["session"], opts["workspace"]
        )
        note("session %s resolved by %s (%d candidate(s) in %s)"
             % (session_id, resolved_by, candidates, directory))
        facts = session_facts(con, session_id)
        model_id, provider = model_from_messages(con, session_id)
        if model_id:
            note("model id read from this session's own message records")
        else:
            model_id, provider = facts["model_id"], facts["provider"]
            note("no message record yet; model id read from the session record")
        provider = provider or "openrouter"
        _turns, _unmapped, attribution, _raw = turns_helper.collect(con, session_id, False)
        con.close()

        floor_class, floor_met = classify(model_id, opts["floor"])
        if floor_class == UNKNOWN_CLASS:
            note("model %s is not in the E9-3 map for this lane: class unknown, floor_met null"
                 % model_id)

        entry, skill_root = installed_entry()
        note("entry measured from this helper's own path: %s" % skill_root)
        sandbox = sandbox_of(binary, facts["agent"], setup)
        catalog = model_catalog(binary, provider, model_id, setup) if model_id else None

        model = {
            "id": model_id or "unknown",
            "floor_class": floor_class,
            "floor_met": floor_met,
            "provider_route": provider,
        }
        variant = facts.get("variant")
        if variant:
            model["effort"] = variant
        settings = {
            "variant": variant or "default",
            "tool_call_format": "structured tool calls over the provider's OpenAI-compatible endpoint",
            "external_skills_disabled": os.environ.get("OPENCODE_DISABLE_EXTERNAL_SKILLS") == "1",
        }
        if catalog:
            limit = catalog.get("limit") or {}
            if isinstance(limit.get("context"), int):
                model["context_tokens"] = limit["context"]
            if isinstance(limit.get("output"), int):
                settings["output_limit_tokens"] = limit["output"]
            capabilities = catalog.get("capabilities") or {}
            for name in ("reasoning", "toolcall", "temperature"):
                if name in capabilities:
                    settings["capability_%s" % name] = bool(capabilities[name])
            if catalog.get("api", {}).get("npm"):
                settings["provider_sdk"] = catalog["api"]["npm"]
            settings["sampling_overrides_sent"] = bool(catalog.get("options"))
        else:
            note("no catalog record for %s: context_tokens omitted" % model_id)
        model["settings"] = settings

        run_date = opts["run-date"] or datetime.date.today().strftime("%Y-%m-%d")
        if opts["run-id"]:
            run_id, run_dir = opts["run-id"], opts["run-dir"]
            note("caller route: keeping the caller's run id and run directory")
        else:
            run_id = mint_run_id(opts["target-token"], run_date)
            run_dir = default_run_dir(run_id)
        if os.path.exists(run_dir) and os.listdir(run_dir):
            note("WARNING: %s already exists and is not empty; a run directory that holds a "
                 "checkpoint, a receipt or a result is spent" % run_dir)

        document = {
            "run_id": run_id,
            "run_dir": run_dir,
            "harness": {
                "name": HARNESS,
                "version": facts["version"] or "unknown",
                "entry": entry,
                "sandbox": sandbox,
            },
            "model": model,
            "run_date": run_date,
            "session_wrote_fix": bool(opts["session-wrote-fix"]),
            "turn_attribution": attribution,
        }
    except turns_helper.Missing as exc:
        sys.stderr.write("invocation.py: %s\n" % exc)
        return 3
    except Missing as exc:
        sys.stderr.write("invocation.py: %s\n" % exc)
        return 3
    except Exception as exc:  # noqa: BLE001 - reported, never worked around
        sys.stderr.write("invocation.py: %s: %s\n" % (type(exc).__name__, exc))
        return 1
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
