"""One declared command, from its template to its kept result (the frame's SEC-3, SEC-4, SEC-12, SEC-2).

`call` builds the argument list from the declaration's template, filled with safe values only; hands
a held value over as a protected input, the path of an owner-only file made from its record;
builds the registered environment; and starts the child through the one runner. Where the
declaration has a secret field it is run only inside an operation: before the child starts the
journal holds the step record that a receipt is due; after the result is parsed each kept secret is
in the register, then in its protected record, the search for it is made, the disproof record is
written where the search found it, and the receipt is given. None of that waits on the rest of the
result.
"""
import os

from . import disproof, protected, results, runner, values


class Disproved(Exception):
    """A value received in a secret field is held by the run's records: a safe ground disproved."""

    def __init__(self, result):
        Exception.__init__(self, "a safe ground disproved")
        self.result = result


class NotCallable(Exception):
    """The command cannot be built as declared. `reason` is a fixed word of the tool's."""

    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason


def secret_fields(declaration):
    """The declaration's secret fields, in the declaration's order (SEC-4)."""
    return [f for f in declaration.get("fields") or [] if f.get("disposition") == "secret"]


def has_secret_field(declaration):
    return bool(secret_fields(declaration))


def _custody(session, found, due_fields, command_name, op, execution, journal):
    """Custody of every secret field of one execution (SEC-4, SEC-12; the reviewer's D8-B). `found` is the
    parser's reading of each secret field, in the declaration's order; `due_fields` the due record's ids, in the
    same order. Each value kept enters the register on receipt, before any field of another disposition is read;
    then three passes over the fields, all of them before any other field: each kept value to its own protected
    record; the search for each, and each disproof record owed; the receipt of each, one record for each field.
    What becomes of one field changes nothing for another. Returns whether a safe ground was disproved."""
    from . import disproofs
    world, register, run_dir = session.world, session.register, session.run_dir
    ids = dict((item["field"], item["record"]) for item in due_fields)
    entries = {}
    for read in found:
        if read.outcome == "kept":
            entries[read.name] = register.add(read.raw, read.components, None, "secret field")
    references = {}
    for read in found:                                   # the first pass: each kept value to its own protected record
        if read.outcome == "kept":
            references[read.name] = protected.write(
                world, run_dir, ids[read.name], protected.envelope(read.raw, read.is_text, read.passed, read.components),
                "secret field", "the secret field %s of %s" % (read.name, command_name))
    disproved = False
    for read in found:                                   # the second pass: the search for each, each disproof owed
        entry = entries.get(read.name)
        spans = disproof.search(world.fs, run_dir, entry) if entry is not None else []
        if spans:
            record = journal.append(world, "disproof", register=register,
                                    **disproof.owed_for_field(references[read.name], spans, op, execution))
            entry.ref = disproofs.reference_of(record)
            disproved = True
    for read in found:                                   # the third pass: the receipt of each field
        fields = {"op": op, "step": "receipt", "execution": execution, "command": command_name, "field": read.name,
                  "outcome": read.outcome}
        if read.name in references:
            fields["reference"] = references[read.name]
        journal.append(world, "step", register=register, **fields)
    return disproved


def argv_for_show(command, params_shown):
    """The command with its declared arguments, as a stop's form shows it (SEC-5): the tool's name
    and the template, a held or private value standing as the fixed name of its slot."""
    decl = command["declaration"]
    if decl.get("via") == "request":
        shown = ["request", str(decl.get("method") or "GET")]
        for part in decl.get("template") or []:
            parts = part["text"] if "text" in part else [part]
            shown.append("".join(str(p["literal"]) if "literal" in p else str(params_shown.get(p.get("param"), "<%s>" % p.get("param")))
                                 for p in parts))
        return " ".join(shown)
    shown = [decl["tool"]]
    for part in decl.get("template") or []:
        if "literal" in part:
            shown.append(str(part["literal"]))
        elif "text" in part:
            shown.append("".join(str(p["literal"]) if "literal" in p else str(params_shown.get(p.get("param"), "<%s>" % p.get("param")))
                                 for p in part["text"]))
        elif "param" in part:
            shown.append(str(params_shown.get(part["param"], "<%s>" % part["param"])))
        elif "slot" in part:
            shown.append("<file:%s>" % part["slot"])
    return " ".join(shown)


