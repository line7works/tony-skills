#!/bin/sh
# Install this core into an isolated Codex home (E13 slice 3, brief 3.3).
#
# Adapted from plugins/recheck-v2/setups/codex/install.sh (E9 lane R, E10-58). Byte-identical in
# build-v2 and signoff-v2: the core is this script's own plugin folder.
#
# Usage: install.sh --home DIR [--credential]    (or <CORE>_CODEX_HOME=DIR, e.g. BUILD_V2_CODEX_HOME)
#
# DIR becomes the CODEX_HOME of this setup; it is REQUIRED (no default) and may never be the
# live ~/.codex or anything under the pilot's ~/.local/share/skills-v2-pilot. Written inside it,
# the pilot's way: config.toml with exactly the model, model_reasoning_effort and sandbox_mode
# lines of ~/.codex/config.toml plus approval_policy never, web_search disabled and
# shell_snapshot off (E10-30), a child/ home for the tool shells ([shell_environment_policy.set]
# CODEX_HOME and UV_CACHE_DIR, E9-25), and marketplace/, this setup's own marketplace whose
# entries are symlinks to the worktree's plugin folders: the core and records (signoff-v2's Codex
# reviewer is a fresh codex exec, so readers is not installed here).
#
# --credential copies ~/.codex/auth.json byte for byte into DIR at mode 600 and links
# child/auth.json to it, the pilot's own step; it is never read, printed or logged. Without the
# flag no credential is written: installs and verification need none, a session does.
#
# Writes DIR/install.json and prints it. Exit 0 every command succeeded, 2 usage, 3 codex or
# ~/.codex/config.toml missing, 1 a marketplace or install command failed (record still lands).
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
PLUGINS_DIR=$(CDPATH= cd -- "$PLUGIN_ROOT/.." && pwd -P)
REPO_ROOT=$(CDPATH= cd -- "$PLUGINS_DIR/.." && pwd -P)
CORE=$(basename -- "$PLUGIN_ROOT")
VAR=$(printf '%s' "$CORE" | tr 'a-z-' 'A-Z_')_CODEX_HOME
SETUP_HOME=$(eval "printf '%s' \"\${$VAR:-}\"")
CREDENTIAL=0
export PYTHONDONTWRITEBYTECODE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --home) [ $# -ge 2 ] || { echo "install.sh: --home takes a directory" >&2; exit 2; }
            SETUP_HOME="$2"; shift 2 ;;
    --credential) CREDENTIAL=1; shift ;;
    -h|--help) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "install.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$SETUP_HOME" ] || { echo "install.sh: name the isolated home: --home DIR or $VAR" >&2; exit 2; }
