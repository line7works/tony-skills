# Slice E evidence — inspect converted: the fresh-read request blocks (2026-09-06)

Slice E of `docs/plans/2026-09-06-readers.md`. inspect now summons `/readers`; its conversion is proven pre-merge by greps (AC1, AC2) and by two fresh `claude -p` reads of the rewritten file at its checkout path (AC3), whose request blocks are piped one by one to the runner's `validate`. No model call was sent for this slice: `validate` dispatches nothing. Repo head at the time of the reads: `84eb6ef` (the Slice E build checkpoint on `feat/readers-slice-e`); the session model that performed the reads reported itself as `claude-fable-5-1`.

## No-spend criteria (run from the repo root at the slice's head)

- AC1: `grep -ciE 'ollama|openrouter-box.sh|mcp__codex__codex|mcp__antigravity__ask_gemini|qwen-code|OPENROUTER_API_KEY|zshrc' plugins/inspect/skills/inspect/SKILL.md` → `0` (before the edit: `8`); `grep -c '/readers' plugins/inspect/skills/inspect/SKILL.md` → `2`; `grep -c 'readers-protocol: 1' plugins/inspect/skills/inspect/SKILL.md` → `1`; `grep -ci 'local qwen' plugins/inspect/.claude-plugin/plugin.json .claude-plugin/marketplace.json` → `0` and `0` (before: `1` and `1`).
- AC2: `grep -c 'feeds them only the doc packet' plugins/inspect/skills/inspect/SKILL.md` → `1`.
- Before and after photo: `readers validate` on the nine `assets/examples/*.json` → `valid` nine times both before and after the edits (readers' own files are untouched by this slice).

## The packet directories the reads were given

Step 3 says the session writes the packet directory before any summon, so each read was told a directory that already existed, prepared by the session exactly as Step 3 describes, with the fixture `plugins/readers/skills/readers/assets/fixtures/smoke-doc.md` standing as both the build doc and the scope doc:

- Claude lane, `<scratch>/packet-claude/`: `build-doc.md`, `scope-doc.md`, `code-book.md`, each line-numbered (`N: `) with `cat -n | sed`.
- GPT lane, `<scratch>/packet-gpt/`: the same three files plus `packet.md`, `assets/inspect-mandate.md` with its three placeholders filled from the numbered files (14,653 bytes).

`<scratch>` stands for this session's scratchpad directory and `<checkout>` for the tony-skills checkout root; the reads and the validate runs used the absolute paths, scrubbed here on Tony's word (2026-09-06) so the public record carries no machine-specific path. `docs/reviews/` already existed in the repo.

## AC3 — the Claude lane: the three-call fleet

Command, from the repo root: `claude -p "<prompt>" --output-format text`, where the prompt was:

> Read the file plugins/inspect/skills/inspect/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: an /inspect run on the build doc plugins/readers/skills/readers/assets/fixtures/smoke-doc.md (repo-relative path), whose scope doc is that same file; the repo root is <checkout>; the run id is inspect-fresh-read; Step 2's suggest has already run; the packet directory for this lane is <scratch>/packet-claude and already holds the line-numbered files Step 3 names; Tony answered 1 (Claude). Your system prompt names your model id; use it where the skill says to. Print ONLY the JSON request blocks Step 3 says you would send to /readers for this lane, as one JSON array holding the request objects (absolute paths for documents and workspace), with no fence, no prose before or after it, and no other output.

Output, verbatim (stdout; stderr was empty):

```
[
  {
    "protocol_version": 1,
    "run_id": "inspect-fresh-read",
    "call_id": "inspect-fresh-read-traceability",
    "row": "claude-session",
    "profile": "packet-only",
    "session_model": "claude-fable-5-1",
    "documents": [
      "<scratch>/packet-claude/build-doc.md",
      "<scratch>/packet-claude/scope-doc.md"
    ],
    "mandate": "You are the traceability inspector. The build doc is about to become a builder's only source of requirements. Every requirement, rationale, and criterion in it must trace to the record (the scope doc, or the repo, which a separate local inspector checks: mark repo-grounded claims 'repo-grounded, not checked here'). Hunt faux context: plausible detail presented as settled that the record never established. When the record is NO RECORD, an untraceable item is 'unverifiable — needs confirmation', never asserted as invented.\n\nYour mandate is to find reasons to REJECT the plan. Report EVERY finding, low-confidence ones included; filtering is the verifier's job, not yours. Each finding: claim (one sentence) · location (`<doc>:<line>` using the `N: ` numbers on the documents; repo `file:line` for repository findings; a finding you cannot pin goes under 'Concerns without location') · failure scenario (what the builder would wrongly build, or what a grader could not check) · severity (BLOCKER: the plan as written would build a mistake · MAJOR: a real doc defect fixable in place · MINOR: a rough edge · QUESTION: unverifiable against a missing or silent record) · confidence (high / medium / low). End with what you attacked that held up, and a one-paragraph judgment: would you approve this plan for construction."
  },
  {
    "protocol_version": 1,
    "run_id": "inspect-fresh-read",
    "call_id": "inspect-fresh-read-code-book",
    "row": "claude-session",
    "profile": "packet-only",
    "session_model": "claude-fable-5-1",
    "documents": [
      "<scratch>/packet-claude/code-book.md",
      "<scratch>/packet-claude/build-doc.md"
    ],
    "mandate": "You are the code-book inspector. Grade the build doc against the code book, quoting the code book's rules, never paraphrasing: checkable criteria (would a grader know pass from fail), self-containedness (could a builder who was never in the room execute it), slice integrity (dependency order, ends wired in, independently verifiable, ceremony scaled), and the exact load-bearing forms downstream stations key on (section names, Status labels, the ledger scaffold, ·-separated fields).\n\nYour mandate is to find reasons to REJECT the plan. Report EVERY finding, low-confidence ones included; filtering is the verifier's job, not yours. Each finding: claim (one sentence) · location (`<doc>:<line>` using the `N: ` numbers on the documents; repo `file:line` for repository findings; a finding you cannot pin goes under 'Concerns without location') · failure scenario (what the builder would wrongly build, or what a grader could not check) · severity (BLOCKER: the plan as written would build a mistake · MAJOR: a real doc defect fixable in place · MINOR: a rough edge · QUESTION: unverifiable against a missing or silent record) · confidence (high / medium / low). End with what you attacked that held up, and a one-paragraph judgment: would you approve this plan for construction."
  },
  {
    "protocol_version": 1,
    "run_id": "inspect-fresh-read",
    "call_id": "inspect-fresh-read-repo-reality",
    "row": "claude-session",
    "profile": "repo",
    "workspace": "<checkout>",
    "session_model": "claude-fable-5-1",
    "documents": [
      "<scratch>/packet-claude/build-doc.md"
    ],
    "mandate": "You are the repo-reality inspector. Every path, component, command, and convention the build doc names must exist in the workspace as claimed; check each against the repository and report what does not hold, with the repo file:line where it should have been.\n\nYour mandate is to find reasons to REJECT the plan. Report EVERY finding, low-confidence ones included; filtering is the verifier's job, not yours. Each finding: claim (one sentence) · location (`<doc>:<line>` using the `N: ` numbers on the documents; repo `file:line` for repository findings; a finding you cannot pin goes under 'Concerns without location') · failure scenario (what the builder would wrongly build, or what a grader could not check) · severity (BLOCKER: the plan as written would build a mistake · MAJOR: a real doc defect fixable in place · MINOR: a rough edge · QUESTION: unverifiable against a missing or silent record) · confidence (high / medium / low). End with what you attacked that held up, and a one-paragraph judgment: would you approve this plan for construction."
  }
]
```

Each element, written to its own file and piped to `plugins/readers/skills/readers/assets/readers validate <file>` (with `READERS_RUN_ROOT` pointed at a scratch directory and a placeholder `OPENROUTER_API_KEY`):

```
inspect-fresh-read-traceability → valid
inspect-fresh-read-code-book → valid
inspect-fresh-read-repo-reality → valid
```

## AC3 — the outside lane: GPT with Tony's word given

Command, from the repo root: `claude -p "<prompt>" --output-format text`, where the prompt was:

> Read the file plugins/inspect/skills/inspect/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: an /inspect run on the build doc plugins/readers/skills/readers/assets/fixtures/smoke-doc.md (repo-relative path), whose scope doc is that same file; the repo root is <checkout>; today is 2026-09-06; the run id is inspect-fresh-read-gpt; Step 2's suggest has already run; the packet directory for this lane is <scratch>/packet-gpt and already holds packet.md and the line-numbered files Step 3 names; docs/reviews/ exists in the repo; Tony answered 2 (GPT) and typed no other id. Your system prompt names your model id; use it where the skill says to. Print ONLY the JSON request blocks Step 3 says you would send to /readers for this lane, as one JSON array holding the request objects (absolute paths for documents, workspace, and raw_path), with no fence, no prose before or after it, and no other output.

Output, verbatim (stdout; stderr was empty):

```
[
  {
    "protocol_version": 1,
    "run_id": "inspect-fresh-read-gpt",
    "call_id": "inspect-fresh-read-gpt-gpt-astra",
    "row": "gpt-astra",
    "profile": "packet-only",
    "documents": [
      "<scratch>/packet-gpt/packet.md"
    ],
    "mandate": "Inspect the build doc per the packet's instructions and report every finding.",
    "raw_path": "<checkout>/docs/reviews/2026-09-06-inspect-smoke-doc-gpt.md",
    "authorized": true
  },
  {
    "protocol_version": 1,
    "run_id": "inspect-fresh-read-gpt",
    "call_id": "inspect-fresh-read-gpt-repo-reality",
    "row": "claude-session",
    "profile": "repo",
    "workspace": "<checkout>",
    "documents": [
      "<scratch>/packet-gpt/build-doc.md"
    ],
    "mandate": "You are the repo-reality inspector. Every path, component, command, and convention the build doc names must exist in the workspace as claimed; check each against the repository and report what does not hold, with the repo file:line where it should have been.\n\nYour mandate is to find reasons to REJECT the plan. Report EVERY finding, low-confidence ones included; filtering is the verifier's job, not yours. Each finding: claim (one sentence) · location (`<doc>:<line>` using the `N: ` numbers on the documents; repo `file:line` for repository findings; a finding you cannot pin goes under 'Concerns without location') · failure scenario (what the builder would wrongly build, or what a grader could not check) · severity (BLOCKER: the plan as written would build a mistake · MAJOR: a real doc defect fixable in place · MINOR: a rough edge · QUESTION: unverifiable against a missing or silent record) · confidence (high / medium / low). End with what you attacked that held up, and a one-paragraph judgment: would you approve this plan for construction.",
    "session_model": "claude-fable-5-1"
  }
]
```

Each element validated the same way:

```
inspect-fresh-read-gpt-gpt-astra → valid
inspect-fresh-read-gpt-repo-reality → valid
```

After the five validations the scratch run root held nothing and `docs/reviews/` held no `smoke-doc` file: `validate` creates no run dir and writes no copy at `raw_path`.

## What the blocks show

- The Claude lane is three `claude-session` calls sharing `run_id`, `packet-only` for the two paper lenses and `repo` with the repo root as `workspace` for repo-reality, each with the lens's fixed mandate ending in the shared reporting paragraph, `session_model` filled, and no `authorized` or `raw_path` (R2, R5).
- The outside lane is two calls: `gpt-astra` on `packet.md` alone under `packet-only` with the fixed one-line mandate, `raw_path` at `docs/reviews/2026-09-06-inspect-smoke-doc-gpt.md`, `authorized: true` from the word in the scenario and no `model` (none was typed); plus the repo-reality call exactly as the Claude lane sends it, with no `authorized` (R2, R3).
- No model id, effort, sandbox, working directory, or window is typed in either lane, which is R2's point.

## What this slice does not prove

The live `/inspect` run through the installed plugins is Slice I's (R5(c): three `READERS:` lines, `Inspector:` carrying `claude-session` and the session model id, `Raw:` n/a). The fresh reads above show the rewritten skill yields valid requests from a cold read of the file; they do not show the summon returning a capture, the banner landing on the `raw_path` copy, or the stamp taking the effective model from a real `READERS:` line.
