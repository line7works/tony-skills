# Architect skill — build plan (2026-08-21)

Intent: /architect is the missing drawings step in Tony's build pipeline — the station between /precon (which settles an idea's scope in a scope doc) and everything downstream (/sunrise provisions infrastructure, /blueprint slices work, /build executes). Today architecture decisions get made implicitly: /blueprint decides structure silently while slicing, and /sunrise's archetype template provisions databases and hosting at the moment of least information, before scope even exists. /architect fixes that with one interview producing one architecture doc: the least structure that serves a named first user's walkthrough without becoming demolition later. Two passes run as one negotiation — delivery (who is the first real person to touch this, by what date, doing what) and architecture (2–3 genuinely distinct candidate structures grilled against that target, then checked against the full vision for one-way doors). The governing distinction: decisions are made at full-vision quality, construction happens at MVP quantity — deciding is free, provisioning is not, so one-way choices (language, database kind, repo shape, data shapes, platform) are settled up front while their construction waits. Tony is a solo developer new to engineering who grasps concepts fast but cannot yet evaluate architecture proposals; the skill exists so the AI's first plausible proposal never ships unexamined. Full decision provenance: the scope doc at `~/Documents/architect-scope.md` (the spec of record; its Decisions ledger includes two cold reads absorbed), plus the pre-precon findings doc at `~/Documents/handoffs/2026-08-21-architecture-skill-sunrise-sunset-findings.md` (which also records the parked "/blueprint post-draft cold review" idea cited under Out of scope).

Constraints: The skill is one file at `plugins/architect/skills/architect/SKILL.md` in this repo (scope doc ruling 2026-09-01), with a `plugins/architect/.claude-plugin/plugin.json` and a `.claude-plugin/marketplace.json` entry shaped like /inspect's, authored in house style (intro, steps, rules, output block, "What NOT to do" — match the voice and structure of `plugins/precon/skills/precon/SKILL.md` and `plugins/blueprint/skills/blueprint/SKILL.md`). Skills are versioned in this repo since the 2026-09-01 migration; a session runs the marketplace-installed copy, so the skill reaches a machine only after the change lands on `main` and that machine runs `/plugin update architect@tony-skills`. This plan originally lived in `~/Documents/skill-lab/` and moved to `~/Developer/tony-skills/docs/` in the 2026-09-01 skills migration, inside /build's hunt path. Hard behavioral constraints, each from the scope doc's Decisions ledger: strictly user-invoked, never auto-triggered; takes the /precon scope doc as its input; never provisions anything (doc only — execution belongs to /sunrise); grilling is Claude-only inside the run; property line as /precon's — the repo, project docs, and Claude's own knowledge only, no web, no research subagents, factual unknowns that need outside checking become marked lines in the architecture doc for Tony to resolve (scope doc ledger line, from the blueprint interview 2026-08-21); the only sanctioned external send is the blind review, on Tony's explicit word in that run. Until the /sunrise and /blueprint reworks land (a separate future build), Tony hand-points those skills at the architecture doc. No runnable test suite applies; verification is manual per criteria below.

