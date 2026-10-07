#!/bin/sh
# The trace proof (the E15 lane contract, ruling E15-7 and section 11; the plan's done-when "a trace demonstrates
# that no v1 back-half station is called indirectly"). No model and no session: installs, CLI calls and the
# end-to-end replay's recorded answers only.
#
# Usage: trace-proof.sh claude-code|codex <fresh isolated home> [--control read|run]
#
# 1. Six tripwire copies (`tripwire.py`, beside this script): the v1 build, signoff, recheck, vertical, handoff and
#    ship plugins of this checkout, each copied whole with its manifest kept, its SKILL.md frontmatter kept and every
#    other byte replaced by a notice, and a v1 entry script added (`skills/<name>/scripts/<name>.py`, the v2 layout's
#    driver place) that leaves a marker and fails when anything runs it.
# 2. ONE marketplace inside the home, entries symlinks to this checkout's ten v2 stations, records and readers, and to
#    the six tripwire copies; all nineteen installed into the harness's isolated home (CLAUDE_CONFIG_DIR=<home>/config,
#    or CODEX_HOME=<home>), every v1 plugin beside its v2. Each installed v1 copy must hold its tripwire entry.
# 3. The audit hook (`tripwire.py`'s `sitecustomize.py`) first on PYTHONPATH, watching the installed v1 folders and
#    the tripwire copies: any hooked Python process that opens, lists or launches a path under them leaves a marker.
#    Its reach, as measured (tripwire.py, THE REACH): a child started isolated (`-I`: ship-v2's identity read of each
#    station, vertical-v2's `readers.py --version`) or by another runtime is not hooked, so a read inside it is not
#    seen; a run of any v1 entry is still caught by the entry's own marker, and a launch of a v1 path from a hooked
#    parent by its `subprocess.Popen` event.
# 4. The end-to-end replay (`../evals/replay/replay.py`) with ship-v2, handoff-v2, vertical-v2, readers and records
#    taken from the INSTALLED copies (`--root`), so build-v2, signoff-v2 and recheck-v2 are the ones ship-v2's own
#    lookup finds installed: a full ship loop on both paths (clean; findings, fix, recheck), handoff-v2's photograph,
#    vertical-v2's gate, packets and summons. Its trace lines are written to `<home>/trace.json`.
# 5. `--control read` then opens one installed v1 file in a hooked Python process; `--control run` runs one installed
#    v1 entry isolated (`-I`, where no hook loads): each must leave a marker, and the proof must then report FAIL. A
#    control run that reports PASS is a broken tripwire.
# A pass: the replay holds; every trace line of ship-v2 and vertical-v2 names a v2 identity (build-v2, signoff-v2,
# recheck-v2; readers for vertical-v2's summons), interface 1, route 3b, its root the installed copy of that name and
# under no v1 folder; the hook armed in every station command the replay ran (each replay command matched to an armed
# record of its own by its argv, `tripwire.unmatched`, never a comparison of totals); the installed
# copies are unchanged by the replay; and no marker. The guard and the temp rule are the setups' (as ten-stations.sh).
# One JSON document on stdout. Exit 0 when every expectation held (PASS), 1 otherwise (FAIL), 2 usage.
set -eu
[ $# -eq 2 ] || [ $# -eq 4 ] || { echo "usage: trace-proof.sh claude-code|codex <fresh isolated home> [--control read|run]" >&2; exit 2; }
HARNESS="$1"; SETUP_HOME="$2"; CONTROL=""
case "$HARNESS" in claude-code|codex) ;; *) echo "trace-proof.sh: harness is claude-code or codex" >&2; exit 2 ;; esac
if [ $# -eq 4 ]; then
  [ "$3" = "--control" ] || { echo "trace-proof.sh: unknown argument: $3" >&2; exit 2; }
  case "$4" in read|run) CONTROL="$4" ;; *) echo "trace-proof.sh: --control is read or run" >&2; exit 2 ;; esac
