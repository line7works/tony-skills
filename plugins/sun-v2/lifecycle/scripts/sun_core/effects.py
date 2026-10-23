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
import json
import os
import re

from . import channels, engine as enginemod, forms, fsio, protected, reads, runner, values

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
    state = _target_state(engine, operation, after)
    spec = operation["thing"].get("commit_of")
    if after and isinstance(spec, dict):
        # a branch's commit, read by the tool from the repository itself (SEC-4's hash row), observed with the completion so
        # that an output field `{"observed": "commit"}` binds it (G19-10)
        from . import commitscan, gitread
        try:
            found = commitscan.repository(engine.session, engine.value(spec["repo"], operation["id"])).ref("refs/heads/" + str(spec["ref"]))
        except (commitscan.Unreadable, gitread.Unreadable, OSError, ValueError):
            found = None
        if found:
            state["commit"] = found
    return state


def _target_state(engine, operation, after=False):
    thing = operation["thing"]
    cid = (operation.get("construction") or {}).get("id") if isinstance(operation.get("construction"), dict) else None
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
            if start["thing"].get("exists") is False and not engine.fs.lexists(path):
                return "not landed"                # a change of an absent file: the before-state is the absence (A147)
            if (operation["construction"].get("edit") or {}).get("kind") == "folder":
                # a folder published as C1 publishes (A154): the same thing where it has the staged identity on record
                staged = [s for s in state.steps.get(op) or [] if s.get("step") == "staged" and s["n"] > start["n"]]
                at = engine.fs.identity(path) if engine.fs.isdir(path) and not engine.fs.islink(path) else None
                return "landed" if at is not None and staged and staged[-1].get("identity") == at else "foreign"
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
            if start["thing"].get("exists") is False:
                # G24-4 (OP-4, OP-6's `landed` row): a thing whose before-state was its absence, published as C1 publishes,
                # takes its construction's modes as `c3_absent` and `c3_absent_folder` give them, a kill having come between the
                # publish and the giving: the folder's mode, and its `.gitkeep`'s 0644
                place = start["thing"]["path"]
                settle_mode(engine, operation, place)
                keep = os.path.join(place, ".gitkeep")
                if ((operation["construction"].get("edit") or {}).get("gitkeep") and engine.fs.isfile(keep) and not engine.fs.islink(keep)
                        and engine.fs.mode(keep) != 0o644):
                    engine.fs.chmod(keep, 0o644)
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
        elif construction.get("copy_folder") is not None:
            extra = copy_folder(engine, operation, staged)
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
                # SEC-2's private password file, built for each command that declares its slot and removed when that command
                # ends, however it ends (G20-1, `calls.call`); a file a kill left here was removed by this invocation once its
                # startup checks had passed (SEC-12)
                password_file = (address, connection.get("slot", "passfile"), op)
            keep_reads = before_the_copy(engine, operation, password_file) if operation["kind"] == "keep" else {}
            run_in = folder
            if construction.get("in_folder"):
                # G21-4 (rise's M-6): the staged object is an empty folder, and the build's program runs in it
                engine.fs.mkdir(staged)
                run_in = staged
            result = engine.call(command, op, extra=params, cwd=run_in, connection=password_file,
                                 hosting_env=operation["kind"] == "keep" and construction.get("hosting_env") is True)
            if keep_reads.get("inventory_spec"):
                keep_reads["after"], keep_reads["after_apart"] = returned_keys(engine, operation, keep_reads["inventory_spec"])
            if result.definite != "success":
                raise Stop("a command failed", op, command=result.shown, result=result.kind)
            scope = operation.get("keep_scope") if isinstance(operation.get("keep_scope"), dict) else {}
            pairs_spec = (scope.get("inventory_from") or {}).get("pairs") if isinstance(scope.get("inventory_from"), dict) else None
            if operation["kind"] == "keep" and pairs_spec:
                pairs = result.held(pairs_spec)
                if not isinstance(pairs, list):
                    raise Stop("the keep is not whole", op)
                if engine.fs.lexists(staged):
                    engine.fs.remove(staged)
                engine.fs.write_new(staged, encode_pairs(pairs))       # the frame writes the held values, in staging (SEC-7)
            if operation["kind"] == "keep":
                cli = (scope.get("inventory_from") or {}).get("cli_keys") if isinstance(scope.get("inventory_from"), dict) else None
                if isinstance(cli, list) and cli and engine.fs.isfile(staged):
                    drop_cli_keys(engine, staged, cli, str(scope["inventory_from"].get("copy_keys", "=")),
                                  list(keep_reads.get("before") or []) + list(keep_reads.get("apart") or []),
                                  scope["inventory_from"].get("cli_secrets") or [], op)
                extra = keep_whole(engine, operation, staged, result, keep_reads)
            if construction.get("in_folder"):
                no_repository(engine, staged)
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


def no_repository(engine, staged):
    """Every `.git` the build's program made in staging, removed before the publish: none is ever published, so no
    scaffolder repository write reaches the project (G21-4; the control room's reading, A153)."""
    while True:
        found = [p for p in engine.fs.walk(staged) if os.path.basename(p) == ".git"]
        if not found:
            return
        if engine.fs.isdir(found[0]) and not engine.fs.islink(found[0]):
            engine.fs.rmtree(found[0])
        else:
            engine.fs.remove(found[0])


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
    # wrapped in the lane's fixed head lines, settled by the look (v1's frontmatter and title; G20-5)
    lines = list(manifest.get("last_record_head") or [])
    lines.append("%s: the record of run %s" % (manifest.get("kind", "").upper(), manifest.get("run")))
    body = forms.status_lines(manifest, state, engine.run_dir, "ended", None, engine.journal.count(),
                              manifest.get("kind") == "sunset")
    lines += [l for l in body[4:] if not l.startswith("position: ")]
    lines += not_saved_lines(engine)
    return "\n".join(l for l in lines if not l.startswith("to go on")) + "\n"


