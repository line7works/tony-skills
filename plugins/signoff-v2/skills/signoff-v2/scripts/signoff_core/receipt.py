"""The write-ahead receipt: what this run meant to do, and what actually happened.

One file, `receipt.json`, rewritten at every step and announced in `receipt.log` before each
rewrite, so an interrupted rewrite leaves the one tolerated state rather than a file whose
provenance nothing recorded.

Two kinds of entry, and the difference between them is the whole of Revision 7:

- **An append block** (`appends.findings`, `appends.card`) carries the log and the head read at
  plan time BEFORE the call, and one of three outcomes after it:
  `landed` with the resulting head and the seqs; `refused` with the component's exit code, its
  error and its own sentence; or `unknown`, which is the crash window itself — an intent with no
  outcome. A `refused` is DEFINITIVE and no later pass retries it. An `unknown` is settled
  against the head this block already names, never against a head read afresh.
- **A document step** carries its target, the exact bytes it appends or the value it sets, the
  target's hash before, and the hash the step plans to leave. A later pass compares the target's
  current hash with those two: equal to the planned hash means the step landed, equal to the
  hash before means it must be redone, and anything else is an outside edit that stops the run.

The transaction guard stores each target's hash beside the source identity before the first
append, so an edit that reaches a target before a document plan exists can never become that
plan's `before` state (Revision 7, the reviewer's second MAJOR).
"""
import os

from . import canon

UNKNOWN = "unknown"
LANDED = "landed"
REFUSED = "refused"
PENDING = "pending"
DONE = "done"


class Receipt:
    """The run's receipt, on disk at `<run_dir>/receipt.json`."""

    def __init__(self, run_dir):
        self.run_dir = run_dir
        self.path = os.path.join(run_dir, "receipt.json")
        self.doc = None

    # ---- lifecycle -----------------------------------------------------------------------

    def exists(self):
        return os.path.isfile(self.path)

    def load(self):
        self.doc = canon.read_json(self.path)
        return self.doc

    def create(self, run_id, workspace, ledger_doc, slice_name, guard):
        self.doc = {
            "receipt_version": 1,
            "run_id": run_id,
            "workspace": workspace,
            "ledger_doc": ledger_doc,
            "slice": slice_name,
            "guard": guard,
            "appends": {},
            "steps": [],
            "committed": False,
        }
        self._save("created the receipt for run %s" % run_id)
        return self.doc

    def _save(self, line):
        canon.log_then_rename(self.path, self.doc, line)

    # ---- appends -------------------------------------------------------------------------

    def append_intent(self, name, log, expected_head, events):
        """Record what this append is about to do, BEFORE the component is called."""
        self.doc["appends"][name] = {
            "name": name,
            "log": log,
            "expected_head": expected_head,
            "event_kinds": [event["kind"] for event in events],
            "events": len(events),
            "outcome": UNKNOWN,
            "head": None,
            "seqs": [],
            "refused": None,
            "recovered": False,
        }
        self._save("append %s: intent, log %s at head %s, %d event(s)"
                   % (name, log, expected_head, len(events)))
        return self.doc["appends"][name]

    def append_landed(self, name, head, seqs, recovered=False):
        block = self.doc["appends"][name]
        block["outcome"] = LANDED
        block["head"] = head
        block["seqs"] = list(seqs)
        block["recovered"] = bool(recovered)
        self._save("append %s: landed at head %s, seqs %s%s"
                   % (name, head, seqs, " (recovered)" if recovered else ""))
        return block

    def append_refused(self, name, exit_code, error, reason):
        """A refusal the component RETURNED. Persisted before the named stop; never retried."""
        block = self.doc["appends"][name]
        block["outcome"] = REFUSED
        block["refused"] = {"exit_code": exit_code, "error": error, "reason": reason}
        self._save("append %s: refused by the component (exit %s, %s): %s"
                   % (name, exit_code, error, reason))
        return block

    def append_block(self, name):
        return self.doc["appends"].get(name)

    # ---- document steps ------------------------------------------------------------------

    def plan_steps(self, steps):
        """Fix the document plan. It never changes afterwards."""
        self.doc["steps"] = [dict(step, state=PENDING, observed=None) for step in steps]
        self._save("planned %d document step(s): %s"
                   % (len(steps), ", ".join(step["kind"] for step in steps)))
        return self.doc["steps"]

    def step_intent(self, index):
        step = self.doc["steps"][index]
        step["state"] = "intent"
        self._save("step %d (%s -> %s): intent" % (index, step["kind"], step["target"]))
        return step

    def step_done(self, index, observed):
        step = self.doc["steps"][index]
        step["state"] = DONE
        step["observed"] = observed
        self._save("step %d (%s -> %s): done, target at %s"
                   % (index, step["kind"], step["target"], observed))
        return step

    def commit(self):
        self.doc["committed"] = True
        self._save("the recording transaction is complete")

    def steps(self):
        return self.doc.get("steps", [])


def guard_of(identity_fingerprint, targets, workspace, masked=None):
    """The transaction guard: the source identity, and each target's hash, pinned together.

    Without the target hashes an edit that reaches a target before the document plan exists is
    invisible to every check, because the guard's tracked diff EXCLUDES the targets — that is
    what lets the transaction write them (Revision 7).

    `masked` is the identity with the targets left out, taken when the receipt is created, right
    after the reviewed identity was confirmed (Astra's F3). A recovering pass compares it with the
    same computation made then: the targets are the only paths this run may have changed, so a
    difference anywhere else is source that moved under a recording the review never saw."""
    guard = {
        "identity": dict(identity_fingerprint),
        "targets": {rel: canon.sha256_file_or_none(os.path.join(workspace, rel))
                    for rel in sorted(targets)},
    }
    if masked is not None:
        guard["masked"] = dict(masked)
    return guard


def guard_breaks(guard, workspace, identity_now):
    """[] when the guard still holds, else one reason per thing that moved."""
    reasons = []
    for field in sorted(guard["identity"]):
        if guard["identity"][field] != identity_now.get(field):
            reasons.append("the source identity's %s changed since the transaction began" % field)
    for rel, was in sorted(guard["targets"].items()):
        now = canon.sha256_file_or_none(os.path.join(workspace, rel))
        if was != now:
            reasons.append("%s changed outside this run since the transaction began" % rel)
    return reasons
