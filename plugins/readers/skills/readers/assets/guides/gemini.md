# Prompting guide — the Gemini row (`gemini`)

Documentation for mandate authors and for whoever debugs the lane. Nothing in this file is runtime text; the runner reads none of it, and the skill body takes every parameter from `readers compose`, never from here. The row is `gemini-3.1-pro-high`, a host lane: the runner composes the prompt and the working directory, the skill body calls the `mcp__antigravity__ask_gemini` tool (the wrapper in `tools/antigravity-mcp/`, which shells out to Google Antigravity's `agy` CLI), and the reply goes back to `readers record`. The runner never rewrites a caller's mandate.

## Verified behaviours of the tool, each with its source

1. **The spawn cwd is not the workspace; `--add-dir` is.** Run `agy -p` inside a directory and it still reports "you did not have an active workspace" and answers from nothing. The wrapper always passes `--add-dir <cwd>`, so the `cwd` the tool receives is the reader's workspace. Source: `tools/antigravity-mcp/README.md`, "Three behaviours of `agy` this wrapper works around", item 1 (verified against `agy` 1.1.11, 2026-08-07); the same fact is a repo invariant in `AGENTS.md`. Consequence for readers: the working directory `compose` prints per profile (a fresh empty `<call dir>/work` under `starved`, `<call dir>/packet` holding copies of the documents under `packet-only`, the caller's workspace under `repo`) is exactly what the reader can see, and everything under it ships to Google (`README.md`, "Permissions": "workspace scope is a disclosure decision").
2. **An empty response is a failed run, whatever the status says.** When headless mode auto-denies a tool it cannot prompt for, `agy` returns `"response": ""` under `status: SUCCESS`, the tokens already spent. Source: `tools/antigravity-mcp/README.md`, item 2. readers' guard: `record` marks empty or whitespace content `empty` (`contract.md`, "The Gemini lane" and "Host lanes: compose and record"). Measured 2026-09-06 (`docs/evidence/readers/slice-c-host-runs.md`, AC6): a mandate that asked the reader to create a file was auto-denied and the whole reply came back empty, so **a Gemini mandate must never ask the reader to write** (the roster's `gemini` quirks line records the trap).
3. **Plan mode is not a write guard.** Tested directly: in `--mode plan` with permissions skipped, the agent was asked to create a file and did so. Source: `tools/antigravity-mcp/README.md`, item 3. readers never passes `mode` (`contract.md`, "The Gemini lane"; `compose` lists it under `tool.omit`).
4. **`skip_permissions` off is the only real guard.** The wrapper's `skip_permissions` argument auto-approves every tool and "is the real safety switch"; leaving it off (the default) is what holds. Source: `tools/antigravity-mcp/README.md`, the `ask_gemini` argument table and item 3. readers never passes `skip_permissions` (`tool.omit`), so the guard is always on; the measured result is the roster's `sandbox-enforced` isolation label for `starved` and `packet-only` (`repo` stays `unmeasured`).
5. **Content decides over the status flag.** `agy` can report ERROR while delivering a complete response (verified live 2026-08-21). Source: vertical SKILL.md:58 as it stood before Slice F rewrote it (git `957327d^`; the rule now lives in `contract.md`, "The Gemini lane", which cites that line). readers' `record` applies it: a non-empty, complete, mandated-format reply under an error flag is `ok` with the anomaly in `reason`; partial text or a diagnostic string under an error flag is `transport-failed`, the text kept in diagnostics.
6. **Effort is the model-name suffix, never also a parameter.** `model: "gemini-3.1-pro-high"`: the `-high` suffix IS the effort setting; never also pass the `effort` param. Source: jpb's `assets/box-runners.md:81` as written before Slice G retired that file into a pointer (git `aa58238^`; the roster's `gemini` row carries the rule as `effort_encoding: suffix` and its quirks line). readers never passes `effort` (`tool.omit`); a request's `effort` on this row selects the suffix through the roster's `efforts` list.

## How the composed prompt is laid out for it

`compose` writes `<call dir>/prompt.md` and prints the tool call: `name: mcp__antigravity__ask_gemini`, `params: {model, cwd}` passed exactly, `prompt_param: prompt` (the file's contents, verbatim), `omit: effort, mode, skip_permissions, add_dirs, conversation_id, timeout_ms`. The prompt, top to bottom (`readers.py`, `GEMINI_PREFIX`, `GEMINI_PROFILE_LINES`, `compose`):

```
READER INSTRUCTIONS (fixed by readers; the mandate follows them):
- You are a cold reader. Report everything you find; your reply is captured verbatim.
- Use no web search or fetch tool.
- Access profile <profile>: <the profile line: the working directory is empty on purpose | holds copies of the documents in this message and nothing else | is the workspace to read>

<the mandate, byte for byte>

<<<DOCUMENT name>>>
...
<<<END DOCUMENT>>>
```

Under `repo` with no documents the trailer is `<<<WORKSPACE>>>` / "Your working directory holds the material to read." / `<<<END WORKSPACE>>>` instead. The tool has no web switch, so the fixed prefix is the whole no-web parity; the row's `parity` line per profile (`skip_permissions off, cwd = <per profile>, non-empty response`) is what the sidecar records. The reply's trailer line (conversation id, model, mode, timing, tokens) is part of the verbatim capture; the skill body passes the tool's status word to `record --transport-status` (`SUCCESS` on a clean reply, the tool's own error text otherwise).

## Writing the mandate

- Put the task, the output contract, and the grounding rule in the mandate; the fixed prefix carries only "report everything", "no web", and the profile line. The block structure in `guides/gpt.md` works here too; the tag names are conventions for the author, not something the runner adds.
- Never ask the reader to write, create, or run anything: a denied tool call empties the reply (behaviour 2) and the call is `empty`, nothing delivered.
- Under `repo`, say what to read and where the answer must be grounded; the reader may read anything under `cwd`, and anything it reads is sent to Google. Point `workspace` at an export or a worktree, never the live checkout (vertical's rule).
- Do not restate the model id, effort, or `cwd`; the runner resolves them and the body passes what `compose` printed.
