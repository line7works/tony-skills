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

## Install (on any of Tony's machines)

```
/plugin marketplace add tiny-tunnel-dot/tony-skills
/plugin install sun@tony-skills
```

Restart Claude Code once. The commands then register as `/sun:sunrise` and `/sun:sunset` (plugin skills are namespaced by the plugin name).

Because the repo is private, the installing machine needs working git auth (the `gh` login or an SSH key), which Tony's machines already have.

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

## Assets and the plugin root

The skills play a cosmetic sound and terminal animation on launch. Inside a plugin those asset paths use `${CLAUDE_PLUGIN_ROOT}/assets/...`, which resolves to the installed plugin location. The cue is best-effort and skips silently if anything is missing, so a path miss never breaks a run. Verify the cue fires after the first install; if it does not, asset path resolution is the thing to check.
