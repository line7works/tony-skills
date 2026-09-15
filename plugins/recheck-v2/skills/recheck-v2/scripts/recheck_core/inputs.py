"""The validated input (pilot contract section 2), scope normalization (section 3), grants
(section 8), the review sheet (section 14), and the missing-input envelope (section 10).

Field paths in envelopes follow the examples: dotted, with `[i]` for array members
(`target.items[1].claim`). A record-level gap found in a build doc names `target.build_doc`
and describes the line under `ambiguity` (the contract fixes no path for it).
"""
import json
import os
import re

from . import canon, ledger

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---- loading and validation ------------------------------------------------------------------

def load_input(path):
    """(doc, raw_bytes, error). A missing or unreadable file is an error (usage, exit 2)."""
    if not os.path.isfile(path):
        return None, None, "input file does not exist: %s" % path
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        return json.loads(raw.decode("utf-8")), raw, None
    except (OSError, ValueError) as exc:
        return None, None, "input file is not readable JSON: %s (%s)" % (path, exc)


def field_path(parts):
    out = ""
    for p in parts:
        if isinstance(p, int):
            out += "[%d]" % p
        else:
            out += ("." if out else "") + str(p)
    return out


def _refine_target(doc, err, schemas):
    """A oneOf failure on target reports at the parent; re-validate the branch the keys select."""
    target = doc.get("target") if isinstance(doc, dict) else None
    if schemas is None or not isinstance(target, dict) or err["path"] != "/target" or "not valid under any" not in err["message"]:
        return None
    branches = schemas.docs["input"]["properties"]["target"]["oneOf"]
    key = "build_doc" if "build_doc" in target else "items" if "items" in target else None
    if key is None:
        return None
    branch = next((b for b in branches if key in b.get("required", [])), None)
    if branch is None:
        return None
    from . import validate as vmod
    V = vmod.require_jsonschema()
    sub = V({"$schema": schemas.docs["input"]["$schema"], "$defs": schemas.docs["input"]["$defs"], **branch})
    out = []
    for e in sub.iter_errors(target):
        out.append({"path": "/target" + ("/" + "/".join(str(p) for p in e.absolute_path) if e.absolute_path else ""), "message": e.message})
    out.sort(key=lambda e: (e["path"], e["message"]))
    return out or None


def schema_fields(errors, doc=None, schemas=None):
    """Envelope fields from validator errors: required-property errors name the property; a oneOf
    failure on target keeps the validator's own path (`target`) and gains the leaf the branch the
    target's own keys select reports (`target.items[0].record`) as a further entry (E7-7, E8-A9)."""
    fields = []
    refined = []
    for err in errors:
        refined.append(err)
        sub = _refine_target(doc, err, schemas)
        if sub:
            refined.extend(sub)
    errors = refined
    for err in errors:
        parts = [p for p in err["path"].split("/") if p != ""]
        parts = [int(p) if p.isdigit() else p for p in parts]
        m = re.match(r"^'([^']+)' is a required property$", err["message"])
        if m:
            parts = parts + [m.group(1)]
        name = field_path(parts) or "$"
        if name not in fields:
            fields.append(name)
    return fields


def is_under(path, root):
    """True when the real path of `path` sits under the real path of `root`."""
    rp, rr = os.path.realpath(path), os.path.realpath(root)
    return rp == rr or rp.startswith(rr.rstrip(os.sep) + os.sep)


