#!/usr/bin/env python3
"""Read-only, after-the-fact summary of tool use in a Claude Code session transcript (.jsonl).

Usage: toolwatch.py <session.jsonl> [--repo PATH] [--full] [--since ISO]

Prints a timeline (user prompts, assistant text, each tool call with its short input, result
size, error flag and wall time between call and result), then totals per tool, the repo
scripts run via Bash, identical repeated calls, and token totals.

It prints command text and output snippets, so its output can hold private data: local use
only. livewatch.py is the one safe to stream.

--repo   repo root for the scripts table (default: git root of the current directory, else
         the directory). A script is any path ending .py/.sh/.js/.ts/.rb inside it.
--full   longer snippets.
--since  skip records before this ISO timestamp.
"""
import argparse
import collections
import datetime
import json
import os
import re
import subprocess

SCRIPT_TOKEN = re.compile(r"[\w./~+-]+\.(?:py|sh|js|ts|rb)(?![\w.])")
SUBCOMMAND = re.compile(r"^[a-z][\w-]*$")


def default_repo():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except OSError:
        pass
    return os.getcwd()


def ts(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def short(v, n=160):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= n else s[:n] + f"…(+{len(s) - n})"


def result_text(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        out = []
        for b in c:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    out.append(b.get("text", ""))
                elif b.get("type") == "image":
                    out.append("[image]")
        return "\n".join(out)
    return str(c)


def repo_scripts(cmd, repo):
    """(repo-relative script, next bare word) for each script path inside repo named in cmd."""
    found = []
    for m in SCRIPT_TOKEN.finditer(cmd):
        p = os.path.expanduser(m.group(0))
        if not os.path.isabs(p):
            p = os.path.join(repo, p)
        p = os.path.realpath(p)
        if os.path.commonpath([p, repo]) != repo or p == repo:
            continue
        nxt = cmd[m.end():].split(None, 1)
        sub = nxt[0] if nxt and SUBCOMMAND.match(nxt[0]) else ""
        found.append((os.path.relpath(p, repo), sub))
    return found


def summarize(path, repo, full=False, since=None, out=None):
    def emit(*a):
        print(*a, file=out)

    repo = os.path.realpath(repo)
    calls, order, events = {}, [], []
    usage = collections.Counter()
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            t = ts(d.get("timestamp"))
            if since and t and t < since:
                continue
            typ = d.get("type")
            msg = d.get("message") or {}
            if typ == "assistant":
                u = msg.get("usage") or {}
                for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                    usage[k] += u.get(k, 0) or 0
                for b in msg.get("content") or []:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use":
                        calls[b["id"]] = {"name": b.get("name", "?"), "input": b.get("input") or {}, "t": t}
                        order.append(b["id"])
                        events.append(("call", t, b["id"]))
                    elif b.get("type") == "text" and b.get("text", "").strip():
                        events.append(("say", t, b["text"]))
            elif typ == "user":
                c = msg.get("content")
                if isinstance(c, str):
                    if not d.get("isMeta"):
                        events.append(("user", t, c))
                elif isinstance(c, list):
                    for b in c:
                        if not isinstance(b, dict):
                            continue
                        if b.get("type") == "tool_result":
                            cid = b.get("tool_use_id")
                            if cid in calls:
                                calls[cid].update(rt=t, err=bool(b.get("is_error")), out=result_text(b.get("content")))
                        elif b.get("type") == "text" and not d.get("isMeta"):
                            events.append(("user", t, b.get("text", "")))
    start = next((t for _, t, _ in events if t), None)
    for kind, t, x in events:
        rel = f"{(t - start).total_seconds() / 60:6.1f}m" if t and start else "     ?"
        if kind == "user":
            emit(f"{rel} USER  {short(x, 4000 if full else 300)}")
        elif kind == "say":
            emit(f"{rel} SAY   {short(x, 4000 if full else 200)}")
        else:
            c = calls[x]
            inp = c["input"]
            if c["name"] == "Bash":
                desc = inp.get("command", "")
            elif c["name"] in ("Read", "Write", "Edit"):
                desc = inp.get("file_path", "")
            elif c["name"] == "Agent":
                desc = f"[{inp.get('subagent_type', '')}/{inp.get('model', '')}] {inp.get('description', '')}"
            else:
                desc = inp
            dur = (c["rt"] - c["t"]).total_seconds() if c.get("rt") and c["t"] else None
            flag = "ERR " if c.get("err") else ""
            res = c.get("out", "")
            emit(f"{rel} {flag}{c['name']:<10} {short(desc, 3000 if full else 220)}")
            emit(f"         -> {len(res)} chars, {dur if dur is None else round(dur, 1)}s :: {short(res, 2000 if full else 160)}")

    emit("\n== totals")
    byname = collections.Counter(calls[i]["name"] for i in order)
    errs = collections.Counter(calls[i]["name"] for i in order if calls[i].get("err"))
    outsz = collections.Counter()
    for i in order:
        outsz[calls[i]["name"]] += len(calls[i].get("out", ""))
    for n, k in byname.most_common():
        emit(f"  {n:<14} calls {k:4}  errors {errs[n]:3}  result chars {outsz[n]:8}")

    emit("\n== repo scripts run via Bash")
    rt = collections.Counter()
    for i in order:
        if calls[i]["name"] == "Bash":
            for key in repo_scripts(calls[i]["input"].get("command", ""), repo):
                rt[key] += 1
    for (p, sub), k in rt.most_common():
        emit(f"  {k:3}  {p} {sub}".rstrip())

    sig = collections.Counter(json.dumps([calls[i]["name"], calls[i]["input"]], sort_keys=True) for i in order)
    reps = [(s, k) for s, k in sig.items() if k > 1]
    if reps:
        emit("\n== identical calls repeated")
        for s, k in sorted(reps, key=lambda x: -x[1]):
            emit(f"  x{k}  {short(s, 200)}")
    emit("\n== tokens", dict(usage))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("transcript")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--since", default=None)
    a = ap.parse_args(argv)
    since = ts(a.since)
    if since and since.tzinfo is None:
        since = since.replace(tzinfo=datetime.timezone.utc)
    summarize(a.transcript, a.repo or default_repo(), full=a.full, since=since)


if __name__ == "__main__":
    main()
