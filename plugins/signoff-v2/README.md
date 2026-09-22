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
(`plugins/records/references/interface.md`, version 1). `signoff_core/records_client.py` is
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
| the block's bytes, and the component's reader over them | `tests/test_block_form.py` |
| every seeded case, at contract level | `tests/test_seeded_cases.py` |

## Known open points

Three things are open, none of them hidden by the code. All three sit on the records component's
boundary, which is frozen for this step (ruling E13-2), so this plugin reports them and changes
nothing there.

1. **The review block is rendered here, not by the component.** At records interface version 1,
   `records.py render` renders a block only when the run holds a `disposition` or a
   `defect_raised`; a `finding_raised` comes back under `skipped`, and the only block heading it
   writes is Appendix A's RECHECK heading. Measured: one valid `finding_raised` appended, then
   `render --run-id` returns `{"block": "", "rendered": 0, "skipped": [{"kind":
   "finding_raised", "seq": 0}]}`. So `signoff_core/blocks.py` renders the review block from
   this run's events as the component stored them, in Appendix A's grammar. It is marked
   PROVISIONAL and is one function wide. Two tests hold it: the line form against Appendix A,
   and a round trip proving the component's own importer reads the written block back as the
   same facts, with the same computed finding identity.

2. **A document this station wrote cannot be levelled again.** After a run appends a native
   `finding_raised` AND writes its Appendix A line into the build doc, the next `import-legacy`
   over that document stops with exit 5: *"this line and line 0 compute the same finding id
   ... (section 7: two raises in one document)"*. The importer's idempotence is keyed on the
   `origin` records of lines IT imported — a second pass over an unchanged document reports
   `previously_imported: N, imported: 0, ok: true` — and not on the finding identities the log
   already holds natively. A line this station wrote was never imported, so the tracking never
   covers it. The behaviour is loud and writes nothing, and
   `tests/test_block_form.py` pins the observed exit 5 by name so the day the seam is fixed the
   test says so.

3. **The importer does not name an unparsed line** (the slice 1 builder's Finding 2, left open
   by the owner). Amendment A3 item 3 has this station stop on any importer signal, naming the
   line. Interface version 1 publishes `counts.legacy_unparsed` as a COUNT with no line number
   in any field, and the lines exist only as `legacy_unparsed` EVENTS, which requires a real
   import — a write, the opposite of a read-only stop. So the stop names the document and the
   count, says that interface version 1 does not name the lines, and points at `records.py
   survey`. A line the importer silently drops remains a known open point for the full review.

## Provenance

Built in E13 slice 2 against the stations E13 lane contract (section 10) and its amendment A3.
The seeded cases under `evals/seeded-cases/` were written in slice 0 by an agent that built
neither core; their expected outcomes live in an answer key this lane never saw, which is why
`observe.py` emits facts and never an expectation.
