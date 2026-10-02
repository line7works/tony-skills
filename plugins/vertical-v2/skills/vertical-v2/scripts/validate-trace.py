#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""Validate one trace file: every line against `references/trace.schema.json`, its sequence, and the
refusal rule on every visit and summons (ruling E15-7; a back-frame file, `references/back-files.txt`).

    uv run validate-trace.py <trace.jsonl> [--known-version N ...] [--skill-root DIR]

A visit or summons whose identity breaks the refusal rule (a v1 name, a name that is not the expected
one, a root under a v1 plugin folder, an interface version not known) is a finding: such a station
should have been refused before the visit. stdout: one JSON document, `{"ok", "lines", "findings":
[{"line", "rule" | "path", "message"}]}`. Exit 0 the trace holds, 2 usage (no such file), 3 the missing
dependency, 4 a finding. Side effects: none; it reads one file and writes nothing.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

from station_core import exits, validate  # noqa: E402
from back_core import trace  # noqa: E402


def check(path, known, root):
    findings = []
    count = 0
    with open(path, encoding="utf-8") as fh:
        for index, raw in enumerate(fh):
            count += 1
            number = index + 1
            try:
                one = json.loads(raw)
            except ValueError as exc:
                findings.append({"line": number, "path": "/", "message": "the line does not parse: %s" % exc})
                continue
            errors = trace.schema_errors(one, root, validate.prefix_of(os.path.basename(validate.skill_root(root))))
            for error in errors:
                findings.append({"line": number, "path": error["path"], "message": error["message"]})
            if errors:
                continue
            for problem in trace.check_line(one, with_seq=True):
                findings.append({"line": number, "path": "/", "message": problem})
            if one.get("seq") != index:
                findings.append({"line": number, "path": "/seq", "message": "seq is %r, not the line index %d"
                                                                            % (one.get("seq"), index)})
            if one.get("kind") in ("visit", "summons"):
                for refusal in trace.refusals(one["expected"], one["identity"], known):
                    findings.append({"line": number, "rule": refusal["rule"],
                                     "message": "a %s that the refusal rule refuses: %s" % (one["kind"], refusal["message"])})
    return count, findings


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate-trace.py", description="Validate one back core's trace.jsonl.",
        epilog="example:\n  uv run validate-trace.py /tmp/run-0001/trace.jsonl\n\n"
               "side effects: none; it reads one file and writes nothing.\n"
               "exit: 0 the trace holds, 2 usage, 3 the missing dependency, 4 a finding.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trace", help="the trace file (a run directory's trace.jsonl)")
    parser.add_argument("--known-version", type=int, action="append", default=None, metavar="N",
                        help="an interface version the caller knows (repeatable; default 1)")
    parser.add_argument("--skill-root", metavar="DIR", default=None,
                        help="the directory holding SKILL.md (default: this script's own)")
    args = parser.parse_args(argv)
    if not os.path.isfile(args.trace):
        sys.stderr.write("no such trace file: %s\n" % args.trace)
        return exits.USAGE
    try:
        root = validate.skill_root(args.skill_root)
        validate.require_jsonschema(validate.prefix_of(os.path.basename(root)))
        count, findings = check(args.trace, tuple(args.known_version or (1,)), root)
    except (validate.SkillRootMissing, validate.ReferenceUnavailable) as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    sys.stdout.write(json.dumps({"ok": not findings, "interface_version": 1,
                                 "plugin_version": validate.plugin_version(root), "lines": count,
                                 "findings": findings}, indent=2, sort_keys=True) + "\n")
    return exits.SUCCESS if not findings else exits.VALIDATION


if __name__ == "__main__":
    sys.exit(main())
