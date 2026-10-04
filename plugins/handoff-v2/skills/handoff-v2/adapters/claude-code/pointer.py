#!/usr/bin/env python3
"""pointer.py: the Claude Code adapter's own step, the auto-memory pointer (the E15 lane contract A2 Q3, E15-12).

    python3 pointer.py --run-dir D --memory-dir M

v1's memory pointer, written from the text the core's `write` left in the run directory (`D/pointer.json`): one
auto-memory file per feature, `M/handoff-<feature>.md`, overwritten each run (never a second dated file), and its
index line in `M/MEMORY.md`, added or replacing every earlier line that links the same file (superseded, never
seconded), worded as the build loop's kickoff pointer for the named build doc. The memory folder is the one the
executor GIVES: this script has no default, never derives one, and reads no environment for it. The core writes
nothing outside the workspace; this is the adapter's step, and on Codex there is none.

Refused, nothing written: no `--memory-dir` (exit 2), a memory folder that is not an existing absolute directory
(exit 2), a run directory with no `pointer.json` (exit 2), a pointer that is not this adapter's (a Codex run or a
report-only run: `for_adapter` false, exit 5), and a link, or anything that is not a regular file, at either target
(exit 5). On success it writes `D/pointer-receipt.json` (every write with its hash before and after) and prints the
same document; `handoff.py report` checks it and records the two writes. Exit 0.
Standard library only, Python 3.9; no network, no subprocess.
"""
import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile

sys.dont_write_bytecode = True


class Refused(RuntimeError):
    pass


def _sha(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except FileNotFoundError:
        return None


def _regular_or_absent(path):
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise Refused("%s is a link or not a regular file: the pointer is never written through one" % path)


def _write(path, data):
    folder = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix=".pointer-", dir=folder)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def index_text(current, file_name, line):
    """The index with every line linking `file_name` replaced by `line`, in the first one's place, or `line` added at
    the end when none links it."""
    link = "](%s)" % file_name
    rows = current.splitlines(True) if current else []
    out, placed = [], False
    for row in rows:
        if link in row:
            if not placed:
                out.append(line + "\n")
                placed = True
            continue
        out.append(row)
    if not placed:
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append(line + "\n")
    return "".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pointer.py", description="Write v1's auto-memory pointer for a handoff-v2 run, under the memory folder "
                                       "you give (the Claude Code adapter's step).",
        epilog="example:\n  python3 pointer.py --run-dir /path/to/run --memory-dir /path/to/project/memory\n\n"
               "side effects: writes <memory-dir>/handoff-<feature>.md and <memory-dir>/MEMORY.md, and\n"
               "<run-dir>/pointer-receipt.json; nothing else.\n"
               "exit: 0 written, 2 usage (no memory folder, no pointer.json), 5 refused (nothing written).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", required=True, metavar="D", help="the handoff-v2 run directory")
    parser.add_argument("--memory-dir", required=True, metavar="M",
                        help="the auto-memory folder of this project, as the harness names it (no default)")
    args = parser.parse_args(argv)
    memory = args.memory_dir
    if not os.path.isabs(memory) or not os.path.isdir(memory) or os.path.islink(memory):
        sys.stderr.write("pointer.py: --memory-dir is an existing absolute directory, not a link: %s\n" % memory)
        return 2
    source = os.path.join(args.run_dir, "pointer.json")
    if not os.path.isfile(source) or os.path.islink(source):
        sys.stderr.write("pointer.py: no pointer.json in the run directory %s: run handoff.py write first\n"
                         % args.run_dir)
        return 2
    with open(source, encoding="utf-8") as fh:
        pointer = json.load(fh)
    try:
        if not pointer.get("for_adapter"):
            raise Refused("this run's pointer is not the Claude Code adapter's: %s"
                          % (pointer.get("note") or "for_adapter is false"))
        name = pointer["file_name"]
        if os.path.basename(name) != name or not name.startswith("handoff-") or not name.endswith(".md"):
            raise Refused("the pointer's file name %r is not one handoff-<feature>.md in the memory folder" % name)
        target = os.path.join(memory, name)
        index = os.path.join(memory, "MEMORY.md")
        for path in (target, index):
            _regular_or_absent(path)
        before = {target: _sha(target), index: _sha(index)}
        current = ""
        if before[index] is not None:
            with open(index, encoding="utf-8", newline="") as fh:
                current = fh.read()
        _write(target, pointer["text"].encode("utf-8"))
        _write(index, index_text(current, name, pointer["index_line"]).encode("utf-8"))
    except Refused as exc:
        sys.stderr.write("pointer.py: refused, nothing written: %s\n" % exc)
        return 5
    receipt = {"receipt_version": 1, "run_id": pointer.get("run_id"), "feature": pointer.get("feature"),
               "writes": [{"path": path, "kind": "memory_pointer", "sha256_before": before[path],
                           "sha256_after": _sha(path)} for path in (target, index)]}
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    with open(os.path.join(args.run_dir, "pointer-receipt.json"), "w", encoding="utf-8") as fh:
        fh.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
