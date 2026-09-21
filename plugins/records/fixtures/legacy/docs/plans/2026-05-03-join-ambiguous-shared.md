# Crate packer, an ambiguous join: a shared location

Join rule 4: two findings hold the location and neither claim matches, so the line is ambiguous
and the import of the whole document writes nothing (exit 5).

## Slice A — the crate seal
Status: signed off

## Punch list

### 2026-05-03 — review: Slice A
- MAJOR · src/seal.py:30 · the seal number is not checked against the manifest · a swapped crate passes · Slice A review
- MINOR · src/seal.py:30 · the seal colour is not recorded · a reader cannot tell this week's seals from last week's · Slice A review

### 2026-05-04 — recheck: Slice A
- MAJOR · src/seal.py:30 · (the seal is not verified) · fixed · executed the seal suite
