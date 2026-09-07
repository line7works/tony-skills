# Slice D evidence — precon and architect converted: the fresh-read request blocks (2026-09-06)

Slice D of `docs/plans/2026-09-06-readers.md`. Two caller skills now summon `/readers`; their conversion is proven pre-merge by greps (AC1–AC4, AC6) and by a fresh `claude -p` read of each file at its checkout path (AC5), whose request block is piped to the runner's `validate`. No model call was sent for this slice: `validate` dispatches nothing. Repo head at the time of the reads: `a101386` (the checkpoint commit on `feat/readers-slice-d`); the session model that performed the reads reported itself as `claude-fable-5-1`.

## No-spend criteria (run from the repo root at the slice's head)

- AC1: `grep -cE 'mcp__codex__codex|base-instructions|web_search|~/.claude/' <file>` → `0` for both files; `grep -c '/readers' <file>` → precon `7`, architect `5`; `grep -c 'readers-protocol: 1' <file>` → `1` for both.
- AC2: `grep -c 'there is no multi-model panel' plugins/precon/skills/precon/SKILL.md` → `0`; `grep -c 'several readers' plugins/precon/skills/precon/SKILL.md` → `1`.
- AC3: `grep -c 'You are the architect. Read the attached precon scope doc' plugins/architect/skills/architect/SKILL.md` → `1`; `grep -c 'what would you ask before building' plugins/precon/skills/precon/SKILL.md` → `1`.
- AC4: grep -c for the literal phrase except-backtick-/readers-backtick (the carve-out text, `except` followed by `/readers` in backticks) on plugins/precon/skills/precon/SKILL.md → `4`; the same on architect's SKILL.md → `3`; `grep -c "Don't invoke any skill, ever" plugins/precon/skills/precon/SKILL.md` → `1`.
- AC6: `awk '/^## Dispositions$/{f=1} f' docs/feedback.md | grep -c 'readers precon'` → `1`, and that line contains `readers plan inspect`.
- Before and after photo: `readers validate` on the nine `assets/examples/*.json` → `valid` nine times both before and after the edits (readers' own files are untouched by this slice).

## AC5 — precon: the Claude reader on the fixture as the scope doc

Command, from the repo root: `claude -p "<prompt>" --output-format text`, where the prompt was:

> Read the file plugins/precon/skills/precon/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: a /precon sitting on the scope doc plugins/readers/skills/readers/assets/fixtures/smoke-doc.md (repo-relative path) has reached Step 5, the run id is precon-fresh-read, and Tony answered the exit-test question with 1 (the Claude reader). Your system prompt names your model id; use it where the skill says to. Print ONLY the JSON request block that Step 5 says you would send to /readers for that reader, as a single JSON object with no fence, no prose before or after it, and no other output.

Output, verbatim (stdout; stderr was empty):

```
{"row": "claude-session", "documents": ["plugins/readers/skills/readers/assets/fixtures/smoke-doc.md"], "profile": "starved", "mandate": "Read this scope doc — what's unclear, what would you ask before building this?", "protocol_version": 1, "run_id": "precon-fresh-read", "call_id": "precon-fresh-read-claude-session", "session_model": "claude-fable-5-1"}
```

Piped to `plugins/readers/skills/readers/assets/readers validate -` (with `READERS_RUN_ROOT` pointed at a scratch directory):

```
valid
```

## AC5 — architect: GPT on the fixture with Tony's word given

Command, from the repo root: `claude -p "<prompt>" --output-format text`, where the prompt was:

> Read the file plugins/architect/skills/architect/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: an /architect run whose precon scope doc is plugins/readers/skills/readers/assets/fixtures/smoke-doc.md (repo-relative path) has finished the doc and visual and reached Step 6; the run id is architect-fresh-read; Tony was asked and answered 'GPT, send it' in this run, naming the default GPT row. Print ONLY the JSON request block that Step 6 says you would send to /readers for that reviewer, as a single JSON object with no fence, no prose before or after it, and no other output.

Output, verbatim (stdout; stderr was empty):

```
{"row":"gpt-astra","mandate":"You are the architect. Read the attached precon scope doc and return your own full architecture-and-delivery take for it: the walkthrough target, a v0 drawing (component list, plain-prose data flow, one simple diagram), the poured-concrete list of one-way decisions, and the deferred list. You have no other input; do not ask for any.","documents":["plugins/readers/skills/readers/assets/fixtures/smoke-doc.md"],"profile":"starved","protocol_version":1,"run_id":"architect-fresh-read","call_id":"architect-fresh-read-gpt-astra","authorized":true}
```

Piped to `plugins/readers/skills/readers/assets/readers validate -` (the same scratch run root):

```
valid
```

The block carries the fixed instruction verbatim as `mandate` (byte-equal to the SKILL.md line), `row: gpt-astra` (the default GPT row), `profile: starved`, `protocol_version: 1`, and `authorized: true` from the word in the scenario; no model id, effort, sandbox, or working directory is typed, which is R2's point.

## What this slice does not prove

The live `/precon` exit test and the live `/architect` blind review through the installed plugins are Slice I's (the plan's Source of truth constraint: no installed `readers` exists until Slice C's merge reaches a machine, and the rule against `--plugin-dir` for an installed plugin stands for precon and architect). The fresh reads above show each rewritten skill yields a valid request from a cold read of the file; they do not show the summon returning a capture.
