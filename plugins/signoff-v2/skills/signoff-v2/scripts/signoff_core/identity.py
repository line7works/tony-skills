"""Source identity and the section 8 source set.

Two facts about the reviewed content, both computed from git and never guessed:

- `identity_of(workspace)` is the six-field fingerprint of pilot contract section 6, computed the
  way `recheck_core/identity.py` computes it and the way the records component computes it, with
  one fixed prefix excluded from the dirty check, the tracked diff and the untracked list:
  `docs/records/`, the component's own history (CR-3). The component publishes that same
  exclusion under `excluded`, and `append` refuses a clear whose `verified_source` is not the
  identity the component computes, so the two must agree field for field.
- `source_set(workspace, base)` is the set a review covers (lane contract section 8): committed
  since the slice's base, changed in the working tree against HEAD (staged or not), and untracked
  but not ignored. `docs/records/` is excluded from all three for the same reason: the log
  describes the source and is never part of it.

A set that cannot be computed is a `ScopeUnavailable` carrying a reason code — never a guess and
never an empty set standing in for a failure.

Git runs read-only, inside the workspace only, under a clean configuration environment, so no
user configuration can change the bytes that are hashed.
"""
import os
import subprocess

from . import canon
from .constants import RECORDS_PREFIX

EXCLUDED_PREFIXES = (RECORDS_PREFIX,)
EXCLUDED_PATHSPECS = tuple(p.rstrip("/") for p in EXCLUDED_PREFIXES)

GIT_CONFIG_ARGS = [
    "-c", "core.hooksPath=/dev/null",
    "-c", "commit.gpgsign=false",
    "-c", "core.autocrlf=false",
    "-c", "core.fileMode=true",
    "-c", "protocol.file.allow=always",
]
FIELDS = ("commit", "dirty", "tracked_diff_sha256", "untracked", "untracked_sha256", "submodules")


class GitError(RuntimeError):
    pass


class ScopeUnavailable(RuntimeError):
    """The source set could not be computed. Carries a reason code for the result's stop."""

    def __init__(self, reason_code, message):
        RuntimeError.__init__(self, message)
        self.reason_code = reason_code


def _exclude_args():
    return [":(exclude)" + p for p in EXCLUDED_PATHSPECS]


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


