---
name: handoff
description: End-of-slice thread prep for the build loop — pauses on unanswered questions, records rulings, writes a dated handoff block into the build doc and a superseding memory pointer, then hands over the exact kickoff line for the fresh session. STRICTLY user-invoked, only when Tony summons it ("/handoff", "prep for the next slice", "prep the repo for slice X", "clear the thread and prep", "get ready for slice X", "get ready for the next slice"); never auto-invoke, suggest-invoke, or trigger from conversation shape. NOT for machine or terminal settle-up or account switches (that's /shutdown), and NOT for cross-machine hand-offs ("tell the laptop / tell the studio" — the claude-relay protocol in CLAUDE.md).
---

# Handoff

The end-of-phase walkthrough. `/blueprint` draws the plans, `/build` frames a slice, `/signoff` inspects it, `/recheck` re-inspects the fixes — and when the thread is about to be cleared, `/handoff` sweeps the site: everything a `/clear` would destroy gets asked, recorded, or written down, and Tony leaves with the exact line to type in the fresh session.

**The spine — photograph, never gate.** Open cards never stop this run; they change its output. The one sanctioned pause is the question gate: unanswered questions stop the run before any write, until Tony answers them. Enforcement of the loop's standings stays where it lives — /build's preflight — and /handoff reports the record, it never blocks on it.

**The one unforgivable move is the invented photograph:** state written from what the session remembers instead of verified against the doc and git right now. A wrong pointer poisons the next session's cold start, and nobody is there to catch it — the thread that knew better is gone.

## Step 1 — Find the doc

The siblings' hunt, same tiers, same priority: `docs/plans/*.md` (what `/blueprint` writes — the repo doc kit's folder; a candidate is matched to the invocation by the `<topic>` in its `YYYY-MM-DD-<topic>.md` name or its `Intent:` line, and several plausible matches are listed and asked, never silently picked), then the older flat `docs/<feature>-build-plan.md` (when both tiers match, `docs/plans/` wins and the report says which doc it took), any phase/slice doc under `docs/` or `plan/`, the vault project folder, or the plan established in this session — the first tier that yields a doc wins, and two candidates inside one tier is a stop-and-ask, never a silent pick.

## Step 2 — Read the record

Read every slice's `Status:` card and the punch-list ledger, and compute the open set by the loop's latest-dated-record rule: an item is open when the latest-dated record for it (recheck line, dated `WAIVED (per user)` line, or `REOPENED (per user)` line, matched on `file:line` + claim) leaves it neither fixed nor waived. A record with no claim field matches on `file:line` alone — only where a single entry holds that `file:line`; at a shared location it decides nothing and the ambiguity goes to the user. The claim field is its own `·`-separated field, parentheses wrapping it are not part of it, and a parenthetical glued to the `file:line` is a legacy tag, not a claim. This is read from the doc now, never reconstructed from the session's memory of the verdicts.

## Step 3 — The question gate

Before ANY write, assemble the open questions from four sources:

1. Unanswered `Questions:` lines from this session's /signoff and /recheck outputs.
2. Rulings Tony gave in chat this session that never became dated ledger lines — a chat-only waiver counts for nothing downstream, so it would resurface at the next preflight.
3. Ambiguity about which slice is next — when the `Status:` cards and `Depends on:` chains don't yield exactly one answer.
4. Open questions the build doc records that touch the slice about to be built.

Any found: present them all in one batch and pause — nothing has been written yet. Every question answered: record the answers (Step 4) and continue the run. Any question unanswered — some or all, whether Tony skipped it or never replied: the run ends with nothing written, reported in the gate-open form (Output section), never the standard block — a partial set of answers never buys a partial handoff. Never answer a gate question on Tony's behalf, and never write around one.

## Step 4 — Record the answers

An answer that waives or reopens a finding is appended as the loop's dated line — `WAIVED (per user) · <YYYY-MM-DD> · severity · file:line · claim` or `REOPENED (per user) · <YYYY-MM-DD> · file:line · claim` — /handoff is then the station receiving the user's word, same law as the siblings, and after a grant or revocation it updates the slice's card from what remains open of that slice, waived items excluded: any BLOCKER open → `rejected` · else any MAJOR open → `signed off with conditions` · else → `signed off`. A slice standing `built` (a rebuild) never takes a verdict from this update — clearing or waiving its items leaves the card `built`; a fresh /signoff earns the signature. Appended `WAIVED`/`REOPENED` lines land at the ledger's home's tail, outside any block — the home is where the doc's punch-list blocks already live, or the `## Punch list` section when none exist yet, and when blocks sit in more than one place the latest-dated block's location is the home (on a date tie, the later in the file): one home per doc, never split; when records share a date, the later in the file wins — appends only land at the home's tail, so file order is time order.

Every other answer lands in this run's handoff block (Step 7) as question · answer.

## Step 5 — Harvest the perishables

Collect from this session what dies at `/clear`: the gate's answered questions, seam notes for the next slice, workarounds discovered, items pending Tony's word (a migration he must push, a deploy he must trigger), and open MINORs worth the next builder's attention. Nothing shaped like a requirement — the block is ledger, never spec, and /signoff grades against the doc's requirements alone.

