# Tony Tools

Everything worth preserving that Claude Code does **not** install, so it lives
outside `plugins/` and is not listed in `.claude-plugin/marketplace.json`.

That covers macOS automations, dotfiles, and standalone scripts you copy onto a
Mac directly, and also implementation specs and design docs for code that lives
somewhere else (a deployed service, another repo). If it was built on one of
Tony's machines and should outlive that machine, it belongs here — a thing does
not have to be installable to be worth keeping.

Each is a self-contained folder with its own `README.md` covering what it is, its
dependencies, and how to install or use it. For a spec rather than a tool, the
README should say plainly that it is a spec and where the real code lives.

## Tools

- `gmail-mcp/` — multi-account Gmail MCP server. Registers with Claude Code as `gmail` and
  reaches every authorized inbox at once by alias, which claude.ai's Google connector
  cannot do (it holds one OAuth grant; a second Gmail replaces the first). Real source,
  installable; runs from this checkout rather than a copy.

- `antigravity-mcp/` — MCP server wrapping Google Antigravity's `agy` CLI, so a Claude
  Code session can consult Gemini Pro the way it consults Codex. Needed because `agy`
  consumes MCP servers but does not serve as one, so there is no built-in bridge. Real
  source, installable; runs from this checkout. Registers as `antigravity`.

- `arcade-publish/` — the findings ledger (`punch-list.md`) for the arcade-publish CLI,
  and nothing else. The code moved to `plugins/arcade/assets/` on 2026-08-12 so the
  `/arcade` skill and the terminal command share one copy; the ledger deliberately stayed
  behind as the single consolidated list. See `plugins/arcade/assets/README.md`.

- `mcp-obsidian-worker/` — implementation spec for the Cloudflare Worker serving the
  `Obsidian Vault` MCP server on claude.ai web. Spec only; the Worker source is not here
  and may not exist on disk anywhere.

_(copy-on-select was sunset 2026-07-21 — archived at
`~/Developer/_archive/copy-on-select/`; still in this repo's git history.)_

## Conventions

- One folder per tool, named for the tool.
- Every tool folder has a `README.md` (what / why / dependencies / install /
  caveats).
- Keep install steps copy-pasteable and note any manual step (like an
  Accessibility grant) that can't be automated.
- New-Mac setup: install the tools here alongside the terminal/shell setup.
