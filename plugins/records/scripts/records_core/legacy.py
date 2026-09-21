# Origin (records E12 contract, ruling E12-2): everything from the docstring below down to the
# banner "the tolerant reader" is a copy of the qualified recheck pilot's
# plugins/recheck-v2/skills/recheck-v2/scripts/recheck_core/ledger.py, taken from `main` at
# commit fc3945adfbbd793c5782c5be130a07aceadb1982, unchanged from that revision. The tolerant
# reader of contract section 11.3 is appended below it and is this component's own; it calls the
# copy's helpers and never changes one. A divergence in the copied part is a change to this
# component, never to the pilot, which E12 leaves byte-identical. The parity suite
# (tests/test_parity.py) holds the copy to the pilot's behaviour on every E7 fixture.
"""The record grammar of pilot contract Appendix A: parse, open filter, home, cards, render, apply.

Byte compatibility with the E7 library's writers (evals/fixtures/_lib/fixturelib.py) is the
rule of this module (E8-28): SEP is " · "; an appended block is one blank line, the heading,
its lines; a standalone WAIVED / REOPENED line lands directly after the ledger home's last
line; a status step replaces the text after "Status: " and nothing else; files end with one
newline. `apply_step(content, step)` produces the exact bytes the receipt plan hashes.

What is a record (E8-20): a bullet line in an Appendix A shape under a heading
`### <YYYY-MM-DD> — review: …` or `### <YYYY-MM-DD> — recheck: …` (wherever it sits), or a
`WAIVED (per user)` / `REOPENED (per user)` line anywhere. Lines inside fenced code blocks are
quoted text, never records (W3-03's fenced example); a grant-shaped line inside a fence is
reported as a grant claim. Records are ordered by file position, later wins; dates are
informational for the open filter (E8-1). A legacy tag glued to the location (`file:line (tag)`)
is not part of the join key (E8-22); `()` in a recheck line's claim field means no claim.
"""
import os
import re

SEP = " · "
SEVERITIES = ("BLOCKER", "MAJOR", "MINOR")
DISPOSITIONS = ("fixed", "not fixed")
WAIVED = "WAIVED (per user)"
REOPENED = "REOPENED (per user)"
CARD_VALUES = ("not started", "built", "rejected", "signed off with conditions", "signed off", "none")
MOVABLE_CARDS = ("not started", "rejected", "signed off with conditions", "signed off")  # E8-A8: not started moves like any other
NO_CLAIM = "()"  # the sentinel the checklist carries for a legacy entry without a claim (E8-22)
PUNCH_LIST_DOC = "docs/punch-list.md"
PUNCH_LIST_LABEL = "punch list"  # the heading label rendered for entries whose slice is none

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RECORD_HEADING_RE = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})\s+[—–-]+\s+(review|recheck):\s*(.*?)\s*$")
SLICE_HEADING_RE = re.compile(r"^##\s+Slice\s+(.+?)(?:\s+[—–-]+\s*(.*?))?\s*$")
LOCATION_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+)(?:\s*\((?P<tag>[^()]*)\))?$")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
BROKE_RE = re.compile(r"^broke:\s*(.*?)\s+[—–-]+\s+(.*)$")


# ---- parsing ---------------------------------------------------------------------------------

def parse_location(text):
    m = LOCATION_RE.match(text.strip())
    if not m:
        return None
    return {"file": m.group("file"), "line": int(m.group("line")), "tag": m.group("tag")}


def strip_parens(field):
    """Parentheses wrapping the whole claim field are not part of the claim; `()` is no claim."""
    f = field.strip()
    if f == NO_CLAIM:
        return None
    if len(f) >= 2 and f.startswith("(") and f.endswith(")"):
        return f[1:-1]
    return f


def heading_slices(rest):
    """`Slice A, Slice B` -> ["A", "B"]; `punch list` -> ["none"]; bare names pass through."""
    out = []
    for part in rest.split(","):
        p = part.strip()
        if not p:
            continue
        if p.lower() == PUNCH_LIST_LABEL:
            out.append("none")
            continue
        if p.lower().startswith("slice "):
            p = p[6:].strip()
        out.append(p)
    return out


def _record(kind, line_no, text, heading, **fields):
    rec = {"kind": kind, "line_no": line_no, "text": text, "heading": heading}
    rec.update(fields)
    return rec


def _ambiguous(line_no, text, heading, reason):
    return _record("ambiguous", line_no, text, heading, reason=reason)


def _grant_record(fields, line_no, text, heading):
    n = len(fields)
    if fields[0] == WAIVED:
        if n not in (5, 6):
            return _ambiguous(line_no, text, heading, "waiver line has %d fields; the waiver shape has 6 (5 in the legacy form)" % n)
        if not DATE_RE.match(fields[1].strip()):
            return _ambiguous(line_no, text, heading, "waiver line without its date (second field %r)" % fields[1])
        if fields[2] not in SEVERITIES:
            return _ambiguous(line_no, text, heading, "waiver line's severity field is %r" % fields[2])
        loc = parse_location(fields[3])
        if loc is None:
            return _ambiguous(line_no, text, heading, "waiver line's location field is %r" % fields[3])
        claim = strip_parens(fields[4])  # E8-A28: one claim normalization for every shape
        if claim is not None and "·" in claim:
            return _ambiguous(line_no, text, heading, "claim contains the separator character")
        words = _unquote(fields[5]) if n == 6 else None
        return _record("waiver", line_no, text, heading, date=fields[1].strip(), severity=fields[2],
                       file=loc["file"], line=loc["line"], tag=loc["tag"], claim=claim, words=words)
    if n not in (4, 5):
        return _ambiguous(line_no, text, heading, "reopening line has %d fields; the reopening shape has 5 (4 in the legacy form)" % n)
    if not DATE_RE.match(fields[1].strip()):
        return _ambiguous(line_no, text, heading, "reopening line without its date (second field %r)" % fields[1])
    loc = parse_location(fields[2])
    if loc is None:
        return _ambiguous(line_no, text, heading, "reopening line's location field is %r" % fields[2])
    claim = strip_parens(fields[3])  # E8-A28
    if claim is not None and "·" in claim:
        return _ambiguous(line_no, text, heading, "claim contains the separator character")
    words = _unquote(fields[4]) if n == 5 else None
    return _record("reopening", line_no, text, heading, date=fields[1].strip(), severity=None,
                   file=loc["file"], line=loc["line"], tag=loc["tag"], claim=claim, words=words)


