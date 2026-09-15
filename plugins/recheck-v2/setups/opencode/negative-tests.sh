#!/bin/sh
# Negative installation tests for the OpenCode pilot setup (E9 lane contract section 9.2,
# amendment A7b; guide "The harness layer", the silent-failure list).
#
# Usage:  sh negative-tests.sh [--setup DIR] [--keep] [--skip-reinstall]
#   --setup DIR       the installed isolated setup to copy from
#                     (default ~/.local/share/skills-v2-pilot/opencode)
#   --keep            do not delete the throwaway setups (they land under
#                     ${TMPDIR}/recheck-v2-neg)
#   --skip-reinstall  skip the update row, which runs the real install.sh (npm, from the
#                     setup's pinned cache). The row is then reported with behavior `n/a` and
#                     ok false, never as a pass
#
# Each test runs in its own throwaway copy of the isolated setup: the config tree is copied,
# a fresh empty data/cache/state tree is made, and the binary is reused from the real setup by
# path (it is 138 MB and read-only here). Nothing touches the real setup, the live
# ~/.config/opencode, or any repository.
#
# Prints one JSON object per line on stdout: {"test", "expectation", "observed", "behavior",
# "message", "exit_status", "catalog", "ok"}. `behavior` is one of enforced | prevented
# activation | ignored | crashed | check failed | n/a, and it is derived from the check's exit
# status, the harness's own catalog and its diagnostics — never assumed (Astra finding 11: a
# loader that exited 1 was reported as `ignored` seven times). `ok` is false whenever the check
# itself did not produce a real observation, and the script then exits 4 rather than 0.
#
# Diagnostics go to stderr. Exit 0 when every test produced a real observation, 4 when any did
# not, 2 on a usage slip, 3 when the source setup is missing.
set -eu

SETUP="${HOME}/.local/share/skills-v2-pilot/opencode"
KEEP=0
SKIP_REINSTALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --setup) SETUP="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    --skip-reinstall) SKIP_REINSTALL=1; shift ;;
    -h|--help) sed -n '2,31p' "$0"; exit 0 ;;
    *) echo "negative-tests.sh: unknown argument $1" >&2; exit 2 ;;
  esac
done

[ -d "$SETUP/xdg-config/opencode/skill" ] || {
  echo "negative-tests.sh: no installed setup at $SETUP (run install.sh)" >&2; exit 3; }
SETUP=$(cd "$SETUP" && pwd)
OC="$SETUP/npm/node_modules/.bin/opencode"
[ -x "$OC" ] || { echo "negative-tests.sh: no opencode binary at $OC" >&2; exit 3; }

