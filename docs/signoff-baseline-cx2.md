# SIGN-OFF: CX2 · One Claude call writes the note and the package

**Verdict: REJECTED**

- **Scope:** `git diff main...HEAD` on `feat/cx2-one-brief-call` — commits `3b7d529` (build) and `a01e48b` (punch-list corrections). 10 files, +539/−71.
- **Spec:** `docs/build-plan-2026-07-19.md` lines 1642–1753 (spec, BUILT note, CORRECTED note).
- **Depth:** LEAN + `tests` lens (4 independent reviewers). The extra lens was added because the CORRECTED note claims new tests pin three previously-found MAJORs.
- **Method:** Executed. Reviewed in a clean worktree at `a01e48b` (the working tree holds in-progress CX3 work that would have corrupted the read). Full iOS suite run; the ordering test run 22 times in the simulator; the encoder mechanism probed in 40 standalone processes.

---

## Bottom line

The merge itself is sound: one call, one prompt, one schema, every session rule carried over byte-identical, the deleted symbols genuinely gone, no persistence or cross-target break, and the token cap arithmetic correct. But the slice cannot be signed.

Two blockers. First, the test the CORRECTED note presents as the guard for the slice's central mechanism is nondeterministic — it fails about half of runs, and the pre-push hook rejects on non-zero exit, so `main` goes red at random. Even when green it frequently passes for the wrong reason. Second, the `readDayForBrief` paragraph — scope the spec did not ask for — breaks the shipped check-in staleness banner: tapping "update the call" mid-workout now asks the coach for *tomorrow's* session.

Underneath both sits the same problem: the documented ordering mechanism is not the real one, and the real one is weaker than the note claims.

---

## BLOCKERS

### B1 · The ordering guard is a coin flip, and it takes the suite with it — CONFIRMED
`AtlasTests/DailyBriefCallTests.swift:41-49`

`briefSchemaPutsThePlanBeforeTheNote` encodes with a bare `JSONEncoder()` (line 43) and compares byte offsets. `JSONEncoder` without `.sortedKeys` emits a keyed container in the backing dictionary's hash order, which Swift randomises per process. `JSONValue.object`'s `for key in entries.keys.sorted()` (`Shared/Services/JSONValue.swift:46`) orders the *encode calls*, not the emitted bytes — as `JSONValue.swift:9-12` states in its own doc comment.

**Measured directly, not inferred:**

| Harness | Result |
|---|---|
| `-only-testing:…/DailyBriefCallTests`, 10 simulator runs | **5 failed**, exit 65 |
| Standalone probe replicating `JSONValue.encode`, 40 processes | **8 failed (20%)**; key order visibly permutes |
| Full suite, 1 run | passed, exit 0, 0 restarts (a lucky seed) |

Observed failures, byte offsets: `(plan → 241) < (greeting → 31)`, `(254) < (44)`, `(225) < (15)`.

Two distinct consequences:

1. **`main` will go red at random.** `scripts/git-hooks` rejects on non-zero exit — roughly half of pushes fail on correct code. This repo already lost a week to a red suite nobody trusted (SC1); this reintroduces exactly that failure class.
2. **The guard does not guard, even when it passes.** The probe caught runs like
   `PASS {"required":["dayPlan","greeting"],"properties":{"greeting":…,"dayPlan":…`
   — green while the property order was *wrong*, because the first `"dayPlan"` match came from the insertion-ordered `required` array rather than from `properties`. And the bytes that actually reach the API come from `ClaudeClient.send`'s `.sortedKeys` encoder (`ClaudeClient.swift:230-232`), which this test never uses: switch `.sortedKeys` off and the wire order goes random while the test keeps passing at its usual rate.

Production ordering is correct today — `.sortedKeys` is set, and `dayPlan` < `greeting` — but nothing in the suite verifies the thing that makes it correct.

### B2 · `readDayForBrief` breaks the shipped check-in staleness banner — CONFIRMED
`Shared/Services/CoachPrompts.swift:64-77` · `Shared/Models/DailyBrief.swift:188-190` · `Atlas/Home/TodayCard.swift:67,290`

