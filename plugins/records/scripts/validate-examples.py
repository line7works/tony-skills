#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""Validate the records component's example events against event.schema.json.

    uv run validate-examples.py [--records-root DIR] [--verbose]      (from any directory)

Resolves `references/` from the component root, which is this script's own location
(`scripts/..`) unless `--records-root` names another directory (test only).

Checks:

- every file under `references/examples/valid/` is one event that validates;
- every file under `references/examples/invalid/` is `{"reason": ..., "event": ...}` and the
  event is rejected, the reason saying which rule rejects it;
- every valid example still fails once any one of its required fields is dropped, so a
  `required` list that quietly stopped being enforced is caught here (the guide's "rerun both
  sets after tightening a schema");
- `references/examples/example.events.jsonl` walks clean: every line parses and validates, `seq`
  equals the line index, and every `prev` equals the hash of the line before (section 10).

stdout: one JSON object {"ok", "valid": {"files", "failing"}, "invalid": {"total", "rejected"},
"mutations": {"total", "rejected"}, "log": {"lines", "ok"}, "failures": [strings]} and nothing
else. stderr: diagnostics; with --verbose one line per check.

Exit status: 0 every check passed; 4 a check failed (the failures list names each, an example
that does not load included); 2 usage (an unknown argument, a --records-root that is not a
directory); 3 jsonschema missing (nothing on stdout); 1 a schema under the component root
missing or unreadable.
Side effects: none (read-only). Reruns are safe.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from records_core import events as events_mod, validate  # noqa: E402

EXAMPLE = """example:
  uv run validate-examples.py
  -> {"ok": true, "valid": {"files": 17, "failing": 0}, "invalid": {"total": 28, "rejected": 28},
      "mutations": {"total": 229, "rejected": 229}, "log": {"lines": 9, "ok": true}, "failures": []}
  uv run validate-examples.py --verbose 2>checks.log

exit status: 0 every check passed; 4 a check failed; 2 usage; 3 jsonschema missing (nothing on
  stdout); 1 a schema under the component root missing or unreadable.
side effects: none (read-only). Reruns are safe."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        sys.exit(2)


def build_parser():
    p = Parser(prog="validate-examples.py",
               description="Validate the records component's example events against event.schema.json, "
                           "reject every invalid example and every dropped-field mutation, and walk the "
                           "example log's chain.",
               epilog=EXAMPLE, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--records-root", metavar="DIR", default=None,
                   help="test only: load references from DIR instead of this script's own component root")
    p.add_argument("--verbose", action="store_true", default=False, help="one line per check on stderr")
    return p


def log(verbose, message):
    if verbose:
        sys.stderr.write(message + "\n")


def load(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def files_in(directory):
    if not os.path.isdir(directory):
        return []
    return sorted(os.path.join(directory, n) for n in os.listdir(directory) if n.endswith(".json"))


def required_fields(event, schemas):
    """The fields the schema requires of this event: the common list plus its kind's own.

    Read from the schema rather than from what the example happens to carry, so a field the
    schema leaves optional (a `join_basis` on a waiver) is not asserted to be required.
    """
    doc = schemas.docs["event"]
    out = set(doc.get("required", []))
    kind = event.get("kind")
    for entry in doc.get("allOf", []):
        condition = entry.get("if", {}).get("properties", {}).get("kind", {})
        if condition.get("const") == kind:
            out.update(entry.get("then", {}).get("required", []))
    return sorted(out)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    validate.require_jsonschema()
    try:
        root = validate.component_root(args.records_root)
        schemas = validate.load_schemas(root)
    except validate.ComponentRootMissing as exc:
        parser.error(str(exc))
    except validate.ReferenceUnavailable as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1

    examples = os.path.join(root, "references", "examples")
    failures = []
    valid_files = files_in(os.path.join(examples, "valid"))
    failing = 0
    mutations = rejected_mutations = 0

    for path in valid_files:
        name = os.path.relpath(path, examples)
        try:
            event = load(path)
        except (OSError, ValueError) as exc:
            failures.append("%s: %s" % (name, exc))
            failing += 1
            continue
        errors = validate.validate_event(event, schemas)
        if errors:
            failing += 1
            failures.append("%s: %s %s" % (name, errors[0]["path"] or "/", errors[0]["message"]))
            log(args.verbose, "FAIL     %s" % name)
        else:
            log(args.verbose, "PASS     %s" % name)
        for field in required_fields(event, schemas):
            if not isinstance(event, dict) or field not in event:
                continue  # the example is already failing above; its absent field is that failure
            mutated = copy.deepcopy(event)
            mutated.pop(field)
            mutations += 1
            if validate.validate_event(mutated, schemas):
                rejected_mutations += 1
                log(args.verbose, "REJECTED %s without /%s" % (name, field))
            else:
                failures.append("%s: dropping /%s is still accepted" % (name, field))
                log(args.verbose, "ACCEPTED (BUG) %s without /%s" % (name, field))

    invalid_files = files_in(os.path.join(examples, "invalid"))
    rejected = 0
    for path in invalid_files:
        name = os.path.relpath(path, examples)
        try:
            doc = load(path)
            reason, event = doc["reason"], doc["event"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            failures.append("%s: %s" % (name, exc))
            continue
        if not isinstance(reason, str) or not reason.strip():
            failures.append("%s: an invalid example says which rule rejects it" % name)
        if validate.validate_event(event, schemas):
            rejected += 1
            log(args.verbose, "REJECTED %s" % name)
        else:
            failures.append("%s: accepted, though it must be rejected (%s)" % (name, reason))
            log(args.verbose, "ACCEPTED (BUG) %s" % name)

    log_path = os.path.join(examples, "example.events.jsonl")
    log_lines, log_ok = 0, False
    if not os.path.isfile(log_path):
        failures.append("references/examples/example.events.jsonl is missing")
    else:
        try:
            walked = events_mod.walk(log_path, schemas)
            log_lines, log_ok = len(walked["events"]), True
            log(args.verbose, "CHAIN OK example.events.jsonl (%d lines, head %s)" % (log_lines, walked["head"][:12]))
        except events_mod.RecordsError as exc:
            failures.append("example.events.jsonl: %s" % exc.document.get("reason"))
            log(args.verbose, "CHAIN (BUG) example.events.jsonl")

    out = {
        "ok": not failures,
        "valid": {"files": len(valid_files), "failing": failing},
        "invalid": {"total": len(invalid_files), "rejected": rejected},
        "mutations": {"total": mutations, "rejected": rejected_mutations},
        "log": {"lines": log_lines, "ok": log_ok},
        "failures": failures,
    }
    sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return 0 if out["ok"] else 4


if __name__ == "__main__":
    sys.exit(main())
