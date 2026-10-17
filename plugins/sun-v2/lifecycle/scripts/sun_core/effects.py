"""The probe, and what the tool does with each answer (the frame's OP-3, OP-4, OP-5, OP-6, OP-7; EV-1;
KEEP-1 to KEEP-3, KEEP-5; SEC-2's private password file).

Seven constructions and no other. For each the probe decides what "the same thing" means:

    C1  publish from staging     the object at the place has the staged identity in the step record
    C2  a provider's create      the id read is the id the answer record refers to; no answer record: outstanding, but
                                 after the step record of the runner's refusal of its send (A99): nothing under its name
    C3  swap                     the file at the recorded path; the staged identity decides only the ground
    C4  compare-and-swap         the same named value of the same store
    C5  a refusing call          the named thing, by the read its row declares
    C6  read, then ask           the same; only for the four rows RK3 names
    C7  exclusive move           the object with the identity read at the source into the start record
"""
import os

from . import channels, engine as enginemod, forms, fsio, protected, reads, rundir, runner, values

Stop = enginemod.Stop
UNCONFIRMED = "the entry is at its place and unconfirmed"


def run(engine, operation):
    op, kind = operation["id"], operation["kind"]
    thing = operation["thing"]
    if thing.get("retires"):
        barrier(engine, operation)
        tied(engine, operation)
    other = others_as_expected(engine, operation)
    if other is not None:
        raise Stop("foreign", op, what=other)
    answer = probe(engine, operation)
    if answer == "ready":
        changed = target_as_expected(engine, operation)
        if changed is not None:
            raise Stop("foreign", op, what=changed)
    if answer == "foreign":
        # EV-3 (batch 34): a target in a state that is neither gives `foreign`, "and the form names the file as the
        # operation's target by its role and its safe name"; EV-6: where the declared placement cannot be met, "the form
        # names the file, the place and the protected records, and shows no text of the file or of a record"
        unmet = placement_cannot_be_met(engine, operation) if not engine.state.starts.get(op) else None
        raise Stop(answer, op, what=unmet or target_named(engine, operation))
    if answer == "unreadable":
        raise Stop(answer, op)
    if answer == "already so":
        if kind in ("build", "keep"):
            raise Stop("something is at the place", op)
        if kind == "create":
            raise Stop("something has the name", op)
        engine.log("status", op=op, status="already so", observed=target_state(engine, operation, after=True),
                   way_back={"offered": False, "reason": "found already so"})
        return
    cid = operation["construction"]["id"]
    if answer == "landed":
        landed(engine, operation, cid)
        return
    if answer == "not landed" and kind in ("build", "keep"):
        clear_staging(engine, op)
    HANDLERS[cid](engine, operation, answer)


# ---- the present, per thing (EV-3) -------------------------------------------------------------------
def others_as_expected(engine, operation):
    """An operation's named things, other than its target, must each be in the last tracked state the journal holds for
    it or, where it holds none, in the state the manifest recorded at the look (EV-3). Returns, for the first that is
    not, how the stop names it as its row and the manifest hold it: by its role in the row and its safe name, its path;
    or, where its identity is a held value, by its role, its kind and the reference of the protected record that holds
    that identity, and never by the held value. None where every one is as expected."""
    recorded = operation.get("also_states") or []
    for index, other in enumerate(operation["thing"].get("also") or []):
        role = other.get("role") or "a thing the operation names"
        if other.get("place") is None:
            named = held_thing(engine, operation, other, role)
            if named is not None:
                return named
            continue
        path = engine.value(other["place"], operation["id"])
        facts = other.get("tracked") or ("exists", "sha256")
        now = reads.tracked_state(engine.fs, path, facts)
        expected = engine.state.tracked.get(path)
        if expected is None and index < len(recorded) and recorded[index]:
            expected = recorded[index]
        if expected is None:
            continue
        if any(now.get(fact) != expected.get(fact) for fact in facts if fact in expected):
            return "%s, %s" % (role, path)
    return None


def target_as_expected(engine, operation):
    """EV-3 for the operation's own target, where the probe answers `ready` (no start record, the after-test not holding and
    the before-test holding): OP-5 gives `ready` only where "each thing the operation names is in its expected state (EV-3)",
    the last tracked state the journal holds for it or, where it holds none, the state the manifest recorded at the look.
    A difference in a fact the row tracks is `foreign`, named by its role and its path. None where it is as expected, or
    where neither the journal nor the manifest holds a state of it (a place the plan is to make, RUN-6)."""
    thing = operation["thing"]
    if thing.get("place") is None:
        return None
    path = engine.value(thing["place"], operation["id"])
    expected = engine.state.tracked.get(path)
    if expected is None and isinstance(operation.get("tracked_state"), dict) and operation["tracked_state"].get("path") == path:
        expected = operation["tracked_state"]
    if not isinstance(expected, dict):
        return None
    facts = thing.get("tracked") or ("exists", "identity", "sha256", "mode")
    now = reads.tracked_state(engine.fs, path, facts)
    if any(now.get(fact) != expected.get(fact) for fact in facts if fact in expected and fact in now):
        return "%s, %s" % (thing.get("role") or "the thing the operation acts on", path)
    return None