`wantsFreshProposal(checkIn:dayIsDone:)` takes `dayIsDone: completedSession != nil`, and `completedSession` is `WorkoutSession.completedToday(in:)` — which is nil for an **active** session. The banner therefore fires mid-workout by design.

Failure path:
1. 07:00 brief, "Heavy pull day". Accept → a `WorkoutSession` exists.
2. 08:00 he starts it (`.active`), logs two sets, feels wrecked.
3. 08:20 he saves a fatigued check-in. `isStale` → true, `dayIsDone` → false → banner: *"Check-in noted — update the call?"*
4. He taps it. `regenerate` calls `generateBrief`; the facts header renders `— IN PROGRESS right now` (`FactsRenderer.swift:236`).
5. `readDayForBrief` instructs, unconditionally for that case: *"when the header says training is DONE for today, or a session is IN PROGRESS, the plan you write is the NEXT session… the greeting speaks to the work he just did rather than sending him back to the gym."*

The banner's entire purpose — cut today's loads after a bad check-in — is unreachable on the one path it exists for. The brief stores tomorrow's session under today's `dayKey` with a greeting congratulating him on a workout he is two sets into. Pre-CX2 `proposalSystem()` had no day-awareness and re-prescribed today with the back-off, correctly.

This is a regression caused by the `readToday` → `readDayForBrief` work, which the BUILT note itself advertised as "one thing the merge added beyond the spec."

---

## MAJOR

### M1 · The CORRECTED note's stated mechanism is not the real one, and the real one is weaker than claimed — CONFIRMED
`docs/build-plan-2026-07-19.md:1719-1728` · `Shared/Services/CoachPrompts.swift:303-320`

Three separate problems with the same paragraph:

- **`keys.sorted()` contributes nothing.** The comment says the order comes from `JSONValue.object`'s sort "and `ClaudeClient` sets `.sortedKeys` on top." It is the reverse: `ClaudeClient.swift:231` is the *only* thing ordering the wire bytes. The slice's mechanism rests on one line in another file that the comment describes as belt-over-braces — precisely the comment that gets simplified away later.
- **Schema key order is not a documented generation-order guarantee.** JSON Schema `properties` is an unordered map, and Anthropic's structured-outputs contract documents no ordering guarantee (checked against the repo's sanctioned `claude-api` reference: it covers `output_config.format`, schema limits, `additionalProperties`, caching, refusals, token limits — and says nothing about key order determining output order). The claim is asserted, not sourced, and nothing here tests it against a live model.
- **Adaptive thinking runs to completion before the first output token.** `RequestBody.thinking` is a non-optional stored property with `type = "adaptive"` (`ClaudeClient.swift:299-327`), pinned by `structuredCallsAlsoCarryThinking`. The model has already reasoned about both halves before it emits a single character of `dayPlan`. So "the model was writing the greeting before it had committed a single token of session" cannot describe this request shape, and the mechanism the note names as the failed one ("honored inside the thinking block") is what still happens and cannot be turned off on this path.

The rename is harmless and probably mildly helpful. What is not harmless is recording it as a proven mechanism: **CX3 is specified to add a rest-day field, and this note tells its author that `d` < `g` is "the only lever there is."** That is a false constraint on the next slice's naming, derived from a mechanism that does not work the way it is written down.

### M2 · Adjust rewrites the greeting without being shown the greeting it replaces
`Shared/Services/CoachService.swift:103-124` · `Atlas/Home/DailyBriefModel.swift:150`

The adjust user turn carries `facts`, `# Current proposal (JSON)`, and the lifter's note — but no `# Current greeting`. It nonetheless instructs the model that "a note about the old one reads as the coach not having heard him," reasoning about text it was never given. `adjust` then does `brief.greeting = reply.greeting`, overwriting in place with no history.

07:00: *"Happy Wednesday, Tony — you're carrying fatigue from Tuesday's pull, so today backs off."* 12:00 Adjust: "swap squats for leg press." The replacement is written blind — the fatigue framing, the deload call and the name are all at the model's discretion to re-derive or drop, and the original is gone. The proposal gets an anchor precisely so the model changes as little else as possible; the greeting gets none.

