# SIGN-OFF: CX2 · One Claude call writes the note and the package

**Verdict: REJECTED**

**Scope:** `main..a01e48b` — commits `3b7d529` (feat: one Claude call writes the note and the session) and `a01e48b` (fix: work the CX2 sign-off punch list). Reviewed in an isolated worktree pinned to `a01e48b`, so CX3 (`5824342`, on the branch tip) is excluded as out of scope per instruction. Working tree was clean, so the union of committed + uncommitted work is exactly these two commits.

**Spec:** `docs/build-plan-2026-07-19.md` §CX2 (line 1642), including its `✅ BUILT` and `⚠️ CORRECTED` notes — treated as claims to verify, not as evidence.

**Depth:** LEAN + `tests` (added because the build note makes load-bearing claims about what the new tests pin — encoded bytes, cap coverage, schema/type agreement — which makes the tests part of the deliverable).

**Method:** Ran it. `xcodegen generate`, full iOS suite executed **5 times** (897 tests / 93 suites each run, redirect-not-pipe, exit status and restart count checked per CLAUDE.md); the ordering guard run 6 times in isolation; a standalone `swiftc` probe of the encoder mechanism over 30 independent process launches, plus 12 launches of the production `.sortedKeys` path. Anthropic's structured-outputs documentation checked directly for the key-ordering guarantee the slice rests on. Arithmetic computed, not eyeballed.

**Refuted: 7.**

---

## Bottom line

The production code in this slice is right, and I want that stated plainly before the rejection: the prompt merge is faithful (all seven session rules byte-identical to the deleted `proposalSystem`), the schema nests without drift, `BriefReply` decodes correctly, Adjust genuinely rewrites both halves as the spec's "Confirm first" default required, and the wire really does put `dayPlan` before `greeting` — deterministically, 12 of 12 probe runs.

It is rejected on one thing: **the guard added by the punch list to prove the slice achieves its own purpose does not work, and the suite is red roughly 40% of the time because of it.** Two of my five full-suite runs failed, exit 65, zero restarts. The build note's "897 tests in 93 suites, exit 0, zero restarts" is reproducible only as a coin flip; it was a lucky run, not a green suite. Compounding it, the correction that guard was written to protect rests on an assertion about Anthropic API behavior that the vendor documentation does not make.

Fix is small — one line on the encoder, plus honest re-derivation of the ordering claim. Nothing here requires redesigning the slice.

---

## BLOCKERS

**1 · The ordering guard is nondeterministic and passes vacuously — the suite is red ~40% of runs · `AtlasTests/DailyBriefCallTests.swift:41-49` · CONFIRMED**

The test encodes with a bare `JSONEncoder()`. Production encodes with `.sortedKeys` (`Shared/Services/ClaudeClient.swift:231`). Foundation's `JSONEncoder` does not preserve keyed-container insertion order, so `JSONValue.encode`'s `entries.keys.sorted()` loop (`Shared/Services/JSONValue.swift:46`) is discarded — a fact the repo already documents in that file's own header at `JSONValue.swift:9-12`. Emission order is per-process hash-seeded.

There is a second defect layered on the first: `range(of:)` returns the *first* occurrence, and both `"dayPlan"` and `"greeting"` appear twice in the encoded schema — once in the top-level `required` **array** (order always preserved) and once in `properties`. When the seed emits `required` ahead of `properties`, the assertion is satisfied by the array literal and never inspects `properties` at all.

Measured, 30 independent process launches of a probe replicating `JSONValue` and the exact `briefSchema()` shape:

```
15  PASS — VACUOUS (read the `required` array; never inspected `properties`)
 8  PASS — actually inspected `properties`
 7  FAIL
```

Measured, the real full suite at `a01e48b`, five consecutive runs:

```
run 1 exit=0   restarts=0   897 tests passed
run 2 exit=0   restarts=0   897 tests passed
run 3 exit=65  restarts=0   FAILED — briefSchemaPutsThePlanBeforeTheNote()
run 4 exit=65  restarts=0   FAILED — briefSchemaPutsThePlanBeforeTheNote()
run 5 exit=0   restarts=0   897 tests passed
```

Assertion text, runs 3 and 4 identically: `DailyBriefCallTests.swift:48:37: Expectation failed: (plan.lowerBound → 254[utf8]) < (greeting.lowerBound → 44[utf8])`. Zero restarts throughout — this is a genuine assertion failure, not the SC1 crash signature.

