# Skill-loop edits — build plan (2026-08-02)

Intent: Tie the three loop skills (blueprint → build → signoff) into one consistent
system and add the missing re-inspection station, /recheck. Today, fixes made after a
signoff verdict are never independently verified (the next signoff's scope rule
excludes them as belonging to a different slice), status flags go stale after fixes
(a rejected-then-fixed slice reads `rejected` forever), and a fresh build session
cannot tell which punch-list entries are the MAJORs its preflight requires fixed.
These edits close those seams. The agreed working sequence this enables:
build A → signoff A → fix → recheck A (card flips) → build B → signoff B (sweep
finds nothing open, moves on).

Constraints:
- All targets are prose skill files under `~/.claude/skills/<name>/SKILL.md`. Not a
  git repository and no test suite exists — /build's feature-branch and before-photo
  preflight steps do not apply; verification is the grep/read checks named per
  criterion.
- House style is load-bearing: frontmatter `name` + `description` (with trigger
  phrases, under 1,024 chars), a short opening frame, bolded spine, numbered rules,
  compact `ALLCAPS:` chat output block with `·` separators, a "What NOT to do" list.
  Match the register of the existing three skills.
- Surgical edits only. Signoff's A/B-validated spine (anti-rubber-stamp rule, the
  ten rules' substance, reviewer independence, report-everything-then-filter,
  mandatory "Tried and failed to break") stays intact except where a requirement
  names the change.
- Model-agnostic: no model names hardcoded, except the existing model-floor pattern
  ("Opus-class or better; omit the override so agents inherit") which /recheck
  copies from /signoff.
- Skills auto-load from `~/.claude/skills/<name>/SKILL.md`; creating the directory
  and file is the whole installation.
- Punch-list ledger law is additive-only everywhere: no skill ever rewrites or
  resolves an earlier entry; state changes are recorded as new dated blocks and
  `Status:` line updates.

Out of scope:
- Blueprint SKILL.md edits — reviewed this session; needs none. Its wargame harvest
  line deliberately stays (supports the wargame → blueprint chain Tony intends).
  (Superseded 2026-08-02, narrowly: Slice D R4 authorizes exactly three stale
  sentences in blueprint to be refreshed. The wargame harvest line still stays.)
  (Amended 2026-08-02: Slices F and J also edit blueprint per their own recorded
  requirements — F-R1/F-R2/F-R3 and J-R1/J-R2 — and queued Slice K adds its
  `SKILL NOTE:` line there via K-R3. The wargame harvest line still stays.)
  (Corrected 2026-08-02: the amendment above overcounts F — its blueprint edits
  are F-R2 and F-R3 only; F-R1 edits signoff:10. The slice roster D, F, J, K
  stands.)
- The wargame skill — standalone by Tony's decision; never tied into the loop.
- Fable/Opus-specific hardening (Stop hooks, /goal contracts,
  disable-model-invocation) — deferred until a baseline run shows the symptom.
- Any further ceremony scaling beyond signoff's LIGHT mode.
- Retrofitting old punch lists or ledgers to the new severity/authority formats —
  new entries only; readers treat unlabeled old entries per the stated defaults.

## Slice A — the /recheck skill
Goal: A standalone skill that verifies named fixes against a closed checklist, with
a fresh reviewer, and flips the slice's status card.
Requirements:
- R1: New skill at `~/.claude/skills/recheck/SKILL.md`, name `recheck`. Description
  triggers: "recheck", "recheck slice A", "recheck the fixes", after a fix pass on
  signoff findings. Tony rejected "signoff recheck" as too much to type.
- R2: Closed checklist, not a review. Input: the still-open BLOCKERs and MAJORs —
  punch-list entries not cleared by the latest recheck block, plus the chat
  verdict's findings when the session has them — deduped on file:line + claim.
  MINORs join only when the user names them, and never gate. The user naming a
  previously cleared item re-opens it (the one sanctioned expansion). Each item
  needs severity, file:line, claim, and failure scenario; what the record lacks is
  recovered from the chat verdict or supplied/confirmed by the user — a
  reconstructed scenario becomes the test only after user confirmation. Each
  checklist item resolves to exactly **fixed** or **not fixed**. An empty checklist
  against a card reading `rejected` or `signed off with conditions` is a record
  gap — say so and ask; never report "nothing to recheck" against an open card.
- R3: The narrow door. A defect *introduced by the fix* enters as a NEW named item
  with its own claim, file:line, failure scenario, and an orchestrator-assigned
  severity (/signoff's table). An item can be not fixed and also have broken
  something — two records. A pre-existing issue newly noticed does not enter — no
  hunting license; at most one line offering /signoff.
- R4: Independence, floor, and conservative adjudication. One fresh subagent
  reviewer verifies the items; the session that wrote the fixes never grades them.
  Same model floor as /signoff. Adjudication may confirm outcomes or downgrade
  fixed → not fixed with evidence; upgrading not fixed → fixed requires evidence
  the reviewer lacked and is forbidden when the session wrote the fix — the
  dispute is recorded, the item stays open, a fresh-session recheck is recommended.
- R5: Verification is earned. Each item is checked against its recorded failure
  scenario — executed where runnable, static otherwise — and the method is declared
  in the output. Read-only posture: report, don't repair; no mutations of real
  state.
- R6: Status from everything open — unfixed checklist items plus fix-introduced
  defects at their assigned severities: any BLOCKER open → `rejected` (demoting a
  higher card is authorized); else any MAJOR open → `signed off with conditions`;
  else → `signed off`. MINORs, named or not, never move the Status (matches
  /signoff, which signs with MINORs on the punch list).
- R7: Punch-list record: one block appended to the doc's `## Punch list` (created
  if missing), headed `### <YYYY-MM-DD> — recheck: <slice>`; one line per checklist
  item: severity · file:line (the ORIGINAL entry's location — the join key; post-fix
  location noted in the clause when code moved) · fixed | not fixed; one line per
  fix-introduced defect: severity · file:line · broke: claim — scenario. Latest-
  dated block wins conflicts. Additive-only; earlier entries are never edited. This
  block is what /signoff's sweep reads to know what is still open.
- R9: Doc and slice resolution. Hunt path mirrors the siblings
  (docs/<feature>-build-plan.md, docs/, plan/, vault project folder, session);
  a correctness-only review resolves to docs/punch-list.md with no Status writes
  (no card exists — stated in the output). Unnamed slice: the latest-dated
  punch-list review block among slices standing `signed off with conditions` or
  `rejected`; ambiguity → ask; other open slices are named in the output.
- R8: Compact chat output block in house style (`RECHECK:` header): per-item
  results, method, the Status change stated, and what remains open if anything.
Acceptance criteria:
- AC1: File exists with valid frontmatter (name `recheck`; description carries the
  trigger phrases, under 1,024 chars) and the body is lean — under 120 lines —
  verify: read + `wc -l`.
- AC2: The closed-list mandate, the fixed/not-fixed outcomes, the new-item door
  with assigned severity, and the record-gap and re-open provisions all appear —
  verify: read against R2/R3.
- AC3: The R6 mapping appears with demotion authorized and MINORs excluded from
  gating — verify: read.
- AC4: The additive punch-list block is specified and editing earlier entries is
  forbidden — verify: read + `grep -i additive`.
- AC5: No open-review language anywhere: nothing instructs finding issues beyond
  fix-introduced defects — verify: read.
- AC6: Model-agnostic: `grep -iE 'fable|opus'` matches only the model-floor line —
  verify: grep.
- AC7: `RECHECK:` output block present in house style — verify: read.
Footprint: `~/.claude/skills/recheck/SKILL.md` (new file, new directory)
Not in this slice: any edit to signoff, build, or blueprint files.
Depends on: nothing
Status: signed off

## Slice B — signoff tie-backs
Goal: Signoff writes durable severity-labeled findings, sweeps unfinished prior
slices, guards reviewer independence from the ledger, adjudicates deviations by
authority, and offers a light mode.
Requirements:
- R1: Severity and scenario on every punch-list line. Format becomes: severity ·
  `file:line` · claim · concrete failure scenario · which slice's review found it.
  Review blocks are headed `### <YYYY-MM-DD> — review: <slice>` — no verdict word
  in the doc. The chat verdict's finding lines carry the claim field too, so
  /recheck's dedup key (file:line + claim) is computable from either source. (A
  fresh session must be able to find "the named MAJORs" from the doc alone AND
  re-test them — the scenario is the test /recheck depends on.)
- R2: REJECTED leaves a durable record: on a REJECTED verdict, the BLOCKERs and
  any MAJORs are appended to the punch list too, severity-labeled, same format.
- R3 (amended in the Slice B fix pass): The sweep (backstop, not primary). Any
  prior slice standing `signed off with conditions` or `rejected` brings its
  still-open BLOCKERs/MAJORs into scope — open meaning not cleared by the
  LATEST-DATED recheck block (matching /recheck's rule). The REVIEWERS verify the
  swept items — never the orchestrator alone, and never on the word of the session
  that wrote the fixes. An open card with no matching open entries is a record
  gap: reported, /recheck recommended, never treated as clear. The verdict carries
  "Prior conditions: N verified fixed · M still open". Only full clearance (every
  item fixed, no fix-introduced defects) flips the prior card, to `signed off`,
  recorded as a standard recheck-format block so the clearing record is durable
  and shared with /recheck; anything less leaves the card untouched and recommends
  /recheck. Fix-introduced defects found by the sweep get assigned severity, are
  attributed to the prior slice, and block the flip. MINORs never gate and are
  not swept.
- R4: Ledger off-limits to reviewers. The reviewer mandate states: the build doc's
  `## Build assumptions`, `## Deviations`, `## Discovered`, `## Punch list`
  sections and `Status:` lines are the builder's and inspector's working records —
  not spec, not evidence. Blueprint-authored `Out of scope:` and `Not in this
  slice:` lines remain spec. The orchestrator still reads the ledger for rule-4
  adjudication; that split already exists.
- R5: Two-tier deviation adjudication in rule 4. A `## Deviations` entry labeled
  "per user" is sanctioned descope → Deferred, not a defect. An entry labeled
  "builder call" — or carrying no label — that leaves an acceptance criterion unmet
  caps the verdict at SIGNED OFF WITH CONDITIONS and appears in the verdict as a
  question for the user. Disclosure changes honesty, not doneness. (Fix-pass
  amendment:) the capping deviation is appended to the punch list as a MAJOR line
  whose claim is the open question — the card's conditions must survive the chat.
- R6: LIGHT mode, below LEAN: one fresh reviewer with a fused spec + correctness
  lens; the execute step and every rule stay intact. Selected only by the user's
  invocation or the user accepting signoff's offer when the diff is small — never
  self-selected. (Fix-pass amendment:) DEEP's content triggers outrank LIGHT — a
  slice touching auth, money, or user data gets the conflict named and DEEP run;
  the user can insist after hearing why, and the Depth line records it.
- R7: Wargame reference removed: the opener's parenthetical about /wargame is cut;
  the loop line reads blueprint → build → signoff.
- R8: The verdict points at the next station: under SIGNED OFF WITH CONDITIONS or
  REJECTED, the output names /recheck as the path to flip the card after fixes.
Acceptance criteria:
- AC1: `grep -i wargame` on signoff's SKILL.md returns nothing — verify: grep.
- AC2: Punch-list line format carries severity, and the REJECTED path appends
  BLOCKERs — verify: read.
- AC3: Sweep language present: prior-slice scope pull, latest-dated recheck-block
  awareness, reviewer (not orchestrator) verification, the record-gap guard, the
  "Prior conditions:" verdict line, and the full-clearance-only flip with its
  recheck-format clearing block — verify: read.
- AC4: Reviewer mandate excludes the four ledger sections and Status lines while
  keeping blueprint's descope lines as spec — verify: read.
- AC5: Rule 4 distinguishes "per user" from "builder call"/unlabeled, with the
  WITH CONDITIONS cap and the user question — verify: read.
- AC6: LIGHT mode present with the never-self-selected guard — verify: read.
- AC7: Surgical footprint: file stays under 150 lines and rules 1–10 keep their
  substance apart from the named changes — verify: `wc -l` + read the diff.
- AC8: A WITH CONDITIONS / REJECTED verdict names /recheck — verify: read.
Footprint: `~/.claude/skills/signoff/SKILL.md`
Not in this slice: recheck (Slice A) and build (Slice C) files.
Depends on: Slice A (references /recheck by name)
Status: signed off

## Slice C — build tie-backs
Goal: Build names its upstream, transcribes blueprint's slice anatomy instead of
re-deriving it, and labels deviation authority.
Requirements:
- R1: The opener names /blueprint as the plan-drawer (the current line credits
  /wargame — it predates blueprint); loop reads blueprint → build → signoff. No
  wargame reference remains.
- R2: Step 1's hunt path names `docs/<feature>-build-plan.md` (what /blueprint
  writes) first, then the existing fallbacks (docs/, plan/, vault, session).
- R3: Contract-is-transcription: against a blueprint-format doc, Step 1's contract
  transcribes the slice anatomy — Requirements → In scope, each criterion's stated
  verify → how verified, Footprint → Footprint, Not in this slice → Not authorized,
  Depends on → preflight standing — rather than re-deriving boundaries the doc
  already states. (Fix-pass amendment:) Step 2 carries a Dependency standing
  bullet backing that promise — every slice named in Depends on must stand `built`
  or better; `not started` or `rejected` is a stop-and-report.
- R4: Deviation authority: `## Deviations` ledger entries and the report block's
  Deviations lines carry "per user" (came from a stop-and-ask the user answered) or
  "builder call". Unlabeled reads as builder call downstream, so label honestly.
  (Fix-pass amendment:) `per user` means the user's answer sanctioned the specific
  change — an answered-but-adjacent exchange is still `builder call`.
Acceptance criteria:
- AC1: `grep -i wargame` on build's SKILL.md returns nothing — verify: grep.
- AC2: The hunt path opens with the blueprint filename — verify: read.
- AC3: The transcription sentence appears in Step 1 — verify: read.
- AC4: The authority label appears in both the Step 5 ledger spec and the Output
  block's Deviations line — verify: read.
- AC5: Surgical footprint: file stays under 115 lines; no rule loses substance —
  verify: `wc -l` + read the diff.
Footprint: `~/.claude/skills/build/SKILL.md`
Not in this slice: signoff and recheck files.
Depends on: nothing
Status: signed off

