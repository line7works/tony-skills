# /fb capture skill — build plan (2026-08-03)

Intent: one keystroke-cheap habit for dropping feedback notes from any
thread, routed to the right inbox: notes about the four build-loop skills
land in the standing skill-lab feedback doc; notes about whatever repo Tony
is building land in that repo's own feedback doc. Capture is clerical by
design — verbatim logging with zero analysis — so the model never starts
fixing things from inside an intake thread. Runs cheap (Sonnet-class, low
effort) per the user's chosen thread settings; nothing in the skill may
demand more.

Constraints: prose skill executed as law by fresh sessions; personal skill
in ~/.claude/skills/, NOT mirrored to the claude-build-loop GitHub repo
(2026-08-03: the repo ships the four loop skills only). Line budget: SKILL.md
≤ 60 lines including frontmatter — the skill lives in long cheap capture
threads where an invoked body is a recurring token cost, so every line earns
its place (Anthropic 2026 guidance; budget added 2026-08-03 per user after
the alignment review). No test suite — verification is read-back plus
paper-walks. The four loop skills are byte-untouched by this work. /fb never
runs git write commands; files it creates are left untracked (the git gates
are the user's). Every guard in this skill is prose, not enforcement — a
session that ignores the rules is not mechanically blocked; the path-echoing
confirm (A-R5) exists so any such failure is visible immediately (deliberate,
matching the loop's prose-by-design posture; a hook is the upgrade path if
the record ever shows drift).

Out of scope: a capture server or shell alias (rejected 2026-08-03 — user
declined, "ill jsut setup my own terminal window when i want"); loop-only
routing (rejected 2026-08-03 — agnostic chosen so one habit serves every
project); a loose instructions doc instead of a skill (rejected — the skill
re-invocation is the mid-thread rules refresh); auto-triage or any
disposition-writing at capture time (triage is a separate, user-ordered
batch session); changes to skill-feedback.md's format (shipped by Slice O of
the loop plan, governed by the loop).

## Slice A — the /fb skill
Goal: create the /fb capture skill with per-note routing and the four
anti-drift guards, exactly as settled in the 2026-08-03 discussion.
Requirements:
- A-R1: new skill at `~/.claude/skills/fb/SKILL.md`, invocable as /fb, whose
  sole job is appending feedback notes to the correct inbox. It performs no
  analysis, proposes no fixes, assigns no severities, and never touches any
  file in ~/.claude/skills/ or any ## Dispositions section. (Trace: the
  capture-prompt discussion, 2026-08-03.)
- A-R2: routing, re-derived fresh on EVERY capture, never reused from
  earlier in the thread: (a) a note about the four build-loop skills — a
  SKILL NOTE, or the user says it concerns blueprint/build/signoff/recheck —
  routes to `~/Documents/skill-lab/skill-feedback.md` regardless of working
  directory; (b) any other note routes to `<repo-root>/docs/feedback.md`
  where repo-root comes from running `git rev-parse --show-toplevel` at
  capture time; (c) when the note names or clearly concerns a different
  project than the resolved repo, or the lookup says there is no repo and
  the note is not loop feedback, the skill asks one question — which
  inbox — and never guesses; the user's answer routes that note. (Trace:
  "route per note, not per thread"; "mismatch means ask"; "not in a repo,
  no target" — 2026-08-03.)
