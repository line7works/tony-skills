# gmail-mcp

## What this is

A **multi-account Gmail MCP server**. Registers with Claude Code as `gmail` and exposes one
set of tools across every authorized inbox at once, addressed by short alias.

Unlike `mcp-obsidian-worker/`, this folder holds the real source. It is installable.

## Why it exists

claude.ai's Google connector holds exactly **one** OAuth grant. Connecting a second Gmail
*replaces* the first rather than adding to it, and the same ceiling applies to Notion and
Drive. Multi-account connectors are an open, heavily-upvoted feature request
([anthropics/claude-code#27302](https://github.com/anthropics/claude-code/issues/27302),
still open as of 2026-07-28).

Every off-the-shelf multi-account Gmail MCP on GitHub had 0-5 stars and no meaningful
review. That is a bad place to put a long-lived refresh token for a business inbox, so this
was built in-house instead. Nothing third-party ever sees the tokens.

## What it can do

Scope granted is `gmail.modify`: read, compose, send, label, archive, trash. It deliberately
stops short of `https://mail.google.com/`, so **permanent deletion is structurally
impossible** — worst case is Trash, which Gmail holds for 30 days.

| Tool | Purpose |
|---|---|
| `list_accounts` | Which aliases map to which inboxes |
| `search_threads` | Gmail query syntax, returns thread ids and snippets |
| `read_thread` | Full headers and plain-text bodies |
| `create_draft` | Save a draft without sending |
| `send_message` | Send immediately; requires `confirm: true` |
| `list_labels` | Label names and ids |
| `modify_labels` | Archive, mark read, star, apply custom labels |
| `trash_message` | Move to Trash (recoverable) |

Every tool takes an `account` alias. With one account authorized it may be omitted; with
several it is **required**, so mail can never go out from the wrong inbox by default.

## Dependencies

- Node 20+ (built and run on Node 22)
- A Google Cloud project with the Gmail API enabled and a Desktop-app OAuth client

## Install on a Mac

This runs **from this checkout**, not from a copy. MCP servers can live anywhere, unlike
skills which must be copied to `~/.claude/skills`. One copy per machine, `git pull` updates
it, no drift.

### 1. Build

```bash
cd ~/Developer/tony-skills/tools/gmail-mcp
npm install
npm run build
```

### 2. Google Cloud OAuth client

**Do this once, in one project, and reuse it on every machine.** The client is per-project,
not per-machine.

1. Create a project at <https://console.cloud.google.com/projectcreate>. Use a **dedicated**
   project — the OAuth consent screen is per project, so reusing an existing app's project
   changes that app's configuration too.
2. Enable the Gmail API:
   <https://console.cloud.google.com/apis/library/gmail.googleapis.com>
3. Google Auth Platform → fill in app name, support email, **User type: External**.
4. **Audience → Publish app, so publishing status reads "In production".**
5. Data access → add scope `https://www.googleapis.com/auth/gmail.modify`.
6. Clients → Create client → **Desktop app** → Download JSON.

```bash
mkdir -p ~/.gmail-mcp && chmod 700 ~/.gmail-mcp
mv ~/Downloads/client_secret_*.json ~/.gmail-mcp/credentials.json
chmod 600 ~/.gmail-mcp/credentials.json
```

> **Leave publishing status on "Testing" and Google revokes every refresh token after 7
> days**, forever. "In production" makes them long-lived. Because the app is unverified you
> get an "unverified app" interstitial when authorizing — **Advanced → Go to gmail-mcp
> (unsafe)**. That warning means Google has not reviewed the app; the app is yours and runs
> only on your machine. Do not submit for verification, it is not needed under 100 users.
>
> If you ever see a "Back to testing" button on the Audience page, leave it alone. Flipping
> back kills every token on every machine after 7 days.

### 3. Authorize each inbox

```bash
npm run auth -- personal
npm run auth -- pour-main
```

Browser opens, pick the matching Google account, click through the unverified-app screen.
Tokens land in `~/.gmail-mcp/accounts/<alias>.json` at mode 600.

```bash
npm run auth -- --list                    # show authorized accounts
npm run auth -- --rename old new          # rename an alias, token kept
npm run auth -- --remove alias            # forget one locally
```

Aliases are one word. `npm run auth -- pour guys old` is rejected rather than silently
truncated; use `pour-guys-old`.

### 4. Register with Claude Code

```bash
claude mcp add --scope user gmail -- node ~/Developer/tony-skills/tools/gmail-mcp/dist/server.js
```

Restart Claude Code. `/mcp` should list `gmail` as connected.

## Second machine

The code comes from `git pull`. The secrets do not, by design.

**Copy `~/.gmail-mcp/credentials.json` across** (the OAuth client is shared), then **re-run
`npm run auth` per inbox on the new machine**. Do not copy `~/.gmail-mcp/accounts/`.

Re-authorizing is safer than copying refresh tokens and costs nothing: Google issues
independent tokens per authorization, both machines stay valid simultaneously, and the
100-user cap counts distinct Google accounts, not devices. If tokens on one machine are ever
compromised you can revoke without touching the other.

Never move either file through iCloud, Drive, or chat. Use a direct transfer.

## Sending

`send_message` requires `confirm: true`, and its description instructs the assistant to show
the sending account, recipients, subject and body and get an explicit go-ahead first. That
is a convention, not a hard lock — an assistant could pass `confirm: true` on its own. For a
real gate, add a Claude Code permission rule:

```json
{ "permissions": { "ask": ["mcp__gmail__send_message"] } }
```

## Caveats

- **Tools load at Claude Code startup.** Registering or re-registering the server needs a
  restart before the `mcp__gmail__*` tools appear.
- **The claude.ai Gmail connector overlaps.** Once an inbox is authorized here, turn that
  connector off in `/mcp` or you have two Gmail toolsets and ambiguity about which was used.
- **`dist/` is gitignored.** `npm run build` must run on each machine; the registered
  command points at `dist/server.js`, which does not exist until you build.
- **`brace-expansion` is pinned** via `overrides` to clear a high-severity advisory reachable
  through the `googleapis` tree. Keep the override when bumping deps; re-check with
  `npm audit`.

## Backlog — agreed 2026-08-23, build later

Deferred until the Caelan pipeline (build step 5) is authorized; items 1–3 are the ones
that unblock her triage loop, 4–6 are conveniences. Decided with Tony on 2026-08-23.

1. **`send_draft` + `list_drafts`** — drafts are currently a dead end: the server can
   create one but not see or send it. Needed for the approval loop (she drafts, Tony
   says send, it goes out by draft id).
2. **`check_new` via the History API** — "what changed since historyId X" in one cheap
   call, the right primitive for the heartbeat cron instead of re-searching the inbox.
3. **`untrash_message`** — the undo verb for `trash_message`.
4. **Label management** — create/rename/delete labels, so she can make her own triage
   labels (e.g. `caelan/studying`, `caelan/killed`) without manual setup.
5. **`forward_message`** — forward carrying the original MIME parts, so attachments
   don't need a download-and-rebuild round trip.
6. **`get_profile`** — message counts and current historyId; pairs with item 2.

Considered and rejected: Gmail filters/vacation settings (extra OAuth scope; triage
logic belongs in her code, not Gmail settings), Pub/Sub push notifications (real
infrastructure to replace a polling design deliberately chosen), permanent delete
(needs full-access scope; violates the nothing-is-truly-gone posture).

## Troubleshooting

| Symptom | Cause |
|---|---|
| `No accounts authorized yet` | Run `npm run auth -- <alias>` |
| HTTP 401/403 on every call | Token revoked or expired; re-run auth. Weekly recurrence means publishing status is back on "Testing" |
| `Google did not return a refresh token` | Stale grant; revoke at <https://myaccount.google.com/permissions> and retry |
| Server missing from `/mcp` | `npm run build` not run, or Claude Code not restarted |

## Layout

```
src/store.ts    credentials and per-account token storage
src/auth.ts     OAuth CLI, loopback redirect on 127.0.0.1
src/gmail.ts    authorized client cache, MIME parsing and building
src/server.ts   MCP server and tool definitions
```

Secrets live in `~/.gmail-mcp/`, never in this repo. The nested `.gitignore` blocks
credential filenames as a second line of defence.
