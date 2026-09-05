# agent-file-flip — Slice D requirement map (2026-09-04)

Build doc: `docs/plans/2026-09-04-agent-file-flip.md`, Slice D. Line numbers are from branch `feat/agent-file-flip-d` at the slice's final build commit. Paths are abbreviated: `precon` = `plugins/precon/skills/precon/SKILL.md`, `signoff` = `plugins/signoff/skills/signoff/SKILL.md`, `marketplace` = `.claude-plugin/marketplace.json`, `evidence/` = `docs/evidence/agent-file-flip/`.

| Req | Implemented at | What the cited line says |
|---|---|---|
| R1 README `docs/` description names the four subfolders and what lands in each | `README.md:97`, `README.md:101–108` | Layout line: "the loop's paper trail: scope/ plans/ reviews/ architecture/ evidence/"; the paragraph names `docs/scope/` (precon), `docs/plans/` (blueprint; what build, signoff, recheck work from), `docs/reviews/` (signoff and vertical verdicts, cold reads, inspect output), `docs/architecture/` (architect), `docs/evidence/` (requirement maps). Roster lines 38–47 untouched |
| R2 CLAUDE.md `sun` bullet reflects Slice B | `CLAUDE.md:20` | "`/sunrise` seeds the repo doc kit's Tier 0 (`README.md`, `AGENTS.md` as the instruction body, `CLAUDE.md` as a one-line `@AGENTS.md` stub, …) and adopts any precon or architect doc staged in `~/Documents`"; "`/sunset` reads and writes no repo instruction file" |
| R2 CLAUDE.md signoff invariant reflects Slice C, still report-only | `CLAUDE.md:43` | "`signoff` is report-only — do not add fixing behavior" kept; "The two files it does write are records, not repairs: the verdict doc under `docs/reviews/`, and the repo's `REVIEW.md` sheet (created on the first run only on the user's word, appended to only by the second-failure rule); `/recheck` and `/vertical` read `REVIEW.md` and never write it" |
| R3 sunset re-read on record with the pasted grep | `evidence/sunset-reread.md` | The one `AGENTS.md` mention (vault guard, sunset line 83), the statement that it reads or writes no repo instruction file, the grep command and output |
| R4 close-out checklist: three gated steps verbatim, two optional live checks | `evidence/close-out-checklist.md` | (a) the eleven `/plugin update` lines; (b) vault note lines 38–39 before and after, backup path, expected grep count; (c) the memory note's `description:` line before and after; the `/sunrise --dry-run` and scratch-repo `/signoff` checks |
| R5 precon says relocation is Tony's or sunrise's | `precon:59`, `precon:130` | "relocating the doc is Tony's or /sunrise's (its staged-doc adoption step, when it creates the repo), never this skill's"; What-NOT: "relocation is Tony's or /sunrise's, never this skill's" |
| R6 marketplace architect entry no longer says Tony hand-points | `marketplace:81` | "staged in ~/Documents before a repo exists, adopted into docs/architecture/ by /sunrise when it creates the repo, and read there by /blueprint"; JSON still parses |
| R7 fresh-session checks re-run from the installed cache | `evidence/fresh-session-rerun.md` | Four sessions (build, sun, signoff, recheck-and-vertical), the cache commit per plugin, the question and full answer for each, all four passing |
| R8 enclosing function resolved against the verdict block's Scope-line commit | `signoff:140` | "A ledger line carries only `file:line`, so its enclosing function is resolved against the commit named in that verdict block's own Scope line, never the working tree" |

## Acceptance criteria, as exercised

| AC | Command | Result |
|---|---|---|
| AC1 | `grep -n "docs/scope\|docs/plans\|docs/reviews\|docs/architecture" README.md` | hits at 102, 104, 105 (the `docs/` paragraph) |
| AC2 | `grep -n "AGENTS.md" CLAUDE.md`; `grep -n "REVIEW.md" CLAUDE.md` | 20 (sun bullet); 43 (signoff invariant) |
| AC3 | rerun of the sunset grep, diffed against the pasted output | identical, one line (83) |
| AC4 | read; `grep -c "Changing 2026-09" ~/ObsidianVault/01-domain/claude-skills/sunrise.md`; memory note md5 before and after | 1; `e81f4b00ffd6c18286681dec156dee2f` unchanged |
| AC5 | this file | R1–R8 mapped |
| AC6 | `grep -n "relocation is Tony's" precon` lines all contain "sunrise"; `grep -c "never the skill's" precon` | yes (1 of 1); 0 |
| AC7 | `grep -c "hand-points" marketplace`; `python3 -c "import json;json.load(open('.claude-plugin/marketplace.json'))"` | 0; exit 0 |
| AC8 | read `evidence/fresh-session-rerun.md` | four answers, each with its cache commit, none missing expected content |
| AC9 | `grep -n "Scope line" signoff` | 140 |
