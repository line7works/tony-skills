# Precon skill — build plan (2026-08-19)

Intent: /precon is the pre-construction meeting of Tony's build loop — the skill that fills the slot between "the idea" and /blueprint. Today the idea stage lives entirely in conversation: decisions made while talking an idea out have no home on disk, blueprint re-interviews from scratch, and marinating ideas evaporate into compacted threads. /precon extends the loop's paper trail one station upstream: Tony talks free-flowing as always, summons /precon when an idea gets serious, and the skill harvests what was already said, asks only the load-bearing questions that remain (each with a recommendation, answerable by number), and lands every settled decision in a fixed-format **scope doc** the moment it settles. The scope doc is designed for /blueprint Step 1 to harvest so the interview never happens twice — note that blueprint's hunt list does not yet include scope docs; that enabling one-line edit to /blueprint is deferred work (see Out of scope), and until it lands Tony points /blueprint at the doc himself. Research prior art: the "Grill Marks" dossier (https://claude.ai/code/artifact/1f0c95e6-28a8-43b5-a490-6d70f8eba840), Tony-commissioned 2026-08-18 on Matt Pocock's viral grill-me pre-build interview skill; this design steals the dossier's verified mechanics and rejects grill-me's statelessness and interviewer-led posture.

Constraints: The skill is one file at `~/.claude/skills/precon/SKILL.md`, authored in house style (intro, steps, rules, output block, "What NOT to do" — match the voice and structure of `~/.claude/skills/blueprint/SKILL.md`). Loop skills live unversioned in `~/.claude/skills/` (no git repo; Time Machine covers backup), which is why this plan lives in `~/Documents/skill-lab/` beside Tony's prior skill build plans (`fb-skill-build-plan.md`, `shutdown-skill-build-plan.md`) rather than in a repo docs/ folder. Hard behavioral constraints, each from Tony's rulings 2026-08-19: user-invoked only, never model/auto-invoked; never researches (no web, no research docs, no research subagents — property-only lookups: the repo and docs already in the project); never invokes any skill; never builds anything, prototypes included; anything sent to an external model goes out only on Tony's explicit word in that run. The exit test's readers are: a local zero-context Claude subagent (the default), or a GPT model via the codex MCP (`gpt-5.6-sol` pinned, another GPT selectable — pinned id and refresh procedure live in jpb's SKILL.md; precon borrows that transport only, never jpb's box mandate or verdict machinery). No runnable test suite applies; verification is manual per criteria below.

Out of scope:
- A research skill — reason: Tony's ruling: research is his, on his initiative; he may build a separate skill for it later. Precon's parked "needs research" items are designed as that future skill's input.
- Editing /blueprint to auto-harvest scope docs ("if a scope doc exists, harvest it first") — reason: separate one-line change to another skill, on Tony's word, not part of this build.
- Build-loop map socket update — the map is a visual artifact of the build loop Tony iterates in a separate session; its dashed "Sharpen the idea" placeholder box eventually becomes a solid /precon box — reason: cosmetic picture change owned by that session, agreed 2026-08-19.
- Change-order machinery — reason: re-invoking /precon on an existing scope doc is the scope-level change path; the map's "change orders" socket stays an honest future slot.
- Question caps — reason: steer in plain language; caps conflate under-specified ideas with bad questioning (prior-art out-of-scope ledger reasoning, adopted in discussion).
- AskUserQuestion/harness UI for rounds — reason: plain-text numbered rounds; the Grill Marks dossier (§ 03, cited in Intent) records field reports of harness question UI corrupting interview sessions.
- Primitive + front-door skill architecture — reason: single inlined file; "skill doesn't load skill" is a documented failure in the prior art.
- Auto-filing scope docs into `~/Developer/_ideas/` or auto-moving them into repos — reason: Tony's Q1 answer: "just build the doc"; relocation is his.
- Multi-model cold-read panel (DeepSeek, Gemini, Opus/Fable seats) — reason: Tony's rulings 2026-08-19 settled the cold read on the local Claude reader as default plus a GPT-family option; the wider panel is the rejected option.