INPUT_PREFIX = "input"       # a file made to hand a protected input to a child: `protected/input-<id>` (SEC-3, LOG-3)


def _input_file(world, run_dir, content):
    """The owner-only file a protected input is handed over in (SEC-3's protected-input row, batch 20): made in the run
    directory's protected folder, the place SEC-7 gives the record it is made from, so that one a kill leaves rests where
    its record may rest. The run removes it once its child has ended (LOG-3); a kill may leave it there."""
    path = os.path.join(protected.folder(run_dir), world.new_id(INPUT_PREFIX))
    world.fs.write_new(path, content)
    return path


SERVICE_ENV = "PGSERVICE"     # libpq's name for the service a password file's one section is named for (G20-1)


def _password_file(world, run_dir, decl, connection):
    """SEC-2's private password file for a command that declares its slot (G20-1): `connection` is (the address, the slot,
    the operation or row it is made for). Where the declaration's environment names the slot as a private path, the whole
    address is written as one libpq service section, named for the service the declaration fixes, in the run directory's
    private folder, owner-only from its first byte; returns (slot, path), or None where the command declares no such slot."""
    from . import channels, rundir
    address, slot, label = connection
    env = decl.get("env") or {}
    if not any(s.get("class") == "private path" and (s.get("slot") or s.get("param")) == slot for s in env.values()):
        return None
    service = (env.get(SERVICE_ENV) or {})
    if service.get("class") != "fixed" or not service.get("value"):
        raise NotCallable("the connection cannot be written as a service file")
    try:
        data = channels.service_file(address, str(service["value"]))
    except ValueError:
        raise NotCallable("the connection cannot be written as a service file")
    path = os.path.join(run_dir, "private", rundir.PASSWORD_PREFIX + label)
    world.fs.write_new(path, data)
    return slot, path


def _part(part, params):
    """One value of a request's query or body (G20-2): a literal of the declaration's, or a value the row gives, filled as a
    template's part is (a held value in memory, going back to its issuer, SEC-2)."""
    if isinstance(part, dict) and "literal" in part:
        return part["literal"]
    if isinstance(part, dict) and "param" in part and part["param"] in params:
        return params[part["param"]]
    raise NotCallable("a template names a value the row does not give")


def _body(node, params):
    """A request's JSON body: an object whose leaves are `_part`s."""
    if isinstance(node, dict) and ("literal" in node or "param" in node) and len(node) == 1:
        return _part(node, params)
    if isinstance(node, dict):
        return dict((k, _body(v, params)) for k, v in node.items())
    if isinstance(node, list):
        return [_body(v, params) for v in node]
    raise NotCallable("a request body leaf is no value of the row")


