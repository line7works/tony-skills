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


# Astra's F3: a citation is resolved to its canonical workspace path BEFORE it is compared with
# the withheld provenance, so `./x`, an absolute path, a `file://` URL, percent encoding, `..`
# segments, a Markdown destination and a `#fragment` or `:line` suffix all land on the same path.
# Nothing is read to do it: the resolution is lexical, and a path outside the workspace resolves to
# nothing rather than to a file this module would open.
MD_DESTINATION = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'(][^)]*)?\)")
ANGLE = re.compile(r"<([^<>\s]+)>")
TOKEN = re.compile(r"[^\s`'\"()<>\[\]{},;|]+")
LINE_SUFFIX = re.compile(r"(?::\d+(?:-\d+)?(?::\d+)?)+$")
TRAILING = ".,;:!?"


def _decode(token):
    """Percent-decoding applied until it stops changing the token (at most three rounds)."""
    try:
        from urllib.parse import unquote
    except ImportError:  # pragma: no cover - Python 2 is not supported
        return token
    for _ in range(3):
        decoded = unquote(token)
        if decoded == token:
            break
        token = decoded
    return token


def canonical(token, workspace=None):
    """(workspace-relative path, fragment or None) for one citation token, or None.

    `file://` and `file:` URLs are reduced to their path; the token is percent-decoded; a query, a
    `#fragment` and a trailing `:line[:col]` or `:line-line` suffix are split off; an absolute path
    is taken relative to the workspace (its literal path or its real path) and dropped when it lies
    outside; `.` and `..` segments are normalised and a path that climbs out is dropped."""
    import posixpath
    if not isinstance(token, str):
        return None
    token = token.strip().rstrip(TRAILING)
    if not token:
        return None
    lowered = token.lower()
    if lowered.startswith("file://"):
        token = token[len("file://"):]
        if not token.startswith("/"):              # file://host/path: drop the host
            token = "/" + token.split("/", 1)[1] if "/" in token else ""
    elif lowered.startswith("file:"):
        token = token[len("file:"):]
    elif re.match(r"^[a-z][a-z0-9+.-]*://", lowered):
        return None                                # another scheme is never a workspace path
    token = _decode(token)
    fragment = None
    if "#" in token:
        token, fragment = token.split("#", 1)
    if "?" in token:
        token = token.split("?", 1)[0]
    token = LINE_SUFFIX.sub("", token).rstrip(TRAILING)
    if not token:
        return None
    if token.startswith("/"):
        rel = None
        if workspace:
            for base in (workspace, os.path.realpath(workspace)):
                base = base.rstrip("/")
                if token == base:
                    return None
                if token.startswith(base + "/"):
                    rel = token[len(base) + 1:]
                    break
        if rel is None:
            return None
        token = rel
    normal = posixpath.normpath(token)
    if normal in (".", "") or normal == ".." or normal.startswith("../"):
        return None
    return normal, (_decode(fragment) if fragment else None)


# punch-F3 (Astra's recheck): `[source](<./builder notes.md#proof>)` was recorded, because the
# destination pattern stopped at the space inside the angle brackets and never reached `canonical`.
# The tokens below follow CommonMark's own link grammar instead of one regular expression: an
# inline link or image destination, angle-bracketed (spaces allowed) or bare (balanced and
# backslash-escaped parentheses allowed), with its optional title; a link reference definition
# line; a `<...>` token with spaces; an HTML `href`/`src` attribute; a quoted span; a run of path
# characters with backslash-escaped characters in it (a shell's `builder\ notes.md`). Backslash
# escapes and HTML entities are undone the way CommonMark undoes them. A title's text is scanned
# again as text, so a citation inside a title is found too.
ESCAPABLE = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
REF_DEFINITION = re.compile(r"^[ ]{0,3}\[(?:[^\]\\]|\\.)+\]:[ \t]*(.*)$", re.M)
ANGLE_ANY = re.compile(r"<([^<>\n]+)>")
HTML_ATTR = re.compile(r"\b(?:href|src)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>\"']+))", re.I)
QUOTED_ANY = re.compile(r'"([^"\n]+)"|\'([^\'\n]+)\'|`([^`\n]+)`')
ESCAPED_RUN = re.compile(r"(?:\\.|[^\s`'\"()<>\[\]{},;|\\])+")


def _unescape(text):
    """CommonMark's backslash escapes and HTML entity references, undone."""
    import html
    out, index = [], 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text) and text[index + 1] in ESCAPABLE + " ":
            out.append(text[index + 1])
            index += 2
            continue
        out.append(char)
        index += 1
    return html.unescape("".join(out))


def _destination_at(text, index):
    """(destination, title, end) for the link destination starting at `index`, or None.

    CommonMark's rule: optional whitespace, then either `<...>` (no line ending, no unescaped `<`
    or `>`; spaces allowed) or a run of non-space characters in which parentheses balance or are
    backslash-escaped; then an optional title in `"..."`, `'...'` or `(...)`."""
    length = len(text)
    while index < length and text[index] in " \t\n":
        index += 1
    if index >= length:
        return None
    if text[index] == "<":
        end = index + 1
        while end < length and text[end] not in "<>\n":
            end += 2 if text[end] == "\\" else 1
        if end >= length or text[end] != ">":
            return None
        dest, index = text[index + 1:end], end + 1
    else:
        depth, end = 0, index
        while end < length:
            char = text[end]
            if char == "\\" and end + 1 < length:
                end += 2
                continue
            if char in " \t\n" or ord(char) < 32:
                break
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            end += 1
        dest, index = text[index:end], end
    while index < length and text[index] in " \t\n":
        index += 1
    title = None
    if index < length and text[index] in "\"'(":
        close = {'"': '"', "'": "'", "(": ")"}[text[index]]
        end = index + 1
        while end < length and text[end] != close:
            end += 2 if text[end] == "\\" else 1
        title = text[index + 1:min(end, length)]
        index = end + 1
    return dest, title, index


