"""The fake rows and the fake providers' declarations (the brief's CR-1): fixtures under the tests, admitted
through the frame's own ROW rules like any lane's row. Nothing here is a lane's row and none is a rule.

`row(kind, id, phase, **entries)` writes a row with every one of ROW-1's entries: the ones a test
gives, and the word `none` for the rest. `clean_lane(...)` is the small set the reference run, the
kill sweep and the seeded cases run on, `clean_rows()`'s eight rows and any `extra` a caller adds:
one row or more of five of the nine kinds (check, build, create, change and move; no keep, owner
step, owner answer or adopt) and of six of the seven constructions (C1, C2, C3, C4, C5 and C7; C6,
open to the tool only for the four rows RK3 names, is in none of them). `ONE_OF_EACH` makes one
well-formed row of each of the nine kinds.
"""
import copy
import json
import os

NONE = "none"
KEYS = ("id", "kind", "phase", "thing", "planning_test", "before_test", "after_test", "construction", "commands",
        "repo_commands", "after_check", "output", "needs", "condition", "lost_answer", "way_back", "reverse_inputs", "span",
        "mode", "safe_content", "answers", "review_file", "owner_names", "keep_scope", "keeps_required", "content_classes",
        "form_lines")
CLASSES = {"reads": ["safe"], "stores": ["safe"], "shows": ["safe"], "validators": [], "resting_places": []}


def lit(value):
    return {"literal": value}


def path(*parts):
    return {"path": [p if isinstance(p, dict) else lit(p) for p in parts]}


DEV = {"location": "developer_root"}
NAME = {"name": 0}


def row(kind, rid, phase, **entries):
    out = dict((key, NONE) for key in KEYS)
    out.update({"id": rid, "kind": kind, "phase": phase, "content_classes": copy.deepcopy(CLASSES),
                "form_lines": {"preview": "the fake row %s" % rid, "status": "the fake row %s" % rid},
                "output": {"name": "out-" + rid, "fields": {}}})
    out.update(entries)
    return out


# ---- the fake providers --------------------------------------------------------------------------------------
def _field(name, kind, disposition, required=("success",), **more):
    out = {"name": name, "place": [name], "type": kind, "disposition": disposition, "required_in": list(required)}
    out.update(more)
    return out


def _command(tool, template, fields, effects=0, exits=None, refusals=(), **more):
    out = {"tool": tool, "template": template, "time_limit": 20, "effects": effects,
           "exits": exits or {"0": "success", "3": "not-found", "4": "conflict"},
           "fields": fields, "definite": {"success": ["success"], "refusals": list(refusals)}}
    out.update(more)
    return out


def _t(*parts):
    return [({"literal": p} if isinstance(p, str) else p) for p in parts]


P = lambda name: {"param": name}      # noqa: E731
NAMEF = dict(alphabet="a-zA-Z0-9._ -", max_length=80)
IDF = dict(alphabet="a-z0-9", max_length=64)
STATES = ["active", "paused", "archived", "connected"]


