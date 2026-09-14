"""The recording transaction (pilot contract section 9; E8-14, E8-16, E8-28, E8-A11): the plan
with content and hashes computed in memory, write-ahead entries with integrity and log-before-
rename, atomic step application, the boundary check, the commit point, classification against
the virtual state, and replay.

The boundary check (section 9 as amended by E8-A11 and E8-A44) runs before every status-line
step's intent entry, or, when the plan holds no live status-line step, before the done entry of
its last step. The violations it finds are written to `run_dir/boundary.json` as
`{"before_step": k, "violations": [...]}` (k the step the check preceded), a run artifact of the
core's own: it joins the checkpoint's artifact ledger at its first write, so `records_written`
lists it in the E8-29 order after `receipt.log` and before the transaction's steps (it is
written during the transaction), and a re-assembly after the commit point reads it back so the
result keeps `not_clear`; status step k and every later status-line step are cancelled, a status
line receipted done before k stands. The file is written only when a violation was found; a
clean transaction leaves none.

Containment (E8-A19): every plan target must resolve inside the workspace's real path, checked
when the plan is made (`plan_containment`) and again inside `apply` immediately before the
atomic replacement.

Test hooks (honored only with RECHECK_TEST=1): RECHECK_TEST_FAIL_AFTER_STEP=<n> raises after
step n's target landed and before its done entry; RECHECK_TEST_FAIL_BEFORE_STEP=<n> raises
after step n's intent entry and before its target lands.
"""
import json
import os

from . import canon, checkpoint as cpmod, identity, ledger, validate

FILE = "receipt.json"
LOG = "receipt.log"
BOUNDARY = "boundary.json"


def boundary_path(run_dir):
    return os.path.join(run_dir, BOUNDARY)


def read_boundary_doc(run_dir):
    """{"before_step": k or None, "violations": [...]} from run_dir/boundary.json, or None when the
    file is absent (E8-A44). The pre-E8-A44 shape (a bare list) reads with before_step None."""
    path = boundary_path(run_dir)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        doc = json.loads(fh.read().decode("utf-8"))
    if isinstance(doc, list):
        return {"before_step": None, "violations": [str(v) for v in doc]}
    if isinstance(doc, dict):
        before = doc.get("before_step")
        return {"before_step": before if isinstance(before, int) and not isinstance(before, bool) else None,
                "violations": [str(v) for v in doc.get("violations") or []]}
    return {"before_step": None, "violations": []}


def read_boundary(run_dir):
    """The violations a boundary check recorded in this run directory, or [] when none."""
    doc = read_boundary_doc(run_dir)
    return doc["violations"] if doc else []


