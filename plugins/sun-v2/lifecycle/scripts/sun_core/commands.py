"""What each kind of summons does once it is past the gate and the name check (the frame's RUN-1, RUN-5,
RUN-9 to RUN-13; OP-9; EV-7; SEC-12's table of the ways an invocation can begin).

    look     a first look: the whole look, the manifest, the preview (RUN-5 to RUN-8)
    go       records his go on the manifest the preview showed, opens the run, runs operations (RUN-9)
    resume   goes on, on his current word; with none or a stale one it renders status (RUN-10)
    status   renders status and ends
    replan   a new plan in the same run: a full look, a new manifest, a new preview (RUN-11)
    close    records the run closed on his word (RUN-13)

Every handler raises `startup.Ended` with the invocation's ending.
"""
import json
import os

from . import calls, disproof, effects, engine as enginemod, exits, forms, fsio, journal as journalmod
from . import locks as locksmod, manifest as manifestmod, plan, rows, rundir, runner, schemas, startup, state as statemod, texts

Ended = startup.Ended


# ---- small shared pieces --------------------------------------------------------------------------------------
def secret_reads_of(session):
    """What the manifest shows the run reads a secret from: for the disproof read (SEC-12)."""
    try:
        found = manifestmod.numbers(session.world.fs, session.run_dir)
        if not found:
            return []
        gos = manifestmod.go_records(session.journal)
        number = gos[-1]["manifest"] if gos else found[-1]
        doc, _sha = manifestmod.load(session.world.fs, session.run_dir, number)
    except (OSError, ValueError):
        return []
    return doc.get("secret_reads") or [] if isinstance(doc, dict) else []


def read_json_file(session, path):
    try:
        return json.loads(session.world.fs.read(path).decode("utf-8"))
    except (OSError, ValueError):
        return None


def capabilities_of(session, args):
    """What the harness adapter declares it can do (RUN-5): the file the adapter handed over."""
    if not args.capabilities:
        return []
    doc = read_json_file(session, args.capabilities)
    found = doc.get("capabilities") if isinstance(doc, dict) else None
    return sorted(c for c in found if isinstance(c, str)) if isinstance(found, list) else []


def refusal_form(session, lines):
    return forms.write(session, "refusal", lines)


def cue_of(session, kind):
    """The cue: no value, a fixed sound and a fixed line (SEC-12). The adapter plays it; the core
    starts no child for it."""
    if session.world.cue is not None:
        session.world.cue(kind)
    here = os.path.dirname(os.path.abspath(__file__))
    assets = os.path.join(os.path.dirname(os.path.dirname(here)), "assets")
    sound = {"sunrise": "rise.wav", "sunset": "set.wav"}.get(kind)
    return {"line": texts.CUE_LINE[kind], "sound": os.path.join(assets, sound) if sound else None}


def context_now(session, manifest, args, refusals=None, unanswered=None):
    """What RUN-10 (b) compares: the accounts, capabilities and machine locations read now. Where `refusals` is
    given, an identity read the runner refused is put there (SEC-3, A53); where `unanswered` is given, the provider
    of an identity read that failed, was partial or ran out of time (OP-9, A120)."""
    causes = []
    accounts = plan.identity_reads(session, sorted(manifest.get("accounts") or {}), causes, refusals, unanswered)
    same = (not causes and accounts == manifest.get("accounts") and capabilities_of(session, args) == manifest.get("capabilities")
            and session.facts.locations(session.world.fs) == manifest.get("locations"))
    return same


def close_in_record(session):
    """The run has ended: it leaves the record of open runs."""
    mapping = locksmod.read_open_runs(session.world.fs, session.facts)
    left = dict((mark, run) for mark, run in mapping.items() if run != session.run_id)
    if left != mapping:
        locksmod.write_open_runs(session.world, session.facts, left)


