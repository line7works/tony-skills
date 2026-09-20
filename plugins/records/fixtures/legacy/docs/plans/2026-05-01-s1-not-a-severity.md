# Crate packer, S1

Family S1: the first field is not a severity. `QUESTION` and its neighbours carry no state, so
every one of them is recorded as `legacy_unparsed` with its raw text.

## Slice A — the dispatch sheet
Status: signed off

## Punch list

### 2026-05-01 — review: Slice A
- MAJOR · src/dispatch.py:3 · the sheet is printed before the crates are counted · the sheet and the truck disagree · Slice A review
- QUESTION · src/dispatch.py:3 · should the sheet reprint after a recount? · Slice A review
- MINOR (pre-existing) · src/dispatch.py:19 · the sheet has no date · two sheets look alike · Slice A review
- note · the dispatch sheet is printed on the yellow paper · kept for the next reader
