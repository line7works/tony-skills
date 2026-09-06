# readers — the request/result contract (protocol version 1)

This file fixes the names every caller and every later slice cites. The runner (`readers.py`, entry `readers`) implements it for the portable lanes (GPT through `codex exec`, DeepSeek and Qwen through OpenRouter); the skill body implements the same shape for the host lanes and hands its capture to the runner's `record` step (Slice C). Field and status names change only by a protocol bump. Steps: `readers --version`, `readers validate <request>`, `readers suggest <rows> --run <run id>`, and `readers <request>` (dispatch).

## The request

A JSON object, from a file path or stdin (`-`):

- `protocol_version` — the version the caller was written against (required; the runner's is `1`).
- `run_id` — the caller's run (a fleet shares one). Minted as `adhoc-<hex>` when absent.
- `call_id` — caller-supplied, or minted by the runner (`c-<hex>`) and returned in the result. A call id is single-use: a call id whose `sidecar.json` already exists under the run dir is refused as `invalid-request` without touching it, whatever the earlier call's status (a retry mints a new id). Both ids are one path segment: characters `[A-Za-z0-9._-]`, not starting with a dot, never `.` or `..`; anything else is `invalid-request`, and because such a request names no legal call directory that refusal is the one case that writes no sidecar (the result is still printed).
- `run_dir` — optional. Default: `$READERS_RUN_ROOT/<run id>` when set, else `${TMPDIR:-/tmp}/readers/<run id>`. Every step (`suggest`, `validate`, dispatch) resolves it the same way; a caller that passes `run_dir` to its calls passes the same directory as `--run-dir` to `suggest`, so they share one snapshot.
- `row` — a roster row id (`roster.json`).
- `mandate` — the text, or a path to a file holding it. The runner never rewrites a mandate.
- `documents` — file paths (UTF-8 text; a document that does not decode is `invalid-request`), and/or `workspace` — a directory. At least one of the two; the `repo` and `repo-with-tools` profiles need a `workspace`. Each document gets one name inside the request, its basename, with `-2`, `-3` appended on a collision; the prompt's `DOCUMENT` labels and the `packet-only` copies use the same names.
- `profile` — the access profile: `starved` (a fresh empty directory), `packet-only` (a fresh directory the runner fills with copies of the documents and nothing else; on rows whose model has no filesystem the documents travel only in the prompt and the sidecar records `packet-only (no workspace)`), `repo` (the caller's workspace, read), `repo-with-tools` (the caller's workspace; the reviewer may run tests, writes confined to scratch and ignored caches, never a tracked file; an execution the sandbox blocks is reported as "verification blocked", never marked checked).
- `effort` — optional; must be one of the row's `efforts`.
- `model` — optional typed model id. Any typed id is an explicit pick (`override_source: explicit pick`): an id that is not the row's default is sent as-is under the row's envelope (`envelope: inherited from <row id>`) and remembered in the last-pick memory when the call is dispatched; the row's own default, typed, is sent as the default (envelope the row) and never remembered, and it beats a remembered pick. On a floor-bound call a typed id that is not the row default is `unknown-model`. An id carrying a web-search suffix (`:online`) is `invalid-request`: readers never sends one, so the parity line `no :online suffix` is always true. With no `model`, a remembered pick for the row (from the run's snapshot) is used and recorded as `remembered pick`; otherwise the roster default.
- `output_budget` — optional positive integer, never above the row's `max_output` when that is known. On the OpenRouter rows it is sent as `max_tokens`; absent, the row's `max_output` is sent.
- `raw_path` — optional path the caller owns; it receives a copy of `raw.md` (collision rule below).
- `authorized` — `true` when Tony's word in this run named an outside row. Required for every outside row: every row whose `provider` is not `anthropic` (GPT, Gemini, DeepSeek, Qwen today, and any row added later). Claude rows never need it.
- `floor` — optional model floor (`opus` today). Enforced by the rules under `floor-refused` and `unknown-model`.
- `session_model` — the harness model id of the session that summoned a `claude-session` call. The skill body fills it; the shell entry leaves it empty. A floor-bound `claude-session` call with none is `floor-refused` (reason `session model unknown`).
- `isolation` — optional, `worktree`: a `repo-with-tools` Claude call whose method mutates the checkout runs its reviewer in the Agent tool's worktree isolation (Slice C); the sidecar records it.

