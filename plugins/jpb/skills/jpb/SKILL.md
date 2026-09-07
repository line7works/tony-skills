---
name: jpb
description: >-
  Jon's Product Box — a consensus instrument that vets an idea before it has a
  name. Three to six independent frontier-model "box teams" (GPT, Fable, Opus,
  Gemini, DeepSeek, Qwen) each receive the same scrubbed brief with an identical
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

## Step 2 — Preflight: the roster, through readers

The six boxes and both judges are calls on roster rows of `/readers`, the
loop's reader component (`readers-protocol: 1`; every request this skill
sends carries `protocol_version: 1`). The model ids, efforts, windows,
budgets, sandboxes, no-web parity lines, and transports live in readers'
roster; this skill pins none of them, and a roster row moves only by PR on
Tony's word, never mid-run (`assets/box-runners.md` says where each of the
old recipes' recorded traps now lives). Before the approval ask, every run:

1. Mint a fresh run id for this run — one path segment, characters
   `[A-Za-z0-9._-]` only (readers refuses anything else as
   `invalid-request`), e.g. `jpb-<YYYYMMDD>-<four hex>` — and make the run
   directory (`mktemp -d`, a scratch path outside any repo). Every request
   below carries that directory as `run_dir` and the suggest carries it as
   `--run-dir`, so the whole run resolves from one frozen snapshot. Nothing
   is ever re-sent under this run id: a call id is single-use, and a rerun
   of the exercise is a fresh Step 1–7 run with a fresh run id.
2. Summon `/readers suggest
   claude-fable,claude-opus,gpt-astra,gemini,deepseek,qwen,claude-session
   --run <run id> --run-dir <run dir>` — one call, every row the run
   touches. This is the roster freshness check: per row it reports the
   model the run would send (a remembered pick or the roster default),
   whether the row is outside, whether it is available, and any drop note;
   its first call freezes the run, so the model the ask shows is the model
   that sends. A row `suggest` reports unavailable is that box
   dropped-with-reason before the ask (the run continues if ≥3 boxes
   remain); a drop note (a remembered pick readers dropped) is shown in the
   ask beside its row as-is, and the row sends the model `suggest` now
   shows. The old "newer model available" scan is gone: a newer model is a
   roster PR on Tony's word, never a run-time suggestion.
3. Confirm the Workflow tool is among this session's tools. The Fable and
   Opus boxes (`starved`, effort pinned) and Judge K route through it;
   without it readers returns `lane-unavailable` for those calls, and a
   failed Judge K is a failed run (Step 8) — so a session without the tool
   stops here and says so, before any ask and before any spend.

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
- a one-line cost estimate (the OpenRouter boxes, DeepSeek and Qwen, are
  the only marginal dollars; short brief ≈ a penny or two, PRD-length ≈
  tens of cents),
- the roster as seven enumerated calls, each with the model `suggest`
  showed for its row and any drop note: the six boxes — `claude-fable`,
  `claude-opus`, `gpt-astra`, `gemini`, `deepseek`, `qwen` — and, seventh,
  Judge G on the GPT row (`gpt-astra`, the same model as the GPT box); a
  box dropped at Step 2 is listed as dropped-with-reason below the seven,
- beneath the seven, one line for Judge K: row `claude-session`, this
  session's own model (name the id the session reports for itself —
  `suggest` shows the placeholder `session` for this row), a Claude call
  that needs no word.

