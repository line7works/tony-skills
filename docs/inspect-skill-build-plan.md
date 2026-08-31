# Inspect skill — build plan (2026-08-30)

Intent: /inspect is the plan-check station of Tony's build loop — the building department reviewing the blueprints against code before ground breaks. /signoff inspects the framing against the plans; today nobody inspects the plans themselves, and a bad plan approved is the loop's most expensive defect because /build treats the doc as law and faithfully builds the mistake. /inspect reviews one /blueprint build doc before /build runs it. Its slot, per Tony's confirmed workflow (2026-08-30): talk the idea → /precon → /blueprint when comfortable → /inspect → /build. Strictly summon-only. There is no spec above the spec, so the inspection runs three lenses: **traceability** (every requirement traces to the upstream record — the /precon scope doc and the repo; faux context is the number one hunt), **code book** (the doc graded against /blueprint's own rules: checkable criteria, self-containedness, slice integrity, exact load-bearing forms), and **repo reality** (do the named paths, components, commands, and conventions actually exist). The inspector is chosen at summon, per run — Claude on this account (fresh subagents), or an outside model: GPT, Gemini, DeepSeek, or local Qwen (Tony's ruling 2026-08-30, superseding an earlier Opus-only-verdict position; the cost containment is that every verdict is stamped with the inspector's identity). The skill stops at the verdict: Tony adjudicates the findings, the drafting session amends the doc, and re-inspection is a fresh /inspect run.

