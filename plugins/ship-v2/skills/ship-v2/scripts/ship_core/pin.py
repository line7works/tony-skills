"""The pin: what the workspace held when a lap's fixing began, so `fix` sees every path the fixes touched (contract
section 3.5, "The pin").

    take(ws) -> {"head", "paths": {path: identity}}: HEAD and the identity of every changed or untracked path
    moved(ws, pin) -> [path]: every path whose identity moved since the pin, plus every path a commit since the pin's
        HEAD changes

A path's identity is its type, its mode and its content with lstat semantics (build-v2's source pin, build-contract
section 10): `file:<mode>:<sha256>`, `link:<sha256 of the target text>` (never followed), `dir`, or `missing`.
`docs/records/` is left out of both (the records component's own history: a waiver ship-v2 records mid-run, or a
station's events, are never a fix). Git runs read-only (`gitio.py`).
"""
import hashlib
import os
import stat

from . import gitio

EXCLUDED = ("docs/records/",)


def identity(ws, rel):
    path = os.path.join(ws, rel)
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return "missing"
    if stat.S_ISLNK(st.st_mode):
        return "link:%s" % hashlib.sha256(os.readlink(path).encode("utf-8", "surrogateescape")).hexdigest()
    if stat.S_ISDIR(st.st_mode):
        return "dir"
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return "file:%s:%s" % ("100755" if st.st_mode & stat.S_IXUSR else "100644", digest)


def _kept(rel):
    return not rel.startswith(EXCLUDED)


def take(ws):
    return {"head": gitio.head(ws), "paths": dict((rel, identity(ws, rel)) for rel in gitio.dirt(ws) if _kept(rel))}


def moved(ws, pin):
    """A path the pin holds moved when its identity on disk now differs from the pinned one (committed as it was is
    no move); a path clean at the pin moved when it is dirty now or a commit since the pin's HEAD changes it."""
    now = take(ws)
    candidates = set(pin["paths"]) | set(now["paths"])
    if now["head"] != pin["head"] and pin["head"] and now["head"]:
        candidates.update(rel for rel in gitio.changed_between(ws, pin["head"], now["head"]) if _kept(rel))
    out = []
    for rel in sorted(candidates):
        if rel in pin["paths"]:
            if identity(ws, rel) != pin["paths"][rel]:
                out.append(rel)
        else:
            out.append(rel)
    return out
