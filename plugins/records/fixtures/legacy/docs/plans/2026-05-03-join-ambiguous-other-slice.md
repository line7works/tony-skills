# Crate packer, an ambiguous join: the finding belongs to another slice

Join rule 3 needs the one finding at that location to belong to a slice the heading names. Here
it does not, so the line is ambiguous and the import stops.

## Slice A — the yard gate
Status: signed off

## Slice B — the yard log
Status: signed off

## Punch list

### 2026-05-03 — review: Slice A
- MAJOR · src/gate.py:8 · the gate opens before the yard is clear · a truck meets a walker · Slice A review

### 2026-05-04 — recheck: Slice B
- MAJOR · src/gate.py:8 · (the gate does not wait for the yard to clear) · fixed · executed: the gate waits
