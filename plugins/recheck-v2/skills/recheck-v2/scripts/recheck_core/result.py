"""Result assembly (pilot contract sections 4, 9; E8-4, E8-21, E8-26, E8-29), validation with
the failure path of lane contract section 5, and the chat block of Appendix A.
"""
import datetime
import json
import os

from . import canon, identity, ledger, validate, verifier as vmod

UNKNOWN_HARNESS = {"name": "unknown", "version": "unknown", "entry": "unknown", "sandbox": "unknown"}
RECORD_KINDS = ("reopened_line", "punch_list_block", "waived_line", "verdict_doc_copy", "status_line")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today():
    return datetime.date.today().isoformat()


def skill_identity(skill_root):
    """{name, version, commit, content_sha256} from the skill root (lane contract section 5)."""
    name, version = "recheck-v2", "unversioned"
    plugin = os.path.join(skill_root, "..", "..", ".claude-plugin", "plugin.json")
    if os.path.isfile(plugin):
        try:
            with open(plugin, "rb") as fh:
                meta = json.loads(fh.read().decode("utf-8"))
            name = meta.get("name") or name
            version = meta.get("version") or version
        except (OSError, ValueError):
            pass
    commit = "unversioned"
    if not os.path.isdir(skill_root):  # a nonexistent root is the caller's usage error; never a git failure
        return {"name": name, "version": version, "commit": commit, "content_sha256": "0" * 64}
    top = identity.git(skill_root, ["rev-parse", "--show-toplevel"], check=False)
    if top is not None:
        head = identity.git(skill_root, ["rev-parse", "HEAD"], check=False)
        if head:
            commit = head.strip()
    body = os.path.join(skill_root, "SKILL.md")
    if not os.path.isfile(body):
        body = os.path.join(skill_root, "references", "pilot-contract.md")
    content = canon.sha256_file(body) if os.path.isfile(body) else "0" * 64
    return {"name": name, "version": version, "commit": commit, "content_sha256": content}


def harness_block(inv):
    h = inv.get("harness")
    if isinstance(h, dict) and all(h.get(k) for k in ("name", "version", "entry", "sandbox")):
        return {k: h[k] for k in ("name", "version", "entry", "sandbox")}
    return dict(UNKNOWN_HARNESS)


def model_block(inv):
    m = inv.get("model")
    if not isinstance(m, dict):
        return {"id": "unknown", "floor_class": "unknown", "floor_met": None}
    out = {"id": m.get("id") or "unknown", "floor_class": m.get("floor_class") or "unknown"}
    if "floor_met" in m:
        out["floor_met"] = m["floor_met"]
    for k in ("effort", "provider_route", "context_tokens", "settings"):
        if k in m:
            out[k] = m[k]
    return out


def run_block(doc, skill_root, run_date=None, continuations=0, started=None, finished=None, verifier=None, session_wrote_fix=None):
    inv = doc.get("invocation") or {}
    run = {"run_id": inv.get("run_id"), "run_dir": inv.get("run_dir"),
           "invocation": {"mode": inv.get("mode"), "caller": inv.get("caller"), "resume": bool(inv.get("resume", False)),
                          "continuations": int(continuations)},
           "harness": harness_block(inv), "model": model_block(inv), "skill": skill_identity(skill_root)}
    if run_date:
        run["invocation"]["run_date"] = run_date
    if started:
        run["started"] = started
    if finished:
        run["finished"] = finished
    if verifier is not None:
        run["verifier"] = verifier
    if session_wrote_fix is not None:
        run["session_wrote_fix"] = bool(session_wrote_fix)
    return run