def path_rules(doc, is_work_tree_root):
    """Section 2 path rules. Returns [(field, message)]; the caller builds the envelope."""
    out = []
    ws = doc.get("workspace")
    inv = doc.get("invocation") or {}
    run_dir = inv.get("run_dir")
    ws_ok = False
    if not isinstance(ws, str) or not os.path.isabs(ws):
        out.append(("workspace", "workspace must be an absolute path"))
    else:
        ok, why = is_work_tree_root(ws)
        if not ok:
            out.append(("workspace", "workspace %s %s" % (ws, why)))
        else:
            ws_ok = True
    if not isinstance(run_dir, str) or not os.path.isabs(run_dir):
        out.append(("invocation.run_dir", "run_dir must be an absolute path"))
    elif isinstance(ws, str) and os.path.isabs(ws) and is_under(run_dir, ws):
        out.append(("invocation.run_dir", "run_dir %s is inside the workspace" % run_dir))
    target = doc.get("target") or {}
    bd = target.get("build_doc")
    if bd is not None:
        if not isinstance(bd, str) or os.path.isabs(bd) or any(seg == ".." for seg in bd.split("/")):
            out.append(("target.build_doc", "build_doc must be relative with no .. segment"))
        elif ws_ok and not is_under(os.path.join(ws, bd), ws):
            out.append(("target.build_doc", "build_doc %s resolves outside the workspace after symlinks" % bd))
    # E8-A19: every explicit item's record.document is contained exactly like build_doc
    items = target.get("items") if isinstance(target.get("items"), list) else []
    for i, it in enumerate(items):
        rd = (it.get("record") or {}).get("document") if isinstance(it, dict) else None
        field = "target.items[%d].record.document" % i
        if not isinstance(rd, str) or os.path.isabs(rd) or any(seg == ".." for seg in rd.split("/")):
            out.append((field, "record.document must be relative with no .. segment"))
        elif ws_ok and not is_under(os.path.join(ws, rd), ws):
            out.append((field, "record.document %s resolves outside the workspace after symlinks" % rd))
    return out


def binding_hash(doc):
    """E8-9: the input with invocation removed, authorization.extra_continuation removed, and
    authorization removed when those removals leave it with no keys."""
    d = {k: v for k, v in doc.items() if k != "invocation"}
    auth = d.get("authorization")
    if isinstance(auth, dict):
        auth = {k: v for k, v in auth.items() if k != "extra_continuation"}
        if auth:
            d["authorization"] = auth
        else:
            d.pop("authorization", None)
    return canon.sha256_hex(canon.canonical_json(d))


def is_direct_interactive(doc):
    inv = doc.get("invocation") or {}
    return inv.get("caller") == "direct" and inv.get("mode") == "interactive"


GRANT_LISTS = ("waivers", "reopen")


def schema_rejected_grants(errors, doc):
    """E8-A35: the grant objects among a schema failure's invalid fields, one entry per object:
    `<JSON path>: <file:line or -> · <the validator's message>` (the E8-A12 shape)."""
    auth = (doc.get("authorization") if isinstance(doc, dict) else None) or {}
    by_path = {}
    for err in errors:
        parts = [p for p in err["path"].split("/") if p != ""]
        if len(parts) < 2 or parts[0] != "authorization":
            continue
        if parts[1] in GRANT_LISTS and len(parts) >= 3 and parts[2].isdigit():
            idx = int(parts[2])
            path = "authorization.%s[%d]" % (parts[1], idx)
            lst = auth.get(parts[1]) if isinstance(auth, dict) else None
            grant = lst[idx] if isinstance(lst, list) and idx < len(lst) else None
        elif parts[1] == "extra_continuation":
            path = "authorization.extra_continuation"
            grant = auth.get("extra_continuation") if isinstance(auth, dict) else None
        else:
            continue
        by_path.setdefault(path, (grant, []))[1].append(err["message"])
    out = []
    for path, (grant, messages) in by_path.items():
        item = grant.get("item") if isinstance(grant, dict) else None
        loc = item.get("location") if isinstance(item, dict) else None
        ref = "%s:%s" % (loc.get("file"), loc.get("line")) if isinstance(loc, dict) and loc.get("file") is not None else "-"
        out.append("%s: %s%s%s" % (path, ref, ledger.SEP, "; ".join(messages)))
    return out


def envelope(doc, fields, ambiguity, question=None, run=None, schema_errors=None):
    """The missing_input result. The run block is omitted when the payload failed the schema; a
    schema-valid payload that fails a path rule gets the block from the presented invocation
    (passed as `run`) with an empty write list and no run directory (section 2, E8-A6); the caller
    adds the block itself once a run directory exists. The question rides only on a direct
    interactive run. On a schema failure (`schema_errors` given) a grant object among the invalid
    fields is also listed under `rejected_grants` (E8-A35)."""
    out = {"protocol_version": 1}
    if run is not None:
        out["run"] = run
    out["status"] = "missing_input"
    out["missing_input"] = {"fields": list(fields) or ["$"], "ambiguity": list(ambiguity)}
    if question and is_direct_interactive(doc):
        out["missing_input"]["question"] = question
    if schema_errors:
        rejected = schema_rejected_grants(schema_errors, doc)
        if rejected:
            out["rejected_grants"] = rejected
    if run is not None:
        out["records_written"] = []
    return out


