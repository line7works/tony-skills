"""The slice's named checks: what the answer reported, or what this core observed.

Honest failure handling (lane contract section 9; amendment A3 item 1). The slice's `Checks:`
list is the closed set that gates the card: a check the slice names and the answer does not
report is `not_run` with an empty output, and a check the answer reports that the slice does not
name is carried through with `named_by_slice: false` so it is visible and never gates anything.

Two sources per row, and the result always says which:

    recorded  the executor ran it and the answer carries its result and its output. The default.
    rerun     `rerun_checks` was set, so this core ran the command the SLICE names, in the
              workspace, and reports what it observed.

A rerun is bound as data, never as shell text: the command is split with `shlex` and run without
a shell. A command carrying shell syntax (a pipe, a redirect, `&&`, a variable, a glob) is NOT
rerun — this core will not reconstruct a shell's meaning. `sh checks/unit.sh` runs; `a | b`
does not.

**A rerun that was asked for and could not execute is `not_run`** (Astra's F2): shell syntax, an
executable that is not there, a timeout, or a report-only run (F15, below). The row keeps the
refusal reason in `rerun_refused` and whatever the attempt captured in `output`, and it keeps the
executor's claim SEPARATELY, in `recorded_result` and `recorded_output`, so the claim is visible
and never stands in for an observation this core could not make. A `not_run` named check keeps
the card where it is and the run finishes `checks_not_passed`.

**One command's output is never attributed to another named command** (F2). The answer names the
command it ran for each check; when that command is not the command the SLICE names for the
check, what the answer reports is the output of a different command. The row then reports the
named check as `not_run`, says why in `attribution_refused`, and keeps the answer's command,
result and output separately (`recorded_command`, `recorded_result`, `recorded_output`). Two
commands are the same when they split into the same arguments. When a rerun was asked for and
the NAMED command executes (Astra's N2), the row reports that observation (`source: "rerun"`, its
exit code, output and `passed` or `failing`) and still keeps the rejected recorded evidence apart,
with `attribution_refused` saying so; a rerun that cannot execute leaves the row `not_run`.

**Report-only reruns nothing in the live workspace** (F15). A check command is an unrestricted
child process, and report-only promises that nothing reaches the workspace, child writes
included. This core has no read-only execution boundary to put around a child, so in a
report-only run every requested rerun is `not_run` with `rerun_refused` saying so.

This core never reruns a model.
"""
import os
import shlex
import subprocess

SHELL_SYNTAX = set("|&;<>()$`\\\"'*?[]{}~\n")
RESULTS = ("passed", "failing", "not_run")


def _runnable(command):
    """(argv, None) when the command can be run without a shell, else (None, why)."""
    if not command:
        return None, "the slice names no command for this check"
    if any(ch in SHELL_SYNTAX for ch in command):
        return None, ("the command carries shell syntax, and this core runs a command as an argv "
                      "list and never through a shell")
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return None, "the command does not split into arguments: %s" % exc
    if not argv:
        return None, "the command is empty"
    return argv, None


def run_command(workspace, command, timeout=600):
    """Run one check command in the workspace, bound as argv. Returns (exit_code, output, why)."""
    argv, why = _runnable(command)
    if argv is None:
        return None, "", why
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "/"),
           "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        proc = subprocess.run(argv, cwd=workspace, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout)
    except OSError as exc:
        return None, "", "the command could not be started: %s" % exc
    except subprocess.TimeoutExpired as exc:
        captured = exc.output or b""
        return None, captured.decode("utf-8", "replace"), (
            "the command did not finish within %d seconds" % timeout)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), None


def same_command(one, two):
    """Do two command strings name the same command? Compared as the arguments they split into,
    so spacing does not matter and nothing else is normalized away."""
    def split(text):
        try:
            return shlex.split(text or "")
        except ValueError:
            return (text or "").split()
    return split(one) == split(two)


def _blank(name, command, named_by_slice):
    return {
        "name": name,
        "command": command,
        "result": "not_run",
        "exit_code": None,
        "output": "",
        "source": "recorded",
        "named_by_slice": named_by_slice,
        "rerun_refused": None,
        "recorded_result": None,
        "recorded_command": None,
        "recorded_output": None,
        "attribution_refused": None,
    }


def _recorded_row(named, reported):
    row = _blank(named["name"], named.get("command"), True)
    if not reported:
        return row
    if named.get("command") and not same_command(reported.get("command"), named.get("command")):
        # The answer ran something else under this check's name. Its output is that command's,
        # never the named check's: the named check was not run, and the claim is kept beside it.
        row.update(recorded_command=reported.get("command"),
                   recorded_result=reported.get("result"),
                   recorded_output=reported.get("output"),
                   attribution_refused=(
                       "the answer reports this check as `%s`, and the slice names it as `%s`; the "
                       "output of one command is never the result of another, so the named check "
                       "was not run" % (reported.get("command"), named.get("command"))))
        return row
    row.update(result=reported.get("result") or "not_run", exit_code=reported.get("exit_code"),
               output=reported.get("output") or "")
    return row


