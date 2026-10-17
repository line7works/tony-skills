"""Forms (the frame's FORM-1, FORM-2, FORM-3; SEC-6; RUN-8, RUN-12).

A form is a file in the run directory, named in the CLI's output and shown by the adapter. Its text
comes from four sources only: the lane's fixed text for that form, the lines this frame fixes
(FORM-2, below), text the tool wrote from safe content, and the owner's own words. No function here
reads a file's text into a form: a form is rendered from the manifest and the journal, and what a
protected record holds is named by its label and its path, never shown.

FORM-2's table has no line for every status the frame's rules name. A line it lacks is the lane's
list of form changes to give (`form_changes` in the lane's file, carried in the manifest). A status
that occurs in a run and has a line in neither place fails the build of every form that lists
operations: `NoLine` is raised and no form is written. A waiting step that OP-9 does not let a form show
(`NOT_SHOWN`) is such a status: its line is the lane's list's, never FORM-2's `waiting` line (A120).
"""
import os

from . import protected

# FORM-2: the lines this frame fixes. Each holds the parts its row of the table names.
LINES = {
    "done": "done: {what}",
    "already so": "found already so; a restore will not reverse it: {what}",
    "not proven": "started by this run and not proven finished by it; a restore will ask before reversing it: {what}",
    "adopted": "taken as the project's on the owner's input: {what}; its identity: {identity}",
    "waiting": "waiting on you: {step}; mode: {mode}; the tool will know it is done {how}",
    "done by owner, read back": "done by you, and a read checked it: {what}",
    "done by owner, on his word": "done by you, on your word; no read checked it: {what}",
    "left": "left, by your word: {what}",
    "held": "not run: {what}; it needed {need}, and {provider} ended {status}",
    "refused": "the branch was not taken: {what}; the provider answered {result}",
    "not needed": "the other branch was taken, so this was not needed: {what}",
    "not applicable": "not applicable ({reason}): {what}{step}",
    "unavailable": "the check could not be made on this harness: {what}",
    "outstanding": ("a create was sent and no answer came: {what}; you can check: {check}; "
                    "the ways on: {ways}"),
    "stop": "stopped: {reason}{what}{operation}{command}{need}; the ways on: {ways}",
    "protected record": "{label}: {path}",
}
NOT_APPLICABLE_REASONS = ("a flag", "the project type", "a layer the project lacks", "not available on this harness",
                          "cannot be tied to its copy")
WAYS_ON = "resume, re-plan, close"
WAYS_ON_RETIREMENT = "resume, re-plan, close, restore over what is finished"
HOW = {"read back": "by its own read", "on his word": "by your word alone", "answer": "by your answer"}
# FORM-2 (batch 51, A120): "A waiting step that OP-9 does not let a form show has no exact step to give, so its line is not
# this table's `waiting` line, which names the exact step: it is a line the table lacks, for the lane's list of form changes
# to give (A9; OP-9)." The key under which the lane's list gives it; FORM-2's table holds no line of that key
NOT_SHOWN = "waiting, not shown"


class NoLine(Exception):
    """A status occurred that has a line neither in FORM-2's table nor in the lane's list."""

    def __init__(self, status):
        Exception.__init__(self, status)
        self.status = status


def line_for(key, changes, **parts):
    """The line for one status, with its parts. The lane's list of form changes may give a line
    FORM-2's table lacks; it never replaces one the table holds."""
    template = LINES.get(key)
    if template is None:
        template = (changes or {}).get(key)
    if not template:
        raise NoLine(key)
    filled = dict((k, "" if v is None else v) for k, v in parts.items())
    try:
        return template.format(**filled)
    except (KeyError, IndexError):
        raise NoLine(key)


def record_line(run_dir, reference):
    """A protected record, named and never shown: its label and the path of its file (SEC-6)."""
    return LINES["protected record"].format(label=reference["label"], path=protected.path_of(run_dir, reference["record"]))


def step_text(run_dir, step):
    """The text of an owner's step as the manifest holds it: a text the row wrote, a literal the look settled from safe
    content, or a protected record, which is named and never shown (SEC-1, SEC-6)."""
    if isinstance(step, dict) and "literal" in step:
        return str(step["literal"])
    if isinstance(step, dict) and isinstance(step.get("record"), dict):
        return record_line(run_dir, step["record"])
    if isinstance(step, dict) and isinstance(step.get("text"), list):
        parts = [step_text(run_dir, part) for part in step["text"]]
        return "".join(parts) if all(isinstance(p, str) for p in parts) else None
    return step if isinstance(step, str) else None


