#!/bin/sh
# recheck-v2 pilot setup, lane Q: OpenCode with its OpenRouter provider (E9 ruling D3a).
#
# Creates the isolated pilot home under ~/.local/share/skills-v2-pilot/opencode/ and installs
# the pinned opencode binary, the isolated XDG config and data homes, the two model
# sub-setups, the recheck-verifier agent, the session-pointer plugin, the recheck-v2 skill
# folder, and the two shared probes. Touches nothing under ~/.config/opencode,
# ~/.local/share/opencode, ~/.claude, or any repository.
#
# Usage:  sh install.sh [--setup DIR] [--model MODEL] [--npm-cache DIR] [--without recheck-v2]
#   --setup DIR      the isolated pilot home (default ~/.local/share/skills-v2-pilot/opencode)
#   --model M        the default model written into opencode.json
#                    (default openrouter/qwen/qwen3.8-flash)
#   --npm-cache DIR  npm's cache and log directory (default <setup>/npm-cache). Pinned so npm
#                    writes nothing under ~/.npm or ~/.npm/_logs (E9 section 3; Astra finding 9)
#   --without recheck-v2
#                    skip the one step that installs the recheck-v2 skill folder, so the home
#                    this install builds never held it on any surface (E10-3, authorized by
#                    ruling E10-56(1)). Everything else is identical: the binary, the config,
#                    the verifier agent, the session-pointer plugin and the two shared probes
#
# Requires OPENROUTER_API_KEY in the environment, ONCE, at install time. Ruling E9-38: the key
# never rides in a session's environment, because every tool shell inherits it and a probe that
# dumps the environment then prints it into the harness's own records. install.sh copies the
# value out of the variable into the harness's own auth store under the setup's XDG_DATA_HOME
# (mode 0600) without printing it, and `launch.sh` and `verifier.py` launch the harness with
# OPENROUTER_API_KEY removed from its environment. The install report names the auth file and
# its mode, never its contents, and the last step scans the setup's own records for
# credential-SHAPED values and refuses to report success when one is present (Astra finding 1).
# No credential value appears in this script.
#
# Side effects: creates <setup>/{npm,npm-cache,records,xdg-config,xdg-data,xdg-cache,xdg-state};
# runs `npm install --prefix <setup>/npm opencode-ai@<pinned>` with its cache and logs pinned;
# writes <setup>/xdg-config/opencode/{opencode.json,plugin/session-pointer.js}, the skill
# folders under <setup>/xdg-config/opencode/skill/, <setup>/xdg-data/opencode/auth.json (mode
# 0600, the provider key, ruling E9-38), and <setup>/records/providers.txt (the
# harness's own provider listing, with any credential-shaped token replaced by its shape
# name). Rerunning replaces those files and leaves the session store
# (<setup>/xdg-data/opencode/opencode.db) alone.
set -eu

OPENCODE_VERSION="1.18.31"   # pinned 2026-09-14 from `npm view opencode-ai version`
SETUP="${HOME}/.local/share/skills-v2-pilot/opencode"
MODEL="openrouter/qwen/qwen3.8-flash"
NPM_CACHE=""
WITHOUT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --setup) SETUP="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --npm-cache) NPM_CACHE="$2"; shift 2 ;;
    --without)
      [ "$2" = "recheck-v2" ] || {
        echo "install.sh: --without takes recheck-v2 (E10-56(1)), not $2" >&2; exit 2; }
      WITHOUT="recheck-v2"; shift 2 ;;
    -h|--help) sed -n '2,34p' "$0"; exit 0 ;;
    *) echo "install.sh: unknown argument $1" >&2; exit 2 ;;
  esac
done

