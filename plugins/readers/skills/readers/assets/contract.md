# readers — the request/result contract (protocol version 1)

This file fixes the names every caller and every later slice cites. The runner (`readers.py`, entry `readers`) implements it for the portable lanes; the skill body implements the same shape for the host lanes and hands its capture to the runner's `record` step (Slice C). Field and status names change only by a protocol bump.

## The request

A JSON object, from a file path or stdin (`-`):

- `protocol_version` — the version the caller was written against (required; the runner's is `1`).
- `run_id` — the caller's run (a fleet shares one). Minted as `adhoc-<hex>` when absent.
- `call_id` — caller-supplied, or minted by the runner (`c-<hex>`) and returned in the result. A call id is single-use: a call id whose `sidecar.json` already exists under the run dir is refused as `invalid-request` without touching it, whatever the earlier call's status (a retry mints a new id). Both ids are one path segment: characters `[A-Za-z0-9._-]`, not starting with a dot, never `.` or `..`; anything else is `invalid-request`.
- `run_dir` — optional. Default: `$READERS_RUN_ROOT/<run id>` when set, else `${TMPDIR:-/tmp}/readers/<run id>`. Every step (`suggest`, `validate`, dispatch) resolves it the same way.
- `row` — a roster row id (`roster.json`).
- `mandate` — the text, or a path to a file holding it. The runner never rewrites a mandate.
- `documents` — file paths (UTF-8 text; a document that does not decode is `invalid-request`), and/or `workspace` — a directory. At least one of the two; the `repo` and `repo-with-tools` profiles need a `workspace`. Each document gets one name inside the request, its basename, with `-2`, `-3` appended on a collision; the prompt's `DOCUMENT` labels and the `packet-only` copies use the same names.
- `profile` — the access profile: `starved` (a fresh empty directory), `packet-only` (a fresh directory the runner fills with copies of the documents and nothing else; on rows whose model has no filesystem the documents travel only in the prompt and the sidecar records `packet-only (no workspace)`), `repo` (the caller's workspace, read), `repo-with-tools` (the caller's workspace; the reviewer may run tests, writes confined to scratch and ignored caches, never a tracked file; an execution the sandbox blocks is reported as "verification blocked", never marked checked).
- `effort` — optional; must be one of the row's `efforts`.
- `model` — optional typed model id. An id that is not the row's default is sent as-is under the row's envelope and recorded as `explicit pick`; on a floor-bound call it is `unknown-model`.
- `output_budget` — optional positive integer, never above the row's `max_output` when that is known.
- `raw_path` — optional path the caller owns; it receives a copy of `raw.md` (collision rule below).
- `authorized` — `true` when Tony's word in this run named an outside row. Required for every outside row: every row whose `provider` is not `anthropic` (GPT, Gemini, DeepSeek, Qwen today, and any row added later). Claude rows never need it.
- `floor` — optional model floor (`opus` today). Enforced by the rules under `floor-refused` and `unknown-model`.
- `session_model` — the harness model id of the session that summoned a `claude-session` call. The skill body fills it; the shell entry leaves it empty. A floor-bound `claude-session` call with none is `floor-refused` (reason `session model unknown`).
- `isolation` — optional, `worktree`: a `repo-with-tools` Claude call whose method mutates the checkout runs its reviewer in the Agent tool's worktree isolation (Slice C); the sidecar records it.

## The result

Every field is present in every sidecar, `null` when not applicable, so a portable and a host sidecar have one shape.

`status` · `reason` · `call_id` · `run_id` · `run_dir` · `row` · `transport` · `kind` · `override_source` (`roster default` | `remembered pick` | `explicit pick`) · `requested_model` · `effective_model` · `requested_effort` · `effective_effort` · `envelope` (the row whose limits applied, or `inherited from <row id>` for a typed id) · `budget_method` · `budget` (`estimate_tokens`, `limit`) · `protocol_version` · `adapter_version` · `mandate_hash` · `packet_hash` · `profile` · `workdir` · `workdir_instruction_files` (`AGENTS.md`/`CLAUDE.md` present in the child's working directory) · `isolation` (the row's label for the profile used) · `parity` (the row's parity line for the profile used) · `raw_text` (the verbatim capture on `ok`; the empty string on any other status) · `raw_file` (`<run dir>/<call id>/raw.md`; null unless `ok`) · `raw_hash` (sha256 of `raw.md`; null unless `ok`) · `raw_path` (the caller's copy when one was named; null otherwise) · `diagnostics` (the directory; an `incomplete` call's partial text is at `<diagnostics>/partial.md` and nowhere else) · `dispatch_log` · `exit_code` · `generation_id` and `response_raw` (null unless the transport provides them; Slice B) · `memory` and `snapshot` (Slice B) · `sidecar` · `started_at` · `ended_at` · `duration_s`.

The shell entry prints the result as JSON on stdout in every case, including `invalid-request`, and exits 0 only on `ok`.

## Statuses

- `ok` — the model answered and the capture is on disk.
- `empty` — no content or whitespace only.
- `incomplete` — truncated: a finish reason, an output cap, or an interrupted stream. Partial text stays in diagnostics only.
- `oversize` — rejected before any send; the result carries the estimate and the limit.
- `invalid-request` — malformed JSON, a missing required field, an unknown row id, an unknown profile, an effort the row does not list, an output budget above the row's max or not a positive integer, a document or workspace that does not exist.
- `lane-unavailable` — the transport is absent (`codex` not on PATH), the credential the row names is not set, the row is marked unavailable in the roster, the Workflow tool is absent for a Claude call that needs it (Slice C), or a `host` row was requested through the shell entry, which cannot run one. The reason names which.
- `unauthorized` — an outside row without the `authorized` flag.
- `floor-refused` — with a floor passed: a row whose `eligibility` is `not eligible`, or a `claude-session` call whose `session_model` is absent or matches none of the roster's `eligible_session_models` patterns.
- `unknown-model` — with a floor passed: a typed id, or a row whose `eligibility` is `not classified`. Tony classifies ids by roster PR.
- `profile-unsupported` — the row does not list the requested profile.
- `version-mismatch` — the request's `protocol_version` differs from the runner's.
- `transport-failed` — the child or the provider failed; the transport's own error is preserved verbatim in `reason` (for example codex's `failed to initialize in-process app-server client: Operation not permitted`).
- `capture-failed` — the model answered but `raw.md` could not be written.
- `cancelled` — the caller interrupted the runner; the child is killed.
- `timed-out` — the row's `timeout_s` elapsed; the child is killed. Beats `incomplete`.

## Pre-send checks, in this order

Every call, host or portable, runs these before a child is launched or a request sent, and any failure returns before that point: request validity, version, authorization, profile support, floor and classification, lane availability, budget. `readers validate <request | ->` runs exactly these and prints `valid` or the refusing status, never dispatching; validate reads the named documents to size them, so a missing document is `invalid-request`; validate does not apply the host-row rule, so a caller can check a host request from a shell. Validate writes nothing to disk: no run directory, no call directory, no sidecar, so a validated request can be dispatched afterwards under the same ids.

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

Every call has `<run dir>/<call id>/` holding `sidecar.json` (every result field; written before the result is returned; never rewritten), `raw.md` (the exact final response; `raw_hash` covers it), `diagnostics/` (the event stream, stderr, the command line, `partial.md` when truncated), and `dispatch.log`, one line appended before any child launch or request. A refused call writes `sidecar.json` alone: no `dispatch.log`, no `diagnostics/`. A caller-named `raw_path` receives a copy; when that path already exists the runner appends `-2`, `-3` to the filename rather than overwriting. What a caller does to its copy (inspect's banner, precon's disposition) never touches `raw.md` or the hash. The run-dir `raw.md` is evidence; whether and where a raw file is filed under `docs/` is the caller's filing policy.

## Guards, GPT lane (codex exec)

In this order, each mapped to a status: the child's exit code and startup failure (`transport-failed`, with the CLI's own message wherever it put it: `error` / `turn.failed` events on stdout, non-JSON stdout lines, then the stderr tail); a truncation signal from the event stream (`incomplete`: a structural field on an event or item, `finish_reason: length`, `stop_reason: max_tokens`, `status: incomplete`, `incomplete_details`, `truncated: true`, or a stream that ends without `turn.completed`; the answer text itself is never scanned); empty content (`empty`); a response, or the caller's `raw_path` copy, that cannot be written (`capture-failed`; `raw.md` may remain on disk and the reason names it, the result's raw fields are null). Transport success and content status are separate fields (`exit_code`, `status`). The child is killed at the row's `timeout_s` (`timed-out`). Before every launch the call directory's `output.md` and `diagnostics/partial.md` from any earlier attempt are removed, so a stale file is never read. An unexpected runner error is still a result: `invalid-request` before the launch, `capture-failed` after it, never a traceback in place of the JSON.

## Isolation

Measured, not claimed (Slice A R9). Per profile, the row's label is `sandbox-enforced` (sentinel outside the packet directory unreadable, write denied), `instruction-only (read)` (sentinel readable, write denied), `no-workspace` (the model has no filesystem), `harness-enforced (toolCalls: 0)` (Claude under the Workflow route), or `unmeasured`. A write that succeeds under a read-only sandbox stops the lane: the row's `available` becomes `false` with a reason and every request on it is `lane-unavailable` until a roster PR on Tony's word records a denial.

## Secrets

A credential is read from the environment into a request header and nowhere else: never persisted, logged, printed, or written to a sidecar, diagnostics file, or evidence file; headers are redacted from anything the adapter writes. Existence is checked with `[ -n "$OPENROUTER_API_KEY" ] && echo set` and nothing else. The runner never reads `~/.zshrc`, and nobody debugging a lane does either: the key lives there beside an alias, and a read lands it in a transcript (it happened 2026-08-30; the 2026-08-11 leak forced a rotation).

## Version

`readers --version` prints the protocol version. A caller states `readers-protocol: 1` in its SKILL.md and passes it as `protocol_version`; a mismatch is refused before any dispatch.
