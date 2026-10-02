#!/bin/sh
# The manual-only probe beside this core (owner pick P5 of the E15 lane contract). precon-v2's script
# (E14 slice 3c, item 3.9) with one line changed: the case below admits handoff-v2, the one back core
# P5 marks manual-only, where the E14 copies admit precon-v2, architect-v2 and inspect-v2. It is not a
# back-frame file (vertical-v2 and ship-v2 carry no manual-only control), so it is not listed in
# references/back-files.txt; it wraps the shared install and verify scripts rather than editing them.
#
# Usage: manual-only.sh claude-code|codex --home DIR [--credential]
#
# 1. `<harness>/install.sh --home DIR` installs the core (and the plugins its case names) into the
#    isolated home, `--credential` passed through on Codex only; then `<harness>/verify-install.sh`.
# 2. A second marketplace in the home, `<home>/probe-marketplace` (`<core>-probes`), holds one entry,
#    a symlink to `_fixtures/manual-only-probe` (recheck-v2's E9 probe, byte for byte), and the harness
#    installs `manual-only-probe@<core>-probes` beside the core.
# 3. The checks, from the INSTALLED copies: the probe's SKILL.md says `disable-model-invocation:
#    true` and its Codex sidecar `agents/openai.yaml` says `allow_implicit_invocation: false` (the E9
#    seam); the core's installed SKILL.md and sidecar say the same (P5); the two prompts the control
#    room's live measurement sends exist for this harness.
# No prompt is sent, no model is called and no session is launched: the live measurement is the
# control room's, through `<harness>/launch.sh` (see `_fixtures/README.md`).
# One JSON document on stdout. Exit 0 every step and check held, 1 otherwise, 2 usage.
set -eu
[ $# -ge 3 ] || { echo "usage: manual-only.sh claude-code|codex --home DIR [--credential]" >&2; exit 2; }
HARNESS="$1"; shift
case "$HARNESS" in claude-code|codex) ;; *) echo "manual-only.sh: harness is claude-code or codex" >&2; exit 2 ;; esac
SETUP_HOME=""; CREDENTIAL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --home) [ $# -ge 2 ] || { echo "manual-only.sh: --home takes a directory" >&2; exit 2; }; SETUP_HOME="$2"; shift 2 ;;
    --credential) CREDENTIAL="--credential"; shift ;;
    *) echo "manual-only.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$SETUP_HOME" ] || { echo "manual-only.sh: name the isolated home with --home" >&2; exit 2; }
[ "$HARNESS" = codex ] || [ -z "$CREDENTIAL" ] || { echo "manual-only.sh: --credential is Codex's" >&2; exit 2; }
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
CORE=$(basename -- "$PLUGIN_ROOT")
case "$CORE" in handoff-v2) ;; *) echo "manual-only.sh: $CORE is not a strictly user-invoked station" >&2; exit 2 ;; esac
export PYTHONDONTWRITEBYTECODE=1
# The interpreter starts with TMPDIR, TEMP and TMP cleared, before install.sh's guard has run, and the body
# puts their values back first (E14 punch list, the outside confirm's F1; the 26 GUARD starts do the same).
exec env -u TMPDIR -u TEMP -u TMP python3 - "$HARNESS" "$SETUP_HOME" "$SCRIPT_DIR" "$CORE" "$CREDENTIAL" \
  "${TMPDIR-}" "${TEMP-}" "${TMP-}" <<'PY'
import json, os, re, subprocess, sys
harness, home, setups, core, credential = sys.argv[1:6]
for key, value in zip(("TMPDIR", "TEMP", "TMP"), sys.argv[6:9]):
    if value:
        os.environ[key] = value
PROBE = "manual-only-probe"
MARKET = core + "-probes"
report = {"harness": harness, "core": core, "home": None, "steps": [], "checks": {}, "problems": []}


