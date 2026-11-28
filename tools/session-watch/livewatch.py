#!/usr/bin/env python3
"""Follow a Claude Code session transcript (.jsonl) and print one sanitized line per finished
tool call and per turn end, for a Claude Code Monitor.

Usage: livewatch.py <session.jsonl> [--repo PATH] [--subcommands a,b,c] [--once]

Never prints message text, addresses, ids or file contents: only the tool, the repo scripts a
Bash command names (relative to the repo) with their flags, the shell verbs it uses, seconds,
result size and an error flag. A Read/Write/Edit path shows relative to the repo; anything
outside it, or under .claude/, shows only as "outside repo: .<ext> file".

--repo         repo root (default: git root of the current directory, else the directory).
--subcommands  words allowed to print after a script name (default: none print).
--once         read to the end of the file and exit instead of following it.
SKIP=n         env var: suppress the first n tool-call lines (replayed after a restart).
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

SCRIPT_TOKEN = re.compile(r"[\w./~+-]+\.(?:py|sh|js|ts|rb)(?![\w.])")
FLAG = re.compile(r"(?<!\S)(--[a-z][\w-]*)")
VERBS = ("git", "tee", "cat", "sed", "grep", "date", "python3 -", "jq", "ls", "find", "osascript")
EXT = re.compile(r"^[A-Za-z0-9]{1,8}$")


def default_repo():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except OSError:
        pass
    return os.getcwd()


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


class Labeler:
    def __init__(self, repo, subcommands=()):
        self.repo = os.path.realpath(repo)
        self.subcommands = set(subcommands)

    def inside(self, path):
        """Repo-relative form of path, or None when it is outside the repo or under .claude/."""
        p = os.path.expanduser(path)
        if not os.path.isabs(p):
            p = os.path.join(self.repo, p)
        p = os.path.realpath(p)
        if os.path.commonpath([p, self.repo]) != self.repo or p == self.repo:
            return None
        rel = os.path.relpath(p, self.repo)
        if ".claude" in rel.split(os.sep):
            return None
        return rel

    def scripts(self, cmd):
        out = []
        for m in SCRIPT_TOKEN.finditer(cmd):
            rel = self.inside(m.group(0))
            # Strict: only a file that exists in the repo prints, so a scratch name never does.
            if rel is None or not os.path.isfile(os.path.join(self.repo, rel)):
                continue
            nxt = cmd[m.end():].split(None, 1)
            if nxt and nxt[0] in self.subcommands:
                rel += " " + nxt[0]
            if rel not in out:
                out.append(rel)
        return out

    def outside(self, path):
        base = os.path.basename(path)
        ext = base.rsplit(".", 1)[-1] if "." in base else ""
        return f"outside repo: .{ext} file" if EXT.match(ext) else "outside repo: file"

    def label(self, name, inp):
        if name == "Bash":
            c = inp.get("command", "")
            flags = sorted(set(FLAG.findall(c)))
            verbs = [w for w in VERBS if re.search(r"(^|[\s|;&(])" + re.escape(w) + r"(\s|$)", c)]
            return f"{'; '.join(self.scripts(c)) or '(no repo script)'} {' '.join(flags)} [{','.join(verbs)}]"
        if name in ("Read", "Write", "Edit"):
            p = inp.get("file_path", "")
            rel = self.inside(p) if p else None
            return rel if rel else self.outside(p)
        if name == "Agent":
            return f"{inp.get('subagent_type', '')} model={inp.get('model', 'default')} effort={inp.get('effort', 'default')}"
        if name == "Skill":
            return str(inp.get("skill", ""))[:80]
        if name == "ToolSearch":
            return str(inp.get("query", ""))[:80]
        return ",".join(sorted(inp.keys()))[:80]


def result_size(c):
    if isinstance(c, str):
        return len(c)
    return sum(len(x.get("text", "")) for x in (c or []) if isinstance(x, dict))


def watch(f, labeler, out=sys.stdout, follow=True, skip=0):
    calls, start, n = {}, None, 0

    def emit(s):
        print(s, file=out, flush=True)

    while True:
        line = f.readline()
        if not line:
            if not follow:
                return
            time.sleep(0.5)
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict) or not d.get("timestamp"):
            continue
        t = ts(d["timestamp"])
        msg = d.get("message") or {}
        typ = d.get("type")
        content = msg.get("content")
        if typ == "user" and isinstance(content, str) and not d.get("isMeta"):
            if "<command-name>" in content or "<local-command" in content:
                continue
            start = start or t
            emit(f"{(t - start).total_seconds():6.0f}s USER prompt ({len(content)} chars)")
        elif typ == "assistant":
            start = start or t
            for b in content or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    calls[b.get("id")] = (b.get("name", "?"), labeler.label(b.get("name", ""), b.get("input") or {}), t)
            if msg.get("stop_reason") == "end_turn":
                emit(f"{(t - start).total_seconds():6.0f}s TURN END ({n} tool calls so far)")
        elif typ == "user" and isinstance(content, list):
            start = start or t
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                    name, lab, t0 = calls.pop(b["tool_use_id"])
                    n += 1
                    if n <= skip:
                        continue
                    err = " ERROR" if b.get("is_error") else ""
                    emit(f"{(t - start).total_seconds():6.0f}s #{n} {name} {lab} :: "
                         f"{(t - t0).total_seconds():.1f}s, {result_size(b.get('content'))} chars{err}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("transcript")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--subcommands", default="")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args(argv)
    labeler = Labeler(a.repo or default_repo(), [s for s in a.subcommands.split(",") if s])
    skip = int(os.environ.get("SKIP", "0") or 0)
    with open(a.transcript, encoding="utf-8", errors="replace") as f:
        watch(f, labeler, follow=not a.once, skip=skip)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
