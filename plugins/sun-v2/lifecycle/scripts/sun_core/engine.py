"""Running the operations of an approved manifest (the frame's ORD-5, OP-1 to OP-10, LOG-2, LOG-3, EV-1 to
EV-4, KEEP-1 to KEEP-5, RISK-1).

One operation at a time: the first, in the manifest's order, whose phase is open, whose condition is
true and whose needs are met; a check that OP-8 says must be attempted again for that operation is
attempted first. For an operation of a kind that has an effect the tool reads the journal for it,
then the world (the probe, OP-5), and does what OP-6's table names for the answer. Every record is
durable before the step it describes begins.

A rule that says stop raises `Stop`; the invocation then ends `stopped`. Nothing here guesses, sends
a create again on its own, takes as the project's a thing it found, or records a way back it cannot
prove (GOV-1).
"""
import os

from . import calls, fsio, protected, reads, runner, state as statemod, values

# A file's start and its end, as a span's save records them in place of the line on that side (EV-6, A83). A line never
# holds a newline, so neither can be a recorded line.
EDGE_START = "\n(the file's start)\n"
EDGE_END = "\n(the file's end)\n"


class Stop(Exception):
    """A rule of the frame says stop. `reason` is what the status form's stop line is built from."""

    refused = False                       # the runner refused the command (SEC-3)
    word = None                           # the runner's own fixed word, where it refused the command

    def __init__(self, kind, op=None, **more):
        Exception.__init__(self, kind)
        self.reason = dict(kind=kind, **more)
        if op is not None:
            self.reason["op"] = op


def refused_stop(refused, op, **more):
    """The stop on a refusal of the runner's (SEC-3): the run ends `stopped` on that refusal, its form naming it."""
    stop = Stop("the runner refused the command: " + refused.reason, op, **more)
    stop.refused = True                  # at a later start, no changed context and no re-plan asked (A53)
    return stop


def sec10_stop(hit, op, register):
    """The stop of SEC-10's check: it names the file and shows nothing. A file whose own name holds a hit is named by the
    fixed words of withholding."""
    from . import texts
    named, why = hit
    shown = named if named and not register.holds(named) else texts.WITHHELD
    return (texts.SEC10_IGNORE if why == "ignore" else texts.SEC10_HIT, op), {"what": texts.SEC10_FILE + shown}


def staging_of(run_dir, op):
    return os.path.join(run_dir, "staging", op)


def step_providers(operation):
    """The providers whose commands an owner step's read uses: each needs its identity read before the step's (OP-9)."""
    commands = operation.get("commands") if isinstance(operation.get("commands"), list) else []
    return sorted(set(str(c.get("use", "")).partition(".")[0] for c in commands if isinstance(c, dict) and c.get("use")))


def unanswered_identity(op, provider):
    """OP-9 (batch 51, A120): "Where the identity read of the step's provider, made before the step's read, fails, is partial
    or runs out of time, so that the step's read is not made, the step is in no form and the run ends `stopped`, its form
    naming the identity read that failed, with no effect applied: a stop that rests on GOV-1"."""
    return Stop("unreadable", op, what="the identity read of " + provider)


