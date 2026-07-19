# tony-skills

A private repo holding Tony's personal Claude Code skills (a plugin
marketplace) plus a small set of machine-level tools.

## What's here

Two things: a **plugin marketplace** under `plugins/` (four Claude Code
plugins) and a **[Tony Tools](tools/)** category under `tools/` (machine-level
tools and configs that are not Claude Code skills).

### Plugins

Five plugins.

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

### Tony Tools

Machine-level tools and configs that are **not** Claude Code skills, so they
live under `tools/` (not `plugins/`) and are not in the marketplace catalog.
These are things you copy onto a Mac directly rather than installing through
Claude Code. See [`tools/README.md`](tools/) for the category. Current tools:

- **[copy-on-select](tools/copy-on-select/)** — system-wide highlight-to-clipboard
  on macOS via Hammerspoon. Select text with the mouse in almost any app (Mail,
  Chrome, iMessage, ...) and it is copied automatically, no `Cmd+C`.

## Layout

```
tony-skills/
├── .claude-plugin/marketplace.json   catalog (lists the sun, clerk, forge, wargame, and signoff plugins)
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
│   └── signoff/
│       ├── .claude-plugin/plugin.json
│       └── skills/signoff/SKILL.md
└── tools/                            machine-level tools, not Claude skills
    ├── README.md
    └── copy-on-select/
        ├── copy-on-select.lua
        └── README.md
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
