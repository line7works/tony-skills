#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""validate-examples.py: check this skill's own accepted and rejected examples.

    uv run validate-examples.py [--verbose] [--skill-root DIR]

Three passes over `references/examples/`:

1. **positive** — every example under `examples/` validates against the schema its name says
   (`input-*.json` the input schema, `result-*.json` the result schema, `answer-*.json` the
   answer schema).
2. **negative** — every example under `examples/invalid/` is REFUSED by that schema. A rejected
   example that quietly passes is the failure this pass exists to catch.
3. **mutations** — for every positive example, dropping each required field in turn must make it
   fail. A schema that has stopped requiring what it says it requires passes passes 1 and 2 and
   fails here.

stdout: {"ok", "positive", "negative", "mutations", "failures"} and nothing else.
stderr: the per-file lines under `--verbose`.
exit 0 when every check passed, 4 when any failed, 2 usage, 3 the dependency is missing.
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
SCHEMA_OF = (("input-", "input.schema.json"), ("result-", "result.schema.json"),
             ("answer-", "answer.schema.json"))

EXAMPLES = """examples:
  uv run validate-examples.py
  -> {"ok": true, "positive": 8, "negative": 7, "mutations": 96, "failures": []}
  uv run validate-examples.py --verbose      # one line per file on stderr

exit status: 0 every check passed; 4 one failed; 2 usage; 3 jsonschema missing.
side effects: none.
"""


def schema_for(name):
    for prefix, schema in SCHEMA_OF:
        if name.startswith(prefix):
            return schema
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate-examples.py",
        description="Check this skill's accepted examples validate and its rejected examples do "
                    "not, then drop each required field of every accepted example in turn.",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="one line per file on stderr")
    parser.add_argument("--skill-root", metavar="DIR", help="TEST ONLY: load references from here")
    args = parser.parse_args(argv)

    from signoff_core import inputs, validate
    references = os.path.join(args.skill_root or SKILL, "references")
    folder = os.path.join(references, "examples")
    try:
        schemas = {name: inputs.load_schema(references, name)
                   for _, name in SCHEMA_OF}
    except (OSError, ValueError) as failure:
        sys.stderr.write("reference unavailable: %s\n" % failure)
        return 1
    try:
        validate.load_jsonschema()
    except validate.MissingDependency as failure:
        sys.stderr.write(str(failure).rstrip("\n") + "\n")
        return 3

    failures, positive, negative, mutations = [], 0, 0, 0

    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        schema_name = schema_for(name)
        if schema_name is None:
            failures.append({"file": name, "why": "the file name says no schema to check it with"})
            continue
        doc = inputs.load(os.path.join(folder, name))
        errors = validate.schema_errors(doc, schemas[schema_name])
        positive += 1
        if errors:
            failures.append({"file": name, "why": "an accepted example was refused",
                             "errors": errors})
        elif args.verbose:
            sys.stderr.write("accepted  %s (%s)\n" % (name, schema_name))
        dropped, broke = drop_each_required(doc, schemas[schema_name], validate)
        mutations += dropped
        for field in broke:
            failures.append({"file": name, "why": "dropping the required field %r still "
                                                  "validated" % field})

    invalid = os.path.join(folder, "invalid")
    for name in sorted(os.listdir(invalid)) if os.path.isdir(invalid) else []:
        if not name.endswith(".json"):
            continue
        schema_name = schema_for(name)
        if schema_name is None:
            failures.append({"file": "invalid/" + name,
                             "why": "the file name says no schema to check it with"})
            continue
        doc = inputs.load(os.path.join(invalid, name))
        errors = validate.schema_errors(doc, schemas[schema_name])
        negative += 1
        if not errors:
            failures.append({"file": "invalid/" + name,
                             "why": "a rejected example validated"})
        elif args.verbose:
            sys.stderr.write("refused   invalid/%s (%s)\n" % (name, errors[0]["message"][:60]))

    ok = not failures
    sys.stdout.write(json.dumps({"ok": ok, "positive": positive, "negative": negative,
                                 "mutations": mutations, "failures": failures},
                                indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return 0 if ok else 4


def drop_each_required(doc, schema, validate):
    """Drop each required field of the top level and of every required object in turn.

    Returns (how many mutations were tried, [the fields whose absence still validated])."""
    tried, survived = 0, []
    for pointer, holder, key in required_fields(doc, schema):
        clone = json.loads(json.dumps(doc))
        target = clone
        for part in pointer:
            target = target[part]
        if key not in target:
            continue
        del target[key]
        tried += 1
        if not validate.schema_errors(clone, schema):
            survived.append("/".join(list(pointer) + [key]))
    return tried, survived


def required_fields(doc, schema, pointer=()):
    """(pointer, holder, key) for every required field the schema names that the document holds."""
    out = []
    for key in schema.get("required", []):
        out.append((pointer, doc, key))
    for key, sub in (schema.get("properties") or {}).items():
        if not isinstance(doc, dict) or key not in doc:
            continue
        if isinstance(sub, dict) and isinstance(doc[key], dict) and sub.get("required"):
            out.extend(required_fields(doc[key], sub, pointer + (key,)))
    return out


if __name__ == "__main__":
    sys.exit(main())