Out of scope:
- /sunrise + /sunset rework (doc-driven provisioning, archetype question removal, teardown parity) — reason: Tony's ruling (precon Round 1 Q4): follow-on build after /architect ships, informed by what it teaches; findings captured in `~/Documents/handoffs/2026-08-21-architecture-skill-sunrise-sunset-findings.md`.
- Hierarchical /blueprint (vertical slices → sub-blueprints) and a standing /blueprint post-draft cold review — reason: Tony parked both for a later blueprint talk; both recorded in the same findings doc.
- Standalone Occam's razor skill — reason: absorbed; the razor is /architect's grilling criterion, not its own skill (Tony, 2026-08-21).
- Named tiers/versions of /sunrise — reason: Tony ruled the architecture doc is the tier; no editions.
- A designed visual system for the end-of-run artifact — reason: Tony's ruling ("we'll establish what it looks like over time"): the visual's look evolves run by run; this build must not over-spec it.
- Editing /precon, /blueprint, /sunrise, or any other skill — reason: /architect is a new file; the interim hand-pointing rule covers integration.
- Multi-model review panel — reason: the scope settles on one blind reviewer per run (pinned GPT, or a substitute on Tony's pick — never a second reviewer added).
Plan: inspected 2026-08-30 by claude-fable-5 · 0 BLOCKER · 2 MAJOR · 17 MINOR
Plan: inspected 2026-08-30 by claude-fable-5 · 0 BLOCKER · 4 MAJOR · 4 MINOR · 1 QUESTION
Plan: inspected 2026-08-30 by gpt-5.6-sol · 0 BLOCKER · 2 MAJOR · 0 MINOR
Plan: inspected 2026-09-01 by claude-fable-5-1 · 1 BLOCKER · 7 MAJOR · 11 MINOR
Plan: inspected 2026-09-01 by gpt-5.6-sol · 2 BLOCKER · 15 MAJOR · 8 MINOR
Plan: inspected 2026-09-01 by gemini-3.1-pro-high · 2 BLOCKER · 7 MAJOR · 14 MINOR

## Slice A — the SKILL.md
Goal: write the complete /architect skill file implementing every decided mechanism from the scope doc, in house style.
Requirements:
- R1 — User-invoked only. The skill runs when Tony types /architect; its description must state it is strictly user-invoked and must not describe auto-invocation triggers.
- R2 — Input gate: the input is a /precon scope doc (path given in the invocation, or found beside the project — when more than one could match, list and ask, never silently pick). Invoked without one, the skill stops and opens a discussion on why it's being run docless — a conversation gate, not a silent refusal. The run may proceed only when the discussion lands on a reason; that reason is recorded at the top of the architecture doc. Docless runs take the current discussion as their input.
- R3 — Exit ramp: the interview's first question is "is there a system here at all?" A static-page-grade idea (no server, no data to keep, no moving parts) ends the interview immediately after that question and still writes a tiny architecture doc (a few lines: static page, no system, no provisioning beyond a repo) — "no doc" stays reserved for ideas that never saw /architect. Exit-ramp runs still end with the visual and the blind-review offer: the scope's "every run" rulings carry no carve-out.
- R4 — Interview shape: two passes run as one negotiation, in three steps. Step 1 (delivery pass): the walkthrough target — a named real person (never "users"), the target date of the walkthrough session, and what that person must be able to do. The walkthrough is the dated session where the named first user actually touches the built thing. Step 2 (architecture pass): candidate structures grilled against that target. Step 3 (architecture pass): the one-way-door check against the full vision. The interview stays short — depth scales with the system's size; heavy ceremony here delays the MVP the skill exists to accelerate (the scope's narrowness guardrail).
- R5 — The razor is the grilling criterion: every component must point at a walkthrough requirement or it is cut from v0. No server unless something needs a server; no database unless something must be remembered.
- R6 — Candidates: step 2 forces 2–3 genuinely distinct candidate structures into the open — distinct means differing in at least one one-way-door category (platform, storage, repo shape, language, or data shape), never variations of one shape (scope doc Decisions ledger, ruled 2026-09-01) — with what each assumes and what each makes expensive later. Never a single proposal for Tony to nod at. Tony picks; the pick and the rejected candidates' one-line whys are recorded in the run log (their home — the four-part output stays four parts).
- R7 — One-way doors: step 3 brings the full vision in only to verify nothing in v0 blocks it. The five named categories — language, database kind, repo shape, data shapes, platform — are the checklist floor, not a cap. One-way decisions are made at full-vision quality; everything else stays two-way. Banked decisions are recorded, not provisioned (e.g. "becomes Postgres when scores go remote").
- R8 — Output doc at `~/Documents/<slug>-architecture.md` pre-repo, where `<slug>` is the precon scope doc's slug (a docless run's slug is the project's working name, settled in the gate discussion). Four required parts: (1) walkthrough target; (2) v0 drawing — component list (what exists) + plain-prose data flow (what talks to what) + one simple diagram; (3) poured-concrete list (the one-way decisions — one list, two names); (4) deferred list — banked decisions plus deliberately-not-built items, each with a line confirming its door stays open. A docless run's reason header sits at the top. Relocating the doc into a repo is Tony's (or the future /sunrise rework's), never this skill's.
- R9 — Re-runs: one living architecture doc per project, never a fork. A re-run (idea blossomed, new precon, changed direction) continues the doc: a run-log section records each run's date, trigger, and what changed; superseded decisions are struck through, never deleted — the trail Tony asked for ("we ran it once; now we're running it again because things have changed").
- R10 — Never provisions: the skill creates no repos, databases, hosting, or accounts, installs nothing, and invokes no other skill. Doc and visual only.
- R11 — Property line: lookups are the repo (if any), the project's existing docs, and Claude's own knowledge. No web access, no research subagents. A factual unknown that genuinely needs outside checking becomes a marked line in the architecture doc for Tony to resolve.
- R12 — The visual: every run ends by rendering a self-contained HTML visual of what was decided — the systems chosen and what each does/provides for the project — written beside the architecture doc and published as a private Claude Artifact, the same artifact URL kept across re-runs (URL recorded in the architecture doc; a re-run finding no recorded URL publishes fresh and records it). The visual is a projection re-rendered from the doc; the markdown stays the record. Its design is deliberately unspecified and evolves run by run — keep the first version plain; do not build a design system.
- R13 — Blind review: after the doc and visual are done, the skill asks Tony once whether he wants an outside-model review. On his word only: the external model receives the precon scope doc ONLY — never Claude's architecture, never chat context — via the codex MCP, using the pinned model named in jpb's SKILL.md preflight (`gpt-5.6-sol` at time of writing; the reference wins if the pin moves; a different model on Tony's pick per run substitutes, never adds a second reviewer), with `web_search: disabled`, read-only sandbox, and a neutral empty cwd. It returns its own full architecture take, saved verbatim to `~/Documents/architect-reviews/<slug>-review-<date>.md` (the skill creates that directory on the first blind review if it is absent — the one sanctioned mkdir). The skill then walks Tony through every substantive disagreement between the two takes — components built vs cut, structure, one-way-door calls, deferrals — and Tony rules each one in discussion; the architecture doc changes only where he rules. Nothing merges silently.
- R14 — Report block in house style, required fields: `ARCHITECT: <project>`, doc path, artifact URL, run number (from the run log), counts (components in v0 / poured-concrete decisions / deferred items), review status (declined | done at <path>), a `Next:` line naming the interim hand-pointing and the doc's downstream contract (Tony points /sunrise at the doc to provision exactly what it lists, and /blueprint at it to slice with the user-touchable slice up front), and a `SKILL NOTE:` line only when a rule was worked around.
- R15 — "What NOT to do" section covering, at minimum: don't auto-invoke; don't proceed docless without the discussion landing on a recorded reason; don't provision anything or invoke any skill; don't leave the property (no web, no research subagents); don't send anything external without Tony's word in that run; don't show the external reviewer Claude's work; don't merge review differences silently; don't skip the candidates and present one proposal; don't fork a second architecture doc; don't delete or rewrite run-log history; don't over-spec the visual; don't publish the visual anywhere public (the arcade included).
Acceptance criteria:
- AC1: `plugins/architect/skills/architect/SKILL.md` and `plugins/architect/.claude-plugin/plugin.json` exist, `.claude-plugin/marketplace.json` lists `architect`, and after `/plugin install architect@tony-skills` /architect shows in the session's skill listing — verify: manual: `ls plugins/architect/skills/architect/`, `grep architect .claude-plugin/marketplace.json`, and check the skill list.
- AC2: A reviewer can point to the line(s) implementing each of R1–R15 — verify: manual: read-through mapping each requirement to text.
- AC3: The output-doc specification in the file names all four required parts, the slug rule (including the docless case), the docless reason header, and the run log — verify: manual: compare against R8/R9.
- AC4: No instruction anywhere in the file directs provisioning, web access, research subagents, skill invocation, auto-invocation, or an external send without Tony's word — verify: manual: adversarial read for contradictions.
- AC5: The blind-review passage carries all four transport guards (scope-doc-only payload, web_search disabled, read-only sandbox, neutral cwd), pins the model by reference, and states the substitute-not-second-reviewer rule — verify: manual: compare against R13 and against the pinned id in `plugins/jpb/skills/jpb/SKILL.md`.
Footprint: `plugins/architect/skills/architect/SKILL.md` and `plugins/architect/.claude-plugin/plugin.json` (new files, new directory); one new entry in `.claude-plugin/marketplace.json`; a roster line in `README.md` and `CLAUDE.md`.
Not in this slice: any live run; any edit to any other skill; any change to the scope doc.
Depends on: nothing
Status: not started

## Slice B — live smoke test
Goal: one real /architect run end to end with Tony on a genuine project; every mechanism the run's path reaches observably fires; fixes fold back into the SKILL.md.
Requirements:
Numbered B-R to keep Slice A's R-numbers unambiguous.
- B-R1 — The test subject is a real precon scope doc Tony picks at the start of the slice. Not a synthetic toy. If no scope doc suits, the slice stops and reports; any /precon run to produce one happens outside this slice on Tony's word.
- B-R2 — Defects found during the run are fixed in `plugins/architect/skills/architect/SKILL.md` within this slice (then reinstalled via `/plugin update architect@tony-skills` before the re-run of the affected step); material behavior changes get one more run-through of the affected step.
- B-R3 — The run ends with an evidence note at `docs/evidence/architect-smoke-run.md` in this repo recording, per acceptance criterion, what was observed (quoted lines from the run where a criterion turns on wording). The session transcript is not evidence; the note and the files are what /signoff inspects.
Acceptance criteria:
- AC1: The input gate fires correctly for the chosen path (scope doc accepted, or the docless discussion runs and its reason lands at the top of the doc) — verify: manual: evidence note.
- AC2: The exit-ramp question is asked first and visibly steers the run: a "no system" answer skips the candidate round and produces the tiny doc; a real system gets all three steps — verify: manual: evidence note.
- AC3: Step order holds: walkthrough target before candidates, candidates before the one-way-door check — verify: manual: evidence note.
- AC4: 2–3 candidates presented, each differing in at least one poured-concrete category per Slice A R6, with assumptions and later-expense stated, before Tony picks — verify: manual: evidence note.
- AC5: Architecture doc written at `~/Documents/<slug>-architecture.md` with all four parts (or the tiny exit-ramp form) and the run log, matching Slice A R8/R9 — verify: manual: open the file.
- AC6: The visual renders and publishes as an Artifact (private by default — not posted to the arcade or any public host), with its URL recorded in the doc and reported — verify: manual: open the artifact URL, confirm the doc records it.
- AC7: The blind review is offered exactly once at the end; nothing external sends without Tony's word (declining counts as a pass); if run, the review file exists at the R13 path and disagreements were walked with Tony ruling each — verify: manual: evidence note + file.
- AC8: Zero provisioning, zero skill invocations, zero web/research actions in the run — verify: manual: evidence note.
- AC9: Report block printed with all of Slice A R14's fields — verify: manual: evidence note.
Footprint: `plugins/architect/skills/architect/SKILL.md` (fixes); one architecture doc; one artifact; possibly one review file (and `~/Documents/architect-reviews/` if created); `docs/evidence/architect-smoke-run.md`.
Not in this slice: acting on the tested idea itself; building anything the architecture doc describes; re-run mechanics beyond what one sitting exercises (the run log must still be written for run 1).
Depends on: Slice A
Status: not started

## Build assumptions

## Deviations

## Discovered

## Handoffs

## Punch list

### 2026-08-30 — inspect: plan
- MAJOR · architect-skill-build-plan.md:24 · R6 defines "distinct" via poured-concrete categories the scope doc never ruled · builder hard-codes a definition Tony never made and Slice B AC4 grades against it · claude-fable-5
- MAJOR · architect-skill-build-plan.md:5 · plan lives outside /build's hunt path (~/Documents/skill-lab/) · bare /build or /ship cannot find the doc; loop stalls or forks · claude-fable-5
- MINOR · architect-skill-build-plan.md:48 · "trash-can game example from the design discussion" untraceable in any record · cold builder chases a candidate that may not exist (converged: code-book + traceability) · claude-fable-5
- MINOR · architect-skill-build-plan.md:24 · R6 routes pick + rejected-whys to the run log without a scope ruling · record location baked in undecided · claude-fable-5
- MINOR · architect-skill-build-plan.md:20 · R2 scope-doc discovery mechanics (list-and-ask, docless fallback) unsourced · builder writes undecided mechanism as settled · claude-fable-5
- MINOR · architect-skill-build-plan.md:26 · R8 docless slug rule invented · plausible gap-fill presented as spec · claude-fable-5
- MINOR · architect-skill-build-plan.md:22 · R4 softens scope's "~three answers" guardrail to "depth scales" · elastic guardrail where spec gave a hard one · claude-fable-5
- MINOR · architect-skill-build-plan.md:31 · R13 disagreement taxonomy is elaboration beyond scope line 32 · unsourced detail in decided voice · claude-fable-5
- MINOR · architect-skill-build-plan.md:32 · R14 report counts/run-number have no scope source · house-style invention as required fields · claude-fable-5
- MINOR · architect-skill-build-plan.md:30 · R12 URL-recording + republish-if-missing mechanics unruled · mechanical gap-fill as spec · claude-fable-5
- MINOR · architect-skill-build-plan.md:31 · ~/Documents/architect-reviews/ does not exist and plan never sanctions creating it · first live review fails or unsanctioned mkdir · claude-fable-5
- MINOR · architect-skill-build-plan.md:26 · R8 unconditional ~/Documents/ home conflicts with precon's repo-first doc convention · project's spec docs split across locations · claude-fable-5
- MINOR · architect-skill-build-plan.md:52 · Slice B AC2 states both branches but one run reaches one · untaken branch ungradeable · claude-fable-5
- MINOR · architect-skill-build-plan.md:36 · Slice A AC2 "point to the line implementing each R" is a judgment call at the edges · verdict becomes taste · claude-fable-5
- MINOR · architect-skill-build-plan.md:38 · AC4 "adversarial read" proves a universal negative with no stopping rule · pass/fail depends on reader stamina · claude-fable-5
- MINOR · architect-skill-build-plan.md:5 · no runnable check anywhere and no evidence the rule-6 smell was flagged and accepted · flagged-and-waived indistinguishable from skipped · claude-fable-5
- MINOR · architect-skill-build-plan.md:35 · AC numbering restarts per slice while requirements got B-R prefixes · "AC5" ambiguous to /recheck checklist assembly · claude-fable-5
- MINOR · architect-skill-build-plan.md:7 · Out of scope rendered as bullets vs templated line field · downstream descope-evidence parsing untested against multi-line shape · claude-fable-5

### 2026-08-30 — inspect: plan
- MAJOR · architect-skill-build-plan.md:24 · (R6 defines "distinct" via poured-concrete categories the scope doc never ruled) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:5 · (plan lives outside /build's hunt path (~/Documents/skill-lab/)) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:48 · ("trash-can game example from the design discussion" untraceable in any record) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:24 · (R6 routes pick + rejected-whys to the run log without a scope ruling) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:20 · (R2 scope-doc discovery mechanics (list-and-ask, docless fallback) unsourced) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:26 · (R8 docless slug rule invented) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:22 · (R4 softens scope's "~three answers" guardrail to "depth scales") · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:31 · (R13 disagreement taxonomy is elaboration beyond scope line 32) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:32 · (R14 report counts/run-number have no scope source) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:30 · (R12 URL-recording + republish-if-missing mechanics unruled) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:31 · (~/Documents/architect-reviews/ does not exist and plan never sanctions creating it) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:26 · (R8 unconditional ~/Documents/ home conflicts with precon's repo-first doc convention) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:52 · (Slice B AC2 states both branches but one run reaches one) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:36 · (Slice A AC2 "point to the line implementing each R" is a judgment call at the edges) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:38 · (AC4 "adversarial read" proves a universal negative with no stopping rule) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (no runnable check anywhere and no evidence the rule-6 smell was flagged and accepted) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:35 · (AC numbering restarts per slice while requirements got B-R prefixes) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:7 · (Out of scope rendered as bullets vs templated line field) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:66 · ledger scaffold missing the `## Handoffs` section blueprint now mandates (code updated 2026-08-30 17:49) · /handoff has no append target mid-loop · claude-fable-5
- MAJOR · architect-skill-build-plan.md:48 · Slice B mutates the exact `Requirements:` heading with a parenthetical · heading-keyed downstream reads miss the block · claude-fable-5
- MAJOR · architect-skill-build-plan.md:31 · ~/Documents/architect-reviews/ absent and no slice sanctions creating it (upgraded from MINOR: Slice B AC7 depends on the write) · first blind review errors or forces unsanctioned mkdir · claude-fable-5
- MAJOR · architect-skill-build-plan.md:49 · "trash-can game example from the design discussion" has no artifact on disk anywhere (upgraded from MINOR: it is B-R1's named fallback for the slice's test subject) · cold builder hunts a record that does not exist · claude-fable-5
- MINOR · architect-skill-build-plan.md:15 · a Plan: inspected stamp sits inside the Out of scope parse range · descope-evidence harvest ingests an inspection stamp as a deferred item · claude-fable-5
- MINOR · architect-skill-build-plan.md:32 · R13's transport guards exceed the cited precon convention (read-only sandbox + neutral cwd are jpb-judge plumbing precon does not carry) · builder codifies guards the record never attached · claude-fable-5
- MINOR · architect-skill-build-plan.md:40 · AC5 enforces the invented guard set, falls with :32 · claude-fable-5
- MINOR · architect-skill-build-plan.md:3 · Intent embellishes Tony's profile beyond the record ("cannot yet evaluate architecture proposals") · character detail presented as record · claude-fable-5
- QUESTION · architect-skill-build-plan.md:5 · "Time Machine covers backup" asserted for ~/.claude/skills/ without a cited record · claude-fable-5

### 2026-08-30 — inspect: plan
- MAJOR · architect-skill-build-plan.md:24 · (R6 defines "distinct" via poured-concrete categories the scope doc never ruled) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:5 · (plan lives outside /build's hunt path (~/Documents/skill-lab/)) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:48 · ("trash-can game example from the design discussion" untraceable in any record) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:24 · (R6 routes pick + rejected-whys to the run log without a scope ruling) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:20 · (R2 scope-doc discovery mechanics (list-and-ask, docless fallback) unsourced) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:26 · (R8 docless slug rule invented) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:22 · (R4 softens scope's "~three answers" guardrail to "depth scales") · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:31 · (R13 disagreement taxonomy is elaboration beyond scope line 32) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:32 · (R14 report counts/run-number have no scope source) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:30 · (R12 URL-recording + republish-if-missing mechanics unruled) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:31 · (~/Documents/architect-reviews/ does not exist and plan never sanctions creating it) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:26 · (R8 unconditional ~/Documents/ home conflicts with precon's repo-first doc convention) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:52 · (Slice B AC2 states both branches but one run reaches one) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:36 · (Slice A AC2 "point to the line implementing each R" is a judgment call at the edges) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:38 · (AC4 "adversarial read" proves a universal negative with no stopping rule) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (no runnable check anywhere and no evidence the rule-6 smell was flagged and accepted) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:35 · (AC numbering restarts per slice while requirements got B-R prefixes) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:7 · (Out of scope rendered as bullets vs templated line field) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:49 · B-R1's "if none suits, he runs /precon on a real idea first" expands the build's prerequisites without a record · Slice B cannot complete without unagreed scope work · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:52 · Slice B treats "transcript" as verification evidence with no retention requirement or path · the live run's session dies and signoff cannot inspect AC1–AC4/AC7–AC9 · gpt-5.6-sol

### 2026-09-01 — adjudication (Tony's rulings on the 2026-08-30 inspect MAJORs)
- FIXED · R6 "distinct" definition · Tony ruled it in: scope doc Decisions ledger now carries the one-way-door-category definition (2026-09-01); R6 cites it
- FIXED · plan outside /build's hunt path · resolved by the 2026-09-01 migration to `docs/`; Constraints line updated
- FIXED · missing `## Handoffs` scaffold · added
- FIXED · Slice B `Requirements:` heading mutated · restored; numbering note moved to a sentence beneath it
- FIXED · `~/Documents/architect-reviews/` unsanctioned · R13 now sanctions creating it on first blind review
- FIXED · "trash-can game" untraceable · struck; Tony: "i do not need the trash can game"
- FIXED · B-R1 expands prerequisites with an unrecorded /precon run (gpt-5.6-sol) · struck; no suitable scope doc is a stop-and-report
- FIXED · transcript as verification evidence (gpt-5.6-sol) · B-R3 added: evidence note at `docs/evidence/architect-smoke-run.md`; Slice B ACs verify against it
- RULED · skill home · `plugins/architect/skills/architect/SKILL.md` in this repo, catalogued in the marketplace (Tony, 2026-09-01); scope doc ledger line superseded and replaced; Constraints, Slice A AC1, both Footprints, B-R2 updated
- MINORs and the QUESTION remain open for the fresh /inspect

### 2026-09-01 — inspect: plan
- BLOCKER · architect-skill-build-plan.md:53 · B-R2 reinstalls mid-slice fixes via `/plugin update architect@tony-skills`, but the marketplace is GitHub-sourced (`~/.claude/plugins/known_marketplaces.json`: `line7works/tony-skills`; clone on `main`; installs pinned to a `main` sha) · every mid-run fix on the feature branch needs a PR + merge on Tony's word before the re-run sees it; Slice B either stalls at the git gate or re-runs the step against the stale cached copy and records a fix never exercised (converged: all three lenses) · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:38 · Slice A AC1's third clause (`/plugin install architect@tony-skills` then /architect in the listing) is unrunnable pre-merge for the same reason · /signoff cannot pass the slice on its own criteria before Tony's merge word, or a builder invents a local-marketplace workaround the plan never names (converged: all three lenses) · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:3 · the "pre-precon findings doc" `~/Documents/handoffs/2026-08-21-architecture-skill-sunrise-sunset-findings.md` cited as half of the plan's decision provenance (and again at :8, :9; scope doc :57, :58, :62) does not exist anywhere on disk · Out of scope items 1–2 rest on a record nobody can open; :9's parked "/blueprint post-draft cold review" has no surviving record at all (scope :58 parks only hierarchical /blueprint) (converged: all three lenses) · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:31 · R10 "invokes no other skill" and B AC8 (:63) "zero skill invocations" have no scope source (scope :23 says doc-only, never provisions) and collide with R12 — this environment's Artifact contract requires loading the `artifact-design` skill before writing any artifact · a builder who obeys the harness fails AC8 on a correct run; one who obeys R10 writes a skill that skips a mandated preflight (converged: traceability + code book) · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:23 · R2's "found beside the project" is undefined vocabulary; precon SKILL.md:59 names two concrete homes (`<repo>/docs/<idea>-scope.md`, else `~/Documents/<idea>-scope.md`) and the plan names neither (code book SKILL.md:74) · the builder guesses the hunt; a `docs/`-only hunt never finds `~/Documents/architect-scope.md`, the very doc Slice B would use · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:29 · R8 "pre-repo" reads as either an unconditional `~/Documents/` path or a condition on no repo existing; scope :26 itself says both "~/Documents/" and "beside the precon scope doc", which precon puts in `<repo>/docs/` for repo-owned ideas (code book SKILL.md:104) · a builder who reads it conditionally writes a `docs/` branch; B AC5 grades the unconditional path and fails a correct-by-one-reading build · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:39 · Slice A AC2 ("a reviewer can point to the line(s)") is the only check on R2–R4, R6, R7, R9–R12, R14, R15 and leaves no artifact behind (code book SKILL.md:75; upgraded from the prior MINOR because it carries eleven requirements) · pass/fail rests on reviewer taste at the edges and /signoff has no R-to-line map to check · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:151 · the `### 2026-09-01 — adjudication` block was written into `## Punch list` by the drafting session in a form no station owns: `FIXED ·`/`RULED ·` lines carry no severity and no `file:line` (code book SKILL.md:36, :65, :107) · the loop's open-filter and /signoff's sweep (signoff SKILL.md:34) match closures on `file:line` + claim and find none there; this run's closure lines below supply the sanctioned record, but the block itself stays malformed history · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:5 · Constraints label "strictly user-invoked" a hard constraint "from the scope doc's Decisions ledger" though scope :31 marks it `assumed`; the plan carries the assumed/decided distinction nowhere (R7 :39, R9 :50, R12 :51/:54, R13 :36/:37, Out of scope :14 vs :42 are all assumed lines in decided voice) and `## Build assumptions` is empty · builder and grader weigh precon's unchallenged fill the same as Tony's rulings · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:24 · R3's classification test "(no server, no data to keep, no moving parts)" is unsourced; scope :24 says "a single static page" · in-remit gap-fill in decided voice with no assumed tag · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:34 · R13 never says what mandate text accompanies the scope doc so the reviewer "returns its own full architecture take"; the cold read left that question downstream · a literal builder sends a bare doc, or invents a prompt · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:43 · Footprint's "roster line in `README.md` and `CLAUDE.md`" has no requirement or criterion, and both files count "Nineteen plugin folders / twenty skills" (CLAUDE.md:14, README.md:4-5), which the new plugin falsifies · builder adds a line and leaves a false count; nothing grades the edit (converged: all three lenses) · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:5 · `plugin.json` "shaped like /inspect's": all 19 plugin.json files carry the pre-transfer `tiny-tunnel-dot/tony-skills` repository URL while the remote and marketplace say `line7works/tony-skills` · copying the shape verbatim propagates a stale URL into a new file on a public repo · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:54 · B-R3's evidence path `docs/evidence/architect-smoke-run.md` follows neither existing convention (`docs/evidence/<build>/<slice>-<name>` per skills-migration-build-plan.md:11, or dated `docs/<skill>-smoke-run-<date>.md`) · a builder matching house convention writes a different path and /signoff grades the wrong one · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:51 · a prose sentence sits under the exact `Requirements:` heading before the bullets; the template (code book SKILL.md:47-48) has only `- <R>` bullets there · /build may carry the sentence as a requirement or drop the block's first line · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:27 · R6 names the categories "platform, storage, repo shape, language, data shape"; R7 (:28) names "language, database kind, repo shape, data shapes, platform"; B AC4 grades "per R6" · a candidate pair differing only in blob storage passes R6's wording and fails R7's · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:33 · R12 "written beside the architecture doc" gives the HTML source no filename · Slice B's grader cannot name the file that should exist next to the doc · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:34 · R13 "every substantive disagreement" and B AC7 (:62) leave "substantive" to judgment · a grader confirms listed disagreements got rulings, never that the set was complete · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:56 · Slice B AC1–AC4, AC8, AC9 verify by "evidence note" alone, which B-R3 defines as the builder's own record (signoff SKILL.md:87 treats build notes as claims); the architecture doc carries checkable traces the ACs never name (run log for AC3, rejected-candidate whys for AC4, docless header for AC1, printed report block for AC9) · the grader's only path is trusting the note · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:27 · (R6 defines "distinct" via poured-concrete categories the scope doc never ruled) · fixed — scope :18 ruled 2026-09-01, R6 cites it
- MAJOR · architect-skill-build-plan.md:5 · (plan lives outside /build's hunt path) · fixed — moved to `docs/` 2026-09-01
- MAJOR · architect-skill-build-plan.md:76 · (ledger scaffold missing `## Handoffs`) · fixed
- MAJOR · architect-skill-build-plan.md:50 · (Slice B mutates the exact `Requirements:` heading) · fixed — but see the new MINOR at :51
- MAJOR · architect-skill-build-plan.md:34 · (`~/Documents/architect-reviews/` absent and unsanctioned) · fixed — R13 sanctions the mkdir
- MAJOR · architect-skill-build-plan.md:52 · ("trash-can game" has no artifact on disk) · fixed — struck
- MAJOR · architect-skill-build-plan.md:52 · (B-R1 expands prerequisites with an unrecorded /precon run) · fixed — struck; no suitable doc is a stop-and-report
- MAJOR · architect-skill-build-plan.md:54 · (Slice B treats "transcript" as verification evidence) · fixed — B-R3 evidence note; but see the new MINORs at :54 and :56
- MINOR · architect-skill-build-plan.md:52 · ("trash-can game example" untraceable) · fixed — struck
- MINOR · architect-skill-build-plan.md:34 · (`~/Documents/architect-reviews/` never sanctioned) · fixed
- MINOR · architect-skill-build-plan.md:27 · (R6 routes pick + rejected-whys to the run log without a scope ruling) · not fixed
- MINOR · architect-skill-build-plan.md:23 · (R2 scope-doc discovery mechanics unsourced) · not fixed — escalated to MAJOR this run
- MINOR · architect-skill-build-plan.md:29 · (R8 docless slug rule invented) · not fixed
- MINOR · architect-skill-build-plan.md:25 · (R4 softens scope's "~three answers" guardrail) · not fixed
- MINOR · architect-skill-build-plan.md:34 · (R13 disagreement taxonomy is elaboration beyond scope :34) · not fixed
- MINOR · architect-skill-build-plan.md:35 · (R14 report counts/run-number have no scope source) · not fixed
- MINOR · architect-skill-build-plan.md:33 · (R12 URL-recording + republish-if-missing mechanics unruled) · not fixed
- MINOR · architect-skill-build-plan.md:29 · (R8 unconditional `~/Documents/` home conflicts with precon's repo-first convention) · not fixed — escalated to MAJOR this run
- MINOR · architect-skill-build-plan.md:57 · (Slice B AC2 states both branches but one run reaches one) · not fixed
- MINOR · architect-skill-build-plan.md:39 · (Slice A AC2 "point to the line" is a judgment call) · not fixed — escalated to MAJOR this run
- MINOR · architect-skill-build-plan.md:41 · (AC4 "adversarial read" proves a universal negative with no stopping rule) · not fixed
- MINOR · architect-skill-build-plan.md:5 · (no runnable check and no evidence the rule-6 smell was flagged and accepted) · not fixed
- MINOR · architect-skill-build-plan.md:56 · (AC numbering restarts per slice while requirements got B-R prefixes) · not fixed
- MINOR · architect-skill-build-plan.md:7 · (Out of scope rendered as bullets vs templated line field) · not fixed — refuted this run: code book SKILL.md:43 shows one line per item, inspect's stamp rule tolerates list lines, signoff reads "Out of scope lines"
- MINOR · architect-skill-build-plan.md:15 · (a `Plan: inspected` stamp sits inside the Out of scope parse range) · not fixed — inspect's own placement rule, not a plan defect
- MINOR · architect-skill-build-plan.md:34 · (R13's transport guards exceed the cited precon convention) · not fixed
- MINOR · architect-skill-build-plan.md:42 · (AC5 enforces the invented guard set) · not fixed
- MINOR · architect-skill-build-plan.md:3 · (Intent embellishes Tony's profile beyond the record) · not fixed
- QUESTION · architect-skill-build-plan.md:5 · ("Time Machine covers backup" asserted without a cited record) · resolved — line removed with the skill-home ruling

### 2026-09-01 — inspect: plan
- BLOCKER · architect-skill-build-plan.md:24 · docless runs (R2 :24, scope :35/:46) must still receive the blind-review offer every run (R3 :25, scope :41), but R13 (:35, scope :34/:40) lets the reviewer receive the precon scope doc ONLY, which a docless run does not have · Tony accepts the offer on a docless run and the skill must send a nonexistent doc, improperly send the discussion or Claude's doc, or abandon the promised review — a contradiction inherited from the record and never surfaced as open · gpt-5.6-sol
- BLOCKER · architect-skill-build-plan.md:54 · B-R2 fixes the SKILL.md then runs `/plugin update architect@tony-skills`, but the marketplace is GitHub-sourced from `main` (line 5 says so itself) · the update pulls the unchanged `main` copy and the re-run exercises stale behavior while the evidence note reports the fix as tested (converged: repo reality — `known_marketplaces.json`, clone on `main` at 83923f1, installs pinned to a `main` sha) · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:3 · the findings doc `~/Documents/handoffs/2026-08-21-architecture-skill-sunrise-sunset-findings.md` cited as decision provenance (again at :8; scope :57/:62) does not exist anywhere on this machine · /build, /signoff, and the future /sunrise rework cannot open the record Out of scope items 1–2 rest on · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:39 · AC1's `/plugin install architect@tony-skills` clause cannot pass on the feature branch — `origin/main` has no `plugins/architect` and install fetches from `main` · Slice A cannot be signed off in-session as written; needs Tony's merge word first · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:5 · Constraints (and scope :55) say "the only sanctioned external send is the blind review, on Tony's explicit word", yet R12 (:34) publishes a Claude Artifact on every run, exit-ramp runs included, with no word · publishing to claude.ai is an external send; R11/R15/AC4 and R12 contradict each other and AC4's adversarial read fails on the plan's own text · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:24 · R2's "path given in the invocation, or found beside the project — list and ask" discovery contract is not established by the record (scope :28, :35) · builder codifies an automatic filesystem hunt Tony never selected · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:24 · R2's "Docless runs take the current discussion as their input" is presented as settled; the record (scope :46) only authorizes proceeding after a recorded reason · builder treats the whole chat as the substitute scope, importing unsettled statements into the architecture · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:30 · R8's docless slug ("the project's working name, settled in the gate discussion") is invented; the record (scope :43) defines the slug only for runs with a precon doc · a later precon with a different slug produces a second architecture doc for the same project, breaking R9's one-living-doc rule · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:28 · R6's requirement that the pick and rejected-candidate whys live in the run log is not established by the record (code book rule 4: the builder decides how) · rationale for the current architecture lands only in historical entries · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:26 · R4 replaces the record's "~three answers + sorted scope" guardrail (scope :32) with "depth scales with the system's size" · builder writes a skill that runs a long interview for a large system, against the recorded limit · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:34 · R12's publish-fresh-when-no-URL-recorded and record-it mechanics are not in the record (scope :52 says only same URL kept) · a missing URL yields a second Artifact and two competing visuals · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:35 · R13 and AC5 (:43) mandate read-only sandbox and a neutral empty cwd that the record's transport line (scope :36, "same as /precon's exit test") does not carry — precon SKILL.md:80 has only `web_search: disabled`; the four-guard set is jpb Judge G's (jpb SKILL.md:191-194) · builder rejects a conforming codex review integration over guards Tony never attached (verifier's correction: `web_search: disabled` IS sourced via precon; the other two are not; converged: repo reality) · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:36 · R14's run number and three counts are not established by the record or marked as assumptions · counting semantics become the command contract and /signoff fails the build over fields Tony never approved · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:63 · AC7 treats declining the blind review as a pass, so the only live slice can finish without exercising the payload, model pin, file write, comparison, or ruling workflow · the skill ships with a broken codex path while Slice B passes · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:58 · AC2 states outcomes for both exit-ramp branches but B-R1 (:53) supplies one subject and one run · a real-system run passes Slice B while the tiny-doc path could still be broken · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:64 · AC8 asks the builder's own evidence note (B-R3 :55) to prove zero provisioning / skill / web / research actions with no retained execution record · /signoff cannot tell an observed absence from an unsupported assertion · gpt-5.6-sol
- MAJOR · architect-skill-build-plan.md:55 · B-R3's evidence path `docs/evidence/architect-smoke-run.md` matches neither existing convention (`docs/evidence/<plan>/<slice>-<name>` per skills-migration-build-plan.md:11, or dated `docs/<skill>-smoke-run-<date>.md`) and carries no date · a re-run overwrites run 1's evidence; /signoff hunting by convention misses it · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:3 · Intent's "cannot yet evaluate architecture proposals" is stronger than the record (scope :7) · builder writes the skill in a paternalistic voice on a limitation Tony did not state · gpt-5.6-sol
- MINOR · architect-skill-build-plan.md:44 · Footprint names "a roster line in `README.md` and `CLAUDE.md`" with no requirement or criterion; CLAUDE.md:14 carries no roster, only the count "Nineteen plugin folders covering twenty skills", which the new plugin falsifies · builder omits or mis-writes the edit and every Slice A criterion still passes (converged: repo reality) · gpt-5.6-sol
- MINOR · architect-skill-build-plan.md:39 · AC1's verify commands never inspect `plugins/architect/.claude-plugin/plugin.json`, and `grep architect .claude-plugin/marketplace.json` matches unrelated text · a missing manifest or a stray word satisfies the written check · gpt-5.6-sol
- MINOR · architect-skill-build-plan.md:5 · "No runnable test suite applies" with `## Build assumptions` empty and no recorded owner acceptance of manual-only verification (code book rule 6) · flagged-and-accepted indistinguishable from skipped · gpt-5.6-sol
- MINOR · architect-skill-build-plan.md:5 · `plugin.json` "shaped like /inspect's": all 19 manifests carry the pre-transfer `tiny-tunnel-dot/tony-skills` URL; the remote is `line7works/tony-skills` · copying the exemplar propagates a stale org URL into a 20th file on a public repo · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:24 · R2 "beside the project" and R8 (:30) `~/Documents/` do not name precon's two locations (precon SKILL.md:59: `<repo>/docs/` when a repo owns the idea, else `~/Documents/`) · a repo-owned idea's scope and architecture docs split across locations · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:35 · R13's "neutral empty cwd" needs a directory to exist (codex `cwd` must be a path) while "the one sanctioned mkdir" is `~/Documents/architect-reviews/` · the skill either mkdirs a second directory against the wording or reuses a non-empty one · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:34 · R12 publishes an Artifact but never instructs loading the `artifact-design` skill the Artifact contract requires; whether its design pass conflicts with "keep the first version plain" is unknown · the run trips a contract the SKILL.md never mentions · claude-fable-5-1
- BLOCKER · architect-skill-build-plan.md:54 · (B-R2 reinstalls mid-slice fixes via `/plugin update`, but the marketplace is GitHub-sourced) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:39 · (Slice A AC1's install-and-list clause is unrunnable pre-merge) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:3 · (the 2026-08-21 findings doc cited as provenance does not exist) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:32 · (R10 "invokes no other skill" unsourced and collides with R12's Artifact contract) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:24 · (R2 "found beside the project" is undefined vocabulary) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:30 · (R8 "pre-repo" ambiguous: unconditional or conditional) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:40 · (Slice A AC2 is the only check on eleven requirements and leaves no artifact) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:152 · (the 2026-09-01 adjudication block is in a form no station owns) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (assumed ledger lines rendered as decided; `## Build assumptions` empty) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:25 · (R3's classification test unsourced) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:35 · (R13 never says what mandate text accompanies the scope doc) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:44 · (roster line has no criterion; "Nineteen/twenty" count goes stale) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (plugin.json "shaped like /inspect's" propagates the stale repository URL) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:55 · (evidence path follows neither house convention) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:52 · (prose sentence under the `Requirements:` heading) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:28 · (R6 vs R7 category vocabulary mismatch) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:34 · (R12 HTML source has no filename) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:35 · ("substantive disagreement" is judgment) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:57 · (Slice B ACs trust the builder's note; the doc has checkable traces they skip) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:28 · (R6 routes pick + rejected-whys to the run log without a scope ruling) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:30 · (R8 docless slug rule invented) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:26 · (R4 softens scope's "~three answers" guardrail) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:35 · (R13 disagreement taxonomy is elaboration beyond scope :34) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:36 · (R14 report counts/run-number have no scope source) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:34 · (R12 URL-recording + republish-if-missing mechanics unruled) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:58 · (Slice B AC2 states both branches but one run reaches one) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:42 · (AC4 "adversarial read" proves a universal negative with no stopping rule) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (no runnable check and no evidence the rule-6 smell was flagged and accepted) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:57 · (AC numbering restarts per slice while requirements got B-R prefixes) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:15 · (a `Plan: inspected` stamp sits inside the Out of scope parse range) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:35 · (R13's transport guards exceed the cited precon convention) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:43 · (AC5 enforces the invented guard set) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:3 · (Intent embellishes Tony's profile beyond the record) · not fixed — doc unchanged since the prior run

### 2026-09-01 — inspect: plan
- BLOCKER · architect-skill-build-plan.md:53 · B-R2 reaches the running copy via `/plugin update architect@tony-skills` — the marketplace clone is on `main` (24 commits behind origin, HEAD 83923f1) and installs pin a `main` sha · every "re-run of the affected step" tests the stale installed copy; same mechanic sinks Slice A AC1's install half (:38); the plan names no local-dev path such as `claude --plugin-dir plugins/architect` (converged: third lane to confirm) · claude-fable-5-1
- BLOCKER · architect-skill-build-plan.md:25 · R4 softens the record's "~three answers + sorted scope" guardrail (scope :32) to "depth scales with the system's size" · builder writes an unbounded interview for a large system against the recorded limit (verifier's note: PLAUSIBLE at this severity — the scope line is `assumed`; Claude and GPT lanes rated it MINOR/MAJOR) · gemini-3.1-pro-high
- MAJOR · architect-skill-build-plan.md:31 · R10/R15/B AC8 forbid skill invocations while R12/B AC6 publish a Claude Artifact, whose contract in this environment requires loading the `artifact-design` skill first (a session built-in, not on disk) · AC6 and AC8 cannot both pass; the SKILL.md needs a carve-out or AC8 rewording · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:3 · decision provenance and Out of scope items 1–2 (:8, :9) cite `~/Documents/handoffs/2026-08-21-architecture-skill-sunrise-sunset-findings.md`, which does not exist on this machine; scope :62 and blueprint-review-experiment-2026-08-21.md:5 cite the same dead path · the paper trail the plan leans on does not exist · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:23 · R2 "found beside the project" and R8 (:29) `~/Documents/` ignore precon SKILL.md:59 (`<repo>/docs/` by default, `~/Documents/` only when no repo owns the idea; repo-owned scope docs are the live norm — 3 here, 9 more under `~/Developer/*/docs/`) and scope :26's "beside the precon scope doc" · for a repo-owned scope doc the architecture doc lands in the wrong place; the hunt has no defined search path or candidate set · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:34 · R13's read-only sandbox and "neutral empty cwd" exceed precon SKILL.md:80 (the transport scope :36 says to copy); codex `cwd` must exist, so the empty dir is a second mkdir the same sentence forbids · "same as /precon's exit test" and R13 disagree on what the transport is · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:43 · Footprint's "roster line in `README.md` and `CLAUDE.md`": CLAUDE.md:14-18 carries no per-skill roster since the migration (it defers to README and the catalog); what must change is the count sentence at CLAUDE.md:14 and README.md:4-5 ("Nineteen … twenty"), neither listed · builder adds a roster line against CLAUDE.md's stated convention while both counts go stale (Gemini's BLOCKER at :43 — "edit not in the record" — refuted: README/CLAUDE.md registration is repo convention; its residue merges here) · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:39 · Slice A AC2 ("read-through mapping") and AC4 (:41, "adversarial read") rely on reader judgment rather than a measurable end state · /signoff cannot objectively pass or fail the slice · gemini-3.1-pro-high
- MAJOR · architect-skill-build-plan.md:56 · Slice B AC1 ("or the docless discussion runs") and AC7 (:62, "declining counts as a pass") carry or-branches a single run cannot both exercise · the slice is marked verified with branches never proven · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:15 · `Plan: inspected` stamps sit inside the Out of scope block · parsers ingest stamps as deferred items (inspect's own placement rule; carried) · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:23 · R2's list-and-ask fallback for multiple scope docs is imported from the code book, not established by the record · builder implements a disambiguation flow Tony never scoped · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:29 · R8's docless slug rule is invented · an extra mechanical requirement on the gate discussion · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:34 · R13's sandbox and cwd flags are not in the cited precon convention (verifier's correction: `web_search: disabled` IS at precon SKILL.md:80; the other two are jpb's) · builder hardcodes parameters the record never provided · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:35 · R14's counts and run number have no scope source · metric tracking built for an output block never asked for · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:33 · R12's publish-fresh-when-no-URL mechanism is invented · state-recovery logic never specified · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:27 · R6 routes the pick and rejected whys to the run log without a scope ruling · unapproved structure locked in · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:34 · R13's disagreement taxonomy is not in the record · hardcoded agenda may miss other disagreements · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:3 · Intent embellishes Tony's profile beyond the record · faux persona steers tone · gemini-3.1-pro-high
- MINOR · architect-skill-build-plan.md:5 · "that machine runs `/plugin update architect@tony-skills`": `installed_plugins.json` has no such plugin and the marketplace clone is 24 commits behind, so first delivery is `/plugin marketplace update tony-skills` then `/plugin install` · a session following line 5 verbatim on a fresh machine gets nothing · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:5 · `plugin.json` "shaped like /inspect's" bakes in the pre-transfer `tiny-tunnel-dot` URL (all 19 manifests; remote is `line7works`) · stale URL on a public repo · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:54 · evidence note at `docs/evidence/architect-smoke-run.md` breaks the one-folder-per-plan layout (`docs/evidence/<plan>/<slice>-<name>`, skills-migration-build-plan.md:11) · not fatal · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:33 · R12 "self-contained HTML … same URL across re-runs": the Artifact contract publishes a body fragment (no doctype/html/head/body), needs a `favicon` on first publish, and refuses a republish by `url` from another conversation unless the artifact is read first · a re-run that only passes `url` is refused; the SKILL.md must state read-then-publish · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:32 · R11 claims "property line as /precon's" but precon SKILL.md:24/:95 confine lookups to repo + project docs and park unknowns as `needs research` ledger lines; R11 adds Claude's own knowledge and marked lines — scope :55 rules it that way, so the defect is the "as /precon's" wording · builder copies precon's mechanism instead of the ruled one · claude-fable-5-1
- BLOCKER · architect-skill-build-plan.md:53 · (B-R2 reinstalls via `/plugin update`; marketplace is GitHub-sourced from main) · not fixed — doc unchanged since the prior run
- BLOCKER · architect-skill-build-plan.md:24 · (docless runs vs mandatory blind-review offer vs scope-doc-only payload) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:38 · (AC1's install-and-list clause unrunnable pre-merge) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:3 · (the 2026-08-21 findings doc cited as provenance does not exist) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:31 · (R10 "invokes no other skill" unsourced and collides with the Artifact contract) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:5 · (Artifact publish every run is an external send the "only sanctioned send" ruling forbids) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:23 · (R2 "found beside the project" undefined; discovery contract invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:23 · (R2 docless input = current discussion invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:29 · (R8 "pre-repo" ambiguous; docless slug invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:27 · (R6 run-log location invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:25 · (R4 guardrail softened) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:33 · (R12 missing-URL mechanics invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:34 · (R13 sandbox + cwd guards unsourced) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:35 · (R14 fields invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:39 · (Slice A AC2 sole check on eleven requirements, leaves no artifact) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:62 · (AC7 lets Slice B pass without exercising the review) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:57 · (AC2 both branches, one run) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:63 · (AC8 evidence note cannot prove negatives) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:54 · (evidence path undated and off-convention; re-run overwrites run 1) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:151 · (the 2026-09-01 adjudication block is in a form no station owns) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (assumed ledger lines rendered as decided; Build assumptions empty) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:24 · (R3's classification test unsourced) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:34 · (R13 never says what mandate text accompanies the scope doc) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:43 · (roster line has no criterion; "Nineteen/twenty" count goes stale) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (plugin.json "shaped like /inspect's" propagates the stale repository URL) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:51 · (prose sentence under the `Requirements:` heading) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:27 · (R6 vs R7 category vocabulary mismatch) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:33 · (R12 HTML source has no filename) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:34 · ("substantive disagreement" is judgment) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:56 · (Slice B ACs trust the builder's note; doc traces unnamed) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:38 · (AC1 checks skip plugin.json; grep too loose) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:34 · (neutral cwd needs a second mkdir) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:33 · (artifact-design load never instructed) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:24 · (precon's two locations unnamed) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:34 · (R13 disagreement taxonomy is elaboration beyond scope :34) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:41 · (AC4 universal negative with no stopping rule) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (no runnable check; rule-6 smell not recorded as flagged and accepted) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:56 · (AC numbering restarts per slice while requirements got B-R prefixes) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:15 · (a `Plan: inspected` stamp sits inside the Out of scope parse range) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:42 · (AC5 enforces the invented guard set) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:3 · (Intent embellishes Tony's profile beyond the record) · not fixed — doc unchanged since the prior run
