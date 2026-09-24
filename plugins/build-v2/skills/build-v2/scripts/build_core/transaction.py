"""The one transaction a build run makes: the card move, recorded then written.

Two halves, in this order and no other:

    1. the `card_set` event, through `records.py append` with `--expect-head <the head read at
       plan time>`, carrying the RUN's id as `actor.run_id` and the six-field identity
    2. the slice's `Status:` line in the build doc, set to match

Both halves are planned before either runs, and the plan is written to `receipt.json` first:

    card_append   {log, expected_head, expected_seq, event}    the INTENT, before the call
                  {..., head, seqs}                            the OUTCOME, after it
                  {..., refused: {exit_code, error, reason}}   a refusal the component RETURNED
    document_step {target, line, value, sha256_before, sha256_planned}   pinned BEFORE the append
                  {..., done: true, sha256_after}                        after the write

Four rules this shape exists to keep, each one a failure the outside reviewer found in the
pilot before its fix round (astra-short-look.md, findings 1 to 4):

- **An intent with no outcome IS the crash window.** It is settled against the head the receipt
  already names, never against a head read afresh: a head that moved since is a conflict the
  component refuses, not permission to append against the new one.
- **A refusal the component RETURNED is definitive.** It is persisted before the stop is
  returned, and no later pass retries it.
- **A failed history read is not an empty history.** It keeps its exit and its explanation,
  becomes the matching stop, and returns before any append; only a card a SUCCESSFUL read proved
  absent is ever appended.
- **The document target's bytes are pinned before the append.** Without that, an edit that
  reaches the document between the plan and the write becomes the plan's `before` state and is
  accepted. The baseline is never regenerated from edited bytes.

Completing the document step does not complete the transaction on its own: every pass, a first
`report` and a later settling one alike, reconciles the card event with the log through the CLI
before it reports anything.
"""
import os

from . import canon, doc as docmod, records_link as link, statefile, view
from .records_client import RecordsRefusal


class OutsideEdit(RuntimeError):
    """The document is at neither the hash the plan recorded nor the hash it planned."""


def open_receipt(run_dir, run_id, document, slice_name):
    """The receipt of this run, created or reopened. A corrupt one is a stop, never a fresh one."""
    path, log_path = statefile.receipt_paths(run_dir)
    if os.path.isfile(path):
        return statefile.StateFile.open(path, log_path), False
    return statefile.StateFile.create(path, log_path, {
        "receipt_version": 1, "run_id": run_id, "document": document, "slice": slice_name,
    }), True


def plan(receipt, client, workspace, document, entry, slice_name, before, after,
         run_id, session_id, harness, at, identity):
    """Write the whole plan — both halves — before either runs. Returns the planned event.

    `run_id` goes on the event as `actor.run_id`; `session_id`, the executor's, goes in the
    receipt beside it, so the log says which RUN moved the card and the receipt says which
    session's answer it recorded.
    """
    walked = view.head_of(client, workspace, document)
    text = docmod.read(workspace, document)
    planned_text = docmod.set_status(text, entry, after)
    event = link.card_event(document, slice_name, before, after, run_id, harness, at, identity)
    receipt.doc["card_append"] = {
        "log": walked["log"],
        "expected_head": walked["head"],
        "expected_seq": walked.get("events"),
        "event": {"slice": slice_name, "before": before, "after": after,
                  "run_id": run_id, "session_id": session_id},
    }
    receipt.doc["document_step"] = {
        "target": document,
        "line": entry["status_line"],
        "value": after,
        "sha256_before": canon.sha256_text(text),
        "sha256_planned": canon.sha256_text(planned_text),
        "done": False,
        "sha256_after": None,
    }
    receipt.save()
    return event


def persist_refusal(receipt, refusal):
    """A refusal the component gave, recorded as non-resumable BEFORE the stop is returned."""
    block = dict(receipt.doc.get("card_append") or {})
    if not block.get("log"):
        return
    block["refused"] = {"exit_code": refusal.exit_code, "error": refusal.error,
                        "reason": refusal.sentence()}
    receipt.doc["card_append"] = block
    receipt.save()


def refused_stop(block, document):
    """The named stop a persisted refusal produces on this pass and on every later one."""
    refused = block.get("refused") or {}
    return view.RecordsStop(
        link.refusal_tag(refused.get("exit_code")),
        "the card event of this run was refused by the records component (exit %s, %s): %s. A "
        "refusal the component gave is definitive and is never retried: nothing was appended to "
        "the log of %s, nothing will be, and the slice's `Status:` line was not written. Re-read "
        "the log and decide."
        % (refused.get("exit_code"), refused.get("error") or "-", refused.get("reason") or "",
           document))


