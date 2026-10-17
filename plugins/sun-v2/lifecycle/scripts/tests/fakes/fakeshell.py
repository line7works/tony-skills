#!/usr/bin/python3
"""The fixture's login zsh (the frame's SEC-3, its command row and test line; RUN-7; EV-6; RK12; RK13). Standard library only.

    zsh [-l] [-i] -c LINE ARG0 NAME

Started from a system folder of the fixture's search list (`tests/fakes/system/zsh`). It answers as his login zsh would
running the tool's one fixed line: it hands LINE, exactly as the tool wrote it, to the system's own zsh (`/bin/zsh`)
started with no startup files of its own (`-f`), with NAME as the line's one argument, after that shell has read the
fixture's own files the way a shell started with the flags it was given reads them:

- as a login shell (`-l`), his own login file, `$HOME/.zprofile` (for example `path+=(FOLDER)`, as a package manager's
  line puts a folder on the shell's path);
- as an interactive shell (`-i`), his own `$HOME/.zshrc` (an `alias`, a shell function, a function behind a reserved
  word, a `zmodload` that brings in a module's builtins).

So what the line counts (a program in a folder of that shell's path, an alias, a shell function, a builtin, a reserved
word) is counted by zsh itself, over the fixture's files and never over the account's: its `HOME` is the fixture home
and the system's zsh reads no startup file of its own. The exit number is the one the line gives (80 taken, 81 free).

It keeps its record under `$HOME/.fakes/zsh/`: `calls.jsonl` (every call's arguments, the names and values of the
environment it was given, its working directory, and, in the shape every fake's record has, that it changed nothing).
`plan.json` tells it, for every call, to print a value on both of its streams (`print`), to write a file of its own into
its `TMPDIR` (`tmpfile`), to hang (`hang`), or to end with another exit number (`exit`), as a startup file that prints,
writes its cache, waits or fails would make it.
"""
import json
import os
import subprocess
import sys
import time

HOME = os.environ.get("HOME", "")
ROOT = os.path.join(HOME, ".fakes", "zsh")
SHELL_OWN = ("PWD", "SHLVL", "_", "OLDPWD", "FAKE_GIVEN")
SYSTEM_ZSH = "/bin/zsh"
# what the system zsh runs: the fixture's own files as the flags say, then the tool's line, `$1` the name
READER = ('if [[ $FAKE_LOGIN == 1 && -r $HOME/.zprofile ]]; then source $HOME/.zprofile; fi\n'
          'if [[ $FAKE_INTERACTIVE == 1 && -r $HOME/.zshrc ]]; then source $HOME/.zshrc; fi\n'
          'eval "$FAKE_LINE"\n')


def given():
    out = {}
    for line in os.environ.get("FAKE_GIVEN", "").split("\n"):
        if "=" in line:
            name, value = line.split("=", 1)
            if name not in SHELL_OWN:
                out[name] = value
    return out


def load(path, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def main():
    argv = sys.argv[1:]
    env = given()
    os.makedirs(ROOT, exist_ok=True)
    with open(os.path.join(ROOT, "calls.jsonl"), "a") as fh:
        fh.write(json.dumps({"tool": "zsh", "argv": argv, "env_names": sorted(env), "env_values": env, "cwd": os.getcwd(),
                             "pid": os.getpid(), "changing": False}, sort_keys=True) + "\n")   # a question: it changes nothing
    flags, i = set(), 0
    while i < len(argv) and argv[i].startswith("-") and argv[i] != "-c":
        flags.update(argv[i][1:])
        i += 1
    if i >= len(argv) or argv[i] != "-c" or len(argv) < i + 4:
        sys.exit(2)
    name = argv[i + 3]
    login, interactive = "l" in flags, "i" in flags
    plan = load(os.path.join(ROOT, "plan.json"), {})
    if plan.get("print"):
        sys.stdout.write("startup: %s\n" % plan["print"])
        sys.stderr.write("startup: %s\n" % plan["print"])
        sys.stdout.flush()
        sys.stderr.flush()
    if plan.get("tmpfile"):
        with open(os.path.join(env.get("TMPDIR", "/nonexistent"), "zsh-cache-%d" % os.getpid()), "w") as fh:
            fh.write("a cache of the shell's own\n")
    if plan.get("hang"):
        time.sleep(600)
    if plan.get("exit") is not None:
        sys.exit(int(plan["exit"]))
    line = argv[i + 1]
    child = dict(env)
    child.update({"FAKE_LOGIN": "1" if login else "0", "FAKE_INTERACTIVE": "1" if interactive else "0", "FAKE_LINE": line})
    code = subprocess.call([SYSTEM_ZSH, "-f", "-c", READER, "zsh", name], env=child, stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sys.exit(code)


main()
