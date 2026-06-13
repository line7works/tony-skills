# tony-skills

## What this is

A private Claude Code plugin marketplace holding Tony's personal skills. Three plugins:

- `sun` provides `/sunrise` (bootstrap a project across every layer) and `/sunset` (archive one reversibly).
- `clerk` bundles the `clerk-auditor` subagent (Clerk), a strictly read-only auditor that returns a cleanup "punch list" and changes nothing.
- `det-audit` provides `/det-audit [session|repo]`, a report-only audit that finds recurring LLM work convertible to deterministic code (scripts, hooks, cron, CI) and returns a PURE SCRIPT / JIG / KEEP LLM punch list.

See `README.md` for install and structure.

## Source of truth

The live skill files a Claude Code session actually runs are the user-level copies at `~/.claude/skills/sunrise|sunset/` on each machine. This repo is the canonical, shareable, version-controlled home for them. A change made here reaches a machine only after that machine reinstalls or updates the plugin (`/plugin update sun@tony-skills`). Do not assume editing this repo changes a running machine's behavior until it is reinstalled.

The `clerk-auditor` agent works the same way, but Tony runs it **user-level, not as the plugin** (to match how `sun` is installed on his machines). The live copy is `~/.claude/agents/clerk-auditor.md` on each machine, synced by `git pull` here then copying `plugins/clerk/agents/clerk-auditor.md` over it. The `clerk` plugin (`/plugin install clerk@tony-skills`) is the alternative managed route. Never run both on one machine — two definitions of the agent name `clerk-auditor` collide. Edit the agent at `plugins/clerk/agents/clerk-auditor.md`, push, then re-sync each machine (re-copy for user-level, or `/plugin update clerk@tony-skills` for the plugin route). See `README.md` → "Clerk: user-level vs plugin".

The `det-audit` command works the same way. Tony runs it **user-level**, so the live copy is `~/.claude/commands/det-audit.md` on each machine, synced by `git pull` here then copying `plugins/det-audit/commands/det-audit.md` over it. The `det-audit` plugin (`/plugin install det-audit@tony-skills`) is the alternative managed route, namespaced `/det-audit:det-audit`. Edit the command at `plugins/det-audit/commands/det-audit.md`, push, then re-sync each machine.

## Invariants

- Keep private. The skills and the Clerk agent contain Tony-specific paths, handles, and project names.
- Asset references in the SKILL.md files use `${CLAUDE_PLUGIN_ROOT}/assets/...`. Do not revert them to absolute `~/.claude/...` paths, which break once the plugin is installed to its cache dir.
- The `sun` plugin bundles both skills because they share the `assets/` folder. Keep them together.
- The `clerk` plugin is strictly read-only by design. The agent's hard rule (never modify, move, delete, commit, or push anything) is the whole point of Clerk. Do not add write-capable tools or relax that rule when editing `plugins/clerk/agents/clerk-auditor.md`.
- The `det-audit` command is report-only by design ("Report only. Change nothing."). Keep that rule in `plugins/det-audit/commands/det-audit.md`; do not turn it into a command that edits, creates, or deletes files. Its job is to produce the punch list, not to apply it.

## Workflow

Feature branches plus PRs for ongoing changes. Never push to `main` directly (the initial scaffold commit is the only exception). Merge via the GitHub PR web UI or terminal, never GitHub Desktop.
