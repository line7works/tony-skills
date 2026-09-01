---
name: blueprint
description: Draft a build document in dependency-ordered, verifiable slices from a feature discussion — produces the doc that /build executes slice by slice and /signoff grades against. Use when the user says "draft a build doc", "blueprint this", "slice this up", "write the build plan", or finishes discussing a feature and wants it scoped into slices.
---

# Blueprint

The front of the loop. `/blueprint` draws the plans, `/build` frames them one slice at a time, `/signoff` inspects the work. This skill turns a feature discussion into the build document the loop's downstream skills — /build, /signoff, and /recheck — all consume, written for a builder who was never in the room.

**The spine.** The doc records what was decided; it does not decide. Every requirement traces to the discussion, the repo, or a question asked and answered here. The most useful doc is self-contained — real files, real interfaces, explicit out-of-scope, every criterion checkable — because a fresh session with no memory of this conversation must be able to execute it.

**The one unforgivable move is faux context:** padding the doc with plausible requirements, rationales, or criteria the discussion never established. Downstream, /build treats this doc as the only source of requirements and /signoff grades against it — invented detail becomes law. When something is unknown, ask or mark it open; never make it up.

## Step 1 — Harvest

Mine what already exists before asking anything:

- **The discussion:** decisions made, options rejected (record these — they are descope evidence), constraints stated, names used.
- **The repo:** the test command, existing components and conventions the slices should reuse, real file paths. Slices reference reality, not guesses.
- **Prior docs:** a `docs/<idea>-scope.md` scope doc for this feature if one exists (what /precon writes — harvest it first: its Decisions are settled ground, its Out of scope lines are descope evidence; match the doc to the named feature, and when more than one could match, list them and ask — never silently pick); a /wargame doc if one exists (its verified failure modes become constraints and acceptance criteria); an existing build doc for this feature (extend it — never fork a second plan).

## Step 2 — Interview

Ask about load-bearing gaps only — choices that shape architecture, data, user-visible contracts, or slice boundaries. Batch them into one round of a few questions, each with a recommendation attached. Small reversible gaps don't earn questions: decide, and record the assumption in the doc where builder and inspector will see it. Invoked cold with no prior discussion, this step *is* the discussion — interview until the shape is settled, then proceed.

## Step 3 — Slice

- **Size:** one slice = one /build invocation — a coherent piece one session completes and verifies in a sitting. When in doubt, smaller.
- **Order:** dependency-ordered — data before services, services before surfaces. The earliest slice that can prove the feature end-to-end comes as early as possible.
- **Ends wired in:** every slice leaves the system integrated and demonstrable. No slice whose output only matters if a later slice remembers to connect it.
- **Independently verifiable:** each slice carries criteria checkable at that slice, never "will be tested later."
- **Ceremony scales:** a change describable in one sentence gets told so — "this doesn't need a build doc" is a valid outcome. A modest feature gets two or three slices, not eight.

## Step 4 — Write the doc

Save to `docs/<feature>-build-plan.md` in the repo (inside /build's hunt path). The format is load-bearing — /build's contract and ledger, /signoff's punch list and sweep (which also writes recheck-headed clearing blocks), and /recheck's checklist assembly and its in-place `Status:` edits all key off it — so keep the load-bearing forms exact: the section names, the `Status:` label, the block headings, and the ·-separated line fields:

```
# <Feature> — build plan (<date>)

Intent: <what this is, who it's for, what it enables — the why the builder needs>
Constraints: <stack, conventions, test command, hard requirements>
Out of scope: <deferred item — reason it was deferred (this is /signoff's written evidence)>

## Slice A — <short name>
Goal: <one sentence>
Requirements:
- <R1 — traceable to the discussion>
Acceptance criteria:
- <AC1: one measurable end state> — verify: <existing test | new test at <path> | manual: <steps>>
Footprint: <files expected to change>
Not in this slice: <adjacent work that belongs elsewhere>
Depends on: <nothing | Slice X>
Status: not started

## Slice B — ...

## Build assumptions
## Deviations
## Discovered
## Handoffs
## Punch list
```

The last five sections start empty and belong to the other skills — /build appends assumptions, deviations, and discoveries; /signoff and /recheck append the punch-list blocks; /handoff appends its dated blocks to `## Handoffs`; the dated `WAIVED`/`REOPENED` lines are appended by whichever station receives the user's word; and inside the punch list, /build's own lines are limited to those two plus its dated `REBUILT` line. Scaffold them; never pre-fill them. Each slice's `Status:` line is likewise maintained downstream — /build sets `built`; /signoff, /recheck, and recorded user waivers set the verdict states.

## Step 5 — Read back and stop

Post the summary block below in chat: the slice map, open questions, every assumption made. The user corrects the map cheaply here — a wrong doc costs a build. Then stop. Never start building; "blueprint it and build slice A" in the invocation collapses that gate, the skill never assumes it.

## The rules

1. **Record, don't invent.** Every requirement traces to the discussion, the repo, or an answered question. An unanswered load-bearing question stays visibly open in the doc, never silently resolved.
2. **Write for a builder who wasn't in the room.** No "as discussed," no vocabulary the chat invented without defining, no pronouns pointing at the conversation. Real paths, real names.
3. **Criteria are checkable or they aren't criteria.** One measurable end state plus the stated check. "Works correctly" and "handles errors well" are goals — turn them into observable outcomes or leave them in Intent.
4. **Requirements say what, slices say when, the builder decides how.** Don't prescribe implementation detail the builder is better placed to choose — over-specification locks in bad solutions.
5. **Descoping is recorded with reasons.** Rejected options and deferred work go in Out of scope with the why — that written evidence is what keeps /signoff from flagging them as failures.
6. **Tests are part of the plan.** Criteria that can be tests name them; a slice with no runnable check is a smell worth flagging to the user before the doc ships.
7. **One living doc.** One build doc per feature, revised in place. Never fork a parallel plan; never rewrite the ledger sections' history — and any `Plan: inspected` lines under `Out of scope:` are /inspect's records: preserve them through every revision.

## Output

After writing the file:

```
BLUEPRINT: <feature>
Doc: <path>  ·  Slices: N  ·  Open questions: N  ·  Assumptions: N

Slice A — <one line>
Slice B — <one line>

Open: <questions the user still owes answers on, if any>
Assumed: <assumptions made, one line each, if any>
Next: /build slice A when ready.
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```

When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

## What NOT to do

- Don't invent requirements, rationales, or criteria the discussion never established.
- Don't write criteria a grader couldn't check.
- Don't prescribe implementation detail (the builder's altitude) — and don't leave load-bearing decisions unstated (guessing, moved downstream).
- Don't explode a small change into ceremony — recommend skipping the doc when it isn't needed.
- Don't fork a second plan when one exists — extend it.
- Don't pre-fill the ledger sections or write anything shaped like a verdict.
- Don't start building. That gate is the user's.
