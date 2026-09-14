# recheck-v2 (pilot)

The portable recheck pilot from the skills v2 execution plan
(`~/ObsidianVault/03-projects/tony-skills/skills-v2-execution-plan.md`). One closed-checklist
re-inspection skill meant to run as a native entry point on several harnesses from one shared
core with a small adapter per harness.

Status: **E8: contract revision 5, schemas, core scripts, skill body built; E9 adds the
adapters.** The plugin is not yet listed in `.claude-plugin/marketplace.json`; E9 lists it
with the adapters. The rulings that shaped the core (E8-1 to E8-30 and the amendments E8-A1 to
E8-A46) are in `docs/plans/2026-09-13-recheck-v2-e8-core.md`; the contract
(`skills/recheck-v2/references/pilot-contract.md`, revision 5) outranks that document. E7's
fixtures, answer key, trigger set, and check runner are under `evals/` (`evals/README.md`).

Names carry the `-v2` suffix (plugin and skill) while v1 `recheck` stays installed; both are
renamed at cutover (ruling 10, 2026-09-13).

## Layout

```text
plugins/recheck-v2/
  .claude-plugin/plugin.json          # name recheck-v2, version 0.1.0
  README.md
  skills/recheck-v2/
    SKILL.md                          # the portable core: the procedure the executor follows
    references/
      pilot-contract.md               # the behavioral contract, revision 5
      input.schema.json               # the one validated input structure
      result.schema.json              # the common result
      checkpoint.schema.json          # the checkpoint of contract section 11
      receipt.schema.json             # the receipt of contract section 9
      verifier.md                     # the verifier protocol: brief, report, statuses, readers request
      examples/                       # inputs, results, a checkpoint and a receipt, with a README
    scripts/
      recheck.py                      # the phase driver, one CLI (start, record-call, adjudicate, new-defect, record, resume, identity, ledger, skill-identity)
      validate-result.py              # schema plus semantic validator for a result
      validate-examples.py            # the example suite
      recheck_core/                   # the library the three scripts import
      tests/                          # unittest suites, stdlib
  evals/                              # E7: fixtures, answer key, trigger set, the check runner
```

## Running the suites

From the repository root (the tests derive every path from their own location, so the same
commands with absolute paths run from anywhere):

    uv run --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/recheck-v2/skills/recheck-v2/scripts/tests -v
    uv run plugins/recheck-v2/skills/recheck-v2/scripts/validate-examples.py
    cd plugins/recheck-v2/evals && uvx --with jsonschema python3 checks/run-checks.py --out /tmp/recheck-v2-runner --json

Expected output:

- The unittest run ends with `Ran <N> tests` and `OK`, exit 0; two tests print the description's
  300- and 500-character cuts and the body's size on the way.
- `validate-examples.py` prints one JSON object on stdout and nothing else, exit 0 when every
  check passes: `{"ok": true, "positive": {"files": 14, "failing": 0}, "negative": {"total": 155,
  "rejected": 155}, "mutations": {"total": 32, "accepted": 32}, "checkpoint": {"total": 15,
  "passed": 15}, "receipt": {"total": 9, "passed": 9}, "failures": []}` (the counts follow the
  example set). Diagnostics go to stderr (`--verbose` adds the per-file lines); `--help` and
  `--skill-root DIR` (a test-only references directory) are accepted; exit 4 when any check
  fails (`ok` false, each failure listed under `failures`), 2 on an unknown argument, 3 when
  `jsonschema` is missing.
- The E7 check runner prints one object `{"steps": [{step, name, pass, detail, failures: [{lane,
  case, side, detail}]}]}` with every `pass` true, exit 0; exit 1 when a step fails.

The tests build the E7 fixtures into a temporary directory (`RECHECK_TEST_SCRATCH` when it
names one) and clean up after themselves; nothing is written under `evals/`. The Python 3.9
floor is proved separately: `python3 -m py_compile` under `/usr/bin/python3` and one suite run
under `uv run --python /usr/bin/python3 --with jsonschema==4.25.1`.

## Build record (E8)

- Contract revision 5, 2026-09-13 evening (commit `8cfc095`): the control room settled the four
  Appendix B items and the sixteen gaps E7 carried as rulings E8-1 to E8-30 in
  `docs/plans/2026-09-13-recheck-v2-e8-core.md`, with the lane contract's design (the CLI, the
  run directory, the phases, the verifier protocol, the validator checks) written before any code.
- Three build slices, each by one fresh Fable low agent, each checked by a fresh Fable high agent
  before the next started, each with one low fix round: slice 1 (schemas revision 5, checkpoint
  and receipt schemas, validators; `53d1df8`; the checker rejected it once, 1 BLOCKER, 3 MAJOR,
  8 MINOR), slice 2 (the core library and the nine-subcommand driver; `f4e2613`; rejected once,
  3 BLOCKER, 7 MAJOR, 9 MINOR), slice 3 (the skill body, `verifier.md`, the manifest, this README,
  end-to-end tests on the E7 fixtures with a canned verifier; `eb03818`; held, 0 BLOCKER, 2
  MAJOR, 12 MINOR). Amendments E8-A1 to E8-A18 record what the checks changed.
- Astra (GPT-6, max, fresh, `codex exec` on a copy of this folder behind the wall, with all 113
  fixtures built beside it): CORE REJECTED, 15 BLOCKER, 10 MAJOR, 2 MINOR across 27 findings
  (its first run's verdict message was blocked by the provider's content filter; the thread was
  resumed and wrote the verdict as a file). One fix round under rulings E8-A19 to E8-A46 (four
  fresh low agents in sequence; `d1065d5`; 235 to 318 tests). Verification: 21 of 27 FIXED. A
  targeted fix under E8-A47 to E8-A51 (`29c6700`) and a targeted re-check: 9, 26, 16, 29
  cleared. A second targeted pass (two tooling changes by the control room) and re-check:
  BOTH CLEARED, no new BLOCKER (`1346eb2`; Astra's own run of the suites from the copy: 326 tests OK, the example suite green).
- Suites at close: 326 unit tests OK under uv (Python 3.12) and `/usr/bin/python3` 3.9.6, also
  from a standalone copy of this folder; `validate-examples.py` 14 positive, 156 negative, 33
  mutations, 15 checkpoint, 9 receipt; the E7 runner green on all nine steps.
- **E8 CLOSED under plan ruling 17 on 2026-09-14**: no BLOCKER open; every MAJOR fixed or
  carried in writing; the checks pass. Carried to E9: the adapter's reported facts (E8-13,
  E8-18, E8-24, E8-25, E8-A17), the ended-run and resume behavior the adapters branch on
  (E8-A20, E8-A23, E8-A30, E8-A38), the A7b delivery fixture and sidecars, the unauthorized-grant
  tests with each harness's `turn_attribution`. Carried to E10: gaps 14 and 16 with the fix named
  (`commands_run` and `observed` in the report block, E8-A43); keys I4-03/06/07 accept `target`
  before the leaf (E8-A9); `fixturelib`'s symlink hashing aligned with the core (E8-A46); the
  IA lane's `CASES.md` text on the pin pattern; gaps 9 and 13 as E7 carried them. Astra's prompts,
  verdicts, and logs are in the Clerk packet under `astra-outputs/e8/`.
