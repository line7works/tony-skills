---
name: wargame
description: Adversarial planning/pre-mortem for any target — a new project, an existing feature, or a planned change. Produces one canonical war-game doc with ranked, verified failure modes, phased plan with kill criteria, and plain-language decision questions. Use when the user says "war game <target>" or asks for a failure-first plan or adversarial review.
---

# War Game

Plan or stress-test the target as a war game: assume the happy path is a lie, enumerate how things fail, and — this is the spine — **convert the top failures into something real** (a verified code check, a test, or a spike). A war game that stops at a list of worries is theater; refuse to produce that.

## Step 0 — Model floor (hard gate)

This skill requires **Opus-class reasoning or better** (Opus, Fable/Mythos, or any successor tier above Opus). Check what model you are:

- At or above the floor → proceed.
- Below the floor (Haiku, Sonnet, or equivalent) → STOP. Tell the user: "War game needs Opus or greater; this session is running <model>. I can give you a lightweight failure checklist instead, or rerun /wargame on a stronger model." Do not run the full methodology on a lesser model and label it a war game.
- Adversary agents (FULL depth): every one is a `/readers` call on row `claude-session` that carries the floor as `floor: opus` and this session's own model id as `session_model` — readers refuses a session below the floor as `floor-refused` and never upgrades silently; the floor is passed, never assumed. No model id is ever typed into a request: nothing is pinned below `opus` because nothing is pinned at all, and each adversary inherits this session's model. A call that comes back `floor-refused` means this session is below the floor: STOP as above.

## Step 1 — Identify the target and pick the mode

Restate the target in one sentence and classify it. If the target is ambiguous, ask ONE clarifying question before anything else.

| Mode | When | Where rigor comes from |
|---|---|---|
| **GREENFIELD** | Nothing exists yet (new project/product/feature with no code) | Structure: phases, assumptions, kill criteria, take budgets. Failures are imagined — the anti-theater rule carries all the weight. |
| **EXISTING** | The target is built and in the repo | Verification: every claimed failure mode is checked against real source and stamped with a verdict. Imagination without file:line evidence is worthless here. |
| **CHANGE** | A planned modification to existing code (migration, refactor, new slice on a built system) | Hybrid: map the real terrain first (verified), then war-game the change against it. |

Auto-detect by checking whether the target exists in the codebase. The user can force a mode ("war game this as greenfield").

## Step 2 — Pick the depth

- **QUICK** (default): solo pass. Terrain map, ranked failure list, verify/spike the top 3–5, short doc. Right for a single feature, a slice, a small tool.
- **FULL**: parallel adversary agents, then hand-verification, then the doc. Use when the user says "full", "thorough", "deep", or the target is a whole system/subsystem spanning many files or an entire new product.

State which depth you chose and why in one line before starting.

## The rules (apply in every mode)

