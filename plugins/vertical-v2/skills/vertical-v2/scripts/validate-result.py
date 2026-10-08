#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""Validate one result document: the result schema, then the semantic checks S1 to S4.

    uv run validate-result.py <result.json> [--skill-root DIR]

Shared by the four front cores (station-loop.md section 5). stdout: one JSON document with the
schema findings and the semantic findings. Exit 0 the result holds, 2 usage (the file is not there
or not JSON), 3 the missing dependency, 4 the result fails its schema or a semantic check.
Side effects: none; it reads and writes nothing.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

from station_core import exits, validate  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate-result.py", description="Validate one front-core result document.",
        epilog="example:\n  uv run validate-result.py /tmp/run-0001/result.json\n\n"
               "side effects: none.\nexit: 0 holds, 2 usage, 3 the missing dependency, 4 a finding.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("result", help="the result document")
    parser.add_argument("--skill-root", metavar="DIR", default=None,
                        help="the directory holding SKILL.md (default: this script's own)")
    args = parser.parse_args(argv)
    try:
        root = validate.skill_root(args.skill_root)
    except validate.SkillRootMissing as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    prefix = validate.prefix_of(os.path.basename(root))
    try:
        with open(args.result, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        sys.stderr.write("the result is not a readable JSON file: %s (%s)\n" % (args.result, exc))
        return exits.USAGE
    try:
        schema = validate.load_schema("result", prefix, root)
    except validate.ReferenceUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    errors = validate.errors_for(doc, schema, prefix)
    semantic = validate.semantic(doc) if not errors else []
    ok = not errors and not semantic
    sys.stdout.write(json.dumps({"ok": ok, "interface_version": 1,
                                 "plugin_version": validate.plugin_version(root),
                                 "schema": errors, "semantic": semantic}, indent=2, sort_keys=True) + "\n")
    return exits.SUCCESS if ok else exits.VALIDATION


if __name__ == "__main__":
    sys.exit(main())
