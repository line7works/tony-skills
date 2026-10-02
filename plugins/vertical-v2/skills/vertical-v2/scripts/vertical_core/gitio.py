"""Read-only git, run inside the workspace with a fixed environment (contract section 5).

Every call is an argv list; a caller value is one argv item, never shell text. The one function here
that writes anything is `archive_into`, and it writes only under a directory the caller names inside
the run directory: `git ls-tree` lists the reviewed commit's tracked files and `git cat-file --batch`
streams their stored bytes, so the copy has no `.git`, no history and no commit message, and the
reviewed repo's `.gitattributes` export rules never apply (no `export-subst` expansion writes a commit
message into a file, no `export-ignore` drops a tracked file; C1A-5). It is the copy `git archive` would
cut, less those two attribute rules and any checkout filter: each file holds the commit's bytes. No
command here changes a branch, an index or a worktree; `git worktree` is never run (A2, Q1).
"""
import os
import subprocess

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
    """Every path `git status --porcelain` names (tracked changes, staged or not, and untracked files). A
    rename or copy names both of its paths, the new one and the one it came from (C1A-8), so a boundary
    file moved away reads as dirt on the boundary file."""
    raw = run(workspace, ["status", "--porcelain", "-z", "--untracked-files=all"]).stdout.decode("utf-8", "replace")
    parts = raw.split("\0")
    out = []
    index = 0
    while index < len(parts) and parts[index]:
        entry = parts[index]
        out.append(entry[3:])
        if entry[:1] in ("R", "C") or entry[1:2] in ("R", "C"):
            if index + 1 < len(parts) and parts[index + 1]:
                out.append(parts[index + 1])
            index += 2
        else:
            index += 1
    return sorted(set(out))


def untracked(workspace):
    return sorted(p for p in text(workspace, ["ls-files", "-z", "--others", "--exclude-standard"]).split("\0") if p)


def ignored(workspace):
    return sorted(p for p in text(workspace, ["ls-files", "-z", "--others", "--ignored", "--exclude-standard",
                                              "--directory"]).split("\0") if p)


def _excluded(path, exclusions):
    """Whether a tracked path falls under one of `exclusions` (a path, or a folder and everything in it),
    the way a plain pathspec matches: from the top of the tree, never by base name alone."""
    return any(path == e or path.startswith(e.rstrip("/") + "/") for e in exclusions)


def tree_files(workspace, commit):
    """[(mode, object id, path)] for every blob the commit's tree holds, recursively (`git ls-tree -r -z
    --full-tree`). A submodule (a commit entry) is not a blob and is not listed."""
    raw = run(workspace, ["ls-tree", "-r", "-z", "--full-tree", commit]).stdout
    out = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, _, path = record.partition(b"\t")
        mode, kind, oid = meta.decode("ascii").split(" ")
        if kind == "blob":
            out.append((mode, oid, path.decode("utf-8", "surrogateescape")))
    return out


def blobs(workspace, oids):
    """{object id: bytes} for each blob, read through one `git cat-file --batch` (the stored bytes: no
    attribute, filter or line-ending rule applies)."""
    wanted = sorted(set(oids))
    if not wanted:
        return {}
    proc = subprocess.run(["git", "-C", workspace, "cat-file", "--batch"], input=("\n".join(wanted) + "\n").encode(),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_env())
    if proc.returncode != 0:
        raise GitFailed("git cat-file --batch failed (%d): %s" % (proc.returncode,
                                                                 proc.stderr.decode("utf-8", "replace").strip()))
    data = proc.stdout
    out = {}
    at = 0
    for oid in wanted:
        end = data.index(b"\n", at)
        header = data[at:end].decode("ascii").split(" ")
        if len(header) != 3 or header[0] != oid or header[1] != "blob":
            raise GitFailed("git cat-file --batch answered %r for %s" % (" ".join(header), oid))
        size = int(header[2])
        out[oid] = data[end + 1:end + 1 + size]
        at = end + 1 + size + 1
    return out


def archive_into(workspace, commit, dest, exclusions):
    """Write the tracked files of `commit` into `dest` (a fresh directory), each path in `exclusions` (a
    path, or a folder and everything in it) left out. Returns the written relative paths. Each file holds
    the bytes the commit stores for it; the repo's `.gitattributes` export rules are not applied (C1A-5). A
    symbolic link is written as a plain file holding its target text, the bytes git records for it, so
    nothing in the copy reaches outside it."""
    if os.path.exists(dest):
        raise GitFailed("the copy's directory already exists: %s" % dest)
    entries = []
    for mode, oid, path in tree_files(workspace, commit):
        name = os.path.normpath(path)
        if name.startswith("..") or os.path.isabs(name) or _excluded(path, exclusions):
            continue
        entries.append((mode, oid, name))
    contents = blobs(workspace, [oid for mode, oid, name in entries])
    os.makedirs(dest)
    names = []
    for mode, oid, name in entries:
        target = os.path.join(dest, name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as out:
            out.write(contents[oid])
        os.chmod(target, 0o755 if mode == "100755" else 0o644)
        names.append(name)
    return sorted(names)
