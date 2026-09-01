# Ship skill — build plan (2026-08-20)

Intent: /ship runs one whole slice loop with a single command — find the build doc,
/build the named slice, /signoff, fix every BLOCKER + MAJOR, /recheck, at most one
extra fix+recheck lap, then report. It replaces the chain Tony hand-types every slice
(`/goal /build slice A of docs/<plan>.md then /signoff and fix any blocker & majors,
then /recheck`). Scope doc (settled ground, harvested): ~/Documents/ship-scope.md.
Handoffs: ~/Documents/handoffs/2026-08-20-ship-skill-handoff.md + parent
2026-08-20-three-new-loop-skills-handoff.md. Cold read + disposition:
~/Documents/precon-cold-reads/ship-cold-read-2026-08-20.md.

Constraints:
- Skill file at ~/.claude/skills/ship/SKILL.md, house style of the loop skills
  (blueprint/build/signoff/recheck/precon: spine paragraph, numbered rules, fixed
  report block, "What NOT to do", SKILL NOTE convention). Siblings run 91–143 lines;
  stay in that band.
- Composes /build, /signoff, /recheck, and /blueprint's doc-hunt BY NAME — never
  copies their content in, so upstream changes flow through.
- Documented summon line is `/goal /ship <slice> [doc]` typed by Tony; the skill
  itself never claims to arm the Stop hook (it can't — vault
  01-domain/claude-goal-hook/_index.md, rule 8, run-4 evidence).
- Validation method: run-twice-and-diff (skill-lab convention).
- Git gates and all standing CLAUDE.md rules hold inside a /ship run.

Out of scope:
- Replacing /goal — Tony ruled wrap-only ("keep goals strong and as is").
- A third fix+recheck lap unasked — handoff: "never a third lap unasked".
- /digest and /vertical — sibling skills with their own handoffs, built after /ship.
- Editing the sibling skills — /ship adapts to them, not the reverse.

## Slice A — the SKILL.md
Goal: write the complete /ship skill file implementing every decided mechanism, in house style.
Requirements:
- R1 — Invocation `/ship <slice> [doc]`. Build doc auto-hunted the way /blueprint does it (by name, not copied); 2+ candidates = ask Tony; zero candidates = ask Tony.
- R2 — Step zero: verify the "Stop hook is now active" confirmation appeared for this session; report armed or not-armed in the final report. Runs either way, honestly labeled. Documented summon line in the skill text: `/goal /ship <slice> [doc]`.
- R3 — Fixed step order: find doc → /build the named slice → /signoff → fix every BLOCKER + MAJOR directly in this session (never by re-invoking /build) → /recheck → if not ALL CLEAR, exactly ONE more fix+recheck lap on still-open findings only → stop.
- R4 — MINORs are left unless Tony says otherwise in the invocation or mid-run.
- R5 — Four stop conditions, each "stop and report", never "use your judgment": (1) retry lap exhausted without ALL CLEAR, (2) a fix would change the spec, (3) /build honestly stops mid-slice, (4) the work wants to touch files outside the slice scope (scope = what the build doc's slice defines, per /build's boundary rules).
- R6 — Pause-vs-stop rule stated explicitly: a sub-skill question addressed to Tony pauses the run and passes the question through; the four enumerated conditions stop it.
- R7 — Final report block: slice, verdict, card status, hook armed/not-armed, what was fixed, what remains; plus the SKILL NOTE self-feedback convention (as in signoff/precon: only when a rule was worked around, reinterpreted, or excepted).
- R8 — Composition by name throughout: the file names /build, /signoff, /recheck and blueprint's hunt; it never restates their internal rules.
- R9 — "What NOT to do" list covering at minimum: no third lap, no spec edits as fixes, no out-of-scope file touches, no silently skipping signoff or recheck, no claiming the hook armed when it didn't, no git push/PR/merge (standing gates hold).
Acceptance criteria:
- AC1: ~/.claude/skills/ship/SKILL.md exists with valid frontmatter (name + description that triggers on "/ship", "ship slice X") — verify: manual: file present, frontmatter parses, `ls ~/.claude/skills/ship/`.
- AC2: every requirement R1–R9 is locatable in the file by line — verify: manual: R-by-R checklist against the file.
- AC3: sibling content not copied in: no restatement of build/signoff/recheck internal rule text — verify: manual: spot-diff distinctive phrases from sibling SKILL.md files, zero matches.
- AC4: file length within the sibling band (~90–145 lines) — verify: manual: `wc -l`.
Footprint: ~/.claude/skills/ship/SKILL.md (new dir + file).
Not in this slice: any live run; edits to sibling skills; memory updates.
Depends on: nothing
Status: signed off