def save_inputs(session, number, data):
    """Save the inputs SEC-9 has passed, under the first free name `inputs_names` gives, made new and never over another."""
    for name in rundir.inputs_names(number):
        try:
            session.world.fs.write_new(os.path.join(session.run_dir, name), data)
            return name
        except fsio.Exists:
            continue


def do_look(session, args, kind, number, state, journal_count):
    """The whole look, to a manifest on disk and its preview. Raises what `plan.build` raises."""
    world = session.world
    inputs = read_json_file(session, args.inputs)
    if not isinstance(inputs, dict):
        raise plan.InputRefused()
    found = schemas.errors("input", inputs)
    if found:
        raise plan.BuildFailed([{"row": None, "entry": "inputs" + f["path"], "finding": "fails its schema (%s)" % f["rule"]} for f in found])
    plan.check_inputs(session.register, inputs, session.names)            # SEC-9: before anything of it is saved
    save_inputs(session, number, fsio.pretty_json(inputs).encode("utf-8"))
    look = plan.Look(inputs, list(session.names), session.facts.locations(world.fs), capabilities_of(session, args), session.run_id)
    doc = plan.build(session, kind, look, number, state, journal_count)
    manifestmod.validate(doc)
    sha = manifestmod.write(world, session.run_dir, number, doc, session.register)
    loaded, _ = manifestmod.load(world.fs, session.run_dir, number)
    try:
        lines = forms.preview_lines(loaded)
    except forms.NoLine as missing:
        # FORM-2: a line neither the table nor the lane's list of form changes gives fails the build of the form
        raise plan.BuildFailed([{"row": None, "entry": "form_changes", "finding": "no form has a line for: " + missing.status}])
    form = forms.write(session, "preview", lines)
    return loaded, sha, form


def look_failed(session, exc, has_go, in_force_note=""):
    """A look that ends without a manifest. Before a first go it is `refused`; in a re-plan of a
    run that has its go it is `stopped`, with the manifest in force unchanged (RUN-12)."""
    ending = "stopped" if has_go else "refused"
    if isinstance(exc, plan.BuildFailed):
        lines = [texts.BUILD_FAILED] + ["row %s, entry %s: %s" % (f.get("row"), f.get("entry"), f.get("finding")) for f in exc.findings]
        raise Ended(ending, lines, exits.VALIDATION, findings=exc.findings)
    if isinstance(exc, manifestmod.Invalid):
        lines = [texts.BUILD_FAILED] + ["the manifest, at %s: %s" % (f["path"], f["rule"]) for f in exc.findings]
        raise Ended(ending, lines, exits.VALIDATION)
    if isinstance(exc, plan.Questions):
        lines = [texts.QUESTIONS] + list(exc.questions)
    elif isinstance(exc, plan.PlanningStop):
        lines = [texts.PLANNING_STOP] + list(exc.causes)
    elif isinstance(exc, journalmod.Withheld):
        lines = [texts.DISPROVED_BEFORE_GO if not has_go else texts.VALUE_WITHHELD_STOP]
    else:
        lines = [texts.INPUT_REFUSED_REPLAN if has_go else texts.INPUT_REFUSED]
        raise Ended(ending, lines)
    form = refusal_form(session, lines)
    raise Ended(ending, lines, forms=[form], run=session.run_id)


LOOK_FAILURES = (plan.BuildFailed, plan.Questions, plan.PlanningStop, plan.InputRefused, manifestmod.Invalid, journalmod.Withheld)


# ---- look ---------------------------------------------------------------------------------------------------------
def look(session, args):
    prospective = session.world.new_id(args.kind)
    session.lock_and_look(args.kind, None, prospective)
    session.make_run_directory(prospective)
    session.startup_passed()
    cue = cue_of(session, args.kind)
    try:
        doc, sha, form = do_look(session, args, args.kind, 1, None, 0)
    except LOOK_FAILURES as exc:
        look_failed(session, exc, has_go=False)
    raise Ended("preview", ["The preview is rendered; nothing is done before your go.", "run: %s" % session.run_id],
                exits.SUCCESS, run=session.run_id, manifest_sha256=sha, forms=[form], cue=cue)


