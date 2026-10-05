"""Read-only git, run inside the workspace with a fixed environment (contract section 3.5, "The pin").

Every call is an argv list; a caller value is one argv item, never shell text. Every subcommand here reads:
`rev-parse`, `status`, `diff`. No command here changes a branch, an index or a worktree, and nothing is pushed,
merged or opened (CR-24): `run` refuses a first argv item outside `READ_ONLY` (`GitRefused`) before git starts,
however the argv was built (`tests/test_static.py` plants one through a variable).
"""
import os
import subprocess

ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")
READ_ONLY = ("rev-parse", "status", "diff")


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
        raise GitRefused("git %r is not a read this core makes (%s); nothing ran" % (args[:1], ", ".join(READ_ONLY)))
    proc = subprocess.run(["git", "-C", workspace] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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
    return os.path.realpath(proc.stdout.decode("utf-8", "replace").strip()) == os.path.realpath(workspace)


def head(workspace):
    proc = run(workspace, ["rev-parse", "--verify", "HEAD^{commit}"], check=False)
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


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


def changed_between(workspace, old, new):
    """Every path the commits from `old` to `new` change (`git diff --name-only --no-renames -z`), sorted."""
    raw = run(workspace, ["diff", "--name-only", "--no-renames", "-z", old, new]).stdout.decode("utf-8", "replace")
    return sorted(set(part for part in raw.split("\0") if part))
