# tony-skills

## What this is

The permanent home for things Tony builds on his workstations and wants to keep. Not just skills: skills, subagents, standalone scripts, machine configs, and implementation specs all belong here. The test is "was this made on one of these Macs and should it survive the machine," not "is it a Claude Code skill."

Two parts, split by how a thing is consumed rather than what it is:

- `plugins/` — a Claude Code plugin marketplace. Things Claude Code installs and runs (skills, subagents), listed in `.claude-plugin/marketplace.json`.
- `tools/` — everything else. Things a human copies, runs, or reads directly: macOS automations, dotfiles, scripts, and specs for code that lives elsewhere. Not installed through Claude Code, not in `marketplace.json`.

When something does not obviously fit either, it goes in `tools/` — do not conclude it belongs outside the repo.

Five plugins:

- `sun` provides `/sunrise` (bootstrap a project across every layer) and `/sunset` (archive one reversibly).
- `clerk` bundles the `clerk-auditor` subagent (Clerk), a strictly read-only auditor that returns a cleanup "punch list" and changes nothing.
- `forge` provides `/forge` (Claude-driven image generation on Fal.ai — the skill writes prompts, runs vision QA, and renders on-brand images through the bundled `assets/forge.py` CLI).
- `wargame` provides `/wargame` (adversarial pre-mortem of any target — new project, existing feature, or planned change; ranked + verified failure modes, kill criteria, plain-language decision questions).
- `signoff` provides `/signoff` (independent adversarial review of freshly built work against its spec doc, ending in a signed verdict plus punch list). The back half of `/wargame`: war game before building, sign-off after.

Tony Tools (`tools/`): anything preserved here that Claude Code does not install — macOS automations, dotfiles, scripts, and implementation specs for code that lives elsewhere. Each is a folder with its own `README.md`. Currently one: `mcp-obsidian-worker/` (spec only — the Worker source is not in this repo and may not exist on disk anywhere). See `tools/README.md`.

See `README.md` for install and structure.

## Source of truth

The live skill files a Claude Code session actually runs are the user-level copies at `~/.claude/skills/sunrise|sunset|forge|wargame|signoff/` on each machine. This repo is the canonical, shareable, version-controlled home for them. A change made here reaches a machine only after that machine reinstalls or updates the plugin (`/plugin update sun@tony-skills`). Do not assume editing this repo changes a running machine's behavior until it is reinstalled.

The `clerk-auditor` agent works the same way, but Tony runs it **user-level, not as the plugin** (to match how `sun` is installed on his machines). The live copy is `~/.claude/agents/clerk-auditor.md` on each machine, synced by `git pull` here then copying `plugins/clerk/agents/clerk-auditor.md` over it. The `clerk` plugin (`/plugin install clerk@tony-skills`) is the alternative managed route. Never run both on one machine — two definitions of the agent name `clerk-auditor` collide. Edit the agent at `plugins/clerk/agents/clerk-auditor.md`, push, then re-sync each machine (re-copy for user-level, or `/plugin update clerk@tony-skills` for the plugin route). See `README.md` → "Clerk: user-level vs plugin".

## Invariants

- Keep private. The skills and the Clerk agent contain Tony-specific paths, handles, and project names.
- Asset references in the SKILL.md files use `${CLAUDE_PLUGIN_ROOT}/assets/...`. Do not revert them to absolute `~/.claude/...` paths, which break once the plugin is installed to its cache dir.
- The `sun` plugin bundles both skills because they share the `assets/` folder. Keep them together.
- The `clerk` plugin is strictly read-only by design. The agent's hard rule (never modify, move, delete, commit, or push anything) is the whole point of Clerk. Do not add write-capable tools or relax that rule when editing `plugins/clerk/agents/clerk-auditor.md`.
- The `wargame` skill's Opus-or-greater model floor (Step 0) is deliberate — do not remove or soften it, and never let it pin subagents below `opus`. Its anti-theater rule (HIGH-ranked failures must convert to a verified check, named test, or spike) is the skill's whole point; edits that let failures stay as unranked table rows defeat it.
- The `signoff` skill's independence rule is the whole point: the session that wrote the code must never review it, reviewers are always fresh subagents, and they never receive the author's rationale. Its anti-rubber-stamp rule (a clean review must say what it tried to break and failed to break) exists so "looks good" can't masquerade as inspection. It shares wargame's Opus floor. `signoff` is report-only — do not add fixing behavior; the user decides what to repair after seeing the verdict.

## Workflow

Feature branches plus PRs for ongoing changes. Never push to `main` directly (the initial scaffold commit is the only exception). Merge via the GitHub PR web UI or terminal, never GitHub Desktop.