# ---- ending an invocation of a run that has its go (RUN-12) --------------------------------------------------------
def end_run(session, engine, manifest, stop=None, lines=None):
    """Exactly one of five endings, each with a status form from the manifest and the journal."""
    state = engine.refresh()
    reason = stop.reason if stop is not None else None
    retirement = manifest.get("kind") == "sunset"
    if stop is None and state.all_final():
        ending = "ended with exceptions" if state.exceptions() else "complete"
        engine.log("run-end", ending=ending)
        close_in_record(session)
    elif stop is None and state.waiting:
        ending = "waiting"
        engine.log("invocation-end", ending="waiting")
    else:
        ending = "stopped"
        if reason is None:
            reason = {"kind": "nothing can run, nothing waits on you, and an operation is not final"}
        clean = dict((k, v) for k, v in reason.items() if k in ("kind", "op", "need", "provider", "provider_status", "result", "command", "what")
                     and v is not None)
        engine.log("invocation-end", ending="stopped", reason=clean)
    state = engine.refresh()
    position = session.journal.count()
    try:
        form = forms.write(session, "status", forms.status_lines(manifest, state, session.run_dir, ending, reason, position, retirement))
    except forms.NoLine as missing:
        raise Ended(ending, [texts.NO_FORM_LINE + missing.status], run=session.run_id, position=position)
    out = list(lines or []) + ["the run now: %s" % ending]
    if reason:
        out.append("stopped: %s" % reason.get("kind"))
        if reason.get("op"):
            out.append("operation: %s" % reason["op"])
        if reason.get("command"):
            out.append("the command you can run: %s" % reason["command"])
        if reason.get("kind") in (texts.SEC10_HIT, texts.SEC10_IGNORE) and reason.get("what"):
            out.append(reason["what"])                       # SEC-10: a hit names the file and shows nothing
    raise Ended(ending, out, run=session.run_id, position=position, forms=[form])


def as_it_stood(session, engine, manifest, lines, form_says=()):
    """An invocation that ends with no effect ends in the way the run already stood, `waiting` or
    `stopped`, and its status form says so (RUN-10, RUN-12). `form_says` are fixed lines the status form
    itself must also say: a resume on his current word while a re-plan's manifest awaits its go, whose
    "status form saying that a new plan awaits his go" (RUN-12; OP-9; the owner's ruling, A130)."""
    state = engine.refresh()
    if state.all_final():
        end_run(session, engine, manifest, None, lines)      # his own step, read back, was the last thing open
    last = [r for r in session.journal.records if r.get("kind") == "invocation-end"]
    # the way the run already stood: a run whose last invocation ended `stopped` stands `stopped`, a step waiting on
    # him beside the stop or not (RUN-12: "one on a run left `stopped` ends `stopped`")
    stood = last[-1].get("ending") if last else None
    ending = "stopped" if stood == "stopped" or not state.waiting else "waiting"
    position = session.journal.count()
    reason = last[-1].get("reason") if last and ending == "stopped" else None
    try:
        form = forms.write(session, "status", forms.status_lines(manifest, state, session.run_dir, ending, reason, position,
                                                                 manifest.get("kind") == "sunset") + list(form_says))
    except forms.NoLine as missing:
        raise Ended(ending, [texts.NO_FORM_LINE + missing.status], run=session.run_id, position=position)
    raise Ended(ending, list(lines) + ["the run now: %s" % ending], run=session.run_id, position=position, forms=[form])


def run_operations(session, engine, manifest, first=None):
    stop = None
    try:
        if first is not None:
            first()
        engine.read_back()
        for op in list(engine.state.order):
            operation = engine.state.ops[op]
            if op in engine.state.outstanding and operation.get("resolve_by_status"):
                effects.resolve_outstanding(engine, operation)
        engine.run()
    except enginemod.Stop as found:
        stop = found
    except journalmod.Withheld:
        stop = enginemod.Stop("a record would have carried a value this tool may not show", getattr(session, "operation", None))
    end_run(session, engine, manifest, stop)


