"""The recorded reviewer answer, and what the core does with it.

The reviewer judges the code; this module never does. What it decides is bookkeeping the contract
fixes in advance (ruling E13-4, "the executor decides, the script records"):

1. **Is the answer recordable at all?** An answer from the session that built the slice is
   refused (`independence`). A finding missing a location, a claim, a scenario or an evidence
   kind refuses the whole answer (`answer_invalid`): nothing is raised, no verdict is recorded,
   and the answer is neither acted on nor repaired. A finding or a verdict that quotes the
   builder's withheld conversation is refused (`independence`) — a claim is never evidence,
   wherever it rode in.
2. **Raised or note?** A finding whose location sits inside the source set is RAISED. One whose
   location sits outside it is kept as a NOTE, not raised (lane contract section 10), and so is
   anything the reviewer itself kept in `notes_kept`.
3. **The verdict.** v1's severity mapping over the raised findings (`verdict.py`). The reviewer's
   stated verdict is recorded beside it and a disagreement is reported, never silently resolved.

A clean review must list its checks: no findings and no executed check with output is not a clean
verdict but an answer the run refuses, which the result schema then also refuses (exit 4).
"""
import re

from . import verdict as vdmod
from .constants import EVIDENCE_KINDS

LOCATION = re.compile(r"^(?P<file>[^\s:][^:]*?):(?P<line>\d+)(?:-(?P<line_end>\d+))?"
                      r"(?:\s*\((?P<tag>[^)]*)\))?$")
REQUIRED = ("location", "claim", "scenario", "evidence_kind")
MIN_QUOTE = 24   # a withheld line shorter than this is not treated as a citation


def parse_location(raw):
    """(file, line) for a `file:line` location, or (None, None).

    The grammar is Appendix A's location field: a path, a colon, a line, optionally a range and a
    parenthetical tag glued to it."""
    if not isinstance(raw, str):
        return None, None
    match = LOCATION.match(raw.strip())
    if not match:
        return None, None
    return match.group("file"), int(match.group("line"))


def _normalize(text):
    return " ".join(str(text or "").split()).lower()


def citations(row, withheld_lines):
    """The withheld lines a finding or an answer quotes, verbatim, ignoring whitespace."""
    haystack = " · ".join(_normalize(row.get(field)) for field in
                               ("claim", "scenario", "notes", "verdict", "location"))
    hits = []
    for line in withheld_lines:
        needle = _normalize(line)
        if len(needle) >= MIN_QUOTE and needle in haystack:
            hits.append(line)
    return hits


def check_finding(row, index, source_paths, withheld_lines):
    """[] when the finding is recordable, else one problem per rule it breaks."""
    problems = []
    if not isinstance(row, dict):
        return [{"index": index, "why": "a finding must be an object"}]
    for field in REQUIRED:
        value = row.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            problems.append({"index": index, "field": field,
                             "why": "a finding carries a location, a claim, a scenario and an "
                                    "evidence kind; %s is missing" % field})
    kind = row.get("evidence_kind")
    if kind is not None and kind not in EVIDENCE_KINDS:
        problems.append({"index": index, "field": "evidence_kind",
                         "why": "the evidence kind %r is not one of %s"
                                % (kind, ", ".join(EVIDENCE_KINDS))})
    if row.get("location") is not None:
        path, line = parse_location(row.get("location"))
        if path is None:
            problems.append({"index": index, "field": "location",
                             "why": "the location %r does not name a file and a line"
                                    % row.get("location")})
    severity = row.get("severity")
    if severity not in ("BLOCKER", "MAJOR", "MINOR"):
        problems.append({"index": index, "field": "severity",
                         "why": "the severity %r is not BLOCKER, MAJOR or MINOR" % severity})
    return problems


