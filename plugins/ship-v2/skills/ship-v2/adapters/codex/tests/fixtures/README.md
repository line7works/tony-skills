# tests/fixtures

`real-rollout.jsonl` is a byte-identical copy of the recheck-v2 pilot's
`skills/recheck-v2/adapters/codex/tests/fixtures/real-rollout.jsonl`: a sanitized real Codex
0.154.0 rollout (thread `01a0a1be-7b64-7383-9974-3e586fec7fb3`, 2026-09-14) that keeps only the
`session_meta`, `turn_context` and `event_msg/item_completed` records, with every user and
assistant text replaced by neutral words and paths rewritten to `/tmp/neutral-workspace` and
`/tmp/neutral-home`. The pilot's fixture README says what was removed. Copied, not referenced,
because an installed plugin cannot reach a sibling plugin's folder.

The fields these helpers read are the harness's own: `session_meta.id`, `.originator`,
`.cli_version`, `.model_provider`, `.cwd`; `turn_context.model`, `.sandbox_policy`,
`.collaboration_mode.settings.reasoning_effort`. Tests that need another shape mutate a copy
under a temporary directory.
