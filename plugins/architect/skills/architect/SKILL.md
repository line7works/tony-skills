---
name: architect
description: The drawings step of the build loop — one interview after /precon that produces the architecture-and-delivery doc the downstream skills consume, plus a visual of what was decided. STRICTLY user-invoked, only when Tony types /architect; never auto-invoke, suggest-invoke, or trigger from conversation shape, no matter how architecture-shaped the discussion looks.
---

# Architect

The station between `/precon` and everything downstream. /precon settles what an idea is; /sunrise provisions and /blueprint slices. Until now nobody drew the building in between, so structure got decided implicitly — by /blueprint while slicing, or by /sunrise's archetype template at the moment of least information. `/architect` is that drawings step: one interview that produces one architecture doc, the least structure that serves a named first user's walkthrough without becoming demolition later. It exists so the AI's first plausible proposal never ships unexamined.

**The spine.** Decisions at full-vision quality, construction at MVP quantity. Deciding is free and provisioning is not, so the one-way doors — language, database kind, repo shape, data shapes, platform — are settled up front for the whole vision, while their construction waits for the walkthrough that needs it. Two passes run as one negotiation: delivery (who first touches this, by when, doing what) and architecture (what is the least structure that serves exactly that). The tension between them is the product.

**The one unforgivable move is the nod:** Claude proposes one structure and Tony agrees. Step 2 forces genuinely distinct candidates into the open with what each assumes and what each makes expensive later, every run, or the interview did not happen.

This skill runs only when Tony types /architect. It writes a doc and a visual; it never provisions anything, and it never invokes another skill.

## Step 1 — The input gate

The input is a /precon scope doc. Find it in this order:

1. The path given in the invocation.
2. Otherwise, a glob over precon's two homes: `<repo>/docs/*-scope.md` when invoked inside a repo, plus `~/Documents/*-scope.md`. Match candidates to the project by their `Intent:` lines against the project Tony is talking about. More than one plausible match is listed and asked as a plain-text numbered question, never silently picked. The glob is best-effort — a repo-owned scope doc is only visible from inside that repo or by path.

**Docless.** Invoked with no scope doc found, the skill stops and opens a discussion on why it is being run without a precon doc — a conversation gate, not a silent refusal. The run proceeds only when that discussion lands on a reason; the reason is recorded in the header of the architecture doc. A docless run takes the current discussion as its input, and its `<slug>` is the project's working name, settled in that same discussion.

**The property line.** Lookups during a run are the repo (if any), the project's existing docs, and Claude's own knowledge. No web access, no research subagents, no research documents. A factual unknown that genuinely needs outside checking is not looked up and not guessed: it becomes a marked line in the architecture doc — `NEEDS CHECK: <what>` — for Tony to resolve.

## Step 2 — The exit ramp

The first question of every interview: **is there a system here at all?**

A single static page is not a system. When the answer is that small — no server, no data, nothing remembered — the interview ends after this one question. The run still writes a tiny architecture doc (a few lines: static page, no system, nothing to provision beyond a repo, which this skill still does not create), still renders the visual, and still makes the blind-review offer when a scope doc exists. "No doc" stays reserved for ideas that never saw /architect.

## Step 3 — The interview

Three steps, in this order, run as one negotiation. Questions are plain-text, numbered, each with a ➡️ recommendation, so Tony can answer by number. Facts the property can answer are looked up, never asked.

**Step 3.1 — the walkthrough target (delivery pass).** Three things, all concrete:

- A named real person. Never "users". The first human who is not Tony to touch the built thing.
- The date of the walkthrough — the dated session where that person actually uses it.
- What that person must be able to do in that session, as a short list.

**Step 3.2 — candidate structures (architecture pass).** Put 2–3 genuinely distinct candidate structures on the table before any is chosen. Distinct means differing in at least one one-way-door category — platform, storage, repo shape, language, data shape, or any other one-way-door category the project surfaces — never variations of one shape. For each candidate: what it assumes, and what it makes expensive later. Then grill every candidate against the walkthrough target with the razor: **every component must point at a walkthrough requirement or it is cut from v0.** No server unless something needs a server; no database unless something must be remembered. Tony picks. The pick and each rejected candidate's one-line why go in the run log.

**Step 3.3 — the one-way-door check (architecture pass).** Bring the full vision in, for one purpose only: verify that nothing in v0 blocks it. Walk the checklist — language, database kind (storage), repo shape, data shapes, platform — as the floor, not a cap; add any other door the project has. One-way decisions are made at full-vision quality now. Everything else stays two-way and undecided. Banked decisions are recorded, not provisioned: "becomes Postgres when scores go remote" is a line in the doc, not a database.

