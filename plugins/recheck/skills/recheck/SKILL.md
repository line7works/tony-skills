---
name: recheck
description: Closed-checklist re-inspection after a /signoff verdict — verifies each named BLOCKER/MAJOR fix actually landed and flips the slice's status card. Use when the user says "recheck", "recheck slice A", "recheck the fixes", or has just fixed signoff findings and wants the card flipped. Not a fresh review — the checklist is closed; open-ended hunting belongs to /signoff.
---

# Recheck

The re-inspection visit. /signoff failed items on a slice, the fixes went in, /recheck comes back and looks at exactly those items, then flips the card. Where it sits: build → signoff → fix → **recheck** (card flips) → next build.

**The spine — the checklist is closed.** One question per named finding: did this specific fix land? The list only shrinks, which is why re-inspection terminates instead of treadmilling — nobody is asked "what's wrong with this code" twice. The open-ended hunt is /signoff's job; recheck offers it rather than becoming it.

**The one unforgivable move is the unearned flip:** setting `signed off` on the fixer's word. "Done" from the fix session is a claim. The card flips on verification or not at all.

## Step 0 — Model floor

Same floor as /signoff: the reviewer runs at Opus-class or better — never pin below `opus`; when this session is at or above the floor, omit the override so the agent inherits it. If this session is below the floor: STOP. Never flip a `Status:` line or emit the `RECHECK:` block from below the floor.

## Step 1 — The checklist

**The repo's inspection sheet, first.** Read `<repo>/REVIEW.md` before the doc hunt. It is the sheet only under /signoff's test (the three headings, every pass line `on` or `off`); a file of that name that fails it is reported as `present but not the kit sheet — defaults` and ignored. Present and well-formed, it governs what this run grades: its `## Severity bar` is the severity mapping for every fix-introduced defect this run assigns, overriding /signoff's generic table where they differ; its `## Passes` change nothing here — this run hunts nothing, so there is no pass to skip, and a fix-introduced defect the verifier reports is entered on the record whatever kind it is, graded by the bar, exactly as /signoff's sweep would enter it (one event, one ledger shape); and its `## Repo-specific checks` are /signoff's hunt, not this checklist — the closed list never grows from them (rule 1). Absent, the run grades on /signoff's defaults and the report's `REVIEW.md:` line says `absent — defaults`. /recheck reads the file and never writes it — not a toggle, not the stamp, not a line; a recurrence this run notices is /signoff's second-failure rule to record, and one line naming it is the most this run says.