def call(session, command, outputs, op=None, journal=None, extra_params=None, cwd=None, own=None, connection=None, hosting_env=False):
    """Run one command of a row. Returns (results.Result, shown) where `shown` is the command as a
    form may show it. Raises `runner.Refused`, `NotCallable` or `Disproved`. `connection`, where given, is the address SEC-2's
    private password file is built from for a command that declares its slot (G20-1); the file is removed when the call ends,
    however it ends. `hosting_env` is true for the builder of the keep construction marked as the one that saves a hosting
    environment's values, and for no other call: RK19's floor is applied there alone (G22-3)."""
    if connection is not None:
        made = _password_file(session.world, session.run_dir, command["declaration"], connection)
        if made is not None:
            try:
                return call(session, command, outputs, op, journal, dict(extra_params or {}, **{made[0]: made[1]}), cwd, own,
                            hosting_env=hosting_env)
            finally:
                session.world.fs.remove(made[1])
    world, register, run_dir = session.world, session.register, session.run_dir
    decl = command["declaration"]
    params, shown, private = {}, {}, []
    held_params = set()          # a held value the request carries, or a protected input's path: never a ground (G22-1)
    given = dict(command.get("params") or {})
    given.update(extra_params or {})
    slots = dict((s["slot"], s) for s in decl.get("protected_inputs") or [])
    request = decl.get("via") == "request"
    for name, value in given.items():
        resolved = values.resolve(value, outputs) if isinstance(value, dict) else value
        if isinstance(resolved, values.Held) and request:
            # SEC-2: a held value goes back to the provider that issued it in the frame's own request, in memory; a secret
            # goes in no request
            if resolved.reference.get("type") == "secret field":
                raise NotCallable("a secret goes in no request")
            params[name] = protected.read(world.fs, run_dir, resolved.reference).decode("utf-8")
            shown[name] = "<held:%s>" % name
            held_params.add(name)
            continue
        if isinstance(resolved, values.Held):
            if name not in slots:
                raise NotCallable("a held value has no protected input to travel by")
            content = protected.read(world.fs, run_dir, resolved.reference)
            if resolved.reference.get("type") == "secret field":
                content = protected.open_envelope(content)["raw"].encode("utf-8")
            path = _input_file(world, run_dir, content)
            private.append(path)
            params[name] = path
            shown[name] = "<file:%s>" % name
            held_params.add(name)
        else:
            params[name] = resolved
            shown[name] = resolved
    argv = []
    for part in decl.get("template") or []:
        if "literal" in part:
            argv.append(str(part["literal"]))
        elif "text" in part:
            # G24-2: one argument built from literals and parameters (vercel's `cli-team`: the team in `/v2/teams/<team>`),
            # each parameter filled as a part of its own is
            if any("param" in p and p["param"] not in params for p in part["text"]):
                raise NotCallable("a template names a value the row does not give")
            argv.append("".join(str(p["literal"]) if "literal" in p else str(params[p["param"]]) for p in part["text"]))
        elif "param" in part or "slot" in part:
            key = part.get("param") or part.get("slot")
            if key not in params:
                raise NotCallable("a template names a value the row does not give")
            argv.append(str(params[key]))
    request_query = [(item["name"], _part(item["value"], params)) for item in decl.get("query") or []] if request else None
    request_body = _body(decl["body"], params) if request and isinstance(decl.get("body"), dict) else None
    env = {}
    for name, spec in (decl.get("env") or {}).items():
        kind = spec.get("class")
        if kind == "fixed":
            env[name] = str(spec.get("value", ""))
        elif kind == "passed":
            if name in world.env:
                env[name] = world.env[name]
        elif kind == "private path":
            key = spec.get("slot") or spec.get("param")
            if key in params:
                env[name] = str(params[key])
    fields = []
    for field in decl.get("fields") or []:
        spec = field.get("equals")
        if field.get("disposition") == "equal" and isinstance(spec, dict):
            field = dict(field)
            if "param" in spec and spec["param"] in shown and spec["param"] not in held_params:
                # what the tool sent in that request, where it is safe content. A held value sent back to its issuer is no
                # ground: "An equality ground may use only independently safe content; a held request parameter and its
                # echo must remain held" (the reviewer's F1, G22-1). Such a field has no safe value to equal: its value stays
                # held and the tool keeps the fixed fact that it differs
                field["equals_value"] = params[spec["param"]]
            elif "literal" in spec:
                field["equals_value"] = spec["literal"]
            elif "settings" in spec:                                      # ground C: a name in his settings
                field["equals_value"] = list(session.facts.accounts(world.fs).get(spec["settings"], []))
            elif "own" in spec:                                           # what the tool counted or measured itself
                field["equals_value"] = (own or {}).get(spec["own"])
        fields.append(field)
    decl = dict(decl, fields=fields)
    execution = None
    secret = has_secret_field(decl)
    # a command run for an operation (its effect call, its probe's and after-check's reads, an owner step's read): a file the
    # runner found that is gone as it starts it is a refusal of the runner's (SEC-3's command row, A109)
    context = runner.Context(register, run_dir, session.facts.search_list(world.fs, world.system_folders),
                             of_operation=op is not None)
    program = None
    if secret:
        if op is None or journal is None:
            raise NotCallable("a command with a secret field is run only inside an operation")
        if not request:
            # SEC-12 (batch 44, A102): "A command the runner refuses (SEC-3) has no execution and starts no child: the
            # runner's check is made before that step record, and where it refuses, no receipt is due." The check is made
            # here, on the command as it would be started, the runner's search for the program among it (batch 46, A110: "a
            # program in no folder of the search list is refused there, before that step record, and no receipt is due"); a
            # refusal goes on as every refusal of the runner's does, with no due record written and no execution counted. The
            # file the search found is the one `runner.run` starts. A request of the frame's own (SEC-2) is no command of the
            # runner's: its due record is written before the frame's own checks of it, and where the frame refuses it the
            # receipt stays due (RK17, A107)
            try:
                program = runner.check(world, context, decl, argv, env)
            except runner.Refused:
                for path in private:
                    world.fs.remove(path)
                raise
        execution = 1 + len([r for r in journal.records if r.get("kind") == "step" and r.get("step") == "receipt-due"
                             and r.get("op") == op and r.get("command") == command["name"]])
        # SEC-12: one due record before the child starts, naming, field by field in the declaration's order, the
        # id under which that field's value will be kept
        due_fields = [{"field": f["name"], "record": world.new_id("p")} for f in secret_fields(decl)]
        journal.append(world, "step", register=register, op=op, step="receipt-due", execution=execution,
                       command=command["name"], fields=due_fields)
    try:
        if request:
            from . import hostcall
            provider = command["use"].partition(".")[0] if isinstance(command.get("use"), str) else decl.get("provider")
            try:
                raw = hostcall.send(world, register, session.providers.get(provider) or {}, decl, argv, session.tokens.get(provider),
                                    query=request_query, body=request_body)
            except hostcall.Refused as refused:
                raise runner.Refused(refused.reason)
        else:
            raw = runner.run(world, context, decl, argv, env, cwd or run_dir, program=program)
    except runner.Refused as refused:
        if secret and not request and refused.at_start:
            # SEC-12 (batch 46, A110): "Where the file the runner found is gone as it starts it, so that no child is created,
            # the refusal is met after that step record: a step record then gives the receipt of each field, one for each,
            # saying that no child was started, and none is left due (A109)." One record for each field, in the
            # declaration's order, each saying so in fixed words and naming no protected record, none having been written
            for item in due_fields:
                journal.append(world, "step", register=register, op=op, step="receipt", execution=execution,
                               command=command["name"], field=item["field"], outcome=results.NO_CHILD)
        for path in private:
            world.fs.remove(path)
        raise
    for path in private:
        world.fs.remove(path)
    # RK1 and SEC-4 meet here. RK1's entry: the frame "reads nothing they print"; SEC-4 parses a started program's
    # answer. What the runner hands over is standard output alone, in memory (standard error is read and dropped,
    # `runner.run`), and the parser reads from it only the declared fields at their declared places, never the
    # tool's text (`results.Parser`); what it keeps is held unless a ground proves it, and the records are only as
    # true as that program's answer (RK11, where the program stands in a folder he named).
    parser = results.Parser(decl, raw, register, hosting_env=hosting_env)
    disproved = False
    if secret:
        disproved = _custody(session, parser.secrets(), due_fields, command["name"], op, execution, journal)
    result = parser.finish()
    result.secret_outcome = None
    result.shown = argv_for_show(command, shown)
    if disproved:
        raise Disproved(result)
    return result
