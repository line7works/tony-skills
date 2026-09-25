"""What `harvest` collects (brief 3.3): the scope doc's ledger, the living doc, the slug and the target.

`describe(...)` is pure: given the texts it builds the harvest record `harvest.json` holds. The
handler (`phases.harvest`) reads the files, decides the stops, and writes the record.
"""
import os
import re

from station_core import fsio, ledger, runlog, templates

from .common import SLUG, display, inside
from . import docs

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


def living_findings(text):
    """Why the living doc cannot be continued: its form's findings, and CR line endings."""
    findings = [dict(f) for f in templates.check("architecture-doc", text)]
    if "\r" in text:
        findings.append({"line": 1, "message": "the doc has CR line endings; this core continues LF documents only"})
    return findings


def describe(workspace, staging, today, slug, scope_path, scope_text, living_path, living_text, run_id=None,
             input_publish=True):
    """The harvest record. Raises `station_core.ledger.LedgerRefused` on a ledger it cannot tag."""
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
            "input_publish": bool(input_publish)}
