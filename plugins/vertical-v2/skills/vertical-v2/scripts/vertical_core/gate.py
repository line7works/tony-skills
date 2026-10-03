"""`gate`: the doc hunt, the cards and the `Status:` lines, the preconditions, the base and the boundary
(contract section 3.1; readings CR-1 and CR-2 of the slice 1a brief; v1's Step 1 and Step 3's base).

The gate passes only when every slice stands `signed off`. Each slice's card comes from the records
component's `state` (`card_observed`, the last card set or observed in the log), compared with the build
doc's `Status:` line; a disagreement is a stop naming both. The component's derived card
(`card_derived`) is recorded beside it and never stops the gate (the owner's ruling, E15 lane contract
A3, C1A-2): a slice whose derived card differs is named, with both cards, in the verdict's Method line.
A slice the log names nothing about falls back to its `Status:` line, and the result says so. The slices
and their `Status:` lines are read with vertical-v2's own reading rule (the E15 lane contract A7 and A8,
`fences.py`: strict plain code blocks, no raw HTML lines, A9, exact labels, A10, and plain structure, A12), so a
heading or a label inside a fence is never a slice or a card, and a doc holding any fence line the rule does not
accept, any raw HTML line outside an accepted fence, any heading or label line off the plain form (indented,
after a list-item or block-quote marker, or a heading whose `#`s are not followed by exactly one space), or any
`Status:` line in a slice or `Base:` line in the header that is not exact and the last line of its paragraph (or
is a second one), stops the gate (`doc-unreadable`, naming the
line) before the ask. A doc the rule accepts is read a second time by a CommonMark reader (the E15 lane contract
A13, `spec.read`, `readings.py`): a decision the two readings take differently (the slices, a card, the recorded
base, the withheld sections), or one of the CommonMark reading's three refusals (A14: a rendered label line in a
paragraph it cannot map to source lines, a level 1 or 2 heading off the slice form that starts with "slice", a
heading that starts with `Status:` or `Base:`), stops the gate `doc-unreadable` naming the first such line, and so
does, once the workspace is known to be a git work tree, another Markdown file of HEAD that a CommonMark reader
declares the builder's notes and the line reading does not (`packet.commit_notes`, A14), before the ask. Zero slices, or a slice with no
`Status:` line, is malformed input and never passes,
collapsed or not. A collapse
comes only from `station.owner_words.collapse_gate` and passes short slices only.

The preconditions run here, before the ask: the workspace is a git work tree root; the base is found
(a `Base:` header line the build doc records, then `git merge-base` with the default branch, then the
owner's base from the input, else a stop that asks; a `Base:` line the label rule refuses (A10: not exactly 7
to 40 lowercase hex, text after it, not the last line of its paragraph, a second one) has already stopped the
gate `doc-unreadable`; an exact recorded `Base:` that resolves to nothing or names HEAD itself stops naming the
line, unless the owner's base in the input clears it (C1A2-3), and an owner's base that names HEAD itself
stops, C1A2-4); the boundary is `git diff --name-status
<base>..HEAD`; dirt (`git status --porcelain`) touching a boundary file or the build doc stops unless
the owner's `committed_only` words are in the input; dirt elsewhere is listed and the review proceeds
on HEAD. Nothing is read from a v1 file and nothing is written outside the run directory.
"""
import os

from station_core import driver, hunt as huntmod, records_link, templates

from . import common, gitio, packet, report, spec as specmod

D = templates.D
HUNTS = {
    "build": [
        {"home": "repo-plans", "root": "workspace", "globs": ["docs/plans/*-{name}.md", "docs/plans/{name}.md"], "tier": 1},
        {"home": "repo-flat", "root": "workspace", "globs": ["docs/{name}-build-plan.md"], "tier": 2},
        {"home": "phase-or-slice", "root": "workspace", "globs": ["docs/*phase*.md", "docs/*slice*.md", "plan/*.md"],
         "tier": 3},
    ],
}


def _named(run, path):
    """The build doc the invocation names (or the plan established in the session), as a workspace path."""
    ws = os.path.realpath(common.workspace(run))
    full = path if os.path.isabs(path) else os.path.join(ws, path)
    real = os.path.realpath(full)
    if not real.startswith(ws.rstrip(os.sep) + os.sep) or not real.endswith(".md") or not os.path.isfile(real):
        return None
    return os.path.relpath(real, ws)