def not_saved_lines(engine):
    """The tombstone's lines for the keys a keep set apart: each named by its key, never its value, as not saved (SEC-6 as the
    owner's ruling A148 words it: "in the preview and the tombstone"). The one place a form names what a protected record
    holds; the record is the run's own `apart` list of keys (G23-8)."""
    out, changes = [], engine.manifest.get("form_changes") or {}
    for op in engine.state.order:
        apart = ((engine.state.completions.get(op) or {}).get("keep") or {}).get("apart")
        if not apart:
            continue
        what = forms.what_of(engine.state.ops[op], "status", engine.state)
        for key in json.loads(protected.read(engine.fs, engine.run_dir, apart).decode("utf-8")):
            out.append(forms.line_for("not saved", changes, name=key, what=what))
    return out


def held_list(engine, operation, spec):
    """A read command's held list field (G19-25), or a stop where it cannot be read."""
    result = engine.call(engine.command(operation, spec["command"]), operation["id"])
    found = result.held(spec.get("field")) if result.kind == "success" else None
    if not isinstance(found, list):
        raise Stop("the keep is not whole", operation["id"])
    return found


def split_keys(result, spec, env=None):
    """(returned, apart) from one read of a keep's inventory command, or None where its lists cannot be read: the held list of
    keys, filtered to the row's environment by a parallel target list where `env` is given (G23-6), and split by a parallel
    type list where the row names the type of a key listed apart (`apart`). Shared by the keep and by the look (G23-8)."""
    keys = result.held(spec.get("field")) if result.kind == "success" else None
    if not isinstance(keys, list):
        return None
    apart = spec.get("apart") if isinstance(spec.get("apart"), dict) else None
    types = result.held(apart.get("field")) if apart is not None else None
    if apart is not None and (not isinstance(types, list) or len(types) != len(keys)):
        return None
    target = spec.get("target") if isinstance(spec.get("target"), dict) else None
    if target is not None:
        targets = result.held(target.get("field"))
        if not isinstance(targets, list) or len(targets) != len(keys):
            return None
        mine = [env in t if isinstance(t, list) else env == t for t in targets]
        keys = [k for k, kept in zip(keys, mine) if kept]
        types = [t for t, kept in zip(types, mine) if kept] if types is not None else None
    if apart is None:
        return keys, []
    return ([k for k, t in zip(keys, types) if t != apart.get("equals")], [k for k, t in zip(keys, types) if t == apart.get("equals")])


def returned_keys(engine, operation, spec):
    """(the keys whose values the provider returns, the keys it never returns), from the keep's inventory command read now
    (`split_keys`); a read whose lists cannot be read fails the keep."""
    result = engine.call(engine.command(operation, spec["command"]), operation["id"])
    env = None
    target = spec.get("target") if isinstance(spec.get("target"), dict) else None
    if target is not None:
        env = engine.value(target.get("holds"), operation["id"])
        if isinstance(env, values.Held):
            env = protected.read(engine.fs, engine.run_dir, env.reference).decode("utf-8")      # compared in memory (SEC-4)
    found = split_keys(result, spec, env)
    if found is None:
        raise Stop("the keep is not whole", operation["id"])
    return found


def before_the_copy(engine, operation, connection=None):
    """What a keep reads just before its builder runs: the inventory, where the row has it read by a command before and
    after the builder (G19-25; A148), and the source's identity, where the copying tool reports none, read over the same
    connection or link immediately before the copy (KEEP-1 as A147 words it; G19-18)."""
    scope = operation.get("keep_scope") or {}
    out = {}
    spec = scope.get("inventory_from")
    if isinstance(spec, dict) and spec.get("command"):
        out["inventory_spec"] = spec
        out["before"], out["apart"] = returned_keys(engine, operation, spec)
    read = scope.get("source_identity_read")
    if not scope.get("source_field") and isinstance(read, dict):
        result = engine.call(engine.command(operation, read["command"]), operation["id"], connection=connection)
        out["source"] = result.held(read.get("field")) if result.kind == "success" else None
    return out


BREAKS = "\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029"


def encode_pairs(pairs):
    """Key and text pairs as one `KEY="value"` line each (G19-29; the reviewer's N3): the value double-quoted, a backslash, a
    double quote and every line break escaped, so that one entry is always one line and the file decodes back whole."""
    out = []
    for key, value in pairs:
        text = []
        for ch in value:
            if ch in ("\\", '"'):
                text.append("\\" + ch)
            elif ch == "\n":
                text.append("\\n")
            elif ch == "\r":
                text.append("\\r")
            elif ch in BREAKS:
                text.append("\\u%04x" % ord(ch))
            else:
                text.append(ch)
        out.append('%s="%s"\n' % (key, "".join(text)))
    return "".join(out).encode("utf-8")


