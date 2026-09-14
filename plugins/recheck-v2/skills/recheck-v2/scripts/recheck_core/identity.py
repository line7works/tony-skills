"""Source identity (pilot contract section 6; evals/README.md "Identity encoding").

identity_of(workspace) returns the six fields exactly as fixturelib.identity_of computes them:
git runs read-only, inside the workspace only, under the same clean configuration environment
(GIT_CONFIG_NOSYSTEM=1, GIT_CONFIG_GLOBAL=/dev/null, LANG=C, TZ=UTC, the same -c flags), so no
user configuration can change the bytes that are hashed.
"""
import os
import subprocess

from . import canon

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
    """Run one read-only git command inside cwd; return stdout (bytes when binary)."""
    proc = subprocess.run(["git"] + GIT_CONFIG_ARGS + list(args), cwd=cwd, env=_git_env(),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        if check:
            raise GitError("git %s failed (%d): %s" % (" ".join(args), proc.returncode,
                                                       proc.stderr.decode("utf-8", "replace").strip()))
        return None
    return proc.stdout if binary else proc.stdout.decode("utf-8")


def is_work_tree_root(path):
    """(ok, reason): path exists, is inside a git work tree, is that tree's root, and has a HEAD commit."""
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


def identity_of(workspace):
    """The six-field fingerprint of pilot contract section 6 (byte-compatible with fixturelib)."""
    commit = git(workspace, ["rev-parse", "HEAD"]).strip()
    status = git(workspace, ["status", "--porcelain", "--untracked-files=all"])
    diff = git(workspace, ["diff", "HEAD", "--binary"], binary=True)
    raw = git(workspace, ["ls-files", "--others", "--exclude-standard", "-z"], binary=True)
    untracked = sorted(p.decode("utf-8") for p in raw.split(b"\0") if p)
    lines = []
    for path in untracked:
        with open(os.path.join(workspace, path), "rb") as fh:
            lines.append(path + "\0" + canon.sha256_hex(fh.read()) + "\n")
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


def reported(identity):
    """The identity as a result reports it: the six fields with submodules empty (E8-2)."""
    out = dict(identity)
    out["submodules"] = []
    return out


def normalize_pin(workspace, pin_commit):
    """The full hash `git rev-parse --verify <pin>^{commit}` resolves, or None (a mismatch)."""
    out = git(workspace, ["rev-parse", "--verify", "--quiet", pin_commit + "^{commit}"], check=False)
    if out is None or not out.strip():
        return None
    return out.strip()


def pin_matches(workspace, actual, pin):
    """(matched, reasons): every supplied pin field must equal the actual identity's."""
    reasons = []
    for field in FIELDS:
        if field not in pin:
            continue
        want = pin[field]
        if field == "commit":
            full = normalize_pin(workspace, want)
            if full is None:
                reasons.append("expected commit %s does not resolve in the workspace" % want)
                continue
            if full != actual["commit"]:
                reasons.append("expected commit %s (%s), actual %s" % (want, full, actual["commit"]))
            continue
        if want != actual.get(field):
            reasons.append("expected %s=%r, actual %r" % (field, want, actual.get(field)))
    return (not reasons), reasons


def changed_tracked_paths(workspace):
    """Tracked paths that differ from HEAD (staged or unstaged), sorted."""
    out = git(workspace, ["diff", "HEAD", "--name-only", "-z"], binary=True)
    return sorted(set(p.decode("utf-8") for p in out.split(b"\0") if p))


def tracked_diff_excluding(workspace, paths):
    """The bytes of `git diff HEAD --binary` with the given workspace-relative paths excluded."""
    args = ["diff", "HEAD", "--binary", "--", "."]
    for p in paths:
        args.append(":(exclude)" + p)
    return git(workspace, args, binary=True)
