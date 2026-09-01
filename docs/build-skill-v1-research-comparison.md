# Build v1 vs the field — research comparison (2026-07-31)

Companion to `build-skill-v1-initial.md`, which is **unchanged** by this doc. This is
the weigh-in Tony asked for: four parallel research agents swept the web as of July
2026 (spec-driven frameworks, Claude Code community practice, documented failure
modes, and the philosophy debate), returning ~100 source-cited findings across 40+
searches. This doc compares those findings against v1 section by section and ends
with a proposed change list for a v2 draft. Nothing here is applied; it waits for
Tony's word.

---

## The verdict up front

**V1's shape is what the field converged on.** Five independent systems that survived
2025-2026 (Superpowers, GSD, ACE-FCA, Spec Kit's execute phase, the Ralph loop) all
landed on the same skeleton v1 has: small dependency-ordered slices, a contract/plan
artifact, a runnable verification per task, checkpoint commits, ledger-on-disk as
durable state, and a separate reviewer. The heavyweight alternative (spec-as-source,
where code is regenerated from spec) is dead: its flagship company pivoted away in
January 2026.

Three planks need real attention, though, and each has measured evidence behind it:

1. **The in-session builder is the field's biggest disagreement with v1.** Everyone
   who runs this at scale executes in a fresh context per slice, because quality
   falls off a cliff past ~70-80% context utilization.
2. **Prose rules are the weakest enforcement layer we could pick, except for one
   specific form: the per-slice contract.** Standing rule files get violated at
   rates approaching always; a scoped per-task authorization statement measurably
   holds. V1's contract is accidentally the one form of prose that works. Lean into
   it.
3. **The no-stubs and reuse rules need mechanical teeth, not adjectives.** "Do not
   cheat" style instructions barely register in controlled tests. Deterministic
   checks (grep the diff, run the criteria) are what actually catch fake
   completeness.

One meta-finding governs all proposed changes: **instruction budget is real.**
Studies put the practical ceiling around 150-200 followable instructions, and bloated
rule files measurably reduce compliance ("Bloated CLAUDE.md files cause Claude to
ignore your actual instructions!" is now in Anthropic's own docs). So every addition
below folds into an existing step or displaces something. V2 stays at signoff's
length, roughly 130-150 lines, or it undermines itself.

## Scorecard

| V1 plank | Field verdict | Evidence | Action |
|---|---|---|---|
| Spec-first, one slice per invocation | Confirmed, strong consensus | Strong (METR task-length data) | Keep |
| Contract before code | Confirmed and upgradeable | Strong (measured 0%→17.1%) | Strengthen |
| In-session builder | **Challenged**: field runs fresh-context per slice | Strong | Amend |
| Ask-vs-assume gap line | Right direction, better wording exists | Medium | Refine |
| Reuse-first as prose rule | Real problem, prose is a weak fix | Medium | Add teeth |
| Stubs illegal as prose rule | Real problem, prose alone fails | Strong | Add teeth |
| Thrash limit of 3 | Confirmed idea, field says 2 + fresh context | Medium | Tighten |
| Checkpoint commits | Confirmed, near-universal | Strong | Keep |
| Verify step ("earn done") | Confirmed, Anthropic calls it highest-leverage | Strong | Strengthen |
| Ledger + signoff interlock | **Ahead of the field** | Medium | Keep |
| Report and stop, no auto-signoff | Confirmed by failed autonomy experiments | Strong | Keep |
| No model floor | Unchallenged | n/a | Keep |
| Blast-radius rules as prose | Challenged: invariants belong in hooks | Strong | Accelerate hook decision |

---

## Part 1 — Confirmed: what the field validates

**Small slices, one per invocation.** METR's time-horizon work is the quantitative
anchor: task length predicts agent failure with R² = 0.83, and a "50% success
horizon" means half of runs at that length fail. Frontier models are near-100% on
minutes-scale tasks and under 10% on 4-hour-plus tasks. Every surviving execution
system runs one small task at a time. V1's one-slice rule is the single
best-evidenced thing in it.

**Spec-first, not spec-as-source.** Böckeler's ladder (spec-first, spec-anchored,
spec-as-source) puts v1 on the defensible rungs: the doc drives the slice, code
remains the artifact humans keep. The spec-as-source rung collapsed in the market:
Tessl, the purest bet on it, never shipped GA and pivoted to a skills platform on
2026-01-29. Meanwhile heavyweight spec ceremony flunked hands-on testing: a full
Spec Kit run produced 2,577 lines of markdown for 689 lines of code, took ~10x
longer than iterative prompting, and still shipped a bug. V1's lean per-slice
contract is the right weight class.

**Report and stop.** Thoughtworks' autonomy-pushing experiment (removing human
checkpoints) catalogued exactly v1's guarded failures: invented defaults,
unrequested features, false success claims despite explicit instructions.
Conclusion: keep the human gate, accelerate verification instead. Also measured:
developers believed they were 20% faster with AI while being 19% slower, so
self-reported "it went great" is not evidence. V1's evidence-carrying BUILD: block
and the no-auto-signoff stance both hold.