def decode_pairs(data):
    """The pairs a file `encode_pairs` wrote holds, or None where it is not such a file."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if text and not text.endswith("\n"):
        return None
    out = []
    for line in text.split("\n")[:-1]:
        key, eq, rest = line.partition("=")
        if not eq or not key or len(rest) < 2 or rest[0] != '"' or rest[-1] != '"':
            return None
        body, value, i = rest[1:-1], [], 0
        while i < len(body):
            ch = body[i]
            if ch == '"':
                return None
            if ch == "\\":
                nxt = body[i + 1:i + 2]
                if nxt in ("\\", '"'):
                    value.append(nxt)
                    i += 2
                elif nxt == "n":
                    value.append("\n")
                    i += 2
                elif nxt == "r":
                    value.append("\r")
                    i += 2
                elif nxt == "u" and len(body) >= i + 6:
                    try:
                        value.append(chr(int(body[i + 2:i + 6], 16)))
                    except ValueError:
                        return None
                    i += 6
                else:
                    return None
                continue
            value.append(ch)
            i += 1
        out.append([key, "".join(value)])
    return out


def copy_keys(data, mark):
    """A copy's own keys: the text before `mark` on each line that holds it and is no comment."""
    out = []
    for line in data.decode("utf-8", "replace").split("\n"):
        if mark in line and not line.lstrip().startswith("#"):
            out.append(line.split(mark, 1)[0].strip())
    return out


def held_cli_secrets(engine, op, lines, secrets, mark):
    """J7 (D8; SEC-12): the values of the dropped lines whose key the row names among the CLI's secrets (`cli_secrets`),
    entered in the withheld register as they are read, before anything is written, so that every later output of this
    invocation withholds them; the line's text as the copy holds it (quoted, escaped) is a component of the entry. Where one
    already stands in the run's own records (a description that equals it, say), the disproof is recorded, durable, naming
    where it rests and holding no value, and the run stops on it: every later invocation reads that record back into its
    register (SEC-12's startup read), and no earlier record is rewritten. Each such secret gets its own record, all of them
    written before the one stop (E17, D8's closing rule). Returns the stop to raise, or None."""
    from . import disproof
    marker = mark.encode("utf-8")
    owed, entries = [], []
    for line in lines:
        key, _sep, raw = line.partition(marker)
        if key.strip().decode("utf-8", "replace") not in secrets:
            continue
        raw = raw.strip().decode("utf-8", "replace")
        pairs = decode_pairs((key.strip().decode("utf-8", "replace") + "=" + raw + "\n").encode("utf-8"))
        value = pairs[0][1] if pairs else raw
        entry = engine.session.register.add(value, [raw] if raw != value else [], None, "channel")
        if entry is None:
            continue
        spans = disproof.search(engine.fs, engine.run_dir, entry)
        if spans and not engine.session.register.hit(value).ref and entry not in entries:
            entries.append(entry)
            owed.append(spans)
    for spans in owed:
        engine.log("disproof", **disproof.owed_for_channel(spans, "cli-added secret"))
    if owed:
        return Stop("a safe ground disproved", op)
    return None


def drop_cli_keys(engine, staged, names, mark, inventory=(), secrets=(), op=None):
    """J6g (L-15; the owner's ruling): the lines of the keys a provider's own tool adds to its copy of a hosting environment,
    which no project variable is (vercel's VERCEL_OIDC_TOKEN and its system and build entries, J6h), dropped from the staged
    copy before the keep is checked, so that no kept copy holds one. Exactly the keys the row names in `cli_keys`, and only
    where the environment's own inventory (the read just before the pull, `inventory`) does not hold that key: a name the
    project defines itself is a project key and stays (J6h, the Board's binding). Every other line stays as it was, and any
    other key the copy holds still fails the keep. The staged object is written again in staging, never elsewhere."""
    names = set(names) - set(inventory)
    data = engine.fs.read(staged)
    lines = data.split(b"\n")
    marker = mark.encode("utf-8")
    kept = [l for l in lines if l.lstrip().startswith(b"#") or marker not in l
            or l.split(marker, 1)[0].strip().decode("utf-8", "replace") not in names]
    stop = held_cli_secrets(engine, op, [l for l in lines if l not in kept], set(secrets), mark) if secrets else None
    if len(kept) != len(lines):
        engine.fs.remove(staged)
        engine.fs.write_new(staged, b"\n".join(kept))
    if stop is not None:
        raise stop