## Slice B — live smoke test
Goal: one real /ship run end to end with Tony on a small genuine slice; every mechanism observably fires; fixes fold back into the SKILL.md.
Requirements:
- R10 — Tony picks the target (a real repo with a real build doc and an unbuilt slice) and types the full summon line `/goal /ship <slice> [doc]`.
- R11 — Observe and record: step-zero hook verification result, doc hunt, build, signoff, fix pass, recheck, report block — against the R1–R9 checklist.
- R12 — Any defect found folds back into the SKILL.md in this slice; run notes land in ~/Documents/skill-lab/ (ship-smoke-run-<date>.md).
- R13 — Run-twice-and-diff applies at /signoff time for the SKILL.md itself, per the skill-lab convention.
Acceptance criteria:
- AC5: one completed live run whose final report block matches R7's shape — verify: manual: the run's transcript/report.
- AC6: run notes file exists in skill-lab recording what fired and what was fixed — verify: manual: file present.
Footprint: ~/.claude/skills/ship/SKILL.md (fixes only), ~/Documents/skill-lab/ship-smoke-run-<date>.md.
Not in this slice: building /digest or /vertical; goal-hook run-log entries (Tony's vault process owns those).
Depends on: Slice A
Status: signed off

## Build assumptions

### 2026-08-20 — build: Slice A
- ~/.claude/skills/ is not a git repo and has no test suite; feature-branch and before-photo preflight steps do not apply (siblings were built the same way) — builder call
- "Card: <final Status>" field added to the SHIP report block to satisfy R7's "card status"; wording drawn from /recheck's Status vocabulary by reference, not copied — builder call
- Pause-vs-stop got its own section rather than a line inside a step, since R6 calls it load-bearing — builder call
## Deviations

### 2026-08-20 — build: Slice B
- R13 (run-twice-and-diff at /signoff for the SKILL.md) not exercised — Slice A's signoff used a three-lens adversarial review instead; flagging rather than absorbing — builder call
- Repo-confined hunt language (the run-1 fold-back) untested live: run 2 resolved its doc from the session tier, no hunt ran — builder call to flag, not rerun

### 2026-08-20 — fix pass: Slice A
- Doc hunt composed from /build's Step 1, not /blueprint's, contra R1/R8's wording — /blueprint defines no build-doc hunt (it hunts scope docs and defines the save path); /build Step 1 is where the build-doc hunt lives. Surfaced in the signoff verdict's Questions; standing unless Tony disowns — builder call
## Discovered
## Punch list

### 2026-08-20 — review: Slice A
- BLOCKER · SKILL.md:36-40 · clean SIGNED OFF has no route to ALL CLEAR · zero-finding slice falls through "Not ALL CLEAR" into the lap counter and reports STOPPED condition 1 · Slice A review
- MAJOR · SKILL.md:20 · hunt attributed to /build Step 1 vs spec R1/R8's "/blueprint's hunt", deviation unlogged · AC2 R-by-R walk fails on R1/R8; silent spec deviation · Slice A review
- MAJOR · SKILL.md:20 · hunt rules restated and extended ("explicit doc argument wins" defined by no sibling; "reconstructed from memory" near-verbatim /build lift) while claiming composition by name · AC3 spot-diff fails; upstream changes to /build's hunt silently diverge · Slice A review
- MAJOR · SKILL.md:32 · "fix every BLOCKER and MAJOR" vs stop condition 4 on sweep findings from prior slices · session either exceeds slice scope or stops the run on the first sweep item; no precedence stated · Slice A review
- MAJOR · SKILL.md:40 · "nothing new enters" contradicts recheck's fix-introduced-defect door · lap-2 fix pass skips a fix-introduced defect as out of scope; run ends STOPPED on an item the text forbade touching · Slice A review
- MAJOR · SKILL.md:46,68 · Result: PAUSED in the report contradicts pause semantics · one session emits a SHIP block at a pause (converting it to a stop), another never uses the value · Slice A review
- MAJOR · SKILL.md:56 · mid-fix waiver has no writer under rule 2's "writes nothing into the build doc" · Tony waives a MAJOR during the fix pass; the line lands nowhere, recheck still counts the item, run ends STOPPED against his ruling · Slice A review
- MAJOR · SKILL.md:66-69 · report fields unfillable on early stop (no "not reached" values; Laps only 1|2) · every early-stopped session invents its own filler · Slice A review
- MINOR · SKILL.md:16 · hook-check mechanism underspecified ("for this run" undefined with multiple /goal wraps) · sessions disagree on what counts as armed · Slice A review
- MINOR · SKILL.md:20 · Step 1's "stop and ask" unclassified against the Pause/Stop taxonomy · one session STOPs with no citable condition, another pauses · Slice A review
- MINOR · SKILL.md:58,69 · "lap" never defined · Laps field filled inconsistently · Slice A review
- MINOR · SKILL.md:69 · Card field has no vocabulary anchor · fresh session doesn't know the value set · Slice A review
- MINOR · SKILL.md:44-47 · model-floor stops and recheck's fresh-session-dispute dead end fit neither pause nor stop · lap 2 burns on an item that structurally cannot clear in-session; report misdiagnoses as lap exhausted · Slice A review
- MINOR · SKILL.md:24,47 · /build preflight stops (failed foundation, dependency standing) ambiguous between condition 3 and a pause · safe either way but two different runs · Slice A review
- MINOR · SKILL.md:36 · "invoke /recheck on the fixed findings" reads as a named-entries invocation, scoping recheck to the named set · phrasing risk only; sets should coincide · Slice A review

### 2026-08-20 — recheck: Slice A
- BLOCKER · SKILL.md:36-40 · (clean SIGNED OFF has no route to ALL CLEAR) · fixed — clean route now at Step 3, line 28
- MAJOR · SKILL.md:20 · (hunt attributed to /build vs spec's /blueprint, deviation unlogged) · fixed — deviation ledgered with authority
- MAJOR · SKILL.md:20 · (hunt rules restated and extended) · fixed — Step 1 defers wholly to /build's definition
- MAJOR · SKILL.md:32 · (fix-everything vs stop condition 4 on sweep findings) · fixed — precedence stated, punch list scoped to this slice
- MAJOR · SKILL.md:40 · (nothing-new-enters contradicts recheck's narrow door) · fixed — lap includes fix-introduced defects
- MAJOR · SKILL.md:46,68 · (Result: PAUSED contradicts pause semantics) · fixed — enum reduced, pause never emits the block
- MAJOR · SKILL.md:56 · (mid-fix waiver has no writer) · fixed — /ship writes the dated line as the receiving station
- MAJOR · SKILL.md:66-69 · (report fields unfillable on early stop) · fixed — not reached / not run / Laps 0 admitted
- MAJOR · SKILL.md:90 · broke: What-NOT-to-do bullet still bans all build-doc writes after the waiver exception was sanctioned — a session honoring the bullet refuses Tony's mid-fix waiver line, reproducing the original failure
- MAJOR · SKILL.md:28 · broke: clean-signoff bypass skips Steps 4–6 unconditionally — Tony's invocation-ordered MINOR pass never runs on a clean verdict; no rule says which line wins

### 2026-08-20 — recheck: Slice A (lap 2)
- MAJOR · SKILL.md:90 · (What-NOT-to-do bullet bans all build-doc writes after waiver exception sanctioned) · fixed — carve-out added, consistent with rule 2 and Step 4
- MAJOR · SKILL.md:28 · (clean-signoff bypass drops invocation-ordered MINOR pass) · fixed — qualifier added; MINOR pass runs first, non-gating, no recheck

### 2026-08-20 — review: Slice B
- MAJOR · SKILL.md:20 · repo confinement overrides /build's vault-project-folder tier while rule 1 claims no overrides · same summon resolves under bare /build, pauses under /ship · Slice B review
- MAJOR · SKILL.md:20 · "not inside a repo = pause" unconditional, fires before /build's session tier · home-cwd session with an in-session plan pauses needlessly (run 2's own resolution path) · Slice B review
- MAJOR · SKILL.md:16 · summon-line shortening shipped as an unruled, unledgered builder call, live-untested against the hook · risks recreating the pause-spin collision it exists to fix · Slice B review
- MAJOR · ship-smoke-run-2026-08-20.md:91-93 · stale "NOT yet exercised live" tail contradicts the run-2 final record · future session re-runs slice C off a false record · Slice B review
- MINOR · SKILL.md:16 · copy-paste summon print ambiguous (placeholders vs concrete values at Step 0) · Slice B review
- MINOR · SKILL.md:28,32 · clean-bypass MINOR-fix path has no inspector; a fix-introduced defect there goes unnamed under ALL CLEAR · pre-existing, sharpened by amendment 4 · Slice B review
- MINOR · SKILL.md:46 · pause defined as a station's question; Step 4's Tony-only-MAJOR pause originates from /ship itself · literal reading converts it to a stop · Slice B review
- MINOR · run notes · AC5 verified via cross-session report, not a seen transcript · hearsay chain a strict reading refuses · Slice B review
- MINOR · SKILL.md:20 · R1 "blueprint's hunt" spec mismatch re-shipped in the rewritten sentence · already a ledgered deviation; flag only · Slice B review

### 2026-08-20 — recheck: Slice B
- MAJOR · SKILL.md:20 · (repo confinement overrides /build's vault tier unspoken) · fixed — override stated aloud as deliberate, per Tony's repo-only ruling
- MAJOR · SKILL.md:20 · (not-in-repo pause fires before the session tier) · fixed — session-established plan is an allowed source before any pause
- MAJOR · SKILL.md:16 · (summon clause unruled and untested) · fixed — bare summon per Tony's word; goal semantics defined in the skill
- MAJOR · ship-smoke-run-2026-08-20.md:91-93 · (stale tail contradicts run-2 record) · fixed — replaced with explicit removal note
- MINOR · ship-smoke-run-2026-08-20.md:44-46,79-84 · broke: historical fold-back notes now describe the removed carve-out design as current — needs a "superseded by bare-summon redesign" annotation
