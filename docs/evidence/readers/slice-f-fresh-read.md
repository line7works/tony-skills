# Slice F evidence — vertical converted: the fresh-read request blocks (2026-09-07)

Slice F of `docs/plans/2026-09-06-readers.md`. vertical now summons `/readers` for every reviewer, local and outside; the conversion is proven pre-merge by greps (AC1, AC2) and by one fresh `claude -p` read of the rewritten SKILL.md at its checkout path (AC3), whose request blocks are piped one by one to the runner's `validate`, plus four session-built requests on the full export that prove the packet-only sizing and the `profile-unsupported` refusal. No model call was sent for this slice: `validate` dispatches nothing. The session model that performed the read reported itself as `claude-fable-5-1`.

`<checkout>` stands for the tony-skills checkout root and `<scratch>` for this session's scratchpad directory (the read and the runner calls used the absolute paths; scrubbed here per the Slice E convention, Tony's word 2026-09-06). Sizes are bytes (`wc -c`).

## No-spend criteria (run from the repo root at the slice's head)

- AC1: `grep -cE 'mcp__codex__codex|mcp__antigravity__ask_gemini|base-instructions|skip_permissions' plugins/vertical/skills/vertical/SKILL.md` → `0` (before the edit: `4`); `grep -c '/readers' plugins/vertical/skills/vertical/SKILL.md` → `3`; `grep -c 'readers-protocol: 1' plugins/vertical/skills/vertical/SKILL.md` → `1`; `grep -c 'export directory IS the workspace' plugins/vertical/skills/vertical/SKILL.md` → `1`.
- AC2: `grep -c 'fresh subagent reviewers originate the findings' plugins/vertical/skills/vertical/SKILL.md` → `1`.
- Before and after photo: `readers validate` on the nine `assets/examples/*.json` → `valid` nine times both before and after the edit (readers' own files are untouched by this slice).

## The run directory the read was given

Steps 2 and 3 say the session mints the run id, makes the run directory, cuts the export, composes the mandate, writes the lens briefs, and stages any packet before the fleet, so the read was told a run directory that already existed, prepared by the session as those steps describe, with `plugins/readers/skills/readers/assets/fixtures/smoke-doc.md` standing as the build doc:

- `<scratch>/vertical-run/export/` — `git archive HEAD . ':!docs/reviews' ':!REVIEW.md'` unpacked (the checkout at 005b4b3)
- `<scratch>/vertical-run/mandate.md` — `assets/vertical-mandate.md` with `[BUILD_DOC]` the fixture, `[BASE_COMMIT]` `6d8f19d`, `[BOUNDARY_FILES]` two lines
- `<scratch>/vertical-run/local-spec.md`, `local-correctness.md`, `local-seams.md`, `local-security.md` — the lens briefs (LEAN's three plus the `security` pass `REVIEW.md` marks on)
- `<scratch>/vertical-run/packet-deepseek/` — a three-file stand-in for the staged export, named per Step 3: `README.md`, `plugins__vertical__skills__vertical__SKILL.md`, `plugins__readers__skills__readers__assets__contract.md`
- `<scratch>/vertical-run/readers/` — the readers run directory, empty

## The full export as a packet (session-built, the size question)

Step 3 stages the export's UTF-8 text files under path-encoded names. On this checkout that is 186 files (2.9 MB staged); three tracked files do not decode and are left out: `plugins/sun/assets/rise.wav`, `plugins/sun/assets/set.wav`, `plugins/jpb/skills/jpb/assets/jpb-wordmark.png`. Four requests were built by the session on those 186 documents with `<scratch>/vertical-run/mandate.md` as the mandate, `authorized: true`, run id `vertical-fresh-read-full`, and validated with `READERS_RUN_ROOT` at a scratch directory and a placeholder `OPENROUTER_API_KEY`:

```
deepseek · packet-only · output_budget 32768 → valid
deepseek · packet-only · no output_budget    → oversize
deepseek · repo · workspace = the export      → profile-unsupported
qwen     · packet-only · output_budget 32768 → valid
```

The `oversize` line is why Step 4 passes `output_budget: 32768` on the packet-only rows: the runner's estimate (bytes ÷ 3.5 + 10 %) puts this export near 800 k tokens, and with no budget the row's default output cap (`max_output` 384,000 on `deepseek`) leaves 664,576 of the 1,048,576 window, so the whole-repo packet is refused before any send. With a review-sized budget the limit is 1,016,576 and the packet fits. The `profile-unsupported` line is AC3's negative case on the real export: the OpenRouter rows list `starved` and `packet-only` only. After the four validations the scratch run root held nothing: `validate` creates no run dir and writes no sidecar.

## AC3 — the fresh read: GPT, the local fleet, DeepSeek

Command, from the repo root: `claude -p "<prompt>" --output-format text` (about four minutes), where the prompt was:

> Read the file plugins/vertical/skills/vertical/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: a /vertical run on the build doc plugins/readers/skills/readers/assets/fixtures/smoke-doc.md (repo-relative path; every slice signed off, the gate passed); the repo root is <checkout> and REVIEW.md is present there with passes correctness on, security on, accessibility off, data-safety off; the run id is vertical-fresh-read; the run directory is <scratch>/vertical-run; Step 2's suggest has already run (every row available, no drop notes); Tony answered 'local + GPT + DeepSeek' (GPT on the default GPT row, no model typed); the base is 6d8f19d; Step 3 is done: the export sits at <scratch>/vertical-run/export, the composed mandate at <scratch>/vertical-run/mandate.md, the local lens briefs at <scratch>/vertical-run/local-<lens>.md for the lenses signoff selects at LEAN depth plus the REVIEW.md passes marked on, and the DeepSeek packet is staged at <scratch>/vertical-run/packet-deepseek holding exactly three files: README.md, plugins__vertical__skills__vertical__SKILL.md, plugins__readers__skills__readers__assets__contract.md. Your system prompt names your model id; use it where the skill says to. Print ONLY the JSON request blocks this skill would send to /readers, as one JSON object with three keys: "gpt" (the GPT reviewer's request object), "local_fleet" (an array of the local lens request objects), "deepseek" (the DeepSeek reviewer's request object) — absolute paths everywhere, no fence, no prose before or after it, and no other output.

Output, verbatim (stdout; stderr was empty), pretty-printed here for reading:

```
{
  "gpt": {
    "protocol_version": 1,
    "run_id": "vertical-fresh-read",
    "run_dir": "<scratch>/vertical-run/readers",
    "call_id": "vertical-fresh-read-gpt-astra",
    "row": "gpt-astra",
    "profile": "repo",
    "workspace": "<scratch>/vertical-run/export",
    "mandate": "<scratch>/vertical-run/mandate.md",
    "authorized": true
  },
  "local_fleet": [
    {
      "protocol_version": 1,
      "run_id": "vertical-fresh-read",
      "run_dir": "<scratch>/vertical-run/readers",
      "call_id": "vertical-fresh-read-local-spec",
      "row": "claude-session",
      "profile": "repo-with-tools",
      "workspace": "<checkout>",
      "documents": [
        "<checkout>/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md",
        "<checkout>/REVIEW.md"
      ],
      "mandate": "<scratch>/vertical-run/local-spec.md",
      "floor": "opus",
      "session_model": "claude-fable-5-1"
    },
    {
      "protocol_version": 1,
      "run_id": "vertical-fresh-read",
      "run_dir": "<scratch>/vertical-run/readers",
      "call_id": "vertical-fresh-read-local-correctness",
      "row": "claude-session",
      "profile": "repo-with-tools",
      "workspace": "<checkout>",
      "documents": [
        "<checkout>/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md",
        "<checkout>/REVIEW.md"
      ],
      "mandate": "<scratch>/vertical-run/local-correctness.md",
      "floor": "opus",
      "session_model": "claude-fable-5-1"
    },
    {
      "protocol_version": 1,
      "run_id": "vertical-fresh-read",
      "run_dir": "<scratch>/vertical-run/readers",
      "call_id": "vertical-fresh-read-local-seams",
      "row": "claude-session",
      "profile": "repo-with-tools",
      "workspace": "<checkout>",
      "documents": [
        "<checkout>/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md",
        "<checkout>/REVIEW.md"
      ],
      "mandate": "<scratch>/vertical-run/local-seams.md",
      "floor": "opus",
      "session_model": "claude-fable-5-1"
    },
    {
      "protocol_version": 1,
      "run_id": "vertical-fresh-read",
      "run_dir": "<scratch>/vertical-run/readers",
      "call_id": "vertical-fresh-read-local-security",
      "row": "claude-session",
      "profile": "repo-with-tools",
      "workspace": "<checkout>",
      "documents": [
        "<checkout>/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md",
        "<checkout>/REVIEW.md"
      ],
      "mandate": "<scratch>/vertical-run/local-security.md",
      "floor": "opus",
      "session_model": "claude-fable-5-1"
    }
  ],
  "deepseek": {
    "protocol_version": 1,
    "run_id": "vertical-fresh-read",
    "run_dir": "<scratch>/vertical-run/readers",
    "call_id": "vertical-fresh-read-deepseek",
    "row": "deepseek",
    "profile": "packet-only",
    "documents": [
      "<scratch>/vertical-run/packet-deepseek/README.md",
      "<scratch>/vertical-run/packet-deepseek/plugins__vertical__skills__vertical__SKILL.md",
      "<scratch>/vertical-run/packet-deepseek/plugins__readers__skills__readers__assets__contract.md"
    ],
    "mandate": "<scratch>/vertical-run/mandate.md",
    "output_budget": 32768,
    "authorized": true
  }
}
```

Each block, written to its own file and piped to `plugins/readers/skills/readers/assets/readers validate <file>` (with `READERS_RUN_ROOT` at a scratch directory and a placeholder `OPENROUTER_API_KEY`):

```
vertical-fresh-read-gpt-astra → valid
vertical-fresh-read-local-spec → valid
vertical-fresh-read-local-correctness → valid
vertical-fresh-read-local-seams → valid
vertical-fresh-read-local-security → valid
vertical-fresh-read-deepseek → valid
```

The negative case, AC3's fourth request: the read's `deepseek` block with `profile` set to `repo`, `workspace` the export directory, `documents` and `output_budget` removed, and a fresh call id (`vertical-fresh-read-deepseek-repo`) — built by the session, since the skill never sends that shape:

```
vertical-fresh-read-deepseek-repo → profile-unsupported
```

After the seven validations both scratch run roots held nothing: `validate` creates no run dir and writes no sidecar.

## What the blocks show

- The GPT reviewer is one `gpt-astra` call under `repo` with the export directory as `workspace`, the composed mandate by path, `authorized: true` from the answer in the scenario, `call_id` `<run id>-<row>`, and no `model` (none was typed), no `raw_path`, no effort (R2; the inversion sentence survives at Step 4).
- The local review is four `claude-session` calls sharing the run id, one per lens (LEAN's three plus the `security` pass `REVIEW.md` marks on), each `repo-with-tools` with the repo root as `workspace`, the build doc and `REVIEW.md` as documents, the lens brief by path, `floor: opus`, `session_model` the read's own model id, `call_id` `<run id>-local-<lens>`, and no `authorized`, `effort`, `model`, or `raw_path` (R2).
- The DeepSeek reviewer is one `deepseek` call under `packet-only` with the staged export files as `documents` (path-encoded names), the same mandate, `output_budget: 32768`, and `authorized: true`; the same row asked for `repo` is refused before any send (R2, AC3).
- No model id, effort, sandbox, working directory, or window is typed in any block, which is R2's point; every block carries `protocol_version: 1` and `run_dir` (R4).

## What this slice does not prove

A live `/vertical` run is deferred (Out of scope: it needs a fully signed-off build and Tony's call after this plan's own slices are signed off). The read above shows the rewritten skill yields valid requests from a cold read of the file; it does not show the summon returning captures, the local fleet's `raw_text` reaching the appendix, an outside reviewer's sidecar `profile` landing in the Method line, or a packet-only reviewer's path-encoded citations mapping back at the merge.

## Fix pass (2026-09-07) — the read repeated against the fixed text

The signoff's three in-footprint MAJORs changed the local fleet's shape (workspace a worktree Step 3 cuts at the reviewed head, no `isolation`), the suggest (`--floor opus`), and the launch (two summons in sequence), so the cold read was run again at de21386 with the same scenario plus the worktree at `<scratch>/vertical-run/worktree` (cut with `git worktree add --detach` at the reviewed head) and a fourth key asking which requests go out in each summon. Command as above; the prompt was:

> Read the file plugins/vertical/skills/vertical/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: a /vertical run on the build doc plugins/readers/skills/readers/assets/fixtures/smoke-doc.md (repo-relative path; every slice signed off, the gate passed); the repo root is <checkout> and REVIEW.md is present there with passes correctness on, security on, accessibility off, data-safety off; the run id is vertical-fresh-read-2; the run directory is <scratch>/vertical-run; Step 2's suggest has already run (every row available, no drop notes); Tony answered 'local + GPT + DeepSeek' (GPT on the default GPT row, no model typed); the base is 6d8f19d; Step 3 is done: the export sits at <scratch>/vertical-run/export, the worktree at <scratch>/vertical-run/worktree, the composed mandate at <scratch>/vertical-run/mandate.md, the local lens briefs at <scratch>/vertical-run/local-<lens>.md for the lenses signoff selects at LEAN depth plus the REVIEW.md passes marked on, and the DeepSeek packet is staged at <scratch>/vertical-run/packet-deepseek holding exactly three files: README.md, plugins__vertical__skills__vertical__SKILL.md, plugins__readers__skills__readers__assets__contract.md. Your system prompt names your model id; use it where the skill says to. Print ONLY the JSON request blocks this skill would send to /readers, as one JSON object with four keys: "local_fleet" (an array of the local lens request objects, the first summon), "gpt" (the GPT reviewer's request object), "deepseek" (the DeepSeek reviewer's request object), "summons" (an array of strings naming, in order, which requests go out in each summon) — absolute paths everywhere, no fence, no prose before or after it, and no other output.

Output, verbatim (stdout; stderr was empty), pretty-printed here for reading:

```
{
  "local_fleet": [
    {
      "protocol_version": 1,
      "run_id": "vertical-fresh-read-2",
      "run_dir": "<scratch>/vertical-run/readers",
      "call_id": "vertical-fresh-read-2-local-spec",
      "row": "claude-session",
      "profile": "repo-with-tools",
      "workspace": "<scratch>/vertical-run/worktree",
      "documents": [
        "<checkout>/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md",
        "<checkout>/REVIEW.md"
      ],
      "mandate": "<scratch>/vertical-run/local-spec.md",
      "floor": "opus",
      "session_model": "claude-fable-5-1"
    },
    {
      "protocol_version": 1,
      "run_id": "vertical-fresh-read-2",
      "run_dir": "<scratch>/vertical-run/readers",
      "call_id": "vertical-fresh-read-2-local-correctness",
      "row": "claude-session",
      "profile": "repo-with-tools",
      "workspace": "<scratch>/vertical-run/worktree",
      "documents": [
        "<checkout>/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md",
        "<checkout>/REVIEW.md"
      ],
      "mandate": "<scratch>/vertical-run/local-correctness.md",
      "floor": "opus",
      "session_model": "claude-fable-5-1"
    },
    {
      "protocol_version": 1,
      "run_id": "vertical-fresh-read-2",
      "run_dir": "<scratch>/vertical-run/readers",
      "call_id": "vertical-fresh-read-2-local-seams",
      "row": "claude-session",
      "profile": "repo-with-tools",
      "workspace": "<scratch>/vertical-run/worktree",
      "documents": [
        "<checkout>/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md",
        "<checkout>/REVIEW.md"
      ],
      "mandate": "<scratch>/vertical-run/local-seams.md",
      "floor": "opus",
      "session_model": "claude-fable-5-1"
    },
    {
      "protocol_version": 1,
      "run_id": "vertical-fresh-read-2",
      "run_dir": "<scratch>/vertical-run/readers",
      "call_id": "vertical-fresh-read-2-local-security",
      "row": "claude-session",
      "profile": "repo-with-tools",
      "workspace": "<scratch>/vertical-run/worktree",
      "documents": [
        "<checkout>/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md",
        "<checkout>/REVIEW.md"
      ],
      "mandate": "<scratch>/vertical-run/local-security.md",
      "floor": "opus",
      "session_model": "claude-fable-5-1"
    }
  ],
  "gpt": {
    "protocol_version": 1,
    "run_id": "vertical-fresh-read-2",
    "run_dir": "<scratch>/vertical-run/readers",
    "call_id": "vertical-fresh-read-2-gpt-astra",
    "row": "gpt-astra",
    "profile": "repo",
    "workspace": "<scratch>/vertical-run/export",
    "mandate": "<scratch>/vertical-run/mandate.md",
    "authorized": true
  },
  "deepseek": {
    "protocol_version": 1,
    "run_id": "vertical-fresh-read-2",
    "run_dir": "<scratch>/vertical-run/readers",
    "call_id": "vertical-fresh-read-2-deepseek",
    "row": "deepseek",
    "profile": "packet-only",
    "documents": [
      "<scratch>/vertical-run/packet-deepseek/README.md",
      "<scratch>/vertical-run/packet-deepseek/plugins__vertical__skills__vertical__SKILL.md",
      "<scratch>/vertical-run/packet-deepseek/plugins__readers__skills__readers__assets__contract.md"
    ],
    "mandate": "<scratch>/vertical-run/mandate.md",
    "output_budget": 32768,
    "authorized": true
  },
  "summons": [
    "summon 1 (local fleet): vertical-fresh-read-2-local-spec, vertical-fresh-read-2-local-correctness, vertical-fresh-read-2-local-seams, vertical-fresh-read-2-local-security",
    "summon 2 (outside fleet, after the local merge and verification are written): vertical-fresh-read-2-gpt-astra, vertical-fresh-read-2-deepseek"
  ]
}
```

Each block validated the same way (`READERS_RUN_ROOT` at a scratch directory, a placeholder key; both run roots empty afterwards):

```
vertical-fresh-read-2-local-spec → valid
vertical-fresh-read-2-local-correctness → valid
vertical-fresh-read-2-local-seams → valid
vertical-fresh-read-2-local-security → valid
vertical-fresh-read-2-gpt-astra → valid
vertical-fresh-read-2-deepseek → valid
```

The fixed suggest, session-run against a scratch memory seeded with a remembered `opus` on `claude-session` and a remembered `gpt-5.6-sol` on `gpt-astra`: `readers suggest claude-session,gpt-astra,gpt-sol,gemini,deepseek,qwen --run fx1 --run-dir <scratch>/fx1 --floor opus` dropped both picks with a drop note each (`typed id … is not classified against floor opus`) and showed the roster default beside every row; the Step 4 local request under that run on the worktree → `valid` (the same request under a floorless suggest of the same memory → `unknown-model`, the review's reproduction); a `gpt-astra` request re-typing `gpt-5.6-sol` as `model` with no floor → `valid`.