**Find the doc.** Same hunt as the siblings: `docs/plans/*.md` (what `/blueprint` writes — the repo doc kit's folder), then the older flat `docs/<feature>-build-plan.md` — both of these are read before choosing: a candidate matches the invocation by filename (the `<topic>` of a `YYYY-MM-DD-<topic>.md` name, or the `<feature>` of a flat name), an `Intent:` line is consulted only when no filename in either matches, a filename match in either beats an Intent-line match in the other, and when a `docs/plans/` doc and a flat doc both match by filename, `docs/plans/` wins and the report says which doc it took; several plausible matches are listed and asked, never silently picked, and an invocation that names nothing to match against is a stop-and-ask, never the lone doc on disk — then any phase/slice doc under `docs/` or `plan/`, the vault project folder, or this session's record. A correctness-only review with no build doc leaves `docs/punch-list.md` instead — append there and skip every `Status:` write (there is no card; say so in the output).

**Resolve the slice:** the one named — or, when the invocation names entries rather than a slice, the named set is the run's scope and no slice resolves — else the slice whose punch-list review block carries the latest date among slices standing at `signed off with conditions` or `rejected` — or at `built` with uncleared BLOCKER/MAJOR entries (a rebuilt slice whose findings were never re-verified). Ambiguous → ask. Slices still open outside the run's scope → name them in the output, never absorb them.

**Assemble the items:** the still-open BLOCKERs and MAJORs — deduped on `file:line` + claim across punch-list entries *and* the chat verdict's findings when this session has them, with the open-filter applied to the merged set. Open means the latest-dated record for the item (recheck line, dated `WAIVED (per user)` line, or `REOPENED (per user)` line, matched on `file:line` + claim) leaves it neither fixed nor waived. A record with no claim field matches on `file:line` alone — only where a single entry holds that `file:line`; at a shared location it decides nothing and the ambiguity goes to the user. The claim field is its own `·`-separated field, parentheses wrapping it are not part of it, and a parenthetical glued to the `file:line` is a legacy tag, not a claim. Only the user's word creates or revokes a waiver. MINORs join only when the user names them: recorded, never gating. The naming door: the user naming any still-open entry — by its review block's slice or by `file:line` + claim — adds it to this run's checklist regardless of the card its slice stands at; one run may take named entries from more than one slice's blocks, and a run may assemble entirely from named entries — a still-open entry is already on the record, so naming it widens this run's scope, never the record. The user naming a previously cleared or waived item re-opens it — append a `REOPENED (per user) · <YYYY-MM-DD> · file:line · claim` line; that is the one sanctioned expansion, and only the user's word opens either door. Appended `WAIVED`/`REOPENED` lines land at the ledger's home's tail, outside any block — the home is where the doc's punch-list blocks already live, or the `## Punch list` section when none exist yet, and when blocks sit in more than one place the latest-dated block's location is the home (on a date tie, the later in the file): one home per doc, never split; when records share a date, the later in the file wins — appends only land at the home's tail, so file order is time order.

Each item needs severity · `file:line` · claim · failure scenario. Recover what the record lacks from the chat verdict; otherwise ask the user to supply or confirm it — a scenario reconstructed from a claim becomes the test only after the user confirms it, never silently.

**An empty checklist against a card reading `rejected` or `signed off with conditions` is a record gap, not a clean slate** — the findings live in a verdict this session may not have. Say so and ask for them; never report "nothing to recheck" against an open card. Only an empty checklist ends a run early — and only against a card already clear (or no open items anywhere); a non-empty checklist runs, whatever the cards read.

## Step 2 — Independence

The session that wrote the fixes never grades them. One fresh `general-purpose` subagent (it must be able to run things) receives the checklist — each item's file:line, claim, and failure scenario — and `REVIEW.md` when present, and reads the current source itself. It does not receive the fixer's account of what was fixed or how. The failure scenario is the test: it either still reproduces or it doesn't.

## Step 3 — Verify each item

Each checklist item resolves to exactly one of:

- **fixed** — the failure scenario no longer holds against the current source.
- **not fixed** — the scenario still reproduces, or the fix missed the named case.

Executed where runnable, static where not — and a scenario whose only execution path would mutate real state is verified statically and declared so.

**Fix-introduced defects are new items, not outcomes.** When a fix broke something, the reviewer reports it as its own claim · `file:line` · failure scenario, and you assign its severity at adjudication (same table as /signoff). It joins the open set. The door stays narrow: only defects the fix caused enter; a pre-existing issue newly noticed gets at most one line offering /signoff. An item can be not fixed *and* have broken something else — two records, not one.

Keep bulk output out of context: redirect runs to a file and read back the summary lines (`> /tmp/run.log 2>&1`, then grep).

## Step 4 — Adjudicate and flip

**Adjudicate conservatively.** Verify the reviewer's evidence; you may confirm any outcome, or downgrade fixed → not fixed with evidence. Upgrading not fixed → fixed requires evidence the reviewer lacked — and is forbidden when this session wrote the fix: record the dispute, leave the item open, and recommend a fresh-session recheck. The fixer never argues its own fix across the line.

**Status**, per slice: each slice with items on this run's checklist takes the mapping over everything still open of its own — unfixed checklist items, fix-introduced defects (each charged to the slice whose fix caused it), and its record's still-open BLOCKER/MAJOR entries this run never verified, so a partially named slice can close its named items without its card ever being raised past the rest: any BLOCKER open → `rejected` (demote the card if it stood higher) · else any MAJOR open → `signed off with conditions` · else → `signed off`. A slice's card never moves on another slice's items. MINORs, named or not, never move the Status — /signoff itself signs with MINORs on the punch list. Edit each `Status:` line the mapping commands; leave a card untouched when nothing changed. Two carve-outs: a waiver the user grants mid-run is appended as its dated `WAIVED (per user) · <YYYY-MM-DD> · severity · file:line · claim` line and the item leaves the open set before the mapping runs — the `WAIVED` line is written after this run's punch-list block, so the user's word lands later in the file and wins the same-date tiebreak over the block's own line for that item; and a slice standing `built` (a rebuild) never gets a verdict from recheck — clearing its items closes them, the card stays `built`, and a fresh /signoff earns the signature. Appended `WAIVED`/`REOPENED` lines land at the ledger's home's tail, outside any block — the home is where the doc's punch-list blocks already live, or the `## Punch list` section when none exist yet, and when blocks sit in more than one place the latest-dated block's location is the home (on a date tie, the later in the file): one home per doc, never split; when records share a date, the later in the file wins — appends only land at the home's tail, so file order is time order.

**Punch list:** append one block at the tail of the doc's ledger home (create the `## Punch list` section if no home exists), headed `### <YYYY-MM-DD> — recheck: <slice>`. One line per checklist item: severity · `file:line` · (claim) · fixed | not fixed — the *original* entry's location and claim are together the join key, so co-located findings stay distinct; note the post-fix location in the prose after fixed | not fixed — never inside the claim field — when code moved. One line per fix-introduced defect: severity · `file:line` · broke: claim — scenario. When blocks conflict on an item, the latest-dated block wins. Earlier entries are never edited. The same block is also appended to the slice's signoff verdict doc, found by glob — `docs/reviews/*-signoff-<feature>-<slice>.md`, where `<feature>` is the build doc's identity (the `<topic>` of a `docs/plans/<YYYY-MM-DD>-<topic>.md` name, else the filename minus `-build-plan.md`) and `<slice>` is the slice's letter or name from its `## Slice <X> —` heading, lower-cased with spaces as hyphens, the same rule /signoff names — so the record and the working state carry the same clearing; when the glob finds nothing, say so in the report's `Verdict doc:` field and append to the build doc only. /recheck never creates a verdict doc.

## The rules

1. **The checklist is what the record names.** Never re-derived, never expanded mid-run — the user re-opening a cleared item by name is the one exception.
2. **The narrow door.** Only defects the fix introduced enter, as new named items with assigned severity. A pre-existing issue newly noticed stays out of the verdict and the punch list — at most one line offering /signoff.
3. **Evidence flips the card.** Never the fixer's word; executed where runnable, and the method declared in the output.
4. **Additive only.** Recheck appends its block; earlier punch-list entries are never edited or resolved in place. Latest-dated block wins.
5. **MINORs never gate.**
6. **Report, don't repair.** The Status line, the punch-list block, its copy appended to the slice's verdict doc under `docs/reviews/`, and user-granted `WAIVED`/`REOPENED` lines are the run's own bookkeeping; beyond them, mutate nothing and fix nothing — never `REVIEW.md`, which /signoff alone writes — the next fix pass is the user's to order.

## Output

```
RECHECK: <slice> — N items (+M new)
Result: ALL CLEAR | PARTIAL (n open) | NOT CLEAR  ·  Status: <old → new | unchanged | no card — punch-list.md>
Verdict doc: <docs/reviews/... path — appended | none found, build doc only>
REVIEW.md: read — bar applied | present but not the kit sheet — defaults | absent — defaults
Method: <per item — executed or static, and how>

Bottom line: <2-3 sentences. What cleared, what didn't, what's next.>

<severity · file:line · (claim) · fixed | not fixed | broke: <what> · how verified>
Still open: <each open item · what's still needed>
Other open slices: <cards this run did not touch>
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```

ALL CLEAR = nothing open · NOT CLEAR = nothing cleared · PARTIAL otherwise — "open" counts unfixed items and fix-introduced defects. Omit `Still open` and `Other open slices` when empty. The verdict lives in chat; the build doc gets the `Status:` line and the punch-list block, never a verdict, and the slice's verdict doc under `docs/reviews/` gets a copy of that block.

When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

## What NOT to do

- Don't hunt — recheck is not a review, and "recheck everything properly" is /signoff, offered, never absorbed.
- Don't flip the card on the fixer's word, and don't overrule your reviewer's "not fixed" on fixes this session wrote.
- Don't adopt a reconstructed failure scenario the user hasn't confirmed.
- Don't edit or resolve earlier punch-list entries.
- Don't repair anything, and don't mutate real state to verify — the run's own doc writes (the `Status:` line, the punch-list block and its copy in the slice's verdict doc, user-granted waiver lines) are bookkeeping, not repair.
- Don't write `REVIEW.md` — read its bar and passes, never its toggles, stamp, or checks list; recording a recurrence there is /signoff's.
- Don't treat MINORs as gates.
- Don't emit the `RECHECK:` block below the model floor.