# ---- go -------------------------------------------------------------------------------------------------------------
def keys_as_looked(session, doc):
    """RUN-9 (the owner's rulings A76 and A79; RUN-2): a first go recorded by an invocation other than its look's is recorded
    only where the keys that invocation holds are exactly those its manifest records (RUN-8). Where it holds a key the look
    did not hold, by its alias reads or by a name it carries, or fewer keys than its look did, a name form being gone from its
    alias reads or a name the owner gave that look being left off its summons, no go is recorded, no journal is written and no
    run is opened: once its startup checks have passed it ends `refused`, its refusal form saying so in fixed words and naming
    the private file that holds that name (SEC-6). It returns only where the keys are exactly the look's."""
    from . import keys as keysmod, protected
    world, fs = session.world, session.world.fs
    held, recorded = set(session.prints), set(doc.get("keys") or [])
    if held == recorded:
        return

    def mark(name):
        return keysmod.fingerprint(session.keying, keysmod.fold(name))

    def private(names, label):
        reference = protected.write(world, session.run_dir, world.new_id("p"), "".join(n + "\n" for n in names).encode("utf-8"),
                                    "values", label)
        return protected.path_of(session.run_dir, reference["record"])
    causes = []
    more = held - recorded
    if more:
        names = [n for n in session.names + session.alias_names if mark(n) in more]
        causes.append(texts.NEW_NAME_AT_GO.format(path=private(sorted(set(names)), "the names this go holds that its look did not")))
    fewer = recorded - held
    if fewer:
        looked = list(doc.get("names") or [])
        if isinstance(doc.get("alias_names"), dict):
            try:
                looked += protected.read(fs, session.run_dir, doc["alias_names"]).decode("utf-8").splitlines()
            except (protected.Unreadable, UnicodeDecodeError):
                pass
        names = [n for n in looked if n and mark(n) in fewer]
        causes.append(texts.NAME_GONE_AT_GO.format(path=private(sorted(set(names)), "the names the look held that this go does not")))
    look_failed(session, plan.PlanningStop(causes), has_go=False)


