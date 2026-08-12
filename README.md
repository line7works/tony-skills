# tony-skills

A private repo holding what Tony builds on his workstations and wants to keep —
Claude Code skills and subagents, plus standalone tools, configs, and specs.

## What's here

The test for belonging here is "was this made on one of these Macs and should it
outlive the machine," not "is it a Claude Code skill." Two parts, split by how a
thing is consumed rather than what it is:

- a **plugin marketplace** under `plugins/` (seven Claude Code plugin folders,
  five of them catalogued in `marketplace.json`) — what Claude Code installs
  and runs
- a **[Tony Tools](tools/)** category under `tools/` — everything else: macOS
  automations, dotfiles, scripts, and implementation specs for code that lives
  elsewhere

### Plugins

Seven plugin folders. Five are catalogued in `.claude-plugin/marketplace.json`
and installable with `/plugin`; `shutdown` and `arcade` are in the tree but not
yet catalogued.

**`sun`** provides two slash commands:

- `/sunrise` stands up a new project across every layer (local repo, GitHub, Vercel, database, Notion board, Obsidian vault, CLI memory) and proves it live, then emits a handoff prompt for other LLMs.
- `/sunset` archives an abandoned project reversibly across every layer (vault, memory, scheduled agents, repo, GitHub, Vercel, database, Notion), then emits a handoff prompt.

They share a set of cosmetic "sun cue" assets (sounds plus terminal and browser animations) bundled in `plugins/sun/assets/`.

**`clerk`** bundles one subagent, `clerk-auditor` (Clerk): a portable, strictly read-only auditor. Point it at any pile of files, repos, or notes ("audit ~/Downloads", "what's stale under ~/Developer", "reconcile my projects") and it surveys the target, changes nothing, and hands back a prioritized cleanup "punch list." It lives in this repo so every machine pulls the same Clerk instead of a laptop-only copy.

**`forge`** is a Claude-driven, model-agnostic image generator on Fal.ai. The `/forge` skill is the "foreman" (writes prompts, generates drafts, inspects them with vision, fixes misses, renders finished on-brand images); a dependency-free Python CLI (`plugins/forge/assets/forge.py`) does the mechanical work against Fal's REST queue. It is model-agnostic (nano-banana, GPT Image 2, FLUX, swappable per `--model`): single prompts or shot-list batches, a `compare` that races models, `edit` and `style` for existing images, `finish` for higher-quality keepers, `--transparent` cut-outs, and `export` to size presets, all under a running cost cap with an auditable run manifest. It reads `FAL_KEY` from the environment for live renders and auto-loads a per-project `.forge/brand.json`. Not for pixel-art sprites (PixelLab handles those).

**`wargame`** provides one slash command:

- `/wargame <target>` runs an adversarial pre-mortem — plan or stress-test anything assuming the happy path is a lie. It auto-detects the terrain (GREENFIELD new project / EXISTING code / planned CHANGE), ranks failure modes by likelihood × blast radius, and forces every high-ranked one to convert into a verified code check, a named test, or a spike ("anti-theater rule"). Output is one canonical doc (`docs/wargames/<slug>.md` in a repo) plus plain-language decision questions in chat. Hard floor: Opus-class models or better — it refuses to run on smaller models rather than produce a shallow war game.

**`signoff`** provides one slash command:

- `/signoff` runs an independent adversarial review of freshly built work and ends in a signed verdict. It is the back half of `/wargame`: war game before building, sign-off after. It auto-detects what was built (working diff, branch diff, or a named slice), finds the phase/slice doc and treats it as acceptance criteria, then spawns fresh reviewers who did **not** write the code and never receive the author's rationale — with a mandate to reject rather than bless. Lean by default (three lenses: spec conformance, correctness, seams against shipped code); DEEP adds security and test-quality. Findings need `file:line` plus a concrete failure scenario or they get cut, and blockers are re-verified against source before reporting. Output is a compact chat verdict — SIGNED OFF / WITH CONDITIONS / REJECTED — plus a punch list and a "tried and failed to break" line, so a clean review can't hide behind "looks good." Report-only; it never fixes what it finds. Shares wargame's Opus-class floor.

**`shutdown`** provides `/shutdown` — settle up before restarting Terminal or
switching accounts: verify and report git state read-only, write a self-contained
handoff to `~/Documents/handoffs/`, and save a memory pointer so the next session
finds it. `/shutdown all` sweeps every open terminal session on the same machine.
Not catalogued in `marketplace.json`, and unlike the others it carries no
`.claude-plugin/plugin.json` — only `skills/shutdown/SKILL.md`.

**`arcade`** bundles the `arcade-publish` CLI (`plugins/arcade/assets/`), which
publishes, updates, reorders, and takes down pages on the Line 7 Arcade
(`arcade.line7.works`) from the terminal. The `/arcade` skill that drives it is
not built yet — see `docs/arcade-skill-build-plan.md`. Not catalogued in
`marketplace.json` until that skill lands. Writes to live production.

### Tony Tools

