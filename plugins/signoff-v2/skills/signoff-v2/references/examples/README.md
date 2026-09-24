# Examples

Accepted examples here, rejected ones in `invalid/`. `scripts/validate-examples.py` checks both
sets and then drops each required field of every accepted example in turn, so a schema that has
stopped requiring what it says it requires fails even when both sets still pass.

The file name says which schema checks a file: `input-*` the input schema, `answer-*` the answer
schema, `result-*` the result schema.

Every accepted `result-*` and `input-*` file was produced by a real run of the CLI over a seeded
case and then had its two absolute paths replaced by `/workspace/signpost` and
`/tmp/<run id>`, so nothing here is hand-written prose about what the code might emit, and no
personal path is committed.

## Accepted

| File | The run it came from |
|---|---|
| `input-caller.json` | the resolved input of a caller-supplied run, defaults filled in |
| `input-report-only.json` | the same, with `report_only` true |
| `answer-clean.json` | a reviewer answer with no findings and four executed checks |
| `answer-with-findings.json` | a reviewer answer carrying one MAJOR with executed evidence |
| `result-completed.json` | a run that raised one finding, recorded it, and moved the card |
| `result-clean.json` | a clean review: no findings, its checks listed, card `signed off` |
| `result-report-only.json` | findings named as raised, nothing written, no verdict recorded |
| `result-stopped-answer-invalid.json` | a finding with no evidence kind: the whole answer refused |
| `result-stopped-independence.json` | the reviewing session is the building session |
| `result-stale-source-moved.json` | an untracked file added after the answer: `stale_source`, both identities, nothing recorded (Astra's F3) |
| `result-missing-input-legacy-ambiguous.json` | a hand-written review line Appendix A cannot place: stopped before levelling, with its document, line and bytes (F12) |
| `result-recording-failed-after-writes-landed.json` | `mirrors` refused after the block, the verdict doc and the card landed: every landed write reported from the receipt (F8) |
| `answer-with-findings-and-model.json` | the same MAJOR answer, carrying the reviewer's `model` as the adapter's sidecar map fills it (Astra's F5) |
| `result-stopped-floor-refused.json` | a Haiku session: `request` stops `floor_refused` before any reviewer request, nothing recorded (Astra's F5) |
| `result-stopped-floor-answer.json` | an answer naming a Sonnet reviewer under an Opus session: refused `floor` before it is accepted (Astra's F5) |
| `result-stale-source-final-append.json` | `src/late.py` added while the final card append was forwarded: `stale_source`, the landed appends and document steps reported, no verdict (Astra's F2) |
| `result-stale-source-recovered-after-a-kill.json` | `record` killed right after its card append landed, `src/late.py` added, `record` again: `stale_source`, and the card append the receipt held as `unknown` found in the log and reported landed at its seq, `recovered` (punch-F2) |
| `result-stale-source-card-absent-after-a-kill.json` | `record` killed before its card append reached the log, `src/late.py` added, `record` again: `stale_source`, the findings reported landed and the card reported under `records.not_landed` as `absent` (punch-F2) |

The two marked punch-F2 came from the E13 punch list's runs of the same CLI over seeded case
`S1-02-untracked-defect`, normalized the same way with the run directory as
`/tmp/signoff-fix2-run`.

The four marked F2 and F5 came from the E13 full-review fix round's runs of the same CLI over the
same case, normalized the same way with the run directory as `/tmp/<run id>`.

The three before them came from the slice 2 fix round's own runs of the same CLI over seeded case
`S1-02-untracked-defect`, normalized the same way with the run directory as
`/tmp/signoff-fix2-run`.

## Rejected

Each names the one rule it breaks. Together they cover the refusals a reader most needs the
schema to make: an unknown key rather than a silently ignored one, a ledger address the records
component itself refuses (`docs/records/`, `docs/reviews/`), a run id that is not one path
segment, an evidence kind outside the three, a verdict outside the three, a terminal status
outside the two, a packet file in no list, a verdict recorded on a stop, a report-only run
that recorded one, a document step in a state outside the three, an unplaceable record line
reported without its bytes, a floor block whose `met` is not a boolean, a refusal reason outside
the four, a packet entry whose `link_target` is not its link text, and a `records.not_landed` entry whose
`checked` is outside `absent` and `unreadable` (punch-F2).