def git(cwd, args, binary=False, check=True):
    """One read-only git command inside `cwd`; stdout (bytes when binary), or None when it failed
    and `check` is false."""
    try:
        proc = subprocess.run(["git"] + GIT_CONFIG_ARGS + list(args), cwd=cwd, env=_git_env(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as failure:
        if check:
            raise GitError("git is not runnable: %s" % failure)
        return None
    if proc.returncode != 0:
        if check:
            raise GitError("git %s failed (%d): %s"
                           % (" ".join(args), proc.returncode,
                              proc.stderr.decode("utf-8", "replace").strip()))
        return None
    return proc.stdout if binary else proc.stdout.decode("utf-8")


def is_work_tree_root(path):
    """(ok, reason): the path exists, is inside a git work tree, is that tree's root, and has a
    HEAD commit."""
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


def require_work_tree_root(workspace):
    ok, reason = is_work_tree_root(workspace)
    if not ok:
        raise ScopeUnavailable("not_a_git_work_tree",
                               "the workspace %s %s" % (workspace, reason))


def untracked_bytes(full):
    """The bytes an untracked path contributes to the fingerprint. A symlink contributes its link
    target text, as git stores one, and is never followed; a directory contributes nothing."""
    if os.path.islink(full):
        return os.readlink(full).encode("utf-8", "surrogateescape")
    if os.path.isdir(full):
        return b""
    with open(full, "rb") as fh:
        return fh.read()


def _name_list(workspace, args):
    raw = git(workspace, args + ["-z", "--", "."] + _exclude_args(), binary=True)
    return sorted(set(p.decode("utf-8") for p in raw.split(b"\0") if p))


def tracked_diff_excluding(workspace, paths=()):
    """`git diff HEAD --binary` with the given paths and `docs/records/` excluded."""
    args = ["diff", "HEAD", "--binary", "--", "."]
    for p in list(paths) + [p for p in EXCLUDED_PATHSPECS if p not in paths]:
        args.append(":(exclude)" + p)
    return git(workspace, args, binary=True)


def identity_of(workspace):
    """The six-field fingerprint, with `docs/records/` excluded from all three checks (CR-3)."""
    require_work_tree_root(workspace)
    commit = git(workspace, ["rev-parse", "HEAD"]).strip()
    status = git(workspace, ["status", "--porcelain", "--untracked-files=all", "--", "."]
                 + _exclude_args())
    diff = tracked_diff_excluding(workspace)
    untracked = _name_list(workspace, ["ls-files", "--others", "--exclude-standard"])
    lines = []
    for path in untracked:
        lines.append(path + "\0" + canon.sha256_hex(untracked_bytes(os.path.join(workspace, path))) + "\n")
    lines.sort()
    submodules = []
    for line in git(workspace, ["submodule", "status"]).splitlines():
        if line.strip():
            submodules.append(line[1:].split()[1])
    return {
        "commit": commit,
        "dirty": bool(status.strip()),
        "tracked_diff_sha256": canon.sha256_hex(diff),
        "untracked": untracked,
        "untracked_sha256": canon.sha256_hex("".join(lines).encode("utf-8")),
        "submodules": submodules,
    }


def reported(fingerprint):
    """The identity as a result reports it: the six fields with `submodules` empty."""
    out = dict(fingerprint)
    out["submodules"] = []
    return out


def resolve_ref(workspace, ref):
    """The 40-hex commit `ref` names, or None."""
    out = git(workspace, ["rev-parse", "--verify", "--quiet", str(ref) + "^{commit}"], check=False)
    if out is None or not out.strip():
        return None
    return out.strip()


def source_set(workspace, base_ref):
    """The three lists and the base (lane contract section 8).

    committed: `git diff --name-only <base>..HEAD`
    changed:   `git diff HEAD --name-only` (staged and unstaged alike)
    untracked: `git ls-files --others --exclude-standard`

    `docs/records/` is excluded from each (CR-3). A workspace that is not a git work tree root, or
    a base that does not resolve, is a `ScopeUnavailable`, never an empty set.
    """
    require_work_tree_root(workspace)
    if base_ref is None or str(base_ref).strip() == "":
        raise ScopeUnavailable("base_missing", "the input names no base for the slice")
    base_commit = resolve_ref(workspace, base_ref)
    if base_commit is None:
        raise ScopeUnavailable("base_unresolvable",
                               "the base ref %r does not resolve to a commit in %s"
                               % (base_ref, workspace))
    head = git(workspace, ["rev-parse", "HEAD"]).strip()
    committed = _name_list(workspace, ["diff", "--name-only", "%s..%s" % (base_commit, head)])
    changed = _name_list(workspace, ["diff", "HEAD", "--name-only"])
    untracked = _name_list(workspace, ["ls-files", "--others", "--exclude-standard"])
    return {
        "base_ref": base_ref,
        "base_commit": base_commit,
        "head": head,
        "committed": committed,
        "changed": changed,
        "untracked": untracked,
        "excluded": list(EXCLUDED_PREFIXES),
    }


def flatten(source):
    """Every path of the set once, sorted, with the list it came from.

    A path can sit in more than one list (a committed file edited again in the work tree); the
    packet carries it once and names every list that holds it, so nothing leaves the review by
    appearing twice."""
    lists = {}
    for name in ("committed", "changed", "untracked"):
        for path in source[name]:
            lists.setdefault(path, []).append(name)
    return [{"path": path, "lists": lists[path]} for path in sorted(lists)]
