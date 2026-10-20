#!/bin/sh
# Install sun-v2 alone into an isolated Codex home (E16 slice 5, part J4).
#
# Adapted from plugins/ship-v2/setups/codex/install.sh, its home guard kept byte for byte; the plugin list is
# the core alone, this script's own plugin folder (sun-v2 summons no other plugin).
#
# Usage: install.sh --home DIR    (or SUN_V2_CODEX_HOME=DIR install.sh)
#
# DIR becomes the CODEX_HOME of this setup; it is REQUIRED (no default) and is refused, before anything is
# created, under ~/.claude, ~/.codex or ~/.local/share/skills-v2-*, as given or resolved, ~ read as $HOME.
# Written inside it: marketplace/, this setup's own marketplace, whose one entry is a symlink to the worktree's
# plugin folder. Unlike ship-v2's installer, nothing is read from ~/.codex: no config line and no sign-in is
# copied (an install and its verification need neither; a session would), and there is no --credential.
#
# Writes DIR/install.json and prints it. Exit 0 every command succeeded, 2 usage or a refused home, 3 codex
# is missing, 1 a marketplace or install command failed (the record still lands).
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
PLUGINS_DIR=$(CDPATH= cd -- "$PLUGIN_ROOT/.." && pwd -P)
REPO_ROOT=$(CDPATH= cd -- "$PLUGINS_DIR/.." && pwd -P)
CORE=$(basename -- "$PLUGIN_ROOT")
VAR=$(printf '%s' "$CORE" | tr 'a-z-' 'A-Z_')_CODEX_HOME
SETUP_HOME=$(eval "printf '%s' \"\${$VAR:-}\"")
export PYTHONDONTWRITEBYTECODE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --home) [ $# -ge 2 ] || { echo "install.sh: --home takes a directory" >&2; exit 2; }
            SETUP_HOME="$2"; shift 2 ;;
    -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "install.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$SETUP_HOME" ] || { echo "install.sh: name the isolated home: --home DIR or $VAR" >&2; exit 2; }
command -v codex >/dev/null 2>&1 || { echo "install.sh: codex is not on PATH" >&2; exit 3; }
# The home guard, before anything is created (E14 slice 3c fix 3): the home, as given and resolved,
# may not be or sit under ~/.claude, ~/.codex or ~/.local/share/skills-v2-*, whichever harness this is.
# TMPDIR, TEMP and TMP are held to the same rule (E14 punch list, check 6 C3C6-1; review F1).
SETUP_HOME=$(env -u TMPDIR -u TEMP -u TMP python3 - "$SETUP_HOME" "$HOME" "install.sh" "${TMPDIR-}" "${TEMP-}" "${TMP-}" <<'GUARD'
import os, sys
target, home, name = sys.argv[1:4]


def refuse(why):
    sys.stderr.write("%s: %s; nothing created\n" % (name, why))
    sys.exit(2)


def forms(path):
    return (os.path.abspath(path), os.path.realpath(path))


def rest(path, base):
    """The part of `path` below `base` ("" when they are the same), or None; compared casefolded."""
    p, b = path.casefold(), base.casefold().rstrip(os.sep)
    return "" if p == b else (p[len(b) + 1:] if p.startswith(b + os.sep) else None)


def same_below(path, base):
    """The part of `path` below `base` by the file system's own identity ("" when they are the same
    folder), or None. macOS names one folder by more than one path that neither abspath nor realpath
    rewrites (/System/Volumes/Data/..., /.nofollow/..., /.resolve/N/...), so the nearest existing
    ancestor of `path` is compared with `base` by device and inode."""
    try:
        want = os.stat(base)
    except OSError:
        return None
    probe, tail = os.path.realpath(path), []
    while True:
        try:
            if os.path.samestat(os.stat(probe), want):
                return os.sep.join(reversed(tail)).casefold()
        except OSError:
            pass
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        tail.append(os.path.basename(probe))
        probe = parent


def below_home(path, base):
    """`same_below`, and for a `base` that does not exist yet the same answer read through HOME: `path` is
    compared with HOME by device and inode and the part below HOME is read against `base`'s place below it."""
    got = same_below(path, base)
    if got is not None:
        return got
    below = same_below(path, home)
    if below is None:
        return None
    rel = os.path.relpath(base, home).casefold()
    return "" if below == rel else (below[len(rel) + 1:] if below.startswith(rel + os.sep) else None)


if not os.path.isabs(home):
    refuse("HOME is not an absolute path")
share = os.path.join(home, ".local", "share")
homes = (os.path.join(home, ".claude"), os.path.join(home, ".codex"),
         os.path.join(share, "skills-v2-pilot"), os.path.join(share, "skills-v2-locked"))
temps = [value for value in sys.argv[4:7] if value] or ["/tmp"]
for given in [target] + temps:
    for path in forms(given):
        for forbidden in homes:
            if (any(rest(path, base) is not None for base in forms(forbidden))
                    or below_home(path, forbidden) is not None):
                refuse("%s is under %s, which no setup may touch" % (given, forbidden))
        for below in [rest(path, base) for base in forms(share)] + [below_home(path, share)]:
            if below and below.split(os.sep)[0].startswith("skills-v2-"):
                refuse("%s is under %s, which no setup may touch"
                       % (given, os.path.join(share, below.split(os.sep)[0])))
print(os.path.realpath(target))
GUARD
) || exit $?
mkdir -p "$SETUP_HOME"
SETUP_HOME=$(CDPATH= cd -- "$SETUP_HOME" && pwd -P)
export CODEX_HOME="$SETUP_HOME"
PLUGIN="$CORE"
MARKET_NAME="$CORE-setup"
SPEC="$PLUGIN@$MARKET_NAME"