def keep_whole(engine, operation, staged, result, reads_before=None):
    """KEEP-1: the copy is compared with the inventory taken in the same state; what the provider
    returned of it is held, and the size and the fingerprint are the tool's own measure. The inventory may come from the
    copy's own lines with a declared prefix, or from a read made just before and again just after the builder, equal both
    times and equal to the copy's own keys; any difference fails the keep (G19-25)."""
    op, scope = operation["id"], operation.get("keep_scope") or {}
    reads_before = reads_before or {}
    data = engine.fs.read(staged)
    for check in scope.get("content_checks") or []:
        if check.get("check") == "count-lines":
            own = sum(1 for line in data.decode("utf-8", "replace").splitlines() if line.startswith(check.get("prefix", "")))
            held = result.held(check.get("field"))
            kept = result.fields.get(check.get("field"))
            reported = held if held is not None else (kept.safe if kept is not None else None)
            if reported != own:
                raise Stop("the keep is not whole", op)
        elif not text_checks_hold(data, check):
            raise Stop("the keep is not whole", op)        # checked as the keep is built, not only at the barrier (G23-9)
    extra = {"size": len(data), "sha256": fsio.sha256_hex(data)}
    spec = scope.get("inventory_from") if isinstance(scope.get("inventory_from"), dict) else {}
    taken = {}
    if spec.get("lines") is not None:
        taken["inventory"] = [l for l in data.decode("utf-8", "replace").split("\n") if l.startswith(str(spec["lines"]))]
    elif spec.get("pairs"):
        # a keep built from an answer's key and text pairs (G19-29): its inventory is that answer's keys, and the staged copy
        # decodes back to the answer's pairs whole, or the keep fails
        pairs = result.held(spec["pairs"])
        if not isinstance(pairs, list) or decode_pairs(data) != [list(p) for p in pairs]:
            raise Stop("the keep is not whole", op)
        taken["inventory"] = [p[0] for p in pairs]
        unreturned = (getattr(result, "not_returned", None) or {}).get(spec["pairs"]) or []
        if unreturned:
            # G23-7 (KEEP-1, A148): a member whose value the provider did not return is set apart by the parallel type list,
            # where its type is the one the row names; any other such member fails the keep
            apart = spec.get("apart") if isinstance(spec.get("apart"), dict) else {}
            types = result.held(apart.get("field")) if apart else None
            if (not isinstance(types, list) or len(types) != len(pairs) + len(unreturned)
                    or any(index >= len(types) or types[index] != apart.get("equals") for index, _key in unreturned)):
                raise Stop("the keep is not whole", op)
            extra["apart"] = engine.protect(op, fsio.canonical_json(sorted(k for _i, k in unreturned)).encode("utf-8"), "values",
                                            "the keys whose values the provider never returns")
    elif spec.get("command"):
        # a hosting environment's variables alone (KEEP-1 as A148 and A149 word it): the returned-value keys read just before
        # and again just after the pull, the two equal, and each of them present in the copy; a key whose value the provider
        # never returns (`apart`) is listed apart and fails nothing; any other key of the copy fails the keep
        before, after = reads_before.get("before"), reads_before.get("after")
        apart = sorted(set(reads_before.get("apart") or []))
        own = copy_keys(data, spec.get("copy_keys", "="))
        # the keys listed apart are compared across the two reads too (G23-F3): either list changing fails the keep
        if (before is None or after is None or sorted(before) != sorted(after) or not set(before) <= set(own)
                or sorted(set(reads_before.get("apart") or [])) != sorted(set(reads_before.get("after_apart") or []))
                or not set(own) <= set(before) | set(apart)):
            raise Stop("the keep is not whole", op)
        taken["inventory"] = before
        if apart:
            extra["apart"] = engine.protect(op, fsio.canonical_json(apart).encode("utf-8"), "values", "the keys whose values the provider never returns")
    if "source" in reads_before:
        taken["source"] = reads_before["source"]
    for key, field in (("inventory", scope.get("inventory_field")), ("source", scope.get("source_field"))):
        held = taken[key] if key in taken else (result.held(field) if field else None)
        if held is None:
            raise Stop("the keep is not whole", op)
        extra[key] = engine.protect(op, fsio.canonical_json(held).encode("utf-8"), "values" if key == "inventory" else "held field",
                                    "the %s of a keep" % key)
    return {"keep": extra}


def folder_listing(engine, folder, op=None):
    """A folder of this machine by its files' names and fingerprints, in a fixed order ([[name, sha256], ...]), and their size
    in bytes, the tool's own measure; a link in it is no file the keep can copy whole."""
    listing, size = [], 0
    for path in engine.fs.walk(folder):
        if engine.fs.islink(path):
            raise Stop("the keep is not whole", op)
        if engine.fs.isfile(path):
            data = engine.fs.read(path)
            listing.append([os.path.relpath(path, folder), fsio.sha256_hex(data)])
            size += len(data)
    return sorted(listing), size


def copy_folder(engine, operation, staged):
    """A keep of a folder of this machine copied whole by the tool, in a row RK18 names (G21-10; KEEP-1 as A151 words it): the
    folder's file names and fingerprints read just before and again just after the copy, the two equal and equal to the
    copy's own, and the folder's identity the same before and after. The inventory is that listing, in a protected record;
    the size and the fingerprint (of the listing) are the tool's own measure."""
    op = operation["id"]
    source = engine.value(operation["construction"]["copy_folder"], op)
    identity = engine.fs.identity(source)
    if identity is None or not engine.fs.isdir(source):
        raise Stop("the keep is not whole", op)
    before, size = folder_listing(engine, source, op)
    engine.fs.mkdir(staged)
    for rel, _digest in before:
        target = os.path.join(staged, rel)
        engine.fs.makedirs(os.path.dirname(target))
        engine.fs.write_new(target, engine.fs.read(os.path.join(source, rel)))
    after, _ = folder_listing(engine, source, op)
    own, _ = folder_listing(engine, staged, op)
    if before != after or own != before or engine.fs.identity(source) != identity:
        raise Stop("the keep is not whole", op)
    text = fsio.canonical_json(before).encode("utf-8")
    return {"keep": {"size": size, "sha256": fsio.sha256_hex(text),
                     "inventory": engine.protect(op, text, "values", "the names and fingerprints of a folder kept whole"),
                     "source": engine.protect(op, fsio.canonical_json(identity).encode("utf-8"), "values", "the identity of the folder kept")}}


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
    if (operation.get("construction") or {}).get("copy_folder") is not None:
        # a folder kept whole (G21-10): owner-only throughout, and its listing and size as recorded
        try:
            if engine.fs.islink(place) or not engine.fs.isdir(place) or any(engine.fs.mode(p) & 0o077 for p in [place] + engine.fs.walk(place)):
                return False
            listing, size = folder_listing(engine, place, op)
        except (OSError, Stop):
            return False
        return size == kept.get("size") and fsio.sha256_hex(fsio.canonical_json(listing).encode("utf-8")) == kept.get("sha256")
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
        if not text_checks_hold(data, check):
            return False
    return True


