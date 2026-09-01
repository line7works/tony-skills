# mcp-obsidian-worker

## What this is

The implementation spec for **the Cloudflare Worker that serves the `Obsidian Vault` MCP
server on claude.ai web**. The Worker exposes ~30 MCP tools (read / inspect / discover /
query / write / modify / destructive / hygiene) wrapping the Obsidian Local REST API.

This folder holds `IMPLEMENTATION.md` **only**. It is a spec, not an installable tool;
`tools/` explicitly covers specs for code that lives elsewhere. The real code is the
deployed Worker on Cloudflare.

## Why it is here

As of 2026-07-27 this document existed in exactly one place: `~/Documents/mcp-obsidian-worker/`,
inside iCloud, with no git repo and no second copy. Because `~/Documents` is iCloud-synced,
both of Tony's Macs saw the same single folder — so what looked like two copies was one.

The Worker's actual source (`src/index.ts`, `wrangler.jsonc`) is **not** in that folder and
is not known to exist on either machine. The deployed Worker is likely the only surviving
copy of the code. That makes this spec the highest-value recoverable artifact: it describes
all 30 tools, the audit log, optimistic concurrency, and trash semantics in enough detail to
rebuild from.

## Architecture

```
claude.ai web  ──> Worker (MCP, ~30 tools) ──> mcp.line7.works ──> Mac Studio Obsidian
Claude Code    ─────────────────────────────> mcp.line7.works ──> Mac Studio Obsidian
```

Claude Code reaches the vault directly over the tunnel and does not go through the Worker.
Claude **Desktop** uses neither — its MCP config points at a local `uvx mcp-obsidian`.

## Invariants the spec declares (do not drift from these)

- `ALLOWED_EMAILS = new Set(["<owner-email>"])` — single-user email gate (set to the vault owner's Google account email)
- `OBSIDIAN_API_BASE = https://mcp.line7.works`
- `McpServer({ name: "Obsidian Vault", version: "1.0.0" })`
- `export default new OAuthProvider({...})` and its config
- `wrangler.jsonc`, `tsconfig.json`, `worker-configuration.d.ts`

## Dependencies

None to store this. To rebuild or redeploy the Worker: Node, `wrangler`, a Cloudflare
account with the Worker, and the `OBSIDIAN_API_KEY` secret set on it
(`wrangler secret list` to confirm).

## Caveats

- **This is not the source.** Recovering `src/index.ts` from Cloudflare yields the esbuild
  *bundle*, with dependencies inlined — readable and redeployable, but not the original
  TypeScript. Rebuilding from this spec will produce cleaner code than un-bundling.
- **There is no `wrangler download` command.** Retrieval is via the dashboard
  (Workers & Pages → the Worker → Edit code) or the Workers Scripts API.
- **`wrangler.jsonc` is not recoverable as a file.** Its effective settings (routes,
  compatibility date, bindings, secret *names*) are visible in the dashboard and can be
  reconstructed from there.
- The original copy still lives at `~/Documents/mcp-obsidian-worker/IMPLEMENTATION.md`.
  Two copies can now diverge; treat this one as canonical and delete the iCloud copy once
  this is merged.
