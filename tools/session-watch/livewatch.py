#!/usr/bin/env python3
"""Follow a Claude Code session transcript (.jsonl) and print one sanitized line per finished
tool call and per turn end, for a Claude Code Monitor.

Usage: livewatch.py <session.jsonl> [--repo PATH] [--subcommands a,b,c] [--flags a,b,c]
                    [--show-skills] [--once]

Never prints message text, addresses, ids, queries or file contents: only the tool, the repo
scripts a Bash command names (relative to the repo), allowlisted flag names, the shell verbs it
uses, seconds, result size and an error flag. A Read/Write/Edit path shows relative to the
repo; anything outside it, or under .claude/, shows only as "outside repo: .<ext> file".

--repo         repo root (default: git root of the current directory, else the directory).
--subcommands  words allowed to print after a script name (default: none print).
--flags        flag names, without the leading --, allowed to print (default: none print).
--show-skills  print a Skill call's name when it is short and plain (default: "skill").
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
FLAG_NAME = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
VERBS = ("git", "tee", "cat", "sed", "grep", "date", "python3 -", "jq", "ls", "find", "osascript")
EXT = re.compile(r"^[A-Za-z0-9]{1,8}$")
PLAIN = re.compile(r"^[a-z0-9:-]{1,40}$")
WORD = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


def default_repo():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except OSError:
        pass
    return os.getcwd()


def ts(s):
    """Aware datetime for an ISO string (naive read as UTC), or None when it is not one."""
    if not isinstance(s, str):
        return None
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def plain(v, pattern=WORD):
    return v if isinstance(v, str) and pattern.match(v) else "?"


def flags(cmd, allowed):
    """--name for each allowed name that is a whole word of the command before any heredoc.
    Allowlist only: no shell parser to get wrong, and an allowed word reveals nothing private."""
    head = cmd.split("<<", 1)[0]
    return sorted("--" + n for n in set(allowed)
                  if re.search(r"(?:^|[ \t\n\r\f\v;|&(])--" + re.escape(n) + r"(?=$|[ \t\n\r\f\v=;|&)])", head))


class Labeler:
    def __init__(self, repo, subcommands=(), show_skills=False, flags=()):
        self.repo = os.path.realpath(repo)
        self.subcommands = set(subcommands)
        self.flags = tuple(flags)
        self.show_skills = show_skills

    def inside(self, path):
        """Repo-relative form of path, or None when it is outside the repo or under .claude/."""
        if not isinstance(path, str) or not path:
            return None
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

    @staticmethod
    def outside(path):
        base = os.path.basename(path) if isinstance(path, str) else ""
        ext = os.path.splitext(base)[1][1:]
        return f"outside repo: .{ext} file" if EXT.match(ext) else "outside repo: file"

    def label(self, name, inp):
        if not isinstance(inp, dict):
            inp = {}
        if name == "Bash":
            c = inp.get("command")
            c = c if isinstance(c, str) else ""
            head = c.split("<<", 1)[0]
            verbs = [w for w in VERBS if re.search(r"(^|[\s|;&(])" + re.escape(w) + r"(\s|$)", c)]
            shown = ["; ".join(self.scripts(head)) or "(no repo script)"] + flags(c, self.flags)
            return f"{' '.join(shown)} [{','.join(verbs)}]"
        if name in ("Read", "Write", "Edit"):
            p = inp.get("file_path")
            return self.inside(p) or self.outside(p)
        if name == "Agent":
            return (f"{plain(inp.get('subagent_type', ''))} model={plain(inp.get('model', 'default'))} "
                    f"effort={plain(inp.get('effort', 'default'))}")
        if name == "Skill":
            s = inp.get("skill")
            return s if self.show_skills and isinstance(s, str) and PLAIN.match(s) else "skill"
        if name == "ToolSearch":
            q = inp.get("query")
            if isinstance(q, str) and q.startswith("select:"):
                return f"select {len([x for x in q[7:].split(',') if x.strip()])} tools"
            return "keyword search"
        return ",".join(sorted(k for k in inp if isinstance(k, str) and WORD.match(k)))[:80]


def result_size(c):
    if isinstance(c, str):
        return len(c)
    if isinstance(c, list):
        return sum(len(x["text"]) for x in c if isinstance(x, dict) and isinstance(x.get("text"), str))
    return 0


def watch(f, labeler, out=sys.stdout, follow=True, skip=0, sleep=time.sleep):
    calls, start, n = {}, None, 0

    def emit(s):
        print(s, file=out, flush=True)

    while True:
        pos = f.tell()
        line = f.readline()
        if not line or not line.endswith("\n"):
            if not follow:
                return  # EOF, or a partial last line: ignore it
            f.seek(pos)  # re-read the whole line once the writer finishes it
            sleep(0.5)
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        t = ts(d.get("timestamp"))
        if t is None:
            continue
        msg = d.get("message")
        msg = msg if isinstance(msg, dict) else {}
        typ = d.get("type")
        content = msg.get("content")
        if typ == "user" and isinstance(content, str) and not d.get("isMeta"):
            if "<command-name>" in content or "<local-command" in content:
                continue
            start = start or t
            emit(f"{(t - start).total_seconds():6.0f}s USER prompt ({len(content)} chars)")
        elif typ == "assistant":
            start = start or t
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and isinstance(b.get("id"), str):
                    name = plain(b.get("name"))
                    calls[b["id"]] = (name, labeler.label(name, b.get("input")), t)
            if msg.get("stop_reason") == "end_turn":
                emit(f"{(t - start).total_seconds():6.0f}s TURN END ({n} tool calls so far)")
        elif typ == "user" and isinstance(content, list):
            start = start or t
            for b in content:
                if not isinstance(b, dict) or b.get("type") != "tool_result":
                    continue
                cid = b.get("tool_use_id")
                if isinstance(cid, str) and cid in calls:
                    name, lab, t0 = calls.pop(cid)
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
    ap.add_argument("--flags", default="")
    ap.add_argument("--show-skills", action="store_true")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args(argv)
    allowed = [x for x in a.flags.split(",") if x]
    bad = [x for x in allowed if not FLAG_NAME.match(x)]
    if bad:
        ap.error(f"--flags names must match [a-z][a-z0-9-]{{0,30}} (no leading --): {len(bad)} do not")
    labeler = Labeler(a.repo or default_repo(), [s for s in a.subcommands.split(",") if s], a.show_skills, allowed)
    skip = int(os.environ.get("SKIP", "0") or 0)
    with open(a.transcript, encoding="utf-8", errors="replace") as f:
        watch(f, labeler, follow=not a.once, skip=skip)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