### M3 · Adjust restamps `factsSnapshot` but not `generatedAt` or `checkInAt` — the audit row now contradicts itself
`Atlas/Home/DailyBriefModel.swift:156,161` · `Shared/Models/DailyBrief.swift:45-50,174-190`

`main`'s `adjustProposal` did not touch `factsSnapshot`. This diff adds the write and moves neither timestamp.

07:00 brief, no check-in → `generatedAt=07:00`, `checkInAt=nil`, `factsSnapshot=F₀`. 12:00 fatigued check-in. 12:05 Adjust. The row then claims *both* that the coach saw no check-in (`checkInAt=nil`, documented as "the check-in included at generation") and that it was handed one (`factsSnapshot=F₁`, which contains `# Today's check-in`, documented as "the exact facts string sent to Claude"). `factsSnapshot` is single-valued, so F₀ is unrecoverable — "what did the coach know this morning?" is no longer answerable, which is the field's entire stated reason for existing.

Compounding: `isStale` reads `generatedAt`, still 07:00, so the banner keeps offering "update the call" for a plan that already heard the check-in. Tapping it runs `regenerate`, which discards the adjustment *and* the adjusted greeting, and resets `briefStatus` to `.proposed`.

### M4 · The punch list's third fix ships with zero tests — CONFIRMED
`Atlas/Home/DailyBriefModel.swift:83,156,161`

The note claims adjust now stamps `greetingAt`/`factsSnapshot` and regenerate clears `greetingAt`. Verified: no test anywhere exercises `DailyBriefModel.adjust`, `regenerate`, or `generateIfNeeded`, and there are no `CoachService` tests at all. The only related hits are `PostWorkoutStateTests.swift:111-120` (sets `greetingAt` by hand to test the `??` accessor) and `SupabaseRowTests.swift:108-116` (round-trip). Each of these one-line reversions keeps all 897 tests green:

- delete `brief.greetingAt = .now` → an 18:15 adjust renders under 07:00 again (the exact reported bug);
- delete `brief.greetingAt = nil` → `greetingWrittenAt` reports earlier than `generatedAt` again;
- delete `brief.factsSnapshot = facts` → the audit invariant breaks silently.

### M5 · `readDayForBrief` is inert for a day logged without a session, and the guard it replaced covered that case
`Shared/Services/CoachPrompts.swift:64-77` · `Shared/Services/FactsRenderer.swift:148-155` · `Shared/Services/ContextAssembler.swift:268`

`todaySection` appends a status suffix only `if let session = today.session`, so a day logged through the Log hub with no session renders `# Today` as a bare header plus lifts — no DONE/IN-PROGRESS marker. `readDayForBrief` gates every instruction on that header, so it does nothing. Meanwhile `readToday`'s content-based guard — *"You can see their workout; never claim otherwise"* — was dropped from the brief path.

Concrete: he quick-logs a full chest day without starting a session, opens Home for the first time that evening, `generateIfNeeded` fires, and the brief prescribes a fresh full session on top of it while the greeting can again claim it cannot see his workout. That is the original gf16-1b-adjacent report, reopened. Note the asymmetry: `regenerateGreeting` still uses `greetingSystem`, which still keeps the guard.

### M6 · A decodable-but-degenerate reply latches a dead card for the rest of the day, and now blanks both halves
`Shared/Services/SessionProposal.swift:134` · `Atlas/Home/DailyBriefModel.swift:48-56,132-149`

`slots` has no `minItems`, and `BriefReply.greeting` is a non-optional `String` that accepts `""`. `{"greeting":"","dayPlan":{…,"slots":[]}}` decodes cleanly, gets inserted, and `shouldGenerate` then returns false for the rest of the Pacific day — no retry until midnight. The card renders with an empty title and a live Accept button that silently does nothing.

Before CX2 this was survivable: a bad proposal call still left a real greeting from the other call. One merged reply now blanks both at once. Same hole on adjust, which guards its *input* (`!current.slots.isEmpty`) but not its output — a zero-slot adjust reply wipes the plan and then permanently disables adjust, a one-way door.