## Slice D — record integrity (waivers, rebuilds, failed foundations, stale references)
Goal: every card state and open finding is derivable from the doc alone — through
waivers, rebuilds, and rejected foundations.
Requirements:
- R1 (waivers): when the user explicitly waives a named finding, the station that
  received the waiver appends a dated punch-list line — WAIVED (per user) ·
  severity · `file:line` · claim — and sweep, recheck, and build's preflight all
  treat a waived item as closed. Waived is always per user; there is no
  builder-call waiver. (Trace: Slice C review — "explicitly waived has no record
  representation anywhere in the loop.") (Fix-pass amendment, per user:) Full
  lifecycle. Formats are dated: `WAIVED (per user) · <YYYY-MM-DD> · severity ·
  file:line · claim` and revocation `REOPENED (per user) · <YYYY-MM-DD> ·
  file:line · claim`. All three stations carry the append authorization and
  format in their own text — their write enumerations include these lines. The
  latest-dated record for an item (recheck line, WAIVED, REOPENED) decides its
  state, and the filter applies to doc entries and chat findings alike. The
  station appending a waiver also updates the slice's card from what remains
  open, waived items excluded; an open card whose items are all waiver-closed is
  stale — updated per the mapping, never a record gap. Any named finding is
  waivable; only the user's word creates or revokes.
- R2 (rebuilds): a COMPLETE build on a slice standing `rejected` or `signed off
  with conditions` still sets `built`, and appends a dated punch-list note that
  the slice was rebuilt and its open findings need re-verification against the
  new code. Signoff's sweep treats a `built` card with uncleared BLOCKER/MAJOR
  entries as open scope — reported and verified, never skipped — and recheck's
  unnamed-slice resolution includes such slices. (Trace: Slice C review — rebuild
  orphans open findings.) (Fix-pass amendment, per user:) Clearance on a rebuilt
  `built` slice closes the entries but the card stays `built` — rebuilt code
  earns its verdict only from a fresh /signoff, never from the sweep or recheck.
  The built-with-open-entries state is "a rebuild awaiting re-verification," not
  a record inconsistency.
- R3 (failed foundations): build's preflight stops and reports when the
  immediately prior slice stands `rejected` — no framing on a failed foundation
  without the user's word. (Trace: Slice B verdict Deferred; Discovered entry.)
- R4 (blueprint refresh, narrowly authorized): blueprint's opener counts recheck
  among the doc's consumers; the format-is-load-bearing line adds recheck to the
  key-off list; the Status ownership line reads that /build sets `built` and
  /signoff and /recheck set the verdict states. Nothing else in blueprint
  changes; the wargame harvest line stays. (Trace: Slice A and C reviews.)
Acceptance criteria:
- AC1 (amended): the dated WAIVED/REOPENED formats, the append authorization
  inside each station's own write rules, and closed-treatment with
  latest-dated-wins appear in build, signoff, and recheck — verify: read all
  three + grep WAIVED and REOPENED.
- AC2 (amended): the rebuild note, the sweep's built-with-open-entries scope
  pull, recheck's resolution inclusion, AND the stays-built clearance rule
  (verdict only from a fresh /signoff) are present — verify: read build Step 5,
  signoff sweep, recheck Steps 1 and 4.
- AC3: the stop-on-rejected preflight bullet is present — verify: read build
  Step 2.
- AC4: the three blueprint sentences updated; wargame harvest line intact —
  verify: read + grep wargame in blueprint (exactly the harvest line remains).
- AC5: line budgets hold (build ≤ 115, signoff ≤ 150, recheck ≤ 120, blueprint
  ≤ 115) and no rule loses substance — verify: wc + diff read.
Footprint: all four SKILL.md files (small edits each).
Not in this slice: the open MINOR backlog on the punch list (separate triage);
any loop-shape rewording of the three-station openers (family-wide question,
user's call pending).
Depends on: Slice C
Status: signed off

## Slice E — MINOR cleanup (write enumerations, join keys, preflight vocabulary, signoff wording debts)
Goal: close eleven mechanical MINORs from the punch-list backlog with one-line
edits, per the 2026-08-02 reconcile and the user's triage ("yes blueprint").
Requirements:
- E-R1 (write enumeration, signoff): the exhaustive further-doc-writes list
  explicitly names the stale-card mapping update the sweep itself commands.
  (Trace: Slice D recheck broke-MINOR, signoff:125.)
- E-R2 (write enumeration, build): Step 5's punch-list guard names the REOPENED
  line alongside the waiver line, since Step 2 commands both appends.
  (Trace: Slice D recheck broke-MINOR, build:56.)
- E-R3 (don't-list carve-out, build): the don't-list punch-list bullet carves
  out the appends Steps 2 and 5 sanction instead of a flat prohibition.
  (Trace: Slice D review, build:101.)
- E-R4 (claim in clearing lines, recheck): the clearing-line format gains the
  claim — severity · file:line · (claim) · fixed | not fixed — so co-located
  findings stay distinguishable. The sweep's own text states the same line
  shape inline — amended 2026-08-02 (fix pass, per user); the original "inherits
  it via 'standard recheck-format block'" was the defect: a cross-file reference
  transmits no content. (Trace: Slice B review recheck:53; Slice D review
  join-key line.)
- E-R5 (join key stated): wherever records join — recheck's assembly and
  clearing, signoff's sweep, build's preflight — the item key is stated as
  file:line + claim. Amended 2026-08-02 (fix pass, per user): each join site
  also states the claimless-record default, byte-identically — "A record with
  no claim field matches on `file:line` alone" — covering the ledger's
  pre-format lines, whose claim never existed as a ·-separated field.
  Amended again 2026-08-02 (second fix pass, per user): the default is scoped
  to single-entry locations — a shared file:line decides nothing and goes to
  the user — and the claim-field boundary is defined: its own ·-separated
  field, wrapping parentheses excluded, a parenthetical glued to the file:line
  is a legacy tag. (Trace: Slice D review, recheck:24,53.)
- E-R6 (preflight vocabulary, build): the caps "SIGNED OFF WITH CONDITIONS"
  string in Step 2 becomes the lowercase backticked status the doc actually
  carries. (Trace: Slice C review, build:31.)
- E-R7 (dependency conditions, build): a dependency standing `signed off with
  conditions` gets the same fixed-or-waived demand the immediately prior slice
  gets. (Trace: Slice D review, build:31-32.)
- E-R8 (rule 10 closing sentence, signoff): amended for the shared-file case to
  match Step 2's section split — reviewers get the spec sections and the diff;
  the ledger sections stay outside their mandate. (Trace: Slice B review,
  signoff:42 vs 87.)
- E-R9 (LIGHT consistency, signoff): "only the reviewer count shrinks" reworded
  so it no longer contradicts the sanctioned added-lens allowance.
  (Trace: Slice B review, signoff:56,58.)
- E-R10 (output slots, signoff): the SIGN-OFF template gains a Next: slot (the
  /recheck pointer under WITH CONDITIONS and REJECTED) and a Questions: slot
  (rule 4's user questions). (Trace: Slice B review, signoff:101,107-121.)
Acceptance criteria:
- AC1: each write enumeration names every write its own steps command —
  signoff's list includes the stale-card update, build's guard includes
  REOPENED, build's don't-list carve-out present — verify: read signoff's
  ledger paragraph and build Step 5 + don't-list; grep REOPENED in build.
- AC2: the claim field appears in recheck's clearing-line format and the
  file:line + claim join key is stated at recheck's assembly, the sweep, and
  build's preflight — verify: read those passages in all three files.
- AC3: grep "SIGNED OFF" in build returns nothing; the with-conditions
  dependency demand is present — verify: grep + read build Step 2.
- AC4: rule 10's closing sentence matches Step 2's split; the LIGHT paragraph
  no longer contradicts the added-lens allowance; the template carries Next:
  and Questions: slots — verify: read rule 10, the LIGHT paragraph, the
  output template.
- AC5: line budgets hold (build ≤ 115, signoff ≤ 150, recheck ≤ 120) and no
  rule loses substance — verify: wc + diff read.
Footprint: build/SKILL.md, signoff/SKILL.md, recheck/SKILL.md (one-line edits;
blueprint untouched).
Not in this slice: loop-shape wording (Slice F); the baseline watch items
(model-floor wording, Fable early-stop, don't-list redundancy — parked per
their own recorded entries until the real-repo baseline); every other open
MINOR the user's triage leaves standing.
Depends on: Slice D
Status: signed off

## Slice F — loop-shape wording
Goal: make the family's loop-shape prose true with /recheck live, per the
user's (a)/(b) call.
Open question (load-bearing, user's call — recommendation attached): (a) three
stations plus a re-inspection visit — recheck stays a visit by the same
inspector, openers stand, two sentences change. Recommended. (b) four-station
rewording — all four openers name the full chain. Resolved 2026-08-02
(per user): (a) — asked at build time, answered "(a) Three stations + visit".
(Corrected 2026-08-02: "(a) two sentences change" undercounted — the answer
touched three requirement sites, F-R1, F-R2, and F-R3; recorded so a spec-lens
read stops raising the false scope-creep question.)
Requirements:
- F-R1 (either answer): signoff's "the last station of the loop" sentence stops
  claiming last-ness — under (a) it names /recheck as its re-inspection visit;
  under (b) it takes its place in the four-station chain. (Trace: Slice B
  review, signoff:10.)
- F-R2 (either answer): blueprint's ledger-ownership sentence stops saying
  "/signoff appends the punch list" alone — it names the actual appenders:
  /signoff and /recheck append blocks, /build appends its sanctioned lines.
  (Trace: Slice D review, blueprint:64.)
- F-R3 (either answer): blueprint's key-off list names /recheck's reads as well
  as its writes. (Trace: Slice D review, blueprint:36.)
- F-R4 (only under (b)): build's and blueprint's three-station openers reworded
  to the four-step chain; under (a) they stand untouched. (Trace: Slice C
  review, build:8.)
Acceptance criteria:
- AC1: no file claims signoff is last while /recheck exists, and the four
  files' shape statements are mutually consistent under the chosen answer —
  verify: read all four openers plus signoff's opening frame.
- AC2: blueprint's ownership sentence names every actual punch-list appender —
  verify: read blueprint Step 4's closing paragraph.
- AC3: line budgets hold (blueprint ≤ 115; others as in E-AC5) — verify: wc.
Footprint: signoff/SKILL.md, blueprint/SKILL.md; build/SKILL.md only under (b).
Not in this slice: everything in Slice E.
Depends on: Slice E
Status: signed off

## Slice G — sweep partial-outcome durability (the standing MAJOR)
Goal: partial sweep results and sweep-found defects survive into the ledger, so
no later recheck flips a card over a lost, known defect.
Requirements:
- G-R1: on partial clearance the sweep appends its recheck-format block anyway —
  one line per verified item, fixed and not fixed alike, in the standard
  clearing-line format; the card-untouched rule is unchanged. (Trace: Slice E
  review MAJOR at signoff:34,127 — "sweep partial outcomes have no sanctioned
  durable write.")
- G-R2: a fix-introduced defect the sweep finds is appended as a punch-list
  line attributed to the prior slice (severity · file:line · claim · scenario ·
  attribution) in the same write; it already blocks the flip — now it also
  survives the chat. (Trace: same entry; Slice B review "no channel for defects
  found mid-sweep.")
- G-R3: signoff's exhaustive further-doc-writes enumeration names the
  partial-clearance block and the attributed defect line. (Trace: same entry.)
Acceptance criteria:
- AC1: the recorded failure scenario no longer holds — a later recheck
  assembling from the record sees the sweep's fixed/not-fixed lines and the
  attributed defect line — verify: read signoff Step 1 + the ledger paragraph
  and walk the scenario end to end.
- AC2: the writes stay format-compatible with recheck's (same heading, same
  line shape, latest-dated-wins unbroken) — verify: side-by-side read of
  signoff's sweep and recheck Steps 1/4.
- AC3: signoff ≤ 150 lines — verify: wc.
Footprint: signoff/SKILL.md.
Not in this slice: Slices H–J; the parked baseline-watch trio (model-floor
wording, Fable early-stop, don't-list redundancy — per user, 2026-08-02, they
wait for the real-repo baseline their entries call for).
Depends on: Slice F
Status: signed off

## Slice H — signoff wording debts
Goal: close every open signoff-file MINOR except the parked trio, one edit per
recorded line.
Requirements (each cites its punch line; the recorded scenario is the test):
- H-R1: signoff:10 — "the upstream skills" antecedent explicitly excludes
  /recheck's records. (F review.)
- H-R2: signoff:10 — visit vocabulary aligned to "re-inspection visit"; the
  card flip named. (F review.)
- H-R3: signoff:122 — the Next: slot no longer strands the sweep's /recheck
  recommendation under a clean current verdict. (E review.)
- H-R4: signoff:127 — the stale-card-update clause de-garden-pathed. (E review.)
- H-R5: signoff:34,127 — "the mapping" given an in-file referent (builder
  decides how: inline it or point at the Severity → verdict section). (E review.)
- H-R6: signoff:34,112 — the Prior-conditions N/M counting rule stated.
  (B review.)
- H-R7: signoff:56 — "genuinely small" bounded (builder picks the boundary
  form). (B review.)
- H-R8: signoff:56,58 — LIGHT-plus-added-lens reviewer arithmetic stated.
  (E review.)
- H-R9: signoff:87 vs 40 — reviewer-input mechanics aligned (spec path vs spec
  sections). (E review.)
- H-R10: signoff:87 vs 34 — a sweep-items carve-out added to rule 10's closing
  sentence. (E review.)
- H-R11: signoff:127 — the builder-call-deviation MAJOR line's mandatory
  file:line/scenario fields resolved for deviations. (E review.)
- H-R12: signoff:34 and recheck:53 — "the clause" holding the post-fix location
  given a defined referent in both files. (E recheck broke-line + its
  pre-existing recheck twin.)
- H-R13: correctness-only mode states its sweep behavior (there is no doc, so
  no sweep — say it). (B review residual.)
- H-R14: signoff:81 vs 87 — rule 4's trust in the `per user` label reconciled
  with rule 10's claims-not-evidence doctrine (builder decides the form; the
  label's meaning is already pinned by build Step 5's definition). (B review —
  the audit's one fully uncovered line.)
Acceptance criteria:
- AC1: each cited punch line's scenario no longer holds at its site — verify:
  read each edited passage against the recorded scenario.
- AC2: signoff ≤ 150, recheck ≤ 120 — verify: wc.
Footprint: signoff/SKILL.md; recheck/SKILL.md (H-R12 only).
Not in this slice: G's sweep writes; the parked trio.
Depends on: Slice G
Status: signed off

## Slice I — build preflight and ledger mechanics
Goal: close every open build-file MINOR; state the cross-file placement rules
where the appends are commanded.
Requirements:
- I-R1: build:31 — the state-deciding record types enumerated (the siblings'
  closed trio: recheck line, WAIVED line, REOPENED line). (E review.)
- I-R2: build:31 vs 56 — Step 2's commanded card update reconciled with Step
  5's verdict-shape ban. (E review.)
- I-R3: build:31, signoff:127, recheck:24,51 — WAIVED/REOPENED append placement
  stated, and a same-date tiebreak defined, byte-identically at every site that
  commands the append. (E review; also closes the header/placement sub-claim of
  the D-review build:31 dateless-WAIVED line.)
- I-R4: build:32-33 — a `built` dependency with uncleared BLOCKER/MAJOR entries
  carries the same fixed-or-waived demand; the rebuilt-over-rejected preflight
  pass-through closed. (D review + E review sharpening.)
- I-R5: build:56 — the rebuild note given an exact dated format. (D review.)
- I-R6: build:16 — hunt-path priority stated. (C review.)
- I-R7: build:25 — Reuse and New given their transcription sources; the
  requirements-to-criteria join stated. (C review.)
- I-R8: build:25 — doc-level Out of scope feeds Not authorized; "seeds" made
  explicitly additive. (C review.)
- I-R9: build:84-85 — the Deviations authority-label placement stated as a
  rule, not a template convention. (C review.)
- I-R10: build:54 vs signoff:81 — assumptions may carry the per-user label
  (signoff already honors it); the edit site is build Step 5. (C review;
  citation corrected by the audit pass.)
- I-R11: build:31 — preflight names /recheck as the clearing station.
  (C review residual.)
Acceptance criteria:
- AC1: each cited punch line's scenario no longer holds — verify: read each
  edited passage against the recorded scenario.
- AC2: I-R3's placement rule byte-identical at all three sites — verify: grep.
- AC3: build ≤ 115, signoff ≤ 150, recheck ≤ 120 — verify: wc.
Footprint: build/SKILL.md; signoff/SKILL.md and recheck/SKILL.md (I-R3 only).
Not in this slice: the parked trio.
Depends on: Slice H
Status: signed off

## Slice J — blueprint summaries, recheck output, spec bookkeeping
Goal: close the remaining blueprint and recheck MINORs and square the spec's
own bookkeeping.
Requirements:
- J-R1: blueprint:64 — the appender sentence rewritten: names all three of
  build's sanctioned line types, drops the block/line exclusivity, scopes
  "only" inside the punch list. (Three F-review lines, one rewrite.)
- J-R2: blueprint:36 — the key-off sentence rewritten: keep-exact broadened to
  the load-bearing labels and formats (Status:, block headings, ·-separated
  fields); the writes named accurately (recheck edits the Status line in
  place; the sweep also writes recheck-headed blocks). (Two F-review lines.)
- J-R3: recheck:73 — the chat output finding line gains the claim field.
  (E review; matches Slice E's Discovered entry.)
- J-R4: recheck:36,61,67 — the bulk-output redirect example and bottom-line
  length aligned with the siblings, and the read-only rule gains signoff's
  bookkeeping-not-repair carve-out for the run's own doc writes. (A review
  residual, all three sub-claims.)
- J-R5: spec bookkeeping, dated amendments only — the doc-level Out of scope
  supersession note extended to name every blueprint-editing slice (F, J); a
  dated correction on the "(a) two sentences" undercount. (F review.)
Acceptance criteria:
- AC1: each cited punch line's scenario no longer holds — verify: read.
- AC2: the supersession note names every blueprint-editing slice — verify: read.
- AC3: blueprint ≤ 115, recheck ≤ 120 — verify: wc.
Footprint: blueprint/SKILL.md; recheck/SKILL.md; the build-plan doc's spec
prose (dated amendments only).
Not in this slice: the parked trio.
Depends on: Slice I
Status: signed off

## Slice K — field feedback: mutation isolation + skill-note channel
Goal: close the apple-mcp field run's mutation-contamination misreading vector
and give every skill a marked, event-triggered channel for skill feedback.
Requirements:
- K-R1: signoff:86 (rule 9) — the example list names the shared source
  checkout / working tree as mutable shared state. (Trace: apple-mcp field run
  2026-08-02, lesson 1 — an orchestrator wrote a mutation-testing lens prompt
  sanctioning source mutation in the shared checkout and contaminated three of
  five reviewers; rule 9's all-external examples — databases, dev/prod
  services, destructive commands — anchored "real state" to other systems, so
  the working tree read as exempt. The rule's remedy clause already named
  isolated worktrees; the example list was the vector.)
- K-R2: signoff Step 3 Mechanics — a lens whose method requires mutating the
  checkout runs in an isolated worktree (the Agent tool's `isolation:
  "worktree"`), stated as a mechanical default. Scoped to mutation-requiring
  lenses, not to a named lens — the offending lens in the field run was a
  custom one. (Same trace.)
- K-R3: all four skills' report/output steps — one identical event-triggered
  sentence: when executing the skill required working around, reinterpreting,
  or excepting one of its rules, the report carries one line marked
  `SKILL NOTE:` saying what and why, addressed to the skill's author, not the
  project. No always-on prompt; a clean run emits nothing. Explicitly
  removable later per user (2026-08-02: "if it gets too much we can remove
  the feedback line later"). (Trace: this session's discussion, accepted with
  that caveat.)
Acceptance criteria:
- AC1: the recorded contamination scenario's misreading vector is gone —
  rule 9's examples include the checkout — verify: read rule 9.
- AC2: the worktree default is stated at the lens-launch site and scoped to
  mutation-requiring lenses — verify: read Step 3 Mechanics.
- AC3: `SKILL NOTE` appears exactly once per file in all four skills, sentence
  identical — verify: grep -c per file + compare the four sentences.
- AC4: signoff ≤ 150, build ≤ 115, recheck ≤ 120, blueprint ≤ 115 — verify: wc.
Footprint: signoff/SKILL.md (all three); build/SKILL.md, recheck/SKILL.md,
blueprint/SKILL.md (K-R3 only).
Not in this slice: an always-on "any feedback?" prompt (rejected 2026-08-02 —
prompted-opinion noise and an attention tax on every run); reviewer-subagent-
level notes (the orchestrator's report carries the note); the field handoff's
lesson 2 (project feedback about apple-mcp's own gate scripts, per user); the
parked trio.
Depends on: Slice J (ordering only — J's requirements cite blueprint and
recheck line numbers that K's appended lines could shift; no semantic
dependency, and the user may reorder)
Status: signed off

## Slice L — ledger home rule + SKILL NOTE template slot
Goal: make the punch-list blocks' landing spot deterministic in docs whose
existing conventions diverge from the skill wording, and pin the SKILL NOTE
line's place in every report template.
Requirements:
- L-R1: the block-append commands in signoff (review block, sweep block) and
  recheck (recheck block), and the `WAIVED`/`REOPENED`/`REBUILT` record-append
  commands in all three stations, state a home rule: the home is where the
  doc's punch-list blocks already live, or the `## Punch list` section when
  none exist yet; when blocks sit in more than one place, the latest-dated
  block's location is the home (on a date tie, the later in the file) — one
  home per doc, never split — and every append lands at the home's tail, so
  file order stays time order. (Amended 2026-08-02 per the L review's three
  sentence MAJORs — per user: a positive definition replaces the "that home"
  pronoun, "punch-list blocks" replaces the ledger-scoped term, and the
  split-doc selection procedure is added.) (Trace: apple-mcp field run 2026-08-02, slice 5a.13, SKILL NOTE
  verbatim: "the doc's review blocks live at end-of-file rather than inside
  its ## Punch list section (line 2426) — I followed the existing convention
  set by 5a.17 so file order stays time order, rather than inserting mid-file
  as the skill's wording implies." Also this doc's own 2026-08-02 history:
  four misplaced-append incidents, and the K-review placement MINORs. The
  convention-wins direction is an assumption argued from the loop's own
  same-date tiebreak law: forcing the section home in a diverged doc splits
  the record between two homes and breaks "later in the file wins.")
- L-R2: the placement/tiebreak sentence byte-identical at build:31,
  signoff:129, recheck:24, recheck:51 is amended to name the home rule's home
  rather than only the `## Punch list` section, and remains byte-identical at
  all four sites after the amendment.
- L-R3: each of the four skills' fenced output templates gains a SKILL NOTE
  slot as the template's final line, identical across the four templates,
  marked as emitted only when the note fires (omitted on a clean run); the
  four prose SKILL NOTE sentences stay byte-identical and unedited. Per-file
  `SKILL NOTE` count intentionally moves from 1 to 2 (prose sentence +
  template slot) — this supersedes Slice K's AC3 count expectation, not its
  identity requirement. (Trace: the field note landed after `Next:`, this
  project's K sign-off placed its note after the verdict body — drift the
  K review recorded as the no-template-slot MINOR, same species as E-R10.)
Acceptance criteria:
- AC1: the home rule is stated at every block-append and record-append
  command site — verify: read signoff's Output ledger paragraph and Step 1
  sweep paragraph, recheck Step 4, build Steps 2 and 5; grep the home-rule
  phrase and count sites.
- AC2: the amended placement sentence extracts byte-identical at its four
  sites — verify: bounded grep -o + sort -u = 1.
- AC3: every fenced output template ends with the identical SKILL NOTE slot
  line; `grep -c "SKILL NOTE"` = 2 per file; the prose sentence's four copies
  still extract identical — verify: grep + sha per file.
- AC4: signoff ≤ 150, build ≤ 115, recheck ≤ 120, blueprint ≤ 115 — verify:
  wc -l.
Footprint: signoff/SKILL.md, build/SKILL.md, recheck/SKILL.md (home rule +
amended shared sentence + template slot); blueprint/SKILL.md (template slot;
plus its Step 4 appender summary only if the builder finds it names a home
the rule changes).
Not in this slice: re-homing this doc's stray C/E discovered entries or the
field doc's end-of-file blocks (existing records stand; the rule governs
future appends); the two open K MAJORs at signoff:60/86 (next fix pass, not
slice work); the open signoff:34 "uncleared" ambiguity (home still
undecided).
Depends on: Slice K (ordering and preflight only — K stands `signed off with
conditions`, so build's own gate requires its open MAJORs fixed or waived
before L frames)
Status: signed off

## Slice M — signoff record semantics: write order, "uncleared", the sweep pointer
Goal: close the three signoff record-machinery defects the L review surfaced
or re-surfaced — the unordered mid-review waiver write, the "uncleared"
ambiguity that can mint an unearned signature on a rebuilt card, and the
sweep site's undefined home reference.
Requirements:
- M-R1: signoff's Output ledger paragraph orders the mid-review waiver write
  the way recheck Step 4 orders its own — the dated `WAIVED (per user)` line
  is written after the run's punch-list writes (the review block and, when
  the sweep wrote one, its recheck-format block), so the user's word lands
  later in the file and wins the same-date tiebreak over any same-item line
  in those blocks. (Trace: L review, pre-existing MAJOR at signoff:130,
  recorded not-gating / next-slice candidate; recheck:51's I-era write-order
  command is the model — "the `WAIVED` line is written after this run's
  punch-list block".)
- M-R2: signoff:34 defines the sweep trigger's "uncleared" and guards the
  stale-card update: an entry is uncleared when its latest-dated record
  leaves it neither fixed nor waived (so waiver-closed entries do not put a
  `built` card in the sweep's scope), and the stale-card update never
  assigns a verdict state to a `built` card — a stale rebuilt `built` card
  keeps `built`, and rebuilt code earns its verdict only from a fresh
  /signoff. (Trace: the I review's open MAJOR keyed signoff:34 — "uncleared"
  is ambiguous under an all-waived rebuilt `built` card; on the
  waived-is-not-cleared reading the card enters the sweep, its entries are
  all excluded as waived, the stale-card update runs the Severity → verdict
  mapping with nothing open, and `signed off` is minted for rebuilt code no
  review ever saw. The G-era clearance carve-out already pins stays-built
  for sweep-verified clearance; M extends the same carve-out to the stale
  path. Semantics chosen here are the blueprint's recommendation — flagged
  in the readback for user correction.)
- M-R3: signoff:34's "at the ledger's home's tail" gains a pointer to the
  defining sentence in the Output section, the way build Step 5 carries
  "(Step 2's placement sentence defines the home)". (Trace: L review MINOR,
  three-lens convergence — the sweep site references the home 96 lines
  before its definition with no pointer; the user routed the open pointer
  question into this slice by invoking it.)
Acceptance criteria:
- AC1: the waiver-write order is explicit in signoff's Output ledger
  paragraph and agrees with recheck's Step 4 order — verify: read both
  sites; block-then-waiver stated at both stations.
- AC2: "uncleared" carries a definition at the signoff:34 trigger site and
  the stale-card update's text excludes `built` cards from verdict
  assignment — verify: read signoff:34, then walk the all-waived rebuilt
  `built` card on paper and confirm no path reaches `signed off` without a
  fresh /signoff.
- AC3: the sweep site's home reference carries its pointer — verify: read
  signoff:34.
- AC4: signoff ≤ 150; build, recheck, blueprint byte-unchanged — verify:
  wc -l (expect 108/91/107 untouched) plus the shared-sentence and SKILL
  NOTE identity greps still passing.
Footprint: signoff/SKILL.md only (the Step 1 sweep paragraph and the Output
ledger paragraph).
Not in this slice: the stranded-entries visibility gap (open BLOCKER/MAJOR
entries behind `signed off` cards are invisible to the sweep's card-state
trigger and to recheck's slice resolution — recorded on the ledger, needs
its own design decision); record-closing the E-review sweep-durability
entry (station work on the ledger, not skill text); the remaining L-review
MINORs; the parked trio.
Depends on: Slice L (M-R1 and M-R3 edit text L wrote or amended)
Status: signed off

## Slice N — the stranded-entry door
Goal: give the loop one sanctioned, user-driven path to open BLOCKER/MAJOR
entries that sit behind `signed off` cards, where the sweep's card-state
trigger and recheck's unnamed slice resolution cannot see them.
Requirements:
- N-R1: recheck Step 1's naming door generalizes — the user naming any
  still-open entry (by its review block's slice or its `file:line` + claim)
  adds it to the checklist regardless of the entry's card state, and one run
  may take named entries from more than one slice's blocks; the existing
  reopen door (cleared or waived items) is unchanged. (Trace: the ledger's
  recorded visibility gap — three open MAJORs stand behind `signed off`
  cards as of 2026-08-02: the E-review sweep-durability entry keyed
  signoff:34,127 whose substance Slice G built, the I-review "uncleared"
  entry keyed signoff:34 whose substance Slice M built, and the L-review
  write-order entry keyed signoff:130 whose substance M-R1 built. All are
  substance-fixed and need only verification to close; the user's word is
  the trigger, matching the loop's waiver ethos. Rejected alternative,
  recorded: widening the SWEEP to scan all open entries regardless of card
  state — an automatic full-ledger walk on every review, a standing cost for
  a rare state, and the user said to close out, not grow machinery.)
Acceptance criteria:
- AC1: the clause is present in recheck Step 1 and covers both doors
  (reopen for cleared/waived, surface for stranded-open), multi-slice in one
  run — verify: read Step 1; paper-walk one run naming the three 2026-08-02
  stranded entries and confirm a three-item checklist assembles with every
  card at `signed off`.
- AC2: recheck ≤ 120; signoff, build, blueprint byte-unchanged — verify:
  wc -l (expect 143/108/107 untouched) plus the placement-sentence and
  SKILL NOTE identity greps.
Footprint: recheck/SKILL.md only (Step 1). (Amended 2026-08-02, per user:
widened to Step 4's Status mapping — the review's recheck:51 MAJOR named the
out-of-footprint constraint in its verdict and the user's "Fix pass go"
sanctioned the fix; Step 1's resolve and early-end sentences were always in
footprint.)
Not in this slice: any automatic stranded-entry scan in signoff's sweep
(rejected above, reason recorded); Status/card changes for slices whose
entries clear this way (the card already reads `signed off`; clearing the
entries needs no flip); the cleanup run itself (station work after N ships).
Depends on: Slice M (ordering only — M's edits settled the record semantics
these entries are verified under)
Status: signed off

## Slice O — the living feedback document
Goal: one standing document where field feedback on the four skills lands,
so any session receiving the user's collected notes knows exactly where to
put them and what happens to them next.
Requirements:
- O-R1: create `~/Documents/skill-lab/skill-feedback.md` with: a header
  stating the flow (SKILL NOTE lines and field observations from any thread
  are appended verbatim to the Inbox; triage turns notes into /blueprint
  slices on this doc's plan — the Slice K path; dispositions are recorded,
  additive-only, so a note is never re-triaged); an `## Inbox` section
  (append-only: date · thread/project · skill · the note verbatim); and a
  `## Dispositions` section (dated lines: note → what became of it). (Trace:
  user 2026-08-02: "create some sort of a living feedback document. That
  way, when I start gathering feedback from using this, I can give you the
  notes and you know exactly where to put it.")
- O-R2: the doc is seeded with the two field notes already received, as
  worked examples of the format: the apple-mcp rule-9 mutation-contamination
  lesson (disposition: became Slice K, shipped 2026-08-02) and the apple-mcp
  end-of-file punch-list convention SKILL NOTE (disposition: became Slice L,
  shipped 2026-08-02). (Trace: both notes quoted verbatim in this doc's
  Slice K and Slice L requirement traces.)
Acceptance criteria:
- AC1: the file exists with the three parts (flow header, `## Inbox`,
  `## Dispositions`) and both seed notes carry verbatim text plus a
  disposition line — verify: read the file; grep the two section headings
  and the two slice names.
- AC2: no skill file changes — verify: wc -l all four unchanged
  (143/108/91-or-post-N/107) and the identity greps pass.
Footprint: `~/Documents/skill-lab/skill-feedback.md` (new file) only.
Not in this slice: any reference to the feedback doc inside the four skills
(K-R3's design deliberately keeps the skills decoupled from the compilation
target — the SKILL NOTE line names the author, not a file; rejected to avoid
coupling every run to a doc path); auto-triage machinery.
Depends on: nothing (Slice N ordering preferred so the loop closes first)
Status: signed off

## Build assumptions
### 2026-08-02 — Slice A (/recheck)
- Named MINORs are recorded in the recheck block but never move the Status flip — extends the spec's "MINORs never gate" to the flip mapping, which only enumerates BLOCKER/MAJOR cases.
- Reviewer agent type is `general-purpose` — the spec says "one fresh subagent"; it must be able to execute failure scenarios, and read-only agents can't (same reasoning /signoff states).
- When the punch-list record is too thin to identify open items (no severity labels or scenarios), recheck asks the user which items to verify — spec is silent on pre-format legacy punch lists.
- Slice resolution when none is named: the most recent slice whose Status is `signed off with conditions` or `rejected`.
### 2026-08-02 — Slice D (record integrity)
- The waiver-writer rule ("appended by whichever station received the user's word") is stated once, in build's preflight bullet, worded generically — not repeated in signoff/recheck, whose texts carry the closed-treatment AC1 names. Budget discipline; flagged in case the inspector wants it mirrored.
- The waiver-append instruction folded into the existing prior-slice bullet rather than a new bullet — placement choice, reversible.
### 2026-08-02 — Slice B (signoff tie-backs)
- Sweep placed at the end of Step 1 (scope establishment is where prior standing is read); status mapping referenced to /recheck's rather than duplicated — single source of truth.
- LIGHT placed after DEEP in Step 3; output template's Depth line gains LIGHT and a conditional "Prior conditions:" line.
- R8's /recheck pointer placed after the three verdict definitions; the opener stays at the three-station loop line per R7 — /recheck is named where R8 requires, not in the opener (no spec line authorizes that).
### 2026-08-02 — Slice E (MINOR cleanup)
- No git repo and no test suite (continuing the A–D convention): the before
  photo is `wc -l` on the three files plus the AC greps, rerun after — before:
  build 105 · signoff 138 · recheck 88; after: 105 · 140 · 88 (the +2 is
  E-R10's template slots).
- E-R5's join-key statement is placed inside each site's existing latest-dated
  parenthetical rather than as a new sentence, to preserve the Slice D fix
  pass's sentence-density resolution (punch line: signoff sweep density,
  reconciled resolved).

### 2026-08-02 — Slice F (loop-shape wording)
- Answer (a) obtained before the contract (the spec's own open question, asked
  and answered in-session); F-R4 therefore unfired — build and recheck
  untouched, per the spec's "under (a) they stand."
- Before photo per the A–E convention: wc signoff 140 · blueprint 104,
  "last station" ×1; after: 140 · 104, ×0 — in-place single-line edits only.
- F-R1 replacement wording ("the inspection station of the loop ... /recheck is
  this station's follow-up visit") is builder-chosen phrasing of the spec's
  named content — local, reversible, logged.

### 2026-08-02 — Slice G (sweep durability)
- Before photo per the A–F convention: wc signoff 140 · recheck 88; greps
  "flip or entry-clearing block" ×1, "broke:" ×0, "recheck-format block" ×1.
  After: signoff 140 (two in-place single-line edits at 34 and 127); greps
  ×0 / ×1 / ×2 as intended.
- G-R2's defect line reuses recheck:53's broke-line shape plus a fifth
  ·-separated attribution field styled like the review line's "which slice's
  review found it" — not a new shape. AC2's format compatibility governed;
  all five G-R2 fields (severity, file:line, claim, scenario, attribution)
  are present, and the appended field leaves the claim field's position
  untouched.
- The block write is scoped "whenever the sweep verified at least one item":
  no block on clean cards, waiver-closed stale cards, or record gaps —
  nothing was verified there, so there is nothing to record. Spec was silent;
  local and reversible.

### 2026-08-02 — Slice H (signoff wording debts)
- Before photo per convention: wc signoff 140 · recheck 88; after: 140 · 88 —
  fourteen requirements, nine in-place edits, no line-count change. Old-phrase
  greps ("follow-up visit", "its mapping commands", "in the clause when code
  moved") all ×1-or-more → ×0 in both files.
- The spec's five builder-decides items, decided: H-R5 points at the Severity →
  verdict section by name rather than inlining the mapping (preserves the
  Slice D density resolution); H-R7 bounds "genuinely small" as one concern, a
  few files, ~a hundred changed lines or fewer; H-R8 fuses the added lens into
  LIGHT's single reviewer (coverage equivalent per the recorded line; keeps
  LIGHT = one reviewer definitional); H-R11 fills the format's mandatory
  fields from the unmet criterion (scenario) and the deviation's ledger entry
  or named code site (file:line); H-R14 states the per-user trust as rule 10's
  one sanctioned exception, leaning on build Step 5's pinned definition.
- H-R12's clause wording matched in substance, not byte-identically, across
  signoff:34 and recheck:53 — the sentences sit in different grammatical
  frames; the join-protecting content ("never inside the claim field") is
  identical in both.

### 2026-08-02 — Slice I (build mechanics)
- Before photo per convention: wc build 105 · signoff 140 · recheck 88; after:
  unchanged — eleven requirements, ten in-place edit sites, no new lines. AC2
  grep: the I-R3 sentence byte-identical at build:31, signoff:127, and both
  recheck sites (24 and 51).
- I-R3's builder calls: placement = the end of the `## Punch list` section,
  outside any block; tiebreak = later-in-file wins. Grounds: appends only land
  at the end, so file order is time order — matches the live ledger's own
  precedent (the two same-day Slice E recheck blocks resolved by position) and
  makes a same-day REOPENED beat the clearing line it revokes, preserving the
  only-the-user's-word guarantee the H review flagged as the tie's worst
  direction.
- I-R5's format: `REBUILT · <YYYY-MM-DD> · <slice> — open findings need
  re-verifying against the new code`, placed by the same end-of-section rule.
- I-R1 mirrors recheck:24's record-trio parenthetical verbatim, including
  "dated" — build:31 now matches the sibling it cites; signoff:34's copy
  retains its recorded drift (H-review MINOR, not in this slice's scope).
- I-R11's wording adds the waive-vs-fix distinction ("the user's word waives;
  it doesn't fix") — the recorded scenario's unearned trust was specifically
  the user's word standing in for verification.

### 2026-08-02 — Slice J (blueprint summaries, recheck output, spec bookkeeping)
- Before photo per convention: wc blueprint 104 · recheck 88; after: unchanged —
  five requirements, six in-place skill edits plus two dated spec amendments.
  Old-phrase greps ("status and clearing records", "user-granted waivers,
  rebuild notes", "1-2 sentences") all → ×0.
- J-R3's chat claim field is parenthesized, matching recheck:53's doc-line
  convention — the same shape at both surfaces so co-located findings stay
  distinguishable in chat exactly as on the ledger.
- J-R4's redirect example copies the siblings' text verbatim
  (`> /tmp/run.log 2>&1`, then grep); the bottom-line length aligned upward to
  the siblings' 2-3 (alignment direction the requirement left to the builder).
- J-R5's amendments are additive dated parentheticals — the superseded 2026-08-02
  note and the F open-question prose stand unedited above them; queued Slice K
  is named in the supersession note because K-R3's blueprint edit is already
  recorded spec.

### 2026-08-02 — Slice K (field feedback: mutation isolation + skill-note channel)
- Before photo per convention: wc signoff 140 · build 105 · recheck 88 ·
  blueprint 104; `SKILL NOTE` grep ×0 in all four. After: 142 · 107 · 90 · 106;
  grep ×1 per file, the four sentences sha-identical.
- K-R3 placement inside each report/output step was the builder's altitude (the
  spec pins the step, not the line): the sentence lands as standalone prose in
  each skill's `## Output` section beside the report-format instructions —
  signoff:127, build:94, recheck:80, blueprint:96.
- The sentence transcribes K-R3's semantics ("working around, reinterpreting,
  or excepting", the `SKILL NOTE:` marker, author-not-project addressee,
  clean-run silence); "the report" is the generic term covering all four
  output blocks.
- K-R1 leads rule 9's example list with the checkout ("and the shared source
  checkout is shared state: no edits to the working tree under review") — the
  misreading vector was the all-external list, so the internal example goes
  first; the rule's existing worktree remedy clause stands unedited.
- K-R2 scopes by method, not name ("a lens whose method requires mutating the
  checkout — any lens, named or custom"), per the requirement's scoping.
- K's signoff Output insert shifted the I-R3 placement/tiebreak sentence from
  signoff:127 to signoff:129 — prior ledger and handoff citations of
  signoff:127 now point two lines high; byte-identity across the four sites
  (build:31, signoff:129, recheck:24, recheck:51) re-verified after the shift.

### 2026-08-02 — Slice L (ledger home rule + SKILL NOTE template slot)
- Before photo per convention: wc signoff 142 · build 107 · recheck 90 ·
  blueprint 106; "ledger's home" grep ×0 everywhere; `SKILL NOTE` ×1 per
  file. After: 143 · 108 · 91 · 107 (+1 per file, the slot line); `SKILL
  NOTE` ×2 per file (prose sentence sha unchanged, slot line one sha ×4);
  old placement sentence ×0 everywhere, amended sentence one form ×4.
- L-R1 design: the home is defined once, inside the amended shared placement
  sentence, so the definition travels to all three station files with the
  sentence; secondary command sites carry short "ledger's home" references —
  signoff:34 (sweep write), signoff:130 (ledger paragraph), recheck:53
  (block append), build:56 (REBUILT). Site count by grep: 7 (build:31,
  build:56, recheck:24, recheck:51, recheck:53, signoff:34, signoff:130).
- L-R1's conditional blueprint footprint item not triggered — blueprint:64
  describes who appends each ledger line, not where blocks land, so the home
  rule changes nothing there · builder call.
- L-R3 slot line wording: "SKILL NOTE: <only when a rule was worked around,
  reinterpreted, or excepted — what and why; omit otherwise>", placed as the
  final line inside each fence, byte-identical ×4.
- Line shifts from the slot inserts, enumerated in full: signoff +1 at 123
  (prose sentence 127→128, ledger paragraph with the shared sentence
  129→130 — L-R2's cited signoff:129 now resolves to signoff:130); build +1
  at 91 (prose 94→95); recheck +1 at 77 (prose 80→81); blueprint +1 at 95
  (prose 96→97). Sites cited above are post-shift.

### 2026-08-02 — Slice M (signoff record semantics: write order, "uncleared", the sweep pointer)
- Before photo per convention: wc 143/108/91/107, placement sentence one
  form ×4, `SKILL NOTE` two unique lines across the four files. After:
  identical on every count — all four edits extended existing signoff lines;
  build, recheck, blueprint byte-untouched per AC4's identity greps.
- Four in-place signoff edits: the sweep trigger's uncleared definition and
  the built-card stale-path guard (both in the line 34 paragraph), the
  sweep-site home pointer (same paragraph), and the waiver-write order
  (line 130 paragraph). recheck:51's order sentence was the model; signoff's
  copy names both block types (review block and sweep block) because signoff
  writes two where recheck writes one.
- AC2's paper walk, recorded: an all-waived rebuilt `built` card never
  enters the sweep (the trigger definition excludes it), the stale update
  therefore never sees it, and the explicit guard bars a verdict even for a
  mixed card that clears mid-sweep — no path to `signed off` without a
  fresh /signoff.
- The blueprint flagged M-R2's semantics as its recommendation and invited
  correction; the user proceeded to /build without correcting, so the spec
  stands as built — built as specced, no per-user label claimed.

### 2026-08-02 — Slice N (the stranded-entry door)
- "a run may assemble entirely from named entries" is in the clause though
  N-R1 doesn't say it verbatim — AC1's paper-walk requires it (three entries
  named, no slice named, every card `signed off`, so the default resolve
  hunt yields nothing); without it the named-entry run has no sanctioned
  scope · builder call
- The surface branch writes nothing to the record — a still-open entry is
  already open, so naming it "widens this run's scope, never the record";
  the REOPENED append stays exclusive to the cleared/waived branch, per
  N-R1's "existing reopen door unchanged" · builder call
- Step 1's early-end sentence ("Only a card already clear ... ends the run
  early") read as a permission governing the default flow, not a command
  that kills a named-entry run — the door's explicit add is the specific
  over that general; left untouched (footprint discipline) · builder call
- No repo: before photo = wc -l + md5 + identity greps (143/108/91/107;
  placement sentence ×4, SKILL NOTE prose ×4, slot line ×4), all matched
  the record before the edit · standing environment, as prior slices

### 2026-08-03 — Slice O (the living feedback document)
- The Inbox `skill` field for both seed notes attributed to signoff — the
  mutation lesson concerns signoff's review mechanics and the end-of-file
  note came from a signoff run's ledger write; the spec's format names the
  field but not these values · builder call
- The K lesson is marked "(pre-channel, via field handoff)" in its Inbox
  line — it predates the SKILL NOTE channel K itself built, and an honest
  worked example shows both arrival paths O-R1's flow header names · builder
  call
- The L disposition line records the template-slot drift caveat as folded
  in, matching the L slice's actual shipped content (L-R3), not just the
  original note · builder call
- User declined a capture-command/server extension pre-build (2026-08-03:
  "dotn change the build") — the slice ships exactly as blueprinted · per
  user

## Deviations
### 2026-08-02 — Slice A fix pass (per user: "fix the blockers and majors")
- Spec amended in place per the sign-off's spec-attributed MAJORs — per user: A-R2,
  R3, R4, R6, R7 rewritten + R9 added (broke-as-new-item with assigned severity,
  general status mapping with demotion, fully specified block format and join key,
  hunt/resolution path, scenario recovery, re-open door, record-gap conduct);
  AC2/AC3 aligned; B-R1 gains the failure-scenario field; B-R2 gains REJECTED
  MAJORs.
- Named MINORs ruled non-gating — builder call on the specific resolution (the
  sign-off's open question; grounds: /signoff's own severity table signs with
  MINORs on the punch list). Flagged for user overrule.
### 2026-08-02 — Slice B fix pass (per user: "fix the blockers and majors including
the B-R3 spec amendments")
- Spec amended per the sign-off's spec-attributed findings — per user: B-R3
  rewritten (latest-dated clearing, reviewer verification, record-gap guard,
  full-clearance-only flip recorded as a shared recheck-format block,
  fix-introduced defects block the flip); B-R1 gains the review-block header
  template and the chat-verdict claim field; B-R5 gains the capped-deviation
  punch-list line; B-R6 gains LIGHT/DEEP precedence; AC3 updated to match.
- Sweep flip narrowed to full-clearance-only (no partial flips, no inline mapping
  copy) — builder call: kills the dead-arms divergence and the drift risk of a
  duplicated mapping; partial states report and route to /recheck instead.
### 2026-08-02 — Slice D fix pass (per user: "go with your rec" ×3)
- Waiver lifecycle completed per the sign-off's BLOCKERs/MAJORs — per user: dated
  WAIVED/REOPENED formats, append authorization in all three stations' own write
  rules, latest-dated-wins across all record types, filter applied to the merged
  doc∪chat set, waiving station updates the card (waived excluded), all-waived
  card is stale-not-gap; D-R1 and AC1 amended to match.
- Rebuild clearance leaves the card at `built`; verdict only from a fresh
  /signoff; "record inconsistency" label replaced with "a rebuild awaiting
  re-verification" — per user; D-R2 and AC2 amended to match.
- Blueprint's ownership sentence (already in R4's authorized set) now names
  recorded user waivers among the verdict-state setters — per user.
- Incidentally resolved while rewriting the same sentences (punch-list MINORs):
  the inconsistency mislabel, the dateless waiver line, the chat-branch bypass
  (was MAJOR), BLOCKER-waivability ("any named finding"), and the sweep
  sentence's density (broken into short sentences).
- Incidentally resolved while editing the same sentences (three punch-list
  MINORs): the REJECTED "as well" ambiguity, the doc-write count, and "MINORs
  never gate" restored to the sweep text.
### 2026-08-02 — Slice C fix pass (per user: "fix the 2 conditions now")
- Step 2 gains the Dependency standing bullet, making R3's "checked in preflight"
  promise true; C-R3 amended to match — per user.
- `per user` label redefined to require the answer sanctioned the specific change;
  C-R4 amended to match — per user.
### 2026-08-02 — Slice E fix pass (per user: "fix the majors and i sanction the er4 spec")
- Sweep clearing-line shape inlined in signoff's own sweep sentence (severity ·
  `file:line` · (claim) · fixed | not fixed); "standard recheck-format block"
  stays as the name but no longer carries the format alone. E-R4 amended to
  match — per user.
- Claimless-record default stated byte-identically at the three join sites
  (build preflight, signoff sweep, recheck assembly): "A record with no claim
  field matches on `file:line` alone." Covers both legacy shapes — bare lines
  and tag-in-file:line lines alike have no ·-separated claim field. E-R5
  amended to match — per user (the ordered fix for the second MAJOR).
### 2026-08-02 — Slice E second fix pass (per user: "run the secon fix pass")
- Claimless-record default reworded byte-identically at the three join sites:
  scoped to single-entry locations (a shared file:line decides nothing; the
  ambiguity goes to the user) and the claim-field boundary defined (·-separated
  field; wrapping parentheses excluded; a parenthetical glued to the file:line
  is a legacy tag, not a claim). Settles the tag-parenthetical shape and the
  co-location over-clearing in one rule. E-R5 amended again to match — per user.
- The boundary's parentheses clause incidentally resolves the recorded Slice E
  MINOR on claim-wrapping drift (exact-form matchers); the punch line stands
  until a reconcile marks it — builder note, not a clearing.
- Signoff's inline clearing-line format gains recheck:53's original-location
  join-key clause (post-fix location noted in the clause when code moved),
  making E-R4's amended "same line shape" sentence true as written; no further
  spec change needed — per user.

### 2026-08-02 — Slice G fix pass (per user: "a, run the fix pass")
- Per user, option (a) on the G-review MAJOR: build:31's with-conditions gate
  widened from "the named MAJORs" to "the named BLOCKERs and MAJORs" — one
  in-place phrase edit; build:32's dependency-standing rule inherits it via
  "the same fixed-or-waived demand," so no second edit; build:33 and the
  card-untouched rule untouched. Edit lands outside G's Footprint (signoff
  only) — sanctioned by the user's (a). wc build 105 → 105.

### 2026-08-02 — Slice H fix pass (per user: "run the fix pass")
- Per user, the H-review MAJOR at signoff:32: the false "or ledger" clause
  replaced — the sentence now reads "there are no cards: correctness-only mode
  runs no sweep — its findings still land in `docs/punch-list.md` per the
  Output section." Beyond the deletion, the added pointer affirms line 127's
  existing append command rather than adding new machinery; "no cards" (true)
  still carries the no-sweep conclusion. wc signoff 140 → 140; grep "no cards
  or ledger" ×0, "punch-list.md" ×2 (lines 32 and 127, consistent).

### 2026-08-02 — Slice I fix pass (per user: "run the fix pass")
- Per user, the two I-review MAJORs. First: build:56's carve-out widened from
  "after a waiver" to "after a waiver grant or revocation" — the
  REOPENED-triggered demotion is now inside the verdict-shape exemption,
  matching signoff:127's grants-or-revokes symmetry. Second: the mid-run
  waiver inversion fixed at its source, recheck:51 — the carve-out now orders
  the writes ("the `WAIVED` line is written after this run's punch-list
  block"), so the user's word lands later in the file and wins the same-date
  tiebreak. The shared I-R3 sentence was left untouched at all four sites —
  byte-identity re-verified by grep (4/4) — because only recheck's paragraph
  order diverged from event order; signoff already writes block-then-waiver
  and build writes no blocks. Type-ranking user-word records over clearing
  lines was considered and rejected: it breaks the legitimate
  reopen-then-reverify-same-day sequence that position order resolves
  correctly. wc build 105 → 105, recheck 88 → 88.

### 2026-08-02 — Slice J fix pass (per user: "run the fix pass")
- Per user, the J-review MAJOR: a dated correction appended under the
  supersession amendment — F's blueprint edits are F-R2/F-R3 only, F-R1 edits
  signoff:10, the D/F/J/K roster stands. The wrong amendment line is left in
  place per the additive-only law; the correction supersedes it as the
  latest-dated statement. No skill file touched.
### 2026-08-02 — Slice C (build tie-backs)
- Build's preflight has no stop-on-rejected-prior-card rule — flagged as Deferred in Slice B's sign-off ("belongs in Slice C's scope, spec amendment flagged") but the amendment was never applied, so C's requirements don't authorize it. Logged, not built; needs the user's word plus a spec line (likely a fourth preflight bullet in build).
### 2026-08-02 — Slice E (MINOR cleanup)
- recheck's chat-output finding line (recheck:73) still carries no claim field,
  the same gap E-R4 closed for the doc's clearing lines — out of scope for
  Slice E (its footprint named the punch-list format only); logged, not built.

### 2026-08-02 — Slice K fix pass (per user: "run the fix pass")
- Per user, the two K-review MAJORs, both fixed in place with no spec
  amendment — neither fix alters what K-R1/K-R2 command; each adds a
  supplementary clause. signoff:60 gains the dirty-state bridge ("A worktree
  checks out committed state only — when the review scope includes
  uncommitted work, carry it in (apply the working tree's diff inside the
  worktree) before the lens runs, or the verdict's Method line declares that
  the lens exercised committed state only."). signoff:86's ban gains the
  byproduct carve-out ("(a sanctioned run's own byproducts — snapshot
  updates, lockfile touches, caches — are not edits; the ban is on altering
  the code being reviewed)"). wc signoff 142 → 142; `SKILL NOTE` ×1 per file,
  sha-identical ×4 unchanged; placement-law sentence byte-identical 4/4
  unchanged. MINORs untouched per the loop's law.
- This entry is appended at the literal end of `## Deviations`, which now
  places it after the two stray Slice C/E discovered entries — file order is
  append order; the strays' placement is the Discovered-section gap K logged.

### 2026-08-02 — Slice K fix pass 2 (per user: "run the fix pasds" [sic])
- Per user, the two recheck-found fix-introduced MAJORs, both fixed in place.
  signoff:86's carve-out gains its priority rule on one mechanically checkable
  axis, replacing the two colliding classifications: "a sanctioned run's
  gitignored byproducts — caches, build artifacts — are not edits; a run that
  would write unignored content, snapshot files and lockfiles included, is a
  mutation and runs where mutations run" — the contaminating run is no longer
  blessed or refused; it routes to the worktree path. signoff:60's carry-in
  now commands the whole scope: "carry all of it into the worktree before the
  lens runs (the tracked diff and the untracked files — a bare `git diff`
  drops the untracked half)" — the compliant-looking partial carry is a plain
  violation. wc signoff 142 → 142; `SKILL NOTE` ×1 per file, one sha;
  placement-law sentence one sha across its four sites.

### 2026-08-02 — Slice L fix pass (per user: "run the fix pass")
- Per user, the four gating L-review MAJORs. The three sentence defects fixed
  by one rewrite at all four sites (build:31, signoff:130, recheck:24,
  recheck:51), byte-identical after: the home is now defined positively
  ("where the doc's punch-list blocks already live, or the `## Punch list`
  section when none exist yet") killing the "that home" pronoun;
  "punch-list blocks" replaces the ledger-scoped term; and the split-doc
  selection procedure is added ("when blocks sit in more than one place the
  latest-dated block's location is the home (on a date tie, the later in the
  file)"). L-R1 amended in place to match — per user, spec-attributed MAJOR,
  dated amendment note in the requirement.
- Correction of the false record (J-precedent, the wrong line stays): the
  Slice L build-assumptions entry's final item misstates three of four slot
  positions — its build:91, recheck:77, blueprint:95 are the closing fences.
  The true slot lines are signoff:123, build:90, recheck:76, blueprint:94.
  The same wrong numbers appeared in the BUILD chat block and the L review
  briefs; this dated entry supersedes them all.
- Not touched, per the loop's law: the pre-existing write-order MAJOR
  (recorded not-gating, next-slice candidate), all ten L-review MINORs, and
  the open design question on signoff:34's pointer (user has not answered).
- wc unchanged 143/108/91/107; new sentence one form ×4; old form ×0;
  `SKILL NOTE` ×2 per file, two unique lines (prose + slot), both identical
  across files.

### 2026-08-02 — Slice M fix pass (per user: "fix the major")
- Per user, the one M-review MAJOR: the write-order command's "that line"
  (binding the WAIVED-or-REOPENED disjunction) narrowed to "the `WAIVED`
  line" at signoff:130, matching M-R1's spec text and recheck:51's model.
  REOPENED reverts to its pre-M state — unordered at the sentence level,
  governed by the general placement sentence — deliberately: commanding
  REOPENED-before-blocks would be another uncommanded extension beyond spec,
  the exact class this MAJOR was. wc signoff 143 → 143; "that line is
  written after" ×0; placement sentence one form ×4; `SKILL NOTE` two
  unique lines unchanged. MINORs untouched per the loop's law.

### 2026-08-02 — Slice N fix pass (per user: "Fix pass go")
- recheck:22 — the resolve paragraph gains the named-entry branch ("when the
  invocation names entries rather than a slice, the named set is the run's
  scope and no slice resolves") and the other-open-slices sentence is
  rescoped to "outside the run's scope → name them in the output, never
  absorb them" — the old "recheck the resolved one" had no referent in a
  named-entry run · per user (the review's recheck:22 MAJOR)
- recheck:28 — the early-end license now keys on the checklist, not the
  card: "Only an empty checklist ends a run early — and only against a card
  already clear (or no open items anywhere); a non-empty checklist runs,
  whatever the cards read" — preserves the record-gap ask for empty-against-
  open-card · per user (the review's recheck:28 MAJOR)
- recheck:51 — Step 4's mapping rescoped per slice: each slice with
  checklist items takes the mapping over its own remaining-open items,
  fix-introduced defects charged to the slice whose fix caused them, "a
  slice's card never moves on another slice's items", "Edit each `Status:`
  line the mapping commands". Out of N's original footprint; the spec's
  Footprint line amended in place, dated · per user (the verdict named the
  constraint, "Fix pass go" collapsed it)
- Correction (L-precedent; the wrong line stays): the Slice N
  build-assumptions line justifying the untouched early-end sentence as
  "(footprint discipline)" was false — recheck line 28 sits inside Step 1,
  inside the authorized footprint; the guard was buildable at build time
  and the fix pass has now built it
- After: wc recheck 91 (≤ 120); placement sentence ×4 (build:31,
  signoff:130, recheck:24, recheck:51); SKILL NOTE prose ×4, slot ×4;
  signoff/build/blueprint untouched. MINORs untouched per the loop's law.

### 2026-08-03 — Slice N fix pass 2 (per user: "fix the majors")
- recheck:51 — the per-slice mapping's input widened from checklist items
  to everything still open of the slice's own: "unfixed checklist items,
  fix-introduced defects (each charged to the slice whose fix caused it),
  and its record's still-open BLOCKER/MAJOR entries this run never
  verified, so a partially named slice can close its named items without
  its card ever being raised past the rest". A raise now requires the open
  set empty, which requires every open entry verified or waived this run —
  full coverage is structural, not policed; demotions only move a card
  toward what the record already holds open. Faces walked: Q `rejected`
  B1+M1 open, M1 named fixed → input {B1} → stays `rejected`, no false
  flip; the three previously-fixed faces re-walked unchanged · per user
  (the recheck's broke-item)
- Design decision inside the sanctioned fix, disclosed for the next
  reviewer: a `signed off` card holding two stranded MAJORs, one named and
  verified fixed, now maps over the unnamed open sibling → card demoted to
  `signed off with conditions` — record-driven demotion toward truth,
  un-stranding the sibling into every trigger; the spec's Not-in-this-slice
  carve-out ("whose entries clear this way ... needs no flip") is preserved
  exactly: when all entries clear, the mapping yields `signed off` and the
  card is already there, no write · builder call within the per-user
  footprint amendment
- Still-open MINOR entries never enter the mapping input (the widened set
  is BLOCKER/MAJOR only), keeping "MINORs, named or not, never move the
  Status" true · per the loop's law
- After: wc recheck 91 (≤ 120); placement sentence ×4 one unique string
  (extraction-diffed); signoff/build/blueprint md5-unchanged

## Discovered
### 2026-08-02 — Slice K (field feedback: mutation isolation + skill-note channel)
- The doc's `## Discovered` scaffold heading was absent (this block recreates
  it at its scaffold position); the Slice C and Slice E discovered entries —
  which the doc's own prose cites as "Discovered entry" — sit at the tail of
  `## Deviations`, immediately above this heading. Logged, not moved:
  re-homing history entries is the user's to order.

## Punch list
### 2026-08-02 — Slice A sign-off (REJECTED). Lines carry severity + a failure-scenario clause — a forward deviation from the current signoff format, in the already-approved Slice B direction, so this verdict's substance survives outside chat.
- BLOCKER · recheck/SKILL.md:34,42-43 · a `broke:` outcome carries no severity and never gates the Status flip — all originals fixed + one fix introduces a data-loss-grade defect → literal mapping reads "nothing open → signed off" over a recorded live defect, and the unlabeled line is invisible to the future sweep · Slice A review
- MAJOR · recheck/SKILL.md:22,26 · the record recheck reads never contains failure scenarios (today's or Slice B's punch-list format), yet Step 2 makes the scenario the test and forbids re-deriving — cross-session recheck either guesses (forbidden) or stalls; the ask-branch recovers item names but not severities or scenarios · Slice A review
- MAJOR · recheck/SKILL.md:20,22 · pre-Slice-B REJECTED path is a silent no-op — BLOCKERs live only in chat, punch list is empty/MINOR-only, so "nothing open, say so and stop" strands the card at `rejected` forever; post-B variant: MAJORs from a REJECTED verdict are still never appended (spec B-R2 gap) · Slice A review
- MAJOR · recheck/SKILL.md:40,72 · when the fix session invokes /recheck (the description's own primary trigger), Step 4's "adjudicate the results yourself" collides with "don't grade fixes this session wrote" — the fixer can overrule its reviewer's "not fixed" and make the unearned flip, or rubber-stamp; no rule says which wins · Slice A review
- MAJOR · recheck/SKILL.md:43 · the recheck block's on-disk format is under-specified for its downstream readers — no block-header template, no slice attribution, no latest-block-wins tiebreak for conflicting outcomes, no join-key rule (original vs post-fix file:line as lines drift), destination section never named, no create-if-missing — the future sweep misparses or misses clears · Slice A review
- MAJOR · recheck/SKILL.md:20,42 · no build-doc hunt path and circular slice resolution ("most recent" undefined; multiple docs/slices unhandled; correctness-only signoff leaves no doc and no Status line, making Step 4's writes untargetable) — wrong doc means the wrong slice's card gets flipped · Slice A review
- MAJOR · recheck/SKILL.md:42 vs spec R2/R6 · named-MINOR carve-out: skill flips `signed off` with a user-named MINOR verified not-fixed; spec's literal "all named items cleared" withholds the flip — builder-logged assumption, needs the user's ruling on whether named MINORs gate · Slice A review
- MAJOR · recheck/SKILL.md:20,47 · no path to re-open a cleared item even on explicit user order ("recheck :41 again, it regressed") — checklist definition excludes it, rule 1 forbids mid-run expansion, the only user door admits MINORs · Slice A review
- MINOR · recheck/SKILL.md:16 · model-floor wording family-watch: "Opus-class or better" is undecidable from a non-Opus frontier session, and "never pin below opus" describes a branch that can't occur (inherited from signoff by spec's order) · Slice A review
- MINOR · recheck/SKILL.md:40-43 · Fable early-stop watch: three terminal writes follow the interesting work; verdict-in-chat with no card flip breaks bookkeeping silently — baseline watch item, don't pre-fix · Slice A review
- MINOR · recheck/SKILL.md:32,52 · "executed where runnable" vs "read-only against real state" has no bridge clause ("fall back to static and declare it") — inherited tension from spec R5 · Slice A review
- MINOR · recheck/SKILL.md:58 · PARTIAL vs NOT CLEAR boundary undefined (0-of-3 fixed reads as either), and whether a broke item increments "n still open" is unstated · Slice A review
- MINOR · recheck/SKILL.md:20 · no dedup rule for doc-entries ∪ chat-verdict — same finding can enter the checklist twice · Slice A review
- MINOR · recheck/SKILL.md:20 · multiple open slices: skill resolves one and is silent that others remain open · Slice A review
- MINOR · recheck/SKILL.md:69-77 · register watch: don't-list restates body rules near-wholesale; family-wide trait the corpus's deletion test flags — evaluate at baseline across all four skills, not per-file · Slice A review
- MINOR · recheck/SKILL.md:36,61,67 · style drift: bulk-output line omits the redirect example siblings give; bottom-line length differs; read-only rule lacks signoff's "bookkeeping, not repair" carve-out for its own doc writes · Slice A review
- MINOR · blueprint/SKILL.md:64 · "/build sets `built`, /signoff sets the verdict" is falsified by recheck also flipping Status — blueprint's ownership line needs the third station named (spec's "blueprint needs no edits" is now wrong) · Slice A review
### 2026-08-02 — recheck: Slice A
- BLOCKER · recheck/SKILL.md:34,42-43 · fixed
- MAJOR · recheck/SKILL.md:22,26 · fixed
- MAJOR · recheck/SKILL.md:20,22 · fixed
- MAJOR · recheck/SKILL.md:40,72 · fixed
- MAJOR · recheck/SKILL.md:43 · fixed
- MAJOR · recheck/SKILL.md:20,42 · fixed
- MAJOR · recheck/SKILL.md:42 vs spec R2/R6 · fixed
- MAJOR · recheck/SKILL.md:20,47 · fixed
### 2026-08-02 — review: Slice B (signoff tie-backs)
- BLOCKER · signoff/SKILL.md:34 · the sweep has no record-gap guard · a prior slice stands `rejected` with an empty/legacy punch list (findings chat-only) → zero open entries reads as "comes fully clear" → the card flips to `signed off` with nothing verified; recheck got exactly this guard, the sweep did not · Slice B review
- MAJOR · signoff/SKILL.md:34 · sweep verification has no independence requirement · the sweep runs in Step 1 before reviewers exist, so the session that wrote the prior slice's fixes self-verifies them and flips the card — the unearned flip both files call unforgivable · Slice B review
- MAJOR · signoff/SKILL.md:34 · the inline flip mapping is a divergent copy of recheck's · it omits fix-introduced defects and demotion, and its non-signed-off arms are unreachable under the "fully clear" trigger — the same state processed by the two texts yields different cards; a recheck-demoted `rejected` card can flip to `signed off` over an open broke-BLOCKER · Slice B review
- MAJOR · signoff/SKILL.md:34,125 · sweep clears leave no durable record · the sweep flips a Status but appends no clearing block, so the doc permanently shows open entries behind a closed card — unverifiable from the doc alone, the exact state the loop exists to prevent · Slice B review
- MAJOR · signoff/SKILL.md:34 vs recheck/SKILL.md:24 · clearing semantics diverge: any-block-wins vs latest-dated-wins · an item cleared in block 1, re-opened, and recorded `not fixed` in block 2 counts as cleared to the sweep — it flips the card over a latest-dated live finding; spec B-R3's wording predates recheck's fix-pass semantics · Slice B review
- MAJOR · signoff/SKILL.md:81,125 · a builder-call cap can mint a WITH CONDITIONS card with zero recorded findings · the capping deviation gets no punch-list line and the user question lives only in chat → recheck stalls on a record gap or the sweep vacuously clears the card, dissolving the unanswered question · Slice B review
- MAJOR · signoff/SKILL.md:125 · signoff's own review block has no header template · "one dated entry block" with no format — a later recheck resolving an unnamed slice keys on block dates and slice attribution it can't parse; the working ledger's own headers modeled a verdict word the same paragraph forbids · Slice B review
- MAJOR · signoff/SKILL.md:116 · chat verdict finding lines carry no claim field · recheck dedupes doc entries ∪ chat findings on file:line + claim, so the key is uncomputable for chat items — duplicates enter the checklist or the session improvises · Slice B review
- MAJOR · signoff/SKILL.md:54,56 · LIGHT's user-invocation path and DEEP's content-mandated trigger have no precedence rule · "light signoff" on an auth-touching slice: one session honors LIGHT with no security lens, another escalates — divergent coverage on the highest-stakes content · Slice B review
- MINOR · signoff/SKILL.md:125 · REJECTED append clause lacks the "too" marker · one reading drops REJECTED-review MINORs from the accumulation ledger · Slice B review
- MINOR · signoff/SKILL.md:125 · "one more doc write" counts one Status write · a literal reader refuses the sweep's second, prior-slice flip as unauthorized · Slice B review
- MINOR · signoff/SKILL.md:34,112 · Prior-conditions arithmetic underdetermined · whether N counts recheck-cleared items and how multiple open slices aggregate varies by session · Slice B review
- MINOR · signoff/SKILL.md:101,107-121 · R8's /recheck pointer and rule 4's user questions have no output-template slots · a template-following session ships a WITH CONDITIONS verdict that names no next station and buries the question · Slice B review
- MINOR · signoff/SKILL.md:56 · "genuinely small" is undefined, so the LIGHT offer is the self-selection vector · offer-every-time + habitual acceptance drifts toward rubber stamp; bounded by explicit consent · Slice B review
- MINOR · signoff/SKILL.md:34 · sweep has no fallback for pre-format entries and no channel for defects found mid-sweep · legacy entries dead-end (no ask branch); a fix-introduced defect found by the sweep gates the wrong card; correctness-only mode has no sweep at all and neither file says so · Slice B review
- MINOR · signoff/SKILL.md:10 · "the last station of the loop" is false with /recheck live · two files now disagree about the loop's shape · Slice B review
- MINOR · signoff/SKILL.md:81 vs 87 · rule 4 trusts the "per user" label rule 10 calls a claim · a builder can launder a descope; spec-mandated trust, observation only · Slice B review
- MINOR · signoff/SKILL.md:56,58 · LIGHT plus an added lens contradicts "only the reviewer count shrinks" · under-specified, harmless · Slice B review
- MINOR · recheck/SKILL.md:53 · clearing lines omit the claim, so two findings at one file:line are indistinguishable · the sweep joins `fixed` to the wrong claim · Slice B review
- MINOR · signoff/SKILL.md:42 vs 87 · Step 2's ledger boundary and rule 10's closing sentence describe incompatible regimes · spec and ledger share one file, so "not the builder's ledger" is unsatisfiable by passing the spec path; the new paragraph resolves it in practice but rule 10's sentence was never amended · Slice B review
- MINOR · signoff/SKILL.md:34 · "MINORs never gate" dropped from the sweep text (spec says both) · implicit in the mapping; narrow textual loss · Slice B review
- MINOR · build-plan ## Build assumptions (Slice B entry) · the ledger claims the mapping was "referenced to /recheck's rather than duplicated" but the file duplicates it inline · the ledger misdescribes the build — drift risk if recheck's mapping changes · Slice B review
### 2026-08-02 — recheck: Slice B
- BLOCKER · signoff/SKILL.md:34 · fixed
- MAJOR · signoff/SKILL.md:34 (independence) · fixed
- MAJOR · signoff/SKILL.md:34 (mapping) · fixed
- MAJOR · signoff/SKILL.md:34,125 (durable record) · fixed
- MAJOR · signoff/SKILL.md:34 vs recheck:24 (latest-dated) · fixed
- MAJOR · signoff/SKILL.md:81,125 (capped-deviation record) · fixed
- MAJOR · signoff/SKILL.md:125 (header template) · fixed
- MAJOR · signoff/SKILL.md:116 (claim field) · fixed
- MAJOR · signoff/SKILL.md:54,56 (LIGHT/DEEP precedence) · fixed
### 2026-08-02 — review: Slice C
- MAJOR · build/SKILL.md:25 · "Depends on is checked in preflight" names a check Step 2 never defines · a slice with Depends on: B where B stands not started or rejected — the prior-slice bullet covers neither non-adjacent dependencies nor those states, so the slice gets framed on a missing foundation · Slice C review
- MAJOR · build/SKILL.md:54 · the per-user label attaches to the exchange, not the sanction · builder asks about one descope, user answers something adjacent, entry gets labeled per user → signoff rule 4 defers an unmet criterion the user never sanctioned · Slice C review
- MAJOR · build/SKILL.md:31 vs recheck:36/signoff:34 · pre-existing, not gating Slice C — "explicitly waived" has no record representation anywhere in the loop · a waived MAJOR stays open forever: every sweep re-flags it, recheck records not fixed, the card never clears without a dishonest entry · Slice C review (slice D candidate)
- MAJOR · build/SKILL.md:54 vs signoff:34/recheck:22 · pre-existing, not gating Slice C — a COMPLETE rebuild flips rejected → built, blinding the sweep and recheck's unnamed-slice resolution · open BLOCKER lines orphaned behind a clean-looking card · Slice C review (slice D candidate)
- MINOR · build/SKILL.md:25 · Reuse and New have no transcription source and the N:M requirements-to-criteria join is unstated · a session leaves New empty as nothing-to-transcribe, then hits the no-late-dependencies rule · Slice C review
- MINOR · build/SKILL.md:25 · "seeds" additive side implicit; blueprint's doc-level Out of scope never feeds Not authorized · an aggressive don't-re-derive reading omits shared-file/schema boundaries · Slice C review
- MINOR · build/SKILL.md:16 · hunt-path priority implied by sequence, never stated · a stale plan/ doc can win without triggering stop-and-ask · Slice C review
- MINOR · build/SKILL.md:84 · Deviations label placement is convention, not statement · a block-level parse corrupts the chat block only · Slice C review
- MINOR · build/SKILL.md:54 vs signoff:81 · assumptions cannot carry a per-user label · user-answered gap-fills read as builder call and re-ask the user downstream · Slice C review
- MINOR · build/SKILL.md:31 · preflight has no latest-dated-block tiebreak · an early fixed line beats a later not-fixed when joining findings to clearings · Slice C review
- MINOR · build/SKILL.md:31 · preflight accepts "fixed" on the user's word and never names /recheck · unearned trust the rest of the loop forbids · Slice C review
- MINOR · build/SKILL.md:31 · the caps "SIGNED OFF WITH CONDITIONS" string never appears in the artifact preflight reads (lowercase Status lines only, post-B) · a literal matcher finds nothing · Slice C review
- MINOR · blueprint/SKILL.md:8,36 · "both downstream skills consume" and the format-keys-off list predate recheck · stale consumer count; blueprint edits need a spec line · Slice C review
- MINOR · build/SKILL.md:8 · the spec-mandated three-station opener bakes the stale loop shape into newly written text · the family-wide loop-shape decision is still open · Slice C review
### 2026-08-02 — recheck: Slice C
- MAJOR · build/SKILL.md:25 (Depends-on preflight check) · fixed
- MAJOR · build/SKILL.md:54 (per-user label sanction) · fixed
- Note: the two "pre-existing, not gating Slice C" MAJOR lines above are excluded from this checklist per their own recorded text — Slice D R1/R2 are their sanctioned home.
### 2026-08-02 — review: Slice D
- BLOCKER · signoff/SKILL.md:125, recheck/SKILL.md:62 · the waiver-writer rule is unreachable and affirmatively forbidden in two of three stations · user waives a MAJOR mid-signoff or mid-recheck — the writer rule lives only in build's file (which those sessions never load) and both files' own write enumerations forbid the append, so the waiver evaporates as chat-only, which build:31 explicitly voids; disclosure in the ledger covered placement, not the prohibition · Slice D review
- BLOCKER · signoff/SKILL.md:34, recheck/SKILL.md:28 · an all-waived open card deadlocks with phantom record-gap reports · the most ordinary waiver flow (one open MAJOR, user waives it) leaves the card at with-conditions forever: no station flips on waivers, both record-gap guards misfire on open-card-plus-zero-open-entries, sweep bounces to recheck and recheck asks for findings visibly closed on the page; card-keyed preflight stops fire forever · Slice D review
- MAJOR · signoff/SKILL.md:34, recheck/SKILL.md:24 · waivers are irrevocable — closure is presence-based and dateless · a regretted waiver has no un-waive path: the line can't be removed (additive-only), the re-open door admits only "cleared" items, and even a later dated not-fixed block loses to the WAIVED line's presence; recheck holds the item open while sweep and preflight hold it closed, permanently · Slice D review
- MAJOR · recheck/SKILL.md:24 · the chat-verdict branch bypasses the waiver filter · the WAIVED exclusion grammatically attaches only to punch-list entries; a session holding the chat verdict but not the waiver (resumed or compacted) re-admits the waived item, grades it not fixed, and demotes a card the sweep holds clear · Slice D review
- MAJOR · signoff/SKILL.md:34, recheck/SKILL.md:22,36 · the rebuild flip mints an unearned signed off for code nobody reviewed · a rejected slice rebuilt COMPLETE has its old failure scenarios vacuously moot against rewritten code — every item reads "verified fixed," full clearance fires, and the card flips built → signed off with the new implementation never adversarially inspected; spec D-R2 itself never says what the card becomes, so this is partly a spec defect · Slice D review
- MINOR · signoff/SKILL.md:34 · the sweep labels the sanctioned rebuild state "a record inconsistency" · every legitimate rebuild triggers a false alarm about a record the loop itself wrote; the rebuild note has no reader to distinguish sanctioned from anomalous · Slice D review
- MINOR · build/SKILL.md:31 · the "dated" WAIVED line has no date slot, no header, and no placement rule · sessions serialize differently; if revocation ever needs sequencing, the dates aren't there · Slice D review
- MINOR · recheck/SKILL.md:24,53 · the waiver join key is unstated and collides with file:line-only clearing · one WAIVED line can close a co-located sibling finding · Slice D review
- MINOR · build/SKILL.md:56 · the rebuild note is formatless and write-only · no consumer parses it; divergence is cosmetic until something needs it · Slice D review
- MINOR · build/SKILL.md:101 · the don't-list still reads "Don't touch punch-list history" flat while Step 5 sanctions two punch-list appends · a don't-list-skimming session refuses the sanctioned writes · Slice D review
- MINOR · build/SKILL.md:31 · whether a BLOCKER is waivable at build's station is ambiguous — the append instruction is embedded in the named-MAJORs sentence while spec R1 says "a named finding" · Slice D review
- MINOR · build/SKILL.md:31-32 · a dependency standing signed off with conditions passes "built or better" without the fixed-or-waived demand (that demand is scoped to the prior-slice bullet) · framing proceeds on a foundation with open MAJORs; caught one station late · Slice D review
- MINOR · build/SKILL.md:32-33,56 · a rebuilt-over-rejected slice passes preflight silently — rejected becomes built, and neither the dependency nor failed-foundation bullet fires · spec-conformant (D-R2 assigned the guard downstream) but the stop-state launders · Slice D review
- MINOR · blueprint/SKILL.md:64 · the line's unedited first half ("/signoff appends the punch list") is now false three ways while its edited second half is correct · outside R4's three authorized sentences — needs a spec line · Slice D review
- MINOR · blueprint/SKILL.md:36 · the key-off list names recheck's writes, not its reads · summary prose, low harm · Slice D review
- MINOR · signoff/SKILL.md:34 · the sweep sentence now nests four dash-pairs deep with the swept-item definition separated from its antecedent · readability hazard in the loop's most load-bearing sentence · Slice D review
### 2026-08-02 — recheck: Slice D
- BLOCKER · signoff/SKILL.md:125, recheck/SKILL.md:62 (waiver writer) · fixed
- BLOCKER · signoff/SKILL.md:34, recheck/SKILL.md:28 (all-waived deadlock) · fixed
- MAJOR · signoff/SKILL.md:34, recheck/SKILL.md:24 (irrevocability) · fixed
- MAJOR · recheck/SKILL.md:24 (chat-branch bypass) · fixed
- MAJOR · signoff/SKILL.md:34, recheck/SKILL.md:22,36 (rebuild flip) · fixed
- MINOR · signoff/SKILL.md:125 · broke: the "exhaustively" write list doesn't explicitly name the stale-card mapping update the sweep commands — a literal session refuses the write, card stays cosmetically open, re-reported each sweep; no deadlock, no wrong verdict · Slice D recheck
- MINOR · build/SKILL.md:56 · broke: the Step 5 punch-list guard names the waiver line but not REOPENED, which Step 2 explicitly commands — explicit command wins on any reasonable reading · Slice D recheck
### 2026-08-02 — reconcile: MINOR backlog (per user)
Bookkeeping, not a recheck: fix passes incidentally resolved MINOR lines whose entries additive-only forbids editing. Each line below was verified resolved against current file text by an independent reader and spot-checked at adjudication. Resolved lines only; every MINOR not listed here remains open. Latest-dated record wins. Join keys are the original entries'; claims disambiguate co-located items.
- MINOR · recheck/SKILL.md:32,52 · (executed-vs-read-only bridge clause) · resolved — recheck:41 "verified statically and declared so"
- MINOR · recheck/SKILL.md:58 · (PARTIAL vs NOT CLEAR boundary, broke counting) · resolved — recheck:78 defines all three; "open" counts fix-introduced defects
- MINOR · recheck/SKILL.md:20 · (no dedup rule for doc ∪ chat) · resolved — recheck:24 dedupes on file:line + claim across the merged set
- MINOR · recheck/SKILL.md:20 · (other open slices silently dropped) · resolved — recheck:22 names the rest; output template carries "Other open slices:"
- MINOR · blueprint/SKILL.md:64 · (ownership line omits recheck) · resolved — blueprint:64 names /signoff, /recheck, and recorded user waivers
- MINOR · signoff/SKILL.md:125 · (REJECTED append could drop MINORs) · resolved — signoff:125 appends "the BLOCKERs and any MAJORs as well" on top of the MINORs
- MINOR · signoff/SKILL.md:125 · ("one more doc write" undercounts) · resolved — signoff:125 enumerates further doc writes exhaustively, sweep block included
- MINOR · signoff/SKILL.md:34 · ("MINORs never gate" dropped from sweep) · resolved — signoff:34 "MINORs are never swept and never gate"
- MINOR · build-plan ## Build assumptions (Slice B entry) · (ledger misdescribed inline mapping copy) · resolved — the inline copy is gone from signoff:34; the flip is full-clearance-only and the mapping is referenced, not duplicated, so the ledger's description is now true
- MINOR · build/SKILL.md:31 · (preflight lacks latest-dated tiebreak) · resolved — build:31 "the latest-dated record for an item decides its state"
- MINOR · blueprint/SKILL.md:8,36 · (consumer count predates recheck) · resolved — blueprint:8 names all three consumers; blueprint:36 adds /recheck's records to the key-off list
- MINOR · signoff/SKILL.md:34 · (rebuild state mislabeled "record inconsistency") · resolved — signoff:34 "a rebuild awaiting re-verification"
- MINOR · build/SKILL.md:31 · (BLOCKER waivability at build's station ambiguous) · resolved — build:31 "any named finding can carry one, only the user's word creates or revokes one"
- MINOR · signoff/SKILL.md:34 · (sweep sentence four dash-pairs deep) · resolved — signoff:34 rebuilt as short sentences; the swept-item definition now follows its antecedent directly
### 2026-08-02 — review: Slice E
- MAJOR · signoff/SKILL.md:34 · the sweep's clearing-line shape lives only in recheck's file — "standard recheck-format block" is a cross-file reference that transmits no content · a /signoff session (which never loads recheck's file) writes the full-clearance block with claimless lines; the file:line + claim open-filter then can't match them to their originals, co-located findings collapse, and a rebuilt card's "closed" entries treadmill through every later sweep · Slice E review
- MAJOR · build/SKILL.md:31, signoff/SKILL.md:34, recheck/SKILL.md:24,53 · the file:line + claim join states no default for records carrying no claim · the ledger's own A–D clearing blocks are claimless or tag-parenthetical; when a legacy card re-enters scope (rebuild, REOPENED) a strict session reads every legacy-cleared BLOCKER/MAJOR as open while a loose one fuzzy-matches — and the Out of scope retrofit line leans on "stated defaults" that exist for authority labels but not for claims · Slice E review
- MAJOR · signoff/SKILL.md:34,127 · pre-existing, not gating Slice E — sweep partial outcomes and sweep-found fix-introduced defects still have no sanctioned durable write (sharper successor to the standing Slice B line) · sweep finds all priors fixed but one fix introduced a serious defect: no flip fires, nothing is written, and a later fresh-session /recheck re-verifies the originals from the record, never meets the defect, and flips the card over it · Slice E review (next-slice candidate)
- MINOR · signoff/SKILL.md:122 · the Next: slot's "WITH CONDITIONS or REJECTED only" strands the sweep's /recheck recommendation when the current slice signs off clean over an open prior card · Prior conditions shows M still open but the structured slot forbids naming the station · Slice E review
- MINOR · signoff/SKILL.md:127 · "the stale-card update its mapping commands" is a garden-path reduced relative with an ambiguous "its" · an exhaustive list carrying parse debt invites a refused or misdirected write · Slice E review
- MINOR · recheck/SKILL.md:53 · the claim is parenthesized only in clearing lines while every sibling record carries it bare, and a post-fix-location parenthetical can share the line · an exact-form matcher fails the very join the field exists to serve; spec-mandated format, design debt · Slice E review
- MINOR · recheck/SKILL.md:73 · the chat output line still lacks the claim field the doc line gained · two co-located findings resolving differently are indistinguishable in the chat verdict; matches the build's Discovered entry, found independently by two lenses · Slice E review
- MINOR · signoff/SKILL.md:34,127 · "per the mapping" / "its mapping" points at a mapping defined only in recheck:51 · a signoff-only session infers the stale-card target state, and inferences can diverge on a card that stood rejected · Slice E review
- MINOR · build/SKILL.md:31 · "the latest-dated record" enumerates no record types while both siblings close the set to recheck/WAIVED/REOPENED lines · a later review block at the same file:line + claim silently overrides a standing waiver at build's station only · Slice E review
- MINOR · build/SKILL.md:31 vs 56 · Step 2's commanded card update can write `signed off` while Step 5 flatly bans verdict-shaped writes and its carve-outs don't name the Step 2 update · a literal builder refuses the commanded write; recoverable via the sweep's stale-card path · Slice E review
- MINOR · build/SKILL.md:31, signoff/SKILL.md:127, recheck/SKILL.md:24 · WAIVED/REOPENED lines have no stated append location and same-date records no tiebreak · three sessions file them three ways; a block and a floating line sharing one date have no resolution rule · Slice E review
- MINOR · signoff/SKILL.md:56,58 · whether a LIGHT run's added lens spawns a second reviewer or fuses into the one is unstated, and "nothing else" survives only by its trailing concession · three lenses converged; coverage equivalent either way · Slice E review
- MINOR · signoff/SKILL.md:87 vs 40 · rule 10 says reviewers get "spec sections" while Step 2 says "the spec path" — excerpting vs whole-file are different mechanics · a careless excerpt drops the doc-level Out of scope line · Slice E review
- MINOR · signoff/SKILL.md:87 vs 34 · "ledger sections stay outside their mandate" carries no carve-out for the sweep items the same file sends into reviewer scope · downgraded from a seams-lens MAJOR at adjudication: the pre-E sentence ("not the builder's ledger") excluded the same content, so the tension is pre-existing in kind; E-R8 didn't resolve it · Slice E review
- MINOR · signoff/SKILL.md:127 · the builder-call-deviation MAJOR line has no natural file:line or scenario for the format's mandatory fields · pre-existing (B-era); recheck's ask-branch recovers downstream · Slice E review
- MINOR · build/SKILL.md:32 · pre-existing core, sharpened by E-R7 — a rebuilt `built` dependency with open BLOCKER/MAJOR entries passes ungated while the strictly better `signed off with conditions` now carries a demand · framing proceeds on unre-verified foundations the sweep catches only after the build · Slice E review
### 2026-08-02 — recheck: Slice E
- MAJOR · signoff/SKILL.md:34 · (sweep clearing-line shape lives only in recheck's file) · fixed
- MAJOR · build/SKILL.md:31, signoff/SKILL.md:34, recheck/SKILL.md:24,53 · (file:line + claim join states no default for claimless records) · not fixed — the bare-line shape is now covered at all three sites, but the tag-parenthetical legacy shape still parses two ways everywhere: the canonical claim is itself parenthesized and no file defines a claim-field boundary, so strict and loose sessions still diverge on the same record
- MAJOR · build/SKILL.md:31, signoff/SKILL.md:34, recheck/SKILL.md:24 · broke: the no-claim fallback un-disambiguates co-located findings — a claimless latest-dated record at a location holding two open entries matches on file:line alone and reads both as fixed or waived when only one was ever verified, conflicting with recheck:53's stay-distinct rule
- MAJOR · signoff/SKILL.md:34 · broke: the inlined clearing-line format omits recheck:53's original-location join-key clause — a sweep clearance on moved code records the post-fix location, every later open-filter matches on the original location and misses it, and the entry treadmills as still open
- Note: the review block's third MAJOR (sweep partial-outcome writes) is excluded from this checklist per its own recorded "pre-existing, not gating Slice E" text — next-slice candidate.
### 2026-08-02 — recheck: Slice E (second)
- MAJOR · build/SKILL.md:31, signoff/SKILL.md:34, recheck/SKILL.md:24,53 · (file:line + claim join states no default for claimless records) · fixed
- MAJOR · build/SKILL.md:31, signoff/SKILL.md:34, recheck/SKILL.md:24 · (no-claim fallback un-disambiguates co-located findings) · fixed
- MAJOR · signoff/SKILL.md:34 · (inlined clearing-line format omits original-location join-key clause) · fixed
- MINOR · signoff/SKILL.md:34 · broke: "the clause" in the new post-fix-location tail has no defined referent — one reading tucks the moved location into the claim field, breaking the join the keyed-to clause protects; low likelihood, conservative direction (recheck:53 carries the same wording pre-existing)
### 2026-08-02 — review: Slice F
- MINOR · blueprint/SKILL.md:64 · the sanctioned-lines parenthetical omits REOPENED — "user-granted waivers, rebuild notes" names two of build's three sanctioned line types · an auditor reading blueprint as the ownership map flags a build-appended REOPENED line as unsanctioned · Slice F review (three lenses converged; builder-added parenthetical)
- MINOR · blueprint/SKILL.md:64 · the block/line split implies waiver lines are /build-only while all three stations append them on the user's word · a literal reader flags a signoff-written WAIVED line as a ledger violation or reroutes mid-review waivers to the next build · Slice F review (partly F-R2's own spec wording)
- MINOR · blueprint/SKILL.md:64 · "only" can scope beyond the punch list, reading as forbidding the ledger-section appends the same sentence grants /build · visible-in-sentence contradiction, most readers recover · Slice F review
- MINOR · blueprint/SKILL.md:36 · "keep the section names exact" is narrower than what the listed consumers key off (the Status: label, block headings, ·-separated fields) · a session renames Status: while keeping headings exact and breaks preflight and the flip · Slice F review (structure predates F)
- MINOR · blueprint/SKILL.md:36 · "status and clearing records" half-misnames the writes — recheck's status write is an in-place line edit, not a dated record, and the sweep also writes recheck-headed clearing blocks · a reader scaffolds a status-record section or attributes every recheck-headed block to a /recheck run · Slice F review
- MINOR · signoff/SKILL.md:10 · "The upstream skills leave a paper trail ... never as evidence" now has /recheck in its antecedent set while the sweep treats latest-dated recheck lines as authoritative · a broad reader re-verifies recheck-closed items every sweep, skewing Prior conditions counts · Slice F review (two lenses; low fire-chance — "this station's follow-up visit" pulls recheck out of "upstream")
- MINOR · signoff/SKILL.md:10 · "follow-up visit ... re-verifying the named findings" drifts from the family's "re-inspection visit" vocabulary, can parse as re-validating findings rather than checking fixes, and omits the card flip · downstream operative text corrects all three readings · Slice F review
- MINOR · build-plan doc (Out of scope block; Slice F open-question prose) · spec bookkeeping — the blueprint-edits supersession note was never extended for F-R2/F-R3, and the (a) description says "two sentences change" against three requirement sites · a literal spec-lens reviewer raises a false scope-creep question · Slice F review
### 2026-08-02 — reconcile: E/F incidental resolutions (per user)
Bookkeeping preceding the G–J blueprint: backlog lines fixed by Slices E/F, each verified by that slice's independent review or recheck (cited). Resolved lines only; every line not listed remains open. Latest-dated record wins.
- MINOR · signoff/SKILL.md:125 · (exhaustive write list omits the stale-card update) · resolved — E-R1, confirmed by E review spec lens
- MINOR · build/SKILL.md:56 · (Step 5 guard names WAIVED but not REOPENED) · resolved — E-R2, confirmed by E review spec lens
- MINOR · build/SKILL.md:101 · (don't-list flatly forbids sanctioned punch-list writes) · resolved — E-R3, confirmed by E review spec lens
- MINOR · recheck/SKILL.md:53 · (clearing lines omit the claim; co-located findings indistinguishable) · resolved — E-R4, confirmed by E review spec lens
- MINOR · recheck/SKILL.md:24,53 · (waiver join key unstated) · resolved — E-R5, confirmed by E review spec lens; hardened by the E fix passes
- MINOR · build/SKILL.md:31 · (caps verdict string absent from the lowercase artifact) · resolved — E-R6, grep-verified by two lenses
- MINOR · build/SKILL.md:31-32 · (with-conditions dependency passes without the fixed-or-waived demand) · resolved — E-R7, confirmed by E review spec lens
- MINOR · signoff/SKILL.md:42 vs 87 · (rule 10's closing sentence unamended for the shared-file case) · resolved — E-R8, confirmed by E review spec lens
- MINOR · signoff/SKILL.md:56,58 · (LIGHT plus added lens contradicts "only the reviewer count shrinks") · resolved — E-R9; the reviewer-arithmetic residual is its own open E-review line
- MINOR · signoff/SKILL.md:101,107-121 · (no output-template slots for the /recheck pointer and rule-4 questions) · resolved — E-R10, confirmed by E review spec lens
- MINOR · signoff/SKILL.md:10 · ("the last station of the loop" false with /recheck live) · resolved — F-R1, grep-verified by all three F lenses
- MINOR · build/SKILL.md:8 · (three-station opener bakes in stale loop shape) · resolved — the user's recorded (a) ruling: the openers stand deliberately
- MINOR · blueprint/SKILL.md:64 · ("/signoff appends the punch list" false three ways) · resolved — F-R2, confirmed by F review; successor wording debts recorded as F-review lines
- MINOR · blueprint/SKILL.md:36 · (key-off list names recheck's writes, not its reads) · resolved — F-R3, confirmed by F review
- MINOR · recheck/SKILL.md:53 · (claim parenthesized only in clearing lines; exact-form matchers fail the join) · resolved — E second fix pass's claim-field boundary rule, verified in the second E recheck's Item 1 evidence
### 2026-08-02 — reconcile: audit pass before G–J (per user)
A coverage audit of G–J against the open backlog found records resolved in substance but never closed on the ledger; each verified against its cited evidence. Sub-claims named where a line only partially closes.
- MAJOR · build/SKILL.md:31 vs recheck:36/signoff:34 · (waived findings have no record representation anywhere in the loop) · resolved — built as Slice D R1 (the WAIVED/REOPENED lifecycle), verified by the D review/recheck cycle; the C recheck's exclusion note deferred this line but never closed it
- MAJOR · build/SKILL.md:54 vs signoff:34/recheck:22 · (COMPLETE rebuild flips rejected → built, blinding the sweep and recheck) · resolved — built as Slice D R2 (rebuild rule + built-with-open-entries scope pulls), verified by the D review/recheck cycle
- MINOR · build/SKILL.md:31 · (the date-slot sub-claim of the D-review dateless-WAIVED line) · resolved — the D fix pass's dated formats, verified by the D recheck; the header/placement sub-claim stays open and is Slice I-R3's subject
- MINOR · signoff/SKILL.md:34 · (the pre-format-entries-fallback sub-claim of the B-review sweep line) · resolved — E-R5's claimless-record default with its shared-location ask branch, verified in the second E recheck; the mid-sweep-channel and correctness-only sub-claims stay open, covered by G-R2 and H-R13

### 2026-08-02 — review: Slice G
- MAJOR · signoff/SKILL.md:34 × build/SKILL.md:31 · the sweep's now-durable fix-introduced BLOCKER leaves a `signed off with conditions` card that build's preflight never gates on — build:31/32 read only "the named MAJORs" and build:33 keys only on `rejected` · sweep assigns BLOCKER to a fix-introduced defect, the card-untouched rule holds the card at with-conditions, user skips /recheck, next /build's preflight passes and framing proceeds over a recorded open BLOCKER · Slice G review
- MINOR · signoff/SKILL.md:34, recheck/SKILL.md:24,53, build/SKILL.md:31 · bare-claim extraction from a broke line's fused "broke: claim — scenario" field is defined nowhere, and signoff is now the shape's second author · a strict matcher string-compares the fused field against a later clearing line's bare kernel, fails the join, and the defect reads open forever; live ledger practice joins these semantically, so the failure direction is a conservative treadmill · Slice G review (three lenses converged; downgraded from MAJOR — pre-existing in kind at recheck:53)
- MINOR · signoff/SKILL.md:34 vs spec G-R2 vs recheck/SKILL.md:53 · the defect line is a third dialect — recheck's fused shape plus a trailing attribution field recheck lacks, vs G-R2's literal five clean ·-fields — and the inline format sits between prose em-dashes its own body also uses · field-count matchers and shape-keyed readers diverge by writer; join-key fields align, so joins survive · Slice G review
- MINOR · signoff/SKILL.md:127 vs 34 · "written whatever the verified outcome" can read as write-on-every-sweep against 34's ≥1-item-verified guard · a session executing from the enumeration alone appends an empty recheck-headed block on a record-gap or all-waived card — ledger noise and a same-date-tie seed · Slice G review
- MINOR · signoff/SKILL.md:34 · the write guard's "verified" collides with the file's own "verified fixed" idiom (lines 34, 112) · a reader keyed to the idiom skips the block on a nothing-fixed sweep; the same sentence's "full, partial, or nothing fixed" enumeration disambiguates, so divergence needs a partial read · Slice G review (downgraded from MAJOR)
- MINOR · signoff/SKILL.md:34 · the block write is not explicitly per-card and the heading's `<slice>` is never bound to the swept prior slice · a multi-card sweep files two slices' lines under one heading, or a naive executor heads the block with the slice under review; joins are heading-agnostic so damage is misfiled reads, not lost items · Slice G review (downgraded from MAJOR)
- MINOR · signoff/SKILL.md:34 vs recheck/SKILL.md:51 · "blocks any flip" is severity-unqualified and card-unscoped — a MINOR-rated defect blocks the sweep's flip though "MINORs are never swept and never gate," and /recheck's mapping would flip the same card · same doc state, different card outcome by station; pre-G wording G-R2 preserved ("it already blocks the flip") · Slice G review
- MINOR · signoff/SKILL.md:34,127, recheck/SKILL.md:24,53, build/SKILL.md:31 · same-date records still have no tiebreak and G's partial blocks put sweep-then-same-day-recheck ties on the happy path · a same-day not-fixed sweep line ties a fixed recheck line; a same-day REOPENED can tie against a fixed line and lose the user's word · Slice G review (amplifies the recorded Slice E tiebreak line, I-R3's target)
- MINOR · signoff/SKILL.md:34 · an item the sweep cannot resolve has no sanctioned line — the sweep never imported recheck:41's verify-statically-and-declare rule · the unresolvable item silently vanishes from the block; its original entry stays latest-dated and open, so degradation is conservative · Slice G review
- MINOR · signoff/SKILL.md:34,127 · block-then-card sequencing plus an interrupted session can strand an all-items-closed card at `signed off with conditions` — fixed-closed is neither "stale" nor a "record gap," and a zero-open sweep writes nothing · low likelihood; a later /recheck's card-already-clear path recovers it under a reasonable read · Slice G review
- MINOR · blueprint/SKILL.md:36 · the key-off list credits "status and clearing records" to /recheck alone while the sweep now also writes clearing records and flips · descriptive staleness only; blueprint:64's ownership sentence stays accurate · Slice G review

### 2026-08-02 — recheck: Slice G
- MAJOR · signoff/SKILL.md:34 × build/SKILL.md:31 · (the sweep's now-durable fix-introduced BLOCKER leaves a with-conditions card build's preflight never gates on) · fixed — build:31 now reads "the named BLOCKERs and MAJORs are fixed or waived before new framing goes up," and build:32's dependency demand inherits it by reference; verified by walking the constructed with-conditions-plus-open-BLOCKER state through the current preflight

### 2026-08-02 — review: Slice H
- MAJOR · signoff/SKILL.md:32 vs 127, recheck/SKILL.md:20 · the H-R13 sentence's "no cards or ledger" is false for correctness-only mode — line 127 creates `docs/punch-list.md` and recheck:20 assembles from it · a correctness-only session reads 32, skips the 127 append or improvises against the contradiction; findings die in chat and the next /recheck finds nothing to assemble · Slice H review (three lenses converged)
- MINOR · signoff/SKILL.md:122 · residual stranding one state over from H-R3: a dirty current verdict plus an open prior card gives the prior card's recommendation no commanded home, and a cleared rebuilt card (owed a fresh /signoff) has no Next: vocabulary at all · mitigated by the Prior-conditions M count and recheck's Other-open-slices line · Slice H review (downgraded from MAJOR — the strictly-worse original stranding was recorded MINOR)
- MINOR · signoff/SKILL.md:81 vs 34, build/SKILL.md:31 · "rule 10's one sanctioned exception" undercounts — a build-appended WAIVED (per user) line is a second trusted builder-written attestation, and "build Step 5 pins its meaning" is half-true (the assumptions label is pinned nowhere; I-R10's target) · a pedantic rule-10 reader counts waived items open and inflates M · Slice H review (downgraded from MAJOR — the byte-identical open-filter law commands the exclusion at the execution site)
- MINOR · signoff/SKILL.md:81 vs 87 · the reconciliation is one-directional — rule 10 carries no pointer back to the exception · a rule-10-first reader re-litigates a per-user descope rule 4 settled · Slice H review
- MINOR · signoff/SKILL.md:34 · the N/M counting rule is silent on sweep-found fix-introduced defects · three fixed plus one broke prints "3 · 0" beside a card that did not flip, or mislabels the defect a prior condition — divergent by session · Slice H review (three lenses converged)
- MINOR · signoff/SKILL.md:34,112 · a record-gap or all-waived card yields "0 verified fixed · 0 still open" — a clean-looking line beside a card the paragraph calls never fully clear · Slice H review
- MINOR · signoff/SKILL.md:127 vs 89-101 · the enumeration attributes the flip and stale-card update to the Severity → verdict mapping, which commands neither — line 34 commands both, using the mapping · a pedantic cross-checker finds no command in the named section, voids the item, and skips the write; the "that ... commands" attachment stays residually ambiguous · Slice H review
- MINOR · signoff/SKILL.md:87 · the except-clause can attach to "the whole doc," inverting the carve-out into withholding the sweep items; the relative clause forces repair so fire-chance is low; whether reviewers receive the precomputed open set or run the open-filter themselves is unstated · Slice H review
- MINOR · signoff/SKILL.md:10 · "the sweep honors them" reads as unbounded endorsement of any recheck-format line (the unearned clearance's sibling), and "flipping the card" over-promises — PARTIAL outcomes and rebuilt built cards do not flip; intro gloss, governing text elsewhere · Slice H review
- MINOR · signoff/SKILL.md:127 · a deviation MAJOR line keyed to a doc-internal file:line goes stale on the next ledger append — the join survives as an opaque string; human resolution drifts · Slice H review
- MINOR · signoff/SKILL.md:56 · the new size bound inherits the attachment ambiguity (readable as conditioning user-invoked LIGHT too, with no refusal path stated) and "on the order of a hundred" is soft, not a cap · Slice H review (attachment pre-existing; H added the bound)
- MINOR · signoff/SKILL.md:34 vs recheck/SKILL.md:24, build/SKILL.md:31 · pre-existing open-filter drift surfaced by this review: signoff drops "dated" before the WAIVED record type, bolds latest-dated where siblings are plain, and says "entry" for their "item" · a dateless legacy WAIVED line is a candidate record in signoff and excluded in recheck — same card, two open sets · Slice H review (pre-existing; I-R3-adjacent)

### 2026-08-02 — recheck: Slice H
- MAJOR · signoff/SKILL.md:32 vs 127, recheck/SKILL.md:20 · ("no cards or ledger" false for correctness-only — punch-list.md exists) · fixed — line 32 now affirms the ledger and points at the Output section's append command; cross-reference, file path, and per-verdict-class append rules verified word-for-word against 127 and recheck:20; no fix-introduced defects

### 2026-08-02 — review: Slice I
- MAJOR · build/SKILL.md:56 vs 31 · the Step 5 verdict-shape carve-out names the card update "after a waiver" while Step 2 commands it on grant AND revocation — the REOPENED-triggered demotion is not exempted · user revokes a waiver at preflight; a conservative session appends the REOPENED line but refuses the demotion as verdict-shaped; the card stays `signed off` and a reopened BLOCKER escapes every station's trigger list (preflight, sweep, and recheck all key on conditions/rejected/built-with-entries) · Slice I review
- MAJOR · recheck/SKILL.md:51,53 × build/SKILL.md:31, signoff/SKILL.md:127 · the new same-date tiebreak plus recheck Step 4's own paragraph order mechanically revokes a mid-run waiver · recheck verifies an item not fixed, user waives mid-run; text order appends the WAIVED line, then the block whose one-line-per-checklist-item rule still includes the waived item's "not fixed" line; same date, block line later in file, tiebreak resolves the item open — the user's waiver dies without the user's word, and signoff's opposite paragraph order gives the opposite outcome for the same state · Slice I review (two lenses converged; pre-I the tie was undefined ambiguity, the new sentence makes the wrong outcome deterministic)
- MAJOR · signoff/SKILL.md:34 · pre-existing, not gating Slice I — "uncleared" is ambiguous under an all-waived rebuilt `built` card: if waiver ≠ clearing, the sweep trigger fires and the stale-card mapping flips never-reviewed code to `signed off`, contradicting the stays-built guarantee two sentences later; if waiver = cleared, the trigger never fires and the card benignly stays `built` · one reading mints the unearned flip both files call unforgivable · Slice I review (next-slice candidate; I's build:32-33 reuse the same term but converge harmlessly there — the fixed-or-waived demand is satisfied under either reading)
- MINOR · signoff/SKILL.md:127, recheck/SKILL.md:53, build/SKILL.md:31 · the tiebreak's axiom ("appends only land at the end") is asserted for all appends but commanded only for WAIVED/REOPENED lines — block placement is nowhere commanded · a mis-inserted block (it happened twice in this very session) silently falsifies file-order-equals-time-order and the tiebreak returns a wrong answer with no escape hatch, unlike the shared-location rule's ambiguity-goes-to-user · Slice I review
- MINOR · all four tiebreak sites · the scope of "when records share a date" is two-ways readable — WAIVED/REOPENED lines only, or all records including block lines · the narrow reading leaves same-date block-vs-block conflicts (real: a sweep block and a true recheck block share the heading format and a date) with no tiebreak at recheck:53 · Slice I review
- MINOR · all four tiebreak sites · "at the end of the section" and "outside any block" are jointly unsatisfiable once the section ends with a block — markdown heading scope runs to the next heading · execution (A) appends inside the last block's scope; execution (B) appends before the first heading and permanently falsifies file-order-equals-time-order · Slice I review
- MINOR · build/SKILL.md:25 · "'seeds' is additive" glosses a word the edit itself deleted — the operative verb is now "feed" and the quoted term has no antecedent · a fresh reader meets a floating definition; the gloss's content survives on its own · Slice I review
- MINOR · build/SKILL.md:32 · "carries the same fixed-or-waived demand as the prior slice" admits a state-reference reading (whatever demand the prior slice currently carries — none, when it stands clean) alongside the intended rule-reference; pre-existing phrasing, reused for the new built-with-entries case · Slice I review
- MINOR · build/SKILL.md:25 · "a requirement no criterion checks is a gap to flag" names no destination (chat contract, ledger, or rule 2's stop) · sessions diverge in process, not ledger state · Slice I review
- MINOR · build/SKILL.md:85 vs 56 · the authority-label placement rule lives only inside the chat template's angle-bracket slot — the doc-side `## Deviations` entries signoff rule 4 actually parses get no field-position rule, and rule prose inside a template slot can leak into filled reports · Slice I review
- MINOR · build/SKILL.md:56 · the assumptions gloss "a user-answered gap-fill is `per user` there too" can detach from the Deviations definition's exclusion ("not merely that a stop-and-ask got an answer"); "with the same meanings" pulls the strict way · Slice I review
- MINOR · build/SKILL.md:31 · "recheck line" covers sweep-written clearing lines only by block-heading convention — an authorship reader excludes them and re-demands sweep-cleared items; conservative direction · Slice I review
- MINOR · build/SKILL.md:16 vs signoff/SKILL.md:28, recheck/SKILL.md:20 · hunt-priority asymmetry introduced: build alone has tier priority and the same-tier stop-and-ask; signoff's hunt can still silently pick, and recheck defers to "same hunt as the siblings" — siblings that now disagree · Slice I review
- MINOR · build/SKILL.md:56 · the REBUILT line remains write-only — exact format delivered, but no consumer parses it; every trigger keys on card state plus uncleared entries · Slice I review
- MINOR · build/SKILL.md:25 · the requirements-to-criteria pairing is 1:1-shaped ("the acceptance criterion that checks it") — one-requirement-two-criteria and criterion-checking-nothing are unstated; the recorded scenario itself is dead · Slice I review
- MINOR · signoff/SKILL.md:34, recheck/SKILL.md:53 · the tiebreak lives only at append-command sites — signoff's open-filter (the read site, 93 lines from its copy) and recheck's block-conflict rule get it by cross-reference only; letter-compliant with I-R3 · Slice I review
- MINOR · build/SKILL.md:101 vs 31,56 · the don't-list's unqualified verdict-shape ban and its "appends" vocabulary don't name Step 2's commanded card update or the Status set (both edits, not appends) — I-R2's reconciliation stopped one line short of the NOT-to-do list · Slice I review
- MINOR · build/SKILL.md:32, signoff/SKILL.md:34, recheck/SKILL.md:22 · three names for the one rebuilt state ("a rebuild never re-verified" / "awaiting re-verification" / "whose findings were never re-verified") — cosmetic drift, all three sites gate correctly · Slice I review
- MINOR · blueprint/SKILL.md:64 · staleness widened by I: "user-granted waivers, rebuild notes" now under-describes build's REOPENED lines and the formatted REBUILT line · amplifies the queued J-R1/J-R2 targets · Slice I review
- MINOR · signoff/SKILL.md:34, build/SKILL.md:31 · pre-existing residue: after a rebuilt slice earns a fresh `signed off`, its old open entries are never closed by any station and become invisible — no trigger reads `signed off` cards · Slice I review (pre-existing; observation)
- MINOR · spec Slice I Goal line vs build/SKILL.md:31 · the Goal's "close every open build-file MINOR" overclaims — the G-review broke-line-extraction MINOR cites build:31 and sits in no I requirement · bookkeeping only; requirements are the contract · Slice I review

### 2026-08-02 — recheck: Slice I
- MAJOR · build/SKILL.md:56 vs 31 · (Step 5 carve-out grant-only; REOPENED demotion not exempted) · fixed — the carve-out now reads "after a waiver grant or revocation" and classifies the update as a recorded user ruling; the refusal path is gone and the demoted card re-enters every trigger list
- MAJOR · recheck/SKILL.md:51,53 × build/SKILL.md:31, signoff/SKILL.md:127 · (same-date tiebreak plus paragraph order mechanically revokes a mid-run waiver) · fixed — recheck:51 now commands the write order ("the `WAIVED` line is written after this run's punch-list block"), so the user's word is the item's latest same-date record on either branch of the block-line question; shared-sentence byte-identity re-verified 4/4, and the ordering clause checked consistent with the shared sentence, the open-set carve-out, and signoff:127's symmetric order
- Note: the I-review block's third MAJOR (signoff:34 "uncleared" under all-waived rebuilt cards) is excluded from this checklist per its own recorded "pre-existing, not gating Slice I" text — next-slice candidate.

### 2026-08-02 — review: Slice J
- MAJOR · build-plan doc:40-42 (the Out of scope supersession amendment) · the amendment misattributes F-R1 as a blueprint-editing requirement — F-R1's own text and trace target signoff:10; F's blueprint edits are F-R2/F-R3 only · a future auditor maps F-R1 → blueprint via the note, finds nothing, and files the exact false scope-creep question the note exists to kill; a dated correction is required since the record is additive-only · Slice J review (three lenses converged; the slice roster D/F/J/K is correct — the defect is the requirement numbers)
- MINOR · recheck/SKILL.md:86 vs 62, 24 · the new bookkeeping carve-out enumerates "user-granted waiver lines" and omits REOPENED, which Step 1 sanctions and rule 6 names — two conflicting enumerations of one write set · a literal don't-list reader classifies a mid-run REOPENED append as forbidden · Slice J review (downgraded from MAJOR — rule 6 and Step 1 command explicitly, matching the E-R2 precedent where the identical build-side shape was MINOR)
- MINOR · recheck/SKILL.md:73 vs 53 · the chat template's inserted (claim) slot grammatically covers broke lines, which the doc grammar denies a claim field — sessions diverge on the chat broke-line shape and a wrongly filled slot can mis-join through Step 1's chat-merge path · joins run off the doc blocks, so chat is display · Slice J review (downgraded from MAJOR; extends the recorded G-review broke-line dialect line)
- MINOR · blueprint/SKILL.md:36 · the keep-exact enumeration's precision invites expressio unius — `Depends on:`, `Not in this slice:`, `Out of scope:`, and the `— verify:` clause are all literally read by consumers yet unlisted, and naming `Status:` separately implies sibling labels are free to vary · renaming `Not in this slice:` destroys signoff's Deferred evidence while every named form stays exact · Slice J review (spec-faithful — the delivered list matches J-R2's own enumeration; residual is spec-shaped)
- MINOR · blueprint/SKILL.md:36 · the rewritten consumer list credits recheck with assembly and Status edits but no longer names its punch-list block append — the mirror image of the scenario the rewrite fixed · mitigated by line 64's correct ownership sentence · Slice J review
- MINOR · blueprint/SKILL.md:64 · "Scaffold them; never pre-fill them" now sits four clauses from its referent, and the final preceding noun is line types — a literal reader scaffolds empty WAIVED/REBUILT stubs the join machinery would match · the template block above anchors most readers · Slice J review
- MINOR · blueprint/SKILL.md:64 · "names all three line types" delivered as one name plus the pronoun "those two" — resolves uniquely today, dangles under any future edit to the preceding clause · Slice J review
- MINOR · recheck/SKILL.md:45 vs signoff:72 · the aligned redirect line lacks signoff's pass-it-along clause, and recheck's runs happen inside the Step 2 subagent — the party producing bulk output never receives the instruction · Slice J review
- MINOR · build-plan doc:371-373 · the correction note quotes "(a) two sentences change" — a string that never appears contiguously in the prose it corrects · an exact-form matcher finds nothing; same species as the legacy-tag rules · Slice J review
- MINOR · recheck/SKILL.md:73 vs signoff/SKILL.md:116 · cross-station chat dialect: recheck parenthesizes (claim), signoff's chat finding line carries it bare, and the parens-are-not-claim rule lives at neither chat site · Slice J review
- MINOR · blueprint/SKILL.md:64 · pre-existing, unchanged sentence: "recorded user waivers set the verdict states" does not literally cover REOPENED-driven demotions build:31 and signoff:127 command · Slice J review (pre-existing; outside J's mandate)
- MINOR · recheck/SKILL.md:24 vs build/SKILL.md:31, signoff/SKILL.md:127 · pre-existing, surfaced by this review: recheck sanctions REOPENED for "previously cleared or waived" items while the siblings frame it as waiver revocation only — the cleared-item reopen is receivable at one station · Slice J review (pre-existing; observation)

### 2026-08-02 — recheck: Slice J
- MAJOR · build-plan doc:40-42 · (the supersession amendment misattributes F-R1 as a blueprint edit) · fixed — the appended dated correction names F-R2/F-R3 as F's only blueprint edits and F-R1 as signoff:10's; the auditor walk through the full chain now resolves to the correct roster, the correction's own claims verified against Slice F's traces, and "only" verified sound against F-R4's (b)-only condition; no fix-introduced defects

### 2026-08-02 — review: Slice K
- MAJOR · signoff/SKILL.md:60 · the worktree default carries no dirty-state bridge while Step 1 scopes the review union to include the uncommitted tree · part-committed mid-work state (Step 1's own "normal" case) + a mutation-requiring lens → the reviewer's worktree checks out committed state only, so the lens exercises code missing the dirty half and grades stale state; under LIGHT that single reviewer is the whole review · Slice K review
- MAJOR · signoff/SKILL.md:86 · "no edits to the working tree under review" collides with the same sentence's sanctioned test runs, whose byproducts write the tree (snapshots, lockfiles, caches, build artifacts) · a strict executor skips a runnable suite and reports weaker Method, or classes every test-running lens as mutation-requiring and routes the whole review into worktrees, amplifying the stale-tree path · Slice K review
- MINOR · signoff/SKILL.md:127 · K's inserts staled prior ledger citations, and K's own ledger note under-enumerates the shifts: signoff:127→129 recorded, build:101→103 and recheck:86→88 not · a future reader resolving an old citation lands on the wrong line; recovery via claim text · Slice K review (×3 lenses)
- MINOR · signoff/SKILL.md:60 · "by default" implies an unnamed override path the rest of the rule forbids · a reader with a "good reason" treats the default as waivable back onto the shared tree; the trailing never-the-test-bed clause and rule 9 catch careful readers · Slice K review (×3 lenses; wording spec-mandated by K-R2)
- MINOR · signoff/SKILL.md:127 · garden-path opening "When executing this skill required..." plus transitive "excepting" · momentary always-on misparse, resolves on completing the sentence; fixing requires touching all four sites to preserve AC3 identity · Slice K review (spec-shaped, K-R3 wording; also at build:94, recheck:80, blueprint:96)
- MINOR · signoff/SKILL.md:107-123 · no fenced output template carries a SKILL NOTE slot (same at build:76-90, recheck:66-76, blueprint:84-94) · when the note fires, sessions place it inconsistently or misfile it under Questions:/Assumed:; same species as the E-R10 finding · Slice K review (×2 lenses)
- MINOR · signoff/SKILL.md:127 · "one of its rules" under-triggers on Step-, floor-, or Mechanics-level workarounds — the motivating field case was Mechanics-level · the channel silently misses the exact feedback class that created it · Slice K review (spec-shaped, K-R3 verbatim)
- MINOR · signoff/SKILL.md:127 · "one line" literally caps a run that bent two different rules · merge-or-drop on multi-workaround runs · Slice K review (spec-shaped)
- MINOR · blueprint/SKILL.md:96 · "the report" has no antecedent in blueprint, whose own vocabulary is "the summary block" · a literal reader must infer the referent; per-file tailoring was blocked by AC3's identical-sentence requirement · Slice K review (spec-shaped)
- MINOR · signoff/SKILL.md:60 · non-git projects have no worktree and Mechanics names no fallback · the named default is unactionable there; rule 9's report-as-unverifiable path recovers a careful executor · Slice K review
- MINOR · signoff/SKILL.md:60 · a worktree a mutation lens actually used is by definition changed, so the harness's auto-clean-if-unchanged never fires · every such review leaves a worktree plus branch registered in the repo rule 9 protects; harness-dependent · Slice K review
- MINOR · signoff/SKILL.md:60 vs recheck/SKILL.md:41 · verification asymmetry: signoff executes mutation scenarios in worktrees, recheck verifies the same class "statically and declared so" · the card flips on strictly weaker evidence than created the finding; pre-existing in kind, widened by K · Slice K review (×2 lenses)
- MINOR · signoff/SKILL.md:86 · the colon grammatically attaches the three external examples to the interposed checkout clause · category-error parse; each prohibition stays individually clear, no wrong action found · Slice K review
- MINOR · signoff/SKILL.md:86 vs 129 · the flat working-tree ban nominally collides with signoff's own commanded ledger writes · a literal reader refuses the bookkeeping; the scoped subject ("Reviewers and the execute step") and 129's bookkeeping-not-repair line resolve it; E-R2 explicit-command-wins shape · Slice K review
- MINOR · signoff/SKILL.md:60 vs 34 · the worktree trigger is lens-method-scoped, so a mutation-requiring swept item inside an otherwise non-mutating lens falls through to rule 9's generic remedy · Slice K review (spec-faithful, K-R2 scoped to lenses)
- MINOR · signoff/SKILL.md:127 · the SKILL NOTE sentence presupposes workarounds happen and never states the note does not authorize one · a session cites the note as fig leaf for overriding a hard stop (e.g. sub-floor SIGN-OFF emission) · Slice K review (downgraded from MAJOR at adjudication: no permissive verb in the sentence, Step 0's STOP and the don't-list line are unqualified, presupposition structure is K-R3-verbatim; also at build:94, recheck:80, blueprint:96)

### 2026-08-02 — recheck: Slice K
- MAJOR · signoff/SKILL.md:60 · (the worktree default carries no dirty-state bridge while Step 1 scopes the review union to include the uncommitted tree) · fixed — the Mechanics paragraph's closing sentence now commands carry-in ("apply the working tree's diff inside the worktree" before the lens runs) or forced Method-line disclosure as an exclusive or; the silent stale-code review is no longer a permitted reading, including under LIGHT
- MAJOR · signoff/SKILL.md:86 · ("no edits to the working tree under review" collides with the same sentence's sanctioned test runs whose byproducts write the tree) · fixed — the byproduct carve-out ("a sanctioned run's own byproducts — snapshot updates, lockfile touches, caches — are not edits; the ban is on altering the code being reviewed") dissolves both failure arms: test execution neither violates the ban nor triggers the Mechanics worktree default
- MAJOR · signoff/SKILL.md:86 · broke: the carve-out's two classifications collide when the byproduct file is review-scoped source — snapshots and lockfiles are checked-in code, a plain jest run writes new `.snap` content with the first clause's blessing while the second clause's own definition condemns it, and no priority rule stands between them → a strict reader mutates review-scoped source in the shared tree and reviewers read snapshots the builder never wrote; introduced by the Slice K fix pass
- MAJOR · signoff/SKILL.md:60 · broke: the named carry-in mechanism ("apply the working tree's diff") excludes untracked files under its obvious execution (`git diff`) — a slice whose new files are untracked carries only the tracked half, the executor believes the carry-in branch satisfied so the disclosure branch is never taken, and the silent-partial-state review survives with a compliant-looking paper trail; introduced by the Slice K fix pass

### 2026-08-02 — recheck: Slice K
- MAJOR · signoff/SKILL.md:86 · (the carve-out's two classifications collide when the byproduct file is review-scoped source) · fixed — the fix-pass-2 text partitions on one classifier: gitignored byproducts are not edits, unignored writes (snapshot files and lockfiles named) are mutations routed to the remedy clause; boundary cases verified statically — a brand-new `.snap` is untracked but unignored so it classifies as mutation, `go.sum` classifies as mutation, a gitignored cache write proceeds in the shared tree
- MAJOR · signoff/SKILL.md:60 · (the carry-in mechanism excludes untracked files under its obvious execution) · fixed — the command now enumerates both halves ("the tracked diff and the untracked files") and names the trap ("a bare `git diff` drops the untracked half"), so a tracked-only carry is a plain violation rather than a compliant-looking reading; the Method-line disclosure branch stays intact; no fix-introduced defects found

### 2026-08-02 — review: Slice L
- MAJOR · signoff/SKILL.md:130 · "that home" in the amended placement sentence grammatically binds to "the `## Punch list` section" — the sentence's only noun called a home — inverting the keeps-diverged-home rule · an executor on the nearest-antecedent parse appends the WAIVED line at the mid-file section tail of a doc whose blocks live at EOF, producing the split and tiebreak break L-R1 exists to prevent; same text at build:31, recheck:24, recheck:51; construction inherited verbatim from L-R1's wording · Slice L review
- MAJOR · signoff/SKILL.md:130 · "ledger blocks" scopes the keeps-that-home condition to the wrong term — the loop defines the ledger as all four sections (signoff Step 2) and build Step 5 opens "Write the ledger into the build doc" naming the three non-punch sections, so every doc with one build has "ledger blocks living elsewhere" · a rule-follower homes WAIVED lines at the `## Build assumptions` tail or reads every doc as already split; the loop's term for these blocks is "punch-list blocks" (blueprint:64); builder drift — L-R1's spec text says "existing blocks" · Slice L review
- MAJOR · signoff/SKILL.md:130 · no selection procedure for an already-split doc — "one home per doc, never split" describes a state, names no tiebreak between two existing homes, and additive-only forbids consolidating · on a doc with punch records in two places (the recorded input class: this doc's own misplaced-append history, the field doc's section-plus-EOF shape) two stations pick different homes, appends interleave, and the same-date tiebreak resolves by home choice instead of time — wrong open/closed reads, wrong Status flip, wrong preflight gate; spec-shaped: L-R1's own wording carries the gap, fix needs a spec amendment · Slice L review
- MAJOR · build-plan doc (Slice L build-assumptions entry, "Line shifts from the slot inserts, enumerated in full") · the entry misstates three of four slot positions — claims build:91, recheck:77, blueprint:95, which are the closing fences; actual slots are build:90, recheck:76, blueprint:94 (signoff:123 correct) — in a record labeled "enumerated in full", and the same wrong numbers propagated into this review's own briefs and the BUILD chat block · a future reader resolving the record lands on a bare fence line and trusts it because the entry's prose-shift numbers beside it are all correct; J-precedent species: false record, dated correction supersedes, wrong line stays · Slice L review
- MAJOR · signoff/SKILL.md:130 · pre-existing, surfaced by this review, not gating Slice L: signoff enumerates the mid-review WAIVED write and the sweep's recheck-format block with no write-order rule between them — recheck:51 pins block-then-waiver for exactly this tiebreak; signoff does not · a WAIVED line appended at grant time followed by a same-date sweep block written at output time puts the block's not-fixed line later in the file, defeating the waiver the user just granted; next-slice candidate · Slice L review (pre-existing)
- MINOR · signoff/SKILL.md:34 · the sweep write says "at the ledger's home's tail" 96 lines before the home is defined, with no pointer — build:56 got one ("Step 2's placement sentence defines the home"), the sweep did not · a session executing Step 1 top-down on a diverged doc meets an undefined term at the backstop station and can default to the literal section tail; three lenses converged, severities split (MINOR functionally, MAJOR under the strictest AC1 letter) · Slice L review
- MINOR · recheck/SKILL.md:53 · phrase variant "the doc's ledger home" vs the other seven sites' "ledger's home" — no single phrase greps all eight sites, defeating AC1's stated verify method, and the L ledger's "site count by grep: 7" is not reproducible under the phrase it names · Slice L review
- MINOR · build/SKILL.md:31 · the home definition's subject is "Appended `WAIVED`/`REOPENED` lines" — block appends borrow "the ledger's home" by implication only, so a strict reader can hold blocks unhomed by rule · same at signoff:130, recheck:24, recheck:51 · Slice L review
- MINOR · signoff/SKILL.md:123 · slot trigger says "a rule" where the prose sentence says "one of its rules" — a template-only reader fires SKILL NOTE for repo rules or git gates; noise, not corruption · same at build:90, recheck:76, blueprint:94 · Slice L review
- MINOR · recheck/SKILL.md:24 · "appends only land at the home's tail, so file order is time order" is asserted unconditionally but false on docs with pre-rule misplaced records — the assembly reader gets a justification that fails on exactly the docs the rule was written for; spec-sanctioned risk ("existing records stand"), caveat unstated · Slice L review
- MINOR · signoff/SKILL.md:130 · "create the `## Punch list` section if no home exists" is circular — the default clause defines a home unconditionally, so the condition is never literally true; both readings resolve to the same action · also recheck:53 · Slice L review
- MINOR · blueprint/SKILL.md:64 · "inside the punch list, /build's own lines are limited to..." is locative and not home-aware — on a diverged doc an auditor using it as the placement map files a false misplacement finding; the L ledger's skip rationale ("describes who appends, not where") mischaracterized the clause, though the no-change outcome stands for blueprint-scaffolded docs · Slice L review
- MINOR · build/SKILL.md:56 · Step 5's additive-only guard still reads "never touch the `## Punch list` history" while the same sentence's appends are now home-aware — on a diverged doc the guard is literally vacuous where the history actually lives; siblings phrase it section-agnostically · Slice L review
- MINOR · build/SKILL.md:31 · convention-wins cannot distinguish an established convention from yesterday's mistake — one accidentally misplaced block on an otherwise empty scaffold becomes the permanent home and "never split" forbids returning; deliberate design per L-R1's trace, entrenchment edge unstated · Slice L review
- MINOR · build-plan doc (K build-assumptions entry) · the citation-staleness chain is now two hops: K's recorded forwarding "signoff:127→129" is itself stale post-L (true site signoff:130) — resolving an H/I-era citation requires chaining K's note into L's; recorded species, joins unaffected (both open MAJORs key on signoff:34, unmoved) · Slice L review

### 2026-08-02 — recheck: Slice L
- MAJOR · signoff/SKILL.md:130 · ("that home" grammatically binds to the `## Punch list` section, inverting the keeps-diverged-home rule) · fixed — the home is now defined positively and the section branch is guarded by "when none exist yet"; walked: an EOF-blocks doc yields exactly one home (EOF), no parse reaches the mid-file section tail; byte-identical at build:31, recheck:24, recheck:51
- MAJOR · signoff/SKILL.md:130 · ("ledger blocks" scopes the keeps-that-home condition to the wrong term) · fixed — the determining term is now "the doc's punch-list blocks", matching blueprint:64's vocabulary; a doc with only build entries has zero punch-list blocks and resolves to the section home; no reading reaches a non-punch section's tail
- MAJOR · signoff/SKILL.md:130 · (no selection procedure for an already-split doc) · fixed — the latest-dated block's location is the home, later-in-file on a date tie; both split-doc scenarios walked deterministically, and all stations share the rule so appends cannot interleave across homes
- MAJOR · build-plan doc (Slice L build-assumptions entry) · (three of four slot positions false in a record labeled "enumerated in full") · fixed — the dated fix-pass correction supersedes it (same date, later in the file, wins the doc's own tiebreak) and its numbers verified independently true: signoff:123, build:90, recheck:76, blueprint:94; the wrong line stays per the additive law; no fix-introduced defects found

### 2026-08-02 — review: Slice M
- MAJOR · signoff/SKILL.md:130 · the write-order command binds "that line" to the WAIVED-or-REOPENED disjunction, ordering REOPENED after the run's blocks — M-R1 and recheck:51's model order the WAIVED line only, and the I-era fix pass explicitly rejected position-ranking user-word records because it breaks reopen-then-reverify-same-day · a waiver revoked mid-review, the item swept and verified fixed, then the REOPENED line lands after the block and wins the same-date tiebreak: the record reads open despite the verification postdating the user's word, while the identical event at recheck resolves fixed — two stations, opposite records; extension beyond spec, unlogged in the M ledger entry · Slice M review (×3 lenses, severity split 2-1)
- MINOR · signoff/SKILL.md:34 · "the next sentence's definition" is a positional anchor — a future sentence inserted between the trigger and the Open definition silently retargets "uncleared" while every identity grep still passes; the corpus's named-anchor form (build:56's "Step 2's placement sentence") was available · Slice M review (×2 lenses)
- MINOR · recheck/SKILL.md:22 · "uncleared" is now defined at signoff only; recheck's slice resolution keeps the bare phrase — on the waived-is-not-cleared reading an all-waived rebuilt `built` card with the latest-dated block wins resolution, empties the checklist, ends the run early, and a genuinely open slice goes unrechecked that run (wasted run, no wrong write) · Slice M review (spec-shaped: M's footprint pinned recheck byte-unchanged; ×2 lenses)
- MINOR · signoff/SKILL.md:34 · the stale-path guard states the stays-built law in different words than the G-era clearance carve-out later in the same paragraph — consistent today, dual-wording drift risk on any future one-copy edit · Slice M review
- MINOR · signoff/SKILL.md:130 · the mid-review waiver's "card update it implies" carries no local built-card carve-out — an Output-focused executor could derive `signed off` from the adjacent Severity → verdict mapping for a swept rebuilt card; mitigated by Step 1's guard, stated twice · Slice M review
- MINOR · signoff/SKILL.md:34 · "the Output section's placement sentence" resolves by inference — the section holds two placement-shaped sentences and only one defines the home; a hasty reader grabs the appender opener; model-conformant with build:56's pointer form · Slice M review (×2 lenses, one noting the referent is unique)
- MINOR · signoff/SKILL.md:34 · the Open definition quantifies over records a fresh entry does not have — a zero-record entry gives "the latest-dated record" no referent; every practical reader lands on the intended no-clearing-record-means-open, and the new parenthetical makes the definition load-bearing at the trigger · Slice M review
- MINOR · signoff/SKILL.md:130 · "the review block and, when the sweep wrote one, its recheck-format block" uses definite articles a zero-write run cannot satisfy (clean verdict, no MINORs, waiver granted anyway) — execution survives via the placement sentence; misreadable as commanding an empty block · Slice M review (×2 lenses)

### 2026-08-02 — recheck: Slice M
- MAJOR · signoff/SKILL.md:130 · (the write-order command binds "that line" to the WAIVED-or-REOPENED disjunction, ordering REOPENED after the run's blocks) · fixed — the command's subject is now "the `WAIVED` line", matching M-R1's spec text verbatim and recheck:51's model; REOPENED reverts to placement-sentence governance only (silence restored, not a new gap — the pre-M state was equally silent); the walked revoked-waiver-then-sweep-verifies-fixed scenario now resolves FIXED at both stations; no fix-introduced defects found

### 2026-08-02 — review: N
- MAJOR · recheck/SKILL.md:51 · Step 4's Status machinery is unscoped for the multi-slice checklists the door creates · a foreign named MAJOR verifying not fixed demotes the resolved slice's card while the foreign card stays wrong; with every card `signed off` the mapping has no defined write target (divergent sessions); and door-clearing a foreign open card's last entry strands that card in a permanent phantom-recheck bounce · Slice N review (×3 lenses)
- MAJOR · recheck/SKILL.md:22 · the slice-resolution paragraph never yields for a named-entry run — "the one named" is singular and the fallback scans only open-card slices · AC1's flagship (three named entries, every card `signed off`) stalls at "Ambiguous → ask" or, read as gating, reports nothing to recheck — the visibility gap N exists to close; in footprint, unbridged · Slice N review (×3 lenses)
- MAJOR · recheck/SKILL.md:28 · the early-end sentence admits a card-already-clear reading that ends a named-entry run before verification — every door run presents a clear card, so the trap sits on the feature's mainline · in footprint, and the builder's ledger justification for leaving it ("footprint discipline") is false — line 28 is Step 1 · Slice N review (×2 lenses)
- MINOR · recheck/SKILL.md:57 · rule 1's "one exception" and the spine's "list only shrinks" were not synced with the second door · mid-run naming of a still-open entry: rule 1's letter forbids what Step 1 grants — divergent, worst case deferral to a fresh run; out of N's footprint · Slice N review (×3 lenses, severity split)
- MINOR · recheck/SKILL.md:53 · the block heading and Output slots are singular for multi-slice named runs · a three-slice run must invent a heading dialect or file foreign entries under one slice's header; joins survive — the open-filters key file:line + claim, heading-agnostic · Slice N review (×2 lenses, severity split)
- MINOR · recheck/SKILL.md:24 · "a run may assemble entirely from named entries" admits a shrink reading · user names one of a resolved slice's three open MAJORs, reader narrows the checklist to it, clears it, and flips over two live MAJORs — requires overriding the unconditional base assembly command; both finding lenses self-graded low-med confidence · Slice N review (×2 lenses)
- MINOR · recheck/SKILL.md:24 · the reopen sentence gained ", and only the user's word opens either door" though N-R1 declared that door unchanged · textual extension restating an existing law; behavior identical · Slice N review
- MINOR · recheck/SKILL.md:24 · naming "by its review block's slice" underdetermines the entry when a block holds several still-open entries · "the open E entry" against two candidates: add one, all, or ask — uncommanded; spec-inherited verbatim from N-R1's parenthetical · Slice N review (×2 lenses)
- MINOR · recheck/SKILL.md:24 · door dispatch is computed from the record, not stated by the user · an imprecise by-slice reference to an item whose latest record is WAIVED routes to the reopen door and silently revokes a waiver the user never meant to touch · Slice N review
- MINOR · recheck/SKILL.md:24 · no dedup commanded for named entries already in the default assembly · naming an already-assembled item double-counts it in the checklist, the N-items header, and the appended block · Slice N review
- MINOR · recheck/SKILL.md:24 · "either door" names a second door the text never labels · the reader retroactively construes the reopen sentence as door two; friction, no wrong outcome found · Slice N review
- MINOR · recheck/SKILL.md:24 · the flagship close-join is unexercised by N's ACs — a strict string-compare of abbreviated claim kernels against the stranded entries' long claim fields treadmills them open · conservative direction; live practice joins semantically; amplifies the recorded heading-agnostic-join species · Slice N review
- MINOR · recheck/SKILL.md:3 · the frontmatter and signoff's framing over-claim "flips the card" for door runs that legitimately flip nothing · cosmetic staleness, no wrong action commanded · Slice N review (×2 lenses)

### 2026-08-02 — recheck: N
- MAJOR · recheck/SKILL.md:22 · (the slice-resolution paragraph never yields for a named-entry run) · fixed — the paragraph's new second disjunct ("when the invocation names entries rather than a slice, the named set is the run's scope and no slice resolves") sanctions the flagship run before the fallback or the ask is reached, and the trailing sentence's "outside the run's scope" has a referent in a named-entry run
- MAJOR · recheck/SKILL.md:28 · (the early-end sentence admits a card-already-clear reading that ends a named-entry run before verification) · fixed — early end now requires an empty checklist first ("a non-empty checklist runs, whatever the cards read"); the record-gap ask for empty-against-open-card verified intact
- MAJOR · recheck/SKILL.md:51 · (Step 4's Status machinery is unscoped for the multi-slice checklists the door creates) · fixed — the mapping is per slice, each defect charged to the slice whose fix caused it, "a slice's card never moves on another slice's items"; all three recorded faces walked to one commanded outcome each, carve-outs coherent, no cross-file contradiction
- MAJOR · recheck/SKILL.md:51 · broke: the per-slice mapping's open set is glossed as checklist items only, so partially naming an open foreign slice flips its card past record entries never on the checklist — scenario: slice Q stands `rejected` with open BLOCKER B1 and MAJOR M1; the user names only M1; M1 verifies fixed; Q "has items on this run's checklist" and its mapped-over set is empty → `signed off` written over an open, unverified BLOCKER (the unearned flip); pre-fix text left foreign cards untouched, so this is fix-introduced · Slice N fix pass

### 2026-08-03 — recheck: N
- MAJOR · recheck/SKILL.md:51 · (the per-slice mapping's open set is glossed as checklist items only, so partially naming an open foreign slice flips its card past record entries never on the checklist) · fixed — the mapping input now includes "its record's still-open BLOCKER/MAJOR entries this run never verified": B1 enters Q's input and both the primary and not-fixed variants walk to `rejected` / card unchanged; no raise is reachable without full coverage of the slice's open set; faces (a)/(b)/(c), the ordinary single-slice run, both carve-outs (waived items filtered by "still-open", `built` cards still verdict-free), and the MINOR exclusion all re-walked clean; placement sentence ×4 sha256-identical; no fix-introduced defects found

### 2026-08-03 — recheck: stranded entries (E/I/L reviews, via the Slice N door)
- MAJOR · signoff/SKILL.md:34,127 · (pre-existing, not gating Slice E — sweep partial outcomes and sweep-found fix-introduced defects still have no sanctioned durable write) · fixed — the sweep now records "full, partial, or nothing fixed" as a recheck-format block whenever it verified at least one item, a fix-introduced defect gets its own severity-bearing `broke:` line in that block "and blocks any flip", and the Output section's exhaustive write list carries the block "whatever the verified outcome"; the recorded scenario's later fresh-session /recheck now meets the defect as a ledger entry; substance built by Slice G, verified here
- MAJOR · signoff/SKILL.md:34 · (pre-existing, not gating Slice I — "uncleared" is ambiguous under an all-waived rebuilt `built` card) · fixed — the trigger pins "uncleared means open by the next sentence's definition, so waiver-closed entries do not put a `built` card in the sweep's scope"; the all-waived rebuilt card never enters scope, and both the stale path and the clearance path independently bar a `built` card from taking any verdict; no path mints `signed off` on never-reviewed code; substance built by M-R2, verified here
- MAJOR · signoff/SKILL.md:130 · (pre-existing, surfaced by the L review — signoff enumerates the mid-review WAIVED write and the sweep's recheck-format block with no write-order rule between them) · fixed — the ledger paragraph now commands "the `WAIVED` line is written after this run's punch-list writes (the review block and, when the sweep wrote one, its recheck-format block)", so the user's word lands later in the file and wins the same-date tiebreak; the grant-time-waiver-defeated scenario cannot occur; substance built by M-R1, verified here

### 2026-08-03 — review: O
- MINOR · skill-feedback.md:27 · the K seed is 2 characters off character-verbatim — the trace's nested "real state" double quotes were demoted to single quotes inside the outer wrapper · a session grepping the trace's exact substring against the Inbox gets zero hits and reads the seed as a paraphrase, undermining the never-re-triaged guarantee; the doc's first worked example silently normalizes what its own rule calls verbatim · Slice O review
- MINOR · skill-feedback.md:23 · seed 1's fourth field carries a "(pre-channel, via field handoff)" prefix the stated `date · thread/project · skill · note verbatim` format doesn't allow · future sessions pattern-matching the worked example learn that free-form commentary may precede the verbatim note inside field four · Slice O review
- MINOR · skill-feedback.md:42 · disposition 2's shorthand "the ledger home rule" doesn't match L-R1's amended vocabulary ("punch-list blocks") · a reader grepping the build plan for the shorthand lands on the L review's phrase-variant MINOR rather than the requirement; low confidence · Slice O review