def go(session, args):
    world = session.world
    found = session.lock_and_look(args.kind, args.run, None)
    session.open_run_directory(args.run, secret_reads_of)
    session.startup_passed()
    numbers = manifestmod.numbers(world.fs, session.run_dir)
    gos = manifestmod.go_records(session.journal)
    in_force = gos[-1]["manifest"] if gos else 0
    number = numbers[-1] if numbers else 0
    # the journal holds the go and the record of open runs does not: the deciding write was not made
    # durable (a kill between the two), so the run is open under none of its keys; the go is given again
    unfinished = bool(gos) and found is None and number == in_force
    if not numbers or (number <= in_force and not unfinished):
        raise Ended("refused" if not gos else "stopped", [texts.ALREADY_HAS_GO if gos else texts.NOT_THE_PREVIEWED])
    has_go = bool(gos) and not unfinished
    if session.owed and not has_go:
        # a safe ground disproved before a first go: no go is recorded, no journal written, no run opened
        lines = [texts.DISPROVED_BEFORE_GO]
        form = refusal_form(session, lines + ["a value the look saved: %s" % session.register.words()])
        raise Ended("refused", lines, forms=[form], run=session.run_id)
    doc, sha = manifestmod.load(world.fs, session.run_dir, number)
    if sha != args.manifest_sha256:
        raise Ended("stopped" if has_go else "refused", [texts.NOT_THE_PREVIEWED])
    try:
        manifestmod.validate(doc)
    except manifestmod.Invalid as bad:
        look_failed(session, bad, has_go)
    if not has_go and not unfinished:
        keys_as_looked(session, doc)
    refusals, unanswered = [], []
    if not context_now(session, doc, args, refusals, unanswered):
        if has_go and not refusals and unanswered:
            # OP-9 (batch 51, A120): the identity read of a waiting step's provider, made before the step's read, failed, was
            # partial or ran out of time: the step's read is not made, the step is in no form, and the run ends `stopped`,
            # its form naming that identity read. It is the re-plan's go of a run that has its go, whose waiting steps are
            # the manifest in force's
            _number, in_force = manifestmod.in_force(world.fs, session.run_dir, session.journal)
            engine = enginemod.Engine(session, in_force)
            stop = engine.waiting_identity_stop(unanswered)
            if stop is not None:
                session.first_records()
                end_run(session, enginemod.Engine(session, in_force), in_force, stop)
        if refusals:
            # RUN-10 (b)'s read, refused by the runner: no changed context and no look again (SEC-3, A53). Before a first
            # go there is no run to stand `stopped` (RUN-12): `refused`, with its refusal form; in a re-plan's go the run
            # ends `stopped` on that refusal, its status form naming it
            provider, reason = refusals[0]
            if not has_go:
                lines = [texts.REFUSED_READ_AT_GO.format(reason=reason, provider=provider)]
                raise Ended("refused", lines, forms=[refusal_form(session, lines)], run=session.run_id)
            session.first_records()
            _number, in_force = manifestmod.in_force(world.fs, session.run_dir, session.journal)
            stop = enginemod.Stop("the runner refused the command: " + reason, None, what="the identity read of " + provider)
            stop.refused = True
            end_run(session, enginemod.Engine(session, in_force), in_force, stop)
        raise Ended("stopped" if has_go else "refused", [texts.CONTEXT_CHANGED_BEFORE_GO])
    prints = sorted(session.prints)
    if unfinished:
        session.first_records()
        if gos[-1]["manifest_sha256"] != sha or sorted(gos[-1]["keys"]) != prints:
            raise Ended("refused", [texts.NOT_THE_PREVIEWED])
    elif not has_go:
        session.journal.append(world, "open", register=session.register, run=session.run_id, run_kind=args.kind, keys=prints,
                               manifest=number, manifest_sha256=sha, word="go", closes=session.over)
    else:
        session.first_records(word=("go", {"manifest": number, "manifest_sha256": sha, "keys": prints, "word": "go"}))
    # the deciding write: the run is open under every key it holds the lock of, or under none (RUN-3, EV-7)
    mapping = locksmod.read_open_runs(world.fs, session.facts)
    mapping = dict((mark, run) for mark, run in mapping.items() if run != session.over)
    for mark in prints:
        mapping[mark] = session.run_id
    locksmod.write_open_runs(world, session.facts, mapping)
    if session.over:
        retirement = rundir.check(world.fs, session.facts.run_dir(session.over))
        if not [r for r in retirement.records if r.get("kind") == "run-end"]:
            retirement.append(world, "run-end", register=session.register, ending="closed", by="a restore's go", restore=session.run_id)
    engine = enginemod.Engine(session, doc)
    run_operations(session, engine, doc)