def what_of(operation, form):
    lines = operation.get("form_lines") if isinstance(operation.get("form_lines"), dict) else {}
    return lines.get(form) or lines.get("preview") or operation.get("id")


def preview_lines(manifest):
    """The preview, from the manifest and from nothing else (RUN-8)."""
    changes = manifest.get("form_changes") or {}
    kind = manifest.get("kind", "")
    out = ["%s PREVIEW" % kind.upper(), "run: %s" % manifest.get("run")]
    names = manifest.get("names") or []
    if names:
        out.append("names: %s" % ", ".join(names))
    description = (manifest.get("inputs") or {}).get("description")
    if description:
        out.append("in your words: %s" % description)
    for provider, account in sorted((manifest.get("accounts") or {}).items()):
        out.append("acts at %s as: %s" % (provider, account))
    carried = manifest.get("carried") or {}
    for phase in manifest.get("phases") or []:
        rows = [o for o in manifest.get("operations") or [] if o.get("phase") == phase]
        if not rows:
            continue
        out.append("phase %s:" % phase)
        for operation in rows:
            what = what_of(operation, "preview")
            if operation["id"] in carried:
                out.append("  [%s] finished earlier in this run (%s): %s" % (operation["id"], carried[operation["id"]], what))
                continue
            head = "  [%s] %s: %s" % (operation["id"], operation.get("kind"), what)
            if operation.get("kind") in ("owner step", "owner answer"):
                mode = operation.get("resolved_mode")
                head += "; yours to do; mode: %s" % mode
                if operation.get("kind") == "owner step" and operation.get("no_reverse"):
                    head += "; no reverse can be offered for this step"
            if operation.get("planned_unavailable"):
                head += "; " + line_for("unavailable", changes, what=what)
            if operation.get("resend"):
                head += "; an earlier send got no answer"
            if operation.get("not_proven"):
                head += "; " + line_for("not proven, on his word", changes, what=what)     # EV-5: on every form
            out.append(head)
            for name in operation.get("repo_commands") if isinstance(operation.get("repo_commands"), list) else []:
                out.append("      changes a repository: %s" % name)
    for item in manifest.get("already_so") or []:
        out.append(line_for("already so", changes, what=item.get("what")))
    for item in manifest.get("not_applicable") or []:
        step = "; you can do it yourself: %s" % item["step"] if item.get("step") else ""
        out.append(line_for("not applicable", changes, reason=item.get("reason"), what=item.get("what"), step=step))
    for item in manifest.get("not_offered") or []:
        # EV-5: everything a restore does not offer it lists, with the reason EV-4 recorded; FORM-2 has no line for it,
        # so the lane's list of form changes gives it (ROW-3)
        out.append(line_for("not offered", changes, reason=item.get("reason"), what=item.get("what")))
    for item in manifest.get("held_things") or []:
        out.append("%d %s found at %s; their names are in a private file: %s" % (item["count"], item["kind"], item["provider"],
                                                                                item["file"]))
    for item in manifest.get("settled_needs") or []:
        out.append("%s: %s (%s ended %s)" % (item["operation"], item["treatment"], item["need"], item["status"]))
    out.append("manifest: %d operations; nothing is done before your go." % len(manifest.get("operations") or []))
    return out


