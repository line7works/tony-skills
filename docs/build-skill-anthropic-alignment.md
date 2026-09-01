# Build skill vs Anthropic's 2026 guidance — alignment check (2026-08-01)

Companion to `build-skill-v1-initial.md` and `build-skill-v1-research-comparison.md`.
The installed skill (`~/.claude/skills/build/SKILL.md`, 101 lines) is **unchanged** by
this doc. Method: two research agents fetched Anthropic's official 2026 material —
the dedicated Opus 5 and Fable 5 prompting pages, the general prompting best
practices, the migration guide, the Claude Code best-practices and skills docs, the
June 2026 steering post, the skill-authoring best practices, the auto-mode and
long-running-harness engineering posts, and three July 2026 Claude blog posts
(context engineering for the Claude 5 generation, verification loops with skills,
the Fable field guide). ~70 findings, quoted verbatim where load-bearing. Opus 5 is
treated as the primary target since it is Tony's daily driver; Fable 5 deltas are
called out separately.

---

## The verdict up front

**We are in line.** The skill's shape, register, and most of its specific rules match
what Anthropic now publishes, and in several places the official docs contain
recommended snippets that are near-paraphrases of our rules. On Tony's two stated
worries:

- **Bloat:** 101 lines against an official SKILL.md ceiling of 500, a frontmatter
  description well under the 1,024-char cap, references zero levels deep, and a
  register that already matches the Claude 5-generation shift away from
  prescription. Not bloated. A handful of rationale clauses could be trimmed if the
  baseline ever shows drift, listed in Part 3, but nothing warrants a change now.
- **Drift:** the docs' consistent position is that prose never guarantees anything
  (hooks and permissions do), and that fewer, clearer instructions are followed
  better. Our skill already leans on the strongest prose form available (a per-task
  contract) and keeps the rule count low. The one structural upgrade the docs offer
  is a ladder of harder enforcement (/goal conditions and Stop hooks) that v1
  deliberately deferred; the docs now give it concrete mechanisms. Part 4.

One genuine tension exists — the famous "delete your verification scaffolding"
guidance for Opus 5 versus our Step 4 — and it resolves in our favor once you read
the guidance's actual scope. Part 1 walks through it, because it is the thing most
worth understanding before the baseline run.

## Scorecard

| Skill plank | Official 2026 position | Verdict |
|---|---|---|
| Step 1 contract (in scope / not authorized / footprint / out-of-scope) | Specs should be "self-contained: they name the files and interfaces involved, state what is out of scope, and end with an end-to-end verification step" | **Match, near-verbatim** |
| Per-criterion verification named up front | Verification checks the model can run = the #1 Claude Code best practice | Match |
| Step 4 "earn the claim of done" + evidence | "Have Claude show evidence rather than asserting success" | Match |
| Mechanical self-checks (stub grep, manifest diff, suite rerun) | Project-specific deterministic checks explicitly endorsed, packaged in skills | Match |
| Rule 9 report-faithfully | Fable doc's grounding snippet ("if tests fail, say so with the output; if a step was skipped, say that") — "nearly eliminated fabricated status reports" in Anthropic's testing | **Match, near-verbatim** |
| Rules 1/2/5 scope discipline | Opus 5 scope snippet ("Deliver what was asked, at the scope intended… Finish the whole task") | **Match, near-verbatim** |
| Gap protocol ask-line | "check in only when different readings of the request would lead to materially different work" | Match |
| Rule 8 thrash limit of two + fresh context | "After two failed corrections, /clear and write a better initial prompt" | Match |
| Context gate + self-contained contract | "consider starting with a brand new context window rather than using compaction"; models recover state from the filesystem | Match |
| In-session builder, no subagents | Opus 5: damp delegation, "do not use subagents to verify or double-check your own work" | Match (Fable delta noted, Part 5) |
| Never auto-run /signoff | Claude Code v2.1.215 made its own /verify and /code-review user-invoked only | **Match — Anthropic's product moved to our design** |
| Ledger in the build doc | Fable guidance: give the model a memory surface, even a plain .md; field guide recommends a deviations log | Match |
| No stubs rule | Opus 5 "completes full tasks rather than leaving stubs" by default | Redundant-by-default but kept as insurance; see Part 3 |
| Prose blast-radius rules | "'Never do this' cannot be reliably enforced through prompting alone" — hooks | Known gap, deliberate; hardening path in Part 4 |
| 101 lines, goals-not-checklists register | <500-line ceiling; 80%-of-system-prompt-deleted posture; "state what to do rather than narrating how or why" | In line; minor trim candidates in Part 3 |