def read(text):
    """The build doc read whole with vertical-v2's one reading rule (`fences.read`: strict plain code blocks, A8; no
    raw HTML lines, A9; exact labels, A10; plain structure, A12) and then a second time by a CommonMark reader (A13,
    `spec.read`), or spec.SpecUnreadable naming the first line the rule refuses or the first line where the two
    readings take a decision differently."""
    return specmod.read(text)


def slices_of(text):
    """[{"name", "short", "status", "line", "status_at"}] in document order, read with vertical-v2's own reading
    rule (`fences.py`, the E15 lane contract A7, A8, A9 and A10; never the frame's parse): outside fences, a
    `## Slice <name> <dash> <short>` heading (the build-doc form's slice pattern, `templates.BUILD["slice"]`)
    opens a slice, any other `## ` heading closes it, and the slice's one exact `Status:` label inside it is its
    line (A10: exact, the last line of its paragraph, at most one). A heading or a label inside a fence is
    content, never a slice or a card. Any fence line the rule does not accept, any raw HTML line outside an
    accepted fence, any heading or label line off the plain form (A12), and any `Status:` or header `Base:` line
    the label rule does not take raises
    spec.SpecUnreadable naming the line (both lines for a second label)."""
    return read(text).slices


def recorded_base(text):
    """The `Base:` line of the build doc's header (before the first `## ` heading outside a fence), or None:
    {"line": the line as written, "commit": its 7 to 40 lowercase hex value}. Under the label rule (A10) the
    header holds at most one, exact and the last line of its paragraph; any other `Base:` line there, a fence
    line the rule does not accept or a raw HTML line raises spec.SpecUnreadable naming the line, so a wrong
    value is never a base and the owner's base never clears it. A `Base:` or a `## ` line inside a fence is
    content. The handler reads the slices from the same text first (`slices_of`, the same reading), so a doc
    the reader cannot place has already stopped (`doc-unreadable`)."""
    return read(text).base


def _cards(run, ctx, doc, slices, records_root):
    """{slice name: state row} from the records component, and whether a log exists."""
    client = records_link.open_client(common.STATION, records_root=records_root)
    try:
        state = client.state(common.workspace(run), doc)
    except records_link.RecordsRefusal as refusal:
        report.finish(ctx, run, "stopped", "records-refused",
                      records_link.refusal_sentence(refusal, "reading the cards for the gate"))
    return dict((row["name"], row) for row in state.get("slices") or []), bool(state.get("exists"))


