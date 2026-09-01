---
name: digest
description: Compile a repo's raw /fb feedback log into a current-state docs/notes.md — the compile half of the capture system (/fb captures, /digest compiles). Use when the user says "/digest", "digest my notes", "compile the feedback log", or wants the notes board refreshed. Runs only on the current repo's docs/feedback.md unless the user explicitly names another file.
---

# digest — compile the raw notes into the board

Sole job: read the repo's raw feedback log and rewrite `docs/notes.md` as a
clean current-state board. /fb owns capture; /digest owns compilation. The
raw log is the permanent record and is STRICTLY READ-ONLY to this skill —
/digest never writes one byte into a feedback log, ever. notes.md is the
living whiteboard, and /digest fully owns it.

## Target — current repo only

1. Resolve the repo root by running `git rev-parse --show-toplevel` now.
   The input is `<repo-root>/docs/feedback.md`, the output is
   `<repo-root>/docs/notes.md`. Never leave the current repo.
2. Explicit target: only when the user's invocation names a markdown FILE
   path (a directory or repo name is not an explicit target — ask, don't
   guess), compile that file instead. Its board is `notes.md` in that
   file's own directory; if a `notes.md` already exists there and is not
   in the board shape below, ask before overwriting it. An explicit
   target needs no repo — skip step 1's rev-parse entirely. Without an
   explicitly named file, no other file — including
   `~/Developer/tony-skills/docs/feedback.md` — is ever touched, and a
   target that is itself a `notes.md` is refused (a board is output,
   never input).
3. On the default path, `git rev-parse` failing (not a repo) is a
   stop-and-report: name the cwd and stop. Never improvise a repo root.
4. The input file missing? Stop and report the path checked. Never create
   a feedback file — that is /fb's file.

## The cutoff — a date, not a mark

The compile boundary lives in the board itself: notes.md's footer line
`last compiled YYYY-MM-DD`. Nothing is ever written into the feedback log.

- Read the whole log every run. New material is: every entry dated AFTER
  the cutoff date, plus every entry ON the cutoff date that is not yet
  represented on the board — a same-day capture after a compile is new,
  even though its date equals the cutoff. Cutoff-date entries already
  boarded are re-folded — folding is idempotent, so an already-boarded
  item simply confirms what's there. Older entries confirm existing board
  items and are otherwise left alone.
- No cutoff — notes.md missing, or lacking the footer — means first run:
  the entire eligible log compiles.
- An entry's date is its own stamp (/fb lines lead with YYYY-MM-DD); an
  undated note takes its nearest enclosing session heading's date, and
  failing that today's date.
- Nothing new — no entries after the cutoff AND every cutoff-date entry
  already on the board? Report "nothing to digest — <input path> has no
  new entries since <cutoff date>" (or, with no cutoff and an empty log,
  "the log is empty") and change NO files. The run ends there. This check
  runs AFTER comparing cutoff-date entries against the board, never on
  dates alone.

## What counts as input

Raw logs vary. Two shapes exist and are handled differently:

- **/fb-format** (a `## Inbox` section followed by `## Dispositions`):
  ONLY the `## Inbox` section is input. `## Dispositions` records, the
  `Flow:` boilerplate, and section headers never reach the board — they
  are /fb's bookkeeping, not notes.
- **Freeform** (session markdown, headings and bullets): the whole file
  is input, minus obvious boilerplate front matter.

A "note" is one captured thought: an /fb Inbox line, or a top-level
bullet (with its sub-bullets) in a freeform log. Every eligible note ends
up represented on the board or deliberately folded into an item already
there. Nothing is silently dropped.

## Compile

Sort each note by judgment into the board's buckets:

- **Open questions** — anything unresolved, and any note too ambiguous to
  place with confidence. Ambiguity always lands here, never guessed into
  another bucket.
- **Ideas (undecided)** — proposals with no ruling yet.
- **Decisions made** — dated, one line each, date per the cutoff section.
- **Bugs & friction** — defects, annoyances, things that fought back.
- **Parked** — explicitly deferred or waiting-on items.

Rework is allowed and expected: when a new note changes the status of an
existing item — an idea gets ruled on, a bug gets called resolved, a
question gets answered — move it, merge it, or resolve it off the board.
notes.md shows current state only; history lives in the raw log. A
missing or differently-shaped notes.md on the default path is created or
overwritten to the exact shape below (the explicit-target ask rule above
is the one exception).

If a prior run was interrupted, the only possible state is a board newer
than its own footer suggests — recompiling from the footer date is always
safe precisely because folding is idempotent. Never stop over it;
recompile.

## The board — exact shape of notes.md

    # Notes — <project>

    ## Open questions
    ## Ideas (undecided)
    ## Decisions made
    ## Bugs & friction
    ## Parked

    Raw log: <input path as written in this run> · last compiled YYYY-MM-DD

`<project>` is the repo directory's basename (for an explicit target, the
target file's parent directory name). Sections always appear, in that
order, even when empty. The footer's raw-log path names the actual input
(repo-relative `docs/feedback.md` on the default path, the full path for
an explicit target); its date is the machine-authoritative cutoff — it is
written only as part of a completed board rewrite, so a failed or
interrupted compile never advances it.

## Safety rules — absolute

- ZERO writes to any feedback log. Not a marker, not a fix, not a
  reformat. Read-only means read-only.
- Never create a feedback file. Missing input is a stop-and-report.
- Never run git write commands (add/commit/push); leave both files as
  they are on disk. Read-only git (rev-parse, diff) is fine.
- Never touch `~/.claude/projects/*/memory/`, `*.jsonl` transcripts, or
  `~/.claude/settings.json`.

## Confirm — every run

End with a report block:

    DIGEST: <project>
    Board: <absolute path to notes.md>
    Counts: open questions N · ideas N · decisions N · bugs N · parked N
    Cutoff: last compiled <date> (footer written)
    Raw log: <absolute input path> · unmodified (read-only)

State the counts from the board just written, and confirm the feedback
log was not modified. On a nothing-to-digest run, the block reports that
instead and names both untouched paths.
