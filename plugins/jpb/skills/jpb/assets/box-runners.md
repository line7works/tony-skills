# Box runners — the committed invocation mechanism for all six boxes

This file is the mechanism, not a memo: the fleet launcher (Slice B's
SKILL.md) executes these recipes verbatim. The verified traps each recipe
guards against are recorded inline — do not rediscover them.

Prompt composition (every box, identical): take `box-mandate.md`, replace
its `[TEMPLATE]` token with the full contents of `box-template.md`, append
`\n---\n\nThe brief:\n\n` plus the (scrubbed) brief. Every box output goes
through `validate-box.py`; INVALID means the box is dropped with the
validator's reasons recorded.

Parity rule (applies to every route): web access must be OFF and its
off-state RECORDED per box in the run's evidence/output doc, using the
route's mechanism named below. A box whose no-web parity cannot be
established is dropped for the run and the doc says so.

## DeepSeek — `deepseek/deepseek-v4-pro` · Grok — `x-ai/grok-4.5` (OpenRouter)

    ./openrouter-box.sh <model-id> <composed-prompt-file> <out-file>

`OPENROUTER_API_KEY` from the environment. NEVER echo, cat, or otherwise
print the key — anything printed lands in the session transcript
permanently (it happened 2026-08-11; the key had to be rotated). To check
it exists, run `[ -n "$OPENROUTER_API_KEY" ] && echo set` and nothing
else. The script enforces the full
guard (HTTP 200, no top-level `error`, `finish_reason == "stop"`, non-empty
content) and exits 1 on FAILED without writing the box file. `max_tokens`
8000 — both are reasoning models; thinking can eat a small budget.
Parity: OpenRouter chat completions do not browse unless the model id
carries `:online` — record "no :online suffix" as the parity line.

## GPT — `gpt-5.6-sol` (codex MCP)

`mcp__codex__codex` with exactly:
- `model: "gpt-5.6-sol"`
- `base-instructions`: the composed mandate+template (no brief)
- `prompt`: the brief
- `sandbox: "read-only"`
- `cwd`: a neutral empty directory (never a repo)
- `config: {"web_search": "disabled"}` — string enum, not boolean

Guard: response content must parse as a box and pass the validator.
Parity: record `web_search: disabled` from the invocation as the parity line.

## Fable — `claude-fable-5` · Opus — `claude-opus-5` (Workflow)

Run `claude-boxes.workflow.js` (committed beside this file) via the
Workflow tool, with the composed prompt embedded IN the script body.
Verified trap: the Workflow `args` input can arrive in the script as a JSON
string, so `args.prompt` is undefined — never pass the prompt via `args`.

Substitution (verified trap, 2026-08-11): replace the backtick-delimited
placeholder literal on the `const prompt = ` line — the backticks included
— and assert exactly one occurrence before substituting. Never do a bare
replace of the placeholder token alone: any other occurrence of the token
(e.g. in a comment) would receive the full prompt, whose first newline
breaks out of a `//` comment and fails the script parse.

Escaping (verified trap, 2026-08-11 — load-bearing): the prompt lands in a
JS template literal, and a real brief carries fenced code blocks. Escape
in this order before substituting: backslashes, then backticks, then
`${` — in Python:

    esc = p.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
    target = '`' + '__COMPOSED_PROMPT__' + '`'   # backticks included
    assert tmpl.count(target) == 1
    out = tmpl.replace(target, '`' + esc + '`')
The bare Agent tool has no effort parameter; the workflow's `agent()` opts
pin `model` and `effort: 'high'` — that pinning is the whole reason this
route uses Workflow.

Guard: empty/`null` agent result = FAILED run; output must pass the
validator. Parity: the workflow result's per-agent `toolCalls` count must
be 0 (the box needs no tools; any tool call voids no-web parity) — record
`toolCalls: 0` per box as the parity line.

## Gemini — `gemini-3.1-pro-high` (antigravity MCP)

`mcp__antigravity__ask_gemini` with exactly:
- `model: "gemini-3.1-pro-high"` — the `-high` suffix IS the effort
  setting; never also pass the `effort` param
- `prompt`: the fully composed prompt
- `cwd`: a neutral empty directory (never a repo — the workspace ships to
  Google)
- `skip_permissions` OFF (omit it)

Guard: an EMPTY response is a FAILED run — a fully-denied `agy` run still
reports SUCCESS, so emptiness is the only failure signal. Output must pass
the validator. Parity: with `skip_permissions` off and a neutral empty
`cwd`, the agent has no granted web tool and nothing to read; record
"plan mode, skip_permissions off, neutral cwd, non-empty response" as the
parity line.