def _unquote(field):
    f = field.strip()
    if len(f) >= 2 and f[0] == '"' and f[-1] == '"':
        return f[1:-1]
    return f


def _block_record(fields, line_no, text, heading):
    n = len(fields)
    if fields[0] not in SEVERITIES:
        return _ambiguous(line_no, text, heading, "first field %r is neither a severity nor a grant keyword" % fields[0])
    loc = parse_location(fields[1])
    if loc is None:
        return _ambiguous(line_no, text, heading, "second field %r is not a file:line location" % fields[1])
    base = dict(severity=fields[0], file=loc["file"], line=loc["line"], tag=loc["tag"])
    kind = heading["kind"]
    # a recheck line: `(<claim>) · fixed | not fixed · <how>` (under either heading kind)
    if n == 5 and fields[3].strip() in DISPOSITIONS and fields[2].strip().startswith("(") and fields[2].strip().endswith(")"):
        claim = strip_parens(fields[2])
        if claim is not None and "·" in claim:
            return _ambiguous(line_no, text, heading, "claim contains the separator character")
        return _record("recheck", line_no, text, heading, claim=claim, disposition=fields[3].strip(), how=fields[4], **base)
    if n in (3, 4) and fields[2].startswith("broke:"):
        m = BROKE_RE.match(fields[2])
        if not m:
            return _ambiguous(line_no, text, heading, "fix-introduced defect line lacks `broke: <claim> — <scenario>`")
        # E8-A25: under a heading naming more than one slice the fourth field names the slice charged;
        # under a single-slice heading the line keeps its three fields (the heading's slice is the charge)
        multi = len(heading.get("slices") or []) > 1
        if multi and n == 3:
            return _ambiguous(line_no, text, heading, "fix-introduced defect line under a multi-slice heading lacks its slice field")
        if not multi and n == 4:
            return _ambiguous(line_no, text, heading, "field count 4 matches no Appendix A shape under a single-slice heading (a fix-introduced defect line names its slice only under a heading naming more than one slice)")
        slice_field = None
        if n == 4:
            named = heading_slices(fields[3])
            if len(named) != 1:
                return _ambiguous(line_no, text, heading, "fix-introduced defect line's slice field %r names no single slice" % fields[3])
            slice_field = named[0]
        return _record("defect", line_no, text, heading, claim=m.group(1), scenario=m.group(2), slice=slice_field, **base)
    if kind == "review":
        if n == 5:
            claim = strip_parens(fields[2])  # E8-A28
            if claim is not None and "·" in claim:
                return _ambiguous(line_no, text, heading, "claim contains the separator character")
            return _record("finding", line_no, text, heading, claim=claim, scenario=fields[3], found_by=fields[4], **base)
        if n == 4:
            return _record("finding", line_no, text, heading, claim=None, scenario=fields[2], found_by=fields[3], **base)
        return _ambiguous(line_no, text, heading, "field count %d matches no Appendix A shape under a review heading" % n)
    if n == 5:
        return _ambiguous(line_no, text, heading, "fourth field %r is not a disposition (fixed | not fixed)" % fields[3].strip())
    return _ambiguous(line_no, text, heading, "field count %d matches no Appendix A shape under a recheck heading" % n)