- A-R3: file creation is limited to exactly one case: `docs/feedback.md` at
  a repo root the same capture's lookup just confirmed, created on first
  use with the same three-part shape as the skill-lab doc (flow header
  stating verbatim capture / batch triage to /blueprint slices /
  additive-only dispositions; append-only `## Inbox`; `## Dispositions`).
  The skill-lab doc is never created by /fb — if it is missing, stop and
  report, do not recreate it. (Trace: "the only file it may ever create";
  the loop doc is Slice O's artifact.)
- A-R4: the capture discipline, stated as rules: the note is quoted verbatim
  including its punctuation; the Inbox line is `date · thread/project ·
  skill · "note"` in the skill-lab doc and `date · thread/project · area ·
  "note"` in repo docs; appends land at the Inbox tail only; existing lines
  are never edited, reordered, or deleted; when project or skill/area is
  missing the skill asks those things and nothing else; an apparent
  duplicate of an existing Inbox line is logged anyway and flagged in the
  confirm — duplicates are signal. (Trace: the capture prompt, 2026-08-03.)
- A-R5: every capture ends with a one-line confirm that names the absolute
  path appended to and the running Inbox count of that file (e.g. "Logged
  to ~/Developer/inky-frame/docs/feedback.md (Inbox: 7)") — the guard that
  makes any routing drift visible in the same breath it happens. (Trace:
  "the confirm line always carries the full path" — the load-bearing
  guard.)
Acceptance criteria:
- AC1: the skill file exists at ~/.claude/skills/fb/SKILL.md with name `fb`
  in frontmatter, and the frontmatter description meets the Anthropic
  description standard: it states WHAT the skill does (append feedback
  notes verbatim to the right inbox) and WHEN to use it, and it contains at
  least these trigger phrases verbatim: "fb", "log this feedback", "note
  this" — verify: read the frontmatter; grep each trigger phrase; confirm
  /fb appears in the session's skill listing. (Tightened 2026-08-03 per
  user after the alignment review — the prior wording, "triggers on
  feedback-capture intent", was not gradeable.)
- AC5: wc -l ~/.claude/skills/fb/SKILL.md ≤ 60 — verify: wc.
- AC2: all four anti-drift guards are present and survive a paper-walk of
  four scenarios: (1) loop note pasted while cwd is a repo → skill-lab doc;
  (2) repo note in its own repo → that repo's docs/feedback.md; (3) note
  naming project X while cwd is project Y → the one question, no guess;
  (4) note outside any repo, not loop feedback → the one question, no file
  created — verify: read the skill; walk each scenario against its text.
- AC3: the capture discipline of A-R4 and the confirm of A-R5 are each
  present, and no sentence licenses analysis, severity, fixes, or
  Dispositions writes — verify: read the skill.
- AC4: the four loop skills are byte-unchanged — verify: wc -l =
  143/108/91/107 and md5 match against pre-build capture.
Footprint: ~/.claude/skills/fb/SKILL.md (new file) only.
Not in this slice: adding /fb to the claude-build-loop repo; retrofitting
docs/feedback.md into existing repos ahead of first use (files appear on
first capture, per repo, on demand); the triage prompt/procedure (lives in
chat practice for now — a candidate future skill if batch triage becomes
routine).
Depends on: nothing
Status: signed off

## Build assumptions
### 2026-08-03 — build: Slice A
- The repo feedback doc's exact template text (title `# Feedback — <project>`,
  flow-header wording) — the spec named the three parts, not verbatim prose;
  written to match the skill-lab doc's shape · builder call
- When rule (c)'s one question routes a note to a repo other than the resolved
  one, creation of a missing docs/feedback.md still requires running the lookup
  at that named root within the same capture (reading A-R3's "the same
  capture's lookup just confirmed" as satisfiable by a lookup run at the
  user-named root) · builder call
## Deviations
### 2026-08-03 — fix pass: Slice A
- fb/SKILL.md:24-25 · rule 3 now instructs rerunning the lookup inside a
  user-named repo, whose returned root is this capture's confirmed root —
  closes the underivable-creation-permission MAJOR · per user ("Fix the majors")
- fb/SKILL.md:57-58 · confirm count pinned to Inbox entries ("one note = one
  entry, however many lines it wraps"), replacing the two-way-readable
  "running Inbox count" · per user ("Fix the majors")
- fb/SKILL.md:49 · dropped the redundant word "existing" from the tail-append
  bullet to hold AC5's 60-line budget against the rule-3 addition; meaning
  unchanged (all lines are existing lines) · builder call

### 2026-08-03 — fix pass 2: Slice A (two named MINORs)
- fb/SKILL.md:48-49 · Inbox line format now carries the leading "- " bullet
  and pins the date as YYYY-MM-DD; the two per-target formats fused into one
  line ("repo docs use `area` in place of `skill`") to hold the 60-line
  budget — closes the A-review MINORs at :47-48 (missing bullet) and :47-48
  (date unpinned) · per user ("fix these: 1. Missing bullet ... 2. Date
  format unpinned")
## Discovered
## Punch list
### 2026-08-03 — review: Slice A
- MAJOR · fb/SKILL.md:21-24 · rule-3 answer naming an unresolved repo leaves creation permission underivable (Files gate at :28-30 demands "this capture's own lookup confirmed") · cwd not a repo, note about Helix, user answers "Helix", Helix lacks docs/feedback.md → one session creates the file, another refuses as unconfirmed; divergent mainline behavior · A-review
- MAJOR · fb/SKILL.md:57-58 · "running Inbox count" has two readings — entries vs physical lines · real skill-lab doc: 2 entries spanning ~13 wrapped lines → one session confirms "Inbox: 2", another "Inbox: 13"; the count half of the drift guard cannot signal drift · A-review
- MINOR · fb/SKILL.md:51 · bare /fb with no note leaves no licensed question to obtain one · user types /fb intending to paste next → strict session stalls or asks an unlicensed question; downgraded from MAJOR — no write can occur without a note, and :51's "nothing else" is conditioned on the metadata ask · A-review
- MINOR · fb/SKILL.md:15-16 · unconditional "a SKILL NOTE" disjunct routes non-loop SKILL NOTEs to the loop doc · a SKILL NOTE from a non-loop skill lands in skill-feedback.md against that doc's own scope; spec A-R2(a) shares the wording — open question to the user · A-review
- MINOR · fb/SKILL.md:11 · "never write to" narrows spec A-R1's "never touches" for Dispositions · a session reads/summarizes Dispositions mid-capture and claims compliance · A-review
- MINOR · fb/SKILL.md:19-20 · rule 2 lacks an explicit rule-3 precedence guard · strictly sequential reader appends to cwd repo before reaching the mismatch check · A-review
- MINOR · fb/SKILL.md:57-59 · confirm demands "the absolute path" but the example is tilde-relative · sessions emit either form · A-review
- MINOR · fb/SKILL.md:1-60 · file sits at exactly 60/60 lines under AC5 · any future one-line addition busts the budget · A-review
- MINOR · fb/SKILL.md:47-48 · date format unpinned in the Inbox line · two sessions write 2026-08-03 vs 8/3/26 into the same file · A-review
- MINOR · fb/SKILL.md:47 · "thread/project" readable as one either/or field or two-part literal, and "thread" is not in :51's askable set · incompatible lines in one file; missing thread value has no licensed question · A-review
- MINOR · fb/SKILL.md:19-20 · worktree/submodule rev-parse roots fragment a project's inbox · capture from a linked worktree creates a second docs/feedback.md that dies with the worktree · A-review
- MINOR · fb/SKILL.md:49 · pre-existing docs/feedback.md without a ## Inbox section leaves the append point undefined · hand-made file → no referent for "Inbox tail", no stop-and-report path · A-review
- MINOR · fb/SKILL.md:6 · multiple notes in one message undefined · N notes → N captures, one fused line, or refusal; text picks none · A-review
- MINOR · fb/SKILL.md:52-53 · duplicate flag vs "one line" confirm formatting tension · sessions format the flagged confirm differently · A-review
- MINOR · fb/SKILL.md:11 · latent: a git repo ever containing ~/.claude/skills would collide rule 2 with the self-protection rule · today rev-parse fails there so rule 3 fires; latent only · A-review
- MINOR · fb/SKILL.md:47-48 · Inbox line format omits the leading "- " bullet every existing skill-lab entry uses · bare-line append breaks the doc's list formatting and bullet-based counting · A-review
- MINOR · fb/SKILL.md:32-40 · repo template omits the format-carrying header lines the skill-lab doc carries (line format, append-only rule) · a later session touching a repo feedback doc without /fb has no in-file law · A-review
- MINOR · fb/SKILL.md:3 · description's "drops a mid-thread note to record" can read as license to auto-invoke /fb after a loop report emits a SKILL NOTE · capture without the user's word; visible via confirm · A-review
- MINOR · fb/SKILL.md:3 · "note this" trigger collides with Apple Notes intent on this machine · a Notes.app request gets captured to a feedback inbox; visible via confirm · A-review
- info · fb-skill-build-plan.md:99-100 · AC4 lists counts as 143/108/91/107, not in the blueprint/build/signoff/recheck order used elsewhere · positional pairing false-fails; multiset matches · A-review

### 2026-08-03 — recheck: Slice A
- MAJOR · fb/SKILL.md:21-24 · (rule-3 answer naming an unresolved repo leaves creation permission underivable) · fixed — governing text now at :23-25: rule 3 mandates rerunning the lookup inside the named repo and declares the returned root "this capture's confirmed root", the Files gate's exact predicate; strict-refusal reading no longer exists
- MAJOR · fb/SKILL.md:57-58 · ("running Inbox count" has two readings — entries vs physical lines) · fixed — unit pinned to entries at :57-59 ("one note = one entry, however many lines it wraps"); verified against skill-feedback.md: 2 entries across 12 wrapped lines yield exactly one answer
- MINOR · fb/SKILL.md:24 · broke: "rerun the lookup inside it" gives no procedure for locating the named repo on disk — duplicate checkouts (~/Developer/Helix plus a stale clone elsewhere) each confirm their own root, licensing docs/feedback.md creation in the wrong checkout; the path-echoing confirm makes the miss visible · Slice A's fix introduced it

Note · 2026-08-03 · the A-review MINOR at fb/SKILL.md:15-16 (unconditional SKILL NOTE routing): user ruled "leave it, for now" — not a defect to fix; skill-feedback.md serves as the inbox for notes about any skill, loop or not. Revisit only if non-loop skill notes start landing wrong.

### 2026-08-04 — recheck: Slice A (items from a cross-model /signoff pass; never recorded as a review block — see SKILL NOTE)
- MAJOR · fb/SKILL.md:47 · ("Quote the note verbatim" conflicts with embedding the note inside double quotes; no escaping rule) · fixed — governing text now at :45-46, "it is the line's last field and runs to end of line, so inner quotes need no escaping"; `fb rename "draft" to "saved"` in repo app / area copy yields exactly one derivable line, `- 2026-08-04 · app · copy · "rename "draft" to "saved""`, and the escaped reading is explicitly forbidden · static paper-walk, independent reviewer
- MAJOR · fb/SKILL.md:50 · ("Inbox tail" unpinned when `## Inbox` is followed by `## Dispositions`) · fixed — governing text now at :49-50, "Append as the last line of the `## Inbox` section, directly above `## Dispositions`"; the end-of-file reading is closed by a landmark the skill's own creation template guarantees, so the first capture in a new repo has one landing spot · static paper-walk, independent reviewer