Then STOP and wait. No box launches before Tony approves. "Go" approves
the seven calls exactly as shown, and that answer is the word for the five
outside calls among them (the GPT, Gemini, DeepSeek, and Qwen boxes, and
Judge G): `authorized: true` goes on those five requests and on nothing
else — never on a Claude call, never inferred, never carried over from
another run. A model switch is an id Tony types against a row ("GPT box on
gpt-5.6-sol"): it is passed as `model` on every call on that row in this
run (the box, and Judge G when the row is the GPT row) and readers
remembers it as an explicit pick for future runs, so the next run's
`suggest` shows it as the row's model; record the switch in the run doc's
roster. A switch is never a different row — the rows are fixed, the id is
his. "Skip <box>" drops that box with the reason "Tony's word" and the run
continues if three or more boxes remain. If anything re-asks after a change
(a fresh run's `suggest` showing a different model beside a row), the send
goes out under the model he saw, never under one he did not.

## Step 5 — Fleet launch

The launch is one `/readers` fleet of six calls under this run's id,
launched together (readers runs the portable rows in the background and the
host rows through their tools in one message), each with ZERO shared
context: a box receives the prompt readers composes from its request — the
mandate and the brief, plus readers' fixed reader instruction on the Claude
rows — never chat history, never another box's output.

- Compose the one mandate every box receives, jpb's as before:
  `assets/box-mandate.md` with `[TEMPLATE]` replaced by the full contents of
  `assets/box-template.md`, written to `<run dir>/box-mandate.md`. Write the
  scrubbed brief to `<run dir>/brief.md`; it travels as each request's one
  document, so the composed prompt is the mandate, then the brief delimited
  as `<<<DOCUMENT brief.md>>>` … `<<<END DOCUMENT>>>` (readers' contract,
  Prompt composition) where the old separator line stood.
- Six requests, one per box row, identical except for the row-specific
  fields: `protocol_version: 1`, `run_id` this run's, `run_dir` this run's
  directory, `call_id` `<run id>-box-<row>`, `row` the box's row, `mandate`
  `<run dir>/box-mandate.md`, `documents` `["<run dir>/brief.md"]`,
  `profile: starved`, `raw_path` `<run dir>/boxes/<row>.md`, `effort: high`
  on the rows that accept one (`claude-fable`, `claude-opus`, `gpt-astra`;
  `gemini`'s effort is the suffix of its roster id and DeepSeek and Qwen take
  none, so those three carry no `effort`), `authorized: true` on the four
  outside boxes only, and `model` only where Tony typed an id against that
  row at approval. No `session_model`: no box runs on `claude-session`.
- Each `READERS:` line is one box's result. `ok` means the box text is at
  its `raw_path` (readers' verbatim copy; the `raw.md`, sidecar, and
  diagnostics under `<run dir>/<call id>/` are the evidence and are never
  edited). Any other status — `lane-unavailable`, `unauthorized`, `empty`,
  `incomplete`, `transport-failed`, `oversize`, any refusal — is that box
  dropped, with the status and the sidecar's `reason` recorded; never
  retried, never re-sent under another id (one box per model per run).
- Validate every `ok` box's copy with `assets/validate-box.py <raw_path>`.
  INVALID → that box is dropped, the validator's reasons recorded.
- A box's no-web parity and isolation record are its sidecar's `parity` and
  `isolation` fields — what readers recorded for the row and profile, never
  a sentence typed here.
- **Minimum three** template-valid boxes or the run aborts with a plain
  message naming what failed; failed/dropped boxes are recorded with
  reasons and the run otherwise continues.

## Step 6 — Cost actuals

Dollars only — Tony's rule (2026-08-09): record real money for anything
API-billed; no token counts anywhere. For each OpenRouter box (DeepSeek,
Qwen) that returned, take the sidecar's `response_raw` path — readers' copy
of the exact HTTP body, `<run dir>/<call id>/response.raw` — and fetch the
actual billed USD: `assets/openrouter-cost.sh <response_raw>` (the script
reads the body's top-level `id`, unchanged). Sum an OpenRouter total.
Subscription boxes (Fable, Opus, GPT) each record a cost line of: a
dollar sign, the digit zero, an em dash, then "subscription" — per the
vision doc's format. Gemini records the same zero-dollar figure followed
by "— no billing". (Spelled out character by character here because the
skill-invocation layer substitutes the skill argument for a literal
dollar-sign-zero appearing in this file; the run doc itself carries the
normal dollar figure exactly as the vision doc and prior run docs write
it.)

If the cost fetch FAILS (script exit 1): record the box's cost line as
"unavailable (generation id <the sidecar's `generation_id`>; response.raw
kept at <response_raw>)" so the cost stays recoverable, and move on — a
cost-fetch failure never fails the run. `response.raw` is readers'
run-directory evidence: this skill never deletes or rewrites it, whatever
the cost fetch did, and raw files never live in or beside the doc's
directory (the run directory is scratch, outside any repo).

## Step 7 — Output doc

Home: the current repo's `docs/` when run inside a git repo, else
`~/Developer/_ideas/`. Filename `jpb-<slug>-<YYYY-MM-DD>.md` (slug from the
scrubbed idea, not the working name); on collision append `-2`, `-3`, … —
reruns never overwrite.

Frontmatter: `status: open`, run date, roster (which model filled which
box, which were dropped and why, any id switch Tony ordered), a `parity:`
block — one line per box recording its no-web parity fact exactly as the
box's sidecar `parity` field reads (readers' line for the row under
`starved`: DeepSeek and Qwen "no :online suffix"; GPT "web_search:
disabled …"; Fable/Opus "toolCalls: 0"; Gemini "skip_permissions off, cwd =
fresh empty dir, non-empty response") — and the cost block (per-box billed
USD + OpenRouter total). A box whose parity line cannot be truthfully
written — its status was not `ok`, or its sidecar carries no `parity` — is
dropped-with-reason.

Body, in order: the scrubbed brief, then every box VERBATIM under a
vendor-labeled heading (`## GPT box — gpt-6-astra`, …), dropped boxes as a
heading + reason. `<Vendor>` is the row's label — `claude-fable` Fable,
`claude-opus` Opus, `gpt-astra` GPT, `gemini` Gemini, `deepseek` DeepSeek,
`qwen` Qwen, the six names `render-page.py` and the styles JSON key on —
and `<model-id>` is the effective model id the box's `READERS:` line
carries (the harness names `fable` and `opus` on the two Claude rows). Nothing summarizes, ranks, or replaces the raw boxes; no
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

Both judges are `/readers` calls that receive an identical mandate and
identical documents and NOTHING else: `mandate` `assets/judge-mandate.md`
(by path); `documents` two files written into the run directory —
`<run dir>/judge-brief.md` (the scrubbed brief) and `<run dir>/judge-boxes.md`
(every filled box verbatim under its vendor-labeled heading, parsed from
the doc by the `## <Vendor> box — <model-id>` contract above). Readers
composes the prompt as the mandate, then the two documents delimited, the
same for both rows (the Claude row's copy opens with readers' fixed reader
instruction — the one difference). No chat context, no repo context, and
neither judge ever sees the other's tally — independence is structural, not
promised. One fleet of two calls, launched together under this run's id:
`protocol_version: 1`, `run_id` this run's, `run_dir` this run's directory,
`profile: starved`, `effort: high`, `raw_path` `<run dir>/judges/<judge>.md`.

- **Judge K** — one `claude-session` call, `call_id` `<run id>-judge-k`,
  `session_model` the model id this session reports for itself (it becomes
  the sidecar's effective model), no `authorized` (a Claude row never
  carries it). The pinned effort routes it through the Workflow tool
  (readers' committed script pattern; the prompt lives in the script body,
  never in Workflow `args`), so it inherits the session model at effort
  high, as before.
- **Judge G** — one call on the GPT row, `row: gpt-astra`, `call_id`
  `<run id>-judge-g`, `authorized: true` — the Step 4 approval's seventh
  line is its word — and `model` only when Tony typed an id against the GPT
  row at approval. Its read-only sandbox, neutral working directory, and
  `web_search: disabled` parity are the row's, resolved by readers.

Guards: a `READERS:` status other than `ok` (`empty` included) is a FAILED
judge; a judge's tally is its `raw_text` (the copy at its `raw_path`). If
Judge G fails or its parity can't be established (its sidecar carries no
`parity` line), the run completes with Judge K alone and the doc says so
plainly. Judge K failing is a failed run — report honestly and stop. Judges
are never re-run to "get a better tally"; one tally per judge per run, and
no call is ever re-sent under this run's id.

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
- Never pass a `model` Tony didn't type at this run's approval, and never
  move a roster row — that is a readers PR on his word, never a run.
- Never put `authorized: true` on a call the approval didn't enumerate, and
  never on a Claude call.
- Never edit readers' `raw.md`, a sidecar, or `response.raw`; the run
  directory is evidence.
- Never write the output doc anywhere but the two sanctioned homes, and
  never overwrite an existing run doc.
- Never put an API key in the doc, the chat, or the repo.