def target_named(engine, operation):
    """The operation's own target as a stop names it (EV-3): by its role in the row and its path, a safe name, where it is
    a thing of this machine; None where the row places it nowhere (a thing at a provider)."""
    thing = operation["thing"]
    if thing.get("place") is None:
        return None
    try:
        path = engine.value(thing["place"], operation["id"])
    except Stop:
        return None
    role = thing.get("role") or "the thing the operation acts on"
    return "%s, %s" % (role, path) if isinstance(path, str) else role


def held_thing(engine, operation, other, role):
    """EV-3 for a thing whose only identity is a held id an earlier operation provided: its state is read by the row's
    declared command, the id going back to its issuer through a protected input (SEC-2, SEC-3), and compared with the
    last tracked state the journal holds for it, the state the providing operation's completion observed."""
    op = operation["id"]
    held = engine.value(other.get("id"), op)
    reference = getattr(held, "reference", None)
    if not isinstance(reference, dict):
        raise Stop("a value the operation needs is not bound", op)
    named = "%s, %s, the protected record %s (%s): %s" % (role, other.get("kind") or "a thing at a provider", reference.get("record"),
                                                        reference.get("label"), protected.path_of(engine.run_dir, reference.get("record")))
    provider = str(other["id"].get("output", "")).partition(".")[0] if isinstance(other.get("id"), dict) else ""
    expected = None
    for record in engine.journal.records:
        source = engine.state.ops.get(record.get("op")) or {}
        if record.get("kind") == "completion" and (source.get("output") or {}).get("name") == provider:
            word = (record.get("observed") or {}).get("word")
            expected = word or expected
    if not expected:
        return None
    spec = other.get("read") or {}
    result = engine.call(engine.command(operation, spec.get("command")), op)
    if result.kind != "success":
        raise Stop("unreadable", op, what=named)
    if result.safe().get(spec.get("field")) != expected:
        return named
    return None


def target_state(engine, operation, after=False):
    thing = operation["thing"]
    cid = operation["construction"]["id"]
    if cid == "C7" and after:
        return reads.tracked_state(engine.fs, engine.value(operation["construction"]["to"], operation["id"]),
                                   thing.get("tracked") or ("exists", "identity"))
    if thing.get("place") is not None:
        return reads.tracked_state(engine.fs, engine.value(thing["place"], operation["id"]),
                                   thing.get("tracked") or ("exists", "identity", "sha256", "mode"))
    return {"word": str(thing.get("after_word" if after else "before_word", ""))[:64]}


# ---- the probe (OP-5) -----------------------------------------------------------------------------------
def probe(engine, operation):
    """Exactly one of six answers. A probe only reads; the after-state is asked before the before-state."""
    op, state = operation["id"], engine.state
    starts = state.starts.get(op) or []
    reader = engine.reader(operation)
    cid = operation["construction"]["id"]
    try:
        if not starts:
            after = reader.evaluate(operation.get("after_test"))
            if after == reads.UNREADABLE:
                return "unreadable"
            if after is True:
                return "already so"
            before = reader.evaluate(operation.get("before_test"))
            if before == reads.UNREADABLE:
                return "unreadable"
            if before is True and placement_cannot_be_met(engine, operation):
                return "foreign"              # EV-6: "Where the declared placement cannot be met the probe answers `foreign`"
            return "ready" if before is True else "foreign"
        start = starts[-1]
        if cid == "C1":
            place = start["after"]["path"]
            at = engine.fs.identity(place)
            if at is None:
                return "not landed"
            staged = [s for s in state.steps.get(op) or [] if s.get("step") == "staged" and s["n"] > start["n"]]
            return "landed" if staged and staged[-1].get("identity") == at else "foreign"
        if cid == "C3":
            path = start["thing"]["path"]
            if not engine.fs.isfile(path):
                return "foreign"
            now = fsio.sha256_hex(engine.fs.read(path))
            if now == start["after"].get("sha256"):
                return "landed"
            return "not landed" if now == start["thing"].get("sha256") else "foreign"
        if cid == "C2":
            if not state.answers.get(op):
                # OP-5, C2 (batch 43, A99): "with no answer record the create is outstanding whatever is read (OP-7), but
                # where the step record of the runner's refusal of its send follows its start record (LOG-2): no request
                # left the tool, so nothing under the create's name is the before-state, `not landed`, and a thing under
                # that name is `foreign`". Without that record the engine stops before the probe, as outstanding
                if op not in state.unsent:
                    raise enginemod.Stop("an outstanding create", op)
                after = reader.evaluate(operation.get("after_test"))
                if after == reads.UNREADABLE:
                    return "unreadable"
                if after is True:
                    return "foreign"          # a thing under the create's name, which no request of the run's made
                before = reader.evaluate(operation.get("before_test"))
                if before == reads.UNREADABLE:
                    return "unreadable"
                return "not landed" if before is True else "foreign"
            # OP-5, C2: "the id read is the id the answer record refers to (LOG-2), the two compared in memory". With its
            # answer record the thing is read by the recorded id: in the after-state, `landed`; anything else, `foreign`
            # (OP-5's test line, batch 39: "a create with its answer record whose read by the recorded id finds nothing
            # yields `foreign`, never `not landed`"; Part 5, example 3)
            verdict = reader.evaluate(operation.get("after_check"))
            if verdict == reads.UNREADABLE:
                return "unreadable"
            return "landed" if verdict is True else "foreign"
        if cid == "C7":
            source, target = start["thing"]["path"], start["after"]["path"]
            want = start["thing"].get("identity")
            at_source, at_target = engine.fs.identity(source), engine.fs.identity(target)
            if at_source == want and at_target is None:
                return "not landed"
            if at_source is None and at_target == want:
                return "landed"
            return "foreign"
        after = reader.evaluate(operation.get("after_test"))
        if after == reads.UNREADABLE:
            return "unreadable"
        if after is True:
            return "landed"
        before = reader.evaluate(operation.get("before_test"))
        if before == reads.UNREADABLE:
            return "unreadable"
        return "not landed" if before is True else "foreign"
    except OSError:
        return "unreadable"
    except runner.Refused as refused:
        # a child a read of the probe starts, refused by the runner: the shortcut check's shell at the read of the
        # before-test, or at the after-test the probe asks first (SEC-3's test line, batch 40, A94). SEC-3's refusals row:
        # "Where the refused command is an operation's, the operation is not started and the run ends `stopped` on that
        # refusal." So no start record is written, no effect call is made, and the run ends `stopped` on it, as `Engine.call`
        # ends a row's command; no exception reaches the command line's defect line
        stop = Stop("the runner refused the command: " + refused.reason, op)
        stop.refused = True
        raise stop


