---
name: jpb
description: >-
  Jon's Product Box — a consensus instrument that vets an idea before it has a
  name. Three to six independent frontier-model "box teams" (GPT, Fable, Opus,
  Gemini, DeepSeek, Grok) each receive the same scrubbed brief with an identical
  mandate and fill a strict product-box template; the run produces one output
  doc holding the scrubbed brief and every box verbatim. Use when Tony says
  "/jpb <idea or path>", "run the product box on this", "box this idea", or
  wants independent-model consensus on a product concept before /blueprint.
  Also "/jpb resolve" to record Tony's calls into an open run doc and close it.
---

# JPB — Jon's Product Box

You are Jon: hand the same wrapped box to teams that cannot see each other,
collect what comes back, and change nothing. The value is
consensus-by-independence — every step below either protects that independence
or records what happened. The design source of truth is
`docs/jpb-vision.md` in this repo; on any conflict between this file and
that doc, the vision doc wins and the conflict goes to Tony.

**Current coverage.** This version runs intake → scrub → approval → fleet →
boxes doc → two judge tallies → reconciliation → debate card, end to end,
plus `/jpb resolve` (the Resolve section below) to record Tony's calls and
close a run doc, and the arcade page (Step 11) — a styled HTML projection
of the finished doc posted to the Line 7 Arcade, re-posted at resolve.

Asset paths below resolve at the plugin's install location (this plugin
nests its assets beside this SKILL.md):
`${CLAUDE_PLUGIN_ROOT}/skills/jpb/assets/` — referred to as
`assets/`.

## Step 1 — Intake

The input is a file path (PRD, plan doc) or raw idea text given inline.
A path is read in full; raw text is taken as-is. Nothing else enters the
run — no chat history, no repo context.

