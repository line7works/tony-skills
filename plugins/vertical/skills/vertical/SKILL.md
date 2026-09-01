---
name: vertical
description: The whole-build adversarial signoff — the capstone of the loop. Runs only after ALL slices of a build doc are signed off and rechecked; reviews the entire vertical against its base with Claude at full scope plus optional outside frontier models (ChatGPT, Gemini) under a reject-it mandate, and writes one verified verdict doc. Use when Tony says "/vertical", "vertical review", "run the vertical", or "whole-build signoff" on a completed build. Stops at the verdict; never fixes.
---

# Vertical

The final inspection before a build is called done. `/signoff` inspects one slice; `/vertical` inspects the whole structure once every slice's card stands `signed off` — Claude reviewing the entire vertical against its base, joined (on Tony's per-run word) by outside frontier models with a mandate to reject it. One verdict doc comes out. Nothing gets fixed here.

**The spine.** /signoff's doctrine governs every finding in this skill — the finding shape (claim · `file:line` · concrete failure scenario · severity BLOCKER/MAJOR/MINOR · confidence), verify-before-reporting (CONFIRMED/PLAUSIBLE, `Refuted: N`), the severity → verdict mapping, and report-don't-repair. /vertical adds only the whole-build scope, the outside reviewers, and the merge. Where this file is silent on review mechanics, /signoff's SKILL.md is the law.

**The one unforgivable move is an unverified outside finding reaching the verdict.** Outside models hallucinate file paths and invent plausible defects. Every outside finding is adversarially verified against the source before it can land in the verdict section; what fails verification is dropped from the verdict, counted, and left visible only in the raw appendix.

## Step 1 — Gate

The invocation names a build doc, or the skill hunts the current repo per /build's Step 1 doc tiers (`docs/<feature>-build-plan.md`, then any phase/slice doc under `docs/` or `plan/`) or takes the plan established in this session — /ship's two-source narrowing: nowhere else, no wider hunt; unresolvable means ask Tony.

