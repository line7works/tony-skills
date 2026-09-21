# Crate packer, F3

Family F3: a defect line with an extra or missing field, or without the
`broke: <claim> — <scenario>` form. The `fix-introduced` marker is the other legacy spelling.

## Slice A — the strapping tool
Status: signed off

## Punch list

### 2026-05-01 — review: Slice A
- MAJOR · src/strap.py:11 · the strap tension is never measured · a loose strap passes · Slice A review

### 2026-05-02 — recheck: Slice A
- MAJOR · src/strap.py:11 · (the strap tension is never measured) · fixed — executed: the tension is measured per strap
- MINOR · src/strap.py:30 · broke: the tension check runs twice per strap — the second run reports the first run's value · Slice A recheck
- MINOR · src/strap.py:41 · broke: the strap log now writes one line per measurement
- MINOR · src/strap.py:52 · fix-introduced: the tension constant is duplicated — one copy is never read
