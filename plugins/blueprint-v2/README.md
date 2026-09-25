# blueprint-v2

Draft a build document in dependency-ordered, verifiable slices, every requirement traced and the load-bearing forms rendered by script, so build, signoff and recheck read what they read today. The portable blueprint core of the skills v2 rebuild; the -v2 suffix stays while v1 blueprint is installed and both are renamed at cutover.

## Status

The frame (E14 slice 1) and the station's core (E14 slice 2, lane L). The frame holds the shared
station loop, its library, the load-bearing templates, the shared schemas' base, the adapters and
setups for Claude Code and Codex, and the seeded cases of this core's families. Lane L built the
station on it: the portable procedure in `SKILL.md` (v1 blueprint's five steps and seven rules,
each step naming its command), the lane contract `references/blueprint-v2-contract.md`, the
recorded answer's schema and examples, the four lane phases (`harvest`, `record-answer`, `write`,
`report`) and one own command (`choose`, the owner's pick among several candidates) in
`scripts/blueprint_core/`, the scope hunt's homes in one tier (carried item C1-7), the stop tags
`no-build-doc`, `stale-harvest` and `unsafe-path`, the station's sections of both adapter profiles,
and `evals/seeded-cases/lane_observe.py` for the lane facts of L1 to L3. Records: none (E14-9).

Lane L's second round: a line may trace to the owner's words quoted; an out-of-scope line carries a
parked or deferred item forward and never an open one no answered question touched; dated names are
matched by their whole topic; a malformed poured-concrete or deferred section stops `harvest`
(`ledger-refused`); an extension drops nothing the answer carries; a `Status:` line in any case or
indent is protected; a criterion's check is one of the template's three forms.

Lane L's third round: the `Constraints:` line's items are compared per kind, so an open question
already written as an assumption or a constraint is still added as open; the view the shared
refusals read carries a requirement's words without their `R<n>` prefix and a line's without its
label; an open item carried out of scope in its own words, under any trace, is refused like one
carried by its id; a verify form names its test, its path or two words of steps; the architecture
doc's two sections are known by their exact headings; the hunts hold the v1 homes only (no undated
`<topic>.md` in the scope or architecture folder).

Lane L's fifth round (after the outside reviewer's lane look): every rendered build doc validates, so
an extension of a doc that fails its form stops `write-refused` with every finding named and nothing
written; the build hunt's first tier holds the undated `docs/plans/<topic>.md` beside the dated name
(an existing undated plan is extended where it lies, never forked); the shared refusals read each
answer line's original text, so a bare item label is part of the words when both sides carry one.

For the join: the version and the marketplace entry are the control room's at close. Interface
version 1, plugin version 0.1.0. Test counts are measured and filled in by the control room.

## Layout

```text
.claude-plugin/plugin.json           name blueprint-v2, version 0.1.0
skills/blueprint-v2/
  SKILL.md                           the portable procedure
  agents/openai.yaml                 the Codex sidecar
  references/
    blueprint-v2-contract.md         this core's lane contract
    station-loop.md                  the contract the four front cores share
    shared-files.txt                 the files identical in the four cores
    templates/                       the load-bearing forms, v1's byte for byte
    input.schema.json, result.schema.json, answer.schema.json
    examples/                        input/, result/, answer/ (valid and invalid)
  scripts/
    blueprint.py                     the phase driver: the hunt table, the phases, `choose`
    blueprint_core/                  this core's library: phases, checks, buildoc, harvest, readback
    station_core/                    the shared library
    validate-examples.py, validate-result.py
    tests/                           the unittest suites (standard library; bplib.py, test_bp_*.py and
                                     test_answer_examples.py are this core's own)
  adapters/                          README.md, claude-code/, codex/ (each with tests/test_profile.py)
setups/                              install, verify, negative tests and launch per harness
evals/seeded-cases/                  the seeded cases of this core's families, and lane_observe.py
```

## Tests

```sh
cd skills/blueprint-v2/scripts
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
