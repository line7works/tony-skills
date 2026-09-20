# Crate packer, F1

Family F1: a recheck line whose disposition and how-verified share one field, `fixed — how`.
Every dash the corpus uses is here: em, en, and hyphen.

## Slice A — the crate door
Status: signed off

## Punch list

### 2026-05-01 — review: Slice A
- BLOCKER · src/door.py:9 · the door latch is never tested · a crate opens in transit · Slice A review
- MAJOR · src/door.py:22 · the hinge count is hard-coded · a four-hinge crate is refused · Slice A review
- MINOR · src/door.py:44 · the door log has no crate id · a reader cannot tell two doors apart · Slice A review

### 2026-05-02 — recheck: Slice A
- BLOCKER · src/door.py:9 · (the door latch is never tested) · fixed — executed: the latch test runs on every crate
- MAJOR · src/door.py:22 · (the hinge count is hard-coded) · not fixed — static: the constant is still there
- MINOR · src/door.py:44 · (the door log has no crate id) · fixed - executed: the crate id is in every line