**The narrowness guardrail.** The interview stays short — about three answers plus the sorted scope. If it grows into heavy ceremony it delays the MVP the skill exists to accelerate. When a thread runs long, record what is settled and move on.

## Step 4 — The architecture doc

One living doc per project, never a fork. Its home is beside the precon scope doc: `<repo>/docs/<slug>-architecture.md` when the scope doc is repo-owned, `~/Documents/<slug>-architecture.md` otherwise, where `<slug>` is the scope doc's slug. A docless run's doc goes to `~/Documents/<slug>-architecture.md` unless the gate discussion named a repo. Moving the doc between homes is Tony's (or the future /sunrise rework's), never this skill's.

The format is load-bearing — /sunrise will provision exactly what the poured-concrete list names, and /blueprint will slice from the v0 drawing with the user-touchable slice up front — so keep it exact:

```
# <Project> — architecture (<date of first run>)

Scope doc: <path> | Docless: <the reason the gate discussion landed on>
Artifact: <private artifact URL, recorded after the first publish>

## Walkthrough target
Who: <named real person>  ·  When: <date>  ·  Must be able to: <short list>

## v0 drawing
Components: <what exists — one line each>
Data flow: <plain prose — what talks to what>
Diagram: <one simple diagram — ASCII or a mermaid block>

## Poured concrete (one-way doors)
- <category> — <decision> — <why it is one-way>

## Deferred
- <banked decision or deliberately-not-built item> — door stays open because <line>

## Run log
### Run <N> — <date> — trigger: <first run | idea blossomed | new precon | changed direction | ...>
Step 1 (walkthrough target): <what was settled>
Step 2 (candidates): <the 2–3 candidates in one line each; chosen: <which>; rejected: <candidate> — <one-line why>>
Step 3 (one-way doors): <what was settled>
Changed this run: <what changed vs the prior run, or "first run">
```

Four required parts, always present: the walkthrough target, the v0 drawing (component list + plain-prose data flow + one simple diagram), the poured-concrete list (the one-way decisions — one list, two names), and the deferred list (banked decisions plus deliberately-not-built items, each with a line confirming its door stays open). The exit-ramp form is the same skeleton with a few lines in it.

**Re-runs.** When the idea blossoms or changes — possibly after a fresh /precon — a new run continues the same doc: a new `### Run <N>` block in the run log with the date, the trigger, what changed, and the three steps in the order taken; superseded decisions elsewhere in the doc are struck through (`~~like this~~`), never deleted. The trail is the point: it ran once, and now it runs again because something changed.

## Step 5 — The visual

Every run ends by rendering what was decided — the systems chosen and what each does or provides for the project — as an HTML page written beside the doc as `<slug>-architecture.html`, and published as a **private** Claude Artifact via the Artifact tool. The page follows that tool's contract: a page body only (no doctype, html, head, or body wrapper), a `<title>` at the top, and a favicon on the first publish. The Artifact tool requires loading the `artifact-design` skill before writing the page; that harness preflight is not a skill invocation in this file's sense.

Same URL across runs: the first publish records the artifact URL in the doc's `Artifact:` line; a re-run reads that artifact (the tool's read action, by URL) before republishing to it; a re-run that finds no recorded URL publishes fresh and records the new one. The visual is a projection re-rendered from the doc each run — the markdown stays the record.

The visual's design is deliberately unspecified and gets established over time, run by run. Keep the first version plain. Do not build a design system, and never publish it anywhere public — not the arcade, not any other host.

## Step 6 — The blind review

Only when the run had a precon scope doc: after the doc and visual are done, ask Tony once, as one plain-text question, whether he wants an outside-model review. A docless run gets no offer — there is no brief to send — and the report says so.

On his word in this run, and only then:

