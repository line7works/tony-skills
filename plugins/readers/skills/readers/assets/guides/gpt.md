# Prompting guide — the GPT rows (`gpt-astra`, `gpt-sol`)

Documentation for mandate authors: the callers that offer a GPT row (precon, architect, inspect, vertical, jpb) and Tony in the direct form. Nothing in this file is runtime text; the runner reads none of it. The runner never rewrites a caller's mandate: the `mandate` a request carries (inline text, or a file the runner reads verbatim) is what the reader receives, at the top of the composed prompt, byte for byte (`contract.md`, "Prompt composition"; `readers.py`, `mandate_text` and `compose`). This guide is about writing that mandate so a GPT reader does the job well; it changes nothing about how the lane runs.

## How the mandate reaches GPT

- Rows: `gpt-astra` is `gpt-6-astra`, effort `low` unless the request sets one (Tony's default GPT row, blueprint Q3); `gpt-sol` is `gpt-5.6-sol`, effort `medium` unless set. Both run transport `codex-exec`: the runner launches `codex exec` with the composed prompt on stdin, web search disabled, the read-only sandbox, and the working directory the profile sets (a fresh empty directory under `starved`, a directory holding copies of the documents under `packet-only`, the caller's workspace under `repo`). The row's `parity` lines in `roster.json` and "Guards, GPT lane (codex exec)" in `contract.md` are the record.
- The composed prompt is the mandate, then each document between `<<<DOCUMENT name>>>` and `<<<END DOCUMENT>>>`. A GPT reader receives no fixed reader instruction: the fixed prefix (report everything, no web, no tools) exists on the Claude and Gemini host rows only (`readers.py`, `host_prefix` returns none for a portable row). Everything a GPT reader is told, the mandate tells it, including "report everything you find" and "you have no web access".
- Effort is the row's default unless the request sets `effort`. Do not raise effort to compensate for a loose mandate; tighten the contract first. This is the Codex plugin's own rule ("Do not raise reasoning or complexity first. Tighten the prompt and verification rules before escalating").

## The recipe, adapted for cold reads

Adapted from the prompting recipe the Codex plugin ships (`codex@openai-codex` 1.0.6, `skills/gpt-5-4-prompting/SKILL.md` with `references/prompt-blocks.md`, `codex-prompt-recipes.md`, and `codex-prompt-antipatterns.md`). That recipe is written for coding runs with tools; a cold read is a review with no tools and no follow-up turn, so the review blocks apply and the action blocks do not.

1. **One task per run.** A mandate asks for one read with one purpose (find the gaps; grade against the spec; rank the failure modes). Two unrelated asks are two calls in the fleet, each with its own `call_id`, never one mandate that does both.
2. **Say what done looks like.** State the end state in the mandate: "done is every gap you found, one per line with the line it sits on, or the single line `no gaps found`". A GPT reader does not infer the desired end state.
3. **Block-structured prompts with stable tags.** Wrap the mandate's parts in XML tags with the recipe's names so the prompt has stable internal structure: `<task>`, `<structured_output_contract>` (or `<compact_output_contract>` for prose), `<grounding_rules>`, `<dig_deeper_nudge>`. Keep the tag names constant across a caller's runs; the model keys on them.
4. **An explicit output contract.** Name the exact shape, ordering, and brevity: the line form, the severity vocabulary, the order (highest-value first), and what to print when there is nothing to report. A caller that parses the reply (jpb's box validator, inspect's merge of `READERS:` results) states the shape it parses, verbatim, in the contract block.
5. **Grounding rules for anything that could drift.** A read is grounded in the documents and nothing else: "ground every claim in the documents provided; cite the document name and line; label an inference as an inference; never present a guess as a fact". Under `starved` there are no documents in the prompt and the mandate says so; under `repo` the workspace is the ground and the mandate names it as such.
6. **Leave out the action blocks.** `default_follow_through_policy`, `completeness_contract`, `verification_loop`, `action_safety`, `tool_persistence_rules`, and `missing_context_gating` are for write-capable coding runs that can retrieve, retry, or ask. A reader cannot act, fetch, or ask a question that gets answered. Replace `missing_context_gating` with one line that says what to do when the material is insufficient: say so inside the report, in the output contract's shape, rather than stop or guess.
7. **Trim.** Remove every instruction that does not change the read. The recipe's anti-patterns (vague framing, a missing output contract, "think harder", unsupported certainty, unrelated jobs mixed into one run) are the same failures in a mandate.

## A mandate skeleton

```xml
<task>
Read the scope document below cold. Find every gap a builder would hit: an undefined term, a decision the document defers without naming who decides, a requirement with no way to verify it.
</task>

<structured_output_contract>
Return only a list, one finding per line, highest-impact first:
<severity> · <document>:<line> · <the gap in one sentence> · <what would close it>
Severity is one of BLOCKER, MAJOR, MINOR. When you find nothing, return the single line: no gaps found
</structured_output_contract>

<grounding_rules>
Ground every finding in the documents provided; cite the document name and line. Label an inference as one. Never present a guess as a fact. Use nothing outside the documents: you have no web access, and no files beyond what this prompt carries.
</grounding_rules>

<dig_deeper_nudge>
After the first plausible gap, keep going: check the edges (empty inputs, retries, the failure path, who decides) before you finish.
</dig_deeper_nudge>
```

## What a mandate must not do

- Ask the reader to write a file, run a command, or fetch a URL. The sandbox is read-only and web search is off; the ask wastes the run or lands a refusal in the reply.
- Restate the roster's model id, effort, window, or budget. The runner resolves them; a value typed into the mandate binds nothing.
- Carry a credential, or anything the never-read-`~/.zshrc` rule covers (`contract.md`, "Secrets").
- Assume the reader knows the session. It is cold; the mandate and the documents are the whole briefing.
