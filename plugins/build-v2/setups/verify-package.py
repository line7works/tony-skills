#!/usr/bin/env python3
"""The installed-package verification both harness setups of this core run (E13 slice 3, 3.3).

Adapted from the recheck-v2 pilot's two `verify-install.sh` scripts (their embedded Python), one
file for both harnesses so the two checks cannot drift apart. Byte-identical in build-v2 and
signoff-v2; the core is this file's own plugin folder.

    verify-package.py --cache <harness plugin cache root> --market <marketplace name>

Checks, each a finding when it fails:
  1. exactly one installed copy of the core under <cache>/<market>/<core>/<version>/, named for
     the canonical plugin.json version;
  2. `diff -r -x __pycache__` of the installed plugin against this checkout's plugin folder;
  3. the installed SKILL.md frontmatter block (through the closing delimiter) byte-equal to the
     canonical one (a whole-block compare, stricter than a parsed field compare, standard library
     only);
  4. every runtime reference the installed SKILL.md, adapters/README.md, references/*.md and each
     adapters/*/profile.md names, Markdown links and backticked paths alike, whose first segment
     is one of the skill's own directories: resolved from the document and from the skill root,
     required to exist inside the installed root and to be reached through no symlink. A
     backticked path whose first segment is not one of those directories is listed, never gating
     (workspace paths such as docs/plans/..., artifact names), and so is `scripts/records.py`,
     which names the records component's own CLI inside that component, not this skill;
  5. an lstat walk of the whole installed tree, the root included: no symlink anywhere;
  6. the core's own identity command, `<script> skill-identity`, run through `uv run` from the
     installed copy and from the checkout: content_sha256 equal (version and commit recorded,
     never compared, the pilot's E9-16), each run's exit kept.

Prints one JSON object; exit 0 when there is no finding, 4 when there is one, 2 usage.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
CORE = os.path.basename(PLUGIN)
SKILL = os.path.join(PLUGIN, "skills", CORE)
SCRIPT = {"build-v2": "build.py", "signoff-v2": "signoff.py"}[CORE]
SKILL_DIRS = ("references", "adapters", "scripts", "agents", "claude-code", "codex")


def canonical_version():
    with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")) as handle:
        return json.load(handle)["version"]


def frontmatter(path):
    with open(path, "rb") as handle:
        data = handle.read()
    if not data.startswith(b"---\n"):
        return None
    end = data.find(b"\n---\n", 4)
    return data[:end + 5] if end >= 0 else None


def through_symlink(path, root):
    """True when any component from `root` down to `path` is a symlink."""
    rel = os.path.relpath(path, root)
    current = root
    for part in rel.split(os.sep):
        current = os.path.join(current, part)
        if os.path.islink(current):
            return True
    return False


def references(installed_skill, installed_root):
    docs = [os.path.join(installed_skill, "SKILL.md"),
            os.path.join(installed_skill, "adapters", "README.md")]
    refs_dir = os.path.join(installed_skill, "references")
    docs += sorted(os.path.join(refs_dir, n) for n in os.listdir(refs_dir) if n.endswith(".md"))
    adapters = os.path.join(installed_skill, "adapters")
    docs += sorted(os.path.join(adapters, n, "profile.md") for n in os.listdir(adapters)
                   if os.path.isfile(os.path.join(adapters, n, "profile.md")))
    checked, findings, prose = [], [], []
    for doc in docs:
        if not os.path.isfile(doc):
            findings.append("a document the check reads is missing: %s" % doc)
            continue
        text = open(doc, encoding="utf-8").read()
        links = re.findall(r"\]\(([^)\s]+)\)", text)
        ticks = re.findall(r"`([A-Za-z0-9_.-]+/[A-Za-z0-9_./-]*[A-Za-z0-9_-])`", text)
        for ref in links + ticks:
            if "://" in ref or ref.startswith("#") or ref.startswith("/"):
                continue
            ref = ref.split("#")[0]
            first = ref.split("/")[0]
            if first not in SKILL_DIRS and first not in ("..", "."):
                prose.append(ref)
                continue
            hit = None
            for base in (os.path.dirname(doc), installed_skill):
                candidate = os.path.normpath(os.path.join(base, ref))
                if os.path.exists(candidate):
                    hit = candidate
                    break
            if hit is None and ref.split("/")[-1] == "records.py":
                # the records component's own CLI (`<records root>/scripts/records.py`), which
                # the contract names by its path inside THAT component, never this skill's
                prose.append(ref + " (the records component's path)")
                continue
            checked.append(ref)
            if hit is None:
                findings.append("reference %r in %s does not resolve" % (ref, os.path.relpath(doc, installed_root)))
                continue
            real_root = os.path.realpath(installed_root)
            if not (os.path.realpath(hit) + os.sep).startswith(real_root + os.sep) and \
                    os.path.realpath(hit) != real_root:
                findings.append("reference %r resolves outside the installed root" % ref)
            elif through_symlink(hit, installed_root):
                findings.append("reference %r is reached through a symlink" % ref)
    return checked, findings, sorted(set(prose))


def identity(script, env):
    proc = subprocess.run(["uv", "run", "--quiet", script, "skill-identity"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="/", env=env)
    out = proc.stdout.decode("utf-8", "replace").strip()
    try:
        doc = json.loads(out) if out else None
    except ValueError:
        doc = None
    return {"exit": proc.returncode, "document": doc,
            "stderr": proc.stderr.decode("utf-8", "replace").strip()[-600:]}


def main():
    parser = argparse.ArgumentParser(description="Verify the installed %s package." % CORE)
    parser.add_argument("--cache", required=True, help="the harness's plugin cache root")
    parser.add_argument("--market", required=True, help="the marketplace name")
    args = parser.parse_args()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("RECORDS_ROOT", None)
    findings = []
    version = canonical_version()
    base = os.path.join(args.cache, args.market, CORE)
    versions = sorted(os.listdir(base)) if os.path.isdir(base) else []
    report = {"core": CORE, "cache": args.cache, "marketplace": args.market,
              "canonical": PLUGIN, "canonical_version": version, "installed_versions": versions}
    if versions != [version]:
        findings.append("expected exactly one installed copy at %s/%s, found %s"
                        % (base, version, versions or "none"))
    installed = os.path.join(base, version)
    if not os.path.isdir(installed):
        report.update(ok=False, findings=findings)
        print(json.dumps(report, indent=2))
        return 4
    report["installed"] = installed
    diff = subprocess.run(["diff", "-r", "-x", "__pycache__", PLUGIN, installed],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = [l for l in diff.stdout.decode("utf-8", "replace").splitlines() if l.strip()]
    report["diff"] = {"exit": diff.returncode, "lines": len(lines), "head": lines[:20]}
    if diff.returncode != 0 or lines:
        findings.append("the installed package differs from the checkout (%d diff lines)" % len(lines))
    installed_skill = os.path.join(installed, "skills", CORE)
    same = frontmatter(os.path.join(installed_skill, "SKILL.md")) == frontmatter(
        os.path.join(SKILL, "SKILL.md"))
    report["frontmatter_equal"] = same
    if not same:
        findings.append("the installed SKILL.md frontmatter differs from the canonical block")
    checked, ref_findings, prose = references(installed_skill, installed)
    report["references_checked"] = len(checked)
    report["reference_findings"] = ref_findings
    report["prose_paths_not_gating"] = prose
    findings.extend(ref_findings)
    links = []
    if os.path.islink(installed):
        links.append(installed)
    for root, dirs, files in os.walk(installed):
        for name in dirs + files:
            if os.path.islink(os.path.join(root, name)):
                links.append(os.path.join(root, name))
    report["symlinks_in_the_installed_package"] = links
    if links:
        findings.append("the installed package holds %d symlink(s)" % len(links))
    ids = {"canonical": identity(os.path.join(SKILL, "scripts", SCRIPT), env),
           "installed": identity(os.path.join(installed_skill, "scripts", SCRIPT), env)}
    report["identity_command"] = "%s skill-identity" % SCRIPT
    report["identities"] = ids
    hashes = [(ids[k]["document"] or {}).get("content_sha256") for k in ("canonical", "installed")]
    report["identity_equal"] = bool(hashes[0]) and hashes[0] == hashes[1]
    if not report["identity_equal"]:
        findings.append("skill-identity content_sha256 differs or could not be read (exits %s, %s)"
                        % (ids["canonical"]["exit"], ids["installed"]["exit"]))
    report["ok"] = not findings
    report["findings"] = findings
    print(json.dumps(report, indent=2))
    return 0 if not findings else 4


if __name__ == "__main__":
    sys.exit(main())
