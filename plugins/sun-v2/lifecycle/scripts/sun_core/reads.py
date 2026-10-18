"""The reads a test is made of (the frame's RUN-6, OP-5, OP-8, OP-9, KEEP-3).

A test is a list of conditions, every one of which must hold. A condition is one read and what it
must show:

    {"read": "path", "path": V, "is": "absent" | "file" | "dir" | "present"}
    {"read": "sha256", "path": V, "equals": V}
    {"read": "line", "path": V, "line": V, "present": true | false, "count": n}
    {"read": "line", "path": V, "line": V, "number": n}   the file's line number n is that line (G21-5)
    {"read": "identity", "path": V, "equals": V}
    {"read": "mode", "path": V, "at_most": 0o600}
    {"read": "name-free", "name": V, "free": false}  no program, alias, shell function, builtin or reserved word of
                                                     that name, as his login zsh holds them (RK5's check; RUN-7,
                                                     SEC-3, A55, A63); `"free": false` asks that the name is now taken,
                                                     as an after-check (G19-11)
    {"read": "text", "path": V, "text": V, "count": n | "present": B}   how many lines of a file hold a safe value
    {"read": "text", ..., "under": V}                 the same of the lines under the heading line V only (G25-4)
    {"read": "text", "command": NAME, ...}           the same over a command's answer declared `protected text`, counted in
                                                     memory and kept nowhere (SEC-4, A147; G19-8)
    {"read": "index-current", "repo": V, "is": B}    nothing left for `git add --all` to stage: every path of the index
                                                     stands with its content, and every other file is one git ignores
    {"read": "ref", "repo": V, "ref": WORD, "exists": B | "equals": V}   a branch's commit, read by the tool from the
                                                     repository itself (SEC-4's hash row; G19-10)
    {"read": "command", "command": NAME, "result": KIND, "field": F, "equals": WORD}   false where the field stands
                                                     nowhere in the answer (G24-1)
    {"read": "commit-scan", "repo": V, "env_file": V, "link_file": V, "fixed_words": {VAR: [WORD]}}
    {"read": "push-scan", ..., "branch": WORD, "base": REF}   SEC-10's check before a commit and before a push
                                                             (`commitscan`); false on a hit, which `last_hit` names

`evaluate` answers True, False, or `UNREADABLE` where a read failed, was partial, was made as the
wrong account, or ran out of time. A probe only reads: a command used in a test is one whose
declaration says it changes nothing.
"""
from . import commitscan, fsio, gitread, shellcheck, values

UNREADABLE = "unreadable"