def providers():
    host = {
        "provider_version": 1, "provider": "fakehost", "host": "api.fakehost.invalid",
        "token": {"env": "FAKEHOST_TOKEN", "credentials": {"location": "fakehost_credentials", "field": "token"}},
        "credential_env": ["FAKEHOST_TOKEN"], "trace_flags": ["--debug", "--verbose", "--trace"],
        "identity": {"command": "whoami", "field": "account"},
        "commands": {
            "whoami": _command("fakehost", _t("whoami"), [_field("account", "name", "equal", equals={"settings": "fakehost"}, **NAMEF)]),
            "create": _command("fakehost", _t("create", "--kind", P("kind"), "--name", P("name")),
                               [_field("id", "id", "held", **IDF), _field("name", "name", "equal", equals={"param": "name"}, **NAMEF),
                                _field("state", "state", "fixed", list=STATES)],
                               effects=1, exits={"0": "success", "4": "conflict", "6": "terms"}, refusals=("conflict", "terms"),
                               alternatives=["terms"]),
            "request-status": _command("fakehost", _t("request-status", "--name", P("name")),
                                       [_field("made", "state", "fixed", list=["made", "nothing"]), _field("id", "id", "held", required=(), **IDF)]),
            "get": _command("fakehost", _t("get", "--name", P("name")),
                            [_field("state", "state", "fixed", list=STATES), _field("name", "name", "equal", equals={"param": "name"}, **NAMEF),
                             _field("id", "id", "held", required=(), **IDF)], refusals=("not-found",)),
            "get-by-id": _command("fakehost", _t("get", "--id-file", {"slot": "idfile"}),
                                  [_field("state", "state", "fixed", list=STATES), _field("id", "id", "held", **IDF)],
                                  refusals=("not-found",), protected_inputs=[{"slot": "idfile", "accepts": "held field"}]),
            "set-if": _command("fakehost", _t("set", "--name", P("name"), "--state", P("state"), "--if", P("if")),
                               [_field("state", "state", "fixed", list=STATES)], effects=1, refusals=("conflict", "not-found")),
            "set": _command("fakehost", _t("set", "--name", P("name"), "--state", P("state")),
                            [_field("state", "state", "fixed", list=STATES)], effects=1, refusals=("not-found",)),
            "issue": _command("fakehost", _t("issue"), [_field("token", "id", "secret", **IDF), _field("state", "state", "fixed", list=["issued"])],
                              effects=1),
            "identify": _command("fakehost", _t("identify"), [_field("identity", "id", "held", alphabet="a-z0-9-", max_length=64)],
                                 refusals=("not-found",)),
            "issued": _command("fakehost", _t("issued"), [_field("made", "state", "fixed", list=["made", "nothing"])]),
            "say": _command("fakehost", _t("noop", "--name", P("words")), []),
            "write": _command("fakehost", _t("write", "--out", P("out")), [_field("count", "count", "held", required=())],
                              effects=1, secret_output="staging"),
            "noop": _command("fakehost", _t("noop"), []),
        }}
    git = {
        "provider_version": 1, "provider": "fakegit", "host": None, "token": None, "credential_env": [],
        "trace_flags": ["--verbose"], "identity": NONE,
        "commands": {
            "cas": _command("fakegit", _t("cas", "--ref", P("ref"), "--new", P("new"), "--old", P("old")),
                            [_field("ref", "name", "equal", equals={"param": "new"}, **NAMEF)], effects=1, refusals=("conflict",),
                            changes_repository=True),
            "ref": _command("fakegit", _t("ref", "--ref", P("ref")), [_field("ref", "name", "equal", equals={"param": "expect"}, **NAMEF)]),
        }}
    dump = {
        "provider_version": 1, "provider": "fakedump", "host": None, "token": None, "credential_env": [],
        "trace_flags": ["--verbose"], "identity": NONE,
        "commands": {
            "dump": _command("fakedump", _t("dump", "--out", P("out")),
                             [_field("identity", "id", "held", alphabet="a-z0-9-", max_length=64), _field("count", "count", "held")],
                             effects=1, exits={"0": "success", "5": "other"}, secret_output="staging",
                             env={"FAKEDUMP_PASSFILE": {"class": "private path", "param": "passfile"}}),
            "inventory": _command("fakedump", _t("inventory"),
                                  [_field("identity", "id", "held", alphabet="a-z0-9-", max_length=64),
                                   _field("readable", "state", "fixed", list=["yes", "no"]),
                                   _field("unreadable", "name", "held", required=(), **NAMEF)]),
        }}
    scaffold = {
        "provider_version": 1, "provider": "fakescaffold", "host": None, "token": None, "credential_env": [],
        "trace_flags": ["--verbose"], "identity": NONE,
        "commands": {"scaffold": _command("fakescaffold", _t("scaffold", "--out", P("out")), [], effects=1, repository_writes="off")}}
    return {"fakehost": host, "fakegit": git, "fakedump": dump, "fakescaffold": scaffold}


def use(local, command, **params):
    return {"name": local, "use": command, "params": params}


# ---- one well-formed row of each kind ------------------------------------------------------------------------
def check(rid="K1", phase="one", place=None, needs=NONE, **more):
    place = place or DEV
    thing = {"role": "a folder the run reads", "identity": "path", "place": place, "tracked": ["exists"],
             "passes": [{"read": "path", "path": place, "is": "dir"}]}
    thing.update(more.pop("thing", {}))
    return row("check", rid, phase, thing=thing, needs=needs, output={"name": more.pop("output", "checked-" + rid), "fields": {}}, **more)


def build(rid="B1", phase="one", place=None, output="project folder", **more):
    place = place or path(DEV, NAME)
    return row("build", rid, phase,
               thing={"role": "the project folder", "identity": "path", "place": place, "tracked": ["exists", "identity"]},
               planning_test=[{"read": "path", "path": place, "is": "absent"}],
               before_test=[{"id": "free", "read": "path", "path": place, "is": "absent"}],
               after_test=[{"read": "path", "path": place, "is": "dir"}],
               construction={"id": "C1", "mode": 0o755,
                             "files": [{"rel": "README.md", "text": {"text": [lit("# "), NAME, lit("\n")]}},
                                       {"rel": "docs/notes.txt", "text": {"text": [{"input": "description"}, lit("\n")]}}]},
               after_check=[{"read": "path", "path": path(place, "README.md"), "is": "file"}],
               output={"name": output, "fields": {"path": place}}, **more)


def create(rid="C1", phase="one", name=None, output="remote", **more):
    name = name or NAME
    return row("create", rid, phase,
               thing={"role": "a thing at the fake host", "identity": "provider id"},
               planning_test=[{"read": "command", "command": "look", "result": "not-found"}],
               before_test=[{"id": "free", "read": "command", "command": "look", "result": "not-found"}],
               after_test=[{"read": "command", "command": "look", "result": "success"}],
               construction={"id": "C2", "document": "fakehost keeps a name unique in an account (the fake's own document)",
                             "command": "make", "id_field": "id"},
               commands=[use("look", "fakehost.get", name=name), use("make", "fakehost.create", kind=lit("repo"), name=name),
                         use("by-id", "fakehost.get-by-id", idfile={"output": output + ".id"})],
               after_check=[{"read": "command", "command": "by-id", "result": "success", "field": "state", "equals": "active"}],
               output={"name": output, "fields": {"id": {"held": "id"}, "name": name}},
               lost_answer={"way": "provider-unique", "document": "fakehost keeps a name unique in an account"}, **more)


