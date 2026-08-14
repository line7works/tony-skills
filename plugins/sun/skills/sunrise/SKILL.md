---
name: sunrise
description: >-
  Bootstrap ("sunrise") a new project Tony is ready to make real, across every
  layer at once: scaffold a local repo in ~/Developer by archetype (web app /
  monorepo / static / Electron / library / script), seed its boot docs (README,
  CLAUDE.md, AGENTS.md, .gitignore, .env), create + push a private GitHub repo,
  link Vercel with auto-deploys, provision a Supabase (or Neon) database through
  the Vercel Marketplace and wire its env, create the Obsidian project folder +
  index, create the CLI/Claude-Code memory note, and provision a per-project
  Notion task tracker + roadmap board (mirroring Project Knight). Ends by deploying once to a
  live URL and generating a copy-paste handoff prompt that tells a browser/app
  LLM the project is now active. Use when Tony wants to start, spin up, kick off,
  bootstrap, scaffold, formalize, or "sunrise" a new project he is committing to.
  ALWAYS previews every change first and asks what the project is before
  executing. Never clobbers anything that already exists; ends at a verified
  green baseline. The inverse of the `sunset` skill.
---

# Sunrise a project

Break ground on a new project cleanly and completely. Sunrising means Tony has
taken an idea past the "let's make this real" line and wants the full scaffold
stood up across every layer at once, wired together, and proven live. Nothing
is left half-built: the run ends only when the repo is pushed, the deploy is
green, and the project is on the active rolls in the vault and in memory.

This is the inverse of `sunset`, but it is **not** a pure mirror:

- **Creation is conditional, teardown is uniform.** Sunset shuts down all layers
  the same way every time. Sunrise only hooks up the layers the archetype needs
  (a library gets no database; an Electron app is not web-hosted). See the
  archetype matrix below.
- **It must end verified-live, not just created.** Sunset ends reversible;
  sunrise ends proven. The push succeeded, the deploy returns 200, and
  `vercel env pull` returns the keys.

## Invocation

- `/sunrise <name>` — full sunrise (repo + GitHub + Vercel + database + vault + memory).
- `/sunrise <name> --dry-run` — run Phase 0 only (resolve + preview), then stop.
- `/sunrise <name> --type <archetype>` — preset the archetype, skip the type prompt.
- `/sunrise <name> --promote <path>` — adopt an existing local prototype dir instead of scaffolding from zero.
- `/sunrise <name> --public` — make the GitHub repo public (default is private).
- `/sunrise <name> --db <supabase|neon>` — pick the database provider (default supabase).
- `/sunrise <name> --no-db` — skip the database layer.
- `/sunrise <name> --no-vercel` — skip the Vercel layer.
- `/sunrise <name> --no-github` — local + vault + memory only.
- `/sunrise <name> --no-notion` — skip the Notion task tracker + roadmap board (provisioned by default, mirroring Project Knight).

If no project name is given, ask for one. If no archetype is given, ask (default: web app, single).

## Archetype decides which layers fire

The "what type of repo" answer drives the rest. Only hook up the utilities the
building actually needs.

| Archetype | Vercel | Database | npm publish | Scaffolder (default, overridable) |
|---|---|---|---|---|
| **1. Web app (single)** | host | optional (default on) | no | `npx create-next-app@latest` |
| **2. Monorepo** | per-app | optional (default on) | maybe | npm workspaces (`packages/*` + `apps/*`); or `create-turbo` |
| **3. Static / content** | static host | off | no | `npm create astro@latest`; or single-file `index.html` |
| **4. Desktop / Electron** | env-plane only* | usually (default on) | no | electron-vite; Vercel is a no-op build |
| **5. Library / package** | none | none | yes | `npm init` + tsup/tsconfig |
| **6. Script / CLI / Python** | none | optional (default off) | maybe | `npm init` (Node) or `uv`/venv + pyproject (Python) |

