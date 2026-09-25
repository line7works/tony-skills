"""Verify and adjudicate, the mechanical half (contract section 7; v1's Step 4).

The script never judges a finding (ruling E14-4). What it does is mechanical and stated:

- **A citation is checked against the numbered packet** of the call's lens, and only against the
  documents that call's request carried (the paper call's `packet.md` carries all three); a
  repo-reality finding may also cite a workspace file, never one under `docs/records/` (the records
  log is read through the component only). `<file>:<line>` or `<file>:<line>-<line>`; the file must be one
  the packet holds (or, for repo reality, a regular file inside the workspace), every cited line
  must exist, and at least one must carry text. A citation that matches nothing is a refutation,
  counted, never raised. When the finding quotes the cited text (`quote`), a line that carries it
  is CONFIRMED and one that does not is a refutation; with no quote the finding is PLAUSIBLE until
  the executor's adjudication says `confirmed`.
- **Which findings are verified** (v1): every outside finding, every severity; every Claude-lane
  BLOCKER and MAJOR. A Claude-lane MINOR or QUESTION passes UNVERIFIED (v1: "Claude-lane MINORs
  pass through unverified"): its claim is nobody's to confirm, but its citation is still checked,
  because what reaches the records log or a QUESTION line must name a place in the workspace; one
  whose citation matches nothing is refuted and counted like any other.
- **A finding with no location** never reaches the result; it is counted `locationless`.
- **The no-record rule**: with no scope doc, every finding of the traceability lens (and every
  paper-call finding the reply marks `lens: traceability`) becomes a QUESTION note, never a
  BLOCKER; so does any finding of severity QUESTION, and any the executor adjudicates `question`.
- **Dedupe** on location and claim (whitespace collapsed, case folded): one finding, the highest
  severity, the call ids that converged on it listed once.
- **The verdict** is arithmetic over the surviving severities (v1's mapping, signoff-v2's
  contract section 7 in plan-check words): any BLOCKER is REJECTED; else any MAJOR is APPROVED WITH
  CONDITIONS; else APPROVED. Questions never gate.
"""
import os
import re

from station_core import fsio

from . import common

LOCATION = re.compile(r"^(?P<file>[^:\s][^:]*?):(?P<start>\d+)(?:\s*[-\u2013]\s*(?P<end>\d+))?$")
ORDER = {"BLOCKER": 3, "MAJOR": 2, "MINOR": 1, "QUESTION": 0}
LABEL_ORDER = {"CONFIRMED": 2, "PLAUSIBLE": 1, "UNVERIFIED": 0}
SEP = " · "


def verdict(findings):
    severities = set(f["severity"] for f in findings)
    if "BLOCKER" in severities:
        return "REJECTED"
    if "MAJOR" in severities:
        return "APPROVED WITH CONDITIONS"
    return "APPROVED"


def _norm(text):
    return " ".join((text or "").replace("`", "").split()).casefold()


def parse_location(raw):
    if not isinstance(raw, str):
        return None
    match = LOCATION.match(raw.strip().strip("`").strip())
    if not match:
        return None
    start = int(match.group("start"))
    end = int(match.group("end")) if match.group("end") else start
    return {"file": match.group("file").strip("`"), "start": start, "end": end}


def packet_lines(folder, name):
    """{number: text} of one numbered packet file (the `N: ` prefix removed)."""
    out = {}
    with open(os.path.join(folder, name), encoding="utf-8") as fh:
        for raw in fh.read().split("\n"):
            head, sep, rest = raw.partition(": ")
            if sep and head.isdigit():
                out[int(head)] = rest
    return out


def workspace_lines(workspace, rel):
    if os.path.isabs(rel) or ".." in rel.replace("\\", "/").split("/"):
        return None
    path = os.path.join(workspace, rel)
    if not os.path.isfile(path) or not fsio.inside(path, workspace):
        return None
    try:
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return dict((i, l.rstrip("\r")) for i, l in enumerate(lines, 1))


def in_records(workspace, rel):
    """Whether a workspace-relative path lies in the records component's folder (`docs/records/`),
    however it is spelled (`./`, a link, another letter case): the log is read through the component's
    CLI only, never opened by a citation check (contract section 12)."""
    records = os.path.join(workspace, "docs", "records")
    if not os.path.isdir(records):
        return False
    here = os.path.dirname(os.path.normpath(os.path.join(workspace, rel)))
    while fsio.inside(here, workspace):
        if os.path.exists(here) and os.path.samefile(here, records):
            return True
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return False


