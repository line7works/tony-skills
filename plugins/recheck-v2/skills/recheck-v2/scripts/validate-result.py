#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""Validate a recheck-v2 result: the schema, then the semantic checks of the E8 lane contract.

    uv run validate-result.py <result.json> [--input <input.json>] [--run-dir D] [--strict]

Schema validation against references/result.schema.json comes first; the semantic checks of
lane contract section 8 (V1 to V18) follow, each running when the supplied inputs allow it
(the input for cardinality, slices, grants, and the run-block rule; the run directory for the
receipt, the retained report, and artifact containment) and reporting itself as skipped
otherwise. Slice 1 implements V1, V5, V9, V10, V11, V15, V16, the workspace-free part of V2
(explicit-items inputs, amendment E8-A5), and the result-only part of V12; the run-directory
and workspace checks arrive with slice 2.

stdout: one JSON object {"ok": bool, "schema": [{path, message}], "semantic": [{id, path,
message}], "skipped": [{id, reason}]} and nothing else. stderr: diagnostics.
Exit 0 when ok; 4 when the result fails the schema or a semantic check (or, with --strict,
when any check was skipped). A result file that exists but is not JSON is invalid input: exit
4, with the parse error as the one entry inside schema[] (amendment E8-A4). A result file that
does not exist is a usage error: exit 2 with nothing on stdout; so is an --input that does not
exist or is not JSON, a --run-dir that is not a directory, or a bad argument. Exit 3 missing
dependency (jsonschema); 1 anything else (a schema under the skill root missing or unreadable).
Side effects: none. Reads only the files named and the schemas under the skill root.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from recheck_core import validate  # noqa: E402

EXAMPLE = """example:
  uv run %(prog)s /tmp/recheck-a-20260920-7f3c/result.json \\
      --input /tmp/recheck-a-20260920-7f3c/input.json
  -> {"ok": true, "schema": [], "semantic": [], "skipped": [{"id": "V3", "reason": "skipped: needs run directory"}, ...]}

exit status: 0 ok; 4 the result fails the schema or a semantic check (with --strict, also when any
  check was skipped), including a result file that exists but is not JSON (the parse error is the
  one entry inside schema[]); 2 usage (a result file that does not exist, an --input that does not
  exist or is not JSON, a --run-dir that is not a directory, a bad argument); 3 jsonschema missing;
  1 anything else (a schema under the skill root missing or unreadable).
side effects: none (read-only). Reruns are safe."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        sys.exit(2)


def build_parser():
    p = Parser(prog="validate-result.py",
               description="Validate a recheck-v2 result document: schema, then the semantic checks "
                           "of E8 lane contract section 8 that the supplied inputs allow.",
               epilog=EXAMPLE, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("result", help="the result.json to validate (absolute, or relative to the current directory); "
                                  "missing: exit 2; present but not JSON: exit 4 with the parse error inside schema[]")
    p.add_argument("--input", metavar="INPUT", default=None,
                   help="the input.json the run resolved; enables V1 key order and V2 slices on explicit items, and V16 (default: none)")
    p.add_argument("--run-dir", metavar="D", default=None,
                   help="the run directory (receipt, checkpoint, retained report); its checks arrive with slice 2 (default: none)")
    p.add_argument("--strict", action="store_true",
                   help="treat every skipped check as a failure (exit 4), so a caller can require the full validator")
    p.add_argument("--skill-root", metavar="DIR", default=None,
                   help="test only: load references from DIR instead of the script's own skill root")
    return p


def read_json(path, what):
    """Return (doc, error). The caller decides: a missing result file is exit 2 (checked before this
    runs), a result file that is not JSON is exit 4 with the error inside schema[], and an --input
    with either fault is exit 2 (E8-A4)."""
    if not os.path.isfile(path):
        return None, "%s does not exist: %s" % (what, path)
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8")), None
    except (OSError, ValueError) as exc:
        return None, "%s is not readable JSON: %s (%s)" % (what, path, exc)


def emit(out, ok):
    sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return 0 if ok else 4


def main(argv=None):
    args = build_parser().parse_args(argv)
    validate.require_jsonschema()  # exit 3 with the contract's message when jsonschema is absent
    try:
        schemas = validate.load_schemas(args.skill_root)
    except validate.ReferenceUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return 1
    if not os.path.isfile(args.result):
        build_parser().error("result file does not exist: %s" % args.result)
    input_doc = None
    if args.input is not None:
        input_doc, err = read_json(args.input, "--input")
        if err:
            build_parser().error(err)
    if args.run_dir is not None and not os.path.isdir(args.run_dir):
        build_parser().error("--run-dir is not a directory: %s" % args.run_dir)

    out = {"ok": False, "schema": [], "semantic": [], "skipped": []}
    result, err = read_json(args.result, "result")
    if err:
        out["schema"].append({"path": "", "message": err})
        sys.stderr.write("schema: %s\n" % err)
        return emit(out, False)
    out["schema"] = validate.validate_result(result, schemas)
    if out["schema"]:
        out["skipped"] = [{"id": cid, "reason": "skipped: schema failed"} for cid in validate.CHECK_IDS]
        sys.stderr.write("schema: %d error(s); semantic checks skipped\n" % len(out["schema"]))
        return emit(out, False)
    sem = validate.run_semantic(result, input_doc=input_doc, run_dir=args.run_dir, schemas=schemas)
    out["semantic"], out["skipped"] = sem["semantic"], sem["skipped"]
    ok = not out["semantic"] and (not args.strict or not out["skipped"])
    sys.stderr.write("schema ok; semantic: %d finding(s), %d check(s) skipped%s\n"
                     % (len(out["semantic"]), len(out["skipped"]), " (strict: skipped counts as failure)" if args.strict else ""))
    out["ok"] = ok
    return emit(out, ok)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - anything else is exit 1 with the cause named
        sys.stderr.write("validate-result.py failed: %s: %s\n" % (type(exc).__name__, exc))
        sys.exit(1)
