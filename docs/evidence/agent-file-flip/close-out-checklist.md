# agent-file-flip — close-out checklist (2026-09-04)

Slice D, R4. Three steps that happen outside any PR and only on Tony's word, plus two optional live checks. None of these was executed by the Slice D build session; each is copied verbatim so the session that runs it needs no interpretation.

## (a) Reinstall on the Studio after each slice's merge

Run inside Claude Code on the Studio, after the slice's PR is merged to `main`. After Slice D merges, the full list (D touches `precon` and `signoff`; the rest are listed so every plugin lands on the same commit):

```
/plugin update sun@tony-skills
/plugin update precon@tony-skills
/plugin update architect@tony-skills
/plugin update blueprint@tony-skills
/plugin update inspect@tony-skills
/plugin update signoff@tony-skills
/plugin update recheck@tony-skills
/plugin update vertical@tony-skills
/plugin update ship@tony-skills
/plugin update handoff@tony-skills
/plugin update build@tony-skills
```

Then restart the session; a running session keeps the old cache. Verify with `cat ~/.claude/plugins/installed_plugins.json`: each of the eleven plugins above shows the merged `main` commit as its version, and the other nine (`forge`, `wargame`, `arcade`, `shutdown`, `digest`, `fb`, `huh`, `jpb`, `print-tune`) keep whatever version they had, since no slice touched them and they are not updated here.

## (b) The vault note `~/ObsidianVault/01-domain/claude-skills/sunrise.md`

Line 39 (the `*Changing 2026-09:*` sub-bullet) is removed, and line 38's seed set is rewritten to the kit's Tier 0. Before (verbatim, lines 38–39 as of 2026-09-04):

```
- **Local repo:** `~/Developer/<Name>` scaffolded by archetype, with seeded boot docs (README, CLAUDE.md, AGENTS.md, .gitignore, .env.example), git init, first commit.
  - *Changing 2026-09:* the seed set is now defined by [[repo-doc-kit]] Tier 0, with `AGENTS.md` as the body and `CLAUDE.md` as the one-line `@AGENTS.md` stub (the reverse of what the skill wrote before). The skill edit is pending; until it lands, this note describes the old behavior.
```

After (one line replaces both):

```
- **Local repo:** `~/Developer/<Name>` scaffolded by archetype, with the [[repo-doc-kit]] Tier 0 seeded (`README.md`, `AGENTS.md` as the instruction body, `CLAUDE.md` as the one-line `@AGENTS.md` stub, `.gitignore`, `.env.example`, an empty `docs/`), any precon or architect doc staged in `~/Documents` adopted into `docs/`, git init, first commit.
```

Run the vault check from `~/.claude/CLAUDE.md` first (`VAULT OK`), back up the note outside the vault, then edit. Expected after: `grep -c "Changing 2026-09" ~/ObsidianVault/01-domain/claude-skills/sunrise.md` prints `0`. The kit note's own line 12 ("skill edit pending as of 2026-09-03") is the same stale claim in the other file and is worth the same word.

## (c) The memory note `~/.claude/projects/-Users-tonycoon/memory/agent-file-flip-program.md`

Its status is the frontmatter `description:` line (line 3), currently:

```
description: "2026-09-03 program to make AGENTS.md the body and CLAUDE.md the @AGENTS.md stub in every repo, plus the repo doc kit; vault pass DONE, skills + per-repo passes pending"
```

Rewrite to:

```
description: "2026-09-03 program to make AGENTS.md the body and CLAUDE.md the @AGENTS.md stub in every repo, plus the repo doc kit; vault pass DONE, phase 2 (skills) DONE 2026-09-04, per-repo pass (phase 3) pending"
```

That one line is the whole edit; nothing else in the note or in `MEMORY.md` changes under this step.

## Optional live checks (Tony's word, each spends real resources)

1. One `/sunrise --dry-run` on a throwaway name (for example `flip-check`) from a plain session, to watch the Phase 0 preview table: it lists the Tier 0 files the run would seed and, in its staged-docs row, the single line `nothing staged` for a name with nothing in `~/Documents`. A dry run stops after Phase 0 and creates nothing; Phase 1 never runs, so the seeding itself is exercised only by a live run, which is outward and stays gated.
2. One live `/signoff` in a scratch repo with no `REVIEW.md` (a fresh `git init` in a throwaway folder under `~/Developer/`, with one file and a two-line build doc; move it to `~/Developer/_archive` after), to exercise the first-run gate: infer, show the sheet, wait for the word, write on the word, continue on defaults without it. Spends subagents.