def parse_document(text, document=None):
    """Parse one document. Returns a dict:

    lines: the text split on "\\n" (the trailing "" kept when the file ends with a newline)
    sections: [{title, start, end}] level-2 sections (start = heading index, end = next ## or len)
    slices: [{name, title, heading_line, status_line, status}]
    blocks: [{line_no, date, kind, slices, text, section}] every dated record heading
    records: every record in file order (kind finding | recheck | defect | waiver | reopening | ambiguous)
    ambiguities: the ambiguous records (missing input, Appendix A)
    claims: grant-shaped lines that are not records (inside a fence): reported, never obeyed
    document: the workspace-relative path when given
    """
    lines = text.split("\n")
    sections, slices, blocks, records, claims = [], [], [], [], []
    is_punch = document is not None and os.path.normpath(document) == PUNCH_LIST_DOC
    in_fence, fence_marker = False, None
    heading = None  # the governing record heading, or None
    for i, line in enumerate(lines):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker[0]
            elif marker[0] == fence_marker:
                in_fence, fence_marker = False, None
            continue
        if in_fence:
            stripped = line.strip()
            if stripped.startswith("- ") and SEP in stripped:
                f = stripped[2:].split(SEP)
                if f[0] in (WAIVED, REOPENED):
                    claims.append({"line_no": i + 1, "text": line, "reason": "inside a fenced code block"})
            continue
        if line.startswith("## ") or line.rstrip() == "##":
            if sections:
                sections[-1]["end"] = i
            sections.append({"title": line[3:].strip(), "start": i, "end": len(lines)})
            heading = None
            sm = SLICE_HEADING_RE.match(line.rstrip())
            if sm:
                slices.append({"name": sm.group(1).strip(), "title": (sm.group(2) or "").strip(),
                               "heading_line": i, "status_line": None, "status": None})
            continue
        if line.startswith("#"):
            rm = RECORD_HEADING_RE.match(line.rstrip())
            if rm:
                heading = {"line_no": i + 1, "date": rm.group(1), "kind": rm.group(2),
                           "slices": ["none"] if is_punch else heading_slices(rm.group(3)),
                           "text": line.rstrip(), "section": len(sections) - 1}
                blocks.append(heading)
            else:
                heading = None
            continue
        if slices and slices[-1]["status_line"] is None and line.startswith("Status:") \
                and (not sections or sections[-1]["start"] == slices[-1]["heading_line"]):
            slices[-1]["status_line"] = i
            slices[-1]["status"] = line[len("Status:"):].strip()
            continue
        stripped = line.rstrip()
        if not stripped.startswith("- ") or SEP not in stripped:
            continue
        fields = stripped[2:].split(SEP)
        if fields[0] in (WAIVED, REOPENED):
            records.append(_grant_record(fields, i + 1, stripped, heading))
            continue
        if heading is None:
            continue
        records.append(_block_record(fields, i + 1, stripped, heading))
    # two review findings with the same location and claim in one block are ambiguous
    seen = {}
    for rec in records:
        if rec["kind"] != "finding":
            continue
        key = (rec["heading"]["line_no"], rec["file"], rec["line"], rec["claim"])
        seen.setdefault(key, []).append(rec)
    for key, group in seen.items():
        if len(group) > 1:
            for rec in group:
                rec["kind"] = "ambiguous"
                rec["reason"] = "two review findings with the same location and claim in one block (lines %s)" % ", ".join(str(r["line_no"]) for r in group)
    for s in slices:
        if s["status"] is not None and s["status"] not in CARD_VALUES:
            s["card"] = "none"
        else:
            s["card"] = s["status"] if s["status"] is not None else "none"
    return {"lines": lines, "sections": sections, "slices": slices, "blocks": blocks, "records": records,
            "ambiguities": [r for r in records if r["kind"] == "ambiguous"], "claims": claims, "document": document}


# ---- entries and the open filter -------------------------------------------------------------

def entry_slice(rec, document=None):
    if document is not None and os.path.normpath(document) == PUNCH_LIST_DOC:
        return "none"
    h = rec.get("heading")
    if not h or not h.get("slices"):
        return "none"
    if rec.get("kind") == "defect" and rec.get("slice") is not None and len(h["slices"]) > 1:
        return rec["slice"]  # E8-A25: the fourth field is the charge under a multi-slice heading
    return h["slices"][0]


def open_set(parsed):
    """Build the entries and their state by walking the records in file order (Appendix A).

    Returns {"entries": [entry], "ambiguities": [record]}. An entry:
    {file, line, claim (None for a legacy claim-less entry), severity, scenario, slice, document,
     heading, date, state (open | fixed | waived), last (the record that decided it), origin}.
    Records that match no entry become entries of their own when they carry a severity.
    """
    entries, ambiguities = [], list(parsed["ambiguities"])
    document = parsed.get("document")

    def at_location(f, l):
        return [e for e in entries if e["file"] == f and e["line"] == l]

    def matches(rec):
        same_loc = at_location(rec["file"], rec["line"])
        exact = [e for e in same_loc if e["claim"] is not None and rec.get("claim") is not None and e["claim"] == rec["claim"]]
        if exact:
            return exact
        if rec.get("claim") is None or any(e["claim"] is None for e in same_loc):
            if len(same_loc) == 1:
                return same_loc
            return []
        return []

    for rec in parsed["records"]:
        kind = rec["kind"]
        if kind == "ambiguous":
            continue
        if kind in ("finding", "defect"):
            entries.append({"file": rec["file"], "line": rec["line"], "claim": rec["claim"], "severity": rec["severity"],
                            "scenario": rec.get("scenario"), "slice": entry_slice(rec, document), "document": document,
                            "heading": rec["heading"]["text"], "date": rec["heading"]["date"], "state": "open",
                            "last": rec, "origin": rec, "history": [rec]})
            continue
        found = matches(rec)
        if not found:
            if rec.get("severity"):
                entries.append({"file": rec["file"], "line": rec["line"], "claim": rec.get("claim"), "severity": rec["severity"],
                                "scenario": None, "slice": entry_slice(rec, document), "document": document,
                                "heading": rec["heading"]["text"] if rec.get("heading") else None,
                                "date": rec["heading"]["date"] if rec.get("heading") else rec.get("date"),
                                "state": "open", "last": rec, "origin": rec, "history": [rec]})
                found = [entries[-1]]
            else:
                continue
        for e in found:
            e["history"].append(rec)
            e["last"] = rec
            if kind == "recheck":
                e["state"] = "fixed" if rec["disposition"] == "fixed" else "open"
            elif kind == "waiver":
                e["state"] = "waived"
            elif kind == "reopening":
                e["state"] = "open"
    # a claim-less entry at a location several entries hold decides nothing (Appendix A)
    for e in entries:
        if e["claim"] is None and len(at_location(e["file"], e["line"])) > 1 and e["origin"]["kind"] == "finding":
            rec = dict(e["origin"])
            rec["kind"] = "ambiguous"
            rec["reason"] = "a claim-less finding at a location several entries share (%s:%d)" % (e["file"], e["line"])
            ambiguities.append(rec)
    ambiguities.sort(key=lambda r: r["line_no"])
    return {"entries": entries, "ambiguities": ambiguities}


