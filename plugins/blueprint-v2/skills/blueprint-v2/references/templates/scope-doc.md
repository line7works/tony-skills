# Template: the scope doc (precon)

Shared by the four front cores (listed in `references/shared-files.txt`). Two parts, kept apart:
the FORM, the one fenced block tagged `form` below, which `station_core/templates.py` parses and
renders; and the READING, v1's own words about the form, quoted for the executor and never
rendered. The form is the v1 station's fenced form byte for byte (ruling E14-12); a change to it
is a stop, never a lane's edit. Source: the v1 precon station's Step 4, its fenced scope-doc form.

## Form

```form
# <Idea> — scope doc (<date>)

Intent: <what it is, who it's for, why — the why /blueprint needs>
Decisions:
- <one line> — decided (<source: Tony's words or the answered question>)
- <one line> — assumed (<why it didn't earn a question>)
- <one line> — parked: <needs research | needs prototype | waiting on <x>>
Out of scope: <item — reason>
Research: <paths/links to research Tony did himself, if any>
Open: <unresolved threads for the next sitting>
Next: /blueprint when ready.
```

## Reading (v1's words, quoted; the executor's reading, not a rule of this core)

> Every settled decision lands in the scope doc the moment it settles — not at the end of the sitting — appended at the tail of the `Decisions:` block, never below `Out of scope:`, `Research:`, or `Open:`; mid-doc edits keep the template's section order intact. Each line carries one tag:
>
> - `decided` — with its source: Tony's words in the discussion, or the answered question.
> - `assumed` — with why it didn't earn a question.
> - `parked` — with one of: `needs research`, `needs prototype`, or `waiting on <x>`.
>
> Every line traces to Tony's words or an answered question. The skill records; it never decides for him.
>
> **The out-of-scope channel.** When Tony rules something out — an option rejected, a feature deferred, a direction declined — it lands in the doc's `Out of scope:` section with the reason, not as a Decisions line. Those lines are /blueprint's descope evidence, they trace to Tony's words or an answered question like everything else, and they are what the report's `out of scope N` counts.

> **The scope doc.** Written to `<repo>/docs/scope/<YYYY-MM-DD>-<idea>.md` (the repo doc kit's layout: `docs/scope/` is precon's folder, names inside are date-topic; create the folder on first use) — the repo the idea unambiguously belongs to, whether or not the session was invoked inside it, with that call ledgered as `assumed` when it wasn't; when no repo owns the idea, `~/Documents/<idea>-scope.md` — the pre-repo staging home, which /sunrise empties into the new repo's `docs/` when it creates the repo. The doc is born at the first settled ledger line — always after triage, so a napkin idea ruled "no scope doc" never leaves an orphan file. `<idea>` is a kebab-case slug of the idea's working name; when the name isn't obvious, settling it is a round-one question, and a re-invocation looks for an existing doc under that slug in three places (`docs/scope/*-<idea>.md`, the older flat `docs/<idea>-scope.md`, and `~/Documents/<idea>-scope.md`) before creating anything — rule 8 depends on the slug matching. The path is printed in the report block; relocating the doc is Tony's or /sunrise's (its staged-doc adoption step, when it creates the repo), never this skill's. The format is load-bearing — these are the sections /blueprint Step 1 harvests — so keep it exact:

## Notes of the frame

- The ledger line forms (`decided`, `assumed`, `parked` with its three reasons) are the three
  `Decisions:` lines of the form; `station_core/ledger.py` reads them and `templates.py`
  renders them.