command -v codex >/dev/null 2>&1 || { echo "install.sh: codex is not on PATH" >&2; exit 3; }
[ -f "$HOME/.codex/config.toml" ] || { echo "install.sh: ~/.codex/config.toml is missing" >&2; exit 3; }
mkdir -p "$SETUP_HOME"
SETUP_HOME=$(CDPATH= cd -- "$SETUP_HOME" && pwd -P)
for forbidden in "$HOME/.codex" "$HOME/.local/share/skills-v2-pilot" "$HOME/.local/share/skills-v2-locked"; do
  case "$SETUP_HOME/" in "$forbidden"/*) echo "install.sh: $SETUP_HOME is under $forbidden, which no setup may touch" >&2; exit 2 ;; esac
done
export CODEX_HOME="$SETUP_HOME"
MARKET_NAME="$CORE-setup"
PLUGINS="$CORE records"

python3 - "$SETUP_HOME" "$CREDENTIAL" "$PLUGINS_DIR" "$MARKET_NAME" $PLUGINS <<'PY'
import json, os, re, sys
from pathlib import Path
home, credential, plugins_dir, market_name = Path(sys.argv[1]), sys.argv[2] == "1", Path(sys.argv[3]), sys.argv[4]
names = sys.argv[5:]
source = Path.home() / ".codex"
lines = [l for l in (source / "config.toml").read_text().splitlines()
         if re.match(r"^(model|model_reasoning_effort|sandbox_mode)\s*=", l)]
if len(lines) != 3:
    raise SystemExit("expected exactly the model, effort and sandbox lines in ~/.codex/config.toml")
base = "\n".join(lines) + '\napproval_policy = "never"\nweb_search = "disabled"\n\n[features]\nshell_snapshot = false\n'
child = home / "child"
child.mkdir(exist_ok=True)
(child / "uv-cache").mkdir(exist_ok=True)
(child / "config.toml").write_text(base)
(home / "config.toml").write_text(base + "\n[shell_environment_policy.set]\nCODEX_HOME = "
                                  + json.dumps(str(child)) + "\nUV_CACHE_DIR = "
                                  + json.dumps(str(child / "uv-cache")) + "\n")
if credential:
    if not (source / "auth.json").is_file():
        raise SystemExit("missing ~/.codex/auth.json")
    fd = os.open(str(home / "auth.json"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write((source / "auth.json").read_bytes())
    os.chmod(str(home / "auth.json"), 0o600)
    link = child / "auth.json"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(home / "auth.json")
market = home / "marketplace"
(market / ".claude-plugin").mkdir(parents=True, exist_ok=True)
rows = []
for name in names:
    link = market / name
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(plugins_dir / name)
    rows.append({"name": name, "source": "./" + name})
(market / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
    {"name": market_name, "owner": {"name": "skills v2 setup"}, "plugins": rows}, indent=2))
# A rerun installs fresh: clear this marketplace's cache so the copy is this checkout's.
cache = home / "plugins" / "cache" / market_name
if cache.is_dir():
    import shutil
    shutil.rmtree(str(cache))
sys.stderr.write(json.dumps({"home": str(home), "credential_written": credential}) + "\n")
PY

WORK=$(mktemp -d "${TMPDIR:-/tmp}/$CORE-codex-install.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM
: > "$WORK/failures"; : > "$WORK/results"
VERSION=$(codex --version 2>/dev/null | awk '{print $NF}')
st=0; codex plugin marketplace add "$SETUP_HOME/marketplace" --json > "$WORK/m.out" 2>&1 || st=$?
cat "$WORK/m.out" >&2
if [ "$st" -ne 0 ] && ! grep -qi "already" "$WORK/m.out"; then echo "marketplace add: exit $st" >> "$WORK/failures"; fi
for plugin in $PLUGINS; do
  st=0; codex plugin add "$plugin@$MARKET_NAME" --json > "$WORK/out" 2>&1 || st=$?
  line=$(head -1 "$WORK/out"); echo "$plugin@$MARKET_NAME: exit $st: $line" >&2
  [ "$st" -eq 0 ] || echo "plugin add $plugin@$MARKET_NAME: exit $st" >> "$WORK/failures"
  printf '%s\t%s\t%s\n' "$plugin@$MARKET_NAME" "$st" "$line" >> "$WORK/results"
done
python3 - "$SETUP_HOME" "$CORE" "$VERSION" "$REPO_ROOT" "$MARKET_NAME" "$WORK/results" "$WORK/failures" "$CREDENTIAL" <<'PY'
import json, os, subprocess, sys
home, core, version, repo, market, results, failures, credential = sys.argv[1:9]
rows = []
for line in open(results).read().splitlines():
    spec, status, first = (line.split("\t") + ["", ""])[:3]
    rows.append({"plugin": spec, "exit": int(status), "first_line": first})
failed = [l for l in open(failures).read().splitlines() if l.strip()]
cache = os.path.join(home, "plugins", "cache", market)
installed = sorted(os.path.join(cache, p, v) for p in (os.listdir(cache) if os.path.isdir(cache) else [])
                   for v in os.listdir(os.path.join(cache, p)))
commit = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], stdout=subprocess.PIPE).stdout.decode().strip()
auth = os.path.join(home, "auth.json")
doc = {"core": core, "harness": "codex", "codex_home": home, "marketplace": market,
       "codex_version": version, "repo_root": repo, "commit": commit, "installs": rows,
       "installed_plugin_dirs": installed,
       "credential": ("written by --credential, mode %s" % oct(os.stat(auth).st_mode & 0o777))
                     if credential == "1" and os.path.isfile(auth) else "not written (no --credential)",
       "ok": not failed, "failed_commands": failed}
with open(os.path.join(home, "install.json"), "w") as handle:
    json.dump(doc, handle, indent=2); handle.write("\n")
print(json.dumps(doc, indent=2))
sys.exit(1 if failed else 0)
PY
