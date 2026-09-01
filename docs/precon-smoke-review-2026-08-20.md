# Precon Slice B smoke test — independent monitor review (2026-08-20)

Written by the session that designed /precon and blueprinted its build plan
(`~/Documents/skill-lab/precon-skill-build-plan.md`). This session monitored the
smoke run passively from outside (transcript + files only, nothing injected) and
graded it against Slice B's nine acceptance criteria. This file is for the
smoke-terminal's records alongside its own self-assessment.

**Standing gate, stated up front: findings only. Nothing in this file is
authorization. The two proposed fixes at the bottom are AWAITING TONY'S WORD —
if he gives it in your session, apply them there and log per B-R2; if he gives
it in the monitor session, it will apply them and tell you.**

## Verdict

The skill works. Seven of nine ACs pass clean, one real failure (AC2), one
minor judgment (AC9). The run also demonstrated correct seam judgment beyond
what the ACs measure.

## The card

- **AC1 Harvest before first question — PASS.** Atlas property reads
  (`BaselineTestPlan.swift`, TGU grep, web/ inspection) all preceded round 1;
  the scope doc was born from harvest + Tony's opening ramble before any
  question was asked.
- **AC2 Triage stated aloud — FAIL.** No tier classification was ever spoken in
  the run. Every occurrence of napkin/bounded/architectural in the transcript is
  quoted skill text (from the Slice A build earlier in the same session), not a
  classification of the Atlas idea. Step 2 was silently skipped. Interview depth
  self-calibrated fine (4 rounds, bounded-appropriate), but the mechanism did
  not observably fire, and R10's "doc born after triage" ordering was therefore
  also not observable.
- **AC3 Numbered questions with ➡️ recs — PASS.** Every round; answer-by-number
  exercised repeatedly (doc ledger cites "Q1 answered", "round 3 Q2 answered").
- **AC4 Board opens each round — PASS.** All four rounds:
  R1 `decided 6 · assumed 1 · parked 0 · open your-calls 4` → R4
  `decided 19 · assumed 5 · parked 1 · open your-calls 1`.
- **AC5 Zero research — PASS.** Zero WebFetch/WebSearch tool uses in the entire
  run. The one parked item is `needs prototype` (correct tag; no research needs
  arose).
- **AC6 Scope doc path + sections — PASS with note.** All seven template
  sections present; ledger discipline strong (including an honestly-recorded
  superseded assumption at the video-labels line). Path deviates from R10's
  letter: invoked from `~` (not inside a repo), the letter says
  `~/Documents/<idea>-scope.md`; the run filed to
  `~/Developer/Atlas/docs/baseline-test-page-scope.md` because the idea
  unambiguously belongs to Atlas, and ledgered that call as `assumed`. Better
  behavior than the written rule (see proposed fix 2).
- **AC7 Exit test offer + send gate — PASS.** Offer was exactly the spec'd
  shape: one numbered question, local Claude reader as ➡️ recommended default,
  GPT named with pinned id, decline as a clean path. The external send happened
  only after Tony's literal word ("Do a GPT one since we're doing the smoke
  test"), via `mcp__codex__codex` with `model: gpt-5.6-sol`,
  `sandbox: read-only`, `approval-policy: never`, and
  `config: {web_search: disabled}` — the parity setting carried unprompted (see
  "already applied" below).
- **AC8 Read-back, justification, full stop — PASS.** Read-back covered
  decided (21), assumed (5, each with its why), parked (1), out of scope (1),
  open (1); the one-line ending justification was present; genuine stop with no
  building and no auto-/blueprint, plus an honest reminder that blueprint does
  not yet hunt scope docs.
- **AC9 Report block — PASS, minor.** All required fields present
  (`PRECON:`, Doc path, four counts, Parked lines with tags, Next). Arguably
  the path reinterpretation warranted a `SKILL NOTE:` line and none was carried
  — though the deviation WAS visible via the `assumed` ledger line, so Tony saw
  it through the other channel. Judgment call, not a clear violation.

## Beyond the ACs — things the run got right

- **Seam filtering of the cold reader's output.** Sol returned a mix of
  scope-level and blueprint-altitude confusions. The run reopened only the
  scope-level ones (history/multi-run behavior, link visibility semantics,
  editable video names) and left framework/URL-pattern/field-spec questions
  downstream, even marking "exact widget is builder altitude" in the ledger.
  This is the /blueprint seam working as designed.
- **Suggest-only held at its ceiling.** The prototype suggestion ("a couple of
  mock layouts would settle it — that's yours to order") was one line, nothing
  was built, and the item was parked `needs prototype`.
- **Record-don't-decide under dictation mush.** The garbled phrase ("a visual
  separation from one technical rep max and the technical rep max") was read
  back with an interpretation and a confirm request, not silently ledgered.
- **B-R1 satisfied.** Real idea (Tony's fresh pick), not a synthetic toy.

## Already applied during the run (Tony's word given in the monitor session)

- SKILL.md Step 5 option 2 now carries: the codex call includes
  `config: {web_search: disabled}` with the rationale (a reader that can search
  answers its own questions instead of reporting them). Logged in the build
  plan's `## Discovered` section, 2026-08-20. Do not re-apply.

## Proposed fixes — NOT YET AUTHORIZED, awaiting Tony's word

1. **Fix AC2 structurally (the real failure):** weld triage to the board so it
   cannot be silently skipped — the round header renders as
   `Round N — <tier> — board: ...`. One-line changes to Step 2/Step 3 board
   text in `~/.claude/skills/precon/SKILL.md`.
2. **Legalize the better path behavior:** amend R10/Step 4's save rule to
   "file into the repo the idea unambiguously belongs to when one exists, and
   ledger that call as `assumed`; else `~/Documents/<idea>-scope.md`" —
   matching what this run did. Mirror the same wording change in the build
   plan's R10 so the spec and skill stay in step, and note it in the plan's
   ledger.

After fixes land (whoever applies them), Slice B's `Status:` line in the build
plan is ready to advance per the loop's normal stations.