1. **Anti-theater rule (the spine).** Rank every failure by `likelihood × blast radius` (H/M/L each). Every HIGH-ranked failure MUST convert into one of: (a) a verified code check with file:line evidence, (b) a named test to write (with the deny-side condition it pins), or (c) a spike experiment with a pass/fail question. Failures that remain table rows are explicitly marked `UNCONVERTED — accepted risk` so the reader sees the residue. Cap the master table at what you can rank honestly; 15 ranked and converted beats 60 speculative.
2. **Terrain-fidelity rule.** Name the single hardest/riskiest component of the target, out loud, early — and spend disproportionate depth there. The riskiest part getting one sentence is the classic war-game failure; make it structurally impossible.
3. **Kill criteria.** Every phase states what result would make you ABANDON the approach (not just retry). Plans without exits become sunk-cost machines.
4. **Take budgets.** Every phase gets a max-attempts number; exceeding it escalates to the human instead of grinding.
5. **Deny-side exit criteria.** Exit criteria must be verifiable by a named command, test, or observable check — and where a guard is involved, the criterion is that removing the guard FAILS something. "It works end to end" is not an exit criterion.
6. **Scope ladder.** Define the MVP spine before phase 1 — the smallest shippable/provable core. The war game covers the spine first; the full vision hangs off it as later phases.
7. **The boring dimensions.** The failure sweep must include: money (per-unit cost, quotas, rate limits), data (PII, retention, backup/restore), concurrency/races, and the business metric (what success is *for* — a plan can pass every technical gate and still fail at its purpose; say what gets measured).
8. **Porting hazards.** Wherever the plan assumes habits from a different stack/tool/API than the one chosen, call the difference out explicitly so nothing gets ported blindly.
9. **Openings vs defects (EXISTING/CHANGE modes).** Unbuilt-by-design is not a defect. Catalogue such gaps in an **Openings register** — no fixes prescribed, no product behavior invented for areas the owner hasn't designed yet. Ask-or-flag, never assume.
10. **Cold-start writing.** The doc must be executable by an agent (or human) with zero context from this conversation: preamble with what/why, terrain map, no unexplained codenames.
11. **One canonical artifact.** A single markdown doc. In a git repo: `docs/wargames/<target-slug>.md` (create the dir). Outside a repo: current directory, same name. Never maintain a second synced copy; a visual/HTML rendering is produced only if the user asks, generated FROM the doc.

## FULL depth — the fan-out

The adversaries are one `/readers` fleet (`readers-protocol: 1`; every request carries `protocol_version: 1`): 4–6 calls launched together in one summon, each with a **distinct lens** as its mandate — diversity catches what redundancy can't. Before the fleet: mint a FRESH run id for this run — one path segment, characters `[A-Za-z0-9._-]` only (readers refuses anything else as `invalid-request`), e.g. `wargame-<target-slug>-<YYYYMMDD>-<four hex>`; make the run directory (`mktemp -d`, a scratch path outside the repo); write each lens's brief to `<run dir>/<lens>.md`; then `/readers suggest claude-session --run <run id> --run-dir <run dir>/readers --floor opus` (the floor at suggest drops a remembered typed pick on the row with a note; without it every floor-bound call below is refused as `unknown-model`). `suggest` shows the placeholder `session` for this row: the model that runs is this session's own, the id its system prompt names. Each adversary is one call: `row: claude-session`, `profile: repo-with-tools` (readers' fixed instruction: the adversary may read files and run tests inside the workspace, writes only to scratch and ignored caches, never a tracked file; no web tools, no spawned agents, no summoning `/readers`; an execution the sandbox stopped is reported as "verification blocked", never marked checked), `workspace` the repo root (outside a repo, the current directory), `documents` the target's own document when the target is one (a scope or plan doc in GREENFIELD or CHANGE mode) and nothing else, `mandate` `<run dir>/<lens>.md` — the lens, the target as Step 1 restated it, the mode, and the finding shape below; never this skill's own text, never the session's terrain map or findings — `floor: opus`, `session_model` the exact model id this session's system prompt says it is powered by, `run_id`, `run_dir` `<run dir>/readers`, `call_id` `<run id>-<lens>` (single-use), and no `raw_path` (the doc is built from each call's `raw_text`; the runner's `raw.md` and sidecar under `<run dir>/readers/<call id>/` are the evidence and are never edited), no `effort` and no `model` (an unpinned `repo-with-tools` call runs as a plain subagent inheriting the session model through the Agent tool — no Workflow tool is needed and no `.readers/` copy lands in the repo), no `isolation` (adversaries read and run; they never mutate the checkout), and no `authorized` (a Claude row never carries it). A call whose status is `transport-failed`, `empty`, or `incomplete` is re-sent once as `<run id>-<lens>-2` (a call id is single-use); a second failure, or a deterministic refusal (`unknown-model`, `invalid-request`, `lane-unavailable`, `profile-unsupported`, `version-mismatch` — the same request refuses the same way), drops that lens, named with its status in the doc's Verification log — never papered over; a rerun of the fan-out is a fresh run id with its own `suggest`. Default lenses; drop/swap per target:

- `security` — authz gaps, injection, trust boundaries, secrets
- `races` — concurrency, idempotency, partial failure, retry storms
- `data` — integrity, migrations, PII/retention, backup/restore, denormalization drift
- `cost-limits` — per-unit economics, rate limits, quotas, runaway loops
- `failure-ux` — what the human sees when it breaks: silent failures, swallowed errors, stuck states
- `terrain` (GREENFIELD only) — attack the assumptions: what does the plan believe about the platform/APIs/users that nobody verified?

Each adversary returns findings as: claim, where (file:line if EXISTING), failure scenario (concrete inputs → wrong outcome), severity — the mandate states that shape, and readers hands each call's report back verbatim as its `raw_text`. A check an adversary reports as "verification blocked" (the sandbox stopped an execution it needed) enters the Verification log as `verification blocked: <what the sandbox stopped>` — never as CONFIRMED, never silently dropped — and is yours to run by hand or to leave named as unverified. Then **you hand-verify every headline finding yourself before it enters the doc** — reviewers are fallible; in EXISTING mode read the actual source and stamp CONFIRMED / PLAUSIBLE / REFUTED. Convergence across independent lenses is signal; note it.

## The doc template

```
# War Game: <target>
> Mode: GREENFIELD|EXISTING|CHANGE · Depth: QUICK|FULL · Date · Model
> Verdict: one-paragraph bottom line (sound? risky where? build/no-build posture)

## Terrain map        — what exists / what's assumed; THE HARDEST COMPONENT named + why
## MVP spine          — the smallest provable core (GREENFIELD/CHANGE)
## Decisions          — LOCKED (chosen, with rationale) and NEEDED (see Decision loop)
## Phases             — per phase: objective · optimistic assumption · pessimistic
                        assumption · likely failures (detection + recovery) ·
                        exit criteria (deny-side, named commands/tests) ·
                        take budget · kill criteria
## Master failure table — ranked L×B; every HIGH row → converted-to column
                        (verified <file:line> / test <name> / spike <question>)
                        or `UNCONVERTED — accepted risk`
## Verification log   — EXISTING/CHANGE: each headline claim → CONFIRMED/PLAUSIBLE/REFUTED
                        with evidence
## Openings register  — unbuilt-by-design gaps, no prescriptions (EXISTING/CHANGE)
## Porting hazards    — stack-habit differences called out
## Suggested order    — build/fix sequence with S/M/L sizing and dependency notes
```

Sections that don't apply to the mode are omitted, not left empty.

## Decision loop (how NEEDED decisions reach the user)

The user may not read the doc. After drafting, surface every NEEDED decision as a **numbered plain-language question in chat** — self-contained (no doc references required to answer), with your recommendation stated first and the trade-off in one or two sentences. Lock everything that has an obvious right answer yourself (record it under LOCKED with rationale); only genuine judgment calls — product behavior, risk appetite, scope — go to the user. After answers come back, fold them into the doc as LOCKED with the user's wording preserved where it matters.

## What NOT to do

- Don't write code or fixes — the war game is a plan/assessment. Building is a separate, later instruction.
- Don't pad the failure table to look thorough. Ranked-and-converted or cut.
- Don't prescribe product behavior for areas the owner said are undesigned (Openings register instead).
- Don't produce the HTML/visual version unsolicited.
- Don't run the full methodology below the model floor.
- Don't trust adversary findings unverified — headliners get your own eyes on the source, and a "verification blocked" check is logged as blocked, never counted as verified.
- Don't type a model id, effort, or `authorized` into an adversary's request, and don't hand an adversary your terrain map or another adversary's findings — the mandate and the documents are all it gets.
- Don't reuse a run id or a call id — a re-send is a fresh call id, a rerun a fresh run id with its own `suggest`.