fi
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGINS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
[ ! -e "$SETUP_HOME" ] || [ -z "$(ls -A "$SETUP_HOME" 2>/dev/null)" ] || { echo "trace-proof.sh: $SETUP_HOME is not empty" >&2; exit 2; }
# The home guard, before anything is created (inspect-v2's seven-stations.sh, byte for byte but its name): the home,
# as given and resolved, may not be or sit under ~/.claude, ~/.codex or ~/.local/share/skills-v2-*, whichever harness
# this is. TMPDIR, TEMP and TMP are held to the same rule.
SETUP_HOME=$(env -u TMPDIR -u TEMP -u TMP python3 - "$SETUP_HOME" "$HOME" "trace-proof.sh" "${TMPDIR-}" "${TEMP-}" "${TMP-}" <<'GUARD'
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
exec env -u TMPDIR -u TEMP -u TMP python3 - "$HARNESS" "$SETUP_HOME" "$PLUGINS_DIR" "$SCRIPT_DIR" "$CONTROL" \
  "${TMPDIR-}" "${TEMP-}" "${TMP-}" <<'PY'
import json, os, subprocess, sys
harness, home, plugins_dir, setups, control = sys.argv[1:6]
for key, value in zip(("TMPDIR", "TEMP", "TMP"), sys.argv[6:9]):
    if value:
        os.environ[key] = value
sys.path.insert(0, setups)
sys.dont_write_bytecode = True
import tripwire  # noqa: E402

MARKET = "trace-proof"
V2 = ["recheck-v2", "build-v2", "signoff-v2", "precon-v2", "architect-v2", "blueprint-v2", "inspect-v2",
      "vertical-v2", "handoff-v2", "ship-v2", "records", "readers"]
# the six v1 plugins a v2 back core could reach, assembled so no file of this core names a v1 folder
V1 = ["bu" + "ild", "sign" + "off", "re" + "check", "verti" + "cal", "hand" + "off", "sh" + "ip"]
TRACED = {"ship": ("build-v2", "signoff-v2", "recheck-v2"), "vertical": ("readers",)}
names = V2 + V1
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
env.pop("RECORDS_ROOT", None)
if harness == "claude-code":
    env["CLAUDE_CONFIG_DIR"] = os.path.join(home, "config")
    cache = os.path.join(home, "config", "plugins", "cache", MARKET)
    os.makedirs(os.path.join(home, "config"))
else:
    env["CODEX_HOME"] = home
    cache = os.path.join(home, "plugins", "cache", MARKET)
markers = os.path.join(home, "markers")
tripwires = os.path.join(home, "tripwires")
hook = os.path.join(home, "hook")
report = {"harness": harness, "home": home, "marketplace": MARKET, "control": control or None, "steps": [],
          "problems": []}


def run(argv, extra=None, cwd="/"):
    proc = subprocess.run(argv, env=dict(env, **(extra or {})), cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    return {"command": " ".join(argv), "exit": proc.returncode,
            "stdout": proc.stdout.decode("utf-8", "replace").strip(),
            "stderr": proc.stderr.decode("utf-8", "replace").strip()}


def tree_state(root):
    out = {}
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in files + [d for d in dirs if os.path.islink(os.path.join(base, d))]:
            full = os.path.join(base, name)
            st = os.lstat(full)
            out[os.path.relpath(full, root)] = (st.st_size, st.st_mtime_ns, st.st_mode)
    return out


def under(path, root):
    path, root = os.path.realpath(path).casefold(), os.path.realpath(root).casefold().rstrip(os.sep)
    return path == root or path.startswith(root + os.sep)


for name in V1:
    tripwire.build_copy(os.path.join(plugins_dir, name), os.path.join(tripwires, name), markers)
tripwire.write_hook(hook)
market = os.path.join(home, "marketplace")
os.makedirs(os.path.join(market, ".claude-plugin"))
for name in names:
    os.symlink(os.path.join(tripwires if name in V1 else plugins_dir, name), os.path.join(market, name))
with open(os.path.join(market, ".claude-plugin", "marketplace.json"), "w") as handle:
    json.dump({"name": MARKET, "owner": {"name": "E15 slice 3"},
               "plugins": [{"name": n, "source": "./" + n} for n in names]}, handle)
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
installed = dict((n, sorted(os.listdir(os.path.join(cache, n))) if os.path.isdir(os.path.join(cache, n)) else [])
                 for n in names)
report["installed"] = installed
roots = dict((n, os.path.join(cache, n, v[0])) for n, v in installed.items() if len(v) == 1)
for name in names:
    if name not in roots:
        report["problems"].append("%s: expected one installed version, found %s" % (name, installed[name]))
report["v1_beside_v2"] = {}
for name in V1:
    root = roots.get(name)
    entry = os.path.join(root, "skills", name, "scripts", name + ".py") if root else None
    held = bool(entry) and os.path.isfile(entry) and os.path.isfile(os.path.join(root, ".claude-plugin",
                                                                                  "plugin.json"))
    report["v1_beside_v2"][name] = {"installed": root, "tripwire_entry": entry if held else None,
                                    "v2_beside": roots.get(name + "-v2")}
    if not held:
        report["problems"].append("%s: the installed v1 copy holds no tripwire entry" % name)
watched = [os.path.join(cache, name) for name in V1] + [tripwires]
report["watched"] = watched
report["markers_before"] = len(tripwire.markers(markers))
hooked = {"PYTHONPATH": hook, "TRIPWIRE_ROOTS": os.pathsep.join(watched), "TRIPWIRE_MARKERS": markers}

missing = [n for n in ("ship-v2", "handoff-v2", "vertical-v2", "readers", "records") if n not in roots]
replay = None
if not missing and not report["problems"]:
    before = tree_state(cache)
    trace_out = os.path.join(home, "trace.json")
    argv = ["uv", "run", "--offline", "--quiet", "--python", "/usr/bin/python3", "--with", "jsonschema==4.25.1",
            "python", os.path.join(plugins_dir, "ship-v2", "evals", "replay", "replay.py"),
            "--keep", os.path.join(home, "replay"), "--trace-out", trace_out]
    for name in ("ship-v2", "handoff-v2", "vertical-v2", "readers", "records"):
        argv += ["--root", "%s=%s" % (name, roots[name])]
    replay = run(argv, hooked)
    try:
        summary = json.loads(replay["stdout"])
    except ValueError:
        summary = None
    report["replay"] = {"exit": replay["exit"], "ok": (summary or {}).get("ok"),
                        "problems": (summary or {}).get("problems"), "stderr": replay["stderr"][-1500:],
                        "stations_run_by": (summary or {}).get("stations_run_by"),
                        "loop": dict((k, (v.get("assertions") or {}).get("loop"))
                                     for k, v in ((summary or {}).get("paths") or {}).items())}
    if replay["exit"] != 0 or not summary or summary.get("ok") is not True:
        report["problems"].append("the replay did not hold over the installed copies (exit %s)" % replay["exit"])
    report["installed_unchanged"] = tree_state(cache) == before
    if not report["installed_unchanged"]:
        report["problems"].append("the replay changed the installed copies")
    # the trace: every line a v2 identity at its installed copy, route 3b, interface 1, under no v1 folder
    lines = {}
    try:
        with open(trace_out, encoding="utf-8") as handle:
            traces = json.load(handle)
    except (OSError, ValueError):
        traces = {}
        report["problems"].append("the replay wrote no trace file")
    seen, bad = [], []
    for path, kinds in sorted(traces.items()):
        for which, rows in sorted(kinds.items()):
            for line in rows:
                identity = line.get("identity") or {}
                name, root = identity.get("name"), identity.get("root") or ""
                seen.append("%s %s %s %s %s (interface %s, route %s)" % (path, which, line.get("kind"),
                                                                         line.get("status"), name,
                                                                         identity.get("interface_version"),
                                                                         line.get("route")))
                why = []
                if line.get("kind") == "refused":
                    why.append("a refused line")
                if name not in TRACED.get(which, ()):
                    why.append("names %r" % name)
                if identity.get("interface_version") != 1:
                    why.append("interface %r" % identity.get("interface_version"))
                if line.get("route") != "3b":
                    why.append("route %r" % line.get("route"))
                if name not in roots or not under(root, roots[name]):
                    why.append("root %s is not the installed copy of %s" % (root, name))
                if any(under(root, w) for w in watched):
                    why.append("root %s sits under a v1 tripwire" % root)
                if why:
                    bad.append({"line": "%s %s seq %s" % (path, which, line.get("seq")), "why": why})
    report["trace"] = {"lines": len(seen), "names": sorted(set(s.split(" ")[4] for s in seen)), "seen": seen,
                       "bad": bad}
    if not seen:
        report["problems"].append("the trace holds no line")
    if bad:
        report["problems"].append("%d trace line(s) do not name the installed v2 identity" % len(bad))
    # the hook armed in every station command the replay ran: each command matched to an armed record of its own
    commands = []
    for kind, path in sorted(((summary or {}).get("paths") or {}).items()):
        commands += [dict(c, path=kind) for c in path.get("commands") or [] if c.get("station") != "executor"]
    armed = tripwire.armed(markers)
    armed_under = sum(1 for a in armed if (a.get("argv") or [""])[0] and under((a.get("argv") or [""])[0], cache))
    missed = tripwire.unmatched(commands, armed, cache)
    report["hook"] = {"armed_processes": len(armed), "armed_in_installed_station_scripts": armed_under,
                      "station_commands_in_the_replay": len(commands),
                      "commands_matched_to_an_armed_record": len(commands) - len(missed),
                      "unmatched": ["%s %s %s %s" % (c.get("path"), c.get("station"), c.get("command"), c.get("argv"))
                                    for c in missed][:20],
                      "not_hooked_by_design": "children started isolated (-I) or by another runtime; a v1 entry run "
                                              "there is still caught by its own marker"}
    if not commands or missed:
        report["problems"].append("%d of the replay's %d station commands have no armed record of their own (the hook "
                                  "did not load in them)" % (len(missed), len(commands)))
else:
    report["problems"].append("the replay was not run: %s" % (", ".join(missing) or "the install did not hold"))

if control == "read":
    target = os.path.join(roots.get(V1[0], ""), "skills", V1[0], "SKILL.md")
    report["control_step"] = run(["/usr/bin/python3", "-c", "open(%r).read()" % target], hooked)
elif control == "run":
    target = os.path.join(roots.get(V1[0], ""), "skills", V1[0], "scripts", V1[0] + ".py")
    report["control_step"] = run(["/usr/bin/python3", "-I", "-B", target, "skill-identity"])
marks = tripwire.markers(markers)
report["markers"] = marks
report["tripwire"] = tripwire.verdict(marks)
if marks:
    report["problems"].append(report["tripwire"]["why"])
report["ok"] = not report["problems"]
report["verdict"] = "PASS" if report["ok"] else "FAIL"
print(json.dumps(report, indent=2))
sys.exit(0 if report["ok"] else 1)
PY
