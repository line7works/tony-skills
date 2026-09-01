---
name: inspect
description: The plan-check station — adversarial review of a /blueprint build doc BEFORE /build runs it, by an inspector chosen at summon. STRICTLY user-invoked, only when Tony types /inspect; never auto-invoke or suggest-invoke, no matter how ready a fresh blueprint looks.
---

# Inspect

The building department. `/blueprint` draws the plans, `/build` frames them, `/signoff` inspects the framing — but until now nobody checked the blueprints against code before ground broke. `/inspect` is that plan check: one build doc, reviewed adversarially before /build treats it as law. Its slot in the loop: /precon → /blueprint → /inspect → /build. A bad plan approved is the loop's most expensive defect, because /build faithfully builds the mistake.

**The spine.** There is no spec above the spec, so the rubric is three fixed lenses — traceability, the code book, and repo reality — and the findings come from fresh inspectors, never this session: the summoning session may be the very session that drafted the doc, and the drafter does not stamp his own plans. The inspector's mandate is to find reasons to REJECT the plan; a clean verdict must state what it hunted for and failed to find.

**The one unforgivable move is inspecting the doc solo and calling it a plan check** — or its quieter twin, feeding the inspectors a summary instead of the record. The packet is always the actual docs, never this session's account of the discussion: a summary is a faux-context vector into the very inspection meant to catch faux context.

**/signoff's SKILL.md is the law of review mechanics wherever this file is silent** — finding shape (claim · location · concrete failure scenario · severity · confidence), verify-before-reporting (CONFIRMED/PLAUSIBLE, `Refuted: N`), the severity → verdict mapping, report-don't-repair, and the additive-ledger doctrine. Nothing here restates it to drift. One deliberate exception, stated so it can't be imported by silence: **/signoff's Step 0 model floor does not bind here.** Tony's ruling (2026-08-30): the lane choice at the ask is this skill's floor, and the model-named stamp is the compensating trust label — a below-Opus inspection is legal when Tony picks that lane, and the stamp is what keeps it from ever passing as more than it was.

## Step 1 — Gate and hunt

The invocation names a build doc, or the skill hunts the current repo under the same two-source narrowing /vertical uses — a deliberate narrowing of /build's wider hunt, so don't "fix" it back: `docs/<feature>-build-plan.md`, then any phase/slice doc under `docs/` or `plan/`. Nowhere else. /inspect reviews **written docs only**: a plan that lives only in this session's chat is not inspectable — writing it out here would package this session's summary, the faux-context vector rule 3 forbids — so say so, point at /blueprint, and stop. A hunt with zero candidates is a report-and-stop, nothing further asked (there is nothing to inspect); more than one candidate is a list-and-ask, never a silent pick.

Then hunt the scope doc **by glob, never by guessed slug** — precon's slug and blueprint's feature name are set independently and do differ (bitten live 2026-08-30): every `docs/*-scope.md` in the build doc's repo plus every `~/Documents/*-scope.md` (precon's two locations; a build doc summoned by absolute path outside any repo gets its own directory's `*-scope.md` plus the `~/Documents` glob). Match candidates to the feature by their Intent lines; an ambiguous match is a list-and-ask. Only a no-candidates result triggers the no-record rule, and the verdict's Scope doc field then names the hunt that came up empty. The scope doc is the traceability lens's record.

- Build doc missing or unreadable: report and stop. Nothing else is a gate failure — a doc with missing sections or malformed forms is exactly what the code-book lens exists to find, so it inspects.
- Slices already carrying a `Status:` beyond `not started`: still inspects, with a one-line note that construction already started.
- No scope doc: still inspects, under the no-record rule (Step 4).

## Step 2 — The ask

Every run, before any inspection work, one plain-text numbered question (never harness question UI):

