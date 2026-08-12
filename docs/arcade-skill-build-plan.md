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
  - `PATCH /api/admin/seeds/<id>` `{ name? | slug? | featured? | order? }` →
    `{ seed }`; 404 unknown id; 409 slug taken.
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
Status: signed off with conditions

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
Status: not started

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
Status: not started

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
Status: not started

## Build assumptions

### Slice A · 2026-08-12
- AC1's verification ran `list` against live production `line7.works`; reading the
  gallery is non-destructive and the localhost exception does not exist until
  Slice B · builder call
- `plugins/arcade/assets/README.md`'s stale pointer to a findings ledger at
  `~/Developer/line7-site/docs/punch-list.md` was corrected to
  `tools/arcade-publish/punch-list.md` while rewriting that file's location
  sections; leaving a contradictory ledger pointer would have fought R3 · builder call

## Deviations

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