def append_card(receipt, client, workspace, document, event, expect_head, run_dir):
    """The append. A refusal is persisted and becomes the named stop; nothing reaches the document."""
    try:
        result = client.append(workspace, document, [event], expect_head, run_dir)
    except RecordsRefusal as refusal:
        persist_refusal(receipt, refusal)
        raise view.stop_for(refusal, "the card event of this run was not appended, so the slice's "
                                     "`Status:` line was not written either")
    block = dict(receipt.doc["card_append"])
    block["head"] = result["head"]
    block["seqs"] = [row["seq"] for row in result.get("appended") or []]
    receipt.doc["card_append"] = block
    receipt.save()
    return result


def landed_event(rows, block):
    """This run's own card event in the log, or None. Matched at the seq the plan named.

    Two things must both hold: the event sits at the seq the plan named — the log's event count
    as it stood when the head was read, and nowhere else — and it carries this RUN's id. The seq
    alone would be enough now that `actor.run_id` is unique per run, and the actor alone would be
    enough too; keeping both is belt and braces around the one write this core makes.
    """
    want = block.get("expected_seq")
    intent = block.get("event") or {}
    for row in rows:
        if row.get("seq") != want:
            continue
        event = row["event"]
        if event.get("kind") != "card_set":
            return None
        actor = event.get("actor") or {}
        if (event.get("slice") == intent.get("slice")
                and event.get("after") == intent.get("after")
                and event.get("before") == intent.get("before")
                and actor.get("run_id") == intent.get("run_id")
                and actor.get("station") == link.STATION):
            return row
    return None


def settle_append(receipt, client, workspace, document, event, run_dir):
    """Settle the append half. Returns (result or None, the half that was missing or None).

    Three states, and only three:
      - the receipt carries a head: the append landed and was recorded. Nothing to do.
      - the receipt carries a refusal: definitive, re-raised, never retried.
      - the receipt carries an intent and no outcome: the crash window. The log decides.
    """
    block = dict(receipt.doc.get("card_append") or {})
    if not block:
        return None, None
    if block.get("refused"):
        raise refused_stop(block, document)
    if block.get("head"):
        return None, None

    rows = view.card_events(client, workspace, document)   # a failed read is a stop
    landed = landed_event(rows, block)
    if landed is not None:
        walked = view.head_of(client, workspace, document)
        block["head"] = walked["head"]
        block["seqs"] = [landed["seq"]]
        block["recovered"] = True
        receipt.doc["card_append"] = block
        receipt.save()
        return {"appended": [{"seq": landed["seq"], "kind": "card_set"}], "head": walked["head"],
                "log": block["log"]}, "the card event's record in the receipt"

    walked = view.head_of(client, workspace, document)
    if walked["head"] != block["expected_head"]:
        raise view.RecordsStop(
            "records_conflict",
            "the card event of this run has no outcome in the receipt and is not in the log, and "
            "the log of %s is now at head %s rather than the %s this run expected. Another writer "
            "appended between the two. A head that moved is a conflict the component refuses, not "
            "permission to append against the new one: nothing was appended and the `Status:` line "
            "was not written. Re-read the log and decide."
            % (document, walked["head"][:12], block["expected_head"][:12]))
    result = append_card(receipt, client, workspace, document, event, block["expected_head"], run_dir)
    return result, "the card event"


def _status_on_disk(workspace, target, slice_name):
    """The slice's `Status:` value in the build doc as it is on disk, or None when it cannot be
    read (read only; the words of a stop, never a decision)."""
    try:
        with open(os.path.join(workspace, target), "r", encoding="utf-8") as fh:
            return docmod.find_slice(fh.read(), slice_name).get("status")
    except (OSError, UnicodeDecodeError, docmod.DocumentError):
        return None


def _line_is_ours(workspace, step, slice_name):
    """Whether the slice's line on disk holds the value this run's document step writes, and that
    value is this run's to have put there: the receipt records the write, or the plan changed the
    line (its planned bytes differ from the bytes it read)."""
    current = _status_on_disk(workspace, step["target"], slice_name)
    return current is not None and current == step.get("value") and (
        bool(step.get("done")) or step.get("sha256_before") != step.get("sha256_planned"))


def _edit_window(workspace, step, slice_name):
    """When the edit an `outside_edit` stop names reached the document, as far as it is known.

    punch4-C2-3: the receipt decides first. A receipted write is this run's write whatever the
    line reads now, so any edit the stop names came after it; only without a receipted write does
    the line's current value decide."""
    if step.get("done"):
        return "after this run's own `Status:` line reached it"
    if _line_is_ours(workspace, step, slice_name):
        return "after this run planned the card move"
    return "between the plan and the write"


