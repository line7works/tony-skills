# Examples

Every `input-*` and `result-*` file here validates against its schema, and
`validate-examples.py` (E8 will move this into `scripts/`) also runs the negative suite
(documents that must fail), the positive mutations (documents the contract allows and the
schema must accept), and the checkpoint checks of contract section 11 (the item-state union,
the digest, the chain, the log, and the one tolerated state). Run from this folder:

    uvx --with jsonschema python3 validate-examples.py

Every result with a run directory lists its own artifacts in write order (contract section 9);
only `completed` and `recording_failed` list project-record writes.

| File | Path it exercises |
|---|---|
| `input-direct.json` | direct interactive invocation, build doc plus slice |
| `input-caller.json` | station caller, explicit items with provenance, a forwarded waiver on the user channel, an identity pin |
| `result-completed.json` | completed run: one fixed, one missed case, card moved, full write list with hashes and receipt |
| `result-completed-blocked.json` | completed run after a resume: verification blocked, static with reason, missing evidence, a fix-introduced defect, a reopened item with its line and marker, a rejected grant, an injection attempt |
| `result-missing-input-headless.json` | station caller envelope: every field listed, no question |
| `result-missing-input-interactive.json` | direct interactive envelope with the one question |
| `result-invalid-input-envelope.json` | payload failed validation before a run id existed: no `run` block |
| `result-stale-source.json` | pin mismatch: both identities, `matched: false`, no write |
| `result-verifier-unavailable.json` | below the floor: nothing graded, no retry |
| `result-nothing-open.json` | empty checklist against a clear card: no write |
| `result-stopped.json` | retryable verifier failure twice: nothing graded, no record write, the artifact-only write list |
| `result-recording-failed.json` | step 6 (status line) failed mid-transaction: receipt, block and verdict-doc copy landed, no card |
| `checkpoint-partial.json` + `checkpoint-partial.log` | a checkpoint written mid-adjudication: one `done` item, two `pending`, an accepted reopening in scope, the integrity block, and the log whose last line it matches (`input_sha256` and the first three log hashes are illustrative; the fourth is computed) |
