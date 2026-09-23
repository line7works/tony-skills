#!/bin/sh
# Three stations, one records component (E13 slice 3, brief 3.4; E12 amendment A6's installed
# shape). No model and no session: installs and CLI calls only.
#
# Usage: three-stations.sh claude-code|codex <fresh isolated home>
#
# Builds ONE marketplace inside the home whose entries are symlinks to the worktree's
# recheck-v2, build-v2, signoff-v2 and records folders, installs all four into the harness's
# isolated home (CLAUDE_CONFIG_DIR=<home>/config, or CODEX_HOME=<home>), then for each installed
# station:
#   1. `uv run <installed station>/skills/<station>/scripts/<cli> skill-identity`, a command that
#      performs the lookup and the confirm step (every one of the three opens its records client
#      before answering), with RECORDS_ROOT unset and no --records-root;
#   2. the station's own copied client, imported from its INSTALLED location, printing the root
#      it resolved and the interface version it confirmed;
# and then renames the installed records folder away and repeats step 1, where each station must
# exit 3 with the interface's one line naming route 3b's directory. The folder is put back.
# One JSON document on stdout. Exit 0 when every expectation held, 1 otherwise, 2 usage.
set -eu
[ $# -eq 2 ] || { echo "usage: three-stations.sh claude-code|codex <fresh isolated home>" >&2; exit 2; }
HARNESS="$1"; SETUP_HOME="$2"
case "$HARNESS" in claude-code|codex) ;; *) echo "three-stations.sh: harness is claude-code or codex" >&2; exit 2 ;; esac
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGINS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
[ ! -e "$SETUP_HOME" ] || [ -z "$(ls -A "$SETUP_HOME" 2>/dev/null)" ] || { echo "three-stations.sh: $SETUP_HOME is not empty" >&2; exit 2; }
mkdir -p "$SETUP_HOME"
SETUP_HOME=$(CDPATH= cd -- "$SETUP_HOME" && pwd -P)
case "$SETUP_HOME/" in "$HOME/.claude/"*|"$HOME/.codex/"*|"$HOME/.local/share/skills-v2-"*) echo "three-stations.sh: not a live or pilot home" >&2; exit 2 ;; esac
export PYTHONDONTWRITEBYTECODE=1
unset RECORDS_ROOT || true
exec python3 - "$HARNESS" "$SETUP_HOME" "$PLUGINS_DIR" <<'PY'
import json, os, shutil, subprocess, sys
harness, home, plugins_dir = sys.argv[1:4]
MARKET = "three-stations"
STATIONS = {"recheck-v2": ("recheck.py", "recheck_core"), "build-v2": ("build.py", "build_core"),
            "signoff-v2": ("signoff.py", "signoff_core")}
names = list(STATIONS) + ["records"]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
env.pop("RECORDS_ROOT", None)
if harness == "claude-code":
    env["CLAUDE_CONFIG_DIR"] = os.path.join(home, "config")
    cache = os.path.join(home, "config", "plugins", "cache", MARKET)
else:
    env["CODEX_HOME"] = home
    cache = os.path.join(home, "plugins", "cache", MARKET)
os.makedirs(os.path.join(home, "config") if harness == "claude-code" else home, exist_ok=True)
market = os.path.join(home, "marketplace")
os.makedirs(os.path.join(market, ".claude-plugin"))
for name in names:
    os.symlink(os.path.join(plugins_dir, name), os.path.join(market, name))
with open(os.path.join(market, ".claude-plugin", "marketplace.json"), "w") as handle:
    json.dump({"name": MARKET, "owner": {"name": "E13 slice 3"},
               "plugins": [{"name": n, "source": "./" + n} for n in names]}, handle)

