"""What `harvest` reads before anything is asked (contract section 6).

    selected(run_dir, hunt)      the hunt's selection as `select` (or the owner's `choose`) left it
    architecture_lines(text)     the architecture doc's poured-concrete and deferred lines, each
                                 with a stable id, read through `templates.parse`, and `refused`:
                                 every line of those two sections that is not a `- <text>` item, and
                                 either section missing by its exact heading text (a re-cased or
                                 renamed heading reads as missing, and is quoted), each quoted
    ledger_view(scope, arch)     the ledger `record-answer`'s shared refusals read: the scope doc's
                                 lines as the ledger reader emits them, then the architecture doc's
                                 poured-concrete lines as `decided` and its deferred lines as `parked`
    build_doc(path, text)        an existing build doc: its slices and their `Status:` lines, its
                                 `Plan: inspected` lines and its five ledger sections, byte for byte

A struck poured-concrete line (`~~...~~`) is superseded: it is listed, and it is not in the view,
so a line cannot pass forward through it. A poured-concrete or deferred line the reader cannot read
is refused, never dropped: `harvest` stops `ledger-refused` quoting every refused line (round 2,
R4), so a decision it could not see can never be re-asked or quietly resolved. A `### ` subheading
inside either section is passed over (the section runs to the next `## ` heading, so it hides no
item). Nothing here writes a file.
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


SECTION_MISSING = tuple("missing the section '%s'" % heading for heading in (POURED, DEFERRED))


def _names_a_section(message):
    """A `templates.check` finding that one of the two sections is missing, known by its exact heading
    text as the template writes it (round 3, R5); an unrelated section whose heading merely holds the
    word (`## Why we deferred the cache`, `## Notes`) is passed over."""
    return message in SECTION_MISSING


def _near_miss(parsed, message):
    """The doc's own heading nearest the missing one (re-cased, or without its suffix), quoted."""
    wanted = POURED if POURED in message else DEFERRED
    stem = wanted.casefold() if wanted == DEFERRED else "## poured concrete"
    for row in parsed["outline"]:
        raw = parsed["lines"][row["line"] - 1].rstrip("\r\n")
        if row["role"] == "heading" and raw != wanted and (
                raw.strip().casefold() == stem or raw.strip().casefold().startswith(stem + " ")
                or raw.strip().casefold() == wanted.casefold()):
            return row["line"], raw
    return None


def architecture_lines(text):
    parsed = templates.parse("architecture-doc", text)
    section = None
    out = {"poured": [], "struck": [], "deferred": [], "refused": []}
    seen = {}
    fence = False
    for row in parsed["outline"]:
        raw = parsed["lines"][row["line"] - 1].rstrip("\r\n")
        if row["role"] == "fence":
            fence = not fence
        if row["role"] == "heading":
            section = row["key"]
            continue
        if section not in (POURED, DEFERRED) or not raw.strip() or row["role"] == "subheading":
            continue
        item = raw[2:].strip() if raw.startswith("- ") else ""
        if fence or row["role"] == "fence" or not item:
            out["refused"].append({"line": row["line"], "raw": raw,
                                   "why": "not a '- <text>' item under %s" % section})
            continue
        if section == POURED:
            struck = item.startswith("~~") and item.endswith("~~")
            bucket = "struck" if struck else "poured"
            out[bucket].append({"id": _line_id("arch", item, seen), "text": item, "line": row["line"]})
        else:
            out["deferred"].append({"id": _line_id("defer", item, seen), "text": item, "line": row["line"]})
    for finding in templates.check("architecture-doc", text):
        if _names_a_section(finding["message"]):
            near = _near_miss(parsed, finding["message"])
            if near is not None:
                out["refused"].append({"line": near[0], "raw": near[1], "why": "%s; the doc's heading here is not "
                                       "it, whole" % finding["message"]})
            else:
                out["refused"].append({"line": finding["line"], "raw": "(no such heading in the doc)",
                                       "why": finding["message"]})
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
