---
name: sunset
description: >-
  Archive ("sunset") a project Tony has abandoned, across every layer at once:
  move its Obsidian vault docs to 90-archive, archive both its CLI/Claude-Code
  memory stores, cancel any scheduled agents or crons tied to it, move the local
  repo to ~/Developer/_archive, archive the GitHub repo, pause the Vercel
  project, back up + idle its database (Neon / Supabase), and archive its Notion
  board. Ends by generating a copy-paste handoff prompt that tells a browser/app
  LLM the project is now archived. Use when Tony wants to retire, shelve,
  mothball, archive, wind down, or "sunset" a project he will no longer work on.
  ALWAYS previews every change first and asks for a one-line reason before
  executing. Never deletes anything; every step is reversible.
---

# Sunset a project

Retire an abandoned project cleanly and reversibly. Sunsetting means Tony is
done with it and wants it out of his active view, so the default is a FULL
sunset across every layer. Nothing is ever deleted; everything moves to an
archive location, a paused state, a cancelled state, or is backed up, and can
be revived.

## Invocation

- `/sunset <project>` — full sunset (all layers below).
- `/sunset <project> --dry-run` — run Phase 0 only (resolve + preview), then stop.
- `/sunset <project> --keep-local` — skip moving the local repo.
- `/sunset <project> --keep-github` — skip archiving the GitHub repo.
- `/sunset <project> --keep-vercel` — skip pausing the Vercel project.
- `/sunset <project> --keep-db` — skip the database backup/idle step.

If no project name is given, ask which one.

## Where a project lives (the layers)

