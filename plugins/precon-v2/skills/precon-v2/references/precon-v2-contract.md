# The precon core contract, version 1

What `precon-v2` does, what it is allowed to write, when it stops, and what every word in its
result means. This document, `station-loop.md` beside it (the contract the four front cores
share) and the schemas beside them are the interface a caller writes against; everything under
`scripts/precon_core/` and `scripts/station_core/` is internal.

Written for E14 slice 2, lane P, against the E14 lane contract (section 9, the precon core;
section 14, its seeded families P1 to P3; rulings E14-1 to E14-12). Where this document and that
contract differ, the contract is the authority and this document is the defect.

Contents: 1 The job · 2 What is kept from v1 · 3 The sitting and its runs · 4 The input ·
5 The recorded answer · 6 The write · 7 The exit test · 8 The report · 9 Report-only ·
10 The result · 11 The hunts · 12 Stops · 13 The records component · 14 The gate ·
15 The seeded families · 16 Exit codes · 17 What this core never does · 18 Open points ·
19 Interface.

## 1. The job

The idea stage. The owner talks an idea out; when it gets serious he summons the station, which
harvests what was already said, asks only the load-bearing questions that remain, and lands every
settled decision in the scope doc with its source, so the interview never happens twice.

**The executor decides, this core records** (ruling E14-4). The executor, the model running
`SKILL.md`, talks to the owner, triages, asks, and hands its judgment to the script once per run
as the recorded answer. `scripts/precon.py` validates the input, finds the scope doc, reads its
ledger, counts the board, checks the answer, renders and writes the documents, builds the exit
test's readers requests and reads their results, and writes the result. It never judges an
idea, and every line it writes carries who concluded it.

## 2. What is kept from v1

v1 precon's six steps and nine rules are the behavior, unchanged (ruling E14-1). They are restated
here in this core's words; no v1 file is read at run time or deferred to.

| v1 step | Where it lives now |
|---|---|
| 1. Harvest before asking (the conversation, the property, an existing scope doc) | the executor reads the conversation and the repository; `select --hunt scope --name <idea>` finds an existing doc in its three homes, `harvest` reads its ledger with ids and counts; the parked and open items it lists are re-opened by the executor |
| 2. Triage aloud (`napkin`, `bounded`, `architectural`), the owner's override in a word | the answer's `triage` (`tier`, `why`); the tier is welded into the doc as its header comment when the doc is born; the napkin outcome "no scope doc" is `triage.no_scope_doc` and ends the run `no-scope-doc` with no file |
| 3. Frontier rounds, numbered questions with a recommendation, only-if-it-differs, the counted board | the executor asks; the board each round opens with is `state`'s count of the doc as it stands, never remembered; each round is a run, so the doc changes between rounds and the next count sees it |
| 4. The ledger as you go, the out-of-scope channel, suggest-only, the doc's placement | the answer's `lines` and `out_of_scope`; `write` appends them at the tail of their sections (section 6); the file is born after triage, at the first settled line, in the home section 6 names |
| 5. The exit test: the cold read offered as one numbered question, the readers named, the cold-read doc verbatim, the dispositions | the own command `request`, readers' own summon (the executor's), the answer's `exit_test`, and `write` (section 7) |
| 6. The gate: read back, one written line justifying the ending, full stop | the answer's `gate` and `sitting`, `report`'s chat block, and the stop (section 14) |

The nine rules, and where each is held:

