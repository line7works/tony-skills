# build-v2

The portable build core of the skills v2 rebuild: one slice of a build doc, made true, inside the
scope the slice draws, with plain reporting when something did not pass. Same procedure on every
harness — one portable body plus a small adapter per harness (slice 3).

It keeps v1 build's five steps and its rules unchanged (E13 lane contract ruling E13-1). What the
portable core adds is that the scope, the checks and the card stop being things a model asserts
and become things a script computes: the source set comes from git, a path outside the slice's
named paths is reported with the executor's stated reason or the run stops, a failing or skipped
check is reported with its output and the card does not move, and the one card move the station
makes is an event in the shared records component.

Names carry the `-v2` suffix (plugin and skill) while v1 `build` stays installed; both are renamed
at cutover.

## Status

Interface version 1, plugin version 0.1.0. Built in E13 slice 2, lane B, against the lane
contract `docs/plans/2026-09-21-stations-e13.md` sections 8 and 9 with amendments A1 to A3.

**The records component is a dependency.** Without it every command that needs it exits 3 with one
line on stderr naming where it looked; `--help` and argument checking still work. It is found
through `--records-root`, `RECORDS_ROOT`, the component beside this plugin, or the installed shape
below it, and the pick is confirmed with `component-identity` at interface version 1.

**The records wiring is copied, not reinvented.** `skills/build-v2/scripts/build_core/records_client.py`
is the qualified recheck pilot's `recheck_core/records_client.py` byte for byte below a header
naming its origin and the commit it was taken from; `scripts/tests/test_records_client.py`
compares the two files and fails when they differ. Two constants in the copy belong to the pilot
(`STATION`, `NO_RECORDS_HOOK`) and are never read here; `build_core/records_link.py` carries this
station's own.

**What build asks the records for** (the records assessment, lane contract section 9: question 2
yes, questions 1 and 3 no): the read commands and ONE card event. Build raises nothing and clears
nothing.

**Not here yet.** `adapters/` and `setups/` are slice 3's, and the seam is left open: nothing in
`SKILL.md` or in the scripts is harness-specific and no adapter is named.

## Layout

```text
plugins/build-v2/
  .claude-plugin/plugin.json          # name build-v2, version 0.1.0
  README.md                           # this file
  skills/build-v2/
    SKILL.md                          # the portable procedure the executor follows
    references/
      build-contract.md               # what each phase does, the authorized writes, the stops
      input.schema.json               # the one validated input structure
      answer.schema.json              # the recorded executor answer
      result.schema.json              # the one result
      receipt.schema.json             # the card transaction
      checkpoint.schema.json          # what a run carries between its phases
      examples/                       # accepted and rejected examples of each, with the stops
    scripts/
      build.py                        # the phase driver: check-input, contract, preflight,
                                      #   record-answer, report, identity, skill-identity
      build_core/                     # the library the CLI imports (internal, not the interface)
      validate-examples.py            # every example against its schema, both directions
      validate-result.py              # one result against its schema and the semantic checks
      tests/                          # the unittest suites (standard library)
  evals/
    seeded-cases/                     # the slice 0 cases, copied unchanged, plus observe.py
```

## Running it

```sh
uv run skills/build-v2/scripts/build.py --help
uv run skills/build-v2/scripts/build.py check-input /tmp/build-c-20260922-7f3c/input.json
```

`jsonschema==4.25.1` is the one dependency, declared in each script's PEP 723 block and supplied
by `uv run`. Started without it, a command that validates something exits 3 with one line on
stderr and nothing on stdout; `--help` and argument checking still work. The runtime floor is
Python 3.9 (`/usr/bin/python3` 3.9.6) and git 2.50.1. Git runs read-only, and only inside the
workspace it is pointed at.

**What it writes.** The run's own artifacts under the run directory (outside the workspace); ONE
`card_set` event through the records component, which writes only under `docs/records/`; and the
slice's `Status:` line in the build doc when the card moves. Nothing else. A report-only run
writes none of the last two and says so. `references/build-contract.md` section 11 is the
complete list.

## Tests

```sh
cd skills/build-v2/scripts
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t tests
uv run validate-examples.py
```