class Reader(object):
    """What a test is evaluated with: the world, the outputs bound so far, and the row's commands."""

    def __init__(self, session, outputs, commands, caller, op=None, journal=None):
        self.session = session
        self.fs = session.world.fs
        self.outputs = outputs
        self.commands = dict((c["name"], c) for c in commands or [] if isinstance(c, dict))
        self.caller = caller          # caller(command, outputs, op, journal) -> results.Result
        self.op = op
        self.journal = journal
        self.last_command = None      # the last command read, as a form may show it
        self.last_kind = None
        self.last_safe = {}           # what the last command read may show: the tool's own words and copies
        self.seen_safe = {}           # the same, of every command read so far: what a form line's `<field>` may show (G19-28)
        self.last_hit = None          # SEC-10: (the file named, why) of the last scan that found a hit

    def value(self, mark):
        return values.resolve(mark, self.outputs)

    def text(self, mark):
        """A value to compare in memory: a held value (a protected record of this run) by its content (SEC-4)."""
        found = self.value(mark)
        if isinstance(found, values.Held):
            from . import protected
            try:
                return protected.read(self.fs, self.session.run_dir, found.reference).decode("utf-8")
            except protected.Unreadable:
                raise OSError("a protected record cannot be read")
        return found

    def joined(self, mark):
        """A line read's value where it is a text of parts: each part by its content, a held part read from its record in
        memory, and the parts joined (G23-14: a literal heading and a held line, two lines). Any other value as `text` gives it."""
        if values.is_mark(mark) and "text" in mark:
            return "".join(str(self.joined(part)) for part in mark["text"])
        return self.text(mark)

    def condition(self, c):
        read = c.get("read")
        try:
            if read == "path":
                path = self.text(c["path"])
                exists = self.fs.lexists(path)
                want = c.get("is")
                if want == "absent":
                    return not exists
                if want == "present":
                    return exists
                if not exists or self.fs.islink(path):
                    return False
                return self.fs.isdir(path) if want == "dir" else self.fs.isfile(path)
            if read == "sha256":
                path = self.text(c["path"])
                if not self.fs.isfile(path):
                    return False
                return fsio.sha256_hex(self.fs.read(path)) == self.value(c["equals"])
            if read == "line":
                path = self.text(c["path"])
                if not self.fs.isfile(path):
                    # no file is there: it is in neither state a row names by its lines, but where the row says that its
                    # absence is a state of its own (`or_absent`: a kit file absent or lacking its line, G19-13)
                    return bool(c.get("or_absent")) and not self.fs.lexists(path)
                lines = self.fs.read_text(path).split("\n")
                if "number" in c:
                    # one line at a given line number (G21-5, rise's M-7): that line is the row's line, or it is not
                    n = int(c["number"])
                    at = lines[n - 1] if 0 < n <= len(lines) else None
                    return (at == str(self.text(c["line"]))) == bool(c.get("present", True))
                count = len(span_at(lines, str(self.joined(c["line"])).split("\n")))   # a span of one line or more (EV-6)
                if "count" in c:
                    return count == c["count"]
                return (count > 0) == bool(c.get("present", True))
            if read == "identity":
                return self.fs.identity(self.text(c["path"])) == self.value(c["equals"])
            if read == "mode":
                path = self.text(c["path"])
                return self.fs.lexists(path) and (self.fs.mode(path) & ~int(c.get("at_most", 0o600)) & 0o777) == 0
            if read == "name-free":
                # RK5's check, as the owner ruled it (A55): his login zsh is asked, through the runner (`shellcheck`)
                # made for an operation (its probe's reads, its after-check's, an owner step's), the shell is a command of that
                # operation: no zsh in a system folder, its zsh gone at its start, or a start of it the system refuses, is the
                # runner's refusal (A112, A113, A125, A126); in a look, as before, a read that could not be made
                free, self.last_kind = shellcheck.name_free(self.session, str(self.value(c["name"])), of_operation=self.op is not None)
                self.last_command = None
                return UNREADABLE if free is None else free == bool(c.get("free", True))
            if read == "text":
                text = self.value(c["text"])
                if not isinstance(text, str) or not text:
                    return UNREADABLE              # a safe value the row names, and no other (SEC-4, A147)
                if c.get("command"):
                    command = self.commands.get(c["command"])
                    if command is None or (command.get("declaration") or {}).get("answer") != "protected text":
                        return UNREADABLE
                    result = self.caller(self.session, command, self.outputs, self.op, self.journal)
                    self.last_command, self.last_kind = getattr(result, "shown", None), result.kind
                    body = getattr(result, "protected_text", None)
                    if result.definite == "refusal" and not result.alternative and c.get("or_refused"):
                        # G23-16: the command answered a refusal its declaration lists (no crontab: `crontab -l` exits 1), a
                        # state of its own where the row says so, as `or_absent` has a file's absence
                        return True
                    if result.kind != "success" or body is None:
                        return UNREADABLE
                    lines = body.split("\n")
                else:
                    path = self.text(c["path"])
                    if not self.fs.isfile(path):
                        return bool(c.get("or_absent")) and not self.fs.lexists(path)
                    lines = self.fs.read_text(path).split("\n")
                if c.get("under") is not None:
                    # G25-4 (set's C2: "T16's after-test and after-check must verify both the link and its required heading
                    # placement"): only the lines that stand under the heading: after a line equal to it, before the next
                    # line that begins with `#`
                    heading = self.value(c["under"])
                    if not isinstance(heading, str) or not heading:
                        return UNREADABLE
                    under, inside = [], False
                    for line in lines:
                        if line == heading or line.startswith("#"):
                            inside = line == heading
                        elif inside:
                            under.append(line)
                    lines = under
                count = sum(1 for line in lines if text in line)
                if "count" in c:
                    return count == c["count"]
                return (count > 0) == bool(c.get("present", True))
            if read == "index-current":
                return index_current(self.session, self.value(c["repo"]), self.op is not None) == bool(c.get("is", True))
            if read == "ref":
                found = commitscan.repository(self.session, self.value(c["repo"])).ref("refs/heads/" + str(c["ref"]))
                if "equals" in c:
                    return found is not None and found == self.value(c["equals"])
                return (found is not None) == bool(c.get("exists", True))
            if read in ("commit-scan", "push-scan"):
                where = dict((k, self.value(c[k]) if c.get(k) is not None else None) for k in ("repo", "env_file", "link_file"))
                if read == "commit-scan":
                    named, why = commitscan.commit_scan(self.session, where["repo"], where["env_file"], where["link_file"],
                                                        c.get("fixed_words") or {}, of_operation=self.op is not None)
                else:
                    named, why = commitscan.push_scan(self.session, where["repo"], where["env_file"], where["link_file"],
                                                      c.get("fixed_words") or {}, c.get("branch") or "main", c.get("base"))
                self.last_hit = (named, why) if why else None
                return why is None
            if read == "command":
                command = self.commands.get(c.get("command"))
                if command is None:
                    return UNREADABLE
                result = self.caller(self.session, command, self.outputs, self.op, self.journal)
                self.last_command, self.last_kind = getattr(result, "shown", None), result.kind
                self.last_safe = result.safe()
                self.seen_safe.update((k, v) for k, v in self.last_safe.items() if isinstance(v, str) and len(v) <= 200)
                if result.kind in ("malformed", "timeout", "auth", "other"):
                    return UNREADABLE
                if result.kind != c.get("result", "success"):
                    return False
                if "field" not in c:
                    return True
                kept = result.fields.get(c["field"])
                if "present" in c:
                    return (kept is not None) == bool(c["present"])      # an optional field that stood nowhere (G19-9)
                if kept is None:
                    # G24-1 (OP-5): an equality on a field that stands nowhere is false (a tag read before it exists is not
                    # the scanned commit), so a probe that asks the after-test first reads the before-test next
                    return False if "equals" in c else UNREADABLE
                if "equals" in c:
                    want = c["equals"]
                    want = self.value(want) if isinstance(want, dict) else want
                    if kept.is_held:
                        # a held field compared in memory with a held output: the protected record's content (SEC-4)
                        if not c.get("compare_held"):
                            return False
                        expected = self.text(c["equals"]) if isinstance(c["equals"], dict) else want
                        return str(kept.held) == str(expected)
                    return kept.safe == want
                if "is_equal" in c:
                    return bool(kept.equal) == bool(c["is_equal"])
                return True
        except (OSError, UnicodeDecodeError):
            return UNREADABLE
        except values.Unsettled:
            return UNREADABLE
        except commitscan.Unreadable:
            return UNREADABLE
        except (ValueError, gitread.Unreadable):
            return UNREADABLE
        return UNREADABLE

    def evaluate(self, test):
        """True where every condition holds; False where one does not; UNREADABLE where one cannot be read."""
        verdict = True
        for c in test or []:
            answer = self.condition(c)
            if answer == UNREADABLE:
                return UNREADABLE
            if answer is False:
                verdict = False
        return verdict