# ---- the summonses that continue a run -----------------------------------------------------------------------------
def open_continued(session, args):
    """Startup for a summons that continues a run, to the point where its startup checks have
    passed. Returns the manifest in force, or raises the refusal the frame names."""
    world = session.world
    found = session.lock_and_look(args.kind, args.run, None)
    run_id = found or args.run
    if session.partner is not None:
        # a retirement that a restore's go may have closed (EV-7): the handover's repair, then refused
        partner_dir = session.facts.run_dir(session.partner)
        try:
            partner = rundir.check(world.fs, partner_dir)
        except rundir.Failed as failed:
            session._stop_on_rundir(failed.cause, session.partner, True)
        opening = partner.records[0] if partner.records else {}
        run_id = run_id or opening.get("closes")
        if not run_id or opening.get("closes") != run_id:
            session._refuse_open(session.partner)
        session.open_run_directory(run_id, secret_reads_of)
        if not [r for r in session.journal.records if r.get("kind") == "run-end"]:
            session.closed_owed = (session.journal, session.partner)
        session.startup_passed()
        session.first_records()
        raise Ended("refused", [texts.CLOSED_NEVER_RESUMES])
    session.open_run_directory(run_id, secret_reads_of)
    session.startup_passed()
    if not session.is_open or [r for r in session.journal.records if r.get("kind") == "run-end"]:
        if session.is_open:
            close_in_record(session)             # the run's own ending is on record: the index is brought up to it
        raise Ended("refused", [texts.CLOSED_NEVER_RESUMES])
    try:
        number, doc = manifestmod.in_force(world.fs, session.run_dir, session.journal)
    except manifestmod.Altered:
        raise Ended("stopped", [texts.MANIFEST_ALTERED], run=session.run_id)
    if doc is None:
        raise Ended("refused", [texts.NOTHING_TO_RESUME])
    # a restore whose go closed a retirement: the retirement's own closing record, where it is missing (EV-7)
    opening = session.journal.records[0]
    if opening.get("closes"):
        try:
            retirement = rundir.check(world.fs, session.facts.run_dir(opening["closes"]))
        except rundir.Failed as failed:
            session._stop_on_rundir(failed.cause, opening["closes"], True)
        if not [r for r in retirement.records if r.get("kind") == "run-end"]:
            session.closed_owed = (retirement, session.run_id)
    return doc


def resume(session, args):
    doc = open_continued(session, args)
    position = session.journal.count()
    op, said, value = None, "go on", None
    spoken = getattr(args, "word", None) == "go on" or bool(getattr(args, "done", None) or getattr(args, "leave", None) or getattr(args, "answer", None))
    # his word, given in answer to the latest status form: the position alone authorizes nothing (RUN-10)
    word = spoken and getattr(args, "position", None) is not None and args.position == position
    if getattr(args, "done", None):
        op, said = args.done, "done"
    elif getattr(args, "leave", None):
        op, said = args.leave, "leave it"
    elif getattr(args, "answer", None):
        op, value = args.answer.split("=", 1)
        said = "answer"
    engine = enginemod.Engine(session, doc)
    if not word:
        session.first_records()
        engine.refresh()
        try:
            engine.read_back()
        except enginemod.Stop as stop:
            # a read this start makes, refused by the runner: no changed context, no re-plan asked; no effect is applied, and
            # the run ends `stopped` on that refusal, its form naming it (SEC-3, A53). And a waiting step's read that did not
            # answer: OP-9 (batch 50, A118), "At the start of an invocation it is that failed read, and not RUN-10's own
            # ending, that ends the invocation, a summons with no word among them (RUN-12)". `read_back` raises no other stop
            end_run(session, engine, doc, stop)
        as_it_stood(session, engine, doc, [texts.WORD_NEEDED])
    if manifestmod.numbers(session.world.fs, session.run_dir)[-1] > manifestmod.go_records(session.journal)[-1]["manifest"]:
        # a resume on his current word while a re-plan's manifest awaits its go (the owner's ruling, A130): no identity read,
        # no read of a waiting step and no other read RUN-10 (b) compares (OP-9; SEC-12's table); it applies nothing and ends
        # as the run stood, `waiting` or `stopped` (RUN-12; A131), its status form saying that a new plan awaits his go
        session.first_records()
        as_it_stood(session, engine, doc, [texts.NEW_PLAN_AWAITS], form_says=[texts.NEW_PLAN_AWAITS])
    fields = {"word": said, "position": position}
    if op:
        fields["op"] = op
    if value is not None and op in engine.state.ops and value in (engine.state.ops[op].get("answers") or []):
        fields["value"] = value
    session.first_records(word=("word", fields))
    engine.refresh()
    refusals, unanswered = [], []
    same = context_now(session, doc, args, refusals, unanswered)
    if refusals:
        # RUN-10 (b)'s read, refused by the runner: no changed context, and no re-plan, whose look would meet the
        # same refusal (GOV-1); no effect is applied, and the run ends `stopped` on that refusal (SEC-3, A53)
        provider, reason = refusals[0]
        stop = enginemod.Stop("the runner refused the command: " + reason, None, what="the identity read of " + provider)
        stop.refused = True
        end_run(session, engine, doc, stop)
    stop = engine.waiting_identity_stop(unanswered)
    if stop is not None:
        # OP-9 (batch 51, A120): "Where the identity read of the step's provider, made before the step's read, fails, is
        # partial or runs out of time, so that the step's read is not made, the step is in no form and the run ends
        # `stopped`, its form naming the identity read that failed, with no effect applied". That read is the one RUN-10 (b)
        # compares (SEC-12's table); it ends the invocation here, before RUN-10 (b)'s re-plan is asked for
        end_run(session, engine, doc, stop)
    if not same:
        as_it_stood(session, engine, doc, [texts.REPLAN_NEEDED])
    note = []

    def first():
        if op:
            outcome = engine.owner_word(op, said, value, position)
            if outcome == "refused":
                note.append("that answer is not one the step allows; it stays waiting")
    run_operations(session, engine, doc, first)