def check_citation(finding, lens_dir, lens, workspace, documents=None):
    """(ok, why, where): where is {"kind": "packet"|"repo", "file", "start", "end"}. `documents` names
    the packet files the call's request carried (None: every file of the lens's packet, as the paper
    call's `packet.md` carries all three); a citation of any other packet file matches nothing."""
    loc = parse_location(finding.get("location"))
    if loc is None:
        return False, "the location %r names no <file>:<line>" % finding.get("location"), None
    names = sorted(os.listdir(lens_dir)) if lens_dir and os.path.isdir(lens_dir) else []
    if loc["file"] in names and documents is not None and loc["file"] not in documents:
        return False, "%s is not among the documents the %s request carried (%s)" % (
            loc["file"], lens, ", ".join(documents)), None
    if loc["file"] in names:
        lines, kind = packet_lines(lens_dir, loc["file"]), "packet"
    elif lens == "repo-reality" and not os.path.isabs(loc["file"]) and in_records(workspace, loc["file"]):
        return False, "%s is in the records log, which is read through the records component only, never " \
                      "by a citation check" % loc["file"], None
    elif lens == "repo-reality":
        lines, kind = workspace_lines(workspace, loc["file"]), "repo"
        if lines is None:
            return False, "%s is no file of the workspace" % loc["file"], None
    else:
        return False, "%s is not in the packet (it holds %s)" % (loc["file"], ", ".join(names)), None
    if loc["end"] < loc["start"]:
        return False, "the range %d-%d runs backwards" % (loc["start"], loc["end"]), None
    count = max(lines) if lines else 0
    if loc["start"] < 1 or loc["end"] > count:
        return False, "line %d is past the end of %s (%d lines)" % (loc["end"] if loc["end"] > count else loc["start"],
                                                                     loc["file"], count), None
    cited = [lines.get(n, "") for n in range(loc["start"], loc["end"] + 1)]
    if not any(line.strip() for line in cited):
        return False, "the cited line of %s is blank" % loc["file"], None
    quote = finding.get("quote")
    where = dict(loc, kind=kind)
    if quote is not None and not any(quote in line for line in cited):
        return False, "the cited line does not carry the quoted text %r" % quote, None
    return True, None, where


def carried(call):
    """The packet files a call's request carried, or None for the paper call (its `packet.md` holds
    all three numbered documents)."""
    if call["lens"] == "paper":
        return None
    return list(call.get("documents") or [])


def translate(where, harvest):
    """A packet or repo location as the document it names: `build-doc.md:12` -> `<build doc>:12`."""
    span = "%d" % where["start"] if where["start"] == where["end"] else "%d-%d" % (where["start"], where["end"])
    name = where["file"]
    if where["kind"] == "packet":
        if name == "build-doc.md":
            name = harvest["build_doc"]["rel"]
        elif name == "scope-doc.md" and harvest.get("scope_doc"):
            name = harvest["scope_doc"]["label"]
        elif name == "code-book.md":
            name = "skills/blueprint-v2/SKILL.md"
    return "%s:%s" % (name, span)


def slice_of(where, harvest):
    if where is None or where["kind"] != "packet" or where["file"] != "build-doc.md":
        return "plan"
    for s in harvest.get("slices") or []:
        if s["start"] <= where["start"] <= s["end"]:
            return s["name"]
    return "plan"


