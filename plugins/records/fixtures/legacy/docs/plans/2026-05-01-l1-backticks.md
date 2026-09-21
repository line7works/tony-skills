# Crate packer, L1

Family L1 of contract section 11.1: one location wrapped in backticks, otherwise `file:line`.
The strict reader calls every line here ambiguous; the tolerant reader reads all three.

## Slice A — the packing loop
Status: signed off

## Punch list

### 2026-05-01 — review: Slice A
- MAJOR · `src/packer.py:12` · the lid closes before the count is taken · a half-packed crate ships · Slice A review
- MINOR · `src/packer.py:40` · the crate label is written twice · the second label hides the first · Slice A review

### 2026-05-02 — recheck: Slice A
- MAJOR · `src/packer.py:12` · (the lid closes before the count is taken) · fixed · executed the packer suite, 14 crates
