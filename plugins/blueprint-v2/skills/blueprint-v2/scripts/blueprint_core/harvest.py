"""What `harvest` reads before anything is asked (contract section 6).

    selected(run_dir, hunt)      the hunt's selection as `select` (or the owner's `choose`) left it
    architecture_lines(text)     the architecture doc's poured-concrete and deferred lines, each
                                 with a stable id, read through `templates.parse`
    ledger_view(scope, arch)     the ledger `record-answer`'s shared refusals read: the scope doc's
                                 lines as the ledger reader emits them, then the architecture doc's
                                 poured-concrete lines as `decided` and its deferred lines as `parked`
    build_doc(path, text)        an existing build doc: its slices and their `Status:` lines, its
                                 `Plan: inspected` lines and its five ledger sections, byte for byte

A struck poured-concrete line (`~~...~~`) is superseded: it is listed, and it is not in the view,
so a line cannot pass forward through it. Nothing here writes a file.
"""
import hashlib
import os

from station_core import fsio, templates

from . import buildoc

POURED = "## Poured concrete (one-way doors)"
DEFERRED = "## Deferred"


class NotSelected(RuntimeError):
    """A hunt `harvest` needs was not run."""


def selected(run_dir, hunt):
    path = os.path.join(run_dir, "selection-%s.json" % hunt)
    if not os.path.isfile(path):
        raise NotSelected(hunt)
    return fsio.read_json(path)


def taken(selection):
    """(path or None, several list or None, the owner's words or None)."""
    outcome = selection.get("outcome")
    if outcome == "one":
        return selection["candidates"][0]["path"], None, None
    if outcome == "several":
        chosen = selection.get("chosen")
        if chosen:
            return chosen["path"], None, chosen.get("words")
        return None, [c["path"] for c in selection.get("candidates") or []], None
    return None, None, None


def _line_id(prefix, text, seen):
    digest = hashlib.sha256(("%s\0%s" % (prefix, text.strip())).encode("utf-8")).hexdigest()[:12]
    base = "%s-%s" % (prefix, digest)
    seen[base] = seen.get(base, 0) + 1
    return base if seen[base] == 1 else "%s-%d" % (base, seen[base])


def architecture_lines(text):
    parsed = templates.parse("architecture-doc", text)
    section = None
    out = {"poured": [], "struck": [], "deferred": []}
    seen = {}
    for row in parsed["outline"]:
        raw = parsed["lines"][row["line"] - 1].rstrip("\r\n")
        if row["role"] == "heading":
            section = row["key"]
            continue
        if section not in (POURED, DEFERRED) or not raw.startswith("- "):
            continue
        item = raw[2:].strip()
        if not item:
            continue
        if section == POURED:
            struck = item.startswith("~~") and item.endswith("~~")
            bucket = "struck" if struck else "poured"
            out[bucket].append({"id": _line_id("arch", item, seen), "text": item, "line": row["line"]})
        else:
            out["deferred"].append({"id": _line_id("defer", item, seen), "text": item, "line": row["line"]})
    return out


def ledger_view(scope_ledger, arch):
    view = [{"id": r["id"], "tag": r["tag"], "text": r["text"]} for r in scope_ledger or []]
    if arch:
        view += [{"id": r["id"], "tag": "decided", "text": r["text"]} for r in arch["poured"]]
        view += [{"id": r["id"], "tag": "parked", "text": r["text"]} for r in arch["deferred"]]
    return view


def build_doc(path, text):
    st = buildoc.structure(text)
    return {"path": path, "sha256": fsio.sha256_bytes(text.encode("utf-8")),
            "newline": buildoc.newline_of(text),
            "slices": [{"name": s["name"], "short": s["short"], "status": s["status"],
                        "status_line": s["status_line"], "line": s["start"] + 1} for s in st["slices"]],
            "stamps": st["stamps"],
            "ledger_lines": st["lines"][st["ledger_start"]:] if st["ledger_start"] is not None else [],
            "form_findings": templates.check("build-doc", text)}
