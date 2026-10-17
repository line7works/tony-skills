"""The one runner (the frame's SEC-3). Every child the lifecycle code starts is started here.

- The command is an argument list, never a shell line. A command with no declaration is refused, so
  is an argument on the tool's registered list of debug, verbose and trace flags, and so is any
  argument or environment value of the child as it would be started that holds an entry of the
  secret register in any form: the values of the base names and the path of the temporary folder
  among them (SEC-3's refusals row; the reviewer's D8-C), and the program's full path, which the
  child is started with first, before its arguments (the reviewer's D8-X; A140).
- The program is found by the runner itself: its declared name is looked for in the folders of the
  search list (`facts.search_list`), in the list's order, and the first file of that name is started
  by its full path. The session's path is not consulted. A name found in no folder is a tool not
  found (RUN-7). For a command of an operation a file the runner found that is gone as it starts it,
  so that no child is created, is a tool not found too, refused (A109); and so is a start the system
  refuses before the program runs, the file still there, where the system's answer shows that the
  program never ran: "start refused" (A113). A program in a folder the owner named is started as it
  stands there, with no check (RK11).
- The environment is built from nothing: `PATH`, set to the search list; `HOME`, `USER` and `LOGNAME`
  as the tool itself has them; `LANG` and `LC_ALL` set to one fixed locale; `TMPDIR` set to a private
  folder in the run directory, and for a child of a start that is no summons, which has none, no
  `TMPDIR`; for the shortcut check's shell alone, his account's own temporary folder (A58); and the names the provider module registered for that command, which
  never stand in the place of a base name. Nothing else of the session reaches a child.
- Files it makes: a file-creation mask that gives every new file to the owner only; the working
  directory the caller declares.
- Standard input is empty. Both output streams are captured in memory up to a fixed size and handed
  only to the parser (`results.py`); standard error is read and dropped. Output over the size is
  discarded. A declaration whose output is "none" (the shortcut check's shell) has both streams read and dropped.
- Lifetime: its own process group; a time limit from the declaration; at the limit, and when the
  call ends, the runner ends the group it started, every descendant in it included, and nothing else.
"""
import errno
import os
import selectors
import signal
import subprocess
import time

from . import results

LOCALE = "C"
MOST_OUTPUT = 1024 * 1024
AS_THE_TOOL_HAS_THEM = ("HOME", "USER", "LOGNAME")


class Refused(RuntimeError):
    """The runner refused the command before the start. `reason` is the tool's own fixed word."""

    def __init__(self, reason, program=None, at_start=False):
        RuntimeError.__init__(self, reason)
        self.reason = reason
        self.program = program            # the declared name, where the reason is a tool not found
        # a refusal met where the runner starts the file it found, so that no child is created: that file gone (A109), or the
        # system refusing the start before the program runs, the file still there (A113) (SEC-3's command row): for a
        # command with a secret field, met after the step record that a receipt is due (SEC-12)
        self.at_start = at_start


class Context(object):
    def __init__(self, register, run_dir, search, find_in=None, tmpdir=None, of_operation=False):
        self.register = register
        self.run_dir = run_dir
        self.search = list(search)        # the tool's search list, in its order (SEC-3): the child's PATH
        # where the program is looked for, where that is not the whole search list: for the shortcut check's shell, the
        # system folders of the list alone (SEC-3's command row, A55)
        self.find_in = list(find_in) if find_in is not None else None
        # the child's TMPDIR where it is not the run directory's: for the shortcut check's shell, his account's own
        # temporary folder, read from the system (SEC-3's environment row, A58)
        self.tmpdir = tmpdir
        # a command of an operation (SEC-3's command row, A109): where the file the runner found is gone as it starts it, so
        # that no child is created, that is a refusal of the runner's, a tool not found. For any other command (a look's, a
        # read a later invocation makes at its start, a start that is no summons) no rule says so, and such a start stays
        # what it was before A109, a child that could not be started (report-17)
        self.of_operation = of_operation


def find(world, name, search):
    """The full path of the first file of the declared name in the folders of the search list, in the list's
    order; None where no folder holds one. A name that is not a bare name names no program on the list."""
    if not isinstance(name, str) or not name or os.sep in name or name in (".", ".."):
        return None
    for folder in search:
        path = os.path.join(folder, name)
        if world.fs.is_program_file(path):
            return path
    return None


def _owner_only_children():
    os.umask(0o077)


def _end_group(pgid):
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass


