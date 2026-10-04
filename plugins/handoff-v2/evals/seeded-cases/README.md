# E15 seeded cases: handoff-v2

The seeded cases that grade handoff-v2 against the claims of the plan's done-when for E15: handoff reconstructs state
from durable records (an answer that asserts a photograph fact the record contradicts is refused and nothing is
written); the question gate is the one pause (any question unanswered ends the run with nothing written anywhere); the
writes are additive (an earlier block changed, or a block outside `## Handoffs`, is refused before any write); the next
move is resolved from the record (a clean boundary, an open card's fix list, a complete loop with no kickoff line); no
implicit import of v1. Written in slice 1, hand-back 2 by its builder (the E15 lane contract section 12, owner pick
P4); the outcome of each case lives in an answer key outside this repository and outside every builder's reach. This
folder carries the cases, the vocabulary, and nothing else.

`RUNNING.md`, `observe.py`, `_lib/caselib.py` and `_lib/backlib.py` are the back frame's, byte for byte
(`skills/handoff-v2/references/back-files.txt`, the seeded rows); `lane_observe.py` is this core's observer, driving its
real CLI.

## The families

| Family | Planted condition (the lane contract's table) | Cases |
|---|---|---|
| H1-the-record-over-the-recollection | an answer asserting a card, an open item or a branch the record contradicts | 4 |
| H2-the-question-gate | one session question unanswered; one left out; a record question unanswered | 4 |
| H3-additive | an earlier block changed in the working copy; changed between the answers and the write; a block outside `## Handoffs` | 4 |
| H4-the-next-move | an open card; every card clear with no slice left; the owner naming the next slice | 4 |
| T1-no-v1-import | a planted v1 path, a deference, a Codex mention of a v1 skill in a scratch copy | 4 |

Every family holds one case with nothing planted (`<family>-01-clean`), so a core that finds trouble everywhere fails
too.

## Building and observing

```sh
PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh <family>/build.py --out <dir>
PYTHONDONTWRITEBYTECODE=1 uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 observe.py --all --out <dir>
```

Standard library only, `/usr/bin/python3` 3.9.6 and git 2.50.1, no network. Git runs only inside the throwaway
repositories under `--out`, with a fixed author, committer and date, so two builds of one case produce the same commits
and the same tree. H1's cases and H4-02 commit a records log: the bytes the records component's own `import-legacy`
wrote for that case's build doc when the family was generated, carried as a file of the case (the station reads it only
through the component's CLI). The observer drives the real CLI under `uv run` (the driver needs jsonschema); without it
every lane fact stays pending.

## The recorded answers

`answers/<case>.json` (`seeded_answer` 1, `case`, `role` `executor`, `session_id`) carries what the executor brings to
the station: `questions` (the session's questions for `gate`), `answers` (one entry per question id, in the owner's
words; a waiver's finding named by its location as `finding_at`, which the observer turns into the id the gate
printed), `perishables`, and, where the case plants one, `asserts` (what the executor believes of the photograph).
Nothing in an answer or a `CASES.md` states an outcome.

## The neutral vocabulary

| Assertion | What it names |
|---|---|
| `selected` | `select` exited 0 |
| `terminal_status`, `stop_tag` | the run's status and tag at the phase that ended it (`report`'s completion included) |
| `record_answer_refused` | `record-answer` refused the answer (exit 5) |
| `gate_sources` | the sources of every question `gate` printed (`session-question`, `chat-ruling`, `next-slice`, `doc-question`) |
| `chat_form` | which chat form the result carries: `handoff`, `gate-open`, or null |
| `doc_changed` | the build doc's bytes after the run differ from its bytes before the station ran (a drive step's own edit excluded) |
| `log_events_added` | the kinds of the events the run added to the records log, in order |
| `pointer_output` | the run directory holds `pointer.json` |
| `earlier_blocks_unchanged` | every handoff block the doc held before the station ran is in it after, byte for byte, in order |
| `new_blocks`, `new_blocks_in_handoffs` | how many handoff blocks the run added, and whether each sits under `## Handoffs` |
| `next_shape` | the next move's shape: `clean-boundary`, `open-card`, `loop-complete`, `owner-holds` |
| `kickoff` | the kickoff line, the doc's path written `<doc>`, or null |
| `recheck_slices`, `fix_list_locations` | an open card's slices to recheck and the locations its fix list names |
| `v1_findings_present`, `v1_finding_count` | the no-v1-import scan on the scanned copy |
| `writes_none` | the workspace unchanged by the run |

A list assertion is an exact list. A name the run has no fact for is omitted, never guessed.

## Rules these cases were written under

- Synthetic content only: a made-up bench-rig turn counter. Nothing personal, legal, financial or key-shaped, and no
  text copied from another repository.
- No network, no MCP tool, no model call, no harness launch, in the generators or in a case.
- Tests and grading runs build into a temporary directory and clean up; no `__pycache__` is left.
- Neither a `CASES.md` nor an answer file states an outcome. The outcomes live in the answer key.