## The result

Every field is present in every sidecar, `null` when not applicable, so a portable and a host sidecar have one shape.

`status` · `reason` · `call_id` · `run_id` · `run_dir` · `row` · `transport` · `kind` · `override_source` (`roster default` | `remembered pick` | `explicit pick`) · `requested_model` · `effective_model` · `requested_effort` · `effective_effort` · `envelope` (the row whose limits applied, or `inherited from <row id>` for a typed or remembered id) · `budget_method` · `budget` (`estimate_tokens`, `limit`) · `protocol_version` · `adapter_version` · `mandate_hash` · `packet_hash` · `profile` (the requested profile; `packet-only (no workspace)` on a row whose model has no filesystem) · `workdir` (null on such a row) · `workdir_instruction_files` (`AGENTS.md`/`CLAUDE.md` present in the child's working directory; empty on such a row) · `isolation` (the row's label for the profile used) · `parity` (the row's parity line for the profile used) · `raw_text` (the verbatim capture on `ok`; the empty string on any other status) · `raw_file` (`<run dir>/<call id>/raw.md`; null unless `ok`) · `raw_hash` (sha256 of `raw.md`; null unless `ok`) · `raw_path` (the caller's copy when one was named; null otherwise) · `diagnostics` (the directory; an `incomplete` call's partial text is at `<diagnostics>/partial.md` and nowhere else) · `dispatch_log` · `exit_code` (the child's exit code; the HTTP status on the OpenRouter lane) · `generation_id` (the provider's top-level `id`; OpenRouter lane, null elsewhere) · `response_raw` (`<run dir>/<call id>/response.raw`, the exact HTTP body; OpenRouter lane, null elsewhere) · `memory` (`ok: <memory path>`, `ok: remembered <id> for <row> at <path>` when the call wrote a pick, or `unavailable: <reason>`; memory trouble of any kind, a lock not taken within 5 s included, is a status here and never loses the call: the pick is still sent) · `snapshot` (`<run dir>/snapshot`, the frozen roster and memory this call resolved from; null on validate when no snapshot exists, and null when the run dir could not be made) · `snapshot_fault` (null, or the run-dir fault that made this call resolve from the live files instead of a snapshot; the call's own pre-send status stands, never replaced by the fault) · `canned` (null, or the test hook that stood in for the transport) · `sidecar` · `started_at` · `ended_at` · `duration_s`.

The shell entry prints the result as JSON on stdout in every case, including `invalid-request`, and exits 0 only on `ok`.

## Statuses

