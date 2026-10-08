"""A `readers` request built from a core's input and documents (station-loop.md section 8, rule 5).

    build(row, input_doc, roster, mandate, profile, run_id, call_id, documents=None,
          workspace=None, session_model=None, model=None, effort=None, raw_path=None,
          run_dir=None) -> the request, a dict holding only the fields readers' contract defines

The fields are readers' own (its `contract.md`, "The request"; `readers-protocol: 1`). The script
builds the request and records the result; the executor summons readers (ruling E14-4).

`authorized` is the one field this module decides, and it decides it from the input alone:
`true` only when the row's provider (read from readers' roster) is not `anthropic` AND the input's
`owner_word.rows` names the row. It is never a parameter, so no caller can set it, and nothing is
remembered between calls. On every other request the field is absent, which readers reads as no
word. `session_model` rides on the `claude-session` row only.
"""
import json

PROTOCOL_VERSION = 1
HOME_PROVIDER = "anthropic"
PROFILES = ("starved", "packet-only", "repo", "repo-with-tools")
REQUEST_FIELDS = ("protocol_version", "run_id", "call_id", "run_dir", "row", "mandate", "documents",
                  "workspace", "profile", "effort", "model", "output_budget", "raw_path",
                  "authorized", "floor", "session_model", "isolation")


class RequestRefused(ValueError):
    """A request this module will not build: an unknown row or profile, nothing to read."""


def load_roster(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def provider_of(roster, row):
    for entry in (roster or {}).get("rows") or []:
        if isinstance(entry, dict) and entry.get("id") == row:
            return entry.get("provider")
    raise RequestRefused("row %r is not in readers' roster" % (row,))


def owner_named(input_doc, row):
    word = (input_doc or {}).get("owner_word")
    if not isinstance(word, dict):
        return False
    rows = word.get("rows")
    return isinstance(rows, list) and row in rows


def build(row, input_doc, roster, mandate, profile, run_id, call_id, documents=None, workspace=None,
          session_model=None, model=None, effort=None, raw_path=None, run_dir=None):
    provider = provider_of(roster, row)
    if profile not in PROFILES:
        raise RequestRefused("profile %r is none of %s" % (profile, ", ".join(PROFILES)))
    if not documents and not workspace:
        raise RequestRefused("a request carries documents, a workspace, or both")
    req = {"protocol_version": PROTOCOL_VERSION, "run_id": run_id, "call_id": call_id, "row": row,
           "mandate": mandate, "profile": profile}
    if documents:
        req["documents"] = list(documents)
    if workspace:
        req["workspace"] = workspace
    if run_dir:
        req["run_dir"] = run_dir
    if model:
        req["model"] = model
    if effort:
        req["effort"] = effort
    if raw_path:
        req["raw_path"] = raw_path
    if row == "claude-session" and session_model:
        req["session_model"] = session_model
    if provider != HOME_PROVIDER and owner_named(input_doc, row):
        req["authorized"] = True
    return req
