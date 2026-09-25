# E14 seeded cases

The seeded cases that grade the four front cores against the claims of the plan's done-when for
E14: decisions pass forward without invention or re-interview, document selection handles
ambiguity, inspect receives the permitted primary evidence, no implicit import of v1, and the
visual's two actions. Written in slice 1 by the frame's builder (lane contract section 4, pick
P4); the outcome of each case lives in an answer key outside this folder and outside every lane
builder's reach. This folder carries the cases, the vocabulary, and nothing else.

This README, `RUNNING.md`, `observe.py` and `_lib/caselib.py` are identical in the four cores
(`references/shared-files.txt`); each core holds the family folders that are its own.

## The families

| Family | Core | Cases |
|---|---|---|
| P1-ledger-traceability | precon-v2 | 4 |
| P2-one-living-doc | precon-v2 | 4 |
| P3-the-exit-test | precon-v2 | 4 |
| A1-no-re-interview | architect-v2 | 4 |
| A2-candidates-and-the-razor | architect-v2 | 4, lane |
| A3-the-living-doc | architect-v2 | 4 |
| A4-two-actions | architect-v2 | 3, lane |
| L1-traceability | blueprint-v2 | 4 (one lane) |
| L2-the-forms | blueprint-v2 | 4 (one lane) |
| L3-document-selection | blueprint-v2 | 4 |
| I1-primary-evidence | inspect-v2 | 4, lane |
| I2-the-no-record-rule | inspect-v2 | 3, lane (their selection half runs now) |
| I3-records-and-the-stamp | inspect-v2 | 3, lane |
| I4-no-v1-import | inspect-v2 | 4 |

Every family holds one case with nothing planted (`<family>-01-clean`), so a core that finds
trouble everywhere fails too. A case marked `lane` in its `CASES.md` exercises behavior a slice 2
lane builds (the razor, the packet, the stamp, the visual): it is built now and its `drive.json`
names the facts the lane will produce; the frame observes only its frame facts, where it has any.

## Building the cases

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 <family>/build.py --out <dir>
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 <family>/build.py --list
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 <family>/build.py --out <dir> --case <id> --json
```

Standard library only, `/usr/bin/python3` 3.9.6 and git 2.50.1, no network. Git runs only inside
the throwaway repositories the library creates under `--out`, with a fixed author, committer and
date, so two builds of one case produce the same commit and the same tree; `tree_sha256` in each
`manifest.json` normalizes the absolute output directory to `<OUT>`.

Each built case directory holds:

```
workspace/        the directory the core reads (a git work tree)
staging/          the staging home (empty unless the case says otherwise)
run/              an empty run directory
input.json        the neutral input (below)
drive.json        the steps observe.py runs; never an outcome
answer.json       a copy of answers/<case id>.json, when the family ships one
manifest.json     case, family, core, HEAD, tree_sha256, notes
(case files)      a proposed document, a run block, a packet directory, when the case names one
```

## The neutral input

`input.json` is not a core's input schema; `observe.py` translates it.

| Field | Meaning |
|---|---|
| `seeded_input` | the version of this shape, `1` |
| `case`, `core` | the case id and the core it belongs to |
| `workspace`, `staging`, `run_dir` | absolute paths under the output directory |
| `report_only` | false in every E14 case |
| `answer` | `answer.json` or null |
| `owner_word` | the owner's word in the run (P3 cases), as the core's input carries it |
| `station_publish` | A4-02 only: the executor's `publish: false` |

## The recorded answers

An **executor** answer (`role: "executor"`): `seeded_answer`, `case`, `session_id`, `questions`
(each `id`, `text`, `touches` (ledger line ids), `answer`), `lines` (each `text`, `tag`, and a
`trace` of `kind` and `ref`, or no trace), and, where the family needs them, `criteria`,
`candidates`, `components`, `walkthrough`, `exit_ramp`, `pick`, `rejected`, `publish`,
`publish_url`. A **reader** answer (`role: "reader"`): `row`, `call_id`, `effective_model`,
`findings` (each `severity`, `location`, `claim`, `scenario`, `confidence`). Some answers are
deliberately ill-formed; nothing in an answer or a `CASES.md` states an outcome.

## The neutral vocabulary

| Assertion | What it names |
|---|---|
| `selection_outcome` | `none`, `one` or `several`, as the run's `select` reports it |
| `selection_candidates` | the candidates' paths relative to the case directory, sorted |
| `ledger_refused` | true when the ledger reader refuses the scope doc |
| `ledger_refused_lines` | the line numbers it refuses |
| `ledger_tags` | per tag, how many lines the reader emits |
| `answer_refused` | true when the recorded answer is refused on its content |
| `refusal_rules` | the rule names of the refusals, sorted, unique |
| `refusal_reason` | a lane's short reason for a refusal the frame does not make: the lane's own rule name, several sorted and joined by `, `; null when nothing was refused |
| `answer_written` | true when the run records the answer in its run directory |
| `form_holds` | true when the document conforms to its template's labels and headings |
| `round_trip_identical` | true when parse then render gives the document's bytes back |
| `next_run` | the run number the next architecture run takes |
| `losses_count` | how many prior run-log blocks or poured-concrete lines a proposed document loses |
| `runlog_refused` | true when the run-log write is refused |
| `authorized_rows` | the rows whose built readers request carries `authorized: true`, sorted |
| `request_documents` | the documents' basenames the built requests carry |
| `request_profiles` | the profiles the built requests carry |
| `v1_findings_present` | true when the no-v1-import scan finds anything in the scanned copy |
| `writes_none` | true when the workspace and the staging home are unchanged by the run |
| `refused_at_request`, `packet_files` | inspect's packet: refused at `request`; the files it holds |
| `question_locations`, `blocker_count`, `no_record_noted` | inspect's no-record rule |
| `raised_locations`, `refuted_count`, `stamp_written`, `stamp_model`, `terminal_status` | inspect's records and stamp |
| `visual_rendered`, `published`, `artifact_line_unchanged` | architect's two actions |
| `extended_in_place`, `protected_lines_identical`, `importer_reads` | blueprint's living doc |

A list assertion is an exact list. A name the run has no fact for is omitted, never guessed. A location
(`question_locations`, `raised_locations`) is `<file>:<line>` as the core writes it: the workspace-relative path
of the document it names (`docs/plans/<date>-<topic>.md:10`), never a packet file name; a document outside the
workspace (inspect-v2's code book, a staging scope doc) is named by the path the core resolves it at, as the core
writes it into the log.

## Rules these cases were written under

- Synthetic content only: a made-up bench-rig turn counter. Nothing personal, legal, financial or
  key-shaped, and no text copied from another repository.
- No network, no MCP tool, no model call, no harness launch, in the generators or in a case.
- Tests and grading runs build into a temporary directory and clean up; no `__pycache__` is left.
- Neither a `CASES.md` nor an answer file states an outcome. The outcomes live in the answer key.
