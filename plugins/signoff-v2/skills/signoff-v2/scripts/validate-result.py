#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""validate-result.py: schema and semantic validation of one signoff-v2 result.

    uv run validate-result.py <result.json> [--input <input.json>] [--run-dir D] [--strict]

The schema says what shape a result has; the semantic checks say what a schema cannot:

- a raised finding's location file is inside the source set, and a note's is not;
- the verdict is v1's severity mapping over the raised findings;
- a result with no raised findings carries a non-empty list of executed checks, each with its
  output — an empty list is a validation failure, not a clean verdict;
- a result that records a verdict has status `completed` and is not report-only;
- a report-only result wrote nothing to the workspace or the log;
- every path in `records_written` is an authorized write of this station: the run directory, the
  ledger document, its verdict doc, or the component's log under `docs/records/`.

stdout: {"ok", "schema", "semantic", "result"} and nothing else. stderr: diagnostics.
exit 0 when ok, 4 when not, 2 usage, 3 the dependency is missing, 1 anything else.
`--help` and argument checking work without the dependency.

side effects: none. This script only reads.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SKILL = os.path.dirname(HERE)

EXAMPLES = """examples:
  uv run validate-result.py /tmp/signoff-d-20260921-7f3c/result.json \\
      --input /tmp/signoff-d-20260921-7f3c/input.json
  -> {"ok": true, "schema": [], "semantic": []}

exit status: 0 ok; 4 the result failed a check; 2 usage; 3 jsonschema missing; 1 anything else.
side effects: none.
"""


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate-result.py",
        description="Validate one signoff-v2 result against its schema and the semantic checks.",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("result", metavar="result.json", help="the result to validate")
    parser.add_argument("--input", metavar="input.json",
                        help="the run's input, for the checks that compare the two")
    parser.add_argument("--run-dir", metavar="D",
                        help="the run directory, for the checks that read its artifacts")
    parser.add_argument("--skill-root", metavar="DIR", help="TEST ONLY: load references from here")
    parser.add_argument("--strict", action="store_true",
                        help="treat a semantic finding as a failure even when the schema passed")
    args = parser.parse_args(argv)

    from signoff_core import inputs, validate
    references = os.path.join(args.skill_root or SKILL, "references")
    try:
        result = inputs.load(args.result)
        supplied = inputs.load(args.input) if args.input else None
    except inputs.InputError as failure:
        sys.stderr.write("usage: %s\n" % failure)
        return 2
    try:
        schema = inputs.load_schema(references, "result.schema.json")
    except (OSError, ValueError) as failure:
        sys.stderr.write("reference unavailable: references/result.schema.json (%s)\n" % failure)
        return 1
    try:
        errors = validate.schema_errors(result, schema)
    except validate.MissingDependency as failure:
        sys.stderr.write(str(failure).rstrip("\n") + "\n")
        return 3
    semantic = validate.semantic(result, supplied)
    if args.run_dir:
        semantic.extend(run_dir_checks(result, args.run_dir))
    ok = not errors and not semantic
    sys.stdout.write(json.dumps({"ok": ok, "schema": errors, "semantic": semantic,
                                 "result": os.path.abspath(args.result)},
                                indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return 0 if ok else 4


def run_dir_checks(result, run_dir):
    """Every artifact the result names under the run directory is there, and the receipt agrees."""
    out = []
    for row in (result.get("records_written") or []):
        if row.get("kind") != "run_artifact":
            continue
        if not os.path.exists(row["path"]):
            out.append({"path": "/records_written",
                        "message": "%s is listed as written and is not there" % row["path"]})
    receipt = result.get("receipt")
    if receipt and os.path.isfile(receipt):
        try:
            with open(receipt, "rb") as fh:
                doc = json.loads(fh.read().decode("utf-8"))
        except (OSError, ValueError) as failure:
            out.append({"path": "/receipt", "message": "the receipt could not be read: %s" % failure})
            return out
        if doc.get("run_id") != (result.get("run") or {}).get("run_id"):
            out.append({"path": "/receipt",
                        "message": "the receipt's run id is not the result's"})
        if result.get("status") == "completed" and not doc.get("committed"):
            out.append({"path": "/receipt",
                        "message": "the run completed but its receipt is not committed"})
    return out


if __name__ == "__main__":
    sys.exit(main())
