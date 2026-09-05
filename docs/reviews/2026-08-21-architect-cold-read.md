# Architect — cold reads (2026-08-21)

Two readers, both approved by Tony this run: a fresh zero-context Claude
subagent, and GPT (`gpt-5.6-sol` via codex MCP, `web_search: disabled`,
read-only sandbox, neutral cwd). Both received the scope doc only.

## Summary — what was taken, what was left behind

The readers converged hard on three genuine gaps, which went to Tony as
Round 3 questions (surfaced): the exit-ramp artifact, whether a docless run
may proceed after the gate discussion, and the v0 drawing's format. A cluster
of naming/clarity confusions (walkthrough, date, poured concrete vs one-way
doors, brief vs scope doc, pass-vs-step mapping, external-ask timing,
substitute-vs-additional model, slug derivation) were absorbed into the scope
doc as new ledger lines — clarifications of what the discussion already
meant, no new rulings invented. Everything else — exact interview questions,
output templates, comparison formats, failure handling, acceptance tests —
is blueprint-altitude build detail and was left downstream with reasons
below. The largest single theme, "the surrounding pipeline is assumed
knowledge," was mostly left downstream: the doc's audience is Tony and
/blueprint running on this machine, where every referenced skill's SKILL.md
is on the property.

## Disposition

**Surfaced (put to Tony, Round 3):**
- Exit-ramp outcome — does a static-page run still produce a doc? (both readers)
- Docless gate — after the "why docless" discussion, can the run proceed? (both readers)
- v0 drawing format — prose, diagram, component list? (both readers)

**Absorbed (folded into the scope doc as ledger lines):**
- "Walkthrough" and its "date" undefined (both) → new decided line defining both.
- Poured-concrete list vs one-way doors overlap (both) → new assumed line: one list, two names; five categories are floor not cap.
- "Brief" vs "precon scope doc" two names for one input (both) → new decided line unifying.
- External-review ask: when, and substitute-vs-second-reviewer ambiguity (both) → one decided line (asked once, end of every run) + one assumed line (substitute, never additional).
- `<project>` slug derivation (both) → new assumed line: precon doc's slug.
- Two passes vs three steps mapping (both) → new assumed line: delivery = step 1, architecture = steps 2–3.
- Vision-up-front vs razor-cuts-to-v0 tension (GPT) → already answered by the existing "decisions at full-vision quality, construction at MVP quantity" line; no edit needed.

