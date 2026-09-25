"""The result (brief 3.8) and the read-back rendered from it.

`build(...)` assembles `result.json`: the shared fields (station-loop.md section 5), the writes
copied from the receipt (every write with its hashes, the receipt and the result themselves
last), the selections the run used, and `station_result`. `write(...)` validates it against
`references/result.schema.json` and the semantic checks S1 to S4 before it lands; a result that
does not hold is a defect of this script (exit 1), never written. `chat(result)` is the read-back.
"""
import os

from station_core import fsio, validate

from .common import D, M, PREFIX
from .review import lane_of

NEXT = ("Next: point /sunrise at the doc to provision exactly what it lists, and /blueprint-v2 at it to "
        "slice with the user-touchable slice up front.")


class ResultInvalid(RuntimeError):
    pass


def empty_station_result():
    return {"doc_path": None, "run_number": None, "visual_path": None, "published": False, "artifact_url": None,
            "publish_outcome": "not-reached", "project": None, "slug": None, "scope_doc": None, "docless": None,
            "candidates": [], "pick": None, "rulings_count": 0, "review": None, "review_reason": None, "review_files": [],
            "review_failed_lanes": [], "passed_forward": [], "counts": None}


def selections(run_dir):
    out = {}
    for name in sorted(os.listdir(run_dir)):
        if name.startswith("selection-") and name.endswith(".json"):
            doc = fsio.read_json(os.path.join(run_dir, name))
            out[name[len("selection-"):-len(".json")]] = doc
    return out


def build(envelope, run, status, stop_tag, reason, station_result, receipt):
    run_dir = run.run_dir
    writes = [dict(w) for w in receipt.writes]
    receipt_path = os.path.join(run_dir, "receipt.json")
    if os.path.isfile(receipt_path):
        writes.append({"path": receipt_path, "kind": "run_artifact", "sha256_before": None,
                       "sha256_after": fsio.sha256_file(receipt_path)})
    result_path = os.path.join(run_dir, "result.json")
    writes.append({"path": result_path, "kind": "run_artifact",
                   "sha256_before": fsio.sha256_file_or_none(result_path), "sha256_after": None})
    outside = [w for w in writes if not fsio.inside(w["path"], run_dir)]
    doc = dict(envelope)
    doc.update({"run_id": run.checkpoint["run_id"], "run_dir": run_dir, "status": status, "stop_tag": stop_tag,
                "reason": reason, "report_only": bool(run.input.get("report_only")),
                "wrote_nothing": not outside, "writes": writes, "selection": selections(run_dir),
                "invocation": run.input["invocation"], "station_result": station_result})
    return doc


def write(doc, root=None):
    schema = validate.load_schema("result", PREFIX, root)
    errors = validate.errors_for(doc, schema, PREFIX)
    semantic = validate.semantic(doc) if not errors else []
    if errors or semantic:
        raise ResultInvalid("the result does not hold its schema: %s" % (errors or semantic)[:4])
    path = os.path.join(doc["run_dir"], "result.json")
    fsio.write_json(path, doc)
    return path


def chat(result):
    sr = result["station_result"]
    lines = ["ARCHITECT: %s" % (sr.get("project") or sr.get("slug") or "(no project)")]
    if sr.get("doc_path"):
        lines.append("Doc: %s" % sr["doc_path"])
        outcome = sr.get("publish_outcome")
        if outcome == "published":
            artifact = sr["artifact_url"]
        elif outcome == "skipped":
            artifact = "not published (publish: false)"
        elif outcome == "rendered-not-published":
            artifact = "rendered, not published (the publish returned no URL)"
        else:
            artifact = sr.get("artifact_url") or "not published"
        lines.append("Artifact: %s" % artifact)
        lines.append("Run: %s" % sr["run_number"])
        c = sr.get("counts") or {}
        lines.append("Counts: components in v0 %s %s poured-concrete decisions %s %s deferred items %s"
                     % (c.get("components", 0), M, c.get("poured", 0), M, c.get("deferred", 0)))
        review = sr.get("review")
        if review == "done":
            # v1's words: `done at <files>, with <lane> failed <dash> <reason>` after any lane that did not return
            failed = "".join(", with %s failed %s %s" % (lane_of(f["row"]), D, f["reason"])
                             for f in sr.get("review_failed_lanes") or [])
            lines.append("Review: done at %s%s" % (", ".join(sr["review_files"]), failed))
        elif review == "not-offered":
            lines.append("Review: not offered %s docless" % D)
        elif review == "failed":
            lines.append("Review: failed %s %s" % (D, sr.get("review_reason") or result["reason"]))
        elif review:
            lines.append("Review: %s" % review)
    if result["status"] == "stopped":
        lines.append("Stopped: %s: %s" % (result["stop_tag"], result["reason"]))
    elif sr.get("doc_path"):
        lines.append(NEXT)
    if result["report_only"]:
        lines.append("Report only: nothing was written outside the run directory.")
    return "\n".join(lines) + "\n"
