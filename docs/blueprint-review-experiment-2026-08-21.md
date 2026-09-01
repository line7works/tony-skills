# Blueprint cold-review experiment — 2026-08-21

**What this is:** the first live test of the parked "/blueprint post-draft cold
review" idea (Tony, 2026-08-21, recorded in
`~/Documents/handoffs/2026-08-21-architecture-skill-sunrise-sunset-findings.md`).
Tony ordered it mid-/blueprint on the /architect build plan: "Do a 'blueprint
review/signoff' with a local and a gpt. Both cold and with the precon doc."
This doc is the record for the later blueprint-rework talk: process, both
reviews verbatim, disposition, and a verdict on whether the mechanism earns a
standing place in /blueprint.

## Process

- **Subject:** `~/Documents/skill-lab/architect-skill-build-plan.md` (the
  freshly drafted plan) reviewed against
  `~/Documents/architect-scope.md` (the precon scope doc, the spec of record).
- **Reviewer 1 — local:** a fresh zero-context Claude subagent
  (general-purpose), read-only, given only the two file paths.
- **Reviewer 2 — GPT:** `gpt-5.6-sol` via codex MCP, `web_search: disabled`,
  read-only sandbox, neutral cwd, instructed to read only the two named files.
- **Identical mandate to both:** adversarial inspector who was never in the
  room; four fixed lists — MISSING/MISREPRESENTED (decided scope lines the
  plan omits/weakens/contradicts), INVENTED (plan obligations with no scope
  basis; builder-level gap-filling explicitly legitimate), UNCHECKABLE
  (criteria too vague to verify), QUESTIONS. No redesign, no solutions.
- **Blindness:** neither reviewer saw chat context, the other reviewer's
  output, or the findings doc (only the two files). Both ran in parallel;
  GPT returned in ~1 min, local in ~2 min.
- **Timing in the /blueprint run:** after Step 4 (doc written), before Step 5
  (read-back) — so findings could fold into the plan before Tony graded the map.

## Headline result