1. **Claude** (➡️ recommended) — fresh subagents on this account.
2. **GPT** — `gpt-5.6-sol` via the codex MCP.
3. **Gemini** — `gemini-3.1-pro-high` via the antigravity MCP.
4. **DeepSeek** — `deepseek/deepseek-v4-pro` via OpenRouter (known limit: fails on plans of real size until jpb's script gains an output budget — see its recipe).
5. **Qwen (local)** — `qwen-code` on this machine's Ollama, free and offline.

One paper inspector per run — Tony's either/or. An answer naming several lanes is several runs: execute them one at a time in the named order, each with its own packet directory, verify pass, verdict block, doc writes, and stamp — never one merged consensus run (that is /jpb and /vertical territory). The skill always waits for the answer — silence never proceeds, and the recommendation is a recommendation, not a trigger. The answer applies to this run only; nothing is remembered between runs, and every external send in this skill is authorized by this run's answer and nothing else. Pinned ids change only on Tony's word, never mid-run.

**The lane-down rule.** A lane that cannot run — MCP disconnected, `OPENROUTER_API_KEY` unset (check with `[ -n "$OPENROUTER_API_KEY" ] && echo set` and NOTHING else — never print the key), Ollama down, a guard-failed or empty response — is reported with the specific failure and the ask is re-asked. Never silently substitute a different lane.

## Step 3 — The lenses

The packet: the build doc and the scope doc (when one exists), by path, verbatim — never a summary, never chat context, never this session's reasoning about either.

Three lenses, none of them ever this session. In the **Claude lane**, each is a fresh subagent (general-purpose, launched together in one message); in an **outside lane**, the chosen model covers the two paper lenses via the packet (below) and only repo-reality runs as a local subagent — never both origins for the same lens, or Claude findings land under an outside model's stamp:

- **Traceability** — every requirement, rationale, and criterion in the build doc traces to the scope doc or the repo. The number one hunt is faux context: plausible detail the record never established, presented as settled. /blueprint names it the one unforgivable move; this lens exists to catch it.
- **Code book** — the doc graded against /blueprint's live SKILL.md (`~/Developer/tony-skills/plugins/blueprint/skills/blueprint/SKILL.md`), read at run time and cited as the code, never paraphrased from memory: checkable criteria (would a grader know pass from fail), self-containedness (the builder-who-wasn't-in-the-room test), slice integrity (dependency order, ends wired in, independently verifiable, ceremony scaled), and the exact load-bearing forms downstream stations key on (section names, `Status:` labels, the ledger scaffold, ·-separated fields).
- **Repo reality** — the paths, components, test commands, and conventions the doc names exist as claimed. This lens always runs as local Claude, in every lane present or future, because an outside model can't walk the site.

Findings come back in /signoff's shape: claim · `<doc-path>:<line>` (repo `file:line` for repo-reality findings) · concrete failure scenario — what /build would wrongly build, or what a grader couldn't check · severity · confidence. Inspectors report everything; filtering belongs to the verify pass, and it is the session's.

**Outside lanes (GPT, Gemini, DeepSeek, local Qwen).** The chosen outside model runs the two paper lenses via `assets/inspect-mandate.md`; the repo-reality subagent still runs locally and its findings merge into the same verdict and block. **The packet, one rule for every lane:** create a FRESH scratch directory for this lane's run and write `packet.md` into it — the mandate with its placeholders filled verbatim (`[CODE_BOOK]` = /blueprint's live SKILL.md, `[BUILD_DOC]` = the build doc, `[SCOPE_DOC_OR_NO_RECORD]` = the scope doc or the literal line `NO RECORD — no scope doc exists for this feature.`), each filled document with line numbers prefixed (`N: `) so the inspector's `<doc>:<line>` citations have ground truth. The directory holds `packet.md` and nothing else, one directory per lane per run — never shared, never reused (a shared dir let one lane's response land where another could read it, bitten live 2026-08-30). Size check before any send: `wc -c packet.md`, and bytes/3.5 is the token estimate — over a lane's window (qwen: 64k tokens ≈ 220KB), report too-big and re-ask, never silently truncate. Never in the packet: repo code, chat context, session summaries, prior inspection output, another reviewer's output — cold means cold; the inversion vs the siblings, stated so nobody "fixes" it back: jpb starves its boxes of everything, /vertical feeds them the whole repo, **/inspect feeds them only the doc packet**. Transports reuse jpb's recorded recipes (`~/Developer/tony-skills/plugins/jpb/skills/jpb/assets/box-runners.md`) with `packet.md` as the payload:

