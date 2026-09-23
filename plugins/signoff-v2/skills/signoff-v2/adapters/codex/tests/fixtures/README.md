# tests/fixtures

`real-rollout.jsonl` and `child-rollout.jsonl` are byte-identical copies of the recheck-v2 pilot's
`skills/recheck-v2/adapters/codex/tests/fixtures/` files of the same names: sanitized real Codex
0.154.0 rollouts (the executor's, thread `01a0a1be-7b64-7383-9974-3e586fec7fb3`, and a verifier
child's, thread `01a0a1e3-1b19-7d23-8225-c251b82329dc`, 2026-09-14) that keep only session
identity, model, the item and message shapes, with every text replaced by neutral words; the
pilot's fixture README says what was removed. `test_reviewer.py` stands the child rollout in for
the fresh reviewer's own record in the canned transport.

Copied, not referenced, because an installed plugin cannot reach a sibling plugin's folder.