def swap_add(rid="S1", phase="one", line=None, file=None, **more):
    file = file or {"location": "shortcut_file"}
    line = line or {"text": [lit("alias "), NAME]}
    reverse = row("change", rid + "-reverse", phase,
                  thing={"role": "the shortcut file", "identity": "path", "place": file, "tracked": ["exists", "sha256"], "span": True},
                  planning_test=[{"read": "path", "path": file, "is": "file"}],
                  before_test=[{"id": "has", "read": "line", "path": file, "line": line, "count": 1}],
                  after_test=[{"read": "line", "path": file, "line": line, "present": False}],
                  construction={"id": "C3", "risks": ["RK2"], "edit": {"kind": "remove-line", "line": line}},
                  after_check=[{"read": "line", "path": file, "line": line, "present": False}],
                  way_back={"none": "the row declares none: it is itself a reverse"})
    return row("change", rid, phase,
               thing={"role": "the shortcut file", "identity": "path", "place": file, "tracked": ["exists", "sha256"], "span": True},
               planning_test=[{"read": "path", "path": file, "is": "file"}],
               before_test=[{"id": "lacks", "read": "line", "path": file, "line": line, "present": False},
                            {"id": "name", "read": "name-free", "name": NAME, "on": "other"}],
               after_test=[{"read": "line", "path": file, "line": line, "present": True}],
               construction={"id": "C3", "risks": ["RK2", "RK5", "RK13"], "edit": {"kind": "append-line", "line": line}},
               after_check=[{"read": "line", "path": file, "line": line, "count": 1}],
               way_back={"reverse": reverse},
               reverse_inputs=[{"read": "file", "path": file, "type": "before-image", "label": "the shortcut file before the line was added"}],
               span={"placement": "at the end", "ordered": False},
               output={"name": more.pop("output", "shortcut"), "fields": {"file": file}}, **more)


def cas(rid="G1", phase="one", ref="main", new="c1", old="none", **more):
    """A compare-and-swap of a named value of the fake store. `old` may be a reference to the output of
    the operation that is to leave that value (RUN-6)."""
    old_mark = old if isinstance(old, dict) else lit(old)
    return row("change", rid, phase,
               thing={"role": "a named value of the fake store", "identity": "named value",
                      "before_word": old if isinstance(old, str) else "the value an earlier operation left", "after_word": new},
               planning_test=[{"read": "command", "command": "read-old", "result": "success", "field": "ref", "is_equal": True}],
               before_test=[{"id": "old", "read": "command", "command": "read-old", "result": "success", "field": "ref", "is_equal": True}],
               after_test=[{"read": "command", "command": "read-new", "result": "success", "field": "ref", "is_equal": True}],
               construction={"id": "C4", "command": "swap"},
               commands=[use("read-old", "fakegit.ref", ref=lit(ref), expect=old_mark), use("read-new", "fakegit.ref", ref=lit(ref), expect=lit(new)),
                         use("swap", "fakegit.cas", ref=lit(ref), new=lit(new), old=old_mark)],
               repo_commands=["swap"],
               after_check=[{"read": "command", "command": "read-new", "result": "success", "field": "ref", "is_equal": True}],
               way_back={"none": "the row declares none: a push is not taken back"},
               output={"name": more.pop("output", "pushed"), "fields": {"ref": lit(new)}}, **more)


def retiring(base, keeps=("P1",), where="provider"):
    """A row made a retirement: it names the keeps it requires and how its target's identity is read (KEEP-2)."""
    base["thing"].update({"retires": True, "where": where, "identity_read": {"command": "identity", "field": "identity"}})
    side = "fakehost.identify" if where == "provider" else "fakedump.inventory"
    base["commands"] = (base["commands"] if isinstance(base["commands"], list) else []) + [use("identity", side)]
    base["keeps_required"] = list(keeps)
    return base


def refusing(rid="H1", phase="one", name=None, before="active", after="paused", construction="C5", **more):
    name = name or NAME
    built = {"id": construction, "command": "set"}
    if construction == "C5":
        built.update({"document": "fakehost refuses a state change when --if does not hold (the fake's own document)", "conditions": ["was"]})
        command = use("set", "fakehost.set-if", name=name, state=lit(after), **{"if": lit(before)})
    else:
        built.update({"risks": ["RK3"]})
        command = use("set", "fakehost.set", name=name, state=lit(after))
    return row("change", rid, phase,
               thing={"role": "a thing at the fake host", "identity": "provider id", "before_word": before, "after_word": after},
               planning_test=[{"read": "command", "command": "look", "result": "success"}],
               before_test=[{"id": "was", "read": "command", "command": "look", "result": "success", "field": "state", "equals": before}],
               after_test=[{"read": "command", "command": "look", "result": "success", "field": "state", "equals": after}],
               construction=built, commands=[use("look", "fakehost.get", name=name), command],
               after_check=[{"read": "command", "command": "look", "result": "success", "field": "state", "equals": after}],
               way_back={"none": "the row declares none"},
               output={"name": more.pop("output", "state-" + rid), "fields": {}}, **more)