**Failure scenario:** `scripts/git-hooks` runs the iOS suite and rejects on non-zero exit — CLAUDE.md names it as the only thing in the repo that catches the exit-65-alongside-a-green-line crash. This test reds ~40% of pushes at random with a message that reads like a schema regression. The rational response to a flaky red is `--no-verify`, which retires the gate that exists to catch a bug that was red on `main` for a week. Inversely: rename `dayPlan` back to `session` — the exact regression the punch list corrected — and roughly two-thirds of the green runs still pass, because they never read `properties`. The guard is more likely to fail when the code is right than to fail when the code is wrong.

**Fix:** set `outputFormatting = .sortedKeys` on the test's encoder — production's actual configuration. That is deterministic, and it sorts `properties` (`p`) ahead of `required` (`r`) so the assertion lands on the real keys. Verified: 12 of 12 launches PASS having inspected `properties`.

---

## MAJOR

**2 · The premise the whole correction rests on is undocumented vendor behavior, asserted three times as settled fact · `Shared/Services/CoachPrompts.swift:303-317`, `AtlasTests/DailyBriefCallTests.swift:36-40`, `docs/build-plan-2026-07-19.md:1719-1728` · CONFIRMED**

The punch list's first MAJOR was fixed by renaming `session` → `dayPlan` on the stated mechanism that "a structured reply is generated in schema order, so the model was writing the greeting before it had committed a single token of session."

I checked this against the sanctioned reference rather than the comment. Anthropic's structured-outputs documentation is **silent on key emission order** — it specifies schema *conformance*, and says nothing about whether generation follows `properties` order, `required` order, or neither. The claim is stated as certainty in three places ("the name is the mechanism", "insertion order cannot survive and `d` < `g` is the only lever there is").

There is also a logical gap independent of the vendor question: `ClaudeClient.RequestBody` always sends adaptive `thinking` (pinned by `ClaudeRequestEncodingTests.structuredCallsAlsoCarryThinking`). The model reasons in the thinking block *before emitting any JSON key*. Key order therefore controls **serialization** order, not **decision** order. The note claims the rename moved the session decision out of the thinking block; it cannot have. If the ordering premise is wrong, the original BLOCKER was never actually fixed — and nothing in this repo can detect that.

This is not "the code is wrong" — the wire ordering is real and deterministic. It is that the *reason* it is claimed to matter is unverified, and per the repo's own rule a documented mechanism that isn't the real one poisons the next slice.

**3 · `readDayForBrief` reaches Adjust and the staleness regenerate, and instructs the model to write *tomorrow's* session mid-workout · `Shared/Services/CoachPrompts.swift:64-76`, `Shared/Services/CoachService.swift:112-131`, `Atlas/Home/TodayCard.swift:381-397` · CONFIRMED**

The new paragraph says: *"when the header says training is DONE for today, **or a session is IN PROGRESS**, the plan you write is the NEXT session, not more work to pile on today."* It lives in `briefSystem()`, which `adjustBrief` also uses as its system prompt.

I verified the reachability directly. `completedSession` resolves to `WorkoutSession.completedToday`, which requires `sessionStatus == .completed` (`Shared/Models/WorkoutSession.swift:270-271`) — an **active** session returns nil. `hasProposal` (`TodayCard.swift:381-383`) excludes only `isDismissed` and `completedSession`, and the Adjust button at `:397` is gated solely on `!hasProposal || isGenerating`. So Adjust is live mid-session.

**Failure scenario:** Accept → Go → two of five slots logged. Facts render `# Today — <title> — IN PROGRESS right now`. Tony taps Adjust: *"shoulder feels off, swap the overhead press."* The system prompt orders the model to write the NEXT session; the user turn orders it to revise this one changing as little else as possible. Whichever wins, `adjust` writes `brief.proposal = reply.session` and `brief.greeting = reply.greeting` unconditionally — so a next-day plan can land in today's proposal, under today's `dayKey`, with Accept live, while a workout is running. The swap he asked for never happens.

Pre-CX2 `proposalSystem` contained no `readToday` at all, so this instruction class did not exist on either path. The build note itself flags the paragraph as *"a product decision made under a rejected finding"* — it is unasked-for scope that the spec's Build/Files/Confirm-first sections never mention, and it is the direct cause of this finding.

**4 · Adjust after Accept makes the greeting describe a plan no surface renders · `Atlas/Home/DailyBriefModel.swift:146-163`, `Atlas/Home/TodayCard.swift:381-397`, `Shared/Services/SessionEditing.swift:405-408` · CONFIRMED**