def find_entries(entries, file, line, claim):
    """Resolve a (location, claim) reference against the whole record (legacy rules). The reference's
    claim is normalized like every record's (E8-A28: outer parentheses are not part of the claim)."""
    if isinstance(claim, str):
        claim = strip_parens(claim)
    same = [e for e in entries if e["file"] == file and e["line"] == line]
    exact = [e for e in same if e["claim"] == claim]
    if exact:
        return exact
    if claim in (None, NO_CLAIM) or any(e["claim"] is None for e in same):
        return same if len(same) == 1 else []
    return []


def entry_claim_field(entry):
    return NO_CLAIM if entry["claim"] is None else entry["claim"]


# ---- cards ---------------------------------------------------------------------------------

def card_after(before, open_entries):
    """Appendix A's status card mapping over everything still open for the slice."""
    if before not in MOVABLE_CARDS:
        return before
    sevs = set(e["severity"] for e in open_entries if e.get("severity"))
    if "BLOCKER" in sevs:
        return "rejected"
    if "MAJOR" in sevs:
        return "signed off with conditions"
    return "signed off"


def slice_card(parsed, name):
    for s in parsed["slices"]:
        if s["name"] == name:
            return s["card"]
    return "none"


def slice_names(parsed):
    return [s["name"] for s in parsed["slices"]]


def canonical_slice(given, names):
    """The document's own spelling of a slice a caller named (E11-7 item 3).

    A slice's name is what follows `## Slice ` in its heading: the heading `## Slice A —
    export` names the slice `A`. A session reading that heading naturally passes the words
    it saw, `Slice A`, and seven runs of the E10 campaign did exactly that: the core keyed
    them as `missing_input`, wrote that envelope into the pinned run directory, and then
    refused the corrected start as a reused run id (Astra's E11 read: "The seven
    `missing_input` results all name `target.slice`").

    Returns `(name or None, why)`. The document's own spelling always wins; a caller's
    spelling is accepted only when it resolves to exactly one slice.
    """
    if given is None:
        return None, "no slice was named"
    given = str(given)
    if given in names:
        return given, "the document's own spelling"

    def key(text):
        text = " ".join(str(text).split()).strip().lower()
        if text.startswith("slice "):
            text = text[len("slice "):].strip()
        return text.rstrip(":").strip()

    wanted = key(given)
    if not wanted:
        return None, "the slice named is empty once its heading words are removed"
    matches = [n for n in names if key(n) == wanted]
    if len(matches) == 1:
        return matches[0], "the heading's words %r resolve to the slice %r" % (given,
                                                                               matches[0])
    if len(matches) > 1:
        return None, "%r matches more than one slice (%s)" % (given, ", ".join(matches))
    return None, "%r matches no slice heading" % given


def sort_slices(names):
    """Ascending slice order: single letters first (A, B, ...), then the rest lexically."""
    return sorted(set(names), key=lambda n: (0 if len(n) == 1 else 1, n))


# ---- the ledger home and appends (byte-compatible with fixturelib._ledger_append) --------------

def _section_of_line(parsed, line_no):
    """The index of the level-2 section holding a 1-based line number, or -1 before any section."""
    idx = -1
    for i, sec in enumerate(parsed["sections"]):
        if sec["start"] < line_no:
            idx = i
    return idx


def _place(parsed, idx):
    lines = parsed["lines"]
    if idx >= 0:
        sec = parsed["sections"][idx]
        return sec["start"], sec["end"]
    return 0, parsed["sections"][0]["start"] if parsed["sections"] else len(lines)


def ledger_home(parsed):
    """The home section: (start, end, create). start is the index of the section's `## ` line
    (or 0 when the home is the document top), end the index of the next `## ` line or len(lines);
    create is True when no `## Punch list` section exists and no record does either.

    Appendix A as amended by E8-A13 (the home under file order, E8-1): where the document's
    records already live; when records sit in more than one place, the place whose tail comes
    last in the file, so that a record the run appends is the last record in file order and never
    dead under the open filter; the `## Punch list` section when no record exists yet."""
    places = {}
    for b in parsed["blocks"]:
        places[b["section"]] = _place(parsed, b["section"])
    for rec in parsed["records"]:
        if rec["kind"] in ("waiver", "reopening"):
            idx = _section_of_line(parsed, rec["line_no"])
            places[idx] = _place(parsed, idx)
    if places:
        start, end = max(places.values(), key=lambda p: (p[1], p[0]))
        return start, end, False
    for sec in parsed["sections"]:
        if sec["title"].rstrip() == "Punch list":
            return sec["start"], sec["end"], False
    return None, None, True


