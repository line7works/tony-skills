"""The look and the plan (the frame's RUN-5 to RUN-8, RUN-11; ORD-2 to ORD-4; KEEP-2, KEEP-4, KEEP-5; OP-4, OP-7,
OP-10; SEC-9, SEC-12's "Another run's journal").

The look only reads. It reads the tools' identities (the account every remote operation will act
as), what the harness adapter declares it can do, the journals of the project key's earlier runs,
and for each candidate row one planning test, which reads only what exists before the run. Then it
builds the manifest: every operation with everything its row states, its planning outcome and the
tracked state read, and every `already so` and `not applicable` line. Nothing about the shape of the
plan is settled after the go.

Three ways a look ends without a manifest: `BuildFailed` (a row, the checklist or the plan's shape
breaks a rule: the findings name the row), `PlanningStop` (RUN-7's causes, each named) and
`Questions` (an answer the look needs is lacking).
"""
import copy
import json
import os
import re

from . import calls, channels, disproof, disproofs, journal as journalmod, protected, reads, rows, rundir
from . import runner, screen as screenmod, state as statemod, texts, values

RETIREMENT_PHASES = ["keeping", "retiring on this machine", "retiring at the providers", "the last record"]
READ_KINDS = {"timeout": "the read ran out of time", "malformed": "the read was partial", "auth": "the read was made as the wrong account",
              "other": "the read failed", None: "the read failed"}
ADDRESS_WITH_PASSWORD = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:[^/\s@]+@")


class BuildFailed(Exception):
    def __init__(self, findings):
        Exception.__init__(self, "the manifest's build failed")
        self.findings = findings


class PlanningStop(Exception):
    def __init__(self, causes):
        Exception.__init__(self, "a planning stop")
        self.causes = causes


class Questions(Exception):
    def __init__(self, questions):
        Exception.__init__(self, "an answer is lacking")
        self.questions = questions


class InputRefused(Exception):
    pass


class Look(object):
    def __init__(self, inputs, names, locations, capabilities, run_id=None):
        self.run_id = run_id
        self.inputs = inputs
        self.names = names
        self.locations = locations
        self.capabilities = capabilities
        self.date = None              # the run's date by the tool's own clock, read once by the look (`build`)
        self.facts = {"flags": inputs.get("flags") or {}, "type": inputs.get("type"), "adopt": inputs.get("adopt") or {},
                      "answers": inputs.get("answers") or {}}