def move(rid="M1", phase="one", source=None, target=None, **more):
    source = source or path(DEV, {"text": [NAME, lit("-scope.md")]})
    target = target or path(DEV, {"text": [NAME, lit("-scope-moved.md")]})
    reverse = row("move", rid + "-reverse", phase,
                  thing={"role": "the staged document", "identity": "path", "place": target, "tracked": ["exists", "identity"]},
                  planning_test=[{"read": "path", "path": target, "is": "file"}],
                  before_test=[{"id": "there", "read": "path", "path": target, "is": "file"}],
                  after_test=[{"read": "path", "path": target, "is": "absent"}, {"read": "path", "path": source, "is": "file"}],
                  construction={"id": "C7", "risks": ["RK4"], "to": source},
                  after_check=[{"read": "path", "path": source, "is": "file"}], way_back={"none": "the row declares none: it is itself a reverse"})
    return row("move", rid, phase,
               thing={"role": "the staged document", "identity": "path", "place": source, "tracked": ["exists", "identity"]},
               planning_test=[{"read": "path", "path": source, "is": "file"}],
               before_test=[{"id": "there", "read": "path", "path": source, "is": "file"}, {"id": "free", "read": "path", "path": target, "is": "absent"}],
               after_test=[{"read": "path", "path": source, "is": "absent"}, {"read": "path", "path": target, "is": "file"}],
               construction={"id": "C7", "risks": ["RK4"], "to": target},
               after_check=[{"read": "path", "path": target, "is": "file"}],
               way_back={"reverse": reverse},
               reverse_inputs=[{"read": "value", "value": source, "type": "line", "label": "where the document was taken from"}],
               output={"name": more.pop("output", "moved document"), "fields": {"path": target}}, **more)


def keep(rid="P1", phase="one", place=None, env_file=None, **more):
    place = place or path(DEV, {"text": [NAME, lit("-dump.txt")]})
    env_file = env_file or path(DEV, {"text": [NAME, lit(".env")]})
    return row("keep", rid, phase,
               thing={"role": "the database's dump", "identity": "path", "place": place, "tracked": ["exists", "identity", "sha256"],
                      "secret_read": {"file": env_file, "keys": ["DATABASE_URL"], "command_to_show": "fakehost write --out <the env file>"}},
               planning_test=[{"read": "path", "path": place, "is": "absent"},
                              {"id": "scope", "read": "command", "command": "inventory", "result": "success", "field": "readable", "equals": "yes"}],
               before_test=[{"id": "free", "read": "path", "path": place, "is": "absent"}],
               after_test=[{"read": "path", "path": place, "is": "file"}],
               construction={"id": "C1", "builder": "dump", "out_param": "out", "single_file": True, "mode": 0o600,
                             "connection": {"file": env_file, "keys": ["DATABASE_URL"], "slot": "passfile"}},
               commands=[use("dump", "fakedump.dump"), use("inventory", "fakedump.inventory")],
               after_check=[{"read": "path", "path": place, "is": "file"}, {"read": "mode", "path": place, "at_most": 0o600}],
               keep_scope={"scope": "every table of the fake database", "same_state": "the dump tool's own answer carries the inventory of the snapshot it copied",
                           "inventory_field": "count", "source_field": "identity",
                           "source_identity_read": {"command": "inventory", "field": "identity"},
                           "unreadable_read": {"command": "inventory", "field": "unreadable", "kind": "table"},
                           "content_checks": [{"check": "count-lines", "prefix": "TABLE ", "field": "count"}]},
               content_classes={"reads": ["secret"], "stores": ["secret"], "shows": ["safe"], "validators": [], "resting_places": ["the sunset folder"]},
               output={"name": more.pop("output", "dump"), "fields": {"path": place}}, **more)


def secret_op(rid="X1", phase="one", **more):
    """A change whose one request returns a secret in a secret field (a C5: the fake refuses a second issue)."""
    return row("change", rid, phase,
               thing={"role": "a credential at the fake host", "identity": "provider id", "before_word": "nothing", "after_word": "made"},
               planning_test=[{"read": "command", "command": "look", "result": "success"}],
               before_test=[{"id": "was", "read": "command", "command": "look", "result": "success", "field": "made", "equals": "nothing"}],
               after_test=[{"read": "command", "command": "look", "result": "success", "field": "made", "equals": "made"}],
               construction={"id": "C5", "command": "issue", "conditions": ["was"],
                             "document": "fakehost issues a credential once (the fake's own document)"},
               commands=[use("look", "fakehost.issued"), use("issue", "fakehost.issue")],
               after_check=[{"read": "command", "command": "look", "result": "success", "field": "made", "equals": "made"}],
               way_back={"none": "the row declares none"},
               output={"name": more.pop("output", "credential"), "fields": {}}, **more)


def says(rid="Y1", phase="one", words=None, **more):
    """A check whose read carries the owner's own words in an argument: what a later command would show."""
    words = words or {"input": "description"}
    return row("check", rid, phase,
               thing={"role": "the fake host, told the owner's words", "identity": "none",
                      "passes": [{"read": "command", "command": "say", "result": "success"}]},
               commands=[use("say", "fakehost.say", words=words)],
               output={"name": more.pop("output", "said-" + rid), "fields": {}}, **more)