`hasProposal` does not exclude `briefStatus == .accepted` — only the *Accept* button is disabled at `:393`; Adjust at `:397` stays live. But once a session is materialized, `SessionEditing.todaysPlan` returns `.session(session)` for any non-abandoned session (`:405-408`), so the Log hub renders the materialized session, not `brief.proposal`.

**Failure scenario:** 07:00 brief → deadlift day. 07:30 Accept → `WorkoutSession` materialized. 08:00 Adjust: *"drop the overhead press."* `brief.proposal` is replaced and `brief.greeting` is replaced — and the greeting is visible on Home. The Log hub still lists overhead press off the materialized session. Home now reads "we've pulled the overhead press today" above a plan that still contains it. Before this diff Adjust-after-Accept quietly rewrote an invisible field; the diff makes half of it visible, which converts a no-op into the exact contradiction the slice exists to kill. Secondary: `briefStatus = .adjusted` overwrites `.accepted`, re-enabling the Accept button over an already-materialized session.

**5 · Adjust leaves the staleness banner up, and tapping it destroys the adjustment · `Atlas/Home/DailyBriefModel.swift:157-162`, `Shared/Models/DailyBrief.swift:174-191` · CONFIRMED (staleness half pre-existing)**

`isStale` is `checkIn.date > generatedAt` (`DailyBrief.swift:176`). `adjust` now writes `factsSnapshot` but touches neither `generatedAt` nor `checkInAt`.

**Failure scenario:** 07:00 brief. 10:00 check-in "shoulder sore" → banner "Check-in noted — update the call?". Tony taps Adjust at 10:02 instead. `adjust` builds fresh facts *including the 10:00 check-in*, gets a revised session, and stores that string. `generatedAt` is still 07:00, so the banner remains on screen above a plan that demonstrably already heard him. One tap runs `regenerate`, which overwrites the adjusted session and resets status to `.proposed` — his adjustment is gone with no confirmation.

The staleness behavior predates CX2. What is new is that `factsSnapshot` — documented as the exact string sent to Claude — now proves the coach saw the 10:00 check-in while `generatedAt` and `checkInAt` both assert it did not. The audit record is self-contradicting rather than merely stale.

---

## MINOR

- **Token-cap rationale is backwards, and one of the two "replaced" caps is still live** · `Shared/Services/CoachPrompts.swift:206-213`, `docs/build-plan-2026-07-19.md:1703-1706`. Computed: 4096 + 6144 = **10240**; `briefMaxTokens` = **12288**, i.e. 2048 *above* the sum. Both the comment and the note explain it as "not the sum … both outputs now share one thinking budget instead of paying for it twice" — sharing one pool argues for a number *below* the sum, and it is offered as the explanation for one above. Separately, `greetingMaxTokens` was not replaced: it is still live behind `generateGreeting`/`regenerateGreeting`. The value is safe (12288 ≤ 16000, the ceiling `ClaudeRequestEncodingTests.swift:65` enforces); only the reasoning is wrong.

- **`theCapCoversTwoOutputsAndOneThinkingPool` asserts no such thing** · `AtlasTests/DailyBriefCallTests.swift:195-201`. Assertions are `> 6144`, `> 4096`, `<= 16000`. A cap of **6145** passes all three while covering neither output plus thinking. The `>= 10240` floor that would pin the stated purpose is absent.

- **Every state write the punch-list commit added is untested** · `Atlas/Home/DailyBriefModel.swift:149-162`. `greetingAt = .now` and `factsSnapshot = facts` in `adjust`, `greetingAt = nil` in `regenerate` — the three lines that fix punch-list MAJOR #3 — have no coverage. Deleting `brief.greeting = reply.greeting` from `adjust` defeats the slice's entire premise and nothing goes red. `DailyBriefModel.coach` is a non-injectable `private let`, which is the structural reason none of it is testable; `ClaudeClient.transport` is injectable and `AtlasToolLoopTests` already uses that seam.

- **No test pins that `generateBrief` actually sends `briefMaxTokens`/`briefSystem`/`briefSchema`** · no test file references `CoachService` at all. Swapping `briefMaxTokens` → `greetingMaxTokens` in `CoachService.swift` leaves all 10 new tests green while every daily brief truncates mid-JSON — the slice's own named "one real trap."

- **Prompt-content tests detect deletion, not inversion** · `AtlasTests/DailyBriefCallTests.swift:122-134`. Inverting rule 4 from `"When readiness is low"` to `"When readiness is high"` keeps every assertion passing. I diffed the merged prompt against `main`'s `proposalSystem` by hand — all seven rules are byte-identical, so nothing was dropped; the tests just cannot see meaning.

