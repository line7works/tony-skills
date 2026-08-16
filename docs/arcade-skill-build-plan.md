# /arcade skill — build plan (2026-08-12)

Intent: Wrap the arcade-publish CLI in an `/arcade` plugin skill so Tony can say
"put that on the arcade" from any repo — hauler, PGL, quarters, anywhere — and
get full gallery management: publish, update, delete (with a confirmation gate),
feature, and reorder pages on the Line 7 Arcade (arcade.line7.works). The CLI is
rewired onto line7-site's new per-resource `/api/admin/seeds` endpoints, which
eliminates the whole-document read-modify-write that could clobber concurrent
admin edits, and gives CLI-published pages a real `order` value so they stop
sinking to the bottom after any admin reorder.

Constraints:
- Repo: `~/Developer/tony-skills`. Its CLAUDE.md forbids pushing to `main`;
  feature branch + PR is the only route. Nothing is pushed, PR'd, or merged
  until Tony says the word.
- Plugin pattern: copy `plugins/forge/` — `.claude-plugin/plugin.json`,
  `skills/<name>/SKILL.md`, bundled executable under `assets/`, invoked via
  `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/arcade}/assets/...` so it
  resolves both as an installed plugin and as a user-level skill.
- Marketplace: new plugins register in `.claude-plugin/marketplace.json`.
- The CLI is plain Node (single file, no dependencies). Keep it that way.
- One source of truth for the CLI. Tony chose: the real copy moves into the
  plugin at `plugins/arcade/assets/arcade-publish`; the terminal command
  resolves that path at run time; `tools/arcade-publish/` keeps only
  `punch-list.md` and a pointer README. No second copy **in the repo**.
  (Corrected 2026-08-12 after Slice A review: the original wording promised no
  second copy anywhere, which is unachievable — installing a skill user-level
  or through the marketplace produces a real copy by design, so an installed
  `/arcade` necessarily has its own. The repo holds one canonical file; the
  installed copy is derived and refreshed by reinstalling. Slice D must
  document that reinstall step rather than claim parity.)
- The punch list stays the single consolidated ledger at
  `tools/arcade-publish/punch-list.md` (deliberate; it was split once and the
  same bug got re-reported as new). It does not move with the code.
- Server API contract (shipped on line7-site `Main`, PR #23, 2026-08-12; shape
  is final — build against it, do not redesign it):
  - All endpoints sit behind the admin session cookie from
    `POST /api/admin/session` (unchanged login flow).
  - `GET /api/admin/seeds` → `{ seeds: [...] }` in menu order.
  - `POST /api/admin/seeds` `{ name, url, slug?, featured? }` → 201 `{ seed }`;
    400 missing name/url or unusable slug; 409 slug taken. Server assigns
    `order` = max existing + 1.
  - `PATCH /api/admin/seeds/<id>` `{ name? | slug? | featured? | order? | url? }`
    → `{ seed }`; 404 unknown id; 409 slug taken; 400 unusable url.
    (Amended 2026-08-14 — `url` was added to the server's PATCH allow-list to
    unblock Slice B R3; see the Slice B entry under `## Discovered`. The server
    restamps `uploadedAt` whenever `url` changes, so the CLI must not send one.)
  - `DELETE /api/admin/seeds/<id>` → `{ ok: true }`; 404.
  - `PATCH /api/admin/seeds/reorder` `{ ids: [every seed id, in order] }` →
    `{ seeds }`; 400 unless the list covers every seed exactly once.
  - Seed shape: `{ id, slug, name, featured, uploadedAt, url, order? }`.
    `order` is optional (legacy seeds lack it).
  - Sort rule (server-applied on every read): featured first, then `order`
    ascending within each block, then order-less seeds oldest-first.
  - File upload is unchanged: `POST /api/admin/upload` (multipart) returns the
    blob `url` the seed points at; `DELETE /api/admin/upload` removes a blob.
  - Endpoints are documented in line7-site `docs/arcade/README.md`.
- Config: `~/.config/line7/arcade.json` → `{ "password", "base" }`, unchanged.
- Test command: the repo has no test suite. Verification is by running the CLI
  against a local line7-site dev server (`npm run dev` in
  `~/Developer/line7-site`; with no `DATABASE_URL` it falls back to a local
  `data/site.json`, so nothing touches production). The CLI currently rejects
  non-https `base` values — see Slice B requirement R6.

Out of scope:
- Any change to line7-site — its work shipped in PR #23 and is done.
  (Amended 2026-08-14, Tony's call: ONE exception, the `url` addition to the
  seeds PATCH allow-list described above. It is the option-B resolution of the
  Slice B R3 stop and it is the whole exception — no other line7-site change
  rides along under this plan.)
- Migrating the CLI's legacy whole-blob PUT path for *other* site sections; the
  CLI only ever touched `seeds`, and after the rewire it uses no whole-blob
  writes at all.
- Open MINOR punch-list findings in code paths this plan does not touch (e.g.
  slugify trailing-hyphen at :26, config-error message at :45) — they stay on
  the ledger; fixing them here would put unreviewed drive-by changes under this
  plan's review. Findings *in* touched paths are in scope where a requirement
  names them.
- A "featured pages bump to top" change — that is server sort behavior and
  already shipped in line7-site PR #23.
- An MCP server for the arcade — Tony wants a proper API/MCP surface for Line 7
  eventually; that is its own future project, not this plan.
- Screenshot/thumbnail support, analytics, or any admin-UI change.

## Slice A — plugin scaffold and the move

Goal: The plugin skeleton exists, the CLI's single copy lives inside it, the
terminal command still works, and the approved `.gitignore` edit is committed.

Requirements:
- R1: Create `plugins/arcade/` with `.claude-plugin/plugin.json` (forge's as
  the model: name `arcade`, author Tony Coon, repo homepage) and
  `plugins/arcade/assets/`.
- R2: `git mv tools/arcade-publish/arcade-publish plugins/arcade/assets/arcade-publish`
  and `git mv tools/arcade-publish/README.md plugins/arcade/assets/README.md`
  (updating the README's stated location and install steps). History is
  preserved via `git mv`.
- R3: `tools/arcade-publish/` retains `punch-list.md` unchanged plus a new
  short README stating the code moved to `plugins/arcade/assets/` and that the
  punch list deliberately stays here as the single ledger.
- R4: Repoint `~/.local/bin/arcade-publish` to
  `~/Developer/tony-skills/plugins/arcade/assets/arcade-publish`.
- R5: Update the `tools/README.md` bullet for `arcade-publish/` to say the
  folder now holds the ledger and pointer, code lives in the plugin.
- R6: Commit the already-approved `.gitignore` edit (ignore
  `generated-assets/`) as its own commit on this slice's branch (approved by
  Tony 2026-08-11; folded into this PR by Tony 2026-08-12).
Acceptance criteria:
- AC1: `arcade-publish list` run from a random directory prints the current
  gallery, and the installed command resolves the CLI in the repo — verify:
  manual: run it, confirm seeds print, and confirm the command reaches
  `plugins/arcade/assets/arcade-publish`. (Amended 2026-08-12 after the Slice A
  recheck: this criterion originally required `readlink ~/.local/bin/arcade-publish`
  to print the plugin path. The fix for the branch-dependent-symlink finding
  replaced that symlink with a launcher script, so `readlink` now correctly
  returns nothing and the original wording would grade the fix as a regression.)
- AC2: Exactly one copy of the executable exists in the repo — verify: manual:
  `git ls-files | grep arcade-publish` shows the executable only under
  `plugins/arcade/assets/`.
- AC3: `git log --follow plugins/arcade/assets/arcade-publish` shows the
  pre-move history — verify: manual: run it, confirm the three PR #17 commits
  appear.
- AC4: `git status` no longer lists `.gitignore` as modified, and
  `generated-assets/` stays untracked — verify: manual: `git status --short`.
Footprint: `plugins/arcade/.claude-plugin/plugin.json`,
`plugins/arcade/assets/arcade-publish`, `plugins/arcade/assets/README.md`,
`tools/arcade-publish/README.md` (new pointer), `tools/README.md`,
`.gitignore`, `~/.local/bin/arcade-publish` (launcher script, outside the repo).
Not in this slice: any change to the CLI's code; SKILL.md; marketplace entry.
Depends on: nothing
Status: signed off

## Slice B — rewire onto per-resource endpoints, gate the delete