| Layer | Location | Sunset action |
|---|---|---|
| Vault docs | `~/ObsidianVault/03-projects/<slug>/` | move to `~/ObsidianVault/90-archive/<slug>/` |
| CLI memory (home summary) | `~/.claude/projects/-Users-tonycoon/memory/project_<slug>.md` (+ `MEMORY.md` line) | mark `status: archived`, de-index |
| CLI memory (project's own store) | `~/.claude/projects/*<Name>*/memory/` | archive contents into `_archive/<Name>/.claude-memory/` |
| Scheduled agents / crons | `/schedule` routines, `crontab -l`, `~/Library/LaunchAgents` | cancel/disable anything tied to the project |
| Local repo | `~/Developer/<Name>` | move to `~/Developer/_archive/<Name>` |
| GitHub repo | remote of the local repo | archive (read-only) |
| Vercel project | linked via `<repo>/.vercel/project.json`, or matched by name | pause (production blocked, reversible) |
| Database | connection string in the repo env (Neon / Supabase / other) | back up, then idle/pause. NEVER drop. |
| Notion board | searchable by project name via the Notion MCP | archive (move to trash, reversible) |

Names differ per layer (vault `project-knight`, repo `Project-Knight`, memory
`project_knight.md`). Resolve them in Phase 0 and confirm before acting.

## Core principles

- **Never delete.** Only move, flag, archive, pause, back up, or cancel. The database especially is never dropped.
- **Preview before executing.** Always show the full "what will change and where" table and wait for an explicit go.
- **Ask for the reason.** Always prompt Tony for a one-line "why" and use his words in the tombstone and the handoff prompt.
- **Kill active automation.** Scheduled agents and crons keep firing after everything else is archived; cancel them.
- **Capture knowledge before it strands.** The project's own CLI memory store gets orphaned when the repo moves; archive it first.
- **Protect the data.** The repo is in git; the database is not. Always back the database up before idling it.
- **Protect the code.** Never move or archive a repo with uncommitted or unpushed work without surfacing it first.
- **Operate on the vault via the local filesystem** (`~/ObsidianVault` is on this Mac). Obsidian picks up external changes on its own.

---

## Phase 0 — Resolve and preflight (always, even on --dry-run)

0. **Play the sunset cue** (cosmetic, non-blocking, best-effort): the moment a sunset begins, fire the sound and a compact terminal stamp. Run both, ignore any failure, and never let this block or fail the flow:
   - `afplay ${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sunset}/assets/set.wav >/dev/null 2>&1 &`
   - `python3 ${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sunset}/assets/sun_bar.py set`
   - Use the 3-line `sun_bar.py` stamp so it renders above Claude Code's output fold (taller scenes get collapsed; in-place animation gets captured as raw escape codes). A richer browser animation exists (`open "file://${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sunset}/assets/sun.html#set"`) but it pops a window, so use it only if Tony asks. If `afplay`/`python3` are unavailable, skip silently. (The matching `rise` cue belongs to the sunrise/revive skill.)

1. **Resolve the project across all layers.** Match case/hyphen/underscore variants.
   - Vault: `ls -d ~/ObsidianVault/03-projects/*<slug>*/`
   - CLI memory (home): `ls ~/.claude/projects/-Users-tonycoon/memory/*<slug>*.md` and grep that store's `MEMORY.md`.
   - CLI memory (project's own store): `ls -d ~/.claude/projects/*<Name>*/memory/ 2>/dev/null` and count its `.md` files. This per-directory store is what gets stranded on the repo move.
   - Scheduled agents / crons: enumerate `/schedule` routines (CronList), `crontab -l 2>/dev/null`, and `ls ~/Library/LaunchAgents`. Flag any whose prompt/command/path references `<Name>`, `<slug>`, or the repo path.
   - Local repo: `ls -d ~/Developer/*<Name>*/`
   - GitHub remote: `git -C <repo> remote get-url origin` (parse to `owner/repo`).
   - Vercel: read `<repo>/.vercel/project.json` for `projectId` + `orgId` (teamId); else match the name via the Vercel MCP `list_projects`. No match means not on Vercel; skip.
   - Database: grep the repo env (`.env`, `.env.local`, `.vercel/.env*`, or `vercel env pull`) for `DATABASE_URL` / `POSTGRES_URL` / `NEON_*` / `SUPABASE_*`. Identify the provider from the host (`*.neon.tech` = Neon, `*.supabase.co` / `*.pooler.supabase.com` = Supabase, else note the host and ask). **Capture the connection string now** for the backup step. None found means skip.
   - Notion board: `notion-search` for the project name and any board title named in the vault doc. Note the matching page(s) to archive.
   - Loose ends (surface only, never auto-acted): scan the repo for non-Vercel hosting (`wrangler.toml`/`wrangler.jsonc` = Cloudflare, `netlify.toml` = Netlify, `fly.toml` = Fly, `render.yaml` = Render) and any external tracker that is not Notion. Collect into one line for the preview.
   - Note any layer where nothing is found; that layer is skipped.

2. **Git safety check** (if a local repo was found and not `--keep-local`):
   - `git -C <repo> status --porcelain` for uncommitted changes.
   - `git -C <repo> log --branches --not --remotes --oneline` for unpushed commits.
   - If either is non-empty, STOP and tell Tony exactly what is unsaved. Offer to commit and push it before archiving. Do not proceed until the repo is clean and pushed, or Tony explicitly says to archive it as-is.

3. **Ask for the one-line reason.** Prompt: "One line: why are you sunsetting <project>?" Wait for his answer.

4. **Print the preflight table and STOP for confirmation.** Show every concrete action, for example:

   ```
   SUNSET PREVIEW — <project>      reason: "<Tony's reason>"
   ─────────────────────────────────────────────────────────
   Vault     move  03-projects/<slug>/  ->  90-archive/<slug>/      (N files)
             flip  _index.md  status -> archived; tombstone; fix index + AGENTS.md
   Memory    flip  home note project_<slug>.md  status: archived + de-index
             archive  project store (M notes)  ->  _archive/<Name>/.claude-memory/
   Schedules cancel  <list of routines/crons tied to the project>   (none = skip)
   Repo      move  ~/Developer/<Name>  ->  ~/Developer/_archive/<Name>   (git clean + pushed: yes)
   GitHub    archive  <owner>/<repo>  (read-only)
   Vercel    pause    <project>  (production blocked; reversible)
   Database  backup   <provider> -> _archive/<Name>/db-backup-<date>.sql, then idle (never drop)
   Notion    archive  "<board title>"  (move to trash, reversible)
   Loose end surfaced only (you decide): <non-Vercel hosting / other trackers, or "none">
   Output    handoff prompt to paste into a browser/app LLM
   ─────────────────────────────────────────────────────────
   Nothing is deleted. Reply "go" to execute, or tell me what to change.
   ```

   If `--dry-run`, stop here. Otherwise wait for an explicit "go" before Phase 1.

---

## Phase 1 — Vault

1. `mkdir -p ~/ObsidianVault/90-archive` and move the folder:
   `mv ~/ObsidianVault/03-projects/<slug> ~/ObsidianVault/90-archive/<slug>`
2. In the moved `90-archive/<slug>/_index.md`, set frontmatter `status: archived` and add `archived: <today>`.
3. Write the tombstone `90-archive/<slug>/_sunset.md` (template at the bottom).
4. Edit the root `~/ObsidianVault/_index.md`: remove the project from "Active projects" and add it under an "## Archived" heading (create it if missing), linking to `90-archive/<slug>/_index`.
5. Edit `~/ObsidianVault/AGENTS.md`: remove the slug from the "Known projects" line.
6. Check for links the move broke: `grep -rn "03-projects/<slug>" ~/ObsidianVault --include='*.md'` and repoint any survivors to `90-archive/<slug>`.

## Phase 2 — CLI / Claude Code memory (two stores)

Claude Code memory is per launch-directory, so a sunset project has up to two stores.

1. **Home summary note** (`~/.claude/projects/-Users-tonycoon/memory/project_<slug>.md`): set frontmatter `status: archived`, add `archived: <today>`, keep the file, and move its bullet in that store's `MEMORY.md` under an `## Archived` heading (create it if missing).
2. **The project's own store** (`~/.claude/projects/*<Name>*/memory/`): it will be orphaned once the repo moves, so preserve it:
   - `mkdir -p ~/Developer/_archive/<Name>/.claude-memory`
   - `cp -R ~/.claude/projects/*<Name>*/memory/. ~/Developer/_archive/<Name>/.claude-memory/`
   - Confirm the copy, record the source path and file count in the tombstone. Leave the original in place (a harmless orphan once the repo path changes); do not delete it.

## Phase 3 — Scheduled agents and crons (cancel)

Active automation is the one leftover that keeps firing after everything else is archived, so cancel anything tied to the project.

1. From the Phase 0 scan, take the flagged entries (routines, crontab lines, launchd agents) that reference the project.
2. On "go," cancel/disable each: `CronDelete` (or the `/schedule` delete path) for Claude Code routines; remove or comment out the crontab line; unload the launchd agent. 
3. Record exactly what was cancelled in the tombstone so it can be recreated if revived.
4. If the scheduling tools are unavailable in this session, surface the findings and ask Tony to cancel them manually.

## Phase 4 — Local repo (skip if --keep-local)

Only after the Phase 0 git safety check passed, and after Phase 2 copied the project memory store:
1. `mkdir -p ~/Developer/_archive`
2. `mv ~/Developer/<Name> ~/Developer/_archive/<Name>`

## Phase 5 — GitHub (skip if --keep-github)

Order matters: push everything BEFORE archiving, because an archived repo is read-only and rejects pushes.
1. Optional final marker (run before the repo move and before GitHub archive): `git -C <repo path> tag sunset-<today> && git -C <repo path> push origin sunset-<today>`.
2. `gh repo archive <owner>/<repo> --yes`

## Phase 6 — Vercel (skip if --keep-vercel)

Pause, never delete. Pausing blocks the production deployment and stops auto-assigning custom domains. Reversible with unpause; keeps env vars, domains, and deploy history.

1. Get `projectId` + `orgId` (team id) from `<repo>/.vercel/project.json`, or via the Vercel MCP `list_projects` if the file is absent.
2. Pause via the REST API (needs a Vercel token from `$VERCEL_TOKEN` or the logged-in CLI):
   `curl -X POST "https://api.vercel.com/v1/projects/<projectId>/pause?teamId=<orgId>" -H "Authorization: Bearer $VERCEL_TOKEN"`
3. If no token is available, do not guess: print the ready-to-run curl plus the dashboard path (Project → Settings → Pause Project) and ask Tony to run it with `!` or click it.

## Phase 7 — Database (skip if --keep-db)

The database is the only layer whose data is NOT in git, and abandoned free-tier projects can eventually be reclaimed by the provider. So "archive" here means keep a copy and idle it. **NEVER drop or delete a database during sunset.**

1. Use the connection string captured in Phase 0.
2. **Back it up first, while it is still reachable** (before any pause):
   `pg_dump "<direct/non-pooled connection string>" > ~/Developer/_archive/<Name>/db-backup-<today>.sql`
   Confirm the file is non-empty. If `pg_dump` is unavailable or the dump fails, STOP and tell Tony rather than skipping the backup silently.
3. **Idle the compute, never the data:** Neon auto-suspends when idle (optionally suspend now); Supabase pause from the dashboard (or it auto-pauses after ~1 week idle); other providers, note and let Tony idle.
4. **Never** run `DROP`, delete the database, or remove the integration resource during sunset.

## Phase 8 — Notion (archive the project's board)

If the project has a Notion board or pages, archive them automatically (no need to ask first; this is reversible, Notion keeps trashed items ~30 days).

1. Use the Phase 0 `notion-search` matches. Confirm the page(s) belong to this project (title/parent), not a coincidental name hit.
2. Archive each via the Notion MCP: `notion-update-page` to set it archived, or `notion-move-pages` to move it to trash.
3. Record the archived page titles/URLs in the tombstone.
4. If the Notion MCP is unavailable in this session, surface the board link and ask Tony to archive it manually.

## Phase 9 — Closeout

1. Print a summary of what changed, then the revive recipe:

   ```
   SUNSET COMPLETE — <project>
     Vault     -> 90-archive/<slug>/ (status: archived)
     Memory    -> home note archived + de-indexed; project store -> _archive/<Name>/.claude-memory/
     Schedules -> cancelled: <list, or none>
     Repo      -> ~/Developer/_archive/<Name>
     GitHub    -> archived (read-only)
     Vercel    -> paused (production blocked)
     Database  -> backed up to _archive/<Name>/db-backup-<date>.sql; idled (not dropped)
     Notion    -> "<board>" archived (in trash, restorable ~30 days)
     Loose ends (you handle): <non-Vercel hosting / other trackers, or none>

   To revive: move the vault folder back to 03-projects/, set both status fields
   to active, move the repo back to ~/Developer/, `gh repo unarchive <owner>/<repo>`,
   unpause Vercel (`POST /v1/projects/<projectId>/unpause`), restore/unsuspend the
   database, restore the Notion board from trash, and recreate the cancelled schedules.
   ```

2. **Generate the browser/app LLM handoff prompt.** Sunsetting in Claude Code does not inform Tony's other LLM surfaces (claude.ai web, the desktop app, ChatGPT, Codex). Fill in the variables and print this in a fenced block for Tony to copy-paste:

   ```
   Heads up: I have sunset (archived) my project "<Project Name>" as of <today>.
   Reason: <Tony's reason>.

   It is now retired across all my systems:
   - Obsidian vault: moved to 90-archive/<slug>/ (status: archived)
   - Local repo: ~/Developer/_archive/<Name>
   - GitHub: archived (read-only)
   - Vercel: paused
   - Database: backed up and idled (not deleted)
   - Notion board: archived
   - Scheduled agents/crons: cancelled

   Going forward, treat "<Project Name>" as inactive: do not suggest new work on
   it, do not include it in active-project lists, and if you keep any project
   context or memory about it, mark it archived. If you can reach my Obsidian
   vault, note it now lives under 90-archive/. If you have a saved Project or
   space for it, archive that too. Acknowledge and update accordingly.
   ```

---

## Tombstone template (`90-archive/<slug>/_sunset.md`)

```markdown
---
created: <today>
source: claude-code
type: sunset
status: archived
tags: [meta, archived]
---

# Sunset — <Project Name>

- **Date:** <today>
- **Reason:** <Tony's one-line reason>

## Where everything went
- Vault docs: `90-archive/<slug>/`
- CLI memory (home note): `project_<slug>.md` (status: archived)
- CLI memory (project store): copied to `_archive/<Name>/.claude-memory/` (M notes, from `<source path>`)
- Scheduled agents/crons: cancelled -> <list, or none>
- Local repo: `~/Developer/_archive/<Name>`
- GitHub: `<owner>/<repo>` archived (read-only)
- Vercel: `<project>` paused (production blocked)
- Database: `<provider>` backed up to `_archive/<Name>/db-backup-<date>.sql`; idled (not dropped)
- Notion: "<board>" archived (in trash, restorable ~30 days)
- Loose ends surfaced for manual handling: <list, or none>

## Final state at sunset
<one or two lines on where the project stood when retired>

## To revive
Move the vault folder back to `03-projects/`, flip both status fields to
`active`, move the repo back to `~/Developer/`, `gh repo unarchive <owner>/<repo>`,
unpause Vercel, restore/unsuspend the database, restore the Notion board, and
recreate the cancelled schedules.
```
