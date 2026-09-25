# inspect-v2

Check a build doc before it is built: fresh inspectors read a packet built by script from the build doc, the scope doc and the code book alone; surviving findings are raised in the shared records and the plan is stamped with the model that inspected it. Strictly user-invoked. The portable inspect core of the skills v2 rebuild; the -v2 suffix stays while v1 inspect is installed and both are renamed at cutover.

## Status

Built in E14 slice 2, lane I, on the frame of slice 1. The station's procedure is in `SKILL.md`
(the ask, then gate and hunt, the lenses, verify and adjudicate, the verdict and the two writes, in
v1 inspect's order and under its ten rules) and its behavior in
`references/inspect-v2-contract.md`, which also states the review mechanics v1 took from signoff
by reference. Every phase of the driver is built (`harvest`, `record-answer`, `write`, `report`),
with four commands of the core's own (`named`, `choose`, `packet`, `request`); the recorded answer
has its schema (`references/answer.schema.json`) and examples; the seeded families I1 to I4 have
their lane facts through `evals/seeded-cases/lane_observe.py`; both adapter profiles are filled.
Surviving findings are raised through the records component's CLI; the station clears nothing.

Round 2 of the lane (the independent check's fourteen findings, under the control room's rulings
R1 to R8): a short fleet is named in the verdict mirror too; the outside raw copy is bannered at
`record-answer`, before any triage, stopped runs included; `hunted_and_held` and `bottom_line` are
required (v1 rule 10); an outside result the input never authorized is refused
(`unauthorized-send`); a finding whose citation matches nothing is refuted whatever its severity;
a doc the invocation names by path is taken with `named`; and the `mirrors` answer, the citation
rules, the stamp placement and the blank station fields as the check's replacement text says.

What stays for the join (slice 3): the full suites on the joined tree, the seven-station install
proof with inspect-v2 resolving blueprint-v2 by route 3b beside the real blueprint-v2 core (in this
lane route 3a finds the frame's skeleton `SKILL.md` of lane L), the end-to-end replay across the
front of the loop, the interface document for this plugin, and the owner's rulings on the open
points of the contract's section 15. Interface version 1, plugin version 0.1.0. Test counts are
measured and filled in by the control room at close.

## Layout

```text
.claude-plugin/plugin.json           name inspect-v2, version 0.1.0
skills/inspect-v2/
  SKILL.md                           the portable procedure
  agents/openai.yaml                 the Codex sidecar (manual-only)
  references/
    inspect-v2-contract.md           this core's contract: phases, commands, mandates, verify, writes, stops
    inspect-mandate.md               v1's outside mandate, byte for byte, filled by `request`
    station-loop.md                  the contract the four front cores share
    shared-files.txt                 the files identical in the four cores
    templates/                       the load-bearing forms, v1's byte for byte
    input.schema.json, answer.schema.json, result.schema.json, examples/
  scripts/
    inspect_v2.py                    the phase driver and this core's own commands
    inspect_core/                    this core's library: gate, packet, request, verify, answering, writing, reporting
    station_core/                    the shared library
    validate-examples.py, validate-result.py
    tests/                           the unittest suites (standard library)
  adapters/                          README.md, claude-code/, codex/ (each with its profile and tests)
setups/                              install, verify, negative tests and launch per harness
evals/seeded-cases/                  the seeded cases of this core's families, and lane_observe.py
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
