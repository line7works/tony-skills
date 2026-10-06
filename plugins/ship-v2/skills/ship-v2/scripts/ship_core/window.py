"""THE WINDOW RULE (the E15 lane contract A28 (1); contract section 3.5): one rule for every station visit and every
step between visits, stated once here and once in the contract, coded once.

    take(run, state) -> the pin, set into `state` (`state["pin"]`, `state["own"]` emptied)
    hold(run, state, where, station=None, named=(), leave_inside=False, footprint=None) -> Held
    evidence(run, state, name, result, visit_run_dir) -> the station's own listed writes, for `hold(station=...)`
    own(state, receipt) -> ship-v2's own `Status:` write of a grant, recorded against the pin

THE PIN. What the workspace holds: HEAD and the identity of every changed or untracked path (`pin.take`, build-v2's
source pin: `docs/records/` left out, ignored files not seen), and the build doc's sha256. ship-v2 takes it when each
station visit opens (build-v2, signoff-v2 and recheck-v2 alike), and again after each check point that holds with
nothing left over.

THE CHECK POINTS. A visit's opening (`visit --station`, the window since the last step), a visit's close (`visit
--result`, the window the visit was open in), `fix`, `lap`, a pause's answer (`pause --answer`; a pause asked while a
visit is open is inside that visit's window, which its close holds), and `report` at `clean` or `exhausted` (a run
that already ended at a stop, or ends `visit-unfinished`, holds nothing more).

THE RULE. At each check point everything that moved since the last pin is held, net of two kinds of sanctioned write:

1. The station's own listed writes, at that station's close only, as its own result lists them:
   - build-v2: the paths its source set lists (`committed`, `changed`, `untracked`: the build's own work, named);
     and the build doc when its result names it in `source_set.sanctioned` (the ledger document the loop writes by
     design, build-contract section 8): its `status_line` write is a link from any bytes to the hash that row gives
     (a sanctioned doc with no such row is the build's whatever its bytes);
   - signoff-v2: the project files its `records_written` lists, by the document steps of its own `receipt.json` (the
     path its result names, a regular file inside the visit's run directory): each step's target, its hash before and
     after, its state `done`;
   - recheck-v2: the project files its `records_written` lists, each row's hash before and after.
2. ship-v2's own sanctioned writes since the pin: each grant's `Status:` line (`state["own"]`: its receipt's hash
   before and after, in order).

The build doc counts as theirs only when those writes, the station's in their order and ship-v2's in theirs,
interleaved, run as one chain of hashes from the doc at the pin to the doc as it stands, so a hand edit before, between
or after them is never taken for theirs. Another project file counts as the station's when the station lists it and
it stands at the last hash the station gives (or the station gives none). Of what is left:

- the build doc moved (or named by a fix) is stop 2 (`spec-change`);
- a path outside the slice's footprint, moved or named, is stop 4 (`outside-footprint`);
- a path inside it is the step's to name: the lap's fixes name theirs at `fix`, build-v2's source set names the
  build's at its close; any other is refused (exit 5, nothing written: put it back, then run the command again),
  except while a lap's fixes are open (`leave_inside`: a pause answered at `fixing` or `lap-needed`, and `lap`), where
  it is left for `fix` to name and the pin stays where it is.

The pin moves forward only at a check point that holds with nothing left over. Git runs read-only (`gitio.py`).
"""
import json
import os
import stat

from station_core import fsio

from . import common, doc as docmod, pin

ANY = "*any bytes*"          # a link's `before` for build-v2's sanctioned ledger write: the build loop's own bytes


class Held(object):
    """A check point's verdict: `stop` (tag, reason, condition), `refuse` (reason), or neither; `left` the inside paths
    left for `fix` to name; `moved` every path that moved since the pin, net of the sanctioned writes."""

    def __init__(self, stop=None, refuse=None, left=(), moved=()):
        self.stop, self.refuse, self.left, self.moved = stop, refuse, list(left), list(moved)

    @property
    def holds(self):
        return self.stop is None and self.refuse is None


def _doc_sha(run, state):
    return fsio.sha256_file_or_none(os.path.join(common.workspace(run), state["doc"]))


def take(run, state):
    """The pin, set into `state` (THE PIN); ship-v2's own writes recorded against the old pin are dropped with it."""
    state["pin"] = dict(pin.take(common.workspace(run)), doc_sha256=_doc_sha(run, state))
    state["own"] = []
    return state


def own(state, receipt):
    """ship-v2's own `Status:` write of one grant, recorded once against the pin (2. above)."""
    if not receipt or not receipt.get("doc_written") or not receipt.get("card"):
        return state
    links = list(state.get("own") or [])
    if not any(link.get("pause") == receipt["pause"] for link in links):
        links.append({"pause": receipt["pause"], "before": receipt.get("doc_sha256_before"),
                      "after": receipt.get("doc_sha256_after")})
    state["own"] = links
    return state


# ---- the station's own listed writes --------------------------------------------------------------------------------

def _rel(ws, path):
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


def _sha(value):
    return value if isinstance(value, str) else None


def _receipt_steps(path, visit_run_dir):
    """signoff-v2's own document steps, from its `receipt.json`; [] when the path is not a regular file inside the visit's
    run directory, cannot be read, or holds no steps (so nothing is taken for the station's)."""
    if not isinstance(path, str) or not path:
        return []
    try:
        mode = os.lstat(path).st_mode
    except OSError:
        return []
    if not stat.S_ISREG(mode) or not fsio.inside(path, visit_run_dir):
        return []
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError):
        return []
    steps = doc.get("steps") if isinstance(doc, dict) else None
    return [s for s in steps if isinstance(s, dict)] if isinstance(steps, list) else []