def last_record(rid="L1", phase="the last record", **more):
    """A run's own record among the project's things (KEEP-5): one new file per run, rendered from the journal."""
    place = path({"location": "developer_root"}, {"text": [NAME, lit("-record-"), {"run": "id"}, lit(".txt")]})
    return row("build", rid, phase,
               thing={"role": "the run's entry in the project's record", "identity": "path", "place": place, "tracked": ["exists", "identity", "sha256"]},
               planning_test=[{"read": "path", "path": place, "is": "absent"}],
               before_test=[{"id": "free", "read": "path", "path": place, "is": "absent"}],
               after_test=[{"read": "path", "path": place, "is": "file"}],
               construction={"id": "C1", "last_record": True, "single_file": True, "mode": 0o644},
               after_check=[{"read": "path", "path": place, "is": "file"}],
               output={"name": more.pop("output", "last record"), "fields": {"path": place}}, **more)


def owner_step(rid="O1", phase="one", mode="read back", name=None, state="connected", **more):
    name = name or NAME
    entries = dict(thing={"role": "a thing only the owner can change", "identity": "provider id"},
                   mode=mode, safe_content={"step": "connect the fake host by hand"},
                   way_back={"none": "the row declares none"},
                   output={"name": more.pop("output", "connected"), "fields": {}})
    if mode == "read back":
        entries["after_test"] = [{"read": "command", "command": "look", "result": "success", "field": "state", "equals": state}]
        entries["commands"] = [use("look", "fakehost.get", name=name)]
    entries.update(more)
    return row("owner step", rid, phase, **entries)


def owner_answer(rid="A1", phase="one", answers=("use it", "keep the old file"), **more):
    return row("owner answer", rid, phase, safe_content={"question": "use the merged file?"}, answers=list(answers),
               output={"name": more.pop("output", "answer-" + rid), "fields": {}}, **more)


def adopt(rid="D1", phase="one", **more):
    place = {"input": "adopt.project folder"}
    return row("adopt", rid, phase,
               thing={"role": "the project folder he named", "identity": "path", "place": place, "tracked": ["exists", "identity"]},
               planning_test=[{"read": "path", "path": place, "is": "dir"}], owner_names={"input": "adopt.project folder"},
               output={"name": "project folder", "fields": {"path": place}}, **more)


ONE_OF_EACH = (check, build, keep, create, swap_add, move, owner_step, owner_answer, adopt)

FORM_CHANGES = {
    "passed": "the check passed: {what}",
    "answered": "you answered: {what}",
    "a receipt due": "a secret may have been received and lost: operation {operation}, execution {execution}, field {field}",
    "a safe ground disproved": "a value this run held as safe is withheld ({count} on record)",
    # a restore's lines that FORM-2's table does not hold (EV-5; FORM-3): the lane gives them
    "not offered": "not offered by this restore ({reason}): {what}",
    "not proven, on his word": "runs on your word; it was not proven the retirement's: {what}",
    # a waiting step that OP-9 does not let a form show (A120): FORM-2's table has no line for it, and its `waiting` line,
    # which names the exact step, is not its line; the lane gives it (FORM-2; A9)
    "waiting, not shown": ("waiting on you, not shown: {what}; the step is not shown, since no read of it answered in this "
                           "invocation; mode: {mode}; the tool will know it is done {how}"),
}


def lane(kind, rows, phases=("one",), **more):
    out = {"lane_version": 1, "kind": kind,
           "alias_reads": [{"location": "developer_root", "path": ["{name}", "names.txt"], "form": "lines"}],
           "phases": list(phases), "facts": [], "questions": [], "rows": list(rows), "form_changes": dict(FORM_CHANGES), "checklist": []}
    out.update(more)
    return out


def install(machine, *lanes, **kw):
    """Write a rows root for the machine: the fake providers and the given lanes."""
    root = os.path.join(machine.root, "rows-" + machine.seed)
    os.makedirs(os.path.join(root, "providers"), exist_ok=True)
    decls = kw.get("providers") or providers()
    for name, decl in decls.items():
        with open(os.path.join(root, "providers", name + ".json"), "w") as fh:
            json.dump(decl, fh, indent=1, sort_keys=True)
    for one in lanes:
        os.makedirs(os.path.join(root, one["kind"]), exist_ok=True)
        with open(os.path.join(root, one["kind"], "lane.json"), "w") as fh:
            json.dump(one, fh, indent=1, sort_keys=True)
    machine.rows_root = root
    return root


# ---- a create whose look is a request of the frame's own and whose send is a child (LOG-2, OP-5 to OP-7, SEC-3; A99) ------
def refused_send_providers():
    """The fake providers, with one request of the fake host's own, `api-get` (SEC-2: no child is started for it), and with
    no identity read of the fake host, so that no child is started at an invocation's start. A register entry held in a
    base name's value, or in a part of the temporary folder's path, then refuses the create's send, a child, and refuses
    none of the reads that probe it."""
    decls = providers()
    decls["fakehost"]["identity"] = NONE
    decls["fakehost"]["commands"]["api-get"] = {
        "tool": "fakehost", "via": "request", "method": "GET", "template": _t("v1", "things", P("name")), "time_limit": 20,
        "effects": 0, "exits": {"200": "success", "404": "not-found"},
        "fields": [_field("state", "state", "fixed", list=STATES), _field("name", "name", "equal", equals={"param": "name"}, **NAMEF)],
        "definite": {"success": ["success"], "refusals": ["not-found"]}}
    return decls


