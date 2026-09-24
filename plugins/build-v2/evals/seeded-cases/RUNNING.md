# Running the seeded cases against this core

The cases themselves — `README.md`, `_lib/`, `B1-scope-adherence/` and `B2-honest-failure/` — are
the slice 0 writer's, copied here unchanged. This file and `observe.py` are lane B's. A case, an
answer or a generator is never edited by this lane: a case believed wrong is a question to the
control room, with the case id and what was observed.

## The one command

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --all --out /tmp/observe
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --case B2-05-report-only --out /tmp/observe
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --list
```

Each case is built by its own family's `build.py` into `--out`, then driven through the REAL CLI:

```text
build.py check-input <core-input.json>     the seeded input translated into this core's schema
build.py contract     --run-dir <case>/run
build.py preflight    --run-dir <case>/run
build.py record-answer --run-dir <case>/run --answer <case>/answer.json
build.py report       --run-dir <case>/run
```

and `observed.json` is written beside the case. The run stops early when a phase delivers a
terminal status (exit 10); `_phases` in the observation records every phase and its exit code.

`observe.py` needs the records component, the way any run of this core does: it is found beside
this plugin, or wherever `RECORDS_ROOT` points.

## What `observed.json` holds

The neutral vocabulary of the cases' `README.md`, and only the names this core has a fact for:

| Name | Where it comes from |
|---|---|
| `base_ref` | the ref the run reports as the slice's base |
| `source_set_committed` / `_changed` / `_untracked` | the three lists, sorted |
| `out_of_scope_paths` | the source-set paths the run listed as outside the slice's named paths |
| `checks_passed` / `_failing` / `_skipped` / `_not_passed` | the checks the SLICE names, by result |
| `check_output_contains` | per check name, the output the run reported for it, in full |
| `card_after` | the slice's `Status:` text after the run, read from the DOCUMENT by this script |
| `terminal_status` | `completion` or `stop` |
| `answer_refused` | true when the run did not accept the recorded answer |
| `refusal_reason` | the tag when it refused: `answer_invalid` |
| `writes_none` | a digest over the whole workspace, the records log included, before and after |

Names this core has no fact for — every signoff name, and the key's own word `either` — are
omitted, never guessed. Keys beginning with `_` are the observer's own bookkeeping (`_case`,
`_result`, `_phases`), not assertion names.

Two values are measured by `observe.py` rather than read out of the core's result, so the
observation is an outside one: `card_after` is read from the build doc's `Status:` line by this
script's own reader, and `writes_none` is a tree digest taken before and after the run. `.git` is
left out of that digest: git's own bookkeeping is not a write of this core, and nothing here runs
a git command that changes a repository.

## What is NOT here

**No expected value.** This lane never saw the answer key, so it could not write one, and
`scripts/tests/test_seeded_cases.py` reads every shipped file of the plugin and fails when a
comparison against a case id appears. The control room grades `observed.json` for all nine cases
against the key and reports pass or fail per case with the assertion NAME that failed.

The suite's own assertions are only what the lane contract guarantees for EVERY run: a terminal
status exists, the source set has three lists and a base, the result validates against its schema
and the semantic checks, the report-only case wrote nothing, and a refused answer is neither acted
on nor repaired.

## Determinism

Two builds of one case produce the same commit hashes and the same tree, and two observations of
one case produce the same facts; `TheObserverIsDeterministic` in the suite runs a case twice and
compares. The only bytes that differ between two output directories are the absolute paths inside
the inputs, which the cases' own `tree_sha256` normalizes.