Everything preserved here that Claude Code does **not** install, so it lives
under `tools/` (not `plugins/`) and is not in the marketplace catalog. That
covers things you copy onto a Mac directly (macOS automations, dotfiles,
scripts) and also implementation specs for code that lives somewhere else. See
[`tools/README.md`](tools/) for the category.

Currently four:

- **`gmail-mcp/`** — a multi-account Gmail MCP server, registered with Claude
  Code as `gmail`. Reaches every authorized inbox at once by alias, which the
  claude.ai Google connector cannot do: it holds one OAuth grant, so connecting
  a second Gmail replaces the first. Real source and installable, unlike the
  spec below. Runs from this checkout rather than a copy, so `git pull` updates
  it. Secrets live in `~/.gmail-mcp/`, never here.
- **`antigravity-mcp/`** — an MCP server wrapping Google Antigravity's `agy`
  CLI, so a Claude Code session can consult Gemini Pro the way it consults
  Codex. Needed because `agy` consumes MCP servers but does not serve as one.
  Real source, installable; registers as `antigravity`.
- **`mcp-obsidian-worker/`** — the implementation spec for the Cloudflare Worker
  serving the `Obsidian Vault` MCP server on claude.ai web. Spec only; the
  Worker source is not in this repo.
- **`arcade-publish/`** — the findings ledger (`punch-list.md`) for the
  arcade-publish CLI, and a pointer README. The code moved to
  `plugins/arcade/assets/` on 2026-08-12; the ledger deliberately stayed behind
  as the single consolidated list. The one entry here that is documentation
  rather than a runnable thing.

(`copy-on-select` was sunset 2026-07-21 and is still in git history.)

## Layout

```
tony-skills/
├── .claude-plugin/marketplace.json   catalog (lists sun, clerk, forge, wargame, signoff — not shutdown or arcade)
├── docs/                             build plans and their punch lists
├── plugins/                          Claude Code plugins (installed via /plugin)
│   ├── sun/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/
│   │   │   ├── sunrise/SKILL.md
│   │   │   └── sunset/SKILL.md
│   │   └── assets/                    rise.wav, set.wav, sun_bar.py, sun.html, ...
│   ├── clerk/
│   │   ├── .claude-plugin/plugin.json
│   │   └── agents/clerk-auditor.md
│   ├── forge/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/forge/SKILL.md
│   │   ├── assets/                    forge.py, models.json
│   │   └── IMPLEMENTATION.md          full spec + per-milestone build log
│   ├── wargame/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/wargame/SKILL.md
│   ├── signoff/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/signoff/SKILL.md
│   ├── shutdown/                     not in the catalog; no plugin.json
│   │   └── skills/shutdown/SKILL.md
│   └── arcade/                       not in the catalog until /arcade lands
│       ├── .claude-plugin/plugin.json
│       └── assets/                   arcade-publish (CLI), README.md
└── tools/                            preserved work Claude Code doesn't install
    ├── README.md
    ├── gmail-mcp/                    multi-account Gmail MCP server (real source)
    │   ├── README.md
    │   ├── src/                      store.ts, auth.ts, gmail.ts, server.ts
    │   ├── package.json
    │   └── tsconfig.json
    ├── antigravity-mcp/              MCP bridge to Google Antigravity's agy CLI
    ├── arcade-publish/               findings ledger + pointer (code lives in plugins/arcade/)
    │   ├── README.md
    │   └── punch-list.md
    └── mcp-obsidian-worker/          spec for the claude.ai Obsidian MCP Worker
        ├── README.md
        └── IMPLEMENTATION.md
```

There are two ways to install from this repo. Pick by whether you want clean
managed updates (plugin) or the bare `/sunrise` / `/sunset` / `/forge` / `/wargame` / `/signoff` commands (user-level).

## Install as a plugin (namespaced, shareable)

```
/plugin marketplace add tiny-tunnel-dot/tony-skills
/plugin install sun@tony-skills
/plugin install clerk@tony-skills
/plugin install forge@tony-skills
/plugin install wargame@tony-skills
/plugin install signoff@tony-skills
```

Restart Claude Code once. The `sun` commands register as `/sun:sunrise` and `/sun:sunset`, wargame as `/wargame:wargame`, and signoff as `/signoff:signoff`. Plugin skills are always namespaced by the plugin name, so there is no bare form in this mode. This is the mode to use when sharing with someone else.

`clerk` ships a subagent rather than a slash command, so there is nothing to type. Once installed it shows up as the `clerk-auditor` agent type and triggers on audit-style asks ("audit X", "what's stale", "reconcile", "give me a report on X"). Clerk can also run user-level instead of as a plugin, and Tony's machines use that route — see [Clerk: user-level vs plugin](#clerk-user-level-vs-plugin-pick-one-route-per-machine) below. Pick one route per machine; the `clerk@tony-skills` line above is only for the plugin route.

`forge` registers the `/forge` skill (namespaced `/forge:forge` in plugin mode), which triggers on image-generation asks ("make an image of X", "generate icons for Commish"). It shells out to its bundled `assets/forge.py`, so the only requirement is `python3` (3.8+, standard library only) plus a `FAL_KEY` in the environment for live renders. `estimate`, `models`, and any `--dry-run` work with no key.

