"""The `BLUEPRINT:` read-back block, rendered from the result (contract section 10).

v1's block, line for line, with two readings: `Next:` names the v2 build station, and a run whose
owner collapsed the gate says so with his words. A stop renders its tag and its reason; the
no-build-doc stop renders the executor's why with the open questions and the assumptions.
"""
import os

M = "·"
D = "\u2014"


def _rel(path, workspace):
    if not path:
        return "-"
    try:
        return os.path.relpath(path, workspace)
    except ValueError:
        return path


def render(sr, workspace, report_only=False, stop_tag=None, reason=None, open_items=(), assumed=()):
    feature = sr.get("feature") or "-"
    lines = ["BLUEPRINT: %s" % feature]
    if stop_tag == "no-build-doc":
        lines.append("No build doc: %s" % (sr.get("why") or reason))
    elif stop_tag:
        lines.append("Stopped: %s" % stop_tag)
        lines.append(reason or "")
        return "\n".join(lines)
    else:
        lines.append("Doc: %s  %s  Slices: %d  %s  Open questions: %d  %s  Assumptions: %d" % (
            _rel(sr.get("doc"), workspace), M, sr["slices"], M, sr["open_questions"], M, sr["assumptions"]))
        if report_only:
            lines.append("This run is report-only: nothing was written; the doc above is what write would produce "
                         "(proposed-build-doc.md in the run directory).")
        lines.append("")
        for name, short in sr.get("slice_titles") or []:
            lines.append("Slice %s %s %s" % (name, D, short))
        lines.append("")
    for item in open_items:
        lines.append("Open: %s" % item)
    for item in assumed:
        lines.append("Assumed: %s" % item)
    if sr.get("collapsed_gate"):
        lines.append("Gate collapsed by the owner's words: %s" % sr["collapsed_gate"])
    if stop_tag is None and sr.get("new_slices"):
        lines.append("Next: build-v2 slice %s when ready." % sr["new_slices"][0])
    return "\n".join(lines)
