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

The canonical copy is this file. `~/.local/bin/arcade-publish` is a **symlink**
to it, so editing the repo copy changes the installed command immediately.

```sh
ln -s ~/Developer/tony-skills/tools/arcade-publish/arcade-publish ~/.local/bin/arcade-publish
chmod +x ~/Developer/tony-skills/tools/arcade-publish/arcade-publish
```

Then create the config, which is **not** in this repo and never should be:

```sh
mkdir -p ~/.config/line7
cat > ~/.config/line7/arcade.json <<'JSON'
{ "password": "<the live /admin password>", "base": "https://line7.works" }
JSON
chmod 600 ~/.config/line7/arcade.json
```

`base` must be `https://` — the admin password is sent on every request. The
script refuses redirects for the same reason: a cross-origin hop would drop the
session cookie, and a redirected login would re-send the password body to
wherever it pointed.

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
That addition was reviewed, hardened, and re-verified; the findings ledger lives
at `~/Developer/line7-site/docs/punch-list.md`.