def append_at_home(content, text, document=None):
    """Append text at the ledger home's tail, producing fixturelib._ledger_append's bytes."""
    if not text.endswith("\n"):
        text += "\n"
    parsed = parse_document(content, document)
    start, end, create = ledger_home(parsed)
    lines = list(parsed["lines"])
    if lines and lines[-1] == "":
        lines.pop()
    if create:
        while lines and lines[-1].strip() == "":
            lines.pop()
        return "\n".join(lines) + "\n" + "\n## Punch list\n" + text
    nxt = end if end < len(parsed["lines"]) else None
    if nxt is None or nxt >= len(lines):
        while lines and lines[-1].strip() == "":
            lines.pop()
        return "\n".join(lines) + "\n" + text
    k = nxt
    while k > 0 and lines[k - 1].strip() == "":
        k -= 1
    head = "\n".join(lines[:k]) + "\n"
    tail = "\n".join(lines[nxt:]) + "\n"
    return head + text + "\n" + tail


def set_status_text(content, slice_name, value):
    """Replace the text after `Status: ` on the slice's status line and nothing else."""
    parsed = parse_document(content)
    for s in parsed["slices"]:
        if s["name"] == slice_name:
            if s["status_line"] is None:
                raise ValueError("no Status: line for slice %r" % slice_name)
            lines = list(parsed["lines"])
            lines[s["status_line"]] = "Status: %s" % value
            out = "\n".join(lines)
            if not out.endswith("\n"):
                out += "\n"
            return out
    raise ValueError("no heading for slice %r" % slice_name)


def apply_step(content, step):
    """The bytes of the target after one plan step (E8-28); content and result are str."""
    if step["kind"] == "status_line":
        return set_status_text(content, step["slice"], step["value"])
    return append_at_home(content, step["content"], step.get("target"))


# ---- renderers (byte-compatible with fixturelib's writers) -----------------------------------

def _single_line(text):
    """No line break and no separator inside a rendered field (Appendix A)."""
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return text.replace(SEP, " - ").replace("·", "-")


def render_location(file, line):
    return "%s:%s" % (file, line)


def render_how(verification):
    """`<how verified>` from the item's verification: the method, the first evidence, the block
    or missing text, the post-fix location. A stored detail that already begins with the method
    word (the E7 seeds) is not prefixed twice."""
    method = verification.get("method")
    label = "executed" if method == "executed" else "static (%s)" % verification.get("static_reason", "")
    evidence = verification.get("evidence") or []
    detail = evidence[0]["detail"] if evidence else ""
    if detail.startswith("executed ") or detail.startswith("static "):
        how = detail
    else:
        how = (label + " " + detail).strip()
    if verification.get("blocked"):
        how += "; blocked: " + verification["blocked"]
    if verification.get("missing"):
        how += "; missing: " + verification["missing"]
    loc = verification.get("location_after_fix")
    if loc:
        how += "; now at %s:%s" % (loc["file"], loc["line"])
    return _single_line(how)


def render_recheck_line(severity, file, line, claim, disposition_text, how):
    field = NO_CLAIM if claim in (None, NO_CLAIM) else "(%s)" % claim
    return "- " + SEP.join([severity, render_location(file, line), field, disposition_text, _single_line(how)])


def defect_slice_field(heading_slices, charged_to_slice):
    """E8-A25: the slice a rendered defect line names, only when the block heading names more than
    one slice; None otherwise (the heading's slice is the charge and the line keeps three fields)."""
    return charged_to_slice if len(set(heading_slices)) > 1 else None


def render_defect_line(severity, file, line, claim, scenario, slice=None):
    fields = [severity, render_location(file, line), "broke: %s — %s" % (_single_line(claim), _single_line(scenario))]
    if slice is not None:
        fields.append(PUNCH_LIST_LABEL if slice == "none" else _single_line(str(slice)))
    return "- " + SEP.join(fields)


def render_heading(date, slices):
    labels = []
    for s in sort_slices(slices):
        labels.append(PUNCH_LIST_LABEL if s == "none" else "Slice %s" % s)
    return "### %s — recheck: %s" % (date, ", ".join(labels))


def render_block(date, slices, lines):
    """One blank line, the heading, the lines, one trailing newline (fixturelib.recheck_block)."""
    return "\n" + render_heading(date, slices) + "\n" + "\n".join(lines) + "\n"


def ledger_words(words):
    """The ledger form of a grant's quoted words (Appendix A, E8-A16): one line, a double quote
    written as a single quote; the form the waived / reopened markers carry."""
    return _single_line(words).replace('"', "'")


def quoted(words):
    return '"%s"' % words.replace('"', "'")


def render_waiver(date, severity, file, line, claim, words):
    fields = [WAIVED, date, severity, render_location(file, line), _single_line(claim), quoted(_single_line(words))]
    return "- " + SEP.join(fields) + "\n"


def render_reopen(date, file, line, claim, words):
    fields = [REOPENED, date, render_location(file, line), _single_line(claim), quoted(_single_line(words))]
    return "- " + SEP.join(fields) + "\n"


# ---- verdict doc glob (Appendix A) -----------------------------------------------------------

def feature_of(build_doc):
    base = os.path.basename(build_doc)
    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)\.md$", base)
    if m:
        return m.group(1)
    if base.endswith("-build-plan.md"):
        return base[:-len("-build-plan.md")]
    return base[:-3] if base.endswith(".md") else base


def verdict_doc_glob(workspace, build_doc, slice_name):
    """The paths matching docs/reviews/*-signoff-<feature>-<slice>.md, sorted, workspace-relative."""
    feature = feature_of(build_doc)
    tail = "-signoff-%s-%s.md" % (feature, slice_name.lower().replace(" ", "-"))
    folder = os.path.join(workspace, "docs", "reviews")
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join("docs", "reviews", n) for n in os.listdir(folder) if n.endswith(tail))


