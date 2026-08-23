# Digest — build plan (2026-08-20)

Intent: /digest is the compile half of Tony's note-capture system. /fb (existing,
unchanged) captures raw notes into `<repo>/docs/feedback.md`; /digest reads that raw
log and rewrites `<repo>/docs/notes.md` into one fixed current-state shape, so
week-long notes sessions stop dying in scrolled-out chat context. Scope doc (settled
ground, harvest first): `~/Developer/tony-skills/docs/digest-scope.md`. Cold-read
record: `~/Documents/precon-cold-reads/digest-cold-read-2026-08-20.md`.

Constraints:
- The deliverable is one skill: `~/.claude/skills/digest/SKILL.md` (markdown skill
  with `name` + `description` frontmatter, matching the house style of
  `~/.claude/skills/fb/SKILL.md`).
- /fb is NOT touched. No code, no scripts — the skill is instructions Claude follows.
- One run compiles the current repo only (repo root via `git rev-parse
  --show-toplevel`). Any repo with `docs/feedback.md` qualifies.
- AMENDED 2026-08-21 (per user, after Slice A rejection): /digest makes ZERO writes
  to feedback.md — the file is strictly read-only to this skill; there is no marker
  line. The cutoff is date-based: notes.md's footer date ("last compiled
  YYYY-MM-DD") is the sole cutoff record. On a run, /digest reads the whole log;
  entries dated after the cutoff are new, entries on the cutoff date are re-folded
  (folding is idempotent), older entries confirm existing board items. No cutoff
  (notes.md missing or lacking the footer) = first run: compile the entire history.
- On /fb-format files (a `## Inbox` / `## Dispositions` structure), ONLY the
  `## Inbox` section is input; `## Dispositions` records and boilerplate headers
  never reach the board (per user 2026-08-21). Freeform logs are read whole.
- An undated note takes its session heading's date, else the compile date.
- /digest fully owns notes.md: creates it if missing, overwrites any prior shape,
  and later runs may move/merge/resolve earlier items (living board). Raw history
  lives in feedback.md only.
- notes.md fixed shape, in this order: `# Notes — <project>`, then sections
  `## Open questions`, `## Ideas (undecided)`, `## Decisions made` (dated, one line
  each), `## Bugs & friction`, `## Parked`, then a footer line naming the raw log
  path and the last-compiled date.
- Raw logs are heterogeneous (Atlas: /fb one-line Inbox format; Caelan and
  sunday-sitdown: freeform session markdown). /digest reads any markdown notes.
- Classification is Claude's judgment; an ambiguous note lands in Open questions.
- Skill-lab feedback (`~/Documents/skill-lab/skill-feedback.md`) is out of the
  default path; the skill accepts an explicit target file argument for when Tony
  points it somewhere, and only then.
- No git write commands; leave files untracked. Protected paths stay untouched:
  `~/.claude/projects/*/memory/`, `*.jsonl` transcripts, `~/.claude/settings.json`.
- Test command: none (markdown skill); verification is manual, per slice criteria.

Out of scope:
- Transcript scraping (`~/.claude/projects/*/*.jsonl`) as an input — Tony chose /fb
  log-as-you-go 2026-08-20; brittle, ruled out.
- `/digest all` multi-repo sweep — v1 is current-repo only (Tony, Round 1).
- Archiving or rotating feedback.md — never wiped; archiving is a separate later
  decision if ever (Tony, Round 2).
- Touching skill-lab feedback by default — only on explicit summon (Tony, Round 1).
- Rebuilding or altering /fb — capture side is done.
- Canonical repo copy under tony-skills plugins/ — user-level skill only for v1;
  revisit if the skill ever ships publicly.

## Slice A — the /digest skill
Goal: author `~/.claude/skills/digest/SKILL.md` so any session can run a correct compile.
Requirements:
- R1: Frontmatter `name: digest` and a `description` that triggers on "/digest",
  "digest my notes", "compile the feedback log" — and states it runs only on the
  current repo (scope doc: current repo only).
- R2: Procedure — resolve repo root; read `docs/feedback.md` (on /fb-format files,
  the `## Inbox` section only); read the cutoff date from notes.md's footer (absent
  = first run, whole history); fold entries dated after the cutoff into
  `docs/notes.md` in the fixed shape above, re-folding cutoff-date entries
  idempotently and reworking existing items when a newer note changes their status
  (idea → decision, bug resolved out). Undated notes take their session heading's
  date, else the compile date.
- R3: Ambiguity rule stated: a note that doesn't clearly fit a bucket goes to Open
  questions, never guessed elsewhere.
- R4: Cutoff record stated: the notes.md footer date is the sole cutoff; it is
  written as part of the notes.md rewrite, so a failed compile never advances it.