# ---- the review sheet (section 14) -----------------------------------------------------------

PASS_LINE = re.compile(r"^- [^:]+: (on|off)( \(.*\))?$")


def review_sheet(workspace, doc):
    """{"verdict": read | not_kit_sheet | absent, "path": abs or None, "bar": [lines], "error": str|None}."""
    named = doc.get("review_sheet", "auto")
    if named is None:
        return {"verdict": "absent", "path": None, "bar": [], "error": None}
    if named == "auto":
        path = os.path.join(workspace, "REVIEW.md")
        if not os.path.isfile(path):
            return {"verdict": "absent", "path": None, "bar": [], "error": None}
    else:
        path = named if os.path.isabs(named) else os.path.join(workspace, named)
        if not os.path.isfile(path):
            return {"verdict": "absent", "path": None, "bar": [], "error": "review_sheet names a file that does not exist: %s" % named}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return {"verdict": "not_kit_sheet", "path": path, "bar": [], "error": None}
    sections, current = {}, None
    for line in text.split("\n"):
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    needed = ("Passes", "Severity bar", "Repo-specific checks")
    if not all(h in sections for h in needed):
        return {"verdict": "not_kit_sheet", "path": path, "bar": [], "error": None}
    for line in sections["Passes"]:
        if line.strip() == "":
            continue
        if not PASS_LINE.match(line.rstrip()):
            return {"verdict": "not_kit_sheet", "path": path, "bar": [], "error": None}
    bar = [l.rstrip() for l in sections["Severity bar"] if l.strip()]
    return {"verdict": "read", "path": path, "bar": bar, "error": None}


# ---- grants (section 8, E8-24) --------------------------------------------------------------

def _ref(item):
    loc = item.get("location") or {}
    return "%s:%s" % (loc.get("file"), loc.get("line"))


def grant_channel_ok(grant, doc):
    """(ok, why) on the field rules of section 8, forwarded_by on station routes (E7-13),
    and the adapter's turn attribution (E8-24). `why` is the reason alone; the caller prefixes
    the grant's JSON path and item (E8-A12)."""
    inv = doc.get("invocation") or {}
    if grant.get("by") != "user":
        return False, "by is %r, not user; not a grant" % (grant.get("by"),)
    if grant.get("channel") != "user-turn":
        return False, "channel is %r, not user-turn; not a grant" % (grant.get("channel"),)
    if not grant.get("turn_ref"):
        return False, "no turn_ref; not a grant"
    if not grant.get("quoted_words"):
        return False, "no quoted words; not a grant"
    if not DATE_RE.match(str(grant.get("date", ""))):
        return False, "no date; not a grant"
    if inv.get("caller") != "direct" and not grant.get("forwarded_by"):
        return False, "the station route carries no forwarded_by; not a grant (ruling E7-13)"
    has_map = "turn_attribution" in inv and inv.get("turn_attribution") is not None
    attribution = inv.get("turn_attribution") or {}
    who = attribution.get(grant["turn_ref"])
    if who is not None and who != "user":
        return False, "turn_ref %r maps to %s (the adapter's turn_attribution); not a grant" % (grant["turn_ref"], who)
    if has_map and who is None:
        # E9-1: a supplied map is the session's turn list; a reference outside it names no turn of the session.
        # E9-29: a supplied map that is empty is still the session's turn list (no turns), so every reference is rejected.
        return False, "turn_ref %r is not in the adapter's turn_attribution (no turn of this session); not a grant (ruling E9-1)" % (grant["turn_ref"],)
    return True, ""


def rejected_entry(path, item, why):
    """A rejected grant object's entry: `<JSON path in the input>: <file:line> · <why>` (E8-A12)."""
    return "%s: %s%s%s; not written" % (path, _ref(item or {}), ledger.SEP, why)


