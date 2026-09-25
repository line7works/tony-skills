# The architect core contract, version 1

What `architect-v2` does, what it is allowed to write, when it stops, and what every word in its
answer and its result means. This document, `station-loop.md` beside it (the contract the four
front cores share) and the schemas under `references/` are the interface a caller writes against;
everything under `scripts/architect_core/` and `scripts/station_core/` is internal.

Written for E14 slice 2, lane A, against the E14 lane contract (`docs/plans/2026-09-24-stations-e14.md`,
sections 6, 8, 10 and 14). Where this document and that contract differ, the contract is the
authority and this document is the defect.

Contents: 1 The job · 2 What is kept from v1 · 3 The commands · 4 The input · 5 Selection and
harvest · 6 The recorded answer · 7 The write · 8 The result · 9 Stops · 10 The blind review ·
11 The visual and the publish · 12 Records, report-only, the gate · 13 Exit codes · 14 The seeded
families · 15 Open points.

## 1. The job

The drawings step between precon and everything downstream: one interview that produces one living
architecture doc, the least structure that serves a named first user's walkthrough, with the
one-way doors settled for the whole vision and their construction left for the walkthrough that
needs it; and a visual of what was decided.

**The executor decides, this core records** (ruling E14-4). The executor runs `SKILL.md`: it talks
to the owner, judges, and hands its judgment over as ONE recorded answer (amended once after the
blind review, section 6.5). This core validates the input, finds the documents, reads the scope
doc's ledger, checks the answer, renders and continues the doc, renders the visual, records the
publish, builds the review's reader requests, saves the takes, and writes the result. It never
judges an idea or an architecture, never publishes, never summons a reader, and never provisions.

## 2. What is kept from v1

The v1 station's six steps and eleven rules are the behavior, unchanged (ruling E14-1). Stated here
in this core's own words; no v1 file is read, named as a place to read, or deferred to (E14-7).

