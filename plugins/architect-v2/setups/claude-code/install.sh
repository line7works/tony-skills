#!/bin/sh
# Install this core into an isolated Claude Code setup (E13 slice 3, brief 3.3).
#
# Adapted from plugins/recheck-v2/setups/claude-code/install.sh (E9 lane C). Byte-identical in
# the four front cores (E14); build-v2's and signoff-v2's (E13) differ in the plugin list, a case here, and this header; their home guard is this one (E14 punch list): the core is this script's own plugin folder, never configured.
#
# Usage: install.sh --home DIR      (or <CORE>_CLAUDE_HOME=DIR install.sh, e.g. BUILD_V2_CLAUDE_HOME)
#
# The home is REQUIRED (no default, so two setups never share one) and is refused, before anything is
# created, under ~/.claude, ~/.codex or ~/.local/share/skills-v2-*, as given or resolved. Inside it: config/
# (CLAUDE_CONFIG_DIR) and marketplace/, this setup's own marketplace, whose entries are symlinks
# to the worktree's plugin folders: the core and the plugins the case below names (the repo's
# marketplace.json is the control room's and does not list the v2 cores). Every plugin is
# uninstalled, its cache folder cleared, and installed again, so the cache is this checkout.
# Writes <home>/install.json and prints it. Exit 0 every command succeeded, 2 usage, 3 claude is
# missing, 1 a marketplace or install command failed or reported an outcome other than ok (the
# record still lands, with ok false and the failing commands named). No sign-in is read or copied:
# Claude Code keeps its sign-in in the macOS Keychain and an isolated config dir has none.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
PLUGINS_DIR=$(CDPATH= cd -- "$PLUGIN_ROOT/.." && pwd -P)
REPO_ROOT=$(CDPATH= cd -- "$PLUGINS_DIR/.." && pwd -P)
CORE=$(basename -- "$PLUGIN_ROOT")
VAR=$(printf '%s' "$CORE" | tr 'a-z-' 'A-Z_')_CLAUDE_HOME
SETUP_HOME=$(eval "printf '%s' \"\${$VAR:-}\"")
export PYTHONDONTWRITEBYTECODE=1

while [ $# -gt 0 ]; do
  case "$1" in
    --home) [ $# -ge 2 ] || { echo "install.sh: --home takes a directory" >&2; exit 2; }
            SETUP_HOME="$2"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "install.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$SETUP_HOME" ] || { echo "install.sh: name the isolated home: --home DIR or $VAR" >&2; exit 2; }
command -v claude >/dev/null 2>&1 || { echo "install.sh: claude is not on PATH" >&2; exit 3; }
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

case "$CORE" in
  signoff-v2) PLUGINS="$CORE records readers" ;;
  inspect-v2) PLUGINS="$CORE records readers blueprint-v2" ;;
  precon-v2|architect-v2) PLUGINS="$CORE readers" ;;
  blueprint-v2) PLUGINS="$CORE" ;;
  *) PLUGINS="$CORE records" ;;
esac
CONFIG_DIR="$SETUP_HOME/config"
MARKET="$SETUP_HOME/marketplace"
MARKET_NAME="$CORE-setup"
export CLAUDE_CONFIG_DIR="$CONFIG_DIR"
mkdir -p "$CONFIG_DIR" "$MARKET/.claude-plugin"

# A marketplace entry's source must resolve inside the marketplace root (the pilot measured an
# absolute path and a `..` path both rejected), so the entries are symlinks to the worktree.
ENTRIES=""
for plugin in $PLUGINS; do
  ln -sfn "$PLUGINS_DIR/$plugin" "$MARKET/$plugin"
  ENTRIES="$ENTRIES{ \"name\": \"$plugin\", \"source\": \"./$plugin\" },"
done
cat > "$MARKET/.claude-plugin/marketplace.json" <<JSON
{
  "name": "$MARKET_NAME",
  "owner": { "name": "skills v2 setup" },
  "description": "Isolated marketplace of the $CORE Claude Code setup: symlinks to the worktree's plugin folders.",
  "plugins": [ ${ENTRIES%,} ]
}
JSON

WORK=$(mktemp -d "${TMPDIR:-/tmp}/$CORE-install.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM
: > "$WORK/failures"
: > "$WORK/results"
CLAUDE_VERSION=$(claude --version 2>/dev/null | awk '{print $1}')

status=0
claude plugin marketplace add "$MARKET" >"$WORK/m.out" 2>&1 || status=$?
if [ "$status" -ne 0 ]; then
  # A rerun finds the marketplace already added; an update is then the same step.
  ustatus=0
  claude plugin marketplace update "$MARKET_NAME" >>"$WORK/m.out" 2>&1 || ustatus=$?
  [ "$ustatus" -eq 0 ] || echo "marketplace add/update $MARKET_NAME: exit $status/$ustatus" >> "$WORK/failures"
fi
cat "$WORK/m.out" >&2

for plugin in $PLUGINS; do
  claude plugin uninstall "$plugin@$MARKET_NAME" >/dev/null 2>&1 || true
  # `uninstall` leaves the cache folder on disk (the pilot's E10-24), so it is cleared here.
  find "$CONFIG_DIR/plugins/cache/$MARKET_NAME" -mindepth 1 -maxdepth 1 -type d -name "$plugin" -print0 2>/dev/null \
    | xargs -0 python3 -c 'import shutil,sys; [shutil.rmtree(p) for p in sys.argv[1:]]' || true
done
for plugin in $PLUGINS; do
  spec="$plugin@$MARKET_NAME"
  st=0
  claude plugin install "$spec" --json -y > "$WORK/out" 2>&1 || st=$?
  line=$(head -1 "$WORK/out")
  echo "$spec: exit $st: $line" >&2
  if [ "$st" -ne 0 ]; then
    echo "install $spec: exit $st" >> "$WORK/failures"
  elif ! printf '%s' "$line" | grep -q '"outcome":"ok"'; then
    echo "install $spec: outcome is not ok" >> "$WORK/failures"
  fi
  printf '%s\t%s\t%s\n' "$spec" "$st" "$line" >> "$WORK/results"
done

python3 - "$SETUP_HOME" "$CORE" "$CLAUDE_VERSION" "$REPO_ROOT" "$MARKET_NAME" "$WORK/results" "$WORK/failures" <<'PY'
import json, os, subprocess, sys
home, core, version, repo, market, results, failures = sys.argv[1:8]
rows = []
for line in open(results, encoding="utf-8").read().splitlines():
    spec, status, first = (line.split("\t") + ["", ""])[:3]
    rows.append({"plugin": spec, "exit": int(status), "first_line": first})
failed = [l for l in open(failures, encoding="utf-8").read().splitlines() if l.strip()]
cache = os.path.join(home, "config", "plugins", "cache", market)
installed = sorted(os.path.join(cache, p, v) for p in (os.listdir(cache) if os.path.isdir(cache) else [])
                   for v in os.listdir(os.path.join(cache, p)))
def git(*args):
    proc = subprocess.run(["git", "-C", repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stdout.decode().strip() or None
doc = {"core": core, "harness": "claude-code", "setup_home": home,
       "config_dir": os.path.join(home, "config"), "marketplace": market,
       "claude_version": version, "repo_root": repo, "commit": git("rev-parse", "HEAD"),
       "installs": rows, "installed_plugin_dirs": installed, "ok": not failed,
       "failed_commands": failed}
with open(os.path.join(home, "install.json"), "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
print(json.dumps(doc, indent=2))
if failed:
    sys.stderr.write("install.sh: the setup is not installed: %s\n" % "; ".join(failed))
    sys.exit(1)
PY
