"""Read-only git, run inside the workspace with a fixed environment (contract section 4, "The photograph").

Every call is an argv list; a caller value is one argv item, never shell text. Every subcommand here reads:
`rev-parse`, `symbolic-ref`, `rev-list`, `status`, `show`, `log`, `cat-file`, `diff`. No command here changes a
branch, an index or a worktree (the E15 lane contract A2, Q2): the checkpoint commit is the executor's named step,
outside the script, and the script only reads the commit it finds afterwards. `run` holds that at run time: a first
argv item outside `READ_ONLY` is refused (`GitRefused`) before git starts, however the argv was built
(`tests/test_static.py` plants one through a variable; the slice 1b check's C1B1-6).
"""
import os
import subprocess

ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")
READ_ONLY = ("rev-parse", "symbolic-ref", "rev-list", "status", "show", "log", "cat-file", "diff")


class GitFailed(RuntimeError):
    """A git command that failed; carries its argv tail and stderr."""


class GitRefused(ValueError):
    """A git argv whose subcommand is not a read this core makes: refused before git starts."""


def _env():
    env = dict((k, os.environ[k]) for k in ENV_KEYS if k in os.environ)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0",
                "LC_ALL": "C", "LANG": "C"})
    return env


def run(workspace, args, check=True):
    args = list(args)
    if not args or args[0] not in READ_ONLY:
        raise GitRefused("git %r is not a read this core makes (%s); nothing ran"
                         % (args[:1], ", ".join(READ_ONLY)))
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
    if not ref or ref.startswith("-"):
        return None
    proc = run(workspace, ["rev-parse", "--verify", "--quiet", "%s^{commit}" % ref], check=False)
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def branch(workspace):
    """The checked-out branch's short name, or None when HEAD is detached."""
    proc = run(workspace, ["symbolic-ref", "--quiet", "--short", "HEAD"], check=False)
    name = proc.stdout.decode("utf-8", "replace").strip()
    return name if proc.returncode == 0 and name else None


def default_branch(workspace):
    """(the default branch's ref, its short name): the remote's HEAD when a remote names one, else `main`, else
    `master`; (None, None) when none resolves."""
    proc = run(workspace, ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], check=False)
    if proc.returncode == 0:
        ref = proc.stdout.decode().strip()
        if commit_of(workspace, ref):
            return ref, ref[len("refs/remotes/"):] if ref.startswith("refs/remotes/") else ref
    for name in ("main", "master"):
        if commit_of(workspace, "refs/heads/%s" % name):
            return "refs/heads/%s" % name, name
    return None, None


def ahead(workspace, ref):
    """How many commits HEAD holds that `ref` does not (`git rev-list --count <ref>..HEAD`)."""
    return int(text(workspace, ["rev-list", "--count", "%s..HEAD" % ref]).strip() or "0")


def dirt(workspace):
    """Every path `git status --porcelain` names (tracked changes, staged or not, and untracked files); a rename or
    copy names both of its paths."""
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


def show(workspace, commit, path):
    """The bytes `path` holds at `commit`, or None when the commit does not hold it."""
    proc = run(workspace, ["show", "%s:%s" % (commit, path)], check=False)
    return proc.stdout if proc.returncode == 0 else None


def parents(workspace, commit):
    """The commit's parents, in order."""
    return text(workspace, ["rev-list", "--parents", "-n", "1", commit]).split()[1:]


def subject(workspace, commit):
    return text(workspace, ["log", "-1", "--format=%s", commit]).strip()


def changed_between(workspace, old, new):
    """Every path the commits from `old` to `new` change (`git diff --name-only --no-renames -z`), sorted: a rename
    names both of its paths, as `dirt` does."""
    raw = run(workspace, ["diff", "--name-only", "--no-renames", "-z", old, new]).stdout.decode("utf-8", "replace")
    return sorted(set(part for part in raw.split("\0") if part))
