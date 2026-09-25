---
name: architect-v2
description: >-
  The drawings step: one interview after precon that produces the architecture-and-delivery doc
  the downstream stations consume, plus a visual of what was decided, with the scope doc's
  decided lines passed forward by script and never re-asked. Use only when the owner types
  /architect-v2 by name. Strictly user-invoked: never auto-invoke, suggest-invoke, or trigger
  from conversation shape, no matter how architecture-shaped the discussion looks. Not the scope
  doc (precon-v2), not the sliced plan (blueprint-v2), not provisioning, and not the v1 architect
  station.
disable-model-invocation: true
---

# Architect v2

The drawings step between precon and everything downstream. Precon settles what an idea is;
provisioning and blueprint-v2 come after. This station draws the building in between: one
interview that produces one living architecture doc, the least structure that serves a named first
user's walkthrough without becoming demolition later, and a visual of what was decided.

**The spine.** Decisions at full-vision quality, construction at MVP quantity. The one-way doors
(language, storage, repo shape, data shapes, platform, and any other the project has) are settled
now for the whole vision; their construction waits for the walkthrough that needs it. Delivery
(who first touches this, by when, doing what) and architecture (the least structure that serves
exactly that) run as one negotiation.

**The one unforgivable move is the nod:** you propose one structure and the owner agrees. Two or
three genuinely distinct candidates go on the table every run, each with what it assumes and what
it makes expensive later, or the interview did not happen.

**You decide, the script records** (rule E14-4). You talk to the owner and judge; you hand your
judgment to `scripts/architect.py` as ONE recorded answer (amended once after the blind review).
The script finds the documents, reads the scope doc's ledger, checks your answer, renders and
continues the doc, renders the visual, records the publish, builds the reviewers' requests, saves
their takes and writes the result. It writes no event and never opens the records component. You
never type the doc: it is rendered from your answer.

Run only when the owner types it by name. Never invoke it on your own or suggest invoking it.

## How to run a command

Every command is `uv run scripts/architect.py <command> ...`, the script resolved against the
directory holding this file; paths inside a run are absolute. Each prints one JSON document and
exits 0 (go on), 10 (the run ended: read it back), 2 (your slip: read stderr, fix, rerun), 3
(`jsonschema` missing: use `uv run`), 4 (your answer failed its schema: fix the file), 5 (your
answer was refused on its content: nothing was written; read each refusal, fix what it names,
record again), or 1 (a defect: report it, never work around it). `references/architect-v2-contract.md`
is the contract of every command; `references/answer.schema.json` is your answer's shape.

## Step 1. The input gate

1. Read `adapters/README.md`: its profile names the helper that prints the `invocation` block and
   your `answer_fields.session_id`. Copy both whole; type none of their fields.
2. Write the input (`references/input.schema.json`): a fresh `run_id`, a `run_dir` outside the
   workspace and the staging home, the workspace (the repository, when there is one), the staging
   home, `station.scope_doc` when the owner named a scope doc's path, `station.publish: false` when
   he said not to publish, and `owner_word` when his invocation already names reviewers (his
   words verbatim). Run `check-input <input.json>`.
3. Run `select --run-dir D --hunt scope`. `one`: read its `Intent:` line; when it is the project
   he is talking about, that is the scope doc; when it is not, treat the hunt as `none`. `several`:
   list them for the owner in a plain numbered question and never pick; `harvest` will stop the
   run, and his pick goes into a new run's `station.scope_doc`. `none`: ask him once, in plain text, whether a
   scope doc exists somewhere the glob cannot see, and take the path he gives (a new run, with it
   as `station.scope_doc`). Only his "none" opens the docless gate: discuss why the station runs
   without a scope doc until the talk lands on a reason and a working name. When the hunt's `one`
   was another project's doc, `harvest` would take it: on his "none", start a new run whose input
   carries `station.docless: true` and `station.docless_reason` (that reason, word for word); it
   sets the hit aside, and your answer's `docless.reason` is the same reason.
