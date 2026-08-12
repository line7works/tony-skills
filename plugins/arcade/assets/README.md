# arcade-publish

Publish HTML pages to the **Line 7 Arcade** from the terminal, without opening
the admin UI or a browser. One Node script, no dependencies.

The arcade itself is the public HTML host at `arcade.line7.works`, served by the
`line7-site` repo. This tool drives the same `/api/admin` endpoints the Arcade
tab in `/admin` uses: session login → multipart upload → rewrite the `seeds`
array.

**This writes to live production.** There is no staging arcade and no undo.
`delete` removes a live page and its uploaded file immediately.

## Commands

```
arcade-publish list
arcade-publish publish <file.html> --name "Name" [--slug my-page] [--featured]
arcade-publish update <slug> <file.html> [--name "New Name"] [--featured|--no-featured]
arcade-publish delete <slug>
```

- `publish` refuses a slug that already exists — it never silently overwrites.
  Use `update` to replace a page's contents.
- `update` keeps the slug and public URL stable, which is the point: a page can
  be revised in place and anyone holding the link still lands on it. It can also
  rename the page or toggle its featured flag in the same call.
- Slug rules mirror the admin UI's `slugify` byte for byte: lowercased,
  non-alphanumerics collapsed to `-`, trimmed to 60 chars. `admin`, `api`,
  `new`, `edit`, and `index` are reserved.
- Pages land at `https://arcade.line7.works/arcade/<slug>`; the gallery is
  `https://line7.works/arcade`.

Argument parsing is strict on purpose — one of these commands is destructive.
Unknown flags, flags missing their value, and extra positional arguments are all
hard errors rather than silent no-ops. Notably `--slug` is rejected on `update`:
slugs cannot be renamed, because the stable URL is the feature.

## Dependencies

- Node 18 or newer (uses the built-in `fetch`, `FormData`, and `Blob` — no npm
  install, no `node_modules`).

## Install

This file is the source of truth. There are two front doors to it, and they do
**not** stay in sync automatically:

- **The terminal command.** `~/.local/bin/arcade-publish` is a small launcher
  that resolves this file in the checkout at run time, so editing the repo copy
  changes the command immediately. It probes the plugin path first and the old
  `tools/arcade-publish/` path second, so it keeps working on branches cut
  before the 2026-08-12 move instead of dangling.
- **The `/arcade` skill** (from Slice D onward) reaches its own installed copy
  via `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/arcade}/assets/arcade-publish`.
  Installing a skill — user-level by copying, or through the plugin
  marketplace — **produces a real copy**, not a link. That copy goes stale the
  moment this file changes.

So after editing this file, reinstall the skill (`/plugin update arcade@tony-skills`,
or re-copy for a user-level install) or the skill and the terminal will run
different versions against live production. This is the same reinstall rule
CLAUDE.md states for every skill in this repo; bundling the CLI does not exempt
it.

```sh
install -m 0755 /dev/stdin ~/.local/bin/arcade-publish <<'SH'
#!/bin/sh
REPO="$HOME/Developer/tony-skills"
for c in "$REPO/plugins/arcade/assets/arcade-publish" \
         "$REPO/tools/arcade-publish/arcade-publish"; do
  [ -f "$c" ] && exec node "$c" "$@"
done
echo "arcade-publish: cannot find the CLI in $REPO" >&2; exit 127
SH
```

Then create the config, which is **not** in this repo and never should be:

```sh
mkdir -p ~/.config/line7
cat > ~/.config/line7/arcade.json <<'JSON'
{ "password": "<the live /admin password>", "base": "https://www.line7.works" }
JSON
chmod 600 ~/.config/line7/arcade.json
```

Two things about `base`, both of which bit us on day one:

- It must be the canonical **`www`** host. The apex `line7.works` 307-redirects
  to `www`, and this script refuses redirects on purpose — a cross-origin hop
  would silently drop the session cookie, and a redirected login would re-send
  the password body to wherever it pointed.
- It must be `https://`. The admin password rides on every request.

Note that the session cookie effectively *is* the admin password (server design,
predates this tool). Rotating the password is the only way to revoke it.

## How it behaves when things go wrong

Worth knowing before trusting it in a script:

- The seed list is one array replaced wholesale by `PUT /api/admin`, so it is
  last-write-wins. Every destructive command re-reads the list immediately
  before writing to keep that window as small as one round trip. It is narrowed,
  not closed — don't drive this while editing the same page in the admin UI.
- `update` uploads the new file *before* touching the registry. If registration
  fails, the new upload is rolled back and the existing page is untouched.
- `delete` unregisters the seed first and removes the file second, so a failure
  between the two leaves an orphaned file (harmless) rather than a live page
  pointing at nothing.
- Cleanup failures never mask the outcome. If the page was updated or deleted
  successfully but removing the old file failed, the command still reports
  success and prints a note about the orphan on stderr.

## Caveats

- Deleting a page while the admin UI is open in a browser can resurrect it: that
  tab holds a stale copy of the seed list in memory and any save there re-sends
  it. The page comes back in the gallery pointing at a file that no longer
  exists. Reload the admin tab after using this tool.
- The success URLs print `arcade.line7.works` hardcoded, while the canonical
  host is env-derived server-side (`lib/arcadeHost.ts`). If that host ever
  changes, the printed link goes stale before the tool does.

## History

Built 2026-08-09 (`list`, `publish`). `update` and `delete` added 2026-08-10 at
the request of the JPB skill, which re-posts a resolved run doc to the same slug.
That addition was reviewed, hardened, and re-verified. The findings ledger is
`tools/arcade-publish/punch-list.md` in this repo — deliberately one consolidated
list, and it deliberately stays under `tools/` even though the code now lives
here.

Moved from `tools/arcade-publish/` into this plugin on 2026-08-12, so the skill
and the terminal command share one copy instead of drifting apart.