def collect_grants(doc):
    """Split the presented grants into accepted and rejected on the channel rules alone.

    Returns {"waivers": [(index, grant)], "reopenings": [(index, grant)], "rejected": [str],
             "rejected_fields": [field]}; the caller resolves items and R28. A rejected entry
    reads `authorization.<kind>[<i>]: <file:line> · <why>` (E8-A12)."""
    auth = doc.get("authorization") or {}
    out = {"waivers": [], "reopenings": [], "rejected": [], "rejected_fields": []}
    for key, slot in (("waivers", "waivers"), ("reopen", "reopenings")):
        for i, g in enumerate(auth.get(key) or []):
            path = "authorization.%s[%d]" % (key, i)
            ok, why = grant_channel_ok(g, doc)
            if ok:
                out[slot].append((i, g))
            else:
                out["rejected"].append(rejected_entry(path, g.get("item"), why))
                out["rejected_fields"].append(path)
    return out


def continuation_grant_ok(doc):
    """(present, ok, reason) for authorization.extra_continuation on the presented input."""
    g = (doc.get("authorization") or {}).get("extra_continuation")
    if not g:
        return False, False, "no extra_continuation grant in the presented input"
    ok, why = grant_channel_ok(g, doc)
    return True, ok, ("authorization.extra_continuation: " + why) if why else ""


def grant_key(g):
    item = g.get("item") or {}
    loc = item.get("location") or {}
    return loc.get("file"), loc.get("line"), item.get("claim")


# ---- scope (section 3, E8-1, E8-20, E8-22, E8-26) -------------------------------------------

def read_doc(workspace, rel):
    path = os.path.join(workspace, rel)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _checklist_item(entry):
    return {"severity": entry["severity"], "location": {"file": entry["file"], "line": entry["line"]},
            "claim": ledger.entry_claim_field(entry), "failure_scenario": entry.get("scenario") or "",
            "record": {"document": entry["document"], "heading": entry["heading"] or "", "date": entry["date"] or ""},
            "slice": entry["slice"]}


def _ambiguity_lines(document, records):
    return ["%s:%d: %s: %s" % (document, r["line_no"], r["reason"], r["text"]) for r in records]


