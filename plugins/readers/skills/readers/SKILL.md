---
name: readers
description: The loop's reader component — one cold read on any roster row (a fresh Claude subagent, GPT, Gemini, DeepSeek, or Qwen), read-only against a mandate and documents, output captured verbatim with a sidecar. Summon form, for a caller skill: invoke /readers with a request block (one call or a fleet sharing a run id). Direct form, for Tony: `/readers <row id> <document path> "<one-line mandate>" [<profile>]`. Suggest form, no call made: `/readers suggest <row id>[,<row id>...] --run <run id>`. Use when inspect, vertical, precon, architect, jpb, signoff, wargame, or recheck needs a reader, or when Tony wants an ad hoc read of one document.
---

# Readers

One component, every reader. A caller hands over a mandate and documents; a fresh reader answers with no memory of this session; the capture lands on disk verbatim beside a sidecar that says what ran. This body implements `readers-protocol: 1`. It carries no model id, effort value, window, budget, or transport parameter: those live in the roster (`${CLAUDE_PLUGIN_ROOT}/skills/readers/assets/roster.json`) and the contract (`${CLAUDE_PLUGIN_ROOT}/skills/readers/assets/contract.md`), and the runner resolves them. `RUNNER` below is `${CLAUDE_PLUGIN_ROOT}/skills/readers/assets/readers` (the runner's shell entry). Read the contract once per run; every field, status, step, and line form used here is defined there.

**The spine.** Every call, host or portable, is resolved by `suggest` (the first call freezes the run), then passes the runner's pre-send checks, then runs, then is recorded by the runner. The model the checks saw is the model that ran, and a refused call spends nothing.

**The one unforgivable move is a warm reader:** anything from this session (its conversation, its reasoning, its prior findings, another reader's output) reaching the reader. The reader receives the prompt `compose` wrote and nothing else from this session, while the harness's own channels the contract names still reach it.

## Step 0 — The version line

Print `READERS-PROTOCOL: 1` as the first line of the run, before any dispatch, in every form, and repeat it as the first line of the final report so a headless run's output carries it too. Callers key on the `READERS:` lines (Step 4), never on this one.

## Step 1 — Read the summon

- **Summon** (a caller skill): a request block in the contract's fields, one call or a fleet (several calls sharing `run_id` and the caller's authorization, each with its own `row`, `mandate`, `documents` or `workspace`, `profile`, `call_id`, `raw_path`). Ask Tony nothing: the caller's `authorized` flag is his word for an outside row, and its absence refuses the call.
- **Direct** (Tony types it): `/readers <row id> <document path> "<one-line mandate>" [<profile>]`. The profile is `starved` unless the fourth argument names one. Mint `run_id` and `call_id`. When the row is outside (its roster `provider` is not `anthropic`), ask once for the word and wait, unless the invocation itself already carries it as an explicit send instruction (the words "send it"; ordinary prose in the mandate never counts); then set `authorized: true`. Claude rows need no word.
- **Suggest** (`/readers suggest <rows> --run <run id> [--run-dir <dir>] [--floor <floor>]`): run `RUNNER suggest` with those arguments, print its lines (per row: the model, whether it is outside, any drop note), make no call, and stop.

## Step 2 — Prepare every call

1. Make a scratch directory for request files (`mktemp -d`). The run dir is the request's `run_dir` when the caller passed one, else the runner's default.
2. `RUNNER suggest <row>[,<row>...] --run <run id> [--run-dir <run dir>] [--floor <floor>]` once per run, every requested row in one call. Its `model` per row is the model the run sends.
3. Write each call's request JSON to `<scratch>/<call id>.json` with the contract's fields and `protocol_version: 1`. On row `claude-session`, set `session_model` to the exact model id your system prompt says you are powered by; leave it unset on other rows.
4. `RUNNER validate <request file>` prints `valid` or the refusing status. A refusal is the call's status; never repair the request. Its sidecar comes from Step 3's lane step, which refuses again and writes `sidecar.json` alone.

## Step 3 — Run the lane

**Portable rows** (roster `kind: portable`): `RUNNER <request file> > <scratch>/<call id>.result.json`, in the background when the fleet has more than one call, all launched before any host call. The result JSON is the runner's stdout.

**Host rows** (`kind: host`): `RUNNER compose <request file>`, with `--no-workflow` added when the Workflow tool is not among your tools. `status: composed` comes with `call_dir`, `prompt_file`, and `tool`; anything else is the refusal, and its sidecar is written. Then invoke the tool `tool.name` with `tool.params` exactly, the contents of `tool.prompt_file` read verbatim as the parameter `tool.prompt_param` (null means the prompt does not travel as a parameter: on the Workflow route it is already inside the script; on the Agent route it stays at `<call dir>/prompt.md` and `tool.params.prompt` is the runner's short hand-off text that sends the reader to that file, the same on every Agent-route call whatever the document size, so the composed prompt is never pasted into the Agent call), never any parameter under `tool.omit`, and nothing else. The reply is where `tool.capture` says: for the Workflow tool the run's `capture` plus the `tool_uses` count in the run's usage record (one reader per script, so it is the reader's count); for the Agent tool the subagent's final message, ending where the reviewer's text ends (the Agent tool's trailing usage footer, the agent id and usage block, is not the reply); for the Gemini tool the returned text plus the status flag it reported. The Workflow tool reads the script from the working directory copy `compose` wrote; `record` removes it. Several Workflow invocations in one fleet go out in one message.

Write the reply verbatim to `<call dir>/capture.md` (a heredoc or the Write tool; change nothing, and include nothing past the reviewer's text). Then record:
- `RUNNER record <request file> --capture <call dir>/capture.md [--tool-calls <count>] [--transport-status <flag>]`: `--tool-calls` on every Workflow-route call, `--transport-status` on every Gemini call. The runner applies the guards (empty, parity, an error flag under a complete reply).
- A tool that failed, timed out, or returned partial text or a diagnostic string instead of a report: `RUNNER record <request file> --failed "<the tool's own error text>" [--status <status>] [--capture <file holding the partial text>]`.
- A `record` that comes back `invalid-request` with `sidecar: null` is a usage slip (no compose, the wrong request file, an unreadable capture, a missing `--tool-calls`): nothing was written, the call keeps its id; fix the slip and record again.
One call, one record. Never re-run a reader for a better answer; a retry is a new call id on the caller's or Tony's word.

## Step 4 — Report

Your final report carries, for every call, one line in this fixed form, bare at the start of a line (no backticks, no bullet, no prefix), immediately followed by the result JSON verbatim (the runner's stdout, in a fenced `json` block), whatever earlier messages already showed:
READERS: <row id> · <status> · <effective model id> · <raw path | none> · <sidecar path>
`<effective model id>` is the result's `effective_model`, or `none` when it is null (a call refused before the model was resolved); `<raw path>` is the result's `raw_path` or `none`; `<sidecar path>` is the result's `sidecar`, or `none` when it is null (a usage slip the runner returned without writing: fix the slip and record again under the same call id). In the direct form, also print `raw_text` in chat, and file a copy only when Tony names a path (`raw_path`).

## The rules

1. **Cold means cold.** The reader gets the prompt `compose` wrote and nothing else from this session (the harness's own channels the contract names do reach it): no added context, no summary of the documents, no other reader's output.
2. **The runner decides.** Statuses, models, parity lines, and paths come from the runner's JSON; this body never restates or overrides them.
3. **One word per outside call.** The caller's `authorized` flag, or Tony's word in the direct form; a fleet authorizes the calls it enumerates and nothing else; a retry needs the word again.
4. **Secrets.** Never read `~/.zshrc`; never print a credential; a key's existence is checked only the way the contract says.
5. **Report faithfully.** A refusal, a failure, and an empty reply are results with their own `READERS:` lines; never a retry, never a softened status.

## What NOT to do

- Don't type a model id, effort, window, or tool parameter from memory; take them from `compose`'s output.
- Don't pass the prompt through Workflow `args`; the script carries it.
- Don't ask Tony about lanes when a caller summoned you, and don't skip the ask in the direct form on an outside row.
- Don't edit `raw.md`, a sidecar, or a capture, and don't file a copy under `docs/` unless the caller or Tony named the path.
- Don't run a reader twice to get a better answer.