MARKET="$SETUP_HOME/marketplace"
mkdir -p "$MARKET/.claude-plugin"
ln -sfn "$PLUGINS_DIR/$PLUGIN" "$MARKET/$PLUGIN"
cat > "$MARKET/.claude-plugin/marketplace.json" <<JSON
{
  "name": "$MARKET_NAME",
  "owner": { "name": "skills v2 setup" },
  "plugins": [ { "name": "$PLUGIN", "source": "./$PLUGIN" } ]
}
JSON
# A rerun installs fresh: clear this marketplace's cache so the copy is this checkout's.
rm -rf "$SETUP_HOME/plugins/cache/$MARKET_NAME"

WORK=$(mktemp -d "${TMPDIR:-/tmp}/$CORE-codex-install.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM
: > "$WORK/failures"
VERSION=$(codex --version 2>/dev/null | awk '{print $NF}')
st=0; codex plugin marketplace add "$MARKET" --json > "$WORK/m.out" 2>&1 || st=$?
cat "$WORK/m.out" >&2
if [ "$st" -ne 0 ] && ! grep -qi "already" "$WORK/m.out"; then echo "marketplace add: exit $st" >> "$WORK/failures"; fi
st=0; codex plugin add "$SPEC" --json > "$WORK/out" 2>&1 || st=$?
line=$(head -1 "$WORK/out"); echo "$SPEC: exit $st: $line" >&2
[ "$st" -eq 0 ] || echo "plugin add $SPEC: exit $st" >> "$WORK/failures"

python3 - "$SETUP_HOME" "$CORE" "$VERSION" "$REPO_ROOT" "$MARKET_NAME" "$SPEC" "$st" "$line" "$WORK/failures" <<'PY'
import json, os, subprocess, sys
home, core, version, repo, market, spec, status, first, failures = sys.argv[1:10]
failed = [l for l in open(failures).read().splitlines() if l.strip()]
cache = os.path.join(home, "plugins", "cache", market)
installed = sorted(os.path.join(cache, p, v) for p in (os.listdir(cache) if os.path.isdir(cache) else [])
                   for v in os.listdir(os.path.join(cache, p)))
commit = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], stdout=subprocess.PIPE).stdout.decode().strip()
doc = {"core": core, "harness": "codex", "codex_home": home, "marketplace": market,
       "codex_version": version, "repo_root": repo, "commit": commit,
       "installs": [{"plugin": spec, "exit": int(status), "first_line": first}],
       "installed_plugin_dirs": installed, "credential": "not written (this installer copies none)",
       "ok": not failed, "failed_commands": failed}
with open(os.path.join(home, "install.json"), "w") as handle:
    json.dump(doc, handle, indent=2); handle.write("\n")
print(json.dumps(doc, indent=2))
sys.exit(1 if failed else 0)
PY
