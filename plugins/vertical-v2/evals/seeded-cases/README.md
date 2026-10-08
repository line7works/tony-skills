# E15 seeded cases: vertical-v2

The seeded cases that grade vertical-v2 against the claims of the plan's done-when for E15: vertical
checks the correct base and source scope; reviewer packets exclude prior verdicts and author advocacy;
the local review forms before any outside request; every outside finding is verified; an outside
reviewer is authorized only by the owner's word in the run; no implicit import of v1. Written in slice 1
by its builder (the E15 lane contract section 12, owner pick P4); the outcome of each case lives in an
answer key outside this repository and outside every builder's reach. This folder carries the cases, the
vocabulary, and nothing else.

`RUNNING.md`, `observe.py` and `_lib/caselib.py` are precon-v2's, byte for byte (the back frame,
`skills/vertical-v2/references/back-files.txt`); `_lib/backlib.py` is the back frame's own addition (a
case's history and dirt); `lane_observe.py` is this core's observer, driving its real CLI.

## The families

| Family | Planted condition (the lane contract's table) | Cases |
|---|---|---|
| V1-the-gate | a slice `built`; zero slices; a card and its `Status:` line disagree; a slice with no `Status:` line | 5 |
| V2-base-and-scope | a doc-recorded base; no base and no merge base; dirt inside the boundary; dirt outside it | 5 |
| V3-the-cold-packet | a prior verdict, a punch-list block and a handoff block; `REVIEW.md`; an untracked `.env` and builder notes | 4 |
| V4-independence-and-verification | an outside request before `record-local`; an outside finding at a location that does not exist | 3 |
| V5-the-word | `authorized` sought for a Claude row; for an outside row the answer did not name | 3 |
| T1-no-v1-import | a planted v1 path, a deference, a Codex mention of a v1 skill in a scratch copy | 4 |

Every family holds one case with nothing planted (`<family>-01-clean`), so a core that finds trouble
everywhere fails too.

## Building and observing

```sh
PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh <family>/build.py --out <dir>
PYTHONDONTWRITEBYTECODE=1 uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 observe.py --all --out <dir>
```

Standard library only, `/usr/bin/python3` 3.9.6 and git 2.50.1, no network. Git runs only inside the
throwaway repositories under `--out`, with a fixed author, committer and date, so two builds of one case
produce the same commits and the same tree. Two V1 cases commit a records log: the bytes the records
component's own `import-legacy` wrote for that case's build doc when the family was generated, carried as
a file of the case (the station reads it only through the component's CLI). The observer drives the
real CLI under `uv run` (the driver needs jsonschema); without it every lane fact stays pending.

## The recorded answers

`answers/<case>.json` (`seeded_answer` 1, `case`, `role` `executor`, `session_id`) carries the owner's
answer to the ask (`ask`: `rows`, `words`), the outside rows the executor asks for (`request_rows`), the
readers' half (`readers`: per call kind, `local` or an outside row, its `status`, `raw` text and `model`),
the executor's local answer (`local`) and the outside answer attempts in order (`outside`), with `{RUN}`
standing for the run id. Nothing in an answer or a `CASES.md` states an outcome.

## The neutral vocabulary

| Assertion | What it names |
|---|---|
| `gate_passed` | `gate` exited 0 |
| `terminal_status`, `stop_tag` | the run's status and tag when `gate` ended it |
| `short_slices`, `disagreeing_slices` | the slices the gate named short, and named as disagreeing with the records |
| `card_sources` | where the cards came from: `records`, `status-line` |
| `requests_built` | a request file exists in the run directory |
| `base_how`, `base_ref` | how the base was found (`doc`, `merge-base`, `owner`), and which of `main~1`, `main`, `HEAD` it is |
| `boundary_paths` | the paths of `git diff --name-status <base>..HEAD` |
| `dirt_inside`, `dirt_outside` | the dirt touching the boundary or the build doc, and the rest |
| `outside_packet_files` | the paths an outside repo row's packet lists (its workspace's files and its mandate) |
| `outside_withheld` | what that packet's withheld list names |
| `local_packet_documents` | the documents a local lens receives |
| `markers_found` | the planted marker words found in any packet file (the material `scope` cuts) |
| `copies_have_git` | any packet's workspace holds `.git` |
| `outside_request_refused`, `outside_request_files` | `request --outside` was refused; how many outside request files exist |
| `record_outside_refused` | an outside answer attempt was refused |
| `authorized_rows`, `local_authorized_rows` | the rows whose built request carries `authorized: true`, outside and local |
| `refuted_count`, `verdict`, `verdict_findings`, `verdict_docs` | the verdict's count, word and finding locations, and the verdict docs under `docs/reviews/` |
| `v1_findings_present`, `v1_finding_count` | the no-v1-import scan on the scanned copy |
| `writes_none` | the workspace unchanged by the run |

A list assertion is an exact list. A name the run has no fact for is omitted, never guessed.

## Rules these cases were written under

- Synthetic content only: a made-up bench-rig turn counter. Nothing personal, legal, financial or
  key-shaped (`TOKEN=not-a-real-value` is a marker word), and no text copied from another repository.
- No network, no MCP tool, no model call, no harness launch, in the generators or in a case.
- Tests and grading runs build into a temporary directory and clean up; no `__pycache__` is left.
- Neither a `CASES.md` nor an answer file states an outcome. The outcomes live in the answer key.
