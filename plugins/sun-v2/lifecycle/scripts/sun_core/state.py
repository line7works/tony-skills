"""What a run's journal says, read against its manifest (the frame's ORD-1, EV-2, EV-3, OP-7, OP-8).

`State` is derived, every time, from the manifest in force and the journal, and from nothing else:
each operation's final status, what is outstanding and what waits on the owner, which outputs are
bound and to what, the last tracked state the journal holds for each thing, each check's attempts,
the receipts that are due and not given, and the disproof records.

`CELLS` is ORD-1's table: what a provider that ended in a final status is to a need at a level.
"""
from . import disproof as disproofmod
from . import values

FINAL = ("done", "already so", "not proven", "adopted", "passed", "unavailable", "refused",
         "done by owner, read back", "done by owner, on his word", "answered", "left", "not needed", "held")
LEVELS = ("state", "made", "passed", "answered")
#                                    state     made      passed    answered
CELLS = {
    "done":                         ("meets",  "meets",  "stop",   "stop"),
    "already so":                   ("meets",  "stop",   "stop",   "stop"),
    "not proven":                   ("meets",  "stop",   "stop",   "stop"),
    "adopted":                      ("meets",  "stop",   "stop",   "stop"),
    "passed":                       ("stop",   "stop",   "meets",  "stop"),
    "unavailable":                  ("stop",   "stop",   "accepts", "stop"),
    "refused":                      ("branch", "branch", "branch", "branch"),
    "done by owner, read back":     ("meets",  "stop",   "stop",   "stop"),
    "done by owner, on his word":   ("accepts", "stop",  "stop",   "stop"),
    "answered":                     ("stop",   "stop",   "stop",   "value"),
    "left":                         ("his",    "his",    "his",    "his"),
    "not needed":                   ("branch", "branch", "branch", "branch"),
    "held":                         ("his",    "his",    "his",    "his"),
}
ACCEPTS = {"unavailable": "unavailable", "done by owner, on his word": "his word"}
# a thing that existed before the run is bound by the look's resolution; one the run was to make,
# by `done` or `adopted` and by nothing else (EV-2)
BINDS_MADE = ("done", "adopted")
BINDS_EXISTING = ("done", "already so", "not proven", "done by owner, read back", "done by owner, on his word")


# LOG-2 (the owner's ruling, A99): the step record of the runner's refusal of a create's send, written only where the runner
# refused it before any child was created, so that it stands only where no request left the tool
SEND_REFUSED = "send-refused"


def unsent(starts, steps):
    """Whether the step record of the runner's refusal of a create's send follows its latest start record. OP-7: "A create
    with a start record and no recorded answer is outstanding, whatever the world shows, and the run stops, but for one
    case: where the start record is followed by the step record of the runner's refusal of its send (LOG-2), no request
    left the tool, and the create is not outstanding ... Where a kill falls between the start record and that step record,
    the create is outstanding, since the tool cannot then tell." A refusal that follows an earlier start record, and no
    longer the latest, says nothing of the latest send."""
    if not starts:
        return False
    latest = starts[-1].get("n", -1)
    return any(s.get("step") == SEND_REFUSED and s.get("n", -1) > latest for s in steps or [])


def cell(status, need, answer_value=None):
    """`meets`, `stop`, `his` or `branch` for one provider's final status against one need."""
    raw = CELLS[status][LEVELS.index(need["level"])]
    if raw == "accepts":
        return "meets" if ACCEPTS[status] in (need.get("accepts") or []) else "stop"
    if raw == "value":
        return "meets" if answer_value == need.get("value") else "his"
    return raw


