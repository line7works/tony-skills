# sun-live-run-fixes-2 — build plan (2026-09-05)

Intent: Second round of live-run fixes for the `sun` plugin, one slice per skill file so each PR touches one skill. Slice A fixes `/sunset` from its 2026-09-05 live run on the throwaway project Banana Dunk (cache `75b836b0c1ff`, byte-identical to `main`'s sunset file): Phase 2 pre-creates `~/Developer/_archive/<Name>/.claude-memory`, so Phase 4's `mv` finds the destination already a directory and nests the repo inside it (`_archive/Banana-Dunk/Banana-Dunk/`); and Phase 6's token fallback stops and hands Tony a curl when `$VERCEL_TOKEN` is unset, although the logged-in CLI's token at `~/Library/Application Support/com.vercel.cli/auth.json` worked in the live run. Slice B carries two `/sunrise` follow-ups from the Slice A signoff of `docs/plans/2026-09-05-sunrise-live-run-fixes.md`: nothing after Phase 2 commits or pushes, so the post-link `.gitignore` re-assert (and the Electron placeholder files) stay uncommitted while Phase 8 prints "pushed"; and a real project name, `Banana-Dunk`, sits at line 231 of a public skill. For Tony, so a sunset lands the repo where the tombstone says it is and pauses Vercel without a hand step, and so a sunrise ends with the tree it claims to have pushed. Source of every requirement: the four 2026-09-05 Inbox notes in `docs/feedback.md` tagged `sunset live run (Banana Dunk) · sunset` (A, B) and `sunrise live run follow-up (Banana Dunk) · sunrise` (F, G), plus the current text of the two skill files.

Constraints:
- Stack: two Markdown files, `plugins/sun/skills/sunset/SKILL.md` (312 lines on `main` at e706492) and `plugins/sun/skills/sunrise/SKILL.md` (543 lines). No code, no test runner. Verification is mechanical (`grep`, `awk`, `git diff --name-only`) plus one fresh-session read per slice.
- Fresh-session reads are plain `claude -p` from the repo root told to read the file at its checkout path, never `--plugin-dir` (it loads the branch copy beside the installed one; `docs/evidence/agent-file-flip/slice-a-requirement-map.md`). The installed-cache read happens only after merge and Tony's reinstall.
- Source of truth: a change here reaches a session only after it lands on `main` AND Tony runs `/plugin update sun@tony-skills`. Nothing in either slice may assume the running skills have changed.
- The two slices are independent and each is its own PR. Both touch `docs/feedback.md` (one Dispositions line each) and this plan's ledger, so whichever ships second branches from `main` after the first has merged; its build preflight checks that.
- Ordering is the whole fix for finding A (orchestrator's scratch reproduction, 2026-09-05): `mkdir -p _archive/Name/.claude-memory` then `mv Developer/Name _archive/Name` nests; `mv Developer/Name _archive/` with the memory dir pre-made fails "Directory not empty"; move first, then `mkdir -p`, is clean. So the repo must move before anything creates `~/Developer/_archive/<Name>`, and Phase 4 refuses to `mv` when that path already exists.
- The Vercel token is a credential. The skill may read `~/Library/Application Support/com.vercel.cli/auth.json` (JSON, key `token`) into a shell variable for the `Authorization` header only; it never echoes the value, never writes it into the tombstone or any file. This build never reads that file's values either; `ls` is the most it does.
- Sunrise's Phase 2 already pushes `main` of the brand-new repo (`gh repo create … --push`); the Slice B pre-flight commit-and-push is the same first-day push, not a violation of the feature-branch rule that applies once the repo is live. The Phase 8 kit check stays exactly the four lines mirroring the vault kit note; the pre-flight is its own step before them.
- Git gate: feature branch per slice, local commits fine, stop before `git push` and `gh pr create`; Tony says "PR" then "merge" in the terminal for each slice.
- Repo invariants (repo `CLAUDE.md`): public repo, nothing Tony-specific by default; `${CLAUDE_PLUGIN_ROOT}` asset references untouched; `sun` keeps both skills.
- Evidence files follow the brief's paths exactly: Slice A at `docs/evidence/sunset-live-run-fixes/fresh-session-read.md`, Slice B at `docs/evidence/sun-live-run-fixes-2/fresh-session-read-sunrise.md` (question, whole answer, checkout commit read; pattern from `docs/evidence/sunrise-live-run-fixes/fresh-session-read.md`).

Out of scope:
- Finding C from the sunset run (Phase 0 resolution matched sunrise's list; `.vercel/project.json` held the right id) — reason: not a defect (test session and orchestrator, 2026-09-05).
- `~/ObsidianVault/.obsidian/workspace.json` still naming `03-projects/banana-dunk` — reason: Obsidian's own UI state, not a note; the vault sweep is right to ignore it (orchestrator, 2026-09-05).
- Sunset's Phase 8 (Notion) and Phase 9 (closeout) text beyond the one conditional wording Slice A's R3 needs — reason: brief item 5.
- Sunset's by-name Vercel lookup naming no `<Name>`/`<slug>` variant, and its `project_<slug>.md` vs sunrise's `project_<slug_>.md` — reason: recorded as Deferred in the sunrise Slice A verdict; no live-run finding names them; a later note can.
- Sunrise's Phase 8 `<project>.vercel.app` alias placeholders (`:84`, `:312`) and the pre-existing "Phase 2 git-connect" cross-reference at `:312` — reason: Deferred and MINOR in the sunrise Slice A verdict; not in the four notes.
- Finding E (vault path in the seeded `AGENTS.md`) — reason: still pending Tony's ruling.
- The `Banana Dunk` mentions in `docs/feedback.md`, `docs/plans/`, `docs/reviews/`, and `docs/evidence/` — reason: those are records of the live runs; finding G names only the instruction text at sunrise `:231`.
- Installed-cache fresh reads and live `/sunset` or `/sunrise` reruns — reason: post-merge, after Tony's reinstall; a live run creates or archives real infrastructure and is Tony's call.
- Bumping a plugin version or the marketplace catalog — reason: no version field; the cache is keyed by commit.

## Slice A — sunset live-run fixes
Goal: `/sunset` moves the repo to `~/Developer/_archive/<Name>` as a rename, never nested, and pauses Vercel with the logged-in CLI's token when `$VERCEL_TOKEN` is unset, with no hand step at either point.
Requirements:
- R1: Phase 4 gains a guard step before the `mv`: if `~/Developer/_archive/<Name>` already exists (a prior sunset or a name collision), STOP and report exactly what is there; never `mv` onto an existing path. (finding A)
- R2: The project-memory-store copy (today Phase 2 step 2's `mkdir -p ~/Developer/_archive/<Name>/.claude-memory`, `cp -R`, and the confirm-and-record line) moves into Phase 4 as steps after the `mv`, copying into the moved repo, so nothing creates `~/Developer/_archive/<Name>` before the repo arrives. Phase 2 step 2 keeps its explanation of why the store would be orphaned and points forward to Phase 4 for the copy. Phase 4's intro sentence ("and after Phase 2 copied the project memory store") is rewritten to match. The Phase 0 preview's Memory line and the tombstone's project-store line (`_archive/<Name>/.claude-memory/`) stay true and stay put. (finding A)
- R3: Under `--keep-local` the repo does not move, so its store is not orphaned: the copy is skipped, and the Phase 9 summary's Memory line and the tombstone's project-store line say the store was left in place because the repo was kept local. Blueprint decision (orchestrator's pick; small and reversible; flagged in the read-back for Tony to flip). (finding A, brief item 2)
- R4: Phase 6 step 2 reads the token from `$VERCEL_TOKEN`, else from `~/Library/Application Support/com.vercel.cli/auth.json` (key `token`), into a shell variable used only in the `Authorization` header; step 3's stop-and-hand-Tony-a-curl applies only when both are absent; one sentence forbids echoing the token or writing it into the tombstone or any file. (finding B)
- R5: `docs/feedback.md` gains one line under the real `## Dispositions` heading, dated 2026-09-05, naming the two sunset notes (A, B) and pointing at Slice A of this plan. Additive only; no Inbox line edited, reordered, or removed. (the file's Flow line; precedent lines)
- R6: Nothing else changes: not `sunrise/SKILL.md`, not any other plugin, not sunset's Phase 8, and Phase 9 only as R3 requires.
Acceptance criteria:
- AC1: The repo moves before the memory dir is created — verify: `S=plugins/sun/skills/sunset/SKILL.md; grep -c 'mkdir -p ~/Developer/_archive/<Name>/.claude-memory' $S` prints `1`; `grep -c 'mv ~/Developer/<Name> ~/Developer/_archive/<Name>' $S` prints `1`; the `mkdir` line number is greater than the `mv` line number; both lines fall inside the Phase 4 region (`awk '/^## Phase 4/{f=1} /^## Phase 5/{f=0} f' $S` contains both).
- AC2: The guard exists and precedes the `mv` — verify: within the Phase 4 region, a line matching `_archive/<Name>` together with `STOP` (case-sensitive) has a smaller line number than the `mv` line.
- AC3: Phase 2 no longer performs the copy — verify: `awk '/^## Phase 2/{f=1} /^## Phase 3/{f=0} f' $S | grep -c 'mkdir -p\|cp -R'` prints `0` and `… | grep -c 'Phase 4'` prints `1` or more.
- AC4: The keep-local rule is stated — verify: `awk '/^## Phase 2/{f=1} /^## Phase 5/{f=0} f' $S | grep -c 'keep-local'` prints `1` or more (was `1`, the Phase 4 heading, so `2` or more after), and the tombstone template region (`awk '/^## Tombstone template/{f=1} f'`) contains `keep-local`.
- AC5: The token fallback is named once and guarded — verify: `grep -c 'auth.json' $S` prints `1`; the hit is inside the Phase 6 region; the Phase 6 region still contains `VERCEL_TOKEN`; `awk '/^## Phase 6/{f=1} /^## Phase 7/{f=0} f' $S | grep -ci 'never echo\|never print\|do not echo\|do not print'` prints `1` or more; the Phase 6 region contains `both` on the stop line (the stop applies only when both sources are absent).
- AC6: Footprint closed — verify: `grep -c timeout $S` prints `0`; `git diff --name-only main...HEAD` lists only `plugins/sun/skills/sunset/SKILL.md`, `docs/feedback.md`, `docs/plans/2026-09-05-sun-live-run-fixes-2.md`, and `docs/evidence/sunset-live-run-fixes/fresh-session-read.md`; `git diff main...HEAD -- plugins/sun/skills/sunrise/SKILL.md` is empty.
- AC7: A fresh session reads the edited text and describes the fixes — verify: manual: plain `claude -p` from the repo root, no `--plugin-dir`, prompt names `plugins/sun/skills/sunset/SKILL.md`, says "do not run it and do not edit any file", asks in what order Phase 4 moves the repo and copies the memory store, what happens if `~/Developer/_archive/<Name>` already exists, what happens to the copy under `--keep-local`, and where Phase 6 gets its token when `$VERCEL_TOKEN` is unset and what it must never do with it; the answer names move-then-copy, the STOP on an existing path, the skip under `--keep-local`, the `auth.json` path with key `token`, and the no-echo/no-persist rule. Question, whole answer, and the commit read recorded at `docs/evidence/sunset-live-run-fixes/fresh-session-read.md`.
- AC8: The disposition landed and the Inbox is intact — verify: `awk '/^## Dispositions$/{f=1;next} f && /^- 2026-09-05/' docs/feedback.md | wc -l` prints one more than on `main` at build start (2 if Slice A ships first), and `awk '/^## Inbox$/{f=1;next} /^## Dispositions$/{f=0} f && /^- /' docs/feedback.md | wc -l` still prints `35`.
Footprint: `plugins/sun/skills/sunset/SKILL.md` (Phase 2 step 2, Phase 4 intro and steps, Phase 6 steps 2 and 3, Phase 9 summary Memory line and tombstone project-store line for R3); `docs/feedback.md` (one Dispositions line); `docs/evidence/sunset-live-run-fixes/fresh-session-read.md` (new); this plan's ledger.
Not in this slice: anything in `sunrise/SKILL.md` (Slice B); sunset's Notion phase; the by-name Vercel lookup variant; a live `/sunset` rerun.
Depends on: nothing
Status: built

## Slice B — sunrise follow-ups
Goal: `/sunrise` ends with every working-tree edit committed and pushed before it claims "pushed", and its instruction text names no real project.
Requirements:
- R1: Phase 8 gains a pre-flight step before step 1's deploy check: `git status --porcelain` must be empty; otherwise the skill stages and commits the remaining changes with a named message and pushes. Only after this passes may the summary line print "(git init, pushed)". The kit check's four lines stay exactly as they are; the pre-flight is a separate step. Phase 3 step 2 gains one clause saying the `.gitignore` change is committed by Phase 8's pre-flight, so the two sites read as one rule. (finding F)
- R2: Line 231's `Banana-Dunk` becomes a generic mixed-case example such as `My-App`; the date and the HTTP 400 stay. (finding G; Tony's word relayed 2026-09-05 and confirmed in the sunrise PR #43 ship report)
- R3: `docs/feedback.md` gains one line under the real `## Dispositions` heading, dated 2026-09-05, naming the two sunrise follow-up notes (F, G) and pointing at Slice B of this plan. Additive only. (the file's Flow line; precedent lines)
- R4: Nothing else changes: not `sunset/SKILL.md`, not any other plugin, not the kit check, not the alias placeholders.
Acceptance criteria:
- AC1: The real name is gone, the example stays — verify: `R=plugins/sun/skills/sunrise/SKILL.md; grep -c 'Banana-Dunk' $R` prints `0`; `awk '/^## Phase 3/{f=1} /^## Phase 4/{f=0} f' $R | grep -c 'HTTP 400'` prints `1`; the same region still contains `2026-09-05`.
- AC2: The pre-flight exists in Phase 8 — verify: `awk '/^## Phase 8/{f=1} /^## Templates/{f=0} f' $R | grep -c 'git status --porcelain'` prints `1`; `awk '/^## Phase 8/{f=1} /^## Templates/{f=0} f' $R | grep -c 'commit.*push\|push.*commit'` prints `1` or more; the `git status --porcelain` line number is smaller than the line number of the `SUNRISE COMPLETE` summary block; the Phase 3 region contains `Phase 8`.
- AC3: The kit check is unchanged — verify: `awk '/^## Phase 8/{f=1} /^## Templates/{f=0} f' $R | grep -c 'git ls-files\|head -1 CLAUDE.md\|! -L CLAUDE.md\|claude -p'` prints `4`, same as on `main`.
- AC4: Footprint closed — verify: `grep -c timeout $R` prints `0`; `git diff --name-only main...HEAD` lists only `plugins/sun/skills/sunrise/SKILL.md`, `docs/feedback.md`, `docs/plans/2026-09-05-sun-live-run-fixes-2.md`, and `docs/evidence/sun-live-run-fixes-2/fresh-session-read-sunrise.md`; `git diff main...HEAD -- plugins/sun/skills/sunset/SKILL.md` is empty.
- AC5: A fresh session reads the edited text — verify: manual: plain `claude -p` from the repo root, no `--plugin-dir`, prompt names `plugins/sun/skills/sunrise/SKILL.md`, says "do not run it and do not edit any file", asks what Phase 8 does before proving the deploy is live when the working tree is dirty, and what example directory name Phase 3 step 1 cites as rejected by Vercel; the answer names the `git status --porcelain` check with commit-and-push, and cites the generic example, not a real project. Recorded at `docs/evidence/sun-live-run-fixes-2/fresh-session-read-sunrise.md`.
- AC6: The disposition landed and the Inbox is intact — verify: `awk '/^## Dispositions$/{f=1;next} f && /^- 2026-09-05/' docs/feedback.md | wc -l` prints one more than on `main` at build start, and the Inbox count still prints `35`.
Footprint: `plugins/sun/skills/sunrise/SKILL.md` (Phase 3 step 1 example name, Phase 3 step 2 pointer clause, Phase 8 new pre-flight step); `docs/feedback.md` (one Dispositions line); `docs/evidence/sun-live-run-fixes-2/fresh-session-read-sunrise.md` (new); this plan's ledger.
Not in this slice: anything in `sunset/SKILL.md` (Slice A); the `<project>` alias placeholders; the "Phase 2 git-connect" cross-reference; finding E.
Depends on: nothing
Status: not started

## Build assumptions

### 2026-09-05 — build: Slice A
- AC8 Inbox count read as 36, not 35 · builder call · the 35 was the blueprint-time baseline; Tony's `/fb` of the handoff SKILL NOTE (checkpointed as 11c0433 before this build) made it 36 at build start; the intact test is "unchanged from build start", so 36 is the number the criterion's intent pins
- Phase 6 token read uses `jq -r .token` · builder call · `jq` 1.7.1 is at `/usr/bin/jq` on macOS 26; the path is named on that one command line so AC5's `auth.json` count stays 1 (the prose says "the logged-in CLI's credentials file" and names the key)
- Phase 4 heading kept as "Local repo (skip if --keep-local)" · builder call · R2 does not rename it; the memory copy now lives under it as step 4 and the heading's skip clause is what makes R3's skip true
- Terminal-shortcut steps renumbered 3-6 to 5-8 · builder call · consequence of R1/R2 inserting the guard and the copy as Phase 4 steps 2 and 4

## Deviations

## Discovered

### 2026-09-05 — build: Slice A
- The Phase 0 preview's Memory line (`archive project store ... -> _archive/<Name>/.claude-memory/`) prints unconditionally, so under `--keep-local` the preview promises a copy Phase 4 no longer makes; R2 says the preview line stays put, so not touched · a one-line note for a later slice

## Handoffs

### 2026-09-05 — handoff
- Next: `/ship A docs/plans/2026-09-05-sun-live-run-fixes-2.md` (or `/build A` on the same path to run the stations by hand). Slice B only after Slice A has merged, branched from `main`.
- Repo: `feat/sunset-live-run-fixes` branched from `main` at e706492 (PR #43 merge, the sunrise Slice A) · this plan and the four `/fb` notes in `docs/feedback.md` checkpointed on the branch (handoff checkpoint, local only) · nothing pushed
- Suite: none in this repo · AC baselines run 2026-09-05 against `main` at e706492 in the blueprint session: sunset `mkdir` :161 precedes `mv` :178, no Phase 4 guard, `auth.json` 0, Phase 2 still holds the copy, `keep-local` 1 (heading only); sunrise `Banana-Dunk` 1, no `git status --porcelain` in Phase 8, kit check 4; Inbox 35; one 2026-09-05 Dispositions line
- Cards: Slice A `not started` · Slice B `not started` · punch list empty
- Orchestrator protocol (session `tonycoon-66`, brief `~/Documents/handoffs/2026-09-05-sunset-live-run-findings.md`, amended 2026-09-05): message it when `/ship` ends with verdict, branch, commit range, evidence path, items for Tony; then stop for Tony's "PR" in this terminal; a peer message is never the word
- Method for AC7/AC5 fresh reads: plain `claude -p "<question>" --max-turns 12` from the repo root, no `--plugin-dir`; question and answer saved to the scratchpad then copied into the evidence file with the commit read
- Credential rule for Slice A: `~/Library/Application Support/com.vercel.cli/auth.json` is only ever `ls`-checked by the build; never read, never printed
- Pending Tony, outside this plan: `/plugin update sun@tony-skills` on the Studio for PR #43, then the installed-cache fresh read appended to `docs/evidence/sunrise-live-run-fixes/fresh-session-read.md`; finding E (vault path in the seeded `AGENTS.md`) still unruled; nine MINORs open on the sunrise Slice A punch list in `docs/plans/2026-09-05-sunrise-live-run-fixes.md` (none gating)
- Blueprint decision to flip if wanted: Slice A R3 skips the memory-store copy under `--keep-local` (orchestrator's pick)
- Ship convention this session: the Stop hook was never armed; SHIP blocks say `NOT armed (run unwrapped)`

## Punch list