def resolve_scope(doc, workspace, accepted_reopenings):
    """Section 3. Returns one of:
    {"status": "missing_input", "fields", "ambiguity", "question"}
    {"status": "nothing_open", "document", "slice", "reason"}
    {"status": "ok", "checklist": [items], "source", "document", "slice", "parsed", "entries",
     "reopened": {index: grant}, "candidates"}
    """
    target = doc["target"]
    named = doc.get("named_items") or []
    if "items" in target:
        return _resolve_items(doc, workspace, target["items"], accepted_reopenings)
    rel = target["build_doc"]
    if not os.path.isfile(os.path.join(workspace, rel)):
        return {"status": "missing_input", "fields": ["target.build_doc"],
                "ambiguity": ["build doc %s does not exist in the workspace" % rel],
                "question": "The build doc %s does not exist in the workspace; which document holds the record?" % rel}
    parsed = ledger.parse_document(read_doc(workspace, rel), rel)
    opened = ledger.open_set(parsed)
    if opened["ambiguities"]:
        amb = _ambiguity_lines(rel, opened["ambiguities"])
        return {"status": "missing_input", "fields": ["target.build_doc"], "ambiguity": amb,
                "question": "The record line at %s:%d matches no Appendix A shape (%s); supply or confirm its fields." % (rel, opened["ambiguities"][0]["line_no"], opened["ambiguities"][0]["reason"])}
    entries = opened["entries"]
    slice_name = target.get("slice")
    candidates = []
    deferred = None  # E8-A29: an empty automatic selection is nothing_open only after the named entries and reopenings
    if slice_name is None:
        slice_name, candidates, problem = _select_slice(parsed, entries)
        if problem and problem["status"] != "nothing_open":
            return problem
        deferred = problem
    elif slice_name not in ledger.slice_names(parsed) and os.path.normpath(rel) != ledger.PUNCH_LIST_DOC:
        return {"status": "missing_input", "fields": ["target.slice"],
                "ambiguity": ["slice %s has no heading in %s (slices: %s)" % (slice_name, rel, ", ".join(ledger.slice_names(parsed)) or "none")],
                "question": "Slice %s has no heading in %s; which slice should this recheck cover?" % (slice_name, rel)}
    checklist, reopened = [], {}
    selected = []
    for e in entries:
        if e["slice"] == slice_name and e["state"] == "open" and e["severity"] in ("BLOCKER", "MAJOR"):
            selected.append(e)
    # named items and the reopening grants (each names an entry; none or several is missing input)
    refs = [("named_items[%d]" % i, n, None) for i, n in enumerate(named)]
    for gi, g in accepted_reopenings:
        refs.append(("authorization.reopen[%d]" % gi, g["item"], (gi, g)))
    problems, fields = [], []
    entered_by_name = set()
    for field, ref, grant in refs:
        loc = ref["location"]
        found = ledger.find_entries(entries, loc["file"], loc["line"], ref["claim"])
        if len(found) != 1:
            fields.append(field)
            problems.append("%s names %s:%s (%s) which matches %s in %s" % (
                field, loc["file"], loc["line"], ref["claim"], "no entry" if not found else "%d entries" % len(found), rel))
            continue
        e = found[0]
        if e["state"] != "open":
            has_grant = grant is not None or any(_same_item(g2["item"], e) for _, g2 in accepted_reopenings)
            if not has_grant:
                fields.append("authorization.reopen")
                problems.append("%s names %s:%s (%s), whose latest record leaves it %s; reopening it needs a reopening grant on the user channel naming it" % (
                    field, e["file"], e["line"], ledger.entry_claim_field(e), e["state"]))
                continue
        if e not in selected:
            selected.append(e)
        entered_by_name.add(id(e))
        if grant is not None:
            reopened[id(e)] = grant
        else:
            for gi2, g2 in accepted_reopenings:
                if _same_item(g2["item"], e):
                    reopened[id(e)] = (gi2, g2)
    if problems:
        return {"status": "missing_input", "fields": fields, "ambiguity": problems, "question": problems[0] + "; which entry is meant?"}
    # order: file order of the entries (the open filter's order); named entries keep that order too
    selected.sort(key=lambda e: e["origin"]["line_no"])
    for e in selected:
        checklist.append(_checklist_item(e))
    if slice_name is None and selected:
        # E8-A29: named entries and reopenings on a doc with no automatic candidate: the scope's slice is
        # theirs when they share one, else the run spans slices and names none
        shared = ledger.sort_slices(e["slice"] for e in selected)
        slice_name = shared[0] if len(shared) == 1 else None
    # E8-A32: the normalized checklist is checked before the brief and the checkpoint are written
    no_scenario = [e for e in selected if not (e.get("scenario") or "").strip()]
    if no_scenario:
        amb = ["the record at %s:%d has no failure scenario; supply or confirm it" % (rel, e["origin"]["line_no"]) for e in no_scenario]
        return {"status": "missing_input", "fields": ["target.build_doc"], "ambiguity": amb, "question": amb[0]}
    if not checklist:
        if deferred is not None:
            return deferred
        card = ledger.slice_card(parsed, slice_name)
        if card in ("rejected", "signed off with conditions"):
            return {"status": "missing_input", "fields": ["target.build_doc"],
                    "ambiguity": ["slice %s stands at %s with no open BLOCKER or MAJOR entry in %s: a record gap, not a clean slate (R14)" % (slice_name, card, rel)],
                    "question": "Slice %s stands at %s but the record holds no open finding for it; what are the findings this recheck should cover?" % (slice_name, card)}
        return {"status": "nothing_open", "document": rel, "slice": slice_name, "parsed": parsed, "entries": entries,
                "reason": "slice %s stands at %s with no open BLOCKER or MAJOR entry; nothing to recheck, no record written" % (slice_name, card)}
    # E8-26: named_items when every checklist entry entered by naming, else build_doc
    source = "named_items" if all(id(e) in entered_by_name for e in selected) else "build_doc"
    return {"status": "ok", "checklist": checklist, "source": source, "document": rel, "slice": slice_name,
            "parsed": parsed, "entries": entries, "reopened": {id(e): reopened[id(e)] for e in selected if id(e) in reopened},
            "selected": selected, "candidates": candidates}


def _same_item(item, entry):
    loc = item.get("location") or {}
    claim = item.get("claim")
    if isinstance(claim, str):
        claim = ledger.strip_parens(claim)  # E8-A28: the join key normalizes the claim
    return loc.get("file") == entry["file"] and loc.get("line") == entry["line"] and (
        claim == entry["claim"] or entry["claim"] is None or claim is None)


