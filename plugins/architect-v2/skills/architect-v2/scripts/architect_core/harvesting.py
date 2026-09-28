"""What `harvest` collects (brief 3.3): the scope doc's ledger, the living doc, the slug and the target.

`describe(...)` is pure: given the texts it builds the harvest record `harvest.json` holds. The
handler (`phases.harvest`) reads the files, decides the stops, and writes the record.
"""
import os
import re

from station_core import fsio, ledger, runlog, templates

from .common import HEADER_LABELS, SLUG, display, inside
from . import docs, schema

DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)$")


def slug_of(path):
    """The scope doc's idea slug: the `<idea>` of `docs/scope/<YYYY-MM-DD>-<idea>.md`, of a flat
    `<idea>-scope.md`, or a dateless `docs/scope/<idea>.md`; never the date. None when the name
    yields no slug a hunt can take."""
    name = os.path.basename(path)
    if name.endswith("-scope.md"):
        slug = name[:-len("-scope.md")]
    elif name.endswith(".md"):
        slug = name[:-3]
        match = DATED.match(slug)
        if match:
            slug = match.group(1)
    else:
        return None
    return slug if SLUG.match(slug) else None


def home_of(path, workspace, staging):
    if inside(path, workspace):
        return "workspace"
    if staging and inside(path, staging):
        return "staging"
    return None


def new_doc_path(home, workspace, staging, today, slug):
    if home == "workspace":
        return os.path.join(workspace, "docs", "architecture", "%s-%s.md" % (today, slug))
    return os.path.join(staging, "%s-architecture.md" % slug)


LISTED = (docs.POURED, docs.DEFERRED)


def free_lines(text):
    """The non-blank lines under `## Poured concrete (one-way doors)` or `## Deferred` that are no
    `- ` list line, and the lines of the head (after the title) that are none of its header
    lines. An answer carries or strikes list lines only, and the header lines are each run's own,
    so such a line (a note or a heading the owner typed there) could be neither kept nor struck by
    any re-run: the run stops at harvest naming it, and the owner fixes the doc (CA1-11)."""
    out = []
    heading = None
    for number, line in enumerate(text.split("\n"), 1):
        if line.startswith("## "):
            heading = line
            continue
        if heading is None and number > 1 and line.strip() and not line.startswith(HEADER_LABELS):
            out.append({"line": number, "message": "%r in the doc's head is none of its header lines (Scope doc or "
                        "Docless, Blind review, Artifact), which each run renders anew, so no re-run could keep it; "
                        "move it into a section by hand, then start a new run" % line})
        if heading in LISTED and line.strip() and not line.startswith("- "):
            out.append({"line": number, "message": "%r under %s is no '- ' list line, so no answer can carry or strike "
                        "it; make it a list line or move it out of the section by hand, then start a new run"
                        % (line, heading[3:])})
    return out


def living_findings(text):
    """Why the living doc cannot be continued: its form's findings, a free line under a listed
    section, CR line endings, and a line holding a line boundary other than LF and CR (slice 3b R5,
    CA7-3): every answer string refuses those, so such a line could be neither carried nor struck.
    The character is named by its code point; the line is quoted by `%r`, which never prints it raw."""
    findings = [dict(f) for f in templates.check("architecture-doc", text)]
    findings += free_lines(text)
    if "\r" in text:
        findings.append({"line": 1, "message": "the doc has CR line endings; this core continues LF documents only"})
    boundaries = schema.LINE_BOUNDARIES - {"\n", "\r"}
    for number, line in enumerate(text.split("\n"), 1):
        held = sorted(set(ch for ch in line if ch in boundaries))
        if held:
            findings.append({"line": number, "message": "%r holds %s, a line boundary other than LF (vertical tab, "
                             "form feed, U+001C to U+001E, U+0085, U+2028 or U+2029), so no answer can carry or "
                             "strike it; the doc is left as found: replace it by hand, then start a new run"
                             % (line, " and ".join("U+%04X" % ord(ch) for ch in held))})
    return findings


def describe(workspace, staging, today, slug, scope_path, scope_text, living_path, living_text, run_id=None,
             input_publish=True, set_aside=None, docless_reason=None):
    """The harvest record. Raises `station_core.ledger.LedgerRefused` on a ledger it cannot tag.
    `set_aside` is the scope hunt's hits the input set aside, one or several (`{paths, reason}`), and
    `docless_reason` the input's `station.docless_reason`, which the answer's docless reason must be."""
    rows = ledger.read(scope_text) if scope_text is not None else []
    scope = None
    if scope_path is not None:
        scope = {"path": scope_path, "display": display(scope_path, workspace),
                 "home": home_of(scope_path, workspace, staging),
                 "sha256": fsio.sha256_bytes(scope_text.encode("utf-8"))}
    living = None
    if living_path is not None:
        parsed = templates.parse("architecture-doc", living_text)
        living = {"path": living_path, "home": home_of(living_path, workspace, staging),
                  "outline": [{"line": o["line"], "role": o["role"], "key": o.get("key")} for o in parsed["outline"]
                              if o["role"] in ("title", "heading", "subheading")],
                  "round_trip_identical": templates.render(parsed) == living_text,
                  "sha256": fsio.sha256_bytes(living_text.encode("utf-8")),
                  "runs": [n for n, _ in runlog.runs(living_text)], "next_run": runlog.next_run(living_text),
                  "artifact_url": docs.artifact_url(living_text) if not living_findings(living_text) else None,
                  "findings": living_findings(living_text)}
    if living is not None:
        target = {"path": living_path, "home": living["home"]}
    elif scope is not None:
        target = {"path": new_doc_path(scope["home"], workspace, staging, today, slug), "home": scope["home"]}
    else:
        target = {"path": None, "home": None}
    return {"harvest_version": 1, "run_id": run_id, "today": today, "workspace": workspace, "staging": staging,
            "slug": slug, "docless": scope is None, "scope_doc": scope, "ledger": rows,
            "ledger_counts": ledger.counts(rows), "living_doc": living, "target": target,
            "input_publish": bool(input_publish), "set_aside": set_aside, "docless_reason": docless_reason}
