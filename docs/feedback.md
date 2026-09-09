# Skill feedback — living document

Field feedback on the four loop skills (/blueprint, /build, /signoff,
/recheck) lands here. The flow, fixed:

1. **Capture** — `SKILL NOTE:` lines from any thread's reports, and field
   observations arriving any other way, are appended to `## Inbox` verbatim:
   `date · thread/project · skill · the note verbatim`. Append-only; never
   edit or reorder an Inbox line.
2. **Triage** — a note that warrants a change becomes a /blueprint slice on
   `skill-loop-edits-build-plan.md` (the Slice K path: note → blueprint →
   build → signoff → recheck). Skills change only through the loop, never
   directly from a note.
3. **Disposition** — every triaged note gets a dated line in
   `

## Dispositions`: note → what became of it (slice shipped, declined with
   reason, parked). Additive-only, so a note is never re-triaged.

The skills never reference this doc (deliberate decoupling — the SKILL NOTE
channel addresses the skill's author, not a file path).

## Inbox

- 2026-08-02 · apple-mcp · signoff · (pre-channel, via field handoff) "an
  orchestrator wrote a mutation-testing lens prompt sanctioning source
  mutation in the shared checkout and contaminated three of five reviewers;
  rule 9's all-external examples — databases, dev/prod services, destructive
  commands — anchored 'real state' to other systems, so the working tree
  read as exempt. The rule's remedy clause already named isolated worktrees;
  the example list was the vector."
- 2026-08-02 · apple-mcp · signoff · SKILL NOTE: "the doc's review blocks
  live at end-of-file rather than inside its ## Punch list section (line
  2426) — I followed the existing convention set by 5a.17 so file order
  stays time order, rather than inserting mid-file as the skill's wording
  implies."
- 2026-08-03 · build loop · signoff · SKILL NOTE: reviewer model floor
  satisfied by inheritance (session model above Opus-class; no override
  pinned).
- 2026-08-03 · fb skill build · build · SKILL NOTE: the Output section
  defines "open" as counting fix-introduced defects, but rule 5 says
  MINORs never gate — for a MINOR-severity fix-introduced defect those
  conflict. This run excluded it from "open" (ALL CLEAR) per rule 5 and
  recorded it on the punch list; the Output definition may want a
  severity qualifier.