- **The edited `PlanVisibility` doc-comment states a guarantee the renderer does not provide** · `Shared/Services/FactsRenderer.swift:42-52`. It says *"the call that must never see a plan is `CoachService.generateBrief`"*, but `todaySection` gates only the slot list on visibility — the `# Today` header still carries the session title and status unconditionally. Pre-existing (CX1), but this diff rewrote the comment restating it and added a paragraph pointing the model at that header.

- **`regenerateGreeting`'s new justification is false** · `Atlas/Home/DailyBriefModel.swift:104-105` claims *"There is no session being written here, so there is nothing for the note to disagree with."* The button is gated only on a brief existing (`HomeView.swift:38`), so it is live all morning with the day's proposal rendered directly below — an independent sample that can contradict it. The *behavior* is spec-authorized ("Leave `regenerateGreeting` alone"), so this is a comment-accuracy finding, not unbuilt scope.

- **Docs still present the deleted two-call pipeline as current** · `docs/coaching-home-m2-plan.md:98,108`, `docs/coaching-home-m3-plan.md:177`, `docs/build-plan.md:458`, `docs/slice-E-coach-actor.md:41` all name `generateProposal`/`adjustProposal` or "two sanctioned daily calls". The CORRECTED note claims the rename sweep covered "four comments and two build-plan rows"; it stopped at the build plan. Also `CoachPrompts.swift:98,107` still say the greeting is "1/day", and `readinessLens` at `:78-84` still says "both proactive calls".

- **The BUILT note describes a wire key that no longer exists** · `docs/build-plan-2026-07-19.md:1686-1691` says the shape is `{ greeting, session: … }`. CORRECTED renamed it to `dayPlan` but never amended the earlier paragraph, so the doc holds two mutually exclusive descriptions with no supersede marker on the stale one.

- **The spec's file list names a file with zero lines in the diff** · `docs/build-plan-2026-07-19.md:1661` lists `Shared/Services/ClaudeClient.swift` `proposalMaxTokens`; the constant lives in `CoachPrompts.swift` and `ClaudeClient.swift` is untouched. The implementation is right and the spec was wrong, but neither note flags it, so the list still reads as a satisfied checklist.

---

## Deferred (spec items intentionally not built — not defects)

- **`regenerateGreeting` left out of the merge.** Written evidence: spec line 1655-1656, *"Leave `regenerateGreeting` (greeting-only) alone."* Honored; `greetingSystem`, `greetingSchema`, `greetingMaxTokens` all still present and wired. (The *rationale comment* added for it is inaccurate — see MINOR above — but the decision itself is authorized.)

- **Nested schema rather than five flat sibling keys.** Spec line 1653 listed `greeting, focusTitle, whyLine, isDeload, slots` as siblings; built shape is `{ dayPlan: {…}, greeting }`. Written evidence: BUILT note lines 1685-1689 states and justifies the deviation (one schema definition, cannot drift from the decoding type), and two tests guard it. Sound call, documented — flagged only because it was decided unilaterally on the one artifact the spec spelled out field by field.

---

## Tried and failed to break

Stated explicitly, because a review that returns findings still has to say what held.

- **Production wire ordering.** I suspected `.sortedKeys` might not reach nested containers, making `entries.keys.sorted()` load-bearing and fragile. Verified with a 12-launch probe through the production encoder configuration: `properties` → `dayPlan` → `greeting`, byte-stable, every run, always having inspected `properties`. `d < g` holds. The design is correct; only the test is broken.

- **`briefSchema` ↔ `BriefReply` decoding.** Required `["dayPlan","greeting"]`, `additionalProperties: false`, `CodingKeys` maps `session = "dayPlan"`. The nested half calls `SessionProposal.schema` directly so it cannot drift from the type that decodes it; every optional is `anyOf [T, null]` with all keys in `required`, which Swift optionals decode identically whether null or absent. No mismatch.

- **The prompt merge itself.** Diffed `git show main:CoachPrompts.swift`'s `proposalSystem` against `briefSystem()`'s `# The session` block line by line. All seven priority rules and the "typically 3-6 slots / whyLine" trailer are byte-identical. No rule was silently dropped. The greeting half carries the length, voice, and lead-with-the-call instructions from `greetingSystem`.