Goal: The CLI's four commands run entirely on `/api/admin/seeds`, the
whole-blob PUT is gone from the CLI, and delete cannot fire without showing its
target first.

Requirements:
- R1: `list` uses `GET /api/admin/seeds` and prints seeds in the returned
  (menu) order, including each seed's `order` value and featured mark.
- R2: `publish` uploads via `POST /api/admin/upload` (unchanged), then creates
  the seed via `POST /api/admin/seeds`. Map 409 to the existing "slug taken"
  message (including the orphan-cleanup attempt the CLI already does); map 400
  to a clear error. The client-side pre-check against a stale list may go —
  the server's 409 is now authoritative.
- R3: `update` resolves slug → id via `GET /api/admin/seeds`, uploads the new
  file, then `PATCH /api/admin/seeds/<id>` with the new url/name/featured.
  Keep the existing rollback behavior on failure after upload.
- R4: `delete` resolves slug → id, then `DELETE /api/admin/seeds/<id>`, then
  deletes the blob (existing unregister-first ordering stands). Before any
  destructive call it prints the target — slug, name, live URL — and requires
  confirmation: interactive y/N prompt on a TTY, or an explicit `--yes` flag
  for non-interactive use. No confirmation, no delete. (Closes the open
  punch-list finding "delete is one-shot destructive with no confirmation".)
- R5: No code path in the CLI issues `PUT /api/admin` any longer; the
  read-modify-write defenses that existed only to protect that pattern
  (post-upload re-read before PUT, empty-seeds-shape guard on the whole
  document) are removed with it. Guards that validate per-endpoint responses
  stay.
- R6: `base` values of exactly `http://localhost[:port]` or
  `http://127.0.0.1[:port]` are accepted; every other `base` must still be
  https (the existing check and redirect guard stand). This exists so the CLI
  can be verified against a local dev server.
- R7: Version-bump the usage header comment to describe the new behavior.
Acceptance criteria:
- AC1: Against a local line7-site dev server (fresh `data/site.json`), the
  cycle publish → list → update → delete works end to end and leaves the local
  gallery as it started — verify: manual: run the four commands with `base`
  pointed at localhost; confirm list output after each step.
- AC2: `delete` with no `--yes` on a non-TTY stdin exits non-zero without
  deleting; with `--yes` it deletes; interactively, answering `n` aborts with
  the seed still present — verify: manual: `echo | arcade-publish delete
  <slug>` (non-TTY, must refuse), then interactive run answering n, then
  `--yes`.
- AC3: `grep -n '"/api/admin"' arcade-publish` finds no whole-blob PUT call
  site — verify: manual: run the grep; only `/api/admin/seeds*`,
  `/api/admin/session`, `/api/admin/upload` remain.
- AC4: A publish while the local server has other seeds present does not
  disturb them — verify: manual: seed two entries via a second publish, delete
  one, confirm the other and all non-seed site data in `data/site.json` are
  unchanged.
- AC5: `http://line7.works` as base is still rejected before any network call
  — verify: manual: set it in a scratch config, run `list`, confirm the
  pre-network failure message.
Footprint: `plugins/arcade/assets/arcade-publish`,
`plugins/arcade/assets/README.md` (usage updates).
Not in this slice: reorder/feature commands; SKILL.md.
Depends on: Slice A
Status: signed off

## Slice C — reorder and feature commands

Goal: The CLI can rearrange the wall and flip the featured pin without a file
upload.

