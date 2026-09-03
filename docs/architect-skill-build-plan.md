# Architect skill — build plan (2026-08-21)

Intent: /architect is the missing drawings step in Tony's build pipeline — the station between /precon (which settles an idea's scope in a scope doc) and everything downstream (/sunrise provisions infrastructure, /blueprint slices work, /build executes). Today architecture decisions get made implicitly: /blueprint decides structure silently while slicing, and /sunrise's archetype template provisions databases and hosting at the moment of least information. /architect fixes that with one interview producing one architecture doc: the least structure that serves a named first user's walkthrough without becoming demolition later. Two passes run as one negotiation — delivery (who is the first real person to touch this, by what date, doing what) and architecture (2–3 genuinely distinct candidate structures grilled against that target, then checked against the full vision for one-way doors). The governing distinction: decisions are made at full-vision quality, construction happens at MVP quantity — deciding is free, provisioning is not, so one-way choices (language, database kind, repo shape, data shapes, platform) are settled up front while their construction waits. Tony is a solo developer new to engineering whose architecture decisions currently get made implicitly; the skill exists so the AI's first plausible proposal never ships unexamined. Decision provenance: the scope doc at `~/Documents/architect-scope.md` (the spec of record; every `assumed` line there is Tony's to veto) and the cold reads at `~/Documents/precon-cold-reads/architect-cold-read-2026-08-21.md`. The pre-precon findings doc earlier versions cited does not exist on disk (verified 2026-09-01); the parked "/blueprint post-draft cold review" idea's only surviving record is `docs/blueprint-review-experiment-2026-08-21.md`.