- `ok` — the model answered and the capture is on disk.
- `empty` — no content or whitespace only.
- `incomplete` — truncated: a finish reason (`length` on OpenRouter), an output cap, or an interrupted stream. Partial text stays in diagnostics only. Beats `empty`: a truncated body with empty content is `incomplete`.
- `oversize` — rejected before any send; the result carries the estimate and the limit.
- `invalid-request` — malformed JSON, a missing required field, an unknown row id, an unknown profile, an effort the row does not list, an output budget above the row's max or not a positive integer, a document or workspace that does not exist.
- `lane-unavailable` — the transport is absent (`codex` not on PATH), the credential the row names is not set or is malformed (a line break, NUL, or only whitespace in the value: it could not be a header, and it is refused before any request so the value never reaches an error message), the row is marked unavailable in the roster, the Workflow tool is absent for a Claude call that needs it (Slice C), or a `host` row was requested through the shell entry, which cannot run one. The reason names which.
- `unauthorized` — an outside row without the `authorized` flag.
- `floor-refused` — with a floor passed: a row whose `eligibility` is `not eligible`, or a `claude-session` call whose `session_model` is absent or matches none of the roster's `eligible_session_models` patterns.
- `unknown-model` — with a floor passed: a typed id, or a row whose `eligibility` is `not classified`. Tony classifies ids by roster PR.
- `profile-unsupported` — the row does not list the requested profile.
- `version-mismatch` — the request's `protocol_version` differs from the runner's.
- `transport-failed` — the child or the provider failed; the transport's own error is preserved verbatim in `reason` (for example codex's `failed to initialize in-process app-server client: Operation not permitted`; on OpenRouter a non-200 status with the provider's message, a top-level `error`, an unparseable body, a network failure, or a finish reason that is neither `stop` nor `length`, such as `tool_calls` or `content_filter`). Also a test hook set without `READERS_TEST=1` (reason `canned response outside test`): nothing is sent.
- `capture-failed` — the model answered but `raw.md` could not be written.
- `cancelled` — the caller interrupted the runner; the child is killed.
- `timed-out` — the row's `timeout_s` elapsed; the child is killed. Beats `incomplete`.

## Pre-send checks, in this order

Every call, host or portable, runs these before a child is launched or a request sent, and any failure returns before that point: request validity, version, authorization, profile support, floor and classification, lane availability, budget. `readers validate <request | ->` runs exactly these and prints `valid` or the refusing status, never dispatching; validate reads the named documents to size them, so a missing document is `invalid-request`; validate does not apply the host-row rule, so a caller can check a host request from a shell. Validate writes nothing to disk: no run directory, no call directory, no sidecar, no snapshot, so a validated request can be dispatched afterwards under the same ids; it resolves rows and picks from the run's snapshot when one exists and from the live files otherwise.

## Budget

The composed prompt (mandate, delimiters, documents) is estimated at bytes divided by 3.5 plus ten percent headroom (`budget_method` records the method; a provider tokenizer may replace it when available) and compared with the row's or envelope's context window minus the output budget: the request's `output_budget`, else the row's `max_output`, else nothing when that is `unknown` (recorded as `window-only`). A row whose window is `unknown` skips the check and records `skipped (window unknown)`. The packet is never truncated or summarized to fit.

## Prompt composition

The mandate at the top, then each document delimited as evidence:

```
<mandate>

<<<DOCUMENT smoke-doc.md>>>
...
<<<END DOCUMENT>>>
```

This is a semantic migration from the MCP route's `base-instructions`; nothing is placed in Codex's instructions-file setting. Document bytes reach the child through stdin or files, never through generated shell source, argv, or `eval`. The child's environment is built from a fixed list (`PATH`, `HOME`, `TMPDIR`, locale, `TERM`, `USER`, `SHELL`, `CODEX_HOME`) and nothing else: a credential in the runner's environment never reaches the model's sandbox.

## Evidence

