---
description: Audit for LLM→deterministic-code conversion opportunities (report only)
argument-hint: [session|repo]
---

# Determinism audit

You are auditing for opportunities to convert LLM-driven processes into
deterministic code. Report only. Change nothing.

SCOPE: $ARGUMENTS

If SCOPE above is blank, infer it: if this conversation already contains
substantive work (tool calls, edits, generated artifacts), treat SCOPE as
`session`; otherwise treat it as `repo`. State which you chose in one line
before the report.

## The principle
LLM calls are non-deterministic and cost tokens every run. Deterministic
code costs tokens once (to build) and then runs forever: free, fast, and
identical output every time. Your job is to find work an LLM currently does
repeatedly that a script, hook, cron job, or CI step could do instead. The
best conversions are "jigs": a script does the mechanical part (gathering,
diffing, formatting) and the LLM is only used, if at all, for the judgment
part.

## Scope rules
- If SCOPE is "session": audit the work we just did in this conversation.
  Every multi-step tool sequence you ran, every fact you re-derived by
  reading files or running commands, every artifact you generated. For each,
  ask: if we do this again next week, which part should be a script?
- If SCOPE is "repo": audit this repo and its surrounding workflow. Look in:
  app source (runtime LLM/API calls), scripts/, CI configs, agent and skill
  definitions (.claude/, AGENTS.md, CLAUDE.md, commands/), cron or scheduled
  jobs, docs and READMEs describing manual or recurring rituals, and recent
  git history for artifacts that get regenerated over and over.

## What to hunt for
1. Polling and monitoring: anything that "checks X" on a schedule or on
   request. Deterministic version: script fetches, diffs against last-known
   state, alerts only on change.
2. Fact re-derivation: flows where the LLM gathers the same kinds of facts
   each time (git log, diff stats, open PRs, DB state, file inventories)
   before producing output. Deterministic version: a gather script emits one
   digest; the LLM only writes the narrative.
3. Mechanical sequences: fixed multi-step procedures run via agent tool
   calls (scaffolding, deploys, syncs, env setup, file generation from
   templates). Deterministic version: one script; the LLM only picks inputs.
4. Rule-based computation hiding in prompts: classification, parsing,
   validation, extraction, or math done by an LLM where the rules are
   actually fixed. Deterministic version: plain code, or a small locally-run
   trained model for fuzzy pattern-matching at scale.
5. Token spend inside the product: app features that call an LLM per request
   where the same input always wants the same output. Deterministic version:
   precompute, cache, or replace with code.
6. Format rituals: prompts saying "only output X" or "be concise", retry
   loops to coax structure. Deterministic version: code builds the
   structure; the LLM fills only the free-text slots.

## What NOT to flag
- Genuinely fuzzy work: judgment, taste, design review, novel summarization,
  anything where the input shape varies unpredictably.
- One-offs that won't recur.
- Conversions where brittleness costs more than the tokens saved (e.g.
  scraping a page that changes layout weekly). Name the trade-off honestly
  instead of recommending it.

## Report format
A ranked punch list. For each item give:
- **Name** + where found (file paths, or the step in our session)
- **Today:** what happens now and rough cost per run (tool calls, tokens,
  minutes)
- **Convert to:** PURE SCRIPT (zero tokens) | JIG (script gathers, LLM
  finishes) | KEEP LLM (say why)
- **Sketch:** the deterministic version in 2-3 lines: language, trigger
  (hook / cron / CI / manual), inputs, outputs
- **Build cost vs payoff:** one line ("30 min to build, saves ~N tokens per
  run, runs daily")

End with the top 3 quick wins (highest frequency x lowest build cost), plus
anything you examined and deliberately left non-deterministic, with one
sentence on why. If nothing is worth converting, say exactly that. Do not
pad the list.
