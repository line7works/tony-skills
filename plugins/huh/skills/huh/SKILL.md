---
name: huh
description: Re-explain the pending question, finding, or decision in plain language as a simple list, ending with a recommendation. Use when the user invokes /huh, says "explain what you're asking", "I don't understand the question", "say that simply", or pastes back a confusing finding they need to weigh in on. A bare "huh" as a casual reaction ("huh, ok do it") is not a trigger; only confusion about a pending question is.
---

# huh — re-explain what I just asked you

Sole job: take the thing Tony didn't understand and restate it so he can
decide. Never add new analysis, change the question, or start the work —
the turn ends waiting for his answer.

## Target

1. Text pasted or quoted with the invocation → explain that.
2. Otherwise → the most recent question, finding, or decision point put
   to Tony in this conversation.
3. Nothing pending and nothing pasted → say so in one line and stop.

## Output — always this exact shape

One block per decision. A target holding several independent decisions
gets the full block repeated for each, numbered (*Question 1 — ...*),
with a single opening sentence naming how many decisions there are.

**What I'm asking:** one sentence, plain words. When the target is a
finding rather than a question, the header is **What this means:**
instead — one sentence on what the finding means for him.

**Your options:**
- **Option name** — what choosing it means in practice, one or two plain
  sentences. What it costs or risks, if anything.
- (repeat per option; a yes/no question gets a Yes bullet and a No bullet)

**My pick:** which option and why, in one or two sentences, so "do that"
is a complete answer.

A purely informational target with nothing to decide gets no options and
no pick: **What this means** plus one line saying no decision is needed.
Never invent options to fill the shape.

## Language rules

- No jargon, no codenames, no abbreviations from earlier in the thread.
  Any term that must appear (a file, a flag, an acronym) gets a plain
  gloss in the same breath.
- Short sentences. One idea per bullet. No hedging chains.
- If the concept is abstract, map it to construction terms (foundations,
  framing, rough-in vs finish, inspections) — Tony's default mental model.
- Do not restate the original confusing text; replace it.

## After answering

Stop. Do not proceed with any option, even the recommended one, until
Tony picks. His reply ("do that", an option name, or something else)
resolves the ORIGINAL question — carry it back to that context and
continue the work there.
