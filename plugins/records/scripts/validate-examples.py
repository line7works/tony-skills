#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema==4.25.1"]
# ///
"""Validate the records component's examples against its four schemas.

    uv run validate-examples.py [--component-root DIR] [--verbose]      (from any directory)

Resolves `references/` from the component root, which is this script's own location
(`scripts/..`) unless `--component-root` names another directory (test only).

Checks:

- every file under `references/examples/valid/` is one event that validates;
- every file under `references/examples/invalid/` is `{"reason": ..., "event": ...}` and the
  event is rejected, the reason saying which rule rejects it;
- every valid example still fails once any one of its required fields is dropped, so a
  `required` list that quietly stopped being enforced is caught here (the guide's "rerun both
  sets after tightening a schema");
- `references/examples/example.events.jsonl` walks clean: every line parses and validates, `seq`
  equals the line index, and every `prev` equals the hash of the line before (section 10);
- the same three checks for the other three schemas of section 1, whose examples live under
  `references/examples/<state | import-report | resolutions>/valid` and `/invalid`. An invalid
  example there is `{"reason": ..., "document": ...}`. The dropped-field pass takes the required
  list from the PIN below for the schema's top level and, where the schema is a `oneOf` over
  branches in `$defs`, for the one branch the example matches, so a branch that quietly stopped
  requiring a field is caught too;
- every `required` list of ALL FOUR schemas equals the list pinned in `SCHEMA_REQUIRED`, and
  each schema's `oneOf` branches are the ones pinned in `SCHEMA_BRANCHES`. The pins are literals
  written from the contract and `references/interface.md`; nothing here reads an obligation out
  of the schema it is checking, and a `required` list that nothing pins is itself a failure
  (carry item 3, amendment A11; send-back 1).

stdout: one JSON object {"ok", "valid": {"files", "failing"}, "invalid": {"total", "rejected"},
"mutations": {"total", "rejected"}, "log": {"lines", "ok"}, "documents": {<schema>: {...}},
"pins": {"schemas", "lists"}, "failures": [strings]} and nothing else. stderr: diagnostics; with
--verbose one line per check.

Exit status: 0 every check passed; 4 a check failed (the failures list names each, an example
that does not load included); 2 usage (an unknown argument, a --component-root that is not a
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
    p.add_argument("--component-root", metavar="DIR", default=None,
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


DOCUMENT_SCHEMAS = {"state": "state", "import-report": "import_report",
                    "resolutions": "resolutions"}


# ---- the pinned `required` lists of all four schemas (carry item 3; send-back 1, item 1) ------
#
# Contract sections 6 to 9, 11.5 and 12 and `references/interface.md`, written down here rather
# than read out of the schema under test. An obligation a checker reads from the thing it checks
# is no obligation: a `required` field removed from such a list removed the obligation to test
# it, and every mutation still passed.
#
# The first fix round pinned the event schema's top-level and per-kind lists (review finding 13,
# `CONTRACT_COMMON` and `CONTRACT_KIND_FIELDS` below). Carry item 3 (amendment A11) pinned the
# `state`, `import-report` and `resolutions` schemas, where 38 of 44 lists were blind. Send-back
# 1 pins what was left: every other `required` list of `event.schema.json` — `$defs/actor`,
# `$defs/origin`'s two branches, `$defs/identity`, `$defs/location` and its `more` items,
# `$defs/source`'s two branches, `$defs/resolution_answer`'s three, and the `if` clause of every
# `allOf` rule. No `required` list of any of the four schemas is read from the schema under test
# any more, and `check_pins` fails on one that is not pinned here.
#
# The key is a JSON pointer into the schema file: "" is the top level. Changing a list here is a
# change to the interface, not to a test.
SCHEMA_REQUIRED = {
    "event": {
        "": ("v", "seq", "prev", "kind", "at", "ledger_doc", "actor", "origin", "source"),
        "/$defs/actor": ("station", "run_id", "harness"),
        "/$defs/identity": (
            "commit", "dirty", "tracked_diff_sha256", "untracked", "untracked_sha256",
            "submodules",
        ),
        "/$defs/location": ("raw", "file", "line", "line_end", "tag", "more", "resolved"),
        "/$defs/location/allOf/0/if": ("resolved",),
        "/$defs/location/allOf/1/if": ("resolved",),
        "/$defs/location/allOf/1/then": ("file", "line"),
        "/$defs/location/properties/more/items": ("file", "line", "line_end", "tag"),
        "/$defs/origin/oneOf/0": ("kind",),
        "/$defs/origin/oneOf/1": (
            "kind", "doc", "doc_sha256", "line", "raw", "heading_line", "recorded_commit",
            "commit_named",
        ),
        "/$defs/resolution_answer/oneOf/0": ("finding",),
        "/$defs/resolution_answer/oneOf/1": ("new_finding",),
        "/$defs/resolution_answer/oneOf/2": ("skip", "why"),
        "/$defs/source/oneOf/0": ("known", "identity"),
        "/$defs/source/oneOf/1": ("known",),
        "/allOf/0/if": ("origin",),
        "/allOf/0/if/properties/origin": ("kind",),
        "/allOf/1/if": ("kind",),
        "/allOf/1/then": ("interface_version", "component_version"),
        "/allOf/10/if": ("kind",),
        "/allOf/10/then": ("doc_sha256", "lines_read", "counts"),
        "/allOf/11/if": ("kind",),
        "/allOf/11/then": ("doc_sha256", "lines_read", "counts"),
        "/allOf/12/if": ("kind",),
        "/allOf/12/then": ("line", "answer", "answered_by", "answered_on"),
        "/allOf/13/if": ("kind",),
        "/allOf/14/if": ("seq",),
        "/allOf/15/if": ("origin",),
        "/allOf/15/if/properties/origin": ("kind",),
        "/allOf/16/if": ("origin",),
        "/allOf/16/if/properties/origin": ("kind",),
        "/allOf/2/if": ("kind",),
        "/allOf/2/then": (
            "finding", "slice", "severity", "location", "claim", "scenario", "raised_by",
        ),
        "/allOf/3/if": ("kind",),
        "/allOf/3/then": (
            "finding", "slice", "severity", "location", "claim", "scenario", "raised_by",
            "caused_by",
        ),
        "/allOf/4/if": ("kind",),
        "/allOf/4/then": ("finding", "disposition", "how", "verified_source", "join_basis"),
        "/allOf/5/if": ("kind",),
        "/allOf/5/then": ("finding", "severity", "words", "grant_date", "verified_source"),
        "/allOf/6/if": ("kind",),
        "/allOf/6/then": ("finding", "words", "grant_date"),
        "/allOf/7/if": ("kind",),
        "/allOf/7/then": ("slice", "value", "card"),
        "/allOf/8/if": ("kind",),
        "/allOf/8/then": ("slice", "before", "after"),
        "/allOf/9/if": ("kind",),
        "/allOf/9/then": ("reason",),
    },
    "state": {
        "": (
            "interface_version", "component_version", "ok", "log", "head", "events", "exists",
            "spec", "findings", "slices", "open", "counts", "at_source", "filters",
        ),
        "/$defs/finding": (
            "id", "slice", "severity", "location", "claim", "scenario", "status",
            "cleared_unbound", "verified_source", "join_basis", "raised", "decided", "events",
            "raised_by", "caused_by",
        ),
        "/$defs/finding/allOf/0/if": ("status",),
        "/$defs/history": ("log", "seq"),
        "/$defs/identity": (
            "commit", "dirty", "tracked_diff_sha256", "untracked", "untracked_sha256",
            "submodules",
        ),
        "/$defs/location": ("raw", "file", "line", "line_end", "tag", "more", "resolved"),
        "/$defs/location/allOf/0/if": ("resolved",),
        "/$defs/location/allOf/1/if": ("resolved",),
        "/$defs/location/allOf/1/then": ("file", "line"),
        "/$defs/location/properties/more/items": ("file", "line", "line_end", "tag"),
        "/$defs/severity_counts": ("BLOCKER", "MAJOR", "MINOR"),
        "/$defs/slice": (
            "name", "open", "open_total", "card_derived", "card_observed", "card_observed_text",
            "card_drift",
        ),
        "/$defs/source/oneOf/0": ("known", "identity"),
        "/$defs/source/oneOf/1": ("known",),
        "/$defs/spec": ("doc", "slice"),
        "/properties/at_source/oneOf/0": ("commit",),
        "/properties/counts": ("findings", "open", "fixed", "waived", "cleared_unbound"),
        "/properties/filters": ("slice",),
    },
    "import_report": {
        "": ("interface_version", "component_version", "ok", "report"),
        "/$defs/ambiguity": ("line", "raw", "reason", "candidates"),
        "/$defs/ambiguity/properties/candidates/items": ("finding", "line", "slice"),
        "/$defs/duplicate_answers_refused": (
            "interface_version", "component_version", "ok", "report", "error", "reason", "doc",
            "log", "line", "answers",
        ),
        "/$defs/history": ("log", "seq"),
        "/$defs/import_ok": (
            "interface_version", "component_version", "ok", "report", "log", "doc", "doc_sha256",
            "dry_run", "run_id", "lines_read", "lines_classified", "previously_imported",
            "blocks", "slices", "counts", "imported", "would_import", "ambiguous", "ambiguities",
            "rejected_resolutions", "spec", "opened_log", "head", "events",
        ),
        "/$defs/import_ok/allOf/0/else": ("appended",),
        "/$defs/import_ok/allOf/0/if": ("dry_run",),
        "/$defs/import_ok/allOf/0/then/not": ("appended",),
        "/$defs/import_ok/properties/appended/items": ("seq", "kind", "finding", "history"),
        "/$defs/import_ok/properties/broke_lock": ("pid", "pid_start"),
        "/$defs/import_refused": (
            "interface_version", "component_version", "ok", "report", "error", "reason", "log",
            "doc", "head", "events", "dry_run", "counts", "lines_read", "lines_classified",
            "spec", "ambiguities",
        ),
        "/$defs/import_refused/allOf/0/if": ("error",),
        "/$defs/import_refused/allOf/0/then": ("rejected_resolutions",),
        "/$defs/rejection": ("line", "why", "reason", "answer"),
        "/$defs/resolutions_file_refused": (
            "interface_version", "component_version", "ok", "report", "error", "reason", "doc",
            "log",
        ),
        "/$defs/resolutions_file_refused/properties/errors/items": ("path", "message"),
        "/$defs/spec": ("doc", "slice"),
        "/$defs/survey": (
            "interface_version", "component_version", "ok", "report", "workspace", "documents",
            "counts", "total", "returned", "offset", "truncated",
        ),
        "/$defs/survey/properties/counts": (
            "documents", "ledger_documents", "mirrors", "blocks", "records", "stops",
            "documents_that_would_stop",
        ),
        "/$defs/survey_document": (
            "doc", "role", "doc_sha256", "lines", "blocks", "slices", "records", "join_basis",
            "stops", "ambiguous",
        ),
        "/$defs/survey_document/allOf/0/else": ("events", "event_counts"),
        "/$defs/survey_document/allOf/0/if": ("role",),
        "/$defs/survey_document/allOf/0/then/not": ("events",),
    },
    "resolutions": {
        "": ("answered_by", "answered_on", "answers"),
        "/$defs/answer": ("line", "raw"),
        "/$defs/answer/oneOf/0": ("finding",),
        "/$defs/answer/oneOf/1": ("new_finding",),
        "/$defs/answer/oneOf/2": ("skip", "why"),
    },
}

# Which branch of a `oneOf` a document is held to, by the field values that tell the shapes
# apart (`import-report.schema.json` is the one schema with branches). Pinned for the same
# reason the lists are: a branch discriminator read out of the schema proves nothing about it.
SCHEMA_BRANCHES = {
    "import_report": (
        ("/$defs/import_ok", (("report", "import"), ("ok", True))),
        ("/$defs/import_refused", (("report", "import"), ("ok", False))),
        ("/$defs/duplicate_answers_refused",
         (("report", "import"), ("ok", False), ("error", "invalid"))),
        ("/$defs/resolutions_file_refused",
         (("report", "import"), ("ok", False), ("error", "invalid"))),
        ("/$defs/survey", (("report", "survey"), ("ok", True))),
    ),
}


def required_lists(schema):
    """Every `required` list in a schema, by JSON pointer, arrays inside `$defs` included."""
    found = {}

    def walk(node, pointer):
        if isinstance(node, dict):
            if isinstance(node.get("required"), list):
                found[pointer] = list(node["required"])
            for key, value in node.items():
                walk(value, pointer + "/" + key.replace("~", "~0").replace("/", "~1"))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, pointer + "/" + str(index))

    walk(schema, "")
    return found


def check_pins(schemas, verbose):
    """Hold each schema's `required` lists and `oneOf` branches to the pins above."""
    failures = []
    counted = 0
    for key in sorted(SCHEMA_REQUIRED):
        name = validate.SCHEMA_FILES[key]
        live = required_lists(schemas.docs[key])
        pinned = SCHEMA_REQUIRED[key]
        counted += len(pinned)
        for pointer in sorted(set(live) | set(pinned)):
            where = "%s at %s" % (name, pointer or "the top level")
            if pointer not in pinned:
                failures.append("%s: a `required` list nothing pins" % where)
            elif pointer not in live:
                failures.append("%s: the pinned `required` list is gone" % where)
            elif list(pinned[pointer]) != live[pointer]:
                failures.append("%s: reads %s; the contract pins %s"
                                % (where, live[pointer], list(pinned[pointer])))
            else:
                log(verbose, "PINNED   %s" % where)
        branches = [entry.get("$ref") for entry in schemas.docs[key].get("oneOf", [])]
        expected = ["#/$defs/" + pointer[len("/$defs/"):]
                    for pointer, _ in SCHEMA_BRANCHES.get(key, ())]
        if sorted(b for b in branches if b) != sorted(expected):
            failures.append("%s: its oneOf branches are %s; the pins name %s"
                            % (name, branches, expected))
    return counted, failures