def handler(ctx, args):
    """`gate --run-dir D [--doc PATH] [--name NAME] [--records-root DIR]`."""
    run = common.open_run(ctx, args.run_dir, ("checked",), "gate")
    ws = common.workspace(run)
    words = common.owner_words(run)
    selection = {}
    if args.doc:
        doc = _named(run, args.doc)
        if doc is None:
            return ctx.emit(ctx.envelope(accepted=False, run_id=run.checkpoint["run_id"],
                                         reason="the named build doc is not an existing .md file inside the workspace: %s"
                                                % args.doc), 5)
        selection["build"] = {"outcome": "one", "named": doc}
    else:
        try:
            found = huntmod.hunt(HUNTS["build"], {"workspace": ws}, name=args.name)
        except huntmod.HuntRefused as exc:
            raise driver.Usage(str(exc))
        selection["build"] = dict(found, hunt="build", name=args.name)
        common.write(run, "selection-build.json", selection["build"])
        if found["outcome"] == "none":
            report.finish(ctx, run, "stopped", "selection-none",
                          "no build doc was found in the repo's tiers (docs/plans/, then docs/<feature>-build-plan.md, "
                          "then a phase or slice doc): ask the owner which build doc this review is for, and run again "
                          "with --doc", selection=selection)
        if found["outcome"] == "several":
            names = ", ".join(os.path.relpath(c["path"], ws) for c in found["candidates"])
            report.finish(ctx, run, "stopped", "selection-several",
                          "several build docs match (%s): list them for the owner and run again with --doc naming his "
                          "pick; none is picked here" % names, selection=selection)
        doc = os.path.relpath(found["candidates"][0]["path"], ws)
    gate = {"doc": doc, "feature": common.feature_of(doc), "slices": [], "short": [], "disagree": [], "notes": [],
            "collapse": None, "committed_only": None, "malformed": [], "base": None, "head": None, "boundary": [],
            "dirt": None}
    with open(os.path.join(ws, doc), encoding="utf-8", newline="") as fh:
        text = fh.read()
    try:
        slices = slices_of(text)
    except specmod.SpecUnreadable as exc:
        gate["malformed"].append(str(exc))
        common.write(run, "gate.json", gate)
        report.finish(ctx, run, "stopped", specmod.STOP_TAG,
                      "the gate cannot read the build doc's slices and Status: lines cleanly, so it never passes: %s"
                      % exc, selection=selection, gate=gate)
    if not slices:
        gate["malformed"].append("the build doc has no '## Slice <name> %s <short name>' heading" % D)
    for item in slices:
        if item["status"] is None:
            gate["malformed"].append("slice %s has no Status: line" % item["name"])
    if gate["malformed"]:
        common.write(run, "gate.json", gate)
        report.finish(ctx, run, "stopped", "gate-malformed",
                      "the build doc is malformed input and the gate never passes vacuously: %s"
                      % "; ".join(gate["malformed"]), selection=selection, gate=gate)
    if not gitio.is_work_tree_root(ws) or gitio.head(ws) is None:
        common.write(run, "gate.json", gate)
        report.finish(ctx, run, "stopped", "not-git",
                      "the workspace is not a git work tree root with a commit: no base, no export and no boundary, "
                      "so vertical-v2 cannot run here", selection=selection, gate=gate)
    try:
        packet.commit_notes(ws, gitio.head(ws), doc)
    except specmod.SpecUnreadable as exc:
        gate["malformed"].append(str(exc))
        common.write(run, "gate.json", gate)
        report.finish(ctx, run, "stopped", specmod.STOP_TAG,
                      "the gate cannot read a Markdown file of the reviewed commit cleanly, so it never passes: %s"
                      % exc, selection=selection, gate=gate)
    cards, log_exists = _cards(run, ctx, doc, slices, args.records_root)
    for item in slices:
        row = cards.get(item["name"])
        entry = {"name": item["name"], "status_line": item["status"], "card": None, "card_source": "status-line",
                 "card_derived": None}
        if row is None or row.get("card_observed") is None:
            entry["card"] = item["status"]
            gate["notes"].append("slice %s: no log events name its card%s, so its card is its Status: line"
                                 % (item["name"], "" if log_exists else " (the build doc has no records log)"))
        else:
            card = row["card_observed"] if row["card_observed"] != "none" else row.get("card_observed_text")
            entry.update(card=card, card_source="records", card_derived=row.get("card_derived"))
            if card != item["status"]:
                gate["disagree"].append({"name": item["name"], "card": card, "status_line": item["status"]})
        gate["slices"].append(entry)
        if entry["card"] != common.SIGNED_OFF:
            gate["short"].append({"name": item["name"], "state": entry["card"]})
    if gate["disagree"]:
        common.write(run, "gate.json", gate)
        report.finish(ctx, run, "stopped", "card-disagrees",
                      "the records and the build doc disagree; reconcile them before a whole-build review: %s"
                      % "; ".join("slice %s: the records say %r, its Status: line says %r"
                                  % (d["name"], d["card"], d["status_line"]) for d in gate["disagree"]),
                      selection=selection, gate=gate)
    if gate["short"]:
        if words.get("collapse_gate"):
            gate["collapse"] = {"words": words["collapse_gate"], "short": list(gate["short"])}
        else:
            remedy = ""
            if any(s["state"] == "built" for s in gate["short"]):
                remedy = " A built slice's remedy is a fresh signoff, never a recheck."
            common.write(run, "gate.json", gate)
            report.finish(ctx, run, "stopped", "gate-short",
                          "every slice must stand signed off before a whole-build review; short: %s.%s"
                          % (", ".join("slice %s (%s)" % (s["name"], s["state"]) for s in gate["short"]), remedy),
                          selection=selection, gate=gate)
    gate["head"] = gitio.head(ws)
    gate["base"] = _base(run, ctx, ws, text, words, selection, gate)
    gate["boundary"] = gitio.name_status(ws, gate["base"]["commit"])
    touched = set(r["path"] for r in gate["boundary"]) | set(r["from"] for r in gate["boundary"] if r.get("from"))
    touched.add(doc)
    dirty = gitio.dirt(ws)
    gate["dirt"] = {"inside": sorted(p for p in dirty if p in touched),
                    "outside": sorted(p for p in dirty if p not in touched)}
    if gate["dirt"]["inside"]:
        if words.get("committed_only"):
            gate["committed_only"] = {"words": words["committed_only"]}
        else:
            common.write(run, "gate.json", gate)
            report.finish(ctx, run, "stopped", "dirty-boundary",
                          "the working tree is dirty where the review looks (%s): the review would grade stale code. "
                          "The owner decides: commit first, or order a committed-state-only run in his words"
                          % ", ".join(gate["dirt"]["inside"]), selection=selection, gate=gate)
    common.write(run, "gate.json", gate)
    common.advance(run, "gated")
    return ctx.emit(ctx.envelope(next="ask", run_id=run.checkpoint["run_id"], doc=doc, base=gate["base"],
                                 head=gate["head"], boundary=len(gate["boundary"]), dirt=gate["dirt"],
                                 collapse=gate["collapse"], notes=gate["notes"]))


