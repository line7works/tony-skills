# Signoff skill test + fix — state doc (2026-07-30)

Written before a /compact on the Mac Studio session. If the compacted session loses
detail, this file is the source of truth. Supersedes nothing; companion to
`~/Documents/signoff-skill-review.md` (the punch list, still fully valid).

## Mission

Test `/signoff` as-is, fold in fixes, rerun, compare.

1. **Baseline run (IN PROGRESS, not by this session):** Tony is running, in a separate
   fresh terminal: `/signoff the CX2 work — write the full verdict to
   ~/Documents/signoff-baseline-cx2.md` in `~/Developer/Atlas`
   (branch `feat/cx2-one-brief-call`). DO NOT run the review yourself. Wait for Tony to
   bring the doc back.
2. **Then:** fold fixes into `~/.claude/skills/signoff/SKILL.md`, rerun `/signoff` on the
   same CX2 scope, compare against the baseline doc.

## Key facts already established

- The skill file `~/.claude/skills/signoff/SKILL.md` (105 lines) is UNCHANGED since the
  review doc was written (2026-07-27) — every line ref in the review doc still lands.
- Baseline target chosen deliberately: Atlas CX2 slice = 2 commits on
  `feat/cx2-one-brief-call` (a01e48b punch-list fix, 3b7d529 feature) PLUS ~8 dirty
  files. That committed+dirty split live-tests review-doc finding 4 (scope else-chain
  reviews only half). Spec lives inside `docs/build-plan-2026-07-19.md` (no dedicated
  CX2 doc), which tests spec-hunting.
- The baseline run includes one instructed deviation (write verdict to a file; skill
  default is chat-only) — ignore that when comparing behavior.

## Fold plan (review doc findings + doc-reading adjustments)

Apply from `~/Documents/signoff-skill-review.md`:
- First pass: findings 1+2 folded as ONE unit (execute step must land together with the
  read-only/blast-radius guardrail), 3 (tried-and-failed-to-break mandatory), 4 (scope =
  union of uncommitted + branch diff), 7 (Deferred needs written evidence, else BLOCKER
  + question to user).
- Second pass: 5 (empty-scope stop), 6+9 collapsed into one subagent-mechanics item
  (general-purpose agents, background, dedup on file:line before verify), 8 (reword
  "never review the diff yourself" to "never form the initial verdict yourself").
- Cleanup: 10 (Refuted: N count — UPGRADED to load-bearing, see below), 11 (hard model
  floor like /wargame), 12 (arithmetic recorded in output), 13 (verdict enum match).

Adjustments from reading the new Anthropic docs (2026-07-30, this session):
1. **Finder/filter split:** official Opus 5 guidance says conservative-reporting
   instructions ("verified or cut", "don't pad") given to FINDERS depress recall —
   reviewers should report EVERYTHING with confidence + severity; filtering belongs to
   the orchestrator verify pass (rule 2). Move rules 1/3 filtering language to the
   orchestrator only. This upgrades finding 10.
2. **Wording of the execute step:** Opus 5 self-verifies; over-prescriptive re-check
   language causes over-verification. Write Step 3.5 as a goal ("earn the Method line by
   running what's runnable") not a checklist.
3. **Add one line: reviewers do not spawn their own subagents** (Opus 5 delegates
   readily; skill caps orchestrator spawns at 3/5 but says nothing about reviewers).
4. **Skill text ≠ enforcement:** per Claude Code docs, instructions are context; hard
   blast-radius guarantees need hooks/permission rules. Add the prose rule now; flag the
   hook option to Tony as a decision, don't build it unasked.

## Doc sources read (for citations in the final writeup)

- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- https://code.claude.com/docs/en/memory
  (CLAUDE.md: <200 lines/file, path-scoped .claude/rules/, HTML comments stripped,
  /doctor trim check — separate future task for Tony's global CLAUDE.md, not this one)

## Rules for the continuation

- Do not edit SKILL.md until Tony delivers the baseline doc AND says to fold.
- Discuss-only unless Tony says build. Stop and report over improvising.
- Comparison must be apples to apples: same CX2 scope, same repo state if possible
  (note: Tony may have committed the dirty files by then — record the repo state at
  rerun time and say so in the comparison).