def write_boundary(run_dir, violations, before_step):
    """E8-A44: the violations with the step they were found before."""
    doc = {"before_step": before_step, "violations": list(violations)}
    canon.atomic_write(boundary_path(run_dir), (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return boundary_path(run_dir)


class ReceiptError(RuntimeError):
    pass


class ContainmentError(ReceiptError):
    """E8-A19: a plan target resolves outside the workspace's real path."""


def contained(workspace, target):
    """E8-A19: the real path of workspace/target lies under the real path of the workspace."""
    root = os.path.realpath(workspace)
    real = os.path.realpath(os.path.join(workspace, target))
    return real == root or real.startswith(root.rstrip(os.sep) + os.sep)


def containment_reason(step, target):
    return "step %d target %s resolves outside the workspace; no write" % (step, target)


def plan_containment(workspace, plan):
    """The stop reason of the first plan step whose target resolves outside the workspace, or None."""
    for s in plan:
        if not contained(workspace, s["target"]):
            return containment_reason(s["step"], s["target"])
    return None


class TestHookFailure(RuntimeError):
    """Raised by the test hooks to simulate a failure between steps."""


def _hook(name, step):
    if os.environ.get("RECHECK_TEST") != "1":
        return
    value = os.environ.get(name)
    if value and value.isdigit() and int(value) == step:
        raise TestHookFailure("%s=%s (test hook)" % (name, value))


def file_text(path):
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def sha(text):
    return canon.sha256_hex(text.encode("utf-8"))


# ---- the plan (section 9) ------------------------------------------------------------------

def plan_transaction(workspace, document, run_date, checklist, item_results, new_defects, waivers, reopenings, cards_before):
    """Compute every step in order with content, before and after hashes, over in-memory states.

    checklist: the checkpoint's scope.checklist; item_results: the done results in index order;
    waivers / reopenings: the accepted grants ({"grant": g, "slice": s}); cards_before:
    {slice: card}. Returns (plan, states, cards_after) where states maps target -> final text.
    """
    states = {}

    def text_of(target):
        if target not in states:
            states[target] = file_text(os.path.join(workspace, target))
        return states[target]

    plan = []

    def add(kind, target, content=None, value=None, heading=None, slice_name=None):
        before = text_of(target)
        step = {"step": len(plan) + 1, "kind": kind, "target": target, "before_sha256": sha(before)}
        if kind == "status_line":
            step["value"] = value
            step["slice"] = slice_name
        else:
            step["content"] = content
            if heading:
                step["heading"] = heading
        after = ledger.apply_step(before, step)
        step["after_sha256"] = sha(after)
        states[target] = after
        plan.append(step)

    for g in sorted(reopenings, key=lambda x: (x["grant"]["date"], x["index"])):
        it = g["grant"]["item"]
        add("reopened_line", document, ledger.render_reopen(g["grant"]["date"], it["location"]["file"], it["location"]["line"], it["claim"], g["grant"]["quoted_words"]))
    slices = ledger.sort_slices(it["slice"] for it in checklist)
    lines = []
    for it, res in zip(checklist, item_results):
        disp = "fixed" if res["disposition"] == "fixed" else "not fixed"
        lines.append(ledger.render_recheck_line(it["severity"], it["location"]["file"], it["location"]["line"], it["claim"], disp, ledger.render_how(res["verification"])))
    for d in new_defects:
        lines.append(ledger.render_defect_line(d["severity"], d["location"]["file"], d["location"]["line"], d["claim"], d["failure_scenario"],
                                               ledger.defect_slice_field(slices, d["charged_to_slice"])))
    heading = ledger.render_heading(run_date, slices)
    block = ledger.render_block(run_date, slices, lines)
    add("punch_list_block", document, block, heading=heading)
    for g in sorted(waivers, key=lambda x: (x["grant"]["date"], x["index"])):
        it = g["grant"]["item"]
        add("waived_line", document, ledger.render_waiver(g["grant"]["date"], g["grant"]["severity"], it["location"]["file"], it["location"]["line"], it["claim"], g["grant"]["quoted_words"]))
    verdict_docs = {}
    for s in slices:
        if s == "none":
            continue
        matches = ledger.verdict_doc_glob(workspace, document, s)
        verdict_docs[s] = matches
        if len(matches) == 1:
            add("verdict_doc_copy", matches[0], block, heading=heading)
    cards_after = {}
    parsed_after = ledger.parse_document(states[document], document)
    opened = ledger.open_set(parsed_after)
    for s in slices:
        if s == "none":
            continue
        before = cards_before.get(s, "none")
        open_here = [e for e in opened["entries"] if e["slice"] == s and e["state"] == "open"]
        after = ledger.card_after(before, open_here)
        cards_after[s] = after
        if after != before:
            add("status_line", document, value=after, slice_name=s)
    return plan, states, cards_after, verdict_docs


# ---- the receipt file --------------------------------------------------------------------

class Receipt:
    def __init__(self, run_dir, doc, schemas):
        self.run_dir, self.doc, self.schemas = run_dir, doc, schemas

    @property
    def path(self):
        return os.path.join(self.run_dir, FILE)

    @property
    def log_path(self):
        return os.path.join(self.run_dir, LOG)

    @classmethod
    def new(cls, run_dir, run_id, plan, schemas):
        stored = []
        for s in plan:
            step = {k: v for k, v in s.items() if k in ("step", "kind", "target", "before_sha256", "after_sha256", "content", "value", "heading", "cancelled")}
            stored.append(step)
        doc = {"run_id": run_id, "phase": "recording", "plan": stored, "entries": [], "integrity": {"seq": 0, "prev": None, "self": "0" * 64}}
        rc = cls(run_dir, doc, schemas)
        rc._write(0, None)
        return rc

    def save(self):
        integ = self.doc["integrity"]
        self._write(integ["seq"] + 1, integ["self"])

    def _write(self, seq, prev):
        self.doc["integrity"] = {"seq": seq, "prev": prev, "self": "0" * 64}
        self.doc["integrity"]["self"] = cpmod.self_hash(self.doc)
        errors = validate.validate_receipt(self.doc, self.schemas)
        if errors:
            raise ReceiptError("receipt would not validate: %s %s" % (errors[0]["path"], errors[0]["message"]))
        canon.log_then_rename(self.log_path, "%d %s" % (seq, self.doc["integrity"]["self"]), self.path, cpmod.serialize(self.doc))

    def entry(self, step, kind, observed=None):
        e = {"step": step, "type": kind}
        if kind == "done":
            e["observed_sha256"] = observed
        self.doc["entries"].append(e)
        self.save()

    def has(self, step, kind):
        return any(e["step"] == step and e["type"] == kind for e in self.doc["entries"])

    def done_steps(self):
        return sorted(set(e["step"] for e in self.doc["entries"] if e["type"] == "done"))


def read_and_verify(run_dir, schemas):
    """Step 5 of section 11: existence, parse, schema, integrity against receipt.log."""
    path, log = os.path.join(run_dir, FILE), os.path.join(run_dir, LOG)
    if not os.path.isfile(path):
        return {"exists": False, "ok": True, "reason": "", "doc": None}
    if not os.path.isfile(log):
        return {"exists": True, "ok": False, "reason": "receipt.log does not exist", "doc": None}
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
        rows = cpmod.read_log(log)
    except (OSError, ValueError, cpmod.CheckpointError) as exc:
        return {"exists": True, "ok": False, "reason": "receipt does not parse: %s" % exc, "doc": None}
    errors = validate.validate_receipt(doc, schemas)
    if errors:
        return {"exists": True, "ok": False, "reason": "receipt fails its schema at %s: %s" % (errors[0]["path"], errors[0]["message"]), "doc": doc}
    v = cpmod.verify_integrity(doc, rows, "receipt")
    if not v["ok"]:
        return {"exists": True, "ok": False, "reason": v["reason"], "doc": doc}
    corrupt = check_entries(doc.get("plan") or [], doc.get("entries") or [])
    if corrupt:
        return {"exists": True, "ok": False, "reason": "the receipt is corrupt: " + corrupt, "doc": doc}
    return {"exists": True, "ok": True, "reason": v["reason"], "doc": doc, "tolerated": v["tolerated"]}


def check_entries(plan, entries):
    """E8-A21: the receipt proves the state. Entries in sequence order (a step number never falls),
    each intent before its done, at most one intent and one done per step, every done entry's
    observed hash equal to the step's planned after-hash, every entry naming a plan step. Returns
    the reason naming the offending entry, or None."""
    steps = {s["step"]: s for s in plan}
    last_step = 0
    intents, dones = set(), set()
    for n, e in enumerate(entries):
        step, kind = e.get("step"), e.get("type")
        label = "entry %d (%s, step %s)" % (n, kind, step)
        if step not in steps:
            return "%s names no plan step" % label
        if step < last_step:
            return "%s is out of sequence after step %d" % (label, last_step)
        if kind == "intent":
            if step in intents:
                return "%s repeats the step's intent" % label
            if step in dones:
                return "%s follows the step's done entry" % label
            intents.add(step)
        elif kind == "done":
            if step not in intents:
                return "%s precedes the step's intent" % label
            if step in dones:
                return "%s repeats the step's done entry (one done per step)" % label
            if e.get("observed_sha256") != steps[step]["after_sha256"]:
                return "%s observed %s, not the step's planned after-hash %s" % (label, (e.get("observed_sha256") or "")[:12], steps[step]["after_sha256"][:12])
            dones.add(step)
        else:
            return "%s has an unknown type" % label
        last_step = step
    return None


def last_plan_step(plan):
    live = [s for s in plan if not s.get("cancelled")]
    return live[-1]["step"] if live else None


# ---- classification (E8-14) ----------------------------------------------------------------

def classify(plan, entries, workspace):
    """Walk the plan keeping a virtual hash per target. Returns [{"step", "class"}] with class
    done | redo | outside | cancelled, and the virtual before-hash the redo must start from."""
    done = set(e["step"] for e in entries if e["type"] == "done")
    virtual, pending_redo = {}, set()
    out, before_of, per_target = [], [], {}
    for s in plan:
        target = s["target"]
        if target not in virtual:
            virtual[target] = s["before_sha256"]
        before_of.append(virtual[target])
        per_target.setdefault(target, []).append(len(out))
        if s.get("cancelled"):
            out.append({"step": s["step"], "class": "cancelled"})
            continue
        if s["step"] in done:
            virtual[target] = s["after_sha256"]
            out.append({"step": s["step"], "class": "done"})
            continue
        current = sha(file_text(os.path.join(workspace, target)))
        if current == s["after_sha256"]:
            out.append({"step": s["step"], "class": "done", "landed": True})
            virtual[target] = s["after_sha256"]
        elif current == virtual[target] or target in pending_redo:
            # the walk redoes a step before advancing (section 9), so a later step on a target with a
            # pending redo starts from that redo's after hash, which the file at rest cannot show yet
            out.append({"step": s["step"], "class": "redo"})
            pending_redo.add(target)
            virtual[target] = s["after_sha256"]
        else:
            out.append({"step": s["step"], "class": "outside", "current": current, "expected_before": virtual[target], "expected_after": s["after_sha256"]})
            virtual[target] = s["after_sha256"]
    # E8-A21: a target whose steps are all done must rest at its final virtual hash; otherwise its
    # last step is an outside edit
    for target, idxs in per_target.items():
        if not all(out[i]["class"] == "done" for i in idxs):
            continue
        current = sha(file_text(os.path.join(workspace, target)))
        if current != virtual[target]:
            last = idxs[-1]
            out[last] = {"step": plan[last]["step"], "class": "outside", "current": current, "expected_before": before_of[last],
                         "expected_after": plan[last]["after_sha256"], "resting": True}
    return out


def regenerate(step, regen):
    """Content or value for a plan step without one (a seeded receipt); regen(step) supplies it."""
    if step["kind"] == "status_line":
        if "value" not in step:
            step["value"] = regen(step)
        return step
    if "content" not in step:
        step["content"] = regen(step)
    return step


# ---- applying steps ------------------------------------------------------------------------

def apply(workspace, step):
    # E8-A19: the containment test again, immediately before the replacement
    if not contained(workspace, step["target"]):
        raise ContainmentError(containment_reason(step["step"], step["target"]))
    target = os.path.join(workspace, step["target"])
    before = file_text(target)
    if sha(before) != step["before_sha256"]:
        raise ReceiptError("step %d: %s is not at its before hash" % (step["step"], step["target"]))
    after = ledger.apply_step(before, step)
    if sha(after) != step["after_sha256"]:
        raise ReceiptError("step %d: regenerated content for %s does not reach the planned after hash" % (step["step"], step["target"]))
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    canon.atomic_write(target, after.encode("utf-8"))
    return step["after_sha256"]


def boundary_violations(workspace, pre, plan, virtual, pre_nontarget_diff, pre_nontarget_sha256=None):
    """Section 9's check before every status line (or before the last step's done entry when
    the plan has no status line, E8-A11, E8-A44). pre: the pre-transaction identity;
    virtual: {target: expected sha256 now}; pre_nontarget_diff: the pre-transaction
    `git diff HEAD --binary` with the plan targets excluded, or None when unknown; then
    pre_nontarget_sha256, the transaction guard's digest of that diff (E8-A45), is compared when
    given, else only a clean start's expectation of no other change is checked."""
    now = identity.identity_of(workspace)
    out = []
    if now["commit"] != pre["commit"]:
        out.append("HEAD moved from %s to %s during the transaction (a git state change)" % (pre["commit"], now["commit"]))
    if now["untracked"] != pre["untracked"] or now["untracked_sha256"] != pre["untracked_sha256"]:
        added = sorted(set(now["untracked"]) - set(pre["untracked"]))
        out.append("untracked content changed during the transaction%s" % (": " + ", ".join(added) if added else " (content of an untracked file)"))
    targets = sorted(set(s["target"] for s in plan))
    for t in targets:
        current = sha(file_text(os.path.join(workspace, t)))
        if current != virtual.get(t):
            out.append("%s is at %s, not the receipted state %s" % (t, current[:12], (virtual.get(t) or "")[:12]))
    changed = [p for p in identity.changed_tracked_paths(workspace) if p not in targets]
    diff_now = identity.tracked_diff_excluding(workspace, targets)
    if pre_nontarget_diff is not None or pre_nontarget_sha256 is not None:
        same = diff_now == pre_nontarget_diff if pre_nontarget_diff is not None else canon.sha256_hex(diff_now) == pre_nontarget_sha256
        if not same:
            out.append("tracked files outside the plan changed during the transaction: %s" % (", ".join(changed) or "(diff differs)"))
    elif not pre["dirty"]:
        if changed:
            out.append("tracked files outside the plan changed since the clean start: %s" % ", ".join(changed))
    return out, now
