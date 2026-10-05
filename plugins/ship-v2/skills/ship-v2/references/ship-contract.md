# Ship v2 core: behavioral contract

What this station does, what it reads, what it may write, what stops it, and the words it uses for a state. Written for
E15 slice 2 of the skills v2 rebuild, against the E15 lane contract (sections 6, 10 and 12, amendments A1 to A26) and
the control room's readings CR-21 to CR-27 in the slice 2 brief. Where this document and that contract differ, the
contract is the authority and this document is the defect. `references/back-loop.md` is the discipline the three back
cores share; this document is this core's own.

Contents: 1 Job · 2 What is kept and what moved · 3 The phases · 4 The input · 5 Reading the build doc · 6 The one
sanctioned write · 7 The stops and the pause · 8 The load-bearing form · 9 The result · 10 The records component ·
11 The harness seams · 12 Stops and exits · 13 The seeded families · 14 What this core never does · 15 Interface.

## 1. Job

One slice, all the way through the loop: build-v2, signoff-v2, the fixes, recheck-v2, at most one extra lap, then
the report, calling only the qualified v2 stations and proving it with a trace (ruling E15-7). The script never judges
code, a finding, a fix or a slice (ruling E15-4): it finds the doc, reads it twice, reads each station's identity
through the station's own CLI before the visit and writes the trace, reads each station's own result, decides the
loop's next step from the station's own words and the records, keeps the lap counter, holds the fixes to the slice's
footprint, passes a question through, records the owner's waiver or reopening, and renders the `SHIP:` block. The
fixing, the visiting and the talking are the executor's; the waivers are the owner's, in his words.

## 2. What is kept and what moved

