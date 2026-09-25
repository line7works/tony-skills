# The inspect-v2 core contract, version 1

What `inspect-v2` does, what it may write, when it stops, and what every word in its result means.
This document, `references/station-loop.md` (what the four front cores share) and the schemas
beside them are the interface a caller writes against; everything under `scripts/inspect_core/`
and `scripts/station_core/` is internal. Written for E14 slice 2 of the skills v2 rebuild (lane I)
against the E14 lane contract (`docs/plans/2026-09-24-stations-e14.md`, sections 6, 8, 12 and 14,
amendments A1 to A3). Where this document and that contract differ, the contract is the authority
and this document is the defect.

Contents: 1 The job · 2 What is kept from v1 · 3 The phases · 4 The input · 5 The core's own
commands · 6 The hunt, the packet and the requests · 7 record-answer · 8 write · 9 report ·
10 Report-only · 11 Stops · 12 The records · 13 The gate · 14 The seeded families · 15 Open points.

## 1. The job

A build doc is about to become a builder's only source of requirements. Before `build-v2` runs
it, fresh inspectors read it against its record (the scope doc), the code book (blueprint-v2's
installed `SKILL.md`) and the repository, with a mandate to find reasons to reject it. Their
verified findings are raised in the shared records, the station's own QUESTION or clean lines and
a stamp naming the model that inspected are written into the build doc, and a verdict mirror is
filed under `docs/reviews/`. A bad plan approved is the loop's most expensive defect, because the
builder builds the mistake faithfully.

**The executor decides, this core records** (ruling E14-4). The executor is the model running
`SKILL.md`: it asks the owner which lane runs, summons the readers, adjudicates what they report,
and hands its judgment over once, as the recorded answer. The script validates, finds, packs,
builds requests, verifies citations mechanically, talks to the records component, renders and
writes. It never judges a plan or a finding, and what was concluded is recorded with who
concluded it: the reader's call id and effective model, the executor's session.

## 2. What is kept from v1

Ruling E14-1: nothing v1 inspect decided changes. Its five steps and ten rules are the behaviour;
what moved is where the deterministic half lives (this script) and where the findings are kept
(the records component, pick P8). No v1 file is read, run or deferred to (ruling E14-7): every
mechanic v1 took from signoff by reference is stated here in this core's own words.