def evidence(run, state, name, result, visit_run_dir):
    """{"links": [(before, after)] of the build doc in the station's order, or None (the doc is the station's whatever
    its bytes), "files": {path: last hash after or None}, "named": [paths]}: the station's own listed writes (1.)."""
    ws, rel = common.workspace(run), state["doc"]
    out = {"links": [], "files": {}, "named": []}
    if not isinstance(result, dict):
        return out
    if name == "build-v2":
        source = result.get("source_set") if isinstance(result.get("source_set"), dict) else {}
        out["named"] = sorted(set(p for key in ("committed", "changed", "untracked")
                                  for p in (_rel(ws, x) for x in source.get(key) or []) if p is not None))
        sanctioned = [_rel(ws, (row or {}).get("path")) for row in source.get("sanctioned") or []
                      if isinstance(row, dict)]
        if rel in sanctioned:
            afters = [_sha(row.get("sha256_after")) for row in result.get("writes") or []
                      if isinstance(row, dict) and row.get("kind") == "status_line" and _rel(ws, row.get("path")) == rel]
            out["links"] = [(ANY, afters[-1])] if afters and afters[-1] else None
        return out
    if name == "signoff-v2":
        listed = set(_rel(ws, row.get("path")) for row in result.get("records_written") or []
                     if isinstance(row, dict) and row.get("kind") != "run_artifact")
        for step in _receipt_steps(result.get("receipt"), visit_run_dir):
            target = _rel(ws, step.get("target"))
            if target is None or target not in listed or step.get("state") != "done":
                continue
            if target == rel:
                out["links"].append((_sha(step.get("before_sha256")), _sha(step.get("after_sha256"))))
            else:
                out["files"][target] = _sha(step.get("after_sha256"))
        return out
    for row in result.get("records_written") or []:
        if not isinstance(row, dict) or row.get("kind") == "run_artifact":
            continue
        target = _rel(ws, row.get("path"))
        if target is None:
            continue
        if target == rel:
            out["links"].append((_sha(row.get("sha256_before")), _sha(row.get("sha256_after"))))
        else:
            out["files"][target] = _sha(row.get("sha256_after"))
    return out


# ---- the rule -------------------------------------------------------------------------------------------------------

def _chain(start, end, station, ship):
    """Whether the station's links (in order) and ship-v2's (in order), interleaved and each used once, run from
    `start` to `end`. A station link whose `before` is ANY starts from any bytes."""
    seen = set()

    def walk(i, j, at):
        key = (i, j, at)
        if key in seen:
            return False
        seen.add(key)
        if i == len(station) and j == len(ship):
            return at == end
        if i < len(station):
            before, after = station[i]
            if after is not None and (before == ANY or (before is not None and before == at)) and walk(i + 1, j, after):
                return True
        if j < len(ship):
            before, after = ship[j]
            if after is not None and before is not None and before == at and walk(i, j + 1, after):
                return True
        return False
    return walk(0, 0, start)


def hold(run, state, where, station=None, named=(), leave_inside=False, footprint=None):
    """THE RULE at one check point (module docstring). `where` names the window in the stop's or the refusal's words;
    `station` is `evidence(...)` at a visit's close; `named` the paths the step names (a lap's fixes)."""
    base = state.get("pin")
    if not base:
        return Held()
    ws, rel = common.workspace(run), state["doc"]
    footprint = state["footprint"] if footprint is None else footprint
    station = station or {"links": [], "files": {}, "named": []}
    declared = set(named)
    named = declared | set(station.get("named") or [])
    now = _doc_sha(run, state)
    ship = [(link.get("before"), link.get("after")) for link in state.get("own") or []]
    doc_moved = now != base.get("doc_sha256")
    if doc_moved and station.get("links") is not None:
        doc_moved = not _chain(base.get("doc_sha256"), now, station["links"], ship)
    elif doc_moved:
        doc_moved = False                       # build-v2's sanctioned ledger document, no hash given
    files = station.get("files") or {}

    def theirs(path):
        if path not in files:
            return False
        return files[path] is None or files[path] == fsio.sha256_file_or_none(os.path.join(ws, path))
    moved = [p for p in pin.moved(ws, base) if p != rel and not theirs(p)]
    if doc_moved or rel in declared:
        return Held(stop=("spec-change", "the build doc %s moved %s, and not by a write the station's result lists or "
                                         "ship-v2's own `Status:` write%s: the doc holds the slice's spec and a fix is "
                                         "never a spec edit, so the run stops at condition 2"
                          % (rel, where, " (a fix names it)" if rel in declared else ""), 2), moved=moved)
    outside = sorted(set(p for p in moved + sorted(declared) if not docmod.in_footprint(p, footprint)))
    if outside:
        return Held(stop=("outside-footprint", "%s, files outside slice %s's footprint (%s) moved or were named: %s; "
                                               "work wants to touch files outside the slice scope, so the run stops "
                                               "at condition 4" % (where[0].upper() + where[1:], state["slice"],
                                                                   ", ".join(footprint) or "the slice names no path",
                                                                   ", ".join(outside)), 4), moved=moved)
    unnamed = [p for p in moved if p not in named]
    if unnamed and leave_inside:
        return Held(left=unnamed, moved=moved)
    if unnamed:
        return Held(refuse="%s, paths inside slice %s's footprint moved that nothing names (no fix, and no listed write "
                           "of the station): %s; every change traces to a named finding, so put them back, then run the "
                           "command again" % (where[0].upper() + where[1:], state["slice"], ", ".join(unnamed)),
                    moved=moved)
    return Held(moved=moved)
