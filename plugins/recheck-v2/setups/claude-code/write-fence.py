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
# The READ side is GONE, and this is the whole of Astra's gap 1.
#
# E11-46 R4 added `Read`, `Glob`, `Grep` and `NotebookRead` denials for the same roots as the
# write denials. `denied_roots` names the pilot HOMES, and a Claude Code session's own
# installed skill lives inside its home (`<home>/config/plugins/cache/.../recheck-v2/`), so
# the read fence denied the skill its own `references/`, `scripts/`, `adapters/` and schemas
# in all twelve with-skill sessions of the round-2 rerun: the condition under test could not
# read the thing under test.
#
# On the sealed bench the read boundary is the WALL — an OS-level `sandbox-exec` profile that
# refuses every other trial's tree, every other condition's home and the rest of the user
# area, and that cannot be argued with by a tool name. A read denial at the harness's
# permission layer is not needed for it and was never sufficient for it. The write denials
# and the outbound-command denials stay exactly as they were, as a second layer inside the
# wall (E11-45 S1, E11-41 R6).
READ_TOOLS = ()


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
