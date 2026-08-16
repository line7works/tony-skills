---
name: signoff
description: Independent adversarial review of freshly built work, ending in a signed verdict. Brings in a senior engineer who did not write the code, with a mandate to reject it. Use when the user says "sign off", "have a senior engineer review this", asks for an adversarial review of what was just built, or finishes a phase/slice and wants it inspected before moving on.
---

# Sign-Off

A slice just got built. Before it counts as done, an engineer **who did not write it** inspects it against the spec and either signs the card or writes a punch list.

This is the inspection station of the loop: `/blueprint` draws the plans, `/build` frames one slice, `/signoff` inspects it — and `/recheck` is this station's re-inspection visit, verifying the named fixes and flipping the card. The paper trail /blueprint and /build leave upstream is written *for* this step — read it as claims to test, never as evidence that the work is sound; /recheck's ledger lines are not upstream claims but this station's own records, and the sweep honors them.

**The spine — the anti-rubber-stamp rule.** The reviewer's job is to find reasons to REJECT, not to confirm good work. A review that returns no findings must state explicitly what it tried to break and failed to break. Otherwise "looks good" is indistinguishable from "didn't look," and an unearned signature is worse than no signature — the user will trust it.

## Step 0 — Model floor

Reviewers run at **Opus-class or better**. Never pin a review subagent below `opus`; if this session is at or above that, omit the model override so agents inherit it. A weak adversary produces a confident, wrong signature.

If this session itself is below the floor: STOP. Never emit the `SIGN-OFF:` block from below the floor. Offer a lightweight review explicitly labeled NOT a sign-off, with no verdict line, and run it only if the user accepts that framing.

## Step 1 — Establish scope and spec

Two questions, both answered before spawning anyone:

**What got built?** Detect the **union**: the uncommitted working tree PLUS the current branch's commits against its base. Fall back to the files touched this session only if both are empty. If the user named a slice or phase, adjudicate the union against it — work that belongs to a different slice is excluded, and the verdict states the exclusion and the reason. Never silently review half a slice: the normal mid-work state is part committed, part dirty, and each half either belongs to the slice or doesn't.

If detection comes up empty, stop and ask what to review. Never sign off on an empty diff.

**What was it supposed to do?** Look for the build doc: `docs/<feature>-build-plan.md` (what `/blueprint` writes), any phase/slice doc under `docs/`, `plan/`, the vault project folder, or the plan established in this session. This is the acceptance criteria, not background reading.

A blueprint-format doc hands you the grading rubric directly: the slice's **Acceptance criteria** (each naming how it was to be verified) are what you grade against, its **Footprint** is what should have changed, and its **Not in this slice** and the doc's **Out of scope** lines are what must not count against the build. Use them; don't re-derive criteria you were given.

If no spec exists, say so plainly and run in **correctness-only** mode. Never invent acceptance criteria and grade against them — that manufactures both the test and the score. And with no build doc there are no cards: correctness-only mode runs no sweep — its findings still land in `docs/punch-list.md` per the Output section.

