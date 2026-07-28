# mcp-obsidian-worker — Implementation Doc

Single source of truth for the rewrite of `src/index.ts`. Scope: a Cloudflare
Worker that exposes an MCP server wrapping the Obsidian Local REST API
plugin, designed for a vault that is read/written/curated **primarily by
LLMs**, with a human-in-the-loop directing intent and approving destructive
actions in chat.

---

## Table of contents

1. [Context & goals](#1-context--goals)
2. [Repo invariants — do not touch](#2-repo-invariants--do-not-touch)
3. [File structure & code layout](#3-file-structure--code-layout)
4. [Cross-cutting concerns](#4-cross-cutting-concerns)
   - 4.1 [`obsidianFetch` rewrite](#41-obsidianfetch-rewrite)
   - 4.2 [Audit log](#42-audit-log)
   - 4.3 [Optimistic concurrency (`expected_mtime`)](#43-optimistic-concurrency-expected_mtime)
   - 4.4 [Trash semantics](#44-trash-semantics)
   - 4.5 [Human-confirm gate (docstring convention)](#45-human-confirm-gate-docstring-convention)
   - 4.6 [Helpers](#46-helpers)
5. [Tools — full reference](#5-tools--full-reference)
   - [READ (10)](#read-10)
   - [INSPECT (3)](#inspect-3)
   - [DISCOVER (1)](#discover-1)
   - [QUERY (2)](#query-2)
   - [WRITE (5)](#write-5)
   - [MODIFY (2)](#modify-2)
   - [DESTRUCTIVE (4)](#destructive-4)
   - [HYGIENE (3)](#hygiene-3)
6. [Pre-flight checklist](#6-pre-flight-checklist)
7. [Verification](#7-verification)
8. [Out of scope](#8-out-of-scope)
9. [Open questions / resolved ambiguities](#9-open-questions--resolved-ambiguities)
10. [Final report template](#10-final-report-template)

---

## 1. Context & goals

`src/index.ts` is a Cloudflare Worker exposing an MCP server that wraps the
[Obsidian Local REST API plugin](https://github.com/coddingtonbear/obsidian-local-rest-api).
Today: 8 tools. After this rewrite: **30 tools**, plus cross-cutting features
(audit log, optimistic concurrency, soft-delete trash). The vault is owned
by the user but written by an LLM acting on the user's chat instructions.

**Design principles:**

- **Recoverability over speed.** Every write is logged; every delete is reversible without a backup.
- **Pre-bake common queries.** LLMs choose tools by name; making `get_files_by_tag` exist is more valuable than a clever `query_jsonlogic`.
- **Behavioral safety first.** Where MCP can't enforce confirmation, docstrings instruct the LLM to ask in chat. Hard-delete and similar irreversible ops use Zod literal guards on top of that.
- **Tool-count discipline.** ~30 tools is the upper edge of where models tool-pick cleanly. Convenience wrappers earn their keep when they pre-bake a common combo (e.g. `set_frontmatter_field`). Pure sugar that the LLM can compose in one turn (e.g. an old `read_anchors` = `list_files` + filter + `read_files`) is cut.
- **Single file.** Keep `src/index.ts` cohesive until it crosses ~1500 lines or someone other than the user starts editing it.

**What this rewrite is NOT:**

- A refactor of the OAuth/Access infrastructure.
- A change to deployment, secrets, or `wrangler.jsonc`.
- A test-suite addition (no harness exists; manual verification only).

---

## 2. Repo invariants — do not touch

These stay byte-identical:

- `import` block at the top of `src/index.ts`
- `ALLOWED_EMAILS` constant (`new Set(["tonycoon@gmail.com"])`)
- `OBSIDIAN_API_BASE` constant (`https://mcp.line7.works`)
- `MyMCP extends McpAgent<Env, Record<string, never>, Props>`
- `server = new McpServer({ name: "Obsidian Vault", version: "1.0.0" })`
- The email gate at the top of `init()`
- `export default new OAuthProvider({...})` and its config
- `wrangler.jsonc`, `tsconfig.json`, `worker-configuration.d.ts`

Bump `version: "1.0.0"` → `"2.0.0"` in the McpServer constructor (the only
metadata change). Tool count nearly quadrupling justifies a major bump.

---

## 3. File structure & code layout

`src/index.ts` is organized top-to-bottom as:

```
imports
constants (ALLOWED_EMAILS, OBSIDIAN_API_BASE, TRASH_FOLDER, AUDIT_LOG_PATH)
type aliases (McpTextResponse, ErrorBody, NoteJson, etc.)
class MyMCP {
  server = ...

  // --- Cross-cutting helpers ---
  private encodeVaultPath(...)
  private encodeFrontmatterTarget(...)
  private generateBlockId()
  private async obsidianFetch(...)
  private async appendAuditLog(...)
  private async getMtime(path)
  private async assertMtimeMatch(path, expected)

  async init() {
    if (!ALLOWED_EMAILS.has(this.props!.email)) return;

    // === READ ===
    this.server.tool("list_files", ...)
    ...

    // === INSPECT ===
    ...

    // === DISCOVER ===
    ...

    // === QUERY ===
    ...

    // === WRITE ===
    ...

    // === MODIFY ===
    ...

    // === DESTRUCTIVE ===
    ...

    // === HYGIENE ===
    ...
  }
}

export default new OAuthProvider({...})
```

Group dividers (`// === <Group> ===`) are mandatory — they are how a future
reader navigates a 1000+ line `init()`.

---

## 4. Cross-cutting concerns

### 4.1 `obsidianFetch` rewrite

**Bug being fixed:** current code force-sets `Content-Type: application/json`
on any request with a body, clobbering `text/markdown` PATCH/POST bodies.

**New rules, in order:**

1. Build URL: `${OBSIDIAN_API_BASE}${path}`.
2. Set `Authorization: Bearer ${env.OBSIDIAN_API_KEY}`.
3. **Content-Type defaulting:** only set if (a) body present, (b) caller did not set one, **and** (c) body looks like JSON (`body.trimStart().startsWith("{") || body.trimStart().startsWith("[")`). Otherwise, leave unset — caller's explicit header wins, no default.
4. `fetch` the URL; read `body = await res.text()`.
5. **On non-2xx:** parse body as JSON and look for `{ errorCode: number, message: string }`. Compose a friendly prefix from the error-code map below. `console.log` a single line: `OLRAPI ${method} ${path} → ${status} ${errorCode ?? "?"} ${message ?? ""}`. Return `{ isError: true, content: [{ type: "text", text: `${prefix} (HTTP ${status}, errorCode ${errorCode}): ${message}\n--- raw body ---\n${body}` }] }`.
6. **On 2xx:** if this is a write/modify/destructive call, fire-and-forget (`ctx.waitUntil` if available, else just don't `await`) `appendAuditLog(...)`. Then return `{ content: [{ type: "text", text: body }] }`.

**Error-code prefix map:**

| `errorCode` | Prefix |
| --- | --- |
| `40101` | `Auth failed (bad/missing API key)` |
| `40053` | `Missing required header` |
| `40400` | `File or target not found` |
| `40500` | `Plugin error` |
| any other | `Plugin error <code>` |

Mapping is best-effort; if the body is not JSON, fall back to `HTTP <status>`.

**Optional second arg:** `obsidianFetch(path, init, opts?: { audit?: AuditEntry, suppressAudit?: boolean })`. Audit-log writes themselves pass `suppressAudit: true` to avoid recursion.

### 4.2 Audit log

Every successful non-GET call appends a single line to
`00-meta/llm-edit-log.md` via a direct POST `/vault/00-meta/llm-edit-log.md`
with `Content-Type: text/markdown`. (The plugin auto-creates the file on
first append, so no bootstrap is required.)

Line format (one logical line, no embedded newlines):

```
- {iso-ts} `{tool_name}` {method} `{path}` → {status} {extra}
```

Where `extra` is tool-specific freeform context (e.g. for `delete_file`:
`(soft → 99-trash/2026-05-06-…)`; for `move_file`: `→ {to}`; for
`patch_file`: `target=heading::Foo op=append`).

**Implementation:**

- The audit appender is `private async appendAuditLog(entry)`.
- Called from inside `obsidianFetch` on 2xx for non-GET, **only when the caller passed an `audit` opt**. (Prevents the audit-write itself from triggering recursion, and lets read-shaped writes — there shouldn't be any — opt out.)
- Failure to write the audit log must NOT fail the parent operation. Wrap the call in try/catch; on failure, `console.warn` and continue.
- Tool authors compose the `extra` string in the tool body and pass it via the second arg of `obsidianFetch`.

**File location is fixed.** `00-meta/llm-edit-log.md`. No need to make it
configurable; the user can rename later by editing the constant.

### 4.3 Optimistic concurrency (`expected_mtime`)

Every WRITE / MODIFY / DESTRUCTIVE tool that operates on an **existing**
file (i.e. not `create_file` overwrites and not `append_to_inbox` of a new
file) gets an **optional** `expected_mtime: z.number().optional()`. Param
docstring: *"Unix-ms mtime returned by `get_file_metadata`. If supplied,
the operation aborts when the file has been modified since. Use this when
you read-then-write to detect concurrent edits."*

**Implementation:**

- `private async assertMtimeMatch(path, expected): Promise<McpTextResponse | null>` — returns `null` if OK, otherwise an error response that the tool returns directly.
- Reads `/vault/<path>` with `Accept: application/vnd.olrapi.note+json`, parses, compares `stat.mtime` to `expected` exact-equal.
- On mismatch: error message `"File modified since you last read it. Expected mtime ${expected}, current ${actual}. Re-read and try again."`
- Tools that accept `expected_mtime` call this as the first thing inside their handler. If `expected_mtime === undefined`, skip the check.

This is one extra API call per gated write. Cost is acceptable for the
safety it buys; LLMs are slow enough that the latency isn't noticeable.

### 4.4 Trash semantics

- **Constant:** `const TRASH_FOLDER = "99-trash";`
- **`delete_file`** does NOT call DELETE on the plugin. It:
  1. Reads the file (markdown).
  2. Computes a trash path: `99-trash/<YYYY-MM-DD-HHMMSS>-<slugified-original-path>.md`. Slugification: replace `/` with `__`, strip leading dots, percent-encoding only on the URL side.
  3. PUTs the file to the trash path (`Content-Type: text/markdown`).
  4. PUT also a sidecar JSON at `99-trash/<same-stem>.meta.json` with `{ original_path, deleted_at, deleted_by_tool: "delete_file" }`. (Used by `restore_from_trash`.)
  5. Calls plugin DELETE on the original path.
  6. Audit-logs `(soft → <trash-path>)`.
- **`restore_from_trash(trash_path, restore_to?)`**:
  1. Reads the file at `<trash_path>`.
  2. Reads the sidecar to determine `original_path` if `restore_to` is not provided.
  3. PUTs to `restore_to ?? original_path`.
  4. DELETEs both the trash file and the sidecar.
  5. Audit-logs.
- **`empty_trash(confirm: z.literal(true), older_than_days?: number)`**:
  1. Lists `99-trash/` (recursive).
  2. Filters by `<= now - older_than_days` if provided (using sidecar `deleted_at` or filename timestamp).
  3. DELETEs each. **This is the only tool that hard-deletes data.**
  4. Audit-logs once with the count.

The trash folder grows unbounded if the user never calls `empty_trash`.
That's a feature, not a bug — disk is cheap, regret is expensive.

### 4.5 Human-confirm gate (docstring convention)

MCP cannot reliably prompt the user mid-tool-call across all clients.
Instead:

- **Tier-1 destructive tools** (`empty_trash`, anything that hard-deletes) have docstrings opening with: *"⚠ DESTRUCTIVE — Before calling this tool, state your intended action in chat and wait for the user to type 'yes' (or equivalent affirmation). Do NOT call this tool speculatively or on a 'best guess'."*
- **Tier-2 substantive writes** (`delete_file` even though soft, `move_file` with `update_backlinks=true`, `active_file` with `op="replace"`, vault-wide hygiene tools) have docstrings opening with: *"⚠ Substantive change — Confirm the target with the user in chat before calling."*
- **Zod guards remain** on top of docstring guidance: `confirm: z.literal(true)` for `empty_trash`; the "type the path again" pattern (`confirm_path: z.string()` that must equal `path`) for `delete_file`.

This is honor-system safety, but combined with the audit log and trash
folder it gives a strong practical safety net.

### 4.6 Helpers

```ts
// Encode a vault-relative path for use after /vault/.
// trailingSlash=true for directory endpoints, false for file endpoints.
private encodeVaultPath(path: string, opts: { trailingSlash?: boolean } = {}): string

// Generate Obsidian's native 6-char alphanumeric block ID (lowercase a-z + 0-9).
private generateBlockId(): string

// Read /vault/<path> as NoteJson and return parsed object, or null on 404.
private async getNoteJson(path: string): Promise<NoteJson | null>

// Returns null if mtime matches, otherwise an error McpTextResponse.
private async assertMtimeMatch(path: string, expected?: number): Promise<McpTextResponse | null>

// Append one line to 00-meta/llm-edit-log.md. Never throws.
private async appendAuditLog(entry: { tool: string; method: string; path: string; status: number; extra?: string }): Promise<void>

// Slugify a vault path for use as a trash filename component.
private trashifyPath(originalPath: string): string  // "10-projects/foo.md" → "10-projects__foo"
```

---

## 5. Tools — full reference

**Total: 30 tools across 8 groups.**

For each tool: name, group, params (Zod), endpoint, behavior, docstring intent.

### READ (10)

#### 1. `list_files` *(updated)*

- **Params:**
  - `path: z.string().default("")` — vault-relative folder, empty = root.
  - `recursive: z.boolean().default(false)`.
  - `max_depth: z.number().int().min(1).max(10).default(2)`.
- **Endpoint:** GET `/vault/<dir>/`.
- **Behavior:**
  - `recursive=false`: single GET, return body as-is.
  - `recursive=true`: BFS from `path`, descend into entries ending in `/`, cap at `max_depth` levels and **1000 entries total**. On cap, append a single `… (truncated at 1000 entries)` line. Output is newline-separated full paths.
- **Docstring:** *"List files and directories in a vault folder. Pass empty path to list root. Set `recursive=true` to walk subdirectories (capped at 1000 entries and `max_depth` levels). For one-level listing, leave `recursive=false`."*

#### 2. `read_file` *(unchanged)*

- **Params:** `path: z.string()`.
- **Endpoint:** GET `/vault/<path>` with `Accept: text/markdown`.
- **Docstring:** *"Read the full markdown contents of a file in the vault."*

#### 3. `read_files` *(new)*

- **Params:** `paths: z.array(z.string()).min(1).max(20)`.
- **Endpoint:** N parallel GET `/vault/<path>` (markdown).
- **Behavior:** `Promise.all`. Format result as `=== <path> ===\n<content>\n\n` per file. Errors inline as `=== <path> (error) ===\n<msg>\n\n`. Never returns `isError: true` — partial success is a feature.
- **Docstring:** *"Read up to 20 files in parallel. Output is delimited by `=== <path> ===` headers. Use this instead of N separate `read_file` calls to amortize round-trips. Also the right tool when reading a folder of related notes (compose with `list_files`)."*

#### 4. `get_file_metadata` *(new)*

- **Params:** `path: z.string()`.
- **Endpoint:** GET `/vault/<path>` with `Accept: application/vnd.olrapi.note+json`.
- **Behavior:** Parse JSON. Drop `content`. Return pretty-printed `{ path, frontmatter, tags, stat }`.
- **Docstring:** *"Get a note's frontmatter, tags, and filesystem stat (ctime/mtime/size) without its content. Use to retrieve `mtime` for `expected_mtime` concurrency, or to inspect frontmatter without paying for the body."*

#### 5. `get_document_map` *(new)*

- **Params:** `path: z.string()`.
- **Endpoint:** GET `/vault/<path>` with `Accept: application/vnd.olrapi.document-map+json`.
- **Behavior:** Pass through.
- **Docstring:** *"List a note's headings, block references, and frontmatter field names without reading content. Use this BEFORE `patch_file` to discover valid `Target` values cheaply — saves you from reading the whole file just to find a heading."*

#### 6. `search` *(unchanged)*

- **Params:** `query: z.string()`, `context_length: z.number().int().min(1).max(1000).default(100)`.
- **Endpoint:** POST `/search/simple/?query=<q>&contextLength=<n>`.
- **Docstring:** *"Full-text search across all files in the vault. Returns matches with surrounding context. For structured queries, use `query_dataview` or `query_jsonlogic`."*

#### 7. `read_project_state` *(unchanged)*

- **Params:** none.
- **Endpoint:** GET `/vault/00-meta/obsidian-setup-log.md`.
- **Docstring:** *"Read the Obsidian setup log at `00-meta/obsidian-setup-log.md`. Use this first when picking up work to get current infrastructure state, decisions locked, and remaining phase breakdown."*

#### 8. `list_recent_files` *(new)*

- **Params:**
  - `limit: z.number().int().min(1).max(100).default(20)`.
  - `since: z.number().optional()` — Unix-ms cutoff. If provided, ignore `limit` and return all files mtime ≥ `since`.
- **Endpoint:** POST `/search/` with `Content-Type: application/vnd.olrapi.jsonlogic+json` and body `{"var":"stat.mtime"}` (returns mtime as `result` for every file).
- **Behavior:** Sort by `result` desc on the worker. If `since`, filter `result >= since`. Slice to `limit` if `since` not provided. Format as `<iso-mtime>\t<path>`, one per line.
- **Docstring:** *"List files most recently modified, newest first. Pass `since` (Unix ms) for everything modified after a cutoff; otherwise top-N by `limit`."*

#### 9. `list_tags` *(new)*

- **Params:** none.
- **Endpoint:** GET `/tags/`.
- **Behavior:** Pass through. Plugin v3.5+.
- **Docstring:** *"List all tags in the vault with usage counts. Includes both inline (`#tag`) and frontmatter tags. Hierarchical tags contribute to parent counts."*

#### 10. `read_periodic_note` *(new)*

- **Params:** `period: z.enum(["daily","weekly","monthly","quarterly","yearly"]).default("daily")`.
- **Endpoint:** GET `/periodic/<period>/` with `Accept: text/markdown`.
- **Docstring:** *"Read the current periodic note for the chosen period. Defaults to daily. Returns 404 if the periodic note hasn't been created yet — use `append_to_periodic_note` to create+append in one step."*

### INSPECT (3)

#### 11. `get_files_by_tag` *(new)*

- **Params:** `tag: z.string()` (with or without leading `#`; stripped if present).
- **Endpoint:** POST `/search/` JSONLogic.
- **Body:**
  ```json
  {"or": [
    {"in": ["#<tag>", {"var": "tags"}]},
    {"in": ["<tag>",  {"var": "tags"}]}
  ]}
  ```
- **Behavior:** Returns the response as-is (array of `{filename, result}`).
- **Docstring:** *"Find all files tagged with the given tag (inline `#tag` or in frontmatter `tags:` list). Hierarchical tags require exact match — use `query_jsonlogic` for prefix matching."*

#### 12. `get_tags_for_file` *(new)*

- **Params:** `path: z.string()`.
- **Endpoint:** GET `/vault/<path>` with NoteJson Accept.
- **Behavior:** Parse, return only `tags`.
- **Docstring:** *"Return the tag list for one file (inline + frontmatter, deduped by the plugin). Cheaper than reading the file when you only need tags."*

#### 13. `get_outgoing_links` *(new)*

- **Params:** `path: z.string()`.
- **Endpoint:** GET file as markdown.
- **Behavior:** Regex `/\[\[([^\]]+)\]\]/g`. For each match, split on `#` (drop heading), then `|` (drop alias), trim, dedupe. Picks up embeds (`![[...]]`) too. Return newline-separated.
- **Docstring:** *"Extract all `[[wikilink]]` targets from a note (deduped, with heading and alias suffixes stripped). Includes embeds. Does NOT resolve to actual paths — wikilinks are by note name, not path."*

### DISCOVER (1)

#### 14. `get_backlinks` *(new)*

- **Params:** `path: z.string()`.
- **Endpoint:** POST `/search/` JSONLogic.
- **Body:**
  ```json
  {"regexp": ["\\[\\[<escaped-bareName>(\\||#|\\])", {"var":"content"}]}
  ```
  Where `bareName = basename(path).replace(/\.md$/i, "")`, regex-escaped.
- **Behavior:** Worker filters out the source `path` from the response. Return newline-separated filenames.
- **Docstring:** *"Find all notes whose content references this note as `[[bareName]]`, `[[bareName|alias]]`, or `[[bareName#heading]]`. Excludes self. Note that wikilinks are name-based, not path-based — name collisions across folders will produce false positives."*

### QUERY (2)

#### 15. `query_dataview` *(new)*

- **Params:** `query: z.string()`.
- **Endpoint:** POST `/search/` with `Content-Type: application/vnd.olrapi.dataview.dql+txt`.
- **Behavior:** Body is the raw DQL. If response indicates Dataview error, prepend `"Dataview plugin not installed or DQL invalid:"` to the error.
- **Docstring:** *"Run a Dataview DQL query (must start with `TABLE`, `LIST`, `TASK`, or `CALENDAR`). Requires the Dataview plugin. Use this for structured tabular reports across the vault."*

#### 16. `query_jsonlogic` *(new)*

- **Params:** `query: z.union([z.string(), z.record(z.any())])`.
- **Endpoint:** POST `/search/` with `Content-Type: application/vnd.olrapi.jsonlogic+json`.
- **Behavior:** If string, pass through; if object, `JSON.stringify`. Always sets the JSONLogic Content-Type explicitly so the new `obsidianFetch` defaults don't kick in.
- **Docstring:** *"Run a JSONLogic query against every note. Available variables: `path`, `content`, `tags` (string array), `frontmatter.<key>` (any), `stat.{ctime,mtime,size}`. Plugin extras: `glob` and `regexp` operators. Returns array of `{filename, result}` for non-falsy matches. Falsy = false, null, 0, [], {}."*

### WRITE (5)

#### 17. `append_to_file` *(unchanged behavior)*

- **Params:** `path: z.string()`, `content: z.string()`, `expected_mtime?: number`.
- **Endpoint:** POST `/vault/<path>` with `text/markdown`.
- **Behavior:** mtime check (if provided), POST, audit-log.
- **Docstring:** *"Append to an existing file (creates if missing). Include leading newline if you need a paragraph break. Pass `expected_mtime` to abort on concurrent edits."*

#### 18. `create_file` *(unchanged behavior)*

- **Params:** `path: z.string()`, `content: z.string()`.
- **Endpoint:** PUT `/vault/<path>` with `text/markdown`.
- **Behavior:** No mtime check (this is an overwrite/create by design). Audit-log.
- **Docstring:** *"Create a new file or overwrite an existing one. ⚠ Overwrites silently. Use `append_to_file` to preserve existing content."*

#### 19. `append_to_inbox` *(unchanged)*

- **Params:** `filename: z.string()`, `content: z.string()`.
- **Endpoint:** POST `/vault/99-inbox/<filename>` with `text/markdown`.
- **Behavior:** Reject path separators in filename. Audit-log.
- **Docstring:** *"Append a note to `99-inbox/`. Use for quick captures, session wraps, or anything that belongs in the inbox per vault conventions. Filename only — no path separators."*

#### 20. `append_to_periodic_note` *(new — replaces old `append_to_daily_note`)*

- **Params:** `period: z.enum(["daily","weekly","monthly","quarterly","yearly"]).default("daily")`, `content: z.string()`.
- **Endpoint:** POST `/periodic/<period>/` with `text/markdown`.
- **Behavior:** Audit-log.
- **Docstring:** *"Append content to the current periodic note for the given period (defaults to daily). Creates the note if it doesn't exist."*

#### 21. `add_block_id` *(new)*

- **Params:**
  - `path: z.string()`.
  - `target_type: z.enum(["heading","block","end_of_file"]).default("end_of_file")`.
  - `target: z.string().optional()` — required when not `end_of_file`.
  - `content: z.string()`.
  - `expected_mtime?: number`.
- **Behavior:** Generate 6-char alphanumeric block ID. Then:
  - `end_of_file` → POST `/vault/<path>` body `\n\n${content} ^${id}\n`.
  - `heading` → PATCH `/vault/<path>` headers `Operation: append`, `Target-Type: heading`, `Target: ${urlEncode(target)}`, `Content-Type: text/markdown`, body `\n${content} ^${id}`.
  - `block` → same as heading but `Target-Type: block`.
  - Return `{ content: [{type:"text", text: `Created block ^${id}`}] }`.
- **Docstring:** *"Append content with a generated 6-char block ID anchor (`^abc123`). Use the returned ID to reference this block from other notes (`[[note#^abc123]]`). `target_type=block` appends after an existing block."*

### MODIFY (2)

#### 22. `patch_file` *(unchanged)*

Full v3 docstring preserved verbatim, including:
- Heading: append/prepend adds content under heading; replace replaces the entire section.
- Block: extends the block's text inline (no new paragraph unless newline included).
- Block-ID-migration warning.
- Frontmatter: replaces field value; use `content_type: 'json'` for lists/objects.
- `create_target_if_missing` is frontmatter-only.

Add `expected_mtime?: number`. Pre-flight mtime check, then PATCH.

#### 23. `active_file` *(new — collapses 4 separate active-file tools into one)*

- **Params:**
  - `op: z.enum(["read","append","replace","patch"])`.
  - `content: z.string().optional()` — required for `append`, `replace`, `patch`.
  - `target_type: z.enum(["heading","block","frontmatter"]).optional()` — `patch` only; required when patching.
  - `target: z.string().optional()` — `patch` only; required when patching.
  - `operation: z.enum(["append","prepend","replace"]).optional()` — `patch` only; defaults to `append`.
  - `content_type: z.enum(["markdown","json"]).default("markdown")` — `patch` only.
  - `create_target_if_missing: z.boolean().default(false)` — `patch` + frontmatter only.
  - `expected_mtime: z.number().optional()` — applies to `replace` and `patch`.
- **Endpoint dispatch:**
  - `read` → GET `/active/` with `Accept: text/markdown`.
  - `append` → POST `/active/` with `text/markdown`. Audit-log.
  - `replace` → mtime check → PUT `/active/` with `text/markdown`. Audit-log.
  - `patch` → mtime check → PATCH `/active/` with headers `Operation`, `Target-Type`, `Target` (URL-encoded), `Content-Type` per `content_type`, optional `Create-Target-If-Missing`. Audit-log.
- **Behavior:** Validate per-op required params (`content` for non-read; `target`/`target_type` for `patch`). Returns 405 if no file is active.
- **Docstring:** *"⚠ `op=replace` is a substantive change — confirm with the user in chat first. Operate on the currently-open note in Obsidian without specifying a path. Use when the user says 'this note', 'here', etc. Modes: `read` returns the content; `append` adds to end; `replace` overwrites the whole file; `patch` does targeted insertion (see `patch_file` for `target_type`/`target`/`operation` semantics — identical here). Returns 405 if no file is active."*

### DESTRUCTIVE (4)

#### 24. `move_file` *(merged with rename_with_backlinks via `update_backlinks` flag)*

- **Params:**
  - `from: z.string()`.
  - `to: z.string()`.
  - `update_backlinks: z.boolean().default(false)`.
  - `expected_mtime?: number`.
- **Behavior:**
  1. mtime check on `from`.
  2. Read `from` (markdown).
  3. PUT `to` with the body. If error, return — do not delete `from`.
  4. If `update_backlinks=true`: compute old `bareName` and new `bareName`. Use `get_backlinks`-style JSONLogic to find every file referencing `[[oldBareName(\\||#|\\])`. For each, GET → regex-replace `\[\[oldBareName(\||#|\])` with `[[newBareName$1` → PUT back. Cap at 200 affected files; if exceeded, abort with an error and tell the user to use the Obsidian UI rename.
  5. DELETE `from`. If error, surface `"Moved to <to> but failed to delete <from>; manual cleanup needed"`.
  6. Audit-log with affected backlink count.
- **Docstring:** *"⚠ Substantive change — Confirm with the user in chat first. Move/rename a file. With `update_backlinks=true`, also rewrites every `[[old-name]]` reference across the vault (capped at 200 files; aborts if exceeded). With `update_backlinks=false`, wikilinks pointing at the old name break."*

#### 25. `delete_file` *(soft-delete to `99-trash/`)*

- **Params:**
  - `path: z.string()`.
  - `confirm_path: z.string()` — must equal `path`. Validate inside the handler with a clear "type the path again" error.
  - `expected_mtime?: number`.
- **Behavior:** Soft-delete sequence per [section 4.4](#44-trash-semantics). Audit-log `(soft → <trash-path>)`.
- **Docstring:** *"⚠ Soft-delete — Confirm with the user in chat first. Moves the file to `99-trash/<timestamp>-<slug>` and writes a sidecar `.meta.json` with the original path. Restorable via `restore_from_trash`. Pass `confirm_path` exactly equal to `path`."*

#### 26. `restore_from_trash` *(new)*

- **Params:**
  - `trash_path: z.string()` — vault-relative, must start with `99-trash/`.
  - `restore_to: z.string().optional()` — defaults to original path from sidecar.
- **Behavior:**
  1. Validate `trash_path` starts with `99-trash/`.
  2. Read sidecar (`<stem>.meta.json`) to determine `original_path` if `restore_to` not provided. If sidecar is missing AND `restore_to` is missing, error.
  3. Read trash file (markdown).
  4. PUT to destination. If destination already exists, error — caller should use a different `restore_to`.
  5. DELETE trash file and sidecar.
  6. Audit-log.
- **Docstring:** *"Restore a file from `99-trash/`. Defaults to its original path (read from sidecar). Errors if the destination already exists — pass `restore_to` to choose a different path in that case."*

#### 27. `empty_trash` *(new)*

- **Params:**
  - `confirm: z.literal(true)`.
  - `older_than_days: z.number().int().min(0).optional()` — if omitted, empties everything.
- **Behavior:**
  1. List `99-trash/` recursively.
  2. Filter by age (using sidecar `deleted_at`, falling back to filename timestamp).
  3. DELETE each file. **This is the only tool that hard-deletes data.**
  4. Audit-log with count.
- **Docstring:** *"⚠⚠ HARD DELETE — irreversible. Before calling: state your intended action in chat and wait for the user to type 'yes'. Empties the `99-trash/` folder. Pass `older_than_days=N` to keep recently-deleted files. `confirm` must be `true`."*

### HYGIENE (3)

#### 28. `set_frontmatter_field` *(new)*

- **Params:**
  - `path: z.string()`.
  - `key: z.string()`.
  - `value: z.union([z.string(), z.number(), z.boolean(), z.array(z.any()), z.record(z.any()), z.null()])`.
  - `expected_mtime?: number`.
- **Behavior:** PATCH `/vault/<path>` with headers `Operation: replace`, `Target-Type: frontmatter`, `Target: <key>`, `Content-Type: application/json`, `Create-Target-If-Missing: true`. Body is `JSON.stringify(value)`. Audit-log.
- **Docstring:** *"Set a frontmatter field by name. Creates the field if missing. Value can be string, number, boolean, list, object, or null. Easier than `patch_file` for common frontmatter writes."*

#### 29. `find_broken_links` *(new)*

- **Params:**
  - `scope_folder: z.string().optional()` — limit to a folder if provided.
- **Behavior:**
  1. Get all wikilinks across vault: POST `/search/` JSONLogic with `{"regexp": ["\\[\\[[^\\]]+\\]\\]", {"var": "content"}]}` to find files with links. (Or fetch all files in `scope_folder`.)
  2. For each result, extract `[[name]]` targets per `get_outgoing_links` logic.
  3. Get the set of all note names in the vault: GET `/vault/` recursively (or scoped).
  4. For each link target not present in the name set, record `{from_path, target}`.
  5. Return as `<from_path>\t→\t<target>` lines, sorted.
  6. Cap at 500 broken links; if exceeded, append `… (truncated)`.
- **Docstring:** *"Find every wikilink whose target note doesn't exist. Slow on large vaults — pass `scope_folder` to limit. Output is `<from>\\t→\\t<missing-target>` per line."*

#### 30. `find_orphans` *(new)*

- **Params:**
  - `scope_folder: z.string().optional()`.
  - `exclude_globs: z.array(z.string()).default(["99-inbox/**","99-trash/**","00-meta/**"])`.
- **Behavior:**
  1. Get all `.md` files (vault or scope).
  2. Get all wikilink targets across the vault (same regex sweep as `find_broken_links`).
  3. For each file in the file set, check whether its bare name appears as a wikilink target. If not, and not matched by any exclude glob, it's an orphan.
  4. Return paths, one per line.
- **Docstring:** *"Find notes that no other note links to. Useful for vault hygiene. Excludes `99-inbox`, `99-trash`, and `00-meta` by default — override with `exclude_globs`."*

---

## 6. Pre-flight checklist

Before any edits to `src/index.ts`:

1. `cp src/index.ts src/index.ts.bak-pre-rewrite-claude-code` — fresh backup distinct from existing `*.bak*` files.
2. Verify `npx tsc --noEmit` passes on the *current* file (baseline).
3. Confirm `OBSIDIAN_API_KEY` secret is set in production (don't deploy yet, but confirm presence so post-rewrite testing isn't blocked):
   `npx wrangler secret list 2>&1 | grep OBSIDIAN_API_KEY` — should show it.
4. Confirm the vault has a `99-inbox/` folder. If `99-trash/` doesn't exist, the first soft-delete will create it. If `00-meta/` doesn't exist, the first audit log line will create the file (and folder, if the plugin permits).

---

## 7. Verification

After implementation:

1. **Type-check:** `npx tsc --noEmit` — must pass with zero errors. Fix in place.
2. **Tool count check:** `grep -c '\.server\.tool(' src/index.ts` → must equal **30** (READ:10, INSPECT:3, DISCOVER:1, QUERY:2, WRITE:5, MODIFY:2, DESTRUCTIVE:4, HYGIENE:3).
3. **Invariants visual diff:** Read the new file and confirm imports, constants, email gate, and OAuthProvider export are byte-identical to the backup (sans the `version` bump).
4. **Local sanity:** `npx wrangler dev` and hit `/mcp` with the OAuth flow. Smoke-test 4 representative tools:
   - `list_files` (recursive=false)
   - `get_file_metadata` for any known file (capture `mtime`)
   - `append_to_file` to a known scratch file with `expected_mtime` from previous step
   - `active_file` with `op="read"` against an open note
5. **Deploy:** **Not done by Claude.** User triggers `npx wrangler deploy` themselves.

---

## 8. Out of scope

- Changes to `wrangler.jsonc`, `tsconfig.json`, `worker-configuration.d.ts`.
- Changes to `src/access-handler.ts`, `src/workers-oauth-utils.ts`.
- Test harness (none exists; manual smoke-test only).
- Removing existing `*.bak*` files in the working tree.
- Git commit / push / deploy.
- Any changes to OAuth, Cloudflare Access policy, or the tunnel.

---

## 9. Open questions / resolved ambiguities

**Resolved during planning:**

- **Tool-count target:** 30. Cuts taken vs. earlier draft: dropped `read_anchors` (LLM composes from `list_files` + `read_files`); dropped `append_unique_line` (YAGNI — add when retry-idempotency proves needed); collapsed 4 active-file tools into one `active_file(op)` tool.
- **JSONLogic shape for `get_files_by_tag`**: matches both `#tag` and `tag` because `NoteJson.tags` may include the `#` prefix on inline tags but not on frontmatter tags. Accepting both is robust.
- **JSONLogic shape for `get_backlinks`**: regex `\\[\\[<bareName>(\\||#|\\])` against `var:content`, with self-exclusion done on the worker side after the response.
- **`add_block_id` semantics for `target_type: "block"`**: interpreted as "append after an existing block id". If a different convention is wanted, only that branch needs to change.
- **`obsidianFetch` Content-Type default**: only auto-set `application/json` when the body looks like JSON (starts with `{` or `[`); never override caller-set headers. Fixes the bug where `text/markdown` PATCH/POST bodies were being mislabeled.
- **Trash slug format**: `<YYYY-MM-DD-HHMMSS>-<path-with-slashes-replaced-by-double-underscore>`. Avoids needing a manifest while keeping original path human-readable.
- **Audit log location**: `00-meta/llm-edit-log.md`. Hardcoded — user can rename later by editing one constant.
- **Backlink rewrite cap**: 200 files. Beyond that, aborts and recommends Obsidian UI. This caps blast radius on a misuse of `move_file` with `update_backlinks=true`.

**Open (will be decided at code time):**

- Whether `find_broken_links` and `find_orphans` should respect `.obsidianignore` or similar. Default: no — too plugin-specific. They respect `exclude_globs` instead.
- Whether to expose `Apply-If-Content-Preexists` and `Trim-Target-Whitespace` headers on `patch_file`. Default: no — out of scope, can add later if needed.

---

## 10. Final report template

After implementation, print to user:

```
Rewrite complete. src/index.ts: <line-count> lines.
Tools: 30 across 8 groups.
  READ (10):       list_files, read_file, read_files, get_file_metadata,
                   get_document_map, search, read_project_state,
                   list_recent_files, list_tags, read_periodic_note
  INSPECT (3):     get_files_by_tag, get_tags_for_file, get_outgoing_links
  DISCOVER (1):    get_backlinks
  QUERY (2):       query_dataview, query_jsonlogic
  WRITE (5):       append_to_file, create_file, append_to_inbox,
                   append_to_periodic_note, add_block_id
  MODIFY (2):      patch_file, active_file
  DESTRUCTIVE (4): move_file, delete_file, restore_from_trash, empty_trash
  HYGIENE (3):     set_frontmatter_field, find_broken_links, find_orphans

Cross-cutting:
  - obsidianFetch: Content-Type default fixed; error-code map; non-2xx logged.
  - Audit log: 00-meta/llm-edit-log.md, every successful non-GET call.
  - Optimistic concurrency: optional expected_mtime on existing-file writes.
  - Trash: delete_file is soft (→ 99-trash/); empty_trash is the only hard-delete.
  - Human-confirm gate: docstring convention on tier-1 destructive tools.

Resolved ambiguities: see IMPLEMENTATION.md §9.
Verification: npx tsc --noEmit passed. Tool count grep matches 30.
Deploy: NOT done. Run `npx wrangler deploy` when ready.
```
