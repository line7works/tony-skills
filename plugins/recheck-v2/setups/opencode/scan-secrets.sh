#!/bin/sh
# Credential scan for the OpenCode pilot setup (E9 lane Q, Astra finding 1).
#
# Usage:  sh scan-secrets.sh [--setup DIR] [--quiet] [DIR ...]
#   --setup DIR   the isolated pilot setup to scan (default
#                 ~/.local/share/skills-v2-pilot/opencode); its records, config and data
#                 trees are scanned
#   --quiet       print the JSON summary only (no human line on stderr)
#   DIR ...       extra directories to scan (an evidence packet, a probe directory)
#
# Greps for credential-shaped values by SHAPE. No credential value appears in this script, and
# none is ever printed: a hit is reported as the file, the byte offset, the matched length and
# the shape's name, never the text. Bundled dependency trees (node_modules) and git objects are
# skipped: a library's own test fixtures are not this setup's records.
#
# Shapes:
#   openrouter-key    sk-or-v1- followed by 64 hex characters (73 bytes, the shape
#                     $OPENROUTER_API_KEY carries on this machine)
#   provider-key      sk- followed by 40 or more key characters (any other provider's key)
#   jwt               three base64url segments separated by dots (a bearer token)
#
# Prints one JSON object on stdout and nothing else. Exit 0 when nothing was found, 5 when any
# hit was found, 2 on a usage slip, 3 when a named directory does not exist.
# Side effects: none. It reads files and writes nothing.
set -eu

SETUP="${HOME}/.local/share/skills-v2-pilot/opencode"
QUIET=0
EXTRA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --setup) SETUP="$2"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
    --*) echo "scan-secrets.sh: unknown argument $1" >&2; exit 2 ;;
    *) EXTRA="$EXTRA
$1"; shift ;;
  esac
done

ROOTS=""
for d in "$SETUP/records" "$SETUP/xdg-config" "$SETUP/xdg-data" "$SETUP/xdg-state"; do
  [ -d "$d" ] && ROOTS="$ROOTS
$d"
done
for d in $EXTRA; do
  [ -d "$d" ] || { echo "scan-secrets.sh: no directory at $d" >&2; exit 3; }
  ROOTS="$ROOTS
$d"
done

printf '%s' "$ROOTS" | /usr/bin/python3 -c '
import json, os, re, sys

SHAPES = [
    ("openrouter-key", re.compile(rb"sk-or-v1-[0-9a-f]{64}")),
    ("provider-key", re.compile(rb"sk-[A-Za-z0-9_-]{40,}")),
    ("jwt", re.compile(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv"}
MAX_BYTES = 8 * 1024 * 1024

roots = [line for line in sys.stdin.read().split("\n") if line.strip()]
hits = []
files = 0
for root in roots:
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            path = os.path.join(base, name)
            try:
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if os.path.getsize(path) > MAX_BYTES:
                    continue
                with open(path, "rb") as handle:
                    blob = handle.read()
            except (IOError, OSError):
                continue
            files += 1
            for shape, pattern in SHAPES:
                for match in pattern.finditer(blob):
                    # the value is never printed: the shape, where it sits, and how long it is
                    hits.append({"file": path, "shape": shape,
                                 "offset": match.start(),
                                 "length": match.end() - match.start()})
print(json.dumps({"ok": not hits, "roots": roots, "files_scanned": files,
                  "hits": hits, "hit_count": len(hits),
                  "note": "a hit reports the shape, the offset and the length; never the value"},
                 indent=2, sort_keys=True))
sys.exit(0 if not hits else 5)
' > "${TMPDIR:-/tmp}/recheck-v2-scan-$$.json" && RC=0 || RC=$?
cat "${TMPDIR:-/tmp}/recheck-v2-scan-$$.json"
rm -f "${TMPDIR:-/tmp}/recheck-v2-scan-$$.json"
[ "$QUIET" -eq 1 ] || {
  if [ "$RC" -eq 0 ]; then
    echo "scan-secrets.sh: clean" >&2
  else
    echo "scan-secrets.sh: credential-shaped values found; see the hits above" >&2
  fi
}
exit "$RC"
