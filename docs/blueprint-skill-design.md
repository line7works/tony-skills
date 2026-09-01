# Blueprint — design rationale (2026-08-01)

The front of the loop: `/blueprint` turns a feature discussion into the build
document that `/build` executes slice by slice and `/signoff` grades against.
Companion to `build-skill-v1-initial.md`, `build-skill-v1-research-comparison.md`,
and `build-skill-anthropic-alignment.md` — the research base for this skill is those
three docs; this one records only the decisions specific to Blueprint.

Tony's workflow being encoded: discuss the feature with the LLM until comfortable,
then ask for a build document "in proper slices so it's scoped out correctly."

## Name

**/blueprint.** Completes the construction loop: wargame (pre-mortem) → blueprint
(drawings) → build (framing) → signoff (inspection). No collision with existing
skills.

## Spine and the unforgivable move

Spine: **the doc records what was decided; it does not decide.** The mirror of
build's "the spec is the only source of requirements" — since downstream treats
this doc as law, the doc must contain only what was actually established.

Unforgivable move: **faux context** — the Scott Logic finding that agent-drafted
specs pad themselves with plausible detail that was never a real requirement, which
downstream then treats as law. For our loop this is doubly dangerous: /build will
faithfully build the invention and /signoff will faithfully grade against it.

## Research findings applied (sources in the two comparison docs)

1. **Interview before drafting.** Anthropic's "let Claude interview you" guidance;
   BrainGrid's data (a five-minute clarifying conversation replaces three or four
   rebuilds); the benchmark showing agents guess instead of ask on underspecified
   tasks in 55-68% of runs. Step 2 asks load-bearing questions only, batched, each
   with a recommendation; small gaps become logged assumptions instead.
2. **Self-contained spec shape.** Anthropic verbatim: the best specs "name the
   files and interfaces involved, state what is out of scope, and end with an
   end-to-end verification step" — and are executed in a fresh session. Hence
   "written for a builder who wasn't in the room" (adapted from Superpowers'
   junior-with-no-context framing, which forces completeness).
3. **Slice sizing.** METR task-length data (task length predicts failure, R²=0.83)
   plus field consensus: one slice = one /build invocation, dependency-ordered,
   earliest end-to-end proof first, every slice ends wired in (Harper Reed's
   no-orphaned-code rule, already in /build rule 6 — now enforced at planning time
   too).
4. **Checkable criteria.** "Once specs are captured as tests, the LLM can no longer
   hallucinate" (the only drift-stopper the field research credited besides scope
   limits); /goal's condition shape (one measurable end state + a stated check)
   borrowed as the criterion format. Each criterion names its verification, which
   feeds /build's contract directly.
5. **Ceremony scaling.** The loudest tooling failure (Kiro's sixteen acceptance
   criteria for a bug fix; Anthropic's "if you could describe the diff in one
   sentence, skip the plan"). Declining to write a build doc is a valid outcome.
6. **What/when vs how.** Both over- and under-specification are named failure
   modes; requirements state what, slices state when, the builder chooses how.
   Matches the Claude 5-generation de-prescription posture.
7. **One living doc.** Stale/forked specs get executed confidently (Augment
   finding); rule 7 keeps a single copy edited in place, ledger history protected.

## The interlock spec (what makes the three skills one system)

- **Location:** saved to `docs/<feature>-build-plan.md` — inside /build's existing
  hunt path (docs/, plan/, vault, session).
- **Slice anatomy** (Goal, Requirements, Acceptance criteria with named
  verification, Footprint, Not in this slice, Depends on) maps one-to-one onto
  /build's Step 1 contract fields — the contract becomes transcription plus
  boundaries rather than interpretation.
- **Ledger scaffolding:** Blueprint creates `## Build assumptions`, `## Deviations`,
  `## Discovered`, `## Punch list` empty. /build appends the first three, /signoff
  the fourth. Nobody hunts for where to write.
- **Descope evidence:** `Out of scope: item — reason` entries are exactly the
  "written evidence" /signoff rule 4 demands before Deferred is accepted — the
  loop's biggest false-BLOCKER source, closed at drafting time.
- **Wargame input:** Step 1 reads an existing war-game doc; verified failure modes
  become constraints and acceptance criteria.

## Status-field seam — RESOLVED (folds applied 2026-08-01, per Tony)

The template carries `Status: not started` per slice (harness doctrine: a feature
list with status-only edits). Tony approved the folds the same day the seam was
identified, before any baseline run (so no comparison contamination):
- **/build Step 5:** on a COMPLETE build, sets the slice's `Status:` line to
  `built`; PARTIAL and STOPPED leave it untouched.
- **/signoff punch-list step:** sets it to the verdict — `signed off`,
  `signed off with conditions`, or `rejected` — framed as a one-word state flag
  for the next build's preflight, explicitly not the verdict block (which still
  lives only in chat, preserving signoff's ledger-hygiene rule).
- **/blueprint Step 4:** one clause added noting the field is maintained
  downstream.

## Test plan (evaluation-first, three seeded scenarios)

1. **Rich discussion** — invoke after a real feature discussion. Grade: does every
   requirement trace to something actually said? Any faux context is a fail.
2. **Cold invocation** — "blueprint X" with no prior discussion. Grade: does it
   interview before drafting, or fabricate a plausible plan?
3. **Trivial feature** — a one-sentence change. Grade: does it decline the
   ceremony?
Then the pair test: run /build slice A against a Blueprint-produced doc and check
the contract writes itself from the slice anatomy without interpretation gaps.

## Open decisions for Tony

1. Name settled as /blueprint unless renamed.
2. ~~The Status-field seam~~ — resolved 2026-08-01, folds applied (see above).
3. Whether /wargame should be recommended inside Blueprint for risky features (a
   one-line "consider /wargame first" nudge) — left out of v1 to avoid ceremony.
