"""The check of the examples the tool ships (the A7a helper; the frame's RUN-1: the tool's own check of its
own schema files). `sun check-examples [--references DIR] [--verbose]`.

For each schema `<name>.schema.json` it reads `examples/<name>/valid/*.json`, each of which must pass, and
`examples/<name>/invalid/*.json`, each of which must fail. A schema this check cannot apply in full, or with
no accepted or no rejected example, is a failure. Its one document: `{"ok", "schemas", "valid", "invalid",
"failures"}`, which the command line prints inside its envelope (`interface_version`, `plugin_version`, `tool`,
`command`, `exit`; the contract's E16-15). Exit 0 when every example behaves, 4 when one does not, 2 on an unknown argument.
"""
import json
import os

from . import exits, jsoncheck, schemas


def check(root, verbose_lines=None):
    failures, counts = [], {"valid": 0, "invalid": 0}
    names = sorted(n[: -len(".schema.json")] for n in os.listdir(root) if n.endswith(".schema.json")) if os.path.isdir(root) else []
    if sorted(names) != sorted(schemas.NAMES):
        failures.append("the schemas in %s are not the %d this plugin freezes" % (os.path.basename(root), len(schemas.NAMES)))
    for name in names:
        try:
            with open(os.path.join(root, name + ".schema.json"), "rb") as fh:
                checker = jsoncheck.Checker(json.loads(fh.read().decode("utf-8")))
        except (OSError, ValueError):
            failures.append("%s: the schema does not load" % name)
            continue
        for kind in ("valid", "invalid"):
            folder = os.path.join(root, "examples", name, kind)
            files = sorted(f for f in os.listdir(folder) if f.endswith(".json")) if os.path.isdir(folder) else []
            if not files:
                failures.append("%s: no %s example" % (name, "accepted" if kind == "valid" else "rejected"))
            for entry in files:
                try:
                    with open(os.path.join(folder, entry), "rb") as fh:
                        document = json.loads(fh.read().decode("utf-8"))
                except (OSError, ValueError):
                    failures.append("%s/%s/%s: not JSON" % (name, kind, entry))
                    continue
                passes = not checker.errors(document)
                counts[kind] += 1
                if passes != (kind == "valid"):
                    failures.append("%s/%s/%s: %s" % (name, kind, entry, "rejected" if kind == "valid" else "accepted"))
                if verbose_lines is not None:
                    verbose_lines.append("%s/%s/%s: %s" % (name, kind, entry, "accepted" if passes else "rejected"))
    doc = {"ok": not failures, "schemas": len(names), "valid": counts["valid"], "invalid": counts["invalid"], "failures": failures}
    return doc, (exits.SUCCESS if not failures else exits.VALIDATION)