| v1 step | Where it lives now |
|---|---|
| 1. The input gate: the scope doc from the invocation's path, else a glob over precon's homes; several are asked, never picked; none (or none of the hits this project's, whether one or several) asks once whether one exists where the glob cannot see, and only the owner's "none" opens the docless gate, whose reason lands in the doc's header | `select --hunt scope`, the input's `station.scope_doc`, `harvest` (section 5); the answer's `docless` block and its `scope-doc` question (section 6) |
| 2. The exit ramp: "is there a system here at all?" first, answered by the owner in words; a no ends the interview and still writes a tiny doc and renders the visual | the answer's `exit_ramp`; an ended interview carries no candidates (section 6) |
| 3. The interview: the walkthrough target (a named person, a date, what they must do), two or three candidates distinct in a one-way-door category with what each assumes and makes expensive later, the razor, the pick in the owner's words, the one-way-door check at full-vision quality | the answer's `walkthrough`, `candidates`, `pick`, `rejected`, `components`, `doors`, `poured_concrete`, `deferred`; the content checks of section 6 |
| 4. The architecture doc: one living doc per project, its fixed form, re-runs continue it with a new run block and strikethroughs, never a fork and never a rewrite | `write` through the shared templates and run log (section 7) |
| 5. The visual: rendered from the doc beside it, published privately to the same URL across runs, re-rendered and republished after the rulings | `render-visual` and `record-publish` (section 11); the publish itself is the executor's, through the harness's own artifact tool (ruling E14-6) |
| 6. The blind review: on the owner's word in this run only, each named reviewer gets the scope doc alone and the fixed instruction, each take saved verbatim before triage, every disagreement ruled by the owner, the doc changed only where he rules, the review file never edited | `request`, `save-take`, the amended answer's `review` and `rulings` (section 10) |

The eleven rules, as this core holds them:

1. **User-invoked only.** `disable-model-invocation: true` and the Codex sidecar's
   `allow_implicit_invocation: false` (pick P5); the procedure starts only when the owner types it.
2. **The scope doc is the input.** Without one, the answer is refused unless it records the
   gate's reason (`docless-without-reason`) and the one question that asked (`docless-unasked`).
3. **The exit ramp is real.** `exit_ramp` is a required field; `continued: false` ends the interview
   and the answer carries no candidates (`exit-ramp-ended-with-candidates`); the doc is still written.
4. **Candidates or it didn't happen.** Two or three, pairwise distinct in a named one-way-door
   category, each with its assumption and later cost, the pick one of them, every other one rejected
   with its why (section 6.3).
5. **The razor cuts.** Every component names the walkthrough requirement it serves (`razor`).
6. **Decide for the vision, build for the walkthrough.** The poured-concrete lines are the one-way
   decisions; the deferred lines bank the rest; nothing is provisioned.
7. **Doc and visual only.** The script writes the doc, the visual, the takes and its run directory,
   nothing else; it launches nothing and publishes nothing.
8. **The property line.** An outside unknown is not looked up and not guessed: it is a `NEEDS
   CHECK` line (the answer's `lines`), rendered in the Deferred section.
9. **One living doc.** Selection finds it; several are asked; a re-run continues it with strikes
   and a new run block; the no-loss check refuses an answer that would drop a line (section 7).
10. **Blind means blind.** The scope doc alone, the fixed instruction, `authorized` only from the
    input's `owner_word`, every disagreement the owner's ruling (section 10).
11. **Keep it short.** About three answers plus the sorted scope: the procedure's rule, not the
    script's; the script counts nothing it could mistake for ceremony.

The rules that stay advice to the executor rather than checks of this core (the narrowness
guardrail, the questions in plain text with a recommendation, looking facts up on the property)
are in `SKILL.md`, because they govern judgment this core does not make.

## 3. The commands

```text
check-input <input.json>                            validate, create the run          (shared)
select --run-dir D --hunt scope                      precon's homes                    (shared)
select --run-dir D --hunt architecture --name SLUG   the living doc for the slug       (shared)
harvest --run-dir D                                  the ledger, the living doc, the target
record-answer --run-dir D --answer FILE              the executor's answer, checked
write --run-dir D                                    the doc, rendered or continued
render-visual --run-dir D                            <slug>-architecture.html beside the doc
record-publish --run-dir D [--url URL]               the Artifact: line from the publish's URL
request --run-dir D --row ROW [--row ROW ...]        the blind review's readers requests
save-take --run-dir D --row ROW --take FILE ...      one take, saved verbatim
report --run-dir D                                   the result and the read-back
identity <workspace>, skill-identity                 (shared)
```

They run in that order. `request` and `save-take` run between the first `write` and the amended
answer; `record-answer`, `write`, `render-visual` and `record-publish` run a second time after the
review (section 6.5). A command out of turn is exit 2 naming the command to run instead; a command
against a run that ended is exit 2, except `report`, which prints the recorded result again.

### Own commands

| Command | Input | Output | Exits |
|---|---|---|---|
| `render-visual` | `--run-dir D`, a run whose doc this run wrote | `<slug>-architecture.html` beside the doc (in the run's `preview/` on report-only), in the receipt; stdout `{visual, next}` | 0; 2 out of turn, or a folder on the way that leads outside the homes (section 7.4), nothing written |
| `record-publish` | `--run-dir D`, `--url URL` (the https URL the executor's publish returned: a host of dot-separated labels, an optional port and path, no space; omitted when it returned none), after a render | the `Artifact:` line written once (section 11), `publish.json` in the run; stdout `{outcome, artifact_url, reason, next}` | 0; 2 out of turn, a URL that is no such URL, a URL on a `publish: false` answer, no URL after this run recorded a published URL for the same render, or a doc folder that leads outside the homes; 5 `artifact-url-changed` with nothing written; 10 `document-changed` |
| `request` | `--run-dir D`, one `--row ROW` per reviewer the owner named, `--session-model ID` (the `claude-session` row only), `--model ROW=ID` (a typed id), `--roster FILE` (default: readers beside this core, route 3a then 3b) | one request per row under `requests/<call id>.json`; stdout `{requests: [{row, call_id, path, authorized}], mandate, next}` | 0; 2 out of turn, a docless run, no row, an unknown row, no roster, or a scope doc whose bytes are not the ones harvest read (its sha256), nothing written |
| `save-take` | `--run-dir D`, `--row`, `--take FILE` (the reply's raw text), `--model` (the effective model), `--isolation` (the isolation label), `--sidecar` (the readers sidecar path) | the take saved verbatim under the review home (the home harvest recorded for the doc) and copied under `takes/`, `takes.json`, both in the receipt; stdout `{path, copy, lane, next}` | 0; 2 out of turn, a docless run, an unreadable file, a row no `request` of this run built, or a review folder that leads outside the homes; 5 `take-empty` with nothing saved |

## 4. The input

The shared input (`station-loop.md` section 4), plus `station`, each field optional:

| Field | Meaning |
|---|---|
| `station.scope_doc` | the scope doc the owner named: in his invocation (v1's first place to look), or his pick after a `selection-several` stop. An absolute path inside the workspace or the staging home; taken over the scope hunt |
| `station.publish` | `false` when the owner said not to publish the visual in this run (E14-6); the answer then cannot publish (`publish-against-input`). Default `true`, v1's default |
| `station.docless` | `true` when no hit of the scope hunt (one or several) is this project's scope doc (each `Intent:` line names another project) and the owner, asked once, said no scope doc exists for his: every hit is set aside and the docless gate opens (section 5.2). Requires `station.docless_reason`; excludes `station.scope_doc`. Default `false`. Without it `several` stops and asks |
| `station.docless_reason` | the reason the executor states for the docless run, one line, only with `station.docless: true`, holding at least one visible character (the invisible set is the frame's, every character `answer._visible` drops or `str.strip` removes: whitespace, format and zero-width characters, the default-ignorable code points and the letter-shaped fillers; those alone are refused at `check-input`, exit 4): recorded with the set-aside hits, and the answer's `docless.reason` (the doc's `Docless:` header) must be this reason, byte for byte once runs of whitespace are collapsed to one space and the ends trimmed, case kept (`docless-reason-mismatch`) |

`owner_word` is the one source of a review request's `authorized` flag (section 10). The run's date
is the machine's local calendar date, read once per command; under `ARCHITECT_V2_TEST=1` the hook
`ARCHITECT_V2_TEST_TODAY` pins it, and outside a test it is ignored.

## 5. Selection and harvest

### 5.1 The hunt table

| Hunt | Home | Root | Globs | Tier | Why |
|---|---|---|---|---|---|
| `scope` | `repo-scope` | workspace | `docs/scope/*.md` | 1 | precon's home in the repository doc kit |
| `scope` | `repo-flat` | workspace | `docs/*-scope.md` | 1 | the older flat name, still read |
| `scope` | `staging` | staging | `*-scope.md` | 1 | the pre-repository staging home |
| `architecture` | `repo-architecture` | workspace | `docs/architecture/*-{name}.md` | 1 | the living doc's repository home |
| `architecture` | `repo-flat` | workspace | `docs/{name}-architecture.md` | 2 | the older flat name, continued where it lies, never moved |
| `architecture` | `staging` | staging | `{name}-architecture.md` | 3 | the staged doc |

The scope homes share one tier: v1 lists every plausible match across the three and asks, and
matching a candidate to the project by its `Intent:` line is the executor's. The architecture homes
are tiered in v1's order, so a doc in the repository's folder wins over the older flat name and the
staged copy.

### 5.2 `harvest`

It needs both selections (or `station.scope_doc` in place of the scope one). Then:

- **The scope doc.** `station.scope_doc` when given (a file inside the workspace or the staging home,
  else exit 2); else the scope hunt: `one` is taken; `several` stops the run `selection-several` with
  every candidate listed, never picked (the owner's pick arrives as `station.scope_doc` in a new
  run), unless `station.docless` is set: the owner, shown the list in an earlier run, said none of
  them is his project's; `none` is the docless path: harvest continues, and the answer must carry
  the gate (section 6). With `station.docless: true`, every hit of a `one` or a `several` is set
  aside: the scope selection (`selection-scope.json`, and so the result's `selection.scope`) gains
  `set_aside` (`paths`, each hit's path, and `reason`, the input's `station.docless_reason`),
  `harvest.json` and harvest's output carry it, the run is docless, and the architecture hunt's
  `--name` is the working name, never refused against a hit's slug (v1's gate matches candidates by
  their `Intent:` lines: when none matches, the hunt counts as zero plausible matches, the owner is
  asked once, and his "none" opens the docless gate however many files the glob found).
- **The slug.** The scope doc's idea: the `<idea>` of `docs/scope/<YYYY-MM-DD>-<idea>.md`, of a flat
  `<idea>-scope.md`, or a dateless `docs/scope/<idea>.md`, never the date. The architecture hunt must
  have run with `--name` equal to it (exit 2 naming the slug otherwise). On a docless run the slug is
  the working name the gate discussion settled, passed as that `--name`.
- **The living doc.** The architecture hunt's `one` is the living doc: its bytes are copied into the
  run (`harvested-doc.md`) with their hash, its run numbers and next run number
  (`station_core/runlog.py`), its recorded `Artifact:` URL, and its form checked
  (`station_core/templates.py`); a doc off its form stops the run `living-doc-malformed`, quoted, and
  so does a line under Poured concrete or Deferred that is no `- ` list line (a note or a heading
  the owner typed there), or a line in the head that is none of its header lines: an answer carries
  or strikes list lines only and the header lines are each run's own, so no re-run could keep it,
  and the owner fixes the doc by hand.
  `several` stops `selection-several`. `none` means a new doc.
- **The ledger.** The scope doc read by `station_core/ledger.py`: every line with its tag, source and
  stable id. A line it cannot tag stops the run `ledger-refused`, quoted, never dropped.
- **The target.** The living doc where it lies; else, following the scope doc's home,
  `<workspace>/docs/architecture/<YYYY-MM-DD>-<slug>.md` or `<staging>/<slug>-architecture.md`; on
  a docless run, the home the answer's `docless.home` names.

`harvest.json` in the run holds all of it. Nothing is written outside the run directory.

## 6. The recorded answer

`references/answer.schema.json`, closed at every level, with accepted and rejected examples under
`references/examples/answer/` (a name starting `content-<rule>` passes the schema and is refused by
that content check; any other rejected name is refused by the schema). Every text the doc carries
is one line: a line break would put a bare line, or a heading, inside a section of the form.

### 6.1 The fields

| Field | What it carries |
|---|---|
| `answer_version`, `run_id`, `session_id` | `1`; this run's id (`run-mismatch` otherwise); the executor's session, the adapter's `answer_fields.session_id`, equal to the input's `invocation.session_id` (`session-mismatch` otherwise) |
| `project`, `trigger`, `changed` | the title's project; the run log's trigger; its `Changed this run:` (`first run` on the first) |
| `questions` | every question put to the owner in this run: `id`, `text`, `touches` (the ledger line ids it touches), `answer` (blank: unanswered), optional `about` (`scope-doc` marks the input gate's one question) |
| `docless` | only when no scope doc was found (or the input set the hunt's hits aside): `reason` (the doc's `Docless:` header; with `station.docless`, the input's `station.docless_reason`) and `home` (`staging` or `workspace`) |
| `exit_ramp` | `continued` (true: a system, the interview went on) and `why` |
| `walkthrough` | `who`, `when`, `must` (a list), all present and non-blank (`n/a` is a value, blank is not), none holding the line's separator (the middle dot), no `must` item holding the list's separator (`; `, which the doc joins the items with), and its `trace` |
| `candidates` | each `name`, `categories` (`<one-way-door category>:<choice>`, such as `platform:library`), `assumes`, `later_cost` |
| `pick`, `rejected` | the picked candidate's name (null when the interview ended); each other candidate's `name` and one-line `why` |
| `components` | each `name` and `serves`, the walkthrough requirement it serves |
| `data_flow`, `diagram` | the v0 drawing's two other lines (the diagram one line: an ASCII one-liner or a one-line mermaid) |
| `doors` | `{settled}`, the one-way-door check (Step 3.3); null when the interview ended |
| `poured_concrete`, `deferred` | the section in full, in order: a new line `{text, tag, trace}`, a prior line kept `{carried}`, a prior line superseded `{strike, trace}` |
| `lines` | the `NEEDS CHECK` lines, each `{text, tag, trace}`, rendered in the Deferred section |
| `review` | `outcome`: `pending`, `declined` (with `date`), `failed` (with `date` and `reason`), `done` (with `spine`, what the takes agreed on, and optional `failed_lanes`, each lane that did not return: its `row` and the `reason` its `READERS:` line carried), or `not-offered` (a docless run only) |
| `rulings` | the owner's ruling on each disagreement: `disagreement`, `ruling`, `reviewers`, `changes` (the answer fields the ruling changes), `trace` |
| `publish`, `publish_url` | whether this run publishes; the artifact it republishes to: the living doc's recorded URL, or null on a first publish |

A line that records a decision carries its `trace`: `ledger` (a ledger line id of the scope doc),
`repo_path` (a path in the workspace), `question` (an answered question of this run) or `assumed`
(the executor's why). `owner_words` is not admitted here: the owner's words reach the doc through
the question he answered.

### 6.2 The order of the checks

`record-answer` validates the answer against the schema (exit 4, the findings on stdout, nothing
written); then runs the shared refusals of rule E14-11 once, through `station_core/answer.check`,
on the answer's neutral view (the questions, and each line that records a decision: the walkthrough
target, each new or struck poured-concrete and deferred line, each `NEEDS CHECK` line, each ruling;
a new poured-concrete line on its form, `<category> <dash> <decision> <dash> <why>`, gives a second
row whose text is its decision field, everything between the first field and the last, with the
category and the why beside it, so the shared text rule meets a `parked` or `open` line asserted
as the decision alone or as the whole line; a refusal of one line is reported once),
with the trace kinds above; then this core's own checks; then renders the proposed doc and holds it
to the no-loss check. Any refusal is exit 5 with every refusal on stdout, each `{"rule", "message",
...}`, and nothing written; the run stays where it was, so a corrected answer can be recorded.
Only then is `answer.json` written. The shared `answer.record` is not called: it writes the neutral
view as `answer.json`, and this core's `answer.json` is the whole answer; `answer.check` is the same
one implementation of the shared refusals.

### 6.3 The refusals

| Rule | When |
|---|---|
| `re-asked-decided`, `unknown-line`, `untraced`, `quietly-resolved`, `shape` | the shared refusals (`station-loop.md` section 8, rule 2): a question touching, or repeating the text of, a `decided` ledger line; an id the ledger does not hold; a decision line with no trace, a kind not admitted, or a trace that names nothing; a line asserted `decided` over a `parked` or `open` line no answered question touched |
| `session-mismatch`, `run-mismatch` | the answer's session or run is not this run's |
| `docless-without-reason` | no scope doc was found and the answer records no reason (no `docless`, or a reason of whitespace, format or zero-width characters only) |
| `docless-unasked` | no scope doc was found and no answered question `about: scope-doc` asked whether one exists where the glob cannot see |
| `docless-with-scope-doc` | a `docless` block on a run that has a scope doc |
| `docless-home` | the docless doc's home is the staging home and the input names none |
| `docless-reason-mismatch` | the input carries `station.docless_reason` and the answer's `docless.reason` is another reason: the two are compared byte for byte once each one's runs of whitespace are collapsed to one space and its ends trimmed, case kept (a re-cased reason, or one with an added invisible character, is another reason); the doc's `Docless:` header carries the reason so collapsed |
| `exit-ramp-ended-with-candidates` | the interview ended at the exit ramp and the answer still carries candidates, a pick or a rejected list |
| `candidates-fewer-than-two`, `candidates-more-than-three` | the interview continued with fewer than two candidates, or more than three |
| `candidate-names-repeat` | two candidates share a name |
| `candidates-not-distinct` | two candidates differ in no one-way-door category (their `categories` read as category and choice, each casefolded and whitespace-normalized; a difference counts only in a category both of them name, and only when they share no choice in it, so a second choice padded into a shared category is no difference) |
| `pick-not-a-candidate` | the pick is null or names no candidate |
| `rejected-mismatch` | the rejected list is not exactly the candidates not picked, once each |
| `rejected-without-why` | a rejected candidate's why is blank |
| `doors-missing` | the interview continued and `doors` is null |
| `razor` | a component serves nothing (blank), or serves something that is not one of the walkthrough's `must` items |
| `review-offer` | a scope-doc run whose review is `not-offered`, or a docless run whose review is anything else |
| `review-fields` | a declined or failed review with no date, a failed one with no reason, a done one with no spine, `failed_lanes` on a review that is not done, or a `failed_lanes` row that is no row a `request` of this run built, a row whose take was saved, or a row named twice |
| `review-no-take` | the review is `done` and no take was saved in this run |
| `rulings-without-review` | rulings on a review that is not `done` |
| `publish-against-input` | the answer publishes and the input's `station.publish` is false |
| `republish-url` | the answer publishes and `publish_url` is not the living doc's recorded URL (or is set when the doc records none), or it does not publish and names a URL |
| `unknown-prior-line` | a carried or struck entry names no line of the living doc's section (a struck one, no unstruck line) |
| `amendment-outside-rulings` | an amended answer (section 6.5) changes a field no ruling names, or rewrites an earlier question |
| `no-loss` | the proposed doc would drop a prior run-log block, a prior poured-concrete line, or any other prior line (section 7.3) |

### 6.4 What passes forward

Every `decided` ledger line reaches the doc untouched: an accepted answer touches none (touching one
is refused), and the run log's `Rulings:` line lists each by id and text after
`passed forward untouched:`. `parked` and `open` lines pass forward as they are; one asserted as
`decided` is refused unless an answered question of this run touched it.

### 6.5 The amended answer

The blind review comes after the doc and the visual (v1's order), so its outcome and the owner's
rulings arrive after the first write. A run takes one recorded answer and ONE amended answer. Before
the first write, the answer may be recorded again in full (nothing has been written from it). After
the first write, `record-answer` takes the amendment: the first answer kept as
`answer-round-1.json`, the new one checked in full, and refused (`amendment-outside-rulings`) if it
changes anything but `review`, `rulings`, `changed`, `publish_url` and questions added after the
first ones, plus the fields a ruling names in `changes`. The amendment recorded again before its
write is held to the first answer exactly the same way, and replaces the amendment only, never the
first answer. After the amendment's write, another `record-answer` is usage (exit 2, "one amended
answer per run; start a new run for more"). The doc then changes only where a ruling says so.
`write`, `render-visual` and `record-publish` run again, and only then `report`.

## 7. The write

### 7.1 A first run

The doc is rendered by `station_core/templates.render_architecture_doc` and `render_run_block` from
the answer and the harvest, never typed: the title `<project>` and the run's date; `Scope doc:` (the
path, workspace-relative inside the workspace) or `Docless:` (the reason); `Blind review:`; no
`Artifact:` line until the first publish. The walkthrough line joins the `must` items with `; `;
`Components:` lists each component with the requirement it serves; the poured-concrete and deferred
lines are the answer's; the run block is `### Run 1`. The values the run block carries: the exit
ramp's answer and why; Step 3.1 the walkthrough target, Step 3.2 the candidates with their
categories, the pick and each rejected candidate with its why, Step 3.3 `doors.settled` (each of the
three `n/a` with the dash and `exit ramp` when the interview ended); `Rulings:` the review's line
(below) and the passed-forward list; `Changed this run:`.

The header's either-or forms, one each: `Blind review:` reads `none yet` while the review is
pending, `declined <date>`, `failed <date>` with the dash and the reason, `none` with the dash and
`docless`, or each saved take as `<path> (<model>, <date>)`, comma-separated. The run log's
`Rulings:` reads `none yet`, `declined`, `failed` with the dash and the reason, `not offered` with
the dash and `docless`, or `blind review: agreed on <spine>; N disagreements: 1. <disagreement>:
<ruling> (<reviewers>); ...`, then `; passed forward untouched: ...`.

### 7.2 A re-run

The living doc is continued in place: the title stays; the header lines are this run's, in their
order (Scope doc or Docless, Blind review, Artifact); in the walkthrough and the v0 drawing a line
whose value changed is struck through (`~~...~~`) and the new line goes below it; the
poured-concrete and deferred sections are the answer's entries in order (new, carried, struck); the
run log keeps every block byte for byte and gains `### Run <N>`, N one more than the highest
(`station_core/runlog.append_run`). Nothing is deleted.

### 7.3 The no-loss check

Before `answer.json` is written, and again before the doc is: `runlog.losses` against the harvested
doc (a prior run-log block dropped or changed, a prior poured-concrete line dropped) and, for every
other non-blank line of the harvested doc outside the three header lines, that it survives as it was
or struck through. A loss is `no-loss` at `record-answer` and stops `write-refused` at `write`; in
both, nothing is written.

### 7.4 The receipt

Every write of the run is in `<run_dir>/receipt.json` in order: `path`, `kind` (`document` outside
the run directory, `run_artifact` inside it), `sha256_before`, `sha256_after`. A document is written
through a temporary file in its folder and a rename. Before any document write (`write`,
`render-visual`, `save-take`, `record-publish`), the real path of the target's nearest existing
folder must lie inside the home the target's own path names (the workspace, the staging home or
the run directory): a symlinked folder that leads anywhere else, outside every home or from the
workspace into the run directory or the staging home, stops `write` `write-refused` and makes the
own commands usage, with nothing written, so the result never lists a write at a path it did not
write. Then the bytes on disk are
compared with what the run expects there (the harvested hash, or the hash this run last wrote): a
difference stops the run `document-changed` with the bytes left as found. A new doc's path must hold
no file.

## 8. The result

`report` needs the doc written, the visual rendered after the last write, and, when the answer
publishes, the publish recorded after the last render. It writes `result.json` (validated against
`references/result.schema.json` and the semantic checks before it lands; a result that does not hold
is exit 1, never written) and prints it with the read-back under `chat`. `writes` is the receipt,
then the receipt and the result themselves. `station_result`:

| Field | Meaning |
|---|---|
| `doc_path`, `run_number`, `visual_path` | the doc, its run block, the visual |
| `published`, `artifact_url`, `publish_outcome` | true only when the publish's URL is recorded; the doc's `Artifact:` URL; `published`, `skipped` (publish: false), `rendered-not-published` (no URL returned), `not-reached` (a stop before it) |
| `project`, `slug`, `scope_doc`, `docless` | what the run drew and from what |
| `candidates`, `pick`, `rulings_count` | the candidates' names, the pick, the number of rulings |
| `review`, `review_reason`, `review_files`, `review_failed_lanes` | the review's outcome, a failure's reason, the takes saved, and beside a done review each lane that did not return (`row`, `reason`) |
| `passed_forward` | the decided ledger ids passed forward untouched |
| `counts` | components in v0, poured-concrete decisions, deferred items (unstruck lines) |

The read-back is v1's block rendered from the result: `ARCHITECT:`, `Doc:`, `Artifact:` (the URL, or
which of the two named non-publishes), `Run:`, `Counts:`, `Review:` (a done review reads `done at
<files>` and then, for each failed lane in v1's own words, `, with <lane> failed`, the dash and the
reason), the `Next:` line, and on a stop the tag and its reason.

## 9. Stops

A stop is `status: stopped` with one tag and a result. The shared tags this core emits:
`selection-several` (harvest, either hunt), `ledger-refused` (harvest), `write-refused` (write, a
loss the answer's check did not catch, or a doc folder that leads outside the homes, section 7.4). It never emits `phase-not-built`, `selection-none` (a docless
run continues) or `records-refused`.

### Own stop tags

| Tag | Phase | When |
|---|---|---|
| `living-doc-malformed` | harvest | the living doc does not hold its form, holds a line under Poured concrete or Deferred that is no list line or a line in its head that is no header line, or has CR line endings; continuing it would mean guessing |
| `document-changed` | write, record-publish | the doc's bytes are not the bytes this run harvested or last wrote; nothing written, the bytes as found |
| `review-pending` | report | the blind-review offer has no outcome, so the doc's `Blind review:` line still reads `none yet` |

## 10. The blind review

Only on a run with a scope doc, after the doc and the visual. The executor asks the owner once
whether he wants an outside-model review and from whom. On his word:

- `request` builds one readers request per reviewer he named, through
  `station_core/readers_request.build`: `protocol_version` 1, `run_id` `<run id>-review`, a `call_id`
  per reviewer, `row` the roster row, the scope doc as the single document, `profile: starved`,
  `session_model` on `claude-session` only, a typed model id as `model`, and this mandate verbatim:

<!-- mandate -->
> You are the architect. Read the attached precon scope doc and return your own full architecture-and-delivery take for it: the walkthrough target, a v0 drawing (component list, plain-prose data flow, one simple diagram), the poured-concrete list of one-way decisions, and the deferred list. You have no other input; do not ask for any.
<!-- /mandate -->

- The packet is the scope doc harvest read: `request` refuses (usage) when the file's sha256 is not
  the harvested one, so neither an edited scope doc nor another file under its name is sent.
- `authorized: true` is set by the shared builder alone: only on a row whose provider is not
  `anthropic` and that the input's `owner_word.rows` names, never remembered between runs. A row the
  owner named after `check-input` has no word in this run's input: the executor ends the run with
  `report` (`review-pending`) and starts a new one whose input carries his words (section 15, point 1).
- The executor summons `/readers` with each request. A call the harness backgrounds past its
  foreground limit is not a failure: the executor waits for its notification. A `READERS:` status
  other than `ok` is a failed review for that lane: nothing is saved for it, the other lanes still
  run, and the amended answer's `review.failed_lanes` names it beside a done review (done when at
  least one take was saved; `failed` when none was).
- The executor unescapes HTML entities (`&amp;`, `&lt;`, `&gt;`) the harness put in the raw text,
  the only transformation the take ever gets; `save-take` then saves it as given, and only for a row
  a `request` of this run built.
- `save-take` saves each non-empty take verbatim, before any triage: the first line names the row,
  the effective model, the isolation label and the sidecar path, then a blank line, then the reply as
  it came. The home: `<workspace>/docs/reviews/<YYYY-MM-DD>-architect-review-<slug>-<lane>.md` for a
  repository doc, `<staging>/architect-reviews/<slug>-review-<YYYY-MM-DD>-<lane>.md` for a staged
  one (`<lane>`: `gpt` for the GPT rows, `gemini`, `claude` for the Claude rows); a same-day repeat
  appends `-2`, `-3`, never overwriting. A copy lands under the run's `takes/`. The review file is
  never edited.
- The executor walks the owner through every disagreement; his rulings, and the review's outcome,
  arrive in the amended answer (section 6.5).

## 11. The visual and the publish

`render-visual` writes `<slug>-architecture.html` beside the doc from the doc's own content (the
title, the walkthrough target, the components, the data flow, the diagram, the poured-concrete doors
and the deferred list, each unstruck line): a page body with `<title>` first, every value escaped,
no style, no script, no link, no image and no external resource. Nothing else is written.

The publish is the executor's separate step, through the harness's own artifact tool, privately, to
the same URL across runs (the tool's `url` parameter is the doc's recorded `Artifact:` URL on a
re-run). `record-publish` records what it returned:

| The answer and the call | Outcome | The `Artifact:` line |
|---|---|---|
| `publish: false` | `skipped`, named in the output and the result | untouched |
| `publish: true`, no `--url` (the publish returned none) | `rendered-not-published`: the doc was rendered and not published | untouched |
| `publish: true`, `--url` and the doc records none | `published` | written once, below `Blind review:` |
| `publish: true`, `--url` equal to the recorded URL | `published` | unchanged |
| `publish: true`, `--url` another URL | refused, `artifact-url-changed`, exit 5 | untouched |
| `publish: true`, no `--url` after this run recorded a published URL for the same render | usage, exit 2: the republish is recorded with the same URL | untouched |

A run that re-renders after the rulings records the republish before `report`; when that
republish returned no URL, the record without `--url` is taken (`rendered-not-published`, the
line as it stands) and `report` says the doc was rendered and not published.

## 12. Records, report-only, the gate

**Records.** architect-v2 writes no event and never opens the records component (ruling E14-9): an
architecture doc carries no finding and no card move.

**Report-only.** Every phase and own command reads `report_only` from the run's input. In that mode
the doc and the visual land in the run's `preview/` folder and the takes in its `reviews/` folder;
nothing is written to the workspace or the staging home; the result says `wrote_nothing: true`. A
report-only run still selects, harvests, checks the answer and renders.

**The gate.** Every run ends by reading back and stopping. No other loop station is invoked: the
read-back points at provisioning and at blueprint-v2 and stops. A collapsed gate in the owner's
invocation is the executor's to act on, recorded in the answer's `changed` with his words.

## 13. Exit codes

`station-loop.md` section 2: 0 the command did its work; 1 a defect; 2 usage (out of turn, a missing
file, a slug that does not match); 3 `jsonschema` missing (`--help` works without it); 4 the answer
fails its schema; 5 the answer, the publish record or the take refused on its content, nothing
written; 10 the run reached a terminal status.

## 14. The seeded families

The families under `evals/seeded-cases/` that exercise this core, and the facts each run records
(`observe.py`, with this core's `lane_observe.py` for the lane steps); what a fact should be is the
answer key's, outside this repository's lane.

| Family | What it plants | The facts recorded |
|---|---|---|
| A1 no re-interview | a decided ledger line re-asked; a poured-concrete line with no trace; a trace that names nothing; a clean answer | `answer_refused`, `refusal_rules`, `answer_written` (the shared refusals on the case's answer) |
| A2 candidates and the razor | one candidate; two in one category; a component serving nothing; a clean answer | `answer_refused`, `refusal_reason` (this core's candidate and razor checks, the ones `record-answer` runs) |
| A3 the living doc | a proposed doc dropping the run-log blocks; deleting a poured-concrete line; a wrong run number; a clean re-run | `next_run`, `losses_count`, `runlog_refused`, `form_holds`, `round_trip_identical` |
| A4 two actions | `publish: false`; a publish that returned no URL; a clean publish to the recorded URL | `visual_rendered`, `published`, `artifact_line_unchanged`, `terminal_status` (a real drive of this core's CLI, `check-input` to `report`, in the case's own built tree, so the frame's `writes_none` measures the drive; the translation's choices are stated in `lane_observe.py`) |

## 15. Open points

1. **The owner's word arrives after the input.** v1 asks the blind-review question after the doc and
   the visual; `authorized` comes only from the input's `owner_word`, fixed at `check-input`. A row
   the owner names only at the offer is built without `authorized`, and readers refuses an outside
   row without it. The executor can carry the word when the owner gives it in his invocation; for a
   later word, ruled: the executor ends this run and starts a new one whose input carries the word;
   this core does not widen the source. The procedure (`SKILL.md` Step 6) says so: tell the owner,
   run `report` (it stops `review-pending`), and start a new run on the same doc whose input carries
   his words verbatim in `owner_word`, never the flag or the word added by hand.
2. **The diagram is one line.** The form puts the diagram on its label line; a multi-line value
   would put bare lines inside the v0 drawing that a re-run could not strike as one.