---

## Part 1 — The verification question, settled

The scariest line in the Opus 5 docs, verbatim: *"Claude Opus 5 verifies its own
work without being told to. If your prompt contains explicit verification
instructions ('include a final verification step for any non-trivial task,' 'use a
subagent to verify'), remove them… The same applies to legacy harness scaffolding
that adds separate verification steps."* Plus, separately: avoid *"double-check
your answer"* and *"re-verify before responding."*

Read precisely, the ban covers three things: open-ended exhortations to verify,
instructions to re-check work already checked, and verification-by-subagent. It
does **not** cover runnable checks, and the same docs keep recommending those
emphatically — the Claude Code best-practices doc's #1 practice is still "give
Claude a check it can run" with a four-rung ladder (in-prompt check → /goal →
Stop hook → fresh-context verifier), and the July 2026 verification-loops post
endorses exactly our kind of deterministic project-specific rule ("Reject any
migration that drops a column without a backfill step").

Anthropic's own resolution of the apparent contradiction is the most useful
finding: they deleted verification guidance from Claude Code's *always-loaded
system prompt* and moved it into *selectively-invoked skills*. Quote: "we moved
verification and code review into their own skills that Claude Code could
selectively call." **A skill is the sanctioned home for verification content.**
The "delete your scaffolding" advice is about always-on context and redundant
passes, not about a per-slice skill that names concrete one-time checks.

Auditing our Step 4 against the banned list:

- "Execute the verification the contract named for each criterion, and record
  what ran and what it showed" — a named, one-time, evidence-producing check.
  Endorsed category.
- The three mechanical self-checks — deterministic, greppable, one pass each.
  Endorsed category.
- We never say "double-check," never say "re-verify," and never tell the builder
  to verify via subagent. The skill's one subagent-verification pathway is
  /signoff, which it is forbidden to run itself — and as of v2.1.215, Claude
  Code's own bundled /verify and /code-review work exactly that way (user-invoked
  only, where the model previously could auto-run them). Our build/signoff gate
  separation is now literally Anthropic's shipped behavior.

**One watch item for the baseline:** Opus 5 will also self-verify natively during
Step 3. The failure mode to look for is compounding — the model running the suite
during the build, then re-running everything in Step 4, then re-running again "to
be sure." If the baseline transcript shows triple-checking, the fix per the docs
is to trim Step 4's framing toward pure bookkeeping ("record what ran") rather
than instruction ("execute the verification"). Don't pre-fix it; measure first.

## Part 2 — Direct validations worth knowing about