**The mechanism caught a real spec-integrity defect the room could not see:**
the plan's property-line requirement (R11) rested on Tony's interview answer
("Ok then") that was never ledgered in the scope doc — which claimed
"Open: none." The local reviewer flagged it precisely ("the spec is stale or
the plan is inventing — which is it?"). Neither the plan author nor Tony
caught this; it is exactly the class of defect a cold reviewer with only the
two documents can see and an in-room author cannot. Repair: the ruling was
ledgered into the scope doc post-gate (flagged as such) and the plan now cites
the ledger line.

## Reviewer comparison (for the mechanism verdict)

- **Overlap (found by both):** the downstream contract (sunrise-provisions /
  blueprint user-touchable-first) had no home in the plan; the rejected-
  candidates recording had no home in the four-part output; the docless-input
  sentence was an unsettled invention; "genuinely distinct candidates" was
  uncheckable. Convergence = high-confidence findings, same effect as jpb's
  matched clusters.
- **Local-only strengths:** the property-line provenance defect (headline);
  pin-by-value vs pin-by-reference drift on the GPT model id; the exit-ramp /
  "every run" ambiguity (do tiny runs get the visual + review offer?); the
  docless slug hole; missing-URL-on-re-run edge; the narrowness guardrail
  dropped from the plan. The local reader was markedly stronger on
  cross-referencing ledger lines and even verified the plan's claimed
  27/13 counts against the scope doc.
- **GPT-only strengths:** flagged that R13's disagreement-walk wording
  narrowed the scope's "disagreements" ruling to build-vs-cut only; pressed on
  "one negotiation" having no observable criterion; systematically listed
  house-convention content (report block, smoke-test slice) as scope-invented —
  technically correct from two files, practically noise given house precedent.
- **Noise profile:** both reviewers flagged legitimate builder-level
  gap-filling as INVENTED despite the mandate's carve-out; the GPT list was
  noisier. A future standing mechanism should hand reviewers the house
  precedent (a prior accepted build plan) to suppress convention
  false-positives.

## Disposition of findings

**Fixed in the plan (12 edits, all pre-read-back):** exit-ramp runs
explicitly keep the visual + review offer; narrowness guardrail added to R4;
"genuinely distinct" operationalized (differ in ≥1 poured-concrete category);
rejected-candidates' whys homed in the run log; docless slug rule added;
R13 widened to every substantive disagreement + model pinned by reference
(gpt-5.6-sol at time of writing); R14 Next-line now carries the downstream
contract; R1 "must not invite" made checkable; R12 missing-URL fallback;
AC5 verifies against jpb's pinned id; Slice B AC2 depth made observable;
AC6 privacy check made observable; "in a minute" de-literalized.

**Fixed in the scope doc:** property-line ruling ledgered (post-gate append,
flagged as such in the line).

**Rejected as noise (with why):** house-convention content flagged as
invented (report block, SKILL NOTE discipline, live smoke-test slice, B-R2
wording) — established across precon/ship/fb build plans, all signed off;
"/blueprint post-draft cold review has no scope basis" — provenance lives in
the findings doc the plan cites, which reviewers didn't receive;
"one negotiation unenforceable" — the three-step order + razor criterion IS
the mechanism, accepted as prose intent; transport guards "unverifiable from
two files" — verifiable on the property (jpb SKILL.md), AC5 now points there.

**Left as recorded assumptions (Tony can veto at read-back):** docless runs
take the discussion as input; rejected-whys live in the run log; missing-URL
fallback publishes fresh; docless slug from working name.

## Verdict on the mechanism (for the blueprint-rework talk)

Worth adopting. Cost: ~3 minutes wall-clock, two parallel sends, zero
marginal dollars on subscription transports. Yield on first live run: one
real spec-integrity defect, two decided-line fidelity drifts, ~10 checkability
fixes, all folded in before the doc could become law downstream. The
plan-vs-spec framing (two docs, four fixed lists) discriminated well; the
main tuning need is convention-awareness to cut the INVENTED noise. Open
design questions for the rework: one reviewer or two (the local reader alone
caught the headline defect; GPT added breadth but more noise); where the
review lands in blueprint's step order (post-draft, pre-read-back worked);
whether reviewers get a prior accepted plan as a convention reference.

---

## Reviewer 1 — local Claude subagent (verbatim)

I read both files cold. Findings follow, in exactly the four lists requested.

### 1. MISSING / MISREPRESENTED

- **Scope line 21 (decided): "Output doc is consumed downstream: /sunrise provisions exactly what it lists; /blueprint slices from it with the user-touchable slice up front."** The plan records only the interim hand-pointing rule (Constraints paragraph; Slice A R14 `Next:` line). The downstream contract itself — especially "user-touchable slice up front" — appears nowhere in the plan, not even as a line the architecture doc or SKILL.md should carry. The /sunrise//blueprint reworks are out of scope, but the decided contract has no recorded home in the plan.

- **Scope line 39 (decided): "The external-review offer comes once, at the end of every run."** Plan R13 says the offer comes "after the doc and visual are done," which weakens "every run": read together with R3 (exit-ramp runs "end the interview in a minute" with a tiny doc), the plan never says whether an exit-ramp run still gets the visual and the review offer. Scope line 47 also says "End of every run produces a visual" — R3's tiny-run path is silent on both, so two "every run" decisions are ambiguously weakened for the exit-ramp case.

- **Scope line 34 (assumed, but restated in the plan with drift): "pinned model per jpb's SKILL.md."** Plan R13 hardcodes the literal id `gpt-5.6-sol`. The scope pins by reference (whatever jpb's SKILL.md says); the plan pins by value. If jpb's pin ever changes, the plan's literal contradicts the scope's indirection. AC5 then verifies against the hardcoded value.

### 2. INVENTED

- **Plan Constraints + R11 — the entire "property line" requirement**: "property line as /precon's — the repo, project docs, and Claude's own knowledge only, no web, no research subagents, factual unknowns that need outside checking become marked lines in the architecture doc for Tony to resolve (Tony's interview answer, 'Ok then,' 2026-08-21)." Nothing in the scope doc establishes any of this. The scope's closest line is "Grilling is Claude-only inside the run" (line 26), which is about the review, not lookups. The plan cites provenance ("Tony's interview answer") that lives outside the spec of record — and the scope explicitly says "Open: none." This is a full requirement (R11) plus part of AC4 and Slice B AC8 built on a ruling the scope never recorded.

- **Plan R13 — the four transport guards**: "with `web_search: disabled`, read-only sandbox, and a neutral empty cwd." The scope's transport line (34) says only "same as /precon's exit test — GPT via the codex MCP, pinned model per jpb's SKILL.md." The three guards may genuinely be that convention, but the scope doc never names them, and AC5 makes them hard acceptance criteria. From these two files alone they are unverifiable obligations.

- **Plan R6 — "Tony picks; the pick and the rejected candidates' one-line whys land in the doc."** The scope decides that candidates are forced into the open (line 17) but never says rejected candidates' rationales are recorded in the doc — and the decided four-part output (line 20 / R8) has no section for them.

- **Plan R2 — "Docless runs take the current discussion as their input."** The scope decides the docless gate and the recorded reason (lines 33, 44) but is silent on what a docless run's input is. This sentence settles a question the scope never settled.

- **Plan Out of scope, item 2 — "and a standing /blueprint post-draft cold review — reason: Tony parked both."** The scope's out-of-scope list (line 55) parks only hierarchical /blueprint. The "standing post-draft cold review" and the claim Tony parked it have no basis in the scope doc.

### 3. UNCHECKABLE

- R6 / Slice B AC4: **"2–3 genuinely distinct candidate structures"** — no test for "genuinely distinct." An inspector reading a transcript cannot rule whether two candidates were distinct or the same idea twice; the criterion turns on judgment the plan never operationalizes.
- R12: **"keep the first version simple and legible; do not build a design system"** — "simple and legible" is unverifiable, and "design system" is undefined; the scope deliberately unspecified the visual, but the plan converts that into a soft requirement nobody can pass or fail.
- R3: **"ends the interview in a minute"** — not measurable and presumably not literal; a builder cannot know what satisfies it.
- Slice B AC2: **"the run's depth matches its answer"** — "depth matches" has no definition; any transcript can be argued either way.
- Slice B B-R2: **"material behavior changes get one more run-through of the affected step"** — "material" is undefined, so the trigger for the extra run-through is unfalsifiable.
- R1: **"its description must not invite model auto-invocation"** — "invite" is a judgment call with no stated test (contrast /precon-style explicit "strictly user-invoked, never auto-invoke" wording, which is checkable).

### 4. QUESTIONS

1. **Where is the property-line ruling recorded?** The scope doc says "Open: none" yet contains no property-line decision. If R11 rests on an interview answer outside the spec, the spec is stale or the plan is inventing — which is it, and should the scope doc be amended first?
2. **Do exit-ramp (tiny-doc) runs produce the visual, publish the artifact, and get the blind-review offer?** Scope says "every run" for both; plan R3 is silent. Slice B could hit this path and have no criterion.
3. **What is the doc filename for a docless run?** R8 derives `<slug>` from the precon scope doc; a docless run has none. Same question for the review file path in R13.
4. **Is `gpt-5.6-sol` actually the current pin in jpb's SKILL.md, and are `web_search: disabled` / read-only sandbox / neutral cwd actually /precon's exit-test transport?** Both are asserted, neither is verifiable from the two files, and both are acceptance-checked (AC5).
5. **Where in the four-part output doc do the rejected candidates' one-line whys (R6) live?** R8's four parts don't include them, so a builder must either add a fifth section or violate R6.
6. **The narrowness guardrail (scope line 30, assumed: interview stays ~three answers) has no counterpart anywhere in the plan** — no requirement, no acceptance criterion. Intentional drop, or omission?
7. **Should the SKILL.md or the architecture doc carry the decided downstream contract (scope line 21 — "user-touchable slice up front"), or is that wholly deferred to the /sunrise//blueprint reworks?** Right now it lives nowhere.
8. **R12 says the same artifact URL is kept across re-runs, with the URL recorded in the doc — what happens on a re-run if the URL is missing from the doc** (first migration, hand-edited doc)? No behavior specified, and Slice B only exercises run 1.
9. **Slice B AC6 asks Tony to verify the artifact is "private"** — what observable check establishes privacy from the transcript or the URL?

One cross-check that passed: the plan's claimed provenance count ("27 decided / 13 assumed lines") matches my tally of the scope doc's Decisions list exactly.

---

## Reviewer 2 — GPT `gpt-5.6-sol` via codex MCP (verbatim)

1. **MISSING/MISREPRESENTED**
- Scope decision: "`/sunrise provisions exactly what it lists; /blueprint slices from it with the user-touchable slice up front`." The plan does not require `SKILL.md` to state this downstream contract. Slice A R14 only says Tony manually points the two skills at the document; "user-touchable slice up front" is omitted.
- Scope decision: external review "`presents the two docs' disagreements side by side and Tony rules each one in discussion`." Slice A R13 narrows this to "`where the outside model built what Claude cut, or cut what Claude built`," potentially excluding disagreements about structures, assumptions, one-way doors, data flow, or deferred decisions.
- Scope decision: "`One skill, two passes ... run as one negotiation — the tension is the product`." Slice A R4 specifies the passes and order, but provides no enforceable requirement that delivery and architecture be negotiated against one another rather than executed as a sequential questionnaire.
- Scope decision: "`One-way doors ... decided for the vision up front; everything else stays two-way`." Slice A R7 says this, but R8 defines the poured-concrete list merely as "`the one-way decisions`" without requiring the document to identify or preserve the two-way status of remaining decisions.

2. **INVENTED**
- Constraints: "`property line as /precon's — the repo, project docs, and Claude's own knowledge only, no web, no research subagents`." No such property-line decision appears in the scope document.
- Constraints: "`factual unknowns that need outside checking become marked lines in the architecture doc for Tony to resolve`." This creates a new required document category and owner.
- Slice A R2: "`path given in the invocation, or found beside the project — when more than one could match, list and ask`." The scope establishes only that the precon scope document is input; it does not establish discovery beside a project or ambiguity handling.
- Slice A R2: "`Docless runs take the current discussion as their input.`" The scope permits proceeding after recording a reason, but does not designate the discussion as a substitute input.
- Slice A R6: "`Tony picks; the pick and the rejected candidates' one-line whys land in the doc.`" The scope requires exposing candidates, assumptions, and later expense, but not recording rejected candidates or rejection reasons in the output.
- Slice A R12: "`URL recorded in the architecture doc`." The scope requires a stable private Artifact URL, but not recording that URL in the markdown record.
- Slice A R14 creates a mandatory report schema: "`ARCHITECT: <project>`," run number, counts, review status, `Next:`, and conditional `SKILL NOTE:`. The scope establishes no terminal report block or these fields.
- Slice A R15: "`don't publish the visual anywhere public (arcade included)`." Private Artifact delivery excludes public publication, but the arcade-specific prohibition is new.
- Slice B mandates "`one real /architect run end to end with Tony on a genuine project`," including in-place defect fixes and rerunning affected steps. The scope establishes skill behavior, not a mandatory live-project validation phase.
- Slice B R1: "`if none suits, he runs /precon on a real idea first`." This creates an additional prerequisite activity not established by the scope.

3. **UNCHECKABLE**
- Intent: "`the least structure ... without becoming demolition later`." Neither "least" nor acceptable future demolition is defined.
- Slice A R4: "`Two passes run as one negotiation`." No observable criterion distinguishes one negotiation from three sequential steps.
- Slice A R6: "`2–3 genuinely distinct candidate structures`." "Genuinely distinct" has no stated test.
- Slice A R7: "`One-way decisions are made at full-vision quality`." "Full-vision quality" is undefined.
- Slice A R11: "`A factual unknown that genuinely needs outside checking`." "Genuinely needs" is left to subjective judgment.
- Slice A R12: "`keep the first version simple and legible`." No legibility or simplicity standard is supplied.
- Slice B Goal: "`every mechanism observably fires`." AC7 permits declining the blind review, so its transport, saving, comparison, and ruling mechanisms need not fire.
- Slice B R2: "`material behavior changes get one more run-through of the affected step`." "Material" and the required extent of a run-through are undefined.
- Slice B AC2: "`the run's depth matches its answer`." No expected depth by answer is specified.
- Slice B AC4: "`distinct candidates`." The acceptance test does not define how the inspector determines distinctness.

4. **QUESTIONS**
- Must `SKILL.md` explicitly encode the decided downstream contract that `/sunrise` provisions exactly the document and `/blueprint` puts the user-touchable slice first?
- Must external-review comparison cover every substantive disagreement between the documents, or only build-versus-cut component disagreements?
- What observable behavior proves the two passes operated "as one negotiation"?
- Is the repo/docs/Claude-knowledge property line an approved requirement, and what source authorizes it?
- Must rejected candidates and rejection reasons remain in the architecture document?
- Is the mandatory report block approved, including counts, run number, review status, `Next:`, and `SKILL NOTE:`?
- Is a genuine-project smoke test part of the approved build, and may it require Tony to run `/precon` first?
- What objective standards determine "genuinely distinct," "full-vision quality," "simple and legible," and a run depth that "matches" the exit-ramp answer?