def _named(line, prefix):
    """The whole name a line of a prefix carries (G23-F2): what follows the prefix to the first space or opening parenthesis
    that stands outside double quotes, a quoted part kept whole with its spaces (`""` inside quotes is one quote). None where
    the name cannot be read whole: empty, or a quote left open."""
    rest, quoted, i, out = line[len(prefix):], False, 0, []
    while i < len(rest):
        ch = rest[i]
        if ch == '"':
            if quoted and rest[i + 1:i + 2] == '"':
                out.append('""')
                i += 2
                continue
            quoted = not quoted
        elif not quoted and ch in " (":
            break
        out.append(ch)
        i += 1
    name = "".join(out)
    return None if quoted or not name else name


ALPHABETS = {"letters and digits": frozenset(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}


def text_checks_hold(data, check):
    """A keep's content checks that read the copy alone (KEEP-1, KEEP-3; G23-9): `ends-with` its declared text, or, where
    the check names a `then_line`, that text followed by one line of the line's fixed `prefix` and a non-empty key of its
    named `alphabet`, then one or two newlines, as the end (J3b: pg_dump 17.6 and later write `\\unrestrict <key>` after
    their last line); and `has-section`, each line of `prefix` paired with a line of `section` carrying the same name (each
    table the copy creates has its data section in the copy; a partitioned parent, which holds no rows, excepted: J6f). A
    check of another kind is not this function's and holds here."""
    if check.get("check") == "ends-with":
        text = str(check.get("text", "")).encode("utf-8")
        if data.endswith(text):
            return True
        then = check.get("then_line") if isinstance(check.get("then_line"), dict) else {}
        alphabet, start = ALPHABETS.get(then.get("alphabet")), text + str(then.get("prefix", "")).encode("utf-8")
        if alphabet is None or not then.get("prefix") or start not in data:
            return False
        key = data[data.rindex(start) + len(start):]
        key = key[:-2] if key.endswith(b"\n\n") else key[:-1] if key.endswith(b"\n") else b""
        return bool(key) and all(byte in alphabet for byte in key)
    if check.get("check") == "has-section":
        lines = data.decode("utf-8", "replace").splitlines()
        prefix, section = str(check.get("prefix", "")), str(check.get("section", ""))
        if not prefix or not section:
            return False                      # a pairing with a side missing proves nothing, and fails the keep
        made = []
        for index, line in enumerate(lines):
            if not line.startswith(prefix):
                continue
            # J6f (L-13): a CREATE TABLE whose own statement ends, at its closing `;`, in a `PARTITION BY` clause is a
            # partitioned parent: Postgres keeps no rows in it and pg_dump writes no data section for it (Supabase's
            # `realtime.messages`). A statement that cannot be read whole to its `;` fails the keep (G23-F2)
            end = next((j for j in range(index, len(lines)) if lines[j].rstrip().endswith(";")), None)
            if end is None:
                return False
            if _named(line, prefix) is not None and lines[end].strip().startswith("PARTITION BY "):
                continue
            made.append(_named(line, prefix))
        filled = [_named(l, section) for l in lines if l.startswith(section)]
        if None in made or None in filled:
            return False                      # a name the pairing cannot read whole fails the keep (G23-F2)
        return all(name in set(filled) for name in made)
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
        engine.log("answer", op=op, result="success", held=reference, source=source, **other_held(engine, operation, result))
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


def other_held(engine, operation, result):
    """Each held field the create's output names beside its one id, kept by the answer record as a protected record of its
    own, so that the output's field binds that field and not the id (G23-2; ORD-1, SEC-4). {} where it names none."""
    op, id_field = operation["id"], operation["construction"].get("id_field", "id")
    kept = {}
    for name, mark in sorted(((operation.get("output") or {}).get("fields") or {}).items()):
        field = mark.get("held") if isinstance(mark, dict) else None
        if isinstance(field, str) and field != id_field and field not in kept and result.held(field) is not None:
            kept[field] = engine.protect(op, str(result.held(field)).encode("utf-8"), "held field",
                                         "the %s of what %s made" % (field, op))
    return {"held_fields": kept} if kept else {}


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
        engine.log("answer", op=op, result="success", held=reference, source="status-read", **other_held(engine, operation, result))
        after_check(engine, operation)
        complete(engine, operation, "c", [])
        return "made"
    if word == lost.get("nothing_word", "nothing"):
        return "nothing"
    return None


# ---- C3: swap ------------------------------------------------------------------------------------------------
# J7 (L-24; the owner's "Links only"): the link forms a vault note uses, and no other text. A wiki link `[[target]]`, its
# alias `[[target|alias]]` and heading `[[target#heading]]` parts, and an embed `![[target]]`; a Markdown link
# `[text](path)` and an image `![alt](path)`. Only a target or path that begins with the old folder is repointed.
WIKI_LINK = re.compile(r"(\[\[)([^\]\|#\n]*)")
MD_LINK = re.compile(r"(\]\()([^)\s]*)")


def replace_links(text, old, new):
    """`text` with each link whose target begins with `old` made to begin with `new`, plain text left as it was; and how
    many links were repointed."""
    count = [0]

    def swap(found):
        target = found.group(2)
        if old and target.startswith(old):
            count[0] += 1
            return found.group(1) + new + target[len(old):]
        return found.group(0)
    out = MD_LINK.sub(swap, WIKI_LINK.sub(swap, text))
    return out, count[0]


def edited(data, edit, value_of, read_other=None):
    """The new bytes of a file after one declared edit; None where the edit does not apply. `data` is None where the file is
    absent (OP-2, A147: a change whose before-state is its absence is published as C1 publishes); `read_other` reads another
    file's text in memory, for the kit's lift (G19-13)."""
    kind = edit.get("kind")
    if data is None:
        if kind != "kit":
            return None
        body = str(value_of(edit["text"]))
        if edit.get("where_it_stands") == "merge":
            body = _lifted(body, edit, value_of, read_other)        # the lift where the file is absent too (G23-13)
        return body.encode("utf-8")
    text = data.decode("utf-8")
    if kind == "kit" and edit.get("where_it_stands") == "merge":
        return _lifted(_merged(text, str(value_of(edit["text"])), str(value_of(edit["pointer"])) if edit.get("pointer") is not None else None),
                       edit, value_of, read_other).encode("utf-8")
    if kind == "kit":
        # the kit in place (rows-rise 3.5): kept where it stands; or its text added below what stands, the other lines of
        # the file it lifts from (all but its stub line) added under a heading; or the file made the stub, only where each
        # of its other lines stands in the file it was lifted into
        stands = edit.get("where_it_stands")
        if stands == "append":
            out = text + ("" if text.endswith("\n") or not text else "\n") + str(value_of(edit["text"]))
            if edit.get("lift_from") is not None:
                other = read_other(value_of(edit["lift_from"])) if read_other else None
                stub = str(value_of(edit["stub"])) if edit.get("stub") is not None else None
                lifted = [l for l in (other or "").split("\n") if l.strip() and l != stub]
                if lifted:
                    out += ("" if out.endswith("\n") else "\n") + str(value_of(edit["lift_heading"])) + "\n" + "".join(l + "\n" for l in lifted)
            return out.encode("utf-8")
        if stands == "stub":
            stub = str(value_of(edit["stub"]))
            into = read_other(value_of(edit["lift_from"])) if read_other else None
            if into is None:
                return None
            have = into.split("\n")
            if any(l.strip() and l != stub and l not in have for l in text.split("\n")):
                return None
            return str(value_of(edit["text"])).encode("utf-8")
        return None
    if kind == "replace-all":
        old, new = str(value_of(edit["old"])), str(value_of(edit["new"]))
        if not old or text.count(old) < 1:
            return None
        return text.replace(old, new).encode("utf-8")
    if kind == "replace-links":
        old, new = str(value_of(edit["old"])), str(value_of(edit["new"]))
        out, count = replace_links(text, old, new)
        return out.encode("utf-8") if old and count else None
    if kind == "move-line":
        # the one line holding a text, a replacement made in it where the edit names one, moved just under a heading line
        # (the heading added at the end where it is missing), or, for its reverse, back between its recorded neighbours
        holding = str(value_of(edit["holding"]))
        lines, ended = reads.file_lines(text)
        at = [i for i, l in enumerate(lines) if holding in l]
        if len(at) != 1:
            return None
        line = lines.pop(at[0])
        if edit.get("old") is not None:
            line = line.replace(str(value_of(edit["old"])), str(value_of(edit["new"])))
        if edit.get("under") is not None:
            heading = str(value_of(edit["under"]))
            heads = [i for i, l in enumerate(lines) if l == heading]
            if len(heads) > 1:
                return None
            if not heads:
                lines.append(heading)
                heads = [len(lines) - 1]
            lines.insert(heads[0] + 1, line)
            return reads.join_lines(lines, True).encode("utf-8")
        if str(value_of(edit["below"])) == enginemod.EDGE_END and str(value_of(edit["above"])) != enginemod.EDGE_START:
            # the join's J1b item 3 (J1's Stop 3): the line was its file's last, so its saved line below stood nowhere, and the
            # move put a heading after its line above; it goes back right after that line above, found exactly once
            above = str(value_of(edit["above"]))
            after = [i + 1 for i, l in enumerate(lines) if l == above]
            if len(after) != 1:
                return None
            return reads.join_lines(lines[:after[0]] + [line] + lines[after[0]:], ended).encode("utf-8")
        back = edited(reads.join_lines(lines, ended).encode("utf-8"),
                      {"kind": "insert-between", "line": {"literal": line}, "above": edit["above"], "below": edit["below"]},
                      lambda mark: mark["literal"] if isinstance(mark, dict) and "literal" in mark and len(mark) == 1 else value_of(mark))
        return back
    if kind == "append-line":
        line = str(value_of(edit["line"]))
        return (text + ("" if text.endswith("\n") or not text else "\n") + line + "\n").encode("utf-8")
    if kind == "remove-line" and edit.get("holding") is not None:
        # every line that holds a text taken out (rows-set T10d's table, G21-8); none is no edit
        holding = str(value_of(edit["holding"]))
        lines, ended = reads.file_lines(text)
        kept = [l for l in lines if holding not in l]
        return reads.join_lines(kept, ended).encode("utf-8") if len(kept) != len(lines) else None
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
    if edited(engine.fs.read(path), construction["edit"], lambda mark: held_text(engine, mark, op), lambda p: other_text(engine, p)) is not None:
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
             "append-line": "at the end", "move-line": "between its recorded neighbours, next to each other exactly once",
             "replace-all": "where its recorded text occurs",
             "replace-links": "in the links where its recorded text begins a target"}.get(edit.get("kind"), "its declared placement")
    return "the declared placement cannot be met: the file %s; the place: %s; the records: %s" % (path, place, ", ".join(records) or "none")


