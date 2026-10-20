#!/usr/bin/python3
"""The installed-package check both harness setups of sun-v2 run (E16 slice 5, part J4).

Adapted from plugins/ship-v2/setups/verify-package.py, cut to what sun-v2's install has to show. One file for
both harnesses, so the two checks cannot drift apart; the core is this file's own plugin folder.

    verify-package.py --cache <harness plugin cache root> --market <marketplace name>

Checks, each a finding when it fails:
  1. exactly one installed copy under <cache>/<market>/sun-v2/<version>/, named for plugin.json's version;
  2. every skill `lifecycle/skills.json` lists has its SKILL.md in the installed copy, byte-equal to the checkout's;
  3. the installed `lifecycle/scripts/sun.py`, started by its own entry (`/bin/sh lifecycle/scripts/sun`) from
     the cache folder: `--help` exits 0 and prints what the checkout's prints;
  4. `skill-identity` from the installed copy and from the checkout: both exit 0, content_sha256 equal (the
     commit is recorded, never compared: the installed copy is no repository);
  5. no symlink anywhere in the installed copy.

Prints one JSON object; exit 0 when there is no finding, 4 when there is one, 2 usage.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
CORE = os.path.basename(PLUGIN)


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def sun(root, *args):
    proc = subprocess.run(["/bin/sh", os.path.join(root, "lifecycle", "scripts", "sun")] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="/")
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")[-600:]


def identity(root):
    code, out, err = sun(root, "skill-identity")
    try:
        doc = json.loads(out) if out.strip() else None
    except ValueError:
        doc = None
    return {"exit": code, "document": doc, "stderr": err}


def main():
    parser = argparse.ArgumentParser(description="Verify the installed %s package." % CORE)
    parser.add_argument("--cache", required=True, help="the harness's plugin cache root")
    parser.add_argument("--market", required=True, help="the marketplace name")
    args = parser.parse_args()
    findings = []
    version = load(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"))["version"]
    base = os.path.join(args.cache, args.market, CORE)
    versions = sorted(os.listdir(base)) if os.path.isdir(base) else []
    report = {"core": CORE, "cache": args.cache, "marketplace": args.market, "canonical": PLUGIN,
              "canonical_version": version, "installed_versions": versions}
    if versions != [version]:
        findings.append("expected exactly one installed copy at %s/%s, found %s" % (base, version, versions or "none"))
    installed = os.path.join(base, version)
    if not os.path.isdir(installed):
        report.update(ok=False, findings=findings)
        print(json.dumps(report, indent=2))
        return 4
    report["installed"] = installed

    skills = {}
    for entry in load(os.path.join(PLUGIN, "lifecycle", "skills.json"))["skills"]:
        rel = os.path.join(entry["folder"], "SKILL.md")
        got = read(os.path.join(installed, rel))
        skills[entry["name"]] = {"path": os.path.join(installed, rel), "present": got is not None,
                                 "equal": got is not None and got == read(os.path.join(PLUGIN, rel))}
        if not skills[entry["name"]]["equal"]:
            findings.append("the installed %s is missing or differs from the checkout's" % rel)
    report["skills"] = skills

    helps = {"canonical": sun(PLUGIN, "--help"), "installed": sun(installed, "--help")}
    report["help"] = {k: {"exit": v[0], "lines": len(v[1].splitlines())} for k, v in helps.items()}
    report["help_equal"] = helps["installed"][0] == 0 and helps["installed"][1] == helps["canonical"][1]
    if not report["help_equal"]:
        findings.append("the installed sun.py --help exits %s or differs from the checkout's" % helps["installed"][0])

    ids = {"canonical": identity(PLUGIN), "installed": identity(installed)}
    report["identities"] = ids
    hashes = [(ids[k]["document"] or {}).get("content_sha256") for k in ("canonical", "installed")]
    report["identity_equal"] = all(ids[k]["exit"] == 0 for k in ids) and bool(hashes[0]) and hashes[0] == hashes[1]
    if not report["identity_equal"]:
        findings.append("skill-identity content_sha256 differs or could not be read (exits %s, %s)"
                        % (ids["canonical"]["exit"], ids["installed"]["exit"]))

    links = [installed] if os.path.islink(installed) else []
    for root, dirs, files in os.walk(installed):
        links += [os.path.join(root, n) for n in dirs + files if os.path.islink(os.path.join(root, n))]
    report["symlinks_in_the_installed_package"] = links
    if links:
        findings.append("the installed package holds %d symlink(s)" % len(links))
    report["ok"] = not findings
    report["findings"] = findings
    print(json.dumps(report, indent=2))
    return 0 if not findings else 4


if __name__ == "__main__":
    sys.exit(main())
