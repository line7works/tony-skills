# antigravity-mcp

An MCP server that exposes Google Antigravity's `agy` CLI as a tool, so a Claude Code
session can consult Gemini Pro the same way it consults Codex.

## Why this exists

Codex plugs straight into Claude Code because the Codex CLI ships an MCP server mode
(`codex mcp-server`). Antigravity is wired the other way round: `agy` **consumes** MCP
servers, it does not serve as one. There is nothing to proxy, so this wrapper shells out
to `agy --print --output-format json` and reshapes the envelope into an MCP tool result.

Installing the Antigravity IDE does not give you `agy`. It is a separate binary:

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash   # installs ~/.local/bin/agy
agy                                                           # once, to authenticate
```

Auth is shared with the IDE through the macOS keyring.

## Install

```bash
cd tools/antigravity-mcp
npm install
claude mcp add antigravity --scope user -- node "$PWD/src/server.js"
```

Verify with `claude mcp list`. Set `AGY_BIN` if `agy` is not at `~/.local/bin/agy`.

## Tools

### `ask_gemini`

| Arg | Default | Notes |
| --- | --- | --- |
| `prompt` | required | The question. |
| `model` | `gemini-3.1-pro-high` | See `list_models`. |
| `mode` | `plan` | `plan` or `accept-edits`. Not a write guard, see below. |
| `effort` | model default | `low` / `medium` / `high`. |
| `cwd` | server cwd | Becomes the agent's workspace. |
| `add_dirs` | none | Extra workspace directories. |
| `conversation_id` | none | Resume a thread. Returned by every call. |
| `timeout_ms` | 600000 | Hard kill. `agy`'s own deadline is set to 90% of it. |
| `skip_permissions` | `false` | Auto-approves every tool. This is the real safety switch. |

### `list_models`

Returns the model ids currently available.

## Three behaviours of `agy` this wrapper works around

All three were verified against `agy` 1.1.11 on 2026-08-07.

**1. The spawn cwd is not the workspace.** Run `agy -p` inside a directory and it still
reports "you did not have an active workspace", fails to read the project, and answers
from nothing. The server always passes `--add-dir <cwd>`. This, not permissions, was the
cause of the empty answers seen during the build.

**2. A fully-denied run still reports `status: SUCCESS`.** When headless mode auto-denies
a tool it cannot prompt for, `agy` returns `"response": ""` with a success status, having
already burned the tokens. The server treats an empty response as an error and surfaces
the CLI's own diagnostic, so a silent nothing never reaches the caller.

**3. `--mode plan` does not prevent writes.** Tested directly: in plan mode with
`--dangerously-skip-permissions`, the agent was asked to create a file and did so. Plan
mode biases the agent toward analysis; it is not a sandbox. The guard that actually holds
is leaving `skip_permissions` off, which is the default.

`agy` also emits glog preamble lines (`ERROR: logging before google.Init: ...`) on both
streams. They are noise, not failures. `extractEnvelope` scans upward for the last line
that parses as JSON.

## Permissions

`agy` reads `~/.gemini/antigravity-cli/settings.json` (machine-level, not in this repo).
Rules are `action(target)` with precedence deny > ask > allow. The working config on this
machine is read-only and scoped to `~/Developer`, with explicit denies over `~/.ssh`,
`~/.aws`, `~/.config`, `~/.gmail-mcp`, `~/.claude`, and the Obsidian vault.

Two things to know before widening it. Prefix rules do not match shell pipelines: with
`command(env)` and `command(grep)` both allowed, `env | grep PWD` is still denied. And
anything the agent reads is sent to Google, so workspace scope is a disclosure decision,
not just a correctness one.

Denials are diagnosable. `~/.gemini/antigravity-cli/cli.log` logs the exact rejected
command under `permission_manager.go`.

## Test

```bash
node test/smoke.mjs
```

Starts the server over stdio, lists its tools, and makes one real Flash-tier round trip.
Requires `agy` installed and authenticated.
