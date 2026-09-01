# Architect skill — build plan (2026-08-21)

Intent: /architect is the missing drawings step in Tony's build pipeline — the station between /precon (which settles an idea's scope in a scope doc) and everything downstream (/sunrise provisions infrastructure, /blueprint slices work, /build executes). Today architecture decisions get made implicitly: /blueprint decides structure silently while slicing, and /sunrise's archetype template provisions databases and hosting at the moment of least information, before scope even exists. /architect fixes that with one interview producing one architecture doc: the least structure that serves a named first user's walkthrough without becoming demolition later. Two passes run as one negotiation — delivery (who is the first real person to touch this, by what date, doing what) and architecture (2–3 genuinely distinct candidate structures grilled against that target, then checked against the full vision for one-way doors). The governing distinction: decisions are made at full-vision quality, construction happens at MVP quantity — deciding is free, provisioning is not, so one-way choices (language, database kind, repo shape, data shapes, platform) are settled up front while their construction waits. Tony is a solo developer new to engineering who grasps concepts fast but cannot yet evaluate architecture proposals; the skill exists so the AI's first plausible proposal never ships unexamined. Full decision provenance: the scope doc at `~/Documents/architect-scope.md` (the spec of record; its Decisions ledger includes two cold reads absorbed), plus the pre-precon findings doc at `~/Documents/handoffs/2026-08-21-architecture-skill-sunrise-sunset-findings.md` (which also records the parked "/blueprint post-draft cold review" idea cited under Out of scope).

Constraints: The skill is one file at `~/.claude/skills/architect/SKILL.md`, authored in house style (intro, steps, rules, output block, "What NOT to do" — match the voice and structure of `~/.claude/skills/precon/SKILL.md` and `~/.claude/skills/blueprint/SKILL.md`). Loop skills live unversioned in `~/.claude/skills/` (no git repo; Time Machine covers backup), which is why this plan lives in `~/Documents/skill-lab/` beside the prior skill build plans (`precon-skill-build-plan.md`, `ship-skill-build-plan.md`) rather than a repo docs/ folder. Hard behavioral constraints, each from the scope doc's Decisions ledger: strictly user-invoked, never auto-triggered; takes the /precon scope doc as its input; never provisions anything (doc only — execution belongs to /sunrise); grilling is Claude-only inside the run; property line as /precon's — the repo, project docs, and Claude's own knowledge only, no web, no research subagents, factual unknowns that need outside checking become marked lines in the architecture doc for Tony to resolve (scope doc ledger line, from the blueprint interview 2026-08-21); the only sanctioned external send is the blind review, on Tony's explicit word in that run. Until the /sunrise and /blueprint reworks land (a separate future build), Tony hand-points those skills at the architecture doc. No runnable test suite applies; verification is manual per criteria below.

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

