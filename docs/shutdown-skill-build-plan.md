# /shutdown skill — build plan (2026-08-09)

Intent: Tony restarts Terminal or switches Anthropic accounts several times a
week. Before each shutdown he asks every open Claude Code session to write a
self-contained handoff to `~/Documents/handoffs/` so fresh sessions can resume
with zero context (23 such files exist; conventions studied 2026-08-09). This
skill formalizes that: `/shutdown` makes the current session settle up — clean
its tree, verify state, write the handoff — and `/shutdown all` triggers every
open session on this account to do the same. Tony pastes each handoff's read
line into the proper new thread himself; the skill never manages resume.

Constraints:
- Skill lives at `~/.claude/skills/shutdown/SKILL.md`, same frontmatter format
  as the existing loop skills (see `~/.claude/skills/fb/SKILL.md`).
- Handoff files go to `~/Documents/handoffs/`, named
  `YYYY-MM-DD-<topic>-handoff.md`. Files are never moved, archived, or
  deleted; no stale-file scan of the folder (Tony curates it himself).
- Git gates hold everywhere: local commits fine, never push/PR/merge, never
  commit WIP directly to a repo's default branch.
- Sweep reaches only live Claude Code sessions on the same Anthropic account
  (ListAgents scope) — so `/shutdown all` must run BEFORE switching keys.
  Terminals with no Claude session are out of reach (Tony preps those by
  hand).
