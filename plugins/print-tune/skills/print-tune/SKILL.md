---
name: print-tune
description: Collaborative per-setting tuning of one specific model Tony is about to print on the Bambu H2C, driven by the sourced setting playbook. Use when Tony hands over a .3mf/STL to prep, says "tune this print", "prep this for the H2C", "let's set up this print", or wants to walk settings for a model. NOT an automation pipeline — every decision is discussed.
---

# print-tune — the walk

One model, one material plan, one collaborative pass through the settings that
matter, a baked project file, a verified GUI state, a print-log record. Same
way every time.

**What this is not.** Not CLI slicing (dual-nozzle CLI slicing is buggy; the
GUI is the source of truth for slicing). Not a black-box baked file — Tony
wants the discussion and the reasoning per setting; that is the product. Not
"touch every key": tune what fires, name what you deliberately leave alone.

## Authority and hard rules

- **The playbook governs:** `~/Developer/print-tune/docs/setting-playbook.md`,
  pinned to Bambu Studio **02.06.00.51**. Read its **Scope contract** first,
  and resolve any internal conflict by its **order-of-precedence** clause
  (rows govern). Coverage claims come only from
  `scripts/check-playbook-coverage.py` — never hand-count.
- **Version check before trusting the playbook:** if the installed Studio
  version differs from the pin, run the gate in `--project` drift mode and
  surface what moved before recommending anything.
- **Never fetch `wiki.bambulab.com`** (402s every automated fetch) and never
  invent a wiki URL. Captured wiki pages live in `docs/wiki-capture/`.
- **Known-risk sections:** §0, §5, §7, §10, §11 were repaired but never
  independently re-confirmed (recorded in the playbook banner). When a rec
  from those sections is load-bearing for this print, say so and verify it
  against ground truth (`docs/ground-truth/`, `scripts/dump-section-groundtruth.py`)
  before leaning on it.
- **Construction framing when explaining:** Tony's mental model is general
  contracting. Orientation is siting the building; the playbook is the spec
  book; the GUI check is the inspection before pouring.

## Phase 1 — Intake

1. Read the file headlessly before saying anything about it:
   - `.3mf`: `python3 scripts/bake-3mf.py <file> --report-only` for the baked
     config (preset targeted, plate, key values). Bounding box from
     `3D/3dmodel.model` if size matters and Tony hasn't stated it.
   - bare STL / geometry-only 3mf: no config to read — Tony must open it in
     Studio and save as a project before the bake step can work. Say so now,
     not at Phase 4.
2. Discuss intent — ask only what the file can't answer (AskUserQuestion for
   real forks): what the part is, the goal (`L:finish` / `L:strength` /
   `L:speed` / `L:accuracy` / `L:cost` — finish forks painted vs as-printed),
   materials + which nozzle, scale/orientation constraints, deadline.
3. Confirm bed fit and any scale decision with arithmetic, not eyeballing
   (H2C: 330×320×325; brim/skirt margin comes off that).

## Phase 2 — Fire the triggers

Walk the playbook's **Trigger vocabulary** table against the geometry, the
materials and the stated intent. Output a fired-trigger list with one line of
evidence each ("G:tall — 303 mm at 112 %").

- Stage 2 (mechanical trigger→signal map) is **not built**. Firing is
  judgment against the vocabulary; say that plainly in the walk report.
- A model that fires **no** triggers is a **failure of the trigger
  vocabulary**, not a pass — record it in the print log and flag it for the
  build plan.

## Phase 3 — The walk (the product)

Sections in order: **§0 orientation/mode/plate → §1 quality → §2 walls →
§3 infill → §4 supports → §5 adhesion → §6 speed → §7 cooling → §8 seam →
§9 special → §10 material assignment → §11 annex**. Orientation first — it is
the biggest lever and everything downstream depends on it.

Per section:
1. Pull the rows whose triggers fired (plus rows the intent obviously
   implicates). Skip the rest *out loud*: "§9: nothing fired, trusting preset."
2. For each pulled row: **recommendation first, then the reasoning**, the
   trade-off, and what the preset default would do instead. Cite the row; if
   its footnote disagrees with the row, the row governs — but flag it.
3. Decide **together**. AskUserQuestion for genuine forks (quality vs time,
   strength vs weight); decide routine calls yourself and state them.
4. Track two lists as you go — these become the record:
   - **CHANGED**: key, value, one-line why.
   - **LEFT AT DEFAULT, because…**: every row that fired but was deliberately
     not changed. A silent omission is the canonical baseline failure
     (`support_top_z_distance`, 2026-07-22); this list is the fix.