def citation_tokens(text, _depth=0):
    """Every token of `text` that could be a path citation (Astra's F3, punch-F3): link and image
    destinations and their titles, reference definitions, `<...>` tokens with or without spaces,
    HTML `href`/`src` values, quoted spans, backslash-escaped runs, and every run of path
    characters. Each is returned as written and, when escapes or entities change it, undone too."""
    if not isinstance(text, str) or not text:
        return []
    raw, titles = [], []
    index = text.find("](")
    while index != -1:
        got = _destination_at(text, index + 2)
        if got:
            raw.append(got[0])
            if got[1]:
                titles.append(got[1])
        index = text.find("](", index + 2)
    for match in REF_DEFINITION.finditer(text):
        got = _destination_at(match.group(1), 0)
        if got:
            raw.append(got[0])
            if got[1]:
                titles.append(got[1])
    raw.extend(match.group(1) for match in ANGLE_ANY.finditer(text))
    raw.extend(next(g for g in match.groups() if g is not None)
               for match in HTML_ATTR.finditer(text))
    raw.extend(next(g for g in match.groups() if g is not None)
               for match in QUOTED_ANY.finditer(text))
    raw.extend(ESCAPED_RUN.findall(text))
    raw.extend(TOKEN.findall(text))
    out = []
    for token in raw:
        out.append(token)
        undone = _unescape(token)
        if undone != token:
            out.append(undone)
    if _depth < 2:
        for title in titles:
            out.extend(citation_tokens(title, _depth + 1))
        undone = _unescape(text)
        if undone != text:
            out.extend(citation_tokens(undone, _depth + 1))
    return out


def spaced_mentions(text, provenance):
    """[(token, withheld path)] for every mention of a withheld path in plain text that the token
    rules cannot split out, because the path itself holds a space (punch-F3): `./builder notes.md:2`
    in prose, an absolute path with a space, `src/../builder notes.md`. Each occurrence of the
    withheld file's name, in the text as written and with percent encoding, backslash escapes and
    entities undone, is joined with the run of path characters right before it and right after it,
    and the whole is resolved with `canonical` like any other token."""
    provenance = provenance or {}
    workspace = provenance.get("workspace")
    hits = []
    variants = [text]
    for variant in (_decode(text), _unescape(text), _decode(_unescape(text))):
        if variant not in variants:
            variants.append(variant)
    for path in provenance.get("paths") or []:
        name = os.path.basename(path)
        if " " not in path or not name:
            continue
        pattern = re.compile(re.escape(name), re.I)
        for variant in variants:
            for match in pattern.finditer(variant):
                start, end = match.start(), match.end()
                while start > 0 and not variant[start - 1].isspace() \
                        and variant[start - 1] not in "`'\"()<>[]{},;|":
                    start -= 1
                while end < len(variant) and not variant[end].isspace() \
                        and variant[end] not in "`'\"()<>[]{},;|":
                    end += 1
                token = variant[start:end]
                got = canonical(token, workspace)
                if got and got[0].lower() == path.lower():
                    hits.append((token, path))
    return hits


def _slug(text):
    return " ".join(re.sub(r"[-_]+", " ", str(text or "")).lower().split())


def resolved_citations(texts, provenance):
    """[{"cited", "why"}] for every citation in `texts` that resolves to withheld material.

    A resolved path that equals a withheld builder-conversation path, or whose file name is a
    withheld file's name while no delivered file shares that name, is a citation of the builder's
    conversation; a resolved `<ledger doc>#<section>` whose section is a withheld section is a
    citation of the builder's working record. Case is ignored, as the file systems this runs on do.
    """
    provenance = provenance or {}
    workspace = provenance.get("workspace")
    withheld = dict((p.lower(), p) for p in provenance.get("paths") or [])
    delivered_names = set(os.path.basename(p).lower() for p in provenance.get("delivered_paths") or [])
    names = dict((os.path.basename(p).lower(), p) for p in provenance.get("paths") or []
                 if os.path.basename(p).lower() not in delivered_names)
    anchors = {}
    for anchor in provenance.get("anchors") or []:
        doc, _, section = anchor.partition("#")
        anchors.setdefault(doc.lower(), {})[_slug(section)] = anchor
    hits, seen = [], set()
    for text in texts:
        for token, target in spaced_mentions(text, provenance):
            if target not in seen:
                seen.add(target)
                hits.append({"cited": token,
                             "why": "the answer cites %s (as %r), the builder's own account of its "
                                    "work, which is a claim and never evidence" % (target, token)})
        for token in citation_tokens(text):
            got = canonical(token, workspace)
            if got is None:
                continue
            path, fragment = got
            key = path.lower()
            target = withheld.get(key) or (names.get(key) if "/" not in path else None)
            if target and target not in seen:
                seen.add(target)
                hits.append({"cited": token,
                             "why": "the answer cites %s (as %r), the builder's own account of its "
                                    "work, which is a claim and never evidence" % (target, token)})
            if fragment and key in anchors:
                anchor = anchors[key].get(_slug(fragment))
                if anchor and anchor not in seen:
                    seen.add(anchor)
                    hits.append({"cited": token,
                                 "why": "the answer cites %s (as %r), a withheld section of the "
                                        "builder's working record" % (anchor, token)})
    return hits


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
    # Astra's F3: the same comparison after every citation, in every answer string (check commands,
    # outputs and kept notes included), is resolved to its canonical workspace path.
    known = set(row["line"] for row in cited)
    for hit in resolved_citations(strings_of(a), provenance):
        if hit["cited"] not in known:
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