| v1 step | Where it lives now |
|---|---|
| 1. Gate and hunt | `named` for a doc the invocation names by path, else `select --hunt build`; `select --hunt scope`; `choose` for a listed tie; and `harvest` (sections 3, 5, 6) |
| 2. The ask | before `check-input`: the row the owner named and, for an outside row, his words, are data in this run's input (section 4); `request --suggest` holds the send to the model he saw |
| 3. The lenses | `packet` and `request` build the packet and the fleet's requests; the executor summons readers |
| 4. Verify and adjudicate | the executor's adjudications in the answer, the mechanical pass in `record-answer` (section 7) |
| 5. The verdict and the two writes | `write` (the records append and the block, the station's lines and the stamp, the mirror) and `report` (the chat block) |

The ten rules, as this core keeps them:

1. **Summon only.** The station runs when the owner types it by name, never because a plan looks
   ready (`disable-model-invocation: true`; the Codex sidecar's `allow_implicit_invocation: false`).
2. **Fresh inspectors originate; the session merges, verifies and adjudicates.** Every finding
   carries the reader call id this run's `request` built; a result with none, or with another
   call id, is refused (`independence`).
3. **The packet is the record.** The build doc, the scope doc (or the station's one no-record
   line) and the code book, by their bytes, numbered; nothing else. `request` refuses a packet
   directory holding anything more.
4. **The ask is real.** Every run, the owner names the lane; nothing is remembered between runs;
   `authorized` is set from this run's input alone.
5. **Evidence or it does not count.** Every finding carries its location; a locationless one never
   reaches the result; a citation that matches nothing is a refutation.
6. **No record is not invention.** With no scope doc, an untraceable item is a QUESTION for the
   owner, never an automatic BLOCKER, and the run says it is weaker.
7. **Stop at the verdict.** Additive writes only: the records block, the station's own lines, the
   stamp, the mirror. No fix, no plan edit, no `Status:` line, no verdict word in the build doc.
8. **The stamp names the model.** `<model>` is the effective model the readers' result carries,
   never a typed id; a run that cannot read one stops with no stamp.
9. **The review mechanics are this contract's own** (the list below), stated here so nothing is
   imported by silence.
10. **Anti-rubber-stamp.** Every verdict states what was hunted and not found, every run: the
    answer's `hunted_and_held` (with its `bottom_line`) is required by the answer schema, so an
    answer without it is refused (exit 4) and nothing prints a fallback; both are printed in the chat
    block and the verdict mirror.

The review mechanics, restated (signoff-v2's contract sections 1, 5, 6 and 7 are the pattern;
the words and the plan-stage meanings are this core's):

- **The finding shape.** claim (one sentence), location (`<packet file>:<line>` against the
  numbered packet; a repository `file:line` for repo reality), failure scenario (what the builder
  would wrongly build, or what a grader could not check), severity, confidence (high, medium,
  low). A reader reports everything; filtering belongs to the verify pass.
- **Verify before reporting.** Every outside finding of every severity, and every Claude-lane
  BLOCKER and MAJOR, is verified against the numbered packet before it reaches the result, and
  carries CONFIRMED or PLAUSIBLE; what is refuted is dropped and counted (`Refuted: N`).
  Claude-lane MINORs pass UNVERIFIED. Section 7 says what the script checks and what the executor
  decides.
- **Severity, plan-stage meaning.** BLOCKER: the plan as written would build a mistake (an
  invented requirement presented as settled, an uncheckable criterion on a load-bearing item, a
  wrong repository fact a slice depends on, a slice-integrity break, a missing or malformed
  load-bearing form that breaks a downstream station). MAJOR: a real defect of the doc, fixable in
  place. MINOR: a rough edge. QUESTION: unverifiable against a missing or silent record; never
  gating.
- **Severity to verdict,** arithmetic over the surviving findings: any BLOCKER is **REJECTED**; no
  BLOCKER and any MAJOR is **APPROVED WITH CONDITIONS** (the named MAJORs fixed before build); no
  BLOCKER and no MAJOR is **APPROVED**. The words are the plan check's own and never signoff's.
- **Report, never repair.** The station reports; the owner adjudicates; the drafting session
  amends on his word; a re-inspection is a fresh run. No invocation wording collapses that gate.
- **The additive ledger.** Nothing already in the build doc is rewritten or removed; the records
  log only grows; inspect-v2 raises and never clears (no `disposition`, no `waived`, ever).

One v1 behaviour retires under pick P8: a re-inspection writes no `fixed | not fixed` line for a
prior inspect finding (v1's closure record for the loop's open-filter). Inspect clears nothing; a
prior finding stays open in the records log, which carries its closure, until a station that
clears, or the owner's waiver, decides it.

One v1 exception is kept as v1 stated it: signoff's model floor does not bind here. The lane the
owner picks is this station's floor and the model-named stamp is the compensating trust label, so
no request this core builds carries a `floor`.

## 3. The phases

`scripts/inspect_v2.py`, run through `uv run` (station-loop.md section 2 for the exit codes). Every
command prints one JSON document on stdout; a phase run against a run at the wrong phase is exit 2
naming the command to run instead.

| Phase | Reads | Writes (all in the run directory unless named) | Prints | Exits | Stops |
|---|---|---|---|---|---|
| `check-input <input.json>` | the input | `input.json`, `checkpoint.json` | `next: select` | 0, 2, 3, 4 | none |
| `select --hunt build --name N` / `--hunt scope` | the homes of the hunt (section 6) | `selection-<hunt>.json` | the hunt's result | 0, 2 | none |
| `named` (own) | the doc the invocation names | `selection-build.json` (`one`, home `named`), the checkpoint | the choice | 0, 2 | none |
| `choose` (own) | a hunt's `several` | the choice in `checkpoint.json` | the choice | 0, 2 | none |
| `harvest` | the settled build doc and scope doc, the code book, the records component | `harvest.json`, `sources/` (a copy of each document as read) | what was harvested | 0, 2, 3, 10 | `selection-none`, `selection-several`, `build-doc-unreadable`, `code-book-missing`, `records-refused` |
| `packet` (own) | `sources/`, readers' roster | `packet/<lens>/` (three numbered files each), `packet.json` | the directories | 0, 2, 3 | none |
| `request` (own) | the packet, the roster, `--suggest` | `requests/<call id>.json`, `outside/<call id>/packet.md`, `requests.json` | the calls to summon | 0, 2, 3, 5, 10 | `model-changed` |
| `record-answer --answer FILE` | the answer | `answer.json`, the raw copies' banner (`banner.json`), `triage.json` | the counts, the verdict | 0, 2, 4, 5, 10 | `lane-down`, `no-effective-model` |
| `write` | the triage, the build doc, the records component | the log (through the component), the build doc, the mirror; `receipt.json`, `write.json` | what was written | 0, 2, 3, 10 | `write-refused`, `records-refused` |
| `report` | every artifact | `result.json` | the result and the chat block | 10, 2 | the tag the run reached |

What `harvest` collects: the build doc (path, workspace-relative path, bytes' hash, line count, its
`## Slice` sections with their line spans and `Status:` values, the stamps it already carries, the
form findings `templates.check` reports, which are the code-book lens's to judge and never a
gate); the scope doc when one was settled, with its ledger read by `station_core/ledger.py` (a line
the reader cannot tag is quoted under `ledger.refused` and the plan is still inspected, as v1
inspects it); the code book, `blueprint-v2`'s installed `SKILL.md` through
`station_core/sibling.py` (route 3a in a checkout, then 3b installed; never a v1 file, never a
personal path); the records component through `station_core/records_link.py`, confirmed at
interface version 2 through `component-identity`, and the head of the build doc's log read through
`events` (64 zeros for a log that does not exist), pinned for `write`. `harvest` keeps a copy of
each document in `sources/`, so the packet is the record exactly as harvested.

Every stop, at any phase, goes through one path: the result is assembled from the run's artifacts,
validated (the schema and S1 to S4), written to `result.json`, and printed with the chat block
(exit 10); the checkpoint reads `done`, and `report` prints the same result again.

## 4. The input

`references/input.schema.json`: the shared fields (station-loop.md section 4) and under `station`:

| Field | What it is |
|---|---|
| `row` | the readers row the owner named at the ask. Required by `packet` and `request` (exit 2 without it); not by `select` or `harvest` |
| `model` | a model id the owner typed against the row, sent as that row's `model`; absent, readers resolves the row's own |
| `displayed_model` | the model the ask showed for the named row (from `readers suggest`); `request` then needs `--suggest` and compares |
| `session_model` | the model id the executor's session reports for itself, on every `claude-session` request |

The owner's word for an outside row is the shared `owner_word` field (`rows` and his words
verbatim); it is the one source of `authorized` (station-loop.md rule 5). Because the word must be
data in this run's input, the ask comes before `check-input` (section 15, point 1).

## 5. The core's own commands

| Command | Input | Output | Exits |
|---|---|---|---|
| `named` | `--run-dir D --path P`, after `check-input`, instead of `select --hunt build`: the build doc the invocation names (absolute, or relative to the workspace) | `selection-build.json` as the hunt's `one` (candidate home `named`, tier 0), the named doc and its scope directory in `checkpoint.json`; `harvest` then takes it | 0; 2 when the path is not an existing `.md` file, lies outside the workspace by its real path (a link out included), the run is past `select`, or `select --hunt scope` already ran (run `named` first) |
| `choose` | `--run-dir D --hunt build\|scope --path P --by intent\|owner [--words TEXT]`, after `select`, at a hunt whose outcome was `several` | the choice recorded in `checkpoint.json` (`path`, `by`, the owner's words); `harvest` then takes it | 0; 2 when the hunt was not `several`, the path is not one of the listed candidates, or an owner's pick carries no words |
| `packet` | `--run-dir D [--readers-root DIR]`, after `harvest` | `packet/<lens>/` for each lens of the named row's lane, each holding exactly `build-doc.md`, `scope-doc.md` or `no-record.md`, and `code-book.md`, numbered `N: `; `packet.json` with each file's hash | 0; 2 no `station.row`, a row not in the roster, a packet already built; 3 readers not found |
| `request` | `--run-dir D [--suggest FILE] [--readers-root DIR]`, after `packet` | one request per lens under `requests/`, `requests.json`; for an outside row the filled mandate `outside/<call id>/packet.md` | 0; 2 a displayed model and no `--suggest`; 3 readers not found; 5 the packet refused (the file named, nothing built); 10 `model-changed` |

`choose` never picks: it takes only a path the hunt listed, and says who decided (`intent`: the
executor matched the candidate's `Intent:` line to the feature, v1's rule for a scope doc and for
a build doc no filename matches; `owner`: the owner named it, with his words). `named` never hunts:
it takes the one path the invocation named, checked and recorded, v1's "the invocation names a
build doc".

## 6. The hunt, the packet and the requests

**The hunt table** (`scripts/inspect_v2.py` `HUNTS`, v1 Step 1's homes):

| Hunt | Tier | Home | Globs | Why |
|---|---|---|---|---|
| `build` | 1 | `repo-plans` (workspace) | `docs/plans/*-{name}.md` | the repo doc kit's folder, matched by the doc's topic |
| `build` | 2 | `repo-flat` (workspace) | `docs/{name}-build-plan.md` | the older flat name; a tier-1 match beats it |
| `build` | 3 | `phase-or-slice` (workspace) | `docs/*phase*.md`, `docs/*slice*.md`, `plan/*.md` | the fallback, then nowhere else |
| `scope` | 1 | `repo-scope` (workspace) | `docs/scope/*.md` | precon's folder, by glob, never a guessed slug |
| `scope` | 1 | `repo-flat` (workspace) | `docs/*-scope.md` | precon's older flat path |
| `scope` | 1 | `staging` (the staging home) | `*-scope.md` | precon's pre-repository home |
| `build` | 0 | `named` (the invocation) | none: `named --path P` | v1: "the invocation names a build doc, or the skill hunts" |
| `scope` | 1 | `named-dir-scope`, `named-dir-flat` (workspace), only for a doc `named` outside every build home | `<its directory>/scope/*.md`, `<its directory>/*-scope.md` | v1 Step 1: a named doc outside the homes gets its own directory's `scope/*.md` and `*-scope.md` |

The lowest tier holding a candidate decides. When no filename matches (a `none` from the build hunt
with a `--name`), the executor runs `select --hunt build` without `--name`, matches the listed docs
by their `Intent:` lines and records the match with `choose --by intent`: a filename match beats an
Intent match, and when two tiers match by filename the lower tier's doc is taken and the chat block's
`Selected:` line names it, how it was taken, and every doc another tier matched. A doc `named` lies
outside every build home when its directory is none of `docs/plans`, `docs` and `plan`; the two
named-dir scope homes are recorded in the run's checkpoint by `named` and added by
`scripts/inspect_v2.py` for that run alone (`gate.hunts_for_run`, which reads `--run-dir` the way the
driver's parser does, abbreviations included), and are listed in `searched`. `named` after
`select --hunt scope` is usage (exit 2, "run `named` before `select --hunt scope`"), and `harvest`
refuses (exit 2) a scope selection of a named doc outside the build homes that never searched them,
so a scope doc beside the named doc is never lost into the no-record rule. `several` is listed and never picked: the executor
matches a scope doc by its `Intent:` line or puts the list to the owner, and records the result
with `choose`. Only a `none` from the scope hunt applies the no-record rule; a `none` from the
build hunt stops the run (`selection-none`: a plan that lives only in the conversation is not
inspectable).

**The packet.** One fresh directory per lens per run, `<run dir>/packet/<lens>/`, never shared and
never reused, holding exactly three files numbered `N: `: `build-doc.md`, `scope-doc.md` or
`no-record.md` (holding the one line below), and `code-book.md`. The lenses of a Claude row
(provider `anthropic` in readers' roster) are `traceability`, `code-book` and `repo-reality`; an
outside row's are `paper` and `repo-reality`. Never in a packet: a summary, a prior verdict, repo
code, another reader's output, this session's account. `request` holds every packet directory to
that rule before it builds anything: a file or folder not named, a dotfile, a link, a missing file,
or a file whose bytes changed after `packet` wrote them is refused, exit 5, each refusal naming the
file, and nothing is built.

The no-record line, verbatim:

```text
NO RECORD — no scope doc exists for this feature.
```

**The requests,** built by `station_core/readers_request.py` (the one place `authorized` is
decided), `protocol_version` 1, `run_id` the run's, `run_dir` `<run dir>/readers`, one call id per
lens: `<run id>-traceability`, `<run id>-code-book`, `<run id>-repo-reality`, and for an outside
row `<run id>-<row>`.

| Lens | Row | Documents | Profile | Mandate |
|---|---|---|---|---|
| `traceability` | the named Claude row | `build-doc.md`, then `scope-doc.md` or `no-record.md` | `packet-only` | the traceability text, then the reporting paragraph |
| `code-book` | the named Claude row | `code-book.md`, `build-doc.md` | `packet-only` | the code-book text, then the reporting paragraph |
| `repo-reality` | the named Claude row, or `claude-session` beside an outside row | `build-doc.md`, `workspace` the repository | `repo` | the repo-reality text, then the reporting paragraph |
| `paper` | the named outside row | `packet.md`: `references/inspect-mandate.md` with its three slots filled from the lens's packet | `packet-only` | the outside line |

`authorized: true` rides only on the outside call whose row the input's `owner_word.rows` names,
never on a Claude row. The accept path holds the same line: `record-answer` refuses a status-`ok`
result of an outside call whose request carried no `authorized` (`unauthorized-send`, section 7),
so no finding is raised and no stamp is written under a row the owner never named in this run. `session_model` rides on `claude-session` calls; `model` on the named row's
calls when the owner typed one; `raw_path` on the outside call,
`<workspace>/docs/reviews/<YYYY-MM-DD>-inspect-<feature>-<lane>.md` (`gpt-*` rows file as `gpt`),
and never in a report-only run. No request carries a `floor` (section 2). Repo reality is the one
lens that reads the repository, under the `repo` profile, as v1 has it in every lane; the packet
rule governs the paper lenses.

The mandates, verbatim (the v1 station's fixed texts; the long dashes are v1's):

Traceability:

```text
You are the traceability inspector. The build doc is about to become a builder's only source of requirements. Every requirement, rationale, and criterion in it must trace to the record (the scope doc, or the repo, which a separate local inspector checks: mark repo-grounded claims 'repo-grounded, not checked here'). Hunt faux context: plausible detail presented as settled that the record never established. When the record is NO RECORD, an untraceable item is 'unverifiable — needs confirmation', never asserted as invented.
```

Code book:

```text
You are the code-book inspector. Grade the build doc against the code book, quoting the code book's rules, never paraphrasing: checkable criteria (would a grader know pass from fail), self-containedness (could a builder who was never in the room execute it), slice integrity (dependency order, ends wired in, independently verifiable, ceremony scaled), and the exact load-bearing forms downstream stations key on (section names, Status labels, the ledger scaffold, ·-separated fields).
```

Repo reality:

```text
You are the repo-reality inspector. Every path, component, command, and convention the build doc names must exist in the workspace as claimed; check each against the repository and report what does not hold, with the repo file:line where it should have been.
```

The reporting paragraph that ends every Claude-lane mandate, after one blank line:

```text
Your mandate is to find reasons to REJECT the plan. Report EVERY finding, low-confidence ones included; filtering is the verifier's job, not yours. Each finding: claim (one sentence) · location (`<doc>:<line>` using the `N: ` numbers on the documents; repo `file:line` for repository findings; a finding you cannot pin goes under 'Concerns without location') · failure scenario (what the builder would wrongly build, or what a grader could not check) · severity (BLOCKER: the plan as written would build a mistake · MAJOR: a real doc defect fixable in place · MINOR: a rough edge · QUESTION: unverifiable against a missing or silent record) · confidence (high / medium / low). End with what you attacked that held up, and a one-paragraph judgment: would you approve this plan for construction.
```

The outside call's mandate line (its instructions travel in `packet.md`):

```text
Inspect the build doc per the packet's instructions and report every finding.
```

**The ask, the lane-down rule and a changed model.** One paper inspector per run; an answer naming
several lanes is several runs, each with its own run id. A call whose result is not `ok` stops the
run `lane-down` (section 7): nothing from the lane is triaged and the ask is re-asked; the lane the
owner then names runs as a fresh run. When the ask displayed a model for the row
(`station.displayed_model`), `request` needs this run's later `readers suggest` output
(`--suggest`) and stops `model-changed` when it shows another model for that row: the send goes
out under the model the owner saw, or waits for his word.

## 7. record-answer

`references/answer.schema.json`: the executor's document with the readers' results inside it
(`results`, one per lens call, each `call_id`, `row`, `effective_model`, optional `status`,
`reason`, `raw_path`, `isolation`, `parity`, and `findings`, each `severity`, `location`, `claim`,
`scenario`, `confidence`, optional `lens` and `quote`). The executor's fields: the shared
`answer_version`, `run_id`, `session_id`, `questions`, `lines`; then `row`, `owner_word` (only for
an outside row), `lanes` (the lenses that ran), `adjudications` (per finding `<call id>#<n>`:
`confirmed`, `plausible`, `refuted` or `question`, each with its why), `hunted_and_held` and
`bottom_line`.

Three layers, in order: the schema (exit 4); the shared E14-11 refusals through
`station_core/answer.py` `check`, with the scope doc's ledger lines (exit 5); this core's own rules
(exit 5). On 4 and 5 nothing is written and the run stays where it was. Only then does
`station_core/answer.py` `record` write `answer.json`.

| Rule | Refused when |
|---|---|
| `run-mismatch` | the answer names another run |
| `session-mismatch` | the answer's `session_id` is not the input's `invocation.session_id` |
| `row-mismatch` | the answer's `row` is not `station.row`, or a result's row is not the row its request was built for |
| `owner-word-mismatch` | an owner word on a Claude row, or one that differs from the input's |
| `independence` | a result whose `call_id` is null (a finding with no reader call id has no reader), or a call id this run's `request` never built |
| `duplicate-call` | two results for one call |
| `lanes-mismatch` | `lanes` is not the set of lenses the results came from |
| `field-separator` | a claim, scenario or location holding a line break or the ` · ` separator, or an effective model a stamp cannot carry |
| `unknown-finding` | an adjudication naming no finding of the results, or one already adjudicated |
| `refuted-citation` | an adjudication keeping (`confirmed`, `plausible`) a finding whose citation matches nothing |
| `unauthorized-send` | a status-`ok` result of an outside row's paper call whose request was built without `authorized` (the input's `owner_word` names no such row): readers sends nothing for an outside row until the owner names it, so such a result was never sent under the rule, and nothing of it is raised or stamped under that row's name. The refusal names the call and the row. A result whose status is not `ok` (readers refused the unauthorized send) is not refused here: it ends the run `lane-down` |

Once the answer is written and before anything is triaged, the banner goes on top of each outside
raw copy readers filed at its request's `raw_path` under `docs/reviews/`, once, and on nothing else
(v1 Step 3). The request's own `raw_path` is the one source (recorded at `request`, in
`requests.json`), never the result's optional field: the copy at that path is bannered whether the
result names it, names none, or names a path elsewhere (a path elsewhere is left alone), and so is
every existing member of readers' same-day family of it (`-2` to `-9`, `-10` and onwards), whatever
the result names: a same-day repeat files this run's copy at a variant while an earlier run's copy
sits at the base, and the banner is idempotent, so an earlier run's bannered copy is left as it
is. `banner.json` names each write with its hashes, `write`'s receipt
opens with them, and a run that stops here or at any later tag names them in its result and leaves
no bare copy. Never in report-only (a report-only request carries no `raw_path`). Then two outcomes end the run instead
of refusing the answer: any result whose `status` is not
`ok` (stop `lane-down`, its status and reason in the stop's sentence), and any result with a null
`effective_model`, or paper calls that report more than one (stop `no-effective-model`, no stamp).

**The mechanical pass** (`inspect_core/verify.py`), written to `triage.json`:

- A citation is `<file>:<line>` or `<file>:<line>-<line>` against the numbered packet of the
  call's lens, and only against the documents that call's request carried (traceability: the
  build doc and the record; code book: the code book and the build doc; repo reality: the build
  doc; the paper call's `packet.md` carries all three); a repo-reality finding may cite a regular
  file inside the workspace, never one under `docs/records/` however it is reached (a folder link,
  a file symlink into it, a hard link to one of its files: the records log is read through the
  component's CLI only, never opened by a citation check). It matches nothing when the file is
  none of those, a packet file this packet does not hold (`scope-doc.md` in a no-record run,
  `no-record.md` beside a scope doc, for every lens), a line is past the end, or every cited line
  is blank; and, when the finding quotes the cited text (`quote`), when no cited line carries it.
- Every citation is checked, and one that matches nothing is refuted and counted, whatever the
  severity and whoever found it: every finding raised into the records log, and every QUESTION
  line, names a place in the workspace (ruling R5). Verified, in v1's sense: every outside finding
  of every severity; every Claude-lane BLOCKER and MAJOR; any finding the executor keeps by
  adjudication. A Claude-lane MINOR whose citation holds passes UNVERIFIED: its claim is nobody's to
  confirm.
- A finding with a null location never reaches the result (`locationless`, counted).
- Labels: CONFIRMED when the quote was found or the executor adjudicated `confirmed`; PLAUSIBLE
  otherwise (the citation holds and no one confirmed the claim).
- QUESTION notes: every finding of severity QUESTION; every finding the executor adjudicates
  `question`; under the no-record rule every finding of the traceability lens (and every
  paper-call finding marked `lens: traceability`); and every finding, of any lens and severity,
  that cites `no-record.md` (the NO RECORD line itself), written `no-scope-doc:<line>` with its
  claim prefixed `no scope doc exists for this feature: `. A QUESTION is never raised and never
  gates.
- `refuted` by the executor: dropped and counted, with his why.
- Dedupe on location and claim (whitespace collapsed, case folded): one finding at the highest
  severity, the converging call ids listed.
- Locations are written as the documents they name (`verify.translate`), every packet file the
  packet can hold mapped: `build-doc.md:12` becomes the build doc's workspace path, `:12`;
  `scope-doc.md` the scope doc's; `no-record.md` becomes `no-scope-doc:<line>`, naming the scope
  doc's absence (never a packet file name in the build doc, the mirror or the result);
  `code-book.md` becomes `skills/blueprint-v2/SKILL.md`. Any other packet name, or a packet file
  the run's record does not match, stands for no document of this run and is refuted. The slice
  is the `## Slice` section holding a cited build-doc line, else `plan`.
- The verdict (section 2) over the survivors; `weaker` is true with no scope doc; the stamp's model
  is the paper calls' one effective model.

## 8. write

In this order, each step checked before the next (`inspect_core/writing.py`):

1. **Before any write.** The build doc still holds the bytes `harvest` read, else stop
   `write-refused` and nothing is written; the stamp, every QUESTION line and the clean line are
   rendered by `station_core/templates.py` (`render_stamp`, `render_question`, `render_clean`,
   forms from `references/templates/inspect-lines.md`) and must parse back to themselves.
2. **The records,** only when a finding survived: one `finding_raised` per surviving finding
   (`ledger_doc` the build doc, `slice`, `severity`, `location`, `claim`, `scenario`, `raised_by`
   the effective model of the call that found it, `actor.station` `inspect-v2`, `origin` native,
   `source` the workspace identity from `records.py identity`), appended in one batch through
   `records.py append --expect-head <the head harvest pinned>`. A head that moved, or any refusal,
   is the stop `records-refused` carrying the component's own sentence; the build doc is left as
   found. Then `records.py render --run-id <run id>` gives the text of the review blocks, one per
   slice (`### <date> — review: Slice <X>`).
3. **The build doc,** one atomic rewrite of insertions only, checked additive and still holding its
   form: at the tail of `## Punch list` (created at the end when absent) the component's rendered
   text, then the station's QUESTION lines in the same block, or, with no finding and no question,
   the clean line; and the stamp `Plan: inspected <YYYY-MM-DD> by <model> · <counts>` (`· N
   QUESTION` when any; `clean` when no finding and no question), placed by v1's rule: directly
   below the previous `Plan: inspected` line, looked for only where a stamp lives (above the first
   `## Slice` heading, or, in a doc with no slice, above its ledger scaffold: never a line of a
   slice's body or a ledger section that happens to start so); else directly after the
   `Out of scope:` block (its line and the `- ` lines continuing it); else directly above the first
   `## Slice` heading. A prior stamp is never rewritten. The station writes no finding line of its own.
4. **The banner** is already on each outside raw copy: `record-answer` put it there before any
   triage (section 7); its writes open the receipt.
5. **The verdict mirror** `docs/reviews/<YYYY-MM-DD>-inspect-<feature>.md` (`-2`, `-3` on a
   same-day repeat, never an overwrite): the verdict, the scope doc, the refuted count, the stamp,
   the lenses not run on a short fleet (section 15, point 4), the block's bytes as rendered, the
   station's lines, what was hunted and held, and the bottom line; then `records.py mirrors` is
   asked and its answer kept whole, verbatim, as `mirror.answer` (section 15, point 2).

The date is the UTC date of the run's instant, the same instant every event carries.
`receipt.json` names every write with its bytes' hash before and after; the log is the component's
to keep, so its entry names the log and the result carries the heads the component reported.

## 9. report

`result.json` (`references/result.schema.json`, S1 to S4 checked before it is written), and in
`station_result`: the build doc and scope doc, `no_record` and `weaker`, the code book and its
route, the packet's directories with their file lists, the requests (lens, call id, row, profile,
documents, `authorized`), the calls with their effective models and statuses, the counts
(`blocker`, `major`, `minor`, `confirmed`, `plausible`, `unverified`, `refuted`, `questions`,
`locationless`), the verdict, the surviving findings (with their records finding ids), the
questions, the refutations, the stamp and whether it was written, the records (`log`,
`head_before`, `head_after`, `appended`), the mirror (its path, whether `mirrors` lists it, and
the component's answer whole), `hunted_and_held`, `bottom_line`, the slices already under
construction, the lenses not run, and the chat block, v1's read-back, with one line added after
`INSPECT:`, `Selected:`, naming the doc taken, its home and tier, how it was taken, and any doc
another tier matched by filename (v1: "the verdict says which doc it took"):

```text
INSPECT: <doc path>
Selected: <its folder>/ (tier N, <home>), <how>[; also matched by filename, outranked by the lower tier: <docs>]
Verdict: APPROVED | APPROVED WITH CONDITIONS | REJECTED
Inspector: <row · effective model id · isolation label>  ·  Scope doc: <path | none — no-record rule applied>  ·  Refuted: N
Raw: <the raw paths the requests named | n/a — Claude lane>
Findings: N BLOCKER · N MAJOR · N MINOR

Bottom line: <the answer's bottom_line>

BLOCKERS   <severity · path:line · claim · scenario · CONFIRMED/PLAUSIBLE/UNVERIFIED>
MAJOR
MINOR
Questions: <location · what>
Hunted and held: <the answer's hunted_and_held>
Next: <by the verdict>
```

`Raw:` names, per outside call, the member of the request's same-day family the result names when
that member exists, else every existing member (so an earlier run's copy is never listed as this
run's when the result names this run's); `n/a` is for the Claude lane only, and an outside lane with no copy on disk says
`none:` and why (report-only, or readers filed none at the request's path). A stopped run's block
names the stop, its sentence, that no stamp was written when none was, and what follows.

## 10. Report-only

`report_only: true` selects, harvests, packs, builds requests (with no `raw_path`), records and
triages the answer, and computes what `write` would write (`write.json`: the findings it would
raise, the stamp, the station's lines, the mirror path) without writing any of it: no append, no
stamp, no mirror, no banner (at `record-answer` or anywhere), `receipt.json` empty, and the result says `wrote_nothing: true`.

## 11. Stops

A stop is `status: stopped` with one tag. The shared tags keep their station-loop meanings:

| Tag | When, in this core |
|---|---|
| `phase-not-built` | never: every phase of this core is built |
| `selection-none` | the build hunt found no doc |
| `selection-several` | a hunt found several and no `choose` settled them |
| `ledger-refused` | never: an untaggable scope-doc line is quoted under `ledger.refused` and the plan is still inspected (section 15, point 3) |
| `write-refused` | the build doc changed after `harvest`, or a rendered line would not read back, or the composed doc would change a line; nothing is written to the doc |
| `records-refused` | the records component refused (`events` at harvest, `identity`, `append`, `render` at write); its sentence carried |
| `build-doc-unreadable` | the one build doc selected cannot be read as UTF-8 text |
| `code-book-missing` | blueprint-v2's `SKILL.md` resolves by neither route |
| `model-changed` | the later `suggest` shows another model for the row than the ask displayed |
| `lane-down` | a lens call's result is not `ok`: nothing triaged, the ask re-asked |
| `no-effective-model` | a result carries no effective model, or the paper calls report more than one: nothing raised, no stamp |

## 12. The records

This core is the one front core that opens the records component (ruling E14-9): through the
resolver snippet and the CLI only (`station_core/records_client.py`, `records_link.py`), never
`records_core`, never a log file opened by hand. It confirms interface version 2 at `harvest`
(exit 3 with one plain line otherwise; `INSPECT_V2_TEST_NO_RECORDS=1` under `INSPECT_V2_TEST=1`
makes the real failure happen). Its calls: `component-identity`, `events` (the pinned head),
`identity`, `append` (one batch of `finding_raised`), `render`, `mirrors`. It raises and clears
nothing: no `disposition`, no `waived`, ever; the answer schema is closed, so neither can ride in.

## 13. The gate

The run ends by reading back and stopping: the executor prints the chat block and waits. No loop
skill is invoked from this station; a collapsed gate in the owner's invocation is the executor's to
act on, and the answer records by which words. The owner adjudicates the findings; the drafting
session amends the doc on his word; a re-inspection is a fresh run.

## 14. The seeded families

Facts each family proves, never outcomes (the outcomes are in an answer key no builder reads):

| Family | What it exercises | The facts `lane_observe.py` fills |
|---|---|---|
| I1 primary evidence | a packet directory holding a summary, a prior verdict, a repo file, or only the three files, held to `request`'s three-file rule | `refused_at_request`, `packet_files` |
| I2 the no-record rule | a traceability reader's answer against a doc with and without a scope doc | `question_locations`, `blocker_count`, `no_record_noted` |
| I3 records and the stamp | an outside reader's answer: a citation inside the doc, one past its end, a result with no effective model | `raised_locations`, `refuted_count`, `stamp_written`, `stamp_model`, `terminal_status` |
| I4 no v1 import | a planted v1 reference in a scratch copy of this core | the frame's `v1_findings_present` |

Two translation choices of `lane_observe.py`, never facts of a case: a seeded replay carries no
`hunted_and_held` and no `bottom_line`, so the translation supplies one neutral sentence for each;
the I3 cases' neutral input carries no owner word while their answers come from `gpt-astra`, so the
drive's input and answer carry an `owner_word` naming that row with a one-line quotation, as an
owner's answer at the ask would. The facts' `_via` names the supplied owner word as that choice.

## 15. Open points

1. **The ask comes before `check-input`.** v1 hunts, then asks. The owner's word must be data in
   this run's input (station-loop.md rule 5; lane contract section 12, "the input carries the
   row"), and the input is fixed at `check-input`, so the ask moves ahead of the hunt; a run whose
   hunt finds no build doc has asked one question for nothing. Recorded for the owner.
2. **`mirrors` does not list an inspect mirror.** The component's `mirrors` associates a build
   doc's slices with `docs/reviews/*-signoff-<feature>-<slice>.md` only, so
   `docs/reviews/<date>-inspect-<feature>.md` is written, `mirrors` is asked, and its answer is
   kept whole in the result (`mirror.answer`), with `recognised: false` recorded honestly beside it. The records component is frozen in this step
   (E14-2); making `mirrors` recognise an inspect mirror is the owner's call.
3. **An untaggable scope-doc line does not stop the run.** Quoted, never dropped or guessed, under
   `harvest.json`'s `ledger.refused`; v1 inspects a plan whatever its record's form, and the
   traceability lens reads the scope doc's bytes.
4. **A fleet recorded short completes, and says so.** `record-answer` refuses a `lanes` list that is
   not the lenses of the results, but it does not refuse results that cover fewer lenses than
   `request` built: the run completes, `lenses_not_run` names the missing lenses in the result and
   the chat block. v1 treats a failed lens as a lane that is down (kept here as `lane-down`); a lens
   whose result was never recorded is not a status readers reports. The seeded families' recorded
   answers (I2, I3) carry one reader's result each, so refusing a short fleet would refuse every
   seeded replay. Whether a short fleet should stop the run is the owner's call. A short fleet is
   never silent: `lenses_not_run` names the missing lenses in the result, the chat block and the
   verdict mirror (ruling R1 of round 2).