Constraints: The deliverable is one skill directory `~/.claude/skills/inspect/` — `SKILL.md` plus `assets/inspect-mandate.md` — authored in house style (intro with a named spine, numbered steps, "The rules", output block, "What NOT to do", and the SKILL NOTE convention paragraph, matching the voice and structure of `~/.claude/skills/signoff/SKILL.md` and `~/.claude/skills/vertical/SKILL.md`). Loop skills live unversioned in `~/.claude/skills/` (no git repo; Time Machine covers backup), which is why this plan lives in `~/Documents/skill-lab/` beside the prior skill build plans. **/signoff's SKILL.md is the law of review mechanics wherever /inspect's file is silent** — finding shape (claim · location:line · concrete failure scenario · severity · confidence), verify-before-reporting (CONFIRMED/PLAUSIBLE, `Refuted: N`), the severity → verdict mapping, report-don't-repair, and the additive-ledger doctrine — /inspect states this the way /vertical's rule 9 does, and never restates mechanics to drift. Strictly user-invoked, never auto- or suggest-invoked (precon's posture; the description must not invite auto-invocation). All asks are plain-text numbered questions with a ➡️ recommendation, never AskUserQuestion (house rule; the Grill Marks dossier records harness question UI corrupting interview sessions). External sends are authorized only by this run's answer to the lane ask — nothing remembered between runs, pinned model ids change only on Tony's word and never mid-run, and `OPENROUTER_API_KEY` is never printed (existence check is `[ -n "$OPENROUTER_API_KEY" ] && echo set` and nothing else — the 2026-08-11 key leak is why). No runnable test suite applies to a skill file; every acceptance criterion below verifies by manual smoke run, per house precedent.

Out of scope:
- Wiring /build or /ship preflight to the `Plan: inspected` line — reason: Tony's accepted design keeps the stamp advisory, warn-never-block; adding the preflight read is a separate small edit to those skills on his word, after live /inspect runs prove the line's shape.
- A Grok lane — reason: the same OpenRouter route exists in jpb's box-runners.md, but Tony never named Grok for this skill; add on his word, the transport is already recorded.
- Multi-inspector consensus in one run — reason: Tony's words were "either/or", one paper inspector per run; /jpb and /vertical own multi-model territory.
- jpb-style scrubbing of the packet — reason: rejected in discussion — scrubbing paths and names would break the traceability lens's whole job, and /vertical already sends the full tracked code outside on a per-run word while /inspect sends only two plan docs; the per-run lane answer is the authorization.
- A doc-flavored /recheck — reason: accepted design; /recheck is slice-shaped and flips Status cards, a plan re-inspection is just a fresh /inspect run, one less skill to maintain.
- Any auto-invocation of /inspect from /blueprint's read-back, or /blueprint edits of any kind — reason: summon-only; this build touches no other skill's file.
- DeepSeek/Qwen lanes for /signoff or /vertical — reason: this build touches only /inspect; extending sibling rosters is its own discussion.

## Slice A — core skill, Claude lane end to end
Goal: /inspect exists and completes a full inspection through the Claude lane — gate, ask, three lenses via fresh subagents, verify pass, chat verdict, and the two ledger writes.
Requirements:
- R1 — `~/.claude/skills/inspect/SKILL.md` in house style per Constraints; the description marks it strictly summon-only (precon's wording posture).
- R2 — Gate and hunt: the invocation names a build doc, or the skill hunts the current repo per /build's doc tiers exactly as /vertical Step 1 does (`docs/<feature>-build-plan.md`, then phase/slice docs under `docs/` or `plan/`, then the plan established in this session; nowhere else; unresolvable means ask Tony). The skill also hunts the feature's matching scope doc (`docs/<idea>-scope.md`, precon's output, both precon locations). A build doc that can't be found or read is a report-and-stop; a build doc with missing sections or malformed forms is NOT a gate failure — malformed structure is exactly what the code-book lens exists to find. A doc whose slices already carry non-`not started` Status lines still inspects, with a one-line note that construction already started.
- R3 — The ask: every run, before any inspection work, one numbered plain-text question — which inspector — with the Claude lane as the ➡️ recommendation. The skill always waits; silence never proceeds; the answer applies to this run only (vertical's ask law). In this slice the selectable roster is the Claude lane alone, and the ask says plainly that the outside lanes land in the next slice; the ask machinery is written to take a roster so Slice B extends it without rework.
- R4 — The three lenses are pinned in the SKILL.md as the rubric, because there is no spec above the spec: (a) **traceability** — every requirement, rationale, and criterion in the build doc traces to the scope doc, the repo, or a recorded answer; the number one hunt is faux context, blueprint's own named unforgivable move; (b) **code book** — the doc graded against /blueprint's live SKILL.md (`~/.claude/skills/blueprint/SKILL.md`), read at run time and quoted as the code, never paraphrased from memory, covering at minimum: checkable criteria, the builder-who-wasn't-in-the-room test, slice integrity (dependency order, ends wired in, independently verifiable), and the exact load-bearing forms downstream stations key on; (c) **repo reality** — the paths, components, test commands, and conventions the doc names exist in the repo as claimed.
- R5 — Independence: findings originate from fresh subagents that did not draft the doc — never this session solo, because the summoning session may well be the drafting session, and the drafter does not stamp his own plans. The session's job is scope, packet, merge, verification, and adjudication, per /signoff's split. Lenses (a) and (b) are the paper review; lens (c) runs as its own local fresh subagent — in this slice and in every future lane, because an outside model can't walk the site.
- R6 — Finding shape and the verify pass follow /signoff's law: claim · `<doc-path>:<line>` (or `file:line` in the repo for lens-c findings) · concrete failure scenario stated as what /build would wrongly build or what a grader couldn't check · severity · confidence; the session reads the cited lines itself on every BLOCKER and MAJOR, stamps CONFIRMED or PLAUSIBLE, drops and counts refutations (`Refuted: N`); locationless concerns never reach the verdict.
- R7 — The no-record rule: when no scope doc exists, requirements that can't be traced become Questions to Tony ("unverifiable — confirm this was decided"), never automatic BLOCKERs — the inspector can't see a chat, and absence of record is not evidence of invention. The verdict states plainly that the run is weaker without a precon doc. The packet is always the actual docs: the summoning session never substitutes its own summary of the discussion, which would be a faux-context vector into the inspection itself.
- R8 — Severity carries plan-stage meaning and maps to the verdict per /signoff's table: **BLOCKER** — the plan as written would build a mistake (an invented requirement presented as settled, an uncheckable criterion on a load-bearing item, a repo fact a slice depends on that is wrong, a slice-integrity break, a missing or malformed load-bearing form that breaks a downstream station); **MAJOR** — a real doc defect fixable in place; **MINOR** — a rough edge. Verdict words: **APPROVED / APPROVED WITH CONDITIONS / REJECTED** — the plan-check stamp, deliberately distinct from /signoff's SIGNED OFF family so a chat log never confuses the stations.
- R9 — Stops at the verdict: /inspect never edits the plan's content, never fixes, never re-slices, and no invocation wording collapses that for the fixes. Tony adjudicates each finding (a plan finding can be wrong — the inspector has less context than he does); the drafting session amends the doc; re-inspection is a fresh /inspect. The anti-rubber-stamp rule applies: a clean verdict must state what it hunted for and failed to find, in a mandatory section.
- R10 — Doc writes, exhaustively two, both additive, Status lines never touched, no verdict word in the doc: (1) a punch-list block headed `### <YYYY-MM-DD> — inspect: plan` appended at the ledger home's tail (creating `## Punch list` when absent), one ·-separated line per surviving finding in /signoff's line format with the inspector named; (2) the stamp line `Plan: inspected <YYYY-MM-DD> by <model> · <N BLOCKER · N MAJOR · N MINOR | clean>` appended directly under the doc's `Out of scope:` header line — one new line per run, prior lines never rewritten, so the inspection history reads top to bottom.
- R11 — Output block in house style (`INSPECT:` header; doc path · verdict · lane/model · `Refuted: N` · finding counts; bottom line; findings by severity; Questions; the mandatory hunted-and-held section; `Next:`; `SKILL NOTE:` only when earned) plus the SKILL NOTE convention paragraph in the SKILL.md — included day one, per the precon lesson of shipping without it.
Acceptance criteria:
- AC1: a smoke run completes end to end — verify: manual: copy a real blueprint-format doc (e.g. `~/Documents/skill-lab/architect-skill-build-plan.md`) to a scratch location, summon /inspect on the copy by path, answer the ask with the Claude lane; confirm the ask appeared and waited, fresh subagents originated the findings (the session originated none), and the chat verdict carries the verdict word, `Refuted: N`, and the mandatory hunted-and-held section.
- AC2: the copy carries exactly the two writes in exact form — verify: manual: diff the copy against the original; the only changes are one `### <date> — inspect: plan` block with ·-separated lines and one `Plan: inspected <date> by <model> · <counts>` line under `Out of scope:`; every `Status:` line is byte-identical.
- AC3: the gate is honest — verify: manual: summon /inspect in a directory with no build doc; it reports and stops, asks nothing further, writes nothing.
Footprint: `~/.claude/skills/inspect/SKILL.md` (new)
Not in this slice: outside lanes, `assets/inspect-mandate.md`, the raw-output file (Claude-lane subagent output lives in the session like /signoff's reviewers).
Depends on: nothing
Status: signed off

## Slice B — outside lanes
Goal: the ask offers the full roster — GPT, Gemini, DeepSeek, local Qwen — each running as a cold paper inspector over a docs-only packet, with Claude's repo-reality pass still local and every outside finding verified before the verdict.
Requirements:
- R1 — Roster and transports pinned in the SKILL.md, reusing jpb's recorded recipes (`~/.claude/skills/jpb/assets/box-runners.md`) with /inspect's own inversion stated so nobody "fixes" it back: jpb starves its boxes of context, /vertical feeds them the whole repo, **/inspect feeds them only the doc packet — never code, never the working tree**. Web access stays OFF on every lane. The lanes:
  - **GPT** — `mcp__codex__codex`: `model: "gpt-5.6-sol"`, `base-instructions` = the composed mandate, `prompt` = one fixed review-request line, `sandbox: "read-only"`, `cwd` = the packet directory, `config: {"web_search": "disabled"}` (string enum); parity line recorded per /vertical.
  - **Gemini** — `mcp__antigravity__ask_gemini`: `model: "gemini-3.1-pro-high"` (the `-high` suffix IS the effort setting, never also pass `effort`), `prompt` = composed mandate + request, `cwd` = the packet directory, `skip_permissions` omitted. An EMPTY response is a FAILED run (a fully-denied agy run still reports SUCCESS), and content decides over the status flag (agy can report ERROR while delivering a complete response — a non-empty mandated-format review is a survivor with the anomaly recorded). Both traps verified live, recorded in box-runners.md and /vertical.
  - **DeepSeek** — jpb's `openrouter-box.sh`: model `deepseek/deepseek-v4-pro`, composed-prompt file carrying the mandate and the docs inline, out-file in the session scratchpad; `OPENROUTER_API_KEY` from the environment under the never-print rule; the script's own guard (HTTP 200, no top-level error, `finish_reason == "stop"`, non-empty content, exit 1 on FAILED) is the failure signal; parity line: no `:online` suffix.
  - **Qwen (local)** — Claude Code launched headless on the local model via `ollama launch claude --model qwen-code` with `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` (the `~/.zshrc` `qwen` alias is the reference invocation; the builder verifies the exact headless one-shot flags and records them in the SKILL.md). The packet must fit the `qwen-code` tag's 64k window: an over-budget packet reports too-big and re-asks, never silently truncates.
- R2 — The packet: `assets/inspect-mandate.md` with placeholders (the vertical-mandate pattern) + the build doc verbatim + the scope doc verbatim when one exists. Never in the packet: repo code, chat context, session summaries, prior inspection output, or another reviewer's output — cold means cold, and the docs-as-is ruling is Tony's (2026-08-30), authorized per run by the lane answer.
- R3 — The lane-down rule: a disconnected MCP, an unset key, a down Ollama, or a guard-failed/empty response is reported with the specific failure and the ask is re-asked; the skill never silently substitutes a different lane.
- R4 — The repo-reality lens (Slice A R5c) runs as a local fresh Claude subagent in every outside-lane run, and its findings merge into the same verdict and punch-list block as the paper inspector's.
- R5 — Verify before verdict, /vertical's law: every outside or local-model finding is adversarially verified by the session against the actual docs and repo before it reaches Tony — CONFIRMED/PLAUSIBLE stamped, refuted findings dropped and counted, and a hallucinated line citation is a refutation unless the session locates the real site and says so on the finding.
- R6 — Raw output: before any triage, the paper inspector's output is written VERBATIM to `~/Documents/inspect-raw/<feature>-inspect-<YYYY-MM-DD>.md` (the precon cold-read precedent) under /vertical's no-standing banner, and the chat verdict carries the pointer. Tony reviews the raw take; the session never filters invisibly.
- R7 — The stamp names the actual model: the `Plan: inspected ... by <model>` line and the chat verdict carry the paper inspector's pinned id (Claude lane: the model id the fresh subagents actually ran on). A lightweight inspection must never be mistakable for a heavyweight one — Tony stays the trust layer.
- R8 — Pinned ids change only on Tony's word, never mid-run (jpb's standing rule, restated in the SKILL.md).
Acceptance criteria:
- AC1: one live outside-lane smoke on the Slice A copy doc, lane chosen by Tony at the ask (➡️ recommend Qwen: free and local) — verify: manual: the packet directory contains only the mandate and the docs; the raw file exists verbatim at the R6 path; the verify pass produced CONFIRMED/PLAUSIBLE stamps and a `Refuted: N` count; the appended `Plan:` line names the pinned model id.
- AC2: the lane-down rule holds — verify: manual: pick a deliberately broken lane (e.g. DeepSeek with `OPENROUTER_API_KEY` unset in the environment); the skill reports the named failure and re-asks; nothing is sent, no substitute lane runs.
- AC3: the ask presents the full roster with the Claude-lane ➡️ recommendation and per-run-only wording — verify: manual: read the ask as it appears in AC1's run.
Footprint: `~/.claude/skills/inspect/SKILL.md` (extend), `~/.claude/skills/inspect/assets/inspect-mandate.md` (new)
Not in this slice: a Grok lane, preflight wiring, consensus runs (all Out of scope).
Depends on: Slice A
Status: signed off

## Build assumptions

### 2026-08-30 — build: Slice A
- Claude lane runs three fresh subagents, one per lens (the spec pins fresh subagents and the lens split but not the count) · builder call
- AC1's smoke ask was answered by the session operator following AC1's own manual steps ("answer the ask with the Claude lane"), Tony present via the /ship invocation · builder call

### 2026-08-30 — build: Slice B
- The mandate carries a `[CODE_BOOK]` placeholder filled with /blueprint's SKILL.md — the outside code-book lens is impossible without it and the spec's packet list simply didn't name it · builder call
- The codex lane delivers the three documents as workspace files with a pointer-filled mandate (read-only sandbox reads them from cwd), rather than one inlined blob · builder call

## Deviations

### 2026-08-30 — build: Slice B
- AC1 ran on three lanes (Claude, GPT, DeepSeek) as three runs, per Tony's answer to the live ask ("1, 2, and 4"); the Qwen recommendation was not taken · per user
- AC1's "packet directory contains only the three filled documents" was violated in execution: one shared scratch dir served all lanes and DeepSeek's raw response file landed in it while GPT ran; GPT's output shows no sign of reading it, but the isolation the SKILL.md specifies (a fresh dir per lane) was not honored by this smoke · builder call
- DeepSeek's run produced no inspection: openrouter-box.sh guard FAILED (finish_reason=length, empty content — the reasoning budget consumed the script's 8000-token cap); the lane-down rule fired correctly (failure named, nothing written, no substitute) · builder call

## Discovered

### 2026-08-30 — build: Slice A
- A scope doc for the smoke target EXISTS at ~/Documents/architect-scope.md (precon slug "architect", not "architect-skill") — the smoke exercised the record-found path; R7's no-record branch remains unexercised by any run so far
- The smoke's real findings against the architect plan (2 MAJOR · 17 MINOR) live only in the scratch COPY; porting them to the real architect plan is Tony's call, outside this slice

### 2026-08-30 — build: Slice B
- /blueprint's SKILL.md changed on disk mid-build (17:49 — /handoff shipped): `## Handoffs` is now a mandated ledger section; THIS build plan lacks it, having been written against the older code — one-line scaffold add, Tony's call
- jpb's openrouter-box.sh max_tokens 8000 is too small for inspection packets on reasoning models (DeepSeek burned it all thinking); the script is jpb's file, outside this footprint — needs a budget parameter or an inspect-owned variant
- Same-day multi-lane runs collide on the spec'd raw filename `<feature>-inspect-<date>.md`; this run suffixed the lane (`-gpt`) — the SKILL.md should pin that
- /inspect has no cross-run rule for findings that converge with already-open ledger entries, and back-to-back same-day runs duplicate closure lines O(n) — skill-design gap found live
- The Claude run found a defect in /inspect's own mechanism: a `Plan: inspected` stamp inside the Out of scope parse range (corroborates the open Slice A MINOR about stamp-adjacent spec lines)

## Handoffs


## Punch list

### 2026-08-30 — review: Slice A
- MAJOR · ~/.claude/skills/inspect/SKILL.md:106 · "unverified finding" bar admits no severity carve-out while Step 4 verifies only BLOCKER/MAJOR · a many-MINOR run yields an empty verdict or an unscoped verify pass · Slice A review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:60 · stamp requires "the pinned id the inspectors actually ran on" with no mechanism to know it · session fabricates the trust label · Slice A review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:50 · Questions have no doc home and cannot fill the punch-list severity field · a precon-less run's confirm-list dies in chat · Slice A review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:18 · "plan established in this session" tier is unservable by the packet rule (no path; serializing chat is the named faux-context vector) · executor violates rule 3 or dead-ends · Slice A review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:18 · scope-doc hunt has no slug rule or ambiguity behavior · run misses an existing scope doc and silently applies the no-record rule · Slice A review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:60 · stamp anchor ambiguous, re-run ordering self-contradictory, no fallback for docs without an Out of scope anchor · second write lands in undefined places and history misorders · Slice A review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:14 · model floor undecidable — signoff-as-law imports the Opus floor while stamp doctrine assumes lightweight inspections are legal · sub-floor run must STOP or emit a forbidden verdict, text decides neither · Slice A review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:59 · inspect's severity-bearing ledger lines never receive a closing record · stale plan findings read as open items by siblings' open-filter later in the doc's life · Slice A review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:18 · empty-hunt branch reads both "ask Tony" and "report and stop" · AC3 outcome depends on which sentence the session weights · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:41 · spec's "quoted as the code" weakened to "cited" · code-book findings can rest on a gloss · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:57 · zero-findings run leaves write 1 undefined (empty block or skipped, either violates "exactly two") · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:59 · "the siblings' placement rule" is a dangling phrase no sibling file names · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:60 · a Questions-only run stamps "clean" and misleads the doc-side record · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:59 · same-day re-runs produce identical block headings with no discriminator · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:18 · scope hunt undefined for an out-of-repo build doc summoned by absolute path · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:18 · tiers labeled "/build's doc tiers" though they are /vertical's deliberate narrowing · a future editor widens the hunt · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:55 · CONDITIONS path states both "fixed before /build" and "fresh /inspect" without saying whether re-inspection is required · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:60 · stamp sits adjacent to Out of scope spec lines downstream stations harvest · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:40 · traceability lens's repo leg not pinned local for future outside lanes · repo-less outside inspector mis-flags repo-traceable items · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:59 · ledger line field 5 (inspector model) diverges from siblings' "which slice found it" · Slice A review
- MINOR · ~/.claude/skills/inspect/SKILL.md:60 · a /blueprint revision could drop stamp lines (header outside blueprint's protected ledger sections) — demoted from MAJOR: revision is in-place edits; real fix is a one-line /blueprint edit outside this slice · Slice A review

### 2026-08-30 — recheck: Slice A
- MAJOR · ~/.claude/skills/inspect/SKILL.md:106 · ("unverified finding" bar admits no severity carve-out) · fixed — now SKILL.md:108, MINOR carve-out explicit
- MAJOR · ~/.claude/skills/inspect/SKILL.md:60 · (stamp id has no mechanism) · fixed — now SKILL.md:62, launched-on rule
- MAJOR · ~/.claude/skills/inspect/SKILL.md:50 · (Questions have no doc home) · fixed — now SKILL.md:61, QUESTION lines
- MAJOR · ~/.claude/skills/inspect/SKILL.md:18 · (session-plan tier unservable by packet rule) · fixed — written-docs-only, tier removed
- MAJOR · ~/.claude/skills/inspect/SKILL.md:18 · (scope-doc hunt has no slug rule) · fixed — glob hunt, Intent matching, list-and-ask
- MAJOR · ~/.claude/skills/inspect/SKILL.md:60 · (stamp anchor/ordering/fallback undefined) · fixed — now SKILL.md:62, one placement rule, three cases
- MAJOR · ~/.claude/skills/inspect/SKILL.md:14 · (model floor undecidable) · fixed — explicit Step 0 exception, Tony's 2026-08-30 ruling cited
- MAJOR · ~/.claude/skills/inspect/SKILL.md:59 · (ledger lines never receive a closing record) · fixed — now SKILL.md:61, re-inspection closure lines
- MAJOR · ~/.claude/skills/inspect/SKILL.md:18 · (empty-hunt ask-vs-stop ambiguity) · fixed — zero candidates = report-and-stop, plural = list-and-ask
- MINOR · ~/.claude/skills/inspect/SKILL.md:75 · broke: Rule 8 demands a "pinned id" the Claude lane no longer has — re-creates the fabrication pressure the stamp fix removed
- MINOR · ~/.claude/skills/inspect/SKILL.md:61 · broke: "clean run" block line conflicts with the stamp's zero-findings-AND-zero-Questions definition of clean

### 2026-08-30 — recheck: Slice A
- MINOR · ~/.claude/skills/inspect/SKILL.md:75 · (Rule 8 demands a pinned id the Claude lane lacks) · fixed — delegates to Step 5's launched-on stamp rule
- MINOR · ~/.claude/skills/inspect/SKILL.md:61 · (clean-line conflicts with the stamp's clean definition) · fixed — definitions now word-for-word aligned, Questions case explicit

### 2026-08-30 — review: Slice B
- BLOCKER · ~/.claude/skills/inspect/SKILL.md:57 · Qwen packet passed inline via -p in a double-quoted shell argument, no cwd/isolation parity, "verified live" covered only a tiny literal · doc content with $() or backticks executes locally at send time; qwen can walk the repo the mandate forbids · Slice B review
- BLOCKER · ~/.claude/skills/inspect/SKILL.md:52 · packet composition defined three contradictory ways (verbatim-fill rule vs GPT files-in-cwd vs mandate's "verbatim below") · a literal executor cannot pick a winner; live run matched none · Slice B review
- BLOCKER · ~/.zshrc:29 · OPENROUTER_API_KEY captured in a reviewer transcript while verifying the adjacent qwen alias · key must be rotated; skill lacks a never-read-the-alias-from-zshrc warning · Slice B review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:121 · "MINORs pass through unverified" unscoped, contradicts the every-severity outside verify rule at :59 · hallucinated outside MINORs reach the ledger · Slice B review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:59 · raw filename collides on same-day/multi-lane runs and <feature> derivation undefined · a second run overwrites the first's verbatim record · Slice B review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:97 · Output template has no field for the mandated raw-file pointer · pointer silently dropped by a faithful renderer · Slice B review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:36 · multi-lane ask answer has no defined behavior (given live: "1, 2, and 4") · executor must refuse, re-ask, or silently violate one-per-run · Slice B review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:65 · outside QUESTION findings have no disposal rule when a scope doc exists (QUESTION lives only in the mandate) · silent drop or silent promotion · Slice B review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:44 · "three lenses, each a fresh subagent" unscoped to the Claude lane · GPT run double-originates paper lenses; Claude findings under a GPT stamp · Slice B review
- MAJOR · ~/.claude/skills/inspect/SKILL.md:56 · DeepSeek lane structurally dead on real plans (8000-token cap, proven live) with no roster warning · guaranteed lane-down loop on pick 4 · Slice B review
- MINOR · ~/.claude/skills/inspect/assets/inspect-mandate.md:58 · [CODE_BOOK] in the packet vs the spec's three-item list (ledgered builder call, spec text never amended) · Slice B review
- MINOR · ~/.claude/skills/inspect/SKILL.md:55 · Gemini parity line claims "copied literally" while necessarily differing from box-runners · parity auditor flags it · Slice B review
- MINOR · ~/.claude/skills/inspect/SKILL.md:54 · packet directory defined only inside the GPT bullet; Gemini/Qwen must infer from an unchosen lane · Slice B review
- MINOR · ~/.claude/skills/inspect/SKILL.md:57 · 64k "estimate before sending" names no estimation method · one session silently sends over budget · Slice B review
- MINOR · ~/.claude/skills/inspect/SKILL.md:54 · GPT cwd deviation from box-runners' neutral-empty not stated as deliberate · invites a fix-it-back · Slice B review
- MINOR · ~/.claude/skills/inspect/assets/inspect-mandate.md:44 · <doc>:<line> citations demanded from unnumbered inlined text · real findings refuted on citation error · Slice B review
- MINOR · ~/.claude/skills/inspect/SKILL.md:59 · Claude-lane raw-file expectation unstated (outside-only is inferable, not written) · Slice B review
- MINOR · ~/.claude/skills/inspect/SKILL.md:74 · plan-stage B/M ledger lines have no closer unless a re-inspect ever runs · adjudicated-wrong findings sit open-looking forever · Slice B review
- MINOR · ~/.claude/skills/inspect/SKILL.md:31 · the ask hides the Claude lane's effective model id; Tony picks the floor blind · Slice B review

### 2026-08-30 — recheck: Slice B
- BLOCKER · ~/.claude/skills/inspect/SKILL.md:57 · (qwen packet inline in a shell arg, no isolation statement) · fixed — safe file-read recipe, hostile-content live test created no file, isolation honesty note carried to the verdict
- BLOCKER · ~/.claude/skills/inspect/SKILL.md:52 · (packet composition defined three contradictory ways) · fixed — one fresh-dir packet.md rule for every lane, line-numbered fills, GPT cwd deviation labeled deliberate
- BLOCKER · ~/.zshrc:29 · (key captured in a reviewer transcript; skill lacked a never-read warning) · not fixed — the warning half IS fixed (SKILL.md:58), but the key rotation is Tony's act and remains outstanding
- MAJOR · ~/.claude/skills/inspect/SKILL.md:121 · (MINOR-verify exemption unscoped) · fixed — Claude-lane scoping explicit at :123
- MAJOR · ~/.claude/skills/inspect/SKILL.md:59 · (raw filename collides, feature underived) · fixed — lane suffix + -2 rule + feature derivation at :60
- MAJOR · ~/.claude/skills/inspect/SKILL.md:97 · (no Output field for the raw pointer) · fixed — Raw: field at :101
- MAJOR · ~/.claude/skills/inspect/SKILL.md:36 · (multi-lane answer undefined) · fixed — several lanes = several sequential runs
- MAJOR · ~/.claude/skills/inspect/SKILL.md:65 · (outside QUESTION disposal undefined with a scope doc) · fixed — routes to Questions machinery regardless, no stamp, QUESTION ledger line
- MAJOR · ~/.claude/skills/inspect/SKILL.md:44 · (three-subagent rule unscoped to the Claude lane) · fixed — per-lane origins explicit, never both
- MAJOR · ~/.claude/skills/inspect/SKILL.md:56 · (DeepSeek dead lane unlabeled) · fixed — caveat on the roster line and in the recipe with the mechanism
WAIVED (per user) · 2026-08-30 · BLOCKER · ~/.zshrc:29 · key captured in a reviewer transcript; rotation waived, exposure accepted