These are places where the official docs contain language that could have been
lifted from our skill (they weren't — convergence is the signal):

1. **The contract is the official spec shape.** "The most useful specs are
   self-contained: they name the files and interfaces involved, state what is out
   of scope, and end with an end-to-end verification step that proves the feature
   works." That is Step 1's four bullets, in order.
2. **Rule 9 is Anthropic's tested anti-fabrication snippet.** The Fable doc's
   grounding language ("audit each claim against a tool result… if a step was
   skipped, say that") nearly eliminated fabricated status reports in their
   testing. Our rule 9 and the Method line implement the same thing.
3. **The scope snippet.** Opus 5 docs ship a scope-discipline paragraph including
   "Finish the whole task, and stop short of actions that are clearly beyond what
   was asked" — our rules 1, 2, and 5 cover the same ground, and the official
   ask-line ("only when different readings would lead to materially different
   work") is our clarification-vs-behavior-change distinction in different words.
4. **The thrash number is officially two.** "After two failed corrections, /clear
   and write a better initial prompt incorporating what you learned." Rule 8
   matches, including the fresh-context remedy.
5. **Fresh context over compaction.** The best-practices doc now says prefer a
   brand-new context window and let the model recover state from the filesystem,
   with prescriptive restart steps. Our context gate plus self-contained contract
   plus ledger plus checkpoint commits is that pattern.
6. **One-slice discipline is harness doctrine.** The long-running-agents post:
   one feature at a time from a protected list, status-only edits, verification
   before marking complete, descriptive commits, progress file. Our slice + build
   doc + ledger + checkpoint commits map one-to-one.
7. **In-session builder is the Opus 5 default.** "Do not delegate work you can
   finish yourself… do not use subagents to verify" — our no-subagent-ceremony
   choice, which the July web research had flagged as our biggest divergence from
   community practice, is now the officially recommended posture for Opus 5.

## Part 3 — The bloat-and-drift audit (Tony's question)

**Numbers.** SKILL.md ceiling: 500 lines (we are at 101). Description cap: 1,024
chars (ours ~340, triggers included, key use case first — matching the guidance
that the listing truncates at 1,536 chars). References: guidance says one level
deep max; we have zero. Post-compaction, an invoked skill keeps its first 5,000
tokens; we are well under. On every published number, we pass with room.

**The recurring-cost caveat.** The skills doc notes an invoked skill's body stays
in context for the whole session, so every line is a recurring token cost, and
says to "state what to do rather than narrating how or why." Our skill carries
short why-clauses ("it poisons the inspection that follows," "the polluted
context is the disease," "drift wearing a hard hat"). Strictly applying the
guidance would trim perhaps 8–12 lines. Two reasons not to do it now: the same
2026 posture warns against over-prescription and trusts judgment, and brief
rationale is what lets the model apply a rule to cases the rule didn't enumerate;
and this register is exactly what the signoff A/B validated. Recommendation:
leave as-is for the baseline; trim only if the transcript shows rules being
ignored (the docs' stated symptom of an overlong instruction file).

**Emphasis language.** The docs deprecate "CRITICAL: You MUST" spam but sanction
sparing emphasis. We use one strong marker ("the one unforgivable move") and no
all-caps imperatives. In line.

**The deletion test.** The context-engineering post's standard: delete any rule
the model already follows by default. Two of ours are partially redundant on
Opus 5 — no-stubs (the model "completes full tasks rather than leaving stubs")
and parts of Step 4 (native self-verification). Both stay justified: the rules
also define the *honest-stop alternative* (what to do when the slice can't be
finished), which is not default behavior, and a skill's cost is only paid when
invoked, unlike the system prompt the 80%-deletion posture was aimed at. But this
is the right lens for every future addition: if Opus 5 already does it, the line
doesn't go in.

**Drift.** The bright line across all 2026 docs: prose is advisory, hooks and
permissions are enforcement, and conversation-stated boundaries can be lost to
compaction. Our blast-radius rules are prose by design (v1 open decision 4). Two
mitigations we already have are the strongest available in prose: the per-task
contract (the one prose form with measured scope-holding effect, per the July
research) and the low rule count. The upgrade path when evidence demands it is
Part 4.

## Part 4 — New mechanisms the docs offer (not in v1's design space)

These weren't available or weren't documented when v1 was designed. None require
changing the skill now; all are candidates for the fold after baseline.

1. **Stop hook as the home for the mechanical self-checks.** The official
   verification ladder's third rung: "a Stop hook runs your check as a script and
   blocks the turn from ending until it passes" (model can override after 8
   consecutive blocks). Our stub-grep and manifest-diff are already written as
   mechanical checks — they could graduate from prose to a Stop hook verbatim.
   This is the concrete version of v1's "hooks later" decision.
2. **/goal as a contract enforcer.** A /goal condition is evaluated by a fresh
   model against the transcript ("one measurable end state, a stated check,
   constraints that must not change, optionally 'or stop after N turns'"). The
   Step 1 contract could optionally be distilled into a /goal at build start —
   an independent evaluator holding the scope boundary while the builder works.
   Worth one experiment; not in the skill text.
3. **`disable-model-invocation: true`.** The skills doc recommends it for
   side-effect workflows ("You don't want Claude deciding to deploy because your
   code looks ready" — analogously, deciding to build slice B because A looks
   done). Tradeoff: it would also stop "build slice A" said in natural language
   from loading the skill, forcing explicit /build invocation. Tony's call;
   current behavior (model-invocable, triggered by the description) matches how
   he phrases requests, and the skill's own rules prevent slice-chaining.
4. **The don't-end-on-a-promise clause.** Fable 5 occasionally ends a turn with
   "I'll now run X" without running it. The official one-line fix ("Before ending
   your turn, check your last paragraph…") is a candidate addition **only if**
   /build runs under Fable and the baseline shows it; on Opus 5 it's not a
   documented failure mode, and our stops are deliberate by design.

## Part 5 — Opus 5 vs Fable 5: the skill is model-agnostic, mostly

The two prompting pages diverge exactly on axes our skill touches, so if Tony
switches /build between models, these deltas matter:

| Axis | Opus 5 (daily driver) | Fable 5 |
|---|---|---|
| Verification | Remove verify instructions; no verify-subagents | Make self-verification *explicit* on long runs, fresh-context verifier subagents |
| Subagents | Damp; cap; never for verification | "Use subagents frequently," async, long-lived |
| Prescriptiveness | De-escalate imperatives | Skills for prior models "often too prescriptive… can degrade output" — review and remove |
| Failure quirks | Scope expansion, over-verification, over-delegation | Early stopping (text-only intent), context anxiety, unrequested-but-adjacent actions |

The skill as written sits on the Opus 5 side of every divergence, which is
correct for the daily driver. The Fable deltas mostly don't bite at our scale: a
slice is deliberately a short run, not the hours-long autonomous work Fable's
verifier-subagent guidance targets. One Fable-specific audit passed: nothing in
our skill instructs the model to echo or transcribe its internal reasoning (which
can trigger Fable's `reasoning_extraction` refusal in skills) — the Method line
reports actions and evidence, not reasoning.

## Part 6 — Baseline watch list (what these docs say to measure)

1. Over-verification: does the builder re-run checks it already ran? (Part 1.)
2. Rule adherence under length: any rule ignored → the trim list in Part 3
   activates before any new rule is added.
3. Scope: any unrequested addition surviving to the diff → tighten rule 1 toward
   the official snippet's exact wording.
4. Narration volume between tool calls → the official communication snippet is
   the fix if needed; not pre-added.
5. Self-check integrity: if the stub-grep or manifest-diff gets skipped or
   narrated-but-not-run, that's the evidence that graduates them to a Stop hook
   (Part 4.1).

## Sources (all official Anthropic, fetched 2026-08-01)

- platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5
- platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- platform.claude.com/docs/en/about-claude/models/migration-guide (Opus 5 / Fable 5 sections)
- platform.claude.com/docs/en/build-with-claude/effort
- code.claude.com/docs/en/best-practices · /skills · /memory · /goal · /workflows · /permission-modes · /context-window
- platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more (2026-06-18)
- claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models (2026-07-24)
- claude.com/blog/building-verification-loops-in-claude-code-with-skills (2026-07-22)
- claude.com/blog/a-field-guide-to-claude-fable-finding-your-unknowns (2026-07-03)
- anthropic.com/engineering/claude-code-auto-mode (2026-03-25)
- anthropic.com/engineering/effective-harnesses-for-long-running-agents (2025-11-26)
- anthropic.com/engineering/effective-context-engineering-for-ai-agents (2025-09-29)