def after_check(engine, operation):
    """The after-check's read, after the effect call. A check that does not show the after-state
    stops the run with no completion recorded."""
    try:
        verdict = engine.reader(operation).evaluate(operation.get("after_check"))
    except runner.Refused as refused:
        # a child the after-check's read starts (the shortcut check's shell; a row's command is stopped so by `call`),
        # refused by the runner. SEC-3's refusals row (batch 41, A96): "A refused command met after the operation's start
        # record, at its effect call or at its after-check, leaves the operation as that record left it: no completion is
        # recorded, the run ends `stopped` on that refusal, its form naming it, and the next invocation's probe reads the
        # world again". Raised before `complete`, so the start record stands and nothing more is written of the operation
        raise enginemod.refused_stop(refused, operation["id"], what="the after-check")
    if verdict is not True:
        raise Stop("the after-check does not show the after-state", operation["id"])


def complete(engine, operation, ground, inputs, extra=None):
    fields = {"op": operation["id"], "ground": ground, "observed": target_state(engine, operation, after=True),
              "way_back": engine.way_back(operation, None, inputs)}
    fields.update(extra or {})
    engine.log("completion", **fields)


def inputs_of(engine, op):
    start = (engine.state.starts.get(op) or [{}])[-1]
    return start.get("inputs") or []


def landed(engine, operation, cid):
    """OP-6's `landed` row."""
    op, kind = operation["id"], operation["kind"]
    if kind in ("build", "keep"):
        place = engine.state.starts[op][-1]["after"]["path"]
        settle_mode(engine, operation, place)
        last = bool(operation["construction"].get("last_record"))
        staged = [s for s in engine.state.steps.get(op) or [] if s.get("step") == "staged"][-1]
        try:
            # the object in place is the one the run built: for a file, its fingerprint is the one on record (LOG-2)
            if staged.get("sha256") is not None and fsio.sha256_hex(engine.fs.read(place)) != staged["sha256"]:
                raise Stop(UNCONFIRMED if last else "the published object is not the one on record", op, what=place)
            after_check(engine, operation)
        except OSError:
            raise Stop(UNCONFIRMED if last else "unreadable", op, what=place)
        except Stop as stop:
            if last:
                raise unconfirmed(stop, op, place)
            raise
        complete(engine, operation, "b", [], keep_fields(engine, operation) if kind == "keep" else None)
        return
    if kind == "create":
        after_check(engine, operation)
        answered_now = engine.state.answers[op][-1].get("inv") == engine.world.invocation
        complete(engine, operation, "a" if answered_now else "c", [])
        return
    if cid == "C3":
        start = engine.state.starts[op][-1]
        staged = [s for s in engine.state.steps.get(op) or [] if s.get("step") == "staged" and s["n"] > start["n"]]
        if staged and staged[-1].get("identity") == engine.fs.identity(start["thing"]["path"]):
            if start["thing"].get("mode") is not None and engine.fs.mode(start["thing"]["path"]) != start["thing"]["mode"]:
                engine.fs.chmod(start["thing"]["path"], start["thing"]["mode"])
            after_check(engine, operation)
            complete(engine, operation, "b", inputs_of(engine, op))
            return
    engine.log("status", op=op, status="not proven", observed=target_state(engine, operation, after=True),
               way_back={"offered": False, "reason": "not proven"})


