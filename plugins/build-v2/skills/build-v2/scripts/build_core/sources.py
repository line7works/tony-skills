"""The source set: what this slice touched, computed from git and never guessed.

Lane contract section 8, restated in lane B's brief: three lists plus the base.

    committed   `git diff --name-only <base>..HEAD`
    changed     `git diff --name-only HEAD`  (staged or not, against HEAD)
    untracked   `git ls-files --others --exclude-standard`  (ignored files are not in it)

ONE prefix is excluded from all three lists, and `excluded` publishes it: `docs/records/`
(CR-3), the records component's own history, never source this build touched. The component
excludes exactly that prefix from the identity it computes, so the two agree.

The ledger document this run is executing is NOT excluded. It stays in the set, because section
8 is the truth of what changed and a reader must see that the build doc moved. It is instead
SANCTIONED for the scope comparison: `sanctioned` names it with the reason, and `scope.py` never
lists a sanctioned path as out of scope. The loop writes into that document by design — v1
build's step 5 has the executor write its assumptions, deviations and discoveries there, and
`report` writes the slice's `Status:` line — so the scope stop would otherwise fire on a change
the loop itself sanctions, on every run after the first. Sanctioning says so out loud; excluding
would have hidden it. (Lane B question 3, ruled by the control room in the first check round:
"keep it IN the source set, but make it a SANCTIONED path".)

A set that cannot be computed — no git, no such base — is a STOP with a reason, never a guess.

Git runs read-only and only inside the workspace, under the same clean configuration the pilot
and the component use (`GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, LANG C, TZ UTC,
the same `-c` flags), so no user configuration changes what is reported.

The six-field source identity is NOT computed here. It is read from the component
(`records.py identity`), which is the identity `append` compares a clear against, so there is
one computation and no second one to drift from it. `EXCLUDED_PREFIXES` below is held against
the component's published `excluded` list by a test.
"""
import os
import subprocess

EXCLUDED_PREFIXES = ("docs/records/",)
EXCLUDED_PATHSPECS = tuple(p.rstrip("/") for p in EXCLUDED_PREFIXES)

GIT_CONFIG_ARGS = [
    "-c", "core.hooksPath=/dev/null",
    "-c", "commit.gpgsign=false",
    "-c", "core.autocrlf=false",
    "-c", "core.fileMode=true",
]


class GitError(RuntimeError):
    """A git command inside the workspace failed, or the workspace is not one."""


def _git_env():
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/"),
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _exclude_args():
    return [":(exclude)" + p for p in EXCLUDED_PATHSPECS]


