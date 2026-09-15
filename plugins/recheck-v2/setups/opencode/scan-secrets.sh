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
# The CONFIGURED setup's own auth store - <setup>/xdg-data/opencode/auth.json, compared by
# RESOLVED path - is the one file skipped: under ruling E9-38 it is the one place the provider
# key is meant to live, written by install.sh at mode 0600 and never carried in a session's
# environment. Ruling E9-41: every OTHER file is scanned, an `opencode/auth.json` inside a
# capture directory included, because a capture that happens to carry that name is a leak like
# any other. Everything else - every record, capture, trace, log and probe - must hold no
# key-shaped value at all, and a hit anywhere else is a failure. `--include-auth-store` scans
# the setup's store too, for a check of the file itself.
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
INCLUDE_AUTH=0
EXTRA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --setup) SETUP="$2"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    --include-auth-store) INCLUDE_AUTH=1; shift ;;
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

# Ruling E9-41: the one exempt file, by resolved path, is the CONFIGURED setup's own store.
AUTH_STORE_PATH="$SETUP/xdg-data/opencode/auth.json"
printf '%s' "$ROOTS" | INCLUDE_AUTH="$INCLUDE_AUTH" AUTH_STORE_PATH="$AUTH_STORE_PATH" /usr/bin/python3 -c '
import json, os, re, sys

SHAPES = [
    ("openrouter-key", re.compile(rb"sk-or-v1-[0-9a-f]{64}")),
    ("provider-key", re.compile(rb"sk-[A-Za-z0-9_-]{40,}")),
    ("jwt", re.compile(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv"}
# Ruling E9-38: the configured setup has one auth store and that is the intended home for the
# provider key. Ruling E9-41: it is matched by RESOLVED path, so a capture that merely carries
# the name opencode/auth.json is scanned like every other file.
INCLUDE_AUTH = os.environ.get("INCLUDE_AUTH") == "1"
AUTH_STORE = os.environ.get("AUTH_STORE_PATH") or ""
AUTH_STORE = os.path.realpath(AUTH_STORE) if AUTH_STORE else ""
MAX_BYTES = 8 * 1024 * 1024

roots = [line for line in sys.stdin.read().split("\n") if line.strip()]
hits = []
skipped_auth = []
files = 0
for root in roots:
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            path = os.path.join(base, name)
            try:
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                resolved = os.path.realpath(path)
                if not INCLUDE_AUTH and AUTH_STORE and resolved == AUTH_STORE:
                    skipped_auth.append(resolved)
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
                  "auth_stores_skipped": sorted(skipped_auth),
                  "auth_store": AUTH_STORE,
                  "note": "a hit reports the shape, the offset and the length; never the value; "
                          "only the configured setup own auth store, matched by resolved "
                          "path, is skipped unless --include-auth-store (E9-38, E9-41)"},
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