def status(session, args):
    args.position = None
    args.word = None
    args.done = args.leave = args.answer = None
    resume(session, args)


def close(session, args):
    doc = open_continued(session, args)
    engine = enginemod.Engine(session, doc)
    position = session.journal.count()
    if args.word != "close":
        session.first_records()
        as_it_stood(session, engine, doc, [texts.CLOSE_WORD_NEEDED])
    session.first_records(word=("run-end", {"ending": "closed", "by": "the owner's word", "position": position}))
    close_in_record(session)
    state = engine.refresh()
    position = session.journal.count()
    try:
        form = forms.write(session, "status", forms.status_lines(doc, state, session.run_dir, "closed", None, position,
                                                                 doc.get("kind") == "sunset"))
    except forms.NoLine as missing:
        raise Ended("closed", [texts.NO_FORM_LINE + missing.status], run=session.run_id)
    raise Ended("closed", ["the run now: closed"], run=session.run_id, position=position, forms=[form])


def replan(session, args):
    doc = open_continued(session, args)
    session.first_records()
    engine = enginemod.Engine(session, doc)
    ends = [r for r in session.journal.records if r.get("kind") == "invocation-end"]
    if ends and (ends[-1].get("reason") or {}).get("kind") == effects.UNCONFIRMED:
        # KEEP-5: with an entry at its place and unconfirmed, the ways on are resume and close
        as_it_stood(session, engine, doc, [texts.UNCONFIRMED_NO_REPLAN])
    if session.learnt:
        # RUN-2 (A72): the alias reads showed a name form whose key the run does not hold. No lock was taken under it and no
        # key is added; the look ends at once as a planning stop, `stopped`, with the manifest in force unchanged, its form
        # saying so in fixed words and naming the private file that holds the name (SEC-6), as for a name a provider shows
        from . import protected
        reference = protected.write(session.world, session.run_dir, session.world.new_id("p"),
                                    ("\n".join(session.learnt) + "\n").encode("utf-8"), "values", "the other names the project now shows")
        look_failed(session, plan.PlanningStop([texts.NEW_NAME_IN_REPLAN.format(path=protected.path_of(session.run_dir, reference["record"]))]),
                    has_go=True)
    numbers = manifestmod.numbers(session.world.fs, session.run_dir)
    number = numbers[-1] + 1
    kind = doc.get("kind")
    try:
        new, sha, form = do_look(session, args, kind, number, engine.state, session.journal.count())
    except LOOK_FAILURES as exc:
        look_failed(session, exc, has_go=True)
    raise Ended("waiting" if engine.state.waiting else "stopped",
                ["A new plan is rendered; the manifest in force is unchanged until your go on the new one.", "run: %s" % session.run_id],
                run=session.run_id, manifest_sha256=sha, forms=[form], position=session.journal.count())


HANDLERS = {"look": look, "go": go, "resume": resume, "status": status, "replan": replan, "close": close}