def unconfirmed(stop, op, place):
    """KEEP-5: "an entry that cannot be confirmed leaves the run `stopped`, the form saying that the entry is at its place and
    unconfirmed, and the ways on are resume and close." Batch 42 (A98): "An after-check of the entry that the runner refuses
    is one that cannot confirm it: the form says both, the refusal by name (SEC-3) beside the entry at its place and
    unconfirmed, and the ways on stay resume and close." The reason kind stays KEEP-5's (its ways on, and no re-plan:
    `forms.status_lines`, `commands.replan`); the refusal is named beside the place."""
    if getattr(stop, "refused", False):
        found = Stop(UNCONFIRMED, op, what="%s; %s" % (place, stop.reason.get("kind")))
        found.refused, found.word = True, stop.word
        return found
    return Stop(UNCONFIRMED, op, what=place)


# ---- staging (OP-4, LOG-3) --------------------------------------------------------------------------------
def clear_staging(engine, op):
    """Remove an unpublished staged object, and nothing else: it lies under the run's own staging."""
    staged = enginemod.staging_of(engine.run_dir, op)
    if engine.fs.lexists(staged):
        engine.fs.rmtree(staged)


def no_link_on_the_way(engine, path, op):
    """A place is never reached through a symbolic link (C1, SEC-7)."""
    parent = os.path.dirname(path)
    if engine.fs.realpath(parent) != parent or engine.fs.islink(path):
        raise Stop("a link stands at the place or on the way to it", op)


def owner_only_tree(engine, root):
    for path in [root] + engine.fs.walk(root):
        if engine.fs.islink(path):
            continue
        mode = engine.fs.mode(path)
        if mode & 0o077:
            engine.fs.chmod(path, mode & 0o700)


def start_record(engine, operation, probe_answer, thing, after, inputs=None):
    op = operation["id"]
    fields = {"op": op, "start": len(engine.state.starts.get(op) or []) + 1, "probe": probe_answer, "thing": thing, "after": after}
    if inputs:
        fields["inputs"] = inputs
    checked = []
    for need in operation.get("needs") if isinstance(operation.get("needs"), list) else []:
        if need.get("level") == "passed":
            for provider, status in engine.state.providers_of(need["output"]):
                if status == "passed":
                    latest = engine.state.attempts[provider][-1]
                    checked.append({"check": provider, "attempt": latest["attempt"], "subject": latest["subject"]})
    if checked:
        fields["checked"] = checked          # the attempt that let it run, and the state that attempt read (OP-8)
    engine.log("start", **fields)
    engine.mark_risks(operation)


# ---- C1: publish from staging (build, keep) -----------------------------------------------------------------
def c1(engine, operation, answer):
    op, construction = operation["id"], operation["construction"]
    place = engine.value(operation["thing"]["place"], op)
    no_link_on_the_way(engine, place, op)
    start_record(engine, operation, answer, {"path": place, "exists": False}, {"path": place, "exists": True})
    folder = enginemod.staging_of(engine.run_dir, op)
    clear_staging(engine, op)
    engine.fs.mkdir(folder)
    staged = os.path.join(folder, "object")
    password_file = None
    extra = None
    try:
        if construction.get("last_record"):
            engine.fs.write_new(staged, last_record(engine).encode("utf-8"))
        elif isinstance(construction.get("copy"), dict):
            # a reverse that copies from a keep (EV-5, KEEP-4): the keep is read, never changed, and must be at its place,
            # of its recorded size and fingerprint, now as at the look (EV-7)
            copy = construction["copy"]
            if engine.fs.islink(copy["path"]) or not engine.fs.isfile(copy["path"]):
                raise Stop("a keep it needs is missing or fails its fingerprint", op)
            data = engine.fs.read(copy["path"])
            if len(data) != copy["size"] or fsio.sha256_hex(data) != copy["sha256"]:
                raise Stop("a keep it needs is missing or fails its fingerprint", op)
            engine.fs.write_new(staged, data)
        elif "files" in construction:
            root = staged
            single = construction.get("single_file")
            if not single:
                engine.fs.mkdir(root)
            for item in construction["files"]:
                target = root if single else os.path.join(root, item["rel"])
                if not single:
                    engine.fs.makedirs(os.path.dirname(target))
                content = item.get("text")
                if isinstance(content, dict) and "held_fields" in content:      # built from held ids (SEC-4, SEC-7)
                    content = fsio.pretty_json(dict((k, held_text(engine, v, op)) for k, v in content["held_fields"].items()))
                else:
                    content = str(engine.value(content, op))
                engine.fs.write_new(target, content.encode("utf-8"))
        else:
            command = engine.command(operation, construction["builder"])
            params = {construction.get("out_param", "out"): staged}
            connection = construction.get("connection")
            if isinstance(connection, dict):
                address = channels.read_connection(engine.world, engine.value(connection["file"], op), connection.get("keys") or [])
                if not address:
                    raise Stop("the connection is in no file on this machine", op)
                entry = engine.session.register.add(address, channels.address_components(address), None, "channel")
                from . import disproof
                spans = disproof.search(engine.fs, engine.run_dir, entry)
                if spans and not engine.session.register.hit(address).ref:
                    engine.log("disproof", **disproof.owed_for_channel(spans, "connection"))
                    raise Stop("a safe ground disproved", op)
                # a file a kill left here was removed by this invocation once its startup checks had passed (SEC-12)
                password_file = os.path.join(engine.run_dir, "private", rundir.PASSWORD_PREFIX + op)
                engine.fs.write_new(password_file, (address + "\n").encode("utf-8"))
                params[connection.get("slot", "passfile")] = password_file
            try:
                result = engine.call(command, op, extra=params, cwd=folder)
            finally:
                if password_file is not None:           # removed when the tool ends, however the call ended (SEC-2)
                    engine.fs.remove(password_file)
                    password_file = None
            if result.definite != "success":
                raise Stop("a command failed", op, command=result.shown, result=result.kind)
            if operation["kind"] == "keep":
                extra = keep_whole(engine, operation, staged, result)
        owner_only_tree(engine, folder)
    except OSError:
        raise Stop("the build failed", op)
    identity = engine.fs.identity(staged)
    digest = fsio.sha256_hex(engine.fs.read(staged)) if engine.fs.isfile(staged) else None
    staged_fields = {"op": op, "step": "staged", "identity": identity, "sha256": digest}
    if extra:
        staged_fields.update(extra)          # a keep's inventory, source, size and fingerprint, durable before the publish
    engine.log("step", **staged_fields)
    if engine.fs.volume(staged) != engine.fs.volume(os.path.dirname(place)):
        raise Stop("the place is on another volume", op)
    try:
        engine.fs.rename_noreplace(staged, place)
    except fsio.Exists:
        raise Stop("something is at the place", op)
    except OSError:
        raise Stop("the publish failed", op)
    settle_mode(engine, operation, place)
    engine.fs.rmdir(folder)
    after_check(engine, operation)
    complete(engine, operation, "a", [], extra)


