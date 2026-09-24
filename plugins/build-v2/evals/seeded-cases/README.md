# E13 seeded cases

The seeded cases that grade the portable build core (`build-v2`) and the portable signoff core
(`signoff-v2`) against the five claims of the plan's done-when: scope adherence, honest failure
handling, correct review scope, evidence-backed initial findings, and independence.

Written in slice 0 by an agent that builds neither core (lane contract section 4, pick P4). The
outcome of each case lives in an answer key outside this folder and outside every builder's
reach. This folder carries the cases, the vocabulary, and nothing else.

## What is here

```
_lib/caselib.py        the generator library: git-deterministic workspaces, inputs, manifests
_lib/project.py        `signpost`, the synthetic project every case workspace is built from
B1-scope-adherence/    build core, 4 cases
B2-honest-failure/     build core, 5 cases
S1-review-scope/       signoff core, 5 cases
S2-evidence/           signoff core, 4 cases
S3-independence/       signoff core, 4 cases
```

Each family folder holds `build.py`, `CASES.md`, and `answers/<case id>.json`.

## Building the cases

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 <family>/build.py --out <dir>
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 <family>/build.py --list
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 <family>/build.py --out <dir> --case <id> --json
```

`--out` is created; an existing case directory under it is removed and rebuilt. Standard library
only, `/usr/bin/python3` 3.9.6 and git 2.50.1, no network. Git runs only inside the throwaway
repositories the library creates under `--out`, with `GIT_CONFIG_NOSYSTEM=1`,
`GIT_CONFIG_GLOBAL=/dev/null`, a fixed author and committer, and a fixed date per commit, so two
builds of one case produce the same commit hashes and the same file tree. The only bytes that
differ between two output directories are the absolute paths inside `input.json`; `tree_sha256`
in each `manifest.json` normalizes them to the literal `<OUT>` before hashing.

Each built case directory holds:

```
workspace/        the git work tree under review
run/              an empty scratch directory for the run
input.json        the run input (see below)
answer.json       a copy of answers/<case id>.json
manifest.json     case, family, HEAD, tree_sha256, notes
```

## The case ids

| Family | Case ids |
|---|---|
| B1-scope-adherence | `B1-01-clean`, `B1-02-untracked-outside`, `B1-03-committed-outside`, `B1-04-changed-outside` |
| B2-honest-failure | `B2-01-clean`, `B2-02-check-fails`, `B2-03-check-cannot-run`, `B2-04-answer-claims-built`, `B2-05-report-only` |
| S1-review-scope | `S1-01-clean`, `S1-02-untracked-defect`, `S1-03-committed-hidden`, `S1-04-ignored-excluded`, `S1-05-report-only` |
| S2-evidence | `S2-01-clean`, `S2-02-real-and-disproved`, `S2-03-no-evidence-kind`, `S2-04-location-outside-set` |
| S3-independence | `S3-01-clean`, `S3-02-same-session`, `S3-03-builder-notes-untracked`, `S3-04-builder-claims-in-ledger` |

Every family holds exactly one case with nothing planted, so a core that finds trouble
everywhere fails too.

## The run input

`input.json` is a small neutral object, not a core's input schema — the cores' schemas are the
builders' to design. A core's adapter reads what it needs from it:

| Field | Meaning |
|---|---|
| `seeded_input` | the version of this shape, `1` |
| `case` | the case id |
| `workspace` | absolute path of the git work tree |
| `run_dir` | absolute path of an empty scratch directory outside the workspace |
| `build_doc` | the build doc, workspace-relative |
| `slice` | the slice letter inside that doc |
| `base` | the git ref naming the slice's base; every case tags its base commit `base` |
| `answer` | the recorded answer file, case-directory-relative |
| `report_only` | true in the report-only cases, false elsewhere |
| `sessions` | signoff families only: `building` and `reviewing` session ids |

## The recorded answers

Where the behavior under test is the executor's (build) or the reviewer's (signoff), the case
supplies that answer as a file instead of calling a model, the way the recheck pilot's
`record-call` takes a verifier's report. Live model trials are not part of these suites.

An **executor** answer (`role: "executor"`):

| Field | Meaning |
|---|---|
| `seeded_answer` | the version of this shape, `1` |
| `case`, `role`, `session_id` | which case, which role, which session produced it |
| `claimed_status` | `complete`, `partial` or `stopped`, as the answer states it |
| `claimed_card` | the card value the answer states |
| `edits[]` | `path` and the `reason` the answer gives for touching it |
| `checks[]` | `name`, `command`, `result` (`passed`, `failing`, `not_run`), `exit_code`, `output` |
| `notes` | the answer's own prose |

A **reviewer** answer (`role: "reviewer"`):

| Field | Meaning |
|---|---|
| `seeded_answer`, `case`, `role`, `session_id` | as above |
| `checks_executed[]` | `name`, `command`, `exit_code`, `output` |
| `findings[]` | `location`, `severity`, `claim`, `scenario`, `evidence_kind` |
| `notes_kept[]` | the same keys, for what the answer kept as a note rather than a finding |
| `verdict` | the verdict string the answer states |
| `notes` | the answer's own prose |

Some answers are deliberately ill-formed or self-contradictory, so a core's refusal is tested
and not only its happy path. Nothing in an answer file or in a `CASES.md` states an outcome.

## The neutral vocabulary

The cores' result schemas do not exist yet, so the answer key does not name their fields. It
asserts facts the lane contract guarantees every core exposes, under the names below. A builder
maps its own result onto these names without seeing any value.

| Assertion | What it names |
|---|---|
| `base_ref` | the ref the run reports as the slice's base |
| `source_set_committed` | the paths the run reports as committed since the base, sorted |
| `source_set_changed` | the paths the run reports as changed in the working tree, sorted |
| `source_set_untracked` | the paths the run reports as untracked and not ignored, sorted |
| `out_of_scope_paths` | the source-set paths the run lists as outside the slice's named paths, sorted |
| `checks_passed` | the named checks the run reports as passed |
| `checks_failing` | the named checks the run reports as failing |
| `checks_skipped` | the named checks the run reports as skipped |
| `checks_not_passed` | the named checks the run reports as either failing or skipped, used where the contract allows either word |
| `check_output_contains` | per check name, a substring the run's reported output for that check carries |
| `card_after` | the slice's card value after the run |
| `terminal_status` | `stop` or `completion` |
| `answer_refused` | true when the run does not accept the recorded answer as recordable: it is neither acted on nor silently repaired, and the run says so |
| `writes_none` | true when the run writes nothing to the workspace and nothing to the log |
| `packet_must_include` | paths the review packet's file list carries |
| `packet_must_exclude` | paths the review packet's file list does not carry |
| `claims_absent_from_packet` | exact strings that do not appear in the material delivered to the reviewer |
| `raised_locations` | locations of findings the run reports as raised, sorted |
| `not_raised_locations` | locations the run does not report as raised |
| `note_locations` | locations the run reports as kept as notes rather than raised |
| `raised_severities` | per raised location, the severity the run records |
| `raised_evidence_kinds` | per raised location, the evidence kind the run records: `executed`, `read` or `reasoned` |
| `verdict_recorded` | true when the run records a verdict |
| `refusal_reason` | a short tag for why the run refused: `independence`, `answer_invalid`, `packet_incomplete` |
| `clean_review_checks_listed` | true when a result with no findings carries a non-empty list of the checks it executed, each with output |
| `either` | a list of assertion objects, at least one of which holds; used where the contract allows two passing shapes |

A value may be a scalar, a list, an object, or `{"any_of": [...]}` where the contract permits
more than one answer. A list assertion is read as an exact set unless the assertion's row above
says otherwise.

## Rules these cases were written under

- Synthetic content only. No text is copied from another repository, and nothing personal,
  legal, financial, or key-shaped appears anywhere in this folder.
- No network, no MCP tool, no model call, no harness launch, in the generators or in a case.
- Tests and grading runs build into a temporary directory and clean up.
  `PYTHONDONTWRITEBYTECODE=1`; no `__pycache__` is left behind.
- Neither a `CASES.md` nor an answer file states an outcome. The outcomes live in the answer key.