def create_looked_by_request(rid="C1", phase="one", **more):
    """`create`, with its look (its planning test, its before-test and its after-test) made by the fake host's own request."""
    row = create(rid, phase, **more)
    row["commands"][0] = use("look", "fakehost.api-get", name=NAME)
    return row


class ThingsByName(object):
    """The fake host of the frame's own requests, for `api-get`: GET /v1/things/<name> answers from the fake host's own state,
    which its fake program keeps, `success` where a thing of that name is there and `not-found` where none is."""

    def __init__(self, machine):
        self.m = machine
        self.records = []

    def request(self, host, method, path, headers, timeout):
        from urllib.parse import unquote
        self.records.append({"host": host, "method": method, "path": path})
        parts = [unquote(p) for p in path.strip("/").split("/")]
        if host == "api.fakehost.invalid" and method == "GET" and parts[:2] == ["v1", "things"] and len(parts) == 3:
            thing = ((self.m.fake("fakehost", "state.json") or {}).get("things") or {}).get(parts[2])
            if thing:
                return 200, json.dumps({"state": thing.get("state"), "name": thing.get("name")}).encode("utf-8")
        return 404, b"{}"


def install_refused_send(machine, rows=None, providers=None):
    """The lane of one create looked by request, the providers above, and the fake host's own requests answered."""
    install(machine, lane("sunrise", rows or [create_looked_by_request("C1")]), providers=providers or refused_send_providers())
    machine.transport = ThingsByName(machine)
    return machine


def secret_send_providers():
    """`refused_send_providers`, the create's send given a secret field (SEC-4, SEC-12): `token`, not required, which the fake
    does not return, so that a send that is made gives the receipt that the result held no such value."""
    decls = refused_send_providers()
    decls["fakehost"]["commands"]["create"]["fields"].append(_field("token", "id", "secret", required=(), **IDF))
    return decls


# ---- a create whose send is a request of the frame's own (LOG-2, OP-7; RK16, A103) ------------------------------------------
def request_send_providers(host=True):
    """The fake providers, with the create's send a request of the fake host's own (SEC-2), `api-make`: POST /v1/make/<name>,
    its fields the create's. The fake host's identity read none. With `host` false the fake host has no host, and the frame
    refuses the request before anything is sent ("no host", `hostcall.send`)."""
    decls = providers()
    decls["fakehost"]["identity"] = NONE
    if not host:
        decls["fakehost"]["host"] = None
    decls["fakehost"]["commands"]["api-make"] = {
        "tool": "fakehost", "via": "request", "method": "POST", "template": _t("v1", "make", P("name")), "time_limit": 20,
        "effects": 1, "exits": {"201": "success", "409": "conflict"},
        "fields": copy.deepcopy(decls["fakehost"]["commands"]["create"]["fields"]),
        "definite": {"success": ["success"], "refusals": ["conflict"]}}
    return decls


def create_sent_by_request(rid="C1", phase="one", **more):
    """`create`, its send the fake host's own request `api-make`; its look, before-test, after-test and after-check children."""
    row = create(rid, phase, **more)
    row["commands"][1] = use("make", "fakehost.api-make", name=NAME)
    return row


class Connections(object):
    """A fake host of the frame's own requests that records every connection opened to it and makes nothing."""

    def __init__(self):
        self.records = []

    def request(self, host, method, path, headers, timeout):
        self.records.append({"host": host, "method": method, "path": path})
        return 500, b"{}"


def install_request_send(machine, rows=None, host=True, providers=None):
    install(machine, lane("sunrise", rows or [create_sent_by_request("C1")]), providers=providers or request_send_providers(host))
    machine.transport = Connections()
    return machine


def secret_request_providers(host=True):
    """`request_send_providers`, the request `api-make` given a secret field (SEC-12; RK17, A107): `token`, not required."""
    decls = request_send_providers(host)
    decls["fakehost"]["commands"]["api-make"]["fields"].append(_field("token", "id", "secret", required=(), **IDF))
    return decls


# ---- a program the runner finds in a folder of the fixture's own, which a test takes away and puts back (SEC-3; A109) ------
FAKES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fakes")


def put_program(folder, tool="fakehost"):
    """A program of the fake's name in `folder`: it starts the fake of that name as it stands under the tests."""
    target = os.path.join(FAKES, tool)
    path = os.path.join(folder, tool)
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\nexec '%s' \"$@\"\n" % target.replace("'", "'\\''"))
    os.chmod(path, 0o755)
    return path


def take_program(folder, tool="fakehost"):
    os.remove(os.path.join(folder, tool))


def program_folder(machine, tools=("fakehost",)):
    """The folder of the fixture's own that its settings name as the one folder of his on the search list, in the place of
    the tests' fakes folder, holding a program of each name in `tools` and nothing else: a program a test takes out of it is
    in no folder of the search list (the system folders hold no fake)."""
    folder = os.path.join(machine.root, "programs-" + machine.seed)
    os.makedirs(folder, exist_ok=True)
    for tool in tools:
        put_program(folder, tool)
    machine.settings["program_folders"] = [folder]
    machine.write_settings()
    return folder