def settle_mode(engine, operation, place):
    """The permissions an object has once it is at its place are its construction's to say (OP-4).
    They are given there, after the publish: while it is in staging everything is owner-only, so
    that a kill never leaves the run directory holding anything wider (RUN-4). Giving them again
    after a kill changes nothing that was already so."""
    mode = operation["construction"].get("mode")
    try:
        if mode is not None and engine.fs.mode(place) != int(mode):
            engine.fs.chmod(place, int(mode))
    except OSError:
        raise Stop("the permissions of the published object could not be set", operation["id"])


def held_text(engine, mark, op):
    """The content of a held value, for a file SEC-7 names for it. In memory only."""
    from . import protected
    found = engine.value(mark, op)
    if not isinstance(found, values.Held):
        return found
    content = protected.read(engine.fs, engine.run_dir, found.reference)
    return content.decode("utf-8")


def last_record(engine):
    """A run's last record, rendered from the journal alone (KEEP-5)."""
    state, manifest = engine.state, engine.manifest
    lines = ["%s: the record of run %s" % (manifest.get("kind", "").upper(), manifest.get("run"))]
    body = forms.status_lines(manifest, state, engine.run_dir, "ended", None, engine.journal.count(),
                              manifest.get("kind") == "sunset")
    lines += [l for l in body[4:] if not l.startswith("position: ")]
    return "\n".join(l for l in lines if not l.startswith("to go on")) + "\n"


def keep_whole(engine, operation, staged, result):
    """KEEP-1: the copy is compared with the inventory taken in the same state; what the provider
    returned of it is held, and the size and the fingerprint are the tool's own measure."""
    op, scope = operation["id"], operation.get("keep_scope") or {}
    data = engine.fs.read(staged)
    for check in scope.get("content_checks") or []:
        if check.get("check") == "count-lines":
            own = sum(1 for line in data.decode("utf-8", "replace").splitlines() if line.startswith(check.get("prefix", "")))
            held = result.held(check.get("field"))
            kept = result.fields.get(check.get("field"))
            reported = held if held is not None else (kept.safe if kept is not None else None)
            if reported != own:
                raise Stop("the keep is not whole", op)
    extra = {"size": len(data), "sha256": fsio.sha256_hex(data)}
    for key, field in (("inventory", scope.get("inventory_field")), ("source", scope.get("source_field"))):
        held = result.held(field) if field else None
        if held is None:
            raise Stop("the keep is not whole", op)
        extra[key] = engine.protect(op, fsio.canonical_json(held).encode("utf-8"), "values" if key == "inventory" else "held field",
                                    "the %s of a keep" % key)
    return {"keep": extra}