Every call has `<run dir>/<call id>/` holding `sidecar.json` (every result field; written before the result is returned; never rewritten), `raw.md` (the exact final response; `raw_hash` covers it), `diagnostics/` (GPT lane: the event stream, stderr, the command line; OpenRouter lane: `request-meta.json` with the url, model, `max_tokens`, `reasoning`, and prompt byte count, never a header, and `http.txt` with the status; `partial.md` when truncated), `response.raw` on the OpenRouter lane (the exact HTTP body, so jpb's cost script can read its top-level `id`), and `dispatch.log`, one line appended before any child launch or request. The run directory also holds `snapshot/` (below). A refused call writes `sidecar.json` alone: no `dispatch.log`, no `diagnostics/` (the one exception: a request whose `run_id`, `call_id`, or `run_dir` is invalid has no call directory and writes nothing). A caller-named `raw_path` receives a copy; when that path already exists the runner appends `-2`, `-3` to the filename rather than overwriting. What a caller does to its copy (inspect's banner, precon's disposition) never touches `raw.md` or the hash. The run-dir `raw.md` is evidence; whether and where a raw file is filed under `docs/` is the caller's filing policy.

## Guards, GPT lane (codex exec)

In this order, each mapped to a status: the child's exit code and startup failure (`transport-failed`, with the CLI's own message wherever it put it: `error` / `turn.failed` events on stdout, non-JSON stdout lines, then the stderr tail); a truncation signal from the event stream (`incomplete`: a structural field on an event or item, `finish_reason: length`, `stop_reason: max_tokens`, `status: incomplete`, `incomplete_details`, `truncated: true`, or a stream that ends without `turn.completed`; the answer text itself is never scanned); empty content (`empty`); a response, or the caller's `raw_path` copy, that cannot be written (`capture-failed`; `raw.md` may remain on disk and the reason names it, the result's raw fields are null). Transport success and content status are separate fields (`exit_code`, `status`). The child is killed at the row's `timeout_s` (`timed-out`). Before every launch the call directory's `output.md` and `diagnostics/partial.md` from any earlier attempt are removed, so a stale file is never read. An unexpected runner error is still a result: `invalid-request` before the launch, `capture-failed` after it, never a traceback in place of the JSON.

## Guards, OpenRouter lane (deepseek, qwen)

The request: the chat-completions endpoint, the row's or the pick's model id, the prompt as one user message, `max_tokens` from the output budget, `"reasoning": {"enabled": true}` on rows whose `reasoning` is `on` (verified live 2026-09-06 on both rows), and no `:online` suffix (parity line `no :online suffix`). Documents travel only in the prompt; there is no working directory (`repo` and `repo-with-tools` are `profile-unsupported`). The body is saved as `response.raw` whatever the status. Guards in this order, the earlier one winning when two coexist: an unparseable body, a non-200 status, or a top-level `error` is `transport-failed` with the provider's message; finish reason `length` is `incomplete` with the partial text at `<diagnostics>/partial.md` only; empty or whitespace content is `empty`; any finish reason other than `stop` (a tool call, a content filter) is `transport-failed` with the reason preserved; else `ok`. The response's top-level `id` is `generation_id`. A missing `OPENROUTER_API_KEY` is caught by the lane-availability check (`lane-unavailable`, no `dispatch.log`). The socket timeout is the row's `timeout_s` (`timed-out`).

## The last-pick memory