def make_parents(engine, operation, path):
    """C3 and C7 make a missing parent folder of their target inside the folder the construction names (the project
    folder), and no other (G19-13): owner's folders, made one by one, never through a link."""
    spec = operation["construction"].get("make_parents")
    parent = os.path.dirname(path)
    if not isinstance(spec, dict) or engine.fs.lexists(parent):
        return
    op = operation["id"]
    within = os.path.abspath(str(engine.value(spec["within"], op)))
    if not engine.fs.isdir(within) or engine.fs.islink(within) or not os.path.abspath(parent).startswith(within + os.sep):
        return
    missing = []
    while not engine.fs.lexists(parent) and parent != within:
        missing.insert(0, parent)
        parent = os.path.dirname(parent)
    for folder in missing:
        try:
            engine.fs.mkdir(folder)
            engine.fs.chmod(folder, int(spec.get("mode", 0o755)))
        except OSError:
            raise Stop("the folder could not be made", op, what=folder)


def c3(engine, operation, answer):
    op, construction = operation["id"], operation["construction"]
    path = engine.value(operation["thing"]["place"], op)
    make_parents(engine, operation, path)
    no_link_on_the_way(engine, path, op)
    if not engine.fs.lexists(path):
        if construction["edit"].get("kind") == "folder":
            return c3_absent_folder(engine, operation, answer, path)
        return c3_absent(engine, operation, answer, path)
    if construction["edit"].get("kind") == "folder":
        raise Stop("foreign", op, what=path)          # a folder's change publishes only where nothing is (G23-11)
    try:
        before = engine.fs.read(path)
        mode = engine.fs.mode(path)
        identity = engine.fs.identity(path)
    except OSError:
        raise Stop("unreadable", op)
    new = edited(before, construction["edit"], lambda mark: held_text(engine, mark, op), lambda p: other_text(engine, p))
    if new is None:
        raise Stop("foreign", op, what=placement_unmet(engine.value, operation, path, op))
    # G24-6 (a): the swap's own computed text handed as G22-7's `computed`, so that a `computed` input is the very text the swap
    # puts in place (set's T17: "the note after", which its reverse V06 checks the note against, EV-6)
    inputs = engine.save_reverse_inputs(operation, (None, before, new))
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


