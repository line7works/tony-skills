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

## Rejected

Each names the one rule it breaks. Together they cover the refusals a reader most needs the
schema to make: an unknown key rather than a silently ignored one, a ledger address the records
component itself refuses (`docs/records/`, `docs/reviews/`), a run id that is not one path
segment, an evidence kind outside the three, a verdict outside the three, a terminal status
outside the two, a packet file in no list, a verdict recorded on a stop, and a report-only run
that recorded one.
