#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""Check one result against its schema and against the checks a schema cannot make.

    uv run validate-result.py <result.json> [--input <input.json>] [--run-dir D] [--skill-root DIR]

The schema says what shape a result has; the semantic checks say whether it is a result this
core could honestly have produced. Ten of them (`build_core/validate.py` names each): the card
moved only on its three conditions together; the two status fields agree; the out-of-scope list
is exactly the source-set paths outside the slice's named paths; every named check has one row;
every write is an authorized destination; a report-only run wrote nothing; a refused answer
changed nothing; the log's bookkeeping agrees with itself; a failing check and `completed`
cannot both stand; and an appended event carries the identity.

`--input` and `--run-dir` are optional: a check that needs one it was not given reports itself
as skipped rather than passing quietly, so a caller can see what was not checked.

stdout: `{"ok", "schema": [...], "semantic": [...], "skipped": [...]}`. stderr: diagnostics.
Exit 0 when it holds, 2 a usage slip, 3 the missing dependency, 4 when any check failed.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_core import exits, validate  # noqa: E402


def read(path, what):
    if not os.path.isfile(path):
        raise SystemExit2("no such %s file: %s" % (what, path))
    try:
        with open(path, "rb") as fh:
            body = json.loads(fh.read().decode("utf-8"))
    except ValueError as exc:
        raise SystemExit2("the %s file is not JSON: %s (%s)" % (what, path, exc))
    if not isinstance(body, dict):
        raise SystemExit2("the %s file is not a JSON object: %s" % (what, path))
    return body


class SystemExit2(RuntimeError):
    """A usage slip: exit 2."""


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate-result.py",
        description="Validate one build-v2 result against references/result.schema.json and the "
                    "semantic checks of references/build-contract.md.",
        epilog="example:\n"
               "  uv run validate-result.py /tmp/build-c-20260922-7f3c/result.json \\\n"
               "      --input /tmp/build-c-20260922-7f3c/input.json\n\n"
               "side effects: none; it reads and writes nothing.\n"
               "exit: 0 the result holds, 2 a usage slip, 3 the missing dependency, 4 a failure.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("result", metavar="result.json", help="the result to check")
    parser.add_argument("--input", metavar="FILE", default=None,
                        help="the run's input, for the checks that need it")
    parser.add_argument("--run-dir", metavar="D", default=None,
                        help="the run directory, for the write-containment check")
    parser.add_argument("--skill-root", metavar="DIR", default=None,
                        help="the directory holding SKILL.md (default: this script's own)")
    args = parser.parse_args(argv)

    try:
        result = read(args.result, "result")
        input_doc = read(args.input, "input") if args.input else None
        schema = validate.load_schema("result", args.skill_root)
    except SystemExit2 as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except validate.SkillRootMissing as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except validate.ReferenceUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE

    schema_errors = validate.errors_for(result, schema)
    semantic = validate.run_semantic(result, input_doc, args.run_dir)
    report = {
        "ok": not schema_errors and not semantic["semantic"],
        "interface_version": 1,
        "plugin_version": validate.plugin_version(args.skill_root),
        "result": os.path.abspath(args.result),
        "schema": schema_errors,
        "semantic": semantic["semantic"],
        "skipped": semantic["skipped"],
        "checks": validate.CHECK_IDS,
    }
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return exits.SUCCESS if report["ok"] else exits.VALIDATION


if __name__ == "__main__":
    sys.exit(main())