def branch_required(key, doc):
    """The required lists this document is held to: the top level's, plus its matched branch's.

    Both come from `SCHEMA_REQUIRED`, never from the schema being checked. A schema whose top
    level is a `oneOf` over `$defs` branches (import-report.schema.json) says nothing useful at
    the top about a document's own shape; the branch does, and `SCHEMA_BRANCHES` pins which
    field values pick which branch.
    """
    pins = SCHEMA_REQUIRED[key]
    out = set(pins.get("", ()))
    for pointer, discriminators in SCHEMA_BRANCHES.get(key, ()):
        if all(doc.get(name) == value for name, value in discriminators):
            out.update(pins.get(pointer, ()))
    return sorted(out)


def check_documents(key, folder, root, schemas, verbose):
    """The valid / invalid / dropped-field passes for one of the three document schemas."""
    base = os.path.join(root, "references", "examples", folder)
    failures = []
    valid_files = files_in(os.path.join(base, "valid"))
    failing = mutations = rejected_mutations = 0
    for path in valid_files:
        name = os.path.relpath(path, os.path.join(root, "references", "examples"))
        try:
            doc = load(path)
        except (OSError, ValueError) as exc:
            failures.append("%s: %s" % (name, exc))
            failing += 1
            continue
        errors = validate.validate_document(key, doc, schemas)
        if errors:
            failing += 1
            failures.append("%s: %s %s" % (name, errors[0]["path"] or "/", errors[0]["message"]))
            log(verbose, "FAIL     %s" % name)
        else:
            log(verbose, "PASS     %s" % name)
        for field in branch_required(key, doc):
            if not isinstance(doc, dict) or field not in doc:
                continue
            mutated = copy.deepcopy(doc)
            mutated.pop(field)
            mutations += 1
            if validate.validate_document(key, mutated, schemas):
                rejected_mutations += 1
                log(verbose, "REJECTED %s without /%s" % (name, field))
            else:
                failures.append("%s: dropping /%s is still accepted" % (name, field))
                log(verbose, "ACCEPTED (BUG) %s without /%s" % (name, field))
    invalid_files = files_in(os.path.join(base, "invalid"))
    rejected = 0
    for path in invalid_files:
        name = os.path.relpath(path, os.path.join(root, "references", "examples"))
        try:
            entry = load(path)
            reason, doc = entry["reason"], entry["document"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            failures.append("%s: %s" % (name, exc))
            continue
        if not isinstance(reason, str) or not reason.strip():
            failures.append("%s: an invalid example says which rule rejects it" % name)
        if validate.validate_document(key, doc, schemas):
            rejected += 1
            log(verbose, "REJECTED %s" % name)
        else:
            failures.append("%s: accepted, though it must be rejected (%s)" % (name, reason))
            log(verbose, "ACCEPTED (BUG) %s" % name)
    return {
        "valid": {"files": len(valid_files), "failing": failing},
        "invalid": {"total": len(invalid_files), "rejected": rejected},
        "mutations": {"total": mutations, "rejected": rejected_mutations},
    }, failures


# Contract section 6.2, written down here rather than read out of the schema under test. The
# outside review's finding 13: this list used to be derived from `event.schema.json`, so
# removing a field from that schema's `required` list removed the obligation to test it and all
# 227 mutations still passed. An obligation a test reads from the thing it tests is no
# obligation. Changing either of these lists is a change to the interface, not to a test.
CONTRACT_COMMON = ("v", "seq", "prev", "kind", "at", "ledger_doc", "actor", "origin", "source")
CONTRACT_KIND_FIELDS = {
    "log_opened": ("interface_version", "component_version"),
    "finding_raised": ("finding", "slice", "severity", "location", "claim", "scenario", "raised_by"),
    "defect_raised": ("finding", "slice", "severity", "location", "claim", "scenario",
                      "raised_by", "caused_by"),
    "disposition": ("finding", "disposition", "how", "verified_source", "join_basis"),
    "waived": ("finding", "severity", "words", "grant_date", "verified_source"),
    "reopened": ("finding", "words", "grant_date"),
    "card_observed": ("slice", "value", "card"),
    "card_set": ("slice", "before", "after"),
    "legacy_unparsed": ("reason",),
    "import_started": ("doc_sha256", "lines_read", "counts"),
    "import_finished": ("doc_sha256", "lines_read", "counts"),
    "resolution_applied": ("line", "answer", "answered_by", "answered_on"),
}


def required_fields(event, schemas):
    """The fields section 6.2 requires of this event: the common list plus its kind's own."""
    kind = event.get("kind")
    if kind not in CONTRACT_KIND_FIELDS:
        raise KeyError("no contract field list for event kind %r" % (kind,))
    return sorted(set(CONTRACT_COMMON) | set(CONTRACT_KIND_FIELDS[kind]))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    validate.require_jsonschema()
    try:
        root = validate.component_root(args.component_root)
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

    pinned_lists, pin_failures = check_pins(schemas, args.verbose)
    failures.extend(pin_failures)

    documents = {}
    for folder, key in sorted(DOCUMENT_SCHEMAS.items()):
        summary, more = check_documents(key, folder, root, schemas, args.verbose)
        documents[folder] = summary
        failures.extend(more)

    out = {
        "ok": not failures,
        "documents": documents,
        "pins": {"schemas": len(SCHEMA_REQUIRED), "lists": pinned_lists},
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
