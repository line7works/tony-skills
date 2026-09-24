#!/usr/bin/env python3
"""The negative installation tests of this core, for either harness (E13 slice 3, 3.3).

Adapted from the recheck-v2 pilot's `setups/claude-code/negative-tests.sh` and
`setups/codex/negative-tests.sh` + `prepare-negative.py`. One file for both harnesses; each
harness's `negative-tests.sh` calls it. Byte-identical in build-v2 and signoff-v2.

    negative-cases.py --harness claude-code|codex --out DIR [--live]

The pilot's nine cases, each in its own throwaway copy under DIR: its own mutated copy of THIS
core's plugin folder, its own marketplace (a symlink to that copy, the way install.sh builds
one) and its own harness home (CLAUDE_CONFIG_DIR or CODEX_HOME). The pilot mutated two probe
plugins; here the core itself is mutated, since its own package is what the setup ships.

  malformed-sidecar   agents/openai.yaml replaced by YAML of the wrong shape
  missing-sidecar     agents/openai.yaml deleted
  missing-name        the SKILL.md `name:` line removed
  broken-delimiter    a line put before the SKILL.md opening `---`
  duplicate-name      a second plugin carrying a skill of the same name
  missing-resource    references/input.schema.json deleted; the installed core's own
                      `check-input` is then run on an input file and its refusal recorded
  symlink-file        SKILL.md replaced by a symlink to a file outside the plugin
  symlink-directory   skills/<core> replaced by a symlink to a folder outside the plugin
  update-copy-symlink installs at 0.1.1 (a copy), 0.1.2 (SKILL.md a symlink), 0.1.3 (a copy)

FREE HALF, always run: the harness's own plugin commands (validate where it has one, marketplace
add, install), every child's exit and first output line, and what the installer wrote into the
cache (is SKILL.md there, is it a symlink, does the copy equal the mutated source). No session is
started and no model is called. LIVE HALF, only with --live: one headless session per case in
the case's own home, through this setup's launch.sh, reading the catalog the session built; not
run in E13 slice 3. One JSON line per case on stdout. Exit 0 when every case ran (whatever it
observed), 2 usage, 1 a case could not be prepared.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
CORE = os.path.basename(PLUGIN)
SCRIPT = {"build-v2": "build.py", "signoff-v2": "signoff.py"}[CORE]
CASES = ["malformed-sidecar", "missing-sidecar", "missing-name", "broken-delimiter",
         "duplicate-name", "missing-resource", "symlink-file", "symlink-directory",
         "update-copy-symlink"]
MARKET = "negative-probe"


def run(argv, env, cwd="/"):
    try:
        proc = subprocess.run(argv, env=env, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"argv": argv, "exit": None, "error": str(exc)}
    out = proc.stdout.decode("utf-8", "replace").strip()
    err = proc.stderr.decode("utf-8", "replace").strip()
    return {"argv": argv, "exit": proc.returncode, "stdout_first": out.splitlines()[0] if out else "",
            "stdout": out[:3000], "stderr_tail": err[-400:]}


def copy_core(dest):
    shutil.copytree(PLUGIN, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def set_version(plugin_dir, version):
    path = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    with open(path) as handle:
        manifest = json.load(handle)
    manifest["version"] = version
    with open(path, "w") as handle:
        json.dump(manifest, handle, indent=2)


def mutate(case, plugin_dir, trial):
    skill = os.path.join(plugin_dir, "skills", CORE)
    body = os.path.join(skill, "SKILL.md")
    side = os.path.join(skill, "agents", "openai.yaml")
    if case == "malformed-sidecar":
        with open(side, "w") as handle:
            handle.write("interface:\n  display_name: [not, a, string]\npolicy: nonsense\n")
    elif case == "missing-sidecar":
        os.remove(side)
    elif case == "missing-name":
        lines = open(body).read().splitlines(True)
        with open(body, "w") as handle:
            handle.writelines(l for l in lines if not l.startswith("name:"))
    elif case == "broken-delimiter":
        text = open(body).read()
        with open(body, "w") as handle:
            handle.write("broken\n" + text)
    elif case == "missing-resource":
        os.remove(os.path.join(skill, "references", "input.schema.json"))
    elif case == "symlink-file":
        saved = os.path.join(trial, "saved-SKILL.md")
        shutil.copyfile(body, saved)
        os.remove(body)
        os.symlink(saved, body)
    elif case == "symlink-directory":
        saved = os.path.join(trial, "saved-skill")
        shutil.move(skill, saved)
        os.symlink(saved, skill, target_is_directory=True)


def marketplace(trial, entries):
    market = os.path.join(trial, "market")
    os.makedirs(os.path.join(market, ".claude-plugin"), exist_ok=True)
    rows = []
    for name, source in entries:
        link = os.path.join(market, name)
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(source, link)
        rows.append({"name": name, "source": "./" + name})
    with open(os.path.join(market, ".claude-plugin", "marketplace.json"), "w") as handle:
        json.dump({"name": MARKET, "owner": {"name": "negative tests"}, "plugins": rows}, handle)
    return market


def harness_env(harness, home):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("RECORDS_ROOT", None)
    if harness == "claude-code":
        env["CLAUDE_CONFIG_DIR"] = os.path.join(home, "config")
    else:
        env["CODEX_HOME"] = home
    os.makedirs(os.path.join(home, "config") if harness == "claude-code" else home, exist_ok=True)
    return env


def cache_root(harness, home):
    return (os.path.join(home, "config", "plugins", "cache", MARKET) if harness == "claude-code"
            else os.path.join(home, "plugins", "cache", MARKET))


def add_market(harness, env, market):
    if harness == "claude-code":
        return run(["claude", "plugin", "marketplace", "add", market], env)
    return run(["codex", "plugin", "marketplace", "add", market, "--json"], env)


def install(harness, env, name):
    if harness == "claude-code":
        return run(["claude", "plugin", "install", "%s@%s" % (name, MARKET), "--json", "-y"], env)
    return run(["codex", "plugin", "add", "%s@%s" % (name, MARKET), "--json"], env)


def validate(harness, env, plugin_dir):
    if harness == "claude-code":
        step = run(["claude", "plugin", "validate", plugin_dir, "--json"], env)
        try:
            report = json.loads(step.get("stdout") or "")
        except ValueError:
            return step
        said = []
        for part in [report.get("manifest") or {}] + list(report.get("contents") or []):
            for kind in ("errors", "warnings"):
                for item in part.get(kind) or []:
                    said.append("%s %s: %s" % (kind[:-1], item.get("path"), item.get("message")))
        step["success"] = report.get("success")
        step["said"] = said
        step["skills_seen"] = [c.get("file") for c in report.get("contents") or []]
        step.pop("stdout", None)
        return step
    return {"argv": [], "exit": None, "note": "Codex has no plugin validate command"}


def observe(harness, home, name, source_dir):
    root = os.path.join(cache_root(harness, home), name)
    copies = []
    for version in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        installed = os.path.join(root, version)
        skill_dir = os.path.join(installed, "skills", CORE)
        body = os.path.join(skill_dir, "SKILL.md")
        diff = subprocess.run(["diff", "-r", "-x", "__pycache__", source_dir, installed],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        copies.append({"version": version, "path": installed,
                       "skill_dir_present": os.path.lexists(skill_dir),
                       "skill_dir_is_symlink": os.path.islink(skill_dir),
                       "skill_md_present": os.path.lexists(body),
                       "skill_md_is_symlink": os.path.islink(body),
                       "sidecar_present": os.path.isfile(os.path.join(skill_dir, "agents",
                                                                      "openai.yaml")),
                       "diff_exit_against_mutated_source": diff.returncode,
                       "diff_head": diff.stdout.decode("utf-8", "replace").splitlines()[:4]})
    return copies


# Measured in E13 slice 3 (setups/claude-code/RESULTS.md, "Delivery probe"): Claude Code 2.1.280
# loads a plugin from a DIRECTORY marketplace at its source path (the init event's plugins[].path
# and the delivered base-directory line both name <home>/marketplace/<core>), not from the cache
# copy. So on Claude Code what the installer dropped from the cache says nothing about what a
# session loads; on Codex the catalog names the cache copy, so a dropped skill is not offered.
CACHE_IS_WHAT_LOADS = {"claude-code": False, "codex": True}


def classify(harness, installs, copies):
    if any(step.get("exit") not in (0,) for step in installs):
        return "prevented install"
    if not copies:
        return "prevented install (nothing in the cache)"
    last = copies[-1]
    if not last["skill_md_present"] or not last["skill_dir_present"]:
        if CACHE_IS_WHAT_LOADS[harness]:
            return "prevented activation at install (the installer dropped the skill silently)"
        return ("the installer dropped the skill from the cache silently, but a session loads "
                "this marketplace's plugin from its source path: activation is the live half's "
                "question")
    return "installed as mutated (activation is the live half's question)"


def one_case(harness, case, out, live):
    trial = os.path.join(out, case)
    os.makedirs(trial)
    home = os.path.join(trial, "home")
    env = harness_env(harness, home)
    src = copy_core(os.path.join(trial, "src", CORE))
    row = {"test": case, "harness": harness, "core": CORE, "half": "free", "trial": trial}
    steps = []
    if case == "update-copy-symlink":
        market = marketplace(trial, [(CORE, src)])
        steps.append(add_market(harness, env, market))
        stages = []
        body = os.path.join(src, "skills", CORE, "SKILL.md")
        for stage, version in (("copy", "0.1.1"), ("symlink", "0.1.2"), ("copy-again", "0.1.3")):
            if stage == "symlink":
                saved = os.path.join(trial, "saved-SKILL.md")
                shutil.copyfile(body, saved)
                os.remove(body)
                os.symlink(saved, body)
            elif stage == "copy-again":
                data = open(body, "rb").read()
                os.remove(body)
                with open(body, "wb") as handle:
                    handle.write(data)
            set_version(src, version)
            if harness == "claude-code":
                steps.append(run(["claude", "plugin", "marketplace", "update", MARKET], env))
                steps.append(run(["claude", "plugin", "update", "%s@%s" % (CORE, MARKET)], env))
            step = install(harness, env, CORE)
            steps.append(step)
            stages.append({"stage": stage, "version": version, "install_exit": step.get("exit"),
                           "cache": observe(harness, home, CORE, src)})
        row["stages"] = stages
        symlinked = [c for s in stages for c in s["cache"] if c["skill_md_is_symlink"]]
        versions = [{c["version"] for c in s["cache"]} for s in stages]
        refreshed = all(s["version"] in v for s, v in zip(stages, versions))
        if symlinked:
            row["classification"] = "not enforced: a symlink reached the cache"
        elif not all(s["install_exit"] == 0 for s in stages):
            row["classification"] = "an install failed"
        elif not refreshed:
            row["classification"] = ("not measured: the cache was not refreshed to every "
                                     "stage's version (versions seen %s)"
                                     % [sorted(v) for v in versions])
        else:
            symlink_stage = [c for c in stages[1]["cache"] if c["version"] == stages[1]["version"]]
            row["classification"] = ("enforced in the cache: every installed copy is a real "
                                     "copy; the symlinked SKILL.md %s at the symlink stage%s"
                                     % ("was DROPPED" if symlink_stage and
                                        not symlink_stage[0]["skill_md_present"] else
                                        "was copied as a file",
                                        "" if CACHE_IS_WHAT_LOADS[harness] else
                                        " (a session loads the source path, not the cache)"))
    else:
        mutate(case, src, trial)
        entries = [(CORE, src)]
        if case == "duplicate-name":
            dup = copy_core(os.path.join(trial, "src", CORE + "-duplicate"))
            with open(os.path.join(dup, ".claude-plugin", "plugin.json")) as handle:
                manifest = json.load(handle)
            manifest["name"] = CORE + "-duplicate"
            with open(os.path.join(dup, ".claude-plugin", "plugin.json"), "w") as handle:
                json.dump(manifest, handle, indent=2)
            entries.append((CORE + "-duplicate", dup))
        market = marketplace(trial, entries)
        row["validate"] = validate(harness, env, src)
        steps.append(add_market(harness, env, market))
        for name, _source in entries:
            steps.append(install(harness, env, name))
        row["cache"] = observe(harness, home, CORE, src)
        if case == "duplicate-name":
            row["cache_duplicate"] = observe(harness, home, CORE + "-duplicate", entries[1][1])
        row["classification"] = classify(harness, [s for s in steps if "install" in " ".join(
            s.get("argv", [])) or " add " in " %s " % " ".join(s.get("argv", []))], row["cache"])
        if case == "missing-resource" and row["cache"]:
            installed = row["cache"][-1]["path"]
            probe_input = os.path.join(trial, "input.json")
            with open(probe_input, "w") as handle:
                json.dump({"note": "a probe input; the reference check comes first"}, handle)
            row["core_refusal"] = run(["uv", "run", "--quiet", os.path.join(
                installed, "skills", CORE, "scripts", SCRIPT), "check-input", probe_input], env)
            row["classification"] = ("installed; the harness does not notice the missing "
                                     "resource; the core refuses (exit %s)"
                                     % row["core_refusal"].get("exit"))
    row["steps"] = steps
    if live:
        row["live"] = "not implemented in this slice: the live half launches through launch.sh"
    else:
        row["live"] = "not run (free half only; --live adds the catalog session)"
    return row


def main():
    parser = argparse.ArgumentParser(description="The negative installation tests of %s." % CORE)
    parser.add_argument("--harness", required=True, choices=["claude-code", "codex"])
    parser.add_argument("--out", required=True, help="a fresh directory for the trials")
    parser.add_argument("--live", action="store_true", help="also run the live half")
    parser.add_argument("--case", action="append", default=[], choices=CASES)
    args = parser.parse_args()
    out = os.path.abspath(args.out)
    if os.path.exists(out):
        sys.stderr.write("negative-cases.py: %s exists; retained trials are never overwritten\n"
                         % out)
        return 2
    os.makedirs(out)
    for case in args.case or CASES:
        try:
            row = one_case(args.harness, case, out, args.live)
        except (OSError, ValueError) as exc:
            sys.stderr.write("negative-cases.py: %s could not be prepared: %s\n" % (case, exc))
            return 1
        sys.stdout.write(json.dumps(row) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