class State(object):
    def __init__(self, manifest, journal):
        self.manifest = manifest
        self.ops = dict((o["id"], o) for o in manifest.get("operations") or [])
        self.order = [o["id"] for o in manifest.get("operations") or []]
        self.finals, self.reasons, self.starts, self.steps, self.answers = {}, {}, {}, {}, {}
        self.attempts, self.completions, self.waiting_records, self.owner_answers = {}, {}, {}, {}
        self.tracked, self.marks, self.records_of = {}, set(), {}
        self.adopted_identity, self.steps_shown = {}, {}
        self.unknown = []
        self.fresh = {}
        self.read_now = set()             # set by the engine: the steps whose read this invocation made and answered (OP-9)
        # the manifest in force took force at the latest go on record; what stands before it may speak of an
        # operation a re-plan has since dropped (RUN-11), and that is no record without a rule
        self.in_force_from = max([r["n"] for r in journal.records if r.get("kind") in ("open", "go")] or [0])
        for record in journal.records:
            self._take(record)
        self.receipts_due = disproofmod.receipts_due(journal.records)
        self.disproofs = [r for r in journal.records if r.get("kind") == "disproof"]
        for op, found in self.attempts.items():
            if found and found[-1]["answer"] in ("passed", "unavailable"):
                self.finals[op] = found[-1]["answer"]
        # a create with a start record and no recorded answer, but for one whose latest start record is followed by the step
        # record of the runner's refusal of its send (OP-7; A99): that one is not outstanding, and its probe reads the world
        self.unsent = set(op for op in self.order if self.ops[op].get("kind") == "create" and not self.answers.get(op)
                          and op not in self.finals and unsent(self.starts.get(op), self.steps.get(op)))
        self.outstanding = set(op for op in self.order if self.ops[op].get("kind") == "create" and self.starts.get(op)
                               and not self.answers.get(op) and op not in self.finals and op not in self.unsent)
        self.waiting = set(op for op in self.order if op in self.waiting_records and op not in self.finals)
        self.outputs = {}
        self._bind()

    def _track(self, thing):
        if isinstance(thing, dict) and thing.get("path"):
            self.tracked[thing["path"]] = thing
            if thing.get("target"):
                self.tracked[thing["target"]] = None

    def _take(self, record):
        kind, op = record.get("kind"), record.get("op")
        if op is not None and op not in self.ops and kind not in ("disproof",):
            if record.get("n", 0) >= self.in_force_from:
                self.unknown.append(record)
            return
        if kind in ("start", "step", "answer") and record["n"] < self.ops[op].get("fresh_from", 0):
            return                      # an earlier send, planned again by a re-plan (OP-7)
        if kind == "start":
            self.starts.setdefault(op, []).append(record)
            self._track(record.get("thing"))
            for reference in record.get("inputs") or []:
                self.records_of.setdefault(op, []).append(reference)
        elif kind == "step":
            self.steps.setdefault(op, []).append(record)
            if record.get("step") == "risk-mark":
                self.marks.add((op, record.get("risk")))
            if record.get("step") == "reverse-inputs-saved":
                for reference in record.get("inputs") or []:
                    self.records_of.setdefault(op, []).append(reference)
        elif kind == "answer":
            self.answers.setdefault(op, []).append(record)
        elif kind == "completion":
            self.completions[op] = record
            self.finals[op] = "done"
            self._track(record.get("observed"))
            moved = ((self.starts.get(op) or [{}])[-1]).get("thing") or {}
            if moved.get("target") and moved.get("path"):
                # a move that is done left nothing at its source: the state the run left that place in (EV-3)
                self.tracked[moved["path"]] = {"path": moved["path"], "exists": False, "identity": None, "sha256": None}
        elif kind == "status":
            if record.get("status") not in FINAL:
                self.unknown.append(record)       # a status no rule names (GOV-1)
                return
            self.finals[op] = record["status"]
            self.reasons[op] = record.get("reason") or {}
            self._track(record.get("observed"))
            if record.get("binds"):
                self.adopted_identity[op] = "the object %s of volume %s" % ((record["binds"].get("identity") or {}).get("object"),
                                                                           (record["binds"].get("identity") or {}).get("volume"))
        elif kind == "attempt":
            self.attempts.setdefault(op, []).append(record)
            self._track(record.get("subject"))
        elif kind == "waiting":
            self.waiting_records[op] = record
            for reference in record.get("inputs") or []:
                self.records_of.setdefault(op, []).append(reference)
            if record.get("review"):
                self.records_of.setdefault(op, []).append(record["review"])
        elif kind == "owner-answer":
            self.owner_answers[op] = record

    def _bind(self):
        """The outputs that are bound, in manifest order, so that one may be built from another."""
        for item in self.manifest.get("already_so") or []:
            if item.get("output") and isinstance(item.get("fields"), dict):
                self._bind_fields(item["output"], item["fields"], None)
        for op in self.order:
            operation = self.ops[op]
            status = self.finals.get(op)
            output = operation.get("output") if isinstance(operation.get("output"), dict) else None
            if status is None or not output:
                continue
            made = operation.get("kind") in ("build", "create", "keep", "adopt")
            if status in (BINDS_MADE if made else BINDS_EXISTING):
                self._bind_fields(output["name"], output.get("fields") or {}, op)

    def with_own(self, op):
        """The outputs as an operation's own reads see them: its own output's fields are bound for it
        as soon as the journal holds them (a create's after-check reads by the id its answer record
        refers to), though no other operation may refer to them before it is `done` (EV-2)."""
        operation = self.ops[op]
        output = operation.get("output") if isinstance(operation.get("output"), dict) else None
        if not output:
            return self.outputs
        saved = self.outputs
        self.outputs = dict((k, dict(v)) for k, v in saved.items())
        self._bind_fields(output["name"], output.get("fields") or {}, op)
        own, self.outputs = self.outputs, saved
        return own

    def _bind_fields(self, name, fields, op):
        bound = {}
        for field, mark in fields.items():
            try:
                if isinstance(mark, dict) and "held" in mark:
                    answer = (self.answers.get(op) or [{}])[-1]
                    if answer.get("held"):
                        bound[field] = values.Held(answer["held"])
                elif isinstance(mark, dict) and "observed" in mark:
                    observed = (self.completions.get(op) or {}).get("observed") or {}
                    if mark["observed"] in observed:
                        bound[field] = observed[mark["observed"]]
                else:
                    bound[field] = values.resolve(mark, self.outputs)
            except values.Unsettled:
                continue
        self.outputs.setdefault(name, {}).update(bound)

    # ---- needs (ORD-1) --------------------------------------------------------------------------
    def providers_of(self, output):
        found = [(o, self.finals.get(o)) for o in self.order
                 if isinstance(self.ops[o].get("output"), dict) and self.ops[o]["output"].get("name") == output]
        for item in self.manifest.get("already_so") or []:
            if item.get("output") == output:
                found.append((item.get("row"), "already so"))
        return found

    def need(self, need):
        """(`met` | `wait` | `stop` | `his` | `branch`, provider, provider's status)."""
        providers = self.providers_of(need["output"])
        cells = []
        for provider, status in providers:
            if status is None:
                continue
            value = (self.owner_answers.get(provider) or {}).get("answer") if status == "answered" else None
            found = cell(status, need, value)
            if found == "meets":
                return "met", provider, status
            cells.append((found, provider, status))
        if any(status is None for _p, status in providers) or not providers:
            return "wait", None, None
        for verdict in ("stop", "his", "branch"):
            for found, provider, status in cells:
                if found == verdict:
                    return verdict, provider, status
        return "branch", None, None

    def phase_open(self, op):
        phases = self.manifest.get("phases") or []
        mine = phases.index(self.ops[op]["phase"])
        return all(o in self.finals for o in self.order if phases.index(self.ops[o]["phase"]) < mine)

    def condition(self, op):
        """True: it can run. False: it is to be recorded `not needed`. None: not settled yet."""
        condition = self.ops[op].get("condition")
        if not isinstance(condition, dict) or condition.get("on") == "fact":
            return True
        other = condition.get("operation")
        if condition.get("on") == "alternative":
            if other not in self.finals and other not in [i.get("row") for i in self.manifest.get("already_so") or []]:
                return None
            return self.finals.get(other) == "refused" and (self.reasons.get(other) or {}).get("result") == condition.get("result")
        if condition.get("on") == "answer":
            if other not in self.finals:
                return None
            if self.finals[other] != "answered":
                return False
            return (self.owner_answers.get(other) or {}).get("answer") == condition.get("equals")
        return True

    def all_final(self):
        return all(o in self.finals for o in self.order)

    def exceptions(self):
        return [o for o in self.order if self.finals.get(o) in ("left", "held")]
