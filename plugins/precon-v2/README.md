# precon-v2

Harvest an idea discussion into a fixed-format scope doc, every decided, assumed or parked line traced to the owner's words or an answered question, the doc placed and continued by script. Strictly user-invoked. The portable precon core of the skills v2 rebuild; the -v2 suffix stays while v1 precon is installed and both are renamed at cutover.

## Status

The frame (E14 slice 1) and the precon core (E14 slice 2, lane P). Built in lane P: the station's
procedure in `SKILL.md` (v1 precon's six steps and nine rules, each step naming the command it
runs); its lane contract, `references/precon-v2-contract.md`; its answer schema with valid and
invalid examples; the four phases the frame left as `phase-not-built` (`harvest`,
`record-answer`, `write`, `report`) and two commands of its own (`state`, the counted board;
`request`, the exit test's readers requests), in `scripts/precon_core/`; the input's `station`
fields (`home`, `date`) and the result's `station_result` with the core's four stop tags; the
lane's observer of the seeded cases, `evals/seeded-cases/lane_observe.py`; and both adapter
profiles filled. What stays for the join (slice 3): the four cores merged and the shared files
held equal across them, the end-to-end replay across the front of the loop, the interface-document
test, the version bump, and the marketplace entry. Interface version 1, plugin version 0.1.0.
Test counts are measured and filled in by the control room at close.

## Layout

```text
.claude-plugin/plugin.json           name precon-v2, version 0.1.0
skills/precon-v2/
  SKILL.md                           the portable procedure
  agents/openai.yaml                 the Codex sidecar (manual-only)
  references/
    precon-v2-contract.md            this station's own contract (lane P)
    station-loop.md                  the contract the four front cores share
    shared-files.txt                 the files identical in the four cores
    templates/                       the load-bearing forms, v1's byte for byte
    input.schema.json, answer.schema.json, result.schema.json
    examples/                        input/, answer/, result/: valid and invalid
  scripts/
    precon.py                        the phase driver: its hunts, phases and own commands
    precon_core/                     this station's library (phases, scope doc, rules, exit test, run)
    station_core/                    the shared library
    validate-examples.py, validate-result.py
    tests/                           the unittest suites (standard library)
  adapters/                          README.md, claude-code/, codex/ (each with its profile and tests)
setups/                              install, verify, negative tests and launch per harness
evals/seeded-cases/                  the seeded cases of this core's families, and lane_observe.py
```

## Tests

```sh
cd skills/precon-v2/scripts
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