def _not_run(row, why, captured=""):
    """A requested rerun that could not execute: `not_run`, the claim kept separately."""
    if row["recorded_result"] is None and row["attribution_refused"] is None:
        row["recorded_result"] = row["result"]
        row["recorded_output"] = row["output"]
    row.update(result="not_run", exit_code=None, output=captured or "", source="rerun",
               rerun_refused=why)
    return row


def rows(contract_checks, answer_checks, workspace=None, rerun=False, rerun_blocked=None):
    """One row per check, the slice's in document order first, then any the answer adds.

    `contract_checks` is `[{"name", "command"}]` from the build doc; `answer_checks` is the
    recorded answer's `checks` list. With `rerun`, each named command is run in the workspace,
    unless `rerun_blocked` names why no child process may run there (a report-only run), in which
    case every named check is `not_run` with that reason.
    """
    reported = {}
    for row in answer_checks or []:
        reported.setdefault(row.get("name"), row)

    out = []
    for named in contract_checks or []:
        row = _recorded_row(named, reported.get(named["name"]))
        if rerun and rerun_blocked:
            _not_run(row, rerun_blocked)
        elif rerun:
            code, output, why = run_command(workspace, named.get("command"))
            if why is None:
                observed = "passed" if code == 0 else "failing"
                # A rerun that disagrees with what the answer recorded keeps both: the row
                # reports what this core observed, and `recorded_result` says what the answer
                # claimed, so the disagreement is visible rather than quietly overwritten.
                if row["attribution_refused"] is not None:
                    # Astra's N2: the answer's recorded evidence was REJECTED (another command
                    # under this check's name) and stays apart in `recorded_command`,
                    # `recorded_result` and `recorded_output`; the NAMED command has now been
                    # executed, so the row reports that observation, and says both things.
                    row["attribution_refused"] = (
                        "the answer reports this check as `%s`, and the slice names it as `%s`; "
                        "the output of one command is never the result of another, so the "
                        "answer's recorded command, result and output are rejected and kept apart, "
                        "and the result reported is the one observed when this core ran `%s`"
                        % (row["recorded_command"], named.get("command"), named.get("command")))
                elif observed != row["result"] and row["recorded_result"] is None:
                    row["recorded_result"] = row["result"]
                row["result"] = observed
                row["exit_code"] = code
                row["output"] = output
                row["source"] = "rerun"
            else:
                _not_run(row, why, output)
        out.append(row)

    named_names = set(row["name"] for row in out)
    for row in answer_checks or []:
        if row.get("name") in named_names:
            continue
        extra = _blank(row.get("name"), row.get("command"), False)
        extra.update(result=row.get("result") or "not_run", exit_code=row.get("exit_code"),
                     output=row.get("output") or "")
        out.append(extra)
    return out


def workspace_digest(workspace):
    """A digest of every byte under the workspace, `.git` excluded, ignored files INCLUDED.

    Astra's F15 remainder: the source identity sees tracked and untracked-but-not-ignored files,
    so a check that wrote a git-IGNORED file (a cache, a build product) changed the workspace
    without changing the identity, and the result claimed `wrote_nothing`. This measurement is
    taken right before the requested reruns and right after them; any difference is a child
    write. Each file contributes its path, its kind and mode, and its content (a symlink its
    target, never what it points at); a directory contributes its path, so an empty directory a
    child created is a change too. Nothing is followed outside the workspace.
    """
    import hashlib
    entries = []
    for base, dirs, files in os.walk(workspace, followlinks=False):
        rel_base = os.path.relpath(base, workspace)
        if rel_base == ".":
            dirs[:] = sorted(d for d in dirs if d != ".git")
        else:
            dirs[:] = sorted(dirs)
            entries.append("d\0" + rel_base.replace(os.sep, "/"))
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, workspace).replace(os.sep, "/")
            if rel == ".git":
                continue
            try:
                st = os.lstat(full)
                if os.path.islink(full):
                    body = os.readlink(full).encode("utf-8", "surrogateescape")
                    kind = "l"
                else:
                    with open(full, "rb") as fh:
                        body = fh.read()
                    kind = "f%04o" % (st.st_mode & 0o7777)
            except OSError as exc:
                body, kind = str(exc).encode("utf-8", "replace"), "e"
            entries.append("%s\0%s\0%s" % (kind, rel, hashlib.sha256(body).hexdigest()))
    entries.sort()
    return hashlib.sha256(("\n".join(entries) + "\n").encode("utf-8", "surrogateescape")).hexdigest()


def named(rows_):
    return [row for row in rows_ if row.get("named_by_slice")]


def not_passed(rows_):
    """The named checks that are failing or were not run: what keeps the card where it is."""
    return [row for row in named(rows_) if row.get("result") != "passed"]


def by_result(rows_, value):
    return [row["name"] for row in named(rows_) if row.get("result") == value]