Kept from v1 (ruling E15-1): compose by name (each station runs under its own `SKILL.md`; the schedule, the lap limit
and the stop conditions are this core's, nothing of a station's rulebook is restated here); the hook check and what
the goal condition means; the narrowed hunt and its pause; the lap counter (one initial pass, at most one extra lap,
a third only on the owner's words); the four stop conditions in v1's words and order; pause versus stop; the fixes by
the session's own hands inside the slice's footprint, never a spec edit; the one sanctioned record of the owner's
mid-run waiver or reopening; the `SHIP:` block; report and stop, the git gates untouched.

What moved: the deterministic half is a script; each station is reached as a v2 sibling, resolved by allowlist
identity and read through its own CLI before the visit, with a trace line before and after (CR-21); the station's
result is its own `result.json`, validated against its own result schema (a v1 station's report is refused); the lap
counter, the footprint check and the stops are the script's (CR-22, CR-23); the waiver or reopening is a records event
through `records.py append`, not a hand-written ledger line (ruling E15-9, CR-24); every line read from the doc is
read twice (CR-27); the summon and kickoff lines name the v2 stations (A2 Q5, CR-26); the owner is "the owner" in the
portable text.

## 3. The phases

`check-input`, then `select`, `hook`, `visit` (once per station visit, each with `--result`), `fix`, `lap`, `pause`,
`report`; `identity` and `skill-identity` at any time. A command against a run at another stage is exit 2 naming the
command to run instead. Every phase reads and writes only the run directory, except the records event of section 6.
Every run file this core reads or writes is checked first with `os.lstat`: a link, a pipe or a file outside the run
directory is refused, never followed.

### 3.1 `select --run-dir D [--doc PATH | --name NAME] [--slice NAME]`

The narrowed hunt (ruling E15-10, `station_core/hunt.py`, three outcomes, never a silent pick). A doc named in the
invocation, or the plan established in the session, is `--doc` (an existing `.md` inside the workspace, not under
`docs/records/` or `docs/reviews/`; anything else is refused, exit 5). Otherwise `--name` hunts the repo's tiers by
file name: `docs/plans/*-<name>.md` and `docs/plans/<name>.md`, then `docs/<name>-build-plan.md`. No vault, no other
repository, no home directory, no heuristic across candidates. Nothing named (`selection-unnamed`), nothing found
(`selection-none`), several found (`selection-several`, listed), no slice named (`slice-unnamed`) or a slice the doc
does not hold (`slice-unknown`) is a PAUSE: exit 0, `paused` true, `why`, the question for the owner, `next`
`select`, and nothing written (the run stays at `checked`). `--slice` takes the owner's answer when the input named
no slice. The doc is then read (section 5); a line the readings refuse ends the run (`doc-unreadable`). Writes
`ship.json`: the doc, its hash, the slice, its card, its footprint, the lap counter's start.

### 3.2 `hook --run-dir D --reading FILE`

The adapter's reading (`references/answer.schema.json`, kind `hook`), taken whole: refused (exit 5) when it is another
harness's, or when a harness other than Claude Code claims an armed hook. Recorded in `ship.json` with its label,
`armed` or `NOT armed (run unwrapped)`. The run proceeds identically either way.

### 3.3 The stages

The checkpoint's `phase` holds the run's stage; each command runs at the stages named here and nowhere else:

| Stage | Reached by | Next |
|---|---|---|
| `checked` | `check-input`; a `select` pause | `select` |
| `selected` | `select` | `hook` |
| `hooked` | `hook` | `visit --station build-v2` |
| `visiting` | `visit --station` | `visit --result` |
| `built` | build-v2 COMPLETE | `visit --station signoff-v2` |
| `fixing` | signoff-v2 with a BLOCKER or MAJOR charged to the slice (or MINORs the owner ordered); `lap` | `fix` |
| `fixed` | `fix` | `visit --station recheck-v2` |
| `lap-needed` | recheck-v2 not ALL CLEAR, a lap left | `lap` |
| `exhausted` | recheck-v2 not ALL CLEAR, no lap left | `report` (stop condition 1); `lap` is refused |
| `clean` | ALL CLEAR | `report` |
| `ending` | any other stop, decided where it happens | `report` |
| `paused` | `pause --question` | `pause --answer` |
| `done` | `report` | nothing |

A stop is decided where it happens and moves the run to `ending`, where only `report` runs: no later visit, fix, lap
or pause can reach the trace or the records (CR-23).

### 3.4 `visit --run-dir D --station NAME` and `visit --run-dir D --result`

CR-21, rulings E15-6 and E15-7. **Opening.** The station is the one the loop's order names (build-v2 at `hooked`,
signoff-v2 at `built`, recheck-v2 at `fixed`); any other name is exit 2 (compose by name, never skip or reorder). It is
resolved by allowlist identity (`scripts/ship_core/stations.py`, the same design vertical-v2 uses for readers, A5
(1)): the checkout sibling `<plugin root>/../<name>` (route 3a) or an installed `<plugin root>/../../<name>/<version>`
(route 3b), each a real directory (never a link) under its exact name, compared by device and inode; every candidate is
held to the allowlist before anything of it is opened; every file opened or run from the root taken (its manifest, its
`skills/<name>/scripts/<script>`, its result schema) must resolve inside it by identity; a manifest naming another
plugin is refused without running anything (`v1-name` for a v1 station's name, else `name-mismatch`); and the
name-based screen stays as a second line (a root whose path, in any letter case, sits under a v1 plugin folder, or
holds a v1 station's name over a dotted version, is `v1-root`). Then the station's identity is read through its own CLI,
`scripts/<script> skill-identity`, run isolated (`-I -B`, a fixed environment, a timeout): name, version, commit,
content hash, interface version, and the root's real path. It is held to the trace's refusal rule
(`back_core/trace.py`: a v1 name, a name not the expected one, a root under a v1 plugin folder, an interface version
not in `stations.KNOWN`, which is 1 for each station), and to the plugin version (the version the CLI reports must be
the root's own manifest's, `no-identity` otherwise). A station that fails any of it is refused: a `refused` trace line
(its rules and the reason) and the stop `station-refused`, nothing of it run but its `skill-identity`. A station that
holds gets the opening trace line (`visit`, status `visiting`, the identity, the route, the visit's run directory
`visits/<seq>-<name>` under this run's directory, which the station's own `check-input` creates), and only then is the
visit handed over: the station's `SKILL.md`, its summon line, the run id (`<run id>-<seq>-<name>`) and run directory,
and the caller fields.

**Closing.** `visit --result` reads `<visit run dir>/result.json`, the station's own result, written by the station
run by its own `SKILL.md`. No result yet is exit 2. Before it is read, the station is resolved and identified again: a
station that changed since the opening is refused (a `refused` line, `station-refused`). The result is refused, exit
5, nothing written, the run still `visiting`, when: the visit's run directory or the file is a link, not a regular
file or outside this run's directory; it is not JSON; it does not validate against the station's own result schema (a
v1 station leaves no such document); it names another run id or run directory, another slice, doc or workspace; its
plugin version is not the version visited; or, on a report-only run, it is not a report-only result that wrote
nothing (recheck-v2, which has no report-only mode, must have written only run artifacts). A result that holds is
recorded (`ship.json`'s `visits`) and closed on the trace (`visit`, the station's own status). Then the next step, from
the station's own words and the records:

| Station | Its result | Next |
|---|---|---|
| build-v2 | `completed` (COMPLETE) | `built` |
| build-v2 | anything else (`checks_not_passed`, `not_complete`: PARTIAL; `answer_refused`, `stopped`, or `not_complete` claimed `stopped`: STOPPED) | stop condition 3, `build-not-complete` |
| signoff-v2 | a status other than `completed`, an answer it refused, or a refusal reason | `signoff-stopped`, its status carried |
| signoff-v2 | completed, and the records hold a BLOCKER or MAJOR open for the slice (or a fix-introduced defect, or a MINOR the owner ordered) | `fixing`, lap 1, the named findings printed |
| signoff-v2 | completed, nothing to fix | `clean` (ALL CLEAR, recheck not run) |
| recheck-v2 | a status other than `completed` or `nothing_open` | `recheck-stopped`, its status carried |
| recheck-v2 | `result` `all_clear` (or `nothing_open`) and no BLOCKER or MAJOR open for the slice in the records | `clean` |
| recheck-v2 | otherwise, with a lap left | `lap-needed` |
| recheck-v2 | otherwise, with none left | `exhausted` |

On a report-only run, where signoff-v2 wrote nothing, the findings to fix are its result's own raised findings.

### 3.5 `fix --run-dir D --fixes FILE`

The lap's fixes (kind `fixes`): per fix the finding it answers (one of the lap's named findings), every path it
touched or wants to touch, one line on what changed; `spec_change` for a fix that needs the spec changed. In order: (1)
refused, exit 5: another lap's file, an unnamed finding, a finding twice, a path that is not workspace-relative; (2) the
doc read again, twice (a doc that no longer reads cleanly, or no longer holds the slice, ends the run
`doc-unreadable`); (3) **stop 2** (`spec-change`): any `spec_change` entry, or the build doc declared or moved since
the pin; (4) **stop 4** (`outside-footprint`): any path declared or moved since the pin outside the slice's footprint;
(5) refused, exit 5: a path moved since the pin, inside the footprint, that no fix names; (6) recorded in `fixes.json`,
then `fixed` (or, for the MINORs the owner ordered after a clean signoff, `clean`: they never gate and never trigger a
recheck).

**The pin** (`scripts/ship_core/pin.py`): taken when a lap's fixing begins (at signoff-v2's result, and at each `lap`),
HEAD and the identity of every changed or untracked path (type, mode and content with lstat semantics:
`file:<mode>:<sha256>`, `link:<sha256 of the target>`, `dir`, `missing`), `docs/records/` left out. A path moved when
its identity differs from the pin's (one committed as it was is no move), or, clean at the pin, it is dirty now or a
commit since the pin's HEAD changes it. Git runs read-only (`gitio.py`: `rev-parse`, `status`, `diff`).

### 3.6 `lap --run-dir D`

CR-22. At `lap-needed`: lap N+1 opens (`laps.json`), the findings the records hold open for the slice are named again,
the pin is taken again, and the run goes back to `fixing`. A lap beyond the allowed count is refused (exit 5, nothing
written, the run where it was); at `exhausted` every `lap` is refused. The allowed count is 2 (the initial pass and the
extra lap) plus `station.extra_laps.count`, the laps the owner's words in the input order; a lap they open records his
`words` verbatim in `laps.json` and the result (`station_result.laps`). **Not on the trace:** the trace's line shape
(`references/trace.schema.json`, a frozen back-frame file, ruling E15-3) is closed and has no field for words, so
CR-22's "recorded verbatim on the trace" is read as recorded in the run's own `laps.json` and result (the slice 2
report's numbered question). The counter never resets.

### 3.7 `pause --run-dir D --question FILE` and `pause --run-dir D --answer FILE`

CR-23 and CR-24. **The question** (kind `question`): a station's question to the owner (`source` `station`, the station
that asked) or ship-v2's own waive-or-hold question about a MAJOR only the owner can resolve (`source` `ship`), its text
verbatim. Allowed at every stage of a live run after `select`. Recorded in `pauses.json`; the run waits at `paused`;
the question is printed back verbatim with `next` `pause --answer`. Nothing is written outside the run directory and
no trace line is written: a pause is no visit. While it waits every other command is refused (exit 2): `report` does not
run at `paused`, so a pause is never turned into a stop, and the script never answers it.

**The answer** (kind `answer`): the owner's words verbatim and their effect: `resume` (the words go back to whoever
asked; nothing is written) or `waive` or `reopen` with a finding's id (section 6). Refused (exit 5, nothing written, the
run still paused): an answer to another pause, blank words, a grant on a finding the records do not hold, or at a status
the grant does not admit (a waiver takes `open` or `fixed`, a reopening `fixed` or `waived`). A refusal the records
component returns ends the run (`records-refused`, its sentence carried). The run resumes at the stage it paused at; a
grant at `fixing` names the lap's findings again from the records; a reopening after ALL CLEAR that leaves a BLOCKER or
MAJOR open for the slice sends the run to the next lap, or, with none left, to `exhausted`: the record over the
recollection.