def run(argv, cwd="/"):
    proc = subprocess.run(argv, env=env, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {"command": " ".join(argv), "exit": proc.returncode,
            "stdout": proc.stdout.decode("utf-8", "replace").strip(),
            "stderr": proc.stderr.decode("utf-8", "replace").strip()}

report = {"harness": harness, "home": home, "marketplace": MARKET, "steps": [], "stations": {},
          "negative": {}, "problems": []}
version = run(["claude" if harness == "claude-code" else "codex", "--version"])
report["harness_version"] = version["stdout"]
if harness == "claude-code":
    report["steps"].append(run(["claude", "plugin", "marketplace", "add", market]))
    for name in names:
        report["steps"].append(run(["claude", "plugin", "install", "%s@%s" % (name, MARKET),
                                    "--json", "-y"]))
else:
    report["steps"].append(run(["codex", "plugin", "marketplace", "add", market, "--json"]))
    for name in names:
        report["steps"].append(run(["codex", "plugin", "add", "%s@%s" % (name, MARKET), "--json"]))
for step in report["steps"]:
    if step["exit"] != 0:
        report["problems"].append("install step failed: %s (exit %s)" % (step["command"], step["exit"]))
report["installed"] = {n: sorted(os.listdir(os.path.join(cache, n))) if os.path.isdir(
    os.path.join(cache, n)) else [] for n in names}
records_versions = report["installed"]["records"]
expected_root = os.path.join(cache, "records", records_versions[0]) if len(records_versions) == 1 else None
report["route_3b_directory"] = os.path.join(cache, "records")

PROBE = ("import json,sys\nsys.path.insert(0,sys.argv[1])\n"
         "from %s import records_client as rcl\n"
         "c=rcl.open_client()\nprint(json.dumps({'root':c.root,'interface_version':c.interface_version}))\n")
for station, (cli, package) in STATIONS.items():
    versions = report["installed"][station]
    if len(versions) != 1:
        report["problems"].append("%s: expected one installed version, found %s" % (station, versions))
        continue
    scripts = os.path.join(cache, station, versions[0], "skills", station, "scripts")
    identity = run(["uv", "run", "--quiet", os.path.join(scripts, cli), "skill-identity"])
    client = run(["python3", "-c", PROBE % package, scripts])
    row = {"installed_scripts": scripts, "skill_identity": identity, "client": client}
    try:
        resolved = json.loads(client["stdout"])
        row["resolved_root"] = resolved["root"]
        row["confirmed_interface_version"] = resolved["interface_version"]
        row["resolved_by_route_3b"] = (expected_root is not None and
                                       os.path.realpath(resolved["root"]) == os.path.realpath(expected_root))
    except (ValueError, KeyError):
        row["resolved_by_route_3b"] = False
    if identity["exit"] != 0 or not row.get("resolved_by_route_3b"):
        report["problems"].append("%s did not resolve the installed component by route 3b" % station)
    report["stations"][station] = row

hidden = os.path.join(cache, "records.hidden-by-three-stations")
if os.path.isdir(os.path.join(cache, "records")):
    os.rename(os.path.join(cache, "records"), hidden)
    try:
        for station, (cli, _package) in STATIONS.items():
            versions = report["installed"][station]
            if len(versions) != 1:
                continue
            scripts = os.path.join(cache, station, versions[0], "skills", station, "scripts")
            got = run(["uv", "run", "--quiet", os.path.join(scripts, cli), "skill-identity"])
            line = got["stderr"].splitlines()[-1] if got["stderr"] else ""
            names_3b = (os.path.join(cache, station, versions[0], "..", "..", "records")
                        + " (no such directory)") in line
            got["one_line_refusal"] = line
            got["names_route_3b_directory"] = names_3b
            report["negative"][station] = got
            if got["exit"] != 3 or not line.startswith("missing dependency: records component (looked in: ") or not names_3b:
                report["problems"].append("%s: the missing-component refusal is not the interface's" % station)
    finally:
        os.rename(hidden, os.path.join(cache, "records"))
report["ok"] = not report["problems"]
print(json.dumps(report, indent=2))
sys.exit(0 if report["ok"] else 1)
PY
