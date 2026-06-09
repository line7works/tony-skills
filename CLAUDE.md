# tony-skills

## What this is

A private Claude Code plugin marketplace holding Tony's personal skills. Two plugins:

- `sun` provides `/sunrise` (bootstrap a project across every layer) and `/sunset` (archive one reversibly).
- `clerk` bundles the `clerk-auditor` subagent (Clerk), a strictly read-only auditor that returns a cleanup "punch list" and changes nothing.

See `README.md` for install and structure.

## Source of truth

The live skill files a Claude Code session actually runs are the user-level copies at `~/.claude/skills/sunrise|sunset/` on each machine. This repo is the canonical, shareable, version-controlled home for them. A change made here reaches a machine only after that machine reinstalls or updates the plugin (`/plugin update sun@tony-skills`). Do not assume editing this repo changes a running machine's behavior until it is reinstalled.

The `clerk-auditor` agent works the same way, but Tony runs it **user-level, not as the plugin** (to match how `sun` is installed on his machines). The live copy is `~/.claude/agents/clerk-auditor.md` on each machine, synced by `git pull` here then copying `plugins/clerk/agents/clerk-auditor.md` over it. The `clerk` plugin (`/plugin install clerk@tony-skills`) is the alternative managed route. Never run both on one machine — two definitions of the agent name `clerk-auditor` collide. Edit the agent at `plugins/clerk/agents/clerk-auditor.md`, push, then re-sync each machine (re-copy for user-level, or `/plugin update clerk@tony-skills` for the plugin route). See `README.md` → "Clerk: user-level vs plugin".

## Invariants

- Keep private. The skills and the Clerk agent contain Tony-specific paths, handles, and project names.
- Asset references in the SKILL.md files use `${CLAUDE_PLUGIN_ROOT}/assets/...`. Do not revert them to absolute `~/.claude/...` paths, which break once the plugin is installed to its cache dir.
- The `sun` plugin bundles both skills because they share the `assets/` folder. Keep them together.
- The `clerk` plugin is strictly read-only by design. The agent's hard rule (never modify, move, delete, commit, or push anything) is the whole point of Clerk. Do not add write-capable tools or relax that rule when editing `plugins/clerk/agents/clerk-auditor.md`.

## Workflow

Feature branches plus PRs for ongoing changes. Never push to `main` directly (the initial scaffold commit is the only exception). Merge via the GitHub PR web UI or terminal, never GitHub Desktop.