def _lines(text):
    return text.split("\n")[:-1] if text.endswith("\n") else text.split("\n")


def _merged(text, body, pointer):
    """The kit merge (G23-13; rows-rise 3.5, SR03-agents): where the file's content lines are the old pointer (one line, or
    the lines of a text of several, G24-5), standing next to each other, those lines replaced by the body; else each line of
    the body the file lacks added at the end of its heading's section, the heading added at the end where it is absent, and
    what stands kept. A line before the body's first heading goes at the
    end of the file's lines before its own first heading."""
    have = _lines(text)
    content = [l for l in have if l.strip() and not l.startswith("#")]
    stub = pointer.split("\n") if pointer is not None else None
    found = reads.span_at(have, stub) if stub and content == stub else []
    if len(found) == 1:
        # the old stub as it stands, its one line or its lines next to each other (G24-5: v1's old AGENTS.md stub has two),
        # being the file's every content line: those lines replaced by the body, nothing else of the file touched
        at = found[0]
        return "".join(l + "\n" for l in have[:at]) + body + "".join(l + "\n" for l in have[at + len(stub):])
    out, heading = list(have), None
    for line in _lines(body):
        if line.startswith("#"):
            heading = line
            if line not in out:
                out.append(line)
            continue
        if not line.strip() or line in out:
            continue
        if heading is None:
            first = next((i for i, l in enumerate(out) if l.startswith("#")), len(out))
            out.insert(first, line)
            continue
        start = out.index(heading)
        end = next((i for i in range(start + 1, len(out)) if out[i].startswith("#")), len(out))
        out.insert(end, line)
    return "".join(l + "\n" for l in out)


def _lifted(text, edit, value_of, read_other):
    """The other lines of the file the kit lifts from (all but its stub line), each the text lacks, added unchanged under the
    lift's heading (the heading added at the end where it is absent); the text as it is where nothing is to be lifted."""
    if edit.get("lift_from") is None:
        return text
    other = read_other(value_of(edit["lift_from"])) if read_other else None
    stub = str(value_of(edit["stub"])) if edit.get("stub") is not None else None
    have = _lines(text)
    lifted = [l for l in _lines(other or "") if l.strip() and l != stub and l not in have]
    if not lifted:
        return text
    heading = str(value_of(edit["lift_heading"]))
    out = text + ("" if text.endswith("\n") or not text else "\n")
    if heading not in have:
        out += heading + "\n"
        return out + "".join(l + "\n" for l in lifted)
    out_lines = _lines(out)
    start = out_lines.index(heading)
    end = next((i for i in range(start + 1, len(out_lines)) if out_lines[i].startswith("#")), len(out_lines))
    out_lines[end:end] = lifted
    return "".join(l + "\n" for l in out_lines)


def other_text(engine, path):
    """Another file's text, read in memory for an edit (the kit's lift); None where it cannot be read."""
    try:
        return engine.fs.read_text(path) if isinstance(path, str) and engine.fs.isfile(path) else None
    except (OSError, UnicodeDecodeError):
        return None


