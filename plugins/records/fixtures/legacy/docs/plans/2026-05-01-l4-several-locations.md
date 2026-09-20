# Crate packer, L4

Family L4: several locations in one field. The first becomes the location and the rest `more`; a
bare `:N` inherits the first location's file.

## Slice A — the label printer
Status: signed off

## Punch list

### 2026-05-01 — review: Slice A
- MAJOR · src/label.py:8, :19 and src/printer.py:33 · the label width is fixed in three places · a wider crate prints a clipped label · Slice A review
- MINOR · `src/label.py:60,74` · two label caches never agree · the second print shows the first crate's weight · Slice A review

### 2026-05-02 — recheck: Slice A
- MAJOR · src/label.py:8, :19 and src/printer.py:33 · (the label width is fixed in three places) · fixed · executed: one width constant, three call sites
