# tony-skills

## What this is

A private Claude Code plugin marketplace holding Tony's personal skills. One plugin, `sun`, provides `/sunrise` (bootstrap a project across every layer) and `/sunset` (archive one reversibly). See `README.md` for install and structure.

## Source of truth

The live skill files a Claude Code session actually runs are the user-level copies at `~/.claude/skills/sunrise|sunset/` on each machine. This repo is the canonical, shareable, version-controlled home for them. A change made here reaches a machine only after that machine reinstalls or updates the plugin (`/plugin update sun@tony-skills`). Do not assume editing this repo changes a running machine's behavior until it is reinstalled.

## Invariants

- Keep private. The skills contain Tony-specific paths, handles, and project names.
- Asset references in the SKILL.md files use `${CLAUDE_PLUGIN_ROOT}/assets/...`. Do not revert them to absolute `~/.claude/...` paths, which break once the plugin is installed to its cache dir.
- The `sun` plugin bundles both skills because they share the `assets/` folder. Keep them together.

## Workflow

Feature branches plus PRs for ongoing changes. Never push to `main` directly (the initial scaffold commit is the only exception). Merge via the GitHub PR web UI or terminal, never GitHub Desktop.
