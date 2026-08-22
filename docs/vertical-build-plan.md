# Vertical — build plan (2026-08-21)

Intent: /vertical is the capstone of Tony's build loop (blueprint → build → signoff →
recheck). After every slice of a build is individually signed off and rechecked, one
big adversarial review of the whole vertical runs: Claude at full scope plus outside
frontier models (ChatGPT, Gemini) with a reject-it mandate, merged into one verified
verdict doc. It is the final inspection before a build is called done. Scope doc
(settled ground, harvest first): `~/Developer/tony-skills/docs/vertical-scope.md`.
Cold-read record with the blueprint-altitude disposition table:
`~/Documents/precon-cold-reads/vertical-cold-read-2026-08-21.md`.

Constraints:
- The deliverable is one skill: `~/.claude/skills/vertical/SKILL.md` plus
  `~/.claude/skills/vertical/assets/vertical-mandate.md` (the outside-reviewer prompt
  template). House style matches `~/.claude/skills/signoff/SKILL.md` and
  `~/.claude/skills/digest/SKILL.md` (frontmatter `name` + `description`, prose rules,
  What NOT to do, SKILL NOTE convention).
- The skill is instructions Claude follows plus one prompt asset — no new scripts.
  Transports reuse /jpb's recorded recipes (`~/.claude/skills/jpb/assets/box-runners.md`)
  with ONE deliberate inversion, stated in R6: jpb's parity denies repo access (neutral
  cwd); /vertical grants it — the whole point is that outside models read the code.
  Web access stays OFF both places.