def triage(answer, requests, harvest, packet, workspace):
    """The whole mechanical pass; returns the triage document `record-answer` writes."""
    lens_of = dict((c["call_id"], c["lens"]) for c in requests["calls"])
    docs_of = dict((c["call_id"], carried(c)) for c in requests["calls"])
    dir_of = dict((d["lens"], d["dir"]) for d in packet["dirs"])
    outside = packet["provider"] != common.ANTHROPIC
    adjudications = dict((a["finding"], a) for a in answer.get("adjudications") or [])
    no_record = harvest["no_record"]
    survivors, questions, refuted, locationless = [], [], [], []
    calls = []
    for result in answer["results"]:
        call_id = result["call_id"]
        lens = lens_of[call_id]
        calls.append({"call_id": call_id, "lens": lens, "row": result["row"],
                      "effective_model": result["effective_model"], "status": result.get("status", "ok"),
                      "authorized": next(c["authorized"] for c in requests["calls"] if c["call_id"] == call_id)})
        for index, f in enumerate(result["findings"], 1):
            fid = "%s#%d" % (call_id, index)
            adj = adjudications.get(fid)
            if not (f.get("location") or "").strip():
                # null or blank: a concern without location never reaches the result
                locationless.append({"finding": fid, "claim": f["claim"]})
                continue
            outside_call = outside and lens == "paper"
            checked = outside_call or f["severity"] in ("BLOCKER", "MAJOR") or \
                (adj is not None and adj["decision"] in ("confirmed", "plausible"))
            ok, why, where = check_citation(f, dir_of.get(lens), lens, workspace, docs_of[call_id])
            if not ok:
                # a citation that matches nothing is refuted and counted, whatever the severity: nothing
                # reaches the records log or a QUESTION line without a place in the workspace (R5)
                refuted.append({"call_id": call_id, "finding": fid, "location": f["location"], "why": why})
                continue
            location = translate(where, harvest)
            model = result["effective_model"]
            if adj is not None and adj["decision"] == "refuted":
                refuted.append({"call_id": call_id, "finding": fid, "location": location,
                                "why": "the executor refuted it: %s" % adj["why"]})
                continue
            to_question = f["severity"] == "QUESTION" or (adj is not None and adj["decision"] == "question") or \
                (no_record and (lens == "traceability" or (lens == "paper" and f.get("lens") == "traceability")))
            if to_question:
                why = adj["why"] if adj is not None and adj["decision"] == "question" else (
                    "the no-record rule: unverifiable, needs confirmation" if no_record and f["severity"] != "QUESTION"
                    else "unverifiable against a missing or silent record")
                questions.append({"location": location, "what": f["claim"], "model": model, "call_id": call_id,
                                  "why": why})
                continue
            if not checked:
                label = "UNVERIFIED"
            elif adj is not None and adj["decision"] == "confirmed":
                label = "CONFIRMED"
            elif adj is not None and adj["decision"] == "plausible":
                label = "PLAUSIBLE"
            else:
                label = "CONFIRMED" if f.get("quote") is not None else "PLAUSIBLE"
            survivors.append({"severity": f["severity"], "label": label, "location": location, "claim": f["claim"],
                              "scenario": f["scenario"], "slice": slice_of(where, harvest), "raised_by": model,
                              "call_id": call_id, "converged": [call_id], "finding_id": None})
    survivors = _dedupe(survivors)
    questions = _dedupe_questions(questions)
    counts = {"blocker": sum(1 for s in survivors if s["severity"] == "BLOCKER"),
              "major": sum(1 for s in survivors if s["severity"] == "MAJOR"),
              "minor": sum(1 for s in survivors if s["severity"] == "MINOR"),
              "confirmed": sum(1 for s in survivors if s["label"] == "CONFIRMED"),
              "plausible": sum(1 for s in survivors if s["label"] == "PLAUSIBLE"),
              "unverified": sum(1 for s in survivors if s["label"] == "UNVERIFIED"),
              "refuted": len(refuted), "questions": len(questions), "locationless": len(locationless)}
    requested = [c["lens"] for c in requests["calls"]]
    ran = set(lens_of[r["call_id"]] for r in answer["results"])
    return {"findings": survivors, "questions": questions, "refuted": refuted, "locationless": locationless,
            "survivors": survivors, "counts": counts, "verdict": verdict(survivors), "weaker": no_record,
            "no_record": no_record, "calls": calls, "lenses_not_run": [l for l in requested if l not in ran],
            "hunted_and_held": answer["hunted_and_held"], "bottom_line": answer["bottom_line"]}


def _dedupe(rows):
    merged, order = {}, []
    for row in rows:
        key = (_norm(row["location"]), _norm(row["claim"]))
        if key not in merged:
            merged[key] = row
            order.append(key)
            continue
        kept = merged[key]
        if ORDER[row["severity"]] > ORDER[kept["severity"]]:
            row["converged"] = kept["converged"] + [c for c in row["converged"] if c not in kept["converged"]]
            if LABEL_ORDER[kept["label"]] > LABEL_ORDER[row["label"]]:
                row["label"] = kept["label"]
            merged[key] = row
        else:
            kept["converged"] += [c for c in row["converged"] if c not in kept["converged"]]
            if LABEL_ORDER[row["label"]] > LABEL_ORDER[kept["label"]]:
                kept["label"] = row["label"]
    return [merged[k] for k in order]


def _dedupe_questions(rows):
    seen, out = set(), []
    for row in rows:
        key = (_norm(row["location"]), _norm(row["what"]))
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def paper_models(answer, requests):
    """The effective models of the paper calls (the stamp's model, v1 Step 5)."""
    lens_of = dict((c["call_id"], c["lens"]) for c in requests["calls"])
    return sorted(set(r["effective_model"] for r in answer["results"]
                      if lens_of.get(r["call_id"]) in common.PAPER_LENSES))