HEAD_STOP = "names HEAD itself, so the boundary is empty and there is nothing to review"
ANSWER_HOME = "run again with his answer in station.owner_words.base"


def _owner(ws, given):
    """(the owner's base commit, or None, and why it cannot be taken, or None)."""
    if not isinstance(given, dict):
        return None, None
    commit = gitio.commit_of(ws, given.get("commit"))
    if commit is None:
        return None, "the owner's base %r resolves to no commit here: ask him for the base again" % given.get("commit")
    if commit == gitio.head(ws):
        return None, "the owner's base %s: ask him for the base again" % HEAD_STOP
    return commit, None


def _base(run, ctx, ws, text, words, selection, gate):
    """v1's precedence: the doc's `Base:` line, then the merge base with the default branch, then the owner's
    base. An exact `Base:` line that cannot be taken is cleared by the owner's base on a fresh run (C1A2-3), and
    an owner's base that names HEAD itself stops wherever it is taken (C1A2-4). A `Base:` line the label rule
    refuses never reaches here (A10: the gate stopped `doc-unreadable`)."""
    given = words.get("base")
    recorded = recorded_base(text)
    if recorded is not None:
        stop = None
        commit = gitio.commit_of(ws, recorded["commit"])
        if commit is None:
            stop = ("the build doc records the base %r on its Base: line, and it resolves to no commit here: ask the "
                    "owner for the base and never guess" % recorded["line"])
        elif commit == gitio.head(ws):
            stop = ("the build doc's base line %r %s: ask the owner for the base and never guess"
                    % (recorded["line"], HEAD_STOP))
        if stop is None:
            return {"commit": commit, "how": "doc", "field": recorded["line"]}
        owner, why = _owner(ws, given)
        if owner is not None:
            return {"commit": owner, "how": "owner", "words": given.get("words"),
                    "field": "over the build doc's %r" % recorded["line"]}
        common.write(run, "gate.json", gate)
        report.finish(ctx, run, "stopped", "base-unresolved",
                      "%s; %s" % (stop, why or ANSWER_HOME), selection=selection, gate=gate)
    branch = gitio.default_branch(ws)
    if branch is not None:
        base = gitio.merge_base(ws, branch)
        if base and base != gitio.head(ws):
            return {"commit": base, "how": "merge-base", "field": "git merge-base %s HEAD" % branch}
    owner, why = _owner(ws, given)
    if owner is not None:
        return {"commit": owner, "how": "owner", "words": given.get("words")}
    common.write(run, "gate.json", gate)
    report.finish(ctx, run, "stopped", "base-unresolved",
                  why or ("no base: the build doc records none (a Base: line) and the merge base with the default "
                          "branch is %s; ask the owner for the base and %s"
                          % ("HEAD itself" if branch is not None else "not resolvable", ANSWER_HOME)),
                  selection=selection, gate=gate)