### M7 · The web renders the "next session" plan under today's date with no guard
`web/src/app/(app)/briefs/page.tsx:53-80` · `web/src/components/dashboard-view.tsx:166-186`

Mobile hides a next-day proposal behind `recapBlock` once a session is completed. The web renders `proposal.focusTitle`/`whyLine`/`slots` unconditionally under `dayHeading(b.day_key)`; `livePlan()` filters dismissals only and has no notion of the day being over. So Thursday's dashboard shows Friday's session titled under Thursday, above a Thursday he already trained.

Per `docs/surfaces.md`, absence is a scope decision but disagreement is a defect, and no register row covers "is this brief's plan still current." CX2 created the condition that needs one.

---

## MINOR

- **`required` order is pinned by nothing.** `DailyBriefCallTests.swift:54` calls `.sorted()` before comparing, discarding the one container in the schema that *does* survive encoding in insertion order (`CoachPrompts.swift:327`). Reorder it to `["greeting","dayPlan"]` and the suite stays green.
- **The cap comment's arithmetic argues the opposite of what it says.** `CoachPrompts.swift:206-213`: 4096 + 6144 = 10240, and 12288 − 10240 = **+2048**. The cap went *up*; the comment presents it as a saving from sharing one thinking pool. (The value itself is correct — see below.)
- **The cap test adds about one bit.** `DailyBriefCallTests.swift:195-200` asserts `> 6144`, `> 4096`, `<= 16000`; the last is already covered by `ClaudeRequestEncodingTests`. `briefMaxTokens = 6145` passes a test named `theCapCoversTwoOutputsAndOneThinkingPool`. The specific value 12288 is pinned by nothing.
- **Adjust turn contradicts its own system prompt.** `CoachService.swift:118-123` says "not a fresh morning note. Do not open it as a greeting"; `CoachPrompts.swift:238,276` says "You are writing the lifter's whole morning in one shot" and "the note that opens the lifter's day." System text usually outranks a user turn — and the new `greetingAt` stamp makes an 18:15 "Morning, Tony…" visible where it previously was not.
- **`readToday` under `.hidden` is fixed on one of the two calls that has it.** `greetingSystem` still splices it (`CoachPrompts.swift:115`) and `regenerateGreeting` still renders at `.hidden`, so two of the three defects the punch list enumerated are still live on the re-read path. The `readDayForBrief` doc comment asserts a repo-wide invariant ("every brief call renders at `PlanVisibility.hidden`") that is true, but pairs it with a claim the greeting path contradicts.
- **Stale references to the two-call shape.** `Atlas/DevSeed.swift:106` ("what a real morning's two Claude calls would have") is a fifth instance the "four comments renamed" claim missed; `docs/build-plan.md:458`, `docs/coaching-home-m2-plan.md:98`, `docs/slice-E-coach-actor.md:41`, `docs/coaching-home-m3-plan.md:177` still name the deleted functions.
- **Force casts can crash the host rather than fail.** `DailyBriefCallTests.swift:21-24,54-56,65,78-81` use `as!` throughout. A trap produces `Restarting after unexpected exit` and a summary counting only the last launch — the shrinking-count symptom `CLAUDE.md` warns about.
- **One near-vacuous assertion.** `#expect(!CoachPrompts.greetingSystem.isEmpty)` on a `static let` literal cannot fail; symbol deletion is a compile error, not a test failure.
- **Doc count drift.** The BUILT note says 10 tests added; `DailyBriefCallTests` has 13.

---

## Deferred (spec-sanctioned, not defects)

- The `readDayForBrief` "the plan is the NEXT session" paragraph is explicitly marked as superseded by CX3 once the call can say "take the day off." B2 and M5 are about it being wrong *now*, not about it being temporary.
- Rotation, rest-day tier, and warm-up/tonnage work are CX3 and later.

---

## Tried and failed to break