def check(world, context, declaration, argv, registered_env):
    """SEC-3's refusals, made on the command as `run` would start it and starting nothing: a command with no declaration;
    an argument on the registered list of trace flags; an argument or an environment value of the child, the base names'
    values and the temporary folder's path among them, that holds an entry of the register; the runner's search, a
    program in no folder of the search list (A109); and the full path the search found, which the child is started with
    first, that holds an entry (D8-X, A140). Raises `Refused`; returns the file the search found. SEC-12
    (batch 44, A102): "A command the runner refuses (SEC-3) has no execution and starts no child: the runner's check is made
    before that step record [that a receipt is due], and where it refuses, no receipt is due." `run` makes the same checks
    again, in its own order, before it starts the child."""
    if not isinstance(declaration, dict) or not declaration.get("tool"):
        raise Refused("no declaration")
    argv = [str(a) for a in argv]
    flags = set(declaration.get("trace_flags") or [])
    if any(a in flags or a.split("=", 1)[0] in flags for a in argv):
        raise Refused("trace flag")
    env = _child_env(world, context, registered_env)
    if any(context.register.holds(a) for a in argv) or any(context.register.holds(v) for v in env.values()):
        raise Refused("register entry")
    # SEC-12 (batch 46, A110): "The runner's search for the program is part of its check: a program in no folder of the
    # search list is refused there, before that step record, and no receipt is due (SEC-3; the owner's ruling, A109)." Made
    # after the register's check, so that where both hold the refusal named is the register entry (report-16's choice; no
    # rule orders them, A110). The file found is what `run` is to start
    program = find(world, declaration["tool"], context.find_in if context.find_in is not None else context.search)
    if program is None:
        raise Refused("tool not found", declaration["tool"])
    # the child is started with the program's full path first, before its arguments (`run`: `[program] + argv`), so the
    # path is checked as an argument is (SEC-3's refusals row: "every argument and every environment value of the child as
    # it would be started"; the reviewer's D8-X; the owner's ruling, A140)
    if context.register.holds(program):
        raise Refused("register entry")
    return program


def _gone(world, program, failed):
    """Whether a start that failed did so because no file stands at the path the runner found (SEC-3's command row, A109:
    "a file that the runner found and that is gone as it starts it, so that no child is created"): the system's own answer
    that no file is there, naming that path, and no file there now. A start that fails for any other cause (a file that
    cannot be run, a program it names that is missing, a working directory that is gone) is not read as the file gone: the
    frame's words do not say whether it is (report-17, question 34)."""
    if not isinstance(failed, FileNotFoundError) or failed.filename != program:
        return False
    try:
        return not world.fs.lexists(program)
    except OSError:
        return False


# The causes A113 names, each the system's answer to a start that shows that the program never ran, the file still there
# (SEC-3's command row): read only from the answer the start raised, by its number, the path it names, and the file found
# still standing at the path the runner started.
NEVER_RAN = {errno.EACCES: "the file not runnable", errno.ENOENT: "a program its first line names missing",
             errno.ENOEXEC: "a format the system cannot run"}


def _never_ran(world, program, cwd, failed):
    """Where a start that failed did so before the program ran, the file still there, and the system's answer shows it
    (SEC-3's command row, A113: "the file not runnable, a program its first line names missing, a format the system cannot
    run, the working folder gone, or no process to be had, wherever the system's answer shows that the program never
    ran"): the cause, in the tool's fixed words; None where the runner cannot read the answer so (a start of that kind is
    no refusal, and stays as OP-6 has a killed child).

    - The file not runnable, a program its first line names missing, a format the system cannot run: the system's refusal
      to run the file, EACCES, ENOENT or ENOEXEC, naming the very path the runner started, with a file still standing at
      that path (an ENOENT with no file there is the file gone, A109, `_gone`).
    - The working folder gone: ENOENT naming the working folder the runner handed the start (the system's change into it is
      made before the program is run, and fails so where no folder stands there).
    - No process to be had: EAGAIN naming no path, the system's answer that it cannot make the process.
    Any other answer, among them another number, or one of these numbers naming another path or none, is not read as the
    program never having run. SEC-3's command row (batch 49, A117): "for one of these five causes and for no other ... A
    start the system refuses for any cause that is none of the five ... [is] no refusal" (an argument list too long, E2BIG,
    among them)."""
    if not isinstance(failed, OSError):
        return None
    number, named = failed.errno, failed.filename
    if number == errno.EAGAIN and named is None and getattr(failed, "filename2", None) is None:
        return "no process to be had"
    if number == errno.ENOENT and cwd is not None and named == cwd and named != program:
        return "the working folder gone"
    if number not in NEVER_RAN or named != program:
        return None
    try:
        there = world.fs.lexists(program)
    except OSError:
        return None
    return NEVER_RAN[number] if there else None


def _child_env(world, context, registered_env):
    """The child's environment, built from nothing (SEC-3's environment row)."""
    env = dict((str(name), str(value)) for name, value in (registered_env or {}).items())
    env["PATH"] = os.pathsep.join(context.search)
    for name in AS_THE_TOOL_HAS_THEM:
        if world.env.get(name):
            env[name] = world.env[name]
        else:
            env.pop(name, None)
    env["LANG"] = env["LC_ALL"] = LOCALE
    if context.tmpdir:
        env["TMPDIR"] = context.tmpdir
    elif context.run_dir:
        env["TMPDIR"] = os.path.join(context.run_dir, "tmp")
    # a child of a start that is no summons is given no TMPDIR: that start makes no run directory, and nothing of
    # the session stands in its place (SEC-3's environment row, A53)
    return env


