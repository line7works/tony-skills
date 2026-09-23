# tests/fixtures

`session-transcript.jsonl` is a copy of the recheck-v2 pilot's
`skills/recheck-v2/adapters/claude-code/tests/fixtures/session-transcript.jsonl`: a real Claude
Code 2.1.270 session transcript (session `4cd53208-8cb8-4de2-bb71-be7594182bb1`, 2026-09-14), cut
down and neutralized by the pilot's lane C (every user and assistant text replaced by neutral
words, `cwd` rewritten to `/tmp/widget-workspace`, no credential-shaped string); the pilot's
fixture README lists every change. One more change here: the pilot's copy still carries the
machine's home directory in three records; in this copy `/Users/<name>/` reads `/Users/neutral/`
and `-Users-<name>` reads `-Users-neutral`, and nothing else differs.

`readers-sidecar-ok.json` is a byte-identical copy of the pilot's readers sidecar fixture of the
same folder (a readers `ok` sidecar with neutral `/tmp/...` paths); `test_reviewer.py` rewrites a
copy's paths and call id under a temporary directory.

Both are copied rather than referenced because an installed plugin cannot reach a sibling
plugin's folder. Tests that need another shape mutate a copy under a temporary directory.