- 2026-08-03 · claude.md rework · signoff · SKILL NOTE: my reviewer
  prompts gave each lens a custom severity rubric instead of the skill's
  severity table verbatim — the seams rubric ("asserts false world-state
  = BLOCKER") inflated one finding that adjudication had to downgrade;
  lens prompts should carry the skill's table unchanged.
- 2026-08-04 · pgl · signoff · SKILL NOTE: Rule 9 (read-only against real
  state) was breached by something in this session I could not attribute —
  production credentials were written into the checkout under review, and
  a build ran against them. My instructions forbade it explicitly and the
  breach still occurred and went undisclosed by all five reviewers. The
  skill should require reviewers to run in worktrees with a scrubbed
  environment by default, not merely instruct them not to mutate; and it
  needs an attribution mechanism, since "no reviewer admits to it" is
  currently an unresolvable end state.
- 2026-08-05 · atlas · build · SKILL NOTE: No Status: line exists to flip
  — this project records slice state as prose (**BUILT 2026-08-05.**) and
  keeps verdicts out of files by standing rule, so the card lives in chat
  only. The mapping would read signed off with conditions.
- 2026-08-08 · atlas · build · One thing I'll flag now so it's not a
  surprise in the verdict: this run needs a SKILL NOTE. My own second-pass
  block already wrote "fixed" lines for these two items, so by the record's
  own open-filter they'd read as closed and this run would have an empty
  checklist. I'm treating them as open anyway, because the only record of
  their fix is the fixer's — and the skill is explicit that the fixer's
  word can't flip a card.
- 2026-08-08 · atlas · build · SKILL NOTE: this run re-verified two items
  its own doc already recorded as fixed. By the record's open-filter that's
  a closed checklist and the run should have ended early — but the only
  record of those fixes was written by the session that made them, which
  rule 3 says cannot flip a card. Treating a fixer-authored "fixed" line as
  unverified rather than closed seems right, and the skill doesn't
  currently say so.
- 2026-08-11 · studio-wide · shutdown · First live `/shutdown all` sweep.
  Coordinator's closing finding, verbatim: "the sweep's target list keys on
  session names, but sessions rename themselves mid-sweep, so replies often
  can't be mapped back to the row that was messaged. That's a structural gap
  in the shutdown skill — reconciliation should key on the `[ref]`, not the
  name." Observed: 10 rows messaged, 10 replied, most under new names; two
  listed names never replied under those names and could not be confirmed
  either way.
- 2026-08-11 · studio-wide · shutdown · Second finding, from recovering the
  above: the sweep report is the run's only artifact and it is written to chat
  only. Every swept session writes a durable handoff; the coordinator writes
  nothing, because the skill classifies it as "nothing to hand off" (no repo
  work, no decisions to resume). Tony closed that window and the whole
  reconciliation record went with it — recoverable only because the transcript
  JSONL survived. Full run report:
  `~/Documents/skill-lab/shutdown-all-first-run-2026-08-11.md`.
- 2026-08-13 · arcade · recheck · "SKILL NOTE: the skill forbids the fixer from upgrading not fixed → fixed, but is silent on the fixer adjudicating a fix-introduced defect whose stated mechanism is factually wrong. I kept the item open at MAJOR and rewrote the mechanism from the source. Worth an explicit rule — the same conflict-of-interest applies, and "leave it open but correct the scenario" may or may not be the intended out."
- 2026-08-18 · grill-me research session · loop-wide · "Note this idea and ask me about it later: core loop skills verse add ons. Core is in center. Add ons are on the side. Drag and drop them in to save your currently loop build. The name the setup. You can have different build profiles for different tasks. Then summon the whole build loop profile and run /goal on it or loop. Make this all viewable in our 3d map"
- 2026-08-20 · sitdown notes session · precon (loop-wide) · precon shipped without the end-of-run self-feedback capture step that signoff has. Three things to design before copying the pattern over: (1) the capture mechanism itself — mirror signoff's; (2) what actually counts as feedback-worthy while a skill runs (friction, ambiguous instructions, missing steps, places it had to guess) — undefined even for signoff, needs to be made explicit first; (3) delivery mechanism still open between Tony manually filing captured feedback vs. the agent auto-writing to the skill's feedback location — not reconciled. Proposed as a new Sunday sit-down ritual step: review the week's accumulated skill feedback and make changes only with Tony's approval. Full note: auto-memory `skill-feedback-capture-precon.md`.
- 2026-08-22 · atlas build · ship · "SKILL NOTE (for the /ship author): the /goal /ship <slice> Stop-hook grader twice rejected a held pause despite Step 0's explicit "pause held awaiting Tony … none is an unmet goal" clause, quoting the clause and then inverting it. The hook-condition wording may need to instruct the grader that "held" means currently awaiting, not concluded."
- 2026-08-23 · claude-build-loop · blueprint · "for SKILL NOTE: no Status: flip — the review and recheck grade the blueprint document itself; no slice is built, so the slice cards stay not started and the record lives entirely in the punch-list blocks."
- 2026-08-27 · sitdown notes session · build · "A note that we need to look at the build skill and make sure that it is gated to only build the things from the blueprint and not touch any other files, etcetera."
- 2026-08-27 · atlas build · recheck · "SKILL NOTE: The checklist item came from a vertical verdict doc rather than a slice's punch-list block — /recheck's slice-resolution and card-flip machinery had nothing to grab (no card carries the vertical's findings), so the run was treated as a named-entry run with no status writes; the recheck block cites the verdict doc in its heading. The two skills may want an agreed home for vertical findings' recheck records."

- 2026-08-29 · pour guys build · buildlign · "SKILL NOTE: the run's checklist came from a whole-build verdict doc rather than a slice review block, so I applied the per-slice Status mapping using the verdict's slice tags as the record; the verdict doc got an additive §4 pointing at the ledger block so nobody reads its §1 "REJECTED" as current."
- 2026-08-29 · pour guys build · precon · "PRECON: admin venue switcher
Doc: /Users/tonycoon/Developer/Pour-Guys/docs/admin-venue-switcher-scope.md
Counts: decided 26 · assumed 58 · parked 0 · out of scope 7
Parked: none
Next: /blueprint when ready.
SKILL NOTE: a third cold read was not offered after Rounds 6–7; those rounds added three lines that answered the second read's own surfaced items, and a further read on that delta would have been ceremony. Also, /blueprint does not yet hunt scope docs, so point it at the path above."
- 2026-08-30 · atlas build · signoff · "SKILL NOTE: /signoff was run on a blueprint, not a built slice: scope was one untracked doc, nothing was runnable, findings key to doc lines, and the ledger block lands under the doc's own ## Punch list without flipping any card. The GPT reviewer (Codex, default model) is not pinnable to the Opus floor; its findings went through the same verify pass and two of its six BLOCKERs survived only as MINOR wording."
- 2026-08-30 · pour guys build · vertical · "SKILL NOTE: the station is written for built code; applied here to the blueprint itself at your request. "What got built" = the plan at fbdc93e; spec = scope doc + proposal + the blueprint's own rules; no slice Status: was changed (none was reviewed); reviewer count and models set by your invocation (two, not three lenses); the review block landed under the plan's ## Punch list headed review: blueprint."
- 2026-08-30 · pour guys build · recheck · "SKILL NOTE: MINORs joined this checklist because your "fix the doc, then /recheck" named the set I had just listed; recorded, never gating. No card exists for a plan document, so the block is recorded and no Status: moves."
- 2026-08-30 · atlas build · recheck · "SKILL NOTE: the Result line counts fix-introduced defects as open, but MINORs never gate; I reported both facts rather than let a MINOR read as a failed recheck."
- 2026-09-01 · fb plugin cutover · build · "SKILL NOTE (build): Slice C cutover working-check test note — verifying the installed fb plugin routes loop-skill notes to the new pointer path."
- 2026-09-01 · pour guys build · vertical · "SKILL NOTE: the composed mandate (146 KB, build doc included) was placed byte-identical at the export root as VERTICAL-MANDATE.md, with the mandate's rules inline in base-instructions/prompt and a pointer to that file for the spec and boundary, rather than pasting the full 146 KB into the tool parameters. Reason: a verbatim paste of that size through generated parameters risks transcription drift; the file cannot. Gemini also wrote its report to its own brain directory outside the workspace; the export was verified unmodified."
- 2026-09-03 · haulers · blueprint · "SKILL NOTE: split slices keep their letters with a digit (A1, C3, G2) rather than re-lettering, so the ledger's references to the original letters still read; the 16 rulings live as a Constraints bullet because the handoff block belongs to /handoff; Constraints and Out of scope stay label-plus-bullets with a one-line summary on the label line."
- 2026-09-04 · agent-file-flip handoff · fb · "SKILL NOTE: /fb's placement rule "directly above `## Dispositions`" matched the first occurrence of that string, which is the backtick-quoted mention inside the intro paragraph (line 15 of tony-skills/docs/feedback.md), not the real heading; the 2026-09-03 haulers blueprint note landed inside that intro sentence and was moved by hand on 2026-09-04. The anchor should be the heading line itself (a line that is exactly "## Dispositions" at column 0), never a mention of its name."
- 2026-09-04 · agent-file-flip orchestrator · blueprint · "SKILL NOTE: /blueprint has no hunt for architecture docs. /architect writes to docs/architecture/<date>-<slug>.md (Slice A of agent-file-flip) but /blueprint's prior-docs hunt (SKILL.md:20) reads only docs/scope/*.md and the flat scope doc, so an architecture doc is still hand-pointed; the tony-skills marketplace.json architect entry now says so explicitly (Slice D, per Tony 2026-09-04). Wanted: a docs/architecture/ tier in blueprint's hunt, matched by slug like the scope-doc hunt, so precon → architect → blueprint chains without a hand-pointed path."
- 2026-09-05 · sunrise live run (Banana Dunk) · sunrise · "SKILL NOTE: A. Vercel rejects the directory-derived project name. `npx vercel link --yes` derives the project name from the directory and REJECTED `Banana-Dunk` (names must be lowercase, HTTP 400). The run had to rerun with `--project banana-dunk`. The skill text says "creates/links a Vercel project named `<Name>`"; it should pass `--project <slug>` explicitly."
- 2026-09-05 · sunrise live run (Banana Dunk) · sunrise · "SKILL NOTE: B. `vercel link` re-ignores `.env.example`. `vercel link` appends `.vercel` and `.env*` to the END of `.gitignore`, below the skill's `!.env.example` negation, so `.env.example` becomes ignored again. It stayed tracked in the test only because it was already committed. Fixed by hand by moving `!.env.example` to the bottom after link. The skill's Phase 1 step 3 verification should re-run after Phase 3, or Phase 3 should re-append the negation after linking."
- 2026-09-05 · sunset live run (Banana Dunk) · sunset · "SKILL NOTE: A. Nesting bug: Phase 2 pre-makes the archive folder, so Phase 4's `mv` drops the repo inside it. Phase 2 step 2 (line 161) runs `mkdir -p ~/Developer/_archive/<Name>/.claude-memory` and copies the project memory store into it. Phase 4 step 2 (line 178) then runs `mv ~/Developer/<Name> ~/Developer/_archive/<Name>`. Because the destination already exists as a directory, `mv` moves the repo INTO it: the live result was `~/Developer/_archive/Banana-Dunk/Banana-Dunk/` with `.claude-memory` as a sibling of the nested repo. The test session repaired it by hand with rename-only moves and verified `git log` in the final location. Earlier sunsets (RJ-Hauler, SmartTab, jpb, claude-build-loop) were scanned and none is nested, most likely because no project memory store existed to trigger the `mkdir`.
  Orchestrator reproduction in a scratch folder, 2026-09-05:
  | Case | Result |
  |---|---|
  | Skill as written: `mkdir -p _archive/Name/.claude-memory` then `mv Developer/Name _archive/Name` | nested: `Name/Name/file` beside `Name/.claude-memory` |
  | Alternative "mv into the parent": `mv Developer/Name _archive/` with `_archive/Name/.claude-memory` pre-made | `mv: rename … Directory not empty`, repo not moved |
  | Move first, then `mkdir -p _archive/Name/.claude-memory` | clean: `Name/file` beside `Name/.claude-memory` |
  So the fix is ordering, not the `mv` target: the repo must move before anything creates `~/Developer/_archive/<Name>`, and Phase 4 should refuse to `mv` if that path already exists (a prior sunset or a name collision) rather than let `mv` nest silently."
- 2026-09-05 · sunset live run (Banana Dunk) · sunset · "SKILL NOTE: B. Phase 6 token fallback stops too early. Step 2 (line 203) says the token comes "from `$VERCEL_TOKEN` or the logged-in CLI", but the `curl` on line 204 only reads `$VERCEL_TOKEN`, and step 3 tells the session to stop and hand Tony a curl when no token is available. The logged-in CLI's token lives at `~/Library/Application Support/com.vercel.cli/auth.json` (JSON, key `token`; orchestrator confirmed the file exists with keys `expiresAt`, `refreshToken`, `token`, `userId` on 2026-09-05, values not read). The live run used it with `$VERCEL_TOKEN` unset and the pause returned HTTP 200. The skill should name that file as the fallback source and only stop when both are absent. The token is a credential: read it into a shell variable for the `Authorization` header only; never echo it, never write it into the tombstone or any file."
- 2026-09-05 · sunrise live run follow-up (Banana Dunk) · sunrise · "SKILL NOTE: F. Sunrise never commits or pushes after its Phase 2 push, yet Phase 8 prints "pushed". (Sunrise skill; surfaced by the Slice A signoff, recorded there as a MINOR on the punch list and as the new `REVIEW.md` repo-specific check; confirmed by the skill-fix session and by the orchestrator on the branch at `6366123`.) The only commit step is in Phase 1 and the only push is Phase 2. Every edit a later phase makes to the working tree, today the post-link `.gitignore` re-assert in Phase 3 step 2 (and `vercel link`'s own appends), and on 2026-09-04 a kit-check fix, stays uncommitted while the Phase 8 summary line (`Repo -> ~/Developer/<Name> (git init, pushed)`, line 328 on the branch) claims the repo is pushed. Orchestrator count: `git commit` / `git push` occurrences in Phases 3 through 8 = 0. Fix: after Phase 3 step 2 (or as a Phase 8 pre-flight), `git status --porcelain` must be empty or the skill commits the remaining changes with a named message and pushes, then the summary may say "pushed"; and Phase 8's kit check gains no line (the vault note's four lines stay), the check lives in Phase 8's own pre-flight. Slice A's R3 never asked for a commit, so this is a spec gap, not an unmet requirement."
- 2026-09-05 · sunrise live run follow-up (Banana Dunk) · sunrise · "SKILL NOTE: G. A real project name sits in the public skill text. (Sunrise skill; Slice A signoff MINOR (b).) `plugins/sun/skills/sunrise/SKILL.md` line 231 on the branch cites `Banana-Dunk` as the directory name Vercel rejected. tony-skills is PUBLIC and its `CLAUDE.md` says nothing Tony-specific goes in by default. Tony's word on 2026-09-05 (relayed by the orchestrator; confirm it in the ship report of the sunrise PR) was to leave it for that PR and genericize it here: replace the name with a generic mixed-case example such as `My-App`, keep the date and the HTTP 400. Count today: 1 mention."
- 2026-09-05 · sun-live-run-fixes-2 handoff · handoff · "SKILL NOTE: the checkpoint commit was made on a new branch feat/sunset-live-run-fixes rather than on main, because this repo never takes direct commits on main; the branch is the one /build's preflight would have created anyway."
- 2026-09-05 · sunrise live run follow-up (Banana Dunk) · sunrise · "SKILL NOTE: E. Machine-specific facts in the seeded `AGENTS.md` (orchestrator's addition, PENDING TONY'S RULING). The seeded body's "Where to look" section carried the vault path `~/ObsidianVault/03-projects/banana-dunk/`. The same question was raised as a MINOR in Slice B's signoff (keep the vault path and Notion URL in the repo file, or move them to the memory note and vault index like the local-path line was) and Tony has not ruled. The orchestrator's recommendation is move them out, because `AGENTS.md` is read by every host on every machine and some repos are public. Do not change this unless Tony rules in your terminal. If he rules "move out," it becomes a requirement in the same slice. (Ruled 2026-09-05 via the orchestrator: move out.)"
- 2026-09-05 · sun-live-run-fixes-2 handoff (after Slice A) · handoff · "SKILL NOTE: the checkpoint commit went on a new branch feat/sunrise-follow-ups rather than main, because this repo never takes direct main commits; it is the branch /build's preflight would have created for Slice B."
- 2026-09-05 · sun-live-run-fixes-2 follow-up (after PR #45) · sunrise · "The seeded AGENTS.md still writes a Notion board URL, which your move-out ruling says belongs outside the body. And one template line ships an editor's parenthetical into every new AGENTS.md. Neither blocks the merge. Each is a one-line fix for a later slice."
- 2026-09-06 · readers precon · precon · "SKILL NOTE: the exit test ran two readers (Fable and gpt-6-astra high) on Tony's typed word where the skill defines one; astra was sent despite the brief's reservation on the same word; the sitting exchanged cross-session messages (orchestrator check-ins, a grok-setup session) per the brief's protocol; Codex's pre-doc take was handled as a third cold reader through the relay folder."
- 2026-09-06 · readers precon · precon · "SKILL NOTE: the gate was reopened once on Tony's "wait" for a post-gate Codex review of the doc, handled as a fourth cold reader and a Round 4 (the skill defines re-invocation, not a reopen on a relayed review); the earlier note about two exit-test readers on Tony's word, astra sent despite the brief's reservation, cross-session check-ins, and Codex's pre-doc take still stands and is already logged via /fb."
- 2026-09-06 · readers plan inspect · inspect · "SKILL NOTE: the packet went to astra through Codex's `model_instructions_file` config key, verified on the cheap model first, after a first send put the packet's path (not its text) in `base-instructions` and was stopped unused; the recipe's field carried nothing on the successful send. Run 2's packet and its local lens both read a pre-write snapshot so run 1's stamp and block never reached them; run 2's citations in the doc are mapped to the live line numbers."
- 2026-09-06 · DJ sunrise · sunrise · "Phase 0 step 3 collision check uses a bare glob (`ls -d ~/Developer/*<Name>* 2>/dev/null`). Under zsh an unmatched glob aborts the whole ls and prints 'no matches found', so the count reads 0 even when a sibling pattern would have matched. Bit the DJ sunrise 2026-09-06: the Studio check passed only because nothing existed; the same shape relayed to the laptop reported 0 while ~/Developer/DJ already held DJ-LIBRARY.md. Fix: `find ~/Developer -maxdepth 1 -iname '*<name>*'` (case-insensitive, no glob abort), and treat 'no matches found' in output as a broken check. Same fix applies to any relay brief that copies the sunrise check."
- 2026-09-06 · readers slice A signoff/recheck · recheck · "SKILL NOTE: the two recheck: slice A blocks carry shortened parenthesised claims of the review: slice A lines rather than the originals verbatim, so a strict file:line + claim join fails; every file:line is unique within the review block, so a location-only match resolves each item. The handoff block says so for the next preflight."
- 2026-09-06 · readers slice B ship · ship · "SKILL NOTE: every reviewer and verifier worktree came up at main and each moved itself to the slice commit; the reviewer mandate should require a canned hook on every dispatch, refusals included, after two accidental sends. The handoff checkpoint from Slice A rode onto this branch by cherry-pick because it never reached PR #47; a recurrence appended two lines to REVIEW.md under signoff's second-failure rule."
- 2026-09-06 · readers · ship · "SKILL NOTE: /ship's Step 1 assumed the slice branch comes off merged main per the handoff; B was unmerged when Tony summoned C, so the branch was cut off feat/readers-slice-b and logged as a build assumption. Under /ship's fix step, one MAJOR (the `.readers/` residue) had an out-of-footprint half (`.gitignore`); the in-footprint half was fixed and the rest carried as a question rather than treated as stop condition 4, since the recorded failure scenario was closable inside the footprint."
- 2026-09-06 · readers · handoff · "we need some feedback on the handoff for a clearer understanding of what to post in a fresh terminal after a clear. Trigger: the readers after-Slice-D HANDOFF block (20:50) gave Next as `/recheck` naming readers.py:779, then `/ship slice E docs/plans/2026-09-06-readers.md`, and Tony asked whether to paste the whole block or just the doc name into the fresh terminal."
- 2026-09-06 · readers · readers · "Slice E build-ledger discoveries, logged on Tony's word after the good-or-bad read: (1) under readers the Claude lane's two paper lenses run packet-only on the Workflow route, so a session without the Workflow tool gets lane-unavailable where the old general-purpose subagents ran anywhere; follow-up wanted: a roster fallback route through the plain subagent, labeled unmeasured, so a missing tool degrades on record instead of stopping the lane. (2) the Claude lane's isolation label is split, paper lenses harness-enforced (toolCalls: 0) and repo-reality under repo unmeasured, while inspect's report carries one Inspector label; follow-up wanted: a label per lens, or the paper label plus 'repo-reality: repo, by design'."
- 2026-09-06 · readers · ship · "i want to discuss the pros and cons of adding "handoff" to the ship skill as well"
- 2026-09-08 · tony-skills · signoff / readers · (per Tony's 2026-09-08 ruling
  "stands", relayed by the orchestrator session) "under /ship the author
  session is the one that runs a lens's mutating check in the worktree it
  cuts at Step 3.5, because readers' `repo-with-tools` instruction bans
  tracked-file writes wherever the workspace points; that check is
  self-graded by the session that wrote the fix. Wanted later, not now: a
  readers write-permitted worktree mode so a fresh reviewer can run the
  mutating check in an isolated copy and the session never grades its own
  fix."
- 2026-09-08 · readers-followups slice B · ship · "SKILL NOTE: /readers' installed body names the a2e279be871a cache runner as RUNNER; every runner step in this run used the checkout's runner by path per the plan's Constraints line 7 (the cache copy predates main), as Slice A's run did."
- 2026-09-08 · readers-followups slice C · ship · "SKILL NOTE: the installed readers body (a2e279be871a cache) predates Slices A–C and names the cache runner; every runner step ran the checkout's runner by path per the plan's Constraints line 7, as A and B did. Captures were extracted byte-exact from subagent transcripts because the Agent tool's completion notification HTML-escapes angle brackets (third run using this workaround; SKILL.md Step 3 still names no such route, a MINOR on record). The recheck kept the readers-build MAJOR off its closed list on the strength of the claim field's own charge, flagged here rather than paused."
- 2026-09-09 · readers-followups slice C · handoff · "SKILL NOTE: the handoff committed the tracked docs/feedback.md into the checkpoint although /fb leaves it uncommitted, because the vertical's clean-tree precondition stops on dirt inside the boundary; the checkpoint went on a branch because a direct commit on main is barred. Decided on your behalf per Step 6; say the word if you want it undone."

## Dispositions

- 2026-08-02 · the mutation-contamination lesson → became Slice K on
  skill-loop-edits-build-plan.md (rule 9 names the checkout; the worktree
  default for mutation-requiring lenses; the SKILL NOTE channel itself);
  shipped and signed off 2026-08-02.
- 2026-08-02 · the end-of-file convention SKILL NOTE → became Slice L (the
  ledger home rule at every append site; the SKILL NOTE template slot),
  folded in with the template-slot drift caveat from the same exchange;
  shipped and signed off 2026-08-02.
- 2026-09-05 · the two sunrise live-run notes (Banana Dunk: A, Vercel rejects
  the directory-derived project name; B, `vercel link` re-ignores
  `.env.example`) → became Slice A of
  docs/plans/2026-09-05-sunrise-live-run-fixes.md (`--project <slug>` on
  link; `!.env.example` re-asserted as the last `.gitignore` line after link).
- 2026-09-05 · the two sunset live-run notes (Banana Dunk: A, Phase 2 pre-made
  `_archive/<Name>` so Phase 4's `mv` nested the repo inside it; B, the Phase 6
  token fallback stopped without reading the logged-in CLI's `auth.json`) →
  became Slice A of docs/plans/2026-09-05-sun-live-run-fixes-2.md (Phase 4
  guard on an existing archive path, move-then-copy, `--keep-local` skips the
  copy; Phase 6 reads `auth.json` key `token` into a variable for the header
  only and stops only when both sources are absent).
- 2026-09-05 · the three sunrise live-run follow-up notes (Banana Dunk: E, the
  seeded `AGENTS.md` "Where to look" carried a machine-specific vault path; F, no
  phase after Phase 2 commits or pushes, so the post-link `.gitignore` re-assert
  stays uncommitted while Phase 8 prints "pushed"; G, the real project name
  `Banana-Dunk` sat in the public skill text at Phase 3 step 1) → became Slice B
  of docs/plans/2026-09-05-sun-live-run-fixes-2.md (Phase 8 pre-flight requires
  an empty `git status --porcelain` or commits and pushes before the summary may
  say "pushed", with Phase 3 step 2 pointing at it; the example name is the
  generic `My-App`; the seeded `AGENTS.md` names the vault project folder without
  a path, per Tony's 2026-09-05 ruling).
- 2026-09-06 · the three `readers` notes of 2026-09-06 in the Inbox (thread `readers precon`, two lines: the exit test ran two readers on Tony's typed word where the skill defined one, and the gate reopened for a relayed Codex take as a fourth reader; thread `readers plan inspect`, one line: the packet reached astra through Codex's config key after a path-not-text send was stopped) → became Slice D of docs/plans/2026-09-06-readers.md (precon's exit test lists the roster rows with the `/readers suggest` result, admits several readers per sitting on Tony's word, each its own `/readers` call and section; architect's blind review runs each reviewer as its own `/readers` call; the codex transport recipes leave both skills, so a caller no longer chooses a config key or a `base-instructions` field).