def run(argv, env=None):
    proc = subprocess.run(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {"command": " ".join(argv), "exit": proc.returncode,
            "stdout": proc.stdout.decode("utf-8", "replace").strip()[-2000:],
            "stderr": proc.stderr.decode("utf-8", "replace").strip()[-2000:]}


def step(argv, env=None):
    got = run(argv, env)
    report["steps"].append(got)
    if got["exit"] != 0:
        report["problems"].append("step failed: %s (exit %s)" % (got["command"], got["exit"]))
    return got


install = [os.path.join(setups, harness, "install.sh"), "--home", home] + ([credential] if credential else [])
home = os.path.realpath(home)
report["home"] = home
for argv in (["sh"] + install, ["sh", os.path.join(setups, harness, "verify-install.sh"), "--home", home]):
    if step(argv)["exit"] != 0:
        report["ok"] = False
        print(json.dumps(report, indent=2))
        sys.exit(1)

env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
if harness == "claude-code":
    env["CLAUDE_CONFIG_DIR"] = os.path.join(home, "config")
    cache = os.path.join(home, "config", "plugins", "cache")
else:
    env["CODEX_HOME"] = home
    cache = os.path.join(home, "plugins", "cache")
market = os.path.join(home, "probe-marketplace")
os.makedirs(os.path.join(market, ".claude-plugin"), exist_ok=True)
link = os.path.join(market, PROBE)
if os.path.islink(link):
    os.unlink(link)
os.symlink(os.path.join(setups, "_fixtures", PROBE), link)
with open(os.path.join(market, ".claude-plugin", "marketplace.json"), "w") as handle:
    json.dump({"name": MARKET, "owner": {"name": "skills v2 setup"},
               "plugins": [{"name": PROBE, "source": "./" + PROBE}]}, handle)
if harness == "claude-code":
    step(["claude", "plugin", "marketplace", "add", market], env)
    step(["claude", "plugin", "install", "%s@%s" % (PROBE, MARKET), "--json", "-y"], env)
else:
    step(["codex", "plugin", "marketplace", "add", market, "--json"], env)
    step(["codex", "plugin", "add", "%s@%s" % (PROBE, MARKET), "--json"], env)


def one_version(folder):
    versions = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
    return os.path.join(folder, versions[0]) if len(versions) == 1 else None


def frontmatter(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else ""


def controls(root, name):
    skill = os.path.join(root, "skills", name, "SKILL.md")
    sidecar = os.path.join(root, "skills", name, "agents", "openai.yaml")
    row = {"skill_md": skill, "sidecar": sidecar}
    row["disable_model_invocation"] = (os.path.isfile(skill) and re.search(
        r"^disable-model-invocation: true$", frontmatter(skill), re.M) is not None)
    text = open(sidecar, encoding="utf-8").read() if os.path.isfile(sidecar) else ""
    row["allow_implicit_invocation_false"] = re.search(
        r"^policy:\n(?:  .*\n)*?  allow_implicit_invocation: false$", text, re.M) is not None
    return row


probe_root = one_version(os.path.join(cache, MARKET, PROBE))
core_root = one_version(os.path.join(cache, core + "-setup", core))
for label, root, name in (("probe", probe_root, PROBE), ("core", core_root, core)):
    if root is None:
        report["problems"].append("%s: expected one installed version under %s" % (label, cache))
        continue
    row = controls(root, name)
    row["installed"] = root
    report["checks"][label] = row
    if not (row["disable_model_invocation"] and row["allow_implicit_invocation_false"]):
        report["problems"].append("%s: the installed copy does not carry both manual-only controls" % label)
ext = ".txt" if harness == "claude-code" else ".md"
prompts = {kind: os.path.join(setups, harness, "prompts", "manual-only-%s%s" % (kind, ext))
           for kind in ("words", "explicit")}
report["checks"]["prompts"] = {kind: {"path": path, "present": os.path.isfile(path) and os.path.getsize(path) > 0}
                               for kind, path in prompts.items()}
for kind, row in report["checks"]["prompts"].items():
    if not row["present"]:
        report["problems"].append("the %s prompt is missing: %s" % (kind, row["path"]))
report["ok"] = not report["problems"]
print(json.dumps(report, indent=2))
sys.exit(0 if report["ok"] else 1)
PY
