"""Verify and adjudicate, the mechanical half (contract section 7; v1's Step 4).

The script never judges a finding (ruling E14-4). What it does is mechanical and stated:

- **A citation is checked against the numbered packet** of the call's lens, and only against the
  documents that call's request carried (the paper call's `packet.md` carries all three); a
  repo-reality finding may also cite a workspace file, never one under `docs/records/` (the records
  log is read through the component only). `<file>:<line>` or `<file>:<line>-<line>`; the file must be one
  the packet holds (or, for repo reality, a regular file inside the workspace), every cited line
  must exist, and at least one must carry text. A citation that matches nothing is a refutation,
  counted, never raised. When the finding quotes the cited text (`quote`), a line that does not
  carry it is a refutation. A citation that holds establishes only that the cited text exists,
  never that the claim is true (round 5, R1).
- **The executor's adjudication decides the label** (round 5, R1; ruling E14-4: the script does the
  mechanics, the executor judges). Every finding that is verified (below) and whose citation holds
  carries an adjudication (`confirmed`, `plausible`, `refuted` or `question`, with its why) before
  it survives; `record-answer` refuses a missing one (`missing-adjudication`, `unadjudicated`
  here). CONFIRMED and PLAUSIBLE come from that adjudication and from nothing else: a quote the
  line carries is never a confirmation.
- **Which findings are verified** (v1): every outside finding, every severity; every Claude-lane
  BLOCKER and MAJOR. A Claude-lane MINOR or QUESTION passes UNVERIFIED (v1: "Claude-lane MINORs
  pass through unverified"): its claim is nobody's to confirm, but its citation is still checked,
  because what reaches the records log or a QUESTION line must name a place in the workspace; one
  whose citation matches nothing is refuted and counted like any other.
- **A finding with no location** never reaches the result; it is counted `locationless`.
- **The no-record rule**: with no scope doc, every finding of the traceability lens (and every
  paper-call finding the reply marks `lens: traceability`) becomes a QUESTION note, never a
  BLOCKER; so does any finding of severity QUESTION, and any the executor adjudicates `question`.
  A finding citing `no-record.md` (the NO RECORD line itself) is a QUESTION whatever its lens,
  written `no-scope-doc:<line>`: every packet file maps to the document it stands for (`translate`),
  and one that stands for none (a file the packet does not hold, an unknown name) is refuted. The
  rule's QUESTION notes (`mechanical_question`) need no adjudication: nothing in a missing record
  can be verified, which is why the rule makes them questions.
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

# every file a lens packet can hold, each standing for one document (round 3, R2); `no-record.md` stands
# for the scope doc's absence, written `no-scope-doc:<line>`, never a packet file name
PACKET_FILES = ("build-doc.md", "scope-doc.md", "no-record.md", "code-book.md")
NO_SCOPE_DOC = "no-scope-doc"
CODE_BOOK_AS_WRITTEN = "skills/blueprint-v2/SKILL.md"
LOCATION = re.compile(r"^(?P<file>[^:\s][^:]*?):(?P<start>\d+)(?:\s*[-\u2013]\s*(?P<end>\d+))?$")
ORDER = {"BLOCKER": 3, "MAJOR": 2, "MINOR": 1, "QUESTION": 0}
LABEL_ORDER = {"CONFIRMED": 2, "PLAUSIBLE": 1, "UNVERIFIED": 0}
SEP = " · "


class UnadjudicatedFinding(Exception):
    """A verified finding reached triage without the executor's adjudication: a defect, never a label."""


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


def _is_a_records_file(target, records):
    """Whether `target` is, by real path or by file identity, a file under the records folder: a file
    symlink resolves into it, a hard link shares a file's inode (round 3, R3, CI1-7)."""
    if not os.path.exists(target):
        return False
    if fsio.inside(os.path.realpath(target), os.path.realpath(records)):
        return True
    if not os.path.isfile(target):
        return False
    for base, _dirs, files in os.walk(records):
        for name in files:
            try:
                if os.path.samefile(target, os.path.join(base, name)):
                    return True
            except OSError:
                continue
    return False


def in_records(workspace, rel):
    """Whether a workspace-relative path lies in the records component's folder (`docs/records/`),
    however it is spelled or reached (`./`, a folder link, another letter case, a file symlink, a hard
    link): the log is read through the component's CLI only, never opened by a citation check
    (contract section 12)."""
    records = os.path.join(workspace, "docs", "records")
    if not os.path.isdir(records):
        return False
    if _is_a_records_file(os.path.normpath(os.path.join(workspace, rel)), records):
        return True
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
    if loc["file"] in PACKET_FILES and loc["file"] not in names:
        # a packet file this packet does not hold (`scope-doc.md` in a no-record run, `no-record.md`
        # beside a scope doc) matches nothing, for every lens, repo reality included (round 3, R2)
        return False, "the packet holds no %s (it holds %s)" % (loc["file"], ", ".join(names)), None
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


def outside_call(lens, packet):
    """Whether a call is an outside row's (its paper call; its repo-reality call is a Claude lane)."""
    return packet["provider"] != common.ANTHROPIC and lens == "paper"


def verified(finding, lens, packet):
    """v1's verify set: every outside finding of every severity, every Claude-lane BLOCKER and MAJOR."""
    return outside_call(lens, packet) or finding["severity"] in ("BLOCKER", "MAJOR")