Because the repo is private, the installing machine needs working git auth (the `gh` login or an SSH key), which Tony's machines already have.

### Clerk: user-level vs plugin (pick one route per machine)

Clerk is an agent, not a slash command, so it can be consumed two ways. **Pick one route per machine — never both, or the agent name `clerk-auditor` is defined twice and the two definitions collide.**

- **User-level (the route Tony runs).** Copy the agent file into `~/.claude/agents/`. This matches how `sun` is installed on his machines and needs no `/plugin` commands:

  ```bash
  cd ~/Developer/tony-skills && git pull
  cp plugins/clerk/agents/clerk-auditor.md ~/.claude/agents/clerk-auditor.md
  ```

  Restart Claude Code once. To pull a later change to Clerk, re-run those two lines. Skip the `/plugin install clerk@tony-skills` step above when using this route.

- **Plugin (managed updates).** Use `/plugin install clerk@tony-skills` (above) and update with `/plugin update clerk@tony-skills`. If that machine was previously on the user-level route, remove the copy first so the two don't collide:

  ```bash
  rm ~/.claude/agents/clerk-auditor.md
  ```

The agent's memory at `~/.claude/agent-memory/clerk-auditor/` is machine-local on either route and stays put; each machine keeps its own audit history.

## Install for bare commands (`/sunrise`, `/sunset`, `/forge`, `/wargame`, `/signoff`)

Prefer the bare command names? Install them as user-level skills instead of as a plugin. Copy the skill folders (plus sun's shared assets) into `~/.claude/skills/`; forge follows the same pattern in its subsection below:

```bash
mkdir -p ~/.claude/skills
cp -R ~/Developer/tony-skills/plugins/sun/skills/sunrise      ~/.claude/skills/sunrise
cp -R ~/Developer/tony-skills/plugins/sun/skills/sunset       ~/.claude/skills/sunset
cp -R ~/Developer/tony-skills/plugins/sun/assets              ~/.claude/skills/sunset/assets
cp -R ~/Developer/tony-skills/plugins/wargame/skills/wargame  ~/.claude/skills/wargame
cp -R ~/Developer/tony-skills/plugins/signoff/skills/signoff  ~/.claude/skills/signoff
```

Restart Claude Code once. You get bare `/sunrise`, `/sunset`, `/wargame`, and `/signoff`. The asset paths are dual-mode, so the sun cue still fires in this mode (it falls back to `~/.claude/skills/sunset/assets`); wargame and signoff have no assets.

Trade-off versus the plugin: no `/plugin update`. To pull changes, `git pull` in `~/Developer/tony-skills` and re-run the `cp` lines.

### forge (user-level, the same pattern)

Copy forge's skill folder plus its `assets/` (the `forge.py` CLI and `models.json` registry) into `~/.claude/skills/forge/`:

```bash
mkdir -p ~/.claude/skills
cp -R ~/Developer/tony-skills/plugins/forge/skills/forge ~/.claude/skills/forge
cp -R ~/Developer/tony-skills/plugins/forge/assets       ~/.claude/skills/forge/assets
```

Restart Claude Code once and you get the bare `/forge`. The skill calls its CLI via `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/forge}/assets/forge.py`, so in user-level mode it resolves to the copy you just placed. Needs `python3` (3.8+) and a `FAL_KEY` in the environment for live renders (`estimate` / `models` / `--dry-run` need no key). To update on any machine: `git pull` in `~/Developer/tony-skills` and re-run the two `cp` lines.

## Updating

After editing a skill or the Clerk agent and pushing:

```
/plugin marketplace update tony-skills
/plugin update sun@tony-skills
/plugin update clerk@tony-skills
/plugin update forge@tony-skills
/plugin update wargame@tony-skills
/plugin update signoff@tony-skills
```

No version is pinned, so every pushed commit is the latest.

## A note on sharing

These skills are personal. They reference Tony's GitHub handle (`tiny-tunnel-dot`), his `~/Developer` layout, Project Knight, his Obsidian vault structure, and his Notion board pattern. Keep this repo private.

To share a skill publicly later, make a genericized copy in a fresh public repo (strip the personal paths and handles) rather than flipping this one public. Git history would otherwise expose those details even after a cleanup commit. (`wargame` and `signoff` are the exceptions — they contain no personal paths or handles, so they're the easy candidates to copy out as-is if sharing ever comes up.)

## Assets and the plugin root (dual-mode)

The skills play a cosmetic sound and terminal animation on launch. The asset paths use `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sunset}/assets/...`, which resolves both ways:

- **Plugin install:** `$CLAUDE_PLUGIN_ROOT` is set, so it points at the plugin's bundled `assets/`.
- **User-level install:** `$CLAUDE_PLUGIN_ROOT` is empty, so it falls back to `~/.claude/skills/sunset/assets/` (which the bare-command install populates).

The cue is best-effort and skips silently if anything is missing, so a path miss never breaks a run. Verify the cue fires after the first install in whichever mode you used.
