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
rerun — this core will not reconstruct a shell's meaning — and the row keeps the recorded result
with `rerun_refused` saying why. `sh checks/unit.sh` runs; `a | b` does not.

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
    except subprocess.TimeoutExpired:
        return None, "", "the command did not finish within %d seconds" % timeout
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), None


def _recorded_row(named, reported):
    return {
        "name": named["name"],
        "command": named.get("command"),
        "result": reported.get("result") if reported else "not_run",
        "exit_code": reported.get("exit_code") if reported else None,
        "output": reported.get("output") if reported else "",
        "source": "recorded",
        "named_by_slice": True,
        "rerun_refused": None,
        "recorded_result": None,
    }


def rows(contract_checks, answer_checks, workspace=None, rerun=False):
    """One row per check, the slice's in document order first, then any the answer adds.

    `contract_checks` is `[{"name", "command"}]` from the build doc; `answer_checks` is the
    recorded answer's `checks` list.
    """
    reported = {}
    for row in answer_checks or []:
        reported.setdefault(row.get("name"), row)

    out = []
    for named in contract_checks or []:
        row = _recorded_row(named, reported.get(named["name"]))
        if rerun:
            code, output, why = run_command(workspace, named.get("command"))
            if why is None:
                observed = "passed" if code == 0 else "failing"
                # A rerun that disagrees with what the answer recorded keeps both: the row
                # reports what this core observed, and `recorded_result` says what the answer
                # claimed, so the disagreement is visible rather than quietly overwritten.
                if observed != row["result"]:
                    row["recorded_result"] = row["result"]
                row["result"] = observed
                row["exit_code"] = code
                row["output"] = output
                row["source"] = "rerun"
            else:
                row["rerun_refused"] = why
        out.append(row)

    named_names = set(row["name"] for row in out)
    for row in answer_checks or []:
        if row.get("name") in named_names:
            continue
        out.append({
            "name": row.get("name"),
            "command": row.get("command"),
            "result": row.get("result") or "not_run",
            "exit_code": row.get("exit_code"),
            "output": row.get("output") or "",
            "source": "recorded",
            "named_by_slice": False,
            "rerun_refused": None,
            "recorded_result": None,
        })
    return out


def named(rows_):
    return [row for row in rows_ if row.get("named_by_slice")]


def not_passed(rows_):
    """The named checks that are failing or were not run: what keeps the card where it is."""
    return [row for row in named(rows_) if row.get("result") != "passed"]


def by_result(rows_, value):
    return [row["name"] for row in named(rows_) if row.get("result") == value]
