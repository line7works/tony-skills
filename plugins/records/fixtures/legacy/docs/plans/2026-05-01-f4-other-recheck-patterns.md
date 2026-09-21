# Crate packer, F4

Family F4: a recheck line of another pattern, three, four, or six fields, or a fourth field that
is not a disposition. Section 11.3 adds no rule for these, so each is recorded as
`legacy_unparsed`: it bears no state and blocks nothing.

## Slice A — the dock light
Status: signed off

## Punch list

### 2026-05-01 — review: Slice A
- MAJOR · src/dock.py:7 · the dock light never turns amber · a driver reads green as clear · Slice A review

### 2026-05-02 — recheck: Slice A
- MAJOR · src/dock.py:7 · fixed
- MAJOR · src/dock.py:7 · (the dock light never turns amber) · confirmed · executed the dock suite