HERE=$(cd "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(cd "$HERE/../.." && pwd)     # plugins/recheck-v2
SKILL_SRC="$PLUGIN_ROOT/skills/recheck-v2"
FIXTURES="$PLUGIN_ROOT/setups/_fixtures"

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "install.sh: OPENROUTER_API_KEY is not set in the environment" >&2
  echo "install.sh: it is read once, here, and copied into the setup's own auth store; no session ever sees it (ruling E9-38)" >&2
  exit 3
fi
echo "credential: OPENROUTER_API_KEY set in this shell (read once, written to the auth store below)"

mkdir -p "$SETUP/npm" "$SETUP/records" "$SETUP/xdg-config/opencode" \
         "$SETUP/xdg-data" "$SETUP/xdg-cache" "$SETUP/xdg-state"
SETUP=$(cd "$SETUP" && pwd)
[ -n "$NPM_CACHE" ] || NPM_CACHE="$SETUP/npm-cache"
mkdir -p "$NPM_CACHE" "$NPM_CACHE/_logs"
NPM_CACHE=$(cd "$NPM_CACHE" && pwd)

# npm's cache and logs stay inside the permitted roots: without these it writes ~/.npm and
# ~/.npm/_logs, outside the setup and against section 3's isolation rule (Astra finding 9).
echo "installing opencode-ai@$OPENCODE_VERSION into $SETUP/npm (npm cache $NPM_CACHE)"
npm_config_cache="$NPM_CACHE" npm_config_logs_dir="$NPM_CACHE/_logs" \
  npm install --prefix "$SETUP/npm" "opencode-ai@$OPENCODE_VERSION" >/dev/null
OC="$SETUP/npm/node_modules/.bin/opencode"
[ -x "$OC" ] || { echo "install.sh: opencode binary missing at $OC" >&2; exit 3; }

# The config: the two model sub-setups, the verifier agent, the default model, and the
# external-directory allow rule for the run root.
#
# Measured on 1.18.31: the default rule is `external_directory * ask`, and in a headless
# `opencode run` an "ask" is auto-rejected ("The user rejected permission to use this specific
# tool call"), so a write to the run directory the contract puts OUTSIDE the workspace fails.
# The run root is ${TMPDIR:-/tmp}/recheck-v2 (contract section 2 and the adapter profile
# section 3); install.sh writes the machine's concrete TMPDIR into the rule and keeps a
# /tmp/recheck-v2 rule for a shell without TMPDIR. Rules are evaluated last-match-wins, so
# the broad "ask" comes first.
RUNROOT="${TMPDIR:-/tmp}"
RUNROOT="${RUNROOT%/}/runs"  # E10-22: a neutral name; the E10 prompt names this path
TMPROOT="${TMPDIR:-/tmp}"; TMPROOT="${TMPROOT%/}"  # E10-23: the whole TMPDIR is allowed, so a model-chosen scratch path there is not auto-rejected
# E11-45 S1: the write fence's denied side. Last-match-wins, so these rules come after the
# allows in the asset and a write to a pilot home, the checkout or either wall is declined by
# the harness rather than only forbidden by the mandate. The trial's own roots are never here.
DENY_1="${SKILLS_V2_PILOT_ROOT:-$HOME/.local/share/skills-v2-pilot}/claude-code"
DENY_2="${SKILLS_V2_PILOT_ROOT:-$HOME/.local/share/skills-v2-pilot}/codex"
DENY_3="${SKILLS_V2_PILOT_ROOT:-$HOME/.local/share/skills-v2-pilot}/opencode"
DENY_4="$SETUP"   # E10-62 item 3: the homes are keyed by SETUP NAME, so this home's own
                  # directory is named directly; the three harness names above miss
                  # `opencode-deepseek` and every future second setup of one harness.
sed -e "s|__MODEL__|$MODEL|g" -e "s|__RUNROOT__|$RUNROOT|g" -e "s|__TMPROOT__|$TMPROOT|g" \
    -e "s|__DENY_1__|$DENY_1|g" -e "s|__DENY_2__|$DENY_2|g" \
    -e "s|__DENY_3__|$DENY_3|g" -e "s|__DENY_4__|$DENY_4|g" \
  "$HERE/assets/opencode.json" > "$SETUP/xdg-config/opencode/opencode.json"
echo "run root allowed: $RUNROOT (and $TMPROOT/** under E10-23)"
echo "write fence denied: $DENY_1, $DENY_2, $DENY_3, $DENY_4 (E11-45 S1)"

# The session pointer plugin (the user channel; see adapters/opencode/profile.md section 4).
# It also records which CLI command started the harness process, which is where
# `invocation.mode` comes from (ruling E9-33).
mkdir -p "$SETUP/xdg-config/opencode/plugin"
cp "$HERE/assets/session-pointer.js" "$SETUP/xdg-config/opencode/plugin/session-pointer.js"

# The skill folder and the two shared probes, on the surface this setup ships:
# <isolated XDG_CONFIG_HOME>/opencode/skill/<name>/ (measured in RESULTS.md).
SKILLDIR="$SETUP/xdg-config/opencode/skill"
mkdir -p "$SKILLDIR"
for name in recheck-v2 delivery-probe manual-only-probe; do
  rm -rf "$SKILLDIR/$name"
done
# E10-56(1): the one install step of the skill, skipped by --without recheck-v2, so the home
# never held it on any surface. The loop above already cleared any earlier copy.
if [ "$WITHOUT" = "recheck-v2" ]; then
  echo "skill: recheck-v2 NOT installed (--without recheck-v2, E10-56(1))"
else
  cp -R "$SKILL_SRC" "$SKILLDIR/recheck-v2"
fi
cp -R "$FIXTURES/delivery-probe/skills/delivery-probe" "$SKILLDIR/delivery-probe"
cp -R "$FIXTURES/manual-only-probe/skills/manual-only-probe" "$SKILLDIR/manual-only-probe"
find "$SKILLDIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

export XDG_CONFIG_HOME="$SETUP/xdg-config"
export XDG_DATA_HOME="$SETUP/xdg-data"
export XDG_CACHE_HOME="$SETUP/xdg-cache"
export XDG_STATE_HOME="$SETUP/xdg-state"
export OPENCODE_DISABLE_EXTERNAL_SKILLS=1

# The auth store (ruling E9-38). Measured on 1.18.31: the harness reads
# $XDG_DATA_HOME/opencode/auth.json, a record keyed by provider id whose api-key variant is
# {"type": "api", "key": "<value>"}. With the file absent and OPENROUTER_API_KEY unset,
# `opencode providers list` reports "0 credentials"; with the file present it reports
# "OpenRouter api" and "1 credentials". The value moves from the variable to the file inside
# python, through a 0600 file descriptor, and is never echoed, logged or passed as an argument.
AUTH="$SETUP/xdg-data/opencode/auth.json"
mkdir -p "$SETUP/xdg-data/opencode"
/usr/bin/python3 - "$AUTH" <<'PY'
import json, os, sys
path = sys.argv[1]
key = os.environ.get("OPENROUTER_API_KEY") or ""
if not key:
    sys.stderr.write("the variable vanished before the auth store was written\n")
    raise SystemExit(3)
record = {}
if os.path.isfile(path):
    try:
        with open(path, encoding="utf-8") as handle:
            record = json.load(handle) or {}
    except (IOError, OSError, ValueError):
        record = {}
record["openrouter"] = {"type": "api", "key": key}
fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as handle:
    json.dump(record, handle)
    handle.write("\n")
os.replace(path + ".tmp", path)
os.chmod(path, 0o600)
PY
chmod 600 "$AUTH"
echo "auth store: $AUTH mode $(/usr/bin/python3 -c 'import os,sys;print("%o" % (os.stat(sys.argv[1]).st_mode & 0o777))' "$AUTH") (contents never printed)"

# Everything the installer runs from here on runs WITHOUT the variable, so no record it writes
# can carry the value and the auth store is proved to be what the harness reads.
env -u OPENROUTER_API_KEY "$OC" --version

# The provider proof, read from the harness's own listing with the credential column left out
# (Astra finding 1). `opencode providers list` prints the credential FILE and a count, never a
# value, on 1.18.31; the filter below is the guard, not the measurement: it strips terminal
# colour codes and replaces any credential-shaped token with the shape's name, so no value can
# reach the record even if a later version starts printing one.
env -u OPENROUTER_API_KEY "$OC" providers list > "$SETUP/records/providers.raw" 2>/dev/null || true
/usr/bin/python3 - "$SETUP/records/providers.raw" "$SETUP/records/providers.txt" <<'PY'
import re, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8", errors="replace").read()
text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
for shape, pattern in (("openrouter-key", r"sk-or-v1-[0-9a-f]{64}"),
                       ("provider-key", r"sk-[A-Za-z0-9_-]{40,}"),
                       ("jwt", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")):
    text = re.sub(pattern, "<%s omitted>" % shape, text)
open(dst, "w", encoding="utf-8").write(text)
PY
rm -f "$SETUP/records/providers.raw"
echo "providers: $SETUP/records/providers.txt (credential column omitted)"
# The auth store is the only thing that authorizes a run now: with OPENROUTER_API_KEY removed
# the harness must still report the credential, or this install is not usable.
if grep -q "1 credentials" "$SETUP/records/providers.txt"; then
  echo "auth check: the harness reports 1 credential with OPENROUTER_API_KEY removed from its environment"
else
  echo "install.sh: FAILED - with OPENROUTER_API_KEY removed the harness reports no credential; see $SETUP/records/providers.txt" >&2
  exit 3
fi

echo "setup:   $SETUP"
echo "binary:  $OC"
echo "model:   $MODEL"
echo "skills:  $(ls "$SKILLDIR" | tr '\n' ' ')"

# The last step of the report: scan the setup's own records for credential-shaped values. A
# hit means this install must not be reported as done (Astra finding 1).
SCAN="$SETUP/records/secret-scan.json"
if sh "$HERE/scan-secrets.sh" --setup "$SETUP" --quiet > "$SCAN"; then
  echo "secret scan: clean ($(/usr/bin/python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("%d files, 0 hits" % d["files_scanned"])' "$SCAN"))"
  echo "install.sh: done"
else
  echo "install.sh: FAILED — the setup's records hold credential-shaped values; see $SCAN" >&2
  /usr/bin/python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); [sys.stderr.write("  %s shape=%s offset=%d length=%d\n" % (h["file"], h["shape"], h["offset"], h["length"])) for h in d["hits"]]' "$SCAN" >&2
  exit 5
fi