class Engine(object):
    def __init__(self, session, manifest):
        self.session = session
        self.world = session.world
        self.fs = session.world.fs
        self.journal = session.journal
        self.manifest = manifest
        self.run_dir = session.run_dir
        self.fresh = {}                   # what this invocation's own read of a waiting step gave (OP-9)
        # the steps in read-back mode whose read this invocation made and got an answer from. OP-9 (batch 51, A120): "a
        # waiting step whose read this invocation did not make, or made and got no answer from, is in no form this
        # invocation renders, neither from the manifest's text nor from an earlier form's"; a waiting step not here has
        # the lane's line for it (`forms`, FORM-2)
        self.read_now = set()
        self.refresh()

    def refresh(self):
        self.state = statemod.State(self.manifest, self.journal)
        self.state.fresh = self.fresh
        self.state.read_now = self.read_now
        return self.state

    def log(self, kind, **fields):
        record = self.journal.append(self.world, kind, register=self.session.register, **fields)
        self.refresh()
        return record

    # ---- reading --------------------------------------------------------------------------------
    def reader(self, operation, with_journal=True):
        return reads.Reader(self.session, self.state.with_own(operation["id"]), operation.get("commands") if isinstance(operation.get("commands"), list) else [],
                            self.call_for_read, operation["id"], self.journal if with_journal else None)

    def call_for_read(self, session, command, outputs, op, journal):
        if command["declaration"].get("effects", 0) != 0:
            raise Stop("a read would change something", op)
        return self.call(command, op)

    def call(self, command, op, extra=None, cwd=None, own=None):
        try:
            outputs = self.state.with_own(op) if op in self.state.ops else self.state.outputs
            return calls.call(self.session, command, outputs, op, self.journal, extra, cwd, own)
        except calls.Disproved:
            self.refresh()
            raise Stop("a safe ground disproved", op)
        except runner.Refused as refused:
            stop = Stop("the runner refused the command: " + refused.reason, op)
            stop.refused = True              # a refusal of the runner's (SEC-3): at a later start, no changed context
            stop.word = refused.reason       # the runner's own fixed word, for a create's step record of it (LOG-2, A99)
            raise stop
        except calls.NotCallable as bad:
            raise Stop("the command cannot be built: " + bad.reason, op)
        except values.Unsettled:
            raise Stop("a value the command needs is not bound", op)

    def command(self, operation, name):
        for command in operation.get("commands") if isinstance(operation.get("commands"), list) else []:
            if command.get("name") == name:
                return command
        raise Stop("the row names a command it does not declare", operation["id"])

    def value(self, mark, op):
        try:
            return values.resolve(mark, self.state.with_own(op) if op in self.state.ops else self.state.outputs)
        except values.Unsettled:
            raise Stop("a value the operation needs is not bound", op)

    def evaluate(self, operation, test, what):
        try:
            answer = self.reader(operation).evaluate(test)
        except runner.Refused as refused:
            # an owner step's read, made when the step is first reached (`begin_wait`), refused by the runner: a child the
            # read starts (the shortcut check's shell; a row's command is stopped so by `call`). SEC-3's refusals row (batch
            # 41, A96): "An owner step's read, made when the step is first reached, is a command of that operation: where it
            # is refused, the step is not shown, no `waiting` record is written, and the run ends `stopped` on that refusal
            # (OP-9)." The stop is raised before anything of the step is written or shown
            raise refused_stop(refused, operation["id"], what=what)
        if answer == reads.UNREADABLE:
            raise Stop("unreadable", operation["id"], what=what)
        return answer

    # ---- choosing (ORD-5) -----------------------------------------------------------------------
    def next(self):
        """The next thing to do: ("run", op), ("attempt", check, for_op), ("not needed", op),
        ("held", op, need, provider, status), or None where nothing can run. Raises `Stop`."""
        state = self.state
        if state.unknown:
            # the journal holds a record no rule names: the tool stops and hands it to the owner (GOV-1)
            raise Stop("the journal holds a record no rule names", state.unknown[0].get("op"))
        for op in state.order:
            if op in state.finals or op in state.waiting:
                continue
            if op in state.outstanding:
                raise Stop("an outstanding create", op)
            if not state.phase_open(op):
                continue
            condition = state.condition(op)
            if condition is None:
                continue
            if condition is False:
                return ("not needed", op)
            operation = state.ops[op]
            blocked, again = False, None
            for need in operation.get("needs") if isinstance(operation.get("needs"), list) else []:
                verdict, provider, status = state.need(need)
                if verdict == "wait":
                    blocked = True
                elif verdict in ("stop", "branch"):
                    raise Stop("need unmet", op, need="%s at the %s level" % (need["output"], need["level"]),
                               provider=provider, provider_status=status)
                elif verdict == "his":
                    return ("held", op, "%s at the %s level" % (need["output"], need["level"]), provider, status)
                elif need["level"] == "passed" and status == "passed" and not self._pass_stands(provider, operation):
                    again = provider
            if blocked:
                continue
            if again is not None:
                return ("attempt", again, op)
            return ("run", op)
        return None

    def _pass_stands(self, check, needing):
        """OP-8: a need on a check is met only by its latest attempt, and only if that attempt read
        the subject in the tracked state it has now and, where the operation that needs it has an
        effect, was made in that operation's own invocation."""
        latest = self.state.attempts[check][-1]
        subject = self.subject_state(self.state.ops[check])
        if subject != latest.get("subject"):
            return False
        if needing.get("kind") in ("build", "keep", "create", "change", "move") and latest.get("inv") != self.world.invocation:
            return False
        return True

    def run(self):
        """Run until nothing can run or a rule says stop. Returns nothing; `Stop` ends it."""
        while True:
            action = self.next()
            if action is None:
                return
            if action[0] == "not needed":
                self.log("status", op=action[1], status="not needed",
                         reason={"condition": "the other branch was taken"},
                         way_back=self.no_way_back(self.state.ops[action[1]], "not needed"))
            elif action[0] == "held":
                self.log("status", op=action[1], status="held",
                         reason={"need": action[2], "provider": action[3], "provider_status": action[4]},
                         way_back=self.no_way_back(self.state.ops[action[1]], "held"))
            elif action[0] == "attempt":
                self.attempt(self.state.ops[action[1]])
            else:
                self.run_operation(self.state.ops[action[1]])

    def run_operation(self, operation):
        kind = operation["kind"]
        self.session.operation = operation["id"]
        if kind == "check":
            self.attempt(operation)
        elif kind in ("owner step", "owner answer"):
            self.begin_wait(operation)
        elif kind == "adopt":
            self.adopt(operation)
        else:
            self.effect(operation)
        self.session.operation = None

    # ---- checks (OP-8) --------------------------------------------------------------------------
    def subject_state(self, operation):
        thing = operation["thing"]
        if thing.get("subject_git"):
            # SEC-10's check: its subject is what it scans, the index or the head commit, by the tool's own measure (OP-8).
            # Asked before the place's own state, which the repository's folder alone would give: a new commit leaves the
            # folder as it was, and OP-8's need would then be met by an attempt made on another commit (report-12, item 4)
            from . import commitscan, gitread
            try:
                repo = commitscan.repository(self.session, self.value(thing["place"], operation["id"]))
                if thing["subject_git"] == "head":
                    return {"word": repo.ref("HEAD") or "no commit"}
                index = repo.index()
                return {"word": fsio.sha256_hex(fsio.canonical_json(sorted(index.items())).encode("utf-8"))}
            except (commitscan.Unreadable, gitread.Unreadable, OSError, ValueError, IndexError):
                raise Stop("unreadable", operation["id"], what="the check's subject")
        if thing.get("place") is not None:
            path = self.value(thing["place"], operation["id"])
            try:
                return reads.tracked_state(self.fs, path, thing.get("tracked") or ("exists", "sha256"))
            except OSError:
                raise Stop("unreadable", operation["id"], what="the check's subject")
        if thing.get("subject_field"):
            name, _, field = thing["subject_field"].partition(".")
            found = self.state.outputs.get(name, {}).get(field)
            return {"word": str(found)[:64]} if found is not None and not isinstance(found, values.Held) else {}
        return {}

    def attempt(self, operation):
        op, thing = operation["id"], operation["thing"]
        number = len(self.state.attempts.get(op) or []) + 1
        capability = thing.get("capability")
        if capability and capability not in (self.manifest.get("capabilities") or []):
            self.log("attempt", op=op, attempt=number, subject={}, answer="unavailable", way_back=self.no_way_back(operation, "unavailable"))
            return
        subject = self.subject_state(operation)
        reader = self.reader(operation)
        try:
            verdict = reader.evaluate(thing.get("passes") or [])
        except runner.Refused as refused:
            # a child a check's own read starts (SEC-10's ignore proof asks git) refused by the runner: stopped on that
            # refusal as `call` stops a row's command, and no attempt is recorded. SEC-10 (batch 40, A94): "Where the runner
            # refuses a command of this check, the proof's git or a read of the scan, the check is not made and no attempt
            # is recorded: as SEC-3's refusals row has it for every operation's command, the operation is not started and
            # the run ends `stopped` on that refusal, its form naming the refusal."
            stop = Stop("the runner refused the command: " + refused.reason, op)
            stop.refused = True
            raise stop
        if verdict == reads.UNREADABLE:
            raise Stop("unreadable", op, what="the check's subject")
        if verdict:
            self.log("attempt", op=op, attempt=number, subject=subject, answer="passed", way_back=self.no_way_back(operation, "passed"))
        else:
            self.log("attempt", op=op, attempt=number, subject=subject, answer="failed")
        if not verdict:
            if reader.last_hit:
                args, more = sec10_stop(reader.last_hit, op, self.session.register)
                raise Stop(*args, **more)
            raise Stop("a check failed", op)

    # ---- adopt (OP-10) --------------------------------------------------------------------------
    def adopt(self, operation):
        op = operation["id"]
        path = self.value(operation["thing"]["place"], op)
        now = reads.tracked_state(self.fs, path, operation["thing"].get("tracked") or ("exists", "identity"))
        if now != operation.get("tracked_state"):
            raise Stop("the thing named for adoption is not as the manifest recorded it", op)
        self.log("status", op=op, status="adopted", binds=now, way_back=self.no_way_back(operation, "adopted"))

    # ---- owner operations (OP-9) ----------------------------------------------------------------
    def begin_wait(self, operation):
        op = operation["id"]
        mode = operation.get("resolved_mode")
        inputs = []
        if operation["kind"] == "owner step" and isinstance(operation.get("reverse_inputs"), list) and not operation.get("no_reverse"):
            inputs = self.save_reverse_inputs(operation)       # saved and read back before the step is shown
        if mode == "read back":
            if self.evaluate(operation, operation.get("after_test"), "the step's read") is True:
                self.log("status", op=op, status="done by owner, read back", way_back=self.way_back(operation, "done by the owner", inputs))
                return
            self.read_now.add(op)         # read when first reached, and answered: shown as that read builds it (OP-9)
        fields = {"op": op, "mode": mode}
        if inputs:
            fields["inputs"] = inputs
        review = operation.get("review_file")
        if isinstance(review, dict):
            content = self.value(review.get("content"), op)
            fields["review"] = self.protect(op, str(content).encode("utf-8"), review.get("type", "definition"), review.get("label", "a review file"))
        self.log("waiting", **fields)

    def read_back(self):
        """Every waiting step in read-back mode is read again at the start of each invocation but a
        close (OP-9). Completes on the read alone."""
        for op in list(self.state.order):
            if op not in self.state.waiting:
                continue
            operation = self.state.ops[op]
            if operation.get("resolved_mode") != "read back":
                continue
            if not self.identity_first(operation):
                continue
            reader = self.reader(operation)
            try:
                verdict = reader.evaluate(operation.get("after_test"))
            except runner.Refused as refused:
                # the read of a step left `waiting`, made at an invocation's start, refused by the runner (a row's command is
                # stopped so by `call`). SEC-3's refusals row (batch 41, A96): "Where it is a read that a later invocation
                # makes at its start, the reads RUN-10 (b) compares and OP-9's reads among them, ... no effect is applied,
                # and the run ends `stopped` on that refusal, its form naming it. That holds for a summons with no word too,
                # whose OP-9 reads are among them: a run left `waiting` then ends `stopped` on that refusal". Both callers end
                # the run on a refused stop (`commands.resume` with no word, `commands.run_operations` on his word)
                raise refused_stop(refused, op, what="the step's read")
            if verdict == reads.UNREADABLE:
                # OP-9 (batch 50, A118): "Where an owner step's read ... fails, is partial, is made as the wrong account or runs
                # out of time (OP-5's last row), whether it is made when the step is first reached or when a waiting step is
                # read again at the start of an invocation, the step is not shown, since it is shown only as a fresh read
                # builds it, and the run ends `stopped`, its form naming the step and the read that failed, with no effect
                # applied." The step stays `waiting` on record; no form of this invocation shows its text (`forms`)
                raise Stop("unreadable", op, what="the step's read")
            self.read_now.add(op)
            self.fresh[op] = ", ".join("%s %s" % (k, v) for k, v in sorted(reader.last_safe.items()) if isinstance(v, str))
            if verdict is True:
                inputs = self.state.waiting_records[op].get("inputs") or []
                self.log("status", op=op, status="done by owner, read back", way_back=self.way_back(operation, "done by the owner", inputs))

    def identity_first(self, operation):
        """Before a waiting step's read, its provider's identity read, where this invocation has not made it yet (OP-9;
        SEC-12's table). A refusal of the runner's stops the run on that refusal (SEC-3, A53); a read that fails, is partial
        or runs out of time stops it too, one whose credentials the provider refuses among them (OP-9, A120, A122); one that
        shows an account his settings do not name, which is RUN-10 (b)'s, leaves the step's read unmade, and the step
        waiting. True where the step's read may be made."""
        from . import plan
        pending = [p for p in step_providers(operation) if p not in self.session.identities_read
                   and isinstance((self.session.providers.get(p) or {}).get("identity"), dict)]
        if not pending:
            return True
        causes, refusals, unanswered = [], [], []
        plan.identity_reads(self.session, pending, causes, refusals, unanswered)
        if refusals:
            provider, reason = refusals[0]
            stop = Stop("the runner refused the command: " + reason, operation["id"], what="the identity read of " + provider)
            stop.refused = True
            raise stop
        if unanswered:
            raise unanswered_identity(operation["id"], unanswered[0])
        if causes:
            self.fresh[operation["id"]] = "the step's read was not made: " + "; ".join(causes)
            return False
        return True

    def waiting_identity_stop(self, unanswered):
        """Where an invocation's start has made the identity reads already, those RUN-10 (b) compares (a resume on his
        current word; a re-plan's go), and one that a waiting step in read-back mode needs before its read did not answer:
        the stop of OP-9 (A120) for the first such step in the manifest's order, else None. A provider no waiting step
        needs is left as it was (A120's seen line)."""
        for op in self.state.order:
            operation = self.state.ops[op]
            if op not in self.state.waiting or operation.get("resolved_mode") != "read back":
                continue
            for provider in step_providers(operation):
                if provider in unanswered:
                    return unanswered_identity(op, provider)
        return None

    def owner_word(self, op, word, value, position):
        """His word on one waiting operation. Returns a fixed word for what was done with it."""
        state = self.state
        if op not in state.waiting:
            return "not waiting"
        operation = state.ops[op]
        mode = operation.get("resolved_mode")
        if word == "leave it":
            self.log("owner-answer", op=op, answer="leave it", position=position)
            self.log("status", op=op, status="left", way_back=self.no_way_back(operation, "left"))
            return "left"
        if word == "done":
            if mode == "on his word":
                self.log("owner-answer", op=op, answer="done", position=position)
                inputs = state.waiting_records[op].get("inputs") or []
                self.log("status", op=op, status="done by owner, on his word", way_back=self.way_back(operation, "done by the owner", inputs))
                return "done"
            return "read again"           # in read-back mode his "done" asks for the read to be made again
        if word == "answer":
            if mode != "answer" or value not in (operation.get("answers") or []):
                return "refused"
            self.log("owner-answer", op=op, answer=value, position=position)
            self.log("status", op=op, status="answered", way_back=self.no_way_back(operation, "answered"))
            return "answered"
        return "refused"

    # ---- protected records, reverse inputs, ways back (SEC-6, LOG-2, EV-4) -------------------------
    def protect(self, op, content, kind, label):
        try:
            return protected.write(self.world, self.run_dir, self.world.new_id("p"), content, kind, label)
        except (OSError, protected.Unreadable):
            raise Stop("a protected record could not be saved", op)

    def save_reverse_inputs(self, operation):
        """Every input the row's reverse names, read and saved as a protected record before the
        effect (LOG-2), each read back against its fingerprint."""
        op, saved = operation["id"], []
        for item in operation.get("reverse_inputs") if isinstance(operation.get("reverse_inputs"), list) else []:
            try:
                if item.get("read") == "file":
                    content = self.fs.read(self.value(item["path"], op))
                elif item.get("read") == "value":
                    content = str(self.value(item["value"], op)).encode("utf-8")
                elif item.get("read") in ("line-above", "line-below", "head"):
                    # EV-6 (A83, A84): "For a span that stood at its file's start or at its end, the file's start, or its
                    # end, stands as the recorded line on that side, and the sunset's save records it so"
                    lines, _ended = reads.file_lines(self.fs.read_text(self.value(item["path"], op)))
                    span = str(self.value(item["line"], op)).split("\n")
                    found = reads.span_at(lines, span)
                    if len(found) != 1:
                        raise Stop("an input a reverse needs could not be read", op)
                    at = found[0]
                    if item["read"] == "line-above":
                        content = (lines[at - 1] if at > 0 else EDGE_START).encode("utf-8")
                    elif item["read"] == "line-below":
                        content = (lines[at + len(span)] if at + len(span) < len(lines) else EDGE_END).encode("utf-8")
                    else:
                        content = "".join(l + "\n" for l in lines[:at]).encode("utf-8")
                elif item.get("read") == "command":
                    result = self.call(self.command(operation, item["command"]), op)
                    held = result.held(item.get("field")) if result.kind == "success" else None
                    if held is None:
                        raise Stop("an input a reverse needs could not be read", op)
                    content = fsio.canonical_json(held).encode("utf-8")
                else:
                    raise Stop("an input a reverse needs could not be read", op)
            except OSError:
                raise Stop("an input a reverse needs could not be read", op)
            saved.append(self.protect(op, content, item.get("type", "before-image"), item.get("label", "an input of the reverse")))
        return saved

    def no_way_back(self, operation, status):
        """EV-4 (batch 30), for an operation that ends in a final status other than `done`, `already so`, `not proven` or
        `done by owner`: "no way back", with the reason "the row declares none" where its row declares none, and otherwise,
        none of the five reasons being true of it, its own final status, named as such (a `not needed`, `refused`, `left`
        or `held` change, move or owner step whose row declares a way back among them). Every final record holds one."""
        declared = operation.get("way_back")
        if not isinstance(declared, dict) or "reverse" not in declared:
            return {"offered": False, "reason": "the row declares none"}
        return {"offered": False, "reason": status}

    def way_back(self, operation, absent_reason, inputs):
        """EV-4: a way back is recorded when the row declares one, the operation is `done`, and
        every input the reverse needs was on disk before the effect; in every other case `none`
        with one reason of the list."""
        declared = operation.get("way_back")
        if not isinstance(declared, dict) or "reverse" not in declared:
            return {"offered": False, "reason": "the row declares none"}
        if absent_reason not in (None, "done by the owner"):
            return {"offered": False, "reason": absent_reason}
        wanted = operation.get("reverse_inputs") if isinstance(operation.get("reverse_inputs"), list) else []
        for reference in inputs:
            try:
                protected.read(self.fs, self.run_dir, reference)
            except protected.Unreadable:
                return {"offered": False, "reason": "an input is missing"}
        if len(inputs) < len(wanted):
            return {"offered": False, "reason": "an input is missing"}
        if absent_reason == "done by the owner":
            # no way back of the tool's is recorded for his step; what its reverse needs stays named (EV-5, OP-9)
            return {"offered": False, "reason": "done by the owner", "reverse": declared["reverse"].get("id", operation["id"] + "-reverse"),
                    "inputs": inputs}
        return {"offered": True, "reverse": declared["reverse"].get("id", operation["id"] + "-reverse"), "inputs": inputs}

    def mark_risks(self, operation):
        """RISK-1: an operation carried under RK2, RK3, RK4, RK5 or RK13 is marked so in the journal, once
        for each of those risks, also after a kill and a resume (a shortcut's add and its put-back carry RK5's and RK13's
        marks beside RK2's)."""
        construction = operation.get("construction") if isinstance(operation.get("construction"), dict) else {}
        for risk in construction.get("risks") or []:
            if (operation["id"], risk) not in self.state.marks:
                self.log("step", op=operation["id"], step="risk-mark", risk=risk)

    # ---- the probe and the effect (OP-5, OP-6) -----------------------------------------------------
    def effect(self, operation):
        from . import effects
        effects.run(self, operation)
