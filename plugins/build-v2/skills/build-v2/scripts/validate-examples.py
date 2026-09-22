#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""Check every example under `references/examples/` against its schema.

    uv run validate-examples.py [--skill-root DIR] [--verbose]

Four passes, so a schema that drifts from what this core actually writes fails here rather than
in a run:

1. **Accepted.** Every file under `<kind>/valid/` validates against `<kind>.schema.json`. A
   result example additionally passes the semantic checks, unless its name starts with
   `semantic-`, which marks a file that is schema-valid on purpose.
2. **Rejected.** Every file under `<kind>/invalid/` is refused. A `semantic-` file must be
   refused by a SEMANTIC check and pass the schema; every other file must be refused by the
   schema. A file refused by the wrong one is a failure, so "it is rejected" never passes for
   the wrong reason.
3. **Dropped field.** Every required field of every accepted example is dropped in turn and the
   result must be refused. A required field the schema does not actually require is caught here.
4. **Coverage.** Every status of the result schema's enum, every stop tag this core can emit,
   and every semantic check id has at least one example; a legitimate outcome with no accepted
   example is a failure, which is the guide's rule for schemas. The tag list comes from
   `build_core.result.STOP_TAGS`, and the schema's published list is held to it in the same pass,
   so a tag the code can emit and the schema does not describe fails here.

stdout: one JSON document. stderr: the per-file lines under `--verbose`.
Exit 0 everything held, 2 an unknown argument, 3 the missing dependency, 4 any check failed.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_core import exits, result as resultmod, validate  # noqa: E402

KINDS = ("input", "answer", "result", "receipt", "checkpoint")
SEMANTIC_PREFIX = "semantic-"


def files_in(folder):
    if not os.path.isdir(folder):
        return []
    return [os.path.join(folder, name) for name in sorted(os.listdir(folder))
            if name.endswith(".json")]


def read(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def required_fields(schema, document):
    """The top-level required fields the document actually carries."""
    return [name for name in schema.get("required") or [] if name in document]


def check(root, verbose):
    schemas = validate.load_schemas(root)
    examples = os.path.join(validate.references_dir(root), "examples")
    failures = []
    counts = {"accepted": 0, "rejected": 0, "dropped": 0}
    seen_status, seen_tags, seen_semantic = set(), set(), set()

    def note(line):
        if verbose:
            sys.stderr.write(line + "\n")

    for kind in KINDS:
        schema = schemas[kind]
        folder = os.path.join(examples, kind)
        if not os.path.isdir(folder):
            continue

        for path in files_in(os.path.join(folder, "valid")):
            document = read(path)
            errors = validate.errors_for(document, schema)
            counts["accepted"] += 1
            if errors:
                failures.append({"file": os.path.relpath(path, examples), "why": "accepted example refused",
                                 "errors": errors[:4]})
                note("REFUSED  %s" % path)
                continue
            note("ok       %s" % path)
            if kind == "result":
                seen_status.add(document.get("status"))
                if document.get("stop_tag"):
                    seen_tags.add(document["stop_tag"])
                semantic = validate.run_semantic(document, None, None)["semantic"]
                if semantic:
                    failures.append({"file": os.path.relpath(path, examples),
                                     "why": "accepted result failed a semantic check",
                                     "errors": semantic[:4]})

            # pass 3: every required field it carries is actually required
            for field in required_fields(schema, document):
                dropped = copy.deepcopy(document)
                del dropped[field]
                counts["dropped"] += 1
                if not validate.errors_for(dropped, schema):
                    failures.append({"file": os.path.relpath(path, examples),
                                     "why": "dropping the required field %r was accepted" % field,
                                     "errors": []})

        for path in files_in(os.path.join(folder, "invalid")):
            document = read(path)
            errors = validate.errors_for(document, schema)
            counts["rejected"] += 1
            semantic = []
            if kind == "result":
                semantic = validate.run_semantic(document, None, None)["semantic"]
                for finding in semantic:
                    seen_semantic.add(finding["id"])
            wants_semantic = os.path.basename(path).startswith(SEMANTIC_PREFIX)
            if wants_semantic:
                if errors:
                    failures.append({"file": os.path.relpath(path, examples),
                                     "why": "a semantic example was refused by the schema instead",
                                     "errors": errors[:4]})
                elif not semantic:
                    failures.append({"file": os.path.relpath(path, examples),
                                     "why": "a semantic example was accepted by every check",
                                     "errors": []})
                else:
                    note("refused  %s (%s)" % (path, semantic[0]["id"]))
            elif not errors:
                failures.append({"file": os.path.relpath(path, examples),
                                 "why": "a rejected example was accepted by the schema", "errors": []})
                note("ACCEPTED %s" % path)
            else:
                note("refused  %s" % path)

    # pass 4: coverage
    result_schema = schemas["result"]
    for status in result_schema["properties"]["status"]["enum"]:
        if status not in seen_status:
            failures.append({"file": "result/valid", "why": "no accepted example ends as %r" % status,
                             "errors": []})
    described_tags = [tag.strip("`") for tag in
                      result_schema["properties"]["stop_tag"]["description"].split("`")[1::2]]
    for tag in resultmod.STOP_TAGS:
        if tag not in described_tags:
            failures.append({"file": "references/result.schema.json",
                             "why": "the schema does not describe the stop tag %r, which this core "
                                    "can emit" % tag, "errors": []})
        if tag not in seen_tags:
            failures.append({"file": "result/valid", "why": "no accepted example stops with the tag "
                                                            "%r" % tag, "errors": []})
    for tag in described_tags:
        if tag not in resultmod.STOP_TAGS:
            failures.append({"file": "references/result.schema.json",
                             "why": "the schema describes the stop tag %r, which this core never "
                                    "emits" % tag, "errors": []})
    missing_semantic = [cid for cid in validate.CHECK_IDS if cid not in seen_semantic]
    for cid in missing_semantic:
        failures.append({"file": "result/invalid",
                         "why": "no rejected example is refused by the semantic check %s" % cid,
                         "errors": []})

    return {
        "ok": not failures,
        "interface_version": 1,
        "plugin_version": validate.plugin_version(root),
        "counts": dict(counts, stop_tags=len(resultmod.STOP_TAGS),
                       stop_tags_described=len(described_tags),
                       stop_tags_with_an_example=len(seen_tags),
                       semantic_checks=len(validate.CHECK_IDS),
                       semantic_checks_with_an_example=len(seen_semantic)),
        "statuses": sorted(s for s in seen_status if s),
        "stop_tags": sorted(seen_tags),
        "semantic_checks_without_an_example": missing_semantic,
        "failures": failures,
    }


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
    except validate.SkillRootMissing as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    except validate.ReferenceUnavailable as exc:
        sys.stderr.write("%s\n" % exc)
        return exits.USAGE
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return exits.SUCCESS if report["ok"] else exits.VALIDATION


if __name__ == "__main__":
    sys.exit(main())