# ---- inputs (SEC-9) ---------------------------------------------------------------------------------------
def texts_in(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for item in node:
            for text in texts_in(item):
                yield text
    elif isinstance(node, dict):
        for key, item in node.items():
            yield key
            for text in texts_in(item):
                yield text


def check_inputs(register, inputs, names):
    """An input that holds a secret is refused at the start and is stored nowhere."""
    for text in list(texts_in(inputs)) + list(names):
        if register.holds(text) or ADDRESS_WITH_PASSWORD.search(text):
            raise InputRefused()


# ---- rows, expanded -----------------------------------------------------------------------------------------
def expand(lane, providers):
    """The lane's rows with every command's declaration written in, as the manifest will hold it."""
    expanded = []
    for row in lane.get("rows") or []:
        row = copy.deepcopy(row)
        if isinstance(row, dict) and isinstance(row.get("commands"), list):
            for command in row["commands"]:
                if not isinstance(command, dict) or not isinstance(command.get("use"), str):
                    continue
                provider, _, name = command["use"].partition(".")
                decl = ((providers.get(provider) or {}).get("commands") or {}).get(name)
                if isinstance(decl, dict):
                    decl = copy.deepcopy(decl)
                    # a command's own trace flags replace the module's for it (G19-27)
                    decl["trace_flags"] = list(decl["trace_flags"] if isinstance(decl.get("trace_flags"), list)
                                               else (providers.get(provider) or {}).get("trace_flags") or [])
                    decl["provider"] = provider
                    command["declaration"] = decl
        expanded.append(row)
    return expanded


def held_outputs(expanded):
    """{"output.field": the provider that issues it} for every held or secret field of an output: the provider of the
    command the row that provides it makes its effect by, or of its one command where it names none (SEC-2: a held value
    goes back only to the provider that issued it)."""
    out = {}
    for row in expanded:
        output = row.get("output") if isinstance(row, dict) and isinstance(row.get("output"), dict) else {}
        construction = row.get("construction") if isinstance(row, dict) and isinstance(row.get("construction"), dict) else {}
        commands = [c for c in (row.get("commands") if isinstance(row, dict) and isinstance(row.get("commands"), list) else [])
                    if isinstance(c, dict) and isinstance(c.get("use"), str)]
        by = [c for c in commands if c.get("name") == construction.get("command")] or (commands if len(commands) == 1 else [])
        issuer = by[0]["use"].partition(".")[0] if by else None
        for field, mark in (output.get("fields") or {}).items():
            if isinstance(mark, dict) and ("held" in mark or "secret" in mark):
                out["%s.%s" % (output.get("name"), field)] = issuer
    return out


def admit_all(lane, expanded, providers):
    findings = []
    held = held_outputs(expanded)
    seen = set()
    for row in expanded:
        findings += rows.admit(row, providers, held)
        if isinstance(row, dict):
            if row.get("id") in seen:
                findings.append(rows.finding(row, "id", "two rows have one id"))
            seen.add(row.get("id"))
            if isinstance(row.get("phase"), str) and row["phase"] not in (lane.get("phases") or []):
                findings.append(rows.finding(row, "phase", "not a phase the lane declares (ORD-4)"))
    for found in rows.checklist_findings(lane):
        findings.append({"row": None, "entry": "checklist", "finding": "%s: %s" % (found["item"], found["finding"])})
    return findings


# ---- the shape of the plan (ORD-2, ORD-3, ORD-4, KEEP-4, KEEP-5) ----------------------------------------------
def _providers(operations, already):
    table = {}
    for operation in operations:
        output = operation.get("output") if isinstance(operation.get("output"), dict) else {}
        if output.get("name"):
            table.setdefault(output["name"], []).append(operation)
    for item in already:
        if item.get("output"):
            table.setdefault(item["output"], [])
    return table


def settle_needs(operations, already, not_applicable, impossible=None):
    """ORD-2: a need that names an output no operation provides is settled when the manifest is
    built, by the treatment the row declares. Returns (operations left, settled lines, findings)."""
    findings, settled = [], []
    impossible = impossible or {}
    changed = True
    while changed:
        changed = False
        table = _providers(operations, already)
        state_met = set(item["output"] for item in already if item.get("output"))
        for operation in list(operations):
            for need in list(operation.get("needs") if isinstance(operation.get("needs"), list) else []):
                providers = table.get(need.get("output"))
                real = [p for p in (providers or []) if not (need.get("level") == "made" and p.get("kind") == "adopt")]
                cause = impossible.get((operation["id"], need.get("output")))
                if (real and cause is None) or (need.get("level") == "state" and need.get("output") in state_met and cause is None):
                    continue
                treatment = need.get("treatment")
                if treatment == "then not applicable":
                    operations.remove(operation)
                    not_applicable.append({"row": operation["id"], "reason": "a layer the project lacks",
                                           "what": (operation.get("form_lines") or {}).get("preview") or operation["id"]})
                    settled.append({"operation": operation["id"], "treatment": "left out", "need": need.get("output"),
                                    "status": cause or "nothing provides it"})
                    changed = True
                    break
                if treatment == "then not needed":
                    operation["needs"] = [n for n in operation["needs"] if n is not need] or rows.NONE
                    # a check's pass that names the output is dropped with the need (G21-7; ORD-2)
                    thing = operation.get("thing")
                    if isinstance(thing, dict) and isinstance(thing.get("passes"), list):
                        thing["passes"] = [c for c in thing["passes"]
                                           if not any(r.partition(".")[0] == need.get("output") for r in values.refers_to(c))]
                    settled.append({"operation": operation["id"], "treatment": "the need was dropped", "need": need.get("output"),
                                    "status": cause or "nothing provides it"})
                    changed = True
                    break
                findings.append(rows.finding(operation, "needs", "a need that nothing provides has no declared treatment (ORD-2)"))
                operation["needs"] = [n for n in operation["needs"] if n is not need] or rows.NONE
                changed = True
                break
            if changed:
                break
    # a circle of needs
    table = _providers(operations, already)
    graph = {}
    for operation in operations:
        wanted = set()
        for need in operation.get("needs") if isinstance(operation.get("needs"), list) else []:
            for provider in table.get(need.get("output")) or []:
                wanted.add(provider["id"])
        graph[operation["id"]] = wanted

    def reaches(start, goal, seen):
        for nxt in graph.get(start, ()):
            if nxt == goal or (nxt not in seen and reaches(nxt, goal, seen | {nxt})):
                return True
        return False
    for operation in operations:
        if reaches(operation["id"], operation["id"], set()):
            findings.append(rows.finding(operation, "needs", "a circle of needs (ORD-2)"))
    return operations, settled, findings


def _apart(a, b):
    """Whether two operations that provide one output can never run at the same time (ORD-3)."""
    ca = a.get("condition") if isinstance(a.get("condition"), dict) else None
    cb = b.get("condition") if isinstance(b.get("condition"), dict) else None
    for first, second, cond in ((a, b, cb), (b, a, ca)):
        if cond and cond.get("on") == "alternative" and cond.get("operation") == first["id"]:
            return True
    if ca and cb and ca.get("on") == cb.get("on") and ca.get("operation") == cb.get("operation") and ca.get("on") in ("alternative", "answer"):
        return (ca.get("result"), ca.get("equals")) != (cb.get("result"), cb.get("equals"))
    return False


def shape_findings(kind, lane, operations):
    findings = []
    phases = lane.get("phases") or []
    table = _providers(operations, [])
    for name, providers in table.items():
        for i, a in enumerate(providers):
            for b in providers[i + 1:]:
                if not _apart(a, b):
                    findings.append(rows.finding(b, "condition", "two alternatives that could run at the same time (ORD-3)"))
    conditions = [o.get("condition") for o in operations if isinstance(o.get("condition"), dict)]
    for operation in operations:
        construction = operation.get("construction") if isinstance(operation.get("construction"), dict) else {}
        for result in construction.get("alternatives") or []:
            if not any(c.get("on") == "alternative" and c.get("operation") == operation["id"] and c.get("result") == result for c in conditions):
                findings.append(rows.finding(operation, "construction", "an alternative result is the condition of no operation (ORD-3)"))
        if construction.get("last_record"):
            last = phases[-1] if phases else None
            alone = [o for o in operations if o.get("phase") == last]
            if operation.get("phase") != last or len(alone) != 1:
                findings.append(rows.finding(operation, "phase", "a run's last record is alone in the last phase (KEEP-5)"))
    if kind == "sunset":
        if phases != RETIREMENT_PHASES:
            findings.append({"row": None, "entry": "phases", "finding": "a retirement's phases are keeping, this machine, the providers, the last record, in that order (ORD-4)"})
        for operation in operations:
            thing = operation.get("thing") if isinstance(operation.get("thing"), dict) else {}
            if thing.get("retires") and operation.get("phase") == RETIREMENT_PHASES[0]:
                findings.append(rows.finding(operation, "phase", "a retiring operation in the keeping phase (ORD-4)"))
            if operation.get("kind") == "keep" and operation.get("phase") != RETIREMENT_PHASES[0]:
                findings.append(rows.finding(operation, "phase", "a keep outside the keeping phase (ORD-4)"))
            if thing.get("retires") and thing.get("where") == "provider" and operation.get("phase") != RETIREMENT_PHASES[2]:
                findings.append(rows.finding(operation, "phase", "a provider retirement outside the providers' phase (ORD-4)"))
            if thing.get("retires") and thing.get("where") == "machine" and operation.get("phase") != RETIREMENT_PHASES[1]:
                findings.append(rows.finding(operation, "phase", "a machine retirement outside the machine's phase (ORD-4)"))
    if kind == "restore":
        for operation in operations:
            thing = operation.get("thing") if isinstance(operation.get("thing"), dict) else {}
            for name in thing.get("runs_on") or []:
                for provider in table.get(name) or []:
                    if phases.index(provider["phase"]) >= phases.index(operation["phase"]):
                        findings.append(rows.finding(operation, "phase", "it starts something running in the phase that puts back what it runs on (ORD-4)"))
    keep_places = [json.dumps(o["thing"].get("place"), sort_keys=True) for o in operations if o.get("kind") == "keep"]
    for operation in operations:
        if operation.get("kind") in ("change", "move", "build"):
            thing = operation.get("thing") if isinstance(operation.get("thing"), dict) else {}
            targets = [json.dumps(thing.get("place"), sort_keys=True)]
            construction = operation.get("construction") if isinstance(operation.get("construction"), dict) else {}
            if construction.get("to") is not None:
                targets.append(json.dumps(construction["to"], sort_keys=True))
            if any(t in keep_places for t in targets):
                findings.append(rows.finding(operation, "thing", "an effect that would write to, move or remove a keep's place (KEEP-4)"))
    return findings


# ---- earlier runs of the key (RUN-5; SEC-12, "Another run's journal") ---------------------------------------
def earlier_runs(session):
    """The key's earlier runs, found as RUN-5 says and by nothing else (batches 20C and 20D): a run is an earlier run of
    the look's keys when its journal's record of its opening holds the fingerprint, keyed with the value now on this
    machine, of a key whose lock the invocation holds. The look reads that record in every run directory, and nothing
    else of a run it has not found, and uses it for one thing: each fingerprint it holds is matched against the
    fingerprints the invocation made itself (`session.prints`); nothing of it is rendered, copied, written or taken as a
    ground. A directory with no journal, or whose journal holds only a cut-off record (LOG-1), is no earlier run. Where
    the look cannot tell, it stops and tells (A57): a first record that is there and cannot be read, and a folder of run
    directories that cannot be listed (A59), each end the look as a failed read (RUN-7), its form saying so in fixed
    words and where the run directories are kept, and naming no directory. Returns the run ids found, in the folder's
    sorted order."""
    fs, facts = session.world.fs, session.facts
    found = []
    try:
        names = fs.listdir(facts.runs_root)
    except FileNotFoundError:
        return found                    # no folder of run directories yet: no run of any key
    except OSError:
        raise PlanningStop([texts.RUNS_UNLISTABLE, texts.RUNS_KEPT_AT + facts.runs_root])
    for name in names:
        if name == session.run_id:
            continue
        what, record = journalmod.Journal.first_record(fs, facts.run_dir(name))
        if what == "unreadable":
            raise PlanningStop([texts.FIRST_RECORD_UNREADABLE, texts.RUNS_KEPT_AT + facts.runs_root])
        if what == "open" and set(record["keys"]) & set(session.prints):
            found.append(name)
    return found


# ---- a restore's own look (EV-5, EV-7; LOG-1's record of a run's opening; RK14) ----------------------------------
CLOCK_FORM = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
OWNER_DONE = ("done by owner, read back", "done by owner, on his word")


def retiring_run(journals):
    """EV-7: the retiring run EV-5 builds from, among the runs the look found and read as SEC-12 has another run's journal
    read (`read_other_runs`, made on every one of them first): a retiring run is a sunset, told by the kind its record of its
    opening names (LOG-1); the latest is the one whose record of its opening holds the latest time of go, by the machine's
    clock (the owner's ruling A68; a clock set back is RK14, which takes no mark). The clock's form is fixed width, so its
    texts order as its times do. Where none is a sunset, or two sunsets carry the latest time, no rule picks, and the look
    stops (GOV-1) as RUN-7's planning stop, with the tool's fixed words."""
    sunsets = []
    for run_id in sorted(journals):
        records = journals[run_id].records
        opening = records[0] if records else {}
        if opening.get("kind") != "open" or opening.get("run_kind") != "sunset":
            continue
        at = opening.get("at")
        if not isinstance(at, str) or not CLOCK_FORM.match(at):
            raise PlanningStop(["the read failed: an earlier run's record of its opening holds no time of go in the tool's own form"])
        sunsets.append((at, run_id))
    if not sunsets:
        raise PlanningStop([texts.NO_RETIRING_RUN])
    latest = max(at for at, _run in sunsets)
    tops = [run_id for at, run_id in sunsets if at == latest]
    if len(tops) != 1:
        raise PlanningStop([texts.RETIREMENTS_AT_ONE_TIME])
    return tops[0]


def _way_back_of(state, journal, op):
    """The way-back field the retiring journal recorded with an operation's final record (EV-4): its completion's, else
    its last status record's, else, for a check, its last attempt's; {} where none holds one."""
    completion = state.completions.get(op)
    if isinstance(completion, dict) and isinstance(completion.get("way_back"), dict):
        return completion["way_back"]
    found = {}
    for record in journal.records:
        if record.get("kind") in ("status", "attempt") and record.get("op") == op and isinstance(record.get("way_back"), dict):
            found = record["way_back"]
    return found


def restore_offer(session, look, retiring, journal, other_held):
    """EV-5: the reverses a restore offers, from the retiring run's journal read against its manifest in force, and every
    operation it does not offer, with the reason EV-4 recorded. Returns (reverse rows, not offered, not applicable).

    - `done` with a way back on record: its reverse;
    - `not proven`: listed, and its reverse offered only where the owner asks for that line in this look
      (`restore_lines` of his inputs), the reverse then marked as running on his word (every form says so);
    - `done by owner`, in either mode: the reverse as an owner step in the same mode, where the retiring run saved what that
      reverse needs, and none where its preview said none could be;
    - every other final status: not offered, with the reason its record holds.
    A reverse whose protected record is missing or fails its fingerprint, or whose operation has a receipt due and not given
    (SEC-12), is planned `not applicable` with that reason; so is one whose content holds a value another run's disproof read
    gave (SEC-12, "Another run's journal"). An operation of the retiring run's manifest in force that has no final record in
    its journal is listed too, with the tool's fixed words that it was not run to its end and that no way back is on record
    for it (EV-5, batch 30). The last tracked state the retiring journal holds of each thing
    is handed back too (EV-3, EV-5), as {path: state}."""
    from . import manifest as manifestmod, state as statemod
    fs = session.world.fs
    run_dir = session.facts.run_dir(retiring)
    try:
        _number, retired = manifestmod.in_force(fs, run_dir, journal)
    except manifestmod.Altered:
        raise PlanningStop(["the read failed: the retiring run's manifest no longer gives its hash"])
    if retired is None:
        raise PlanningStop(["the read failed: the retiring run has no manifest in force"])
    state = statemod.State(retired, journal)
    asked = set(look.inputs.get("restore_lines") or [])
    due = set(d.get("op") for d in state.receipts_due)
    reverses, not_offered, not_applicable = [], [], []
    for op in state.order:
        operation = state.ops[op]
        status = state.finals.get(op)
        what = (operation.get("form_lines") or {}).get("preview") or op
        if status is None:
            not_offered.append({"row": op, "reason": texts.NOT_RUN_TO_ITS_END, "what": what})
            continue
        declared = (operation.get("way_back") or {}).get("reverse") if isinstance(operation.get("way_back"), dict) else None
        record = _way_back_of(state, journal, op)
        inputs = None
        if status == "done" and record.get("offered") and isinstance(declared, dict):
            inputs = record.get("inputs") or []
        elif status == "not proven" and isinstance(declared, dict):
            if op not in asked:
                not_offered.append({"row": op, "reason": "not proven", "what": what})
                continue
            inputs = ((state.starts.get(op) or [{}])[-1]).get("inputs") or []
        elif status in OWNER_DONE and isinstance(declared, dict) and record.get("reverse") and not operation.get("no_reverse"):
            inputs = record.get("inputs") or []
        if inputs is None:
            not_offered.append({"row": op, "reason": record.get("reason") or "the row declares none", "what": what})
            continue
        reverse = copy.deepcopy(declared)
        reverse["reverse_of"] = op
        if status == "not proven":
            reverse["not_proven"] = True
        if status in OWNER_DONE and reverse.get("kind") == "owner step":
            reverse["mode"] = operation.get("resolved_mode")          # the reverse as an owner step in the same mode (EV-5)
        rwhat = (reverse.get("form_lines") or {}).get("preview") or reverse.get("id")
        missing, contents = op in due, []
        for reference in inputs:
            try:
                contents.append(protected.read(fs, run_dir, reference).decode("utf-8", "replace"))
            except protected.Unreadable:
                missing = True
        if missing:
            not_applicable.append({"row": reverse.get("id"), "reason": "a record it needs is missing", "what": rwhat})
            continue
        construction = reverse.get("construction") if isinstance(reverse.get("construction"), dict) else {}
        if construction.get("from_keep"):
            from_keep = keep_copy(fs, state, construction["from_keep"])
            if from_keep is None:
                # EV-7: a keep the restore needs is missing or fails its fingerprint: its dependents are `not applicable`
                not_applicable.append({"row": reverse.get("id"), "reason": "a keep it needs is missing or fails its fingerprint", "what": rwhat})
                continue
            # SEC-7: copied back by C1 at the original place, with the permissions recorded at the retirement, never wider
            recorded = (operation.get("tracked_state") or {}).get("mode")
            mode = (recorded & 0o777) if isinstance(recorded, int) else 0o600
            reverse["construction"] = {"id": "C1", "single_file": True, "copy": from_keep, "mode": mode}
        # SEC-12, "Another run's journal": a reverse whose row or whose inputs hold a value a disproof read of that run gave
        if any(other_held.holds(text) for text in [json.dumps(reverse, sort_keys=True, ensure_ascii=False)] + contents):
            not_applicable.append({"row": reverse.get("id"), "reason": "it would carry a value this tool may not show", "what": rwhat})
            continue
        if '"saved"' in json.dumps(reverse):
            # EV-5, EV-6: the inputs the forward operation saved (LOG-2), copied into this run's own protected folder, where
            # SEC-7 lets them rest, and every {"saved": n} of the reverse bound to its copy; the restore reads no record of
            # the retiring run again after its look
            copies = []
            items = operation.get("reverse_inputs") if isinstance(operation.get("reverse_inputs"), list) else []
            held = held_outputs(retired.get("operations") or [])
            for index, reference in enumerate(inputs):
                content = protected.read(fs, run_dir, reference)
                if index < len(items) and saved_from_safe(items[index], held):
                    # an input its forward row saved from safe content (SEC-1: what the tool built from safe content) stays
                    # usable as text: in a name check, a path and an argument (G19-3); it was searched above (`other_held`)
                    copies.append({"literal": content.decode("utf-8")})
                    continue
                copies.append(protected.write(session.world, session.run_dir, session.world.new_id("p"), content,
                                              reference.get("type", "values"), reference.get("label", "an input of the reverse")))
            try:
                reverse = values.bind_saved(reverse, copies)
            except values.Unsettled:
                not_applicable.append({"row": reverse.get("id"), "reason": "a record it needs is missing", "what": rwhat})
                continue
        reverses.append(reverse)
    return reverses, not_offered, not_applicable, dict((p, t) for p, t in state.tracked.items() if isinstance(t, dict))


def saved_from_safe(item, held):
    """Whether a forward row's saved input was made from safe content: a `value` read whose value, as its manifest froze
    it, holds no protected record and refers to no held or secret field of an output (SEC-1, SEC-6), saved as a type SEC-1
    does not itself name protected: the before-image and the after-image of a span stay protected records (EV-6)."""
    if not isinstance(item, dict) or item.get("read") != "value" or item.get("type") in ("before-image", "after-image"):
        return False
    text = json.dumps(item.get("value"), sort_keys=True)
    return '"record"' not in text and not any(ref in held for ref in values.refers_to(item.get("value")))


def keep_copy(fs, state, keep_id):
    """A reverse that copies from a keep (EV-5, KEEP-4): the keep of the retiring run, at its place, of the size and
    fingerprint its completion record holds (KEEP-1), read now. Returns {"path", "size", "sha256"}, or None where the keep is
    missing or fails its fingerprint (EV-7)."""
    from . import fsio
    keep = state.ops.get(keep_id)
    completion = state.completions.get(keep_id)
    if not isinstance(keep, dict) or keep.get("kind") != "keep" or not isinstance(completion, dict):
        return None
    recorded = completion.get("keep") if isinstance(completion.get("keep"), dict) else {}
    try:
        path = values.resolve((keep.get("thing") or {}).get("place"), {})
        if not isinstance(path, str) or fs.islink(path) or not fs.isfile(path):
            return None
        data = fs.read(path)
    except (values.Unsettled, OSError):
        return None
    if len(data) != recorded.get("size") or fsio.sha256_hex(data) != recorded.get("sha256"):
        return None
    return {"path": path, "size": recorded["size"], "sha256": recorded["sha256"]}


def read_other_runs(session, run_ids):
    """RUN-4's checks and the disproof read on every one of them, before anything of any of them is
    used. Returns ({run id: Journal}, the screen of every value those reads gave). A failure is a
    failed read."""
    journals, held = {}, screenmod.Screen()
    for run_id in run_ids:
        run_dir = session.facts.run_dir(run_id)
        try:
            journal = rundir.check(session.world.fs, run_dir)
        except rundir.Failed:
            raise PlanningStop(["the read failed: an earlier run's directory does not check out"])
        found, every = disproofs.read_all(session.world.fs, run_dir, journal.records)
        if not every:
            raise PlanningStop(["the read failed: an earlier run's record of a withheld value cannot be read"])
        for record, value, components in found:
            held.add(value, components, None, "another run")
        # that run's disproof read, whole (SEC-12, "What holds from then on"): beside its disproof records' values, the search
        # for the hosting token the name check read, for each secret its manifest shows it reads from a file on this
        # machine, and for the value in the protected record of each receipt due and not given; what it finds is held too.
        # It is made on a register of its own: those values do not enter the reading run's register (SEC-12, "Another run's
        # journal"), and nothing is written.
        from . import manifest as manifestmod
        try:
            _number, doc = manifestmod.in_force(session.world.fs, run_dir, journal)
        except manifestmod.Altered:
            raise PlanningStop(["the read failed: an earlier run's manifest no longer gives its hash"])
        reads_of = (doc or {}).get("secret_reads") or [] if isinstance(doc, dict) else []
        try:
            owed, _receipts = disproof.startup_read(session.world, run_dir, journal, screenmod.Screen(), session.tokens, reads_of)
            for item in owed:
                value, components = disproofs.read_value(session.world.fs, run_dir, item)
                held.add(value, components, None, "another run")
        except (rundir.Failed, disproofs.Unreadable):
            raise PlanningStop(["the read failed: an earlier run's record of a withheld value cannot be read"])
        journals[run_id] = journal
    return journals, held


# ---- the look ---------------------------------------------------------------------------------------------------
def providers_used(expanded):
    return sorted(set((c.get("declaration") or {}).get("provider") for row in expanded
                      for c in (row.get("commands") if isinstance(row.get("commands"), list) else []) if isinstance(c, dict)) - {None})


def identity_reads(session, used, causes, refusals=None, unanswered=None):
    """Each provider's identity: the account every remote operation will act as (RUN-5). An account
    that equals no name in his settings ends the look, and the name the provider reported is shown
    nowhere (SEC-4, ground C). Where `refusals` is given, a read the runner refused is also put there,
    as (provider, the runner's fixed word): at a later start it is no changed context (SEC-3, A53).
    Where `unanswered` is given, a provider whose read failed, was partial or ran out of time is also
    put there, a read whose credentials the provider refused among them (OP-9, A120, A122)."""
    accounts = {}
    for provider in used:
        spec = (session.providers.get(provider) or {}).get("identity")
        if not isinstance(spec, dict):
            continue
        # one identity read per route (G19-26): a module may declare one for its requests and one for its runner commands,
        # each compared with his settings; the provider's account is proven only where every route's is, and is one account
        routes = [spec[k] for k in ("request", "runner") if isinstance(spec.get(k), dict)] if "command" not in spec else [spec]
        found = [identity_read(session, provider, route, causes, refusals, unanswered) for route in routes]
        if not found or any(f is None for f in found):
            continue
        if len(set(found)) != 1:
            causes.append("the read was made as the wrong account: %s reports an account your settings do not name" % provider)
            continue
        accounts[provider] = found[0]
        session.identities_read[provider] = found[0]     # made once in this invocation (SEC-12's table; OP-9)
    return accounts


def identity_read(session, provider, spec, causes, refusals=None, unanswered=None):
    """One route's identity read: the account it proved equal to a name in his settings, or None with its cause named."""
    decl = copy.deepcopy(session.providers[provider]["commands"][spec["command"]])
    if not isinstance(decl.get("trace_flags"), list):
        decl["trace_flags"] = list(session.providers[provider].get("trace_flags") or [])
    try:
        result = calls.call(session, {"name": "identity", "declaration": decl, "params": {}}, {})
    except runner.Refused as refused:
        causes.append("the read failed: %s's identity" % provider)
        if refusals is not None:
            refusals.append((provider, refused.reason))
        return None
    except calls.NotCallable:
        causes.append("the read failed: %s's identity" % provider)
        if unanswered is not None:
            unanswered.append(provider)
        return None
    if result.kind != "success":
        causes.append("%s: %s's identity" % (READ_KINDS.get(result.kind, READ_KINDS[None]), provider))
        # OP-9 (batches 51 and 52, A120, A122): an identity read that "fails, is partial or runs out of time"; "An identity
        # read that shows another account is RUN-10 (b)'s; one whose credentials the provider refuses shows no account at
        # all, and is one that fails (OP-5's last row)". So `auth` is put there too; an account his settings do not name,
        # below, is the one that shows another account, RUN-10 (b)'s. A look names each cause as before (RUN-7)
        if unanswered is not None:
            unanswered.append(provider)
        return None
    kept = result.fields.get(spec.get("field", "account"))
    if kept is None or not kept.equal:
        causes.append("the read was made as the wrong account: %s reports an account your settings do not name" % provider)
        return None
    return kept.safe


def excluded_by_inputs(look, row):
    """A candidate the owner's own inputs leave out, settled before anything of it is read: a flag or
    the project type (a condition on a planning fact), a layer he dropped, an adoption he did not
    ask for. Returns the reason, or None."""
    thing = row.get("thing") if isinstance(row.get("thing"), dict) else {}
    condition = row.get("condition")
    if isinstance(condition, dict) and condition.get("on") == "fact":
        try:
            actual = values._dig(look.facts, condition["fact"])
        except values.Unsettled:
            actual = None
        if actual != condition.get("equals"):
            try:
                adopted = values._dig(look.facts, str(condition["fact"]).rpartition(".")[0]).get("adopted")
            except (values.Unsettled, AttributeError):
                adopted = None
            if isinstance(adopted, str):
                return "already adopted: " + adopted          # a document at its destination (G21-2; OP-6, EV-1)
            return condition.get("reason", "a flag")
    if thing.get("layer") and thing["layer"] in (look.inputs.get("drop_layers") or []):
        return "a layer the project lacks"
    if row.get("kind") == "adopt":
        named = row.get("owner_names") if isinstance(row.get("owner_names"), dict) else {}
        try:
            values.freeze({"input": named.get("input", "")}, look)
        except values.Unsettled:
            return "a flag"
    return None


def lane_texts(session, look, entry, spec, findings, causes):
    """The lane's own lines, settled by the look into safe text for the manifest (RUN-8): `fixed_text`, v1's fixed text of the
    preview, the summary and the hand-off prompt, and `last_record_head`, the last record's head lines (G20-5), each line a
    value the look freezes to a literal; `present_lines`, a preview line shown where a named path is present (G20-4), that
    path read once by the look. A line that is no literal is a value the look cannot settle."""
    def text(mark):
        try:
            frozen = values.freeze(mark, look)
        except values.Unsettled:
            frozen = None
        if not (isinstance(frozen, dict) and "literal" in frozen and len(frozen) == 1):
            findings.append({"row": None, "entry": entry, "finding": "a value the look cannot settle"})
            return ""
        return str(frozen["literal"])
    if entry == "fixed_text":
        # a hand-off line may name an operation (`when`): shown only where the run did it (G21-11; a layer the run lacked is
        # left out)
        return dict((form, [dict(line=text(m["line"]), when=m["when"]) if isinstance(m, dict) and "when" in m and "line" in m else text(m)
                            for m in marks]) for form, marks in sorted(spec.items()))
    if entry == "last_record_head":
        return [text(m) for m in spec]
    shown = []
    for item in spec:
        path = text(item["path"])
        try:
            there = bool(path) and session.world.fs.lexists(path)
        except OSError:
            causes.append("the read failed: the lane's preview line for %s" % path)
            continue
        if there:
            shown.append(text(item["line"]))
    return shown


def given_answer(look, name):
    """His answer to a lane question: the input of that name, his answer of that name, or a dotted planning fact
    (`flags.as_is`)."""
    if not name:
        return None
    found = look.inputs.get(name) or (look.inputs.get("answers") or {}).get(name)
    if found:
        return found
    try:
        return values._dig(look.facts, name)
    except values.Unsettled:
        return None


def read_questions(session, look, lane, causes):
    """The lane's questions asked only where their declared read fails (G20-4): each read once by the look, with the
    question's own commands, which change nothing (RUN-5); a question he has answered, or whose layer he dropped, is not
    read. A read that cannot be made is a failed read (RUN-7)."""
    asked = []
    for q in lane.get("questions") or []:
        test = q.get("when_read_fails")
        if not test or given_answer(look, q.get("input")) or (q.get("layer") and q["layer"] in (look.inputs.get("drop_layers") or [])):
            continue
        commands = expand({"rows": [{"commands": q.get("commands") or []}]}, session.providers)[0]["commands"]
        if any(not isinstance(c.get("declaration"), dict) or c["declaration"].get("effects", 0) != 0 for c in commands):
            raise BuildFailed([{"row": None, "entry": "questions", "finding": "a look that would change something (RUN-5)"}])
        try:
            reader = reads.Reader(session, {}, values.freeze_all(commands, look), lambda s, command, o, _op, _j: calls.call(s, command, o))
            verdict = reader.evaluate(values.freeze_all(test, look))
        except (runner.Refused, calls.NotCallable, values.Unsettled, OSError):
            verdict = reads.UNREADABLE
        if verdict == reads.UNREADABLE:
            causes.append("the read failed: the lane's question for %s" % q.get("input"))
        elif verdict is not True:
            asked.append(q.get("question"))
    return asked


# ---- found reads, lane facts and family rows (RUN-5 to RUN-7; G19-5 to G19-7) -------------------------------------
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def found_items(fs, spec):
    """The things a found read gives, each a dict of its fields, in a fixed order (a read of this machine, in-process):

        {"read": "files", "folder": P, "glob": G, "holding": T, "date": true}   the files of a folder whose name fits G (a
              name with `*` for any run of characters, it may begin with one subfolder) and whose text holds T where T is
              given: {"path", "name", "stem" (what `*` matched, else the name), "date" (the first line's, else the name's)};
              with `"tree": true`, the files of every folder under it too, a link never followed (G22-7, rows-set T17)
        {"read": "lines", "path": P, "holding": T, "name_after": A}             the lines of a file that hold T:
              {"line", "name" (the word after A up to `=` or white space, where A is given and stands in the line)}

    Raises OSError or UnicodeDecodeError where a read fails."""
    out = []
    if spec.get("read") == "files":
        glob = str(spec.get("glob") or "*")
        folder = os.path.join(str(spec["folder"]), os.path.dirname(glob)) if os.path.dirname(glob) else str(spec["folder"])
        fit = re.compile(re.escape(os.path.basename(glob)).replace("\\*", "(.*)"))
        if spec.get("tree"):
            paths = fs.walk(folder) if fs.isdir(folder) and not fs.islink(folder) else []
        else:
            paths = [os.path.join(folder, n) for n in sorted(fs.listdir(folder))] if fs.isdir(folder) else []
        for path in paths:
            name = os.path.basename(path)
            matched = fit.fullmatch(name)
            if matched is None or fs.islink(path) or not fs.isfile(path):
                continue
            text = fs.read_text(path) if spec.get("holding") or spec.get("date") else ""
            if spec.get("holding") and str(spec["holding"]) not in text:
                continue
            item = {"path": path, "name": name, "stem": matched.group(1) if matched.groups() else name}
            if spec.get("date"):
                first = DATE.search(text.split("\n")[0]) or DATE.search(name)
                if first:
                    item["date"] = first.group(0)
            out.append(item)
    elif spec.get("read") == "lines":
        path = str(spec["path"])
        if fs.isfile(path):
            for line in fs.read_text(path).split("\n"):
                if spec.get("holding") and str(spec["holding"]) in line:
                    item = {"line": line}
                    after = spec.get("name_after")
                    if after and after in line:
                        item["name"] = re.split(r"[=\s]", line.split(after, 1)[1], 1)[0]
                    out.append(item)
    else:
        raise ValueError("a found read of no kind this tool reads")
    return out


def _resolved_spec(spec, look):
    out = dict(spec)
    for key in ("folder", "glob", "path", "holding"):
        if isinstance(spec.get(key), dict):
            out[key] = values.resolve(values.freeze(spec[key], look), {})
    return out


def _item_marks(session, spec, item, row_id):
    """Each field of a found thing as a value: safe where the validator the read declares for that field passes and no entry
    of the register is in it (SEC-1's fourth source), else held in a protected record (SEC-6). A date is the tool's own
    match of the date's form, and is safe."""
    marks = {}
    declared = spec.get("validators") or {}

    def passes(field):
        name = declared.get(field)
        check = values.VALIDATORS.get(name) if name else (values.VALIDATORS["a date"] if field == "date" else None)
        return check is not None and check.fullmatch(item[field]) is not None and not session.register.holds(item[field])
    for field, text in sorted(item.items()):
        # a file's path is the tool's own build from the read's folder and the file's name: safe where the name is
        ok = passes(field) if field != "path" or "path" in declared else ("name" in item and passes("name"))
        if ok and not session.register.holds(text):
            marks[field] = {"literal": text}
        else:
            marks[field] = {"record": protected.write(session.world, session.run_dir, session.world.new_id("p"), text.encode("utf-8"),
                                                      "line" if field == "line" else "values",
                                                      "a field of a thing row %s was made for" % row_id)}
    return marks


def lane_facts(session, look, lane, causes, asked=None):
    """The lane's facts (G19-5): each one read the look makes of a thing there before the run, put among the planning facts,
    so that a condition and a value can name it. `path`: whether the path is present; `line`: whether a line of the file
    holds the value; `files` and `lines`: a found read, giving `count`, `found` (exactly one) and, where there is exactly
    one, that thing's safe fields. A read that fails is a failed read (RUN-7)."""
    fs = session.world.fs
    for spec in lane.get("facts") or []:
        if not isinstance(spec, dict) or not spec.get("name"):
            continue
        try:
            resolved = _resolved_spec(spec, look)
            read = spec.get("read")
            if read == "path":
                value = fs.lexists(str(resolved["path"]))
            elif read == "line":
                path = str(resolved["path"])
                value = fs.isfile(path) and any(str(resolved["holding"]) in line for line in fs.read_text(path).split("\n"))
            elif isinstance(spec.get("adopted"), dict) and adopted_at(session, look, spec) is not None:
                # G21-2 (rise's M-2): the destination is read first; a document already there is "already adopted", and its
                # staged source is not looked for
                value = {"count": 0, "found": False, "adopted": adopted_at(session, look, spec)}
            else:
                items = found_items(fs, resolved)
                value = {"count": len(items), "found": len(items) == 1}
                chosen = items[0] if len(items) == 1 else None
                if spec.get("choose") and items:
                    chosen = staged_choice(session, look, spec, items, asked if asked is not None else [])
                    value["found"] = chosen is not None
                if chosen is not None:
                    for field, mark in _item_marks(session, spec, chosen, spec["name"]).items():
                        if "literal" in mark:
                            value[field] = mark["literal"]
        except (OSError, UnicodeDecodeError, ValueError, KeyError, values.Unsettled):
            causes.append("the read failed: the lane's fact %s" % spec.get("name"))
            continue
        node = look.facts
        parts = str(spec["name"]).split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value


def adopted_at(session, look, spec):
    """A staged document's destination, read before its staged source (G21-2): the first document there whose name fits the
    read's pattern, by its path where its name passes the read's validator, else by the private file that holds it; None
    where none stands there."""
    where = dict((k, values.resolve(values.freeze(v, look), {})) for k, v in spec["adopted"].items())
    items = found_items(session.world.fs, {"read": "files", "folder": where["folder"], "glob": where["glob"]})
    if not items:
        return None
    mark = _item_marks(session, spec, {"path": items[0]["path"], "name": items[0]["name"]}, spec["name"])["path"]
    return mark["literal"] if "literal" in mark else "a document whose name is in a private file, %s" % protected.path_of(
        session.run_dir, mark["record"]["record"])


def filled_checks(candidates):
    """Each value filled into a row's text that names an output (G21-6): checked in the look by what that output's field
    holds in this plan, where an operation of it gives the field as a literal. Returns (refusals, findings)."""
    given = {}
    for row in candidates:
        output = row.get("output") if isinstance(row.get("output"), dict) else {}
        for field, value in (output.get("fields") or {}).items():
            if isinstance(value, dict) and set(value) == {"literal"}:
                given.setdefault(output.get("name"), {})[field] = value["literal"]
    refusals, findings = [], []

    def walk(row, node):
        if isinstance(node, list):
            for item in node:
                walk(row, item)
        elif isinstance(node, dict):
            if values.is_mark(node) and "checked" in node:
                try:
                    values.check(node["checked"]["validator"], values.resolve(node["checked"]["value"], given))
                except values.Refused as refused:
                    refusals.append(texts.PART_REFUSED.format(row=row["id"], validator=refused.validator))
                except values.Unsettled:
                    findings.append(rows.finding(row, "thing", "a value the look cannot settle"))
                return
            for item in node.values():
                walk(row, item)
    for row in candidates:
        walk(row, row)
    return refusals, findings


def staged_choice(session, look, spec, items, asked):
    """A staged document chosen in the look (G20-7; A150, the control room's reading, his to change by a word): where several
    match, the look lists them by the tool's own numbers and asks which one; where the one taken has no date, it asks for
    one. His answers (`answers.<fact>`, a number of the list; `answers.<fact>.date`, a date he types) choose before the
    preview. Returns the chosen thing with its date, or None with the question put in `asked`."""
    name = spec["name"]
    answers = look.inputs.get("answers") or {}
    chosen = items[0]
    if len(items) > 1:
        number = answers.get(name)
        if not (isinstance(number, str) and number.isdigit() and 1 <= int(number) <= len(items)):
            listing = []
            for n, item in enumerate(items, 1):
                mark = _item_marks(session, spec, {"name": item["name"]}, name)["name"]
                listing.append("%d: %s" % (n, mark["literal"] if "literal" in mark else "its name is in a private file, %s"
                                           % protected.path_of(session.run_dir, mark["record"]["record"])))
            asked.append(texts.CHOOSE_STAGED.format(fact=name, listing="; ".join(listing)))
            return None
        chosen = items[int(number) - 1]
    if "date" not in chosen:
        typed = answers.get(name + ".date")
        if not (isinstance(typed, str) and values.VALIDATORS["a date"].fullmatch(typed)):
            asked.append(texts.DATE_STAGED.format(fact=name))
            return None
        chosen = dict(chosen, date=typed)
    return chosen


EACH_TOKEN = re.compile(r"\{each\.([A-Za-z_]+)\}")


def _records_in(node):
    """Every protected record a value refers to, at any depth of its marks."""
    if isinstance(node, list):
        return [r for v in node for r in _records_in(v)]
    if isinstance(node, dict):
        if isinstance(node.get("record"), dict) and len(node) == 1:
            return [node["record"]]
        return [r for v in node.values() for r in _records_in(v)]
    return []


def issuer_findings(candidates, issuers):
    """SEC-2 for every held value a request of the frame's own carries, a protected record's reference among them (the
    reviewer's F2, G22-2): "Preserve and enforce issuer provenance for every held request value, including family members
    and protected-record references." `issuers` maps a record the look made from a provider's held value to that provider;
    a record it does not map, or maps to another provider, goes in no request, and the build fails naming the row."""
    out = []
    for row in candidates:
        for command in row.get("commands") if isinstance(row.get("commands"), list) else []:
            if not isinstance(command, dict) or (command.get("declaration") or {}).get("via") != "request":
                continue
            provider = command["use"].partition(".")[0] if isinstance(command.get("use"), str) else None
            if any(issuers.get(r.get("record")) != provider for r in _records_in(command.get("params") or {})):
                out.append(rows.finding(row, "commands", "a held value goes back only to the provider that issued it (SEC-2)"))
    return out


def expand_family(session, look, row):
    """A family row (G19-7): one ordinary operation per thing its found read gives, each with its own id (`<id>-<n>`), its
    `{"each": f}` marks the thing's fields, and each `{each.f}` in its texts (its output's name, its needs, its form lines)
    the field where it is safe and the member's number where it is held. Nothing downstream changes."""
    spec = row["thing"]["family"]
    if spec.get("read") == "command":
        # a look read's held list (the control room's item 7): the fixed members the row writes (`also`, safe), then one
        # member per value of the list, each held
        command = [c for c in row.get("commands") or [] if isinstance(c, dict) and c.get("name") == spec.get("command")][0]
        issuer = command["use"].partition(".")[0]
        result = calls.call(session, values.freeze_all(command, look), {})
        listed = result.held(spec.get("field")) if result.kind == "success" else None
        if not isinstance(listed, list):
            raise OSError("the list could not be read")
        # a member found in the list stays held; the row carries the tool's own label, `custom-<n>`, its place in the list,
        # for its id, its paths and its forms (the control room's G19-7 widened; SEC-2, SEC-3)
        items = ([{"member": str(v), "label": str(v)} for v in spec.get("also") or []]
                 + [{"member": str(v), "label": "custom-%d" % i, "_held": True} for i, v in enumerate(listed, 1)])
    else:
        items = found_items(session.world.fs, _resolved_spec(spec, look))
    members = []
    for n, item in enumerate(items, 1):
        held = item.pop("_held", False)
        marks = _item_marks(session, dict(spec, validators={"label": "a launch agent's label"} if held else
                                          {"member": "one line of plain words", "label": "a launch agent's label"})
                            if spec.get("read") == "command" else spec, item, row["id"])
        label = marks.get("label", {}).get("literal") if spec.get("read") == "command" else None
        if spec.get("read") == "command":
            # the issuer of each held member (G22-1's sibling, her F2): the provider of the family's own read
            for mark in marks.values():
                if isinstance(mark.get("record"), dict):
                    look.issuers[mark["record"]["record"]] = issuer
        within = spec.get("within") if isinstance(spec.get("within"), dict) else None
        if within and "path" in marks:
            # G21-12 (RUN-6): a thing inside a folder a move of this plan moves is placed by that move's output
            moved = str(values.resolve(values.freeze(within["folder"], look), {}))
            literal = marks["path"].get("literal")
            if isinstance(literal, str) and literal.startswith(moved.rstrip(os.sep) + os.sep):
                marks["place"] = {"path": [{"output": within["output"]}, {"literal": os.path.relpath(literal, moved)}]}
            else:
                marks["place"] = copy.deepcopy(marks["path"])
        shown = dict((f, m["literal"] if "literal" in m else (label or "#%d" % n)) for f, m in marks.items())
        shown["n"] = str(n)        # the member's index, carried by its outputs and needs (G21-9; a reverse keeps its row's)

        def put(node):
            if isinstance(node, list):
                return [put(v) for v in node]
            if isinstance(node, dict):
                if values.is_mark(node) and "each" in node:
                    if node["each"] not in marks:
                        raise values.Unsettled("a field the found thing does not have")
                    return copy.deepcopy(marks[node["each"]])
                return dict((k, put(v)) for k, v in node.items())
            if isinstance(node, str) and "{each." in node:
                return EACH_TOKEN.sub(lambda found: shown.get(found.group(1), "#%d" % n), node)
            return node
        member = put(copy.deepcopy(row))
        del member["thing"]["family"]
        member["id"] = "%s-%s" % (row["id"], label) if label else "%s-%d" % (row["id"], n)
        members.append(member)
    return members


class LocalUnreadable(values.Unsettled):
    """A file on this machine a row's `local` mark names cannot be read: a failed read (RUN-7)."""


def local_value(session, path, validator):
    """SEC-1's fourth safe source: the content of a file on this machine, read in-process (one line, its ending newline left
    out). Where the validator the row declares passes it, and no entry of the register is in it, it is safe and the
    manifest holds it as a literal; otherwise it is protected ("Content the run read from the owner's files and has not
    validated"): it rests in a protected record, and the manifest refers to it (RUN-8, SEC-6)."""
    world = session.world
    try:
        text = world.fs.read_text(path)
    except (OSError, UnicodeDecodeError):
        raise LocalUnreadable(path)
    if text.endswith("\n"):
        text = text[:-1]
    check = values.VALIDATORS.get(validator)
    if check is not None and check.fullmatch(text) and not session.register.holds(text):
        return {"literal": text}
    reference = protected.write(world, session.run_dir, world.new_id("p"), text.encode("utf-8"), "values",
                                "the content of a file on this machine that its row's validator did not pass")
    return {"record": reference}


def present_places(row):
    """RUN-6: "A thing that lies inside a thing another operation moves is named relative to that operation's output: the
    look reads it where it is, and the probe reads it where the move's record says it went." For a move planned `in`, the
    fields of its output that name where the move puts the thing, each given the place where the thing is now: {output
    name: {field: present path}}. Empty for any other row."""
    construction = row.get("construction") if isinstance(row.get("construction"), dict) else {}
    output = row.get("output") if isinstance(row.get("output"), dict) else {}
    if row.get("kind") != "move" or construction.get("id") != "C7" or not output.get("name"):
        return {}
    try:
        to = values.resolve(construction.get("to"), {})
        where = values.resolve((row.get("thing") or {}).get("place"), {})
    except values.Unsettled:
        return {}
    fields = {}
    for field, value in (output.get("fields") or {}).items():
        try:
            if values.resolve(value, {}) == to:
                fields[field] = where
        except values.Unsettled:
            continue
    return {output["name"]: fields} if fields else {}


def plan_row(session, look, row, state, causes, held_things, resend=False, present=None):
    """One candidate: (`in` | `already so` | `not applicable` | `stop`, detail). `present` is what `present_places` gives
    for the moves this plan has planned `in` before this row."""
    fs = session.world.fs
    op, kind = row["id"], row["kind"]
    thing = row.get("thing") if isinstance(row.get("thing"), dict) else {}
    capability = thing.get("capability")
    if capability and capability not in look.capabilities:
        if kind == "check":
            row["planned_unavailable"] = True
            return "in", {}
        return "not applicable", {"reason": "not available on this harness"}
    if kind == "owner answer":
        row["resolved_mode"] = "answer"
    if kind == "owner step":
        row["resolved_mode"] = row.get("mode")
    if state is not None and (state.starts.get(op) or op in state.waiting_records) and not resend:
        return "in", {}                     # the journal shows the run began it: the probe decides, not the look
    own = (row.get("output") or {}).get("name") if isinstance(row.get("output"), dict) else None
    refers = [r for r in values.refers_to([row.get("thing"), row.get("planning_test"), row.get("before_test"), row.get("commands")])
              if r.partition(".")[0] != own]
    outputs = {}
    if refers:
        present = present or {}
        if not all(r.partition(".")[0] in present and r.partition(".")[2] in present[r.partition(".")[0]] for r in refers):
            return "in", {}                 # it depends on what the plan is to make: the probe tests it (RUN-6)
        # a thing inside a thing a move of this plan moves: the look reads it where it is now (RUN-6); the manifest keeps
        # the reference, and the probe reads it where the move's record says it went
        outputs = present
    connection = []                 # SEC-2's password file, for a look's command that declares its slot (G20-1; G9)
    reader = reads.Reader(session, outputs, row.get("commands") if isinstance(row.get("commands"), list) else [],
                          lambda s, command, o, _op, _j: calls.call(s, command, o, connection=connection[0] if connection else None))

    def unreadable(what):
        causes.append("%s: %s of row %s" % (READ_KINDS.get(reader.last_kind, READ_KINDS[None]), what, op))
        return "stop", {}

    secret = thing.get("secret_read")
    if isinstance(secret, dict):
        path = values.resolve(secret["file"], outputs)
        address = channels.read_connection(session.world, path, secret.get("keys") or [])
        if not address:
            causes.append("a secret the look needs is in no file on this machine (row %s); run this yourself and summon again: %s"
                          % (op, secret.get("command_to_show", "")))
            return "stop", {}
        session.register.add(address, channels.address_components(address), None, "channel")
        row["_secret_read"] = {"file": path, "keys": list(secret.get("keys") or [])}
        built = (row.get("construction") or {}).get("connection") if isinstance(row.get("construction"), dict) else None
        connection.append((address, (built or {}).get("slot", "passfile") if isinstance(built, dict) else "passfile", op))
    try:
        if kind in ("build", "keep", "create"):
            tests = row.get("planning_test") if isinstance(row.get("planning_test"), list) else []
            scope = [c for c in tests if c.get("id") == "scope"]
            free = reader.evaluate([c for c in tests if c.get("id") != "scope"])
            if free == reads.UNREADABLE:
                return unreadable("the place")
            if free is not True:
                causes.append("the place is taken by a thing this run did not make: row %s" % op)
                if row.get("reverse_of") and thing.get("place") is not None:
                    # EV-7: a reverse that would make a thing where an earlier restore made one: the place is named
                    causes.append("the place taken: %s" % values.resolve(thing["place"], outputs))
                return "stop", {}
            if scope:
                whole = reader.evaluate(scope)
                if whole == reads.UNREADABLE:
                    return unreadable("the keep's scope")
                if whole is not True:       # KEEP-1: where the look can already see that the whole scope cannot be read
                    causes.append("the whole scope of a keep cannot be read or established: row %s" % op)
                    told = unreadable_told(session, row, outputs)
                    if told:
                        causes.append(told)
                    return "stop", {}
        elif kind in ("change", "move"):
            after = reader.evaluate(row.get("after_test"))
            if after == reads.UNREADABLE:
                return unreadable("the thing")
            if after is True:
                return "already so", {}
            tests = row.get("before_test") if isinstance(row.get("before_test"), list) else []
            names = [c for c in tests if isinstance(c, dict) and c.get("read") == "name-free"]
            before = reader.evaluate([c for c in tests if c not in names])
            if before == reads.UNREADABLE:
                return unreadable("the thing")
            if before is not True:
                causes.append("the thing is in neither state the row names: row %s" % op)
                edit = (row.get("construction") or {}).get("edit") if isinstance(row.get("construction"), dict) else None
                if row.get("reverse_of") and isinstance(edit, dict) and thing.get("place") is not None:
                    from . import effects
                    causes.append(effects.placement_unmet(None, row, values.resolve(thing["place"], outputs), op))
                return "stop", {}
            if names:
                # RUN-7's `in` for a shortcut's line, added or put back: its name is free, as his login zsh finds it (A55)
                free = reader.evaluate(names)
                if free == reads.UNREADABLE:
                    return unreadable("whether the shortcut's name is free")
                if free is not True:
                    causes.append(texts.SHORTCUT_NAME_TAKEN.format(row=op))
                    return "stop", {}
        elif kind == "adopt":
            present = reader.evaluate(row.get("planning_test"))
            if present is not True:
                causes.append("the thing named for adoption is not there, or cannot be read: row %s" % op)
                return "stop", {}
    except (runner.Refused, calls.NotCallable, values.Unsettled):
        causes.append("the read failed: row %s" % op)
        return "stop", {}
    name_form = thing.get("name_form")
    if isinstance(name_form, dict):
        try:
            result = calls.call(session, [c for c in row["commands"] if c["name"] == name_form["command"]][0], outputs)
        except (runner.Refused, calls.NotCallable, IndexError):
            return unreadable("the project's name at the provider")
        kept = result.fields.get(name_form.get("field", "name")) if result.kind == "success" else None
        if result.kind == "success" and kept is not None and kept.is_held:
            holds = [n for n in session.names + session.alias_names]
            if kept.held not in holds:
                reference = protected.write(session.world, session.run_dir, session.world.new_id("p"), str(kept.held).encode("utf-8"),
                                            "held field", "the other name a provider shows the project under")
                causes.append("a provider shows the project under another name; the private file that holds it: %s; "
                              "summon again and give that name too" % protected.path_of(session.run_dir, reference["record"]))
                return "stop", {}
    listing = thing.get("found_things")
    if isinstance(listing, dict):
        try:
            result = calls.call(session, [c for c in row["commands"] if c["name"] == listing["command"]][0], outputs)
        except (runner.Refused, calls.NotCallable, IndexError):
            return unreadable("what is at the provider")
        kept = result.fields.get(listing.get("field", "name")) if result.kind == "success" else None
        if kept is not None and kept.is_held:
            # a thing found at a provider under a name he did not type: its kind, how many, and a private file (SEC-6)
            reference = protected.write(session.world, session.run_dir, session.world.new_id("p"),
                                        (str(kept.held) + "\n").encode("utf-8"), "values",
                                        "the %s found at %s" % (listing.get("kind", "things"), listing.get("provider", "a provider")))
            held_things.append({"count": 1, "kind": listing.get("kind", "things"), "provider": listing.get("provider", "a provider"),
                                "file": protected.path_of(session.run_dir, reference["record"])})
    detail = {}
    if thing.get("place") is not None:
        path = values.resolve(thing["place"], outputs)
        detail["tracked_state"] = reads.tracked_state(fs, path, thing.get("tracked") or ("exists", "identity", "sha256", "mode"))
        if kind in ("build", "keep", "change"):
            parent = path if fs.lexists(path) else os.path.dirname(path)
            if fs.volume(parent) != fs.volume(session.run_dir):
                causes.append("the place is on another volume: %s" % path)
                return "stop", {}
    also = []
    for other in thing.get("also") or []:
        if other.get("place") is None:
            # a thing named by a held id an operation of this plan provides: the look reads nothing it is to make (RUN-6)
            also.append({})
            continue
        also.append(reads.tracked_state(fs, values.resolve(other["place"], outputs), other.get("tracked") or ("exists", "sha256")))
    if also:
        detail["also_states"] = also
    return "in", detail


def unreadable_told(session, row, outputs):
    """KEEP-1: what of a keep's scope cannot be read, told as SEC-6 has held names told: the kind of thing, how many by
    the tool's own count, and the private file that lists them; a name a provider gave is in no form and no output.
    None where the row declares no such read or the read gives nothing."""
    spec = (row.get("keep_scope") or {}).get("unreadable_read")
    if not isinstance(spec, dict):
        return None
    try:
        command = [c for c in row["commands"] if c["name"] == spec.get("command")][0]
        result = calls.call(session, command, outputs)
    except (runner.Refused, calls.NotCallable, IndexError, values.Unsettled):
        return None
    kept = result.fields.get(spec.get("field")) if result.kind == "success" else None
    names = [str(kept.held)] if kept is not None and kept.is_held else []
    if not names:
        return None
    kind = spec.get("kind") or "thing"
    reference = protected.write(session.world, session.run_dir, session.world.new_id("p"),
                                ("\n".join(names) + "\n").encode("utf-8"), "values",
                                "the %ss of row %s that cannot be read" % (kind, row.get("id")))
    path = protected.path_of(session.run_dir, reference["record"])
    if len(names) == 1:
        return "1 %s of row %s cannot be read; its name is in a private file: %s" % (kind, row.get("id"), path)
    return "%d %ss of row %s cannot be read; their names are in a private file: %s" % (len(names), kind, row.get("id"), path)


def status_of_request(session, row, lost):
    """OP-7's first way, as the look may make it: the provider's own read of the status of that very
    request. Returns the fixed word it gave, or None."""
    try:
        command = [c for c in row["commands"] if c["name"] == lost.get("command")][0]
        result = calls.call(session, command, {})
    except (runner.Refused, calls.NotCallable, IndexError, KeyError, TypeError):
        return None
    return result.safe().get(lost.get("field", "made")) if result.kind == "success" else None


def tie_retirements(session, operations, not_applicable):
    """KEEP-2: a retirement is planned `in` only if the look read the same identity from both
    sides. Where that cannot be read, the keep stays, the retirement is `not applicable`, and the
    preview says what will not be retired and the step the owner can take himself."""
    by_id = dict((o["id"], o) for o in operations)

    def identity(operation, spec):
        try:
            result = calls.call(session, [c for c in operation["commands"] if c["name"] == spec["command"]][0], {})
        except (runner.Refused, calls.NotCallable, IndexError, KeyError, TypeError):
            return None
        return result.held(spec.get("field")) if result.kind == "success" else None
    for operation in list(operations):
        thing = operation.get("thing") if isinstance(operation.get("thing"), dict) else {}
        required = operation.get("keeps_required") if isinstance(operation.get("keeps_required"), list) else []
        if not thing.get("retires") or not required:
            continue
        mine = identity(operation, thing.get("identity_read") or {})
        tied = mine is not None
        for keep_id in required:
            keep = by_id.get(keep_id)
            source = identity(keep, (keep.get("keep_scope") or {}).get("source_identity_read") or {}) if keep else None
            tied = tied and source is not None and source == mine
        if not tied:
            operations.remove(operation)
            not_applicable.append({"row": operation["id"], "reason": "cannot be tied to its copy",
                                   "what": (operation.get("form_lines") or {}).get("preview") or operation["id"],
                                   "step": (operation.get("form_lines") or {}).get("owner_step", "")})


def build(session, kind, look, number, state=None, journal_count=0):
    """Build manifest `number` for the run. `state` is the journal's, on a re-plan."""
    lane = session.lane
    if not isinstance(lane, dict):
        raise BuildFailed([{"row": None, "entry": "lane", "finding": "no lane has written rows for this kind of run"}])
    if state is None and not journalmod.opening_fits(len(session.prints)):
        # RUN-5 (batch 27): the keys this look holds would make its run's record of its opening longer than the most a
        # look reads of a first record; no rule says what follows, and the look stops (GOV-1). A re-plan adds no key
        # (RUN-3) and meets RUN-2's stop for a name the run does not hold first, so it never comes here.
        raise PlanningStop([texts.TOO_MANY_NAMES])
    expanded = expand(lane, session.providers)
    findings = admit_all(lane, expanded, session.providers)
    if findings:
        raise BuildFailed(findings)
    kept = lane.get("types")
    if isinstance(kept, list) and look.inputs.get("type") is not None and look.inputs.get("type") not in kept:
        # G20-3: a type off the lane's list of kept types is refused before the look reads anything, in plain words
        raise PlanningStop([texts.TYPE_NOT_KEPT.format(type=look.inputs.get("type"), kept=", ".join(kept))])
    lacking = []
    for q in lane.get("questions") or []:
        if q.get("layer") and q["layer"] in (look.inputs.get("drop_layers") or []):
            continue
        given = given_answer(look, q.get("input"))
        if q.get("required") and not given and not q.get("when_read_fails"):
            lacking.append(q.get("question"))
        elif given and q.get("validator"):
            check = values.VALIDATORS.get(q["validator"])
            if check is None:
                raise BuildFailed([{"row": None, "entry": "questions", "finding": "a validator this tool does not have"}])
            if not isinstance(given, str) or check.fullmatch(given) is None:
                lacking.append(texts.ANSWER_REFUSED.format(question=q.get("question"), validator=q["validator"]))
    if lacking:
        raise Questions(lacking)
    causes = []
    look.project_memory = lambda folder: session.facts.project_memory(session.world.fs, folder)      # G21-10 (E16-12)
    look.tables = lane.get("tables") or {}       # the lane's own tables, keyed by a planning fact (G21-1)
    look.date = session.world.now()[:10]       # the run's date, by the tool's own clock, read once here and frozen (RUN-8)
    earlier = earlier_runs(session)
    journals, other_held = read_other_runs(session, earlier)
    session.other_held = other_held
    retiring, not_offered, unoffered, retired_tracked = None, [], [], {}
    if kind == "restore":
        # EV-5, EV-7: a restore builds its manifest from the latest retiring run's journal; its reverses are ordinary
        # operations under every rule, admitted as rows of their own kind in this lane's phases, and planned first
        retiring = retiring_run(journals)
        if session.over is not None and session.over != retiring:
            # EV-7 (batch 30): a retirement of the key is open and the latest sunset by time is another run, which only a
            # clock set back can make; the restore would build from a run that is not open, its go closing nothing, and
            # RUN-3 lets no summons but a restore over that open retirement through: the look ends as RUN-7's planning
            # stop, nothing closed and nothing planned from either run
            raise PlanningStop([texts.OPEN_RETIREMENT_NOT_LATEST])
        reverses, not_offered, unoffered, retired_tracked = restore_offer(session, look, retiring, journals[retiring], other_held)
        marks = [dict((k, r.pop(k)) for k in ("reverse_of", "not_proven") if k in r) for r in reverses]
        reverses = expand({"rows": reverses}, session.providers)
        for reverse in reverses:
            findings += rows.admit(reverse, session.providers, held_outputs(reverses + expanded), as_reverse=True)
            if reverse.get("phase") not in (lane.get("phases") or []):
                findings.append(rows.finding(reverse, "phase", "not a phase the lane declares (ORD-4)"))
        if findings:
            raise BuildFailed(findings)
        for reverse, mark in zip(reverses, marks):
            reverse.update(mark)
        expanded = reverses + expanded
        if other_held.holds(retiring):
            retiring = None
    candidates, excluded = [], list(unoffered)
    look.local = lambda path, validator: local_value(session, path, validator)
    asked = []
    lane_facts(session, look, lane, causes, asked)
    asked += read_questions(session, look, lane, causes)
    if asked and not causes:
        raise Questions(asked)
    flat = []
    look.issuers = {}               # a protected record the look made from a provider's held value: its issuer (G22-2)
    for row in expanded:
        family = (row.get("thing") or {}).get("family") if isinstance(row.get("thing"), dict) else None
        if isinstance(family, dict) and excluded_by_inputs(look, row) is None:
            try:
                members = expand_family(session, look, row)
            except (OSError, UnicodeDecodeError, ValueError, KeyError, IndexError, runner.Refused, calls.NotCallable):
                causes.append("the read failed: the things row %s is made for" % row["id"])
                continue
            except values.Unsettled:
                findings.append(rows.finding(row, "thing", "a value the look cannot settle"))
                continue
            if not members:
                excluded.append({"row": row["id"], "reason": "none found", "what": row["id"]})
            flat += members
            continue
        flat.append(row)
    refusals = []
    for row in flat:
        reason = excluded_by_inputs(look, row)
        if reason is not None:
            excluded.append({"row": row["id"], "reason": reason, "what": (row.get("form_lines") or {}).get("preview") or row["id"]})
            continue
        try:
            frozen = values.freeze_all(dict((k, v) for k, v in row.items() if k not in ("commands", "owner_names")), look)
            frozen["commands"] = values.freeze_all(row["commands"], look) if isinstance(row.get("commands"), list) else row.get("commands")
            frozen["owner_names"] = row.get("owner_names")       # how the owner names the thing: a statement, no value
        except LocalUnreadable:
            causes.append("the read failed: a file on this machine of row %s" % row["id"])
            continue
        except values.Refused as refused:
            refusals.append(texts.PART_REFUSED.format(row=row["id"], validator=refused.validator))
            continue
        except values.Unsettled:
            findings.append(rows.finding(row, "thing", "a value the look cannot settle"))
            continue
        candidates.append(frozen)
    if refusals:
        raise Questions(refusals)
    if findings:
        raise BuildFailed(findings)
    search = session.facts.search_list(session.world.fs, session.world.system_folders)
    for tool in sorted(set((c.get("declaration") or {}).get("tool") for row in candidates
                           for c in (row.get("commands") if isinstance(row.get("commands"), list) else []) if isinstance(c, dict)) - {None}):
        if runner.find(session.world, tool, search) is None:      # the tools on the search list (RUN-5, RUN-7, SEC-3)
            causes.append(texts.PROGRAM_NOT_FOUND.format(program=tool, settings=session.facts.settings_path))
    if causes:
        raise PlanningStop(causes)
    accounts = identity_reads(session, providers_used(candidates), causes)
    # an account mark is settled once the identity reads have proved each account (SEC-4's ground C): the second freeze
    look.accounts = accounts
    for index, row in enumerate(candidates):
        try:
            again = values.freeze_all(dict((k, v) for k, v in row.items() if k != "owner_names"), look)
        except values.Unsettled:
            if not causes:
                findings.append(rows.finding(row, "thing", "a value the look cannot settle"))
            continue
        again["owner_names"] = row.get("owner_names")
        candidates[index] = again
    refusals, more = filled_checks(candidates)
    if refusals:
        raise Questions(refusals)
    findings += more + issuer_findings(candidates, look.issuers)
    if findings:
        raise BuildFailed(findings)
    operations, already, not_applicable, held_things, secret_reads = [], [], list(excluded), [], []
    carried = dict((op, status) for op, status in (state.finals.items() if state is not None else []))
    earlier_outstanding = set()
    for run_id, journal in journals.items():
        seen_start, seen_answer, starts_of, steps_of = set(), set(), {}, {}
        for record in journal.records:
            if record.get("kind") == "start":
                seen_start.add(record.get("op"))
                starts_of.setdefault(record.get("op"), []).append(record)
            if record.get("kind") == "step":
                steps_of.setdefault(record.get("op"), []).append(record)
            if record.get("kind") in ("answer", "completion", "status"):
                seen_answer.add(record.get("op"))
        # OP-7 (A99): a create whose latest start record is followed by the step record of the runner's refusal of its send
        # is not outstanding; with no such record after it, it is, and every later look for the key reads it so
        earlier_outstanding |= set(op for op in seen_start - seen_answer if not statemod.unsent(starts_of.get(op), steps_of.get(op)))
    present = {}                            # RUN-6: where the things the plan's moves move stand now
    for row in candidates:
        op = row["id"]
        what = (row.get("form_lines") or {}).get("preview") or op
        if op in carried:
            row["planning_outcome"] = "in"
            operations.append(row)
            continue
        resend = False
        if row["kind"] == "create":
            lost = row.get("lost_answer") if isinstance(row.get("lost_answer"), dict) else {}
            mine = state is not None and op in state.outstanding
            if mine or (op in earlier_outstanding and state is None):
                way = lost.get("way")
                if way in ("provider-unique", "idempotency-key"):
                    resend = True               # the provider guarantees a second send cannot make a second thing
                elif way == "status-read" and mine:
                    word = status_of_request(session, row, lost)
                    if word == lost.get("nothing_word", "nothing"):
                        resend = True           # "made nothing and will make nothing": it may be planned again
                    elif word == lost.get("made_word", "made"):
                        row["resolve_by_status"] = True
                    else:
                        causes.append("a create was sent and no answer came, and its provider does not say what became of it: row %s" % op)
                        continue
                else:
                    causes.append("a create was sent and no answer came, and only dropping its layer resolves it: row %s" % op)
                    continue
                if resend:
                    row["resend"] = True
                    if mine:
                        row["fresh_from"] = journal_count
        outcome, detail = plan_row(session, look, row, state, causes, held_things, resend, present)
        if "_secret_read" in row:
            secret_reads.append(row.pop("_secret_read"))
        if outcome == "not applicable":
            not_applicable.append({"row": op, "reason": detail["reason"], "what": what})
            continue
        if outcome == "already so":
            output = row.get("output") if isinstance(row.get("output"), dict) else {}
            already.append({"row": op, "what": what, "output": output.get("name"),
                            "fields": dict((k, v) for k, v in (output.get("fields") or {}).items() if isinstance(v, dict) and "literal" in v)})
            continue
        if outcome == "stop":
            continue
        if row.get("reverse_of") and isinstance(detail.get("tracked_state"), dict):
            # EV-5, EV-3: a reverse's thing must be in the last tracked state the retiring run's journal holds for it; a
            # difference is `foreign`, and the restore stops, naming the thing by its role and its safe name, its path
            now = detail["tracked_state"]
            path = now.get("path")
            expected = retired_tracked.get(path)
            if expected is not None and any(now.get(f) != expected.get(f) for f in ("exists", "identity", "sha256") if f in expected and f in now):
                causes.append("the thing is not in the last tracked state the retiring run's journal holds: %s, %s: row %s"
                              % ((row.get("thing") or {}).get("role") or "a thing the operation names", path, op))
                continue
        row["planning_outcome"] = "in"
        row.update(detail)
        present.update(present_places(row))
        if row["kind"] == "owner step" and isinstance(row.get("reverse_inputs"), list):
            for item in row["reverse_inputs"]:
                if item.get("read") == "file" and not session.world.fs.isfile(values.resolve(item["path"], {})):
                    row["no_reverse"] = True
        operations.append(row)
    tie_retirements(session, operations, not_applicable)
    impossible = {}
    if state is not None:
        for operation in operations:
            for need in operation.get("needs") if isinstance(operation.get("needs"), list) else []:
                verdict, provider, status = state.need(need) if state.providers_of(need["output"]) else ("wait", None, None)
                if verdict in ("stop", "branch", "his") and operation["id"] not in carried:
                    impossible[(operation["id"], need["output"])] = status
    operations, settled, more = settle_needs(operations, already, not_applicable, impossible)
    findings = more + shape_findings(kind, lane, operations)
    lane_lines = {}
    for entry in ("fixed_text", "last_record_head", "present_lines"):
        if entry in lane:
            lane_lines[entry] = lane_texts(session, look, entry, lane[entry], findings, causes)
    if findings:
        raise BuildFailed(findings)
    for text in texts_in(look.inputs):
        if session.register.holds(text):
            raise InputRefused()
    if causes:
        raise PlanningStop(causes)
    manifest = {"manifest_version": 1, "run": session.run_id, "kind": kind, "number": number,
                "inputs": look.inputs, "names": list(look.names), "keys": sorted(session.prints),
                "accounts": accounts, "capabilities": sorted(look.capabilities),
                "locations": look.locations, "phases": list(lane.get("phases") or []), "operations": operations,
                "already_so": already, "not_applicable": not_applicable, "held_things": held_things,
                "settled_needs": settled, "secret_reads": secret_reads, "form_changes": lane.get("form_changes") or {},
                "carried": carried}
    manifest.update(lane_lines)
    if session.alias_names:
        # the name forms this look's alias reads showed are content read from the owner's files and not validated
        # (protected, SEC-1): they rest in a protected record the manifest refers to, so that a later go whose alias reads
        # no longer show one can name the private file that holds it (RUN-9, A79)
        manifest["alias_names"] = protected.write(session.world, session.run_dir, session.world.new_id("p"),
                                                  "".join(n + "\n" for n in session.alias_names).encode("utf-8"), "values",
                                                  "the other names the look's alias reads showed")
    if kind == "restore":
        manifest["retiring"] = retiring
        manifest["not_offered"] = not_offered
    return manifest
