# /ship — live smoke run notes (2026-08-20)

Run: Slice B of ~/Documents/skill-lab/ship-skill-build-plan.md. Target: Tony's "atlas
work" session, summon `/goal /ship D` (no doc argument), resolved to Slice D (History
prototype gate) of ~/Developer/Atlas/docs/baseline-test-page-build-plan.md — Tony's
pick at the pause. Observed from the skill-building session via Tony's relays and a
screenshot; the atlas session owes a post-run report (SHIP block, hook check, friction,
pause/stop classifications).

## Observed so far

- ✅ Step 0 fired: hook-armed confirmation verified before anything else (rule 8),
  reported in chat. Session also read the goal-hook vault index on its own — Tony's
  standing rule composing cleanly with /ship, not prescribed by it.
- ✅ Pause-vs-stop: two-candidate doc tie correctly classified as a pause (question to
  Tony), not a stop.
- ❌ DEFECT (fixed live): session cwd was the home folder, not a repo; the hunt swept
  ~/Developer cross-repo and invented a "narrow by unsigned Slice D" heuristic no spec
  sanctions. Tony's ruling: hunt confined to the current repo; not in a repo or
  nothing found = ask, never sweep. SKILL.md Step 1 amended 2026-08-20 (per user).

## Run 1 result (atlas session's report, received cross-session)

Ended STOPPED (condition 3): Slice D depends on Slice C, not started — /build preflight
stop, correctly mapped, nothing built or changed, no git actions. SHIP block emitted
verbatim per R7 with the early-stop values filling cleanly (Signoff/Recheck: not
reached · Laps: 0 · Card untouched) — the lap-1 fix for unfillable fields held. Prior
Atlas punch-list MINORs correctly listed in Remains as not this run's to fix.

Mechanisms verified live: Step 0 hook check (armed, reported) · pause (2-candidate doc
tie → question → resume on Tony's answer, no SHIP block at the pause) · stop condition
3 (preflight) · honest report fields. Friction reported: (a) hunt outside a repo —
already fixed per Tony's ruling above; (b) condition 3's "stops mid-slice" wording vs
a preflight stop (nothing built) — classification unambiguous in practice; matches the
existing preflight-ambiguity MINOR on the punch list, wording to fold with the MINORs.

## Run 1 addendum — hook/skill collision (MAJOR design finding, fixed live)

> NOTE 2026-08-20 (post-signoff): the carve-out-clause design described in this section
> and in the run-2 fold-back list was SUPERSEDED same day by the bare-summon redesign —
> Tony ruled the summon stays `/goal /ship <slice> [doc]` bare, with the goal semantics
> (ALL CLEAR, honest stop, or held pause = met) defined inside the SKILL.md. History
> below kept verbatim.

After the SHIP block, the /goal Stop hook FIRED against the honest stop: a bare
`/goal /ship slice D` condition reads only ALL CLEAR as met, so the hook blocked the
session's exit on an ending /ship's rules command. The session held the stop (refused
to build Slice C unasked or D on a bad foundation) and reported the collision —
first live case of the hook being load-bearing against an honest stop. Fix folded
into SKILL.md Step 0 same day: the documented summon line now carries a carve-out
("met when /ship reports: ALL CLEAR, or an honest stop or pause per its rules") plus
an explicit never-grind instruction. For Tony's goal-hook log: hook fired, held,
session honest under pressure — a strong scorecard row.

## Run 2 (slice C, Atlas) — in progress

- ✅ Repo rule composed: Atlas's "stop on any UI/UX change until Tony sees it" fired
  inside /build; /ship classified it as a PAUSE (Tony-question), relayed it with the
  review URL + steps, and held.
- ✅ Rule 6 stress-tested: the /goal hook blocked the turn NINE consecutive times; the
  session refused to answer the Tony-question on his behalf every time, until the
  harness's stop-hook block cap (9) force-ended the turn.
- ❌ Collision repeat: Tony typed the bare `/goal /ship C` without the amended
  carve-out clause — the hook can't see a pause as legitimate and spun ~17 min. The
  SKILL.md fix is correct but relies on the summon line actually being typed; the
  human-compliance gap is the remaining risk. Candidate MINOR: shorten the documented
  clause to something typeable from memory (e.g. `— met per /ship's rules`).
- ✅ Pause discipline under conversation: Tony asked questions mid-pause ("what am I
  looking for", a lost-nav question); session answered inside the pause without
  treating them as the resume word — only "looks good" resumed it. Survived three
  9-block hook cycles total.
- ✅ Resume-from-pause: on Tony's word the run picked up exactly where it held —
  build ledger written, card flipped to built, proceeding to /signoff.

## Run 2 final (atlas session's report): ALL CLEAR, Laps: 2

Full loop exercised: contract + preflight + before photo (274 green) → BUILD COMPLETE
(2 honest deviations) → DEEP signoff, 5 lenses, SIGNED OFF WITH CONDITIONS (4 MAJORs,
1 refuted, 13 MINORs) → fix pass (3 code MAJORs fixed in-footprint; AC3 Tony-only MAJOR
paused → WAIVED (per user) line written, the rule-2 sanctioned write, exercised live) →
recheck lap 1 PARTIAL (1 fix-introduced MINOR) → lap 2 → ALL CLEAR. Laps reported 2,
matches reality. 3 pauses, 0 stops, no third lap, git gates untouched (5 local commits,
feature branch, no push).

Fold-backs from run 2 friction (all applied to SKILL.md same day):
- Step 4: fix-introduced MINORs are fixed unasked (Step 6's ALL CLEAR demands it) —
  the one exception to leave-MINORs; and Tony-only MAJORs are named as a pause case.
- Step 0: a bare summon gets one line printing the full carve-out summon line
  copy-pasteable (Tony typed the bare wrap in both runs; hook spun on every pause —
  ~20 block-cycles in run 2).
- Untested still: the repo-confined hunt language (run 2 resolved its doc from the
  session tier; no hunt ran).

Slice B verdict material: every mechanism except the amended hunt confinement verified
live. Both /goal-hook collisions (vs stop, vs pause) documented for Tony's hook log.

(Stale closing paragraph removed 2026-08-20 — it predated run 2 and contradicted the
final record above. Authoritative state: run 2 drove the full loop to ALL CLEAR; see
"Run 2 final". Still untested live: the repo-confined hunt language.)

## Run 3 (2026-08-21, /digest build repo) — bare-summon semantics VERIFIED

Tony ran /ship during the /digest build. Run ended on stop condition 2 (a BLOCKER's
fix required amending the spec) and the session correctly declared the /goal condition
met by /ship's own definition — honest stop, hook released, no block cycles, no
grinding. The bare `/goal /ship <slice>` summon with skill-defined goal semantics is
now live-verified. Remaining untested: the repo-confined hunt language only.
