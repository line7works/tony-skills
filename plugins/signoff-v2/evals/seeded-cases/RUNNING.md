# Running the seeded cases against signoff-v2

`README.md`, `_lib/` and the three families beside it are the slice 0 writer's, copied here
unchanged; nothing in them was edited. This file and `observe.py` are this lane's.

## The two commands

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --list
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --all --out <dir>
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 observe.py --case S1-02-untracked-defect --out <dir>
```

Each case is built into a temporary directory with its own family's `build.py`, driven through
the real CLI (`check-input`, `scope`, `request`, `record-answer`, `record`) with the case's own
`answer.json` fed at `record-answer`, and written to `<dir>/<case id>/observed.json`. The
temporary directory is removed; nothing is written into this repository.

`--records-root DIR` is passed through to the core when the records component is not beside the
plugin. `observe.py` needs no `jsonschema` of its own; the core it drives declares that itself.

## What `observed.json` carries

Facts, in the neutral vocabulary of `README.md`. No expected value appears anywhere in this
plugin: this lane never saw the answer key, so it could not write one. Names the table lists and
this core has a fact for are emitted; names it has no fact for are omitted rather than guessed —
`out_of_scope_paths` and `checks_skipped` belong to the build core and never appear here.

Keys beginning with `_` are for a person reading the file (`_status`, `_verdict`,
`_stop_reason_code`, `_packet_files`, `_packet_withheld`, `_trail`) and are not part of the
vocabulary.

### The three assertion-shaped names, and how each is answered

Three names in the table describe an assertion rather than a fact a run can emit. Each is
answered with the complete underlying fact, so the assertion is a straight test against it:

| Name | What this file carries | How to grade it |
|---|---|---|
| `packet_must_include` | the packet's COMPLETE file list, sorted | each asserted path is a member of it |
| `packet_must_exclude` | the same complete file list | no asserted path is a member of it |
| `claims_absent_from_packet` | the delivered material VERBATIM | no asserted string is a substring of it |

The file list is complete — it carries every path of the source set, once — so "absent from the
list" and "excluded from the packet" are the same statement. The delivered material is the exact
bytes the reviewer receives, so an absence assertion is decided against what was actually sent
rather than against a summary of it.

`not_raised_locations` carries every location the recorded answer named that the run did not
raise, so an assertion about a location that must not be raised is a membership test against it.

## What the suite beside this asserts, and what it does not

`skills/signoff-v2/scripts/tests/test_seeded_cases.py` drives every case through `observe.py`
and asserts only what the lane contract guarantees for EVERY run: a terminal status exists, the
source set has three lists and a base, the result validates, the report-only case wrote nothing,
a refused answer is neither acted on nor repaired, nothing is raised outside the source set, and
no run clears a finding. The outcome of each case — which finding is raised, which verdict is
recorded, which path is in the packet — is the control room's to grade against the key.

## Do not edit a case

A case, an answer or a generator that looks wrong is a question to the control room, with the
case id and what was observed. Nothing in these families may be changed here.