def _line_words(workspace, step, slice_name):
    """What the `outside_edit` reason says about the `Status:` line, read from the document on
    disk (punch3-C2-3, NEW-1's words): when the line already holds the value this run writes, it
    says so, whether the receipt records this run's write, and that the line is left as it is.

    punch4-C2-3: when the receipt records this run's write and the line reads something else now
    (put back by hand, changed to a third value, the document re-saved), the words say what the
    line reads now, that this run wrote its value there earlier, and that it is left as it is.
    Without a receipted write the run cannot know the line was ever its, and the words say the
    line was not written, as before."""
    if step.get("done") and not _line_is_ours(workspace, step, slice_name):
        current = _status_on_disk(workspace, step["target"], slice_name)
        now = ("reads `%s` in %s now" % (current, step["target"]) if current is not None else
               "can no longer be read in %s" % step["target"])
        return ("the slice's `Status:` line %s, although this run's own document step wrote `%s` "
                "there earlier (its receipt records that write); someone changed the line after "
                "that write, and it is left as it is, neither written again nor reverted."
                % (now, step.get("value")))
    if _line_is_ours(workspace, step, slice_name):
        return ("the slice's `Status:` line already reads `%s` in %s, %s, and it is left as it is, "
                "neither written again nor reverted."
                % (step.get("value"), step["target"],
                   "written by this run's own document step before the run was interrupted (its "
                   "receipt records that write)" if step.get("done") else
                   "the value this run's document step writes (the run was interrupted before its "
                   "receipt recorded a write, so the line is this run's write or an edit that set "
                   "the same value)"))
    return "the `Status:` line was not written."


def write_document_step(receipt, workspace):
    """The second half. Returns (wrote, the step) or raises OutsideEdit.

    The guard: the document must be at the hash the plan recorded (write it) or at the hash the
    plan computed (it already landed; record that and write nothing). Any other hash is an edit
    that reached the target after the plan was made, and this core stops rather than taking the
    edited bytes as its baseline.
    """
    step = dict(receipt.doc.get("document_step") or {})
    if not step:
        return False, None
    path = os.path.join(workspace, step["target"])
    current = canon.sha256_file_or_none(path)
    if current is None:
        raise OutsideEdit("the build doc %s is no longer in the workspace, so the slice's "
                          "`Status:` line cannot be written" % step["target"])
    if current == step.get("sha256_planned"):
        if not step.get("done"):
            step["done"] = True
            step["sha256_after"] = current
            receipt.doc["document_step"] = step
            receipt.save()
        return False, step
    if current == step.get("sha256_before") and step.get("done"):
        # punch3-C2-2: this run already wrote the line (the receipt says so) and the document is
        # back at the bytes the plan read: a hand edit BACK to the value the move started from,
        # which the contract leaves to a person. The line is never written a second time.
        raise OutsideEdit(
            "the build doc %s is back at the bytes this run read when it planned the card move "
            "(%s): its `Status:` line reads `%s` again, although this run's own document step "
            "wrote `%s` there and its receipt records that write (%s). Someone put the line back "
            "after the write. This run will not write it a second time and leaves the document as "
            "it is; its card event is in the log and is reported as landed, so the document now "
            "contradicts the last recorded move and a person decides. Read the document and the "
            "log." % (step["target"], (step.get("sha256_before") or "")[:12],
                      _status_on_disk(workspace, step["target"], receipt.doc.get("slice")) or "-",
                      step.get("value"), (step.get("sha256_after") or "")[:12]))
    if current != step.get("sha256_before"):
        raise OutsideEdit(
            "the build doc %s is at neither the bytes this run read when it planned the card move "
            "(%s) nor the bytes that plan produces (%s); it now hashes to %s. Something edited it "
            "%s, so this run will not take the edited bytes as its baseline: %s Read the document "
            "and run again."
            % (step["target"], (step.get("sha256_before") or "")[:12],
               (step.get("sha256_planned") or "")[:12], current[:12],
               _edit_window(workspace, step, receipt.doc.get("slice")),
               _line_words(workspace, step, receipt.doc.get("slice"))))

    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    entry = docmod.find_slice(text, receipt.doc["slice"])
    canon.atomic_write(path, docmod.set_status(text, entry, step["value"]).encode("utf-8"))
    step["done"] = True
    step["sha256_after"] = canon.sha256_file(path)
    receipt.doc["document_step"] = step
    receipt.save()
    return True, step