# =================================================================================================
# The tolerant reader (records E12 contract section 11.3). Everything above this banner is the
# pilot's ledger.py byte for byte; everything below is this component's own.
# =================================================================================================
#
# The tolerant reader accepts everything the strict reader accepts, with the same result, and in
# addition the shape families section 11.1 measured in the owner's repositories:
#
#   L1  a location wrapped in backticks
#   L2  a line range, `file:N-N` (hyphen or en dash)
#   L6  a parenthetical tag glued after either of those
#   L4  several locations in one field, separated by `,`, `;`, ` and `, or ` + `; the first
#       becomes the location and the rest `more`, and a bare `:N` in `more` inherits the first
#       location's file
#   L3, L5  a field naming no `file:line` at all, kept as `raw` with `resolved: false`
#   F1  a recheck line whose fourth field is `fixed`/`not fixed`, a dash, and the how-verified text
#   F2  a review finding with three fields, or with more than five
#   F3  a defect line in either legacy form, with or without the ` — <scenario>` half
#
# A line under a record heading that still fits nothing, or whose first field is not a severity
# (S1), becomes an `unparsed` item carrying its raw text and a reason. It bears no state and
# blocks nothing. The fence rule (E8-20), the heading rule, and the slice rule are the strict
# reader's, replayed here so one scan produces both the document's frame and the tolerant items;
# `tests/test_parity.py` holds that frame equal to the strict reader's on every fixture and on
# every document of this repository.
#
# One shape this repository holds that section 11.3 does not name: a `WAIVED (per user)` or
# `REOPENED (per user)` line written WITHOUT the leading `- ` bullet. All three structured grant
# lines under `docs/` are written that way, and contract section 13 requires the dry run of
# `docs/plans/2026-09-06-readers.md` to report its waiver line, so a grant line is read whether or
# not it carries the bullet. Nothing else is read without one. This is reported as a contract
# question in the slice 2 builder's report.
#
# The items this reader returns are NOT events. `importer.py` turns them into events; the join
# key of section 7 is computed from `location["raw"]` by `ids.location_key`, never from the
# `file` / `line` / `tag` this module parses out, which are information for a reader.

from . import ids

FIXED_HOW_RE = re.compile(r"^(?P<disposition>not fixed|fixed)\s*[—–-]\s*(?P<how>\S.*)$")
DEFECT_MARKER_RE = re.compile(r"^(?:broke|fix-introduced)\s*:?\s*(?P<rest>.*)$")
DEFECT_SPLIT_RE = re.compile(r"^(?P<claim>.*?)\s+[—–-]\s+(?P<scenario>.+)$")
LOCATION_SPLIT_RE = re.compile(r",|;|\s+and\s+|\s+\+\s+")
# one location: `<file>:<N>` or `<file>:<N>-<N>`, optionally followed by a glued parenthetical
ONE_LOCATION_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+)(?:\s*[-–]\s*(?P<end>\d+))?"
                             r"(?:\s*\((?P<tag>[^()]*)\))?$")
# a continuation inside a multi-location field: `:N`, `N`, `:N-N`, `N-N`, with an optional tag
BARE_LOCATION_RE = re.compile(r"^:?(?P<line>\d+)(?:\s*[-–]\s*(?P<end>\d+))?"
                              r"(?:\s*\((?P<tag>[^()]*)\))?$")
GRANT_KEYWORDS = (WAIVED, REOPENED)
UNRESOLVED = {"file": None, "line": None, "line_end": None, "tag": None}


def collapse(text):
    """Internal whitespace collapsed to single spaces, ends trimmed; case kept."""
    return " ".join(text.split()) if isinstance(text, str) else ""


def _one_location(text, inherited_file=None):
    """{file, line, line_end, tag} for one location, or None when the text names none."""
    body = collapse(text).strip()
    if not body:
        return None
    m = ONE_LOCATION_RE.match(body)
    if m is not None:
        return {"file": m.group("file").strip(), "line": int(m.group("line")),
                "line_end": int(m.group("end")) if m.group("end") else None,
                "tag": m.group("tag")}
    if inherited_file is not None:
        m = BARE_LOCATION_RE.match(body)
        if m is not None:
            return {"file": inherited_file, "line": int(m.group("line")),
                    "line_end": int(m.group("end")) if m.group("end") else None,
                    "tag": m.group("tag")}
    return None


def _location_parts(body):
    """The field's locations, in order. A field that is one tagged location is never split.

    The tag rule and the multi-location rule are the pair `ids.location_key` uses, so a field the
    key treats as one tagged location is parsed as one here too.
    """
    m = ids.TAGGED_LOCATION_RE.match(body)
    if m is not None and not ids.MULTI_LOCATION_RE.search(m.group("loc")):
        return [body]
    return [p for p in LOCATION_SPLIT_RE.split(body) if p.strip()]


def tolerant_location(field):
    """Section 6.2's location object, read tolerantly (families L1 to L6).

    `raw` is the field exactly as written, which is what section 7's key is computed from; the
    other keys are what this reader could make of it. `resolved` is false when the field names no
    `file:line` at all, and then `file`, `line` and `line_end` are null and `raw` is all there is.
    """
    raw = field.strip() if isinstance(field, str) else ""
    body = collapse(raw.replace("`", ""))
    parts = _location_parts(body)
    first = _one_location(parts[0]) if parts else None
    if first is None:
        out = {"raw": raw, "more": [], "resolved": False}
        out.update(UNRESOLVED)
        return out
    more = []
    for part in parts[1:]:
        item = _one_location(part, inherited_file=first["file"])
        if item is not None:
            more.append(item)
    return {"raw": raw, "file": first["file"], "line": first["line"],
            "line_end": first["line_end"], "tag": first["tag"], "more": more, "resolved": True}