| v1 rule | Held by |
|---|---|
| 1. User-invoked only | `disable-model-invocation: true` in `SKILL.md` and the Codex sidecar's `allow_implicit_invocation: false` (pick P5) |
| 2. Harvest before asking | `SKILL.md` step 1; `harvest` runs before `record-answer` accepts anything (exit 2 out of turn) |
| 3. The property line is absolute: no web, no research, no research subagents; outside research is parked `needs research` | the script has no network and reads only the workspace, the staging home and the run directory (readers' roster and the sidecars a cold-read doc names excepted); a question marked `needs_research` must leave a parked `needs research` line and is never resolved in the run: no decided or assumed line, no out-of-scope item and no parked line of another reason traces to it (`research-not-parked`, `research-resolved`) |
| 4. Facts are looked up, decisions are asked | `SKILL.md`; a line may trace to a repo path, which `record-answer` confirms exists in the workspace |
| 5. Record, don't decide: every line traces to the owner's words or an answered question; unsettled means open or parked | the shared refusals (`untraced`, `quietly-resolved`) and precon's own (`decided-without-source`, `assumed-without-why`, `parked-without-reason`, `open-without-call`, `source-kind`, `retagged`, the last also refusing a ledger line's words repeated under another trace, so no line gains a twin) |
| 6. Questions earn their slot; the rest is `assumed` with its why | the `assumed` trace kind carries the why; an assumed line without one is refused |
| 7. Suggest only, never act; nothing external sends without the owner's word in the run | the script invokes nothing and sends nothing; `request` refuses an outside row the input's `owner_word` does not name, and `authorized` comes from that field alone |
| 8. One living doc | the scope hunt's three homes at one tier: `several` stops the run and is listed, never picked; `one` is continued in place |
| 9. The gate is real | record-answer's `gate-missing` refusal; `report` runs only after `write`, so no run without a gate line completes (section 14) |

## 3. The sitting and its runs

A run is one pass of the station loop (`station-loop.md` section 1): `check-input`, `select`,
`harvest`, then the executor's work with the owner, then `record-answer`, `write`, `report`. A
run records one answer, so a sitting of several rounds is several runs, one per round, and every
decision lands in the doc at the end of the round it settled in; the next round's `harvest` and
`state` count the doc that round left. The exit test is a run of its own (section 7), and the
dispositions of its cold read are recorded by a later run.

```text
check-input <input.json>                              validate, create the run
select --run-dir D --hunt scope --name IDEA           find the scope doc (three homes, one tier)
select --run-dir D --hunt cold-read --name IDEA       only for a run that records dispositions
harvest --run-dir D                                   read the doc, its ledger, its board
state --run-dir D                                     the board as the doc stands, any time after select
request --run-dir D --row ROW [--row ROW ...]         the exit test's readers requests
record-answer --run-dir D --answer FILE               the executor's one answer, checked
write --run-dir D                                     the documents, with a receipt
report --run-dir D                                    the result and the chat block
```

Each phase runs in that order and refuses to run out of turn (exit 2). A phase command against a
run that has ended prints the recorded result again and writes nothing (exit 10). `state` is
read-only and runs at any phase after `select`.

**`harvest`** reads the scope selection (it needs `--name`: the idea's slug is what the doc is
found and named by). On `several` it stops `selection-several` and lists the candidates. On `one`
it reads the doc through the ledger reader (a line it cannot tag stops the run `ledger-refused`,
quoted with its line number) and against the form (`form-refused` with the findings; a triage
comment off its form, `<!-- precon-v2 triage: <tier> -->` with one of the three tiers, or a second
comment, is a finding too), then
records the doc's header (title, date, intent, and the tier from the header comment when there
is one), its sha256, its ledger (every line with its tag, source and stable id), its counts and
its board, and keeps a copy of the bytes it read in the run directory. On `none` it records where
a new doc would go (section 6); with `home` `repo` the workspace must be a git work tree root
(exit 2 otherwise). Before either, an entry the scope globs match that the hunt did not take (a
symlink leaving its home, a broken link, something that is not a file) is exit 2 naming it,
nothing written: one living doc, so the run neither forks a second doc beside it nor continues it.
A `cold-read` selection, when the run made one, is recorded with each candidate's sha256 and the
rows that have a section in it (section 7). The new doc's folder must resolve inside the workspace
or the staging home: a symlinked folder that leaves them is exit 2, nothing written; the cold-read
doc's folder is checked the same way by `request`, the one run that builds a cold read, so a stray
`docs/reviews` never blocks a run with no exit test. Output: `harvest.json` in the run directory,
printed.

**`state`** prints `{"doc", "counts", "board"}`: the scope doc this run left (the doc it wrote,
else the one it selected) read through the ledger reader now, and the board
`decided N · assumed N · parked N · open your-calls N` (the `open` count is the `Open:` items).
A doc the reader refuses prints `counts: null` and the refused lines.

