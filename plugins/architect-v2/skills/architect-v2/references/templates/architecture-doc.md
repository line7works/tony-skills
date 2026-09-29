# Template: the architecture doc (architect)

Shared by the four front cores (listed in `references/shared-files.txt`). Two parts, kept apart:
the FORM, the one fenced block tagged `form` below, which `station_core/templates.py` parses and
renders; and the READING, v1's own words about the form, quoted for the executor and never
rendered. The form is the v1 station's fenced form byte for byte (ruling E14-12); a change to it
is a stop, never a lane's edit. Source: the v1 architect station's Step 4, its fenced architecture-doc form.

## Form

```form
# <Project> — architecture (<date of first run>)

Scope doc: <path> | Docless: <the reason the gate discussion landed on>
Blind review: <review file path (model, date)>, one per reviewer, comma-separated | declined <date> | failed <date> — <reason> | none — docless | none yet
Artifact: <private artifact URL, recorded after the first publish>

## Walkthrough target
Who: <named real person>  ·  When: <date>  ·  Must be able to: <short list>

## v0 drawing
Components: <what exists — one line each>
Data flow: <plain prose — what talks to what>
Diagram: <one simple diagram — ASCII or a mermaid block>

## Poured concrete (one-way doors)
- <category> — <decision> — <why it is one-way>

## Deferred
- <banked decision or deliberately-not-built item> — door stays open because <line>

## Run log
### Run <N> — <date> — trigger: <first run | idea blossomed | new precon | changed direction | ...>
Exit ramp: <the answer to "is there a system here at all?" — "system" and the interview continued, or "no system" and it ended here>
Step 3.1 (walkthrough target): <what was settled | n/a — exit ramp>
Step 3.2 (candidates): <the 2–3 candidates in one line each; chosen: <which>; rejected: <candidate> — <one-line why> | n/a — exit ramp>
Step 3.3 (one-way doors): <what was settled | n/a — exit ramp>
Rulings: <blind review: agreed on <spine>; N disagreements, each numbered with Tony's ruling | declined | not offered — docless | failed — <reason>>
Changed this run: <what changed vs the prior run, or "first run">
```

## Reading (v1's words, quoted; the executor's reading, not a rule of this core)

> One living doc per project, never a fork. Its home follows the precon scope doc: `<repo>/docs/architecture/<YYYY-MM-DD>-<slug>.md` when the scope doc is repo-owned (the repo doc kit's folder, created on first use; a re-run continues that file rather than dating a new one), `~/Documents/<slug>-architecture.md` otherwise — the pre-repo staging home, which /sunrise empties into the new repo's `docs/` when it creates the repo — where `<slug>` is the scope doc's idea slug: the `<idea>` of a `docs/scope/<YYYY-MM-DD>-<idea>.md` name, else the `<idea>` of a flat `docs/<idea>-scope.md` or `~/Documents/<idea>-scope.md` name (never the date). A re-run finds the living doc by glob before writing anything: `docs/architecture/*-<slug>.md`, then the older flat `docs/<slug>-architecture.md` (continued where it lies, never moved), then `~/Documents/<slug>-architecture.md`; only when none exists is a new dated file created. A docless run's doc goes to `~/Documents/<slug>-architecture.md` unless the gate discussion named a repo. Moving the doc between homes is Tony's (or /sunrise's adoption step), never this skill's.

> The format is load-bearing — /sunrise will provision exactly what the poured-concrete list names, and /blueprint will slice from the v0 drawing with the user-touchable slice up front — so keep it exact:

> Header lines keep that order (Scope doc, Blind review, Artifact) so a re-run never reshuffles them; each `|` is an either-or and the unchosen forms are dropped, never left as placeholders. The `Blind review:` line moves off `none yet` when the run ends: the file path when a review ran, `declined <date>` when Tony said no, `failed <date> — <reason>` when the call failed, `none — docless` when there was no offer.
>
> Four required parts, always present: the walkthrough target, the v0 drawing (component list + plain-prose data flow + one simple diagram), the poured-concrete list (the one-way decisions — one list, two names), and the deferred list (banked decisions plus deliberately-not-built items, each with a line confirming its door stays open). The exit-ramp form is the same skeleton with a few lines in it.
>
> **Re-runs.** When the idea blossoms or changes — possibly after a fresh /precon — a new run continues the same doc: a new `### Run <N>` block in the run log (N = one more than the highest existing block) with the date, the trigger, what changed, and the three steps in the order taken; superseded decisions elsewhere in the doc are struck through (`~~like this~~`), never deleted. The trail is the point: it ran once, and now it runs again because something changed.

## Notes of the frame

- The run-log continuation and the strikethrough rule of the reading are
  `station_core/runlog.py`'s.