**Thin-input floor.** If the input cannot honestly support 9 distinctive
properties and 3 load-bearing assumptions — a bare one-liner, a name with no
substance — do NOT launch anything. Reply with an enrichment ask: 3–5
pointed questions (who is it for, what does it do, what exists already,
what's the constraint) and stop. The run resumes only when Tony supplies
more.

## Step 2 — Preflight: roster freshness

Before the approval ask, re-verify the pinned roster and look for newer
frontier models per vendor:

1. `curl -s https://openrouter.ai/api/v1/models` — confirm the pinned
   `deepseek/deepseek-v4-pro` and `x-ai/grok-4.5` still exist, and scan
   `deepseek/*` and `x-ai/*` entries for ids with a newer `created`
   timestamp that read as frontier successors (ignore minis/distills).
2. `~/.codex/models_cache.json` — confirm `gpt-5.6-sol`; note any newer
   `gpt-*` frontier variant.
3. antigravity `list_models` — confirm `gemini-3.1-pro-high`; note newer.

A pinned id that no longer exists marks that box dropped-with-reason (the
run continues if ≥3 boxes remain). Anything newer becomes a suggestion line
in the approval ask ("newer model available: X — switch?"). **Pinned ids
change only on Tony's word, and never mid-run.**

## Step 3 — Scrub

Launch ONE dedicated low-context agent (general-purpose subagent, no other
duties, receives only the raw input) with this mandate: replace the working
name and any branding/naming language with neutral placeholders ("the
product", "the company") WITHOUT rewriting, summarizing, or improving the
brief — a find-and-replace with judgment, not an edit. It returns the
scrubbed brief verbatim-otherwise.

Check its work mechanically: grep the scrubbed brief for the working name
(case-insensitive). Any hit → send it back once; a second failure stops the
run with the honest state.

## Step 4 — Approval (hard pause)

Show Tony, in chat:
- the scrubbed brief in full,
- a one-line cost estimate (OpenRouter boxes are the only marginal dollars;
  short brief ≈ a penny or two, PRD-length ≈ tens of cents),
- the roster: which boxes will launch, any dropped-with-reason,
- any freshness suggestions from Step 2.

Then STOP and wait. No box launches before Tony approves. "Go" approves the
roster as shown; a model-switch instruction updates the pinned id for this
and future runs (record it in the run doc's roster).

## Step 5 — Fleet launch

Execute `assets/box-runners.md` verbatim — it is the mechanism, not a
reference. Per run:

- Compose the one prompt every box receives: `assets/box-mandate.md` with
  `[TEMPLATE]` replaced by `assets/box-template.md`, then
  `\n---\n\nThe brief:\n\n` + the scrubbed brief.
- Launch all reachable roster boxes in parallel with ZERO shared context:
  each invocation contains only the composed prompt — never chat history,
  never another box's output. Routes and guards per box-runners.md
  (OpenRouter via `assets/openrouter-box.sh`; Fable/Opus via
  `assets/claude-boxes.workflow.js` with the prompt embedded in the script
  body, never via Workflow `args`; GPT via codex MCP; Gemini via
  antigravity MCP — each with its recorded parity mechanism).
- Validate every returned box with `assets/validate-box.py`. INVALID →
  that box is dropped, the validator's reasons recorded. Guard-FAILED →
  dropped, the guard's reason recorded.
- **Minimum three** template-valid boxes or the run aborts with a plain
  message naming what failed; failed/dropped boxes are recorded with
  reasons and the run otherwise continues.

## Step 6 — Cost actuals

Dollars only — Tony's rule (2026-08-09): record real money for anything
API-billed; no token counts anywhere. For each OpenRouter box, read the
generation id from the run's `.raw` response and fetch the actual billed
USD: `assets/openrouter-cost.sh <raw-file>`. Sum an OpenRouter total.
Subscription boxes (Fable, Opus, GPT) each record a cost line of: a
dollar sign, the digit zero, an em dash, then "subscription" — per the
vision doc's format. Gemini records the same zero-dollar figure followed
by "— no billing". (Spelled out character by character here because the
skill-invocation layer substitutes the skill argument for a literal
dollar-sign-zero appearing in this file; the run doc itself carries the
normal dollar figure exactly as the vision doc and prior run docs write
it.)

If the cost fetch FAILS (script exit 1): do NOT delete that `.raw`. Record
the box's cost line as "unavailable (generation id <id>; raw kept at
<path>)" so the cost stays recoverable, and move on — a cost-fetch failure
never fails the run. Only after a box's cost is recorded (or its id
preserved in the doc) is its `.raw` deleted, and raw files never live in
or beside the doc's directory.

## Step 7 — Output doc

Home: the current repo's `docs/` when run inside a git repo, else
`~/Developer/_ideas/`. Filename `jpb-<slug>-<YYYY-MM-DD>.md` (slug from the
scrubbed idea, not the working name); on collision append `-2`, `-3`, … —
reruns never overwrite.

Frontmatter: `status: open`, run date, roster (which model filled which
box, which were dropped and why, any id switch Tony ordered), a `parity:`
block — one line per box recording its no-web parity fact exactly as
box-runners.md defines it (OpenRouter: "no :online suffix"; GPT:
"web_search: disabled"; Fable/Opus: "toolCalls: 0"; Gemini: "plan mode,
skip_permissions off, neutral cwd, non-empty response") — and the cost
block (per-box billed USD + OpenRouter total). A box whose parity line
cannot be truthfully written is dropped-with-reason, per box-runners.md.

Body, in order: the scrubbed brief, then every box VERBATIM under a
vendor-labeled heading (`## GPT box — gpt-5.6-sol`, …), dropped boxes as a
heading + reason. Nothing summarizes, ranks, or replaces the raw boxes; no
recommendation language anywhere. **The vendor-heading pattern is a
contract**: `## <Vendor> box — <model-id>` is exactly what Step 8 parses to
hand the boxes to the judges — never vary it. A box runs from its vendor
heading to the next vendor heading, or to the first judge-phase H2
(`## Judge K tally`, `## Judge G tally`, `## Reconciliation`, `## Debate
card`), or to a `## Verdicts` heading (a resolved doc — see Resolve), or
to end of file — whichever comes first; a box's internal headings never
terminate it. Dropped boxes get a heading that does NOT
match the contract (`## Dropped — <Vendor> (<model-id>)` + the reason) so
the parse can never feed a reason-stub to a judge.

## Step 8 — Two judges (independent, fresh)

**Rerun guard (hard stop).** Before judging, check the run doc for any
judge-phase H2 (`## Judge K tally`, `## Judge G tally`, `## Reconciliation`,
`## Debate card`), any `## Verdicts` heading, or frontmatter
`status: closed`. A judge-phase hit means the doc is already judged; a
Verdicts or closed hit means the doc is already resolved — Tony's calls
are in it, and feeding them to a judge destroys the independence this
skill exists to protect. Either way: STOP and report
— judges are never re-run over a judged doc, and a rerun of the exercise is
a fresh Step 1–7 run producing a new doc under the collision rule.

Both judges receive an identical composed prompt and NOTHING else:
`assets/judge-mandate.md` + `\n---\n\nThe scrubbed brief:\n\n` + the scrubbed
brief + `\n---\n\nThe boxes:\n\n` + every filled box verbatim under its
vendor-labeled heading (parsed from the doc by the `## <Vendor> box —
<model-id>` contract above). No chat context, no repo context, and neither
judge ever sees the other's tally — independence is structural, not
promised.

- **Judge K** — a fresh Claude subagent of the session-model class with
  effort pinned high. The bare Agent tool has no effort parameter, so route
  through the Workflow tool with the composed prompt embedded IN the script
  body (never via `args` — the recorded trap), `agent(prompt, {label:
  'judge-k', effort: 'high'})`, model omitted so it inherits the session
  model. `assets/claude-boxes.workflow.js` is the committed pattern.
- **Judge G** — `gpt-5.6-sol` via `mcp__codex__codex` with exactly the GPT
  box's parity config: `model: "gpt-5.6-sol"`, `base-instructions`: the
  judge mandate, `prompt`: the brief + boxes, `sandbox: "read-only"`,
  `cwd`: a neutral empty directory, `config: {"web_search": "disabled"}`.

Guards: an empty/null result is a FAILED judge. If Judge G fails or its
parity can't be established, the run completes with Judge K alone and the
doc says so plainly. Judge K failing is a failed run — report honestly and
stop. Judges are never re-run to "get a better tally"; one tally per judge
per run.

## Step 9 — Reconciliation + debate card (mechanical)

Performed by the orchestrating session, no editorializing and no
recommendation language — match, count, and list:

- A reconciliation table matching clusters across the two tallies by
  meaning: matched clusters (both judges = strongest signal) with each
  judge's label and support count; clusters only one judge formed listed
  as single-judge, as such.
- **Mechanical recount**: for every cluster in both tallies, recount the
  DISTINCT boxes in its member list. A judge's stated count or consensus
  label that the recount does not support is recorded as unsupported in
  that cluster's table row, with the recount — a count correction is
  mechanical fact, never editorializing. Tally text itself is never edited.
- The final debate card: the union of both judges' proposed questions,
  deduped by meaning, capped at 3, questions raised by both judges first.
  If nothing survives, the card reads "No material disagreement."

## Step 10 — Final doc assembly

Append the judge sections to the run doc from Step 7, so the finished doc
reads in exactly this order: scrubbed brief · boxes verbatim · Judge K
tally (verbatim) · Judge G tally (verbatim, or a heading + reason if it
failed) · reconciliation · debate card. Tally sections must nest under
their `## Judge K/G tally` headings: the mandate's output format uses H3/H4
for this reason; if a judge returns H2/H3 headings anyway, demote every
heading inside its tally one level at assembly (structure only, text
untouched) and note the demotion in the reconciliation preamble. No recommendation language anywhere
in the doc — before reporting, grep the doc for "recommend", "should
choose", "the best option" and fix any hit by removing the editorializing,
never by rewording it into a synonym.

Report the doc path in chat, render and post the arcade page (Step 11),
then POST THE DEBATE CARD IN CHAT: the card's questions verbatim, each
with one plain-language line of what's at stake and which boxes/judges
stand where (drawn from the card and reconciliation — restating recorded
disagreement is not recommendation language), plus any question the cap
dropped. Tony must see the questions where he is, never be sent to find a
doc. Then stop and wait — the debate is human.

When Tony answers the questions in chat — in this session, at any later
point — that IS the resolve trigger: go straight into Resolve at R2
against this run's doc (R1's listing is skipped only because the doc is
already identified; every other Resolve step, including the R3
call-by-call attribution confirmation, runs unchanged). `/jpb resolve`
(below) remains the entry point from a fresh session.

## Step 11 — Arcade page (projection, not record)

After the COMPLETE run — brief, boxes, both tallies, reconciliation,
debate card all in the doc — render one self-contained scrolling HTML page
and post it to the Line 7 Arcade. Never mid-run, never from a partial doc.
The markdown doc stays the record; the page is its projection.

**Render.** Run `python3 assets/render-page.py <doc.md>
assets/jpb-page-template.html assets/jpb-vendor-styles.json
assets/jpb-wordmark.png <out.html>` — the committed renderer is the
mechanism, this prose is its contract:

- `{{TITLE}}` = the doc's filename slug, title-cased, minus the `jpb-`
  prefix, the date, and any `-2`/`-3` collision suffix (grep the finished
  page for any unscrubbed working name before posting).
- The page opens with a Brief panel (the scrubbed brief, `brief` styles
  from the styles JSON) and a Brief tab — first in the tab bar.
  `{{RUN_DATE}}` from frontmatter. `{{STATUS_LINE}}` = " · resolved" when
  the doc is closed, empty otherwise.
- `{{WORDMARK_IMG}}` = `<img class="wordmark" alt="JPB" src="<data URI>">`
  with the committed `assets/jpb-wordmark.png` inlined base64 — the page
  makes no external requests.
- One `<section class="panel">` per box, in doc order, on the shared
  skeleton: badge, H2 vendor name, model id line, then the box's Front /
  Back / Side / Bottom content as H3 groups. Each section gets
  `style="--accent:<accent>;--tint:<tint>"` from
  `assets/jpb-vendor-styles.json` — accents are preset there, never
  invented per run. Dropped boxes render as
  `<section class="panel dropped">` with the `dropped` styles and the drop
  reason in a `.dropreason` line.
- Then panels for: Judges (both tallies, condensed to their cluster tables
  and flag lines, using the `judges` styles), Summary (the reconciliation
  table + names/preamble notes, `summary` styles), and — when the doc is
  resolved — Verdicts (`verdicts` styles). Tab bar: one link per box
  section plus Judges and Summary (and Verdicts when present), each tab
  carrying its section's accent as `--tab-accent`.
- Cost panel content lives inside the Summary section: a small table
  mirroring the frontmatter cost block verbatim — per-box lines and the
  OpenRouter total, dollars only.
- No recommendation language anywhere — before posting, grep the HTML for
  "recommend", "should choose", "the best option"; fix by removal, same
  rule as the doc.

**Post.** Slug = the doc's filename minus `.md` (it already follows the
`jpb-<slug>-<date>` collision rule). First post:
`arcade-publish publish <file.html> --name "<title> — JPB" --slug <slug>`.
Record the returned URL in the doc frontmatter as `arcade_url: <url>` —
that is the only body/frontmatter write Step 11 makes. A publish failure
NEVER fails the run: record `arcade_url: "render/post failed: <reason>"`
instead, report it, and move on — the doc is the record either way.

