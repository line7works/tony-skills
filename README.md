# tony-skills

A private Claude Code plugin marketplace holding Tony's personal skills.

## What's here

One plugin, `sun`, providing two slash commands:

- `/sunrise` stands up a new project across every layer (local repo, GitHub, Vercel, database, Notion board, Obsidian vault, CLI memory) and proves it live, then emits a handoff prompt for other LLMs.
- `/sunset` archives an abandoned project reversibly across every layer (vault, memory, scheduled agents, repo, GitHub, Vercel, database, Notion), then emits a handoff prompt.

They share a set of cosmetic "sun cue" assets (sounds plus terminal and browser animations) bundled in `plugins/sun/assets/`.

## Layout

```
tony-skills/
├── .claude-plugin/marketplace.json   catalog (lists the "sun" plugin)
└── plugins/
    └── sun/
        ├── .claude-plugin/plugin.json
        ├── skills/
        │   ├── sunrise/SKILL.md
        │   └── sunset/SKILL.md
        └── assets/                    rise.wav, set.wav, sun_bar.py, sun.html, ...
```

There are two ways to install from this repo. Pick by whether you want clean
managed updates (plugin) or the bare `/sunrise` / `/sunset` commands (user-level).

## Install as a plugin (namespaced, shareable)

```
/plugin marketplace add tiny-tunnel-dot/tony-skills
/plugin install sun@tony-skills
```

Restart Claude Code once. The commands register as `/sun:sunrise` and `/sun:sunset`. Plugin skills are always namespaced by the plugin name, so there is no bare form in this mode. This is the mode to use when sharing with someone else.

Because the repo is private, the installing machine needs working git auth (the `gh` login or an SSH key), which Tony's machines already have.

## Install for bare commands (`/sunrise`, `/sunset`)

Prefer typing `/sunrise` and `/sunset`? Install them as user-level skills instead of as a plugin. Copy the two skill folders plus the shared assets into `~/.claude/skills/`:

```bash
mkdir -p ~/.claude/skills
cp -R ~/Developer/tony-skills/plugins/sun/skills/sunrise ~/.claude/skills/sunrise
cp -R ~/Developer/tony-skills/plugins/sun/skills/sunset  ~/.claude/skills/sunset
cp -R ~/Developer/tony-skills/plugins/sun/assets         ~/.claude/skills/sunset/assets
```

Restart Claude Code once. You get bare `/sunrise` and `/sunset`. The asset paths are dual-mode, so the sun cue still fires in this mode (it falls back to `~/.claude/skills/sunset/assets`).

Trade-off versus the plugin: no `/plugin update`. To pull changes, `git pull` in `~/Developer/tony-skills` and re-run the three `cp` lines.

## Updating

After editing a skill and pushing:

```
/plugin marketplace update tony-skills
/plugin update sun@tony-skills
```

No version is pinned, so every pushed commit is the latest.

## A note on sharing

These skills are personal. They reference Tony's GitHub handle (`tiny-tunnel-dot`), his `~/Developer` layout, Project Knight, his Obsidian vault structure, and his Notion board pattern. Keep this repo private.

To share a skill publicly later, make a genericized copy in a fresh public repo (strip the personal paths and handles) rather than flipping this one public. Git history would otherwise expose those details even after a cleanup commit.

## Assets and the plugin root (dual-mode)

The skills play a cosmetic sound and terminal animation on launch. The asset paths use `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/sunset}/assets/...`, which resolves both ways:

- **Plugin install:** `$CLAUDE_PLUGIN_ROOT` is set, so it points at the plugin's bundled `assets/`.
- **User-level install:** `$CLAUDE_PLUGIN_ROOT` is empty, so it falls back to `~/.claude/skills/sunset/assets/` (which the bare-command install populates).

The cue is best-effort and skips silently if anything is missing, so a path miss never breaks a run. Verify the cue fires after the first install in whichever mode you used.
