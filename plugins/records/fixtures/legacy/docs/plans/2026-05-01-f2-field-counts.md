# Crate packer, F2

Family F2: a review finding with three, six, seven, or eight fields. Fields one to four are the
severity, the location, the claim and the scenario; the last field is who raised it; anything
between joins the scenario with the separator kept.

## Slice A — the pallet stacker
Status: signed off

## Punch list

### 2026-05-01 — review: Slice A
- MAJOR · src/stacker.py:15 · the stack height is unbounded · a tall stack topples · the ramp test reproduces it · Slice A review
- MINOR · src/stacker.py:28 · a stack is never numbered
- BLOCKER · src/stacker.py:61 · the pallet weight is read from the wrong column · every stack is under-weighted · observed on the Tuesday run · the loader agrees · Slice A review

### 2026-05-02 — recheck: Slice A
- MAJOR · src/stacker.py:15 · (the stack height is unbounded) · fixed — executed: the height is capped at six