Read every `## Slice` heading's `Status:` line in the build doc. A doc with zero `## Slice` headings, or a slice heading missing its `Status:` line, is malformed input: report it and STOP — the gate never passes vacuously. The gate passes only when **every slice stands `signed off`** — the loop's terminal clean state. Anything less — `built`, `signed off with conditions`, `rejected`, `not started` — fails the gate: report exactly which slices are short and in what state, and STOP. (A `built` card's remedy is a fresh /signoff, never /recheck — say so when naming it.)

Two more preconditions run with the gate, before any ask:

- **The reviewed repo must be a git repo.** No git means no base, no export, no boundary — report that /vertical cannot run here and STOP.
- **The working tree must be clean where the review looks** (`git status --porcelain`, checked against the change boundary and the build doc). Dirt that touches a boundary file or the build doc means the review would grade stale code: report it and STOP; Tony decides whether to commit first or order a committed-state-only run, and that order is recorded in the Method line. Dirt entirely outside the boundary and the build doc (a perpetually-dirty feedback log, unrelated untracked docs) does not stop the run: the review proceeds against committed state (HEAD) on both legs, and the unrelated dirt is listed in the Method line. (Scoped from an any-dirt stop 2026-08-21, per Tony, after the first live Atlas run stopped on unrelated docs.)

Only wording in Tony's own invocation ("run it anyway") collapses the gate. The skill never proposes it, and a collapsed gate is recorded in the verdict doc's Method line. The gate and preconditions run BEFORE the reviewer ask — no picking a crew for a run that stops.

## Step 2 — The ask

Stop and ask, every run:

> Local-only review, or local + ChatGPT + Gemini? (Recommended: local + both. Outside reviewers see the full tracked code.)

The skill **always waits for an answer** — silence never proceeds, and the recommended default is a recommendation, not a trigger. Tony may answer with any subset ("local + ChatGPT only" is legal). The answer applies to this run only; nothing is remembered between runs. Every external send in this skill is authorized by this answer in this run and nothing else.

## Step 3 — The base and the packet

Determine the base — the build's starting commit — by this precedence: (1) a base commit the build doc records, if any; (2) the branch point from the default branch (`git merge-base`); (3) neither resolvable → ask Tony for the base, never guess. Record the base and how it was determined; both go in the Method line.

When outside reviewers are on, compose the cold packet. Each outside reviewer receives exactly three things:

1. The build doc, verbatim — the spec they grade against.
2. The full tracked code, via a **tracked-files-only export**: `git archive` the reviewed state into a fresh directory under the session scratchpad. Never point an outside tool at the live working tree. This is a hard rule with a reason: untracked files, gitignored files, `.env`, and credential files must be *physically absent* from what outside models can read, not merely unmentioned.
3. The change boundary: the base commit id and the list of files the vertical touched (`git diff --name-status <base>..HEAD`), so they know new construction from the existing house.

Never in the packet: per-slice signoff verdicts, punch-list history, chat context, or another reviewer's output. The reviewers go in cold on findings — that is the point of paying for outside eyes.

The prompt is composed from `assets/vertical-mandate.md`: fill its placeholders with the build doc and the boundary; the code is the workspace the transport points at.

## Step 4 — The reviews

**Local, always.** The local review runs at vertical scope — the whole vertical against its base — under /signoff's full reviewer mechanics: **fresh subagent reviewers originate the findings, never this session solo** (the session merges, verifies, and adjudicates; reviewing the code itself and calling it the local review is /signoff's one unforgivable move, and it is this skill's too). The local review forms its findings **before reading any outside section** (independence), and runs regardless of which outside reviewers were picked or how they fare.

**Outside, on Tony's word from Step 2.** Transports reuse /jpb's recorded recipes (`~/Developer/tony-skills/plugins/jpb/skills/jpb/assets/box-runners.md`) with **one deliberate inversion, stated here so nobody "fixes" it back: jpb starves its boxes of repo access (neutral empty cwd — parity for a product-box); /vertical feeds the repo to them — the export directory IS the workspace, because reading the code is the assignment.** Web access stays OFF in both skills.

- **GPT** — `mcp__codex__codex` with exactly these parameters and no others: `model: "gpt-5.6-sol"`, `base-instructions`: the composed mandate, `prompt`: the review request (one fixed line: "Review the build in this workspace per your instructions and report every finding."), `sandbox: "read-only"`, `cwd`: the export directory, `config: {"web_search": "disabled"}` (string enum, not boolean). Parity line, copied literally: `web_search: disabled`.
- **Gemini** — `mcp__antigravity__ask_gemini` with exactly these parameters and no others — no modes, no ad-hoc flags: `model: "gemini-3.1-pro-high"` (the `-high` suffix IS the effort setting — never also pass `effort`), `prompt`: the composed mandate + review request, `cwd`: the export directory (box-runners' workspace parameter — the inversion is its *value*: jpb points it at a neutral empty directory, /vertical points it at the export), `skip_permissions` OFF (omit it — jpb's guard stands; the workspace grant comes from `cwd`, and anything beyond it stays denied). **An EMPTY response is a FAILED run** — a fully-denied agy run still reports SUCCESS; emptiness is the only failure signal (jpb's verified trap), and it is also what catches a permission setup that denied the reads. The converse also holds: agy can report ERROR while delivering a complete response (verified live 2026-08-21) — content decides, not the status flag: a non-empty, complete mandated-format review is a delivered survivor, with the anomaly recorded in the Method line. Parity line, copied literally: `skip_permissions off, cwd = export dir only, non-empty response`. Parity lines are copy-paste strings, not paraphrases — a literal audit greps for them.

Pinned model ids change only on Tony's word, never mid-run (jpb's standing rule). A reviewer that errors, times out, or returns empty is **dropped with its reason recorded**; the run continues with the survivors. The local review always completes.

## Step 5 — Merge and verify

- **Dedupe** on `file:line` + claim. Convergence across independent reviewers is signal — note it on the merged finding, never list it twice.
- **Adversarially verify every outside finding** against the source before it reaches Tony: read the code at the claimed location, check the failure scenario holds, stamp CONFIRMED or PLAUSIBLE per /signoff's rules. A hallucinated `file:line` is a refutation unless Claude locates the real site and says so on the finding. Refuted findings are dropped from the verdict and counted: the verdict carries `Refuted: N`.
- **Re-gradings are recorded, never silent.** Any change the merge makes to a reviewer's stated severity or confidence — a demoted MAJOR, an upgraded PLAUSIBLE — is noted on the merged finding with one clause of why (e.g. "GPT graded MAJOR; demoted: no data-loss path"). The verdict's audit trail is the product; an unexplained re-grade poisons it.
- **Compare against the per-slice record.** Claude (never the outside reviewers) reads the on-disk record — the build doc's punch-list history, its recheck blocks, and `Status:` lines; per-slice chat verdicts are gone with their sessions and are never assumed. Call out in the verdict prose: repeats (a finding the ledger already caught — note its recorded disposition) and misses (a ledgered finding marked fixed that no one re-found — verify it stayed fixed). A cleanly signed-off slice may have no ledger entries at all; the comparison covers what the record holds and says so.
- **Locationless concerns never reach the verdict.** A reviewer's "concerns without location" stay in the raw appendix unless Claude verifies one into a real `file:line` (then it is an ordinary finding). This is /signoff's evidence rule applied at the merge.

## Step 6 — The verdict doc

One file per run: `docs/vertical-signoff-<date>.md` in the reviewed repo, `<date>` in YYYY-MM-DD. A second run the same day writes `-2`, a third `-3`, and so on — never overwrite a prior run's doc. This is the skill's ONLY write: never code, never the build plan, never a `Status:` card.

Structure, top to bottom:

1. **THE VERDICT** — the merged verified findings only. /signoff's severity → verdict mapping names the outcome; findings appear in /signoff's punch-list line format (severity · `file:line` · claim · scenario · which reviewer(s) found it); `Refuted: N`; the repeats/misses prose from Step 5. (The verdict doc is its own record — /recheck's checklist reads the build doc's ledger, not this file; routing fixes from a vertical verdict is Tony's instruction after reading it.)
2. **Method line** — what ran and what didn't: base commit, reviewers used and dropped (with reasons), parity line per outside reviewer, how the local review verified (per /signoff's declare-the-method rule), and any collapsed gate.
3. **Unverified appendix** — one section per reviewer, raw output VERBATIM, under this banner: *"Raw reviewer output — unverified. Findings here that are absent from the verdict above were refuted or could not be verified. Nothing in this appendix has standing."*

The verdict is section 1 alone. That is how "nothing unverified lands in the verdict" and "every model's raw section verbatim" coexist.

## Step 7 — Stop

Report the verdict in chat and stop. Offer fixes; never start them. Fixing is Tony's separate instruction after reading the verdict — same as /signoff, and no invocation wording collapses this gate for the fixes themselves. The git gates are untouched: no push, no PR, no merge.

## The rules

1. **The gate is real.** Every slice `signed off`, or report-and-stop. Only Tony's invocation wording overrides, and the override is recorded.
2. **The ask is real.** Every run, wait for the answer. No remembered answers, no silence-defaults. Outside sends happen only on this run's answer.
3. **Secrets are physically absent.** Outside reviewers read the tracked-files-only export, never the working tree. No exceptions, no "it's probably fine."
4. **Cold means cold.** No prior verdicts, no chat context, no cross-reviewer leakage in any packet.
5. **Nothing unverified lands in the verdict.** Every outside finding is verified or it stays in the appendix. `Refuted: N` is always reported.
6. **Survivors continue.** A dropped reviewer is recorded, never papered over; the local review always runs.
7. **One write.** The verdict doc, dated, never overwriting. The build plan and its cards belong to the other stations.
8. **Stops at the verdict.** No fixes, ever, from this skill.
9. **/signoff is the law of review mechanics.** Where this file is silent, its SKILL.md governs; nothing here restates it to drift.
10. **Interactive only.** /vertical runs with Tony present to answer the gate, the ask, and the base — never headless, never from a script or cron.

## Output

```
VERTICAL: <build doc> @ <base>..<head>
Verdict: <SIGNED OFF | SIGNED OFF WITH CONDITIONS | REJECTED>  ·  per /signoff's mapping
Reviewers: local + <list | none>  ·  Dropped: <who — why | none>  ·  Refuted: N
Doc: <path to the verdict doc>

Bottom line: <2-3 sentences — the build's state and what to do next.>
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```

When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

## What NOT to do

- Don't run with any slice short of `signed off` unless Tony's own invocation said to — and record it when he does.
- Don't send anything outside without this run's answer to the ask — no defaults, no memory.
- Don't point an outside tool at the live working tree — export tracked files or don't send.
- Don't put prior verdicts, chat context, or one reviewer's output in another's packet.
- Don't let an unverified outside finding into the verdict section — appendix only.
- Don't change a pinned model id without Tony's word, and never mid-run.
- Don't treat an empty agy response as success — it is the failure signal.
- Don't fix anything, don't touch the build plan or its cards, don't write a second file.
- Don't push, open a PR, or merge — the git gates are Tony's, always.