def _select_slice(parsed, entries):
    """build_doc without slice (section 3): the candidate whose punch-list block carries the latest date."""
    cands = []
    for s in parsed["slices"]:
        card = s["card"]
        open_bm = [e for e in entries if e["slice"] == s["name"] and e["state"] == "open" and e["severity"] in ("BLOCKER", "MAJOR")]
        if card in ("rejected", "signed off with conditions") or (card == "built" and open_bm):
            dates = [b["date"] for b in parsed["blocks"] if s["name"] in b["slices"]]
            cands.append((max(dates) if dates else "", s["name"], card))
    if not cands:
        return None, [], {"status": "nothing_open", "document": parsed.get("document"), "slice": None, "parsed": parsed,
                          "entries": entries, "reason": "no slice stands at rejected or signed off with conditions, and no built slice holds an open BLOCKER or MAJOR entry; nothing to recheck, no record written"}
    best = max(c[0] for c in cands)
    top = [c for c in cands if c[0] == best]
    if len(top) > 1:
        names = ", ".join(c[1] for c in top)
        return None, top, {"status": "missing_input", "fields": ["target.slice"],
                           "ambiguity": ["slices %s all stand at %s with punch-list blocks dated %s" % (names, " / ".join(sorted(set(c[2] for c in top))), best or "none")],
                           "question": "Which slice should this recheck cover, %s?" % " or ".join(c[1] for c in top)}
    return top[0][1], cands, None


def _resolve_items(doc, workspace, items, accepted_reopenings):
    """Explicit items: each carries its provenance and slice; the core guesses neither."""
    fields, amb = [], []
    seen = {}
    for i, it in enumerate(items):
        key = (it["location"]["file"], it["location"]["line"], it["claim"])
        if key in seen:
            fields.append("target.items[%d]" % i)
            amb.append("items %d and %d share location %s:%s and claim %r" % (seen[key], i, key[0], key[1], key[2]))
        else:
            seen[key] = i
    docs = sorted(set(it["record"]["document"] for it in items))
    if len(docs) > 1:
        for i, it in enumerate(items):
            fields.append("target.items[%d].record.document" % i)
        amb.append("items name several documents (%s); one run records one document" % ", ".join(docs))
    if fields:
        return {"status": "missing_input", "fields": fields, "ambiguity": amb, "question": amb[0] + "; which item is meant?"}
    rel = docs[0]
    # E8-A16: a record.document that does not exist in the workspace is missing input (section 3's
    # docs/punch-list.md is the document the review wrote, never one this run creates)
    if not os.path.isfile(os.path.join(workspace, rel)):
        return {"status": "missing_input", "fields": ["target.items[0].record.document"],
                "ambiguity": ["record document %s does not exist in the workspace" % rel],
                "question": "The record document %s does not exist in the workspace; which document holds the record?" % rel}
    parsed = ledger.parse_document(read_doc(workspace, rel), rel)
    opened = ledger.open_set(parsed)
    if opened["ambiguities"]:
        return {"status": "missing_input", "fields": ["target.items[0].record.document"],
                "ambiguity": _ambiguity_lines(rel, opened["ambiguities"]),
                "question": "The record line at %s:%d matches no Appendix A shape; supply or confirm its fields." % (rel, opened["ambiguities"][0]["line_no"])}
    # E8-A16: an item's slice that is not `none` needs a `## Slice <name>` heading in its document
    names = ledger.slice_names(parsed)
    for i, it in enumerate(items):
        if it["slice"] != "none" and it["slice"] not in names:
            fields.append("target.items[%d].slice" % i)
            amb.append("target.items[%d].slice names %s, which has no `## Slice %s` heading in %s (slices: %s)" % (
                i, it["slice"], it["slice"], rel, ", ".join(names) or "none"))
    if fields:
        return {"status": "missing_input", "fields": fields, "ambiguity": amb, "question": amb[0] + "; which slice is meant?"}
    checklist = [dict(it) for it in items]
    slices = ledger.sort_slices(it["slice"] for it in items if it["slice"] != "none")
    reopened = {}
    for gi, g in accepted_reopenings:
        for idx, it in enumerate(items):
            if grant_key(g) == (it["location"]["file"], it["location"]["line"], it["claim"]):
                reopened[idx] = (gi, g)
    return {"status": "ok", "checklist": checklist, "source": "items", "document": rel, "slice": slices[0] if len(slices) == 1 else None,
            "parsed": parsed, "entries": opened["entries"], "reopened_by_index": reopened, "selected": None, "candidates": []}
