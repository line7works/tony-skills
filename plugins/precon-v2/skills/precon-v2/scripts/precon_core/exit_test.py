"""The exit test: the readers requests of a cold read, the calls' results, and the cold-read doc.

The script builds the requests and records the results; the executor summons `readers`
(rule E14-4). A request is `station_core/readers_request.py`'s, so `authorized` is set from the
input's `owner_word` alone and never on an anthropic row; this module adds precon's own rule on
top: an outside row the owner's word does not name is not built at all (v1: nothing is sent
until the owner answers with a row).

readers' run directory for the calls is `<run_dir>/readers`, so each call's sidecar is found at
`<run_dir>/readers/<call id>/sidecar.json`, read from disk, never typed by the executor.
"""
import json
import os
import re

from station_core import fsio, readers_request, templates

D = templates.D
M = templates.M
# v1's cold-reader prompt, verbatim (the lane contract quotes it once); the dash is carried, not typed
MANDATE = "read this scope doc " + D + " what's unclear, what would you ask before building this?"
PROFILE = "starved"
HOME = readers_request.HOME_PROVIDER
READERS = "readers"
MANIFEST = os.path.join(".claude-plugin", "plugin.json")
SECTION = re.compile(r"^## (?P<row>[a-z0-9][a-z0-9-]*) %s (?P<model>.+)$" % M)
DISPOSITIONS = ("surfaced", "absorbed", "left downstream")


class RosterMissing(LookupError):
    """readers' roster could not be found beside this core."""


def _manifest(folder):
    try:
        with open(os.path.join(folder, MANIFEST), encoding="utf-8") as fh:
            body = json.load(fh)
        return body if isinstance(body, dict) else None
    except (OSError, ValueError):
        return None


def _version_key(name):
    parts = name.split(".")
    return tuple(int(p) for p in parts) if all(p.isdigit() for p in parts) else None


def roster_path(plugin_root, explicit=None):
    """readers' `roster.json`: an explicit file, else route 3a (the checkout sibling), else route 3b
    (the installed shape, the highest version folder whose manifest names `readers` at that
    version). The records component's two routes, applied to readers."""
    if explicit:
        if not os.path.isfile(explicit):
            raise RosterMissing("--roster is not a file: %s" % explicit)
        return explicit
    looked = []
    sibling = os.path.join(os.path.dirname(plugin_root), READERS)
    looked.append(sibling)
    body = _manifest(sibling)
    if body and body.get("name") == READERS:
        return os.path.join(sibling, "skills", READERS, "assets", "roster.json")
    parent = os.path.join(os.path.dirname(os.path.dirname(plugin_root)), READERS)
    looked.append(parent)
    best = None
    if os.path.isdir(parent):
        for name in os.listdir(parent):
            key = _version_key(name)
            body = _manifest(os.path.join(parent, name))
            if key is not None and body and body.get("name") == READERS and body.get("version") == name:
                if best is None or key > best[0]:
                    best = (key, os.path.join(parent, name))
    if best:
        return os.path.join(best[1], "skills", READERS, "assets", "roster.json")
    raise RosterMissing("readers is not installed beside this core (looked in %s); pass --roster FILE"
                        % ", ".join(looked))


def plan_requests(rows, input_doc, roster, run_id, run_dir, document, session_model=None, models=None):
    """(requests, refusals): every named row built, or nothing and the reasons."""
    refusals = []
    models = models or {}
    if not rows:
        refusals.append("name at least one readers row with --row")
    if len(set(rows)) != len(rows):
        refusals.append("a row is named twice: %s" % ", ".join(rows))
    for row in rows:
        try:
            provider = readers_request.provider_of(roster, row)
        except readers_request.RequestRefused as exc:
            refusals.append(str(exc))
            continue
        if provider != HOME and not readers_request.owner_named(input_doc, row):
            refusals.append("row %r is outside (provider %s) and this run's owner_word does not name it: ask the "
                            "owner which row, and start a new run whose input's owner_word carries his words and "
                            "that row" % (row, provider))
    for row in models:
        if row not in rows:
            refusals.append("--model names %r, which is not a requested row" % row)
    if refusals:
        return [], refusals
    out = []
    for row in rows:
        call_id = "%s-%s" % (run_id, row)
        req = readers_request.build(row, input_doc, roster, MANDATE, PROFILE, run_id, call_id, documents=[document],
                                    session_model=session_model, model=models.get(row),
                                    run_dir=os.path.join(run_dir, READERS))
        out.append(req)
    return out, []