- **GPT** — `mcp__codex__codex` with exactly: `model: "gpt-5.6-sol"`, `base-instructions` = the full text of `packet.md`, `prompt` = "Inspect the build doc per your instructions and report every finding.", `sandbox: "read-only"`, `cwd` = the packet directory, `config: {"web_search": "disabled"}` (string enum). The `cwd` deliberately deviates from box-runners' neutral-empty rule — it anchors the read-only sandbox at a directory holding only the packet the model already has; do not "fix" it back. Parity line: `web_search: disabled`.
- **Gemini** — `mcp__antigravity__ask_gemini` with exactly: `model: "gemini-3.1-pro-high"` (the `-high` suffix IS the effort setting — never also pass `effort`), `prompt` = the full text of `packet.md`, `cwd` = the packet directory, `skip_permissions` omitted. An EMPTY response is a FAILED run (a fully-denied agy run still reports SUCCESS); content decides over the status flag — a non-empty mandated-format report delivered under an ERROR status is a survivor with the anomaly recorded. Parity line (adapted from box-runners for this lane's cwd): `skip_permissions off, cwd = packet dir only, non-empty response`.
- **DeepSeek** — `~/Developer/tony-skills/plugins/jpb/skills/jpb/assets/openrouter-box.sh deepseek/deepseek-v4-pro <packet dir>/packet.md <packet dir>/out.md`. `OPENROUTER_API_KEY` from the environment under the never-print rule; the script's own guard (HTTP 200, no top-level error, `finish_reason == "stop"`, non-empty content, exit 1 on FAILED) is the failure signal; parity line: `no :online suffix`. **Known limit, verified live 2026-08-30:** the script hardcodes `max_tokens` 8000 and DeepSeek reasons before writing — on an inspection-size packet the budget dies in thinking and the guard fails with `finish_reason=length`. Until jpb's script grows a budget parameter (its file, not this skill's), this lane completes only on small plans; the ask's roster line carries this caveat so Tony picks it knowingly.
- **Qwen (local)** — never pass the packet through a shell argument: doc content carries backticks and `$()`, and an inlined `-p "<packet>"` is a local command-execution path (rejected 2026-08-30). The recipe: `cd` into the packet directory and run `ollama launch claude --model qwen-code -- -p "You are the inspector. Read packet.md in this directory and execute its mandate exactly. Report per its How-to-report section." --strict-mcp-config --mcp-config '{"mcpServers":{}}'` — the fixed prompt string is the only thing the shell sees; qwen reads the packet itself with its built-in file tools. The reply arrives on stdout after a telemetry warning line — content decides, and an empty reply is a FAILED run. Honesty note this lane carries into the verdict: unlike GPT's read-only sandbox, qwen's isolation is by instruction only (a `-p` harness can read files outside the packet dir); the stamp's trust label is the containment.
- Never verify or debug any lane by reading `~/.zshrc` — the OpenRouter key lives beside the qwen alias there, and a read captures it in a transcript (it happened 2026-08-30; the 2026-08-11 leak forced a rotation). The recipes above are the reference; the alias is not.

**Raw output.** Before any triage, write the outside inspector's output VERBATIM to `~/Documents/inspect-raw/<feature>-inspect-<YYYY-MM-DD>-<lane>.md` — `<feature>` is the build doc's filename minus `-build-plan.md`, `<lane>` is gpt | gemini | deepseek | qwen, and a same-day repeat on the same lane appends `-2`, `-3`, never overwrites. Create the directory on first use. Banner at the top: *"Raw inspector output — unverified. Findings absent from the chat verdict were refuted or could not be verified. Nothing in this file has standing."* The chat verdict carries the pointer in its `Raw:` field. The Claude lane writes no raw file — its subagent reports live in the session, like /signoff's reviewers. Then the verify pass: **every outside finding — every severity, not just BLOCKER/MAJOR — is adversarially verified** against the actual docs and repo before it reaches Tony (line-number cites are checked against the numbered packet; a citation that matches nothing is a refutation unless the session locates the real site and says so on the finding). An outside QUESTION finding — the mandate's severity for items unverifiable against a missing or silent record — routes to the Questions machinery whatever the scope-doc situation: no CONFIRMED/PLAUSIBLE stamp, a `QUESTION` ledger line, never gating. The stamp names the lane's pinned id per Step 5.

## Step 4 — Verify and adjudicate

- Dedupe on location + claim; convergence across lenses is signal, noted once on the merged finding.
- Verify every BLOCKER and MAJOR yourself against the cited lines before it reaches Tony: stamp CONFIRMED or PLAUSIBLE; drop what you refute and count it (`Refuted: N`). Locationless concerns never reach the verdict.
- **The no-record rule.** With no scope doc, an untraceable requirement is NOT evidence of invention — the inspector can't see a chat, and absence of record is not proof of faux context. Those findings become Questions to Tony ("unverifiable — confirm this was decided"), never automatic BLOCKERs, and the verdict states plainly that the run is weaker without a precon doc. The skill works best precon-first.
- Severity carries plan-stage meaning: **BLOCKER** — the plan as written would build a mistake: an invented requirement presented as settled, an uncheckable criterion on a load-bearing item, a wrong repo fact a slice depends on, a slice-integrity break, or a missing/malformed load-bearing form that breaks a downstream station. **MAJOR** — a real doc defect fixable in place. **MINOR** — a rough edge.

## Step 5 — Verdict and the two writes

Verdict per /signoff's mapping, in plan-check words so the stations never blur: **APPROVED** (no BLOCKER or MAJOR) · **APPROVED WITH CONDITIONS** (no BLOCKERs; named MAJORs fixed before /build) · **REJECTED** (any BLOCKER).

Report in chat (Output below), then exactly two doc writes, both additive, then stop:

1. **The punch-list block.** `### <YYYY-MM-DD> — inspect: plan` appended at the ledger home's tail — the home is where the doc's punch-list blocks already live, or the `## Punch list` section (created when absent), per /signoff's home rule. One ·-separated line per surviving finding: severity · `<path>:<line>` · claim · concrete failure scenario · <inspector model>. Questions land in the same block as `QUESTION · <path>:<line> · what needs confirming · <inspector model>` lines — no severity, never gating, never swept — so a precon-less run's confirm-list survives the chat. A clean run — zero surviving findings AND zero open Questions, the stamp's own definition — still writes the block, holding the single line `clean — no surviving findings or questions · <inspector model>`; a zero-finding run with open Questions writes its QUESTION lines and no clean line. A **re-inspection's** block additionally carries one line per still-open prior inspect entry — severity · `<path>:<line>` · (claim) · fixed | not fixed — the recheck-format closure record the loop's open-filter honors, so plan-stage findings never read as open forever.
2. **The stamp.** `Plan: inspected <YYYY-MM-DD> by <model> · <N BLOCKER · N MAJOR · N MINOR>` — append `· N QUESTION` when any are open, and write `clean` in place of the counts only when there are zero findings AND zero open Questions. Placement, one rule: directly below the previous `Plan: inspected` line when one exists, so history reads top to bottom; on a first inspection, directly after the `Out of scope:` block (the header line and any list lines continuing it); in a doc with no `Out of scope:` at all, directly above the first `## Slice` heading. Prior stamp lines are never rewritten. `<model>` is the id the inspectors were **launched** on: an outside lane's pinned id, or — Claude lane — the session's own model id, which fresh subagents launched without an override inherit; if a configured subagent default is known to differ, name that id instead. Never write an id you didn't launch: the stamp is the trust label, and a lightweight inspection must never be mistakable for a heavyweight one.

Never: a `Status:` line, a verdict word in the doc, an edit to the plan's content, a fix, a re-slice. Tony adjudicates the findings — a plan finding can be wrong; the inspector has less context than he does. The drafting session amends the doc on his word, and re-inspection is a fresh /inspect run. No invocation wording collapses the fixing gate.

## The rules

1. **Strictly summon-only.** /inspect runs when Tony types it, never because a blueprint just landed and looks ready.
2. **Fresh inspectors originate; the session merges, verifies, adjudicates.** Inspecting the doc solo and labeling it a plan check is this skill's unforgivable move.
3. **The packet is the record.** Actual docs by path, verbatim — never a summary, never chat context.
4. **The ask is real.** Every run, wait for the answer; per-run only, nothing remembered.
5. **Evidence or it doesn't count.** Every finding carries its `path:line`; every BLOCKER/MAJOR is verified before Tony sees it (/signoff law).
6. **No record is not invention.** Untraceable items without a scope doc become Questions, never automatic BLOCKERs.
7. **Stops at the verdict.** Two additive writes, nothing else touched — no fixes, no plan edits, no `Status:` lines, no verdict words in the doc.
8. **The stamp names the model.** Every verdict, chat and doc, carries the id the inspectors were launched on, per Step 5's stamp rule.
9. **/signoff is the law where this file is silent.** Nothing restated to drift.
10. **Anti-rubber-stamp.** A clean verdict states what it hunted and failed to find — mandatory, every run.

## Output

Report in chat:

```
INSPECT: <doc path>
Verdict: APPROVED | APPROVED WITH CONDITIONS | REJECTED
Inspector: <lane · model id>  ·  Scope doc: <path | none — no-record rule applied>  ·  Refuted: N
Raw: <path to the verbatim raw file | n/a — Claude lane>
Findings: N BLOCKER · N MAJOR · N MINOR

Bottom line: <2-3 sentences — the plan's state and what to do next.>

BLOCKERS   <severity · path:line · claim · scenario · CONFIRMED/PLAUSIBLE>
MAJOR
MINOR
Questions: <no-record confirmations and adjudication calls for Tony — only when any>
Hunted and held: <what the inspectors attacked that held up — mandatory in every verdict>
Next: <under CONDITIONS or REJECTED — Tony adjudicates, the drafting session amends, fresh /inspect; under APPROVED — /build when ready>
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```

Omit empty severity sections; `Hunted and held` is mandatory in every verdict. When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

## What NOT to do

- Don't auto-invoke, suggest-invoke, or trigger from a fresh blueprint's existence — Tony types it or it doesn't run.
- Don't inspect the doc yourself and call it a plan check — fresh subagents originate, always.
- Don't summarize the discussion into the packet — actual docs only.
- Don't proceed without the ask's answer, and don't remember it between runs.
- Don't let a locationless finding — or an unverified BLOCKER or MAJOR — reach the verdict. Claude-lane MINORs pass through unverified, per the law; OUTSIDE findings are verified whatever their severity (Step 3's raw-output rule).
- Don't auto-BLOCKER untraceable items when no scope doc exists — those are Questions.
- Don't fix, re-slice, or edit the plan's content — Tony adjudicates, the drafter amends.
- Don't touch a `Status:` line or write a verdict word into the doc — the stamp and the punch-list block are the only writes.
- Don't borrow /signoff's verdict words — APPROVED-family here, SIGNED OFF-family there, never blurred.
- Don't put repo code, chat context, or another reviewer's output in an outside packet — docs only, cold means cold.
- Don't substitute a lane when the chosen one is down — report the failure and re-ask.
- Don't print `OPENROUTER_API_KEY`, ever — existence check only.
- Don't triage an outside report before its verbatim raw file is written, and don't let an unverified outside finding reach the verdict.
- Don't change a pinned model id without Tony's word, and never mid-run.
