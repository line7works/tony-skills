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
   `## Dispositions`: note → what became of it (slice shipped, declined with
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

## Dispositions

- 2026-08-02 · the mutation-contamination lesson → became Slice K on
  skill-loop-edits-build-plan.md (rule 9 names the checkout; the worktree
  default for mutation-requiring lenses; the SKILL NOTE channel itself);
  shipped and signed off 2026-08-02.
- 2026-08-02 · the end-of-file convention SKILL NOTE → became Slice L (the
  ledger home rule at every append site; the SKILL NOTE template slot),
  folded in with the template-slot drift caveat from the same exchange;
  shipped and signed off 2026-08-02.