def mechanical_question(finding, lens, where, no_record):
    """Whether the no-record rule makes this finding a QUESTION note by itself: it cites the NO RECORD
    line (`no-record.md`), or, with no scope doc, it is a traceability item."""
    absent = where["kind"] == "packet" and where["file"] == "no-record.md"
    return absent or (no_record and (lens == "traceability" or
                                     (lens == "paper" and finding.get("lens") == "traceability")))


def unadjudicated(answer, requests, harvest, packet, workspace):
    """Round 5, R1: the ids (`<call id>#<n>`) of every finding that must carry the executor's
    adjudication and carries none: a verified finding (`verified`) with a location whose citation holds
    and names a document of this run, and which the no-record rule does not turn into a QUESTION note by
    itself. An invalid citation (refuted mechanically) and a locationless concern (excluded) need none.
    Only results of calls this run built are read."""
    built = dict((c["call_id"], c) for c in requests["calls"])
    dir_of = dict((d["lens"], d["dir"]) for d in packet["dirs"])
    judged = set(a["finding"] for a in answer.get("adjudications") or [])
    out = []
    for result in answer["results"]:
        call = built.get(result["call_id"])
        if call is None:
            continue
        for index, f in enumerate(result["findings"], 1):
            fid = "%s#%d" % (result["call_id"], index)
            if fid in judged or not (f.get("location") or "").strip() or not verified(f, call["lens"], packet):
                continue
            ok, _, where = check_citation(f, dir_of.get(call["lens"]), call["lens"], workspace, carried(call))
            if not ok or translate(where, harvest) is None:
                continue
            if mechanical_question(f, call["lens"], where, harvest["no_record"]):
                continue
            out.append({"finding": fid, "call_id": result["call_id"], "severity": f["severity"],
                        "location": f["location"], "outside": outside_call(call["lens"], packet)})
    return out


def carried(call):
    """The packet files a call's request carried, or None for the paper call (its `packet.md` holds
    all three numbered documents)."""
    if call["lens"] == "paper":
        return None
    return list(call.get("documents") or [])


def translate(where, harvest):
    """A packet or repo location as the document it names (round 3, R2), or None when the packet file
    stands for no document of this run: `build-doc.md` -> the build doc's workspace path;
    `scope-doc.md` -> the scope doc's label (None in a no-record run); `no-record.md` -> `no-scope-doc`,
    the scope doc's absence (None beside a scope doc); `code-book.md` -> `skills/blueprint-v2/SKILL.md`;
    any other packet name -> None. A repo location is the workspace path it already is."""
    span = "%d" % where["start"] if where["start"] == where["end"] else "%d-%d" % (where["start"], where["end"])
    name = where["file"]
    if where["kind"] == "packet":
        scope = harvest.get("scope_doc")
        if name == "build-doc.md":
            name = harvest["build_doc"]["rel"]
        elif name == "scope-doc.md" and scope:
            name = scope["label"]
        elif name == "no-record.md" and not scope:
            name = NO_SCOPE_DOC
        elif name == "code-book.md":
            name = CODE_BOOK_AS_WRITTEN
        else:
            return None
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
            checked = verified(f, lens, packet) or (adj is not None and adj["decision"] in ("confirmed", "plausible"))
            ok, why, where = check_citation(f, dir_of.get(lens), lens, workspace, docs_of[call_id])
            if not ok:
                # a citation that matches nothing is refuted and counted, whatever the severity: nothing
                # reaches the records log or a QUESTION line without a place in the workspace (R5)
                refuted.append({"call_id": call_id, "finding": fid, "location": f["location"], "why": why})
                continue
            location = translate(where, harvest)
            if location is None:
                refuted.append({"call_id": call_id, "finding": fid, "location": f["location"],
                                "why": "%s stands for no document of this run" % where["file"]})
                continue
            model = result["effective_model"]
            absent = where["kind"] == "packet" and where["file"] == "no-record.md"
            if adj is not None and adj["decision"] == "refuted":
                refuted.append({"call_id": call_id, "finding": fid, "location": location,
                                "why": "the executor refuted it: %s" % adj["why"]})
                continue
            to_question = mechanical_question(f, lens, where, no_record) or f["severity"] == "QUESTION" or \
                (adj is not None and adj["decision"] == "question")
            if to_question:
                if absent:
                    # the finding cites the NO RECORD line itself: a question naming the scope doc's absence,
                    # whatever its lens or severity, never raised, never a packet file name (round 3, R2)
                    why = "the no-record rule: the finding cites the NO RECORD line, not a place in a document"
                    what = "no scope doc exists for this feature: %s" % f["claim"]
                else:
                    why = adj["why"] if adj is not None and adj["decision"] == "question" else (
                        "the no-record rule: unverifiable, needs confirmation" if no_record and
                        f["severity"] != "QUESTION" else "unverifiable against a missing or silent record")
                    what = f["claim"]
                questions.append({"location": location, "what": what, "model": model, "call_id": call_id,
                                  "why": why})
                continue
            if not checked:
                label = "UNVERIFIED"
            elif adj is not None and adj["decision"] in ("confirmed", "plausible"):
                # round 5, R1: the label is the executor's adjudication, never a quote the line carries
                label = adj["decision"].upper()
            else:
                raise UnadjudicatedFinding("%s reached triage verified and unadjudicated: record-answer refuses "
                                           "that (missing-adjudication) before anything is triaged" % fid)
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