- R5: Safety rules stated verbatim-strength: feedback.md is strictly READ-ONLY to
  this skill — zero writes, ever; no git writes; stop and report if
  `docs/feedback.md` is missing (never create it — that is /fb's file); a rev-parse
  failure (non-repo cwd) with no explicit target is a stop-and-report, and an
  explicit target needs no repo at all.
- R6: No-new-material rule: if no entries postdate the cutoff, report "nothing to
  digest" and change no files.
- R7: Optional explicit target: an invocation naming a file path compiles that file
  instead, writing its notes doc alongside it (`notes.md` in the same directory);
  without an explicit path, never leave the current repo.
- R8: Output block: report ends with the notes.md path, counts per section, the new
  cutoff date, and a confirmation that feedback.md was not modified.
Acceptance criteria:
- AC1: `~/.claude/skills/digest/SKILL.md` exists with valid frontmatter and covers
  R1–R8 — verify: manual read-through against this list, each R located in the file.
- AC2: The skill file nowhere instructs ANY write to feedback.md, creating
  feedback.md, or running git write commands — verify: manual read-through.
Footprint: `~/.claude/skills/digest/SKILL.md` (new).
Not in this slice: running a compile on any real repo (Slice B).
Depends on: nothing
Status: signed off

## Slice B — first live digest
Goal: prove the skill end-to-end on a real /fb-format repo, including the full
fb → digest → fb → digest cycle (retargeted to Atlas 2026-08-21, per user, after the
Slice A review showed a freeform log cannot exercise the fb-format seam).
Requirements:
- R1: Run /digest per the Slice A skill in `~/Developer/Atlas` (fb-format log; Tony
  may redirect at run time).
- R2: The run is a first run: no cutoff footer exists, so the entire `## Inbox`
  history compiles. `## Dispositions` and boilerplate never reach the board.
- R3: Cycle proof: after the first digest, Tony captures one real note via /fb, then
  /digest runs again and that note lands on the board.
Acceptance criteria:
- AC1: `~/Developer/Atlas/docs/notes.md` exists with exactly the six fixed sections
  in order plus the footer (raw log path + last-compiled date) — verify: manual:
  open the file, check section order and footer.
- AC2: `docs/feedback.md` is byte-identical before and after every digest run —
  verify: manual: `git diff docs/feedback.md` or pre/post copies, expect zero
  changes from digest (the /fb capture between runs is the only change, made by /fb).
- AC3: Every `## Inbox` note is represented in some bucket or deliberately folded
  (nothing silently dropped), and nothing from `## Dispositions` or the boilerplate
  header appears on the board — verify: manual: Tony spot-reads notes.md against
  feedback.md.
- AC4: An immediate rerun with no new capture reports "nothing to digest" and
  changes neither file — verify: manual: rerun, diff both files, expect zero changes.
- AC5: The R3 cycle works: the post-digest /fb note appears on the board after the
  second digest run — verify: manual: read the board.
Footprint: `~/Developer/Atlas/docs/notes.md` (new). `docs/feedback.md` is read
only (the mid-test /fb capture is /fb's write, not this slice's).
Not in this slice: digesting Caelan or sunday-sitdown backlogs (routine use, not
part of the build).
Depends on: Slice A
Status: built

## Build assumptions

### 2026-08-20 — Slice A
- Exact footer wording fixed as `Raw log: docs/feedback.md · last compiled YYYY-MM-DD` — spec named the footer's content, not its text · builder call
- Nothing-to-digest runs reuse the DIGEST report block form with both paths named — spec's R6/R8 silent on that report's shape · builder call
- Read-only git (rev-parse, diff) explicitly permitted in the skill; only write commands forbidden — spec's "no git write commands" read literally · builder call
## Deviations
## Discovered

### 2026-08-21 — Slice B
- Slice B ran live 2026-08-21 with Tony driving two peer sessions (atlas, sitdown). All five ACs verified pass on Atlas (board shape/footer; feedback.md byte-identical across all three digest runs; Inbox-only, nothing dropped; no-op rerun including the same-day-date trap; the fb→digest cycle note landed in Ideas). Bonus freeform first run on sunday-sitdown also clean (checksum-verified read-only). Verification was manual per the ACs, checksums recorded in-session by the monitoring session; no /signoff verdict exists for this slice — Status reflects built + user-witnessed acceptance.
## Punch list

### 2026-08-20 — review: Slice A
- BLOCKER · ~/.claude/skills/digest/SKILL.md:82-84 · marker-at-file-end is geometrically incompatible with /fb's insert rule (fb/SKILL.md:49-50: new notes land at end of ## Inbox, above ## Dispositions) · on any fb-format file (Atlas today, every file /fb bootstraps), digest run 1 stakes the marker below ## Dispositions; every subsequent /fb note lands above it; digest run 2+ reports "nothing to digest" forever — silent permanent note loss in the core fb→digest cycle · slice A review (correctness + seams, convergent)
- MAJOR · ~/.claude/skills/digest/SKILL.md:83-84 · marker lands inside/after ## Dispositions, a region /fb declares protected structure · the marker reads as the last Disposition and makes the section's end ambiguous for triage appends · slice A review (seams)
- MAJOR · ~/.claude/skills/digest/SKILL.md:27-31 · marker detection is not anchored to whole lines · a raw note quoting the marker string (e.g. feedback about /digest itself) is treated as the cutoff, silently discarding every real note between the true marker and the quote · slice A review (correctness)
- MAJOR · ~/.claude/skills/digest/SKILL.md:14-20 · non-repo and rev-parse-failure paths unspecified; explicit-target step reads as overriding the input file but not step 1's unconditional rev-parse · invoked from a non-repo cwd with an explicit target (the spec's own intended skill-lab case), rev-parse errors and the session must improvise · slice A review (correctness)
- MAJOR · ~/.claude/skills/digest/SKILL.md:33,39-42 · first run "entire file is the new material" + "nothing silently dropped" forces /fb's boilerplate header and the ## Dispositions section onto the board as raw notes · Atlas first run compiles 7 Disposition records and the Flow: boilerplate into buckets; the Inbox/Dispositions boundary is never mentioned · slice A review (seams)
- MINOR · ~/.claude/skills/digest/SKILL.md:34-35 · "nothing below the last marker" undefined for blank/whitespace-only lines · trailing blanks could make a no-op run compile "new material" or append a second marker · slice A review (correctness + seams)
- MINOR · ~/.claude/skills/digest/SKILL.md:86-87 · interrupted-run recovery state (notes.md written, marker absent) never described · a cautious next session may stop instead of recompiling; today-dated fallback dates shift on the recovery run · slice A review (correctness)
- MINOR · ~/.claude/skills/digest/SKILL.md:17-20 · explicit-target wording permits loose readings (a directory path; a target that IS notes.md) and can clobber an unrelated notes.md in the target's directory (e.g. ~/Documents/skill-lab/notes.md) · slice A review (correctness + seams)
- MINOR · ~/.claude/skills/digest/SKILL.md:29-31 · same-day re-run appends a second identical marker; duplicate markers never declared expected · slice A review (correctness)
- MINOR · ~/.claude/skills/digest/SKILL.md:66 · <project> in the board title has no defined source; two sessions could title the same board differently, churning the living board · slice A review (correctness)
- MINOR · ~/.claude/skills/digest/SKILL.md:84,91-93 · appending to a file lacking a trailing newline fuses the marker onto the last raw line — an edit of a raw line by the skill's own absolute rule, and the marker hides from line matching · slice A review (correctness)
- MINOR · ~/.claude/skills/digest/SKILL.md:41-42 · "every raw note represented" leaves note granularity undefined for freeform nested logs (topic vs bullet); AC3 spot-check could fail on either reading · slice A review (correctness)
- MINOR · ~/.claude/skills/digest/SKILL.md:74 · footer template hardcodes docs/feedback.md; explicit-target runs would write a misdirecting raw-log pointer · slice A review (spec)
- MINOR · ~/.claude/skills/digest/SKILL.md:34-35 · nothing-to-digest message assumes a marker date exists; first run on an empty log has none to cite · slice A review (spec)
- MINOR · ~/.claude/skills/digest/SKILL.md:29 · a line starting --- renders as an hr/setext hazard in Markdown preview; the grep target is invisible in rendered view — design fact of the frozen string, noted · slice A review (seams)