4. Run `select --run-dir D --hunt architecture --name <slug>`: the slug is the scope doc's idea
   (the `<idea>` of `docs/scope/<date>-<idea>.md` or `<idea>-scope.md`), or the working name on a
   docless run.
5. Run `harvest --run-dir D`. Read what it prints before asking anything: every ledger line with
   its id and tag, and the living doc with its run count when there is one. A `decided` line is
   settled: it passes forward by script and you never ask it again. A stop (`selection-several`,
   `ledger-refused`, `living-doc-malformed`) ends the run: read it back and stop.

**The property line.** Lookups are the repository, the project's docs and your own knowledge. No
web access, no research agents, no research documents. An outside unknown is not looked up and
not guessed: it becomes a `NEEDS CHECK` line (the answer's `lines`) for the owner.

## Step 2. The exit ramp

The first question, asked alone and answered before anything else: **is there a system here at
all?** His answer is never inferred from silence or from your recommendation. A single static page
is not a system. When it is that small, the interview ends after this one question: the answer
records `exit_ramp.continued: false`, no candidates, no pick, and the tiny doc is still written and
the visual still rendered.

## Step 3. The interview

Questions in plain text, numbered, each with a recommendation, so he can answer by number; never
the harness's question UI. A recommended item his answer does not mention is accepted at its
recommendation, and you say so in the next message, except the two answers that must be his in
words: the exit ramp and the candidate pick, re-asked until he answers. Keep it short: about three
answers plus the sorted scope; when a thread runs long, record what is settled and move on.

1. **The walkthrough target.** A named real person (never "users"), the date of the session where
   they use it, and what they must be able to do, as a short list. All three fields filled; `n/a` is
   a value, a blank is not. Each `must` item is one requirement, with no `; ` inside it.
2. **The candidates and the razor.** Two or three structures, distinct in at least one one-way-door
   category (write each as `category:choice`), each with what it assumes and what it makes
   expensive later. Grill each against the walkthrough: every component names the requirement it
   serves, or it is cut from v0. He picks in his own words; every other candidate is rejected with
   a one-line why.
3. **The one-way doors.** Bring the full vision in for one purpose: nothing in v0 blocks it. Walk
   the doors (language, storage, repo shape, data shapes, platform, and any other) as the floor.
   One-way decisions become poured-concrete lines; banked decisions and deliberately-not-built
   items become deferred lines, each with why its door stays open.

## Step 4. The architecture doc

Write ONE answer file in the shape of `references/answer.schema.json` and run
`record-answer --run-dir D --answer FILE`. Every line that records a decision carries its trace: a
ledger id, a repository path, a question of this run he answered, or `assumed` with your why. List
every question you put to him with the ledger ids it touches. On a re-run, the poured-concrete and
deferred sections are given in full: each prior line carried or struck (with its trace), then the
new ones; nothing is dropped. The blind review is `pending` for now (`not-offered` on a docless
run). A refusal (exit 5) says what is wrong; fix that and record again; never argue it away.

Then run `write --run-dir D`. The script renders a new doc or continues the living one: a new
`### Run <N>` block, superseded lines struck through, never deleted, the header's lines in their
order. A `document-changed` stop means the doc moved under the run: its bytes are left as found.

## Step 5. The visual

Run `render-visual --run-dir D`: `<slug>-architecture.html` lands beside the doc, rendered from the
doc. Then publish it as a separate step, through your harness's own artifact tool, privately, never
anywhere public: on a re-run pass the doc's recorded `Artifact:` URL as the tool's `url` (the same
URL across runs; omitting it makes a second artifact). Then run
`record-publish --run-dir D --url <the URL it returned>`, or without `--url` when it returned none
(the result will say the doc was rendered and not published). With `publish: false` in the answer,
skip the publish and run `record-publish --run-dir D` so the result names the skip.

## Step 6. The blind review

Only when the run had a scope doc. Ask him once, as one plain-text question, whether he wants an
outside-model review and from whom (the reviewers are readers roster rows; the default GPT row
alone is the default; a bare "yes" is that row and nothing more). Run readers' `suggest` for the
rows first, so the question shows what each would run.

On his word in this run, and only then:

1. Run `request --run-dir D --row <row>` once per reviewer he named (`--session-model` for the
   `claude-session` row). Each request sends the scope doc ONLY, never your doc, never this
   conversation, with the fixed instruction the contract quotes, `profile: starved`. `authorized`
   rides only on an outside row his word in this run's input names; a row he names only at this
   offer has no word in this run's input, and readers refuses it. Tell him so, run `report` (it
   stops `review-pending`), and start a new run on the same doc whose input carries his words
   verbatim in `owner_word` (`rows` the rows he named); that run's `request` carries `authorized`.
   Never add the flag or the word by hand.