\* **Electron env-plane:** per Project Knight's ADR 002, an Electron app still
gets a Vercel project, but only as the Neon/Supabase **management plane** — a
no-op build whose job is to hold the DB integration and feed `vercel env pull`.
Add a placeholder `public/index.html` + minimal `vercel.json` so the build
succeeds. There is no website.

`--db` / `--no-db` / `--no-vercel` override the archetype defaults. The Notion
task board (Phase 5) is archetype-independent and on by default; `--no-notion` skips it.

## Core principles

- **Never clobber.** If anything already exists at any layer in Phase 0, STOP and surface it. Offer to adopt it (`--promote`), never overwrite. This is the mirror of sunset's "never delete."
- **Preview before executing.** Always show the full "what will be created and where" table and wait for an explicit "go."
- **Ask what it is.** Always prompt Tony for a one-line "what is this / what are you building" and use his words in `_index.md`, `CLAUDE.md`, the memory note, and the handoff prompt. (Mirror of sunset's "ask the reason.")
- **Layers are conditional on the archetype.** Don't run a gas line to a tool shed. Gate Vercel and the database per the matrix.
- **Get to green.** Don't hand back a half-wired skeleton. End on a verified push + a **200 on the clean `<project>.vercel.app` alias** + a populated `.env.local`.
- **Wire the cross-links from birth.** The repo `CLAUDE.md`, the vault `_index.md`, and the memory note all point at each other on day one, so the boot path works immediately.
- **Resumable.** If a run dies partway and is re-invoked, detect what already exists (Phase 0 collision check) and continue rather than double-create.
- **Operate on the vault via the local filesystem.** Canonical is `~/ObsidianVault` **on the Mac Studio** — not the laptop, whose copy is retired. Obsidian picks up external changes on its own. Never proceed without passing the vault gate in Phase 0.

---

## Phase 0 — Resolve and preflight (always, even on --dry-run)

### Vault gate — run this FIRST, before the cue, before anything else

Canonical is `~/ObsidianVault` **on the Mac Studio** (moved there 2026-07-27). The laptop's
copy is retired to `~/ObsidianVault-RETIRED-2026-07-27` and `~/ObsidianVault` does not
exist there. Phase 6 runs `mkdir -p ~/ObsidianVault/03-projects/<slug>`, which on a machine
without canonical **silently creates a phantom second vault** holding exactly one project —
no error, nothing to notice. That is the split-brain that took a full session to unwind in
July 2026. `mkdir -p` cannot tell you the vault is missing; this gate is the only thing
that can.

Run this and STOP unless it prints `VAULT OK`:

```bash
V="$HOME/ObsidianVault"
RP="$(cd "$V" 2>/dev/null && pwd -P)"
if   [ -z "$RP" ];                      then echo "STOP: no vault at $V"
elif [ ! -f "$V/AGENTS.md" ];           then echo "STOP: $V has no AGENTS.md — stub, not canonical"
elif [ ! -d "$V/03-projects" ];         then echo "STOP: $V has no 03-projects/ — incomplete"
elif [ "${RP#*/Documents/}" != "$RP" ]; then echo "STOP: vault is inside Documents/iCloud: $RP"
else echo "VAULT OK — $RP — $(find "$V" -name '*.md' -not -path '*/.obsidian/*' | wc -l | tr -d ' ') notes"
fi
```

If it prints anything other than `VAULT OK`, **abort the whole skill.** Do not `mkdir` the
vault or anything beneath it, and do not continue to any later phase — a partial sunrise
that scaffolds a repo but writes its vault docs into a phantom vault is worse than no
sunrise at all. Tell Tony which machine he appears to be on and that canonical lives on
the Mac Studio.

0. **Play the sunrise cue** (cosmetic, non-blocking, best-effort): the FIRST thing the skill does. The moment a sunrise begins, fire the sound and a compact one-line terminal stamp. Run both, ignore any failure, and never let this block or fail the flow:
   - `afplay ${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sunset}/assets/rise.wav >/dev/null 2>&1 &`
   - `python3 ${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sunset}/assets/sun_bar.py rise`
   - Keep it to the **ONE-LINE** `sun_bar.py rise` output (gold→blue half-block bar, sun on the left, "☀ S U N R I S E"). Claude Code collapses taller output behind a "+N lines" fold and captures in-place ANSI animation as raw escape codes, so one line is the only reliable in-flow cue — do not attempt terminal motion. A richer browser animation exists (`open "file://${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sunset}/assets/sun.html#rise"`) but it pops a window, so use it only if Tony asks. If `afplay`/`python3` are unavailable, skip silently. (Assets are shared with `sunset`; do not rebuild them. The `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sunset}/assets` form resolves both ways: the plugin's bundled `assets/` when installed as a plugin, or `~/.claude/skills/sunset/assets/` when copied in as a user-level skill.)

1. **Gather the inputs.**
   - **Name** (required). **Archetype** (the 6 above; default web app, single). **One-line "what is this."** **Visibility** (default private). **Database?** (archetype default; `--db`/`--no-db` override). **Promote an existing dir?** (`--promote <path>`).

2. **Derive the three name variants and show them for confirmation.** Tony's local-dir casing is inconsistent (`Helix`, `PGL`, `belgariad-codex`), so always confirm.
   - `<Name>` — repo + local dir under `~/Developer/` (spaces → hyphens; keep his casing).
   - `<slug>` — kebab-case, lowercase (vault folder + frontmatter `name` + handoff).
   - `<slug_>` — the slug with hyphens → underscores (memory filename only, matching existing `project_pour_guys.md` / `project_belgariad_codex.md`).

3. **Collision check across all layers (never clobber).** Each must be clear, unless `--promote` points at it:
   - Local: `ls -d ~/Developer/*<Name>* 2>/dev/null`
   - GitHub: `gh repo view <owner>/<repo>` should 404 (`tiny-tunnel-dot` is the owner).
   - Vault: `ls -d ~/ObsidianVault/03-projects/<slug> 2>/dev/null`
   - Memory: `ls ~/.claude/projects/-Users-tonycoon/memory/project_<slug_>.md 2>/dev/null`
   - Vercel: Vercel MCP `list_projects` (or `npx vercel project ls`) — name must be free.
   - Notion (low priority — page titles aren't unique): optionally `notion-search` the project name to avoid a duplicate parent page.
   - If any exists, STOP and tell Tony exactly what is already there. Offer to adopt it (treat as `--promote`) or pick a different name. Do not overwrite.

4. **Tooling preflight.**
   - `gh auth status` (expect logged in as `tiny-tunnel-dot`).
   - `git config user.email` and `git config user.name` — both must be set, or the first commit is authorless. If either is empty, fail loud HERE (ask Tony to set them, or plan to pass `git -c user.email=… -c user.name=…` on the commit) rather than producing an authorless commit deep in the run.
   - `npx vercel whoami` (expect logged in).
   - If a database is in scope, confirm the Marketplace slug with `npx vercel integration discover supabase` (returns the slug Phase 4 uses). The first-time terms gate is handled in Phase 4 — don't guess.

5. **Ask the one-line description.** Prompt: "One line: what is <project> / what are you building?" Wait for his answer.

6. **Print the create preview and STOP for confirmation.** Show every concrete action, for example:

   ```
   SUNRISE PREVIEW — <project>     "<Tony's one-line>"
   archetype: <archetype>   visibility: private   db: supabase (via Vercel)
   names: dir/repo <Name>  ·  slug <slug>  ·  memory project_<slug_>.md
   ──────────────────────────────────────────────────────────────────────
   Repo     mkdir ~/Developer/<Name>; scaffold <scaffolder>; git init
            seed README.md, CLAUDE.md, AGENTS.md, .gitignore, .env.example
   GitHub   create tiny-tunnel-dot/<repo> (private); push main
   Vercel   link project <Name> (auto-connects GitHub repo; auto-deploys on)
   Database vercel integration add supabase (auto-connect + auto-pull)
            -> .env.local (POSTGRES_URL + keys, ~17 vars)
   Notion   create page "<project>" + Task Tracker & Roadmap DBs
            (mirror Project Knight); record DB IDs in _index.md
   Vault    create 03-projects/<slug>/_index.md (seed, status: active)
            add to root _index.md "Active projects"
   Memory   create project_<slug_>.md + MEMORY.md line
   Verify   first deploy -> live URL, expect 200
   Output   handoff prompt to paste into a browser/app LLM
   ──────────────────────────────────────────────────────────────────────
   Nothing existing is touched. Reply "go" to execute, or tell me what to change.
   ```

   If `--dry-run`, stop here. Otherwise wait for an explicit "go" before Phase 1.

---

## Phase 1 — Local repo + scaffold (foundation and framing)

Dependencies run forward here (you can't hook utilities before the framing is
up), so the repo comes first.

1. `mkdir -p ~/Developer/<Name>` (or adopt the `--promote` path in place).
2. **Scaffold per archetype** using the matrix's default scaffolder (or Tony's override), non-interactively where possible. Two things current scaffolders do that you must expect:
   - **They init git themselves.** `create-next-app` ignores `--no-git` (use `--disable-git`, or just let it init) and prints "Initialized a git repository." So the dir may already be a git repo — possibly with a scaffold commit — before step 4.
   - **They pre-seed agent files.** `create-next-app` now ships its own `CLAUDE.md` (just `@AGENTS.md`) and `AGENTS.md` (with a `<!-- BEGIN:nextjs-agent-rules -->` block: "this is NOT the Next.js you know… read `node_modules/next/dist/docs/` before writing code"). Astro/Turbo may do the same. Do NOT blind-overwrite these — the "never clobber" rule applies.
3. **Seed the boot docs** (templates at the bottom), MERGING with anything the scaffolder already wrote:
   - `CLAUDE.md` — the 60-second boot doc pointing at the vault `_index.md`; keep it primary. If the scaffolder left a `CLAUDE.md`/`AGENTS.md`, merge rather than overwrite: write the boot-doc content but PRESERVE any framework `nextjs-agent-rules` (or equivalent) block — it's real and load-bearing.
   - `AGENTS.md` — the stub pointing at `CLAUDE.md`, keeping the framework warning block.
   - `README.md` — name, one-liner, dev commands, links.
   - `.gitignore` — archetype-appropriate. **Then append `!.env.example`** so the example env is actually tracked: scaffolder `.gitignore`s use `.env*`, which silently swallows `.env.example`. Verify after the commit: `.env.example` tracked, `.env.local` still ignored.
   - `.env.example` — committed, keys present with no values.
4. **Idempotent git.** The scaffolder may have already `git init`'d (and committed), so: init only if not already a repo; ensure the default branch is `main`; stage everything; commit. If there's nothing to commit because the scaffold already committed, that's fine — don't fail. Never assume a clean slate.

## Phase 2 — GitHub (the permit)  [skip if --no-github]

Create the remote, link it, and push in one shot:

1. `gh repo create tiny-tunnel-dot/<repo> --private --source=. --remote=origin --push` (`--public` if chosen).
2. **Document the branch rule** in `CLAUDE.md`: feature branches + PRs, never push to `main` (Tony's standing rule). Optionally add a GitHub ruleset requiring PRs via `gh api`; note that branch protection on Free private repos may be limited, so if it errors, leave it documented rather than failing the run.

## Phase 3 — Vercel (the meter)  [archetype-gated; skip if --no-vercel]

Skip entirely for library / script / pure-Python. For Electron, wire it as the
env-plane only.

1. `npx vercel link --yes` (creates/links a Vercel project named `<Name>`).
2. **`npx vercel git connect` is usually a no-op now** — `vercel link --yes` already connects the GitHub repo in the same call ("Connecting GitHub repository… Connected"). Run it only as an idempotent safety confirm (expect "already connected"). If `link` did NOT connect — e.g. the Vercel GitHub App is scoped to "select repositories" and this repo isn't on the allowlist — surface that exact GitHub step; don't guess.
3. **Electron env-plane only:** add a placeholder `public/index.html` + minimal `vercel.json` (the Project Knight pattern) so the no-op build succeeds. There is no website to host.

## Phase 4 — Database (the utilities)  [archetype-gated; skip if --no-db]

Default on for web app / monorepo / Electron; off for static / library / script.
Provision **Supabase via the Vercel Marketplace** (default). `--db neon` swaps the
provider through the same flow — provider-agnostic.

1. **Provision + connect + pull in ONE command:** `npx vercel integration add supabase -m region=sfo1`. This installs the integration, provisions the resource (e.g. `supabase-gray-umbrella`), connects it to the linked project, AND auto-runs `env pull` (writes `.env.local`, development env) — unless you pass `--no-env-pull` / `--no-connect`. So for a **single app there is NO separate `vercel env pull` step.** (`-m region=…` sets the region; `sfo1` = SF.)
2. **First-time terms gate — one-time per TEAM, not per project.** With an agent detected the command runs `--non-interactive`; if Tony hasn't accepted the integration's terms yet it returns **exit 0** with a clean JSON `action_required` payload — a `verification_uri` to click plus a `next[]` retry command. Print the URL, ask Tony to accept, then run the retry (fully idempotent). This fires only the FIRST time Supabase is added on the team; later sunrises skip it entirely. Do NOT report it as a failure. **While Tony accepts, don't idle** — proceed with the deploy check (Phase 8 step 1; a default build is green with no DB env) and the DB-independent phases (Notion, vault, memory), then finish the DB on the retry.
3. **Database name MUST match the project: `<slug>-db`.** The Marketplace auto-generates a junk name (`supabase-gray-umbrella` style) that later reads as cruft — RJ-Hauler's DB sat unidentifiable as `supabase-yellow-island` until 2026-08-14. If the provisioning command accepts a resource name, pass `<slug>-db` up front; otherwise, immediately after provisioning, rename the project to `<slug>-db` (Supabase dashboard → Project Settings → General — the Supabase MCP has no rename tool, so if no API path works, hand Tony the exact click path and treat the phase as incomplete until he confirms). Never leave an auto-generated name in place.
4. **Monorepo / Electron only:** the auto-pull lands at the repo root, so re-pull to the app-scoped path: `npx vercel env pull apps/<app>/.env.local` (Project Knight uses `apps/desktop/.env.local`).
5. Confirm `.env.local` is non-empty (~17 keys incl. `POSTGRES_URL` / `DATABASE_URL`) and gitignored. If the pull is empty or the resource didn't connect, STOP and tell Tony rather than continuing with a dead DB.

## Phase 5 — Notion task board (mirror of Project Knight)  [skip if --no-notion]

Provision the project's Notion task tracker + roadmap, faithfully mirroring the
Project Knight board (the reference setup; full schema in the Templates section
below). This is the one layer that is **archetype-independent** — it is project
management, not stack infrastructure, so it runs for every archetype unless
`--no-notion`. Uses the connected Notion MCP; if that MCP is absent (e.g. a
headless/cron run where the claude.ai connector is not available), skip and tell
Tony rather than failing the run. Requires Tony's Notion Plus plan (API tooling
needs it; already true for the Project Knight integration).

1. **Create the project parent page.** A top-level Notion page titled `<Project Name>` (optionally with an emoji icon, like Knight's ⚔️). The two DBs live inside it, mirroring the "⚔️ Project Knight" parent. Use the Notion MCP `create-pages` tool.
2. **Create the Roadmap database first** (the Task Tracker relates to it). Properties per the schema below: `Item` (title), `Status` (select: Backlog/Planned/In progress/Testing/Launched — declare the options IN THAT ORDER; option order is what drives the board column order, no extra config), `Priority` (select: High/Medium/Low), `Type` (select: Feature/Improvement/Bug Fix/Polish). Use `create-database`, and **grab the returned `data_source_id` (`collection://…`)** — the Task Tracker references it.
3. **Create the Task Tracker database, relation inline.** Properties: `Task name` (title), `Status` (**status** type — a plain `Status` yields Notion's default options Not started / In progress / Done, exactly the spec), `Done` (checkbox), `Due date` (date), `Priority` (select: High/Medium/Low), and `Roadmap` as `RELATION('<roadmap_data_source_id>', DUAL 'Tasks')`. The `DUAL` form creates BOTH sides in one shot — the reverse `Tasks` relation appears on Roadmap automatically. Use `create-database`; no separate relation step needed.
4. **Views are mostly free.** Task Tracker's default Table view already satisfies "a sortable table" — no view creation needed there. For Roadmap, add one Board view grouped by `Status` (`create-view`); its columns already follow the option order from step 2.
5. **Print the two manual automations** (Notion does NOT expose Automations via the API, so Tony sets these once in the Notion UI on the Task Tracker DB). Give him the exact steps:
   - "When `Done` is checked → set `Status` = Done."
   - "When `Status` is set to Not started or In progress → uncheck `Done`."
   - (Optional third: "When `Status` is set to Done → check `Done`.")
   These keep the checkbox and Status in lock-step. Nothing breaks if they are skipped (a consumer can OR the two signals, per ADR 009), but the board reads cleaner with them.
6. **Capture the coordinates:** the parent page URL + both DB IDs (`tasksDbId`, `roadmapDbId`). Record them in the vault `_index.md` "Notion" section (Phase 6) and the repo `CLAUDE.md`. Do NOT wire app consumption by default — the board is a PM artifact. If this project's code will later read it (the Knight pattern: a PAT in Vercel env + an `identityRules.notion` shape), point Tony at ADR 009 in the Project Knight repo as the reference implementation.

**Status property — no fallback needed (tested 2026-06-01).** A plain `Status` property via `create-database` yields Notion's default options Not started / In progress / Done — exactly the Task Tracker spec. The select-fallback (create as select, convert in the UI) only matters if you ever need CUSTOM status options beyond those three defaults. Duplicating the Knight DBs (`duplicate-page`) stays an option, but building fresh is clean and avoids repointing relations.

## Phase 6 — Vault (on the map)

Tony invoking `/sunrise` is the explicit instruction the vault's AGENTS.md requires
before creating a project `_index.md`. Create the seed, then leave it for Tony /
future sessions to grow (the vault's "don't auto-update `_index.md`" rule applies
after creation).

1. `mkdir -p ~/ObsidianVault/03-projects/<slug>`
2. Write `03-projects/<slug>/_index.md` (seed template at the bottom): standard frontmatter (`created`, `source: claude-code`, `type: project-index`, `project: <slug>`, `status: active`, `tags`) + sections What this is / Tech stack / Repo (GitHub URL + local path + branch) / Notion / Status. Fill in the real URLs and IDs from Phases 2-5 (including the Notion DB IDs).
3. Edit root `~/ObsidianVault/_index.md`: add ONLY the new project under "## Active projects" linking to `03-projects/<slug>/_index`. Do NOT auto-repair other stale entries — adding `[[…/_index]]` links to folders you haven't verified creates broken wikilinks. Only repair another entry after confirming its folder exists (`ls ~/ObsidianVault/03-projects/<name>`); otherwise leave it.

Note (contract since 2026-08-09): the vault folder is a home for durable project
knowledge (research, decisions, specs), not a state mirror. The `_index.md` seed is
a pointer — repo location, what it is, what's in the folder. Current status lives in
the repo and auto-memory; there is no obligation to keep `_index.md` current, and
there is no "Known projects" line in the vault's AGENTS.md to update.

## Phase 7 — CLI / Claude Code memory

1. **Home summary note:** write `~/.claude/projects/-Users-tonycoon/memory/project_<slug_>.md` with memory frontmatter (`name: <slug>`, a one-line `description`, `metadata: { type: project }`) and a short body: what it is (Tony's one-liner) + pointers to the repo `CLAUDE.md` (canonical detail) and the vault folder (durable notes). Mirror the shape of `project_knight.md`.
2. Add a one-line entry to that store's `MEMORY.md` under the active list: `- [<Project>](project_<slug_>.md) — <hook>`.
3. **The project's own per-directory memory store** auto-creates the first time Claude Code runs in `~/Developer/<Name>` — nothing to pre-create. (This is the inverse of sunset archiving that store.)

## Phase 8 — Closeout (the certificate of occupancy)

1. **Prove it's live — verify the CLEAN production alias, not the deploy-hash URL.** New Vercel projects ship with Deployment Protection ON, so the deploy-hash URL `vercel --prod` prints (`<project>-<hash>-<team>.vercel.app`) and the team alias both return **401** — that's expected protection, NOT a failed deploy. The clean production alias `https://<project>.vercel.app` returns **200**. So: deploy (`npx vercel --prod`, or confirm the Phase 2 git-connect auto-deploy), then `curl -sI https://<project>.vercel.app` and treat **200 on the clean alias** as green; treat 401 on hash/team URLs as expected. If the clean alias isn't reserved, derive the prod alias from `npx vercel ls <project> --prod` / `npx vercel inspect` instead of curling the deploy output. For an Electron env-plane, "live" = the no-op build succeeded. If `--no-vercel`, skip; the green bar is the local scaffold running.
2. **Print the summary + revisit recipe:**

   ```
   SUNRISE COMPLETE — <project>     "<Tony's one-line>"
     Repo     -> ~/Developer/<Name> (git init, pushed)
     GitHub   -> tiny-tunnel-dot/<repo> (private)
     Vercel   -> linked, auto-deploys on; live: <url> (200)
     Database -> <provider> via Vercel Marketplace; .env.local pulled
     Notion   -> Task Tracker + Roadmap board (mirror of Knight); IDs in _index
     Vault    -> 03-projects/<slug>/ (status: active), on the index
     Memory   -> project_<slug_>.md created + indexed

   To start building: open ~/Developer/<Name> and say "continue on <project>".
   CLAUDE.md will auto-load; durable notes live in the vault project folder.
   ```

3. **Generate the browser/app LLM handoff prompt.** Sunrising in Claude Code does not inform Tony's other LLM surfaces (claude.ai web, the desktop app, ChatGPT, Codex). Fill in the variables and print this in a fenced block for Tony to copy-paste (template at the bottom).

4. Offer to open the repo and kick off the first build session.

---

## Templates

### Vault seed `03-projects/<slug>/_index.md`

```markdown
---
created: <today>
source: claude-code
type: project-index
project: <slug>
status: active
tags: [project-index, <slug>]
---

# <Project Name>
Created: <today>

> Pointer + durable notes, not a state mirror. Current status lives in the repo
> and auto-memory. Add research, decisions, and specs to this folder as they earn
> a place.

## What this is
<Tony's one-line description.>

## Tech stack
<archetype + scaffolded stack>

## Repo
- **GitHub:** github.com/tiny-tunnel-dot/<repo>
- **Local path:** ~/Developer/<Name>
- **Branch:** main
- **Vercel:** <project url, or "env-plane only" / "none">
- **Database:** <provider> via Vercel Marketplace (or "none")

## Notion
- **Board:** <parent page URL> (mirror of the Project Knight setup)
- **Task Tracker DB:** <tasksDbId>
- **Roadmap DB:** <roadmapDbId>
- Done↔Status automations: <set up / pending> (see ADR 009 pattern)

## Notes in this folder
None yet — scaffolded via /sunrise on <today>. Add durable docs here and list them.
```

### Repo `CLAUDE.md` (boot doc)

```markdown
# <Project Name>

## What this is
<Tony's one-line description.>

## Stack
<archetype + scaffolded stack>

## Current state
Scaffolded <today> via /sunrise. Green baseline.

## Where to look
- Durable notes (research, decisions, specs): vault `~/ObsidianVault/03-projects/<slug>/`
- Architecture decisions: `docs/decisions/` (add ADRs as the design shifts)

## Workflow
- Feature branches + PRs. Never push to `main`.
- Merge via the GitHub PR web UI or terminal, never GitHub Desktop.
- Local: ~/Developer/<Name>   Run: <dev command>
- Env: `vercel env pull` writes .env.local (gitignored).

## End-of-session protocol
Nothing automatic — no session wraps or build logs (vault contract, 2026-08-09).
If a session produced something durable (a decision, research, a spec) and Tony
wants it kept, write it as a reference note in the vault project folder.
```

### Repo `AGENTS.md` (stub)

```markdown
# AGENTS.md

The canonical agent file for this repo is **`CLAUDE.md`** in the same directory.
This stub exists for tools that look for `AGENTS.md`. Read `CLAUDE.md`.
```

### Memory home note `project_<slug_>.md`

```markdown
---
name: <slug>
description: <one-line: what it is + stack + ~/Developer/<Name>>
metadata:
  type: project
---

<Tony's one-line description.> <archetype + stack>. Repo at `~/Developer/<Name>`.

Canonical detail (read before substantive work):
- Repo `CLAUDE.md` (boot doc + invariants).
- Vault `03-projects/<slug>/` (durable notes: research, decisions, specs).
```

### Browser/app LLM handoff prompt

```
Heads up: I have started (sunrised) a new project "<Project Name>" as of <today>.
What it is: <Tony's one-line description>.

It is now set up across all my systems:
- Local repo: ~/Developer/<Name>
- GitHub: tiny-tunnel-dot/<repo> (private)
- Vercel: linked, auto-deploys on (live: <url>)
- Database: <provider> via Vercel Marketplace
- Notion: Task Tracker + Roadmap board (mirror of Project Knight)
- Obsidian vault: 03-projects/<slug>/ (status: active)

Going forward, treat "<Project Name>" as an active project: you can suggest work
on it and include it in active-project lists. If you can reach my Obsidian vault,
its durable notes live under 03-projects/<slug>/ (current status lives in the
repo, not the vault). If you keep saved Projects or spaces, add one for it.
Acknowledge and update accordingly.
```

### Notion board schema (mirror of Project Knight)

The reference setup is the "⚔️ Project Knight" parent page with two related
databases. Reproduce this exactly (colors included — they carry the board read).

**Task Tracker** (database)

| Property | Type | Options |
|---|---|---|
| `Task name` | title | — |
| `Status` | status | Not started (to-do) · In progress / blue · Done / green |
| `Done` | checkbox | — |
| `Due date` | date | — |
| `Priority` | select | High / red · Medium / yellow · Low / green |
| `Roadmap` | relation | → Roadmap DB (reverse auto-creates `Tasks` on Roadmap) |

Default view: Table, sortable on Done / Task name / Due date / Status / Priority.

**Roadmap** (database)

| Property | Type | Options |
|---|---|---|
| `Item` | title | — |
| `Status` | select | Backlog / gray · Planned / blue · In progress / orange · Testing / yellow · Launched / green |
| `Priority` | select | High / red · Medium / yellow · Low / green |
| `Type` | select | Feature / green · Improvement / blue · Bug Fix / red · Polish / pink |
| `Tasks` | relation | → Task Tracker DB (reverse of `Roadmap`) |

Default view: Board grouped by `Status`, column order Backlog → Planned → In progress → Testing → Launched.

**Two manual automations** (Task Tracker, set in the Notion UI — not API-creatable):
1. When `Done` is checked → `Status` = Done.
2. When `Status` is set to Not started or In progress → uncheck `Done`.
   (Optional third: When `Status` = Done → check `Done`.)

Prereq: Notion Plus plan (API tooling requires it). See ADR 009 in the Project
Knight repo for the full rationale and the app-consumption pattern.
