# Examples

Every `input-*` and `result-*` file here validates against its schema, `checkpoint-partial.json`
against `checkpoint.schema.json`, and `receipt-partial.json` against `receipt.schema.json`.
`scripts/validate-examples.py` (moved out of this folder at E8) also runs the negative suite
(documents that must fail), the positive mutations (documents the contract allows and the
schema must accept), the checkpoint checks of contract section 11 (the item-state union, the
digest, the chain, the log, the one tolerated state with its predecessor link, E8-15), and the
same integrity checks on the receipt. It resolves this folder from its own location, so it runs
from any directory; from this folder:

    uv run ../../scripts/validate-examples.py

Every result with a run directory lists its own artifacts in write order (contract section 9);
only `completed` and `recording_failed` list project-record writes.

| File | Path it exercises |
|---|---|
| `input-direct.json` | direct interactive invocation, build doc plus slice; `harness` and `model` as objects with `floor_met` (E8-18), `session_wrote_fix` false (E8-13) |
| `input-caller.json` | station caller, explicit items with provenance, a forwarded waiver on the user channel, an identity pin; `harness` and `model` as objects with the adapter's settings |
| `result-completed.json` | completed run: one fixed, one missed case, card moved, full write list with hashes and receipt |
| `result-completed-blocked.json` | completed run after a resume: verification blocked, static with reason, missing evidence, a fix-introduced defect, a reopened item with its line and marker, a rejected grant object, an injection attempt, a waiver claimed in reviewed material listed under both `rejected_grants` and `injection_attempts` (E8-3), a refused action under `run.verifier.refused_actions` (E8-5) |
| `result-missing-input-headless.json` | station caller envelope: every field listed, no question |
| `result-missing-input-interactive.json` | direct interactive envelope with the one question |
| `result-invalid-input-envelope.json` | payload failed validation before a run id existed: no `run` block |
| `result-stale-source.json` | pin mismatch: both identities, `matched: false`, no write |
| `result-verifier-unavailable.json` | below the floor: nothing graded, no retry |
| `result-nothing-open.json` | empty checklist against a clear card: no write |
| `result-stopped.json` | retryable verifier failure twice: nothing graded, no record write, the artifact-only write list |
| `result-recording-failed.json` | step 6 (status line) failed mid-transaction: receipt, block and verdict-doc copy landed, no card |
| `checkpoint-partial.json` + `checkpoint-partial.log` | a checkpoint written mid-adjudication: one `done` item, two `pending`, an accepted reopening in scope, the integrity block, and the log whose last line it matches (`input_sha256` and the first three log hashes are illustrative; the fourth is computed) |
| `receipt-partial.json` + `receipt-partial.log` | the receipt of `result-recording-failed.json` as it stood when step 3 (the status line) failed: a three-step plan (block, verdict-doc copy, status line) with `content`, `heading`, and `value` (E8-28), entries through step 3's `intent`, and the integrity chain and log computed for real over six writes (the target hashes are the illustrative values of the result example) |
