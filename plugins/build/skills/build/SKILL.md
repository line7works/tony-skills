---
name: build
description: Execute one slice of a build document inside strict boundaries — the spec is the only source of requirements, reuse before writing, no stubs, honest stops. Use when the user says "build slice X", "build the next slice", "execute the plan for X", or hands over a build/phase doc and names a slice to implement.
---

# Build

One slice of the build doc, made true. `/blueprint` draws the plans, `/build` frames one slice, `/signoff` inspects it. This is the middle of that loop: the crew that shows up with one page of the blueprints, builds exactly what is on that page with the materials already on site, and calls for inspection when done.

**The spine.** The spec is the only source of requirements. The builder's job is to make the slice doc true, not to make the software better. Every change must trace to a line of the slice; anything that doesn't is drift (cut it) or a discovery (log it, don't build it).

**The one unforgivable move is fake completeness:** a stub, a vacuous test, or a TODO presented as a finished slice. It poisons the inspection that follows. Honest incompleteness — "80% done, here is the missing 20% and why" — is a good outcome. Fake completeness is the worst possible one.

## Step 1 — Contract

Find the build doc: `docs/<feature>-build-plan.md` (what `/blueprint` writes), any phase/slice doc under `docs/` or `plan/`, the vault project folder, or the plan established in this session — that order is priority: the first tier that yields a doc wins, and two candidates inside one tier is a stop-and-ask, never a silent pick. Resolve the named slice. If the doc or the slice doesn't resolve, stop and ask. Never build from a spec you invented or reconstructed from memory.

Then post the contract in chat before touching code:

- **In scope:** each requirement of the slice, and how it will be verified (existing test, new test, manual exercise). Verification is designed before the code exists.
- **Not authorized:** what stays untouched — neighboring slices, shared files outside the footprint, schema, anything the slice doesn't need.
- **Reuse:** the existing components this slice will build on.
- **Footprint:** files expected to change. **New:** dependencies or components that must be written fresh, each with a one-line justification. A dependency not in the contract does not get added later.

Against a blueprint-format doc, the contract is transcription plus boundaries, not interpretation: the slice's Requirements become In scope, each requirement paired with the acceptance criterion that checks it (state the pairing; a requirement no criterion checks is a gap to flag), and each criterion's stated verify line becomes how it's verified; its Footprint is the Footprint; Not in this slice and the doc-level Out of scope lines both feed Not authorized — "seeds" is additive: the contract may add boundaries, never drop one the doc states; Reuse transcribes the components the doc's Constraints and requirement lines name, verified against the repo, and New is what rule 3's search then fails to find — an empty New is a search result, not a default; and Depends on is checked in preflight. Don't re-derive boundaries the doc already states.

The explicit authorized / not-authorized form is load-bearing — a scoped per-task boundary statement is the one form of prose instruction measured to actually hold scope. Make the contract self-contained (spec path, slice, boundaries) so a fresh session could execute it unchanged. Scale ceremony to the slice: work describable in one sentence gets a three-line contract, not a form. The contract states assumptions and proceeds; it does not wait for approval. Load-bearing gaps are the exception (rule 2).

## Step 2 — Preflight

- **Prior slice's standing:** read the punch list in the build doc. Under `signed off with conditions`, the named BLOCKERs and MAJORs are fixed or waived before new framing goes up — fixed meaning cleared on the record by `/recheck` (or the sweep), the loop's clearing stations, never by the fixer's or the user's bare word (the user's word waives; it doesn't fix). A waiver is real only as a `WAIVED (per user) · <YYYY-MM-DD> · severity · file:line · claim` punch-list line — any named finding can carry one, only the user's word creates or revokes one (revocation: `REOPENED (per user) · <YYYY-MM-DD> · file:line · claim`), and the latest-dated record for an item (recheck line, dated `WAIVED (per user)` line, or `REOPENED (per user)` line, matched on `file:line` + claim) decides its state. A record with no claim field matches on `file:line` alone — only where a single entry holds that `file:line`; at a shared location it decides nothing and the ambiguity goes to the user. The claim field is its own `·`-separated field, parentheses wrapping it are not part of it, and a parenthetical glued to the `file:line` is a legacy tag, not a claim. Chat-only waivers don't count. When the user grants or revokes one here, append the line, then update that slice's card from what remains open, waived items excluded. Appended `WAIVED`/`REOPENED` lines land at the ledger's home's tail, outside any block — the home is where the doc's punch-list blocks already live, or the `## Punch list` section when none exist yet, and when blocks sit in more than one place the latest-dated block's location is the home (on a date tie, the later in the file): one home per doc, never split; when records share a date, the later in the file wins — appends only land at the home's tail, so file order is time order.
- **Dependency standing:** read the slice's `Depends on:` line — every slice named there must stand `built` or better, and one standing `signed off with conditions` — or `built` with uncleared BLOCKER/MAJOR entries, a rebuild never re-verified — carries the same fixed-or-waived demand as the prior slice. `not started` or `rejected` is a stop-and-report, never a foundation.
- **Failed foundation:** the immediately prior slice standing `rejected` is a stop-and-report — no framing on a failed foundation without the user's word. A rebuild does not launder that state: the immediately prior slice standing `built` with uncleared BLOCKER/MAJOR entries carries the same fixed-or-waived demand before framing.
- **Feature branch confirmed.** Never build on main.
- **The before photo:** run the project's test suite once and record the result. Without it, "prior slices still green" at the end is an assertion, not a fact.
- **Context gate:** if this session is already long or polluted with failed approaches, say so and recommend a fresh session. The contract is written to survive the move.

## Step 3 — Build

The session builds; no subagent ceremony — independence belongs to the inspector, not the builder. Governed by the rules below. Checkpoint commit at natural boundaries so a bad direction is revertible. Local commits only; the git gates are the user's.

## Step 4 — Verify

Earn the claim of done: execute the verification the contract named for each criterion, and record what ran and what it showed. A criterion that couldn't be exercised is reported as unexercised, never implied as done.

Then the mechanical self-checks — necessary, not sufficient:

- Grep the diff for TODO / FIXME / HACK / PLACEHOLDER / "not implemented". Any hit means not done.
- Diff the dependency manifest against the contract. Anything new the contract didn't name is a violation to fix, not to explain away.
- Rerun the before-photo suite. Prior slices stay green.

Keep bulk output out of context: redirect test and build output to a file and read back the summary lines (`> /tmp/run.log 2>&1`, then grep).

## Step 5 — Report and stop

Write the ledger into the build doc — `## Build assumptions`, `## Deviations`, `## Discovered` — one dated entry block per build, one line per item, additive-only. Deviation entries carry their authority: `per user` — meaning the user's answer sanctioned this specific change, not merely that a stop-and-ask got an answer — or `builder call`; unlabeled reads as builder call downstream, so label honestly. `## Build assumptions` entries may carry the same labels with the same meanings — a user-answered gap-fill is `per user` there too, and /signoff honors it. On a COMPLETE build, also set the slice's `Status:` line to `built` (PARTIAL and STOPPED leave it untouched) — and when that overwrites `rejected` or `signed off with conditions`, append the punch-list line `REBUILT · <YYYY-MM-DD> · <slice> — open findings need re-verifying against the new code` at the ledger's home's tail (Step 2's placement sentence defines the home); the entries stay open and visible. Beyond that line, the user-granted `WAIVED` / `REOPENED` lines, and the card update Step 2 commands after a waiver grant or revocation — a recorded user ruling, not the builder's verdict — never touch the `## Punch list` history, and never write anything shaped like a verdict: the builder writes intentions, the inspector writes signatures.

Emit the `BUILD:` block. Offer `/signoff`; never run it. The user can collapse the gate in the invocation ("build slice A and sign it off"); the skill never assumes it. A stop is a real end of turn — never infer permission to continue from anything short of the user's actual word.

## The rules

1. **Every change traces to a spec line.** No trace: drift (cut) or discovery (log). This also cuts gold-plating — extra config, premature abstraction, and unrequested edge handling are drift wearing a hard hat.
2. **The gap protocol.** A *clarification* — the spec is silent, any reasonable reading works, the choice is local and reversible — gets decided and logged. A *behavior change* — acting requires the spec to say something it doesn't, or the choice is architectural, irreversible, or shapes a contract later slices build on — stops and asks. An unlogged assumption is a defect. And if implementation reveals the plan itself is wrong, stop and report: never silently build the corrected version, and never knowingly build the wrong one.
3. **Reuse before writing.** Search the repo before writing any new component or helper — and search before concluding something doesn't exist; one failed grep is not evidence of absence. New code carries its one-line justification into the report.
4. **No stubs, ever.** If the slice can't be finished, stop and report the honest state.
5. **Descoping is a deviation, reported.** Never absorbed because a requirement turned out hard.
6. **No orphaned code.** The slice ends wired in — nothing dangling that a later slice must remember to integrate.
7. **Blast radius.** Feature branch; no migrations against real databases; shared-file rewrites flagged in the contract; prior slices stay green against the before photo.
8. **Thrash limit: two.** Two failed attempts at the same problem means stop, report, and recommend a fresh-context resume. The polluted context is the disease; attempt three from inside it is the anti-pattern.
9. **Report faithfully.** The BUILD block states what ran and what didn't. Never let "wrote the code" imply "watched it work."

## Output

Report in chat. Compact — this runs after every slice and must stay fast to read:

```
BUILD: <slice/phase>
Status: COMPLETE | PARTIAL (honest state) | STOPPED (blocked on <what>)
Spec: <path · slice>  ·  Contract: held | deviations: N  ·  Suite: <before → after>
Method: <how each criterion was exercised; self-checks run>

Bottom line: <2-3 sentences. What got built, what state it is in, what to do next.>

Built        <requirement · file:line · how verified>
Deviations   <narrowed or changed vs spec, each with why · per user | builder call — the authority label is each line's final ·-field, a placement rule, not a template convention>
Assumptions  <gaps the spec left open, decided and logged>
Discovered   <out-of-scope work found — logged, not built>
New          <components/deps written fresh · justification>
Ready for /signoff: yes | no (<why>)
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```

Omit empty sections. `Method`, `Bottom line`, and `Ready for /signoff` appear in every report.

When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

## What NOT to do

- Don't invent requirements, and don't build from a spec reconstructed from memory.
- Don't write stubs or vacuous tests and call the slice done — the self-checks are necessary, not sufficient, and the inspector is coming.
- Don't absorb descoping silently, and don't gold-plate.
- Don't add a dependency the contract doesn't name.
- Don't write new what a search would have found.
- Don't touch punch-list history beyond the appends Steps 2 and 5 sanction, and don't write anything shaped like a verdict.
- Don't push, open a PR, or merge — those gates are the user's, always.
- Don't run /signoff on your own build unless the invocation collapsed the gate.
- Don't take attempt three. Two failures at one problem is a stop.
- Don't continue past a stop because something looked like approval.