## Slice A — the SKILL.md
Goal: write the complete /architect skill file implementing every decided mechanism from the scope doc, in house style.
Requirements:
- R1 — User-invoked only. The skill runs when Tony types /architect; its description must state it is strictly user-invoked and must not describe auto-invocation triggers.
- R2 — Input gate: the input is a /precon scope doc (path given in the invocation, or found beside the project — when more than one could match, list and ask, never silently pick). Invoked without one, the skill stops and opens a discussion on why it's being run docless — a conversation gate, not a silent refusal. The run may proceed only when the discussion lands on a reason; that reason is recorded at the top of the architecture doc. Docless runs take the current discussion as their input.
- R3 — Exit ramp: the interview's first question is "is there a system here at all?" A static-page-grade idea (no server, no data to keep, no moving parts) ends the interview immediately after that question and still writes a tiny architecture doc (a few lines: static page, no system, no provisioning beyond a repo) — "no doc" stays reserved for ideas that never saw /architect. Exit-ramp runs still end with the visual and the blind-review offer: the scope's "every run" rulings carry no carve-out.
- R4 — Interview shape: two passes run as one negotiation, in three steps. Step 1 (delivery pass): the walkthrough target — a named real person (never "users"), the target date of the walkthrough session, and what that person must be able to do. The walkthrough is the dated session where the named first user actually touches the built thing. Step 2 (architecture pass): candidate structures grilled against that target. Step 3 (architecture pass): the one-way-door check against the full vision. The interview stays short — depth scales with the system's size; heavy ceremony here delays the MVP the skill exists to accelerate (the scope's narrowness guardrail).
- R5 — The razor is the grilling criterion: every component must point at a walkthrough requirement or it is cut from v0. No server unless something needs a server; no database unless something must be remembered.
- R6 — Candidates: step 2 forces 2–3 genuinely distinct candidate structures into the open — distinct means differing in at least one poured-concrete category (platform, storage, repo shape, language, or data shape), never variations of one shape — with what each assumes and what each makes expensive later. Never a single proposal for Tony to nod at. Tony picks; the pick and the rejected candidates' one-line whys are recorded in the run log (their home — the four-part output stays four parts).
- R7 — One-way doors: step 3 brings the full vision in only to verify nothing in v0 blocks it. The five named categories — language, database kind, repo shape, data shapes, platform — are the checklist floor, not a cap. One-way decisions are made at full-vision quality; everything else stays two-way. Banked decisions are recorded, not provisioned (e.g. "becomes Postgres when scores go remote").
- R8 — Output doc at `~/Documents/<slug>-architecture.md` pre-repo, where `<slug>` is the precon scope doc's slug (a docless run's slug is the project's working name, settled in the gate discussion). Four required parts: (1) walkthrough target; (2) v0 drawing — component list (what exists) + plain-prose data flow (what talks to what) + one simple diagram; (3) poured-concrete list (the one-way decisions — one list, two names); (4) deferred list — banked decisions plus deliberately-not-built items, each with a line confirming its door stays open. A docless run's reason header sits at the top. Relocating the doc into a repo is Tony's (or the future /sunrise rework's), never this skill's.
- R9 — Re-runs: one living architecture doc per project, never a fork. A re-run (idea blossomed, new precon, changed direction) continues the doc: a run-log section records each run's date, trigger, and what changed; superseded decisions are struck through, never deleted — the trail Tony asked for ("we ran it once; now we're running it again because things have changed").
- R10 — Never provisions: the skill creates no repos, databases, hosting, or accounts, installs nothing, and invokes no other skill. Doc and visual only.
- R11 — Property line: lookups are the repo (if any), the project's existing docs, and Claude's own knowledge. No web access, no research subagents. A factual unknown that genuinely needs outside checking becomes a marked line in the architecture doc for Tony to resolve.
- R12 — The visual: every run ends by rendering a self-contained HTML visual of what was decided — the systems chosen and what each does/provides for the project — written beside the architecture doc and published as a private Claude Artifact, the same artifact URL kept across re-runs (URL recorded in the architecture doc; a re-run finding no recorded URL publishes fresh and records it). The visual is a projection re-rendered from the doc; the markdown stays the record. Its design is deliberately unspecified and evolves run by run — keep the first version plain; do not build a design system.
- R13 — Blind review: after the doc and visual are done, the skill asks Tony once whether he wants an outside-model review. On his word only: the external model receives the precon scope doc ONLY — never Claude's architecture, never chat context — via the codex MCP, using the pinned model named in jpb's SKILL.md preflight (`gpt-5.6-sol` at time of writing; the reference wins if the pin moves; a different model on Tony's pick per run substitutes, never adds a second reviewer), with `web_search: disabled`, read-only sandbox, and a neutral empty cwd. It returns its own full architecture take, saved verbatim to `~/Documents/architect-reviews/<slug>-review-<date>.md`. The skill then walks Tony through every substantive disagreement between the two takes — components built vs cut, structure, one-way-door calls, deferrals — and Tony rules each one in discussion; the architecture doc changes only where he rules. Nothing merges silently.
- R14 — Report block in house style, required fields: `ARCHITECT: <project>`, doc path, artifact URL, run number (from the run log), counts (components in v0 / poured-concrete decisions / deferred items), review status (declined | done at <path>), a `Next:` line naming the interim hand-pointing and the doc's downstream contract (Tony points /sunrise at the doc to provision exactly what it lists, and /blueprint at it to slice with the user-touchable slice up front), and a `SKILL NOTE:` line only when a rule was worked around.
- R15 — "What NOT to do" section covering, at minimum: don't auto-invoke; don't proceed docless without the discussion landing on a recorded reason; don't provision anything or invoke any skill; don't leave the property (no web, no research subagents); don't send anything external without Tony's word in that run; don't show the external reviewer Claude's work; don't merge review differences silently; don't skip the candidates and present one proposal; don't fork a second architecture doc; don't delete or rewrite run-log history; don't over-spec the visual; don't publish the visual anywhere public (the arcade included).
Acceptance criteria:
- AC1: `~/.claude/skills/architect/SKILL.md` exists and /architect shows in the session's skill listing — verify: manual: `ls ~/.claude/skills/architect/` and check the skill list.
- AC2: A reviewer can point to the line(s) implementing each of R1–R15 — verify: manual: read-through mapping each requirement to text.
- AC3: The output-doc specification in the file names all four required parts, the slug rule (including the docless case), the docless reason header, and the run log — verify: manual: compare against R8/R9.
- AC4: No instruction anywhere in the file directs provisioning, web access, research subagents, skill invocation, auto-invocation, or an external send without Tony's word — verify: manual: adversarial read for contradictions.
- AC5: The blind-review passage carries all four transport guards (scope-doc-only payload, web_search disabled, read-only sandbox, neutral cwd), pins the model by reference, and states the substitute-not-second-reviewer rule — verify: manual: compare against R13 and against the pinned id in `~/.claude/skills/jpb/SKILL.md`.
Footprint: `~/.claude/skills/architect/SKILL.md` (new file, new directory).
Not in this slice: any live run; any edit to any other skill; any change to the scope doc.
Depends on: nothing
Status: not started

## Slice B — live smoke test
Goal: one real /architect run end to end with Tony on a genuine project; every mechanism the run's path reaches observably fires; fixes fold back into the SKILL.md.
Requirements (numbered B-R to keep Slice A's R-numbers unambiguous):
- B-R1 — The test subject is a real precon scope doc Tony picks (if none suits, he runs /precon on a real idea first — the trash-can game example from the design discussion is a natural candidate). Not a synthetic toy.
- B-R2 — Defects found during the run are fixed in `~/.claude/skills/architect/SKILL.md` within this slice; material behavior changes get one more run-through of the affected step.
Acceptance criteria:
- AC1: The input gate fires correctly for the chosen path (scope doc accepted, or the docless discussion runs and its reason lands at the top of the doc) — verify: manual: transcript.
- AC2: The exit-ramp question is asked first and visibly steers the run: a "no system" answer skips the candidate round and produces the tiny doc; a real system gets all three steps — verify: manual: transcript.
- AC3: Step order holds: walkthrough target before candidates, candidates before the one-way-door check — verify: manual: transcript.
- AC4: 2–3 candidates presented, each differing in at least one poured-concrete category per Slice A R6, with assumptions and later-expense stated, before Tony picks — verify: manual: transcript.
- AC5: Architecture doc written at `~/Documents/<slug>-architecture.md` with all four parts (or the tiny exit-ramp form) and the run log, matching Slice A R8/R9 — verify: manual: open the file.
- AC6: The visual renders and publishes as an Artifact (private by default — not posted to the arcade or any public host), with its URL recorded in the doc and reported — verify: manual: open the artifact URL, confirm the doc records it.
- AC7: The blind review is offered exactly once at the end; nothing external sends without Tony's word (declining counts as a pass); if run, the review file exists at the R13 path and disagreements were walked with Tony ruling each — verify: manual: transcript + file.
- AC8: Zero provisioning, zero skill invocations, zero web/research actions in the run — verify: manual: transcript.
- AC9: Report block printed with all of Slice A R14's fields — verify: manual: transcript.
Footprint: `~/.claude/skills/architect/SKILL.md` (fixes); one architecture doc; one artifact; possibly one review file.
Not in this slice: acting on the tested idea itself; building anything the architecture doc describes; re-run mechanics beyond what one sitting exercises (the run log must still be written for run 1).
Depends on: Slice A
Status: not started

## Build assumptions

## Deviations

## Discovered

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