### 2026-08-21 — recheck: Slice A
- BLOCKER · ~/.claude/skills/digest/SKILL.md:82-84 · (marker-at-file-end geometrically incompatible with /fb's insert rule) · fixed — marker removed entirely; date-based cutoff at current :34-50, zero feedback.md writes at :36-37/:115-116
- MAJOR · ~/.claude/skills/digest/SKILL.md:83-84 · (marker lands inside/after ## Dispositions) · fixed — no marker exists; scenario cannot arise
- MAJOR · ~/.claude/skills/digest/SKILL.md:27-31 · (marker detection not anchored to whole lines) · fixed — no marker string to detect; cutoff is the notes.md footer date, current :36-37/:109-111
- MAJOR · ~/.claude/skills/digest/SKILL.md:14-20 · (non-repo and rev-parse-failure paths unspecified) · fixed — explicit target skips rev-parse (current :19-24); default-path rev-parse failure is a stop-and-report (current :29-31)
- MAJOR · ~/.claude/skills/digest/SKILL.md:33,39-42 · (first run compiles ## Dispositions and boilerplate onto the board) · fixed — fb-format input scoped to ## Inbox only, current :56-59; "nothing dropped" scoped to eligible notes
- MAJOR · ~/.claude/skills/digest/SKILL.md:39-50 · broke: nothing-to-digest exit strands same-day captures — run 1 stamps "last compiled <today>"; /fb captures a note today; run 2 finds no entries dated AFTER today and exits before the cutoff-date re-fold pass runs, leaving the note off the board until a later-dated entry arrives · Slice A's fix introduced it

### 2026-08-21 — recheck: Slice A
- MAJOR · ~/.claude/skills/digest/SKILL.md:39-50 · (nothing-to-digest exit strands same-day captures) · fixed — new material now includes unboarded cutoff-date entries (current :39-45) and the exit is gated on the board comparison, never dates alone (current :51-56); no-op rerun and first-run paths verified intact