## Resolve — `/jpb resolve`

Runs after the human debate, in a later session or the same one. Its body
writes are exactly two: append one `## Verdicts` section after the doc's
last section, and flip the one frontmatter field `status: open` →
`status: closed` (Step 11 and R5 additionally maintain the frontmatter
`arcade_url` field — the only other sanctioned doc write anywhere in this
skill). Nothing already in the doc is ever edited, reordered, or removed —
in particular the reconciliation's recount corrections stay untouched.

**R1 — List.** (Skipped when Resolve is entered inline from Step 10 —
Tony just answered the debate card in the session that ran the doc, so the
doc is already identified; start at R2.) Find candidate docs: every file matching the run-doc
filename convention `jpb-<slug>-<YYYY-MM-DD>.md` (with optional `-2`/`-3`
collision suffix) whose frontmatter reads `status: open`, in the current
repo's `docs/` and in `~/Developer/_ideas/`. Both filters apply — a
non-`jpb-` file with open frontmatter is never a candidate (Tony's call
2026-08-09, matching the vision doc's fixed-filename convention). Check the frontmatter block (between the opening
`---` lines), not the whole file. If none exist anywhere, say so plainly
("no open JPB run docs in <repo>/docs/ or ~/Developer/_ideas/") and stop —
no writes, no guesses. If one or more exist, list them (path + run_date)
and ask Tony which one to resolve; never auto-pick, even with a single
candidate.