`$READERS_CHECKOUT/plugins/readers/last-picks.json` (`$READERS_CHECKOUT` defaults to `~/Developer/tony-skills`; the tracked seed is `{"protocol_version": 1, "picks": {}}`), shared by both Macs through git. Keyed by roster row id; an entry holds `model` (the picked id), `date`, `row_default` (the row's default id when the pick was made), and `dropped` (null, or `{date, reason}`). Written when a call is dispatched with an explicit `model` that differs from the row's default; read by `suggest` and, through the run's snapshot, by dispatch. Writes are atomic: an exclusive `last-picks.json.lock` beside the file (created `O_EXCL`, removed after the write, broken when older than 60 s, waited for at most 5 s), read, modify, write to a temporary file in the same directory, rename over the original, so concurrent fleet calls never lose each other's entries. When the checkout is absent or the file's directory is not writable, the file does not parse, the lock cannot be taken in time, or the write fails, the result says `memory: unavailable: <reason>`, the roster row (or the explicit pick, which is still sent) is used, and nothing is written anywhere else; memory trouble never aborts a call. The installed plugin cache is never read or written for memory; the roster is always the one beside the running `readers.py`.

## Suggest

`readers suggest <row id>[,<row id>...] --run <run id> [--run-dir <dir>] [--floor <floor>]` prints JSON: `run_id`, `run_dir`, `snapshot`, `memory`, `floor`, and one `suggestions` entry per row with `model` (the remembered pick when one exists and is usable, else the roster default), `source` (`remembered pick` | `roster default`), `picked_on`, `effort` (the row's default), `outside` and `needs_word` (true when the row needs Tony's word), `available`, `eligibility` (`not classified` for a remembered typed id), `drop_note`, and `note` (an existence check that could not run). On its first call for a run id it also freezes the run (below), after applying the drop rules, so the model the caller shows Tony is the model the run sends. A remembered pick is dropped at suggest time and never after, with a note that appears once (the drop is recorded in the entry's `dropped` field): when the row's default has changed since the pick (a roster PR bumped the row); when the id is no longer listed where that can be checked (OpenRouter's public model list for the OpenRouter rows, `~/.codex/models_cache.json` for the GPT rows; an unreachable list drops nothing and is reported in `note`); or when a floor is passed and the pick is a typed id, which is never classified. A later `suggest` for the same run id reads the frozen copy and re-evaluates nothing. Exit 0 on a suggestion, 1 with a JSON `invalid-request` for an unknown row, a malformed run id, or a run dir that cannot be made or read; `suggest` prints JSON in every case, never a traceback.

## The run-wide freeze

The first `suggest` or dispatch carrying a run id copies the roster and the memory file into `<run dir>/snapshot/` (`roster.json`, `memory.json` when the memory is available, and `meta.json` with the creation time, the sources, and the memory status). The directory is built in a temporary sibling and renamed into place, so two concurrent first calls produce exactly one snapshot and the loser reads the winner's. Every later call with that run id resolves rows and picks from the snapshot, never the live files, and its sidecar names it in `snapshot`; a call whose run dir cannot be made or whose snapshot cannot be read resolves from the live files, keeps its own pre-send status, and reports the fault in `snapshot_fault`; a snapshot plus each call's `override_source`, `effective_model`, and `effective_effort` is the run record. A refused call also resolves from (and, when first, creates) the snapshot, because refusal needs the row. Validate never creates one.

## Transport test hooks

Only under `READERS_TEST=1`; set without it, the call is `transport-failed` with reason `canned response outside test` and nothing is sent. `READERS_CANNED_RESPONSE=<file>` makes the OpenRouter adapter read a saved reply (a JSON file with top-level `http_status` and `body`, the body an object or a string) instead of calling the network; `READERS_CANNED_CODEX=<dir>` makes the GPT adapter read a saved `events.jsonl`, `output.md`, `stderr.txt`, and `exit` from that directory instead of launching a child. The sidecar's `canned` field names the hook used. The seven canned cases live at `fixtures/canned/`. Pre-send checks are not relaxed under the hooks: the credential must still be set for an OpenRouter row.

## Isolation

Measured, not claimed (Slice A R9). Per profile, the row's label is `sandbox-enforced` (sentinel outside the packet directory unreadable, write denied), `instruction-only (read)` (sentinel readable, write denied), `no-workspace` (the model has no filesystem), `harness-enforced (toolCalls: 0)` (Claude under the Workflow route), or `unmeasured`. A write that succeeds under a read-only sandbox stops the lane: the row's `available` becomes `false` with a reason and every request on it is `lane-unavailable` until a roster PR on Tony's word records a denial.

## Secrets

A credential is read from the environment into a request header and nowhere else: never persisted, logged, printed, or written to a sidecar, diagnostics file, or evidence file; the adapter writes no request header of any kind to disk (`request-meta.json` carries the url, model, budget, reasoning flag, and prompt size only), and the child environment of the GPT lane never carries it. Existence is checked with `[ -n "$OPENROUTER_API_KEY" ] && echo set` and nothing else. The runner never reads `~/.zshrc`, and nobody debugging a lane does either: the key lives there beside an alias, and a read lands it in a transcript (it happened 2026-08-30; the 2026-08-11 leak forced a rotation).

## Version

`readers --version` prints the protocol version. A caller states `readers-protocol: 1` in its SKILL.md and passes it as `protocol_version`; a mismatch is refused before any dispatch.
