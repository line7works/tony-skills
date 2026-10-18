"""SEC-10's check before a commit and before a push (the owner's rulings A87 and A89; SEC-7's row for the frame's own
memory; RK15).

"Before every commit a check scans, by content, exactly what will be committed and proves the ignore rule; before a push
a check scans every commit to be pushed." A hit is any entry of the register at the check, or any value of the pulled env
file or of the hosting link file of that working tree, which the check reads in-process at the check, uses for this match
and for nothing else, enters in no register, and drops after it; each is matched whole, by each component its source
declares, and in the percent-encoded and base64 forms of both, as SEC-12 names the forms. A value of either file that has
no length is no hit. A value of the pulled env file is no hit where it is under SEC-4's least length of eight bytes,
counted in UTF-8 on the value without the marks that enclose it in the file and with white space at either end left out,
and no hit where it is the value of one of the hosting module's own variables and stands on the list of fixed words the
module declares for that variable (the lane's rows hold that list); the same word under a variable of the owner's own is
no fixed word. A hit stops the run, names the file and shows nothing.

What the check reads: the repository's own files, in-process (`gitread`), and the two files, through the one file system
seam; and, for the ignore rule, git's own answer for each of the two files, asked of git through the one runner (SEC-3).
It writes nothing. The values of the two files live in a `Matcher` of this module, which is no register: it is made for
one check and dropped with it.
"""
import json
import os

from . import channels, gitread, results, runner, screen

LEAST = 8          # SEC-4's least length, in bytes


class Unreadable(Exception):
    """What the check must read cannot be read: the check is a failed read (RUN-7, OP-8)."""