**R2 — Confirm the doc.** Restate the chosen doc's path and its debate-card
questions (if it has a `## Debate card` section) so Tony is answering
against the right run. A doc with no judge sections can still be resolved —
Tony may close an idea straight from the boxes — but say what the doc does
and doesn't contain before taking calls.

**R3 — Take the calls.** Tony states his calls in plain language ("going
with name X, buyer is Y, kill the white-label idea"). For each call,
confirm its attribution before anything is written: which box (`## <Vendor>
box — <model-id>`) or which judge-tally cluster the call traces to, stated
back to Tony as "call → source" pairs. A call that traces to nothing in the
doc is recorded with attribution "Tony — outside the boxes", stated as
such in the confirmation. Only after Tony confirms the full set do the
writes happen.

**R4 — Write.** Append to the end of the doc body:

```markdown
## Verdicts — <YYYY-MM-DD>

| # | Call | Source |
|---|------|--------|
| 1 | <Tony's call, his words> | <box heading / cluster label / Tony — outside the boxes> |
```

Then flip the frontmatter `status: open` line to `status: closed`. Those
two writes are the whole footprint in the doc body/frontmatter (plus the
`arcade_url` update below).

**R5 — Re-post the page.** Re-render the now-closed doc per Step 11 (the
page gains the Verdicts panel and its tab, and the masthead gains
"resolved") and re-post to the SAME slug:
`arcade-publish update <slug> <file.html>`. Use `update` only when
`arcade_url` holds a real URL; when the field is missing OR holds a
"render/post failed" note (the page never went live), use `publish`
instead. Either branch records the resulting URL in `arcade_url` on
success. A re-post failure never fails the resolve:
note "render/post failed: <reason>" in the `arcade_url` field and report
it. Report the closed doc's path and the page URL, and stop; committing is
Tony's word, per the repo's git gates.

**Resolve hard rules.** Never re-run judges over the doc (any judge-phase
H2 means judged — same guard as Step 8). Never invent, infer, or complete
a call Tony didn't state. Never resolve a doc whose frontmatter already
reads `status: closed` — say so and stop.

## What NOT to do

- Never launch a box before Tony's approval, and never re-launch a box to
  "get a better one" — one box per model per run; failures are recorded,
  not retried into shape.
- Never let a box see chat context or another box's output, and never let a
  judge see chat context or the other judge's tally.
- Never edit, trim, or paraphrase a box in the doc — verbatim or dropped.
- Never change a pinned model id without Tony's word.
- Never write the output doc anywhere but the two sanctioned homes, and
  never overwrite an existing run doc.
- Never put an API key in the doc, the chat, or the repo.