### 3.8 `report --run-dir D --bottom-line TEXT [--skill-note TEXT]`

At `clean`, `exhausted` or `ending` only. Reads the slice's card from the doc as it stands (read twice; a doc that no
longer reads is reported as `unread` with why), the findings the records hold open (`Remains`: this slice's, with
`/recheck-v2 <slice> <doc>`; other slices', charged elsewhere and never this run's to fix), the fixes recorded
(`Fixed`) and the trace; renders the `SHIP:` block into `chat.md`; writes `result.json`, validated against
`references/result.schema.json` and the semantic checks S1 to S4 (a result that fails is a defect, exit 1); ends the run
(exit 10).

### 3.9 `identity <workspace>` and `skill-identity`

The frame's: the workspace as this station sees it, and this skill's name, version, commit and content hash.

## 4. The input

`references/input.schema.json`, closed. The shared fields (back-loop section 3) and `station`, each optional: `slice`
(the slice the invocation names), `minor_fixes` (`words`: the owner's words ordering the slice's MINORs fixed),
`extra_laps` (`count` and `words`: the laps beyond the extra lap the owner ordered, his words verbatim). The fixes, the
questions, the answers and the hook reading arrive later, in their own files (`references/answer.schema.json`).

## 5. Reading the build doc

CR-27, as slice 1b ended it (A22, A25, A26; `scripts/ship_core/doc.py`). Every line this core reads from a build doc
to decide anything (the slices, the slice's card, its footprint) is read twice. First by vertical-v2's plain-structure
line rules: `scripts/ship_core/fences.py` is vertical-v2's `vertical_core/fences.py` byte for byte (A8's strict fences,
A9's raw HTML lines, A10 and A11's exact labels, A12's plain structure, A16's character list, A18's stray `Status:`
line and leading marks); any problem it names stops the run (when the first is a stray `Status:` line, an earlier line
the second reading names is named instead, as vertical-v2's `spec.read` does). Then by vertical-v2's second reading
(A13): `commonmark.py`, `readings.py`, `spec.py` and `notes.py` are vertical-v2's byte for byte, over the vendored
`markdown-it-py` 3.0.0 and `mdurl` 0.1.2 under `scripts/vendor/` (vertical-v2's tree byte for byte, with
`VENDOR.json`), compared with the line rules by `readings.compare`: the slices, each slice's card, the recorded base,
the withheld sections, and the second reading's four refusals. `scripts/tests/test_doc_reading.py` holds the five files
and the vendored tree equal to vertical-v2's (skipped, never passed, in the installed shape) and
`scripts/tests/test_vendor.py` holds the tree to its manifest in every shape. None of these is a back-frame file
(`references/back-files.txt` is unchanged). `templates.parse` decides nothing here. The first line where the two
readings differ, or a refusal, stops the run `doc-unreadable`, naming the line, before any visit or write.

**THE FOOTPRINT RULE** (A26's one rule for the one label this core reads; the code's statement is `doc.py`'s). Inside
a slice's section, a line that, after any prefix and any leading listed mark, folds to `footprint`, spaces or tabs,
then a colon is read only in its plain form: at column 0 with exactly `Footprint:`, its value on the same line; any
other such line stops, named; an empty value stops ("write the slice's paths on the label's own line"); a second
`Footprint:` in one slice stops. In the second reading, every rendered heading or paragraph line in a slice's section
that reads as a `Footprint:` label candidate must be that slice's plain `Footprint:` line on the same source line: a
bold or code-span label, a `### Footprint:` heading, a label in a paragraph whose rendered lines cannot all be mapped
to source lines, or a rendered label line running over more than one source line all stop. A `Footprint:` paragraph may
go on with any line: a value on a later line is never read, so the footprint is read narrower, never wider, than a
person sees it, and a narrower footprint only stops more fixes.

**The footprint's paths.** The value is split on commas outside code spans; an entry holding code spans names their
contents, any other entry its trimmed text. Containment is build-v2's rule (build-contract section 6): equal to an
entry, under one as a directory, or under an entry that ends in `/`; only literal leading `./` segments removed; a
shared prefix of a file name is no relationship. A slice with no `Footprint:` line names no path.

**Measured** on the 25 real build docs the control room snapshotted (the evidence corpus, never copied here; the slice
2 report's corpus table): the readings stop the same six docs handoff-v2's do, at the same lines, and the footprint rule
adds none.

## 6. The one sanctioned write

Ruling E15-9 and CR-24, exhaustively: ship-v2 writes the `waived` and `reopened` events the owner gives mid-run, each
with his words, through one `records.py append` per grant (`scripts/ship_core/record.py`); and its own run directory and
trace. Nothing else, ever: no line of the build doc, no `Status:` line, no card event, no finding, no disposition. The
stations it visits write their own records. A grant's event: `waived` (the finding's severity, `verified_source` the
workspace identity the component computes now, `join_basis` null) or `reopened` (`join_basis` null), `words` verbatim,
`grant_date` the run's date, `actor` this station, this run's id and the harness, appended against the head `verify`
reads. A report-only run plans the event in `events.json` and appends nothing.

### 6.2 What the records hold after a grant (CR-25, measured; the owner's question)

Slice 1b found that a `waived` event with no card move leaves vertical-v2's gate stalling a waived slice and passing a
reopened one (C1B1-2), and the owner ruled the card move for handoff-v2 (A23 (2)). E15-9 still says ship-v2 writes only
the grant events, and this core follows it as written. Measured (`scripts/tests/cr25lib.py`, `test_cr25.py`): after a
mid-run waiver of a slice's only open MAJOR, the run ends ALL CLEAR (or waits at a later pause, or ends at stop 3) with
the card at `signed off with conditions` in the records and on the `Status:` line, while v1's rule gives `signed off`,
and vertical-v2's gate stalls the slice (`gate-short`); after a mid-run reopening of a fixed MAJOR, a run that ends at
stop 2 or stop 4, or waits at a pause, leaves the card at `signed off` while v1's rule gives `signed off with
conditions`, and vertical-v2's gate passes the reopened slice. A run that goes on to another recheck lets recheck-v2
move the card, and the card then agrees. Whether ship-v2 should move the card with the grant (as A23 (2) did for
handoff-v2) is the owner's ruling; this core does not change E15-9 on its own.

## 7. The stops and the pause

In v1's words and order. **Pause:** a station puts a question to the owner (a stop-and-ask, an owner-only ruling, a
waiver decision); ship-v2 passes the question through verbatim and waits; his answer resumes the run where it paused; a
pause never emits the SHIP block. **Stop:** one of the four enumerated conditions: (1) the extra lap is exhausted
without ALL CLEAR (`extra-lap-exhausted`), (2) a fix would change the spec (`spec-change`), (3) build-v2 honestly stops
mid-slice (`build-not-complete`), (4) work wants to touch files outside the slice scope (`outside-footprint`). Each is
stop and report; the run ends and what happens next is the owner's call. Besides the four (CR-23): a signoff-v2 or
recheck-v2 stop or refusal ends the run with its status (`signoff-stopped`, `recheck-stopped`); a station that is not
the expected v2 sibling ends it before any visit (`station-refused`); a doc that cannot be read cleanly
(`doc-unreadable`); the records refusing the owner's grant (`records-refused`). v1's form has a slot for the four
conditions only; such an end reads `STOPPED (<station or tag>: <tag>)` (the slice 2 report's numbered question).

## 8. The load-bearing form

Ruling E15-11. v1's `SHIP:` block, rendered and parsed by one module, `scripts/ship_core/forms.py`, with a round trip
(`scripts/tests/test_forms.py`): `SHIP: <slice> <dash> <doc path>`; `Hook: armed | NOT armed (run unwrapped)`;
`Result: ALL CLEAR | STOPPED (condition N: <which>)`; the five fields `Build`, `Signoff`, `Recheck`, `Card`, `Laps`
with v1's double-spaced middle dot; a blank line; `Bottom line:`; and, only when any, a blank line, one `Fixed:` line
per fixed finding (`<finding> · <file:line> · <one line>`), one `Remains:` line per open finding (`<finding> ·
<severity> · <what is needed>`) and `SKILL NOTE:`. `Build` is build-v2's status in v1's words (`completed` COMPLETE;
`checks_not_passed` and `not_complete` PARTIAL; `answer_refused`, `stopped` and a `not_complete` that claimed
`stopped` STOPPED); `Signoff` is signoff-v2's verdict as it wrote it, or its status when it stopped, or `not reached`;
`Recheck` is recheck-v2's `result` in capitals (`ALL CLEAR`, `PARTIAL`, `NOT CLEAR`), `nothing open`, its status when it
stopped, `not run` after a clean signoff, or `not reached`; `Card` the slice's `Status:` line as the doc holds it at
`report`; `Laps` the fix-and-recheck laps whose recheck closed.

**The em-dash exception.** `<dash>` is U+2014, v1's byte, kept (E15-11): standing rule 10's one named exception. It is
one constant, `forms.D`, written in code as an escape; no file of this core types the character
(`scripts/tests/test_forms.py`, `NoTypedDash`), and this document names it rather than typing it.

**The station names** (A2 Q5, CR-26): every line ship-v2 renders that names a station names the v2 station
(`/build-v2`, `/signoff-v2`, `/recheck-v2`, `/goal /ship-v2`); `forms.summon` refuses any other name.

## 9. The result

`references/result.schema.json`, closed, with the E14 semantic checks S1 to S4 (`scripts/validate-result.py`). Every
run that reaches `report` ends in a terminal status, every stop included: `completed` (ALL CLEAR) or `stopped` with one
tag. `writes` lists ship-v2's own writes: its run artifacts (`ship.json`, `chat.md`, `laps.json`, `fixes.json`,
`pauses.json`, `events.json`, `records-events.json`, `trace.jsonl`; `checkpoint.json` and `result.json` themselves
aside) and the records log a grant reached (`records_log`, its hash before and after). `trace` names `trace.jsonl`, its
lines, the visits closed and the stations refused. `station_result` carries the doc, the slice, the hook, the result
line and condition, the five fields, the laps (taken, allowed, the owner's words and each lap opened), the visits, the
fixed and remaining findings, the pauses, the events and `chat`.

## 10. The records component

Reached through the resolver snippet and the CLI only (`station_core/records_client.py`, `records_link.py`), confirmed
at `interface_version` 2; exit 3 when missing or at another version. Read: `state` (the open set for the named findings
and the ALL CLEAR test, the `Remains` lines), `identity` (a waiver's source), `verify` (the head an append expects).
Written: one `append` per grant (section 6). Never a levelling pass, never a log file opened.

## 11. The harness seams

Ruling E15-12. **The Stop-hook check**: on Claude Code, `adapters/claude-code/hook.py` reads this session's own
transcript (found as `invocation.py` finds it, ruling E9-28) for the Stop hook's confirmation and prints the reading
(`armed`, with the record as `evidence`, or not armed): `helper-derived`, a reading of a harness record, never a fact
the harness enforces. On Codex, `adapters/codex/hook.py` prints `Hook: NOT armed`, labelled honestly: Codex has no Stop
hook this core can read. **The invocation facts**: each adapter's `invocation.py` (the back frame's). No manual-only
control (owner pick P5): ship-v2 keeps its phrases and commands.

## 12. Stops and exits

The exits are the back loop's: 0, 1, 2, 3, 4, 5, 10 (back-loop section 2). A stop is `status: stopped` with one tag:

| Tag | Phase | Means |
|---|---|---|
| `station-refused` | visit | a station that is not the expected v2 sibling, refused before the visit or at its result, a `refused` trace line (shared tag) |
| `records-refused` | pause | the records component refused the owner's grant, its sentence carried (shared tag) |
| `doc-unreadable` | select, fix | a doc line the two readings refuse or take differently (CR-27), named |
| `build-not-complete` | visit | stop condition 3: build-v2 PARTIAL or STOPPED |
| `signoff-stopped` | visit | signoff-v2's own stop or refusal, its status carried |
| `recheck-stopped` | visit | recheck-v2's own stop, its status carried |
| `spec-change` | fix | stop condition 2: a fix needs the spec changed, or touches the build doc |
| `outside-footprint` | fix | stop condition 4: a path outside the slice's footprint |
| `extra-lap-exhausted` | report | stop condition 1: the extra lap spent without ALL CLEAR |

`selection-none` and `selection-several` (the shared tags) are pauses here, never stops (v1's step 1), so this core
uses them as a pause's `why`, never as a stop tag. `phase-not-built` is the frame's placeholder; this core uses none.

## 13. The seeded families

`evals/seeded-cases/`: S1 v2 only, S2 the lap counter, S3 the stops, S4 pause and waiver, and T1 no v1 import (lane
contract section 12), each with a case where nothing is planted; built by script, observed by `lane_observe.py`
through the real CLI on a copy of this plugin beside stand-in stations (the real stations' manifests and result schemas,
and a script that answers `skill-identity` and nothing else) or a planted v1-shaped one; the outcomes live in an answer
key outside this repository.

## 14. What this core never does

Run a station's phases (the one station command it runs is `skill-identity`); answer a question meant for the owner;
turn a pause into a stop; take a third lap without the owner's words; write into the build doc; write a card event, a
finding or a disposition; run a git command that changes a branch, an index or a worktree; push, open a pull request or
merge (`scripts/tests/test_static.py`); launch a harness or summon a reader; read a v1 skill's files.

## 15. Interface

Commands: `check-input <input.json>`, `select`, `hook`, `visit`, `fix`, `lap`, `pause`, `report` (each with `--run-dir
D`), `identity <workspace>`, `skill-identity`; `--help` on each, without `jsonschema`. Runtime: `/usr/bin/python3` 3.9
syntax, standard library plus `jsonschema==4.25.1` through `uv run` (PEP 723) and the vendored CommonMark reader
(section 5); git 2.50.1. Run-directory artifacts: `input.json`, `checkpoint.json`, `ship.json`, `trace.jsonl`,
`visits/<seq>-<station>/` (each the station's own run), `laps.json`, `fixes.json`, `pauses.json`, `events.json`,
`records-events.json` (an append's input), `chat.md`, `result.json`.