## Step 6 — Photograph the repo

Verified against git and the filesystem now, never trusted from session memory:

- Current branch, and commits ahead of main.
- Working-tree state. Loose work gets a local checkpoint commit labeled as a handoff checkpoint — local only; the git gates stay Tony's: never push, PR, or merge.
- The last-recorded suite state, with its provenance (which run, when). Never run the suite fresh — the next /build's preflight takes its own before photo; a handoff-time run duplicates the cost and earns nothing.

## Step 7 — Resolve the next move and write

**The next move.** Clean boundary — the just-finished slice's card clear, exactly one next slice resolvable: the kickoff line is `/ship <next slice> <doc path>` (or `/build <next slice> <doc path>` for running the stations by hand — state the alternative once). Open card — BLOCKERs or MAJORs still standing: the kickoff is the fix list — the open items, then /recheck. Loop complete — every slice's card clear and no slice left to build: there is no kickoff line; the block and the report say the loop is done, and the next move is Tony's (a new /blueprint, or nothing) — never a `/ship` of a slice that doesn't exist.

**The doc write.** Exactly one dated block per run, headed `### <YYYY-MM-DD> — handoff`, appended at the tail of the `## Handoffs` section — created before `## Punch list` when missing. Contents: the next move, the repo photograph, the perishables — dated heading, one line per item, ·-separated fields where fields exist. Additive-only: earlier blocks are never edited, nothing verdict-shaped is ever written, and punch-list history stays untouched beyond Step 4's sanctioned lines.

**The memory pointer.** One auto-memory file per feature, `handoff-<feature>` (type: project), overwritten each run — never a second dated file — pointing at the doc path, the block's date, and the kickoff line. `<feature>` is the doc's identity, derived one way per doc, every run: the `<topic>` of a `docs/plans/<YYYY-MM-DD>-<topic>.md` filename, else the `<feature>` from an older flat `docs/<feature>-build-plan.md` filename, else a slug of the doc's own top-line title; when neither yields one, ask Tony to name it — never guess, and never let two runs name the same doc differently. The MEMORY.md index line is added or updated, worded as the build loop's kickoff pointer for the named build doc — wording no session can mistake for a /shutdown session handoff — and earlier handoff pointers for the same feature are superseded, never seconded.

## Step 8 — Report and stop

Emit the `HANDOFF:` block and end the turn, closing with the statement that the thread is safe to clear. The skill never runs `/clear`, never starts the next slice, and never invokes another station.

## The rules

1. **Photograph, never gate.** Open BLOCKERs/MAJORs change the kickoff line, never stop the run. The question gate is the one pause.
2. **Nothing is written before the gate resolves.** An abandoned gate leaves the doc, the ledger, and memory exactly as found.
3. **The record over the recollection.** Cards, open items, and repo state come from the doc and git read now — a handoff written from memory is the unforgivable move.
4. **The block is ledger, never spec.** Handoff notes inform the next builder; they never bind it. Requirements live in the slices alone.
5. **Additive only.** One dated block per run at the section's tail; earlier blocks and punch-list history are never edited. The sanctioned writes, exhaustively: the handoff block, Step 4's dated `WAIVED`/`REOPENED` lines with their card updates, the checkpoint commit, and the memory pointer.
6. **The git gates are Tony's.** Local checkpoint commits only — never push, PR, or merge.
7. **Report faithfully.** The kickoff line matches the record, not the mood — an open card's fix list is never rounded up to a clean `/ship`.

## Output

Report in chat. Compact — this runs at every slice boundary and must stay fast to read:

```
HANDOFF: <feature> — after <slice>
Doc: <path>  ·  Next: <the exact kickoff line to type>
Repo: <branch · N ahead of main · clean | checkpointed>  ·  Suite: <last-recorded state · provenance | none recorded>
Questions: <N asked · N answered · where each answer landed>  ·  Perishables: <N carried>

Bottom line: <2-3 sentences. What was captured, what state the record is in, what to type after clearing.>

Open: <each still-open finding · severity · one line — only when any>
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>

Thread is safe to clear.
```

Omit `Open` when empty.

A run the question gate ends emits the gate-open form instead — never the standard block, and never the safe-to-clear closer, because nothing was saved:

```
HANDOFF: <feature> — GATE OPEN, nothing written
Doc: <path>
Unanswered: <each open question, one line>

Thread is NOT safe to clear — answer the questions and re-run /handoff, or clear and accept the loss.
```

When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

## What NOT to do

- Don't gate on open cards — they change the kickoff line, nothing else.
- Don't write anything before the question gate resolves, and don't answer a gate question on Tony's behalf.
- Don't write verdicts, and don't touch punch-list history beyond Step 4's dated lines.
- Don't push, open a PR, or merge — the git gates are Tony's, always.
- Don't run the test suite — report the last-recorded state with its provenance.
- Don't start the next slice, run `/clear`, or invoke another station.
- Don't absorb /shutdown's job (machine and terminal settle-up) or the claude-relay protocol's (cross-machine hand-offs).
- Don't photograph from memory — read the doc and git now.