## Slice A — the SKILL.md
Goal: write the complete /precon skill file implementing every decided mechanism, in house style.
Requirements:
- R1 — User-invoked only. The stage stays free-flowing by default; the skill's description must not invite model auto-invocation. (Ruling: "leave it free-flowing in my own way.")
- R2 — Harvest first: on invocation, mine the conversation so far and the property (repo, existing project docs) before asking anything. Invoked cold with no prior discussion, listening is step one: Tony talks, the skill captures.
- R3 — Property line: facts the property can answer are looked up, never asked (facts vs decisions). The skill never leaves the property: no web, no research dispatch. A question needing outside research is parked and tagged `needs research`; parked items are Tony's break points — natural places to pause the session while he does the research himself, and pick back up after.
- R4 — Triage before interviewing: classify the idea aloud to set interview depth, overridable by Tony. The tiers: **napkin** (describable in a sentence or two; one short round or none), **bounded** (a normal feature or project with known edges; a few rounds), **architectural** (spawns repos or systems, or changes how other things work; full depth). Recommending "this doesn't need a scope doc, go straight to /blueprint" is a valid outcome for napkin-grade ideas.
- R5 — Rounds: batched frontier rounds, a few questions each; only questions whose prerequisites are settled; every question numbered with a ➡️ recommendation, answerable by number.
- R6 — Only-if-it-differs: small reversible calls are decided and logged as assumptions in the ledger, not asked. Questions are spent where Tony's answer could plausibly differ from the recommendation.
- R7 — The board: every round opens with the header `Round N — <tier> — board: decided / assumed / parked / open your-calls` (tier welded in so triage cannot be silently skipped; counts recounted from the doc, where "your-calls" are decisions identified but not yet put to Tony or answered). The board is mid-interview state; it deliberately differs from R14's final report tallies. (Amended 2026-08-20 per Tony.)
- R8 — Ledger as you go: every settled decision lands in the scope doc the moment it settles, tagged `decided`, `assumed` (with why it didn't earn a question), or `parked` (with tag: `needs research`, `needs prototype`, or `waiting on <x>`). Every ledger line traces to Tony's words or an answered question — the skill records, it never decides for him.
- R9 — Suggest only, never act: when the idea deserves an outside panel it may say "this smells like a /jpb" (Tony's multi-model product-box consensus skill, `~/.claude/skills/jpb/`) in one line; when a question needs something to react to it may say "this would be easier with a throwaway to look at." It never invokes a skill, never builds a prototype, never queues anything.
- R10 — Scope doc, fixed format, written to `<repo>/docs/<idea>-scope.md` — the repo the idea unambiguously belongs to, whether or not the session was invoked inside it (that call ledgered as `assumed` when it wasn't) — else `~/Documents/<idea>-scope.md`; the path is printed in the report block; relocation is Tony's. (Path rule amended 2026-08-20 per Tony, matching smoke-run behavior.) Exact template:

  Load-bearing: these are the sections /blueprint Step 1 is meant to harvest once its deferred one-line edit lands (see Out of scope); keep them exact.

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

- R11 — Resumable: invoked with an existing scope doc, the skill re-opens its parked and open items and continues the ledger in place — one living doc, never a fork. This is also the scope-level change-order path.
- R12 — Exit test, after the frontier empties: offer the cold read as one numbered question with a recommendation, default the local reader. Options: (a) local Claude reader — a fresh zero-context subagent reads the scope doc read-only and reports confusions in chat (the default and the recommendation); (b) GPT Sol via codex MCP (`gpt-5.6-sol`), or another GPT model on Tony's pick — external, so it sends only on his word in that run. The reader gets a cold-reader prompt (zero context supplied: what's unclear, what would you ask before building this); the reader's raw findings are written verbatim to `~/Documents/precon-cold-reads/<idea>-cold-read-<date>.md` with a top summary of what was taken vs left behind and per-item dispositions (surfaced / absorbed / left downstream), pointer recorded in the scope doc's Research section (amended 2026-08-20 per Tony); returned confusions reopen branches. Declining entirely is a clean path. No other readers exist — no multi-model panel (Tony's rulings 2026-08-19).
- R13 — The gate: the session ends by reading the record back and stopping. Ending the interview requires a one-line written justification that every branch was visited or explicitly parked. It never starts building and never auto-invokes /blueprint.
- R14 — Report block in house style, required fields: `PRECON: <idea>`, doc path, counts (decided / assumed / parked / out of scope), parked items one line each with tags, `Next: /blueprint when ready.`, and a `SKILL NOTE:` line only when a rule was worked around (house discipline).
- R15 — "What NOT to do" section covering, at minimum: don't research or leave the property; don't ask what the property can answer; don't invoke any skill or build anything; don't drip questions one at a time; don't cap questions; don't invent or embellish ledger entries beyond what Tony said; don't blow the gate; don't use harness question UI; don't auto-file or move the scope doc.
Acceptance criteria:
- AC1: `~/.claude/skills/precon/SKILL.md` exists and `/precon` shows in the skill listing — verify: manual: `ls ~/.claude/skills/precon/` and check the session's skill list.
- AC2: A reviewer can point to the line(s) implementing each of R1–R15 — verify: manual: read-through mapping each requirement to text.
- AC3: The scope-doc template appears verbatim with all seven elements (title line, Intent, Decisions with the three tags, Out of scope, Research, Open, Next) — verify: manual: compare against R10.
- AC4: No instruction anywhere in the file directs web access, research, skill invocation, or building — verify: manual: adversarial read for contradictions.
Footprint: `~/.claude/skills/precon/SKILL.md` (new file, new directory).
Not in this slice: any live run; any edit to jpb, blueprint, or the map.
Depends on: nothing
Status: signed off

## Slice B — live smoke test
Goal: one real /precon run end to end with Tony on a small genuine idea; every mechanism observably fires; fixes fold back into the SKILL.md.
Requirements (numbered B-R to keep Slice A's R-numbers unambiguous):
- B-R1 — The test idea is real (one from `~/Developer/_ideas/` or a fresh one Tony picks), not a synthetic toy.
- B-R2 — Defects found during the run are fixed in `~/.claude/skills/precon/SKILL.md` within this slice; material behavior changes get one more run-through of the affected step.
Acceptance criteria:
- AC1: Harvest visibly precedes the first question — verify: manual: transcript order.
- AC2: Triage classification stated aloud before round one — verify: manual: transcript.
- AC3: Every question numbered with a ➡️ recommendation; at least one answered by number worked — verify: manual: transcript.
- AC4: The board line with counts opens each round — verify: manual: transcript.
- AC5: Zero research actions in the run; any research need became a `parked: needs research` ledger line — verify: manual: transcript + scope doc.
- AC6: Scope doc written at the correct path with every template section present — verify: manual: open the file, compare to Slice A's R10.
- AC7: Exit test offered the cold read with the local Claude reader as the recommended default and the GPT option named; nothing external was sent without Tony's word (picking local, or declining entirely, counts as a pass) — verify: manual: transcript.
- AC8: Session ended with read-back, justification line, and a full stop — no building, no /blueprint — verify: manual: transcript.
- AC9: Report block printed with all of Slice A R14's fields — verify: manual: transcript.
Footprint: `~/.claude/skills/precon/SKILL.md` (fixes); one scope doc at the Slice A R10 path.
Not in this slice: acting on the test idea itself; building anything the scope doc describes.
Depends on: Slice A
Status: signed off

## Build assumptions
2026-08-19 · Slice A:
- Board line rendered as `decided N · assumed N · parked N · open your-calls N` — R7 names the counts but not an exact string · builder call
- Exit test rendered as one numbered question with three options (1 local reader ➡️ recommended, 2 GPT via codex, 3 decline) — R12 names the offer shape loosely · builder call
- "What NOT to do" carries 11 items — R15's nine plus explicit no-external-send-without-word and no-auto-/blueprint lines, both restating hard constraints from the plan · builder call

## Deviations
2026-08-19 · Slice A: none. (Rule 7 branch/before-photo N/A per the plan's Constraints — skills dir is unversioned, no test suite applies.)
2026-08-20 · Slice B: closed per user — B-R2's run-through of the materially changed steps (3 and 5) waived by Tony ("we can close out slice B"); the changed mechanisms get watched live at the next real sitting instead · per user. Inspection record: smoke run graded twice — in-session grading (8 pass / 2 partial / 0 fail) and the monitor session's independent review (~/Documents/skill-lab/precon-smoke-review-2026-08-20.md); AC2 dispute resolved with transcript evidence (triage was stated aloud); both partials (AC6 path, AC9 SKILL NOTE) retired by the Tony-authorized path-rule amendment. No separate /signoff run — the monitor's outside review stands as the independent inspection · per user.

## Discovered
2026-08-20 · Post-close, per user: the deferred /blueprint hunt edit landed — blueprint Step 1's Prior docs bullet now harvests a `docs/<idea>-scope.md` matching the named feature first, with a list-and-ask tiebreak when more than one could match (never a silent pick). The plan's Out of scope entry #2 is thereby executed on Tony's word, not violated.
2026-08-20 · Slice B fold (per user, all four authorized): board header now `Round N — <tier> — board: ...` with recount-from-doc (monitor fix 1 + smoke defect: board-count drift); path rule amended to owning-repo (monitor fix 2; also retires the missing-SKILL-NOTE defect by legalizing the behavior); cold-read findings doc at `~/Documents/precon-cold-reads/` with top summary + per-item dispositions (Tony's mechanism, summary requirement his); ledger appends pinned to the Decisions tail (smoke defect: two lines landed under Research and needed repair). Monitor's AC2 FAIL disputed with transcript evidence — triage WAS stated aloud before round 1 ("Triage: bounded... override me in a word"); fix 1 taken as insurance regardless. R7/R10/R12 mirrored in this plan same date.
2026-08-20 · Slice B (smoke, live): GPT cold reader must carry `web_search: disabled` — the smoke run's operator applied jpb's parity setting unprompted; the skill text never required it (was review MINOR re: SKILL.md:78). Fixed on Tony's word during the run: one line added to SKILL.md Step 5 option 2, applied by the monitoring session.

## Punch list

### 2026-08-19 — review: Slice A
- MAJOR · SKILL.md:8,57 · blueprint hand-off overstated: spec's "once its deferred one-line edit lands / until then Tony points /blueprint at the doc himself" qualifier dropped · Tony runs /blueprint cold expecting auto-harvest; the re-interview happens anyway · Slice A review
- MAJOR · SKILL.md:47,67,106 · out-of-scope channel undefined: report counts `out of scope N` and template has the section, but no step says how items get there · sessions file "not doing X" rulings divergently; counts and doc content differ · Slice A review
- MAJOR · SKILL.md:30,47,57,104 · scope-doc lifecycle undefined at the edges: creation timing vs ledger-as-you-go, slug naming, napkin no-doc exit vs mandatory Doc/counts report fields · orphan doc after napkin triage, or forked doc when a guessed slug misses the existing one · Slice A review
- MINOR · SKILL.md:85,69 · gate justification ("every branch visited or explicitly parked") vs template's Open section · literal session refuses to end with Open items or force-parks them · Slice A review
- MINOR · SKILL.md:42 · board's "open your-calls" count sourced "from the ledger" but open items are never written to disk · count not reconstructible after resume/compaction · Slice A review
- MINOR · SKILL.md:20 · existing-doc discovery has no stated mechanism · session in a repo misses a ~/Documents doc and forks · Slice A review
- MINOR · SKILL.md:19,57 · "inside a repo" boundary and property extent outside a repo undefined · divergent doc paths and lookup surfaces · Slice A review
- MINOR · SKILL.md:85 · destination of the gate's one-line written justification unspecified · one session appends it to the fixed-format doc, another to chat · Slice A review
- MINOR · SKILL.md:24,77,91,116 · property-line absolutism never carves out the two sanctioned actions (exit-test reader, Tony-worded GPT send) · rule-literal session refuses the default exit test · Slice A review
- MINOR · SKILL.md:77 · reader "read-only" not operationalized (no agent type named) · full-tool reader edits the doc or researches its own confusions · Slice A review
- MINOR · SKILL.md:81 · re-offer of the exit test after confusion-driven rounds unstated · sessions diverge on looping Step 5 · Slice A review
- MINOR · SKILL.md:67-69 · multi-item rendering undefined for single-line template sections under "keep it exact" · divergent doc shapes for the load-bearing format · Slice A review
- MINOR · SKILL.md:60 · title-line date semantics on resume undefined · trivial divergence · Slice A review
- MINOR · SKILL.md:78 · "refresh procedure" named as living in jpb but jpb has no section by that name (it is the "roster freshness" preflight) · fresh session hunts a nonexistent heading · Slice A review
- MINOR · SKILL.md:78 · codex transport config unspecified (jpb's parity bundle disables web_search; precon doesn't say carry it) · GPT reader web-searches during the cold read · Slice A review
- MINOR · SKILL.md:118 · NOT-list "don't invoke any skill, ever" lacks the gate-collapse carve-out Step 6 acknowledges · literal session refuses a collapsed "precon it and blueprint it" invocation · Slice A review
- MINOR · SKILL.md:106 · report has no Open count/listing (matches spec R14 as written — spec-level seam) · Tony ends a sitting without seeing open threads in chat · Slice A review

### 2026-08-19 — recheck: Slice A
- MAJOR · SKILL.md:8,57 · (blueprint hand-off overstated: deferred-edit qualifier dropped) · fixed — caveat now at SKILL.md:8 and :59, all other blueprint mentions swept clean; verified by fresh reviewer against current source
- MAJOR · SKILL.md:47,67,106 · (out-of-scope channel undefined) · fixed — new "The out-of-scope channel" paragraph at SKILL.md:55 defines trigger, destination, traceability, and report-count linkage
- MAJOR · SKILL.md:30,47,57,104 · (scope-doc lifecycle undefined at the edges) · fixed — birth-after-triage + slug rule + existing-doc lookup at SKILL.md:59, napkin no-doc exit with `Doc: none` report shape at SKILL.md:30; template block re-diffed byte-identical to spec R10, no fix-introduced defects