## 4. The input

`references/input.schema.json`, the shared base plus precon's `station` fields:

| Field | Meaning |
|---|---|
| `station.home` | where a NEW scope doc goes: `repo` (the default), `<workspace>/docs/scope/<date>-<idea>.md`, the workspace a git work tree root; `staging`, `<staging>/<idea>-scope.md`, when no repository owns the idea (the input then carries `staging`, which the schema requires). An existing doc is continued where `select` found it |
| `station.date` | the date a new doc and a cold-read doc are named and titled with, `YYYY-MM-DD`; absent, `harvest` takes the machine's local calendar date and records it |
| `owner_word` | the owner's words in this run and the readers rows they name: the one source of a request's `authorized` (section 7); `words` holds at least one character that is not whitespace (blank words name no row, exit 4 at `check-input`) |
| `invocation.session_id` | the executor's session as the adapter read it; the answer's `session_id` must equal it |

## 5. The recorded answer

`references/answer.schema.json` (closed at every level; examples under
`references/examples/answer/`). The schema holds the shape; the content rules are refusals,
exit 5, each named, and nothing is written.

| Field | What it carries |
|---|---|
| `answer_version`, `run_id`, `session_id` | `1`; this run; the executor's session (`run-mismatch`, `session-mismatch`) |
| `triage` | `tier` (`napkin`, `bounded`, `architectural`) and `why`; `no_scope_doc: true` is the napkin outcome |
| `doc` | a new doc only: its `title` and its `intent` |
| `questions` | every question put to the owner in this run: `id`, `text`, `touches` (the ledger line ids it touches), `answer` (verbatim, absent or blank when unanswered), `needs_research` |
| `lines` | every line asserted: `text`, `tag` (`decided`, `assumed`, `parked`, `open`), `trace` (`kind`, `ref`); a parked line's `reason`, an open line's `waits_on` |
| `out_of_scope` | what the owner ruled out: `text`, `reason`, `trace` |
| `research` | paths or links to research the owner did himself |
| `open_items` | unresolved threads for the next sitting |
| `exit_test` | the cold read (section 7) |
| `sitting` | `ends` on the sitting's last run; `continues` on a round that hands on to the next |
| `gate` | the one-line justification (section 14) |

