# Followups Slice A evidence — the contract tells the truth about the Claude lane: the fresh read (2026-09-08)

Slice A of `docs/plans/2026-09-08-readers-followups.md`. The contract, both fixed prefixes, the six Claude-row isolation labels, and readers' `SKILL.md` were edited at commit `4403cad`; this file records the no-spend criteria and the one fresh `claude -p` read AC6 asks for. No reader was dispatched: `compose` writes and prints, it sends nothing. The session model that ran the build reported itself as `claude-fable-5-1`.

`<checkout>` stands for the tony-skills checkout root and `<scratch>` for the session's scratchpad directory (the commands used the absolute paths; scrubbed here per the Slice E convention, Tony's word 2026-09-06 and 2026-09-08). Every number below is the printed output of the command beside it.

## No-spend criteria (run from the repo root at `4403cad`)

Files: `C` = `plugins/readers/skills/readers/assets/contract.md`, `P` = `plugins/readers/skills/readers/assets/readers.py`, `R` = `plugins/readers/skills/readers/assets/roster.json`, `S` = `plugins/readers/skills/readers/SKILL.md`.

- AC1: `grep -c 'receives the composed prompt and nothing else' C` → `0` (before: `1`); `grep -c 'auto-memory index' C` → `1`; `grep -c 'workdir_instruction_files' C` → `2` (the result-field list and the Claude lane); `grep -c 'git-status' C` → `2` (the Claude lane and Isolation).
- AC2: `grep -c 'Use no other model, no MCP tool, and no outbound service' P` → `2`; `grep -c 'no outbound service' C` → `2` (the Claude lane's fixed-instruction list and the Gemini lane); the two composes are below.
- AC3: `python3 -c "import json;r=json.load(open('R'));print(sorted(set(x['isolation']['starved'] for x in r['rows'] if x['transport']=='claude-subagent')))"` → `['harness-enforced (toolCalls: 0 measured; harness-injected context, the git-status block included, not measured)']` (one label; the `packet-only` labels are the same string); `grep -cF "<that label>" C` → `2` (the Claude lane and Isolation); `grep -c '"harness-enforced (toolCalls: 0)"' R` → `0` (before: `6`).
- AC4: `grep -in 'footer' C | grep -c 'capture'` → `2`, at C:72 (the `record` paragraph) and C:76 (the Claude lane's capture sentence).
- AC5: `grep -c 'nothing else' S` → `4` before (`git show main:S`) and `4` after; `wc -l < S` → `63` before and after; the two lines R5 names (S:12 and S:51) each contain `harness`. The other two matches (S:35, "never any parameter under `tool.omit`, and nothing else"; S:53, "a fleet authorizes the calls it enumerates and nothing else") are not about what the reader receives and are unchanged; recorded as a build assumption.
- AC6, examples: `readers validate` on the nine `assets/examples/*.json` → `valid` nine times before the edits and nine times after. `python3 -m py_compile P` → ok. `git diff main --stat` at `4403cad` → the four footprint files plus `docs/plans/2026-09-08-readers-followups.md` (the build doc, committed on this branch before the slice; its ledger and card are the builder's writes).

## AC2 — the two composes

Scratch clone and run root, so the tracked memory file is untouched: `git clone -q <checkout> <scratch>/clone`, then `READERS_CHECKOUT=<scratch>/clone READERS_RUN_ROOT=<scratch>/runs`, the runner run by path from the checkout (`plugins/readers/skills/readers/assets/readers compose <request>`). After both composes `git status --short` in the checkout showed only the four edited files, no `.readers/` directory in the repo root, and the scratch clone's `git status --short` was empty (`last-picks.json` not written).

Request 1 (`claude-session`, `repo-with-tools`, `floor: opus`, `session_model: claude-fable-5-1`, `workspace: .`, `run_id: followups-a-compose`, `call_id: a-claude-rwt`): `status composed`, `route agent`, `effective_model claude-fable-5-1`, `effective_effort null`. `head -6 <call dir>/prompt.md`, verbatim:

```
READER INSTRUCTIONS (fixed by readers; the mandate follows them):
- You are a cold reader. Report everything you find, low-confidence findings included; never self-censor or pre-filter. Your final message is the report and is captured verbatim.
- Use no web tool of any kind (no search, no fetch, no browser), under any profile.
- Use no other model, no MCP tool, and no outbound service.
- Do not summon /readers, do not use the Skill tool, and do not spawn agents.
- Access profile repo-with-tools: you may read files and run tests inside the workspace <checkout>; writes only to scratch and ignored caches, never a tracked file. When the sandbox stops an execution you needed, report "verification blocked" for that check and never mark it checked.
```

`head -6 <call dir>/prompt.md | grep -c 'no outbound service'` → `1`.

Request 2 (`gemini`, `starved`, `authorized: true`, same run id, `call_id: a-gemini-starved`): `status composed`, `route mcp`, `effective_model gemini-3.1-pro-high`, `effective_effort high` (the row's default; Slice B changes this). `head -6 <call dir>/prompt.md`, verbatim (the prompt's sixth line is blank):

```
READER INSTRUCTIONS (fixed by readers; the mandate follows them):
- You are a cold reader. Report everything you find; your reply is captured verbatim.
- Use no web search or fetch tool.
- Use no other model, no MCP tool, and no outbound service.
- Access profile starved: your working directory is empty on purpose; answer from this message alone.
```

`head -6 <call dir>/prompt.md | grep -c 'no outbound service'` → `1`.

## AC6 — the fresh read of `contract.md`

Run from `<scratch>/fresh` (an empty directory, so no repo instruction file loads), started 2026-09-08T16:14:02Z, ended 2026-09-08T16:14:25Z, exit 0, stderr empty:

```
claude -p "Read the file <checkout>/plugins/readers/skills/readers/assets/contract.md and answer two questions from it alone, citing the section each answer comes from: (1) On the Agent route, what does a Claude reviewer receive besides the composed prompt? (2) What does the isolation label for a Claude row under starved or packet-only measure, and what does it not measure? Do not read any other file." --output-format text < /dev/null
```

Output verbatim (nothing below this line was edited until the next heading):

**1. Agent route: what a Claude reviewer gets besides the composed prompt** (section: *The Claude lane*)

Three harness-added channels outside the composed prompt, measured 2026-09-07:

- The workspace's instruction files (`AGENTS.md`, `CLAUDE.md`, and what they import)
- The user's global `~/.claude/CLAUDE.md` with its imports
- The repo's auto-memory index

The sidecar's `workdir_instruction_files` names only the workspace half of that. (The git-status block is the Workflow route's extra channel, not the Agent route's.)

**2. What the isolation label measures under starved / packet-only** (section: *Isolation*, corroborated in *The Claude lane*)

The label is `harness-enforced (toolCalls: 0 measured; harness-injected context, the git-status block included, not measured)`.

- Measures: the run record's tool-use count, `toolCalls: 0`.
- Does not measure: the harness's own injected context, specifically the git-status block it injects under `starved` and `packet-only`, which reaches the reader anyway.

## Read-back

The answer names the three Agent-route channels (the workspace instruction files with their imports, the global `~/.claude/CLAUDE.md` with its imports, the auto-memory index), names `workdir_instruction_files` as the workspace half, places the git-status block on the Workflow route, and states the label measures the tool-use count and not the harness-injected context. AC6 met.
