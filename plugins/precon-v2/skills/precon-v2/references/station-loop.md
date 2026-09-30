# The station loop: the contract the four front cores share (E14 slice 1)

This file is identical, byte for byte, in `precon-v2`, `architect-v2`, `blueprint-v2` and
`inspect-v2` (`references/shared-files.txt` lists it; `scripts/tests/test_shared_equal.py` holds
it equal). It states what every front core does the same way. It says nothing a lane must
change: where a phase's content belongs to one station (what `harvest` collects for precon
against what it collects for architect), it names that station's own contract,
`references/<core>-contract.md`, written in the core's slice 2 lane, as the place.

Contents: 1 The cores and their loop · 2 The CLI and the exit codes · 3 The phases (3.8 the core's own commands) · 4 The input ·
5 The result · 6 Report-only · 7 The stop vocabulary · 8 The rules · 9 The hand-offs · 10 The
records component · 11 The shared code · 12 What this contract never does.

## 1. The cores and their loop

Four stations run before a slice is built: `precon-v2` (the idea stage: a scope doc),
`architect-v2` (the drawings: an architecture doc and its visual), `blueprint-v2` (the sliced
build doc) and `inspect-v2` (the plan check). Each is a portable core: a `SKILL.md` procedure,
this contract and its own, schemas and examples under `references/`, one phase driver
`scripts/<station>.py` over the shared library `scripts/station_core/`, adapters for Claude Code
and Codex, setups, and seeded cases.

Every run of every core walks the same loop:

```
check-input  ->  select  ->  harvest  ->  record-answer  ->  write  ->  report
```

`identity` and `skill-identity` answer at any time and belong to no run.

The executor is the model running the core's `SKILL.md`. It talks to the owner, judges, and hands
its judgment to the script once per run as the recorded answer. The script does everything that
is deterministic: it validates, finds, reads, checks, renders, writes and records. That split is
rule E14-4 (section 8).

## 2. The CLI and the exit codes

`scripts/<station>.py` (run through `uv run`, which supplies the one declared dependency,
`jsonschema==4.25.1`, from the script's PEP 723 block). One exception to the name: inspect-v2's
driver is `inspect_v2.py`, because a file named `inspect.py` in the scripts folder shadows the
standard library's `inspect` module, which `jsonschema` imports. stdout carries one JSON document and
nothing else; stderr carries diagnostics. Every response carries `interface_version` (1) and
`plugin_version` (from `.claude-plugin/plugin.json`).

| Exit | Meaning |
|---|---|
| 0 | the command did its work; an intermediate phase has more to do |
| 1 | anything else: a defect of the script, an unreadable run directory |
| 2 | usage: a missing or malformed argument, a file that is not there or not JSON, a phase command against the wrong phase, an unknown hunt or a malformed name |
| 3 | missing dependency: `jsonschema` did not import, or (inspect-v2 only) the records component is missing or speaks another interface version. One line on stderr, nothing on stdout |
| 4 | validation: a supplied file failed its schema (`check-input`, and the lane's own `record-answer` schema). Nothing is written and the run stays where it was |
| 5 | refused: the recorded answer on its content (rule E14-11, section 8), or an input, a path or a run artifact a core's own rule refuses (a file outside its home, a run artifact outside the run). Nothing is written and the run stays where it was, so a corrected answer or input can be offered |
| 10 | the run reached a terminal status, a completion or a stop alike |

`--help` and every argument check work without `jsonschema`. Test hooks are honored only when
`<PREFIX>_TEST=1` is set, `<PREFIX>` being the core's name upper-cased with `-` as `_`
(`PRECON_V2`, `ARCHITECT_V2`, `BLUEPRINT_V2`, `INSPECT_V2`): `<PREFIX>_TEST_NO_JSONSCHEMA=1`
behaves as if `jsonschema` were not importable, and `<PREFIX>_TEST_NO_RECORDS=1` as if no records
component were installed. Each makes the real failure happen.

## 3. The phases

Each phase names its input, its output, its exits and the stop tags it may end in. A phase
command against a run at the wrong phase is exit 2 with the command to run instead.

### 3.1 `check-input <input.json>`

- Input: one input document (section 4).
- Output: the run directory created, `input.json` and `checkpoint.json` written in it; stdout
  `{"next": "select", "run_id", "run_dir", "workspace", "staging", "report_only", ...}`.
- Exits: 0; 2 when the file is not there or not a JSON object, or the run directory already holds
  a run; 3 without `jsonschema`; 4 when the document fails the schema or a path rule, with the
  findings on stdout and nothing written.
- Stop tags: none; `check-input` never ends a run.

### 3.2 `select --run-dir D [--hunt NAME] [--name NAME]`

- Input: a checked run; `--hunt` names one of the core's hunts (its table lives in
  `scripts/<station>.py` and its lane contract states it; a core with one hunt needs no flag);
  `--name` fills the `{name}` slot of the hunt's globs (a slug or a topic, one path segment of
  lowercase letters, digits, `.`, `_` and `-`; absent, the slot reads `*`).
- Output: the hunt's result, one shape for every core (rule E14-10, `station_core/hunt.py`):
  `{"outcome": "none" | "one" | "several", "candidates": [...], "searched": [...]}`, written to
  `selection-<hunt>.json` in the run directory and printed. `searched` names every home looked
  in, whether it was given and what each glob found. The homes are tried in tiers: the lowest
  tier that holds any candidate decides, so a newer home beats an older flat name the way the v1
  stations rank them.
- Exits: 0 for every outcome (the outcome is data); 2 on an unknown hunt, a malformed name, or
  the wrong phase.
- Stop tags: none in the frame. What `none` and `several` lead to is each core's own rule, in its
  lane contract: `several` is always listed for the owner and never picked; `none` is reported,
  and the core's rule says whether the run stops (`selection-none`) or asks.

### 3.3 `harvest --run-dir D`

- Input: a run that has selected. Output: what the core reads before anything is asked: the
  selected documents, and for every core that receives a scope doc, the scope doc's ledger read
  by `station_core/ledger.py` (every line with its tag, its source text and a stable line id; a
  line the reader cannot tag is refused, quoted, never dropped or guessed). What else is
  harvested (repo facts, a prior architecture doc, a prior build doc) is the core's lane
  contract.
- Exits: 0; 2; 10 when the harvest itself stops the run (for example `ledger-refused`).
- Stop tags: `ledger-refused`, and the lane's own.
- In the frame this phase exits 10 with `phase-not-built` (section 7) until the lane fills it.

### 3.4 `record-answer --run-dir D --answer FILE`

- Input: the executor's one recorded answer for this run, a file. Its schema is the core's own
  answer schema under `references/`, which the lane writes; its shared checks are `station_core/answer.py`,
  one implementation for all four cores.
- Output: `answer.json` in the run directory, only when the answer is accepted.
- Exits: 0 accepted; 4 the answer fails its schema; 5 the answer is refused on its content by
  rule E14-11 (a question that re-asks a `decided` ledger line; an asserted line that traces to
  no ledger line, no repo path and no answered question of this run; a `parked` or `open` line
  passed forward as `decided` that does not name the row's id, or names it with no answered
  question of this run touching that row). On 4 and 5 nothing is written and the refusals are
  listed on stdout, each with the line or question it names.
- The row id (ruling A5(4)): every answer line that decides, settles, passes forward or moves a
  ledger row names that row by its id, in the line's `row` field (a core's answer schema holds it on
  exactly the lines its view hands the frame; a line whose trace is `ledger` names that trace's row,
  and `row` may repeat it, never differ from it). A line that names its row is judged by the id
  alone, never by its words: settled as `decided` only when an answered question of this run touches
  that row; a `decided` row named as `parked`, `open` or `deferred` is refused as a re-ask (any
  other tag is the core's own pass-forward vocabulary, which the frame does not judge). The words
  are compared only as a guard on the id-less path: a line asserted as `decided` whose words restate
  a `parked` or `open` row it does not name is refused, and the refusal says to name the row's id.
  An answered question of this run that touches that row does not substitute for the line's id.
  In that comparison an item label, bare (`R2 `) or marked (`AC1:`, `(R2)`, `[R2]`, `**R2:**`), is
  part of the words on both sides.
- Stop tags: none; a refusal leaves the run where it was.
- In the frame this phase exits 10 with `phase-not-built` until the lane fills it. The refusal
  logic already exists and is tested (`scripts/tests/test_answer.py`).

### 3.5 `write --run-dir D`

- Input: an accepted answer. Output: the core's documents, rendered through
  `station_core/templates.py` from the answer and the harvest (never typed by the executor), with
  a receipt in the run directory naming every write and the bytes' hash before and after. A
  write that would drop or change a protected line (a prior run-log block, a prior poured-concrete
  line, a ledger section of a build doc, a `Status:` line, a `Plan: inspected` line) is refused
  before anything is written.
- Exits: 0; 2; 10 when the write stops the run.
- Stop tags: `write-refused`, and the lane's own.
- In the frame this phase exits 10 with `phase-not-built` until the lane fills it.

### 3.6 `report --run-dir D`

- Input: a run that wrote (or a report-only run, section 6). Output: `result.json` in the run
  directory, validated against `references/result.schema.json` and the semantic checks of
  `scripts/validate-result.py` before it is written, and the core's chat block rendered from it.
- Exits: 10.
- Stop tags: every tag the run reached.
- In the frame this phase exits 10 with `phase-not-built` until the lane fills it.

### 3.7 `identity <workspace>` and `skill-identity`

- `identity`: the workspace as this station sees it, without the records component:
  `{"workspace": <real path>, "kind": "git" | "directory", "head": <commit or null>}`.
- `skill-identity`: `{"name", "version", "commit", "content_sha256"}` of the installed skill, the
  hash over every file under the skill root in path order (`__pycache__` and `.pyc` excluded).
- Exits: 0; 2 when the workspace is not a directory.

### 3.8 The core's own commands

A lane may add commands of its own to its driver, where its section of the E14 contract names
one (`state`, `render-visual`, `record-publish`, `packet`, `request`), through the `commands`
argument of `station_core/driver.py`'s `main`: each is a subcommand with the common options,
listed under "Commands of this core" in `--help`, answering with the envelope and the exit codes
of section 2, and never a shared name. What each does, its input, its output and its exits are
the lane contract's (`references/<core>-contract.md`); the shared contract only fixes the seam. A
core's own command never writes a document except through `write`'s receipt discipline, and
never opens the records component unless the core is `inspect-v2`.

## 4. The input

One validated input document per run, `references/input.schema.json`, closed at every level
(an unknown key is refused, never ignored), with valid and invalid examples under
`references/examples/input/`. The shared fields:

| Field | What it is |
|---|---|
| `input_version` | `1`; the bump path a closed schema needs |
| `run_id` | this run's own id, single-use, one path segment |
| `workspace` | absolute path of the directory the core reads and writes; a git work tree root when the core writes into a repository |
| `staging` | optional: absolute path of the named non-repository home (`~/Documents` in v1, passed resolved, never expanded by a script); precon and architect write there when no repository owns the idea |
| `run_dir` | absolute path of this run's directory, outside the workspace and outside the staging home |
| `report_only` | optional, default `false` (section 6) |
| `owner_word` | optional: `{"rows": [<readers row id>, ...], "words": "<the owner's words, verbatim>"}`, the one source of a reader request's `authorized` flag (section 8, rule 5) |
| `invocation` | `{"harness", "caller", "mode", "session_id"}`, filled by the adapter's `invocation.py`, never typed |
| `station` | the object the core's lane fills with its own fields; closed and empty in the frame |

Caller values arrive as data, argv items or files, and are never pasted into shell text. The path
rules the schema cannot state are enforced by `station_core/inputs.py` and reported the way a
schema finding is (`{"path", "message"}`): the workspace is an existing absolute directory; the
staging home, when given, is an existing absolute directory; the run directory is absolute and
inside neither of them.

## 5. The result

One result document per run, `references/result.schema.json`, with valid and invalid examples
under `references/examples/result/` and the validator `scripts/validate-result.py`. Every run
ends in a terminal status, every stop included:

| Field | What it is |
|---|---|
| `interface_version`, `plugin_version`, `station` | which core wrote it |
| `run_id`, `run_dir` | the run |
| `status` | `completed` or `stopped` |
| `stop_tag`, `reason` | a stop carries a tag from section 7 and a sentence; a completion carries a reason and no tag |
| `report_only`, `wrote_nothing` | section 6 |
| `writes` | every write of the run: `path`, `kind` (`run_artifact`, `document`, `records_log`), `sha256_before` and `sha256_after` |
| `selection` | the hunt results the run used, as `select` printed them |
| `invocation` | as the input carried it |
| `station_result` | the object the lane fills |

The semantic checks a schema cannot make (`validate-result.py`): S1 a `stopped` result carries a
tag and a reason, and a `completed` one carries no tag; S2 a report-only result lists no write
outside the run directory and says `wrote_nothing: true`; S3 `wrote_nothing` is true exactly when
no write lies outside the run directory; S4 a write under the run directory is a `run_artifact`
and a `run_artifact` lies under it.

## 6. Report-only

Every core takes `report_only`. In that mode the run writes nothing to the workspace, nothing to
the staging home and nothing to the records log; its own artifacts in the run directory are the
only writes, and its result says `wrote_nothing: true`. A report-only run still selects,
harvests and checks the answer, so what it would have written is reported, not written.

## 7. The stop vocabulary

A stop is `status: stopped` with one tag. The shared tags, which every core uses for these
situations and for nothing else:

| Tag | When |
|---|---|
| `phase-not-built` | the frame's placeholder: the phase exists on the CLI and its station's lane has not built it |
| `selection-none` | the core's rule makes an empty hunt a stop |
| `selection-several` | the hunt found several candidates; they are listed for the owner, never picked |
| `ledger-refused` | a harvested document (the scope doc, or an architecture doc's poured-concrete or deferred section) holds a line the reader cannot tag; the line is quoted |
| `write-refused` | the write would drop or change a protected line; nothing was written |
| `records-refused` | inspect-v2 only: the records component refused a call; its own sentence is carried |

Each lane adds its own tags in its contract and never reuses a shared tag for another meaning.
The result schema's `stop_tag` description publishes the full list a core can emit, and
`validate-examples.py` holds the list and the examples to each other.

## 8. The rules

1. **E14-4, the executor decides, the script records.** A script validates inputs, finds
   documents, reads the ledger, builds packets, talks to the records component, renders and
   parses the templates, validates results and writes the documents. It never judges an idea, an
   architecture, a plan or a finding. What the executor or an independent reader concluded is
   recorded with who concluded it: the executor's session (`invocation.session_id`), or the
   reader's call id and effective model.
2. **E14-11, the record passes forward.** A `decided` line of a scope doc reaches the architecture
   doc and the build doc by script, with its line id, and is never re-asked. A recorded answer
   lists the questions the executor put to the owner, each with the ledger line ids it touches;
   `record-answer` refuses, exit 5, a question that touches a `decided` line. A line the executor
   asserts carries its trace: a ledger line id, a repo path that exists in the workspace, or the
   id of a question answered in this run (and, where the core's lane contract allows them,
   `assumed` with its why, or the owner's words quoted); a line with no trace, or a trace that
   names nothing, is refused the same way. `parked` and `open` lines pass forward as `parked` and
   `open`; one asserted as `decided` is refused unless it names the row by its id and an answered
   question of this run touches it.
   A line that decides, settles, passes forward or moves a ledger row names the row by its id
   (`row`, or its `ledger` trace) and is judged by the id alone; a `decided` row is never named as
   `parked`, `open` or `deferred`. The text match is only the guard on the id-less path: a `decided`
   line whose words restate a `parked` or `open` row it does not name is refused with "name the
   row's id", whether or not an answered question of this run touched that row, an item label (bare
   or marked, `R2 ` or `AC1:`) being part of the words on both sides (section 3.4).
3. **Documents are rendered, never typed.** Every load-bearing form (the scope doc, the
   architecture doc, the build doc, the stamp and the station's own block lines) is rendered and
   parsed by `station_core/templates.py` from `references/templates/`, whose forms are v1's byte
   for byte (ruling E14-12). A form change is a stop, never a lane's edit.
4. **One living document.** A core that finds its own document continues it in place; it never
   forks a second one. Selection finds it (section 3.2); `several` is asked, never picked.
5. **The owner's word is data in this run's input.** A reader request carries `authorized: true`
   only on an outside row that `owner_word.rows` names, never on a row whose provider is
   `anthropic`, and never from anything remembered between runs (`station_core/readers_request.py`).
6. **No v1 station at run time.** A core never reads a v1 skill's files, never shells to one and
   never defers to one as law (ruling E14-7); `scripts/tests/test_no_v1_import.py` fails when it
   does. A code book, where a core needs one, is a v2 sibling resolved by `station_core/sibling.py`.
7. **The gate.** Every core ends by reading back and stopping. No core invokes another loop
   skill; a collapsed gate in the owner's invocation is the executor's to act on, and the core
   records that it was collapsed and by which words.

## 9. The hand-offs

What each core leaves for the next, and where the next core's `select` finds it. The forms are
the templates of section 8, rule 3.

| From | Leaves | Found by | With the hunt |
|---|---|---|---|
| `precon-v2` | the scope doc: `<workspace>/docs/scope/<YYYY-MM-DD>-<idea>.md`, or `<staging>/<idea>-scope.md` when no repository owns the idea | `architect-v2` and `blueprint-v2` | `scope`: `docs/scope/*.md` and the older flat `docs/*-scope.md` in the workspace (and `<staging>/*-scope.md` for architect-v2 and inspect-v2) |
| `architect-v2` | the architecture doc: `<workspace>/docs/architecture/<YYYY-MM-DD>-<slug>.md`, or `<staging>/<slug>-architecture.md`; its `Scope doc:` header line names the scope doc | `blueprint-v2` | `architecture`: `docs/architecture/*.md`, then the older flat `docs/*-architecture.md` |
| `blueprint-v2` | the build doc: `<workspace>/docs/plans/<YYYY-MM-DD>-<feature>.md`, extended in place when one exists | `inspect-v2` (and `build-v2`'s own reader) | `build`: `docs/plans/*-<name>.md` and `docs/plans/<name>.md` (one tier), then the older flat `docs/<name>-build-plan.md` |
| `blueprint-v2` | the scope doc it read, unchanged | `inspect-v2` | `scope`, by glob over every home, never by a guessed slug |
| `inspect-v2` | the `Plan: inspected` stamp and the station's own lines in the build doc, its findings in the records log, a verdict mirror under `docs/reviews/` | `build-v2`, `signoff-v2`, `recheck-v2` | their own readers, unchanged |

Each core's full hunt table (the globs, their tiers, the homes each needs) is in its
`scripts/<station>.py` and its lane contract.

## 10. The records component

Only `inspect-v2` opens the records component (ruling E14-9): it raises each surviving finding as
a `finding_raised` event and appends what the component renders. It reaches the component through
the resolver snippet and the CLI only (`station_core/records_client.py`, `records_link.py`),
confirms `interface_version` 2 through `component-identity`, and stops with exit 3 and a plain
message when the component is missing or speaks another version. `precon-v2`, `architect-v2` and
`blueprint-v2` write no event and never open the component: a scope doc, an architecture doc and
a fresh build doc carry no finding and no card move. The shared library ships the records helpers
in all four cores so the frame stays one copy; the three front cores never call them.

## 11. The shared code

`references/shared-files.txt` lists every file that is identical in the four cores, relative to
the plugin root, `{core}` standing for the core's own name. A lane that needs a shared file to
change asks the control room, which changes it in the frame and merges it into every lane.

| Module | Job |
|---|---|
| `station_core/driver.py` | the phase driver every `scripts/<station>.py` runs: the parser, the envelope, the run directory, `check-input`, `select`, `identity`, `skill-identity`, and the placeholder stop of the phases a lane has not built |
| `station_core/inputs.py`, `validate.py` | the input's path rules; schema loading, the `jsonschema` guard, the result's semantic checks |
| `station_core/hunt.py` | the one selection function (E14-10) |
| `station_core/ledger.py` | the scope doc's ledger reader |
| `station_core/answer.py` | `record-answer`'s shared refusals (E14-11) |
| `station_core/templates.py` | parse and render of the four forms and the station's line forms (E14-12) |
| `station_core/runlog.py` | the architecture doc's run log: the next run number, the strikethrough, the no-loss check |
| `station_core/sibling.py` | a v2 sibling plugin's root, route 3a then 3b; a v1 name refused |
| `station_core/readers_roster.py` | readers' roster, found the same way (argument, route 3a, route 3b), for every core |
| `station_core/readers_request.py` | a `readers` request built from the input and the documents |
| `station_core/records_client.py`, `records_link.py` | the records component, for inspect-v2 |

## 12. What this contract never does

It never names a v1 station's file as a place to read, never defers to another skill's text as
law, never states a lane's own decisions, and never publishes, launches a harness, calls a model
or touches the network from a script.
