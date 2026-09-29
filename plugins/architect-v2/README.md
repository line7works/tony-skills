# architect-v2

One interview after precon that writes the one living architecture doc and renders its visual, with the scope doc's decided lines passed forward by script, never re-asked, and the run log continued, never rewritten. Strictly user-invoked. The portable architect core of the skills v2 rebuild; the -v2 suffix stays while v1 architect is installed and both are renamed at cutover.

## Status

The frame (E14 slice 1) and the architect core (E14 slice 2, lane A). Built in lane A: the
station's procedure in `SKILL.md` (v1's six steps and eleven rules, each step naming its command);
its lane contract `references/architect-v2-contract.md`; the recorded answer's schema
`references/answer.schema.json` with accepted and rejected examples; the four phases `harvest`,
`record-answer`, `write` and `report` and four own commands, `render-visual`, `record-publish`,
`request` and `save-take` (`scripts/architect_core/`); the result's `station_result` and three own
stop tags (`living-doc-malformed`, `document-changed`, `review-pending`); the lane observer
`evals/seeded-cases/lane_observe.py` for the A2 and A4 lane steps; the adapter profiles' lane
sections. It writes no event and never opens the records component (ruling E14-9).

Slices 3a and 3b (the join's first two steps): answer lines name their ledger row by its id and
deferred rows pass forward by it; the readers roster is found by the shared resolver; the write
guards refuse a folder or a file planted where the run writes, before anything is written; a scope
doc that is not UTF-8 stops `ledger-refused`, named with its decoding error; and every read of the
run directory (the requests, the written doc, a doc unreadable at harvest) stops on a hand-planted
node instead of failing.

Slice 3c (the join, its first hand-back): the contract's section 19, Interface, states the CLI in
build-v2's four tables (commands with their arguments and exit codes, result statuses, invocation
fields, run-directory artifacts), and `scripts/tests/test_interface_document.py` reads them against
the parser, the dispatch table, the schemas and the source, with a mutation proof; the shared hunt
lists a candidate as its folder spells it, so `select` and every later use of a candidate carry the
disk spelling on a case-insensitive disk; and the plugin has its marketplace entry.

Slice 3c's second hand-back: `setups/manual-only.sh` installs the manual-only probe
(`setups/_fixtures/`, recheck-v2's E9 probe) beside this core and checks both carry the manual-only
controls; the two prompts per harness are in `setups/<harness>/prompts/`; the live measurement is
the control room's.

Interface version 1, plugin version 0.1.1. Tests: <COUNT>.

## Layout

```text
.claude-plugin/plugin.json           name architect-v2, version 0.1.1
skills/architect-v2/
  SKILL.md                           the portable procedure
  agents/openai.yaml                 the Codex sidecar (manual-only)
  references/
    architect-v2-contract.md         this core's contract: commands, answer, refusals, stops
    station-loop.md                  the contract the four front cores share
    shared-files.txt                 the files identical in the four cores
    templates/                       the load-bearing forms, v1's byte for byte
    input.schema.json, result.schema.json, answer.schema.json
    examples/                        input/, result/, answer/ (valid and invalid, answer's context)
  scripts/
    architect.py                     the phase driver: its hunts, phases and own commands
    architect_core/                  this core's library (phases, answer checks, doc, visual, review)
    station_core/                    the shared library
    validate-examples.py, validate-result.py
    tests/                           the unittest suites (standard library)
  adapters/                          README.md, claude-code/, codex/
setups/                              install, verify, negative tests and launch per harness
evals/seeded-cases/                  the seeded cases of this core's families, and lane_observe.py
```

## Tests

```sh
cd skills/architect-v2/scripts
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
