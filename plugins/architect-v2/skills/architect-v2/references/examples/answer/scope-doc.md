# Turnstile — scope doc (2026-09-20)

Intent: a small turn counter for the bench rig, so one session can report how many turns a fixture made.
Decisions:
- Python 3.9 standard library only — decided (the owner's words: "no dependencies on the bench")
- One module, no package — assumed (small and reversible; nothing imports it yet)
- Where the count is kept between sessions — parked: needs research
Out of scope: a web dashboard
Research:
Open:
- how often the counter resets
Next: /blueprint when ready.