# ---- a start the system refuses before the program runs, the file still there (SEC-3, SEC-12, LOG-2, OP-6, OP-7; A113 to
# A115) ----------------------------------------------------------------------------------------------------------------------
# The five causes the test lines name, each planted after the look, and the start whose answer the runner cannot read as one
# in which the program never ran. SEC-3's test line: "the fixture's file made not runnable, its first line made to name a
# program in no folder, its bytes replaced by bytes of no format the system can run with no first line naming a program,
# the row's working folder removed, and the fixture's system answering the start that no process can be had".
START_CAUSES = ("the file made not runnable", "its first line naming a program in no folder", "bytes of no format",
                "the working folder removed", "no process to be had")
UNREADABLE_START = "an answer the runner cannot read as never ran"
# A start the system refuses for a cause that is none of the five (A117; SEC-3's and OP-7's test lines): "an argument list too
# long". The fixture's system gives the answer as the real one words it, naming the very file the runner started, a file still
# standing there: read by its number alone, it is no refusal
ARG_LIST_TOO_LONG = "an argument list too long"
NO_FORMAT = b"\x00\x01\x02\x03 these bytes are no program of any format the system can run\n" * 8


def refuse_start(machine, cause, program, working, tool):
    """Plant `cause` for the start of `tool`, whose file is `program` and whose working folder is `working`. Returns (hook,
    put_right): `hook` is None or an act over the record's events, which never kills; `put_right` puts the cause right.

    - not runnable: the file's mode made 0644 (the runner's search finds a file of that name, SEC-3; the system refuses to
      run it);
    - its first line: rewritten to name a program in a folder that does not exist;
    - no format: the bytes replaced by `NO_FORMAT`, the file still runnable by its mode, no first line naming a program;
    - the working folder: moved away at the runner's own record that it is about to start that child (`pre child`), and put
      back at its record that the start ended (`post child`), so that it is gone as the system starts the child and the run
      can go on writing its records after it;
    - no process to be had, and an answer the runner cannot read: the fixture's system gives the answer (A115: "its pass
      has the fixture's system give that answer"): `machine.start`, the world's start of a process, raises the system's
      answer that no process can be had (EAGAIN, no file named), or an answer of no cause the runner reads (EIO), for a start
      of `tool` alone. That pass shows what the tool does with the answer, not that the real system gives it.
    - an argument list too long (A117): the fixture's system answers E2BIG naming the file the runner started, which stands
      there still; a cause that is none of the five."""
    import errno
    import subprocess
    if cause == START_CAUSES[0]:
        os.chmod(program, 0o644)
        return None, lambda: os.chmod(program, 0o755)
    if cause in (START_CAUSES[1], START_CAUSES[2]):
        with open(program, "rb") as fh:
            kept = fh.read()
        mode = os.stat(program).st_mode & 0o777
        with open(program, "wb") as fh:
            if cause == START_CAUSES[1]:
                rest = kept.split(b"\n", 1)[1] if b"\n" in kept else b""
                fh.write(b"#!" + os.path.join(machine.root, "no-such-folder-" + machine.seed, "sh").encode("utf-8") + b"\n" + rest)
            else:
                fh.write(NO_FORMAT)
        os.chmod(program, 0o755)

        def put_right():
            with open(program, "wb") as fh:
                fh.write(kept)
            os.chmod(program, mode)
        return None, put_right
    if cause == START_CAUSES[3]:
        away = working + ".away-" + machine.seed

        def hook(event):
            if event["op"] == "child" and str(event["subject"]) == tool:
                if event["stage"] == "pre" and os.path.isdir(working):
                    os.rename(working, away)
                elif event["stage"] == "post" and os.path.isdir(away):
                    os.rename(away, working)
            return False
        return hook, lambda: None
    if cause in (START_CAUSES[4], UNREADABLE_START, ARG_LIST_TOO_LONG):
        number = {START_CAUSES[4]: errno.EAGAIN, UNREADABLE_START: errno.EIO, ARG_LIST_TOO_LONG: errno.E2BIG}[cause]

        def start(argv, **kw):
            if os.path.basename(str(argv[0])) == tool:
                if cause == ARG_LIST_TOO_LONG:
                    # the system's own answer names the file it was asked to run (subprocess hands it so)
                    raise OSError(number, os.strerror(number), str(argv[0]))
                raise OSError(number, os.strerror(number))
            return subprocess.Popen(argv, **kw)
        machine.start = start
        return None, lambda: setattr(machine, "start", None)
    raise ValueError(cause)