The trace kinds a line may carry (`station_core/answer.py`'s `allowed`, all five): `ledger` (a
ledger line id of the doc this run read), `question` (a question of this run the owner answered),
`owner_words` (his words quoted), `repo_path` (a path that exists in the workspace), and
`assumed` (the executor's why, on assumed lines only). The out-of-scope items are checked with the
lines.

**The checks, in order.** The schema (exit 4). Then `station_core/answer.check` over the
questions and every asserted line (the shared refusals, one implementation, never copied here:
`shape`, `re-asked-decided`, `unknown-line`, `untraced`, `quietly-resolved`), and precon's own
rules over the whole answer; every refusal of both is listed at once. Then, only when both are
clean, the documents are planned exactly as `write` will write them and read back (below). Then
`station_core/answer.record` writes `answer.json`. Any refusal: exit 5, the refusals on stdout,
nothing written, the run where it was, so a corrected answer can be recorded.

| Rule | Refuses |
|---|---|
| `run-mismatch` | an answer naming another run |
| `session-mismatch` | a `session_id` other than the input's `invocation.session_id` |
| `decided-without-source` | a decided line whose trace is an assumption; an assumed ledger line asserted as decided with no answered question of this run touching it (a decided line with no trace at all is the shared `untraced`) |
| `assumed-without-why` | an assumed line whose trace is not its why (a blank why is the shared `untraced`) |
| `parked-without-reason` | a parked line whose reason is none of the three: `needs research`, `needs prototype`, `waiting on <x>` (with what it waits on named) |
| `open-without-call` | an open line that does not say which of the owner's calls it waits on |
| `source-kind` | a new parked or open line, or an out-of-scope item, traced to anything but the owner's words or a question he answered (an assumption is no source, and what he ruled out is his ruling) |
| `retagged` | a line traced to a ledger line under another tag, other than the one move a question can make: a parked, open or assumed line settled as decided; a parked line passed forward with another reason; a line whose text repeats a `Decisions:` or `Open:` ledger line's (whitespace collapsed, case folded) under any trace but that line's id, whatever its tag and whether or not a question touched the line: the doc would hold the line and its twin |
| `research-resolved` | a line resolving a question marked `needs_research`, a parked line of another reason or an out-of-scope item traced to one, or a parked or open ledger line whose only touching questions are marked `needs_research` asserted as decided |
| `research-not-parked` | a question marked `needs_research` that leaves no parked `needs research` line traced to it and touches none |
| `napkin-outcome` | `no_scope_doc` outside the napkin tier, with any line, item, doc field or exit test, over an existing doc, or with a `sitting` other than `ends` (the napkin outcome ends the sitting) |
| `doc-fields` | a new doc with a settled line and no title or intent; doc fields on an existing doc (its title and intent are kept as found) |
| `gate-missing` | no gate, a blank one (nothing but whitespace and format characters, a zero-width space or a byte-order mark among them), or one on more than one line |
| `unrenderable` | a value the documents cannot carry and read back: a text or detail on two lines, a blank item, a source holding the form's own separator, a planned doc the ledger reader or the form check would refuse |
| `exit-test-rows` | an exit test whose rows are not the rows this run built requests for; requests built and no exit test recorded |
| `exit-test-unrecorded` | a built request with no result readers recorded (no sidecar, or one naming another call) |
| `disposition-before-raw` | dispositions in the run that writes the readers' raw text |
| `disposition` | a disposition outside `surfaced`, `absorbed`, `left downstream`; left downstream with no why; a row with no section in the doc; no summary |
| `cold-read-doc` | dispositions for a cold-read doc this run did not select |

The E14-11 rule on the precon side: a parked or open line is never rewritten as decided unless
an answered question of this run touches it (the shared `quietly-resolved`, which also catches
the line's words asserted as decided under another trace kind), and a question that touches a
decided line re-asks it (the shared `re-asked-decided`). Precon's `retagged` covers the rest of
the twin case: a ledger line's words asserted under any trace but its id (an assumed line's, a
decided line's, or a parked or open line's after a question touched it) are refused, so a line
is settled only in place, by its id, and the doc never holds a line and its twin. Both refusals
are computed and listed together.

**A needs-research question.** Its `answer` is the owner's words parking it (the shared
`untraced` needs an answered question behind the parked line that traces to it); the script
cannot judge what those words say (E14-4), so it refuses every way the run could record a
resolution instead: a decided or assumed line, an out-of-scope item, or a parked line of another
reason traced to the question.

## 6. The write

`write` plans the documents from the harvest and the accepted answer, the same plan
`record-answer` read back, and writes them. Every write goes through a temporary file and a rename
and is listed in `receipt.json` in the run directory (`path`, `kind`, `sha256_before`,
`sha256_after`); `report` copies the receipt into the result's `writes`.

**Before anything is written**, each target is hashed again: the scope doc must still hash as
harvest read it, a new doc's path must still be free, a cold-read doc must still hash as it did.
A difference stops the run `doc-changed`: nothing is written, and every byte is as found. So does
a target whose folder has come to resolve outside the workspace and the staging home.

