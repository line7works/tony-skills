---
name: precon
description: The pre-construction meeting — harvest a free-flowing idea discussion into a fixed-format scope doc that /blueprint can later consume. STRICTLY user-invoked, only when Tony types /precon; never auto-invoke, suggest-invoke, or trigger from conversation shape, no matter how idea-like the discussion looks.
---

# Precon

The station upstream of the loop. Tony talks an idea out free-flowing, and when it gets serious he summons `/precon`; the skill harvests what was already said, asks only the load-bearing questions that remain, and lands every settled decision in a scope doc the moment it settles — a record for `/blueprint` so the interview never happens twice. One caveat, stated honestly: /blueprint does not yet hunt scope docs (that one-line edit to /blueprint is deferred work); until it lands, Tony points /blueprint at the doc himself, and this skill never implies otherwise. This skill runs only when Tony invokes it — the idea stage stays free-flowing in his own way, and no amount of idea-shaped conversation is an invitation.

**The spine.** The skill records; it never decides. Every ledger line traces to Tony's words in the discussion or to a numbered question he answered here. The scope doc is a transcript of his decisions in fixed form, not the skill's opinion of what the idea should be.

**The one unforgivable move is an invented ledger line:** a decision Tony never made, an embellished version of what he said, an assumption dressed as a ruling. /blueprint will treat the scope doc as settled ground — an invented line becomes law downstream. When something is unsettled, it is `open` or `parked`, never quietly resolved.

## Step 1 — Harvest

Mine what already exists before asking anything:

- **The conversation so far:** decisions already made, options already rejected, constraints already stated, names already used. Most of the scope doc usually exists in the chat; harvesting it is the whole point.
- **The property:** the repo (if invoked inside one) and the project docs already on it — existing components, conventions, prior scope or build docs, anything under `docs/`. Facts the property can answer are looked up here, never asked as questions.
- **An existing scope doc:** invoked with one (or when one exists for this idea), re-open its `parked` and `open` items and continue the ledger in place — one living doc, never a fork. This is also how a scope-level change order runs: re-invoke /precon on the doc.

Invoked cold with no prior discussion, listening is step one: Tony talks, the skill captures. Don't open with an interrogation.

**The property line.** The skill never leaves the property: no web access, no research documents, no research subagents — lookups are confined to the repo and the docs already in the project. A question that needs outside research is not asked and not answered; it is parked in the ledger tagged `needs research`. Parked items are Tony's break points — natural places to pause the sitting while he does the research himself, and pick back up after.

## Step 2 — Triage

Classify the idea aloud before round one, to set interview depth. Tony can override the tier in a word.

- **napkin** — describable in a sentence or two. One short round of questions, or none. Recommending "this doesn't need a scope doc, go straight to /blueprint" is a valid outcome here — and when Tony takes it, Steps 3–5 are skipped, no doc is written, and the sitting ends at Step 6 with a read-back of what was said and a report block carrying `Doc: none — napkin, straight to /blueprint` and zeroed counts.
- **bounded** — a normal feature or project with known edges. A few rounds.
- **architectural** — spawns repos or systems, or changes how other things work. Full depth.

## Step 3 — Rounds

Interview in batched frontier rounds, a few questions each:

- **Frontier only:** a round contains only questions whose prerequisites are already settled. Questions that depend on an open answer wait for a later round.
- **Numbered, with recommendations:** every question is numbered and carries a ➡️ recommendation, so Tony can answer by number ("1", or "1 and 3, but for 2 do X").
- **Only-if-it-differs:** questions are spent where Tony's answer could plausibly differ from the recommendation. Small reversible calls are decided and logged as `assumed` in the ledger — with why they didn't earn a question — not asked.
- **Facts vs decisions:** if the property can answer it, look it up. Questions are for decisions only.
- **The board:** every round opens with the header `Round N — <tier> — board: decided N · assumed N · parked N · open your-calls N` — the triage tier welded in so it can never be silently skipped, and "your-calls" are decisions identified but not yet put to Tony or not yet answered. Recount from the scope doc itself before posting, never from memory — a board that disagrees with the ledger is a defect. The board is mid-interview state; it deliberately differs from the final report's tallies.
- **No drip, no cap:** questions come in batches, never one at a time — and there is no fixed question budget. Depth is steered by triage tier and plain language, not a counter.