- **Deleted symbols are genuinely gone.** `proposalSystem` / `proposalSchema` / `proposalMaxTokens` / `generateProposal` / `adjustProposal` return zero live-code hits across the entire tree including `AtlasWatch/`, `AtlasWidgets/`, `LiveActivity/`, `web/`, `scripts/`, `supabase/`, `fastlane/`. Remaining hits are doc prose and two deliberately-historical comments.
- **Call-site migration is complete.** `generateBrief` has exactly two callers, `adjustBrief` one, `generateGreeting` one (the preserved re-read). No surface calls a migrated path with old expectations.
- **The "Confirm first" question is answered in both directions.** Request side: `adjustBrief` uses `briefSystem()` + `briefSchema()` and orders a greeting rewrite. Response side: `adjust` assigns both halves. No path revises the session without the note.
- **Persistence is safe.** `CoachMemory.swift`'s entire diff is one word in a doc comment; no stored property added, renamed, or made non-optional. `DailyBrief` is untouched. Old proposal blobs decode byte-identically — `SessionProposal` gained no fields, and Supabase columns, `blobs.ts`, and `gen_fixtures.swift` are all unchanged.
- **CX1's other coach surface is intact.** `FactsRenderer.swift`'s diff is comment-only. `readToday` still exists and still feeds `greetingSystem`, `recapSystem`, and the chat builder; `readDayForBrief` is a new sibling, not a replacement. `PlanVisibility` still has two cases and `renderedFacts` still defaults `.hidden`.
- **Watch and widgets are untouched** and cannot see a brief at all (`AtlasWidgets` never compiles `Shared/`).
- **Snapshot baselines correctly not re-recorded** — no view file changed beyond one comment line in `HomeView.swift`.
- **Token arithmetic is correct.** `briefMaxTokens = 12288`; worst-case JSON output computed at ~730 tokens (6 slots × ~70, greeting ~250, envelope ~60), padded to 1000. Thinking headroom 11288, versus 5664 and 3846 on the two calls it replaces. `.truncated` fires only on `stop_reason == "max_tokens"`, which now needs an ~11.3k-token thinking block. **The spec's "one real trap" is genuinely closed** — only the comment justifying the number is wrong.
- **Prompt merge is faithful.** `proposalSystem` on `main` diffed line-by-line against `briefSystem`: all seven priority rules, the deload clause, the `isHero` clause, the catalog constraint, the slot-count guidance and the whyLine sentence survive byte-identical. The greeting half keeps its length, voice, and lead-with-the-call rules. The merge is purely additive; M5 is the only substantive loss.
- **Decoding is sound.** `BriefReply.CodingKeys` maps `session → "dayPlan"` correctly; nothing on the path is force-unwrapped; every `DecodingError` funnels to `.malformedResponse`.
- **Concurrency is clean, and `regenerate` is safer than `main`.** `async let` is gone — no dangling child task, no lost cancellation. All four methods are `@MainActor` with an immediate `defer { isGenerating = false }` and no `await` between the guard and the assignment. `main` assigned the greeting and *then* awaited the proposal, so a throw left a new note beside an old plan on a live `@Model`; the merged version assigns both after one await. Fixed by accident, but fixed.
- **Nested schema keeps one definition.** `theSessionHalfIsTheProposalSchemaItself` compares `.sortedKeys` serialisations and is deterministic (it normalises through `JSONSerialization`) — unlike its flaky sibling. Catalog narrowing reaches `exerciseId.enum` through the nesting.

---

## What to fix before this can be signed

1. **B1** — point the ordering test at the encoder that actually ships (`.sortedKeys`), and assert order *inside* `properties` rather than on first occurrence in the whole document, so the `required` array cannot satisfy it by accident.
2. **B2** — make `readDayForBrief` inapplicable when the regenerate came from a staleness banner on an in-progress day, or drop the paragraph and let CX3 reintroduce it deliberately.
3. **M1** — correct the mechanism note: `.sortedKeys` is the lever, key naming is a weak secondary, and adaptive thinking already gives the model both halves before it emits anything. CX3 should not inherit the "d < g is the only lever" constraint.
4. **M2–M4** — pass the current greeting into adjust; make the adjust timestamps mutually coherent; add tests for the three stamping writes.