- The external model receives the precon scope doc ONLY. Never Claude's architecture doc, never chat context, never this session's reasoning. It gets the brief fresh, exactly as Tony ruled: "the model reviewing it doesn't get the Claude input."
- The instruction it receives is fixed, verbatim: **"You are the architect. Read the attached precon scope doc and return your own full architecture-and-delivery take for it: the walkthrough target, a v0 drawing (component list, plain-prose data flow, one simple diagram), the poured-concrete list of one-way decisions, and the deferred list. You have no other input; do not ask for any."**
- Transport is the codex MCP (`mcp__codex__codex`) with the model pinned by reference to jpb's preflight in `~/Developer/tony-skills/plugins/jpb/skills/jpb/SKILL.md` (`gpt-5.6-sol` at time of writing; if that pin moves, the reference wins). A different model on Tony's pick for this run substitutes for the pinned one — it never adds a second reviewer. There is no panel.
- The transport guards are jpb Judge G's, plus the payload rule above: `base-instructions` = the fixed instruction, `prompt` = the scope doc text, `sandbox: "read-only"`, `config: {"web_search": "disabled"}`, and `cwd` = an absolute, empty directory created fresh for this run.
- The take is saved verbatim, before any triage, to `~/Documents/architect-reviews/<slug>-review-<YYYY-MM-DD>.md`. Creating `~/Documents/architect-reviews/` on the first blind review, and creating the run's empty cwd, are the only two directory creations this skill ever makes.

Then the comparison: walk Tony through every disagreement between the two takes — at minimum components built vs cut, structure, one-way-door calls, and deferrals — one at a time, and he rules each in discussion. The architecture doc changes only where he rules. Nothing merges silently, and the review file itself is never edited.

## The rules

1. **User-invoked only.** /architect runs when Tony types it, never because the discussion looks ready for drawings.
2. **The scope doc is the input.** Without one, the gate discussion must land on a recorded reason before anything else happens.
3. **The exit ramp is real.** "Is there a system here at all?" comes first, and a "no" ends the interview in a minute — with a tiny doc, not no doc.
4. **Candidates or it didn't happen.** 2–3 genuinely distinct structures, each differing in a one-way-door category, with assumptions and later costs, before Tony picks.
5. **The razor cuts.** Every v0 component points at a walkthrough requirement or it is out.
6. **Decide for the vision, build for the walkthrough.** One-way doors settled at full-vision quality; everything else two-way; banked decisions recorded, never provisioned.
7. **Doc and visual only.** No repos, databases, hosting, or accounts; nothing installed; no other loop skill invoked. Execution belongs to /sunrise.
8. **The property line is absolute.** Repo, project docs, and Claude's own knowledge. Outside unknowns become `NEEDS CHECK` lines for Tony.
9. **One living doc.** Re-runs continue it with a run-log block and strikethroughs. Never a fork, never a rewrite of history.
10. **Blind means blind.** The reviewer gets the scope doc only, on Tony's word in this run only, and every disagreement is Tony's to rule.
11. **Keep it short.** About three answers plus the sorted scope. Ceremony that delays the MVP is the failure mode.

## Output

Report in chat when the run ends:

```
ARCHITECT: <project>
Doc: <path>
Artifact: <private URL>
Run: <N>
Counts: components in v0 N · poured-concrete decisions N · deferred items N
Review: declined | not offered — docless | done at <review file path>
Next: point /sunrise at the doc to provision exactly what it lists, and /blueprint at it to slice with the user-touchable slice up front (hand-pointed until those reworks land).
SKILL NOTE: <only when a rule was worked around, reinterpreted, or excepted — what and why; omit otherwise>
```

When executing this skill required working around, reinterpreting, or excepting one of its rules, the report carries one line marked `SKILL NOTE:` — what and why, addressed to the skill's author, not the project; a clean run carries none.

## What NOT to do

- Don't auto-invoke, suggest-invoke, or trigger from conversation shape. Tony types it or it does not run.
- Don't proceed docless without the gate discussion landing on a reason that is recorded in the doc's header.
- Don't provision anything — no repos, databases, hosting, accounts, or installs — and don't invoke any loop skill (/sunrise, /blueprint, /precon, /jpb, or any other).
- Don't leave the property — no web, no research subagents, no research documents. Mark the unknown for Tony instead.
- Don't send anything to another model without Tony's explicit word in that run.
- Don't show the external reviewer Claude's work — the scope doc only, cold.
- Don't merge review differences silently — Tony rules each one, and the doc changes only where he ruled.
- Don't skip the candidates and present one proposal for Tony to nod at.
- Don't fork a second architecture doc — re-runs continue the one living doc.
- Don't delete or rewrite run-log history — strike through, append, never erase.
- Don't over-spec the visual — plain first, evolved run by run, no design system.
- Don't publish the visual anywhere public — the arcade included. Private Artifact only.
- Don't use harness question UI (AskUserQuestion) for the interview — plain-text numbered questions only.