- **CX1 regression through the shared facts builder.** The 17-line `FactsRenderer.swift` change is doc-comment only — no `renderedFacts`, `todaySection`, `planLines`, or `PlanVisibility` case behavior moved; byte output identical. `readToday` is byte-identical and still reaches the Coach tab, in-session sheet, and recap. No CX1 degradation.

- **Deleted-symbol sweep.** Full-tree grep for `proposalSystem`, `proposalSchema`, `proposalMaxTokens`, `generateProposal`, `adjustProposal`: zero live code or test references. Survivors are historical docs (reported above) and one deliberate labelled back-reference.

- **SwiftData persistence and migration.** No `@Model` property added, removed, renamed, or retyped — `DailyBrief` is untouched. The wire rename lives entirely in `BriefReply.CodingKeys` and is unwrapped to a bare `SessionProposal` before reaching `proposalData`, so pre-CX2 and post-CX2 briefs produce byte-identical blobs. Old rows decode and render. Nothing to migrate.

- **Partial/half-written state on a mid-flight throw.** Every mutation in all four paths is a straight-line synchronous block after the single `await`, on `@MainActor`, with `saveChanges()` last. A throw from `generateBrief`/`adjustBrief` reaches `catch` before any field is touched. `.truncated`, `.refused`, `.malformedResponse` all land the same way. No torn writes.

- **Re-entrancy on double-tap.** All four entry points check `!isGenerating` and set it with no `await` in between, on a `@MainActor` class, so check-then-set is atomic against MainActor interleaving. Two fast taps cannot double-fire; `defer` fires on cancellation too.

- **Dismissal interaction on the new adjust path.** `adjust` still passes `proposal?.excluding(dismissedSlots)` as the subject, and `brief.proposal = reply.session` still clears the set through the computed setter. Adding the greeting write after it changes nothing about that ordering.

- **Watch and web surfaces.** `AtlasWatch` builds clean; the watch never touches `DailyBrief`. Nothing under `web/src/lib/atlas/` changed, so no `docs/surfaces.md` §4 register row is owed. `DailyBriefRow` carries `greeting`, `greeting_at`, `facts_snapshot` — every field this diff writes reaches the hub.

- **Snapshot baselines.** The only view-file change is one comment in `HomeView.swift:74`. No `body`, layout, or chrome touched, so no re-record is owed. All snapshot suites ran green inside the 897 across five runs, `harnessIsDeterministic` and `harnessLeavesNoLiveViewBehind` included.

- **The reported snapshot-suite crash.** One reviewer reported 2 of 3 full runs crashing in `LogScreenSnapshotTests` with the SC1 shrinking-count signature. **Not reproduced** — five consecutive full runs, zero restarts, 897/93 every time. Refuted as a CX2 finding; most likely cold-simulator/fresh-DerivedData thrash in that agent's environment.

---

## Also refuted or dropped (7)

Reported by reviewers, cut after verification: the snapshot-suite crash (above, not reproduced); `@State` reset double-firing the daily call (pre-existing, acknowledged in the model's own doc, no concrete trigger); empty-`slots` dead-ending the UI (no `minItems` is pre-existing on `SessionProposal.schema`, speculative); the DevSeed `factsSnapshot` marker erasure (needs a pre-marker store never re-seeded — too narrow to act on); the `try`-vs-`?? ""` change "hardening an unreachable path" (true that `adjust` already guards it, but the change is strictly better and harmless, not a defect); no `output_config.effort` bounding thinking against the cap (pre-existing across every call site in the repo); and the 60-second `URLSession` timeout against a doubled 12288-token non-streaming reply — plausible and worth watching, but I could not measure real latency without an API key under the test host, so I will not assert it as a finding.

---

## What to do next

Minimum to lift the rejection:

1. `AtlasTests/DailyBriefCallTests.swift:41-49` — set `outputFormatting = .sortedKeys` on the test encoder, then run the suite 5+ times to confirm stability. This alone clears the BLOCKER.
2. Re-derive or soften the ordering claim in `CoachPrompts.swift:303-317`, the test docstring, and the build-plan note. If schema-order generation cannot be substantiated from Anthropic's documentation, say so — the rename is still harmless and probably helpful, but it should not be recorded as a proven mechanism, and the "moved the decision out of the thinking block" sentence is not true regardless.

Then the four MAJORs, which are fixable in place and do not block the next slice if you take them knowingly. Note that CX3 (already on the branch tip) supersedes the `readDayForBrief` paragraph behind MAJOR 3 — worth confirming it also removes the Adjust and regenerate exposure, not just the daily-brief wording.

I have not fixed anything. Say the word if you want the punch list worked.
