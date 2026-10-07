#!/bin/sh
# Ten stations, one records component (the E15 lane contract section 11, slice 3): inspect-v2's seven-stations.sh
# (E14 slice 3c, item 3.7; that file is frozen by ruling E15-2 and stays as it is), copied here and extended to the
# ten v2 stations. No model and no session: installs and CLI calls only.
#
# Usage: ten-stations.sh claude-code|codex <fresh isolated home>
#
# Builds ONE marketplace inside the home whose entries are symlinks to the worktree's recheck-v2, build-v2,
# signoff-v2, precon-v2, architect-v2, blueprint-v2, inspect-v2, vertical-v2, handoff-v2, ship-v2 and records
# folders, installs all eleven into the harness's isolated home (CLAUDE_CONFIG_DIR=<home>/config, or
# CODEX_HOME=<home>), then for each installed station:
#   1. `uv run <installed station>/skills/<station>/scripts/<cli> skill-identity`, with RECORDS_ROOT unset and no
#      --records-root (build-v2 and signoff-v2 open their records client before answering; recheck-v2 answers
#      without it since the E15 lane contract A27 (2); the four front cores and the three back cores answer
#      without it);
#   2. the station's own copied client, imported from its INSTALLED location, printing the root it resolved and the
#      interface version it confirmed (route 3b: the installed records folder);
#   3. its manual-only controls as installed: `disable-model-invocation: true` in its SKILL.md frontmatter and
#      `allow_implicit_invocation: false` in its Codex sidecar. Owner pick P5 is held for the three back cores:
#      handoff-v2 carries both; vertical-v2 and ship-v2 carry neither (their summons are kept). The other seven are
#      recorded as found.
# then inspect-v2's code book (`station_core/sibling.py` resolving blueprint-v2's installed SKILL.md by route 3b),
# and ship-v2's sibling lookup: `ship_core/stations.py`, imported from ship-v2's installed location, resolving
# build-v2, signoff-v2 and recheck-v2 installed (route 3b, the installed folder), reading each one's identity through
# that station's own CLI as a visit does, and holding it to the trace's refusal rule (no refusal).
# Then the negatives. The installed records folder is renamed away: build-v2's and signoff-v2's `skill-identity`
# must exit 3 with the interface's one line naming route 3b's directory; every other station's `skill-identity` must
# still exit 0 (it never opens the component) and its installed client must refuse with exit 3 and that same line.
# The folder is put back. The installed blueprint-v2 folder is renamed away: inspect-v2's sibling lookup must refuse
# (exit 3) naming route 3b's directory. The folder is put back. Each of build-v2, signoff-v2 and recheck-v2 is renamed
# away in turn: ship-v2's sibling lookup must refuse it (exit 3, `missing station: <name>`) and still resolve the
# other two. Each folder is put back.
# One JSON document on stdout. Exit 0 when every expectation held, 1 otherwise, 2 usage.
set -eu
[ $# -eq 2 ] || { echo "usage: ten-stations.sh claude-code|codex <fresh isolated home>" >&2; exit 2; }
HARNESS="$1"; SETUP_HOME="$2"
case "$HARNESS" in claude-code|codex) ;; *) echo "ten-stations.sh: harness is claude-code or codex" >&2; exit 2 ;; esac
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGINS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
[ ! -e "$SETUP_HOME" ] || [ -z "$(ls -A "$SETUP_HOME" 2>/dev/null)" ] || { echo "ten-stations.sh: $SETUP_HOME is not empty" >&2; exit 2; }
# The home guard, before anything is created (inspect-v2's seven-stations.sh, byte for byte but its name): the home,
# as given and resolved, may not be or sit under ~/.claude, ~/.codex or ~/.local/share/skills-v2-*, whichever harness
# this is. TMPDIR, TEMP and TMP are held to the same rule.
SETUP_HOME=$(env -u TMPDIR -u TEMP -u TMP python3 - "$SETUP_HOME" "$HOME" "ten-stations.sh" "${TMPDIR-}" "${TEMP-}" "${TMP-}" <<'GUARD'
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
export PYTHONDONTWRITEBYTECODE=1
unset RECORDS_ROOT || true
# The interpreter starts with TMPDIR, TEMP and TMP cleared (the guard has held their values) and the body puts them
# back first, as manual-only.sh does.
exec env -u TMPDIR -u TEMP -u TMP python3 - "$HARNESS" "$SETUP_HOME" "$PLUGINS_DIR" "${TMPDIR-}" "${TEMP-}" \
  "${TMP-}" <<'PY'
import json, os, re, subprocess, sys
harness, home, plugins_dir = sys.argv[1:4]
for key, value in zip(("TMPDIR", "TEMP", "TMP"), sys.argv[4:7]):
    if value:
        os.environ[key] = value
MARKET = "ten-stations"
# station -> (its CLI, the package that holds its copied records client, opens the client at skill-identity)
STATIONS = {"recheck-v2": ("recheck.py", "recheck_core", False), "build-v2": ("build.py", "build_core", True),
            "signoff-v2": ("signoff.py", "signoff_core", True),
            "precon-v2": ("precon.py", "station_core", False),
            "architect-v2": ("architect.py", "station_core", False),
            "blueprint-v2": ("blueprint.py", "station_core", False),
            "inspect-v2": ("inspect_v2.py", "station_core", False),
            "vertical-v2": ("vertical.py", "station_core", False),
            "handoff-v2": ("handoff.py", "station_core", False),
            "ship-v2": ("ship.py", "station_core", False)}
CODE_BOOK = "blueprint-v2"
SIBLINGS = ["build-v2", "signoff-v2", "recheck-v2"]
# owner pick P5 for the three back cores; the other seven are recorded as found
MANUAL_ONLY = {"handoff-v2": True, "vertical-v2": False, "ship-v2": False}
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
    json.dump({"name": MARKET, "owner": {"name": "E15 slice 3"},
               "plugins": [{"name": n, "source": "./" + n} for n in names]}, handle)


def run(argv, cwd="/"):
    proc = subprocess.run(argv, env=env, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {"command": " ".join(argv), "exit": proc.returncode,
            "stdout": proc.stdout.decode("utf-8", "replace").strip(),
            "stderr": proc.stderr.decode("utf-8", "replace").strip()}


def last_line(result):
    return result["stderr"].splitlines()[-1] if result["stderr"] else ""


report = {"harness": harness, "home": home, "marketplace": MARKET, "steps": [], "stations": {}, "code_book": {},
          "siblings": {}, "siblings_expected": SIBLINGS, "manual_only_expected": MANUAL_ONLY, "manual_only": {},
          "negative": {}, "negative_code_book": {}, "negative_siblings": {}, "problems": []}
version = run(["claude" if harness == "claude-code" else "codex", "--version"])
report["harness_version"] = version["stdout"]
if harness == "claude-code":
    report["steps"].append(run(["claude", "plugin", "marketplace", "add", market]))
    for name in names:
        report["steps"].append(run(["claude", "plugin", "install", "%s@%s" % (name, MARKET), "--json", "-y"]))
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
         "try:\n"
         "    c=rcl.open_client()\n"
         "except rcl.ComponentUnavailable as exc:\n"
         "    sys.stderr.write('%%s\\n' %% exc)\n"
         "    sys.exit(3)\n"
         "print(json.dumps({'root':c.root,'interface_version':c.interface_version}))\n")
SIBLING = ("import json,sys\nsys.path.insert(0,sys.argv[1])\n"
           "from station_core import sibling\nfrom inspect_core import common\n"
           "try:\n"
           "    found=sibling.resolve(sys.argv[2],common.plugin_root())\n"
           "    path=sibling.skill_file(found['root'],sys.argv[2])\n"
           "except (LookupError, sibling.SiblingRefused) as exc:\n"
           "    sys.stderr.write('%s\\n' % exc)\n"
           "    sys.exit(3)\n"
           "print(json.dumps({'root':found['root'],'route':found['route'],'skill_file':path}))\n")
# ship-v2's own sibling lookup and identity read, from its installed copy: the code a visit runs before the visit
SHIP_SIBLING = ("import json,sys\nsys.path.insert(0,sys.argv[1])\n"
                "from ship_core import stations\n"
                "try:\n"
                "    found=stations.resolve(sys.argv[2])\n"
                "except (LookupError, stations.RootRefused) as exc:\n"
                "    sys.stderr.write('%s\\n' % exc)\n"
                "    sys.exit(3)\n"
                "identity=stations.identify(sys.argv[2],found)\n"
                "refusals=stations.refusals(sys.argv[2],identity,found)\n"
                "print(json.dumps({'root':found['root'],'route':found['route'],'identity':identity,"
                "'refusals':refusals}))\n")


def scripts_of(station):
    versions = report["installed"][station]
    if len(versions) != 1:
        return None
    return os.path.join(cache, station, versions[0], "skills", station, "scripts")


def root_of(station):
    versions = report["installed"][station]
    return os.path.join(cache, station, versions[0]) if len(versions) == 1 else None


def route_3b_named(station, line, component):
    versions = report["installed"][station]
    return (os.path.join(cache, station, versions[0], "..", "..", component) + " (no such directory)") in line


def frontmatter(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else ""


def controls(root, name):
    skill = os.path.join(root, "skills", name, "SKILL.md")
    sidecar = os.path.join(root, "skills", name, "agents", "openai.yaml")
    text = open(sidecar, encoding="utf-8").read() if os.path.isfile(sidecar) else ""
    return {"skill_md": skill, "sidecar": sidecar if os.path.isfile(sidecar) else None,
            "disable_model_invocation": os.path.isfile(skill) and re.search(
                r"^disable-model-invocation: true$", frontmatter(skill), re.M) is not None,
            "allow_implicit_invocation_false": re.search(
                r"^policy:\n(?:  .*\n)*?  allow_implicit_invocation: false$", text, re.M) is not None}


for station, (cli, package, opens) in STATIONS.items():
    scripts = scripts_of(station)
    if scripts is None:
        report["problems"].append("%s: expected one installed version, found %s"
                                  % (station, report["installed"][station]))
        continue
    identity = run(["uv", "run", "--quiet", os.path.join(scripts, cli), "skill-identity"])
    client = run(["python3", "-c", PROBE % package, scripts])
    row = {"installed_scripts": scripts, "opens_records_at_skill_identity": opens,
           "skill_identity": identity, "client": client}
    try:
        said = json.loads(identity["stdout"])
        row["identity_name"] = said.get("name")
        row["identity_version"] = said.get("version")
        row["identity_interface_version"] = said.get("interface_version")
        if said.get("name") != station:
            report["problems"].append("%s: skill-identity names %r" % (station, said.get("name")))
    except ValueError:
        report["problems"].append("%s: skill-identity printed no JSON document" % station)
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
    found = controls(root_of(station), station)
    report["manual_only"][station] = found
    if station in MANUAL_ONLY:
        want = MANUAL_ONLY[station]
        if found["disable_model_invocation"] != want or found["allow_implicit_invocation_false"] != want:
            report["problems"].append("%s: installed manual-only controls %s, P5 says %s" % (
                station, {k: found[k] for k in ("disable_model_invocation", "allow_implicit_invocation_false")},
                "both" if want else "neither"))

inspect_scripts = scripts_of("inspect-v2")
book_versions = report["installed"][CODE_BOOK]
expected_book = os.path.join(cache, CODE_BOOK, book_versions[0]) if len(book_versions) == 1 else None
if inspect_scripts is not None:
    got = run(["python3", "-c", SIBLING, inspect_scripts, CODE_BOOK])
    report["code_book"] = got
    try:
        found = json.loads(got["stdout"])
        got["route"] = found["route"]
        got["resolved_by_route_3b"] = (found["route"] == "3b" and expected_book is not None and
                                       os.path.realpath(found["root"]) == os.path.realpath(expected_book)
                                       and os.path.isfile(found["skill_file"]))
    except (ValueError, KeyError):
        got["resolved_by_route_3b"] = False
    if got["exit"] != 0 or not got["resolved_by_route_3b"]:
        report["problems"].append("inspect-v2 did not resolve blueprint-v2's installed SKILL.md by route 3b")

ship_scripts = scripts_of("ship-v2")


def ship_lookup(name):
    return run(["uv", "run", "--offline", "--quiet", "--with", "jsonschema==4.25.1", "python3", "-c", SHIP_SIBLING,
                ship_scripts, name])


if ship_scripts is not None:
    for name in SIBLINGS:
        got = ship_lookup(name)
        report["siblings"][name] = got
        want = root_of(name)
        try:
            found = json.loads(got["stdout"])
            got["route"] = found["route"]
            got["identity"] = found["identity"]
            got["refusals"] = found["refusals"]
            got["resolved_by_route_3b"] = (found["route"] == "3b" and want is not None
                                           and os.path.realpath(found["root"]) == os.path.realpath(want))
        except (ValueError, KeyError):
            got["resolved_by_route_3b"] = False
        if got["exit"] != 0 or not got["resolved_by_route_3b"] or got.get("refusals") \
                or (got.get("identity") or {}).get("name") != name \
                or (got.get("identity") or {}).get("interface_version") != 1:
            report["problems"].append("ship-v2 did not resolve and identify %s installed by route 3b" % name)

hidden = os.path.join(cache, "records.hidden-by-ten-stations")
if os.path.isdir(os.path.join(cache, "records")):
    os.rename(os.path.join(cache, "records"), hidden)
    try:
        for station, (cli, package, opens) in STATIONS.items():
            scripts = scripts_of(station)
            if scripts is None:
                continue
            got = run(["uv", "run", "--quiet", os.path.join(scripts, cli), "skill-identity"])
            client = run(["python3", "-c", PROBE % package, scripts])
            refusal = got if opens else client
            line = last_line(refusal)
            row = {"skill_identity": got, "client": client, "one_line_refusal": line,
                   "names_route_3b_directory": route_3b_named(station, line, "records")}
            report["negative"][station] = row
            if not line.startswith("missing dependency: records component (looked in: ") \
                    or not row["names_route_3b_directory"] or refusal["exit"] != 3:
                report["problems"].append("%s: the missing-component refusal is not the interface's" % station)
            if not opens and got["exit"] != 0:
                report["problems"].append("%s: skill-identity opened the records component" % station)
            if opens and client["exit"] != 3:
                report["problems"].append("%s: its installed client did not refuse" % station)
    finally:
        os.rename(hidden, os.path.join(cache, "records"))

book_hidden = os.path.join(cache, CODE_BOOK + ".hidden-by-ten-stations")
if inspect_scripts is not None and os.path.isdir(os.path.join(cache, CODE_BOOK)):
    os.rename(os.path.join(cache, CODE_BOOK), book_hidden)
    try:
        got = run(["python3", "-c", SIBLING, inspect_scripts, CODE_BOOK])
        line = last_line(got)
        got["one_line_refusal"] = line
        got["names_route_3b_directory"] = route_3b_named("inspect-v2", line, CODE_BOOK)
        report["negative_code_book"] = got
        if got["exit"] != 3 or not line.startswith("missing sibling: blueprint-v2 (looked in: ") \
                or not got["names_route_3b_directory"]:
            report["problems"].append("inspect-v2: the missing code book refusal does not name route 3b")
    finally:
        os.rename(book_hidden, os.path.join(cache, CODE_BOOK))

if ship_scripts is not None:
    for name in SIBLINGS:
        if not os.path.isdir(os.path.join(cache, name)):
            continue
        away = os.path.join(cache, name + ".hidden-by-ten-stations")
        os.rename(os.path.join(cache, name), away)
        try:
            got = ship_lookup(name)
            line = last_line(got)
            others = dict((other, ship_lookup(other)["exit"]) for other in SIBLINGS if other != name)
            row = {"lookup": got, "one_line_refusal": line, "others_still_resolve": others}
            report["negative_siblings"][name] = row
            if got["exit"] != 3 or not line.startswith("missing station: %s (looked in: " % name):
                report["problems"].append("ship-v2: %s renamed away is not refused as a missing station" % name)
            if any(code != 0 for code in others.values()):
                report["problems"].append("ship-v2: with %s away, another sibling no longer resolves" % name)
        finally:
            os.rename(away, os.path.join(cache, name))
report["ok"] = not report["problems"]
print(json.dumps(report, indent=2))
sys.exit(0 if report["ok"] else 1)
PY