HERE=$(cd "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(cd "$HERE/../.." && pwd)
ROOT="${TMPDIR:-/tmp}/recheck-v2-neg"
rm -rf "$ROOT"; mkdir -p "$ROOT"
NEUTRAL="$ROOT/cwd"; mkdir -p "$NEUTRAL"
FAILED="$ROOT/failed"

# The classifier: one row, derived from the harness's own exit status, catalog and stderr.
EMIT_PY="$ROOT/emit.py"
cat > "$EMIT_PY" <<'PY'
import json, os, sys

case, want, test, expectation, expect_state = sys.argv[1:6]
failed_marker = sys.argv[6]


def read(name, default=""):
    try:
        with open(os.path.join(case, name), encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (IOError, OSError):
        return default


status = read("skills.rc").strip() or "missing"
err = " ".join(read("skills.err").split())[:200]
raw = read("skills.json")
catalog = None
parse_error = None
try:
    skills = json.loads(raw)
    if not isinstance(skills, list):
        raise ValueError("the listing is not a list")
    catalog = sorted(s.get("name") for s in skills if s.get("name"))
except Exception as exc:          # noqa: BLE001 - the failure itself is the observation
    skills = None
    parse_error = str(exc)

entry = None
if skills is not None:
    for skill in skills:
        if skill.get("name") == want:
            entry = skill
            break

ok = True
if status != "0" or skills is None:
    behavior = "check failed"
    ok = False
    observed = ("the harness's own listing did not produce a catalog: `opencode debug skill` "
                "exited %s%s" % (status, ("; " + parse_error) if parse_error else ""))
elif entry is not None:
    behavior = "ignored"
    observed = ("listed name=%s location=%s description=%s"
                % (entry.get("name"), entry.get("location"),
                   (entry.get("description") or "")[:60]))
else:
    behavior = "prevented activation"
    observed = "absent from the catalog"

if ok and expect_state in ("present", "absent"):
    seen = "present" if entry is not None else "absent"
    if seen != expect_state:
        ok = False
        observed += " (expected the skill %s, found it %s)" % (expect_state, seen)

print(json.dumps({"test": test, "expectation": expectation, "observed": observed,
                  "behavior": behavior, "message": err or parse_error or "",
                  "exit_status": status, "catalog": catalog, "ok": ok}))
if not ok:
    open(failed_marker, "a").write(test + "\n")
PY

# A row whose observation is not a loader listing (the core row, the update row) emits here.
PLAIN_PY="$ROOT/plain.py"
cat > "$PLAIN_PY" <<'PY'
import json, sys
test, expectation, observed, behavior, message, status, ok = sys.argv[1:8]
failed_marker = sys.argv[8]
ok = ok == "1"
print(json.dumps({"test": test, "expectation": expectation, "observed": observed,
                  "behavior": behavior, "message": message, "exit_status": status,
                  "catalog": None, "ok": ok}))
if not ok:
    open(failed_marker, "a").write(test + "\n")
PY

make_case () {   # make_case <name> -> echoes the case dir
  name="$1"
  d="$ROOT/$name"
  mkdir -p "$d/xdg-data" "$d/xdg-cache" "$d/xdg-state"
  cp -R "$SETUP/xdg-config" "$d/xdg-config"
  rm -rf "$d/xdg-config/opencode/node_modules" "$d/xdg-config/opencode/package-lock.json"
  echo "$d"
}

run_list () {   # run_list <case dir>: leaves skills.json, skills.err and skills.rc in it
  d="$1"
  set +e
  ( cd "$NEUTRAL" && env XDG_CONFIG_HOME="$d/xdg-config" XDG_DATA_HOME="$d/xdg-data" \
      XDG_CACHE_HOME="$d/xdg-cache" XDG_STATE_HOME="$d/xdg-state" \
      OPENCODE_DISABLE_EXTERNAL_SKILLS=1 "$OC" debug skill > "$d/skills.json" 2> "$d/skills.err" )
  echo $? > "$d/skills.rc"
  set -e
}

emit () {   # emit <case dir> <skill> <test> <expectation> <expected state>
  /usr/bin/python3 "$EMIT_PY" "$1" "$2" "$3" "$4" "$5" "$FAILED"
}

# 1. a malformed agents/openai.yaml (guide silent failure 2)
D=$(make_case malformed-sidecar)
printf 'interface:\n  display_name: "Manual-only probe\npolicy:\n  allow_implicit_invocation: [\n' \
  > "$D/xdg-config/opencode/skill/manual-only-probe/agents/openai.yaml"
run_list "$D"
emit "$D" manual-only-probe "malformed agents/openai.yaml" \
  "OpenCode never reads the Codex sidecar, so the skill stays loadable and the policy was never in force here" \
  present

# 2. a missing agents/openai.yaml on the manual-only probe
D=$(make_case missing-sidecar)
rm -rf "$D/xdg-config/opencode/skill/manual-only-probe/agents"
run_list "$D"
emit "$D" manual-only-probe "missing agents/openai.yaml" \
  "unchanged: the sidecar is not an OpenCode surface" present

# 3. SKILL.md with the name field removed
D=$(make_case no-name)
/usr/bin/python3 - "$D/xdg-config/opencode/skill/delivery-probe/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
text = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(
    "\n".join(l for l in text.split("\n") if not l.startswith("name: ")))
PY
run_list "$D"
emit "$D" delivery-probe "SKILL.md with no name field" \
  "the loader either refuses the skill or falls back to the folder name" any

# 4. a broken frontmatter delimiter (guide silent failure 4)
D=$(make_case broken-delimiter)
/usr/bin/python3 - "$D/xdg-config/opencode/skill/delivery-probe/SKILL.md" <<'PY'
import sys
p = sys.argv[1]
text = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write("a stray line before the delimiter\n" + text.replace("---\n", "--\n", 1))
PY
run_list "$D"
emit "$D" delivery-probe "broken frontmatter delimiter" \
  "the loader skips the skill or loads it with no description" any

# 5. a duplicate skill name: the probe installed under two surfaces at once
D=$(make_case duplicate-name)
mkdir -p "$D/xdg-config/opencode/skills"
cp -R "$SETUP/xdg-config/opencode/skill/delivery-probe" "$D/xdg-config/opencode/skills/delivery-probe"
run_list "$D"
emit "$D" delivery-probe "duplicate skill name on two surfaces" \
  "the loader resolves the duplicate one way or lists it twice; which copy wins is recorded" any

# 6. a missing resource: references/verifier.md deleted from the installed copy
D=$(make_case missing-resource)
rm -f "$D/xdg-config/opencode/skill/recheck-v2/references/verifier.md"
run_list "$D"
emit "$D" recheck-v2 "references/verifier.md deleted: what the harness does" \
  "the harness itself still lists the skill and would still deliver it; nothing at this layer notices" present
WS="$D/ws"; mkdir -p "$WS"; ( cd "$WS" && git init -q . && echo x > README.md \
  && git -c user.email=p@p -c user.name=p add -A && git -c user.email=p@p -c user.name=p commit -qm base ) >/dev/null 2>&1
IN="$D/in.json"
/usr/bin/python3 - "$IN" "$WS" "$D/run" <<'PY'
import json, sys
json.dump({"protocol_version": 1,
           "invocation": {"mode": "headless", "caller": "neg-test",
                          "run_id": "neg-missing-reference", "run_dir": sys.argv[3],
                          "harness": {"name": "opencode", "version": "1.18.31",
                                      "entry": "opencode skill directory", "sandbox": "test"},
                          "model": {"id": "qwen/qwen3.8-flash", "floor_class": "opus",
                                    "floor_met": True}},
           "workspace": sys.argv[2],
           "target": {"build_doc": "docs/plan.md", "slice": "A"}},
          open(sys.argv[1], "w"), indent=2)
PY
set +e
CORE=$(cd "$PLUGIN_ROOT" && uv run "$D/xdg-config/opencode/skill/recheck-v2/scripts/recheck.py" start "$IN" 2>"$D/core.err")
CORE_RC=$?
set -e
/usr/bin/python3 - "$CORE" "$D/core.err" "$CORE_RC" "$PLAIN_PY" "$FAILED" <<'PY'
import json, os, subprocess, sys
raw, err_path, rc, plain, failed = sys.argv[1:6]
reason = None
status = None
ok = False
try:
    d = json.loads(raw)
    status = d.get("status")
    reason = d.get("stop_reason")
    if not reason and d.get("result") and os.path.isfile(d["result"]):
        try:
            reason = json.load(open(d["result"])).get("stop_reason")
        except Exception:
            reason = None
except Exception:
    d = None
err = open(err_path, encoding="utf-8", errors="replace").read()
if not reason:
    for line in err.split("\n"):
        if "reference unavailable" in line:
            reason = line.strip()
            break
# The row claims enforcement only when the core actually stopped on the missing reference.
if d is not None and status == "stopped" and reason and "reference unavailable" in str(reason):
    behavior, ok = "enforced", True
    observed = "core: %s: %s" % (status, reason)
elif d is None:
    behavior, observed = "check failed", "the core printed no JSON on stdout (exit %s)" % rc
else:
    behavior = "check failed"
    observed = "core: %s: %s (the core did not stop on the missing reference)" % (status, reason)
subprocess.call([sys.executable, plain,
                 "references/verifier.md deleted: what the core does",
                 "the core stops as stopped with reference unavailable",
                 observed, behavior, " ".join(err.split())[:200], str(rc),
                 "1" if ok else "0", failed])
PY

# 7a. a symlinked SKILL.md file
D=$(make_case symlink-file)
rm -f "$D/xdg-config/opencode/skill/delivery-probe/SKILL.md"
ln -s "$SETUP/xdg-config/opencode/skill/delivery-probe/SKILL.md" "$D/xdg-config/opencode/skill/delivery-probe/SKILL.md"
run_list "$D"
emit "$D" delivery-probe "symlinked SKILL.md file" \
  "a loader may skip a symlinked SKILL.md (Codex does); OpenCode's behaviour is measured here" any

# 7b. a symlinked skill directory
D=$(make_case symlink-dir)
rm -rf "$D/xdg-config/opencode/skill/delivery-probe"
ln -s "$SETUP/xdg-config/opencode/skill/delivery-probe" "$D/xdg-config/opencode/skill/delivery-probe"
run_list "$D"
emit "$D" delivery-probe "symlinked skill directory" "as above, for the whole folder" any

# 8. an update over an edited install: the REAL installer runs, then the package is verified.
# Astra finding 11: the old row performed its own remove/copy and reported what install.sh
# supposedly proved. This one edits the installed copy, runs install.sh against the throwaway
# setup, and then runs verify-install.sh against it.
if [ "$SKIP_REINSTALL" -eq 1 ]; then
  /usr/bin/python3 "$PLAIN_PY" "update over an edited install: install.sh then verify-install.sh" \
    "the installer replaces the edited copy and the package verifies clean" \
    "not run (--skip-reinstall)" "n/a" "" "n/a" "0" "$FAILED"
else
  D=$(make_case update-over-edit)
  EDITED="$D/xdg-config/opencode/skill/recheck-v2/SKILL.md"
  printf '\n<!-- a local edit the update must replace -->\n' >> "$EDITED"
  rm -rf "$D/xdg-config/opencode/skill/recheck-v2/references"
  ln -s "$PLUGIN_ROOT/skills/recheck-v2/references" "$D/xdg-config/opencode/skill/recheck-v2/references"
  BEFORE="edited SKILL.md + references/ replaced by a symlink"
  set +e
  sh "$HERE/install.sh" --setup "$D" --npm-cache "$SETUP/npm-cache" > "$D/install.out" 2> "$D/install.err"
  INSTALL_RC=$?
  sh "$HERE/verify-install.sh" --setup "$D" > "$D/verify.json" 2> "$D/verify.err"
  VERIFY_RC=$?
  set -e
  /usr/bin/python3 - "$D" "$BEFORE" "$INSTALL_RC" "$VERIFY_RC" "$PLAIN_PY" "$FAILED" <<'PY'
import json, subprocess, sys
case, before, install_rc, verify_rc, plain, failed = sys.argv[1:7]
try:
    verify = json.load(open(case + "/verify.json"))
except Exception as exc:          # noqa: BLE001
    verify = {"ok": False, "findings": ["verify-install.sh printed no JSON: %s" % exc]}
ok = install_rc == "0" and verify_rc == "0" and verify.get("ok") is True
observed = ("before=%s | install.sh exit %s | verify-install.sh exit %s, ok=%s, diff_empty=%s, "
            "symlinks_in_package=%s, findings=%s"
            % (before, install_rc, verify_rc, verify.get("ok"), verify.get("diff_empty"),
               verify.get("symlinks_in_package"), verify.get("findings")))
err = open(case + "/install.err", encoding="utf-8", errors="replace").read()
subprocess.call([sys.executable, plain,
                 "update over an edited install: install.sh then verify-install.sh",
                 "the installer replaces the edited copy and the symlink, and the package verifies clean",
                 observed, "enforced" if ok else "check failed",
                 " ".join(err.split())[:200], install_rc, "1" if ok else "0", failed])
PY
fi

if [ -f "$FAILED" ]; then
  echo "negative-tests.sh: $(wc -l < "$FAILED" | tr -d ' ') row(s) did not produce a real observation:" >&2
  sed 's/^/  /' "$FAILED" >&2
  [ "$KEEP" -eq 1 ] || rm -rf "$ROOT"
  exit 4
fi
[ "$KEEP" -eq 1 ] || rm -rf "$ROOT"