5. **The annex is part of every walk.** §10 (nozzle/material assignment) and
   §11 (temps, fan, volumetric, retraction) get walked even when no trigger
   fires — the baseline's biggest miss was never opening them. PETG anywhere
   in the job pulls the PETG rows (M:petg); dual-material support pulls
   M:dual-support.
6. **`M:second-nozzle` + `G:tall` pulls §9's prime-tower set.** A dual-material
   job builds a tower as tall as the part, and towers falling over is the
   most-reported H2-family failure, at 900–1000 layers. Set
   `prime_tower_brim_width` ~10 (not −1/auto) and `prime_tower_skip_points`
   off. Added 2026-07-31 after the first live walk missed it on a
   1,435-layer job — the tower is not "special", it is a printed object with
   its own aspect ratio, and nothing else in the walk looks at it.

Dead/inert keys: the playbook records which keys are dead or inert at the
shipped config. Never recommend one; if Tony asks about one, say why it does
nothing. `bake-3mf.py`'s guard does **not** catch code-dead keys — this walk
is the only defense.

## Phase 4 — Bake

```
python3 scripts/bake-3mf.py <input>.3mf --out <input>-CONFIGURED.3mf \
    [--process-preset "<leaf name>"] --set key=value ... [--overrides o.json]
```

- Never overwrite the input; output alongside it as `-CONFIGURED.3mf`.
- Preset switch (e.g. 0.20 Standard → 0.16 HQ) goes through
  `--process-preset` so the full resolved chain lands, then explicit
  overrides on top.
- Per-filament/per-extruder keys are JSON lists via `--overrides`; the script
  refuses scalars against lists and wrong widths by design.
- GUI-only actions (scale, nozzle mapping, plate choice, variable layer
  height tool) **cannot be baked** — put them on the GUI checklist instead.

## Phase 5 — GUI verification (mandatory, before slicing)

The bake report ends with a `VERIFY IN GUI` checklist. **A baked value is a
hypothesis until seen in the Studio panel** — #1704-class silent reversion on
reopen is documented in this repo's research.

0. **Before the file is opened: confirm Studio's machine state matches the
   file's target** — printer model AND both nozzle diameters (panel dropdowns,
   not just what's physically mounted). A mismatch does not revert single
   keys; Studio **replaces the whole process preset silently** (found
   2026-07-31: a 0.2-nozzle session swallowed the entire baked config and
   re-sliced at 0.10 mm Standard). This check comes first because every other
   check reads as mass reversion when it fails.
1. Tony opens the CONFIGURED file in Bambu Studio.
2. Every changed key is confirmed against the panel — screenshot or readback.
   Tony screenshots; you read. Ask for the specific panels the changed keys
   live in, not "screenshot everything".
3. A value that did not survive the open is **re-entered by hand in the GUI**
   and noted in the record.
4. GUI-only checklist items (scale, nozzle mapping) are performed now.
5. Only after this check is the **left-at-default report** emitted as final.
6. Tony slices in the GUI (authoritative), screenshots the sliced preview
   (supports, seam, estimate) — review it together before printing.

## Phase 6 — Record (built-in, not optional)

Write `docs/print-log/YYYY-MM-DD-<model>.md` before the print starts:

- files (input/output paths), model stats, intent, decisions made via
  AskUserQuestion;
- the CHANGED table (key, value, why) — the settings diff vs pinned defaults;
- the LEFT-AT-DEFAULT-because list;
- fired triggers (and any vocabulary failure);
- GUI verification result — which keys survived the open, which were
  re-entered by hand;
- sliced estimate (time/grams);
- an empty **Outcome** section to append after the print.

Commit it immediately (direct to `main`; print-log entries are written in
real time — that is the point). After the print, append the outcome: photos,
per-setting verdicts. **Attribution rule:** a failed print writes a cause
*hypothesis* in the log only; it becomes a playbook footnote only with a
corroborating second print or an agreeing external source. Never edit the
playbook from a single bad print.

## Files

| What | Where |
|---|---|
| Playbook (governs) | `docs/setting-playbook.md` |
| Coverage/drift gate | `scripts/check-playbook-coverage.py` |
| Bake transport | `scripts/bake-3mf.py` |
| Ground truth dump | `scripts/dump-section-groundtruth.py` |
| Print records | `docs/print-log/` |
| Wiki captures (offline) | `docs/wiki-capture/` |

All paths relative to `~/Developer/print-tune/` — the skill may fire from
anywhere (it runs from a plugin install), so use absolute paths
when running the scripts.
