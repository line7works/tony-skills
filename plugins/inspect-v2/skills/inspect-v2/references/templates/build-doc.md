# Template: the build doc (blueprint)

Shared by the four front cores (listed in `references/shared-files.txt`). Two parts, kept apart:
the FORM, the one fenced block tagged `form` below, which `station_core/templates.py` parses and
renders; and the READING, v1's own words about the form, quoted for the executor and never
rendered. The form is the v1 station's fenced form byte for byte (ruling E14-12); a change to it
is a stop, never a lane's edit. Source: the v1 blueprint station's Step 4, its fenced build-doc form.

## Form

```form
# <Feature> — build plan (<date>)

Intent: <what this is, who it's for, what it enables — the why the builder needs>
Constraints: <stack, conventions, test command, hard requirements>
Out of scope: <deferred item — reason it was deferred (this is /signoff's written evidence)>

## Slice A — <short name>
Goal: <one sentence>
Requirements:
- <R1 — traceable to the discussion>
Acceptance criteria:
- <AC1: one measurable end state> — verify: <existing test | new test at <path> | manual: <steps>>
Footprint: <files expected to change>
Not in this slice: <adjacent work that belongs elsewhere>
Depends on: <nothing | Slice X>
Status: not started

## Slice B — ...

## Build assumptions
## Deviations
## Discovered
## Handoffs
## Punch list
```

## Reading (v1's words, quoted; the executor's reading, not a rule of this core)

> Before saving, hunt an existing build doc for this feature — `docs/plans/*.md` matched by its `<topic>`, then the older flat `docs/<feature>-build-plan.md` — and when one exists, extend it in place where it lies (rule 7: one living doc, never a fork; a flat doc is not moved). Only when none exists, save the new doc to `docs/plans/<YYYY-MM-DD>-<feature>.md` in the repo (the repo doc kit's folder for build docs and the first tier of /build's hunt; the older flat path is the second tier, so existing repos keep working; create `docs/plans/` on first use). The format is load-bearing — /build's contract and ledger, /signoff's punch list and sweep (which also writes recheck-headed clearing blocks), and /recheck's checklist assembly and its in-place `Status:` edits all key off it — so keep the load-bearing forms exact: the section names, the `Status:` label, the block headings, and the ·-separated line fields:

> The last five sections start empty and belong to the other skills — /build appends assumptions, deviations, and discoveries; /signoff and /recheck append the punch-list blocks; /handoff appends its dated blocks to `## Handoffs`; the dated `WAIVED`/`REOPENED` lines are appended by whichever station receives the user's word; and inside the punch list, /build's own lines are limited to those two plus its dated `REBUILT` line. Scaffold them; never pre-fill them. Each slice's `Status:` line is likewise maintained downstream — /build sets `built`; /signoff, /recheck, and recorded user waivers set the verdict states.
