"""The back cores' additions to the shared case library (E15; a back-frame file, vertical-v2 canonical).

`caselib.py` (precon-v2's, byte for byte) builds a case's workspace as one commit. A back core's case
needs history and an untidy tree: a base on `main`, the build on a branch, the records log as the
records component wrote it, later commits, and uncommitted dirt. `install(caselib)` wraps
`caselib.build` so a spec may also carry, applied in this order after the base commit:

    "main_after": [{"files": {rel: text}, "message": "..."}]   more commits on main (the base's history)
    "branch": "feat"                                         a branch cut from main's tip, checked out
    "commits": [{"files": {rel: text}, "remove": [rel], "message": "..."}]   commits on the branch
    "dirt": {rel: text}                                      files written and never committed

A file text may hold `{REV:<ref>}`, replaced at build time by the full commit `<ref>` names in the case's
own repository (so a build doc can record a base that only exists once the case is built). Git runs only
inside the case's workspace, through `caselib._git`, with its fixed author, committer and date, so two
builds of one case give the same commits and the same tree hash; the manifest's `head` and
`tree_sha256` are recomputed after the additions. Standard library only, Python 3.9.
"""
import json
import os
import re

REV = re.compile(r"\{REV:([A-Za-z0-9._~^/-]+)\}")


def _fill(caselib, ws, text):
    return REV.sub(lambda m: caselib._git(ws, ["rev-parse", m.group(1)]).strip(), text)


def _write(caselib, ws, files):
    for rel, text in sorted(files.items()):
        caselib._write(caselib._inside(ws, rel), _fill(caselib, ws, text))


def _commit(caselib, ws, step):
    _write(caselib, ws, step.get("files") or {})
    for rel in step.get("remove") or []:
        os.remove(caselib._inside(ws, rel))
    caselib._git(ws, ["add", "-A"])
    caselib._git(ws, ["commit", "-q", "--allow-empty", "-m", step.get("message") or "a commit"])


def install(caselib):
    """Wrap `caselib.build` with the history and dirt steps above (idempotent)."""
    original = getattr(caselib.build, "_back_original", caselib.build)

    def build(out_dir, case_id, family, core, spec, answers_dir):
        case_dir, manifest = original(out_dir, case_id, family, core, spec, answers_dir)
        ws = os.path.join(case_dir, "workspace")
        for step in spec.get("main_after") or []:
            _commit(caselib, ws, step)
        if spec.get("branch"):
            caselib._git(ws, ["checkout", "-q", "-b", spec["branch"]])
        for step in spec.get("commits") or []:
            _commit(caselib, ws, step)
        _write(caselib, ws, spec.get("dirt") or {})
        manifest["head"] = caselib._git(ws, ["rev-parse", "HEAD"]).strip()
        manifest["tree_sha256"] = ""
        manifest["tree_sha256"] = caselib.tree_sha256(case_dir, os.path.abspath(out_dir))
        caselib._write_json(os.path.join(case_dir, "manifest.json"), manifest)
        return case_dir, manifest

    build._back_original = original
    caselib.build = build
    return caselib