2. Summon `/readers` with each request; a call the harness backgrounds past its foreground limit is
   not a failure: wait for its notification and judge what arrives. A `READERS:` status other than
   `ok` is a failed review for that lane: nothing is saved for it, the other lanes still run, and a
   retry happens only on his word. The review is done when at least one take was saved (each lane
   that failed goes in the amended answer's `review.failed_lanes`, its row and the `READERS:`
   reason), and `failed` when none was.
3. Where the harness delivers the reply with entities in it, unescape HTML entities (`&amp;`,
   `&lt;`, `&gt;`) in the raw text before `save-take`; it is the only transformation the file ever
   gets. Then run `save-take --run-dir D --row <row> --take <raw text file> --model <effective
   model> --isolation <label> --sidecar <sidecar path>` for each take, before any triage. The file
   is never edited afterwards.
4. Walk him through every disagreement between the doc and the takes, one at a time; he rules
   each. Nothing merges silently.

Then record the amended answer (`record-answer` again), once per run: the review's outcome
(`declined` with the date, `failed` with the date and reason, or `done` with what the takes agreed
on and any `failed_lanes`) and one ruling per disagreement with the fields it changes. The doc
changes only where a ruling says so. Run `write`, `render-visual` and `record-publish` again (the
same URL), so the picture never lags the doc. A second amendment is refused: more rulings need a
new run.

## The gate

Run `report --run-dir D` and print its `chat` block as it stands. A `review-pending` stop means the
review has no outcome yet. Then stop. Never invoke another loop station: the read-back points the
owner at provisioning and at blueprint-v2, and he moves. A gate he collapsed in his invocation is
yours to act on; record his words in the answer's `changed`.

When running this station required working around, reinterpreting, or excepting one of its rules,
add one line marked `SKILL NOTE:` under the block: what and why, for the station's author.

## The rules

1. **User-invoked only.** He types it or it does not run.
2. **The scope doc is the input.** Without one, the gate discussion lands on a recorded reason first.
3. **The exit ramp is real.** It comes first; a "no" ends the interview with a tiny doc, not no doc.
4. **Candidates or it didn't happen.** Two or three, distinct in a one-way-door category, before he picks.
5. **The razor cuts.** Every v0 component points at a walkthrough requirement or it is out.
6. **Decide for the vision, build for the walkthrough.** Banked decisions are recorded, never provisioned.
7. **Doc and visual only.** No repositories, databases, hosting, accounts or installs; no other loop
   station, except `/readers` for the blind review.
8. **The property line is absolute.** Outside unknowns become `NEEDS CHECK` lines.
9. **One living doc.** Continued with a run block and strikethroughs; never a fork, never a rewrite.
10. **Blind means blind.** The scope doc only, on his word in this run only; he rules every disagreement.
11. **Keep it short.** Ceremony that delays the MVP is the failure mode.

## References

| File | Read it | For |
|---|---|---|
| `references/architect-v2-contract.md` | before Step 1, and when a refusal or a stop is unclear | every command, refusal, stop and field |
| `references/answer.schema.json` | before Step 4 | your answer's shape |
| `references/station-loop.md` | when a shared phase or exit code is unclear | what the four front stations share |
| `references/templates/architecture-doc.md` | when the doc's form is unclear | the load-bearing form, rendered by the script |
| `references/examples/` | when a shape is unclear | accepted and rejected inputs, answers and results |
| `adapters/README.md` | before Step 1 | your harness's profile and helper |