def _item(kind, line_no, text, heading, **fields):
    item = {"kind": kind, "line_no": line_no, "text": text, "heading": heading,
            "severity": None, "location": None, "claim": None, "scenario": None,
            "raised_by": None, "disposition": None, "how": None, "slice": None,
            "date": None, "words": None, "reason": None}
    item.update(fields)
    return item


def _unparsed(line_no, text, heading, reason):
    return _item("unparsed", line_no, text, heading, reason=reason)


def _claim_field(field):
    """A claim field read the way every Appendix A shape reads one (E8-A28), or the separator stop.

    Returns (claim, reason): the reason is set only when the claim carries the separator
    character, which Appendix A calls ambiguous in every shape, and which the tolerant reader
    therefore refuses as well.
    """
    claim = strip_parens(field)
    if claim is not None and "·" in claim:
        return None, "claim contains the separator character"
    return claim, None


def _tolerant_grant(fields, line_no, text, heading):
    """A `WAIVED (per user)` or `REOPENED (per user)` line, with a tolerantly read location."""
    n = len(fields)
    waiver = fields[0] == WAIVED
    shape = (5, 6) if waiver else (4, 5)
    label = "waiver" if waiver else "reopening"
    if n not in shape:
        return _unparsed(line_no, text, heading,
                         "%s line has %d fields; the %s shape has %d (%d in the legacy form)"
                         % (label, n, label, shape[1], shape[0]))
    if not DATE_RE.match(fields[1].strip()):
        return _unparsed(line_no, text, heading,
                         "%s line without its date (second field %r)" % (label, fields[1]))
    if waiver and fields[2] not in SEVERITIES:
        return _unparsed(line_no, text, heading, "waiver line's severity field is %r" % fields[2])
    loc_field = fields[3] if waiver else fields[2]
    claim_index = 4 if waiver else 3
    claim, reason = _claim_field(fields[claim_index])
    if reason is not None:
        return _unparsed(line_no, text, heading, reason)
    words = _unquote(fields[claim_index + 1]) if n == shape[1] else None
    return _item("waiver" if waiver else "reopening", line_no, text, heading,
                 date=fields[1].strip(), severity=fields[2] if waiver else None,
                 location=tolerant_location(loc_field), claim=claim, words=words)


def _tolerant_defect(fields, line_no, text, heading, location):
    """A fix-introduced defect line in either legacy form (F3)."""
    n = len(fields)
    m = DEFECT_MARKER_RE.match(fields[2].strip())
    rest = m.group("rest").strip()
    split = DEFECT_SPLIT_RE.match(rest)
    if split is not None:
        claim, scenario = split.group("claim").strip(), split.group("scenario").strip()
    else:
        claim, scenario = rest, None  # F3: the defect line without its ` — <scenario>` half
    if not claim:
        return _unparsed(line_no, text, heading,
                         "fix-introduced defect line names nothing after its marker")
    multi = len(set(heading.get("slices") or [])) > 1
    charged, raised_by = None, None
    if n == 4 and multi:
        named = heading_slices(fields[3])  # E8-A25: the fourth field is the charge
        if len(named) != 1:
            return _unparsed(line_no, text, heading,
                             "fix-introduced defect line's slice field %r names no single slice"
                             % fields[3])
        charged = named[0]
    elif n == 4:
        # under a single-slice heading the heading's slice is the charge (E8-A25), so a fourth
        # field is an attribution, the field a review finding calls `raised_by`
        raised_by = fields[3].strip() or None
    return _item("defect", line_no, text, heading, severity=fields[0], location=location,
                 claim=claim, scenario=scenario, slice=charged, raised_by=raised_by)


