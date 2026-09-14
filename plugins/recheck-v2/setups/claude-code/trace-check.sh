#!/bin/sh
# The v1-station trace check of ruling E9-8 over one live session's records.
#
# Usage: trace-check.sh <out-dir of launch.sh>
# Greps the harness's own record of the session (the stream-json trace and the
# transcript) for the v1 station names and prints one JSON object naming every
# hit with its record type and a 120-character window. `/readers` is not a v1
# station on this lane: recheck-v2 summons it as its verifier capability, so it
# is counted separately and never reported as a hit.
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

for path in files:
    with open(path, "r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                kind = json.loads(line).get("type")
            except ValueError:
                kind = "<unparsed>"
            readers_mentions += len(re.findall(r"/readers\b", line))
            for station in STATIONS:
                # The bare slash command only: not `scripts/recheck.py`, not
                # `plugins/signoff/...`, not `2026-09-19-signoff-widget-a.md`.
                pattern = r"(?<![A-Za-z0-9_.\-])" + re.escape(station) + r"(?![A-Za-z0-9_.\-])"
                for match in re.finditer(pattern, line):
                    counts[station] += 1
                    start = max(0, match.start() - 50)
                    hits.append({
                        "file": os.path.basename(path),
                        "record": number,
                        "record_type": kind,
                        "station": station,
                        "window": line[start:match.end() + 70],
                    })

document = {
    "out_dir": out_dir,
    "files_checked": [os.path.basename(p) for p in files],
    "stations": STATIONS,
    "hit_counts": {k: v for k, v in counts.items() if v},
    "total_hits": len(hits),
    "readers_mentions": readers_mentions,
    "hits": hits[:40],
    "hits_truncated": len(hits) > 40,
}
sys.stdout.write(json.dumps(document, indent=2) + "\n")
PY
