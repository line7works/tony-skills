# records

The shared records component: one append-only event log per ledger document, versioned finding
IDs, source identifiers, derived state, a legacy importer, and a documented reader interface.

A ledger document is a build doc or a `docs/punch-list.md` — the Markdown that carries review
findings, recheck lines, waivers and reopenings. Until now that Markdown was both the
specification and the whole operational history. This component keeps the history in its own
file beside the documents, so the two are separately addressable: the document still says what
was asked for, and the log says what happened.

It has no `SKILL.md` and no model trigger. Stations and other consumers reach it through one
CLI and write against `references/interface.md`, which is the interface; `scripts/records_core/`
is internal.

## Status

Interface version 2, component version 0.2.0 (E13 amendment A7; version 1's shapes stay
available through `--interface-version 1`). Built in E12 of the skills v2 rebuild, in three
slices, under the lane contract the control room holds. Its first consumer is the `recheck-v2`
pilot, which moved onto it in E13 slice 1; the E12 freeze that kept `plugins/recheck-v2/`
byte-identical ended with that step. Rules have moved since, E13 amendments A2, A4 and A7, all
in the build record below. Running the importer over real repositories is a separate job, one
repository at a time.

## Build record

Facts about how this component was built, in order. Review results are not recorded here.

| Step | What it was | Tests after it |
|---|---|---|
| Slice 1 | the event log core: schemas, the chain, the lock, finding IDs, source identity, the clearing rule | 131 |
| Slice 2 | derived state, render parity with the pilot, the tolerant reader, the legacy importer, mirrors, survey | 318 |
| Slice 3 | `interface.md`, the manifest, the CLI's final shape, install probes in isolated homes | 376 |
| Amendment A6 | the installed-shape lookup in both resolver snippets | 430 |
| Outside review | one reviewer on another model family, in a copy with no `.git`, no answer key, no held-out requests | |
| Fix round | the review's fifteen findings and the owner's ruling on its three questions (A9), each test first | 515 |
| Verification | the same reviewer, once, on the closed list | |
| Second fix round | the four items verification left (A10), closed on the control room's own check | 536 |
| Third fix round | the items once listed for E13, fixed here on the owner's word (A11): two refusals published, examples regenerated, every required list pinned, the lock a response carries published | 591 |
| Recheck | the same reviewer, once more, on the second and third fix rounds and regressions | |
| Fourth fix round | what the recheck found: lock ownership at commit time is inode and bytes; a guard on the liveness judgement | 593 |
| E13 amendment A2 | the owner's ruling of 2026-09-21 on the recheck lane's finding 1: `append` admits a `waived` whose finding is `fixed` at the current head, which is the pair a station writes when one run clears an item the user also waived. A `waived` over a `waived`, and a `disposition: "fixed"` over anything but `open`, are refused as before, and the `known` and `identity` conditions did not move; `interface_version` stays 1 because `state` already decided the pair by its later-wins rule. The E12-2 freeze test over `plugins/recheck-v2` went with the same ruling; its sibling, that this component writes nowhere near the pilot, stays | 601 |
| E13 amendment A4 | the owner's ruling of 2026-09-22 ("Option A") on one defect with two halves, found by lane S and by the control room (CR-F2). `render` gains Appendix A's review block, one per slice, for a run's `finding_raised` events, so the component owns that grammar as it owns the recheck block's; the recheck block's bytes did not move. `import-legacy` recognises a record line that is byte-equal to what `render` produces for a NATIVE event the log already holds, and a `Status:` line matching the last card a native `card_set` or `card_observed` carries for its slice: it counts them under the new report field `native_rendered`, skips them, and never imports or questions them. Before this, a completed recheck run's own rendered lines were read back as news on the next levelling: a second `disposition` with `known: false` that `state` reported as `cleared_unbound`, and a review line that stopped the document exit 5 as a second raise of one finding. `interface_version` stays 1: every change is additive, and no reader of a version-1 response loses a field. The component version stays `0.1.0`: amendment A2 changed `append`'s clearing rule in this same step without moving it, and the version is written into every `log_opened` event, so moving it rewrites the chain hash of every shipped example and buries this fix's own diff. Whoever closes E13 can move it in one regeneration pass | 615 |
| E13 amendment A7 | the owner's ruling of 2026-09-22 ("Yes fix all 3") on three defects Astra's review of slice 2 found here. **F5**: `import-legacy` recognised a native line by its bytes alone, so a slice A review line placed under slice B's heading vanished instead of importing as B's finding, and two byte-identical native lines of two slices placed under one heading were both skipped without the ambiguity stop; a line is now the rendering of a native event only when its kind, its finding identity in the document's slice context (the heading's slice for a raise, one of the heading's slices for a recheck line; not the heading's date) and its bytes all agree, each native occurrence answers for one line, and a line left over meets the importer's existing rules, whose section 7 stop catches a second raise. **F9**: the review line writes the raise's raw location, so a ranged location reads back to the same finding id; the recheck block's bytes did not move. **F10**: A4's changed response shapes are interface version 2: `records.py` answers in version 2 by default and in version 1's closed shapes under the new top-level `--interface-version 1`; `import-report.schema.json` pins 2 on the two import shapes, and version 1's import report is frozen at `references/v1/import-report.schema.json`; the three copied station clients move to 2 together. Event `v` and the `f1:` prefix did not move. The component version moves to `0.2.0`: the minor digit, because on a `0.x` component the minor is the breaking digit and an interface version is a break for every reader that does not ask for the compatibility response; A4's deferral (the version sits in every `log_opened`, so moving it rewrites example hashes) no longer holds, because moving the interface version rewrites the same hashes, so the examples the suite reproduces from a live run were regenerated once for both | 637 |