Constraints: The skill is one file at `plugins/architect/skills/architect/SKILL.md` in this repo (scope doc ruling 2026-09-01), with a `plugins/architect/.claude-plugin/plugin.json` (same keys as `plugins/inspect/.claude-plugin/plugin.json`, but `homepage`/`repository` pointing at `https://github.com/line7works/tony-skills` — the current remote, not the pre-transfer URL the older manifests carry) and a `.claude-plugin/marketplace.json` entry with the same four keys as the `inspect` entry (name, source, description, tags), authored in house style (intro, steps, rules, output block, "What NOT to do" — match the voice and structure of `plugins/precon/skills/precon/SKILL.md` and `plugins/blueprint/skills/blueprint/SKILL.md`). Skills are versioned in this repo since the skills migration (this plan moved from `~/Documents/skill-lab/` to `docs/` on 2026-08-31, inside /build's hunt path). A session normally runs the marketplace-installed copy: a machine picks up a change only after it lands on `main` and that machine runs `/plugin marketplace update tony-skills` then `/plugin install architect@tony-skills` (first time) or `/plugin update architect@tony-skills`. Inside this build, the branch copy is exercised without a merge via `claude --plugin-dir plugins/architect` (the flag exists in `claude --help`: "Load a plugin from a directory or .zip"; that it surfaces /architect and that a fresh session picks up a branch edit is assumption A1 below, verified at Slice A start). Hard behavioral constraints, each from the scope doc's Decisions ledger (decided unless marked assumed there): strictly user-invoked, never auto-triggered (assumed); takes the /precon scope doc as its input; never provisions anything (doc only — execution belongs to /sunrise); grilling is Claude-only inside the run; property line as the scope doc rules it (ledger line "Property line during a run") — the repo, project docs, and Claude's own knowledge only, no web, no research subagents, factual unknowns that need outside checking become marked lines in the architecture doc for Tony to resolve; the only sanctioned send to another model is the blind review, on Tony's explicit word in that run (publishing the private Artifact is the decided visual delivery, not a send to another model — scope ledger, assumed). Until the /sunrise and /blueprint reworks land (a separate future build), Tony hand-points those skills at the architecture doc (assumed). No runnable test suite applies to a prose skill file; verification is manual per the criteria below — the code book's rule-6 smell, flagged here; not ruled on by Tony (his 2026-09-01 word was "fix the blockers/majors", an order to amend, not an acceptance) — it stands as a recorded smell, open for his call.

Out of scope:
- /sunrise + /sunset rework — reason: Tony's ruling (precon Round 1 Q4, scope doc Out of scope line 1): follow-on build after /architect ships, informed by what it teaches. The findings doc that line once cited does not exist on disk; the ruling stands on the scope doc alone.
- Hierarchical /blueprint (vertical slices → sub-blueprints) — reason: Tony parked it for after /architect lands (scope doc Out of scope line 2).
- A standing /blueprint post-draft cold review — reason: parked for a later blueprint talk; record: `docs/blueprint-review-experiment-2026-08-21.md` (its first live test and verdict).
- Standalone Occam's razor skill — reason: absorbed; the razor is /architect's grilling criterion, not its own skill (Tony, 2026-08-21).
- Named tiers/versions of /sunrise — reason: Tony ruled the architecture doc is the tier; no editions.
- A designed visual system for the end-of-run artifact — reason: Tony's ruling ("we'll establish what it looks like over time"): the visual's look evolves run by run; this build must not over-spec it.
- Editing /precon, /blueprint, /sunrise, or any other skill — reason: /architect is a new file; the interim hand-pointing rule covers integration.
- Multi-model review panel — reason: the scope settles on one blind reviewer per run (pinned GPT, or a substitute on Tony's pick — never a second reviewer added; assumed in the scope ledger).
Plan: inspected 2026-08-30 by claude-fable-5 · 0 BLOCKER · 2 MAJOR · 17 MINOR
Plan: inspected 2026-08-30 by claude-fable-5 · 0 BLOCKER · 4 MAJOR · 4 MINOR · 1 QUESTION
Plan: inspected 2026-08-30 by gpt-5.6-sol · 0 BLOCKER · 2 MAJOR · 0 MINOR
Plan: inspected 2026-09-01 by claude-fable-5-1 · 1 BLOCKER · 7 MAJOR · 11 MINOR
Plan: inspected 2026-09-01 by gpt-5.6-sol · 2 BLOCKER · 15 MAJOR · 8 MINOR
Plan: inspected 2026-09-01 by gemini-3.1-pro-high · 2 BLOCKER · 7 MAJOR · 14 MINOR
Plan: inspected 2026-09-01 by deepseek/deepseek-v4-pro · 1 BLOCKER · 13 MAJOR · 11 MINOR · 1 QUESTION
Plan: inspected 2026-09-02 by claude-fable-5-1 · 0 BLOCKER · 7 MAJOR · 24 MINOR · 3 QUESTION

## Slice A — the SKILL.md
Goal: write the complete /architect skill file implementing every decided mechanism from the scope doc, in house style, registered as a plugin and loadable from the branch.
Requirements:
- R1 — User-invoked only. The skill runs when Tony types /architect; its description must state it is strictly user-invoked and must not describe auto-invocation triggers.
- R2 — Input gate: the input is a /precon scope doc — the path given in the invocation, else hunted by glob over precon's two homes (`<repo>/docs/*-scope.md` when invoked inside a repo, plus `~/Documents/*-scope.md`), matched by title; more than one match is listed and asked, never silently picked (scope ledger, assumed). Invoked without one, the skill stops and opens a discussion on why it's being run docless — a conversation gate, not a silent refusal. The run may proceed only when the discussion lands on a reason; that reason is recorded at the top of the architecture doc. Docless runs take the current discussion as their input (scope ledger, assumed).
- R3 — Exit ramp: the interview's first question is "is there a system here at all?" A single-static-page idea ends the interview immediately after that question and still writes a tiny architecture doc (a few lines: static page, no system, no provisioning beyond a repo) — "no doc" stays reserved for ideas that never saw /architect. Exit-ramp runs still end with the visual and, when a scope doc exists, the blind-review offer.
- R4 — Interview shape: two passes run as one negotiation, in three steps. Step 1 (delivery pass): the walkthrough target — a named real person (never "users"), the target date of the walkthrough session, and what that person must be able to do. The walkthrough is the dated session where the named first user actually touches the built thing. Step 2 (architecture pass): candidate structures grilled against that target. Step 3 (architecture pass): the one-way-door check against the full vision. The interview stays short — about three answers plus the sorted scope; if it grows into heavy ceremony it delays the MVP the skill exists to accelerate (the scope's narrowness guardrail, verbatim).
- R5 — The razor is the grilling criterion: every component must point at a walkthrough requirement or it is cut from v0. No server unless something needs a server; no database unless something must be remembered.
- R6 — Candidates: step 2 forces 2–3 genuinely distinct candidate structures into the open — distinct means differing in at least one one-way-door category (platform, storage, repo shape, language, data shape, or any other one-way-door category per R7's floor-not-cap rule), never variations of one shape (scope doc Decisions ledger, ruled 2026-09-01) — with what each assumes and what each makes expensive later. Never a single proposal for Tony to nod at. Tony picks; the pick and the rejected candidates' one-line whys are recorded in the run log (scope ledger, assumed; the four-part output stays four parts).
- R7 — One-way doors: step 3 brings the full vision in only to verify nothing in v0 blocks it. The five named categories — language, database kind (storage), repo shape, data shapes, platform — are the checklist floor, not a cap. One-way decisions are made at full-vision quality; everything else stays two-way. Banked decisions are recorded, not provisioned (e.g. "becomes Postgres when scores go remote").
- R8 — Output doc beside the precon scope doc: `<repo>/docs/<slug>-architecture.md` when the scope doc is repo-owned, `~/Documents/<slug>-architecture.md` otherwise (scope ledger, decided 2026-09-02), where `<slug>` is the precon scope doc's slug (a docless run's slug is the project's working name, settled in the gate discussion — scope ledger, assumed 2026-09-01; a docless run's doc goes to `~/Documents/` unless the discussion names a repo — this plan's assumption A2). The doc's header names the scope doc it was built from (path), or the docless reason. Four required parts: (1) walkthrough target; (2) v0 drawing — component list (what exists) + plain-prose data flow (what talks to what) + one simple diagram; (3) poured-concrete list (the one-way decisions — one list, two names); (4) deferred list — banked decisions plus deliberately-not-built items, each with a line confirming its door stays open. A docless run's reason header sits at the top. Moving the doc between homes is Tony's (or the future /sunrise rework's), never this skill's.
- R9 — Re-runs: one living architecture doc per project, never a fork. A re-run (idea blossomed, new precon, changed direction) continues the doc: a run-log section records each run's date, trigger, what changed, and the three interview steps in the order taken (the chosen candidate and each rejected candidate's one-line why live here too, per R6); superseded decisions are struck through, never deleted — the trail Tony asked for ("we ran it once; now we're running it again because things have changed").
- R10 — Never provisions: the skill creates no repos, databases, hosting, or accounts, installs nothing, and invokes no other loop skill. Harness-mandated preflights (the Artifact tool's `artifact-design` load) are not skill invocations in this sense (scope ledger, assumed). Doc and visual only.
- R11 — Property line: lookups are the repo (if any), the project's existing docs, and Claude's own knowledge. No web access, no research subagents. A factual unknown that genuinely needs outside checking becomes a marked line in the architecture doc for Tony to resolve.
- R12 — The visual: every run ends by rendering an HTML visual of what was decided — the systems chosen and what each does/provides for the project — written beside the architecture doc as `<slug>-architecture.html` (a page body per the Artifact tool's contract: no doctype/html/head/body wrapper, a `<title>`, a favicon on first publish) and published as a private Claude Artifact, the same artifact URL kept across re-runs: the URL is recorded in the architecture doc; a re-run reads that artifact before republishing to it; a re-run finding no recorded URL publishes fresh and records the new URL (scope ledger, assumed). The visual is a projection re-rendered from the doc; the markdown stays the record. Its design is deliberately unspecified and evolves run by run — keep the first version plain; do not build a design system.
- R13 — Blind review: after the doc and visual are done, and only when the run had a precon scope doc, the skill asks Tony once whether he wants an outside-model review (a docless run has no brief to send: no offer, and the report says so — scope ledger, decided 2026-09-02). On his word only: the external model receives the precon scope doc ONLY — never Claude's architecture, never chat context — with this fixed instruction, verbatim in SKILL.md: "You are the architect. Read the attached precon scope doc and return your own full architecture-and-delivery take for it: the walkthrough target, a v0 drawing (component list, plain-prose data flow, one simple diagram), the poured-concrete list of one-way decisions, and the deferred list. You have no other input; do not ask for any.", via the codex MCP, using the pinned model named in jpb's SKILL.md preflight (`gpt-5.6-sol` at time of writing; the reference wins if the pin moves; a different model on Tony's pick per run substitutes, never adds a second reviewer), with jpb Judge G's transport guards (jpb SKILL.md, Judge G config): `config: {"web_search": "disabled"}`, `sandbox: "read-only"`, and an absolute empty cwd created fresh for the run (scope ledger, assumed). The take is saved verbatim to `~/Documents/architect-reviews/<slug>-review-<date>.md`. Two sanctioned directory creations: `~/Documents/architect-reviews/` on the first blind review, and the run's empty cwd. The skill then walks Tony through every disagreement between the two takes (at minimum: components built vs cut, structure, one-way-door calls, deferrals) and Tony rules each one in discussion; the architecture doc changes only where he rules. Nothing merges silently.
- R14 — Report block in house style (precon's `PRECON:` shape), fields: `ARCHITECT: <project>`, doc path, artifact URL, run number (from the run log), counts (components in v0 / poured-concrete decisions / deferred items), review status (declined | not offered — docless | done at <path>), a `Next:` line naming the interim hand-pointing and the doc's downstream contract (Tony points /sunrise at the doc to provision exactly what it lists, and /blueprint at it to slice with the user-touchable slice up front), and a `SKILL NOTE:` line only when a rule was worked around (fields beyond the scope doc are house-style extrapolation — scope ledger, assumed).
- R15 — "What NOT to do" section covering, at minimum: don't auto-invoke; don't proceed docless without the discussion landing on a recorded reason; don't provision anything or invoke any loop skill; don't leave the property (no web, no research subagents); don't send anything to another model without Tony's word in that run; don't show the external reviewer Claude's work; don't merge review differences silently; don't skip the candidates and present one proposal; don't fork a second architecture doc; don't delete or rewrite run-log history; don't over-spec the visual; don't publish the visual anywhere public (the arcade included).
- R16 — Registration: `plugins/architect/.claude-plugin/plugin.json` and the `architect` entry in `.claude-plugin/marketplace.json` per Constraints; README.md gains one roster line for `architect` in its plugin list and its count sentence moves from "Nineteen plugins covering twenty skills" to twenty / twenty-one; CLAUDE.md's count sentence ("Nineteen plugin folders covering twenty skills") moves the same way (CLAUDE.md's six-skill list at its lines 14-25 is the pre-migration holdover; do not add architect to it). README's roster is three groups; architect goes in "The build loop" between `precon`/`jpb` and `blueprint`. README.md also carries a numeral count in its Layout block ("the catalog — 19 entries", README.md:92) that moves to 20.
Acceptance criteria:
- AC1: `plugins/architect/skills/architect/SKILL.md` and `plugins/architect/.claude-plugin/plugin.json` exist; the manifest parses as JSON with the same keys as inspect's and `repository` = `https://github.com/line7works/tony-skills`; `.claude-plugin/marketplace.json` parses and contains an entry whose `name` is exactly `architect` with `source` `./plugins/architect` — verify: manual: `ls plugins/architect/skills/architect/ plugins/architect/.claude-plugin/`, `python3 -c "import json;print([e for e in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if e['name']=='architect'])"`.
- AC2: a session started with `claude --plugin-dir plugins/architect` lists /architect in its skill listing — verify: manual: start that session from the repo root and check the listing (no merge or install required).
- AC3: a requirement map at `docs/evidence/architect/slice-a-requirement-map.md` lists R1–R15 with, for each, the SKILL.md line number(s) implementing it; every entry cites at least one line, and each cited line contains the mechanism the map claims for it — verify: manual: open the map and check every cited line against the SKILL.md.
- AC4: The output-doc specification in the file names all four required parts, the home rule (repo-owned vs not, and the docless case), the docless reason header, the HTML filename, and the run log — verify: manual: compare against R8/R9/R12.
- AC5: No instruction in the file directs provisioning, web access, research subagents, loop-skill invocation, auto-invocation, or a send to another model without Tony's word — verify: manual, bounded: (a) `grep -nE` the file for `provision|install|create .*repo|web|WebSearch|WebFetch|research|subagent|Agent tool|auto-invoke|trigger|codex|send` and confirm every hit sits inside a prohibition or the R13 blind-review passage; (b) one full read of the file. Pass = both steps done and no hit outside those contexts.
- AC6: The blind-review passage carries the four transport guards (scope-doc-only payload, `web_search: disabled`, read-only sandbox, absolute empty cwd), the docless no-offer rule, the fixed reviewer instruction, pins the model by reference, and states the substitute-not-second-reviewer rule — verify: manual: compare against R13 and against the pinned id and Judge G config in `plugins/jpb/skills/jpb/SKILL.md`.
- AC7: README.md carries the `architect` roster line and its count sentence reads twenty plugins / twenty-one skills; CLAUDE.md's count sentence reads twenty plugin folders / twenty-one skills; `ls plugins | wc -l` = 20 — verify: manual: `grep -nE "architect|wenty|[0-9]+ entries" README.md CLAUDE.md; ls plugins | wc -l` — no line may still say nineteen or 19.
Footprint: `plugins/architect/skills/architect/SKILL.md` and `plugins/architect/.claude-plugin/plugin.json` (new files, new directory); one new entry in `.claude-plugin/marketplace.json`; one roster line + count sentence in `README.md`; count sentence in `CLAUDE.md`; `docs/evidence/architect/slice-a-requirement-map.md` (new).
Not in this slice: any live run; any edit to any other skill; any change to the scope doc; merging or installing the plugin from the marketplace.
Depends on: nothing
Status: signed off

## Slice B — live smoke test
Goal: one real /architect run end to end with Tony on a genuine project, from the branch copy; every mechanism the run's path reaches observably fires; fixes fold back into the SKILL.md.
Requirements:
- B-R1 — The test subject is a real precon scope doc Tony picks at the start of the slice. Not a synthetic toy. If no scope doc suits, the slice stops and reports; any /precon run to produce one happens outside this slice on Tony's word. The run is a scope-doc run (not docless), so the gate's accept path, the blind-review offer, and R8's home rule for that doc's location are the branches this slice exercises; the untaken branches (docless gate, docless no-offer, the other home) are recorded as not exercised in the evidence note, not graded.
- B-R2 — The run happens in a session started with `claude --plugin-dir plugins/architect` from the repo root on the feature branch, so the branch copy is what runs. Defects found are fixed in `plugins/architect/skills/architect/SKILL.md` on the branch, and `docs/evidence/architect/slice-a-requirement-map.md` is re-generated after the last fix (its entries are SKILL.md line numbers; a stale map is a B-AC failure); a material behavior change gets one more run-through of the affected step in a fresh `--plugin-dir` session. No marketplace install, no merge, inside this slice.
- B-R3 — The run ends with an evidence note at `docs/evidence/architect/smoke-run-<YYYY-MM-DD>.md` in this repo recording, per acceptance criterion, what was observed (quoted lines from the run where a criterion turns on wording), the list of tools the session called (from its own tool-call record), and which branches were not exercised. The note is the builder's record; where an AC below can be checked against a file, the file is the evidence and the note is the pointer.
- B-R4 — Numbering: Slice B's criteria are B-AC1…; cross-references say "Slice A AC<n>" or "B-AC<n>".
Acceptance criteria:
- B-AC1: The input gate accepts the chosen scope doc (found by path or by the R2 glob) and the architecture doc's header names it — verify: manual: open the architecture doc; evidence note for the gate exchange.
- B-AC2: The exit-ramp question is asked first, and the run takes the branch the answer implies (a real system: all three steps; the untaken branch is recorded as not exercised) — verify: manual: evidence note (quoted question and answer) + the architecture doc's run log.
- B-AC3: Step order holds: walkthrough target before candidates, candidates before the one-way-door check — verify: manual: the architecture doc's run log records the three steps in that order; evidence note quotes the transitions.
- B-AC4: 2–3 candidates presented, each differing in at least one one-way-door category per Slice A R6, with assumptions and later-expense stated, before Tony picks; the pick and rejected whys are in the run log — verify: manual: open the run log; evidence note quotes the candidate block.
- B-AC5: Architecture doc written at the R8 home for that scope doc (repo-owned → `<repo>/docs/`, else `~/Documents/`) with all four parts (or the tiny exit-ramp form) and the run log — verify: manual: open the file at the location R8 gives for the chosen scope doc.
- B-AC6: `<slug>-architecture.html` exists beside the doc; the visual publishes as a private Artifact (not the arcade or any public host); the URL is recorded in the doc and reported — verify: manual: open the artifact URL; confirm the doc records it and the HTML file exists.
- B-AC7: The blind review is offered exactly once at the end; nothing goes to another model without Tony's word. If Tony gives the word: the review file exists at the R13 path, the reviews directory and the run cwd were the only directories created, and the disagreements were walked with Tony ruling each (the doc changes only where he ruled). If he declines: pass, and the evidence note records "review path not exercised" (a stated limit of this slice — scope ledger, decided 2026-09-02: the plan cannot force Tony's word) — verify: manual: evidence note + files.
- B-AC8: Zero provisioning, zero loop-skill invocations, zero web/research actions — verify: manual: the evidence note's tool-call list (self-reported) shows none; Slice A AC5 covers the file's own text. Stated limit: this is the session's own record, not an independent trace.
- B-AC9: Report block printed with all of Slice A R14's fields — verify: manual: evidence note quotes the block.
Footprint: `plugins/architect/skills/architect/SKILL.md` (fixes); `docs/evidence/architect/slice-a-requirement-map.md` (refreshed); one architecture doc + its HTML; one artifact; possibly one review file (and `~/Documents/architect-reviews/` and one scratch cwd if created); `docs/evidence/architect/smoke-run-<date>.md`.
Not in this slice: acting on the tested idea itself; building anything the architecture doc describes; re-run mechanics beyond what one sitting exercises (the run log must still be written for run 1); marketplace install or merge.
Depends on: Slice A
Status: signed off

## Build assumptions
### 2026-09-02 — build: Slice B
- The live run happened in a separate terminal session ("test") started with `claude --plugin-dir plugins/architect`, since this session was not started that way; its ARCHITECT block, tool list, and quoted exchanges were supplied by that session on request after the run, verbatim, and are the evidence note's source alongside the files · builder call
- The subject (Pour Guys bar-builder) was already built through Slice H1, so run 1 was as-built drawings rather than a pre-construction drawing; still a scope-doc run on the repo-owned home, which is what B-R1 asks for · per user ("find me one, from a repo")
- Outputs were committed in Pour-Guys (slice-f1, 6a61a54) on Tony's word to that session; the commit is outside this repo's footprint and is recorded, not graded · per user
### 2026-09-02 — build: Slice A
- A1 verified · `claude --plugin-dir plugins/architect -p` from the repo root listed `architect:architect` with the branch file's description (AC2) · builder call
- R13 slot mapping: the fixed reviewer instruction goes in `base-instructions`, the scope doc text in `prompt` — the plan names both payloads but not their codex slots; mirrors Judge G's mandate/brief split · builder call
- R11 marker wording: an outside-checking unknown is written as a `NEEDS CHECK: <what>` line — the plan says "marked line" without a form · builder call
- R6 candidate count: the interview asks for candidates from Claude, not Tony; SKILL.md :43 has Claude put them on the table — the plan's "forces into the open" read that way · builder call
- A1 · `claude --plugin-dir plugins/architect` surfaces /architect in that session's skill listing and a fresh session started the same way runs the current branch copy of SKILL.md · verified at Slice A start (AC2); if false, Slice B's B-R2 loop needs a different local-load path and this plan stops for Tony's ruling · 2026-09-02
- A2 · a docless run's architecture doc goes to `~/Documents/` unless the gate discussion names a repo · the scope doc rules only the with-scope-doc case · 2026-09-02

## Deviations
### 2026-09-02 — build: Slice B
- B-R2 re-run-through done only for the exit-ramp/silence change (headless `--plugin-dir` session, first question only, recorded in the evidence note); the template lines (:60, :82), the report-timing rule (:129), the codex backgrounding/unescape guard (:108), and the cwd-home note (:107) were not re-run because they are observable only on a full run with a blind review — their first exercise is the next real /architect run · builder call
### 2026-09-02 — build: Slice A
- none

## Discovered
### 2026-09-02 — build: Slice B
- A first run on an already-built target has no guidance in the skill ("as-built drawings"); the session improvised a timing note and a SKILL NOTE · logged, not built
- The session verified each reviewer claim against the repo before presenting disagreements, so Tony ruled only real differences; the scope doc says every disagreement is presented · logged, not built — Tony's call whether to write it in
- The codex call exceeded the harness's 120 s foreground limit and was backgrounded; the task notification HTML-escapes the response · both now covered in SKILL.md's guard text
### 2026-09-02 — build: Slice A
- The 19 older `plugin.json` manifests still carry the pre-transfer `tiny-tunnel-dot` URL; only architect's points at `line7works` (Constraints acknowledge this; not in this slice's footprint) · logged, not built
- `timeout` is not on this Mac's PATH (zsh: command not found); AC2 ran without it · logged

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

### 2026-09-01 — inspect: plan
- BLOCKER · architect-skill-build-plan.md:34 · R13's transport guards are not established by the record — scope :36 says only "same as /precon's exit test — GPT via the codex MCP" · builder implements guard mechanics the scope never attached; AC5 grades against them (verifier's correction: `web_search: disabled` IS at precon SKILL.md:80, so only read-only sandbox and neutral cwd are unsourced; PLAUSIBLE at this severity — the guards are stricter than the record, not looser, and the other three lanes rated it MINOR/MAJOR) · deepseek/deepseek-v4-pro
- MAJOR · architect-skill-build-plan.md:57 · Slice B AC2 requires both exit-ramp branches verified but one run reaches one · /signoff cannot check the untaken branch and fails an impossible criterion · deepseek/deepseek-v4-pro
- MAJOR · architect-skill-build-plan.md:41 · AC4 proves a universal negative with no bounded check · two graders reading the same file return different verdicts; signoff becomes reader stamina · deepseek/deepseek-v4-pro
- MAJOR · architect-skill-build-plan.md:39 · AC2 "point to the line(s) implementing each R" needs judgment at boundaries (partial, distributed, implied-by-structure) · grading becomes taste; signoff stalls · deepseek/deepseek-v4-pro
- MAJOR · architect-skill-build-plan.md:27 · R6's enumerated five categories read as a closed list while R7 (:28) and scope :39 say floor-not-cap; B AC4 grades "per R6" (inspector cited :25; real site :27) · a candidate differing in a sixth one-way category is failed by AC4 against the record's intent · deepseek/deepseek-v4-pro
- MAJOR · architect-skill-build-plan.md:5 · "No runnable test suite applies" with no record that the rule-6 smell was flagged and accepted · builder and owner argue whether manual-only was an accepted exception or an oversight · deepseek/deepseek-v4-pro
- MAJOR · architect-skill-build-plan.md:35 · R14's counts and run number are elaboration; the record (scope :21) enumerates output parts, not report fields · builder omits a count the skill never defined, or includes one no two inspectors agree on · deepseek/deepseek-v4-pro
- MAJOR · architect-skill-build-plan.md:33 · R12's republish-if-missing procedure is not in the record (scope :52 says only same URL kept) · a re-run with the URL line lost publishes fresh and /signoff disputes the new URL (inspector confidence: low) · deepseek/deepseek-v4-pro
- MAJOR · architect-skill-build-plan.md:42 · AC5 enforces the guard set from :34 · a passage written per the record without sandbox/cwd language fails AC5 (coupled to the :34 finding; same correction applies) · deepseek/deepseek-v4-pro
- MAJOR · architect-skill-build-plan.md:5 · "that machine runs `/plugin update architect@tony-skills`" — `installed_plugins.json` has no `architect`, installs key to the marketplace clone's commit (83923f1, PR #27) while `origin/main` is at fb594ef (PR #32) · AC1's install (:38) fails "plugin not found" until `/plugin marketplace update tony-skills` runs, and B-R2's re-install (:53) silently reuses the stale cache · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:3 · the findings doc cited at :3, :8, :9 does not exist on this machine; only other citation is blueprint-review-experiment-2026-08-21.md:5, itself a pointer · the "why" behind three Out of scope lines is unrecoverable · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:33 · R12 publishes an Artifact while R10/AC4/B AC8 (:31, :41, :63) demand zero skill invocations; the Artifact contract mandates loading the `artifact-design` built-in first · a literal build of R10 breaches the tool contract or fails AC8; carve out harness-mandated built-ins · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:29 · R8's `~/Documents/` home vs scope :26's "beside the precon scope doc": precon puts repo-owned scope docs in `<repo>/docs/` and 12 of 19 scope docs on disk are repo-owned, so B-R1's real subject is most likely repo-owned · R8 gives no rule for that case, R2 (:23) names neither precon home, and B AC5 (:60) grades `~/Documents/` regardless · claude-fable-5-1
- MAJOR · architect-skill-build-plan.md:43 · Footprint's "roster line in `README.md` and `CLAUDE.md`": CLAUDE.md:14-18 has no roster slot (defers to README and the catalog); the "Nineteen … twenty" counts in both files are what go stale · builder adds a line with no home and leaves both counts wrong · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:34 · R13's disagreement taxonomy is not in the record (scope :34) · a platform disagreement fits no named bucket and is skipped · deepseek/deepseek-v4-pro
- MINOR · architect-skill-build-plan.md:3 · Intent adds "cannot yet evaluate architecture proposals" beyond scope :7 · builder infers capability boundaries the record never set · deepseek/deepseek-v4-pro
- MINOR · architect-skill-build-plan.md:15 · three `Plan: inspected` stamps sit inside the Out of scope parse range · a descope harvest ingests stamps as deferred items (inspect's own placement rule; carried) · deepseek/deepseek-v4-pro
- MINOR · architect-skill-build-plan.md:51 · a prose sentence follows the exact `Requirements:` heading before the first bullet · a strict parser rejects the block or reads the sentence as a requirement · deepseek/deepseek-v4-pro
- MINOR · architect-skill-build-plan.md:38 · AC numbering restarts per slice (AC1–AC5, AC1–AC9) · /recheck's flat checklist carries two "AC1"s · deepseek/deepseek-v4-pro
- MINOR · architect-skill-build-plan.md:5 · `plugin.json` "shaped like /inspect's" ships the pre-transfer `tiny-tunnel-dot` URL (all 19 manifests) into a public repo's 20th manifest · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:34 · the four-guard set is jpb Judge G's (jpb SKILL.md:191-194), not precon's (:80, `web_search` only); the plan cites neither · a builder matching precon's voice copies two guards and fails AC5; point at jpb:191-194 · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:34 · "neutral empty cwd" is a second mkdir the same sentence forbids, and a relative `cwd` resolves against the codex server process's cwd (the ChatGPT app bundle) — must be absolute · a literal builder refuses the mkdir or lands the sandbox under the app bundle · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:33 · a republish by `url` from a new conversation is refused unless the artifact is read first; R12 never states read-before-republish · a re-run that jumps to publish is rejected · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:54 · `docs/evidence/architect-smoke-run.md` matches neither the per-plan subfolder convention (skills-migration-build-plan.md:11) nor the dated flat smoke notes in `docs/` · /signoff hunting by convention may miss it · claude-fable-5-1
- MINOR · architect-skill-build-plan.md:5 · "moved … in the 2026-09-01 skills migration" — `~/Documents/skill-lab/README-MOVED.md` says moved 2026-08-31 · date off by a day · claude-fable-5-1
- QUESTION · architect-skill-build-plan.md:29 · where does the architecture doc live when the precon scope doc is repo-owned (scope :26 says both `~/Documents/` and "beside the precon scope doc")? — needs Tony's ruling (inspector's premise that architect's own scope doc is repo-owned is wrong; the question stands for Slice B's subject) · deepseek/deepseek-v4-pro
- BLOCKER · architect-skill-build-plan.md:53 · (B-R2 reinstalls via `/plugin update`; marketplace is GitHub-sourced from main) · not fixed — doc unchanged since the prior run
- BLOCKER · architect-skill-build-plan.md:24 · (docless runs vs mandatory blind-review offer vs scope-doc-only payload) · not fixed — doc unchanged since the prior run
- BLOCKER · architect-skill-build-plan.md:25 · (R4 guardrail softened (Gemini-rated BLOCKER)) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:38 · (AC1's install-and-list clause unrunnable pre-merge) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:3 · (the 2026-08-21 findings doc cited as provenance does not exist) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:31 · (R10 "invokes no other skill" unsourced and collides with the Artifact contract) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:5 · (Artifact publish every run is an external send the "only sanctioned send" ruling forbids) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:23 · (R2 "found beside the project" undefined; discovery contract invented; precon homes unnamed) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:23 · (R2 docless input = current discussion invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:29 · (R8 "pre-repo" ambiguous; docless slug invented; repo-owned case unruled) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:27 · (R6 run-log location invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:33 · (R12 missing-URL mechanics invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:34 · (R13 sandbox + cwd guards unsourced; second mkdir) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:35 · (R14 fields invented) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:39 · (Slice A AC2 sole check on eleven requirements; judgment call) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:41 · (AC4 universal negative (MAJOR-rated by Gemini)) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:62 · (AC7 lets Slice B pass without exercising the review) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:57 · (AC2 both branches, one run) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:63 · (AC8 evidence note cannot prove negatives) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:54 · (evidence path undated and off-convention; re-run overwrites run 1) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:43 · (Footprint roster line has no CLAUDE.md slot; counts go stale) · not fixed — doc unchanged since the prior run
- MAJOR · architect-skill-build-plan.md:151 · (the 2026-09-01 adjudication block is in a form no station owns) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (assumed ledger lines rendered as decided; Build assumptions empty) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:24 · (R3's classification test unsourced) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:34 · (R13 never says what mandate text accompanies the scope doc) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (plugin.json "shaped like /inspect's" propagates the stale repository URL) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (marketplace clone stale; plugin never installed; line 5 update command does nothing on a fresh machine) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:51 · (prose sentence under the `Requirements:` heading) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:27 · (R6 vs R7 category vocabulary mismatch) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:33 · (R12 HTML source has no filename) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:33 · (Artifact contract: body fragment, favicon, read-before-republish unstated) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:32 · (R11 "as /precon's" misdescribes the ruled mechanism) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:34 · ("substantive disagreement" is judgment) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:56 · (Slice B ACs trust the builder's note; doc traces unnamed) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:38 · (AC1 checks skip plugin.json; grep too loose) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:34 · (R13 disagreement taxonomy is elaboration beyond scope :34) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:5 · (no runnable check; rule-6 smell not recorded as flagged and accepted) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:56 · (AC numbering restarts per slice while requirements got B-R prefixes) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:15 · (a `Plan: inspected` stamp sits inside the Out of scope parse range) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:42 · (AC5 enforces the invented guard set) · not fixed — doc unchanged since the prior run
- MINOR · architect-skill-build-plan.md:3 · (Intent embellishes Tony's profile beyond the record) · not fixed — doc unchanged since the prior run

### 2026-09-02 — inspect: plan
MAJOR · docs/architect-skill-build-plan.md:5 · "rule-6 smell … accepted by Tony in ordering the amendment" has no record — Tony's word was "fix the blockers/majors", not an acceptance · /build and /signoff treat manual-only verification as owner-approved when it was asserted · claude-fable-5-1
MAJOR · docs/architect-skill-build-plan.md:5 · `claude --plugin-dir` session-load and edit-pickup behaviour is asserted as fact, not listed under Build assumptions, and is the sole mechanism behind AC2 and every Slice B criterion · if the flag does not surface /architect or pick up branch edits, Slice B re-tests nothing · claude-fable-5-1
MAJOR · ~/Documents/architect-scope.md:41 · decided "offer comes once, at the end of every run" stands unstruck while assumed :55 removes the offer for docless runs; build doc R3/R13 adopt :55 · two builders reading the two lines build two rules; Tony never ruled · claude-fable-5-1
MAJOR · docs/architect-skill-build-plan.md:64 · B-AC1 grades "the architecture doc's header names [the scope doc]" and B-AC3 (:66) grades a run log recording the three interview steps, but R8/R9 require neither field · a SKILL.md built correctly to Slice A fails Slice B · claude-fable-5-1
MAJOR · docs/architect-skill-build-plan.md:39 · R13's "fixed instruction" to the reviewer is never given; AC6 (:49) checks only that one is present · builder invents the one user-visible contract of the blind review · claude-fable-5-1
MAJOR · docs/architect-skill-build-plan.md:73 · Slice B edits SKILL.md but never refreshes `slice-a-requirement-map.md`, whose entries are SKILL.md line numbers (AC3) · first B fix silently invalidates the map /signoff passed Slice A on · claude-fable-5-1
MAJOR · docs/architect-skill-build-plan.md:42 · README.md:92 carries a second count ("the catalog — 19 entries") AC7's grep cannot catch (numeral, not "twenty") · Slice A passes AC7 with README saying 19 beside a 20-entry catalog · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:48 · AC5's grep pattern uses `|` without `-E`; plain grep treats it literally and returns 0 hits · builder passes AC5(a) having inspected nothing · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:44 · AC1 requires plugin.json keys and the line7works `repository`, but its verify commands never open plugin.json · stale URL or missing key passes · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:49 · AC6 counts four Judge G guards, but jpb SKILL.md:191-194 defines three (scope-doc-only payload is architect's own rule) and says "neutral empty directory", not "absolute … created fresh" · the literal comparison AC6 orders cannot pass · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:42 · "CLAUDE.md carries no per-skill roster" is false — CLAUDE.md:14-25 lists six pre-migration skills; say "do not add architect to that list" · builder reconciles or adds a bullet · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:42 · README's roster is three groups (README.md:33-70); the doc does not say architect goes in "The build loop" between precon and blueprint · wrong group misfiles the station · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:28 · R2 globs `<repo>/docs` only when invoked inside a repo, but precon writes repo-owned scope docs regardless of cwd (precon SKILL.md:59); glob is best-effort · repo-owned doc invisible from ~ · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:28 · R2 "matched by title" never says title of what against what · builder invents the match key · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:36 · "loop skill" undefined in this doc; B-AC8's "zero loop-skill invocations" is ungradeable at the edge · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:57 · Slice B Goal is three semicolon-joined clauses, not one sentence (code book :46) · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:62 · B-R4 is a doc-numbering convention filed as a product requirement · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:48 · AC5(b) "one full read" has no pass condition · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:60 · B-R2 "material behavior change" is the builder's call; no criterion tests it · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:30 · R4's interview-length guardrail has no acceptance criterion in either slice · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:68 · B-AC5 keeps "(or the tiny exit-ramp form)" though B-AC2 fixes the run to a real system · dead branch · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:5 · "house style … match the voice" has no criterion; stays taste · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:34 · R8's docless-home rule is cited to "scope ledger, assumed 2026-09-01" but scope :58 gives only the docless slug · citation attributes a rule the ledger lacks · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:33 · R7 (scope :39, assumed) and R9 (scope :50, assumed) carry no assumed tag while neighbours do; Build assumptions (:78) still empty · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:32 · R6 widens decided scope :18's five categories via assumed :39 "or any other one-way-door category"; B-AC4 grades the widened form · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:36 · R10's carve-out (scope :64) excepts a rule "invokes no other skill" that appears nowhere in the ledger · circular sourcing · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:31 · R5's "no server unless … no database unless …" examples are unsourced and untagged (scope :16 states the razor only) · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:39 · R13 disagreement taxonomy "(at minimum: …)" elaborates beyond scope :34, untagged · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:29 · R3 "no provisioning beyond a repo" beside R10 "creates no repos" and AC5's `create .*repo` grep · grader must decide if the hit is inside a prohibition · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:5 · Constraints date the docs/ move 2026-08-31; adjudication block (:161) and closure line (:192) say 2026-09-01 · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:10 · "parked for a later blueprint talk" — scope :73 records only that it is parked · claude-fable-5-1
MINOR · docs/architect-skill-build-plan.md:159 · adjudication block's FIXED/RULED lines carry no severity token or file:line; carried from prior runs, not editable under rule 7 · claude-fable-5-1
QUESTION · ~/Documents/architect-scope.md:41 · rule the docless/blind-review offer: strike :41 in favour of assumed :55, or restore the every-run offer and say what a docless reviewer receives · claude-fable-5-1
QUESTION · ~/Documents/architect-scope.md:26 · decided :26 ("~/Documents/<project>-architecture.md") stands unstruck beside assumed :58's repo-owned home; strike or amend :26 as :29 was · claude-fable-5-1
QUESTION · docs/architect-skill-build-plan.md:70 · B-AC7 "If he declines: pass" — accept as a stated limit (the plan cannot force Tony's word) and record it, or add a criterion that exercises R13 · claude-fable-5-1
BLOCKER · docs/architect-skill-build-plan.md:60 · (B-R2 /plugin update loop GitHub-sourced) · fixed
BLOCKER · docs/architect-skill-build-plan.md:29 · (docless run vs mandatory offer vs scope-doc-only payload) · fixed — by assumed scope :55; decided :41 unstruck, see QUESTION
BLOCKER · docs/architect-skill-build-plan.md:30 · (R4 guardrail softened) · fixed
BLOCKER · docs/architect-skill-build-plan.md:39 · (R13 transport guards unsourced) · fixed
MAJOR · docs/architect-skill-build-plan.md:44 · (AC1 install clause unrunnable pre-merge) · fixed
MAJOR · docs/architect-skill-build-plan.md:3 · (findings doc does not exist) · fixed
MAJOR · docs/architect-skill-build-plan.md:36 · (R10 no-skill rule vs artifact-design) · fixed
MAJOR · docs/architect-skill-build-plan.md:5 · (Artifact publish as external send) · fixed
MAJOR · docs/architect-skill-build-plan.md:28 · (R2 discovery invented; docless input) · fixed
MAJOR · docs/architect-skill-build-plan.md:34 · (R8 pre-repo home / docless slug) · fixed
MAJOR · docs/architect-skill-build-plan.md:32 · (R6 run-log location; categories closed list) · fixed
MAJOR · docs/architect-skill-build-plan.md:38 · (R12 missing-URL mechanics) · fixed
MAJOR · docs/architect-skill-build-plan.md:40 · (R14 fields invented) · fixed
MAJOR · docs/architect-skill-build-plan.md:46 · (Slice A AC2 sole check / judgment) · fixed
MAJOR · docs/architect-skill-build-plan.md:48 · (AC4 universal negative) · fixed
MAJOR · docs/architect-skill-build-plan.md:65 · (AC2 both branches one run) · fixed
MAJOR · docs/architect-skill-build-plan.md:70 · (AC7 pass on decline) · not fixed — see QUESTION
MAJOR · docs/architect-skill-build-plan.md:71 · (AC8 evidence note cannot prove negatives) · fixed — limit stated
MAJOR · docs/architect-skill-build-plan.md:61 · (evidence path off-convention/undated) · fixed
MAJOR · docs/architect-skill-build-plan.md:42 · (Footprint roster line / stale counts) · fixed
MAJOR · docs/architect-skill-build-plan.md:5 · (rule-6 smell not recorded as accepted) · not fixed — closed by an unrecorded acceptance, see MAJOR above
MAJOR · docs/architect-skill-build-plan.md:5 · (installed_plugins has no architect) · fixed
MAJOR · docs/architect-skill-build-plan.md:159 · (adjudication block malformed) · not fixed — ledger history, rule 7

### 2026-09-02 — adjudication (Tony's rulings on the 2026-09-02 inspect QUESTIONs; drafting session amended the seven MAJORs on "fix")
RULED · ~/Documents/architect-scope.md:41 · Q1 docless blind-review offer · "agreed no offer" — scope :41 struck, decided line added; R13 now cites decided 2026-09-02
RULED · ~/Documents/architect-scope.md:26 · Q2 architecture doc home · "besides the scope doc" — scope :26 struck, decided line added; R8 now cites decided 2026-09-02
RULED · docs/architect-skill-build-plan.md:71 · Q3 B-AC7 decline passes · "accept" — recorded as a stated limit in B-AC7 and the scope doc
FIXED · docs/architect-skill-build-plan.md:5 · rule-6 acceptance claim withdrawn; stands as an open smell
FIXED · docs/architect-skill-build-plan.md:5 · `--plugin-dir` behaviour moved to Build assumptions A1, verified at AC2
FIXED · docs/architect-skill-build-plan.md:35,36 · R8 requires the header to name the scope doc; R9's run log records the three steps — B-AC1/B-AC3 now trace
FIXED · docs/architect-skill-build-plan.md:40 · R13 reviewer instruction written verbatim
FIXED · docs/architect-skill-build-plan.md:61,74 · Slice B refreshes the requirement map after the last fix
FIXED · docs/architect-skill-build-plan.md:43,51 · README.md:92 numeral count named; AC7 grep catches "N entries"; roster group and CLAUDE.md six-list clarified
FIXED · docs/architect-skill-build-plan.md:49 · AC5 grep is `grep -nE`

### 2026-09-02 — review: Slice A
MAJOR · plugins/architect/skills/architect/SKILL.md:21 · a scope doc the glob cannot see, or a bare invocation naming no project, falls into the docless gate with no "ask for the path first" step · Tony runs /architect from ~ for a repo-owned project → docless run, doc in ~/Documents, no review offer · Slice A review
MAJOR · plugins/architect/skills/architect/SKILL.md:91 · republish never says to pass the recorded URL to the Artifact tool · a fresh session republishes with only the file path → second artifact, stale Artifact line · Slice A review
MAJOR · plugins/architect/skills/architect/SKILL.md:103 · no failure path for the codex call; an empty or errored response is saved verbatim and reported "done at <path>"; Review field has no failed value · empty codex response → empty review file, comparison walks nothing · Slice A review
MAJOR · plugins/architect/skills/architect/SKILL.md:104 · the call config omits `model:` though :103 says pinned · session sends on the codex default model · Slice A review
MAJOR · plugins/architect/skills/architect/SKILL.md:76 · run-log template labels the interview Step 1/2/3 while headings say 3.1/3.2/3.3; no exit-ramp form · an exit-ramp run must fill "candidates" for an interview that never had them; B-AC2 reads the branch from this log · Slice A review
MAJOR · plugins/architect/skills/architect/SKILL.md:39 · "the first human who is not Tony" narrows R4 / scope :15 ("a named real person"); Deviations says none · a personal tool where Tony is the first real user stalls step 3.1 · Slice A review
MAJOR · plugins/architect/.claude-plugin/plugin.json:3 · present-tense "/sunrise provisions from and /blueprint slices from" the doc in plugin.json, the marketplace entry, and README.md:40; neither skill reads it today · a marketplace stranger expects pickup that does not happen · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:89 · HTML source beside the doc lands in a public repo's docs/ when the project is public, beside "never publish anywhere public" · Tony's call whether "private" means the Artifact only · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:21 · matches by Intent line where R2 says "matched by title" · unrecorded wording change · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:25 · "no research documents" added to R11's property line · a scope doc's own Research: file could be refused · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:103 · pin reference is an absolute repo path, not the installed copy or ${CLAUDE_PLUGIN_ROOT} · dangles on a machine without the clone · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:8 · AC5 descriptive hits (:8, :10, :53, :134) are neither prohibitions nor the R13 passage · a strict grader could refuse AC5(a) · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:47 · guardrail matches the plan's paraphrase, not the scope's text word for word · R4 says verbatim · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:89 · visual renders before Step 6 rulings change the doc; no re-render instruction · artifact ends the run stale · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:76 · run numbering rule unstated; review-ruled edits after the run log is written have no logging instruction · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:89 · nothing says to omit the favicon on republish · run 2 in a fresh session changes the icon · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:31 · exit-ramp run still gets the full blind-review instruction and comparison walk against a three-line doc · no short-circuit · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:51 · slug from a non-conforming scope-doc filename passed by path has no rule · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:47 · "the sorted scope" is precon vocabulary, undefined here · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:14 · :14 says never invokes any skill; rule 7 (:117) says no loop skill; :89 carves out artifact-design · a literal session refuses the preflight on :14 · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:8 · precon's Next: lines route straight to /blueprint and never name /architect; the file does not acknowledge it · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:23 · precon's napkin (no scope doc) and the exit ramp (static page) are different smallness tests, neither names the other · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:25 · NEEDS CHECK vs precon's `parked: needs research` — two vocabularies for one concept · Slice A review
MINOR · README.md:40 · roster line is four clauses where neighbours are one · style drift · Slice A review
MINOR · docs/evidence/architect/slice-a-requirement-map.md:1 · "slice" in a docs/ filename could match a tier-2 slice-doc hunt when a build plan is absent · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:45 · sunrise already keeps docs/decisions/ (ADRs) for architecture decisions; poured concrete is a second home with no cross-reference · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:104 · cwd says absolute and empty but names no location; sessions will pick different places · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:59 · Artifact: header line has a placeholder on run 1 before a URL exists; `|` either-or on :58 has no drop rule · Slice A review
MINOR · plugins/architect/skills/architect/SKILL.md:91 · no instruction for a recorded URL that no longer resolves · Slice A review

### 2026-09-02 — recheck: Slice A
MAJOR · plugins/architect/skills/architect/SKILL.md:21 · (a scope doc the glob cannot see, or a bare invocation naming no project, falls into the docless gate with no "ask for the path first" step) · fixed — :21 asks for a path on zero matches, lists all on a bare invocation
MAJOR · plugins/architect/skills/architect/SKILL.md:91 · (republish never says to pass the recorded URL to the Artifact tool) · fixed — now :92, url parameter named
MAJOR · plugins/architect/skills/architect/SKILL.md:103 · (no failure path for the codex call; empty or errored response saved and reported done) · fixed — now :106 FAILED review rule, :135 Review: failed value
MAJOR · plugins/architect/skills/architect/SKILL.md:104 · (the call config omits model:) · fixed — now :105
MAJOR · plugins/architect/skills/architect/SKILL.md:76 · (run-log template labels Step 1/2/3 vs headings 3.1/3.2/3.3; no exit-ramp form) · fixed — now :77-80
MAJOR · plugins/architect/skills/architect/SKILL.md:39 · ("the first human who is not Tony" narrows R4) · fixed
MAJOR · plugins/architect/.claude-plugin/plugin.json:3 · (present-tense downstream pickup claim in plugin.json, marketplace entry, README.md:40) · fixed — all three hedge "hand-pointed until the reworks land"

### 2026-09-02 — review: Slice B
MAJOR · plugins/architect/skills/architect/SKILL.md:35 · "an item his answer does not mention is accepted at its recommendation" applies to the exit ramp and the candidate pick · Tony answers only the date; the session records the chosen candidate and a "system" exit-ramp on its own recommendation — the nod the skill forbids · Slice B review
MAJOR · docs/evidence/architect/smoke-run-2026-09-02.md:18 · B-AC2 graded pass though the exit ramp was batched with step 3.1 and never answered by Tony · a no-system idea would have had 3.1 asked before the ramp resolved · Slice B review
MAJOR · docs/architect-skill-build-plan.md:93 · B-R2's re-run-through of a materially changed step not done; Deviations says none · the silence rule, report timing, and template lines ship untested in a --plugin-dir session · Slice B review
MAJOR · docs/evidence/architect/smoke-run-2026-09-02.md:28 · "nothing else changed" and "each marked with its ruling number" are false against the architecture doc (walkthrough :17 and storage :57 also changed; deferred :69–70 unmarked) · the note misreports the run · Slice B review
MINOR · plugins/architect/skills/architect/SKILL.md:58 · template header order (Scope/Artifact/Blind review) and run-log label (Rulings:) differ from the only existing doc (Scope/Blind review/Artifact; "Blind review:" plus seven lines) · a re-run must rewrite run-1 lines or carry two vocabularies · Slice B review
MINOR · plugins/architect/skills/architect/SKILL.md:60 · "Blind review: ... | none yet" has no declined / failed / docless form · a declined run reads as pending forever · Slice B review
MINOR · plugins/architect/skills/architect/SKILL.md:108 · backgrounded-call rule does not say the empty/errored guard applies to the response that arrives; no wait bound · a completed-but-empty notification can pass as a review · Slice B review
MINOR · plugins/architect/skills/architect/SKILL.md:108 · unescape covers &amp; &lt; &gt; only and cannot tell whether the harness escaped at all · a take containing literal entities is corrupted; &quot; is half-handled · Slice B review
MINOR · plugins/architect/skills/architect/SKILL.md:129 · report waits on Tony's answer to the offer; if he never answers no block prints · Slice B review
MINOR · plugins/architect/skills/architect/SKILL.md:88 · re-run instruction omits the new Rulings line · a run-2 block lacks the line the template requires · Slice B review
MINOR · plugins/architect/skills/architect/SKILL.md:60 · two more `|` either-or template lines with no drop rule (Slice A MINOR :58 now has three instances) · Slice B review
MINOR · plugins/architect/skills/architect/SKILL.md:92 · visual renders before Step 6 rulings and the report now carries rulings-inclusive counts beside a pre-rulings artifact; no re-render instruction · Slice B review
MINOR · docs/evidence/architect/slice-a-requirement-map.md:19 · R13 row carries a duplicated phrase · hand-patched regeneration · Slice B review
MINOR · docs/architect-skill-build-plan.md:80 · Slice B ledger blocks inserted above Slice A's under each heading; house order is chronological · Slice B review
MINOR · docs/evidence/architect/smoke-run-2026-09-02.md:53 · the five fixes are described without SKILL.md line numbers · a recheck has nothing to open to · Slice B review
MINOR · docs/evidence/architect/smoke-run-2026-09-02.md:20 · B-AC3 asks the note to quote the transitions; it paraphrases · Slice B review
MINOR · docs/evidence/architect/smoke-run-2026-09-02.md:3 · run quotes are second-hand (relayed by the running session after the run); spec accepts self-report at B-AC8 only · Slice B review
MINOR · ~/Developer/Pour-Guys/docs/bar-builder-architecture.md:7 · free-text timing note inside the "exact" format · a downstream parser meets an unlisted section · Slice B review
MINOR · ~/Developer/Pour-Guys/docs/bar-builder-architecture.md:85 · "agreed on the spine" under-lists what the reviewer and the repo already settle (code-owned layout, stable venue ids, repeatable migrations, API boundary) and names two items the doc never records · Slice B review
MINOR · ~/Developer/Pour-Guys/docs/bar-builder-architecture.html:123 · projection says "no documented path found yet" where the doc poses an open question · Slice B review
MINOR · ~/Developer/Pour-Guys/docs/bar-builder-architecture.html:2 · Google Fonts link, three typefaces, palette, dark-mode block — past "keep the first version plain" · Slice B review
MINOR · ~/Developer/Pour-Guys · commit 6a61a54 rides the pre-existing slice-f1 branch with ten unrelated commits; the drawings reach main only when that branch merges · Slice B review

### 2026-09-02 — recheck: Slice B
MAJOR · plugins/architect/skills/architect/SKILL.md:35 · (silence-accepted rule applies to the exit ramp and the candidate pick) · fixed — :29 ramp asked alone, :35 exemption, :43 pick in words; exercised live in a headless --plugin-dir run
MAJOR · docs/evidence/architect/smoke-run-2026-09-02.md:18 · (B-AC2 graded pass though the ramp was batched and unanswered) · fixed — note states it plainly and points at the fix
MAJOR · docs/architect-skill-build-plan.md:93 · (B-R2 re-run-through not done; Deviations "none") · fixed — re-run-through recorded in the note; Deviation with builder-call label
MAJOR · docs/evidence/architect/smoke-run-2026-09-02.md:28 · ("nothing else changed" / "each marked" false against the doc) · fixed — all five changed places described and verified
MINOR · docs/architect-skill-build-plan.md:94 · broke: Deviation inventory incomplete — names three un-rerun fixes, omits the codex guard (:108) and cwd (:107) edits — a reader concludes everything else was exercised · Slice B fix
MINOR · docs/evidence/architect/slice-a-requirement-map.md:9 · broke: map not regenerated after the last fix (9d13e36) — line refs still resolve but the R3/R4/R6 prose omits the new asked-alone / in-his-own-words mechanisms; B-R2's letter · Slice B fix

### 2026-09-02 — recheck: Slice B
MINOR · docs/architect-skill-build-plan.md:94 · (Deviation inventory incomplete) · fixed — all five un-rerun items named with builder-call label
MINOR · docs/evidence/architect/slice-a-requirement-map.md:9 · (map not regenerated after the last fix) · fixed — header names 9d13e36; R3/R4/R6 prose current; R13 duplicate gone; every R1–R15 cite lands

### 2026-09-02 — recheck: named MINORs (Slice A + Slice B, per user; fixed in 7549a44)
MINOR · plugins/architect/skills/architect/SKILL.md:14 · (:14 says never invokes any skill; rule 7 says no loop skill; :89 carves out artifact-design) · fixed — :14 now says "loop skill" and names the artifact-design preflight as the one exception; :94, :123, :150 agree
MINOR · plugins/architect/skills/architect/SKILL.md:89 · (visual renders before Step 6 rulings change the doc; no re-render instruction) · fixed — :96 re-renders and republishes to the same URL after the rulings, report prints after that
MINOR · plugins/architect/skills/architect/SKILL.md:58 · (template header order differs from the only existing doc) · fixed — template now Scope doc / Blind review / Artifact (:56-60), :86 forbids reshuffling; Pour-Guys header :3-5 already matches
MINOR · plugins/architect/skills/architect/SKILL.md:60 · ("Blind review: ... | none yet" has no declined / failed / docless form) · fixed — :59 carries declined / failed / none — docless forms, :86 says the line leaves "none yet" when the run ends
MINOR · plugins/architect/skills/architect/SKILL.md:103 · (pin reference is an absolute repo path) · fixed — :108 points at the installed jpb copy (newest version dir), repo path secondary
MINOR · plugins/architect/skills/architect/SKILL.md:108 · broke: two back-to-back parentheticals in the pin sentence — readability only, no rule conflict · this batch