## Step 4 — Ledger as you go

Every settled decision lands in the scope doc the moment it settles — not at the end of the sitting — appended at the tail of the `Decisions:` block, never below `Out of scope:`, `Research:`, or `Open:`; mid-doc edits keep the template's section order intact. Each line carries one tag:

- `decided` — with its source: Tony's words in the discussion, or the answered question.
- `assumed` — with why it didn't earn a question.
- `parked` — with one of: `needs research`, `needs prototype`, or `waiting on <x>`.

Every line traces to Tony's words or an answered question. The skill records; it never decides for him.

**The out-of-scope channel.** When Tony rules something out — an option rejected, a feature deferred, a direction declined — it lands in the doc's `Out of scope:` section with the reason, not as a Decisions line. Those lines are /blueprint's descope evidence, they trace to Tony's words or an answered question like everything else, and they are what the report's `out of scope N` counts.

**Suggest only, never act.** When the idea deserves an outside panel, the skill may say "this smells like a /jpb" (Tony's multi-model product-box consensus skill, `~/Developer/tony-skills/plugins/jpb/`) in one line. When a question needs something concrete to react to, it may say "this would be easier with a throwaway to look at." That is the ceiling: it never invokes a skill, never builds a prototype (or anything else), never queues anything. The suggestion is one line; acting on it is Tony's.

**The scope doc.** Written to `<repo>/docs/scope/<YYYY-MM-DD>-<idea>.md` (the repo doc kit's layout: `docs/scope/` is precon's folder, names inside are date-topic; create the folder on first use) — the repo the idea unambiguously belongs to, whether or not the session was invoked inside it, with that call ledgered as `assumed` when it wasn't; when no repo owns the idea, `~/Documents/<idea>-scope.md` — the pre-repo staging home, which /sunrise empties into the new repo's `docs/` when it creates the repo. The doc is born at the first settled ledger line — always after triage, so a napkin idea ruled "no scope doc" never leaves an orphan file. `<idea>` is a kebab-case slug of the idea's working name; when the name isn't obvious, settling it is a round-one question, and a re-invocation looks for an existing doc under that slug in three places (`docs/scope/*-<idea>.md`, the older flat `docs/<idea>-scope.md`, and `~/Documents/<idea>-scope.md`) before creating anything — rule 8 depends on the slug matching. The path is printed in the report block; relocating the doc is Tony's or /sunrise's (its staged-doc adoption step, when it creates the repo), never this skill's. The format is load-bearing — these are the sections /blueprint Step 1 is meant to harvest once its deferred one-line edit lands; until then Tony points /blueprint at the doc himself — so keep it exact:

```
# <Idea> — scope doc (<date>)

Intent: <what it is, who it's for, why — the why /blueprint needs>
Decisions:
- <one line> — decided (<source: Tony's words or the answered question>)
- <one line> — assumed (<why it didn't earn a question>)
- <one line> — parked: <needs research | needs prototype | waiting on <x>>
Out of scope: <item — reason>
Research: <paths/links to research Tony did himself, if any>
Open: <unresolved threads for the next sitting>
Next: /blueprint when ready.
```

## Step 5 — Exit test

When the frontier empties — no settled-prerequisite questions remain — offer the cold read as one numbered question with a ➡️ recommendation:

1. **Local Claude reader** (➡️ the recommendation and the default) — a fresh zero-context subagent reads the scope doc read-only and reports its confusions in chat.
2. **GPT via the codex MCP** — `gpt-5.6-sol` pinned, or another GPT model on Tony's pick. This is external: it sends only on Tony's explicit word in this run, never by default. The call carries `config: {web_search: disabled}` — a reader that can search answers its own questions instead of reporting them, and the cold read is contaminated. Transport only is borrowed from jpb (`mcp__codex__codex`; the pinned id and its refresh procedure live in `~/Developer/tony-skills/plugins/jpb/skills/jpb/SKILL.md`) — none of jpb's box mandate or verdict machinery comes with it.
3. **Decline** — a clean path; the doc stands as written.

The reader gets a cold-reader prompt with zero context supplied: read this scope doc — what's unclear, what would you ask before building this?

**The cold-read doc.** The reader's findings are Tony's to review, never the session's to filter invisibly. Before any triage, write the output verbatim to `<repo>/docs/reviews/<YYYY-MM-DD>-precon-cold-read-<idea>.md` when the scope doc is repo-owned (create `docs/reviews/` on first use), or to `~/Documents/precon-cold-reads/<idea>-cold-read-<date>.md` when the scope doc is staged in `~/Documents`; as triage happens, add a summary at the top saying what was taken and what was left behind, and a disposition marking every item `surfaced` (put to Tony), `absorbed` (folded into the doc), or `left downstream` (blueprint-altitude, with the why). The scope doc's `Research:` section gets the pointer. Returned confusions reopen branches: back to Step 3 for whatever they surface. No other readers exist — there is no multi-model panel.

## Step 6 — The gate

The sitting ends by reading the record back — the ledger's decisions, assumptions, parked items, and open threads — and stopping. Ending requires a one-line written justification that every branch was visited or explicitly parked. Then a full stop: the skill never starts building and never auto-invokes /blueprint (or any other skill). "Precon it and blueprint it" is Tony collapsing the gate in his invocation; the skill never assumes it.

## The rules

1. **User-invoked only.** /precon runs when Tony types it, never because the conversation looks ready for it.
2. **Harvest before asking.** The conversation and the property come first; a question the harvest could have answered is a wasted question.
3. **The property line is absolute.** No web, no research, no research subagents. Outside-research needs become `parked: needs research` lines — Tony's break points.
4. **Facts are looked up, decisions are asked.** Never ask what the repo or docs can answer.
5. **Record, don't decide.** Every ledger line traces to Tony's words or an answered question. Unsettled means `open` or `parked`.
6. **Questions earn their slot.** Ask only where the answer could plausibly differ from the recommendation; the rest are logged as `assumed` with the why.
7. **Suggest only, never act.** One-line pointers to /jpb or a throwaway are the ceiling. No invoking, no building, no queuing — and anything external sends only on Tony's word in that run.
8. **One living doc.** Re-invocation continues the existing scope doc in place; never fork a second one.
9. **The gate is real.** Read back, justify the ending in one written line, stop.

## Output

Report in chat when the sitting ends:

```
PRECON: <idea>
Doc: <path>
Counts: decided N · assumed N · parked N · out of scope N
Parked: <one line each, with its tag>
Next: /blueprint when ready.
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```

When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

## What NOT to do

- Don't research or leave the property — no web, no research docs, no research subagents. Park it instead.
- Don't ask what the property can answer — look it up.
- Don't invoke any skill, ever — not /jpb, not /blueprint, not a research dispatch. Suggesting in one line is the ceiling.
- Don't build anything, prototypes included — "a throwaway would help" is something to say, not do.
- Don't send anything to an external model without Tony's explicit word in that run.
- Don't drip questions one at a time — batch them into rounds.
- Don't cap questions — depth is steered by triage and plain language, not a counter.
- Don't invent or embellish ledger entries beyond what Tony said or answered.
- Don't blow the gate — no building, no auto-/blueprint, no continuing past the read-back.
- Don't use harness question UI (AskUserQuestion) for rounds — plain-text numbered questions only.
- Don't auto-file the scope doc into `~/Developer/_ideas/` or move it into a repo — relocation is Tony's or /sunrise's, never this skill's.