Every count is the full suite under `/usr/bin/python3`, and the same count through `uv run`.
Rulings and amendments A1 to A11 and the builders' standing readings are in section 16 of the lane contract, `docs/plans/2026-09-20-records-e12.md`.

## Layout

```text
.claude-plugin/plugin.json   name and version; `component-identity` reads them
README.md                    this file
references/
  interface.md               the interface: commands, arguments, responses, exit codes, versions
  event.schema.json          one event line
  state.schema.json          the derived-state object `state` returns
  import-report.schema.json  what `import-legacy` and `survey` return
  resolutions.schema.json    the answers to ambiguous legacy records
  v1/import-report.schema.json  interface version 1's import report, frozen (E13 amendment A7)
  examples/                  valid and invalid examples for every schema
scripts/
  records.py                 the one CLI
  records_core/              the library the CLI imports (internal, not the interface)
  validate-examples.py       checks every example against its schema
  tests/                     the unittest suites (standard library)
fixtures/
  legacy/                    synthetic legacy documents, one per shape family
  build.py                   the deterministic generator for the git-backed cases
```

## Reaching it from a station

A station resolves the component root and runs `<root>/scripts/records.py`. The resolution
order, the snippets to copy, and the message a station prints when it finds nothing are in
`references/interface.md` under "Reaching the component". The short form: a `--records-root`
argument, then a `RECORDS_ROOT` environment variable, then the component beside the station; the
first that holds `scripts/records.py` wins, and nothing found is exit 3.

"Beside the station" is two lookups, which is what the owner ruled on 2026-09-20 (contract
amendment A6) after the install probes. On Claude Code 2.1.278 and Codex 0.154.0 an installed
plugin's root is `<config>/plugins/cache/<marketplace>/<plugin>/<version>/`, so two plugins from
one marketplace are siblings by NAME but each sits one directory below that, under its own
version. Route 3a is `<station plugin root>/../records`, the checkout shape, unchanged. Route 3b
is `<station plugin root>/../../records/<V>/`, the installed shape: a folder counts only when its
name equals the `version` in its own `.claude-plugin/plugin.json` and it holds
`scripts/records.py`, and among those the highest version wins, compared as dotted integers.
Modification time is never read — the live Claude Code cache keeps several folders per plugin,
most named like commit hashes, and one stale folder is newer than the live one. After any route
picks a root, the station reads `interface_version` from `component-identity` and stops with
exit 3 on a version it does not know.

## Running it

```sh
uv run scripts/records.py --help
uv run scripts/records.py survey --workspace .
```

`jsonschema==4.25.1` is the one dependency, declared in `records.py`'s PEP 723 block and
supplied by `uv run`. Started without it, every command that validates something exits 3 with
one line on stderr and nothing on stdout; `--help` still works, and so does
`component-identity`, which validates nothing and is what a station runs to confirm the root it
picked. The runtime floor is Python 3.9 and git 2.50.1. The
component runs git read-only, and only inside the workspace it is pointed at.

Only `append` and `import-legacy` write, and only two files, both under `docs/records/` inside
the workspace: the log and its lock. Everything else is read-only, including
`import-legacy --dry-run`. A process killed inside a write can leave the lock behind and, if the
kill lands inside the atomic replacement, a sibling `.<log file name>.*.tmp` file; `--break-lock`
removes the lock, names any temporary file it finds in `orphan_temporaries`, and deletes none of
them. Output is bounded: `survey` returns 50 documents unless `--limit` and `--offset` say
otherwise, and its counts still cover the whole workspace.

## Tests

```sh
cd scripts
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t tests
uv run validate-examples.py
```

The suite builds every fixture into a temporary directory and removes it, writes nothing into
the repository, and needs no network. The parity suite additionally reads the recheck-v2 pilot's
modules and its E7 fixture lanes read-only, and holds this component's copied reader to the
pilot's behaviour byte for byte.