- Pinned models: GPT `gpt-5.6-sol` via `mcp__codex__codex`; Gemini
  `gemini-3.1-pro-high` via `mcp__antigravity__ask_gemini`. Pins change only on Tony's
  word (jpb's standing rule). DeepSeek/OpenRouter is not a reviewer.
- /signoff's doctrine is inherited wholesale, not reinvented: finding shape
  (claim · file:line · concrete failure scenario · severity BLOCKER/MAJOR/MINOR ·
  confidence), verify-before-reporting (CONFIRMED/PLAUSIBLE, Refuted: N), severity →
  verdict mapping, report-don't-repair.
- The skill writes exactly one file per run: the verdict doc. Never code, never the
  build plan, never statuses. Fixes after the verdict are Tony's separate instruction.
- No git write commands. Protected paths stay untouched:
  `~/.claude/projects/*/memory/`, `*.jsonl` transcripts, `~/.claude/settings.json`.
- Interactive use only. Every external send happens only after Tony answers the
  per-run ask in that run — never from a remembered or default answer.
- Test command: none (markdown skill); verification is manual, per slice criteria.

Out of scope:
- DeepSeek as a reviewer — Tony ruled ChatGPT + Gemini only, cost per run (scope doc).
- Diff-only disclosure to outside models — Tony chose full code (scope doc).
- Self-fixing after the verdict — Tony ruled stops at the verdict (scope doc).
- Headless/CI invocation — interactive only, like every loop skill (scope doc).
- Canonical repo copy under tony-skills plugins/ — user-level skill only for v1,
  matching /digest's ruling; revisit if it ever ships publicly.
- Changes to /signoff, /recheck, /ship, or /jpb — /vertical only reads their
  conventions and assets; sibling skills are not touched.

## Slice A — the /vertical skill
Goal: author SKILL.md and the mandate asset so any fresh session can run a correct
vertical review end to end, local-only or with outside reviewers.
Requirements:
- R1: Frontmatter `name: vertical`; `description` triggers on "/vertical", "vertical
  review", "run the vertical", "whole-build signoff" and states it runs only after all
  slices are signed off and rechecked.
- R2 (gate): The skill takes a build-doc path argument, else hunts the current repo's
  `docs/*build-plan*.md` the way /ship does. It reads every `## Slice` heading's
  `Status:` line; the gate passes only when every slice reads `signed off`. Anything
  less: report exactly which slices are short and STOP. Only wording in Tony's own
  invocation ("run it anyway") collapses the gate; a collapsed gate is recorded in the
  verdict doc's Method line. Gate check runs BEFORE the per-run ask — no point picking
  reviewers for a run that stops.
- R3 (per-run ask): After the gate, stop and ask: local-only review, or local +
  ChatGPT + Gemini? Recommended default is local + both, but the skill always waits
  for an answer — silence never proceeds — and Tony may answer with any subset
  ("local + ChatGPT only" is legal). The answer applies to this run only.
- R4 (local review): Claude runs a /signoff-style review at vertical scope: the whole
  vertical against its base — the base being the build's starting commit, determined
  from the build doc/branch history, recorded in the verdict doc. The local review
  runs regardless of what outside reviewers were picked, and forms its findings
  before reading any outside section (independence).
- R5 (cold packet): Each outside reviewer receives exactly: the build doc verbatim,
  the full tracked code, and the change boundary — the base commit id plus the list
  of files the vertical touched. Never per-slice signoff verdicts, never chat
  history, never another reviewer's output. The mandate asset carries the reject-it
  instruction and the /signoff finding shape verbatim, composed like jpb composes
  box-mandate + template.
- R6 (transports): GPT — `mcp__codex__codex`, `model: "gpt-5.6-sol"`,
  `sandbox: "read-only"`, `config: {"web_search": "disabled"}`, cwd pointed at the
  code copy (R7) — the deliberate inversion of jpb's neutral-cwd rule, stated in the
  SKILL.md so nobody "fixes" it back. Gemini — `mcp__antigravity__ask_gemini`,
  `model: "gemini-3.1-pro-high"` (never also pass effort), workspace pointed at the
  code copy; an EMPTY response is a FAILED run (a fully-denied agy run still reports
  SUCCESS — jpb's verified trap). Web-off parity is recorded per reviewer in the
  verdict doc, jpb's parity-line style.
- R7 (secrets): Outside reviewers must be physically unable to read secrets: the code
  they see is a tracked-files-only copy of the base-to-head state (e.g. a `git
  archive`-style export to the session scratchpad), never the live working tree —
  untracked files, gitignored files, `.env`, and credential files never reach the
  copy. The SKILL.md states this as a hard rule with the why.
- R8 (merge and verify): Findings dedupe on file:line + claim; convergence across
  reviewers is noted on the merged finding. Claude adversarially verifies every
  outside finding against the source before it reaches Tony — /signoff's
  CONFIRMED/PLAUSIBLE stamps, refuted findings dropped from the verdict and counted
  (`Refuted: N`), a hallucinated file:line is a refutation unless Claude locates the
  real site and says so. Claude then compares the merged set against the per-slice
  verdicts it holds (repeats and misses are called out in the verdict prose).
- R9 (verdict doc): One file, `docs/vertical-signoff-<date>.md` in the reviewed repo
  (second run same day: `-2` suffix; never overwrite a prior run's doc). Top section
  is THE VERDICT: /signoff's severity → verdict mapping, Method line (what ran, base
  commit, reviewers used, parity lines, any collapsed gate), merged verified findings
  in /signoff's punch-list line format so /recheck can consume them, `Refuted: N`,
  repeats/misses vs prior slice verdicts. Below it, one section per reviewer — raw
  output VERBATIM — under a banner naming it an unverified appendix.
- R10 (failure and stop): A reviewer that errors, times out, or returns empty is
  dropped with its reason recorded in the verdict doc; the run continues with
  survivors; the local review always completes. After writing the verdict doc the
  skill stops — offers fixes, never starts them.
Acceptance criteria:
- AC1: `~/.claude/skills/vertical/SKILL.md` and `assets/vertical-mandate.md` exist;
  frontmatter matches R1 — verify: manual read.
- AC2: Every scope-doc decision is enforced by an explicit SKILL.md rule (gate, ask,
  full-code, cold, boundary, secrets, stops-at-verdict) — verify: manual trace of the
  scope doc's Decisions list against SKILL.md, line by line.
- AC3: Transport recipes match `box-runners.md` except the documented repo-access
  inversion and the packet contents; the inversion and the agy empty-response trap
  are stated in SKILL.md — verify: manual diff of R6 against box-runners.md.
- AC4: The mandate asset contains the reject-it instruction, the finding shape, and
  placeholders for build doc + boundary; no placeholder for prior verdicts exists —
  verify: manual read.
- AC5: SKILL.md names the verdict-doc format of R9 exactly, including the unverified
  appendix banner and the -2 suffix rule — verify: manual read.
Footprint: ~/.claude/skills/vertical/SKILL.md, ~/.claude/skills/vertical/assets/vertical-mandate.md (both new)
Not in this slice: running the skill live (Slice B); any edit to sibling skills.
Depends on: nothing
Status: signed off

## Slice B — live smoke on jpb
Goal: prove the skill works on a real completed build — Tony's /jpb repo, whose five
slices all stand signed off.
Requirements:
- R1: Run /vertical against `~/Developer/jpb/docs/jpb-build-plan.md`. The gate must
  pass on the real statuses. The per-run ask must fire and wait; the local-only leg
  runs for real and writes `~/Developer/jpb/docs/vertical-signoff-<date>.md` in the
  R9 format.
- R2: Gate negative test — run against a fixture build doc in the scratchpad with one
  slice not `signed off`; the skill must name that slice and stop. The fixture never
  lives in a repo.
- R3: Outside leg — compose the cold packet and verify both transports resolve (pins
  present, tools reachable) up to the edge of sending. The actual send happens only
  if Tony says so during the smoke when the ask fires; if he declines, the packet
  contents are inspected instead: build doc + tracked-only code + boundary, no
  verdicts, no secrets.
- R4: Confirm the run wrote exactly one file and touched nothing else (git status in
  jpb shows only the verdict doc).
Acceptance criteria:
- AC1: Gate passes on jpb's real build doc; fixture run stops naming the short slice —
  verify: manual, both runs.
- AC2: The verdict doc exists in jpb/docs, verdict section on top with Method line and
  severity mapping, local findings in punch-list format — verify: manual read.
- AC3: Packet inspection (or live send, on Tony's word) shows full tracked code +
  boundary + build doc and no prior verdicts, no untracked/ignored files — verify:
  manual listing of the packet copy.
- AC4: `git status` in jpb shows only the new verdict doc — verify: manual.
Footprint: ~/Developer/jpb/docs/vertical-signoff-<date>.md (new, the smoke's real
output); scratchpad fixture (throwaway).
Not in this slice: fixing anything the smoke's verdict finds in jpb — /vertical stops
at the verdict by design, and jpb fixes are a separate decision of Tony's.
Depends on: Slice A
Status: signed off

## Build assumptions

### 2026-08-21 — build: Slice A
- Footprint home `~/.claude/skills/` is not a git repo, so no feature branch exists
  for this slice; matches how /digest and /ship were built — builder call.
- The mandate asset adds a "Concerns without location" channel for findings an
  outside reviewer cannot pin to file:line, so unpinned hunches are reported without
  masquerading as located claims — extends /signoff's report-everything doctrine to
  R5's shape — builder call.
- R6's agy repo access written as "directory-grant mechanism (--add-dir semantics)"
  without pinning the exact tool parameter — the antigravity MCP surface may name it
  differently per session; Slice B's smoke resolves the concrete form — builder call.

## Deviations

### 2026-08-21 — build: Slice B (live smoke, run in the jpb session)
- R3's edge-of-send inspection was superseded: Tony answered the per-run ask "local +
  both," authorizing the real send, so the outside leg ran live (packet contents
  verified anyway: 28-file tracked-only export, boundary e6500df..HEAD, no
  untracked/ignored/.env, no prior verdicts) — per user.
- The GPT packet's [BUILD_DOC] slot pointed at docs/jpb-build-plan.md inside the
  workspace (identical tracked bytes) instead of inlining ~65k chars — recorded in
  the verdict doc's Method line — builder call.

## Discovered

### 2026-08-21 — amendment: dirty-tree rule scoped (per user)
- The clean-tree precondition is scoped: only dirt touching the change boundary or
  the build doc stops the run; unrelated dirt is listed in the Method line and both
  legs review committed state (HEAD). Ordered by Tony after the first live Atlas run
  stopped on unrelated docs (/fb keeps feedback.md perpetually dirty) — per user.

### 2026-08-21 — build: Slice B (live smoke)
- agy can return status ERROR with a full, substantive response. The skill defines
  empty = failed and error = dropped, but not error-with-complete-content; the smoke
  treated non-empty-complete as a delivered survivor per the empty-is-the-signal
  doctrine and recorded the anomaly in the Method line. SKILL.md may want an explicit
  rule for this case — logged, not built.

## Punch list

### 2026-08-21 — review: Slice A
- MAJOR · SKILL.md:51 · Gemini workspace mechanism wrong, skip_permissions guard dropped · box-runners passes workspace via cwd and pins skip_permissions OFF; "--add-dir semantics" names no real ask_gemini parameter — denied-empty run or unguarded grant · Slice A review
- MAJOR · SKILL.md:37 · no dirty-working-tree behavior · uncommitted work → export stale, boundary omits it, legs review different code silently · Slice A review
- MAJOR · SKILL.md:32 · base has two non-equivalent definitions, no indeterminable handling · builds on main with interleaved commits → sessions pick different bases → different scopes · Slice A review
- MAJOR · SKILL.md:36 · non-git target unexecutable, no defined stop · non-repo footprint → Steps 3-4 impossible, no report path · Slice A review
- MAJOR · SKILL.md:18 · gate passes vacuously on zero-slice or missing-Status doc · wrong file → empty-set pass → nonsensical review · Slice A review
- MAJOR · SKILL.md:59 · Step 5 reads per-slice verdicts that exist only in dead chats · fresh session has only ledger + Status lines; repeats/misses partly impossible · Slice A review
- MAJOR · SKILL.md:67 · "so /recheck can consume them" is a false promise · /recheck reads the build-doc ledger vertical never writes; no card resolves post-gate · Slice A review (spec R9 shares the inaccurate rationale)
- MAJOR · assets/vertical-mandate.md:31 · locationless concerns have no merge path · Step 5 verifies only on file:line; routing undefined → sessions diverge · Slice A review
- MINOR · SKILL.md:67 · punch-list line format drops signoff's 5th attribution field · format-identity claim false · Slice A review
- MINOR · SKILL.md:66 · Method line outside THE VERDICT section vs R9's placement · collapsed-gate disclosure lands below the verdict · Slice A review
- MINOR · assets/vertical-mandate.md:34 · severity definitions paraphrased vs R5's "verbatim" · reviewer/merge grading drift channel · Slice A review
- MINOR · SKILL.md:16 · "same narrowing as /ship" overstates the hunt · docs/*build-plan*.md misses docs/plan.md the loop may have used · Slice A review
- MINOR · SKILL.md:18 · gate provenance prose wrong for clean first-pass signoffs · reader may demand a needless recheck · Slice A review
- MINOR · SKILL.md:18 · built-card fail prose gives no remedy pointer (fresh /signoff, not /recheck) · Tony misrouted after a rebuild · Slice A review
- MINOR · SKILL.md · interactive-only scope decision has no explicit rule · headless local-only run not textually forbidden · Slice A review
- MINOR · SKILL.md:50 · GPT base-instructions/prompt split inverts box-runners' composition order · packet contents in base-instructions vs jpb's brief-in-prompt · Slice A review
- MINOR · SKILL.md:63 · "ONLY write" literal tension with Step 3's export tree · maximally literal session refuses the export · Slice A review
- MINOR · SKILL.md:39 · empty boundary undetected · packet ships naming no new work · Slice A review
- MINOR · SKILL.md:63 · third same-day run unstated (-3 extrapolation implied, unsaid) · Slice A review
- MINOR · SKILL.md:63 · <date> format unstated · breaks -2 collision detection across sessions · Slice A review
- MINOR · SKILL.md:50 · GPT review-request prompt content undefined · divergent parity between runs · Slice A review
- MINOR · SKILL.md:51 · Gemini parity line has no establishing mechanism · unearned parity line or strict drop every run · Slice A review
- MINOR · SKILL.md:46 · "Claude runs a /signoff-style review" readable as solo review · rule 9 deference likely saves it; ambiguity at the most dangerous spot · Slice A review

### 2026-08-21 — recheck: Slice A
- MAJOR · SKILL.md:51 · (Gemini workspace mechanism wrong, skip_permissions dropped) · fixed — cwd is the workspace param, skip_permissions OFF stated, matches box-runners
- MAJOR · SKILL.md:37 · (no dirty-working-tree behavior) · fixed — clean-tree precondition, STOP + Tony's call recorded in Method
- MAJOR · SKILL.md:32 · (base ambiguous, no indeterminable handling) · fixed — ordered precedence ending in ask-Tony-never-guess
- MAJOR · SKILL.md:36 · (non-git target unexecutable) · fixed — git-repo precondition with report-and-STOP
- MAJOR · SKILL.md:18 · (vacuous gate) · fixed — zero-slice / missing-Status = malformed input, STOP
- MAJOR · SKILL.md:59 · (per-slice verdicts unobtainable) · fixed — comparison reads the on-disk ledger only, empty-ledger case stated
- MAJOR · SKILL.md:67 · (/recheck consumability false promise) · fixed — claim replaced with the accurate opposite statement
- MAJOR · assets/vertical-mandate.md:31 · (locationless concerns unrouted) · fixed — appendix-only unless verified into a file:line
- MINOR · SKILL.md Step 3 · broke: preconditions fire after Step 2's ask — dirty-tree/non-git stop happens after Tony already picked a crew, contradicting Step 1's gate-before-ask principle · Slice A fix pass introduced

### 2026-08-21 — recheck: Slice A (lap 2)
- MINOR · SKILL.md Step 3 · (preconditions fire after the ask) · fixed — checks moved into Step 1 with the gate, no residual copy in Step 3, ordering prose now matches

### 2026-08-21 — review: Slice B
- MINOR · jpb/docs/vertical-signoff-2026-08-21.md:11 · "four of six cost rows" miscount · file has seven rows, four mangled; audit patches wrong scope · Slice B review
- MINOR · jpb/docs/vertical-signoff-2026-08-21.md:16 · outside MAJORs re-graded to MINOR with no demotion note · conditions count unauditable · Slice B review
- MINOR · jpb/docs/vertical-signoff-2026-08-21.md:13 · PLAUSIBLE→CONFIRMED upgrade undocumented · provenance gap, substantively correct · Slice B review
- MINOR · jpb/docs/vertical-signoff-2026-08-21.md:41 · refutation rests on out-of-repo harness claim · if wrong, a dropped second MAJOR · Slice B review
- MINOR · jpb/docs/vertical-signoff-2026-08-21.md:35 · "working tree clean" contradicted by the doc's own untracked self · pedantic Method inaccuracy · Slice B review
- MINOR · run Method line · Gemini "plan mode" param beyond the recipe's exactly-list · precedent for ad-hoc flags · Slice B review
- MINOR · run Method line · GPT parity line drops the specified colon form · literal parity audits miss it · Slice B review
- MINOR · run Method line · GPT build doc as in-workspace pointer vs "verbatim" · disclosed builder call, SKILL NOTE emitted; a reviewer could skip opening it · Slice B review

### 2026-08-21 — recheck: launch-prep MINOR fixes (user-named set, Slices A+B blocks)
- MINOR · SKILL.md:16 · (hunt glob misses /build's doc tiers) · fixed — hunts /build's tiers within /ship's two-source narrowing
- MINOR · SKILL.md:46 · ("Claude runs" readable as solo review) · fixed — fresh subagent reviewers originate findings, never the session solo
- MINOR · SKILL.md:50 · (GPT prompt content undefined; parity colon form) · fixed — fixed literal prompt line, parity copied literally
- MINOR · SKILL.md:51 · (Gemini ad-hoc params possible) · fixed — exactly-these-and-no-others, no modes/flags
- MINOR · SKILL.md Step 5 · (silent merge re-gradings) · fixed — re-grades recorded on the finding with a one-clause why
- MINOR · SKILL.md:63 · (date format and -3 rerun unstated) · fixed — YYYY-MM-DD, -2/-3/and-so-on, never overwrite
- MINOR · SKILL.md:67 · (verdict finding line missing attribution field) · fixed — 5th field: which reviewer(s) found it
- MINOR · SKILL.md rules · (interactive-only unstated) · fixed — rule 10, never headless/script/cron
- MINOR · vertical-mandate.md:35 · (severity defs paraphrased) · fixed — verbatim match to /signoff's table

### 2026-08-21 — recheck: dirty-tree scoping amendment (per user)
- (amendment) · SKILL.md:23 · (any-dirt stop → scoped to boundary + build doc) · fixed — scoped stop, Method-line listing, both legs at HEAD all verified; no contradictions with export/secrets/ordering/one-write rules
- MINOR · SKILL.md:23 · a should-have-been-touched file with only uncommitted changes reads as unrelated dirt · fail-loud, not silent: HEAD review flags the requirement missing and the Method line lists the dirt; confusing verdict possible after a post-signoff uncommitted touch-up · recheck noted, left open by design
