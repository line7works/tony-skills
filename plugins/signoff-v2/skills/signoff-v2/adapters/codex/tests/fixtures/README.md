# tests/fixtures

`real-rollout.jsonl` is a byte-identical copy of the recheck-v2 pilot's
`skills/recheck-v2/adapters/codex/tests/fixtures/` file of the same name: a sanitized real Codex
0.154.0 rollout (the executor's, thread `01a0a1be-7b64-7383-9974-3e586fec7fb3`, 2026-09-14) that
keeps only session identity, model, the item and message shapes, with every text replaced by
neutral words; the pilot's fixture README says what was removed.

The child rollout the slice 3 reviewer test stood in for a fresh `codex exec` reviewer is gone
with that transport (Astra's F6): this adapter launches no reviewer and reads no child record.

Copied, not referenced, because an installed plugin cannot reach a sibling plugin's folder.