def status_lines(manifest, state, run_dir, ending, reason, position, retirement):
    """The status form, from the manifest and the journal (RUN-12). `state` is `engine.State`."""
    changes = manifest.get("form_changes") or {}
    ways = WAYS_ON_RETIREMENT if retirement else WAYS_ON
    out = ["%s STATUS" % manifest.get("kind", "").upper(), "run: %s" % manifest.get("run"),
           "the run now: %s" % ending, "position: %d" % position]
    if manifest.get("names"):
        out.append("names: %s" % ", ".join(manifest["names"]))
    if (manifest.get("inputs") or {}).get("description"):
        out.append("in your words: %s" % manifest["inputs"]["description"])
    for operation in manifest.get("operations") or []:
        op = operation["id"]
        what = what_of(operation, "status")
        status = state.finals.get(op)
        if status == "done":
            out.append("[%s] %s" % (op, line_for("done", changes, what=what)))
        elif status == "adopted":
            identity = state.adopted_identity.get(op) or "as you typed it"
            out.append("[%s] %s" % (op, line_for("adopted", changes, what=what, identity=identity)))
        elif status == "held":
            why = state.reasons.get(op) or {}
            out.append("[%s] %s" % (op, line_for("held", changes, what=what, need=why.get("need"), provider=why.get("provider"),
                                                 status=why.get("provider_status"))))
        elif status == "refused":
            out.append("[%s] %s" % (op, line_for("refused", changes, what=what, result=(state.reasons.get(op) or {}).get("result"))))
        elif status is not None:
            out.append("[%s] %s" % (op, line_for(status, changes, what=what)))
        elif op in state.outstanding:
            out.append("[%s] %s" % (op, line_for("outstanding", changes, what=what, check=operation.get("lost_answer_check", "the provider's own list"),
                                                 ways=ways)))
        elif op in state.waiting and operation.get("resolved_mode") == "read back" and op not in getattr(state, "read_now", ()):
            # OP-9 (batch 51, A120): "a waiting step whose read this invocation did not make, or made and got no answer from,
            # is in no form this invocation renders, neither from the manifest's text nor from an earlier form's". Its line is
            # the lane's (FORM-2, A120): none of the step's text is handed to it. Where this invocation's own read was not
            # made for a cause the tool names (`fresh`, the identity read of RUN-10 (b)), that cause is said beside it
            mode = operation.get("resolved_mode")
            line = "[%s] %s" % (op, line_for(NOT_SHOWN, changes, what=what, mode=mode, how=HOW.get(mode, "")))
            if getattr(state, "fresh", {}).get(op):
                line += "; %s" % state.fresh[op]
            out.append(line)
        elif op in state.waiting:
            mode = operation.get("resolved_mode")
            content = operation.get("safe_content") if isinstance(operation.get("safe_content"), dict) else {}
            step = state.steps_shown.get(op) or step_text(run_dir, content.get("step")) or content.get("question") or what_of(operation, "step")
            line = "[%s] %s" % (op, line_for("waiting", changes, step=step, mode=mode, how=HOW.get(mode, "")))
            if getattr(state, "fresh", {}).get(op):
                line += "; its read now shows: %s" % state.fresh[op]
            out.append(line)
        else:
            out.append("[%s] not started: %s" % (op, what))
        if operation.get("not_proven"):
            out[-1] += "; " + line_for("not proven, on his word", changes, what=what)        # EV-5: on every form
        for reference in state.records_of.get(op, []):
            out.append("      " + record_line(run_dir, reference))
    for item in manifest.get("already_so") or []:
        out.append(line_for("already so", changes, what=item.get("what")))
    for item in manifest.get("not_applicable") or []:
        step = "; you can do it yourself: %s" % item["step"] if item.get("step") else ""
        out.append(line_for("not applicable", changes, reason=item.get("reason"), what=item.get("what"), step=step))
    for due in state.receipts_due:
        out.append(line_for("a receipt due", changes, operation=due.get("op"), execution=due.get("execution"), field=due.get("field")))
    if state.disproofs:
        out.append(line_for("a safe ground disproved", changes, count=len(state.disproofs)))
    if ending == "stopped" and reason:
        if reason.get("kind") == "the entry is at its place and unconfirmed":
            ways = "resume, close"                  # KEEP-5
        operation = "; operation %s" % reason["op"] if reason.get("op") else ""
        command = "; the command you can run: %s" % reason["command"] if reason.get("command") else ""
        need = ""
        if reason.get("kind") == "need unmet":
            need = "; the need: %s; %s ended %s" % (reason.get("need"), reason.get("provider"), reason.get("provider_status"))
        what = " (%s)" % reason["what"] if reason.get("what") else ""
        out.append(line_for("stop", changes, reason=reason.get("kind"), what=what, operation=operation, command=command, need=need, ways=ways))
    if ending in ("waiting", "stopped"):
        out.append("to go on, give your word with position %d" % position)
    return out


def write(session, name, lines):
    """Write a form: every line passed through the register, the fixed words standing in the place
    of anything it withholds. Returns the form's path."""
    world = session.world
    rendered = [session.register.redact(line) for line in lines]
    text = "\n".join(rendered) + "\n"
    if session.register.holds(text):
        text = session.register.words() + "\n"
    folder = os.path.join(session.run_dir, "forms")
    existing = [n for n in world.fs.listdir(folder) if n.startswith(name + "-")]
    path = os.path.join(folder, "%s-%d.txt" % (name, len(existing) + 1))
    world.fs.write_new(path, text.encode("utf-8"))
    return path