**The sweep (backstop).** A prior slice standing `signed off with conditions` or `rejected` — or `built` with uncleared BLOCKER/MAJOR entries (uncleared means open by the next sentence's definition, so waiver-closed entries do not put a `built` card in the sweep's scope), a rebuild awaiting re-verification — brings its still-open items into the reviewers' scope. Open means the **latest-dated** record for the entry (recheck line, `WAIVED (per user)` line, or `REOPENED (per user)` line, matched on `file:line` + claim) leaves it neither fixed nor waived. A record with no claim field matches on `file:line` alone — only where a single entry holds that `file:line`; at a shared location it decides nothing and the ambiguity goes to the user. The claim field is its own `·`-separated field, parentheses wrapping it are not part of it, and a parenthetical glued to the `file:line` is a legacy tag, not a claim. The reviewers verify each open item — never you alone, and never on the word of the session that wrote the fixes. The verdict carries `Prior conditions: N verified fixed · M still open` — N what this sweep verified fixed, M what stays open after it, summed across all swept cards; items the record already closed (recheck-cleared or waived) count in neither. An open card whose items are all waiver-closed is **stale, not a gap** — update it per the Severity → verdict mapping below, waived items excluded; a `built` card never takes a verdict from this stale path — stale or cleared, a rebuilt `built` card keeps `built`, and rebuilt code earns its verdict only from a fresh /signoff. An open card with no entries at all is a **record gap** — report it and recommend /recheck; a gap is never "fully clear." Whenever the sweep verified at least one item, the result — full, partial, or nothing fixed — is recorded, at the ledger's home's tail (the Output section's placement sentence defines the home), as a standard recheck-format block (`### <YYYY-MM-DD> — recheck: <slice>`; one line per verified item: severity · `file:line` · (claim) · fixed | not fixed — keyed to the *original* entry's location and claim, post-fix location noted in the prose after fixed | not fixed — never inside the claim field — when code moved), fixed and not-fixed lines alike, so a partial result survives the chat. A defect a fix introduced gets its severity assigned and is appended in that same block as its own line — severity · `file:line` · broke: claim — scenario · the prior slice whose fix introduced it — and blocks any flip. Then the card: full clearance of a verdict-state card — every item verified fixed, no fix-introduced defects — flips it to `signed off`. Clearance on a rebuilt `built` card only closes the entries; the card stays `built` — rebuilt code earns its verdict from a fresh /signoff, never from the sweep. Anything less leaves the card untouched and recommends /recheck. MINORs are never swept and never gate. This is the backstop for a skipped /recheck, not a second one — it costs nothing when the cards are clean.

## Step 2 — Independence (hard rule)

The session that wrote the code cannot review it. It knows what the code *meant* to do and will read intent into what's on disk.

So: reviewers are always fresh subagents. They receive the scope, the spec path, and the mandate. They do **not** receive your reasoning, your justifications, or your account of what you built and why. They read the source themselves and form their own view.

The build doc doubles as the loop's ledger, so the mandate draws the line: its `## Build assumptions`, `## Deviations`, `## Discovered`, and `## Punch list` sections and its `Status:` lines are the builder's and inspector's working records — not spec, not evidence, never requirements. Blueprint's `Out of scope:` and `Not in this slice:` lines *are* spec. You still read the ledger yourself for rule 4's adjudication — that split already exists.

Never *form the initial verdict* yourself — reviewers originate the findings. Your job is scope, execution, verification, and adjudication (the rules below). Reviewing the diff solo and labeling it a sign-off is the one unforgivable move.

## Step 3 — Review

**LEAN (default).** Three parallel reviewers, distinct lenses:

- `spec` — does the built thing match the doc? Hunt for silently skipped requirements, quietly narrowed scope, and stubs presented as finished. Against a blueprint-format doc, walk the slice's acceptance criteria one by one and check files changed outside its Footprint (unlogged scope creep). This lens matters most and is the one a generic code review misses.
- `correctness` — bugs, unhandled edge cases, error paths that swallow failures, state that can desync.
- `seams` — integration with what already shipped. Regressions in prior slices, broken assumptions at the boundary, migrations that don't run twice.

**DEEP.** Add `security` (authz, injection, secrets, trust boundaries) and `tests` (do the tests assert real behavior, or do they pass vacuously?). Use when the user says deep/thorough/full, or the slice touches auth, money, or user data.

**LIGHT.** One fresh reviewer with a fused `spec` + `correctness` lens; the execute step and every rule below stay intact — LIGHT shrinks the reviewer count and nothing else, though the one-line-justified added lens remains available and fuses into that same single reviewer's mandate; LIGHT never grows a second reviewer. Only on the user's invocation, or the user accepting your offer when the diff is genuinely small — one concern, a few files, on the order of a hundred changed lines or fewer. Never self-selected: an inspection that scales itself down is the rubber stamp the spine forbids. DEEP's content triggers outrank LIGHT: a slice touching auth, money, or user data gets that conflict named and DEEP run — the user can still insist after hearing why, and the Depth line then says so.

You may add a lens beyond the chosen set when you can justify it in one line — e.g., a LEAN run gains `tests` because the build note claims new tests pin earlier findings. State depth, lenses, and why in one line before starting.

**Mechanics.** Reviewers are `general-purpose` subagents (`Explore` is read-only and cannot run tests), launched in the background in a single message. Reviewers do not spawn subagents of their own — every finding must be attributable to a lens. A lens whose method requires mutating the checkout — any lens, named or custom — runs its reviewer in an isolated worktree (the Agent tool's `isolation: "worktree"`) by default; the shared working tree is never the test bed. A worktree checks out committed state only — when the review scope includes uncommitted work, carry all of it into the worktree before the lens runs (the tracked diff and the untracked files — a bare `git diff` drops the untracked half), or the verdict's Method line declares that the lens exercised committed state only. **One suite run at a time:** device-bound test suites (anything targeting a simulator or device) must never run concurrently — two runs sharing one booted simulator SIGKILL each other's test host and both print false-green partial summaries (Atlas, 2026-08-09: two review cycles chased this as a flaky harness crash). Designate one lens to run the suite and have the others read its logged output, or serialize the runs; a repo-level lock only makes concurrent runs queue, which is wait time, not parallelism.

**Reviewers report everything.** Each finding comes back as claim · `file:line` · concrete failure scenario (inputs → wrong outcome) · severity · confidence — including low-confidence ones. Do not instruct reviewers to self-censor or pre-filter; a finder told "verified or cut" misses real defects. Filtering happens in the verify pass, and it is yours.

**Merge before verifying.** Dedup findings on `file:line` + claim. Convergence across independent lenses is signal — note it on the merged finding rather than listing it twice.

## Step 3.5 — Execute

The Method line must be earned. Before writing the verdict, run what is runnable: the project's test command, then the thing itself against the spec's acceptance criteria. Record what ran and what it showed. If nothing is runnable — no tests, no entry point, no fixture — say so in one line; that is the **only** path to "static analysis only" in the Method field.

This is a goal, not a checklist: run what teaches you something about whether the slice holds, and don't re-run what a reviewer already proved.

**Keep bulk output out of context.** Redirect test and build output to a file and read back the summary lines (`> /tmp/run.log 2>&1`, then grep) — a full suite streamed raw into the conversation can burn half the context window before the verdict is written. This applies to reviewers too; pass the instruction along.

## The rules

These govern what reaches the user. Reviewers surface everything (Step 3); you apply the rules to decide what survives into the verdict.

1. **Evidence or it doesn't count.** Every finding in the verdict carries `file:line`. A concern without a location is a hunch — verify it into one or leave it out.
2. **Verify before reporting.** Read the source yourself on every BLOCKER and MAJOR before it reaches the user. Reviewers are fallible and a false blocker costs real time. Stamp CONFIRMED or PLAUSIBLE. Drop what you refute — and count the drops: the verdict carries `Refuted: N`, so the user can see how much the verification pass actually filtered.
3. **Concrete failure scenario, or it's not a finding.** "This could be fragile" is noise. "Two calls in the same tick both pass the check and double-charge" is a finding.
4. **Unbuilt-by-design is not a defect — but Deferred requires written evidence, and the evidence has two tiers.** Blueprint's `Out of scope:` and per-slice `Not in this slice:` lines are user-sanctioned: a gap they cover is Deferred, not a defect. Build's `## Deviations` / `## Build assumptions` entries are the builder's own account: an entry labeled `per user` counts as sanctioned; one labeled `builder call` — or unlabeled — that leaves an acceptance criterion unmet caps the verdict at SIGNED OFF WITH CONDITIONS and goes to the user as a question. Disclosure changes honesty, not doneness. An unmet requirement with no record at all is a BLOCKER **and** a question to the user, never a quiet move to Deferred. Trusting the `per user` label is rule 10's one sanctioned exception: build Step 5 pins its meaning, the label is the builder's accountable attestation of the user's word, and it surfaces in the verdict where the user can disown it — a disowned label is a defect, not a defense. Reviewers report the gap; you adjudicate.
5. **Report, don't repair.** Sign-off is an inspection. Fixing is a separate instruction the user gives after seeing the verdict — offer, don't act. The user can collapse the gate up front — an invocation like "sign off and work any MAJORs" authorizes the fix pass in advance. You never assume it.
6. **The signature is real.** Do not sign off to be agreeable. REJECTED on work the user is excited about is the entire value of the skill; a sign-off that never rejects is decoration.
7. **Declare the method.** The verdict states how the work was actually verified — executed and exercised, tests run, or static analysis only. A review that could not run the thing is weaker than one that could, and that belongs in the verdict where the user reads it, not buried in a footnote. Never let "I read the code carefully" pass as "I checked that it works."
8. **Do the arithmetic.** Where a criterion involves numbers — rates, clamps, thresholds, geometry, timing windows — compute it rather than eyeballing the code, and record the computed values in the verdict (Method line or "Tried and failed to break") so the reader can check the math rather than trust that it happened. The dangerous defect is the right technique applied so it doesn't achieve the stated requirement; that kind only falls out of math.
9. **Read-only against real state.** Reviewers and the execute step may run tests and read anything, but never mutate shared state — and the shared source checkout is shared state: no edits to the working tree under review (a sanctioned run's gitignored byproducts — caches, build artifacts — are not edits; a run that would write unignored content, snapshot files and lockfiles included, is a mutation and runs where mutations run), no migrations against a real database, no writes to dev/prod services, no destructive commands. To exercise a mutation, use an isolated worktree and a throwaway/fixture store, or report it as unverifiable in Method. (This is prose, not enforcement — a repo that needs a hard guarantee needs a hook.)
10. **Comments and build notes are claims, not evidence.** A doc that names a mechanism ("the ordering comes from X") gets verified against the source, and external-API behavior gets checked against the sanctioned reference, not the comment. A documented mechanism that isn't the real one poisons the next slice. **This governs the whole upstream paper trail:** build's `BUILD:` block, its ledger entries, and a `Status: built` line are the builder's account of its own work — they tell you where to look and what was claimed, never that a criterion actually passed. Re-run the check yourself or mark it unverified in Method. Reviewers get the spec by path — the whole doc, its ledger sections outside their mandate (Step 2's split), except the open sweep items Step 1 sends into their scope — and the diff.

## Severity → verdict

| Severity | Meaning | Effect |
|---|---|---|
| **BLOCKER** | Spec requirement unmet, or a defect that loses data / corrupts state / breaks a shipped feature | Cannot sign |
| **MAJOR** | Real defect with a concrete failure path, but contained and fixable in place | Conditional |
| **MINOR** | Rough edge, missing guard, thin test | Punch list only |

- **SIGNED OFF** — meets spec, no BLOCKER or MAJOR.
- **SIGNED OFF WITH CONDITIONS** — no BLOCKERs; named MAJORs must be fixed before the next slice.
- **REJECTED** — one or more BLOCKERs.

A WITH CONDITIONS or REJECTED verdict names what comes next: fix the findings, then `/recheck` verifies them and flips the card.

## Output

Report in chat. Compact — this runs after every slice and must stay fast to read:

```
SIGN-OFF: <slice/phase>
Verdict: SIGNED OFF | SIGNED OFF WITH CONDITIONS | REJECTED
Scope: <what was reviewed; what was excluded and why, if anything>  ·  Spec: <path, or "none — correctness only">
Depth: LIGHT | LEAN | DEEP <+ added lenses>  ·  Method: <ran it / tests / static analysis only>  ·  Refuted: N
Prior conditions: N verified fixed · M still open   <sweep line — only when a prior slice stood open>

Bottom line: <2-3 sentences. What holds, what doesn't, what to do next.>

BLOCKERS   <severity · file:line · claim · failure scenario · CONFIRMED/PLAUSIBLE>
MAJOR
MINOR
Deferred   <spec items intentionally not built, each with its written evidence — not defects>
Tried and failed to break: <what the reviewers attacked that held up>
Questions: <rule 4's open questions to the user — only when any>
Next: <WITH CONDITIONS or REJECTED — fix the findings, then /recheck flips the card; also under a clean verdict when the sweep left a prior card open — name its /recheck recommendation. Omit only when neither applies>
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```

Omit empty sections — **except `Tried and failed to break`, which is mandatory in every verdict and is the longest section when findings are few.** No verdict file by default — offer to write the verdict into the project's vault notes or `docs/` only if the user asks or the result is REJECTED.

When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

**The punch-list ledger.** After the verdict is delivered in chat, append the MINORs — plus, under WITH CONDITIONS, the named MAJORs, and under REJECTED, the BLOCKERs and any MAJORs as well (a rejected card with no recorded findings strands the verdict in a dead chat) — at the tail of the ledger's home in the build doc the review graded against. Create the `## Punch list` section if no home exists; if the review ran correctness-only with no doc, create `docs/punch-list.md` instead. Blocks are headed `### <YYYY-MM-DD> — review: <slice>` — no verdict word in the doc. One line per finding: severity · `file:line` · claim · concrete failure scenario · which slice's review found it. A verdict capped by a builder-call deviation appends that deviation as a MAJOR line — the open question is the claim, the unmet criterion stands in as the scenario, and the deviation's own ledger entry (or the code site it names) supplies the `file:line` — so the card's conditions survive the chat. The scenario is the test /recheck re-runs; the severity is what the next build's preflight and the sweep key on. Additive-only — never rewrite or resolve earlier entries, and never write the verdict itself into the doc (a punch list is a work document; the signature lives in chat). Further doc writes, exhaustively: set the reviewed slice's `Status:` to `signed off`, `signed off with conditions`, or `rejected` — a one-word state flag for the next build's preflight, not the verdict block; the sweep's recheck-format block — written whatever the verified outcome, partial clearance included, and carrying its attributed fix-introduced-defect lines — plus the full-clearance flip and the stale-card update that the Severity → verdict mapping commands; and, when the user grants or revokes a waiver mid-review, the dated `WAIVED (per user) · <YYYY-MM-DD> · severity · file:line · claim` or `REOPENED (per user) · <YYYY-MM-DD> · file:line · claim` line plus the card update it implies — the `WAIVED` line is written after this run's punch-list writes (the review block and, when the sweep wrote one, its recheck-format block), so the user's word lands later in the file and wins the same-date tiebreak over any same-item line in those blocks. Appended `WAIVED`/`REOPENED` lines land at the ledger's home's tail, outside any block — the home is where the doc's punch-list blocks already live, or the `## Punch list` section when none exist yet, and when blocks sit in more than one place the latest-dated block's location is the home (on a date tie, the later in the file): one home per doc, never split; when records share a date, the later in the file wins — appends only land at the home's tail, so file order is time order. This ledger is bookkeeping, not repair: no code is touched. Its purpose is accumulation — a MINOR that recurs across slices is a pattern, and it can only be seen if the findings land in one place.

## What NOT to do

- Don't review your own work — always fresh subagents.
- Don't pass the reviewers your rationale for what you built.
- Don't tell reviewers to pre-filter — they report everything; you filter in the verify pass.
- Don't grade against acceptance criteria you invented.
- Don't fix anything during the review.
- Don't mutate real state to verify a finding — isolated worktree and fixtures, or call it unverifiable.
- Don't pad the verdict to look rigorous. Verified or cut — applied by you, after the reviewers report.
- Don't sign off on work you haven't verified against the actual source.
- Don't let a review that couldn't execute the code imply that it did.
- Don't emit the `SIGN-OFF:` block below the model floor.