def verifier_block(checkpoint_doc, sidecar, run_dir):
    """run.verifier from the checkpoint's calls and the sidecar; None when no call was made."""
    calls = checkpoint_doc.get("verifier_calls") or []
    if not calls:
        return None
    meta = {c["call_id"]: c for c in sidecar.get("calls", [])}
    out_calls = []
    kind, model, injected, refused = "unknown", "unknown", [], []
    raw_path = None
    for c in calls:
        entry = {"call_id": c["call_id"], "status": "ok" if vmod.is_complete(c["status"]) else c["status"]}
        if c.get("raw_path"):
            entry["raw_path"] = c["raw_path"]
        if c.get("raw_sha256"):
            entry["raw_sha256"] = c["raw_sha256"]
        out_calls.append(entry)
        m = meta.get(c["call_id"], {})
        kind = m.get("kind") or kind
        model = m.get("model") or model
        # E8-A35: every value lands; channels accumulate across calls, each once
        for name in m.get("injected") or []:
            if name not in injected:
                injected.append(name)
        refused = refused + list(m.get("refused") or [])
        if vmod.is_complete(c["status"]) and c.get("raw_path"):
            raw_path = c["raw_path"]
    if raw_path is None:
        with_raw = [c for c in calls if c.get("raw_path")]
        raw_path = with_raw[-1]["raw_path"] if with_raw else os.path.join(run_dir, "verifier", "raw.md")
    block = {"kind": kind, "model": model, "fresh": True, "injected_channels": list(injected), "restrictions_declared": True,
             "raw_path": raw_path, "calls": out_calls}
    if refused:
        block["refused_actions"] = refused
    return block


def artifact_writes(paths):
    return [{"kind": "run_artifact", "path": p, "appended": False} for p in paths]


def step_writes(plan, workspace_relative=True):
    out = []
    for s in plan:
        if s.get("cancelled") or not s.get("landed"):
            continue
        w = {"kind": s["kind"], "path": s["target"], "appended": s["kind"] != "status_line",
             "sha256_before": s["before_sha256"], "sha256_after": s["after_sha256"]}
        if s.get("heading"):
            w["heading"] = s["heading"]
        out.append(w)
    return out


def apply_markers(items, waivers, reopenings):
    """E8-21: markers from scope.grants; a stored marker is kept. The marker's quoted_words carry
    the ledger form (a double quote written as a single quote, E8-A16); the original words stay in
    the run artifacts (input.json, the checkpoint)."""
    for it in items:
        key = (it["location"]["file"], it["location"]["line"], it["claim"])
        for g in waivers:
            gi = g["item"]
            if (gi["location"]["file"], gi["location"]["line"], gi["claim"]) == key or (
                    it["claim"] == ledger.NO_CLAIM and (gi["location"]["file"], gi["location"]["line"]) == key[:2]):
                it.setdefault("waived", {"date": g["date"], "quoted_words": ledger.ledger_words(g["quoted_words"]), "turn_ref": g["turn_ref"]})
        for g in reopenings:
            gi = g["item"]
            if (gi["location"]["file"], gi["location"]["line"], gi["claim"]) == key or (
                    it["claim"] == ledger.NO_CLAIM and (gi["location"]["file"], gi["location"]["line"]) == key[:2]):
                it.setdefault("reopened", {"date": g["date"], "quoted_words": ledger.ledger_words(g["quoted_words"]), "turn_ref": g["turn_ref"]})
    return items


def needed_text(item):
    reason = item.get("reason")
    ver = item.get("verification") or {}
    if reason == "missed_case":
        detail = ver.get("evidence", [{}])[0].get("detail", "")
        case = detail[len("missed case: "):].split(";")[0] if detail.startswith("missed case: ") else "the missed case"
        return "close the missed case: %s" % case
    if reason == "verification_blocked":
        return "rerun where the execution is not blocked: %s" % ver.get("blocked", "")
    if reason == "missing_evidence":
        return "supply what is missing: %s" % ver.get("missing", "")
    return "fix it; the failure scenario still holds"


def still_open_lines(items, new_defects):
    out = []
    for it in items:
        if it.get("disposition") == "not_fixed" and "waived" not in it:
            out.append(ledger.SEP.join([it["severity"], "%s:%s" % (it["location"]["file"], it["location"]["line"]), it["claim"], needed_text(it)]))
    for d in new_defects:
        out.append(ledger.SEP.join([d["severity"], "%s:%s" % (d["location"]["file"], d["location"]["line"]), "broke: %s" % d["claim"]]))
    return out


def result_value(items, new_defects, violations):
    if violations:
        return "not_clear"
    open_items = [it for it in items if it.get("disposition") == "not_fixed" and "waived" not in it]
    if not open_items and not new_defects:
        return "all_clear"
    if any(it.get("disposition") == "fixed" for it in items):
        return "partial"
    return "not_clear"