The suite builds every fixture into a temporary directory and removes it, writes nothing into the
repository, and needs no network. It reaches the records component of this checkout through the
resolver's own route 3a, and injects faults through a stand-in `records.py` handed to the resolver
as `RECORDS_ROOT`, so what the transaction tests measure is a real log and real refusals.

`BUILD_TEST_SCRATCH` names the directory fixtures are built under, when it is set.

## The seeded cases

`evals/seeded-cases/` holds the two build families of the E13 seeded cases — `B1-scope-adherence`
and `B2-honest-failure` — copied from the slice 0 writer unchanged, with their generators, their
`CASES.md` and their recorded answers. `evals/seeded-cases/observe.py` builds each case, drives
this core through its real CLI, and writes an `observed.json` of FACTS under the neutral
vocabulary of the cases' `README.md`.

**No expected value appears anywhere in this plugin.** The outcome of each case lives in an answer
key this lane never saw, and the control room grades the observations against it;
`scripts/tests/test_seeded_cases.py` asserts only what the lane contract guarantees for every run
and additionally reads every shipped file to fail when a comparison against a case id appears.

`evals/seeded-cases/RUNNING.md` is how to run them.

## Known open points

- **The importer recognises this station's own lines** (E13 amendment A4). A `Status:` line this
  core wrote, and every record line `render` produced, are recognised by their bytes as lines the
  log already records natively: the component counts them under `native_rendered` and imports
  nothing for them. So a second build run on one document levels with `would_import` 0, reads the
  card where the first run left it, and no phantom `card_observed` is appended for the line the
  first run wrote. `scripts/tests/test_a4_second_run.py` measures that against the real component
  and, for the same scenario, RED against the component as it stood before A4 (extracted read-only
  from history), so "A4 is what makes this pass" is a measurement rather than a claim.

  A4 also moved a seam of this core, and the move is worth knowing about: the card-drift rule used
  to be an ORDERING test (the last `card_set` sitting after every `card_observed` for the slice),
  which held only because the pre-A4 importer appended nothing in the split state. A4 made it
  append an observation there, and the ordering read the document as the newer truth and passed a
  split. The rule is now a comparison of facts — drift iff the last `card_set`'s `after` differs
  from the document's card AND the document's card is that event's `before` — which needs no
  import to have happened and cannot be moved by a change in that policy.

- **The importer reads a hand-written record more loosely than this core does** (E13 amendment A3
  item 3; the slice 1 builder's Findings 2 and 3). Since the slice 2 fix round (Astra's F12) this
  core runs Appendix A's stop check, unchanged, before any levelling: `build_core/record_grammar.py`
  is the recheck pilot's `recheck_core/ledger.py` byte for byte (a test holds the two equal), used
  as an ambiguity detector and never as a source of records. A line it cannot place stops the run
  `legacy_unplaced` with the document, the line and its bytes. After it, the core still stops on
  ANY importer signal. It changes nothing in `plugins/records/`.

## The slice 2 fix round (Astra's review, amendment A6)

What changed in behaviour, each with its tests in `scripts/tests/test_fix2_astra.py`:

- **F1** `report` recomputes the source set against the base commit preflight pinned, after any
  rerun and before the scope decision; the card event carries the identity of THAT set, and a
  settling pass re-delivers it without rerunning a check.
- **F2** a requested rerun that cannot execute is `not_run` (claim kept in `recorded_result` and
  `recorded_output`); an answer's check run under another command is `not_run`
  (`attribution_refused`); a `passed` with a nonzero exit refuses the answer (rule R6).
- **F11** a card already at `built` is not moved again: no transaction, no event, no line.
- **F12** the Appendix A stop check before any levelling (above).
- **F14** only literal leading `./` is stripped before the scope comparison; `.config.env` is not
  `config.env`.
- **F15** a refused answer launches no check; report-only reruns nothing in the live workspace;
  a rerun that changed the workspace sets `checks_changed_workspace` and never `wrote_nothing`.
- **The ledger document is sanctioned, not excluded.** It stays in the source set, so a reader
  sees that the build doc changed, and the scope comparison passes over it because the loop writes
  into it by design; `source_set.sanctioned` publishes it with its reason.
  `references/build-contract.md` sections 5 and 18 carry the reasoning.