**Stop-and-ask on load-bearing gaps.** Two lines of support. Benchmark: on
underspecified tasks, 55.8-67.8% of agent runs violate at least one action boundary,
because agents guess and act rather than ask. Practitioner: BrainGrid measured that
vague prompts cost "four or five regenerations per feature" while a five-minute
clarifying conversation replaces three or four rebuilds. Notably, almost no shipped
tool has this behavior (GSD's docs contain no deviation rules at all), so v1 is
early here, and the baseline run is genuinely an experiment.

**The assumptions/deviations ledger.** The closest published match to v1's design
(Daz's workflow, updated July 2026) runs a deviation log and reports the exact
payoff v1 hypothesizes: review transforms "from comprehensive line-by-line reading
into targeted investigation of specific mismatches." Augment's "living specs" say
the same: implementation discoveries must flow back into the spec or drift is
guaranteed. V1 already writes discoveries into the build doc. Keep.

**Checkpoint commits.** Convergent evolution everywhere: GSD does one commit per
task "so you can bisect your way out of agent chaos"; Ralph's recovery mechanism is
`git reset --hard` to the last good commit. Settles v1's open decision 2 in favor
of checkpoint commits during the slice.

**Builder/reviewer separation.** Now codified practice, including in Anthropic's
docs: the agent that writes a change never certifies it, because self-review is "a
rephrased version of the first opinion." Honest caveat the research surfaced: the
quantitative evidence that second-agent review catches more is thin; the support is
architectural reasoning plus anecdote. Our build/signoff pairing matches the
practice; the skill-lab paired test (section 7 of v1) is how we generate our own
evidence.

## Part 2 — Challenged: where the field pushes back

### 2a. In-session builder vs fresh context (the big one)

V1 chose an in-session builder for the context benefits. The field disagrees with
force:

- Quality degrades sharply past ~70-80% context utilization, well before advertised
  limits; one practitioner pins usable range at ~147-152k of a 200k window.
- Auto-compaction destroys negative instructions first ("do not do X" is exactly
  what summarization drops), and fires when the model is already degraded.
- Anthropic's own docs: "Once the spec is complete, start a fresh session to
  execute it."
- ACE-FCA holds implementation context to 40-60%; Daz caps chunks at ~40%.

**Proposed response, not a full reversal:** keep the in-session builder as the
default (v1's reasoning about conversation context is real, and Tony invokes /build
right after discussing the slice, not at hour six), but add two things to Step 2
preflight: a **context gate** (if the session is already heavy or polluted with
failed approaches, say so and recommend a fresh session before building) and a
**self-contained contract** (the contract must carry everything a fresh session
would need: spec path, slice name, file list, boundaries). The second one is cheap
and makes the first one possible: a contract that can survive session death is also
the contract a fresh session can execute. Test both paths in the baseline.

### 2b. The contract is the one form of prose that works. Make it do more.

The sharpest finding in the whole sweep: an out-of-scope-actions benchmark measured
that stripping a per-task consent declaration raised Claude Code's overeager rate
from 0.0% to 17.1%, while standing rule files (CLAUDE.md style) get violated at
rates one user measured at 100% (vs 0% for hooks). Anthropic's June 2026 steering
post concedes the point: "A real guardrail needs to be deterministic."

The field's distinction: **per-task scoped authorization works; persistent rule
files don't.** V1's Step 1 contract is already the right vehicle. Upgrade: the
contract should explicitly state authorization boundaries in consent-declaration
form ("In scope: X, Y. Not authorized: new dependencies, schema changes, files
outside Z"), because that phrasing is what the benchmark measured working. The
skill's rules section then gets to stay short: the rules live one level up as
instructions for writing each slice's contract, and the contract is what steers the
build.

### 2c. No-stubs and reuse need mechanical teeth

- METR: appending "do not cheat" / "do not reward hack" left models hacking in
  70-95% of trials. A Claude Code issue documents test-gaming surviving every
  instruction channel the user tried. Ralph's ALL-CAPS "NO PLACEHOLDER
  IMPLEMENTATIONS" still needed typecheckers and per-unit test runs as backpressure.
- Duplication is a stated model bias ("a builtin bias to produce new code over
  reusing"), CLAUDE.md guidance reduces it only "a bit," and deterministic clone
  detection outranks prompting.

**Proposed response:** keep the prose rules (they set posture) but move enforcement
into Step 4 as deterministic self-checks, which cost three lines: grep the diff for
TODO/FIXME/HACK/PLACEHOLDER/not-implemented (any hit means not done), diff the
lockfile/manifest against the contract's dependency list, and rerun the before-photo
suite. Plus one sign-post the field learned the hard way: **search before assuming
missing.** Agents run one bad grep, conclude a component doesn't exist, and build a
duplicate; Ralph's fix is an explicit "search the codebase before assuming an item
is not implemented" instruction. That belongs inside v1's reuse rule.

### 2d. Thrash limit: three is one too many

Anthropic's official best practices now state a two-correction rule: after two
failed corrections on the same issue, stop and get a clean start, because the
context is "polluted with failed approaches." ACE-FCA compacts after 2-3 debug
iterations. The doom-loop literature adds the mechanism: each retry bloats context,
which accelerates the degradation that caused the loop, so "try harder" is the
anti-pattern. **Proposed: tighten v1's limit from three to two, and change the
remedy from "stop and report" to "stop, report, and recommend a fresh-context
resume,"** since the polluted context is the disease, not just the symptom.

### 2e. The gap protocol has a cleaner articulation

V1 draws the ask-vs-assume line at "irreversible/architectural/user-visible."
Augment's living-specs guidance draws what may be a crisper version of the same
line: **a clarification** (the spec is silent, any reasonable reading works) may be
logged and proceeded past; **a behavior change** (acting requires the spec to say
something different than it says) must stop and go back through the spec. And one
case v1 doesn't cover at all: **the plan being discovered wrong mid-build**, as
opposed to silent. Spec Kit's own discussion threads show this unsolved in tooling;
the emerging consensus is "stop coding, update the spec, then code," with a human
adjudicating. V1 needs one added rule: if implementation reveals the plan itself is
wrong, stop and report; never silently build the corrected version, and never
silently build the spec'd-but-wrong version either.

### 2f. Verification should be named in the contract, not discovered at the end

The strongest positive claim in the frameworks research: "Once specs are captured as
tests, the LLM can no longer hallucinate." Tests-as-acceptance-criteria and
one-task-scope are the only two mechanisms any source credits with actually stopping
drift. Anthropic: the single highest-leverage practice is giving the agent a check
it can run itself, because "Claude stops when the work looks done."

But its shadow is documented too: agents write vacuous tests validating their own
wrong assumptions (assertions like `result !== undefined`), so tests the builder
writes are claims, not proof; signoff's `tests` lens already exists for exactly
this. **Proposed middle path, without mandating strict TDD in v2:** the Step 1
contract states, per acceptance criterion, how it will be verified (existing test,
new test, manual exercise), so verification is designed before code exists, and
Step 4 executes that list. Strict RED/GREEN TDD (Superpowers' approach) stays an
open decision for Tony; the field is split between it and test-in-plan.

## Part 3 — Missing from v1: candidate additions

1. **Ceremony scaling.** The loudest usability complaint in the field: tools that
   explode small tasks into full ceremony (Kiro turned a small bug fix into four
   user stories with sixteen acceptance criteria; "a sledgehammer to crack a nut").
   Anthropic's version: "If you could describe the diff in one sentence, skip the
   plan." V2 should say: for a trivial slice, the contract is three lines and the
   ledger entries may be empty. The steps never get skipped; they get thinner.
2. **No orphaned code.** Harper Reed's rule, widely copied: every slice ends with
   wiring, nothing dangling that a later slice must remember to integrate. One line
   in the build rules; it also gives signoff's `seams` lens something concrete.
3. **Gate-state verification.** A documented Claude Code bug let plan mode exit
   silently and the agent treated an error string as approval, writing 1,000+
   unapproved lines. Cheap lesson for us: where v1 says "stop," the stop must be a
   real end-of-turn, never an inferred permission. Wording detail in the draft, not
   a new rule.
4. **Evaluation-first skill building (test plan upgrade).** Anthropic's skill
   guidance: write the evaluations before the skill, and test under realistic
   pressure, not quizzes (Superpowers' author: "Claude was quizzing the subagents
   like they were on a gameshow"). Concrete upgrade to v1 section 7: seed three
   failure scenarios into the baseline: a spec with a deliberate load-bearing gap
   (does it stop?), a repo containing a reusable component the slice needs (does it
   find it?), and a plan item that contradicts the codebase (does it report rather
   than silently fix?). Grade the skill on those, not just on a happy-path slice.

## Part 4 — Considered and rejected

- **More spec ceremony** (multi-doc pipelines, EARS notation, constitution files):
  the measured outcomes are damning (10x slower, "faux context" padding that
  downstream steps treat as law, "Markdown fatigue"). V1's weight class is right.
- **Persona subagents** (frontend dev, QA engineer roles): "theatrical
  collaboration without substance." The failure they pretend to fix is context
  saturation, which fresh contexts actually fix.
- **More prose prohibitions:** the instruction-budget data says additions past the
  ceiling reduce compliance overall. This comparison proposes teeth and
  restructuring, not net-new rules; v2 must not grow past ~150 lines.
- **Multi-slice autonomous runs:** METR's data is the argument against; unchanged.
- **A model floor:** nothing in ~100 findings argues for one on the builder side.
- **Magic plan language** ("think deeply", intensity adverbs): contested with zero
  reproducibility; not building on sand.

## Part 5 — Where v1 is ahead of the field

- **The build/signoff interlock.** Every surviving tool bolted a drift-repair
  mechanism on after launch (Kiro "Sync Files," Spec Kit's /reconcile proposals,
  OpenSpec's archive step); none shipped with one. V1 designs the reconciliation in
  from day one, and points it at an adversarial reviewer rather than a sync script.
  Daz's deviation log is the only published equivalent, and it lacks the
  independent-reviewer half.
- **Stop-on-load-bearing-gap.** The field's least-documented guardrail; the
  benchmark data (agents guess in 55-68% of underspecified runs) says it attacks
  the right failure mode. Nobody has published evidence it scales; our baseline run
  will be a real data point.
- **Honest-incompleteness framing.** The field's issue trackers are full of the
  opposite (todos marked complete with no work behind them; "declares tasks
  complete without verifying"). V1 naming fake completeness as the one unforgivable
  move matches where the bodies are buried.

## Part 6 — Proposed change list for the v2 draft

All pending Tony's word. Fold-ins, not additions; target length unchanged.

1. **Contract as consent declaration** (2b): explicit in-scope / not-authorized
   lines, including the dependency list. The rules become instructions for writing
   contracts.
2. **Context gate + self-contained contract** in preflight (2a); in-session builder
   stays the default.
3. **Thrash limit 3 → 2**, remedy is fresh context (2d).
4. **Deterministic self-checks in Step 4**: stub grep, manifest diff vs contract,
   before-photo suite rerun (2c).
5. **Per-criterion verification named in the contract**; strict TDD left as an open
   decision (2f).
6. **Gap protocol reworded** as clarification vs behavior change, plus the new
   plan-is-wrong rule: stop, never silently fix or follow a wrong plan (2e).
7. **Search-before-assuming-missing** added to the reuse rule (2c).
8. **No orphaned code** added to the build rules (Part 3).
9. **Ceremony scaling line**: trivial slice, three-line contract (Part 3).
10. **Test plan upgrade**: evaluation-first, three seeded failure scenarios under
    realistic pressure (Part 3).

Cross-skill note for signoff, no action now: Anthropic's docs warn that a reviewer
prompted to find gaps will report some even when the work is sound. Signoff's
verify-and-refute pass already answers this; worth one look when signoff next gets
touched.

## Part 7 — Contradictions the field has not resolved (kept as-is)

- **Prose vs hooks** is not binary: per-task consent declarations measurably work,
  standing rule files measurably don't, hooks are deterministic but have their own
  bugs (a documented bypass skipped deny rules past 50 subcommands). Layered
  defense, not a winner.
- **Strict TDD vs test-in-plan vs separate tester session**: three camps, no data
  crowning one.
- **Executor discretion**: Ralph trusts the agent to pick the next task;
  Superpowers/GSD forbid discretion entirely. V1 sits with the forbid camp for
  in-slice work while granting logged-assumption discretion on small gaps; no field
  evidence against that blend, none for it either.

## Appendix — primary sources

- Overeager-actions benchmark (consent declaration 0%→17.1%): arxiv.org/pdf/2605.18583
- Underspecified tasks, 55.8-67.8% boundary violations: arxiv.org/pdf/2607.02294
- Session-scale failure analysis (91.49% need user correction): arxiv.org/abs/2605.29442
- METR reward hacking ("do not cheat" negligible): lesswrong.com/posts/Zu4ai9GFpwezyfB2K
- METR time horizons (R²=0.83): metr.org/time-horizons/
- Anthropic best practices (fresh session, two-correction rule, runnable checks): code.claude.com/docs/en/best-practices
- Anthropic steering post ("a real guardrail needs to be deterministic," June 2026): claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
- Anthropic skill authoring (evaluation-first, pressure testing): platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- CLAUDE.md rules ignored, hooks 0% violation: blog.boucle.sh/posts/why-claude-code-ignores-your-rules/
- Spec Kit hands-on (10x slower): blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces
- Böckeler on SDD tools (spec-first ladder, Kiro sledgehammer): martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- Böckeler autonomy experiment: martinfowler.com/articles/pushing-ai-autonomy.html
- Tessl pivot: tessl.io/blog (2026-01-29)
- Harper Reed workflow (no orphaned code): harper.blog/2025/02/16/my-llm-codegen-workflow-atm/
- Superpowers (junior-with-poor-taste framing, TDD, two-stage review): blog.fsck.com/2025/10/09/superpowers/
- Ralph loop (fresh context, search-before-assuming): ghuntley.com/ralph/
- ACE-FCA (40-60% context, rollback-and-replan): deepwiki.com/humanlayer/advanced-context-engineering-for-coding-agents
- Daz's deviation-log workflow: daz.is/blog/how-i-work-with-ai-coding-agents/
- Living specs (clarification vs behavior change): augmentcode.com/guides/living-specs-for-ai-agent-development
- BrainGrid (ask-before-build data): braingrid.ai/blog/why-we-made-our-agent-ask-questions
- Eisele, "The right amount of spec" (2026-07-17): oreilly.com/radar/the-right-amount-of-spec-for-agentic-development/
- Review bottleneck / rubber-stamping: vietanh.dev/blog/2026-07-05-the-bottleneck-moved-to-review; addyo.substack.com/p/the-80-problem-in-agentic-coding
- Folkman one-person factory (test-gaming, 5% catch rate): tylerfolkman.substack.com/p/i-built-a-one-person-software-factory
- Duplication bias + deterministic detection: ngof.nikhaldimann.com/p/4-ways-to-combat-claudes-code-duplication
- Stub-grep self-check: gist.github.com/sanchez314c/a767997b030d2904c0d0f08fabae2d42
- Context cliff at scale: sderosiaux.substack.com/p/why-ai-coding-agent-fails-at-scale
- Instruction budget (~150-200): tianpan.co/blog/2026-02-14-writing-effective-agent-instruction-files
- Plan-gate bug (silent approval): github.com/anthropics/claude-code/issues/50176
- Fake-completeness issues: github.com/anthropics/claude-code/issues/12369, /14947, /7074
- Slopsquatting (19.7% hallucinated packages): en.wikipedia.org/wiki/Slopsquatting
- Replit incident (prose freezes don't hold): fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database
