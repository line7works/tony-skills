#!/usr/bin/env python3
"""S1's write fence for one Claude Code launch (E11-45 S1, and E11-41 R6's enforcement).

Reads the installed `launch-settings.json`, adds a path-scoped `Write`/`Edit`/`NotebookEdit`
denial for every root this launch must never write, adds the outbound-command denials, and
writes the result beside the launch's capture. The launch passes THAT file with `--settings`,
so the refusal comes from the harness's own permission layer rather than from the mandate's
prose, and the record carries the exact document the session ran under.

usage: write-fence.py SOURCE TARGET [DENY_DIR ...]
Python 3.9, standard library only.
"""
import json
import sys

OUTBOUND = ("Bash(curl:*)", "Bash(wget:*)", "Bash(nc:*)", "Bash(ncat:*)", "Bash(telnet:*)",
            "Bash(ssh:*)", "Bash(scp:*)", "Bash(sftp:*)")
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
# E11-46 R4: the READ side of the same fence. E11-40 makes the rerun conditional on a native
# isolation check, and a boundary that stops writes says nothing about reads. These are the
# read-kind tools Claude Code can scope to a path.
READ_TOOLS = ("Read", "Glob", "Grep", "NotebookRead")


def fence(document, deny_dirs):
    permissions = document.setdefault("permissions", {})
    deny = list(permissions.get("deny") or [])
    for directory in deny_dirs:
        directory = directory.rstrip("/")
        if not directory:
            continue
        # Claude Code reads a rule path with ONE leading slash as relative to the settings
        # file's directory; a filesystem-absolute path is written with TWO. Measured on the
        # 2026-09-18 proof root: `Write(/Users/.../claude-code/**)` did not stop a Write-tool
        # call to that exact path.
        absolute = "/" + directory if directory.startswith("/") else directory
        for tool in WRITE_TOOLS + READ_TOOLS:
            deny.append("%s(%s/**)" % (tool, absolute))
            deny.append("%s(%s)" % (tool, absolute))
    deny.extend(OUTBOUND)
    seen, ordered = set(), []
    for entry in deny:
        if entry not in seen:
            seen.add(entry)
            ordered.append(entry)
    permissions["deny"] = ordered
    return document


def main(argv):
    if len(argv) < 3:
        sys.stderr.write(__doc__)
        return 2
    source, target, deny_dirs = argv[1], argv[2], argv[3:]
    # A setup without an installed settings document still gets the fence: the denials are the
    # point, and an absent source was already tolerated (the launch passed the missing path
    # straight to `claude`). Starting from {} adds the fence and takes nothing away.
    try:
        with open(source, "r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (IOError, OSError, ValueError):
        document = {}
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(fence(document, deny_dirs), handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
