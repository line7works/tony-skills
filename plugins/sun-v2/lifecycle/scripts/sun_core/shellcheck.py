"""The check that a shortcut's name is free: the one command SEC-3 names that is a shell line (the owner's ruling A55;
RK12; RUN-7's `in` row, EV-6).

SEC-3's command row: "The check that a shortcut's name is free starts his shell, zsh, which the runner finds in the
system folders of the search list, the way a terminal window starts it by default: as a login and interactive shell,
with an environment built as the next row says. It hands the shell one fixed line written in the tool, which asks
whether a command of that name exists, and passes the name as a separate argument, never written into the line. The
declaration maps the shell's exit number to taken or free, and nothing the shell prints is read."

- The shell is found by the one runner in the world's system folders alone (`world.system_folders`), and started by
  its full path, through the runner like every child: the runner's refusals hold for it (the name and every value of
  its environment are checked against the register before it starts).
- Its environment is the runner's: `PATH` the tool's whole search list, `HOME`, `USER` and `LOGNAME` as the tool has
  them, the fixed locale, and as its `TMPDIR` his account's own temporary folder, read from the system and not from the
  session (`world.user_temp`; SEC-3's environment row, A58). It is the one child given that folder.
- The line is `LINE`, written here once. It counts the name taken where any program, alias, shell function, builtin
  or reserved word of it exists for that shell, wherever it stands, though another command of the name comes first
  (RUN-7's `in` row as batch 23 words it; the owner's ruling A63): a program is a file that is a regular file and can be
  run, in any folder of the shell's `path`, in its order; an alias (a global one among them), a function, a builtin and
  a reserved word are those the shell holds, a disabled one among them, read from zsh's own tables (`aliases`,
  `galiases`, `functions`, `builtins`, `reswords` and their `dis_` twins). It does not ask `whence`, which names only
  what the shell would run first (A62). It ends 80 taken and 81 free. The name is the line's `$1`, handed as an argument
  of its own after the line and `$0`, never written into the line; the line holds no command a startup file's alias can
  change (`exit` is written `\exit`), and a function of the name `exit`, `builtin` or `whence` that a startup file
  defines cannot make it read free: such a function ends it with a number that is neither, a read that failed.
- The declaration maps 80 to taken and 81 to free; every other ending (another number, a time limit met, a child
  killed) is a read that failed, and the look stops (RK12: "A startup file that waits or fails ends the check at its
  time limit, and the look stops"). Nothing the shell prints is read: its output is "none", both streams read and
  dropped by the runner.

Each time the check is made, the system's startup files and his own run as a child of the tool: that is RK12, which
the owner accepted. RK12 belongs to no one operation, and no mark is recorded for it (RISK-1). A builtin of the name
that a startup file brings in between the check and the add is RK13 (A63); a shortcut's add and its put-back carry
RK13's mark beside RK5's (RISK-1; `rows.py`, `engine.mark_risks`).
"""
import os
import stat as statmod

from . import results, runner

LINE = ('for _sunv2 in $path; do [[ -f $_sunv2/$1 && -x $_sunv2/$1 ]] && \\exit 80; done; '
        '(( ${+aliases[$1]} || ${+galiases[$1]} || ${+dis_aliases[$1]} || ${+dis_galiases[$1]} || ${+functions[$1]} '
        '|| ${+dis_functions[$1]} || ${+builtins[$1]} || ${+dis_builtins[$1]} || ${reswords[(Ie)$1]} '
        '|| ${dis_reswords[(Ie)$1]} )) && \\exit 80; \\exit 81')
TAKEN, FREE = "80", "81"
TIME_LIMIT = 20
DECLARATION = {
    "tool": "zsh",
    "template": [{"literal": "-l"}, {"literal": "-i"}, {"literal": "-c"}, {"literal": LINE}, {"literal": "zsh"},
                 {"param": "name"}],
    "time_limit": TIME_LIMIT,
    "exits": {TAKEN: "success", FREE: "not-found"},
    "fields": [],
    "definite": {"success": ["success"], "refusals": ["not-found"]},
    "trace_flags": ["-x", "-v", "--xtrace", "--verbose"],
    "output": "none",
    # the working folder it starts in, as a terminal window starts his shell by default: his home (SEC-3's files row, "the
    # working directory the row declares")
    "working_folder": "home",
}


def account_temp(world):
    """His account's own temporary folder as the system gives it, or None where the system gives none or one that is
    not an owner-only folder of his. SEC-3's environment row (batch 22): "Where the system gives no such folder, or gives
    one that is not an owner-only folder of his account, that shell is not started: the check is a failed read, and the
    look ends as RUN-7's planning stop, naming the check. No rule gives that shell another folder, and the tool never
    picks one (GOV-1)"."""
    folder = world.user_temp()
    if not folder:
        return None
    try:
        st = world.fs.lstat(folder)
    except OSError:
        return None
    if not statmod.S_ISDIR(st.st_mode) or statmod.S_IMODE(st.st_mode) & 0o077 or st.st_uid != os.geteuid():
        return None
    return folder


def name_free(session, name, of_operation=False):
    """(True where his login zsh holds no program, alias, shell function, builtin or reserved word of that name, False
    where it holds one, None
    where the check could not be made; the result's kind). Raises `runner.Refused` before the start; and, made for an
    operation (`of_operation`: at its probe, the read of its before-test, or another read of that operation), where no
    system folder holds zsh (A125, A126), where the zsh the runner found is gone as it starts it (A109, A112) or where the
    system refuses its start before it runs, the file still there (A113): the shell is that operation's command wherever the
    check is made for it (SEC-3's command row; A94, A117)."""
    world = session.world
    folder = account_temp(world)
    if folder is None:
        return None, "other"
    if not of_operation and runner.find(world, DECLARATION["tool"], world.system_folders) is None:
        # SEC-3's command row (batch 28): "Where no system folder of the search list holds zsh, the check cannot be made: it
        # is a failed read, and the look ends as RUN-7's planning stop for a read that failed, naming the check. It is not
        # RUN-7's line for a program in no folder of the search list"; no folder he names is searched for this shell. That
        # is the look's (batch 55, A126: "the look keeps its failed read"). Made for an operation, at its probe, its
        # after-check or an owner step's read, it is no failed read (batches 54 and 55, A125, A126): "it is a program that
        # operation needs missing when the runner looks for it, the runner's refusal (the owner's ruling, A109)", so the
        # runner is asked below, finds no zsh in the system folders, starts no shell and raises `Refused("tool not found")`
        return None, "other"
    search = session.facts.search_list(world.fs, world.system_folders)
    context = runner.Context(session.register, session.run_dir, search, find_in=world.system_folders, tmpdir=folder,
                             of_operation=of_operation)
    argv = ["-l", "-i", "-c", LINE, "zsh", str(name)]
    cwd = (session.facts.home or None) if DECLARATION["working_folder"] == "home" else None
    raw = runner.run(world, context, DECLARATION, argv, {}, cwd)
    result = results.Parser(DECLARATION, raw, session.register).finish()
    return {"success": False, "not-found": True}.get(result.kind), result.kind
