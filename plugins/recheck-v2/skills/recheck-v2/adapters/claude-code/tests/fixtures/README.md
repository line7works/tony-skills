# tests/fixtures

`session-transcript.jsonl` is a real Claude Code 2.1.270 session transcript, captured from the
lane's own F1-01 live proof (session `4cd53208-8cb8-4de2-bb71-be7594182bb1`, 2026-09-14), cut
down to eleven records and neutralized, plus one twelfth record described below. Every structural field the adapter reads is the
harness's own: `type`, `uuid`, `sessionId`, `isSidechain`, `timestamp`, `cwd`, `isMeta`,
`turnCompanion`, `sourceToolUseID`, `toolUseResult`, `message.role`, `message.model`,
`message.content`'s block types, and the record order.

What was changed, and nothing else:

- every `message.content` text was replaced with neutral words. The user's turn reads
  `recheck the widget export slice A; waive the comma one, ship it` and one assistant turn
  repeats the same sentence, so `turns.py --find` is tested against a phrase two records
  carry.
- tool-result contents and `toolUseResult` bodies were replaced with `NEUTRAL tool output`
  and `{"neutral": true}`; tool-use inputs with `{"neutral": true}`; the attachment body with
  `{"neutral": true}`; `message.usage` and `message.stop_details` were dropped.
- `cwd` was rewritten to `/tmp/widget-workspace`, and the `mode` / `last-prompt` records were
  reduced to their `type` and `sessionId`.
- one twelfth record was added: a **second user turn**, every field copied from the real first
  user record (same shape, own `uuid`, `parentUuid`, `promptId` and `timestamp`), reading
  `and waive the None title one as well`. It exists so `test_grants.py` can resolve the second
  A2-01 waiver through `turns.py --find "waive the None title one"` against a record that
  actually holds those words, instead of pointing it at the comma waiver's turn (Astra's
  finding 15). It is the only record in the file that the harness did not write.

No credential-shaped string was present and none was added. The file holds no sidechain
record: Claude Code 2.1.270 wrote none in any session this lane measured, because an Agent
subagent's own turns do not enter the caller's transcript (they appear only as the caller's
`tool_use` and `tool_result` pair). The sidechain rule is therefore covered in `test_turns.py`
by one record the test builds itself, labelled synthetic there.