def git(cwd, args, binary=False, check=True):
    """One read-only git command inside cwd; stdout (bytes when binary), or None when it failed
    and `check` is off."""
    try:
        proc = subprocess.run(["git"] + GIT_CONFIG_ARGS + list(args), cwd=cwd, env=_git_env(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:  # git is not on PATH at all
        if check:
            raise GitError("git could not be run in %s: %s" % (cwd, exc))
        return None
    if proc.returncode != 0:
        if check:
            raise GitError("git %s failed (%d): %s" % (
                " ".join(args), proc.returncode, proc.stderr.decode("utf-8", "replace").strip()))
        return None
    return proc.stdout if binary else proc.stdout.decode("utf-8")


def is_work_tree_root(path):
    """(ok, reason): the path exists, is a git work tree root, and has a HEAD commit."""
    if not os.path.isdir(path):
        return False, "does not exist or is not a directory"
    top = git(path, ["rev-parse", "--show-toplevel"], check=False)
    if top is None:
        return False, "is not inside a git work tree"
    if os.path.realpath(top.strip()) != os.path.realpath(path):
        return False, "is not the root of its git work tree (%s)" % top.strip()
    if git(path, ["rev-parse", "--verify", "HEAD^{commit}"], check=False) is None:
        return False, "has no HEAD commit"
    return True, ""


def resolve_base(workspace, ref):
    """The 40-hex commit `ref` names, or None. A ref that does not resolve is a stop, never a guess."""
    out = git(workspace, ["rev-parse", "--verify", "--quiet", "%s^{commit}" % ref], check=False)
    if out is None or not out.strip():
        return None
    return out.strip()


def _paths(raw):
    """Sorted, de-duplicated workspace-relative paths from a NUL-separated git list."""
    return sorted(set(p.decode("utf-8") for p in raw.split(b"\0") if p))


def excluded(path):
    return any(path == p.rstrip("/") or path.startswith(p) for p in EXCLUDED_PREFIXES)


SANCTIONED_REASON = ("the ledger document this run is executing: the loop writes into it by "
                     "design, and this core writes the slice's `Status:` line there, so a change "
                     "to it is never out of scope")


def source_set(workspace, base_ref, document=None):
    """The three lists and the base, or raise GitError naming what could not be computed.

    Every list is sorted and workspace-relative, and `docs/records/` is excluded from each.
    `document`, the ledger document this run executes, stays IN the lists and is named in
    `sanctioned` with its reason: the scope comparison passes over it, and a reader still sees
    that it changed.
    """
    ok, why = is_work_tree_root(workspace)
    if not ok:
        raise GitError("the workspace %s %s, so the source set cannot be computed" % (workspace, why))
    base_commit = resolve_base(workspace, base_ref)
    if base_commit is None:
        raise GitError("the base ref %r does not resolve to a commit in %s, so the source set "
                       "cannot be computed" % (base_ref, workspace))
    head = git(workspace, ["rev-parse", "HEAD"]).strip()
    excludes = _exclude_args()
    committed = _paths(git(workspace, ["diff", "--name-only", "-z", "%s..HEAD" % base_commit,
                                       "--", "."] + excludes, binary=True))
    changed = _paths(git(workspace, ["diff", "--name-only", "-z", "HEAD", "--", "."]
                         + excludes, binary=True))
    untracked = _paths(git(workspace, ["ls-files", "--others", "--exclude-standard", "-z",
                                       "--", "."] + excludes, binary=True))
    return {
        "base": base_ref,
        "base_commit": base_commit,
        "head": head,
        "committed": committed,
        "changed": changed,
        "untracked": untracked,
        "excluded": list(EXCLUDED_PREFIXES),
        "sanctioned": ([{"path": document, "reason": SANCTIONED_REASON}] if document else []),
    }


def sanctioned_paths(source):
    """The paths the scope comparison passes over, as a set."""
    return set(row["path"] for row in (source or {}).get("sanctioned") or [])


def all_paths(source):
    """Every path of the set, once, sorted: what the scope comparison runs over.

    A set that was never computed (a run that stopped before preflight) has no paths, which is
    not the same as a run whose set was empty; the caller knows which it has from the result's
    `source_set` being absent.
    """
    source = source or {}
    return sorted(set(source.get("committed") or []) | set(source.get("changed") or [])
                  | set(source.get("untracked") or []))


def lists_holding(source, path):
    """Which of the three lists a path is in, in a fixed order."""
    return [name for name in ("committed", "changed", "untracked")
            if path in ((source or {}).get(name) or [])]


# ---- the source pin (Astra's F1, E13 full review) ----------------------------------------------

MISSING = "missing"


def _lstat_digest(full):
    """The identity of one path, with lstat semantics: its type, the mode git records for it, and
    its content. A symlink is `link:` and the digest of its link target text and is never
    followed; a regular file is `file:100644:` or `file:100755:` (the executable bit git keeps,
    punch-F1) and the digest of its bytes; a directory (a file replaced by one, or a nested
    repository git lists as a directory) is `dir`; a missing path is `missing`, never None, so a
    deleted path in the pin never compares equal to a path that has left the set (punch-F1: a
    tracked deletion restored between the kill and the resume)."""
    import hashlib
    import stat as statmod
    try:
        st = os.lstat(full)
    except FileNotFoundError:
        return MISSING
    if statmod.S_ISLNK(st.st_mode):
        return "link:" + hashlib.sha256(os.readlink(full).encode("utf-8", "surrogateescape")).hexdigest()
    if statmod.S_ISDIR(st.st_mode):
        return "dir"
    if not statmod.S_ISREG(st.st_mode):
        return "other:%o" % statmod.S_IFMT(st.st_mode)
    mode = "100755" if st.st_mode & statmod.S_IXUSR else "100644"
    with open(full, "rb") as fh:
        return "file:%s:%s" % (mode, hashlib.sha256(fh.read()).hexdigest())


def source_pin(workspace, document):
    """The source state a build decision was made on: HEAD, and the content identity of every path
    that differs from HEAD (changed or untracked, not ignored), `docs/records/` and the ledger
    document excluded. The document is this transaction's own receipted target, guarded by its
    pinned hashes; the log is the component's. Raises GitError when git cannot answer."""
    head = git(workspace, ["rev-parse", "HEAD"]).strip()
    excludes = _exclude_args()
    changed = _paths(git(workspace, ["diff", "--name-only", "-z", "HEAD", "--", "."] + excludes,
                         binary=True))
    untracked = _paths(git(workspace, ["ls-files", "--others", "--exclude-standard", "-z",
                                       "--", "."] + excludes, binary=True))
    paths = {}
    for path in sorted(set(changed) | set(untracked)):
        if path == document or excluded(path):
            continue
        paths[path] = _lstat_digest(os.path.join(workspace, path))
    return {"head": head, "paths": paths}


def pin_moved(workspace, document, pin):
    """The sorted paths whose state moved since `pin`, or [] when none did. A path added to or
    dropped from the set moved, a path whose content identity differs moved, and when HEAD moved
    every path the commits between the two heads name moved too (or the HEAD itself, named as
    `HEAD`, when git cannot list them). Raises GitError when git cannot answer."""
    now = source_pin(workspace, document)
    before = (pin or {}).get("paths") or {}
    # A path absent from one side is compared as its identity on disk NOW, never as None: a path
    # that left the set (a restored deletion, a mode put back) has moved from a pinned `missing`
    # or a pinned mode, and a path that joined it has moved from whatever the pin would have said.
    # Absent from the pin means "equal to HEAD then"; absent now means "equal to HEAD now".
    moved = set()
    for p in set(before) | set(now["paths"]):
        if p in before and p in now["paths"]:
            if before[p] != now["paths"][p]:
                moved.add(p)
        else:
            moved.add(p)
    if now["head"] != (pin or {}).get("head"):
        between = git(workspace, ["diff", "--name-only", "-z", "%s..%s" % (pin.get("head"), now["head"]),
                                  "--", "."] + _exclude_args(), binary=True, check=False) \
            if (pin or {}).get("head") else None
        names = [p for p in _paths(between) if p != document] if between is not None else []
        moved.update(names)
        if not names:
            moved.add("HEAD")
    return sorted(moved)
