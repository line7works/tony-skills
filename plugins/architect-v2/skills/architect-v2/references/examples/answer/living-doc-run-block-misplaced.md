# Turnstile — architecture (2026-09-21)

Scope doc: docs/scope/2026-09-20-turnstile.md
Blind review: declined 2026-09-21

## Walkthrough target
Who: Sam Bench  ·  When: 2026-10-01  ·  Must be able to: count turns; reset the count

## v0 drawing
Components: turnstile.py (serves: count turns); reset() (serves: reset the count)
Data flow: the fixture calls turnstile.py; reset() zeroes the count
Diagram: fixture -> turnstile.py -> count

## Poured concrete (one-way doors)
- language — Python 3.9 — every bench script imports it
- storage — none in v0 — nothing is remembered

## Deferred
- a web dashboard — door stays open because the module has no I/O

### Run 1 — 2026-09-20 — trigger: first run
Exit ramp: system
Changed this run: first run

## Run log
### Run 2 — 2026-09-21 — trigger: first run
Exit ramp: system
Step 3.1 (walkthrough target): Sam Bench
Step 3.2 (candidates): module; service
Step 3.3 (one-way doors): language
Rulings: declined
Changed this run: first run
