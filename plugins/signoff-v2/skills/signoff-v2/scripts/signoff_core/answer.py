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

A clean review must list its checks: when no finding remains RAISED after the partition into
raised findings and notes, and no executed check carries a name and an output, the answer is
refused (`answer_invalid`) here, at `record-answer`, and no recording starts (Astra's F16: a review
whose only finding was demoted to a note is a clean review for this rule, not an exception to it).

**Builder-conversation provenance** (Astra's F4). The packet knows which files are the builder's
conversation and which ledger sections were withheld; `adjudicate` is handed that as
`provenance`. The WHOLE answer — prose, findings, notes kept, the verdict and every
`checks_executed` entry, command and output included — is refused (`independence`) when it
cites one of those paths (by its workspace path, or by its file name when no delivered file shares
it) or a withheld section, or quotes text whose only source is the withheld material (a quoted
span of 12 or more characters found in the withheld text and nowhere in the delivered packet).
The older rule, a withheld line of 24 or more characters repeated verbatim, stays beside these; it
never stood in for citation provenance.
"""
import os
import re

from . import verdict as vdmod
from .constants import EVIDENCE_KINDS

LOCATION = re.compile(r"^(?P<file>[^\s:][^:]*?):(?P<line>\d+)(?:-(?P<line_end>\d+))?"
                      r"(?:\s*\((?P<tag>[^)]*)\))?$")
REQUIRED = ("location", "claim", "scenario", "evidence_kind")
MIN_QUOTE = 24   # a withheld line shorter than this is not treated as a verbatim repetition
MIN_QUOTED_SPAN = 12   # a quoted span at least this long is checked for withheld-only provenance
QUOTED = re.compile(r'(?:(?<![\w])"([^"\n]+)"|(?<![\w])\'([^\'\n]+)\'(?![\w])|`([^`\n]+)`'
                    r'|\u201c([^\u201d\n]+)\u201d)')


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


def strings_of(value):
    """Every string value inside an answer, recursively, in a stable order. Keys are not text the
    reviewer wrote about the code, so only values are read."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out = []
        for key in sorted(value):
            out.extend(strings_of(value[key]))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(strings_of(item))
        return out
    return []


def _path_pattern(token):
    return re.compile(r"(?<![\w./-])" + re.escape(token) + r"(?![\w/-])", re.I)


def provenance_citations(a, provenance):
    """[{"why", "cited"}]: every place the answer cites or quotes the builder's conversation."""
    provenance = provenance or {}
    texts = strings_of(a)
    if not texts:
        return []
    joined = "\n".join(texts)
    hits = []
    delivered_names = set(os.path.basename(p).lower() for p in provenance.get("delivered_paths") or [])
    for path in provenance.get("paths") or []:
        tokens = [path]
        name = os.path.basename(path)
        if name.lower() not in delivered_names:
            tokens.append(name)
        for token in tokens:
            if _path_pattern(token).search(joined):
                hits.append({"cited": token,
                             "why": "the answer cites %s, the builder's own account of its work, "
                                    "which is a claim and never evidence" % path})
                break
    lowered = joined.lower()
    for anchor in provenance.get("anchors") or []:
        if anchor.lower() in lowered:
            hits.append({"cited": anchor,
                         "why": "the answer cites %s, a withheld section of the builder's working "
                                "record" % anchor})
    withheld = _normalize(provenance.get("withheld_text"))
    delivered = _normalize(provenance.get("delivered_text"))
    if withheld:
        for match in QUOTED.finditer(joined):
            span = next(group for group in match.groups() if group is not None)
            needle = _normalize(span)
            if len(needle) >= MIN_QUOTED_SPAN and needle in withheld and needle not in delivered:
                hits.append({"cited": span,
                             "why": "the answer quotes %r, which appears only in the builder's "
                                    "withheld conversation, never in the delivered packet" % span})
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


def adjudicate(a, source_paths, sessions, withheld_lines=(), provenance=None):
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
    # Astra's F4: the WHOLE answer, `checks_executed` and `notes_kept` included.
    rest = {"checks_executed": a.get("checks_executed"), "notes_kept": a.get("notes_kept")}
    for line in citations({"notes": " · ".join(strings_of(rest))}, withheld_lines):
        cited.append({"line": line,
                      "why": "the answer's checks or kept notes repeat the builder's own account "
                             "of its work"})
    for hit in provenance_citations(a, provenance):
        cited.append({"line": hit["cited"], "why": hit["why"]})
    if cited:
        out = _refusal("independence", cited, a, listed)
        out["citations"] = [row["line"] for row in cited]
        return out

    problems = []
    for index, row in enumerate(findings):
        problems.extend(check_finding(row, index, source_paths, withheld_lines))
    if problems:
        return _refusal("answer_invalid", problems, a, listed)

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

    # Astra's F16: the clean-review check runs over what REMAINS raised after the partition. A
    # review whose every finding became a note raises nothing, so it is a clean review and must
    # list the checks it executed, each with its output.
    if not raised and not listed:
        why = ("a review that raises no finding carries the checks it executed, each with its "
               "output; an empty list is not a clean verdict (%d finding(s) reported, none of them "
               "raised)" % len(findings))
        return _refusal("answer_invalid", [{"why": why}], a, listed)

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