def other_open_slices(parsed_after, entries_after, checklist_slices, waiver_slices=()):
    """`<slice>: <card>` for every slice outside the checklist that still holds an open BLOCKER or
    MAJOR entry, and for every slice named by an accepted waiver outside the checklist, with its
    unchanged card (E8-4)."""
    out = []
    for s in parsed_after["slices"]:
        if s["name"] in checklist_slices:
            continue
        open_bm = [e for e in entries_after if e["slice"] == s["name"] and e["state"] == "open" and e["severity"] in ("BLOCKER", "MAJOR")]
        if open_bm or s["name"] in waiver_slices:
            out.append("%s: %s" % (s["name"], s["card"]))
    return out


def waiver_slices(entries_after, waivers):
    """The slices of the entries the accepted waivers name (for other_open_slices, E8-4)."""
    out = set()
    for g in waivers:
        loc = g["item"]["location"]
        for e in ledger.find_entries(entries_after, loc["file"], loc["line"], g["item"]["claim"]):
            if e["slice"] != "none":
                out.add(e["slice"])
    return out


# ---- validation and delivery (lane contract section 5) --------------------------------------

def existing_valid_result(run_dir, schemas):
    """The result.json already in the run directory when it parses and passes the schema, else None."""
    path = os.path.join(run_dir, "result.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or validate.validate_result(doc, schemas):
        return None
    return doc


def deliver(result, run_dir, schemas, input_doc=None, workspace=None, chat_text=None, skill_root=None, stop_builder=None, keep_existing=False):
    """Validate (schema + semantic), write result.json, then chat.md. On failure write
    result.invalid.json beside the validator's output and end stopped (section 5); with
    keep_existing (a re-assembly after the commit point, E8-A11) a valid result.json already in
    the run directory is never overwritten by the stopped document: it and its chat.md stand, and
    the invalid assembly is kept beside them.
    Returns (final_result, result_path, chat_path)."""
    schema_errors = validate.validate_result(result, schemas)
    findings = []
    if not schema_errors:
        sem = validate.run_semantic(result, input_doc=input_doc, run_dir=run_dir, workspace=workspace, schemas=schemas)
        findings = sem["semantic"]
    if schema_errors or findings:
        invalid = os.path.join(run_dir, "result.invalid.json")
        report = os.path.join(run_dir, "result.invalid.validation.json")
        canon.atomic_write(invalid, (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        canon.atomic_write(report, (json.dumps({"schema": schema_errors, "semantic": findings}, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        first = ("%s %s" % (schema_errors[0]["path"], schema_errors[0]["message"])) if schema_errors else ("%s %s %s" % (findings[0]["id"], findings[0]["path"], findings[0]["message"]))
        path = os.path.join(run_dir, "result.json")
        if keep_existing:
            kept = existing_valid_result(run_dir, schemas)
            if kept is not None:
                chat = os.path.join(run_dir, "chat.md")
                if not os.path.isfile(chat):
                    chat = write_chat(run_dir, chat_block(kept))
                return kept, path, chat
        stopped = stop_builder("result failed validation: %s" % first, [invalid, report]) if stop_builder else {
            "protocol_version": 1, "status": "stopped", "stop_reason": "result failed validation: %s" % first}
        canon.atomic_write(path, (json.dumps(stopped, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        chat = write_chat(run_dir, chat_block(stopped))
        return stopped, path, chat
    path = os.path.join(run_dir, "result.json")
    canon.atomic_write(path, (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    chat = write_chat(run_dir, chat_text if chat_text is not None else chat_block(result))
    return result, path, chat


def write_chat(run_dir, text):
    path = os.path.join(run_dir, "chat.md")
    canon.atomic_write(path, text.encode("utf-8"))
    return path


# ---- the chat block (Appendix A) ------------------------------------------------------------

def _method_line(it):
    ver = it.get("verification") or {}
    m = ver.get("method")
    label = "executed" if m == "executed" else "static (%s)" % ver.get("static_reason", "")
    detail = (ver.get("evidence") or [{}])[0].get("detail", "")
    return "%s:%s %s: %s" % (it["location"]["file"], it["location"]["line"], label, detail)


def _record_line(it):
    disp = "fixed" if it.get("disposition") == "fixed" else "not fixed (%s)" % it.get("reason")
    return ledger.SEP.join([it["severity"], "%s:%s" % (it["location"]["file"], it["location"]["line"]),
                            "(%s)" % it["claim"] if it["claim"] != ledger.NO_CLAIM else "()", disp,
                            ledger.render_how(it.get("verification") or {"method": "executed", "evidence": []})])


def chat_block(result, extra=None):
    extra = extra or {}
    status = result.get("status")
    checklist = result.get("checklist") or {}
    slice_label = checklist.get("slice") or extra.get("slice") or "none"
    if status != "completed":
        run = result.get("run") or {}
        lines = ["RECHECK: %s — %s" % (slice_label, status.replace("_", " ").upper())]
        reason = result.get("stop_reason")
        if status == "missing_input":
            mi = result.get("missing_input") or {}
            reason = "missing: %s" % ", ".join(mi.get("fields") or [])
            if mi.get("ambiguity"):
                reason += "; " + "; ".join(mi["ambiguity"])
            if mi.get("question"):
                lines.append("Question: %s" % mi["question"])
        if reason:
            lines.append("Reason: %s" % reason)
        src = result.get("source_identity")
        if src:
            lines.append("Source: %s %s" % (src["actual"]["commit"], "dirty" if src["actual"]["dirty"] else "clean"))
        if result.get("rejected_grants"):
            lines.append("Rejected grants: " + "; ".join(result["rejected_grants"]))
        if run.get("run_dir"):
            lines.append("Run directory: %s" % run["run_dir"])
        return "\n".join(lines) + "\n"
    items = result.get("items") or []
    defects = result.get("new_defects") or []
    open_count = len([it for it in items if it.get("disposition") == "not_fixed" and "waived" not in it]) + len(defects)
    value = result.get("result")
    verdict = {"all_clear": "ALL CLEAR", "partial": "PARTIAL (%d open)" % open_count, "not_clear": "NOT CLEAR"}[value]
    cards = result.get("cards") or []
    if not cards:
        status_text = "no card"
    else:
        parts = []
        for c in cards:
            parts.append("%s → %s" % (c["before"], c["after"]) if c["before"] != c["after"] else "unchanged (%s)" % c["before"])
        status_text = "; ".join(parts) if len(parts) > 1 else parts[0]
    verdict_doc = extra.get("verdict_doc") or "none found, build doc only"
    sheet = {"read": "read — bar applied", "not_kit_sheet": "present but not the kit sheet — defaults", "absent": "absent — defaults"}[checklist.get("review_sheet", "absent")]
    src = result["source_identity"]["actual"]
    ver = (result.get("run") or {}).get("verifier") or {}
    injected = ", ".join(ver.get("injected_channels") or []) or "none"
    lines = ["RECHECK: %s — %d items (+%d new)" % (slice_label, len(items), len(defects)),
             "Result: %s · Status: %s" % (verdict, status_text),
             "Verdict doc: %s" % verdict_doc,
             "Review sheet: %s" % sheet,
             "Source: %s %s · Verifier: %s, %s · injected: %s" % (src["commit"], "dirty" if src["dirty"] else "clean", ver.get("kind", "unknown"), ver.get("model", "unknown"), injected),
             "Method: " + "; ".join(_method_line(it) for it in items), ""]
    fixed = len([it for it in items if it.get("disposition") == "fixed"])
    waived = len([it for it in items if "waived" in it])
    bottom = "%d of %d items fixed, %d still open, %d waived, %d fix-introduced defect(s)." % (fixed, len(items), open_count, waived, len(defects))
    if result.get("boundary_violations"):
        moved = [c["slice"] for c in cards if c.get("before") != c.get("after")]
        if moved:
            bottom += (" A boundary violation froze every remaining card; %s moved before it was found (E8-A44); "
                       "the run is not clear whatever the dispositions." % ", ".join(moved))
        else:
            bottom += " A boundary violation froze every card; the run is not clear whatever the dispositions."
    else:
        bottom += " Cards: %s." % status_text
    lines += ["Bottom line: %s" % bottom, ""]
    for it in items:
        lines.append(_record_line(it))
    for d in defects:
        lines.append(ledger.render_defect_line(d["severity"], d["location"]["file"], d["location"]["line"], d["claim"], d["failure_scenario"])[2:])
    lines.append("Still open: " + ("; ".join(result.get("still_open") or []) or "none"))
    lines.append("Other open slices: " + ("; ".join(result.get("other_open_slices") or []) or "none"))
    lines.append("Rejected grants: " + ("; ".join(result.get("rejected_grants") or []) or "none"))
    if result.get("skill_note"):
        lines.append("SKILL NOTE: %s" % result["skill_note"])
    return "\n".join(lines) + "\n"