def refuse_start_at(machine, cause, program, working, tool, nth):
    """`refuse_start`, planted for the `nth` start of `tool` alone, the starts before it made as they stand (SEC-3's test line,
    A117: a change's after-check "once its effect call has been made"). Returns (hook, put_right) as `refuse_start` does.

    - the file's causes (not runnable, its first line, no format): planted at the runner's record that the start before the
      `nth` ended (`post child`);
    - the working folder: moved away at the `nth` start's record `pre child` and put back at its `post child`;
    - no process to be had, and the other answers the fixture's system gives: the `nth` start of `tool` is answered so."""
    import subprocess
    if nth == 1:
        return refuse_start(machine, cause, program, working, tool)
    seen = {"pre": 0, "post": 0}
    undo = []
    if cause in (START_CAUSES[0], START_CAUSES[1], START_CAUSES[2]):
        def hook(event):
            if event["op"] == "child" and str(event["subject"]) == tool and event["stage"] == "post":
                seen["post"] += 1
                if seen["post"] == nth - 1:
                    undo.append(refuse_start(machine, cause, program, working, tool)[1])
            return False

        def put_right():
            for act in undo:
                act()
        return hook, put_right
    if cause == START_CAUSES[3]:
        away = working + ".away-" + machine.seed

        def hook(event):
            if event["op"] == "child" and str(event["subject"]) == tool:
                if event["stage"] == "pre":
                    seen["pre"] += 1
                    if seen["pre"] == nth and os.path.isdir(working):
                        os.rename(working, away)
                elif event["stage"] == "post" and os.path.isdir(away):
                    os.rename(away, working)
            return False
        return hook, lambda: None
    _none, answer_off = refuse_start(machine, cause, program, working, tool)
    refusing = machine.start
    starts = [0]

    def start(argv, **kw):
        if os.path.basename(str(argv[0])) == tool:
            starts[0] += 1
            if starts[0] == nth:
                return refusing(argv, **kw)
        return subprocess.Popen(argv, **kw)
    machine.start = start
    return None, answer_off


def zsh_system_folder(machine):
    """A system folder of the fixture's own, the one system folder of its list, holding a zsh that starts the fake shell
    (`tests/fakes/system/zsh`) by its full path: a file a test may change or take away. Returns the zsh's path."""
    folder = os.path.join(machine.root, "zsh-system-" + machine.seed.replace(" ", "-"))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "zsh")
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\nexec '%s' \"$@\"\n" % os.path.join(FAKES, "system", "zsh").replace("'", "'\\''"))
    os.chmod(path, 0o755)
    machine.system_folders = (folder,)
    return path


# ---- a change whose reads are a request of the frame's own and whose effect call is a child (SEC-3; A109) ------------------
def change_looked_by_request(rid="H1", phase="one"):
    """`refusing` (a C5), its look, before-test, after-test and after-check the fake host's own request `api-get`, so that its
    effect call, `fakehost set`, is the one child it starts."""
    row = refusing(rid, phase)
    row["commands"][0] = use("look", "fakehost.api-get", name=NAME)
    return row


def install_change_looked_by_request(machine):
    install(machine, lane("sunrise", [change_looked_by_request("H1")]), providers=refused_send_providers())
    machine.transport = ThingsByName(machine)
    machine.set_fake("fakehost", things={"demo": {"id": "t1", "kind": "repo", "state": "active", "name": "demo"}})
    return machine


def change_checked_by_child(rid="H1", phase="one"):
    """`change_looked_by_request`, its after-check a child as well (`fakehost get`): the effect call, `fakehost set`, is the
    first child it starts and the after-check's read the second (SEC-3's test line, A117: "at a change's effect call, and in
    another pass at a change's after-check once its effect call has been made")."""
    row = change_looked_by_request(rid, phase)
    row["commands"].append(use("check", "fakehost.get", name=NAME))
    row["after_check"] = [{"read": "command", "command": "check", "result": "success", "field": "state", "equals": "paused"}]
    return row


def install_change_checked_by_child(machine, providers=None):
    install(machine, lane("sunrise", [change_checked_by_child("H1")]), providers=providers or refused_send_providers())
    machine.transport = ThingsByName(machine)
    machine.set_fake("fakehost", things={"demo": {"id": "t1", "kind": "repo", "state": "active", "name": "demo"}})
    return machine


def clean_rows():
    """The fake rows of the reference run: every kind that has an effect, every construction open
    to the tool, a check that is attempted again, and a last record."""
    project = {"output": "project folder.path"}       # what the plan is to make is named by its output (RUN-6)
    return [
        check("K1", "prepare", output="preflight"),
        build("B1", "prepare"),
        swap_add("S1", "prepare", needs=[{"output": "project folder", "level": "state", "treatment": "then not applicable"}]),
        move("M1", "prepare", target=path(project, "scope.md"),
             needs=[{"output": "project folder", "level": "made", "treatment": "then not applicable"}]),
        create("C1", "remote", needs=[{"output": "project folder", "level": "made", "treatment": "then not applicable"}]),
        check("K2", "remote", place=path(project, "README.md"), output="scanned",
              thing={"tracked": ["exists", "sha256"], "passes": [{"read": "path", "path": path(project, "README.md"), "is": "file"}]},
              needs=[{"output": "project folder", "level": "state", "treatment": "then not applicable"}]),
        cas("G1", "remote", needs=[{"output": "remote", "level": "made", "treatment": "then not applicable"},
                                    {"output": "scanned", "level": "passed", "treatment": "then not applicable"}]),
        refusing("H1", "remote", name={"output": "remote.name"}, needs=[{"output": "remote", "level": "made", "treatment": "then not applicable"}]),
    ]


def clean_lane(kind="sunrise", extra=()):
    return lane(kind, clean_rows() + list(extra), phases=("prepare", "remote"))
