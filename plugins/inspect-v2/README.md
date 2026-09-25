# inspect-v2

Check a build doc before it is built: fresh inspectors read a packet built by script from the build doc, the scope doc and the code book alone; surviving findings are raised in the shared records and the plan is stamped with the model that inspected it. Strictly user-invoked. The portable inspect core of the skills v2 rebuild; the -v2 suffix stays while v1 inspect is installed and both are renamed at cutover.

## Status

The frame only (E14 slice 1). This plugin holds the shared station loop, its library, the load-
bearing templates, the schemas and examples of the shared fields, the phase driver with
`check-input`, `select`, `identity` and `skill-identity` working, the adapters and setups for Claude
Code and Codex, and the seeded cases of its families. The station's own procedure (`harvest`,
`record-answer`, `write`, `report` and the steps of `SKILL.md`) lands in its slice 2 lane (lane
I); until then those four phases stop as `phase-not-built`. Interface version 1, plugin
version 0.1.0. Test counts are measured and filled in by the control room at close.

## Layout

```text
.claude-plugin/plugin.json           name inspect-v2, version 0.1.0
skills/inspect-v2/
  SKILL.md                           the portable procedure (a skeleton until slice 2)
  agents/openai.yaml                 the Codex sidecar
  references/
    station-loop.md                  the contract the four front cores share
    shared-files.txt                 the files identical in the four cores
    templates/                       the load-bearing forms, v1's byte for byte
    input.schema.json, result.schema.json, examples/
  scripts/
    inspect_v2.py                     the phase driver
    station_core/                    the shared library
    validate-examples.py, validate-result.py
    tests/                           the unittest suites (standard library)
  adapters/                          README.md, claude-code/, codex/
setups/                              install, verify, negative tests and launch per harness
evals/seeded-cases/                  the seeded cases of this core's families
```

## Tests

```sh
cd skills/inspect-v2/scripts
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t tests
uv run validate-examples.py
cd ../adapters
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s claude-code/tests -t claude-code/tests
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s codex/tests -t codex/tests
```

Every suite builds its fixtures in a temporary directory and removes them, writes nothing into the
repository, and needs no network. `scripts/tests/test_shared_equal.py` holds the shared files equal
to precon-v2's copy (skipped, and reported as skipped, in the installed shape);
`scripts/tests/test_no_v1_import.py` fails on any reference to a v1 station.