def read_request(path):
    """A request this run built (its file under the run directory)."""
    return fsio.read_json(path)


def sidecar_path(run_dir, call_id):
    return os.path.join(run_dir, READERS, call_id, "sidecar.json")


def read_call(run_dir, req):
    """The call's result as readers recorded it, or a why-not string."""
    path = sidecar_path(run_dir, req["call_id"])
    if not os.path.isfile(path):
        return "no sidecar at %s: readers recorded no result for call %s" % (path, req["call_id"])
    try:
        body = fsio.read_json(path)
    except (OSError, ValueError) as exc:
        return "the sidecar at %s cannot be read: %s" % (path, exc)
    if not isinstance(body, dict):
        return "the sidecar at %s is not an object" % path
    for key in ("call_id", "run_id", "row"):
        if body.get(key) != req[key]:
            return "the sidecar at %s names %s %r, not the request's %r" % (path, key, body.get(key), req[key])
    if body.get("status") == "ok" and not (isinstance(body.get("raw_text"), str) and body["raw_text"].strip()):
        return "the sidecar at %s says ok with no raw_text" % path
    return {"row": body["row"], "call_id": body["call_id"], "status": body.get("status"),
            "reason": body.get("reason"), "effective_model": body.get("effective_model"),
            "raw_text": body.get("raw_text") or "", "sidecar": path}


def cold_read_path(doc_home, workspace, staging, date, idea):
    if doc_home == "staging":
        return os.path.join(staging, "precon-cold-reads", "%s-cold-read-%s.md" % (idea, date))
    return os.path.join(workspace, "docs", "reviews", "%s-precon-cold-read-%s.md" % (date, idea))


def render_sections(calls):
    """One section per ok call: the row and the effective model, the sidecar, the raw text verbatim."""
    out = []
    for call in calls:
        if call["status"] != "ok":
            continue
        raw = call["raw_text"]
        out.append("\n## %s %s %s\nSidecar: %s\n\n%s%s" % (call["row"], M, call["effective_model"] or "unknown",
                                                           call["sidecar"], raw, "" if raw.endswith("\n") else "\n"))
    return "".join(out)


def render_cold_read(existing, idea, date, scope_rel, run_id, calls):
    sections = render_sections(calls)
    if existing is None:
        head = "# Precon cold read: %s (%s)\n\nScope doc: %s\nRun: %s\n" % (idea, date, scope_rel, run_id)
        return head + sections
    return existing + ("" if existing.endswith("\n") else "\n") + sections


def section_rows(text):
    """The rows with a reader section: a `## <row> · <model>` heading followed by its `Sidecar:` line."""
    lines = text.split("\n")
    rows = set()
    for index, line in enumerate(lines[:-1]):
        match = SECTION.match(line)
        if match and lines[index + 1].startswith("Sidecar: "):
            rows.add(match.group("row"))
    return rows


def render_disposition(existing, date, run_id, summary, dispositions):
    """The block inserted above the first section; every byte of the doc below it kept."""
    block = ["## Disposition (%s, run %s)" % (date, run_id), "Summary: %s" % summary]
    for item in dispositions:
        line = "- %s %s %s %s %s" % (item["row"], M, item["item"], M, item["disposition"])
        if item.get("why"):
            line += " (%s)" % item["why"]
        block.append(line)
    text = "\n".join(block) + "\n\n"
    at = existing.find("\n## ")
    if at < 0:
        return existing + ("" if existing.endswith("\n") else "\n") + "\n" + text
    return existing[:at + 1] + text + existing[at + 1:]
