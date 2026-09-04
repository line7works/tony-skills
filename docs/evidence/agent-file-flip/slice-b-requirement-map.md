# agent-file-flip — Slice B requirement map (2026-09-04)

Build doc: `docs/plans/2026-09-04-agent-file-flip.md`, Slice B. Line numbers are from branch `feat/agent-file-flip-b` at the slice's final commit. All citations are in `plugins/sun/skills/sunrise/SKILL.md` unless another path is given.

| Req | Implemented at | What the cited line says |
|---|---|---|
| R1 `AGENTS.md` is the body, spec-sheet sections | `:395`–`:437` | Template headed "Repo `AGENTS.md` (the instruction body)": Commands, Conventions that differ from defaults, Footguns, Where to look, Gates; carries Tony's one-line description, feature-branch and PR gate, never push to `main`, merge via web UI or terminal, `vercel env pull`, end-of-session line |
| R1 `CLAUDE.md` is the stub, one line, section only with Claude-only lines | `:439`–`:458` | Template headed "Repo `CLAUDE.md` (the stub)": `@AGENTS.md` alone; the `## Claude Code specific` form shown only for the case where a Claude-only line exists; sunrise seeds none |
| R2 Phase 1 step 3 seeds Tier 0, six files, kit note and spec sheet named | `:200`–`:206` | "Seed Tier 0 of the repo doc kit": `AGENTS.md`, `CLAUDE.md`, `README.md`, `.gitignore`, `.env.example`, `docs/.gitkeep`; points at `~/ObsidianVault/01-domain/repo-doc-kit.md` for the set and `01-domain/agents-md-best-practices.md` for body content |
| R2 merge-not-overwrite kept | `:201`, `:202` | Framework block stays at the top of `AGENTS.md` inside its markers; a scaffolder `CLAUDE.md` already reading `@AGENTS.md` is kept as is |
| R3 frontmatter description | `:6`–`:9` | "seed the repo doc kit's Tier 0 (README, AGENTS.md as the instruction body, CLAUDE.md as a one-line `@AGENTS.md` stub, …)" |
| R3 Core principles | `:82`, `:85` | "use his words in `_index.md`, `AGENTS.md`, …"; "The repo `AGENTS.md` (…; `CLAUDE.md` is its one-line `@AGENTS.md` stub), the vault `_index.md`, and the memory note all point at each other" |
| R3 Phase 1 step 3 | `:200`–`:202` | as R2 |
| R3 Phase 2 | `:222` | "Confirm the branch rule is in `AGENTS.md` (the seeded Gates section carries it)" |
| R3 Phase 5 | `:265` | Notion coordinates recorded in the vault `_index.md` and "the repo `AGENTS.md` (Where to look)" |
| R3 Phase 7b memory note | `:303` | pointer to "the repo `AGENTS.md` (canonical detail)" (see Build assumptions: line outside the footprint's pointer list, same file) |
| R3 Phase 8 closeout text | `:336`–`:337` | "AGENTS.md loads through the CLAUDE.md stub" |
| R3 handoff-prompt / memory template | `:474` | "Repo `AGENTS.md` (the instruction body: commands, footguns, gates; `CLAUDE.md` is its `@AGENTS.md` stub)" |
| R3 template headings | `:395`, `:439` | "Repo `AGENTS.md` (the instruction body)", "Repo `CLAUDE.md` (the stub)" |
| R3 `REVIEW.md` never seeded | `:200` | "`REVIEW.md` in particular is never seeded (`/signoff` creates it on its first run in the repo)" |
| R4 kit's four verification lines in Phase 8 | `:311`–`:320` | The four lines verbatim from the kit note, run in the new repo's root; canary must match line 1 of `AGENTS.md` or the framework block's first line; "Any line that fails is a failed baseline: report it exactly like a failed deploy" |
| R5 adoption step after git init, before the first commit | `:207`, `:208`–`:214`, `:215` | Step 4 idempotent init; step 5 "Adopt staged docs" with the four staged paths, destination names, date from the doc's own header, `nothing staged`, list-and-ask on more than one candidate, move not copy; step 6 first commit |
| R5 closeout names what was adopted | `:326` | "Docs -> adopted: <each moved doc's new path, or "nothing staged">" |
| R6 dry-run preview lists Tier 0 and staged docs | `:162`–`:166`, `:184`–`:186` | Preview seed line names the six files; `Docs adopt staged:` line, one per match or "nothing staged"; the lookup runs read-only in Phase 0 |

## Acceptance evidence

AC1 (`grep -n -i "boot doc\|canonical agent file\|stub pointing at" plugins/sun/skills/sunrise/SKILL.md`): no output. Every remaining `CLAUDE.md` mention in the file (lines 7, 85, 162, 199, 202, 315, 316, 337, 439, 474) describes the stub role or the scaffolder's own pre-seeded stub. PASS.

AC2 (templates rendered by hand for `fakeproj`, a static-site throwaway, into the session scratchpad; `git init -b main`, one commit; the kit's lines run in that directory):

```
AGENTS.md tracked, exact case
stub imports the body
stub is a real file
```

Canary, `claude -p "Quote verbatim the first line of the project instructions you were given"` in the scratch repo:

```
The first line of the project instructions (from `AGENTS.md`, pulled in by `CLAUDE.md` via `@AGENTS.md`) is:

# Fakeproj
```

Line 1 of the rendered `AGENTS.md` is `# Fakeproj`. PASS on all four. The scratch render is not committed to this repo.

AC3 (`wc -l CLAUDE.md` in the scratch render): `1 CLAUDE.md`. PASS.

AC4 (fresh session, `claude --plugin-dir plugins/sun -p …`, run from the repo root on the branch, asked what Phase 1 step 3 seeds, what Phase 8 verifies, and what the staged-doc step does for none/one/many): the session said it read the branch copy and named all six Tier 0 files by role, the kit note as the seed set and the spec sheet for body content, `REVIEW.md` as never seeded, the four verification lines verbatim with the failed-baseline rule, and the staged-doc rule as "no match: `nothing staged` and continue; one match per role: `mv`, not copy, recorded in the Phase 8 summary; more than one: list with destinations and ask Tony, never pick". As in Slice A, `--plugin-dir` loads the branch copy alongside the installed copy rather than instead of it; the answer was judged on what it said about the branch copy. PASS. Log: session scratchpad `ac4.log`.

AC5 (`grep -n "docs/.gitkeep" plugins/sun/skills/sunrise/SKILL.md`): line 163 (the Phase 0 preview) and line 206 (Phase 1 step 3). PASS.

AC6: this file.
