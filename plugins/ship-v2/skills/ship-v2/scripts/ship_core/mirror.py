"""THE SAVE STEP (the E15 lane contract A30 (1); contract section 3.11): recheck-v2's precondition, named by ship-v2,
taken by the executor. Stated once here and once in the contract, coded once.

    relative(ws, path) -> a listed path as a normalized workspace-relative path, or None
    note(run, state, name, result) -> the verdict mirror the station's result lists, recorded as it stands now
    unsaved(run, state) -> [(path, why)]: each recorded mirror that is not committed as it stands
    saved_as_it_stood(ws, state, rel) -> whether `rel` is a recorded mirror committed exactly as it stood
    step(state, found) -> the step as the executor takes it: its name, the files and why each, the commands
    pending(run, state) -> the step for every mirror not committed as it stands, or None (`fix` prints it)
    refusal(run, state) -> (reason, step) for `visit --station recheck-v2`, or None
    not_taken(run, state) -> the `recheck-stopped` reason for `report` at `fixed` while a mirror is unsaved, or None

THE MIRROR. The signoff verdict mirror: the file under `docs/reviews/` that signoff-v2's result lists as its
`verdict_doc`, and that recheck-v2's result lists as its `verdict_doc_copy` when it appends its block there. ship-v2
records it at that station's close, after the visit's window held (the window rule, `window.py`), as it stood then:
its identity with lstat semantics (`pin.identity`: type, mode and content). A row naming a path outside the workspace,
outside `docs/reviews/`, or a path that is not a regular file is not a mirror.

THE STEP. recheck-v2's own contract (its section 9, E13's F8) requires the mirror committed before a recheck: its
boundary check reads any change to untracked content as a violation, so a recheck that appends its block to an
untracked mirror ends `not_clear` and freezes the card. Before every recheck-v2 visit the executor commits the mirror
locally, exactly that file and nothing else, a named step outside any ship script (as the E15 lane contract A2's Q2
made handoff's checkpoint commit): ship-v2 prints it (`step`) and never runs it. No ship script runs a git command
that changes a branch, an index or a worktree; `gitio.py` reads only.

THE REFUSAL. `visit --station recheck-v2` refuses, exit 5 and nothing written, while a recorded mirror is untracked
(git does not track it, the repository's ignore rules included) or differs from its committed bytes (its bytes on disk
are not the bytes HEAD holds, or git reports it changed or staged), naming the step and the file (`unsaved`).

THE STEP NOT TAKEN (the E15 lane contract A31 (1), the owner's ruling "End it as recheck stopped"). When the step
cannot be taken (the owner declines it, a hook refuses the commit, git cannot commit), `report` at `fixed` while a
recorded mirror is unsaved ends the run STOPPED with the existing tag `recheck-stopped`, its reason naming each unsaved
file and why, in THE REFUSAL's own words (`not_taken`); no new stop word, recheck-v2 is not visited. With every
mirror committed as it stands, `report` at `fixed` stays out of turn (exit 2): the next move is the recheck visit.

THE SANCTIONED COMMIT. The window rule takes a commit of the mirror as the session's sanctioned step when the mirror
is committed exactly as it stood: its identity on disk is the one recorded, and HEAD holds those bytes with nothing
changed or staged (`saved_as_it_stood`). Any other file in that commit is held by the window rule as any move is.
"""
import hashlib
import os
import shlex
import stat

from station_core import fsio

from . import common, gitio, pin

REVIEWS = "docs/reviews/"
KINDS = {"signoff-v2": "verdict_doc", "recheck-v2": "verdict_doc_copy"}
STEP = "save the verdict mirror"


def relative(ws, path):
    """A listed path as a normalized workspace-relative path, or None (outside the workspace, or not a path)."""
    if not isinstance(path, str) or not path:
        return None
    if os.path.isabs(path):
        real, base = os.path.realpath(path), os.path.realpath(ws)
        if not fsio.inside(real, base) or real == base:
            return None
        path = os.path.relpath(real, base)
    path = os.path.normpath(path)
    return None if path.startswith("..") or os.path.isabs(path) else path


def _regular(ws, rel):
    try:
        return stat.S_ISREG(os.lstat(os.path.join(ws, rel)).st_mode)
    except OSError:
        return False


def listed(ws, name, result):
    """The mirror paths the station's own result lists (THE MIRROR), sorted."""
    kind = KINDS.get(name)
    if kind is None or not isinstance(result, dict):
        return []
    out = set()
    for row in result.get("records_written") or []:
        if not isinstance(row, dict) or row.get("kind") != kind:
            continue
        rel = relative(ws, row.get("path"))
        if rel is not None and rel.replace(os.sep, "/").startswith(REVIEWS) and _regular(ws, rel):
            out.add(rel)
    return sorted(out)


