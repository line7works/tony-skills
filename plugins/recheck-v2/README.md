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

filled by the control room at close
