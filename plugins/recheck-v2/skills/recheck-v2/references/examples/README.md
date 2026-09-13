# Examples

Every file here validates against its schema, and `validate-examples.py` (E8 will move this
into `scripts/`) also runs the negative suite: documents that must fail. Run from this folder:

    uvx --with jsonschema python3 validate-examples.py

| File | Path it exercises |
|---|---|
| `input-direct.json` | direct interactive invocation, build doc plus slice |
| `input-caller.json` | station caller, explicit items with provenance, a forwarded waiver on the user channel, an identity pin |
| `result-completed.json` | completed run: one fixed, one missed case, card moved, full write list with hashes and receipt |
| `result-completed-blocked.json` | completed run after a resume: verification blocked, static with reason, missing evidence, a fix-introduced defect, a reopening line, a rejected grant, an injection attempt |
| `result-missing-input-headless.json` | station caller envelope: every field listed, no question |
| `result-missing-input-interactive.json` | direct interactive envelope with the one question |
| `result-invalid-input-envelope.json` | payload failed validation before a run id existed: no `run` block |
| `result-stale-source.json` | pin mismatch: both identities, `matched: false`, no write |
| `result-verifier-unavailable.json` | below the floor: nothing graded, no retry |
| `result-nothing-open.json` | empty checklist against a clear card: no write |
| `result-stopped.json` | retryable verifier failure twice: nothing graded, no write |
| `result-recording-failed.json` | a write failed mid-transaction: receipt, block landed, no card |