def c3_absent(engine, operation, answer, path):
    """OP-2 (A147): a change of a file whose recorded before-state is its absence is published as C1 publishes: built in
    staging, its step record durable before the publish, put at its place by a rename that fails if anything is there."""
    op, construction = operation["id"], operation["construction"]
    new = edited(None, construction["edit"], lambda mark: held_text(engine, mark, op), lambda p: other_text(engine, p))
    if new is None:
        raise Stop("foreign", op, what=placement_unmet(engine.value, operation, path, op))
    start_record(engine, operation, answer, {"path": path, "exists": False}, {"path": path, "exists": True, "sha256": fsio.sha256_hex(new)})
    folder = enginemod.staging_of(engine.run_dir, op)
    clear_staging(engine, op)
    engine.fs.mkdir(folder)
    staged = os.path.join(folder, "object")
    engine.fs.write_new(staged, new)
    engine.log("step", op=op, step="staged", identity=engine.fs.identity(staged), sha256=fsio.sha256_hex(new))
    if engine.fs.volume(staged) != engine.fs.volume(os.path.dirname(path)):
        raise Stop("the place is on another volume", op)
    try:
        engine.fs.rename_noreplace(staged, path)
    except fsio.Exists:
        raise Stop("something is at the place", op)
    except OSError:
        raise Stop("the publish failed", op)
    settle_mode(engine, operation, path)
    engine.fs.rmdir(folder)
    after_check(engine, operation)
    complete(engine, operation, "a", [])


def c3_absent_folder(engine, operation, answer, path):
    """OP-2 (A154): a change of a folder whose recorded before-state is its absence is published as C1 publishes: an empty
    folder (holding one empty `.gitkeep` where the edit says so) built in staging, its step record durable before the publish,
    put at its place by a rename that fails if anything is there, an empty folder included (G23-11)."""
    op, construction = operation["id"], operation["construction"]
    start_record(engine, operation, answer, {"path": path, "exists": False}, {"path": path, "exists": True})
    folder = enginemod.staging_of(engine.run_dir, op)
    clear_staging(engine, op)
    engine.fs.mkdir(folder)
    staged = os.path.join(folder, "object")
    engine.fs.mkdir(staged)
    if construction["edit"].get("gitkeep"):
        engine.fs.write_new(os.path.join(staged, ".gitkeep"), b"")
    engine.log("step", op=op, step="staged", identity=engine.fs.identity(staged), sha256=None)
    if engine.fs.volume(staged) != engine.fs.volume(os.path.dirname(path)):
        raise Stop("the place is on another volume", op)
    try:
        engine.fs.rename_noreplace(staged, path)
    except fsio.Exists:
        raise Stop("something is at the place", op)
    except OSError:
        raise Stop("the publish failed", op)
    settle_mode(engine, operation, path)
    if construction["edit"].get("gitkeep") and engine.fs.mode(os.path.join(path, ".gitkeep")) != 0o644:
        engine.fs.chmod(os.path.join(path, ".gitkeep"), 0o644)
    engine.fs.rmdir(folder)
    after_check(engine, operation)
    complete(engine, operation, "a", [])


# ---- C4, C5, C6: one request of a store or a provider ----------------------------------------------------------
def c456(engine, operation, answer):
    op, construction, thing = operation["id"], operation["construction"], operation["thing"]
    spec = construction.get("computed") if isinstance(construction.get("computed"), dict) else None
    # the computed text read once, before the reverse's inputs are saved, so that a before-image of its read and an
    # after-image of the computed text are the texts the effect starts from and sends (G22-7, rows-set T10d)
    read = computed_text(engine, operation, spec) if spec else None
    inputs = engine.save_reverse_inputs(operation, read)
    start_record(engine, operation, answer, {"word": str(thing.get("before_word", "before"))[:64]},
                 {"word": str(thing.get("after_word", "after"))[:64]}, inputs)
    computed = None
    if spec:
        record = engine.protect(op, read[2], spec.get("type", "after-image"), spec.get("label", "a protected input made from a computed text"))
        computed = {spec["param"]: {"record": record}}
    result = engine.call(engine.command(operation, construction["command"]), op, extra=computed)
    if result.definite != "success":
        raise Stop("a command failed", op, command=result.shown, result=result.kind)
    after_check(engine, operation)
    complete(engine, operation, "a", inputs)


def computed_text(engine, operation, spec):
    """A C6 command's protected input made from a computed text (G21-8; SEC-3): the protected text its read gave (a command
    whose answer is declared `protected text`), or a saved record, with the row's edit applied in memory. Returns (the
    command read, or None; the text read; the computed text); `c456` writes the computed text owner-only in the protected
    folder as a record of the declared type, and hands it to the command's slot by its parameter."""
    op, source = operation["id"], spec.get("from") or {}
    if "command" in source:
        result = engine.call(engine.command(operation, source["command"]), op)
        text = getattr(result, "protected_text", None)
        if result.kind != "success" or text is None:
            raise Stop("an input the command needs could not be read", op)
        data = text.encode("utf-8")
    else:
        found = engine.value(source.get("value"), op)
        data = protected.read(engine.fs, engine.run_dir, found.reference) if isinstance(found, values.Held) else str(found).encode("utf-8")
    out = data
    if spec.get("edit"):
        out = edited(data, spec["edit"], lambda mark: held_text(engine, mark, op))
        if out is None:
            raise Stop("the edit does not apply", op)
    return source.get("command"), data, out


# ---- C7: exclusive move of an identified thing -------------------------------------------------------------------
def c7(engine, operation, answer):
    op, construction = operation["id"], operation["construction"]
    source = engine.value(operation["thing"]["place"], op)
    target = engine.value(construction["to"], op)
    make_parents(engine, operation, target)
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