def _tolerant_block_item(fields, line_no, text, heading):
    """One bullet line under a record heading, read tolerantly."""
    n = len(fields)
    if fields[0] not in SEVERITIES:
        return _unparsed(line_no, text, heading,
                         "first field %r is neither a severity nor a grant keyword" % fields[0])
    location = tolerant_location(fields[1])
    base = dict(severity=fields[0], location=location)
    kind = heading["kind"]
    fourth = fields[3].strip() if n >= 4 else ""
    # a recheck line, under either heading kind, exactly where the strict reader looks for one
    if n == 5 and fourth in DISPOSITIONS and fields[2].strip().startswith("(") \
            and fields[2].strip().endswith(")"):
        claim, reason = _claim_field(fields[2])
        if reason is not None:
            return _unparsed(line_no, text, heading, reason)
        return _item("recheck", line_no, text, heading, claim=claim, disposition=fourth,
                     how=fields[4], **base)
    if n == 4:
        fused = FIXED_HOW_RE.match(fourth)
        if fused is not None:  # F1: the disposition and the how-verified share one field
            claim, reason = _claim_field(fields[2])
            if reason is not None:
                return _unparsed(line_no, text, heading, reason)
            return _item("recheck", line_no, text, heading, claim=claim,
                         disposition=fused.group("disposition"), how=fused.group("how").strip(),
                         **base)
    if n in (3, 4) and DEFECT_MARKER_RE.match(fields[2].strip()):
        return _tolerant_defect(fields, line_no, text, heading, location)
    if kind == "review":
        if n == 5:
            claim, reason = _claim_field(fields[2])
            if reason is not None:
                return _unparsed(line_no, text, heading, reason)
            return _item("finding", line_no, text, heading, claim=claim, scenario=fields[3],
                         raised_by=fields[4], **base)
        if n == 4:  # the pilot's legacy claim-less shape
            return _item("finding", line_no, text, heading, claim=None, scenario=fields[2],
                         raised_by=fields[3], **base)
        if n == 3:  # F2: three fields, the third the scenario, no claim and no attribution
            return _item("finding", line_no, text, heading, claim=None, scenario=fields[2],
                         raised_by=None, **base)
        if n > 5:  # F2: the last field is raised_by; everything between joins the scenario
            claim, reason = _claim_field(fields[2])
            if reason is not None:
                return _unparsed(line_no, text, heading, reason)
            return _item("finding", line_no, text, heading, claim=claim,
                         scenario=SEP.join(fields[3:-1]), raised_by=fields[-1], **base)
        return _unparsed(line_no, text, heading,
                         "field count %d matches no shape under a review heading" % n)
    if n == 5:
        return _unparsed(line_no, text, heading,
                         "fourth field %r is neither a disposition nor `fixed`/`not fixed` "
                         "followed by a dash and the how-verified text" % fourth)
    return _unparsed(line_no, text, heading,
                     "field count %d matches no shape under a recheck heading" % n)


def tolerant_document(text, document=None):
    """Parse one document tolerantly. The frame is the strict reader's, the items are section 11.3's.

    Returns a dict:

    lines, sections, slices, blocks, claims, document: exactly what `parse_document` returns for
      the same text (held equal by the parity suite), so the document's frame has one reading.
    items: every line the reader classified, in file order. An item's `kind` is one of
      finding | recheck | defect | waiver | reopening | unparsed.
    """
    lines = text.split("\n")
    sections, slices, blocks, items, claims = [], [], [], [], []
    is_punch = document is not None and os.path.normpath(document) == PUNCH_LIST_DOC
    in_fence, fence_marker = False, None
    heading = None  # the governing record heading, or None
    for i, line in enumerate(lines):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker[0]
            elif marker[0] == fence_marker:
                in_fence, fence_marker = False, None
            continue
        if in_fence:
            stripped = line.strip()
            body = stripped[2:] if stripped.startswith("- ") else stripped
            if SEP in body and body.split(SEP)[0] in GRANT_KEYWORDS:
                claims.append({"line_no": i + 1, "text": line, "reason": "inside a fenced code block"})
            continue
        if line.startswith("## ") or line.rstrip() == "##":
            if sections:
                sections[-1]["end"] = i
            sections.append({"title": line[3:].strip(), "start": i, "end": len(lines)})
            heading = None
            sm = SLICE_HEADING_RE.match(line.rstrip())
            if sm:
                slices.append({"name": sm.group(1).strip(), "title": (sm.group(2) or "").strip(),
                               "heading_line": i, "status_line": None, "status": None})
            continue
        if line.startswith("#"):
            rm = RECORD_HEADING_RE.match(line.rstrip())
            if rm:
                heading = {"line_no": i + 1, "date": rm.group(1), "kind": rm.group(2),
                           "slices": ["none"] if is_punch else heading_slices(rm.group(3)),
                           "text": line.rstrip(), "section": len(sections) - 1}
                blocks.append(heading)
            else:
                heading = None
            continue
        if slices and slices[-1]["status_line"] is None and line.startswith("Status:") \
                and (not sections or sections[-1]["start"] == slices[-1]["heading_line"]):
            slices[-1]["status_line"] = i
            slices[-1]["status"] = line[len("Status:"):].strip()
            continue
        stripped = line.rstrip()
        body = stripped[2:] if stripped.startswith("- ") else stripped
        if SEP not in body:
            # Review finding 14: a bullet under a record heading that carries no field separator
            # fits no shape, so it is `legacy_unparsed` with its raw text (section 11.3) rather
            # than a line the reader drops on the floor. A bullet outside a record heading is
            # ordinary prose and is not a record at all.
            if heading is not None and stripped.startswith("- "):
                items.append(_unparsed(i + 1, stripped, heading,
                                       "a record bullet with no field separator"))
            continue
        fields = body.split(SEP)
        if fields[0] in GRANT_KEYWORDS:
            items.append(_tolerant_grant(fields, i + 1, stripped, heading))
            continue
        if not stripped.startswith("- "):
            continue  # only a grant line is read without its bullet
        if heading is None:
            continue
        items.append(_tolerant_block_item(fields, i + 1, stripped, heading))
    for s in slices:
        if s["status"] is not None and s["status"] not in CARD_VALUES:
            s["card"] = "none"
        else:
            s["card"] = s["status"] if s["status"] is not None else "none"
    return {"lines": lines, "sections": sections, "slices": slices, "blocks": blocks,
            "items": items, "claims": claims, "document": document}


def item_slice(item, document=None):
    """The slice an item is charged to, the strict reader's `entry_slice` rule (E8-A25)."""
    if document is not None and os.path.normpath(document) == PUNCH_LIST_DOC:
        return "none"
    h = item.get("heading")
    if not h or not h.get("slices"):
        return "none"
    if item.get("kind") == "defect" and item.get("slice") is not None and len(h["slices"]) > 1:
        return item["slice"]
    return h["slices"][0]