class Matcher(object):
    """The forms of the register's entries at the check and of the values of the two files: whole, by component, and in
    the percent-encoded and base64 forms of both (SEC-12's `forms_of`). Bytes are matched, so a file of any content is
    scanned as it is."""

    def __init__(self, register):
        self.forms = []
        for entry in register.entries:
            for form in entry.forms:
                self._add(form)

    def _add(self, form):
        raw = form.encode("utf-8")
        if raw and raw not in self.forms:
            self.forms.append(raw)

    def add_value(self, value, components=()):
        for item in [value] + [c for c in components if c]:
            for form in screen.forms_of(item):
                self._add(form)

    def hit(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8", "surrogateescape")
        return any(form in data for form in self.forms)


def env_values(text):
    """[(variable, value)] of an env file: `NAME=value` lines, `export ` allowed before the name, the value without the
    quotes that enclose it in the file; a line with no `=`, a blank line and a comment are no value."""
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        name = name.strip()
        if name.startswith("export "):
            name = name[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out.append((name, value))
    return out


def env_hit_values(text, fixed_words):
    """The values of the pulled env file that are hits, each with the components its source declares (a connection
    address: the password, and the user and password pair, SEC-12)."""
    out = []
    for name, value in env_values(text):
        if not value:
            continue                                                    # no length: no hit (A87; SEC-12)
        if len(value.strip().encode("utf-8")) < LEAST:
            continue                                                    # under the least length: no hit (A89; RK15)
        if value in (fixed_words.get(name) or []):
            continue                                                    # the module's own word for its own variable (A89)
        trimmed = value.strip()
        components = channels.address_components(trimmed)
        if trimmed != value:
            components = [trimmed] + components
        out.append((value, components))
    return out


def link_hit_values(text):
    """Every text and every number that stands in the hosting link file, at any depth; the names of an object's fields
    are no values (SEC-4's words for what an object holds). Raises Unreadable where the file is not such a document."""
    try:
        doc = json.loads(text)
    except ValueError:
        raise Unreadable("the hosting link file")
    out = []

    def walk(node):
        if isinstance(node, dict):
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, bool) or node is None:
            return
        elif isinstance(node, (int, float)):
            out.append(json.dumps(node))
        elif isinstance(node, str) and node:
            out.append(node)
    walk(doc)
    return out


def matcher(session, env_file, link_file, fixed_words):
    """The match of this one check: the register at the check and the two files' values, read in-process now."""
    found = Matcher(session.register)
    fs = session.world.fs
    for path, read in ((env_file, "env"), (link_file, "link")):
        if not path or not fs.lexists(path):
            continue
        if fs.islink(path) or not fs.isfile(path):
            raise Unreadable(path)
        try:
            text = fs.read(path).decode("utf-8")
        except (OSError, UnicodeDecodeError):
            raise Unreadable(path)
        if read == "env":
            for value, components in env_hit_values(text, fixed_words or {}):
                found.add_value(value, components)
        else:
            for value in link_hit_values(text):
                found.add_value(value)
    return found


def repository(session, repo):
    """The repository whose working tree's top is `repo`: its own git folder, or, for a linked worktree, the folder its
    `.git` file names (which names the common folder in turn, `gitread.Repository`)."""
    fs = session.world.fs
    top = os.path.abspath(repo)
    dot = os.path.join(top, ".git")
    try:
        if fs.isdir(dot):
            gitdir = dot
        elif fs.isfile(dot):
            text = fs.read(dot).decode("utf-8", "replace").strip()
            if not text.startswith("gitdir:"):
                raise Unreadable(repo)
            gitdir = os.path.normpath(os.path.join(top, text[len("gitdir:"):].strip()))
            if not fs.isdir(gitdir):
                raise Unreadable(repo)
        else:
            raise Unreadable(repo)
        return gitread.Repository(top, gitdir, fs)
    except (gitread.Unreadable, OSError, ValueError):
        raise Unreadable(repo)


# ---- the ignore rule (SEC-10, batch 39; SEC-7: "ignored by git, proven before every commit") -------------------------
# SEC-10: "The ignore rule is proven for each of the pulled env file and the hosting link file that stands in the working
# tree: that it is in no stage of the index and that git ignores it. Where the check cannot prove that, the attempt is
# `failed` (OP-8) and the run stops as at a hit, naming the file and showing nothing." The proof follows git's own rules
# for that repository (contract A92) by asking git itself: `git check-ignore`, started by the one runner like every
# other program (SEC-3), in the working tree's top, its exit number read by SEC-4's parser as a fixed word of this
# declaration and nothing it prints read. Git then reads what it reads for that repository: the ignore files at every
# level with their negated, `**` and escaped patterns, the repository's exclude file (a linked worktree's shared one),
# and the owner's own excludes file as his settings of git name it, or where git looks for it by default. Only git's own
# `ignored` (exit 0) proves it; `not ignored` (exit 1), an exit this declaration does not list, a time limit met and a
# child killed each leave it not proven, so a file git does not ignore never passes. Without `--no-index`, git itself
# also answers `not ignored` for a path the index holds, a second guard beside the tool's own read of every stage.
IGNORE_CHECK = {
    "tool": "git",
    "template": [{"literal": "check-ignore"}, {"literal": "-q"}, {"literal": "--"}, {"param": "path"}],
    "time_limit": 30,
    "exits": {"0": "success", "1": "not-found"},
    "fields": [],
    "definite": {"success": ["success"], "refusals": ["not-found"]},
    "trace_flags": ["--verbose", "-v", "--trace"],
    "output": "none",
}


def git_ignores(session, top, rel, of_operation=False):
    """True only where git, asked through the one runner in the working tree at `top`, answers that it ignores `rel`.
    Raises `runner.Refused` before the start (SEC-3's refusals), and, made for a check operation, where the file the runner
    found is gone as it starts it (A109): the proof's git is a command of that check (SEC-10)."""
    world = session.world
    context = runner.Context(session.register, session.run_dir, session.facts.search_list(world.fs, world.system_folders),
                             of_operation=of_operation)
    raw = runner.run(world, context, IGNORE_CHECK, ["check-ignore", "-q", "--", rel], {}, top)
    return results.Parser(IGNORE_CHECK, raw, session.register).finish().kind == "success"


# G23-F1 (OP-8, A154): which ignore file ignores a path, as git itself answers it: `git check-ignore -v`, through the one runner,
# its one line read in memory ("<source>:<line>:<pattern>\t<path>") and never shown. The build check's output folder must be
# ignored by the project's own `.gitignore` (a `.gitignore` file inside the working tree), not by the repository's exclude
# file or the owner's own excludes
IGNORE_SOURCE = {
    "tool": "git",
    "template": [{"literal": "check-ignore"}, {"literal": "-v"}, {"literal": "--"}, {"param": "path"}],
    "time_limit": 30,
    "exits": {"0": "success", "1": "not-found"},
    "fields": [],
    "definite": {"success": ["success"], "refusals": ["not-found"]},
    "trace_flags": ["--verbose", "--trace"],
}


def own_gitignore_ignores(session, top, rel, of_operation=False):
    """True only where git answers that `rel` is ignored and the pattern that decides it stands in a `.gitignore` file of
    the working tree at `top`. Raises `runner.Refused` as `git_ignores` does."""
    world = session.world
    context = runner.Context(session.register, session.run_dir, session.facts.search_list(world.fs, world.system_folders),
                             of_operation=of_operation)
    raw = runner.run(world, context, IGNORE_SOURCE, ["check-ignore", "-v", "--", rel], {}, top)
    if raw.exit_code != 0 or not raw.stdout:
        return False
    line = raw.stdout.decode("utf-8", "replace").split("\n")[0]
    source = line.split("\t", 1)[0].rsplit(":", 2)[0] if "\t" in line and line.count(":") >= 2 else ""
    if not source or os.path.isabs(source) or source.split("/")[0] == ".git":
        return False
    return os.path.basename(source) == ".gitignore"


def ignore_proven(session, repo, index, rel, of_operation=False):
    """Whether `rel` (a path in the working tree, from its top) is in no stage of the index and git ignores it."""
    if rel in index:
        return False                               # the index's own record holds every stage of a path
    return git_ignores(session, repo.top, rel, of_operation)


# ---- the two scans -------------------------------------------------------------------------------------------------
def commit_scan(session, repo_path, env_file, link_file, fixed_words, of_operation=False):
    """(None, None) where what will be committed holds no hit and the ignore rule is proven; else (the file named, why).
    What will be committed: each path of the index whose content differs from the head commit's at that path, or that
    the head commit does not hold (every path of the index where there is no head commit yet)."""
    repo = repository(session, repo_path)
    try:
        index = repo.index()
        head = repo.ref("HEAD")
        before = repo.files(repo.commit(head)[0]) if head else {}
        rels = []
        for path, kept in ((env_file, "env"), (link_file, "link")):
            if path and session.world.fs.lexists(path):
                rel = os.path.relpath(os.path.abspath(path), repo.top)
                if rel.startswith(".." + os.sep) or rel == "..":
                    continue
                rels.append(rel.replace(os.sep, "/"))
        for rel in rels:
            if not ignore_proven(session, repo, index, rel, of_operation):
                return rel, "ignore"
        match = matcher(session, env_file, link_file, fixed_words)
        for name in sorted(index):
            for mode, blob in index[name]:
                if before.get(name) == (mode, blob):
                    continue
                if match.hit(name):
                    return None, "name"
                kind, data = repo.read(blob)
                if match.hit(data):
                    return name, "content"
    except (gitread.Unreadable, OSError, ValueError, IndexError) as exc:
        raise Unreadable(str(type(exc).__name__))
    return None, None


def push_scan(session, repo_path, env_file, link_file, fixed_words, branch, base):
    """(None, None) where no commit to be pushed holds a hit; else (the file named, why). The commits to be pushed: those
    reachable from the branch and not from `base`, the reference that records what the remote holds (all of them where
    it records nothing). Of each, its own text and each file it changes against its first parent (every file of a
    commit with no parent)."""
    repo = repository(session, repo_path)
    try:
        head = repo.ref("refs/heads/" + branch)
        known = repo.ref(base) if base else None
        match = matcher(session, env_file, link_file, fixed_words)
        for sha in repo.to_push(head, known):
            tree, parents, body = repo.commit(sha)
            if match.hit(body):
                return "the commit " + sha, "content"
            now = repo.files(tree)
            before = repo.files(repo.commit(parents[0])[0]) if parents else {}
            for name in sorted(now):
                if before.get(name) == now[name]:
                    continue
                if match.hit(name):
                    return None, "name"
                if match.hit(repo.read(now[name][1])[1]):
                    return name, "content"
    except (gitread.Unreadable, OSError, ValueError, IndexError) as exc:
        raise Unreadable(str(type(exc).__name__))
    return None, None