def checks_listed(a):
    """The executed checks that carry a name and a non-empty output."""
    rows = a.get("checks_executed")
    if not isinstance(rows, list):
        return []
    return [row for row in rows
            if isinstance(row, dict) and str(row.get("name") or "").strip()
            and str(row.get("output") or "").strip()]


def _refusal(reason, problems, a, listed):
    return {"ok": False, "refusal_reason": reason, "problems": problems,
            "raised": [], "notes": [], "verdict": None,
            "verdict_stated": a.get("verdict"), "verdict_matches_mapping": None,
            "checks_executed": [dict(row) for row in (a.get("checks_executed") or [])
                                if isinstance(row, dict)],
            "clean_review_checks_listed": bool(listed),
            "session_id": a.get("session_id"), "citations": []}


def adjudicate(a, source_paths, sessions, withheld_lines=()):
    """What the run records from one reviewer answer. Never edits the answer."""
    source_paths = set(source_paths or ())
    withheld_lines = tuple(withheld_lines or ())
    listed = checks_listed(a)
    findings = a.get("findings")
    findings = list(findings) if isinstance(findings, list) else []
    kept = a.get("notes_kept")
    kept = list(kept) if isinstance(kept, list) else []

    building = (sessions or {}).get("building")
    reviewing = (sessions or {}).get("reviewing")
    session_id = a.get("session_id")
    if building is not None and (reviewing == building or session_id == building):
        why = ("the reviewing session is the session that built the slice (%s); the context that "
               "wrote the code never grades it" % building)
        return _refusal("independence", [{"why": why}], a, listed)

    cited = []
    for index, row in enumerate(findings):
        if isinstance(row, dict):
            for line in citations(row, withheld_lines):
                cited.append({"index": index, "line": line,
                              "why": "the finding quotes the builder's own account of its work, "
                                     "which is a claim and never evidence"})
    for line in citations({"notes": a.get("notes"), "verdict": a.get("verdict")}, withheld_lines):
        cited.append({"line": line,
                      "why": "the verdict quotes the builder's own account of its work"})
    if cited:
        out = _refusal("independence", cited, a, listed)
        out["citations"] = [row["line"] for row in cited]
        return out

    problems = []
    for index, row in enumerate(findings):
        problems.extend(check_finding(row, index, source_paths, withheld_lines))
    if problems:
        return _refusal("answer_invalid", problems, a, listed)

    if not findings and not listed:
        why = ("a review with no findings carries the checks it executed, each with its output; "
               "an empty list is not a clean verdict")
        return _refusal("answer_invalid", [{"why": why}], a, listed)

    raised, notes = [], []
    for row in findings:
        path, line = parse_location(row["location"])
        entry = {"location": row["location"], "file": path, "line": line,
                 "severity": row["severity"], "claim": row["claim"],
                 "scenario": row["scenario"], "evidence_kind": row["evidence_kind"]}
        if path in source_paths:
            raised.append(entry)
        else:
            entry = dict(entry, why="the location is outside the source set")
            notes.append(entry)
    for row in kept:
        if not isinstance(row, dict):
            continue
        path, line = parse_location(row.get("location"))
        notes.append({"location": row.get("location"), "file": path, "line": line,
                      "severity": row.get("severity"), "claim": row.get("claim"),
                      "scenario": row.get("scenario"), "evidence_kind": row.get("evidence_kind"),
                      "why": "the reviewer kept it as a note"})

    computed = vdmod.verdict_for([row["severity"] for row in raised])
    stated = a.get("verdict")
    return {
        "ok": True,
        "refusal_reason": None,
        "problems": [],
        "raised": raised,
        "notes": notes,
        "verdict": computed,
        "verdict_stated": stated,
        "verdict_matches_mapping": (_normalize(stated) == _normalize(computed)),
        "checks_executed": [dict(row) for row in (a.get("checks_executed") or [])
                            if isinstance(row, dict)],
        "clean_review_checks_listed": bool(listed),
        "session_id": session_id,
        "citations": [],
    }