def index_current(session, repo_path, of_operation):
    """Whether nothing is left for `git add --all` to stage (G19-10): every path of the index stands in the working tree with
    the content the index holds for it, and every other file is one git ignores, as git itself answers (`commitscan`)."""
    import os
    from . import commitscan, gitread
    fs = session.world.fs
    repo = commitscan.repository(session, repo_path)
    try:
        index = repo.index()
    except gitread.Unreadable:
        raise commitscan.Unreadable(repo_path)
    folders = set()
    for name, stages in index.items():
        path = os.path.join(repo.top, name)
        if fs.islink(path) or not fs.isfile(path) or gitread.blob_id(fs.read(path)) != stages[0][1]:
            return False
        parts = name.split("/")
        folders.update("/".join(parts[:i]) for i in range(1, len(parts)))
    pending = [""]
    while pending:
        rel = pending.pop(0)
        for entry in sorted(fs.listdir(os.path.join(repo.top, rel) if rel else repo.top)):
            sub = rel + "/" + entry if rel else entry
            if sub == ".git" or sub in index:
                continue
            full = os.path.join(repo.top, sub)
            if fs.isdir(full) and not fs.islink(full):
                if sub in folders or not commitscan.git_ignores(session, repo.top, sub, of_operation):
                    pending.append(sub)
            elif not commitscan.git_ignores(session, repo.top, sub, of_operation):
                return False
    return True


def tracked_state(fs, path, facts=("exists", "identity", "sha256", "mode")):
    """The tracked state of the thing at a path: the facts its row says the run records, each the
    tool's own measure."""
    out = {"path": path}
    exists = fs.lexists(path)
    if "exists" in facts:
        out["exists"] = exists
    if "identity" in facts:
        out["identity"] = fs.identity(path) if exists else None
    if "sha256" in facts:
        out["sha256"] = fsio.sha256_hex(fs.read(path)) if exists and fs.isfile(path) else None
    if "mode" in facts and exists:
        out["mode"] = fs.mode(path)
    return out


def file_lines(text):
    """A file's lines, and whether its last line ends with a newline. A file of no bytes has no line."""
    if text == "":
        return [], False
    parts = text.split("\n")
    if parts[-1] == "":
        return parts[:-1], True
    return parts, False


def join_lines(lines, terminated):
    return "\n".join(lines) + ("\n" if terminated and lines else "")


def span_at(lines, span):
    """Every place at which the lines of `span` stand next to each other, in order, in `lines`."""
    k = len(span)
    return [i for i in range(len(lines) - k + 1) if lines[i:i + k] == span] if k else []
