---
name: sunrise
description: >-
  Bootstrap ("sunrise") a new project Tony is ready to make real, across every
  layer at once: scaffold a local repo in ~/Developer by archetype (web app /
  monorepo / static / Electron / library / script), seed the repo doc kit's Tier 0
  (README, AGENTS.md as the instruction body, CLAUDE.md as a one-line `@AGENTS.md`
  stub, .gitignore, .env.example, docs/), adopt any scope or architecture docs
  staged in ~/Documents before the repo existed, create + push a private GitHub repo,
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
- **Ask what it is.** Always prompt Tony for a one-line "what is this / what are you building" and use his words in `_index.md`, `AGENTS.md`, the memory note, and the handoff prompt. (Mirror of sunset's "ask the reason.")
- **Layers are conditional on the archetype.** Don't run a gas line to a tool shed. Gate Vercel and the database per the matrix.
- **Get to green.** Don't hand back a half-wired skeleton. End on a verified push + a **200 on the clean `<project>.vercel.app` alias** + a populated `.env.local`.
- **Wire the cross-links from birth.** The repo `AGENTS.md` (the instruction body every host reads; `CLAUDE.md` is its one-line `@AGENTS.md` stub), the vault `_index.md`, and the memory note all point at each other on day one, so the boot path works immediately.
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
   - `afplay ${CLAUDE_PLUGIN_ROOT}/assets/rise.wav >/dev/null 2>&1 &`
   - `python3 ${CLAUDE_PLUGIN_ROOT}/assets/sun_bar.py rise`
   - Keep it to the **ONE-LINE** `sun_bar.py rise` output (gold→blue half-block bar, sun on the left, "☀ S U N R I S E"). Claude Code collapses taller output behind a "+N lines" fold and captures in-place ANSI animation as raw escape codes, so one line is the only reliable in-flow cue — do not attempt terminal motion. A richer browser animation exists (`open "file://${CLAUDE_PLUGIN_ROOT}/assets/sun.html#rise"`) but it pops a window, so use it only if Tony asks. If `afplay`/`python3` are unavailable, skip silently. (Assets are shared with `sunset`; do not rebuild them. The `${CLAUDE_PLUGIN_ROOT}/assets` form resolves to the plugin's bundled `assets/` at its install location.)

1. **Gather the inputs.**
   - **Name** (required). **Archetype** (the 6 above; default web app, single). **One-line "what is this."** **Visibility** (default private). **Database?** (archetype default; `--db`/`--no-db` override). **Promote an existing dir?** (`--promote <path>`).

2. **Derive the four name variants and show them for confirmation.** Tony's local-dir casing is inconsistent (`Helix`, `PGL`, `belgariad-codex`), so always confirm.
   - `<Name>` — repo + local dir under `~/Developer/` (spaces → hyphens; keep his casing).
   - `<slug>` — kebab-case, lowercase (vault folder + frontmatter `name` + handoff).
   - `<slug_>` — the slug with hyphens → underscores (memory filename only, matching existing `project_pour_guys.md` / `project_belgariad_codex.md`).
   - `<shortcut>` — the terminal shortcut he'll type to `cd` into the repo. **Propose a default, don't ask open-endedly:** the shortest unambiguous token from the name, 2–5 characters, lowercase, matching the existing set (`pk`, `haul`, `inky`, `pour`, `jpb`, `robo`, `smart`). Show it with the other three and let him override. If he wants none, accept that and skip the shortcut everywhere below.

3. **Collision check across all layers (never clobber).** Each must be clear, unless `--promote` points at it:
   - Local: `ls -d ~/Developer/*<Name>* 2>/dev/null`
   - GitHub: `gh repo view <owner>/<repo>` should 404 (`tiny-tunnel-dot` is the owner).
   - Vault: `ls -d ~/ObsidianVault/03-projects/<slug> 2>/dev/null`
   - Memory: `ls ~/.claude/projects/-Users-tonycoon/memory/project_<slug_>.md 2>/dev/null`
   - Vercel: Vercel MCP `list_projects` (or `npx vercel project ls`) — name must be free.
   - **Shortcut: `zsh -ic 'type -a <shortcut>' 2>/dev/null` must come back empty.** This is the one collision that bites silently — a token like `pr`, `gs`, or `ts` shadows a real binary and the breakage surfaces weeks later in an unrelated command. An existing alias, function, builtin, or anything on `PATH` all disqualify it. If taken, say what it collides with and propose the next candidate; never ship a shadowing shortcut.
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
   names: dir/repo <Name>  ·  slug <slug>  ·  memory project_<slug_>.md  ·  shortcut <shortcut>
   ──────────────────────────────────────────────────────────────────────
   Repo     mkdir ~/Developer/<Name>; scaffold <scaffolder>; git init
            seed Tier 0: README.md, AGENTS.md, CLAUDE.md, .gitignore,
            .env.example, docs/.gitkeep
   Docs     adopt staged: ~/Documents/<slug>-scope.md -> docs/scope/<YYYY-MM-DD>-<slug>.md
            (one line per staged doc found by the Phase 1 lookup, with its
            destination; "already adopted: <path>" for a doc an earlier run
            moved; or the single line "nothing staged")
   GitHub   create tiny-tunnel-dot/<repo> (private); push main
   Vercel   link project <Name> (auto-connects GitHub repo; auto-deploys on)
   Database vercel integration add supabase (auto-connect + auto-pull)
            -> .env.local (POSTGRES_URL + keys, ~17 vars)
   Notion   create page "<project>" + Task Tracker & Roadmap DBs
            (mirror Project Knight); record DB IDs in _index.md
   Vault    create 03-projects/<slug>/_index.md (seed, status: active)
            add to root _index.md "Active projects"
   Memory   create project_<slug_>.md + MEMORY.md line
   Shortcut append alias <shortcut> -> ~/Developer/<Name>
            to ~/.config/zsh/project-shortcuts.zsh (name is free)
   Verify   first deploy -> live URL, expect 200
   Output   handoff prompt to paste into a browser/app LLM
   ──────────────────────────────────────────────────────────────────────
   Nothing existing is touched. Reply "go" to execute, or tell me what to change.
   ```

   The `Docs` line comes from running Phase 1 step 5's lookup read-only here, both
   halves (already-adopted docs in the repo's `docs/` subfolders, then staged matches;
   list them, move nothing), so the seed set and every adoption are visible before
   anything is written, and a resumed run shows what an earlier run already moved. If `--dry-run`, stop here. Otherwise wait for an
   explicit "go" before Phase 1.

---

## Phase 1 — Local repo + scaffold (foundation and framing)

Dependencies run forward here (you can't hook utilities before the framing is
up), so the repo comes first.

1. `mkdir -p ~/Developer/<Name>` (or adopt the `--promote` path in place).
2. **Scaffold per archetype** using the matrix's default scaffolder (or Tony's override), non-interactively where possible. Two things current scaffolders do that you must expect:
   - **They init git themselves.** `create-next-app` ignores `--no-git` (use `--disable-git`, or just let it init) and prints "Initialized a git repository." So the dir may already be a git repo — possibly with a scaffold commit — before step 4.
   - **They pre-seed agent files.** `create-next-app` now ships its own `CLAUDE.md` (just `@AGENTS.md`) and `AGENTS.md` (with a `<!-- BEGIN:nextjs-agent-rules -->` block: "this is NOT the Next.js you know… read `node_modules/next/dist/docs/` before writing code"). Astro/Turbo may do the same. Do NOT blind-overwrite these — the "never clobber" rule applies.
3. **Seed Tier 0 of the repo doc kit** (templates at the bottom), MERGING with anything the scaffolder already wrote. The seed set is the kit's Tier 0 table in `~/ObsidianVault/01-domain/repo-doc-kit.md`; what goes in the instruction body follows `~/ObsidianVault/01-domain/agents-md-best-practices.md` (the spec sheet). Six files, nothing more: a file that does not earn its keep is rent paid every session, and `REVIEW.md` in particular is never seeded (`/signoff` creates it on its first run in the repo).
   - `AGENTS.md` — the instruction body, the one file every host reads (Claude Code, Codex, Cursor, Copilot). Shaped to the spec sheet's sections: commands, conventions, footguns, where to look, gates. If the scaffolder left an `AGENTS.md`, merge rather than overwrite: a framework block (`<!-- BEGIN:nextjs-agent-rules -->` … `<!-- END:nextjs-agent-rules -->`, or equivalent) stays at the top inside its markers, untouched, and the body goes below it so a future upgrade re-injects cleanly. It is real and load-bearing.
   - `CLAUDE.md` — the stub: the line `@AGENTS.md`, then a `## Claude Code specific` section only when Claude-only lines follow it (skills, hooks, plan-mode requests, `.claude/`, `@DESIGN.md`). Sunrise seeds none, so the seeded file is literally one line. A real file, never a symlink. A scaffolder's `CLAUDE.md` that is already `@AGENTS.md` is kept as is. A `CLAUDE.md` that carries real content (a `--promote`d dir sunrised before the flip, with its body in `CLAUDE.md` and a "read CLAUDE.md" stub in `AGENTS.md`; a scaffolder that ships one) is merged, never clobbered and never left as a second body: lift its content into `AGENTS.md` below any framework block, folding it into the template's sections where a line fits and keeping the rest verbatim under its own heading; drop the old `AGENTS.md` stub text; then rewrite `CLAUDE.md` to the one-line stub (plus a `## Claude Code specific` section for any line that was Claude-only). Show the merged `AGENTS.md` before writing it; nothing from the old body is lost, only moved.
   - `README.md` — name, one-liner, dev commands, links.
   - `.gitignore` — archetype-appropriate. **Then append `!.env.example`** so the example env is actually tracked: scaffolder `.gitignore`s use `.env*`, which silently swallows `.env.example`. Verify after the commit: `.env.example` tracked, `.env.local` still ignored.
   - `.env.example` — committed, keys present with no values.
   - `docs/.gitkeep` — an empty file so git tracks the empty `docs/` folder; the loop's paperwork lands in subfolders of `docs/` (`scope/`, `architecture/`, `plans/`, `reviews/`), each created by the first skill that writes there (or by step 5 below).
4. **Idempotent git init.** The scaffolder may have already `git init`'d (and committed), so: init only if not already a repo; ensure the default branch is `main`. Never assume a clean slate.
5. **Adopt staged docs.** Loop paperwork written before a repo existed sits in `~/Documents` (precon's and architect's pre-repo staging). First check the destinations for a doc a previous, interrupted run already adopted (`docs/scope/*-<slug>.md`, `docs/architecture/*-<slug>.md`, `docs/reviews/*-precon-cold-read-<slug>*.md`, `docs/reviews/*-architect-review-<slug>-*.md`): each hit is reported as `already adopted: <path>`, counts in the Phase 8 summary, and its staged source is not looked for again. Then look for exactly these, matched by the project's `<slug>`:
   - `~/Documents/<slug>-scope.md` → `docs/scope/<YYYY-MM-DD>-<slug>.md`
   - `~/Documents/<slug>-architecture.md` → `docs/architecture/<YYYY-MM-DD>-<slug>.md`
   - `~/Documents/precon-cold-reads/<slug>-cold-read-*.md` → `docs/reviews/<YYYY-MM-DD>-precon-cold-read-<slug>.md` (a same-day second file keeps a `-2`, `-3` suffix, matching precon's own naming)
   - `~/Documents/architect-reviews/<slug>-review-*.md` → `docs/reviews/<YYYY-MM-DD>-architect-review-<slug>-<lane>.md` (`<lane>` is the model tag the staged filename carries after the date, if any; a same-day repeat keeps its `-2`, `-3` suffix)

   The date is taken from the doc's own header (precon writes `# <idea> — scope doc (YYYY-MM-DD)`, architect writes the date in its title line); when the header carries none, the date in the staged filename; when neither has one, ask Tony. No match at all (and nothing already adopted): print `nothing staged` and continue. More than one candidate for one role (two scope docs, two architecture docs; or a set of cold reads or reviews): list every candidate with its proposed destination and ask Tony which move — never pick. Matches **move** (`mv`, not copy: staging holds loop paperwork only until sunrise runs), creating the destination subfolder on first use. Record what moved; the Phase 8 summary names it.
6. **First commit.** Stage everything (Tier 0, the scaffold, the adopted docs); commit. If there's nothing to commit because the scaffold already committed and nothing was adopted, that's fine — don't fail.

## Phase 2 — GitHub (the permit)  [skip if --no-github]

Create the remote, link it, and push in one shot:

1. `gh repo create tiny-tunnel-dot/<repo> --private --source=. --remote=origin --push` (`--public` if chosen).
2. **Confirm the branch rule** is in `AGENTS.md` (the seeded Gates section carries it): feature branches + PRs, never push to `main` (Tony's standing rule). Optionally add a GitHub ruleset requiring PRs via `gh api`; note that branch protection on Free private repos may be limited, so if it errors, leave it documented rather than failing the run.

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
6. **Capture the coordinates:** the parent page URL + both DB IDs (`tasksDbId`, `roadmapDbId`). Record them in the vault `_index.md` "Notion" section (Phase 6) and the repo `AGENTS.md` ("Where to look"). Do NOT wire app consumption by default — the board is a PM artifact. If this project's code will later read it (the Knight pattern: a PAT in Vercel env + an `identityRules.notion` shape), point Tony at ADR 009 in the Project Knight repo as the reference implementation.

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

## Phase 7 — CLI / Claude Code memory + terminal shortcut

### 7a — Terminal shortcut

The shortcut file is `~/.config/zsh/project-shortcuts.zsh`, sourced from `~/.zshrc`.
**Never edit `~/.zshrc` itself** — it holds PATH exports and a live API key, and blind
appends land below them. Sunrise owns only the sourced file.

1. Confirm the file is wired up: `grep -q project-shortcuts ~/.zshrc && test -f ~/.config/zsh/project-shortcuts.zsh`. If either is missing you are on a machine that hasn't been migrated (the laptop, most likely) — say so and skip 7a rather than recreating the file blind.
2. Append exactly one line, in this shape and no other — sunset matches on the `cd` target:
   ```bash
   printf 'alias %s="cd ~/Developer/%s"\n' "<shortcut>" "<Name>" >> ~/.config/zsh/project-shortcuts.zsh
   ```
3. **Verify it loads in a fresh shell, not this one:** `zsh -ic 'alias <shortcut>'` must print the new line. The alias is dead in the running shell until Tony reloads — that's expected, and Phase 8 tells him.

### 7b — Memory

1. **Home summary note:** write `~/.claude/projects/-Users-tonycoon/memory/project_<slug_>.md` with memory frontmatter (`name: <slug>`, a one-line `description`, `metadata: { type: project }`) and a short body: what it is (Tony's one-liner) + pointers to the repo `AGENTS.md` (canonical detail) and the vault folder (durable notes). Mirror the shape of `project_knight.md`.
2. Add a one-line entry to that store's `MEMORY.md` under the active list: `- [<Project>](project_<slug_>.md) — <hook>`.
3. **The project's own per-directory memory store** auto-creates the first time Claude Code runs in `~/Developer/<Name>` — nothing to pre-create. (This is the inverse of sunset archiving that store.)

## Phase 8 — Closeout (the certificate of occupancy)

1. **Prove it's live — verify the CLEAN production alias, not the deploy-hash URL.** New Vercel projects ship with Deployment Protection ON, so the deploy-hash URL `vercel --prod` prints (`<project>-<hash>-<team>.vercel.app`) and the team alias both return **401** — that's expected protection, NOT a failed deploy. The clean production alias `https://<project>.vercel.app` returns **200**. So: deploy (`npx vercel --prod`, or confirm the Phase 2 git-connect auto-deploy), then `curl -sI https://<project>.vercel.app` and treat **200 on the clean alias** as green; treat 401 on hash/team URLs as expected. If the clean alias isn't reserved, derive the prod alias from `npx vercel ls <project> --prod` / `npx vercel inspect` instead of curling the deploy output. For an Electron env-plane, "live" = the no-op build succeeded. If `--no-vercel`, skip; the green bar is the local scaffold running.

   **Then verify the repo against the kit**, in the new repo's root (the kit note's own four lines, "Verifying a repo against the kit"):

   ```bash
   git ls-files | grep -qx AGENTS.md && echo "AGENTS.md tracked, exact case"
   [ "$(head -1 CLAUDE.md)" = "@AGENTS.md" ] && echo "stub imports the body"
   [ ! -L CLAUDE.md ] && echo "stub is a real file"
   claude -p "Quote verbatim the first line of the project instructions you were given"
   ```

   The first three are yes/no. The fourth is the canary: the line it quotes from `AGENTS.md` must be the file's first line of content, which is line 1 of `AGENTS.md`, or, where the scaffolder left a framework block on line 1, the block's first prose line (the HTML comment marker `<!-- BEGIN:nextjs-agent-rules -->` is not content and a model will not quote it; verified 2026-09-04: a Next.js render answered "This is NOT the Next.js you know…"). The answer may also quote the stub's own `@AGENTS.md` line first; that is the mechanism, not a mismatch. A model saying "yes, I have it" is not evidence; only the quoted line is. Any line that fails is a failed baseline: report it exactly like a failed deploy, fix the file (case in the git index; a stub that is not `@AGENTS.md` goes through Phase 1 step 3's merge rule, never a bare overwrite; a symlink becomes a real file), rerun, and do not print `SUNRISE COMPLETE` until all four pass.
2. **Print the summary + revisit recipe:**

   ```
   SUNRISE COMPLETE — <project>     "<Tony's one-line>"
     Repo     -> ~/Developer/<Name> (git init, pushed); kit check 4/4
     Docs     -> adopted: <each moved doc's new path; "already adopted" for docs an
                 earlier run moved; or "nothing staged">
     GitHub   -> tiny-tunnel-dot/<repo> (private)
     Vercel   -> linked, auto-deploys on; live: <url> (200)
     Database -> <provider> via Vercel Marketplace; .env.local pulled
     Notion   -> Task Tracker + Roadmap board (mirror of Knight); IDs in _index
     Vault    -> 03-projects/<slug>/ (status: active), on the index
     Memory   -> project_<slug_>.md created + indexed
     Shortcut -> `<shortcut>` -> ~/Developer/<Name>

   To start building: run `source ~/.zshrc` (or open a new terminal tab), then
   type `<shortcut>` and say "continue on <project>". AGENTS.md loads through
   the CLAUDE.md stub; durable notes live in the vault project folder.
   ```

   The `source ~/.zshrc` line is not optional boilerplate — the new alias does
   not exist in any shell that was already open, so without it the shortcut
   looks broken on first use.

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
- **Terminal shortcut:** `<shortcut>`
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

### Repo `AGENTS.md` (the instruction body)

The one file every host reads. Sections per the spec sheet; one plain declarative
line per rule; plain relative paths to deeper docs, never `@import` syntax (only the
stub may import). Where the scaffolder left a framework block, it stays above this,
inside its markers. A `<...>` placeholder is filled from the run or the line is cut;
the empty-section placeholders stay as one line each until a real entry earns its
place (add on the second failure, per the spec sheet).

```markdown
# <Project Name>
<!-- verified: <today> -->

<Tony's one-line description.> <archetype + scaffolded stack>. Scaffolded <today>
via /sunrise; green baseline.

## Commands
- Run: `<dev command>`
- Build: `<build command>` · Typecheck: `<typecheck command>`
- Test one file: `<single-test command>` (not the whole suite)
- Env: <`vercel env pull` writes `.env.local` (gitignored) when Vercel is linked, with the
  app-scoped path for a monorepo or Electron app (Phase 4 step 4); with no Vercel layer,
  "copy `.env.example` to `.env.local` and fill it"; the run picks one>; `.env.example`
  lists the keys

## Conventions that differ from defaults
- <a scaffolder convention an agent's default would get wrong, or leave this one line
  until the second failure>

## Footguns
- <a thing that breaks silently in this repo, or leave this one line until the second
  failure>

## Where to look
- Loop paperwork: `docs/scope/` (scope docs), `docs/architecture/` (architecture docs),
  `docs/plans/` (build docs), `docs/reviews/` (verdicts)
- Durable notes (research, decisions, specs): vault `~/ObsidianVault/03-projects/<slug>/`
- Notion board: <parent page URL> (Task Tracker + Roadmap; IDs in the vault `_index.md`)

## Gates
- Feature branches + PRs. Never push to `main`.
- Merge via the GitHub PR web UI or terminal, never GitHub Desktop.
- End of session: nothing automatic, no session wraps or build logs (vault contract,
  2026-08-09). Something durable (a decision, research, a spec) Tony wants kept is
  written as a reference note in the vault project folder.
```

### Repo `CLAUDE.md` (the stub)

Exactly this, one line, with a trailing newline. A real file, never a symlink.

```markdown
@AGENTS.md
```

Only when a Claude-only line exists to put under it (a skill or hook reference, a
plan-mode request, anything about `.claude/`, an `@DESIGN.md` import) does the file
grow a second part, and only then:

```markdown
@AGENTS.md

## Claude Code specific
- <the Claude-only line>
```

Sunrise seeds no Claude-only lines, so the seeded stub is the one-line form.

### Memory home note `project_<slug_>.md`

```markdown
---
name: <slug>
description: <one-line: what it is + stack + ~/Developer/<Name>>
metadata:
  type: project
---

<Tony's one-line description.> <archetype + stack>. Repo at `~/Developer/<Name>`,
terminal shortcut `<shortcut>`.

Canonical detail (read before substantive work):
- Repo `AGENTS.md` (the instruction body: commands, footguns, gates; `CLAUDE.md` is its `@AGENTS.md` stub).
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
