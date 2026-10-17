"""The reads a test is made of (the frame's RUN-6, OP-5, OP-8, OP-9, KEEP-3).

A test is a list of conditions, every one of which must hold. A condition is one read and what it
must show:

    {"read": "path", "path": V, "is": "absent" | "file" | "dir" | "present"}
    {"read": "sha256", "path": V, "equals": V}
    {"read": "line", "path": V, "line": V, "present": true | false, "count": n}
    {"read": "identity", "path": V, "equals": V}
    {"read": "mode", "path": V, "at_most": 0o600}
    {"read": "name-free", "name": V}                 no program, alias, shell function, builtin or reserved word of
                                                     that name, as his login zsh holds them (RK5's check; RUN-7,
                                                     SEC-3, A55, A63)
    {"read": "command", "command": NAME, "result": KIND, "field": F, "equals": WORD}
    {"read": "commit-scan", "repo": V, "env_file": V, "link_file": V, "fixed_words": {VAR: [WORD]}}
    {"read": "push-scan", ..., "branch": WORD, "base": REF}   SEC-10's check before a commit and before a push
                                                             (`commitscan`); false on a hit, which `last_hit` names

`evaluate` answers True, False, or `UNREADABLE` where a read failed, was partial, was made as the
wrong account, or ran out of time. A probe only reads: a command used in a test is one whose
declaration says it changes nothing.
"""
from . import commitscan, fsio, shellcheck, values

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

    def condition(self, c):
        read = c.get("read")
        try:
            if read == "path":
                path = self.value(c["path"])
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
                path = self.value(c["path"])
                if not self.fs.isfile(path):
                    return False
                return fsio.sha256_hex(self.fs.read(path)) == self.value(c["equals"])
            if read == "line":
                path = self.value(c["path"])
                if not self.fs.isfile(path):
                    return False          # no file is there: it is in neither state a row names by its lines
                lines = self.fs.read_text(path).split("\n")
                count = len(span_at(lines, str(self.text(c["line"])).split("\n")))     # a span of one line or more (EV-6)
                if "count" in c:
                    return count == c["count"]
                return (count > 0) == bool(c.get("present", True))
            if read == "identity":
                return self.fs.identity(self.value(c["path"])) == self.value(c["equals"])
            if read == "mode":
                path = self.value(c["path"])
                return self.fs.lexists(path) and (self.fs.mode(path) & ~int(c.get("at_most", 0o600)) & 0o777) == 0
            if read == "name-free":
                # RK5's check, as the owner ruled it (A55): his login zsh is asked, through the runner (`shellcheck`)
                # made for an operation (its probe's reads, its after-check's, an owner step's), the shell is a command of that
                # operation: no zsh in a system folder, its zsh gone at its start, or a start of it the system refuses, is the
                # runner's refusal (A112, A113, A125, A126); in a look, as before, a read that could not be made
                free, self.last_kind = shellcheck.name_free(self.session, str(self.value(c["name"])), of_operation=self.op is not None)
                self.last_command = None
                return UNREADABLE if free is None else free
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
                if result.kind in ("malformed", "timeout", "auth", "other"):
                    return UNREADABLE
                if result.kind != c.get("result", "success"):
                    return False
                if "field" not in c:
                    return True
                kept = result.fields.get(c["field"])
                if kept is None:
                    return UNREADABLE
                if "equals" in c:
                    want = c["equals"]
                    want = self.value(want) if isinstance(want, dict) else want
                    if kept.is_held:
                        return kept.held == want if c.get("compare_held") else False
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
