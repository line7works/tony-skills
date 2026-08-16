---
name: arcade
description: >-
  Manage the Line 7 Arcade (arcade.line7.works) from any repo by driving the
  bundled arcade-publish CLI. Use when Tony wants to publish, put, or post a
  page "on the arcade" ("put that on the arcade", "post this to the arcade",
  "arcade this"), update or replace an arcade page, take down / remove / delete
  a page from the arcade, reorder the arcade wall ("move X to the top"),
  feature or unfeature a page, or asks "what's on the arcade" / to list the
  gallery. Writes to LIVE production — there is no staging arcade — so delete
  always gets an explicit conversational yes before anything runs.
---

# Arcade: publish and manage pages on the Line 7 Arcade

You drive the bundled `arcade-publish` CLI. You never call the site's API
directly, and you never invoke `arcade-publish` by bare command name — the
PATH-installed command can point at a different checkout or dangle entirely,
which is the exact bug this skill exists to bury. Always resolve the bundled
copy:

```bash
ARCADE="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/arcade}/assets/arcade-publish"
node "$ARCADE" <command> [args]
```

**The installed copy goes stale.** Installing this skill — through the plugin
marketplace or as a user-level copy — produces a real copy of the CLI, not a
link to the repo. Editing `~/Developer/tony-skills` updates the terminal
command immediately (its launcher resolves the repo at run time) but not this
skill's copy: reinstall (`/plugin update arcade@tony-skills`, or re-copy for a
user-level install) or the skill and the terminal run different versions
against live production.

## Before anything else

**Every write hits live production.** Pages go up at
`https://arcade.line7.works/arcade/<slug>`, visible immediately. There is no
staging arcade. `publish` and `update` are slug-idempotent — re-running against
the same slug lands in the same place, and `update` keeps the URL stable — but
**delete is not undoable**: it removes the live page and its uploaded file, and
nothing brings them back.

Requires Node 18+ and the config at `~/.config/line7/arcade.json` (see
Troubleshooting).

## The five jobs

### 1. Publish a page

```bash
node "$ARCADE" publish <file.html> --name "Display Name" [--slug my-page] [--featured]
```

- The file is a local HTML file. If the conversation doesn't make the file
  obvious, ask which one.
- If no display name is obvious from the page or the request, **ask Tony for
  one** — don't invent a label that will sit on the public wall. Offer
  `--featured` when it might belong pinned at the top.
- `publish` refuses a slug that already exists. If Tony means to replace an
  existing page, that's `update`, not a delete-then-publish.
- On success, report the live page URL the CLI prints.

### 2. Update an existing page

```bash
node "$ARCADE" update <slug> <file.html> [--name "New Name"] [--featured|--no-featured]
```

- Keeps the slug and public URL stable — that's the point. It can rename or
  toggle featured in the same call.
- Caveats worth relaying when relevant: toggling `--featured` on restamps the
  seed's `order` to top-of-featured (server behavior, no opt-out), and
  replacing the file on a legacy seed (no `order` value) moves it to the end
  of its block.

### 3. List the gallery

```bash
node "$ARCADE" list
```

Prints the gallery in the site's real menu order — featured first, then by
`order` — with slugs visible. Use it to answer "what's on the arcade" and as
the input for reorder.

### 4. Reorder the wall

Tony states intent ("move X to the top", "put Y after Z"); the CLI takes the
**complete** gallery as slugs in the desired order. So:

1. Run `list` to get the current order.
2. Translate the intent into a full slug list.
3. **Show the before and after order and get Tony's confirmation before
   calling.** Note in the preview that featured pages sort to the top
   regardless of the requested order (server rule) — if the requested list
   doesn't put featured seeds first, the resulting order will differ from the
   raw list shown.
4. Then: `node "$ARCADE" reorder <slug> <slug> ...`

The CLI refuses an incomplete, duplicated, or unknown slug list before sending
anything, and prints the resulting menu order as the server answers it.

### 5. Feature / unfeature

```bash
node "$ARCADE" feature <slug>
node "$ARCADE" unfeature <slug>
```

Flips the featured pin without re-uploading anything. Featuring stamps a
top-of-featured `order`; a seed already in the requested state is skipped with
no request sent.

## Delete — always two-step, no exceptions

Deleting is the one irreversible action here, so the gate lives in the
conversation, not just the CLI:

1. Run `list` (or otherwise resolve the slug) and show Tony the target's
   **slug, name, and live URL**.
2. Ask for an explicit yes. Wait for it. Silence, "probably", or a general
   "clean it up" is not a yes for a specific page.
3. Only after Tony's yes in this conversation, run:
   `node "$ARCADE" delete <slug> --yes`
   (`--yes` is fine here because the human confirmation already happened; the
   CLI's own prompt exists for terminal use, not to replace yours.)

Never chain a delete with any other destructive action under one confirmation.
One yes covers one delete of one named page.

## Troubleshooting

**No config** — the CLI fails saying it can't read
`~/.config/line7/arcade.json`. Show Tony this setup snippet (from the CLI's
README):

```sh
mkdir -p ~/.config/line7
cat > ~/.config/line7/arcade.json <<'JSON'
{ "password": "<the live /admin password>", "base": "https://www.line7.works" }
JSON
chmod 600 ~/.config/line7/arcade.json
```

`base` must be the canonical `www` host over `https` — the apex
`line7.works` 307-redirects and the CLI refuses redirects on purpose. The only
non-https exception is `http://localhost[:port]` / `http://127.0.0.1[:port]`
for a local dev server.

**Auth failure (401 / login rejected)** — the stored password is stale. The
admin password rotates; ask Tony for the current `/admin` password and update
the `password` field in `~/.config/line7/arcade.json`. Don't guess or retry
with variations.
