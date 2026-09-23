# signoff-v2

The portable signoff core of the skills v2 rebuild (step E13, slice 2, lane S). It sits beside
the v1 `signoff` plugin the way `recheck-v2` sits beside `recheck`; nothing in v1 changes, and
both are renamed at cutover (owner pick P2).

An independent adversarial review of one built slice, ending in a signed verdict. What the v1
skill did in prose, this does in a script wherever the step is deterministic: the source set, the
review packet and what it withholds from the reviewer, the independence refusal, the evidence
rules, the severity mapping, and the recording transaction against the records component.

**Nothing it decides is new** (ruling E13-1, owner pick P5). v1's steps, severity-to-verdict
mapping, independence rule, stop rules and `REVIEW.md` sheet are carried over. What moved is
where the findings are kept and which half is mechanical.

## Layout

```
.claude-plugin/plugin.json       the plugin, at 0.1.0
skills/signoff-v2/
  SKILL.md                       the portable procedure: v1's steps, with each script call named
  references/
    signoff-contract.md          what each phase does, the authorized writes, the stop rules,
                                 the status vocabulary
    input.schema.json            the one validated input structure
    answer.schema.json           what the reviewer reports back
    result.schema.json           one result per run, with a terminal status for every run
    examples/                    accepted examples, and invalid/ for the rejected ones
  scripts/
    signoff.py                   the CLI phase driver
    signoff_core/                the library
    validate-result.py           schema plus the semantic checks
    validate-examples.py         the examples, both sets, plus a dropped-field pass
    tests/                       the suite
evals/seeded-cases/              the slice 0 cases, unchanged, plus observe.py and RUNNING.md
```

`adapters/` and `setups/` are slice 3's and are deliberately absent; the seam is left open.

## The phases

```sh
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py check-input <input.json>
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py scope         --run-dir D
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py request       --run-dir D
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py record-answer --run-dir D --answer FILE
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py record        --run-dir D
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py identity <workspace>
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py skill-identity
```

Exit codes are A7a's: 0 the phase succeeded, 10 the run reached a terminal status (a completion
included), 2 usage, 3 missing dependency, 4 validation, 1 anything else. `--help` and argument
checking work without `jsonschema`. Every response carries `interface_version` and
`plugin_version`.

## How it reaches the records component

Through the resolver and the CLI only, never a log file and never an import
(`plugins/records/references/interface.md`, version 2). `signoff_core/records_client.py` is
`recheck_core/records_client.py` **byte for byte**, and
`scripts/tests/test_records_client.py::TheCopyIsExact` fails the moment the two differ. Because
the copy is exact it carries the pilot's own `STATION` constant and test-hook name; nothing here
reads either, and a test holds that line.

## What it proves

| Claim | Where |
|---|---|
| correct review scope | `tests/test_scope.py`, `tests/test_packet.py` |
| independence | `tests/test_packet.py`, `tests/test_answer.py` |
| evidence-backed findings | `tests/test_answer.py` |
| a clean review lists its checks | `tests/test_answer.py`, `tests/test_seeded_cases.py` |
| report-only writes nothing | `tests/test_report_only.py` |
| the recording transaction and its kill windows | `tests/test_records_transaction.py` |
| the A7a interface | `tests/test_cli.py` |
| the repo's inspection sheet | `tests/test_sheet.py` |
| the block is the component's rendering, and the document levels again | `tests/test_block_form.py` |
| a second signoff on one document, and a `/recheck` after one | `tests/test_after_signoff.py` |
| every seeded case, at contract level | `tests/test_seeded_cases.py` |

## Known open point

One, reported rather than hidden, on a boundary this plugin may not write.

**The importer does not name an unparsed line** (the slice 1 builder's Finding 2, left open by
the owner). Amendment A3 item 3 has this station stop on any importer signal, naming the line.
Interface version 1 publishes `counts.legacy_unparsed` as a COUNT with no line number in any
field, and the lines exist only as `legacy_unparsed` EVENTS, which requires a real import, a
write, the opposite of a read-only stop. So the stop names the document and the count, says that
interface version 1 does not name the lines, and points at `records.py survey`. Since the slice
2 fix round (Astra's F12) a line Appendix A cannot place never reaches the importer: the pilot's
own stop check runs first and names the document, the line and its bytes. A line Appendix A
places and the importer still drops in silence is what remains open.

## The slice 2 fix round (Astra's review, amendment A6)

What changed in behaviour, each with its tests in `scripts/tests/test_fix2_astra.py`:

- **F3** `scope` pins the reviewed identity beside the packet; `record` compares the identity now
  before the first project-record write and ends `stale_source` (`source_moved`) with both on a
  mismatch. Every event carries the reviewed identity. Recovery allows only the run's receipted
  changes.
- **F4** builder-conversation provenance reaches answer validation: a citation of a builder-notes
  path or a withheld section, or a quotation found only in withheld material, anywhere in the
  answer (`checks_executed` included) is refused on independence.
- **F6** every fully completed target is checked against its final planned hash at the end of the
  document steps and before commit; an outside edit is `recording_failed/outside_edit` and is left
  intact; the card is reported from the receipt.
- **F7** a refusal of `records.py identity` is a named stop with a result (`identity_refused`).
- **F8** a `recording_failed` result is built from the receipt (landed appends, `document_steps`,
  the authorized verdict doc, the card as far as it got, `records_command`) and validates, exit 10.
- **F12** Appendix A's stop check before any levelling (`missing_input`, `legacy_ambiguous`,
  `unplaced`): `signoff_core/record_grammar.py` is the pilot's `ledger.py` byte for byte.
- **F16** the clean-review check runs after findings are partitioned; `record-answer` refuses a
  review that raises nothing and lists no check, and `record` validates the proposed completion
  before writing anything.

## Closed since round 1

Kept here because the README used to carry them as open.

- **The review block is the component's rendering** (records amendment A4): `render` returns
  `review`, and a document this station wrote levels again. `import-legacy` recognises a line
  byte-equal to what `render` produced for a native event the log already holds, and reports it
  under `native_rendered` instead of reading it as a second raise.
- **A `/recheck` starts on a finding this station raised** (pilot contract Revision 8, E13
  CR-F3). A natively raised finding carries no document line of its own; the pilot now addresses
  it where the component's rendering of it sits in the document, under the heading it actually
  sits under. `tests/test_after_signoff.py` drives `recheck.py start` after a signoff and asserts
  the accepting path outright: one checklist item, the reviewer's location and claim, the
  document's `### <date> — review: Slice <X>` heading, and the run handed to `verify`.

## Provenance

Built in E13 slice 2 against the stations E13 lane contract (section 10) and its amendment A3.
The seeded cases under `evals/seeded-cases/` were written in slice 0 by an agent that built
neither core; their expected outcomes live in an answer key this lane never saw, which is why
`observe.py` emits facts and never an expectation.