def run(world, context, declaration, argv, registered_env, cwd, program=None):
    """Start one declared command and return `results.Raw`. Raises `Refused` before the start, and, for a command of an
    operation, where the file it found is gone as it starts it (A109) or the system refuses the start before the program
    runs, the file still there, its answer showing that the program never ran (A113). `program` is the file `check` found,
    where the caller made the runner's check before a step record of its own (SEC-12): it is started without a second
    search."""
    if not isinstance(declaration, dict) or not declaration.get("tool"):
        raise Refused("no declaration")
    argv = [str(a) for a in argv]
    flags = set(declaration.get("trace_flags") or [])
    if any(a in flags or a.split("=", 1)[0] in flags for a in argv):
        raise Refused("trace flag")
    if program is None:
        program = find(world, declaration["tool"], context.find_in if context.find_in is not None else context.search)
    if program is None:
        raise Refused("tool not found", declaration["tool"])
    env = _child_env(world, context, registered_env)
    # every argument and every environment value of the child as it would be started, the base names' values and
    # the temporary folder's path among them: where one holds an entry, the command is refused before any child. The
    # child is started with the program's full path first (`[program] + argv` below), so that path is checked as an
    # argument is (the reviewer's D8-X; the owner's ruling, A140)
    if any(context.register.holds(a) for a in [program] + argv) or any(context.register.holds(v) for v in env.values()):
        raise Refused("register entry")
    limit = float(declaration.get("time_limit") or 60)
    # a declaration whose output is "none" has nothing it prints read at all: both streams are read and dropped, and the
    # parser is handed the exit alone (the shortcut check's shell: "nothing the shell prints is read", SEC-3, A55)
    quiet = declaration.get("output") == "none"
    world.note("pre", "child", declaration["tool"], argv=list(argv), env_names=sorted(env), path=program)
    start = world.start or subprocess.Popen    # the system's start of a process; a test's fixture system stands here (A115)
    try:
        proc = start([program] + argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                     preexec_fn=_owner_only_children, close_fds=True)
    except OSError as failed:
        world.note("post", "child", declaration["tool"], started=False)
        if context.of_operation and _gone(world, program, failed):
            # SEC-3's command row (batch 46, A110): "For a command of an operation it is also a refusal of the runner's (the
            # refusals row), and so is a file that the runner found and that is gone as it starts it, so that no child is
            # created". No process of the command's was handed back, so none was created and none is waited for
            raise Refused("tool not found", declaration["tool"], at_start=True)
        if context.of_operation and _never_ran(world, program, cwd, failed):
            # SEC-3's command row (batch 48, A114): "So too is a start of a command of an operation that the system refuses
            # before the program runs, the file still there ... wherever the system's answer shows that the program never
            # ran. Such a start creates no child of the program, whatever the system made for the start and ended before the
            # program ran (the owner's ruling, A113)." No process of the command's was handed back: what the system made for
            # the start, where it made one, ended inside the start and was never the program
            raise Refused("start refused", declaration["tool"], at_start=True)
        # SEC-3's command row: "A start whose answer the runner cannot read as one in which the program never ran, and a
        # start that creates a child, are no refusal, however that child ends: they stay as OP-6 has a killed child"
        return results.Raw(None, b"", killed=True)
    pgid = proc.pid
    world.note("mid", "child", declaration["tool"], started=True)
    chunks, size, oversize, timed_out = [], 0, False, False
    deadline = time.time() + limit
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ, "out")
    selector.register(proc.stderr, selectors.EVENT_READ, "err")
    open_streams = 2
    while open_streams:
        remaining = deadline - time.time()
        if remaining <= 0:
            timed_out = True
            break
        exited = proc.poll() is not None
        ready = selector.select(0 if exited else min(remaining, 0.2))
        for key, _mask in ready:
            data = os.read(key.fileobj.fileno(), 65536)
            if not data:
                selector.unregister(key.fileobj)
                open_streams -= 1
                continue
            if key.data == "out" and not quiet:    # standard error is read and dropped: nothing a tool prints is kept
                size += len(data)
                if size > MOST_OUTPUT:
                    oversize = True
                else:
                    chunks.append(data)
        if oversize or (exited and not ready):
            break                            # the child has ended; a descendant holding the pipe is not waited for
    selector.close()
    if timed_out or oversize:
        _end_group(pgid)
    try:
        code = proc.wait(timeout=max(0.1, deadline - time.time()) if not (timed_out or oversize) else 5)
    except subprocess.TimeoutExpired:
        timed_out = True
        _end_group(pgid)
        code = proc.wait()
    _end_group(pgid)                         # the call is ending: every descendant in the group goes with it
    proc.stdout.close()
    proc.stderr.close()
    world.note("post", "child", declaration["tool"], started=True)
    if timed_out:
        return results.Raw(None, b"", timed_out=True)
    if oversize:
        return results.Raw(code, b"", oversize=True)
    if quiet:
        return results.Raw(code, b"") if code >= 0 else results.Raw(None, b"", killed=True)
    if code < 0:
        return results.Raw(None, b"", killed=True)
    return results.Raw(code, b"".join(chunks))