**Left downstream (blueprint-altitude, with why):**
- Undefined pipeline terms and process jargon (/precon, /sunrise, /blueprint, /jpb, spine, altitude, frontier, loop-skill convention, precon-cold-reads pattern) — the doc's consumers (Tony, /blueprint on this machine) hold that context; every referenced SKILL.md is on the property for the builder to read.
- Exact interview questions and follow-up rules; when the interview has enough to stop.
- Output doc template: exact headings, required fields, level of detail per part.
- Candidate-structure presentation format (table vs prose), rejected-candidate retention, comparison dimensions, meaning of "expensive."
- Disagreement detection/presentation format for the external review; where the comparison is stored; how Tony's rulings are recorded and who applies edits.
- External-review failure modes: unavailable model, timeout, malformed response; filename collision policy.
- Narrowness-guardrail enforcement mechanism (guidance vs hard cap).
- Whether the walkthrough date is enforced; what happens when no credible person/date exists (the interview surfaces it; handling is build detail).
- What exactly /sunrise reads as provisionable and how items are marked; what /blueprint treats as the user-touchable slice (both are the *other* skills' rework scope, explicitly out of scope here).
- What artifact set "building /architect" means (SKILL.md, assets, tests) and acceptance tests — /blueprint's job to spec.
- Whether /architect reads the findings doc — build detail.
- "Next: /blueprint when ready" vs sunrise-before-blueprint confusion — the footer is the precon template referring to building THIS skill via /blueprint; the product pipeline ordering lives in the decisions and is unambiguous there.
- Codex MCP / jpb SKILL.md / pinned model resolution — recorded convention on the property; builder reads it there.
- What counts as Tony's "explicit word" for an external send — same standard every skill uses; conversational confirmation in the run.

---

## Reader 1 — fresh Claude subagent (verbatim)

Read complete. Findings as a cold reader with no context, in two lists.

### 1. Unclear or confusing

- **The whole surrounding pipeline is assumed knowledge.** `/precon`, `/blueprint`, `/sunrise`, `/sunset`, `/jpb`, `/architect` are referenced throughout ("Runs after /precon settles scope and before anything is provisioned or sliced") but never defined. A reader cannot tell what any of these skills do, what a "precon scope doc" contains, or what "provisioned or sliced" means concretely.
- **"the missing drawings step in the build pipeline"** (line 3) — which pipeline? "Drawings" is a metaphor never cashed out: is the output prose, a diagram, a checklist?
- **"the least structure that serves a named first user's walkthrough without becoming demolition later"** (intro) — "walkthrough" is used as a term of art throughout ("walkthrough target", "walkthrough requirement") but is never defined. Is it a demo? A user session? A scripted scenario?
- **"the 2026-08-17 Occam's razor idea"** (intro, and line 16 "Tony's Occam's razor thread") — the doc says this idea became "the blade," but the idea itself is never stated beyond the one clause on line 16. Line 16 is the criterion, but the doc leans on an off-doc "thread" for its meaning.
- **"the tension is the product"** (line 13) — I can guess this means the delivery-vs-architecture negotiation is the point, but it's aphorism, not spec.
- **Two passes vs. three steps** — line 13 says "two passes: delivery + architecture," line 15 lists a three-part interview order (walkthrough target, architecture grilling, one-way-door check). How the third step maps onto the two passes is not stated.
- **"named real person, date, what they must be able to do"** (line 15) — date of what? The walkthrough? A deadline? Unspecified.
- **"Decisions at full-vision quality, construction at MVP quantity"** (line 18) — cryptic compression. And "the wrong-language/wrong-DB challenge" is a reference to a conversation not in the doc.
- **"banked decisions recorded but not built"** (line 18) — defined only by one example ("becomes Postgres when scores go remote"). Where and in what form are they recorded — just the deferred list, or somewhere durable?
- **"poured-concrete list"** (line 20) — undefined term. Presumably the one-way doors decided, but the doc never says so, and its relationship to line 19's one-way-door list is left to inference.
- **"v0 drawing"** (line 20) — format unknown. Text description? Mermaid diagram? Component list?
- **"the user-touchable slice up front"** (line 21) — a /blueprint slicing convention the reader doesn't have.
- **Parenthetical provenance is opaque** — "(Round 1 Q1)", "(Round 2 Q2)", "(demote-don't-demolish discussion)", "(discussion of Tony's three 'what if wrong X' fears)" all cite an interview transcript the reader cannot see. The three fears themselves are never listed, yet line 19's one-way-door set was apparently derived from them.
- **"brief" vs. "precon scope doc"** — line 26 says the external model "gets the brief fresh"; line 32 says it receives "the precon scope doc ONLY." Probably the same thing, but two names for one input in a spec invites doubt.
- **"the loop-skill convention"** (line 28), **"every skill at this altitude follows the /precon rule"** (line 29) — convention and rule both undefined; "altitude" is unexplained jargon.
- **"~three answers + sorted scope"** (line 30) — "sorted scope" is unclear. Also "front of spine already crowded" — "spine" is never introduced.
- **"same as /precon's exit test — GPT via the codex MCP, pinned model per jpb's SKILL.md"** (line 34) — three nested references: an exit test in another skill, an MCP transport, and a model pin living in a third skill's file. The actual model is unknowable from this doc. "another model on Tony's pick per run" is also grammatically ambiguous (a second model in addition to GPT, or an alternative?).
- **"mirrors the precon-cold-reads pattern"** (line 35) — undefined pattern.
- **"frontier emptied after Round 2; cold read pending Tony's pick"** (line 44) — "frontier" is process jargon; "Tony's pick" of what is unstated.
- **Exit ramp outcome** (line 23) — "a single static page ends the interview in a minute" — ends it with what result? Does a doc still get written, or does the skill just stop?

### 2. Questions I'd need answered before building

- What is the exact structure/template of the four-part output doc — headings, required fields, level of detail expected in the "v0 drawing"?
- What are the actual interview questions (or question shapes) for each of the three steps? The doc specifies order but not content.
- How are the "2–3 genuinely distinct candidate structures" (line 17) produced and presented — free-form prose, a fixed comparison format, required fields ("what each assumes and what each makes expensive later" suggests a table)?
- What exactly does "each confirmed to keep its door open" (line 20) mean operationally — a stated check per deferred item, or just an assertion?
- What is the walkthrough "date" (line 15) and does the skill enforce anything against it?
- In the exit-ramp case (line 23), what artifact if any is produced, and does the run end entirely or hand off somewhere?
- Where does `<project>` in `~/Documents/<project>-architecture.md` (line 25) come from — the precon doc's name, or asked in the interview?
- External review (line 32): how are "the two docs' disagreements" identified and presented — by whom, in what format? After Tony rules, is the review file annotated, or only the architecture doc edited?
- Which exact model is "pinned per jpb's SKILL.md" (line 34), and what is the concrete send mechanism and prompt given to the external model?
- Line 26 says the skill "ASKS Tony whether he wants an outside-model review" — asked once at the end of every run, or under some condition?
- Does /architect read the findings doc named on lines 37/42, or is it purely provenance for humans?
- The docless-invocation gate (line 33): after the "discussion on why," can the run proceed without a precon doc, and if so with what input?
- What enforces the narrowness guardrail (line 30) — a hard question cap, or just guidance in the skill text?
- Is the one-way-door set fixed to the five named categories (line 19: language, database kind, repo shape, data shapes, platform), or open-ended per project?
- What does "sorted scope" (line 30) refer to — a step, an output section, or the precon doc's scope list?

---

## Reader 2 — GPT `gpt-5.6-sol` via codex MCP, web_search disabled (verbatim)

1. **Unclear or confusing**
   - "**/precon**," "**/sunrise**," "**/blueprint**," and "**/sunset**" are referenced without defining their inputs, outputs, or current behavior.
   - "**One skill, two passes… run as one negotiation**" does not define what separates the passes or how the negotiation proceeds.
   - "**named first user's walkthrough**" is ambiguous: it is unclear how specific the person must be or what constitutes a walkthrough.
   - "**architecture-and-delivery doc**," "**v0 drawing**," and "**full architecture take**" are not defined sufficiently to determine their required technical detail.
   - "**the least structure… without becoming demolition later**" and "**demote-don't-demolish**" are principles, but their operational tests are unspecified.
   - "**One-way doors (language, database kind, repo shape, data shapes, platform)**" treats these categories as inherently irreversible without defining the threshold for a one-way door.
   - "**decided for the vision up front**" conflicts or at least creates tension with "**every component must point at a walkthrough requirement or it's cut from v0**"; it is unclear how much full-vision design belongs in the document.
   - "**force 2–3 genuinely distinct candidate structures**" does not define "genuinely distinct" or whether the exit-ramp case is exempt.
   - "**what each makes expensive later**" does not say whether expense means engineering effort, money, operational burden, migration risk, or all of these.
   - "**poured-concrete list**" is unexplained and may overlap with the one-way-door decisions.
   - "**deferred list (banked decisions + deliberately-not-built, each confirmed to keep its door open)**" does not distinguish a banked decision from a deferred component or specify how openness is confirmed.
   - "**/sunrise provisions exactly what it lists**" leaves "it" ambiguous: the complete architecture document, the v0 drawing, or some explicit provisioning section.
   - "**/blueprint slices from it with the user-touchable slice up front**" does not define a slice or "user-touchable."
   - "**a single static page ends the interview in a minute**" is unclear about whether `/architect` still creates a document, and which sections remain required.
   - "**the interview stays short (~three answers + sorted scope)**" does not identify the three questions/answers or explain "sorted scope."
   - "**front of spine already crowded**" is an unexplained metaphor or reference.
   - "**like /precon**," "**matches the loop-skill convention**," "**follows the /precon rule**," "**same interim rule /precon states**," and "**mirrors the precon-cold-reads pattern**" rely on conventions not contained in this document.
   - "**same as /precon's exit test — GPT via the codex MCP, pinned model per jpb's SKILL.md**" depends on an unspecified MCP, an unidentified `jpb`, and an external `SKILL.md`.
   - "**another model on Tony's pick per run**" is unclear about whether this is an alternative to GPT or an additional review.
   - "**if yes, the external model does NOT get Claude's output — it gets the brief fresh**" is later narrowed to receiving "**the precon scope doc ONLY**"; it is unclear whether the "brief" means exactly that document.
   - "**saved verbatim to a file**" conflicts with the later comparison requirement unless it is clear whether the comparison is a separate artifact.
   - "**Tony rules each one in discussion**" does not define how disagreements are identified, presented, or recorded.
   - "**the architecture doc changes only where he rules**" does not specify whether Claude makes those edits or Tony does.
   - "**strictly user-invoked, never auto-triggered**" is marked assumed, while several other decisions are also only assumed despite "**Open: none**."
   - "**Next: /blueprint when ready**" is ambiguous because the document also says `/sunrise` consumes the output before `/blueprint`.
   - The cited handoff and research files are essential references, but the scope does not summarize the requirements within them.

2. **Questions required before building**
   - What exact artifact is being built: a Claude skill definition, supporting scripts, prompt templates, schemas, tests, or some combination?
   - What are the relevant interfaces and current contracts of `/precon`, `/sunrise`, and `/blueprint`?
   - What is the exact shape or minimum required content of the precon scope document?
   - How is a project name derived for `~/Documents/<project>-architecture.md` and the review filename?
   - What should happen if the target output or review file already exists?
   - What exact questions should `/architect` ask, and which answers count toward "~three answers"?
   - Can the interview ask follow-ups, and what determines when it has enough information to stop?
   - What does "is there a system here at all?" mean, and what criteria classify something as a single static page?
   - In the static-page exit case, what file is produced and which of the four document parts are included?
   - What exact headings, fields, and level of detail are required in each of the four output parts?
   - Is the "v0 drawing" prose, a diagram, a component inventory, data flows, deployment topology, repository layout, or all of these?
   - Which architecture categories must always be evaluated beyond the listed one-way doors?
   - How should the skill distinguish one-way decisions from two-way decisions?
   - How should it prove or record that a deferred choice keeps its door open?
   - Must every run produce exactly 2–3 candidates, including trivial projects?
   - What dimensions must be compared across candidates, and how should assumptions and future expense be documented?
   - Who selects the final candidate, and must the rejected candidates remain in the final document?
   - How should the walkthrough target be specified: identity, date format, actions, success criteria, environment, and constraints?
   - What happens if there is no named real person or no credible walkthrough date?
   - What does "sorted scope" contain, and how is it divided among v0, banked decisions, and deliberately-not-built items?
   - What precisely should `/sunrise` provision from the document, and how should provisionable items be marked?
   - What precisely should `/blueprint` treat as the first "user-touchable slice"?
   - When invoked without a precon document, what discussion should occur, and what outcomes allow the run to proceed or stop?
   - How is the precon document supplied or selected, and how is its existence validated?
   - Which assumptions in this scope are approved requirements versus placeholders that still need confirmation?
   - What Codex MCP server/tool and exact pinned model should be used for external review?
   - Where is `jpb's SKILL.md`, and which instructions from it govern this build?
   - Is Tony's per-run model a substitute reviewer or a second reviewer, and which models are permitted?
   - What exact phrase or confirmation counts as Tony's "explicit word" authorizing an external send?
   - Is any information besides the raw precon document permitted in the external-model prompt, including instructions defining the requested output?
   - How should external-review failures, unavailable models, timeouts, or malformed responses be handled?
   - What filename date format and collision policy should review files use?
   - How are disagreements between the two documents detected and represented side by side?
   - Where is the disagreement comparison stored, if anywhere?
   - How is Tony's ruling on each disagreement recorded, and who applies the resulting edits?
   - Does the external-review process occur within the same `/architect` invocation or through a later invocation?
   - What completion signal should the skill emit, and what downstream path should it report given the conflicting pipeline references?
   - What acceptance tests demonstrate that the skill is complete and conforms to this scope?
