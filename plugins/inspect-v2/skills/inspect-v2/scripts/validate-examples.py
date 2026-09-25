#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""Check every example under `references/examples/` against its schema (shared by the four cores).

    uv run validate-examples.py [--skill-root DIR] [--verbose]

Four passes, so a schema that drifts from what the core writes fails here rather than in a run:

1. **Accepted.** Every file under `<kind>/valid/` validates against `<kind>.schema.json`; a result
   example also passes the semantic checks (S1 to S4).
2. **Rejected.** Every file under `<kind>/invalid/` is refused: a file whose name starts with
   `semantic-` must pass the schema and be refused by a semantic check; every other file must be
   refused by the schema. Refused for the wrong reason is a failure.
3. **Dropped field.** Every required field of every accepted example is dropped in turn, and the
   result must be refused.
4. **Coverage.** Every status and every stop tag of the result schema has an accepted example, and
   every semantic check has a rejected one.

stdout: one JSON document. stderr: the per-file lines under `--verbose`.
Exit 0 everything held, 2 an unknown argument, 3 the missing dependency, 4 any check failed.
Side effects: none; it reads and writes nothing.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

from station_core import exits, validate  # noqa: E402

KINDS = ("input", "result")
SEMANTIC_PREFIX = "semantic-"


def files_in(folder):
    if not os.path.isdir(folder):
        return []
    return [os.path.join(folder, n) for n in sorted(os.listdir(folder)) if n.endswith(".json")]


def read(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def check(root, verbose):
    prefix = validate.prefix_of(os.path.basename(validate.skill_root(root)))
    examples = os.path.join(validate.references_dir(root), "examples")
    failures = []
    counts = {"accepted": 0, "rejected": 0, "dropped": 0}
    seen_status, seen_tags, seen_semantic = set(), set(), set()

    def note(line):
        if verbose:
            sys.stderr.write(line + "\n")

    schemas = {}
    for kind in KINDS:
        schemas[kind] = schema = validate.load_schema(kind, prefix, root)
        folder = os.path.join(examples, kind)
        for path in files_in(os.path.join(folder, "valid")):
            doc = read(path)
            rel = os.path.relpath(path, examples)
            counts["accepted"] += 1
            errors = validate.errors_for(doc, schema, prefix)
            if errors:
                failures.append({"file": rel, "why": "accepted example refused", "errors": errors[:4]})
                note("REFUSED  %s" % rel)
                continue
            note("ok       %s" % rel)
            if kind == "result":
                seen_status.add(doc.get("status"))
                if doc.get("stop_tag"):
                    seen_tags.add(doc["stop_tag"])
                semantic = validate.semantic(doc)
                if semantic:
                    failures.append({"file": rel, "why": "accepted result failed a semantic check",
                                     "errors": semantic[:4]})
            for field in [f for f in schema.get("required") or [] if f in doc]:
                dropped = copy.deepcopy(doc)
                del dropped[field]
                counts["dropped"] += 1
                if not validate.errors_for(dropped, schema, prefix):
                    failures.append({"file": rel, "why": "dropping the required field %r was accepted" % field,
                                     "errors": []})
        for path in files_in(os.path.join(folder, "invalid")):
            doc = read(path)
            rel = os.path.relpath(path, examples)
            counts["rejected"] += 1
            errors = validate.errors_for(doc, schema, prefix)
            semantic = validate.semantic(doc) if kind == "result" else []
            for finding in semantic:
                seen_semantic.add(finding["id"])
            if os.path.basename(path).startswith(SEMANTIC_PREFIX):
                if errors:
                    failures.append({"file": rel, "why": "a semantic example was refused by the schema instead",
                                     "errors": errors[:4]})
                elif not semantic:
                    failures.append({"file": rel, "why": "a semantic example was accepted by every check",
                                     "errors": []})
                else:
                    note("refused  %s (%s)" % (rel, semantic[0]["id"]))
            elif not errors:
                failures.append({"file": rel, "why": "a rejected example was accepted by the schema", "errors": []})
                note("ACCEPTED %s" % rel)
            else:
                note("refused  %s" % rel)

    result_schema = schemas["result"]
    for status in result_schema["properties"]["status"]["enum"]:
        if status not in seen_status:
            failures.append({"file": "result/valid", "why": "no accepted example ends as %r" % status, "errors": []})
    tags = [t for t in result_schema["properties"]["stop_tag"]["enum"] if t]
    described = [t.strip("`") for t in result_schema["properties"]["stop_tag"]["description"].split("`")[1::2]]
    for tag in tags:
        if tag not in seen_tags:
            failures.append({"file": "result/valid", "why": "no accepted example stops with %r" % tag, "errors": []})
        if tag not in described:
            failures.append({"file": "references/result.schema.json",
                             "why": "the stop_tag description does not name %r" % tag, "errors": []})
    missing = [cid for cid in validate.CHECK_IDS if cid not in seen_semantic]
    for cid in missing:
        failures.append({"file": "result/invalid", "why": "no rejected example is refused by %s" % cid, "errors": []})
    return {"ok": not failures, "interface_version": 1, "plugin_version": validate.plugin_version(root),
            "counts": dict(counts, stop_tags=len(tags), stop_tags_with_an_example=len(seen_tags),
                           semantic_checks=len(validate.CHECK_IDS),
                           semantic_checks_with_an_example=len(seen_semantic)),
            "statuses": sorted(s for s in seen_status if s), "stop_tags": sorted(seen_tags),
            "failures": failures}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate-examples.py",
        description="Check every example under references/examples/ against its schema, both "
                    "directions, with a dropped-field pass and a coverage pass.",
        epilog="example:\n  uv run validate-examples.py --verbose\n\n"
               "side effects: none; it reads and writes nothing.\n"
               "exit: 0 every check held, 2 a usage slip, 3 the missing dependency, 4 a failure.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skill-root", metavar="DIR", default=None,
                        help="the directory holding SKILL.md (default: this script's own)")
    parser.add_argument("--verbose", action="store_true", help="one line per file on stderr")
    args = parser.parse_args(argv)
    try:
        report = check(args.skill_root, args.verbose)
    except (validate.SkillRootMissing, validate.ReferenceUnavailable) as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return exits.SUCCESS if report["ok"] else exits.VALIDATION


if __name__ == "__main__":
    sys.exit(main())
