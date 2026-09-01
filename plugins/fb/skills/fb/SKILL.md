---
name: fb
description: Append a feedback note verbatim to the right inbox and confirm the path — capture only, never analysis. Use when the user says "fb", "log this feedback", "note this", or drops a mid-thread note to record. Loop-skill notes (blueprint/build/signoff/recheck, SKILL NOTE lines) go to the loop feedback doc `~/Developer/tony-skills/docs/feedback.md`; anything else goes to the current repo's docs/feedback.md.
---

# fb — capture one feedback note

Sole job: append the user's note, verbatim, to the correct inbox. No
analysis, fixes, severities, or triage — those belong to a later batch
session. Never write to installed skill files or any `## Dispositions` section.

## Route — re-derive fresh on EVERY capture, never reuse an earlier answer

1. Loop note — a SKILL NOTE, or the user says it concerns
   blueprint/build/signoff/recheck → `~/Developer/tony-skills/docs/feedback.md`,
   regardless of working directory. If that file is missing, stop and
   report — never recreate it.
2. Any other note → `<repo-root>/docs/feedback.md`, repo-root from running
   `git rev-parse --show-toplevel` now, for this capture.
3. Mismatch or no target — the note names or clearly concerns a different
   project than the resolved repo, or there is no repo and the note is not
   loop feedback → ask one question (which inbox?) and never guess. The
   answer routes this note only; when it names a repo, rerun the lookup
   inside it — the root returned is this capture's confirmed root.

## Files

The only file this skill may ever create: `docs/feedback.md`, at a repo
root this capture's own lookup confirmed, created on first use as:

    # Feedback — <project>

    Flow: notes are captured verbatim with zero analysis. Triage is a
    separate batch session (/blueprint turns a note into a slice).
    Dispositions are additive-only.

    ## Inbox

    ## Dispositions

Never run git write commands; leave the file untracked.

## Capture

- Quote the note verbatim; it is the line's last field and runs to end of
  line, so inner quotes need no escaping.
- Inbox line: `- YYYY-MM-DD · thread/project · skill · "note"`; repo docs
  use `area` in place of `skill`.
- Append as the last line of the `## Inbox` section, directly above
  `## Dispositions`; never edit, reorder, or delete lines.
- Project or skill/area missing? Ask for those and nothing else.
- An apparent duplicate of an existing Inbox line is logged anyway and
  flagged in the confirm — duplicates are signal.

## Confirm — every capture

End with one line naming the absolute path appended to and that file's
Inbox entry count (one note = one entry, however many lines it wraps),
e.g. `Logged to ~/Developer/inky-frame/docs/feedback.md (Inbox: 7)`. A
wrong path is visible in the same breath it happens — the drift guard.