**The lines an answer adds.** A line traced to a ledger line under its own tag passes that line
forward and writes nothing. A parked or assumed `Decisions:` line settled as decided is rewritten
in place, under the same text and so the same ledger id: `- <text> <dash> decided (answer to <Q>
(run <run id>): <the owner's answer>)`. A settled `Open:` item leaves `Open:` and its decided line
is appended to `Decisions:`; an item written inline on the label line (`Open: <item>`, the form
`render_scope_doc` writes for one item, this core's own new docs included) leaves the label alone,
`Open:`, the form's line for zero items, and the no-loss check counts that label line as rewritten,
never dropped. A new line renders through `templates.render_ledger_line`: decided
with its source from its trace (`the owner's words: "<quote>"`, `answer to <Q> (run <run id>):
<answer>`, `the repo: <path>`), assumed with its why, parked with its reason. An open line lands in
`Open:` as `<text> (waits on: <call>)`; an out-of-scope item as `<text> <dash> <reason>`.

**A new doc** is born only after triage and only at the first settled line (a decided, assumed or
parked line, or an out-of-scope item); a run that settles nothing writes no file and says so. It is
`templates.render_scope_doc`'s output (the v1 form byte for byte, E14-12) with one added line
after the title, the triage comment `<!-- precon-v2 triage: <tier> -->`, at
`<workspace>/docs/scope/<date>-<idea>.md` (home `repo`) or `<staging>/<idea>-scope.md` (home
`staging`). Taken out, the comment leaves the rendered form exactly; the doc passes
`templates.check` and round-trips byte for byte.

**A continued doc** changes only by insertions at the tail of each section (new `Decisions:` lines
after the last `Decisions:` item and so above `Out of scope:`, never below it; new items at the
tail of `Out of scope:`, `Research:` and `Open:`), the one comment line when the doc has none (a
doc that has one keeps it as found; one off its form stopped the run at `harvest`), and the
lines this answer settled. Every other prior line is byte-identical, and the plan checks it
before writing: a plan that would drop or change another line refuses at `record-answer`
(`unrenderable`). The doc's line endings are kept. Its title and intent are never touched.

**A napkin run** that took "no scope doc" writes nothing at all.

## 7. The exit test

When the frontier empties, the executor offers the cold read as one numbered question (v1's
three options: a Claude reader, the default, needing no word; an outside row, named, sent only on
the owner's word in the run; decline). The owner's words that name an outside row go into the
NEXT run's input as `owner_word`; that run is the exit test.

**`request --run-dir D --row ROW [--row ROW ...] [--model ROW=ID] [--session-model ID]`**
builds one readers request per named row through `station_core/readers_request.build`:
`protocol_version` 1, the run's id as `run_id` (the sitting's cold read runs under it),
`call_id` `<run id>-<row>`, `row`, the scope doc as the single document, `profile: starved`,
`run_dir` `<run_dir>/readers` (readers' own run directory for these calls), `session_model` on
`claude-session` only, `model` only where the owner typed one against that row, and `authorized:
true` only on a row whose roster provider is not `anthropic` and which the input's `owner_word`
names; never on an anthropic row, never remembered. The mandate is v1's cold-reader prompt,
verbatim:

```mandate
read this scope doc — what's unclear, what would you ask before building this?
```

Precon's rule on top of the shared builder: an outside row the owner's word does not name is not
built. Every refusal of `request` (an unnamed outside row, an unknown row, no row, a row twice, no
scope doc, a `--model` for a row not requested, readers not installed beside this core, a
cold-read folder resolving outside the workspace or the staging home) is exit 2 with the reasons
on stderr and nothing written. On success the requests are written under `<run_dir>/exit-test/`
with an index, `requests.json`, and printed. readers' roster is found the way the records
component is, and only so: the readers plugin folder beside this plugin's (route 3a, a checkout),
then the highest version folder of readers beside this plugin's own folder (route 3b, the
installed shape). No flag names another roster: a roster of the caller's choosing could relabel
a Claude row's provider and carry `authorized` onto it.

The executor summons `/readers` with each request (the script never does). readers records each
call's result at `<run_dir>/readers/<call id>/sidecar.json`. The answer's `exit_test.rows` names
the rows; `record-answer` reads every sidecar from disk (the executor types none of it) and
refuses a call with none. `write` then writes **the cold-read doc**, before any triage, at
`<workspace>/docs/reviews/<date>-precon-cold-read-<idea>.md` for a repo-owned scope doc or
`<staging>/precon-cold-reads/<idea>-cold-read-<date>.md` for a staged one: a header (`# Precon
cold read: <idea> (<date>)`, the scope doc, the run), then one section per `ok` call, headed
`## <row> · <effective model>`, the sidecar path under the heading, and the reader's `raw_text`
verbatim. A call whose status is not `ok` gets no section; the result lists it by status and
reason. An existing cold-read doc of the same name gains the new sections at its tail. The scope
doc's `Research:` gains the pointer `cold read: <path relative to its home>`.

**The dispositions** are a later run's: `select --hunt cold-read --name <idea>`, then an answer
whose `exit_test` names the `cold_read_doc` (one of the candidates; `several` is the owner's to
pick), a one-line `summary`, and `dispositions` (each `row`, `item`, `disposition`: `surfaced`,
`absorbed`, `left downstream` with its `why`), each for a row with a section in that doc. A row
has a section when a `## <row> · <model>` heading is followed by a `Sidecar:` line naming a
`sidecar.json` that readers recorded, `ok`, for that row; a heading inside a reader's raw text
with no such sidecar behind it is text, never a section. `write` inserts one block,
`## Disposition (<date>, run <run id>)`, above the doc's first section; every byte below it is
kept. The confusions the owner took reopen branches: that run's questions and lines are an
ordinary round.

## 8. The report

`report` assembles the result (section 10), validates it against `references/result.schema.json`
and the shared semantic checks S1 to S4 before writing it (a result that does not validate is a
defect, exit 1, and the run stays at the phase it was, never ended without its `result.json`),
writes `result.json`, and prints it (exit 10). A repeated `report` prints the same result and
writes nothing. The doc, the counts, the board and the parked lines it reports are the ones `write`
recorded in `receipt.json` from the text it wrote (or previewed, or found unchanged), never the
doc on disk by the time `report` runs, which a hand may have changed since.

- A run that wrote (or planned, under report-only): `completed`, with `station_result`.
- A run that recorded the napkin outcome: `stopped`, `no-scope-doc`.
- A run that has not written (only checked, selected or harvested, or answered and not written): the wrong phase, exit 2 on stderr naming the command to run next (`select`, `harvest`, `record-answer`, `write`), nothing written. An abandoned run is abandoned: it has no result.

**The chat block** is v1's read-back, rendered from the result, v1's lines first in v1's order:
`PRECON: <idea>`, `Doc: <path>` (the napkin line when there is none, `none (no settled line yet)`
when nothing settled, `(report-only: not written)` under report-only), `Counts: decided N ·
assumed N · parked N · out of scope N` from the doc as the run left it, one `Parked:` line per
parked line with its tag (`Parked: none` when there is none), and `Next: /blueprint when ready.`
(or, on a round whose sitting continues, `Next: the next round (the sitting continues).`). Then a
blank line and the lines this core adds: one `Exit test:` line per call (`row · status · model` or
the reason), the `Cold read:` doc, and `Gate: <the gate line>`.

## 9. Report-only

`report_only: true` in the input. Every phase still runs: `harvest` reads, `request` builds its
requests (run artifacts), `record-answer` checks and records the answer in the run directory,
`write` plans every document and writes each one as a preview under `<run_dir>/preview/`, listed
in the receipt's and the result's `planned` (path, preview, the target's hash as found), and writes
nothing to the workspace or the staging home. The result says `wrote_nothing: true` and lists run
artifacts only.

## 10. The result

The shared result (`station-loop.md` section 5), with precon's `station_result`, closed:

| Field | Meaning |
|---|---|
| `idea`, `doc`, `home` | the slug; the scope doc as the run leaves it (or null); `repo` or `staging` |
| `tier`, `triage_why` | the answer's triage |
| `counts` | v1's report counts from the doc as the run left it: `decided`, `assumed`, `parked`, `out_of_scope` |
| `board` | `decided N · assumed N · parked N · open your-calls N` from the same read |
| `parked` | each parked line with its tag |
| `exit_test` | `calls` (each `row`, `call_id`, `status`, `reason`, `effective_model`, `section`) and `cold_read_doc` |
| `planned` | report-only: the documents the run would have written, each with its preview |
| `candidates`, `ledger_refused`, `form_findings` | on the stops that name them |
| `sitting` | `ends` or `continues` |
| `chat_block` | section 8 |
| `gate` | the gate line, the last field; required and non-blank on every `completed` result |

## 11. The hunts

| Hunt | Home | Root | Glob | Tier |
|---|---|---|---|---|
| `scope` | `repo-scope` | workspace | `docs/scope/*-{name}.md` | 1 |
| `scope` | `repo-flat` | workspace | `docs/{name}-scope.md` | 1 |
| `scope` | `staging` | staging | `{name}-scope.md` | 1 |
| `cold-read` | `repo-reviews` | workspace | `docs/reviews/*-precon-cold-read-{name}.md` | 1 |
| `cold-read` | `staging` | staging | `precon-cold-reads/{name}-cold-read-*.md` | 1 |

The scope homes are v1's three places for an existing doc under the slug, all one tier: v1 ranks
none above another, so a doc in two homes is `several`, listed for the owner and never picked
(rule 8). The cold-read homes are where section 7 writes. `none` on the scope hunt is not a stop:
the run proceeds and a doc is born at the first settled line.

## 12. Stops

A stop is `status: stopped` with one tag and a reason. The shared tags this core emits, for their
shared meanings only, and its own:

| Tag | Phase | When |
|---|---|---|
| `selection-several` | `harvest` | the idea's scope doc is in more than one home; the candidates are listed |
| `ledger-refused` | `harvest` | the doc holds a line the ledger reader cannot tag; each is quoted with its line number |
| `form-refused` | `harvest` | the doc departs from the form (a label missing or out of order, a section the form has not, a triage comment off its form or a second one), so nothing can be placed in it; the findings are listed |
| `doc-changed` | `write` | a target changed after harvest (the doc edited by hand, a file appeared at the new doc's path, a cold-read doc changed); nothing was written |
| `no-scope-doc` | `report` | the napkin outcome: the owner took no scope doc; nothing was written. It is `stopped`, not `completed`, because the run produced no document |

`selection-none`, `write-refused`, `records-refused` and `phase-not-built` are never emitted by
this core (an empty hunt is not a stop here; a write that would lose a prior line is refused at
`record-answer`, before any write; the records component is never opened; every phase is built).

## 13. The records component

precon-v2 writes no event and never opens the records component (ruling E14-9): a scope doc
carries no finding and no card move. No test of this core touches `plugins/records/`.

## 14. The gate

Every answer carries its `gate`: one line, the executor's justification that every branch was
visited or parked (on a round whose `sitting` continues, what the round visited and what it
leaves open). An answer without one is refused at `record-answer` (the rule `gate-missing`, exit 5,
nothing written), and `report` runs only after `write`, so an accepted answer always carries its
gate; a `completed` result carries the gate as the last field of
`station_result`, and the schema refuses a completion without it. After the read-back the
executor stops: no building, no next station, unless the owner collapsed the gate in his own
invocation, which the executor records in the gate line in his words.

## 15. The seeded families

Facts each family exercises (the outcomes live in the control room's answer key):

| Family | What it drives | The facts |
|---|---|---|
| P1 ledger traceability | the ledger reader on the scope doc; the recorded answer against its ledger (the shared refusals precon's `record-answer` calls) | `ledger_refused`, `ledger_refused_lines`, `ledger_tags`, `answer_refused`, `refusal_rules`, `answer_written`, `writes_none` |
| P2 one living doc | the real `check-input` and `select --hunt scope --name turnstile` over zero, one and two homes and the flat name | `selection_outcome`, `selection_candidates`, `writes_none` |
| P3 the exit test | `readers_request.build` per named row against readers' roster, with and without the owner's word | `authorized_rows`, `request_documents`, `request_profiles`, `writes_none` |

No step of these families is a `lane` step, so `evals/seeded-cases/lane_observe.py` fills no
name in them; it drives the real CLI for any `lane` step naming the facts above (its own test,
`scripts/tests/test_lane_observe.py`, drives it on every case of the three families, and through
the frame's hook with a planted unlisted name). A name the drive gives no fact for stays pending:
the P1 answer facts do, since the neutral answer carries no triage and no gate and precon-v2's
schema refuses it (exit 4) before any traceability rule runs. It never sets a `_via` entry the
frame already set.

## 16. Exit codes

`station-loop.md` section 2's table, as this core uses it:

| Code | Here |
|---|---|
| 0 | `harvest`, `state`, `request`, `record-answer` accepted, `write` |
| 1 | a defect of the script, an unreadable run directory, a result that does not validate |
| 2 | usage: out of turn (`report` before `write` included, the next command named), a missing selection or name, a file not there or not JSON, a refused `request`, a repo home that is not a git work tree root, a write folder resolving outside the workspace and the staging home |
| 3 | `jsonschema` missing (`check-input`, `record-answer`, and every result) |
| 4 | the answer fails `references/answer.schema.json` |
| 5 | the answer refused on its content (section 5) |
| 10 | the run reached a terminal status: a stop of `harvest` or `write`, and every `report` after `write` |

## 17. What this core never does

- judge an idea, or decide what the owner meant: the executor's, recorded with its session;
- write a line with no source, or rewrite a parked or open line as decided without the answered
  question that settled it;
- pick among several docs, or fork a second doc for an idea that has one;
- write below `Out of scope:` what belongs in `Decisions:`, or change a prior line it did not
  settle;
- send a reader anything, summon a skill, or build a request for an outside row the owner's word
  does not name;
- reach the network, call a model, launch a harness, or read anything outside the workspace, the
  staging home and the run directory (readers' roster beside it, and the readers sidecars a
  selected cold-read doc names, excepted);
- open the records component;
- relocate a doc: that is the owner's, or sunrise's when it adopts a staged doc.

## 18. Open points

- **One answer per run, so one run per round.** v1 lands each decision "the moment it settles";
  here it lands at the end of the round it settled in, since a run records one answer. A sitting
  interrupted mid-round loses that round's unrecorded answers, as a v1 sitting interrupted
  mid-question would.
- **The triage comment.** The contract (section 9) puts the tier in the doc's header comment; the
  v1 form has no comment line. The comment is one added line after the title, which the form
  check, the ledger reader and the round trip all pass over. A continued doc that has none gets
  one; one that has one keeps it as found, and the run's own tier is in the result.
- **The answer of a needs-research question.** Section 5 keeps it as the owner's words parking
  the question, since the shared `untraced` needs an answered question behind the parked line;
  a rule refusing any answer on such a question would refuse every parked research line. What the
  words say is the executor's (E14-4); the script refuses every way the run could record a
  resolution.
- **The neutral seeded answers carry no triage and no gate.** A real drive of `record-answer` on
  them refuses at the schema; the families' `answer` steps drive the shared library, which reads
  only `questions` and `lines`.

## 19. Interface

Tables a test reads (`scripts/tests/test_contract_document.py`): each own command is listed in
the driver's `--help` and nothing else is; each stop tag is in the result schema's enum and its
description; `SKILL.md` names every command it runs; the mandate above is the one the code sends.

### Shared commands

| Command | Arguments | Exit codes |
|---|---|---|
| `check-input` | `<input.json>` | 0, 1, 2, 3, 4 |
| `select` | `--run-dir D --hunt scope` or `--hunt cold-read`, `--name IDEA` | 0, 1, 2 |
| `harvest` | `--run-dir D` | 0, 1, 2, 10 |
| `record-answer` | `--run-dir D --answer FILE` | 0, 1, 2, 3, 4, 5, 10 |
| `write` | `--run-dir D` | 0, 1, 2, 10 |
| `report` | `--run-dir D` (after `write`) | 1, 2, 3, 10 |
| `identity` | `<workspace>` | 0, 2 |
| `skill-identity` | none | 0 |

### Commands of this core

| Command | Arguments | Exit codes |
|---|---|---|
| `state` | `--run-dir D` | 0, 1, 2 |
| `request` | `--run-dir D --row ROW [--row ROW ...] [--model ROW=ID] [--session-model ID]` | 0, 1, 2, 10 |

### Stop tags

| Tag | Shared or own |
|---|---|
| `selection-several` | shared |
| `ledger-refused` | shared |
| `form-refused` | own |
| `doc-changed` | own |
| `no-scope-doc` | own |