def keep_fields(engine, operation):
    """A keep found `landed`: what KEEP-1 has the completion record hold was made durable in the
    step record before the publish (LOG-2), and is carried from there."""
    op = operation["id"]
    start = engine.state.starts[op][-1]
    staged = [s for s in engine.state.steps.get(op) or [] if s.get("step") == "staged" and s["n"] > start["n"]]
    if not staged or not staged[-1].get("keep"):
        raise Stop("a keep landed without its inventory on record", op)
    return {"keep": staged[-1]["keep"]}


def recheck_keep(engine, operation):
    """KEEP-3: at its place, with the permissions SEC-7 requires, of the recorded size and
    fingerprint, and passing the content checks its row declares."""
    op = operation["id"]
    completion = engine.state.completions.get(op) or {}
    kept = completion.get("keep") or {}
    place = engine.value(operation["thing"]["place"], op)
    try:
        if not engine.fs.isfile(place) or engine.fs.mode(place) & 0o077:
            return False
        data = engine.fs.read(place)
    except OSError:
        return False
    if len(data) != kept.get("size") or fsio.sha256_hex(data) != kept.get("sha256"):
        return False
    for check in (operation.get("keep_scope") or {}).get("content_checks") or []:
        if check.get("check") == "count-lines":
            from . import protected
            try:
                want = protected.read(engine.fs, engine.run_dir, kept[check.get("record", "inventory")])
            except (protected.Unreadable, KeyError):
                return False
            own = sum(1 for line in data.decode("utf-8", "replace").splitlines() if line.startswith(check.get("prefix", "")))
            if fsio.canonical_json(own) != want.decode("utf-8"):
                return False
        if check.get("check") == "ends-with" and not data.endswith(str(check.get("text", "")).encode("utf-8")):
            return False
    return True


def barrier(engine, operation):
    """KEEP-3: no operation that retires anything starts unless, in the same invocation, every keep
    in the manifest is `done` and has just been checked again in full."""
    for op in engine.state.order:
        keep = engine.state.ops[op]
        if keep["kind"] != "keep":
            continue
        if engine.state.finals.get(op) != "done" or not recheck_keep(engine, keep):
            raise Stop("the barrier: a keep is not done or does not check out", operation["id"], what=op)


def tied(engine, operation):
    """KEEP-2: when the retirement runs, the identity in each required keep's completion record
    must equal the identity of its target as read then."""
    from . import protected
    op = operation["id"]
    required = operation.get("keeps_required") if isinstance(operation.get("keeps_required"), list) else []
    if not required:
        return
    spec = operation["thing"].get("identity_read")
    if not isinstance(spec, dict):
        raise Stop("a retirement names no read of its target's identity", op)
    result = engine.call(engine.command(operation, spec["command"]), op)
    now = result.held(spec.get("field")) if result.kind == "success" else None
    if now is None:
        raise Stop("unreadable", op, what="the target's identity")
    for keep in required:
        completion = engine.state.completions.get(keep) or {}
        try:
            recorded = protected.read(engine.fs, engine.run_dir, (completion.get("keep") or {})["source"])
        except (protected.Unreadable, KeyError):
            raise Stop("a keep's record cannot be read", op, what=keep)
        if fsio.canonical_json(now).encode("utf-8") != recorded:
            raise Stop("the target is not the thing its keep copied", op, what=keep)


# ---- C2: a provider's create ---------------------------------------------------------------------------------
def c2(engine, operation, answer):
    """A create: its start record, then its send. `answer` is the probe's: `ready`, or `not landed` where the step record
    of the runner's refusal of an earlier send follows the start record before this one (OP-6; A99), the run having his
    word to go on (RUN-10), as every invocation after the first that applies an effect has."""
    op, construction = operation["id"], operation["construction"]
    start_record(engine, operation, answer, {"word": "absent"}, {"word": "made"})
    command = engine.command(operation, construction["command"])
    try:
        result = engine.call(command, op)
    except Stop as stop:
        if stop.refused and stop.word is not None and (command.get("declaration") or {}).get("via") != "request":
            # LOG-2 (batch 43, A99): "Where the runner refuses a create's send before any child is created (SEC-3), a step
            # record of that refusal, naming the create and saying that no child was created, is written and synced before
            # the run stops; it is written in that case and in no other, so it stands only where no request left the tool."
            # The runner refuses before it creates a child (`runner.run`), so no request left the tool. A send that is a
            # request of the frame's own (SEC-2) is no child of the runner's: no such record is written for it, and the
            # create stays outstanding (report-15, question 31). A kill before this record leaves the create outstanding
            # (OP-7); the record that would carry a register entry is not written (SEC-12), and the create stays so too
            engine.log("step", op=op, step="send-refused", command=command.get("name"), refusal=stop.word, child="none created")
        raise
    record_answer(engine, operation, result, "call")


