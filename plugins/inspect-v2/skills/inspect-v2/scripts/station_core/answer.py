"""`record-answer`'s shared refusals (ruling E14-11, control room reading CR-3).

One implementation for the four cores. A core maps its own recorded answer onto the neutral view
this module reads, then calls `check` (pure) or `record` (writes `answer.json` only when the
answer is accepted):

    {"questions": [{"id": "Q1", "text": "...", "touches": [<ledger line id>, ...], "answer": "..."}],
     "lines":     [{"text": "...", "tag": "decided" | "assumed" | "parked" | "open" | ...,
                    "trace": {"kind": <trace kind>, "ref": "..."}}]}

`questions` are the questions the executor put to the owner in this run, each with the ledger
line ids it touches and the owner's answer. `lines` are the lines the executor asserts, each with
its trace. The trace kinds:

    ledger        a ledger line id of the scope doc this run read
    repo_path     a path that exists inside the workspace
    question      the id of a question of this run that the owner answered
    assumed       the executor's why, where the core's lane contract allows assumptions
    owner_words   the owner's words quoted, where the core's lane contract allows them

`DEFAULT_TRACES` is the three E14-11 names; a core passes `allowed` to widen it for its own
lines. The refusals, each `{"rule", "message", ...}` naming the question or line:

    shape              the answer is not the view above (not a refusal a person could fix by
                       asking something else, but it is refused the same way, never repaired)
    re-asked-decided   a question touches a `decided` ledger line
    unknown-line       a question touches an id the ledger does not hold
    untraced           a line with no trace, a trace kind the core does not allow, or a trace
                       that names nothing (an unknown ledger id, a path that is not in the
                       workspace, a question not answered in this run, an empty why or quote)
    quietly-resolved   a line asserted as `decided` whose trace is a `parked` or `open` ledger
                       line that no ANSWERED question of this run touched (a question asked and
                       left without an answer settles nothing)

Any refusal is exit 5 and nothing is written (station-loop.md section 3.4).
"""
import os

from . import exits, fsio

DEFAULT_TRACES = ("ledger", "repo_path", "question")
KNOWN_TRACES = DEFAULT_TRACES + ("assumed", "owner_words")


def _refusal(rule, message, **where):
    row = {"rule": rule, "message": message}
    row.update(where)
    return row


def _shape(answer):
    if not isinstance(answer, dict):
        return ["the answer is not an object"]
    problems = []
    for key in ("questions", "lines"):
        if not isinstance(answer.get(key), list):
            problems.append("the answer's %r is a list" % key)
    if problems:
        return problems
    ids = []
    for index, q in enumerate(answer["questions"]):
        if not isinstance(q, dict) or not isinstance(q.get("id"), str) or not q["id"].strip():
            problems.append("question %d carries no id" % index)
            continue
        if not isinstance(q.get("touches", []), list):
            problems.append("question %s: 'touches' is a list of ledger line ids" % q["id"])
        ids.append(q["id"])
    if len(ids) != len(set(ids)):
        problems.append("two questions share an id")
    for index, line in enumerate(answer["lines"]):
        if not isinstance(line, dict) or not isinstance(line.get("text"), str):
            problems.append("line %d is not an object with its text" % index)
    return problems


def _in_workspace(workspace, rel):
    if not workspace or not isinstance(rel, str) or not rel.strip() or os.path.isabs(rel):
        return False
    path = os.path.join(workspace, rel)
    return os.path.exists(path) and fsio.inside(path, workspace)


def check(answer, ledger_lines, workspace=None, allowed=DEFAULT_TRACES):
    """{"exit": 0 | 5, "refusals": [...]}; pure, nothing written."""
    problems = _shape(answer)
    if problems:
        return {"exit": exits.REFUSED,
                "refusals": [_refusal("shape", p) for p in problems]}
    ledger = dict((row["id"], row) for row in ledger_lines)
    refusals = []
    answered = set()
    touched = set()
    for q in answer["questions"]:
        if isinstance(q.get("answer"), str) and q["answer"].strip():
            answered.add(q["id"])
        for ident in q.get("touches", []):
            row = ledger.get(ident)
            if row is None:
                refusals.append(_refusal("unknown-line", "question %s touches %r, which is no line of the "
                                         "scope doc's ledger" % (q["id"], ident), question=q["id"], line_id=ident))
                continue
            if q["id"] in answered:
                # only an answered question of this run settles a line (C1-9); an unanswered one
                # that touches a parked or open line settles nothing
                touched.add(ident)
            if row["tag"] == "decided":
                refusals.append(_refusal("re-asked-decided", "question %s re-asks a decided line: %r (%s); a "
                                         "decided line passes forward and is never asked again"
                                         % (q["id"], row["text"], ident), question=q["id"], line_id=ident))
    for index, line in enumerate(answer["lines"]):
        trace = line.get("trace")
        kind = trace.get("kind") if isinstance(trace, dict) else None
        ref = trace.get("ref") if isinstance(trace, dict) else None
        where = {"line": index, "text": line["text"]}
        why = None
        if kind is None:
            why = "it carries no trace"
        elif kind not in allowed:
            why = "its trace kind %r is not one this core allows (%s)" % (kind, ", ".join(allowed))
        elif kind == "ledger" and ref not in ledger:
            why = "its ledger id %r is no line of the scope doc's ledger" % (ref,)
        elif kind == "repo_path" and not _in_workspace(workspace, ref):
            why = "its path %r is not in the workspace" % (ref,)
        elif kind == "question" and ref not in answered:
            why = "its question %r was not answered in this run" % (ref,)
        elif kind in ("assumed", "owner_words") and not (isinstance(ref, str) and ref.strip()):
            why = "its %s is empty" % ("why" if kind == "assumed" else "quote")
        if why:
            refusals.append(_refusal("untraced", "the line %r is refused: %s" % (line["text"], why), **where))
            continue
        if kind == "ledger" and line.get("tag") == "decided" and ledger[ref]["tag"] in ("parked", "open") \
                and ref not in touched:
            refusals.append(_refusal("quietly-resolved", "the line %r is asserted as decided, but its ledger "
                                     "line %s is %s and no question of this run settled it"
                                     % (line["text"], ref, ledger[ref]["tag"]), **where))
    return {"exit": exits.REFUSED if refusals else exits.SUCCESS, "refusals": refusals}


def record(run_dir, answer, ledger_lines, workspace=None, allowed=DEFAULT_TRACES):
    """(exit code, report). `answer.json` is written in `run_dir` only when the answer is accepted."""
    result = check(answer, ledger_lines, workspace=workspace, allowed=allowed)
    if result["exit"] != exits.SUCCESS:
        return result["exit"], {"accepted": False, "refusals": result["refusals"],
                                "reason": "the recorded answer was refused on its content (%d refusal(s)); "
                                          "nothing was written" % len(result["refusals"])}
    path = os.path.join(run_dir, "answer.json")
    fsio.write_json(path, answer)
    return exits.SUCCESS, {"accepted": True, "refusals": [], "answer": path,
                           "sha256": fsio.sha256_file(path)}