- The skill never touches git state: no commits, no branches, no staging.
  Tony preps each repo terminal himself before triggering; a dirty tree is
  reported honestly in the handoff, never cleaned up. (Per user 2026-08-09,
  replacing the original WIP-commit requirement after Slice A's rejection.)
- Verification is manual (contrived-state runs); there is no test suite for
  skills.

Out of scope:
- Committing, branching, or any git mutation — declined 2026-08-09 ("I'll do
  some cleanup before in each repo terminal shell... if the tree is left
  dirty, that's my fault"). The skill reports state only.
- Secrets scrub of handoff contents — declined 2026-08-09 ("I don't care
  about the secrets getting into the folder... I delete them after a bit").
- Resume-side behavior (reading handoffs, running their negative tests) —
  Tony pastes read lines into new threads himself; declined 2026-08-09.
- Sweep summary/checklist file — declined 2026-08-09 ("I'll drop the handoffs
  back in the proper new threads").
- Stale/superseded-handoff scanning of the folder — declined 2026-08-09
  ("don't check the folder for stale, I'll do that"). Sessions still declare
  supersession of files they themselves know about.
- Archive/delete lifecycle — files stay in place (chosen over archive
  subfolder, 2026-08-09).
- Reaching sessions on the other Anthropic account or bare terminal windows.

## Slice A — solo /shutdown: settle up and write the handoff

Goal: one session, invoked with `/shutdown`, cleans its work state and writes
a correct, complete handoff file — or honestly reports nothing to hand off.

Requirements:
- R1 Verify state before writing; never trust session memory. For each repo
  the session worked in: `git branch --show-current`, `git status`
  (dirty/clean + file list), `git log --oneline -1` (tip hash), `git
  worktree list`, `git stash list`, ahead/behind vs remote — and status run
  inside each listed worktree, not just the main checkout. Verified facts
  go in the file; conflicts with session memory are reported, not papered
  over.
- R2 (revised per user 2026-08-09) Report-only git state: the handoff names
  every dirty file, any in-progress merge/rebase/cherry-pick, any stashes,
  and ahead-of-remote counts — verbatim from Step 1's commands, in every
  checkout including worktrees. The skill never commits, branches, stages,
  or otherwise mutates a repo.
- R3 Fixed handoff template, every file, sections in this order (skip a
  section only when truly empty, and say so): (1) title + date + machine
  ("Mac Studio") + supersedes line naming any earlier handoff this session
  knows it replaces; (2) paste-back line
  `Read ~/Documents/handoffs/<file>.md and follow it.`; (3) authorization
  state — what is signed off, what is NOT authorized, git gates restated;
  (4) where everything lives — repo, branch, tip commit, worktrees, key docs,
  all from R1's verified facts; (5) decisions already made — do not
  relitigate; (6) verified traps / gotchas; (7) background work — any running
  workflows, background tasks, crons, or monitors tied to this session, and
  how to restart them (or "none"); (8) protected paths (added per user
  2026-08-09, "fix the 5, go") — the fixed never-overwrite line naming
  `~/.claude/projects/*/memory/`, `*.jsonl` transcripts, and
  `~/.claude/settings.json`; (9) negative test — 2–3 concrete checks a
  resuming session runs first, ending "if any fail, STOP and report".
  Nine sections total (was eight; amended per user 2026-08-09 — AC-A1's
  count reads accordingly).
- R4 (amended per user 2026-08-09) Filename `YYYY-MM-DD-<topic>-handoff.md`
  with a session-specific topic slug, normalized: lowercase ASCII letters,
  digits, and hyphens only, 60 characters max; never empty — fall back to
  the repo name, then the discussion subject, then `session`. If the name
  already exists in the folder, append `-2` (`-3`, ...) — never overwrite.
  After writing, read the file back to confirm the content is this
  session's; if not (concurrent write), rewrite under the next suffix.
- R5 Removed per user 2026-08-09 (secrets scrub declined — see Out of
  scope).
- R6 Memory pointer: after writing, save an auto-memory note pointing at the
  handoff file, so a fresh session finds it unprompted. A session working in
  a git worktree targets the MAIN checkout's memory directory (worktrees'
  own memory dirs are not loaded by post-restart sessions opened in the main
  repo). If a prior handoff pointer for the same work exists in MEMORY.md,
  update that line rather than adding a second. Re-read MEMORY.md
  immediately before editing it (two same-repo sessions may sweep
  concurrently).
- R7 (amended per user 2026-08-09) Nothing-to-hand-off path: a session with
  no meaningful state (no repo work, no meaningful non-git file work, no
  significant decisions or analysis made in chat — thinking worth resuming
  counts as state, nothing uncommitted, no gates in flight, no background
  work) writes no file and reports
  "nothing to hand off" — in chat when solo, back to the sweep session when
  swept. The swept-reply branch must be reachable from this path, not only
  from the file-written path.

Acceptance criteria:
- AC-A1: In a session with a dirty tree, `/shutdown` produces one file in
  `~/Documents/handoffs/` containing all eight template sections, the dirty
  files named verbatim, and a paste-back line matching the actual filename —
  verify: manual run with a contrived dirty repo; inspect file.
- AC-A2 (revised): After a run against any contrived repo state (dirty,
  mid-merge, detached HEAD), `git status`, the branch tip, and the stash
  list are byte-identical to before the run — verify: capture before/after;
  the skill mutated nothing.
- AC-A3 (revised): A contrived dirty worktree under `.claude/worktrees/` has
  its dirty files named in the handoff — verify: manual run; inspect file.
- AC-A4: In a fresh session with no work state, `/shutdown` writes no file
  and replies "nothing to hand off" — verify: manual run; folder file count
  unchanged.
- AC-A5: When the computed filename already exists, the file is written with
  a `-2` suffix and the paste-back line matches — verify: manual run with a
  pre-planted colliding file.
- AC-A6: After a run, the working directory's MEMORY.md gains one pointer
  line to the new handoff — verify: inspect MEMORY.md before/after.
Footprint: `~/.claude/skills/shutdown/SKILL.md` (new).
Not in this slice: the sweep (`/shutdown all`), messaging other sessions.
Depends on: nothing
Status: signed off

## Slice B — /shutdown all: the sweep

Goal: one invocation triggers every live session on this account to run its
own solo /shutdown, confirms completion, then settles the sweeping session
itself.

Requirements:
- R8 (amended per user 2026-08-09) On `/shutdown all`, call ListAgents;
  SendMessage only rows tagged as live interactive terminal sessions (not
  itself, not Remote Control rows, not subagents; doubtful rows skipped and
  named in the report): run /shutdown, Tony is shutting down, reply with the
  written filename or "nothing to hand off". The sweep is strictly
  per-device: it covers only the machine it runs on ("if I'm on a device and
  run this skill then it's for that device ONLY"); sessions on the other Mac
  must not act.
- R9 Collect replies before declaring done. Sessions mid-tool-call pick the
  message up when they finish — the sweep waits and confirms rather than
  assuming. A session that never replies is reported by name as unconfirmed,
  never marked done.
- R10 The sweeping session runs its own solo /shutdown last.
- R11 (amended per user 2026-08-09) Final chat report lists every target
  with its outcome: filename written, "nothing to hand off", "wrong
  machine", "also sweeping", or UNCONFIRMED — plus any rows skipped in
  doubt. No summary file is written (out of scope).
- R12 If switching Anthropic accounts is the stated reason, the report
  reminds that the sweep covered only this account's sessions.

Acceptance criteria:
- AC-B1: With at least two other live sessions open (one with real state, one
  idle), `/shutdown all` yields a handoff file from the working session, a
  "nothing to hand off" from the idle one, and a final report naming both
  outcomes plus the sweeper's own — verify: manual multi-terminal run.
- AC-B2: The sweeping session's own handoff file exists and its report lists
  it — verify: inspect folder and report.
- AC-B3: With zero other sessions live, `/shutdown all` degrades to a solo
  run and says so — verify: manual run.
Footprint: `~/.claude/skills/shutdown/SKILL.md` (extend).
Not in this slice: reaching non-Claude terminals or the other account.
Depends on: Slice A
Status: signed off

## Build assumptions

### 2026-08-09 — Slice B fix pass
- Interactive-only filter and per-device scope both ratified by Tony and
  amended into R8 — no longer builder calls. (per user)
- Collect deadline set at ~5 minutes via ScheduleWakeup with one full-message
  reminder and one final wake-up — spec named no timeout mechanism; the
  BLOCKER fix required picking one. (builder call)
- Swept-session authority scoped: a sweep message authorizes only this
  skill's read-only settle; wrong-machine and also-sweeping replies added.
  (builder call, implementing the reviewed findings)

### 2026-08-09 — Slice B build
- Broadcast targets narrowed to ListAgents rows marked `interactive` —
  R8 said "every live session"; the listing mixes live terminals with
  hundreds of stale Remote Control rows, and `interactive` is the only
  reading matching the intent ("all open terminals"). Skip-and-name when
  in doubt. (builder call)
- "Reasonable wait" for replies left to the sweeping session's judgment
  with a one-reminder cap — spec named no timeout. (builder call)

### 2026-08-09 — Slice A rebuild (after rejection)
- Spec revised per user before this rebuild: R2 report-only (no git
  mutation ever), R5 secrets scrub removed — both recorded in Constraints /
  Out of scope with Tony's words. (per user)
- Machine name resolved at runtime via `scutil --get ComputerName` rather
  than hardcoded — spec said "state the machine"; runtime lookup is the
  reading that survives a sync to the laptop. (builder call)
- Trigger carve-outs (claude-relay, sunset/server talk) added to the
  description to fix the reviewed collision findings; spec named no
  description wording. (builder call)

### 2026-08-09 — Slice A build
- WIP branch naming fixed as `wip/<topic>-<YYYY-MM-DD>` — spec said "new branch" without a scheme; local, reversible. (builder call)
- Memory pointer notes typed `project` — spec named no type; matches existing handoff-pointer precedent in auto-memory. (builder call)
- AC-A6 exercised against a scratch copy of MEMORY.md rather than the live index, to avoid polluting real memory with a test pointer; mechanics identical. (builder call)

## Deviations

## Discovered

### 2026-08-09 — Slice B build
- ListAgents on this account returns ~606 peer rows, mostly stale Remote
  Control conversations; only `interactive` rows are open terminals. R8's
  "every live session" is unimplementable without a filter.

### 2026-08-09 — Slice A build
- The `sk-` scrub pattern also matches `sk-or-` (substring); harmless since both redact, noted for Slice B doc hygiene.

## Punch list

### 2026-08-09 — review: Slice A
- BLOCKER · SKILL.md:43-45 · "commit everything" has no guard for in-progress merge/rebase/cherry-pick · repo mid-merge with unresolved conflicts: `git add -A && git commit` succeeds, bakes `<<<<<<<` markers into a merge commit and falsely records the merge as completed, destroying the in-progress state the resume needed (reproduced) · Slice A review
- MAJOR · SKILL.md:39-40 · default-branch detection via `origin/HEAD` fails on local-only repos · print-tune/quarters have no remote; one session errors, another decides the rule doesn't apply and commits WIP straight to `main` · Slice A review
- MAJOR · SKILL.md:18,39-46 · detached HEAD unhandled · `git branch --show-current` returns empty; Step 3's only rule is "if on default branch", so the session commits into detached HEAD — orphaned, GC-able commit, empty branch name in the handoff (reproduced) · Slice A review
- MAJOR · SKILL.md:43 · untracked-file handling undefined; can commit secrets into git history · a young repo with an untracked `.env` gets `git add -A`'d into the wip commit; Step 5 scrubs only the handoff file, so the key lands in history · Slice A review
- MAJOR · SKILL.md:83-86 · `sk-` scrub pattern false-positives on ordinary words and the post-write grep is then unsatisfiable · "task-3", "desk-", "risk-" all match; a compliant session redacts the branch names/commands the handoff exists to preserve, or loops on the mandatory clean-grep check (reproduced) · Slice A review
- MAJOR · SKILL.md:21,37 · Step 3 never enters worktrees · `git status` in the main checkout hides a worktree's dirty files; WIP in `.claude/worktrees/` stays uncommitted while the handoff claims the tree was cleaned — Tony explicitly required worktree capture · Slice A review
- MAJOR · SKILL.md:95-100 · memory pointer from a worktree session lands in the worktree's encoded memory dir · a fresh session opened in the main repo dir after restart never loads it, defeating the pointer's purpose; no create-if-missing path for first-use repos either · Slice A review
- MAJOR · SKILL.md:3 · "write a handoff" trigger collides with the claude-relay protocol · "write a handoff for the laptop" routes to this skill, which writes a session-shutdown file to the wrong folder with the wrong template instead of the relay channel · Slice A review
- MAJOR · SKILL.md:29-33 vs 105-107 · swept idle session stops at Step 2 before reaching Step 8's reply-to-sweeper branch · spec R7 requires "nothing to hand off" to go back to the sweep session; as written the sweeper never hears back and marks it unconfirmed · Slice A review
- MAJOR · SKILL.md:90-93 · filename collision check is check-then-write with no atomicity · two same-topic sessions in a concurrent sweep both see the name free and the second write destroys the first handoff · Slice A review
- MAJOR · SKILL.md:83-84 (spec R5 gap) · scrub patterns miss ghp_/github_pat_, AKIA, sk_live_, xoxb-, eyJ (JWT), SSH key blocks · spec's own four patterns cannot meet the spec's absolute no-secrets-in-iCloud constraint; needs Tony's word on the pattern list · Slice A review
- MINOR · SKILL.md:52-54 · empty-section handling ("none" heading) silently narrows the spec's skip-and-say-so option · Slice A review
- MINOR · SKILL.md:40-41 · `wip/<topic>-<date>` branch collision on a second same-day shutdown has no fallback · Slice A review
- MINOR · SKILL.md:18-21 · stashes, ahead-of-origin counts, and dirty submodules invisible to Step 1's commands · Slice A review
- MINOR · SKILL.md:31-33 · non-git work (vault notes, docs) can pass the nothing-to-hand-off gate despite real state · Slice A review
- MINOR · SKILL.md:43 · staged-vs-unstaged boundary flattened into one wip commit · Slice A review
- MINOR · SKILL.md:99-100 · MEMORY.md read-modify-write race narrowed but not closed · Slice A review
- MINOR · SKILL.md:90-91 · topic slug normalization unspecified (spaces, slashes, case) · Slice A review
- MINOR · SKILL.md:84-86 · redaction note can itself trip the post-write grep · Slice A review
- MINOR · SKILL.md:56 · machine name hardcoded as Mac Studio; wrong if skill ever syncs to the laptop · Slice A review
- MINOR · SKILL.md:3 · "shutting down" trigger overlaps sunset-skill and server talk; no negative carve-out · Slice A review
- MINOR · SKILL.md:95-100 · superseded handoffs' memory pointers never retired; contradictory pointers accumulate · Slice A review
- MINOR · SKILL.md:39-44 · absolute never-commit-to-default ignores repo-level CLAUDE.md exceptions (print-tune is direct-to-main) · Slice A review
REBUILT · 2026-08-09 · Slice A — open findings need re-verifying against the new code

### 2026-08-09 — recheck: Slice A
- BLOCKER · SKILL.md:43-45 · (no guard for in-progress merge/rebase/cherry-pick) · fixed — commit capability removed entirely; read-only stated at lines 12-16, in-progress states recorded not touched
- MAJOR · SKILL.md:39-40 · (default-branch detection via `origin/HEAD` fails on local-only repos) · fixed — no default-branch logic remains; no commit path needs it
- MAJOR · SKILL.md:18,39-46 · (detached HEAD unhandled) · fixed — detached HEAD detected and recorded via `git rev-parse HEAD`, current Step 1
- MAJOR · SKILL.md:43 · (untracked-file handling undefined; secrets into history) · fixed — nothing is committed; untracked files named in the handoff only
- MAJOR · SKILL.md:83-86 · (`sk-` scrub false-positives; unsatisfiable post-write grep) · fixed — scrub removed per user spec revision
- MAJOR · SKILL.md:21,37 · (worktrees never entered) · fixed — status now runs inside each listed worktree, current Step 1
- MAJOR · SKILL.md:95-100 · (worktree memory pointer unfindable; no create-if-missing) · fixed — pointer targets main checkout's memory dir; create path added, current Step 5
- MAJOR · SKILL.md:3 · (trigger collides with claude-relay protocol) · fixed — explicit NOT-for carve-outs in description
- MAJOR · SKILL.md:29-33 vs 105-107 · (swept idle session never replies to sweeper) · fixed — Step 2 itself routes the reply to the sweeping session
- MAJOR · SKILL.md:90-93 · (filename check-then-write race) · fixed — read-back-after-write recovery added, current Step 4 (residual window logged as new MINOR below)
- MAJOR · SKILL.md:83-84 · (scrub patterns incomplete vs no-secrets constraint) · fixed — constraint removed from spec per user; no scrub exists
- MINOR · SKILL.md:88-90 · broke: read-back recovery has a losing window — writer that lands first and reads back its own content passes, a later same-name write still destroys it; only second-lander detects the clash · Slice A rebuild
- MINOR · SKILL.md:31 · broke: `git status -sb` shows no ahead/behind on detached HEAD, handoff silently omits the fact · Slice A rebuild

### 2026-08-09 — review: Slice A (rebuilt)
- MAJOR · SKILL.md:22-26 · unborn repo (no commits yet) unhandled in Step 1 · fresh `git init` repo (sunrise starts this way): `git log -1` and `git rev-parse HEAD` both fatal, and `branch --show-current` prints `main` so the detached-HEAD fallback never fires; session aborts or records a fatal-error string as the tip hash · Slice A rebuilt review
- MAJOR · SKILL.md:27-29 · deleted-but-still-listed (prunable) worktree makes Step 1 unexecutable · worktree dir rm -rf'd but not pruned: `git worktree list` still lists it, cd fails, no instruction — and the natural fix (`git worktree prune`) is a mutation the read-only rule doesn't explicitly name · Slice A rebuilt review
- MAJOR · SKILL.md:97-100,105-106 · `<encoded-main-repo-path>` encoding rule never stated; create-if-missing can mkdir a phantom memory dir · a session guesses the encoding wrong (`/` and `.` both become `-`; near-miss siblings already exist in ~/.claude/projects/), creates a directory no future session loads, pointer permanently unfindable — the exact failure R6 exists to prevent (two lenses converged) · Slice A rebuilt review
- MAJOR · SKILL.md:97-101 · pointer routing special-cases worktrees only, not cwd-vs-repo mismatch · session cwd is ~ but the work was in ~/Developer/foo: pointer lands in the home dir's memory, the per-repo session Tony reopens never loads it · Slice A rebuilt review
- MINOR · SKILL.md:22-31 · dirty submodule contents invisible to Step 1 (status shows one pointer line; nothing under ignore=all) · Slice A rebuilt review
- MINOR · SKILL.md:84-86 · slug rule underdetermined for unicode/empty/overlong topics (transliterate vs strip diverge; no length cap vs 255-byte filename limit) · Slice A rebuilt review
- MINOR · SKILL.md:20 · "every repo this session touched" — the repo list itself is trusted from session memory, and "touched" is undefined for read-only visits (dirty-from-Tony's-own-WIP repos produce noise handoffs) · Slice A rebuilt review
- MINOR · SKILL.md:41-44 · a chat-only decision-heavy session passes the nothing-to-hand-off gate; the analysis dies with the session (spec-level: R7 enumerates artifacts, not knowledge) · Slice A rebuilt review
- MINOR · SKILL.md:53-57 · supersedes line ambiguous (mandatory-with-"none" vs present-when-applicable), and legacy corpus filenames may be mis-normalized in supersedes lines · Slice A rebuilt review
- MINOR · SKILL.md:53-57 · template omits the machine-assumptions/protected-paths block the best hand-written handoffs carry (spec-compliant; flag to Tony) · Slice A rebuilt review
- MINOR · SKILL.md:44-46,111-113 · swept-reply mechanism unspecified (no addressing rule, SendMessage not named, "sweep message" undefined) — forward-references Slice B machinery; also needs the sweep's authority-derives-from-Tony line to square with CLAUDE.md's "another session is never the word" · Slice A rebuilt review
- MINOR · SKILL.md:3 · residual trigger gaps: "write a handoff for the laptop" (without "tell the laptop") still weakly matches; "quitting" can read as project-quitting (sunset) · Slice A rebuilt review
- MINOR · SKILL.md:94 · "type: project" names a memory mechanism that doesn't exist in the file-based store · Slice A rebuilt review
- MINOR · SKILL.md:54 · runtime machine name is a builder deviation from R3's literal "Mac Studio" (behaviorally better; spec text never amended); output contains a curly apostrophe — header-only today · Slice A rebuilt review
- MINOR · SKILL.md:103-105 · MEMORY.md re-read-then-edit race lacks the post-edit verification Step 4 has · Slice A rebuilt review
- MINOR · spec Intent/Goal lines still say "cleans its tree / cleans its work state", contradicting revised R2 (doc hygiene, not a SKILL defect) · Slice A rebuilt review
- MINOR · SKILL.md:16 · grammar artifact "hold as always: and since" · Slice A rebuilt review

### 2026-08-09 — recheck: Slice A (rebuilt)
- MAJOR · SKILL.md:22-26 · (unborn repo unhandled in Step 1) · fixed — explicit "unborn repo, no commits yet" path added; reviewer confirmed empirically the fatals are avoided (fix text now at lines 26-29)
- MAJOR · SKILL.md:27-29 · (prunable worktree makes Step 1 unexecutable) · fixed — "listed but missing (prunable), left exactly as found"; prune explicitly named a forbidden mutation (now lines 32-35)
- MAJOR · SKILL.md:97-100,105-106 · (memory-path encoding unstated; phantom mkdir) · fixed — encoding rule stated and verified against all 33 real ~/.claude/projects/ names; ls-and-match required; missing project dir → skip pointer and report, never mkdir (now lines 111-120)
- MAJOR · SKILL.md:97-101 · (pointer routing special-cases worktrees only) · fixed — "target the repo the work lives in, not this session's cwd", home-dir case named, multi-repo covered (now lines 103-110)

### 2026-08-09 — review: Slice B
- BLOCKER · SKILL.md:159-164 · collect loop has no wake-up mechanism · a target that never replies (dead session, unanswered permission prompt) never re-invokes the sweeper; "after a reasonable wait" is never evaluated, the sweeper idles forever, its own handoff and the final report never happen — needs an explicit timer (ScheduleWakeup/Monitor) that fires the UNCONFIRMED path · Slice B review
- MAJOR · SKILL.md:130-134,150-153 · reply addressing contradicts how replies actually work · incoming cross-session messages carry a `from` attribute that IS the reply address; the skill instead has the sweeper hand-type its own name into the template (underivable, typo-able, no [ref] when the sweeper's name is duplicated) — a wrong name makes every settled session report as UNCONFIRMED · Slice B review
- MAJOR · SKILL.md:133-134 vs 165-169 · Step 6's unconditional "then stop" fires before sweep step 4's report · a literal sweeper settles itself and stops; the per-session final report (R11) — the sweep's sole deliverable — never appears · Slice B review
- MAJOR · SKILL.md:143-157 · no machine guard: ListAgents spans both Macs on one account · laptop terminal sessions would be swept, writing handoffs on the wrong machine against Tony's scope ("any open terminal" = this machine's prep); needs a this-machine check in the sweep message · Slice B review
- MAJOR · SKILL.md:138-153 · double-sweep unhandled · /shutdown all run in two sessions: each is an interactive row to the other, each messages the other, and the solo path's "then stop" makes a swept sweeper abandon its own sweep mid-collect — no detection or tie-break rule exists · Slice B review
- MAJOR · SKILL.md:139-141 · sweep authority is only an assertion, and the swept side gets no scope rule · any session can send the magic words and every recipient complies (handoff writes + MEMORY.md edits on an unverifiable peer claim); the swept session needs "a sweep message authorizes ONLY this skill's read-only settle, nothing else" · Slice B review
- MAJOR · SKILL.md:143-149 · interactive-only filter narrows R8 by builder call, and skip-when-in-doubt creates an outcome outside R11's closed set · a live session presenting as a doubtful row is skipped, never messaged, and can never become UNCONFIRMED — needs Tony's word on the filter (question in verdict) · Slice B review
- MINOR · SKILL.md:162-163 · sessions parked at a permission prompt likely never receive the message; predict as UNCONFIRMED rather than implying waiting resolves it · Slice B review
- MINOR · SKILL.md:163-164 · one-reminder cap and target tally have no bookkeeping across turns (compaction loses who replied); "the replies are in" can be read turn-locally and settle early, unrecording a late reply · Slice B review
- MINOR · SKILL.md:164 · reminder content unspecified; a terse reminder without the sender name strands the swept session, which also has no missing-sender fallback · Slice B review
- MINOR · SKILL.md:143-153 · messaging a listed row can resurrect a session whose terminal Tony already closed (send resumes from transcript); headless handoff + memory writes · Slice B review
- MINOR · SKILL.md:147 · subagent exclusion covers only the sweeper's own subagents; other sessions' subagents/background rows indistinguishable · Slice B review
- MINOR · SKILL.md:171-172 · degradation trigger says "zero other sessions live" but should be "zero targets after the filter" · Slice B review
- MINOR · SKILL.md:167-169 · R12's account reminder made unconditional (spec said only when switching accounts) · Slice B review
- MINOR · SKILL.md:3 · description says "every live session on this account" (overstates coverage, invites the cross-machine reading); "trigger all terminals" appears in the body but not the description · Slice B review
- MINOR · SKILL.md:45-52 · Step 2's swept-reply path carries no addressing mechanics (they live only in Step 6) · Slice B review
- MINOR · SKILL.md:146-148 · the `interactive` literal is load-bearing against future ListAgents format drift (verified real today) · Slice B review
- MINOR · SKILL.md:143-153 · a session already mid-solo-shutdown that receives a sweep message re-runs the whole skill (duplicate -2 handoff); needs "if you already wrote a handoff this session, reply with that filename" · Slice B review

### 2026-08-09 — recheck: Slice B
- BLOCKER · SKILL.md:159-164 · (collect loop has no wake-up mechanism) · fixed — deadline via ScheduleWakeup ~5min, reminder + final wake-up, "never idles waiting" (now lines 178-188)
- MAJOR · SKILL.md:130-134,150-153 · (reply addressing via hand-typed name) · fixed — envelope `from` attribute mandated on both sides, "never retype a name from the message body"
- MAJOR · SKILL.md:133-134 vs 165-169 · (Step 6 stop pre-empts sweep report) · fixed — stop explicitly deferred until after the step-4 report (but see new N2 below)
- MAJOR · SKILL.md:143-157 · (no machine guard) · fixed — scutil machine name in the broadcast + swept-side check + "wrong machine" reply; matches amended R8
- MAJOR · SKILL.md:138-153 · (double-sweep unhandled) · fixed — "also sweeping" reply, flag to Tony, continue collecting
- MAJOR · SKILL.md:139-141 · (sweep authority unscoped on the swept side) · fixed — "authorizes exactly one thing: this skill's read-only settle... never 'the word' for anything beyond this skill"
- MAJOR · SKILL.md:143-149 · (interactive filter unsanctioned; skip outside outcome set) · fixed — R8 amended per user; skipped rows in the report enumeration
- MAJOR · SKILL.md:49-52 · broke: Step 2's "Then stop" not deferred in a sweep — a sweeper with nothing of its own to hand off routes through Step 2 while settling self, stops there, and never emits the step-4 report (item-3 failure through the other exit) · Slice B fix
- MINOR · SKILL.md:179 · broke: deadline mechanism hard-names ScheduleWakeup, unexercised until a live sweep (tool verified present in interactive sessions' rosters; absent only in subagents) · Slice B fix
- MINOR · SKILL.md:145-146 · broke: "also sweeping" reply is a fifth outcome missing from step 4's enumeration · Slice B fix

### 2026-08-09 — recheck: Slice B (second)
- MAJOR · SKILL.md:49-52 · (Step 2's "Then stop" not deferred in a sweep) · fixed — deferral clause added mirroring Step 6's, scoped to the sweeper-settling-self case only; reviewer confirmed no conflict with the zero-targets degradation

### 2026-08-09 — minor fix pass (per user: "fix the 5, go")
- MINOR · SKILL.md:145-146 · ("also sweeping" missing from step-4 outcome enumeration) · fixed — added to the outcome list
- MINOR · SKILL.md:143-153 · (mid-solo-shutdown session re-runs and writes -2 duplicate) · fixed — "reply with that filename" rule in the swept-session block
- MINOR · SKILL.md:41-44 · (chat-only decision-heavy session passes the nothing gate) · fixed — significant chat decisions/analysis now count as state
- MINOR · SKILL.md:53-57 · (template lacks protected-paths block) · fixed — new template section 8 (template is now nine sections; spec R3's count superseded by this recorded change)
- MINOR · SKILL.md:84-86 · (slug underdetermined for unicode/empty/overlong) · fixed — ASCII+digits+hyphens, 60-char cap, repo-name fallback

### 2026-08-09 — review: minor fix pass
- MAJOR · SKILL.md:155-156 · already-wrote-a-handoff rule has no freshness condition · handoff written at 2pm, session keeps working, sweep at 6pm replays the stale filename; sweep tallies it as settled, afternoon state silently lost, and the handoff's git facts/negative test no longer match disk — violates the skill's own verify-now principle (three lenses converged) · minor-fix-pass review · charged to Slice B
- MAJOR · SKILL.md:153-159 · swept-session rule order: machine → already-wrote → also-sweeping masks a dual sweep · a sweeper that finished settling itself replies with its filename, never sends "also sweeping", never flags two sweeps to Tony, and may treat the reply as terminal and drop its own step-4 report; also a wrong-machine mid-sweep sweeper reads "do nothing else" as halting its own sweep · minor-fix-pass review · charged to Slice B
- MAJOR · SKILL.md:47-50 vs 99-103,113-121 · chat-only handoffs (newly mandated) can't be served by the slug fallback or the memory pointer · a no-repo session has no repo name to fall back to and no sanctioned pointer target (home-dir memory explicitly forbidden); handoff gets written but nothing leads the next session to it (three lenses converged) · minor-fix-pass review · charged to Slice A
- MAJOR · build-plan R3/AC-A1 (also R4, R7, R11) · spec requirement text never amended for the five per-user fixes · R3 still says eight sections while the skill ships nine; a future signoff grading "all eight template sections" rejects a compliant handoff or invents its own supersession rule — this project's convention amends requirement text in place · minor-fix-pass review · charged to Slice A (doc fix)
- MINOR · SKILL.md:47-50 · "significant decisions/analysis" has no operational test; two sessions diverge on borderline chatter (still strictly better than the pre-fix rule that dropped all chat state) · minor-fix-pass review
- MINOR · SKILL.md:84-86 vs 132-135 · "Never overwrite memory/" needs a carve-out for normal pointer-line updates the skill itself performs · minor-fix-pass review
- MINOR · SKILL.md:99-103 · fallback repo name not guaranteed slug-legal (uppercase/dots); singular "the repo name" with no multi-repo tiebreak; no truncation rule at the 60-char cap; cap-vs-collision-suffix ordering unstated · minor-fix-pass review
- MINOR · SKILL.md:155-156 · "already wrote a handoff this session" doubled wording; broad vs narrow reading diverges · minor-fix-pass review
- MINOR · SKILL.md:204-207 · no outcome bucket for a swept session whose settle fails mid-run (disk error) — lands as misleading UNCONFIRMED; filename reply can't distinguish fresh settle from stale replay, and "settled, no pointer" never reaches the sweep report · minor-fix-pass review

### 2026-08-09 — recheck: minor fix pass
- MAJOR · SKILL.md:155-156 · (already-wrote rule lacks freshness condition) · fixed — "AND has done no work since... Any work since makes it stale — settle again fresh" (now rule 3 of the ordered list)
- MAJOR · SKILL.md:153-159 · (rule order masks dual sweep; "do nothing else" halts own work) · fixed — explicit first-match-wins list, also-sweeping first, wrong-machine now "ignore the sweep message; changes nothing else" (but see new N1 below)
- MAJOR · SKILL.md:47-50 vs 99-103,113-121 · (chat-only handoffs unslugable and unpointable) · fixed — fallback chain repo → subject → `session`; no-repo pointer targets the session's own cwd memory
- MAJOR · build-plan R3/AC-A1/R4/R7/R11 · (spec text never amended) · fixed — all four requirements carry "amended per user 2026-08-09" text matching the skill section-for-section (residual: AC-A1's literal count, N3 below)
- MAJOR · SKILL.md:197 · broke: the sweep BROADCAST template still says "reply 'wrong machine' and do nothing else" — the fixed rule list says ignore-and-continue, but a wrong-machine session reads the message first and may halt its own in-progress work on the message's literal instruction · minor-fix-pass fix
- MINOR · SKILL.md:162-166 · broke: also-sweeping fires before the machine check, so two legitimate per-device sweeps (Studio + laptop) false-alarm each other as dual sweeps instead of answering "wrong machine" · minor-fix-pass fix
- MINOR · build-plan:111 · broke: AC-A1's literal text still grades "all eight template sections"; the amendment lives only in R3's parenthetical · minor-fix-pass fix

### 2026-08-09 — recheck: minor fix pass (second)
- MAJOR · SKILL.md:197 · (broadcast template's "do nothing else" halts a wrong-machine session's own work) · fixed — template now reads "ignore this message — it changes nothing about your own work"; grep confirms "do nothing else" is gone from the file, and the full-message reminder path carries the corrected wording
