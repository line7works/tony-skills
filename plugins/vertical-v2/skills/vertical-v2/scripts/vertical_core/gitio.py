"""Read-only git, run inside the workspace with a fixed environment (contract section 5).

Every call is an argv list; a caller value is one argv item, never shell text. The one command here
that writes anything is `archive_into`, and it writes only under a directory the caller names inside
the run directory: `git archive` streams the reviewed commit's tracked files and this module extracts
them, so the copy has no `.git`, no history and no commit message. No command here changes a branch,
an index or a worktree; `git worktree` is never run (A2, Q1).
"""
import io
import os
import subprocess
import tarfile

ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")


class GitFailed(RuntimeError):
    """A git command that failed; carries its argv tail and stderr."""


def _env():
    env = dict((k, os.environ[k]) for k in ENV_KEYS if k in os.environ)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0",
                "LC_ALL": "C", "LANG": "C"})
    return env


def run(workspace, args, check=True):
    proc = subprocess.run(["git", "-C", workspace] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=_env())
    if check and proc.returncode != 0:
        raise GitFailed("git %s failed (%d): %s" % (" ".join(args), proc.returncode,
                                                    proc.stderr.decode("utf-8", "replace").strip()))
    return proc


def text(workspace, args, check=True):
    return run(workspace, args, check).stdout.decode("utf-8", "replace")


def is_work_tree_root(workspace):
    proc = run(workspace, ["rev-parse", "--show-toplevel"], check=False)
    if proc.returncode != 0:
        return False
    top = proc.stdout.decode("utf-8", "replace").strip()
    return os.path.realpath(top) == os.path.realpath(workspace)


def head(workspace):
    proc = run(workspace, ["rev-parse", "--verify", "HEAD^{commit}"], check=False)
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def commit_of(workspace, ref):
    """The full commit a ref names, or None when it names none."""
    if not ref or ref.startswith("-"):
        return None
    proc = run(workspace, ["rev-parse", "--verify", "--quiet", "%s^{commit}" % ref], check=False)
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def default_branch(workspace):
    """The default branch: the remote's HEAD when a remote names one, else `main`, else `master`."""
    proc = run(workspace, ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], check=False)
    if proc.returncode == 0:
        ref = proc.stdout.decode().strip()
        if commit_of(workspace, ref):
            return ref
    for name in ("main", "master"):
        if commit_of(workspace, "refs/heads/%s" % name):
            return "refs/heads/%s" % name
    return None


def merge_base(workspace, ref):
    proc = run(workspace, ["merge-base", ref, "HEAD"], check=False)
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def name_status(workspace, base):
    """`git diff --name-status <base>..HEAD` as [{"status", "path"}] (a rename names its new path and
    keeps the old one under `from`)."""
    out = []
    raw = run(workspace, ["diff", "--name-status", "-z", "%s..HEAD" % base]).stdout.decode("utf-8", "replace")
    parts = raw.split("\0")
    index = 0
    while index < len(parts) and parts[index]:
        status = parts[index]
        if status[:1] in ("R", "C"):
            out.append({"status": status, "path": parts[index + 2], "from": parts[index + 1]})
            index += 3
        else:
            out.append({"status": status, "path": parts[index + 1]})
            index += 2
    return out


def dirt(workspace):
    """Every path `git status --porcelain` names (tracked changes, staged or not, and untracked files)."""
    raw = run(workspace, ["status", "--porcelain", "-z", "--untracked-files=all"]).stdout.decode("utf-8", "replace")
    parts = raw.split("\0")
    out = []
    index = 0
    while index < len(parts) and parts[index]:
        entry = parts[index]
        out.append(entry[3:])
        if entry[:1] in ("R", "C") or entry[1:2] in ("R", "C"):
            index += 2
        else:
            index += 1
    return sorted(set(out))


def untracked(workspace):
    return sorted(p for p in text(workspace, ["ls-files", "-z", "--others", "--exclude-standard"]).split("\0") if p)


def ignored(workspace):
    return sorted(p for p in text(workspace, ["ls-files", "-z", "--others", "--ignored", "--exclude-standard",
                                              "--directory"]).split("\0") if p)


def archive_into(workspace, commit, dest, exclusions):
    """Extract the tracked files of `commit` into `dest` (a fresh directory), each pathspec in
    `exclusions` left out. Returns the extracted relative paths. A symbolic link is written as a plain
    file holding its target text; any other special member is left out."""
    if os.path.exists(dest):
        raise GitFailed("the copy's directory already exists: %s" % dest)
    specs = ["."] + [":(exclude)%s" % e for e in exclusions]
    data = run(workspace, ["archive", "--format=tar", commit, "--"] + specs).stdout
    os.makedirs(dest)
    names = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as tar:
        for member in tar.getmembers():
            name = os.path.normpath(member.name)
            if name.startswith("..") or os.path.isabs(name) or name == "pax_global_header":
                continue
            target = os.path.join(dest, name)
            if member.isdir():
                os.makedirs(target, exist_ok=True)
            elif member.isfile():
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with tar.extractfile(member) as src, open(target, "wb") as out:
                    out.write(src.read())
                os.chmod(target, 0o755 if member.mode & 0o111 else 0o644)
                names.append(name)
            elif member.issym():
                # never a link in the copy: the entry is written as its link target text, the bytes git
                # records for it, so nothing in the copy reaches outside it
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as out:
                    out.write(member.linkname.encode("utf-8"))
                os.chmod(target, 0o644)
                names.append(name)
    return sorted(names)
