#!/bin/sh
# The v1-station trace check of ruling E9-8 over one live session's records.
#
# Usage: trace-check.sh <out-dir of launch.sh>
# Greps the harness's own record of the session (the stream-json trace and the
# transcript) for the v1 station names and prints one JSON object naming every
# hit with its record type, its class, and a 120-character window. `/readers` is
# not a v1 station on this lane: recheck-v2 summons it as its verifier
# capability, so it is counted separately and never reported as a hit.
#
# Ruling E9-30: the gate is invocation. Every hit is listed with its class —
# `invocation` (a Skill or slash-command call naming a v1 station), `description
# exclusion`, `shared core's own sentence about v1`, `fixture text`, `path
# segment`, or `other supplied text` — and only an `invocation` fails the gate.
# `gate` in the output says pass or fail, and `invocation_hits` lists the ones
# that would fail it.
# Exit 0 always when the files are readable (a hit is a finding to report, not
# an error), 2 usage, 3 the trace is missing.

set -eu
[ $# -eq 1 ] || { echo "usage: trace-check.sh <out-dir>" >&2; exit 2; }
OUT_DIR="$1"
[ -f "$OUT_DIR/trace.jsonl" ] || { echo "trace-check.sh: no trace.jsonl in $OUT_DIR" >&2; exit 3; }

python3 - "$OUT_DIR" <<'PY'
import json
import os
import re
import sys

out_dir = sys.argv[1]
STATIONS = ["/recheck", "/signoff", "/inspect", "/vertical", "/ship", "/build",
            "/blueprint", "/precon", "/architect", "/handoff", "/wargame"]
hits = []
counts = {name: 0 for name in STATIONS}
readers_mentions = 0
files = []
for name in ("trace.jsonl", "transcript.jsonl"):
    path = os.path.join(out_dir, name)
    if os.path.isfile(path):
        files.append(path)

def invocations(record, stations):
    """The station names this record actually CALLS (ruling E9-30's gate).

    A `Skill` or `SlashCommand` tool call whose argument names a station, or a
    harness slash-command record (`<command-name>/signoff</command-name>`).
    Everything else is text: supplied, quoted, planted, or a path.
    """
    called = set()
    message = record.get("message") or {}
    content = message.get("content")
    blocks = content if isinstance(content, list) else []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") in ("Skill", "SlashCommand"):
            payload = json.dumps(block.get("input") or {})
            for station in stations:
                bare = station.lstrip("/")
                if re.search(r'"(skill|command|name)"\s*:\s*"/?%s\b' % re.escape(bare), payload):
                    called.add(station)
        if block.get("type") == "text":
            for match in re.finditer(r"<command-name>\s*(/[A-Za-z0-9_-]+)", block.get("text") or ""):
                if match.group(1) in stations:
                    called.add(match.group(1))
    if isinstance(content, str):
        for match in re.finditer(r"<command-name>\s*(/[A-Za-z0-9_-]+)", content):
            if match.group(1) in stations:
                called.add(match.group(1))
    return called


def classify(window, station, called):
    if station in called:
        return "invocation"
    if "belongs to the v1 station" in window:
        return "description exclusion"
    if "imports nothing from v1" in window or "v1 " in window or " v1" in window:
        return "shared core's own sentence about v1"
    if "REVIEW-INSTRUCTIONS" in window or "take its verdict" in window or "grant" in window:
        return "fixture text"
    if re.search(r"[A-Za-z0-9_.\-]" + re.escape(station), window):
        return "path segment"
    return "other supplied text"


for path in files:
    with open(path, "r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                kind = record.get("type")
            except ValueError:
                record, kind = {}, "<unparsed>"
            readers_mentions += len(re.findall(r"/readers\b", line))
            called = invocations(record, STATIONS)
            for station in STATIONS:
                # The bare slash command only: not `scripts/recheck.py`, not
                # `plugins/signoff/...`, not `2026-09-19-signoff-widget-a.md`.
                pattern = r"(?<![A-Za-z0-9_.\-])" + re.escape(station) + r"(?![A-Za-z0-9_.\-])"
                for match in re.finditer(pattern, line):
                    counts[station] += 1
                    start = max(0, match.start() - 50)
                    window = line[start:match.end() + 70]
                    hits.append({
                        "file": os.path.basename(path),
                        "record": number,
                        "record_type": kind,
                        "station": station,
                        "class": classify(window, station, called),
                        "window": window,
                    })

by_class = {}
for hit in hits:
    by_class[hit["class"]] = by_class.get(hit["class"], 0) + 1
invocation_hits = [hit for hit in hits if hit["class"] == "invocation"]

document = {
    "out_dir": out_dir,
    "files_checked": [os.path.basename(p) for p in files],
    "stations": STATIONS,
    "hit_counts": {k: v for k, v in counts.items() if v},
    "total_hits": len(hits),
    "by_class": by_class,
    "gate": "fail (a v1 station was invoked)" if invocation_hits else
            "pass (no hit is an invocation; ruling E9-30)",
    "invocation_hits": invocation_hits,
    "readers_mentions": readers_mentions,
    "hits": hits[:40],
    "hits_truncated": len(hits) > 40,
}
sys.stdout.write(json.dumps(document, indent=2) + "\n")
PY
