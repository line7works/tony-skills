# Sign-Off Skill — Review Findings

**Target:** `~/.claude/skills/signoff/SKILL.md` (105 lines)
**Date:** 2026-07-27
**Method:** Static read of the skill file, compared against its sibling `/wargame` skill for convention drift. No execution.

**Bottom line:** Strong skill with a clear spine. The problems are almost all gaps where the doc *asserts* rigor it never actually instructs anyone to perform — most importantly, it requires the verdict to declare how the work was verified while never telling anyone to run anything.

---

## Blocking issues

### 1. Rule 7 demands a Method line the skill never lets you earn

`SKILL.md:60` requires the verdict to declare "executed and exercised, tests run, or static analysis only" — but nothing in Step 3 or the rules tells the reviewers or the orchestrator to run the tests, start the app, or exercise the code. Every run lands on "static analysis only" by default, which makes rule 7 a confession rather than a standard.

**Suggested change** — add a Step 3.5:

```markdown
## Step 3.5 — Execute

Before writing the verdict, try to run it. In order: the project's test
command, then the thing itself against the spec's acceptance criteria.
Record what you ran and what it did. If nothing is runnable — no tests, no
entry point, no fixture — say so in one line. That is the *only* path to
"static analysis only" in the Method field.
```

### 2. Reviewers are told to execute things with no blast-radius guardrail

The `seams` lens (`:44`) explicitly hunts "migrations that don't run twice" — the obvious way a subagent checks that is to run it twice, against the real dev database. Combined with rule 5's "report, don't repair" (which reads as *don't edit files*, not *don't mutate state*), nothing stops a reviewer from wrecking local state during an inspection.

**Suggested change** — add to The rules:

```markdown
9. **Read-only against real state.** Reviewers may run tests and read
   anything, but never mutate shared state — no migrations against a real
   DB, no writes to prod/dev services, no destructive commands. To exercise
   a mutation, use `isolation: 'worktree'` and a throwaway/fixture DB, or
   report it as unverifiable and say so in Method.
```

### 3. The anti-rubber-stamp spine has an escape hatch

`:12` says a no-findings review *must* state what it tried and failed to break. But `:94` says "Omit empty sections," and "Tried and failed to break" (`:91`) is formatted as just another section. A lazy run with zero findings can legally omit the exact line that proves it looked.

**Suggested change** — rewrite `:94`:

> Omit empty sections **except `Tried and failed to break`, which is mandatory in every verdict and is the longest section when findings are few.**

---

## Real gaps

### 4. Scope auto-detect can silently review half the slice

`:24` is an `else` chain: uncommitted diff, *else* branch diff. If part of the slice is committed and the rest is still dirty — the normal mid-work state — only the uncommitted half gets reviewed, and the one-line scope statement will read as if it covered everything.

**Suggested change** — make it a union:

> uncommitted working tree **plus** the branch's commits against its base, as one scope. Fall back to files touched this session only if both are empty.

### 5. No empty-scope path

If all three detectors come up dry, the skill has no instruction and will improvise.

**Suggested change:**

> If scope detection finds nothing, stop and ask what to review. Never sign off on an empty diff.

### 6. Zero subagent mechanics

`:40` says "three parallel reviewers, one message" but never names an agent type, sync vs. background, or what they're allowed to touch. Compare `/wargame:53`, which specifies "background, single message."

**Suggested change:** specify `general-purpose` (`Explore` is read-only and can't run tests) and background execution.

### 7. Nobody adjudicates skipped-vs-deferred

Rule 4 (`:57`) sends "unbuilt-by-design" to Deferred, but a reviewer holding only the spec cannot distinguish *deliberately deferred* from *silently dropped* — and that distinction is the difference between SIGNED OFF and REJECTED. "Ask or flag" doesn't say who asks or when.

**Suggested change:**

> Deferred requires written evidence: the spec, the plan, or the user said so. An unmet requirement with no such record is a BLOCKER **and** a question to the user in the verdict — never a quiet move to Deferred. Reviewers report the gap; you adjudicate.

### 8. Step 2 and rule 2 appear to contradict each other

`:36` — "Never review the diff yourself" — versus `:55` — "Read the source yourself on every BLOCKER and MAJOR." Both are right, but a model reading top-down may resolve the conflict the wrong way.

**Suggested change** — reword `:36`:

> Never *form the initial verdict* yourself — reviewers do that. You verify their findings (rule 2); you don't originate them.

### 9. No dedup across lenses

`correctness` and `seams` overlap heavily; the same bug will land in the punch list two or three times, which reads as padding — the exact thing the "don't pad" rule forbids.

**Suggested change** — add to Step 3:

> Merge findings on `file:line` + claim before verifying. Convergence across independent lenses is signal — note it on the merged finding rather than listing it twice.

---

## Smaller stuff

### 10. Refutations vanish

Rule 2 says "Drop what you refute," so the user never learns the reviewers produced 6 findings of which 4 were bogus — real signal about how much to trust the verdict.

**Suggested change:** add a `Refuted: N` count to the Method line.

### 11. Model floor is inconsistent with its sibling skill

`/signoff:18` offers to "run anyway as a lightweight check"; `/wargame:15` hard-STOPs and names the tiers explicitly. Pick one posture. Given rule 6 ("the signature is real"), signoff arguably deserves the stricter gate — a labeled-non-signoff fallback is fine, but it should refuse to emit the `SIGN-OFF:` block at all below floor.

### 12. Rule 8's arithmetic has no home in the output

"Do the arithmetic" (`:61`) is the sharpest rule in the file, and nothing in the template records that it happened.

**Suggested change:** add computed values to the Method line or the "tried and failed to break" section.

### 13. Cosmetic: verdict enum mismatch

The template's `Verdict:` enum (`:81`) reads `WITH CONDITIONS`; the definition (`:72`) is `SIGNED OFF WITH CONDITIONS`. Make them identical so the emitted verdict is greppable.

---

## Suggested order

| Priority | Findings | Rationale |
|---|---|---|
| First pass | 1, 2, 3, 4, 7 | These change review *outcomes* — what gets verified, what gets wrecked, what gets signed |
| Second pass | 5, 6, 8, 9 | Robustness and clarity; prevents improvisation and padding |
| Cleanup | 10, 11, 12, 13 | Polish and cross-skill consistency |