def record_answer(engine, operation, result, source):
    """A create's answer: a definite success is written as the answer record and the create is then
    `landed`; a definite refusal the row names as an alternative is `refused`; any other definite
    refusal stops; an indefinite answer leaves the create outstanding (OP-7)."""
    op, construction = operation["id"], operation["construction"]
    if result.definite == "success":
        held = result.held(construction.get("id_field", "id"))
        if held is None:
            raise Stop("an outstanding create", op)
        reference = engine.protect(op, str(held).encode("utf-8"), "held field", "the id of what %s made" % op)
        engine.log("answer", op=op, result="success", held=reference, source=source)
        after_check(engine, operation)
        complete(engine, operation, "a" if source == "call" else "c", [])
        return
    if result.alternative and result.kind in (construction.get("alternatives") or []):
        engine.log("status", op=op, status="refused", reason={"result": result.kind},
                   way_back=engine.no_way_back(operation, "refused"))
        return
    if result.definite == "refusal":
        raise Stop("the provider refused", op, command=result.shown, result=result.kind)
    raise Stop("an outstanding create", op)


def resolve_outstanding(engine, operation):
    """OP-7's first way: the provider answers for that very request. Returns `made`, `nothing`, or None."""
    op, construction = operation["id"], operation["construction"]
    lost = operation.get("lost_answer") if isinstance(operation.get("lost_answer"), dict) else {}
    if lost.get("way") != "status-read":
        return None
    result = engine.call(engine.command(operation, lost["command"]), op)
    if result.kind != "success":
        return None
    word = result.safe().get(lost.get("field", "made"))
    if word == lost.get("made_word", "made"):
        held = result.held(construction.get("id_field", "id"))
        if held is None:
            return None
        reference = engine.protect(op, str(held).encode("utf-8"), "held field", "the id of what %s made" % op)
        engine.log("answer", op=op, result="success", held=reference, source="status-read")
        after_check(engine, operation)
        complete(engine, operation, "c", [])
        return "made"
    if word == lost.get("nothing_word", "nothing"):
        return "nothing"
    return None


# ---- C3: swap ------------------------------------------------------------------------------------------------
def edited(data, edit, value_of):
    """The new bytes of a file after one declared edit; None where the edit does not apply."""
    text = data.decode("utf-8")
    kind = edit.get("kind")
    if kind == "append-line":
        line = str(value_of(edit["line"]))
        return (text + ("" if text.endswith("\n") or not text else "\n") + line + "\n").encode("utf-8")
    if kind == "remove-line":
        span = str(value_of(edit["line"])).split("\n")
        lines, ended = reads.file_lines(text)
        found = reads.span_at(lines, span)
        if len(found) != 1:
            return None
        return reads.join_lines(lines[:found[0]] + lines[found[0] + len(span):], ended).encode("utf-8")
    if kind == "replace":
        old, new = str(value_of(edit["old"])), str(value_of(edit["new"]))
        if text.count(old) != 1:
            return None
        return text.replace(old, new).encode("utf-8")
    if kind == "insert-between":
        # EV-6, `in place`: "the recorded lines on each side are found next to each other exactly once and, for a file the
        # row marks as ordered ..., everything before that point is as recorded. For a span that stood at its file's start
        # or at its end, the file's start, or its end, stands as the recorded line on that side ...: the span goes back
        # only where the recorded line on the other side stands at that edge of the file and the pair is found exactly
        # once, and, for an ordered file, everything before that point is as recorded"
        above, below, line = str(value_of(edit["above"])), str(value_of(edit["below"])), str(value_of(edit["line"]))
        lines, ended = reads.file_lines(text)
        if above == enginemod.EDGE_START and below == enginemod.EDGE_END:
            places = [0] if not lines else []
        elif above == enginemod.EDGE_START:
            places = [0] if lines and lines[0] == below else []
        elif below == enginemod.EDGE_END:
            places = [len(lines)] if lines and lines[-1] == above else []
        else:
            places = [i + 1 for i in reads.span_at(lines, [above, below])]
        if len(places) != 1:
            return None
        at = places[0]
        if edit.get("ordered") is not None and edit.get("before_sha256") is not None:
            head = "".join(l + "\n" for l in lines[:at - 1 if above != enginemod.EDGE_START else 0])
            if fsio.sha256_hex(head.encode("utf-8")) != edit["before_sha256"]:
                return None
        if edit.get("ordered") and edit.get("head") is not None:
            # everything before that point is as recorded: the lines before the span, the line above included
            if "".join(l + "\n" for l in lines[:at]) != str(value_of(edit["head"])):
                return None
        return reads.join_lines(lines[:at] + line.split("\n") + lines[at:], ended or not lines).encode("utf-8")
    return None


def placement_cannot_be_met(engine, operation):
    """A restore's putting back of text (EV-6): the reverse's declared edit read against the file as it stands, in memory (a
    probe only reads); the stop's words where the edit cannot be made there, None where it can or where the operation is
    no reverse that swaps a file's text."""
    construction = operation.get("construction") or {}
    if (not operation.get("reverse_of") or construction.get("id") != "C3" or not isinstance(construction.get("edit"), dict)
            or operation["thing"].get("place") is None):
        return None
    op = operation["id"]
    path = engine.value(operation["thing"]["place"], op)
    if not engine.fs.isfile(path):
        return None
    if edited(engine.fs.read(path), construction["edit"], lambda mark: held_text(engine, mark, op)) is not None:
        return None
    return placement_unmet(engine.value, operation, path, op)