Requirements:
- R1: New command `reorder <slug> <slug> ...` taking the complete gallery in
  the desired order. It resolves slugs → ids, calls
  `PATCH /api/admin/seeds/reorder`, and prints the resulting menu order. If
  the argument list does not cover every existing seed exactly once, fail
  before calling the server and print which slugs are missing or unknown
  (mirror of the server's own 400 rule, but with actionable output).
- R2: New command `feature <slug>` / `unfeature <slug>` using
  `PATCH /api/admin/seeds/<id>` with `{ featured }`. (Today featuring requires
  re-uploading a file through `update`; these make it a metadata flip.)
- R3: Both commands register in the CLI's per-command grammar table (`COMMANDS`)
  so stray flags and positionals stay hard errors, matching the existing
  parser's design intent.
- R4: `list` output orders and labels such that its printed order is directly
  usable as the argument list for `reorder` (slugs visible, menu order).
Acceptance criteria:
- AC1: Against the local dev server with three seeds, `reorder c a b` changes
  the gallery to c, a, b and `list` reflects it — verify: manual: run it.
- AC2: `reorder` with a missing or unknown slug exits non-zero naming the
  offending slugs and the server receives no call — verify: manual: run with
  an incomplete list while watching the dev server log.
- AC3: `feature a` moves seed a into the featured block at the top of `list`
  (server sort); `unfeature a` returns it — verify: manual: run both.
Footprint: `plugins/arcade/assets/arcade-publish`,
`plugins/arcade/assets/README.md`.
Not in this slice: SKILL.md; any change to how featured sorts (server-owned).
Depends on: Slice B
Status: signed off

## Slice D — the /arcade skill and marketplace entry

Goal: Saying "put that on the arcade" in any repo invokes a skill that drives
the bundled CLI, with the delete gate held at the conversation level too.

Requirements:
- R1: `plugins/arcade/skills/arcade/SKILL.md` in the forge mold: frontmatter
  `name: arcade` plus a trigger-rich description (publish/put/post "on the
  arcade", take down, reorder, feature, "what's on the arcade"), body that
  invokes the CLI only via
  `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/arcade}/assets/arcade-publish` —
  never a bare PATH lookup (PATH is the vanishing bug this plan exists to
  bury).
- R2: The skill covers the five jobs: publish a local HTML file (asking for a
  display name if none is obvious; offering `--featured`), update an existing
  page, list the gallery, reorder (taking Tony's intent like "move X to the
  top" and translating it into the full-order `reorder` call, showing the
  before/after order for confirmation before calling), and feature/unfeature.
- R3: Delete in the skill is always two-step regardless of the CLI's `--yes`:
  show slug, name, and live URL, get Tony's explicit yes in conversation, and
  only then run the CLI (which the skill may then drive with `--yes`, since
  the human confirmation already happened). The skill never chains delete with
  other destructive actions in one confirmation.
- R4: The skill states plainly that every write hits live production
  (arcade.line7.works), there is no staging, and publish/update are
  slug-idempotent but delete is not undoable.
- R5: Register the plugin in `.claude-plugin/marketplace.json` with a
  description and tags in the existing entries' style.
- R6: The skill's error guidance covers the two known operational faults: no
  config at `~/.config/line7/arcade.json` (show the setup snippet from the
  CLI's README) and auth failure (stale password).
Acceptance criteria:
- AC1: With the plugin installed, a session in an unrelated repo (e.g.
  `~/Developer/quarters`) asked to "put this page on the arcade" invokes the
  skill and reaches the CLI by the plugin-root path — verify: manual: live
  session test from another repo.
- AC2: In that session, asking to delete a page produces the preview and a
  question, and nothing is deleted before the yes — verify: manual: run the
  flow against the local dev server (temporarily set `base` to localhost),
  decline, confirm the seed survives.
- AC3: `claude plugin` tooling accepts the manifest: marketplace.json parses
  and the plugin lists — verify: manual: whatever listing command the
  installed Claude Code version provides; at minimum `python3 -m json.tool` on
  both JSON files.
- AC4: `grep -rn 'arcade-publish' plugins/arcade/skills/` shows only
  plugin-root-relative invocations, no bare command name — verify: manual: run
  the grep.
Footprint: `plugins/arcade/skills/arcade/SKILL.md`,
`.claude-plugin/marketplace.json`.
Not in this slice: CLI code changes.
Depends on: Slice C
Status: signed off with conditions

## Build assumptions

### Slice A · 2026-08-12
- AC1's verification ran `list` against live production `line7.works`; reading the
  gallery is non-destructive and the localhost exception does not exist until
  Slice B · builder call
- `plugins/arcade/assets/README.md`'s stale pointer to a findings ledger at
  `~/Developer/line7-site/docs/punch-list.md` was corrected to
  `tools/arcade-publish/punch-list.md` while rewriting that file's location
  sections; leaving a contradictory ledger pointer would have fought R3 · builder call

### Slice B · 2026-08-13
- Verification runs against a throwaway `git worktree` of line7-site at `main`
  (commit `ebceeaa`, the PR #23 merge) under the session scratchpad, not against
  `~/Developer/line7-site` itself: that checkout sits on `feat/arcade-drag-reorder`,
  8 commits ahead of `main` with unmerged changes to both seeds routes, and its
  `data/site.json` and `public/uploads/` are tracked files a fixture would dirty.
  The worktree tests the contract the plan pins (PR #23) and leaves that repo's
  working tree untouched · builder call
- The CLI reads its config from `~/.config/line7/arcade.json` with no override,
  so verification ran every command under a sandboxed `HOME` in the scratchpad
  holding a localhost-pointed config. Tony's real config was never read or
  written, and no run could have reached production even by mistake · builder call
- Declining the delete prompt exits 1, not 0. The spec fixes the exit code for
  the non-TTY refusal ("exits non-zero") but is silent on the interactive `n`.
  Both mean the same thing to a caller — the delete did not happen — so they
  report the same way · builder call
- `pageUrl()` derives printed page links from `base` instead of the hardcoded
  `arcade.line7.works`. Traceable to R4, which requires delete's preview to name
  the target's "live URL": against a dev server the hardcoded host names a
  different page, which would defeat the gate. Applied to `list` and `publish`
  output too, for one consistent answer to "which page is this". This overlaps
  an open ledger MINOR (`arcade-publish:83`, `:269`) the plan's Out of scope
  leaves on the ledger — flagged rather than claimed as a fix, and the
  `Gallery:` line is still hardcoded · builder call

### Slice B · 2026-08-14 (R3/R5 completion build)
- `update`'s success line prints via `pageUrl()` instead of the hardcoded
  `arcade.line7.works` host — extends the prior build's recorded `pageUrl()`
  decision to the last command output still hardcoding it (the `Gallery:` line
  stays hardcoded, unchanged) · builder call
- `update`'s upload-response guard now requires only `url`, no longer `id`: the
  upload's id never reaches the seed under PATCH, so demanding it would fail
  runs the server considers valid · builder call
- R3's rollback-on-failure-after-upload (deleteUpload then fail, on PATCH
  404/409/400/other) is implemented but was not live-exercised: no AC names it,
  and forcing a PATCH failure mid-run means racing the server. The path mirrors
  publish's rollback, which the prior build exercised live · builder call
- AC2's interactive-`n` leg ran under a pty from `script(1)`; the first attempt
  delivered EOF before the prompt attached and reported exit 0 with no delete —
  a harness artifact. With stdin held open the CLI printed Aborted and exited 1,
  seed present · builder call

### Slice C · 2026-08-15
- Verification ran against `~/Developer/line7-site` itself (per the invocation)
  on `Main` at `7e5d87a` — one merge (PR #26, mobile-polish) ahead of the
  `0659cb7` the invocation named; tree clean, seeds routes untouched by that
  merge, `data/site.json` backed up first and restored byte-identical (diff
  verified), `git status` clean after. `DATABASE_URL` never set; CLI ran under
  a sandboxed `HOME` with a localhost-pointed config, as in Slice B · builder call
- `reorder` and `feature`/`unfeature` slugify their slug arguments before
  lookup, matching `update`/`delete`; the known trailing-hyphen unaddressability
  MINOR therefore extends to them — consistency chosen over a one-command fix
  the plan's Out of scope defers · builder call
- R1's "missing or unknown" pre-check also rejects a slug listed twice: the
  server's rule is "every seed exactly once", and a duplicate both shadows a
  missing seed and would send a duplicate id. Reported as its own category in
  the error · builder call
- `feature`/`unfeature` on a seed already in the requested state prints
  "nothing to do" and sends no PATCH, exit 0: the featured transition is what
  stamps top-of-featured `order` server-side, so a redundant `featured: true`
  is not guaranteed a no-op; the safe skip is client-side · builder call
- Both new write paths carry the same response-shape guards as Slice B's
  (reorder demands `seeds` back; feature demands the flag actually flipped),
  mirroring the stale-200 guard the Slice B review mandated for `update` · builder call
- AC3's "unfeature a returns it": the seed returns to the non-featured block,
  but not to its exact prior list position — featuring restamps `order`
  (observed live: `c a b` → feature a → `a★ c b` → unfeature a → `a c b`).
  Server-owned behavior this slice's Not-in-this-slice line excludes; the
  criterion's block-membership intent is met · builder call
- R3 and R4 have no acceptance criterion of their own. R3 was verified by four
  manual grammar probes (stray flag, extra positional, misapplied `--yes`,
  missing positional — all hard errors); R4 by feeding `list`'s printed slugs
  back into `reorder` inside AC1 · builder call

### Slice D · 2026-08-15
- AC1 and AC2's live-session legs were NOT exercised: both require the skill
  installed and an interactive session in another repo, and AC1's publish leg
  writes to live production. Left for Tony as the plan's own verify lines
  state ("manual: live session test"). The mechanical halves ran: the
  plugin-root invocation was executed with `CLAUDE_PLUGIN_ROOT` set and the
  CLI ran from the plugin copy (usage printed, exit 1 on a bogus command);
  AC3 via `python3 -m json.tool` on both JSONs plus `claude plugin validate`
  (passed; no-version warnings are pre-existing across all plugins); AC4 grep
  shows only the plugin-root invocation and prose mentions, no bare command · builder call
- The skill's reorder preview step states the featured-first server-sort
  caveat, closing the Slice C review MINOR aimed at Slice D's surface
  (plan:581): the raw requested list is flagged as differing from the
  resulting order when featured seeds are not listed first · builder call
- The skill invokes the CLI as `node "$ARCADE"` rather than executing the
  file, matching the launcher script and forge's interpreter-explicit
  pattern; R1's path requirement is about resolution, not exec style · builder call
- R2's update coverage carries the two caveats prior reviews forced into the
  CLI README (featured toggle restamps `order`; legacy-seed file replace
  moves it to the end of its block) so Slice D's skill copy does not
  reintroduce the uncaveated survival claim graded MAJOR twice · builder call

## Deviations

### Slice B · 2026-08-13
- R3 and R5 NOT BUILT. R3 is unbuildable against the final API (see `## Discovered`);
  R5 is entangled because `update` is the last `PUT /api/admin` caller. `update`
  was left exactly as Slice A left it rather than half-rewired. AC3 fails by
  design: two `/api/admin` call sites remain, both inside the update path.
  Descoped and reported, not absorbed — resolving it is Tony's call · builder call
- R2's "map 400 to a clear error" is implemented and executed, but the only way
  to reach a server 400 is a whitespace-only `--name` with an explicit `--slug`:
  the server's slug rules (`isUsableSlug`) are byte-identical to the CLI's own
  client-side checks, so every slug the server would reject is already refused
  before upload · builder call

### Slice A · 2026-08-12
- AC3 as written expects "the three PR #17 commits" to appear under
  `git log --follow`; PR #17 was squash-merged, so the pre-move history is a
  single commit `9756cd2`. Criterion's intent (history survives the move) is met
  and verified; the literal count cannot be · builder call

## Discovered

### Slice A · 2026-08-12
- `CLAUDE.md` says Tony Tools is "Currently three" and lists them; there are now
  four folders under `tools/`, and `arcade-publish/` changed character in this
  slice from real source to ledger-plus-pointer. Pre-existing staleness from PR
  #17, worsened here. Not in any slice's footprint — logged, not built
- `plugins/arcade/assets/README.md` still documents the whole-blob
  `PUT /api/admin` behavior under "How it behaves when things go wrong"; Slice B
  removes that code path and must revise those paragraphs

### Slice B · 2026-08-13 — build STOPPED before any code was written
- R3 cannot be built against the final API. It requires
  `PATCH /api/admin/seeds/<id>` "with the new url/name/featured", but the shipped
  PATCH (line7-site `main`, `app/api/admin/seeds/[id]/route.ts:20-31`) builds its
  patch from `name | slug | featured | order` only and drops `url` — matching this
  plan's own Constraints line, which also omits `url`. Verified live against the
  dev server: `PATCH {url}` alone → 400 `nothing to update`; `PATCH {url, name}` →
  **200 OK with the seed still pointing at the old blob**. The CLI would read that
  200 as success and then run its existing old-blob cleanup, leaving the seed
  pointing at a deleted file — a live page that 404s. `uploadedAt` is likewise
  unrefreshable
- Confirming it is a real gap, not a misreading: the shipped admin UI has no
  replace-the-file operation either (`sections/admin/Arcade.tsx` on `main` does
  upload+POST, PATCH name/featured, reorder, delete — nothing that changes an
  existing seed's `url`). File replacement is a CLI-only capability the
  per-resource API never gained
- R5 is entangled: `update` is the last `PUT /api/admin` caller, so AC3 cannot
  pass while R3 is unresolved. R1, R2, R4, R6, R7 are unaffected and buildable
- Resolved after the stop: R1, R2, R4, R6, R7 were built and verified; R3 and R5
  remain open pending a decision between (A) `update` becomes delete-then-recreate,
  which makes it internally destructive and contradicts what Slice D R4 wants the
  skill to say, or (B) add `url` to the server's PATCH allow-list, which the plan's
  Out of scope currently forbids. No third option exists: the upload endpoint mints
  its own id, so a blob cannot be overwritten in place either

### Slice B · 2026-08-14 — the R3 stop is resolved, option B
- Tony chose (B). Built in line7-site on branch `Main`, uncommitted at time of
  writing, three files: `lib/arcadeSeeds.ts` (new exported `SeedPatch` type
  widening `patchSeedList` to carry `url` + `uploadedAt`),
  `app/api/admin/seeds/[id]/route.ts` (PATCH accepts `url`, validates it through
  the same `isSafeSeedUrl` + `ARCADE_SEED_URL_HOSTS` allowlist POST uses, and
  server-stamps `uploadedAt` when `url` changes), and one added case in
  `lib/seedMutations.test.ts`. Docs: `docs/arcade/README.md` seeds-API block
- `uploadedAt` is stamped by the server, never taken from the body — POST stamps
  it the same way, and a caller-chosen value could forge list position because
  `sortSeeds` tiebreaks order-less legacy seeds on `uploadedAt`. Consequence
  worth knowing before Slice D writes the skill's copy: replacing the file on a
  legacy seed with no `order` moves it to the end of its block
- Verified live against a local dev server with `DATABASE_URL` unset (local
  `data/site.json` fallback, restored from backup afterward; nothing touched
  production). Eight probes: `PATCH {url}` alone → 200 and repointed, where it
  was 400 `nothing to update` before; `PATCH {url, name}` → 200 and the seed now
  actually points at the new blob, which is the exact case that previously
  returned 200 while silently keeping the old one; id, slug and `order` all
  survive; metadata-service, loopback, plain-http and `..`-traversal urls each
  400 `unusable url`; a non-string url 400s; an empty body still 400s `nothing
  to update`; a cookie-less PATCH still 401s. `npx tsc --noEmit` clean and
  `npx vitest run` 41/41 green
- R3 and R5 are now buildable and remain NOT BUILT — this entry unblocks them,
  it does not build them. Slice B's AC3 still fails until `update` is rewired
  off `PUT /api/admin`
- Incidental, not built: with `publish` now going through the server, a
  whitespace-only `--name` fails loudly with a 400 instead of storing a blank
  gallery label. That is the open ledger MINOR at `~/.local/bin/arcade-publish:247`
  going away as a side effect of the server owning validation — noted so a later
  recheck does not read it as an unexplained disappearance

## Punch list

### 2026-08-12 — review: Slice A
- MAJOR · `~/.local/bin/arcade-publish` → `plugins/arcade/assets/arcade-publish` (R4, plan:88) · the symlink target exists only on the unmerged `arcade-skill` branch, so any other checkout dangles it · `git checkout main` in tony-skills, then a `/jpb resolve` session runs the bare command `arcade-publish publish ...` (`~/.claude/skills/jpb/SKILL.md:294,356`) → ENOENT, the run doc silently fails to post. Before this slice the symlink resolved on `main`. The same breakage is already recorded happening on 2026-08-11 with the earlier branch · Slice A review (seams + correctness, convergent)
- MAJOR · `plugins/arcade/assets/README.md:46-50` · "one copy, two front doors" is false under both install routes, contradicting the plan's own single-copy Constraint · user-level install copies the skill (`~/.claude/skills/forge/assets/forge.py` is a regular file, not a symlink) and marketplace install materializes into `~/.claude/plugins/cache/`; after Slice B's rewire the terminal command follows the symlink to new code while `/arcade` runs a stale copy — two versions both writing to live production · Slice A review (spec + seams + correctness, convergent)
- MAJOR · `tools/arcade-publish/punch-list.md:19-21` · the ledger's own citation-resolution rule says the script "is now this folder's `arcade-publish`", which is false after the move; 15 bare `arcade-publish:<line>` and 5 `~/.local/bin/arcade-publish:<line>` citations resolve only through that rule · a future /signoff or /recheck checking whether "delete is one-shot destructive" (`:273-299`) is still open follows the documented location, finds no file, and re-reports the finding as new — the exact failure this consolidated ledger exists to prevent, and which happened once already · Slice A review (seams; spec + correctness concur at MINOR)
- MAJOR · `CLAUDE.md:14,22` and `README.md:12,20,49,65-99` · the repo's orientation docs contradict the tree after this slice: CLAUDE.md says "Five plugins" (seven exist) and Tony Tools is "Currently three" (four folders); README says "five Claude Code plugins", "Currently two" tools, and its layout tree omits `plugins/arcade/`, `plugins/shutdown/`, `tools/antigravity-mcp/`, `tools/arcade-publish/` · a session reads CLAUDE.md to place new arcade work, sees `tools/` described as holding installable real source with no mention of `arcade-publish`, and re-lands CLI edits under `tools/`. Partly pre-existing (`shutdown`), worsened here; no slice in the plan touches either doc · Slice A review (seams; spec + correctness concur at MINOR)
- MAJOR · `~/.claude/projects/-Users-tonycoon-Developer-jpb/memory/arcade-publish-location.md:11-17` · the memory note that exists to document this exact hazard still states the symlink targets `tools/arcade-publish/arcade-publish` and that recovery is `git show arcade-publish-cli:tools/arcade-publish/<f>` · a jpb session hits the dangling symlink above, loads this note as the documented remedy, and restores the old path as untracked files — recreating the second copy the plan forbids, at a path `main` also carries, while the symlink still points elsewhere · Slice A review (seams; correctness concurs at MINOR)
- MINOR · `plugins/arcade/assets/README.md:48-50` and `tools/arcade-publish/README.md:3-5` · both describe the `/arcade` skill in the present tense; it does not exist until Slice D and the plugin is not registered in marketplace.json, so it cannot be installed · a reader on this branch is told a front door exists that returns nothing · Slice A review (correctness)
- MINOR · `plugins/arcade/assets/arcade-publish:11,44` · the CLI's own config hint prints `"base": "https://line7.works"`, the apex host the README says will fail · new machine, no config → user pastes the printed hint verbatim → every command fails on the refused 307 redirect to `www`. Carried knowingly (open ledger MINOR at `:45`), but the README rewrite was the moment to flag it · Slice A review (correctness)
- MINOR · `plugins/arcade/assets/README.md:28-30` · asserts slug rules mirror the admin UI "byte for byte", contradicting the open ledger finding at `arcade-publish:26` · a 61-char name truncating on a hyphen yields a trailing-hyphen slug the admin UI would not produce · Slice A review (correctness)
- MINOR · `plugins/arcade/assets/README.md:52-55` · install snippet uses `ln -s`, which fails on any machine that already installed the tool · pasting it prints "File exists" and silently leaves the old target in place — in a doc whose entire purpose is describing a repoint. `ln -sfn` is the correct form · Slice A review (correctness)
- MINOR · `tools/README.md:3-14` vs `:28-32` · `tools/arcade-publish/` no longer satisfies the category definition eighteen lines above its own bullet — it is not an automation, dotfile, script, or spec, documents no dependencies or install, and the code it tracks is now installed by Claude Code · the next tool added follows the precedent and `tools/` degrades into a docs dump · Slice A review (seams)
- MINOR · `plugins/arcade/` · a plugin directory with no skill, no agent, and no marketplace entry; if the branch merges after Slice A alone, `main` gains a marketplace directory that installs nothing · transient by design (Slice D closes it), so a merge-granularity risk rather than a defect in place. Prior art: `plugins/shutdown/` is already in this state · Slice A review (seams)
- MINOR · `.gitignore:5-6` · pattern `generated-assets/` is unanchored and matches at any depth, broader than its "/forge run output" comment · a future tool legitimately named `generated-assets/` goes untracked and a `git clean` removes it silently — the same loss class the jpb memory note already records for this CLI. `/generated-assets/` would match the comment · Slice A review (seams)
- MINOR · `docs/arcade-skill-build-plan.md:95-106` · R1, R3, and R5 have no acceptance criterion; AC1 covers R4, AC2 the single-copy constraint, AC3 R2, AC4 R6 · a build that skipped plugin.json validity, the punch-list survival check, or the tools/README update would pass every stated criterion — a `plugin.json` with a trailing comma ships green here and only fails in Slice D · Slice A review (spec)
- MINOR · `docs/arcade-skill-build-plan.md:105-106` · AC4's "generated-assets/ stays untracked" clause was verified by rule inspection, not observation — no such directory exists in this repo, and `/forge` writes to the host project's cwd, so the rule is inert unless forge runs from inside tony-skills · Slice A review (spec)
- MINOR · `plugins/arcade/assets/README.md:82-90,97-100` · ships documenting the whole-blob `PUT /api/admin` concurrency model that Slice B deletes · if Slice A merges alone the plugin's user-facing doc describes a model the spec already calls obsolete. Builder disclosed this under `## Discovered` and assigned it to Slice B · Slice A review (seams)
- MINOR · `~/ObsidianVault/03-projects/line7/_index.md:52` and `~/ObsidianVault/03-projects/line7/arcade-publish-cli.md:28` · vault docs still route readers to `tony-skills/tools/arcade-publish/` as the source location · reader lands in the ledger folder and recovers via the pointer README — one hop of friction, not a break · Slice A review (seams + correctness)
- MINOR · `~/.claude/skills/jpb/SKILL.md:294,356`, `~/Developer/jpb/README.md:49`, `~/Developer/jpb/CLAUDE.md:46` · jpb invokes `arcade-publish` by bare PATH name, the pattern Slice D R1 calls "the vanishing bug this plan exists to bury" · not broken today, but it is the amplifier for the dangling-symlink MAJOR: the failure surfaces as a bare command-not-found with nothing pointing back at tony-skills. Lives in another repo this plan never touches · Slice A review (seams)

### 2026-08-12 — recheck: Slice A
- MAJOR · `~/.local/bin/arcade-publish` · (symlink target exists only on the unmerged branch, so any other checkout dangles it) · fixed — the installed command is now a launcher script that probes the plugin path then the tools path; executed against a synthetic `main`-shaped tree with no `plugins/` and the CLI ran from the fallback
- MAJOR · `plugins/arcade/assets/README.md:46-50` · ("one copy, two front doors" is false under both install routes) · fixed — README now states the two front doors do not stay in sync and that installing produces a real copy, with a reinstall instruction; the plan's Constraint carries a dated retraction (post-fix text at `plugins/arcade/assets/README.md:44-64`)
- MAJOR · `tools/arcade-publish/punch-list.md:19-21` · (the ledger's citation-resolution rule points at a file that no longer exists) · fixed — original sentence left intact per the additive-only rule and a dated location note appended after it; the named `:273-299` citation now resolves inside a 372-line file that exists (post-fix note at `tools/arcade-publish/punch-list.md:23-29`)
- MAJOR · `CLAUDE.md:14,22` and `README.md:12,20,49,65-99` · (orientation docs contradict the tree) · fixed — counted 7 plugin folders / 5 catalogued / 4 tools dirs against both docs including the Layout fence; no entry described but absent, none present but undescribed
- MAJOR · `~/.claude/projects/-Users-tonycoon-Developer-jpb/memory/arcade-publish-location.md:11-17` · (the note documenting this hazard gives the old path as the recovery route) · fixed — both offending statements replaced, and the copy-into-`tools/` recovery is now explicitly prohibited
- MAJOR · `tools/arcade-publish/README.md:9` · broke: still states "`~/.local/bin/arcade-publish` symlinks to the new location" after the symlink was replaced by a launcher — a session diagnosing a publish failure follows this pointer, runs `readlink`, gets nothing, and "repairs" it with `ln -sf`, reinstating the exact dangling-symlink defect the first item fixed; contradicts three other documents that all say launcher · Slice A fix pass
- MAJOR · `docs/arcade-skill-build-plan.md:103-104,116` · broke: Slice A's AC1 verify line still requires `readlink ~/.local/bin/arcade-publish` to show the plugin path, and the Footprint still labels that file "(symlink, outside the repo)" — `readlink` now exits non-zero on a regular file, so a re-verification pass running AC1 verbatim grades the slice as regressed when the launcher is the fix · Slice A fix pass

### 2026-08-12 — recheck: Slice A (second pass)
- MAJOR · `tools/arcade-publish/README.md:9` · (still describes the installed command as a symlink after it became a launcher, leading a reader to reinstate it with `ln -s`) · fixed — the file now names the launcher, states that `readlink` returning nothing is correct rather than a broken install, and explicitly forbids the `ln -s` "repair"; verified against reality (`file` reports a POSIX shell script, `readlink` exits 1) and cross-checked as consistent with `tools/README.md` and `plugins/arcade/assets/README.md` (post-fix text at `tools/arcade-publish/README.md:8-13`)
- MAJOR · `docs/arcade-skill-build-plan.md:103-104,116` · (AC1 requires `readlink` to succeed and the Footprint labels the file a symlink, so the criterion cannot pass against its own fix) · fixed — AC1 executed verbatim as amended and both halves passed: `arcade-publish list` from an unrelated directory exited 0 printing 7 seeds, and `sh -x` on the launcher showed it exec'ing `plugins/arcade/assets/arcade-publish`. Reviewer specifically checked whether the criterion had been weakened to pass and found it retains the reachability assertion `readlink` existed to prove; only the copy-pasteable one-liner was lost (post-fix text at `docs/arcade-skill-build-plan.md:102-109,121`)

### 2026-08-14 — review: the R3 unblock (line7-site seeds PATCH `url`)
Reviewed work is the line7-site carve-out, not a slice of this plan; no slice card
is flipped. All citations are line7-site paths unless prefixed.

Fix pass 2026-08-14 (same day, Tony's "go"): all 8 MAJORs addressed, pending
/recheck. Open question resolved by Tony: a file replacement does NOT preserve a
legacy seed's list position — simplest option, no `order` stamping, Slice A's
no-migration rule holds; MAJOR #3 became a doc-only fix (README now says the
caller cannot opt out, and why). #1: `lib/seedsPatchRoute.test.ts` added on the
staleWrite pattern; all seven planted mutations verified red against it. #2:
`uploadedAt` stamp now applies inside the mutator only when the url actually
differs. #4: README paragraph rewritten (order caveat, forgery rationale
corrected, `{ seed, seeds }` response documented). #5: CLI header + getSeeds
comments and assets/README.md updated to the true state. #6: duplicate-url →
`UrlTakenError` → 409. #7: `patchSeedList` strips `undefined` values before
spreading. #8: line7-site `docs/content-api-build-plan.md` gained a Deviations
entry and an amendment note on the Slice B PATCH requirement. MINORs fixed on
Tony's word (same day): the triplicated `ARCADE_SEED_URL_HOSTS` derivation is
now one `seedUrlAllowedHosts()` in `lib/arcadeStore.ts` used by all three
routes, and PATCH returns `previousUrl` when a repoint orphans the old blob —
both tested in `lib/seedsPatchRoute.test.ts`. The stale test comment was fixed
in passing. Remaining MINORs (bare `/uploads/` dir 500, silent name drop, 400
vs 404 ordering, plan-wording overstatement, accepted content-swap note) are
left open deliberately — Tony's call, not worth tackling.
- MAJOR · `app/api/admin/seeds/[id]/route.ts:46-48` · the new url guard has zero automated coverage and its removal is invisible to both CI gates · seven planted mutations — delete `isSafeSeedUrl` entirely, honor a caller-supplied `uploadedAt`, never stamp, drop `patch.url`, stamp epoch, allow any `http*`, return 200 instead of 400 — each survived `npx vitest run` 41/41 green with `npx tsc --noEmit` clean. Deleting lines 46-48 makes `PATCH {"url":"https://169.254.169.254/latest/meta-data/"}` a 200 that turns the public arcade page into a metadata-service reader, and nothing goes red. Route-handler tests are an established pattern in this repo (`lib/staleWrite.test.ts:62-98`, with the `@/*` alias added for exactly this in `vitest.config.ts:6`), so infeasibility is not a defense; a probe file on that pattern turned all seven mutations red · convergent across all five lenses (spec, correctness, seams, security, tests)
- MAJOR · `app/api/admin/seeds/[id]/route.ts:37,54` · the `uploadedAt` restamp fires on any PATCH carrying a `url` key, not on the url actually changing · `PATCH legacyA {url: <the url legacyA already has>}` → 200, `uploadedAt 2020-01-01 → now`, and the public list order goes `legacyA legacyB` → `legacyB legacyA`. A no-op request mutates state, bumps the store version (invalidating an in-flight legacy PUT token), and moves a live page; PATCH is non-idempotent, so a client retrying a timed-out request does real damage on the retry. The stamp is computed outside the mutator (correctly, so `updateSeeds` retries stay pure) but the stored url is only readable inside it — the fix is to apply it conditionally inside · convergent (correctness, seams, security, spec)
- MAJOR · `app/api/admin/seeds/[id]/route.ts:54` · replacing a legacy seed's file drops the page to the bottom of the public arcade with no way for the caller to opt out · verified against the real handler: `legacyA(2020) legacyB(2021) legacyC(2022)`, none with `order` → `PATCH legacyA {url}` → 200 → list becomes `legacyB legacyC legacyA`, because `sortSeeds` (`lib/arcadeSeeds.ts:89`) tiebreaks the no-`order` block on `uploadedAt` ascending. Passing `order` alongside `url` does not restore position, it relocates the seed into the ordered block ahead of every remaining legacy seed — a different wrong answer. `docs/arcade/README.md` discloses the consequence; disclosure is not a fix, and the doc does not say the caller cannot opt out · correctness lens
- MAJOR · `docs/arcade/README.md:89-97` · the added paragraph makes three claims the system does not honor · (a) "keeping the seed's id, slug and order" is false for the exact call R3 mandates: `{url, name, featured:true}` on a seed whose stored `featured` is false stamps `order: topOfFeaturedOrder(list)` at `route.ts:66-69`, so a seed at `order 7` lands at `-1`; (b) the `uploadedAt`-forgery rationale does not hold — `validateSeedList` (`lib/arcadeSeeds.ts:122-125`) only typechecks `uploadedAt` as a non-empty string, so the legacy `PUT /api/admin` still accepts a caller-chosen value and the CLI sets one client-side today (`tony-skills plugins/arcade/assets/arcade-publish:303`); an authenticated caller can also forge position more directly by sending `order`; (c) the fence at `:81` still documents the response as `{ seed }` when the route returns `{ seed, seeds }` (`route.ts:79`) — the field that would tell a client where a moved seed landed is the undocumented one. Slice D writes user-facing skill copy from this paragraph · convergent (spec, seams, security)
- MAJOR · `tony-skills plugins/arcade/assets/arcade-publish:19,129` and `plugins/arcade/assets/README.md:118-119` · the primary client's own contract is now false in three places and nothing in the change flags it · both source comments state that no per-resource endpoint can change a seed's `url`, which is why `update` stays on `PUT /api/admin` — the endpoint whose README:138-140 documents it resurrecting a page deleted from an open admin tab, and which forces `GET /api/admin`, flagged in line7-site CLAUDE.md as returning the whole document including secrets. The change removes the reason those hazards exist and leaves both the hazards and the claim in place · seams lens
- MAJOR · `app/api/admin/seeds/[id]/route.ts:49` · PATCH lets two seeds point at one url, and every delete path assumes exclusive blob ownership · no duplicate-url guard exists in `patchSeedList`, the route, or `validateSeedList` (which checks duplicate slug and id only). `PATCH A {url: <seed B's url>}` → 200; removing A in the admin UI then runs `DELETE /api/admin/upload {url: seed.url}` (`sections/admin/Arcade.tsx:435`) → B's blob is deleted → B's live gallery entry 404s with no error surfaced anywhere. Reachable through the whole-blob PUT before, but this puts it on the per-resource path the docs tell people to prefer · seams lens
- MAJOR · `lib/arcadeSeeds.ts:178-180` · `SeedPatch` moves the two fields that 500 the public page into a pure function that validates neither · `tsconfig.json` sets `strict` but not `exactOptionalPropertyTypes`, so `const patch: SeedPatch = { url: undefined, uploadedAt: undefined }` typechecks and the spread at `:196` writes `undefined` into the stored seed; `app/arcade/[slug]/route.ts:44` then does `seed.url.replace(...)` → TypeError → 500 on the page, and `sortSeeds` at `:89` does `a.uploadedAt.localeCompare(...)` → 500 on the whole gallery. `lib/seedGuards.test.ts:28` names `uploadedAt` verbatim as "the field that 500s the public page", and the codebase's own convention is to guard in the library — `validateSeedList` calls `isSafeSeedUrl` inside the pure layer for the other write path. Latent: today's route is the only caller and always stamps a valid ISO string · convergent (tests, seams, security, correctness)
- MAJOR · `docs/content-api-build-plan.md:76,107` · the line7-site plan that owns these routes has no record that its API contract moved · `:76` still specifies "PATCH (partial update: name, slug, featured, order)" and its Slice B stands `Status: signed off`; the change adds no `## Deviations`, `## Discovered`, or punch-list entry in that document. The carve-out authorizing the work lives in tony-skills, a different repo. That plan's own history graded this failure mode BLOCKER twice (`:353`, `:391` — the latter stayed "not fixed" precisely because the fix pass appended nothing to `## Deviations`). A future line7-site builder reads `:76` as governing and either reverts `url` as an unsanctioned drive-by or re-reports it as new · spec lens
- MINOR · `lib/arcadeSeeds.ts:64` reached from `route.ts:46` · PATCH can convert a live working page into an unhandled 500 · `isSafeSeedUrl` accepts any `/uploads/…` string without `..`, including a bare directory. Verified end to end: `PATCH a {url:"/uploads/"}` → 200 stored → `GET /arcade/a` throws `EISDIR: illegal operation on a directory, read` at `app/arcade/[slug]/route.ts:54` (`readFileSync`, no try/catch) → 500 on the public page, not a 404. Same for `/uploads/.` and `/uploads//`. The permissive check is pre-existing and shared with POST, but POST only creates a new broken page where PATCH breaks an existing working one · correctness lens
- MINOR · `app/api/admin/seeds/[id]/route.ts:42-45` · third verbatim copy of the `ARCADE_SEED_URL_HOSTS` split/trim/filter block (`app/api/admin/route.ts:30`, `app/api/admin/seeds/route.ts:33`) · the doc claims PATCH is "validated by the same allowlist POST uses" — the validator is shared, the host-list derivation is not. A future fix landing in one or two of three (e.g. lowercasing entries, or the dot-boundary fix below) means a custom-blob-domain deployment accepts a url at create and 400s the same url at repoint · convergent (spec, seams, security, correctness)
- MINOR · `app/api/admin/seeds/[id]/route.ts:49,79` · repointing orphans the old blob and the response gives no safe way to find it · the reply carries only the new url, so a caller must GET-then-PATCH, which is racy by construction. This is a regression against both existing cleanup paths: the admin UI deletes the blob after the seed delete (`sections/admin/Arcade.tsx:411-441`) and the CLI's current PUT-based `update` captures `oldUrl` and deletes it (`arcade-publish:298,320`). Returning `previousUrl` would make caller-side cleanup correct · convergent (correctness, seams, security)
- MINOR · `app/api/admin/seeds/[id]/route.ts:27,56` · an invalid `name` is now silently dropped when a valid `url` is present · `{name:"   ", url:<valid>}` → 200, name unchanged, no signal. Before this change the same request hit the `nothing to update` 400 and told the caller something was wrong; the url branch masks it. Exactly the class of thing the `Object.keys(patch).length === 0` guard existed to catch · correctness lens
- MINOR · `app/api/admin/seeds/[id]/route.ts:49` · no verification that the new url resolves, and no rollback · a typo'd but allowlist-passing blob URL (right host, wrong filename) is accepted with a 200 and immediately takes the live page down (`app/arcade/[slug]/route.ts:42` returns `notFound()` on `!res.ok`). The API response is indistinguishable from success; delete-then-recreate at least fails loudly at the upload step · correctness lens
- MINOR · `lib/seedMutations.test.ts:53-55` · the added test's comment describes client behavior that does not exist · it says the CLI's `update` "uploads a new blob and repoints the existing seed at it" and that losing the id is what makes the operation delete-then-recreate in disguise; `cmdUpdate` sets `id: upBody.id` today, so it does replace the seed's id, and it does so via PUT rather than PATCH. The test asserts an invariant the current client violates, framed as though it protects it · seams lens
- MINOR · `docs/arcade-skill-build-plan.md:368-369` · "No third option exists" overstates the design space it was used to justify amending `Out of scope` · `lib/blobStore.ts:47` already passes `allowOverwrite: true` with the comment "allow overwriting if the same id is re-uploaded", and the local fallback writes `public/uploads/<id>.html` by the same rule. The only thing preventing in-place replacement is `app/api/admin/upload/route.ts:16` hardcoding `const id = Date.now().toString()` and ignoring any caller-supplied id — a third option at roughly one line. Option B is arguably still the better call; the claim as written is what overstates · spec lens
- MINOR · `app/api/admin/seeds/[id]/route.ts:46` · a bad url against an unknown id returns 400, not 404 · validation runs before the existence check, so `PATCH nonexistent {url:"https://evil.example.com/x"}` → `400 unusable url` while a good url on the same id → `404 seed not found`; the caller cannot distinguish "you sent garbage" from "that seed is gone". Consistent with POST's ordering, just imprecise · correctness lens
- MINOR · `app/api/admin/seeds/[id]/route.ts:37-55` · one-call silent content swap under an established slug · before, replacing a live page meant DELETE+POST — two calls, a new id, visible downtime; now one PATCH repoints a bookmarked slug at different HTML while keeping id, slug and order, and `docs/arcade/README.md:120-129` records that pages on the arcade host are served with no sandbox CSP when `ARCADE_HOST` is set. Post-authentication only and the same reach the admin already had, so this is stealth and persistence, not new capability · security lens, downgraded from MAJOR on that basis

### 2026-08-14 — recheck: the R3 unblock (line7-site seeds PATCH `url`)
Closed-checklist re-inspection of the 8 MAJORs plus the two user-named MINORs
(triplicated host derivation; orphaned-blob previousUrl). Fresh independent
reviewer, current working trees; mutation checks executed and files restored
byte-identical (49/49 green, tsc clean after). No slice card exists for this
work (plan amendment, not a slice) so no Status line moves.
- MAJOR · `app/api/admin/seeds/[id]/route.ts:46-48` · (zero automated coverage on the url guard) · fixed — `lib/seedsPatchRoute.test.ts` exercises the real handler; mutations a/b/d/g planted and each turned the suite red, c/e/f pinned by freshness-window and http assertions
- MAJOR · `app/api/admin/seeds/[id]/route.ts:37,54` · (uploadedAt restamped on any url-carrying PATCH) · fixed — stamp applies only when the url differs from the stored one; pinned by the no-restamp test
- MAJOR · `app/api/admin/seeds/[id]/route.ts:54` · (legacy seed drops position with no opt-out) · fixed — doc-only per Tony's 2026-08-14 call (no position preservation); README states the consequence and the no-opt-out; no position-preserving code added
- MAJOR · `docs/arcade/README.md:89-97` · (three claims the system does not honor) · fixed — order-restamp caveat admitted, forgery rationale corrected, fence documents { seed, seeds, previousUrl? }
- MAJOR · `tony-skills plugins/arcade/assets/arcade-publish:19,129` + `assets/README.md:118-119` · (CLI contract false in three places) · fixed — all three now state PATCH accepts url since 2026-08-14 and the CLI rewire is Slice B R3/R5, unbuilt
- MAJOR · `app/api/admin/seeds/[id]/route.ts:49` · (two seeds can share one url; deletes assume exclusive blob ownership) · fixed — UrlTakenError in patchSeedList, 409 at the route, tested at both layers
- MAJOR · `lib/arcadeSeeds.ts:178-180` · (undefined patch values spread into the stored seed) · fixed — patchSeedList strips undefined before spreading, tested
- MAJOR · `docs/content-api-build-plan.md:76,107` · (owning plan has no record of the contract change) · fixed — requirement line amended, dated Deviations entry added
- MINOR · `app/api/admin/seeds/[id]/route.ts:42-45` · (third verbatim copy of the host-list derivation) · fixed — single seedUrlAllowedHosts() in lib/arcadeStore.ts used by all three routes; env flow through PATCH tested
- MINOR · `app/api/admin/seeds/[id]/route.ts:49,79` · (repoint orphans the old blob with no safe way to find it) · fixed — previousUrl returned iff the url changed, tested both ways, documented
Fix-introduced defects: none found (retry reassignment, not-found path, and env-test leak examined and cleared).

### 2026-08-14 — review: Slice B
- MAJOR · `plugins/arcade/assets/arcade-publish:324-338` · EOF (Ctrl-D / closed stdin) at the delete prompt exits 0 with no message and no delete · a wrapper running `delete` on a pty whose stdin closes early records the delete as done while the page is still live — `rl.question`'s callback never fires on EOF, the promise never resolves, the event loop drains, Node exits 0; reproduced deterministically under a pty. The build ledger's "harness artifact" entry was this bug · Slice B review (correctness, live)
- MAJOR · `plugins/arcade/assets/arcade-publish:303-316` · `update` trusts a PATCH 200 without checking the seed actually repointed (`body.seed.url` vs `upBody.url`) · against a server whose PATCH drops `url` (pre-PR-#25 deploy or rollback) the request returns 200 with the old url — CLI prints `Updated:` exit 0, upload orphaned, page unchanged, no signal; demonstrated live via fault-injection proxy. R5 keeps per-endpoint response guards; this one is missing · Slice B review (correctness)
- MAJOR · `plugins/arcade/assets/README.md:118-119` and `arcade-publish:16` · "id, slug, and order all survive" is uncaveated and false for `update --featured` on a non-featured seed · the server stamps top-of-featured `order` on that call (a seed at order 7 lands at -1); the identical uncaveated claim was graded MAJOR in the R3-unblock review and fixed server-side — reintroduced client-side, and Slice D writes the skill's copy from this README · Slice B review (seams)
- MINOR · `docs/arcade-skill-build-plan.md:335-339,411-413` · the 2026-08-13/14 ledger entries still state "R3 and R5 NOT BUILT" / "AC3 still fails" with no dated closure note · a future reader takes the Deviations entry as current state and re-reports R3/R5 as descoped · Slice B review (spec + seams, convergent)
- MINOR · `plugins/arcade/assets/arcade-publish:272` · whitespace-only `--name` silently drops the rename while the file replace succeeds · `update <slug> <f> --name "  "` → PATCH carries `name: ""`, server drops it (its own open MINOR), CLI prints `Updated:` exit 0 with the name unchanged; `--name ""` is swallowed client-side the same way · Slice B review (spec + seams + correctness, convergent; observed live)
- MINOR · `plugins/arcade/assets/arcade-publish:283-301` · the PATCH-409 rollback deletes a blob that at that moment belongs to another seed · reachable only via a same-millisecond upload-id collision (server mints `Date.now()` ids, blob store allows overwrite); the rollback assumes exclusive ownership of a url the 409 just declared shared · Slice B review (spec + seams, convergent)
- MINOR · `plugins/arcade/assets/arcade-publish:2-21` · R7's "version-bump" has no version identifier to bump — the header prose was rewritten and is accurate, but the literal criterion is unverifiable as written · Slice B review (spec + correctness, convergent)
- MINOR · `plugins/arcade/assets/arcade-publish:396-428` · duplicate or contradictory flags silently last-win (`--featured … --no-featured` lands unfeatured with no complaint) · contradicts the parser's own strictness rationale · Slice B review (correctness)
- MINOR · `plugins/arcade/assets/arcade-publish:245,343` · `update`/`delete` slugify the lookup argument, so a stored slug the slugifier cannot produce (e.g. the known trailing-hyphen case) is unaddressable — the seed becomes CLI-immortal, admin UI only · Slice B review (correctness)
- MINOR · line7-site `lib/arcadeSeeds.ts:103-105` + `app/api/admin/route.ts:27-28` · server comments still justify the raw-writable `seeds` key "for the arcade-publish CLI", which no longer uses it, and no owning-plan record notes the consumer is gone · editing line7-site is out of scope under this plan — record-keeping only · Slice B review (seams)

### 2026-08-14 — recheck: Slice B
Fixes in ceb2269 verified by a fresh independent reviewer; EOF and stale-200
scenarios executed (pty against a line7-site worktree at 0659cb7 on port 3215,
and a stub server for the stale-PATCH mode), docs read and cross-checked
against the server doc. No fix-introduced defects (double-resolve, rollback
honesty, and the absent-previousUrl path examined and cleared).
- MAJOR · `plugins/arcade/assets/arcade-publish:324-338` · (EOF at the delete prompt exits 0 with no message and no delete) · fixed — `rl.on("close")` with an answered flag resolves no; executed `\004` on a pty → `Aborted` + exit 1, seed intact; `n` and `y` regressions both correct (post-fix code at `arcade-publish:339-361`)
- MAJOR · `plugins/arcade/assets/arcade-publish:303-316` · (update trusts a PATCH 200 without checking the seed repointed) · fixed — `body.seed.url !== upBody.url` → rollback + fail; executed against a stale-mode stub: exit 1, clear message, stub logged the rollback DELETE of the new upload; happy mode still exits 0 and cleans up `previousUrl` (post-fix code at `arcade-publish:309-321`)
- MAJOR · `plugins/arcade/assets/README.md:118-119` and `arcade-publish:16` · (uncaveated "id, slug, and order all survive" claim) · fixed — both now carry the featured-toggle order-restamp caveat, verified accurate against line7-site `docs/arcade/README.md:90-92`; no uncaveated survival claim remains

### 2026-08-15 — fix: Slice B MINOR (per user)
- MINOR · `plugins/arcade/assets/arcade-publish:272` · (whitespace-only `--name` silently drops the rename) · fixed — the parser now rejects `--name` that trims empty, before any file read or network call, covering both `update` and `publish`; verified: both invocations fail exit 1 with `--name cannot be empty or whitespace-only`

### 2026-08-15 — review: Slice C
- MAJOR · `plugins/arcade/assets/arcade-publish:505` · unfeature accepts a lying 200 whose seed omits `featured`, and the :486 skip shares the coercion · server returns 200 `{"seed":{}}` while the seed stays featured → `Boolean(undefined)===false===featured` passes, CLI prints "Unfeatured" exit 0 with the site unchanged; a featured seed whose GET entry lacks the field gets "already not featured — nothing to do" with no request sent. `feature` catches the identical response — the lying-200 guard mandated by the Slice B review works in only one direction · Slice C review (correctness, live repro)
- MINOR · `docs/arcade-skill-build-plan.md:215-217` and `arcade-publish:420-446` · AC2's "the server receives no call" cannot pass verbatim — slug→id resolution requires login + GET before the pre-check can run; no write is ever sent (stub request logs) · a future re-verification watching the dev-server log grades AC2 failed; same criterion-can't-pass-verbatim class as Slice A's readlink AC · Slice C review (spec + seams, convergent)
- MINOR · `plugins/arcade/assets/arcade-publish:15-16` · the header comment still claims every command "touches a single seed", false for reorder, which rewrites every seed's `order` via the reorder endpoint; the README states it correctly · a reader of the header alone concludes reorder cannot collide with a concurrent admin edit; Slice D writes skill copy from these docs · Slice C review (seams)
- MINOR · `plugins/arcade/assets/arcade-publish:418` · a stored slugifier-unproducible slug (trailing-hyphen class) bricks `reorder` for the entire gallery — the slug can never be supplied, so every reorder fails the completeness pre-check · wider blast radius than the same known ledger MINOR on update/delete, where one seed is unreachable; no such slug exists today · Slice C review (spec + seams, convergent)
- MINOR · `plugins/arcade/assets/arcade-publish:486-489` · the already-in-state skip narrows R2 (an already-featured seed never PATCHes) and decides on a read that can go stale between GET and decision · disclosed as builder call in the ledger with sound rationale (a redundant featured:true restamps top-of-featured order server-side); logged for the record · Slice C review (spec + correctness)
- MINOR · `plugins/arcade/assets/arcade-publish:434,439` · an argument that slugifies to the empty string prints `unknown: ` naming nothing · `reorder "" a b c` fails safe, exit 1, nothing sent — cosmetic · Slice C review (seams + correctness, convergent)
- MINOR · `plugins/arcade/assets/arcade-publish:422-453` · reorder's slug→id resolution races a concurrent create: the id list goes incomplete and the server's bare 400 fires instead of the actionable client message · safe (nothing changed), degraded UX only · Slice C review (correctness)
- MINOR · `plugins/arcade/assets/arcade-publish:423` · two server-side seeds sharing a slug (corrupted store only) make the slug Map last-win and silently drop an id from the reorder list · client check claims completeness, server 400s · Slice C review (correctness)
- MINOR · `CLAUDE.md:24` (tony-skills) · the repo orientation doc still describes the CLI as "publish, update, and delete" — reorder and feature are missing · the doc sessions load automatically contradicts the command set; same drift pattern Slice A graded MAJOR · Slice C review (seams)
- MINOR · `docs/arcade-skill-build-plan.md:239-243` (Slice D surface) · Slice D's before/after reorder preview requirement does not warn that the requested order is not the resulting order whenever featured seeds are not listed first (server sort) · a skill previewing the raw requested list as "after" shows an order production will not display · Slice C review (seams)

### 2026-08-15 — recheck: Slice C
Fix in a81ab7a verified by a fresh independent reviewer; both scenario legs
executed against a hostile stub server under a sandboxed HOME (lying 200
`{"seed":{}}`, missing-`featured` GET entry), plus happy-path and skip
regressions. No fix-introduced defects.
- MAJOR · `plugins/arcade/assets/arcade-publish:505` · (unfeature accepts a lying 200 whose seed omits `featured`; the :486 skip shares the coercion) · fixed — the response guard now demands a real boolean equal to the requested state (post-fix code at `arcade-publish:510`): lying 200 → exit 1 "the seed did not flip", no success line; the skip is strict equality (post-fix `arcade-publish:488`): a seed lacking the flag gets the PATCH, never a silent skip. Regressions green: honest feature/unfeature exit 0, already-featured skip sends no PATCH

### 2026-08-15 — review: Slice D
- MAJOR · `CLAUDE.md:14,24` and `README.md:13,21,51-55,92,117` (tony-skills) · registering arcade in marketplace.json falsifies both orientation docs — "five catalogued", "/arcade is not built yet ... stays out of marketplace.json" — with no ledger record · a fresh session loads CLAUDE.md, concludes /arcade does not exist, and rebuilds it or strips the marketplace entry as unauthorized drift; re-breaks the doc-accuracy class the Slice A recheck cleared · Slice D review (seams + correctness + spec, convergent)
- MAJOR · `docs/arcade-skill-build-plan.md:29-31` vs `plugins/arcade/skills/arcade/SKILL.md` · the Constraints amendment assigns Slice D to document the installed-copy staleness and reinstall step; no Slice D artifact does — the rule lives only in the Slice A-era assets README · Tony edits the repo CLI, the terminal launcher updates instantly, the installed /arcade silently drives a stale copy against live production and the skill itself says nothing · Slice D review (spec)
- MAJOR · `docs/arcade-skill-build-plan.md:277,364-372` · AC1 and AC2's live-session legs are unexercised (disclosed builder call) — the skill has never been installed or triggered anywhere · the description's trigger phrasing or the plugin-root path fails under a real marketplace install and surfaces only when a live-production write is attempted; needs Tony's manual live-session run against another repo (AC2 against a localhost base) · Slice D review (seams + spec, convergent; rule-4 cap)
- MINOR · `plugins/arcade/skills/arcade/SKILL.md:105` · "a seed already in the requested state is skipped with no request sent" omits the strict-equality nuance — a legacy seed lacking the `featured` field gets the PATCH on unfeature, never a skip · skill predicts no request; CLI sends one · Slice D review (spec + seams + correctness, convergent)
- MINOR · `plugins/arcade/skills/arcade/SKILL.md:33` · "publish and update are slug-idempotent" — publish actually refuses a taken slug, as the file itself states 20 lines later; wording inherited from R4 · a session retries publish on the same slug expecting idempotence and gets a 409 · Slice D review (correctness)
- MINOR · `plugins/arcade/skills/arcade/SKILL.md:23` · the `$HOME/.claude/skills/arcade` fallback dangles under a naive copy of `plugins/arcade/skills/arcade/` alone — the real user-level convention is the flattened SKILL.md + assets/ layout forge uses, documented nowhere for arcade · a hand-installed skill resolves no CLI and every command 127s · Slice D review (correctness + seams, low confidence)