def note(run, state, name, result):
    """Each mirror the station's result lists, recorded in `state["mirrors"]` as it stands now (its identity)."""
    ws = common.workspace(run)
    mirrors = dict(state.get("mirrors") or {})
    for rel in listed(ws, name, result):
        mirrors[rel] = pin.identity(ws, rel)
    if mirrors:
        state["mirrors"] = mirrors
    return state


def _blob_id(ws, rel):
    """The object id git would give the file's bytes as a blob, in the repository's object format."""
    with open(os.path.join(ws, rel), "rb") as fh:
        data = fh.read()
    fmt = gitio.object_format(ws)
    digest = hashlib.new("sha256" if fmt == "sha256" else "sha1")
    digest.update(b"blob %d\0" % len(data))
    digest.update(data)
    return digest.hexdigest()


def why_unsaved(ws, rel):
    """None when git tracks `rel` and HEAD holds its bytes on disk with nothing changed or staged; else why not."""
    if not _regular(ws, rel):
        return "is not a regular file in the workspace any more"
    entries = gitio.status_of(ws, rel)
    codes = set(code for code, _ in entries)
    if "!!" in codes:
        return ("is untracked: the repository's ignore rules leave it out, so committing it takes `git add --force`, "
                "the owner's call (ask him, a pause)")
    if "??" in codes:
        return "is untracked"
    held = gitio.blob_at_head(ws, rel)
    if held is None:
        return "is untracked: HEAD does not hold it (staged, never committed)"
    if entries or held != _blob_id(ws, rel):
        return "differs from its committed bytes (changed or staged since the last commit, not committed)"
    return None


def unsaved(run, state):
    """[(path, why)] for each recorded mirror that is not committed as it stands (THE REFUSAL)."""
    ws = common.workspace(run)
    out = []
    for rel in sorted(state.get("mirrors") or {}):
        why = why_unsaved(ws, rel)
        if why is not None:
            out.append((rel, why))
    return out


def saved_as_it_stood(ws, state, rel):
    """Whether `rel` is a recorded mirror committed exactly as it stood (THE SANCTIONED COMMIT)."""
    recorded = (state.get("mirrors") or {}).get(rel)
    return recorded is not None and pin.identity(ws, rel) == recorded and why_unsaved(ws, rel) is None


def step(state, found):
    """The step as the executor takes it, for `found` ([(workspace-relative path, why)]): its name, the files and why
    each needs it, and the two commands, printed for the executor and run by no ship script."""
    found = sorted(found)
    files = [rel for rel, _ in found]
    if not files:
        return None
    quoted = " ".join(shlex.quote(f) for f in files)
    message = "ship-v2: save the signoff verdict mirror before recheck-v2 (slice %s)" % state.get("slice")
    return {"step": "%s: commit it locally, exactly %s and nothing else, outside any ship script, then run `visit "
                    "--station recheck-v2`; no push, no other file, no hook bypassed"
                    % (STEP, "that file" if len(files) == 1 else "those files"),
            "files": files, "why": dict(found),
            "commands": ["git add -- %s" % quoted, "git commit --only -m %s -- %s" % (shlex.quote(message), quoted)]}


def pending(run, state):
    """The step for every recorded mirror not committed as it stands, or None."""
    return step(state, unsaved(run, state))


def refusal(run, state):
    """(reason, step) for `visit --station recheck-v2` while a mirror is unsaved, or None (THE REFUSAL)."""
    found = unsaved(run, state)
    if not found:
        return None
    taken = step(state, found)
    reason = ("recheck-v2's own contract requires the signoff verdict mirror committed before its visit, and %s; take "
              "the named step %r yourself, outside any ship script (a local commit of exactly %s, nothing else): %s; "
              "then run `visit --station recheck-v2` again; if the step cannot be taken (the owner declines it, a hook "
              "refuses the commit, git cannot commit), never bypass the hook: run `report`, which ends the run "
              "`recheck-stopped`"
              % ("; ".join("%s %s" % (rel, why) for rel, why in found), STEP,
                 ", ".join(rel for rel, _ in found), " then ".join("`%s`" % c for c in taken["commands"])))
    return reason, taken


def not_taken(run, state):
    """The reason `report` at `fixed` ends the run `recheck-stopped` with while a recorded mirror is unsaved (THE STEP
    NOT TAKEN), naming each file and why in THE REFUSAL's own words; None when every mirror is committed as it
    stands (then `report` is out of turn there: the next move is the recheck visit)."""
    found = unsaved(run, state)
    if not found:
        return None
    return ("the named step %r was not taken before recheck-v2's visit: %s; recheck-v2's own contract requires the "
            "signoff verdict mirror committed before it runs, so recheck-v2 was not visited and the run ends here "
            "(no ship script commits anything)"
            % (STEP, "; ".join("%s %s" % (rel, why) for rel, why in found)))