def placement_unmet(value, operation, path, op):
    """EV-6: where the declared placement cannot be met, the form names the file, the place and the protected records, and
    shows no text of the file or of a record."""
    edit = (operation.get("construction") or {}).get("edit") or {}
    records = []

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("record"), dict) and node["record"].get("record"):
                records.append("%s (%s)" % (node["record"]["record"], node["record"].get("label", "")))
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(edit)
    place = {"replace": "where its recorded after-image occurs exactly once", "insert-between": "between its recorded neighbours, "
             "next to each other exactly once" + (", the head before them as recorded" if edit.get("ordered") else ""),
             "append-line": "at the end"}.get(edit.get("kind"), "its declared placement")
    return "the declared placement cannot be met: the file %s; the place: %s; the records: %s" % (path, place, ", ".join(records) or "none")


def c3(engine, operation, answer):
    op, construction = operation["id"], operation["construction"]
    path = engine.value(operation["thing"]["place"], op)
    no_link_on_the_way(engine, path, op)
    try:
        before = engine.fs.read(path)
        mode = engine.fs.mode(path)
        identity = engine.fs.identity(path)
    except OSError:
        raise Stop("unreadable", op)
    new = edited(before, construction["edit"], lambda mark: held_text(engine, mark, op))
    if new is None:
        raise Stop("foreign", op, what=placement_unmet(engine.value, operation, path, op))
    inputs = engine.save_reverse_inputs(operation)
    start_record(engine, operation, answer, {"path": path, "exists": True, "identity": identity, "sha256": fsio.sha256_hex(before), "mode": mode},
                 {"path": path, "exists": True, "sha256": fsio.sha256_hex(new)}, inputs)
    folder = enginemod.staging_of(engine.run_dir, op)
    clear_staging(engine, op)
    engine.fs.mkdir(folder)
    staged = os.path.join(folder, "object")
    engine.fs.write_new(staged, new)
    if engine.fs.volume(staged) != engine.fs.volume(path):
        raise Stop("the place is on another volume", op)
    engine.log("step", op=op, step="staged", identity=engine.fs.identity(staged), sha256=fsio.sha256_hex(new))
    lock = engine.fs.lock_exclusive(path, create=False)       # the file's own lock, held only around the one change
    if lock is None:
        raise Stop("the file's lock is held", op)
    try:
        if fsio.sha256_hex(engine.fs.read(path)) != fsio.sha256_hex(before):
            engine.fs.unlock(lock, path, remove=False)
            lock = None
            raise Stop("the file changed before the swap", op, what=path)
        engine.fs.swap(staged, path)
        engine.fs.chmod(path, mode)                            # the new file takes the old file's permissions
    except OSError:
        if lock is not None:
            engine.fs.unlock(lock, path, remove=False)
        raise Stop("the swap failed", op)
    engine.fs.unlock(lock, path, remove=False)
    engine.fs.rmdir(folder)
    after_check(engine, operation)
    complete(engine, operation, "a", inputs)


# ---- C4, C5, C6: one request of a store or a provider ----------------------------------------------------------
def c456(engine, operation, answer):
    op, construction, thing = operation["id"], operation["construction"], operation["thing"]
    inputs = engine.save_reverse_inputs(operation)
    start_record(engine, operation, answer, {"word": str(thing.get("before_word", "before"))[:64]},
                 {"word": str(thing.get("after_word", "after"))[:64]}, inputs)
    result = engine.call(engine.command(operation, construction["command"]), op)
    if result.definite != "success":
        raise Stop("a command failed", op, command=result.shown, result=result.kind)
    after_check(engine, operation)
    complete(engine, operation, "a", inputs)


# ---- C7: exclusive move of an identified thing -------------------------------------------------------------------
def c7(engine, operation, answer):
    op, construction = operation["id"], operation["construction"]
    source = engine.value(operation["thing"]["place"], op)
    target = engine.value(construction["to"], op)
    no_link_on_the_way(engine, target, op)
    identity = engine.fs.identity(source)
    if identity is None:
        raise Stop("foreign", op, what=source)
    inputs = engine.save_reverse_inputs(operation)
    start_record(engine, operation, answer, {"path": source, "exists": True, "identity": identity, "target": target},
                 {"path": target, "exists": True, "identity": identity}, inputs)
    try:
        engine.fs.rename_noreplace(source, target)
    except fsio.Exists:
        raise Stop("something is at the target", op, what=target)
    except OSError:
        raise Stop("the move failed", op)
    if engine.fs.identity(target) != identity:
        raise Stop("the thing moved is not the thing read: both places are named", op, what="%s and %s" % (source, target))
    after_check(engine, operation)
    complete(engine, operation, "a", inputs)


HANDLERS = {"C1": c1, "C2": c2, "C3": c3, "C4": c456, "C5": c456, "C6": c456, "C7": c7}
