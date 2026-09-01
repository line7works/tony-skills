# arcade-publish

Publish HTML pages to the **Line 7 Arcade** from the terminal, without opening
the admin UI or a browser. One Node script, no dependencies.

The arcade itself is the public HTML host at `arcade.line7.works`, served by the
`line7-site` repo. This tool drives the same `/api/admin` endpoints the Arcade
tab in `/admin` uses: session login → multipart upload → a per-seed write on
`/api/admin/seeds`.

**This writes to live production.** There is no staging arcade and no undo.
`delete` removes a live page and its uploaded file — but never without printing
what it is about to remove and getting a yes first.

## Commands

```
arcade-publish list
arcade-publish publish <file.html> --name "Name" [--slug my-page] [--featured]
arcade-publish update <slug> <file.html> [--name "New Name"] [--featured|--no-featured]
arcade-publish delete <slug> [--yes]
arcade-publish reorder <slug> <slug> ...
arcade-publish feature <slug>
arcade-publish unfeature <slug>
```

- `list` prints the gallery in the site's own menu order — featured pages first,
  then each block by its `order` value, both of which are shown.
- `publish` refuses a slug that already exists — it never silently overwrites.
  Use `update` to replace a page's contents. The server is the judge: a slug
  that gets taken mid-upload comes back as a clean error, and the orphaned
  upload is cleaned up rather than left behind.
- `delete` shows the target's slug, name, and URL, then asks. On a terminal it
  waits for `y`; with no terminal it refuses outright unless `--yes` is passed.
  It never proceeds on silence.
- `update` keeps the slug and public URL stable, which is the point: a page can
  be revised in place and anyone holding the link still lands on it. It can also
  rename the page or toggle its featured flag in the same call.
- `reorder` takes the **complete** gallery as slugs in the desired order — the
  slugs `list` prints, rearranged. If the arguments miss a seed, name an
  unknown one, or repeat one, it refuses before sending anything and says which
  slugs are wrong. On success it prints the new menu order as the server
  answers it — featured pages still sort to the top regardless of the
  requested order (server rule).
- `feature` / `unfeature` flip a page's featured pin without re-uploading its
  file. Featuring stamps a top-of-featured `order` (server behavior, same as
  the admin UI's toggle). Flipping a seed that is already in the requested
  state sends nothing and says so.
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
  via `${CLAUDE_PLUGIN_ROOT}/assets/arcade-publish`.
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
- It must be `https://`. The admin password rides on every request. The one
  exception is a dev server on this machine — `http://localhost[:port]` or
  `http://127.0.0.1[:port]` — where the password never leaves the loopback
  interface. Nothing else in `http://` is accepted, and the check runs before
  any network call.

Note that the session cookie effectively *is* the admin password (server design,
predates this tool). Rotating the password is the only way to revoke it.

## How it behaves when things go wrong

Worth knowing before trusting it in a script:

- Every command runs on the per-resource `/api/admin/seeds` endpoints — the
  whole-document write this tool used to do is gone entirely. All of them
  touch a single seed except `reorder`, which uses the server's dedicated
  reorder endpoint (it rejects any id list that does not cover every seed
  exactly once, so a stale gallery view cannot silently drop a page).
- `update` uploads the new file, then `PATCH`es the existing seed's `url`. The
  seed's id and slug always survive, and its `order` does too — **unless** the
  same call toggles `--featured` on, which stamps the top-of-featured order,
  same as any featured toggle (server behavior, no opt-out). The server stamps
  `uploadedAt` itself (only when the url actually changes). If the PATCH
  fails — seed deleted mid-upload, url owned by another seed, anything — the
  new upload is rolled back and the existing page is untouched. On success the
  server names the old file (`previousUrl`) and the CLI deletes it.
- `publish` cleans up after itself: if the seed cannot be registered — slug
  taken, bad name, anything — the upload it just made is deleted. If that
  cleanup also fails, the error says so and names the orphaned file.
- `delete` unregisters the seed first and removes the file second, so a failure
  between the two leaves an orphaned file (harmless) rather than a live page
  pointing at nothing.
- Cleanup failures never mask the outcome. If the page was updated or deleted
  successfully but removing the old file failed, the command still reports
  success and prints a note about the orphan on stderr.

## Caveats

- Replacing the file on a *legacy* seed — one stored before the `order` field
  existed — moves it to the end of its block, because the server restamps
  `uploadedAt` and that is the legacy block's tiebreak. Deliberate server
  behavior, and the caller cannot opt out; don't compensate by sending `order`.
- Page URLs follow `base`, so a run against a local dev server prints local
  links rather than production ones — which is what makes the `delete` preview
  trustworthy. The `Gallery:` line printed by `publish` is still hardcoded to
  `line7.works`, as is the fallback arcade host, while the canonical host is
  env-derived server-side (`lib/arcadeHost.ts`). If that host ever changes,
  those printed links go stale before the tool does.

## History

Built 2026-08-09 (`list`, `publish`). `update` and `delete` added 2026-08-10 at
the request of the JPB skill, which re-posts a resolved run doc to the same slug.
That addition was reviewed, hardened, and re-verified. The findings ledger is
`tools/arcade-publish/punch-list.md` in this repo — deliberately one consolidated
list, and it deliberately stays under `tools/` even though the code now lives
here.

Moved from `tools/arcade-publish/` into this plugin on 2026-08-12, so the skill
and the terminal command share one copy instead of drifting apart.
